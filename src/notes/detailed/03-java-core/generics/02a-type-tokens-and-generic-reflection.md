# 03 Java Core — Type tokens and recovering generic types at runtime — INTERMEDIATE (§2.7, 2.7.5–2.7.7)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Generics in anger](02-in-anger.md) · Next: [Generic arrays and self-types](02b-generic-arrays-and-self-types.md)

Erasure (`01a-erasure-and-its-consequences.md`) deletes every type argument from a `List<Money>` by the time it becomes bytecode — but Jackson still builds a `List<Money>`, not a `List<LinkedHashMap>`, when it deserialises one. This file is the answer: how a `Class<T>` object works as a runtime witness for an erased type (2.7.5), how an anonymous subclass smuggles a type argument past erasure through its `extends` clause (2.7.6), and exactly which reflective calls can read that smuggled argument back out, and which cannot (2.7.7). It hands off erasure itself, reification, and the `Signature` attribute's byte layout to `01a-erasure-and-its-consequences.md` and `03-internals-erasure.md`; the typesafe heterogeneous container build to `01d-recursive-bounds-and-heterogeneous-containers.md`; and the super-type-token mechanism at bytecode depth, with a `[BUILD]`, to `03e-internals-why-erasure-and-super-type-tokens.md`.

## 1. `Class<T>` as a type token (2.7.5)

Picture a `Class<T>` object not as "metadata about a type" but as a **receipt**. Erasure burns every type argument off a generic signature before it becomes bytecode, so at runtime a `List<Money>` and a `List<LinkedHashMap>` are the identical `ArrayList` object with the identical `getClass()`. A `Class<T>` instance is the one thing the platform still hands you that names a *specific* type at *run time* — because `Class` objects are not erased away, they are loaded, one per type, and kept alive by the class loader for the process lifetime. Passing one around a generic API is passing a witness: "here, at runtime, is proof of what `T` was, because you asked me for it and erasure cannot delete an object I am holding."

### Why it exists

Before `Class<T>` was generic (pre-Java 5, `Class` was raw), a factory or repository that needed to create or check instances of an erased type parameter had no way to connect the compile-time `T` to anything at runtime — `T.class` does not compile, `new T()` does not compile, and `(T) someObject` compiles but checks nothing. The generic `Class<T>` (JDK 5, alongside generics themselves) gives such a method exactly one legitimate bridge: the caller supplies the `Class<T>` object explicitly, and the method uses it to do everything erasure otherwise forbids — construct, cast, check.

### The mechanism

A generic method or constructor takes a `Class<T>` parameter and stores or uses it to stand in for `T` at the three points erasure would otherwise block: construction (`type.getDeclaredConstructor().newInstance()`), checked casting (`type.cast(obj)`), and membership testing (`type.isInstance(obj)`). None of this is compiler magic — `Class<T>` is an ordinary generic type, and the compiler links the type parameter `T` used in the class's own generic signature to the same `T` bound on the `Class<T>` parameter, so a `Class<CashEntry>` can only be assigned where a `CashEntry` witness is expected.

```java
sealed interface LedgerEntry permits CashEntry, BonusEntry {
    java.util.UUID id();
    Money amount();
}
record CashEntry(java.util.UUID id, Money amount) implements LedgerEntry {}
record BonusEntry(java.util.UUID id, Money amount) implements LedgerEntry {}

// The "pass the class so the method can create or cast" idiom: EntryStore has
// no compile-time knowledge of which LedgerEntry subtype it holds, so callers
// hand over the witness at the call site.
final class EntryStore<T extends LedgerEntry> {
    private final Class<T> entryType;
    private final Map<UUID, T> byId = new HashMap<>();

    EntryStore(Class<T> entryType) {
        this.entryType = entryType;
    }

    void put(T entry) {
        byId.put(entry.id(), entry);
    }

    // The witness lets the method assert "whatever is at this id, it had
    // better be a T" and throw HERE if it is not - Class.cast, not (T) x.
    T getChecked(UUID id) {
        Object raw = byId.get(id);
        return entryType.cast(raw);
    }

    Class<T> entryType() {
        return entryType;
    }
}
```

Run on JDK 21.0.7 with `EntryStore<CashEntry> cashStore = new EntryStore<>(CashEntry.class);`, storing and retrieving a `CashEntry`, this prints `entryType=class CashEntry` — the receipt survived the round trip through an erased field.

No diagram: the manifest assigns this section none; the code above is the picture.

**`Class.cast(Object)` versus `(T) x`.** `type.cast(x)` compiles to a real `instanceof`-and-throw inside `Class.cast`'s own body — it is ordinary, checked, working code, not a compiler trick. `(T) x` with an unbounded or object-bounded `T` erases to *nothing at all*: no `checkcast` bytecode is emitted at the cast expression itself, because by the time `javac` erases `T` there is nothing left to check against. The two failure modes this produces are not academic — they land in different files. First, the boundary case: a raw, deliberately erased store (a `Map<String, Object>`, the shape a deserialiser or legacy cache hands you) holds a `BonusEntry` under a key the caller expects to be a `CashEntry`.

```java
final class RawLedger {
    private final Map<String, Object> slots = new HashMap<>();

    void putRaw(String key, Object value) {
        slots.put(key, value);
    }

    <T extends LedgerEntry> T readChecked(String key, Class<T> type) {
        Object raw = slots.get(key);
        return type.cast(raw);
    }
}

public class BoundaryCast {
    public static void main(String[] args) {
        RawLedger ledger = new RawLedger();
        Money stake = new Money(new BigDecimal("4.20"), Currency.getInstance("GBP"));
        ledger.putRaw("settlement-42", new BonusEntry(UUID.randomUUID(), stake));
        CashEntry cash = ledger.readChecked("settlement-42", CashEntry.class);
        System.out.println("unreachable: " + cash);
    }
}
```

Compiled and run on JDK 21.0.7, this throws immediately, naming the mismatch at the exact line of the cast:

```
Exception in thread "main" java.lang.ClassCastException: Cannot cast BonusEntry to CashEntry
	at java.base/java.lang.Class.cast(Class.java:4067)
	at RawLedger.readChecked(BoundaryCast.java:25)
	at BoundaryCast.main(BoundaryCast.java:34)
```

Now the unchecked-cast side, done the way it actually happens in a codebase: not a local `(T) x` in the method that produced the bad value, but heap pollution through a raw type at one call site, read back through a parameterised type at a completely different one.

```java
// A batching helper compiled long before CashEntry and BonusEntry diverged,
// still accepting a raw List so it can service either. This is the failure
// mode an unchecked (T) cast produces at scale: the bad element goes in over
// HERE, far from where it eventually gets read back out.
final class LegacyBatcher {
    @SuppressWarnings("unchecked")
    static void stuffInBonusByMistake(List cashBatch, LedgerEntry entry) {
        // No compile-time link to CashEntry here - raw List erases it away.
        cashBatch.add(entry);
    }
}

public class DeferredCast {
    public static void main(String[] args) {
        List<CashEntry> cashBatch = new ArrayList<>();
        Money stake = new Money(new BigDecimal("4.20"), Currency.getInstance("GBP"));
        cashBatch.add(new CashEntry(UUID.randomUUID(), stake));

        // The pollution happens inside an unrelated helper class.
        LegacyBatcher.stuffInBonusByMistake(cashBatch, new BonusEntry(UUID.randomUUID(), stake));

        System.out.println("batch built, size=" + cashBatch.size());
        // The javac-inserted checkcast at THIS read site is where the
        // exception actually fires - one file, one method, zero lines away
        // from where the caller of stuffInBonusByMistake ever looked.
        for (CashEntry cash : cashBatch) {
            System.out.println("cash entry: " + cash);
        }
    }
}
```

Compiled with `-Xlint:all` (which reports the raw-type warning at the polluting call inside `stuffInBonusByMistake`, and nothing else — no warning at the read site) and run on JDK 21.0.7:

```
batch built, size=2
cash entry: CashEntry[id=ea9deeba-475a-4307-ade6-9ff3200a9a9b, amount=Money[amount=4.20, currency=GBP]]
Exception in thread "main" java.lang.ClassCastException: class BonusEntry cannot be cast to class CashEntry (BonusEntry and CashEntry are in unnamed module of loader 'app')
	at DeferredCast.main(DeferredCast.java:41)
```

The exception fires at `for (CashEntry cash : cashBatch)` — a `checkcast` the compiler inserted at every read of a `List<CashEntry>` element, because `List.get`'s erased return type is `Object` and the parameterised type promised `CashEntry`. `readChecked`'s failure and this one are the same JVM instruction, `checkcast`, in two different guises: one you write explicitly and can put exactly where you want it (`Class.cast`), one the compiler writes for you at every read site regardless of how far that is from where the bad value was written.

**`Class.asSubclass(Class<U>)`.** Its signature, from the JDK 21 `Class<T>` javadoc, is `<U> Class<? extends U> asSubclass(Class<U> clazz)`: it narrows a `Class<?>` — the kind of witness you get back from `Class.forName(String)`, which cannot know anything about your type hierarchy at compile time — to a `Class<? extends U>` you can actually use in a generic context. It throws `ClassCastException` if the receiver is not in fact a subtype of `clazz`. This is strictly better than casting the `Class` object itself with `(Class<? extends Verdict>) raw`, because that cast is unchecked (erased, silent, defers) exactly the way `(T) x` is above, while `asSubclass` performs a real `isAssignableFrom` check and throws at the call.

```java
sealed interface Verdict permits DocumentVerdict {
    String outcome();
}
record DocumentVerdict(String outcome, String reason) implements Verdict {}

// A config string names a Verdict subtype; Class.forName only promises a
// raw Class<?>, so asSubclass narrows it to a usable Class<? extends Verdict>
// - or throws right here, naming exactly what failed to relate.
static Class<? extends Verdict> resolveVerdictType(String className) throws ClassNotFoundException {
    Class<?> raw = Class.forName(className);
    return raw.asSubclass(Verdict.class);
}
```

Run on JDK 21.0.7, `resolveVerdictType("DocumentVerdict")` prints `resolved: class DocumentVerdict`; `resolveVerdictType("java.math.BigDecimal")` throws from inside `asSubclass` itself:

```
Exception in thread "main" java.lang.ClassCastException: class java.math.BigDecimal
	at java.base/java.lang.Class.asSubclass(Class.java:4102)
	at AsSubclassDemo2.main(AsSubclassDemo2.java:4)
```

Note the message shape: `Class.cast`'s `ClassCastException` names both classes ("cannot be cast to"); `Class.asSubclass`'s message on this JDK build is terser, printing only the class that failed the relation. Both are real, both are `ClassCastException`, and the point stands regardless of message wording — the failure happens at the narrowing call, not somewhere downstream.

The typesafe heterogeneous container (Joshua Bloch, *Effective Java*, Item 33: *Consider typesafe heterogeneous containers*) is the flagship consumer of this whole trio — a `Map<Class<?>, Object>` keyed by type token, where `put` uses the key's own generic bound to accept only a matching value and `get` uses `type.cast()` to hand it back typed. `01d-recursive-bounds-and-heterogeneous-containers.md` owns that pattern and ships the full build; the reflection surface you need to read it is exactly `cast`, `asSubclass`, and one fact worth sitting with: there is no `Class<List<Money>>`. `Class` objects are one per raw type, loaded once by the class loader — `List.class` is the only `Class` object a `List<Money>` and a `List<LinkedHashMap>` ever produce, because both erase to the same `.class` file. That is exactly the gap 2.7.6 exists to close.

A fourth token operation, `Array.newInstance(Class<?> componentType, int length)`, uses the same `Class<T>`-as-token idiom to build a reified array from an erased component type — `02b-generic-arrays-and-self-types.md` owns that build; it is the other place you will meet this pattern, not a second one.

Three or more operations on the same object means a table, not three paragraphs:

| Operation | Signature (JDK 21 `Class<T>`) | What it buys | What it throws |
|---|---|---|---|
| `cast` | `T cast(Object obj)` | A checked narrowing cast at a call site you choose | `ClassCastException`, naming the mismatch, at the call |
| `asSubclass` | `<U> Class<? extends U> asSubclass(Class<U> clazz)` | Narrows a `Class<?>` (from a name/config string) to a usable bound | `ClassCastException` if not a subtype |
| `isInstance` | `boolean isInstance(Object obj)` | A reflective `instanceof` with the type supplied as data, not syntax | Never throws — returns `false` |
| `getDeclaredConstructor().newInstance()` | `Constructor<T> getDeclaredConstructor(Class<?>[] parameterTypes)` (a varargs parameter, erased form shown) then `T newInstance(Object[] args)` (also varargs) | Constructs a `T` from the witness alone, where `new T()` cannot compile | `NoSuchMethodException`, `InstantiationException`, `IllegalAccessException`, `InvocationTargetException` (checked, must be handled) |

> A `Class<T>` object is a runtime witness for an erased compile-time type — the one bridge across the erasure boundary the platform gives you for free, and the only way a generic method gets to construct, cast, or type-check a `T` it does not otherwise know.

## 2. Super type tokens: defeating erasure through the `extends` clause (2.7.6)

`[PROVE]` The picture: a plain `Class<T>` witness can only ever name a raw type — `List.class`, never `List<Money>.class`, because no such object exists (§1). But there is exactly one place in the language where a *parameterised* type — the whole thing, `List<Money>`, arguments and all — survives past erasure into a class file: the `extends` clause of a class declaration. `javac` erases every type argument used in an expression (`new ArrayList<Money>()` compiles to `new ArrayList()`), but it does not erase type arguments used in a *declaration* — a superclass, an interface, a field, a method signature — because reflection over declarations is a feature the platform explicitly promises — `Class.getGenericSuperclass`, `Field.getGenericType`, and their siblings (§2.7.7) all exist precisely because `javac` keeps this information somewhere. "Somewhere" is the `Signature` attribute, one per relevant class-file structure, holding the original generic signature as a string.

### Why it exists

Put those two facts together and there is a way to smuggle a type argument past erasure that has nothing to do with `Class<T>` parameters at all: **declare an abstract generic class, and subclass it anonymously with a concrete argument.** The subclass's `extends` clause is a declaration, so `javac` writes a `Signature` attribute on it recording the full parameterised supertype — argument included — even though the anonymous subclass itself never uses that argument in any expression. This trick predates the JDK; it is Neal Gafter's "super type token" pattern, later folded into Guava and popularised as the shape behind Jackson's `TypeReference` and Google Guice's `TypeLiteral`.

### The mechanism — work it through, then prove it with `javap`

Declare an abstract carrier shaped exactly like Jackson's `TypeReference<T>`: its only job is to be subclassed, and its constructor reaches for its own runtime class to read back whatever was written in the `extends` clause that created it.

```java
abstract class VerdictTypeRef<T> {
    private final Type type;

    protected VerdictTypeRef() {
        Type superclass = getClass().getGenericSuperclass();
        if (superclass instanceof ParameterizedType parameterized) {
            this.type = parameterized.getActualTypeArguments()[0];
        } else {
            throw new IllegalStateException("VerdictTypeRef constructed without a type argument");
        }
    }

    Type type() {
        return type;
    }
}
```

Now the piece that makes it work: `new VerdictTypeRef<List<Money>>() {}`, the empty-braces shape, is not the same statement as `new VerdictTypeRef<List<Money>>()`. The braces create an anonymous subclass. Erasure deletes `<List<Money>>` from the `new` expression itself — that part is gone at the bytecode level, exactly as always — but the anonymous class's *declaration* is `class VerdictTypeRefDemo$1 extends VerdictTypeRef<List<Money>>`, and that `extends` clause is a declaration, not an expression. Walk it through before looking at the bytecode: `getClass()` inside the constructor returns the anonymous subclass, not `VerdictTypeRef` itself (constructors run with `this` already bound to the concrete runtime type); `getGenericSuperclass()` on that subclass reads its `Signature` attribute, not its erased `super_class` pointer; and that attribute is exactly the string `javac` wrote when it compiled the anonymous class's `extends` clause. Nothing about this needs the JVM to have "kept" `List<Money>` as a runtime concept — it only needs one string, attached to one class file, that nothing at runtime erases because reflection is the API contract that keeps it alive.

Compiled and disassembled on JDK 21.0.7 (`javap -p -v 'VerdictTypeRefDemo$1.class'`), the class header reads:

```
class VerdictTypeRefDemo$1 extends VerdictTypeRef<java.util.List<Money>>
  minor version: 0
  major version: 65
  flags: (0x0020) ACC_SUPER
  this_class: #7                          // VerdictTypeRefDemo$1
  super_class: #2                         // VerdictTypeRef
  interfaces: 0, fields: 0, methods: 1, attributes: 5
```

and the same disassembly's trailing attribute list reads:

```
Signature: #12                          // LVerdictTypeRef<Ljava/util/List<LMoney;>;>;
SourceFile: "VerdictTypeRefDemo.java"
EnclosingMethod: #16.#18                // VerdictTypeRefDemo.main
```

`super_class` above points at the plain, erased `VerdictTypeRef` constant-pool entry — that is the only supertype link the JVM's verifier and dispatch ever use, and it carries no argument. The argument lives one attribute down, in `Signature`. Read that descriptor left to right. The object-type form every class reference takes in a descriptor is a leading `L`, the binary name, then a trailing `;` (a primitive instead gets a single-letter code). `LVerdictTypeRef` followed by the angle-bracket block is the erased supertype wrapped in that form, with its type argument appended inside angle brackets *within the same descriptor string* — this is a `ClassSignature` grammar production (JVMS §4.7.9.1), not a plain class reference, which is exactly why it can nest. Inside those brackets, `Ljava/util/List` followed by its own angle-bracket block is itself a full nested object-type-with-arguments: `List`'s own binary name, then its own argument, `LMoney;`, one more level in. `Money` appears in the string at all — spelled out, fully — because the `Signature` attribute is not bytecode the JVM executes; it is a UTF-8 string in the constant pool that only `javap`, `javac`, and `java.lang.reflect` ever read. Erasure deletes type arguments from *executable* code — the instructions the JVM interprets — and leaves them completely alone in this one attribute, because the attribute was invented specifically so tools and reflection would not lose the information erasure otherwise destroys everywhere else.

That is the asymmetry stated as a single rule: **a type argument used in a `new` expression is erased and gone; the same argument used in an `extends` clause is written into the `Signature` attribute and stays.**

Now the recovery code, run to completion:

```java
public class VerdictTypeRefDemo {
    public static void main(String[] args) {
        VerdictTypeRef<List<Money>> ref = new VerdictTypeRef<List<Money>>() {};
        System.out.println("recovered type: " + ref.type());
        System.out.println("recovered type class: " + ref.type().getClass());
    }
}
```

On JDK 21.0.7 this prints:

```
recovered type: java.util.List<Money>
recovered type class: class sun.reflect.generics.reflectiveObjects.ParameterizedTypeImpl
```

`ref.type()` is a live `ParameterizedType` object, built by reflection at construction time by parsing that `Signature` string — the full round trip from source-level type argument, through a class-file attribute, back to a runtime `Type` object, with erasure never having deleted it because it was never in erasure's path to begin with. That is `[PROVE]` discharged: the mechanism was worked through above the `javap` output, and the `javap` output and the printed run confirm it, in that order.

No diagram: the manifest assigns this section none; the annotated `javap` excerpt above is the picture.

`[RESEARCH]` The real-world names, verified against each library's own javadoc rather than assumed:

| Library | Class | Where you meet it |
|---|---|---|
| Jackson (`jackson-core`) | `com.fasterxml.jackson.core.type.TypeReference<T>` | `objectMapper.readValue(json, new TypeReference<List<Money>>() {})` — deserialising a generic collection or wrapper |
| Spring Framework | `org.springframework.core.ParameterizedTypeReference<T>` | `restClient.get().retrieve().body(new ParameterizedTypeReference<List<Money>>() {})` on `RestClient`, `WebClient`, and `RestTemplate.exchange` |
| Google Guice | `com.google.inject.TypeLiteral<T>` | `Key.get(new TypeLiteral<List<Money>>() {})` — binding a parameterised type in a Guice module |

Jackson's own javadoc states the pattern by name: `TypeReference` is "based on ideas from Super Type Token" and exists because "Java doesn't yet provide a way to represent generic types" any other way — the same justification Guice's `TypeLiteral` javadoc gives almost verbatim. None of these three classes is on this machine's JDK classpath (they ship in separate library JARs, not the JDK), so `VerdictTypeRef` above is the compiled proof of the mechanism, and this table is the citation of who builds on it, not a second compilation.

**Insight:** the trick works because Java draws the erasure line at the expression/declaration boundary, not at the "was this a generic parameter" boundary — and reflection was deliberately designed to read every declaration site the compiler still records, which is why an *idiom* (subclass anonymously) can do something a *cast* or a stored `Class<T>` object never could: hand back a fully parameterised type, arguments and all.

**Interview:** "generics are erased, so how does Jackson know what to build?" — the 90-second answer: it doesn't recover the type from the erased value at all; it recovers it from the caller's *declaration*. You subclass `TypeReference<List<Money>>` anonymously; `javac` cannot erase the type argument out of the anonymous class's `extends` clause because that's a declaration, not an expression, so it gets written into a `Signature` attribute; Jackson's constructor calls `getGenericSuperclass()` on itself, reads that attribute back as a `ParameterizedType`, and builds a `JavaType` from it before deserialising a single byte. It only works because you wrote `new TypeReference<List<Money>>() {}` with the braces — without them there is no subclass, no `extends` clause, and nothing to read.

> A super type token defeats erasure by moving the type argument from a `new` expression, which erasure deletes, into an anonymous subclass's `extends` clause, which is a declaration erasure never touches — the argument survives as a `Signature` attribute string that `getGenericSuperclass()` parses back into a `ParameterizedType` at runtime.

## 3. Recovering type arguments at runtime — the API and its exact boundary (2.7.7)

`[RESEARCH]` §2 proved one specific case: a class's own generic superclass. The mental model behind the full API surface is that reflection can read a type argument **anywhere `javac` wrote a `Signature` attribute for a declaration** — and nowhere else. `Class.getGenericSuperclass()` returns a plain `Type` when the immediate superclass was not itself generic, or a `ParameterizedType` when it was; `ParameterizedType.getActualTypeArguments()` returns the `Type[]` inside the angle brackets, in declaration order, each element itself possibly another `ParameterizedType` (as `List<Money>` was, nested inside `VerdictTypeRef<List<Money>>`, in §2).

### Why it exists

Before generics, reflection's `getSuperclass`, `getInterfaces`, `getType`, `getReturnType`, and `getParameterTypes` all returned raw `Class` objects — accurate for erased types, useless for asking "what did the source say this collection held?" JDK 5 added a parallel `getGeneric*` family precisely so tools like ORMs, JSON libraries, and DI containers could answer that question without parsing source themselves — by reading the same `Signature` attribute `javap` prints, through an API instead of a disassembler.

### The mechanism

Every accessor in the `getGeneric*` family reads a `Signature` attribute attached to a specific declaration site; the sibling methods below all follow the identical pattern §2 walked through in detail, so a table is the right shape, not five more repetitions of the same argument.

| Accessor | Declares on | `Signature` attribute lives on |
|---|---|---|
| `Class.getGenericSuperclass()` | the `extends` clause of a class | `class_info` |
| `Class.getGenericInterfaces()` | the `implements` clause of a class | `class_info` |
| `Field.getGenericType()` | a field's declared type | `field_info` |
| `Method.getGenericReturnType()` | a method's return type | `method_info` |
| `Method.getGenericParameterTypes()` | a method's parameter types | `method_info` |
| `Parameter.getParameterizedType()` | one formal parameter's type | `method_info` (per-parameter slice) |

**The boundary, stated as the rule that governs every row above and every use of §2's trick:** a type argument is recoverable through reflection **if and only if it was written into a class file as part of a declaration** — a superclass, an interface, a field, a method signature, a type parameter bound. It is never recoverable if it existed only as a local variable's type argument, or only as an argument to a `new` expression that was never also captured in a declaration. Declarations get a `Signature` attribute because reflection is a documented, permanent contract over class-file *structure*; a local variable is not part of that structure — it lives and dies inside one method's `Code` attribute, which reflection has no API to inspect at the statement level at all.

Prove the negative side first, because it is the one people assume works and does not: a plain local `List<Money>` inside a method has no reflective path to `Money` whatsoever — there is no method on `Method`, `Class`, or anywhere else that takes "a local variable" and returns its declared generic type, because a local variable is not a member reflection was ever built to describe. Compare it against a *field* of the identical type, which is a declaration, and recovers cleanly.

```java
final class SettlementBatch {
    // A field's type argument IS recorded in a Signature attribute on the
    // field_info structure - it is part of the class's declaration.
    private final List<Money> settled = new ArrayList<>();

    void addSettled(Money m) {
        settled.add(m);
    }
}

public class FieldVsLocal {
    public static void main(String[] args) throws Exception {
        // A local variable's type argument exists only in the source file and
        // (optionally) a debug-only LocalVariableTypeTable - never in a
        // Signature attribute reflection can read.
        List<Money> localBatch = new ArrayList<>();
        localBatch.add(new Money(new BigDecimal("4.20"), Currency.getInstance("GBP")));
        System.out.println("local variable element type via reflection: NOT RECOVERABLE - " +
                "no API call exists that takes a local variable and returns its declared Type");

        Field field = SettlementBatch.class.getDeclaredField("settled");
        Type genericFieldType = field.getGenericType();
        if (genericFieldType instanceof ParameterizedType parameterized) {
            Type elementType = parameterized.getActualTypeArguments()[0];
            System.out.println("field element type via reflection: " + elementType);
        }
    }
}
```

Run on JDK 21.0.7:

```
local variable element type via reflection: NOT RECOVERABLE - no API call exists that takes a local variable and returns its declared Type
field element type via reflection: class Money
```

Two `javap` dumps make the class-file-level difference concrete. The field's `field_info` structure carries its own `Signature` attribute:

```
Signature: #23                          // Ljava/util/List<LMoney;>;
```

That is a *field descriptor* signature (JVMS §4.7.9.1 `FieldSignature`), not a class signature — the same leading-`L`-binary-name-trailing-`;` grammar as §2, just one nesting level shallower because a field's type is not wrapped in a supertype relationship. The `main` method's `Code` attribute, disassembled with default `javac` flags (no `-g`), has **no** signature information for `localBatch` at all — `javap -p -c` on that method shows the raw bytecode (a `new ArrayList`, `invokeinterface List.add`) with no local-variable metadata whatsoever, because default `javac` output includes only `LineNumberTable`, not variable tables.

Compiling the same source with `javac -g` changes this, but only partially, and it is worth being precise about what it adds rather than assuming: `[RESEARCH]` confirmed by direct compilation on JDK 21.0.7 — `javac -g FieldVsLocal.java` followed by `javap -p -v` on the result **does** produce a `LocalVariableTypeTable` entry for `localBatch`, reading `Ljava/util/List<LMoney;>;` over the byte-code range where the variable is live. So the generic type of a local variable *is* recoverable — but only from a class file compiled with debug variable information (`-g` or `-g:vars`, not the default), only by parsing that debugging-only attribute directly (there is no `java.lang.reflect` API that surfaces it — `LocalVariableTypeTable` is consumed by debuggers and IDEs, not by the reflection API), and never through `getGenericSuperclass`, `getGenericType`, or any sibling in the table above. The practical rule for application code stands: *reflection*, as opposed to bytecode tooling, cannot recover a local variable's type argument, full stop, and production JARs are routinely built without `-g:vars` regardless.

**The practical consequence.** This boundary is *why* framework APIs make you pass a token or subclass an abstract class instead of just handing over a generic value directly — `objectMapper.readValue(json, List.class)` cannot know you wanted `List<Money>` because by the time that call happens, "wanted `List<Money>`" was only ever a local variable's type argument, which is invisible to reflection. Passing a `Class<T>` token (§1) works when `T` itself is a simple class; it fails for `List<Money>` because there is no `Class<List<Money>>` object to pass (§1's closing point). The super type token from §2 is the only fix, and the anonymous-subclass braces exist for exactly one reason: they turn "the type argument I want" from a local expression (invisible) into a class declaration (a `Signature` attribute, fully recoverable by `getGenericSuperclass`).

> A generic type argument is recoverable through reflection exactly when it was recorded in a `Signature` attribute on a declaration — a superclass, interface, field, or method signature — and never when it existed only inside a method body as a local variable's type argument or a `new` expression's argument.

## Supporting facts

### `getClass()` inside a constructor sees the concrete subtype, not the declaring class

`this.getClass()` called from `VerdictTypeRef`'s own constructor (§2) returns the anonymous subclass created by the caller, because `getClass()` is a virtual call resolved against the object's actual runtime type, and by the time any constructor body runs, the object already exists with its final, concrete class. This is the one fact the super-type-token trick depends on beyond the `Signature` attribute itself — get it wrong (call `getClass()` on a `static` context, or cache it before the object is fully constructed in a multi-level hierarchy) and `getGenericSuperclass()` reads the wrong class's attribute entirely.

> `getClass()` always resolves to the most-derived runtime type, never the class whose method body is executing.

### `ParameterizedType.getRawType()` versus `getActualTypeArguments()`

A `ParameterizedType` bundles two things you almost always want separately: `getRawType()` returns the erased `Type` (a `Class` object, e.g. `List.class`), and `getActualTypeArguments()` returns the `Type[]` of what filled the angle brackets. Confusing the two is the most common mistake reading `ParameterizedType` output for the first time — the raw type alone is exactly what §1 already gave you for free via `Class<T>`; the whole reason to reach for `ParameterizedType` in the first place is the argument array.

> `getRawType()` gives back what a plain `Class<T>` witness already told you; `getActualTypeArguments()` gives back the part erasure otherwise deletes.

### `TypeVariable` versus `ParameterizedType` in `getGenericSuperclass()`'s return

`getGenericSuperclass()`'s return type is the general `Type`, and it is not always a `ParameterizedType`: if the immediate superclass is not itself parameterised (a plain `class SettlementBatch extends Object`), it returns the plain `Class` object for `Object`. §2's `instanceof ParameterizedType parameterized` check exists for exactly this reason — it is not defensive boilerplate, it is the correct handling of a real alternative outcome, and skipping it (assuming every `getGenericSuperclass()` result is a `ParameterizedType`) throws a `ClassCastException` the moment someone constructs `VerdictTypeRef` without a concrete argument (raw type usage), which is exactly the branch that condition's `else` throws `IllegalStateException` for instead, with a clearer message.

> `getGenericSuperclass()` returns `ParameterizedType` only when the superclass itself carries type arguments; always check before casting.

## Pitfalls

### "`(T) x` and `type.cast(x)` are the same cast, just different syntax"

**Wrong**

```java
@SuppressWarnings("unchecked")
<T extends LedgerEntry> T readUnchecked(Map<String, Object> slots, String key) {
    Object raw = slots.get(key);
    return (T) raw;   // compiles to a plain reference copy - no checkcast at all
}
```

Called with a `BonusEntry` stored under a key the caller reads back as `CashEntry`, this method returns cleanly — no exception, no warning at runtime, nothing. The mismatch surfaces later, wherever the mistyped reference is finally used as a `CashEntry` (as `DeferredCast` above demonstrated at its `for` loop, one class away from where the bad value was written).

**Right**

```java
<T extends LedgerEntry> T readChecked(Map<String, Object> slots, String key, Class<T> type) {
    Object raw = slots.get(key);
    return type.cast(raw);   // real instanceof + throw, right here
}
```

This throws `ClassCastException` from inside `readChecked` itself, at the line of the cast, naming both classes — the same exception, deliberately relocated to the boundary instead of wherever downstream code happens to dereference the bad value first.

**Why people believe it:** both spellings produce a `ClassCastException` somewhere, eventually, if the types genuinely mismatch — and for correct code, both spellings behave identically, so the difference never shows up in the happy path or in a quick manual test that only exercises correct input.

### "`Class<T>` lets me write `Class<List<Money>>` for a precise witness"

**Wrong**

```java
// Does not compile: List<Money> is not a class, it is a parameterised type,
// and Class<T> objects exist one per loaded .class file - there is exactly
// one Class object for List, shared by every parameterisation of it.
Class<List<Money>> impossible = List.class;
```

`javac` rejects this outright — `List.class` has static type `Class<List>` (raw), which is not assignable to `Class<List<Money>>` and cannot be made so by any cast that isn't itself unchecked and pointless, because no such object is ever created at runtime to assign.

**Right**

```java
ParameterizedTypeReference<List<Money>> ref = new ParameterizedTypeReference<List<Money>>() {};
```

Reach for a super type token (§2.7.6) the moment the type you need a witness for has its own type arguments — that is precisely the situation `Class<T>` cannot serve, and precisely the situation the anonymous-subclass trick exists to serve instead.

**Why people believe it:** `Class<T>` looks generic, so it is natural to assume it can be parameterised by anything, including another parameterised type — but `Class` objects are a runtime concept tied one-to-one to loaded `.class` files, and erasure guarantees there is only ever one `.class` file for `List`, regardless of how many different `List<X>` appear in source.

### "`getGenericSuperclass()` always returns a `ParameterizedType` I can safely cast"

**Wrong**

```java
ParameterizedType parameterized = (ParameterizedType) getClass().getGenericSuperclass();
Type recovered = parameterized.getActualTypeArguments()[0];
```

Constructed as `new VerdictTypeRef() {}` — no type argument at all, a raw usage — `getClass().getGenericSuperclass()` returns the plain `Class` object for `VerdictTypeRef`, not a `ParameterizedType`, and the direct cast above throws `ClassCastException: class VerdictTypeRef cannot be cast to class java.lang.reflect.ParameterizedType` before `getActualTypeArguments()` is ever reached.

**Right**

```java
Type superclass = getClass().getGenericSuperclass();
if (superclass instanceof ParameterizedType parameterized) {
    this.type = parameterized.getActualTypeArguments()[0];
} else {
    throw new IllegalStateException("VerdictTypeRef constructed without a type argument");
}
```

Pattern-match with `instanceof` and handle the non-parameterised case explicitly with a message that names the actual problem (missing type argument), rather than letting an unrelated `ClassCastException` describe it badly.

**Why people believe it:** every worked example of the super-type-token pattern (including this file's own `VerdictTypeRefDemo`) is written with a concrete type argument, so the parameterised branch is the only one most readers ever exercise until a caller — deliberately or by mistake — constructs the raw form.

## Cheat sheet

| Need | API | Throws | Owning section |
|---|---|---|---|
| Checked cast at a chosen boundary | `Class.cast(Object)` | `ClassCastException`, names both types, at the call | 2.7.5 |
| Narrow a `Class<?>` (from a name/config string) | `Class.asSubclass(Class<U>)` | `ClassCastException` if not a subtype | 2.7.5 |
| Test membership without casting | `Class.isInstance(Object)` | never — returns `boolean` | 2.7.5 |
| Construct a `T` from a witness alone | `Class.getDeclaredConstructor().newInstance()` | four checked reflective exceptions | 2.7.5 |
| Capture a fully parameterised type (`List<Money>`) | anonymous subclass of an abstract generic carrier + `getGenericSuperclass()` | `IllegalStateException` if constructed raw (your own guard) | 2.7.6 |
| Real-world super type tokens | `TypeReference<T>` (Jackson), `ParameterizedTypeReference<T>` (Spring), `TypeLiteral<T>` (Guice) | — | 2.7.6 |
| Read a field's declared generic type | `Field.getGenericType()` | — | 2.7.7 |
| Read a method's declared generic return/parameter types | `Method.getGenericReturnType()` / `getGenericParameterTypes()` | — | 2.7.7 |
| Read one parameter's declared generic type | `Parameter.getParameterizedType()` | — | 2.7.7 |
| Recover a local variable's type argument via reflection | **not possible** — no reflective API reads `LocalVariableTypeTable` | — | 2.7.7 |
| Get the erased raw type out of a `ParameterizedType` | `ParameterizedType.getRawType()` | — | Supporting facts |
| Get the type arguments out of a `ParameterizedType` | `ParameterizedType.getActualTypeArguments()` | — | Supporting facts / 2.7.7 |

## Self-test

**Q1.** A `Map<String, Object>` holds a `BonusEntry` under a key you expect to be a `CashEntry`. Compare what happens when you read it back with `Class.cast` versus with an unchecked `(T) x` cast.

<details><summary>Answer</summary>

`Class.cast` performs a real `instanceof`-style check inside its own method body and throws `ClassCastException` immediately, naming both classes, at the exact line of the cast — the failure is local to the boundary where the untyped data entered typed code. `(T) x` with an erased type parameter compiles to no `checkcast` instruction at all; the method returns the mistyped reference without complaint, and the actual `ClassCastException` only fires later, wherever the compiler had to insert its own implicit `checkcast` to satisfy a more specific static type — which can be in a completely different method or class, far from where the bad value was written in.

</details>

**Q2.** What does `Class.asSubclass` do that a direct `(Class<? extends Verdict>) raw` cast does not?

<details><summary>Answer</summary>

`asSubclass` performs a genuine `isAssignableFrom`-style check and throws `ClassCastException` right at the call if the relation does not hold. A direct cast of the `Class` object itself is an unchecked cast — `Class<?>` erases the same way any other generic type does, so `(Class<? extends Verdict>) raw` compiles with an unchecked warning and no runtime check whatsoever; it will silently produce a `Class` reference typed as `Class<? extends Verdict>` even when the underlying class has nothing to do with `Verdict`, and the failure only shows up later when something tries to actually use it as one.

</details>

**Q3.** Why is there no such thing as `Class<List<Money>>`, and what do you reach for instead when you need a witness for a parameterised type?

<details><summary>Answer</summary>

`Class` objects are created one per loaded `.class` file, and erasure guarantees there is exactly one `.class` file for `List`, shared by every parameterisation of it — `List<Money>` and `List<LinkedHashMap>` both produce `List.class` at runtime, so there is nothing for a hypothetical `Class<List<Money>>` object to actually be. Instead you reach for a super type token: an abstract generic carrier class, subclassed anonymously with the concrete argument (`new TypeReference<List<Money>>() {}`), which records the argument in the subclass's `Signature` attribute instead of in a `Class` object.

</details>

**Q4.** Walk through why `new VerdictTypeRef<List<Money>>() {}` can recover `List<Money>` at runtime when generics are erased.

<details><summary>Answer</summary>

Erasure deletes type arguments from expressions, and `new VerdictTypeRef<List<Money>>()` on its own is exactly such an expression — the argument would be gone. But the trailing `{}` creates an anonymous subclass, and that subclass's declaration is `class Anonymous extends VerdictTypeRef<List<Money>>` — an `extends` clause, which is not an expression but a declaration. `javac` writes a `Signature` attribute on every declaration that used generics, regardless of whether anything in the declaration's own body uses the type argument, so the attribute records `List<Money>` in full even though the anonymous class does nothing with it directly. `VerdictTypeRef`'s constructor then calls `getClass().getGenericSuperclass()`, which reads that exact attribute back and parses it into a live `ParameterizedType` object.

</details>

**Q5.** Name the three real-world libraries that use the super-type-token pattern, their classes, and one place each is used.

<details><summary>Answer</summary>

Jackson's `com.fasterxml.jackson.core.type.TypeReference<T>`, used as `objectMapper.readValue(json, new TypeReference<List<Money>>() {})` to deserialise a generic collection. Spring's `org.springframework.core.ParameterizedTypeReference<T>`, used with `RestClient`, `WebClient`, and `RestTemplate.exchange` to deserialise a generic HTTP response body such as a `List<Money>`. Google Guice's `com.google.inject.TypeLiteral<T>`, used to bind a parameterised type in a module, e.g. `Key.get(new TypeLiteral<List<Money>>() {})`.

</details>

**Q6.** Can reflection recover the element type of a plain local variable, `List<Money> batch = new ArrayList<>();`, declared inside a method body? Why or why not?

<details><summary>Answer</summary>

No, not through the `java.lang.reflect` API. A local variable's type argument is never written into a `Signature` attribute, because `Signature` attributes exist only for declarations reflection is contractually built to expose — class superclasses/interfaces, fields, and method signatures — and a local variable is not one of those; it lives inside a method's `Code` attribute. Compiling with `-g` does add a debug-only `LocalVariableTypeTable` entry recording the same generic type string, but no method in `java.lang.reflect` reads that table — it exists for debuggers and IDEs, not for `Field`/`Method`/`Parameter` accessors — so from an application's point of view the answer stays no.

</details>

**Q7.** State the general rule for which type arguments reflection can recover, and give one example each of a recoverable and an unrecoverable case.

<details><summary>Answer</summary>

Reflection can recover a type argument exactly when it was written into a class file as part of a declaration — a superclass, an interface, a field, or a method signature. It can never recover one that existed only inside a `new` expression or as a local variable's type argument, unless that same argument was also captured in a declaration elsewhere (as the super-type-token pattern deliberately does). Recoverable: a field `private final List<Money> settled` — `Field.getGenericType()` returns a `ParameterizedType` naming `Money`. Unrecoverable: a local `List<Money> batch = new ArrayList<>();` inside a method body — no reflective API returns anything about its element type.

</details>

**Q8.** Why does `new TypeReference<List<Money>>(){}` need the trailing braces, and what would happen without them?

<details><summary>Answer</summary>

The braces are what create the anonymous subclass, and the anonymous subclass's `extends` clause is the only place the type argument survives past erasure — it becomes a `Signature` attribute on that subclass, readable via `getGenericSuperclass()`. Without the braces, `new TypeReference<List<Money>>()` is a plain constructor call with no subclass created at all; the type argument is erased from that expression exactly like any other generic instantiation, and `getClass()` inside the constructor returns `TypeReference` itself, whose own `getGenericSuperclass()` (if `TypeReference` extends `Object`) has nothing generic to report. The whole mechanism depends on the caller declaring a new class, not calling a constructor.

</details>

## Open questions

None — the two `[RESEARCH]` leaves were confirmed directly: the three super-type-token library class names were verified against each library's own published javadoc, and the `-g` / `LocalVariableTypeTable` behaviour was confirmed by compiling and disassembling on this machine's JDK 21.0.7 rather than assumed.

---

**Leaves covered:** 2.7.5, 2.7.6, 2.7.7 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 548
