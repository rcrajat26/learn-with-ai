# 04 — Modern Java (8 → 21)

What changed since Java 8, and — more importantly for interviews — what each feature costs and where
it silently misbehaves. Interviewers probe here to see whether you use these idiomatically or
cargo-cult them.

---

## 1. Lambdas and functional interfaces

A **functional interface** has exactly one abstract method. `@FunctionalInterface` makes the compiler
enforce that. A lambda is an implementation of one.

Lambdas are **not** anonymous classes. The compiler emits an `invokedynamic` instruction; at first
execution, `LambdaMetafactory` spins up the implementation. A non-capturing lambda is instantiated
once and reused; an anonymous class allocates per instance and generates a `.class` file per site.

Core interfaces in `java.util.function`:

| Interface | Signature | Typical use |
|---|---|---|
| `Function<T,R>` | `R apply(T)` | `map` |
| `BiFunction<T,U,R>` | `R apply(T,U)` | `merge`, `reduce` |
| `Predicate<T>` | `boolean test(T)` | `filter` |
| `Consumer<T>` | `void accept(T)` | `forEach` |
| `Supplier<T>` | `T get()` | lazy values, `orElseGet` |
| `UnaryOperator<T>` | `T apply(T)` | `replaceAll` |
| `BinaryOperator<T>` | `T apply(T,T)` | `reduce` |

Primitive specializations (`IntPredicate`, `ToIntFunction`, `IntUnaryOperator`, …) exist purely to
avoid boxing. Use them in hot code.

Method references have four forms: static (`Integer::parseInt`), bound instance
(`System.out::println`), unbound instance (`String::length` — the receiver becomes the first
parameter), and constructor (`ArrayList::new`).

**Trap:** `this` inside a lambda refers to the *enclosing* instance, unlike in an anonymous class where
it refers to the anonymous instance. This changes behaviour when you port anonymous classes to
lambdas.

**Trap:** lambdas capture effectively-final locals only. Wanting to mutate a counter from inside a
lambda is a signal you should be using `reduce`, a collector, or an `AtomicInteger` — not a workaround.

---

## 2. Streams

A stream is a **pipeline over a source**, not a data structure. It stores nothing and does not mutate
the source.

Three parts: source (`collection.stream()`, `Stream.of`, `Arrays.stream`, `IntStream.range`,
`Files.lines`), zero or more **intermediate** operations (lazy, return a stream), and one **terminal**
operation (triggers execution).

### Laziness and fusion
Nothing runs until the terminal operation. The pipeline then processes elements **one at a time
through the whole chain**, not stage by stage. That is what makes short-circuiting work:
`list.stream().filter(expensive).findFirst()` stops at the first match rather than filtering
everything.

Intermediate: `filter`, `map`, `flatMap`, `distinct`, `sorted`, `limit`, `skip`, `peek`, `takeWhile`,
`dropWhile` (9+), `mapMulti` (16+).
Terminal: `forEach`, `collect`, `toList`, `reduce`, `count`, `anyMatch`/`allMatch`/`noneMatch`,
`findFirst`/`findAny`, `min`/`max`, `toArray`.

**Stateful** operations (`sorted`, `distinct`, `limit`) need to buffer or track state, which breaks
full laziness and hurts parallel performance. `sorted` on an infinite stream never terminates.

**Trap:** a stream can be consumed once. A second terminal operation throws
`IllegalStateException: stream has already been operated upon or closed`.

**Trap:** `peek` is for debugging only. Its Javadoc explicitly says so, and the JDK is permitted to
skip it entirely — since Java 9, `stream.peek(...).count()` may not invoke peek at all, because count
can be answered from the source's size without traversing. Never put side effects in `peek`.

**Trap:** side effects in `forEach` on a parallel stream (adding to an `ArrayList`) corrupt the list.
Collect instead; collectors handle the combining correctly.

### Collectors

```java
// group and count
Map<Dept, Long> byDept = employees.stream()
    .collect(groupingBy(Employee::dept, counting()));

// group and average a field
Map<Dept, Double> avgSalary = employees.stream()
    .collect(groupingBy(Employee::dept, averagingDouble(Employee::salary)));

// group and map to a different downstream shape
Map<Dept, List<String>> namesByDept = employees.stream()
    .collect(groupingBy(Employee::dept, mapping(Employee::name, toList())));

// group into a specific map type with a set downstream
Map<Dept, Set<String>> sorted = employees.stream()
    .collect(groupingBy(Employee::dept, TreeMap::new, mapping(Employee::name, toSet())));

// two-way split
Map<Boolean, List<Employee>> split = employees.stream()
    .collect(partitioningBy(e -> e.salary() > 100_000));

// to a map, with an explicit merge function for duplicate keys
Map<String, Employee> byEmail = employees.stream()
    .collect(toMap(Employee::email, e -> e, (a, b) -> a));
```

**Trap:** `Collectors.toMap` throws `IllegalStateException: Duplicate key` when two elements produce
the same key, and **throws NPE if a value is null** (unlike HashMap, which accepts null values).
Always supply the merge function; use `toMap(k, v, merge, HashMap::new)` if you need nulls.

**Trap:** `groupingBy` returns a `HashMap` with `ArrayList` values — no order guarantee. Supply a map
factory if order matters.

`Collectors.teeing` (12+) runs two collectors and merges the results — useful for
min-and-max-in-one-pass.

### toList()
Java 16 added `stream.toList()`. It is shorter than `collect(Collectors.toList())` but returns an
**unmodifiable** list, whereas `Collectors.toList()` returns a mutable `ArrayList`. Swapping one for
the other can cause an `UnsupportedOperationException` at runtime. `stream.toList()` does permit null
elements, unlike `Collectors.toUnmodifiableList()`.

### Parallel streams
`.parallel()` splits the source via a `Spliterator` and runs on the **shared ForkJoinPool.commonPool**,
whose default size is `availableProcessors() - 1`.

**Trap:** the common pool is shared by the entire JVM. One long or blocking parallel stream starves
every other parallel stream, `CompletableFuture` default execution, and any library using it. Never
run blocking I/O in a parallel stream.

Parallel pays off only with: a large N, an expensive per-element operation, a cheaply splittable source
(`ArrayList`, arrays, `IntStream.range` — not `LinkedList` or `Files.lines`), and no shared mutable
state. Otherwise the split/merge overhead loses. Measure; do not assume.

For blocking work, use your own `ExecutorService` with `CompletableFuture`, or virtual threads.

---

## 3. Optional

`Optional<T>` is a container that models "a value may be absent" **in a return type**. Its purpose is
to force the caller to acknowledge absence at the type level.

```java
Optional<User> byId(String id);

String name = byId(id).map(User::name).orElse("unknown");
byId(id).ifPresentOrElse(this::render, this::renderEmpty);
User u = byId(id).orElseThrow(() -> new NotFoundException(id));
```

**Trap:** `orElse` evaluates its argument **eagerly, even when the Optional is present**.
`opt.orElse(expensiveCall())` calls `expensiveCall()` every time. Use `orElseGet(this::expensive)` for
anything with a cost or a side effect.

**Trap:** `opt.get()` without a presence check throws `NoSuchElementException` and defeats the entire
point. Use `orElseThrow()`, which is the same thing but self-documenting.

**Trap:** `if (opt.isPresent()) { opt.get() ... }` is the null check you were trying to replace, with
extra allocation. Use `map`/`filter`/`ifPresent`.

Where **not** to use Optional: fields (it is not `Serializable` and adds an allocation per instance),
method parameters (overload or accept null instead), collection elements (use an empty collection),
and anything performance-critical in a tight loop. Return type only, essentially.

Never return `null` from a method declared to return `Optional`.

`Optional.ofNullable(x)` for maybe-null, `Optional.of(x)` when null is a bug (it throws NPE — which is
often what you want). `stream()` (9+) turns an Optional into a 0-or-1 stream, letting you write
`.flatMap(Optional::stream)`.

---

## 4. var

Local variable type inference (Java 10). The type is inferred from the initializer at compile time;
Java remains statically typed and there is no runtime cost.

Rules: locals with an initializer, `for` loop variables, and try-with-resources only. Not fields, not
parameters, not return types. Not `var x = null`, and not without an initializer.

Use it when the right-hand side already states the type
(`var users = new ArrayList<User>()`) or when the type is unpronounceable. Avoid it when the
initializer is an opaque method call (`var result = service.process(x)` costs the reader an IDE
lookup) and when it hides a boxing or a diamond-inference surprise.

**Trap:** `var list = new ArrayList<>()` infers `ArrayList<Object>` — the diamond has no target type
to infer from.

---

## 5. Records

A record is a transparent carrier for immutable data (Java 16). The compiler generates a canonical
constructor, private final fields, accessor methods named after components (`name()`, not
`getName()`), plus `equals`, `hashCode` and `toString` from all components.

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {                              // compact constructor
        Objects.requireNonNull(amount);
        Objects.requireNonNull(currency);
        if (amount.scale() > 2) throw new IllegalArgumentException("too precise");
    }
    public Money plus(Money other) {
        if (!currency.equals(other.currency)) throw new IllegalArgumentException();
        return new Money(amount.add(other.amount), currency);
    }
}
```

The **compact constructor** has no parameter list and no explicit field assignment — you validate or
reassign the parameters, and the compiler assigns them to the fields afterwards. That is where
normalization goes.

Records are implicitly final, cannot extend a class, and cannot declare instance fields beyond the
components. They can implement interfaces, declare static members and instance methods, and be nested
or local.

**Trap:** a record is *shallowly* immutable. `record Team(String name, List<Player> players)` hands out
the same mutable list the caller passed, and the accessor returns a live reference. Copy in the compact
constructor:

```java
public record Team(String name, List<Player> players) {
    public Team {
        players = List.copyOf(players);   // reassign the parameter — this is the fix
    }
}
```

**Trap:** array components break `equals`/`hashCode`, because the generated implementations use
`Arrays`-unaware `Objects.equals`, which is reference identity for arrays. Use a `List` instead.

Records are excellent for DTOs, value objects, compound map keys, and multiple return values.

---

## 6. Sealed types and pattern matching

`sealed` (Java 17) restricts which types may extend or implement a type. Every permitted subtype must
be `final`, `sealed`, or explicitly `non-sealed`.

```java
public sealed interface Shape permits Circle, Rectangle, Triangle {}
public record Circle(double radius) implements Shape {}
public record Rectangle(double w, double h) implements Shape {}
public record Triangle(double base, double height) implements Shape {}
```

Combined with a pattern-matching switch (Java 21), the compiler knows the complete set and enforces
**exhaustiveness**:

```java
double area = switch (shape) {
    case Circle c        -> Math.PI * c.radius() * c.radius();
    case Rectangle r     -> r.w() * r.h();
    case Triangle t      -> 0.5 * t.base() * t.height();
};   // no default needed — compiler verified all cases
```

The value of omitting `default`: when someone adds a fourth shape, every exhaustive switch **fails to
compile** and you are told exactly where to update. With a `default` branch you get a silent runtime
fallthrough instead. That is the whole point of sealed hierarchies.

Record deconstruction patterns and guards:

```java
String describe(Shape s) {
    return switch (s) {
        case Circle(double r) when r > 100 -> "huge circle";
        case Circle(double r)              -> "circle of radius " + r;
        case Rectangle(double w, double h) when w == h -> "square";
        case Rectangle r                   -> "rectangle";
        case Triangle t                    -> "triangle";
    };
}
```

`instanceof` patterns remove the cast: `if (o instanceof String s && s.length() > 3)`. The binding
variable's scope is flow-sensitive — `s` is in scope exactly where the compiler can prove the test
passed.

**Trap:** a `switch` on a reference type throws `NullPointerException` on null unless you write an
explicit `case null` (allowed since 21). Old `switch` on enums/strings behaved the same way; the fix
is now available in the language.

**Trap:** case order matters with patterns. A more general pattern before a specific one is a compile
error (dominance checking), which is helpful — but a `when` guard changes the analysis, so a guarded
case must precede its unguarded twin.

---

## 7. Text blocks and switch expressions

**Text blocks** (Java 15) — triple-quoted multi-line strings. Incidental leading whitespace is
stripped based on the least-indented line *including the closing delimiter*, so the closing `"""`
position controls the indentation. `\` at end of line suppresses the newline; `\s` preserves a
trailing space.

```java
String query = """
        SELECT id, name
        FROM users
        WHERE status = ?
        """;
```

**Switch expressions** (Java 14) — `switch` produces a value, uses `->` (no fallthrough, no `break`),
allows multiple labels per case (`case MON, TUE ->`), and uses `yield` inside a block body. Expression
switches must be exhaustive. This eliminates the classic missing-`break` fallthrough bug.

---

## 8. Virtual threads (Java 21)

A virtual thread is a `Thread` scheduled by the JVM onto a small pool of **carrier** platform threads
(a dedicated ForkJoinPool, default parallelism = CPU count). Creating one costs a few hundred bytes,
not a 1 MB stack, so millions are feasible.

**Mounting/unmounting is the mechanism.** When a virtual thread hits a blocking operation that the JDK
has instrumented (socket I/O, `Thread.sleep`, `BlockingQueue`, most `java.util.concurrent` locks), the
JVM captures its stack into the heap, **unmounts** it from the carrier, and the carrier runs another
virtual thread. When the operation completes the stack is copied back and the thread is remounted.
Blocking becomes cheap, so the thread-per-request model works again without async plumbing.

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (var task : tasks) executor.submit(task);
}   // close() waits for all tasks
```

**Pinning** is the failure mode. A virtual thread that blocks while pinned cannot unmount and holds
its carrier hostage. Causes:
- Blocking inside a `synchronized` block (fixed in Java 24, still a live concern on 21).
- Blocking inside a native frame (JNI).

The fix on 21 is to replace `synchronized` with `ReentrantLock` around any blocking section. Diagnose
with `-Djdk.tracePinnedThreads=full`.

**Trap:** pooling virtual threads is pointless and harmful. They are designed to be created per task
and discarded. `newFixedThreadPool` of virtual threads reimposes the limit you were escaping.

**Trap:** virtual threads do **not** help CPU-bound work. There are still only N cores. They help
exactly one thing: workloads dominated by blocking I/O where thread count was the bottleneck.

**Trap:** `ThreadLocal` still works but its economics invert — a million virtual threads each holding
a ThreadLocal cache is a memory problem. Scoped values (preview) address this.

Also note virtual threads make thread pools a *worse* place to enforce backpressure: if you remove the
pool, you removed the queue limit too. Add an explicit semaphore or bounded queue.

---

## 9. Structured concurrency (preview)

Treats a group of concurrent subtasks as a single unit of work with a defined lifetime, so an error or
cancellation in one propagates predictably instead of leaking orphaned threads.

```java
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Supplier<User>  user  = scope.fork(() -> fetchUser(id));
    Supplier<Order> order = scope.fork(() -> fetchOrder(id));
    scope.join();                 // wait for both
    scope.throwIfFailed();        // propagate the first failure
    return new Dashboard(user.get(), order.get());
}   // scope close cancels any still-running forks
```

The guarantee: subtasks cannot outlive the block. `ShutdownOnFailure` cancels siblings on the first
error; `ShutdownOnSuccess` cancels the rest on the first success (hedged requests). Compare with
`CompletableFuture.allOf`, where a failure leaves the other futures running and cancellation is
advisory. The API is still evolving across releases — know the concept and the guarantee, and say so.

---

## 10. Everything else worth knowing by version

- **9** — module system (JPMS), `List.of`/`Map.of`, `Stream.takeWhile`/`dropWhile`,
  `Optional.stream`, private interface methods, JShell.
- **10** — `var`, `List.copyOf`, `Collectors.toUnmodifiableList`.
- **11** — LTS. `String.isBlank`/`strip`/`lines`/`repeat`, `Files.readString`/`writeString`, the new
  `HttpClient` (HTTP/2, async), single-file source execution, `var` in lambda parameters.
- **14** — switch expressions, helpful NullPointerException messages (which tell you *which* reference
  was null — enabled by default since 15).
- **15** — text blocks.
- **16** — records, `instanceof` patterns, `Stream.toList`.
- **17** — LTS. Sealed classes, `RandomGenerator` API.
- **21** — LTS. Virtual threads, pattern matching for switch, record patterns, sequenced collections
  (`SequencedCollection` with `getFirst`/`getLast`/`reversed` — a uniform API finally added to List,
  Deque and LinkedHashMap).

---

## Atomic concept checklist

- [ ] A functional interface has one abstract method; a lambda compiles to `invokedynamic`, not an anonymous class.
- [ ] `this` in a lambda is the enclosing instance, not the lambda.
- [ ] Streams are lazy and fused element-by-element; nothing runs until the terminal operation.
- [ ] A stream can be consumed only once.
- [ ] `peek` may be skipped entirely by the JDK — debugging only, never side effects.
- [ ] `Collectors.toMap` throws on duplicate keys and on null values; supply a merge function.
- [ ] `groupingBy` returns HashMap/ArrayList by default; pass factories for ordering.
- [ ] `stream.toList()` is unmodifiable; `collect(toList())` is a mutable ArrayList.
- [ ] Parallel streams run on the shared common pool; blocking in one starves the whole JVM.
- [ ] Parallel needs large N, expensive elements, a splittable source, and no shared mutable state.
- [ ] `orElse` evaluates eagerly; use `orElseGet` for anything expensive.
- [ ] Optional is for return types, not fields, parameters, or collection elements; never return null from one.
- [ ] `var` is compile-time inference with no runtime cost; `new ArrayList<>()` infers `ArrayList<Object>`.
- [ ] A record's compact constructor validates and normalizes by reassigning parameters.
- [ ] Records are shallowly immutable — copy mutable components in; avoid array components entirely.
- [ ] Sealed + exhaustive switch turns "someone added a subtype" into a compile error instead of a runtime bug.
- [ ] A pattern switch NPEs on null unless you write `case null`.
- [ ] Text block indentation is set by the least-indented line including the closing delimiter.
- [ ] Switch expressions have no fallthrough and must be exhaustive.
- [ ] Virtual threads unmount from their carrier on instrumented blocking calls; that is the whole mechanism.
- [ ] Pinning (blocking inside `synchronized` or a native frame) defeats virtual threads; use ReentrantLock on 21.
- [ ] Do not pool virtual threads, and do not expect them to help CPU-bound work.
- [ ] Removing thread pools removes your backpressure; add a semaphore.
- [ ] Structured concurrency guarantees subtasks cannot outlive their scope, unlike `CompletableFuture.allOf`.
- [ ] Java 21 sequenced collections give List/Deque/LinkedHashMap a uniform `getFirst`/`getLast`/`reversed`.