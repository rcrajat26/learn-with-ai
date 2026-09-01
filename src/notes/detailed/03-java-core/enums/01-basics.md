# 03 Java Core — Enums — BASICS (§1.18, 1.18.1–1.18.5)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Nested class internals](../inheritance-and-dispatch/04-internals-nested-classes.md) · Next: [The implicit members and enum identity](01a-implicit-members-and-identity.md)

You already know how to declare an enum. What you probably do not have is the model that makes its behaviour predictable: **an enum is an ordinary final class whose entire instance population is created once, in order, by its own `<clinit>`, and whose superclass is chosen for you.** Every rule in this file falls out of that one sentence. The instances are `static final` fields, so class-initialization semantics apply. The superclass is `java.lang.Enum`, so single inheritance of implementation is spent and `equals`/`hashCode`/`compareTo` arrive already `final`. The population is fixed at class-init time, so no deserialization path, no reflective constructor and no `clone()` can widen it — which is what makes an enum the only singleton idiom in Java you do not have to defend.

§1.18 is covered across three files. **This one** owns the enum as a class, constant-specific bodies, and the uniqueness guarantee that follows. [`01a-implicit-members-and-identity.md`](01a-implicit-members-and-identity.md) owns the API you did not declare — `values()`, `valueOf`, `ordinal()`, `hashCode()`. [`01b-collections-patterns-and-guarantees.md`](01b-collections-patterns-and-guarantees.md) owns `EnumMap`/`EnumSet`, enum `switch`, the strategy and persisted-code patterns, and the pre-Java-5 ancestor. The generated class file — `$VALUES`, the synthetic `$values()` helper, `RestrictionSource$1`, the `<clinit>` instruction sequence, the `$SwitchMap` holder — is the subject of [`03-internals-enums.md`](03-internals-enums.md) and its two continuations.

All bytecode, reflective output and runtime results below were measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with version comparisons against **Oracle JDK 17.0.15** and **Oracle JDK 11.0.27**. Quoted library source is from that JDK's `lib/src.zip`. The two enums under test throughout §1.18 and §3.10 are:

```java
public enum RestrictionType {
    DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED,
    WITHDRAWAL_HELD, SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED, SELF_EXCLUDED,
    COOLING_OFF, DORMANT_FROZEN
}

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
```

`RestrictionType` is the flat case: ten constants, no bodies. `RestrictionSource` is the interesting case: one constant carries a class body, and that single fact changes the compiled shape of the whole enum. Both come straight from the QuizStakes restriction model, where **restriction identity is the pair (type, source), not the type alone** — `STAKE_BLOCKED` from `SYSTEM_ONBOARDING` lifts automatically at `AA-801 ACTIVATED`, whereas the same type from `ADMIN` does not, and `SELF_EXCLUDED` carries `reversibleByOperator = false`.

---

## 1. An enum is a class, and its superclass is already spent (1.18.1, 1.18.4)

Picture the declaration as a rewrite rather than a new kind of type. `enum RestrictionType { DEPOSIT_BLOCKED, … }` is shorthand for a `final class RestrictionType extends Enum<RestrictionType>` holding ten `public static final RestrictionType` fields, each initialised by a `new` in the class's static initialiser, in declaration order. Nothing else about it is special. It can have instance fields, instance methods, static methods, static initialisers, nested types and constructors. What it cannot have is a different superclass, because that slot is taken.

### Why it exists

Before Java 5 the only way to model a closed set of named alternatives was `public static final int STAKE_BLOCKED = 1;`. That gives you no type safety (any `int` is assignable), no namespace (two constant families collide), no printable form (a log line says `1`), and no compiler help when you switch (`case 47:` compiles happily against a three-value family). The `typesafe enum` pattern — a class with a private constructor and a fixed set of `public static final` instances — solved all four, but it was verbose, and every author reimplemented `values()`, ordering and serialization safety slightly differently, usually with a bug in the serialization part. Java 5's `enum` keyword is that pattern promoted into the language, with the error-prone parts generated. Hold onto that framing: everything the language does for an enum you could have written by hand, and §1.18.17 in [`01b`](01b-collections-patterns-and-guarantees.md) writes it by hand to show exactly what is automated.

### The mechanism

The rules that follow from "it is a class whose superclass is `Enum`":

- **The constructor is implicitly `private`.** Measured: `javap -p -v RestrictionType.class` prints `private RestrictionType();` with `flags: (0x0002) ACC_PRIVATE`. You may write `private` explicitly or omit it; you may not write `public` or `protected`. There is therefore no way for any caller — yours, the deserializer's, or reflection's — to reach it. Only the enum's own `<clinit>` calls it.
- **You cannot `extend` anything.** `enum RestrictionType extends AbstractRestriction` is a compile error, because the compiler is already writing `extends Enum<RestrictionType>` and Java has single inheritance of implementation. You *can* `implements` any number of interfaces, which is the whole basis of the strategy-enum pattern in [`01b`](01b-collections-patterns-and-guarantees.md).
- **You cannot subclass an enum either.** `class Custom extends RestrictionType` is rejected: the generated class carries `ACC_FINAL` whenever no constant has a body. Measured header for `RestrictionType`:

  ```
  public final class RestrictionType extends java.lang.Enum<RestrictionType>
    flags: (0x4031) ACC_PUBLIC, ACC_FINAL, ACC_SUPER, ACC_ENUM
    super_class: #44   // java/lang/Enum
  ```

  Where a constant *does* have a body the class loses `ACC_FINAL` — and gains a `PermittedSubclasses` attribute instead, which is concept 2.
- **Fields and methods are ordinary.** An instance field is per-constant state, assigned by the constructor. Because the constants are created during `<clinit>`, that state is set exactly once and — if you declare the fields `final` — is frozen before any other thread can reach the constant, since class initialization is a synchronised, once-only event under a JVM-held lock (JVMS §5.5). The `final`-field freeze that makes this safe publication is treated in [`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md).
- **The constants are `static final` fields of the enum class.** Measured flags on each: `(0x4019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL, ACC_ENUM`. So reading `RestrictionType.SELF_EXCLUDED` is a `getstatic`, and — being a field access on the class — it *triggers class initialization* on first touch. The first mention of any constant therefore runs every constructor, every instance initialiser and every static initialiser in the enum. An enum whose constructor does I/O is an enum that does I/O at an unpredictable moment. Class-init triggering is treated in full in [`../classes-and-initialization/03-internals-class-loading-and-init.md`](../classes-and-initialization/03-internals-class-loading-and-init.md).

`ACC_ENUM` (`0x4000`) is the class access flag the JVM uses to recognise an enum, and `Class.isEnum()` reads it. The JDK 21 implementation is stricter than just the flag:

```java
public boolean isEnum() {
    // An enum must both directly extend java.lang.Enum and have
    // the ENUM bit set; classes for specialized enum constants
    // don't do the former.
    return (this.getModifiers() & ENUM) != 0 &&
    this.getSuperclass() == java.lang.Enum.class;
}
```

Read the comment. It is telling you, in the JDK's own words, about the trap in concept 2.

One more consequence of enum-is-a-class that catches people: **an enum may be nested, and a nested enum is implicitly `static`.** `enum MoneyAction { … }` declared inside `RestrictionType` is a static member type, so it has no enclosing instance and no `this$0` field — which follows necessarily, since its constants are `static final` fields and a static field cannot depend on an instance. You may write `static` explicitly; it is redundant. Nested-type mechanics are in [`../inheritance-and-dispatch/02-nested-classes.md`](../inheritance-and-dispatch/02-nested-classes.md).

### Diagram

No diagram for this concept. The generated shape it describes is drawn as D-117 in [`03-internals-enums.md`](03-internals-enums.md), where the class-file evidence for it lives; putting the picture here would use vocabulary (`$VALUES`, `<clinit>` sequence) that this file has not established yet.

### A concrete example

A restriction type that carries per-constant state and behaviour, which is where an enum stops being a glorified `int` and starts being useful:

```java
public enum RestrictionType {
    DEPOSIT_BLOCKED("Deposits blocked", true, false, false),
    STAKE_BLOCKED("Stakes blocked", false, true, false),
    WITHDRAWAL_BLOCKED("Withdrawals blocked", false, false, true),
    DEPOSIT_LIMITED("Deposit limit applied", true, false, false),
    WITHDRAWAL_HELD("Withdrawal held for review", false, false, true),
    SOURCE_OF_FUNDS_REQUIRED("Source of funds required", true, false, true),
    ALL_BLOCKED("All money actions blocked", true, true, true),
    SELF_EXCLUDED("Client self-excluded", true, true, true),
    COOLING_OFF("Cooling-off period active", true, true, false),
    DORMANT_FROZEN("Account dormant", true, true, true);

    private final String description;
    private final boolean blocksDeposit;
    private final boolean blocksStake;
    private final boolean blocksWithdrawal;

    RestrictionType(String description,
                    boolean blocksDeposit,
                    boolean blocksStake,
                    boolean blocksWithdrawal) {
        this.description = description;
        this.blocksDeposit = blocksDeposit;
        this.blocksStake = blocksStake;
        this.blocksWithdrawal = blocksWithdrawal;
    }

    public String description() {
        return description;
    }

    public boolean blocks(MoneyAction action) {
        return switch (action) {
            case DEPOSIT -> blocksDeposit;
            case STAKE -> blocksStake;
            case WITHDRAWAL -> blocksWithdrawal;
        };
    }

    public enum MoneyAction { DEPOSIT, STAKE, WITHDRAWAL }
}
```

Three things to notice. The constructor is not marked `private` and does not need to be. The nested `MoneyAction` enum is legal because an enum is a class and may declare nested types, and it is implicitly `static`. And `blocks` is an instance method reading per-constant state, so `SELF_EXCLUDED.blocks(STAKE)` is a field read rather than a lookup in some external table that can drift out of step with the constant list.

The caller side, in `ClientRestrictions`:

```java
public final class ClientRestrictions {
    private final Set<RestrictionKey> active;

    public ClientRestrictions(Set<RestrictionKey> active) {
        this.active = Set.copyOf(active);
    }

    public void assertPermitted(RestrictionType.MoneyAction action) {
        for (RestrictionKey key : active) {
            if (key.type().blocks(action)) {
                throw new RestrictedActionException(
                    key.type().description() + " (source " + key.source() + ")");
            }
        }
    }

    public record RestrictionKey(RestrictionType type, RestrictionSource source) { }
}
```

`RestrictionKey` is the domain's (type, source) pair as a record, which is the right shape for it — see [`../records-and-sealed/01-basics.md`](../records-and-sealed/01-basics.md).

### The gotcha

**Pitfall:** believing that because an enum "is just constants", its constructor is cheap and its initialization is inert. The constants are `static final` fields, so the *first* read of any one of them initialises the class, which runs every constructor. An enum whose constructor calls `Currency.getInstance(code)`, reads a system property, or registers itself into a static map has moved that work to the first `getstatic` — which may be inside a request thread, inside a lock, or inside a static initialiser of another class. Symptom: a startup or first-request latency spike whose stack trace bottoms out at an innocuous field read; or an `ExceptionInInitializerError` on first touch followed by `NoClassDefFoundError` on every subsequent touch, which hides the original cause completely. Fix: keep enum constructors to field assignment. Put anything that can fail or block behind a lazily-initialised holder class, and never let an enum constructor reference another class's static state whose initialisation might reference back — that is a class-init deadlock, and it is drawn as D-108 in [`../classes-and-initialization/03-internals-class-loading-and-init.md`](../classes-and-initialization/03-internals-class-loading-and-init.md).

> **Definition.** An enum declaration is a `final class` implicitly extending `Enum<E>` whose complete instance population is a fixed, ordered set of `public static final` fields created by the class's own static initialiser through an implicitly `private` constructor.

---

## 2. A constant with a body is a subclass — and the class is no longer final (1.18.5)

The moment one constant gets `{ … }`, the enum stops being one class. Each constant with a body becomes an anonymous subclass, and the enum class itself must stop being `final` so those subclasses can exist. This is not an implementation detail you can ignore: it changes `getClass()`, it changes `Class.isEnum()`, and it changes what `PermittedSubclasses` says about your type.

### Why it exists

Sometimes the per-constant difference is *behaviour*, not data. `RestrictionSource.CLIENT` is not reversible by an operator; the other four are. You can express that with a boolean field — and often should — but where the difference is a whole algorithm, a field forces you into a `switch` inside the method, which the compiler cannot check for exhaustiveness against the constant list unless you write it as an exhaustive expression. A constant-specific body puts the behaviour next to the constant it belongs to, and — in the abstract-method form — makes forgetting one constant a compile error rather than a runtime fall-through.

### The mechanism

Two forms, and the second is the one to reach for.

**Form A — override a concrete method.** `RestrictionSource` above. The base `reversibleByOperator()` returns `true`; `CLIENT` overrides it. Measured on JDK 21.0.7, this produces two class files, and the header of the enum class is:

```
public class RestrictionSource extends java.lang.Enum<RestrictionSource>
  flags: (0x4021) ACC_PUBLIC, ACC_SUPER, ACC_ENUM
  interfaces: 0, fields: 6, methods: 6, attributes: 5
```

`ACC_FINAL` is gone. And the anonymous subclass:

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

The subclass is itself `final`, its constructor is `private`, and it does nothing but forward `name` and `ordinal` to the enum's constructor and override the one method. There is no `this$0` — the enum class is a static context, so the subclass captures nothing.

**Form B — an `abstract` method with a body per constant.** Now the enum class is *abstract*:

```java
public enum GateType {
    AGE_ELIGIBILITY {
        @Override public String failureCode() { return "AO-119"; }
    },
    JURISDICTION {
        @Override public String failureCode() { return "AO-129"; }
    },
    SCREENING {
        @Override public String failureCode() { return "AA-599"; }
    };
    public abstract String failureCode();
}
```

Measured header:

```
public abstract class GateType extends java.lang.Enum<GateType>
  flags: (0x4421) ACC_PUBLIC, ACC_SUPER, ACC_ABSTRACT, ACC_ENUM
PermittedSubclasses:
  GateType$1
  GateType$2
  GateType$3
InnerClasses:
  final #32;   // class GateType$1
  final #36;   // class GateType$2
  final #40;   // class GateType$3
```

**Insight:** the enum is *implicitly sealed*. Since Java 17 (JEP 409, which finalised sealed classes) `javac` emits a `PermittedSubclasses` attribute naming exactly the constant subclasses, so `GateType.class.isSealed()` returns `true` and `getPermittedSubclasses()` returns the three synthetic classes. Measured on `RestrictionSource`: `isSealed = true`, `permitted = [class RestrictionSource$1]`, and `NestMembers: RestrictionSource$1` alongside it. This is what makes "the class is not final, but nothing else can subclass it" enforceable by the verifier at link time rather than resting on constructor accessibility alone. Before 17 the non-final enum class was protected only by its `private` constructor — already sufficient in practice, since a subclass must call some superclass constructor — but the attribute makes the intent explicit and machine-checkable. Sealed classes as a language feature are in [`../records-and-sealed/01-basics.md`](../records-and-sealed/01-basics.md).

Note carefully which form the JLS requires to be `abstract`. Older writing — including this topic's own syllabus at leaf 3.10.4 — says a constant-body enum "becomes an abstract class". That is true only for Form B. In Form A the base method has an implementation, nothing is abstract, and the measured flags carry no `ACC_ABSTRACT`. The invariant that always holds is the weaker one: **a constant body costs the enum class its `ACC_FINAL`.**

The syntactic details that catch people:

- A constant with a body needs the `{ … }` immediately after the constant name and before the comma: `CLIENT { … },` or, if last, `CLIENT { … };`.
- The semicolon after the last constant becomes mandatory as soon as the enum declares any member after the constant list.
- A constant body may not declare a constructor. It is an anonymous class body, and anonymous classes have no constructors — which is why the compiler generates `RestrictionSource$1(String, int)` for it.
- A constant body cannot be referred to as a type. There is no source syntax for `RestrictionSource$1`, so you cannot declare a variable of it, cast to it, or name it in a `catch` or a `permits` clause.
- A constant body may not access the enum's non-`static` members except through inheritance, because it is created during `<clinit>` in a static context.

### Diagram

The full before-and-after class-file evidence for this concept is D-117, embedded in [`03-internals-enums.md`](03-internals-enums.md) concept 1, where the `<clinit>` instruction sequence that constructs `RestrictionSource$1` is read alongside it.

### A concrete example

The gate model, where per-constant behaviour is a genuine algorithm rather than a flag:

```java
public enum GateType {
    AGE_ELIGIBILITY {
        @Override public String failureCode() { return "AO-119"; }
        @Override public boolean holds(Application application) {
            return application.applicantAge() >= 18;
        }
    },
    JURISDICTION {
        @Override public String failureCode() { return "AO-129"; }
        @Override public boolean holds(Application application) {
            return application.jurisdiction().isPermitted();
        }
    },
    SCREENING {
        @Override public String failureCode() { return "AA-599"; }
        @Override public boolean holds(Application application) {
            return application.screeningVerdict().outcome() != Outcome.PROHIBITED;
        }
    };

    public abstract String failureCode();

    public abstract boolean holds(Application application);

    public static Optional<GateType> firstFailing(Application application) {
        for (GateType gate : values()) {
            if (!gate.holds(application)) {
                return Optional.of(gate);
            }
        }
        return Optional.empty();
    }
}
```

Add a fourth gate and the compiler forces you to write both methods for it. That is the property a `switch` inside a single `holds` method would not give you unless the switch were an exhaustive expression — and it is why the abstract-method-per-constant form survives despite its verbosity. The trade-off, stated honestly: **each constant with a body is an extra class file**, so a 20-constant enum with bodies is 21 classes to load, verify and initialise rather than one. At `GateType`'s size that is irrelevant; at 200 constants it is a measurable startup cost, and the field-plus-`switch` form is the better trade.

### The gotcha

**Pitfall:** `getClass()` on a constant with a body does not return the enum class, and `isEnum()` on the result is `false`. Measured on JDK 21.0.7:

```
RestrictionSource.CLIENT.getClass()   ->  class RestrictionSource$1
RestrictionSource.ADMIN.getClass()    ->  class RestrictionSource
CLIENT.getClass().isEnum()            ->  false
ADMIN.getClass().isEnum()             ->  true
CLIENT.getDeclaringClass()            ->  class RestrictionSource
```

Symptom: framework code that keys on `value.getClass()` — a Jackson serializer registry, a JPA `AttributeConverter` lookup, a Spring `Converter` resolution, a hand-rolled `Map<Class<?>, Handler>` — works for four constants and fails for the fifth, with an error naming a class the developer never wrote. The same asymmetry breaks any `if (x.getClass().isEnum())` guard. Fix: **always use `getDeclaringClass()`, never `getClass()`, when you want the enum type of a constant.** `Enum.getDeclaringClass()` exists precisely for this and its javadoc says so: "The value returned by this method may differ from the one returned by the `Object#getClass` method for enum constants with constant-specific class bodies."

> **Definition.** A constant-specific class body compiles to a `final` anonymous subclass `E$n` of the enum class, which therefore loses `ACC_FINAL` and — since Java 17 — gains a `PermittedSubclasses` attribute listing exactly those subclasses; the enum class is additionally `ACC_ABSTRACT` only when a body implements an `abstract` member.

---

## 3. Nothing can produce a second instance of a constant (1.18.2, 1.18.3)

This is the guarantee that makes an enum worth using for identity. The claim is strong: within one class loader's view of the type, the ten `RestrictionType` objects created by `<clinit>` are the only ten that will ever exist, and no serialization stream, no reflective constructor call and no `clone()` can add an eleventh. Every other singleton idiom in Java has to *defend* against those routes; an enum has them closed by specification.

### Why it exists

The classic singleton has three holes. `new` is closed by a private constructor, but Java serialization does not call constructors — it allocates and populates fields directly — so a serializable singleton needs `readResolve` to fold the reconstructed instance back to the canonical one, and getting that right (including making every non-transient reference field `transient` to defeat a stolen-reference attack) is genuinely hard. Reflection can call a private constructor after `setAccessible(true)`, so the constructor must additionally throw if the instance already exists. And `clone()` must be overridden to throw. Enums close all three in the platform, once, correctly, so that no application author ever gets it wrong.

### The mechanism

Three doors, each independently shut.

**Door 1 — the constructor.** Measured `flags: (0x0002) ACC_PRIVATE` on `RestrictionType()`, with no source syntax to widen it. Only `<clinit>` calls it, and `<clinit>` runs at most once per class per loader under a JVM-held initialization lock (JVMS §5.5). That is also why enum initialization is thread-safe with no code from you: the JVM serialises it.

**Door 2 — serialization.** `[PROVE]` The specification says enum constants are serialized by name and that the standard hooks are ignored. The measurement:

```java
enum BonusState implements Serializable {
    GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK;

    private Object readResolve()  { System.out.println("readResolve CALLED");  return GRANTED; }
    private Object writeReplace() { System.out.println("writeReplace CALLED"); return GRANTED; }
    private void readObject(ObjectInputStream in) { System.out.println("readObject CALLED"); }
}
```

Round-tripping `BonusState.CLAWED_BACK` through `ObjectOutputStream`/`ObjectInputStream` on JDK 21.0.7 printed **none** of those three lines, and the result was:

```
round trip = CLAWED_BACK, identical = true
```

All three hooks were bypassed. The stream form is the constant's `name()` — measured, an 81-byte stream for one `RestrictionType` constant, containing the literal text `SELF_EXCLUDED` — and `ObjectInputStream` resolves it by calling `Enum.valueOf(enumType, name)`, which returns the existing constant. `java.lang.Enum` also nails the back door shut from its own side:

```java
@java.io.Serial
private void readObject(ObjectInputStream in) throws IOException,
    ClassNotFoundException {
    throw new InvalidObjectException("can't deserialize enum");
}

@java.io.Serial
private void readObjectNoData() throws ObjectStreamException {
    throw new InvalidObjectException("can't deserialize enum");
}
```

So even a hand-crafted stream that claims to hold a field-by-field enum instance is rejected. Note the consequence for evolution: because the wire form is the *name*, renaming a constant breaks every serialized form in flight, and deleting one makes old streams fail to resolve. That is the same constraint as the wire-and-database rule in §3.10.14, arrived at from the other direction. Java serialization as a whole, including its role as a deserialization-gadget attack surface, is in [`../serialization/02-serialization.md`](../serialization/02-serialization.md).

**Door 3 — reflection.** `[PROVE]` Measured:

```java
Constructor<?> c = RestrictionType.class.getDeclaredConstructors()[0];
c.setAccessible(true);
c.newInstance("FORGED", 99);
```

produces

```
java.lang.IllegalArgumentException: Cannot reflectively create enum objects
```

The check is inside `Constructor.newInstance`, which rejects any constructor whose declaring class has `ACC_ENUM` set. `setAccessible(true)` *succeeded* — the block is not an accessibility check, so no amount of `--add-opens` moves it.

And `clone()`, for completeness, from `Enum`:

```java
protected final Object clone() throws CloneNotSupportedException {
    throw new CloneNotSupportedException();
}
```

Measured: invoking it reflectively threw `java.lang.CloneNotSupportedException`. It is `final`, so no enum can make itself cloneable.

**The class-loader caveat, stated precisely.** The guarantee is *per class*, and a class's identity is the pair (binary name, defining loader). Two loaders that each *define* `RestrictionType` produce two unrelated `Class` objects and therefore twenty constant objects, and `==` between constants from the two is false — as is `equals`, since `Enum.equals` is `this == other`. Symptom: a `switch` or an `EnumMap` that mysteriously misses in a container with per-application loaders, in an OSGi bundle graph, or across a Spring DevTools restart-classloader boundary. This is not a hole in the enum guarantee; it is the ordinary meaning of class identity, and the same thing happens to the `static final` fields of any class. But "an enum constant is a JVM-wide singleton" is the loose phrasing that hides it. The precise claim is: **one instance per constant per class, and a class is per defining loader.**

### Diagram

No diagram for this concept: the evidence is three measured failures, quoted above, and a picture of a closed door adds nothing.

### A concrete example

The enum singleton, with the state that makes it a singleton rather than a bare constant:

```java
public enum LedgerSequencer {
    INSTANCE;

    private final AtomicLong sequence = new AtomicLong();

    public long next() {
        return sequence.incrementAndGet();
    }
}
```

That is the whole thing, and it is thread-safe, lazily initialised, serialization-proof and reflection-proof. Compare the hand-written equivalent that reaches the same guarantees:

```java
public final class LedgerSequencerClassic implements Serializable {
    private static final LedgerSequencerClassic INSTANCE = new LedgerSequencerClassic();

    private final transient AtomicLong sequence = new AtomicLong();

    private LedgerSequencerClassic() {
        if (INSTANCE != null) {
            throw new IllegalStateException("already constructed");
        }
    }

    public static LedgerSequencerClassic getInstance() {
        return INSTANCE;
    }

    public long next() {
        return sequence.incrementAndGet();
    }

    @java.io.Serial
    private Object readResolve() {
        return INSTANCE;
    }
}
```

Six extra constructs — the `static final` field, the accessor, the reflection guard, `Serializable`, `readResolve`, and `transient` on the mutable field so a crafted stream cannot substitute a different `AtomicLong` — and it is still weaker: the reflection guard runs after `super()` and reads a field the attacker's stream can influence, and `readResolve` being `private` would not be inherited by a subclass (closed here only by `final` on the class). *Effective Java* Item 3 (*Enforce the singleton property with a private constructor or an enum type*) recommends the enum "unless the singleton must extend a superclass other than `Enum`" — the one genuine limitation, and the reason the classic form has not disappeared.

**Interview:** "Why is an enum the best singleton?" The answer is three sentences, not one: the constructor is unreachable, because `javac` forces it `private` and the JVM refuses reflective construction on an `ACC_ENUM` class with `IllegalArgumentException: Cannot reflectively create enum objects`; serialization cannot duplicate it, because the specification serialises by name and ignores `writeReplace`/`readResolve`/`readObject`; and initialization is thread-safe for free, because it happens in `<clinit>` under the JVM's class-init lock. Then add the two caveats, because that is what separates a strong answer from a recited one: it cannot extend anything, and "singleton" means per class loader.

### The gotcha

**Pitfall:** treating "enum constants are singletons" as licence to hang mutable state off them. An enum constant is a `static final` field, so mutable state on it is *global* mutable state wearing unusually respectable syntax, and it is never collected while the class is loaded. A `private final Map<ClientId, Integer> attempts = new ConcurrentHashMap<>();` field on an enum constant is a process-lifetime cache with no eviction and no ownership — indistinguishable from a `public static final` map except that it looks like a constant. Symptom: a slow heap climb attributed vaguely to "the enum", plus cross-test pollution, because the state survives every test in the JVM that touches the class. Fix: enum constants carry `final` per-constant *configuration* — descriptions, codes, thresholds, behaviour. Anything with a lifecycle belongs in an injected bean whose scope you chose deliberately.

> **Definition.** For each enum constant exactly one instance exists per (class, defining loader), because the constructor is `ACC_PRIVATE` and called only from `<clinit>`, reflective construction of an `ACC_ENUM` class is refused, `clone` is `final` and throws, and serialization is by `name()` with `writeReplace`/`readResolve`/`readObject` specified as ignored.

---

## Pitfalls

### Assuming `getClass()` returns the enum type

**Wrong**

```java
public final class SourceLabels {
    private final Map<Class<?>, String> labels = Map.of(
        RestrictionSource.class, "restriction source");

    public String label(RestrictionSource source) {
        return labels.getOrDefault(source.getClass(), "unknown");
    }
}
```

Measured behaviour:

```
label(RestrictionSource.ADMIN)  -> restriction source
label(RestrictionSource.CLIENT) -> unknown
```

`CLIENT` carries a constant-specific body, so `CLIENT.getClass()` is `RestrictionSource$1` — a class that is not in the map and that no source file mentions.

**Right**

```java
public String label(RestrictionSource source) {
    return labels.getOrDefault(source.getDeclaringClass(), "unknown");
}
```

`getDeclaringClass()` returns `RestrictionSource` for every constant, body or not, so both resolve to `restriction source`.

**Why people believe it:** for the overwhelming majority of enums — every one without a constant body — `getClass()` and `getDeclaringClass()` return the same thing, so the habit is reinforced by hundreds of correct uses before the first enum with a body arrives. The failure then appears in framework code far from the enum that changed.

### Doing real work in an enum constructor

**Wrong**

```java
public enum SettlementCurrency {
    GBP("GBP"), EUR("EUR"), USD("USD");

    private final Currency currency;
    private final BigDecimal minStake;

    SettlementCurrency(String code) {
        this.currency = Currency.getInstance(code);
        this.minStake = new BigDecimal(
            System.getProperty("quizstakes.minStake." + code, "0.10"));
    }
}
```

Every field read of any constant initialises the class, which now performs three `Currency` lookups and three system-property reads plus three `BigDecimal` parses. Worse, a typo'd or absent property with a non-numeric value throws `NumberFormatException` inside `<clinit>`, which surfaces as `ExceptionInInitializerError` — and every *subsequent* touch of `SettlementCurrency` throws `NoClassDefFoundError: Could not initialize class SettlementCurrency`, with the original `NumberFormatException` nowhere in the trace.

**Right**

```java
public enum SettlementCurrency {
    GBP("GBP"), EUR("EUR"), USD("USD");

    private final String code;

    SettlementCurrency(String code) {
        this.code = code;
    }

    public String code() {
        return code;
    }

    public Currency currency() {
        return Holder.CURRENCIES.get(this);
    }

    public BigDecimal minStake() {
        return Holder.MIN_STAKES.get(this);
    }

    /** Initialised on first call to currency() or minStake(), not on first field read. */
    private static final class Holder {
        private static final Map<SettlementCurrency, Currency> CURRENCIES;
        private static final Map<SettlementCurrency, BigDecimal> MIN_STAKES;

        static {
            EnumMap<SettlementCurrency, Currency> currencies =
                new EnumMap<>(SettlementCurrency.class);
            EnumMap<SettlementCurrency, BigDecimal> minStakes =
                new EnumMap<>(SettlementCurrency.class);
            for (SettlementCurrency value : values()) {
                currencies.put(value, Currency.getInstance(value.code));
                minStakes.put(value, new BigDecimal(
                    System.getProperty("quizstakes.minStake." + value.code, "0.10")));
            }
            CURRENCIES = Collections.unmodifiableMap(currencies);
            MIN_STAKES = Collections.unmodifiableMap(minStakes);
        }
    }
}
```

The constructor is field assignment only, so `SettlementCurrency.GBP` is now free and cannot fail. The parsing moved into a separate holder class whose `<clinit>` runs on first use of `currency()` or `minStake()`, so a bad property fails at a call site you can point at, and it fails only for callers that actually need the value.

**Why people believe it:** the constructor is the obvious place for derived state, and for a plain class it *is* the right place. What makes an enum different is that its constructor runs during class initialization of a type whose fields are read incidentally all over the codebase, so the moment of execution is not under the caller's control.

### Hanging mutable state on a constant

**Wrong**

```java
public enum RateLimiter {
    STAKE_RESERVATION, CARD_DEPOSIT, CARD_WITHDRAWAL;

    private final Map<ClientId, Integer> attempts = new ConcurrentHashMap<>();

    public boolean allow(ClientId clientId, int cap) {
        return attempts.merge(clientId, 1, Integer::sum) <= cap;
    }
}
```

Three process-lifetime maps with no eviction, keyed by client. At 380k monthly active clients and roughly 40 bytes per `ConcurrentHashMap` node plus a 16-byte `ClientId` and a boxed `Integer`, three maps at full population is on the order of tens of megabytes that nothing will ever free — and every test in the JVM shares the counters.

**Right**

```java
public final class RateLimiter {
    private final Cache<ClientId, Integer> attempts;
    private final RateLimitedAction action;

    public RateLimiter(RateLimitedAction action, Cache<ClientId, Integer> attempts) {
        this.action = action;
        this.attempts = attempts;
    }

    public boolean allow(ClientId clientId, int cap) {
        return attempts.asMap().merge(clientId, 1, Integer::sum) <= cap;
    }

    public enum RateLimitedAction { STAKE_RESERVATION, CARD_DEPOSIT, CARD_WITHDRAWAL }
}
```

The enum is back to being a closed set of names. The state lives in an injected, evictable cache whose lifecycle and bound the caller chose, and a test gets a fresh one.

**Why people believe it:** the enum-singleton advice is correct and widely repeated, so "put it on an enum constant" reads as the idiomatic way to get one instance. What the advice does not say — and what this pitfall is — is that an enum constant's lifetime is the class's lifetime, which is almost always the process's lifetime, and that is a lifecycle choice you should make explicitly rather than inherit.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Compiled shape, no constant bodies | `final class E extends Enum<E>`; `flags: (0x4031) ACC_PUBLIC, ACC_FINAL, ACC_SUPER, ACC_ENUM` |
| Compiled shape, a constant has a body | `ACC_FINAL` is **dropped**; `PermittedSubclasses` lists the `E$n` subclasses (Java 17+, JEP 409) |
| Compiled shape, an `abstract` member | additionally `ACC_ABSTRACT`. A concrete override does **not** make the class abstract |
| Constant field flags | `(0x4019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL, ACC_ENUM` — so a read is a `getstatic` and triggers class init |
| Constructor | implicitly `ACC_PRIVATE`; descriptor `(Ljava/lang/String;I)V` — `name` and `ordinal` are injected |
| `ACC_ENUM` | `0x4000`. `Class.isEnum()` tests the bit **and** `getSuperclass() == java.lang.Enum.class` |
| Superclass | always `java.lang.Enum` — an enum may `implements` but can never `extends` |
| Subclassing an enum | impossible from source: `ACC_FINAL`, or `PermittedSubclasses` naming only the compiler's own `E$n` |
| Nested enum | implicitly `static`; no enclosing instance, no `this$0` |
| Constant body → class file | one extra class file per constant with a body; `E$1` is `final`, its constructor `private` |
| `getClass()` on a body constant | returns `E$n`, and `E$n.isEnum()` is **false** — always use `getDeclaringClass()` |
| Constant body limits | no constructor, not nameable as a type, no access to non-static enum members except by inheritance |
| Thread safety of init | free: `<clinit>` runs once per class per loader under the JVM's initialization lock (JVMS §5.5) |
| Serialization | by `name()` only; `writeReplace`/`readResolve`/`readObject` **ignored** by specification |
| `Enum.readObject` | declared `private` on `Enum`, throws `InvalidObjectException("can't deserialize enum")` |
| Reflective construction | `Constructor.newInstance` → `IllegalArgumentException: Cannot reflectively create enum objects` |
| `setAccessible(true)` | succeeds; the reflection block is **not** an accessibility check, so `--add-opens` does not help |
| `clone()` | `protected final` on `Enum`, unconditionally throws `CloneNotSupportedException` |
| Uniqueness scope | one instance per constant per **(binary name, defining loader)** — not literally JVM-wide |
| Enum as singleton | *Effective Java* Item 3; the right default unless the singleton must extend a class other than `Enum` |
| Enum constructor discipline | field assignment only. Anything that can fail or block goes in a lazily-initialised holder class |
| Mutable state on a constant | global, uncollectable, test-polluting. `final` configuration only |

---

## Self-test

**Q1.** `RestrictionSource.CLIENT.getClass()` and `RestrictionSource.ADMIN.getClass()` return different classes. Why, and what breaks?

<details><summary>Answer</summary>

`CLIENT` carries a constant-specific class body, so `javac` compiled it as an anonymous subclass. Measured on JDK 21.0.7: `CLIENT.getClass()` is `RestrictionSource$1`, `ADMIN.getClass()` is `RestrictionSource`. Because `RestrictionSource$1` does not *directly* extend `java.lang.Enum` — it extends `RestrictionSource` — `Class.isEnum()` returns **false** for it; the JDK's `isEnum` implementation tests both the `ACC_ENUM` bit and `getSuperclass() == java.lang.Enum.class`, and its source comment says exactly why. What breaks is anything keyed on `getClass()`: a serializer registry, a converter lookup, a `Map<Class<?>, Handler>`, an `if (x.getClass().isEnum())` guard — all correct for the constants without bodies and wrong for the ones with. The fix is `getDeclaringClass()`, which returns `RestrictionSource` for every constant and exists for exactly this reason.

</details>

**Q2.** You add `private Object readResolve()` to an enum to force deserialization through a canonical instance. What happens?

<details><summary>Answer</summary>

Nothing — the method is never called. Measured on JDK 21.0.7 with an enum declaring `readResolve`, `writeReplace` and `readObject`, all three printing to stdout: a full `ObjectOutputStream`/`ObjectInputStream` round trip of `CLAWED_BACK` printed none of the three lines and returned the identical constant. The serialization specification defines the enum wire form as the constant's `name()` and states that those hooks are ignored for enum types; `ObjectInputStream` resolves the name by calling `Enum.valueOf`. `java.lang.Enum` additionally declares its own `private void readObject` and `readObjectNoData`, both throwing `InvalidObjectException("can't deserialize enum")`, so a hand-crafted stream claiming a field-by-field enum instance is rejected outright. The upshot: you cannot customise enum serialization at all, and you do not need to — the guarantee you were trying to add is already unconditional. What this *does* constrain is evolution: since the wire form is the name, renaming or deleting a constant breaks streams in flight.

</details>

**Q3.** When does a constant-specific body make the enum class `abstract`, and when does it only make it non-final?

<details><summary>Answer</summary>

The body always costs the class its `ACC_FINAL`, because an anonymous subclass has to be able to exist. Whether the class is also `ACC_ABSTRACT` depends on whether anything is left unimplemented. Measured: `RestrictionSource`, where `CLIENT` overrides a *concrete* `reversibleByOperator()`, compiled to `flags: (0x4021) ACC_PUBLIC, ACC_SUPER, ACC_ENUM` — non-final, not abstract. `GateType`, which declares `public abstract String failureCode()` and implements it in each of three constant bodies, compiled to `flags: (0x4421) ACC_PUBLIC, ACC_SUPER, ACC_ABSTRACT, ACC_ENUM`. Both gained a `PermittedSubclasses` attribute naming their `E$n` subclasses — `RestrictionSource$1` for the first, `GateType$1`/`$2`/`$3` for the second — so both report `isSealed() == true`, which is the Java 17+ mechanism (JEP 409) that makes "not final, but nothing else may subclass it" enforceable by the verifier rather than resting on the private constructor alone. Reach for the abstract-method form when you want the compiler to reject a newly added constant that forgets to supply the behaviour; reach for a field plus a switch when the enum is large, because each body costs a class file.

</details>

**Q4.** "An enum constant is a JVM-wide singleton." Sharpen that claim.

<details><summary>Answer</summary>

The precise claim is: exactly one instance exists per constant per **(binary name, defining class loader)** pair — that is, per `Class` object, not per JVM. Three doors enforce it within that scope. The constructor is `ACC_PRIVATE` (measured `flags: (0x0002)`) and is called only from `<clinit>`, which the JVM runs at most once per class per loader under an initialization lock. Reflective construction is refused by `Constructor.newInstance` with `IllegalArgumentException: Cannot reflectively create enum objects` for any `ACC_ENUM` declaring class, and `setAccessible(true)` does not help, because that is not an accessibility check. Serialization is by `name()` with `writeReplace`/`readResolve`/`readObject` ignored, plus `Enum`'s own `readObject` throwing `InvalidObjectException`. But two class loaders that each *define* the type produce two unrelated `Class` objects and two full sets of constants, and `==` — and therefore `equals`, which is `this == other` — is false across them. That surfaces as an `EnumMap` that misses or a `switch` that falls through to `default` in a servlet container with per-application loaders, in an OSGi bundle graph, or across a Spring DevTools restart-classloader boundary. It is not a hole in the enum guarantee; it is what class identity means. The loose phrasing simply hides it.

</details>

**Q5.** An enum's constructor parses a system property. Describe the failure mode precisely.

<details><summary>Answer</summary>

The constants are `static final` fields, so the *first* read of any one of them — which may be an incidental `getstatic` deep in unrelated code — initialises the class and runs every constructor. If the property is absent or non-numeric, `new BigDecimal(property)` throws `NumberFormatException` inside `<clinit>`. The JVM wraps any `Throwable` escaping a static initialiser in `ExceptionInInitializerError` (the `NumberFormatException` is its `cause`), marks the class **erroneous**, and — this is the part that makes it hard to diagnose — every *subsequent* touch of the class throws `NoClassDefFoundError: Could not initialize class SettlementCurrency` with no cause attached at all. So the team sees a `NoClassDefFoundError` for a class that is obviously on the classpath, and the original `NumberFormatException` appears exactly once, in whichever log line happened to catch the very first failure. Fix: keep enum constructors to field assignment and move anything that can fail into a lazily-initialised private holder class, so the failure lands at a call site you can point at.

</details>

**Q6.** Why is enum initialization thread-safe without you writing anything, and what exactly is the guarantee?

<details><summary>Answer</summary>

Because the constants are created by the class's `<clinit>`, and JVMS §5.5 specifies that class initialization is performed under a per-class initialization lock: exactly one thread runs `<clinit>`, any other thread arriving concurrently blocks until it completes, and a thread that arrives afterwards sees the class as already initialised and does not re-run it. So each constant is constructed once, and the constructor's writes are complete before any other thread can observe the constant field — the release of the initialization lock provides the happens-before edge. If the per-constant fields are `final`, the final-field freeze gives the same guarantee independently. Two caveats worth stating. First, this is initialization safety, not general thread safety: a *mutable* field on a constant is as unsafe as any other shared mutable field, and no amount of enum-ness helps. Second, the same lock is what makes a cyclic dependency between two enums' static initialisers a genuine deadlock rather than a benign race — treated in [`../classes-and-initialization/03-internals-class-loading-and-init.md`](../classes-and-initialization/03-internals-class-loading-and-init.md).

</details>

---

## Open questions

- **Unverified:** whether the JLS *requires* `javac` to emit `PermittedSubclasses` for an enum with constant bodies, or whether that is this compiler's choice. Measured on JDK 21.0.7 that it does, for both the abstract form (`GateType` → three permitted subclasses) and the concrete-override form (`RestrictionSource` → one), and that `Class.isSealed()` consequently reports `true`. JEP 409 finalised sealed classes in Java 17, and JLS §8.9 specifies that an enum with constant bodies is implicitly sealed — but the exact normative wording, and therefore whether a conforming compiler could omit the attribute, was not read. What would settle it: JLS 21 §8.9.1 ("Enum Constants") and §8.1.1.2 ("`sealed` Classes") read directly. Nothing in these notes depends on the answer — the observable facts (`ACC_FINAL` absent, `isSealed()` true on this build) are measured.

---

**Leaves covered:** 1.18.1, 1.18.2, 1.18.3, 1.18.4, 1.18.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-052 is embedded in [`01a-implicit-members-and-identity.md`](01a-implicit-members-and-identity.md) with leaf 1.18.7, and D-117 in [`03-internals-enums.md`](03-internals-enums.md)
**Target version:** Java 21 LTS
**Lines:** 695
