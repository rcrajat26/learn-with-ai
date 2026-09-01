# 03 Java Core — Generic builds — a self-referential builder and a super type token — BUILD IT (§4.4 (4.4.6, 4.4.7))

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The typesafe heterogeneous container and a generic Stack](02b-typesafe-container-and-generic-stack.md) · Next: [Wildcard copy, generic varargs, and the §4.4 diff table](02d-wildcard-copy-varargs-and-diff.md)

Two builds, and in both of them the runtime is already right and only the *static* type is in
trouble. Files 6 and 7 built the containers — `Pair`, `Either`, `Result`, `MyOptional`, the
typesafe heterogeneous container, the generic `Stack`. This file builds the two generic
*constructs* that make such types usable from the outside.

A **self-typed builder** — `LimitSet.Builder<T extends Builder<T>>` — threads the subclass type
through every inherited fluent setter, so a chain that passes through a base-class setter does
not decay to the base and lose the subclass's own setters. The JDK ships no builder framework at
all; `record` is the 21-era answer for the flat case and cannot be extended, which is exactly
the case this build is for.

A **super type token** — `TypeRef<T>` — smuggles a parameterised type past erasure by storing it
in the one place erasure does not reach: the `Signature` attribute of an anonymous subclass. That
makes `List<LedgerEntry>` usable as a runtime key even though `List<LedgerEntry>.class` does not
compile. `java.base` ships nothing equivalent; Jackson's `TypeReference`, Guice's `TypeLiteral`
and Spring's `ParameterizedTypeReference` are all this class.

The rest of §4.4 — the wildcard `copy`, the generic-varargs heap pollution demonstration, and the
section-wide diff table against the JDK — is in
[Wildcard copy, generic varargs, and the §4.4 diff table](02d-wildcard-copy-varargs-and-diff.md).

Every implementation below was compiled and run on **Oracle JDK 21.0.7 (build
21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, and every `javac` diagnostic is pasted as
the compiler emitted it. The deliberate compile failures are as much output as the successful
runs.

The QuizStakes types the examples share:

```java
enum RestrictionType { DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, SELF_EXCLUDED }
enum RestrictionSource { SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, ADMIN, CLIENT }

record Restriction(RestrictionType type, RestrictionSource source) {}
record CardRestriction(RestrictionType type, RestrictionSource source, String last4) {}
record LedgerEntry(String position, long minorUnits, String statusCode) {}
```

---

## 4.4.6 A self-referential generic builder `[BUILD]`

The shape first. A builder is a mutable staging object with one fluent setter per field and a
`build()` that hands back the immutable product. Inheritance breaks it. `JurisdictionLimitSet`
extends `LimitSet`, so `JurisdictionLimitSet.Builder` extends `LimitSet.Builder` and inherits
`dailyDeposit(long)` for free — but that inherited setter was declared to return
`LimitSet.Builder`, and the moment the chain passes through it the static type of the
expression *decays to the base*. The next link in the chain, a subclass-only setter, is no
longer in scope.

The fix is to make the base builder generic in its own subtype and have every setter return
that type parameter:

```java
abstract static class Builder<T extends Builder<T>> {
    T dailyDeposit(long minor) { this.dailyDepositMinor = minor; return self(); }
    protected abstract T self();
}
```

`T extends Builder<T>` is a **recursive type bound**: the bound of the parameter mentions the
parameter. Read it as "T is some builder whose own self type is T". Because the base class
cannot produce a `T` — it does not know what `T` is — it declares an abstract
`protected T self()` and every concrete subclass implements it as `return this;`. That single
unchecked-looking-but-actually-checked hop is what carries the subclass type back out of every
inherited setter. Recursive bounds in general (the `Comparable<T>` idiom, `Enum<E extends
Enum<E>>`, mutual recursion) belong to
[`../generics/01d-recursive-bounds-and-heterogeneous-containers.md`](../generics/01d-recursive-bounds-and-heterogeneous-containers.md);
builder design as a design question — when to prefer a record, staged builders, validation
placement — belongs to
[`../immutability-and-design/02b-records-jmm-and-builders.md`](../immutability-and-design/02b-records-jmm-and-builders.md).

### Prove the problem first: the version without a self type

```java
abstract class LimitSetNoSelf {
    private final long dailyDepositMinor;

    abstract static class Builder {
        private long dailyDepositMinor = 0L;
        Builder dailyDeposit(long minor) { this.dailyDepositMinor = minor; return this; }
        abstract LimitSetNoSelf build();
    }

    LimitSetNoSelf(Builder builder) { this.dailyDepositMinor = builder.dailyDepositMinor; }
    public long dailyDepositMinor() { return dailyDepositMinor; }
}

final class JurisdictionLimitSetNoSelf extends LimitSetNoSelf {
    private final String country;

    static final class Builder extends LimitSetNoSelf.Builder {
        private String country = "GB";
        Builder country(String iso2) { this.country = iso2; return this; }
        @Override JurisdictionLimitSetNoSelf build() { return new JurisdictionLimitSetNoSelf(this); }
    }

    private JurisdictionLimitSetNoSelf(Builder builder) { super(builder); this.country = builder.country; }
    public String country() { return country; }
}
```

The hierarchy itself compiles cleanly. The call site does not:

```java
public class BrokenBuilderMain {
    public static void main(String[] args) {
        JurisdictionLimitSetNoSelf limits = new JurisdictionLimitSetNoSelf.Builder()
                .dailyDeposit(50_000L)
                .country("GB")
                .build();
        System.out.println(limits.country());
    }
}
```

```text
BrokenBuilderMain.java:5: error: cannot find symbol
                .country("GB")
                ^
  symbol:   method country(String)
  location: class Builder
1 error
```

`location: class Builder` is `LimitSetNoSelf.Builder` — javac prints the simple name, and both
builders are called `Builder`, which is exactly how this error looks in the field and exactly
why it confuses people. The receiver of the `country` call is whatever the `dailyDeposit` call
returned, and that is the base builder.

Reordering does not fix it, it only moves the failure. Put the subclass setter first and the
chain compiles — until you try to assign the result:

```java
JurisdictionLimitSetNoSelf limits = new JurisdictionLimitSetNoSelf.Builder()
        .country("GB")
        .dailyDeposit(50_000L)
        .build();
```

```text
DecayedAssignMain.java:6: error: incompatible types: LimitSetNoSelf cannot be converted to JurisdictionLimitSetNoSelf
                .build();
                      ^
1 error
```

Widen the target type to `LimitSetNoSelf` and it runs, which is the trap: the code works while
the caller happens not to need the subclass type.

```text
built, but the static type of build() is LimitSetNoSelf; runtime class is JurisdictionLimitSetNoSelf
```

**Insight:** the object was always right. Only the *static type* of the chain was lost. The
self type is not a runtime mechanism at all — it is a way of threading the subclass type
through a sequence of method-return positions so the compiler never has to widen.

### The build

```java
abstract class LimitSet {
    private final long dailyDepositMinor;
    private final long maxStakeMinor;
    private final long monthlyLossMinor;

    abstract static class Builder<T extends Builder<T>> {
        private long dailyDepositMinor = 0L;
        private long maxStakeMinor = 0L;
        private long monthlyLossMinor = 0L;

        T dailyDeposit(long minor) { this.dailyDepositMinor = requireNonNegative(minor, "dailyDeposit"); return self(); }
        T maxStake(long minor)     { this.maxStakeMinor     = requireNonNegative(minor, "maxStake");     return self(); }
        T monthlyLoss(long minor)  { this.monthlyLossMinor  = requireNonNegative(minor, "monthlyLoss");  return self(); }

        private static long requireNonNegative(long minor, String field) {
            if (minor < 0L) throw new IllegalArgumentException(field + " must be >= 0, was " + minor);
            return minor;
        }

        abstract LimitSet build();
        protected abstract T self();
    }

    LimitSet(Builder<?> builder) {
        this.dailyDepositMinor = builder.dailyDepositMinor;
        this.maxStakeMinor     = builder.maxStakeMinor;
        this.monthlyLossMinor  = builder.monthlyLossMinor;
        if (maxStakeMinor > dailyDepositMinor && dailyDepositMinor != 0L)
            throw new IllegalArgumentException("maxStake " + maxStakeMinor + " exceeds dailyDeposit " + dailyDepositMinor);
    }

    public long dailyDepositMinor() { return dailyDepositMinor; }
    public long maxStakeMinor()     { return maxStakeMinor; }
    public long monthlyLossMinor()  { return monthlyLossMinor; }

    @Override public String toString() {
        return String.format(Locale.ROOT, "dailyDeposit=%d maxStake=%d monthlyLoss=%d",
                dailyDepositMinor, maxStakeMinor, monthlyLossMinor);
    }
}

final class JurisdictionLimitSet extends LimitSet {
    private final String country;
    private final boolean operatorSignOffRequired;

    static final class Builder extends LimitSet.Builder<Builder> {
        private String country = "GB";
        private boolean operatorSignOffRequired = false;

        Builder country(String iso2) {
            if (iso2 == null || iso2.length() != 2)
                throw new IllegalArgumentException("country must be ISO-3166 alpha-2, was " + iso2);
            this.country = iso2; return this;
        }
        Builder operatorSignOff(boolean required) { this.operatorSignOffRequired = required; return this; }

        @Override JurisdictionLimitSet build() { return new JurisdictionLimitSet(this); }
        @Override protected Builder self() { return this; }
    }

    private JurisdictionLimitSet(Builder builder) {
        super(builder);
        this.country = builder.country;
        this.operatorSignOffRequired = builder.operatorSignOffRequired;
    }

    public String country() { return country; }
    public boolean operatorSignOffRequired() { return operatorSignOffRequired; }

    @Override public String toString() {
        return "JurisdictionLimitSet[" + super.toString() + " country=" + country
                + " operatorSignOff=" + operatorSignOffRequired + "]";
    }
}
```

Four things in that listing earn their place. `LimitSet(Builder<?> builder)` takes the
wildcard, not `Builder<T>`, because the product class does not need to know the self type — it
only reads fields. `build()` is covariantly overridden to return `JurisdictionLimitSet`, so the
concrete builder's static type is precise even though the abstract declaration says `LimitSet`.
The cross-field invariant (`maxStake` cannot exceed `dailyDeposit`) lives in the *product*
constructor, not in a setter, because a setter cannot see a field that has not been set yet.
And the builder's fields are `private` yet readable from the enclosing class — nested classes
share the top-level class's access domain.

```java
public class BuilderDemo {
    public static void main(String[] args) {
        JurisdictionLimitSet subclassFirst = new JurisdictionLimitSet.Builder()
                .country("GB")
                .dailyDeposit(50_000L)
                .maxStake(420L)
                .monthlyLoss(100_000L)
                .operatorSignOff(true)
                .build();
        System.out.println(subclassFirst);

        JurisdictionLimitSet baseFirst = new JurisdictionLimitSet.Builder()
                .dailyDeposit(50_000L)
                .country("IE")
                .maxStake(420L)
                .operatorSignOff(false)
                .monthlyLoss(100_000L)
                .build();
        System.out.println(baseFirst);

        LimitSet.Builder<?> viaBase = new JurisdictionLimitSet.Builder().dailyDeposit(10_000L);
        System.out.println("built through a LimitSet.Builder<?> reference: " + viaBase.build());

        try {
            new JurisdictionLimitSet.Builder().dailyDeposit(300L).maxStake(420L).build();
        } catch (IllegalArgumentException e) {
            System.out.println("caught: " + e.getMessage());
        }
    }
}
```

```text
JurisdictionLimitSet[dailyDeposit=50000 maxStake=420 monthlyLoss=100000 country=GB operatorSignOff=true]
JurisdictionLimitSet[dailyDeposit=50000 maxStake=420 monthlyLoss=100000 country=IE operatorSignOff=false]
built through a LimitSet.Builder<?> reference: JurisdictionLimitSet[dailyDeposit=10000 maxStake=0 monthlyLoss=0 country=GB operatorSignOff=false]
caught: maxStake 420 exceeds dailyDeposit 300
```

Both orderings compile and both produce identical products. The interleaved second chain —
base, subclass, base, subclass, base — is the one the naive version cannot express at all.
`maxStake(420L)` is the domain's average stake reservation value of 4.20 in minor units.

### What the self type does *not* buy you

The bound `T extends Builder<T>` does not require `T` to be *this* class. It requires only
that `T` be some builder whose declared self type is `T`. A class may therefore name a
*sibling* as its self type, and javac accepts it:

```java
final class DepositLimitSet extends LimitSet {
    static final class Builder extends LimitSet.Builder<Builder> {
        @Override DepositLimitSet build() { return new DepositLimitSet(this); }
        @Override protected Builder self() { return this; }
    }
    private DepositLimitSet(Builder b) { super(b); }
}

final class WithdrawalLimitSet extends LimitSet {
    static final class Builder extends LimitSet.Builder<DepositLimitSet.Builder> {
        @Override WithdrawalLimitSet build() { return new WithdrawalLimitSet(this); }
        @Override protected DepositLimitSet.Builder self() { return new DepositLimitSet.Builder(); }
    }
    private WithdrawalLimitSet(Builder b) { super(b); }
}
```

```text
LiedSelfType.java: compiled with zero errors
```

`WithdrawalLimitSet.Builder.self()` returns a brand-new `DepositLimitSet.Builder`, so any
setter called through the base discards every value set before it. Nothing in the type system
objects. The self type is a **convention the compiler mostly enforces** — it catches the honest
mistake of forgetting to thread the type, not a determined misuse.

**Interview:** "Why does the abstract builder need `self()` instead of just returning `this`?"
— because the static type of `this` inside the base class is `Builder<T>`, not `T`, and there
is no legal conversion from one to the other. `self()` moves the assertion to the subclass,
where `this` really is a `T`.

> A self-referential generic builder is a builder whose base class is parameterised by its own
> subtype, so that every inherited fluent setter returns the subclass's static type and the
> chain never decays.

---

## 4.4.7 A super type token `[PROVE]`

File 7 ended on a wall: `List<String>.class` does not compile, so there is no way to hand a
parameterised type to a method that wants a runtime type key. This is the payoff. The
syllabus phrases the leaf with a placeholder element type; instantiated in QuizStakes it reads
"recover `List<LedgerEntry>` at runtime".

The mechanism, worked through. Erasure deletes type arguments from *instances* — a
`List<LedgerEntry>` object at runtime is an `ArrayList` and nothing more, with no memory of
`LedgerEntry`. But erasure does **not** delete type arguments from *declarations*. When a class
file declares a generic superclass, javac emits a `Signature` attribute (JVMS §4.7.9) recording
the full generic form of `extends`. So if you create an **anonymous subclass** of
`TypeRef<List<LedgerEntry>>`, that anonymous class's own class file must carry
`LTypeRef<Ljava/util/List<LLedgerEntry;>;>;` in its `Signature` attribute — because a class
cannot describe its own supertype without naming the type arguments it supplied. The instance
forgot; its class remembers. `getClass().getGenericSuperclass()`, cast to `ParameterizedType`,
reads that attribute back.

That is the whole trick: **the type argument is stored in the subclass, not in the object.**

### The build

```java
abstract class TypeRef<T> {
    private final Type type;

    protected TypeRef() {
        Type superclass = getClass().getGenericSuperclass();
        if (!(superclass instanceof ParameterizedType parameterized)) {
            throw new IllegalArgumentException(
                    "TypeRef subclass " + getClass().getName()
                    + " has no type argument on its superclass; extend TypeRef<SomeType>, not raw TypeRef");
        }
        this.type = parameterized.getActualTypeArguments()[0];
    }

    public final Type type() { return type; }

    @SuppressWarnings("unchecked")
    public final Class<? super T> rawType() {
        if (type instanceof Class<?> c) return (Class<? super T>) c;
        if (type instanceof ParameterizedType p) return (Class<? super T>) p.getRawType();
        throw new IllegalStateException("no raw type for " + type);
    }

    @Override public boolean equals(Object other) {
        return other instanceof TypeRef<?> that && this.type.equals(that.type);
    }
    @Override public int hashCode() { return Objects.hashCode(type); }
    @Override public String toString() { return "TypeRef<" + type.getTypeName() + ">"; }
}

final class RawTypeRef extends TypeRef {
}
```

`abstract` is load-bearing and is discussed below. `equals`/`hashCode` delegate to the
recovered `Type`, which makes a `TypeRef` usable as a `HashMap` key — the natural upgrade to the
typesafe heterogeneous container file 7 built over `Map<Class<?>, Object>`, which could only key
on raw classes. `rawType()` returns `Class<? super T>` rather than `Class<T>` because for
`T = List<LedgerEntry>` the erasure is `List`, and `List` is a supertype of
`List<LedgerEntry>`, not equal to it.

```java
public class TypeRefDemo {
    static <E> TypeRef<List<E>> listOfTypeVariable() {
        return new TypeRef<List<E>>() {};
    }

    public static void main(String[] args) {
        TypeRef<List<LedgerEntry>> ledgerPage = new TypeRef<List<LedgerEntry>>() {};
        System.out.println("toString      : " + ledgerPage);
        System.out.println("type impl     : " + ledgerPage.type().getClass().getName());
        System.out.println("typeName      : " + ledgerPage.type().getTypeName());
        System.out.println("rawType       : " + ledgerPage.rawType().getName());
        ParameterizedType p = (ParameterizedType) ledgerPage.type();
        System.out.println("arg[0]        : " + p.getActualTypeArguments()[0].getTypeName());
        System.out.println("anon class    : " + ledgerPage.getClass().getName());
        System.out.println("genericSuper  : " + ledgerPage.getClass().getGenericSuperclass().getTypeName());
        System.out.println("plain super   : " + ledgerPage.getClass().getSuperclass().getName());

        TypeRef<Map<String, List<Restriction>>> byClient = new TypeRef<Map<String, List<Restriction>>>() {};
        System.out.println("nested        : " + byClient.type().getTypeName());

        System.out.println("equal refs    : " + new TypeRef<List<LedgerEntry>>() {}.equals(ledgerPage));
        System.out.println("unequal refs  : " + new TypeRef<List<Restriction>>() {}.equals(ledgerPage));

        TypeRef<? extends List<?>> unresolved = listOfTypeVariable();
        Type inner = ((ParameterizedType) unresolved.type()).getActualTypeArguments()[0];
        System.out.println("type-variable : " + unresolved.type().getTypeName()
                + "  arg impl=" + inner.getClass().getSimpleName());

        try {
            new RawTypeRef();
        } catch (IllegalArgumentException e) {
            System.out.println("raw subclass  : " + e.getClass().getSimpleName() + ": " + e.getMessage());
        }
    }
}
```

```text
toString      : TypeRef<java.util.List<LedgerEntry>>
type impl     : sun.reflect.generics.reflectiveObjects.ParameterizedTypeImpl
typeName      : java.util.List<LedgerEntry>
rawType       : java.util.List
arg[0]        : LedgerEntry
anon class    : TypeRefDemo$2
genericSuper  : TypeRef<java.util.List<LedgerEntry>>
plain super   : TypeRef
nested        : java.util.Map<java.lang.String, java.util.List<Restriction>>
equal refs    : true
unequal refs  : false
type-variable : java.util.List<E>  arg impl=TypeVariableImpl
raw subclass  : IllegalArgumentException: TypeRef subclass RawTypeRef has no type argument on its superclass; extend TypeRef<SomeType>, not raw TypeRef
```

`LedgerEntry` survived. Nesting survived to arbitrary depth. `plain super` is bare `TypeRef` —
`getSuperclass()` returns the erasure, `getGenericSuperclass()` returns the signature; the
difference between those two calls is the entire feature. The anonymous class is `TypeRefDemo$2`
rather than `$1` because the one inside `listOfTypeVariable()` was numbered first.

### The evidence: the `Signature` attribute

The information is not computed, it is stored. `javap -v` on the anonymous class:

```text
Classfile /private/tmp/jcb-n-work-02c/out/TypeRefDemo$2.class
  Last modified Aug 29, 2026; size 386 bytes
  Compiled from "TypeRefDemo.java"
class TypeRefDemo$2 extends TypeRef<java.util.List<LedgerEntry>>
  minor version: 0
  major version: 65
  flags: (0x0020) ACC_SUPER
  this_class: #7                          // TypeRefDemo$2
  super_class: #2                         // TypeRef
  interfaces: 0, fields: 0, methods: 1, attributes: 5
```

```text
  #11 = Utf8               Signature
  #12 = Utf8               LTypeRef<Ljava/util/List<LLedgerEntry;>;>;
```

```text
Signature: #12                          // LTypeRef<Ljava/util/List<LLedgerEntry;>;>;
SourceFile: "TypeRefDemo.java"
EnclosingMethod: #16.#18                // TypeRefDemo.main
NestHost: class TypeRefDemo
InnerClasses:
  #7;                                     // class TypeRefDemo$2
```

Read the two lines against each other. `super_class: #2 // TypeRef` is the erased constant-pool
entry the verifier and the `invokespecial` in the constructor use — no type arguments, because
the VM has no use for them. `Signature: LTypeRef<Ljava/util/List<LLedgerEntry;>;>;` is a
separate class-level attribute, a single UTF-8 string in the constant pool, holding the generic
form. Sixteen bytes of text in a 386-byte class file is where `List<LedgerEntry>` physically
lives at runtime. `getGenericSuperclass()` parses that string;
`sun.reflect.generics.reflectiveObjects.ParameterizedTypeImpl` in the output above is the parse
result.

### The boundary: no anonymous subclass, no signature

Drop the braces and there is no subclass, therefore no `Signature`, therefore nothing to read.
With `TypeRef` declared `abstract`, javac stops you before the question arises:

```java
TypeRef<List<LedgerEntry>> ledgerPage = new TypeRef<List<LedgerEntry>>();
```

```text
NoBracesMain.java:5: error: TypeRef is abstract; cannot be instantiated
        TypeRef<List<LedgerEntry>> ledgerPage = new TypeRef<List<LedgerEntry>>();
                                                ^
1 error
```

That error is the reason `abstract` is in the declaration. Take it away and the no-braces form
compiles, then fails at construction:

```java
class ConcreteTypeRef<T> {
    private final Type type;
    protected ConcreteTypeRef() {
        Type superclass = getClass().getGenericSuperclass();
        System.out.println("  getGenericSuperclass() = " + superclass.getTypeName()
                + "  (impl " + superclass.getClass().getSimpleName() + ")");
        this.type = ((ParameterizedType) superclass).getActualTypeArguments()[0];
    }
    public Type type() { return type; }
}

public class ConcreteTypeRefDemo {
    public static void main(String[] args) {
        System.out.println("with braces:");
        System.out.println("  recovered = " + new ConcreteTypeRef<List<LedgerEntry>>() {}.type().getTypeName());
        System.out.println("without braces:");
        ConcreteTypeRef<List<LedgerEntry>> broken = new ConcreteTypeRef<List<LedgerEntry>>();
        System.out.println("  recovered = " + broken.type());
    }
}
```

```text
with braces:
  getGenericSuperclass() = ConcreteTypeRef<java.util.List<LedgerEntry>>  (impl ParameterizedTypeImpl)
  recovered = java.util.List<LedgerEntry>
without braces:
  getGenericSuperclass() = java.lang.Object  (impl Class)
Exception in thread "main" java.lang.ClassCastException: class java.lang.Class cannot be cast to class java.lang.reflect.ParameterizedType (java.lang.Class and java.lang.reflect.ParameterizedType are in module java.base of loader 'bootstrap')
	at ConcreteTypeRef.<init>(ConcreteTypeRefDemo.java:13)
	at ConcreteTypeRefDemo.main(ConcreteTypeRefDemo.java:23)
```

Without the braces, `getClass()` is `ConcreteTypeRef` itself, whose generic superclass is
`java.lang.Object` — a plain `Class`, not a `ParameterizedType`. The `List<LedgerEntry>` written
at the call site was erased away with the instance and never recorded anywhere.

The second boundary is in the successful run above: `type-variable : java.util.List<E>  arg
impl=TypeVariableImpl`. `new TypeRef<List<E>>() {}` inside a generic method records `List<E>`
where `E` is a `TypeVariable`, not a concrete type. A super type token cannot recover a type
argument that was itself a type variable at the point the anonymous class was compiled — the
signature stores the variable's *name*, and its binding existed only at the erased call site.
This is why `TypeReference`-style APIs must be constructed with literal types.

Full treatment of why erasure is designed this way and how the signature grammar works:
[`../generics/03e-internals-why-erasure-and-super-type-tokens.md`](../generics/03e-internals-why-erasure-and-super-type-tokens.md).
The reflection API surface — `Type`, `ParameterizedType`, `GenericArrayType`, `WildcardType`,
`Class.cast`, `Class.asSubclass`:
[`../generics/02a-type-tokens-and-generic-reflection.md`](../generics/02a-type-tokens-and-generic-reflection.md).

**Pitfall:** every `new TypeRef<X>() {}` creates and loads a distinct anonymous class. One per
call site is free; one per *request*, inside a loop or a hot handler, is a class-loading leak
against metaspace. Hoist tokens into `static final` fields.

> A super type token is an instance of an anonymous subclass created solely so that the
> subclass's `Signature` attribute records the type argument the instance itself cannot carry.

---

## Pitfalls

### Believing a fluent setter can return `this` and survive subclassing

**Wrong**

```java
abstract static class Builder {
    Builder dailyDeposit(long minor) { this.dailyDepositMinor = minor; return this; }
}

new JurisdictionLimitSetNoSelf.Builder().dailyDeposit(50_000L).country("GB").build();
```

```text
BrokenBuilderMain.java:5: error: cannot find symbol
                .country("GB")
                ^
  symbol:   method country(String)
  location: class Builder
1 error
```

**Right**

```java
abstract static class Builder<T extends Builder<T>> {
    T dailyDeposit(long minor) { this.dailyDepositMinor = minor; return self(); }
    protected abstract T self();
}
// subclass: static final class Builder extends LimitSet.Builder<Builder> {
//               @Override protected Builder self() { return this; } }
```

Both orderings then work, and `build()` is covariantly overridden so the result type is precise
too:

```text
JurisdictionLimitSet[dailyDeposit=50000 maxStake=420 monthlyLoss=100000 country=IE operatorSignOff=false]
```

**Why people believe it:** `return this` is right in the non-inherited case, and it *reads* like
it returns the runtime type. The runtime type is indeed the subclass — the failure is entirely
in the static type, and the object being correct all along makes the error feel like a compiler
defect.

### Believing `new TypeRef<List<LedgerEntry>>()` works without the anonymous-subclass braces

**Wrong**

```java
ConcreteTypeRef<List<LedgerEntry>> broken = new ConcreteTypeRef<List<LedgerEntry>>();
```

```text
  getGenericSuperclass() = java.lang.Object  (impl Class)
Exception in thread "main" java.lang.ClassCastException: class java.lang.Class cannot be cast to class java.lang.reflect.ParameterizedType (java.lang.Class and java.lang.reflect.ParameterizedType are in module java.base of loader 'bootstrap')
	at ConcreteTypeRef.<init>(ConcreteTypeRefDemo.java:13)
```

(With `TypeRef` correctly declared `abstract`, javac stops it earlier:
`error: TypeRef is abstract; cannot be instantiated`.)

**Right**

```java
TypeRef<List<LedgerEntry>> ledgerPage = new TypeRef<List<LedgerEntry>>() {};
```

```text
typeName      : java.util.List<LedgerEntry>
genericSuper  : TypeRef<java.util.List<LedgerEntry>>
```

Declare the base `abstract` so the braces cannot be forgotten.

**Why people believe it:** the type argument is written right there at the call site, so it
feels like the object must know it. It does not. The argument is recorded in the *anonymous
subclass's* `Signature` attribute — `LTypeRef<Ljava/util/List<LLedgerEntry;>;>;` — and the two
empty braces are the only thing that creates a subclass for it to live in.
### Believing `T extends Builder<T>` proves that `T` is the class that declared it

**Wrong**

```java
final class DepositLimitSet extends LimitSet {
    static final class Builder extends LimitSet.Builder<Builder> {
        @Override DepositLimitSet build() { return new DepositLimitSet(this); }
        @Override protected Builder self() { return this; }
    }
    private DepositLimitSet(Builder b) { super(b); }
}

final class WithdrawalLimitSet extends LimitSet {
    static final class Builder extends LimitSet.Builder<DepositLimitSet.Builder> {
        @Override WithdrawalLimitSet build() { return new WithdrawalLimitSet(this); }
        @Override protected DepositLimitSet.Builder self() { return new DepositLimitSet.Builder(); }
    }
    private WithdrawalLimitSet(Builder b) { super(b); }
}
```

```text
LiedSelfType.java: compiled with zero errors
```

`WithdrawalLimitSet.Builder` names a *sibling* as its self type, and `self()` returns a
brand-new instance of it, so every base-class setter called on a `WithdrawalLimitSet.Builder`
chain writes into an object that is then thrown away. The bound is satisfied — the bound asks
only that `T` be some builder whose declared self type is `T` — so nothing is reported.

**Right**

Each concrete builder parameterises the base with **itself** and returns `this`:

```java
static final class Builder extends LimitSet.Builder<Builder> {
    @Override JurisdictionLimitSet build() { return new JurisdictionLimitSet(this); }
    @Override protected Builder self() { return this; }
}
```

Then the chain keeps every value set through it, including one built entirely through a base
reference:

```text
built through a LimitSet.Builder<?> reference: JurisdictionLimitSet[dailyDeposit=10000 maxStake=0 monthlyLoss=0 country=GB operatorSignOff=false]
```

**Why people believe it:** the recursive bound *looks* like a self-reference constraint, and it
is described everywhere as "the self type", which implies the compiler knows which class `T` is
meant to be. It does not. It checks only that `self()`'s declared return type matches the type
argument — a consistency check on the signature, not a proof about the body. The self type
catches the honest mistake of forgetting to thread the type through; it does not stop a
determined misuse, so nothing replaces reading the `self()` body in review.

---

## Cheat sheet

| Thing | Form | Key fact |
|---|---|---|
| Self-typed builder | `abstract static class Builder<T extends Builder<T>>` + `protected abstract T self()` | subclass writes `extends Builder<Builder>` and `self() { return this; }` |
| Why `self()` | static type of `this` in the base is `Builder<T>`, not `T` | no legal conversion; the subclass must assert it |
| Self type's limit | `class A extends Builder<B>` compiles | convention, not proof |
| Product constructor | `LimitSet(Builder<?> b)` | wildcard: the product does not need the self type |
| Cross-field invariant | in the product constructor | a setter cannot see unset fields |
| Super type token | `abstract class TypeRef<T>` + `new TypeRef<List<LedgerEntry>>() {}` | the braces create the subclass that stores the type |
| Where the type lives | the anonymous class's `Signature` attribute (JVMS §4.7.9) | `LTypeRef<Ljava/util/List<LLedgerEntry;>;>;` |
| The two reflection calls | `getSuperclass()` → erasure; `getGenericSuperclass()` → signature | the difference is the whole feature |
| Token limits | cannot resolve a type-variable argument; one class loaded per call site | hoist to `static final` |

---

## Self-test

**Q1.** The base builder's setters return `T`. Why can the base not just write `return (T) this;`
and skip the abstract `self()`?

<details><summary>Answer</summary>

It can, and it compiles, but it is strictly worse. `(T) this` is an unchecked cast: erasure
deletes it, so nothing is checked at runtime and the compiler emits an unchecked warning that
you then suppress. Worse, it silently succeeds for a subclass that named the wrong self type —
`WithdrawalLimitSet.Builder extends LimitSet.Builder<DepositLimitSet.Builder>` would pass the
erased cast and then fail with a `ClassCastException` at the call site, at whatever line
consumed the returned value. `protected abstract T self()` moves the assertion into the subclass
where `this` genuinely is a `T`, so `return this;` needs no cast at all and there is no unchecked
operation anywhere in the pattern. Forgetting to override it is a compile error rather than a
latent one.

</details>

**Q2.** Why is `TypeRef` declared `abstract`, given that nothing in it is an abstract method?

<details><summary>Answer</summary>

To make the anonymous-subclass braces impossible to forget. The whole mechanism depends on there
being a subclass, because the type argument is recorded in the *subclass's* `Signature`
attribute and nowhere else. Written without braces, `new TypeRef<List<LedgerEntry>>()` would
construct the base class itself, whose `getGenericSuperclass()` is `java.lang.Object` — a plain
`Class`, not a `ParameterizedType`. Measured on the deliberately non-abstract variant, that is a
`ClassCastException: class java.lang.Class cannot be cast to class
java.lang.reflect.ParameterizedType`, thrown from the constructor, at run time. With `abstract`
on the declaration javac refuses the call site instead: `error: TypeRef is abstract; cannot be
instantiated`. Same bug, moved from run time to compile time, for one keyword. The constructor's
own `instanceof ParameterizedType` check is the second line of defence, and it is what catches a
*named* raw subclass such as `class RawTypeRef extends TypeRef {}`, which `abstract` cannot stop.

</details>

**Q3.** The product's constructor is `LimitSet(Builder<?> builder)`. Why the wildcard rather
than `Builder<T>`, and why does the cross-field invariant live there rather than in a setter?

<details><summary>Answer</summary>

`LimitSet` is not a generic class — it has no type parameter, so it has no `T` to write. The
self type exists only to shape the *builder's* method return types, and the product does nothing
with the builder except read three `long` fields, which every instantiation of `Builder`
supports. `Builder<?>` says exactly that: some builder, self type unknown and unneeded. Making
`LimitSet` generic in the builder's self type purely to name it in one constructor parameter
would leak an implementation detail of the builder into every use of the product type.

The invariant — `maxStake` must not exceed `dailyDeposit` — has to be in the product
constructor because it reads two fields, and a fluent setter can only ever see the fields set
before it. Put the check in `maxStake(long)` and `new JurisdictionLimitSet.Builder().maxStake(420L).dailyDeposit(300L)`
passes while the reverse order throws, which makes validity depend on chain order. In the
product constructor there is exactly one moment when all fields are known, and the measured
failure is order-independent: `caught: maxStake 420 exceeds dailyDeposit 300`.

</details>

**Q4.** Explain precisely where `List<LedgerEntry>` is stored at runtime when you write
`new TypeRef<List<LedgerEntry>>() {}`.

<details><summary>Answer</summary>

In the `Signature` attribute of the anonymous class's own class file, as a UTF-8 constant-pool
entry holding the string `LTypeRef<Ljava/util/List<LLedgerEntry;>;>;`. `javap -v` on
`TypeRefDemo$2.class` shows it as constant `#12` and as a class-level
`Signature: #12` attribute, sitting alongside a `super_class: #2 // TypeRef` entry that is fully
erased. The instance stores nothing — no field, no hidden slot. Erasure removes type arguments
from instances but not from declarations, and a class declaring a parameterised superclass must
record which arguments it supplied. `getGenericSuperclass()` parses that attribute and returns a
`sun.reflect.generics.reflectiveObjects.ParameterizedTypeImpl`;
`getActualTypeArguments()[0]` is `List<LedgerEntry>`.

</details>

**Q5.** You need a runtime key for `Map<String, List<Restriction>>`. Give two options and their
costs.

<details><summary>Answer</summary>

Option one, a super type token: `static final TypeRef<Map<String, List<Restriction>>> KEY = new
TypeRef<>() {};` — recovers the full nested type, verified in this file's output as
`java.util.Map<java.lang.String, java.util.List<Restriction>>`. The cost is one anonymous class
loaded per call site, so it must be hoisted to a `static final` field or it leaks metaspace under
load; and it cannot resolve a type argument that was itself a type variable. Option two, a
plain `Class<?>` key plus a documented convention about the element types — the typesafe
heterogeneous container file 7 built. Cost: it cannot distinguish `List<Restriction>` from
`List<LedgerEntry>`, so `Class.cast` checks only the raw type and the element type is unchecked.
Use the token when the parameterisation is load-bearing (deserialization targets, message
codecs) and the raw `Class` when it is not.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.4.6, 4.4.7 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 839
