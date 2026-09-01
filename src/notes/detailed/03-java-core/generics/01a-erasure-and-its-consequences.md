# 03 Java Core — Erasure, stated once, and everything that follows from it — BASICS (§1.21, 1.21.7, 1.21.8, 1.21.17)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Generics: the basics](01-basics.md) · Next: [Variance and wildcards](01b-variance-and-wildcards.md)

This file states the erasure mechanism once, precisely, with spec text and real `javap` output, then derives the six consequences that follow from it, then defines the reifiable/non-reifiable split that those consequences all reduce to. It does not cover invariance, array covariance, wildcards or PECS — that is `01b-variance-and-wildcards.md`. It does not cover raw types or `@SuppressWarnings` — that is `01c-raw-types-and-unchecked-warnings.md`. It does not walk bridge methods, heap pollution, capture conversion, or the full class-file layout — those are internals-tier files listed at the end of each section below. Everything quoted here was compiled and disassembled on Oracle JDK 21.0.7 (`21.0.7+8-LTS-245`) for this file.

## 1. Erasure, stated once (1.21.7)

Picture the compiler doing two separate jobs at two separate times. During compilation, `javac` has the full picture: `Repository<T extends LedgerEntry>`, `Repository<CashEntry>`, `List<Money>` — every type argument, every bound, fully resolved, and it uses that picture to reject anything that doesn't type-check. Then, the moment it needs to emit a `.class` file, it throws almost all of that picture away. The class file that ships has one shape per generic declaration, not one per parameterisation. `Repository<CashEntry>` and `Repository<BonusEntry>` are not two classes at runtime — there is exactly one `Repository.class`, and the type argument has been erased out of every descriptor in it. What the compiler checked never reappears at the class-file level except as a side-channel attribute nobody but reflection reads.

### Why it exists

Generics landed in Java 5 in 2004, twelve years after Java 1.0 shipped `Collection`, `Vector`, `Hashtable` with raw `Object`-typed elements. Millions of lines of that code, and the JVM bytecode already compiled from it, had to keep running unchanged after the upgrade. Erasure was the mechanism that let `List<String>` become, at the bytecode level, indistinguishable from the raw `List` the JVM already knew how to load, verify and link — no new bytecode instructions, no new class-file version, no `.class` file breaking on an old JVM that had never heard of a type parameter. The alternative — a new descriptor per parameterisation, sometimes called *reification* or *specialisation* — is what C++ templates and .NET generics do, and it was rejected for Java 5 specifically because it would have meant `ArrayList<String>` and the already-compiled `ArrayList` could no longer be the same class file. The full cost/benefit argument for that decision, and what a reified alternative would have bought and cost, is `03e-internals-why-erasure-and-super-type-tokens.md`; here the point is only that the choice was migration compatibility with 1.4 collections, stated once, moving on.

### The mechanism

**[SOURCE]** JLS 21 §4.6 defines erasure as a function on types, applied recursively:

> The erasure of a parameterized type (§4.5) `G<T1, T2, up to Tn>` is `|G<T1, T2, up to Tn>|`.
> The erasure of a nested type `T.C` is `|T|.C`.
> The erasure of an array type `T[]` is `|T|[]`.
> The erasure of a type variable (§4.4) is the erasure of its leftmost bound.
> The erasure of every other type is the type itself.

Read each clause against `Repository<T extends LedgerEntry>`:

- **Parameterized type → erasure of the raw type.** `Repository<CashEntry>` erases to `Repository` — the raw class, with every type argument stripped. This is why `Repository<CashEntry>` and `Repository<BonusEntry>` are the same class at runtime: erasure does not look at the argument at all, it discards it.
- **Type variable → erasure of its leftmost bound.** `T extends LedgerEntry` has one bound, `LedgerEntry`, so every occurrence of `T` in `Repository`'s method signatures erases to `LedgerEntry`. If `T` had no explicit bound, its implicit bound is `Object` and it erases to `Object` — that is the case for a plain `<T>` with no `extends` clause. A type variable with an intersection bound (`<T extends Comparable<T> & Serializable>`) erases to the first type in the intersection, left to right — hence "leftmost."
- **Array type → array of the erasure.** `T[]` erases to `LedgerEntry[]`, `List<CashEntry>[]` erases to `List[]`.
- **Everything else → itself.** `Money`, `int`, `UUID` are already non-generic; erasure is the identity function on them.

Now the real evidence. `Repository<T extends LedgerEntry>` declares `T find(UUID id)` and `void save(T entry)`. Compiled and disassembled with `javap -p -v` on JDK 21.0.7:

```
class Repository<T extends LedgerEntry> extends java.lang.Object
Constant pool:
  #32 = Utf8   Signature
  #33 = Utf8   Ljava/util/Map<Ljava/util/UUID;TT;>;
  #41 = Utf8   (Ljava/util/UUID;)TT;
  #42 = Utf8   <T::LLedgerEntry;>Ljava/lang/Object;
{
  T find(java.util.UUID);
    descriptor: (Ljava/util/UUID;)LLedgerEntry;
    flags: (0x0000)
    Signature: #41    // (Ljava/util/UUID;)TT;

  void save(T);
    descriptor: (LLedgerEntry;)V
    flags: (0x0000)
    Signature: #38    // (TT;)V
}
Signature: #42    // <T::LLedgerEntry;>Ljava/lang/Object;
```

Three things to read off this, line by line:

- **`descriptor: (Ljava/util/UUID;)LLedgerEntry;`.** This is the erased signature — the one the JVM actually links against, checks at every call site, and uses for method dispatch. `T` is gone; `LLedgerEntry;` is what's left, because `LedgerEntry` is `T`'s leftmost (only) bound. Any caller anywhere in the program that invokes `Repository.find` links to exactly this descriptor, regardless of whether it holds a `Repository<CashEntry>` or a `Repository<BonusEntry>` reference.
- **`Signature: #41 // (Ljava/util/UUID;)TT;`.** This is the `Signature` attribute — a JVMS-defined optional attribute (JVMS 4.7.9) that records the pre-erasure generic signature as a string in the constant pool. It is not consulted by the verifier, the linker, or `invokevirtual`/`invokeinterface` at a call site. Its only consumer is reflection: `Method.getGenericReturnType()`, `Field.getGenericType()`, `Class.getGenericSuperclass()` parse this string to hand back `ParameterizedType`/`TypeVariable` objects. Delete the `Signature` attribute (which is exactly what happens for anonymous local variables and for any class file older than 5) and reflection falls back to the raw erased type.
- **`Signature: #42 // <T::LLedgerEntry;>Ljava/lang/Object;`** on the class itself records that `Repository` is generic over one type variable `T`, bounded by `LedgerEntry` (`::` marks an interface bound in this signature grammar; a single colon marks a class bound), extending `Object`.

Now the caller-side half, because this is the fact the whole bridge-method file builds on. Given `AbstractStore<E extends LedgerEntry> extends Repository<E>`, `CashEntryStore extends AbstractStore<CashEntry>`, and a caller:

```java
class Caller {
    static CashEntry fetch(Repository<CashEntry> repo, UUID id) {
        CashEntry entry = repo.find(id);
        return entry;
    }
}
```

`javap -p -c -v Caller.class` on JDK 21.0.7:

```
static CashEntry fetch(Repository<CashEntry>, java.util.UUID);
  descriptor: (LRepository;Ljava/util/UUID;)LCashEntry;
  Code:
     0: aload_0
     1: aload_1
     2: invokevirtual #7   // Method Repository.find:(Ljava/util/UUID;)LLedgerEntry;
     5: checkcast     #13  // class CashEntry
     8: astore_2
     9: aload_2
    10: areturn
  Signature: #22   // (LRepository<LCashEntry;>;Ljava/util/UUID;)LCashEntry;
```

`repo.find(id)` compiles to `invokevirtual` against `Repository.find:(Ljava/util/UUID;)LLedgerEntry;` — the erased descriptor, returning `LedgerEntry`, exactly the one `Repository.class` declares. There is no `CashEntry`-returning overload of `find` anywhere; the JVM has never heard of that type. Immediately after the call, bytecode offset `5` is `checkcast #13 // class CashEntry` — a runtime type check inserted by `javac`, not by the reader, not by anything in `Repository` or `AbstractStore` or `CashEntryStore`. **The cast the reader never wrote is in the caller's bytecode, not the callee's.** `Repository.find` itself never mentions `CashEntry`; it hands back a plain `LedgerEntry` reference, and every place that reference gets assigned to a more specific local variable, field, or return type gets its own `checkcast` stamped in by the compiler at that assignment site. That is the exact mechanism `03a-internals-bridge-methods.md` builds its `ClassCastException` scenario on: when the erased type at the call site and the compile-time expected type disagree — because of an unchecked cast, a raw-typed call, or reflective trickery — this inserted `checkcast` is where the exception fires, and the stack trace points at the caller, which is often confusing to someone who has never seen this bytecode.

**Insight:** two attributes exist for the exact same information at two levels of precision, and only one of them is load-bearing at a call site. The descriptor is what the JVM links against; the `Signature` attribute is what reflection reads. Confusing "what the type checker verified" with "what the JVM enforces" is the single misunderstanding erasure produces more than any other.

**Interview:** "Explain type erasure." The one-line answer: `javac` type-checks against the full generic type, then replaces every type variable with the erasure of its leftmost bound in the emitted descriptor, inserts a `checkcast` at every point a caller narrows the erased type back to something specific, and keeps the original generic signature only in a `Signature` attribute that only reflection reads.

> Erasure is the rule that a generic type's runtime shape is its raw shape with every type variable replaced by the erasure of its leftmost bound — checked once by `javac`, discarded from every descriptor, and preserved only in the `Signature` attribute for reflection.

## 2. The six consequences (1.21.8)

Everything below is a direct corollary of §1 above: the runtime has one class per generic declaration, so anything that needs a type argument to exist at runtime is unavailable. Rather than six paragraphs, here is the list, then one demonstration of each.

| # | Consequence | Real `javac`/`java` evidence | Owning workaround, in which file |
|---|---|---|---|
| 1 | One runtime class per generic class, regardless of parameterisation | `getClass()` equal across `List<CashEntry>` and `List<BonusEntry>` | n/a — this *is* erasure |
| 2 | No `new T[n]` | `error: generic array creation` | `Array.newInstance` — `03b-internals-reifiable-types-and-generic-arrays.md` |
| 3 | No `new T()` | `error: unexpected type … found: type parameter T` | `Class<T>` as a factory — `02a-type-tokens-and-generic-reflection.md` |
| 4 | No `instanceof List<CashEntry>` | `error: Object cannot be safely cast to List<CashEntry>` | Wildcard `instanceof List<?>` is legal — see §3 below |
| 5 | No overload on erased signatures | `error: name clash: … have the same erasure` | In depth — `03d-internals-erasure-limits-and-capture.md` |
| 6 | Static fields shared across every parameterisation | Printed count of `2`, not `1` per type | In depth — `03d-internals-erasure-limits-and-capture.md` |

**1. One runtime class regardless of parameterisation.** `List<CashEntry>` and `List<BonusEntry>` are, at runtime, both plain `ArrayList` objects with no memory of what they were declared to hold:

```java
import java.util.ArrayList;
import java.util.List;

class RuntimeClassDemo {
    public static void main(String[] args) {
        List<CashEntry> cashStakes = new ArrayList<>();
        List<BonusEntry> bonusGrants = new ArrayList<>();
        System.out.println(cashStakes.getClass() == bonusGrants.getClass());
        System.out.println(cashStakes.getClass());
    }
}
```

Run on JDK 21.0.7:

```
true
class java.util.ArrayList
```

`getClass()` returns the actual runtime class — `ArrayList` — and it is the *same* `Class` object for both variables. There is no `ArrayList$CashEntry` and no `ArrayList$BonusEntry`; the JVM class-loaded exactly one `ArrayList.class`, once, and both lists point at it.

**2. No `new T[n]`.** A `Reservation<T extends LedgerEntry>` that tries to allocate a batch array of `T`:

```java
class Reservation<T extends LedgerEntry> {
    T[] batch(int n) {
        return new T[n];
    }
}
```

```
Reservation.java:3: error: generic array creation
        return new T[n];
               ^
1 error
```

Array creation needs a concrete component type baked into the instruction (`anewarray` takes a constant-pool class reference, not a variable). Since `T` erases to `LedgerEntry` and `javac` has no way to know at this call site whether the caller wanted a `CashEntry[]` or a `BonusEntry[]`, it refuses outright rather than silently hand back a `LedgerEntry[]` that would later blow up with `ArrayStoreException` on a store. The reifiable-array construction that does work, and why it works, is `03b-internals-reifiable-types-and-generic-arrays.md`.

**3. No `new T()`.** A generic factory method that tries to instantiate its own type parameter:

```java
class Blank<T extends LedgerEntry> {
    T fresh() {
        return new T();
    }
}
```

```
Blank.java:3: error: unexpected type
        return new T();
                   ^
  required: class
  found:    type parameter T
  where T is a type-variable:
    T extends LedgerEntry declared in class Blank
1 error
```

`new` needs a class it can allocate and call a constructor on; `T` at this point in compilation is not a class, it is a type variable, and after erasure it would be `LedgerEntry` — an interface with no constructor at all, so even ignoring the type-variable rule, `new LedgerEntry()` is meaningless. The workaround is to accept a `Class<T>` token (or a `Supplier<T>`) and let the caller supply the concrete factory; that pattern belongs to `02a-type-tokens-and-generic-reflection.md`.

**4. No `instanceof List<CashEntry>`.** A runtime type test against a parameterized type:

```java
import java.util.List;

class InstanceofGeneric {
    boolean isCashList(Object o) {
        return o instanceof List<CashEntry>;
    }
}
```

```
InstanceofGeneric.java:5: error: Object cannot be safely cast to List<CashEntry>
        return o instanceof List<CashEntry>;
               ^
1 error
```

`instanceof` compiles to the `instanceof` bytecode instruction, which checks against a class-file reference — and at runtime there is no such thing as a `List<CashEntry>` class reference to check against, only `List`. `o instanceof List<?>` is legal (§3 below explains exactly why the wildcard survives when the concrete argument doesn't); testing for a *specific* parameterisation is not, because there is nothing left at runtime to distinguish `List<CashEntry>` from `List<BonusEntry>` — see consequence 1.

**5. No overload on erased signatures.** Two `post` overloads that differ only in type argument:

```java
import java.util.List;

class OverloadClash {
    void post(List<CashEntry> entries) {
    }

    void post(List<BonusEntry> entries) {
    }
}
```

```
OverloadClash.java:7: error: name clash: post(List<BonusEntry>) and post(List<CashEntry>) have the same erasure
    void post(List<BonusEntry> entries) {
         ^
1 error
```

Both descriptors erase to `post(Ljava/util/List;)V` — identical — and the JVM's method table is keyed on name-plus-erased-descriptor, so these two methods would collide the instant the source got past `javac`. The `javac` diagnostic to recognise here is the literal phrase "have the same erasure" — seeing it in a build log means an overload set differs only in type argument. The full treatment of why this rule interacts badly with bridge methods and inherited generics is `03d-internals-erasure-limits-and-capture.md`.

**6. Static fields shared across every parameterisation.** Because there is one `Counter.class` regardless of parameterisation, there is exactly one copy of any `static` field, shared by every `Counter<CashEntry>` and `Counter<BonusEntry>` instance in the process:

```java
class Counter<T extends LedgerEntry> {
    static int postings = 0;

    void post(T entry) {
        postings++;
    }
}

class StaticSharedDemo {
    public static void main(String[] args) {
        Counter<CashEntry> cash = new Counter<>();
        Counter<BonusEntry> bonus = new Counter<>();
        cash.post(new CashEntry(java.util.UUID.randomUUID(), null));
        bonus.post(new BonusEntry(java.util.UUID.randomUUID(), null));
        System.out.println(Counter.postings);
    }
}
```

Run on JDK 21.0.7:

```
2
```

One posting through the `CashEntry`-parameterised reference and one through the `BonusEntry`-parameterised reference both incremented the *same* field. A developer expecting `Counter<CashEntry>.postings` and `Counter<BonusEntry>.postings` to be independent counters — as if `T` were reified per instance — gets silent cross-contamination instead, because `static` fields belong to the one class `Counter`, not to any parameterisation of it. This is exactly the trap `03d-internals-erasure-limits-and-capture.md` explores in depth, including why `static` members cannot themselves refer to a class's own type parameter.

**No gotcha beyond the six themselves:** each of these already surprises on first contact; there is no further twist layered on top of the list itself at BASICS depth.

> Because `javac` erases every generic class to one raw runtime shape, anything that needs a type argument to exist as a runtime value — a fresh array, a fresh instance, a runtime type test, an overload key, or an independent static slot — is unavailable, and the compiler either refuses at compile time or, for statics, silently shares state instead.

## 3. Reifiable vs non-reifiable types (1.21.17)

**[RESEARCH]** Every consequence in §2 traces back to one underlying split: a type either survives erasure with enough information intact for the JVM to check against it at runtime, or it doesn't. JLS 21 §4.7 calls the first kind *reifiable* and gives the exact enumeration — not "generics aren't reifiable" as a blanket rule, but a precise list of which specific shapes qualify:

> A type is reifiable if and only if one of the following holds:
> - It refers to a non-generic class or interface type declaration.
> - It is a parameterized type in which all type arguments are unbounded wildcards (§4.5.1).
> - It is a raw type (§4.8).
> - It is a primitive type (§4.2).
> - It is an array type (§10.1) whose element type is reifiable.
> - It is a nested type where, for each type `T` separated by a `.`, `T` itself is reifiable — equivalently, none of the enclosing types in the qualified name is a parameterized type with non-wildcard arguments.

Read that last clause carefully: it isn't only about the outermost type. `Outer<String>.Inner` is non-reifiable even though `Inner` itself carries no type arguments, because the qualifying `Outer<String>` does.

Against the QuizStakes vocabulary, checked one by one:

| Type | Reifiable? | Governing clause |
|---|---|---|
| `int` | Yes | primitive type |
| `Money` | Yes | non-generic class type |
| `LedgerEntry` | Yes | non-generic interface type |
| `List<?>` | Yes | parameterized type, all arguments unbounded wildcards |
| `List` (raw) | Yes | raw type |
| `List<?>[]` | Yes | array of a reifiable element type |
| `Repository<CashEntry>` | No | parameterized type with a concrete, non-wildcard argument |
| `List<Money>` | No | parameterized type with a concrete, non-wildcard argument |
| `T` (a type variable) | No | not covered by any of the six clauses — a type variable is neither primitive, non-generic, wildcard-parameterized, raw, nor an array of a reifiable type |
| `List<? extends LedgerEntry>` | No | wildcard is *bounded*, not unbounded — the clause requires *all* type arguments to be unbounded (`?` alone) |

The last two rows are the ones that trip people who half-remember the rule as "wildcards are reifiable." Only the *unbounded* wildcard qualifies; `List<? extends LedgerEntry>` still carries a bound that erasure would have to discard information about, so JLS 4.7 excludes it. A bare type variable `T` is excluded outright — it has no clause that admits it, which is exactly why none of `new T[n]`, `new T()`, `instanceof List<T>`, or (inside `Reservation<T>`) `o instanceof T` compile.

### Why it exists

The whole reason to name this category at all is that two specific JVM instructions need a reifiable type to operate correctly: `checkcast`/`instanceof` (they compare against a constant-pool class reference, which must denote something the verifier can check structurally at runtime) and array element assignment (every array store executes an implicit `arraystoreck` against the array's own recorded component type — §1c in `arrays/01a-covariance-and-mutability.md` owns that mechanism in full). Both need something concrete to check against. A raw `List`, `Money`, `int`, or `List<?>` supplies that; `Repository<CashEntry>` and `List<Money>` do not, because the JVM would have to somehow check "and specifically holds `CashEntry`s" against an object it has no per-parameterisation identity for — that information was discarded in §1. So `instanceof List<CashEntry>` is rejected at compile time (consequence 4) and `new T[n]` is rejected at compile time (consequence 2) for the identical underlying reason: neither has a reifiable type to check or allocate against.

### The mechanism

There is no bytecode instruction here to disassemble — reifiability is a compile-time classification `javac` consults, not a runtime check with its own instruction. The evidence is the compiler's behavior itself: every rejection quoted in §2 is `javac` refusing to emit code that would need a non-reifiable type checked or allocated at runtime, and every type in the "Yes" column above is exactly the set for which the corresponding operation *is* legal — `o instanceof List<?>` compiles cleanly (unlike `o instanceof List<CashEntry>` in §2's consequence 4) precisely because `List<?>` is reifiable by the second clause.

### Version note

This split has not moved since Java 5; JLS 21 §4.7 states the same six clauses as earlier editions. It is not scheduled to change for reference types either — Project Valhalla's specialised generics target *value classes* getting their own reified, non-erased type parameters, which would sit alongside today's erasure for `Object`-based reference generics, not replace it. What's true in Java 21 is the list above, full stop; do not extrapolate a Valhalla timeline from it. `03e-internals-why-erasure-and-super-type-tokens.md` covers what a fully reified alternative would have cost Java 5's migration story, for readers who want that argument in depth.

**No gotcha beyond the bounded-wildcard trap already called out above.**

> A type is reifiable exactly when JLS 4.7's six clauses admit it — primitive, non-generic, unbounded-wildcard-parameterized, raw, an array of a reifiable type, or a nested type with no parameterized qualifier — and `instanceof`/`checkcast`/array-store all require a reifiable type because those are the only shapes the JVM can check against at runtime.

## Supporting facts

### `javap`'s two-line summary is the whole mental model

The descriptor line (`descriptor: (Ljava/util/UUID;)LLedgerEntry;`) is what the JVM links against, verifies, and dispatches on. The `Signature` attribute (`Signature: #41 // (Ljava/util/UUID;)TT;`) is a string only `java.lang.reflect` parses. Nothing else in the runtime — not the verifier, not `invokevirtual`, not the JIT — ever reads a `Signature` attribute.

> Two records of the same generic information exist per member; only the descriptor is enforced.

### `Class<T>` objects are always raw at the JVM level

`CashEntry.class` and `Repository.class` are `Class` objects with no memory of any type parameter — `Class<Repository>`, not `Class<Repository<CashEntry>>` (that second form isn't even expressible; `Class` only ever takes one type argument matching the raw class). `getClass()` on a `Repository<CashEntry>` and a `Repository<BonusEntry>` both return that same one `Class` object, which is the direct evidence for consequence 1 above.

> `getClass()` always returns the erased, raw `Class` — there is no per-parameterisation `Class` object to get.

## Pitfalls

### "I can check `instanceof List<CashEntry>` if I really need to at runtime"

**Wrong**

```java
import java.util.List;

class InstanceofGeneric {
    boolean isCashList(Object o) {
        return o instanceof List<CashEntry>;
    }
}
```

```
InstanceofGeneric.java:5: error: Object cannot be safely cast to List<CashEntry>
        return o instanceof List<CashEntry>;
               ^
1 error
```

**Right**

```java
import java.util.List;

class InstanceofGeneric {
    boolean isNonEmptyList(Object o) {
        return o instanceof List<?> list && !list.isEmpty();
    }
}
```

Check the raw shape (`List<?>`, reifiable per JLS 4.7) and, if the element type genuinely matters, inspect an actual element with `instanceof CashEntry` after narrowing — there is no way to ask the collection itself what it was declared to hold, because it was never told.

**Why people believe it:** the syntax `List<CashEntry>` type-checks fine as a variable declaration everywhere else in the same file, so it looks like it should type-check here too; nothing about the syntax itself signals that `instanceof` specifically needs a reifiable operand.

### "Two `Repository<T>` instances with different `T` are different runtime classes"

**Wrong**

```java
Repository<CashEntry> cashRepo = new Repository<>();
Repository<BonusEntry> bonusRepo = new Repository<>();
System.out.println(cashRepo.getClass() == bonusRepo.getClass());
```

Output: `true` — not `false` as the belief predicts.

**Right**

```java
class Repository<T extends LedgerEntry> {
    // one class file, one runtime Class object, regardless of T
}
```

Treat "same generic declaration → same runtime class, always" as the default assumption, and reach for a `Class<T>` token (`02a-type-tokens-and-generic-reflection.md`) the moment code genuinely needs to distinguish parameterisations at runtime — erasure will never do that distinguishing for you.

**Why people believe it:** in most other object-oriented reasoning, "different declared type → different runtime behavior" holds (that's what overriding is for), so it's a natural but wrong extrapolation onto type parameters, which are erased before the class file even exists.

### "The compiler generates the `checkcast` inside the generic method that returns `T`"

**Wrong**

Believing `Repository.find`'s bytecode contains a `checkcast CashEntry` because it's declared to return `T` for a `Repository<CashEntry>`.

```
T find(java.util.UUID);
  descriptor: (Ljava/util/UUID;)LLedgerEntry;
  Code:
     0: aload_0
     1: getfield      #10   // Field byId:Ljava/util/Map;
     4: aload_1
     5: invokeinterface #28,  2   // InterfaceMethod java/util/Map.get:(Ljava/lang/Object;)Ljava/lang/Object;
    10: checkcast     #17   // class LedgerEntry
    13: areturn
```

The `checkcast` inside `find` is against `LedgerEntry` — the erased bound — never against `CashEntry`. `Repository.find` has no idea it is ever going to be called through a `Repository<CashEntry>` reference.

**Right**

```
static CashEntry fetch(Repository<CashEntry>, java.util.UUID);
  descriptor: (LRepository;Ljava/util/UUID;)LCashEntry;
  Code:
     2: invokevirtual #7   // Method Repository.find:(Ljava/util/UUID;)LLedgerEntry;
     5: checkcast     #13  // class CashEntry
```

The narrowing `checkcast` against `CashEntry` is emitted in `Caller.fetch`, at the call site where the erased `LedgerEntry` result gets assigned to a `CashEntry` local — not inside `Repository` or `AbstractStore` or `CashEntryStore` anywhere.

**Why people believe it:** the generic declaration `T find(UUID id)` reads as if `find` "knows" what `T` is for a given caller, so it's natural to assume the type-narrowing work happens inside the method that looks generic, rather than realizing the callee only ever sees the erased bound and every caller does its own narrowing independently.

## Cheat sheet

| Fact | Value |
|---|---|
| Spec for erasure | JLS 21 §4.6 |
| Spec for reifiable types | JLS 21 §4.7 |
| Erasure of a parameterized type | the raw type — `Repository<CashEntry>` → `Repository` |
| Erasure of a type variable | erasure of its leftmost bound — unbounded `T` → `Object` |
| Erasure of an array type | array of the erased element type |
| Where the pre-erasure signature survives | `Signature` attribute, string in the constant pool, reflection-only |
| Who inserts narrowing `checkcast`s | the caller, at the point of narrowing — never the generic method itself |
| Reifiable: primitives | yes |
| Reifiable: non-generic class/interface | yes |
| Reifiable: unbounded-wildcard parameterized type (`List<?>`) | yes |
| Reifiable: raw type | yes |
| Reifiable: array of a reifiable element | yes |
| Reifiable: bounded wildcard (`List<? extends LedgerEntry>`) | no |
| Reifiable: concrete parameterized type (`List<Money>`) | no |
| Reifiable: bare type variable (`T`) | no |
| `javac` diagnostic for `new T[n]` | `generic array creation` |
| `javac` diagnostic for `new T()` | `unexpected type … found: type parameter T` |
| `javac` diagnostic for `instanceof List<CashEntry>` | `Object cannot be safely cast to List<CashEntry>` |
| `javac` diagnostic for clashing overloads | `have the same erasure` |
| Static field scope across `T` | one copy, shared by every parameterisation |

## Self-test

**Q1.** What exactly does erasure do to `Repository<T extends LedgerEntry>`'s `T find(UUID id)` method, and where does the pre-erasure information go?

<details><summary>Answer</summary>

`javac` type-checks the full generic declaration, then emits a descriptor with every occurrence of `T` replaced by the erasure of `T`'s leftmost bound — here `LedgerEntry`, since that's `T`'s only bound. The runtime descriptor becomes `(Ljava/util/UUID;)LLedgerEntry;`. The original generic form, `(Ljava/util/UUID;)TT;`, is preserved only as a string in a `Signature` attribute, which nothing in the JVM's verification or dispatch path reads — its only consumer is `java.lang.reflect`, via calls like `Method.getGenericReturnType()`.

</details>

**Q2.** A caller does `CashEntry entry = repo.find(id)` where `repo` is a `Repository<CashEntry>`. Whose bytecode contains the `checkcast` that makes this safe, and why there rather than inside `find`?

<details><summary>Answer</summary>

The caller's bytecode. `Repository.find` returns the erased type `LedgerEntry` — it has no knowledge of `CashEntry` at all, since that information was erased out of its own descriptor. The narrowing from `LedgerEntry` down to `CashEntry` happens at the assignment in the caller, so `javac` inserts a `checkcast CashEntry` there, immediately after the `invokevirtual` to `find`. Every place a caller narrows an erased return value back to something specific gets its own independent `checkcast`.

</details>

**Q3.** Why does `new T[n]` fail to compile inside a generic class, when `new T()` fails with a different message?

<details><summary>Answer</summary>

`new T[n]` fails with "generic array creation" because array allocation needs a concrete component type baked into the `anewarray` instruction's constant-pool reference, and at the point of allocation `javac` cannot know which parameterisation's array the caller actually wants — allowing it would let a `CashEntry[]`-shaped array silently get treated as `BonusEntry[]` somewhere downstream. `new T()` fails with "unexpected type … found: type parameter T" for a more basic reason: at that point in the grammar `new` expects a class it can allocate and invoke a constructor on, and a type variable is not a class — even after erasure it would resolve to `LedgerEntry`, an interface with no constructor to call at all.

</details>

**Q4.** Is `List<?>` reifiable? Is `List<? extends LedgerEntry>`? Cite the JLS clause for each.

<details><summary>Answer</summary>

`List<?>` is reifiable — JLS 4.7's second clause admits a parameterized type in which all type arguments are unbounded wildcards, and `?` alone is unbounded. `List<? extends LedgerEntry>` is not reifiable, because that wildcard is bounded — the clause specifically requires *unbounded* wildcards, and a bound still carries information erasure would have to discard, so the JVM would have nothing concrete to check an object against at runtime.

</details>

**Q5.** Two variables, `Repository<CashEntry> a` and `Repository<BonusEntry> b`, both freshly constructed. What does `a.getClass() == b.getClass()` evaluate to, and why?

<details><summary>Answer</summary>

`true`. There is exactly one `Repository.class` at runtime — erasure means the class file that gets loaded and linked has no per-parameterisation identity, so every `Repository` reference, regardless of what type argument it was declared with, points at the same `Class` object. This is the direct root cause of consequence 1 in the six-consequence list: one runtime class per generic declaration, full stop.

</details>

**Q6.** Why does declaring `void post(List<CashEntry>)` and `void post(List<BonusEntry>)` in the same class fail to compile, and what's the exact diagnostic text to recognise?

<details><summary>Answer</summary>

Both signatures erase to the identical descriptor `post(Ljava/util/List;)V`, because `List<CashEntry>` and `List<BonusEntry>` both erase to raw `List`. The JVM's method table is keyed on name plus erased descriptor, so these two methods would be indistinguishable the moment erasure ran — `javac` refuses before it gets that far. The diagnostic is `name clash: post(List<BonusEntry>) and post(List<CashEntry>) have the same erasure`; the phrase "have the same erasure" is the one to recognise in a build log.

</details>

**Q7.** A `Counter<T>` has a `static int postings` field. One `Counter<CashEntry>` and one `Counter<BonusEntry>` each call `post` once. What does `Counter.postings` read afterward, and why?

<details><summary>Answer</summary>

`2`. `static` members belong to the one class `Counter`, not to any parameterisation of it — erasure means there is no such thing as a `Counter<CashEntry>`-specific copy of `postings` to keep separate from `Counter<BonusEntry>`'s. Both calls incremented the same shared field. This is exactly why a generic class cannot use its own type parameter in a static context: there's no per-parameterisation `T` for a static member to refer to.

</details>

**Q8.** Has type erasure changed at any point since its introduction, and does Project Valhalla remove it?

<details><summary>Answer</summary>

No, the mechanism JLS 4.6 describes has been the same since Java 5 in 2004, and JLS 21 states the identical rule. Project Valhalla does not un-erase reference-type generics; its specialised generics target value classes getting their own reified type parameters, which would exist alongside today's erasure for `Object`-based reference generics rather than replacing it. Nothing about erasure for `List<CashEntry>`-style reference generics is scheduled to change in Java 21 or its near successors.

</details>

## Open questions

None.

---

**Leaves covered:** 1.21.7, 1.21.8, 1.21.17 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 514
