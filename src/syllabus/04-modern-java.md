# Syllabus — 04 Modern Java (8 → 21)

**Target version: Java 21 LTS** (baseline for every constant, signature and behaviour below).
Anything introduced or changed in Java 22–26 is marked inline with its version and, where it
supersedes a Java 21 behaviour, with `[VERSION-TRAP]`. Preview status is stated on every leaf where
it applies — a feature being preview is itself the interview-relevant fact.

Scope boundary against the sibling guides: the collections themselves live in
`02-java-collections.md`, the language substrate (erasure, `==`/`equals`, initialisation order,
exceptions, `java.time`) in `03-java-core.md`, the memory model and the executor framework in
`05-multithreading-concurrency.md`, JIT/GC/class loading in `06-jvm-internals.md`. This file owns the
Java-8-and-later *additions*: lambdas, streams, `Optional`, `var`, records, sealed types, pattern
matching, text blocks, switch expressions, virtual threads, structured concurrency, and the
release-by-release delta. Where a concept is owned elsewhere the leaf carries `[X-REF nn]` and the
bible states the mechanism in one paragraph before pointing away — it never sends the reader off
empty-handed.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the bible must work the argument through, not state the result |
| `[SOURCE]` | must quote real JDK source, JEP text or spec text (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic code |
| `[TRAP]` | must carry a `**Trap:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 21 and what changed |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number/byte arithmetic explicitly |
| `[BYTECODE]` | must show `javap -c` output and read it instruction by instruction |

---

# PART 1 — BASICS

## §1.1 Why "modern Java" is a topic at all

1.1.1 Java 8 (March 2014) as the discontinuity: lambdas, streams, default methods, `Optional` and
      `java.time` landed together and changed the idiom, not just the API surface.
1.1.2 The six-month release train since Java 9 (JEP 322, time-based releases), and what it replaced
      — the multi-year mega-release with feature-driven slips. `[RESEARCH]`
1.1.3 LTS releases: 8, 11, 17, 21, 25. What LTS means commercially (vendor support window) versus
      technically (nothing — the JDK is the same code). `[RESEARCH]`
1.1.4 The vendor matrix: Oracle JDK, Eclipse Temurin, Amazon Corretto, Azul Zulu, BellSoft Liberica,
      IBM Semeru, Microsoft Build of OpenJDK — and why the answer to "which JDK" is a licensing
      question, not a technical one. `[RESEARCH]`
1.1.5 Preview features (JEP 12): `--enable-preview` at both compile and run, the class file's minor
      version set to 65535, and the rule that a preview class file will not load on a *different*
      release. `[RESEARCH]` `[NUM]`
1.1.6 Incubator modules (`jdk.incubator.*`) versus preview features versus experimental VM options
      (`-XX:+UnlockExperimentalVMOptions`) — three different maturity ladders. `[RESEARCH]`
1.1.7 Why "it is still preview" is the interview-relevant fact: it means the API will change and you
      must not build a published contract on it.
1.1.8 Three kinds of change, and which require what: language features (recompile with a new
      `--release`), library features (recompile or not, depending on the call), runtime features
      (just run on the new JVM). `[X-REF 06]`
1.1.9 `--release N` versus `-source`/`-target`: only `--release` also restricts the *API* to that
      release, which is why `-source 8 -target 8` silently lets you call Java 17 methods that
      `NoSuchMethodError` at runtime. `[TRAP]` `[PROVE]`
1.1.10 Class file major versions: 52 = 8, 53 = 9, 55 = 11, 61 = 17, 65 = 21, 69 = 25 — and how to
       read `UnsupportedClassVersionError` from them. `[NUM]` `[RESEARCH]`
1.1.11 `jdeps`, `jdeprscan` and `jlink` as the migration toolchain. `[X-REF 06]`
1.1.12 What "Java 21" means for this file, and how to check what you are actually running:
       `java -version`, `Runtime.version()` and its `feature()`/`interim()`/`update()`/`patch()`
       accessors, `System.getProperty("java.version")`. `[RESEARCH]`

*(12 leaves)*

## §1.2 Functional interfaces

1.2.1 Definition (JLS 9.8): an interface with exactly one abstract method — the SAM. `[SOURCE]`
1.2.2 `@FunctionalInterface` is optional. It documents intent and makes the compiler enforce the
      one-abstract-method rule; a lambda works without it. `[TRAP]`
1.2.3 Methods that override a `public` method of `Object` do not count toward the SAM count —
      `Comparator` declares both `compare` and `equals` and is still functional. `[PROVE]` `[SOURCE]`
1.2.4 `default`, `static` and `private` interface methods do not count either. `[X-REF 03]`
1.2.5 A generic method (one with its own type parameters) cannot be implemented by a lambda, so an
      interface whose only abstract method is generic is not usable as a lambda target. `[TRAP]`
1.2.6 The vocabulary of a function shape: arity, parameter types, return type, declared exceptions.
1.2.7 `java.util.function` contains exactly **43** interfaces in Java 21. `[NUM]` `[RESEARCH]`
1.2.8 The six core shapes: `Function<T,R>`, `BiFunction<T,U,R>`, `Predicate<T>`, `Consumer<T>`,
      `Supplier<T>`, and the operator specialisations.
1.2.9 `UnaryOperator<T> extends Function<T,T>`; `BinaryOperator<T> extends BiFunction<T,T,T>` —
      they are narrowings, not new shapes.
1.2.10 `Predicate`'s surface: `and`, `or`, `negate`, `isEqual(Object)`, and `not(Predicate)`
       (Java 11). `[RESEARCH]`
1.2.11 `Function.identity()`, `andThen`, `compose` — and the reversed argument order between the
       last two. `[TRAP]` `[PROVE]`
1.2.12 `Consumer.andThen`, `BiFunction.andThen`, `BinaryOperator.minBy`/`maxBy`,
       `BiPredicate.and`/`or`/`negate`.
1.2.13 The primitive-specialisation naming scheme, with the full 43-name inventory: `IntX`,
       `ToIntX`, `XToYFunction`, `ObjIntConsumer`, `BooleanSupplier`. `[RESEARCH]`
1.2.14 Why the specialisations exist: one `Integer.valueOf` per element per stage in a hot pipeline.
       `[NUM]` `[X-REF 03]`
1.2.15 The shapes the JDK does **not** give you: no `TriFunction`, no primitive `BiFunction` beyond
       `ToXBiFunction`, no checked-exception variant of anything. `[TRAP]`
1.2.16 Functional interfaces outside `java.util.function`: `Runnable`, `Callable<V>`,
       `Comparator<T>`, `ThreadFactory`, `Executor`, `InvocationHandler`, `FileFilter`,
       `Iterable` is *not* one (it has a `default forEach` but one abstract `iterator`, so it is).
       Enumerate and correct. `[RESEARCH]`
1.2.17 `Comparator` as the most-used functional interface in practice: `comparing`,
       `comparingInt/Long/Double`, `thenComparing` ×3, `reversed`, `naturalOrder`, `reverseOrder`,
       `nullsFirst`, `nullsLast`. `[X-REF 02]`
1.2.18 `Callable<V>` versus `Supplier<T>`: `Callable.call()` declares `throws Exception`,
       `Supplier.get()` does not — which is why executors take `Callable`. `[X-REF 05]`
1.2.19 Declaring your own functional interface, and when it beats the JDK one: naming the domain
       concept (`PriceRule`, `RetryPolicy`) instead of `Function<Order, BigDecimal>`.
1.2.20 A functional interface with a `throws` clause is perfectly legal, and is the cleanest of the
      four checked-exception workarounds. `[BUILD]`

*(20 leaves)*

## §1.3 Lambda expressions

1.3.1 The syntax forms: `() -> expr`, `x -> expr`, `(x, y) -> expr`, `(Type x) -> { ... }`,
      `(var x) -> ...` (Java 11).
1.3.2 Implicitly typed versus explicitly typed parameter lists; you may not mix the two in one
      lambda. `[TRAP]`
1.3.3 `var` in lambda parameters (Java 11, JEP 323) exists only so you can attach an annotation or
      `final` to an otherwise implicitly typed parameter. `[RESEARCH]`
1.3.4 Expression body versus block body; a block body must `return` on every completing path.
1.3.5 A lambda is a **poly expression**: it has no standalone type, and the target type supplies the
      functional interface. `[PROVE]` `[SOURCE]` `[X-REF 03]`
1.3.6 The target-typing contexts: assignment, method invocation argument, cast, `return`, ternary
      branches, array initialiser, lambda body.
1.3.7 `Object o = () -> {};` does not compile; `Object o = (Runnable) () -> {};` does. `[TRAP]`
      `[PROVE]`
1.3.8 The same lambda source text can implement different interfaces at different sites — the
      lambda has no intrinsic type. `[PROVE]`
1.3.9 Overload ambiguity between two functional-interface parameters (`Runnable` versus
      `Callable<T>`): void-compatible versus value-compatible bodies, and when javac gives up.
      `[TRAP]` `[PROVE]`
1.3.10 A lambda body does **not** introduce a new scope for `this`, `super`, or names — it is
       lexically transparent, unlike an anonymous class body. `[TRAP]` `[X-REF 03]`
1.3.11 `this` inside a lambda is the *enclosing* instance; inside an anonymous class it is the
       anonymous instance. The single most consequential difference when porting. `[TRAP]`
1.3.12 A lambda parameter may not shadow an enclosing local — redeclaring `x` is a compile error,
       whereas an anonymous class may shadow freely. `[TRAP]` `[PROVE]`
1.3.13 Capture is by value and requires effectively-final locals; instance fields are not captured
       at all, the enclosing `this` is. `[PROVE]` `[X-REF 03]`
1.3.14 Wanting to mutate a captured counter: the one-element-array hack, `AtomicInteger`, and why
       `reduce`, a collector, or a plain loop is the actual answer. `[TRAP]`
1.3.15 Capturing a loop variable: the enhanced-`for` variable is a fresh variable per iteration and
       is capturable; the classic `for` index is one variable and is not. `[TRAP]` `[PROVE]`
1.3.16 A checked exception thrown inside a lambda whose SAM does not declare it is a compile error;
       the four workarounds, forward-referenced to §2.2.
1.3.17 Recursion: a lambda cannot reference the local variable it is being assigned to; use a field,
       a two-step assignment, or a method reference. `[TRAP]` `[PROVE]`
1.3.18 Lambdas and generics: the SAM's type variables are instantiated by the target type; a lambda
       itself cannot declare type parameters.
1.3.19 Serializable lambdas: the intersection cast `(Runnable & Serializable) () -> ...`, the
       `SerializedLambda` form, and why this is slow and brittle. `[RESEARCH]`
1.3.20 Lambda parameters may be annotated and declared `final`.
1.3.21 Return-type inference for expression bodies; a void-compatible block body versus a
       value-compatible one, and an expression body that is both (a method call returning a value
       used in a `Consumer`). `[PROVE]`
1.3.22 Debugging a lambda: the synthetic frame `Foo.lambda$main$0` in a stack trace, and the
       `Foo$$Lambda/0x...` class name. `[RESEARCH]` `[VERSION-TRAP]`

*(22 leaves)*

## §1.4 Method references

1.4.1 The four documented kinds plus the two extra forms: static, bound instance, unbound instance,
      constructor, `super::method`, `Outer.this::method`. `[RESEARCH]`
1.4.2 `Type::staticMethod` — e.g. `Integer::parseInt`, `Math::max`.
1.4.3 `instance::method` — bound receiver, e.g. `System.out::println`.
1.4.4 `Type::instanceMethod` — unbound; the receiver becomes the first parameter, e.g.
      `String::length`, `String::compareTo`.
1.4.5 `Type::new` for constructors, and `int[]::new` / `String[]::new` for array constructors.
1.4.6 `super::method` inside an instance method, and where it is the only way to express the call.
1.4.7 `Outer.this::method` from inside an inner class. `[X-REF 03]`
1.4.8 Ambiguity when both a static and an unbound-instance form would apply (`Integer::toString`)
      — a compile error, resolved by writing the lambda. `[TRAP]` `[PROVE]`
1.4.9 `String::valueOf` and which of the eleven overloads the target type selects. `[TRAP]`
      `[X-REF 03]`
1.4.10 A bound method reference evaluates its receiver expression **at capture time**, once —
       `list::size` captures the current `list` object, not the variable. `[TRAP]` `[PROVE]`
1.4.11 A bound method reference on a null receiver throws NPE at capture time, even if the function
       is never invoked. `[TRAP]` `[PROVE]`
1.4.12 Method references to varargs methods, and to generic methods with an explicit type argument
       (`Type::<String>method`).
1.4.13 When a method reference is clearer than a lambda, and when it hides the argument order
       (`Map.Entry::comparingByValue` vs a written comparator). `[TRAP]`
1.4.14 A constructor reference to a record's canonical constructor, and to a compact-constructor
       record that validates.
1.4.15 A method reference to an overloaded method: the target type disambiguates; when it cannot,
       the compile error names all candidates.
1.4.16 In bytecode a method reference produces the same `invokedynamic` as a lambda but with a
       direct method handle as `implMethod` and **no** synthetic `lambda$` method. `[BYTECODE]`
       `[PROVE]`

*(16 leaves)*

## §1.5 The stream model

1.5.1 The javadoc definition: a stream "conveys elements from a source through a pipeline of
      computational operations"; it is not a data structure. `[SOURCE]`
1.5.2 The five stated properties: no storage, functional in nature, laziness-seeking, possibly
      unbounded, consumable. `[SOURCE]`
1.5.3 Anatomy: a source, zero or more intermediate operations, exactly one terminal operation.
1.5.4 Intermediate operations are **always lazy** and return a stream; terminal operations are eager
      except `iterator()` and `spliterator()`. `[SOURCE]`
1.5.5 Fusion: elements flow one at a time through the entire chain, not stage by stage. `[PROVE]`
1.5.6 Short-circuiting: intermediate (`limit`, `takeWhile`) versus terminal (`findFirst`,
      `anyMatch`); the javadoc's statement that short-circuiting is "necessary, but not sufficient"
      for an infinite pipeline to terminate. `[SOURCE]` `[PROVE]`
1.5.7 Stateless versus stateful intermediate operations; a stateful op may require a full pass and
      significant buffering, and a pipeline of only stateless ops needs one pass with minimal
      buffering. `[SOURCE]`
1.5.8 Encounter order: defined by the source. `List` and arrays have it; `HashSet` does not.
      `[SOURCE]` `[X-REF 02]`
1.5.9 `unordered()` as a hint that relaxes ordering constraints and legitimises reordering.
      `[SOURCE]`
1.5.10 Non-interference: the source must not be modified while the pipeline executes;
       `ConcurrentModificationException` (or worse, silent wrong answers) is the symptom. `[TRAP]`
       `[X-REF 02]`
1.5.11 Behavioural parameters must be **stateless**; the javadoc's own `Set<Integer> seen`
       counter-example. `[SOURCE]` `[TRAP]`
1.5.12 Side effects are discouraged and may be elided entirely; only `forEach` and `forEachOrdered`
       are documented to rely on them. `[SOURCE]` `[TRAP]`
1.5.13 A stream is consumed once: the second terminal operation throws
       `IllegalStateException: stream has already been operated upon or closed`. `[SOURCE]` `[TRAP]`
1.5.14 Streams are `AutoCloseable`, but only I/O-backed streams (`Files.lines`, `Files.walk`,
       `Files.find`, `Files.list`) actually need closing. `[TRAP]`
1.5.15 `onClose(Runnable)` and the try-with-resources form for a file-backed stream.
1.5.16 `BaseStream` and the four concrete stream types: `Stream<T>`, `IntStream`, `LongStream`,
       `DoubleStream`.
1.5.17 A stream is not a collection: no `size()`, no random access, no reuse, no `get(i)` — and the
       places that hurts.
1.5.18 What a stream buys (composition, laziness, one-line parallelism, declarative aggregation)
       and what it costs (debuggability, stack depth, allocation, no checked exceptions).

*(18 leaves)*

## §1.6 Stream sources

1.6.1 `Collection.stream()` and `Collection.parallelStream()` as `default` methods added to
      `Collection` in Java 8 — the canonical example of why default methods exist. `[X-REF 03]`
1.6.2 `Stream.of(T...)`, `Stream.of(T)`, `Stream.empty()`.
1.6.3 `Arrays.stream(T[])`, `Arrays.stream(T[], from, to)`, and the `int[]`/`long[]`/`double[]`
      overloads.
1.6.4 `Stream.iterate(seed, next)` — infinite; `Stream.iterate(seed, hasNext, next)` (Java 9) — the
      three-argument for-loop form. `[RESEARCH]`
1.6.5 `Stream.generate(Supplier)` — infinite and unordered, so `limit` on it in parallel is
      nondeterministic. `[TRAP]`
1.6.6 `IntStream.range` / `rangeClosed`, and why they are the best-splitting source in the JDK
      (`SIZED | SUBSIZED | ORDERED`). `[NUM]`
1.6.7 `Stream.concat(a, b)` — and why `concat` inside a loop builds a left-deep tree that
      `StackOverflowError`s on traversal. `[TRAP]` `[RESEARCH]`
1.6.8 `Stream.ofNullable(T)` (Java 9) — a zero-or-one stream, the cleanest null bridge.
1.6.9 `Optional.stream()` (Java 9) and the `.map(this::find).flatMap(Optional::stream)` idiom.
1.6.10 `Files.lines(Path)`, `Files.lines(Path, Charset)`, `Files.walk`, `Files.list`, `Files.find`,
       `Files.newDirectoryStream` — all hold a file handle and all must be closed. `[TRAP]`
1.6.11 `BufferedReader.lines()`, `String.lines()` (Java 11), `String.chars()`, `String.codePoints()`.
       `[X-REF 03]`
1.6.12 `Pattern.splitAsStream`, `Matcher.results()` (Java 9), `Scanner.tokens()` (Java 9).
       `[RESEARCH]`
1.6.13 `Random.ints/longs/doubles`, and the Java 17 `RandomGenerator` interface's stream methods.
       `[RESEARCH]`
1.6.14 `Map` has no `stream()`; you stream `entrySet()`, `keySet()` or `values()`. `[TRAP]`
       `[X-REF 02]`
1.6.15 `StreamSupport.stream(Spliterator, boolean)` as the general escape hatch, and
       `Spliterators.spliteratorUnknownSize(Iterator, characteristics)` for an `Iterator`. `[NUM]`
1.6.16 `JarFile.stream()`, `ZipFile.stream()`, `ServiceLoader.stream()`; `ResultSet` has none, so
       JDBC needs a hand-written bridge. `[X-REF 09]`
1.6.17 `Stream.builder()` and when it beats collecting into a list first.
1.6.18 Any infinite source requires a short-circuiting operation; `sorted()` or `distinct()` on an
       infinite stream never terminates. `[TRAP]`

*(18 leaves)*

## §1.7 Intermediate operations, exhaustively

1.7.1 `filter(Predicate)` — stateless, 1:0-or-1.
1.7.2 `map(Function)` — stateless, 1:1.
1.7.3 `mapToInt` / `mapToLong` / `mapToDouble` / `mapToObj` / `boxed` / `asLongStream` /
      `asDoubleStream` — the conversions between the four stream shapes.
1.7.4 `flatMap(Function<T, Stream<R>>)` — 1:N; each inner stream is closed after it is consumed.
1.7.5 `flatMapToInt` / `flatMapToLong` / `flatMapToDouble`.
1.7.6 `mapMulti` and `mapMultiToInt/Long/Double` (Java 16): a push-style `flatMap` taking a
      `BiConsumer<T, Consumer<R>>`, avoiding one `Stream` allocation per element. `[RESEARCH]`
      `[NUM]`
1.7.7 When `mapMulti` beats `flatMap`: few or zero outputs per element, primitive outputs, or
      output produced imperatively. `[RESEARCH]`
1.7.8 `distinct()` — stateful, uses `equals`/`hashCode`, preserves encounter order for ordered
      streams, and holds every distinct element in memory. `[X-REF 02]`
1.7.9 `sorted()` and `sorted(Comparator)` — a full barrier: buffers the whole stream, then sorts
      with TimSort. `[X-REF 01]` `[X-REF 02]`
1.7.10 `sorted()` on non-`Comparable` elements throws `ClassCastException` at *terminal* time, not
       at the `sorted()` call — the laziness surprise. `[TRAP]` `[PROVE]`
1.7.11 `limit(n)` — short-circuiting, cheap sequentially, expensive on an ordered parallel stream.
       `[TRAP]`
1.7.12 `skip(n)` — stateful, with the same parallel-ordering cost.
1.7.13 `takeWhile(Predicate)` / `dropWhile(Predicate)` (Java 9) — **prefix** semantics, not `filter`
       semantics: they stop at the first failure, they do not test every element. `[TRAP]`
1.7.14 `takeWhile`/`dropWhile` on an unordered stream are nondeterministic by specification.
       `[TRAP]` `[SOURCE]`
1.7.15 `peek(Consumer)` — documented as being "mainly to support debugging". `[SOURCE]`
1.7.16 `peek` may be skipped entirely: since Java 9 `count()` can answer from the source's size
       without traversing, so `stream.peek(...).count()` may never call the consumer. `[TRAP]`
       `[PROVE]` `[SOURCE]` `[VERSION-TRAP]`
1.7.17 `parallel()`, `sequential()`, `unordered()`, `onClose()` — `BaseStream` operations that
       change the pipeline rather than the elements.
1.7.18 The stateful/stateless classification table for every intermediate operation.
1.7.19 The short-circuiting classification table.
1.7.20 Operation order is semantics **and** cost: `filter` before `map`, `limit` before `sorted`
       gives a different answer than after. `[PROVE]` `[NUM]`
1.7.21 There is no `zip` in the JDK; the three workarounds (`IntStream.range` over indices, paired
       iterators, a custom `Spliterator`) and why none is pleasant. `[TRAP]`
1.7.22 There is no windowing, batching, `scan` or `distinctBy` in Java 21 — Stream Gatherers
       (JEP 461 preview 22, JEP 473 preview 23, JEP 485 final in 24) fill exactly this gap.
       `[RESEARCH]` `[VERSION-TRAP]`
1.7.23 `flatMap` and short-circuiting: prior to Java 10 a `flatMap` inner stream was fully consumed
       even when the downstream had short-circuited (JDK-8075939). `[VERSION-TRAP]` `[RESEARCH]`
1.7.24 The intermediate-operation inventory table: name, version, laziness, statefulness,
       short-circuiting, effect on `SIZED`/`ORDERED`/`DISTINCT`/`SORTED` flags.

*(24 leaves)*

## §1.8 Terminal operations, exhaustively

1.8.1 `forEach(Consumer)` — no encounter-order guarantee on a parallel stream, by specification.
      `[TRAP]` `[SOURCE]`
1.8.2 `forEachOrdered(Consumer)` — restores encounter order and largely erases the parallel win.
      `[NUM]`
1.8.3 `toArray()` returning `Object[]`, and `toArray(IntFunction<A[]>)` with `String[]::new`.
      `[TRAP]`
1.8.4 `collect(Collector)` and the three-argument `collect(supplier, accumulator, combiner)`.
1.8.5 `toList()` (Java 16) — returns an **unmodifiable** list that *does* permit nulls, unlike
      `Collectors.toUnmodifiableList()`. `[TRAP]` `[NUM]`
1.8.6 `reduce(BinaryOperator)` → `Optional<T>`.
1.8.7 `reduce(identity, BinaryOperator)` → `T`.
1.8.8 `reduce(identity, accumulator, combiner)` → `U`, and its three documented contracts.
      `[SOURCE]` `[PROVE]`
1.8.9 The identity and associativity requirements, and exactly what goes wrong in parallel when
      they are violated (subtraction, string concatenation with a non-identity seed). `[PROVE]`
1.8.10 `reduce` with a mutable accumulator is a bug — that is what `collect` exists for. `[TRAP]`
       `[PROVE]`
1.8.11 `min(Comparator)` / `max(Comparator)` → `Optional<T>`.
1.8.12 `count()` — and the Java 9 change that lets it bypass the pipeline when the size is known.
       `[VERSION-TRAP]` `[SOURCE]`
1.8.13 `anyMatch` / `allMatch` / `noneMatch` — short-circuiting, and the vacuous truth of `allMatch`
       and `noneMatch` on an empty stream (both `true`). `[TRAP]` `[PROVE]`
1.8.14 `findFirst()` versus `findAny()`: `findAny` is nondeterministic by design and is the
       parallel-friendly one.
1.8.15 `findFirst()` on an ordered parallel stream forces cross-task coordination. `[NUM]`
1.8.16 `iterator()` and `spliterator()` — the two lazy escape hatches, and the only terminal
       operations that are not eager. `[SOURCE]`
1.8.17 `sum()`, `average()`, `min()`, `max()`, `summaryStatistics()` on the primitive streams.
1.8.18 `IntSummaryStatistics` / `LongSummaryStatistics` / `DoubleSummaryStatistics`: count, sum,
       min, average, max — and that `DoubleSummaryStatistics` uses compensated summation.
       `[RESEARCH]` `[NUM]`
1.8.19 Which terminal operations return `Optional` and why (the empty-stream case has no answer).
1.8.20 Terminal-operation flags: `StreamOpFlag.SHORT_CIRCUIT` declared by the `TerminalOp`, and how
       it changes `copyInto` to `copyIntoWithCancel`. `[SOURCE]`
1.8.21 A pipeline with no terminal operation does **nothing at all**, silently — no warning, no
       error. `[TRAP]` `[PROVE]`
1.8.22 An exception thrown from a behavioural parameter propagates out of the terminal operation;
       in parallel, one arbitrary exception wins and the others are lost. `[TRAP]`
1.8.23 `collect` versus `reduce` versus `forEach`: the decision rule in one sentence each.
1.8.24 Boxing cost of `collect(toList())` applied to a primitive stream, and `boxed()` as the
       explicit, visible step. `[NUM]`
1.8.25 Null policy across terminal operations: `Stream` itself permits nulls, `Collectors.toMap`
       rejects null values, `Collectors.toUnmodifiableList` rejects null elements, `Stream.toList`
       permits them. `[TRAP]` `[NUM]`
1.8.26 The terminal-operation inventory table: name, version, return type, short-circuiting,
       parallel friendliness, ordering sensitivity.

*(26 leaves)*

## §1.9 Primitive streams

1.9.1 `IntStream`, `LongStream`, `DoubleStream` — and why there is no `CharStream`, `BooleanStream`
      or `FloatStream` (`char`/`short`/`byte`/`float` widen into the three that exist). `[TRAP]`
      `[RESEARCH]`
1.9.2 `String.chars()` returns an `IntStream` of UTF-16 code units, so `forEach(System.out::println)`
      prints numbers. `[TRAP]` `[PROVE]` `[X-REF 03]`
1.9.3 `boxed()`, `mapToObj`, `asLongStream()`, `asDoubleStream()` as the ways back out.
1.9.4 `mapToInt` / `mapToLong` / `mapToDouble` as the ways in from an object stream.
1.9.5 `IntStream.range(a, b)` versus `rangeClosed(a, b)`, and the empty-range case when `a >= b`.
1.9.6 `sum()` → `int`/`long`/`double`; `average()` → `OptionalDouble`; `max()`/`min()` →
      `OptionalInt`/`OptionalLong`/`OptionalDouble`; `count()` → `long`.
1.9.7 `summaryStatistics()` and its four (five with average) accessors.
1.9.8 `OptionalInt` / `OptionalLong` / `OptionalDouble` have **no** `map`, `flatMap` or `filter` —
      a deliberately thinner API that forces you back to the primitive. `[TRAP]` `[RESEARCH]`
1.9.9 `IntStream.of`, `Arrays.stream(int[])`, `IntStream.iterate`, `IntStream.generate`,
      `IntStream.concat`, `IntStream.empty`.
1.9.10 `Collectors.summingInt` versus `IntStream.sum()`: the boxing difference, measured. `[NUM]`
1.9.11 `IntStream.sum()` returns `int` and silently overflows past 2 147 483 647; `mapToLong(i -> i)
       .sum()` is the fix. `[TRAP]` `[NUM]` `[PROVE]` `[X-REF 03]`
1.9.12 `average()` on an empty stream is `OptionalDouble.empty()`, not `0.0`. `[TRAP]`
1.9.13 Sorting a primitive stream uses the primitive dual-pivot quicksort, not TimSort — different
       complexity guarantees and no stability question. `[X-REF 01]` `[X-REF 02]`
1.9.14 `IntStream.toArray()` versus `boxed().toArray(Integer[]::new)`: 4 bytes per element versus
       16 bytes per `Integer` plus a 4-or-8-byte reference. `[NUM]` `[PROVE]` `[X-REF 03]`
1.9.15 The primitive functional interfaces that pair with each stream type (`IntPredicate`,
       `IntUnaryOperator`, `IntToLongFunction`, `ObjIntConsumer`, …).
1.9.16 When to reach for a primitive stream: hot loops, large N, pure numeric aggregation — and
       when the boxed form is fine.

*(16 leaves)*

## §1.10 Collectors

1.10.1 The `Collector<T, A, R>` contract: `supplier()`, `accumulator()`, `combiner()`, `finisher()`,
       `characteristics()`. `[SOURCE]`
1.10.2 `Collector.Characteristics`: `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH`. `[SOURCE]`
1.10.3 `Collectors` exposes **30** distinct static factory methods across **54** overloads in
       Java 21. `[NUM]` `[RESEARCH]`
1.10.4 `toList()`, `toUnmodifiableList()`, `toSet()`, `toUnmodifiableSet()`,
       `toCollection(Supplier)`.
1.10.5 `Collectors.toList()` returns an `ArrayList` in the current implementation, but the contract
       promises neither the type nor mutability — code that casts it is broken by construction.
       `[TRAP]` `[SOURCE]`
1.10.6 `toMap` ×4: `(k,v)`, `(k,v,merge)`, `(k,v,merge,mapFactory)`, plus the concurrent sibling.
1.10.7 `toMap` throws `IllegalStateException: Duplicate key ...` when two elements map to the same
       key and no merge function is supplied. `[TRAP]` `[SOURCE]`
1.10.8 `toMap` throws `NullPointerException` on a null **value**, unlike `HashMap.put` — because it
       is implemented with `map.merge`. `[TRAP]` `[PROVE]` `[SOURCE]`
1.10.9 `toUnmodifiableMap` ×2 and `toConcurrentMap` ×4.
1.10.10 `joining()` ×3: no-arg, delimiter, delimiter+prefix+suffix.
1.10.11 `counting()`, `summingInt/Long/Double`, `averagingInt/Long/Double`,
        `summarizingInt/Long/Double`.
1.10.12 `averagingInt` returns `Double`; `summingDouble` and `averagingDouble` use Kahan compensated
        summation internally, which is why they can disagree with a naive loop. `[RESEARCH]` `[NUM]`
        `[SOURCE]`
1.10.13 `minBy(Comparator)` / `maxBy(Comparator)` → `Optional<T>`.
1.10.14 `reducing` ×3, and why it is the least-used collector (`reduce` on the stream is clearer
        unless it is a downstream).
1.10.15 `mapping(mapper, downstream)`, `flatMapping` (Java 9), `filtering` (Java 9).
1.10.16 `collectingAndThen(downstream, finisher)` — the unmodifiable-wrap and the
        collapse-to-a-single-value idioms.
1.10.17 `groupingBy` ×3: `(classifier)`, `(classifier, downstream)`,
        `(classifier, mapFactory, downstream)`.
1.10.18 `groupingBy` returns a `HashMap` with `ArrayList` values — no ordering guarantee at either
        level. Supply `TreeMap::new` / `LinkedHashMap::new` when order matters. `[TRAP]`
1.10.19 The classifier must not return null — `groupingBy` NPEs on a null key. `[TRAP]` `[PROVE]`
1.10.20 `groupingByConcurrent` ×3, and the three conditions under which it actually runs
        concurrently. `[SOURCE]`
1.10.21 `partitioningBy` ×2 — always returns a two-entry map containing both `false` and `true`,
        even for an empty stream, which is the one thing `groupingBy(pred)` does not give you.
        `[TRAP]` `[PROVE]`
1.10.22 `teeing(c1, c2, merger)` (Java 12) — run two collectors in one pass and merge. `[RESEARCH]`
1.10.23 Nested downstreams three levels deep: `groupingBy → groupingBy → mapping → toSet`.
1.10.24 Hand-writing a collector with `Collector.of(...)` ×2 overloads. `[BUILD]`
1.10.25 The three conditions for a genuine concurrent reduction: the stream is parallel, the
        collector is `CONCURRENT`, and the stream is unordered or the collector is `UNORDERED`.
        `[SOURCE]` `[PROVE]`
1.10.26 Why ordinary `collect(toList())` parallelises correctly without `CONCURRENT`: per-leaf
        containers plus a combiner tree. `[PROVE]`
1.10.27 `joining()` in parallel: the combiner is an O(n) copy at every merge, so it is a poor
        parallel collector. `[NUM]` `[PROVE]`
1.10.28 Collectors that return `Optional` (`minBy`, `maxBy`, `reducing(BinaryOperator)`) and why.
1.10.29 The collector inventory table: name, version, result type, mutability, null policy,
        characteristics, parallel behaviour.
1.10.30 Collectors that do not exist and what to use instead: no `toSortedMap`, no `toBiMap`, no
        `toEnumMap` shortcut, no `countingLong`-by-key beyond `groupingBy(…, counting())`.

*(30 leaves)*

## §1.11 Optional

1.11.1 Purpose: model "a value may be absent" in a **return type**, forcing the caller to
       acknowledge absence at the type level.
1.11.2 The javadoc API note: "primarily intended for use as a method return type where there is a
       clear need to represent 'no result'". Quote it. `[SOURCE]`
1.11.3 `Optional` is a value-based class: do not synchronize on it, do not depend on its identity.
       `[SOURCE]` `[TRAP]` `[X-REF 03]`
1.11.4 `Optional` is **not** `Serializable`, which is the concrete reason it does not belong in a
       field. `[TRAP]`
1.11.5 Construction: `of(T)` (NPE on null), `ofNullable(T)`, `empty()`.
1.11.6 Interrogation: `isPresent()`, `isEmpty()` (11), `get()`, `orElseThrow()` (10),
       `orElseThrow(Supplier)`.
1.11.7 Transformation: `map`, `flatMap`, `filter`, `or(Supplier)` (9), `stream()` (9).
1.11.8 Consumption: `ifPresent(Consumer)`, `ifPresentOrElse(Consumer, Runnable)` (9).
1.11.9 Defaults: `orElse(T)`, `orElseGet(Supplier)`.
1.11.10 The full method table with the version each was added: 15 methods at 1.8, three at 9
        (`ifPresentOrElse`, `or`, `stream`), one at 10 (`orElseThrow()`), one at 11 (`isEmpty`).
        `[NUM]` `[RESEARCH]`
1.11.11 `orElse` evaluates its argument **eagerly, even when a value is present**. `[TRAP]`
        `[PROVE]`
1.11.12 `get()` without a presence check throws `NoSuchElementException: No value present` and
        defeats the point; `orElseThrow()` is the same code with a self-documenting name. `[TRAP]`
1.11.13 `if (opt.isPresent()) { opt.get() }` is the null check you were replacing, plus one
        allocation. `[TRAP]`
1.11.14 `Optional` in a field: not serializable, one extra object and one extra dereference per
        access. `[TRAP]` `[NUM]`
1.11.15 `Optional` as a method parameter: overload the method or accept null instead. `[TRAP]`
1.11.16 `Optional` as a collection element or a map value: use an empty collection or an absent key.
        `[TRAP]`
1.11.17 Never return `null` from a method declared to return `Optional`. `[TRAP]`
1.11.18 `Optional<List<T>>` is almost always wrong; return an empty list. `[TRAP]`
1.11.19 `map` internally does `ofNullable(mapper.apply(value))`, so a mapper returning null yields
        `empty()` rather than an NPE. `[SOURCE]` `[PROVE]`
1.11.20 `flatMap` versus `map` when the mapper already returns an `Optional` — and the compile error
        that tells you which you needed.
1.11.21 Chained null-safe navigation: `a.map(A::b).map(B::c).filter(...).orElseGet(...)`.
1.11.22 `OptionalInt` / `OptionalLong` / `OptionalDouble`: `getAsInt`/`getAsLong`/`getAsDouble`, no
        `map`, and why you usually convert with `stream()` or `orElse`. `[TRAP]`
1.11.23 `Optional` in frameworks: Spring Data repository `findById`, Jackson's `Jdk8Module`,
        `@JsonInclude(NON_ABSENT)`, and the serialised shape you get without the module. `[TRAP]`
        `[RESEARCH]` `[X-REF 08]`
1.11.24 `Optional`'s allocation cost in a hot loop, why escape analysis usually removes it, and
        Valhalla's plan to make it genuinely free. `[NUM]` `[RESEARCH]` `[X-REF 06]`

*(24 leaves)*

## §1.12 `var`

1.12.1 Local variable type inference (Java 10, JEP 286). Compile-time only; Java stays statically
       typed and there is no runtime cost. `[PROVE]` `[BYTECODE]`
1.12.2 `var` is not `Object`, not `dynamic`, and not a keyword — it is a reserved *type name*, so a
       variable or method may still be called `var`. `[TRAP]` `[RESEARCH]` `[X-REF 03]`
1.12.3 Where `var` is legal: a local with an initialiser, the enhanced-`for` variable, the classic
       `for` index, a try-with-resources resource, and a lambda parameter (Java 11).
1.12.4 Where `var` is illegal: fields, method parameters, return types, `catch` parameters, a local
       without an initialiser, `var x = null`, an array-initialiser shorthand, and as a generic
       type argument. `[TRAP]`
1.12.5 `var x = null;` does not compile — the null type is not denotable. `[PROVE]`
1.12.6 `var arr = {1, 2, 3};` does not compile; `var arr = new int[]{1, 2, 3};` does.
1.12.7 `var list = new ArrayList<>();` infers `ArrayList<Object>` — the diamond has no target type
       to work from. `[TRAP]` `[PROVE]`
1.12.8 `var` with a ternary works; with a lambda or a method reference it does not, because those
       are poly expressions with no standalone type. `[TRAP]` `[PROVE]`
1.12.9 `var` can capture non-denotable types: an anonymous class type, an intersection type, a
       capture variable — types you cannot write down. `[PROVE]` `[X-REF 03]`
1.12.10 `var` and numeric literals: `var x = 1` is `int`, `var y = 1L` is `long`, `var f = 1.0` is
        `double`, `var b = (byte) 1` is `byte`. `[NUM]`
1.12.11 `var` in an enhanced-`for` over a raw or wildcard-typed collection, and what gets inferred.
1.12.12 `final var` is legal; `var` alone is **not** implicitly final.
1.12.13 You cannot annotate the inferred type, which is precisely why `(var x) -> ...` exists in
        lambda parameter lists.
1.12.14 JEP 323 (Java 11): `var` in lambda parameters is all-or-nothing across the parameter list.
        `[RESEARCH]`
1.12.15 The OpenJDK LVTI style guide's principles: reading code matters more than writing it; code
        should be clear from local reasoning; readability should not depend on an IDE; explicit
        types are a trade-off, not a virtue. `[RESEARCH]`
1.12.16 When `var` hurts: an opaque factory call, an accumulator whose width matters, and pinning
        the concrete implementation type into the local's static type
        (`var list = new ArrayList<String>()` makes `list` an `ArrayList`, not a `List`). `[TRAP]`

*(16 leaves)*

## §1.13 Records

1.13.1 A record is a transparent, shallowly immutable carrier for data — JEP 359 preview (14),
       JEP 384 second preview (15), JEP 395 final (16). `[RESEARCH]`
1.13.2 Brian Goetz's framing: records are "nominal tuples". Why the name matters and what it rules
       out. `[RESEARCH]`
1.13.3 The header declares the components; everything else is derived by the compiler.
1.13.4 Generated members: one `private final` field per component, a canonical constructor, an
       accessor per component, `equals`, `hashCode`, `toString`.
1.13.5 Accessors are `name()`, not `getName()` — which is exactly what older bean-convention
       frameworks fail on. `[TRAP]`
1.13.6 Implicit modifiers: the class is `final`, extends `java.lang.Record`, and therefore cannot
       extend anything else.
1.13.7 A record may not declare additional instance fields; it may declare static fields, static
       and instance methods, static initialisers, nested types, and it may implement interfaces.
1.13.8 The canonical constructor: implicit, or declared explicitly with the full parameter list.
1.13.9 The compact constructor: no parameter list, no explicit field assignment; you validate or
       reassign the parameters and the compiler assigns them at the end. `[PROVE]`
1.13.10 Validation and normalisation belong in the compact constructor, and the fix is always
        *reassigning the parameter*, never assigning the field. `[TRAP]`
1.13.11 Alternate constructors must delegate to the canonical one via `this(...)`.
1.13.12 An explicit canonical constructor must be at least as accessible as the record itself.
1.13.13 You may override an accessor, `equals`, `hashCode` or `toString` — and you then own the
        contracts, including the equal-implies-equal-hash rule. `[TRAP]` `[X-REF 03]`
1.13.14 Generic records, and how their type parameters appear in record patterns.
1.13.15 Local records (Java 16), nested records (implicitly static), and records declared inside an
        interface.
1.13.16 A record is **shallowly** immutable: a `List` or array component is still mutable, and the
        accessor hands out the live reference. `[TRAP]` `[PROVE]`
1.13.17 The fix: `List.copyOf` / `Map.copyOf` / `Set.copyOf` in the compact constructor, plus
        `clone()` on copy-out for array components. `[BUILD]`
1.13.18 An array component silently breaks `equals`/`hashCode`, because the generated code uses
        reference equality for arrays. Use a `List`. `[TRAP]` `[PROVE]`
1.13.19 Generated `equals` compares primitives with `==`, `float`/`double` with
        `Float.equals`/`Double.equals` semantics, and references with `Objects.equals`. `[SOURCE]`
        `[PROVE]`
1.13.20 Therefore inside a record `NaN` equals `NaN` and `0.0` does **not** equal `-0.0` — the
        opposite of `==`. `[TRAP]` `[PROVE]` `[X-REF 03]`
1.13.21 The generated `hashCode` algorithm is deliberately unspecified; never persist it, never
        assume stability across releases. `[TRAP]` `[SOURCE]`
1.13.22 `toString` format: `Point[x=1, y=2]`.
1.13.23 Records and null: components may be null unless you reject them;
        `Objects.requireNonNull` in the compact constructor is the convention.
1.13.24 Reflection: `Class.isRecord()`, `Class.getRecordComponents()`, and `RecordComponent`'s
        `getName`/`getType`/`getGenericType`/`getAccessor`/`getAnnotations`. `[RESEARCH]`
1.13.25 Record serialization: the components govern the serialised form, and deserialization goes
        through the canonical constructor. `[SOURCE]` `[RESEARCH]` `[X-REF 03]`
1.13.26 That closes the classic "deserialization bypasses the constructor and therefore your
        validation" hole. `[PROVE]` `[RESEARCH]`
1.13.27 Where records fit: DTOs, value objects, compound map keys, multiple return values, sealed
        hierarchy cases, and short-lived intermediate shapes inside a pipeline.
1.13.28 Where they do not, and the "record cliff": the moment you need a mutable field, an internal
        representation different from the API, or inheritance, you lose every generated member at
        once. JPA entities are the canonical example. `[TRAP]` `[RESEARCH]` `[X-REF 08]`

*(28 leaves)*

## §1.14 Sealed types

1.14.1 `sealed` restricts which types may extend or implement a type — JEP 360 preview (15),
       JEP 397 second preview (16), JEP 409 final (17). `[RESEARCH]`
1.14.2 Syntax: `public sealed interface Shape permits Circle, Rectangle, Triangle {}`.
1.14.3 Every permitted subtype must itself be `final`, `sealed`, or explicitly `non-sealed` — there
       is no default. `[TRAP]`
1.14.4 `non-sealed` reopens one branch of the hierarchy, and is the only hyphenated modifier in the
       language.
1.14.5 The `permits` clause may be omitted when all permitted subtypes are declared in the same
       source file. `[RESEARCH]`
1.14.6 Permitted subtypes must be in the same module as the sealed type, or — in the unnamed module
       — in the same package. `[RESEARCH]` `[TRAP]` `[X-REF 03]`
1.14.7 Every permitted subclass must **directly** extend or implement the sealed type; a
       grandchild is not permitted by the grandparent. `[RESEARCH]` `[PROVE]`
1.14.8 Anonymous classes and local classes can never be permitted subtypes — they have no canonical
       name to write in `permits`. `[TRAP]` `[RESEARCH]`
1.14.9 A sealed abstract class with record subclasses, versus a sealed interface implemented by
       records — the two ADT shapes and when each reads better.
1.14.10 Sealed interfaces plus records give Java algebraic data types: a sum of products.
1.14.11 Sealed versus enum: an enum is a closed set of *instances*, a sealed type is a closed set of
        *types*. Use an enum when the cases carry no per-case data. `[X-REF 03]`
1.14.12 What sealing buys you: exhaustiveness in a pattern switch, so adding a case turns every
        consumer into a compile error instead of a runtime fall-through. `[PROVE]`
1.14.13 What sealing buys the compiler: narrowing reference conversion can be rejected at compile
        time when the sealed hierarchy proves the cast impossible. `[RESEARCH]` `[PROVE]`
1.14.14 The cost: adding a permitted subtype is a source-incompatible change for every exhaustive
        switch over the hierarchy — a feature internally, a breaking change across an API boundary.
        `[TRAP]`
1.14.15 You cannot permit a type you do not control, which is what makes sealing a within-module
        design tool.
1.14.16 `sealed` + `non-sealed` as a controlled framework extension point.
1.14.17 Reflection: `Class.isSealed()` and `Class.getPermittedSubclasses()`. `[RESEARCH]`
1.14.18 The three ways to restrict extension compared: `final`, a package-private constructor, and
        `sealed` — visibility, granularity, and what the compiler can prove from each.

*(18 leaves)*

## §1.15 Pattern matching

1.15.1 A pattern is three things at once: a type test, a conditional extraction, and a binding.
1.15.2 Type patterns in `instanceof` — JEP 305 preview (14), JEP 375 (15), JEP 394 final (16):
       `if (o instanceof String s)`. `[RESEARCH]`
1.15.3 Flow scoping: the binding variable is in scope exactly where the compiler can prove the test
       succeeded — not a lexical block rule. `[PROVE]` `[X-REF 03]`
1.15.4 Flow scoping with negation: `if (!(o instanceof String s)) return;` puts `s` in scope for the
       rest of the method. `[PROVE]` `[TRAP]`
1.15.5 Flow scoping with `&&` (binding available on the right) versus `||` (it is not). `[TRAP]`
       `[PROVE]`
1.15.6 Type patterns in `switch` — four previews (17, 18, 19, 20), final as JEP 441 in Java 21.
       `[RESEARCH]`
1.15.7 `case null` and `case null, default` — `switch` is no longer null-hostile. `[RESEARCH]`
1.15.8 Without a `case null`, a pattern switch throws `NullPointerException` on a null selector,
       matching the historical behaviour. `[TRAP]` `[PROVE]`
1.15.9 Guarded patterns use `when` in the final syntax; the earlier previews used `&&`, so older
       material is wrong. `[VERSION-TRAP]` `[RESEARCH]`
1.15.10 Record patterns — JEP 405 preview (19), JEP 432 (20), JEP 440 final (21):
        `case Circle(double r)`. `[RESEARCH]`
1.15.11 Nested record patterns: `case Line(Point(int x1, int y1), Point(int x2, int y2))`.
1.15.12 `var` inside a record pattern component, and generic record pattern inference — the compiler
        infers the type arguments so you can drop them. `[RESEARCH]` `[PROVE]`
1.15.13 Record patterns in the header of an enhanced `for` were **removed** before Java 21 shipped;
        code and articles showing them do not compile on 21. `[VERSION-TRAP]` `[RESEARCH]`
1.15.14 Exhaustiveness is required of any `switch` that uses a pattern or null label, or whose
        selector type is not one of the legacy types. `[SOURCE]` `[RESEARCH]`
1.15.15 The legacy selector types that do **not** require exhaustiveness: `char`, `byte`, `short`,
        `int`, `Character`, `Byte`, `Short`, `Integer`, `String`, and enum types. `[SOURCE]`
        `[RESEARCH]`
1.15.16 Type coverage over a sealed hierarchy: the compiler reads `permits` to decide exhaustiveness,
        so omitting `default` is what makes future additions loud. `[PROVE]`
1.15.17 `MatchException` (new in 21): thrown when an exhaustive switch matches nothing at runtime —
        the separate-compilation drift case — and when a record accessor throws during
        deconstruction. `[RESEARCH]` `[TRAP]`
1.15.18 Dominance: writing a more general label before a more specific one is a compile error, not a
        silent shadow. `[PROVE]` `[SOURCE]`
1.15.19 A guarded case must precede its unguarded twin; the guard removes it from the dominance
        analysis. `[TRAP]` `[PROVE]`
1.15.20 A total type pattern dominates everything including `default`, so you cannot write both.
        `[TRAP]` `[RESEARCH]`
1.15.21 Patterns and generics: `case Box<String> b` is only allowed where it is provably safe;
        otherwise you get an unchecked-pattern error. `[X-REF 03]`
1.15.22 Record patterns in `instanceof`, outside a switch:
        `if (o instanceof Point(int x, int y))`.
1.15.23 Qualified enum constant labels in a pattern switch (`case Suit.HEARTS`) — new in 21.
        `[RESEARCH]`
1.15.24 What patterns still do not do in 21: no primitive type patterns (JEP 455/507, still
        preview), no array patterns, no deconstruction of non-record classes, no alternation
        (`or`) patterns, no unnamed patterns (final in 22). `[RESEARCH]` `[VERSION-TRAP]`

*(24 leaves)*

## §1.16 `switch` expressions and statements

1.16.1 Switch expressions — JEP 325 preview (12), JEP 354 (13), JEP 361 final (14): `switch`
       produces a value. `[RESEARCH]`
1.16.2 The arrow form `case L ->`: no fall-through, no `break`.
1.16.3 Multiple labels per arm: `case MONDAY, TUESDAY, WEDNESDAY ->`.
1.16.4 Block-bodied arms and `yield`.
1.16.5 `return` inside a switch **expression** is illegal; `yield` is the only way out. `[TRAP]`
1.16.6 A switch expression must be exhaustive; an enum switch expression without `default` fails to
       compile the moment a constant is added — which is the point. `[PROVE]`
1.16.7 The colon form with `yield` (a switch expression in legacy syntax) is legal and rare.
1.16.8 You may not mix arrow arms and colon arms in one `switch`. `[TRAP]`
1.16.9 Switch **statements** in the colon form keep the historical fall-through semantics, and
       `-Xlint:fallthrough` still exists for them. `[X-REF 03]`
1.16.10 Arrow-form switch statements: no fall-through, and no value produced.
1.16.11 Exhaustiveness in Java 21 applies to pattern switch *statements* as well as expressions —
        the rule is about the labels, not the form. `[RESEARCH]` `[TRAP]`
1.16.12 Definite assignment through a switch expression: every arm must yield a value or complete
        abruptly. `[X-REF 03]`
1.16.13 The permitted selector types: `char`, `byte`, `short`, `int` and their boxes, `String`,
        enums, and (21) any reference type with patterns. Never `long`, `float`, `double`,
        `boolean`. `[TRAP]`
1.16.14 Enum constants in an arrow switch are unqualified; in a pattern switch they may be
        qualified. `[RESEARCH]`
1.16.15 The `default`-in-an-enum-switch trade-off: silence on new constants versus a compile error.
        `[TRAP]`
1.16.16 A switch expression is an expression: assignable, returnable, passable as an argument, and
        nestable inside another switch arm.
1.16.17 The classic missing-`break` fall-through bug, and how the arrow form makes it unwritable.
1.16.18 When a switch expression beats a `Map<K, Supplier<V>>` lookup table and when it does not.

*(18 leaves)*

## §1.17 Text blocks

1.17.1 Text blocks — JEP 355 preview (13), JEP 368 (14), JEP 378 final (15). The result is an
       ordinary `java.lang.String`. `[RESEARCH]`
1.17.2 Syntax: opening delimiter `"""` followed by optional whitespace and a line terminator, then
       the content, then the closing `"""`.
1.17.3 Content may not begin on the opening delimiter's line — that is a compile error. `[TRAP]`
1.17.4 Three compile-time steps, in this order: normalise line terminators to `\n`, remove
       incidental whitespace, translate escape sequences. `[SOURCE]` `[RESEARCH]`
1.17.5 Normalisation means a CRLF source file still yields `\n` in the string — text blocks are
       platform-deterministic. `[PROVE]` `[RESEARCH]`
1.17.6 Incidental whitespace: the common prefix is computed over all non-blank content lines **plus
       the closing delimiter's line**. `[SOURCE]` `[PROVE]`
1.17.7 Therefore the closing delimiter's indentation controls the result — moving it left adds
       indentation to every line. `[TRAP]` `[PROVE]`
1.17.8 Trailing whitespace is stripped from every line, always. `[TRAP]`
1.17.9 `\s` (Java 15) is a space that survives stripping — the "fence" idiom for preserving trailing
       spaces. `[RESEARCH]`
1.17.10 `\` at end of line suppresses the line terminator (line continuation).
1.17.11 Escapes are processed **after** stripping, so a literal `\n` you wrote is not a candidate for
        normalisation and `\s` is not a candidate for stripping. `[PROVE]` `[RESEARCH]`
1.17.12 Ending without a trailing newline: put the closing delimiter at the end of the last content
        line.
1.17.13 `"` and `""` need no escaping inside a text block; three consecutive quotes need one `\"`.
1.17.14 The runtime siblings: `String.stripIndent()`, `String.translateEscapes()`,
        `String.formatted(Object...)`, `String.indent(int)` — all Java 12–15. `[RESEARCH]`
        `[X-REF 03]`
1.17.15 A text block is a constant expression: interned, usable as a `case` label and as an
        annotation value. `[PROVE]` `[X-REF 03]`
1.17.16 Where they earn their keep: SQL, JSON, HTML, GraphQL — and where they do not: regex, where
        `\` is still an escape and everything doubles. `[TRAP]`

*(16 leaves)*

## §1.18 Virtual threads — the model

1.18.1 JEP 425 preview (19), JEP 436 (20), JEP 444 final (21): a virtual thread is a
       `java.lang.Thread` scheduled by the Java runtime rather than the operating system.
       `[RESEARCH]`
1.18.2 The problem being solved: the thread-per-request model capped by platform thread count, and
       the async/reactive workaround's loss of readable stack traces, debuggers and profilers.
       `[RESEARCH]`
1.18.3 Little's law framing: concurrency = throughput × latency, so the thread count was the
       throughput cap. `[PROVE]` `[NUM]`
1.18.4 Virtual threads deliver **scale (throughput), not speed (latency)** — the javadoc's own
       phrasing. `[SOURCE]` `[TRAP]`
1.18.5 Carrier threads: a dedicated `ForkJoinPool` in FIFO mode, with default parallelism equal to
       the number of available processors. `[RESEARCH]` `[NUM]`
1.18.6 `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize` as the
       system properties that tune it. `[RESEARCH]` `[NUM]`
1.18.7 Mounting and unmounting: on a blocking call the continuation's stack is copied to the heap
       and the carrier is released; on resumption it is copied back. `[PROVE]`
1.18.8 What triggers an unmount: the JDK-instrumented blocking points — socket and channel I/O,
       `Thread.sleep`, `LockSupport.park`, `BlockingQueue`, `java.util.concurrent` locks,
       `HttpClient`, `Selector`, `Process.waitFor`. `[X-REF 05]`
1.18.9 What does not: file I/O on most platforms, `Object.wait` before Java 24, and any native
       frame. `[TRAP]` `[RESEARCH]`
1.18.10 Cost: a few hundred bytes plus a growable heap-resident stack, versus a platform thread's
        typically 1 MB reserved stack and an OS thread. `[NUM]`
1.18.11 `Thread.ofVirtual()` / `Thread.ofPlatform()` and the `Thread.Builder` API: `name(String)`,
        `name(prefix, start)`, `unstarted`, `start`, `factory`. `[RESEARCH]`
1.18.12 `Thread.startVirtualThread(Runnable)` as the one-liner.
1.18.13 `Executors.newVirtualThreadPerTaskExecutor()` — a new virtual thread per task, not a pool;
        `close()` waits for every submitted task. `[RESEARCH]`
1.18.14 `ExecutorService` is `AutoCloseable` since Java 19, which is what makes the
        try-with-resources form work. `[RESEARCH]`
1.18.15 Virtual threads are always daemon threads; `setDaemon(false)` throws. `[TRAP]` `[RESEARCH]`
1.18.16 Priority is fixed at `NORM_PRIORITY` and `setPriority` is silently a no-op. `[TRAP]`
        `[RESEARCH]`
1.18.17 They belong to a single fixed thread group, and `getName()` is the empty string unless you
        name them — which is why an unnamed virtual thread is hard to find in a dump. `[TRAP]`
1.18.18 `stop`, `suspend` and `resume` are unsupported and throw `UnsupportedOperationException`.
        `[RESEARCH]`
1.18.19 `ThreadLocal` still works, but its economics invert: a per-thread cache is now a per-task
        cache, and a million of them is a heap problem. `[TRAP]` `[SOURCE]`
1.18.20 `Thread.Builder.allowSetThreadLocals(boolean)` and
        `inheritInheritableThreadLocals(boolean)`. `[RESEARCH]`
1.18.21 Pinning: a virtual thread that cannot unmount holds its carrier. On Java 21 the two causes
        are blocking inside a `synchronized` block or method, and blocking inside a native or
        foreign frame. `[TRAP]` `[RESEARCH]`
1.18.22 Diagnosing pinning: `-Djdk.tracePinnedThreads=full|short`, and the `jdk.VirtualThreadPinned`
        JFR event, which is enabled by default with a 20 ms threshold. `[NUM]` `[RESEARCH]`
1.18.23 The fix on 21 is `ReentrantLock` around any blocking section; JEP 491 removes the
        `synchronized` cause entirely in Java 24, so "use ReentrantLock" is a version-scoped
        answer. `[VERSION-TRAP]` `[RESEARCH]` `[X-REF 05]`
1.18.24 Three standing rules: do not pool virtual threads, do not expect them to help CPU-bound
        work, and use a `Semaphore` — not a pool — to limit concurrency. `[TRAP]` `[SOURCE]`

*(24 leaves)*

## §1.19 Structured concurrency

1.19.1 The problem: unstructured concurrency leaks threads, loses cancellation, and produces
       thread dumps with no parent-child relationship. `[RESEARCH]`
1.19.2 The principle: a task split into concurrent subtasks returns to the same block, so the
       subtasks cannot outlive it — the concurrency analogue of structured programming.
1.19.3 The Java 21 shape (JEP 453, preview): `StructuredTaskScope` with `fork`, `join`, `close`, and
       `Subtask<T>`. `[RESEARCH]`
1.19.4 `fork` returns `Subtask<T>`, not `Future<T>` — JEP 453 changed this from the incubator form,
       so older articles are wrong. `[VERSION-TRAP]` `[RESEARCH]`
1.19.5 `StructuredTaskScope.ShutdownOnFailure`: cancel all siblings on the first failure;
       `join()` then `throwIfFailed()`.
1.19.6 `StructuredTaskScope.ShutdownOnSuccess`: cancel the rest on the first success — hedged
       requests.
1.19.7 `joinUntil(Instant)` for one deadline across the whole scope.
1.19.8 `Subtask.state()` (`UNAVAILABLE`, `SUCCESS`, `FAILED`), `get()`, `exception()`, and the
       `IllegalStateException` from calling `get()` before `join()`. `[TRAP]` `[RESEARCH]`
1.19.9 The scope must be created, forked into, joined and closed on the same thread, inside a
       try-with-resources block; violating that throws `StructureViolationException`. `[RESEARCH]`
1.19.10 Cancellation propagates by interrupt, so a subtask that swallows `InterruptedException`
        still leaks. `[TRAP]` `[X-REF 05]`
1.19.11 Versus `CompletableFuture.allOf`: there a failure leaves the siblings running and
        cancellation is advisory. `[PROVE]` `[X-REF 05]`
1.19.12 Versus `ExecutorService.invokeAll`: that does cancel on return, but the executor's lifetime
        has no relationship to the calling block.
1.19.13 On Java 21 this needs `--enable-preview`; the package moved from `jdk.incubator.concurrent`
        to `java.util.concurrent` at 21. `[TRAP]` `[RESEARCH]`
1.19.14 The API was reworked in Java 25 (JEP 505): public constructors replaced by static `open()`
        factories, and `ShutdownOnFailure`/`ShutdownOnSuccess` replaced by a composable `Joiner`.
        `[VERSION-TRAP]` `[RESEARCH]`
1.19.15 Scoped values — JEP 429 incubator (20), previews at 21/22/23/24, final as JEP 506 in
        Java 25: an immutable, bounded-lifetime, inheritable replacement for `ThreadLocal`.
        `[RESEARCH]`
1.19.16 `ScopedValue.where(KEY, value).run(...)` / `.call(...)`; the static `runWhere`/`callWhere`
        forms were removed in Java 24, so most published examples no longer compile.
        `[VERSION-TRAP]` `[RESEARCH]`

*(16 leaves)*

## §1.20 The library additions, 9 → 21

1.20.1 Java 9: `List.of` / `Set.of` / `Map.of` / `Map.ofEntries` — immutable, null-hostile, and with
       deliberately randomised iteration order for `Set`/`Map` per JVM run. `[TRAP]` `[X-REF 02]`
1.20.2 Java 10: `List.copyOf` / `Set.copyOf` / `Map.copyOf`, and
       `Collectors.toUnmodifiableList/Set/Map`.
1.20.3 Java 9 stream and `Optional` additions: `takeWhile`, `dropWhile`, `ofNullable`, the
       three-argument `iterate`, `Optional.stream`, `Optional.or`, `Optional.ifPresentOrElse`.
1.20.4 Java 9 language additions: private interface methods, effectively-final resources in
       try-with-resources, the diamond on anonymous classes, `@SafeVarargs` on private methods.
       `[X-REF 03]`
1.20.5 Java 9 platform: JPMS, JShell, jlink, multi-release JARs. `[X-REF 03]` `[X-REF 06]`
1.20.6 Java 9 APIs: the `Process` API (`pid`, `info`, `children`, `onExit`), `Flow` (the reactive
       streams SPI), `VarHandle`, `StackWalker`. `[X-REF 05]` `[X-REF 06]`
1.20.7 Java 9 runtime: compact strings and indified string concatenation — invisible but the two
       biggest string performance changes of the era. `[X-REF 03]`
1.20.8 Java 11 `String`: `isBlank`, `strip`, `stripLeading`, `stripTrailing`, `lines`, `repeat`.
       `[X-REF 03]`
1.20.9 Java 11 utility: `Files.readString`, `Files.writeString`, `Path.of`,
       `Collection.toArray(IntFunction)`, `Predicate.not`.
1.20.10 Java 11: the standard `HttpClient` (HTTP/2, WebSocket, synchronous and `CompletableFuture`
        forms) — the replacement for `HttpURLConnection`. `[X-REF 10]`
1.20.11 Java 11: single-file source-code launch (`java Foo.java`) and the shebang form.
1.20.12 Java 12: `Collectors.teeing`, `String.indent`, `String.transform`, `Files.mismatch`,
        `CompactNumberFormat`.
1.20.13 Java 14: helpful `NullPointerException` messages (JEP 358), on by default since 15.
        `[X-REF 03]`
1.20.14 Java 15: `String.stripIndent`, `translateEscapes`, `formatted`; `CharSequence.isEmpty`.
1.20.15 Java 16: `Stream.toList`, `Stream.mapMulti`, `Period`/`Duration` additions,
        day-period formatting in `DateTimeFormatter` (`B`). `[X-REF 03]`
1.20.16 Java 17: the `RandomGenerator` interface family and `RandomGeneratorFactory` (JEP 356),
        replacing the `java.util.Random`-only world. `[RESEARCH]`
1.20.17 Java 18: UTF-8 as the default charset (JEP 400) — the single most behaviour-changing library
        change of the decade for existing code. `[TRAP]` `[X-REF 03]`
1.20.18 Java 19/20: virtual threads, structured concurrency, record patterns and pattern switch all
        in preview or incubator — the "everything landed in 21" story starts here.
1.20.19 Java 21 sequenced collections (JEP 431): `SequencedCollection`, `SequencedSet`,
        `SequencedMap`, with `getFirst`, `getLast`, `addFirst`, `addLast`, `removeFirst`,
        `removeLast`, `reversed`, and on the map `putFirst`, `putLast`, `firstEntry`, `lastEntry`,
        `pollFirstEntry`, `pollLastEntry`, `sequencedKeySet`, `sequencedValues`,
        `sequencedEntrySet`. `[RESEARCH]` `[X-REF 02]`
1.20.20 The retrofit: `List` and `Deque` gain `SequencedCollection` as a superinterface;
        `LinkedHashSet` implements `SequencedSet`; `SortedSet` extends `SequencedSet`;
        `LinkedHashMap` implements `SequencedMap`; `SortedMap` extends `SequencedMap`.
        `[RESEARCH]` `[X-REF 02]`
1.20.21 `reversed()` returns a **view**, not a copy — writing through it writes through to the
        source. `[TRAP]` `[X-REF 02]`
1.20.22 `getFirst()` on an empty sequenced collection throws `NoSuchElementException`; it does not
        return null. `[TRAP]`
1.20.23 Java 21 smaller additions: `Math.clamp`, `StringBuilder.repeat`, `Character.isEmoji` and
        friends, `Thread.threadId()`, `Runtime.availableProcessors` container awareness.
        `[RESEARCH]`
1.20.24 Java 21 items named here only so you can place them: generational ZGC, the KEM API, the
        Vector API (sixth incubator), the FFM API (third preview). `[RESEARCH]` `[X-REF 06]`

*(24 leaves)*

---

**PART 1 total: 410 leaves**

---

# PART 2 — INTERMEDIATE

## §2.1 The master tables

2.1.1 **The master cost table**: every stream operation with per-element cost, allocation per stage,
      statefulness, buffering, and parallel behaviour — amortised and worst case split out. `[NUM]`
2.1.2 The master feature-by-version table: feature, JEP number, first preview, final release, what
      it replaced, and the one trap that comes with it.
2.1.3 The lambda vs anonymous class vs inner class vs method reference table: class files generated,
      allocations, capture semantics, `this`, startup cost, serialization, debuggability. `[NUM]`
2.1.4 The absence-representation table: `Optional`, `null`, an exception, an empty collection, a
      null object, a sentinel — with the case each is correct for.
2.1.5 The data-carrier table: record vs final class vs enum vs interface vs `Map<String,Object>`.
2.1.6 The concurrency-model table: platform threads, virtual threads, reactive, structured
      concurrency — throughput, latency, debuggability, backpressure, library support, team cost.
2.1.7 The list-factory table: `new ArrayList<>()`, `Arrays.asList`, `List.of`, `List.copyOf`,
      `Collectors.toList`, `Collectors.toUnmodifiableList`, `Stream.toList` — mutability, null
      policy, structural modification, set-in-place. `[TRAP]` `[NUM]` `[X-REF 02]`
2.1.8 The one-page "which construct" index for the whole topic, forward-referenced to §2.15.

*(8 leaves)*

## §2.2 Lambda cost and choice

2.2.1 Startup cost: the first execution of a lambda call site links an `invokedynamic` and spins a
      hidden class — hundreds of microseconds, once per site. `[NUM]` `[PROVE]`
2.2.2 Steady-state cost: after linking, invoking a lambda is an ordinary interface call and inlines
      like one. `[X-REF 06]`
2.2.3 A non-capturing lambda is instantiated **once** and cached in a static field of the spun
      class — the same object is returned every time. `[PROVE]` `[SOURCE]`
2.2.4 A capturing lambda allocates per evaluation; escape analysis usually scalar-replaces it, and
      "usually" is where the surprise lives. `[NUM]` `[X-REF 06]`
2.2.5 An anonymous class costs one class file per site, one allocation per instance, and a synthetic
      `this$0` reference to the enclosing instance. `[NUM]` `[X-REF 03]`
2.2.6 When an anonymous class is still the right answer: needing fields, needing more than one
      method, needing its own `this`, needing a name in a stack trace.
2.2.7 Lambda count and JVM startup: thousands of distinct lambdas measurably slow startup, and
      AppCDS/dynamic CDS archiving of the spun classes is the mitigation. `[RESEARCH]` `[NUM]`
      `[X-REF 06]`
2.2.8 Megamorphic call sites: a `Function` field assigned twenty different lambdas will not inline,
      and the pipeline slows by an order of magnitude. `[TRAP]` `[X-REF 06]`
2.2.9 Composition: `andThen`/`compose` on `Function`, `and`/`or`/`negate` on `Predicate`, and
      building a composite predicate by reducing a list with `Predicate::and`. `[BUILD]`
2.2.10 Currying and partial application in Java (`Function<A, Function<B, C>>`) and why it reads
       badly enough to avoid outside a DSL.
2.2.11 Checked exceptions in lambdas, workaround 1: a custom `@FunctionalInterface` that declares
       `throws E`. `[BUILD]`
2.2.12 Workarounds 2–4: an `unchecked(...)` adapter that wraps into a `RuntimeException`; the
       sneaky-throw generic cast; a `Result`/`Either` return type. Each with its cost. `[BUILD]`
       `[TRAP]` `[X-REF 03]`
2.2.13 Why `Stream` has no checked-exception story at all, and what that means for I/O inside a
       pipeline. `[TRAP]`
2.2.14 Testing behaviour expressed as a lambda: extract it to a named method or a named constant so
       it can be asserted on directly. `[X-REF 16]`

*(14 leaves)*

## §2.3 Streams: the cost model, and when not to use one

2.3.1 What a pipeline costs versus a `for` loop: the pipeline stage objects, the sink chain, the
      megamorphic dispatch, and the boxing. `[NUM]`
2.3.2 Where streams are effectively free: a monomorphic pipeline over an `ArrayList` that the JIT
      inlines end to end. `[NUM]` `[X-REF 06]`
2.3.3 Where they are not: primitive-heavy inner loops, collections of ten elements, deeply nested
      `flatMap`.
2.3.4 The allocation profile of a three-stage pipeline: how many objects exist before the first
      element flows. `[NUM]` `[PROVE]`
2.3.5 Debuggability: what a stream stack trace looks like, and why a breakpoint inside a lambda is
      not the same as a breakpoint inside a loop body. `[TRAP]`
2.3.6 Stack depth: a long pipeline plus recursion plus `flatMap` can `StackOverflowError` where the
      loop version would not. `[TRAP]`
2.3.7 Short-circuiting as the case where a stream genuinely beats the naive loop.
2.3.8 Ordering as optimisation: filter early, map late, and never `sorted()` before `limit()` when
      the comparator is expensive. `[PROVE]` `[NUM]`
2.3.9 `sorted().findFirst()` is O(n log n); `min(comparator)` is O(n). The same answer, different
      class of algorithm. `[PROVE]` `[NUM]` `[X-REF 01]`
2.3.10 `distinct()` cost, its memory profile, and its total dependence on a correct
       `equals`/`hashCode`. `[X-REF 02]` `[X-REF 03]`
2.3.11 Streaming a `LinkedList`: the spliterator reports no useful size and splits by batching, so
       both traversal and parallelism are poor. `[X-REF 02]`
2.3.12 Re-streaming inside a loop — the accidental O(n·m), and the fix (build a `Map` index once).
       `[TRAP]` `[NUM]`
2.3.13 Grouping in one pass versus collecting to a map and iterating it.
2.3.14 When to use a loop: side effects, early exit carrying several values, index arithmetic,
       in-place mutation, checked exceptions, and measured hot paths. `[TRAP]`
2.3.15 When to use a stream: transformation chains, grouping and aggregation, laziness over an
       expensive or infinite source, and one-line parallelism over a splittable source.
2.3.16 Readability rules that survive review: one operation per line, extract predicates to named
       methods, never nest a pipeline inside another pipeline's argument, name the intermediate
       collection when it clarifies.

*(16 leaves)*

## §2.4 Parallel streams

2.4.1 `.parallel()` / `.parallelStream()`: the pipeline becomes a ForkJoin task tree over the
      source `Spliterator`.
2.4.2 The shared `ForkJoinPool.commonPool()`, whose default parallelism is
      `availableProcessors() - 1` — because the submitting thread also participates. `[NUM]`
      `[PROVE]`
2.4.3 `-Djava.util.concurrent.ForkJoinPool.common.parallelism=N` as the only supported knob, and
      that it is process-global. `[RESEARCH]` `[NUM]`
2.4.4 Submitting the terminal operation to your own `ForkJoinPool` makes the stream use that pool —
      but this is emergent behaviour of `ForkJoinTask.fork`, not a documented API. `[TRAP]`
      `[RESEARCH]` `[PROVE]`
2.4.5 Blocking I/O inside a parallel stream starves the common pool for the entire JVM, including
      every other library that uses it. `[TRAP]`
2.4.6 The four preconditions for parallel to pay: large N, expensive per-element work, a cheaply
      splittable `SIZED`/`SUBSIZED` source, and no shared mutable state.
2.4.7 The N×Q heuristic: roughly 10 000 total "units of work" before the split/merge overhead is
      repaid. `[NUM]` `[RESEARCH]`
2.4.8 Source splitting quality, ranked: `int[]`/`ArrayList`/`IntStream.range` (excellent) →
      `HashMap`/`HashSet`/`TreeMap` (good but uneven) → `LinkedList`/`Files.lines`/
      `Stream.iterate`/`BufferedReader.lines` (effectively serial). `[NUM]` `[X-REF 02]`
2.4.9 Ordering costs: `limit`, `skip`, `findFirst` and `forEachOrdered` all force cross-task
      coordination on an ordered parallel stream. `[NUM]`
2.4.10 Merge cost: `toList` and `joining` both have O(n) combiners, and a bad combiner can dominate
       the whole run. `[PROVE]` `[NUM]`
2.4.11 Shared mutable state: `parallelStream().forEach(list::add)` corrupts the list — lost
       elements, nulls, or `ArrayIndexOutOfBoundsException` from inside `ArrayList.add`. `[TRAP]`
       `[PROVE]` `[X-REF 02]`
2.4.12 Collectors are safe because each leaf gets its own container and the combiner merges them —
       no shared state is ever touched. `[PROVE]`
2.4.13 `groupingByConcurrent` and the three conditions for it to actually reduce concurrently.
       `[SOURCE]`
2.4.14 Parallel streams inside a request thread, and the interaction with virtual threads: the
       common pool is still platform threads and still global. `[TRAP]`
2.4.15 Measuring: JMH with warm-up and a blackhole, never `System.nanoTime` around a cold loop.
       `[X-REF 06]` `[X-REF 16]`
2.4.16 The default answer in a server application: do not use parallel streams; use an executor you
       own and can size, name and monitor. `[TRAP]`

*(16 leaves)*

## §2.5 Collectors in anger

2.5.1 Multi-level grouping: `groupingBy(a, groupingBy(b, counting()))` and reading the resulting
      nested map type.
2.5.2 Downstream shaping: `mapping`, `filtering`, `flatMapping`, `collectingAndThen`, `reducing`.
2.5.3 `filtering(p, toList())` keeps empty groups; a `filter(p)` before `groupingBy` removes them —
      two different answers from code that looks equivalent. `[TRAP]` `[PROVE]`
2.5.4 Choosing the map implementation: `TreeMap::new` for order, `LinkedHashMap::new` for encounter
      order, `EnumMap::new` for enum keys. `[X-REF 02]`
2.5.5 `toMap` merge strategies: last-wins `(a, b) -> b`, first-wins `(a, b) -> a`, and combining
      `(a, b) -> a.merge(b)`.
2.5.6 Building an index and an inverted index in one pass each.
2.5.7 `teeing` for min-and-max, count-and-sum, or two independent aggregates in a single traversal.
2.5.8 A bounded top-N collector written with `Collector.of` over a `PriorityQueue`, with a correct
      combiner. `[BUILD]` `[X-REF 02]`
2.5.9 A boxing-free statistics collector over a `long[]` accumulator. `[BUILD]` `[NUM]`
2.5.10 Which characteristics to declare on a custom collector and what each unlocks.
2.5.11 Three ways to an immutable result — `toUnmodifiableList()`,
       `collectingAndThen(toList(), List::copyOf)`, and `Stream.toList()` — with three different
       null policies. `[TRAP]` `[NUM]`
2.5.12 Collectors that return `Optional`, and how to flatten that away with `collectingAndThen`.
2.5.13 Collecting into a record instead of a nested map — the readability upgrade that also gives
       you a name for the aggregate.
2.5.14 A `Collector` is a stateless factory of state, so a `static final Collector` field is safe to
       share across threads. `[PROVE]`

*(14 leaves)*

## §2.6 Optional discipline

2.6.1 The rule set in one place: return type only; never a field, parameter, collection element or
      map value; never null.
2.6.2 The chain style: `map`/`flatMap`/`filter`/`or`/`orElseGet`, never `isPresent` + `get`.
2.6.3 `orElse` vs `orElseGet` vs `orElseThrow`: the decision table, with the eager-evaluation cost
      spelled out. `[NUM]`
2.6.4 `ifPresentOrElse` for the genuine two-branch case.
2.6.5 `or(Supplier)` for a fallback lookup chain (cache → database → default).
2.6.6 `Optional` inside a stream: `.map(this::find).flatMap(Optional::stream)`.
2.6.7 Spring Data: `findById` returns `Optional`, `getReferenceById` returns a proxy and throws
      later — a different contract with the same shape. `[TRAP]` `[X-REF 08]`
2.6.8 Jackson: serialising an `Optional` field without the `Jdk8Module` produces
      `{"present":true}`; with it, the unwrapped value or `null`. `[TRAP]` `[RESEARCH]`
2.6.9 `Optional` as a builder argument or a constructor parameter: the anti-pattern, and the
      overload alternative. `[TRAP]`
2.6.10 The four absence strategies compared: `Optional`, nullability annotations
       (`@Nullable`/`@NonNull` + NullAway), the null-object pattern, and an exception. `[X-REF 03]`
2.6.11 `Optional.of(1).equals(Optional.of(1))` is true (it delegates to the value's `equals`);
       `Optional.empty().equals(null)` is false. `[PROVE]`
2.6.12 `Optional` in a hot loop: one allocation per call, why the JIT usually removes it, and how to
       confirm with an allocation profiler. `[NUM]` `[X-REF 06]`

*(12 leaves)*

## §2.7 `var` in practice

2.7.1 A style policy you can defend in review: use `var` when the initialiser already names the
      type, and only then.
2.7.2 `var` with builders and fluent chains, where the type is both long and obvious.
2.7.3 `var` with try-with-resources.
2.7.4 `var` in an enhanced-`for` over `Map.Entry<K, V>` — the single biggest readability win.
2.7.5 `var` for deeply generic types (`Map<String, List<Map<String, Integer>>>`).
2.7.6 `var` and the interface-versus-implementation question: the local's static type becomes the
      concrete class, which changes what compiles later. `[TRAP]` `[PROVE]`
2.7.7 `var` and numeric literals: `var total = 0` is an `int` accumulator, and the overflow is
      yours. `[TRAP]` `[NUM]` `[X-REF 03]`
2.7.8 `var` in lambda parameters: only worth it for an annotation.
2.7.9 `var` and refactoring: changing a method's return type silently retypes every `var` local —
      sometimes a compile error where you want one, sometimes a behaviour change where you do not.
      `[TRAP]`
2.7.10 Team conventions, and why both "never use var" and "always use var" fail the style guide's
       own test.

*(10 leaves)*

## §2.8 Records in practice

2.8.1 Records as request/response DTOs at an HTTP boundary, with the validated compact constructor.
      `[X-REF 12]`
2.8.2 Records with Jackson: the canonical constructor is used from 2.12 onward; `@JsonProperty` on
      components; `@JsonCreator` when parameter names are unavailable. `[TRAP]` `[RESEARCH]`
2.8.3 `-parameters` as a compile flag: what stops working without it (Spring constructor binding,
      Jackson name inference, some validation messages). `[X-REF 07]`
2.8.4 Records with Bean Validation: the annotation must have a `@Target` including
      `RECORD_COMPONENT` or `PARAMETER`/`FIELD` for it to land where the validator looks. `[TRAP]`
      `[RESEARCH]`
2.8.5 Records with Spring: `@ConfigurationProperties` constructor binding, `@RequestBody`,
      and the limits with `@ModelAttribute` form binding. `[RESEARCH]` `[X-REF 07]`
2.8.6 Records with JPA: not entities (no no-arg constructor, no proxying, no dirty checking), not
      `@Embeddable` for the same reason — but excellent as JPQL constructor-expression projections
      and Spring Data DTO projections. `[TRAP]` `[X-REF 08]`
2.8.7 Records as compound map keys: correct `equals`/`hashCode` for free, which is the whole
      problem with hand-written keys. `[X-REF 02]`
2.8.8 Records as multiple return values, replacing an out-parameter, an array, or a `Pair`.
2.8.9 Local records as scratch types inside a stream pipeline — declare, use, discard.
2.8.10 The "wither" pattern: hand-written `withX` methods returning a new instance, and the fact
       that derived record creation is still not a language feature. `[RESEARCH]`
2.8.11 Builders for records with many components, and when the builder earns its boilerplate.
2.8.12 Records and inheritance: a sealed interface for the family, composition for the shared state.
2.8.13 Defensive copying, done properly: copy-in in the compact constructor and copy-out in the
       accessor for arrays. `[BUILD]`
2.8.14 Records versus Lombok `@Value`: what each generates, and what a record gives that Lombok
       cannot (pattern deconstruction, the `Record` attribute, serialization through the
       constructor). `[RESEARCH]`
2.8.15 Floating-point components: `Double.equals` semantics inside a record mean `NaN` matches and
       `-0.0` does not — a real bug in a price or coordinate type. `[TRAP]` `[PROVE]`
2.8.16 Migrating an existing value class to a record: the checklist, and the four things that block
       it (mutability, inheritance, a hidden representation, a framework requiring a no-arg
       constructor).

*(16 leaves)*

## §2.9 Sealed types and data-oriented programming

2.9.1 Algebraic data types in Java: sealed types are the sum, records are the product.
2.9.2 Data-oriented programming as Brian Goetz frames it: model data as immutable data, keep
      behaviour separate, make illegal states unrepresentable, use exhaustive pattern matching.
      `[RESEARCH]`
2.9.3 The Visitor pattern replaced by a sealed interface plus a pattern switch — with the line
      count and the coupling comparison. `[PROVE]`
2.9.4 The expression problem: sealed hierarchies make adding *operations* easy and adding *cases*
      loud; open polymorphic hierarchies do the exact opposite. Pick per axis of change. `[PROVE]`
2.9.5 A state machine as a sealed interface of records, with transitions as a pattern switch.
2.9.6 A result type: `sealed interface Result<T> permits Ok, Err` and why it beats an exception for
      expected failures. `[X-REF 03]`
2.9.7 A parse tree, a protocol message set, and a domain event stream — the three canonical shapes.
2.9.8 Sealed types across a published API boundary: exhaustiveness becomes a compatibility promise
      you cannot take back. `[TRAP]`
2.9.9 When an enum is better (no per-case data), and when open polymorphism is better (third
      parties must extend). `[TRAP]`
2.9.10 One worked domain model combining sealed interfaces, records, pattern switch and text blocks.
2.9.11 Testing exhaustiveness: the test is that it compiles; there is nothing to assert. `[X-REF 16]`
2.9.12 Serialising a sealed hierarchy: Jackson polymorphic typing with `@JsonTypeInfo` /
       `@JsonSubTypes`, and the security caveat on `DefaultTyping`. `[RESEARCH]` `[X-REF 13]`

*(12 leaves)*

## §2.10 Pattern matching in anger

2.10.1 Refactoring an `if`/`else if` chain of `instanceof` + cast into a pattern switch, step by
       step.
2.10.2 Replacing getter-plus-condition code with record deconstruction.
2.10.3 Guards versus nested switches: which one the dominance rules make readable.
2.10.4 Naming the total pattern instead of writing `default`, so the case is documented.
2.10.5 Handling `null` explicitly at the top of a switch, and when `case null, default ->` is right.
2.10.6 Pattern matching over a JSON-shaped sealed model (`JsonValue` → `JsonObject`, `JsonArray`,
       `JsonString`, `JsonNumber`, `JsonNull`).
2.10.7 Pattern matching inside a stream: a switch expression as the body of a `map`.
2.10.8 A pattern switch **statement** over a non-sealed type still requires a `default`. `[TRAP]`
2.10.9 Migration risk: adding a permitted subtype breaks downstream compilation, and recompiling
       only one side produces `MatchException` or `IncompatibleClassChangeError` at runtime.
       `[TRAP]` `[PROVE]`
2.10.10 Performance: a pattern switch compiles to a single `invokedynamic` `typeSwitch` returning an
        index, not a chain of `instanceof` tests. `[PROVE]`
2.10.11 The readability limit: three levels of nested deconstruction is where it stops helping.
2.10.12 Testing a pattern switch across every permitted subclass, driven by
        `getPermittedSubclasses()`. `[X-REF 16]`

*(12 leaves)*

## §2.11 Text blocks in practice

2.11.1 SQL in a text block — and why you still bind parameters rather than interpolating.
       `[X-REF 13]` `[X-REF 09]`
2.11.2 JSON fixtures in tests, with `.formatted(...)` for the varying parts. `[X-REF 16]`
2.11.3 Regex in a text block: `\` is still an escape, so every pattern backslash doubles. `[TRAP]`
2.11.4 HTML, GraphQL and YAML payloads, and the indentation discipline each needs.
2.11.5 Trailing-newline discipline when comparing a text block against a file's contents. `[TRAP]`
2.11.6 Text blocks in annotations and `case` labels, because they are constant expressions.
2.11.7 There is no interpolation in Java 21: `formatted`, `MessageFormat`, or a template library.
       String templates were previewed in 21 and 22 and then **withdrawn** in 23. `[VERSION-TRAP]`
       `[RESEARCH]`
2.11.8 When a text block is worse than a resource file: anything a non-Java tool should be able to
       lint, format or diff.

*(8 leaves)*

## §2.12 Virtual threads in production

2.12.1 The thread-per-request model restored: what actually changes in a Spring Boot service.
       `[X-REF 07]`
2.12.2 `spring.threads.virtual.enabled=true` (Spring Boot 3.2+) and what it switches — the servlet
       container's executor and `@Async`, but not everything you might assume. `[RESEARCH]`
       `[X-REF 07]`
2.12.3 Tomcat and Jetty virtual-thread executors: `maxThreads` stops being the concurrency cap,
       which means it stops being the accidental rate limiter. `[TRAP]`
2.12.4 Losing the pool means losing the queue: add a `Semaphore`, a bounded queue, or a
       rate limiter deliberately. `[TRAP]` `[X-REF 05]`
2.12.5 The new bottleneck is downstream: the JDBC connection pool, the HTTP client's connection
       limit, the database's max connections. Size them on purpose. `[TRAP]` `[X-REF 08]`
2.12.6 Drivers and libraries that use `synchronized` internally pin on Java 21 — JDBC drivers are
       the common offender. `[TRAP]` `[RESEARCH]`
2.12.7 Libraries with `ThreadLocal` caches or their own thread pools built on the assumption that
       threads are expensive.
2.12.8 Logging and MDC: MDC is a `ThreadLocal`, so it still works, but the copy cost is now per
       task. Scoped values are the eventual answer. `[X-REF 20]`
2.12.9 Thread dumps: `jcmd <pid> Thread.dump_to_file -format=json <file>` includes virtual threads
       and the structured-concurrency tree; `jstack` does not show them. `[TRAP]` `[RESEARCH]`
2.12.10 JFR events: `jdk.VirtualThreadStart` and `jdk.VirtualThreadEnd` (disabled by default),
        `jdk.VirtualThreadPinned` (enabled, 20 ms threshold), `jdk.VirtualThreadSubmitFailed`
        (enabled). `[NUM]` `[RESEARCH]` `[X-REF 20]`
2.12.11 Metrics: what a "live threads" gauge means now, and what to measure instead (in-flight
        requests, semaphore permits, pool saturation). `[X-REF 20]`
2.12.12 Memory sizing: a million virtual threads is a heap question, not a stack question. `[NUM]`
        `[X-REF 06]`
2.12.13 Debugging: breakpoints work, stepping across a mount boundary works, but the debugger's
        thread list becomes useless at scale.
2.12.14 CPU-bound work still needs a bounded executor sized to the cores. `[TRAP]`
2.12.15 The migration checklist: audit `synchronized` around blocking calls, audit `ThreadLocal`
        caches, resize downstream pools, add explicit backpressure, name your threads.
2.12.16 When not to migrate: an application that never approaches ten thousand concurrent tasks
        will see no benefit — the JDK's own guidance. `[SOURCE]`
2.12.17 Virtual threads versus reactive (WebFlux/Reactor): you regain stack traces, debuggers,
        profilers and straight-line code; you still lack declarative backpressure and operator
        fusion. `[X-REF 07]`
2.12.18 Virtual threads and `CompletableFuture`: composition is still useful, and the executor
        behind it is now cheap. `[X-REF 05]`

*(18 leaves)*

## §2.13 Structured concurrency and scoped values in practice

2.13.1 The fan-out call: two remote lookups, one deadline, one failure policy, one return.
2.13.2 Hedged requests with `ShutdownOnSuccess` against two replicas.
2.13.3 Timeouts: `joinUntil(Instant)` for the scope versus per-subtask timeouts inside each task.
2.13.4 Error handling: which exception surfaces from `throwIfFailed()`, and how to see the others
       via each `Subtask.exception()`.
2.13.5 Nesting scopes, and what the resulting task tree looks like in a JSON thread dump.
       `[RESEARCH]`
2.13.6 Scoped values for request context — tenant, principal, trace id — instead of `ThreadLocal`.
       `[X-REF 20]`
2.13.7 Rebinding: a scoped value is immutable within its scope, and a nested `where` shadows rather
       than mutates. `[PROVE]`
2.13.8 Scoped values are inherited by subtasks forked in a `StructuredTaskScope`, which is what
       makes the pair usable together. `[RESEARCH]`
2.13.9 Preview risk: the API changed in every release from 19 to 26 — do not expose it in a library
       signature. `[TRAP]` `[RESEARCH]`
2.13.10 What to actually say in an interview: name the guarantee (subtasks cannot outlive the
        block), name the comparison (`allOf` leaves orphans), name the status (preview on 21,
        reworked in 25).

*(10 leaves)*

## §2.14 Migration, 8 → 21

2.14.1 What breaks at 9: strong encapsulation of JDK internals, split packages, and the
       `--illegal-access` escape hatch that was removed in 17. `[X-REF 03]` `[X-REF 06]`
2.14.2 What breaks at 11: `java.xml.bind`, `java.activation`, CORBA and the other Java EE modules
       are gone; the `javax` → `jakarta` rename is a separate, later axis. `[RESEARCH]`
2.14.3 What breaks at 16: strong encapsulation on by default, so reflective access into
       `java.base` needs `--add-opens`. `[X-REF 06]`
2.14.4 What breaks at 17: `strictfp` becomes a no-op, the Security Manager is deprecated, and
       illegal reflective access is denied. `[X-REF 03]`
2.14.5 What breaks at 18: the default charset becomes UTF-8, so `new FileReader(f)`,
       `String.getBytes()` and `PrintStream` change behaviour silently on a non-UTF-8 platform.
       `[TRAP]` `[X-REF 03]`
2.14.6 What breaks at 21: pattern-switch exhaustiveness for previously-compiling code, and
       sequenced-collection method-name clashes for classes that already declare `getFirst`,
       `reversed` or `putFirst`. `[TRAP]` `[RESEARCH]` `[X-REF 02]`
2.14.7 The library floor: Lombok, Mockito, ByteBuddy, ASM, Groovy and Spring each have a hard
       minimum version per JDK, and bytecode-manipulating libraries fail loudest. `[X-REF 16]`
2.14.8 The mechanical refactors worth doing: anonymous class → lambda, manual loops building strings
       → `Collectors.joining`, `Date`/`Calendar` → `java.time`, `if`/`else instanceof` → pattern
       switch, hand-written value classes → records.
2.14.9 The refactors not worth doing: rewriting every loop as a stream, adopting `var` everywhere,
       converting working DTOs to records for their own sake. `[TRAP]`
2.14.10 Toolchain: `--release`, `jdeps --jdk-internals`, `jdeprscan`, and the Maven/Gradle toolchain
        declaration. `[X-REF 17]`
2.14.11 The safe rollout order: run on the new JDK with the old `--release` first, then raise the
        language level, then adopt features.
2.14.12 Performance changes to check on the way through: G1 defaults, string deduplication, compact
        strings, JIT and GC behaviour changes. `[X-REF 06]`
2.14.13 The deprecated-for-removal watch list relevant to this guide: finalization, the Security
        Manager, `sun.misc.Unsafe` memory access, the 32-bit x86 port. `[X-REF 03]`
2.14.14 A "which JDK does my team actually run" checklist, because every version-specific claim in
        an interview must be dated.

*(14 leaves)*

## §2.15 Which construct

2.15.1 Lambda, method reference, or anonymous class?
2.15.2 Stream or loop?
2.15.3 Parallel stream, your own executor, or virtual threads?
2.15.4 `Optional`, `null`, an exception, or an empty collection?
2.15.5 Record, final class, enum, or interface?
2.15.6 Sealed interface, enum, or open polymorphism?
2.15.7 Pattern switch or virtual dispatch?
2.15.8 Text block, resource file, or constant?
2.15.9 Virtual thread, platform thread, or reactive?
2.15.10 Structured concurrency, `CompletableFuture`, or `invokeAll`?

*(10 leaves)*

---

**PART 2 total: 190 leaves**

---

# PART 3 — UNDER THE HOOD

## §3.1 Lambda translation

3.1.1 `javac` desugars the lambda body into a private synthetic method named
      `lambda$<enclosingMethod>$<n>`. `[SOURCE]` `[BYTECODE]` `[RESEARCH]`
3.1.2 That method is `static` when the lambda does not capture `this`, and an instance method when
      it does. `[PROVE]` `[BYTECODE]`
3.1.3 The call site becomes `invokedynamic` with `LambdaMetafactory.metafactory` as the bootstrap
      method. `[BYTECODE]` `[SOURCE]`
3.1.4 `metafactory`'s six parameters: `MethodHandles.Lookup caller`, `String interfaceMethodName`,
      `MethodType factoryType`, `MethodType interfaceMethodType`, `MethodHandle implementation`,
      `MethodType dynamicMethodType`. `[SOURCE]` `[RESEARCH]`
3.1.5 `altMetafactory` and its flags: `FLAG_SERIALIZABLE = 1`, `FLAG_MARKERS = 2`,
      `FLAG_BRIDGES = 4`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.1.6 Static versus dynamic argument lists: the static arguments live in the constant pool; the
      captured values are the dynamic arguments pushed onto the operand stack at capture time.
      `[SOURCE]` `[RESEARCH]`
3.1.7 Therefore `factoryType`'s return type is the functional interface, and its parameter types are
      exactly the captured values — reading the `invokedynamic` descriptor tells you what was
      captured. `[PROVE]` `[BYTECODE]`
3.1.8 `InnerClassLambdaMetafactory` spins a class implementing the interface at first linkage.
      `[SOURCE]` `[RESEARCH]`
3.1.9 Since Java 15 that class is a **hidden class** (JEP 371), which replaced
      `Unsafe.defineAnonymousClass`. `[RESEARCH]` `[VERSION-TRAP]`
3.1.10 Non-capturing lambda: the spun class holds a single instance in a static field and the
       bootstrap returns a `ConstantCallSite` over it — one allocation for the life of the JVM.
       `[PROVE]` `[SOURCE]`
3.1.11 Capturing lambda: the spun class gets one field per captured value plus a constructor, and
       the `CallSite` target is that constructor — one allocation per evaluation. `[PROVE]`
3.1.12 Why not inner classes: separating the binary form (an `invokedynamic` recipe) from the
       runtime strategy lets the JDK change the strategy — to hidden classes, to Valhalla, to
       whatever — without changing a single class file. `[SOURCE]` `[RESEARCH]`
3.1.13 What that choice costs: first-call linkage latency and a JVM startup profile that is
       sensitive to the number of distinct lambda call sites. `[NUM]`
3.1.14 A method reference skips the `lambda$` method entirely — `implementation` is a direct method
       handle to the referenced method. `[BYTECODE]` `[PROVE]`
3.1.15 Serializable lambdas: the compiler emits a `$deserializeLambda$` synthetic method, capture is
       recorded in a `SerializedLambda`, and the whole path is slow, reflective, and refactoring-
       fragile. `[SOURCE]` `[TRAP]` `[RESEARCH]`
3.1.16 Bridge methods: `FLAG_BRIDGES` exists for functional interfaces that inherit generic bridge
       methods, so the spun class implements all of them. `[RESEARCH]` `[X-REF 03]`
3.1.17 Reading it yourself: `javap -c -p` on a class containing one capturing and one non-capturing
       lambda, with the `BootstrapMethods` attribute read line by line. `[BYTECODE]`
3.1.18 The runtime class name — `Foo$$Lambda/0x0000000801…` since Java 21, `Foo$$Lambda$1` before
       it — and what it tells you in a stack trace, a heap dump, or a `getClass().getName()` log.
       `[RESEARCH]` `[VERSION-TRAP]`

*(18 leaves)*

## §3.2 Lambda capture and identity

3.2.1 Capture is by value: the captured value is copied into a field of the spun instance. `[PROVE]`
3.2.2 Effectively-final is required precisely so the copy can never diverge from the original.
      `[PROVE]` `[X-REF 03]`
3.2.3 Reading an instance field inside a lambda captures `this`, not the field — so the lambda sees
      later writes to the field. `[PROVE]` `[TRAP]`
3.2.4 A lambda stored in a long-lived structure that captures `this` keeps the whole enclosing
      object alive — the listener-registry leak, identical to the anonymous-class one. `[TRAP]`
      `[PROVE]` `[X-REF 03]` `[X-REF 06]`
3.2.5 Identity: two evaluations of the same non-capturing lambda expression yield the same object;
      two evaluations of a capturing one usually do not. The specification promises **neither**.
      `[TRAP]` `[SOURCE]`
3.2.6 Consequently `==` on lambdas is meaningless, and `removeListener(x -> ...)` never removes
      anything. `[TRAP]` `[PROVE]`
3.2.7 `equals` and `hashCode` on a lambda are `Object`'s — identity based.
3.2.8 `toString()` on a lambda is `Foo$$Lambda/0x...@1b6d3586` — useless in a log, so log the intent
      instead. `[TRAP]`
3.2.9 Reflection on a lambda: `getClass().getInterfaces()` works, the implementing method does not
      appear where you expect, and there is no supported way to recover the source form.
3.2.10 The JIT: a monomorphic lambda call site inlines through the interface call; a
       lambda-heavy pipeline that goes megamorphic deoptimises and stays slow. `[X-REF 06]`

*(10 leaves)*

## §3.3 Stream pipeline internals

3.3.1 The class hierarchy: `BaseStream` → `Stream`/`IntStream`/`LongStream`/`DoubleStream`;
      `AbstractPipeline` → `ReferencePipeline`/`IntPipeline`/`LongPipeline`/`DoublePipeline`.
      `[SOURCE]`
3.3.2 `AbstractPipeline`'s fields, verbatim: `sourceStage`, `previousStage`, `sourceOrOpFlags`,
      `nextStage`, `depth`, `combinedFlags`, `sourceSpliterator`, `sourceSupplier`,
      `linkedOrConsumed`, `sourceAnyStateful`, `sourceCloseAction`, `parallel`. `[SOURCE]`
      `[RESEARCH]`
3.3.3 Every intermediate operation allocates exactly one new pipeline stage object, doubly linked to
      the previous — that is the cost of building a pipeline before any element moves. `[NUM]`
      `[PROVE]`
3.3.4 `ReferencePipeline.StatelessOp` and `ReferencePipeline.StatefulOp` as the two op base classes.
      `[SOURCE]`
3.3.5 `Sink<T> extends Consumer<T>` with `begin(long size)`, `accept(T)`, `cancellationRequested()`,
      `end()` — the four-method protocol that makes fusion and short-circuiting possible.
      `[SOURCE]`
3.3.6 `Sink.ChainedReference` as the standard downstream-forwarding base class. `[SOURCE]`
3.3.7 `opWrapSink(int flags, Sink downstream)` is where each operation's behaviour actually lives;
      `map`'s is a one-line `accept` that calls the mapper and forwards. `[SOURCE]` `[PROVE]`
3.3.8 `wrapSink` walks **backwards** from the terminal stage to depth 0, wrapping each stage's sink
      around the one after it. `[SOURCE]` `[PROVE]`
3.3.9 `copyInto(sink, spliterator)`: `begin`, `forEachRemaining`, `end` — and
      `copyIntoWithCancel` when the pipeline can short-circuit. `[SOURCE]`
3.3.10 `evaluate(TerminalOp)`: assert the shape, set `linkedOrConsumed`, then dispatch to
       `evaluateSequential` or `evaluateParallel`. `[SOURCE]`
3.3.11 That is the entire fusion story: one sink chain, one traversal, no intermediate collections.
       `[PROVE]`
3.3.12 `linkedOrConsumed` and its two messages — `"stream has already been operated upon or
       closed"` and `"source already consumed or closed"` — verbatim from the source. `[SOURCE]`
3.3.13 `StreamOpFlag`: the `DISTINCT`/`SORTED`/`ORDERED`/`SIZED`/`SHORT_CIRCUIT` bit set, each with
       SET/CLEAR/PRESERVE encodings across the stream, op and terminal-op positions. `[SOURCE]`
       `[NUM]` `[RESEARCH]`
3.3.14 How the flags let `count()` skip the pipeline: `SIZED` survives, no stateful op cleared it,
       nothing short-circuits — so the answer is the source's size. `[PROVE]` `[SOURCE]`
3.3.15 That is exactly why `peek` may never run, and exactly why the behaviour changed in Java 9.
       `[PROVE]` `[VERSION-TRAP]`
3.3.16 `sorted()` is a no-op when `SORTED` is already set with the same comparator. `[PROVE]`
       `[SOURCE]`
3.3.17 `distinct()` on a `SORTED` stream uses adjacent comparison instead of a `HashSet`. `[PROVE]`
       `[SOURCE]`
3.3.18 Lazy source binding: `sourceSupplier` versus `sourceSpliterator`, late binding, and the
       interference window that makes `ConcurrentModificationException` a terminal-time event.
       `[PROVE]` `[X-REF 02]`
3.3.19 Closing: `sourceCloseAction`, `onClose`, and the composed close chain across concatenated
       streams.
3.3.20 The file map of `java.util.stream` — about forty classes, and the five worth actually reading
       (`AbstractPipeline`, `ReferencePipeline`, `Sink`, `StreamOpFlag`, `ReduceOps`). `[RESEARCH]`

*(20 leaves)*

## §3.4 `Spliterator`

3.4.1 The interface: `tryAdvance`, `forEachRemaining`, `trySplit`, `estimateSize`,
      `getExactSizeIfKnown`, `characteristics`, `hasCharacteristics`, `getComparator`. `[SOURCE]`
3.4.2 The eight characteristics with their bit values: `ORDERED 0x10`, `DISTINCT 0x01`,
      `SORTED 0x04`, `SIZED 0x40`, `NONNULL 0x100`, `IMMUTABLE 0x400`, `CONCURRENT 0x1000`,
      `SUBSIZED 0x4000`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.3 `SIZED` versus `SUBSIZED`: a balanced tree reports `SIZED` (the total is known) but not
      `SUBSIZED` (the subtree sizes are not) — the javadoc's own example. `[SOURCE]` `[PROVE]`
      `[RESEARCH]`
3.4.4 `trySplit` returns null when splitting is impossible or not worthwhile, and the returned
      spliterator covers the **prefix**. `[SOURCE]`
3.4.5 `ArrayList`'s spliterator: index-range halving, `ORDERED | SIZED | SUBSIZED` — the ideal
      parallel source. `[SOURCE]` `[X-REF 02]`
3.4.6 `HashMap`'s spliterator: splits over ranges of the bucket table, `SIZED` but with unevenly
      populated halves. `[X-REF 02]`
3.4.7 `LinkedList`'s spliterator: batch-based with a doubling batch size, never `SUBSIZED`, so
      parallelism is nearly worthless. `[NUM]` `[SOURCE]` `[X-REF 02]`
3.4.8 `IteratorSpliterator` and `Spliterators.spliteratorUnknownSize` use the same batching
      fallback — this is why any `Iterator`-derived stream parallelises badly. `[NUM]`
3.4.9 `Files.lines`' spliterator and why line-oriented file input is effectively serial.
3.4.10 Late-binding spliterators and the exact window in which a concurrent modification is
       detectable. `[X-REF 02]`
3.4.11 `Spliterators.AbstractSpliterator` and `AbstractIntSpliterator` as bases for a hand-written
       one. `[BUILD]`
3.4.12 Writing a spliterator that splits well: implement `trySplit` genuinely and report
       `SIZED | SUBSIZED`. `[BUILD]` `[PROVE]`
3.4.13 `Spliterator.OfInt`/`OfLong`/`OfDouble` and the primitive traversal path.
3.4.14 The characteristics-to-optimisation map: which stream optimisation each characteristic
       unlocks, and which operation clears it. `[PROVE]`

*(14 leaves)*

## §3.5 Parallel execution internals

3.5.1 `AbstractTask`: a `CountedCompleter` that recursively splits the spliterator until each leaf
      is below a target size. `[SOURCE]`
3.5.2 `suggestTargetSize(sizeEstimate)` = `sizeEstimate / LEAF_TARGET`, rounded up — aiming at
      roughly four tasks per core. `[NUM]` `[PROVE]` `[RESEARCH]`
3.5.3 `LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2`. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.5.4 The op implementations: `ForEachOps`, `ReduceOps`, `FindOps`, `MatchOps`, `SliceOps`,
      `SortedOps`, `DistinctOps`, `WhileOps`, `Nodes`. `[SOURCE]`
3.5.5 `ReduceTask`: accumulate per leaf into a local container, then combine pairwise up the tree —
      which is why the combiner's cost is O(log n) merges of growing size. `[PROVE]` `[NUM]`
3.5.6 `ForEachTask` versus `ForEachOrderedTask`: the ordered variant buffers completed subtrees to
      restore encounter order. `[PROVE]` `[NUM]`
3.5.7 `SliceOps` (`limit`/`skip`) on an ordered parallel stream must count in order, so it cannot
      simply discard work. `[PROVE]`
3.5.8 `Nodes` and the flat/conc-tree node structures used to accumulate parallel results before
      flattening into an array. `[SOURCE]` `[NUM]`
3.5.9 The common pool: `ForkJoinPool.commonPool()`, parallelism `availableProcessors() - 1`, plus
      the submitting thread, so effective width equals the core count. `[NUM]` `[PROVE]`
3.5.10 Common-pool threads are daemon threads and the pool is never shut down; a task left running
       at exit is simply abandoned. `[RESEARCH]` `[TRAP]`
3.5.11 Work stealing: each worker owns a deque, pushes and pops at its own head, and steals from the
       tail of another. `[X-REF 05]`
3.5.12 `ForkJoinPool.ManagedBlocker` as the sanctioned way to block inside a ForkJoin worker, and
       the fact that parallel streams do not use it for you. `[RESEARCH]` `[X-REF 05]`
3.5.13 Exception propagation: the first exception to reach the joining task wins; the rest are
       discarded. `[TRAP]` `[PROVE]`
3.5.14 A parallel stream inside a parallel stream's lambda: nested tasks on the same pool, the
       starvation shape, and the rare true deadlock. `[TRAP]` `[PROVE]`

*(14 leaves)*

## §3.6 Collector internals

3.6.1 `Collectors.CollectorImpl<T, A, R>`: a small private class holding the five functions plus the
      characteristics set. `[SOURCE]`
3.6.2 The pre-built characteristic sets: `CH_CONCURRENT_ID`, `CH_CONCURRENT_NOID`, `CH_ID`,
      `CH_UNORDERED_ID`, `CH_UNORDERED_NOID`, `CH_NOID`. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.6.3 `toList()`'s three functions: `ArrayList::new`, `List::add`, and a combiner that `addAll`s the
      right into the left. `[SOURCE]` `[PROVE]`
3.6.4 The combiner is O(size of the right half) at every merge, so parallel `collect` pays an
      O(n) copy overall — which is why it needs a large N to win. `[NUM]` `[PROVE]`
3.6.5 `groupingBy`'s implementation: a `HashMap`, `computeIfAbsent` for the container, and the
      downstream accumulator applied to it. `[SOURCE]`
3.6.6 `groupingBy`'s finisher when the downstream has one: an in-place rewrite of every map value
      through an unchecked cast — the reason the intermediate type `A` is not the result type `R`.
      `[SOURCE]` `[PROVE]`
3.6.7 `summingDouble` and `averagingDouble` accumulate into a three-element `double[]` using Kahan
      compensated summation, then add the compensation back at the end. `[SOURCE]` `[NUM]`
      `[PROVE]` `[RESEARCH]` `[X-REF 03]`
3.6.8 `averagingInt`/`summingInt` accumulate into a `long[]`, so no compensation is needed. `[SOURCE]`
3.6.9 `joining()`'s combiner appends one `StringBuilder` to another — O(n) per merge, O(n log n)
      across the tree. `[PROVE]` `[NUM]`
3.6.10 Why `IDENTITY_FINISH` matters: the framework skips the finisher entirely and returns the
       accumulation container itself, saving a full pass. `[PROVE]` `[SOURCE]`

*(10 leaves)*

## §3.7 `Optional` internals

3.7.1 The class: `public final class Optional<T>` with a single `private final T value` field and a
      `private static final Optional<?> EMPTY`. `[SOURCE]`
3.7.2 Annotated `@jdk.internal.ValueBased`, which is where the "do not synchronize, do not depend on
      identity" warnings come from. `[SOURCE]` `[RESEARCH]` `[X-REF 03]`
3.7.3 `Optional.empty()` returns the shared `EMPTY`, so `Optional.empty() == Optional.empty()` is
      true — and relying on that is exactly the identity dependence the annotation forbids.
      `[PROVE]` `[TRAP]`
3.7.4 `map` is `isEmpty() ? empty() : Optional.ofNullable(mapper.apply(value))` — one line that
      explains the null-mapper behaviour. `[SOURCE]` `[PROVE]`
3.7.5 `get()` and `orElseThrow()` have identical bodies; `get` was very nearly deprecated and was
      kept only for compatibility. `[SOURCE]` `[RESEARCH]`
3.7.6 Memory: a 16-byte object plus the reference field; escape analysis removes it in an inlined
      chain and does not when the chain is megamorphic or crosses a non-inlined boundary. `[NUM]`
      `[X-REF 06]`
3.7.7 Not `Serializable` by design, and the value-based contract means a future Valhalla value class
      can replace it without changing semantics. `[PROVE]`
3.7.8 Valhalla: `Optional` as a value class removes the allocation entirely; that is the stated
      plan, and it is the honest answer to "isn't Optional slow?". `[RESEARCH]` `[X-REF 06]`

*(8 leaves)*

## §3.8 `var` and inference internals

3.8.1 `javac` takes the initialiser's **standalone** type and then applies *upward projection* to
      remove non-denotable capture variables. `[RESEARCH]` `[PROVE]`
3.8.2 The inferred type is written into `LocalVariableTable`/`LocalVariableTypeTable` and nowhere
      else — `var` leaves no other trace in the class file. `[BYTECODE]` `[PROVE]`
3.8.3 Why `var` cannot be a field or parameter type: separate compilation would make a signature
      depend on an initialiser that is not part of the signature. `[PROVE]`
3.8.4 Upward projection worked through: `var x = list.get(0)` where `list` is `List<? extends
      Number>` infers `Number`, not the capture variable. `[RESEARCH]` `[PROVE]`
3.8.5 Poly expressions have no standalone type, which is the formal reason a lambda or method
      reference cannot initialise a `var`. `[PROVE]`
3.8.6 `var` with an anonymous class initialiser infers the anonymous type, so its extra members are
      callable — a rare legitimate use of a type you cannot write. `[PROVE]`
3.8.7 Diamond inference with no target type resolves to `Object`, which is why
      `var l = new ArrayList<>()` is `ArrayList<Object>`. `[PROVE]` `[TRAP]`
3.8.8 Surfacing the inferred type: IDE inlay hints, `javap -l`, and `-Xlint` where it applies.

*(8 leaves)*

## §3.9 Record internals

3.9.1 The class file gains a `Record` attribute containing one `record_component_info` per
      component: name index, descriptor index, and its own attributes (`Signature`,
      `RuntimeVisibleAnnotations`, `RuntimeVisibleTypeAnnotations`). `[SOURCE]` `[RESEARCH]`
3.9.2 The generated accessors are ordinary public methods; the backing fields are `private final`.
      `[BYTECODE]`
3.9.3 `equals`, `hashCode` and `toString` are emitted as `invokedynamic` to
      `java.lang.runtime.ObjectMethods.bootstrap`. `[SOURCE]` `[BYTECODE]` `[RESEARCH]`
3.9.4 `ObjectMethods.bootstrap`'s static arguments: the record class, a semicolon-separated
      component-name string, and one `MethodHandle` getter per component. `[SOURCE]` `[RESEARCH]`
3.9.5 Why `invokedynamic` rather than inline bytecode: smaller class files, and the JDK retains the
      right to change the algorithm. `[PROVE]`
3.9.6 The consequence: the `hashCode` algorithm is **unspecified** and may change between releases,
      so it must never be persisted or used across JVMs. `[TRAP]` `[PROVE]`
3.9.7 The generated `equals` compares primitives with `==`, `float`/`double` with
      `Float.compare`/`Double.compare`-style bit semantics, and references with `Objects.equals`.
      `[SOURCE]` `[PROVE]`
3.9.8 Hence `NaN` equals `NaN` and `0.0` does not equal `-0.0` inside a record, the reverse of `==`.
      `[TRAP]` `[PROVE]` `[X-REF 03]`
3.9.9 The compact constructor desugars to the canonical constructor with `this.x = x;` appended for
      every component — visible in `javap`. `[BYTECODE]` `[PROVE]`
3.9.10 Reflection: `Class.isRecord()`, `Class.getRecordComponents()`, and `RecordComponent`'s
       `getName`, `getType`, `getGenericType`, `getAccessor`, `getAnnotations`. `[RESEARCH]`
3.9.11 `java.lang.Record` is an abstract class declaring abstract `equals`, `hashCode` and
       `toString`, and it cannot be extended directly. `[SOURCE]` `[PROVE]`
3.9.12 Record serialization: the serialised form is the component values; deserialization invokes
       the canonical constructor, so validation and normalisation always run. `[SOURCE]` `[PROVE]`
       `[RESEARCH]`
3.9.13 Record serialization ignores `writeObject`, `readObject`, `readObjectNoData`, `writeExternal`,
       `readExternal` and `serialPersistentFields`; the default `serialVersionUID` is 0.
       `[SOURCE]` `[RESEARCH]` `[TRAP]` `[NUM]`
3.9.14 `setAccessible` on a record's field is blocked, so reflection-based mutation frameworks
       (some ORMs, some mocking libraries) simply do not work on records. `[TRAP]` `[RESEARCH]`

*(14 leaves)*

## §3.10 Sealed internals

3.10.1 The class file gains a `PermittedSubclasses` attribute listing the permitted classes by
       constant-pool index. `[SOURCE]` `[RESEARCH]`
3.10.2 There is no `ACC_SEALED` access flag — sealing is an attribute, and a class with the
       attribute is sealed regardless of its other modifiers. `[RESEARCH]` `[PROVE]`
3.10.3 `non-sealed` produces no attribute at all; it is a source-level acknowledgement that the
       compiler requires and then discards. `[PROVE]`
3.10.4 Load-time enforcement: the JVM checks that a subclass appears in its superclass's
       `PermittedSubclasses`, so sealing survives bytecode manipulation. `[PROVE]` `[RESEARCH]`
3.10.5 Same-module (or same-package in the unnamed module) enforcement, and where the check happens.
       `[RESEARCH]` `[X-REF 03]`
3.10.6 Narrowing reference conversion over a sealed hierarchy: `javac` can prove a cast impossible
       and reject it at compile time, which it cannot do for an open hierarchy. `[PROVE]`
       `[RESEARCH]`
3.10.7 `Class.isSealed()` and `Class.getPermittedSubclasses()`, and their use in a test that iterates
       every case. `[RESEARCH]`
3.10.8 The separate-compilation hazard: recompiling the sealed hierarchy without its switch sites
       yields `MatchException` or `IncompatibleClassChangeError` at runtime, not a link error.
       `[TRAP]` `[PROVE]`

*(8 leaves)*

## §3.11 Pattern matching internals

3.11.1 `instanceof` with a type pattern compiles to `instanceof` + `checkcast` + `astore` — no
       runtime machinery at all. `[BYTECODE]` `[PROVE]`
3.11.2 Flow scoping is a compile-time analysis in the same family as definite assignment; nothing
       about it exists at runtime. `[PROVE]` `[X-REF 03]`
3.11.3 A pattern switch compiles to `invokedynamic` against
       `java.lang.runtime.SwitchBootstraps.typeSwitch`, which returns the **index** of the first
       matching label. `[SOURCE]` `[BYTECODE]` `[RESEARCH]`
3.11.4 The bootstrap's static arguments are the label list: `Class` objects for type patterns,
       `String`/`Integer` for constants, and `EnumDesc` for qualified enum labels. `[SOURCE]`
       `[RESEARCH]`
3.11.5 The generated code then does an ordinary `tableswitch` on the returned index. `[BYTECODE]`
       `[PROVE]`
3.11.6 Cost model: the bootstrap builds a chain of method handles that tests labels in order, and
       the JIT collapses the hot ones — so a pattern switch is closer to an if-chain than to a jump
       table, but a well-optimised one. `[RESEARCH]` `[NUM]`
3.11.7 `SwitchBootstraps.enumSwitch` for switches over enum constants with qualified labels.
       `[RESEARCH]`
3.11.8 Record deconstruction compiles to accessor calls in declaration order, short-circuiting on
       the first component mismatch. `[PROVE]` `[BYTECODE]`
3.11.9 If a record accessor throws during deconstruction, the exception is wrapped in a
       `MatchException` with the original as its cause. `[RESEARCH]` `[TRAP]`
3.11.10 Exhaustiveness is computed over the transitive `permits` closure plus the declared labels;
        the algorithm lives in JLS 14.11.1.1. `[SOURCE]` `[RESEARCH]`
3.11.11 Dominance is a compile-time subsumption check over label order, specified in JLS 14.11.1.
        `[SOURCE]`
3.11.12 Null handling: the compiler emits an explicit null test before the `invokedynamic` unless a
        `case null` label is present, in which case null is routed to that index. `[PROVE]`
        `[BYTECODE]`

*(12 leaves)*

## §3.12 `switch` compilation

3.12.1 `tableswitch` versus `lookupswitch`, and the density heuristic `javac` uses to choose.
       `[BYTECODE]` `[NUM]` `[X-REF 03]`
3.12.2 `switch` on `String`: a `lookupswitch` on `hashCode`, then `equals` to confirm, then a second
       switch on a synthetic index. `[BYTECODE]` `[X-REF 03]`
3.12.3 `switch` on an enum: a synthetic `$SwitchMap$...` `int[]` mapping `ordinal()` to a stable
       case index — which exists so that reordering the enum does not silently rewire a
       separately-compiled switch. `[PROVE]` `[X-REF 03]`
3.12.4 The arrow form compiles to the same instructions as a colon form with `break` after every
       arm — there is no runtime difference. `[PROVE]` `[BYTECODE]`
3.12.5 Switch expressions and the operand stack: every arm leaves exactly one value at the join
       point. `[BYTECODE]`
3.12.6 `yield` compiles as a branch to the join point with the value on the stack.
3.12.7 An exhaustive enum switch **expression** still emits a synthetic default that throws
       `IncompatibleClassChangeError` (Java 21+; `IncompatibleClassChangeError` replaced the older
       `NoSuchFieldError`/`MatchException` shapes across releases). `[PROVE]` `[RESEARCH]` `[TRAP]`
       `[VERSION-TRAP]`
3.12.8 Why that guard exists: an enum constant added after your class was compiled would otherwise
       fall off the end of an expression that must produce a value. `[PROVE]`

*(8 leaves)*

## §3.13 Text block compilation

3.13.1 A text block is a constant expression: the entire transformation happens in `javac` and
       nothing survives to runtime. `[PROVE]` `[BYTECODE]`
3.13.2 The three-step algorithm as specified: normalise line terminators, remove incidental white
       space, interpret escape sequences — in that order and no other. `[SOURCE]`
3.13.3 The exact minimal-indent computation: blank lines are excluded from the minimum, the closing
       delimiter's line is included, and trailing whitespace is removed from every line first.
       `[PROVE]` `[SOURCE]`
3.13.4 The result is a `CONSTANT_String_info` in the constant pool, and therefore interned.
       `[PROVE]` `[X-REF 03]`
3.13.5 `String.stripIndent()` implements the same algorithm at runtime, minus the closing-delimiter
       line. `[SOURCE]`
3.13.6 A text block and an equal string literal are `==` because both are interned constants — the
       one case where `==` on strings is reliable, and still not a habit to build. `[PROVE]`
       `[TRAP]` `[X-REF 03]`

*(6 leaves)*

## §3.14 Virtual thread internals

3.14.1 The three layers: `java.lang.VirtualThread`, `jdk.internal.vm.Continuation`, and the
       scheduler. `[RESEARCH]`
3.14.2 `Continuation`: `enter`/`yield`, with the JVM copying stack frames between the carrier's
       stack and a heap-resident `StackChunk`. `[RESEARCH]` `[PROVE]`
3.14.3 Mount copies frames from the heap chunk onto the carrier stack; unmount copies them back.
       Lazy/partial copying is what keeps the common case cheap. `[NUM]` `[RESEARCH]`
3.14.4 `VirtualThread`'s state machine: `NEW`, `STARTED`, `RUNNABLE`, `RUNNING`, `PARKING`,
       `PARKED`, `PINNED`, `YIELDING`, `TERMINATED`. `[RESEARCH]`
3.14.5 The default scheduler is a `ForkJoinPool` created in FIFO async mode, with parallelism equal
       to `availableProcessors()` and a `maxPoolSize` defaulting to 256. `[NUM]` `[RESEARCH]`
3.14.6 `jdk.virtualThreadScheduler.parallelism` and `jdk.virtualThreadScheduler.maxPoolSize`, and
       how to confirm the effective values at runtime. `[NUM]` `[RESEARCH]`
3.14.7 Why FIFO rather than the LIFO work-stealing used for parallel streams: virtual threads are
       independent tasks, not recursively split subtasks, so fairness matters more than locality.
       `[PROVE]`
3.14.8 The instrumented blocking points, enumerated: `java.net` sockets, NIO channels and
       `Selector`, `HttpClient`, `Thread.sleep`, `LockSupport.park`, `java.util.concurrent` locks
       and queues, `Process.waitFor`. `[X-REF 05]`
3.14.9 The non-instrumented ones: most file I/O (delegated to a carrier or an internal pool),
       `Object.wait` before Java 24, and any JNI frame. `[TRAP]` `[RESEARCH]`
3.14.10 Stack chunks live in the heap and are ordinary garbage-collected objects — which is why a
        million threads is a heap-sizing exercise, not a virtual-address-space one. `[NUM]`
        `[X-REF 06]`
3.14.11 `Thread.currentThread()` inside a virtual thread returns the `VirtualThread`; the carrier is
        only reachable through internal API. `[RESEARCH]`
3.14.12 Thread-local storage is per virtual thread, so a `ThreadLocal` cache is now a per-task cache
        with per-task allocation. `[NUM]` `[PROVE]`
3.14.13 Pinning is a property of the continuation: it cannot yield while a native frame or a held
        monitor is on its stack. `[PROVE]` `[RESEARCH]`
3.14.14 JEP 491 (Java 24) makes object monitors continuation-aware, so `synchronized` no longer
        pins; native frames still do. Every "use ReentrantLock" answer must be dated. `[VERSION-TRAP]`
        `[RESEARCH]`
3.14.15 `-Djdk.tracePinnedThreads` was introduced by JEP 444 and is superseded by the
        `jdk.VirtualThreadPinned` JFR event, which carries both the pinning reason and the carrier's
        identity. `[RESEARCH]` `[VERSION-TRAP]`
3.14.16 Thread dumps: `jcmd <pid> Thread.dump_to_file -format=json` includes virtual threads and
        the structured-concurrency tree, but omits object addresses, lock information and JNI
        statistics. `[RESEARCH]` `[TRAP]`
3.14.17 There is no preemption: a CPU-bound virtual thread holds its carrier until it blocks or
        finishes, so one runaway loop can occupy a core indefinitely. `[TRAP]` `[PROVE]`
3.14.18 Compensation: the carrier pool may grow toward `maxPoolSize` when threads pin or use a
        `ManagedBlocker`, which is why the pool has a max at all. `[RESEARCH]` `[NUM]`

*(18 leaves)*

## §3.15 Structured concurrency and scoped values internals

3.15.1 `StructuredTaskScope` is built on virtual threads plus a per-thread scope stack; every `fork`
       starts one virtual thread. `[RESEARCH]`
3.15.2 The ownership check: `fork`, `join`, `shutdown` and `close` must all be called by the owning
       thread. `[RESEARCH]`
3.15.3 `StructureViolationException` and the stack-discipline invariant that scopes must close in
       reverse order of opening. `[RESEARCH]`
3.15.4 Cancellation: `shutdown()` interrupts every unfinished subtask and prevents further forks;
       `close()` then joins. `[PROVE]`
3.15.5 `ScopedValue`'s implementation: an immutable linked binding snapshot per thread plus a small
       fixed-size per-thread cache keyed by the value's hash. `[RESEARCH]` `[NUM]`
3.15.6 Why scoped values are cheaper than `ThreadLocal`: no map, no `remove()` discipline, no
       inheritance copy — the bindings are shared structurally and unbound by stack unwinding.
       `[PROVE]` `[RESEARCH]`
3.15.7 Inheritance into forked subtasks is what makes scoped values and structured concurrency a
       pair rather than two independent features. `[RESEARCH]`
3.15.8 The version-by-version API churn table for both features, 19 → 26, so any code sample can be
       dated. `[RESEARCH]` `[VERSION-TRAP]`

*(8 leaves)*

## §3.16 Version-by-version delta

3.16.1 Java 8 (2014): lambdas, method references, functional interfaces, streams, default and static
       interface methods, `Optional`, `java.time`, `CompletableFuture`, `StringJoiner`, `Base64`,
       `Arrays.parallelSort`, repeating and type annotations, PermGen replaced by Metaspace,
       Nashorn. `[RESEARCH]` `[X-REF 03]` `[X-REF 06]`
3.16.2 Java 9: JPMS, `List/Set/Map.of`, `Optional.stream/or/ifPresentOrElse`,
       `Stream.takeWhile/dropWhile/ofNullable/iterate(3)`, private interface methods, JShell, jlink,
       `Flow`, `VarHandle`, `StackWalker`, compact strings, indified concatenation, G1 by default,
       `finalize` deprecated.
3.16.3 Java 10: `var`, `List/Set/Map.copyOf`, `Collectors.toUnmodifiable*`,
       `Optional.orElseThrow()`, application class-data sharing, parallel full GC for G1.
3.16.4 Java 11 (LTS): `HttpClient`, `String.isBlank/lines/strip/repeat`,
       `Files.readString/writeString`, `Predicate.not`, `var` in lambda parameters, single-file
       source launch, ZGC and Epsilon experimental, Java EE and CORBA modules removed, Nashorn
       deprecated, Flight Recorder open-sourced.
3.16.5 Java 12: `Collectors.teeing`, `String.indent/transform`, `Files.mismatch`, Shenandoah,
       switch expressions (preview), `CompactNumberFormat`.
3.16.6 Java 13: text blocks (preview), switch expressions (second preview), dynamic CDS archives,
       ZGC uncommit.
3.16.7 Java 14: switch expressions **final**, records (preview), pattern `instanceof` (preview),
       helpful NPE messages, JFR event streaming, `jpackage` (incubator), CMS removed.
3.16.8 Java 15: text blocks **final**, sealed (preview), records (second preview), hidden classes
       (JEP 371), ZGC and Shenandoah production, EdDSA, Nashorn removed, helpful NPE on by default.
       `[RESEARCH]`
3.16.9 Java 16: records **final**, pattern `instanceof` **final**, `Stream.toList`,
       `Stream.mapMulti`, static members in inner classes, strong encapsulation by default,
       Unix-domain sockets, `jpackage` final, Vector API and FFM incubating. `[RESEARCH]`
3.16.10 Java 17 (LTS): sealed classes **final**, pattern switch (preview), `RandomGenerator`
        (JEP 356), always-strict floating point (JEP 306), context-specific deserialization
        filters, Security Manager deprecated, applet API deprecated, macOS/AArch64 port.
        `[RESEARCH]`
3.16.11 Java 18: UTF-8 by default (JEP 400), simple web server, `@snippet` in javadoc, internet
        address resolution SPI, finalization deprecated for removal (JEP 421), pattern switch
        (second preview). `[RESEARCH]`
3.16.12 Java 19: virtual threads (preview), structured concurrency (incubator), record patterns
        (preview), pattern switch (third preview), FFM (preview), Linux/RISC-V port.
3.16.13 Java 20: all four re-previewed; scoped values (incubator); no final language features.
3.16.14 Java 21 (LTS): virtual threads **final**, record patterns **final**, pattern matching for
        switch **final**, sequenced collections, generational ZGC, key encapsulation API; preview:
        string templates, structured concurrency, scoped values, unnamed patterns and variables,
        unnamed classes and instance `main`. `[RESEARCH]`
3.16.15 Java 22: unnamed variables and patterns **final**, FFM **final**, multi-file source launch,
        statements before `super()` (preview), stream gatherers (preview), string templates
        (second preview), region pinning for G1. `[RESEARCH]`
3.16.16 Java 23: string templates **withdrawn**, gatherers (second preview), primitive types in
        patterns (preview), Markdown javadoc, generational ZGC by default, `sun.misc.Unsafe`
        memory-access methods deprecated (JEP 471). `[RESEARCH]`
3.16.17 Java 24: stream gatherers **final** (JEP 485), JEP 491 removes `synchronized` pinning,
        Class-File API **final**, scoped values and structured concurrency re-previewed, AOT class
        loading and linking, compact object headers (experimental), Security Manager permanently
        disabled (JEP 486). `[RESEARCH]`
3.16.18 Java 25 (LTS): scoped values **final** (JEP 506), compact source files and instance `main`
        **final** (JEP 512), module import declarations **final** (JEP 511), flexible constructor
        bodies **final** (JEP 513), structured concurrency fifth preview (JEP 505), primitive types
        in patterns third preview (JEP 507), stable values (preview), PEM encodings, generational
        Shenandoah. `[RESEARCH]`
3.16.19 Still in flight as of this file's date: structured concurrency (sixth/seventh preview via
        JEP 525/533), primitive patterns, stable values, Valhalla value classes, derived record
        creation, and a redesigned string-template proposal. `[RESEARCH]`
3.16.20 The consolidated feature → version table, so every claim in this guide can be dated in one
        lookup.
3.16.21 The consolidated removed-or-disabled table: Nashorn, Java EE modules, CORBA, applets,
        Security Manager, finalization, the 32-bit x86 port, `Unsafe` memory access.
3.16.22 How to answer "what is new in Java N" in an interview: three features, the problem each
        solves, one trap each, and the release you personally run in production.

*(22 leaves)*

## §3.17 Observability and tooling

3.17.1 `javap -c -p -v` for every desugaring claim in this part: the lambda indy, the record indy,
       the pattern-switch indy, and the text block constant. `[BYTECODE]`
3.17.2 `jshell` for a ten-second experiment: `peek` elision, `Optional.empty()` identity, text-block
       indentation, `Stream.toList` immutability.
3.17.3 `-Djdk.internal.lambda.dumpProxyClasses=<dir>` to write the spun lambda classes to disk and
       decompile them. `[RESEARCH]` `[VERSION-TRAP]`
3.17.4 `-Xlog:class+load=info` to watch the hidden classes appear at the first invocation of each
       lambda call site. `[X-REF 06]`
3.17.5 JFR for this topic: `jdk.VirtualThreadStart/End/Pinned/SubmitFailed`, plus
       `jdk.ObjectAllocationSample` for boxing and `jdk.JavaExceptionThrow`. `[X-REF 20]`
3.17.6 `jcmd <pid> Thread.dump_to_file -format=json <file>` for virtual threads and scope trees.
       `[RESEARCH]`
3.17.7 `jcmd <pid> Thread.print` for platform threads, monitors and deadlock detection. `[X-REF 06]`
3.17.8 async-profiler, and the frame names you will actually see for lambdas, stream stages and
       ForkJoin leaves. `[X-REF 06]`
3.17.9 JMH for every stream-versus-loop or parallel-versus-sequential claim: warm-up, forks,
       `Blackhole`, and why a microbenchmark without them lies. `[X-REF 16]`
3.17.10 IDE support worth using: IntelliJ's stream debugger and "trace current stream chain", and
        the inlay hints that show a `var`'s inferred type.
3.17.11 Static analysis for this topic: ErrorProne (`OptionalUsedAsFieldOrParameterType`,
        `StreamResourceLeak`, `ReturnValueIgnored`, `OptionalNotPresent`), SpotBugs, SonarQube's
        stream and `Optional` rules, NullAway. `[RESEARCH]`
3.17.12 Confirm before you quote: `-XX:+PrintFlagsFinal` for VM flags,
        `System.getProperties()` for the scheduler properties,
        `ForkJoinPool.getCommonPoolParallelism()` for the pool width. `[X-REF 06]`

*(12 leaves)*

---

**PART 3 total: 210 leaves**

---

# PART 4 — BUILD IT

Every item is `[BUILD]`: complete, compiling, generic Java 21, followed by a **Diff vs the real one**
table covering at minimum edge cases, intrinsics, serialization, null policy, thread safety,
allocation tricks, and why the JDK bothers.

## §4.1 A functional toolkit from scratch

4.1.1 `MyFunction<T,R>` with `andThen`, `compose` and `identity`, plus a harness that proves the
      two composition orders differ. `[PROVE]`
4.1.2 `MyPredicate<T>` with `and`, `or`, `negate`, `not`, and a short-circuit demonstration using a
      side-effecting predicate. `[PROVE]`
4.1.3 `CheckedFunction<T,R,E extends Exception>` plus `unchecked(...)` and `sneaky(...)` adapters,
      used to put an `IOException`-throwing call inside a `map`. `[X-REF 03]`
4.1.4 A `Result<T,E>` sealed interface with `Ok` and `Err` records, `map`/`flatMap`/`fold`/
      `orElseThrow`, as the type-level alternative to checked exceptions in a pipeline.
4.1.5 A memoizing `Function` decorator over a `ConcurrentHashMap`, including the
      `computeIfAbsent`-recursion deadlock and its fix. `[TRAP]` `[PROVE]` `[X-REF 05]`
4.1.6 A curry/partial-application helper for `BiFunction`, with an honest note on when it stops
      being readable.
4.1.7 A `TriFunction` the JDK does not provide, and the argument for why the JDK stops at two.
4.1.8 Diff vs `java.util.function`: 43 interfaces, the primitive specialisations,
      `@FunctionalInterface` enforcement, the deliberate absence of a checked variant, and why
      arity stops at two.

*(8 leaves)*

## §4.2 `MyStream` — a lazy fused pipeline

4.2.1 `MySink<T>` with `begin(long)`, `accept(T)`, `cancellationRequested()`, `end()`.
4.2.2 `MyStream<T>` over an iterator source, with `filter`, `map` and a terminal `forEach`, fused
      through a sink chain rather than staged through collections.
4.2.3 Proving fusion: a print statement in each stage, showing interleaved per-element traversal
      rather than three sequential passes. `[PROVE]`
4.2.4 Adding `limit` and `findFirst` via `cancellationRequested`, proving short-circuiting on an
      infinite source. `[PROVE]`
4.2.5 Adding `sorted` as a stateful barrier, and demonstrating exactly where laziness stops.
      `[PROVE]`
4.2.6 Adding a `linkedOrConsumed` flag and reproducing
      `IllegalStateException: stream has already been operated upon or closed`. `[PROVE]`
4.2.7 A minimal flags mechanism (`SIZED`) that lets `count()` bypass the pipeline — reproducing the
      real `peek`-elision behaviour in fifty lines. `[PROVE]`
4.2.8 A trivial parallel evaluation over a splittable array source with a leaf-size threshold and
      `ForkJoinTask`. `[NUM]`
4.2.9 A JMH comparison of `MyStream`, `java.util.stream`, and a plain `for` loop over 1 000 000
      elements. `[NUM]`
4.2.10 Diff vs `java.util.stream`: four stream shapes, thirty-odd operations, the full
       `StreamOpFlag` lattice, the `Spliterator` contract, ForkJoin integration, primitive
       specialisation, closing, and exception semantics.

*(10 leaves)*

## §4.3 Collectors from scratch

4.3.1 `MyCollector<T,A,R>` mirroring the five-function contract and the characteristics set.
4.3.2 `toList`, `joining` and `groupingBy` implemented on it, with correct combiners.
4.3.3 A bounded top-N collector over a `PriorityQueue`, with a combiner that merges two heaps
      correctly. `[PROVE]` `[X-REF 02]`
4.3.4 A frequency/mode collector returning a record of `(value, count)`.
4.3.5 A boxing-free statistics collector over a `long[]` accumulator, benchmarked against
      `Collectors.summarizingInt`. `[NUM]`
4.3.6 A `CONCURRENT` collector plus a harness proving it only reduces concurrently when all three
      conditions hold. `[PROVE]`
4.3.7 Diff vs `java.util.stream.Collectors`: `CollectorImpl`, the pre-built characteristic sets,
      Kahan compensated summation, the `IDENTITY_FINISH` fast path, and the unchecked casts the JDK
      uses to keep `A` hidden.

*(7 leaves)*

## §4.4 `MyOptional`

4.4.1 `MyOptional<T>` with `of`, `ofNullable`, `empty`, `map`, `flatMap`, `filter`, `or`, `stream`,
      `ifPresent`, `ifPresentOrElse`, `orElse`, `orElseGet`, `orElseThrow` ×2.
4.4.2 A shared `EMPTY` instance, and a demonstration that `empty() == empty()` — followed by the
      argument for why you must not depend on it. `[PROVE]`
4.4.3 A counter-based harness proving `orElse` evaluates eagerly and `orElseGet` does not. `[PROVE]`
4.4.4 An allocation count for a five-`map` chain, run with and without `-XX:-DoEscapeAnalysis`.
      `[NUM]` `[PROVE]`
4.4.5 A null-returning mapper, matched against the JDK's `empty()` behaviour. `[PROVE]`
4.4.6 Diff vs `java.util.Optional`: `@ValueBased`, the absence of `Serializable`, the primitive
      variants, the intended-use API note, and the Valhalla trajectory.

*(6 leaves)*

## §4.5 Records, sealed types and patterns from scratch

4.5.1 The hand-written pre-record equivalent of a three-component record — constructor, accessors,
      `equals`, `hashCode`, `toString`, defensive copies — counted in lines against the one-line
      record. `[NUM]` `[PROVE]`
4.5.2 A record with a `List` component written three ways — no copy, copy-in only, copy-in and
      copy-out — each with a mutation test that either passes or fails. `[PROVE]` `[TRAP]`
4.5.3 A record with an array component demonstrating the `equals`/`hashCode` failure, then the
      `List` fix, then the `Arrays.equals` override if the array is unavoidable. `[PROVE]`
4.5.4 A `sealed interface Shape` with record cases, an exhaustive pattern switch, and the exact
      compile error produced when a fourth case is added. `[PROVE]`
4.5.5 The same hierarchy expressed as a Visitor, side by side, with a line count and a "where do I
      edit to add a case / add an operation" table. `[PROVE]`
4.5.6 An expression-tree interpreter over a sealed record hierarchy using nested deconstruction and
      guards.
4.5.7 A reflective "wither" helper built from `getRecordComponents()` and the canonical constructor
      — and the argument for why you should not ship it. `[TRAP]`
4.5.8 Diff vs the compiler's output: the `Record` attribute, `ObjectMethods` indy,
      `PermittedSubclasses`, `SwitchBootstraps.typeSwitch` indy, and `MatchException`.

*(8 leaves)*

## §4.6 Concurrency builds

4.6.1 A blocking echo server written twice — one platform thread per connection, then one virtual
      thread per connection — measured at 1, 1 000 and 50 000 concurrent connections. `[NUM]`
      `[PROVE]`
4.6.2 A pinning reproducer: `synchronized` around a blocking sleep, run on Java 21 with
      `-Djdk.tracePinnedThreads=full`, the output read line by line, then the `ReentrantLock` fix
      and the re-measurement. `[PROVE]` `[TRAP]`
4.6.3 A `ThreadLocal`-cache memory harness at 10 000 and 1 000 000 virtual threads, with heap
      numbers. `[NUM]`
4.6.4 A `Semaphore`-bounded virtual-thread client demonstrating precisely what removing the thread
      pool removed. `[PROVE]`
4.6.5 A fan-out written with `StructuredTaskScope.ShutdownOnFailure` and again with
      `CompletableFuture.allOf`, with a deliberate failure, showing the orphaned task in one and
      not the other. `[PROVE]` `[TRAP]`
4.6.6 A hedged request with `ShutdownOnSuccess` against two simulated backends of different
      latency.
4.6.7 A common-pool starvation reproducer: one blocking parallel stream and one innocent one, both
      timed, then the same with a dedicated executor. `[PROVE]` `[TRAP]`
4.6.8 Diff vs the JDK: `Continuation` and `StackChunk`, the FIFO ForkJoin scheduler, the JEP 505
      `Joiner` API shape, `ManagedBlocker`, and the JFR instrumentation.

*(8 leaves)*

## §4.7 Filling the Java 21 gaps

4.7.1 A fixed-window batching intermediate operation on Java 21 via a custom `Spliterator`, matching
      what `Gatherers.windowFixed` does in Java 24. `[RESEARCH]`
4.7.2 A `zip` over two streams via a paired spliterator, with the correct `estimateSize` and no
      `SUBSIZED` claim.
4.7.3 A running-total `scan` via a stateful mapper, with the explicit warning that it is illegal in
      parallel — and a demonstration of it producing wrong answers there. `[TRAP]` `[PROVE]`
4.7.4 `distinctBy(keyExtractor)` via a `Set`-capturing predicate, with the same warning and the same
      demonstration. `[TRAP]` `[PROVE]`
4.7.5 A `takeUntil`, and a `mapConcurrent` equivalent built on virtual threads plus a semaphore.
4.7.6 Diff vs `Gatherers` (Java 24): the `Gatherer` contract (`initializer`, `integrator`,
      `combiner`, `finisher`), greedy versus short-circuiting integrators, and the built-ins
      `fold`, `scan`, `windowFixed`, `windowSliding`, `mapConcurrent`. `[RESEARCH]`

*(6 leaves)*

## §4.8 Diagnostic harnesses

4.8.1 A fifteen-snippet puzzler set, each printing something surprising with the mechanism named:
      `peek` elision, stream reuse, `toList` immutability, `toMap` null value, `groupingBy` null
      key, `orElse` eagerness, `Optional.empty()` identity, `var` diamond, record array `equals`,
      pattern-switch NPE, text-block indentation, bound method-reference NPE, `allMatch` on an
      empty stream, `IntStream.sum` overflow, parallel `forEach` corruption. `[PROVE]`
4.8.2 A stream-versus-loop JMH benchmark at N = 10, 1 000 and 1 000 000, boxed and primitive.
      `[NUM]` `[X-REF 16]`
4.8.3 A parallel-versus-sequential JMH sweep across N and per-element cost, locating the crossover
      empirically rather than quoting the rule of thumb. `[NUM]` `[PROVE]`
4.8.4 A source-splitting benchmark: `int[]`, `ArrayList`, `LinkedList`, `HashSet`, `Files.lines` and
      `IntStream.range`, all under `.parallel()`. `[NUM]` `[PROVE]`
4.8.5 A lambda-startup harness with 1, 100 and 10 000 distinct call sites, measuring class-loading
      count and first-call latency. `[NUM]` `[PROVE]`
4.8.6 A capturing-versus-non-capturing lambda identity and allocation harness. `[PROVE]` `[NUM]`
4.8.7 A `javap` walk of one class containing a lambda, a method reference, a record, a pattern
      switch and a text block, reading each `BootstrapMethods` entry. `[BYTECODE]` `[PROVE]`
4.8.8 A collector-combiner cost harness: `toList` versus `joining` versus `groupingBy` in parallel
      at increasing N. `[NUM]`
4.8.9 An exhaustiveness-drift harness: compile a switch, add a permitted subtype, recompile only the
      hierarchy, and catch the resulting `MatchException` / `IncompatibleClassChangeError`.
      `[PROVE]` `[TRAP]`
4.8.10 A record-serialization harness proving the canonical constructor runs on deserialization and
       that validation cannot be bypassed — contrasted with the same class written as a plain class.
       `[PROVE]`
4.8.11 A text-block indentation harness printing each result with visible markers for four different
       closing-delimiter positions. `[PROVE]`
4.8.12 A migration smoke harness: the same program compiled with `--release` 8, 11, 17 and 21,
       diffing observable behaviour (default charset, NPE messages, `toList` mutability, iteration
       order of `Set.of`). `[PROVE]` `[NUM]`

*(12 leaves)*

---

**PART 4 total: 65 leaves**

---

# PART 5 — INTERVIEW AND RETENTION

## §5.1 The questions, with the answer shape

5.1.1 "What is a functional interface? Does it need `@FunctionalInterface`?"
5.1.2 "`Comparator` declares two abstract-looking methods — why is it still functional?"
5.1.3 "Is a lambda just syntactic sugar for an anonymous inner class?" — the 30-second and the
      5-minute answer.
5.1.4 "What bytecode does a lambda compile to? Walk me through the `invokedynamic`."
5.1.5 "What is `LambdaMetafactory` and when does it run?"
5.1.6 "Is the same lambda expression the same object every time?"
5.1.7 "What does `this` mean inside a lambda?"
5.1.8 "Why must a captured local be effectively final?"
5.1.9 "How do I increment a counter from inside a lambda?" — and why the question is the bug.
5.1.10 "Name the four kinds of method reference and give an example of each."
5.1.11 "When does a bound method reference evaluate its receiver?"
5.1.12 "How do you throw a checked exception from inside a `map`?"
5.1.13 "What is a stream, and how is it different from a collection?"
5.1.14 "Explain laziness. What runs when, in `list.stream().filter(f).map(g).findFirst()`?"
5.1.15 "Does a stream process stage by stage or element by element? Prove it."
5.1.16 "Can you reuse a stream? What exactly happens if you try?"
5.1.17 "What does `peek` do and when is it not called?"
5.1.18 "Which stream operations are stateful, and why does that matter?"
5.1.19 "What is encounter order, and which operations depend on it?"
5.1.20 "Difference between `findFirst` and `findAny`?"
5.1.21 "What does `allMatch` return on an empty stream?"
5.1.22 "`map` vs `flatMap` vs `mapMulti`."
5.1.23 "`takeWhile` vs `filter`."
5.1.24 "How would you batch a stream into windows of 100 on Java 21?"
5.1.25 "How would you zip two streams?"
5.1.26 "`collect(toList())` vs `stream.toList()` — name three differences."
5.1.27 "What does `Collectors.toMap` do on a duplicate key? On a null value?"
5.1.28 "What map and list types does `groupingBy` return?"
5.1.29 "`groupingBy(p)` vs `partitioningBy(p)` — what is different about the empty case?"
5.1.30 "Write a collector that gives the top 3 by salary per department."
5.1.31 "Explain the `Collector` contract's five functions."
5.1.32 "When is `reduce` wrong and `collect` right?"
5.1.33 "Why must a `reduce` combiner be associative?"
5.1.34 "How does a parallel stream decide how many tasks to create?"
5.1.35 "Which thread pool does a parallel stream use, and how big is it?"
5.1.36 "What happens if I do blocking I/O inside a parallel stream?"
5.1.37 "Can I give a parallel stream my own pool? Is that supported?"
5.1.38 "When is a parallel stream faster? Give me the four conditions."
5.1.39 "Why is `parallelStream().forEach(list::add)` broken but `collect(toList())` fine?"
5.1.40 "What is a `Spliterator` and what do its characteristics do?"
5.1.41 "Why does a `LinkedList` parallelise badly?"
5.1.42 "What is `Optional` for, and where should it never appear?"
5.1.43 "`orElse` vs `orElseGet` — show me the bug."
5.1.44 "Why is `isPresent()` + `get()` an anti-pattern?"
5.1.45 "Why is `Optional` not `Serializable`?"
5.1.46 "What happens if `map`'s function returns null?"
5.1.47 "Is `Optional.empty() == Optional.empty()` true? Should you rely on it?"
5.1.48 "What is `var`, and where can you not use it?"
5.1.49 "Does `var` have a runtime cost?"
5.1.50 "What does `var list = new ArrayList<>()` infer?"
5.1.51 "Why can't you write `var f = () -> 1;`?"
5.1.52 "What does a record generate for you?"
5.1.53 "What is a compact constructor and what is it for?"
5.1.54 "Are records immutable?"
5.1.55 "Why is an array component in a record a bug?"
5.1.56 "How do you make a record with a `List` component genuinely immutable?"
5.1.57 "Can you persist a record's `hashCode`?"
5.1.58 "Can a record be a JPA entity? Why not?"
5.1.59 "How does record deserialization differ from ordinary Java serialization?"
5.1.60 "How are a record's `equals`/`hashCode`/`toString` actually implemented in bytecode?"
5.1.61 "What does `sealed` do, and what must every permitted subtype declare?"
5.1.62 "Can an anonymous class be a permitted subtype?"
5.1.63 "What is the difference between `sealed` and `final`?"
5.1.64 "Sealed interface or enum — how do you choose?"
5.1.65 "What does a sealed hierarchy buy a `switch`?"
5.1.66 "Why would you deliberately omit `default` from a switch?"
5.1.67 "What is flow scoping? Why is `s` in scope after `if (!(o instanceof String s)) return;`?"
5.1.68 "What happens when a pattern switch gets a null?"
5.1.69 "What is `MatchException` and when have you seen one?"
5.1.70 "Explain dominance. Why must a guarded case come first?"
5.1.71 "What are record patterns and how deep can they nest?"
5.1.72 "How does a pattern switch compile? Is it a chain of `instanceof`?"
5.1.73 "Switch statement vs switch expression — name three differences."
5.1.74 "`yield` vs `return` inside a switch."
5.1.75 "What is `$SwitchMap` and why does it exist?"
5.1.76 "How does a text block decide indentation?"
5.1.77 "What does `\\s` do in a text block, and why would you need it?"
5.1.78 "Are text blocks interned?"
5.1.79 "Does Java have string interpolation?"
5.1.80 "What is a virtual thread and how is it scheduled?"
5.1.81 "Walk me through mounting and unmounting."
5.1.82 "What is pinning? What causes it on Java 21, and what changed in 24?"
5.1.83 "How do you detect pinning in production?"
5.1.84 "Should you pool virtual threads?"
5.1.85 "Do virtual threads help CPU-bound work?"
5.1.86 "You removed the thread pool. What did you also remove?"
5.1.87 "What breaks in a Spring Boot app when you turn virtual threads on?"
5.1.88 "How many virtual threads can you create, and what limits it?"
5.1.89 "What does `ThreadLocal` cost now?"
5.1.90 "What is structured concurrency and what does it guarantee?"
5.1.91 "How is `StructuredTaskScope` different from `CompletableFuture.allOf`?"
5.1.92 "Is structured concurrency final? What changed in 25?"
5.1.93 "What are scoped values and why not just use `ThreadLocal`?"
5.1.94 "What are sequenced collections and which types got them?"
5.1.95 "What is the single most useful thing added between Java 8 and 21, and why?"

*(95 leaves)*

## §5.2 The trap index

5.2.1 One table of every `**Trap:**` in the file: the wrong belief, the symptom you would see in
      production, and the fix — usable as a single pre-interview scan.
5.2.2 The version-stale claims table: `synchronized` pins virtual threads (fixed in 24), guarded
      patterns use `&&` (became `when` in 21), record patterns work in enhanced `for` (removed
      before 21 shipped), string templates are coming (withdrawn in 23),
      `StructuredTaskScope.fork` returns a `Future` (it returns `Subtask` since 21),
      `ShutdownOnFailure` is the API (replaced by `Joiner` in 25), `ScopedValue.runWhere` exists
      (removed in 24), `peek` always runs (elidable since 9), `flatMap` cannot short-circuit (fixed
      in 10), the default charset is platform-dependent (UTF-8 since 18), `Foo$$Lambda$1` naming
      (changed in 21).
5.2.3 The five most expensive real-world mistakes from this guide: blocking I/O in a parallel
      stream, mutable state in a record component, `Optional` in an entity field, pooling virtual
      threads, and shipping a public API over a preview feature.
5.2.4 The five most common interview-losing wrong answers: "a lambda is an anonymous class",
      "streams are faster than loops", "parallel streams use all your cores so they are free",
      "records are immutable", "virtual threads make everything faster".
5.2.5 The five claims that are true but must be dated: pinning, the toList mutability rule, the
      default charset, the exhaustiveness rules, and the structured-concurrency API shape.

*(5 leaves)*

## §5.3 One-line assertions and drills

5.3.1 The numbers drill: recite every constant with its value — 43 function interfaces, 30
      collectors / 54 overloads, common-pool parallelism `n − 1`, `LEAF_TARGET = parallelism << 2`,
      the 20 ms `VirtualThreadPinned` threshold, `maxPoolSize` 256, class-file majors 52/55/61/65,
      the eight spliterator characteristic bits, `FLAG_SERIALIZABLE = 1`.
5.3.2 The mechanism drill: explain in one sentence each — `invokedynamic`, `LambdaMetafactory`,
      hidden class, `Sink`, `StreamOpFlag`, `Spliterator.trySplit`, `CollectorImpl`,
      `ObjectMethods.bootstrap`, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch`,
      `Continuation`, `StackChunk`, `MatchException`, `StructureViolationException`.
5.3.3 The code-reading drill: ten snippets, say what each prints and why it is not what it looks
      like.
5.3.4 The "which construct" drill: fifteen scenarios → the right feature, one line each.
5.3.5 The symptom drill: given a symptom (a request storm that pegs one core, a corrupted list after
      a refactor, an `UnsupportedOperationException` after a library upgrade, a duplicate-key
      `IllegalStateException` at 3 a.m., a `MatchException` after a partial redeploy), name the
      mechanism.
5.3.6 The dating drill: for each of ten features, state the release it became final and the release
      it was first previewed.
5.3.7 The refactor drill: rewrite five imperative snippets as streams, then argue which two should
      be left alone.
5.3.8 Spaced-repetition schedule for this file: day 1 read, day 3 checklist, day 7 numbers and
      mechanism drills, day 14 code-reading and symptom drills, day 21 build two items from Part 4.
5.3.9 `## Atomic concept checklist` — every one of the 25 existing checklist lines from the current
      guide, preserved verbatim in substance, plus one line per new concept in this syllabus.

*(9 leaves)*

---

**PART 5 total: 109 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 1 — Basics | 410 |
| PART 2 — Intermediate | 190 |
| PART 3 — Under the hood | 210 |
| PART 4 — Build it | 65 |
| PART 5 — Interview & retention | 109 |
| **Total** | **984** |

Leaves carrying `[RESEARCH]`: **202**.
Leaves carrying `[VERSION-TRAP]`: **22**.
Leaves carrying `[TRAP]`: ~**135**. `[PROVE]`: ~**150**. `[SOURCE]`: ~**75**.
`[BYTECODE]`: ~**30**. `[NUM]`: ~**85**.
`[BUILD]`: **65** (all of Part 4), plus 1.2.20, 1.10.24, 1.13.17, 2.2.9, 2.2.11, 2.2.12, 2.5.8,
2.5.9, 2.8.13, 3.4.11, 3.4.12.

---

## Sources consulted

| Source | What it contributed |
|---|---|
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/invoke/LambdaMetafactory.html | the `metafactory`/`altMetafactory` signatures, the static-vs-dynamic argument-list distinction, and the statement that the recommended strategy is to desugar the body to a method and link through an indy call site — §3.1.3–3.1.7 |
| https://cr.openjdk.org/~briangoetz/lambda/lambda-translation.html | the full translation strategy: `lambda$N` naming, non-capturing vs capturing instantiation, `SerializedLambda` and `$deserializeLambda$`, the bridge-method flag, and the explicit "why not inner classes" argument — §3.1.1–3.1.16 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html | the normative stream vocabulary quoted throughout §1.5 and §1.7–1.8: the five properties, laziness, short-circuiting, stateless/stateful, non-interference, statelessness of behavioural parameters, side-effect elision, encounter order, the reduction and mutable-reduction contracts, associativity, and the three conditions for a concurrent reduction |
| https://raw.githubusercontent.com/openjdk/jdk/jdk-21%2B35/src/java.base/share/classes/java/util/stream/AbstractPipeline.java | the verbatim field list (`sourceStage`, `previousStage`, `sourceOrOpFlags`, `nextStage`, `depth`, `combinedFlags`, `sourceSpliterator`, `sourceSupplier`, `linkedOrConsumed`, `sourceAnyStateful`, `sourceCloseAction`, `parallel`), the two exception messages (`"stream has already been operated upon or closed"`, `"source already consumed or closed"`), and the bodies of `wrapSink`, `copyInto` and `evaluate` — §3.3.2, §3.3.8–3.3.12 |
| https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/stream/ReferencePipeline.java | `StatelessOp`/`StatefulOp`, `opWrapSink` per operation, and the `Sink.ChainedReference` pattern — §3.3.4–3.3.7 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/function/package-summary.html | the complete 43-interface inventory of `java.util.function` and the naming scheme — §1.2.7, §1.2.13 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collectors.html | the 30 distinct static factory methods across 54 overloads, with per-method overload counts — §1.10.3–1.10.22 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html | the complete method list with the version each was added (15 at 1.8, three at 9, one at 10, one at 11), the "primarily intended for use as a method return type" API note, and the value-based-class warning — §1.11.2–1.11.10, §3.7.2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Spliterator.html | the eight characteristics, the `SIZED`-but-not-`SUBSIZED` balanced-tree example, and the `trySplit` contract — §3.4.2–3.4.4 |
| https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html | the scheduler (ForkJoinPool, parallelism = available processors), `jdk.virtualThreadScheduler.parallelism`/`maxPoolSize`, the two pinning causes, `-Djdk.tracePinnedThreads=full|short`, the four JFR events with their default states and the 20 ms `VirtualThreadPinned` threshold, `jcmd Thread.dump_to_file -format=json`, the `Thread.ofVirtual`/`Thread.Builder` API, "scale not speed", the never-pool rule, the semaphore-instead-of-pool guidance, the ThreadLocal-caching warning, and the 10 000-threads rule of thumb — §1.18, §2.12, §3.14 |
| https://openjdk.org/jeps/444 (403 on direct fetch; content taken from the Oracle core guide above and from inside.java) | virtual threads final in 21, and the origin of the `jdk.tracePinnedThreads` property — §1.18.1, §3.14.15 `[RESEARCH]` |
| https://inside.java/2024/11/21/newscast-80/ and https://openjdk.org/jeps/491 (via search) | JEP 491: `synchronized` no longer pins in Java 24, the `jdk.VirtualThreadPinned` event retained for native/monitor pinning and extended to carry the reason and carrier identity — §1.18.23, §3.14.14–3.14.15 |
| https://openjdk.org/jeps/431 (via search) + https://docs.oracle.com/en/java/javase/21/core/creating-sequenced-collections-sets-and-maps.html | the three interfaces, the exact method sets on `SequencedCollection` and `SequencedMap`, and the full retrofit list (List, Deque, LinkedHashSet, SortedSet, LinkedHashMap, SortedMap) — §1.20.19–1.20.22 |
| https://openjdk.org/jeps/441 (via search) + https://docs.oracle.com/en/java/javase/21/language/pattern-matching-switch.html | exhaustiveness rules, the exact list of legacy selector types exempt from them, `MatchException`, the sealed-`permits` type-coverage check, and the relaxation of null-hostility — §1.15.6–1.15.20, §3.11.10 |
| https://openjdk.org/jeps/440 (via search) | record patterns final in 21, nested patterns, generic record pattern inference, and the removal of record patterns from the enhanced-`for` header before release — §1.15.10–1.15.13 |
| https://openjdk.org/jeps/409 (via search) + https://cr.openjdk.org/~gbierman/jep409/jep409-20210507/specs/sealed-classes-jls.html | same-module / same-package requirement, the direct-extension requirement, the final/sealed/non-sealed obligation, the canonical-name reason anonymous and local classes cannot be permitted, and the extension of narrowing reference conversion — §1.14.3–1.14.13, §3.10.6 |
| https://openjdk.org/jeps/395 (via search) + https://docs.oracle.com/en/java/javase/16/docs/specs/records-serialization.html | `java.lang.runtime.ObjectMethods` as the common bootstrap for `toString`/`equals`/`hashCode`, `getRecordComponents()`/`RecordComponent`, and the serialization specification (components govern the form, the canonical constructor deserialises, the custom serialization hooks are ignored) — §1.13.24–1.13.26, §3.9.3–3.9.13 |
| https://openjdk.org/jeps/378 (via search) + https://docs.oracle.com/en/java/javase/17/text-blocks/index.html + https://openjdk.org/projects/amber/guides/text-blocks-guide | the three-step compile-time algorithm in order, the re-indentation rule including the closing delimiter, `\s` as a stripping fence, `\` line continuation, and the fact that escapes are translated after stripping — §1.17.4–1.17.11, §3.13.2–3.13.3 |
| https://openjdk.org/jeps/485 (via search) + https://docs.oracle.com/en/java/javase/24/core/stream-gatherers.html | Gatherers final in 24 after previews in 22 and 23, the `Gatherer` contract, and the built-ins `fold`, `scan`, `windowFixed`, `windowSliding`, `mapConcurrent` — §1.7.22, §4.7.6 |
| https://openjdk.org/jeps/505 (via search) + https://www.happycoders.eu/java/structured-concurrency-structuredtaskscope/ | the incubator→preview lineage (428, 437, 453, 462, 480, 499, 505, 525, 533), `fork` returning `Subtask` from JEP 453, and the Java 25 rework replacing constructors with `open()` factories and `ShutdownOnFailure`/`ShutdownOnSuccess` with a `Joiner` — §1.19.3–1.19.14, §3.15.8 |
| https://openjdk.org/jeps/506 (via search) + https://openjdk.org/jeps/487 | scoped values final in Java 25, and the removal of the static `runWhere`/`callWhere` methods in Java 24 leaving only the fluent `where(...).run/call` form — §1.19.15–1.19.16 |
| https://javaalmanac.io/features/stringtemplates/ + https://bugs.openjdk.org/browse/JDK-8329949 + https://inside.java/2024/06/20/newscast-71/ | string templates previewed as JEP 430 (21) and JEP 459 (22), JEP 465 withdrawn, and the feature removed in Java 23 with no replacement shipped — §2.11.7, §3.16.16 |
| https://www.jrebel.com/blog/java-25 + https://inside.java/2025/10/17/new-in-jdk-25-2-mins/ | the Java 25 JEP list used for §3.16.18: JEP 506 scoped values, JEP 511 module imports, JEP 512 compact source files and instance `main`, JEP 513 flexible constructor bodies, JEP 505 structured concurrency, JEP 507 primitive patterns, JEP 502 stable values, JEP 470 PEM |
| https://nipafx.dev/inside-java-newscast-29/ + https://inside.java/u/BrianGoetz/ | data-oriented programming: records as nominal tuples, sealed + records as algebraic data types, and the "record cliff" framing used in §1.13.2, §1.13.28 and §2.9.2 |
| https://www.jrebel.com/blog/parallel-java-streams + https://dzone.com/articles/think-twice-using-java-8 + https://michaelbespalov.medium.com/parallel-stream-pitfalls-and-how-to-avoid-them-91f11808a16c | the production failure modes of parallel streams: common-pool sharing, I/O starvation, the custom-ForkJoinPool workaround and its unsupported status, and the N×Q threshold — §2.4 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Collector.html | the five-function contract and the three `Characteristics` values — §1.10.1–1.10.2 |
| https://education.oracle.com/java-se-21-developer-professional/pexam_1Z0-830 (objectives via the CertificationBox and course-outline summaries) | the certification objective list used as a completeness checklist; it surfaced `var` (§1.12), text blocks (§1.17), sequenced collections (§1.20.19) and the switch-expression/pattern-switch split (§1.16) as areas the current guide covers only in passing `[RESEARCH]` |

Searches that returned nothing usable: `openjdk.org` returns HTTP 403 to direct fetches, so every
JEP above was read through search summaries plus a secondary source; the write pass must re-fetch
each JEP through a mirror (`javaalmanac.io`, `bugs.openjdk.org`, or the `cr.openjdk.org` spec
drafts) before quoting JEP text verbatim. The OpenJDK LVTI style guide (§1.12.15) also 403'd, so its
guideline numbering is stated in substance rather than as `G1`–`G7` and must be verified before the
write pass prints identifiers. The `jdk.virtualThreadScheduler.maxPoolSize` default of 256
(§3.14.5) and the `LEAF_TARGET` and `suggestTargetSize` formulas (§3.5.2–3.5.3) come from secondary
sources and recall; confirm them against `AbstractTask.java` and `VirtualThread.java` in the
jdk-21+35 tag before printing the numbers. General "Java 8 to 21 interview questions" searches
returned only SEO listicles whose concept names were already covered, so §5.1 was built from the
source walks and the trap inventory instead.

---

## Gaps vs the current guide

`src/topics/04-modern-java.md` is 425 lines across 10 sections plus a 25-line checklist. Every
concept in it maps to a leaf below and nothing is dropped. Coverage of this syllabus:

| Syllabus area | Present in current guide | Missing | Shallow |
|---|---|---|---|
| §1.1 why modern Java (12) | — | all 12: the release train, LTS, preview mechanics, `--release`, class-file versions, the vendor question | — |
| §1.2 functional interfaces (20) | the 7-row core table, "primitive specialisations exist to avoid boxing" | the 43-name inventory, the `Object`-methods rule, `Predicate.not`, `andThen`/`compose` ordering, the missing shapes, `Callable` vs `Supplier`, declaring your own | a table |
| §1.3 lambdas (22) | SAM definition, `invokedynamic` mention, the `this` trap, the effectively-final trap | poly expressions and target typing, overload ambiguity, shadowing, loop-variable capture, recursion, serializable lambdas, `var` parameters, checked exceptions | two traps and a paragraph |
| §1.4 method references (16) | the four kinds, one line each | `super::`, the static-vs-unbound ambiguity, receiver evaluation timing, the capture-time NPE, generic and varargs forms, the bytecode difference | one sentence |
| §1.5 stream model (18) | "pipeline over a source", laziness, fusion, single consumption | the five normative properties, non-interference, statelessness of behavioural parameters, side-effect elision, encounter order, `unordered`, closing, `BaseStream` | good, missing the spec |
| §1.6 stream sources (18) | five sources named in one line | `iterate` 3-arg, `ofNullable`, `concat`'s stack overflow, `Matcher.results`, `RandomGenerator`, `StreamSupport`, closing I/O sources, why `Map` has none | a clause |
| §1.7 intermediate ops (24) | the op list, statefulness note, the `peek` trap, `mapMulti` named | `mapMulti` semantics, `takeWhile` prefix semantics, the flag effects, operation ordering, the missing zip/window/scan, the pre-10 `flatMap` behaviour, the inventory table | a list plus one trap |
| §1.8 terminal ops (26) | the op list, `toList` differences, the `forEach` parallel trap | `reduce`'s three contracts, associativity, `allMatch` on empty, `findFirst` vs `findAny` cost, summary statistics, the no-terminal-op silent no-op, null policy, the inventory table | a list |
| §1.9 primitive streams (16) | — | all 16, including `String.chars`, `IntStream.sum` overflow, `OptionalInt`'s thin API, the memory arithmetic | — |
| §1.10 collectors (30) | six worked examples, the `toMap` trap, the `groupingBy` trap, `teeing` named | the `Collector` contract, characteristics, the 30-method surface, Kahan summation, `filtering`/`flatMapping`, `Collector.of`, the concurrent-reduction conditions, the inventory table | six code samples, no model |
| §1.11 `Optional` (24) | purpose, three traps, the where-not-to-use list, `ofNullable` vs `of`, `stream()` | the javadoc API note, value-based semantics, the version table, `or`, `ifPresentOrElse` mechanics, the null-mapper behaviour, primitive variants, framework integration, cost | the strongest existing section; still half the leaves |
| §1.12 `var` (16) | the rules, the diamond trap, style advice | the reserved-type-name fact, the full illegal list, non-denotable types, `var` in lambda params, the LVTI style guide, numeric-literal inference | good for its length |
| §1.13 records (28) | generated members, compact constructor, the mutable-component trap, the array trap, where to use | the `Record` supertype, accessor override rules, generics, local records, float/double `equals` semantics, unspecified `hashCode`, reflection, serialization, the record cliff, JPA/Jackson reality | strong, missing internals and integration |
| §1.14 sealed types (18) | `sealed`/`permits`/`non-sealed`, the exhaustiveness argument | the same-module rule, direct-extension rule, anonymous/local exclusion, narrowing conversion, the API-compatibility cost, reflection, enum comparison | three sentences |
| §1.15 pattern matching (24) | `instanceof` patterns, flow scoping named, record deconstruction, guards, the null trap, the dominance trap | the preview lineage, `when` vs `&&`, generic inference, the enhanced-`for` removal, the exhaustiveness rule text, the legacy-type exemption, `MatchException`, total patterns, qualified enum labels, what 21 still cannot do | good, missing the rules |
| §1.16 switch expressions (18) | arrow form, `yield`, multi-label, exhaustiveness, the fallthrough fix | `return` illegality, colon-form expressions, no mixing, statement-vs-expression exhaustiveness in 21, selector types, definite assignment, the `default` trade-off | one paragraph |
| §1.17 text blocks (16) | the delimiter rule, incidental whitespace, `\` and `\s` | the three-step order, line-terminator normalisation, blank-line exclusion, trailing-whitespace stripping, the runtime siblings, constant-expression status, the regex trap | one paragraph |
| §1.18 virtual threads (24) | the model, mounting/unmounting, pinning, the three traps, backpressure note | Little's law, scheduler properties, the instrumented-blocking-point list, the `Thread.Builder` API, daemon/priority/name behaviour, JFR events, the JEP 491 delta | the second strongest section |
| §1.19 structured concurrency (16) | the concept, `ShutdownOnFailure`, the `allOf` comparison | `Subtask`, `joinUntil`, the ownership rules, `StructureViolationException`, preview status per release, the JEP 505 rework, scoped values | one code sample |
| §1.20 library additions (24) | a 10-line version bullet list | sequenced collections in detail, the `reversed()` view trap, `Files`/`String`/`HttpClient` additions, JEP 400, `RandomGenerator`, `Math.clamp` | a bullet list |
| §2.1 master tables (8) | — | no comparative table of any kind exists | — |
| §2.2 lambda cost (14) | "non-capturing instantiated once", the class-file contrast | linkage cost, megamorphic sites, CDS, composition, all four checked-exception workarounds, testability | two sentences |
| §2.3 stream cost model (16) | — | all 16 | — |
| §2.4 parallel streams (16) | the common pool, its size, the starvation trap, the four preconditions, "measure" | the parallelism flag, the custom-pool trick, N×Q, the source ranking, ordering costs, merge costs, the corruption symptoms, the default answer | the best short section in the guide |
| §2.5 collectors in anger (14) | six examples | multi-level grouping rationale, `filtering` vs `filter`, custom collectors, immutability strategies, reuse safety | examples only |
| §2.6 Optional discipline (12) | the rule list and three traps | the decision table, `or` chains, framework behaviour, the four absence strategies, cost | good |
| §2.7 `var` in practice (10) | two sentences of style advice | the review-defensible policy, the interface-pinning trap, accumulator width, refactoring risk | two sentences |
| §2.8 records in practice (16) | "excellent for DTOs, value objects, map keys, multiple returns" | Jackson, `-parameters`, validation, Spring binding, JPA reality, withers, builders, Lombok, the migration checklist | one line |
| §2.9 sealed + DOP (12) | the exhaustiveness argument | ADTs, data-oriented programming, the Visitor comparison, the expression problem, the modelling patterns, API compatibility | one paragraph |
| §2.10 pattern matching in anger (12) | one `describe` example | the refactoring path, guards vs nesting, migration risk, testing, the readability limit | one example |
| §2.11 text blocks in practice (8) | one SQL example | JSON fixtures, the regex trap, trailing-newline discipline, interpolation's absence | one example |
| §2.12 virtual threads in production (18) | the pooling trap, the CPU trap, the ThreadLocal trap, the backpressure note | Spring Boot integration, container executors, the downstream-pool shift, driver pinning, MDC, thread dumps, JFR, metrics, memory sizing, the migration checklist, the reactive comparison | four sentences, no operations |
| §2.13 structured concurrency in practice (10) | one code sample | hedging, deadlines, error inspection, scoped values, preview risk, the interview answer | one sample |
| §2.14 migration (14) | — | all 14 | — |
| §2.15 which construct (10) | — | all 10 | — |
| §3.1 lambda translation (18) | "the compiler emits `invokedynamic`; `LambdaMetafactory` spins up the implementation" | the desugaring, the six metafactory parameters, the flags, static vs dynamic arguments, hidden classes, the caching mechanism, serializable lambdas, the naming change in 21 | one sentence |
| §3.2 lambda capture and identity (10) | "non-capturing instantiated once and reused" | capture mechanics, the `this` retention leak, identity being unspecified, the listener-removal bug, JIT behaviour | one clause |
| §3.3 stream internals (20) | — | all 20 leaves | — |
| §3.4 `Spliterator` (14) | "splits the source via a Spliterator" | the interface, the eight characteristics, `SIZED` vs `SUBSIZED`, per-collection split quality, batching fallbacks, writing one | one clause |
| §3.5 parallel internals (14) | the pool and its size | `AbstractTask`, the leaf threshold formula, the op classes, ordered buffering, work stealing, `ManagedBlocker`, exception loss, nesting | one fact |
| §3.6 collector internals (10) | — | all 10 leaves | — |
| §3.7 `Optional` internals (8) | — | all 8 leaves | — |
| §3.8 `var` internals (8) | "compile-time, no runtime cost" | upward projection, the local-variable table, why not fields, poly expressions, anonymous types | one clause |
| §3.9 record internals (14) | — | all 14 leaves | — |
| §3.10 sealed internals (8) | — | all 8 leaves | — |
| §3.11 pattern matching internals (12) | — | all 12 leaves | — |
| §3.12 switch compilation (8) | — | all 8 leaves (the enum `$SwitchMap` is in 03, but the switch-expression guard is nowhere) | — |
| §3.13 text block compilation (6) | — | all 6 leaves | — |
| §3.14 virtual thread internals (18) | mounting/unmounting described correctly, the carrier pool named | `Continuation`, `StackChunk`, the state machine, the scheduler properties, FIFO vs LIFO, the blocking-point list, no preemption, compensation, the JEP 491 mechanism | the guide's best mechanism paragraph, still a third of the leaves |
| §3.15 structured concurrency internals (8) | — | all 8 leaves | — |
| §3.16 version delta (22) | a 10-bullet list covering 9, 10, 11, 14, 15, 16, 17, 21 | 8, 12, 13, 18, 19, 20, 22, 23, 24, 25, the in-flight list, and the two consolidated tables | a bullet list |
| §3.17 observability (12) | `-Djdk.tracePinnedThreads=full` only | the other 11 leaves | one flag |
| PART 4 build it (65) | **nothing** — the guide has illustrative snippets only | all 65 leaves | — |
| §5.1 interview questions (95) | — | all 95 leaves | — |
| §5.2 trap index (5) | 13 `**Trap:**` markers exist inline and all survive | the consolidated index, the version-stale table, the top-five lists | — |
| §5.3 drills (9) | the 25-line atomic concept checklist (every line survives) | the numbers, mechanism, code-reading, which-construct, symptom, dating and refactor drills, plus the review schedule | — |

Summary: of 984 leaves, roughly **105** are present in the current guide at any depth, **40** of
those at a depth the bible should keep and expand, and **879** are missing outright.

Three existing claims must be corrected rather than carried forward:

1. The guide says virtual thread pinning inside `synchronized` is "fixed in Java 24, still a live
   concern on 21" — correct, but it must cite JEP 491 and state that the JFR event survives for
   native-frame pinning, otherwise the reader will assume the diagnostic disappears too.
2. The guide says the common pool's "default size is `availableProcessors() - 1`" without noting
   that the submitting thread also participates, so the effective width is the core count. The
   write pass must state both halves. `[NUM]`
3. The guide's structured-concurrency section says "the API is still evolving across releases" —
   true, but the write pass must name the actual shape on 21 (`fork` → `Subtask`,
   `ShutdownOnFailure`) and the Java 25 rework (`open()` factories, `Joiner`), because the current
   text lets a reader recite an API that no longer exists.

Eight further claims in the guide are true for Java 21 but sit exactly where older material is
stale, and each gets a `[VERSION-TRAP]` treatment in the bible: `peek` elision (Java 9+, not
always), `flatMap` short-circuiting (fixed in 10), guarded patterns using `when` (was `&&` in
preview), record patterns in enhanced `for` (removed before 21 shipped), string templates (preview
in 21, withdrawn in 23), `ScopedValue.runWhere` (removed in 24), the `Foo$$Lambda$1` class-name
format (changed in 21), and the default charset (UTF-8 since 18, which changes what
`Files.lines(path)` does without a charset argument).
