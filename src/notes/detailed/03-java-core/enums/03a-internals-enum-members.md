# 03 Java Core — `Enum`'s members and constant-body subclasses — INTERNALS (§3.10, 3.10.4–3.10.6)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Enum internals — what `javac` generates](03-internals-enums.md) · Next: [The uniqueness guarantees and the switch map](03b-internals-guarantees-and-switch.md)

[`03-internals-enums.md`](03-internals-enums.md) read the generated class: the flags, the `<clinit>`, the two static methods. This file finishes the class-file layer with the three things that live above and beside it. What a constant body actually produces, and which three class-file attributes record the relationship — one from 1998, one from Java 11, one from Java 17, all three present on the same enum. Which fields `java.lang.Enum` declares, and why one of them stopped being two. And which of its members are `final`, with the specific invariant each one is defending, because the list is only worth memorising if you can say what breaks without it.

Everything here is measured. Version-sensitive claims are stated against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)** as the baseline, with **Oracle JDK 17.0.15**, **Oracle JDK 11.0.27** and **Oracle JDK 1.8.0_202** for comparison; library source is quoted from each build's own `lib/src.zip`.

The language-level consequences of everything below are in [`01-basics.md`](01-basics.md) (`getClass()` versus `getDeclaringClass()`, the uniqueness guarantee) and [`01a-implicit-members-and-identity.md`](01a-implicit-members-and-identity.md) (the member inventory, `hashCode`'s instability). This file does not re-argue them; it shows the class-file facts they follow from. Serialization, reflection and `$SwitchMap` are in [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md); `EnumSet`/`EnumMap` layout in [`03c-internals-enumset-enummap.md`](03c-internals-enumset-enummap.md).

The enums under test, carried forward from [`01-basics.md`](01-basics.md):

```java
public enum RestrictionSource {
    SYSTEM_ONBOARDING,
    SYSTEM_COMPLIANCE,
    SYSTEM_LIFECYCLE,
    ADMIN,
    CLIENT {
        @Override public boolean reversibleByOperator() { return false; }
    };
    public boolean reversibleByOperator() { return true; }
}

public enum GateType {
    AGE_ELIGIBILITY { @Override public String failureCode() { return "AO-119"; } },
    JURISDICTION    { @Override public String failureCode() { return "AO-129"; } },
    SCREENING       { @Override public String failureCode() { return "AA-599"; } };
    public abstract String failureCode();
}
```

`RestrictionSource` overrides a *concrete* method; `GateType` implements an *abstract* one. The difference between those two is the correction in concept 1.

## 1. A constant body is an anonymous subclass, and the attributes prove it (3.10.4)

`[PROVE]` `[BYTECODE]` The language-level consequence — `getClass()` is not the enum type, `isEnum()` is false, use `getDeclaringClass()` — is [`01-basics.md`](01-basics.md) concept 2. Here is the class-file evidence, and one correction to the folklore.

### Why it exists

Per-constant behaviour needs per-constant *method dispatch*, and the JVM dispatches on the receiver's class. So each behaviourally-distinct constant needs its own class. `javac` already had a mechanism for "a one-off subclass with a body and no name" — the anonymous class — and reuses it verbatim, right down to the `Outer$N` naming scheme.

### The mechanism

Two forms, and the folklore is right about one and wrong about the other.

**Form A, a concrete method overridden.** `RestrictionSource`, where `CLIENT` overrides a `reversibleByOperator()` that has a body. Measured header:

```
public class RestrictionSource extends java.lang.Enum<RestrictionSource>
  flags: (0x4021) ACC_PUBLIC, ACC_SUPER, ACC_ENUM
  interfaces: 0, fields: 6, methods: 6, attributes: 5
```

**No `ACC_FINAL`, and no `ACC_ABSTRACT`.** Compare `RestrictionType`'s `0x4031`: the difference is exactly the `0x0010` `ACC_FINAL` bit, gone. Nothing became abstract, because nothing is unimplemented.

**Form B, an `abstract` member implemented per constant.** `GateType`. Measured:

```
public abstract class GateType extends java.lang.Enum<GateType>
  flags: (0x4421) ACC_PUBLIC, ACC_SUPER, ACC_ABSTRACT, ACC_ENUM
  interfaces: 0, fields: 4, methods: 6, attributes: 5
```

`0x4421` adds `ACC_ABSTRACT` (0x0400). So the widely-repeated claim that "an enum with constant bodies becomes an abstract class" — which this topic's own syllabus states at leaf 3.10.4 — is true for Form B and false for Form A. The invariant that holds in both cases is the weaker one: **a constant body costs the class its `ACC_FINAL`.** Worth getting right, because it is a two-second `javap` check that distinguishes someone who has looked from someone who has read.

The subclass, measured for `RestrictionSource$1`:

```
final class RestrictionSource$1 extends RestrictionSource {
  private RestrictionSource$1(java.lang.String, int);
    Code:
       0: aload_0
       1: aload_1
       2: iload_2
       3: invokespecial #1   // Method RestrictionSource."<init>":(Ljava/lang/String;I)V
       6: return

  public boolean reversibleByOperator();
    Code:
       0: iconst_0
       1: ireturn
}
```

`final`, `private` constructor, forwards `name` and `ordinal`, overrides the one method. **No `this$0` field**, because the enum class is a static context and the anonymous class captures nothing — the elision rule from [`../inheritance-and-dispatch/04-internals-nested-classes.md`](../inheritance-and-dispatch/04-internals-nested-classes.md) applied to a case where there is nothing to capture in the first place.

Three attributes on the enum class record the relationship, and their combination is the interesting part. Measured tail of `RestrictionSource.class`:

```
NestMembers:
  RestrictionSource$1
PermittedSubclasses:
  RestrictionSource$1
InnerClasses:
  final #43;   // class RestrictionSource$1
```

and for `GateType`, three of each:

```
PermittedSubclasses:
  GateType$1
  GateType$2
  GateType$3
InnerClasses:
  final #32;   // class GateType$1
  final #36;   // class GateType$2
  final #40;   // class GateType$3
```

- **`InnerClasses`** is the Java 1.1 mechanism that lets reflection answer `getSimpleName()` and `getEnclosingClass()` despite the flattening. For an anonymous class the name index is zero, which is why `getSimpleName()` on one is the empty string.
- **`NestMembers`** is JEP 181 (Java 11), and it is what lets `RestrictionSource$1` call `RestrictionSource`'s `private` constructor with a direct `invokespecial` rather than through a synthetic `access$000` bridge. Pre-11 compilers generated that bridge, widening a `private` member to package-private in the process; the nest attributes replaced it with a JVM-enforced mutual check.
- **`PermittedSubclasses`** is JEP 409 (Java 17), and its presence here is the surprising one: **the enum is implicitly sealed.** Measured: `RestrictionSource.class.isSealed()` is `true` and `getPermittedSubclasses()` returns `[class RestrictionSource$1]`. Note there is no `ACC_SEALED` flag — sealedness in the class file *is* the attribute, and the same is true of records, which have a `Record` attribute and no `ACC_RECORD` flag.

**Insight:** the three attributes together tell a story about how the same problem was solved three times. In 1.1 the answer to "these flat classes are really one unit" was a purely informational attribute (`InnerClasses`) plus generated bridges that the JVM did not understand. In 11 the JVM was taught the relationship for *access* (`NestMembers`). In 17 it was taught the relationship for *extension* (`PermittedSubclasses`). An enum with constant bodies is one of the few constructs that carries all three at once, which makes it a good specimen for reading them.

`[PROVE]` The class-file cost is one file per body constant. `GateType` produced four class files: `GateType.class`, `GateType$1.class`, `GateType$2.class`, `GateType$3.class`. That is the trade-off against the field-plus-`switch` form: at three constants irrelevant, at two hundred it is two hundred extra classes to load, verify, and initialise, each with its own constant pool.

### Diagram

D-117, embedded in [`03-internals-enums.md`](03-internals-enums.md) concept 1, is drawn on `RestrictionSource` specifically so the missing `ACC_FINAL`, the `RestrictionSource$1` box and the `PermittedSubclasses`/`NestMembers` annotation panel all appear together.

### A concrete example

The `<clinit>` is where the two forms differ visibly. For `RestrictionSource`, the four plain constants get `new RestrictionSource` and the one with a body gets `new RestrictionSource$1` — the anonymous subclass is instantiated in the enum's own static initialiser, with the same `(String, int)` constructor call:

```java
public final class ConstantBodyEvidence {

    /** Every constant reports the same declaring class. */
    public static Map<String, String> classesOf() {
        Map<String, String> byName = new LinkedHashMap<>();
        for (RestrictionSource source : RestrictionSource.values()) {
            byName.put(source.name(),
                source.getClass().getName()
                    + " (declaring: " + source.getDeclaringClass().getName()
                    + ", isEnum: " + source.getClass().isEnum() + ")");
        }
        return byName;
    }

    /** The safe way to obtain the type token from a constant. */
    public static <E extends Enum<E>> EnumSet<E> universeOf(E anyConstant) {
        return EnumSet.allOf(anyConstant.getDeclaringClass());
    }
}
```

Measured output of `classesOf()` on JDK 21.0.7, abbreviated to the two interesting rows:

```
ADMIN  -> RestrictionSource   (declaring: RestrictionSource, isEnum: true)
CLIENT -> RestrictionSource$1 (declaring: RestrictionSource, isEnum: false)
```

`universeOf` is the pattern worth memorising: a generic method taking `E extends Enum<E>` and calling `getDeclaringClass()` works for every constant of every enum, body or not, whereas the obvious `anyConstant.getClass()` version compiles — the generic signature does not distinguish them — and fails at runtime on exactly the constants with bodies, with `ClassCastException: class RestrictionSource$1 not an enum` out of `EnumSet.noneOf`.

### The gotcha

**Pitfall:** relying on the `E$N` numbering. The number is positional, assigned in source order among the enum's anonymous classes, and the JLS explicitly leaves the binary names of anonymous classes to the compiler (§13.1). Inserting a new constant *with a body* earlier in the declaration list renumbers every body constant after it. Symptom: a log filter, a heap-dump runbook query, an APM class-name rule, or a `Class.forName("RestrictionSource$1")` in a test that silently starts referring to a different constant after an edit that looks additive. Fix: never name an `E$N` class in any artefact outside the class file. Identify a constant by `name()`, and if you need to reason about the subclass at all, get it from `constant.getClass()` at runtime rather than from a string.

> **Definition.** Each constant with a class body compiles to a `final` anonymous subclass `E$N` with a `private (String, int)` constructor; the enum class consequently loses `ACC_FINAL`, gains `ACC_ABSTRACT` only if a body implements an `abstract` member, and carries `InnerClasses`, `NestMembers` and — since Java 17 — `PermittedSubclasses` naming exactly those subclasses.

---

## 2. `Enum`'s fields: two `final`, and one that is not (3.10.5)

`[SOURCE]` The claim everyone makes is "an enum constant holds a name and an ordinal, both `final`". True, and incomplete on JDK 21.

### Why it exists

`name` and `ordinal` are the two pieces of state every enum constant has, and both must be immutable: `name` because it is the serialization identity and the `valueOf` key, `ordinal` because it indexes `EnumSet` bits and `EnumMap` slots and is the basis of `compareTo`. Making them `final` and setting them from a compiler-injected constructor call means no code path — yours, reflection's, or a subclass body's — can change them after construction, and the `final`-field freeze guarantees other threads see them fully initialised.

### The mechanism

Measured by reflection on JDK 21.0.7:

```
Enum fields = [private final java.lang.String java.lang.Enum.name,
               private final int java.lang.Enum.ordinal,
               private int java.lang.Enum.hash]
```

The declarations, from the source:

```java
private final String name;

public final String name() {
    return name;
}

private final int ordinal;

public final int ordinal() {
    return ordinal;
}
```

Both `private`, both `final`, both exposed by a `final` accessor — so a subclass cannot shadow the accessor either. They are set by `Enum`'s own constructor, which the generated enum constructor calls with `invokespecial Enum.<init>:(Ljava/lang/String;I)V`, as the `<clinit>` listing in [`03-internals-enums.md`](03-internals-enums.md) concept 1 shows. `Enum`'s constructor is `protected`, which is what makes it callable by a generated subclass constructor and by nothing else you can write, since you cannot declare a class extending `Enum` directly.

The third field is the JDK 21 addition:

```java
/**
 * The hash code of this enumeration constant.
 */
@Stable
private int hash;
```

It is **not** `final`, which it cannot be, because it is lazily assigned. `@Stable` is the JDK-internal annotation that tells the JIT "this field is written at most once from its default value; after you have observed a non-default value you may treat it as a constant". That is what buys the optimisation: after the first `hashCode()` call on a constant, a compiled caller can fold the value in as a literal. Concept 3 has the method that fills it.

`[NUM]` The memory arithmetic for one constant, derived from the confirmed settings on this build (`UseCompressedOops = true`, `ObjectAlignmentInBytes = 8`): a 12-byte object header, a 4-byte compressed reference for `name`, a 4-byte `int` for `ordinal`, a 4-byte `int` for `hash` — 24 bytes, already 8-aligned. Add your own per-constant fields on top. Ten `RestrictionType` constants with no declared fields are therefore 240 bytes of constant objects, plus the `String` objects for the names (which are interned literals shared with the constant pool, so not attributable per constant), plus the 56-byte `$VALUES` array. On **JDK 17 and earlier**, without the `hash` field, a bare constant is 12 + 4 + 4 = 20 bytes padded to 24 — so the field is free in practice, having landed in the alignment padding that already existed. Object layout arithmetic is in [`../objects-equality-and-lifecycle/05-internals-object-layout.md`](../objects-equality-and-lifecycle/05-internals-object-layout.md).

### Diagram

No diagram for this concept: three fields and their flags are a list, and the reflective output above is the list.

### A concrete example

The fields being `private` on `Enum` rather than `protected` has a practical consequence worth demonstrating: there is no way to write an enum whose `name()` differs from its declared identifier, no matter what you do.

```java
public enum RestrictionSource {
    SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT;

    /** Overridable, so this changes every log line and every "%s". */
    @Override public String toString() {
        return name().toLowerCase(Locale.ROOT).replace('_', '-');
    }

    /**
     * name() is final and reads a private final field on Enum, so this is the
     * only spelling that can ever be the serialization identity and the
     * valueOf key. No override, no reflection, no subclass changes it.
     */
    public String canonicalName() {
        return name();
    }
}
```

Measured: `ADMIN.toString()` is `"admin"`, `ADMIN.name()` is `"ADMIN"`, and `RestrictionSource.valueOf("ADMIN")` succeeds while `valueOf("admin")` throws. The asymmetry is the point — the platform gave you one mutable-looking surface (`toString`) and kept the identity surface sealed, which is why the [`01a`](01a-implicit-members-and-identity.md) pitfall about round-tripping `toString` is a design consequence rather than an oversight.

Reflective mutation is closed too, and by a stronger mechanism than accessibility. Even with `--add-opens java.base/java.lang=ALL-UNNAMED`, `Field.setAccessible(true)` on `Enum.name` succeeds but `Field.set` throws `IllegalAccessException: Can not set final java.lang.String field`, because since Java 9 the reflective write to a `final` field of a non-`static` kind is refused outright rather than merely discouraged. The version-stale folklore that reflection can rewrite `final` fields is treated in [`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md).

### The gotcha

**Pitfall:** reading `Enum.java` from an older JDK and concluding the `hash` field does not exist, or from JDK 21 and concluding it always did. Measured across three source archives on this machine: JDK 11.0.27 and JDK 17.0.15 both declare exactly two fields and implement `hashCode()` as `return super.hashCode();`; JDK 21.0.7 declares three and caches. Symptom: an object-size calculation, a JOL layout listing, or a heap-histogram comparison that differs between LTS versions for a class nobody changed — and a colleague insisting your arithmetic is wrong because their JDK gives 20 bytes where yours gives 24 (before padding hides it). Fix: state the JDK version alongside any layout number, and read the source you are actually running rather than the source you remember.

> **Definition.** `java.lang.Enum` declares `private final String name` and `private final int ordinal`, both set by its `protected` constructor from the two parameters `javac` prepends to every enum constructor and both exposed by `final` accessors; JDK 21 adds a third, non-final `@Stable private int hash` for the lazy identity-hash cache.

---

## 3. Which `Enum` members are `final`, and why each had to be (3.10.6)

`[SOURCE]` `[PROVE]` `Enum` is unusually aggressive about `final`: of its instance methods, only `toString` is overridable. Each `final` is defending a specific invariant, and being able to say which is the difference between reciting the list and understanding it.

### Why it exists

An enum is a value with identity semantics, a total order, and a serialization contract that other parts of the platform depend on. `EnumSet` assumes `ordinal()` is a stable dense index. `EnumMap` assumes the same. `Enum.valueOf` assumes `name()` is the identity. Serialization assumes both. The `switch` desugaring assumes `ordinal()`. If any of those were overridable, a single badly-written enum could break `EnumSet`, `EnumMap`, `switch` and deserialization simultaneously — and the failure would surface far from the override. So the platform seals them rather than documenting a contract nobody would read.

### The mechanism

Measured by reflection on JDK 21.0.7, confirming rather than recalling:

```
Enum.equals    final? true
Enum.hashCode  final? true
Enum.compareTo final? true
Enum.name      final? true
```

The four bodies, with what each `final` protects.

**`equals` — `final`, identity.**

```java
public final boolean equals(Object other) {
    return this==other;
}
```

`final` because the uniqueness guarantee of [`01-basics.md`](01-basics.md) concept 3 makes identity *equivalent* to equality, and any other implementation would be either the same thing more slowly or wrong. It also means `==` and `equals` can never disagree for enums, which is why `==` on enums is idiomatic rather than a bug — the one reference type where that is true by construction. And it is what makes `EnumSet.contains`, which never calls `equals` at all, correct.

**`hashCode` — `final`, identity-derived, cached since 21.**

```java
public final int hashCode() {
    // Once initialized, the hash field value does not change.
    // HotSpot's identity hash code generation also never returns zero
    // as the identity hash code. This makes zero a convenient marker
    // for the un-initialized value for both @Stable and the lazy
    // initialization code below.
    int hc = hash;
    if (hc == 0) {
        hc = hash = System.identityHashCode(this);
    }
    return hc;
}
```

`final` because it must stay consistent with `equals`, and `equals` is identity. The caching is the JDK 21 change; on 11 and 17 the body is `return super.hashCode();`. The comment explains why zero works as the sentinel — HotSpot's identity-hash generator never produces zero, so there is no value that is both a legitimate hash and indistinguishable from "unset". The `@Stable` annotation on the field then lets a compiled caller treat the observed value as a constant. Note what this does *not* fix: the value is still identity-derived, so it still varies between JVM runs, so hash-ordered iteration over enum keys is still unreproducible — see [`01a`](01a-implicit-members-and-identity.md) concept 5.

**`compareTo` — `final`, ordinal-based.**

```java
public final int compareTo(E o) {
    Enum<?> other = o;
    Enum<E> self = this;
    if (self.getClass() != other.getClass() && // optimization
        self.getDeclaringClass() != other.getDeclaringClass())
        throw new ClassCastException();
    return self.ordinal - other.ordinal;
}
```

`final` because declaration order is the enum's *specified* natural order — `TreeSet`, `TreeMap`, `Collections.sort` and `Stream.sorted` all rely on it, as does the documented iteration order of `EnumSet` and `EnumMap`. An override could make an enum's natural order disagree with its `EnumSet` iteration order, which would be indefensible.

Two details in the body. The double class test accommodates constant bodies: `getClass()` differs between `CLIENT` (a `RestrictionSource$1`) and `ADMIN` (a `RestrictionSource`), so without the `getDeclaringClass()` fallback, sorting any collection containing a body constant would throw. The JDK's own comment marks the first test `// optimization` — it is a header read, versus a walk to find the declaring class. And `self.ordinal - other.ordinal` is a subtraction rather than `Integer.compare`, safe *only* because ordinals are small non-negative ints so the difference cannot overflow; the same idiom on arbitrary ints is the textbook broken comparator. Measured: `SELF_EXCLUDED.compareTo(ALL_BLOCKED)` is `1`, being 7 − 6.

**`clone` — `final`, throws.**

```java
/**
 * Throws CloneNotSupportedException.  This guarantees that enums
 * are never cloned, which is necessary to preserve their "singleton"
 * status.
 */
protected final Object clone() throws CloneNotSupportedException {
    throw new CloneNotSupportedException();
}
```

`[PROVE]` Measured: invoking it reflectively (with `--add-opens java.base/java.lang=ALL-UNNAMED`, since it is `protected`) threw `java.lang.CloneNotSupportedException`. The javadoc states the reason in one sentence, and it is the third door of the uniqueness guarantee. `protected` rather than `public` means no external caller can even reach it without reflection; `final` means no enum can widen it or make itself `Cloneable`. Note the signature the reflection attempt reported, which is itself the evidence: `protected final java.lang.Object java.lang.Enum.clone() throws java.lang.CloneNotSupportedException`.

Two more `final` members that complete the picture:

```java
@Deprecated(since="18", forRemoval=true)
@SuppressWarnings("removal")
protected final void finalize() { }
```

`final` and empty — so no enum can have a finalizer. That removes every enum from the finalizer queue and closes the resurrection route a finalizer otherwise opens on a singleton. The `@Deprecated(since="18", forRemoval=true)` is `Object.finalize`'s deprecation propagating; see [`../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`](../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md).

```java
public final Class<E> getDeclaringClass()
```

`final` because it is the *answer* to the `getClass()` problem — a constant body must not be able to lie about which enum it belongs to.

And the one that is not `final`:

```java
public String toString() {
    return name;
}
```

Overridable, deliberately, as the single sanctioned hook for a display form. Every trap that follows from overriding it — `valueOf` not round-tripping, log lines and `%s` changing, a JSON serializer that uses `toString` diverging from one that uses `name()` — is the price of that one affordance, and [`01a`](01a-implicit-members-and-identity.md) concept 1 has the pitfall.

### Diagram

No diagram for this concept: it is a member table with a justification per row, and the prose above is the table read aloud. The identity hash's storage in the mark word, which `hashCode` reads through `System.identityHashCode`, is D-124 in [`../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`](../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md).

### A concrete example

The practical payoff of knowing the list is that it tells you what an enum can and cannot be made to do, without trial and error:

```java
public final class RestrictionOrdering {

    /**
     * Cannot be done by overriding compareTo — it is final. An explicit
     * Comparator is the sanctioned route, and it is better anyway because
     * the ordering is named and does not hijack the natural order.
     */
    public static final Comparator<RestrictionType> BY_SEVERITY =
        Comparator.comparingInt(RestrictionType::severity)
                  .thenComparing(RestrictionType::code);

    /**
     * A TreeSet with the natural order gives declaration order; with the
     * comparator it gives severity order. Both are deterministic, unlike
     * a HashSet over the same keys.
     */
    public static NavigableSet<RestrictionType> bySeverity(
            Collection<RestrictionType> types) {
        NavigableSet<RestrictionType> ordered = new TreeSet<>(BY_SEVERITY);
        ordered.addAll(types);
        return ordered;
    }

    /**
     * Cannot be done by overriding equals or hashCode — both final. Grouping
     * several constants under one key needs an explicit key function.
     */
    public static Map<Queue, EnumSet<RestrictionType>> groupByQueue(
            Collection<RestrictionType> types) {
        EnumMap<Queue, EnumSet<RestrictionType>> grouped = new EnumMap<>(Queue.class);
        for (RestrictionType type : types) {
            grouped.computeIfAbsent(type.queue(), key -> EnumSet.noneOf(RestrictionType.class))
                   .add(type);
        }
        return grouped;
    }

    public enum Queue { PAYMENTS, TRADING, COMPLIANCE, SELF_SERVICE, LIFECYCLE }
}
```

Every one of those three is the *correct* design, and the `final` modifiers are what push you towards it. An overridable `compareTo` would tempt you into making severity the natural order, at which point `EnumSet` iteration order (ordinal) and `TreeSet` order (severity) would silently disagree. An overridable `equals` would tempt you into making two constants equal, at which point `EnumMap` — which never calls `equals` and indexes by ordinal — would disagree with `HashMap`, for the same two keys, in the same program.

### The gotcha

**Pitfall:** writing `enum X implements Comparable<X>` with your own `compareTo`, and being surprised that it does not compile. `Enum<E> implements Comparable<E>` already, with a `final` implementation, so the redeclaration collides: `error: compareTo(X) in X cannot override compareTo(E) in Enum; overridden method is final`. Symptom: a developer concluding that enums "cannot be sorted the way I want" and reaching for a `List<String>` of names instead. Fix: an explicit `Comparator`, as above — and prefer it even where you *could* override, because a named comparator documents which ordering is in play at the call site, whereas a hijacked natural order is invisible from `TreeSet::new`.

> **Definition.** On `java.lang.Enum`, `equals` (identity), `hashCode` (identity-derived, `@Stable`-cached since JDK 21), `compareTo` (ordinal difference, with a `getDeclaringClass()` fallback for body constants), `name`, `ordinal`, `getDeclaringClass`, `finalize` (empty) and `clone` (throws `CloneNotSupportedException`) are all `final`; only `toString` is overridable.

---
---

## Pitfalls

### Getting the enum type from a constant with `getClass()`

**Wrong**

```java
public static <E extends Enum<E>> EnumSet<E> universeOf(E anyConstant) {
    @SuppressWarnings("unchecked")
    Class<E> type = (Class<E>) anyConstant.getClass();
    return EnumSet.allOf(type);
}
```

Compiles — the generic signature cannot distinguish the two cases — and works for every enum in the codebase until it meets a constant with a body. Measured: `universeOf(RestrictionSource.CLIENT)` throws `java.lang.ClassCastException: class RestrictionSource$1 not an enum`, thrown by `EnumSet.noneOf` because `getEnumConstantsShared` returned `null` because `isEnum()` requires `getSuperclass() == java.lang.Enum.class` and `RestrictionSource$1`'s superclass is `RestrictionSource`.

**Right**

```java
public static <E extends Enum<E>> EnumSet<E> universeOf(E anyConstant) {
    return EnumSet.allOf(anyConstant.getDeclaringClass());
}
```

No cast and no `@SuppressWarnings`, because `Enum.getDeclaringClass()` is declared to return `Class<E>` exactly. Measured: works for `ADMIN` and `CLIENT` alike, returning all five constants. The `@SuppressWarnings` in the wrong version was the warning sign — an unchecked cast that the API could have given you correctly is usually the API being used wrongly.

**Why people believe it:** `getClass()` is the reflex for "what type is this object", and it is right for every enum without a constant body, which is most of them. The `@SuppressWarnings` needed to make it compile is the tell, and it gets added without thought.

### Treating `E$N` class names as stable identifiers

**Wrong**

```java
// In a heap-dump runbook, an APM class rule, or a test.
Class<?> clientArm = Class.forName("RestrictionSource$1");
```

The `N` is positional among the enum's anonymous classes and the JLS (§13.1) leaves the binary names of anonymous classes to the compiler. Adding a *body* to `SYSTEM_COMPLIANCE`, which is declared earlier than `CLIENT`, makes `RestrictionSource$1` the new constant and `RestrictionSource$2` the old one — an edit that reads as purely additive.

**Right**

```java
// Identify the constant, then ask it for its class if you actually need it.
Class<?> clientArm = RestrictionSource.CLIENT.getClass();
```

`name()` and the constant reference are stable contracts; the mangled subclass name is not. If a runbook genuinely needs to match the subclass in a heap histogram, express the rule as a prefix (`RestrictionSource$`) rather than a specific number, and note in the runbook that the number is positional.

**Why people believe it:** the name appears in stack traces, heap dumps and `javap` output, so it looks like an identifier the platform has committed to. It is a compiler artefact with the same stability guarantee as a local variable's slot number.

---

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Class flags, no constant bodies | `(0x4031) ACC_PUBLIC, ACC_FINAL, ACC_SUPER, ACC_ENUM` |
| Class flags, Form A (concrete method overridden) | `(0x4021)` — `ACC_FINAL` dropped, **not** abstract |
| Class flags, Form B (abstract member implemented) | `(0x4421)` — `ACC_ABSTRACT` (`0x0400`) added as well |
| Folklore correction | "constant bodies make the enum abstract" holds only for Form B. What always holds: `ACC_FINAL` is lost |
| Body subclass | `final class E$N extends E`, `private E$N(String, int)` forwarding to `E.<init>`, plus the overrides |
| No `this$0` on a body subclass | the enum class is a static context, so there is nothing to capture |
| Class-file cost | one extra class file per body constant. `GateType` produced four files |
| `InnerClasses` | Java 1.1. Informational; lets reflection answer `getSimpleName()` / `getEnclosingClass()`. Name index 0 for anonymous |
| `NestMembers` | JEP 181, Java 11. Lets `E$N` call `E`'s `private` constructor with a direct `invokespecial`, no `access$000` bridge |
| `PermittedSubclasses` | JEP 409, Java 17. The enum is **implicitly sealed**; `isSealed()` is `true` |
| No `ACC_SEALED` flag | sealedness in the class file *is* the attribute — same design as records, which have a `Record` attribute and no flag |
| Attribute count | a body enum carries all three at once, which makes it a good specimen for reading them |
| `E$N` numbering | positional among the enum's anonymous classes, compiler-chosen (JLS §13.1). Never reference it |
| `getClass()` on a body constant | `E$N`, and `E$N.isEnum()` is **false** — `isEnum()` needs `getSuperclass() == java.lang.Enum.class` |
| Correct type token from a constant | `getDeclaringClass()`, declared `Class<E>`, so no cast and no `@SuppressWarnings` |
| `Enum` fields | `private final String name`, `private final int ordinal`, `@Stable private int hash` |
| `hash` is new | absent on JDK 8, 11 and 17, where `hashCode()` is `return super.hashCode();` |
| Why `hash` cannot be `final` | it is lazily assigned; `@Stable` gives the JIT the constant-folding guarantee `final` would have |
| Why zero is the sentinel | HotSpot's identity-hash generator never returns zero |
| Constant object size | 12 B header + 4 B `name` + 4 B `ordinal` + 4 B `hash` = 24 B, derived. 20 → 24 padded on 17 |
| `Enum.<init>` | `protected`, called by `invokespecial` from the generated constructor with the injected `(String, int)` |
| `final` members | `equals`, `hashCode`, `compareTo`, `name`, `ordinal`, `getDeclaringClass`, `finalize`, `clone` |
| Only overridable member | `toString()` — the single sanctioned display hook, and the source of the `valueOf` round-trip trap |
| `equals` | `return this==other;` So `==` and `equals` can never disagree for an enum |
| Why `equals` is `final` | uniqueness makes identity equivalent to equality; any other body is slower or wrong |
| `hashCode` | `int hc = hash; if (hc == 0) { hc = hash = System.identityHashCode(this); } return hc;` |
| What caching does **not** fix | still identity-derived, so still varies per JVM run, so hash iteration order is still unreproducible |
| `compareTo` | `self.ordinal - other.ordinal` after a two-way class check |
| Why the subtraction is safe | ordinals are small and non-negative, so the difference cannot overflow. The same idiom on arbitrary ints is broken |
| Why the class check is doubled | body constants: `getClass()` differs, so `getDeclaringClass()` is the fallback. First test marked `// optimization` |
| Why `compareTo` is `final` | declaration order is the *specified* natural order that `TreeSet`, `sorted()`, `EnumSet` and `EnumMap` all rely on |
| `clone` | `protected final Object clone() throws CloneNotSupportedException`, unconditionally throws |
| `finalize` | `final` and empty, `@Deprecated(since="18", forRemoval=true)` — so **no enum can have a finalizer** |
| Overriding `compareTo` | compile error: "overridden method is final". Use a named `Comparator` |
| Reflective write to `name` | `setAccessible` succeeds; `Field.set` throws `IllegalAccessException` — final-field writes refused since Java 9 |
| Practical upshot of all the `final`s | grouping needs an explicit key function, custom ordering needs an explicit `Comparator` — both better designs |

---

## Self-test

**Q1.** "An enum with constant bodies becomes an abstract class." Correct that.

<details><summary>Answer</summary>

It loses `ACC_FINAL`; it becomes abstract only if a body implements an `abstract` member. Measured on JDK 21.0.7: `RestrictionSource`, where `CLIENT` overrides a *concrete* `reversibleByOperator()`, compiled to `flags: (0x4021) ACC_PUBLIC, ACC_SUPER, ACC_ENUM` — compare `RestrictionType`'s `(0x4031)`, and the only difference is the missing `0x0010` `ACC_FINAL` bit. `GateType`, which declares `public abstract String failureCode()` and implements it in each of three constant bodies, compiled to `flags: (0x4421)`, adding `ACC_ABSTRACT` (`0x0400`). So the invariant to state is the weaker one: a constant body costs the enum class its `ACC_FINAL`, because an anonymous subclass has to be able to exist. Both forms additionally gained `PermittedSubclasses` naming exactly their `E$N` subclasses — one for `RestrictionSource`, three for `GateType` — so both report `isSealed() == true`, and both gained `NestMembers` and `InnerClasses` entries for the same classes. Worth adding: there is no `ACC_SEALED` access flag; sealedness in the class file *is* the `PermittedSubclasses` attribute, exactly as record-ness is the `Record` attribute rather than a flag.

</details>

**Q2.** Why is `Enum.compareTo` `final`, and what are the two oddities in its body?

<details><summary>Answer</summary>

`final` because declaration order is the enum's *specified* natural order, and several parts of the platform depend on that agreeing with `ordinal()`: `TreeSet`, `TreeMap`, `Collections.sort` and `Stream.sorted` use `compareTo`, while `EnumSet` and `EnumMap` document iteration in ordinal order. An override could make a single enum's natural order disagree with its own `EnumSet` iteration order, in the same program, for the same constants. The two oddities. First, the class test is doubled: `if (self.getClass() != other.getClass() && self.getDeclaringClass() != other.getDeclaringClass()) throw new ClassCastException();`, with the JDK's own comment marking the first test `// optimization`. The fallback exists for constants with bodies, whose `getClass()` is `E$N` rather than `E` — without it, sorting any collection containing `RestrictionSource.CLIENT` would throw. The cheap test is a header read; the expensive one walks to find the declaring class, so the common no-bodies case short-circuits. Second, the result is `self.ordinal - other.ordinal` — a subtraction, not `Integer.compare`. That is the textbook broken comparator in general, because the difference of two arbitrary ints can overflow and flip the sign; it is safe here only because ordinals are small non-negative ints bounded by the constant count. Measured: `SELF_EXCLUDED.compareTo(ALL_BLOCKED)` is `1`, being 7 − 6. If you want a different ordering, an explicit `Comparator` is the only route — and it is better anyway, because it names the ordering at the call site instead of hijacking the natural one.

</details>

**Q3.** `java.lang.Enum` has three fields on JDK 21. Name them, say which is not `final`, and explain why it cannot be.

<details><summary>Answer</summary>

Measured by reflection on JDK 21.0.7: `private final java.lang.String name`, `private final int ordinal`, `private int hash`. The third is not `final` because it is lazily assigned by `hashCode()`: `int hc = hash; if (hc == 0) { hc = hash = System.identityHashCode(this); } return hc;`. A `final` field must be assigned in the constructor, and the whole point of the cache is to *not* compute the identity hash for constants nobody hashes. It carries the JDK-internal `@Stable` annotation instead, which tells the JIT the field is written at most once away from its default, so a compiled caller may fold the observed value in as a constant — the same guarantee `final` would give, without the eager assignment. Zero works as the "unset" marker because HotSpot's identity-hash generator never returns zero, which the source comment states explicitly. Two things to add. The field is new: JDK 11.0.27 and 17.0.15 both declare exactly two fields and implement `hashCode()` as `return super.hashCode();`, so any object-size arithmetic or JOL listing differs between LTS versions for a class nobody edited — 12 + 4 + 4 = 20 bytes padded to 24 on 17, 12 + 4 + 4 + 4 = 24 exactly on 21, so in practice the field landed in existing padding and is free. And the change is purely an optimisation: the value is still identity-derived, so it still varies between JVM runs, so hash-ordered iteration over enum keys is still unreproducible.

</details>


**Q4.** An enum with constant bodies carries three different attributes describing the same relationship. Name them, date them, and say what each one is for.

<details><summary>Answer</summary>

Measured on `RestrictionSource` (one body constant) and `GateType` (three), all three present on each. **`InnerClasses`**, from Java 1.1, is purely informational: it records each nested class with its simple name — or a zero name index for an anonymous one, which is why `getSimpleName()` on an anonymous class is the empty string — and it is how reflection answers `getSimpleName()` and `getEnclosingClass()` despite `javac` having flattened everything into peer class files. It is a *record* of nesting, not an enforcement of it. **`NestMembers`**, from JEP 181 in Java 11, is enforcement for *access*: it lists the nest members on the host, each member carries a `NestHost` pointing back, the JVM checks the relationship is mutual, and the payoff is that `RestrictionSource$1` can call `RestrictionSource`'s `private` constructor with a direct `invokespecial`. Before 11, `javac` synthesised a package-private `access$NNN` forwarder instead, which quietly widened a `private` member to its whole runtime package. **`PermittedSubclasses`**, from JEP 409 in Java 17, is enforcement for *extension*: it names exactly the `E$N` subclasses, so `isSealed()` returns `true` and the verifier rejects any other subclass at link time rather than relying on the constructor being private. Note there is no `ACC_SEALED` access flag — the attribute *is* the sealedness, exactly as a record's `Record` attribute is its record-ness with no `ACC_RECORD` flag. The three together are the same problem solved at three levels of JVM involvement, twenty years apart, and a body enum is one of the few constructs carrying all three at once.

</details>

**Q5.** Why can `Enum.hash` not be `final`, and what does `@Stable` buy instead?

<details><summary>Answer</summary>

It cannot be `final` because it is assigned lazily, and a `final` instance field must be assigned during construction. The whole purpose of the cache is to avoid computing an identity hash for constants nobody hashes: `int hc = hash; if (hc == 0) { hc = hash = System.identityHashCode(this); } return hc;`. An eager assignment in `Enum`'s constructor would force an identity hash for every constant of every enum at class-initialization time, which for HotSpot means touching the mark word on each one — exactly the cost the change was made to avoid. `@Stable` is the JDK-internal annotation that recovers the optimisation `final` would have given: it tells the JIT the field is written at most once away from its default value, so once a compiled method has observed a non-default value it may fold it in as a constant, with no re-read and no guard. Zero works as the "not yet computed" marker because HotSpot's identity-hash generator never returns zero — the JDK source comment states this explicitly, and it is also the reason `System.identityHashCode` can never be used to distinguish "the hash is zero" from "no hash yet". Two footnotes. The race is benign: two threads can both compute and both write, and both write the same value, since `System.identityHashCode` is stable per object once assigned. And the field is new — JDK 8, 11 and 17 all have `hashCode()` as `return super.hashCode();` with no field at all, so any object-layout arithmetic differs between LTS versions for a class nobody edited.

</details>

---

## Open questions

- **Unverified:** the 24-byte constant object size in concept 2. It is derived from the confirmed flags on this build (`UseCompressedOops = true`, `ObjectAlignmentInBytes = 8`) plus the standard 12-byte object header and the three field widths read from `Enum.java`, giving 12 + 4 + 4 + 4 = 24 with no padding needed. HotSpot may reorder fields, and the header's exact composition under compressed oops is version-sensitive. What would settle it: `org.openjdk.jol.info.ClassLayout.parseInstance(RestrictionSource.ADMIN).toPrintable()`, which would also show the reordering and any padding. JOL was not available in this environment. The related claim that the JDK 21 `hash` field is "free" because it lands in padding that already existed follows from the same derivation and inherits the same uncertainty.
- **Unverified:** whether the JLS *requires* `javac` to emit `PermittedSubclasses` for an enum with constant bodies, or whether that is this compiler's choice. Measured on JDK 21.0.7 that it does, for both the concrete-override form (`RestrictionSource` → one permitted subclass) and the abstract-member form (`GateType` → three), and that `Class.isSealed()` consequently returns `true` with `getPermittedSubclasses()` returning the synthetic classes. JLS §8.9 specifies that such an enum is implicitly sealed, but the normative wording — and therefore whether a conforming compiler could omit the attribute while remaining correct — was not read directly. What would settle it: JLS 21 §8.9.1 ("Enum Constants") and §8.1.1.2 ("`sealed` Classes"). The observable facts reported here are measured; only the *obligation* is unverified.
- **Unverified:** the exact JDK release that introduced the `hash` field on `java.lang.Enum`. Confirmed by reading `Enum.java` from three `src.zip` archives on this machine that JDK 11.0.27 and JDK 17.0.15 both implement `hashCode()` as `return super.hashCode();` with no field, and that JDK 21.0.7 has the caching form — so the change landed in 18, 19, 20 or 21. No JDK 18/19/20 install was available to narrow it, and no bug id is cited here rather than guessed. What would settle it: `git log -p src/java.base/share/classes/java/lang/Enum.java` in `openjdk/jdk`. Observable behaviour is unchanged either way.

---

**Leaves covered:** 3.10.4, 3.10.5, 3.10.6 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — §3.10's generated-shape diagram, D-117, is embedded in [`03-internals-enums.md`](03-internals-enums.md), and is drawn on `RestrictionSource` specifically so the missing `ACC_FINAL`, the `RestrictionSource$1` box and the `PermittedSubclasses`/`NestMembers` panel discussed in concept 1 all appear together
**Target version:** Java 21 LTS
**Lines:** 581
