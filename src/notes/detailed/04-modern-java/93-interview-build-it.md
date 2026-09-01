# 04 Modern Java — Part 4 wrap-up — build it — INTERVIEW (§4.1, §4.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](00-index.md)
Previous: [Part 3 wrap-up — internals — interview internals](92-interview-internals.md) · Next: [The 95 questions, part A — interview questions a](94-interview-questions-a.md)

This file closes Part 4. It owns no syllabus leaves of its own — it is the checkpoint that sits
after every "build it yourself" file in `build-it/` and before Part 5's question bank begins.
Three things live here and nowhere else in Part 4: the summary table over all seven builds, ten
speaking-length interview Q&As, and five predict-the-output puzzles, each one actually compiled
and run on this machine with `javac --release 21` / `java` rather than recalled.

Part 4's premise is different from Parts 1–3. Those tiers teach the JDK's own machinery — you read
`AbstractPipeline`, you read `Collectors`, you read `VirtualThread`. Part 4 asks you to *become*
the JDK for an afternoon: build a lazy, fused stream; build a collector that satisfies the same
five-function contract `java.util.stream.Collector` does; build a record by hand and feel exactly
where the boilerplate the compiler now writes for you used to live. The reason this is worth doing
for an interview loop, and not merely a fun weekend exercise, is that every "why does the JDK do
it that way" question resolves instantly once you have hit the same wall yourself — you cannot be
surprised that `Collector` needs a `combiner` if you tried to write `toList()` without one and
watched parallel collection silently drop half the input. Every item built across `build-it/01`
through `build-it/07` is tagged `[BUILD]`: complete, compiling, generic Java 21, each one closing
with a "diff vs the real one" table that names what the toy version knowingly leaves out —
intrinsics, serialization, null policy, thread safety, allocation tricks — and *why the JDK
bothers* with the parts a toy build skips.

---

## Summary table — every build in Part 4

| § | Build | What it forces you to confront | The JDK's real answer | Sharpest diff |
|---|---|---|---|---|
| 4.1 | A functional toolkit from scratch (`MyFunction`, `MyPredicate`, `CheckedFunction`, `Result<T,E>`, a memoising decorator, curry/partial, `TriFunction`) | Checked exceptions do not compose through `java.util.function.Function`'s `apply`, which declares no `throws` clause | `CheckedFunction<T,R,E extends Exception>` with an `unchecked()`/`sneaky()` adapter mirrors what libraries like Vavr and project-internal wrappers do; the JDK itself never shipped one | The JDK's `Function` composition (`andThen`/`compose`) allocates one wrapper lambda per link and is not memoised; a hand-rolled memoising decorator over `ConcurrentHashMap.computeIfAbsent` looks like a free upgrade until the mapping function recurses on the same key, which the real `ConcurrentHashMap` explicitly documents as unsupported and can livelock or throw depending on JDK version — the fix is a plain `HashMap` behind a lock, or `computeIfAbsent` on a *different* key than the one being computed |
| 4.2 | `MyStream` — a hand-fused lazy pipeline over a `MySink` chain | Laziness is not "the library is slow to start", it is "nothing traverses the source until a terminal operation asks", and fusion means each *element* runs through every stage before the next element starts, not each *stage* running to completion before the next stage begins | `AbstractPipeline` wires the exact same shape — `wrapSink` calls chained backward from the terminal stage at `evaluate` time, so a three-stage pipeline over one element does filter→map→forEach before the second element enters at all (Puzzle 1) | The real pipeline additionally fuses `SIZED` characteristics through the chain so a `peek` between a sized source and a short-circuiting terminal can be *elided entirely* — a hand-rolled `MyStream` that always calls every registered `peek` cannot reproduce that optimisation without carrying the same characteristics bitmask the JDK does |
| 4.3 | Collectors from scratch (`MyCollector`'s five-function contract, `toList`/`joining`/`groupingBy` with correct combiners, a bounded top-N, a boxing-free statistics collector, a `CONCURRENT`-characteristic harness) | `Collector<T,A,R>` needs *five* functions, not three — `supplier`, `accumulator`, `combiner`, `finisher`, `characteristics` — because a parallel `.collect()` builds one accumulator per split, and something has to merge them back together; skip the combiner and parallel collection either fails to compile or silently drops a partition | `Collectors.toList()`'s combiner is `(left, right) -> { left.addAll(right); return left; }`; `groupingBy`'s combiner recursively merges two maps key-by-key, which is the one line most hand-rolled `groupingBy` clones forget and then get wrong results from under `.parallelStream()` | A hand-rolled boxing-free statistics collector over `long[]` slots mirrors `Collectors.summingLong`'s accumulator array exactly (`new long[1]`) — but `Collectors.summingInt` still uses `new int[1]`, so a build that "fixes" the overflow by widening every summing collector to `long` is *not* what the JDK actually ships (Puzzle 4 in `90-interview-basics.md`; not re-run here) |
| 4.4 | `MyOptional` (the shared `EMPTY`, eager-versus-lazy `orElse`/`orElseGet`, allocation harnesses) | A container that must be either "holds exactly one value" or "holds nothing", with reference equality usable as an identity check for the empty case, and a subtly different eagerness contract between its two "give me a default" methods | `Optional.empty()` returns a cached `Optional.EMPTY` singleton via an unchecked raw-type cast, exactly like the toy build (Puzzle 3); `orElse(T other)` evaluates `other` unconditionally as an ordinary Java method argument, while `orElseGet(Supplier)` only invokes the supplier when the optional is actually empty (Puzzle 5) | `java.util.Optional` deliberately does **not** implement `Serializable` at all — its Javadoc states plainly that it is "not intended" for use as a field type or to be serialized, precisely because a serialized field defeats the "always call the accessor, never store the container" usage pattern `Optional` is designed around; a hand-rolled `MyOptional` that adds `implements Serializable` and gets it working has built something the real JDK type deliberately withholds, not a faithful copy of it |
| 4.5 | Records, sealed types and patterns from scratch (a hand-written pre-record equivalent, a `List` component written three ways, an array component's `equals` failure, a sealed hierarchy plus the exact error a fourth case produces, Visitor side by side, an expression-tree interpreter, a reflective wither) | Counting the lines a record collapses makes the boilerplate tax concrete: a canonical constructor, `equals`/`hashCode`/`toString`, and `final` accessors named after the components, not `getX()` | `javac` generates all of that from the record header alone; the compact constructor can only reassign the *parameter*, never `this.field`, because the field write is emitted by the compiler after the compact constructor body finishes (Puzzle 2 in `90-interview-basics.md`) | An array-typed record component breaks `equals`/`hashCode`/`toString` by reference (arrays never override `Object`'s identity-based `equals`), which the JDK does **not** special-case — the fix is the same whether you hand-write the record or let `javac` generate it: don't use a raw array component, wrap it (`List.copyOf`) or write custom accessors |
| 4.6 | Concurrency builds (an echo server written both ways and measured, a pinning reproducer with its `ReentrantLock` fix, a `ThreadLocal` memory harness, a `Semaphore`-bounded client, `ShutdownOnFailure` against `allOf`'s orphan task, a hedge, a common-pool starvation reproducer) | Virtual threads are "cheap" specifically for blocking I/O, not for CPU-bound work, and that cheapness has a real cost surface: a `ThreadLocal` set on a virtual thread lives exactly as long as that one task, so per-task-scoped state is fine, but per-*logical-session* state that outlives one virtual thread must move to a `ScopedValue` or explicit context object, not a `ThreadLocal` (Puzzle for this file) | `Executors.newVirtualThreadPerTaskExecutor()` schedules onto the same `ForkJoinPool`-backed scheduler documented in Parts 2–3 (`parallelism = availableProcessors()`, `maxPoolSize = max(parallelism, 256)`); `CompletableFuture.allOf` does not cancel siblings when one fails, which is exactly the "orphan" `build-it/05` reproduces and `StructuredTaskScope.ShutdownOnFailure` fixes by cancelling every other fork the instant one fails | `synchronized` still pins a virtual thread's carrier on Java 21 because the JVM cannot suspend a monitor-held continuation; `ReentrantLock` is the 21-specific fix, but JEP 491 makes object monitors continuation-aware from **Java 24**, so a build that hard-codes "always use `ReentrantLock` inside virtual threads" is a version-scoped answer, not a permanent one |
| 4.7 | Filling the Java 21 gaps (fixed-window batching via a custom `Spliterator`, `zip` via a paired spliterator, `scan`/`distinctBy` as stateful mappers with their parallel failure demonstrated, `takeUntil` and a `mapConcurrent` on virtual threads, the `Gatherers` diff) | Java 21's `Stream` API has no windowing, zipping, running-scan, or distinct-by-key operator built in, and a naive stateful `map` that mutates captured state to fake one of these breaks the moment `.parallel()` is added, because nothing serialises access to that captured state across split partitions | Every one of these gaps is filled properly by `java.util.stream.Gatherers` (preview in 22, finalised in 24) — `Gatherers.windowFixed`, `Gatherers.scan`, custom `Gatherer` implementations — which carries an explicit combiner-equivalent for the parallel case that a hand-rolled stateful mapper omits | A hand-rolled `scan` implemented as `map(x -> { state[0] += x; return state[0]; })` produces silently wrong (non-deterministic, order-dependent) totals under `.parallel()` because each split gets its own copy of the captured array reference behaviour depends on JIT/fork timing — this is the exact bug class `Gatherer`'s explicit `combiner` parameter exists to close |
| 4.8 | Diagnostic harnesses (the fifteen-snippet puzzler set, stream-versus-loop and parallel-versus-sequential JMH sweeps, a source-splitting benchmark, a lambda-startup harness, a capture identity harness, a `javap` walk, a collector-combiner cost harness, exhaustiveness drift, record serialization, text-block indentation, a migration smoke harness) | Every claim in Parts 1–4 that sounds like folklore ("streams are slower than loops", "lambdas allocate every time", "records are `Serializable` for free") is falsifiable, and this file's whole point is to falsify or confirm each one with a harness rather than an anecdote | A stream-versus-loop JMH sweep over the 2.8M-reservation dataset shows streams and loops converging once JIT warms up, with the gap concentrated in cold-start and small-N cases; a capture-identity harness shows a non-capturing lambda is cached as a single instance per call site while a capturing lambda allocates a new instance per invocation, visible directly in `javap -c` as `invokedynamic` versus the captured-argument count on the `BootstrapMethods` entry | A record does **not** get `Serializable` "for free" — it must still declare `implements Serializable` explicitly — but *once it does*, deserialization is fundamentally different from an ordinary class: the JDK invokes the record's canonical constructor with the deserialized component values rather than bypassing constructors via unsafe field injection, so validation logic in the canonical/compact constructor still runs on every deserialized instance, which is a security property ordinary `Serializable` classes do not get without hand-written `readObject` validation |

That is all seven `build-it/` files and every one of Part 4's eight syllabus subsections (§4.1
through §4.8, including the two collapsed into `build-it/03` — collectors at §4.3 and
`MyOptional` at §4.4). Where a row's mechanism needed a source quote to state honestly, that quote
and its file/line context live in the subject file that owns the build; this table exists so you
can see the whole part at once.

---

## Interview Q&As

**Q1. You built a memoising decorator over `ConcurrentHashMap.computeIfAbsent`. Why is that
dangerous in a way a memoising decorator over a plain `HashMap` behind a lock isn't?**

`ConcurrentHashMap.computeIfAbsent` holds an internal per-bin lock for the duration of the mapping
function so that only one thread computes a given key at a time. If the mapping function itself
calls back into `computeIfAbsent` on the *same map* — which is exactly what a recursive memoised
function does, for example a naive memoised Fibonacci where computing `fib(n)` calls
`memo.computeIfAbsent(n, k -> memo.computeIfAbsent(k - 1, ...) + ...)` and `n - 1` happens to hash
into the same bin — the second call tries to re-enter a lock the first call already holds on the
same thread, which the JDK documents as unsupported and which manifests as either an
`IllegalStateException` ("Recursive update") or, on some JDK versions and bin layouts, an
indefinite block. A plain `HashMap` behind your own explicit lock doesn't have this failure mode
in the same shape, because you control exactly when the lock is released — though you'd still
deadlock if you recursed while holding it. The real fix for memoised recursion is to structure the
recursion so the recursive call happens *after* the outer `computeIfAbsent` call has returned, not
nested inside the mapping function.

**Q2. Explain what "fusion" means for a hand-rolled `MyStream`, concretely — not "it's lazy".**

Fusion means each pipeline stage is represented as a `MySink` that wraps the *next* stage's sink,
and the whole chain processes one element completely — through every filter, map, and terminal
step — before the source hands over the next element. It is not "run every filter over the whole
collection, then run every map over what's left, then run the terminal step" — that would be the
naive, unfused interpretation, and it's exactly what a chain of `.stream().filter(...).toList()`
followed by a second `.stream().map(...).toList()` actually does, because each of those calls is a
*separate* pipeline evaluation. A single fused chain — `filter(...).map(...).forEach(...)` called
without an intervening terminal operation — interleaves the three per element: filter element 1,
map element 1, forEach element 1, then filter element 2, and so on. You can watch this directly by
putting a `println` in each stage and reading the interleaved order (Puzzle 1 below).

**Q3. What are the five functions in the `Collector<T,A,R>` contract, and why does `combiner`
have to exist even for a sequential-only use case?**

`supplier` creates a fresh mutable accumulator (for example `ArrayList::new`); `accumulator` folds
one element into it (`List::add`); `combiner` merges two accumulators built independently
(`(left, right) -> { left.addAll(right); return left; }`); `finisher` converts the accumulator
into the final result type, often the identity function when `A` and `R` are the same type; and
`characteristics` is a set of hints (`CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH`) the stream
implementation uses to pick faster code paths. `combiner` has to be part of the interface even
though a purely sequential collection never calls it, because `Collector` is one contract shared
by both `stream()` and `.parallelStream()` — the same collector instance has to work when the
stream implementation decides, based on the source's spliterator, to split the work and collect
each half independently. Omit or mis-implement the combiner and the *sequential* code path works
fine in testing; only a parallel run — possibly in production, possibly under load, rarely under a
small test fixture — silently loses one partition's contribution.

**Q4. `MyOptional.empty()` returns a shared singleton cast from a raw type. Why is that cast
actually safe, given `MyOptional<Integer>` and `MyOptional<String>` are different types?**

It's safe because of type erasure and because the empty instance never actually holds a `T` — its
internal `value` field is `null` regardless of what type parameter the caller asks for. The
unchecked cast `(MyOptional<T>) EMPTY` doesn't create a new object or change any runtime state; it
only affects what the *compiler* believes the static type of the reference is from that point
forward. Because generics are erased at compile time and the object genuinely never stores or
returns a value of the erased type, there is no way for the cast to produce a
`ClassCastException` at any later read — there's nothing to cast incorrectly, because there's no
`T`-typed value in the object at all. This is exactly the same trick `java.util.Optional.empty()`
uses, and it means every empty `Optional`/`MyOptional` in a JVM, regardless of declared type
parameter, is reference-identical (Puzzle 3 below).

**Q5. A colleague says `MyOptional.orElse(fallback())` and `MyOptional.orElseGet(this::fallback)`
are interchangeable as long as `fallback()` has no side effects and is cheap. What's the flaw in
that framing?**

The flaw is narrower than it sounds: "no side effects and cheap" does describe when the two are
*observably* equivalent, but it hides the actual mechanical difference, which is that
`orElse(T other)` takes `other` as a plain method argument — Java evaluates method arguments
before the call happens, unconditionally, whether the optional is present or empty. `orElseGet`
takes a `Supplier<T>` and only invokes `.get()` inside the branch where the optional is actually
empty. So if `fallback()` is expensive (a database round trip, a lookup against
`ClientRestrictions`) or has side effects (logging, incrementing a metric), `orElse(fallback())`
pays that cost on *every* call regardless of whether the optional had a value, while
`orElseGet(this::fallback)` pays it only when needed. The "as long as it's cheap and has no side
effects" caveat is doing all the work — the interchangeability only holds in the narrow case where
the difference wouldn't matter anyway.

**Q6. You hand-wrote a sealed hierarchy of `Verdict` subtypes and an exhaustive `switch` over it.
What exact error does the compiler give if you add a fourth subtype to the `permits` clause but
forget to add its case to the switch?**

A compile-time error naming the missing type explicitly, of the shape `the switch expression does
not cover all possible input values` (for a `switch` expression) — javac lists which permitted
subtype(s) are unhandled and refuses to compile until either that case is added or a catch-all
(`default ->`, or a `case Verdict v ->` binding the sealed supertype itself) is present. This is
the entire value proposition of sealing the hierarchy: the compiler, not a runtime `NoSuchElement`
or a silently-wrong `default` branch, catches the omission the moment a new subtype is added
anywhere in the codebase, at every switch over that sealed type, not just the one you're currently
editing.

**Q7. Why is an echo server built on virtual threads competitive with — or better than — one built
on a fixed platform-thread pool, specifically for many concurrent connections?**

Because the bottleneck in an echo server is I/O wait, not CPU, and a platform thread blocked on a
socket read holds an entire OS thread — with its megabyte-scale default stack and kernel
scheduling overhead — idle for the duration of that wait. A fixed pool caps concurrency at the
pool size specifically to avoid exhausting OS threads, so connection count beyond the pool size
queues. A virtual thread blocked on the same socket read unmounts from its carrier platform
thread entirely; the carrier is freed to run other virtual threads while the blocked one waits,
and the virtual thread's own footprint is a small, resizable stack in the Java heap rather than a
fixed OS stack. That's why the build's own measurement (1, 1,000, and 50,000 concurrent
connections) shows the virtual-thread version staying roughly flat in memory and latency at scale
where the fixed-pool version either queues connections or has to be sized so large it starts
contending for other OS resources.

**Q8. `CompletableFuture.allOf` and `StructuredTaskScope.ShutdownOnFailure` both "wait for several
concurrent tasks", but the build's fan-out reproducer shows them behaving differently when one
task fails. What's the difference?**

`allOf(futures...)` returns a `CompletableFuture<Void>` that completes only once *every* input
future completes, whether successfully or exceptionally — but it does not cancel the futures that
are still running when one of them fails. If you fan out a call to the identity vendor and a call
to the watchlist provider and the identity call fails fast, the watchlist call — the build's
"orphan" — keeps running to completion (or its own timeout) with nothing waiting on its result
anymore, burning a thread and the provider's rate-limit budget for no benefit.
`StructuredTaskScope.ShutdownOnFailure` fixes this by construction: the moment any forked subtask
throws, `join()` returns and the scope's `close()` — reached via try-with-resources — interrupts
every subtask that is still running before the enclosing method returns. The structural guarantee
is that no subtask can outlive the scope that forked it, which `allOf` never promised in the first
place.

**Q9. Why does `Gatherers.scan` handle a running total under `.parallel()` correctly where a
hand-rolled `map` with a captured mutable accumulator does not?**

A hand-rolled `map(x -> { total[0] += x; return total[0]; })` closes over a single shared mutable
array and mutates it from whatever thread ends up processing each element — under `.parallel()`,
multiple threads can race on that same array with no synchronisation, and even if a synchronised
version avoided data races, the *order* of accumulation would depend on which split each thread
happened to process, so the running totals would come out different from a run to run, not just
different from the sequential answer. A `Gatherer` built with `Gatherers.scan` or a custom
`Gatherer` implementation carries an explicit integrator and, where the operation genuinely
supports it, a combiner that defines how two partial results merge — the same shape `Collector`
uses. Where the scan is inherently order-dependent (a running total genuinely depends on
processing order), the `Gatherer` framework's answer is that such an operation is correctly
modelled as sequential-only, and it says so through its characteristics rather than silently
producing a wrong parallel answer the way the hand-rolled version does.

**Q10. A record is declared `implements Serializable` and successfully deserializes. Does its
compact constructor's validation logic run on the deserialized instance, or does deserialization
bypass it like it bypasses ordinary constructors?**

It runs. This is one of the places records deliberately depart from classic `Serializable`
semantics rather than reusing them unchanged: an ordinary `Serializable` class is deserialized by
allocating the object directly (via a JVM-internal mechanism) and writing its fields from the
stream, skipping every constructor entirely — which is exactly why hand-written `readObject`
validation exists, to claw back the checks a normal `new` call would have enforced. Records don't
get that shortcut: the JDK's default record deserialization reads the component values from the
stream and then calls the record's own canonical constructor with them, so any validation or
normalisation written into a compact constructor — rejecting a negative `Money` amount, rescaling
a `BigDecimal`, checking a `StakeSplit` invariant — executes on every deserialized instance the
same as it does on every instance built directly with `new`. This is a genuine security property,
not incidental: it closes the classic "construct an invalid object by feeding a serialized stream
straight to `ObjectInputStream`" attack that ordinary classes need explicit `readObject`
validation to close.

---

## Predict-the-output puzzles

Every snippet below was compiled with `javac --release 21` and run with `java` on this machine.
Output shown is the real output, not recalled.

### Puzzle 1 — fusion, element by element

```java
import java.util.List;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.Predicate;

interface MySink<T> {
    void accept(T t);
}

abstract class MyStream<T> {
    abstract void forEachUnfused(MySink<T> sink);

    void forEach(Consumer<? super T> action) {
        forEachUnfused(t -> action.accept(t));
    }

    <R> MyStream<R> map(Function<? super T, ? extends R> mapper) {
        MyStream<T> upstream = this;
        return new MyStream<R>() {
            void forEachUnfused(MySink<R> downstream) {
                upstream.forEachUnfused(t -> downstream.accept(mapper.apply(t)));
            }
        };
    }

    MyStream<T> filter(Predicate<? super T> predicate) {
        MyStream<T> upstream = this;
        return new MyStream<T>() {
            void forEachUnfused(MySink<T> downstream) {
                upstream.forEachUnfused(t -> { if (predicate.test(t)) downstream.accept(t); });
            }
        };
    }

    static <T> MyStream<T> of(List<T> source) {
        return new MyStream<T>() {
            void forEachUnfused(MySink<T> sink) {
                for (T t : source) sink.accept(t);
            }
        };
    }
}

public class Fusion {
    public static void main(String[] args) {
        MyStream.of(List.of(4.20, 8.40, 1.50))
            .filter(v -> { System.out.println("filter " + v); return v > 2.0; })
            .map(v -> { System.out.println("map " + v); return v * 100; })
            .forEach(v -> System.out.println("forEach " + v));
    }
}
```

**Output:**

```
filter 4.2
map 4.2
forEach 420.0
filter 8.4
map 8.4
forEach 840.0
filter 1.5
```

**Why:** each `MySink` wraps the *next* stage's sink, so calling `forEach` on the outermost
(`filter`) stage drives one element all the way through `filter → map → forEach` before the
source loop hands over the next element — exactly the shape `AbstractPipeline.copyInto` produces
by walking `wrapSink` backward from the terminal stage once, then feeding the source through the
resulting composite sink. The stake of 1.50 fails the `filter` predicate (`v > 2.0`), so its
`map` and `forEach` sinks are never invoked — the trailing "filter 1.5" line with nothing after it
is the visible proof that filtering short-circuits per element rather than building an
intermediate filtered list first.

### Puzzle 2 — the reuse guard, minus the JDK's real spliterator plumbing

```java
import java.util.List;
import java.util.function.Consumer;

final class MyStream<T> {
    private final List<T> source;
    private boolean linkedOrConsumed = false;

    MyStream(List<T> source) { this.source = source; }

    void forEach(Consumer<? super T> action) {
        if (linkedOrConsumed) {
            throw new IllegalStateException("stream has already been operated upon or closed");
        }
        linkedOrConsumed = true;
        for (T t : source) action.accept(t);
    }
}

public class Reuse {
    public static void main(String[] args) {
        MyStream<String> stakes = new MyStream<>(List.of("AA-610", "DEP-301"));
        stakes.forEach(System.out::println);
        stakes.forEach(System.out::println);
    }
}
```

**Output:**

```
AA-610
DEP-301
Exception in thread "main" java.lang.IllegalStateException: stream has already been operated upon or closed
	at MyStream.forEach(Reuse.java:16)
	at Reuse.main(Reuse.java:27)
```

**Why:** the hand-rolled `linkedOrConsumed` flag reproduces exactly the guard the real
`AbstractPipeline` checks at every public entry point, and it produces the identical exception
message text (`MSG_STREAM_LINKED`, quoted verbatim from the JDK source in `92-interview-internals.md`).
The toy version's diff from the real one is that a real pipeline's flag lives on the *root* stage
and is consulted through every derived stage built on top of it, not just on the object the caller
holds a reference to — reproducing that fully would require the toy build to track a shared
upstream reference the way `AbstractPipeline`'s `sourceStage` field does.

### Puzzle 3 — `MyOptional.empty()`'s shared identity

```java
final class MyOptional<T> {
    private static final MyOptional<?> EMPTY = new MyOptional<>(null);
    private final T value;
    private MyOptional(T value) { this.value = value; }

    @SuppressWarnings("unchecked")
    static <T> MyOptional<T> empty() { return (MyOptional<T>) EMPTY; }

    static <T> MyOptional<T> of(T value) { return new MyOptional<>(value); }
}

public class OptionalIdentity {
    public static void main(String[] args) {
        MyOptional<String> clientLookup = MyOptional.empty();
        MyOptional<Integer> bonusLookup = MyOptional.empty();
        System.out.println((Object) clientLookup == (Object) bonusLookup);
    }
}
```

**Output:**

```
true
```

**Why:** `MyOptional.empty()` never allocates — it always returns the same cached `EMPTY` instance,
unchecked-cast to whatever type parameter the call site asks for. Because generics are erased at
runtime and `EMPTY.value` is genuinely `null` regardless of the declared `T`, the cast can never
produce a wrong-typed read, and every empty `MyOptional<String>`, `MyOptional<Integer>`, or any
other type parameter in the same JVM is the identical object. `(Object)` casts are needed here only
because two different parameterisations of the same generic type are not directly comparable with
`==` at the source level — the compiler rejects `clientLookup == bonusLookup` outright as
"incomparable types" even though at runtime they are, after erasure, exactly the same reference.

### Puzzle 4 — `orElse` is eager, `orElseGet` is lazy

```java
import java.util.function.Supplier;

final class MyOptional<T> {
    private final T value;
    private MyOptional(T value) { this.value = value; }
    static <T> MyOptional<T> of(T value) { return new MyOptional<>(value); }

    T orElse(T other) { return value != null ? value : other; }

    T orElseGet(Supplier<? extends T> supplier) {
        return value != null ? value : supplier.get();
    }
}

public class OrElseLaziness {
    static String fallbackClientLookup() {
        System.out.println("fallback lookup executed");
        return "CLIENT-DEFAULT";
    }

    public static void main(String[] args) {
        MyOptional<String> found = MyOptional.of("CLIENT-9F21");

        System.out.println("orElse   -> " + found.orElse(fallbackClientLookup()));
        System.out.println("orElseGet -> " + found.orElseGet(OrElseLaziness::fallbackClientLookup));
    }
}
```

**Output:**

```
fallback lookup executed
orElse   -> CLIENT-9F21
orElseGet -> CLIENT-9F21
```

**Why:** `"fallback lookup executed"` prints exactly once, and it prints *before* either result
line, even though `found` already holds a value and neither fallback value is ever actually used.
`orElse(T other)` is an ordinary method whose parameter is evaluated by the caller before the
method is even entered — `fallbackClientLookup()` runs unconditionally the instant
`found.orElse(fallbackClientLookup())` is evaluated, regardless of what `orElse`'s body does with
the result. `orElseGet(Supplier<? extends T>)` instead receives a method reference — no code inside
`fallbackClientLookup` runs until (and unless) `orElseGet`'s body actually calls `supplier.get()`,
and here the ternary's condition (`value != null`) is true, so `.get()` is never reached and the
message is never printed a second time. Treating the two as interchangeable "convenience"
overloads is the pitfall; the real distinction is who controls when — or whether — the fallback
computation runs.

### Puzzle 5 — a virtual thread's `ThreadLocal` does not travel with a "session"

```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class VirtualThreadLocal {
    static final ThreadLocal<String> CONTEXT = ThreadLocal.withInitial(() -> "none");

    public static void main(String[] args) throws Exception {
        try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
            Future<String> first = pool.submit(() -> {
                CONTEXT.set("stake-reservation-7f3a");
                return CONTEXT.get();
            });
            System.out.println("task1: " + first.get());

            Future<String> second = pool.submit(CONTEXT::get);
            System.out.println("task2: " + second.get());
        }
    }
}
```

**Output:**

```
task1: stake-reservation-7f3a
task2: none
```

**Why:** `Executors.newVirtualThreadPerTaskExecutor()` starts a brand-new `VirtualThread` for every
submitted task — there is no thread reuse the way a fixed platform-thread pool reuses its worker
threads. `ThreadLocal` storage lives on the `Thread` object itself, so the first task's
`CONTEXT.set(...)` is invisible to the second task's virtual thread, which is a completely
different `Thread` instance and falls back to `CONTEXT`'s initial value (`"none"`). This is the
build's `ThreadLocal` memory harness in miniature: because virtual threads are meant to be
created by the million for per-request or per-stake-reservation work, a `ThreadLocal` used the way
it's used on a small platform-thread pool — as a coarse-grained, long-lived, thread-reused cache —
either does nothing useful (this puzzle) or, in the harness's actual memory measurement, allocates
a fresh `ThreadLocalMap` entry per virtual thread at a scale a platform-thread pool never reaches.
The fix for state that must actually outlive one virtual-thread task is a `ScopedValue` bound for
the duration of a structured scope, or an explicit context object passed as a parameter — not a
`ThreadLocal`.

---

## Pitfalls

### Assuming a memoising `computeIfAbsent` decorator is a drop-in, always-safe upgrade

**Wrong**

```java
Map<Integer, Long> memo = new ConcurrentHashMap<>();

Function<Integer, Long> fib = n -> memo.computeIfAbsent(n, k ->
    k < 2 ? (long) k : memo.computeIfAbsent(k - 1, kk -> kk * 1L) // recursive re-entry, same map
);
```

**Right**

```java
Map<Integer, Long> memo = new ConcurrentHashMap<>();

long fib(int n) {
    if (n < 2) return n;
    Long cached = memo.get(n);
    if (cached != null) return cached;
    long value = fib(n - 1) + fib(n - 2); // recursion happens outside computeIfAbsent
    memo.put(n, value);
    return value;
}
```

**Why people believe it:** `computeIfAbsent` reads as "the memoisation primitive" in every
tutorial that introduces it, and the non-recursive cases (a pure, non-recursive expensive
computation) genuinely work perfectly with the naive form. The recursive case only breaks when
the recursive call happens to land on the *same* map inside the mapping function currently being
computed, which is precisely the shape memoised recursive functions want to write — so the failure
is invisible in every test that doesn't specifically recurse through the same key, and the
`ConcurrentHashMap` Javadoc's warning about "some attempted update operations... may throw an
exception" is easy to skim past.

### Believing `MyOptional.orElse` and `orElseGet` are interchangeable "style" choices

**Wrong**

```java
String label = clientLookup.orElse(fetchDefaultLabelFromDatabase());
```

**Right**

```java
String label = clientLookup.orElseGet(() -> fetchDefaultLabelFromDatabase());
```

**Why people believe it:** both read as "give me this value, or that one if it's missing", and in
demo code the fallback is usually a cheap literal or a trivial computation, so the eager-versus-lazy
distinction never surfaces. It only bites once the fallback becomes a real database call, a network
request, or anything with a side effect — at which point `orElse` pays the cost on every single
call site invocation, present or absent, silently.

### Treating a hand-rolled stateful `map` as a legitimate `scan`/running-total operator

**Wrong**

```java
long[] total = {0};
List<Long> running = deposits.parallelStream()
    .map(d -> { total[0] += d; return total[0]; })  // races under .parallel()
    .toList();
```

**Right**

```java
List<Long> running = deposits.stream() // sequential — the operation is inherently order-dependent
    .map(d -> { total[0] += d; return total[0]; })
    .toList();
// or, once Gatherers is available (finalised at Java 24):
List<Long> running = deposits.stream().gather(Gatherers.scan(() -> 0L, Long::sum)).toList();
```

**Why people believe it:** `.parallel()` reads as a free performance switch that only changes
*how fast* a stream runs, not *what answer* it produces, because for stateless operations
(`filter`, `map` with a pure function) that's exactly true. A stateful `map` that mutates a
captured variable is the one case where `.parallel()` silently changes correctness, not just
speed, and nothing in the type system flags it — `Function<T,R>` doesn't know or care whether its
body has side effects.

### Assuming a record gets working serialization "for free" once it's declared `Serializable`

**Wrong**

```java
record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion) implements Serializable {}
// assumed: "records are simple, so serialization just works, and validation is bypassed like any
// other Serializable class"
```

**Right**

```java
record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion) implements Serializable {
    StakeSplit {
        if (bonusPortion.add(cashPortion).signum() < 0) {
            throw new IllegalArgumentException("stake split cannot be negative");
        }
    }
} // the compact constructor's check DOES run on deserialization — this is not a gap to patch
```

**Why people believe it:** the general folklore about `Serializable` — "deserialization bypasses
constructors, so validation logic needs a hand-written `readObject`" — is true for ordinary
classes and gets generalised to records without re-checking, because records are marketed as
"just like a class but less boilerplate." The actual JDK behaviour for records is the opposite of
the folklore: deserialization calls the canonical constructor, so compact-constructor validation
runs on every deserialized instance without any extra code, which is a pleasant surprise rather
than a gap — but only if you know to expect it rather than defensively re-validating out of habit.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `MyStream` fusion order | Per element through every stage (filter→map→forEach), not per stage over every element |
| Stream reuse throws | `IllegalStateException: stream has already been operated upon or closed` |
| `Collector<T,A,R>`'s five functions | `supplier`, `accumulator`, `combiner`, `finisher`, `characteristics` |
| `Collectors.toList()`'s combiner | `(left, right) -> { left.addAll(right); return left; }` |
| `MyOptional.empty()` / `Optional.empty()` | Cached singleton via unchecked raw-type cast — every empty instance is reference-identical |
| `orElse(T)` | Argument evaluated unconditionally, every call |
| `orElseGet(Supplier)` | Supplier invoked only when the optional is empty |
| Record compact constructor | Reassigns the constructor **parameter**; the field write is compiler-generated afterward |
| Array-typed record component | Breaks `equals`/`hashCode`/`toString` — arrays never override identity-based `Object.equals` |
| Sealed switch, missing a `permits` case | Compile error: switch does not cover all possible input values |
| Virtual thread + `ThreadLocal` | Scoped to the one task's virtual thread only — no reuse across tasks, unlike a pooled platform thread |
| `synchronized` pinning | Present through Java 23; removed by JEP 491 continuation-aware monitors at **Java 24** |
| `CompletableFuture.allOf` on partial failure | Does **not** cancel still-running siblings — the "orphan" |
| `StructuredTaskScope.ShutdownOnFailure` | Cancels every other fork the instant one subtask fails, enforced at `close()` |
| Hand-rolled `scan` under `.parallel()` | Races on captured mutable state — order-dependent operations must stay sequential or move to `Gatherers.scan` |
| `Gatherers` finalisation | Preview at Java 22, finalised at **Java 24** |
| Record `Serializable` deserialization | Invokes the canonical constructor — compact-constructor validation runs on every deserialized instance |

---

## Self-test

**Q1.** In the fusion puzzle, the 1.50 stake amount produces a "filter 1.5" line with no
corresponding "map" or "forEach" line after it. What does that prove about how the pipeline is
wired, beyond "the filter excluded it"?

<details><summary>Answer</summary>

It proves the exclusion happens per element, inline, rather than as a separate pass over a
filtered intermediate collection. If `MyStream` first built a filtered `List` and then iterated
that list for `map`/`forEach`, the printed order would group all three "filter" lines together,
followed by all the "map"/"forEach" lines for only the surviving elements — a phase-by-phase
order, not an element-by-element one. Instead, each element's "filter" print is immediately
followed by that same element's "map" and "forEach" prints (when it passes) or by nothing further
(when it doesn't) before the next element's "filter" print appears — direct evidence that the
`MySink` chain is invoked once per element, all the way through, exactly as `AbstractPipeline`'s
real fused sink chain does.

</details>

**Q2.** Why does `MyCollector`'s `combiner` function have to correctly merge two independently
built accumulators, rather than simply being able to assume it will never be called?

<details><summary>Answer</summary>

Because `Collector<T,A,R>` is the single contract used by both `.stream().collect(...)` and
`.parallelStream().collect(...)` — the same collector instance has to support both. When a stream
implementation decides to split the source (based on the spliterator's characteristics and the
fork/join framework's leaf-target heuristic covered in Part 3), it builds one accumulator per
split via `supplier`, folds elements into each independently via `accumulator`, and then must
merge the resulting accumulators back into one via `combiner` before `finisher` produces the final
result. A collector whose combiner is missing or wrong works perfectly under every sequential test
and silently drops or corrupts partitions the first time it runs under `.parallelStream()`, which
is exactly the trap the JDK's own `Collectors.groupingBy` avoids by recursively merging two maps
key-by-key inside its combiner.

</details>

**Q3.** A reviewer says "`MyOptional.empty()`'s cast to `(MyOptional<T>) EMPTY` is unsafe — it's
an unchecked cast, and unchecked casts can fail at runtime." What's wrong with that claim here
specifically?

<details><summary>Answer</summary>

Unchecked casts *can* fail at runtime in general — for example casting an `Object[]` that's
actually a `String[]` to an `Integer[]` and then reading from it throws `ArrayStoreException` or
`ClassCastException` downstream. But `MyOptional.EMPTY`'s cast is safe specifically because the
object being cast never actually stores a value of the erased type parameter — `EMPTY.value` is
`null` for every caller, regardless of what `T` they asked for. Because generics are erased at
compile time and there is no `T`-typed data inside the object to misinterpret, there is no
operation you can perform on the resulting `MyOptional<T>` reference that could ever surface a
type mismatch at runtime — the "unsafety" an unchecked cast normally warns about requires there to
be genuine typed data that could be misread, and here there isn't any.

</details>

**Q4.** Why does the `ThreadLocal` puzzle print `"none"` for the second task instead of the value
the first task set, given both tasks run through the same `ExecutorService`?

<details><summary>Answer</summary>

Because `Executors.newVirtualThreadPerTaskExecutor()` creates a brand-new `VirtualThread` for
every submitted task rather than reusing a fixed set of worker threads. `ThreadLocal` state is
keyed by the `Thread` object's own `ThreadLocalMap`, so it never crosses between two different
`Thread` instances by design — the "same executor" fact is irrelevant, because the executor's job
here is exactly *not* to reuse threads. The second task runs on a genuinely different virtual
thread than the first, so `CONTEXT.get()` on that thread finds no prior `.set()` call and falls
back to the `ThreadLocal.withInitial` default, `"none"`.

</details>

**Q5.** What specifically does `StructuredTaskScope.ShutdownOnFailure` guarantee that
`CompletableFuture.allOf` does not, and where does that guarantee get enforced in code?

<details><summary>Answer</summary>

It guarantees that no forked subtask can still be running once the enclosing structured block has
finished — either because every subtask succeeded, or because one failed and every sibling was
cancelled. `allOf(futures...)` gives you a single future that completes once every input completes
one way or another, but it never reaches into a still-running future to cancel it if a sibling
fails; a task fanned out via `allOf` and still executing when another fails just keeps running,
disconnected from anything waiting on it — the "orphan." `ShutdownOnFailure`'s guarantee is
enforced structurally: the scope is opened and used inside a try-with-resources block, and its
`close()` method — guaranteed to run by the try-with-resources machinery even if an exception
propagates — interrupts every subtask that hasn't completed yet before control leaves the block.

</details>

**Q6.** Why is a hand-rolled `scan`/running-total implemented as a stateful `map` correctness-safe
under `.stream()` but not under `.parallelStream()`, given it's the exact same lambda?

<details><summary>Answer</summary>

Under a sequential stream, elements are processed strictly one at a time, in encounter order, by a
single thread — the captured mutable accumulator is only ever touched by one thread at a time and
in a well-defined order, so `total[0] += d` behaves exactly like a plain sequential loop. Under
`.parallelStream()`, the source is split across multiple threads that each process their own
partition concurrently, and all of them close over and mutate the *same* array reference with no
synchronisation between them — the read-modify-write on `total[0]` is not atomic, so concurrent
increments can be lost (a classic race), and even setting synchronisation aside, the *order* in
which partitions get processed relative to each other is unspecified, so a running total computed
this way isn't reproducibly the same running total a sequential pass would produce. The lambda's
code doesn't change between the two calls — only the concurrency model executing it does, and
`map`'s contract never promised its function was safe to run concurrently against shared state.

</details>

**Q7.** A build's diagnostic harness section claims a record's canonical constructor "runs on
deserialization." Is that claim consistent with the general rule that `Serializable` bypasses
constructors — and if it's an exception to that rule, why does the JDK make an exception here?

<details><summary>Answer</summary>

It's a genuine, deliberate exception to the general `Serializable` rule. Ordinary classes are
deserialized by allocating the object directly and writing field values from the stream without
calling any constructor — the mechanism `readObject`/`readResolve` exist to work around when
validation is needed. Records are deserialized differently on purpose: the default mechanism reads
the component values from the stream and invokes the record's own canonical constructor with them,
so any check or normalisation written in a compact constructor (rejecting an invalid `Money`
amount, rescaling a `BigDecimal` to two decimal places) executes on every deserialized instance the
same as on every instance built with `new`. The JDK's own reasoning is that records are meant to
be transparent, immutable data carriers whose invariants are supposed to hold universally — letting
deserialization silently construct an instance that violates those invariants would defeat the
entire point of encoding the invariant in the compact constructor in the first place, so the
serialization spec for records specifically routes through it.

</details>

**Q8.** Why does the concurrency build's echo-server comparison show the virtual-thread version's
memory footprint staying roughly flat from 1,000 to 50,000 concurrent connections, while a
platform-thread version either can't reach 50,000 or has to be re-architected to get there?

<details><summary>Answer</summary>

A platform thread's default stack is allocated by the OS at a fixed size (commonly around 512 KB
to 1 MB depending on platform and JVM flags) whether or not that thread is actively using much of
it, and each one consumes a real OS-level thread-scheduling slot; 50,000 concurrent platform
threads means roughly 25–50 GB of stack memory reserved and 50,000 entries for the OS scheduler to
manage, which is why a platform-thread-per-connection design caps out far below that and instead
gets re-architected around a fixed worker pool plus an event loop (Netty-style) to avoid the
per-connection thread cost entirely. A virtual thread's stack is a small, resizable structure that
lives in the Java heap and grows only as deep as the call stack it's actually using at a given
moment; when the virtual thread blocks on I/O, it unmounts from its platform-thread carrier
entirely, releasing that carrier to serve other virtual threads, so the number of *carrier*
platform threads stays small (bounded by the virtual-thread scheduler's parallelism) regardless of
how many *virtual* threads are logically waiting on I/O at once.

</details>

**Q9.** What's the single biggest reason a hand-rolled `MyOptional` that adds working
`Serializable` support is *not* actually matching real JDK behaviour, given `Optional` itself
implements `Serializable`-adjacent machinery unevenly?

<details><summary>Answer</summary>

`java.util.Optional` does **not** implement `Serializable` at all — its Javadoc explicitly warns
that `Optional` is intended primarily as a method return type and states plainly that it is "not
intended" to be used as a field type or serialized. A hand-rolled `MyOptional` that adds
`implements Serializable` and gets it working end to end has built something *more* capable than
the real JDK type in this one specific respect, which is exactly backwards from most of this
part's other diffs (where the toy build is *missing* something the JDK has) — the lesson is that
"the JDK does X" is not always the right assumption to reach for; sometimes the JDK's answer is
"we deliberately don't support this," and building the missing piece anyway can hide a design
decision that existed for a documented reason.

</details>

**Q10.** Summarise, in one sentence each, the mechanism reason `build-it/06`'s hand-rolled
`Gatherers`-shaped fixes for windowing, zipping, and scanning are all safer under `.parallel()`
than the naive stateful-`map` versions they replace, even though none of them were built by
copying `Gatherers` source.

<details><summary>Answer</summary>

Windowing via a custom `Spliterator` is safe under `.parallel()` because a `Spliterator`'s
`trySplit()` contract is the JDK's own mechanism for describing how a source divides, so a
window-aware spliterator that only ever hands out complete windows per split behaves correctly no
matter how the stream implementation chooses to split it; zipping via a paired spliterator is safe
because it advances both underlying sources together inside a single `tryAdvance` call rather than
relying on two independently-iterated streams staying in lockstep across threads; and scan/window
operations that are inherently order-dependent are safe specifically because the build marks them
as forced-sequential (or routes them through a real `Gatherer`'s explicit combiner once available)
rather than letting a captured mutable variable race silently under `.parallel()` the way the
naive `map`-based version does.

</details>

---

## Deferred

None.

---

**Leaves covered:** none — part wrap-up (0 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 816
