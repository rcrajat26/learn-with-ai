# 03 Java Core — Raw types, heap pollution, and unchecked-warning discipline — BASICS (§1.21, 1.21.15, 1.21.16, 1.21.18, 1.21.19)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Variance and wildcards](01b-variance-and-wildcards.md) · Next: [Recursive bounds and heterogeneous containers](01d-recursive-bounds-and-heterogeneous-containers.md)

This file covers the raw type as a total type-checking off switch (not "a generic type with the brackets left off"), the three-way distinction between raw `List`, `List<Object>` and `List<?>`, generic varargs and `@SafeVarargs` at the level needed to answer the interview question, and the discipline around `@SuppressWarnings("unchecked")`. It hands off erasure itself and the reifiable/non-reifiable split to `01a-erasure-and-its-consequences.md`, invariance and wildcards to `01b-variance-and-wildcards.md`, the typesafe heterogeneous container to `01d-recursive-bounds-and-heterogeneous-containers.md`, the exact four-step heap-pollution sequence and its bytecode to `03c-internals-heap-pollution-and-safevarargs.md`, `(T[]) new Object[n]` versus `Array.newInstance` to `02b-generic-arrays-and-self-types.md`, and the historical reason raw types exist at all to `02d-migration-and-reading-signatures.md`.

## 1. Raw types: the type checker's off switch, not a shorthand (1.21.15)

The instinctive mental model is that `List` is just `List<Object>` with the angle brackets omitted — a lazy shorthand that still gets checked, just less precisely. That model is wrong in a way that matters: a raw type is not "generics with weaker checking", it is **generics with the checking switched off for the entire type**, including for members that never mention the class's own type parameter. Writing `Repository raw = new Repository()` does not mean "a `Repository` of unknown element type" the way `Repository<?>` does — it means "treat `Repository` as it existed before generics were retrofitted onto the language in Java 5", and every method you call through that reference is typed as if erasure had already happened to its declaration, not just to the class's type variable.

### Why it exists

Generics arrived in Java 5 on top of a language and a standard library that had shipped for a decade without them. Binary compatibility meant a `.class` file compiled against `List` in 1999 had to keep working when loaded next to code compiled against `List<String>` in 2004, and source compatibility meant fifteen years of `List`-typed fields, parameters and return types across every enterprise codebase had to keep compiling without a rewrite. The raw type is that compatibility bridge: JLS §4.8 defines it precisely so that legacy source and legacy bytecode both keep working, at the cost of the type checker doing nothing for you inside that reference. `02d-migration-and-reading-signatures.md` owns the full migration-compatibility argument and the erasure history behind it; the one sentence that matters here is that raw types are a deliberate, permanent escape hatch for pre-generics interop, not an accident nobody got around to removing.

### The mechanism

JLS 21 §4.8 states it as a rule about *members*, not about the type parameter alone: "The type of a constructor, instance method, or non-static field of a raw type `C` that is not inherited from its superclasses or superinterfaces is the raw type that corresponds to the erasure of its type in the generic declaration corresponding to `C`." Read that literally: it does not say "the type parameter is replaced by its bound and everything else is left alone." It says the type of the *member* is the erasure of its type in the generic declaration — full stop. A generic method declared inside a generic class, with its own, unrelated type variable, is still a member of that class, so it is still erased when you reach it through a raw reference.

**Claim 1 — a raw reference lets a `BonusEntry` into a `List<CashEntry>`, with only a warning, and the failure surfaces at an unrelated read site.** Work it through: `pollute` below takes a raw `List` and a `BonusEntry`. Because the parameter is raw, `List.add(E)` is typed as `add(Object)` inside that method body — there is no `E` left to check `bonus` against, so the call type-checks. The caller passes a `List<CashEntry>` where a raw `List` is expected; that direction is always legal, because a parameterized type is assignable to its own raw type (JLS §4.10.2) — no cast, no warning at that assignment. The warning appears where the *unchecked write actually happens*, inside `pollute`. No diagram: the manifest assigns this section none; the compiler output above is the evidence.

```java
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) {}
interface LedgerEntry { UUID id(); Money amount(); }
record CashEntry(UUID id, Money amount) implements LedgerEntry {}
record BonusEntry(UUID id, Money amount) implements LedgerEntry {}

public class RawInject {
    static void pollute(List cashEntries, BonusEntry bonus) {
        cashEntries.add(bonus);
    }

    public static void main(String[] args) {
        Currency gbp = Currency.getInstance("GBP");
        List<CashEntry> cashEntries = new ArrayList<>();
        cashEntries.add(new CashEntry(UUID.randomUUID(), new Money(BigDecimal.TEN, gbp)));

        BonusEntry bonus = new BonusEntry(UUID.randomUUID(), new Money(BigDecimal.ONE, gbp));
        pollute(cashEntries, bonus);

        for (CashEntry entry : cashEntries) {
            System.out.println(entry.amount());
        }
    }
}
```

Compiled on JDK 21.0.7 with `javac -Xlint:all RawInject.java`, the real diagnostics are:

```
RawInject.java:13: warning: [rawtypes] found raw type: List
    static void pollute(List cashEntries, BonusEntry bonus) {
                        ^
  missing type arguments for generic class List<E>
  where E is a type-variable:
    E extends Object declared in interface List
RawInject.java:14: warning: [unchecked] unchecked call to add(E) as a member of the raw type List
        cashEntries.add(bonus);
                       ^
  where E is a type-variable:
    E extends Object declared in interface List
2 warnings
```

Two warnings, zero errors — the file compiles clean. Running it with `java RawInject` on the same JDK 21.0.7 build produces:

```
Money[amount=10, currency=GBP]
Exception in thread "main" java.lang.ClassCastException: class BonusEntry cannot be cast to class CashEntry (BonusEntry and CashEntry are in unnamed module of loader 'app')
	at RawInject.main(RawInject.java:25)
```

The first list element (a genuine `CashEntry`) prints fine. The exception fires at line 25 — the `for (CashEntry entry : cashEntries)` loop — not at line 14 where the bad element was inserted. The enhanced-for loop desugars to `cashEntries.iterator().next()` followed by an implicit `checkcast CashEntry`, inserted by the compiler at every read site because `List<CashEntry>` erases to `List` at the bytecode level and the JVM has no other way to enforce the element type. The write silently succeeded; the read many lines and possibly many milliseconds later is where the lie gets caught. `03-internals-erasure.md` owns the general `checkcast`-insertion mechanism; this is it happening at a raw-type boundary specifically.

**Claim 2 — the unrelated-methods claim: using a raw type erases the generic signatures of members that don't mention the class's own type parameter.** This is the genuinely non-obvious half. Build `Repository<T extends LedgerEntry>` with an *instance* method `<K> Map<K, Money> totalsBy(K key, T entry)` — a method with its own type variable `K`, independent of `T`. Naive intuition says: `T` gets erased because the raw type has no type argument for it, but `K` is still inferred per-call from the argument you pass, so the return type should still be `Map<String, Money>` when you pass a `String` key. JLS §4.8 says otherwise — the *member's* type is the erasure of its type in the generic declaration, and that includes methods whose type variables are locally scoped to the method rather than to the class. Reached through a raw `Repository`, `totalsBy` is typed as the erasure `Map totalsBy(Object, LedgerEntry)`, not `<K> Map<K, Money> totalsBy(K, LedgerEntry)`. `K` is gone; there is nothing left to infer.

```java
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) {}
interface LedgerEntry { UUID id(); Money amount(); }
record CashEntry(UUID id, Money amount) implements LedgerEntry {}

class Repository<T extends LedgerEntry> {
    <K> Map<K, Money> totalsBy(K key, T entry) {
        Map<K, Money> result = new HashMap<>();
        result.put(key, entry.amount());
        return result;
    }
}

public class RawErasesUnrelated {
    public static void main(String[] args) {
        Repository raw = new Repository();
        CashEntry entry = new CashEntry(UUID.randomUUID(), new Money(BigDecimal.TEN, Currency.getInstance("GBP")));
        Money total = raw.totalsBy("KEY", entry).get("KEY");
        System.out.println(total);
    }
}
```

Compiled on JDK 21.0.7 with `javac -Xlint:all RawErasesUnrelated.java`:

```
RawErasesUnrelated.java:21: warning: [rawtypes] found raw type: Repository
        Repository raw = new Repository();
        ^
  missing type arguments for generic class Repository<T>
  where T is a type-variable:
    T extends LedgerEntry declared in class Repository
RawErasesUnrelated.java:21: warning: [rawtypes] found raw type: Repository
        Repository raw = new Repository();
                             ^
  missing type arguments for generic class Repository<T>
  where T is a type-variable:
    T extends LedgerEntry declared in class Repository
RawErasesUnrelated.java:23: warning: [unchecked] unchecked call to <K>totalsBy(K,T) as a member of the raw type Repository
        Money total = raw.totalsBy("KEY", entry).get("KEY");
                                  ^
  where K,T are type-variables:
    K extends Object declared in method <K>totalsBy(K,T)
    T extends LedgerEntry declared in class Repository
RawErasesUnrelated.java:23: error: incompatible types: Object cannot be converted to Money
        Money total = raw.totalsBy("KEY", entry).get("KEY");
                                                    ^
1 error
3 warnings
```

`totalsBy("KEY", entry)` returns raw `Map`, so `.get("KEY")` returns `Object`, not `Money` — a hard compile **error**, not a warning, because unlike the `add` case above there is no unchecked-conversion path that lets an `Object` silently stand in for `Money` at an assignment with no cast at all. `K` never existed at this call site as far as the compiler is concerned; it was erased the moment the reference became raw, even though `K` has nothing to do with `Repository`'s own `T`. That is the trap version of this leaf, expanded fully in the Pitfalls section below.

**Pitfall:** believing a raw type only turns off checking for the class's own declared type parameter, so an unrelated generic method keeps its precise signature. It does not — JLS §4.8 erases every member, and the fix is to never use the raw type at all: parameterize the reference (`Repository<CashEntry>`) or, if the element type is genuinely unknown, use the wildcard `Repository<?>` from §2 below, which keeps unrelated generic methods fully checked.

### Gotcha

The raw-type warning at the *declaration* site (`found raw type: Repository`) and the unchecked warning at the *call* site (`unchecked call to <K>totalsBy`) are two separate diagnostics for two separate risks, and suppressing one does not suppress the other — a common mistake is to `@SuppressWarnings("rawtypes")` on a field declaration and assume every downstream unchecked call through that field is now silent, when in fact each call site keeps emitting its own `[unchecked]` warning independently.

> A raw type is JLS §4.8's compatibility bridge to pre-generics Java: it erases the type of every member of the class — including generic methods whose type variables have nothing to do with the class's own — not merely the class's declared type parameter.

## 2. Raw `List` vs `List<Object>` vs `List<?>` — the three-way distinction (1.21.16)

Three declarations that look like they do roughly the same job — "hold anything" — but that differ on every axis that matters: what you may assign into the variable, what you may `add`, what a read gives back, and whether the compiler is even watching.

| | raw `List` | `List<Object>` | `List<?>` |
|---|---|---|---|
| What you may assign in | any `List` or `List<T>` for any `T` | only `List<Object>` itself | any `List<T>` for any `T`, including `List<Object>` |
| What you may `add` | anything — no check | anything assignable to `Object` — fully writable | nothing except `null` — the compiler cannot prove any concrete type is safe |
| What a read gives back | `Object`, with **no compile-time warning** at the read | `Object`, precisely and safely typed | `Object`, precisely and safely typed |
| Type checker on for this reference | **off** — every operation is unchecked | on — full generic checking | on — full generic checking |

### Why it exists

Before wildcards existed as a first-class idea (they landed with generics in Java 5, JLS §4.5.1), the only way to write "a list of I-don't-care-what, but still type-checked" was to leave the type raw and accept unchecked everything. Wildcards gave the language a way to say "unknown but type-safe" without falling back to "unknown and unchecked." `List<Object>` solves a different problem again — "a list that is genuinely allowed to hold any object, and I want the compiler enforcing that at every `add`." All three read as "holds anything" in casual description, which is exactly why interviewers ask the distinction: it separates people who have written the words `List<?>` from people who understand what capture conversion is protecting them from. `01b-variance-and-wildcards.md` owns wildcards, PECS and capture conversion in full; this section only needs the three-way comparison.

### The mechanism

`List<?>` is shorthand for `List<? extends Object>`, and the compiler treats the `?` as an unknown-but-fixed type — call it `CAP#1` — for the duration of the expression. Because the compiler cannot prove that whatever `CAP#1` turns out to be is compatible with any concrete type you might pass to `add`, every `add(E)` call except `add(null)` is rejected at compile time; `null` is the one value assignable to every reference type, `CAP#1` included. `List<Object>` carries a real, known type argument, so `add(Object)` is fully open — anything is an `Object`. Raw `List` has no type argument to reason about at all: `add` is typed as `add(Object)` at the erased signature level exactly like `List<Object>`'s `add`, but with none of the surrounding checks — assigning a `List<String>` into a raw `List` variable, then adding a `CashEntry` to it, compiles with only a warning, whereas the same sequence through `List<Object>` never type-checks in the first place because you cannot assign a `List<String>` to a `List<Object>` variable (that is invariance, owned by `01b`).

No diagram: the manifest assigns this section none; the table above and the code below are the evidence.

```java
import java.util.ArrayList;
import java.util.List;
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) {}

public class ThreeWayDistinction {
    static void demonstrate() {
        List<Money> stakes = new ArrayList<>();
        stakes.add(new Money(BigDecimal.TEN, Currency.getInstance("GBP")));

        List<?> unknownElement = stakes;
        unknownElement.add(null);

        List<Object> anyObject = new ArrayList<>();
        anyObject.add(new Money(BigDecimal.ONE, Currency.getInstance("GBP")));
        anyObject.add("not even money, and the compiler lets it in");

        List raw = stakes;
        raw.add("this compiles with a warning and blows up at the next typed read");
    }
}
```

`unknownElement.add(null)` is the only `add` the wildcard reference accepts; both `anyObject.add` calls in the listing above compile cleanly because `List<Object>` accepts any reference type at `add`, and both are safe because nobody downstream is relying on `anyObject` holding only `Money`; the final `raw.add` call compiles with the same `[unchecked]` warning shape as §1's `RawInject.pollute`, and the failure — if `stakes` is later read as `List<Money>` — surfaces at that read, not here.

**Interview:** "what's the difference between `List<Object>`, `List<?>` and raw `List`?" — the one-line answer is: `List<Object>` is fully type-checked and fully writable but only `List<Object>` itself is assignable to it; `List<?>` is fully type-checked and effectively read-only (only `null` is writable) because the element type is unknown-but-fixed; raw `List` accepts any assignment and any `add` because the type checker is switched off entirely for that reference.

### Gotcha

`List<?>` being "read-only-ish" is about what you can *write*, not about mutation in general — `list.clear()`, `list.remove(int index)` and `list.removeIf(Predicate<? super Object> filter)`-style bulk-remove operations that don't require inserting a new element of the unknown type all still compile through a `List<?>` reference, so "read-only" is a common but imprecise way to describe it; "write-nothing-except-null" is the precise statement.

> Raw `List`, `List<Object>` and `List<?>` all read as "holds anything", but only one of the three has the type checker switched off — the other two differ in whether the element type is a concrete, writable `Object` or an unknown-but-fixed capture that only `null` satisfies.

## 3. Heap pollution, generic varargs, and `@SafeVarargs` (1.21.18)

The picture: a varargs parameter is sugar for an array parameter, and an array of a non-reifiable component type is a thing the JVM cannot honestly represent — there is no bytecode instruction for "array of `List<Money>`", only "array of `List`" — yet the language lets you write the parameter anyway, because forbidding it would make an enormous swath of existing generic-varargs APIs (`List.of`, `Arrays.asList`) impossible to declare. The compiler's way of squaring that circle is to build the array at the call site as a raw `List[]`, let you treat it as `List<Money>[]` inside the method body, and warn you twice that it is trusting you not to break the illusion.

### Why it exists

Varargs (Java 5) and generics (Java 5) shipped in the same release and were never designed to compose cleanly. A varargs parameter, written as a type followed by a varargs ellipsis and a name, is exactly a parameter of the corresponding array type, decided by array creation, and arrays have always tracked their component type at runtime (`ArrayStoreException` depends on this — owned by `../arrays/01a-covariance-and-mutability.md`). Generics, by contrast, erase their type arguments, so `List<Money>` and `List<String>` are indistinguishable at runtime — `List<Money>` is a non-reifiable type. A varargs parameter of a non-reifiable type therefore asks for an array whose component type cannot exist honestly at runtime. The alternative — banning generic varargs outright — would have broken `Arrays.asList`, `List.of`, `Collections.addAll` and every fluent generic builder API; the language chose to allow it with a warning instead of a compile error, and `@SafeVarargs` (Java 7) is the annotation that lets an API author assert the warning is a false alarm for a specific method.

### The mechanism

Take a method that logs a `FundsLedger` payout run's batches, each batch a `List<Money>` gathered from `PaymentRun` entries, declared with a varargs parameter. **Gate note:** this file may not contain a literal varargs ellipsis, so the listing below shows the parameter in its already-erased array form, `List<Money>[] batches`; the real source this was compiled from spells the same parameter with a varargs ellipsis after `List<Money>`, and the two forms are the same parameter — varargs is array-parameter sugar, nothing more.

```java
import java.util.List;
import java.util.ArrayList;
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) {}

public class PayoutBatchesNoAnnotation {
    static void logBatches(List<Money>[] batches) {
        for (List<Money> batch : batches) {
            System.out.println(batch.size());
        }
    }

    public static void main(String[] args) {
        Currency gbp = Currency.getInstance("GBP");
        List<Money> first = new ArrayList<>();
        first.add(new Money(BigDecimal.TEN, gbp));
        List<Money> second = new ArrayList<>();
        second.add(new Money(BigDecimal.ONE, gbp));
        logBatches(first, second);
    }
}
```

Compiled from the real varargs source — line 9 declares `logBatches` with a `List<Money>` varargs parameter named `batches`, line 21 calls `logBatches(first, second)` — on JDK 21.0.7 with `javac -Xlint:unchecked`, the two real diagnostics are (the declaration line below is reproduced in its erased array form, per this file's no-ellipsis constraint):

```
PayoutBatchesNoAnnotation.java:9: warning: [unchecked] Possible heap pollution from parameterized vararg type List<Money>
    static void logBatches(List<Money>[] batches) {
                                          ^
PayoutBatchesNoAnnotation.java:21: warning: [unchecked] unchecked generic array creation for varargs parameter of type List<Money>[]
        logBatches(first, second);
                  ^
2 warnings
```

The first — "Possible heap pollution from parameterized vararg type" — is the **declaration**-site warning: the method's own signature is admitting the risk exists. The second — "unchecked generic array creation for varargs parameter" — is the **call**-site warning: the specific array `javac` builds for *this* invocation (a raw `List[]` of length 2, populated with `first` and `second`) is being trusted to hold only `List<Money>` even though its declared component type at the bytecode level is plain `List`. Both are `[unchecked]` category, so `-Xlint:unchecked` alone surfaces both; `javac` with no flags at all only prints two summary lines — `Note: PayoutBatchesNoAnnotation.java uses unchecked or unsafe operations.` and `Note: Recompile with -Xlint:unchecked for details.` — and exits 0, which is why these warnings are so easy to never see in a default build.

The rule `@SafeVarargs` encodes is an assertion **you** make, not something `javac` verifies by inspecting the method body. It is honest — safe to write without lying to the next reader — only when all three hold:

1. The method never **stores** anything into the varargs array parameter (no `batches[0] = someList`).
2. The method never lets a **reference** to that array escape to code that doesn't already know its true erased type (no `return batches;`, no passing it to an unconstrained `Object[]`-accepting method).
3. The method **cannot be overridden**, because an override could break both promises above without the annotation being re-checked — so the method must be `static`, `final`, `private`, or a constructor.

`logBatches` above only iterates and reads — it satisfies all three, so annotating it is honest:

```java
import java.util.List;
import java.util.ArrayList;
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) {}

public class PayoutBatches {
    @SafeVarargs
    static void logBatches(List<Money>[] batches) {
        for (List<Money> batch : batches) {
            System.out.println(batch.size());
        }
    }

    public static void main(String[] args) {
        Currency gbp = Currency.getInstance("GBP");
        List<Money> first = new ArrayList<>();
        first.add(new Money(BigDecimal.TEN, gbp));
        List<Money> second = new ArrayList<>();
        second.add(new Money(BigDecimal.ONE, gbp));
        logBatches(first, second);
    }
}
```

(Again, the real compiled source spells the parameter with a varargs ellipsis; the array form above is the same parameter, shown to satisfy this file's no-ellipsis constraint.) Compiled on JDK 21.0.7 with `javac -Xlint:all PayoutBatches.java`: zero warnings, zero errors, clean exit — `@SafeVarargs` suppresses both the declaration-site and the call-site warning together, because it tells `javac` the whole risk the two warnings describe has been manually verified.

**Version note — the `private` boundary.** `@SafeVarargs` was added in Java 7 and, until Java 9 (JEP 213 rolled the change in as part of that release's javac work), was legal only on `static` and `final` methods and constructors — condition 3 above was enforced as "must be `static`, `final`, or a constructor", with no `private` option, even though a `private` instance method is exactly as un-overridable as a `final` one. Java 9 added `private` instance methods to the allowed set. `[PROVE]` this boundary directly: compile the same `private` instance `@SafeVarargs` method under `--release 8` and `--release 21` on the one JDK 21.0.7 toolchain.

```java
import java.util.List;

public class SafeVarargsBoundary {
    @SafeVarargs
    private void logBatches(List<String>[] batches) {
        for (List<String> batch : batches) {
            System.out.println(batch.size());
        }
    }
}
```

(Real source uses a `List<String>` varargs parameter named `batches` on line 5; shown here in array form for the same reason as above.) `javac --release 8 SafeVarargsBoundary.java` on JDK 21.0.7:

```
SafeVarargsBoundary.java:5: error: Invalid SafeVarargs annotation. Instance method logBatches(List<String>[]) is not final.
    private void logBatches(List<String>[] batches) {
                 ^
1 error
```

`javac --release 21 SafeVarargsBoundary.java` on the same JDK: no output, exit 0 — clean compile. Same source, same JDK binary, only the `--release` target changed, and the `private`-instance boundary flips exactly where JEP-tracked history says it should.

No diagram: the manifest assigns this section none; `03c-internals-heap-pollution-and-safevarargs.md` carries D-106, the diagram for the exact four-step sequence that turns a `String` into a polluted `List<Money>` slot and the bytecode that produces it — that sequence and its diagram belong there, not here. `../arrays/01d-varargs-and-choosing-arrays.md` owns varargs as arrays generally, including the per-call array allocation cost and the overload-resolution ambiguity between an `Object` array parameter and an `Object` varargs parameter; read it first if the array-allocation half of this mechanism isn't already solid, because `@SafeVarargs` only makes sense once you know the compiler is silently allocating an array on every call.

**Pitfall:** believing `@SafeVarargs` is checked by the compiler the way `@Override` is, so slapping it on any method that "feels safe" is harmless. It is not checked against the method body at all — it only checks the *legality* conditions (is the method `static`/`final`/`private`/a constructor), never whether the body actually avoids storing into or leaking the array. The fix is to manually verify the three conditions above before adding the annotation, every time, because a wrong `@SafeVarargs` compiles cleanly and silently turns a real heap-pollution warning into silence.

**Pitfall:** believing `@SafeVarargs` has always been legal on any non-overridable method, including a `private` instance method, since Java 7. Until Java 9 it was restricted to `static`, `final`, and constructors; a `private` instance method — equally non-overridable — was rejected with exactly the "is not final" error reproduced above. The fix, when reading pre-Java-9 code or answering a version-sensitive interview question, is to say "Java 7 introduced it for `static`/`final`/constructors; Java 9 extended it to `private` instance methods", not "it always worked on anything that can't be overridden."

### Gotcha

The declaration-site warning and the call-site warning are independent per call: annotating the declaration with `@SafeVarargs` suppresses the warning at every call site automatically, but if the *caller* itself has a generic-varargs call nested inside another generic-varargs call, each layer is judged separately — annotating the outer method does nothing for a genuinely unsafe inner one.

> `@SafeVarargs` is a compiler-enforced *legality* check (the method must be non-overridable) wrapped around a human-verified *safety* promise (never store into, never leak, the varargs array) — javac checks the first half only and trusts you completely on the second.

## Supporting facts

### `@SuppressWarnings("unchecked")` discipline (1.21.19)

`@SuppressWarnings("unchecked")` should sit on the narrowest possible scope — a single local variable declaration — never on a method and never on a class. The reason is failure containment: a method-level suppression silences every unchecked operation in that method's entire body, including one a different engineer adds three years later that has nothing to do with the original, verified-safe cast; a variable-level suppression silences exactly the one line it sits on, so anything new stays visible. The idiom that forces the narrow scope, taken almost verbatim from how `ArrayList` itself backs a generic array behind `Object[]` internally:

```java
import java.util.UUID;
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) {}
interface LedgerEntry { UUID id(); Money amount(); }

class FixedCapacityStakeBuffer<E extends LedgerEntry> {
    private final Object[] elements;
    private int size;

    FixedCapacityStakeBuffer(int capacity) {
        this.elements = new Object[capacity];
    }

    void push(E entry) {
        elements[size++] = entry;
    }

    E pop() {
        // SAFETY: every element in this array was inserted by push(E), which
        // only ever accepts E, so the cast back to E cannot fail at runtime —
        // the array's true element type is erased to Object, not lied about.
        @SuppressWarnings("unchecked")
        E entry = (E) elements[--size];
        return entry;
    }
}
```

The `@SuppressWarnings` sits on the local variable `entry`, not on `pop()`. If a second unchecked cast were added to `pop()` later — say, casting an unrelated field — it would still warn, because the suppression only covers the one declaration it annotates. Cite this by title: *Effective Java*, **Item 27: *Eliminate unchecked warnings*** — the item-number mapping is on this project's standing unverified list, so the title is the load-bearing citation, not the number.

## Pitfalls

### "A raw type is just a generic type with the type arguments left off, so the checker still watches what goes in"

**Wrong**

```java
static void pollute(List cashEntries, BonusEntry bonus) {
    cashEntries.add(bonus);
}
```

Compiling this with `javac -Xlint:all` on JDK 21.0.7 gives two warnings — not two errors, not zero:

```
RawInject.java:13: warning: [rawtypes] found raw type: List
RawInject.java:14: warning: [unchecked] unchecked call to add(E) as a member of the raw type List
2 warnings
```

The file compiles clean and runs; a `BonusEntry` lands inside what the caller believes is a `List<CashEntry>`, and the mismatch only surfaces later, as a `ClassCastException` at the read site (`RawInject.java:25` in the walk-through above), not here.

**Right**

```java
static void pollute(List<CashEntry> cashEntries, BonusEntry bonus) {
    cashEntries.add(bonus);
}
```

This does not compile at all: `add(BonusEntry)` is not a member of `add(CashEntry)`'s overload set once the list is properly parameterized, so `javac` rejects the call outright with `incompatible types: BonusEntry cannot be converted to CashEntry` — the exact bug, caught at the exact line that causes it, instead of three method calls and one collection traversal downstream.

**Why people believe it:** the raw type still shows the method name `add` and still takes an argument, so it *looks* like the same generic method with weaker inference, not a completely different, unchecked overload; nothing in the syntax signals that the entire member has silently reverted to its pre-Java-5 erasure.

### "A raw type only erases the class's own type parameter — a generic method with its own type variable stays fully checked"

**Wrong**

```java
Repository raw = new Repository();
Money total = raw.totalsBy("KEY", entry).get("KEY");
```

`totalsBy` is declared `<K> Map<K, Money> totalsBy(K key, T entry)` — `K` is the method's own type variable, unrelated to `Repository<T>`'s `T`. Compiling on JDK 21.0.7:

```
RawErasesUnrelated.java:23: error: incompatible types: Object cannot be converted to Money
```

`K` never survives the raw reference: `totalsBy` is typed as `Map totalsBy(Object, LedgerEntry)`, so `.get("KEY")` returns `Object`, and assigning that to `Money` with no cast is a hard error, not a warning.

**Right**

```java
Repository<CashEntry> repository = new Repository<>();
Money total = repository.totalsBy("KEY", entry).get("KEY");
```

Parameterizing the reference restores full inference for `totalsBy`'s own `K`: the compiler infers `K = String` from the `"KEY"` argument, returns `Map<String, Money>`, and `.get("KEY")` correctly yields `Money` with no cast needed.

**Why people believe it:** the mental shortcut "raw erases the class's type parameter" is half the JLS rule and sounds complete — nobody reads a generic method's own type variable as also being "the class's", so it feels exempt, when JLS §4.8 erases the type of the *member*, and a generic method is a member regardless of whose type variable it declares.

### "`List<Object>` and `List<?>` both mean 'holds anything', so they're interchangeable"

**Wrong**

```java
List<?> unknownElement = stakes;
unknownElement.add(new Money(BigDecimal.TEN, Currency.getInstance("GBP")));
```

This does not compile: `javac` reports `incompatible types: Money cannot be converted to CAP#1` (or the equivalent "no suitable method found for add(Money)" depending on diagnostic verbosity) — `List<?>`'s captured element type is unknown-but-fixed, and the compiler cannot prove a `Money` matches it, even though `stakes` is in fact a `List<Money>`.

**Right**

```java
List<Object> anyObject = new ArrayList<>();
anyObject.add(new Money(BigDecimal.TEN, Currency.getInstance("GBP")));
anyObject.add("also legal — anyObject's element type really is Object");
```

`List<Object>` has a concrete, known type argument, so any reference type is assignable to `Object` and every `add` compiles. If the wildcard version needs to accept a specific new element, capture it through a private helper method with its own type variable (the wildcard-capture idiom, owned by `02-in-anger.md`) instead of reaching for `List<Object>` and losing the original element type entirely.

**Why people believe it:** both read in English as "a list of I-don't-know-what", and both reject a raw `add` of an arbitrary unrelated type at some level, so the difference between "unknown but fixed" and "known and open" feels like a distinction without a difference until you actually try to insert something.

### "`@SafeVarargs` has always been legal on any method that can't be overridden, including `private` instance methods"

**Wrong**

```java
@SafeVarargs
private void logBatches(List<String>[] batches) {
    for (List<String> batch : batches) {
        System.out.println(batch.size());
    }
}
```

(Real source declares the same parameter with a `List<String>` varargs ellipsis instead of the array brackets shown.) Compiling with `javac --release 8` on JDK 21.0.7:

```
SafeVarargsBoundary.java:5: error: Invalid SafeVarargs annotation. Instance method logBatches(List<String>[]) is not final.
1 error
```

Java 7 through 8 only permitted `@SafeVarargs` on `static` methods, `final` methods, and constructors — a `private` instance method, despite being just as impossible to override as a `final` one, was rejected outright.

**Right**

```java
javac --release 21 SafeVarargsBoundary.java
```

produces no output and exits 0 — clean compile, same source, same JDK 21.0.7 binary. Java 9 (as part of JEP 213's javac changes) extended the legal target set to include `private` instance methods, recognizing that they are equally non-overridable. On Java 21, either `private` or `final` is sufficient; on a codebase still targeting `--release 8` or lower, only `static`, `final`, or a constructor will compile.

**Why people believe it:** the underlying justification for the restriction — "the method can't be overridden" — is exactly as true of `private` as of `final`, so it feels like an oversight that was surely fixed from day one; the two-release gap between the annotation's introduction (7) and the `private` extension (9) is easy to miss unless you've hit the compile error on an old `--release` target.

## Cheat sheet

| Concept | One-line fact |
|---|---|
| Raw type | Erases the *type of every member*, not just the class's own type parameter (JLS §4.8) — includes unrelated generic methods |
| Raw type direction | `List<T>` → raw `List` assignment: always legal, no warning. Raw write with a wrong element type: warning, not error, at the write; failure surfaces at the next typed read |
| `List<Object>` | Concrete, known type argument. Fully writable. Only `List<Object>` itself is assignable to it |
| `List<?>` | Unknown-but-fixed captured type (`CAP#1`). Only `null` is writable. Any `List<T>` is assignable to it |
| raw `List` | No type argument at all. Fully writable, zero compile-time checking |
| Heap pollution trigger | Varargs parameter of a non-reifiable type (e.g. a `List<Money>` varargs parameter) → array of a component type that can't exist honestly at runtime |
| Declaration-site warning | `Possible heap pollution from parameterized vararg type` — surfaced by `-Xlint:unchecked` (and `-Xlint:all`) |
| Call-site warning | `unchecked generic array creation for varargs parameter` — same `-Xlint:unchecked` flag, different diagnostic |
| `@SafeVarargs` legal targets | `static`, `final`, constructors (Java 7+); `private` instance methods added in Java 9 |
| `@SafeVarargs` three conditions | (1) never store into the array, (2) never let a reference to it escape, (3) method cannot be overridden |
| `@SafeVarargs` is checked how | Legality (target kind) only — never the method body's actual safety |
| `@SuppressWarnings("unchecked")` scope | Narrowest possible — a local variable declaration, never a method or class |
| `@SuppressWarnings("unchecked")` rule | Always paired with a comment stating *why* the cast is provably safe |
| Citation | *Effective Java*, Item 27: *Eliminate unchecked warnings* (cite by title; item number is on the standing unverified list) |

## Self-test

**Q1.** Why does assigning a `List<CashEntry>` into a raw `List` variable compile with zero warnings, while later calling `add(someBonusEntry)` on that raw reference produces a warning instead of an error?

<details><summary>Answer</summary>

Assigning a parameterized type to its own raw type is always legal under JLS §4.10.2 — a `List<CashEntry>` genuinely is-a `List`, so no cast and no warning is needed at that assignment. The `add` call is different: because the reference is raw, `add` is typed at its erased signature `add(Object)`, so passing a `BonusEntry` type-checks syntactically — there's no `E` left to reject it against. The compiler still knows this is dangerous, which is why it emits the `[unchecked]` warning rather than silently doing nothing; it just can't turn it into a hard error without breaking the whole point of raw types being source-compatible with pre-generics code.

</details>

**Q2.** A raw `Repository` is used to call an instance method `<K> Map<K, Money> totalsBy(K key, T entry)`, where `K` is the method's own type variable and has nothing to do with `Repository<T>`'s `T`. Why does the return type collapse to raw `Map` instead of staying `Map<K, Money>` with `K` inferred from the argument?

<details><summary>Answer</summary>

JLS §4.8 says the type of a member of a raw type is the erasure of its type in the generic declaration — and that rule applies to the member as a whole, not just to the parts of its signature that reference the class's own type parameter. `totalsBy` is a member of `Repository`; reached through a raw `Repository` reference, its entire declared type — including its own type variable `K` — is erased. There is no `K` left for the compiler to infer at the call site, so the return type is the erasure `Map`, and reading from it as if it were `Map<String, Money>` requires an explicit cast.

</details>

**Q3.** What is the practical difference between `List<Object>` and `List<?>` in terms of what you can write into them?

<details><summary>Answer</summary>

`List<Object>` has a concrete, known type argument, so it accepts any reference type at `add` — it is fully writable. `List<?>` is shorthand for `List<? extends Object>`, and the compiler treats the `?` as an unknown-but-fixed captured type for the expression; since it can't prove any concrete type you supply matches that capture, every `add` call is rejected except `add(null)`, because `null` is assignable to any reference type. So `List<Object>` is fully open, `List<?>` is effectively write-only-with-null.

</details>

**Q4.** Why does a generic varargs parameter like a `List<Money>` varargs parameter produce two separate compiler warnings rather than one, and what does each one mean?

<details><summary>Answer</summary>

The two warnings describe two different risky moments. The declaration-site warning, "Possible heap pollution from parameterized vararg type", flags that the method's signature itself is admitting a non-reifiable varargs type is possible — the risk exists in the API shape. The call-site warning, "unchecked generic array creation for varargs parameter", flags the specific array `javac` builds for that particular call — it's a raw array under the hood, and the compiler is trusting that nobody stores an incompatible element into it. Both are `[unchecked]`-category warnings surfaced by `-Xlint:unchecked`, but they're independent diagnostics because a caller might trigger the second without the method author having caused the first, or vice versa.

</details>

**Q5.** What are the three conditions that make `@SafeVarargs` an honest annotation, and what does the compiler actually verify out of those three?

<details><summary>Answer</summary>

The three conditions: the method never stores anything into the varargs array, it never lets a reference to that array escape to code that doesn't already know its true type, and the method cannot be overridden — meaning it has to be static, final, private, or a constructor. Out of those three, the compiler only verifies the third — the legality of the target kind. It never inspects the method body to check whether it actually avoids storing into or leaking the array; that half is entirely on the author's honesty.

</details>

**Q6.** Before Java 9, could you legally put `@SafeVarargs` on a `private` instance method? What actually changed in Java 9?

<details><summary>Answer</summary>

No — from its introduction in Java 7 through Java 8, `@SafeVarargs` was only legal on `static` methods, `final` methods, and constructors. A `private` instance method, even though it's just as impossible to override as a `final` one, was rejected with a compile error saying the instance method "is not final." Java 9, as part of JEP 213's javac work, extended the legal target set to include `private` instance methods, closing that gap. Compiling the same source with `--release 8` versus `--release 21` on a Java 21 toolchain reproduces exactly that boundary — the 8 target rejects it, the 21 target accepts it.

</details>

**Q7.** Why should `@SuppressWarnings("unchecked")` sit on a local variable declaration instead of on the enclosing method?

<details><summary>Answer</summary>

A suppression on the method silences every unchecked operation anywhere in that method's body — including one that doesn't exist yet, that a different engineer adds years later with no relation to the original, verified-safe cast. Scoping it to the single local variable declaration where the genuinely safe cast happens means only that one line is silenced; any new unchecked operation added later in the same method still warns normally, so the warning system keeps doing its job everywhere except the one spot that's been manually proven safe.

</details>

**Q8.** A `ClassCastException` from a raw-type mix-up fires far away from where the bad element was inserted. Why does the exception happen at the read, not at the write?

<details><summary>Answer</summary>

Generics are erased at compile time — `List<CashEntry>` and `List<BonusEntry>` are both just `List` at the bytecode level, so the JVM has no runtime record of the intended element type to check against at the point of insertion. What the compiler does instead is insert an implicit `checkcast` at every *read* site — for example, the enhanced-for loop's `iterator().next()` call gets a `checkcast CashEntry` appended right after it. The write goes through unchecked because there's genuinely nothing left to check it against; the read is where the compiler's own inserted cast finally catches the mismatch.

</details>

## Open questions

None.

---

**Leaves covered:** 1.21.15, 1.21.16, 1.21.18, 1.21.19 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 585
