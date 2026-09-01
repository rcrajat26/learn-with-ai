# Every pitfall and every concept heading in the set

Extracted from the 68 note files of `src/notes/detailed/04-modern-java/`.
381 inline `**Pitfall:**` callouts and 249 wrong-then-right `## Pitfalls` entries.

## `90-interview-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Treating a `Stream` reference as reusable plumbing
- Assuming `summingInt` can't overflow because "the summing collectors are safe"
- Believing the synthetic-default exception type is fixed across releases

Section headings (concept-level), in order:

- Puzzle 1 — reusing a stream
- Puzzle 2 — assigning inside a record's compact constructor
- Puzzle 3 — recompiling only the enum under an exhaustive switch
- Puzzle 4 — `summingInt` versus `summingLong` over large values
- Puzzle 5 — `BigDecimal` in a `HashSet`

## `91-interview-intermediate.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `Collectors.summingInt` is as safe as `averagingInt`
- Believing `orElse` and `orElseGet` are interchangeable style choices

Section headings (concept-level), in order:

- Puzzle 1 — `summingInt` versus `summingLong`
- Puzzle 2 — the exhaustive enum switch's synthetic default, Java 21 shape
- Puzzle 3 — a record's compact constructor and the field it cannot touch
- Puzzle 4 — a stream used twice
- Puzzle 5 — `Optional.orElse` and the fallback that runs anyway

## `92-interview-internals.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `Collectors.summingInt` is overflow-safe because `averagingInt` is
- Calling a terminal operation twice on the same `Stream` reference
- Stating "the default is 256" for the virtual-thread scheduler's `maxPoolSize`
- Treating the Java 21 synthetic switch default's exception type as unconditionally

Section headings (concept-level), in order:

- Puzzle 1 — the enum widens, the switch doesn't know
- Puzzle 2 — `summingInt` on ledger amounts
- Puzzle 3 — one stream, two terminal calls
- Puzzle 4 — the compact constructor that won't compile
- Puzzle 5 — same lambda expression, two identity questions

## `93-interview-build-it.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a memoising `computeIfAbsent` decorator is a drop-in, always-safe upgrade
- Believing `MyOptional.orElse` and `orElseGet` are interchangeable "style" choices
- Treating a hand-rolled stateful `map` as a legitimate `scan`/running-total operator
- Assuming a record gets working serialization "for free" once it's declared `Serializable`

Section headings (concept-level), in order:

- Puzzle 1 — fusion, element by element
- Puzzle 2 — the reuse guard, minus the JDK's real spliterator plumbing
- Puzzle 3 — `MyOptional.empty()`'s shared identity
- Puzzle 4 — `orElse` is eager, `orElseGet` is lazy
- Puzzle 5 — a virtual thread's `ThreadLocal` does not travel with a "session"

## `94-interview-questions-a.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a lambda is sugar for `new AnonymousClass() { ... }`
- Reusing a stream reference across two terminal operations
- Trusting `groupingBy(...).get(key)` the same way you'd trust `partitioningBy(...).get(key)`

Inline `**Pitfall:**` callouts (opening words):

- Assuming any interface with more than one method declaration in its source can't be a lambda target. **Fix:** count only the abstract methods that don't already have an `Object` im
- Believing a lambda desugars to `new SomeAnonymousClass() { ... }` and therefore behaves identically for `this` binding and allocation cost. **Fix:** treat them as two different com
- Using a lambda as a `Map` key or a `HashSet` member and expecting `equals`/identity stability across runs. **Fix:** lambdas don't override `equals`, so two functionally-identical l
- Reaching for the single-element-array trick under a `parallelStream()` because it "compiles and looks thread-safe since it dodges the effectively-final error." **Fix:** use `Atomic
- Writing `expensiveLookup()::process` inside a hot loop expecting the lookup to happen once per iteration when reused as the *same* reference — it does evaluate once per reference c
- Believing `map(this::mightThrowIOException)` will compile because "streams handle exceptions specially." **Fix:** streams don't touch exception handling at all; the functional inte
- Storing a `Stream` in a field or passing it to two different consumers expecting to run two different terminal operations on it. **Fix:** either build the pipeline twice from the s
- Using `peek` for anything beyond debugging — e.g., mutating shared state as the "real" side effect of a pipeline — because whether and how many times it runs depends on downstream
- Calling `.sorted()` on an infinite stream, or a large one, without a preceding `.limit()`, expecting laziness to save you the way it does for stateless operations. **Fix:** materia
- Using `findAny()` on a sequential stream and assuming that's proof it always returns the "actual first" element — it happens to on today's sequential implementation, but the contra
- Treating `allMatch` as "there's at least one element and every one of them passes," when it actually means "there is no element that fails" — the empty case is where that distincti
- Reaching for `filter` to "get the leading run while some condition holds" on an infinite or very large stream. **Fix:** `takeWhile` is both semantically correct for that specific q
- Swapping `collect(Collectors.toList())` for `.toList()` as a pure refactor-for-brevity, without checking whether the calling code later mutates the returned list or whether the str
- Assuming a `BinaryOperator` merge function is also the escape hatch for `null` values. **Fix:** it isn't — `toMap` rejects `null` at value-mapping time, before any duplicate-key lo

Section headings (concept-level), in order:

- 5.1.1 "What is a functional interface? Does it need `@FunctionalInterface`?"
- 5.1.2 "`Comparator` declares two abstract-looking methods — why is it still functional?"
- 5.1.3 "Is a lambda just syntactic sugar for an anonymous inner class?" — the 30-second and the 5-minute answer
- 5.1.4 "What bytecode does a lambda compile to? Walk me through the `invokedynamic`."
- 5.1.5 "What is `LambdaMetafactory` and when does it run?"
- 5.1.6 "Is the same lambda expression the same object every time?"
- 5.1.7 "What does `this` mean inside a lambda?"
- 5.1.8 "Why must a captured local be effectively final?"
- 5.1.9 "How do I increment a counter from inside a lambda?" — and why the question is the bug
- 5.1.10 "Name the four kinds of method reference and give an example of each."
- 5.1.11 "When does a bound method reference evaluate its receiver?"
- 5.1.12 "How do you throw a checked exception from inside a `map`?"
- 5.1.13 "What is a stream, and how is it different from a collection?"
- 5.1.14 "Explain laziness. What runs when, in `list.stream().filter(f).map(g).findFirst()`?"
- 5.1.15 "Does a stream process stage by stage or element by element? Prove it."
- 5.1.16 "Can you reuse a stream? What exactly happens if you try?"
- 5.1.17 "What does `peek` do and when is it not called?"
- 5.1.18 "Which stream operations are stateful, and why does that matter?"
- 5.1.19 "What is encounter order, and which operations depend on it?"
- 5.1.20 "Difference between `findFirst` and `findAny`?"
- 5.1.21 "What does `allMatch` return on an empty stream?"
- 5.1.22 "`map` vs `flatMap` vs `mapMulti`."
- 5.1.23 "`takeWhile` vs `filter`."
- 5.1.24 "How would you batch a stream into windows of 100 on Java 21?"
- 5.1.25 "How would you zip two streams?"
- 5.1.26 "`collect(toList())` vs `stream.toList()` — name three differences."
- 5.1.27 "What does `Collectors.toMap` do on a duplicate key? On a null value?"
- 5.1.28 "What map and list types does `groupingBy` return?"
- 5.1.29 "`groupingBy(p)` vs `partitioningBy(p)` — what is different about the empty case?"
- 5.1.30 "Write a collector that gives the top 3 by salary per department."
- 5.1.31 "Explain the `Collector` contract's five functions."
- 5.1.32 "When is `reduce` wrong and `collect` right?"

## `94-interview-questions-b.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `orElse` and `orElseGet` are interchangeable
- Believing `parallelStream()` is a free performance switch
- Reaching for `hashCode()` as a persisted content fingerprint

Inline `**Pitfall:**` callouts (opening words):

- treating `parallelStream()` as a free concurrency primitive for I/O-bound work. It is
- treating this as a documented, guaranteed-stable feature. There is no public API on
- believing `forEach` is "just a loop" and therefore safe the way a sequential
- picking `LinkedList` because "streams are lazy anyway" or because insertion-heavy
- using `orElse(expensiveCall())` out of habit because it reads slightly shorter than
- `isPresent()` + `get()` is not merely "less idiomatic" — it is a genuine
- assuming `map` needs `Optional.ofNullable(...)` wrapped around every mapper's return
- writing `someOptional == Optional.empty()` as a presence check, whether out of habit
- confusing `var` with genuinely dynamic-typing constructs from other languages (or
- this is exactly why the LVTI style guide's **G6** ("take care when using `var` with
- trying to assign the field directly inside the compact constructor —
- reaching for a `byte[]` or `int[]` as a record component because "it's just a value
- copying with `Collections.unmodifiableList(new ArrayList<>(limitHistory))` — a
- reaching for `hashCode()` as a cheap stand-in for a real content digest or audit
- modeling genuinely different-shaped cases as one `enum` with an ever-growing set of

Section headings (concept-level), in order:

- 5.1.33 "Why must a `reduce` combiner be associative?"
- 5.1.34 "How does a parallel stream decide how many tasks to create?"
- 5.1.35 "Which thread pool does a parallel stream use, and how big is it?"
- 5.1.36 "What happens if I do blocking I/O inside a parallel stream?"
- 5.1.37 "Can I give a parallel stream my own pool? Is that supported?"
- 5.1.38 "When is a parallel stream faster? Give me the four conditions."
- 5.1.39 "Why is `parallelStream().forEach(list::add)` broken but `collect(toList())` fine?"
- 5.1.40 "What is a `Spliterator` and what do its characteristics do?"
- 5.1.41 "Why does a `LinkedList` parallelises badly?"
- 5.1.42 "What is `Optional` for, and where should it never appear?"
- 5.1.43 "`orElse` vs `orElseGet` — show me the bug."
- 5.1.44 "Why is `isPresent()` + `get()` an anti-pattern?"
- 5.1.45 "Why is `Optional` not `Serializable`?"
- 5.1.46 "What happens if `map`'s function returns null?"
- 5.1.47 "Is `Optional.empty() == Optional.empty()` true? Should you rely on it?"
- 5.1.48 "What is `var`, and where can you not use it?"
- 5.1.49 "Does `var` have a runtime cost?"
- 5.1.50 "What does `var list = new ArrayList<>()` infer?"
- 5.1.51 "Why can't you write `var f = () -> 1;`?"
- 5.1.52 "What does a record generate for you?"
- 5.1.53 "What is a compact constructor and what is it for?"
- 5.1.54 "Are records immutable?"
- 5.1.55 "Why is an array component in a record a bug?"
- 5.1.56 "How do you make a record with a `List` component genuinely immutable?"
- 5.1.57 "Can you persist a record's `hashCode`?"
- 5.1.58 "Can a record be a JPA entity? Why not?"
- 5.1.59 "How does record deserialization differ from ordinary Java serialization?"
- 5.1.60 "How are a record's `equals`/`hashCode`/`toString` actually implemented in bytecode?"
- 5.1.61 "What does `sealed` do, and what must every permitted subtype declare?"
- 5.1.62 "Can an anonymous class be a permitted subtype?"
- 5.1.63 "What is the difference between `sealed` and `final`?"
- 5.1.64 "Sealed interface or enum — how do you choose?"

## `94-interview-questions-c.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `default` on a pattern switch catches a `null` selector
- Placing an unguarded case before the guarded case it should carve an exception out of
- Treating `-Djdk.virtualThreadScheduler.maxPoolSize` as an independent knob

Inline `**Pitfall:**` callouts (opening words):

- assuming `default` catches `null` the way it catches every other unmatched value.
- treating `MatchException` as "the switch has a bug." It almost never does — the
- writing `return` inside a switch **expression**'s block case expecting it to behave
- assuming the source-file indentation of the text block literal is preserved verbatim.
- believing text blocks get some special non-interned "multi-line string" treatment
- citing "avoid `synchronized`, use `ReentrantLock`" as a timeless virtual-thread rule.
- wrapping virtual threads in a fixed-size pool "to be safe," carried over from
- flipping `spring.threads.virtual.enabled=true` and assuming it's purely additive
- assuming `reversed()` returns a copy. It returns a **view** — mutations through the

Section headings (concept-level), in order:

- 5.1.65 "What does a sealed hierarchy buy a `switch`?"
- 5.1.66 "Why would you deliberately omit `default` from a switch?"
- 5.1.67 "What is flow scoping? Why is `s` in scope after `if (!(o instanceof String s)) return;`?"
- 5.1.68 "What happens when a pattern switch gets a null?"
- 5.1.69 "What is `MatchException` and when have you seen one?"
- 5.1.70 "Explain dominance. Why must a guarded case come first?"
- 5.1.71 "What are record patterns and how deep can they nest?"
- 5.1.72 "How does a pattern switch compile? Is it a chain of `instanceof`?"
- 5.1.73 "Switch statement vs switch expression — name three differences."
- 5.1.74 "`yield` vs `return` inside a switch."
- 5.1.75 "What is `$SwitchMap` and why does it exist?"
- 5.1.76 "How does a text block decide indentation?"
- 5.1.77 "What does `\s` do in a text block, and why would you need it?"
- 5.1.78 "Are text blocks interned?"
- 5.1.79 "Does Java have string interpolation?"
- 5.1.80 "What is a virtual thread and how is it scheduled?"
- 5.1.81 "Walk me through mounting and unmounting."
- 5.1.82 "What is pinning? What causes it on Java 21, and what changed in 24?"
- 5.1.83 "How do you detect pinning in production?"
- 5.1.84 "Should you pool virtual threads?"
- 5.1.85 "Do virtual threads help CPU-bound work?"
- 5.1.86 "You removed the thread pool. What did you also remove?"
- 5.1.87 "What breaks in a Spring Boot app when you turn virtual threads on?"
- 5.1.88 "How many virtual threads can you create, and what limits it?"
- 5.1.89 "What does `ThreadLocal` cost now?"
- 5.1.90 "What is structured concurrency and what does it guarantee?"
- 5.1.91 "How is `StructuredTaskScope` different from `CompletableFuture.allOf`?"
- 5.1.92 "Is structured concurrency final? What changed in 25?"
- 5.1.93 "What are scoped values and why not just use `ThreadLocal`?"
- 5.1.94 "What are sequenced collections and which types got them?"
- 5.1.95 "What is the single most useful thing added between Java 8 and 21, and why?"

## `build-it/01-functional-toolkit.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `andThen`/`compose` order does not matter for `Money`
- Trusting `computeIfAbsent` inside a recursive memoized function
- Catching a specific checked exception subtype off an unbounded `throws E`

Section headings (concept-level), in order:

- `MyFunction<T, R>`
- `MyPredicate<T>`
- `CheckedFunction<T, R, E extends Exception>`
- `Result<T, E>`
- The memoizing `Function` decorator
- Curry and partial application for `BiFunction`
- `TriFunction<A, B, C, R>`

## `build-it/02-mystream.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing `.filter().map()` runs as two separate passes over the whole collection
- Assuming `count()` always visits every element
- Reassigning a stream reference after calling an intermediate op on the original

Inline `**Pitfall:**` callouts (opening words):

- believing that because the fluent API *reads* left to right — `filter` then `map`
- assuming `limit(n)` on a source with side effects (a `Supplier` backed by a paid API
- writing `.sorted().limit(2)` and expecting the same cost profile as `.limit(2)`
- the belief that `IllegalStateException: stream has already been operated upon or
- putting a diagnostic `peek()` in front of a `.count()` call to "check what's flowing

Section headings (concept-level), in order:

- 1. Mental model
- 2. Why it exists
- 3. When to reach for it, and when not
- 4. How it works
- 6. A minimal concrete example
- 7. The gotcha
- 8. The definition
- 1. Mental model
- 2. Why it exists
- 3. When to reach for it, and when not
- 4. How it works
- 6. A minimal concrete example
- 7. The gotcha
- 8. The definition
- 1. Mental model
- 2. Why it exists
- 3. When to reach for it, and when not
- 4. How it works
- 6. A minimal concrete example
- 7. The gotcha
- 8. The definition
- 1. Mental model
- 2. Why it exists
- 3. When to reach for it, and when not
- 4. How it works
- 6. A minimal concrete example
- 7. The gotcha
- 8. The definition
- 1. Mental model
- 2. Why it exists
- 4. How it works
- 6. A minimal concrete example
- 7. The gotcha
- 8. The definition
- 1. Mental model
- 2. Why it exists
- 3. When to reach for it, and when not
- 4. How it works
- 6. A minimal concrete example
- 7. The gotcha
- 8. The definition

## `build-it/03-collectors-and-myoptional.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a broken `groupingBy` combiner only breaks on "big" data
- Depending on `MyOptional.empty() == MyOptional.empty()`
- Treating `summingInt` and `summarizingInt` as the same overflow story

Section headings (concept-level), in order:

- The five-function collector contract, and why a contract exists at all
- A bounded top-N collector over a `PriorityQueue`, with a correct heap-merge combiner
- A boxing-free statistics collector over a `long[]` accumulator
- The `CONCURRENT` characteristic and its three-condition fast path
- The Optional family, before the details
- `MyOptional<T>`, its shared `EMPTY`, and its null-handling contract
- Allocation cost of a five-`map` chain, with and without escape analysis

## `build-it/04-records-sealed-patterns.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing `List.copyOf` in a compact constructor gives you two distinct object identities across accessor calls
- Fixing a record's array-component `equals` bug in only one direction
- Assuming a sealed hierarchy's exhaustiveness is checked across module/JAR boundaries the way it is within one compilation
- Trusting a reflective wither's component name the way you'd trust a compiler-checked field reference

Inline `**Pitfall:**` callouts (opening words):

- ` The obvious claim to make about variant 3 is "the accessor returns
- ` Fix B needs *two* defensive `clone()` calls, not one — the compact
- ` "Sealed types make exhaustiveness a compile-time guarantee" is true
- ` The last line, `0% of 3.33 = 0`, is not a formatting bug in this
- ` "It compiles, so it's safe" does not apply here — `with(original,

Section headings (concept-level), in order:

- 1. The hand-written pre-record equivalent, counted in lines
- 2. A `List` component written three ways
- 3. An array component's `equals`/`hashCode` failure, and its two fixes
- 4. A sealed hierarchy, an exhaustive switch, and the exact error a fourth case produces
- 5. The same hierarchy as a Visitor, side by side
- 6. An expression-tree interpreter over a sealed record hierarchy
- 7. A reflective "wither" built from `getRecordComponents()` and the canonical constructor
- 8. Diff vs the compiler's actual output — `Record`, `ObjectMethods`, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch`, `MatchException`

## `build-it/05-concurrency-builds.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a virtual-thread migration removes every concurrency ceiling
- Trusting a timeout on `CompletableFuture.allOf` to have stopped the losing branch
- Blaming the pool size instead of the blocking call for common-pool starvation

Inline `**Pitfall:**` callouts (opening words):

- treating a virtual-thread migration as a blanket fix for "we can't handle
- "just use virtual threads and delete the old thread-pool tuning" is a real migration
- porting a `ThreadLocal`-cached helper (a formatter, a connection scratch buffer, a
- believing "virtual threads removed the pool, so there is no concurrency limit to worry
- wrapping a
- calling a synchronous, blocking dependency — a JDBC call, a synchronous HTTP client,

Section headings (concept-level), in order:

- Diff vs the real one

## `build-it/06-filling-the-21-gaps.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a `synchronized` block makes a stateful `map()`/`filter()` argument parallel-safe
- Assuming `Collections.synchronizedSet` fully fixes a shared-`Set` `distinctBy` predicate
- Claiming a hand-rolled `Spliterator` is `SIZED` because `estimateSize()` returns a number

Inline `**Pitfall:**` callouts (opening words):

- "I added `synchronized` around the mutation, so it's safe in parallel now." **Wrong**
- "I'll just wrap the `Set` in `Collections.synchronizedSet` and call it a day."

Section headings (concept-level), in order:

- A fixed-window batching intermediate operation via a custom `Spliterator`
- `zip` over two streams via a paired spliterator
- A running-total `scan` via a stateful mapper — and its parallel failure, proved
- `distinctBy(keyExtractor)` via a `Set`-capturing predicate — and its parallel failure, proved
- `takeUntil`, and `mapConcurrent` on virtual threads
- Diff vs `Gatherers` (Java 24): the `Gatherer` contract itself

## `build-it/07-diagnostic-harnesses.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a bound method reference defers null-checking like an equivalent lambda
- Believing `groupingBy` tolerates whatever `HashMap` tolerates
- Trusting `--release N` alone as proof of Java-N runtime behaviour
- Assuming `Collectors.summingInt` is overflow-safe because `averagingInt` is

Inline `**Pitfall:**` callouts (opening words):

- believing sealed-type exhaustiveness is a *runtime* guarantee because it is enforced so
- assuming "the constructor validates, so the object is always valid" for a plain
- reflowing a text block's closing `"""` to match the surrounding code's indentation
- treating "I compiled and tested with `--release 8`" as evidence the code will behave

Section headings (concept-level), in order:

- Mental model first
- Why this exists
- When to reach for this drill, and when not
- How it works — table D-178, then each mechanism in order
- The diagram
- A minimal concrete example — all fifteen, run for real
- The gotcha
- The definition, last
- Mental model first
- Why this exists
- When to reach for `.parallel()`, and when not
- How it works — three sweeps
- `[X-REF 16]` for the sibling treatment
- The gotcha
- Diff vs the real one
- The definition, last
- Mental model first
- Why this exists
- When this cost matters, and when it does not
- How it works — two harnesses
- The gotcha
- Diff vs the real one
- The definition, last
- Mental model first
- Why this exists
- When to reach for it, and when not
- How it works — one class, five features, real disassembly
- The gotcha
- Diff vs the real one
- The definition, last
- Mental model first
- Why this exists
- When to reach for which, and when not
- How it works — measured at three scales
- The diagram
- The gotcha
- Diff vs the real one
- The definition, last
- Mental model first
- Why this exists
- When this bites, and how to avoid it
- How it works — reproduced end to end
- The diagram
- The gotcha
- Diff vs the real one
- The definition, last
- Diff vs the real one
- The definition, last
- Diff vs the real one
- The definition, last
- Mental model first
- Why this exists
- When each kind of check matters
- How it works — four probes, one program (mostly)
- The diagram
- Diff vs the real one
- The definition, last

## `collectors/01-basics-a.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `Collectors.toList()` guarantees a mutable `ArrayList`
- Treating `toMap`'s two-argument overload as safe for streams with any possible key repetition
- Passing a `null` value into `toMap` and expecting `HashMap.put`'s permissiveness
- Using `summingInt` for a value that can plausibly exceed roughly two billion in aggregate
- Filtering upstream of `groupingBy` when the empty-group case matters

Inline `**Pitfall:**` callouts (opening words):

- assuming `Collectors.toList()` returns a specific, mutable, serializable type.
- reaching for `toMap` with a same-value merge function (`(a, b) -> a`) purely to
- assuming `toConcurrentMap`'s null
- calling `.map(Object::toString).collect(joining(", "))` on a stream of a custom type
- using `summingInt` on a value that can plausibly exceed roughly two billion in
- calling `.get()` on the result without handling the empty-stream case, which for
- reaching for the identity-less `reducing(op)` and forgetting it returns `Optional<T>`,
- wrapping `toConcurrentMap` (or any `CONCURRENT` collector) with `collectingAndThen` and

Section headings (concept-level), in order:

- The family, before the details
- The `Collector<T, A, R>` contract
- The `toX` family: `toList`, `toUnmodifiableList`, `toSet`, `toUnmodifiableSet`, `toCollection`
- `toMap`
- `joining`
- The summing / averaging / summarizing family, and Kahan summation
- `minBy` / `maxBy`
- `reducing`
- Downstream collectors: `mapping`, `filtering`, `flatMapping`, `collectingAndThen`

## `collectors/01-basics-b.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `groupingBy` iteration order reflects any meaningful sequence
- Grouping on a classifier that can be `null` in the domain
- Using `groupingBy(predicate)` where both branches must always be present
- Parallel `joining()` on a large result
- Reaching for `Collectors.summingInt` on volumes that can overflow

Inline `**Pitfall:**` callouts (opening words):

- assuming a printed `groupingBy` result reflects a meaningful key
- classifying by a field that can legitimately be `null` in the
- using `groupingBy(predicate)` for a report that must always show
- replacing `.collect(Collectors.toList())` with
- reaching for `.parallelStream().collect(Collectors.joining(","))`

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The definition
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — the three overloads
- The diagram
- The three conditions — `[SOURCE]`
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — the two overloads
- The diagram
- A minimal concrete example — `[PROVE]`
- The gotcha
- Mental model first
- Why it exists — verified against the JDK 21 source
- When to reach for it, and when not
- How it works
- The gotcha
- A minimal concrete example
- Mechanism
- Gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — the two overloads `[BUILD]`
- Gotcha
- Mechanism `[SOURCE]`
- `[PROVE]` — why all three, not fewer
- The definition
- Mental model first
- How it works — `[PROVE]`
- The diagram
- Mental model first
- Why this matters — `[NUM]` `[PROVE]`
- When to reach for it, and when not
- Mechanism
- Gotcha
- Mechanism

## `collectors/02-in-anger.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `filtering` and a pre-`filter` produce the same map
- Calling two-argument `toMap` on a classifier that is not provably unique
- Trusting `Stream.toList()` and `Collectors.toUnmodifiableList()` to behave identically
- Reaching for `summingInt` on a value that can exceed two billion

Inline `**Pitfall:**` callouts (opening words):

- treating `filtering` and a pre-`filter` as interchangeable produces silently different
- reaching for `Stream<Integer>.collect(Collectors.summingInt(...))` on a value that can
- assuming `Stream.toList()` is "just a shorthand" for `collect(toUnmodifiableList())`

Section headings (concept-level), in order:

- Shared domain types for this file
- A bounded top-N collector
- Which characteristics to declare
- A boxing-free statistics collector

## `collectors/03-internals-collectors.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `.parallelStream().collect(toList())` is always faster
- Assuming `groupingBy`'s result `Map` is unmodifiable or insertion-ordered
- Assuming `summingInt` is exempt from `IntStream.sum()`'s overflow trap
- Treating `Characteristics.CONCURRENT` as framework-enforced rather than author-promised

Inline `**Pitfall:**` callouts (opening words):

- treating `Characteristics.CONCURRENT` as something the framework enforces rather than
- believing `.parallelStream().collect(toList())` is a free win because "more cores
- assuming the `Map` `groupingBy` hands back is immutable, or that its iteration order
- assuming `summingInt` is "the safe one" because it looks simpler than
- assuming a collector's `IDENTITY_FINISH` flag is a promise about the *type* the

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha

## `cost-model/02-master-tables.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `sorted()` costs the same as `filter()`/`map()`
- Assuming `Arrays.asList` returns a resizable `java.util.ArrayList`
- Believing a lambda is sugar for an anonymous class
- Storing `Optional<T>` as a field to "document" absence
- Reaching for `Map<String, Object>` because the shape "isn't final yet"

Inline `**Pitfall:**` callouts (opening words):

- treating `sorted()` and `distinct()` as if they cost the same as `filter`/`map`
- citing a feature's preview JEP number as if it were the final one. JEP 406 describes
- believing a lambda has its own `this` because it "looks like a method body." Inside
- storing `Optional<Restriction>` as a field on `Application` because "it documents that
- modelling `Verdict` as `Map<String, Object>` with keys `"outcome"`, `"reason"`,
- assuming virtual threads make reactive programming obsolete across the board.
- treating `Arrays.asList(...)` as if it returns a plain, fully mutable

Section headings (concept-level), in order:

- The master stream cost table
- The master feature-by-version table
- Lambda vs anonymous class vs inner class vs method reference
- Six ways to say "absent"
- Five ways to carry data
- Four concurrency models
- Seven ways to get a `List`
- The one-page "which construct" index

## `functional-interfaces/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `@FunctionalInterface` is required for lambda compatibility
- Treating `f.andThen(g)` and `f.compose(g)` as order-equivalent
- Stating flatly that `Iterable` is not a functional interface

Inline `**Pitfall:**` callouts (opening words):

- engineers sometimes believe redeclaring `equals` on a
- `[TRAP]` believing `@FunctionalInterface` is required for `x -> ...` to compile
- seeing exactly one abstract method and assuming "therefore lambda-compatible" —
- believing this only matters for "very large" pipelines — the allocation is per
- writing `restrictions.stream().filter(Restriction::isActive).negate()` — that does
- reading `f.andThen(g)` as "f composed with g" (mathematical
- expecting `BiFunction.compose` to exist by analogy with `Function.compose` — it does
- hunting through `java.util.function` for a three-argument or
- stating flatly "`Iterable` is not a functional interface"
- chaining `thenComparing` calls that reference primitive key extractors without the
- trying to pass a lambda that calls a checked-exception-throwing method where a
- declaring a bespoke interface for every single lambda "for clarity"
- believing a `throws` clause on an interface method somehow

Section headings (concept-level), in order:

- The SAM definition and why `Object` methods don't count
- `@FunctionalInterface` is documentation, not the rule
- Generic abstract methods break lambda-implementability
- Why the specialisations exist — the boxing arithmetic

## `lambdas/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Mixing implicit and explicit parameter typing in one lambda
- Treating `this` inside a ported lambda as the old anonymous instance
- Shadowing an enclosing local with a lambda parameter
- Capturing the classic `for` loop's index
- Overload ambiguity between `Runnable` and `Callable<T>`
- Self-referencing a lambda from its own initializer for recursion

Inline `**Pitfall:**` callouts (opening words):

- writing `(Reservation r, y) -> ...` because "the second one is obvious from context."
- assuming the ambiguity is about `Runnable` "versus" `Callable` in general. It is not —
- copy-pasting an anonymous-class callback into a lambda and finding a compile error on
- believing "you can't capture loop variables in Java." You can — the enhanced `for`'s
- reaching for `AtomicInteger` as the default fix the moment `effectively final` shows
- assuming you can simply add `throws IOException` to the lambda the way you would to a
- trying `final Function<Integer, Integer> factorial;` split across two

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the five surface forms
- Mental model
- Why it exists
- When to reach for it, and when it fights you
- How it works
- Mental model
- Why it exists
- When it matters, and the anonymous-class alternative
- How it works
- Mental model
- Why it exists
- When it bites, and the escape hatch
- How it works
- Mental model
- Why it exists
- When to reach for which, and when not

## `lambdas/02-cost-and-choice.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming escape analysis always eliminates a capturing lambda's allocation
- Believing `summingInt` cannot silently overflow the way `IntStream.sum()` does
- Treating the anonymous-class alternative as strictly obsolete

Inline `**Pitfall:**` callouts (opening words):

- treating escape-analysis elimination as
- assuming "megamorphic" means "the code is broken" or "will throw." It
- believing `Predicate::and` reducing over a list of *predicates* is the
- discovering this

Section headings (concept-level), in order:

- 1. First-call linkage cost versus steady-state cost
- 2. Steady-state cost, non-capturing caching, and capturing allocation
- 3. The anonymous-class alternative
- 4. Lambda count and JVM startup
- 5. Megamorphic call sites
- D-170 — Where the JIT can and cannot help
- 6. Composition
- 7. The four checked-exception workarounds
- 8. Testing behaviour expressed as a lambda

## `lambdas/03-internals-translation.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming "lambdas compile to anonymous inner classes"
- Assuming a captured lambda is cheap to re-create in a loop because "the JIT will fix it"

Inline `**Pitfall:**` callouts (opening words):

- believing "it's just a lambda, the JIT will optimize it away" as a blanket excuse for writing
- treating a serializable lambda as safe to persist or

## `lambdas/04-internals-capture-and-identity.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a captured field is a snapshot, not a live view
- Removing a listener by passing a freshly-written lambda
- Leaving a `this`-capturing lambda registered forever
- Believing lambda `==` is stable because a quick manual test said so

Inline `**Pitfall:**` callouts (opening words):

- believing "capture is by value" extends to fields, then writing
- assuming a `Runnable` or listener lambda is "just a function" and
- writing test assertions or production logic of the shape
- shipping a `removeListener` call that silently no-ops, discovered
- logging a lambda directly — `log.info("handler={}", handler)` —
- treating "lambdas are just sugar for anonymous classes, and

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha

## `library-additions/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `Set.of`/`Map.of` iteration order is stable across JVM runs
- Using `takeWhile` on a property that isn't a true prefix condition
- Treating `Stream.toList()` like the mutable list `collect(Collectors.toList())` used to return
- Assuming a JDK 17→18 upgrade is charset-neutral because no charset-related code changed
- Assuming `list.reversed()` returns an independent copy
- Assuming `getFirst()` on an empty sequenced collection returns `null`

Inline `**Pitfall:**` callouts (opening words):

- Assuming `Map.of(...).keySet()` or `Set.of(...)` iterates in a fixed, reproducible
- using `takeWhile` where the predicate is not actually monotonic across the stream.
- this is a **diagnostic** improvement only — it does not change when or whether an NPE
- treating `Stream.toList()` like the mutable `ArrayList` `collect(Collectors.toList())`
- assuming an upgrade from Java 17 to 18+ is behaviour-neutral because "we
- treating `reversed()` as a defensive copy because the analogous `Collections.reverse`

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- Example
- Gotcha
- The Java 10 copy factories and unmodifiable collectors (§1.20.2)
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- Example
- Gotcha
- String's Unicode-aware trimming (§1.20.8)
- `Files` and `Path` conveniences (§1.20.9)
- The standard `HttpClient` (§1.20.10)
- Single-file source-code launch (§1.20.11)
- `Collectors.teeing` and its Java 12 neighbors (§1.20.12)
- Helpful `NullPointerException` messages (§1.20.13)
- Text block support methods (§1.20.14)
- `Stream.toList` and `Stream.mapMulti` (§1.20.15)
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- Example
- Gotcha

## `method-references/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a method reference re-reads its receiver on every invocation
- Assuming `Type::name` always compiles when both a static and instance member share the name
- Treating a constructor reference to a record as bypassing validation

Inline `**Pitfall:**` callouts (opening words):

- treating `instance::method` as if it re-reads `instance` every time the resulting
- assuming `System.out::println` re-resolves `System.out` on every call, so that
- assuming a method reference to a zero-argument instance method can *only* mean a
- assuming a constructor reference to an overloaded constructor set behaves like a
- believing this is resolvable by adding an explicit cast or type witness the way
- writing `var ref = String::valueOf;` expecting type inference to somehow pick "the"
- registering a bound method reference as a callback expecting it to track a mutable
- assuming that because the resulting `Runnable` was never invoked (`r.run()` is
- defaulting to "always prefer a method reference over a lambda when one is available,"

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- QuizStakes example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- QuizStakes example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — worked through `[PROVE]`
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works `[PROVE]`
- QuizStakes example
- The gotcha
- Mental model, condensed to a supporting fact plus one genuine primary point
- Where it is the only way to express something
- The tradeoff, stated as tradeoff not fact
- The claim to prove
- Proof, run on this machine
- Why this is the mechanism, not trivia

## `optional/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Synchronizing on or comparing `Optional` by identity
- Putting `Optional` in a `Serializable` field
- Writing `.orElse(expensiveCall())` expecting laziness
- `isPresent()` + `get()` as "the `Optional` way" to null-check
- Returning a bare `null` from an `Optional`-typed method
- Wrapping an already-empty-representable collection in `Optional`
- Using `map` where the mapper already returns `Optional`

Inline `**Pitfall:**` callouts (opening words):

- Treating `Optional` as an ordinary object you can synchronize on or
- Adding an `Optional<T>` field to a class that is `Serializable`
- Reaching for `Optional.of(value)` on a value whose nullability you
- Writing `.orElse(expensiveCall())` and assuming — because the
- Calling `.get()` reflexively, the way you would on any other
- Treating `isPresent()` + `get()` as "the `Optional` way" of doing a
- Declaring `private Optional<AgreementRef> supersededAgreement;` as
- Accepting `Optional<T>` as a parameter to "be consistent" with the
- Modelling "some restrictions may have no lifted-at timestamp yet"
- Returning a bare `null` instead of `Optional.empty()` from a method
- Wrapping a naturally-empty-representable collection type in
- Using `map` on a mapper that itself returns `Optional`, producing
- Reaching for `.map(...)` on an `OptionalInt` out of habit from
- Adding an `Optional<T>` field to a Spring Boot `@RestController`
- Avoiding `Optional` in a hot path purely from an "it allocates"

Section headings (concept-level), in order:

- Mental model
- Why it exists
- 1.11.1 — Purpose: model absence in the return type
- 1.11.2 — The javadoc API note, quoted
- 1.11.3 — Value-based class
- 1.11.4 — Not `Serializable`
- Mental model
- 1.11.9 — Defaults: `orElse(T)` and `orElseGet(Supplier)`
- 1.11.11 — `orElse` evaluates its argument eagerly, even when present `[PROVE]`
- Mental model
- Why it exists — what people did before it, and what they still do with it
- 1.11.12 — `get()` without a check, and `orElseThrow()` as its self-documenting twin
- 1.11.13 — `if (isPresent()) { get() }` is the null check plus an allocation
- Mental model
- 1.11.14 — `Optional` as a field
- 1.11.15 — `Optional` as a method parameter
- 1.11.16 — `Optional` as a collection element or a map value
- 1.11.17 — Never return `null` from an `Optional`-declared method
- 1.11.18 — `Optional<List<T>>` is almost always wrong
- Mental model
- 1.11.19 — `map`'s null-mapper behaviour `[SOURCE]` `[PROVE]`
- 1.11.20 — `flatMap` versus `map`
- 1.11.21 — Chained null-safe navigation
- 1.11.22 — the primitive-specialized siblings
- 1.11.10 — every method, every release `[NUM]` `[RESEARCH]`
- 1.11.23 — Spring Data, Jackson, and what changes without the module `[RESEARCH]`
- 1.11.24 — cost in a hot loop, escape analysis, and Valhalla `[NUM]` `[RESEARCH]`

## `optional/02-discipline.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Reaching for `orElse(expensiveCall())` because it "reads the same" as `orElseGet`
- Treating `getReferenceById` as a cheaper `findById`
- Wrapping a builder or constructor argument in `Optional` "to make it optional"
- Serialising a hand-built `ObjectMapper` without `Jdk8Module`

Inline `**Pitfall:**` callouts (opening words):

- teams that migrate from `orElse` to `orElseGet` purely by
- grep for `Optional::isPresent` and
- calling `getReferenceById` with an ID that turns out not to exist,
- the `Optional`-parameter version also breaks records' canonical
- teams that adopt `Optional` as a blanket "ban
- `assertThat(maybeClient).isEqualTo(null)` on an empty `Optional<Client>`
- "the JIT removes `Optional` allocations, so hot-path

Section headings (concept-level), in order:

- The rule set in one place
- `orElse` vs `orElseGet` vs `orElseThrow`: the decision table
- `Optional` inside a stream: `.map(this::find).flatMap(Optional::stream)`
- Spring Data: `findById` versus `getReferenceById` — a different contract, the same shape
- `Optional` as a builder argument or a constructor parameter: the anti-pattern
- The four absence strategies compared

## `optional/03-internals-optional.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `Optional.get()` is a safe accessor because of its name
- Relying on `Optional.empty() == Optional.empty()`
- Putting `Optional<T>` in a field or a DTO because it "documents optionality"

Inline `**Pitfall:**` callouts (opening words):

- treating `@ValueBased` as merely stylistic advice rather than a real constraint the
- writing `if (opt == Optional.empty())` as a "fast path" instead of `opt.isEmpty()`.
- reading `optional.get()` in someone else's code and assuming it is safe because
- designing a JPA entity or a DTO with an `Optional<T>` field, then discovering the
- benchmarking `Optional` in a microbenchmark method that is too small and too hot not to
- treating "Valhalla will fix `Optional`'s cost" as a reason to stop caring about the

Section headings (concept-level), in order:

- Concept 1 — The single `value` field and the shared `EMPTY` instance
- Concept 2 — `@jdk.internal.ValueBased` and what it forbids
- Concept 3 — `Optional.empty() == Optional.empty()` is true, and relying on it is the trap
- `map`'s one-line body (§3.7.4)
- `get()` and `orElseThrow()` are the same method under two names (§3.7.5)
- Not `Serializable`, by design, and what that buys the Valhalla trajectory (§3.7.7)
- Concept 4 — Memory: the 16-byte cost, and when escape analysis removes it
- Concept 5 — The Valhalla trajectory: `Optional` as a value class

## `pattern-matching/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a pattern variable is scoped to its enclosing braces
- Reaching for `||` to unify two type tests under one binding
- Believing pattern switch makes `null` fall through to `default` automatically
- Placing an unguarded label before its guarded twin
- Diagnosing every `MatchException` as "you forgot a case"
- Assuming a total type pattern can coexist with `default` as extra safety

Inline `**Pitfall:**` callouts (opening words):

- engineers who learned pattern variables from a single textbook example (`if (x
- a common attempted "clever" pattern is `x instanceof TypeA a || x instanceof TypeB a`
- the belief "pattern switch made `switch` accept `null` by default" is wrong and
- engineers
- the belief "`default` is always safe to include as a defensive fallback" breaks here
- the natural but wrong assumption is "`MatchException` means my switch is missing a

Section headings (concept-level), in order:

- 1. A pattern is a test, an extraction, and a binding
- 2. Flow scoping: not a block rule
- 3. Pattern switch: null, guards, and routing
- 4. Exhaustiveness, legacy exemptions, and dominance
- 5. `MatchException`
- 6. Record patterns and nested deconstruction

## `pattern-matching/02-in-anger.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a guarded case counts toward exhaustiveness
- Assuming the sealed hierarchy's guarantee survives independent redeployment

Inline `**Pitfall:**` callouts (opening words):

- deconstructing a record you're about to discard most of buys you nothing
- believing a guarded case "uses up" its type for exhaustiveness. It does
- writing `case null, default ->` for a type where the earlier cases are
- conflating `JsonNull` (a value that means "the JSON document says null
- believing that listing "all the subtypes I know about" is the same as
- treating a compiler-checked exhaustive switch as a *runtime* guarantee
- assuming "compiles to `invokedynamic`" implies "hashed, O(1) dispatch

Section headings (concept-level), in order:

- The hierarchy, once, before the details
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the four-step conversion
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example, continued in the domain
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha
- Supporting fact
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha
- Supporting fact
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- Mental model
- Why it exists — the argument, worked through
- When this actually bites
- The gotcha
- Mental model
- Why it exists
- How it works — `[PROVE]`, worked from real bytecode
- The gotcha
- Supporting fact
- Supporting fact

## `pattern-matching/03-internals-pattern-matching.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming the `tableswitch` at the end of a pattern switch's bytecode is where the real dispatch cost lives
- Assuming `case null` is free to add to a switch that used to rely on the implicit NPE
- Believing a record accessor's exception during deconstruction propagates as its original type
- Assuming `enumSwitch` is definitely what a given enum-typed pattern switch compiles to

Inline `**Pitfall:**` callouts (opening words):

- believing that because `switch` patterns use `invokedynamic`, `instanceof`
- assuming flow scoping means the JVM "knows" a variable was bound by a
- believing the `tableswitch` at offset 16 is "the real dispatch" and the
- benchmarking a pattern switch with a JMH-less loop of 100 iterations and
- citing "enum switches use a special faster bootstrap" as a settled optimization
- adding `case null` "just in case" and assuming it's free. It isn't semantically
- assuming a record pattern deconstructs a record's components without calling
- catching `IllegalStateException` (or whatever the accessor's real exception
- believing that covering every class that appears in a `permits` clause is
- assuming a broad label with a guard is safe to place before narrower unguarded

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example, minimal and concrete
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha

## `platform-and-releases/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `-source`/`-target` is equivalent to `--release`
- Believing "the default virtual-thread pool size is 256"

Inline `**Pitfall:**` callouts (opening words):

- Treating "Java 9" as a normal, feature-complete release the way Java 7 or 8 were.
- Believing an LTS release is more thoroughly tested, more stable, or built from a
- Assuming `--enable-preview` at compile time alone is enough, or assuming a preview
- Believing `-source N -target N` is a safe, complete way to build for an older
- Reading `UnsupportedClassVersionError`'s two numbers backwards — assuming the first

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The definition
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Concrete example
- The gotcha
- Mental model first
- Why it exists
- How it works
- Concrete example
- The gotcha

## `platform-and-releases/02-migration.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a Java-9-era illegal-access warning stays a warning forever
- Assuming `String.getBytes()` is safe because tests pass on the developer's laptop

Inline `**Pitfall:**` callouts (opening words):

- Teams read "Java 9 introduced modules" and assume the breakage is a Java-9-only
- "We upgraded to 18 and nothing broke" is not evidence of safety — it is evidence that
- Bumping only the JDK in CI and leaving `pom.xml`/`build.gradle` dependency versions
- Treating "worth doing" as "do it everywhere in one pass". A migration PR that both
- Bundling the language-level bump with a large feature-adoption pass "since we're

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha

## `platform-and-releases/03-internals-version-delta.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Stating "the virtual thread scheduler's maxPoolSize is 256" as a flat constant
- Claiming `summingInt` is overflow-safe like `averagingInt`
- Answering "what's new in Java N" as an undifferentiated feature list

Inline `**Pitfall:**` callouts (opening words):

- a class compiled with `--enable-preview` on Java 21 does not run on Java 22 even with
- believing an exhaustive sealed-hierarchy switch can never throw at runtime, because
- `synchronized` pins a virtual thread to its carrier on Java 21 — a virtual thread
- treating "deprecated" and "removed" as interchangeable when answering an upgrade-risk

Section headings (concept-level), in order:

- Java 8 (2014) — §3.16.1
- Java 9 — §3.16.2
- Java 10 — §3.16.3
- Java 11 (LTS) — §3.16.4
- Java 12 — §3.16.5
- Java 13 — §3.16.6
- Java 14 — §3.16.7
- Java 15 — §3.16.8 `[RESEARCH]`
- Java 16 — §3.16.9 `[RESEARCH]`
- Java 17 (LTS) — §3.16.10 `[RESEARCH]`
- Java 18 — §3.16.11 `[RESEARCH]`
- Java 19 — §3.16.12
- Java 20 — §3.16.13
- Java 21 (LTS) — §3.16.14 `[RESEARCH]`
- Java 22 — §3.16.15 `[RESEARCH]`
- Java 23 — §3.16.16 `[RESEARCH]`
- Java 24 — §3.16.17 `[RESEARCH]`
- Java 25 (LTS) — §3.16.18
- Still in flight — §3.16.19

## `platform-and-releases/04-internals-observability.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `javap -c` alone is enough evidence for a desugaring claim
- Trusting a hand-timed loop as a performance benchmark

Inline `**Pitfall:**` callouts (opening words):

- ` below.
- treating an internal, undocumented property as a stable API. `jdk.internal.lambda.dumpProxyClasses`
- ` on Java 21, `synchronized` blocks are the classic pinning cause and
- running `Thread.dump_to_file` (without `-format=json`) and expecting the same
- assuming a virtual thread pinned inside a `synchronized` block will show up in
- seeing `ReferencePipeline$2$1` or a `$$Lambda` frame in a flame graph and assuming
- ` writing `@Benchmark public long streamCount() { return reservations.stream()...count(); }`

Section headings (concept-level), in order:

- `javap -c -p -v` as the evidence discipline
- `jshell` for a ten-second experiment
- `-Djdk.internal.lambda.dumpProxyClasses=<dir>` to inspect the spun class `[RESEARCH]` `[VERSION-TRAP]`
- `-Xlog:class+load=info` to watch hidden classes appear `[X-REF 06]`
- JFR for this topic `[X-REF 20]`
- `jcmd <pid> Thread.dump_to_file -format=json <file>` for virtual threads `[RESEARCH]`
- `jcmd <pid> Thread.print` for platform threads `[X-REF 06]`
- async-profiler and the frame names you actually see `[X-REF 06]`
- JMH for every stream-versus-loop or parallel-versus-sequential claim `[X-REF 16]`
- IDE support worth using
- Static analysis for `Optional`/`Stream` misuse `[RESEARCH]`
- Confirm before you quote `[X-REF 06]`

## `records/01-basics-a.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assigning the field instead of the parameter inside a compact constructor
- Expecting a record to serialize cleanly through an old Jackson version because accessors "look like getters"
- Assuming a record can hold extra mutable state "just this once"

Inline `**Pitfall:**` callouts (opening words):

- serializing a `StakeSplit` record with an un-upgraded Jackson (pre-2.12, before
- overriding `equals` on a record without overriding `hashCode` in the same change.

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the header and what it derives
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works `[PROVE]`
- The QuizStakes worked example — the 3.33 split
- Validation and normalisation belong in the compact constructor, and the fix is reassignment, not field assignment `[TRAP]`
- Alternate constructors must delegate via `this(...)`
- An explicit canonical constructor must be at least as accessible as the record itself
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works, and the contract you now own `[TRAP]` `[X-REF 03]`
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works

## `records/01-basics-b.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Trusting a record's `List` component is safe without a compact-constructor copy
- Comparing two records with array components and expecting content equality
- Assuming `0.0 == -0.0` implies `record.equals()` treats them the same
- Persisting or hard-coding a record's `hashCode()` value
- Trying to add "just one mutable field" to an existing record

Inline `**Pitfall:**` callouts (opening words):

- believing `List.copyOf` inside the compact constructor is enough on its own regardless
- trusting a record's generated `equals` on a type with an array component because "it's
- assuming a record's `.equals()` for a floating-point component tracks `==`. It is the
- persisting a record's `hashCode()` output to a database column, embedding it in a URL,
- believing "records are serializable-safe by default." A record only gets this
- starting a type as a record because it currently looks like pure data, then hitting

Section headings (concept-level), in order:

- Records are shallowly immutable, and the accessor hands out the live reference
- The fix: defensive copies in the compact constructor and on the way out — `[BUILD]`
- An array component silently breaks `equals` and `hashCode`
- The generated `equals`: the exact per-component comparison rules — `[SOURCE]` `[PROVE]`
- `NaN` equals `NaN`, and `0.0` does not equal `-0.0`, inside a record — the opposite of `==`
- The generated `hashCode` is deliberately unspecified — never persist it
- `toString` format: `Point[x=1, y=2]`
- Records and null: components may be null unless you reject them
- Reflection over a record's shape — `[RESEARCH]`
- Record serialization: components govern the wire form, and the canonical constructor runs on the way back — `[SOURCE]` `[RESEARCH]` `[X-REF 03]`
- That closes the classic constructor-bypass validation hole — `[PROVE]` `[RESEARCH]`
- Where records fit
- Where records do not fit, and the record cliff — `[TRAP]` `[RESEARCH]` `[X-REF 08]`

## `records/02-in-practice.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing `-parameters` is what makes Jackson deserialize records
- Assigning `this.field` inside a compact constructor
- Trusting `HashSet<PriceCoordinate>` for floating-point deduplication
- Assuming a `record` can be a JPA `@Entity` because it is "just a class with fields"

Inline `**Pitfall:**` callouts (opening words):

- a team on jackson-databind 2.12–2.14 removes `-parameters` from the Maven/Gradle
- a **custom** constraint annotation carried over unchanged from a pre-record codebase —
- a fraud-detection dedup pass built on

Section headings (concept-level), in order:

- Records as request/response DTOs at the HTTP boundary
- Wiring records through the framework boundary — Jackson, `-parameters`, Bean Validation, Spring
- Why a record cannot be a JPA entity, but is an excellent projection
- Records as compound map keys
- Defensive copying, done properly
- Floating-point components: `Double.equals`, `NaN`, and `-0.0`
- Records as multiple return values `[LEAF 2.8.8]`
- Local records as stream-pipeline scratch types `[LEAF 2.8.9]`
- The "wither" pattern `[LEAF 2.8.10]` `[RESEARCH]`
- Builders for records `[LEAF 2.8.11]`
- Records and inheritance `[LEAF 2.8.12]`
- Records versus Lombok `@Value` `[LEAF 2.8.14]` `[RESEARCH]`
- Migrating an existing value class to a record `[LEAF 2.8.16]`

## `records/03-internals-records.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Persisting a record's `hashCode()` across a JDK upgrade
- Believing a record's generated `equals` is a `==`-scan on primitives
- Leaving a defensive `writeObject`/`readObject` pair on a record migrated from a plain class
- Assuming `setAccessible(true)` on a record field grants the same power it grants on any other class

Inline `**Pitfall:**` callouts (opening words):

- using a `StakeSplit`'s `hashCode()` as a cache key that survives a JDK upgrade, or
- writing a unit test that asserts `new StakeSplit(...).equals(...)` for a `Money`-typed
- porting a plain `Serializable` class to a record and leaving behind a
- adopting a mocking library that stubs behavior by reflectively swapping out a field's

Section headings (concept-level), in order:

- The `Record` class-file attribute
- `ObjectMethods.bootstrap` behind `equals`, `hashCode` and `toString`
- The generated `equals`: field-wise comparison rules
- Compact-constructor desugaring
- Record serialization and the ignored hooks
- `setAccessible` blocked on record fields

## `sealed-types/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a permitted subtype inherits closure automatically from a sealed parent
- Reaching for an anonymous class to implement a sealed interface
- Adding a defensive `default` arm to a switch over a sealed type
- Adding a permitted subtype to a sealed type published across an API boundary, treating it as a routine additive change

Inline `**Pitfall:**` callouts (opening words):

- assuming a `class` (not a `record`) that implements a sealed interface "inherits"
- believing sealing is purely a source-level, `javac`-only restriction, the way
- trying to shortcut a two-level hierarchy by listing the grandchildren directly on the
- reaching for an anonymous class as a quick one-off implementation of a sealed
- modeling something that genuinely needs per-instance data as an enum anyway, by
- adding a `default` arm defensively "just in case," which silently defeats the whole
- treating a sealed type in a shared library exactly like an internal, single-module

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Three beats (supporting fact)
- Three beats (supporting fact)
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model first
- Why it exists
- `[PROVE]` — walking the argument
- The example
- The gotcha
- Mental model first
- Why it exists
- `[RESEARCH]`
- The example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model first
- Why it exists
- `[PROVE]` — working it through
- The diagram
- The example
- The gotcha
- Mental model first
- Why it exists
- `[PROVE]` — working it through
- The example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Three beats (supporting fact)
- Three beats (supporting fact)
- Three beats (supporting fact)
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha

## `sealed-types/02-data-oriented-programming.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing `permits` is optional boilerplate once every case is in one file
- Reaching for `Result<T>` for a rare, unrecoverable failure
- Trusting an exhaustive `switch` as proof the *values*, not just the *cases*, are correct

Inline `**Pitfall:**` callouts (opening words):

- treating a sealed interface's exhaustiveness as purely an internal safety net and
- modeling `Verdict` as an `enum` with constant-specific class bodies to smuggle in
- sealing `PaymentRail`

Section headings (concept-level), in order:

- Algebraic data types in Java: sealed types are the sum, records are the product
- Data-oriented programming as Brian Goetz frames it `[RESEARCH]`
- The Visitor pattern replaced by a sealed interface plus a pattern switch `[PROVE]`
- The expression problem: sealed hierarchies versus open polymorphism `[PROVE]`
- Sealed types across a published API boundary `[TRAP]`
- When an enum is better, and when open polymorphism is better `[TRAP]`
- A state machine as a sealed interface of records
- A result type: `sealed interface Result<T>` `[X-REF 03]`
- Three canonical shapes: parse tree, protocol message set, domain event stream
- A worked domain model: sealed interfaces, records, pattern switch and text blocks together
- Testing exhaustiveness `[X-REF 16]`
- Serialising a sealed hierarchy: Jackson polymorphic typing `[RESEARCH]` `[X-REF 13]`

## `sealed-types/03-internals-sealed.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `ACC_SEALED` exists and checking for it via bytecode tooling
- Assuming a class recompiled against a newer sealed hierarchy is automatically safe once it compiles

Inline `**Pitfall:**` callouts (opening words):

- believing this failure is a `LinkageError` — a class that would not even load — and

Section headings (concept-level), in order:

- `PermittedSubclasses` is a class-file attribute, and there is no `ACC_SEALED` flag
- Load-time enforcement: sealing survives bytecode manipulation
- Same-module (or same-package) enforcement — the boundary the check actually draws
- Narrowing reference conversion over a sealed hierarchy
- `Class.isSealed()` and `Class.getPermittedSubclasses()` (supporting fact)
- The separate-compilation hazard: `MatchException`, not a link error

## `streams/01-basics-the-model.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a pipeline with no terminal operation has done something
- Reusing a stream reference for a second traversal
- Forgetting to close a file-backed stream
- Using a mutable captured variable as a stream filter's memory

Inline `**Pitfall:**` callouts (opening words):

- treating `anyMatch` as if it always scans the whole collection
- assuming `.sorted().limit(5)` is cheap because `limit` is
- relying on `HashSet` iteration order being "stable enough in
- calling `list.removeIf(...)` or `list.add(...)` on the backing
- "it worked in my test" is not evidence a behavioural parameter
- using `.peek(...)` to accumulate a side effect (a counter, a
- storing a `Stream<T>` field or passing one around expecting to
- writing an API that accepts a `Stream<T>` parameter and expects
- reaching for `.parallelStream()` on the strength of "parallel

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the four architectural facts underneath every stream
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the five, read against the source
- Anatomy — source, intermediates, terminal
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the `Sink` chain, worked through
- The diagram
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works, and the proof that short-circuiting is necessary but not sufficient
- The diagram
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- The example
- The gotcha
- Mechanism, gotcha, definition
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works, and the javadoc's own counter-example
- The diagram
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works, with the exact exception text
- The diagram
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- Mechanism, gotcha, definition
- Mechanism, gotcha, definition
- Mechanism, gotcha, definition
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the ledger
- The example
- The gotcha

## `streams/02-sources.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `Stream.generate(supplier).parallel().limit(n)` is reproducible
- Looping `Stream.concat` to join a data-dependent number of sources
- Letting a `Files.lines`-backed stream go unclosed
- Calling `.stream()` directly on a `Map`
- Appending `sorted()`/`distinct()` to an infinite-source pipeline before the short-circuit

Inline `**Pitfall:**` callouts (opening words):

- believing `Stream.generate(supplier).parallel().limit(n)` deterministically returns
- accumulating streams with `result = Stream.concat(result, next)` inside any loop whose
- treating `Files.lines(Path)` like any other stream factory and letting it go out of
- calling `.stream()` directly on a `Map` reference out of habit built from every other
- appending `sorted()` or `distinct()` to an infinite-source pipeline out of habit, the

Section headings (concept-level), in order:

- `Collection.stream()` and `Collection.parallelStream()` — the default-method escape hatch
- `Stream.of(T...)`, `Stream.of(T)`, `Stream.empty()`
- `Arrays.stream(T[])`, `Arrays.stream(T[], from, to)`, and the primitive overloads
- `Stream.ofNullable(T)` — a zero-or-one stream, the cleanest null bridge
- `Optional.stream()` — bridging a maybe-value into a pipeline
- `BufferedReader.lines()`, `String.lines()`, `String.chars()`, `String.codePoints()`
- `Pattern.splitAsStream`, `Matcher.results()`, `Scanner.tokens()`
- `Random.ints/longs/doubles` and the Java 17 `RandomGenerator` stream methods
- `Map` has no `stream()` — you stream a view
- `JarFile.stream()`, `ZipFile.stream()`, `ServiceLoader.stream()`, and `ResultSet`'s missing bridge
- `Stream.builder()` — when it beats collecting into a list first
- Any infinite source needs a short-circuiting terminal operation

## `streams/03-intermediate-operations.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `distinct()` is cheap because duplicates are rare
- Assuming `sorted()` fails at the call site for non-`Comparable` elements
- Assuming `dropWhile` removes every matching element
- Relying on `peek` for a side effect the program's correctness depends on

Inline `**Pitfall:**` callouts (opening words):

- treating `flatMap`'s short-circuiting behaviour as symmetric across JDK versions.
- assuming `distinct()`'s memory cost is proportional to the number of *duplicates*
- believing `sorted()` is lazy in the same sense `filter`/`map` are lazy — i.e., that
- `. The deeper cost story they belong to is
- assuming
- reading `takeWhile`/`dropWhile` as "`filter` that stops early" and expecting the same
- relying on `peek` for any effect whose absence would be observable — updating a
- treating any two adjacent stateless operations as freely reorderable because "streams
- assuming some `Stream` method named close to "zip" exists because the *concept* is so
- reading a blog post or Stack Overflow answer demonstrating `Gatherers.windowFixed`

Section headings (concept-level), in order:

- The hierarchy: what an intermediate operation can do to the pipeline
- Mental model
- Why it exists
- When to reach for each, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — the X-REF paragraph
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works, and why it may not run
- A minimal concrete example
- The gotcha
- Mental model
- Why it matters
- When order changes the answer versus only the cost
- How it works — the arithmetic
- The gotcha
- The missing `zip` — leaf 1.7.21
- No windowing, batching, `scan`, or `distinctBy` in Java 21 — and what fills the gap

## `streams/04-terminal-operations.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `forEach` on a parallel stream preserves list order
- `toArray()` cast to the element array type
- Swapping `Collectors.toList()` for `.toList()` and assuming identical null behaviour
- Using `reduce` with a shared mutable accumulator to "avoid the overhead of `collect`"
- Treating `allMatch(...)` on a possibly-empty collection as suspicious and guarding it
- Building a pipeline and forgetting the terminal operation
- Assuming a parallel stream's exception reporting resembles sequential exception handling

Inline `**Pitfall:**` callouts (opening words):

- assigning

Section headings (concept-level), in order:

- Supporting facts finishing out the eager, non-reducing terminals
- §2.1 The three contracts, worked through — `[SOURCE]` `[PROVE]`
- §2.2 Identity and associativity violated — `[PROVE]`
- §2.3 `min` and `max` — supporting facts
- §2.4 `reduce` with a mutable accumulator is a bug — `[TRAP]` `[PROVE]`
- Boxing cost of `collect(toList())` on a primitive stream — `[NUM]`

## `streams/05-primitive-streams.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `String.chars()` streams characters
- Trusting `IntStream.sum()`'s return type as proof of correctness
- Treating `average()`'s `0.0` fallback as always safe
- Assuming `OptionalInt` supports `map`/`flatMap`/`filter` like `Optional<T>`

Inline `**Pitfall:**` callouts (opening words):

- `"AA-610".chars().forEach(System.out::println)` does not print the characters
- ` believing
- ` trusting `IntStream.sum()`'s return type as
- ` code that

Section headings (concept-level), in order:

- 1.9.1 — `IntStream`, `LongStream`, `DoubleStream`, and why there is no `CharStream`, `BooleanStream` or `FloatStream`
- 1.9.2 — `String.chars()` returns an `IntStream` of UTF-16 code units
- 1.9.3 — `boxed()`, `mapToObj`, `asLongStream()`, `asDoubleStream()`: the ways back out
- 1.9.4 — `mapToInt` / `mapToLong` / `mapToDouble`: the ways in from an object stream
- 1.9.5 — `IntStream.range(a, b)` versus `rangeClosed(a, b)`, and the empty-range case
- 1.9.6 — `sum()`, `average()`, `max()`/`min()`, `count()`: what type comes back and why
- 1.9.7 — `summaryStatistics()` and its accessors
- 1.9.8 — the deliberately thinner `Optional` family
- 1.9.9 — `of`, `Arrays.stream(int[])`, `iterate`, `generate`, `concat`, `empty`
- 1.9.10 — `Collectors.summingInt` versus `IntStream.sum()`: the boxing difference, measured
- 1.9.11 — `IntStream.sum()` silently overflows past 2,147,483,647
- 1.9.12 — `average()` on an empty stream: `OptionalDouble.empty()`, never `0.0`
- 1.9.13 — dual-pivot quicksort, not TimSort
- 1.9.14 — `IntStream.toArray()` versus `boxed().toArray(Integer[]::new)`: measured in bytes
- 1.9.15 — the interfaces that pair with each primitive stream type
- 1.9.16 — when a primitive stream earns its keep

## `streams/06-cost-model.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming "streams are slow" or "streams are fast" as a blanket property of the syntax
- Sorting the full collection to answer a "give me the smallest one" question
- Re-streaming a fixed collection inside an outer loop
- Wrapping a checked exception inside a stream lambda purely to satisfy the functional interface

Inline `**Pitfall:**` callouts (opening words):

- engineers assume "streams are slow" or "streams are fast" as a blanket property of
- treating "streams allocate stage objects" as meaning the allocation is proportional
- setting a breakpoint on the line containing `.map(m -> m.instrument().lastFour())`
- believing "streams don't recurse, so they can't stack-overflow" because the surface
- believing that because `sorted()` is an intermediate operation, it is lazy in the same
- reaching for `sorted().findFirst()` out of habit because `sorted()` "feels like" the
- calling `distinct()` on a stream of a hand-written (non-record) domain class that
- this exact shape — a `.stream()` call written inside a `for` loop or inside another
- wrapping a checked exception in a `RuntimeException` inside a stream lambda purely to

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- `[NUM]` The three costs a loop does not pay
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- `[NUM]` What "monomorphic" costs versus "megamorphic"
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — the walk
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- Diagram
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- Diagram
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works — `[TRAP]` `[NUM]`
- Diagram
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not — `[TRAP]`
- Diagram
- The gotcha

## `streams/07-parallel-streams.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming the common pool's `getParallelism()` is the whole story
- Raising `-Djava.util.concurrent.ForkJoinPool.common.parallelism` to fix one hot call site
- Submitting a parallel stream's terminal op into a custom `ForkJoinPool` and treating it as a documented API
- Calling blocking I/O from inside a parallel stream operation
- `parallelStream().forEach(list::add)` to gather results
- Assuming `.parallelStream()` over `Files.lines(...)` parallelizes file reads
- Assuming virtual threads make `.parallelStream()` scale further

Inline `**Pitfall:**` callouts (opening words):

- raising the common pool's parallelism to "get more speed" out of one
- assuming this pattern is officially supported because it "just works"
- believing "it's just I/O in a lambda, the compiler didn't complain, it
- `parallelStream().forEach(list::add)` looks identical in shape to the
- assuming that because virtual threads are cheap and plentiful, calling
- treating `.parallelStream()` as the default tool for "make this

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works: `.parallel()` builds a fork/join task tree over the source `Spliterator`
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works, and the arithmetic behind its width
- The gotcha
- Supporting fact — the only supported tuning knob, and its process-wide blast radius
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha
- Mental model
- Why it exists as a failure mode
- When this bites, and what wins instead
- How it works — the QuizStakes identity-vendor case, worked through
- The gotcha
- Mental model
- Why this is stated as a conjunction, not a checklist
- When to reach for parallel, and when the sibling (sequential, or an owned
- How it works — the four preconditions
- A minimal concrete example — checking all four against a real QuizStakes case
- The gotcha
- Mental model
- Why it exists
- When to reach for it
- How it works — the arithmetic
- The gotcha
- Mental model
- Why it exists
- When to reach for a good source, and when the sibling — restructure the data
- How it works — the ranking
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When these operations are cheap, and when they are not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When merge cost matters, and when it doesn't
- How it works — `toList()` and `joining()`, worked through
- The gotcha
- Mental model
- Why this is the single most common parallel-stream bug
- When forEach with a shared sink is safe, and when it never is
- How it works — the exact race, from inside `ArrayList.add`
- The gotcha
- Mental model
- Why it exists
- When to reach for a collector over a hand-rolled sink
- How it works — the mechanism that makes it safe
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when the plain form wins
- How it works — the three conditions
- A minimal concrete example
- The gotcha
- Mental model
- Why this matters specifically for Java 21
- When parallel streams and virtual threads combine safely, and when they don't
- How it works
- The gotcha
- Mental model
- Why it exists
- When to reach for JMH, and when a simpler measurement suffices
- How it works
- The gotcha
- Mental model
- Why this is the closing argument of the whole file
- When `.parallelStream()` is still the right call, and when the executor wins
- How it works — the concrete default, and why
- The gotcha

## `streams/08-internals-pipeline.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `peek` always runs once per element
- Assuming `filter` and `map` are `StatefulOp`s because they can be "expensive"
- Assuming a `ConcurrentModificationException` from a stream means the stream itself is thread-unsafe

Inline `**Pitfall:**` callouts (opening words):

- assuming `peek` is "basically stateful" because it is often used to accumulate into an
- assuming `accept` alone defines a sink's behavior and that `begin`/`end` are
- assuming `wrapSink`'s backward walk means operations execute in reverse source order.
- assuming `evaluate` is called once per stream object. It is called once per *terminal
- believing the two exception messages map to "you called a terminal op twice" versus
- assuming `filter` clears `SIZED` because it is somehow "stateful about size." It is
- writing `.peek(System.out::println).count()` to "see what gets counted" and getting
- treating "`peek` didn't run" as a bug report. It is documented, intentional, and has
- assuming `.stream()` "locks in" the collection's contents at call time, the way copying

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for which
- How it works
- Example
- The gotcha
- Mental model
- Why it exists
- When to reach for it / sibling comparison
- How it works `[SOURCE]` `[RESEARCH]`
- Example
- The gotcha
- Supporting fact treatment
- Mental model
- Why it exists
- When to reach for which / the sibling relationship
- How it works `[SOURCE]`
- Example
- The gotcha
- Mental model
- Why it exists
- When to reach for it
- How it works `[SOURCE]`
- Example
- The gotcha
- Supporting fact treatment
- Mental model
- Why it exists
- When to reach for it
- How it works `[SOURCE]` `[PROVE]`
- Example
- The gotcha
- Mental model
- Why it exists
- When to reach for it / how it differs from `copyInto`
- How it works `[SOURCE]` `[PROVE]`
- Example
- The gotcha
- Mental model
- Why it exists
- When to reach for it
- How it works `[SOURCE]`
- Example
- The gotcha
- Mental model
- Why it exists
- How it works `[SOURCE]`
- Example
- The gotcha
- Supporting fact treatment
- Mental model
- Why it exists
- When it fires, and against what sibling behavior
- How it works `[SOURCE]`
- Example
- The gotcha
- Mental model
- Why it exists
- When to reach for it
- How it works `[SOURCE]` `[NUM]`
- Example
- The gotcha
- Mental model
- Why it exists
- When it applies, and the sibling that does not get it
- How it works `[SOURCE]` `[PROVE]`
- The example, walked stage by stage with depth
- The gotcha `[TRAP]`
- Mental model
- Why the change happened
- When to reach for `peek` and when not to
- How it works `[PROVE]`
- Example
- The gotcha `[TRAP]`
- Supporting fact treatment
- Supporting fact treatment
- Mental model
- Why it exists
- When to reach for which
- How it works `[PROVE]`
- The gotcha
- Supporting fact treatment
- Supporting fact treatment

## `streams/09-internals-spliterator.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a `HashMap`-backed stream splits its elements evenly under `.parallelStream()`
- Assuming `LinkedList.parallelStream()` is free parallelism
- Forgetting to mutate `this` inside a hand-written `trySplit()`

Inline `**Pitfall:**` callouts (opening words):

- ` because the syllabus tags it `[X-REF 02]`-adjacent behaviour interview candidates
- assuming `list.spliterator()` "locks in" the list's contents at the moment it is

Section headings (concept-level), in order:

- `Spliterator.OfInt` / `OfLong` / `OfDouble`
- Late-binding spliterators and the concurrent-modification detection window
- The characteristics-to-optimisation map, closing the loop

## `streams/10-internals-parallel-execution.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing `suggestTargetSize` rounds up
- Assuming the common pool uses all cores
- Trusting a caught exception to mean "only this element failed"

Inline `**Pitfall:**` callouts (opening words):

- ` teams reach for `.parallelStream()...forEachOrdered(...)` expecting
- ` `limit` on a large ordered parallel stream over a **non-`SIZED`**
- ` calling `.parallelStream()` from **multiple application threads
- because common-pool workers are daemon threads, the JVM will exit once all
- ` this makes parallel-stream exception handling fundamentally
- ` the failure mode here rarely manifests as an outright hang in

Section headings (concept-level), in order:

- `AbstractTask`: the shared recursive-split skeleton
- `suggestTargetSize` and the leaf-size arithmetic
- `LEAF_TARGET` and where the "four per core" number actually comes from
- The op implementations: one shared skeleton, nine different leaves
- `ReduceTask`: accumulate per leaf, combine pairwise up the tree
- `ForEachTask` versus `ForEachOrderedTask`: the price of encounter order
- `SliceOps`: why `limit`/`skip` on an ordered parallel stream cannot just discard work
- `Nodes` and the flat/conc-tree accumulation structure
- The common pool: parallelism, the submitting thread, and effective width
- Common-pool threads are daemon threads, and the pool is never shut down
- Work stealing: deques, push/pop at the head, steal at the tail `[X-REF 05]`
- `ForkJoinPool.ManagedBlocker`: the sanctioned way to block inside a worker, and why parallel streams never use it for you `[RESEARCH]`, `[X-REF 05]`
- Exception propagation: first exception to the joining task wins, the rest are discarded
- A parallel stream inside a parallel stream's lambda: the starvation shape

## `structured-concurrency/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `fork` returns a `Future<T>`
- Calling `Subtask.get()` before `join()`
- Swallowing `InterruptedException` inside a forked subtask
- Forgetting `--enable-preview` on Java 21
- Treating `ShutdownOnSuccess` hedging as free latency insurance

Inline `**Pitfall:**` callouts (opening words):

- the belief "structured concurrency's
- assuming `joinUntil` throwing `TimeoutException` means the subtasks have
- calling `.get()` on a `Subtask` immediately after `fork()`, before
- capturing a `StructuredTaskScope` in a field or passing it to
- the belief "I used `StructuredTaskScope`, so my code can't leak threads
- trying `javac AssessmentService.java` (no flags) against code using
- upgrading a project's JDK from 21 to 25 and expecting
- the belief "scoped values need `ThreadLocal.remove()`

Section headings (concept-level), in order:

- Mental model first
- Why it exists (the problem, concretely)
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram, embedded inline
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram, embedded inline in the flow
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram, embedded inline in the flow
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram, embedded inline in the flow
- A minimal concrete example
- The gotcha
- Supporting fact treatment
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The gotcha (this leaf is `[TRAP]`)
- Mental model first
- Why it exists as the comparison
- When each wins
- How it works `[PROVE]`
- The diagram
- The gotcha / X-ref
- Supporting fact treatment
- Mental model first
- Why it exists (the version story specifically)
- When each flag applies
- How it works
- The gotcha (`[TRAP]`)
- Mental model first
- Why it exists
- When to reach for which
- How it works (the shape, stated, not run)
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works, and the version timeline `[VERSION-TRAP]`
- The diagram
- A minimal concrete example
- The gotcha
- Supporting fact treatment

## `structured-concurrency/02-in-practice.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `joinUntil` bounds each subtask individually
- Calling `Subtask.get()` before checking `state()`
- Reaching for `ShutdownOnSuccess` on a fan-out that needs every leg

Inline `**Pitfall:**` callouts (opening words):

- the wrong belief is "these two shipped together in JEP 453 as one unit, so they'll finalize

Section headings (concept-level), in order:

- The fan-out call: one deadline, one failure policy, one return
- Hedged requests with `ShutdownOnSuccess` against two replicas
- Error handling: which exception surfaces, and how to see the rest
- Nesting scopes, and the resulting task tree `[RESEARCH]`
- Scoped values for request context, instead of `ThreadLocal` `[X-REF 20]`

## `structured-concurrency/03-internals.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `WrongThreadException` and `StructureViolationException` are the same failure
- Reading `CURRENT_OPERATOR.get()` outside any `where(...)` block and blaming `ScopedValue`

Inline `**Pitfall:**` callouts (opening words):

- treating `fork()` after `shutdown()` as an error. It isn't one — read the fork source
- believing `shutdown()` is synchronous — that once it returns, no forked subtask is
- calling `.get()` unconditionally from code that might run both inside and outside a
- assuming `ScopedValue`'s cheapness comes from "it's newer" or "it's better optimised."
- assuming a nested `where(...)` "adds" a binding to whatever's already there in a way
- copying a `StructuredTaskScope` code sample from a 2026-dated blog post — plausibly

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The stack discipline: `StructureViolationException`
- The example: `AssessmentService`'s two-way fan-out
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[RESEARCH]` `[NUM]`
- The example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- The proof
- The comparison table
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- Nested shadowing — the example
- The gotcha
- Why this table earns its own primary concept
- The gotcha

## `switch/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Writing `return` inside a switch expression's block arm
- Assuming a colon-form switch statement with all enum constants listed is exhaustive-checked

Inline `**Pitfall:**` callouts (opening words):

- engineers who learned `switch` before Java 14 reach for `return` by muscle memory inside what turns out to be a switch expression's block arm, get "return outside switch expression
- this bites hardest when refactoring an old colon-form `switch` to the arrow form one arm at a time, expecting to convert incrementally and re-test after each arm. The compiler forc
- assuming `-Xlint:fallthrough` is on by default. It is not — `-Xlint` defaults to a curated subset of checks that historically has not always included `fallthrough` in every JDK rel
- engineers who internalized "switch statements are never exhaustive-checked" from pre-21 experience assume a missing `WealthVerdict` arm here is merely a runtime bug waiting to happ
- engineers who know `switch` accepts boxed `Integer` sometimes assume by extension that it accepts boxed `Long`, since both are "just numbers in a box." The boxed-type list is exact
- treating "the switch has no `default` and therefore is exhaustively safe" as a permanent runtime guarantee rather than a compile-time snapshot. A switch compiled with no `default`

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- D-067 — the fall-through-versus-arrow-form picture
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[X-REF 03]`
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[RESEARCH]` `[TRAP]`
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[TRAP]`
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — `[PROVE]`
- D-068 — the exhaustive-versus-`default` picture, including the synthetic default's real behaviour
- A minimal concrete example
- The gotcha — `[TRAP]`
- Mental model
- Why it exists (as a historically real bug class)
- When to reach for the fix, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model
- Why the comparison matters here
- When to reach for the switch, and when to reach for the map
- How it works — the concrete cost difference
- A minimal concrete example
- The gotcha

## `switch/03-internals-switch-compilation.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing "the arrow form is just for expressions" and colon form is "for statements"
- Assuming a `String` switch is O(1) unconditionally
- Treating the exhaustive-enum-switch-expression exception type as version-stable

Inline `**Pitfall:**` callouts (opening words):

- the common belief is "a `String` switch calls `equals()` once
- "switching on an enum in a jar someone else ships is just as
- "the arrow form must be faster, because it avoids the
- "if the switch expression compiled without a `default` and

Section headings (concept-level), in order:

- `tableswitch` versus `lookupswitch`, and the density heuristic
- `switch` on `String`: hash first, equality to confirm, dispatch on a synthetic index
- `switch` on an enum: `$SwitchMap$...` protects a separately compiled switch from reordering
- The arrow form compiles to exactly the same instructions as colon-with-`break`
- Switch expressions and the operand stack: every arm leaves exactly one value at the join point
- The exhaustive enum switch expression's synthetic default — and the type it throws changed at 21

## `text-blocks/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a text block preserves source indentation exactly as typed
- Reformatting a text block and silently changing its value
- Using a text block for a regex and expecting fewer backslashes
- Forgetting that `summingInt`-style silent overflow has nothing to do with text blocks but gets confused with the "stable API" framing of this release family

Inline `**Pitfall:**` callouts (opening words):

- writing `String s = """some text""";` expecting a compact
- reformatting a text block — reindenting the whole method, say,
- building a fixed-width text file — a payout batch record for
- calling `translateEscapes()` on a string sourced from
- reaching for a text block to make a multi-line-looking regex

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- The diagram
- A minimal concrete example
- The gotcha
- Ending a text block without a trailing newline
- Quoting rules inside a text block
- Where text blocks earn their keep, and where they do not

## `text-blocks/02-in-practice.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming a text block is safe to splice caller-supplied SQL into
- Regex inside a text block with un-doubled backslashes
- Comparing a text block against a golden file without normalizing trailing newlines
- Reaching for `STR."..."` string-template syntax on a standard Java 21 build

Inline `**Pitfall:**` callouts (opening words):

- the exact failure this leaf exists to prevent — reaching for
- trusting `.formatted` to escape a substituted value that contains
- believing a text block "relaxes" backslash handling the same way
- assuming the text block and the file "obviously" match because
- writing `STR."..."` from a blog post or an LLM trained on
- embedding a payload that a non-Java stakeholder needs to edit

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists — or rather, why it does not, yet
- When to reach for what — Java 21's real options
- How it works — what "no interpolation" actually means mechanically
- A minimal concrete example — the Java 21 way to do the same thing
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not — the actual decision
- How it works
- A minimal concrete example
- The gotcha

## `text-blocks/03-internals-compilation.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming text-block `==` reliability generalizes to any two equal-content strings
- Closing a text block flush against its last content character to save a line
- Believing `stripIndent()` always mirrors a text block's normalization

Inline `**Pitfall:**` callouts (opening words):

- treating the text-block-vs-literal `==` result as evidence that "text blocks make

Section headings (concept-level), in order:

- Text block → `CONSTANT_String_info`, folding, and `==`
- The three-step transformation, in the order the JLS fixes it
- The minimal-indent computation, exactly
- `String.stripIndent()` as the named runtime sibling

## `var/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `var list = new ArrayList<>()` keeps the type you meant
- Believing `var` is resolved at runtime, like a dynamically-typed variable
- Declaring `var` as a field, parameter, or return type "because it worked for locals"

Inline `**Pitfall:**` callouts (opening words):

- believing `var` defers type
- believing `var` is a keyword like `int` or
- writing `var list = new ArrayList<>();` out of
- assuming this means `var` "sees more" of an
- believing `var` in a lambda parameter is doing
- treating "`var` is shorter" as sufficient
- ` where marked.
- writing `var totalMinorUnits = 0;` as a loop accumulator expecting `long`-sized

Section headings (concept-level), in order:

- The map before the mechanism

## `var/02-in-practice.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Believing a codebase-wide `var`-usage percentage is a quality signal
- Assuming `var` widens or erases generic information at use sites
- Treating "always use `var` after `new`" as equivalent to the §2.7.1 test

Inline `**Pitfall:**` callouts (opening words):

- treating "does it compile" as the bar for using `var`. It always compiles — type
- using `var` on a builder chain whose *builder* type, not its *built* type, is what
- believing `var` changes anything about resource-closing order or exception
- assuming `var entry` makes `entry.getKey()`/`entry.getValue()` return `Object`.
- using `var` to *avoid thinking about* a deeply nested generic shape rather than to
- believing `var` is "the same as programming to the interface, just with less
- believing `var total = 0L;` and `var total = 0;` differ only in the number of
- reaching for `var` in a lambda parameter list as if it were a general style
- reviewing a return-type-widening pull request by checking only the callers that
- adopting a team-wide `var` policy that a linter enforces mechanically by pattern

Section headings (concept-level), in order:

- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not — `[PROVE]`
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- When to reach for it, and when not
- How it works — `[NUM]`, worked with the arithmetic shown
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists — the mechanism, `[PROVE]`
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha
- Mental model first
- Why it exists — the two failure modes, worked
- When to reach for it, and when not
- How it works
- Diagram
- A minimal concrete example
- The gotcha

## `var/03-internals-inference.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming `var`'s inferred type reflects the runtime value rather than the static expression type
- Assuming a bare lambda can initialise `var` if the surrounding code makes the intended type "obvious"
- Assuming diamond with `var` always infers the useful type

Inline `**Pitfall:**` callouts (opening words):

- reaching for an explicit type the moment a lambda is involved, even
- treating `var`'s inferred type as
- ` concluding from a stripped, optimized production
- ` refactoring a `var
- `var restrictions = new ArrayList<>();` looks, to the eye, exactly as clean and

Section headings (concept-level), in order:

- Concept 1 — Standalone typing and upward projection
- Concept 2 — Poly expressions have no standalone type
- Concept 3 — Why `var` cannot be a field or a parameter type
- Concept 4 — Upward projection worked through with a concrete generic bound
- Concept 5 — `LocalVariableTable`/`LocalVariableTypeTable`: the only trace `var` leaves
- Concept 6 — `var` with an anonymous class initialiser
- Concept 7 — Diamond inference with no target type resolves to `Object`

## `virtual-threads/01-basics.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming virtual threads make an individual task run faster
- Treating `maxPoolSize`'s default as a flat 256
- Porting a `ThreadLocal` cache onto virtual threads unchanged
- Believing "use `ReentrantLock` instead of `synchronized`" is a permanent rule

Inline `**Pitfall:**` callouts (opening words):

- believing virtual threads make an individual request finish faster. They do not, and
- tuning `jdk.virtualThreadScheduler.maxPoolSize` alone and expecting `parallelism` to
- assuming a virtual thread stays on "its" carrier across a blocking call, the way code
- assuming `Executors.newVirtualThreadPerTaskExecutor()` behaves like a bounded pool —
- porting a `ThreadLocal`-based cache written for a bounded platform-thread pool
- treating `ReentrantLock` as a permanent, universal replacement for `synchronized`

## `virtual-threads/02-in-production.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming the virtual-threads flag covers every executor in the application
- Diagnosing a virtual-thread stall with `jstack`
- Reflexively raising `maximumPoolSize` on the JDBC pool after enabling virtual threads
- Treating `synchronized` avoidance as a permanent Java rule rather than a Java 21 fact

Inline `**Pitfall:**` callouts (opening words):

- Believing `spring.threads.virtual.enabled=true` makes the whole application
- Turning on `spring.threads.virtual.enabled=true` in a load test, watching CPU and
- Raising `maximumPoolSize` on the JDBC pool as the first reaction to connection
- Diagnosing a virtual-thread throughput cliff by watching `jstack` output and seeing
- Keeping a "live threads" alert threshold that was tuned for a platform-thread world
- Treating "migrate to virtual threads" and "migrate off WebFlux" as the same decision.
- assuming a library is "virtual-thread ready" just
- assuming MDC's cost is now negligible
- none specific beyond the scale problem itself —
- dispatching a CPU-bound batch job — for example, QuizStakes' nightly
- running this
- migrating low-traffic
- none specific — this is a genuine, low-friction

Section headings (concept-level), in order:

- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works — JFR events
- The measurement table
- A minimal concrete example
- The gotcha
- Mental model
- Why it exists
- When to reach for it, and when not
- How it works
- A minimal concrete example
- The gotcha

## `virtual-threads/03-internals-virtual-threads.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Assuming the default `maxPoolSize` is always 256
- Treating `synchronized` pinning as a permanent fact about virtual threads
- Expecting file I/O to yield like socket I/O
- Expecting FIFO fairness to bound how long a task holds its carrier

Inline `**Pitfall:**` callouts (opening words):

- carrying a `ThreadLocal`-based per-thread cache pattern forward from a
- reaching for the JSON thread dump to diagnose a suspected pinning-by-

## `which-construct/02-which-construct.md`

Wrong-then-right entries in its `## Pitfalls` section:

- Wrapping a blocking I/O call in `.parallelStream()` "to make it concurrent"
- Treating `Optional<List<T>>` as more correct than a plain empty `List<T>`
- Believing a sealed hierarchy can never be extended once declared

Inline `**Pitfall:**` callouts (opening words):

- wrapping a blocking
- calling `.get()` directly on an `Optional` returned from a repository lookup — it
- modelling `Account` as a record because "it's just data" — the fix is a final class
- believing "sealed"
- pasting a fixed-width report layout into a text block and finding every line's
- forgetting `throwIfFailed()` after `join()`

Section headings (concept-level), in order:

- D-124 — the index, before the streets

