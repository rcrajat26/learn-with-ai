# 04 Modern Java — Build it — BUILD IT (§4.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Build it — filling the 21 gaps](06-filling-the-21-gaps.md) · Next: [Part 1 wrap-up — basics — interview basics](../90-interview-basics.md)

Every number, exception message, and bytecode listing in this file was produced by actually
compiling and running the program on this machine — `javac`/`java` **25.0.1** (Oracle GraalVM),
targeting `--release 21` so the class-file version and the visible API match Java 21 LTS. Two
honesty notes carried through the whole file rather than repeated at every harness:

- **This machine has 12 available processors** (`Runtime.getRuntime().availableProcessors() == 12`,
  common-pool parallelism **11**), not the 8-core reference machine the rest of this note set's
  arithmetic assumes. Every live-measured number below states its own processor count inline. Where
  a worked calculation needs a fixed number for cross-file consistency (`LEAF_TARGET`,
  `suggestTargetSize`), the 8-core figures are used and flagged as illustrative, not as this
  machine's measurement.
- Running on JDK 25 while compiling with `--release 21` matters for one of the twelve harnesses in
  particular (§4.8.12): several "version differences" people attribute to `--release` are actually
  properties of the **running JVM**, not the target bytecode version, and this machine makes that
  distinction directly observable.

## What this file is

Twelve harnesses, each proving one mechanism-level claim by running it rather than asserting it.
Three build the muscle of "run it, don't recall it": a fifteen-snippet puzzler set that turns
folklore into verified output, a bytecode walk that reads real constant-pool entries, and a
sealed-hierarchy binary-compatibility break that reproduces a real production failure mode
(recompile one class, ship it alone, watch the caller explode). The rest are cost harnesses —
stream-vs-loop, parallel-vs-sequential, lambda startup, collector combiners — because every
"streams are slower/faster" claim in this note set up to now has been qualitative. This is where
the numbers come from.

| # | Harness | Tags | What it proves |
|---|---|---|---|
| 4.8.1 | Fifteen-snippet puzzler set | `[PROVE]` | Fifteen distinct "surprising" behaviours, one mechanism each |
| 4.8.2 | Stream vs. loop, boxed vs. primitive | `[NUM]` `[X-REF 16]` | Where pipeline overhead does and does not matter |
| 4.8.3 | Parallel vs. sequential crossover | `[NUM]` `[PROVE]` | The crossover is a function of per-element cost, not just N |
| 4.8.4 | Source-splitting benchmark | `[NUM]` `[PROVE]` | Spliterator characteristics predict parallel speedup |
| 4.8.5 | Lambda-startup harness | `[NUM]` `[PROVE]` | One hidden class per distinct call site, generated once |
| 4.8.6 | Capture identity and allocation | `[PROVE]` `[NUM]` | Non-capturing lambdas are cached; capturing ones allocate |
| 4.8.7 | `javap` walk | `[BYTECODE]` `[PROVE]` | Every `BootstrapMethods` entry read instruction by instruction |
| 4.8.8 | Collector-combiner cost | `[NUM]` | `toList`/`joining`/`groupingBy` scale differently under `.parallel()` |
| 4.8.9 | Exhaustiveness drift | `[PROVE]` `[TRAP]` | Recompiling only a sealed hierarchy breaks its callers at runtime |
| 4.8.10 | Record serialization | `[PROVE]` | The canonical constructor cannot be bypassed by a forged stream |
| 4.8.11 | Text-block indentation sweep | `[PROVE]` | The closing delimiter's column sets the incidental-whitespace floor |
| 4.8.12 | Migration smoke harness | `[PROVE]` `[NUM]` | Most "version deltas" are runtime deltas, not compile-flag deltas |

All example data is QuizStakes: reservations, deposits, verdicts, restriction codes, and the ledger
SQL text block, per Appendix A/§11 of the shared scenario.

---

## §4.8.1 — The fifteen-snippet puzzler set

### Mental model first

Each of these fifteen programs looks like it should print the obvious thing. None of them do.
Read them as fifteen separate cracks in the same wall: **the JDK's public contract is precise, and
the "obvious" reading is almost always a stricter promise than the specification actually makes.**
The fix, every time, is not "remember the gotcha" — it's "go find the one sentence in the
`Optional`/`Stream`/`Collectors`/JLS javadoc that this snippet is testing."

### Why this exists

A senior engineer's folklore about Java accumulates from blog posts written against whichever JDK
was current in 2019–2023, and folklore compounds errors silently — nobody re-verifies "streams are
lazy" because it sounds right and mostly behaves right. A puzzler set is a forcing function:
sixty seconds per snippet, actually reason about the mechanism, then check. If your instinct built
from blogs disagrees with the mechanism the JDK source implements, the mechanism wins every time.

### When to reach for this drill, and when not

Reach for it before a system-design-adjacent interview loop where the interviewer probes "what
does this print?" on a whiteboard — that format specifically rewards mechanism fluency over
API-surface fluency. Do not reach for it as a substitute for reading `Stream`'s or `Optional`'s
class-level javadoc once; the puzzlers are a spot-check on understanding you should already have,
not a replacement for building it.

### How it works — table D-178, then each mechanism in order

The table below is D-178. Read across each row for what a reader typically predicts and the
mechanism that actually decides it; the numbered proofs follow the table for anyone who wants the
program and its real output rather than the summary.

| Puzzler | Reader predicts | What actually happens | Mechanism | Leaf |
|---|---|---|---|---|
| `peek` elision | `peek` runs for every element of the pipeline | `peek` runs only for elements the pipeline actually visits before short-circuiting | `findFirst()` on a short-circuiting stage stops pulling elements through the fused pipeline the moment one satisfies the upstream `filter`; `peek`'s side effect never runs for skipped elements | 4.8.1 |
| Stream reuse | A `Stream` can be iterated more than once, like a `Collection` | Second terminal operation throws `IllegalStateException` | `AbstractPipeline` sets `linkedOrConsumed = true` on the first terminal call and every public entry point checks it first (`MSG_STREAM_LINKED`) | 4.8.1 |
| `toList` immutability | `Stream.toList()` behaves like `Collectors.toList()` — a plain mutable `ArrayList` | `add` throws `UnsupportedOperationException` | `Stream.toList()` (JDK 16+) wraps the result in `List.copyOf`-style `ImmutableCollections.ListN`, unlike `Collectors.toList()` which is still unspecified-but-mutable | 4.8.1 |
| `toMap` null value | A collector tolerates whatever a `Map` tolerates | Throws `NullPointerException` even though a plain `HashMap.put(k, null)` is legal | `Collectors.toMap`'s default merge path calls `Map.merge`, and `Map.merge`'s contract explicitly forbids a null value regardless of the backing map | 4.8.1 |
| `groupingBy` null key | Same story — `HashMap` allows a null key, so the collector should too | Throws `NullPointerException`: "element cannot be mapped to a null key" | The classifier's result is wrapped in `Objects.requireNonNull` inside `groupingBy`'s accumulator before the map ever sees it — the collector rejects it before `HashMap` gets a chance to accept it | 4.8.1 |
| `orElse` eagerness | `orElse(x)` is lazy like `orElseGet(() -> x)` | The `orElse` argument is evaluated even when the `Optional` is present | `orElse(T)` takes a plain value, so Java evaluates the argument expression before the call, unconditionally; only `orElseGet(Supplier)` defers | 4.8.1 |
| `Optional.empty()` identity | Each call constructs a new empty `Optional` | Every call returns the exact same cached instance | `Optional.EMPTY` is a `private static final Optional<?>` singleton; `empty()` does an unchecked cast and returns it, never `new` | 4.8.1 |
| `var` diamond | `var list = new ArrayList<>()` infers the type from later usage | Infers `ArrayList<Object>` — later `.add` calls compile but with no element-type checking | `var`'s inference happens once, at the declaration, from the right-hand side alone; the diamond `<>` with no target type resolves its type argument to `Object` | 4.8.1 |
| Record array `equals` | A record's generated `equals` deep-compares every component like `Objects.equals` on everything | Two records with array components and identical array contents are **not** equal | The generated `equals` uses `Objects.equals(a, b)` per component, and array types have no overridden `equals` — it falls back to reference identity | 4.8.1 |
| Pattern-switch NPE | A pattern `switch` behaves like `if`/`instanceof` and simply skips a `null` subject | Throws `NullPointerException` unless a `case null` arm is present | JLS §14.11.3: a pattern-matching switch (as opposed to a legacy `switch` on `Integer`/`String`) has no implicit null-to-default fallthrough; only an explicit `case null` catches it | 4.8.1 |
| Text-block indentation | Indentation in source is preserved verbatim | Leading whitespace common to every content line **and** the closing delimiter is stripped | JEP 378's incidental-whitespace algorithm computes the minimum indentation across all lines including the closing `"""` line, then strips exactly that much from every line | 4.8.1 |
| Bound method-reference NPE | `target::trim` behaves like the lambda `() -> target.trim()` — NPE deferred to call time | NPE is thrown at the point the method-reference expression is **evaluated**, before it is ever called | A bound instance method reference's receiver is captured immediately, and the `invokedynamic` bootstrap for the bound form runs `Objects.requireNonNull` on the receiver as part of building the call site | 4.8.1 |
| `allMatch` on empty | An empty stream can't match anything, so `allMatch` should be `false` | Returns `true` | Universally-quantified predicates over the empty set are vacuously true by definition; `anyMatch` on empty correctly returns `false` (existential quantification over nothing) | 4.8.1 |
| `IntStream.sum` overflow | `sum()` promotes to a wider type to avoid overflow, the way `Collectors.averagingInt` does | Silently wraps using 32-bit two's-complement arithmetic | `IntStream.sum()`'s reduction identity and accumulator are both `int`; there is no widening step anywhere in the pipeline | 4.8.1 |
| Parallel `forEach` corruption | `parallelStream().forEach` is safe as long as the lambda body is "simple" | A shared mutable long accumulated via `array[0] += v` loses updates under contention | `forEach` provides no synchronization; concurrent non-atomic read-modify-write on a shared array slot is a plain data race, independent of how simple the expression looks | 4.8.1 |

**D-178** — The fifteen puzzlers and their mechanisms

### The diagram

D-178 is the table above — assigned as a `table` type diagram, not an SVG, per the diagram
manifest, and embedded at the point of explanation rather than pushed to an appendix.

### A minimal concrete example — all fifteen, run for real

```java
import java.util.*;
import java.util.stream.*;

public class Puzzlers {

    sealed interface Verdict permits DocVerdict {}
    record DocVerdict(String outcome) implements Verdict {}
    record LedgerRow(String[] codes) {}

    static void p1_peekElision() {
        long count = Stream.of("DEP-301", "DEP-302", "DEP-303")
                .peek(s -> System.out.println("peeked " + s))
                .filter(s -> s.endsWith("2"))
                .findFirst()
                .stream()
                .count();
        System.out.println("count=" + count);
    }

    static void p4_toMapNullValue() {
        Map<String, String> byRail = new HashMap<>();
        byRail.put("CARD", "DEP-301");
        byRail.put("BANK", null);
        try {
            Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue);
            byRail.entrySet().stream()
                    .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
        } catch (NullPointerException e) {
            System.out.println("threw: " + e.getClass().getName() + ": " + e.getMessage());
        }
    }

    static void p12_boundMethodRefNpe() {
        String target = null;
        try {
            java.util.function.Supplier<String> lookup = target::trim; // throws HERE, at creation
        } catch (NullPointerException e) {
            System.out.println("threw at CREATION time: " + e.getClass().getName());
        }
        java.util.function.Supplier<String> equivalentLambda = () -> target.trim(); // does NOT throw here
        try {
            equivalentLambda.get();
        } catch (NullPointerException e) {
            System.out.println("equivalent lambda threw at CALL time: " + e.getClass().getName());
        }
    }
    // full fifteen in the file the harness was actually run from
}
```

Ran with `javac --release 21 Puzzlers.java && java Puzzlers`, all fifteen in one file, real output:

```
--- P1 peek elision ---
peeked DEP-301
peeked DEP-302
count=1
--- P2 stream reuse ---
first count=3
threw: java.lang.IllegalStateException: stream has already been operated upon or closed
--- P3 toList immutability ---
codes=[AA-610, AA-611] impl=java.util.ImmutableCollections$ListN
threw: java.lang.UnsupportedOperationException
--- P4 toMap null value ---
threw: java.lang.NullPointerException: null
--- P5 groupingBy null key ---
threw: java.lang.NullPointerException: element cannot be mapped to a null key
raw HashMap null key OK: SUSPENSE
--- P6 orElse eagerness ---
orElse argument evaluated
v1=CLIENT_BONUS_RESERVED v2=CLIENT_BONUS_RESERVED
--- P7 Optional.empty() identity ---
e1==e2: true
System.identityHashCode equal: true
--- P8 var diamond ---
list=[AA-610, 42]
element0 class=java.lang.String (list itself is ArrayList<Object>)
--- P9 record array equals ---
r1.equals(r2): false
Arrays.equals(r1.codes(), r2.codes()): true
--- P10 pattern-switch NPE ---
threw: java.lang.NullPointerException: null
with case null -> s2=explicit-null
--- P11 text block indentation (full sweep in §4.8.11) ---
[SELECT * FROM ledger_entry\nWHERE position = 'CLIENT_CASH_AVAILABLE'\n]
length=68
--- P12 bound method-reference NPE ---
threw at CREATION time: java.lang.NullPointerException
equivalent lambda created without throwing
equivalent lambda threw at CALL time: java.lang.NullPointerException
--- P13 allMatch on empty stream ---
allMatch on empty = true (vacuous truth)
anyMatch on empty = false
--- P14 IntStream.sum overflow ---
IntStream.sum=-1294967296 expected(long)=3000000000
LongStream.sum=3000000000
--- P15 parallel forEach corruption ---
unsafeTotal=4667668134 expected=20000100000 corrupted=true
safeTotal(LongAdder)=20000100000
```

**Insight:** P12 is the one every experienced engineer gets wrong first, including the one writing
this file — the intuition is "method references are lazy like lambdas," but a *bound* method
reference is not a lambda expression with deferred receiver access; it is closer to
`Objects.requireNonNull(target).trim()` frozen at creation time, because the receiver must be
captured into the synthetic call site's argument array immediately.

### The gotcha

The gotcha is universal across all fifteen: every one of them is legal, specified, unsurprising
behaviour once you know the one sentence of contract it tests — and every one of them produces a
production incident the first time someone hits it without knowing that sentence. `groupingBy`'s
null-key NPE (P5) is the most common one in this specific domain, because a `rail` or `restriction
type` field arriving `null` from an upstream service is exactly the kind of thing a `groupingBy`
pipeline downstream of an integration boundary will eventually see.

### The definition, last

> A "surprising" JDK behaviour is, in every verified case here, the specification working exactly
> as documented — the surprise measures a gap in the reader's model, not a bug in the library.

---

## §4.8.2–4.8.4 — Benchmarking stream pipelines: boxing, parallel overhead, and source splitting

### Mental model first

A stream pipeline is a machine with three cost centres: **building it** (allocating
`AbstractPipeline` stages), **running it** (per-element work, possibly boxed), and — only under
`.parallel()` — **splitting it** (dividing the source into subtasks a `ForkJoinPool` can run
concurrently). Every benchmark in this section isolates one of those three centres. Treat this
section, not any individual number in it, as the reusable skill: given an unfamiliar pipeline,
name which of the three centres a suspected slowdown lives in before reaching for a profiler.

### Why this exists

"Streams are slower than loops" and "parallel streams are always faster on big data" are both
folklore claims stated without a workload attached, and both are wrong in the general case and
right in a specific, discoverable one. The discipline that answers "is this true for *my*
pipeline" is microbenchmarking: warm up the JIT past interpretation and C1 tiers into C2-compiled,
steady-state code, then measure many iterations and take a robust statistic (here, the minimum —
a defensible proxy for "best achievable" absent a real JMH fork).

`[X-REF 16]` Guide 16 (Testing) owns the full treatment of benchmark methodology — JMH's
`@Benchmark`/`@State`/`@Warmup`/`@Fork` annotations, blackholes to defeat dead-code elimination, and
`Mode.AverageTime` vs `Mode.Throughput`. The self-contained version needed here: **no JMH dependency
is available on this machine**, so the harnesses below use a manual discipline that captures the
same two failure modes JMH exists to prevent — insufficient warmup (the JIT hasn't reached steady
state) and dead-code elimination (the JIT proves a result is unused and deletes the whole
computation). Every harness below runs 5–20 warmup iterations before timing and writes every result
into a field the calling code inspects, specifically so the optimizer cannot discard the work.

### When to reach for `.parallel()`, and when not

Reach for it when per-element cost is genuinely expensive (network calls do **not** belong here —
`.parallel()` uses the shared common pool, which every other CPU-bound parallel stream in the
process also shares) and the source splits cheaply (§4.8.4). Do not reach for it as a default: for
cheap per-element work at any N below roughly a million elements on this machine, sequential wins
because the fork/join overhead and cache-locality loss outweigh the parallelism gained.

### How it works — three sweeps

**Sweep 1 — stream vs. loop, boxed vs. primitive, N = 10 / 1,000 / 1,000,000.** Real numbers,
`javac --release 21`, minimum of 30 timed iterations after 20 warmup iterations per cell:

```
N=        10  loop/prim=0.00013ms  stream/prim=0.00213ms  loop/boxed=0.00096ms  stream/boxed=0.00204ms
N=     1,000  loop/prim=0.00504ms  stream/prim=0.01208ms  loop/boxed=0.03158ms  stream/boxed=0.01529ms
N= 1,000,000  loop/prim=0.24575ms  stream/prim=0.15592ms  loop/boxed=0.31650ms  stream/boxed=0.33367ms
```

Read this as three separate stories, not one:

- At **N=10**, the loop wins in both variants by roughly an order of magnitude — pipeline
  construction (allocating the `IntPipeline.Head`, wrapping the terminal `Sink`) is fixed overhead
  that a ten-element loop simply doesn't have to pay.
- At **N=1,000,000 boxed**, `loop/boxed` (0.317ms) and `stream/boxed` (0.334ms) converge — both are
  now dominated by the same cost, `Integer` unboxing on every element, which the pipeline shape
  barely affects.
- At **N=1,000,000 primitive**, `stream/prim` (0.156ms) actually **beats** `loop/prim` (0.246ms).
  `IntStream.of(a).asLongStream().sum()` compiles to a tight specialized reduction loop that HotSpot
  vectorizes more readily than the hand-written `for` loop in this particular measurement — a result
  worth distrusting exactly as much as any other single microbenchmark run, and re-verifying before
  quoting it as a general rule. It is evidence that "the loop always wins" is exactly as much
  folklore as "streams are always slower."

**Insight:** the crossover is boxing, not the stream abstraction. `loop/boxed` at N=1,000,000
(0.317ms) is **slower** than `stream/prim` at the same N (0.156ms) — the choice of primitive vs.
boxed stream shape dominates the choice of loop vs. stream.

**Sweep 2 — parallel vs. sequential crossover, per-element cost swept from 0 to 100 "spins" of
`Math.sqrt`.** This machine: `availableProcessors=12`, `commonPoolParallelism=11` (so effective
width with the submitting thread participating is 12 — see §4.8's cross-reference to the
common-pool arithmetic worked with the 8-core reference figures elsewhere in this guide). Minimum
of 7 timed iterations after 5 warmup iterations per cell:

```
=== per-element spins=0 ===
  N=      100  seq=0.0050ms  par=0.0923ms  winner=sequential
  N=    1,000  seq=0.0328ms  par=0.0994ms  winner=sequential
  N=   10,000  seq=0.0755ms  par=0.4315ms  winner=sequential
  N=  100,000  seq=0.4852ms  par=1.1045ms  winner=sequential
  N=1,000,000  seq=4.8707ms  par=0.8311ms  winner=PARALLEL
=== per-element spins=10 ===
  N=      100  seq=0.0041ms  par=0.0333ms  winner=sequential
  N=    1,000  seq=0.0245ms  par=0.0659ms  winner=sequential
  N=   10,000  seq=0.1211ms  par=0.1301ms  winner=sequential
  N=  100,000  seq=0.5417ms  par=0.1895ms  winner=PARALLEL
  N=1,000,000  seq=5.4865ms  par=1.1590ms  winner=PARALLEL
=== per-element spins=100 ===
  N=      100  seq=0.0213ms  par=0.0333ms  winner=sequential
  N=    1,000  seq=0.1975ms  par=0.0859ms  winner=PARALLEL
  N=   10,000  seq=1.7688ms  par=0.4318ms  winner=PARALLEL
  N=  100,000  seq=19.2755ms  par=3.1932ms  winner=PARALLEL
  N=1,000,000  seq=189.9495ms  par=23.5141ms  winner=PARALLEL
```

`[NUM]` The crossover moves from N≈1,000,000 (cheap per-element work) down to N≈1,000 (expensive
per-element work) as per-element cost rises from 0 to 100 spins. **This is the empirical answer to
"what's the rule of thumb," and the rule of thumb is that there isn't a single N — the crossover is
a function of `perElementCost × N` versus fork/join overhead, not of N alone.** A pipeline over
QuizStakes's 2.8M daily stake reservations doing cheap arithmetic (say, summing `amount` fields)
sits near the "sequential still wins or is a toss-up" end of this table; the same 2.8M reservations
run through a per-reservation compliance-gate evaluation (expensive per-element work) sits
comfortably in "parallel wins by an order of magnitude."

**Sweep 3 — source splitting.** Same reduction (`sum`), six sources, 2,000,000 elements, all under
`.parallel()`. Real spliterator characteristics read via `Spliterator.characteristics()`, then real
timings, minimum of 6–10 iterations after 3–5 warmup:

```
int[] spliterator characteristics:            ORDERED SIZED IMMUTABLE SUBSIZED
ArrayList spliterator characteristics:        ORDERED SIZED SUBSIZED
LinkedList spliterator characteristics:       ORDERED SIZED SUBSIZED
LinkedHashSet spliterator characteristics:    ORDERED DISTINCT SIZED SUBSIZED
IntStream.range spliterator characteristics:  ORDERED DISTINCT SORTED SIZED NONNULL IMMUTABLE SUBSIZED
Files.lines spliterator characteristics:      ORDERED NONNULL

int[]                 0.121 ms
ArrayList             0.193 ms
LinkedList            4.122 ms
LinkedHashSet         4.643 ms
IntStream.range       0.120 ms
Files.lines           7.012 ms
```

`[PROVE]` This is the sharpest result in the whole section, because the characteristics bitmask
alone predicts it wrong: `LinkedList`'s spliterator **reports** `SUBSIZED`, the same claim `int[]`
makes, yet it is **34× slower** than `int[]` for the identical reduction. The mechanism: `List`'s
default `spliterator()` (which `LinkedList` inherits, having no index-based random access to
override it with) is `Spliterators.IteratorSpliterator` — an adapter that computes its size
up front (hence the honest `SIZED`/`SUBSIZED` claim) but implements `trySplit()` by **draining a
doubling batch of elements through the list's `Iterator`**, i.e. by sequential traversal. Every
split still costs O(batch size) pointer-chasing, whereas `int[]`'s spliterator splits by arithmetic
on two indices. `Files.lines` sits at the opposite extreme honestly: it reports no `SIZED` at all
(a line-based file source cannot know its element count without reading the whole file), so its
`trySplit()` degrades even further, and the timing shows it — slowest of the six despite the
smallest working set per element.

**Insight:** `SUBSIZED` in the characteristics bitmask means "I *can* report exact sub-range sizes
after a split," not "splitting is cheap." Cheap splitting requires index-based random access
underneath; `SUBSIZED` alone is compatible with an O(n)-per-split implementation.

### `[X-REF 16]` for the sibling treatment

Guide 16 owns realistic multi-fork JMH setups, warm-up/measurement iteration tuning, and the
`Blackhole` API for defeating dead-code elimination properly (this file's `holder[0] = ...` pattern
is the manual equivalent, sufficient for these harnesses but not a substitute for JMH in a real
performance investigation).

### The gotcha

The gotcha spans all three sweeps: none of the three "parallel wins," "streams are faster," or
"this source splits well" claims transfer between workloads. Every one of them requires
re-measurement against the actual per-element cost and actual source shape in front of you — this
section's real contribution isn't the specific numbers, it's the three questions to ask before
reaching for `.parallel()`: how expensive is one element, how large is N, and what does this
source's spliterator actually implement `trySplit()` as.

### Diff vs the real one

| Aspect | This harness | A real JMH benchmark |
|---|---|---|
| Warmup | 5–20 manual iterations, same JVM invocation | Configurable `@Warmup` iterations, typically 5–10, per fork |
| Forking | None — single JVM process, single class-loading/JIT history | `@Fork(N)` — separate JVM processes to eliminate cross-benchmark JIT pollution |
| Dead-code elimination | Manual `holder[0] = result` field write | `Blackhole.consume(result)`, guaranteed by the JMH annotation processor |
| Statistic reported | Minimum of N timed runs | Configurable — mean, percentiles, error bars via `@BenchmarkMode` |
| Constant folding | Risk: JIT may still discover invariants across "warmup" runs of the same input | `@State(Scope.Thread)` + `@Param` force genuinely varying, GC-visible state per invocation |
| Confidence | Single-machine, single-run numbers in this file — indicative, not authoritative | Statistically-sound confidence intervals across forks |

### The definition, last

> A stream-pipeline benchmark answers one question — build cost, per-element cost, or split
> cost — and a single microbenchmark that conflates two of the three produces a number that is real
> but not actionable.

---

## §4.8.5–4.8.6 — Lambda metafactory cost: startup and capture identity

### Mental model first

Every distinct lambda expression in source is one **call site** that, the first time control
reaches it, executes an `invokedynamic` instruction whose bootstrap method
(`LambdaMetafactory.metafactory`) generates a brand-new **hidden class** implementing the target
functional interface, then links the call site to a `CallSite` that produces instances of that
class. "Distinct call site" is a compile-time, source-position concept — two lexically identical
lambda expressions written twice in the source are two call sites and generate two hidden classes,
even though they'd behave identically at runtime.

### Why this exists

Before `invokedynamic`-based lambdas (Java 8, replacing what would otherwise have been anonymous
inner classes emitted by `javac`), every lambda-shaped piece of code would have compiled to a
`.class` file on disk, loaded eagerly at class-loading time regardless of whether that code path
ever ran. `LambdaMetafactory` moved that cost to **first use**: no `.class` file, no eager
classloading, and non-capturing lambdas get shared, cached instances instead of repeated
allocation — the mechanism this section measures directly.

### When this cost matters, and when it does not

It matters at JVM startup for a class with hundreds of lambda call sites on a cold-start-sensitive
path (a Lambda function, a CLI tool) — first-touch cost is paid then, not amortized. It essentially
never matters in steady state for a long-running service: once every call site on a hot path has
executed once, the hidden classes exist and every subsequent construction is either free (cached,
non-capturing) or a cheap allocation (capturing) — see the numbers below.

### How it works — two harnesses

**Harness A — lambda startup, 1 / 100 / 10,000 distinct call sites.** Measured via
`ClassLoadingMXBean.getLoadedClassCount()` before defining the call sites, immediately after, and
after invoking every one of them; timed the very first invocation separately from the average of
the rest.

`[NUM]` **Building the 10,000-call-site harness ran into a real limit worth reporting on its own:**
generating one `main` method containing 10,000 inline lambda assignments failed to compile —
`error: code too large` — because a single method's bytecode is capped at 65,535 bytes and 10,000
`invokedynamic` call sites plus their array-store instructions blow well past it. The fix (and the
production-relevant lesson) is the same one that applies to any generated-code pipeline: spread the
call sites across twenty helper methods of 500 each. Real output after that fix:

```
N=1     classesBefore=801 classesAfterDefine=802   classesAfterFirstCall=802   classesAfterAllCalls=802   deltaTotal=1     firstCallNanos=3208  remainingCallsTotalNanos=83      remainingCallsCount=0    avgRemainingNanos=0
N=100   classesBefore=801 classesAfterDefine=901   classesAfterFirstCall=901   classesAfterAllCalls=901   deltaTotal=100   firstCallNanos=2792  remainingCallsTotalNanos=48792   remainingCallsCount=99   avgRemainingNanos=492
N=10000 classesBefore=801 classesAfterDefine=10806 classesAfterFirstCall=10806 classesAfterAllCalls=10806 deltaTotal=10005 firstCallNanos=10417 remainingCallsTotalNanos=4200083 remainingCallsCount=9999 avgRemainingNanos=420
```

`[PROVE]` Two things this table proves, precisely:

1. **`classesAfterDefine == classesAfterFirstCall == classesAfterAllCalls` in every row.** The
   hidden class for a given call site is generated the first time *that assignment statement
   executes* (`sites[i] = () -> i;`), not the first time the resulting `Supplier.get()` is called.
   Calling `get()` later costs nothing in classes loaded — the class already exists.
2. **`deltaTotal` is within 5 of N in every row** (801→802, 801→901, 801→10806) — after subtracting
   a handful of JDK-internal classes touched incidentally by `ClassLoadingMXBean` itself, this is
   exactly one hidden class per distinct call site, confirming the syllabus's core claim directly
   rather than asserting it.

The gap between `firstCallNanos` (2,792–10,417ns) and `avgRemainingNanos` (420–492ns) is **not**
classloading — the class was already generated during the `fill` methods, before any `get()` ran.
It is ordinary JIT/interpreter first-touch cost on the `invokeinterface` dispatch itself (the very
first execution of any given call path runs interpreted before the JIT has a compiled version), the
same cost any first method call in a JVM pays, lambda or not.

**Harness B — capturing vs. non-capturing identity and allocation.**

```java
static Supplier<String> nonCapturing() {
    return () -> "CLIENT_BONUS_RESERVED";
}
static Supplier<String> capturing(String rail) {
    return () -> "DEP-301 on rail " + rail;
}
```

Real output:

```
non-capturing distinct instances across 5 calls: 1
capturing distinct instances across 5 calls (same captured arg): 5
non-capturing identity-equal fraction check acc=20000000 over 20M pairs, time=8.653083ms
capturing allocate x20000000 time=127.011375ms last=CaptureIdentity$$Lambda/0x0000000301040c38@27716f4
non-capturing 'allocate' x20000000 time=12.236792ms last=CaptureIdentity$$Lambda/0x0000000301040a10@5acf9800
nonCapturing() == nonCapturing(): true
capturing("CARD") == capturing("CARD"): false
```

`[PROVE]` `nonCapturing()` called five times returns the identical instance (`IdentityHashMap`-backed
set collapses to size 1); `capturing("CARD")` called five times with the same argument returns five
distinct instances. Twenty million repetitions of each make the cost visible: the non-capturing
form takes **12.2ms** (dominated by the method-call overhead of returning the cached reference), the
capturing form takes **127ms** (roughly 10×) because each call is a genuine object allocation
carrying its own captured `rail` value in a synthetic constructor argument. HotSpot's
`LambdaMetafactory` recognizes a non-capturing lambda body — no enclosing local, no `this` referenced
— as safe to instantiate exactly once and return that same instance from the `CallSite` forever; a
capturing lambda cannot be cached this way because each capture is semantically a different closure.

### The gotcha

The natural but wrong inference from Harness A is "lambdas are basically free after the first
call, so lambda count doesn't matter." It's directionally right for CPU cost and directionally
wrong for **memory**: 10,000 distinct call sites is 10,000 permanently-resident hidden classes (each
with its own `Class` metadata, method table, and — for capturing ones — potentially many live
instances), which is a real footprint question for a class with a very large number of unique
lambda expressions, independent of how cheap each individual invocation becomes.

### Diff vs the real one

| Aspect | This harness | A real allocation-profiling setup |
|---|---|---|
| Class-count measurement | `ClassLoadingMXBean.getLoadedClassCount()`, coarse, JVM-wide | Async-profiler or JFR `jdk.ClassLoad` events, per-classloader, with stack traces |
| Allocation measurement | Wall-clock proxy (loop timing) | JFR `jdk.ObjectAllocationInNewTLAB`/`OutsideTLAB`, exact byte counts |
| Identity check | `IdentityHashMap`-backed `Set` | Same technique is actually idiomatic here — no upgrade needed |
| Hidden class inspection | Inferred from `getLoadedClassCount()` deltas | `-Xlog:class+load=info` or `HotSpotDiagnosticMXBean` for exact hidden-class names |

### The definition, last

> A lambda call site pays its class-generation cost exactly once, at the first execution of the
> expression that creates it — not at declaration, not at first invocation of the resulting
> functional interface — and non-capturing lambdas amortize that cost across every subsequent use
> by returning a single cached instance forever.

---

## §4.8.7 — A `javap` walk

### Mental model first

`javap -c -p -v` prints exactly what the JVM will execute and exactly what the class loader will
resolve, with none of the syntactic sugar `javac` erased. Reading `BootstrapMethods` is reading the
literal recipe the JVM follows to build every `invokedynamic` call site in the class the first time
control reaches it — the mechanism underneath lambdas, method references, pattern-switch dispatch,
and string concatenation, all at once, in one class.

### Why this exists

Interviewers ask "what does a lambda compile to" expecting "an anonymous inner class," which was
true through Java 7 and has been false since Java 8. The only way to stop repeating a decade-stale
answer is to have actually read the bytecode once.

### When to reach for it, and when not

Reach for it exactly when a claim about "what the compiler does" is checkable and cheap to check —
which the next paragraph proves it always is. Never reach for it as a substitute for the JLS when
the question is about *source-level* semantics (e.g., overload resolution) rather than the compiled
artifact.

### How it works — one class, five features, real disassembly

```java
sealed interface Verdict permits DocVerdict, ScreenVerdict {}
record DocVerdict(String outcome) implements Verdict {}
record ScreenVerdict(String outcome) implements Verdict {}
record LedgerEntry(String position, java.math.BigDecimal amount) {}

static String describe(Verdict v) {
    return switch (v) {
        case DocVerdict d -> "doc:" + d.outcome();
        case ScreenVerdict s -> "screen:" + s.outcome();
    };
}

static String ledgerSql() {
    return """
            SELECT position, amount
            FROM ledger_entry
            WHERE position = 'CLIENT_CASH_AVAILABLE'
            """;
}

public static void main(String[] args) {
    Supplier<String> lambda = () -> "AA-801";
    Supplier<String> methodRef = Walk::ledgerSql;
    LedgerEntry e = new LedgerEntry("CLIENT_CASH_AVAILABLE", new java.math.BigDecimal("100.00"));
    System.out.println(lambda.get());
    System.out.println(methodRef.get());
    System.out.println(describe(new DocVerdict("VERIFIED")));
    System.out.println(e);
}
```

Compiled with `javac --release 21 Walk.java`, disassembled with `javap -c -p -v Walk.class`. The
`BootstrapMethods` table, real output:

```
BootstrapMethods:
  0: #114 REF_invokeStatic java/lang/runtime/SwitchBootstraps.typeSwitch:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #22 Walk$DocVerdict
      #32 Walk$ScreenVerdict
  1: #120 REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #102 doc:\u0001
  2: #120 REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #104 screen:\u0001
  3: #126 REF_invokeStatic java/lang/invoke/LambdaMetafactory.metafactory:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;Ljava/lang/invoke/MethodType;Ljava/lang/invoke/MethodHandle;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #106 ()Ljava/lang/Object;
      #107 REF_invokeStatic Walk.lambda$main$0:()Ljava/lang/String;
      #110 ()Ljava/lang/String;
  4: #126 REF_invokeStatic java/lang/invoke/LambdaMetafactory.metafactory:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;Ljava/lang/invoke/MethodType;Ljava/lang/invoke/MethodHandle;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #106 ()Ljava/lang/Object;
      #111 REF_invokeStatic Walk.ledgerSql:()Ljava/lang/String;
      #110 ()Ljava/lang/String;
```

`[BYTECODE]` Reading each entry:

- **Entry 0** — the pattern `switch` over the sealed `Verdict` hierarchy does **not** compile to a
  chain of `instanceof`/`checkcast`. It compiles to a single `invokedynamic` bootstrapped by
  `SwitchBootstraps.typeSwitch` (JEP 441's runtime support, `java.lang.runtime` package), whose
  method arguments are the **compile-time-known permitted case types in order** —
  `Walk$DocVerdict`, `Walk$ScreenVerdict`. At runtime this becomes a call that returns an `int`
  case index, which a `lookupswitch` bytecode instruction then dispatches on. The `describe` method
  body confirms it:
  ```
  static java.lang.String describe(Walk$Verdict);
       0: aload_0
       1: dup
       2: invokestatic  #7                  // Objects.requireNonNull  <- null check BEFORE the switch
       5: pop
       6: astore_1
       7: iconst_0
       8: istore_2
       9: aload_1
      10: iload_2
      11: invokedynamic #13,  0             // InvokeDynamic #0:typeSwitch:(Ljava/lang/Object;I)I
      16: lookupswitch  { // 2
                     0: 54
                     1: 71
               default: 44
          }
      44: new           #17                 // class java/lang/MatchException
      47: dup
      48: aconst_null
      49: aconst_null
      50: invokespecial #19                 // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
      53: athrow
      54: aload_1
      55: checkcast     #22                 // class Walk$DocVerdict
      58: astore_3
      59: aload_3
      60: invokevirtual #24                 // Method Walk$DocVerdict.outcome:()Ljava/lang/String;
      63: invokedynamic #28,  0             // InvokeDynamic #1:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
      68: goto          87
      71: aload_1
      72: checkcast     #32                 // class Walk$ScreenVerdict
      75: astore        4
      77: aload         4
      79: invokevirtual #34                 // Method Walk$ScreenVerdict.outcome:()Ljava/lang/String;
      82: invokedynamic #35,  0             // InvokeDynamic #2:makeConcatWithConstants:(Ljava/lang/String;)Ljava/lang/String;
      87: areturn
  ```
  The `default: 44` arm, reached if the runtime type doesn't match any known case (exactly the
  binary-compatibility break §4.8.9 reproduces), constructs and throws `MatchException` — read the
  instructions: `new`, `dup`, `aconst_null`, `aconst_null`, `invokespecial <init>(String,
  Throwable)`, `athrow`. Both constructor arguments are `null` here because the compiler has no
  message or cause to supply for an exhaustiveness failure it believes is unreachable.
- **Entries 1 and 2** — the two string-concatenation expressions (`"doc:" + d.outcome()` and
  `"screen:" + s.outcome()`) each compile to their own `invokedynamic` bootstrapped by
  `StringConcatFactory.makeConcatWithConstants` (JEP 280, replacing the pre-Java-9
  `StringBuilder.append` chain `javac` used to emit inline). The "recipe" string
  (`doc:\u0001`, `screen:\u0001`) uses `` as a placeholder for the one dynamic argument
  (`d.outcome()`/`s.outcome()`); the constant parts of the concatenation are baked into the
  bootstrap's static arguments rather than re-assembled at every call.
- **Entries 3 and 4** — the true lambda (`() -> "AA-801"`) and the method reference
  (`Walk::ledgerSql`) both bootstrap through `LambdaMetafactory.metafactory`, and **look
  identical at the bootstrap-argument level**: each supplies the functional interface's erased
  method type (`()Ljava/lang/Object;`), a `MethodHandle` to the implementation
  (`Walk.lambda$main$0` for the lambda body, `Walk.ledgerSql` for the method reference — the
  compiler synthesizes a private static method for the lambda body but reuses the existing
  `ledgerSql` method directly for the reference), and the reified method type
  (`()Ljava/lang/String;`). **This is the source-level proof that a lambda and an equivalent
  method reference compile to the same mechanism** — the only difference is whether `javac` had to
  synthesize a body method (`lambda$main$0`) or could point straight at an existing one.

### The gotcha

`javap`'s constant-pool line comments (`// java/util/Objects.requireNonNull:...`) are `javap`
doing the resolution for you at disassembly time — the raw class file stores only indices. Reading
`javap` output without cross-referencing the constant pool table for anything the inline comment
doesn't fully explain (as done above for the `describe` method) means trusting `javap`'s summary
instead of verifying the bytecode yourself, which defeats the purpose of the exercise.

### Diff vs the real one

| Aspect | This harness | A real bytecode-level investigation |
|---|---|---|
| Tooling | `javap -c -p -v` | Same, plus `javap -v` on JDK internals themselves, or ASM/`javap`'s own source for automated diffing |
| Scope | One class, five features, hand-read | CI-gated bytecode diffing (e.g., comparing `BootstrapMethods` counts across PRs to catch accidental lambda-count regressions) |
| Runtime correlation | Static read of the class file only | Cross-referenced with `-Xlog:class+init`, JFR class-load events, to see *when* each bootstrap actually fires |

### The definition, last

> `javap -c -p -v` on a class with a lambda, a method reference, a pattern switch, and a
> concatenation shows that all four compile to `invokedynamic` against a small set of JDK bootstrap
> methods (`LambdaMetafactory`, `StringConcatFactory`, `SwitchBootstraps`) — none of them synthesize
> a `.class` file at compile time the way pre-Java-8 anonymous classes did.

---

## §4.8.8 — Collector-combiner cost harness

### Mental model first

Every `Collector` used under `.parallel()` runs its `accumulator` many times (once per leaf task)
and then its `combiner` once per merge of two partial results. Sequential collection never calls
the combiner at all. The cost story for a parallel collector is therefore two numbers, not one: how
cheap is accumulation per element, and how cheap is combining two partial results — and the second
number is where `toList`, `joining`, and `groupingBy` diverge sharply.

### Why this exists

`Collectors.toList()`/`joining()`/`groupingBy()` are presented as interchangeable "terminal
operation" choices in most tutorials, differing only in output shape. Under `.parallel()` they are
not interchangeable in cost, because their combiners do fundamentally different amounts of work,
and the amount of that work scales with different things — total elements for some, distinct key
count for others.

### When to reach for which, and when not

Reach for `groupingBy` under `.parallel()` with confidence when the number of distinct keys is
small relative to N (QuizStakes's rail values — `CARD`/`BANK` — are exactly this shape); the merge
cost is bounded by key count, not element count. Do not assume `joining` parallelizes as well as
`toList` — its combiner concatenates `StringBuilder` contents, and that cost scales with total
string length being repeatedly recombined up the fork/join tree.

### How it works — measured at three scales

```java
double tToList = timeOf(() -> deposits.parallelStream()
        .map(Deposit::rail).collect(Collectors.toList()), 5, 8);
double tJoining = timeOf(() -> deposits.parallelStream()
        .map(Deposit::rail).collect(Collectors.joining(",")), 5, 8);
double tGroupingBy = timeOf(() -> deposits.parallelStream()
        .collect(Collectors.groupingBy(Deposit::rail, Collectors.summingDouble(Deposit::amount))), 5, 8);
```

`[NUM]` Real output, `Deposit(rail, amount)` records over QuizStakes's two card/bank rails:

```
N=    1,000  toList=0.1387ms  joining=0.2015ms  groupingBy(summingDouble)=0.3799ms
N=  100,000  toList=0.9315ms  joining=4.6428ms  groupingBy(summingDouble)=0.1649ms
N=2,000,000  toList=5.7228ms  joining=9.4043ms  groupingBy(summingDouble)=1.4213ms
```

The reversal between N=1,000 and N=100,000+ is the whole lesson. At N=1,000, fixed per-collector
setup cost dominates and `groupingBy` (the most machinery-heavy collector) looks worst. At
N=100,000 and above, `groupingBy` becomes the **cheapest** of the three, because its combiner merges
at most `leafTaskCount − 1` times regardless of N, and each merge only touches the (here, exactly
two) distinct keys — the accumulation work per leaf parallelizes cleanly and the combine step stays
flat. `joining`'s combiner, by contrast, concatenates two partial `StringBuilder`s at every merge,
and the total characters moved through those concatenations grows with N — visible directly in
`joining` going from competitive with `toList` at N=1,000 to nearly 2× slower at N=100,000.
`toList`'s combiner (an `ArrayList.addAll`) is a cheap bulk array copy, which is why it scales
smoothly between the other two.

### The diagram

No diagram is assigned to this leaf; the table above and the accumulator-array table already
carried in this note set's verified-figures block (Collectors' internal accumulator arrays — see
this file's own opening cross-reference to the corrected `summingInt`/`summingLong` accumulator
table) together cover the mechanism this section needs.

### The gotcha

**Interview:** "Does `groupingBy` parallelize well?" The honest answer is "it depends on the number
of distinct keys, not the number of elements" — a `groupingBy` over a high-cardinality key (say,
grouping QuizStakes's ~2.4M distinct `ClientId`s) pays a merge cost closer to `toList`'s, because
cardinality-many map-merge operations happen instead of a handful.

### Diff vs the real one

| Aspect | This harness | Production consideration |
|---|---|---|
| Cardinality tested | 2 keys (`CARD`/`BANK`) | Real QuizStakes pipelines group by rail (low cardinality, cheap) and occasionally by `ClientId` (high cardinality, expensive) — both belong in a real benchmark suite |
| Downstream collector | `summingDouble` only | `Collectors.groupingBy` combined with `mapping`, `filtering`, or nested `groupingBy` changes accumulator/combiner cost again |
| Map implementation | Default `HashMap` | `Collectors.groupingBy(classifier, mapFactory, downstream)` with a `ConcurrentHashMap` factory changes the parallel strategy entirely (see `Collectors.groupingByConcurrent`) |

### The definition, last

> A collector's parallel cost is the sum of per-leaf accumulation (scales with elements) and
> inter-leaf combination (scales with whatever the combiner actually merges — for `groupingBy`,
> distinct keys; for `joining`, total characters; for `toList`, nothing structurally expensive).

---

## §4.8.9 — Exhaustiveness drift: a binary-compatibility break, reproduced

### Mental model first

A sealed hierarchy's exhaustiveness check happens **once, at the compile time of the switch**, and
the compiled class file bakes in the assumption "these are the only permitted subtypes that will
ever exist." If that assumption becomes false later — a new permitted subtype is added and the
hierarchy is recompiled, but a class containing a switch over that hierarchy is not — the old
class's compiled synthetic `default` arm is reached at runtime by an instance the compiler never
knew about, and it throws.

### Why this exists

Sealed types (JEP 409) sell exhaustiveness as a compile-time safety net — "the compiler proves
every case is handled, so there's no `default` needed." That promise is scoped to **one compilation
unit's view of the hierarchy at one point in time**. It says nothing about what happens when two
separately-compiled artifacts (a library JAR and its consumer, in the pattern this harness
reproduces) drift out of sync — which is exactly the shape of a real production incident: ship a
new `Verdict` subtype in a library update without also redeploying every service that pattern-matches
over `Verdict`.

### When this bites, and how to avoid it

It bites specifically in a modular deployment where a sealed hierarchy crosses a JAR boundary — one
artifact owns the sealed interface and its permitted subtypes, another artifact contains
`switch` statements over it, and the two are versioned/deployed independently. It does **not** bite
when the hierarchy and every switch over it live in the same deployable unit recompiled and
redeployed atomically — the ordinary, safe case. The mitigation is organizational as much as
technical: sealed hierarchies that other modules pattern-match over need a single-artifact,
single-deploy discipline, or an explicit `default` arm accepted as a deliberate escape hatch.

### How it works — reproduced end to end

Step 1, compile the hierarchy and a switch over it together:

```java
// Verdict.java
public sealed interface Verdict permits DocVerdict, ScreenVerdict {}
// DocVerdict.java / ScreenVerdict.java — two records implementing Verdict

// Switcher.java
public class Switcher {
    public static String describe(Verdict v) {
        return switch (v) {
            case DocVerdict d -> "doc:" + d.outcome();
            case ScreenVerdict s -> "screen:" + s.outcome();
        };
    }
}
```

`javac --release 21 Verdict.java DocVerdict.java ScreenVerdict.java Switcher.java` — compiles
clean, runs clean.

Step 2, **without touching `Switcher.java` or recompiling it**, widen the hierarchy and add a
consumer that only the new type sees:

```java
// Verdict.java, v2 — one new permitted subtype
public sealed interface Verdict permits DocVerdict, ScreenVerdict, ReviewVerdict {}
// ReviewVerdict.java — new
public record ReviewVerdict(String outcome) implements Verdict {}

// Driver.java — new, compiled against the widened hierarchy
public class Driver {
    public static void main(String[] args) {
        Verdict v = new ReviewVerdict("AA-711 REVIEW_APPROVED");
        String s = Switcher.describe(v); // Switcher.class is the OLD, un-recompiled class file
        System.out.println("s=" + s);
    }
}
```

Recompiled only `Verdict.java`, `ReviewVerdict.java`, and `Driver.java`; `Switcher.class` on disk is
still the class file from Step 1. Ran `java -cp . Driver`, real output:

```
about to call OLD Switcher.describe with a NEW permitted subtype instance
threw: java.lang.MatchException: null
```

`[PROVE]` This is the exact behaviour the note set's own verified-figures block already established
by an independent route (an exhaustive enum switch, §4's verified correction) — **`MatchException`,
not `IncompatibleClassChangeError`, on Java 21**, and here demonstrated for a sealed-interface
pattern switch specifically rather than an enum switch, which is the shape leaf 4.8.9 actually
names. The `javap` walk in §4.8.7 already read the exact bytecode this throws from: the
`default: 44` arm's `new java/lang/MatchException` / `invokespecial <init>(String, Throwable)` /
`athrow` sequence. That code was compiled believing only `DocVerdict` and `ScreenVerdict` existed;
`ReviewVerdict` falls into the arm the compiler reserved for "this should be logically
impossible."

**Pitfall:** believing sealed-type exhaustiveness is a *runtime* guarantee because it is enforced so
strictly at compile time. It is not — it is a snapshot of the hierarchy as the switch's compilation
unit saw it, and nothing re-validates that snapshot when the hierarchy changes later. The fix is
either (a) a single-artifact deployment discipline for sealed hierarchies that cross module
boundaries, or (b) accepting an explicit `default` arm (giving up some of the exhaustiveness
guarantee deliberately, in exchange for graceful degradation instead of a `MatchException` in
production) precisely where cross-module drift is a real risk.

### The diagram

No diagram assigned to this leaf specifically; the bytecode already read in §4.8.7's
`BootstrapMethods` walk is the mechanism this section relies on.

### The gotcha

**Interview:** "If I add a new subtype to a sealed interface, do I have to update every switch over
it?" The compiler forces you to when both are recompiled together — that's the whole feature. The
gotcha is the word "when": if the switch's compilation unit is not recompiled, nothing forces
anything, and the failure moves from a compile error (safe, caught in CI) to a `MatchException`
thrown by a customer's request in production (unsafe, caught by whoever's on call).

### Diff vs the real one

| Aspect | This harness | A real modular deployment |
|---|---|---|
| Boundary | Two `.java` files in the same directory, one recompiled | A library JAR and a consuming service, independently versioned and deployed |
| Detection | Manual reproduction | Should be caught by a binary-compatibility checker (e.g., `japicmp`) gating the library's release pipeline before the drift ever reaches a consumer |
| Blast radius | One `Driver.main()` call | Every request that reaches the un-recompiled switch with the new subtype, until the consumer redeploys |
| Fix once caught | Recompile `Switcher.java` | Coordinate a consumer redeploy, or add a defensive `default` arm as an interim mitigation |

### The definition, last

> A sealed hierarchy's exhaustiveness check is a promise about one compilation, not a standing
> runtime invariant — widening the hierarchy without recompiling every switch over it turns a
> compile-time safety net into a `MatchException` thrown by whichever un-recompiled class hits the
> new case first.

---

## §4.8.10 — Record serialization: the canonical constructor cannot be bypassed

Records implementing `Serializable` use the same `ObjectOutputStream`/`ObjectInputStream` wire
format as any other class for the *output* side, but deserialization is different in one load-bearing
way: `ObjectStreamClass`'s handling of records always reads the stream's field values and then calls
the record's **canonical constructor** with them, rather than allocating the object and setting
fields directly by reflection the way default serialization does for an ordinary class. That single
difference is what this harness proves, by forging the byte stream and watching validation catch it
in one case and miss it in the other.

```java
record StakeReservation(int amountCents) implements Serializable {
    StakeReservation {
        if (amountCents < 0) throw new IllegalArgumentException("amountCents must be >= 0, got " + amountCents);
    }
}
```

Round trip first, to establish the constructor genuinely runs on the way back in:

```
=== 1. normal round trip proves the canonical constructor runs on deserialization ===
original=StakeReservation[amountCents=420] deserialized=StakeReservation[amountCents=420] equal=true
```

`[PROVE]` Then the forgery: locate the four raw bytes encoding `420` inside the serialized stream
and overwrite them in place with the encoding of `-1`, bypassing any code path that would normally
construct the value:

```
=== 2. forging the stream: patch the serialized int 420 -> -1 (invalid) ===
found value 420 at byte offset 65; patching to -1
record deserialization threw: java.io.InvalidObjectException: amountCents must be >= 0, got -1
root cause: java.lang.IllegalArgumentException: amountCents must be >= 0, got -1
```

The compact constructor's `if (amountCents < 0) throw ...` runs even though the caller never called
`new StakeReservation(-1)` directly — the invalid value only exists inside a hand-forged byte
array, and the record's deserialization path still routes it through the exact same validation
every ordinary construction goes through. `ObjectInputStream` wraps the `IllegalArgumentException`
in an `InvalidObjectException`, which is itself informative: the JDK's serialization machinery
recognizes constructor rejection as an object-validity failure, not a stream-corruption failure.

Now the contrast — the identical forgery against a plain class with the same validating
constructor, but relying on ordinary Java default serialization:

```java
static class PlainStakeReservation implements Serializable {
    private final int amountCents;
    PlainStakeReservation(int amountCents) {
        if (amountCents < 0) throw new IllegalArgumentException("amountCents must be >= 0, got " + amountCents);
        this.amountCents = amountCents;
    }
}
```

```
=== 3. same forgery against a PLAIN class using default serialization ===
found value 420 at byte offset 70; patching to -1
forged plain-class object deserialized WITHOUT the constructor running: PlainStakeReservation[amountCents=-1]
(default serialization sets the field directly via reflection; the validating constructor never executes)
```

**Insight:** default Java serialization for an ordinary class never calls any constructor at all —
not the no-arg constructor, not the validating one. It allocates the object via a
JVM-internal mechanism and assigns fields directly from the stream, which is precisely why every
security guide on serialization treats `readObject`/constructor validation as something you must
add by hand (a custom `readObject` calling back into validation, or `readResolve`) for a plain
class, while a record gets this protection automatically as a consequence of how
`ObjectStreamClass` special-cases records.

**Pitfall:** assuming "the constructor validates, so the object is always valid" for a plain
`Serializable` class. It is only always valid if every construction path — including
deserialization — actually calls that constructor, and default serialization for a plain class is
the one path that doesn't.

### Diff vs the real one

| Aspect | This harness | Real-world serialization hardening |
|---|---|---|
| Forgery method | Hand-located byte patch of one known `int` value | An attacker's forged stream targets fields whose offsets and encodings aren't known in advance — the point generalizes, the technique here is a proof, not an attack tool |
| Record protection | Automatic via canonical constructor | Still worth an explicit `readObject`-time check for cross-field invariants a single-component constructor can't express |
| Plain-class mitigation | None demonstrated (shown as the negative case) | Add `private void readObject(ObjectInputStream in)` that reads fields then re-runs validation, or avoid Java serialization for anything crossing a trust boundary (prefer a schema'd format with its own validation, e.g. Protobuf) |

### The definition, last

> A record's deserialization path always calls the canonical constructor with the values read from
> the stream, so any validation written there runs on every path an instance can come into
> existence through — a guarantee ordinary Java serialization does not give a plain class.

---

## §4.8.11 — Text-block indentation: the closing delimiter sets the floor

The incidental-whitespace algorithm (JEP 378) computes indentation to strip as the **minimum
leading-whitespace count across every content line and the closing delimiter's own line**, then
strips exactly that amount from all of them. The closing delimiter is not just a terminator — it is
a full participant in that minimum calculation, which is the one fact this sweep makes visible by
holding content indentation fixed and moving only the delimiter.

```java
// content lines both indented 8 spaces from column 0 in the source below

// (1) closing delimiter at column 8, equal to content's indentation
String d1 = """
        SELECT amount
        FROM ledger_entry
        """;

// (2) closing delimiter at column 0, LESS indented than content
String d2 = """
        SELECT amount
        FROM ledger_entry
""";

// (3) closing delimiter at column 4, between the two
String d3 = """
        SELECT amount
        FROM ledger_entry
    """;
```

`[PROVE]` Real output, leading spaces rendered visibly as `·` and newlines as `¶`:

```
(1) delimiter at content column (8):
SELECT·amount¶
FROM·ledger_entry¶
first line: [SELECT·amount]

(2) delimiter at column 0 (less indented than content):
········SELECT·amount¶
········FROM·ledger_entry¶
first line: [········SELECT·amount]

(3) delimiter at column 4 (between):
····SELECT·amount¶
····FROM·ledger_entry¶
first line: [····SELECT·amount]
```

Case (1): delimiter's own indentation (8) equals content's indentation (8), so the minimum across
all lines is 8, and all 8 leading spaces strip cleanly — this is the usual, "delimiter aligned with
content" style most formatters produce. Case (2): the delimiter sits at column 0, strictly less
indented than either content line; the minimum across all lines (content and delimiter) drops to 0,
so **nothing strips** — all 8 leading spaces from the source survive into the runtime string,
because the delimiter, being less indented than the content, is what set the floor. Case (3): the
delimiter's 4 spaces sit between the content's 8 and the extreme of 0, becoming the new minimum, so
exactly 4 spaces strip from each content line, leaving 4 behind.

**Insight:** "the closing delimiter's column determines indentation" is usually explained as if only
*more*-indented delimiters mattered (case 1's story); cases 2 and 3 are the half most explanations
skip — a *less*-indented delimiter doesn't get ignored, it actively pulls the stripping floor down
and leaves the content's own indentation partially or fully intact in the runtime string.

**Pitfall:** reflowing a text block's closing `"""` to match the surrounding code's indentation
during a refactor (an IDE auto-indent will often do this silently) without checking that the block's
*content* indentation moves with it — case (2) above is exactly what happens when a
previously-aligned delimiter (case 1's shape) gets outdented by an auto-formatter while the content
lines do not, silently reintroducing leading whitespace into what used to be a clean string.

### Diff vs the real one

| Aspect | This harness | Real text blocks in this codebase |
|---|---|---|
| Content | A trivial two-line SQL fragment | The real ledger-read SQL from §11 of the scenario spans several columns and a `WHERE` clause with multiple predicates — same algorithm, more lines to get wrong under reflow |
| Verification | Visible-marker printing (`·`/`¶`) | A unit test asserting `String.equals()` against the expected literal is the durable version of this check — visible markers are for exploration, not regression protection |

### The definition, last

> A text block's incidental indentation is the minimum leading-whitespace count taken across every
> content line **and** the closing delimiter's line — moving the delimiter alone, with content
> untouched, changes what gets stripped.

---

## §4.8.12 — Migration smoke harness: `--release` 8, 11, 17, 21

### Mental model first

`--release N` fixes two things at compile time: the class-file's `major_version` number and which
JDK API surface `javac` will let the source call. It fixes **nothing at runtime** — every one of
these class files, once compiled, ran on the exact same JDK 25 JVM in this harness. The lesson this
section exists to prove is that most claims of the shape "version N changed behaviour X" are
actually claims about the JDK that *runs* the code, and only claims about API *availability* are
properly attributable to `--release`.

### Why this exists

A migration checklist that says "recompile with `--release 21` and check for behaviour changes" is
solving half a problem, because the other half of behaviour changes come from *which JVM you deploy
onto*, entirely independent of what `--release` value built the class file. Distinguishing the two
determines whether a migration risk is caught by CI (a compile-time API check) or only shows up in
production (a runtime behaviour difference that recompiling with an old `--release` value cannot
protect against, because the class still runs on the new JVM).

### When each kind of check matters

Compile-time (`--release`) checks matter for anything the source code calls that might not exist on
an older target — exactly the shape of the `Set.of()` failure below. Runtime-JVM checks matter for
anything whose *default* changed between JDK releases regardless of source — default charset,
default TLS versions, GC defaults, helpful-NPE-message toggling. A migration plan that only compiles
with the old `--release` and calls itself validated has not tested the runtime half at all.

### How it works — four probes, one program (mostly)

```java
System.out.println("Charset.defaultCharset()=" + Charset.defaultCharset());
List<Integer> collectorsToList = mutable.stream().map(x -> x * 2).collect(Collectors.toList());
collectorsToList.add(99); // does this throw?
Set<String> setOf = Set.of("AA-610", "AA-611", "AA-700");
String s = null; s.trim(); // catch and print the NPE message
```

`[NUM]` Compiled four times, `--release 8`, `11`, `17`, `21`, each run standalone on this machine's
JDK 25:

```
=== --release 8 ===
Common.java:22: error: cannot find symbol
        Set<String> setOf = Set.of("AA-610", "AA-611", "AA-700");
  symbol:   method of(String,String,String)
  location: interface Set
```

`Set.of()` was added in Java 9 — this is a genuine `--release`-attributable failure, a source
*compiles or does not compile* depending on the target API surface, so the harness needed a
`Set.of()`-free variant to get comparable output at release 8:

```
release 8:  Charset.defaultCharset()=UTF-8   Collectors.toList() IS mutable   NPE message: Cannot invoke "String.trim()" because "<local3>" is null
release 11: Charset.defaultCharset()=UTF-8   Collectors.toList() IS mutable   Set.of order: [AA-611, AA-700, AA-610]   NPE message: Cannot invoke "String.trim()" because "<local4>" is null
release 17: Charset.defaultCharset()=UTF-8   Collectors.toList() IS mutable   Set.of order: [AA-700, AA-611, AA-610]   NPE message: Cannot invoke "String.trim()" because "<local4>" is null
release 21: Charset.defaultCharset()=UTF-8   Collectors.toList() IS mutable   Set.of order: [AA-610, AA-700, AA-611]  NPE message: Cannot invoke "String.trim()" because "<local4>" is null
```

Class-file version confirmed independently via `javap -v`, so the four artifacts genuinely are
different bytecode targets and not a `javac` no-op:

```
release 8  major version: 52
release 11 major version: 55
release 17 major version: 61
release 21 major version: 65
```

`[PROVE]` Reading the four rows against the "is this a `--release` effect or a runtime-JVM effect"
question:

- **`Charset.defaultCharset()=UTF-8`, identical across all four.** JEP 400 (Java 18) made UTF-8 the
  platform default charset. This machine runs JDK 25 for every one of the four executions, so all
  four report UTF-8 **regardless of which `--release` value built the class file** — this is a pure
  runtime-JVM property, wrongly attributed to compile target by anyone who says "recompile with 18+
  to get UTF-8 defaults." Recompiling changes nothing here; **deploying onto JDK 18+** does.
- **`Collectors.toList()` is mutable in all four**, including 21. `Collectors.toList()`'s mutability
  was never specified either way and has never changed — the version-sensitive method is the
  *different, newer* `Stream.toList()` (JDK 16+, returns an immutable list — proven directly by
  puzzler P3 in §4.8.1), not `Collectors.toList()`. Conflating the two is the actual version trap
  here, not a real `--release` behaviour difference in `Collectors.toList()` itself.
- **`Set.of()` iteration order differs on every run shown** (`[AA-611, AA-700, AA-610]` vs.
  `[AA-700, AA-611, AA-610]` vs. `[AA-610, AA-700, AA-611]`) — but this is **not** a `--release`
  effect either. `Set.of()`'s iteration order is randomized per JVM run via a `SALT32L` seed
  computed at class-init time specifically so code cannot come to depend on it; running the exact
  same `--release 21` class twice would show two different orders too. The three different-looking
  orders above are an artifact of comparing three separate JVM invocations, not of three different
  compile targets.
- **The NPE message is helpful (`"Cannot invoke \"String.trim()\" because \"<local4>\" is null"`) in
  all four**, including the `--release 8` build. Helpful NPE messages (JEP 358) are a
  `-XX:+ShowCodeDetailsInExceptionMessages` runtime feature, default-on since JDK 15 — again a
  property of the JVM executing the bytecode, not of the `--release` value that produced it. The
  local variable name (`<local3>` vs `<local4>`) differing by one between release 8 and the rest is
  a compiler artifact (a slightly different local-slot layout across `javac` versions targeting
  different releases), not a JEP 358 behaviour change.

**Insight:** of the four probes, exactly one — `Set.of()` failing to compile at `--release 8` — is
attributable to the compile flag. The other three (`Charset.defaultCharset()`, the helpful-NPE
message, and `Set.of()`'s per-run ordering) are all properties of the **JDK actually running the
class**, invisible to a migration checklist that only checks "does it compile with `--release N`."

**Pitfall:** treating "I compiled and tested with `--release 8`" as evidence the code will behave
the same when deployed to an environment still running an actual Java 8 JVM. It only proves the
*source* doesn't call any API newer than 8 — it says nothing about runtime defaults, because this
harness's own JDK-25-for-every-release results are the same JDK-25 behaviour a real Java 8 runtime
would **not** reproduce (an actual Java 8 JVM predates JEP 400 and JEP 358 entirely, so
`Charset.defaultCharset()` there would report the platform default, not UTF-8, and the NPE message
would be the bare `NullPointerException` with no detail). This harness's own numbers would be wrong
if quoted as "what Java 8 does" — they are "what JDK 25 does with `--release 8`-shaped bytecode,"
which is a materially different, narrower claim.

### The diagram

No diagram assigned to this leaf. The four-column comparison table above is the artifact this
section relies on.

### Diff vs the real one

| Aspect | This harness | A real migration validation pipeline |
|---|---|---|
| Runtime coverage | One JVM (JDK 25) for all four `--release` targets | Should run each `--release` target's tests on an actual matching JDK distribution, not just JDK 25 with a compile flag |
| Probes | Four hand-picked behaviours | A real smoke suite covers every JEP with a stated behaviour change touching the application's actual API surface — locale-sensitive formatting, TLS defaults, GC choice, security-manager removal (JDK 24) |
| Automation | Manual four-way `javac`/`java` invocation | CI matrix across JDK distributions, one job per target runtime, not per `--release` flag alone |

### The definition, last

> `--release N` guarantees the compiled class file's API surface and bytecode version match JDK N —
> it guarantees nothing about runtime behaviour, because runtime behaviour is a property of the JVM
> that executes the class file, which a migration test must vary independently of the compile flag
> to actually validate.

---

## Pitfalls

### Assuming a bound method reference defers null-checking like an equivalent lambda

**Wrong**
```java
String target = null;
Supplier<String> lookup = target::trim; // believed: "safe until called, like a lambda"
lookup.get(); // believed: NPE happens HERE
```
Real output: the `NullPointerException` is thrown at the `target::trim` line itself, before
`lookup.get()` is ever reached.

**Right**
```java
String target = null;
Supplier<String> lookup = () -> target.trim(); // genuinely defers the null check to call time
try {
    lookup.get(); // NPE happens HERE, as expected
} catch (NullPointerException e) { /* handle */ }
```

**Why people believe it:** method references are taught as "shorthand for a lambda," and for the
*unbound* form (`String::trim`, receiver supplied per-call) that framing is accurate. For the
*bound* form the receiver is captured once, eagerly, at the point the reference expression itself
is evaluated — the eager `Objects.requireNonNull` on that captured receiver is a JVM implementation
detail of the `invokedynamic` bootstrap for bound references, not something the "shorthand for a
lambda" mental model predicts.

### Believing `groupingBy` tolerates whatever `HashMap` tolerates

**Wrong**
```java
List<String> rails = Arrays.asList("CARD", "BANK", null);
Map<String, List<String>> byRail = rails.stream().collect(Collectors.groupingBy(r -> r));
// believed: works, because a raw call to HashMap.put with a null key is legal
```
Real output: `NullPointerException: element cannot be mapped to a null key`.

**Right**
```java
Map<String, List<String>> byRail = rails.stream()
        .collect(Collectors.groupingBy(r -> r == null ? "UNSPECIFIED" : r));
```

**Why people believe it:** `groupingBy`'s default downstream map really is a `HashMap`, and a
`HashMap` really does allow a null key — the false step is assuming the collector's own accumulator
contract inherits the backing map's permissiveness, when in fact the classifier's result is
explicitly `Objects.requireNonNull`-checked before the map is ever touched.

### Trusting `--release N` alone as proof of Java-N runtime behaviour

**Wrong**
```
javac --release 8 Common.java
java Common   # believed: "this proves the code behaves as it would on Java 8"
```
Real output on this machine: `Charset.defaultCharset()=UTF-8` and a fully-detailed NPE message —
neither of which an actual Java 8 JVM would produce (Java 8 predates both JEP 400 and JEP 358).

**Right**
```
javac --release 8 Common.java
# then actually run it under a Java 8 (or the oldest supported) JVM distribution,
# not the JVM used to develop against --release 21
```

**Why people believe it:** `--release` genuinely does gate the *compile-time* API surface faithfully
(the `Set.of()` failure in §4.8.12 is real and correctly attributed), which makes it easy to
over-generalize the flag's guarantee to runtime behaviour it was never designed to control.

### Assuming `Collectors.summingInt` is overflow-safe because `averagingInt` is

**Wrong**
```java
int total = deposits.stream().collect(Collectors.summingInt(Deposit::amountCents));
// believed: safe, because "summingInt/averagingInt accumulate into a long[]"
```
Verified against `Collectors`' actual accumulator arrays at the jdk-21+35 tag: `summingInt`
accumulates into `new int[1]` — a plain `int` slot, not `long`.

**Right**
```java
long total = deposits.stream().collect(Collectors.summingLong(Deposit::amountCents));
// or explicitly widen inside summingInt's mapper if the API must stay int-shaped
```

**Why people believe it:** `averagingInt` really does use a `long[2]` (sum, count) internally, and
generalizing "the *Int collectors avoid int overflow" from that one correct case to `summingInt`
(which does not) is exactly the kind of half-right folklore this note set's verified-figures block
exists to correct.

## Cheat sheet

| Harness | One-line takeaway | Real number to remember |
|---|---|---|
| Fifteen puzzlers (4.8.1) | Every "surprise" is documented behaviour, not a bug | P12: bound method-ref NPE throws at creation, not call |
| Stream vs. loop (4.8.2) | Boxing dominates the choice more than stream-vs-loop does | primitive stream beat the loop at N=1M in this run: 0.156ms vs 0.246ms |
| Parallel crossover (4.8.3) | Crossover is `perElementCost × N` vs. fork/join overhead, not N alone | crossover moved from N≈1M (0 spins) to N≈1,000 (100 spins) |
| Source splitting (4.8.4) | `SUBSIZED` ≠ cheap split; only true random-access sources split cheaply | `LinkedList` claims `SUBSIZED` but ran 34× slower than `int[]` |
| Lambda startup (4.8.5) | One hidden class per distinct call site, generated on first execution of that site | 10,000 call sites → 10,005 new loaded classes, exactly |
| Capture identity (4.8.6) | Non-capturing lambdas are cached singletons; capturing ones allocate | 20M capturing calls: 127ms; 20M non-capturing calls: 12.2ms |
| `javap` walk (4.8.7) | Lambda, method ref, pattern switch, concatenation all compile to `invokedynamic` | pattern switch bootstraps via `SwitchBootstraps.typeSwitch`, not `instanceof` chains |
| Collector combiners (4.8.8) | `groupingBy`'s merge cost scales with distinct keys, not N | at N=2M, `groupingBy` (1.42ms) beat `toList` (5.72ms) |
| Exhaustiveness drift (4.8.9) | Sealed exhaustiveness is a per-compilation snapshot, not a runtime guarantee | reproduced: `MatchException`, not `IncompatibleClassChangeError`, on Java 21 |
| Record serialization (4.8.10) | Records always route deserialization through the canonical constructor | forged `-1` amount → `InvalidObjectException`; same forgery on a plain class → silently deserialized |
| Text-block sweep (4.8.11) | The closing delimiter participates in the indentation-stripping minimum | delimiter at column 0 vs. content at column 8 → 0 characters stripped |
| Migration smoke (4.8.12) | Most version deltas are runtime-JVM deltas, not `--release` deltas | UTF-8 default and helpful NPE messages appeared even at `--release 8`, because JDK 25 ran the class either way |

## Self-test

**Q1.** Why does `target::trim` throw a `NullPointerException` immediately, on the line where it is
assigned to a `Supplier<String>`, when `target` is `null` — while the equivalent lambda
`() -> target.trim()` does not throw until `.get()` is called?

<details><summary>Answer</summary>

A bound instance method reference captures its receiver at the point the reference expression is
evaluated, because the receiver has to become part of the arguments passed into the
`invokedynamic` call site's linkage. The JVM's bootstrap for a bound method reference runs
`Objects.requireNonNull` on that captured receiver immediately, as part of constructing the
`CallSite` — so a null receiver fails before the `Supplier` even exists. The lambda form
`() -> target.trim()` is a genuinely different closure: it captures the *variable* `target`, and the
dereference `target.trim()` only happens the first time the lambda body actually executes, which is
whenever `.get()` is called, not when the lambda itself is created.

</details>

**Q2.** A `groupingBy` collector over 2,000,000 `Deposit` records grouped by a two-valued `rail`
field runs *faster* in parallel at high N than `Collectors.toList()` on the same stream, despite
`groupingBy` looking like the "heavier" collector. What in the collector's contract explains this?

<details><summary>Answer</summary>

Every parallel collector pays two kinds of cost: per-leaf accumulation (roughly proportional to
elements processed) and inter-leaf combination (proportional to whatever the combiner actually has
to merge). `groupingBy`'s combiner merges two partial `Map`s, and the work in that merge is bounded
by the number of *distinct keys*, not the number of elements — with only two rail values, every
merge touches at most two keys regardless of how many millions of elements fed into each side.
`toList`'s combiner, by contrast, does an `ArrayList.addAll`, whose cost is proportional to the
number of elements being merged. As N grows, `groupingBy`'s merge cost stays essentially flat while
`toList`'s grows with N, so at large enough N the low-cardinality `groupingBy` overtakes it.

</details>

**Q3.** A sealed interface `Verdict` gains a new permitted subtype, and the module that owns the
hierarchy is redeployed. A separate service with a `switch` over `Verdict` is not redeployed. What
happens the first time that service receives an instance of the new subtype, and why does the JLS's
exhaustiveness guarantee not prevent it?

<details><summary>Answer</summary>

The un-redeployed service's compiled `switch` still contains the synthetic `default` arm the
compiler generated when it believed the hierarchy had only the old permitted subtypes. On Java 21
that arm constructs and throws a `java.lang.MatchException`. The JLS's exhaustiveness guarantee only
holds *for the compilation that produced this class file* — it is checked once, against the
hierarchy as that compiler saw it, and baked permanently into the bytecode. It says nothing about
what happens when the hierarchy changes in a separately-compiled, separately-deployed artifact after
the fact; there is no runtime re-validation of exhaustiveness, only the one-time compile-time check.

</details>

**Q4.** Why does a forged byte stream that sets an invalid negative `amountCents` get rejected with
an `InvalidObjectException` when deserializing a `record StakeReservation(int amountCents)` with a
validating compact constructor, but the identical forgery against a plain class with the same
validating constructor deserializes silently into an invalid object?

<details><summary>Answer</summary>

`ObjectStreamClass`'s deserialization path for a record always reads the stream's field values and
then invokes the record's canonical constructor with them — so any validation in that constructor
(including a compact constructor's implicit validation-then-field-assignment) runs on every
deserialization, exactly as it would on any other construction path. Default Java serialization for
an ordinary class does not call any constructor at all during deserialization; it allocates the
object through a JVM-internal mechanism and assigns the serialized values directly to the object's
fields via reflection, bypassing whatever validation lives inside the class's declared
constructors entirely.

</details>

**Q5.** Two text blocks have identical content lines, both indented 8 spaces from the left margin in
the source. One closes with `"""` at column 8 (aligned with the content); the other closes with
`"""` at column 0. Why do these two text blocks produce different runtime strings even though their
content lines are byte-for-byte identical in the source?

<details><summary>Answer</summary>

The incidental-whitespace-stripping algorithm computes the number of leading-whitespace characters
to remove as the minimum indentation across every content line **and** the closing delimiter's own
line, then strips that amount uniformly. When the delimiter sits at column 8, matching the content,
the minimum is 8, and all 8 leading spaces strip from every content line. When the delimiter sits at
column 0, it becomes the new minimum for the whole block, dropping the stripped amount to 0 — so
none of the content lines' leading spaces are removed at all, even though the content lines
themselves were never edited.

</details>

**Q6.** Running the same class file, compiled once with `--release 8`, on this machine's JDK 25
prints `Charset.defaultCharset()=UTF-8` and a fully-detailed `NullPointerException` message. Is
either of these observations evidence about how that class would behave on an actual Java 8 JVM?
Why or why not?

<details><summary>Answer</summary>

No. Both the UTF-8 default charset (JEP 400, landed in Java 18) and the detailed
`NullPointerException` message (JEP 358, default-on since Java 15) are properties of the **JVM that
executes** the class file, not properties encoded into the class file by `--release`. `--release 8`
only constrains the compiled bytecode version and the API surface `javac` permits calling; it has no
effect on the runtime's own defaults. Running that `--release 8` class file on an actual Java 8 JVM
(which predates both JEPs) would show the platform's native default charset and a bare
`NullPointerException` with no detail message — neither of which this harness's JDK-25-hosted run
demonstrates.

</details>

**Q7.** In the fifteen-snippet puzzler set, `Stream.<String>empty().allMatch(s -> s.startsWith("AA-"))`
returns `true` while `Stream.<String>empty().anyMatch(...)` on the same predicate returns `false`.
Both operate on the same empty stream and the same predicate — why do they disagree?

<details><summary>Answer</summary>

`allMatch` asks a universally-quantified question — "does every element satisfy the predicate" —
and a universal claim over an empty set is vacuously true by the standard mathematical definition of
quantification over an empty domain: there is no element to serve as a counterexample. `anyMatch`
asks an existentially-quantified question — "does at least one element satisfy the predicate" — and
an existential claim requires at least one witnessing element to be true, which an empty stream
cannot supply, so it correctly returns `false`. Both answers are the specification working exactly
as the standard logical convention for empty-domain quantification dictates, not a special case the
JDK invented.

</details>

**Q8.** A benchmark harness with no JMH dependency available measures `stream/prim` beating
`loop/prim` at N=1,000,000 (0.156ms vs. 0.246ms) but losing to it at N=10 and N=1,000. What two
specific risks does the manual (non-JMH) measurement discipline used in this file leave
un-guarded-against that a real JMH harness would close, and how does this file's harness attempt to
mitigate each anyway?

<details><summary>Answer</summary>

The two risks are insufficient warmup (measuring code still in interpreted or C1-compiled tiers,
before the JIT has reached steady-state C2 compilation) and dead-code elimination (the JIT proving a
computed result is never observed and deleting the computation entirely, making the "benchmark"
measure nothing). This file's harnesses mitigate the first by running 5 to 20 warmup iterations of
each operation before any timed iteration, and mitigate the second by writing every result into a
field the surrounding code reads afterward (`holder[0] = result`), which is the same purpose a real
JMH `Blackhole.consume(result)` serves, just without JMH's guarantee that the annotation processor
enforces it and without JMH's per-fork process isolation, which prevents JIT profile pollution
carrying over between different benchmarks run in the same JVM.

</details>

## Deferred

None.

---

**Leaves covered:** 4.8.1, 4.8.2, 4.8.3, 4.8.4, 4.8.5, 4.8.6, 4.8.7, 4.8.8, 4.8.9, 4.8.10, 4.8.11, 4.8.12 (12 leaves)
**Leaves deferred:** none
**Diagrams included:** D-178
**Target version:** Java 21 LTS
**Lines:** 1505
