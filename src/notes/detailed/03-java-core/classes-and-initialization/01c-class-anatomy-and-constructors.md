# 03 Java Core — Class anatomy and constructors — BASICS (§1.13, 1.13.1–1.13.5, 1.13.17)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The initialization order of a `new`](01b-initialization-order.md) · Next: [Class initialization triggers and failure](01d-class-initialization-triggers.md)

You already know how to declare a class, a field, a method and a constructor. What this file supplies is the layer underneath the syntax you type every day: the grammar productions that fix the *order* of a declaration's parts and what a wrong order actually does; the fact that a `throws` clause exists only for the compiler and survives into the class file as an attribute the JVM does not enforce; the fact that a varargs parameter is an array parameter plus one flag bit; the all-or-nothing rule that deletes the implicit no-argument constructor the moment you declare any constructor at all; and the four-release story by which Java's oldest and most absolute rule — that `super` or `this` must come first — stopped being absolute. That last one is the file's centre of gravity, because JEP 513 exists to close the exact trap walked frame by frame in `01b-initialization-order.md`.

## 1. Constructors, and the implicit no-arg constructor that vanishes (1.13.4)

Picture the implicit no-argument constructor as a courtesy the compiler extends to classes that ask for nothing. Declare a single constructor of any shape — one parameter, `private`, generic, whatever — and the courtesy is withdrawn silently, in full, with no warning and no diagnostic, because from the compiler's point of view you have taken over the job.

### Why it exists

A class with no state and no invariants should not have to write `Application() { }` to be instantiable, so JLS §8.8.9 supplies one. But a class that declares *any* constructor is asserting that it has instantiation requirements, and continuing to hand out a no-argument back door would let callers bypass exactly the invariant the declared constructor exists to establish. Consider what the alternative would mean for QuizStakes: if adding `Application(ApplicationId id)` left the no-argument form in place, every reflective and every careless caller could still produce an `Application` with a `null` id, and the constructor's `requireNonNull` would be decoration. All-or-nothing is the only rule that is both simple and safe.

### The mechanism

`[SOURCE]` JLS 21 §8.8.9, verbatim:

> "If a class contains no constructor declarations, then a default constructor is implicitly declared. […] The default constructor has the same access modifier as the class, unless the class lacks an access modifier, in which case the default constructor has package access (§6.6). The default constructor has no formal parameters, except in a non-private inner member class, where the default constructor implicitly declares one formal parameter representing the immediately enclosing instance of the class […] The default constructor has no throws clause. If the class being declared is the primordial class `Object`, then the default constructor has an empty body. Otherwise, the default constructor simply invokes the superclass constructor with no arguments."

Four consequences, each a separate interview answer:

| Clause | Consequence |
|---|---|
| "contains **no** constructor declarations" | One declared constructor of any shape removes the default entirely. Not "adds to", removes |
| "same access modifier as the class" | A `public` class gets a `public` default; a package-private class gets a package-private one. So `public class` plus no constructors is instantiable from anywhere, and declaring `private Application() { }` is the idiom for a non-instantiable utility class (§8.8.10) |
| "no formal parameters, except in a non-private inner member class" | A non-`static` nested class's default constructor takes a hidden enclosing-instance parameter, which is why an inner class cannot be instantiated without an outer instance. `../inheritance-and-dispatch/02-nested-classes.md` owns the `this$0` mechanics |
| "no `throws` clause" | Plus §8.8.9's closing rule: "It is a compile-time error if a default constructor is implicitly declared but the superclass does not have an accessible constructor that takes no arguments and has no `throws` clause" — so a superclass with only throwing or argument-taking constructors forces every subclass to declare its own |

Two more mechanism facts that belong here rather than in the quote. First, a constructor has **no return type** — not `void`, none at all — and writing one turns the declaration into an ordinary method that merely happens to share the class's name, which compiles cleanly and then never runs, a genuine and very quiet bug. Second, `javac` names every constructor `<init>` in the class file; the name is not a legal Java identifier, which is why no ordinary method can collide with it, and it is the name you see in the stack traces walked in `01b-initialization-order.md`.

Beat 4 does not apply: this leaf has no diagram, because the mechanism is a single presence-or-absence rule with nothing sequential to trace.

```java
// Before: no declared constructor, so javac supplies `public Application() { super(); }`.
// Jackson, JPA and any reflective mapper can instantiate it.
public class Application {
    private ApplicationId id;
    private StatusCode status;

    public void setId(ApplicationId id) {
        this.id = id;
    }

    public ApplicationId getId() {
        return id;
    }

    public void setStatus(StatusCode status) {
        this.status = status;
    }

    public StatusCode getStatus() {
        return status;
    }
}
```

```java
// After: one constructor added to enforce "an Application always has an id".
// The implicit no-arg constructor is now GONE. Every reflective
// newInstance() path that relied on it fails at runtime, not at compile time.
public class Application {
    private final ApplicationId id;
    private StatusCode status;

    public Application(ApplicationId id) {
        this.id = Objects.requireNonNull(id, "id");
        this.status = new StatusCode("AO", 100, 0, "IDENTITY_CREATED");
    }

    public ApplicationId getId() {
        return id;
    }

    public StatusCode getStatus() {
        return status;
    }

    public void setStatus(StatusCode status) {
        this.status = status;
    }
}
```

**Pitfall:** the wrong belief is "adding a constructor is a source-compatible, behaviour-preserving change." The symptom is that *nothing at all* goes wrong at compile time — the change compiles cleanly, unit tests that call `new Application(id)` pass — and then a deserialization, JPA hydration or bean-instantiation path fails at runtime with a "no suitable constructor found" or `InstantiationException`, often in a different module, often only in the environment that exercises that path. The fix depends on why the class is being reflected: for JPA, declare an explicit `protected Application() { }` alongside the real one (the specification requires a no-argument constructor); for Jackson, annotate the real constructor with `@JsonCreator` and its parameters with `@JsonProperty`, or register the parameter-names module, rather than reintroducing a no-argument constructor that lets an `Application` exist without an id. The structural fix is better than either: model it as a `record`, whose canonical constructor is the only way in and whose deserialization support is constructor-based by design — 1.13.17 below.

> **Definition.** A constructor has no return type and shares its class's name; if and only if a class declares no constructor at all, the compiler implicitly declares a no-argument one with the class's own access modifier, no `throws` clause, and a body that invokes the superclass's no-argument constructor.

## 2. `super` and `this` constructor invocations must come first — and the Java 25 relaxation (1.13.5)

Picture the constructor body on Java 21 as having a locked first slot: either you put an explicit `super` or `this` invocation in it, or the compiler puts an implicit `super()` there for you. Nothing else can go in that slot — not a validation, not an assignment, not a `System.out.println`. Java 25 unlocks the slot: everything before the invocation becomes a named region, the *prologue*, with its own rule — it may compute, validate, throw, and assign your own initialiser-less fields, but it may not *use* the object.

### Why it exists — and the state of play on Java 21

**On Java 21, your target, the rule holds without exception.**

`[SOURCE]` JLS 21 §8.8.7 states it and gives the grammar:

> "The first statement of a constructor body may be an explicit invocation of another constructor of the same class or of the direct superclass (§8.8.7.1).
> `ConstructorBody: { [ExplicitConstructorInvocation] [BlockStatements] }`"

The grammar is the enforcement: `ExplicitConstructorInvocation` is optional but, when present, is positioned *before* `BlockStatements`, so there is no production that derives a statement ahead of it. And §8.8.7 continues: "If a constructor body does not begin with an explicit constructor invocation and the constructor being declared is not part of the primordial class `Object`, then the constructor body implicitly begins with a superclass constructor invocation `super();`" — which is why every class has a superclass constructor call whether its author wrote one or not, and why the construction chain in `01b-initialization-order.md` always reaches `Object`.

The rule exists to guarantee superclass-before-subclass ordering by the cheapest possible means: a purely syntactic check, no flow analysis, no escape analysis, no whole-program reasoning. It is also — as JEP 513 puts it — "simplistic", because it forbids a great deal of code that is perfectly safe. §8.8.7 also fixes two smaller rules worth carrying: it is "a compile-time error for a constructor to directly or indirectly invoke itself through a series of one or more explicit constructor invocations involving `this`", so a `this` delegation cycle is caught at compile time rather than blowing the stack; and a bare `return` is legal in a constructor body while `return e` is not, since a constructor has no return type at all.

### The mechanism, and what changed

`[RESEARCH]` `[VERSION-TRAP]` The feature went through three previews under two different titles before finalising. All four JEPs fetched from `openjdk.org/jeps`, all four `Status: Closed / Delivered`:

| JEP | Exact title | Release |
|---|---|---|
| 447 | Statements before super(…) (Preview) | 22 |
| 482 | Flexible Constructor Bodies (Second Preview) | 23 |
| 492 | Flexible Constructor Bodies (Third Preview) | 24 |
| 513 | **Flexible Constructor Bodies** (final, no preview suffix) | 25 |

The rename between 447 and 482 is the version trap in miniature: search for the old title and you find preview-era material describing a narrower feature; search for the new one and you find the finalised form. JEP 513's own History section confirms the chain: "Flexible constructor bodies were first proposed as a preview feature by JEP 447 (JDK 22), under a different title. They were revised and re-previewed by JEP 482 (JDK 23) and then previewed again, without change, by JEP 492 (JDK 24). We here propose to finalize the feature in JDK 25, without change."

`[SOURCE]` JEP 513's Summary, verbatim except that the JEP writes the two invocation forms with elided parenthesised argument lists, rendered here as `super(arguments)` and `this(arguments)`:

> "In the body of a constructor, allow statements to appear before an explicit constructor invocation, i.e., `super(arguments)` or `this(arguments)`. Such statements cannot reference the object under construction, but they can initialize its fields and perform other safe computations. This change allows many constructors to be expressed more naturally. It also allows fields to be initialized before they become visible to other code in the class, such as methods called from a superclass constructor, thereby improving safety."

That last clause — "fields to be initialized before they become visible to other code in the class, such as methods called from a superclass constructor" — names the trap this feature exists to fix, and it is worth stating in one self-contained paragraph here because it spans two files. On Java 21, a superclass constructor that calls an overridable method reaches the *subclass's* override (dispatch resolves on the object's runtime class, which is the subclass from the instant of allocation), and it does so during the superclass's step 5, which is reached from inside the subclass's step 3 — before the subclass's step 4 has run a single field initialiser. So every subclass field the override touches still holds its default: `null`, `0`, `false`. A subclass on Java 21 has no way to prevent this, because it cannot put anything before `super`. On Java 25 it can: assign the field in the prologue, then invoke `super`, and the override sees the real value. The frame-by-frame walk of the failure, its stack-trace signature and the three discipline-level fixes are §2 of `01b-initialization-order.md` and are not repeated here.

JEP 513's ordering model, which generalises the five-step procedure: **prologues run bottom-up, then epilogues run top-down.** Four restrictions on a prologue, all from JEP 513's Description:

| Restriction | Detail |
|---|---|
| No use of the instance under construction | Code in an *early construction context* "must not use `this`, either explicitly or implicitly, to refer to the current instance or access fields or invoke methods of the current instance" |
| One exception, narrowly drawn | It "may use simple assignment statements to fields declared in the same class, provided that the declarations of those fields do not have initializers" |
| No `return` | "It is a compile-time error for a `return` statement to appear in the prologue of a constructor body" (a bare `return` remains legal in the epilogue) |
| Throwing is allowed, and is the point | "Throwing an exception in the prologue will be typical in fail-fast scenarios" |

Note how tightly the exception is drawn: assignable only, same class only, and only fields *without* their own initialiser — because a field with an initialiser will be assigned by step 4 anyway, and letting the prologue also write it would create two writes with no defined winner. The revised grammar, from JEP 513:

```
ConstructorBody:
    { [BlockStatements] ExplicitConstructorInvocation [BlockStatements] }
    { [BlockStatements] }
```

Beat 4 does not apply: this leaf has no diagram of its own. The failure it repairs is drawn as D-038 in `01b-initialization-order.md`.

The Java 21 workaround and the Java 25 form it replaces, side by side:

```java
// Java 21: the cap check cannot precede super(), so it is smuggled into an
// argument expression via a static helper. Legal, but the validation is now
// hidden inside a call site and cannot span more than one expression.
final class CappedBankWithdrawal extends WithdrawalTransaction {
    private static final Money DAILY_CAP = Money.gbp("500.00");

    private final PaymentRun run;

    CappedBankWithdrawal(Money amount, PaymentRun run) {
        super(requireWithinCap(amount));
        this.run = run;
    }

    private static Money requireWithinCap(Money amount) {
        if (amount.compareTo(DAILY_CAP) > 0) {
            throw new RestrictedActionException("withdrawal exceeds the bank rail daily cap");
        }
        return amount;
    }

    PaymentRun run() {
        return run;
    }
}
```

```java
// Java 25 (JEP 513): the same class, with the check as an ordinary statement.
// Requires JDK 25 or later; this does not compile on Java 21.
final class CappedBankWithdrawal25 extends WithdrawalTransaction {
    private static final Money DAILY_CAP = Money.gbp("500.00");

    private final PaymentRun run;   // no initialiser, so the prologue may assign it

    CappedBankWithdrawal25(Money amount, PaymentRun run) {
        if (amount.compareTo(DAILY_CAP) > 0) {
            throw new RestrictedActionException("withdrawal exceeds the bank rail daily cap");
        }
        this.run = run;             // assigned BEFORE any superclass code can observe it
        super(amount);
    }

    PaymentRun run() {
        return run;
    }
}
```

The second version is not merely tidier. If `WithdrawalTransaction`'s constructor called an overridable method that read `run`, the Java 21 version would hand it `null` and the Java 25 version would hand it the real `PaymentRun`. The prologue closed the hole. There is also a plain efficiency argument the JEP makes: on Java 21 an invalid amount still runs the entire superclass constructor before anything rejects it, which for a hierarchy that opens resources or writes a ledger row in its constructor is not merely wasted work but work that has to be undone.

**Pitfall:** the prologue's field-assignment exception does not extend to *reads*. `this.run = run;` is legal in a prologue; `if (this.run == null)` is not, and neither is `Objects.requireNonNull(this.run)`, because both use the instance. The restriction is "simple assignment statements to fields declared in the same class", nothing wider — not compound assignment, not a read, not a method call on the instance, not passing `this` anywhere, and not an assignment to an inherited field. The escape hatch has a cost worth naming: a field the prologue assigns must have no initialiser, so you give up the declare-and-initialise-in-one-line form for exactly the fields you most want to protect.

> **Definition.** On Java 21, a constructor body's first statement must be an explicit `super` or `this` invocation, or the compiler inserts an implicit `super()`; from Java 25 (JEP 513, previewed by 447/482/492 in 22/23/24) statements may precede it, forming a prologue that may compute, validate, throw and assign the class's own initialiser-less fields, but may not otherwise use the object under construction.

## Supporting facts

### Class declaration anatomy: the order the grammar mandates (1.13.1)

`[SOURCE]` JLS 21 §8.1's production fixes the order absolutely; nothing here is stylistic:

```
NormalClassDeclaration:
    {ClassModifier} class TypeIdentifier [TypeParameters]
        [ClassExtends] [ClassImplements] [ClassPermits] ClassBody
```

Modifiers, then `class`, then the name, then type parameters, then `extends`, then `implements`, then `permits`, then the body — and a single class may have at most one `extends` clause, any number of interfaces in one `implements` clause, and a `permits` clause only if it is `sealed`. Writing them out of order is a syntax error, not a warning: `sealed interface Verdict permits DocumentVerdict extends Auditable` does not parse, because `ClassPermits` derives after `ClassExtends`. The one that actually bites in practice is type parameters after the name rather than before it — `class Movement<T>` is right, `class <T> Movement` does not parse — which is the mirror image of the method rule in 1.13.3, where the type parameters go *before* the return type. `sealed`/`permits` mechanics and the exhaustiveness they buy are guide **04 Modern Java**, `[X-REF 04]`; `abstract`, `final` and the access modifiers are `02-modifiers.md` and `02a-access-and-other-modifiers.md`.

### Field declarations, instance versus static, and where each initialiser runs (1.13.2)

`[SOURCE]` JLS 21 §8.3: `FieldDeclaration: {FieldModifier} UnannType VariableDeclaratorList ;` where each declarator is `VariableDeclaratorId [= VariableInitializer]`. One declaration can declare several fields — `private Money cash, bonus = Money.gbp("0.00");` gives `cash` no initialiser and `bonus` one, which is exactly why the multi-declarator form is a readability trap worth avoiding. The mechanism that matters is *where the initialiser executes*: an **instance** field's initialiser is compiled into every constructor of the class, at the position corresponding to step 4 of §12.5 — so a class with three constructors has that initialiser's bytecode emitted three times, once per `<init>`, which is why an expensive field initialiser costs per-constructor rather than once, and why a constructor that delegates with `this` skips step 4 entirely (the delegated-to constructor already ran it, and running it twice would double every initialiser's side effects). A **static** field's initialiser is compiled into `<clinit>` instead, unless it is a constant variable, in which case it becomes a `ConstantValue` attribute and no code at all. A field with no initialiser gets its default from allocation, and a blank `final` must be definitely assigned by every constructor — definite assignment and the blank-final rules are `01-basics.md`; the `<clinit>` and `ConstantValue` ordering is `01b-initialization-order.md` §3.

### Method declarations: type-parameter position, `throws`, and what varargs really is (1.13.3)

`[SOURCE]` JLS 21 §8.4: `MethodDeclaration: {MethodModifier} MethodHeader MethodBody`, and `MethodHeader: Result MethodDeclarator [Throws]` or `TypeParameters {Annotation} Result MethodDeclarator [Throws]`. So a generic method's type parameters sit **after** the modifiers and **before** the return type — `public static <T extends LedgerEntry> List<T> post(List<T> entries)` — the opposite side of the name from a class's type parameters, which is the single most common syntax error in hand-written generic methods.

Two erasure facts the reader almost certainly does not have. First, the `throws` clause is a **compile-time-only** construct: `javac` enforces it (a checked exception must be declared or caught), and it survives into the class file only as an `Exceptions` attribute on the method (JVMS 21 §4.7.5) which the JVM does not enforce at all. The consequence is real and reachable: bytecode generated by a library, or a reflective `Method.invoke`, can propagate a checked exception out of a method whose signature does not declare it, and the calling code has no `catch` for it because the compiler proved it impossible. Second, a varargs parameter is **an array parameter plus a flag bit**: `void grant(Money[] amounts)` and a varargs declaration of the same method have the identical erased descriptor, and the only difference in the class file is the `ACC_VARARGS` flag (`0x0080`) on the method, which tells `javac` — at *future* call sites — that it may synthesise the array for the caller. Three consequences follow: you cannot overload a method on varargs-versus-array, because the descriptors collide; every varargs call site allocates an array, which is the allocation measured for `Objects.hash` in `../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`; and passing an existing array straight through performs no copy, so the callee can mutate the caller's array. Class-file encoding of `Exceptions` and `ACC_VARARGS` is `../language-substrate/03a-internals-class-file-format.md`.

### The record compact constructor versus a hand-written canonical constructor (1.13.17)

A record's **canonical constructor** is the one whose signature matches the record header. Declare it in full and you write the field assignments yourself; declare it as a **compact constructor** — the header's parameter list omitted entirely — and the compiler appends `this.bonusPortion = bonusPortion;` and `this.cashPortion = cashPortion;` after whatever you wrote, for every component, in header order. That is the whole contrast: a compact constructor is a *validate-and-normalise* body with the assignments implicit and last; a hand-written canonical constructor is an ordinary constructor with the assignments explicit. `[SOURCE]` JLS 21 §8.10.4 confirms the implicit form's shape: if no canonical constructor is declared at all, the implicitly declared one "initializes each component field of the record class with the corresponding formal parameter […] in the order that record components (corresponding to the component fields) appear in the record header," has "no `throws` clause," and takes the record's access modifier.

```java
record StakeSplit(Money bonusPortion, Money cashPortion) {
    // Compact constructor: no parameter list, no assignments written.
    // The invariant is the reason this record has a body at all.
    StakeSplit {
        Objects.requireNonNull(bonusPortion, "bonusPortion");
        Objects.requireNonNull(cashPortion, "cashPortion");
        if (!bonusPortion.currency().equals(cashPortion.currency())) {
            throw new IllegalArgumentException("split portions must share a currency");
        }
        // Reassigning the PARAMETER normalises what gets stored, because the
        // compiler's assignments run after this body and read the parameters.
        bonusPortion = new Money(
                bonusPortion.amount().setScale(2, RoundingMode.DOWN),
                bonusPortion.currency());
    }

    Money stake() {
        return new Money(
                bonusPortion.amount().add(cashPortion.amount()),
                bonusPortion.currency());
    }
}
```

Two gotchas. First, inside a compact constructor you assign the **parameter**, never `this.bonusPortion` — assigning the field is a compile-time error, and assigning the parameter is the only way to normalise a stored value, precisely because the implicit assignments happen after the body and read the parameters. Second, a compact constructor cannot coexist with a normal canonical constructor in the same record (it is a compile-time error to declare both, since their signatures collide), and a normal canonical constructor that forgets one assignment leaves that component field at its default with no warning — which is the whole argument for preferring the compact form. Note also the contrast with 1.13.4: a record has no implicit no-argument constructor to lose, because the canonical constructor is always present, explicitly or implicitly, so the vanishing-constructor failure mode simply cannot arise. `[X-REF 04]` Record accessors, `equals`/`hashCode`/`toString` generation, serialization, non-canonical constructors delegating to the canonical one, and the interaction with `sealed` hierarchies are guide **04 Modern Java**.

## Pitfalls

### "Adding a constructor is a safe, behaviour-preserving change"

**Wrong**

```java
public class Application {
    private ApplicationId id;

    // Added to enforce "an Application always has an id".
    public Application(ApplicationId id) {
        this.id = Objects.requireNonNull(id, "id");
    }

    public ApplicationId getId() {
        return id;
    }
}

// Elsewhere, a reflective mapper that used to work:
Application hydrated = Application.class.getDeclaredConstructor().newInstance();
// -> java.lang.NoSuchMethodException: Application.<init>()
```

The surprise: the implicit no-argument constructor is not augmented by the new declaration, it is deleted. Per JLS 21 §8.8.9 the default is declared only "if a class contains no constructor declarations." Nothing warns you, the module compiles, and the failure surfaces at runtime in whatever code path reflects — deserialization, JPA hydration, a bean container — possibly only in the environment that exercises it.

**Right**

```java
// Model it as a record: the canonical constructor is the only way in, the
// invariant is enforced in one place, and no no-argument back door ever
// existed for anything to depend on.
public record Application(ApplicationId id, StatusCode status) {
    public Application {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(status, "status");
    }
}
```

```java
// Or, if a framework genuinely requires a no-argument constructor (JPA does),
// declare one explicitly and narrowly rather than relying on the implicit one.
public class Application {
    private ApplicationId id;

    protected Application() {
        // For the persistence provider only. Not part of the public API.
    }

    public Application(ApplicationId id) {
        this.id = Objects.requireNonNull(id, "id");
    }

    public ApplicationId getId() {
        return id;
    }
}
```

**Why people believe it:** in almost every other language and in almost every other Java refactoring, adding a member is additive. This is the one case where declaring something removes something.

### "`super` and `this` must be the first statement — that is just how Java works"

**Wrong**

```java
// The belief: this restriction is absolute and permanent, in every Java version.
final class CappedBankWithdrawal extends WithdrawalTransaction {
    private final PaymentRun run;

    CappedBankWithdrawal(Money amount, PaymentRun run) {
        if (amount.compareTo(Money.gbp("500.00")) > 0) {
            throw new RestrictedActionException("exceeds the bank rail daily cap");
        }
        super(amount);
        this.run = run;
    }

    PaymentRun run() {
        return run;
    }
}
// On Java 21: error: call to super must be first statement in constructor
// On Java 25: compiles, and the validation now runs before any superclass code.
```

The surprise: the restriction was lifted. JEP 447 previewed statements before an explicit constructor invocation in **Java 22**, JEP 482 and JEP 492 re-previewed it in **23** and **24** under the new name Flexible Constructor Bodies, and JEP 513 **finalised it in Java 25** — all four `Closed / Delivered`. Saying "it must always be first" in a 2026 interview dates your knowledge to Java 21.

**Right**

```java
// The portable form, which compiles on 21 and on 25 alike: push the check
// into an argument expression via a static helper, so nothing precedes super().
final class CappedBankWithdrawal extends WithdrawalTransaction {
    private final PaymentRun run;

    CappedBankWithdrawal(Money amount, PaymentRun run) {
        super(requireWithinCap(amount));
        this.run = run;
    }

    private static Money requireWithinCap(Money amount) {
        if (amount.compareTo(Money.gbp("500.00")) > 0) {
            throw new RestrictedActionException("exceeds the bank rail daily cap");
        }
        return amount;
    }

    PaymentRun run() {
        return run;
    }
}
// The precise statement, correct on every version: on Java 21 the rule holds
// without exception; from Java 25, statements may precede the invocation,
// forming the constructor's prologue, which may compute, validate, throw and
// perform simple assignments to fields of the same class that have no
// initialiser - but may not otherwise use the object under construction.
```

**Why people believe it:** it was true, without exception, from Java 1.0 through Java 21 — twenty-five years — and Java 21 is still the dominant LTS in production, so most working code and most written material still reflects it.

### "In a compact constructor you validate and then assign the field"

**Wrong**

```java
record StakeSplit(Money bonusPortion, Money cashPortion) {
    StakeSplit {
        Objects.requireNonNull(bonusPortion, "bonusPortion");
        // Trying to normalise by assigning the FIELD:
        this.bonusPortion = new Money(
                bonusPortion.amount().setScale(2, RoundingMode.DOWN),
                bonusPortion.currency());
    }
}
// error: cannot assign a value to final variable bonusPortion
```

The surprise: the compact constructor has no assignments to write, and the field is not assignable from it at all. The compiler emits `this.bonusPortion = bonusPortion;` for you, *after* your body, reading the parameter — so the field is still unassigned while your body runs, and a `final` field cannot be written by the body and then again by the appended assignment.

**Right**

```java
record StakeSplit(Money bonusPortion, Money cashPortion) {
    StakeSplit {
        Objects.requireNonNull(bonusPortion, "bonusPortion");
        // Reassign the PARAMETER; the compiler's appended assignment reads it.
        bonusPortion = new Money(
                bonusPortion.amount().setScale(2, RoundingMode.DOWN),
                bonusPortion.currency());
    }
}
// new StakeSplit(Money.gbp("0.333"), Money.gbp("3.00"))
//   stores bonusPortion = 0.33 GBP
```

**Why people believe it:** every other constructor they have ever written assigns `this.field = field;`, and the compact form's implicit trailing assignments are invisible in the source — there is nothing on the page to suggest the parameter is the thing to change.

## Cheat sheet

| Item | Value |
|---|---|
| Class declaration order | `{modifier} class Name [TypeParameters] [extends] [implements] [permits] Body` (JLS §8.1) |
| At most one | `extends` clause per class; `permits` only on a `sealed` type |
| Common syntax error | `class <T> Movement` does not parse; `class Movement<T>` does |
| Field declaration | `{modifier} Type declarator {, declarator} ;` — a declarator may or may not carry an initialiser |
| Multi-declarator trap | `private Money cash, bonus = Money.gbp("0.00");` initialises only `bonus` |
| Instance field initialiser | Compiled into **every** constructor, at §12.5 step 4 — emitted once per `<init>` |
| Constructor delegating with `this` | Skips step 4 entirely; the delegated-to constructor already ran the initialisers |
| Static field initialiser | Compiled into `<clinit>`, unless a constant variable, which becomes a `ConstantValue` attribute and no code |
| Method declaration order | `{modifier} [TypeParameters] ReturnType name(params) [throws] Body` (JLS §8.4) |
| Generic method type parameters | **Before** the return type — the mirror image of the class rule |
| `throws` at runtime | Compile-time only; class file keeps an `Exceptions` attribute (JVMS §4.7.5) the JVM does not enforce |
| Consequence | Generated bytecode or `Method.invoke` can propagate an undeclared checked exception |
| Varargs at runtime | An array parameter plus the `ACC_VARARGS` flag (`0x0080`) |
| Varargs consequences | Cannot overload against the array form; every call site allocates an array; a passed-through array is not copied |
| Constructor's class-file name | `<init>` — not a legal Java identifier, so nothing can collide with it |
| Constructor return type | None at all, not `void`; adding one silently makes it an ordinary method |
| Implicit constructor exists iff | The class "contains no constructor declarations" (JLS §8.8.9) — one declared constructor removes it |
| Implicit constructor's shape | Class's own access modifier (package access if the class has none), no formal parameters, no `throws`, body is `super()` |
| Non-private inner member class | Its default constructor takes a hidden enclosing-instance parameter |
| Default-constructor compile error | Implicit default plus a superclass with no accessible no-arg, no-`throws` constructor |
| Non-instantiable class idiom | Declare `private Application() { }` (JLS §8.8.10) |
| Java 21 first-statement rule | Holds without exception. `ConstructorBody: { [ExplicitConstructorInvocation] [BlockStatements] }` (JLS §8.8.7) |
| Implicit `super()` | Inserted whenever a constructor body does not begin with an explicit invocation and the class is not `Object` |
| `this` delegation cycle | Compile-time error, not a stack overflow (JLS §8.8.7) |
| `return` in a constructor | Bare `return` legal; `return e` never legal |
| JEP 447 | Statements before super(…) (Preview) — Java **22** |
| JEP 482 | Flexible Constructor Bodies (Second Preview) — Java **23** |
| JEP 492 | Flexible Constructor Bodies (Third Preview) — Java **24** |
| JEP 513 | Flexible Constructor Bodies — final, Java **25** |
| Java 25 grammar | `{ [BlockStatements] ExplicitConstructorInvocation [BlockStatements] }` — prologue, invocation, epilogue |
| Prologue rules | Must not use the instance; may perform **simple assignments** to same-class fields **without initialisers**; `return` is a compile-time error; throwing is expected |
| Java 25 ordering model | Prologues run bottom-up, then epilogues run top-down |
| What the prologue fixes | The overridable-method-from-a-constructor trap — see `01b-initialization-order.md` §2 |
| Canonical constructor | The one whose signature matches the record header |
| Compact constructor | Parameter list omitted; compiler appends `this.c = c` per component, in header order, **after** your body |
| Normalising in a compact constructor | Assign the **parameter**, never the field — assigning the field is a compile-time error |
| Compact plus normal canonical | Compile-time error to declare both — the signatures collide |
| Records and 1.13.4 | A record can never lose an implicit no-arg constructor, because it never had one |

## Self-test

**Q1.** You add a constructor to a class that previously declared none. What exactly happens to the implicit no-argument constructor, and what is the realistic production symptom?

<details><summary>Answer</summary>

It disappears entirely. JLS 21 §8.8.9: "If a class contains no constructor declarations, then a default constructor is implicitly declared." One declared constructor of any shape — any arity, any access level, generic, whatever — means the class now contains a constructor declaration, so the default is not declared at all. It is not augmented, not overloaded, not kept as a fallback.

The symptom is that nothing fails at compile time. The change compiles, direct callers that pass the new argument work, unit tests pass. The failure appears at runtime in any reflective instantiation path: `getDeclaredConstructor().newInstance()` throws `NoSuchMethodException`, JPA hydration fails because the specification requires a no-argument constructor, Jackson deserialization fails with "no suitable constructor found," a bean container cannot instantiate the class. Because those paths are often exercised only in integration or only in production, the change can look clean through several stages of a pipeline. The fixes: annotate the real constructor for the framework (`@JsonCreator` with `@JsonProperty` parameters, or the parameter-names module) rather than reintroducing a no-argument back door; declare an explicit narrow `protected` no-argument constructor where a specification genuinely mandates one; or restructure as a record, whose canonical constructor is the only way in.

</details>

**Q2.** What access modifier does the implicit constructor get, and when is a class with no declared constructor still not instantiable from another package?

<details><summary>Answer</summary>

It gets the class's own access modifier — JLS §8.8.9: "the same access modifier as the class, unless the class lacks an access modifier, in which case the default constructor has package access." So `public class Application` with no declared constructor is instantiable from anywhere, but a package-private `class Application` gets a package-private default constructor and cannot be instantiated from another package even though it declares nothing at all. The `private` case is the useful idiom in the other direction: declaring `private Application() { }` on a utility class removes the implicit `public` default and makes the class non-instantiable, which is JLS §8.8.10's subject. There is one more non-instantiability route worth knowing: §8.8.9 makes it a compile-time error for an implicit default constructor to be declared at all when "the superclass does not have an accessible constructor that takes no arguments and has no `throws` clause" — so a class extending a superclass whose only constructors take arguments must declare its own constructor, whatever its access level.

</details>

**Q3.** On Java 21, what must the first statement of a constructor body be, and how has that changed since?

<details><summary>Answer</summary>

On Java 21 it must be an explicit `super` or `this` constructor invocation, or nothing — and if nothing, JLS §8.8.7 says the body "implicitly begins with a superclass constructor invocation `super();`". The grammar enforces it: `ConstructorBody: { [ExplicitConstructorInvocation] [BlockStatements] }` has no production that puts a statement ahead of the invocation. The rule held without exception from Java 1.0 through Java 21.

It was relaxed over four releases. JEP 447, "Statements before super(…) (Preview)," shipped in Java 22. JEP 482 re-previewed it in Java 23 under the new name "Flexible Constructor Bodies," JEP 492 previewed it again unchanged in Java 24, and JEP 513 finalised it in Java 25. The new grammar is `{ [BlockStatements] ExplicitConstructorInvocation [BlockStatements] }`: the statements before the invocation are the *prologue*, those after it the *epilogue*, and prologues run bottom-up while epilogues run top-down. A prologue may compute, validate and throw, and may perform simple assignments to fields declared in the same class that have no initialiser of their own — but it may not otherwise use the object under construction, and a `return` statement in a prologue is a compile-time error.

</details>

**Q4.** How does the Java 25 relaxation relate to the overridable-method-from-a-constructor trap?

<details><summary>Answer</summary>

It is the language-level fix for it, and JEP 513 says so. Its Summary: statements before the invocation "cannot reference the object under construction, but they can initialize its fields […] It also allows fields to be initialized before they become visible to other code in the class, such as methods called from a superclass constructor, thereby improving safety." "Methods called from a superclass constructor" is exactly the trap. On Java 21 a superclass constructor that calls an overridable method reaches the subclass's override, because dispatch resolves on the object's runtime class, which is the subclass from allocation onward; the call happens during the superclass's §12.5 step 5, reached from inside the subclass's step 3, so the subclass's step 4 has not run and every subclass field the override reads still holds its default. A Java 21 subclass has no defence, because it cannot put anything before `super`. On Java 25 it assigns the field in its prologue, then invokes `super`, and the override sees the real value. JEP 513's Goals list this directly: "Provide additional guarantees that the state of a new object is fully initialized before any code can use it." Two conditions on using it: the field must have no initialiser of its own, and the prologue may only assign it, never read it. The frame-by-frame walk of the failure is `01b-initialization-order.md` §2, diagram D-038.

</details>

**Q5.** Where do a generic method's type parameters go relative to the return type, and where do a generic class's go relative to the class name?

<details><summary>Answer</summary>

Opposite sides of the name, which is why this is a persistent error. JLS §8.4's `MethodHeader` production is `TypeParameters {Annotation} Result MethodDeclarator [Throws]`, so a method's type parameters come after the modifiers and **before** the return type: `public static <T extends LedgerEntry> List<T> post(List<T> entries)`. JLS §8.1's `NormalClassDeclaration` is `{ClassModifier} class TypeIdentifier [TypeParameters] [ClassExtends] [ClassImplements] [ClassPermits] ClassBody`, so a class's type parameters come **after** the name: `class Movement<T>`. Writing `class <T> Movement` does not parse, and writing `public static List<T> <T> post(List<T> entries)` does not parse either. The class production also fixes the rest of the order absolutely — modifiers, `class`, name, type parameters, `extends`, `implements`, `permits`, body — so `permits` before `extends` is a syntax error, not a style choice.

</details>

**Q6.** A library's generated bytecode throws a checked exception out of a method that does not declare it, and your calling code has no `catch` for it. How is that possible?

<details><summary>Answer</summary>

Because the `throws` clause is a compile-time construct only. `javac` enforces it — you must declare or catch a checked exception — but it survives into the class file solely as an `Exceptions` attribute on the method (JVMS 21 §4.7.5), and the JVM does not enforce that attribute at all: there is no verification step and no runtime check tying a thrown exception's type to the method's declared `throws` set. So any bytecode that was not produced by `javac`'s checked-exception analysis — a bytecode-generating library, a proxy, a `Method.invoke` reflective call, or `Unsafe.throwException`-style tricks — can propagate a checked exception through a signature that declares none. Your caller has no `catch` because the compiler proved, correctly *for source-level Java*, that it was impossible. The practical consequence is that catching `Exception` (rather than a specific checked type) at framework boundaries is not always paranoia. The class-file encoding of the `Exceptions` attribute is `../language-substrate/03a-internals-class-file-format.md`.

</details>

**Q7.** In a record's compact constructor, how do you normalise a component's stored value, and why is the obvious approach a compile-time error?

<details><summary>Answer</summary>

You reassign the **parameter**, not the field. A compact constructor omits the parameter list entirely, and the compiler appends one `this.component = component;` assignment per component, in record-header order, *after* whatever body you wrote — reading the parameters. So the fields are still unassigned while your body runs, and because they are `final`, writing `this.bonusPortion = normalised` in the body is a compile-time error: the body's write plus the appended write would be two assignments to a `final` field. Reassigning the local parameter is the supported mechanism, and it works precisely because the appended assignment reads the parameter after your body has finished with it. So `bonusPortion = new Money(bonusPortion.amount().setScale(2, RoundingMode.DOWN), bonusPortion.currency());` stores the truncated value.

Two related facts: it is a compile-time error to declare both a compact constructor and a normal canonical constructor in the same record, because their signatures collide; and a normal canonical constructor that omits one component's assignment leaves that field at its default with no warning at all, which is the strongest argument for preferring the compact form whenever you only need validation and normalisation. This matters for `StakeSplit` specifically, whose invariant is that the two portions sum exactly to the stake — a stake of `3.33` must split `0.33` bonus plus `3.00` cash, and rounding the bonus portion up instead would give `3.34` and create a penny of money.

</details>

## Open questions

- The Java 25 code samples in section 2 and in the second pitfall are written from JEP 513's specification text — its revised `ConstructorBody` grammar, the prologue restrictions, and the early-construction-context rules — rather than compiled on a JDK 25 build. Settled by compiling them on JDK 25 or later.
- JEP 513's Description states that early-construction-context code "may use simple assignment statements to fields declared in the same class, provided that the declarations of those fields do not have initializers." Whether the compiler additionally rejects a prologue assignment to a field the constructor's own epilogue also assigns, and whether a `record`'s components can ever be assigned in a prologue, are not settled by the JEP text quoted here. Settled by the JLS 25 text for §8.8.7 or by compiling the cases on JDK 25.

---

**Leaves covered:** 1.13.1, 1.13.2, 1.13.3, 1.13.4, 1.13.5, 1.13.17 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 536
