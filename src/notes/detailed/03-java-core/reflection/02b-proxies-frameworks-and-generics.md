# 03 Java Core — Reflection: proxies, frameworks and generics — INTERMEDIATE (§2.12, 2.12.7–2.12.9)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Access, cost and method handles](02a-access-cost-and-method-handles.md) · Next: [Final fields and the security surface](02c-final-fields-and-security-surface.md)

`02-reflection.md` owns `Class` objects, the naming methods and member lookup; `02a-access-cost-and-method-handles.md` owns `setAccessible`, cost and the handle layer; this file owns dynamic proxies, where reflection actually appears in a Spring Boot stack, and what survives erasure; `02c-final-fields-and-security-surface.md` closes §2.12 with reflective `final`-field writes and the security surface. The question this file answers, in bold: **how does a framework make an object that is not the class you wrote, and how much of your generic signature can it still read at runtime?**

## 1. Dynamic proxies (2.12.7)

A `java.lang.reflect.Proxy` is not a hand-written wrapper and not subclassing. `Proxy.newProxyInstance` generates a class at runtime — a real `.class` structure, materialised in memory, never written to disk — whose every method body does the same three things: box the call's arguments into an `Object[]`, hand them to one `InvocationHandler`, and cast whatever comes back to the declared return type. Every method on every interface you named collapses to that one indirection. There is no per-method logic in the generated class at all; all of it lives in your handler.

### Why it exists

Frameworks need to intercept method calls on types they did not write and cannot subclass safely — a `@Transactional` service interface, a mock in a test, an RMI stub. Writing a hand-coded delegator for every interface a framework might ever see does not scale; generating the delegator from the interface list at runtime does.

### How it works

`Proxy.newProxyInstance(ClassLoader loader, Class<?>[] interfaces, InvocationHandler h)` takes three arguments. The `ClassLoader` matters more than it looks: it defines where the generated class lives and therefore which types it can even reference (link `../classes-and-initialization/03b-internals-class-loaders-and-identity.md`). The interface array is the complete contract the generated class implements. The handler is where every call actually lands.

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64, for a proxy over a `Ledger` interface (`long post(String position, long minor)`):

| Query | Measured result |
|---|---|
| `p.getClass().getName()` | `$Proxy0` |
| `Proxy.isProxyClass(p.getClass())` | `true` |
| `p.getClass().getSuperclass().getName()` | `java.lang.reflect.Proxy` |
| `p.getClass().getDeclaredMethods().length` | `5` |
| `((Ledger) p).post("CLIENT_CASH_AVAILABLE", 6500)` | handler printed `handler saw post declaredBy=VerB$Ledger`, returned `1` |
| `p.toString()` | handler printed `handler saw toString declaredBy=java.lang.Object`, returned `LedgerProxy` |
| `Proxy.newProxyInstance(loader, new Class<?>[]{ SomeClass.class }, handler)` | `java.lang.IllegalArgumentException: VerB$Restriction is not an interface` |

**The superclass is `Proxy`, and that single fact is the entire interface-only limitation.** Java has single inheritance of implementation; the generated class has already spent its one superclass slot on `java.lang.reflect.Proxy`, so it cannot also extend a class of yours. That is not a policy decision the JDK team made and could relax — it falls straight out of `extends` being single-valued, which is why passing a class instead of an interface fails immediately, with the measured `VerB$Restriction is not an interface` message, before any proxy is even generated.

`InvocationHandler.invoke(Object proxy, Method method, Object[] args)` has three details that catch people. `args` is `null`, not an empty array, for a no-argument method — a handler that does `args.length` unconditionally throws `NullPointerException` on `toString()` and `hashCode()`. The `proxy` parameter is the proxy object itself, so calling a method on it from inside the handler recurses straight back into `invoke`. And the return value is a bare `Object`, so the generated code performs the cast — which is where the trap below comes from.

**`toString`, `hashCode` and `equals` are routed to your handler too**, and this is the concept's whole point. The measured `declaredBy` values prove it: `VerB$Ledger` for `post`, `java.lang.Object` for `toString`. Three consequences follow. First, a handler that does not implement all three throws for something as innocent as putting the proxy in a `HashSet` or logging it. Second, a handler that implements `equals` by delegating to the target object breaks the symmetry half of the `equals` contract — `proxy.equals(target)` can be `true` while `target.equals(proxy)` is `false`, because `target`'s own `equals` has never heard of the proxy (link `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`). Third — **Insight:** a debugger or a logger calling `toString()` on a proxied bean runs your interception logic, which is exactly how a badly written `@Transactional` proxy can open a database transaction because someone hovered a variable in a debugger.

**The `ClassCastException` trap**, reproduced from an earlier buggy version of the same harness that returned a boxed `Long` from the `hashCode` branch:

```
java.lang.ClassCastException: class java.lang.Long cannot be cast to class java.lang.Integer (java.lang.Long and java.lang.Integer are in module java.base of loader 'bootstrap')
	at $Proxy0.hashCode(Unknown Source)
	at VerB.main(VerB.java:52)
```

`InvocationHandler.invoke` returns `Object`, so the compiler cannot check that a `hashCode` branch returns something castable to `int`; the generated proxy performs that cast at the call site and fails there, one frame removed from the mistake. Note `$Proxy0.hashCode(Unknown Source)` — the proxy class has no source file, hence no line number, which is the real operational cost of proxies: unreadable stack traces (link `../exceptions/03b-internals-stack-trace-capture.md`).

**Subclass proxies** are the alternative when there is no interface to proxy — CGLIB (bundled inside Spring for exactly this) and ByteBuddy both generate a real subclass and override methods, rather than implementing an interface:

| Mechanism | Needs an interface | What it cannot intercept | What it needs from the target | Where it fails |
|---|---|---|---|---|
| `java.lang.reflect.Proxy` | Yes | Nothing on the named interfaces — every interface method routes to the handler | Nothing beyond the interface list | Passing a class instead of an interface: measured `IllegalArgumentException` |
| CGLIB subclass proxy | No | `final` methods, `private` methods, `static` methods, calls made from inside the target via `this` (self-invocation) | A non-`final` class; historically an accessible constructor | Target class marked `final`, or a call routed through `this` rather than the proxy |
| ByteBuddy subclass proxy | No | Same shape of limits as CGLIB — anything the JVM already resolved statically before the override could run | A non-`final` class | Same self-invocation problem |
| Hand-written decorator | No (wraps by composition) | Nothing structurally, but you write and maintain every delegating method by hand | Nothing — it is ordinary code | Scales badly: N methods, N delegations, by hand |

**Unverified:** the exact proxy strategy Spring's container selects by default, and current-version specifics of how CGLIB is bundled inside `spring-core`, are not asserted here — guide 07 (Spring core) owns the container's proxying strategy in full; this file gives you the mechanism so the interview question lands cold.

The self-invocation problem is the single most-asked proxy question in Spring interviews, and it follows directly from "a subclass proxy overrides methods." Picture `PaymentService.settleStake` calling `this.recordMovement(movement)`, where `recordMovement` carries `@Transactional`. The container wraps `PaymentService` in a proxy — a *different object* that delegates to the real one. But inside `settleStake`, `this` is the real `PaymentService`, not the proxy, because `this` is bound at the call site the compiler generated, not by the container. The call to `recordMovement` therefore never passes through the proxy, the interception never fires, and the transaction is silently absent — no exception, just missing behaviour. Three fixes, with their costs: extract `recordMovement` into a second bean and inject that bean (clean, but adds a class); self-inject the proxy into `PaymentService` and call through it (works, but the class now depends on its own proxy, which reads oddly); or switch to load-time weaving/AspectJ, which intercepts at the bytecode level regardless of how the call is made (heaviest to configure, but removes the whole problem class). Guide 07 (Spring core) owns the container's side of this in full.

Tie back to `02-reflection.md`: on a proxied bean, `obj.getClass()` returns `$Proxy0` or a CGLIB-generated name, never your declared class, which is why `getClass().getSimpleName()` in a log line and `getClass().getAnnotation(SomeAnnotation.class)` both surprise people who expected their own type back.

```java
package quizstakes.reflection;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

interface Ledger {
    long post(String position, long minorUnits);
    long balance(String position);
}

final class LedgerImpl implements Ledger {
    private final ConcurrentHashMap<String, Long> balances = new ConcurrentHashMap<>();

    @Override
    public long post(String position, long minorUnits) {
        return balances.merge(position, minorUnits, Long::sum);
    }

    @Override
    public long balance(String position) {
        return balances.getOrDefault(position, 0L);
    }
}

final class RestrictedIdempotentLedgerHandler implements InvocationHandler {
    private final Ledger target;
    private final Set<String> restrictedPositions;
    private final Set<UUID> seenKeys = ConcurrentHashMap.newKeySet();

    RestrictedIdempotentLedgerHandler(Ledger target, Set<String> restrictedPositions) {
        this.target = target;
        this.restrictedPositions = restrictedPositions;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        Object[] safeArgs = args == null ? new Object[0] : args;
        switch (method.getName()) {
            case "toString" -> { return "LedgerProxy[" + target + "]"; }
            case "hashCode" -> { return System.identityHashCode(proxy); }
            case "equals" -> { return proxy == safeArgs[0]; }
            default -> { }
        }
        if ("post".equals(method.getName())) {
            String position = (String) safeArgs[0];
            if (restrictedPositions.contains(position)) {
                throw new IllegalStateException("position restricted: " + position);
            }
        }
        try {
            return method.invoke(target, safeArgs);
        } catch (InvocationTargetException wrapped) {
            throw Objects.requireNonNullElse(wrapped.getCause(), wrapped);
        }
    }
}

final class LedgerProxyFactory {
    static Ledger idempotentLedger(Ledger target, Set<String> restrictedPositions) {
        return (Ledger) Proxy.newProxyInstance(
                LedgerProxyFactory.class.getClassLoader(),
                new Class<?>[] { Ledger.class },
                new RestrictedIdempotentLedgerHandler(target, restrictedPositions));
    }
}
```

**Pitfall:** the unwrapping of `InvocationTargetException` in that handler is not defensive dressing — `Method.invoke` wraps every checked and unchecked exception the target throws inside an `InvocationTargetException`, so a handler that rethrows it directly hands the caller a wrapper exception with the wrong type and the wrong message, and every `catch (InsufficientFundsException e)` downstream silently stops matching (link `../exceptions/01a-throwable-api-and-chaining.md`).

> A JDK dynamic proxy is a runtime-generated class, limited to implementing named interfaces because it has already spent its single superclass slot on `Proxy`, that routes every method call — including `equals`, `hashCode` and `toString` — through one `InvocationHandler`.

## 2. Where reflection actually shows up in your stack (2.12.8)

Every framework in a Spring Boot service is a program that reads your code as data. Annotations do nothing by themselves — `@Transactional` is inert metadata sitting in a class-file attribute until something scans for it (link `../language-substrate/02-packages-modules-annotations.md`). "Where does reflection show up" really asks: at which points does a library stop trusting the compiler and start inspecting bytes? Four moments recur across every framework: **discovery** (finding the types), **binding** (matching a name to a member), **construction** (making an instance), and **invocation** (calling it).

| Framework | What it discovers | What it binds | How it constructs | What it needs from you |
|---|---|---|---|---|
| Spring | Component-scans the classpath reading class files (not loading them, for speed) for annotated candidates | `getDeclaredConstructors` for constructor injection, `getDeclaredFields` for `@Autowired` field injection | A bean instance via the chosen constructor, then a possible AOP proxy wrapping it | A non-`final` class if a CGLIB proxy is needed; `-parameters` or an explicit `@Qualifier`/`@Param` name for injection by parameter name |
| Jackson | `getDeclaredMethods` for getter/setter naming conventions, `getDeclaredFields` for field-backed properties | A JSON property name to a field, setter, or constructor parameter | A no-arg constructor, an `@JsonCreator`-annotated constructor, or — measured available on 21 — `getRecordComponents()` for records | Either a default constructor or an explicit creator; correct visibility for the members it reads |
| JPA/Hibernate | `getDeclaredFields` for field-access entities | A column name to a field | A **required no-arg constructor** on the entity | A no-arg constructor (why a record cannot be a JPA entity — link `../records-and-sealed/01a-object-methods-sealed-and-fit.md`); non-`final` class for lazy-loading proxies |
| JUnit 5 | `@Test`-annotated methods by annotation presence | A test method to its declaring class | A fresh test instance per test method via `getDeclaredConstructor` | Package/class/method visibility JUnit can call via `setAccessible` |
| Mockito | The type being mocked, and every method on it | A stubbed call to the method it was stubbed against | Generates a subclass, or — with the inline mock maker — instruments bytecode directly | Non-`final` methods and classes for the default subclass mock maker |

**Spring** and parameter names are the single most concrete "what does the compiler flag buy me" fact in this file. Without `-parameters`, `getParameters()[0].getName()` returns `arg0`, measured as `isNamePresent()` = `false`; recompiled with `-parameters`, the same call returns the real name and `isNamePresent()` = `true`. That is why Spring Boot's own build plugins enable `-parameters` by default — without it, `@RequestParam` and constructor injection by name have nothing to bind against and fall back to explicit `@Qualifier`/`@Param` annotations.

**Jackson**'s two null-adjacent traps are handled elsewhere by reference: the difference between an absent field and an explicit `null` is guide 12's (API design) territory, and Jackson's polymorphic-type handling during deserialization is a separate attack surface that ordinary serialization filters do **not** cover (link `../serialization/02c-attack-surface-filters-and-the-practical-rule.md`).

**JPA/Hibernate**'s lazy-loading proxy has the same `getClass()` consequence as Concept 1: the proxy's `getClass()` is not your entity class, which is exactly why a hand-written `equals` using `getClass() != other.getClass()` breaks entity equality across a lazy reference and an eagerly loaded one. Guide 08 (Spring Data JPA) owns this in full.

**JUnit 5** and **Mockito** are guide 16's (Testing) territory in full detail; the fact worth keeping here is that Mockito's inability to mock a `final` method or a `static` method with the default subclass mock maker is not a Mockito limitation invented in its docs — it is the exact self-invocation-adjacent constraint from Concept 1's subclass-proxy row, which is *why* the inline mock maker (bytecode instrumentation, not subclassing) exists as an alternative.

Every one of these frameworks resolves its reflective metadata **once** and caches it — Spring at context startup, Jackson at `ObjectMapper` configuration, Hibernate at entity-manager-factory build — because `02a-access-cost-and-method-handles.md`'s measured per-call cost (`Method.invoke` ≈ 4.5 ns/op, `setAccessible(true)` ≈ 3.2–3.4 ns/op) is a cost worth paying once, not per row. In QuizStakes terms: at ~19.8M ledger entries/day, a Jackson serializer that resolved `getDeclaredFields()` per row instead of once at startup would allocate roughly 19.8M arrays and ~79M `Field` objects a day for a four-field row — pure per-call overhead with no functional benefit, since the field set never changes at runtime. That is the reason startup is slow and steady state is not, and it is also why native-image/AOT builds need explicit reflection configuration ahead of time: there is no classpath to scan at runtime any more (guide 06, JVM internals).

**Interview:** "Why does Spring need `-parameters`?" — because without it, `getParameters()[0].getName()` is the synthetic `arg0` (measured), which carries no information Spring can bind a request parameter or a constructor argument to by name.

## 3. Reflection and generics: what survives erasure (2.12.9)

"Generics are erased, so reflection cannot see them" is folklore, and it is wrong. What erasure removes is the *runtime type of an instance* — `someList.getClass()` is `ArrayList`, full stop, nothing about `String`. What survives is the *declared signature of a member*, because `javac` writes that signature into a `Signature` attribute in the class file specifically so tools like reflection can read it back. Those are two different things, and conflating them is the entire confusion behind this leaf.

Measured on JDK 21.0.7 aarch64, for `static <T extends Comparable<T>> Map<String, List<T>> bulkPost(List<? extends T> entries, Map<String, ? super T> sink)`:

| Call | Measured result |
|---|---|
| `getParameterTypes()` | `[interface java.util.List, interface java.util.Map]` |
| `getGenericParameterTypes()` | `[java.util.List<? extends T>, java.util.Map<java.lang.String, ? super T>]` |
| `getGenericReturnType()` | `java.util.Map<java.lang.String, java.util.List<T>>` |
| `getTypeParameters()` | `[T]` |
| `getParameters()` | `[java.util.List<? extends T> arg0, java.util.Map<java.lang.String, ? super T> arg1]` |

And on the field `static List<String> positions`:

| Call | Measured result |
|---|---|
| `positionsField.getType()` | `interface java.util.List` |
| `positionsField.getGenericType()` | `java.util.List<java.lang.String>` |

**What survives, what does not:**

| Case | Survives at runtime? | Evidence |
|---|---|---|
| A field's declared type argument | Yes | measured `java.util.List<java.lang.String>` |
| A method parameter's type argument and wildcard | Yes | measured `java.util.List<? extends T>` |
| A method's return type arguments | Yes | measured `Map<String, List<T>>` |
| A type variable's bound | Yes | `T extends Comparable<T>` is written into the `Signature` |
| A superclass's or interface's type argument | Yes, via `getGenericSuperclass()`/`getGenericInterfaces()` — the mechanism behind super-type tokens, owned by `../generics/03e-internals-why-erasure-and-super-type-tokens.md` | link, not re-derived here |
| The type argument of a **live instance** | No | `someList.getClass()` returns bare `ArrayList` |
| A **local variable's** type argument | No | never written to any attribute the JVM keeps |
| The type argument at a **call site** | No | erased before bytecode generation |

*Declarations keep their generics; instances do not.*

`../generics/02a-type-tokens-and-generic-reflection.md` owns the full walk of the `Type` hierarchy and the super-type-token trick; the map you need here, without re-deriving that walk:

| Subinterface of `Type` | Represents | Measured example |
|---|---|---|
| `Class` | A raw, erased type | `getParameterTypes()[0]` → `interface java.util.List` |
| `ParameterizedType` | A generic type with actual arguments, e.g. `List<String>` | `getGenericType()` on the `positions` field |
| `WildcardType` | A `? extends` / `? super` bound | the `? extends T` inside `getGenericParameterTypes()[0]` |
| `TypeVariable` | A declared type parameter, e.g. `T` | `getTypeParameters()[0]` |
| `GenericArrayType` | An array whose component type is itself generic, e.g. `T[]` | not present in this method; same family |

The practical payoff is the exact problem Jackson and Spring Data both solve this way: given a repository method `List<Restriction> findActive(ClientId id)`, a generic mapper needs to know the element type is `Restriction`, not just `List`, to deserialize rows correctly.

```java
package quizstakes.reflection;

import java.lang.reflect.Method;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.List;
import java.util.UUID;

record ClientId(UUID value) {}
record Restriction(String type, String source) {}

interface RestrictionRepository {
    List<Restriction> findActive(ClientId id);
}

final class RepositoryElementTypeInspector {

    static Class<?> elementTypeOf(Method repositoryMethod) {
        Type generic = repositoryMethod.getGenericReturnType();
        if (generic instanceof ParameterizedType parameterized
                && parameterized.getRawType() == List.class) {
            Type elementType = parameterized.getActualTypeArguments()[0];
            if (elementType instanceof Class<?> elementClass) {
                return elementClass;
            }
        }
        throw new IllegalStateException(
                "cannot resolve list element type for " + repositoryMethod);
    }
}
```

`getGenericReturnType()` returns a `ParameterizedType`; `getRawType()` confirms it is a `List`; `getActualTypeArguments()[0]` yields `Restriction`. That chain is the entire mechanism a generic row mapper needs — no `TypeToken`, no super-type-token trick required, because the element type is sitting on a *declared method signature*, not on a live instance.

Three places this breaks, each for a distinct reason:

**The generic signature is a `String`, not a type.** `getGenericReturnType()` parses the `Signature` attribute's text form; a class compiled without one — or a synthetic method the compiler generated without bothering to write one — silently returns the erased type instead of throwing. **Pitfall:** a reflective mapper that assumes every method has a rich generic type needs a fallback to the raw `getReturnType()`, not an assumption that parsing always succeeds.

**Bridge methods.** A generic method that gets overridden with a covariant or erased-different signature receives a synthetic bridge method carrying the *erased* signature, and `getDeclaredMethods()` returns both the bridge and the real method. Code that grabs "the first method named `findActive`" can silently get the bridge, with erased parameter types where it expected generic ones. The honest filter is `method.isBridge()` combined with `method.isSynthetic()` (link `../generics/03a-internals-bridge-methods.md` for the mechanism, `02-reflection.md` for the shape `getDeclaredMethods()` returns). A related, second example of "the class file contains members you did not write, and their presence is version-dependent": `javac` on JDK 21 elides the synthetic `this$0` field entirely when an inner class never reads its enclosing instance — measured, `UsesEnclosing.class.getDeclaredFields()` returns `[final VerA$Outer VerA$Outer$UsesEnclosing.this$0]`, while `IgnoresEnclosing.class.getDeclaredFields()` returns `[int VerA$Outer$IgnoresEnclosing.x]`, with no `this$0` at all (link `../inheritance-and-dispatch/04-internals-nested-classes.md`).

**Parameter names are the thing that actually does not survive**, and this is where the concept lands. Measured, without `-parameters`: `getParameters()[0].isNamePresent()` is `false` and `getParameters()` prints `arg0`/`arg1`. Recompiled with `-parameters`, identical source: `isNamePresent()` is `true` and the same call prints `entries`/`sink`. **Pitfall:** people believe erasure is why a framework cannot see their parameter names. It is not — erasure is unrelated. The generic signature lives in the `Signature` attribute, emitted unconditionally by `javac`; parameter names live in the separate `MethodParameters` attribute, emitted only when `-parameters` is passed. Two different attributes with two different defaults, and only one of them needs an explicit flag (link `../language-substrate/03a-internals-class-file-format.md`).

**Ordering is unspecified.** The `getDeclaredFields()` Javadoc states, verbatim, from JDK 21's `lib/src.zip`: "The elements in the returned array are not sorted and are not in any particular order." A generic mapper that depends on reflective ordering — say, matching constructor parameters to fields positionally — is depending on undefined behaviour that happens to be stable on one JVM build, not a guarantee.

> Generic reflection reads the `Signature` attribute a declaration was compiled with, not the erased runtime type of a live instance — which is why a field's or method's generic type survives while a live object's, a local variable's, and a call site's type argument never do.

---

## Pitfalls

### An `InvocationHandler` only needs to implement the interface's own methods

**Wrong**

```java
Object p = Proxy.newProxyInstance(loader, new Class<?>[]{ Ledger.class }, (proxy, method, args) -> {
    if (method.getName().equals("post")) return target.post((String) args[0], (long) args[1]);
    throw new UnsupportedOperationException(method.getName());
});
p.hashCode(); // throws UnsupportedOperationException: hashCode
```

**Right**

```java
Object p = Proxy.newProxyInstance(loader, new Class<?>[]{ Ledger.class }, (proxy, method, args) -> {
    Object[] safe = args == null ? new Object[0] : args;
    switch (method.getName()) {
        case "hashCode" -> { return System.identityHashCode(proxy); }
        case "equals" -> { return proxy == safe[0]; }
        case "toString" -> { return "LedgerProxy"; }
        case "post" -> { return target.post((String) safe[0], (long) safe[1]); }
        default -> throw new UnsupportedOperationException(method.getName());
    }
});
```

**Why people believe it:** the interface you named is the only contract you wrote, so it looks like the only contract the proxy has to honour — but the generated class also implements every method the proxy object inherits from `Object`, and those go to the handler exactly like the interface methods do, measured `declaredBy=java.lang.Object`.

### Reflection cannot see generic type information because it is erased

**Wrong**

```java
List<String> positions = new ArrayList<>();
System.out.println(positions.getClass()); // class java.util.ArrayList — no String anywhere
// "therefore reflection can never recover List<String>"
```

**Right**

```java
Field positionsField = VerB.class.getDeclaredField("positions");
System.out.println(positionsField.getGenericType()); // java.util.List<java.lang.String>
```

**Why people believe it:** the live-instance case really does erase the type argument, and it is the case everyone hits first (`getClass()` on a collection), so the conclusion generalises past where it is true — to declared members, whose generic signature is written into the class file unconditionally and never erased.

### Spring cannot bind constructor parameter names because generics are erased

**Wrong**

```java
// compiled without -parameters
Constructor<?> ctor = PaymentService.class.getDeclaredConstructors()[0];
System.out.println(ctor.getParameters()[0].getName()); // arg0
// "generics erasure strikes again"
```

**Right**

```java
// compiled with: javac -parameters PaymentService.java
Constructor<?> ctor = PaymentService.class.getDeclaredConstructors()[0];
System.out.println(ctor.getParameters()[0].isNamePresent()); // true
System.out.println(ctor.getParameters()[0].getName());       // ledger
```

**Why people believe it:** erasure is the one generics-adjacent gotcha most engineers have already heard about, so any runtime name loss gets filed under it — but parameter names and generic signatures are two unrelated class-file attributes (`MethodParameters` versus `Signature`) with two different compiler defaults, and only the first one needs an explicit `-parameters` flag.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Proxy.newProxyInstance` needs | A `ClassLoader`, an interface array, one `InvocationHandler` |
| Generated proxy's superclass | `java.lang.reflect.Proxy` — the reason it cannot also extend a class |
| Methods routed to the handler | Every interface method plus `equals`, `hashCode`, `toString` |
| No-arg call's `args` | `null`, not `new Object[0]` |
| `InvocationTargetException` | Always unwrap with `getCause()` before rethrowing |
| CGLIB/ByteBuddy limitation | Cannot intercept `final`/`private`/`static` methods or self-invocation via `this` |
| Self-invocation fix | Extract to a second bean, self-inject the proxy, or load-time weave |
| `-parameters` flag | Emits `MethodParameters`; without it, names are `arg0`, `arg1`, … |
| `Signature` attribute | Emitted unconditionally; carries generic types, always readable |
| Field/method generic type | Survives (`getGenericType`, `getGenericReturnType`, `getGenericParameterTypes`) |
| Live instance's type argument | Does not survive — `list.getClass()` is bare `ArrayList` |
| `getDeclaredFields()` order | Javadoc: not sorted, not in any particular order |
| Bridge method filter | `method.isBridge()` and `method.isSynthetic()` |

## Self-test

**Q1.** Why can a `java.lang.reflect.Proxy` never extend a concrete class, only implement interfaces?

<details><summary>Answer</summary>

Because the class `Proxy.newProxyInstance` generates already extends `java.lang.reflect.Proxy` itself — measured, `p.getClass().getSuperclass().getName()` is `java.lang.reflect.Proxy`. Java permits only single inheritance of implementation, so that superclass slot is spent before your interfaces come into play; the generated class can implement any number of interfaces but has no slot left to extend anything else, and passing a class instead of an interface fails immediately with `IllegalArgumentException`.

</details>

**Q2.** A logging framework calls `toString()` on every bean it logs, including a JDK dynamic proxy. What actually runs, and why can this cause a database transaction to open unexpectedly?

<details><summary>Answer</summary>

`toString()` is not special-cased away from proxy interception — it is routed to the same `InvocationHandler` as every other method, measured with `declaredBy=java.lang.Object` for that call. If the proxy sits in front of a `@Transactional` bean and the handler's interception logic runs regardless of which method triggered it, then merely logging or debugger-inspecting the proxy executes that interception logic, which can open a transaction as a side effect of an operation that was meant to be read-only observation.

</details>

**Q3.** A `PaymentService.settleStake` method calls `this.recordMovement(movement)`, and `recordMovement` is annotated `@Transactional`. The transaction never actually opens. Why, and name one fix.

<details><summary>Answer</summary>

The Spring container wraps `PaymentService` in a proxy that is a distinct object delegating to the real bean. Inside `settleStake`, `this` refers to the real, unproxied `PaymentService`, because the compiler bound that call site directly — it never routes through the container's proxy. The interception that would open the transaction therefore never fires. Fixes: move `recordMovement` to a second bean and call through that bean's proxy, have `PaymentService` self-inject its own proxy and call through it, or use load-time weaving so interception happens at the bytecode level regardless of how the call is made.

</details>

**Q4.** Why does Spring Boot's build tooling pass `-parameters` to `javac` by default?

<details><summary>Answer</summary>

Without `-parameters`, the `MethodParameters` class-file attribute is not emitted, so `Parameter.getName()` returns synthetic names like `arg0` and `arg1` and `isNamePresent()` is `false` — measured directly. Spring's constructor and parameter injection by name has nothing meaningful to bind against in that case, forcing explicit `@Qualifier` or `@Param` annotations everywhere. Emitting `-parameters` gives Spring the real declared names to bind by, with no source changes required.

</details>

**Q5.** `someList.getClass()` on a `List<String>` returns bare `ArrayList`, with no `String` anywhere. Does this mean generic reflection cannot recover type argument information anywhere in the program?

<details><summary>Answer</summary>

No — it means only that the *runtime type of a live instance* has no memory of its type argument, because that argument was erased before bytecode generation. A *declared* member — a field, a method parameter, a method's return type — keeps its generic signature in the class file's `Signature` attribute unconditionally, and reflection reads that back correctly: `getGenericType()` on a `List<String>` field measured `java.util.List<java.lang.String>`. Declarations keep their generics; instances do not.

</details>

**Q6.** A reflective row mapper iterates `getDeclaredMethods()` looking for `findActive` by name and takes the first match. What can silently go wrong?

<details><summary>Answer</summary>

If the method's generic signature involved an override with a covariant or erased-different return type, the compiler emits a synthetic bridge method alongside the real one, and both appear in `getDeclaredMethods()` under the same name. The bridge carries the erased signature, not the generic one, so a mapper that grabs "the first `findActive`" may bind against the bridge and lose the element type it needed. The fix is filtering with `method.isBridge()` and `method.isSynthetic()` before matching by name.

</details>

**Q7.** Why does a proxy's stack trace read `at $Proxy0.hashCode(Unknown Source)` instead of a file name and line number?

<details><summary>Answer</summary>

`$Proxy0` is a class generated at runtime by `Proxy.newProxyInstance`; it was never compiled from a `.java` source file, so it has no `SourceFile` attribute and no line-number table for the JVM to attach to stack frames from it. "Unknown Source" is the JVM reporting exactly that absence, and it is the real operational cost of using proxies heavily — traces through them are harder to read than traces through hand-written code.

</details>

**Q8.** What is `getDeclaredFields()`'s ordering guarantee per the JDK 21 Javadoc, and why does that matter for a generic mapper?

<details><summary>Answer</summary>

The Javadoc states verbatim: "The elements in the returned array are not sorted and are not in any particular order." A mapper that matches constructor parameters to fields positionally, relying on whatever order one JVM build happens to return, is depending on undefined behaviour that is stable in practice but not guaranteed across JVM versions or vendors — it should match by name instead.

</details>

## Open questions

None.

---

**Leaves covered:** 2.12.7–2.12.9 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 428
