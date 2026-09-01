# 03 Java Core — Enum-shaped builds — the pre-Java-5 typesafe enum pattern — BUILD IT (§4.5.1)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Wildcard copy, generic varargs, and the §4.4 diff table](02d-wildcard-copy-varargs-and-diff.md) · Next: [The persisted-code enum](03k-persisted-code-enum.md)

---

## Where this file sits in §4.5

§4.5 builds five enum-shaped things. This file builds the first one, and it is the only one that
is not an `enum` at all: the hand-rolled pattern that `enum` replaced, built far enough to prove
exactly what the language keyword buys you.

| Build | What it is | The one problem it solves | Where |
|---|---|---|---|
| **Typesafe enum pattern (4.5.1)** | `final class`, private constructor, `public static final` instances, private static `VALUES`, `readResolve` | A closed set of constants before `enum` existed in the language | **this file** |
| Persisted-code enum (4.5.2) | `enum` + an immutable `code` field + a static `Map<String, X>` + `fromCode` returning `Optional` | The database and the wire outlive both `ordinal()` and `name()` | [The persisted-code enum](03k-persisted-code-enum.md) |
| Strategy enum (4.5.3) | `enum implements` an interface, per-constant bodies; and the injected-function alternative | Per-constant behaviour without a `switch` someone will forget to extend | [The strategy enum](03f-strategy-enum.md) |
| Enum state machine (4.5.4) | An `EnumMap`-driven transition table over the `AA-` codes | Legal-transition enforcement in one auditable place | [The enum state machine](03a-enum-state-machine-and-singleton.md) |
| Enum singleton (4.5.5) | The `enum`-as-singleton and the attacks it defeats | Guaranteed one instance, against reflection and deserialization both | [The enum singleton and the attacks it defeats](03g-enum-singleton.md) |

Everything here is `[BUILD]`: complete, compiling Java 21, compiled and run on
**Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, with real output
pasted.

---

## 4.5.1 The pre-Java-5 typesafe enum pattern `[PROVE]`

### The shape

A `final class` whose constructor is private, so nobody outside the class can make an instance;
five `public static final` fields that are the only instances; a private static `List` holding
them in declaration order so the class can enumerate itself; and one method, `readResolve`, whose
whole job is to undo what deserialization did.

That last piece is the interesting one, and it is where every hand-rolled version of this pattern
that ships to production goes wrong.

### Why it existed, and why it still matters

Before Java 5 the alternative was `public static final int SYSTEM_ONBOARDING = 0`. Integer
constants have no type, so `applyRestriction(STAKE_BLOCKED, DEPOSIT_BLOCKED)` compiles when both
arguments are `int`; they have no namespace, so two subsystems collide on the value `0`; they
print as `3` in a log; and they are compile-time constants, so a client that recompiled against
last quarter's jar has the *old number* inlined into its own bytecode, because a
`static final int` initialised from a literal is a constant variable and `javac` folds its value
into every use site rather than emitting a field read.
The typesafe enum pattern fixes all four at once with nothing but a private constructor.

The live payoff is not nostalgia. This is the exact shape you fall back to when you need a closed
set that an `enum` cannot express: constants that must extend a shared abstract base class, or a
set whose members are discovered at class-initialisation time from configuration, or a value that
must carry a type parameter (`RestrictionKey<T>`). And it is the shape every "why is my singleton
not a singleton" bug reduces to.

### The build

`RestrictionSource` is the domain's restriction-source set: `SYSTEM_ONBOARDING`,
`SYSTEM_COMPLIANCE`, `SYSTEM_LIFECYCLE`, `ADMIN`, `CLIENT`. Restriction identity is the pair
(type, source), so this class is compared by identity all over `ClientRestrictions`.

```java
import java.io.InvalidObjectException;
import java.io.ObjectStreamException;
import java.io.Serializable;
import java.util.List;

/** Pre-Java-5 typesafe enum, complete: private constructor, public static final
 *  instances, a private static VALUES list, and readResolve for serialization. */
public final class RestrictionSource implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String name;
    private final boolean systemOwned;
    private final int index;

    private RestrictionSource(String name, boolean systemOwned, int index) {
        this.name = name;
        this.systemOwned = systemOwned;
        this.index = index;
    }

    public static final RestrictionSource SYSTEM_ONBOARDING = new RestrictionSource("SYSTEM_ONBOARDING", true, 0);
    public static final RestrictionSource SYSTEM_COMPLIANCE = new RestrictionSource("SYSTEM_COMPLIANCE", true, 1);
    public static final RestrictionSource SYSTEM_LIFECYCLE  = new RestrictionSource("SYSTEM_LIFECYCLE", true, 2);
    public static final RestrictionSource ADMIN             = new RestrictionSource("ADMIN", false, 3);
    public static final RestrictionSource CLIENT            = new RestrictionSource("CLIENT", false, 4);

    private static final List<RestrictionSource> VALUES =
            List.of(SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT);

    public static List<RestrictionSource> values() { return VALUES; }

    public static RestrictionSource valueOf(String name) {
        for (RestrictionSource candidate : VALUES) {
            if (candidate.name.equals(name)) return candidate;
        }
        throw new IllegalArgumentException("No RestrictionSource named " + name);
    }

    public boolean systemOwned() { return systemOwned; }

    public String name() { return name; }

    /** Substitute the canonical instance for the freshly allocated deserialized one. */
    private Object readResolve() throws ObjectStreamException {
        if (index < 0 || index >= VALUES.size()) {
            throw new InvalidObjectException("Unknown RestrictionSource index " + index);
        }
        return VALUES.get(index);
    }

    @Override public String toString() { return name; }
}
```

Three details that are not decoration:

- **The constants are declared before `VALUES`.** Static initialisers run in textual order, so
  `VALUES` sees five constructed instances. Reverse the two blocks and `javac` refuses the direct
  reference outright with `error: illegal forward reference`; hide the same reference behind a
  static factory method and it compiles, then fails at first touch with `ExceptionInInitializerError`
  caused by a `NullPointerException` from `List.of`, which rejects nulls. Both outcomes are in the
  pitfalls below.
- **`VALUES` is `private`, exposed through `values()` returning the immutable `List.of` view.**
  A `public static final` array would be mutable by every caller —
  `RestrictionSource.VALUES[3] = null` compiles. That is exactly why the real `Enum.values()`
  clones — leaf 4.5.6, in [The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md).
- **`index` exists only so `readResolve` can find the canonical instance.** Comparing on `name`
  would work too; the `int` makes the substitution a single array index.

`RestrictionSourceV1` below is the identical class with the `readResolve` method deleted and
nothing else changed. That deletion is the whole experiment.

### Proving `readResolve` is load-bearing, not decoration

The harness writes a constant to an `ObjectOutputStream`, reads it back, and asks the only
question that matters for an identity-compared type: is the thing that came back the same object
that went in.

```java
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;

public final class TypesafeEnumRoundTrip {

    private static byte[] write(Serializable value) throws Exception {
        ByteArrayOutputStream sink = new ByteArrayOutputStream();
        try (ObjectOutputStream out = new ObjectOutputStream(sink)) {
            out.writeObject(value);
        }
        return sink.toByteArray();
    }

    private static Object read(byte[] bytes) throws Exception {
        try (ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(bytes))) {
            return in.readObject();
        }
    }

    public static void main(String[] args) throws Exception {
        byte[] v1Bytes = write(RestrictionSourceV1.ADMIN);
        RestrictionSourceV1 v1 = (RestrictionSourceV1) read(v1Bytes);
        System.out.println("V1 (no readResolve)");
        System.out.println("  stream length            = " + v1Bytes.length + " bytes");
        System.out.println("  deserialized             = " + v1);
        System.out.println("  == RestrictionSourceV1.ADMIN ? " + (v1 == RestrictionSourceV1.ADMIN));
        System.out.println("  identity: canonical=" + Integer.toHexString(System.identityHashCode(RestrictionSourceV1.ADMIN))
                + " decoded=" + Integer.toHexString(System.identityHashCode(v1)));
        System.out.println("  in values() ?            " + RestrictionSourceV1.values().contains(v1));

        byte[] v2Bytes = write(RestrictionSource.ADMIN);
        RestrictionSource v2 = (RestrictionSource) read(v2Bytes);
        System.out.println("V2 (readResolve)");
        System.out.println("  stream length            = " + v2Bytes.length + " bytes");
        System.out.println("  deserialized             = " + v2);
        System.out.println("  == RestrictionSource.ADMIN ?   " + (v2 == RestrictionSource.ADMIN));
        System.out.println("  in values() ?            " + RestrictionSource.values().contains(v2));
    }
}
```

```console
V1 (no readResolve)
  stream length            = 91 bytes
  deserialized             = ADMIN
  == RestrictionSourceV1.ADMIN ? false
  identity: canonical=4a574795 decoded=5b480cf9
  in values() ?            false
V2 (readResolve)
  stream length            = 101 bytes
  deserialized             = ADMIN
  == RestrictionSource.ADMIN ?   true
  in values() ?            true
```

`toString()` prints `ADMIN` in both cases. That is the trap: every log line, every debugger
watch, every `assertEquals` on the string says the object is fine, and `==` says it is a sixth
instance. `values().contains(v1)` is `false` because `List.contains` falls back to `equals`, which
this class does not override, which is `Object.equals`, which is `==`.

**Insight:** deserialization does not call your constructor. `ObjectInputStream` allocates the
object through the same mechanism `Unsafe.allocateInstance` provides — no constructor body runs,
no static initialiser of yours re-runs — and then writes the field values straight out of the
stream. Nothing in that path knows the class has canonical instances. `readResolve` is the one
hook the serialization protocol gives you *after* the object graph is fully reconstituted: return
a different object and `ObjectInputStream` substitutes it, including in every back-reference
already recorded in the stream's handle table.

The exact signature is:

```java
private Object readResolve() throws ObjectStreamException;
```

**The access modifier is a design decision, not boilerplate.** `readResolve` is invoked only if
it is *accessible from the class being deserialized*. Declared `private`, it applies to this class
alone and no subclass can inherit it. Declared `protected` or `public`, every subclass inherits
it — and then deserializing a subclass instance returns an instance of the *superclass*, silently,
because your `VALUES.get(index)` knows nothing about the subclass. Java's serialization
specification calls this out directly. Our class is `final`, so the question is moot here, but
`private` is the right habit precisely because it stays correct when `final` is later removed.

The 10-byte difference between the streams is not `readResolve` — the method is not written to the
stream at all. It is the extra `int index` field: `V1` has two fields, `RestrictionSource` has
three, and the class descriptor carries the field name `index` and its `I` type code. Written as
text (never paste raw serialized bytes into Markdown), the 101-byte stream hex-dumps as:

```text
0000  ac ed 00 05 73 72 00 11 52 65 73 74 72 69 63 74
0010  69 6f 6e 53 6f 75 72 63 65 00 00 00 00 00 00 00
0020  01 02 00 03 49 00 05 69 6e 64 65 78 5a 00 0b 73
0030  79 73 74 65 6d 4f 77 6e 65 64 4c 00 04 6e 61 6d
0040  65 74 00 12 4c 6a 61 76 61 2f 6c 61 6e 67 2f 53
0050  74 72 69 6e 67 3b 78 70 00 00 00 03 00 74 00 05
0060  41 44 4d 49 4e
```

`ac ed` is `STREAM_MAGIC`, `00 05` is `STREAM_VERSION`, `73` is `TC_OBJECT`, `72` is
`TC_CLASSDESC`, then the class name, the `serialVersionUID`, the flag byte `02`
(`SC_SERIALIZABLE`), a field count of `3`, and the three field descriptors — `I index`,
`Z systemOwned`, `L java/lang/String; name`. The payload at the end is the `int` `3`, the
`boolean` `0`, and the string `ADMIN`. No method, and no notion of "this is a constant", appears
anywhere in it.

### Proving the pattern is still not safe

`readResolve` closes the serialization hole. It does nothing about reflection, because reflection
does not go through the stream at all — it calls the private constructor directly.

```java
import java.lang.reflect.Constructor;

public final class ReflectionAttack {
    public static void main(String[] args) throws Exception {
        Constructor<RestrictionSource> ctor =
                RestrictionSource.class.getDeclaredConstructor(String.class, boolean.class, int.class);
        System.out.println("declared constructor      = " + ctor);
        System.out.println("accessible before setter? " + ctor.canAccess(null));
        ctor.setAccessible(true);
        RestrictionSource sixth = ctor.newInstance("ADMIN", false, 3);

        System.out.println("manufactured             = " + sixth);
        System.out.println("== RestrictionSource.ADMIN ? " + (sixth == RestrictionSource.ADMIN));
        System.out.println("values().size()          = " + RestrictionSource.values().size());
        System.out.println("values().contains(sixth) ? " + RestrictionSource.values().contains(sixth));
        System.out.println("systemOwned() agrees ?   " + (sixth.systemOwned() == RestrictionSource.ADMIN.systemOwned()));

        // The switch-on-identity that the pattern promised is safe:
        System.out.println("lifted at AA-801 ?       " + liftsAtActivation(sixth));
        System.out.println("canonical lifts ?        " + liftsAtActivation(RestrictionSource.SYSTEM_ONBOARDING));

        // A real enum refuses the same move, and not for module reasons.
        Constructor<?> enumCtor = RestrictionSourceEnum.class.getDeclaredConstructors()[0];
        System.out.println("enum declared ctor       = " + enumCtor);
        enumCtor.setAccessible(true);           // succeeds: same unnamed module
        try {
            enumCtor.newInstance("ADMIN", 3, false);
        } catch (Throwable t) {
            System.out.println("enum reflective new     -> " + t.getClass().getName() + ": " + t.getMessage());
        }
    }

    private static boolean liftsAtActivation(RestrictionSource source) {
        return source == RestrictionSource.SYSTEM_ONBOARDING;
    }
}
```

```console
declared constructor      = private RestrictionSource(java.lang.String,boolean,int)
accessible before setter? false
manufactured             = ADMIN
== RestrictionSource.ADMIN ? false
values().size()          = 5
values().contains(sixth) ? false
systemOwned() agrees ?   true
lifted at AA-801 ?       false
canonical lifts ?        true
enum declared ctor       = private RestrictionSourceEnum(java.lang.String,int,boolean)
enum reflective new     -> java.lang.IllegalArgumentException: Cannot reflectively create enum objects
```

A sixth `RestrictionSource` exists. It prints as `ADMIN`, it answers `systemOwned()` the same way
`ADMIN` does, and it is invisible to `values()`. A real `enum` refuses the identical call —
`Constructor.newInstance` checks the `ACC_ENUM` flag on the declaring class and throws
`IllegalArgumentException: Cannot reflectively create enum objects` before running any bytecode.
Note that `setAccessible(true)` *succeeded* on the enum constructor; the refusal is specific to
enums, not a module-access accident.

The fix is not a cleverer guard inside the class. The fix is `enum`.
[The enum singleton and the attacks it defeats](03g-enum-singleton.md) (leaf 4.5.5) owns the
full attack surface — `Unsafe.allocateInstance`, `ObjectStreamClass` field spoofing, the
`enum`-as-singleton that defeats all of it — so the defence lives there; the demonstration lives
here.

### What a real `enum` gives you that this class does not

| Facility | Hand-rolled `RestrictionSource` | `enum RestrictionSource` |
|---|---|---|
| `values()` | Written by hand, must be kept in sync with the constants | Generated from `$VALUES` |
| `valueOf(String)` | Written by hand, linear scan | Generated, hash-based via `Class.enumConstantDirectory` |
| `ordinal()` / `name()` | Hand-maintained `index` and `name` fields | Injected by the compiler into the `Enum` superconstructor |
| `Comparable` | Absent unless written | Final, by `ordinal` |
| `EnumSet` / `EnumMap` | Ineligible; you get `HashSet` and its hashing cost | Eligible; bit-vector set, array-backed map |
| `switch` | Not permitted — the case labels must be constant expressions | Permitted, and exhaustive-checked in a `switch` expression |
| Deserialization identity | Only if you write `readResolve` correctly | Guaranteed; the stream carries the name and `Enum.valueOf` resolves it |
| Reflective instantiation | Possible, as proved above | Refused by `Constructor.newInstance` |
| Closed set | Convention only | Compiler-enforced |

The mechanism behind that table in one paragraph: `javac` turns `enum RestrictionSource { ADMIN }`
into a `final class RestrictionSource extends java.lang.Enum<RestrictionSource>` with
`ACC_ENUM` set, one `public static final` field per constant, a synthetic
`private static final RestrictionSource[] $VALUES`, a synthetic `$values()` factory, a `values()`
that returns `$VALUES.clone()`, a `valueOf(String)` delegating to `Enum.valueOf`, and a private
constructor whose first two parameters are the name and the ordinal, injected at each constant's
construction site inside `<clinit>`. Serialization of an enum is handled by `ObjectOutputStream`
as a distinct `TC_ENUM` record carrying only the constant's `name()`, and `readResolve`,
`readObject` and `writeObject` on an enum are **ignored** by the protocol.
`../enums/03-internals-enums.md` owns that desugaring in full.

> **Definition.** The typesafe enum pattern is a `final class` that hides its constructor,
> publishes its instances as `public static final` fields, enumerates them through a private
> static list, and restores canonical identity after deserialization with `readResolve` — giving
> everything `enum` gives except protection from reflection, and requiring you to maintain by hand
> everything the compiler would otherwise generate.

### Diff vs the real one — `RestrictionSource` vs `enum`

| Axis | This build | The real `enum` |
|---|---|---|
| Edge cases | `valueOf` linear-scans; a null `name` argument throws `NullPointerException` from `equals` on the candidate, not a clear message | `Enum.valueOf` throws `NullPointerException("Name is null")` explicitly, and `IllegalArgumentException` naming the class and the constant |
| Intrinsics | None. `values()` is a field read of a `List.of` view | `values()` is `$VALUES.clone()`, an intrinsic-backed array clone; `ordinal()` is a final field read that inlines to nothing |
| Serialization | Full field-by-field graph plus a `readResolve` you must write and get right; 101 bytes for one constant | `TC_ENUM` record carrying the name only; identity guaranteed by the protocol, `readResolve` ignored |
| Null policy | Nothing prevents `new RestrictionSource(null, false, 0)` from reflection | Constants cannot be null; `EnumMap` rejects null keys, `EnumSet` rejects null elements |
| Thread safety | Safe by class-initialisation semantics: `<clinit>` runs under the class-init lock, and the `final` fields are safely published | Identical guarantee, same mechanism |
| Allocation tricks | None. Five instances, one `List.of` (an `ImmutableCollections.ListN`), permanent | Same five instances, plus `$VALUES` and one array clone per `values()` call — the cost leaf 4.5.6 measures |
| Why the JDK bothers | Because every item in the table above was hand-written, per project, and got it wrong — usually the `readResolve`, sometimes the `values()` copy | `enum` moves all of it into the compiler and the serialization protocol, where it cannot be forgotten |

**Interview:** *"Why does a serialized singleton break `==`, and what do you do about it?"* —
Deserialization allocates without calling the constructor, so you get a structurally identical but
distinct object; add `private Object readResolve()` returning the canonical instance, and prefer a
single-constant `enum`, which the serialization protocol handles by name and which reflection
cannot instantiate.

---

The §4.5-wide **diff vs the compiler's generated enum** — `$VALUES`, `$SwitchMap`, the `Enum`
superclass, and the constructor injection of name and ordinal — is leaf 4.5.7, in
[The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md).

---

## Pitfalls

### Believing `readResolve` makes a hand-rolled typesafe enum as safe as an `enum`

**Wrong**

```java
Constructor<RestrictionSource> ctor =
        RestrictionSource.class.getDeclaredConstructor(String.class, boolean.class, int.class);
ctor.setAccessible(true);
RestrictionSource sixth = ctor.newInstance("ADMIN", false, 3);
```

```console
manufactured             = ADMIN
== RestrictionSource.ADMIN ? false
values().size()          = 5
values().contains(sixth) ? false
```

Five canonical instances, one impostor that prints identically and is invisible to `values()`.

**Right**

```java
public enum RestrictionSourceEnum {
    SYSTEM_ONBOARDING(true), SYSTEM_COMPLIANCE(true), SYSTEM_LIFECYCLE(true),
    ADMIN(false), CLIENT(false);
    private final boolean systemOwned;
    RestrictionSourceEnum(boolean systemOwned) { this.systemOwned = systemOwned; }
    public boolean systemOwned() { return systemOwned; }
}
```

```console
enum reflective new     -> java.lang.IllegalArgumentException: Cannot reflectively create enum objects
```

**Why people believe it:** `readResolve` genuinely closes the hole that people actually hit, so
adding it makes the observed bug go away, and the reflection path feels like an attack rather than
an accident. It is not only an attack — deserialization frameworks, mocking libraries and
dependency-injection containers all call private constructors reflectively as a matter of routine.

### Publishing the constant list as a `public static final` array

**Wrong**

```java
public final class RestrictionSourceLeaky {
    private final String name;
    private RestrictionSourceLeaky(String name) { this.name = name; }

    public static final RestrictionSourceLeaky SYSTEM_ONBOARDING = new RestrictionSourceLeaky("SYSTEM_ONBOARDING");
    public static final RestrictionSourceLeaky ADMIN             = new RestrictionSourceLeaky("ADMIN");
    public static final RestrictionSourceLeaky CLIENT            = new RestrictionSourceLeaky("CLIENT");

    /** The tempting shape: a public array, so callers can loop without a wrapper. */
    public static final RestrictionSourceLeaky[] VALUES = { SYSTEM_ONBOARDING, ADMIN, CLIENT };

    @Override public String toString() { return name; }
}
```

`final` protects the *reference*, never the contents:

```console
before: [SYSTEM_ONBOARDING, ADMIN, CLIENT]
after : [SYSTEM_ONBOARDING, CLIENT, CLIENT]
ADMIN still reachable by field: ADMIN
ADMIN findable by scanning VALUES: false
```

One line of caller code — `RestrictionSourceLeaky.VALUES[1] = RestrictionSourceLeaky.CLIENT;` —
compiles, and now every subsystem that enumerates restriction sources by scanning `VALUES` cannot
see `ADMIN`. `ADMIN`-sourced restrictions stop being reported, and the field is still there, so
nothing looks broken.

**Right**

Keep the array or list `private` and publish an unmodifiable view:

```java
private static final List<RestrictionSource> VALUES =
        List.of(SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT);

public static List<RestrictionSource> values() { return VALUES; }
```

```console
the List.of view refuses the same move:
  java.lang.UnsupportedOperationException
  values() = [SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT]
```

**Why people believe it:** `public static final` reads as "constant", and for a primitive or a
`String` it genuinely is one, so the habit is reinforced everywhere else in the language. An array
field is a constant reference to a mutable object, and the compiler gives no warning. This is the
exact reason the real `Enum.values()` returns `$VALUES.clone()` and pays an allocation per call
rather than handing out its own array.

### Declaring `VALUES` before the constants it holds

**Wrong**

```java
public final class RestrictionSourceMisordered {

    private final String name;
    private RestrictionSourceMisordered(String name) { this.name = name; }

    /** Declared BEFORE the constants, so it sees them unassigned. */
    private static final List<RestrictionSourceMisordered> VALUES =
            List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);

    public static final RestrictionSourceMisordered SYSTEM_ONBOARDING = new RestrictionSourceMisordered("SYSTEM_ONBOARDING");
    public static final RestrictionSourceMisordered ADMIN             = new RestrictionSourceMisordered("ADMIN");
    public static final RestrictionSourceMisordered CLIENT            = new RestrictionSourceMisordered("CLIENT");

    public static List<RestrictionSourceMisordered> values() { return VALUES; }

    @Override public String toString() { return name; }
}
```

```console
p1b/RestrictionSourceMisordered.java:10: error: illegal forward reference
            List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
                    ^
p1b/RestrictionSourceMisordered.java:10: error: illegal forward reference
            List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
                                       ^
p1b/RestrictionSourceMisordered.java:10: error: illegal forward reference
            List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
                                              ^
3 errors
```

That is the *lucky* version. Hide the same forward reference behind a static factory method and
`javac` can no longer see it, so the class compiles:

```java
    private static final List<RestrictionSourceMisordered> VALUES = buildValues();

    public static final RestrictionSourceMisordered SYSTEM_ONBOARDING = new RestrictionSourceMisordered("SYSTEM_ONBOARDING");
    public static final RestrictionSourceMisordered ADMIN             = new RestrictionSourceMisordered("ADMIN");
    public static final RestrictionSourceMisordered CLIENT            = new RestrictionSourceMisordered("CLIENT");

    private static List<RestrictionSourceMisordered> buildValues() {
        return List.of(SYSTEM_ONBOARDING, ADMIN, CLIENT);
    }
```

```console
java.lang.ExceptionInInitializerError: null
  cause: java.lang.NullPointerException
```

`List.of` rejects nulls, so the failure is at least loud. Had the code used
`Arrays.asList` or an `ArrayList` copy constructor, both of which accept nulls, `VALUES` would be a three-element
list of nulls and every enumeration in the system would silently iterate nothing.

**Right**

Constants first, aggregate second — the order the working build uses:

```java
    public static final RestrictionSource ADMIN = new RestrictionSource("ADMIN", false, 3);
    public static final RestrictionSource CLIENT = new RestrictionSource("CLIENT", false, 4);

    private static final List<RestrictionSource> VALUES =
            List.of(SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT);
```

```console
  in values() ?            true
```

**Why people believe it:** field declaration order feels like a formatting choice, and in almost
every other class it is one — instance fields are assigned by the constructor whatever order they
are declared in. Static initialisers are different: they run top to bottom exactly once inside
`<clinit>`, so a static field's initialiser can only see what is textually above it. `javac`
catches the direct case and cannot catch the indirect one.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| Typesafe enum pattern | `final class`, private constructor, `public static final` instances, private static `VALUES`, `readResolve` |
| Declaration order | Constants first, then the aggregate. Direct reverse = `error: illegal forward reference`; indirect = `ExceptionInInitializerError` / `NullPointerException` |
| Publishing the constant list | Never a `public static final` array — `final` protects the reference, not the contents. Return an unmodifiable `List.of` view |
| `readResolve` signature | `private Object readResolve() throws ObjectStreamException` |
| `readResolve` access | `private`, so no subclass inherits substitution and returns a superclass instance |
| Why `readResolve` is needed | Deserialization allocates without calling the constructor, so `==` against the canonical constant fails while `toString()` still looks right |
| Symptom to recognise | Logs say `ADMIN`, `==` says false, `values().contains(decoded)` says false |
| Why it is not enough | Reflection calls the private constructor: `getDeclaredConstructor` + `setAccessible(true)` + `newInstance` manufactures a sixth instance |
| What `enum` adds | `values()`, `valueOf`, `ordinal()`, `name()`, `Comparable`, `EnumSet`/`EnumMap` eligibility, `switch`, guaranteed deserialization identity, compiler-enforced closed set |
| Enum vs reflection | `Constructor.newInstance` throws `IllegalArgumentException: Cannot reflectively create enum objects` |
| Enum serialization | `TC_ENUM` record carrying `name()` only; `readResolve`, `readObject` and `writeObject` on an enum are ignored |
| Stream header | `ac ed` `STREAM_MAGIC`, `00 05` `STREAM_VERSION`, `73` `TC_OBJECT`, `72` `TC_CLASSDESC` |
| When to still hand-roll it | Constants that must extend a shared abstract base, a set discovered at class-init time, or a constant that needs a type parameter |
| §4.5 diff table | Leaf 4.5.7, in `03b-enum-values-cache-and-diff.md` |

---

## Self-test

**Q1.** A colleague reports that after adding a Redis cache in front of `ClientRestrictions`, a
`SYSTEM_ONBOARDING` restriction stopped lifting at `AA-801`. The `RestrictionSource` type is a
hand-rolled typesafe enum. What is the first thing you check?

<details><summary>Answer</summary>

Whether `RestrictionSource` has a `readResolve`, and whether the lift check compares with `==`.
A Redis cache serializes and deserializes; deserialization allocates a fresh object without
calling the constructor, so the decoded source is a distinct instance that prints as
`SYSTEM_ONBOARDING` and fails `source == RestrictionSource.SYSTEM_ONBOARDING`. The lift rule is
identity-based, so it silently stops firing. Adding `private Object readResolve()` returning the
canonical instance fixes it; converting the type to an `enum` fixes it and also closes the
reflection hole, because the serialization protocol writes an enum as a `TC_ENUM` record carrying
only the name and resolves it through `Enum.valueOf`.

</details>

**Q2.** Why does `readResolve` have to be `private` on a class that has a real subclass, and what
goes wrong if it is `protected`?

<details><summary>Answer</summary>

`readResolve` is invoked only if it is accessible from the class being deserialized. Declared
`private`, it applies to that one class. Declared `protected` or `public`, every subclass inherits
it, so deserializing a subclass instance calls the superclass's `readResolve`, which returns a
canonical *superclass* instance — the stream's subclass data is discarded and the caller gets an
object of the wrong type, silently, or a `ClassCastException` at the assignment. `private` is the
right default even on a `final` class, because it stays correct if `final` is later removed.

</details>

**Q3.** `readResolve` is in place and the `==` bug is gone. Name a non-adversarial caller that
still manufactures an extra instance.

<details><summary>Answer</summary>

Anything that constructs objects reflectively as a matter of routine, which is most of a modern
Java stack: a dependency-injection container instantiating by private constructor, a mocking
library building an instance without running initialisers, a JSON or protobuf mapper that
allocates then populates fields, an object-relational mapper hydrating an entity, or a test
fixture builder using `setAccessible(true)`. None of these is an attack; they all hit the same
`getDeclaredConstructor` + `setAccessible(true)` + `newInstance` path that produced the sixth
`RestrictionSource` above, and the resulting instance fails every `==` comparison and is invisible
to `values()`. The class has no way to refuse, which is why the fix is `enum` rather than a
cleverer guard.

</details>

**Q4.** Why does the pattern return an unmodifiable `List.of` view from `values()` instead of exposing the array,
and what does the real `Enum.values()` do instead?

<details><summary>Answer</summary>

Because `public static final RestrictionSource[] VALUES` is a constant *reference* to a mutable
object: `VALUES[1] = CLIENT` compiles from any caller and silently rewrites the constant list for
the whole JVM, as the pitfall above shows. `List.of` returns an immutable
`ImmutableCollections` list whose `set` throws `UnsupportedOperationException`, and the field stays
`private`. The real `Enum.values()` solves the same problem differently: it keeps a private
synthetic `$VALUES` array and returns `$VALUES.clone()`, so callers get a mutable array that is
not the enum's own — trading one array allocation per call for the same safety. Leaf 4.5.6
measures that allocation.

</details>

**Q5.** What is actually in the serialized stream of one typesafe enum constant, and what is
conspicuously absent?

<details><summary>Answer</summary>

Present: `ac ed` `STREAM_MAGIC`; `00 05` `STREAM_VERSION`; `73` `TC_OBJECT`; `72` `TC_CLASSDESC`
followed by the class name `RestrictionSource`, the `serialVersionUID`, the flag byte `02`
(`SC_SERIALIZABLE`), a field count of 3, and a descriptor per field — `I index`, `Z systemOwned`,
`L java/lang/String; name` — then the payload: the `int` 3, the `boolean` 0, and the string
`ADMIN`. 101 bytes in total.

Absent: any method, and any notion that this class has canonical instances. `readResolve` is not
written to the stream; it is looked up reflectively on the receiving side. That is why the stream
is identical in shape whether or not the class defines it, and why the 10-byte difference from the
`readResolve`-less version is entirely the extra `int index` field and its descriptor, not the
method.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.5.1 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 682
