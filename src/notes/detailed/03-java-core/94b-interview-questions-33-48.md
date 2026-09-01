# 03 Java Core — The eighty questions, 33–48 — INTERVIEW (§5.1, 5.1.33–5.1.48)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The eighty questions, 17–32](94a-interview-questions-17-32.md) · Next: [The eighty questions, 49–64](94c-interview-questions-49-64.md)

## The questions, continued

Sixteen more of the eighty — how to use this file, and the shared house rules, are in [`94-interview-questions-and-drills.md`](94-interview-questions-and-drills.md).

### Q33. "Explain PECS with a real signature."

**The 30-second answer.** PECS is Producer Extends, Consumer Super: a parameter your method only reads from is a producer and takes `? extends T`; a parameter it only writes into is a consumer and takes `? super T`. The canonical JDK signature that shows both in one method is `Collections.copy(List<? super T> dest, List<? extends T> src)` — `dest` is written to, so it is the consumer and takes `super`; `src` is read from, so it is the producer and takes `extends`.

**The 5-minute answer.** Read the mnemonic off the signature rather than reciting it. `dest`'s declared bound is `? super T`, meaning `dest`'s real element type is `T` or something broader than `T` — a `List<LedgerEntry>` accepting `T = CashEntry`. Every write of a `T` into `dest` is safe because whatever `dest` actually holds is guaranteed to be a supertype of `T`, so a `CashEntry` fits. `src`'s declared bound is `? extends T`, meaning `src`'s real element type is `T` or something narrower — a `List<CashEntry>` accepting the same `T = CashEntry` bound — and every value read out of `src` is guaranteed to be at least a `T`. The same shape recurs once you know to look for it: `Collection.addAll(Collection<? extends E> c)` takes its argument purely as a producer of `E`, and `Comparator<? super T>` (used by `List.sort`) takes a comparator that only consumes pairs of `T`, so a comparator written for a broader type is accepted. The mechanism underneath both bounds is capture: a wildcard type is a constraint attached to one *use* of a generic type, not a nameable type — you cannot write `new ArrayList<? extends LedgerEntry>()`, because there is no single type for `new` to instantiate. Through a `? extends T` parameter you may write nothing but `null`, because no expression is provably a value of the unknown captured subtype; through a `? super T` parameter a read can only be typed `Object`, because `Object` is the only type every possible captured supertype of `T` is guaranteed to share. That asymmetry is exactly why PECS assigns one direction per role rather than letting either wildcard do both jobs.

```java
sealed interface LedgerEntry permits CashEntry, BonusEntry {}
record CashEntry(java.util.UUID id, Money amount) implements LedgerEntry {}
record BonusEntry(java.util.UUID id, Money amount) implements LedgerEntry {}

final class LedgerCopy {
    // dest: consumer of T, takes ? super T. src: producer of T, takes ? extends T.
    static <T> void copy(java.util.List<? super T> dest, java.util.List<? extends T> src) {
        for (int i = 0; i < src.size(); i++) {
            dest.set(i, src.get(i)); // read a T out of src, write a T into dest — both provably safe
        }
    }

    static void postAll(java.util.List<? extends LedgerEntry> entries) {
        // producer only: entries is never written into, so List<CashEntry> or List<BonusEntry> both fit
        entries.forEach(e -> System.out.println(e.id()));
    }
}
```

**The follow-up they will ask** — "why can't `src` be declared as a plain `List<T>` instead?" It could, but it would then reject a caller holding `List<CashEntry>` when `T` is inferred as `LedgerEntry`, because generics are invariant — `? extends T` buys back exactly the substitutability invariance removes, for the read-only direction PECS names.

**Where this is written** — [`generics/01b-variance-and-wildcards.md`](generics/01b-variance-and-wildcards.md), [`generics/02-in-anger.md`](generics/02-in-anger.md).

### Q34. "What is a bridge method?"

**The 30-second answer.** A bridge method is a compiler-synthesised forwarding thunk, flagged `ACC_BRIDGE | ACC_SYNTHETIC` in the class file, that gives a subclass's narrower override the exact erased descriptor its superclass method needs, so that `invokevirtual`'s exact name-and-descriptor dispatch still finds it. `AbstractStore<E extends LedgerEntry>` declaring `abstract void save(E entry)`, overridden in `CashEntryStore extends AbstractStore<CashEntry>` as `void save(CashEntry entry)`, is one method at the source level and two different method descriptors after erasure — `javac` manufactures the connective tissue.

**The 5-minute answer.** `javap -p -c -v` on `CashEntryStore` shows two entries: `void save(CashEntry)` at `flags: (0x0000)`, the real body, and a synthetic `void save(LedgerEntry)` at `flags: (0x1040) ACC_BRIDGE, ACC_SYNTHETIC` whose body is `aload_0; aload_1; checkcast CashEntry; invokevirtual CashEntryStore.save:(LCashEntry;)V; return`. JVMS Table 4.6-A gives `ACC_BRIDGE` the value `0x0040` and `ACC_SYNTHETIC` the value `0x1000`; `0x1000 | 0x0040 = 0x1040` matches the measured flags word exactly. Bridges have two independent triggers, not one: generic override erasure, as above, and covariant return narrowing with no generics involved at all — `EntryFactoryBase.create()` returning `LedgerEntry`, overridden in `CashEntryFactory` as `create()` returning `CashEntry`, gets a synthetic `LedgerEntry create()` bridge too, because `invokevirtual` matches on the full descriptor including the return type. The failure mode: pass a raw-typed `AbstractStore` reference a `BonusEntry` where a `CashEntry` was expected, and the bridge's own `checkcast` throws `ClassCastException` from a stack frame reading `CashEntryStore.save`, pinned to the *class declaration line*, not any statement inside `save` — because the bridge has no source line of its own and `javac` attributes its `LineNumberTable` entry to the declaration that implicitly triggered its generation. `Method.isBridge()`, present since Java 5 (the same release that introduced generics and covariant returns), is the correct filter to recover just the real override from `getDeclaredMethods()`; `isSynthetic()` over-excludes, because plenty of synthetic members — a lambda's implementation method, a nested class's private-member forwarder — are synthetic but not bridges.

```java
abstract class AbstractStore<E extends LedgerEntry> {
    abstract void save(E entry);
}

final class CashEntryStore extends AbstractStore<CashEntry> {
    @Override
    void save(CashEntry entry) {
        System.out.println("stored " + entry.id());
    }
    // javac also emits: synthetic void save(LedgerEntry entry) {
    //     save((CashEntry) entry);   // checkcast lives here, not in your source
    // }
}

final class BridgeFailureDemo {
    @SuppressWarnings({"unchecked", "rawtypes"})
    static void triggerViaRawType(AbstractStore raw, BonusEntry bonus) {
        raw.save(bonus); // resolves to the bridge; its checkcast throws ClassCastException
    }
}
```

**The follow-up they will ask** — "can this happen with no generics at all?" Yes — covariant return narrowing is the second, independent trigger; both cases repair the same kind of descriptor mismatch, one on the parameter side, one on the return side.

**Where this is written** — [`generics/03a-internals-bridge-methods.md`](generics/03a-internals-bridge-methods.md).

### Q35. "What is heap pollution and what does @SafeVarargs promise?"

**The 30-second answer.** Heap pollution is a variable of a parameterized type referring to an object that is not of that parameterized type — the classic route is generic varargs, because `T... args` is really `T[] args` under erasure, and `Object[]` accepts any reference array through covariance, so a caller can smuggle a `List<String>` into a slot the method believes is `List<Money>`. `@SafeVarargs` is not a check — it is a personal, unverified assertion by the method's author that the varargs array is never exposed unsafely; it only suppresses the `[unchecked]`/`[varargs]` warnings and is legal only on `static`, `final`, `private` (Java 9+), or (originally Java 7/8 only `static`/`final`) non-overridable instance methods, because an override could break the promise the annotation makes for the whole call hierarchy.

**The 5-minute answer.** Mechanically: `static void logBatches(List<Money>... batches)` compiles its varargs parameter to `List[] batches` — the array's component type is the erasure of `List<Money>`, which is `List`, and `List[]` is `Object[]`-covariant-compatible. A method that does `Object[] escape = batches; escape[0] = List.of("not money");` compiles with an `[unchecked]` warning at the *declaration* and another at every *call site*, and the store itself succeeds at runtime because `aastore`'s covariance check only verifies against the array's actual component type (`List`, since erasure already flattened `List<Money>` to that), not against the `Money` type argument that no longer exists at runtime — that gap is heap pollution's mechanism. The failure surfaces later, arbitrarily far from the store: whichever method reads slot 0 back as a `List<Money>` gets a `ClassCastException` on the first element it touches, from a stack frame that is a real statement with a real line, distinguishing it from a bridge-method failure (Q34), whose frame sits on a declaration line instead. `@SafeVarargs` (Java 7) exists because the identical erased signature is shared by a genuinely safe method (`List.of`, `Arrays.asList`) and an unsafe one, and there is no way for a caller to tell which from the signature alone — the annotation lets the author who can see the body make that determination once, for every caller. Its three honest conditions: the method must not store anything into the varargs array, must not let the array (or an alias of it) escape to untrusted code, and — for these two to be checkable at all — must be non-overridable, because `@SafeVarargs` on an overridable instance method would let a subclass override violate a promise the annotation makes on the supertype's behalf; `javac` enforces exactly the non-overridable legality check and nothing about the two behavioural conditions, which remain the author's unverified word.

```java
final class VarargsPollutionDemo {
    @SafeVarargs // legal: static — this method neither stores into batches nor lets it escape
    static void logBatches(java.util.List<Money>... batches) {
        for (java.util.List<Money> batch : batches) {
            System.out.println(batch.size());
        }
    }

    // No @SafeVarargs: this one pollutes on purpose to show the mechanism.
    static void polluteAndRead(java.util.List<Money>... batches) {
        Object[] escape = batches;                 // legal: array covariance
        escape[0] = java.util.List.of("not money"); // heap pollution: batches[0] is now a List<String>
        Money first = batches[0].get(0);            // compiles; javac inserts a checkcast here
        // throws ClassCastException at THIS line, not at the polluting store above
        System.out.println(first);
    }
}
```

**The follow-up they will ask** — "does `@SafeVarargs` make the method's body actually safe?" No — it is a suppression switch the compiler only checks for legality (non-overridable), never for correctness; a method that stores into the array or lets it escape can carry `@SafeVarargs` and compile cleanly while remaining exactly as unsafe as before.

**Where this is written** — [`generics/03c-internals-heap-pollution-and-safevarargs.md`](generics/03c-internals-heap-pollution-and-safevarargs.md), [`generics/01c-raw-types-and-unchecked-warnings.md`](generics/01c-raw-types-and-unchecked-warnings.md).

### Q36. "How does Jackson know the element type of a List<LedgerEntry> at runtime?"

**The 30-second answer.** It doesn't recover the type from the erased value at all — it recovers it from the caller's *declaration*, using the super type token trick. `objectMapper.readValue(json, new TypeReference<List<LedgerEntry>>() {})` creates an anonymous subclass whose `extends` clause is `TypeReference<List<LedgerEntry>>`; `javac` erases type arguments out of *expressions* but not out of a class's `extends` clause, because that is a declaration, so the argument survives in a `Signature` attribute. `TypeReference`'s constructor calls `getClass().getGenericSuperclass()`, reads that attribute back as a live `ParameterizedType`, and builds a deserialization target from it before reading a single byte of JSON.

**The 5-minute answer.** A plain `Class<T>` witness can only ever name a raw type — `List.class`, never `List<LedgerEntry>.class`, because no such object exists; ordinary generic reflection over an *expression* (`new ArrayList<LedgerEntry>()`) gives `javac` nothing to keep, since `new ArrayList<LedgerEntry>()` compiles to plain `new ArrayList()`. The one place a fully parameterized type survives past erasure into the class file is a *declaration* — a superclass, an interface, a field, a method signature — because reflection over declarations (`Class.getGenericSuperclass`, `Field.getGenericType`, `Parameter.getParameterizedType`) is a feature the platform explicitly promises, and `javac` backs that promise with a `Signature` attribute per relevant class-file structure, holding the original generic signature as a string, parsed at runtime into `Type` objects — `ParameterizedType`, `TypeVariable` — that never existed in erasure's path to begin with. `new TypeReference<List<LedgerEntry>>() {}` with the trailing braces creates a real anonymous subclass; without the braces there is no `extends` clause and nothing to read — that is the entire trick, and it fails silently (or with a `ClassCastException` on the cast to `ParameterizedType`) the moment someone drops the braces or constructs the raw `TypeReference` type. `ParameterizedType` bundles two things: `getRawType()` returns the erased `Class` (`List.class`), and `getActualTypeArguments()` returns the `Type[]` of what filled the angle brackets, in declaration order — `getGenericSuperclass()` returns a plain `Class`, not a `ParameterizedType`, when the immediate superclass carries no type arguments (a raw-typed usage), so every caller of this pattern must `instanceof`-check before casting or risk a `ClassCastException` on that check alone. Spring's `ParameterizedTypeReference<T>` and Guice's `TypeLiteral<T>` are the identical mechanism under different names — `restClient.get().retrieve().body(new ParameterizedTypeReference<List<LedgerEntry>>() {})` deserializes an HTTP response body the same way.

```java
abstract class VerdictTypeRef<T> {
    private final java.lang.reflect.Type type;

    protected VerdictTypeRef() {
        java.lang.reflect.Type superclass = getClass().getGenericSuperclass();
        if (superclass instanceof java.lang.reflect.ParameterizedType parameterized) {
            this.type = parameterized.getActualTypeArguments()[0];
        } else {
            throw new IllegalStateException("VerdictTypeRef constructed without a type argument");
        }
    }

    java.lang.reflect.Type type() {
        return type;
    }
}

final class SuperTypeTokenDemo {
    static void demo() {
        // The braces create an anonymous subclass whose extends clause carries the argument;
        // javac writes a Signature attribute for it, and the constructor above reads it back.
        VerdictTypeRef<java.util.List<LedgerEntry>> ref =
                new VerdictTypeRef<java.util.List<LedgerEntry>>() {};
        System.out.println(ref.type()); // java.util.List<LedgerEntry>, a live ParameterizedType
    }
}
```

**The follow-up they will ask** — "does this work for a local variable's generic type too?" No — reflection has no API for a local variable's type argument at all; `javac -g:vars` writes a `LocalVariableTypeTable` that debuggers read, but there is no `java.lang.reflect` entry point onto it, so the super type token pattern only ever works at a declaration reflection can already see: a field, a superclass, a method signature.

**Where this is written** — [`generics/02a-type-tokens-and-generic-reflection.md`](generics/02a-type-tokens-and-generic-reflection.md), [`generics/03e-internals-why-erasure-and-super-type-tokens.md`](generics/03e-internals-why-erasure-and-super-type-tokens.md), [`reflection/02b-proxies-frameworks-and-generics.md`](reflection/02b-proxies-frameworks-and-generics.md).

### Q37. "Interface with default methods vs abstract class — when do you pick which?"

**The 30-second answer.** Pick the interface when the thing is a capability unrelated types must be able to claim and there is no instance state to carry; pick the abstract class when there is instance state or a fixed call order to enforce. The causal chain: an interface has no instance fields, so it needs no constructor, so `new` never applies to it directly, so nothing needs protecting from concurrent partial initialization — which is exactly why multiple inheritance is safe for it and unsafe for a class. Where you want both — shared convenience without mandating it — publish the interface as the contract and ship an optional abstract "skeletal implementation" (`AbstractList`, `AbstractMap` are the JDK's own examples) that an implementor may use or ignore.

**The 5-minute answer.** The single-inheritance restriction on classes exists because a class carries fields, and a field inherited along two paths would need two initializations into one storage slot — the C++ diamond-of-state problem, closed in Java by simply forbidding a second parent rather than by virtual inheritance. Interfaces sidestep the whole problem: no storage, so no diamond of state is even representable, so multiple inheritance of *behaviour* (Java 8's default methods) is safe while multiple inheritance of *state* remains impossible and always will be, because an interface still cannot declare an instance field. A `default` method is `public` by implicit modifier, dispatched by ordinary virtual dispatch with the interface's body as the fallback when no class in the hierarchy overrides it — and because the implementing class never gets a copy of the code, fixing a default method in the library fixes it for every implementor on the next upgrade with zero recompilation, which is exactly how `Collection` grew `stream()` in Java 8 without breaking every implementation in the world. The abstract-class alternative buys a real cost along with its real benefit: a `final authorise()` template method holding shared idempotency-check state means a subclass gets the lifecycle for free but spends its one inheritance slot and cannot override that method to adapt it — if `CardRailAdapter` later needs to extend a vendor SDK base class instead, the abstract class becomes an obstacle and the interface-plus-delegate escape hatch is the only way out.

```java
interface PaymentRailPort {
    PaymentIntent authorise(Money amount, IdempotencyKey key);
}

abstract class AbstractRailAdapter implements PaymentRailPort {
    private final java.util.Map<IdempotencyKey, PaymentIntent> replay = new java.util.concurrent.ConcurrentHashMap<>();

    @Override
    public final PaymentIntent authorise(Money amount, IdempotencyKey key) {
        PaymentIntent existing = replay.get(key);
        if (existing != null) {
            return existing; // replay check: shared instance state, only an abstract class can own this
        }
        PaymentIntent created = doAuthorise(amount, key);
        replay.put(key, created);
        return created;
    }

    protected abstract PaymentIntent doAuthorise(Money amount, IdempotencyKey key);
}
```

**The follow-up they will ask** — "why can `default` methods not fully replace abstract classes?" Because a default method has no field to hold onto — the moment a shared behaviour needs per-instance mutable state (a retry counter, a cache), that state has nowhere to live on an interface, and reaching for a `static` map keyed by `this` to fake it leaks every instance forever (Q41's mechanism, applied to a static collection instead of a listener registry).

**Where this is written** — [`inheritance-and-dispatch/01b-interfaces.md`](inheritance-and-dispatch/01b-interfaces.md).

### Q38. "Why were default methods added? Resolve a diamond for me."

**The 30-second answer.** Default methods exist so a published interface can grow a new method without breaking every class that already implements it — without them, `Collection.stream()` could not have been added in Java 8 without every existing `Collection` implementation in the world failing to compile. Diamond resolution follows three rules in strict order: a class's own (or inherited) concrete method always beats any interface default; among competing defaults, the most specific interface (the one that extends the other) wins silently; and unrelated defaults with no such relationship is a compile error the developer must resolve explicitly with `Interface.super.method()`.

**The 5-minute answer.** Rule 1's derivation: a concrete class method is a stronger commitment — the class author wrote a body specifically for this class — and if an interface default could beat it, adding a default method to a library interface would silently change the behaviour of an already-working class, exactly the breakage default methods were invented to prevent. This holds even when the class method is inherited from a superclass rather than declared directly, and it has one sharp, memorable consequence: a default method may never override a `public` method of `Object`. Every class implicitly extends `Object`, which supplies concrete `toString`, `equals`, `hashCode` — so for *any* implementing class whatsoever, a `default toString()` would lose to `Object.toString()` under rule 1, making its body unreachable in every possible program; `javac` rejects the declaration outright at the interface's own compilation unit, with `error: default method toString in interface Verdict overrides a member of java.lang.Object` — Q39 below. Rule 2 fires when one declaring interface extends the other: `Restrictable extends Auditable`, both declaring `default String describe()` — `Restrictable.describe()` is a genuine override of `Auditable.describe()` in the ordinary sense, so the more specific one wins with no error and no override required in the implementing class. Rule 3 is the true diamond: two *unrelated* interfaces, `Auditable` and `Restrictable`, both declaring `default String describe()` with no extends relationship between them — `javac` reports `class ClientAction inherits unrelated defaults for describe() from types Auditable and Restrictable` and refuses to compile until the class overrides `describe()` itself, typically delegating explicitly to one or both with `Auditable.super.describe()`. Java 8 added multiple inheritance of *behaviour* only, never of *state* — an interface still cannot declare an instance field, so there is no storage-layout problem to reconcile and the diamond in Java is purely a name-resolution problem with a local, mechanical fix, unlike C++'s virtual-inheritance machinery for the state case.

```java
interface Auditable {
    default String describe() { return "auditable"; }
}

interface Restrictable {
    default String describe() { return "restrictable"; }
}

final class ClientAction implements Auditable, Restrictable {
    @Override
    public String describe() {
        // unrelated defaults: must resolve explicitly, or javac refuses to compile the class
        return Auditable.super.describe() + "/" + Restrictable.super.describe();
    }
}
```

**The follow-up they will ask** — "what if `Restrictable` had instead extended `Auditable`?" Rule 2 applies silently: `Restrictable.describe()` overrides `Auditable.describe()`, the candidates are no longer unrelated, and `ClientAction implements Restrictable` compiles unchanged with no override needed at all — the same two method bodies are either a hard error or completely silent depending only on whether that extends relationship exists.

**Where this is written** — [`inheritance-and-dispatch/01b-interfaces.md`](inheritance-and-dispatch/01b-interfaces.md).

### Q39. "Can a default method override toString?"

**The 30-second answer.** No — it does not compile. `javac` rejects `interface Verdict { default String toString() { return "v"; } }` at the interface's own declaration site with `error: default method toString in interface Verdict overrides a member of java.lang.Object`, with no implementing class in sight. The reason is diamond rule 1 (Q38): every class implicitly extends `Object`, which supplies a concrete `toString`, and a class method always beats an interface default — so the default body could never win in any possible implementing class, and the language refuses to let you write that dead code rather than accept a declaration that can never have an effect.

**The 5-minute answer.** JLS §9.4.1.2 is the source of the rule, and the compiler's own diagnostic states it precisely: the failure is keyed on membership of `Object`, not on the specific method name, so `default boolean equals(Object other)` and `default int hashCode()` are rejected identically, and the diagnostic text says "overrides a member of `java.lang.Object`" rather than naming `toString` specifically. This is not a runtime surprise discovered by testing — it fires at compile time in the interface's own compilation unit, before any class implements it at all, which is the tell that separates it from every other default-method rule in this note set (all of which only bite once a class enters the picture). The one legitimate way to give implementors shared string-formatting logic is to name the method something `Object` does not own, then let each implementor's own `toString` — which every class has by inheritance and can always override — delegate to it.

```java
interface Verdict {
    // Legal: named describe, not toString — Object owns no method called describe.
    default String describe() {
        return "verdict pending";
    }
}

record ScreeningVerdict(String outcome, String reason) implements Verdict {
    @Override
    public String toString() { // records generate this anyway; shown explicitly to make the delegation visible
        return outcome + ": " + describe();
    }

    @Override
    public String describe() {
        return reason;
    }
}
```

```console
error: default method toString in interface Verdict overrides a member of java.lang.Object
interface Verdict { default String toString() { return "v"; } }
                                     ^
```

**The follow-up they will ask** — "so why does `Comparator`'s abstract `boolean equals(Object)` compile fine?" Because it is `abstract`, not `default` — an abstract re-declaration is guaranteed satisfied by `Object`'s own concrete body in every implementing class and adds only documentation, so it is excluded from the single-abstract-method count and `Comparator` remains a valid lambda target; the restriction is specifically on a `default` body, which would be unreachable, not on re-declaring the signature at all.

**Where this is written** — [`inheritance-and-dispatch/01b-interfaces.md`](inheritance-and-dispatch/01b-interfaces.md), [`objects-equality-and-lifecycle/01c-object-methods.md`](objects-equality-and-lifecycle/01c-object-methods.md).

### Q40. "Static nested vs inner class — which do you use and why?"

**The 30-second answer.** Default to static nested and only reach for a (non-static) inner class when the type genuinely needs continuous access to the enclosing instance's state, because an inner class carries a hidden `this$0` reference to its enclosing instance and every constructor takes that instance as an implicit first parameter — a static nested class has neither, needs no receiver to construct (`new Outer.Inner()`), and cannot even write `Outer.this` (compile error: there is no field to read). The inner class exists historically to solve iterators — a `ReservationBook` iterator needing continuous access to the book's internal state without the caller having to pass the book in and store it by hand.

**The 5-minute answer.** The mechanical distinction is entirely about that one synthetic field. `javac 21` emits `this$0` only when the inner class *actually uses* its enclosing instance — verified with two inner classes side by side, one reading an enclosing field and one not: only the first carries `this$0` in `javap -p` output, even though both constructors' descriptors still take the enclosing type as their first parameter. The practical design rule stands regardless of that optimization: still assume an inner class retains a reference, because adding one enclosing-member access in a later edit silently reinstates the field with no visible change at the construction site — that is exactly the shape of the memory-leak trap in Q41. The choice matters beyond bytes: an inner class cannot be instantiated from a static context without a receiver (`non-static variable this cannot be referenced from a static context`), and it cannot be a top-level API type for any framework that instantiates by no-arg reflection, because its only constructor takes the enclosing instance. Since Java 16 (JEP 395, which shipped with records), an inner class may also declare non-constant `static` members and nested records/enums/interfaces — through Java 15 only `static final` compile-time constants were legal, and JDK 11 rejects anything more with `Illegal static declaration in inner class`; the relaxation changed legality, not cost — a type with static members and no need for enclosing state was always telling you it wanted `static class` all along.

```java
final class ReservationBook {
    private final java.util.List<Reservation> reservations = new java.util.ArrayList<>();
    private int modCount = 0;

    // Inner: needs continuous access to reservations and modCount without the caller
    // constructing it with those as explicit constructor arguments.
    final class BookIterator implements java.util.Iterator<Reservation> {
        private int cursor = 0;
        private final int expectedModCount = modCount;

        @Override public boolean hasNext() { return cursor < reservations.size(); }

        @Override public Reservation next() {
            if (modCount != expectedModCount) {
                throw new java.util.ConcurrentModificationException();
            }
            return reservations.get(cursor++);
        }
    }

    // Static nested: a pure value holder, needs nothing from ReservationBook.
    static final class ReservationSummary {
        private final int count;
        private final Money total;

        ReservationSummary(int count, Money total) {
            this.count = count;
            this.total = total;
        }
    }
}
```

**The follow-up they will ask** — "is it true that every inner class holds a reference to its enclosing instance?" Not literally — `javac 21` elides `this$0` when the inner class never touches enclosing state — but treat it as always true for design purposes, because the field silently reappears the moment a future edit adds one enclosing-member read, with no signal anywhere at the call site.

**Where this is written** — [`inheritance-and-dispatch/02-nested-classes.md`](inheritance-and-dispatch/02-nested-classes.md).

### Q41. "How can an anonymous inner class cause a memory leak?"

**The 30-second answer.** An anonymous class declared inside an instance method captures its enclosing instance through a synthetic `this$0` field the moment it touches any enclosing member — and if that anonymous instance is registered somewhere long-lived (a static listener registry, a cache), the retaining edge runs `REGISTRY → AnonymousListener → this$0 → EnclosingService → everything EnclosingService reaches`, silently pinning the whole enclosing object graph for as long as the registration lives, which in a long-running server means forever. Nothing in the registration call site shows this edge exists; it falls purely out of writing `class Listener` instead of `static class Listener`.

**The 5-minute answer.** The trap is invisible by construction: `javac 21` still only emits `this$0` when the anonymous class actually uses enclosing state, so a listener that happens not to touch it today leaks nothing and starts leaking the moment someone adds one field read in an unrelated edit, with the diff showing nothing at the registration line at all. The fix is the mirror image and equally invisible in the diff: convert the inner class to a `static` nested class (or a static anonymous form, passing exactly what's needed through the constructor), and its retained set collapses from the whole enclosing object graph to precisely its constructor arguments — visible on one line, auditable at a glance. A related, sharper trap for `synchronized (this)` inside such a class: `this` inside an anonymous class means the anonymous instance itself, not the enclosing one, so `synchronized (this)` inside `BonusService$1` locks a freshly allocated object no other thread can ever see, providing zero mutual exclusion — `BonusService.this` is required to lock what every other method of `BonusService` locks. **Version fact:** on Java 8, the same registration required `javac` to synthesise a package-private `access$000`-style static forwarder in the enclosing class so the anonymous class could reach a `private` enclosing member across the two separate class files the JVM required; on Java 11 and later, nestmates (JEP 181) let the anonymous class call the private member directly with `invokevirtual`, and no `access$` forwarder appears in the class file at all — but that JEP 181 change affects only *how* the access compiles, not whether the retention leak exists, because `this$0` and the leak it enables are a completely separate mechanism from the private-access repair.

```java
final class ProfileService {
    static final java.util.List<Runnable> LISTENERS = new java.util.ArrayList<>();
    private final AccountId accountId; // one of eight aggregates reachable from this service

    ProfileService(AccountId accountId) {
        this.accountId = accountId;
    }

    // LEAK: anonymous class reads accountId, so it captures `this` via this$0.
    // Registering it in a static list retains this whole ProfileService forever.
    void registerLeaky() {
        LISTENERS.add(new Runnable() {
            @Override public void run() {
                System.out.println("balance changed for " + accountId);
            }
        });
    }

    // FIX: static nested, retained set is exactly the constructor argument.
    static final class BalanceNotifier implements Runnable {
        private final AccountId accountId;
        BalanceNotifier(AccountId accountId) { this.accountId = accountId; }
        @Override public void run() { System.out.println("balance changed for " + accountId); }
    }

    void registerFixed() {
        LISTENERS.add(new BalanceNotifier(accountId)); // retains only accountId, not this ProfileService
    }
}
```

**The follow-up they will ask** — "how do you prove the leak rather than assert it?" A `WeakReference` to the `ProfileService` plus a `ReferenceQueue`, forced GCs, and checking whether the referent clears — cleared for the static-nested version, never cleared for the anonymous-class-in-a-static-list version — is primary evidence; `jcmd <pid> GC.class_histogram` corroborates by showing the live instance count and retained bytes per class, though neither tool shows the retention *path* without a full heap dump and dominator-tree analysis.

**Where this is written** — [`inheritance-and-dispatch/04-internals-nested-classes.md`](inheritance-and-dispatch/04-internals-nested-classes.md), [`build-it/05h-inner-class-retention.md`](build-it/05h-inner-class-retention.md), [`objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`](objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md).

### Q42. "Why must a captured local be effectively final?"

**The 30-second answer.** A captured local is *copied by value* into the lambda or anonymous class's synthetic instance at the moment the lambda is created — `javac` generates one `final val$x` field per captured local, assigned from an appended constructor parameter — because the lambda does not share the enclosing method's stack frame, which may be long gone by the time the lambda actually runs. If the source local could still be reassigned after capture, the lambda's copy and the live variable would diverge with no defensible rule for which one is "right," so the compiler requires the local to be effectively final: never the left-hand side of an assignment expression, never the operand of `++`/`--` after its initializer, anywhere in its scope.

**The 5-minute answer.** JLS §4.12.4's derivation for a local with an initializer: not declared `final`, never occurs as the left-hand side of an assignment expression (the declarator's own initializer does not count, which is what lets an initialized local qualify at all), and never the operand of a prefix or postfix increment/decrement. For a blank local, the parallel rule is that at every assignment it is definitely unassigned and not definitely assigned beforehand — assigned exactly once on every path. Two independent storage locations exist the instant a lambda captures a local: the frame slot in the enclosing method and the `val$x` field in the lambda's target; with no synchronization mechanism between them, keeping them "in step" after either could change independently is not something the language can offer any coherent semantics for, so it forecloses the possibility at compile time instead. The pre-Java-8 rule was blunter and less ergonomic: anonymous inner classes could only capture locals *declared* `final`, which drove developers to litter method bodies with `final` on obviously-never-reassigned variables purely to satisfy the compiler; Java 8 replaced "declared final" with "effectively final," which is a fact the compiler derives about usage rather than a keyword you must remember to write. The common workaround for a mutable accumulator — `int[] counter = new int[1]` — satisfies the rule because the *variable* `counter` is never reassigned, only `counter[0]` is mutated through it, but it introduces a genuine data race if the lambda runs on another thread with no visibility guarantee; the correct fix for a shared mutable count is `LongAdder` or `AtomicInteger`, whose reference is effectively final while their internal state changes safely.

```java
final class StakeLambdaCapture {
    static Runnable settlementTask(RoundId roundId, Money stake) {
        // roundId and stake are effectively final: captured by value into val$roundId, val$stake.
        return () -> System.out.println("settling " + roundId + " for " + stake);
    }

    static Runnable brokenAccumulator() {
        int settledCount = 0;
        // error: local variables referenced from a lambda expression must be final or effectively final
        // return () -> { settledCount++; System.out.println(settledCount); };
        java.util.concurrent.atomic.LongAdder settled = new java.util.concurrent.atomic.LongAdder();
        return () -> { settled.increment(); System.out.println(settled.sum()); }; // settled itself never reassigned
    }
}
```

**The follow-up they will ask** — "does the same rule apply to try-with-resources?" Yes — a resource expression in `try (rail)` must also be final or effectively final, and JLS §4.12.4 additionally lists three variable kinds that are *implicitly* final regardless of usage: an interface field, a try-with-resources resource local, and a multi-catch exception parameter, the last with `javac` reporting `multi-catch parameter failure may not be assigned` on any attempt to write it.

**Where this is written** — [`classes-and-initialization/01a-names-scope-and-var.md`](classes-and-initialization/01a-names-scope-and-var.md), [`inheritance-and-dispatch/04-internals-nested-classes.md`](inheritance-and-dispatch/04-internals-nested-classes.md).

### Q43. "What is this inside a lambda versus inside an anonymous class?"

**The 30-second answer.** Inside an anonymous class, `this` refers to the anonymous instance itself — a real, separately allocated object with its own identity — and reaching the enclosing instance requires the explicit `Outer.this` syntax. Inside a lambda, `this` refers to the *enclosing* instance directly, because a lambda's body compiles to a private method on the enclosing class rather than to a new class of its own, so there is no separate "lambda instance" for `this` to mean.

**The 5-minute answer.** The difference is a direct consequence of how each is compiled, not an arbitrary language rule. An anonymous `Runnable` produces a real class file (`BonusService$1`), loaded eagerly with the enclosing class, holding `this$0` and `val$` synthetic fields exactly as an inner class does, and `this` inside its body means that `BonusService$1` instance. A lambda produces *no class file at all* — its body is compiled into a private method on the enclosing class (`private void lambda$register$0(String)`, verified present as far back as JDK 8's own bytecode), the actual `Consumer`/`Runnable` instance is manufactured lazily at first execution by an `invokedynamic` call site through `LambdaMetafactory`, and a non-capturing lambda's instance can be cached as a singleton because there is no per-evaluation state to distinguish. Because the body is just another method of the enclosing class, `this` inside it is whatever `this` already means at that point in the source — the enclosing instance — with no rebinding at all. This has a sharp, silent trap: converting an anonymous class to a lambda by mechanically deleting boilerplate changes what `this`, `getClass()`, and any `synchronized (this)` block mean. `this.getClass().getName()` inside the anonymous form prints `BonusService$1`; the lambda form has no equivalent expression that names "the lambda" at all, because there is no such object from the source's point of view. `synchronized (this)` inside the anonymous class locks a `BonusService$1` no other thread can ever see — providing zero mutual exclusion for whatever it was meant to guard — while the same code as a lambda body locks the actual `BonusService`, which is the one every other synchronized method of that class would also lock. Nothing about this rebinding produces a compiler warning; the two forms simply mean different things.

```java
final class BonusService {
    private final java.util.Map<ClientId, Bonus> registry = new java.util.HashMap<>();

    Runnable anonymousGrant(ClientId clientId) {
        return new Runnable() {
            @Override public void run() {
                // this == this Runnable instance (BonusService$1); enclosing instance needs BonusService.this
                synchronized (BonusService.this) {
                    System.out.println(this.getClass().getSimpleName() + " granting for " + clientId);
                }
            }
        };
    }

    Runnable lambdaGrant(ClientId clientId) {
        return () -> {
            // this == the enclosing BonusService directly; body compiled as a private method on it
            synchronized (this) {
                System.out.println("granting for " + clientId + " via " + this.registry.size() + " entries");
            }
        };
    }
}
```

**The follow-up they will ask** — "why does this matter operationally, not just semantically?" Because `synchronized (this)` inside an anonymous class is a common silent no-op — the guard compiles cleanly, runs without error, and provides no mutual exclusion whatsoever, which is exactly the kind of concurrency bug that survives every test run and shows up only under real contention.

**Where this is written** — [`inheritance-and-dispatch/02-nested-classes.md`](inheritance-and-dispatch/02-nested-classes.md), [`inheritance-and-dispatch/04-internals-nested-classes.md`](inheritance-and-dispatch/04-internals-nested-classes.md).

### Q44. "Why is an enum the best singleton?"

**The 30-second answer.** A hand-rolled singleton needs a `private` constructor, a `static final` instance, and — if it must survive serialization — a correctly-written `readResolve`, and even a correct `readResolve` does not stop `Constructor.setAccessible(true)` from reflectively minting a second instance. An enum singleton closes every one of those doors structurally rather than by convention: reflection's `Constructor.newInstance` refuses any constructor of an `ACC_ENUM` class outright with `IllegalArgumentException: Cannot reflectively create enum objects` — `setAccessible(true)` succeeds but does not help, because the refusal is hard-coded, not an accessibility check — serialization writes the constant's name and resolves it through `Enum.valueOf`, so no instance is ever constructed on the wire and there is nothing for `readResolve` to fix, and `Enum.clone()` is `protected final` and unconditionally throws `CloneNotSupportedException`.

**The 5-minute answer.** Each defence closes a specific attack the hand-rolled version leaves open. Reflection: on the classic `enum`-free singleton, `setAccessible(true)` on the `private` constructor followed by `newInstance()` successfully forges a second instance; on an enum, the JVM's own enum-construction check refuses at the `Constructor.newInstance` call itself. Serialization: the Java Object Serialization Specification defines the enum wire form as `name()` alone, and `ObjectOutputStream` writes a `TC_ENUM` marker plus that name — measured as an 81-byte stream for one constant, containing the literal text of its name and nothing else; `ObjectInputStream` reads the name back and calls `Enum.valueOf(enumType, name)`, which returns the *existing* constant with **no constructor invocation at all** for the deserialized value — the standard customization hooks `writeReplace`, `readResolve`, and `readObject` are all specified as ignored for enum types, and `java.lang.Enum` reinforces this from the other side with its own `private readObject`/`readObjectNoData`, both throwing `InvalidObjectException("can't deserialize enum")` if a crafted stream tries the field-by-field path anyway. A `readResolve` written on an enum constant compiles, is harmless, and is simply never called — it teaches the next reader a false mental model of how enum deserialization works. Cloning: `Enum.clone()` is `protected final Object clone() throws CloneNotSupportedException` and unconditionally throws, with the javadoc stating the reason directly: enum constants "are never cloned, which is necessary to preserve their singleton status." The one door that does open is `sun.misc.Unsafe.allocateInstance`, which bypasses every constructor and can produce a zeroed instance with `name() == null`, `ordinal() == 0`, equal to nothing and absent from `values()` — but that is not a singleton-pattern hole, it is the difference between "the JVM enforces this" and "the supported API enforces this," and anything holding `Unsafe` has already won by other means.

```java
public enum ScreeningService {
    INSTANCE;

    private final java.util.Map<ClientId, ScreeningVerdict> cache = new java.util.concurrent.ConcurrentHashMap<>();

    public ScreeningVerdict screen(ClientId clientId) {
        return cache.computeIfAbsent(clientId, id -> new ScreeningVerdict(
                "CLEAR", "no match", java.time.Instant.now(), "watchlist-provider"));
    }
    // No readResolve needed: deserialization resolves by name via Enum.valueOf, never runs a constructor.
}
```

**The follow-up they will ask** — "is the enum singleton immune to everything?" To reflection, serialization and cloning through every supported API, yes; `Unsafe.allocateInstance` can still forge a null-named, ordinal-0 object outside `values()`, but that requires `Unsafe` access, at which point the attacker can corrupt arbitrary object state regardless of the singleton pattern chosen.

**Where this is written** — [`build-it/03g-enum-singleton.md`](build-it/03g-enum-singleton.md), [`enums/01c-production-patterns-and-guarantees.md`](enums/01c-production-patterns-and-guarantees.md), [`enums/03d-internals-enum-evolution.md`](enums/03d-internals-enum-evolution.md).

### Q45. "What does values() actually return, and why should you cache it?"

**The 30-second answer.** `values()` is not an accessor, it is a factory: its generated body is exactly four instructions — `getstatic $VALUES`, `invokevirtual` the array's `clone()`, `checkcast`, `areturn` — so it allocates and returns a fresh, shallow-copied array on **every single call**, forever, with no cache and no branch anywhere in the generated code. For a ten-constant enum that is a 56-byte allocation per call; at QuizStakes's 2.8M/day, 1,200/sec-peak stake reservation volume, calling `values()` once per reservation to scan for a blocking restriction allocates roughly 67 MB/day of pure, immediately-dead garbage for no reason beyond convenience — cache the result once in a `private static final` field, or use `EnumSet`, which reads the JVM's own shared, never-cloned copy.

**The 5-minute answer.** The reason it must copy rather than share is structural: exactly one array of constants exists at rest — `private static final E[] $VALUES`, `ACC_SYNTHETIC` — and Java arrays are mutable with no immutable variant, so if `values()` returned the real array, `RestrictionType.values()[7] = null` would corrupt the one backing array that `EnumSet`, `EnumMap`, and every other caller reads from, with no way to prevent it at the type level; defensive copying on every call is the only correct implementation given that constraint. The clone is shallow — the ten slots in the fresh array hold the *same* ten constant references, so the per-call cost is one array allocation plus an `arraycopy`, not ten object allocations, which is exactly why the cost is invisible in a microbenchmark of a single call and lethal only in a loop: the enhanced-`for` idiom `for (RestrictionType t : RestrictionType.values())` desugars to a local holding the method-call result, hiding the allocation completely behind syntax that reads like it iterates a constant. There is exactly one place a shared, never-recloned copy exists: `Class.getEnumConstantsShared()`, gated on `isEnum()` (which requires both `ACC_ENUM` and `getSuperclass() == Enum.class`), bootstraps its cache by *reflectively invoking your generated `values()` once* and keeping that clone forever; `EnumSet.allOf` and `new EnumMap<>(type)` read through that shared copy via `SharedSecrets`, which is exactly why they allocate no universe array at all, while the public `Class.getEnumConstants()` clones again before returning to a caller and therefore costs the same as `values()`. **Version fact confirmed on JDK 21.0.7:** declaring a `VALUES` field before the enum's own constants is `error: illegal forward reference` at **compile time**, never a runtime NPE — `$VALUES` (the compiler's own synthetic field) is assigned *last* in `<clinit>`, strictly after every constant field, which is why a static lookup map built from `values()` must live in a `static` block (running after `<clinit>`'s constant-creation phase) and never in a constructor (running during it, when `$VALUES` is still `null` and `getstatic; invokevirtual clone()` on it throws `NullPointerException`).

```java
final class RestrictionScan {
    // Cached once, at class init — the only allocation ever paid for this array.
    private static final RestrictionType[] TYPES = RestrictionType.values();

    static boolean anyBlocking(java.util.Set<RestrictionType> active) {
        for (RestrictionType type : TYPES) { // reuses the cached array — allocates nothing per call
            if (active.contains(type) && type.name().endsWith("BLOCKED")) {
                return true;
            }
        }
        return false;
    }

    static boolean anyBlockingSlow(java.util.Set<RestrictionType> active) {
        for (RestrictionType type : RestrictionType.values()) { // allocates a fresh array EVERY call
            if (active.contains(type) && type.name().endsWith("BLOCKED")) {
                return true;
            }
        }
        return false;
    }
}
```

**The follow-up they will ask** — "is `EnumSet.allOf` just `values()` in disguise?" No — `EnumSet` and `EnumMap` are trusted internal callers that read `Class`'s shared, never-recloned cache directly through `SharedSecrets`, so `EnumSet.allOf(RestrictionType.class)` allocates no per-call universe array at all, unlike `values()`, which clones unconditionally on every invocation.

**Where this is written** — [`enums/01a-implicit-members-and-identity.md`](enums/01a-implicit-members-and-identity.md), [`enums/03a-internals-enum-members.md`](enums/03a-internals-enum-members.md), [`build-it/03b-enum-values-cache-and-diff.md`](build-it/03b-enum-values-cache-and-diff.md).

### Q46. "Why should you never persist ordinal()?"

**The 30-second answer.** `ordinal()` is a *declaration index*, not an identifier — it is the constant's zero-based position in the source file, assigned by the JVM at class-initialization time, and it has no relationship to what the constant means. Insert a new constant anywhere but the end of the declaration list, or reorder two existing ones, and every ordinal from that point on silently shifts to mean a different constant — a database row, a Kafka message, or a serialized session written under the old ordinal now decodes as the wrong value with no exception, no warning, and no log line, because the read succeeds and simply returns the wrong enum constant.

**The 5-minute answer.** The bug is invisible precisely because nothing fails: `RestrictionType.values()[storedOrdinal]` is a valid array access for any in-range integer, so a `STAKE_BLOCKED` row written as ordinal `3` reads back as whatever constant now occupies slot 3 after a reorder — silently becoming `WITHDRAWAL_HELD` or any other type, with the application logic proceeding as if that were always correct. This is exactly the failure mode JPA's `@Enumerated` annotation defaults to: its bare form means `EnumType.ORDINAL`, and nothing in the annotation's name suggests it picked the fragile option — an `int` column is genuinely smaller and faster to index, so the choice looks like a considered optimization rather than a default nobody actively chose. The structural fix is the production enum pattern: a `final` code field declared directly in the constant list, owned by the enum and immune to reordering, backed by a `static final Map<String, E>` built in a `static` block (never the constructor — `values()` is only safe to call once `<clinit>`'s constant-creation phase is complete, per Q45) with a `map.put(code, constant) != null` duplicate check that turns a copy-pasted code into a startup-time class-initialization failure rather than a silently-lost mapping, `Map.copyOf` on assignment against caller mutation, an `Optional`-returning lookup (never `valueOf`, which throws `IllegalArgumentException` — a `fillInStackTrace` cost per bad input, and a cheap denial-of-service amplification vector on any endpoint that accepts the raw string), and an explicit JPA `AttributeConverter` at the persistence boundary so a bare `@Enumerated` can never reintroduce the ordinal by accident. `@Enumerated(EnumType.STRING)` is the acceptable middle ground — safe against reordering, not against renaming, and it ties the column width to the longest identifier (`SOURCE_OF_FUNDS_REQUIRED` is 24 characters), which a narrower column silently truncates or rejects depending on the database's strictness.

```java
enum RestrictionType {
    DEPOSIT_BLOCKED("RT-01"),
    STAKE_BLOCKED("RT-02"),
    WITHDRAWAL_BLOCKED("RT-03"),
    WITHDRAWAL_HELD("RT-04");

    private static final java.util.Map<String, RestrictionType> BY_CODE;
    static {
        java.util.Map<String, RestrictionType> byCode = new java.util.HashMap<>();
        for (RestrictionType type : values()) { // safe here: static block runs after <clinit>'s constant phase
            if (byCode.put(type.code, type) != null) {
                throw new ExceptionInInitializerError("duplicate code " + type.code);
            }
        }
        BY_CODE = java.util.Map.copyOf(byCode);
    }

    private final String code; // persisted identity, immune to reordering — never the ordinal

    RestrictionType(String code) { this.code = code; }

    String code() { return code; }

    static java.util.Optional<RestrictionType> fromCode(String code) {
        return java.util.Optional.ofNullable(BY_CODE.get(code));
    }
}
```

**The follow-up they will ask** — "does `Unsafe.allocateInstance` change this analysis?" No — that is a separate, unrelated attack surface (Q44); the ordinal fragility exists purely from ordinary reordering during ordinary maintenance, with no reflection or attacker involved at all, which is precisely what makes it the more common production incident of the two.

**Where this is written** — [`enums/01c-production-patterns-and-guarantees.md`](enums/01c-production-patterns-and-guarantees.md), [`build-it/03k-persisted-code-enum.md`](build-it/03k-persisted-code-enum.md).

### Q47. "What does the compiler generate for an enum, and what is $SwitchMap?"

**The 30-second answer.** `javac` generates, per enum: `ACC_ENUM` on the class and on every constant field; a `private static final E[] $VALUES` (`ACC_SYNTHETIC`); a public, non-synthetic `values()` that is `$VALUES.clone()`; a public, non-synthetic `valueOf(String)` that delegates to `Enum.valueOf`; a `private` constructor whose real descriptor prepends `(String name, int ordinal)` before your own parameters; and a `<clinit>` that constructs every constant, in declaration order, and assigns `$VALUES` **last**. `$SwitchMap` is a separate, per-*switching-class* synthetic `int[]`, cached in its own generated holder class, indexed by `ordinal()` and populated by constant *name* at class-init time — it exists so that an enum `switch`, compiled once against one ordering of constants, keeps routing correctly even if the enum is later recompiled with its constants reordered, as long as the switching class itself is not recompiled.

**The 5-minute answer.** The `<clinit>` ordering is the single fact that answers three different questions at once. `$VALUES` assigned last means it is `null` during every constant's own construction, which is exactly why calling `values()` from an enum constructor throws `NullPointerException` (`getstatic $VALUES` pushes `null`, `invokevirtual clone()` on `null` fails) while calling it from a `static` block works fine (static initializers run strictly after `$VALUES`'s assignment) — the same fact underlying the `illegal forward reference` compile error in Q45 for a `VALUES` field declared before the constants. On JDK 17 and 21, the array-building `anewarray`/`aastore` sequence is factored out of `<clinit>` into a private synthetic `static E[] $values()` method, shrinking `<clinit>`'s own `Code` attribute by roughly a third for a ten-constant enum — relevant because a method's `Code` attribute is capped at 65,535 bytes and `<clinit>` also holds every static initializer, so the refactor raises the constant count at which a very large enum stops compiling; JDK 8 and 11 keep the array build inline. `values()`'s own four-instruction body is byte-for-byte identical across JDK 8 through 21 regardless. `$SwitchMap` addresses a genuinely separate problem: an enum `switch` cannot simply `lookupswitch` on the constant object itself, so `javac` compiles it to `lookupswitch` against `$SwitchMap[ordinal()]` — a synthetic `static final int[]` living in its own per-switching-class holder — where the map is *populated by constant name*, one `case` per constant wrapped individually in `try { $SwitchMap[RestrictionType.X.ordinal()] = 1; } catch (NoSuchFieldError ignored) {}`, guarding against a constant that has been removed from the enum since the switching class was last compiled. Because the map is filled by name and read by ordinal, recompiling only the enum with its constants reordered and redeploying that jar **without recompiling the switching class** still routes every case correctly — the switching class's `$SwitchMap` is rebuilt fresh from the new enum's ordinals at its own class-init time, on every JVM start, so a stale `$SwitchMap` from a previous run is never an issue either.

```java
enum RestrictionSource { SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, ADMIN, CLIENT }

final class RestrictionRouter {
    static String routeFor(RestrictionSource source) {
        // javac compiles this to: lookupswitch on a synthetic $SwitchMap$RestrictionSource[source.ordinal()]
        return switch (source) {
            case SYSTEM_ONBOARDING -> "auto-lift at AA-801";
            case SYSTEM_COMPLIANCE -> "manual review required";
            case ADMIN -> "operator-managed";
            case CLIENT -> "self-service";
        };
    }
}
```

**The follow-up they will ask** — "if the enum's JAR is redeployed with constants reordered but the switching class's JAR is not recompiled, does the switch still route correctly?" Yes, and it is provable from the mechanism: `$SwitchMap` is rebuilt at the switching class's own `<clinit>` time on every JVM start, populated by name against whatever ordinals the currently-loaded enum reports — the map is never a stale artifact carried over from a previous compile, only from a previous *run*, and it is rebuilt fresh at every run.

**Where this is written** — [`enums/03-internals-enums.md`](enums/03-internals-enums.md), [`enums/03b-internals-guarantees-and-switch.md`](enums/03b-internals-guarantees-and-switch.md), [`control-flow/01b-string-and-enum-switch.md`](control-flow/01b-string-and-enum-switch.md).

### Q48. "How do you write a genuinely immutable class? Both defensive copies, please."

**The 30-second answer.** Five rules, and the two people forget are the two that actually get exploited: (1) `final class` (or a private constructor with static factories) so no subclass can widen behaviour; (2) every field `private final`; (3) no mutators — state changes produce a new instance; (4) defensive-copy every mutable constructor argument **in**, in the order null-check, copy, then validate the copy (never the parameter) — this order matters because it closes the window rather than narrowing it, since nothing can change between validation and storage when validation reads the field that was already stored; (5) defensive-copy or wrap every mutable field **out** on the way through an accessor — return the field directly at zero cost when it is already immutable (a `List.copyOf` result, a `Money`, a record), or `List.copyOf(field)` per call only when the field was deliberately kept as a mutable type.

**The 5-minute answer.** Rules 1–3 are the ones every candidate recites and the ones that alone still leave a class fully mutable — `final class`, three `private final` fields, no method named `set` anywhere, and the class can still be mutated in both directions if any field is a mutable type and neither copy is done. The behavioural definition to lead with: no sequence of calls from any caller in any thread changes what the object reports, and `final` on a field reference says nothing about whether the object at the far end of that reference can change — a perfectly sealed box can still hand out a live key to its own insides. Rule 4's ordering, proven rather than asserted: given `PaymentRun(String runId, List<String> withdrawalIds)`, the wrong order is validate-then-copy, because between the validation read and the field assignment there is a window during which the caller's original list — the one that was actually validated — can be mutated by another thread, and the field ends up holding a *different*, unvalidated snapshot; validated `[WD-9001, WD-9002]`, stored `[WD-9001, WD-9002, WD-7777]` with `WD-7777` carrying `WITHDRAWAL_BLOCKED` that was never checked. Copy-then-validate removes the window entirely rather than narrowing it: after `this.withdrawalIds = List.copyOf(withdrawalIds)` returns, the field references an object no other thread has ever had a reference to, so validating `this.withdrawalIds` next is validating exactly the object that will be read forever after — there is no interval during which the validated object and the stored object could differ, because they are the same object by the time validation runs. Rule 5's asymmetry, worked on the read side: return the field directly, allocating nothing, when the field's own type is already immutable (the default, and the common case when rule 4 was done correctly); reach for a per-call `List.copyOf(field)` only when the field is a mutable type kept mutable on purpose — which is itself usually a sign rule 4 was skipped, since there is rarely a reason to store a raw `ArrayList` in an immutable class. The trap specific to rule 5: `Collections.unmodifiableList(field)` makes the *returned reference* refuse writes and nothing else — it is a read-only *view*, not an immutable *copy* — so if the backing `ArrayList` the field wraps is still writable from inside the class (a `recalculate()` method) or from wherever the constructor got it, two calls to the accessor's `.size()` can disagree with no intervening call on the object at all, which is the exact behavioural definition of immutability failing even though `entries().add(...)` correctly throws.

```java
/** A signed-off batch of bank withdrawals. Once constructed, its membership never moves. */
final class PaymentRun {
    private final String runId;
    private final java.util.List<String> withdrawalIds;

    PaymentRun(String runId, java.util.List<String> withdrawalIds) {
        this.runId = java.util.Objects.requireNonNull(runId, "runId must not be null");
        // 1. null check, 2. copy, 3. validate the COPY (never the parameter) — in that exact order.
        java.util.Objects.requireNonNull(withdrawalIds, "withdrawalIds must not be null");
        this.withdrawalIds = java.util.List.copyOf(withdrawalIds);            // copy in
        validateNoneBlocked(this.withdrawalIds);                             // validates the stored copy
    }

    private static void validateNoneBlocked(java.util.List<String> ids) {
        if (ids.contains("WD-7777")) { // stand-in for a real WITHDRAWAL_BLOCKED lookup
            throw new IllegalStateException("PaymentRun cannot include a blocked withdrawal");
        }
    }

    String runId() { return runId; }

    java.util.List<String> withdrawalIds() {
        return withdrawalIds; // copy out is free here: withdrawalIds is already a List.copyOf result
    }
}
```

**The follow-up they will ask** — "when is a per-call copy-out actually load-bearing?" Only when the field was deliberately left mutable — for example a `Movement` that recomputes an internal `ArrayList` of entries on demand — in which case `List.copyOf(entries)` on each accessor call trades an allocation (24 bytes for a two-element list, roughly 326 KB/sec at the ledger's peak 13,600 writes/sec) for a guarantee that a `List.copyOf`-backed field already provides for free; reaching for it on an already-immutable field is the most common way this rule gets over-applied.

**Where this is written** — [`immutability-and-design/02-immutability.md`](immutability-and-design/02-immutability.md), [`immutability-and-design/02a-shallow-deep-and-building-blocks.md`](immutability-and-design/02a-shallow-deep-and-building-blocks.md), [`build-it/04a-defensive-copying-and-collections.md`](build-it/04a-defensive-copying-and-collections.md).

---

**Leaves covered:** 5.1.33–5.1.48 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 558
