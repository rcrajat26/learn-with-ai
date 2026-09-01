# 04 Modern Java — Part 2 wrap-up — intermediate — INTERVIEW (§2.1, §2.15)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](00-index.md)
Previous: [Part 1 wrap-up — basics — interview basics](90-interview-basics.md) · Next: [Part 3 wrap-up — internals — interview internals](92-interview-internals.md)

This file closes Part 2. It teaches nothing new — every mechanism below is taught in full in its
own subject file. What lives here is the cross-subject view: one master table over the whole
intermediate tier, the ten questions an interviewer actually asks at this depth, and five
predict-the-output puzzles whose answers were produced by running them, not recalled.

## Part 2 in one table

Part 2 took the mental models from Part 1 (basics) and asked, for each: what does it cost, which
sibling wins when, and what actually happens when the JDK's own default choices get exercised.
That is the thread running through every subject folder below.

| Subject | Intermediate file(s) | The one thing worth remembering under pressure |
|---|---|---|
| Lambdas | `lambdas/02-cost-and-choice.md` | A non-capturing lambda's call site caches its `CallSite` after the first `invokedynamic` bootstrap — first call is slow, every call after is a cached `invokeinterface`-shaped dispatch. Capturing lambdas allocate a new instance per capture; this is the fork in the road for hot-path lambda use. |
| Method references | `method-references/01-basics.md` | A method reference has no separate identity guarantee — two `this::method` references built in the same call are not `==`, because `LambdaMetafactory` mints a fresh class per call site, not per method. |
| Functional interfaces | `functional-interfaces/01-basics.md` | Counting toward "single abstract method" is about the abstract method count after `Object`'s methods are subtracted, not the method count on the page — `equals`, `hashCode`, `toString` never count. |
| Streams — intermediate ops | `streams/03-intermediate-operations.md` | Intermediate operations are lazy: each call allocates one pipeline stage wrapping the previous one; nothing traverses until a terminal operation calls `evaluate`, so a pipeline with no terminal operation runs zero of its lambdas. |
| Streams — terminal ops | `streams/04-terminal-operations.md` | `findFirst` forces encounter order even in parallel; `findAny` does not — that's the entire reason `findAny` is allowed to be faster on a parallel pipeline. |
| Streams — primitive streams | `streams/05-primitive-streams.md` | `IntStream.sum()` silently overflows on `int` accumulation — no exception, no warning, just a wrapped result. This is the same trap `Collectors.summingInt` carries (below). |
| Streams — cost model | `streams/06-cost-model.md`, `cost-model/02-master-tables.md` | Every stream operation's cost is stated as **per-element work × element count**, not as an aggregate big-O — this is what makes `filter().map()` fusion visible as "one pass, two per-element costs" instead of "two passes". |
| Streams — parallel streams | `streams/07-parallel-streams.md` | Parallel speedup requires all three of: enough elements to amortise fork/join overhead, an efficiently-splittable source (`ArrayList`/array beat `LinkedList`/`Stream.iterate`), and cheap, side-effect-free, non-blocking per-element work. Miss any one and parallel is slower than sequential. |
| Collectors — in anger | `collectors/02-in-anger.md` | `groupingBy` with no downstream collector always returns `Collectors.toList()` per group — the two-arg form is the one-arg form with an implicit third argument, not a different mechanism. |
| Optional — discipline | `optional/02-discipline.md` | `orElse(x)` evaluates `x` unconditionally, every call, whether or not the `Optional` is present — `orElseGet(supplier)` is the lazy sibling. This is a runtime cost bug, not a style nit, whenever `x` is not a bare constant. |
| Var — in practice | `var/02-in-practice.md` | `var` policy is a readability contract, not a type-safety one — the compiler still infers a real, fixed type at the declaration site; `var` never means dynamic typing. |
| Records — in practice | `records/02-in-practice.md` | A record's canonical accessor names match the component names exactly (`bonusPortion()`, not `getBonusPortion()`) — this is what breaks bean-convention tooling (some serializers, some reflection-based mappers) that hard-codes the `getX` prefix. |
| Sealed types — data-oriented programming | `sealed-types/02-data-oriented-programming.md` | A sealed interface plus exhaustive pattern-switch is the modern replacement for the visitor pattern's double-dispatch — the compiler enforces exhaustiveness at compile time instead of a runtime `accept` call enforcing it at runtime. |
| Pattern matching — in anger | `pattern-matching/02-in-anger.md` | Pattern-switch dominance is checked at compile time: a general pattern (an unguarded type pattern) before a more specific one is a compile error, not a silently-unreachable branch — this is stricter than `instanceof`-chain `if`/`else if`, which happily compiles unreachable branches. |
| Switch | `switch/01-basics.md` | The arrow form (`->`) has no fall-through by construction — there is no `break` to forget. The colon form still falls through exactly as it always did; the two forms coexist in Java 21, they are not a replacement of one by the other. |
| Text blocks — in practice | `text-blocks/02-in-practice.md` | Incidental whitespace is computed from the **closing delimiter's** indentation, not the opening one — moving the closing `"""` left or right changes every line's leading whitespace, which is the single most common text-block surprise. |
| Var + records + sealed + pattern + switch + text blocks | `which-construct/02-which-construct.md` | Cross-construct decision table: this file is the "which one do I reach for" companion to all five language-feature subjects above. |
| Virtual threads — in production | `virtual-threads/02-in-production.md` | `synchronized` pins a virtual thread to its carrier on Java 21 — JEP 491 removes that specific cause in Java 24, but native/foreign frames still pin at every release, so `ReentrantLock` advice is version-scoped, not evergreen. |
| Structured concurrency — in practice | `structured-concurrency/02-in-practice.md` | `StructuredTaskScope` is preview in Java 21 (JEP 453, needs `--enable-preview`), with public constructors and `fork` returning `Subtask<T>`, not `Future<T>`. Java 25 (JEP 505) replaces the constructors with `open()` factories and the two shutdown policies with a composable `Joiner`. |
| Platform and releases — migration | `platform-and-releases/02-migration.md` | Every JPMS-driven or reflection-driven break is tied to a specific release (strong encapsulation defaults, illegal-access warnings, removed APIs) — "it broke on upgrade" always has a named release and a named JEP behind it, never "newer Java is stricter" as a vague catch-all. |
| Library additions | `library-additions/01-basics.md` | Sequenced collections (`SequencedCollection`, `SequencedMap`, `SequencedSet`, Java 21) retrofit `getFirst`/`getLast`/`reversed()` onto existing collection types without a new collection hierarchy — `reversed()` returns a live view, not a copy. |

## The ten interview Q&As

Full model answers, spoken length — what a strong candidate actually says out loud, not a hint.

**Q1. Why is `stream().filter(...).map(...).collect(...)` one pass over the data, and what would
break that?**

Each intermediate operation — `filter`, `map` — doesn't touch any elements when you call it; it
just allocates a new pipeline stage that wraps the previous stage and remembers what to do
(`opWrapSink`). Nothing runs until you call a terminal operation like `collect`, which walks
backwards from the terminal stage, builds one nested chain of `Sink` objects — filter's sink
wraps map's sink wraps the terminal's sink — and then pulls elements from the source one at a
time through that whole chain. So a stake reservation goes through `filter`, then `map`, then
gets collected, before the next reservation starts; that's the "one pass" property, and it's why
you can chain ten intermediate operations without allocating ten intermediate lists. What breaks
it: any operation that has to see every element before it can produce the first one — `sorted()`,
`distinct()` on an unordered or infinite source, or a terminal reduction that needs the whole
input, like `collect(toList())` itself, which is one pass over the source but still has to finish
that whole pass before returning. `sorted()` in particular is a full barrier — it buffers
everything, sorts it, and only then starts feeding downstream stages.

**Q2. `IntStream.range(0, n).sum()` versus `Collectors.summingInt(...)` — which one silently
overflows, and why does `summingLong`/`averagingInt` not have the same bug?**

Both `IntStream.sum()` and `Collectors.summingInt` accumulate into a bare `int`, and neither
throws on overflow — Java integer arithmetic wraps silently by the language spec, and streams
don't add a checked-arithmetic mode on top. So summing three stake batches of a billion each in
an `int` wraps to a negative number instead of three billion. `summingLong` doesn't have the bug
because its accumulator is a `long[1]` — the type of the box changed, not the safety of the
operation. The one that surprises people is `averagingInt`: it also accumulates into a `long[2]`
(sum and count both as `long`), so it's safe even though its name pattern-matches `summingInt`.
The rule to actually remember: check the accumulator's declared width, not the collector's name.

**Q3. Why does an exhaustive pattern-switch over a sealed interface need no `default`, and what
happens if you add a new permitted subtype later without recompiling every switch?**

The compiler can prove exhaustiveness only because `permits` is a closed, compile-time-known
list — every subtype that could ever reach the switch is enumerated in the sealed interface's
declaration, so the compiler can check, case by case, that all of them are covered and refuse to
compile if one is missing. That's fundamentally different from an enum switch, where the switch
is exhaustive against the enum's constant list at compile time but the enum class file can change
independently afterwards. If you add a new permitted subtype and recompile only the sealed
interface, existing switches that were compiled against the old permits list still have a
synthetic default the compiler generated for you — and hitting that path throws
`MatchException` on Java 21 (`IncompatibleClassChangeError` before it). It's not silent data
corruption, but it is a runtime failure discovered by a code path that used to be a compile-time
guarantee, which is exactly why "add a case, recompile everything" is the release discipline for
sealed hierarchies.

**Q4. What's actually different between a virtual thread's default scheduler and a fixed
`ExecutorService` backed by a thread pool?**

The virtual-thread scheduler is a `ForkJoinPool` in FIFO mode (`asyncMode = true` — the source's
own comment on that constructor call literally says `// FIFO`), with a small number of **carrier**
platform threads, default count `Runtime.getRuntime().availableProcessors()`. Virtual threads
aren't threads the OS schedules — each one is a continuation that mounts onto a carrier to run
and unmounts at a blocking point, freeing that carrier to run a different virtual thread. A fixed
thread pool has no mount/unmount step: each submitted task owns one real OS thread for its whole
lifetime, so a blocking call just blocks that OS thread. That's the entire value proposition — you
can have tens of thousands of virtual threads blocked on I/O with only `availableProcessors()`
carriers actually consuming OS thread stacks, because blocking unmounts rather than parks a whole
platform thread. The gotcha: `synchronized` blocks and native/foreign calls pin the virtual thread
to its carrier instead of unmounting — the carrier is unavailable to anyone else until the pinned
call returns, which turns a "cheap thread" into a scarce resource again inside that pinned region.

**Q5. Why does `Optional.orElse(x)` sometimes cost you a network call you didn't want, and what's
the fix?**

`orElse` takes its argument as an already-evaluated value, not a supplier — Java evaluates method
arguments before the call happens, so `resolved.orElse(fetchFallbackClient(reason))` calls
`fetchFallbackClient` every single time this line runs, whether or not `resolved` is present. If
`fetchFallbackClient` does a lookup against `ClientAgreements` or hits a cache, you're paying that
cost on the hot path where the `Optional` is present and the fallback is thrown away immediately.
The fix is `orElseGet(() -> fetchFallbackClient(reason))`, which takes a `Supplier` and only
invokes it on the empty path. The rule of thumb that generalises: if the fallback expression is
anything other than a constant or an already-computed local variable, reach for `orElseGet`
by default and only use `orElse` when you've checked the argument is genuinely free to evaluate.

**Q6. When does a parallel stream make a stake-processing pipeline slower, not faster?**

Three conditions have to hold together for parallel to win, and losing any one flips the sign.
First, there have to be enough elements to amortise fork/join overhead — the JDK's own
`ForkJoinTask` sizing targets roughly four leaf tasks per core (`LEAF_TARGET = parallelism << 2`),
so on an 8-core box with 7-way common-pool parallelism that's 28 leaf tasks; a stream of a few
hundred stake reservations doesn't have enough work to justify that decomposition. Second, the
source has to split efficiently — an `ArrayList` or array `Spliterator` can hand off a contiguous
prefix in O(1) via `trySplit`, but a `LinkedList`- or `Stream.iterate`-backed source can only split
by walking, which serialises the very decomposition step parallel was supposed to avoid. Third,
the per-element work has to be cheap, side-effect-free and non-blocking — if each element makes a
blocking call to `CardPayments`, the common pool's limited carrier threads (worker count tied to
`availableProcessors() - 1`) get starved, and worse, if that blocking work runs on the common
pool from inside a request thread that's also using the common pool, you can deadlock the whole
pool, not just slow it down. Any one of these three failing is enough to make parallel lose to
sequential; interviewers are checking whether you know it's three independent conditions, not one
blanket "parallel is faster" belief.

**Q7. What actually happens when you call a terminal operation twice on the same stream?**

Every `AbstractPipeline` entry point checks a `linkedOrConsumed` flag before doing anything else,
and if it's already set, it throws `IllegalStateException` with the message "stream has already
been operated upon or closed" — that string, `MSG_STREAM_LINKED`, is thrown from eight call sites
covering essentially every public API surface a user could call twice. There's a second, related
message, `MSG_CONSUMED` ("source already consumed or closed"), but it guards a much narrower
internal case — a second attempt to pull the *source spliterator* out of a stage whose source has
already been handed out — and it's not reachable from ordinary double-terminal-operation code,
because `linkedOrConsumed` is always checked first and always fires before that path is reached.
So in practice, "stream has already been operated upon or closed" is the only message you will
ever see for this mistake; the design intent, straight from the API docs, is that streams model a
single traversal, not a reusable data structure — if you need to run two different terminal
operations over the same data, you re-derive two streams from the underlying collection.

**Q8. `Collectors.groupingBy(rail)` versus `Collectors.groupingBy(rail, counting())` — what's the
actual relationship, not just "one groups, one counts"?**

`groupingBy(classifier)` is not a separate implementation from the two-argument form — it's
literally implemented as `groupingBy(classifier, toList())`, meaning the single-argument overload
supplies `Collectors.toList()` as an implicit downstream collector. So grouping 95,000 card
deposits by rail with the one-argument form gives you a `Map<Rail, List<Deposit>>`, and swapping
in `groupingBy(Deposit::rail, Collectors.counting())` gives you `Map<Rail, Long>` — same
classification step, different reduction of each group's members. This composability is the whole
point of the design: any `Collector` can be the downstream, so `groupingBy(rail,
summingLong(Deposit::amountMinor))` gives total minor units per rail, and
`groupingBy(rail, mapping(Deposit::id, toSet()))` gives per-rail id sets, all from the same
mechanism. The interview trap is assuming `groupingBy` is one fixed shape of aggregation instead
of a classification step with a pluggable downstream reducer.

**Q9. Why does a record's compact constructor let you reassign a parameter but not the field
itself?**

Every component of a record desugars to a `private final` field, and the compact constructor's
body runs *before* the compiler-generated field assignments, not instead of them — so at the
point where your compact constructor body executes, the fields don't exist as assignable targets
yet in the normal sense; what you have in scope are the constructor's parameters, which shadow the
field names. When you write `bonusPortion = bonusPortion.setScale(2, DOWN);` inside the compact
constructor, you're reassigning the *parameter* to a normalized value, and the compiler then
emits `this.bonusPortion = bonusPortion;` for you at the end, using whatever value the parameter
holds at that point. If you write `this.bonusPortion = ...` explicitly, you're naming the actual
final field directly, and that's a compile error — "cannot assign a value to final variable
bonusPortion" — because the field truly is final and the compiler hasn't reached the point where
it performs its own, single, compiler-generated assignment to it yet.

**Q10. `var` and pattern-matching `instanceof` both look like they weaken type safety. Do either
of them actually do that?**

No, and the mechanism is the same reason for both: the compiler still computes and fixes a
concrete type at compile time; what changes is who writes the type token in the source, not
whether the type exists. `var clientId = accountLookup.find(id);` infers whatever
`accountLookup.find` is declared to return and locks that type in at the declaration — it is not
dynamic, and passing something of the wrong type later is still a compile error, exactly as if
you'd written the type by hand. `if (verdict instanceof ScreeningVerdict(var outcome, var
reason))` is the same story one level deeper: the compiler still checks, at compile time, that
`verdict`'s static type could possibly be a `ScreeningVerdict`, and the pattern still only binds
`outcome` and `reason` if the runtime `instanceof` test passes — there's a real bytecode check
(`instanceof` plus, since Java 21, accessor calls for the record components) backing the binding,
not a dynamic-language-style duck type. Both features move type *inference* to the compiler; they
do not move type *checking* to runtime.

## Five predict-the-output puzzles

Every snippet below was compiled with `javac --release 21` and run on this machine; the output
shown is the real output, not a recalled one.

### Puzzle 1 — `summingInt` versus `summingLong`

```java
import java.util.List;
import java.util.stream.Collectors;

public class StakeSummary {
    public static void main(String[] args) {
        List<Integer> stakes = List.of(1_000_000_000, 1_000_000_000, 1_000_000_000);
        int sumInt = stakes.stream().collect(Collectors.summingInt(Integer::intValue));
        long sumLong = stakes.stream().collect(Collectors.summingLong(Integer::longValue));
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

**Why.** `Collectors.summingInt` accumulates into a `new int[1]` slot — the running sum is a plain
`int` the whole way through. Three billion overflows a 32-bit signed `int` (max `2147483647`);
`3_000_000_000 - 2^32 = -1_294_967_296`, which is exactly the printed value — this is `[NUM]`
arithmetic, not a mystery: `2^32 = 4_294_967_296`, so `3_000_000_000 - 4_294_967_296 =
-1_294_967_296`. `summingLong` accumulates into a `new long[1]`, so the same three additions
never leave `int` range and print the true sum. Neither collector throws or warns — this is a
silent-wraparound bug, and it is the same trap `IntStream.sum()` carries, not a stream-specific
one.

### Puzzle 2 — the exhaustive enum switch's synthetic default, Java 21 shape

```java
// Bonus.java — compiled first, with three constants
public enum Bonus { GRANTED, ACTIVE, CONSUMED }
```

```java
// BonusRules.java — compiled against the three-constant Bonus above
public class BonusRules {
    static String describe(Bonus b) {
        return switch (b) {
            case GRANTED -> "grant pending";
            case ACTIVE -> "stakeable";
            case CONSUMED -> "spent";
        };
    }
}
```

Now `Bonus.java` is recompiled alone, adding a fourth constant, **without recompiling
`BonusRules.java`**:

```java
public enum Bonus { GRANTED, ACTIVE, CONSUMED, EXPIRED }
```

`BonusRules.describe(Bonus.EXPIRED)` is then called against the stale `BonusRules.class`.

**Output:**

```
Exception in thread "main" java.lang.MatchException
	at BonusRules.describe(BonusRules.java:3)
```

**Why.** The switch was exhaustive against the three-constant `Bonus` it was compiled against, so
the compiler emitted no explicit `default` — but it still emits a **synthetic** default branch,
because the switch has to handle *some* value at runtime if the enum changes underneath it. On
Java 21 that synthetic default throws `java.lang.MatchException`, constructed with the
`(String, Throwable)` constructor — confirmed in `javap -c` output as
`invokespecial ... MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V`. On Java 20
and earlier the same synthetic default threw `IncompatibleClassChangeError` instead. This is a
`[VERSION-TRAP]` the wrong way round in a lot of stale material: the exception type **changed at
21**, it did not appear at 21 — the synthetic default itself exists at every release that has
exhaustive switches over sealed types or enums.

### Puzzle 3 — a record's compact constructor and the field it cannot touch

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

public class StakeSplitDemo {
    record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion) {
        StakeSplit {
            this.bonusPortion = bonusPortion.setScale(2, RoundingMode.DOWN);
        }
    }
    public static void main(String[] args) {
        var split = new StakeSplit(new BigDecimal("0.333"), new BigDecimal("3.00"));
        System.out.println(split);
    }
}
```

**Output:**

```
StakeSplitDemo.java:8: error: cannot assign a value to final variable bonusPortion
            this.bonusPortion = bonusPortion.setScale(2, RoundingMode.DOWN);
                ^
1 error
```

**Why.** This doesn't run — it fails to compile, which is the point of the puzzle: predicting a
diagnostic is still predicting output. `bonusPortion` desugars to a `private final` field, and
inside a compact constructor the compiler hasn't performed its own field assignment yet, so
`this.bonusPortion` refers to the real, already-final field, not an assignable target. The fix is
to drop `this.` and reassign the parameter — `bonusPortion = bonusPortion.setScale(2,
RoundingMode.DOWN);` — which the compiler accepts and then uses as the value for the
field assignment it generates on your behalf.

### Puzzle 4 — a stream used twice

```java
import java.util.stream.Stream;

public class ReservationStreamDemo {
    public static void main(String[] args) {
        Stream<Integer> reservations = Stream.of(1, 2, 3);
        long count = reservations.count();
        System.out.println("count = " + count);
        double total = reservations.mapToInt(Integer::intValue).sum();
        System.out.println("total = " + total);
    }
}
```

**Output:**

```
count = 3
Exception in thread "main" java.lang.IllegalStateException: stream has already been operated upon or closed
	at java.base/java.util.stream.AbstractPipeline.<init>(AbstractPipeline.java:201)
	at java.base/java.util.stream.ReferencePipeline.mapToInt(ReferencePipeline.java:224)
	at ReservationStreamDemo.main(ReservationStreamDemo.java:8)
```

**Why.** `count()` is a terminal operation, and every `AbstractPipeline` sets `linkedOrConsumed`
once a terminal operation runs against it. Calling `mapToInt` afterwards is itself a new pipeline
stage constructor call on the same already-consumed source stage, and every stage constructor
checks that flag before doing anything else — throwing `MSG_STREAM_LINKED`, "stream has already
been operated upon or closed", the moment the second operation (intermediate *or* terminal) is
attempted. `count = 3` prints first because the first line completed and returned before the
second statement even started executing — the exception is a property of the second use of the
stream reference, not a retroactive failure of the first.

### Puzzle 5 — `Optional.orElse` and the fallback that runs anyway

```java
import java.util.Optional;

public class ClientLookupDemo {
    static String fetchFallbackClient(String reason) {
        System.out.println("looking up fallback because: " + reason);
        return "CLI-000-FALLBACK";
    }
    public static void main(String[] args) {
        Optional<String> resolved = Optional.of("CLI-482911");
        String clientId = resolved.orElse(fetchFallbackClient("resolved was empty"));
        System.out.println("clientId = " + clientId);
    }
}
```

**Output:**

```
looking up fallback because: resolved was empty
clientId = CLI-482911
```

**Why.** `orElse` is a plain instance method taking a `T`, not a `Supplier<T>` — Java evaluates
every argument expression before the call is made, with no laziness, so
`fetchFallbackClient("resolved was empty")` runs and prints unconditionally, regardless of
whether `resolved` turns out to be present. The `Optional` being present only affects which value
`orElse` *returns* (`"CLI-482911"`, the present value, wins over the already-computed fallback) —
it does not stop the fallback expression from having already executed and printed. `orElseGet(() ->
fetchFallbackClient(...))` is the only one of the pair that skips the call when the `Optional` is
present, because it defers the call behind a `Supplier` that `orElseGet` only invokes on the
empty branch.

## Pitfalls

### Assuming `Collectors.summingInt` is as safe as `averagingInt`

**Wrong**

```java
List<Integer> deposits = List.of(1_500_000_000, 1_500_000_000);
int total = deposits.stream().collect(Collectors.summingInt(Integer::intValue));
System.out.println(total); // -1294967296, not 3000000000
```

**Right**

```java
List<Integer> deposits = List.of(1_500_000_000, 1_500_000_000);
long total = deposits.stream().collect(Collectors.summingLong(Integer::longValue));
System.out.println(total); // 3000000000
```

**Why people believe it:** `averagingInt` genuinely does accumulate into a `long[2]` (sum, count)
despite its `int`-flavoured name, so people generalise "the `*Int` collectors are widened
internally" to `summingInt` too — but `summingInt`'s accumulator array is `new int[1]`, not
widened at all. The name pattern is not a reliable guide; the accumulator array's declared
element type is.

### Believing `orElse` and `orElseGet` are interchangeable style choices

**Wrong**

```java
String clientId = resolved.orElse(fetchFallbackClient("resolved was empty"));
// fetchFallbackClient always runs, even when resolved is present
```

**Right**

```java
String clientId = resolved.orElseGet(() -> fetchFallbackClient("resolved was empty"));
// fetchFallbackClient only runs on the empty path
```

**Why people believe it:** both compile, both return the right value on both branches, and in a
quick manual test with a cheap fallback the difference is invisible — it only shows up as a
measurable cost, or a visible side effect, once the fallback expression does real work (a lookup,
a log line, an allocation), which is exactly the case that doesn't show up in a five-minute
smoke test.

## Cheat sheet

| Concept | One-line fact |
|---|---|
| Stream laziness | No traversal until a terminal op calls `evaluate`; intermediate ops just link `Sink` stages. |
| Stream reuse | Any second operation on a stream that already ran a terminal op throws `IllegalStateException: stream has already been operated upon or closed`. |
| `summingInt` | Accumulates into `int[1]` — silently overflows, same trap as `IntStream.sum()`. |
| `summingLong` / `averagingInt` / `averagingLong` | Accumulate into `long[]` slots — safe from the `int`-overflow trap. |
| `groupingBy(classifier)` | Sugar for `groupingBy(classifier, toList())` — always has an implicit downstream collector. |
| `orElse(x)` | `x` evaluated unconditionally, every call. |
| `orElseGet(supplier)` | Supplier invoked only on the empty path. |
| Exhaustive enum/sealed switch | No explicit `default` needed; compiler emits a synthetic one. Throws `MatchException` on Java 21, `IncompatibleClassChangeError` before it. |
| Record compact constructor | Reassign the parameter, never `this.field` — the field is still final at that point. |
| Parallel stream wins when | Enough elements to amortise fork/join, an efficiently-splittable source, cheap non-blocking per-element work — all three, not any one. |
| Common-pool effective width | `availableProcessors() - 1` workers, plus the submitting thread participates — effective width equals core count. |
| Virtual-thread scheduler | `ForkJoinPool`, FIFO (`asyncMode = true`), default parallelism = `availableProcessors()`, `maxPoolSize = max(parallelism, 256)`. |
| `synchronized` pinning | Pins a virtual thread's carrier on Java 21; JEP 491 removes that cause in Java 24. Native/foreign frames still pin at every release. |
| `var` | Compile-time type inference, fixed at declaration — never dynamic typing. |
| Record accessor naming | Matches the component name exactly (`bonusPortion()`), never a `getX` bean prefix. |
| Text block indentation | Computed from the closing `"""`'s column, not the opening one. |
| `StructuredTaskScope` on 21 | Preview (JEP 453), needs `--enable-preview`, public constructors, `fork` returns `Subtask<T>`. |
| Sequenced collections | `getFirst`/`getLast`/`reversed()` retrofit onto existing types (Java 21); `reversed()` is a live view, not a copy. |

## Self-test

**Q1.** Why does `Collectors.summingInt` overflow while `Collectors.averagingInt` does not, even
though both have "Int" in the name?

<details><summary>Answer</summary>

`summingInt`'s accumulator is a bare `new int[1]` — the running sum never leaves 32-bit `int`
range, so it wraps silently on overflow, exactly like `IntStream.sum()`. `averagingInt`'s
accumulator is a `new long[2]` holding sum and count as `long` values, so despite the name it
never overflows in the same way. The collector's name is not a reliable signal; the declared
width of its accumulator array is.

</details>

**Q2.** A stream pipeline has three `.filter()` calls and a `.map()` call but no terminal
operation. How many of those four lambdas run, and why?

<details><summary>Answer</summary>

Zero. Each intermediate operation only allocates a pipeline stage and records what it would do —
it doesn't touch a single element. Traversal only starts when a terminal operation calls
`evaluate(TerminalOp)`, which walks the stage chain backwards from the terminal stage to build a
`Sink` chain and only then pulls elements from the source through it. No terminal operation means
`evaluate` is never called, so none of the lambdas ever execute.

</details>

**Q3.** What's the practical difference between `Stream.findFirst()` and `Stream.findAny()` on a
parallel stream, and why does that difference exist?

<details><summary>Answer</summary>

`findFirst` is required to honor encounter order even when the pipeline is running in parallel —
it has to identify which of the matching elements is actually first in the source's ordering,
which forces coordination across the parallel tasks. `findAny` drops that requirement: any
matching element is an acceptable answer, so whichever parallel task finds one first can return
immediately without waiting to confirm it's the earliest. That relaxation is the entire reason
`findAny` exists as a separate method — it trades a specific guarantee for the ability to short-
circuit faster under parallel execution.

</details>

**Q4.** Why does `groupingBy(Deposit::rail)` return `Map<Rail, List<Deposit>>` while
`groupingBy(Deposit::rail, counting())` returns `Map<Rail, Long>`, and what does that tell you
about how `groupingBy` is implemented?

<details><summary>Answer</summary>

The single-argument `groupingBy(classifier)` overload is implemented as
`groupingBy(classifier, toList())` — it supplies `Collectors.toList()` as the downstream
collector implicitly. Swapping in `counting()` as an explicit downstream collector changes only
what happens to each group's members, not the classification step itself. This tells you
`groupingBy` is fundamentally a two-part mechanism — classify, then reduce each group with a
pluggable `Collector` — and the one-argument form is a convenience default, not a different code
path.

</details>

**Q5.** On Java 21, what exception type does an exhaustive `switch` expression over a sealed
interface throw if a new permitted subtype is added and only that subtype (not the switch) is
recompiled, and what did the same situation throw before Java 21?

<details><summary>Answer</summary>

`java.lang.MatchException`, constructed via the `(String, Throwable)` constructor, confirmed by
the `invokespecial` instruction targeting that constructor in the compiled switch's bytecode.
Before Java 21, the same synthetic default branch threw `IncompatibleClassChangeError`. The
synthetic default itself exists at every release with exhaustive switches over closed type sets —
what changed at 21 is only which exception type it throws.

</details>

**Q6.** Why is `Optional.orElse(expensiveCall())` a performance smell even in the case where the
`Optional` is always present in production?

<details><summary>Answer</summary>

`orElse` takes an already-evaluated `T`, not a `Supplier<T>` — Java evaluates method arguments
before making the call, so `expensiveCall()` runs on every invocation regardless of whether the
`Optional` turns out to be present. If the `Optional` is always present in practice, every one of
those calls computes a value that is immediately discarded, which is pure wasted work.
`orElseGet(() -> expensiveCall())` defers the call behind a lambda that only runs on the empty
path, eliminating the wasted work entirely.

</details>

**Q7.** What are the three conditions that all have to hold for a parallel stream to actually
outperform its sequential equivalent, using the stake-reservation pipeline as the example?

<details><summary>Answer</summary>

First, there must be enough elements to amortise the fork/join decomposition and combine overhead
— a small collection isn't worth splitting. Second, the source must split efficiently: an
`ArrayList` or array backing lets `trySplit` hand off contiguous prefixes in O(1), while a
`LinkedList` or `Stream.iterate` source can only split by walking, which serialises the very step
parallelism was meant to avoid. Third, the per-element work must be cheap, side-effect-free, and
non-blocking — blocking calls (say, to `CardPayments`) can starve the common pool's limited
carrier threads and, in the worst case, deadlock a pool that's shared with the submitting code.
Missing any single one of the three is enough to make parallel slower than sequential.

</details>

**Q8.** Why does calling a second operation — terminal or intermediate — on a `Stream` after a
terminal operation has already run throw `IllegalStateException`, and what's the exact message?

<details><summary>Answer</summary>

The message is "stream has already been operated upon or closed" (`MSG_STREAM_LINKED`). Every
`AbstractPipeline` sets a `linkedOrConsumed` flag once any terminal operation runs against it, and
every subsequent pipeline-stage constructor or terminal-operation entry point checks that flag
before doing any work — throwing immediately if it's already set. This is by design: a `Stream`
models exactly one traversal, not a reusable data structure, so a second operation on the same
stream reference is always a programming error, never a supported reuse pattern.

</details>

**Q9.** Inside a record's compact constructor, why does `bonusPortion = bonusPortion.setScale(2,
RoundingMode.DOWN);` compile but `this.bonusPortion = bonusPortion.setScale(2,
RoundingMode.DOWN);` does not?

<details><summary>Answer</summary>

Every record component desugars to a `private final` field, and the compact constructor's body
runs before the compiler's own generated field assignments — so at that point in the code, the
field genuinely has not been assigned yet and is still an unassigned final variable as far as the
compiler's flow analysis is concerned for `this.field` access, but the *parameter* named
`bonusPortion` is in scope and freely reassignable within the constructor body. Reassigning the
parameter and letting the compiler's generated `this.bonusPortion = bonusPortion;` pick up the
new value is the only path the compact-constructor design permits; naming the field directly via
`this.` is rejected because it's a direct assignment to a final field.

</details>

**Q10.** Why does `synchronized` pinning a virtual thread matter less on Java 24 than on Java 21,
and what still pins on both?

<details><summary>Answer</summary>

JEP 491 makes object monitors ("`synchronized`") continuation-aware starting in Java 24, meaning a
virtual thread blocked inside a `synchronized` block can unmount its carrier instead of pinning it
— removing the single most common cause of pinning in ordinary application code. What still pins
on every release, 21 through 24 and beyond, is any native call or foreign-function frame on the
virtual thread's stack, because the continuation mechanism can't safely unmount through native
stack frames. That's why "use `ReentrantLock` instead of `synchronized`" is correct, current
advice for Java 21 specifically, and becomes unnecessary — though still harmless — from Java 24
onward for the monitor case, while it remains true forever for the native-frame case.

</details>

## Deferred

None.

---

**Leaves covered:** none — part wrap-up (0 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 620
