# 03 Java Core — Reflection: `final` fields and the security surface — INTERMEDIATE (§2.12, 2.12.10, 2.12.11)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Proxies, frameworks and generics](02b-proxies-frameworks-and-generics.md) · Next: [MyString and MyStringBuilder](../build-it/01-mystring-and-mystringbuilder.md)

`02-reflection.md` owns `Class` objects, the naming methods and member lookup. `02a-access-cost-and-method-handles.md` owns `setAccessible`, its cost, and the `MethodHandle`/`VarHandle` layer. `02b-proxies-frameworks-and-generics.md` owns proxies, where reflection appears inside Spring/Jackson/JPA, and generic reflection. This file closes §2.12 with the one thing reflection was never supposed to be able to do, and the platform's long retreat from letting it. The question this file answers, in bold: **can you still write to a `final` field through reflection on Java 21, and what happened to the mechanism that was supposed to stop you?**

## 1. Setting a `final` field reflectively (2.12.10)

`final` is a promise made to two different audiences at once. To the reader of the code it says: this value never changes after construction, you can reason about it once and stop thinking about it. To the JIT compiler it says something stronger: you may treat this as a true constant, cache it in a register, hoist the read above a loop, or fold it directly into a call site, and you never need to reload it from memory. Reflection breaking that promise is not a style violation. It makes the second audience's optimizations unsound — a compiler that assumed a value could never change now has to worry it might, silently, from code it never analyzed. That is the entire reason the platform has spent a decade tightening this door, and it is the answer to "why does anyone care" that should anchor everything below.

### Why it exists

`Field.set` on a `final` field is not a language feature — the language has no syntax for it. It exists because the reflection API was designed, in 1997, as a general-purpose member-access facility with one universal escape hatch: `setAccessible(true)` suppresses the language-level access check, and historically that suppression extended to the `final` modifier as well as to `private`/`protected`/package visibility. Frameworks that predate cleaner alternatives — old ORMs restoring persisted state, test frameworks resetting fixtures, deserializers reconstructing objects without a constructor — used it because there was no other way to put a value into a field that the class's own API never exposed a setter for. `02b-proxies-frameworks-and-generics.md` covers how modern JPA providers now generate bytecode-enhanced accessors instead of leaning on this escape hatch, precisely because it is this fragile; the historical need for it, not the modern practice, is why the capability exists in the API surface at all.

### How it works

`setAccessible(true)` suppresses Java-language-level access checks (visibility and, historically, finality) at the point the `Field` object is used, not at the point it was obtained. Whether the checked-suppressed write actually lands, and whether anything downstream ever observes it, now depends on exactly what kind of `final` field it is. The orchestrator's measured matrix on JDK 21 draws the line precisely:

| Target | Declaration | Measured result of `Field.set` |
|---|---|---|
| Non-static, non-constant `final` instance field | `static class Restriction { final String type; Restriction(String t){ this.type = t; } }` | **Succeeded.** After `f.set(r, "ALL_BLOCKED")`, both `f.get(r)` and the direct read `r.type` returned `ALL_BLOCKED` |
| Non-static `final` field with a compile-time constant initializer | `static class Holder { final int stakeMinor = 420; }` | `set` did not throw, but a subsequent direct read `h.stakeMinor` still printed `420` |
| `static final` primitive | `static class Holder { static final int CAP = 100; }` | `IllegalAccessException: Can not set static final int field Ver9$Holder.CAP to java.lang.Integer` |
| `static final` reference | `static final List<String> SOURCES = List.of("SYSTEM_ONBOARDING");` | `IllegalAccessException: Can not set static final java.util.List field VerA$Restriction.SOURCES to java.util.ImmutableCollections$List12` |
| A record component's backing field | `record Money(BigDecimal amount, String currency) {}` | `IllegalAccessException: Can not set final java.math.BigDecimal field Ver9$Money.amount to java.math.BigDecimal` |

Four facts fall out of that table and each one is load-bearing on its own.

**A plain `final` instance field is still writable on JDK 21.** This is the fact most engineers assume is false, and it is not. `setAccessible(true)` suppressed the access check, and `Field.set` on a non-static field whose value is not a compile-time constant wrote the memory. In this measurement both the reflective read and the direct field read observed the new value. State the honest caveat rather than gloss over it: that the direct read observed the change is not a guarantee for all code shapes. The JIT is entitled to have already hoisted a read of a `final` field into a register or a constant pool slot inside a hot method, and whether a given read observes a reflective write after the fact is exactly the property under active removal — that a `final` field's value is only trustworthy if nothing reflective ever touched it. **Unverified:** what the JIT actually does under optimization for this exact shape is a JVM-internals question; see guide 06 (JVM internals) for the compiler side.

**Pitfall:** the constant-folded case is the trap, not the plain instance field case. `final int stakeMinor = 420;` is a compile-time constant expression, which the JLS calls a *constant variable*. `javac` folds its value directly into the bytecode of every method that reads it, so a direct read never touches the field at all — it reads a literal baked in at compile time. The measured behavior confirms this exactly: `Field.set` on `stakeMinor` threw nothing (the write to the field's memory succeeded), yet the direct read `h.stakeMinor` still printed `420`, because that read was never going to consult the field. `../classes-and-initialization/04-internals-final-and-constant-folding.md` owns the full mechanism of constant folding; `../strings/01b-the-string-pool.md` owns the identical story for `String` constants. The wrong belief is "the reflective write did nothing" — the truth is there was nowhere for the read to look.

Worked in full, the shape that produced the measurement:

```java
final class StakeHolder {
    final int stakeMinor = 420;
}

StakeHolder holder = new StakeHolder();
Field field = StakeHolder.class.getDeclaredField("stakeMinor");
field.setAccessible(true);

field.set(holder, 999);                 // does not throw
System.out.println(field.get(holder));  // reads the field object directly: 999
System.out.println(holder.stakeMinor);  // reads the compiled-in literal: 420
```

The two prints diverge because they are not reading the same thing. `field.get(holder)` performs the reflective read, which genuinely consults the object's memory and reports the write that just happened — `999`. `holder.stakeMinor` is a direct field access compiled by `javac`, and because `stakeMinor` is a constant variable, `javac` never emitted a `getfield` instruction for it at all; it emitted the literal `420` directly into the calling method's bytecode, the same way it would for any other constant expression used inline. There is no code path left at that call site that could observe the reflective write, no matter how the write itself is performed. This is worse than a failed write, because a failed write throws and tells you it failed — this one succeeds, and the divergence between "the field's memory changed" and "no caller will ever see it" produces no exception, no log line, and no compiler warning anywhere in the chain.

**`static final` is refused outright**, for both a primitive and a reference type, and both throw `IllegalAccessException` naming the field and the rejected value's type. The platform draws the line here because a `static final` is the single most aggressively constant-folded thing in the language: a `static final int` is inlined into every *caller's own class file* at compile time (`../classes-and-initialization/02-modifiers.md` owns this inlining rule across compilation units), so mutating the one copy in the declaring class would still leave every already-compiled caller holding the old literal. There is also no per-instance state to write — a static field has exactly one value for the whole JVM — so the JDK simply refuses the operation rather than let it silently do nothing.

The QuizStakes shape that makes this concrete is the bonus cap:

```java
final class BonusService {
    static final int CAP_MINOR = 10000; // 100.00 in minor units, capped per rules
    Money capApplied(Money grant) {
        return grant.amount().movePointRight(2).intValue() > CAP_MINOR
                ? new Money(new BigDecimal("100.00"), grant.currency())
                : grant;
    }
}
```

Any class compiled against `BonusService` that reads `BonusService.CAP_MINOR` in an expression that itself qualifies as a constant expression gets `10000` baked into its own bytecode at the point of use, in the *caller's* class file, not `BonusService`'s. If a reflective write forced `CAP_MINOR` to a different value at runtime — which JDK 21 refuses outright, as measured — every already-compiled caller across the deployed jar would still be comparing against `10000`, because recompiling `BonusService` alone does not touch the callers that already baked the old constant in. The refusal is not merely defensive; it prevents an operation that could not produce a coherent result even if it were allowed, since half the codebase would observe the change and the already-compiled half would not.

**A record component's field is refused**, with the same exception type but a message that omits `static`. Records were specified from the start (Java 16) as shallowly immutable value carriers with no constructor-bypassing backdoor, so the platform inherited no backward-compatibility obligation to let reflection break them the way it can break an ordinary class. Hidden classes, introduced by `Lookup.defineHiddenClass` in Java 15, are protected the same way. `../records-and-sealed/01a-object-methods-sealed-and-fit.md` owns records' generated-member and immutability guarantees.

**Interview:** "can reflection write a `final` field?" has no single correct yes/no — the correct answer names all four rows: yes for a plain instance field, apparently-yes-but-actually-no for a constant-folded one, no for `static final`, no for a record component. A follow-up worth anticipating: "why does the constant-folded case not also throw, if the platform is trying to protect `final`?" — because `Field.set`'s job is only to write the field's storage location, and it does that successfully; the fact that no caller reads that storage location afterward is a property of `javac`'s inlining decision at compile time, entirely upstream of anything `Field.set` can see or refuse at runtime.

The classic escape from the `static final` refusal does not survive to JDK 21. The recipe every "how to set a static final field" answer on the internet repeats is: reflect on `Field` itself, clear the `Modifier.FINAL` bit from `Field`'s own `modifiers` field, then retry the `set`. On JDK 21:

```java
Field mods = Field.class.getDeclaredField("modifiers");
```

threw verbatim:

```
java.lang.NoSuchFieldException: modifiers
```

`java.lang.reflect.Field` no longer exposes a field reachable by that name. There is nothing to clear. This is the headline version trap in this file — treat any answer that says "reflect on the modifiers field to force a static final write" as describing an API that stopped existing.

The version arc is now measured directly, not received. The identical harness — the same `Restriction`/`Holder` shapes used above — was compiled and run with each JDK's own `javac` on Oracle JDK 11.0.27, JDK 17.0.15, and JDK 21.0.7, all macOS aarch64:

| JDK | Plain `final` instance field via `Field.set` | `static final int` via `Field.set` | The `Field.modifiers` hack |
|---|---|---|---|
| **11.0.27** | **OK** — direct read afterward was `ALL_BLOCKED` | `IllegalAccessException: Can not set static final int field Fin$Holder.CAP to java.lang.Integer` | **WORKS** — `SOURCES=[ADMIN]` after clearing the `FINAL` bit; stderr carried the JDK 9-era illegal-access warning block |
| **17.0.15** | **OK** — `ALL_BLOCKED` | Identical `IllegalAccessException` message | **DEAD** — `NoSuchFieldException: modifiers` |
| **21.0.7** | **OK** — `ALL_BLOCKED` | Identical `IllegalAccessException` message | **DEAD** — `NoSuchFieldException: modifiers` |

Three things fall out of that table, and they are sharper and more specific than the popular version of this story. A plain `final` instance field has been reflectively writable continuously across every one of these three releases, and **still is** on 21 — this was never removed, and nothing about it is scheduled to change short of JEP 500. `static final` has been refused with the identical exception message across all three releases — there was no "it used to be allowed and got locked down" moment for `static final` within this window; it was already refused on 11. The only cell that actually changed across the window is the `modifiers` hack: it worked on 11, and it is gone by 17. That means the commonly repeated claim "the modifiers hack stopped working in Java 9 because `setAccessible` changed" is imprecise — the *reflective operation itself* (`Field.set` on `static final`) was already refused before that, and what changed later was specifically the ability to force it by tampering with `Field`'s own bookkeeping.

The JDK 11 run is worth quoting in full, because it is the JVM warning about the exact change that JDK 17 goes on to make — read line by line, it is a five-year advance notice:

```
WARNING: An illegal reflective access operation has occurred
WARNING: Illegal reflective access by Fin (file:/private/tmp/jc-m/outF/) to field java.lang.reflect.Field.modifiers
WARNING: Please consider reporting this to the maintainers of Fin
WARNING: Use --illegal-access=warn to enable warnings of further illegal reflective access operations
WARNING: All illegal access operations will be denied in a future release
```

Line one names the class of operation being logged — an "illegal reflective access," meaning one that strong encapsulation would refuse outright once it stopped being merely warned about. Line two is the specific instance: code named `Fin`, loaded from a file: URL (unnamed module, classpath code, exactly the deployment shape most Spring Boot applications use), reaching into `Field.modifiers` — the very field this file's headline trap depends on. Line three is boilerplate asking the offending library's maintainers to fix it, which presupposes this was meant to be a temporary grace period, not a permanent feature. Line four names the actual escape hatch of the era, `--illegal-access=warn`, which JDK 11 defaults to `permit`-with-warning rather than outright denial. Line five is the JVM stating its own future plan in plain language: "will be denied in a future release." Pair that with the JDK 21 measurement already on file for `--illegal-access=permit` itself:

```
$ java --illegal-access=permit -version
Java HotSpot(TM) 64-Bit Server VM warning: Ignoring option --illegal-access=permit; support was removed in 17.0
java version "21.0.7" 2025-04-15 LTS
```

and the two measurements together are the whole arc in the JVM's own words, spanning two real releases: 11 warns and names the future in five lines of stderr; 17 is the future the warning named — the flag stops working, the field stops existing, both denied exactly as promised. Java 8 is deliberately left out of the table rather than asserted: the only Java 8 install available in this environment is x86_64, and running the harness against it was not possible, so no Java 8 measurement is claimed anywhere in this file.

**Insight:** the newer invocation API refuses a write the older one permits, on the identical field. `VarHandle` is not merely "the same capability with a different name" — it is stricter than `Field` on purpose. On the same non-static, non-constant `final` field that `Field.set` wrote successfully above:

```java
Restriction r = new Restriction("STAKE_BLOCKED");

Field f = Restriction.class.getDeclaredField("type");
f.setAccessible(true);
f.set(r, "ALL_BLOCKED");                 // succeeded, measured earlier

var lookup = MethodHandles.privateLookupIn(Restriction.class, MethodHandles.lookup());
VarHandle vh = lookup.findVarHandle(Restriction.class, "type", String.class);

System.out.println(vh.get(r));           // reads ALL_BLOCKED — vh.get sees Field.set's write
try {
    vh.set(r, "SELF_EXCLUDED");
} catch (UnsupportedOperationException e) {
    System.out.println(e.getMessage()); // prints: null
}
```

Measured: `findVarHandle` did not throw — the handle was found, on a `final` field, without complaint. `vh.get(r)` worked, returning the current value (which, run in this order, is `ALL_BLOCKED` — `VarHandle` reads are not blind to `Field`'s earlier write; only the *write* direction is refused). `vh.set(r, "SELF_EXCLUDED")` threw `UnsupportedOperationException` with a `null` message. `02a-access-cost-and-method-handles.md` owns `VarHandle` and `privateLookupIn` generally; the point that belongs here is the asymmetry itself. The platform is not closing this by breaking the old, still-supported API — `Field.set` above is not deprecated and is not scheduled for removal on any target this file can cite. It is declining to extend the capability to the new one, and steering all new call sites toward the API that already refuses. That is a materially better interview answer than "reflection on final fields is deprecated," because the deprecation framing is simply false for `Field`, while the asymmetry framing is exactly what was measured.

The direction that asymmetry points toward is JEP 500, "Prepare to Make Final Mean Final," targeted at JDK 24 (verified by web search against openjdk.org mailing-list and JEP listings; the JEP pages themselves returned HTTP 403 to direct fetch, so this is corroborated-secondary, not primary — cite it at that confidence, no higher). In JDK 24 the process began of removing the `sun.misc.Unsafe` methods that permit mutation of `final` fields. The stated rationale: the mere existence of APIs that can mutate a `final` field makes it impossible to trust the value of *any* `final` field in *any* program, which costs both safety and performance everywhere, not just in the code that uses the escape hatch. A limited-purpose replacement API is planned for exactly one case: serialization libraries that must mutate `final` fields during deserialization, because that is the one place the ordinary constructor path cannot run.

That carve-out is not abstract — this batch measured the exact capability it exists to preserve, and the two shapes are worth setting side by side. An ordinary `Serializable` class:

```java
final class Split2 implements Serializable {
    final int bonusMinor;
    final int cashMinor;
    Split2(int bonusMinor, int cashMinor) {
        if (bonusMinor + cashMinor != 333) {
            throw new IllegalArgumentException("split does not sum to stake");
        }
        this.bonusMinor = bonusMinor;
        this.cashMinor = cashMinor;
    }
}
```

has a constructor that would refuse `34 + 300`, because `34 + 300 = 334`, not `333`. But `ObjectInputStream` deserializing this class never calls that constructor at all — it allocates the object via a native path and writes `bonusMinor` and `cashMinor` directly from the byte stream, field by field, exactly the way reflection's `Field.set` writes an instance `final` field. A forged stream carrying `bonusMinor=34, cashMinor=300` reconstructed as `Split2[34+300=333]` — the object's own `toString` reporting a sum that its constructor would have rejected — with no exception anywhere in the path. `../serialization/02a-magic-methods-and-constructor-bypass.md` owns the full mechanism of why the constructor is bypassed.

The equivalent **record**:

```java
record Split2Record(int bonusMinor, int cashMinor) implements Serializable {
    Split2Record {
        if (bonusMinor + cashMinor != 333) {
            throw new InvalidObjectException("split " + bonusMinor + "+" + cashMinor + " != 333");
        }
    }
}
```

refused the identical forged stream, because a record's deserialization path is specified to go through the canonical constructor — there is no direct-field-write bypass for records the way there is for an ordinary class. The measured result was `InvalidObjectException: split 34+300 != 333`, thrown from the compact canonical constructor exactly as it would be for a normally-constructed instance. `../serialization/02b-externalizable-records-and-lambdas.md` owns records' serialization path in full.

That pair is the concrete shape of what JEP 500 is trying to preserve versus what it is trying to remove: keep the narrow serialization-library path — the mechanism `ObjectInputStream` uses to populate `Split2`'s fields without its constructor, which a well-behaved serialization library needs and which a record does not, because a record's own specification already forces validation — and remove the general-purpose reflective write that any arbitrary caller can invoke on any class through `Field.set`, which is a much broader capability than deserialization ever needed. Be explicit that this is intent and direction stated in a "Prepare to" JEP, not a scheduled removal — no removal release for ordinary reflective `final` writes has been announced, and stating one would be wrong.

The practical rule for QuizStakes: never write a `final` field reflectively in production code. `Money`, `LedgerEntry`, `StakeSplit`, and `RestrictionKey` are `final`-field value types whose invariants exist specifically to stop money being created — the 3.33 stake splitting as 0.33 bonus + 3.00 cash, never 0.34 + 3.00 — and any code path that can rewrite those fields after construction has undone every constructor check protecting that invariant. The two places engineers are actually tempted: resetting a `final Clock` in a test, and patching a `final` config constant at runtime. Both have a better answer than reflection.

The temptation, worked through: a `Bonus` aggregate that computes its own 30-day expiry from a `final Clock` field looks tidy until a test needs to fast-forward time:

```java
final class Bonus {
    private final Clock clock;
    private final Instant grantedAt;
    Bonus(Clock clock, Instant grantedAt) {
        this.clock = clock;
        this.grantedAt = grantedAt;
    }
    boolean expired() {
        return Duration.between(grantedAt, clock.instant()).toDays() > 30;
    }
}
```

The reflective-write instinct is to grab the already-constructed `Bonus` in a test and force its `clock` field to a fixed instance obtained from `Clock.fixed`. The better answer is that `clock` was already a constructor parameter for exactly this reason — the test simply constructs a second `Bonus` with a fixed clock instead of mutating the first one:

```java
Bonus bonus = new Bonus(Clock.fixed(Instant.parse("2026-09-30T00:00:00Z"), ZoneOffset.UTC),
                         Instant.parse("2026-08-01T00:00:00Z"));
assertTrue(bonus.expired());
```

no reflection anywhere in the test, and the class's own `final` invariant on `clock` is never in question. Guide 16 (Testing) and `../date-and-time/02e-clock-precision-and-storage.md` own constructor-injected `Clock` in full. Make the "constant" a method or an injected configuration value instead of a `final` field if it genuinely needs to vary at runtime. The one legitimate exception is a serialization or object-mapping library implementing exactly the deserialization path JEP 500 preserves — and even there, the library should validate the reconstructed invariants before trusting the object, the way the record's canonical constructor does automatically.

> Reflective writes to a `final` field succeed for a plain instance field, silently miss for a compile-time-constant one, and are refused outright for `static final` and for record components — and the platform's direction, via `VarHandle`'s stricter refusal and JEP 500, is toward refusing all of it except a narrow serialization carve-out.

## 2. Reflection as a security surface, and the retreat of the Security Manager (2.12.11)

Every access modifier in Java is two things at once: a compile-time contract the compiler enforces at every call site, and a runtime check that reflection has historically been able to ask to have skipped via `setAccessible(true)`. That means `private` was never actually a security boundary in the sense of "code outside this class cannot reach this state" — it was a design boundary that reflection could always negotiate past, given the JVM's permission to do so. The platform's response over roughly the last decade has been to stop granting that permission by default and to make "ask and be granted" require an advance declaration instead — and, separately, to delete the one mechanism whose entire job was to decide whether to grant it.

### Why it exists

Reflection is the platform's general-purpose "resolve a name to code and run it" primitive: it turns a *string* into a class, a member, and a call. That is the identical primitive that most deserialization gadget chains are trying to reach — not because deserialization and reflection are the same feature, but because reflection is the sink almost every "do something arbitrary from data" chain ends at. `../serialization/02c-attack-surface-filters-and-the-practical-rule.md` owns the deserialization attack-surface case in full; the connection worth stating plainly here is that reflection is the general mechanism deserialization gadgets are usually built to invoke.

Note the asymmetry with §2.12.10 above: everything in that concept was about reflection doing something the *language* forbids (writing a `final` field). This concept is about reflection doing something entirely ordinary — invoking a method, reading a field, instantiating a class — except that the *name* of the thing being invoked, read, or instantiated came from data the platform cannot trust. The mechanism is not exotic; the danger is entirely in where the name came from.

### How it works

**The concrete exposure.** In a service shaped like QuizStakes, any place a class name, method name, or field name is taken from *outside* the trust boundary is a code-execution primitive, not a string: a pluggable strategy loader keyed by a configured class name, a `Class.forName` call on a name that came from a request or a database row, a scripting or templating engine evaluating attacker-influenced expressions, an `ObjectMapper` configured with polymorphic typing that resolves a type from a JSON field, a JNDI lookup driven by external input. `02-reflection.md` measured a detail that matters directly here: the one-argument form of `Class.forName` *runs the class's static initializer* as part of resolving the name. That means resolving an attacker-named class can execute code before any inspection of the resulting `Class` object has happened at all — the mitigation has to happen before resolution, not after.

Concretely, a `ScreeningService` that resolves a watchlist-matching strategy by a configured class name looks like this if written carelessly:

```java
String strategyClassName = requestBody.get("strategyClass"); // attacker-influenced
Class<?> strategyClass = Class.forName(strategyClassName);   // one-arg form: runs <clinit> now
Object strategy = strategyClass.getDeclaredConstructor().newInstance();
```

By the time `strategyClass` is inspected for whether it actually implements the expected strategy interface, its static initializer has already run to completion — any side effect in that initializer, from writing a file to opening a socket, has already happened, regardless of what the code does with `strategy` next or whether it ever calls a method on it. The correct control is an allow-list of permitted names checked *before* `Class.forName` is called at all, never a deny-list of known-bad ones, because a deny-list only ever covers the attacks already seen:

```java
private static final Set<String> ALLOWED_SCREENING_STRATEGIES =
        Set.of("com.quizstakes.screening.SanctionsMatchStrategy",
               "com.quizstakes.screening.PepMatchStrategy");

String strategyClassName = requestBody.get("strategyClass");
if (!ALLOWED_SCREENING_STRATEGIES.contains(strategyClassName)) {
    throw new IllegalArgumentException("unrecognized screening strategy: " + strategyClassName);
}
Class<?> strategyClass = Class.forName(strategyClassName, true, ScreeningService.class.getClassLoader());
```

checking membership in `ALLOWED_SCREENING_STRATEGIES` before any call that could resolve or initialize an attacker-named class.

**Strong encapsulation is the mitigation that actually shipped**, and it is worth being precise about what it does and does not cover. The measured evidence:

```java
Field f = String.class.getDeclaredField("value");
f.setAccessible(true);
```

with no module flags, on JDK 21, threw:

```
java.lang.reflect.InaccessibleObjectException: Unable to make field private final byte[] java.lang.String.value accessible: module java.base does not "opens java.lang" to unnamed module @12d3a4e9
```

With `--add-opens java.base/java.lang=ALL-UNNAMED` supplied, the call succeeded, and the `byte[]` backing `"AA-801"` measured **6 bytes** long. The module-state measurements clarify the mechanism: `Object.class.getModule().isExported("java.lang")` was `true`; `isOpen("java.lang", unnamedModule)` was `false` without the flag and `true` with it; `isExported("jdk.internal.misc")` was `false` in both cases. **Exported and open are independent properties** — a package can be exported (its public API is usable at compile time) without being open (its non-public members are reachable via deep reflection). `../language-substrate/02-packages-modules-annotations.md` owns the module system's `exports` versus `opens` distinction in full; `02a-access-cost-and-method-handles.md` owns `setAccessible` and `--add-opens` mechanically.

Give the honest scorecard rather than the popular oversimplification. Strong encapsulation protects the JDK's own internals by default, and protects *your* named modules if you declare them with `module-info.java`. It does nothing at all for classpath code living in the unnamed module — and that is exactly where most Spring Boot applications run: every class in a typical fat jar and every library on its classpath is mutually, unconditionally reflectively open to every other class in the unnamed module, with or without any flag. Readers routinely believe "the module system fixed reflection security"; for a standard Spring Boot 3.x application on the classpath, it changed essentially nothing about the application's own code — only about the JDK's internals.

The platform also encapsulated its own reflective machinery, not just the classes reflection reaches: `Field.class.getDeclaredField("modifiers")` throwing `NoSuchFieldException` (measured above, in Concept 1) is the JDK removing the reflective handle onto its own reflection implementation.

**The Security Manager, mechanism and disappearance.** A `SecurityManager` is a single global object, installed once per JVM, consulted by `checkPermission` calls scattered throughout the standard library at sensitive operations — file access, socket creation, reflective access, `System.exit`, class loading. Each call site asked the installed manager to approve or deny the operation against a `Policy` that granted permissions to code sources (a JAR's origin, a signer), with `AccessController.doPrivileged` available to temporarily elevate a trusted block's effective permissions above its caller's. In shape, not as anything to run, the mechanism looked like this:

```java
// A policy file entry (not Java code) granting one code source one permission:
// grant codeBase "file:/opt/quizstakes/plugins/-" {
//     permission java.io.FilePermission "/opt/quizstakes/plugin-data/-", "read";
// };

// A library checking that it is allowed to do the sensitive thing itself,
// before doing it, so the framework's own reduced-trust callers cannot:
SecurityManager sm = System.getSecurityManager();
if (sm != null) {
    sm.checkPermission(new FilePermission("/opt/quizstakes/plugin-data/-", "read"));
}
```

Every reflective operation this file has measured — `setAccessible`, `Field.set` on a `private` or `final` field — used to route through exactly this same `checkPermission` call with a `ReflectPermission("suppressAccessChecks")`, before the manager itself was retired; strong encapsulation's module-boundary check is architecturally its replacement for that one specific permission, enforced by the module system itself rather than by an installed, policy-driven object.

It failed for reasons specific enough to state, not just "it was old." It was designed for a threat model — untrusted Java applets running in the same JVM as trusted code, needing a fine-grained in-process sandbox — that no longer exists; browsers stopped running applets years ago. Server-side adoption was always rare because writing a correct, complete policy file for a modern dependency graph with hundreds of transitive libraries is not practically achievable. Every `checkPermission` call site was a permanent maintenance and performance cost paid by every JVM whether or not a manager was ever installed. And it never actually contained a determined attacker who already had arbitrary code execution inside the sandboxed region — a security boundary drawn inside a single process, enforced by cooperating code, is not the same strength of boundary as a process or OS boundary.

It was first deprecated for removal (commonly cited as JEP 411 in Java 17 — mark the JEP number `**Unverified:**` if repeating it, since it was not independently re-verified this session) and then, per the corroborated-secondary sourcing above, **permanently disabled by JEP 486, targeted at Java 24**. Word the outcome precisely: in Java 24 the Security Manager *cannot be activated* — not at JVM startup via a flag, not at runtime via `System.setSecurityManager` — and the Java Platform specification itself was revised so that neither developers nor other platform classes can enable or refer to it. This is described in the JEP as the next step *toward* removal, so the correct word is **disabled, not yet removed** — the classes and API surface still exist in Java 24, they simply cannot be turned on. On this file's target, **Java 21, the Security Manager still exists and can still be installed and used** — everything above about Java 24 is a "what is coming" item, not a "what is true on 21" item.

The question this leaf exists to answer is what replaces it, and the honest answer is: nothing, at the in-process level, and that is a deliberate architectural choice rather than a gap. The replacement is not one mechanism but a different layering: strong encapsulation covers the platform's own internals; operating-system and container-level isolation — separate processes, containers, seccomp profiles, read-only filesystems, non-root users — covers everything the Security Manager nominally tried to contain from inside the JVM; and input validation plus allow-lists at the specific points where external data names code covers the reflection-as-sink risk directly.

| What the Security Manager nominally protected | Why it did not work | What actually does the job on Java 21 |
|---|---|---|
| File access | Policy files for a real dependency graph were unmanageable in practice | Container filesystem permissions, read-only mounts |
| Network access | Same policy-authoring problem, plus no defense once code was already running with intended network permissions | Container/network-namespace egress rules, service mesh policy |
| Reflective access to private members | Could be, and routinely was, granted broadly to make frameworks work at all | Strong encapsulation (`opens`/`exports`) for named modules; allow-listed class/member names at the code boundary for the unnamed module |
| `System.exit` | Rarely restricted in practice; a process-level concern anyway | Container orchestration restarts/kills the process; no in-JVM substitute needed |
| Class loading | Manager checks could gate `defineClass`, but a compromised process could often still load intended code | Signed/verified artifact supply chain, restricted classpath composition, no untrusted dynamic loading |

Each row deserves its own sentence of why, because "containers replaced the Security Manager" is too glib on its own. File access: a `Policy` file granting `java.io.FilePermission` per code source had to be hand-authored and kept correct as a dependency tree grew into the hundreds of jars, which nobody actually did correctly at scale; a container's filesystem namespace enforces the same boundary at the OS level, outside the JVM's control entirely, so no application code — however it got compromised — can widen it. Network access: the same authoring burden applied to `SocketPermission`, and even a correct policy only restricted *new* connections the sandboxed code opened, not what it did with a connection the application itself had legitimately been given; a network namespace or service-mesh egress policy restricts the process's sockets regardless of which line of Java code asked for them. Reflective access to private members: this is the one the Security Manager was worst at, because most real applications granted broad reflective permission just to make ORMs and DI frameworks function, so the "protection" was routinely disabled in practice; strong encapsulation flips the default to closed for the JDK's own packages and forces an explicit `opens` declaration, while an allow-list at the code boundary is the only thing that actually restricts *your* classpath code, since the module system does not. `System.exit`: a `RuntimePermission("exitVM")` check existed but was rarely the interesting attack surface, since a process calling its own exit is a self-inflicted denial of service, not a privilege escalation; container orchestration already restarts or replaces a killed process, so nothing in-JVM needs to intervene. Class loading: `checkPackageAccess` and friends could gate which classes a given `ClassLoader` was allowed to define, but a process that already had code execution could usually still reach the classes it wanted through some code path the policy failed to anticipate; a signed, verified artifact supply chain and a classpath fixed at deployment time — no dynamic loading of untrusted bytecode — closes the same gap earlier, before the JVM is even involved.

Guide 13 (Web security) owns the full treatment of input-driven code execution and the broader mitigation architecture this section only sketches; guide 06 (JVM internals) owns the runtime side of module enforcement and classloading.

The operational checklist for QuizStakes, as the practical deliverable of this leaf:

1. **Never resolve a class, method, or field name taken from client input, directly or indirectly.** This includes names that arrive indirectly — a status code, a document type, or a rail identifier that gets string-concatenated into a class name before `Class.forName` is called is exactly as dangerous as a raw class name in the request body.
2. **If a plugin or strategy mechanism must exist, allow-list the permitted names explicitly**, checked before any resolution call, and resolve with the three-argument `Class.forName(name, false, loader)` so that resolution does not run the class's static initializer before the name has been checked; only pass `initialize=true` once the resolved class has been confirmed to implement the expected interface.
3. **Keep `--add-opens` out of runtime configuration unless a specific, named library demands it**, and record the reason it was added, because every open package is a permanent widening of what any code on the classpath — including a compromised dependency — can reach reflectively.
4. **Run the service as a non-root user inside a container with a read-only filesystem**, rather than reaching for an in-JVM sandbox that no longer meaningfully exists; the isolation boundary that used to be attempted with a `SecurityManager` policy is enforced far more reliably by the container runtime and the kernel.
5. **Treat management endpoints — JMX, RMI, and the `InternalPlatforms` actuator surface — as the highest-value reflective attack surface in the estate**, because their entire design purpose is to invoke arbitrary named members remotely; an exposed JMX port or an unauthenticated actuator endpoint is a standing invitation to do exactly what this leaf describes as dangerous, by design rather than by bug.

> Reflection turns a name into executable code, which is why strong encapsulation now gates it by default for the JDK's own internals, why the Security Manager that once tried to police it in-process is being disabled rather than replaced, and why the real defense for classpath code is an allow-list at the boundary where external data would otherwise name code.

**Interview:** "how would you stop a service from being exploited through reflection" invites a one-sentence trap answer — "enable the Security Manager" — that is wrong on Java 21 (it still exists but was never a reliable server-side control) and will be flatly wrong on Java 24 (it cannot be enabled at all). The correct one-line answer names the actual layering: allow-list any externally-influenced class or member name before resolution, keep `--add-opens` off by default, and put the process-level isolation at the container, not the JVM.

## Pitfalls

### A `final` field can never be changed after construction, reflection or not

**Wrong**

```java
static final class Restriction {
    final String type;
    Restriction(String type) { this.type = type; }
}

Restriction r = new Restriction("STAKE_BLOCKED");
Field f = Restriction.class.getDeclaredField("type");
f.setAccessible(true);
f.set(r, "ALL_BLOCKED");
System.out.println(r.type); // prints ALL_BLOCKED, not STAKE_BLOCKED
```

**Right**

```java
static final class Restriction {
    final String type;
    Restriction(String type) { this.type = type; }
}

// Design the type so nothing outside the constructor can reach `type` at all:
// no reflective access path is closed by `final` alone — closing it requires
// either a SecurityManager-free deployment discipline (module encapsulation,
// no --add-opens for this package) or simply not exposing the class to
// reflection-capable code you do not control.
```

**Why people believe it:** the language enforces `final` at every compile-time call site with no exception, so it is natural to assume the guarantee is absolute rather than a compile-time-and-normal-runtime guarantee that reflection's `setAccessible` escape hatch was specifically built to bypass.

### `Field.set` on a `final` field either always throws or always works

**Wrong**

```java
static final class Holder {
    static final int CAP = 100;
    final int stakeMinor = 420;
}

Holder h = new Holder();
Field capField = Holder.class.getDeclaredField("CAP");
capField.setAccessible(true);
capField.set(null, 999); // assumed to work the same way as an instance field

Field stakeField = Holder.class.getDeclaredField("stakeMinor");
stakeField.setAccessible(true);
stakeField.set(h, 999); // assumed to throw the same way CAP does
```

**Right**

```java
// CAP: static final -> IllegalAccessException, always refused.
// stakeMinor: instance final with a constant initializer -> set() succeeds,
// but every direct read of h.stakeMinor was already inlined by javac to the
// literal 420, so no caller ever observes the write.
// Treat each case on its own measured behavior, not as one uniform rule.
```

**Why people believe it:** `final` reads as a single keyword with one meaning, so it is natural to expect one uniform reflective behavior; the actual behavior depends on `static` versus instance, and on whether the initializer is a compile-time constant expression — three independent axes hiding behind one modifier.

### Clearing `Field`'s own `modifiers` field still works to force a static-final write

**Wrong**

```java
Field capField = Holder.class.getDeclaredField("CAP");
capField.setAccessible(true);
Field modifiersField = Field.class.getDeclaredField("modifiers"); // pre-9 recipe
modifiersField.setAccessible(true);
modifiersField.setInt(capField, capField.getModifiers() & ~Modifier.FINAL);
capField.set(null, 999);
```

**Right**

```java
Field capField = Holder.class.getDeclaredField("CAP");
capField.setAccessible(true);
// On JDK 21 there is no bypass: static final fields are refused outright,
// and Field.class.getDeclaredField("modifiers") itself throws
// NoSuchFieldException. If a static final value genuinely needs to vary,
// it should not be static final — expose it through a method or a
// configuration lookup instead.
```

**Why people believe it:** this exact recipe is the most-repeated answer to "how do I set a static final field" across blog posts and Q&A sites dating back over a decade, and it worked on the JVM versions those posts were written against — the internet's collective answer to this question is stale, not wrong-when-written.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Plain instance `final` field via `Field.set` | Succeeds; both reflective and direct reads observed the new value in measurement |
| Instance `final` field, compile-time constant initializer | `set` succeeds but the read is folded to a literal by `javac` — no observable change |
| `static final` via `Field.set` | `IllegalAccessException`, both primitive and reference types |
| Record component field via `Field.set` | `IllegalAccessException`, message omits `static` |
| `Field.class.getDeclaredField("modifiers")` | `NoSuchFieldException: modifiers` — the classic bypass is gone |
| `VarHandle.set` on the same instance `final` field `Field.set` wrote | `UnsupportedOperationException`, `null` message — stricter than `Field` |
| `--illegal-access=permit` | Rejected; JVM warning names 17.0 as the removal release |
| `setAccessible(true)` on a `java.lang` field, no flags | `InaccessibleObjectException` — module `java.base` does not open `java.lang` |
| Same call with `--add-opens java.base/java.lang=ALL-UNNAMED` | Succeeds |
| `isExported` vs `isOpen` | Independent properties; exported can be `true` while open is `false` |
| Classpath (unnamed module) code | Mutually open by default regardless of any flag — strong encapsulation does not protect it |
| Security Manager on Java 21 | Still exists, still installable |
| JEP 486 (Java 24, corroborated-secondary) | Security Manager permanently disabled — cannot be activated at all |
| JEP 500 (Java 24+, corroborated-secondary) | Begins removing `Unsafe` final-field mutation; carve-out planned for deserialization libraries only |
| Deserializing a plain `Serializable` class | Bypasses the constructor, writes `final` fields directly — measured `Split2[34+300=333]` |
| Deserializing a record | Goes through the canonical constructor — measured `InvalidObjectException` on the same forged split |

## Self-test

**Q1.** On JDK 21, does `Field.set` succeed on a plain, non-static `final` instance field after `setAccessible(true)`?

<details><summary>Answer</summary>

Yes. The measured matrix shows `Field.set` succeeding on a `final String type` field with no compile-time constant initializer, and both the reflective read and the direct field read observed the new value in that measurement. This is the fact most engineers assume is false. The caveat is that observing the change through a direct read is not guaranteed in general — the JIT is entitled to have already treated the field as immutable in a given compiled method.

</details>

**Q2.** Why does setting `final int stakeMinor = 420;` via reflection appear to succeed but never change what the program prints?

<details><summary>Answer</summary>

Because `420` is a compile-time constant expression, the field is a JLS *constant variable*, and `javac` folds its value directly into the bytecode of every method that reads it. `Field.set` genuinely writes the field's memory and throws nothing — but no reader ever consults that memory, because every read site already contains the literal `420` baked in at compile time. The write succeeds; there is simply nothing downstream that looks at the field.

</details>

**Q3.** What is the measured exception, verbatim, for `Field.set` on a `static final int`?

<details><summary>Answer</summary>

`java.lang.IllegalAccessException: Can not set static final int field Ver9$Holder.CAP to java.lang.Integer`. The same exception type, `IllegalAccessException`, is also thrown for a record component's field, so the exception type alone does not tell you which rule was hit — the message text, which does or does not mention `static`, is what distinguishes them.

</details>

**Q4.** Does the classic "clear the `modifiers` field to force a static-final write" trick still work on JDK 21?

<details><summary>Answer</summary>

No. `Field.class.getDeclaredField("modifiers")` throws `NoSuchFieldException: modifiers` — the `java.lang.reflect.Field` class no longer exposes a field reachable by that name, so there is nothing to clear the `FINAL` bit on. This is the most-repeated stale answer online for "how do I set a static final field," and it stopped working well before Java 21.

</details>

**Q5.** A `VarHandle` and a `Field` both target the same non-static, non-constant `final` field. `Field.set` succeeded on it. What happens with `VarHandle.set`?

<details><summary>Answer</summary>

It throws `UnsupportedOperationException` with a `null` message, even though `findVarHandle` located the handle without error and `vh.get` read the current value successfully. The two APIs disagree on the identical field: the newer `VarHandle` API refuses the write that the older `Field` API permits. The platform is steering new code toward the stricter API rather than retroactively breaking the older one.

</details>

**Q6.** What is the practical difference between `exports` and `opens` in the module system, and does either protect classpath code?

<details><summary>Answer</summary>

`exports` makes a package's public API usable at compile time by other modules; `opens` additionally permits deep reflection into that package's non-public members at runtime. They are independent: measurement showed `java.lang` was exported (`true`) but not open to the unnamed module (`false`) without `--add-opens`, and open (`true`) with it. Neither property protects classpath code from other classpath code — code in the unnamed module (the typical Spring Boot classpath) is mutually, unconditionally reflectively open regardless of any flag.

</details>

**Q7.** Is the Security Manager available on Java 21? What is its status in Java 24?

<details><summary>Answer</summary>

On Java 21, it still exists and can still be installed and used — nothing about it has changed on this target version. In Java 24, per JEP 486, it is permanently disabled: it cannot be activated at startup or at runtime, and the Platform specification was revised so it cannot be enabled at all. The JEP frames this as a step toward removal, so the precise word is disabled, not yet removed — the classes still exist, they simply cannot be turned on.

</details>

**Q8.** Why did the Security Manager fail as a security mechanism, beyond simply being old?

<details><summary>Answer</summary>

It was designed for a threat model — untrusted applets sharing a JVM with trusted code — that stopped existing once browsers dropped applet support. Server-side adoption was rare because authoring a correct policy file for a realistic modern dependency graph is impractical. Every `checkPermission` call site was a permanent cost paid by every JVM. And an in-process boundary enforced by cooperating code never reliably contained an attacker who already had code execution inside the sandboxed region.

</details>

**Q9.** What is JEP 500 actually removing, and what is it explicitly preserving?

<details><summary>Answer</summary>

It begins removing the `sun.misc.Unsafe` methods that let arbitrary code mutate `final` fields, on the stated rationale that the mere existence of such APIs makes every `final` field's value untrustworthy for both safety and JIT-optimization purposes. It explicitly plans a limited-purpose replacement API for serialization and mapping libraries that must mutate `final` fields during deserialization, since that path cannot go through the normal constructor. No removal has been announced for ordinary reflective `Field.set` writes to instance `final` fields.

</details>

**Q10.** Why is a class name taken from client input treated as a code-execution primitive rather than just a string, and what is the specific danger of the one-argument `Class.forName`?

<details><summary>Answer</summary>

Because reflection resolves a name into a loadable class and, from there, into invocable members — the same general "do anything named by data" capability most deserialization attack chains are built to reach. The one-argument `Class.forName(name)` runs the target class's static initializer as part of resolution, so simply resolving an attacker-supplied name can execute code before any validation of the resulting `Class` object has occurred. The mitigation is an allow-list checked before resolution, and using the three-argument `Class.forName(name, false, loader)` form so initialization does not run automatically.

</details>

## Open questions

1. Whether a reflectively written `final` instance field is reliably observed by an already-JIT-compiled hot method that read the field earlier in the same run — settled by JVM bytecode/inlining behavior, owned by guide 06 (JVM internals), not measured in this session.
2. The exact JEP number and wording for the Security Manager's initial deprecation-for-removal (commonly cited as JEP 411 in Java 17) — the JEP page returned HTTP 403 to direct fetch this session; settled by reading the JEP text directly or the openjdk.org mailing-list archive.
3. The precise JDK 24 release notes' final wording distinguishing "disabled" from "removed" for the Security Manager under JEP 486 — the JEP page itself was not readable this session; settled the same way.

---

**Leaves covered:** 2.12.10–2.12.11 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 520
