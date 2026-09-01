# 03 — Java Core

The language substrate. These are the questions that separate "I use Java" from "I know Java": the
Integer cache, the String pool, erasure, and what `final` actually promises.

---

## 1. The type system

Java has exactly two kinds of types: **primitives** (`byte`, `short`, `int`, `long`, `float`,
`double`, `char`, `boolean`) and **reference types** (classes, interfaces, arrays, enums, records).
Everything that is not a primitive is a reference.

Primitives hold values directly in the stack slot or object field. References hold an address; the
object lives on the heap.

| Type | Bits | Range |
|---|---|---|
| byte | 8 | −128 … 127 |
| short | 16 | −32,768 … 32,767 |
| char | 16 | 0 … 65,535 (unsigned) |
| int | 32 | ±2.1 × 10⁹ |
| long | 64 | ±9.2 × 10¹⁸ |
| float | 32 | ~7 decimal digits |
| double | 64 | ~15 decimal digits |
| boolean | JVM-dependent | true/false |

Widening conversions (`int` → `long` → `float` → `double`) are implicit; narrowing requires a cast and
silently truncates.

**Trap:** integer overflow wraps silently. `Integer.MAX_VALUE + 1 == Integer.MIN_VALUE`. Use
`Math.addExact` when overflow must be an error, and prefer `long` for accumulators, timestamps, and
IDs.

**Trap:** `int / int` is integer division. `1 / 2 == 0`. Cast one operand first.

---

## 2. Wrappers, autoboxing, and the Integer cache

Each primitive has a wrapper class. Autoboxing inserts `Integer.valueOf(int)`; unboxing inserts
`intValue()`.

**`Integer.valueOf` caches boxed instances for −128 to 127** and returns the *same object* for values
in that range. Outside it, every call allocates a new `Integer`.

```java
Integer a = 127, b = 127;
System.out.println(a == b);      // true  — same cached object

Integer c = 128, d = 128;
System.out.println(c == d);      // false — two distinct objects

System.out.println(c.equals(d)); // true  — value comparison
```

The upper bound is tunable via `-XX:AutoBoxCacheMax`; the lower bound is fixed at −128. `Byte`,
`Short`, `Long` and `Character` cache the same low range; `Boolean` caches both values. `Float` and
`Double` cache nothing.

**Trap:** `==` on wrappers compares references. It appears to work in tests with small numbers and
fails in production with large ones. Always `equals` (or unbox one side explicitly).

**Trap:** unboxing a null wrapper throws `NullPointerException` at the unboxing point, which is often
a line that contains no visible method call:

```java
Map<String, Integer> counts = new HashMap<>();
int n = counts.get("missing");   // NPE — get returns null, then .intValue()
```

**Trap:** in a ternary, if one branch is a primitive and the other a wrapper, the wrapper is unboxed —
so `flag ? 1 : nullInteger` can NPE even when you take the primitive branch's type.

Boxing in a loop allocates. `Long sum = 0L; for (...) sum += i;` creates a new Long every iteration.
Use primitives in hot paths.

---

## 3. Strings

`String` is **immutable**: the backing byte array is final and never mutated after construction. That
buys thread safety without synchronization, safe use as a HashMap key (the hash is cached in a `hash`
field after first computation), and safe sharing across code that would otherwise need defensive
copies. Since Java 9, compact strings store Latin-1 content in one byte per character.

### The string pool
String literals are interned in a JVM-managed pool (in the heap since Java 7). Identical literals in
the same or different classes resolve to one object.

```java
String a = "hello";
String b = "hello";
a == b;                      // true — both from the pool

String c = new String("hello");
a == c;                      // false — new String forces a fresh heap object
a == c.intern();             // true  — intern returns the pooled instance
a.equals(c);                 // true  — always compare with equals
```

Compile-time constant expressions are folded and pooled: `"hel" + "lo" == "hello"` is true. Runtime
concatenation is not: `a + variable` produces a new object.

**Trap:** `==` on strings works often enough (literals) to hide the bug and then fails on strings that
came from I/O, parsing, or database rows. Never compare strings with `==`.

### StringBuilder
`StringBuilder` is a mutable char buffer with amortized doubling growth, default capacity 16 (or
16 + initial string length). `StringBuffer` is the synchronized version — legacy; you almost never
want the lock.

Since Java 9, `+` in a single expression compiles to `invokedynamic` with `StringConcatFactory`, which
is often faster than manual StringBuilder for simple cases. But `+` **inside a loop** still creates a
new builder each iteration, making it O(n²). Build loops with an explicit StringBuilder.

Useful: `String.join`, `String.format`, `str.repeat(n)`, `strip()` (Unicode-aware, unlike `trim()`),
`isBlank()`, `lines()`, `chars()`, and text blocks (guide 04).

---

## 4. `==` versus `equals`

`==` compares the two stack slots. For primitives that is the value; for references it is the address,
i.e. object identity. `equals` is a method whose semantics the class defines — by default
`Object.equals` is identity, so a class without an override gains nothing from calling it.

Use `Objects.equals(a, b)` for null-safe comparison, and `Objects.hash(...)` to build hash codes.
For arrays, `equals` is identity — use `Arrays.equals` (shallow) or `Arrays.deepEquals` (nested).

The `equals`/`hashCode` contract and its failure modes are covered in guide 02, section 10.

---

## 5. static and final

**`static`** binds a member to the class rather than an instance. One copy exists, shared. Static
initializers run once at class initialization, in textual order with static field initializers.
Static methods cannot access instance state and are not polymorphic — they are dispatched by the
*compile-time* type, so "overriding" a static method actually hides it.

**`final`** means different things in three positions:
- **final variable** — the *binding* cannot be reassigned. The referenced object can still be mutated.
  `final List<String> l = new ArrayList<>(); l.add("x");` is legal.
- **final method** — cannot be overridden.
- **final class** — cannot be subclassed (`String`, `Integer`, records).

**Trap:** `final` is not immutability. A `final` field pointing at a mutable object gives you nothing
except that the pointer stays put.

`static final` primitives and String literals are **compile-time constants** and get inlined into
calling classes at compile time. If you change the constant and recompile only the defining class, the
caller keeps the stale value until it too is recompiled — a real binary-compatibility hazard.

`final` fields do carry a genuine JMM guarantee: they are safely published, meaning any thread that
sees a properly constructed object sees its final fields fully initialized without synchronization.
That is covered in guide 05.

Effectively final: a local variable never reassigned can be captured by a lambda or anonymous class
without the `final` keyword.

---

## 6. Exceptions

```
Throwable
├── Error              — JVM-level, do not catch (OutOfMemoryError, StackOverflowError)
└── Exception
    ├── RuntimeException  — unchecked (NPE, IllegalArgument, IllegalState, ClassCast)
    └── everything else   — checked (IOException, SQLException)
```

**Checked** exceptions must be caught or declared. The intent was recoverable conditions the caller
should handle. **Unchecked** exceptions signal programming errors.

Modern practice leans heavily unchecked: checked exceptions do not compose with lambdas/streams,
propagate up through every intermediate signature, and encourage empty catch blocks. Spring wraps
`SQLException` into the unchecked `DataAccessException` hierarchy for exactly this reason.

### try-with-resources
Any `AutoCloseable` declared in the parentheses is closed automatically, in reverse declaration order,
before catch/finally run.

```java
try (var conn = dataSource.getConnection();
     var stmt = conn.prepareStatement(sql)) {
    ...
}   // stmt closed, then conn — even on exception
```

**Suppressed exceptions:** if the body throws *and* `close()` throws, the body's exception propagates
and the close exception is attached via `addSuppressed`, retrievable with `getSuppressed()`. In an
old-style `finally { conn.close(); }` the close exception would *replace* the real one and destroy the
diagnosis. This is the main reason to use try-with-resources.

**Trap:** a `return` in `finally` discards any in-flight exception and any value returned from `try`.
Never return from finally.

**Trap:** `catch (Exception e) { }` swallows everything including bugs. If you must catch broadly, log
with the throwable as an argument (`log.error("msg", e)`), not `e.getMessage()` — you lose the stack
trace otherwise.

**Trap:** catching `InterruptedException` and doing nothing clears the interrupt flag and breaks
cancellation. Either rethrow or call `Thread.currentThread().interrupt()`.

Multi-catch: `catch (IOException | SQLException e)` — `e` is effectively final and typed as the common
supertype.

---

## 7. Generics

Generics are a **compile-time** feature. The compiler checks types, then **erases** them: `List<String>`
becomes `List`, and casts are inserted at use sites. The bytecode has no record of the type argument
(beyond signature metadata for reflection).

Consequences of erasure:
- `List<String>` and `List<Integer>` are the same class at runtime — `getClass()` returns the same
  object for both.
- You cannot write `new T[10]` or `new T()`.
- You cannot use `instanceof List<String>`.
- You cannot overload on `f(List<String>)` and `f(List<Integer>)` — same erased signature.
- Static fields are shared across all parameterizations.

**Trap:** generics are **invariant**. `List<String>` is *not* a `List<Object>`, even though `String`
is an `Object`. If it were, you could insert an `Integer` through the `List<Object>` alias and break
the `List<String>`. Arrays, by contrast, are covariant (`String[]` IS-A `Object[]`) — which is exactly
why array stores can throw `ArrayStoreException` at runtime.

### Wildcards and PECS

- `? extends T` — a **producer**. You can read `T` out; you cannot add anything (except null), because
  the compiler does not know which subtype the list actually holds.
- `? super T` — a **consumer**. You can add `T` (and its subtypes); reads come back as `Object`.

**PECS: Producer Extends, Consumer Super.**

```java
// src produces, dest consumes
static <T> void copy(List<? extends T> src, List<? super T> dest) {
    for (T t : src) dest.add(t);
}
```

Bounded type parameters constrain a type variable: `<T extends Comparable<T>>`. Multiple bounds use
`&`: `<T extends Number & Comparable<T>>`.

Use `<?>` (unbounded) when you only need `Object`-level operations or `size()`/`clear()`.

**Trap:** `@SafeVarargs` exists because a generic varargs parameter creates a covariant array of a
non-reifiable type, which can be corrupted — "heap pollution". Only annotate methods that never write
to the varargs array.

---

## 8. Interfaces versus abstract classes

| | Interface | Abstract class |
|---|---|---|
| Multiple inheritance | yes, many interfaces | no, one superclass |
| State | only `public static final` constants | instance fields allowed |
| Constructors | none | yes |
| Method bodies | `default` and `static` (Java 8), `private` (Java 9) | any |
| Access modifiers | implicitly public (private methods allowed since 9) | any |

Choose an interface for a capability contract; choose an abstract class when you share state or
partially implemented lifecycle. In practice, interface + composition beats deep inheritance.

**`default` methods** were added so interfaces could evolve without breaking implementors — that is
how `Collection.stream()` and `Iterable.forEach` were added to the JDK in Java 8.

Diamond resolution rules when a class inherits conflicting defaults:
1. A class implementation always wins over an interface default.
2. A more specific sub-interface wins over its super-interface.
3. Otherwise it is a compile error and you must disambiguate explicitly with
   `InterfaceName.super.method()`.

**Trap:** default methods cannot override `Object` methods (`equals`, `hashCode`, `toString`). The
compiler rejects it, since `Object`'s implementation would always win under rule 1.

---

## 9. Inner and anonymous classes

- **Static nested class** — no reference to an enclosing instance. Use this by default.
- **Inner (non-static) class** — holds an implicit `this$0` reference to the enclosing instance.
- **Local class** — declared inside a method.
- **Anonymous class** — declared and instantiated in one expression.

**Trap:** a non-static inner class keeps the whole enclosing object alive. If the inner instance is
stored somewhere long-lived (a listener registry, a static cache, a thread), the outer object leaks.
The same applies to anonymous classes and non-static inner `Runnable`s. Make it `static` unless you
genuinely need the enclosing instance.

Lambdas differ: they capture only what they reference, do not create a class file per instance, and do
not hold an implicit enclosing reference *unless* the body uses `this` or an instance member.

Captured locals must be final or effectively final — because the value is copied into the lambda, and
allowing reassignment would create two divergent copies.

---

## 10. Enums

An enum is a class whose instances are a fixed, JVM-guaranteed-unique set created at class
initialization. That guarantee makes enums the correct singleton implementation — serialization,
reflection and multiple classloaders cannot produce a second instance.

Enums can have fields, constructors, methods, and per-constant bodies:

```java
public enum Operation {
    PLUS("+")  { public int apply(int a, int b) { return a + b; } },
    TIMES("*") { public int apply(int a, int b) { return a * b; } };

    private final String symbol;
    Operation(String symbol) { this.symbol = symbol; }
    public abstract int apply(int a, int b);
    public String symbol() { return symbol; }
}
```

`values()` returns a **defensive copy each call** — do not call it in a loop; cache it. `ordinal()` is
the declaration index; never persist it, because reordering constants silently corrupts stored data.
Persist `name()` or an explicit code field.

`EnumMap` and `EnumSet` are array/bit-vector backed and are dramatically faster than the hash
equivalents.

Enums work in `switch` without qualification and give exhaustiveness checking in switch *expressions*.

---

## 11. Immutability design

Rules for a genuinely immutable class:
1. Make the class `final` (or all constructors private) so no subclass can add mutable state.
2. Make every field `private final`.
3. Provide no setters and no method that mutates state.
4. **Defensively copy mutable inputs in the constructor.**
5. **Defensively copy mutable fields on the way out of getters.**

```java
public final class Trip {
    private final Date start;                  // Date is mutable — legacy example
    private final List<String> stops;

    public Trip(Date start, List<String> stops) {
        this.start = new Date(start.getTime());     // copy in
        this.stops = List.copyOf(stops);            // copy in, immutable
    }
    public Date start() { return new Date(start.getTime()); }   // copy out
    public List<String> stops() { return stops; }               // already immutable
}
```

Skip step 4 and the caller retains a live handle to your internal state; skip step 5 and you hand one
out. Both are real escape bugs.

Benefits: inherently thread-safe, safe as a map key, safe to cache and share, no defensive copying by
callers. Use `java.time` types and `List.copyOf`/`Map.copyOf` and most of this becomes automatic.

Records (guide 04) give you 1–3 for free but **not** 4 and 5 — a record with a `List` component still
needs a compact constructor to copy.

---

## 12. Object methods

Every class inherits: `equals`, `hashCode`, `toString`, `getClass`, `clone`, `finalize` (deprecated for
removal), `wait`, `notify`, `notifyAll`.

- Override `toString` on anything that appears in logs. A default `ClassName@1b6d3586` in an error
  message costs real debugging time.
- `clone` is broken by design — it bypasses constructors, defaults to a shallow copy, and requires the
  marker interface `Cloneable`. Use a copy constructor or static factory instead.
- `finalize` is deprecated; it was never guaranteed to run. Use try-with-resources or `Cleaner`.

---

## 13. BigDecimal and money

`double` cannot represent 0.1 exactly (binary fraction), so `0.1 + 0.2 == 0.30000000000000004`. Never
represent money as a floating-point type.

`BigDecimal` stores an arbitrary-precision unscaled integer plus a `scale` (digits after the decimal
point). It is immutable — every operation returns a new instance and ignoring the return value is a
silent no-op.

```java
new BigDecimal(0.1);        // 0.1000000000000000055511151231257827... — inherits double's error
new BigDecimal("0.1");      // exactly 0.1
BigDecimal.valueOf(0.1);    // 0.1 — goes via Double.toString, so also fine
```

**Always construct from a String** (or `valueOf`), never from a `double` literal.

**Trap:** `equals` compares value **and scale**, so `new BigDecimal("2.0").equals(new BigDecimal("2.00"))`
is **false**. `compareTo` ignores scale and returns 0. Use `compareTo(x) == 0` for numeric equality.
This also means BigDecimal is a hazardous HashMap key and a hazardous JUnit `assertEquals` argument.

**Trap:** `divide` without a rounding mode throws `ArithmeticException` on a non-terminating result
(1/3). Always pass scale and `RoundingMode` — for money typically `setScale(2, RoundingMode.HALF_UP)`
(or `HALF_EVEN`/banker's rounding to avoid systematic upward bias across many transactions).

The alternative for money is storing minor units (cents) as a `long`, which is faster and exact but
puts the scale in your head rather than in the type.

---

## 14. Date and time

The legacy `java.util.Date`/`Calendar`/`SimpleDateFormat` API is mutable, has a zero-based month, and
`SimpleDateFormat` is **not thread-safe** — a shared static instance produces garbled or wrong dates
under load, a genuinely common production bug. Use `java.time` (JSR-310), which is immutable and
thread-safe throughout.

| Type | Represents | Use for |
|---|---|---|
| `Instant` | a point on the UTC timeline (epoch seconds + nanos) | timestamps, event times, storage |
| `LocalDate` | a date with no time or zone | birthdays, invoice dates |
| `LocalTime` | a time with no date or zone | opening hours |
| `LocalDateTime` | date + time, **no zone** | wall-clock descriptions only |
| `ZonedDateTime` | date + time + zone, DST-aware | user-facing scheduling |
| `OffsetDateTime` | date + time + fixed offset | wire formats, DB columns |
| `Duration` | time-based amount (seconds/nanos) | timeouts, elapsed time |
| `Period` | date-based amount (years/months/days) | "3 months from now" |

**Trap:** `LocalDateTime` is not an instant. It has no zone, so it does not identify a moment in time
and cannot be converted to epoch millis without supplying a zone. Storing `LocalDateTime` for an event
timestamp loses information the moment two regions are involved. Store `Instant` (or a
`TIMESTAMP WITH TIME ZONE` column).

**Trap:** DST. Adding `Duration.ofDays(1)` to a `ZonedDateTime` adds exactly 24 hours and can land on
the wrong wall-clock time across a DST boundary; `Period.ofDays(1)` adds one calendar day and keeps
the local time. Similarly, some local times do not exist (spring forward) or occur twice (fall back);
`ZonedDateTime` resolves these by documented rules rather than throwing, which surprises people.

Use `DateTimeFormatter` (immutable, thread-safe) — `DateTimeFormatter.ISO_INSTANT` for wire formats.
Inject a `Clock` rather than calling `Instant.now()` directly, so time is testable with
`Clock.fixed(...)`.

---

## 15. Pass-by-value of references

Java is **always pass-by-value**. For a reference type, the value copied is the reference (the
address), not the object. Two consequences:

```java
void mutate(List<String> list) { list.add("added"); }   // caller SEES this
void reassign(List<String> list) { list = new ArrayList<>(); }  // caller does NOT
```

Mutating through the copied reference affects the shared object. Reassigning the parameter only
rebinds the local copy. This is why "Java passes objects by reference" is wrong, and why swapping two
objects via a method is impossible in Java.

Same logic explains why passing a `String` and calling `toUpperCase()` inside a method changes nothing
for the caller — strings are immutable, so there is no mutation path at all.

---

## Atomic concept checklist

- [ ] Java has primitives and references; everything else is a reference type.
- [ ] Integer overflow wraps silently; `Math.addExact` throws instead.
- [ ] `Integer.valueOf` caches −128..127, so `==` on boxed values is true for 127 and false for 128.
- [ ] Unboxing a null wrapper throws NPE on a line with no visible call.
- [ ] String is immutable, caches its hash, and literals are interned in the pool.
- [ ] `new String("x") != "x"`; `intern()` returns the pooled instance; compare with `equals`.
- [ ] `+` in a loop is O(n²); use StringBuilder (default capacity 16, doubling growth).
- [ ] `final` prevents reassignment, not mutation; `static final` constants are inlined into callers.
- [ ] Checked exceptions must be handled or declared; Spring converts SQLException to unchecked.
- [ ] try-with-resources closes in reverse order and records close failures as suppressed exceptions.
- [ ] `return` inside `finally` discards the in-flight exception.
- [ ] Swallowing `InterruptedException` clears the interrupt flag and breaks cancellation.
- [ ] Generics are erased: no `new T[]`, no runtime type argument, no overload on erased signatures.
- [ ] Generics are invariant; arrays are covariant, which is why `ArrayStoreException` exists.
- [ ] PECS: `? extends T` to read, `? super T` to write.
- [ ] Default methods let interfaces evolve; a class implementation beats any default; `Object` methods cannot be defaulted.
- [ ] Non-static inner and anonymous classes hold the enclosing instance and can leak it.
- [ ] Lambdas capture effectively-final locals by value.
- [ ] Enum constants are JVM-unique — the correct singleton; never persist `ordinal()`; `values()` copies each call.
- [ ] Immutability needs final class, final fields, no setters, and defensive copies **both** in and out.
- [ ] `clone` is broken; prefer copy constructors. `finalize` is deprecated.
- [ ] Never use `double` for money; construct BigDecimal from a String.
- [ ] `BigDecimal.equals` compares scale, `compareTo` does not — 2.0 does not equal 2.00.
- [ ] `BigDecimal.divide` without a RoundingMode throws on non-terminating results.
- [ ] `SimpleDateFormat` is not thread-safe; `DateTimeFormatter` is.
- [ ] `LocalDateTime` has no zone and is not an instant; store `Instant` for event times.
- [ ] `Duration.ofDays(1)` is 24 hours; `Period.ofDays(1)` is one calendar day across DST.
- [ ] Java is pass-by-value always; you can mutate through a reference but never reassign the caller's variable.