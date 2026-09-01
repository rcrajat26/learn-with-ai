# 03 Java Core — Type inference, and what generics cannot do — INTERMEDIATE (§2.7, 2.7.11–2.7.15)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Generic arrays and self-types](02b-generic-arrays-and-self-types.md) · Next: [Migration compatibility and reading hard signatures](02d-migration-and-reading-signatures.md)

This file has two halves. The first is what the compiler figures out for you without being asked — the five contexts where `javac` runs constraint-based type inference, and how to read it when it fails (2.7.11, 2.7.12). The second is the walls generics puts up on purpose — an overload you cannot write, a static member you cannot declare, an exception type you cannot throw as a type variable, and an `instanceof` you cannot test (2.7.13, 2.7.14, 2.7.15). It hands off the diamond's own version history and the type-witness *syntax* to `01-basics.md`, the reifiable-type enumeration to `01a-erasure-and-its-consequences.md`, wildcard capture and `var`-on-a-wildcard to `01b-variance-and-wildcards.md`, `Class<T>` tokens to `02a-type-tokens-and-generic-reflection.md`, the ternary's own typing rules to `../primitives-and-conversions/02c-conditional-operator.md`, and every bytecode-level mechanism behind the walls in the second half to `03d-internals-erasure-limits-and-capture.md`. All code below compiled or ran on Oracle JDK 21.0.7 (`21.0.7+8-LTS-245`); every quoted diagnostic is real `javac` output from that build, not a paraphrase.

## 1. The five inference contexts you meet (2.7.11)

`[RESEARCH]` JLS 21 chapter 18 defines one constraint-solving algorithm — reduce an expression's shape to a set of bound constraints on inference variables, resolve them to concrete types. It does not run identically in every position; the reader does not need the algorithm, they need to recognise which of five *contexts* triggered it, because that context is what an error message and its fix both depend on.

| Context | Version | Infers from | Quick shape |
|---|---|---|---|
| Diamond `<>` | Java 7; anonymous classes Java 9 (JEP 213) | the target type of the assignment/declaration | `List<CashEntry> batch = new ArrayList<>();` |
| Generic method type arguments | Java 5 from arguments; Java 8 adds target typing | actual argument types, and — since 8 — the surrounding target type when arguments alone underdetermine it | `List<CashEntry> r = FundsLedger.emptyBatch();` |
| Lambda / method reference target typing | Java 8 | the functional interface supplied by context; parameter types come from its abstract method's descriptor | `Comparator<CashEntry> byAmount = (a, b) -> a.amount().amount().compareTo(b.amount().amount());` |
| `var` | Java 10 | the initialiser expression only, once, at the declaration | `var batch = new ArrayList<CashEntry>();` |
| Conditional expression (poly/standalone) | Java 8 poly-expression rules (JLS 15.25) | the target context if the conditional is a poly expression; its own operand types if standalone | `Money m = flag ? cashMoney : bonusMoney;` |

### 1.1 The diamond

`new ArrayList<>()` carries no type argument of its own; the compiler pulls one out of wherever the expression's value is going — the declared type of the variable it is assigned to, the declared parameter type of the method it is passed to, the return type of the enclosing method. Java 7 gave you this for constructor invocations only; Java 9 (JEP 213) extended it to anonymous class bodies — a diamond on `new AbstractStore<>() { }` with an overriding body supplied — which had been excluded because an anonymous subclass's supertype has to be a real, resolvable type at the point the compiler generates the synthetic class file — that resolution order took two releases to work out. `01-basics.md` owns the diamond itself and has already proved that version boundary by compiling the anonymous form under `--release 8` and watching it fail; this file does not repeat that experiment.

### 1.2 Generic method arguments — and the Java 8 change

A generic method's type variable is normally inferred from what you pass it:

```java
static <T> List<T> singletonBatch(T entry) {
    List<T> batch = new ArrayList<>();
    batch.add(entry);
    return batch;
}
```

`singletonBatch(new CashEntry(UUID.randomUUID(), someMoney))` infers `T = CashEntry` from the argument — that rule predates Java 8 and needs no proof. The Java 8 change is specifically about calls where the *arguments* do not pin the type variable down at all and the *target* has to supply it — the case the old folklore witness syntax exists to work around. Concretely: a bare generic factory used as an argument.

```java
static <T> List<T> emptyBatch() { return new ArrayList<>(); }
static void postBatch(List<CashEntry> batch) { /* posts to the ledger */ }

void postNothing() {
    postBatch(emptyBatch());               // T inferred as CashEntry from postBatch's parameter
}
```

This compiles clean on JDK 21 — that much is expected. What I could **not** do is show you the pre-8 failure directly: `javac --release 8` on this machine still runs the JDK 21 compiler with the *language level and API surface* pinned to 8, not the literal `javac` binary that shipped with Java 8. The inference algorithm itself is not rolled back by `--release`, and JDK 21 no longer accepts `--release 7` at all (`error: release version 7 not supported`) to even attempt the comparison from the other direction. So the honest statement is: the "pre-8 code carries type witnesses that look unnecessary today" folklore is well documented (this is literally what the enhanced target-typing work in JSR 335 was for), but this file cannot reproduce the old failure on the tooling available here, and does not assert a diagnostic it has not produced. The practical residue you will actually meet is old code written as `FundsLedger.<CashEntry>emptyBatch()` in a position where a modern compiler no longer needs the witness — 2.7.12 covers reading and writing that witness.

### 1.3 Target typing of lambdas and method references

A lambda has no type of its own to inspect — `(a, b) -> a.amount().amount().compareTo(b.amount().amount())` is meaningless in isolation. The compiler assigns it a type only from context (a functional interface), and once that interface is fixed, its abstract method's parameter types flow back onto the lambda's own parameters, which is why you can usually leave them off:

```java
Comparator<CashEntry> byAmount =
    (a, b) -> a.amount().amount().compareTo(b.amount().amount());   // a, b inferred as CashEntry

Function<? super LedgerEntry, ? extends Money> amountOf = entry -> entry.amount();  // entry inferred as LedgerEntry
```

Both compiled with no warnings. That second line is worth pausing on: the target type is `Function<? super LedgerEntry, ? extends Money>`, a wildcard-bounded functional interface, and the parameter type the lambda actually receives is the wildcard's bound (`LedgerEntry`), not the wildcard itself — wildcards do not appear as concrete types anywhere at the use site, only as constraints on what concrete type gets substituted (`01b-variance-and-wildcards.md` owns wildcard mechanics in full).

Explicit parameter types become mandatory once the target type itself does not fully pin down the descriptor. The clean, real case is a lambda assigned to a **raw** functional interface — a raw `Comparator` erases its abstract method to `int compare(Object, Object)`, so the lambda's parameters are typed `Object`, not `Money`, and only an explicit `(Object a, Object b)` with an internal cast compiles:

```java
@SuppressWarnings("unchecked")
void run() {
    Comparator raw = (Object a, Object b) ->
        ((Money) a).amount().compareTo(((Money) b).amount());
}
```

`javac -Xlint:all` on this produces exactly one diagnostic — `[rawtypes] found raw type: Comparator` — and no error; dropping the explicit `Object` types and writing `(a, b) -> ((Money) a).amount().compareTo(((Money) b).amount())` compiles too (they default to `Object` either way, since the descriptor forces it), but writing `(Money a, Money b) -> a.amount().compareTo(b.amount())` fails outright with `incompatible types: incompatible parameter types in lambda expression`, because a lambda's declared parameter types must match the functional interface's descriptor exactly — unlike overriding, there is no covariant narrowing at a lambda boundary.

`var` and lambdas do not mix at all, regardless of explicit parameter types, because `var` needs a denotable type from the initialiser and a lambda's type is never denotable on its own:

```java
var fn = (CashEntry c) -> c.amount();
```

```
error: cannot infer type for local variable fn
  (lambda expression needs an explicit target-type)
```

### 1.4 `var`

`var` (Java 10) infers strictly once, from the initialiser expression, never from how the variable is used afterward — `var batch = FundsLedger.<CashEntry>emptyBatch();` fixes `batch` as `List<CashEntry>` for the rest of its scope regardless of what you do with it next. `var x = null;` is illegal (`cannot infer type for local variable x`, `variable initializer is 'null'` — confirmed on this build), and `var` is flatly banned on fields, method parameters and return types; it is a local-variable-only feature. One interaction worth a single line here because it bites in exactly this file's territory: `var` on a read through a wildcard-typed reference infers the *captured* type (the wildcard's upper bound when it declares one, `Object` otherwise), not the wildcard itself — `01b-variance-and-wildcards.md` owns that capture mechanism; this file only flags that `var` does not make the wildcard disappear, it just hides the capture variable's synthetic name.

### 1.5 Conditional expressions

Since Java 8, a conditional expression (`cond ? a : b`) sitting in an assignment or invocation context can be a *poly expression* — its type is not computed from its own operands first, it is computed from the target type it is being poured into, the same way a diamond or a lambda is. A *standalone* conditional (one not sitting in such a context — inside a `println`, say) still falls back to the older combined-operand-type rules, and that fallback is exactly where unwanted (un)boxing sneaks in, because the classic operand-type computation for `int ? Integer : int`-shaped conditionals unboxes and can throw `NullPointerException` on a `null` boxed operand at runtime with no compile-time warning. This file does not re-derive that table or that boxing sequence — `../primitives-and-conversions/02c-conditional-operator.md` owns the ternary's full typing rules, and `../primitives-and-conversions/03a-promotion-boxing-and-inference.md` owns numeric promotion and boxing specifically inside inference contexts.

**Interview:** "why did my generic call need an explicit type argument in old code but not now?" — because Java 8 added target typing to generic method inference (JSR 335); before that, a generic method's return type could not be inferred through an assignment context reached via a nested call, only through its own arguments.

The one sentence to keep: inference is a compile-time constraint solve over the type-checking of an entire expression, and it never consults a runtime value — an inference failure is always fixed by telling the compiler *more*, never by casting a value at runtime to make it true.

> Type inference is `javac` solving a system of type constraints over an expression's static shape and its surrounding target type — never over anything that exists only at runtime.

## 2. Reading an inference failure, and reaching for the type witness (2.7.12)

### Why it exists

Constraint solving can fail two different ways that look similar to a reader but need different fixes: the solver can find *no* type that satisfies every constraint (a genuine conflict between call sites), or it can find *some* type but not the one you needed because nothing in the call pinned it down (an underdetermined call). Both surface as a compile error at the call site, not at the place the real mistake was made, which is why these diagnostics read as unhelpful until you know what to look for.

### The mechanism

**Genuine conflict — "incompatible bounds."** Two arguments to the same generic method impose two different concrete requirements on the same type variable:

```java
static <T> List<T> emptyBatch() { return new ArrayList<>(); }
static <T> void postExactly(List<T> batch, T sample) {}

void run() {
    postExactly(Overload1Demo.<BonusEntry>emptyBatch(), new CashEntry(UUID.randomUUID(), null));
}
```

```
error: method postExactly in class Infer3 cannot be applied to given types;
  required: List<T>,T
  found:    List<BonusEntry>,CashEntry
  reason: inference variable T has incompatible bounds
    equality constraints: BonusEntry
    lower bounds: CashEntry
  where T is a type-variable:
    T extends Object declared in method <T>postExactly(List<T>,T)
```

Read it as the solver reporting its own working: the first argument (an explicit witness, `<BonusEntry>emptyBatch()`) forced an *equality* constraint `T = BonusEntry`; the second argument forced a *lower bound* constraint `T ⊇ CashEntry` (T has to be assignable from whatever you pass). `BonusEntry` and `CashEntry` are siblings under `LedgerEntry`, not one another, so no single `T` satisfies both — the fix is to find which of the two call sites actually supplied the wrong constraint and correct it, not to guess a cast on the result.

**Underdetermined call — no target flows through.** A bare generic factory assigned to `var` gets no help from context, because `var`'s own inference runs first and fixes the type before the value is used anywhere else:

```java
static <T> List<T> emptyBatch() { return new ArrayList<>(); }
static void postBatch(List<CashEntry> batch) { }

void run() {
    var batch = emptyBatch();     // no target type available here — infers List<Object>
    postBatch(batch);
}
```

```
error: incompatible types: List<Object> cannot be converted to List<CashEntry>
```

`var` swallowed the target type that `postBatch(emptyBatch())` (single expression, no intermediate variable) would have supplied for free.

**The fix — the explicit type witness.** Supply the type argument the solver was missing, at the call: `ClassName.<T>method(args)`, or, on an instance call, `receiver.<T>method(args)`:

```java
void run() {
    var batch = Infer7b.<CashEntry>emptyBatch();     // now List<CashEntry> from the witness
    postBatch(batch);
    postBatch(Infer7b.<CashEntry>emptyBatch());       // or skip the local entirely
}
```

Both lines compile clean. The receiver-qualified form matters once the method is an instance method rather than static — `this.<CashEntry>emptyBatch()` — the witness always sits immediately before the method name, never before the receiver.

| Witness form | Form | When you reach for it |
|---|---|---|
| Static, own class | `FundsLedger.<CashEntry>emptyBatch()` | a static generic factory whose result feeds a `var` or an unconstrained context |
| Static, JDK method | `Collections.<CashEntry>emptyList()` | same, on a library factory instead of your own |
| Instance, explicit receiver | `this.<T>postExactly(batch, sample)` | an instance generic method called where `this` would otherwise be implicit |

`01-basics.md` introduces the witness's syntax as part of the generic method declaration form; this file's job is recognising *when* the solver needs one from the shape of its own error text.

**Insight:** the two bound lines the compiler prints (`equality constraints:`, `lower bounds:`) are literally naming which call site contributed which constraint — treat them as a worked proof of the conflict, not as noise to skip past.

> An inference failure is the constraint solver reporting either a genuine conflict between two call sites or a call site with not enough information; a type witness resolves the second kind by supplying the missing constraint directly.

## 3. The erased overload clash (2.7.13)

**Pitfall:** the wrong belief is "I can overload the same method name once per parameterisation, the same way I can overload it once per type" — `post(List<CashEntry>)` and `post(List<BonusEntry>)` feel like two different signatures because they read differently. The symptom is a compile error at the *declaration*, not the call site, and it fires even though every call in the program would have been perfectly unambiguous. The fix is one of the three workarounds below, chosen for how the two lists need to be told apart at the call site.

### Why it exists

Overload resolution is documented as choosing among candidate methods by their erased descriptors (JLS §15.12.2's three phases run on the erased applicable set; `../inheritance-and-dispatch/01a-overload-resolution-and-dispatch.md` owns that resolution algorithm in full — the one fact this file needs from it is that resolution is on *erased* descriptors, not declared generic ones). A class file has exactly one method entry per erased descriptor; two source declarations that erase to the same descriptor are, as far as the class file format is concerned, the same method declared twice, and `javac` rejects that at compile time rather than letting the class file writer silently drop one.

### The mechanism

```java
class Overload0 {
    static void post(List<CashEntry> batch) { }
    static void post(List<BonusEntry> batch) { }
}
```

```
error: name clash: post(List<BonusEntry>) and post(List<CashEntry>) have the same erasure
```

Erasure replaces `List<CashEntry>` and `List<BonusEntry>` with the same raw `List`, so both declarations reduce to `post(List)` — one slot, two claimants. No diagram: the manifest assigns this section none; the compiler's own diagnostic above is the picture — it is naming the exact collision. The bytecode-level reason (the class file's method table keyed by name-and-descriptor, and why the `Signature` attribute that preserves the generic form cannot rescue this) is `03d-internals-erasure-limits-and-capture.md`'s territory; this file stops at the rule and the workaround.

| Workaround | Form | Trade-off |
|---|---|---|
| Rename | `postCash(List<CashEntry>)`, `postBonus(List<BonusEntry>)` | Clearest at the call site; loses the "same operation, different type" framing entirely |
| Distinguishing extra parameter | `<T extends LedgerEntry> void postTyped(List<T> batch, Class<T> type)` | One method, one call shape; caller must supply a redundant-looking token (`02a-type-tokens-and-generic-reflection.md` owns `Class<T>` tokens) |
| Wildcard parameter, dispatch inside | `void postAny(List<? extends LedgerEntry> batch)`, `switch` or `instanceof` on each element | One overload total; loses static type-checking of which concrete entry type is actually inside |

```java
static void postCash(List<CashEntry> batch) { }
static void postBonus(List<BonusEntry> batch) { }

static <T extends LedgerEntry> void postTyped(List<T> batch, Class<T> type) { }

static void postAny(List<? extends LedgerEntry> batch) {
    for (LedgerEntry e : batch) {
        System.out.println(e);
    }
}
```

All three declarations coexist and compile clean in one class — confirmed on this build — because none of their erased descriptors collide with each other.

**Gotcha:** the same clash fires across overloaded functional-interface parameters too, not just plain generic ones — `handle(Consumer<CashEntry>)` and `handle(Consumer<Object>)` in the same class is the identical `name clash` diagnostic, for the identical reason, before you ever get as far as writing a lambda that would call either one.

> Two method declarations that erase to the same descriptor are one method as far as the class file is concerned, so `javac` refuses to compile both, no matter how different their declared type arguments look in source.

## 4. What a generic class cannot do (2.7.14)

| Prohibition | Compiles? | Why |
|---|---|---|
| A `static` member typed by the class's own type parameter | No | one class file, one static field, but every parameterisation needs its own value |
| `class X<T> extends Throwable` (or any `Throwable` subtype) | No | `catch` matches against the runtime exception table, which needs a reifiable class |
| `catch (T e)` where `T` is a type variable | No | same reifiability requirement, applied to the catch clause itself |
| `throw t` where `t : T` | Yes, if the enclosing method declares `throws T` | `throws` is a compile-time declaration, not a runtime match |

`[PROVE]`

**1. No static member using the class's type parameter.** `class Repository<T> { static T last; }` gives:

```
error: non-static type variable T cannot be referenced from a static context
```

Work through why, rather than taking it as a rule: a type parameter is resolved once per *instantiation* — `Repository<CashEntry>` and `Repository<BonusEntry>` are, at the source level, two different "shapes" of the class. But erasure means there is exactly one `.class` file for `Repository` at runtime, and a `static` field lives on the class object itself, shared by every use of that class regardless of which `T` a caller had in mind (`01a-erasure-and-its-consequences.md` states this "static fields are shared across parameterisations" consequence in full). If `static T last;` compiled, a `CashEntry` written through `Repository<CashEntry>` and a `BonusEntry` written through `Repository<BonusEntry>` would have to occupy the same single field simultaneously — there is no way to make that safe, so the language refuses the declaration outright rather than let it compile into something that only fails at a `checkcast` later.

**Insight:** a *static generic method* is perfectly legal on the same class — `static <U> U identity(U value) { return value; }` compiled clean, no error, no warning. The type parameter there is the *method's* own, freshly bound at each call site, not the enclosing class's; it does not need an instantiation of the enclosing class to exist at all. The prohibition is about whose type parameter it is, not about the word `static` next to a type variable in general — this is the exact distinction interviewers use this leaf to probe.

**2. A generic class cannot extend `Throwable`, and a type variable cannot be thrown or caught.** Three separate forms, three separate diagnostics, same underlying reason:

```java
class LedgerException<T> extends RuntimeException { }
```

```
error: a generic class may not extend java.lang.Throwable
```

```java
class Retryable<T extends Exception> {
    void run() {
        try {
            System.out.println("stake reserved");
        } catch (T e) {
            System.out.println(e);
        }
    }
}
```

```
error: unexpected type
  required: class
  found:    type parameter T
```

The mechanism behind both: a `catch` clause is matched at runtime against the exception table attribute in the class file, which records reifiable class entries the JVM can compare a thrown object's actual class against directly. An erased type variable has no reifiable identity of its own at that comparison point — by the time the exception table is consulted, "`T`" has already vanished into whatever its erasure was, and there is no way to ask "is this a `T`" at the point a real exception is in flight. Rather than let that fail unpredictably at runtime, the language forbids both the class-level form (a generic `Throwable` subtype would mean every `catch` of it faces this exact problem) and the catch-clause form up front, at compile time (`../exceptions/03-internals-exception-mechanics.md` owns the exception table's structure in full — a concurrent batch in this note set; the path is stable even where the file is still being written).

**3. What is allowed and looks like it should not be: `throws T`.** A generic method may declare `throws T` where `T extends Throwable`-ish (here, `Exception`), and inside it, `throw` a value of that type variable — this compiled with no error on this build:

```java
class Rethrow<T extends Exception> {
    void run(T t) throws T {
        throw t;
    }
}
```

The reason it is legal where `catch (T e)` is not: `throws` is a compile-time-only declaration on the method's signature — it tells callers what checked-exception obligation they take on, and it is enforced entirely by the compiler comparing declared types, never by a runtime match against an exception table entry. `throw t;` at runtime just throws whatever concrete object `t` actually holds — the JVM's `athrow` instruction does not care what static type the source called it, only what the object's real class is. This is the entire basis of the "sneaky throw" idiom (using `throws T` with `T` inferred as an unchecked type to throw a checked exception without declaring it) — a compile-time-only rule, deliberately exploited, and worth recognising by name if it comes up, though building the full idiom is out of this file's scope.

> A generic class's type parameter exists per instantiation but the class file and its static state do not, and `catch`/`extends Throwable` need a reifiable class the erased type variable cannot supply — `throws` and `throw` on a type variable are exempt because they are compile-time-only.

## 5. `instanceof` with generics — and pattern matching does not change it (2.7.15)

**Pitfall:** the wrong belief, common specifically since Java 21's pattern matching landed, is "pattern matching finally lets the JVM check generic types at runtime, so `instanceof List<Money>` should work now." The symptom is a compile error, identically worded in the old `instanceof` form and the new pattern form, because pattern matching for `instanceof` and `switch` is desugared to the same reifiability check the classic form always used — no new runtime type information was added anywhere. The fix is either an unbounded wildcard (test the container, not its argument) or a record deconstruction pattern, where what looks like a generic type test is actually a type *inference*, not a test — a real distinction with a real compile-time boundary, shown below.

### Why it exists

`instanceof` (and any pattern built on it) is required to be checkable by a single runtime class comparison — the type it tests must be *reifiable* (`01a-erasure-and-its-consequences.md` owns the exact reifiable-type enumeration; the short form is: raw types, unbounded wildcards, arrays of reifiable types, and non-generic types qualify, a parameterised type with a concrete or bounded argument does not). `List<Money>` is erased to `List` at runtime — there is no way to ask a `List` instance "were you populated as a `List<Money>`," because that fact was never recorded on the object, only in the `Signature` attribute of whatever variable declared it, which reflection can read but a runtime `instanceof` check cannot.

### The mechanism

```java
void check(Object o) {
    if (o instanceof List<Money>) { }
}
```

```
error: Object cannot be safely cast to List<Money>
```

Java 21's pattern-matching `switch` desugars to the identical check and gives the identical diagnostic:

```java
String describe(Object o) {
    return switch (o) {
        case List<Money> l -> "money list " + l.size();
        default -> "other";
    };
}
```

```
error: Object cannot be safely cast to List<Money>
```

No diagram: the manifest assigns this section none — the two identical diagnostics above, from the pre-pattern-matching form and the Java 21 pattern form, are the evidence pattern matching changed nothing about reifiability. What does compile — both as a plain `instanceof` pattern and inside a `switch` — is the unbounded wildcard, because `List<?>` is on the reifiable list:

```java
if (o instanceof List<?> l) {
    System.out.println("size " + l.size());
}
```

That compiled clean, no warning.

Sealed hierarchies and `switch` exhaustiveness over them are guide `04 Modern Java`'s territory, not this file's; the point here stops at what a single pattern is and is not allowed to test.

`[RESEARCH]` The case actually worth verifying rather than assuming: a **record deconstruction pattern** over a *generic* record, where the record's own type argument is left unspecified. Compiled and run on this build:

```java
record Holder<T>(T value) { }

static String describe(Object o) {
    return switch (o) {
        case Holder(Money m) -> "holder of money " + m.amount();
        case Holder(Object v) -> "holder of other: " + v;
        default -> "other";
    };
}
```

This compiles with **no error and no unchecked warning**, and running it against `new Holder<>(new Money(new BigDecimal("3.33"), Currency.getInstance("USD")))` prints `holder of money 3.33`, while a `new Holder<>("not money")` falls to the second case and prints `holder of other: not money` — confirmed by executing both on JDK 21.0.7. What is happening is not a test of `Holder`'s type argument at all: `Holder` itself is matched as a raw-compatible reifiable type, and the *nested* pattern `Money m` is what actually runs a `checkcast`-equivalent test on the extracted `value()` component at runtime, exactly the same reifiable-type check any other `instanceof Money` would run. The record's type argument `T` is never tested — it is *inferred* to be whatever makes the nested pattern's declared type consistent, and the two cases behave as ordinary sequential type tests on the component, not as a generic-type test on the container. Writing `case Holder<Money> h` directly (testing the container's argument, not a component) reproduces the same `cannot be safely cast` error as the flat `List<Money>` case above — confirmed on this build. The distinction that matters: *testing* a type argument on the container is impossible everywhere in the language; *inferring* one from a nested pattern's own reifiable test is allowed, because the thing actually being checked at runtime is the component, never the container's erased type argument.

**Interview:** "does pattern matching let you check generics at runtime in Java 21?" — no; a pattern's type check still has to be reifiable, and a record deconstruction pattern only *looks* like it tests the outer generic argument because the nested pattern is quietly testing the extracted component instead.

> `instanceof` and every pattern built on it require a reifiable type to test against; a parameterised type with a concrete or bounded argument never qualifies, and a record pattern that appears to test one is actually testing a component through a nested pattern, not the container's erased type argument.

## Pitfalls

### You can overload a method once per generic parameterisation, since the type arguments are obviously different

**Wrong**

```java
class Overload0 {
    static void post(List<CashEntry> batch) { }
    static void post(List<BonusEntry> batch) { }
}
```

```
error: name clash: post(List<BonusEntry>) and post(List<CashEntry>) have the same erasure
```

**Right**

```java
class Overload0Fixed {
    static void postCash(List<CashEntry> batch) { }
    static void postBonus(List<BonusEntry> batch) { }
}
```

Renaming (or the `Class<T>`-token / wildcard-and-dispatch alternatives in §3) sidesteps the collision because the two descriptors are no longer identical after erasure.

**Why people believe it:** the declared signatures read as unmistakably different in source, and nothing about writing them side by side hints that the compiler ever throws the type arguments away before comparing them.

### Java 21's pattern matching finally lets `instanceof` check a generic type argument at runtime

**Wrong**

```java
String describe(Object o) {
    return switch (o) {
        case List<Money> l -> "money list " + l.size();
        default -> "other";
    };
}
```

```
error: Object cannot be safely cast to List<Money>
```

**Right**

```java
String describe(Object o) {
    return switch (o) {
        case List<?> l -> "list of size " + l.size();
        default -> "other";
    };
}
```

Test the container with an unbounded wildcard, then check individual elements with their own `instanceof` if you need to know what is inside; no pattern shape makes the container's own type argument reifiable.

**Why people believe it:** pattern matching is genuinely new capability in the language, and "generics are erased" reads like exactly the kind of old limitation new language features tend to remove — but erasure is unaffected by pattern matching, only the syntax for writing a test is.

### `var` can infer a lambda's type the same way it infers anything else, since it just reads the initialiser

**Wrong**

```java
void run() {
    var fn = (CashEntry c) -> c.amount();
}
```

```
error: cannot infer type for local variable fn
  (lambda expression needs an explicit target-type)
```

**Right**

```java
void run() {
    Function<CashEntry, Money> fn = c -> c.amount();
}
```

Give the lambda a named functional-interface target and let the lambda's own parameter types be inferred from that, rather than asking `var` to invent a type for an expression that has none of its own.

**Why people believe it:** `var` is advertised as "infer from the initialiser," and a lambda is an initialiser expression like any other — the fact that a lambda specifically carries no denotable type of its own is a special case that only bites the first time you try it.

### A generic store can cache its "last written entry" once, in a static field typed by the class's own type parameter

**Wrong**

```java
class Repository<T> {
    static T last;
}
```

```
error: non-static type variable T cannot be referenced from a static context
```

**Right**

```java
class Repository<T> {
    T last;

    void save(T entry) {
        this.last = entry;
    }
}
```

Make it an instance field, one per `Repository` instance, since each instance is already committed to a single `T` at construction — or, if a genuinely shared cache across all parameterisations is intended, key it explicitly by `Class<?>` rather than by the erased, shared static slot.

**Why people believe it:** `static` fields are the natural place to put "one value, shared everywhere," and nothing about declaring `T` at the class level signals that a `static` member sits outside every instantiation's own `T`.

## Cheat sheet

| Situation | Rule | One-line fix |
|---|---|---|
| Diamond `<>` | infers from assignment/argument target type | n/a — `01-basics.md` |
| Generic method call, target underdetermined | Java 8+ infers from surrounding target too | explicit witness `Class.<T>method()` |
| Lambda / method reference | takes type from functional-interface context, never has one of its own | give it a named target type, not `var` |
| `var` | infers once, from the initialiser only | never on fields/params/returns; never with `null` |
| Conditional expression | poly in assignment/invocation context, else standalone | see `../primitives-and-conversions/02c-conditional-operator.md` |
| `T inference variable has incompatible bounds` | two call sites forced two different concrete types | find and fix the conflicting call site |
| `List<Object> cannot be converted to List<X>` | underdetermined call defaulted, usually via `var` | supply the witness or drop the intermediate `var` |
| Two methods differing only by type argument | same erased descriptor, one class-file slot | rename, `Class<T>` token, or wildcard + dispatch |
| `static T field;` on a generic class | one class file, one static slot, many `T`s | instance field, or a static *generic method* instead |
| `class X<T> extends Throwable`, `catch (T e)` | `catch` needs a reifiable exception-table entry | catch a concrete `Throwable` subtype |
| `throws T` / `throw t` where `T extends Exception` | legal — compile-time-only declaration | — |
| `instanceof List<Money>` | parameterised type is not reifiable | `instanceof List<?>` then check elements |
| `case Holder(Money m) ->` on `Holder<T>` | nested pattern infers T by testing the component | not a test of the container's own type argument |

## Self-test

**Q1.** Why does `postBatch(FundsLedger.<CashEntry>emptyBatch())` need a type witness in some call shapes but not others?

<details><summary>Answer</summary>

It needs one exactly when nothing else in the expression pins down the generic method's type variable — if the result is passed straight into `postBatch(List<CashEntry>)` in one expression, the target type flows in for free and no witness is needed. If the result is first assigned to a `var` local, `var`'s own inference runs first with no target type available, defaults to `Object`, and the witness has to be supplied explicitly at the factory call to fix the type before it ever reaches `var`.

</details>

**Q2.** What do the "equality constraints" and "lower bounds" lines in an "incompatible bounds" error actually tell you?

<details><summary>Answer</summary>

They name, literally, which call-site argument contributed which kind of constraint on the same inference variable — an equality constraint typically comes from an explicit type witness or a return-type context, a lower bound comes from an ordinary argument whose type has to be assignable to the variable. When the two disagree, that is the compiler showing its own working: which two call sites are actually in conflict, so you know which one to fix rather than guessing.

</details>

**Q3.** Why can two methods with signatures `post(List<CashEntry>)` and `post(List<BonusEntry>)` not coexist in one class?

<details><summary>Answer</summary>

Overload resolution and the class file's method table both operate on erased descriptors — `List<CashEntry>` and `List<BonusEntry>` both erase to raw `List`, so both declarations reduce to the identical descriptor `post(List)`. A class file has exactly one method entry per name-and-descriptor pair, so the compiler rejects the second declaration as a name clash rather than silently keeping only one.

</details>

**Q4.** Give one situation where overloading two generic-looking methods is fine and does not trip the erasure clash.

<details><summary>Answer</summary>

Any pair whose erased descriptors genuinely differ — different erased parameter types (`List` vs `Set`), different arity, or a distinguishing extra parameter like `Class<T>` in `postTyped(List<T>, Class<T>)`. The clash only fires when the two declarations erase to the exact same descriptor.

</details>

**Q5.** Why is `static T last;` illegal on `class Repository<T>` but `static <U> U identity(U value)` on the same class is fine?

<details><summary>Answer</summary>

`static T last;` refers to the *class's* type parameter, and a static field lives on the single shared class object regardless of which parameterisation created any given instance — there is exactly one slot but potentially many different `T`s in use at once, which is unsound. `static <U> U identity(U value)` declares its own, fresh type parameter scoped to that one method call; it never needs an instantiation of `Repository` to exist and carries no shared state, so nothing is aliased across parameterisations.

</details>

**Q6.** Why can a generic method declare `throws T` and throw a value of type `T`, when `catch (T e)` is illegal?

<details><summary>Answer</summary>

`throws` is a compile-time-only declaration checked by comparing static types at the call site; nothing about it requires a runtime match. `throw t;` at runtime just throws whatever concrete object `t` holds — the JVM's throw instruction dispatches on the object's real class, not on the static type the source used to name it. `catch (T e)`, by contrast, requires the runtime exception-handling machinery to match a thrown object's class against the catch clause's declared type via the exception table, and an erased type variable has no reifiable identity left at that point to match against.

</details>

**Q7.** Does Java 21's pattern matching let `instanceof` test a parameterised type like `List<Money>`? What about a record pattern like `case Holder(Money m)` on a generic `Holder<T>`?

<details><summary>Answer</summary>

No on the first — pattern matching is new syntax over the same reifiability requirement `instanceof` always had; `List<Money>` is still erased to `List` at runtime and still fails to compile with "cannot be safely cast," identically worded to the pre-pattern-matching form. The record pattern compiles, but it is not testing `Holder`'s type argument at all — the nested pattern `Money m` runs an ordinary reifiable test on the extracted `value()` component, and `T` is inferred to be consistent with that, never checked against the container directly. Writing `case Holder<Money> h` instead — testing the container's own type argument — fails with the identical "cannot be safely cast" error.

</details>

## Open questions

None — the one place this file could not construct direct evidence (whether a literal pre-Java-8 `javac` binary would reject the nested generic-factory call in §1.2) is stated inline as a tooling limitation with the reason (`--release` does not roll back the inference algorithm, and JDK 21 no longer accepts `--release 7`), not left as an unverified claim.

---

**Leaves covered:** 2.7.11, 2.7.12, 2.7.13, 2.7.14, 2.7.15 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 558
