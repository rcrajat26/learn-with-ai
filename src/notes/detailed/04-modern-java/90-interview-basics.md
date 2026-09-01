# 04 Modern Java — Part 1 wrap-up — basics — INTERVIEW (§1.1, §1.20)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](00-index.md)
Previous: [Build it — diagnostic harnesses](build-it/07-diagnostic-harnesses.md) · Next: [Part 2 wrap-up — intermediate — interview intermediate](91-interview-intermediate.md)

This file closes Part 1. It owns no syllabus leaves of its own — it is the checkpoint that sits
after every basics-tier subject file in 04 Modern Java and before Part 2 begins. Three things
live here and nowhere else in Part 1: the summary table over the whole basics tier, ten
speaking-length interview Q&As, and five predict-the-output puzzles, each one actually compiled
and run on this machine with `javac --release 21` / `java --release 21` rather than recalled.

Why "modern Java" is a topic at all (§1.1): every release from 9 through 21 shipped language and
library changes that individually look like syntax sugar — `var`, records, sealed interfaces,
pattern-matching `switch`, text blocks, virtual threads — but together they change what idiomatic
Java *is*. An engineer who learned Java 8 and stopped reads 2024-era code fluently at the surface
and misjudges it at the mechanism level: they know a record "is like a class with less
boilerplate" but not that its component fields are `final` and that a compact constructor can only
reassign the constructor *parameter*, never the field, because the compiler writes the field
assignment for you afterward (verified below in Puzzle 2). They know virtual threads are "cheap"
but not that the scheduler carrying them is a `ForkJoinPool` with a documented FIFO comment on its
`asyncMode` argument, a `maxPoolSize` floor of 256 that is *not* a flat default once you cross 256
cores, and a third tunable (`minRunnable`) most blog posts never mention. Part 1 exists to replace
"I've used this" with "I know what allocates, what blocks, and what the JLS actually guarantees."

The library additions, 9 → 21 (§1.20): the basics tier tracks four release lines that matter for
an interview loop — Java 9 (modularity, `List.of`/`Map.of`, private interface methods), Java 10–11
(`var`, `Optional.isEmpty`, the LTS baseline most shops still run), Java 17 (sealed interfaces,
pattern-matching `instanceof`, the second LTS), and Java 21 (records patterns, pattern-matching
`switch`, virtual threads, structured concurrency preview — the LTS this whole note set targets).
Every constant, default, or synthetic-throw type that differs across that span is called out
inline at the point of the claim in the subject files this wraps up, and repeated here in the
summary table below.

---

## Summary table — the whole basics tier

Every row below is a primary concept from a Part 1 subject file. "Landed at" gives the release
that introduced or last changed the behaviour; where a widely repeated claim is version-stale, the
"version trap" column names it explicitly.

| Concept | Landed at | Mechanism, one line | Sibling it is chosen against | Version trap |
|---|---|---|---|---|
| `var` (LVTI) | 10 | Compiler infers the static type from the initializer at the call site; the variable is still statically typed, not dynamic | Explicit type — wins when the initializer alone does not tell the reader the type (`var result = queryLedger();`) | "`var` makes Java dynamically typed" — false; erasure and the inferred type are fixed at compile time, `javap` shows the concrete type in the local variable table |
| Records | 16 | A record header declares components; the compiler generates a canonical constructor, accessors named after the components (`bonusPortion()`, not `getBonusPortion()`), `equals`/`hashCode`/`toString`, and makes every component field `final` | A regular class with a builder — wins when the type needs multiple construction paths or mutable state | "You can assign to a component field inside a compact constructor" — false; you reassign the constructor *parameter*, the compiler emits the field write afterward (Puzzle 2) |
| Sealed interfaces | 17 | `permits` fixes the exhaustive set of implementations at compile time; the compiler tracks that closed set for exhaustiveness checks in pattern-matching `switch` | An open interface — wins when third parties must be able to implement it | None at 21; sealed hierarchies cannot be un-sealed without recompiling the `permits` clause |
| Pattern-matching `instanceof` | 16 | `if (verdict instanceof DocumentVerdict dv)` binds `dv` only in the branch where the test succeeds, tracked by flow scoping, not a separate cast | The classic cast-after-check idiom — always loses once the pattern form is available; it is strictly safer | None; flow scoping is spec behaviour, not a JIT optimisation |
| Pattern-matching `switch` on sealed types | 21 | The compiler proves exhaustiveness against the `permits` list; no `default` is required once every permitted subtype has a case | An `if`/`else if` chain — loses because it gives up compiler-checked exhaustiveness | Exhaustiveness on a plain `enum` still needs every constant *or* a `default`; the enum case is where the synthetic-default trap below lives |
| Exhaustive `switch`'s synthetic default | 14 (throw type changed at 21) | An enum `switch` expression compiles a hidden default branch for the case a class file is out of sync with a recompiled enum | A `default ->` you write yourself, which always wins if you want a chosen fallback | `IncompatibleClassChangeError` through Java 20, `java.lang.MatchException` from Java 21 — the syllabus statement that it "replaced `NoSuchFieldError`" is backwards; both existed, only the throw type moved (Puzzle 3) |
| Text blocks | 15 | `"""` delimiters strip incidental leading whitespace using the *least-indented* non-blank line as the margin, computed at compile time, not at runtime | String concatenation with `+` — always loses for multi-line SQL or JSON, kept only where a single line is genuinely simpler | Trailing spaces before the closing `"""` are significant unless the line ends with `\` or `\s`; copy-pasted text blocks silently gain trailing whitespace |
| Stream laziness / `AbstractPipeline` | 8 (message text stable through 21) | Each intermediate operation allocates one pipeline stage wrapping the previous one; nothing traverses the source until a terminal operation calls `evaluate`, which walks `wrapSink` backwards from the terminal stage, then `copyInto` | A pre-Java-8 manual loop — wins only when the operation is not expressible as filter/map/reduce or when laziness itself is the bug (side effects in `peek`) | A stream with no terminal operation does *nothing at all* — not "runs the intermediate ops eagerly", a common misreading of "eager" library method names like `Collectors.toList()` |
| Stream reuse guard | 8 | `linkedOrConsumed` is checked at every public entry point before the source is asked for; a second terminal call throws before the source is even touched | N/A — this is a safety rail, not a feature with a sibling | `MSG_CONSUMED` ("source already consumed or closed") exists in `AbstractPipeline` but is reachable only through an internal double-take on the source; ordinary reuse always reports `MSG_STREAM_LINKED` ("stream has already been operated upon or closed") — Puzzle 1 |
| `Collectors.summingInt` / `summingLong` | 8 | `summingInt` accumulates into `new int[1]`; `summingLong` into `new long[1]`; both are plain running sums with no compensation | `IntStream.sum()` — same overflow behaviour, chosen instead when the source is already an `IntStream` | "`summingInt` accumulates into a `long[]` so it cannot overflow" is false — only `averagingInt`/`averagingLong` get the wider `long[2]` slot; `summingInt` overflows exactly like `int` addition (Puzzle 4, verified: three additions of 1,000,000,000 give `-1294967296`) |
| `Collectors.averagingDouble` / Kahan summation | 8 | `averagingDouble`/`summingDouble` accumulate into a 3- or 4-slot `double[]` carrying a compensation term, canceling floating-point rounding error across the running sum | A naive `double` accumulator — loses precision silently on large sequences of small values | None specific to 21; the Kahan-summation shape has been stable since introduction |
| `ForkJoinPool.commonPool()` width | 8 | Default parallelism is `availableProcessors() - 1`; the thread that *submits* the terminal operation also executes work, so it participates as an extra worker | A dedicated custom pool — wins when the calling thread must not be blocked doing pool work | Stating only "`parallelism - 1`" without the submitter-participates half is the single most common wrong answer to "how wide is the common pool"; the effective width equals the core count |
| `AbstractTask.LEAF_TARGET` / `suggestTargetSize` | 8 | `LEAF_TARGET = commonPoolParallelism << 2` (four leaf tasks per core, for load balancing); `suggestTargetSize` does floored integer division of the size estimate by that target, floored to a minimum of 1 | Manual chunk sizing — loses because it hardcodes a split width that does not track the pool actually running the task | `suggestTargetSize` is **floored**, not rounded up, and `getLeafTarget()` reads the *current* `ForkJoinWorkerThread`'s pool, not always the common pool — submitting into a custom pool changes the leaf width |
| Virtual threads | 21 | `Thread.ofVirtual()` creates a `VirtualThread` scheduled onto a small `ForkJoinPool` of platform-thread "carriers"; a blocking call unmounts the virtual thread from its carrier instead of blocking the OS thread | Platform threads / a bounded thread pool — still wins for CPU-bound work, where virtual threads add scheduling overhead with no I/O to hide | "The scheduler always caps at 256 threads" — false; `maxPoolSize` defaults to `Integer.max(availableProcessors(), 256)`, a **floor**, not a flat ceiling — on a >256-core box it equals the core count |
| Virtual-thread scheduler tunables | 21 | Three system properties, not one: `jdk.virtualThreadScheduler.parallelism` (default `availableProcessors()`), `.maxPoolSize` (default `max(parallelism, 256)`), `.minRunnable` (default `max(parallelism / 2, 1)`) | N/A | Setting `maxPoolSize` below the processor count also clamps `parallelism` down to it — one property silently moves two numbers |
| Virtual-thread pinning | 21 (removed 24) | `synchronized` pins the carrier because the JVM cannot suspend a monitor-held continuation; native/foreign frames pin regardless of version | `ReentrantLock` — wins on 21 specifically because it does not pin; the win is temporary | JEP 491 makes object monitors continuation-aware from **Java 24**, removing the `synchronized` cause; the `jdk.VirtualThreadPinned` JFR event still fires for native-frame pinning on every version, so "use `ReentrantLock`" is a version-scoped answer, not a permanent rule |
| Structured concurrency | 21 preview → 25 stable (JEP 505) | `StructuredTaskScope` ties the lifetimes of forked subtasks to a single owning thread inside try-with-resources; `fork` returns `Subtask<T>`, not `Future<T>` | Manually managed `ExecutorService` + `Future` — loses the enforced parent/child lifetime, the reason cancellation and error propagation are reliable here | Java 21: public constructors, `ShutdownOnFailure`/`ShutdownOnSuccess` policies, package moved from `jdk.incubator.concurrent` to `java.util.concurrent`, needs `--enable-preview`. Java 25: constructors replaced by static `open()` factories, policies replaced by a composable `Joiner` — do not describe 21's shape as final |
| `BigDecimal` equality | 8 (behaviour stable) | `equals` compares value **and** scale; `compareTo` compares value only | `compareTo` — wins whenever the comparison is numeric, e.g. deduplicating ledger amounts | `0.33` and `0.330` are `!equals` but `compareTo == 0`; putting both into a `HashSet<BigDecimal>` keeps two entries because `HashSet` uses `equals`/`hashCode` (Puzzle 5) |

That is sixteen rows across `var`/LVTI, records, sealed types, pattern matching, text blocks,
streams, collectors, `ForkJoinPool` internals, virtual threads, structured concurrency, and
`BigDecimal` semantics — every subject folder Part 1 touches. Where a row's mechanism needed a
source quote to state honestly rather than from memory, that quote and its file/line context live
in the subject file that owns the concept; this table exists to let you see the whole tier at once
and to be the thing you re-read the morning of the interview.

---

## Interview Q&As

**Q1. "Streams are lazy" — what does that actually mean, mechanically?**

Each intermediate operation you chain — `filter`, `map`, `sorted` — doesn't do any work when you
call it. It allocates one pipeline stage object that wraps a reference to the previous stage and
records what it needs to do, contributing what the JDK internally calls an `opWrapSink`. Nothing
touches the source data at that point. The moment you call a terminal operation — `collect`,
`forEach`, `count` — the pipeline's `evaluate` method walks the chain of stages *backwards* from
the terminal one, building up a chain of `Sink` objects via `wrapSink`, and only then calls
`copyInto` to pull elements from the source spliterator and push them through that sink chain one
element at a time. That's why a stream you build and never terminate — say you call
`.filter(reservation -> reservation.amount().compareTo(BigDecimal.ZERO) > 0)` on a list of stake
reservations and never call anything after it — does absolutely nothing; there's no work
scheduled, only a description of work. It also explains why a `peek()` call you use for "debug
logging" can appear to do nothing: if there's no terminal operation downstream that needs its
elements, or if a later stage short-circuits before reaching it, the `peek` sink is never invoked
for those elements.

**Q2. Why can't a record's compact constructor assign to a component field directly?**

Because every component of a record is a `final` field — that's part of what "record" means, not
an implementation detail. Inside a compact constructor (the `StakeSplit { ... }` form with no
parameter list) you're allowed to validate and transform the incoming values, but the names you
see in scope there are the *constructor parameters*, shadowing the fields of the same name. If you
write `this.bonusPortion = bonusPortion.setScale(2);`, the compiler rejects it with "cannot assign
a value to final variable bonusPortion" — not because the syntax is illegal, but because that
field genuinely cannot be reassigned from user code. The correct pattern is to reassign the
*parameter* — `bonusPortion = bonusPortion.setScale(2);` — and let the compiler emit the field
assignment for you at the end of the compact constructor, the same way it does for the canonical
constructor. I checked this by compiling it: the diagnostic is exactly "cannot assign a value to
final variable bonusPortion", which is the tell that this is a `final`-field rule, not a
record-specific restriction.

**Q3. What's actually different about virtual threads under the hood — not the pitch, the mechanism?**

A virtual thread is a `java.lang.Thread` whose carrier is not a fixed OS thread but a worker
picked from a small `ForkJoinPool`, created by `VirtualThread.createDefaultScheduler()`. When
virtual-thread code makes a blocking call that the JDK has taught to cooperate — `Thread.sleep`,
blocking I/O on `java.io`/`java.net`, `ReentrantLock.lock()` — the runtime unmounts the virtual
thread from its carrier and parks it as a continuation, freeing the carrier to run other virtual
threads. It remounts on any available carrier when the blocking operation completes; there's no
guarantee it comes back on the same carrier, which matters for anyone reasoning about
thread-local-heavy code. The scheduler is constructed with `asyncMode = true`, and the JDK's own
source comment on that line reads `// FIFO` — that's the actual evidence for "virtual thread
scheduling is FIFO", not a inference from behavior. Parallelism defaults to
`availableProcessors()`; `maxPoolSize` defaults to `Integer.max(parallelism, 256)`, which is a
floor — most write-ups say "256 carrier threads" as if it were fixed, but on a machine with more
than 256 cores it equals the core count, not 256.

**Q4. Give me the honest version of "the common pool has parallelism minus one threads."**

That statement is half right and it's the half most people stop at. `ForkJoinPool.commonPool()`'s
default parallelism is indeed `Runtime.getRuntime().availableProcessors() - 1`. But the thread that
*submits* work into the common pool — say, the thread that calls
`stakeReservations.parallelStream().collect(...)` — doesn't just wait for the pool; it participates
as a worker on the very task graph it submitted, because `ForkJoinTask.invoke` on the calling
thread runs the task's `compute()` directly if it's not already inside the pool. So the effective
number of threads doing work is `parallelism` (the pool's own workers) *plus* the submitter, which
equals `availableProcessors()`. On an 8-core box that's common-pool parallelism 7, plus the
submitting thread, for an effective width of 8 — exactly the core count. Answering with only
"cores minus one" is the version of this that loses points, because it implies the machine is
under-utilized by one thread, which isn't true in the common case of a single submitter.

**Q5. Walk me through what happens if I call a terminal operation on a stream twice.**

`AbstractPipeline` tracks a `linkedOrConsumed` flag on the pipeline. Every public entry point that
starts evaluation — `collect`, `forEach`, `count`, building a `Spliterator`, and so on — checks
that flag first, before it ever touches the underlying source. If it's already set, it throws
`IllegalStateException` with the message "stream has already been operated upon or closed". That's
the exception you'll see in practice essentially always. There's a second message,
"source already consumed or closed", guarding a narrower internal case: it fires only from the
`else` branch of the pipeline's spliterator-acquisition methods, reached when both the stage's
`sourceSpliterator` and `sourceSupplier` fields are already null — meaning the source itself has
already been physically handed out to something. Because the `linkedOrConsumed` check runs first
on every public path, you cannot actually reach that second message through ordinary reuse; it
guards an internal double-take on the source object, not a user calling a terminal method twice. I
verified this by trying five different reproductions on a running JVM: calling two terminal
operations always gave the first message; nothing I tried reached the second.

**Q6. Why does `Collectors.summingInt` overflow but `averagingInt` doesn't?**

They accumulate into different-shaped internal arrays. `summingInt`'s accumulator is a plain
`new int[1]` — the running sum lives in an actual `int` slot and adds with ordinary `int`
arithmetic, wraparound included. `averagingInt`, by contrast, accumulates into a `new long[2]` —
one slot for the sum, one for the count — specifically so the sum doesn't overflow before the
final division produces the average. So if you sum card-deposit amounts of a billion each three
times over with `summingInt`, you get `-1294967296`, the same wraparound you'd get from adding
three `int`s directly; `summingLong` on the same data correctly gives `3000000000`. The rule people
misremember is "the summing collectors use a wide accumulator so they can't overflow" — that's only
true of the averaging collectors. `IntStream.sum()` has the identical overflow behaviour as
`summingInt`, for the identical reason: it's summing into an `int`.

**Q7. What actually changed with pattern-matching `switch` on Java 21 versus earlier?**

Two separate things landed. First, `switch` gained the ability to pattern-match — you can write
`case DocumentVerdict dv when dv.outcome() == Outcome.REJECTED ->` and bind `dv` in that branch,
including guarded patterns with `when`, and this composes with sealed types so the compiler can
prove exhaustiveness against the `permits` list without a `default`. Second, and this is the trap
people get backwards: an exhaustive `switch` *expression* over a plain `enum` has always compiled
a hidden synthetic default branch, since Java 14 introduced switch expressions — it has to, because
someone could recompile just the enum, add a constant, and hand your already-compiled `switch`
class file a value it never accounted for. What changed at 21 is *what that synthetic branch
throws*: `IncompatibleClassChangeError` through Java 20, `java.lang.MatchException` starting Java
21. I compiled and ran this exact scenario — compile an enum plus a switch that covers every
current constant, then add a constant and recompile only the enum, then run the old switch class
against it — and on `--release 21` you get `MatchException`, constructed with the `(String,
Throwable)` constructor, which is visible directly in the `javap -c` bytecode as an
`invokespecial` on that constructor.

**Q8. When would you reach for `var`, and when is it actually a readability regression?**

The OpenJDK style guide's own principles are the right frame: reading code matters more than
writing it, and readability shouldn't depend on an IDE showing you the inferred type in a gutter
tooltip. `var` earns its place when the initializer already tells you the type — `var stakeSplit =
new StakeSplit(bonusPortion, cashPortion);` — or when it breaks up a chain of nested generic
expressions into named intermediate steps, which the guide calls out explicitly as guideline G4.
It's a regression when the initializer is a method call whose return type isn't obvious from the
name — `var result = paymentService.process(intent);` tells the reader nothing about what `result`
is — or with numeric literals, where `var timeoutSeconds = 30;` hides whether that's an `int`, a
`long`, or something that should have been a `Duration`. The guide frames explicit types as a
tradeoff, not a default to avoid: you're trading a small amount of writing effort for a a real gain
in local reasoning, and `var` should only win that trade when the initializer already pays that
cost for you.

**Q9. `BigDecimal`, `equals`, and `HashSet` — where's the classic mistake?**

`BigDecimal.equals` compares both the unscaled value *and* the scale, while `compareTo` compares
only numeric value. `new BigDecimal("0.33")` and `new BigDecimal("0.330")` represent the same
number but different scale (2 versus 3 digits after the decimal point), so `equals` returns
`false` even though `compareTo` returns `0`. That bites hardest in a `HashSet<BigDecimal>` or as a
`HashMap<BigDecimal, ...>` key, because both of those use `equals`/`hashCode`, not `compareTo` —
put both of those values into a `HashSet<BigDecimal>` used to de-duplicate ledger amounts and you
get two entries, not one, silently. The fix is either to normalize scale before you compare or
store (`TreeSet`/`TreeMap`, which use `compareTo`), or to explicitly call `.stripTrailingZeros()`
or `.setScale(n, RoundingMode...)` before putting a `BigDecimal` into a hash-based collection. This
matters concretely in this domain because the canonical rounding rule — bonus portion rounds down
to the minor unit, so a stake of 3.33 splits into 0.33 bonus and 3.00 cash — routinely produces
`BigDecimal` values arriving at different scales from different code paths (one path builds `"0.33"`
directly, another computes and gets `"0.330"` from an intermediate multiplication), so this isn't a
contrived example.

**Q10. Structured concurrency — what's the elevator pitch, and what specifically is preview versus stable?**

The pitch: instead of an `ExecutorService` where forked tasks can outlive the method that submitted
them, `StructuredTaskScope` ties every forked subtask's lifetime to a single owning thread's
try-with-resources block. You fork subtasks — say, one to verify a client's identity document and
one to run a screening check in parallel before activation — and the scope guarantees that by the
time `close()` returns, either both have completed, been cancelled, or the scope itself has thrown;
nothing is left running in the background after the method returns, and cancellation/error
propagation is automatic instead of something you wire by hand. On Java 21, this is a *preview*
feature (JEP 453) — it needs `--enable-preview`, it lives in `java.util.concurrent` (moved there
from the earlier incubator package `jdk.incubator.concurrent`), you construct scopes with public
constructors, `fork` returns a `Subtask<T>` rather than a `Future<T>`, and you pick a policy —
`ShutdownOnFailure` or `ShutdownOnSuccess` — up front. Java 25 (JEP 505) changed the shape again:
public constructors are gone in favor of static `open()` factory methods, and the two named
policies are replaced by a composable `Joiner` interface. If you're asked about this for a role
running Java 21 in production, describe the 21 preview shape and say explicitly that it's preview
and that the shape changed again by 25 — don't present either shape as the final, permanent API.

---

## Predict-the-output puzzles

Every snippet below was compiled with `javac --release 21` and run with `java` on this machine.
Output shown is the real output, not recalled.

### Puzzle 1 — reusing a stream

```java
import java.util.List;
import java.util.stream.Stream;

public class StakeTotals {
    public static void main(String[] args) {
        List<Double> stakeAmounts = List.of(4.20, 3.33, 65.00);
        Stream<Double> stakes = stakeAmounts.stream();
        double total = stakes.mapToDouble(Double::doubleValue).sum();
        System.out.println("total=" + total);
        long count = stakes.count();
        System.out.println("count=" + count);
    }
}
```

**Output:**

```
total=72.53
Exception in thread "main" java.lang.IllegalStateException: stream has already been operated upon or closed
	at java.base/java.util.stream.AbstractPipeline.evaluate(AbstractPipeline.java:260)
	at java.base/java.util.stream.ReferencePipeline.count(ReferencePipeline.java:750)
	at StakeTotals.main(StakeTotals.java:10)
```

**Why:** `stakes.mapToDouble(...).sum()` is a full terminal evaluation of the pipeline rooted at
`stakes` — `mapToDouble` builds a new stage on top of it, and `sum()` on that `IntStream`/`DoubleStream`
drives evaluation back through the whole chain, which sets `linkedOrConsumed` on the original
`stakes` pipeline. The first `println` runs fine because the sum completed before the flag mattered
to anything else. The second statement calls `stakes.count()` directly on the *original* stream
object, and `count()` is one of the public entry points that checks `linkedOrConsumed` before doing
anything — it finds the flag already set and throws immediately, without ever touching the
`List.of(...)` source. Building a fresh stream — `stakeAmounts.stream().count()` — would work fine;
the mistake is treating the `Stream<Double>` reference `stakes` as reusable plumbing rather than a
one-shot description of a single traversal.

### Puzzle 2 — assigning inside a record's compact constructor

```java
import java.math.BigDecimal;

public class StakeSplitDemo {
    record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion) {
        StakeSplit {
            this.bonusPortion = bonusPortion.setScale(2);
        }
    }

    public static void main(String[] args) {
        StakeSplit split = new StakeSplit(new BigDecimal("0.33"), new BigDecimal("3.00"));
        System.out.println(split);
    }
}
```

**Output (compile-time, not runtime):**

```
StakeSplitDemo.java:6: error: cannot assign a value to final variable bonusPortion
            this.bonusPortion = bonusPortion.setScale(2);
                ^
1 error
```

**Why:** every component of a record is a `final` field, generated by the compiler from the record
header. Inside the compact constructor, `bonusPortion` in scope refers to the constructor
*parameter*, but qualifying it with `this.` reaches for the *field*, and that field cannot be
assigned by user code — only the compiler-generated implicit assignment at the end of the compact
constructor is allowed to write it. The fix is to drop `this.` and reassign the parameter:
`bonusPortion = bonusPortion.setScale(2);` — the compiler then emits `this.bonusPortion =
bonusPortion;` for you once the compact constructor body finishes, using the now-rescaled value.
This is a compile-time puzzle, not a runtime one, which is itself worth noticing: the mistake never
reaches a running JVM.

### Puzzle 3 — recompiling only the enum under an exhaustive switch

```java
// BonusStatus.java, compiled first
public enum BonusStatus { GRANTED, ACTIVE, CONSUMED, EXPIRED }
```

```java
// BonusLabel.java, compiled against the four-constant enum above
public class BonusLabel {
    public static void main(String[] args) {
        BonusStatus status = BonusStatus.valueOf(args[0]);
        String label = switch (status) {
            case GRANTED -> "grant recorded";
            case ACTIVE -> "stakeable now";
            case CONSUMED -> "fully spent";
            case EXPIRED -> "reversed to PROMOTIONAL_EXPENSE";
        };
        System.out.println(label);
    }
}
```

Then, without touching `BonusLabel.java`, `BonusStatus.java` is changed to add a fifth constant
and recompiled by itself:

```java
public enum BonusStatus { GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK }
```

Running `java BonusLabel CLAWED_BACK` against the old `BonusLabel.class` and the new
`BonusStatus.class`:

**Output:**

```
Exception in thread "main" java.lang.MatchException
	at BonusLabel.main(BonusLabel.java:4)
```

**Why:** `switch` expressions over enums have always compiled a synthetic default branch, because
the compiler cannot prove at compile time that the enum won't gain a constant before the switch is
next run — separate compilation units mean the two class files can drift apart. `BonusLabel.class`
was compiled when `BonusStatus` had exactly four constants and its switch covered all four, so
javac didn't need to warn about missing cases, but it still emitted the hidden default for safety.
When `CLAWED_BACK` is added to the enum and only the enum is recompiled, the old switch's case
labels (which are integer ordinal comparisons under the hood) don't match the new constant's
ordinal, so control falls into that synthetic default — which on Java 21 throws
`java.lang.MatchException` via its `(String, Throwable)` constructor. On Java 20 and earlier the
same scenario throws `IncompatibleClassChangeError` instead; the synthetic branch itself isn't new
at 21, only the exception type it throws.

### Puzzle 4 — `summingInt` versus `summingLong` over large values

```java
import java.util.List;
import java.util.stream.Collectors;

public class DepositTotals {
    public static void main(String[] args) {
        List<Integer> cardDeposits = List.of(1_000_000_000, 1_000_000_000, 1_000_000_000);
        int sumInt = cardDeposits.stream().collect(Collectors.summingInt(Integer::intValue));
        long sumLong = cardDeposits.stream().collect(Collectors.summingLong(Integer::longValue));
        System.out.println("summingInt : " + sumInt);
        System.out.println("summingLong: " + sumLong);
    }
}
```

**Output:**

```
summingInt : -1294967296
summingLong: 3000000000
```

**Why:** `Collectors.summingInt`'s accumulator is a `new int[1]` — the running total is a genuine
`int` and each addition wraps exactly like any other `int` arithmetic. Three billion doesn't fit in
a 32-bit signed `int` (max ~2.147 billion), so the third addition overflows and the two's-complement
result is `-1294967296`. `summingLong`'s accumulator is a `new long[1]`, which holds three billion
without any trouble. This is exactly the same failure mode as summing an `IntStream` directly with
`.sum()` — the "summing collectors use a wide accumulator" belief is true only of `averagingInt` and
`averagingLong`, whose accumulator is a `long[2]` (sum, count) specifically to keep the sum from
overflowing before the division that produces the average.

### Puzzle 5 — `BigDecimal` in a `HashSet`

```java
import java.math.BigDecimal;
import java.util.HashSet;
import java.util.Set;

public class LedgerDedupe {
    public static void main(String[] args) {
        BigDecimal bonusPortion = new BigDecimal("0.33");
        BigDecimal reloaded = new BigDecimal("0.330");
        System.out.println("equals     : " + bonusPortion.equals(reloaded));
        System.out.println("compareTo0 : " + (bonusPortion.compareTo(reloaded) == 0));

        Set<BigDecimal> ledgerAmounts = new HashSet<>();
        ledgerAmounts.add(bonusPortion);
        ledgerAmounts.add(reloaded);
        System.out.println("set size   : " + ledgerAmounts.size());
    }
}
```

**Output:**

```
equals     : false
compareTo0 : true
set size   : 2
```

**Why:** `BigDecimal.equals` treats value *and* scale as part of identity — `"0.33"` is
`unscaledValue=33, scale=2`, `"0.330"` is `unscaledValue=330, scale=3`; different unscaled
value/scale pairs make `equals` return `false` even though they represent the identical number,
which is exactly what `compareTo` measures instead. `HashSet` de-duplicates using `hashCode`/
`equals`, not `compareTo`, and `BigDecimal.hashCode` is derived from the same unscaled-value/scale
pair, so the two values hash differently and both survive as distinct set entries — hence a set
size of 2 for what looks like one ledger amount typed two different ways. Using a `TreeSet<>` in
place of `HashSet<>` here would collapse them to one entry, because `TreeSet` orders and
de-duplicates via `compareTo`.

---

## Pitfalls

### Treating a `Stream` reference as reusable plumbing

**Wrong**

```java
Stream<Double> stakes = stakeAmounts.stream();
double total = stakes.mapToDouble(Double::doubleValue).sum();
long count = stakes.count(); // throws
```

**Right**

```java
double total = stakeAmounts.stream().mapToDouble(Double::doubleValue).sum();
long count = stakeAmounts.stream().count(); // fresh pipeline
```

**Why people believe it:** a `List` reference is reusable for as many operations as you like, and
streams read like a fluent extension of the same collection API, so it's natural to assume the
intermediate `Stream<Double> stakes` variable behaves the same way. It doesn't — a stream models a
single traversal, not a reusable view, and the JDK enforces that with `linkedOrConsumed` rather than
silently letting a second traversal produce wrong answers.

### Assuming `summingInt` can't overflow because "the summing collectors are safe"

**Wrong**

```java
int totalDeposits = cardDeposits.stream()
        .collect(Collectors.summingInt(Integer::intValue)); // silently wraps
```

**Right**

```java
long totalDeposits = cardDeposits.stream()
        .collect(Collectors.summingLong(Integer::longValue));
```

**Why people believe it:** `averagingInt` really does use a wide `long[2]` accumulator, and people
generalize that fact to every `Collectors.*ing*` method without checking that `summingInt` and
`summingLong` are two genuinely different collectors with two genuinely different accumulator
widths — the "averaging" and "summing" family names look parallel but aren't implemented in
parallel.

### Believing the synthetic-default exception type is fixed across releases

**Wrong**

```
"An exhaustive enum switch's hidden default always throws IncompatibleClassChangeError."
```

**Right**

```
"It throws IncompatibleClassChangeError through Java 20, and java.lang.MatchException from
Java 21 onward — same synthetic branch, different exception type."
```

**Why people believe it:** `IncompatibleClassChangeError` was the only shape most engineers ever
saw it throw, because most production code still targets or targeted pre-21 releases when they
learned this; the throw type changing at 21 is a genuinely obscure release note that most write-ups
never revisit once they've internalized the pre-21 answer.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Stream reuse throws | `IllegalStateException: stream has already been operated upon or closed` (from `linkedOrConsumed`) |
| The rarely-seen second message | `IllegalStateException: source already consumed or closed` — internal source double-take, not user-reachable in practice |
| Enum switch synthetic default throws (≤20) | `IncompatibleClassChangeError` |
| Enum switch synthetic default throws (21+) | `java.lang.MatchException`, `(String, Throwable)` constructor |
| Record compact constructor | Reassign the **parameter**, never `this.field` — fields are `final` |
| `summingInt` accumulator | `int[1]` — overflows like plain `int` addition |
| `summingLong` accumulator | `long[1]` — safe for realistic sums |
| `averagingInt` / `averagingLong` accumulator | `long[2]` (sum, count) — safe |
| `summingDouble` / `averagingDouble` accumulator | `double[3]` / `double[4]` — Kahan compensation |
| Common pool default parallelism | `availableProcessors() - 1`, **plus** the submitting thread participates |
| `LEAF_TARGET` | `commonPoolParallelism << 2` (×4) |
| `suggestTargetSize` | Floored integer division, minimum 1 — not rounded up |
| Virtual-thread scheduler parallelism default | `availableProcessors()` |
| Virtual-thread scheduler `maxPoolSize` default | `Integer.max(parallelism, 256)` — a floor, not a flat 256 |
| Virtual-thread scheduler `minRunnable` default | `max(parallelism / 2, 1)` |
| Virtual-thread pinning cause removed at | Java 24 (JEP 491, `synchronized` only) |
| Structured concurrency preview release | 21 (JEP 453, `--enable-preview`) |
| Structured concurrency stable release | 25 (JEP 505, `open()` factories + `Joiner`) |
| `BigDecimal.equals` | Value **and** scale |
| `BigDecimal.compareTo` | Value only |
| Canonical rounding example | Stake 3.33 → 0.33 bonus (rounds down) + 3.00 cash |

---

## Self-test

**Q1.** Why does calling `.count()` a second time on a `Stream` reference throw before it ever
touches the source collection?

<details><summary>Answer</summary>

Because every public entry point on `AbstractPipeline` — `count()` included — checks the
`linkedOrConsumed` flag first, before it does anything with the source. The first terminal
operation on that pipeline (or any pipeline built on top of it) sets that flag once evaluation
starts. The second call finds the flag already set and throws
`IllegalStateException("stream has already been operated upon or closed")` immediately, without
ever asking the source for a spliterator.

</details>

**Q2.** A colleague says "records can't have custom validation logic because the fields are
final." What's wrong with that claim, and what's right about it?

<details><summary>Answer</summary>

What's right: the fields genuinely are final, generated automatically from the record header, and
you cannot assign to them directly (`this.field = ...`) inside the compact constructor. What's
wrong: validation and even transformation are fully supported — you write a compact constructor
(`StakeSplit { if (...) throw ...; bonusPortion = bonusPortion.setScale(2); }`), operating on the
constructor *parameters*, not the fields, and the compiler emits the final field assignments for
you once the compact constructor body finishes. Final fields block direct field assignment, not
validation.

</details>

**Q3.** What specifically changed about the exhaustive enum `switch` synthetic default between
Java 20 and Java 21, and what stayed the same?

<details><summary>Answer</summary>

What stayed the same: the synthetic default branch itself has existed since switch expressions
were introduced (Java 14) — it's the compiler's safety net for the case where a `switch` was
compiled against an enum that has since been recompiled with additional constants. What changed at
21: the exception type that branch throws. Through Java 20 it throws
`IncompatibleClassChangeError`; from Java 21 it throws `java.lang.MatchException`, built with the
`(String, Throwable)` constructor, visible in `javap -c` output as an `invokespecial` on that
constructor.

</details>

**Q4.** Why does `Collectors.averagingInt` not have the same overflow risk as
`Collectors.summingInt`, even though both process the same `int` values?

<details><summary>Answer</summary>

They use accumulator arrays of different widths. `summingInt` accumulates the running total into a
`new int[1]` — a genuine 32-bit `int` that wraps on overflow exactly like manual `int` addition.
`averagingInt` accumulates into a `new long[2]`, one slot for the sum and one for the count,
specifically so the running sum has 64 bits of headroom before the final division that produces
the average. So `summingInt` inherits `int`'s overflow behaviour and `averagingInt` doesn't, even
though the input elements are the same type.

</details>

**Q5.** State the full, accurate answer to "how many threads does `ForkJoinPool.commonPool()`
actually use" — the version that doesn't lose interview points.

<details><summary>Answer</summary>

Default parallelism is `Runtime.getRuntime().availableProcessors() - 1`. But the thread that
submits a task into the common pool (for example, calling `.parallelStream()...collect(...)` from
your own thread) participates in executing that task's work rather than just waiting on the pool,
because `ForkJoinTask.invoke` runs the computation directly when invoked from outside the pool. So
the effective number of threads doing work is the pool's own worker count plus the submitter,
which equals `availableProcessors()` — the full core count, not one fewer.

</details>

**Q6.** Why do two `BigDecimal` values that are numerically equal — `0.33` and `0.330` — behave
differently in a `HashSet` versus a `TreeSet`?

<details><summary>Answer</summary>

`HashSet` de-duplicates using `hashCode`/`equals`. `BigDecimal.equals` compares both the unscaled
value and the scale, so `0.33` (`unscaledValue=33, scale=2`) and `0.330`
(`unscaledValue=330, scale=3`) are `!equals`, and their `hashCode`s differ accordingly — both
survive as separate entries. `TreeSet` de-duplicates using `compareTo`, which compares numeric
value only and treats them as equal, so only one survives. The fix when de-duplication by numeric
value is intended is either to normalize scale before inserting into a hash-based collection, or to
use a `TreeSet`/`TreeMap` in the first place.

</details>

**Q7.** What is `jdk.virtualThreadScheduler.maxPoolSize`'s default, precisely — not "256"?

<details><summary>Answer</summary>

`Integer.max(parallelism, 256)`, where `parallelism` itself defaults to
`Runtime.getRuntime().availableProcessors()`. That means 256 is a floor, not a flat default: on any
machine with 256 or fewer available processors, `maxPoolSize` is exactly 256, which is where the
"256" folklore comes from — but on a machine with more than 256 available processors, `maxPoolSize`
equals the processor count instead, exceeding 256. Setting the `maxPoolSize` system property
explicitly below the processor count also clamps `parallelism` down to match it.

</details>

**Q8.** Structured concurrency on Java 21: name two specific API shapes that are different on
Java 25, and say why you shouldn't describe the 21 shape as final.

<details><summary>Answer</summary>

On Java 21 (JEP 453, preview), `StructuredTaskScope` is created with public constructors and you
choose between two named shutdown policies, `ShutdownOnFailure` and `ShutdownOnSuccess`. On Java 25
(JEP 505, stable), the constructors are replaced by static `open()` factory methods, and the two
named policies are replaced by a single composable `Joiner` interface that can express custom join
strategies. The 21 shape is explicitly a preview feature — it requires `--enable-preview` to
compile and run — and preview features are, by JEP definition, subject to change before becoming
permanent, which is exactly what happened here.

</details>

**Q9.** A reviewer flags `var timeoutSeconds = 30;` in a pull request. Is that a fair flag, and
why?

<details><summary>Answer</summary>

Yes. The OpenJDK LVTI style guide's own guideline (G7) calls out literals specifically: `var` with
a numeric literal hides useful type information the explicit form would have given — is
`timeoutSeconds` an `int`, a `long`, or should it really be a `Duration`? The initializer here
doesn't supply enough information for a reader relying on local reasoning (the guide's P2) to
recover the type without checking a declaration elsewhere or leaning on an IDE (P3), which is
exactly the case where the style guide says explicit types win the tradeoff (P4).

</details>

**Q10.** Why is "the second `IllegalStateException` message from `AbstractPipeline` almost never
seen in a stack trace" a true statement, and not just a coincidence of bad luck?

<details><summary>Answer</summary>

Because of the order the checks happen in. Every public entry point on `AbstractPipeline` checks
`linkedOrConsumed` before doing anything with the source spliterator or supplier. The second
message, `"source already consumed or closed"`, is thrown only from deeper inside spliterator
acquisition, reached solely when both `sourceSpliterator` and `sourceSupplier` are already `null` —
meaning the source has already been physically handed off once. But you can never reach that inner
code path through ordinary stream reuse, because the outer `linkedOrConsumed` check already throws
the first message before execution gets that far. The second message guards an internal invariant
about the source object itself, not a path a normal caller's mistake can reach.

</details>

---

## Deferred

None.

---

**Leaves covered:** none — part wrap-up (0 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 699
