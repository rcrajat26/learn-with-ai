# 03 Java Core — Reflection: access, cost and method handles — INTERMEDIATE (§2.12, 2.12.4–2.12.6)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Class objects, names and member lookup](02-reflection.md) · Next: [Proxies, frameworks and generics](02b-proxies-frameworks-and-generics.md)

`02-reflection.md` owns `Class` objects, the four naming methods and member lookup; this file owns `setAccessible` and strong encapsulation, what reflective invocation actually costs, and the `MethodHandle`/`VarHandle` layer; `02b-proxies-frameworks-and-generics.md` owns dynamic proxies, where reflection appears in your stack, and generic reflection; `02c-final-fields-and-security-surface.md` owns reflective `final`-field writes and the security surface. The question this file answers, in bold: **what does the module system actually stop you doing, what does reflection cost per call, and what is the faster layer underneath it?**

## 1. `setAccessible(true)` and strong encapsulation (2.12.4)

`setAccessible(true)` looks like a cast — flip a bit, ignore `private`. It is not. It is a **request to the module system**, made per `AccessibleObject` at the moment you call it, and the module system either grants it or throws. Before Java 9 the request was rubber-stamped, so generations of code treat the call as a no-op formality. Since JDK 16/17 it is a real negotiation, and the negotiation can fail with a message that names exactly which module refuses which package to whom.

### Why it exists

The JDK's own internal classes — `java.lang.String`'s backing array, `sun.misc.Unsafe`, the guts of `java.util.HashMap` — used to be reachable by any code willing to call `setAccessible(true)`. That made every internal field and method of the platform a de facto public API that library authors depended on, which in turn made the JDK unable to change its own internals without breaking the ecosystem. The module system's strong encapsulation exists to give the JDK back the ability to refactor `java.base` without a compatibility freeze.

### How it works

Two module directives govern this, and they are **independent axes**, not two strengths of the same thing:

- `exports p` (or `exports p to m`) governs **compile-time and public reflective** access to package `p`'s public types and members.
- `opens p` (or `opens p to m`) governs **deep reflective** access — `setAccessible(true)` reaching non-public members, or public members that would otherwise still be checked — to package `p`.

Measured on the same JVM, `java.lang` is exported but not open to the unnamed module:

| Query | No flags | With `--add-opens java.base/java.lang=ALL-UNNAMED` |
|---|---|---|
| `Object.class.getModule().isOpen("java.lang", callerModule)` | `false` | **`true`** |
| `Object.class.getModule().isExported("java.lang")` | `true` | `true` |
| `Object.class.getModule().isExported("jdk.internal.misc")` | `false` | `false` |

That table is the whole concept in four cells: you may `import java.lang.reflect.Field;` and call public `String` methods either way (exported, always true), but you may not reach `String`'s private backing array without `opens` (or the flag that simulates it). `jdk.internal.misc` is neither exported nor opened under any flag shown here — some packages are sealed off from ordinary code entirely.

The five module declarations that matter, and what each buys:

| Declaration | Grants | To whom | Effect on `setAccessible` |
|---|---|---|---|
| `exports p` | compile + public reflective access | everyone | no effect on deep reflection |
| `exports p to m` | compile + public reflective access | only module `m` | no effect on deep reflection |
| `opens p` | deep reflective access to non-public members | everyone | `setAccessible(true)` succeeds |
| `opens p to m` | deep reflective access | only module `m` | succeeds only for callers in `m` |
| `open module` | every package implicitly opened | everyone | `setAccessible(true)` always succeeds |

`../language-substrate/02-packages-modules-annotations.md` owns the module system itself — `module-info.java` syntax, readability edges, automatic modules; this paragraph is the minimum needed to read the `InaccessibleObjectException` below and nothing more.

The failure, measured verbatim on JDK 21 with no flags:

```
java.lang.reflect.InaccessibleObjectException: Unable to make field private final byte[] java.lang.String.value accessible: module java.base does not "opens java.lang" to unnamed module @12d3a4e9
```

Read it phrase by phrase: the field's full declaration (`private final byte[] java.lang.String.value`); the module that refuses (`java.base`); the missing directive, stated as JVM would write it (`does not "opens java.lang"`); and the requester (`unnamed module @12d3a4e9` — code on the classpath, not inside a named module, always lands in one unnamed module per class loader). `InaccessibleObjectException` extends `RuntimeException` directly, so it is unchecked: nothing at compile time flags the risk, and the first sign of it is a runtime crash, typically at application startup where the reflective mapper first touches the field.

**Insight:** the exception message is written to be self-diagnosing — module name, package, requester — because the JDK authors expected exactly this failure to surface far from the code that triggers it (inside a serialization or ORM library), so the fix has to be discoverable from the stack trace alone.

With `--add-opens java.base/java.lang=ALL-UNNAMED` supplied, the identical code succeeded:

```java
Field f = String.class.getDeclaredField("value");
f.setAccessible(true);
```

and read a `byte[]` of length **6** out of the string `"AA-801"` — the QuizStakes activation status code — confirming compact strings' LATIN1 encoding, one byte per character for a pure-ASCII value (`../strings/03-internals-string.md` owns compact strings; `../strings/01b-the-string-pool.md` owns pooling and folding).

The fixes, ranked by what they cost:

| Fix | Reaches | Cost |
|---|---|---|
| `--add-opens java.base/java.lang=ALL-UNNAMED` on the command line | JDK internals only | invisible in code review; breaks silently if omitted on a new base image or in `JAVA_TOOL_OPTIONS` |
| `Add-Opens` entry in a jar manifest | JDK internals, for that jar's own reflective needs | ties the fix to a specific artifact, not the whole JVM |
| `opens p` (or `opens p to m`) in your own `module-info.java` | your own packages, to a chosen module | correct engineering, but only you can add it to your own module |
| `MethodHandles.privateLookupIn(target, lookup)` | any module that has opened the package to yours | the *sanctioned* mechanism — a capability handed to you by the target module, not a bypass; covered fully in §3 below |

Only the first two exist for reaching into `java.base` itself — you cannot add `opens java.lang` to the JDK's own `module-info.java`. The last two are for your own code and are the only durable fixes; a command-line flag is an operational patch that a new deployment environment can silently drop.

**Pitfall:** the belief that `setAccessible(true)` "always works because it always used to." Reflection code written against Java 8 or 11 assumed the call was a formality; the measured `--illegal-access` output is the clearest evidence the assumption died:

```
$ java --illegal-access=permit -version
Java HotSpot(TM) 64-Bit Server VM warning: Ignoring option --illegal-access=permit; support was removed in 17.0
java version "21.0.7" 2025-04-15 LTS
```

The version arc: Java 8 and earlier, `setAccessible` on a JDK internal always succeeded. Java 9 introduced modules but defaulted to permissive with a warning, and `--illegal-access` (values `permit`/`warn`/`debug`/`deny`) tuned that behaviour through Java 15. The default flipped to deny JDK-internal deep reflection starting with JDK 16 (commonly cited as **JEP 396** — **Unverified:** the JEP number itself, since JEP text could not be fetched this session; the behaviour is corroborated by the measured JVM output). JDK 17 removed `--illegal-access` outright (commonly cited as **JEP 403** — **Unverified:** same caveat), and the JVM says so in the exact words captured above, naming `17.0` as the release. Code and Stack Overflow answers written for 8 or 11 that say "just call `setAccessible(true)`, maybe you'll see a warning" are correct for their era and wrong on 17 and 21, where the same call throws.

Also measured on JDK 21: `Field.class.getDeclaredField("modifiers")` threw `java.lang.NoSuchFieldException: modifiers`. The classic "strip `final` by reflecting on `Field`'s own `modifiers` field" trick has no field left to find — the JDK closed the loophole in its own reflection API, not just in application-facing packages. `02c-final-fields-and-security-surface.md` owns what this means for writing `final` fields; here it is evidence only that the reflection API encapsulates itself as tightly as everything else.

None of this touches reflection on **your own** code. `AccountMaintenance`, mapping a `LedgerEntry`'s private fields to a wire format, calls `setAccessible(true)` on `LedgerEntry`'s own declared fields — `LedgerEntry` lives in the unnamed module (or your own named module) alongside the caller, so there is no boundary to cross and the call succeeds exactly as it always did. Readers routinely conclude "modules broke reflection" from library failures against `java.base` and generalize it to their own domain classes, which is backwards: the boundary that broke is specifically the one around the JDK's own internals.

```java
public final class LedgerEntryMapper {

    private final Field positionField;
    private final Field amountMinorField;
    private final Field currencyField;

    public LedgerEntryMapper() {
        this.positionField = declaredField("position");
        this.amountMinorField = declaredField("amountMinor");
        this.currencyField = declaredField("currency");
    }

    private Field declaredField(String name) {
        try {
            Field field = LedgerEntry.class.getDeclaredField(name);
            field.setAccessible(true);
            return field;
        } catch (InaccessibleObjectException e) {
            throw new IllegalStateException(
                "Cannot reflect into LedgerEntry." + name
                    + " — LedgerEntry's own module must open its package to the caller, "
                    + "or run with --add-opens "
                    + LedgerEntry.class.getModule().getName()
                    + "/" + LedgerEntry.class.getPackageName() + "=ALL-UNNAMED",
                e);
        } catch (NoSuchFieldException e) {
            throw new IllegalStateException("LedgerEntry has no field " + name, e);
        }
    }

    public Map<String, Object> toWireMap(LedgerEntry entry) {
        try {
            return Map.of(
                "position", positionField.get(entry).toString(),
                "amountMinor", amountMinorField.get(entry),
                "currency", currencyField.get(entry).toString());
        } catch (IllegalAccessException e) {
            throw new IllegalStateException("Unreachable: fields already made accessible", e);
        }
    }
}
```

The three `setAccessible` calls happen once, in the constructor, not once per `LedgerEntry` mapped — resolving reflective metadata per call rather than once at startup is the real cost, covered next. The catch block that rewrites `InaccessibleObjectException` into a message naming the exact `--add-opens` flag is the actual deliverable: production code that fails this way should tell the operator what to type, not just that it failed.

> `setAccessible(true)` is a per-call request to the module system to permit deep reflection on a member, granted automatically only when the target's module has no boundary against the caller, and refused with a self-diagnosing exception otherwise.

## 2. Reflective invocation cost and JIT opacity (2.12.5)

Reflection is not slow because the call itself costs much in absolute terms. It is slow because it is **opaque to the optimiser**. A direct call is a call site the JIT can inline, devirtualise, constant-fold through, and — if nothing observes the result — delete outright. `Method.invoke` is a call through a generic dispatcher that takes an `Object[]` of arguments and returns `Object`; the JIT cannot see through that indirection to know the target has no side effects, so it cannot do any of those things. Almost everything people call "reflection overhead" is downstream of that one fact.

### Why it exists

`Method.invoke` has to work for *any* method discovered at runtime, with any signature, so its call shape is necessarily generic: box the arguments into an array, dispatch, unbox the result. That genericity is what makes reflection powerful and is exactly what makes it opaque — the same interface that lets a framework call a method it has never seen at compile time is the interface the JIT cannot specialise.

### How it works

Harness: `N = 20,000,000` iterations per loop, three rounds, summing the return of a trivial public getter `public long stakeMinor()` on a `Reservation`, timed with `System.nanoTime()`. **This is a crude `nanoTime` microbenchmark, not JMH** — no dead-code-elimination guards, no warm-up isolation beyond the three rounds themselves — so treat every number below as a ratio between the four call styles, not an absolute figure. Guide 06 (JVM internals) is where a JMH-correct version of this measurement belongs.

| Round | direct call | `Method.invoke` | `Method.invoke` + `setAccessible(true)` | `MethodHandle.invokeExact` |
|---|---|---|---|---|
| 0 | 2,747,292 ns (0.14 ns/op) | 125,367,000 ns (6.27 ns/op) | 82,254,375 ns (4.11 ns/op) | 47,351,125 ns (2.37 ns/op) |
| 1 | 18,430,875 ns (0.92 ns/op) | 91,657,041 ns (4.58 ns/op) | 63,182,125 ns (3.16 ns/op) | 28,692,750 ns (1.43 ns/op) |
| 2 | **0 ns (0.00 ns/op)** | 90,348,042 ns (4.52 ns/op) | 68,843,750 ns (3.44 ns/op) | 28,797,250 ns (1.44 ns/op) |

The load-bearing row is round 2's direct call landing at **0 ns**. That is not measurement noise and must not be read as one: the JIT proved the loop's accumulated sum was never observed anywhere, so it deleted the entire loop. It could not do that to any of the other three columns, because it could not prove `Method.invoke`, the accessible variant, or `invokeExact` had no observable side effect — each is a call through code the optimiser cannot fully see into. That is the actual mechanism behind "reflection is N times slower than a direct call": in the direct-call limit the multiplier is undefined, because the denominator can go to zero. The only honest comparison is between the three reflective forms, which the JIT could not eliminate.

Stable-state figures from rounds 1–2, the ones worth quoting: `Method.invoke` ≈ **4.5 ns/op**; `Method.invoke` after `setAccessible(true)` ≈ **3.2–3.4 ns/op**; `MethodHandle.invokeExact` ≈ **1.4 ns/op**. Qualify the `Method.invoke` figure honestly: it returns `Object`, so every call in the harness boxed a `long` return via `Long.valueOf` and then unboxed it back — some fraction of that 4.5 ns is boxing overhead, not reflective dispatch itself.

**Insight:** `setAccessible(true)` on an already-public method is measurably faster — roughly a 25–30% reduction in the measurement above — because it suppresses the per-invocation access check `Method.invoke` otherwise performs on every call, not just the first. The call every framework makes for correctness reasons (so it can reach non-public members) turns out to also be a performance optimisation on public members, and skipping it because "it's already public, no need to call `setAccessible`" leaves that throughput unclaimed.

The JIT story, kept separate from the version story so as not to over-claim:

- Historically, core reflection's `Method.invoke` began on a native accessor and, after a call-count threshold (`sun.reflect.inflationThreshold`), "inflated" into a JDK-generated bytecode accessor class, at which point subsequent calls became an ordinary virtual call the JIT could inline. That mechanism is the origin of the folklore that reflection "warms up."
- JDK 18 reimplemented core reflection on method handles under the hood (commonly cited as **JEP 416** — **Unverified:** the JEP number, JEP text unreachable this session), which removed the generated-accessor path. On JDK 21, `Method.invoke` is therefore a method-handle invocation internally, and the warm-up story for 21 is not the same mechanism as the pre-18 inflation story. The measured round-0-to-round-1 drop for `Method.invoke` (6.27 → 4.58 ns/op) is *consistent* with some form of warm-up but the harness cannot distinguish which underlying mechanism produced it — state that honestly rather than attributing the drop to a specific cause.
- The one thing the measurement establishes unambiguously, independent of mechanism: reflective invocation never converges on direct-call speed, in any round, under either implementation.

**[NUM]** Scale the 4.5 ns/op figure to QuizStakes' own throughput. At **2.8M stake settlements/day** with a **3,400/sec burst**, a settlement path doing one reflective field read per settlement costs 2,800,000 × 4.5 ns ≈ **12.6 ms/day** of pure dispatch time — negligible, and worth saying so plainly rather than implying reflection is dangerous here. Repeat it against the number that actually dominates the domain: at **≈19.8M ledger entries/day**, with, say, eight reflective member accesses per entry for a generic serializer, that is 19,800,000 × 8 × 4.5 ns ≈ **713 ms/day** — still small in absolute terms. But `02-reflection.md` measured that `getDeclaredFields()` allocates a fresh array and fresh `Field` objects on **every call**; resolving that metadata per row instead of once at startup means 19.8M array allocations plus roughly 79M `Field` objects (eight per entry) a day, purely from lookup, not invocation.

That comparison is the conclusion this concept exists to reach: the cost of reflection in practice is **metadata lookup and allocation**, not invocation. Reflective dispatch itself costs roughly 3–4.5 ns/op and blocks inlining of the surrounding code, **but** the dominant real-world cost is re-resolving `Method`/`Field` objects on every call, **and** the escape hatch is resolving each `Method`, `Field`, or `MethodHandle` exactly once at startup into a cached structure keyed by type — which is precisely what Spring, Jackson, and JPA do internally, and what `02b-proxies-frameworks-and-generics.md` describes for each framework by name.

> Reflective invocation costs a small, constant per-call multiple over a direct call and prevents the JIT from inlining through it, but the throughput-dominating cost in practice is re-resolving `Method`/`Field` metadata per call rather than once at startup.

## 3. `MethodHandle`, `VarHandle`, `LambdaMetafactory` (2.12.6)

A `MethodHandle` is not a reflective object wearing a faster interface — it is a **directly executable, typed reference to a member, resolved and access-checked once, at creation**. `Method.invoke` asks "am I allowed, and does this argument array match?" on every single call. A `MethodHandle` asked both questions once, when you obtained it, and every call thereafter trusts that answer. That difference in *when* the checking happens is the entire performance and safety story, and it is why the measured `invokeExact` figure sits at roughly a third of `Method.invoke`'s.

### Why it exists

Reflection's `Object[]`-in, `Object`-out shape exists to support code that has never seen the target's signature. Most callers, though, know the exact signature they want at the call site — they discovered *which* method reflectively, but they know its shape statically. `MethodHandle` was built to serve that far more common case: pay the discovery cost once, then call through a typed, checked, inlinable handle from then on.

### How it works

**`MethodHandle` and `Lookup`.** `MethodHandles.Lookup` is the access-control object, and it works by capability rather than by flag: a `Lookup` **carries the access rights of the class that created it**. `MethodHandles.lookup()` called inside `LedgerEntryMapper` can find `LedgerEntryMapper`'s own privates; it cannot manufacture the right to reach into `String`'s privates, because no `lookup()` call carries rights it wasn't granted. `MethodHandles.privateLookupIn(target, callerLookup)` returns a lookup with the target class's private access **only if the target's module has opened the relevant package to the caller's module** — the identical check `setAccessible` performs, expressed as an object you hold rather than a boolean you flip. That is the direct comparison worth drawing: `setAccessible(true)` is a mutable, per-`AccessibleObject` request that either throws or silently succeeds; `privateLookupIn` is a single request that, once granted, hands back a reusable capability.

The lookup family: `findVirtual`, `findStatic`, `findGetter`, `findSetter`, `findConstructor`, each taking a `MethodType` — the exact, reified parameter and return types, with no erasure ambiguity. Calling one resolves the member and checks access immediately; nothing about the resulting `MethodHandle` re-checks either on later use.

The critical distinction at the call site is **`invokeExact` versus `invoke`**. `invokeExact` requires the call site's static argument and return types to match the handle's `MethodType` exactly — no boxing, no widening, no adaptation — and is the fast path measured above at **1.4 ns/op**. `invoke` inserts `asType` conversions (boxing, widening, casting) to bridge a mismatch, at a cost this harness did not measure — do not attribute the 1.4 ns/op figure to `invoke`.

`MethodHandle`'s methods declare `throws Throwable`, so every call site needs a `try`/`catch (Throwable t)` or a wrapper that narrows it:

```java
public final class ReservationStakeReader {

    private static final MethodHandle STAKE_MINOR;

    static {
        try {
            MethodHandles.Lookup lookup = MethodHandles.lookup();
            STAKE_MINOR = lookup.findVirtual(
                Reservation.class, "stakeMinor", MethodType.methodType(long.class));
        } catch (NoSuchMethodException | IllegalAccessException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    public long stakeMinor(Reservation reservation) {
        try {
            return (long) STAKE_MINOR.invokeExact(reservation);
        } catch (Throwable t) {
            throw new IllegalStateException("stakeMinor handle invocation failed", t);
        }
    }
}
```

**Insight:** a `MethodHandle` held in a `static final` field is treated by the JIT as effectively constant at that call site, which is where handles reach speeds close to a direct call in steady state — **Unverified:** the precise JIT mechanism (constant folding of the handle target versus a more general call-site specialisation) is not sourced here, but the pattern of caching handles in `static final` fields is exactly what `java.lang.invoke`-based frameworks do, which is itself evidence the pattern earns its keep.

**`VarHandle`** (Java 9) is `MethodHandle`'s sibling for **fields and array elements**, with explicit memory-ordering modes: `get`/`set` (plain), `getVolatile`/`setVolatile`, `getAcquire`/`setRelease`, `getOpaque`, plus atomics `compareAndSet`, `getAndAdd`, `getAndSet`. Guide 05 (Concurrency) owns what each ordering mode guarantees; the one fact worth carrying here is that `VarHandle` is the sanctioned Java-9-onward replacement for `sun.misc.Unsafe` field access and for `AtomicReferenceFieldUpdater` — a `Position` whose running cash-available total is updated under contention reaches for a `VarHandle.compareAndSet` rather than either of those.

The measured asymmetry between `VarHandle` and core reflection on a `final` field is the fact that belongs in this file specifically: `MethodHandles.privateLookupIn(Restriction.class, MethodHandles.lookup())` then `findVarHandle(Restriction.class, "type", String.class)` on `Restriction.type`, a non-static `final` field, **found** the handle and `vh.get(restriction)` **worked**; `vh.set(restriction, "SELF_EXCLUDED")` threw `java.lang.UnsupportedOperationException` with a `null` message. A reflective `Field.set` on that exact same field, after `setAccessible(true)`, **succeeded** on JDK 21. `VarHandle` enforces `final` at the API level; core reflection still does not, on this JDK. `02c-final-fields-and-security-surface.md` owns what a successful reflective `final`-field write means for safety and the security surface — this file states the asymmetry and stops there.

| API | `final` field write | Access model |
|---|---|---|
| `Field.set` (after `setAccessible(true)`) | succeeds (measured, JDK 21) | per-call check, checked at `setAccessible` time only |
| `VarHandle.set` | throws `UnsupportedOperationException` | checked once, at `findVarHandle` time, `final`-aware |

**`LambdaMetafactory`.** The reader has already used this mechanism without being told: `javac` compiles every lambda expression and every method reference into an `invokedynamic` instruction whose bootstrap method is `LambdaMetafactory.metafactory`. On first execution at that call site, the bootstrap spins a small implementation class on the fly and returns a `CallSite`, which the JVM then treats as an ordinary, inlinable call for every subsequent invocation (`../inheritance-and-dispatch/03-internals-dispatch.md` owns `invokedynamic` and the five invoke instructions in full).

The payoff for this file: you can drive `LambdaMetafactory` **yourself**, converting a reflectively-discovered `Method` into a plain functional interface the JIT then treats like any other lambda — reaching near-direct-call speed after a one-time reflective setup cost:

```java
public final class LedgerEntryPositionAccessor {

    private final Function<LedgerEntry, String> positionOf;

    @SuppressWarnings("unchecked")
    public LedgerEntryPositionAccessor() {
        try {
            MethodHandles.Lookup lookup = MethodHandles.lookup();
            Method reflected = LedgerEntry.class.getMethod("position");
            MethodHandle target = lookup.unreflect(reflected);

            CallSite site = LambdaMetafactory.metafactory(
                lookup,
                "apply",
                MethodType.methodType(Function.class),
                MethodType.methodType(Object.class, Object.class),
                target,
                MethodType.methodType(String.class, LedgerEntry.class));

            this.positionOf = (Function<LedgerEntry, String>) site.getTarget().invokeExact();
        } catch (Throwable t) {
            throw new IllegalStateException("Failed to build LedgerEntry.position() accessor", t);
        }
    }

    public String positionOf(LedgerEntry entry) {
        return positionOf.apply(entry);
    }
}
```

This only works when the target can be expressed as a functional interface with an erasure-compatible signature, and it spins one implementation class per target — a startup cost traded for steady-state speed, the same trade `static final MethodHandle` fields make, one level further along. `../serialization/02b-externalizable-records-and-lambdas.md` owns the `SerializedLambda` side of this same machinery; guide 04 (Modern Java) owns lambdas as a language feature in their own right.

**Interview:** asked "why is `MethodHandle` faster than reflection," the one-line answer is that reflection checks access and resolves the target on every call, a `MethodHandle` checks and resolves once at creation and then calls through a typed, JIT-visible path — the measured 4.5 ns/op versus 1.4 ns/op difference is exactly that gap.

| Need | Reach for | Measured cost | Access model |
|---|---|---|---|
| Call a method known at compile time | direct call | ~0.14–0.92 ns/op, or eliminated entirely | checked at compile time |
| Call a method discovered at runtime, once | `Method.invoke` | ~4.5 ns/op | checked on every call |
| Same, called many times | `Method.invoke` + `setAccessible(true)` | ~3.2–3.4 ns/op | check suppressed after the flag is set |
| Same, on a hot path | `MethodHandle.invokeExact` from a `static final` field | ~1.4 ns/op | checked once, at lookup |
| Same, on a very hot path, functional-interface shape | `LambdaMetafactory` → cached lambda | direct-call speed after setup | checked once, at lookup |
| A field with explicit memory-ordering needs | `VarHandle` | not measured in this file | checked once, at lookup; `final`-aware |

> A `MethodHandle` is a typed, directly executable member reference whose access check and resolution happen once at creation rather than on every call, which is what lets it run near direct-call speed and what a `VarHandle` and a `LambdaMetafactory`-built lambda both build further on.

## Pitfalls

### `setAccessible(true)` always works, the way it did on Java 8 and 11.

**Wrong**

```java
Field value = String.class.getDeclaredField("value");
value.setAccessible(true);   // throws on JDK 17+ with no flags
```

**Right**

```java
Field value = String.class.getDeclaredField("value");
try {
    value.setAccessible(true);
} catch (InaccessibleObjectException e) {
    throw new IllegalStateException(
        "Run with --add-opens java.base/java.lang=ALL-UNNAMED", e);
}
```

**Why people believe it:** on Java 8 through 15 the call either always succeeded or, at worst, printed a warning that most teams ignored because nothing broke; the same code was ported forward unchanged and only fails once the runtime moves to 17 or 21.

### `java.lang` being exported means reflection can reach its private fields.

**Wrong**

```java
System.out.println(Object.class.getModule().isExported("java.lang")); // true
Field value = String.class.getDeclaredField("value");
value.setAccessible(true); // throws anyway — exported is not opened
```

**Right**

```java
System.out.println(Object.class.getModule().isOpen("java.lang", callerModule)); // false
// InaccessibleObjectException is certain before you even try setAccessible
```

**Why people believe it:** `exports` and `opens` read like synonyms in casual conversation about modules, and most day-to-day code only ever needs `exports` (to compile against a public API), so the reflective distinction never comes up until a library tries to reach a non-public member.

### `Method.invoke` being "N times slower" than a direct call is a fixed, quotable multiplier.

**Wrong**

```java
// "reflection is always ~30x slower than a direct call" — quoting round 0's ratio
```

**Right**

```java
// Round 2: direct call measured 0 ns (JIT eliminated the dead loop).
// The only stable comparison is among the reflective forms:
// Method.invoke ~4.5 ns/op, +setAccessible ~3.2-3.4 ns/op, invokeExact ~1.4 ns/op.
```

**Why people believe it:** an early, unoptimised microbenchmark round genuinely does show a large ratio, and it is the number people screenshot; by the time the JIT has warmed up and possibly eliminated the direct-call loop entirely, the ratio is either much smaller or mathematically undefined, but the first number is the one that spreads.

### `VarHandle.set` on a `final` field behaves like `Field.set` after `setAccessible(true)`.

**Wrong**

```java
VarHandle type = lookup.findVarHandle(Restriction.class, "type", String.class);
type.set(restriction, "SELF_EXCLUDED"); // throws UnsupportedOperationException
```

**Right**

```java
Field typeField = Restriction.class.getDeclaredField("type");
typeField.setAccessible(true);
typeField.set(restriction, "SELF_EXCLUDED"); // succeeds on JDK 21 — see 02c
```

**Why people believe it:** both APIs are presented together as "the modern reflection layer," and most of their operations are interchangeable in spirit, so the one place they diverge — `final`-field writes — is easy to assume works the same way on both.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `exports` vs `opens` | `exports` = compile/public reflective access; `opens` = deep reflective access; independent |
| `setAccessible(true)` on JDK internals | throws `InaccessibleObjectException` unless opened or `--add-opens` |
| `setAccessible(true)` on your own classes | always succeeds — no module boundary to cross |
| `--illegal-access` flag | removed in 17; passing it now only prints a warning and is ignored |
| `Field.class.getDeclaredField("modifiers")` | throws `NoSuchFieldException` — the classic strip-final hack has no target |
| Direct call, round 2 of measurement | 0 ns — JIT eliminated the entire loop |
| `Method.invoke` steady state | ≈4.5 ns/op (includes boxing of a `long` return) |
| `Method.invoke` + `setAccessible(true)` steady state | ≈3.2–3.4 ns/op — access check suppressed |
| `MethodHandle.invokeExact` steady state | ≈1.4 ns/op |
| Dominant real-world reflection cost | per-call metadata lookup/allocation, not invocation |
| `invokeExact` vs `invoke` | `invokeExact` requires exact `MethodType` match; `invoke` adapts via `asType` |
| `Lookup` access model | carries the rights of the class that created it |
| `privateLookupIn` | grants private access only if target module opened the package to caller's module |
| `VarHandle.set` on `final` field | throws `UnsupportedOperationException` |
| `Field.set` on `final` field (after `setAccessible`) | succeeds on JDK 21 (see `02c`) |
| `LambdaMetafactory` | bootstrap behind every compiled lambda/method reference; usable directly to convert a `Method` into a fast lambda |

## Self-test

**Q1.** Why does `Object.class.getModule().isExported("java.lang")` return `true` while `setAccessible(true)` on `String.value` still throws?

<details><summary>Answer</summary>

`exports` and `opens` are independent module directives. `exports java.lang` grants compile-time and public reflective access to `java.lang`'s public API, which is why ordinary code compiles and calls `String` methods freely. It says nothing about deep reflection into non-public members — that requires `opens java.lang`, which `java.base` does not grant to the unnamed module by default. `isExported` being `true` and `isOpen` being `false` are both simultaneously true and consistent; conflating the two is the commonest mistake with this API.

</details>

**Q2.** A colleague says "reflection is about 30 times slower than a direct call — I measured it." What is the likely flaw in their measurement, based on the round-by-round data in this file?

<details><summary>Answer</summary>

If their loop's result was never read or used, the JIT can prove the direct-call loop has no observable effect and eliminate it entirely, driving its measured time toward zero — as happened in round 2 of the measurement here (0 ns). Dividing a reflective time by a near-zero or fully-eliminated direct-call time produces an arbitrarily large, meaningless ratio. The honest comparison is among the reflective forms themselves, which the JIT could not eliminate because it could not prove they were side-effect free: roughly 4.5 ns/op for `Method.invoke`, 3.2–3.4 ns/op with `setAccessible(true)`, and 1.4 ns/op for `MethodHandle.invokeExact`.

</details>

**Q3.** Why does calling `setAccessible(true)` on an already-public method measurably improve throughput, and by roughly how much in this file's measurement?

<details><summary>Answer</summary>

`Method.invoke` performs an access check on every single call by default, even when the member is already public — checking is unconditional unless suppressed. `setAccessible(true)` suppresses that per-call check permanently for that `AccessibleObject`. In the measured harness this reduced per-call cost from about 4.5 ns/op to about 3.2–3.4 ns/op, roughly a 25–30% reduction, purely from removing the redundant check on an already-accessible member.

</details>

**Q4.** What is the practical difference between calling `field.setAccessible(true)` and obtaining a `MethodHandles.Lookup` via `privateLookupIn`?

<details><summary>Answer</summary>

Both perform the same underlying module check — whether the target's module has opened the relevant package to the caller's module — but they differ in shape and reuse. `setAccessible(true)` is a per-`AccessibleObject`, mutable, side-effecting call that throws or silently flips a flag; the resulting accessibility is a hidden property of that one `Field` or `Method` instance. `privateLookupIn` performs the check once and returns a `Lookup` object carrying that capability explicitly, which can then be used to `find`-resolve any number of members from the target class without repeating the module check per member.

</details>

**Q5.** On JDK 21, does a `VarHandle.set` and a reflective `Field.set` (after `setAccessible(true)`) behave the same way against a non-static `final` field? What did the measurement show?

<details><summary>Answer</summary>

No. `findVarHandle` on the non-static `final` field `Restriction.type` succeeded, and `vh.get(restriction)` worked, but `vh.set(restriction, "SELF_EXCLUDED")` threw `UnsupportedOperationException` with a null message — `VarHandle` enforces `final` at the API level. The equivalent reflective path, `field.setAccessible(true)` followed by `field.set(restriction, "SELF_EXCLUDED")`, succeeded on the same JDK. Core reflection still permits writing a `final` instance field; `VarHandle` does not.

</details>

**Q6.** What was removed from the JVM in Java 17, and what evidence in this file demonstrates it?

<details><summary>Answer</summary>

The `--illegal-access` command-line flag, which had controlled how permissively the module system treated deep reflection into JDK internals across Java 9–16, was removed entirely in Java 17. The measured evidence is the JVM's own output when passed the flag on JDK 21: `Ignoring option --illegal-access=permit; support was removed in 17.0` — the warning itself names the release that removed support, making the JVM its own primary source for the claim.

</details>

**Q7.** Why is `invokeExact` faster than `invoke` on a `MethodHandle`, and which one did this file's 1.4 ns/op figure measure?

<details><summary>Answer</summary>

`invokeExact` requires the call site's static argument and return types to match the handle's `MethodType` exactly, so the JVM can call straight through with no adaptation. `invoke` allows a mismatched call site by inserting `asType` conversions — boxing, widening, casting — at the cost of that extra adaptation work. The measured 1.4 ns/op figure in this file is for `invokeExact`; no figure for `invoke` was measured, and the file is explicit about not extending that number to `invoke`.

</details>

**Q8.** A `LedgerEntryMapper` calls `getDeclaredField` and `setAccessible(true)` once per constructed instance rather than once per `LedgerEntry` mapped. Why does that design choice matter more than the per-call cost of `Method.invoke` or `Field.get` itself?

<details><summary>Answer</summary>

The measured per-call dispatch cost of reflective invocation (roughly 3–4.5 ns/op) is small even at QuizStakes' scale — a full day of settlement-path reflective reads costs single-digit milliseconds. The dominant real cost is metadata lookup: each call to `getDeclaredFields()` or `getDeclaredField()` allocates a fresh array and fresh `Field` objects, and repeating that per row rather than once at construction turns into tens of millions of unnecessary allocations a day at QuizStakes' ledger volume. Resolving the `Field`/`Method`/`MethodHandle` once and caching it, exactly as `LedgerEntryMapper`'s constructor does, is the actual optimisation that matters.

</details>

## Open questions

1. Whether JEP 396 is in fact the JEP that made strong encapsulation of JDK internals the default in JDK 16, and whether JEP 403 is the JEP that removed `--illegal-access` in JDK 17 — the JEP text could not be fetched this session (openjdk.org returned HTTP 403 to the orchestrator); the measured JVM behaviour (the `--illegal-access` warning naming `17.0`, and the measured `InaccessibleObjectException` on JDK 21) is treated as the load-bearing evidence instead. Reading the JEP text directly would settle the exact JEP-to-behaviour mapping.
2. Whether JEP 416 is in fact the JEP that reimplemented core reflection on method handles in JDK 18, and whether that reimplementation is the specific mechanism behind the measured round-0-to-round-1 warm-up drop in `Method.invoke`, as opposed to some other JIT-level effect. OpenJDK source for `jdk.internal.reflect.MethodHandleAccessorFactory` (or equivalent) across 17 and 18, or the JEP text itself, would settle this.
3. Whether a `MethodHandle` held in a `static final` field is treated as a JIT-level constant, and precisely which optimisation (constant folding of the target versus call-site specialisation) that produces — asserted here as a widely-cited pattern rationale, not sourced to JLS/JVMS/Javadoc/JEP text in this session. OpenJDK HotSpot source for `MethodHandle` intrinsics, or a JMH benchmark isolating the effect, would settle it.

---

**Leaves covered:** 2.12.4–2.12.6 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 458
