# 03 Java Core — Enum-shaped builds — the enum singleton, and the attacks it defeats — BUILD IT (§4.5.5)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The enum state machine](03a-enum-state-machine-and-singleton.md) · Next: [The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md)

---

## 4.5.5 The enum singleton, and each attack attempted `[PROVE]`

[File 10](03-enums-exceptions-resources.md) built the pre-Java-5 typesafe enum by hand: a `private` constructor, `public static
final` constants, `readResolve` to survive deserialization — and then a reflection attack that
called `setAccessible(true)` on the private constructor and manufactured a sixth instance of a
five-instance type. The defence is not a better `readResolve`. The defence is to stop writing the
class and let `enum` write it, because the JVM, core reflection and the serialization protocol
each contain an explicit special case for enums that no hand-rolled class can obtain.

A singleton worth attacking needs observable state, so this one is the idempotency-key registry
that `PaymentService` consults on every card deposit — 95k/day, 40/sec at peak. Two instances of
it means a replayed deposit gets captured twice.

```java
package idem;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public enum IdempotencyRegistry {

    SHARED;

    private final Map<String, Long> claimed = new ConcurrentHashMap<>();
    private final AtomicLong replays = new AtomicLong();

    /**
     * Returns true if this is the first time the key has been presented, false if the
     * caller is replaying a card deposit the PaymentService already accepted.
     */
    public boolean claim(String idempotencyKey, long sequence) {
        Long existing = claimed.putIfAbsent(idempotencyKey, sequence);
        if (existing == null) {
            return true;
        }
        replays.incrementAndGet();
        return false;
    }

    public int size() {
        return claimed.size();
    }

    public long replays() {
        return replays.get();
    }

    /** Exists only so the note can call the inherited final Enum.clone() legally. */
    public Object attemptClone() throws CloneNotSupportedException {
        return super.clone();
    }

    @Override
    public String toString() {
        return "IdempotencyRegistry.SHARED[claimed=" + claimed.size()
                + ", replays=" + replays.get() + "]";
    }
}
```

Baseline, so that "is it the same instance" has consequences:

```console
== baseline: the singleton doing real work ==
first  claim DEP-301/aa11: true
replay claim DEP-301/aa11: false
state: IdempotencyRegistry.SHARED[claimed=1, replays=1]
```

### (a) Reflection

```java
static void attackReflection() {
    try {
        Constructor<IdempotencyRegistry> ctor =
                IdempotencyRegistry.class.getDeclaredConstructor(String.class, int.class);
        System.out.println("constructor found : " + ctor);
        ctor.setAccessible(true);
        System.out.println("setAccessible(true): returned normally");
        IdempotencyRegistry forged = ctor.newInstance("FORGED", 1);
        System.out.println("forged instance   : " + forged + " (attack SUCCEEDED)");
    } catch (Exception ex) {
        System.out.println("newInstance threw : " + ex.getClass().getName()
                + ": " + ex.getMessage());
    }
}
```

```console
== attack (a) reflection ==
constructor found : private idem.IdempotencyRegistry(java.lang.String,int)
setAccessible(true): returned normally
newInstance threw : java.lang.IllegalArgumentException: Cannot reflectively create enum objects
```

Read the three lines in order, because the order is the whole point.

The constructor **is found**, and its signature is `(String, int)` — the compiler injected the
name and ordinal parameters that `Enum`'s constructor needs. `../enums/03-internals-enums.md`
owns that desugaring.

`setAccessible(true)` **returns normally**. It is not the guard. Nothing about an enum
constructor makes it un-openable; the same call on the hand-rolled class in file 10 succeeded
too, and it succeeds here.

The failure is later, inside `newInstance`. In JDK 21 the path is
`Constructor.newInstance` → `newInstanceWithCaller` → `acquireConstructorAccessor`, and the check
sits in `acquireConstructorAccessor` at `java.base/java/lang/reflect/Constructor.java:546-547`:

```java
// Otherwise fabricate one and propagate it up to the root
// Ensure the declaring class is not an Enum class.
if ((clazz.getModifiers() & Modifier.ENUM) != 0)
    throw new IllegalArgumentException("Cannot reflectively create enum objects");
```

Two lines of source, and they are the reason `enum` beats the typesafe-enum pattern. The test is
on the class's `ACC_ENUM` flag (`0x4000`) in the class file, which `javac` sets on any `enum`
declaration and which no ordinary class can claim. The check is inside
`acquireConstructorAccessor`, which is only reached when no accessor has been cached yet — that
is why the guard cannot be bypassed by warming the constructor up first: the accessor is never
created for an enum, so the check runs on every attempt.

**Insight:** `setAccessible` controls *access*, `newInstance` controls *instantiation*, and the
enum protection lives entirely in the second. An interviewer asking "does `setAccessible` fail on
an enum?" is checking whether you have run this or only read about it. It does not fail.

### (b) Serialization

```java
static void attackSerialization() throws Exception {
    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
    try (ObjectOutputStream out = new ObjectOutputStream(bytes)) {
        out.writeObject(IdempotencyRegistry.SHARED);
    }
    byte[] form = bytes.toByteArray();
    System.out.println("serialized length : " + form.length + " bytes");
    StringBuilder hex = new StringBuilder();
    for (byte b : form) {
        hex.append(String.format("%02x ", b));
    }
    System.out.println("hex dump          : " + hex.toString().trim());
    StringBuilder printable = new StringBuilder();
    for (byte b : form) {
        printable.append(b >= 0x20 && b < 0x7f ? (char) b : '_');
    }
    System.out.println("printable         : " + printable);

    Object back;
    try (ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(form))) {
        back = in.readObject();
    }
    System.out.println("deserialized      : " + back);
    System.out.println("back == SHARED    : " + (back == IdempotencyRegistry.SHARED));
    System.out.println("identityHashCode  : " + System.identityHashCode(back) + " vs "
            + System.identityHashCode(IdempotencyRegistry.SHARED));
}
```

```console
== attack (b) serialization ==
serialized length : 83 bytes
hex dump          : ac ed 00 05 7e 72 00 18 69 64 65 6d 2e 49 64 65 6d 70 6f 74 65 6e 63 79 52 65 67 69 73 74 72 79 00 00 00 00 00 00 00 00 12 00 00 78 72 00 0e 6a 61 76 61 2e 6c 61 6e 67 2e 45 6e 75 6d 00 00 00 00 00 00 00 00 12 00 00 78 70 74 00 06 53 48 41 52 45 44
printable         : ____~r__idem.IdempotencyRegistry___________xr__java.lang.Enum___________xpt__SHARED
deserialized      : IdempotencyRegistry.SHARED[claimed=1, replays=1]
back == SHARED    : true
identityHashCode  : 531885035 vs 531885035
```

`==` holds. The stream explains why. `ac ed 00 05` is the stream magic and version; `7e` is
`TC_ENUM`; then the class descriptor for `idem.IdempotencyRegistry` with flags `12` —
`SC_SERIALIZABLE | SC_ENUM` — its `java.lang.Enum` superclass descriptor, and then `74 00 06`
followed by `SHARED`: a UTF string of length 6 (the underscores in the printable line are non-printable bytes, not
elided text). **The constant's name and nothing else.** No
field data. `claimed` and `replays` were never written, which is also why the deserialized object
still reports `claimed=1, replays=1` — it is literally the same object, with the state the
baseline left in it.

`ObjectOutputStream.writeEnum` (JDK 21, line 1412 onward) is the whole write side:

```java
bout.writeByte(TC_ENUM);
ObjectStreamClass sdesc = desc.getSuperDesc();
writeClassDesc((sdesc.forClass() == Enum.class) ? desc : sdesc, false);
handles.assign(unshared ? null : en);
writeString(en.name(), false);
```

and `ObjectInputStream.readEnum` (line 2200 onward) resolves it:

```java
Enum<?> en = Enum.valueOf((Class)cl, name);
```

`Enum.valueOf` looks the name up in the constant map for that `Class` and returns the existing
constant. No instance is created, so there is nothing for a `readResolve` to fix, and
`readResolve` is unnecessary on an enum. The belt-and-braces is in `Enum` itself
(`java.base/java/lang/Enum.java:311`):

```java
private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
    throw new InvalidObjectException("can't deserialize enum");
}
```

Default deserialization of an enum is not merely unused, it is actively forbidden — if a stream
ever routed an enum through the ordinary object path, it would fail loudly rather than produce a
duplicate.

Contrast with file 10's hand-rolled typesafe enum: it needed `readResolve` to survive
deserialization at all, and even with `readResolve` correct, reflection still manufactured an
extra instance. The enum needs no `readResolve` and reflection cannot touch it.

### (c) Cloning

```java
static void attackClone() throws Exception {
    Method clone = Enum.class.getDeclaredMethod("clone");
    System.out.println("Enum.clone()      : " + clone);
    System.out.println("is final          : "
            + java.lang.reflect.Modifier.isFinal(clone.getModifiers()));
    try {
        Object copy = IdempotencyRegistry.SHARED.attemptClone();
        System.out.println("clone SUCCEEDED (unexpected): " + copy);
    } catch (CloneNotSupportedException ex) {
        System.out.println("super.clone() threw: " + ex.getClass().getName()
                + ": " + ex.getMessage());
    }
}
```

```console
== attack (c) cloning ==
Enum.clone()      : protected final java.lang.Object java.lang.Enum.clone() throws java.lang.CloneNotSupportedException
is final          : true
super.clone() threw: java.lang.CloneNotSupportedException: null
```

`java.base/java/lang/Enum.java:202-204` is three lines:

```java
protected final Object clone() throws CloneNotSupportedException {
    throw new CloneNotSupportedException();
}
```

`protected` so only a subclass can reach it, `final` so no subclass can replace it, and the body
unconditionally throws. `CloneNotSupportedException: null` in the output is the no-argument
constructor — there is no message, because there is nothing to explain.

And the `final` is not decoration. Attempting to override it:

```java
public enum BonusGrantRegistry {
    SHARED;

    @Override
    protected Object clone() {
        return this;
    }
}
```

```console
broken3/idem/BonusGrantRegistry.java:7: error: clone() in BonusGrantRegistry cannot override clone() in Enum
    protected Object clone() {
                     ^
  overridden method is final
1 error
```

Even the *benign* override — returning `this`, which is what a singleton would want — is
rejected. The language does not negotiate here. (`Enum.finalize()` at line 305 is `final` and
empty for the same defensive reason: no subclass can hook object finalization to resurrect a
constant.)

### (d) A second class loader — the attack that works

```java
static Object constantFrom(ClassLoader loader) throws Exception {
    Class<?> type = loader.loadClass("idem.IdempotencyRegistry");
    Object[] constants = type.getEnumConstants();
    return constants[0];
}

public static void run(String isolatedDir) throws Exception {
    URL[] urls = { Path.of(isolatedDir).toUri().toURL() };

    // parent == null means the bootstrap loader only, so java.base resolves but
    // idem.IdempotencyRegistry does not -- each loader must define its own copy.
    try (URLClassLoader operatorConsoleLoader = new URLClassLoader("operatorConsole", urls, null);
         URLClassLoader paymentRunLoader = new URLClassLoader("paymentRun", urls, null)) {

        Object a = constantFrom(operatorConsoleLoader);
        Object b = constantFrom(paymentRunLoader);
        Object app = IdempotencyRegistry.SHARED;

        System.out.println("app  loader : " + app.getClass().getClassLoader());
        System.out.println("op   loader : " + a.getClass().getClassLoader());
        System.out.println("pay  loader : " + b.getClass().getClassLoader());
        System.out.println("Class objects distinct (op vs pay) : "
                + (a.getClass() != b.getClass()));
        System.out.println("Class objects distinct (app vs op) : "
                + (app.getClass() != a.getClass()));
        System.out.println("a == b                             : " + (a == b));
        System.out.println("names equal                        : "
                + a.getClass().getName().equals(b.getClass().getName()));
        System.out.println("identityHashCodes  : " + System.identityHashCode(a)
                + " / " + System.identityHashCode(b)
                + " / " + System.identityHashCode(app));

        Method claimA = a.getClass().getMethod("claim", String.class, long.class);
        Method claimB = b.getClass().getMethod("claim", String.class, long.class);
        System.out.println("op  claim  bb22 : " + claimA.invoke(a, "bb22", 1L));
        System.out.println("pay claim  bb22 : " + claimB.invoke(b, "bb22", 1L)
                + "   <-- should have been a replay; the registry is duplicated");

        try {
            IdempotencyRegistry narrowed = (IdempotencyRegistry) a;
            System.out.println("cast succeeded: " + narrowed);
        } catch (ClassCastException ex) {
            System.out.println("cast to the app-loaded type : "
                    + ex.getClass().getName() + ": " + ex.getMessage());
        }
    }
}
```

```console
== attack (d) a second class loader ==
app  loader : jdk.internal.loader.ClassLoaders$AppClassLoader@2c854dc5
op   loader : java.net.URLClassLoader@30dae81
pay  loader : java.net.URLClassLoader@1b2c6ec2
Class objects distinct (op vs pay) : true
Class objects distinct (app vs op) : true
a == b                             : false
names equal                        : true
identityHashCodes  : 1848402763 / 933699219 / 531885035
op  claim  bb22 : true
pay claim  bb22 : true   <-- should have been a replay; the registry is duplicated
cast to the app-loaded type : java.lang.ClassCastException: class idem.IdempotencyRegistry cannot be cast to class idem.IdempotencyRegistry (idem.IdempotencyRegistry is in unnamed module of loader 'operatorConsole' @30dae81; idem.IdempotencyRegistry is in unnamed module of loader 'app')
```

Three `IdempotencyRegistry.SHARED` objects exist in one JVM, with three different identity hash
codes. Both `claim("bb22", 1L)` calls return `true`, so the same idempotency key was accepted
twice and a card deposit would be captured twice. The `ClassCastException` message is the
diagnosis printed by the JVM itself: identical names, different loaders, therefore different
types.

Be clear about what this is. It is **not a vulnerability in `enum`**. A runtime type's identity is
the pair (defining loader, binary name), so two loaders that each define `idem.IdempotencyRegistry`
produce two unrelated types, each with its own `<clinit>`, its own `$VALUES` array, and its own
constants. Nothing about the singleton idiom is involved — the static holder idiom, double-checked
locking and an eager `static final` all duplicate identically under two loaders, because the
static field they live in is per-`Class`, and there are two `Class` objects. **No singleton idiom
in Java survives a second class loader.** The fix is never in the singleton; it is in the
deployment — one loader owns the type, or the shared state moves out of static memory entirely
(Redis, or a unique index on the idempotency key in the database).

`../classes-and-initialization/03b-internals-class-loaders-and-identity.md` owns loader-based type
identity, the delegation model, and the `null` parent that makes this demonstration work.

**Interview:** "Is the enum singleton immune to everything?" — reflection, serialization and
cloning, yes, each with an explicit special case in the JDK. A second class loader, no; and
neither is any other Java singleton, because type identity is (loader, name).

### The four idioms

Guide 05 owns the memory model. The one-line version: double-checked locking is only correct if
the instance field is `volatile`, because without it a second thread can observe a non-null
reference to a partially constructed object — the write publishing the reference can be seen
before the writes initialising the object's fields. See guide 05 for the happens-before argument.

| | Enum singleton | Static holder idiom | Double-checked locking | Eager `static final` |
|---|---|---|---|---|
| Lazy or eager | eager — created on first touch of the enum class | **lazy** — created on first touch of the nested holder class | lazy | eager |
| Thread safety, and what provides it | the JVM's class-initialisation lock (JVMS 5.5) | the same class-initialisation lock, on the holder class | `synchronized` block plus a **`volatile`** field; wrong without the `volatile` | class-initialisation lock |
| Reflection resistance | **yes** — `IllegalArgumentException("Cannot reflectively create enum objects")` | no — `setAccessible(true)` on the private constructor works | no | no |
| Serialization resistance | **yes** — written as a name, resolved by `Enum.valueOf`; no `readResolve` needed | only if you write `readResolve` correctly | only with `readResolve` | only with `readResolve` |
| Class-loader resistance | **no** | no | no | no |
| Testability | poor — cannot substitute, cannot reset between tests | fair — the holder can hold an injected instance if you add a setter, which reintroduces the race | fair | fair |
| Constructor arguments | **impossible** — arguments must be compile-time constants in the constant declaration | yes | yes | yes |

The enum singleton's drawbacks are real and they are the reason it is not the universal answer:

- **It is eager.** The constant is constructed during class initialisation, so a registry that
  opens a connection or reads a file does that work the first time anything touches the enum,
  including a `values()` call in an unrelated log statement.
- **It cannot take constructor arguments** that are not compile-time constants. There is no way
  to hand `SHARED` a `Clock`, a `DataSource` or a configured cap; every dependency has to be
  looked up from inside the constant, which is service-location by another name.
- **It is awkward to substitute in a test.** There is exactly one instance, it is global, and it
  accumulates state across test methods — the `claimed` map in the run above still held `aa11`
  from the baseline when the serialization attack ran, which is precisely the cross-test leakage
  that makes tests order-dependent.

That last point is why [`Clock` injection](04b-deep-copy-and-clock-injection.md) exists: time is the dependency you most often
need to control, and no static singleton lets you. Guide 16 owns the testing patterns.

> An enum singleton is a one-constant enum: eager, thread-safe by class initialisation,
> reflection-proof by an explicit check in `Constructor`, serialization-proof by name resolution
> in `ObjectInputStream`, clone-proof by a `final` throwing `Enum.clone()`, and defeated only by a
> second class loader, which defeats every other idiom equally.

### Diff vs the real one — the enum singleton

| Dimension | This build (`IdempotencyRegistry`) | What the JDK does for it, and beyond it |
|---|---|---|
| Edge cases | one constant, no arguments, no lazy init; `claimed` grows without bound | the JDK gives it `values()`, `valueOf`, `name()`, `ordinal()`, `compareTo`, `hashCode` = `System.identityHashCode`, all `final`; a production registry needs a TTL or a bounded cache |
| Intrinsics | none | none; `Enum.equals` and `Enum.hashCode` are `final` and reduce to reference comparison and identity hash, which the JIT already handles optimally |
| Serialization | inherited, `readResolve` deliberately absent | `writeEnum`/`readEnum` special cases in `ObjectOutputStream`/`ObjectInputStream`; `Enum.readObject` and `readObjectNoData` throw `InvalidObjectException("can't deserialize enum")` to close the ordinary path |
| Null policy | `claim(null, …)` would NPE inside `ConcurrentHashMap.putIfAbsent`; not validated | `Enum.valueOf(type, null)` throws `NullPointerException`; `EnumMap`/`EnumSet` reject null keys and elements |
| Thread safety | `ConcurrentHashMap` plus `AtomicLong` for the mutable state; the *instance* is safely published by class initialisation | the JVM guarantees `<clinit>` runs once under a per-class lock and that its writes are visible to any thread that later reads the constant (JVMS 5.5) |
| Allocation tricks | none | none needed — the constant is allocated once, ever; `$VALUES` is a single array, cloned on each `values()` call (leaf 4.5.6, next file) |
| Why the JDK bothers | — | because `readResolve` on a hand-rolled singleton is easy to forget and useless against reflection; special-casing enums in the reflection and serialization layers makes the guarantee structural rather than a convention |

The section-wide **Diff vs the real one** table for all of §4.5 is leaf 4.5.7, in [03b-enum-values-cache-and-diff.md](03b-enum-values-cache-and-diff.md).

---

## Pitfalls

### Believing the enum singleton is immune to every attack

**Wrong**

```java
// "It's an enum, so there is exactly one instance in the JVM. Guaranteed."
Object a = constantFrom(operatorConsoleLoader);
Object b = constantFrom(paymentRunLoader);
System.out.println("a == b : " + (a == b));
System.out.println("op  claim bb22 : " + claimA.invoke(a, "bb22", 1L));
System.out.println("pay claim bb22 : " + claimB.invoke(b, "bb22", 1L));
```

```console
a == b : false
op  claim bb22 : true
pay claim bb22 : true
```

Two registries, so the same idempotency key was accepted twice and the deposit gets captured
twice.

**Right**

State the guarantee accurately: one instance **per defining class loader**. If the singleton
holds state whose duplication is a correctness bug, either pin the type to one loader or move the
state out of static memory:

```java
// PaymentService: the uniqueness constraint lives where all loaders can see it.
boolean firstTime = idempotencyKeyStore.insertIfAbsent(key);   // unique index in the database
```

**Why people believe it:** every article about the enum singleton lists reflection,
serialization and cloning, shows each one defeated, and stops — because those three are the ones
`enum` fixes and therefore the ones worth writing about. Class loaders defeat all four idioms
equally, so the comparison articles have no reason to mention them.

### Believing an enum needs `readResolve`

**Wrong**

```java
public enum IdempotencyRegistry {
    SHARED;

    // "Belt and braces, in case deserialization creates a second one."
    private Object readResolve() {
        return SHARED;
    }
}
```

Harmless, and never called. Worse, it teaches the next reader that enum deserialization goes
through the ordinary object path, which is the belief that produces real bugs elsewhere.

**Right**

Write no `readResolve`, and know why:

```console
back == SHARED    : true
identityHashCode  : 531885035 vs 531885035
printable         : ____~r__idem.IdempotencyRegistry___________xr__java.lang.Enum___________xpt__SHARED
```

The stream carries the constant's **name** (`SHARED`, a 6-byte UTF string) and no field data.
`ObjectInputStream.readEnum` resolves it with `Enum.valueOf(cl, name)`, returning the existing
constant. No instance is created, so there is nothing to resolve. `Enum.readObject` throws
`InvalidObjectException("can't deserialize enum")` precisely so the ordinary path can never be
taken.

**Why people believe it:** because it *was* required — on the pre-Java-5 typesafe enum pattern
that file 10 builds, where `readResolve` is the only thing standing between you and a duplicate
constant. The habit outlived the pattern, and the two look similar on the page.

### Believing an enum singleton is substitutable in a test

**Wrong**

```java
// The code under test reaches for the global constant itself.
static boolean captureDepositUsingGlobal(String key) {
    return IdempotencyRegistry.SHARED.claim(key, 1L);
}

static void firstDepositTest() {
    System.out.println("firstDepositTest      : claim cc33 -> "
            + captureDepositUsingGlobal("cc33"));
}

static void duplicateRejectedTest() {
    System.out.println("duplicateRejectedTest : claim cc33 -> "
            + captureDepositUsingGlobal("cc33")
            + "   (expected true if the registry were fresh)");
}
```

```console
-- global singleton, two tests in sequence --
firstDepositTest      : claim cc33 -> true
duplicateRejectedTest : claim cc33 -> false   (expected true if the registry were fresh)
registry after both   : IdempotencyRegistry.SHARED[claimed=1, replays=1]
```

The second test did not test what it claims. There is one instance, it kept `cc33` from the
first test, and the result now depends on the order the two methods ran in. There is no
constructor to intercept, no setter to override and no `reset()` that would be safe to add.

**Right**

Take the registry as a parameter and let each test supply its own:

```java
interface KeyRegistry {
    boolean claim(String key);
}

static final class LocalKeyRegistry implements KeyRegistry {
    private final Map<String, Boolean> seen = new ConcurrentHashMap<>();

    public boolean claim(String key) {
        return seen.putIfAbsent(key, Boolean.TRUE) == null;
    }
}

static boolean captureDeposit(KeyRegistry registry, String key) {
    return registry.claim(key);
}
```

```console
-- injected registry, two tests in sequence --
firstDepositTest      : claim cc33 -> true
duplicateRejectedTest : claim cc33 -> true
```

Both tests pass independently of order, because neither shares state with the other. The single
production instance is still a singleton — it is just owned by the caller, or by the container,
instead of by a static field.

**Why people believe it:** the enum singleton's three wins (reflection, serialization, cloning)
are so clean that the idiom reads as strictly better than the alternatives, and "there is exactly
one instance" sounds like a property rather than a constraint. In production it is what you want;
in a test it is the one thing you cannot have. Guide 16 owns the testing patterns.

---

## Cheat sheet

| Thing | Fact |
|---|---|
| Enum reflection guard | `Constructor.java:546-547`, `IllegalArgumentException("Cannot reflectively create enum objects")` |
| Where the guard lives | `acquireConstructorAccessor`, not `setAccessible` — `setAccessible(true)` succeeds |
| Enum serial form | `TC_ENUM` (`0x7e`) + class desc + the constant's **name**; no field data; 83 bytes here |
| Enum deserialization | `Enum.valueOf(cl, name)`; no instance created; `readResolve` unnecessary |
| `Enum.readObject` | throws `InvalidObjectException("can't deserialize enum")` |
| `Enum.clone()` | `protected final`, throws `CloneNotSupportedException`; cannot be overridden |
| Enum singleton beaten by | a second class loader — and so is every other Java singleton |
| Type identity | (defining loader, binary name); same name + different loader = `ClassCastException` |
| Enum singleton drawbacks | eager, no constructor arguments, not substitutable in tests |
| DCL requirement | the instance field must be `volatile` (guide 05) |

## Self-test

**Q1.** Does `setAccessible(true)` fail on an enum's constructor? Where exactly does the reflection attack die?

<details><summary>Answer</summary>

No, `setAccessible(true)` returns normally — that is the distinction interviewers probe.
`getDeclaredConstructor(String.class, int.class)` also succeeds, and the returned constructor
prints as `private idem.IdempotencyRegistry(java.lang.String,int)` because `javac` injects the
name and ordinal parameters. The attack dies inside `newInstance`, on the path
`newInstance` → `newInstanceWithCaller` → `acquireConstructorAccessor`, where
`java.base/java/lang/reflect/Constructor.java:546-547` tests
`(clazz.getModifiers() & Modifier.ENUM) != 0` and throws
`IllegalArgumentException("Cannot reflectively create enum objects")`. Because the check is in
the accessor-acquisition path and an accessor is never cached for an enum, it runs on every
attempt.

</details>

**Q2.** An 83-byte serialized enum constant contains no field data. Why does the deserialized object still report the state the original had?

<details><summary>Answer</summary>

Because it is the same object. `ObjectOutputStream.writeEnum` writes `TC_ENUM`, the class
descriptor, and `en.name()` — a UTF string, `SHARED`, six bytes — and nothing else.
`ObjectInputStream.readEnum` reads the name and calls `Enum.valueOf(cl, name)`, which returns
the constant already held by that `Class`. No instance is allocated and no field is assigned, so
`back == IdempotencyRegistry.SHARED` is `true` and both report the same
`System.identityHashCode`. It also means enum fields are *not* part of the serial form: mutable
state in an enum constant survives a round trip untouched, which is a footgun if you were
relying on serialization to snapshot it.

</details>

**Q3.** Name the enum singleton's three real drawbacks and what you would do instead when one of them bites.

<details><summary>Answer</summary>

It is eager — the constant is built during class initialisation, so any I/O in the constructor
happens on the first touch of the enum, including an incidental `values()` call. It cannot take
constructor arguments that are not compile-time constants, so a `Clock`, a `DataSource` or a
configured cap has to be looked up from inside the constant, which is service location. And it is
awkward to substitute in a test: there is one global instance that accumulates state across test
methods, making tests order-dependent. When laziness matters, use the static holder idiom; when
dependencies matter, use a plain class and let the container or the caller own the single
instance — constructor injection, including [`Clock` injection](04b-deep-copy-and-clock-injection.md), is the answer to
the third.

</details>

**Q4.** Two class loaders each define `idem.IdempotencyRegistry`. Is that a flaw in the enum singleton, and what does the resulting `ClassCastException` message tell you?

<details><summary>Answer</summary>

Not a flaw in `enum`. A runtime type's identity is the pair (defining loader, binary name), so
two loaders each defining the same binary name produce two unrelated types, each with its own
`<clinit>`, its own `$VALUES` array and its own constants. Every static-field-based singleton
duplicates identically, because the static field is per-`Class`. The exception message spells the
diagnosis out: `class idem.IdempotencyRegistry cannot be cast to class idem.IdempotencyRegistry`
followed by the two loader names — identical names, different loaders. The fix is in the
deployment (one loader owns the type) or in moving the state out of static memory into a shared
store with a real uniqueness constraint.

</details>

**Q5.** `Enum.clone()` is `protected final` and throws. Why both modifiers, and why is `Enum.finalize()` also `final`?

<details><summary>Answer</summary>

`protected` keeps it out of the public API — no outside caller can invoke `clone()` on a constant
through a normal reference. `final` is what makes the guarantee structural: without it a subclass
could override `clone()` and return anything, including `this`, and the "enums are never cloned"
invariant would depend on nobody choosing to. Attempting the override is a compile error,
`clone() in BonusGrantRegistry cannot override clone() in Enum / overridden method is final`,
even for the benign `return this` version. `Enum.finalize()` is `final` and empty for the same
reason: an overridable finalizer is a resurrection hook, and a constant that could be resurrected
after collection would break the single-instance guarantee from the other end.

</details>

## Open questions

- none

---

**Leaves covered:** 4.5.5 (1 leaf)
**Leaves deferred:** none — leaf 4.5.7, the section-wide §4.5 diff table, is order 14, [03b-enum-values-cache-and-diff.md](03b-enum-values-cache-and-diff.md)
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 684
