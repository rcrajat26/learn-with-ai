# 03 Java Core — Enums in production — BASICS (§1.18, 1.18.14–1.18.17)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Enums in use — collections, switch, strategy](01b-collections-patterns-and-guarantees.md) · Next: [Enum internals — what `javac` generates](03-internals-enums.md)

Three files of §1.18 have built the model. This one closes it with the shape the enum should actually have in a system that stores things: the persisted-code pattern that neutralises the `ordinal()`, `valueOf` and `toString` traps in one place; the two guarantees — serialization by name, reflection refused — restated with their costs rather than only their comfort; and the hand-written typesafe-enum pattern Java 5 automated, annotated obligation by obligation, so you can see exactly what the keyword bought and when you still have to write it yourself.

[`01-basics.md`](01-basics.md) owns the enum as a class, constant bodies and the uniqueness guarantee, and carries the *measurements* for the serialization and reflection claims restated in concepts 2 and 3 below. [`01a-implicit-members-and-identity.md`](01a-implicit-members-and-identity.md) owns `values()`, `valueOf`, `ordinal()` and `hashCode()`. [`01b-collections-patterns-and-guarantees.md`](01b-collections-patterns-and-guarantees.md) owns `EnumMap`/`EnumSet`, `switch`, and the strategy-enum pattern. The class-file layer is [`03-internals-enums.md`](03-internals-enums.md) and its two continuations.

All bytecode, compiler diagnostics and runtime results below were measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with version comparisons against **Oracle JDK 17.0.15** and **Oracle JDK 11.0.27**. The enum under test is the ten-constant `RestrictionType` from [`01-basics.md`](01-basics.md).

## 1. The production pattern: a stable code plus a static lookup (1.18.14)

`[BUILD]` This is the shape every enum that touches a database, a wire format, a config file or a log-parsing rule should have. It is short enough to type from memory and it closes, in one place, the `ordinal()` trap, the `valueOf` trap, the `toString` trap and the duplicate-code mistake.

### Why it exists

Each of the three preceding traps has an individual fix, and applying them separately produces an enum with a code field here, a map there, and a parse method somebody added later that uses `valueOf` after all. Writing them as one pattern makes the enum self-contained: the code is declared next to the constant, the inverse is built from the same source of truth, and the duplicate check runs at class initialization so a copy-paste error fails the deployment rather than losing a mapping.

### The mechanism

Five components, each with a reason:

1. **A `final` code field**, declared in the constant list. It is the persisted identity, owned by the enum, immune to reordering. Keep it short and opaque enough that it will not be "improved" later — renaming a code is a data migration.
2. **A `static final Map<String, E>` built in a `static` block.** Safe there and not in the constructor, because `<clinit>` assigns every constant before running static initialisers.
3. **A duplicate check during the build.** `map.put(code, constant) != null` means two constants claim one code, which is a bug that silently loses one of them.
4. **`Map.copyOf` on the way out.** A `HashMap` behind a `static final` reference is still mutable.
5. **An `Optional`-returning `fromCode`**, so the caller decides between a default, a rejection and a log — and no exception is constructed on the failure path.

Plus, at the persistence boundary, an explicit converter so the mapping cannot be bypassed by a bare `@Enumerated`.

### Diagram

No diagram for this concept: it is a code pattern, and the code below is the artefact.

### A concrete example

The complete, compiling pattern:

```java
public enum RestrictionType {
    DEPOSIT_BLOCKED("DEP_BLK", "Deposits blocked"),
    STAKE_BLOCKED("STK_BLK", "Stakes blocked"),
    WITHDRAWAL_BLOCKED("WDR_BLK", "Withdrawals blocked"),
    DEPOSIT_LIMITED("DEP_LIM", "Deposit limit applied"),
    WITHDRAWAL_HELD("WDR_HLD", "Withdrawal held for review"),
    SOURCE_OF_FUNDS_REQUIRED("SOF_REQ", "Source of funds required"),
    ALL_BLOCKED("ALL_BLK", "All money actions blocked"),
    SELF_EXCLUDED("SELF_EXC", "Client self-excluded"),
    COOLING_OFF("COOL_OFF", "Cooling-off period active"),
    DORMANT_FROZEN("DORM_FRZ", "Account dormant");

    private static final Map<String, RestrictionType> BY_CODE;

    static {
        Map<String, RestrictionType> byCode = new HashMap<>();
        for (RestrictionType type : values()) {
            RestrictionType clash = byCode.put(type.code, type);
            if (clash != null) {
                throw new IllegalStateException(
                    "duplicate restriction code " + type.code
                        + " on " + clash.name() + " and " + type.name());
            }
        }
        BY_CODE = Map.copyOf(byCode);
    }

    private final String code;
    private final String description;

    RestrictionType(String code, String description) {
        this.code = code;
        this.description = description;
    }

    public String code() {
        return code;
    }

    public String description() {
        return description;
    }

    /** Tolerant: no exception, no stack trace, caller decides what unknown means. */
    public static Optional<RestrictionType> fromCode(String code) {
        return code == null ? Optional.empty() : Optional.ofNullable(BY_CODE.get(code));
    }

    /** Strict: for internal callers where an unknown code is a programming error. */
    public static RestrictionType requireCode(String code) {
        return fromCode(code).orElseThrow(() -> new IllegalArgumentException(
            "unknown restriction code: " + code));
    }
}
```

The JPA side, which is where the pattern is most often undermined:

```java
@Converter(autoApply = true)
public final class RestrictionTypeConverter
        implements AttributeConverter<RestrictionType, String> {

    @Override
    public String convertToDatabaseColumn(RestrictionType attribute) {
        return attribute == null ? null : attribute.code();
    }

    @Override
    public RestrictionType convertToEntityAttribute(String column) {
        if (column == null) {
            return null;
        }
        return RestrictionType.fromCode(column).orElseThrow(() -> new IllegalStateException(
            "restriction row holds an unknown code: " + column
                + " — a newer deployment wrote a constant this build does not have"));
    }
}
```

`autoApply = true` is the load-bearing part: it means nobody has to remember `@Convert` on each field, and — more importantly — nobody can accidentally get `EnumType.ORDINAL` by writing a bare `@Enumerated`. The `orElseThrow` message names both the offending code and the likely cause, because during a rolling upgrade an older instance reading a newer instance's row is exactly how this fires, and the operator reading the log needs to know that immediately.

And the wire side, for the API contract:

```java
public record RestrictionView(String type, String source, String description, Instant appliedAt) {

    public static RestrictionView of(Restriction restriction) {
        return new RestrictionView(
            restriction.type().code(),
            restriction.source().name(),
            restriction.type().description(),
            restriction.appliedAt());
    }
}
```

The view carries codes and names, never ordinals and never the enum type itself, so the JSON contract is stable against any edit to the constant list that does not touch the codes. Enum representation on the wire is in [`../../12-api-design/`](../00-index.md) territory; the rule this file owes you is the one above.

### The gotcha

**Pitfall:** building the lookup map in a `private static final Map` initialised with a *field initialiser* that calls a static method declared *after* it.

```java
// Compiles. Throws at class init.
private static final Map<String, RestrictionType> BY_CODE = buildIndex();
```

That is actually fine — a static method may be called from a static field initialiser regardless of textual position. What is *not* fine is a static field initialiser that reads another static field declared *later*:

```java
private static final Map<String, RestrictionType> BY_CODE = index(DEFAULT_CODE);
private static final String DEFAULT_CODE = "DEP_BLK";   // still null when BY_CODE runs
```

Static initialisers run in textual order, so `DEFAULT_CODE` is `null` at the moment `BY_CODE` is built — and because it is a `String` field with a *constant* initialiser the compiler may even inline it, making the behaviour differ between a field that is `static final String` and one that is `static final Object`. Symptom: an NPE inside `<clinit>` surfacing as `ExceptionInInitializerError`, or worse, a map built with a `null` entry and no error at all. Fix: build the whole index inside a single `static { }` block placed after every field it reads, or in a private holder class. Illegal forward reference and static-initialiser ordering are in [`../classes-and-initialization/01-basics.md`](../classes-and-initialization/01-basics.md).

> **Definition.** The production enum pattern is a `final` code field per constant, a `static final Map` from code to constant built in a `static` block with a duplicate check, `Map.copyOf` on assignment, an `Optional`-returning `fromCode`, and an explicit `AttributeConverter` at the persistence boundary so no bare `@Enumerated` can reintroduce the ordinal.

---

## 2. Enum serialization ignores your hooks — and what that costs you (1.18.15)

`[RESEARCH]` `[SOURCE]` A supporting fact rather than a full concept: the *guarantee* and its measurement are in [`01-basics.md`](01-basics.md) concept 3, which proves that `writeReplace`, `readResolve` and `readObject` are all bypassed. What is left to say here is the mechanism's cost, which is the part that shows up in a design review.

**Mechanism.** The Java Object Serialization Specification defines the enum wire form as the constant's `name()`, and states that the standard customisation hooks are ignored for enum types. `ObjectOutputStream` writes a `TC_ENUM` marker, the class descriptor, and the name string. `ObjectInputStream` reads the name and calls `Enum.valueOf(enumType, name)`, so the result is the existing constant and no instance is constructed. `java.lang.Enum` reinforces it from the other side with its own `private void readObject` and `readObjectNoData`, both throwing `InvalidObjectException("can't deserialize enum")`, so a crafted stream claiming a field-by-field enum instance is refused. Measured: an 81-byte stream for one `RestrictionType` constant, containing the literal text `SELF_EXCLUDED`; and a round trip returning `identical = true`.

**The gotcha.** Because the wire form is the name, **renaming or removing a constant is a breaking change for every serialized form in flight** — a message on a Kafka topic, a session in a replicated store, an RMI argument, a cached object in Hazelcast or Coherence. `readResolve` is the hook you would normally use to migrate an old name to a new constant, and it is exactly the hook that is unavailable. So there is no in-enum migration path: the only routes are to keep the old constant as a deprecated alias until every stream has drained, or to stop using Java serialization for the value and put a code on the wire instead (concept 1), where a mapping table *can* absorb a rename. Adding a constant is safe in the write direction and unsafe in the read direction: an older consumer receiving a newer constant's name gets `IllegalArgumentException: No enum constant`, thrown from inside `ObjectInputStream` and wrapped in whatever the framework wraps it in.

> **Definition.** Enum serialization is by `name()` only, with `writeReplace`, `readResolve` and `readObject` specified as ignored — which makes the form tamper-proof and version-migration-proof in equal measure, so a constant rename is a breaking wire change with no in-enum remedy.

---

## 3. Reflection cannot construct an enum constant — but `Unsafe` can (1.18.16)

`[PROVE]` Another supporting fact; the measurement is in [`01-basics.md`](01-basics.md) concept 3. What belongs here is the precise scope of the claim, because it is usually overstated.

**Mechanism.** `Constructor.newInstance` contains an explicit check that rejects any constructor whose declaring class has `ACC_ENUM` set. Measured:

```
c.setAccessible(true);                 // succeeds
c.newInstance("FORGED", 99);           // java.lang.IllegalArgumentException:
                                       //   Cannot reflectively create enum objects
```

`setAccessible(true)` succeeding is the informative part: the block is not an accessibility check, so it is not affected by module opens, `--add-opens`, or a security manager's absence. It is a hard-coded refusal in the reflection implementation.

**The honest caveat.** `sun.misc.Unsafe.allocateInstance` does not go through a constructor at all — it allocates a zeroed instance of the class and returns it. Measured on JDK 21.0.7 (with `sun.misc` opened; the package now lives in the `jdk.unsupported` module, and the JVM prints `WARNING: package sun.misc not in java.base`):

```
Unsafe.allocateInstance SUCCEEDED: RestrictionType name=null ordinal=0
  == SELF_EXCLUDED?  false
  in values()?       false
```

So an eleventh `RestrictionType` object *can* be brought into existence, with `name() == null` and `ordinal() == 0`, equal to nothing and absent from `values()`. This is not a hole worth worrying about operationally — `Unsafe` can also corrupt any object's fields, so an attacker holding it has already won — but it is the difference between "the JVM enforces this" and "the supported API enforces this", and stating the claim as the latter is the accurate version. Note what the forged object does *not* get: `name` and `ordinal` are `final` fields set only by the constructor, so a zeroed instance carries a null name, which makes it immediately detectable and useless as a substitute for a real constant in any code that logs or switches on it.

**The gotcha.** Frameworks that instantiate objects reflectively — some deserializers, some mocking libraries, some object-graph builders — occasionally special-case enums badly, and the symptom is an enum-typed field holding an object that is not any of the constants. `switch` on it falls to `default` (or throws `MatchException`), `EnumMap.put` throws or writes to slot 0, and `name()` returns null, so the log line naming the offender is blank. Fix when you meet it: compare with `==` against a known constant or check `Arrays.asList(values()).contains(x)` at the boundary where the object enters your code, and configure the framework to use `valueOf` rather than instance allocation.

> **Definition.** `Constructor.newInstance` refuses any constructor of an `ACC_ENUM` class with `IllegalArgumentException: Cannot reflectively create enum objects`, and `setAccessible` does not defeat it; only `Unsafe.allocateInstance`, which bypasses constructors entirely, can produce a forged instance — and it arrives with a null `name` and ordinal 0, in no `values()` array.

---

## 4. The typesafe-enum pattern that Java 5 automated (1.18.17)

`[BUILD]` Closing the arc opened in [`01-basics.md`](01-basics.md) concept 1. Writing the pattern out by hand is the fastest way to see exactly which parts of an enum are language features and which are conventions you would otherwise maintain yourself — and it is a standard interview exercise.

### Why it exists

Between 1996 and 2004, `public static final int` was the only built-in option and it was actively harmful: no type safety, no namespace, no printable form, no exhaustiveness. Joshua Bloch's typesafe-enum pattern (*Effective Java* 1st edition, Item 21; retained in later editions as the historical motivation for Item 34, *Use enums instead of int constants*) replaced it with a class. The language feature that arrived in Java 5 is that pattern, with the tedious and error-prone parts generated.

### The mechanism

The hand-written version, complete and compiling, with every generated part labelled:

```java
public final class RestrictionTypeClassic
        implements Comparable<RestrictionTypeClassic>, Serializable {

    // (1) javac generates these as public static final fields with ACC_ENUM.
    public static final RestrictionTypeClassic DEPOSIT_BLOCKED =
        new RestrictionTypeClassic("DEPOSIT_BLOCKED", 0, "DEP_BLK");
    public static final RestrictionTypeClassic STAKE_BLOCKED =
        new RestrictionTypeClassic("STAKE_BLOCKED", 1, "STK_BLK");
    public static final RestrictionTypeClassic SELF_EXCLUDED =
        new RestrictionTypeClassic("SELF_EXCLUDED", 2, "SELF_EXC");

    // (2) javac generates $VALUES, private static final and ACC_SYNTHETIC,
    //     built by a synthetic $values() method.
    private static final RestrictionTypeClassic[] VALUES =
        { DEPOSIT_BLOCKED, STAKE_BLOCKED, SELF_EXCLUDED };

    // (3) Class.enumConstantDirectory() is the generated equivalent, built lazily
    //     and cached on the Class object rather than declared here.
    private static final Map<String, RestrictionTypeClassic> BY_NAME;

    static {
        Map<String, RestrictionTypeClassic> byName = new HashMap<>();
        for (RestrictionTypeClassic value : VALUES) {
            byName.put(value.name, value);
        }
        BY_NAME = Map.copyOf(byName);
    }

    // (4) Enum declares these two as private final and sets them in its constructor.
    private final String name;
    private final int ordinal;
    private final String code;

    // (5) javac makes the constructor ACC_PRIVATE and prepends (String name, int ordinal).
    private RestrictionTypeClassic(String name, int ordinal, String code) {
        this.name = name;
        this.ordinal = ordinal;
        this.code = code;
    }

    // (6) Enum.name(), final.
    public String name() {
        return name;
    }

    // (7) Enum.ordinal(), final.
    public int ordinal() {
        return ordinal;
    }

    public String code() {
        return code;
    }

    // (8) The generated public static E[] values(), which clones $VALUES.
    public static RestrictionTypeClassic[] values() {
        return VALUES.clone();
    }

    // (9) The generated public static E valueOf(String), which delegates to Enum.valueOf.
    public static RestrictionTypeClassic valueOf(String name) {
        RestrictionTypeClassic result = BY_NAME.get(name);
        if (result != null) {
            return result;
        }
        if (name == null) {
            throw new NullPointerException("Name is null");
        }
        throw new IllegalArgumentException(
            "No enum constant " + RestrictionTypeClassic.class.getCanonicalName() + "." + name);
    }

    // (10) Enum.toString(), the one member that is NOT final.
    @Override
    public String toString() {
        return name;
    }

    // (11) Enum.equals, final, identity-based.
    @Override
    public boolean equals(Object other) {
        return this == other;
    }

    // (12) Enum.hashCode, final, identity-derived.
    @Override
    public int hashCode() {
        return System.identityHashCode(this);
    }

    // (13) Enum.compareTo, final, ordinal-based.
    @Override
    public int compareTo(RestrictionTypeClassic other) {
        return this.ordinal - other.ordinal;
    }

    // (14) Enum.getDeclaringClass, final.
    public Class<RestrictionTypeClassic> getDeclaringClass() {
        return RestrictionTypeClassic.class;
    }

    // (15) The serialization specification does this for enums, unconditionally.
    //      Here it is a method you must remember to write, and it is the single
    //      most commonly omitted line in the whole pattern.
    @java.io.Serial
    private Object readResolve() {
        return valueOf(name);
    }

    // (16) Enum.clone, protected final, throws.
    @Override
    protected Object clone() throws CloneNotSupportedException {
        throw new CloneNotSupportedException();
    }
}
```

Sixteen numbered obligations, and the language generates every one. What it buys beyond mere brevity:

| What the keyword adds | Why the hand-written version cannot have it |
|---|---|
| `switch` support with exhaustiveness checking | needs the constant set in the class file, which only `ACC_ENUM` provides |
| `EnumSet` / `EnumMap` | `getEnumConstantsShared` requires `isEnum()`, which requires the flag |
| Reflective construction refused | the `ACC_ENUM` check in `Constructor.newInstance` |
| Serialization by name, hooks ignored | a specification rule keyed on the class being an enum |
| `Class.isEnum`, `getEnumConstants`, `enumConstantDirectory` | all gated on the flag |
| `@Deprecated`-proof `finalize` | `Enum.finalize` is `final` and empty |
| A `readResolve` you cannot forget | in the hand-written form, forgetting item (15) silently breaks singleton-ness across a round trip |

The last row is the historical point. Item (15) is the line everyone omitted, and its absence is invisible until a deserialized "constant" fails an `==` check — which, in a codebase full of `switch` and `==` comparisons, means a value that is simultaneously `SELF_EXCLUDED` by every readable criterion and not `SELF_EXCLUDED` to the program. That single failure mode is most of the reason the keyword exists.

Two limitations of the hand-written version that survive even a correct implementation. `hashCode` returning `System.identityHashCode(this)` reproduces the enum behaviour, including its per-run instability — there is no way to do better while keeping `equals` as identity. And `compareTo` here has no `ClassCastException` guard and no `getDeclaringClass` fallback, which is fine only because the class is `final` and has no constant-body equivalent; the real `Enum.compareTo` needs both.

### Diagram

No diagram for this concept: the artefact is the annotated code above, and a picture of it would be a picture of a code listing.

### The gotcha

**Pitfall:** believing the pattern is purely historical and therefore not worth knowing. It reappears whenever you need something enum-shaped that an enum cannot be: a closed set that must extend a class other than `Enum`; a constant family that must be extensible by a downstream module (an enum's set is closed at compile time, so a plugin cannot add to it); or a value type where the instances are computed rather than declared — a `Currency`, a `ZoneId`, a `Money` with an interned cache. `java.util.Currency` and `java.time.ZoneId` are both exactly this pattern in the JDK, for exactly that reason. Symptom of not knowing it: an enum contorted to fit an open set, usually with an `OTHER` constant carrying a string payload — which is the shape that reintroduces every problem an enum was meant to solve. Fix: recognise the open-set case early and write the class, with item (15) present.

> **Definition.** The typesafe-enum pattern is a `final` class with a `private` constructor, a `public static final` instance per constant, a cloned `values()`, a name-keyed `valueOf`, identity `equals`/`hashCode`, ordinal `compareTo`, and a `readResolve` that resolves by name — the last being the item the language automated because it was the one everyone forgot.

---

## Pitfalls

### Persisting an enum with a bare `@Enumerated`

**Wrong**

```java
@Entity
@Table(name = "client_restriction")
public class RestrictionEntity {

    @Id
    private UUID id;

    @Enumerated
    @Column(name = "restriction_type", nullable = false)
    private RestrictionType type;

    @Enumerated
    @Column(name = "restriction_source", nullable = false)
    private RestrictionSource source;
}
```

A bare `@Enumerated` means `EnumType.ORDINAL` — that is the annotation's declared default, not an accident of the provider. So both columns are `int` holding declaration indices. Measured effect of inserting `WAGERING_HELD` into `RestrictionType`: the constant at index 7 changed from `SELF_EXCLUDED` to `SOURCE_OF_FUNDS_REQUIRED`. Every stored `7` now reads back as a different, entirely valid restriction — silently, with no exception on either the read or the write path.

**Right**

```java
@Entity
@Table(name = "client_restriction")
public class RestrictionEntity {

    @Id
    private UUID id;

    // Converter is @Converter(autoApply = true), so no per-field annotation
    // can be forgotten and no bare @Enumerated can creep back in.
    @Column(name = "restriction_type", length = 16, nullable = false)
    private RestrictionType type;

    @Column(name = "restriction_source", length = 24, nullable = false)
    private RestrictionSource source;
}
```

with the converter from concept 1, whose read path throws with the offending code in the message. `@Enumerated(EnumType.STRING)` is the acceptable middle ground: it persists `name()`, which is safe against reordering but not against renaming, and it ties the column width to the longest identifier — `SOURCE_OF_FUNDS_REQUIRED` is 24 characters, so a `length = 16` column silently truncates or fails on insert depending on the database's strictness.

**Why people believe it:** `@Enumerated` reads as "this is an enum, handle it", and nothing in the name suggests it has picked the ordinal. An `int` column is also genuinely smaller and faster to index, so the choice looks like a considered optimisation rather than a default nobody chose.

### Building the lookup map from a static field initialiser that reads a later field

**Wrong**

```java
public enum RestrictionType {
    DEPOSIT_BLOCKED("DEP_BLK"), STAKE_BLOCKED("STK_BLK"), SELF_EXCLUDED("SELF_EXC");

    private static final Map<String, RestrictionType> BY_CODE = index(FALLBACK_CODE);
    private static final String FALLBACK_CODE = "DEP_BLK";

    private final String code;

    RestrictionType(String code) {
        this.code = code;
    }

    private static Map<String, RestrictionType> index(String fallback) {
        Map<String, RestrictionType> byCode = new HashMap<>();
        for (RestrictionType type : values()) {
            byCode.put(type.code, type);
        }
        byCode.put("", byCode.get(fallback));   // fallback is null here
        return Map.copyOf(byCode);
    }
}
```

Static initialisers run in textual order, so `FALLBACK_CODE` is still `null` when `BY_CODE` is built. `byCode.get(null)` returns `null`, and `Map.copyOf` then throws `NullPointerException` inside `<clinit>` — which surfaces as `ExceptionInInitializerError`, after which every subsequent touch of the class throws `NoClassDefFoundError` with the original cause gone. Worse, the behaviour is sensitive to the field's *type*: a `static final String` with a constant initialiser is a compile-time constant that `javac` may inline at the use site, so moving the declaration or changing the type changes whether the bug fires.

**Right**

```java
public enum RestrictionType {
    DEPOSIT_BLOCKED("DEP_BLK"), STAKE_BLOCKED("STK_BLK"), SELF_EXCLUDED("SELF_EXC");

    private static final String FALLBACK_CODE = "DEP_BLK";
    private static final Map<String, RestrictionType> BY_CODE;

    static {
        Map<String, RestrictionType> byCode = new HashMap<>();
        for (RestrictionType type : values()) {
            RestrictionType clash = byCode.put(type.code, type);
            if (clash != null) {
                throw new IllegalStateException("duplicate restriction code " + type.code
                    + " on " + clash.name() + " and " + type.name());
            }
        }
        RestrictionType fallback = byCode.get(FALLBACK_CODE);
        if (fallback == null) {
            throw new IllegalStateException("FALLBACK_CODE names no constant: " + FALLBACK_CODE);
        }
        byCode.put("", fallback);
        BY_CODE = Map.copyOf(byCode);
    }

    private final String code;

    RestrictionType(String code) {
        this.code = code;
    }
}
```

One `static { }` block, placed after every field it reads, doing all the work with explicit checks. `FALLBACK_CODE` is declared first so the textual ordering is correct by construction rather than by luck, and the `fallback == null` check turns a typo in the fallback code into a named startup failure.

**Why people believe it:** field-initialiser style reads more cleanly than a static block, and the compiler rejects the *obvious* forward reference (`private static final String A = B;` with `B` declared later is an "illegal forward reference" error). It does not reject the indirect one through a method call, so the pattern that looks equivalent is the one that compiles and breaks.

### Contorting an enum to model an open set

**Wrong**

```java
public enum PaymentRail {
    CARD_DEPOSIT, BANK_DEPOSIT, CARD_WITHDRAWAL, BANK_WITHDRAWAL,
    OTHER;                       // carries a name in a side channel

    private static final Map<PaymentRail, String> OTHER_NAMES = new ConcurrentHashMap<>();

    public static PaymentRail other(String name) {
        OTHER_NAMES.put(OTHER, name);
        return OTHER;
    }
}
```

`OTHER` is a single constant, so the "name" is global mutable state on a `static final` field: the last caller wins, concurrently, for every reader in the process. Every property the enum was chosen for is gone — a `switch` over `PaymentRail` cannot distinguish two different `OTHER` rails, `EnumMap` collapses them into one slot, and `equals` says they are the same rail.

**Right**

```java
public sealed interface PaymentRail {

    String code();

    enum Known implements PaymentRail {
        CARD_DEPOSIT("CARD_DEP"),
        BANK_DEPOSIT("BANK_DEP"),
        CARD_WITHDRAWAL("CARD_WDR"),
        BANK_WITHDRAWAL("BANK_WDR");

        private final String code;

        Known(String code) {
            this.code = code;
        }

        @Override public String code() {
            return code;
        }
    }

    record Unknown(String code) implements PaymentRail {
        public Unknown {
            Objects.requireNonNull(code, "code");
        }
    }

    static PaymentRail fromCode(String code) {
        for (Known known : Known.values()) {
            if (known.code().equals(code)) {
                return known;
            }
        }
        return new Unknown(code);
    }
}
```

The closed part stays an enum, with all its guarantees. The open part is a record, so each unknown rail is its own value with its own code. A pattern switch over `PaymentRail` is exhaustive across `Known` and `Unknown`, so the compiler still forces you to handle both — and adding a `Known` constant is still a compile error at any switch that enumerates them. Sealed hierarchies and records are in [`../records-and-sealed/01-basics.md`](../records-and-sealed/01-basics.md).

**Why people believe it:** the set usually *is* closed when the enum is written, and `OTHER` looks like a cheap escape hatch for the one case that turned up later. The cost only becomes visible once two different unknown values need to coexist.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Production pattern, part 1 | a `final` code field per constant — persisted identity the enum owns, immune to reordering |
| Production pattern, part 2 | a `static final Map<String, E>` built in a `static` block, **never** the constructor |
| Why not the constructor | `$VALUES` is still null while constants are being created; `values()` NPEs inside `<clinit>` |
| Why a `static` block is safe | `<clinit>` assigns every constant field and `$VALUES` before running static initialisers |
| Production pattern, part 3 | `map.put(code, constant) != null` duplicate check → a named startup failure, not a lost mapping |
| Production pattern, part 4 | `Map.copyOf` on assignment — a `HashMap` behind a `static final` reference is still mutable |
| Production pattern, part 5 | `Optional<E> fromCode(String)`, plus a strict `requireCode` for internal callers |
| Why `Optional`, not `try`/`catch` | `valueOf` costs a `fillInStackTrace` per bad input, and throws NPE (not IAE) on null |
| JPA | `@Converter(autoApply = true)` on `AttributeConverter<E, String>`. Read path `orElseThrow` with the code in the message |
| Bare `@Enumerated` | means `EnumType.ORDINAL` — the annotation's own default. The ordinal bug with an annotation on it |
| `@Enumerated(EnumType.STRING)` | safe against reordering, not against renaming; column must fit the longest identifier |
| Wire representation | codes and `name()` in the DTO; never the ordinal, never the enum type itself |
| Static-initialiser ordering | textual. A field initialiser calling a method that reads a later field sees `null` — and it compiles |
| Serialization form | `TC_ENUM` + class descriptor + `name()`. 81 bytes measured for one constant |
| Serialization hooks | `writeReplace`, `readResolve`, `readObject` all **ignored** by specification — measured, none fired |
| `Enum.readObject` | `private`, `@java.io.Serial`, throws `InvalidObjectException("can't deserialize enum")` |
| Cost of by-name serialization | renaming or removing a constant breaks streams in flight, with **no** `readResolve` to migrate it |
| Old consumer, new constant | `IllegalArgumentException: No enum constant` from inside `ObjectInputStream` |
| Reflective construction | `IllegalArgumentException: Cannot reflectively create enum objects` |
| `setAccessible(true)` | **succeeds**; the refusal is hard-coded, not an accessibility check, so `--add-opens` is irrelevant |
| `Unsafe.allocateInstance` | **does** forge an instance: `name() == null`, `ordinal() == 0`, `==` nothing, absent from `values()` |
| Accurate claim | the *supported APIs* cannot make a second instance. The JVM, via `Unsafe`, can |
| Typesafe-enum pattern | 16 hand-written obligations; the one everyone omitted is `readResolve`, and that is why the keyword exists |
| What the keyword adds beyond brevity | `switch` exhaustiveness, `EnumSet`/`EnumMap`, reflective refusal, by-name serialization, `Class.isEnum` — all gated on `ACC_ENUM` |
| When to hand-write it | must extend a class other than `Enum`; must be extensible downstream; instances computed rather than declared |
| JDK examples of the hand-written form | `java.util.Currency`, `java.time.ZoneId` — open sets, so an enum was never available |
| Open-set anti-pattern | an `OTHER` constant with a side-channel name. Use a sealed interface with an enum arm and a record arm |

---

## Self-test

**Q1.** Write the production pattern for an enum that is persisted, and name what each part defends against.

<details><summary>Answer</summary>

A `final` code field declared next to each constant, defending against `ordinal()` — the code is owned by the enum and immune to reordering, whereas the ordinal changes whenever anyone inserts a constant. A `static final Map<String, E>` built in a `static` block, not the constructor, defending against the `<clinit>` ordering trap: constant assignments and `$VALUES` precede static initialisers, so `values()` is complete in a `static` block and would NPE in a constructor. A `map.put(code, constant) != null` duplicate check during the build, defending against a copy-pasted code that would otherwise silently lose one mapping — it turns that into a class-initialization failure at startup naming both constants. `Map.copyOf` on assignment, defending against a caller mutating a `HashMap` behind a `static final` reference. An `Optional`-returning `fromCode`, defending against both the `IllegalArgumentException` that `valueOf` throws (which costs a `fillInStackTrace` per bad input, making any endpoint accepting the value a cheap amplification target) and the NPE that `valueOf(null)` throws, which a `catch (IllegalArgumentException)` does not handle. And a `@Converter(autoApply = true) AttributeConverter<E, String>` at the JPA boundary, defending against a bare `@Enumerated`, whose default is `EnumType.ORDINAL` — the original bug wearing an annotation. The converter's read path should `orElseThrow` with the offending code in the message, because an older instance reading a newer instance's row during a rolling upgrade is exactly how it fires.

</details>

**Q2.** "Nothing can create a second instance of an enum constant." Is that true?

<details><summary>Answer</summary>

Through the supported APIs, yes; through `Unsafe`, no. The supported doors are all shut, measured on JDK 21.0.7: the constructor is `ACC_PRIVATE` and called only from `<clinit>`; `Constructor.newInstance` refuses any constructor of an `ACC_ENUM` class with `IllegalArgumentException: Cannot reflectively create enum objects`, and `setAccessible(true)` *succeeds* yet does not help, because the block is a hard-coded refusal rather than an accessibility check, so `--add-opens` is irrelevant; `Enum.clone` is `protected final` and throws `CloneNotSupportedException`; and serialization is by `name()` with `writeReplace`/`readResolve`/`readObject` ignored, plus `Enum`'s own `readObject` throwing `InvalidObjectException`. But `sun.misc.Unsafe.allocateInstance` does not go through a constructor at all — it allocates a zeroed instance. Measured, it succeeded: a `RestrictionType` object with `name() == null`, `ordinal() == 0`, not `==` any constant and not present in `values()`. Operationally this is not a concern, because anything holding `Unsafe` can corrupt arbitrary object fields and has already won. But it is the difference between "the JVM enforces this" and "the supported API enforces this", and the accurate claim is the latter. The practical trace of it: frameworks that instantiate reflectively and special-case enums badly can hand you such an object, and the symptom is a null `name()` in the log line that should have identified the offender.

</details>


**Q3.** Why must the lookup map be built in a `static` block rather than a static field initialiser or the constructor?

<details><summary>Answer</summary>

The constructor is ruled out by `<clinit>`'s two phases. `javac` emits, in order: one `new`/`dup`/`ldc name`/`iconst ordinal`/`invokespecial <init>`/`putstatic` sequence per constant in declaration order, then `invokestatic $values()` and `putstatic $VALUES`, then the static initialisers in textual order. A constructor runs during the first phase, when `$VALUES` is still `null`, so `values()` does a `getstatic` of null and then `invokevirtual clone()` on it — NPE inside `<clinit>`, surfacing as `ExceptionInInitializerError`, after which every later touch of the class throws `NoClassDefFoundError` with the cause gone. A static field *initialiser* is safe with respect to `values()`, because it runs in the third phase, but it is unsafe with respect to *other static fields*: initialisers run in textual order, so `private static final Map X = index(FALLBACK);` with `FALLBACK` declared below it sees `null`. The compiler rejects the direct form (`static final String A = B;`, `B` later) as an illegal forward reference but does **not** reject the indirect form through a method call, so the version that looks equivalent compiles and breaks. Worse, the behaviour depends on the field's type: a `static final String` with a constant initialiser is a compile-time constant `javac` may inline at the use site, so the bug appears or disappears when someone changes the type or moves the declaration. A single `static { }` block placed after every field it reads has neither problem, and gives you somewhere to put the duplicate-code check and the "fallback names no constant" check.

</details>

**Q4.** An enum constant is renamed. What breaks, and why can you not fix it inside the enum?

<details><summary>Answer</summary>

Every serialized form in flight breaks, and the hook you would normally use to migrate is the one that is specified as ignored. The Java serialization form of an enum constant is its `name()` — measured, an 81-byte stream containing the literal text `SELF_EXCLUDED` — and `ObjectInputStream` resolves it by calling `Enum.valueOf(enumType, name)`. After a rename, that call throws `IllegalArgumentException: No enum constant`, from inside `ObjectInputStream`, wrapped in whatever the framework wraps it in. Normally you would add `readResolve` to map the old name onto the new constant, but the specification says `writeReplace`, `readResolve` and `readObject` are ignored for enums — measured, with all three declared and printing to stdout, none fired during a full round trip — and `java.lang.Enum` additionally declares its own `private void readObject` throwing `InvalidObjectException("can't deserialize enum")`. So there is no in-enum migration path at all. The two real options: keep the old constant as a deprecated alias until every stream has drained (a Kafka topic's retention, a session store's TTL, an RMI client's deployment window); or stop putting the *enum* on the wire and put a code on it instead, since a code-to-constant map — unlike `Enum.valueOf` — is yours to edit, so an old code can be pointed at a renamed constant in one line. The same argument is why `@Enumerated(EnumType.STRING)` is safe against reordering but not against renaming.

</details>

**Q5.** You need a closed-ish set: four known payment rails plus whatever a new PSP integration sends. Why is an `OTHER` constant wrong, and what replaces it?

<details><summary>Answer</summary>

Because there is only one `OTHER` object. An enum constant is a `static final` field, so any per-instance payload — the actual rail name — has to live in a side channel such as a `static Map<PaymentRail, String>`, which makes it global mutable state where the last writer wins for every concurrent reader in the process. Every property you chose the enum for then fails: a `switch` cannot distinguish two different unknown rails, an `EnumMap` collapses them into one slot, `equals` reports them as the same rail, and there is no thread-safe reading of the name at all. The replacement is a sealed interface with two arms: an inner `enum Known implements PaymentRail` carrying the four constants with their codes, and a `record Unknown(String code) implements PaymentRail` for anything else. Each unknown rail is then its own value with its own code, comparable and hashable correctly for free. A pattern switch over `PaymentRail` is exhaustive across `Known` and `Unknown`, so the compiler still forces both to be handled; and enumerating the `Known` constants explicitly inside that switch keeps the property that adding a fifth known rail is a compile error. The closed part keeps every enum guarantee — singleton constants, `EnumSet`, by-name serialization — and only the genuinely open part pays for being open.

</details>

---

## Open questions

- **Unverified:** the *Effective Java* item numbers cited in concept 4. Item 34 (*Use enums instead of int constants*) and the 1st-edition Item 21 for the typesafe-enum pattern are cited with both number and title, so a wrong number is self-correcting against the title; the mapping was corroborated against published tables of contents rather than against the physical book, per the note in the index's *Resolved research items*. The 1st-edition reference is the least certain of the two, since the 1st edition's numbering differs substantially from the 2nd and 3rd. What would settle it: the book. Nothing in the notes depends on the number — the pattern is written out in full above.
- **Unverified:** whether `@Enumerated`'s default of `EnumType.ORDINAL` is stated in the Jakarta Persistence specification or is only the annotation's declared default value. The annotation's `value()` element has `EnumType.ORDINAL` as its Java default, which is why a bare `@Enumerated` behaves that way regardless of provider — that much follows from the annotation declaration. Whether the specification also mandates the mapping for a field with *no* `@Enumerated` at all was not checked, and providers have historically differed on untagged enum fields. What would settle it: the Jakarta Persistence 3.1 specification's section on basic mappings, and the `jakarta.persistence.Enumerated` javadoc. The recommendation here — an explicit `@Converter(autoApply = true)` — is correct either way, because it removes the question.
- **Unverified:** whether `Unsafe.allocateInstance` on an enum class is documented as permitted or merely happens to work. Measured on JDK 21.0.7 that it succeeds and yields a `RestrictionType` instance with `name() == null`, `ordinal() == 0`, identical to no constant and absent from `values()`; the JVM printed `WARNING: package sun.misc not in java.base`, confirming the class now lives in `jdk.unsupported`. Whether a future release closes this specifically for `ACC_ENUM` classes, as `Constructor.newInstance` does, was not established. What would settle it: the `sun.misc.Unsafe.allocateInstance` javadoc in the `jdk.unsupported` module, and JEP 471's disposition of `Unsafe`'s memory-access methods (which does not obviously cover `allocateInstance`). The claim as stated — supported APIs cannot, `Unsafe` can, on this build — is measured.

---

**Leaves covered:** 1.18.14, 1.18.15, 1.18.16, 1.18.17 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none — §1.18's diagram, D-052, is embedded in [`01a-implicit-members-and-identity.md`](01a-implicit-members-and-identity.md)
**Target version:** Java 21 LTS
**Lines:** 638
