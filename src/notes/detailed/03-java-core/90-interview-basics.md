# 03 Java Core — Part 1 interview wrap-up — BASICS (§1.1–§1.25)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](00-index.md)
Previous: [The DST harness](build-it/05i-dst-harness.md) · Next: [Part 2 interview wrap-up](91-interview-intermediate.md)

## Summary table

| Section | What it owns | The one thing that gets asked | Where it is written |
|---|---|---|---|
| §1.1 | Why the language substrate is a topic at all: 1995 design goals, source → `javac` → class file → JVM, the three normative documents, the JLS 21 chapter map, why primitives exist, erasure's consequences, backward and binary compatibility, the release train, what "Java 21" means and how to check what you are running | Why is testing `java.version.startsWith("1.")` stale on Java 9+? | [Language substrate](language-substrate/01-basics.md) |
| §1.2 | Lexical structure and literals: unicode source and `\uXXXX` processed before tokenisation, identifiers, contextual keywords, integer and floating literals, octal, underscores, character and string literals, text blocks, `null`, the operator table, comments | Why does a unicode escape for a line terminator inside a `//` comment break compilation? | [Language substrate](language-substrate/01-basics.md) |
| §1.3 | Primitive widths and ranges, two's-complement arithmetic and overflow, shifts and unsigned operations, floating point | Why does `Math.abs(Integer.MIN_VALUE)` come back negative? | [Primitives — basics](primitives-and-conversions/01-basics.md) |
| §1.4 | The reference-type lattice, `null`, `instanceof` on `null`, array supertypes | Does `x instanceof T` throw when `x` is `null`? | [Objects, equality and lifecycle — basics](objects-equality-and-lifecycle/01-basics.md) |
| §1.5 | Variables and declarations, the eight kinds of variable, definite assignment, scope, `var` | Which kinds of variable get a default value, and which never do? | [Classes and initialization — basics](classes-and-initialization/01-basics.md) |
| §1.6 | Operators, precedence and associativity, evaluation order, compound assignment, casts, the conditional operator, `String` concatenation | What is `attempt = attempt++;` and which three bytecodes explain it? | [Operators and expressions](primitives-and-conversions/02-operators-and-expressions.md) |
| §1.7 | The eleven conversion kinds and the six contexts that admit them, promotion, boxing, inference | Which conversions does an invocation admit that an assignment does not? | [Conversions and contexts](primitives-and-conversions/03-conversions-and-contexts.md) |
| §1.8 | Control flow — branches, loops, labelled `break`/`continue`, classic and pattern `switch`, `assert`, `synchronized`, `try`/`finally` | Why does a `return` inside `finally` discard an exception already in flight? | [Control flow — basics](control-flow/01-basics.md) |
| §1.9 | Wrappers, autoboxing/unboxing bytecode, the wrapper caches, boxing cost | Why does `Integer a = 127, b = 127; a == b` differ from the same code with `128`? | [Wrappers and autoboxing — basics](wrappers-and-boxing/01-basics.md) |
| §1.10 | The `String` API: immutability, hash caching, `substring`, `split`, case conversion, default charset | Why can `String` cache its `hashCode()` without any synchronization? | [Strings — basics](strings/01-basics.md) |
| §1.11 | The string pool, `intern()`, compile-time constant folding | Is `new String("AA-801") == "AA-801"`? | [The string pool](strings/01b-the-string-pool.md) |
| §1.12 | `Object`'s eleven members, the `equals`/`hashCode` contract, `toString`, `clone`, `wait`/`notify` | State the `equals`/`hashCode` contract precisely. | [`equals`, `hashCode` and `Object` methods](objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md) |
| §1.13 | Class anatomy, constructor delegation, the five-step `§12.5` object-creation order, class-initialization triggers | What does an overridable method called from a superclass constructor actually see? | [Initialization order](classes-and-initialization/01b-initialization-order.md) |
| §1.14 | Modifiers — `static`, `final`, `abstract`, access levels, constant variables | Why does changing a `static final int` in a library not change a caller's behaviour until it is recompiled? | [Modifiers](classes-and-initialization/02-modifiers.md) |
| §1.15 | Inheritance, method overriding rules, the three-phase overload-resolution algorithm | Why does adding a `reserve(int)` overload change which method an existing call binds to? | [Class inheritance and overriding](inheritance-and-dispatch/01-basics.md) |
| §1.16 | Interfaces, `default`/`static`/`private` interface methods, the diamond rules | How is a diamond conflict between two inherited `default` methods resolved? | [Interfaces](inheritance-and-dispatch/01b-interfaces.md) |
| §1.17 | Nested, inner, local, and anonymous classes; lambda capture; effectively-final locals | Why must a local captured by a lambda be effectively final? | [Nested classes](inheritance-and-dispatch/02-nested-classes.md) |
| §1.18 | Enum declaration, implicit members (`values()`, `valueOf`, `ordinal`, `name`), `EnumSet`/`EnumMap` | Why is referencing an enum's own static array before its constants finish a compile error, not a runtime NPE? | [Enums — basics](enums/01-basics.md) |
| §1.19 | Records — canonical and compact constructors, generated `equals`/`hashCode`/`toString`, sealed interfaces | What does a compact constructor actually do to the parameters versus the fields? | [Records](records-and-sealed/01-basics.md) |
| §1.20 | The exception model — checked vs unchecked, `Throwable` chaining, multi-catch, try-with-resources, `finally` traps | What is the actual rule that separates a checked exception from an unchecked one? | [The exception model](exceptions/01-basics.md) |
| §1.21 | Generics — erasure, bounded type parameters, wildcards and variance, raw types | Why is `List<CashEntry>` not a `List<LedgerEntry>` even though `CashEntry` is a `LedgerEntry`? | [Generics — basics](generics/01-basics.md) |
| §1.22 | Arrays — covariance, `Arrays` utilities, memory layout, varargs | Why does a covariant array assignment compile but still throw at run time? | [Arrays — basics](arrays/01-basics.md) |
| §1.23 | Packages, the classpath, import resolution, canonical vs binary names | What is the practical difference between `exports` and `opens` in a `module-info.java`? | [Packages, modules, annotations](language-substrate/02-packages-modules-annotations.md) |
| §1.24 | The module system — `requires`/`requires transitive`, unnamed and automatic modules, illegal reflective access | What is the difference between an unnamed module and an automatic module? | [Packages, modules, annotations](language-substrate/02-packages-modules-annotations.md) |
| §1.25 | Annotations — retention, `@Inherited`, `@Repeatable`, `@SafeVarargs`; the `java.lang` inventory | Why does an annotation with no `@Retention` become invisible to reflection? | [Packages, modules, annotations](language-substrate/02-packages-modules-annotations.md) |

## The twenty facts of Part 1

| Fact | Why it is true | Section |
|---|---|---|
| The `Integer` cache spans `-128..127` by default, and only its upper bound is tunable, via `-XX:AutoBoxCacheMax` or `-Djava.lang.Integer.IntegerCache.high` | JLS §5.1.7 mandates that range be shared; `IntegerCache.low` is a compile-time literal, `high` is read from the system property once at class init | §1.9 |
| `Integer a = 127, b = 127; a == b` is `true`; the same code with `128` is `false` | `127` resolves to the same cached instance from `IntegerCache.cache`; `128` falls outside the default range and allocates a fresh `Integer` each time | §1.9 |
| The string pool's contents have lived on the ordinary Java heap since Java 7; PermGen was removed entirely in Java 8 | JDK-6962931 moved interned `String` objects off PermGen; the `StringTable` itself was always a native hash table, holding weak references on JDK 21 | §1.11 |
| `new String("AA-801") == "AA-801"` is `false` | The literal is pooled by `ldc` on first resolution of the class's constant-pool entry; `new String(...)` always allocates a fresh header sharing the same backing array, never installing itself in the pool | §1.11 |
| The platform default charset has been UTF-8 since Java 18 | JEP 400 changed the default from the OS-dependent charset that every prior release used | §1.10 |
| Helpful `NullPointerException` messages naming the exact null expression are on by default since Java 15 | JEP 358 shipped opt-in behind a flag in Java 14 and switched the default in 15; `-XX:-ShowCodeDetailsInExceptionMessages` turns it back off | §1.9, §1.12 |
| `0.1 + 0.2` prints `0.30000000000000004`, not `0.3` | `double` is a binary floating-point format; neither `0.1` nor `0.2` has an exact binary64 representation, so their sum does not round to the decimal value `0.3` | §1.3 |
| `1 << 32` evaluates to `1`, not `0` | JVMS §6.5 masks an `int` shift distance to its low 5 bits (`n & 0x1f`); `32 & 0x1f == 0`, so the shift is a no-op | §1.3, §1.6 |
| `Math.abs(Integer.MIN_VALUE)` returns `Integer.MIN_VALUE`, still negative | Two's complement has one more negative value than positive; negating `Integer.MIN_VALUE` (invert, add one) reproduces the same bit pattern, so there is no positive counterpart to return | §1.3 |
| `(byte) 200` evaluates to `-56` | A narrowing primitive cast keeps the low 8 bits and reinterprets the top bit as the sign; `200` is `11001000`, whose signed value is `-56` | §1.3, §1.6 |
| A `return` inside a `finally` block discards any exception already propagating out of the `try`, silently | JLS §14.20.2: a `finally` block's own abrupt completion supersedes whatever completion the `try` or `catch` block was already carrying | §1.8, §1.20 |
| Try-with-resources closes resources in the reverse of their declaration order, and a `close()` failure is attached to the primary exception with `addSuppressed`, never replacing it | A later resource may depend on an earlier one, so teardown must run backwards; suppression (not substitution) preserves both failures for diagnosis | §1.20 |
| The checked/unchecked split is "everything under `Throwable` except the `Error` subtree and the `RuntimeException` subtree" — not "`Exception` is checked, `RuntimeException` is not" | `ClassNotFoundException` and `CloneNotSupportedException` sit directly under `Exception`, outside `RuntimeException`, and are checked; JLS §11.1.1 states the actual rule | §1.20 |
| The `equals`/`hashCode` contract requires equal objects to hash equally; the converse — unequal objects hashing equally — is a legal collision, not a violation | Hash-based collections rely on the forward direction only: they probe a bucket by hash and confirm membership with `equals`; violating the forward direction sends lookups to the wrong bucket where `equals` never runs | §1.12 |
| Calling an overridable method from a superclass constructor dispatches to the subclass's override, which then reads the subclass's fields at their default values | JLS §12.5's five-step object-creation order runs superclass step 3 (constructor invocation) before subclass step 4 (field initializers); the override executes inside that superclass step, before its own class's fields have been assigned | §1.13 |
| A `static final` field with a constant initializer is inlined into every caller's constant pool at compile time, so changing its value in a library has no effect on already-compiled callers until they are recompiled | JLS §13.1 calls this a constant variable; javac folds the literal directly into the caller's bytecode and never emits a `Fieldref` to the declaring class for it | §1.14 |
| Overload resolution runs in three phases — strict (no boxing, no varargs), then loose (boxing allowed), then variable arity — and the first phase with any applicable method wins outright | JLS §15.12.2.2–§15.12.2.4; there is no comparison across phases, so a widening-eligible overload always beats a boxing-eligible one even if the boxing target looks "closer" | §1.15 |
| An interface diamond conflict between two inherited `default` methods is a compile error unless a class-declared method or a more specific sub-interface already resolves it | The compiler applies "most specific" resolution first (a class method beats any default; a sub-interface's default beats its super-interface's); only a genuine tie needs `Interface.super.method()` | §1.16 |
| Generics are invariant while arrays are covariant: `List<CashEntry>` is not a `List<LedgerEntry>` at compile time, but `CashEntry[]` is a `LedgerEntry[]` and fails only at the point of a bad store | JLS §4.10 for generics invariance; JLS §10.10 for array covariance, enforced per-element by the `aastore` bytecode raising `ArrayStoreException` | §1.21, §1.22 |
| `values()` on an enum returns a freshly cloned array on every single call, and referencing the enum's own `$VALUES` holder before every constant has finished construction is a compile-time "illegal forward reference," never a runtime `NullPointerException` | The generated body is `getstatic $VALUES` / `invokevirtual clone()`; the forward-reference restriction is JLS definite-assignment analysis on the enum's own static field, resolved entirely at compile time | §1.18 |

## Interview Q&As

### "Walk me through `Integer a = 127, b = 127;` versus `Integer c = 128, d = 128;` under `==`. What actually happens?"

Both statements autobox an `int` literal into an `Integer`, but the two boxing calls land in different places, and that difference is the whole answer. Autoboxing always goes through `Integer.valueOf(int)`, never `new Integer(int)` — the constructor is deprecated for removal since Java 9 anyway. `valueOf` checks whether the argument falls in the cache's range, which JLS §5.1.7 mandates must cover at least `-128` to `127` inclusive, and which HotSpot implements as a `private static final class IntegerCache` nested inside `Integer`, holding a pre-built array of 256 `Integer` objects.

```java
// java.lang.Integer, simplified
public static Integer valueOf(int i) {
    if (i >= IntegerCache.low && i <= IntegerCache.high)
        return IntegerCache.cache[i + (-IntegerCache.low)];
    return new Integer(i);
}
```

For `127`, `valueOf` returns `IntegerCache.cache[127 + 128]` — the same shared object every time — so `a` and `b` are two references to one instance, and `a == b` compares those references and gets `true`. For `128`, the value is outside the cached range, so `valueOf` falls through to `new Integer(128)` independently for `c` and `d`, producing two distinct objects with two distinct identity hashes, so `c == d` is `false`. Nothing about the source syntax `Integer x = literal;` tells you which branch ran; only the numeric value crossing 127 does, which is exactly why this bug hides in code that only ever sees small values in testing or in a unit test with a suspiciously convenient fixture.

The fix is to never rely on `==` for wrapper comparison — use `.equals()`, or better, unbox to primitive `int` where the comparison is genuinely numeric and let the compiler's unboxing rules do the work instead of an identity check. The follow-up they will ask: is the cache boundary fixed? No — `IntegerCache.low` is hard-coded at `-128`, but `IntegerCache.high` can be raised with `-XX:AutoBoxCacheMax=n` (never lowered below 127), so this exact `==` boundary is not portable across JVM configurations, which makes it an environment-dependent bug on top of a subtle one.

### "Is `String` immutable, and how does the pool actually work?"

Yes — every field on `String` is `final`: the backing byte array, the coder byte that says whether the content is Latin-1 or UTF-16, and a cached `int hash`. No public method mutates a `String` in place; every operation that looks like mutation — `substring`, `concat`, `toUpperCase` — returns a new `String` and leaves the receiver untouched. Immutability is what makes the string pool possible at all: the pool, implemented as the JVM's `StringTable`, is a native hash table of weakly-referenced `String` objects, sized `StringTableSize = 65536` buckets by default on JDK 21, that lived in PermGen through Java 6 and has lived on the ordinary heap since Java 7.

A string literal like `"AA-801"` is resolved the first time the class file's `ldc` instruction touches that constant-pool entry, and the resolved `String` is installed in the table:

```java
String pooled = "AA-801";               // ldc, resolves + installs into StringTable
String copy   = new String("AA-801");   // fresh header, same bytes, never installed
System.out.println(pooled == "AA-801"); // true — same table entry, any class, any loader
System.out.println(copy == "AA-801");   // false — distinct header
System.out.println(copy.equals("AA-801")); // true — equals compares coder + bytes
```

`new String(...)` allocates a fresh `String` header that happens to share the same underlying `byte[]` as the pooled instance in some JVMs, but the new header is never installed in the table, so it is always a different object regardless. `intern()` is the manual door into the table: it returns the table's existing instance for equal content, or installs the receiver and returns it on a miss. The follow-up they will ask is whether over-interning is dangerous — that PermGen-exhaustion risk left with Java 8; what remains true on Java 21 is only that a huge number of distinct interned strings lengthens the table's hash chains and slows every subsequent literal resolution and `intern()` call, since there is no eviction API for the table itself.

### "State the `equals`/`hashCode` contract, and walk me through what breaks if a mutable field feeds `hashCode()`."

The contract, from `Object`'s javadoc, has five parts for `equals` — reflexive, symmetric, transitive, consistent across repeated calls given no mutation, and `x.equals(null)` must be `false`, never throw — plus one binding rule connecting it to `hashCode`: if two objects are equal, they must produce the same hash code. The reverse is not required — two unequal objects are allowed to collide on the same hash; that is just a bucket collision, not a contract violation. The dangerous direction is the one that is required: violate it and a `HashMap` silently stops finding things.

Concretely, suppose a `Restriction` key's `hashCode()` reads a mutable `status` field:

```java
Restriction key = new Restriction(RestrictionType.STAKE_BLOCKED, Source.ADMIN);
map.put(key, reservation);   // hashCode() computed with status = ACTIVE, bucket chosen
key.setStatus(LIFTED);       // same object, mutated in place, no new key created
map.get(key);                // hashCode() recomputed from CURRENT state -> different bucket -> null
```

`HashMap.get` recomputes `hashCode()` from the object's *current* state, gets a different hash than the one used at insertion, probes an entirely different bucket, and finds nothing — even though the key object is the exact same reference that was inserted. No exception, no warning; the entry is still in the map, just permanently unreachable through that key. The fix is structural: never let a field that can change after insertion feed `hashCode()` or `equals()`, which in practice means map keys should be immutable value types — `record`s are a natural fit because their generated `hashCode`/`equals`/`toString` derive from `final` components that cannot drift after construction. When you write these methods by hand, prefer `if (!(obj instanceof Restriction other)) return false;` for `equals` — it handles both `null` and the wrong type in one pattern-matching `instanceof` and reads cleanly against a `final` class. The follow-up they will ask: does a hash collision between unequal objects violate anything? No — only the forward direction (equal implies same hash) is mandatory.

### "Walk me through the exact order of operations when `new DormantAccount(...)` runs, given `DormantAccount extends Account`."

JLS §12.5 specifies five steps, but there is a step zero that precedes all of them: storage for every field on every class in the hierarchy — `Account`'s and `DormantAccount`'s — is allocated and zeroed to its default value before any constructor body runs at all. For the `DormantAccount` constructor actually invoked: step 1 binds the constructor's arguments to its parameter variables. Step 2 checks whether the body opens with an explicit `this(...)` call; if so, execution recurses into that constructor and jumps straight to step 5, skipping 3 and 4 because the delegated-to constructor already ran them. Step 3, assuming no `this(...)`, invokes the superclass constructor — explicit or the compiler-inserted no-arg `super()` — recursing through the same five steps for `Account`. Step 4 runs `DormantAccount`'s own instance initializer blocks and field initializers, in the single textual order they appear in the source. Step 5 runs the rest of `DormantAccount`'s constructor body.

```java
class Account {
    Account() { describe(); }                 // step 5 of Account — calls the OVERRIDE
    void describe() { System.out.println("base"); }
}
class DormantAccount extends Account {
    private final String reasonCode = "DORMANT_FROZEN";  // step 4 — not run yet above
    @Override void describe() { System.out.println(reasonCode); }  // prints null
}
```

The net effect: constructor *invocations* are requested top-down, but complete bottom-up — `Account`'s full construction (its own steps 1 through 5) finishes before `DormantAccount`'s step 4 even starts. This is exactly why calling an overridable method from a superclass constructor is dangerous: the call happens during `Account`'s step 5, nested inside `DormantAccount`'s step 3, which runs strictly before `DormantAccount`'s step 4 — so the override sees `reasonCode` at its zeroed default, `null`, not `"DORMANT_FROZEN"`. The JLS names this a deliberate choice: "Unlike C++, the Java programming language does not specify altered rules for method dispatch from within constructors." The follow-up they will ask: how do you avoid this? Never call an overridable instance method from a constructor — call only `private` or `final` methods there, or move the logic to a static factory that runs after construction completes.

### "What does `final` actually guarantee on a variable, a method, and a class — and where does that guarantee stop?"

On a local variable or field, `final` means exactly one assignment is legal, checked at compile time via definite-assignment analysis for locals and via constructor/initializer analysis for fields — nothing more. It says nothing about the object the variable refers to:

```java
final List<Movement> movements = new ArrayList<>();
movements = new ArrayList<>();  // compile error — reassigning the reference
movements.add(m);               // fine — final freezes the slot, not the referent
```

On a method, `final` forbids overriding in any subclass; the compiler rejects a subclass declaration with the same signature outright, and `final` methods compile to `invokevirtual`, not `invokespecial` — there is no override to resolve, so the JIT can inline freely. On a class, `final` forbids subclassing altogether; no `extends` against it, from any package, in any module.

The place all three interact is a `static final` primitive or `String` field initialized with a constant expression: JLS §4.12.4 calls this a *constant variable*, and §13.1 requires that reads of it resolve to the literal value at compile time and get copied — inlined — into every caller's bytecode, with no `Fieldref` back to the declaring field left behind. That is the mechanism behind the classic stale-deploy bug: change `BONUS_RATE_PERCENT` from `10` to `12` in a shared library and republish the jar, and a consumer compiled against the old value keeps splitting bonuses at 10% with no error and no exception, because its class file literally contains `bipush 10` and never looks the field up again — only recompiling the consumer picks up the new value. The follow-up they will ask: how do you avoid the stale-deploy trap? Stop the field from qualifying as a constant variable — read it from configuration into a non-`final` field, or expose it through a method call instead of a bare field read.

### "What's the actual difference between overload resolution and overriding, mechanically?"

They are resolved by different machines at different times, using different information. Overload resolution — choosing which of several methods named `reserve` to call — is entirely a compile-time decision made by `javac`, based purely on the *static* (declared) types of the arguments at the call site, and it runs in three ordered phases per JLS §15.12.2: phase 1 considers only identity and widening conversions, no boxing and no variable arity; phase 2 adds boxing and unboxing; phase 3 adds variable arity. The compiler tries phase 1 first, and if any applicable method exists in that phase, it picks the most specific one and stops:

```java
void reserve(int stakeCents) { /* ... */ }
void reserve(long stakeCents) { /* ... */ }
void reserve(Integer stakeCents) { /* ... */ }

reserve(420);  // binds to reserve(int) in phase 1 — widening never even reaches boxing
```

Delete `reserve(int)` and the same call binds to `reserve(long)`, still in phase 1, via widening — the compiler never reaches for `reserve(Integer)` even though it exists, because phase 1 already found a match. Once resolution finishes, the *method descriptor* to invoke is baked into the constant pool as a fixed reference; that part never changes at runtime. Overriding is the opposite: it is a runtime decision, made once per call, based on the *actual* (runtime) class of the receiver object, using `invokevirtual` (or `invokeinterface` for an interface-typed receiver) to look up the method in that class's vtable. The follow-up they will ask: does this apply to fields too? No — a field access compiles to `getfield`, resolved by the compiler against the receiver's *static* type, so casting a `DormantAccount` reference to `Account` changes which field you read but never changes which overridden method a call dispatches to, because method lookup ignores the cast entirely and asks the actual object what class it is.

### "What does type erasure actually erase, and what breaks because of it?"

Erasure, JLS §4.6, replaces every parameterized type with its raw type and every type variable with the erasure of its leftmost bound — `Object` if unbounded — uniformly across the compiled class file: field types, method parameter and return types, local variable types all collapse to the erased form. The original parameterized signature survives only in a `Signature` attribute that reflection can read but the JVM's own dispatch and verification never consult. Three concrete consequences fall straight out of that.

First, you cannot overload two methods that differ only in a generic type argument:

```java
void book(List<Money> amounts) { /* ... */ }
void book(List<StatusCode> codes) { /* ... */ }  // compile error: name clash
```

Both erase to descriptor `(Ljava/util/List;)V`, and a class file identifies a method by name plus descriptor, so `javac` rejects the second declaration outright. Second, you cannot create a generic array — `new T[n]` fails with "generic array creation" — because array covariance depends on the JVM checking a component type at every store via `aastore`, and an erased `T` leaves nothing real to check against; the one place this surfaces at runtime instead of compile time is a varargs parameter of a non-reifiable type, "heap pollution," which is exactly what `@SafeVarargs` suppresses the warning for, under three conditions it never verifies: never store into the array, never let it escape, and the method cannot be overridden. Third, a raw type erases the type of *every member*, not just the class's own type parameter — assigning through a raw `List` with the wrong element type compiles with only an unchecked warning, and the `ClassCastException` surfaces much later, at the next typed read, in code that has nothing to do with where the bad value was inserted. The follow-up they will ask: why does Java do this instead of reifying generics like C#? Backward and binary compatibility with pre-generics bytecode — erasure let generic and raw code interoperate on the same class files without a JVM change.

### "What's the real rule for checked versus unchecked exceptions, and what happens if a `return` sits inside a `finally` block?"

The rule people usually state — "checked exceptions extend `Exception`, unchecked ones extend `RuntimeException`" — is wrong, and the standard example that breaks it is `ClassNotFoundException` and `CloneNotSupportedException`, both of which extend `Exception` directly, are outside the `RuntimeException` subtree, and are checked. The actual rule, JLS §11.1.1: a checked exception is anything under `Throwable` that is *not* in the `Error` subtree and *not* in the `RuntimeException` subtree. `Error` never extends `Exception`, which is why `catch (Exception e)` never intercepts `OutOfMemoryError` or `StackOverflowError` — a request-handling boundary that assumes `catch (Exception e)` is a universal safety net will watch those two sail straight past it and kill the thread. The catch-or-declare rule — a checked exception must either be caught or named in a `throws` clause — is compiler-enforced and applies only to the checked family; unchecked exceptions propagate through every intermediate frame with no signature changes required anywhere, silently. As for `finally`: JLS §14.20.2 states that a `finally` block's own abrupt completion — a `return`, `break`, `continue`, or `throw` inside it — supersedes whatever the `try` or `catch` block was already doing, unconditionally. Concretely,
```java
static int settlementDelta() {
    try {
        return 10;
    } finally {
        return 20;
    }
}
```
returns `20`, and if the `try` block had thrown an exception instead of returning `10`, that exception would be discarded just as completely — not caught, not suppressed, not chained onto anything; it is stored to a dead local by the compiler's `astore` and never read again. The bytecode shape is identical across JDK 8, 17, and 21. This is exactly the failure mode try-with-resources exists to avoid: a hand-written `finally { resource.close(); }` that throws *replaces* whatever the `try` block was propagating, whereas the compiler-generated desugaring for `try (var resource = ...)` attaches a `close()` failure onto the primary exception with `addSuppressed` instead, preserving both.

### "Why must a local variable captured by a lambda or an anonymous class be effectively final?"

Because the lambda or anonymous class does not read the enclosing method's stack frame at all — by the time the lambda body runs, that frame may not even exist any more, if the method that created it has already returned. Java's answer is capture-by-value: at the point the lambda or anonymous class instance is created, the compiler copies the *current value* of each local it references into a synthetic field on the generated class — `val$name` for an anonymous or local class, or a constructor argument baked into the hidden lambda class — and every reference inside the body reads from that copy, not from the original stack slot.

If the source local could be reassigned after that copy was taken, the copy and the original would immediately be able to disagree, and there is no mechanism to keep two independent storage locations in step across an arbitrary future reassignment — so the compiler forbids the situation entirely by requiring the captured local to be effectively final: not declared `final`, but never the target of an assignment expression after its declaration, and never the operand of `++`/`--`, checked by the same JLS definite-assignment machinery used elsewhere in the language. This restriction applies only to locals and parameters, never to fields — a field is reached through `this$0`, the enclosing instance reference, which the nested class holds onto for its whole lifetime, so a field read always sees the current value with no staleness question at all.

```java
int reservationsSeen = 0;
reservations.forEach(r -> reservationsSeen++);  // compile error: not effectively final

AtomicInteger reservationsSeen = new AtomicInteger();
reservations.forEach(r -> reservationsSeen.incrementAndGet());  // fine — reference never reassigned
```

The follow-up they will ask: why does this compile-error-free pattern work? Because the lambda captures the *reference* to the `AtomicInteger`, which is itself effectively final and never reassigned — the mutation happens on the referent's internal state, which capture-by-value never touches at all. This is exactly the pattern QuizStakes stream pipelines use for a per-request accumulator: a plain captured `int` cannot be incremented from inside a lambda, but an `AtomicInteger` or an array cell mutated through its single reference can.

### "What implicit members does the compiler generate for an enum, and why is calling `values()` in a tight loop a problem?"

Every enum, with no code of your own beyond the constant list, compiles to a `final class` extending `java.lang.Enum<E>`, and the compiler synthesizes two `public static` members you never wrote: `E[] values()` and `E valueOf(String)`, backed by a private static array field conventionally called `$VALUES` that is populated in the class's `<clinit>` in declaration order. `values()`'s body is exactly four bytecode instructions:

```
getstatic     $VALUES
invokevirtual clone
checkcast     [LRestrictionType;
areturn
```

That `clone()` call is not decorative — `$VALUES` is the single shared backing array for the whole class, and handing out the live array itself would let any caller mutate the constant order for every other caller in the JVM. The consequence is that `values()` allocates a brand-new array on every single invocation, so calling `RestrictionType.values()` inside a hot loop, or inside a per-request method, does an allocation and a full array copy for no reason beyond re-reading a list that never changes at runtime. The fix is to cache the result once — a `private static final` array or an unmodifiable `List` built from it at class-init time — or switch to `EnumSet.allOf(RestrictionType.class)`, since `EnumSet`'s internals read the JVM's shared, never-cloned constant array directly. The follow-up they will ask: what if you reference the enum's own static array too early?

```java
enum RestrictionType {
    STAKE_BLOCKED, WITHDRAWAL_BLOCKED;
    static final RestrictionType[] CACHED = values();  // fine — runs after all constants exist
}
```

Referencing `$VALUES` (or any static field of the enum type) from inside one of the enum's *own constant initializers*, before every constant has finished construction, is not a `NullPointerException` at run time — it is a compile-time "illegal forward reference" error, because definite-assignment analysis tracks the enum's own static array exactly the way it tracks any other static field read before its declaration point in the same class.

## Predict the output

```java
public class WrapperCacheBoundary {
    public static void main(String[] args) {
        Integer clientCountA = 127;
        Integer clientCountB = 127;

        Integer sessionCountA = 128;
        Integer sessionCountB = 128;

        System.out.println((clientCountA == clientCountB) + " " + (sessionCountA == sessionCountB));
    }
}
```

**Output**
```
true false
```

**Why** Both assignments autobox through `Integer.valueOf(int)`, never `new Integer(int)`. `127` falls inside `IntegerCache`'s default `-128..127` range, so `valueOf` returns the same shared cached instance for both `clientCountA` and `clientCountB`, making `==` — a reference comparison on two `Integer` operands per JLS §15.21.3 — return `true`. `128` falls outside that range, so `valueOf` falls through to `new Integer(128)` independently for `sessionCountA` and `sessionCountB`, producing two distinct heap objects with two distinct identity hashes, so the same `==` comparison returns `false`. Nothing about the source syntax distinguishes the two cases; only the numeric value crossing the cache boundary does.

```java
public class SettlementFinallyOverride {
    static int settle() {
        try {
            throw new IllegalStateException("ledger imbalance");
        } finally {
            return 20;
        }
    }

    public static void main(String[] args) {
        System.out.println(settle());
    }
}
```

**Output**
```
20
```

**Why** JLS §14.20.2 states that a `finally` block's own abrupt completion supersedes whatever completion the `try` block was already carrying. The `try` block throws `IllegalStateException`, but before that exception can propagate out of `settle()`, the `finally` block runs, and its `return 20` is itself an abrupt completion of the method — which wins outright. The exception is not caught, not suppressed onto anything, not logged; the compiler stores the in-flight exception reference to a local slot with `astore` purely as an artifact of how `finally` is desugared, and nothing ever reads that slot again. `settle()` returns `20` as if the `throw` had never executed.

```java
public class ReservationCounterIncrement {
    public static void main(String[] args) {
        int reservationSequence = 2;
        int delta = reservationSequence++ + ++reservationSequence;
        System.out.println(delta + " " + reservationSequence);
    }
}
```

**Output**
```
6 4
```

**Why** `reservationSequence++` is postfix: its *value* in the expression is the value before incrementing, `2`, and the increment to `3` happens as a side effect that is visible to subsequent reads. `++reservationSequence` is prefix: it increments first, to `4`, and its value in the expression is that new value. JLS §15.7 fixes left-to-right evaluation order for both operands of `+`, so the left operand's postfix increment resolves and applies before the right operand's prefix increment runs. The sum is `2 + 4 = 6`; `reservationSequence` itself ends at `4`, the value left by the last increment applied, regardless of what value was captured earlier into the sum.

```java
public class RestrictedAccountConstructionOrder {
    static class Account {
        Account() {
            describe();
        }
        void describe() {
            System.out.println("Account: base");
        }
    }

    static class DormantAccount extends Account {
        private final String reasonCode = "DORMANT_FROZEN";

        @Override
        void describe() {
            System.out.println("DormantAccount: " + reasonCode);
        }
    }

    public static void main(String[] args) {
        new DormantAccount();
    }
}
```

**Output**
```
DormantAccount: null
```

**Why** `new DormantAccount()` runs the compiler-inserted `super()` first, per JLS §12.5 step 3, which executes `Account`'s constructor body — and that body calls `describe()`. Dispatch for an instance method call always uses the *runtime* class of the receiver, so `describe()` resolves to `DormantAccount`'s override even though the call textually appears inside `Account`'s own constructor. But `DormantAccount`'s field initializers are step 4, which runs strictly after step 3 completes — so at the moment the override executes, `reasonCode` still holds the default value every reference field gets before any constructor body runs: `null`. The field initializer `"DORMANT_FROZEN"` has not been reached yet. No exception is thrown; the program prints a plainly wrong value with no diagnostic at all, which is exactly why this pattern is dangerous rather than merely surprising.

```java
public class LongHashCollision {
    public static void main(String[] args) {
        Long baseline = 1L;
        Long wrapped = 4_294_967_296L; // 2^32

        System.out.println(baseline.hashCode() + " " + wrapped.hashCode() + " " + baseline.equals(wrapped));
    }
}
```

**Output**
```
1 1 false
```

**Why** `Long.hashCode()` is specified as `(int) (value ^ (value >>> 32))`. For `1L`, `value >>> 32` is `0`, so the hash is `(int) (1 ^ 0) = 1`. For `4_294_967_296L`, which is exactly `2^32` — bit pattern `0x1_00000000` — `value >>> 32` shifts the single high bit down to `0x1`, and XOR-ing that against the original value gives `0x1_00000001`; truncating to `int` discards the high 32 bits entirely, leaving `1`. The two completely different `long` values collide on the same hash code. That collision is legal under the `equals`/`hashCode` contract — only equal objects are required to hash equally, not the reverse — so `baseline.equals(wrapped)` still correctly returns `false`, because `Long.equals` compares the full 64-bit value, not the hash. A `HashMap<Long, ?>` handles this correctly by falling back to `equals` within the colliding bucket; the surprise is purely that two values eight billion apart share a hash bucket at all.

---

**Leaves covered:** none — Part 1 wrap-up over §1.1–§1.25, whose leaves are owned by the files linked in the summary table
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 341
