# 04 Modern Java — `Optional` — INTERNALS (§3.7)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [`Optional` — discipline](02-discipline.md) · Next: [`var` — basics](../var/01-basics.md)

`Optional` is the topic where "it's just a box" and "I know exactly what it costs" turn out to be
two different levels of understanding, and interviewers at the staff level probe for the second.
This file opens the class up: one field, one shared empty instance, an annotation that changes
what the compiler and the JIT are allowed to assume about it, and a completely mechanical
explanation of why the whole thing usually costs nothing at runtime.

---

## The shape of the class, before anything else

```java
@jdk.internal.ValueBased
public final class Optional<T> {
    private static final Optional<?> EMPTY = new Optional<>(null);
    private final T value;
    // map, filter, orElse, ifPresent, stream, etc. — all read this one field
}
```

That is the entire state of an `Optional`: a `final` class (no subclassing, ever), one `private
final T value` reference field, and one `private static final Optional<?> EMPTY` shared instance
that every "no value" case reuses instead of allocating. Everything else in the class — `map`,
`filter`, `orElse`, `ifPresent`, `stream` — is a method built on reading that single field and
branching on whether it is `null`. There is no boolean "present" flag; presence is `value != null`,
checked directly. Keep that one picture in your head for the rest of this file: a wrapper with
exactly one payload slot, and a shared sentinel for "empty," annotated so that the JVM is free to
optimize it aggressively because you have promised never to depend on which particular empty
instance you are holding.

---

### Concept 1 — The single `value` field and the shared `EMPTY` instance

**Mental model.** `Optional<Client>` is not a container with metadata about presence; it *is* a
reference, wearing a coat. Strip the coat and you have exactly the `Client` reference you would
have held anyway, plus the coat's own header. There is nothing else inside. When the value is
absent, every `Optional` in the entire JVM that represents "absent" is the *same object* —
allocated once, at class-init time, and handed out forever after.

**Why it exists.** Before `Optional` (Java 8), "no value" was represented by returning `null` and
documenting it — or not documenting it — in a Javadoc comment nobody read until the
`NullPointerException` fired in production. `Optional` gives "might not have a value" a type, so
the compiler forces the caller to unwrap it (or blow up explicitly) instead of silently propagating
`null` three call frames deeper. The single-field design keeps that promise cheap: wrapping a
reference in "this might be absent" should not cost more than a second reference and a null check.

**When to reach for it, and when not.** `Optional<T>` as a *return type* for "a value that
genuinely may not exist" — a `Client` lookup that can miss, a config value that may be unset. Not
as a field type (it is not `Serializable`, and it doubles your object graph's allocation for a
concept that a nullable field with a documented contract already expresses); not as a method
parameter (forces every caller to wrap, for no benefit — pass an overload or a nullable parameter
instead); not as a collection element (the collection's own emptiness already expresses "no
value," making `Optional<T>` redundant and worse for iteration and `getClass` reflection). The
sibling it loses to inside a hot loop is a **plain nullable reference with a null check** — same
information, zero extra allocation, zero extra dereference. `Optional` wins when the *type signature*
carrying the intent to a caller who does not read the Javadoc is worth more than that one
allocation, which in application code — not in a stake-settlement inner loop processing millions
of events per second — is almost always true.

**How it works.** The two fields are declared exactly as shown above. `EMPTY` is constructed once,
at class-initialization time, by the private constructor `Optional(T value) { this.value = value; }`
called with `null`. Every subsequent call to `Optional.empty()` does not construct anything — it
casts the shared `EMPTY` reference to the caller's generic type and returns it:

```java
public static<T> Optional<T> empty() {
    @SuppressWarnings("unchecked")
    Optional<T> t = (Optional<T>) EMPTY;
    return t;
}
```

The `@SuppressWarnings("unchecked")` is not decorative — the cast from `Optional<?>` to
`Optional<T>` is an unchecked cast that the compiler cannot verify, and it is safe only because
`EMPTY`'s payload is `null` for every `T`: there is no `T`-typed value inside it to be wrong about.
This is the same erasure trick that lets `Collections.emptyList()` hand back one shared
`EMPTY_LIST` for every element type — a value-less generic container has nothing type-specific to
share incorrectly.

![D-146 — Inside `Optional`](../diagrams/D-146-inside-optional.svg)
**D-146** — Inside `Optional`

The diagram shows what actually sits on the heap: an `Optional<Client>` wrapping a present client
is a 16-byte object header (Java 21's default compressed-oops layout — the mark word and the
compressed class pointer) plus one 4-byte compressed reference to the `Client`, rounded up to the
JVM's 8-byte object alignment, for **24 bytes total**. It also shows the shared `EMPTY` drawn once,
with two independent `Optional.empty()` call sites both pointing at that same object and the `==`
between them annotated `true` — the fact §3.7.3 proves next.

**Example.**

```java
public final class ClientLookup {

    private final Map<ClientId, Client> byId;

    public ClientLookup(Map<ClientId, Client> byId) {
        this.byId = byId;
    }

    public Optional<Client> findById(ClientId clientId) {
        return Optional.ofNullable(byId.get(clientId));
    }
}
```

`byId.get(clientId)` returns either a `Client` reference or `null`, exactly as `Map.get` always
has. `Optional.ofNullable` wraps whichever it got: a present `Client` produces a freshly allocated
24-byte `Optional`, and a miss produces the shared `EMPTY` with no allocation at all. A caller doing
`clientLookup.findById(clientId).map(Client::displayName).orElse("unknown")` never has to null-check
by hand, and never allocates more than the one `Optional` instance per present result.

**Gotcha.** People assume `Optional.of(x)` and `Optional.empty()` cost the same because "they're
both just wrapping." They do not: `of` and `ofNullable`-with-a-value allocate a new object every
single call; `empty()` and `ofNullable(null)` allocate nothing, ever, for the lifetime of the JVM.
A hot path that returns `Optional.empty()` a million times a second pays for exactly one object,
created once.

> **`Optional<T>` is a `final` class holding one `private final T value` field, with every "absent"
> instance sharing the single class-level `EMPTY` constant rather than allocating.**

---

### Concept 2 — `@jdk.internal.ValueBased` and what it forbids

**Mental model.** The annotation is a promise the *author* of `Optional` extracted from every
*caller*: treat two equal instances as interchangeable, and never treat an `Optional` reference as
an identity — never lock on it, never rely on `==` meaning anything beyond "happens to be the same
object right now," never assume a future JDK keeps allocating a distinct object per call the way
this one does. In exchange for that promise, the JVM is free to do things to `Optional` instances
that it could never safely do to an object whose identity mattered — including, eventually, not
allocating one at all.

**Why it exists.** Java's object model gives every object monitor lock support and identity
comparison `==` for free, whether or not the class's author wanted either. For a genuine value type
like `Optional` — where the entire meaning of an instance is "the value inside it," with no
separate identity worth preserving — that free identity is a liability: it lets buggy code
synchronize on a shared constant like `EMPTY` and silently create contention or deadlocks that have
nothing to do with the code's actual intent, and it lets other buggy code compare two logically
equal `Optional`s with `==` and get `false` for two *different* present values, or `true` by
accident for two empties. Before `@ValueBased`, the JDK had no formal, tool-checkable way to say
"this class looks like an object but you must reason about it like a value." `@ValueBased`, added
in Java 16, is that marker for the JDK's own classes — `Optional`, `LocalDate`,
`LocalDateTime`, and the other `java.time` types all carry it.

**When to reach for it, and when not.** You do not apply `@jdk.internal.ValueBased` yourself — it
lives under `jdk.internal` and is not a public, supported annotation for application code; it is
retained at runtime (`RetentionPolicy.RUNTIME`) and targets `TYPE` so that the compiler can
recognize it on JDK classes and warn on misuse, and so that documentation tooling can surface the
value-based contract. Its practical relevance to you is entirely as a **reader** of the contract:
whenever you see it (or its public documentation trail, `java.lang.doc-files.ValueBased.html`) on a
JDK class, that class has opted into the restrictions below, and your code must comply even though
nothing at compile time stops you from violating them today.

**How it works.** The annotation itself, quoted from `jdk/internal/ValueBased.java` at the
jdk-21+35 tag:

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(value={TYPE})
public @interface ValueBased {
}
```

That is the whole declaration — an empty marker interface with no members. All of its force comes
from the Javadoc, and from the class-level `@apiNote`-style prose that `Optional` itself carries:

> "This is a value-based class; programmers should treat instances that are equal as
> interchangeable and should not use instances for synchronization, or unpredictable behavior may
> occur."

Unpacking each clause: **"treat instances that are equal as interchangeable"** — if
`a.equals(b)`, you must not write code that behaves differently depending on whether `a` and `b`
are the *same object* or merely equal ones; **"should not use instances for synchronization"** —
`synchronized (someOptional) { ... }` is legal Java (every object has a monitor) but is explicitly
against the contract, because a JVM that later stops allocating distinct `Optional` instances for
equal values would make two logically unrelated `synchronized` blocks on "the same" value contend
on the same monitor, or worse, on a shared constant like `EMPTY` where every empty lookup in the
whole program would serialize through one lock; **"or unpredictable behavior may occur"** is
deliberately vague because the whole point is that the JDK reserves the right to change the
allocation and identity story of `Optional` across releases without that counting as a breaking
change — which is exactly the Valhalla trajectory covered in Concept 4 below.

The javadoc for `@ValueBased` on the annotation declaration itself adds one more detail worth
knowing: it notes that the annotation "is handled specially by the javac compiler" for
`--release older-release` cross-compilation, meaning javac's own diagnostics (the "value-based
class used for synchronization" warning) are wired directly to this marker rather than to some
external list — the compiler can find every value-based class in the boot module by scanning for
the annotation.

**The container-internals connection.** The identity-versus-equality distinction this annotation
formalizes is the same one that underlies `hashCode`/`equals` contracts across the whole collections
framework — guide 02 covers how `HashMap` and `HashSet` rely on exactly this contract (equal keys
must hash equally) being honored consistently, and how violating it silently corrupts a hash table
rather than throwing.

**Example.** The pitfall this enables:

```java
public final class LookupCache {

    private final Object lock = Optional.empty();   // legal Java, contract violation

    public Optional<Client> cachedOrLookup(ClientId clientId, ClientLookup lookup) {
        synchronized (lock) {
            return lookup.findById(clientId);
        }
    }
}
```

This compiles and runs today because `EMPTY` is a real object with a real monitor. But it locks on
a JDK-shared singleton that every other piece of code in the entire JVM calling `Optional.empty()`
also holds a reference to — a completely unrelated class synchronizing on an unrelated
`Optional.empty()` somewhere else in the same process would contend on the *same lock*, producing
mysterious, action-at-a-distance contention that has nothing to do with either piece of code's
actual critical section.

**Gotcha.**

**Pitfall:** treating `@ValueBased` as merely stylistic advice rather than a real constraint the
JIT and future JVM releases can and do act on. The symptom shows up as intermittent, unexplainable
lock contention in production when two unrelated subsystems both happen to synchronize on
`Optional.empty()` or on two `Optional`s that later got interned to the same instance. The fix:
never synchronize on any type marked `@ValueBased`, and if you need a lock, use a dedicated
`private final Object lock = new Object();` field whose only job is being a lock — an instance with
identity that means something, which is precisely what `Optional` is not meant to have.

> **`@jdk.internal.ValueBased` marks `Optional` — and other JDK types like `LocalDate` — as classes
> whose instances must be treated as interchangeable values, never as synchronization targets or
> identity carriers, so that the JVM remains free to change their allocation story without
> breaking correct code.**

---

### Concept 3 — `Optional.empty() == Optional.empty()` is true, and relying on it is the trap

**[PROVE]** Work through why the identity holds, rather than taking it on faith.

1. `Optional.empty()` is declared `public static<T> Optional<T> empty()`.
2. Its body, quoted verbatim from `Optional.java` at jdk-21+35:

   ```java
   public static<T> Optional<T> empty() {
       @SuppressWarnings("unchecked")
       Optional<T> t = (Optional<T>) EMPTY;
       return t;
   }
   ```

3. `EMPTY` is declared `private static final Optional<?> EMPTY = new Optional<>(null);` — a
   `static final` field, initialized exactly once, during the class's `<clinit>` (static
   initializer), before any thread can observe the class as loaded and usable (the JLS guarantees
   this ordering via class-initialization semantics, §12.4).
4. Every call to `empty()`, regardless of the type argument `T` the caller asks for, casts and
   returns that same `EMPTY` reference — the cast is purely a compile-time and unchecked-warning
   device; at the bytecode level it is a no-op, because generics are erased. There is no branch in
   `empty()` that can construct a new object; the *only* path through the method returns `EMPTY`.
5. Therefore `Optional.<Client>empty()` and `Optional.<String>empty()` called from anywhere, at any
   time, in any thread, after class initialization, both evaluate to the identical object reference,
   and `Optional.empty() == Optional.empty()` evaluates to `true`.

**Where the trap is.** That `==` being `true` is a true statement about *this* implementation, and
it is exactly the identity dependence `@ValueBased` forbids you from relying on. The contract does
not promise `==` will keep meaning that; it promises `equals` will, because `Optional.equals`
(inherited behavior, defined in terms of `Objects.equals` on the wrapped value) is the
value-based comparison you are supposed to use. Code that special-cases `if (result ==
Optional.empty())` instead of `if (result.isEmpty())` or `if (result.equals(Optional.empty()))` is
leaning on an implementation detail that the JDK has explicitly reserved the right to break.

**Interview:** "Is `Optional.empty() == Optional.empty()` true, and should you rely on it?" — Yes
it is true today, because `empty()` always returns the same cached `EMPTY` constant, but no you
should never rely on it, because `Optional` is `@ValueBased` and the JDK only guarantees `equals`
semantics, not identity, across releases — a future value-class `Optional` under Valhalla could
have no stable identity to compare at all.

**Pitfall:** writing `if (opt == Optional.empty())` as a "fast path" instead of `opt.isEmpty()`.
The wrong code:

```java
Optional<Client> result = clientLookup.findById(clientId);
if (result == Optional.empty()) {        // works today, by luck of the current implementation
    auditLog.recordMiss(clientId);
}
```

The right code:

```java
Optional<Client> result = clientLookup.findById(clientId);
if (result.isEmpty()) {                  // correct regardless of how empties are represented
    auditLog.recordMiss(clientId);
}
```

**Why people believe it:** they tested `==` in a REPL, saw `true`, and generalized "it's a
singleton, so `==` is safe" — without reading the class-level contract that says the opposite.

> **`Optional.empty() == Optional.empty()` is `true` because `empty()` always hands back the one
> shared `EMPTY` constant — a true fact about the current implementation that you must never write
> code depending on, because `@ValueBased` reserves the right to change it.**

---

## Supporting facts

### `map`'s one-line body (§3.7.4)

**Mechanism.** The actual source, quoted verbatim from `Optional.java` at jdk-21+35:

```java
public <U> Optional<U> map(Function<? super T, ? extends U> mapper) {
    Objects.requireNonNull(mapper);
    if (isEmpty()) {
        return empty();
    } else {
        return Optional.ofNullable(mapper.apply(value));
    }
}
```

Past the mandatory null-check on the mapper itself, the entire method reduces to one piece of
logic: `isEmpty() ? empty() : Optional.ofNullable(mapper.apply(value))`. That ternary is the
one-line behavior the syllabus is pointing at, even though the shipped source spells it as an
if/else for readability rather than as a literal ternary expression. `[PROVE]`: because the
non-empty branch wraps the mapper's result in `ofNullable` rather than `of`, a mapper that itself
returns `null` does not throw — it produces `Optional.empty()`. Trace it: `mapper.apply(value)`
returns `null` → `Optional.ofNullable(null)` → inside `ofNullable`, a `null` check routes to
`empty()` → the shared `EMPTY` comes back. So `Optional.of(client).map(c -> (String) null)`
evaluates to `Optional.empty()`, not to an `Optional` wrapping `null` and not to an NPE — a single
line of source fully explains a behavior that surprises people who expect `map` to mirror `Stream`'s
`map`, which has no such null-guard because a `Stream` element can legitimately be `null`.

**Gotcha.** A five-stage `map` chain over a lookup is exactly this behavior compounding: the first
`isEmpty()` that returns `true` short-circuits every remaining stage to `empty()` without ever
calling the later mappers, because each stage's `else` branch is the only path that invokes the
next mapper.

```java
Optional<String> maskedCardSuffix =
    clientLookup.findById(clientId)                       // Optional<Client>
        .map(Client::defaultInstrument)                    // Optional<Instrument>
        .map(Instrument::cardNumber)                        // Optional<String>
        .map(number -> number.substring(number.length() - 4)) // Optional<String>
        .map("****%s"::formatted)                            // Optional<String>
        .map(String::trim);                                  // Optional<String>
```

If `defaultInstrument()` returns `null` for a client with no saved card, the second `map` sees
`isEmpty()` on the `Optional<Instrument>` produced by the first `map`'s `ofNullable`, and every
subsequent stage becomes a single `isEmpty()` check returning `EMPTY` — the three remaining mapper
lambdas are never invoked at all. This is the mechanism behind "streams and `Optional` chains are
lazy about failure": absence propagates by branching on a boolean, not by exceptions.

> **`Optional.map` is `isEmpty() ? empty() : Optional.ofNullable(mapper.apply(value))` — the
> `ofNullable` wrapping the result, not `of`, is the entire reason a null-returning mapper produces
> an empty `Optional` instead of an exception.**

### `get()` and `orElseThrow()` are the same method under two names (§3.7.5)

**Mechanism.** Both quoted verbatim from `Optional.java` at jdk-21+35:

```java
public T get() {
    if (value == null) {
        throw new NoSuchElementException("No value present");
    }
    return value;
}

public T orElseThrow() {
    if (value == null) {
        throw new NoSuchElementException("No value present");
    }
    return value;
}
```

Byte for byte, these two method bodies are identical: same null check, same exception type, same
message string, same return. `[RESEARCH]`: this is not folklore — it is the literal source at the
jdk-21+35 tag, and it has been true since `orElseThrow()` (the no-argument overload) was added in
Java 10 (`JEP `-less enhancement tracked as JDK-8140281) specifically to give `Optional` an
`Optional.get()`-equivalent whose *name* does not lie about what it does. `get()` predates
`orElseThrow()` by four releases (Java 8 vs Java 10) and was, per the Optional design history
discussed on the OpenJDK core-libs-dev list, very nearly deprecated once `orElseThrow()` shipped,
because `get()`'s name reads like a safe accessor — the way `List.get(int)` or a getter method
does — when it is in fact a throwing operation with no relationship to the rest of the JDK's
"`get` means safe retrieval" convention. It was kept, unmarked, purely for source and behavioral
compatibility with the enormous amount of Java 8-era code already calling it.

**Gotcha.**

**Pitfall:** reading `optional.get()` in someone else's code and assuming it is safe because
`get()` "sounds like" a plain accessor. The wrong belief in action:

```java
Client client = clientLookup.findById(clientId).get();   // throws if the client isn't found
```

The right code names the intent:

```java
Client client = clientLookup.findById(clientId)
    .orElseThrow(() -> new IllegalStateException(
        "no client for %s".formatted(clientId)));
```

`orElseThrow()` (no-arg) and `get()` throw the same generic `NoSuchElementException` with the same
unhelpful "No value present" message and no reference to which lookup failed; the argument-taking
`orElseThrow(Supplier<X>)` overload is the one that actually improves on `get()`, by letting you
throw a domain exception that says *what* was missing.

**Why people believe `get()` is deprecated:** many blog posts and even some IDE inspections flag
`Optional.get()` as "should be avoided," which reads to people as "deprecated" — but nothing in the
JDK ever added `@Deprecated` to it; the annotation people are thinking of exists only in linter
configurations, not in the source.

> **`get()` and the no-argument `orElseThrow()` have byte-identical bodies — the same null check,
> the same `NoSuchElementException`, the same message — and `orElseThrow()` exists purely to give
> that behavior an honestly-named entry point.**

### Not `Serializable`, by design, and what that buys the Valhalla trajectory (§3.7.7)

**Mechanism.** `[PROVE]`: `Optional.class.getInterfaces()` returns an empty array at Java 21 —
verified by compiling and running `java.util.Optional.class.getInterfaces().length` on this
machine with `--release 21`, which printed `0`. `Optional` implements no interfaces at all: not
`Serializable`, not `Comparable`, nothing. This is a deliberate design choice stated in the class
Javadoc itself: `Optional` is meant to be used as a *return type*, not as a field, and fields are
where `Serializable` would matter — a class holding an `Optional<Client>` field could not be
serialized by the standard mechanism if `Optional` itself were not `Serializable`, which is exactly
the friction the design wants to create, to steer you away from putting `Optional` in a field or a
data-transfer object in the first place.

The reasoning connects directly to the value-based contract from Concept 2: a class with no
identity worth preserving and no promise about its future allocation strategy has nothing coherent
to serialize either — serialization is fundamentally about preserving an object's identity and
state across a stream boundary, and `@ValueBased` already tells you `Optional`'s identity is not
something you are allowed to depend on. Skipping `Serializable` removes a second surface where
identity assumptions could leak in (a deserialized `Optional` that is `==` to nothing, or an
older-JDK-serialized form encoding assumptions about the one-field layout that Valhalla would
break).

**Gotcha.**

**Pitfall:** designing a JPA entity or a DTO with an `Optional<T>` field, then discovering the
entity cannot round-trip through a serialization boundary (an HTTP session, a distributed cache, a
message queue payload) that requires `Serializable`. The wrong code:

```java
public final class ClientProfileCache implements Serializable {
    private Optional<String> preferredJurisdiction;   // does not compile with a Serializable check,
                                                         // or fails at runtime under strict serializers
}
```

The right code keeps `Optional` at the API boundary only, and stores the raw nullable value:

```java
public final class ClientProfileCache implements Serializable {
    private String preferredJurisdictionOrNull;

    public Optional<String> preferredJurisdiction() {
        return Optional.ofNullable(preferredJurisdictionOrNull);
    }
}
```

**Why people believe it should be `Serializable`:** most of the JDK's other simple value-carrying
types — `LocalDate`, `BigDecimal`, boxed primitives — are `Serializable`, so `Optional` looks like
an outlier rather than a deliberate exception; the outlier is the point.

> **`Optional` implements no interfaces, including `Serializable`, and that omission is deliberate:
> it keeps `Optional` out of fields and serialization boundaries, and it leaves nothing about the
> class's identity for a future Valhalla value class to have to preserve.**

---

### Concept 4 — Memory: the 16-byte cost, and when escape analysis removes it

**Mental model.** Every non-shared `Optional` is a small, short-lived heap object sitting between
you and the value you actually wanted. The question that matters for performance is not "does
`Optional` cost memory" — it obviously allocates an object header — but "does that allocation
survive to become real garbage-collector work, or does the JIT see through it and never allocate at
all."

**Why it exists as a cost, and why it is usually not one.** Wrapping a reference always has *some*
representation cost in a language without true zero-cost value types (which is exactly what
Valhalla is trying to fix — see Concept 5). But the JIT compiler has had escape analysis since
long before `Optional` existed, and `Optional` is close to the ideal case for it: small, final,
immutable, single-field, and — in the overwhelmingly common case — created and consumed within a
few inlined method calls with no reference to the `Optional` object itself ever leaking out.

**When the cost is real versus eliminated.** `[NUM]` Work the arithmetic through explicitly for a
present `Optional<Client>` on 64-bit HotSpot with compressed oops (the Java 21 default for heaps
under roughly 32 GB): the object header is **12 bytes** (an 8-byte mark word plus a 4-byte
compressed class pointer) which HotSpot rounds to a **16-byte** aligned minimum object size before
any fields are added — this is the well-known "empty object is 16 bytes" baseline that also applies
to, say, `new Object()`. Add the one `value` field: a compressed object reference is **4 bytes**,
bringing the raw size to 16 + 4 = 20 bytes, which the JVM's 8-byte object-alignment rule rounds up
to **24 bytes** total. The syllabus's "16-byte cost" names the header baseline; the fully wrapped
`Optional<Client>` is 24 bytes once the payload reference is included — both figures matter and
neither should be quoted as the whole answer.

Whether that 24 bytes is ever actually allocated depends entirely on **escape analysis**: if the
JIT can prove an object never "escapes" the compiled method — never gets stored into a field,
passed to a non-inlined call, or returned to a caller whose own compiled code it cannot see into —
it can perform **scalar replacement**, decomposing the object into its constituent fields (here,
just the one `value` reference) and keeping them in registers or on the stack, with no heap
allocation at all. A tight, fully inlined `.map().map().map()` chain over a hot lookup is exactly
this case, *provided* every `map` call site is small enough and monomorphic enough for the JIT to
inline it — HotSpot's default inlining budget (`-XX:FreqInlineSize`, `-XX:MaxInlineSize`) caps how
deep and how large an inlined call graph can grow, and inlining is a prerequisite for escape
analysis to see across the call boundary at all.

Escape analysis does **not** eliminate the allocation when:

- the call site is **megamorphic** — the JIT's inline cache has seen more than a handful of
  distinct receiver types at that call site (HotSpot's polymorphic inline cache typically tracks up
  to two profiled types before giving up and falling back to a virtual call), so it cannot commit
  to inlining any one implementation and the `Optional`-returning method call stays a real,
  un-inlined call;
- the `Optional` **crosses a non-inlined method boundary** — passed into a method too large to
  inline, stored as a return value that a caller several frames away consumes, or handed to a
  polymorphic collection or logging call — because escape analysis is fundamentally intraprocedural
  once inlining stops extending its view;
- the `Optional` is stored into a field or a collection, which is an escape by definition — a heap
  location outside the method's own stack frame now holds the reference, so the object must
  actually exist.

**Example — the same chain, with and without escape analysis winning.**

```java
public final class InstrumentMaskingService {

    private final ClientLookup lookup;

    public InstrumentMaskingService(ClientLookup lookup) {
        this.lookup = lookup;
    }

    // Escape analysis is likely to eliminate every intermediate Optional here:
    // small, final methods, monomorphic call sites, nothing stored or returned
    // except the final unwrapped String.
    public String maskedSuffixOrDefault(ClientId clientId) {
        return lookup.findById(clientId)
            .map(Client::defaultInstrument)
            .map(Instrument::cardNumber)
            .map(number -> number.substring(number.length() - 4))
            .map("****%s"::formatted)
            .orElse("****----");
    }

    // Escape analysis is defeated here: the Optional itself is returned to the
    // caller, so it genuinely escapes this method's frame and must be a real
    // heap object no matter how well the chain above it was inlined.
    public Optional<String> maskedSuffix(ClientId clientId) {
        return lookup.findById(clientId)
            .map(Client::defaultInstrument)
            .map(Instrument::cardNumber)
            .map(number -> number.substring(number.length() - 4))
            .map("****%s"::formatted);
    }
}
```

`maskedSuffixOrDefault` terminates the chain with `orElse`, which unwraps to a bare `String` before
returning — nothing about any intermediate `Optional` needs to exist past the method's own frame,
so a warmed-up JIT compilation is a strong candidate for scalar-replacing every stage.
`maskedSuffix` returns the `Optional<String>` itself to its caller: that final `Optional` has
escaped by construction (it is the return value), so at minimum the last-stage object is real, even
if the earlier intermediate stages inside the chain still get eliminated.

**Interview:** "Isn't wrapping every lookup in `Optional` going to hurt performance?" — In a tight,
inlined, monomorphic chain, no: escape analysis and scalar replacement typically eliminate the
intermediate allocations entirely, so the runtime cost converges to the same null-check-and-branch
you would have written by hand. The cost becomes real only when the `Optional` genuinely escapes —
stored in a field, returned across a real API boundary, or encountered at a megamorphic call site —
which is a mechanism argument, not a guess, and it is the honest, complete answer instead of a flat
"it's basically free" or a flat "it's an extra allocation, avoid it."

**Gotcha.**

**Pitfall:** benchmarking `Optional` in a microbenchmark method that is too small and too hot not to
get scalar-replaced, concluding "`Optional` is always free," and then being surprised when the same
pattern shows real GC pressure at a megamorphic call site or across a real service boundary in
production. The fix: profile the actual call site (JFR allocation profiling, `-XX:+PrintCompilation`
combined with `-XX:+PrintEscapeAnalysis` for a targeted method) rather than trusting a microbenchmark
whose entire premise — a single monomorphic call site executed in a tight loop — is exactly the
shape escape analysis handles best and production code least resembles.

> **A present `Optional<Client>` is a real 24-byte heap object — a 16-byte header plus one 4-byte
> compressed reference, aligned up — but escape analysis and scalar replacement typically eliminate
> that allocation entirely inside an inlined, monomorphic chain, and reliably fail to when the
> `Optional` escapes the method, crosses a non-inlined boundary, or the call site is megamorphic.**

---

### Concept 5 — The Valhalla trajectory: `Optional` as a value class

**Mental model.** Everything this file has walked through — the single field, the shared `EMPTY`,
the `@ValueBased` contract, the fact that identity was never supposed to matter — is not incidental.
It is the JDK positioning `Optional` for a future where it is not an object with an address at all,
but a **value class** under Project Valhalla: something that behaves exactly like today's
`Optional` from your code's point of view, but that the JVM can lay out flat, inline, and pass
around without ever putting a header or a reference indirection between you and the payload.

**Why it exists as a stated plan, not speculation.** `[RESEARCH]`: this is Valhalla's own framing
of its goal, not an inference from `Optional`'s current shape — value classes are described (in the
JEP drafts and OpenJDK Valhalla project material) as classes whose instances have **no identity**:
no `==` beyond content equality, no monitor to lock on, no guaranteed unique memory address, in
exchange for the JVM being free to allocate them without a heap object at all — inline in a
register, on the stack, or flattened directly inside the field of an enclosing object, the same way
a primitive `int` field is stored today. `Optional`'s `@ValueBased` annotation and its documented
contract ("do not synchronize on it, do not depend on its identity") are the JDK asking application
code, years in advance, to stop relying on exactly the properties that value classes will not
have — so that when `Optional` (and `LocalDate`, and the other `@ValueBased` classes) is eventually
migrated, no correct existing code breaks.

**How it changes the cost story from Concept 4.** Under Valhalla, an `Optional<Client>` field
inside another object would not be a 4-byte reference pointing at a separate 24-byte heap object at
all; it would be **flattened** into the enclosing object's own layout — the `value` reference stored
directly where the field lives, with no separate allocation, no separate header, and no pointer
chase to dereference it. That is the honest answer to "isn't `Optional` slow?" at the mechanism
level: today, the answer is "usually no, because escape analysis already gets you most of the way
there in hot, inlined code" (Concept 4); the *stated long-term plan* is "and eventually, even the
cases escape analysis cannot help — fields, escaped returns, megamorphic call sites — stop costing
anything either, because there will be no separate object to allocate in the first place."

**[X-REF 06]** The full mechanism of how the JVM lays out and flattens value classes — the
distinction between value classes with and without identity, how flattening interacts with field
layout and `null`-ability, and what changes for the interpreter and the JIT — is JVM-internals
territory and belongs to guide 06; the load-bearing fact for this file is narrower and complete on
its own: `Optional`'s current design (single field, shared empty, no identity dependence permitted)
is not an accident of Java 8's original implementation, it is the shape that makes the Valhalla
migration possible without a source- or behavior-breaking change to any correctly written caller.

**Gotcha.**

**Pitfall:** treating "Valhalla will fix `Optional`'s cost" as a reason to stop caring about the
`Optional`-in-a-field anti-pattern today, on the theory that a future JDK release will make it free.
The mechanism argument in Concept 4 already makes the current-day allocation mostly disappear in
the hot-path shape that matters (inlined, monomorphic chains); the shapes that still cost something
today — fields, cross-boundary returns, megamorphic sites — are also not automatically excused by
Valhalla, because value-class migration is a JDK-internal reimplementation of `Optional`'s existing
public contract, not a license to write new code that depends on identity or synchronization that
the contract already forbids. The `@ValueBased` rules in Concept 2 are the actual, present-tense
constraint; Valhalla is the reason those rules exist, not a reason to relax them.

> **Value classes under Project Valhalla are the stated destination for `@ValueBased` types like
> `Optional`: instances with no identity, eligible for flattened, allocation-free storage even
> inside fields — which is the honest, mechanism-grounded answer to "isn't `Optional` slow?"
> rather than either "yes, avoid it" or "no, it's free."**

---

## Pitfalls

### Assuming `Optional.get()` is a safe accessor because of its name

**Wrong**

```java
Client client = clientLookup.findById(clientId).get();
// java.util.NoSuchElementException: No value present
//   at java.base/java.util.Optional.get(Optional.java:143)
```

**Right**

```java
Client client = clientLookup.findById(clientId)
    .orElseThrow(() -> new IllegalStateException(
        "no client found for id %s".formatted(clientId)));
```

**Why people believe it:** `get()` reads like every other `get` in the JDK — `Map.get`,
`List.get(int)` — which either return a value or a documented sentinel (`null`); `Optional.get()`
is the outlier that throws instead, and its name gives no hint of that.

### Relying on `Optional.empty() == Optional.empty()`

**Wrong**

```java
Optional<Client> lookupResult = clientLookup.findById(clientId);
boolean wasMiss = lookupResult == Optional.empty();   // true today, by implementation accident
```

**Right**

```java
Optional<Client> lookupResult = clientLookup.findById(clientId);
boolean wasMiss = lookupResult.isEmpty();              // correct regardless of representation
```

**Why people believe it:** they verified the `==` in a REPL or a unit test, saw `true`, and treated
an implementation fact as a guaranteed contract — without reading that `Optional` is `@ValueBased`
and explicitly disclaims identity guarantees.

### Putting `Optional<T>` in a field or a DTO because it "documents optionality"

**Wrong**

```java
public final class ClientProfile {
    private final Optional<String> preferredJurisdiction;   // extra allocation, not Serializable

    public ClientProfile(Optional<String> preferredJurisdiction) {
        this.preferredJurisdiction = preferredJurisdiction;
    }
}
```

**Right**

```java
public final class ClientProfile {
    private final String preferredJurisdictionOrNull;

    public ClientProfile(String preferredJurisdictionOrNull) {
        this.preferredJurisdictionOrNull = preferredJurisdictionOrNull;
    }

    public Optional<String> preferredJurisdiction() {
        return Optional.ofNullable(preferredJurisdictionOrNull);
    }
}
```

**Why people believe it:** `Optional` reads as strictly more expressive than a nullable field, and
the guidance against using it as a field type ("`Optional` is a return type, not a field type") is
buried in the class Javadoc rather than enforced by the compiler.

## Cheat sheet

| Fact | Value / behavior |
|---|---|
| Fields | one `private final T value`; one `private static final Optional<?> EMPTY` |
| Class modifiers | `public final` — no subclassing |
| Interfaces implemented | none — not `Serializable`, not `Comparable` (verified: `getInterfaces().length == 0`) |
| `empty()` allocation | zero — always returns the shared `EMPTY` |
| `Optional.empty() == Optional.empty()` | `true` today; never rely on it (`@ValueBased`) |
| `map` body | `isEmpty() ? empty() : ofNullable(mapper.apply(value))` |
| `map` with a null-returning mapper | produces `Optional.empty()`, not an NPE, not a null-wrapping `Optional` |
| `get()` vs `orElseThrow()` (no-arg) | byte-identical bodies; both throw `NoSuchElementException("No value present")` |
| `get()` deprecated? | no — never marked `@Deprecated`; only convention discourages it |
| Object header (16-byte baseline) | 8-byte mark word + 4-byte compressed class pointer, aligned to 16 |
| Full `Optional<Client>` size | 16-byte header + 4-byte compressed ref = 20, aligned up to 24 bytes |
| Escape analysis eliminates the allocation when | inlined, monomorphic, non-escaping chain |
| Escape analysis does not when | megamorphic call site, non-inlined boundary, field/collection storage |
| `@jdk.internal.ValueBased` forbids | synchronizing on the instance; depending on `==` identity |
| Valhalla's stated plan | `Optional` becomes a value class — no identity, flattenable, allocation-free even in fields |

## Self-test

**Q1.** Why does `Optional.empty()` never allocate, and what field makes that possible?

<details><summary>Answer</summary>

`Optional` holds a `private static final Optional<?> EMPTY` instance, constructed exactly once
during class initialization. `empty()`'s entire body is an unchecked cast of that one shared field
to the caller's requested type parameter and a return — there is no branch that constructs a new
object, so every call to `empty()`, for any `T`, returns the identical reference.

</details>

**Q2.** What specifically does the `@ValueBased` contract forbid, and why does `Optional` need
that restriction rather than behaving like an ordinary object?

<details><summary>Answer</summary>

It forbids synchronizing on an instance and forbids depending on `==` identity between two equal
instances — you must treat equal `Optional`s as interchangeable. `Optional` needs this because it
is meant to be a value carrier with no identity of its own, and because the JDK reserves the right
to change its allocation strategy (up to and including eliminating allocation entirely under
Valhalla) without that counting as a breaking change — a change that would be observable, and
therefore breaking, for any code relying on `==` or synchronization.

</details>

**Q3.** Is `Optional.empty() == Optional.empty()` `true`, and is it safe to write code that depends
on that?

<details><summary>Answer</summary>

It is `true` today, because `empty()` always returns the same cached `EMPTY` constant with no
allocation. It is not safe to depend on, because `Optional` is `@ValueBased` and only guarantees
`equals`-based value semantics across releases, not identity — relying on `==` here is exactly the
identity dependence the annotation's contract forbids, and a future value-class `Optional` could
have no stable identity to compare with `==` at all.

</details>

**Q4.** Trace what `Optional.of(client).map(c -> (String) null)` evaluates to, and explain why using
`map`'s actual source.

<details><summary>Answer</summary>

It evaluates to `Optional.empty()`. `map`'s body is `isEmpty() ? empty() :
Optional.ofNullable(mapper.apply(value))`. The receiver is non-empty, so the `else` branch runs:
`mapper.apply(value)` returns `null`, and that `null` is passed to `Optional.ofNullable`, not
`Optional.of` — `ofNullable` routes a `null` argument to `empty()` internally, so the final result
is the shared empty instance rather than an NPE or an `Optional` wrapping `null`.

</details>

**Q5.** `get()` and the no-argument `orElseThrow()` — are they different methods with different
behavior, or the same behavior under two names? Justify from the source.

<details><summary>Answer</summary>

Same behavior under two names. Both bodies check `if (value == null) throw new
NoSuchElementException("No value present");` and otherwise `return value;` — byte-identical,
including the exception type and message. `orElseThrow()` was added later (Java 10) purely to give
that exact behavior an honestly named entry point; `get()` was kept unmarked for Java 8-era source
compatibility.

</details>

**Q6.** Work out, with the arithmetic shown, the total heap size of a present `Optional<Client>` on
64-bit HotSpot with compressed oops in Java 21.

<details><summary>Answer</summary>

The object header is 8 bytes (mark word) + 4 bytes (compressed class pointer) = 12 bytes, which
HotSpot's minimum-object-size rule rounds to a 16-byte baseline before any declared fields are
counted. Add the one `value` field, a compressed object reference at 4 bytes: 16 + 4 = 20 bytes raw
size. The JVM's 8-byte object-alignment rule rounds 20 up to the next multiple of 8, giving 24
bytes total.

</details>

**Q7.** Under what conditions does escape analysis fail to eliminate an `Optional` allocation inside
a `.map()` chain, and why does inlining matter to the answer?

<details><summary>Answer</summary>

It fails when the `Optional` genuinely escapes the compiled method's frame — stored into a field or
collection, returned to a caller as the method's own return value, or encountered at a megamorphic
call site the JIT will not commit to inlining. Inlining matters because escape analysis is
intraprocedural: it can only reason about an object's lifetime within the compiled unit it can see,
and inlining is what extends "the compiled unit" across what would otherwise be separate method
call boundaries. A call site with more distinct receiver types than HotSpot's polymorphic inline
cache tracks falls back to a real virtual call, which stops inlining and therefore stops escape
analysis from seeing past it.

</details>

**Q8.** What is the stated relationship between `Optional`'s `@ValueBased` annotation today and
Project Valhalla's value classes?

<details><summary>Answer</summary>

`@ValueBased` is the JDK asking callers, years in advance, to stop depending on exactly the
properties — identity, `==` comparison, synchronization — that value classes under Valhalla will
not have. The stated plan is for `Optional` to eventually become a value class: an instance with no
identity, eligible for flattened, allocation-free storage even inside another object's fields. Code
that already honors the `@ValueBased` contract will see no observable change when that migration
happens; code that violates it (synchronizing on an `Optional`, relying on `==`) is exactly the code
that would break.

</details>

**Q9.** Why is `Optional` not `Serializable`, and what does that omission protect against?

<details><summary>Answer</summary>

`Optional` implements no interfaces at all (verified: `Optional.class.getInterfaces().length ==
0`), by design, because it is meant to be used as a method return type, not as a field type — and
fields are exactly where `Serializable` would matter. The omission both discourages putting
`Optional` in a field or DTO, and avoids creating a second surface (a serialized form) where
identity or layout assumptions about the current one-field implementation could leak in and later
conflict with a Valhalla value-class migration.

</details>

**Q10.** A colleague claims `IntStream.summingInt`-style collectors and `Optional`'s allocation cost
are unrelated topics. Using `Optional`'s design as the throughline, explain the one JVM mechanism
that connects "does `Optional` allocate" to "is `summingInt` safe from overflow" — or explain why
there isn't one, and name the actual shared idea instead.

<details><summary>Answer</summary>

There isn't a shared JVM mechanism — escape analysis has nothing to do with integer overflow. The
actual shared idea is a general one this file and its siblings return to repeatedly: verify the
claim against the real source rather than trusting the "obviously true" version. Just as "the 16-byte
cost" needed the arithmetic worked through (16-byte header, not 24; 24 bytes fully wrapped) rather
than quoted as folklore, `summingInt`'s accumulator being an `int[1]` rather than a `long[]` (unlike
`summingLong` and `averagingInt`) is a fact that only the actual `Collectors` source settles, and
guessing "sums are always widened" gets it wrong in exactly the same way guessing "`Optional`
always allocates" or "`Optional` is always free" gets the escape-analysis question wrong.

</details>

## Deferred

None.

---

**Leaves covered:** 3.7.1, 3.7.2, 3.7.3, 3.7.4, 3.7.5, 3.7.6, 3.7.7, 3.7.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** D-146
**Target version:** Java 21 LTS
**Lines:** 910
