# 03 Java Core — Generics: the basics — BASICS (§1.21, 1.21.1–1.21.6)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Exception mechanics](../exceptions/03-internals-exception-mechanics.md) · Next: [Erasure and its consequences](01a-erasure-and-its-consequences.md)

This file covers why generics exist (1.21.1), the three declaration forms — generic classes, generic interfaces, generic methods (1.21.2) — the naming convention for type parameters (1.21.3), bounded type parameters and what a bound does to the emitted descriptor (1.21.4), explicit type witnesses (1.21.5), and the diamond operator including its Java 9 extension to anonymous classes (1.21.6). It hands off deliberately: erasure itself, reifiable types and the consequences of erasure live in `01a-erasure-and-its-consequences.md`; wildcards, variance and PECS live in `01b-variance-and-wildcards.md`; raw types, `List<Object>` vs `List<?>`, `@SafeVarargs` live in `01c-raw-types-and-unchecked-warnings.md`; recursive bounds and heterogeneous containers live in `01d-recursive-bounds-and-heterogeneous-containers.md`; the bytecode-level view of erasure and bridge methods lives in `03-internals-erasure.md` and `03a-internals-bridge-methods.md`; full JLS §18 inference and inference failure diagnostics live in `02c-inference-and-generic-limits.md`. All code in this file targets QuizStakes: a `Repository<T>` over `LedgerEntry`, a `FundsLedger` batch API, and the shared sealed hierarchy `LedgerEntry` / `CashEntry` / `BonusEntry` used across this note set.

## 1. Why generics exist: the distance between the fault and the symptom (1.21.1)

Picture a pre-Java-5 collection as a shelf that accepts anything and remembers nothing about what it was handed. You put a `CashEntry` on it; the shelf's contract says "you get an `Object` back." Every reader has to guess the real type and cast, and the compiler has no way to check the guess. The guess is usually right, which is exactly what makes it dangerous: the code that reads the shelf and gets it wrong doesn't fail where the wrong item was placed — it fails wherever the cast happens to live, which can be a different method, a different class, a different day's log file.

### Why it exists

Before Java 5, `java.util.List` held `Object`. A method that accepted a `List` had no way to declare "a list of `CashEntry`" — the type system stopped at "a list." Callers routinely mixed in the wrong element by accident (a stray `String` status code appended by an unrelated ingest path, say), and the compiler had no basis to object because as far as it knew the list only ever promised `Object`. The mistake was silent at the point it happened and loud at the point something tried to use the result.

### The mechanism

Compile and run the pre-generics shape on JDK 21.0.7 with `-source`/`--release` left at its default (21) but the code itself written the old way — raw `List`, `Object` element type, cast at the read site:

```java
static void pollute(List batch) {
    // a stray status code slipped in by an unrelated ingest path
    batch.add("DEP-301");
}

static void report(List batch) {
    for (Object o : batch) {
        CashEntry ce = (CashEntry) o;
        System.out.println(ce.amount());
    }
}
```

`javac -Xlint:all` compiles this with six warnings (`rawtypes`, `unchecked`) but zero errors — a raw `List` accepts anything, so `pollute` is legal. Running it produces:

```
Money[amount=4.20, currency=GBP]
Exception in thread "main" java.lang.ClassCastException: class java.lang.String cannot be cast to class Raw1$CashEntry (java.lang.String is in module java.base of loader 'bootstrap'; Raw1$CashEntry is in unnamed module of loader 'app')
	at Raw1.report(Raw1.java:18)
	at Raw1.main(Raw1.java:28)
```

The `CashEntry` that printed fine came first; the failure is on the *next* iteration, at the cast in `report`, twenty-eight lines and two stack frames away from the `add` in `pollute` that actually put the bad value in. In a real reporting job `pollute`-equivalent code and `report`-equivalent code can be in different services, different deploys, different weeks. The stack trace names the crime scene, not the culprit.

Now the generic version of the same shapes:

```java
static void pollute(List<CashEntry> batch) {
    batch.add("DEP-301");
}
```

`javac` refuses to compile it:

```
Gen1.java:12: error: incompatible types: String cannot be converted to CashEntry
        batch.add("DEP-301");
                  ^
1 error
```

The type parameter turns "found out three frames away at 2 a.m." into "found out at your own desk before the build finishes." That is the entire pitch for generics: not new capability, a **moved failure point** — from a runtime `ClassCastException` at an arbitrary read site to a compile-time diagnostic at the exact write site that caused it.

**Insight:** generics do not make illegal states unrepresentable at runtime — the JVM still only ever has `Object` in that list slot, `[X-REF nn]` see `01a-erasure-and-its-consequences.md`. They make illegal states *unrepresentable at compile time*, which is a weaker guarantee that happens to catch the overwhelming majority of real mistakes, because most bugs are caught by the same person who is about to make them, at the moment they write the bad line.

**Interview:** "why do generics exist if they're erased anyway?" — because the compiler check happens before erasure; erasure only affects what survives to run time, not what `javac` was willing to accept in the first place.

> Generics exist to move a class of type mistakes from a `ClassCastException` thrown at an arbitrary, possibly distant read site to a `javac` diagnostic at the exact write site that caused it.

## 2. The three declaration forms: generic class, generic interface, generic method (1.21.2)

Three different things in the language share the angle-bracket syntax and get treated as one blur by anyone who has not had to write all three by hand: a type parameter can belong to a class, to an interface, or to a single method — and a method's own type parameter list is written in a place people reliably get wrong.

| Form | Where `<T>` is declared | Where `T` is usable | QuizStakes example |
|---|---|---|---|
| Generic class | On the class, after the class name | Every non-static member | `class Repository<T extends LedgerEntry> { }` (body elided) |
| Generic interface | On the interface, after the interface name | Every method signature in the interface | `interface Verifier<V extends Verdict> { boolean verify(V value); }` |
| Generic method | Between the modifiers and the return type, on the method itself | Only that method's parameters, return type and body | `static <T> T firstNonNull(T primary, T fallback)` |

### Why it exists

A generic *class* parameterizes an entire object — every field, every method that isn't `static`, shares the same `T` for the object's lifetime. That is too coarse for a single utility method that has nothing to do with any particular instance's type — a `static` helper that picks between two candidates of the same type, say, has no instance to hang `T` off. The generic *method* form exists so a single method can introduce its own type parameter, scoped to just that call, independent of (or in addition to) any type parameter its enclosing class already has.

### The mechanism

A generic class puts the parameter list right after the class name, and every instance member can use it:

```java
interface Repository<T extends LedgerEntry> {
    void save(T entry);
    Money totalOf(T entry);
}
```

A generic interface is identical in shape — the parameter list sits on the interface declaration, and every method in the interface can reference it. `Repository<T>` above is already both a generic type declaration and, because it is declared with `interface`, a generic interface; QuizStakes' `Verifier<V extends Verdict>` is another:

```java
interface Verifier<V extends Verdict> {
    boolean verify(V value);
}
```

A generic *method* is different: the type parameter list goes **between the access modifiers and the return type**, not before the method name and not after it:

```java
static <T extends LedgerEntry & Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

`static` comes first because it is a modifier, not part of the type; `<T extends LedgerEntry & Comparable<T>>` is the method's own type parameter declaration; `T` after that is the return type, now in scope because it was just declared. Writing `static T <T> max(T a, T b)` or `T static <T> max(T a, T b)` is the mistake this trips people into, and both fail to compile — the parameter list has to introduce `T` before anything in the signature is allowed to refer to it, and the compiler reads left to right the same way you do.

A generic method can exist standalone (as above) or on a class that is *itself* already generic — `Repository<T>` could additionally declare `<R> R runReport(Function<T, R> summarizer)`, where `T` is the class's own parameter and `R` is scoped to just that one method call. The two parameter lists do not collide because they are declared and scoped independently.

No diagram: the manifest assigns this section none; the table above is the picture.

**Gotcha:** a generic method's type parameter can shadow an identically-named type parameter on its enclosing generic class. `class Repository<T extends LedgerEntry> { <T> void save(T x) { } }` compiles — `javac` warns (`-Xlint:all` reports it as a name-shadowing note in most configurations) but does not error — and the inner `T` has nothing to do with the outer one. Reusing the letter is legal and confusing; don't.

> A generic class or interface binds its type parameter to every instance member for the object's whole lifetime; a generic method binds its own type parameter to a single invocation, declared in the parameter list that sits between the modifiers and the return type.

## Supporting facts

### Type parameter naming conventions (1.21.3)

Single uppercase letters are convention, not syntax — `javac` accepts any legal identifier as a type parameter name, including `CashEntryType`. The convention exists purely so a reader can tell at a glance what role a parameter plays without reading the bound.

| Letter | Traditional meaning | Example from the JDK or QuizStakes |
|---|---|---|
| `T` | Type (the general case) | `Repository<T extends LedgerEntry>` |
| `E` | Element (of a collection) | `List<E>`, `Iterator<E>` |
| `K`, `V` | Key, Value (of a map) | `Map<K, V>` |
| `R` | Return type (of a function-shaped generic) | `Function<T, R>` |
| `U`, `S` | A second, unrelated type parameter when `T` is taken | `BiFunction<T, U, R>` |
| `N` | Number | seen in numeric-library generics, not in the JDK collections themselves |

> The letters carry no compiler meaning; they are a naming convention so `Map<K, V>` reads as "key, value" instead of forcing a reader to open the bound to find out.

## 3. Bounded type parameters, and what a bound does to the descriptor (1.21.4)

An unbounded `<T>` only ever promises "some type," which means the only methods callable on a `T` are the ones every `Object` has. A bound is a promise stapled onto the type parameter — "whatever `T` turns out to be, it will have this API" — and that promise is what lets you call domain methods on a value you have not yet named.

### Why it exists

Without a bound, `Repository<T>` could not call `entry.amount()` inside `totalOf(T entry)`, because as far as the compiler is concerned `T` might be anything at all — a `String`, an `Integer`, anything with an `Object`'s API and nothing more. The bound `T extends LedgerEntry` tells the compiler "restrict `T` to subtypes of `LedgerEntry`, and in exchange you may treat any `T` as at least a `LedgerEntry` inside this declaration." That is the whole trade: less freedom in what can be substituted, more API surface usable on the substituted value.

### The mechanism

```java
interface Repository<T extends LedgerEntry> {
    void save(T entry);
    Money totalOf(T entry);   // legal only because T is bounded to LedgerEntry
}
```

Multiple bounds stack with `&`, and the rule is fixed: **at most one class bound, and it must come first**; every bound after the first must be an interface.

```java
static <T extends LedgerEntry & Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```

`LedgerEntry` here is actually an interface too (it is `sealed interface LedgerEntry permits CashEntry, BonusEntry`), so this particular example has no class bound at all — but the ordering rule is unconditional: if a class bound is present, `javac` requires it in the leftmost position, and rejects a second class bound outright, because a type cannot single-inherit from two unrelated classes.

**Insight:** The bound is what erasure keeps. Compiled and inspected with `javap -p -v` on JDK 21.0.7, `Repository`'s `totalOf(T entry)` erases to:

```
public Repo1$Money totalOf(T);
    descriptor: (LRepo1$LedgerEntry;)LRepo1$Money;
    flags: (0x0001) ACC_PUBLIC
    Signature: #25                          // (TT;)LRepo1$Money;
```

and the generic method:

```
static <T extends Repo1$LedgerEntry & java.lang.Comparable<T>> T max(T, T);
    descriptor: (LRepo1$LedgerEntry;LRepo1$LedgerEntry;)LRepo1$LedgerEntry;
```

The `descriptor` line — what the JVM actually dispatches on — carries `LRepo1$LedgerEntry`, the erasure of the *leftmost* bound. `Comparable<T>`, the second bound, is nowhere in the descriptor at all; it survives only in the `Signature` attribute (`#25`, decoded above as `(TT;)LRepo1$Money;` for `totalOf`, and the fuller generic signature on `max`), which is metadata the verifier and the JVM's bytecode dispatch ignore and only `javac` and reflection (`Method.getGenericParameterTypes`, `Class.getTypeParameters`) read back. An unbounded `<T>` erases to `Object` in the descriptor; a bound moves the descriptor's type from `Object` to the erasure of that leftmost bound, which is the entire reason `totalOf` can call `entry.amount()` without a cast — the erased signature genuinely accepts a `LedgerEntry`, not an `Object` narrowed at compile time only. The mechanics of erasure itself — why the leftmost bound specifically, what happens with no bound at all, and the bridge methods this forces the compiler to synthesize — are `03-internals-erasure.md` and `03a-internals-bridge-methods.md`'s subject, not this file's.

No diagram: the manifest assigns this section none; the `javap` excerpt above is the picture.

**Gotcha:** the bound restricts what can be substituted *for* `T`, not what `T` itself can be treated as beyond the bound. Inside `Repository<T extends LedgerEntry>`, a `T` can be used anywhere a `LedgerEntry` is expected, but the reverse does not hold — a plain `LedgerEntry` cannot be passed where a `T` is expected, because `T` might be narrowed by the caller to `CashEntry` specifically. `[X-REF nn]` this asymmetry is also why `<T extends Comparable<? super T>>` exists as a *recursive* bound rather than plain `<T extends Comparable<T>>` — see `01d-recursive-bounds-and-heterogeneous-containers.md`.

> A bound restricts which types may be substituted for a type parameter, and in exchange lets the body treat every value of that parameter as at least the bound's type; erasure keeps only the leftmost bound in the method's actual descriptor, and demotes every other bound to signature metadata that only `javac` and reflection read.

## 4. Generic method invocation and the explicit type witness (1.21.5)

Most of the time `javac` figures out a generic method's type argument from the arguments you pass it or the context it's assigned into, silently, and you never see the angle brackets at the call site. The type witness is what you write when that inference genuinely cannot find an answer — an explicit `<CashEntry>` slotted in before the method name, telling the compiler what it could not work out on its own.

### Why it exists

Inference has a blind spot: it can see the *arguments* to a call and the *assignment target* the call sits in, but it cannot see through an intervening method call. `FundsLedger.emptyBatch()` returning `List<T>` gets its `T` from context when the call is the entire right-hand side of an assignment — but chain one more call onto it, `.get(0)`, and the assignment target (`CashEntry`) is now the target of `.get(0)`, not of `emptyBatch()`. Overload resolution for `.get` has to pick a receiver type before it can even look at what the caller eventually wants, so `emptyBatch()`'s `T` gets resolved first, in isolation, against nothing but its own bound.

### The mechanism

```java
static class FundsLedger {
    static <T extends LedgerEntry> List<T> emptyBatch() {
        return new ArrayList<>();
    }
}
```

Called directly in an assignment, inference works fine — `T` is resolved from the declared type of the left-hand side:

```java
List<CashEntry> batch = FundsLedger.emptyBatch();   // T = CashEntry, infers cleanly
```

Chain a `.get(0)` onto the unqualified call before assigning, and `javac` 21.0.7 rejects it:

```
Witness4.java:18: error: incompatible types: LedgerEntry cannot be converted to CashEntry
        CashEntry first = FundsLedger.emptyBatch().get(0);
                                                      ^
1 error
```

`emptyBatch()` was resolved with no target type available, so `T` fell back to its own bound, `LedgerEntry` — and `.get(0)` on a `List<LedgerEntry>` returns `LedgerEntry`, which is not assignable to `CashEntry` without a cast. The type witness supplies the missing information directly at the call that needed it, ahead of the bound-only fallback:

```java
CashEntry first = FundsLedger.<CashEntry>emptyBatch().get(0);
```

which compiles clean on JDK 21.0.7. The witness sits between the receiver and the method name — `Receiver.<TypeArg>methodName(args)` — which is also how a witness reads on an instance-qualified call, `this.<T>m()`, and on the textbook JDK example, `Collections.<String>emptyList()`. **A witness on a constructor is not this syntax** — `new ArrayList<String>()` supplies the *class's* type argument via the diamond position, not a method-style witness; there is no `new <String>ArrayList()` form. `[X-REF nn]` full inference machinery — what the compiler tries before falling back to a bound, and the exact JLS §18 diagnostics for each failure shape — is `02c-inference-and-generic-limits.md`'s subject.

No diagram: the manifest assigns this section none; the `javac` diagnostic above is the picture.

**Interview:** "when do you actually need an explicit type witness?" — when the generic call is not itself sitting in a context with a target type (an assignment, a return, an argument slot) but is instead the receiver of a further call or otherwise consumed before target typing can reach it; the fix is naming the type argument at the call that has no target.

> An explicit type witness, `Receiver.<Type>method(args)`, supplies a generic method's type argument directly when the call site has no target type for inference to fall back on, which otherwise resolves the parameter to its declared bound instead of the type the caller actually wanted.

## 5. The diamond operator, and its Java 9 extension to anonymous classes (1.21.6)

The diamond is not really about typing fewer characters — it's the compiler agreeing to copy a type argument you already wrote once (on the left of an assignment, or in a target context) onto the constructor call on the right, instead of making you write it twice.

### Why it exists

Before Java 7, `List<CashEntry> batch = new ArrayList<CashEntry>();` required the type argument twice — the compiler already knew `batch`'s type from the left-hand side, but the constructor call still had to spell it out in full, because prior to Java 7 constructor invocations had no target-typing rule that let them infer from the assignment. JLS 21 §15.9.1 specifies the diamond form `new ArrayList<>()` as leaving the type-argument list empty and letting inference supply it from context — the class declaration on the left, or whatever other target type applies.

### The mechanism

The diamond on a plain constructor call has worked since Java 7 and is unremarkable. The extension that people get wrong the version of is **anonymous class creation expressions** — `new SomeType<>()` with a class body attached — which JLS 21 §15.9.1 and JEP 213 ("Milling Project Coin") describe as legal starting in **Java 9**, not Java 7. Compiling the same anonymous-diamond source under `--release 8` versus `--release 21` on JDK 21.0.7 proves the boundary directly:

```java
Comparator<Money> byAmount = new Comparator<>() {
    public int compare(Money a, Money b) {
        return a.amount.compareTo(b.amount);
    }
};
```

`javac --release 8`:

```
Diamond2.java:11: error: cannot infer type arguments for Comparator<T>
        Comparator<Money> byAmount = new Comparator<>() {
                                                   ^
  reason: '<>' with anonymous inner classes is not supported in -source 8
    (use -source 9 or higher to enable '<>' with anonymous inner classes)
  where T is a type-variable:
    T extends Object declared in interface Comparator
1 error
```

`javac --release 21` on the identical source: no errors, and the compiled class runs and reports `class Diamond2$1` for `byAmount.getClass()` — an ordinary anonymous-class name, indistinguishable from one written with the type argument spelled out.

Between Java 7 and Java 8, spelling out `new Comparator<CashEntry>()` with the full type argument on an anonymous class body was mandatory — you could drop the diamond on an anonymous class's supertype only from Java 9 onward. Anyone quoting "the diamond arrived in Java 7, full stop" is describing the Java 7 constructor-only form and missing the anonymous-class carve-out that took two more releases to land — the version trap examiners still probe for.

**Pitfall:** `new ArrayList<>()` and `new ArrayList()` look interchangeable at a glance and are not. `new ArrayList<>()` is diamond inference — the compiler fills in the type argument and full generic checking applies. `new ArrayList()` with no brackets at all is a **raw type** — it disables generic type checking for that expression entirely, the same unchecked-warnings mechanism section 1 demonstrated with `pollute(List batch)`. `javac -Xlint:all` flags `new ArrayList()` with a `rawtypes` warning and nothing more; it does not become an error, and at run time `new ArrayList<>().getClass() == new ArrayList().getClass()` is `true` — both produce the identical `ArrayList` class object, because erasure means there was never a separate raw-type class to begin with. The full raw-type story — `List<Object>` vs `List<?>` vs raw `List`, and where `@SuppressWarnings("unchecked")` and `@SafeVarargs` legitimately apply — is `01c-raw-types-and-unchecked-warnings.md`'s subject.

No diagram: the manifest assigns this section none; the two compiler transcripts above are the picture.

> The diamond `<>` lets a constructor call omit a type argument that inference can recover from context — legal for ordinary constructor invocations since Java 7, and, per JLS 21 §15.9.1 and JEP 213, extended to anonymous class creation expressions only from Java 9 onward.

## Pitfalls

### "The stack trace tells me where the bug is"

**Wrong**

```java
static void pollute(List batch) { batch.add("DEP-301"); }
static void report(List batch) {
    for (Object o : batch) {
        CashEntry ce = (CashEntry) o;   // ClassCastException fires HERE
    }
}
```
Running this throws `ClassCastException` inside `report`, at the cast — nowhere near `pollute`, which is where the real mistake was made.

**Right**

```java
static void pollute(List<CashEntry> batch) { batch.add("DEP-301"); }   // won't compile
```
`javac` rejects the bad `add` at the exact line that would have caused the eventual runtime failure: `error: incompatible types: String cannot be converted to CashEntry`. The fault and the diagnostic are now the same line.

**Why people believe it:** a stack trace does name a real, specific line — it's just the line where the *symptom* surfaced, not the line where the *cause* was introduced, and with `Object`-typed collections those two lines can be arbitrarily far apart.

### "A generic method's type parameter goes next to the method name, like the class form"

**Wrong**

```java
static T <T> max(T a, T b) { return a; }   // does not compile
```
`javac` rejects this — at the point `T` appears as the return type, it has not been declared yet.

**Right**

```java
static <T extends LedgerEntry & Comparable<T>> T max(T a, T b) {
    return a.compareTo(b) >= 0 ? a : b;
}
```
The type parameter list sits between the modifiers (`static`) and the return type, introducing `T` before anything in the signature is allowed to use it.

**Why people believe it:** generic *classes* put `<T>` immediately after the name they parameterize (`Repository<T>`), so it's a natural — but wrong — guess that a generic method puts it after the method name the same way.

### "`new ArrayList<>()` and `new ArrayList()` are the same thing, one's just shorter"

**Wrong**

```java
List<CashEntry> a = new ArrayList<>();
List<CashEntry> b = new ArrayList();   // compiles, with a warning — and is not the same guarantee
b.add("not a CashEntry");              // compiles too — no error, ever
```
`javac -Xlint:all` warns `found raw type: ArrayList` on the second line but produces zero errors on `b.add("not a CashEntry")` at any point — raw-type usage turns off generic checking for that variable completely.

**Right**

```java
List<CashEntry> b = new ArrayList<>();
b.add("not a CashEntry");   // error: incompatible types: String cannot be converted to CashEntry
```
The diamond keeps `b` genuinely parameterized as `List<CashEntry>`, so the compiler checks every subsequent call against `CashEntry`.

**Why people believe it:** both forms produce, at run time, the literal same `ArrayList` class object (`new ArrayList<>().getClass() == new ArrayList().getClass()` is `true` under erasure), so a debugger inspecting the live object shows no difference — the difference is entirely in what the compiler checked before it got there, and that's invisible once the program is running.

### "The diamond has worked with anonymous classes since it was introduced in Java 7"

**Wrong**

```java
Comparator<Money> byAmount = new Comparator<>() {
    public int compare(Money a, Money b) { return a.amount.compareTo(b.amount); }
};
```
Compiled with `javac --release 8` on JDK 21.0.7: `error: cannot infer type arguments for Comparator<T>` / `reason: '<>' with anonymous inner classes is not supported in -source 8`.

**Right**

The identical source compiled with `javac --release 21` produces zero errors and runs, because JEP 213 legalized the diamond on anonymous class creation expressions starting in **Java 9** — two releases after the diamond itself.

**Why people believe it:** the diamond and "Java 7" are genuinely linked for ordinary constructor calls, so the fact stuck without the caveat that anonymous-class supertypes were carved out and shipped later.

## Cheat sheet

| Fact | Value |
|---|---|
| Generic class parameter position | After the class/interface name: `Repository<T extends LedgerEntry>` |
| Generic method parameter position | Between modifiers and return type: `static <T> T method(T arg)` |
| Multiple bounds order | Class bound first (at most one), interface bounds after, joined with `&` |
| What lands in the erased descriptor | Only the leftmost bound (or `Object` if unbounded) |
| Where every bound survives | The class file's `Signature` attribute — reflection-only, ignored by the JVM verifier for dispatch |
| Type witness syntax | `Receiver.<Type>method(args)` — before the method name, after the receiver |
| Witness on a constructor | Not this syntax — use the diamond or an explicit type argument on `new` |
| Diamond on constructors | Legal since Java 7 (JLS 21 §15.9.1) |
| Diamond on anonymous classes | Legal since **Java 9** (JEP 213) — `--release 8` rejects it, `--release 21` accepts it |
| `new ArrayList<>()` vs `new ArrayList()` | Diamond: type-checked. No brackets: raw type, checking disabled for that value |
| `E`, `K`/`V`, `T`, `R`, `U`/`S`, `N` | Element; Key/Value; Type; Return; second/third type; Number |

## Self-test

**Q1.** A `ClassCastException` in a raw-typed reporting job points to the `report` method, but the bad value was added in an unrelated `pollute` method two deploys ago. Why doesn't the stack trace name `pollute`?

<details><summary>Answer</summary>

Because a raw `List` makes no promise about its element type beyond `Object`, `pollute`'s `add` call is completely legal as far as the compiler is concerned — there's nothing to reject at that point. The failure only becomes observable where something tries to use the value as a specific type, which is the cast inside `report`. The stack trace is accurate about where the exception was *thrown*; it says nothing about where the bad data was *introduced*, because nothing detected a problem until the cast.

</details>

**Q2.** Why does `static <T extends LedgerEntry> List<T> emptyBatch()` fail to infer the right type when called as `FundsLedger.emptyBatch().get(0)` and assigned to a `CashEntry`?

<details><summary>Answer</summary>

Because the assignment's target type, `CashEntry`, belongs to `.get(0)`, not to `emptyBatch()`. Overload resolution and type inference for `emptyBatch()` happen first, in isolation, with no visibility into what `.get(0)` will eventually be assigned to — so `T` falls back to its declared bound, `LedgerEntry`. `.get(0)` then genuinely returns a `LedgerEntry`, which can't be narrowed to `CashEntry` without a cast, so the assignment fails to compile. An explicit witness, `FundsLedger.<CashEntry>emptyBatch().get(0)`, fixes it by supplying `T` directly instead of relying on inference to see through the chained call.

</details>

**Q3.** What exactly does a type parameter bound change in the compiled class file, and what does it leave unchanged?

<details><summary>Answer</summary>

It changes the method's actual descriptor — the part the JVM verifier and dispatch mechanism read — from `Object` (unbounded) to the erasure of the leftmost bound. For `<T extends LedgerEntry & Comparable<T>>`, that means the descriptor uses `LedgerEntry`, confirmed by `javap` showing `descriptor: (LRepo1$LedgerEntry;)LRepo1$Money;`. It leaves the *second* bound, `Comparable<T>`, out of the descriptor entirely — that information only survives in the class file's `Signature` attribute, which the JVM ignores for actual method resolution and only `javac` (for later compilation) and reflection read back.

</details>

**Q4.** Where exactly does the type parameter list go on a generic method, and why can't it go where a generic class puts it?

<details><summary>Answer</summary>

It goes between the modifiers and the return type — `static <T extends LedgerEntry & Comparable<T>> T max(T a, T b)`. It can't go after the method name the way a generic class puts `<T>` after the class name, because the return type appears before the method name in a method declaration, and that return type needs `T` to already be in scope. Declaring `<T>` any later than "right before the return type" would mean the return type is read before the type parameter that names it exists.

</details>

**Q5.** What is the actual difference between `new ArrayList<>()` and `new ArrayList()`, given that both produce objects of the identical runtime class?

<details><summary>Answer</summary>

The difference is entirely at compile time. `new ArrayList<>()` is diamond inference — the compiler infers a real type argument from context and then checks every subsequent operation on that list against it. `new ArrayList()` is a raw type — it has no type argument at all, which switches off generic type checking for that value completely; `javac` only warns (`rawtypes`), it never errors, and you can add anything to it. At run time they're indistinguishable because generics are erased — both are plain `ArrayList` objects — but only the diamond version gets compile-time protection against putting the wrong type in.

</details>

**Q6.** JLS 21 §15.9.1 and JEP 213 date the diamond-on-anonymous-classes extension to Java 9. What compiler evidence, specifically, proves that boundary rather than just asserting it?

<details><summary>Answer</summary>

Compiling the identical anonymous `Comparator<>()`-with-a-body source twice on the same JDK 21.0.7 `javac`, once with `--release 8` and once with `--release 21`. The `--release 8` run fails with `cannot infer type arguments for Comparator<T>` and an explicit `reason: '<>' with anonymous inner classes is not supported in -source 8`. The `--release 21` run compiles cleanly and the class runs. Since it's the same compiler and the same source, the only variable is the targeted release level, which isolates the feature boundary precisely to somewhere between "8" and "21" — and the compiler's own error message names Java 9 as the point it becomes legal.

</details>

**Q7.** Why is `Comparable<T>` written second in `<T extends LedgerEntry & Comparable<T>>` rather than first, and is the ordering a style choice?

<details><summary>Answer</summary>

It's not a style choice — it's enforced by the compiler. At most one of the bounds in a multiple-bound type parameter may be a class, and if one is present it must be listed first; every bound after it must be an interface. In this particular declaration `LedgerEntry` happens to be an interface too, so there's no class bound present at all, but the rule is unconditional regardless: were `LedgerEntry` a class instead, putting `Comparable<T>` before it would fail to compile, because a type parameter can only single-inherit from one class, and the compiler needs that one class bound in a fixed, predictable position to resolve the erasure.

</details>

**Q8.** A witness on a generic method looks like `Collections.<String>emptyList()`. Why doesn't the same syntax work for a constructor — why isn't there a `new <String>ArrayList()`?

<details><summary>Answer</summary>

Because a constructor's type argument is supplied through the class's own type argument list — the diamond position, as in `new ArrayList<String>()` or the inferred `new ArrayList<>()` — not through a witness-style prefix. The witness syntax, `Receiver.<Type>method(args)`, exists specifically for *method* type parameters, which are declared separately from any class-level type parameter and need their own slot to be supplied explicitly. A constructor doesn't have an independent method-level type parameter list in that sense; its type argument is the class's, so it's written where the class's type argument always goes.

</details>

## Open questions

None.

---

**Leaves covered:** 1.21.1, 1.21.2, 1.21.3, 1.21.4, 1.21.5, 1.21.6 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 454
