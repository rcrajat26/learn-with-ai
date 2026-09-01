# 03 Java Core — Reflection: `Class` objects, names and member lookup — INTERMEDIATE (§2.12, 2.12.1–2.12.3)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The null-object pattern, annotations and diagnosis](../null-discipline/02b-null-object-annotations-and-diagnosis.md) · Next: [Access, cost and method handles](02a-access-cost-and-method-handles.md)

This file owns `Class` objects, the four naming methods, and member lookup; `02a-access-cost-and-method-handles.md` owns `setAccessible`, strong encapsulation, invocation cost and `MethodHandle`/`VarHandle`; `02b-proxies-frameworks-and-generics.md` owns dynamic proxies, where reflection appears in your stack, and what survives erasure; `02c-final-fields-and-security-surface.md` owns reflective `final`-field writes and the security surface. The question this file answers, in bold: **what is a `Class` object, and why does the same type have four different names and two different member-lookup families?**

## 1. `Class` objects: `X.class`, `obj.getClass()`, `Class.forName`, and array/primitive class objects (2.12.1)

Picture the JVM's class area as a table keyed by `(binary name, defining class loader)`. Every row holds one loaded type's metadata — its constant pool, its field and method descriptors, its superclass pointer — and the JVM hands you exactly one Java object as a handle onto that row: a `Class` instance. `Class` has no public constructor. You cannot build one; the class-loading machinery is the only thing that ever creates one, at the moment a type is loaded. A `Class` object is not a description of `Movement` — as far as the running JVM is concerned, it **is** `Movement`, in the sense that every `instanceof` check, every `invokevirtual` dispatch, and every array-store check ultimately consults that row.

### Why it exists

Reflection needs a live handle onto "the type", not a string, because a string can be misspelled, can name a type that failed to load, and carries no identity. `Class` gives every reflective operation — field lookup, method lookup, construction — a single typed root to hang off, and it doubles as the identity token the JVM itself uses for `instanceof`, casts and array covariance checks.

### How it works

The identity consequence is the load-bearing fact: because a `Class` object is keyed by `(name, loader)`, two `Class` objects for source-identical `Movement` classes loaded by two different class loaders are **not** `==`, are not assignable to each other, and produce the "cannot cast `Movement` to `Movement`" `ClassCastException` that confuses everyone the first time they see it in an application-server or plugin environment. `../classes-and-initialization/03b-internals-class-loaders-and-identity.md` owns that mechanism in full — this file only needs the consequence: never assume same-named types are the same type.

| Form | Compile-time or runtime | Triggers initialization? | Fails how | When to use |
|---|---|---|---|---|
| `Movement.class` | Compile-time checked class literal, no string | **No** | Compile error if the type does not exist | You know the type at compile time |
| `obj.getClass()` | Runtime — the object's actual runtime class | N/A (already initialized to construct `obj`) | Never, given a non-null `obj` | You need the dynamic type, e.g. logging which `Verdict` subtype decided a case |
| `Class.forName(String)` | Runtime, by binary name | **Yes** | `ClassNotFoundException` | Loading a class by name where a side effect (e.g. a JDBC driver registering itself) must run |
| `Class.forName(String, boolean initialize, ClassLoader)` | Runtime, by binary name, explicit loader | Only if `initialize` is `true` | `ClassNotFoundException` | Scanning many classes without running their static initializers |
| `loader.loadClass(String)` | Runtime, by binary name | **No** — loads and links only | `ClassNotFoundException` | Component/plugin scanning where you must not execute arbitrary class-init code |

`obj.getClass()` deserves one flag here and a deferral: for a proxied object — a Spring `@Transactional` bean, a JDK dynamic proxy — `getClass()` returns the **proxy's** class, not the class you wrote. `02b-proxies-frameworks-and-generics.md` owns that in full.

The initialization column is not decorative — it is the entire reason both `forName` overloads and `loadClass` exist, and the measured evidence settles the ambiguity. Three probe classes each print a line from a static initializer:

| Call | Did the static initializer run? |
|---|---|
| `Class.forName("Probe")` | **yes** — printed `Probe <clinit> ran` |
| `loader.loadClass("Probe2")` | **no** |
| `Class.forName("Probe3", false, loader)` | **no** |

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64. The one-argument `Class.forName(String)` is specified to load, link, **and initialize**; the three-argument form takes an explicit `initialize` flag; `ClassLoader.loadClass` only loads and links, never initializes. The practical split: a JDBC driver that registers itself via a static block only works when loaded through the one-argument `forName` — that is precisely why `Class.forName("com.example.Driver")` is the idiom you see in old code, not `loadClass`. A framework enumerating thousands of classpath entries to find annotated types uses `loadClass` or `forName(name, false, loader)` specifically so scanning a jar does not run arbitrary class-init side effects for classes it never actually uses. `../classes-and-initialization/01d-class-initialization-triggers.md` enumerates every trigger; `../classes-and-initialization/03-internals-class-loading-and-init.md` owns load/link/init as a state machine — do not re-derive either here.

Array and primitive class objects are the other place `Class.forName` surprises people. `int.class` exists and is `==` to `Integer.TYPE`, but `Class.forName("int")` measured throws `ClassNotFoundException` — there is no `.class` file for a primitive to load, so the JVM synthesizes the nine primitive `Class` objects (`boolean.class` through `void.class`) directly, and `forName` can only resolve names that name a loadable class file. `Movement[].class` works as a literal. `Class.forName("[LVer9$Movement;")` and `Class.forName("[Ljava.lang.String;")` both work as strings — the latter measured to return `class [Ljava.lang.String;`. The asymmetry to hold in your head: the array descriptor `forName` accepts uses the JVM's internal `[L<binary name>;` grammar with the class's **binary name** inside it (dots inside the binary name, exactly as `getName()` prints it), never the source array syntax `String[]` — `Class.forName("String[]")` throws. Concept 2.12.2 works the character-counting arithmetic of that descriptor in full. `Array.newInstance(Class<?> componentType, int length)` is the only way to build an array whose component type is only known at runtime — you cannot write `new T[n]` for a type parameter `T`, because erasure removes it, and `Array.newInstance` is the reflective escape hatch (`../generics/01a-erasure-and-its-consequences.md` owns why). `Class.arrayType()` and `Class.componentType()` — both added in Java 12 — are the modern accessors for moving between a type and its array form and back without string surgery.

Java 21 adds two reflective queries worth knowing cold. `isRecord()` and `getRecordComponents()` — `getRecordComponents` became final API with records in Java 16 — let you enumerate a record's components without a hand-maintained registry: measured, `Money.class.isRecord()` returns `true` and `Money.class.getRecordComponents()` returns `[java.math.BigDecimal amount, java.lang.String currency]`. `isSealed()` and `getPermittedSubclasses()` — final with sealed classes in Java 17 — let you enumerate a sealed hierarchy's members at runtime: on the measured harness, `Verdict.class.isSealed()` returns `true` and `Verdict.class.getPermittedSubclasses()` returns `[class Ver9$DocumentVerdict, class Ver9$ScreeningVerdict]`. `../records-and-sealed/01a-object-methods-sealed-and-fit.md` owns records' generated members and sealed exhaustiveness in full. The practical value: before Java 17, a polymorphic `Verdict` deserializer needed either a hand-written registry of `DocumentVerdict`/`ScreeningVerdict`/`ReviewVerdict`/`WealthVerdict` or a classpath scan; now `getPermittedSubclasses()` gives the exhaustive member list directly off the sealed interface's `Class` object, with the compiler itself guaranteeing the list is complete.

```java
public final class LedgerEntryComponentReader {

    public List<String> describeComponents(Class<?> ledgerValueType) {
        if (!ledgerValueType.isRecord()) {
            return List.of(ledgerValueType.getSimpleName() + " is not a record");
        }
        RecordComponent[] components = ledgerValueType.getRecordComponents();
        List<String> lines = new ArrayList<>(components.length);
        for (RecordComponent component : components) {
            lines.add(component.getName() + " : " + component.getType().getSimpleName());
        }
        return lines;
    }

    public boolean isCoveredBySealedHierarchy(Class<?> verdictRoot, Class<?> candidate) {
        if (!verdictRoot.isSealed()) {
            throw new IllegalArgumentException(verdictRoot + " is not sealed");
        }
        for (Class<?> permitted : verdictRoot.getPermittedSubclasses()) {
            if (permitted.equals(candidate)) {
                return true;
            }
        }
        return false;
    }
}
```

**Gotcha:** `Class.forName(String)` initializing and `loadClass` not initializing is the exact reason a framework that switches from one to the other silently changes behaviour — a static block that used to register something with a global registry stops running, and the failure shows up far downstream as "why is my handler not registered", not at the call site.

> A `Class` object is the JVM's runtime identity for a loaded type — one per `(name, loader)` pair, synthesized or loaded by the class-loading machinery, never constructed by user code.

## 2. `getName` vs `getSimpleName` vs `getCanonicalName` vs `getTypeName` — the four different answers (2.12.2) `[TRAP]` `[NUM]`

Picture four different audiences asking "what is this type called?" — the JVM's class file, the language grammar for source, a compact diagnostic label, and a generics-aware signature printer — and each audience gets served by its own method, because no single string satisfies all four. There are, in fact, three distinct name systems underneath a Java type, and the four methods are views onto them: the JVM's **binary name** (`Ver9$Movement`), the language's **canonical name** (`Ver9.Movement` — the dotted form you would write in an `import`), and a **simple** human label (`Movement`) with no qualification at all. `getTypeName()` is the odd one out: it exists to describe generics and arrays the way you would write them in a signature, and for non-generic, non-array types it happens to equal `getName()`.

### Why it exists

`getName()` answers "what does the JVM call this" — it is the string baked into `invokevirtual`, `checkcast` and every other bytecode instruction that names a type, and it is what `Class.forName` accepts back. `getSimpleName()` answers "what would I write in a diagnostic" — a label for a log line or an error message, with no package or nesting noise. `getCanonicalName()` answers "what would I write in an `import`" — the fully dotted name a human would type in source to reference the type, which is why it is `null` whenever no such source-typeable name exists. `getTypeName()` answers "what would I write in a signature" — it exists to give arrays and, via subclasses on `ParameterizedType`, generic types a readable form.

### How it works

**D-087** — `getX` versus `getDeclaredX`, and the four naming methods. (block two: the four naming methods)

Harness types declared inside a top-level class `Ver9`, measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

| Class | `getName()` | `getSimpleName()` | `getCanonicalName()` | `getTypeName()` |
|---|---|---|---|---|
| `Movement` | `Ver9$Movement` | `Movement` | `Ver9.Movement` | `Ver9$Movement` |
| `Movement.Inner` (inner) | `Ver9$Movement$Inner` | `Inner` | `Ver9.Movement.Inner` | `Ver9$Movement$Inner` |
| `Movement.Nested` (static nested) | `Ver9$Movement$Nested` | `Nested` | `Ver9.Movement.Nested` | `Ver9$Movement$Nested` |
| `Movement[]` | `[LVer9$Movement;` | `Movement[]` | `Ver9.Movement[]` | `Ver9$Movement[]` |
| `int[][]` | `[[I` | `int[][]` | `int[][]` | `int[][]` |
| `int` | `int` | `int` | `int` | `int` |
| anonymous class | `Ver9$1` | **empty string** | **`null`** | `Ver9$1` |
| local class `LocalRun` | `Ver9$1LocalRun` | `LocalRun` | **`null`** | `Ver9$1LocalRun` |
| a lambda | `Ver9$$Lambda/0x00000070010015d8` | `Ver9$$Lambda/0x00000070010015d8` | **`null`** | `Ver9$$Lambda/0x00000070010015d8` |

Now the `[NUM]` arithmetic behind the array rows. Every reference or array type descriptor the JVM uses is built from a one-character primitive alphabet plus one bracket per array dimension plus, for a reference type, an `L` prefix and a `;` suffix wrapped around the binary name:

| Descriptor | Primitive | Descriptor | Primitive |
|---|---|---|---|
| `Z` | boolean | `I` | int |
| `B` | byte | `J` | long |
| `C` | char | `F` | float |
| `S` | short | `D` | double |
| — | — | `V` | void (return position only) |

`B` was already taken by `byte`, so `long` had to take a letter no other primitive wanted, and the JVM designers picked `J` — the closest remaining letter to "long" with no collision. Likewise `boolean` could not take `B`, so it took `Z` (from the last letter, avoiding `B` and the vowel-leading collisions with `byte`/`bool`-adjacent letters already in use). Count the characters rather than trust the shape: `int[][]` has descriptor `[[I` — that is **3 characters**: one `[` for the outer dimension, one `[` for the inner dimension, and the single-character primitive descriptor `I` for `int`. `Movement[]` has descriptor `[LVer9$Movement;` — that is `[` (1 array dimension) + `L` (reference-type marker) + `Ver9$Movement` (the 13-character binary name) + `;` (terminator), 16 characters total, and the reason `[Ljava.lang.String;` measured out correctly is the same grammar with `java.lang.String`'s binary name in the middle.

Three facts in that matrix are the whole trap, and each earns its own line because each has bitten real logging and serialization code:

`getSimpleName()` on an anonymous class returns the **empty string**, not `null` — measured. `log.warn("handler " + h.getClass().getSimpleName() + " failed")` against an anonymous `InvocationHandler` therefore logs `handler  failed`, with a silent double space and no type information at all — no exception, no hint, just a diagnostic hole exactly when you need the diagnostic most.

`getCanonicalName()` returns **`null`** for anonymous, local, and lambda classes — three separate measured rows, and the reason is principled rather than an oversight: a canonical name is by definition a name you could type in source to reference the type, and none of the three has one. Code written as `type.getCanonicalName().startsWith("com.quizstakes")` NPEs the first time it runs against a `Verdict` implemented as a lambda-backed functional adapter or an anonymous listener.

A **lambda's class name embeds a hex address**: `Ver9$$Lambda/0x00000070010015d8` measured for one lambda, `Ver9$$Lambda/0x000000700115abf0` measured for a different lambda in the same class in the same run. That name is neither stable across runs nor unique per source lambda site in any way you can rely on. Consequence: never use a class name as a cache key, a metric tag, a log correlation key, or a serialized discriminator anywhere a lambda or anonymous class can reach that code path — `../serialization/02b-externalizable-records-and-lambdas.md` owns why lambda serialization itself is fragile for the same underlying reason, and guide 20 (Observability) is where an unbounded metric-tag cardinality from lambda class names actually pages someone.

**Pitfall:** treating `getCanonicalName()` as "the same as `getName()` but nicer" will crash the first time a `Verdict` decision path is implemented with a lambda or an anonymous class, because `getCanonicalName()` silently returns `null` there while `getName()` never does.

```java
public final class VerdictDiagnosticName {

    public String bestEffortName(Object decidingComponent) {
        Class<?> type = decidingComponent.getClass();
        String canonical = type.getCanonicalName();
        if (canonical != null) {
            return canonical;
        }
        if (type.isArray()) {
            return type.getComponentType().getSimpleName() + "[]";
        }
        String simple = type.getSimpleName();
        return simple.isEmpty() ? type.getName() : simple;
    }
}
```

That helper is the recipe for logging which `Verdict` implementation produced an `AA-650 DOCUMENTS_REFERRED` decision: prefer `getCanonicalName()`, fall back to a synthesized array label, then to `getSimpleName()`, and only fall all the way back to the raw `getName()` — with its embedded hex address on a lambda — as the last resort, never the first choice.

**Interview:** "What does `getSimpleName()` return for an anonymous class?" — the empty string, and `getCanonicalName()` returns `null` on the same class; both bite in logging code that assumes a non-empty, non-null label always exists.

> `getName()`, `getSimpleName()`, `getCanonicalName()` and `getTypeName()` answer four different questions about the same type, and only `getName()` is guaranteed non-null and non-empty for every `Class` object.

## 3. Field/Method/Constructor lookup: `getX` vs `getDeclaredX` (2.12.3) `[TRAP]`

Picture the member space of a class sliced along two independent axes at once — access level, and whether a member is inherited — and the two lookup families each answer only one corner of that grid. `getX` means **public, declared or inherited**. `getDeclaredX` means **all access levels, declared on this class only**. Neither is a superset of the other, and there is no single call that returns "everything the class has, at every access level, including what it inherited." That is the entire concept; everything below is evidence for it.

### Why it exists

The JVM's access-control model and its inheritance model are genuinely orthogonal, and the reflection API mirrors that rather than flattening it: `getX` exists because most callers — serialization frameworks walking a public contract, an IDE's autocomplete — want "the API surface, wherever it came from." `getDeclaredX` exists because framework code that must bypass access control — an ORM setting a private field, a DI container calling a private constructor — needs "everything on this exact class, regardless of who is allowed to call it," before it ever reaches for `setAccessible`.

### How it works

**D-087** — `getX` versus `getDeclaredX`, and the four naming methods. (block one: `getX` vs `getDeclaredX`)

| Call | Includes private | Includes inherited | Includes synthetic/bridge | Requires `setAccessible` to use |
|---|---|---|---|---|
| `getFields()` | No | Yes (public only) | No | No |
| `getDeclaredFields()` | Yes | No | Yes | Only to read/write a non-public one |
| `getMethods()` | No | Yes (public only) | Rarely (bridges can be public) | No |
| `getDeclaredMethods()` | Yes | No | Yes | Only to invoke a non-public one |
| `getConstructors()` | No | N/A — never inherited | No | No |
| `getDeclaredConstructors()` | Yes | N/A — never inherited | Rarely | Only to invoke a non-public one |

Measured on `Movement` — public field `position`, private field `minor`, protected field `seq`, package-private field `pkg`; a public no-arg constructor and a private one-arg constructor; a public method `post()` and a private method `audit()`, on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

| Call | Measured result |
|---|---|
| `getFields()` | `[public java.lang.String Ver9$Movement.position]` — one entry |
| `getDeclaredFields()` | `[public java.lang.String Ver9$Movement.position, private long Ver9$Movement.minor, protected int Ver9$Movement.seq, java.lang.String Ver9$Movement.pkg]` — four entries |
| `getConstructors()` | count **1** |
| `getDeclaredConstructors()` | count **2** |
| `getMethods()` | count **10** — one declared public method plus `Object`'s public methods |
| `getDeclaredMethods()` | `[public void Ver9$Movement.post(), private void Ver9$Movement.audit()]` — two entries |
| `Movement.Inner.class.getDeclaredFields()` | `[int Ver9$Movement$Inner.x]` |

Every consequence below is derived from those numbers, not asserted on top of them.

`getFields()` returning **one** entry against `Movement`'s four declared fields proves it skips `protected` and package-private members declared on the class itself — it is not "declared plus inherited restricted to public", it is "public, wherever it comes from." The mental model "`getFields` is `getDeclaredFields` plus superclass fields" is simply wrong; a `protected` field on the class you are inspecting **directly** is invisible to `getFields()`.

`getMethods()` returning **10** against two declared methods on `Movement` is `Object`'s public methods (`equals`, `hashCode`, `toString`, `getClass`, `wait` × 3, `notify`, `notifyAll`) folded in as inherited members. Any `getMethods()` loop that treats `.length` as "how many methods does this class define" is off by however many public `Object` methods it silently absorbed — filter by `getDeclaringClass()` before drawing any conclusion about a type's own API.

`getConstructors()` returning **1** against `getDeclaredConstructors()`'s **2** isolates the one axis that actually matters for constructors: access, never inheritance, because constructors are never inherited in Java. A framework that must instantiate a type through a private constructor — a factory-guarded aggregate constructor, common across `Application`, `Account` and `Reservation` in this domain — has exactly one entry point: `getDeclaredConstructor(long.class)` followed by `setAccessible(true)`. `setAccessible` itself, and the `InaccessibleObjectException` a module boundary can throw instead of quietly succeeding, belongs to `02a-access-cost-and-method-handles.md` — this file only names the need.

To get "every member up the hierarchy", you must walk `getSuperclass()` yourself; no single call does it. The walk must also handle same-named fields at different levels — a subclass field **hides** a same-named superclass field rather than overriding it (`../inheritance-and-dispatch/01-basics.md` owns hiding), so a naive collection keyed by name silently drops one of two distinct `Field` objects that share a name at different declaring classes.

```java
public final class LedgerFieldWalker {

    public Map<String, Field> collectInstanceFields(Class<?> leaf) {
        Map<String, Field> byQualifiedName = new LinkedHashMap<>();
        for (Class<?> current = leaf; current != null; current = current.getSuperclass()) {
            for (Field field : current.getDeclaredFields()) {
                if (Modifier.isStatic(field.getModifiers()) || field.isSynthetic()) {
                    continue;
                }
                String key = current.getName() + "#" + field.getName();
                byQualifiedName.put(key, field);
            }
        }
        return byQualifiedName;
    }
}
```

Synthetic and bridge members ride along in every `getDeclaredX` result and are usually not what a mapper wants. The measured evidence on JDK 21 is a genuine version-sensitive trap: `javac` only emits the synthetic enclosing-instance field `this$0` when an inner class actually reads the enclosing instance. `Outer.UsesEnclosing.class.getDeclaredFields()` measured `[final VerA$Outer VerA$Outer$UsesEnclosing.this$0]`; `Outer.IgnoresEnclosing.class.getDeclaredFields()` measured `[int VerA$Outer$IgnoresEnclosing.x]` — **no `this$0` at all**, on the same JDK 21.0.7 build. Code that skips `this$0` by name assumes it is always present for every inner class; on JDK 21 it is not, so that filter is both necessary and insufficient. The honest filter is `Field.isSynthetic()` and `Method.isSynthetic()` / `Method.isBridge()`, never a name match on `this$0`. `../inheritance-and-dispatch/04-internals-nested-classes.md` owns the bytecode mechanics of `this$0` in full; `../generics/03a-internals-bridge-methods.md` owns bridge methods. Note also that an enum's synthetic `$VALUES` array and a record's generated accessor methods surface through these same calls, for the same reason — the compiler generated real bytecode members, and reflection cannot distinguish "the compiler wrote this" from "you wrote this" without the synthetic/bridge flags.

`getDeclaredFields()`'s ordering is unspecified — verbatim, from `java.base/java/lang/Class.java` in the JDK 21 `src.zip`:

```
The elements in the returned array are not sorted and are not in any
particular order.
```

That is worse than random, because it is *stable in practice* on HotSpot — every test passes, every manual check looks fine, and the code is still depending on undefined behaviour. A hand-rolled `LedgerEntry` CSV exporter that walks `getDeclaredFields()` and writes one column per field, with ledger retention at 7 years and roughly 19.8M entries written per day, produces a file whose column order is not part of any contract the JVM ever promised — a future `javac`, a future field addition, or a different JVM vendor can reorder it, and a file written today may not parse the same way a file written next year does, with no error at write time to warn anyone.

**Pitfall:** assuming `getFields()` is "everything declared plus everything inherited, minus private" will silently drop `protected` fields declared directly on the class under inspection — the measured one-entry result against four declared fields on `Movement` is the proof, not an anecdote.

Every one of `getFields`, `getDeclaredFields`, `getMethods`, `getDeclaredMethods` and both constructor calls allocates a **fresh array** on every invocation — `Class` hands back copies specifically so a caller cannot mutate its cached reflective metadata. Calling `getDeclaredFields()` inside a per-row `LedgerEntry` mapper is one array allocation per row, plus one `Field` object reference per declared field per row; at roughly 19.8M ledger entries written per day and four declared fields per entry that is on the order of 19.8M array allocations and close to 80M `Field` references churned daily for information that never changes after class load. The escape hatch every serialization and ORM framework actually uses: resolve reflective metadata **once** — at class-load time or on first use — into a small cached structure (an array, a `Map`, or, per `02a`, a `MethodHandle`), and never call back into `Class` on the row-processing hot path. Invocation-cost numbers for the reflective call itself, once resolved, belong to `02a-access-cost-and-method-handles.md`.

```java
public final class LedgerEntryMapper {

    private final List<Field> orderedFields;

    public LedgerEntryMapper(Class<?> ledgerEntryType) {
        Map<String, Field> collected = new LedgerFieldWalker().collectInstanceFields(ledgerEntryType);
        List<Field> resolved = new ArrayList<>(collected.values());
        resolved.sort(Comparator.comparing(field -> {
            LedgerColumn column = field.getAnnotation(LedgerColumn.class);
            return column != null ? column.order() : Integer.MAX_VALUE;
        }));
        for (Field field : resolved) {
            field.setAccessible(true);
        }
        this.orderedFields = List.copyOf(resolved);
    }

    public Object[] toRow(Object ledgerEntry) throws IllegalAccessException {
        Object[] row = new Object[orderedFields.size()];
        for (int i = 0; i < orderedFields.size(); i++) {
            row[i] = orderedFields.get(i).get(ledgerEntry);
        }
        return row;
    }
}
```

`LedgerEntryMapper` resolves and orders its `Field` handles exactly once, in the constructor, by an explicit `@LedgerColumn(order = N)` annotation rather than by reflective declaration order — so `toRow` never calls back into `Class` and the exported column order is a real, versioned contract instead of an accident of HotSpot's current layout.

**Gotcha:** No gotcha beyond what is already stated above: the rule that `getX` and `getDeclaredX` slice on two independent axes has no further surprising edge once you stop assuming either family is a superset of the other.

> `getX` returns public members, declared or inherited; `getDeclaredX` returns all members declared on the exact class, at every access level — there is no single call that returns both at once.

---

## Pitfalls

### `getSimpleName()` returns `null` for an anonymous or local class, the same as `getCanonicalName()` does

**Wrong**

```java
Runnable handler = new Runnable() {
    @Override public void run() { }
};
String label = handler.getClass().getSimpleName();
System.out.println("handler [" + label + "] failed");
// prints: handler [] failed  — no exception, no NullPointerException, just silence
```

**Right**

```java
Runnable handler = new Runnable() {
    @Override public void run() { }
};
Class<?> type = handler.getClass();
String label = !type.getSimpleName().isEmpty() ? type.getSimpleName() : type.getName();
System.out.println("handler [" + label + "] failed");
// prints: handler [Ver9$1] failed
```

**Why people believe it:** `getCanonicalName()` really does return `null` for the same class, so it feels consistent for `getSimpleName()` to do the same thing — but the two methods answer different questions (a diagnostic label always exists; a source-typeable canonical name does not), and only one of them returns `null`.

### `getCanonicalName()` is just a nicer-formatted `getName()` and is always non-null

**Wrong**

```java
Verdict decision = documentVerificationService.decide(applicationId);
if (decision.getClass().getCanonicalName().startsWith("com.quizstakes.verdict")) {
    auditLog.record(decision);
}
// throws NullPointerException the day `decision` is produced by a lambda-backed adapter
```

**Right**

```java
Verdict decision = documentVerificationService.decide(applicationId);
String canonical = decision.getClass().getCanonicalName();
if (canonical != null && canonical.startsWith("com.quizstakes.verdict")) {
    auditLog.record(decision);
}
```

**Why people believe it:** `getName()` never returns `null`, so it is easy to assume its "nicer" sibling shares that guarantee — but `getCanonicalName()` is defined in terms of source-level nameability, and anonymous, local and lambda classes measurably have none.

### `getFields()` is "`getDeclaredFields()` restricted to this class, plus inherited fields"

**Wrong**

```java
class Movement {
    public String position;
    protected int seq;
}
Field[] fields = Movement.class.getFields();
System.out.println(fields.length);
// prints 1 — the protected `seq` field is silently absent, not filtered by a bug
```

**Right**

```java
class Movement {
    public String position;
    protected int seq;
}
Field[] declared = Movement.class.getDeclaredFields();
System.out.println(declared.length);
// prints 2 — both fields, because getDeclaredFields ignores access level entirely
```

**Why people believe it:** `getDeclaredFields()` clearly ignores inheritance, so it seems natural that `getFields()` would just add inherited members on top of the same set — but `getFields()` filters by **public access**, not by "declared here", and a `protected` field declared directly on the class you are inspecting fails that filter too.

### `getDeclaredFields()` returns fields in the order they were written in the source file

**Wrong**

```java
public final class LedgerEntryCsvExporter {
    public String header(Class<?> entryType) {
        StringBuilder header = new StringBuilder();
        for (Field field : entryType.getDeclaredFields()) {
            header.append(field.getName()).append(',');
        }
        return header.toString();
    }
}
// stable across every test run on this JVM build — and unspecified by the platform,
// so a future javac, JDK vendor, or field addition can reorder every existing export
```

**Right**

```java
public final class LedgerEntryCsvExporter {
    public String header(Class<?> entryType) {
        List<Field> ordered = Arrays.stream(entryType.getDeclaredFields())
            .filter(f -> f.isAnnotationPresent(LedgerColumn.class))
            .sorted(Comparator.comparingInt(f -> f.getAnnotation(LedgerColumn.class).order()))
            .toList();
        StringBuilder header = new StringBuilder();
        for (Field field : ordered) {
            header.append(field.getName()).append(',');
        }
        return header.toString();
    }
}
```

**Why people believe it:** the order is in fact stable across every observed run on HotSpot, and it usually matches source order closely enough to look intentional — but the Javadoc states plainly that "the elements in the returned array are not sorted and are not in any particular order," and stable-by-accident is not the same guarantee as contractual.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Class` construction | No public constructor; only the JVM's class-loading machinery creates one |
| Identity key | `(binary name, defining class loader)` — same name, different loader ⇒ not `==`, not assignable |
| `X.class` | Compile-time literal, never triggers initialization |
| `obj.getClass()` | Runtime type; returns the proxy's class for a dynamic/CGLIB proxy |
| `Class.forName(String)` | Loads, links, **and initializes** |
| `Class.forName(String, false, loader)` | Loads and links only |
| `ClassLoader.loadClass(String)` | Loads and links only, never initializes |
| `Class.forName("int")` | `ClassNotFoundException` — primitives are synthesized, not loaded |
| Primitive descriptors | `Z` boolean · `B` byte · `C` char · `S` short · `I` int · `J` long · `F` float · `D` double · `V` void |
| `int[][].class.getName()` | `[[I` — 3 characters: 2 dimension brackets + 1 descriptor |
| `getSimpleName()` on anonymous class | Empty string, never `null` |
| `getCanonicalName()` on anonymous/local/lambda | `null` — no source-typeable name exists |
| Lambda class name | Embeds a hex address; differs per run and per lambda |
| `getFields()` | Public members, declared or inherited |
| `getDeclaredFields()` | All members, declared here only, includes synthetics |
| `getMethods()` on a near-empty class | Still returns ~10+ — `Object`'s public methods count |
| `getConstructors()` vs `getDeclaredConstructors()` | Constructors are never inherited — only access level differs |
| `this$0` on JDK 21 | Emitted only if the inner class actually reads the enclosing instance |
| `getDeclaredFields()` ordering | Unspecified by Javadoc; stable-by-accident on HotSpot |
| `isRecord()` / `getRecordComponents()` | Final API since Java 16 |
| `isSealed()` / `getPermittedSubclasses()` | Final API since Java 17 |
| Reflective call cost | Every `getX`/`getDeclaredX` call allocates a fresh array — resolve once, cache, never repeat per row |

## Self-test

**Q1.** Why does `Class` have no public constructor, and what actually creates a `Class` object?

<details><summary>Answer</summary>

Only the JVM's class-loading machinery creates `Class` objects — one per `(binary name, defining class loader)` pair, at load time for a normal class, or synthesized directly by the JVM for the nine primitive types. A public constructor would let user code fabricate a `Class` object disconnected from any actually loaded type, which would break every guarantee reflection depends on: that a `Class` object corresponds to real, loaded bytecode with a real constant pool and real member metadata.

</details>

**Q2.** Two classes named `Movement` are loaded by two different class loaders. Are their `Class` objects equal, and what breaks if code assumes they are?

<details><summary>Answer</summary>

No — they are two distinct `Class` objects, `!=` and not assignable to each other, because `Class` identity is keyed by `(name, loader)`, not by name alone. Code that assumes same-named classes are interchangeable — passing an object across a plugin or application-server boundary and casting it to the "same" type loaded by a different loader — throws a `ClassCastException` whose message reads as if the types were identical, because they print the same simple name even though the JVM treats them as unrelated types.

</details>

**Q3.** What is the difference in behaviour between `Class.forName("Driver")` and `classLoader.loadClass("Driver")`, and which one a legacy JDBC driver depends on?

<details><summary>Answer</summary>

`Class.forName(String)` loads, links, and **initializes** the class — its static initializer runs. `loadClass` only loads and links; it never initializes. A legacy JDBC driver that registers itself with `DriverManager` from a static block only actually registers when loaded via the one-argument `forName`; loading the same class name via `loadClass` leaves the static block unrun and the driver unregistered, with no exception raised anywhere.

</details>

**Q4.** What does `getName()` return for `int[][]`, and how many characters is it, exactly?

<details><summary>Answer</summary>

`[[I` — three characters. The array descriptor grammar is one `[` per array dimension followed by the component type's descriptor; `int[][]` has two dimensions (two `[` characters) followed by the single-character primitive descriptor `I` for `int`, giving `[[I`.

</details>

**Q5.** Why does `long` use the descriptor `J` instead of `L`, and why does `boolean` use `Z` instead of `B`?

<details><summary>Answer</summary>

`L` is already reserved as the reference-type marker (`L<binary name>;`), and `B` is already taken by `byte`, so both `long` and `boolean` needed distinct, unclaimed letters. `long` was assigned `J`; `boolean` was assigned `Z`. Neither is an arbitrary mnemonic guess — they are simply the letters left over once the more "obvious" letters were already claimed by other primitives or by the reference-type marker.

</details>

**Q6.** What does `getSimpleName()` return for an anonymous class, and what does `getCanonicalName()` return for the same class? Why are these two answers different from each other?

<details><summary>Answer</summary>

`getSimpleName()` returns the empty string. `getCanonicalName()` returns `null`. They differ because they answer different questions: `getSimpleName()` always returns *some* label (even if it is empty, because an anonymous class has no name token to strip), while `getCanonicalName()` is defined as the name you could write in source to reference the type — and there is no such name for a type with no declared name, so the method returns `null` rather than an empty string to signal "does not exist" rather than "exists but is blank".

</details>

**Q7.** A class `Movement` declares one `public`, one `private`, one `protected`, and one package-private field. What does `getFields()` return, and what does `getDeclaredFields()` return?

<details><summary>Answer</summary>

`getFields()` returns only the `public` field — one entry — because it filters by public access regardless of where the member is declared, including on the class itself. `getDeclaredFields()` returns all four fields regardless of access level, because it filters only by "declared on this exact class," ignoring access entirely. The two calls are not nested subsets of each other; they slice the same field set along two independent axes.

</details>

**Q8.** Why does `getMethods()` on a class that declares only two methods return more than two entries?

<details><summary>Answer</summary>

`getMethods()` returns public members that are declared **or inherited** — every class implicitly extends `Object`, and `Object`'s public methods (`equals`, `hashCode`, `toString`, `getClass`, the `wait` overloads, `notify`, `notifyAll`) are inherited public members of every class. On the measured harness, a class with two declared methods returned ten total from `getMethods()`, because the other eight are `Object`'s.

</details>

**Q9.** On JDK 21, does every non-static inner class get a synthetic `this$0` field? What did the measured evidence show?

<details><summary>Answer</summary>

No. On JDK 21.0.7, `javac` only emits the synthetic `this$0` enclosing-instance field when the inner class actually reads a member of the enclosing instance. An inner class measured to read an enclosing field (`UsesEnclosing`) had `this$0` in its `getDeclaredFields()` result; a sibling inner class measured to never touch the enclosing instance (`IgnoresEnclosing`) had no `this$0` field at all. Code that assumes `this$0` is always present for every inner class, and filters it out by name, is filtering out a field that may not exist.

</details>

**Q10.** Why is caching resolved `Field` objects at construction time, rather than calling `getDeclaredFields()` per row, the recommended pattern for a high-volume mapper?

<details><summary>Answer</summary>

Every call to `getFields`, `getDeclaredFields`, `getMethods`, `getDeclaredMethods`, or either constructor-listing method allocates a fresh array (and, for fields and methods, the underlying `Field`/`Method` objects are effectively re-materialized), because `Class` deliberately hands back copies rather than its internal cached arrays, so callers cannot mutate reflective metadata. Calling one of these inside a per-row hot path at high volume — tens of millions of rows a day in a ledger mapper, for example — multiplies that allocation cost by the row count for information that never changes after class load. Resolving the member handles once, in a constructor, and reusing them removes the allocation from the hot path entirely.

</details>

## Open questions

None.

---

**Leaves covered:** 2.12.1–2.12.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-087
**Target version:** Java 21 LTS
**Lines:** 500
