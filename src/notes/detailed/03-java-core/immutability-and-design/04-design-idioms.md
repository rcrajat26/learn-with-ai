# 03 Java Core — Design idioms — static factories, builders, singletons, and uninstantiable classes — INTERMEDIATE (§2.14, 2.14.1–2.14.5)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Java is pass-by-value](03-pass-by-value.md) · Next: [Composition, the small rules, and the Effective Java cross-index](04a-composition-and-cross-index.md)

---

Five leaves, and four of the five are about the same thing seen from four sides: **the Java constructor is an unusually restricted method, and most of the design idioms in this section exist to route around one of its restrictions.** A constructor cannot be named, cannot decline to return a fresh object, cannot return a subtype, and cannot be overloaded on meaning when two meanings share a parameter shape — the static factory (§1) lifts all four. It cannot express seventeen optional components without seventeen overloads — the builder (§2) lifts that. It cannot be *prevented* from running, which is what the singleton (§3, §4) and the uninstantiable utility class (§5) both need. [02-immutability.md](02-immutability.md) already argued static factories from the *immutability* angle, as the alternative to sealing a class with `final`; this file owes the general idiom. [02c-unsafe-immutables-builders-and-interning.md](02c-unsafe-immutables-builders-and-interning.md) already ships the full seven-component `PaymentRun.Builder`; this file owes the anti-pattern that builder replaces and the decision shape, not a second copy of the code.

Everything measured below ran on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245), macOS aarch64**, compiled and run in a scratch directory under `/tmp/`. Compiler diagnostics are `javac` output verbatim; bytecode is `javap -c -p`.

---

## 1. Static factory methods over constructors (2.14.1) `[BUILD]`

The mental model: a constructor is the only method in Java that cannot be named, cannot be overloaded on *meaning*, cannot decline to return a new object, and cannot return a subtype. Four restrictions, and every single benefit of the static factory idiom is one of those four restrictions lifted — there is no fifth benefit, and a candidate who knows the four has the complete answer.

### Why it exists

`new Money(420, Currency.GBP)` is ambiguous at the call site and cannot be disambiguated by adding an overload. Is `420` four pounds twenty in minor units, or four hundred and twenty pounds? Both readings are needed — the card PSP reports amounts in minor units, the operator console captures major units — and both have the parameter shape `(long, Currency)`. The compiler rejects the attempt outright:

```java
final class MoneyClash {
    private final BigDecimal amount;
    MoneyClash(long minorUnits, Ccy2 currency) { this.amount = BigDecimal.valueOf(minorUnits, 2); }
    MoneyClash(long majorUnits, Ccy2 currency) { this.amount = BigDecimal.valueOf(majorUnits); }
}
```

Measured, `javac` on JDK 21.0.7:

```
Clash.java:6: error: constructor MoneyClash(long,Ccy2) is already defined in class MoneyClash
    MoneyClash(long majorUnits, Ccy2 currency) { this.amount = BigDecimal.valueOf(majorUnits); }
    ^
1 error
```

Two factories named `ofMinorUnits` and `ofMajorUnits` have the same problem and no error, because the *name* carries the distinction the parameter list cannot. That is restriction one lifted, and it is the benefit that pays every day.

### When to reach for it, and when not

Reach for a static factory whenever any one of the four restrictions bites: two constructions differ in meaning but not in shape; the type has instances worth sharing; the declared return type should be an interface or a sealed supertype rather than one concrete class. Do not reach for it as a blanket rule on every class — a two-field `RestrictionKey(RestrictionType type, RestrictionSource source)` with exactly one meaningful construction gains nothing from `RestrictionKey.of(type, source)` except a redundant indirection, and its canonical record constructor already reads correctly. The line between "earns it" and "ceremony" is exactly the territory leaf 2.14.12 owns; [04a-composition-and-cross-index.md](04a-composition-and-cross-index.md) settles it.

The four restrictions, each lifted, each with its QuizStakes case:

| Constructor restriction | What the static factory does instead | QuizStakes case |
|---|---|---|
| Cannot be named | The method name states the meaning of the arguments | `Money.ofMinorUnits(420, GBP)` versus `Money.ofMajorUnits(new BigDecimal("4.20"), GBP)` |
| Must return a fresh object (`new` is specified to allocate) | May return a shared, cached, or pre-existing instance | `Money.zero(GBP)` returns one shared instance per currency; `Integer.valueOf` and `Boolean.valueOf` do the same in the JDK |
| Is bound to exactly one concrete class | May declare an interface or supertype as its return type, and pick the implementation | `List.of()` returns two different classes depending on size; `Verdict.of(outcome, reason, decidedAt, decidedBy)` picks among the sealed `DocumentVerdict`/`ScreeningVerdict`/`ReviewVerdict`/`WealthVerdict` leaves |
| Cannot have two overloads with the same erased parameter shape | Two factories may share a parameter shape because their names differ | `Money.ofMinorUnits(long, Currency)` and `Money.ofMajorUnits(long, Currency)` coexist; the two constructors above do not compile |

**Caching, stated precisely.** `new` is specified to produce a fresh object, so a constructor is *structurally forbidden* from returning a shared one — there is no expression a constructor body can write that makes `new Money(amount, currency)` yield an object that already existed. A factory has no such constraint. The JDK's own instance controls: `Integer.valueOf(i)` returns `IntegerCache.cache[i + 128]` for `i` in the cached range, which is why `Integer.valueOf(127) == Integer.valueOf(127)` printed `true` and `Integer.valueOf(128) == Integer.valueOf(128)` printed `false` on JDK 21.0.7 — the boundary is set by `AutoBoxCacheMax`, `128` by default (`intx AutoBoxCacheMax = 128 {C2 product} {default}`), against a JLS-mandated floor of −128..127. [../wrappers-and-boxing/01-basics.md](../wrappers-and-boxing/01-basics.md) owns the wrapper caches in full; [02c-unsafe-immutables-builders-and-interning.md](02c-unsafe-immutables-builders-and-interning.md) owns the question of whether interning *your own* type ever pays.

**Subtype return, and the strong form of the claim.** `List.of()` on JDK 21.0.7, measured:

```
empty: java.util.ImmutableCollections$ListN
one:   java.util.ImmutableCollections$List12
two:   java.util.ImmutableCollections$List12
three: java.util.ImmutableCollections$ListN
emptySame: true
```

Two implementation classes behind one declared return type of `List<E>`, with the empty case a shared singleton `ListN` (`List.of() == List.of()` printed `true`). No caller names `List12` or `ListN`; both are package-private, and the JDK is free to add a `List3` tomorrow without breaking a line of existing code. The strong form worth saying out loud in an interview: **a static factory is what makes an interface-typed API possible at all.** A constructor names a concrete class in its own invocation syntax and is therefore inseparable from it — `new` and an interface cannot appear together. Every interface-returning entry point in the JDK is a static method, without exception, because there is no other option.

### How it works

Nothing exotic: a `private` constructor plus `public static` methods on the same class, which have access to that constructor because private access is class-scoped, not instance-scoped. The only real mechanism worth naming is the **naming convention**, because once you own the names you own the discipline — invent your own vocabulary and every reader has to learn it per class. Follow the JDK's:

| Name | Contract | JDK example |
|---|---|---|
| `of` | Concise aggregation of the arguments into an instance | `List.of`, `EnumSet.of`, `Money.ofMinorUnits` |
| `from` | Type conversion from a single argument of a different type | `Instant.from`, `Date.from` |
| `valueOf` | A more verbose conversion, historically the boxing entry point | `Integer.valueOf`, `BigDecimal.valueOf` |
| `getInstance` | Returns an instance described by the arguments; may or may not be cached | `Calendar.getInstance`, `Currency.getInstance` |
| `newInstance` | Like `getInstance`, but guarantees each call returns a distinct instance | `Array.newInstance` |
| `copyOf` | An independent copy of the argument | `List.copyOf`, `Arrays.copyOf` |

`getInstance` versus `newInstance` is the pair that carries real information — `getInstance` reserves the right to cache, `newInstance` promises not to. Choosing between them is a public contract decision, not a style one.

### Diagram

No diagram is assigned here, and the content resists one: the payload of this concept is a four-row restriction-to-benefit mapping and a six-row naming table, both of which are already the tightest possible form. A picture of "call site arrow to factory arrow to private constructor" would restate the code with boxes around it. [../classes-and-initialization/01c-class-anatomy-and-constructors.md](../classes-and-initialization/01c-class-anatomy-and-constructors.md) owns the picture of what a constructor actually is.

### A concrete example

`[BUILD]` — the complete `Money`, compiling on JDK 21.0.7: private constructor, the full factory set covering all four restrictions, a load-bearing validity check on each entry point, and a cached zero per currency.

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.EnumMap;
import java.util.Map;

enum Ccy { GBP, EUR, USD }

final class Money implements Comparable<Money> {
    private static final Map<Ccy, Money> ZEROS = new EnumMap<>(Ccy.class);
    static {
        for (Ccy c : Ccy.values()) ZEROS.put(c, new Money(BigDecimal.ZERO.setScale(2), c));
    }

    private final BigDecimal amount;
    private final Ccy currency;

    private Money(BigDecimal amount, Ccy currency) {
        this.amount = amount;
        this.currency = currency;
    }

    static Money zero(Ccy currency) { return ZEROS.get(currency); }

    static Money ofMinorUnits(long minorUnits, Ccy currency) {
        if (minorUnits < 0) throw new IllegalArgumentException("negative: " + minorUnits);
        return new Money(BigDecimal.valueOf(minorUnits, 2), currency);
    }

    static Money ofMajorUnits(BigDecimal major, Ccy currency) {
        if (major.scale() > 2) throw new IllegalArgumentException("scale " + major.scale());
        return new Money(major.setScale(2, RoundingMode.UNNECESSARY), currency);
    }

    BigDecimal amount() { return amount; }
    Ccy currency() { return currency; }

    @Override public int compareTo(Money other) { return amount.compareTo(other.amount); }
    @Override public String toString() { return amount.toPlainString() + " " + currency; }
}
```

Measured:

```
ofMinorUnits(420, GBP)                    = 4.20 GBP
ofMajorUnits(new BigDecimal("4.20"), GBP) = 4.20 GBP
zero(GBP)                                 = 0.00 GBP
zero(GBP) == zero(GBP)                    : true
ofMinorUnits(-1, GBP) -> java.lang.IllegalArgumentException: negative: -1
ofMajorUnits(4.2049, GBP) -> java.lang.IllegalArgumentException: scale 4
```

Both factories produce the same `4.20 GBP` from different inputs, which is the whole point — the ambiguity a constructor could not resolve is resolved by the names. `zero(GBP) == zero(GBP)` is reference-identical because the factory returned the cached instance a constructor could not have returned. The `RoundingMode.UNNECESSARY` on `ofMajorUnits` is not decoration: it makes an operator typing `4.2049` into a major-units field a loud `IllegalArgumentException` rather than a silent 4.20, which at 95k card deposits/day is the difference between a rounding bug and a rejected input. [../numbers-and-money/02-numbers-and-money.md](../numbers-and-money/02-numbers-and-money.md) owns `BigDecimal` scale and `RoundingMode` in full.

### The gotcha

Three honest costs, none of them fatal, all of them real.

**A private constructor is invisible to anything that reflects over constructors.** Frameworks that instantiate your type by finding a constructor will not find one they can use. JPA requires an accessible no-argument constructor on an `@Entity` (guide 08 owns the rule and the workarounds); Spring's constructor injection needs a constructor it can see (guide 07). Worse, deserialization does not call a constructor *at all* — `readObject` reconstructs the object field by field, bypassing every factory and every validity check the factories enforce, which means `ofMajorUnits`'s scale check offers exactly zero protection against a hostile or stale byte stream. [../serialization/02-serialization.md](../serialization/02-serialization.md) owns that bypass; the mitigation is a `readObject` that re-runs the same validation, or `readResolve` routing through the factory.

**The factories are not discoverable where readers look for them.** Javadoc lists constructors in their own summary block; static factories land in the method summary among every other method, alphabetically. A reader who has never seen the class does not know the entry points exist. The mitigation is a class-level Javadoc paragraph naming them, and the naming convention above so `of`/`from`/`valueOf` are recognisable on sight.

**Pitfall:** believing a private constructor makes the invariants unbreakable. **Wrong belief:** "nothing can construct a `Money` except my factories, so every `Money` in the system has scale 2." **Symptom:** a `Money` with scale 4 appears in the ledger after a deserialization round-trip or a reflective framework call, and the arithmetic that assumed scale 2 produces a bonus split that does not sum to the stake. **Fix:** treat the factory as the *ergonomic* entry point and enforce the invariant in the private constructor itself, so every path — factory, `readObject` with a validating hook, reflective instantiation — hits the same check.

**Interview:** "Why would you use a static factory instead of a constructor?" The four-part answer is naming, instance control, subtype return, and no signature collision. Most candidates give the first and stop. The one that separates a strong answer: *a constructor cannot return an interface, so every interface-typed factory in the JDK has to be a static method* — that reframes the idiom from a style preference into a structural necessity.

> **Definition.** A static factory method is a `public static` method that returns an instance of its own class or a subtype of a type it knows about, replacing a `public` constructor; it lifts exactly four constructor restrictions — it can be named, it can return a cached or pre-existing instance, it can declare a supertype or interface as its return type, and it can share a parameter shape with a sibling factory — at the cost of invisibility to constructor-reflecting frameworks and to the Javadoc constructor summary.

---

## 2. The builder, and the telescoping constructor it replaces (2.14.2) `[BUILD]`

The mental model: the builder is not a pattern you reach for because a class is big. It is the answer to a specific question — *how does a caller supply seven components, three of them optional, and get an immutable object at the end* — and it only makes sense once you have watched the two obvious answers fail. Learn the failures first; the builder falls out of them.

### Why it exists

`PaymentRun` carries seven components: `runRef`, `itemIds`, `createdAt`, `approvedAt`, `approvedBy`, `totalAmount`, `bankFileRef`. The first answer is the **telescoping constructor** — one overload per prefix of the parameter list, each delegating to the next:

```java
public final class PaymentRunTelescoping {
    private final String runRef;
    private final List<String> itemIds;
    private final Instant createdAt;
    private final Instant approvedAt;
    private final String approvedBy;
    private final Money totalAmount;
    private final String bankFileRef;

    public PaymentRunTelescoping(String runRef) { this(runRef, List.of()); }

    public PaymentRunTelescoping(String runRef, List<String> itemIds) {
        this(runRef, itemIds, Instant.EPOCH);
    }

    public PaymentRunTelescoping(String runRef, List<String> itemIds, Instant createdAt) {
        this(runRef, itemIds, createdAt, null);
    }

    public PaymentRunTelescoping(String runRef, List<String> itemIds, Instant createdAt,
                                 Instant approvedAt) {
        this(runRef, itemIds, createdAt, approvedAt, null);
    }

    public PaymentRunTelescoping(String runRef, List<String> itemIds, Instant createdAt,
                                 Instant approvedAt, String approvedBy) {
        this(runRef, itemIds, createdAt, approvedAt, approvedBy, Money.zero(Ccy.GBP));
    }

    public PaymentRunTelescoping(String runRef, List<String> itemIds, Instant createdAt,
                                 Instant approvedAt, String approvedBy, Money totalAmount) {
        this(runRef, itemIds, createdAt, approvedAt, approvedBy, totalAmount, null);
    }

    public PaymentRunTelescoping(String runRef, List<String> itemIds, Instant createdAt,
                                 Instant approvedAt, String approvedBy, Money totalAmount,
                                 String bankFileRef) {
        this.runRef = Objects.requireNonNull(runRef, "runRef must not be null");
        this.itemIds = List.copyOf(itemIds);
        this.createdAt = createdAt;
        this.approvedAt = approvedAt;
        this.approvedBy = approvedBy;
        this.totalAmount = totalAmount;
        this.bankFileRef = bankFileRef;
    }
}
```

"Unreadable" is the usual complaint and it is the weakest one, because it is a matter of taste. The two real failures are not aesthetic.

**Failure (a): adjacent same-typed parameters transpose silently.** `createdAt` and `approvedAt` are both `Instant`. Swapping them at the call site is not a compile error, not a warning, not detectable by any tooling short of a unit test that specifically checks the ordering. Measured with `javac -Xlint:all` on JDK 21.0.7 — zero diagnostics, and then:

```
right: PaymentRun[runRef=PR-2026-08-29, itemIds=[W-1, W-2], createdAt=2026-08-29T09:00:00Z, approvedAt=2026-08-29T17:30:00Z]
wrong: PaymentRun[runRef=PR-2026-08-29, itemIds=[W-1, W-2], createdAt=2026-08-29T17:30:00Z, approvedAt=2026-08-29T09:00:00Z]
wrong compiled with zero warnings; approvedAt is before createdAt: true
```

A `PaymentRun` approved eight and a half hours before it was created, constructed without complaint. At 7k bank withdrawals/day batched into runs with operator sign-off, an inverted approval timestamp is an audit-trail defect that a regulator will find and the compiler never will. `approvedBy` and `bankFileRef` are both `String` and transpose the same way, with the operator identity landing in the bank file reference field.

**Pitfall:** believing a long parameter list is only a readability problem. **Wrong belief:** "it is ugly but it is correct — the types check." **Symptom:** the types *do* check, because two `Instant` parameters are the same type; a run is persisted with `approvedAt` before `createdAt`, or with an operator's name in `bankFileRef`, and nothing fails until reconciliation or an audit weeks later. **Fix:** make the component *name* appear at the call site — that is a builder's `.approvedAt(x)` or, for a smaller type, a set of named static factories per §1. Types cannot distinguish two `Instant`s; names can.

**Failure (b): every optional component multiplies the overload count.** With three genuinely optional components (`approvedAt`, `approvedBy`, `bankFileRef`), expressing every combination a caller might legitimately want takes up to 2³ = 8 constructors, and the telescoping form gives only the 4 *prefix* combinations — a caller wanting `bankFileRef` but not `approvedBy` has no overload at all and must pass `null` for `approvedBy`. That is the second half of the failure: the constructor cannot distinguish "the caller deliberately supplied no approver" from "the caller has not got round to it", because both arrive as `null`. Generalising, N optional components need up to 2^N overloads, or a sentinel vocabulary every caller has to memorise. [../null-discipline/02-null-discipline.md](../null-discipline/02-null-discipline.md) owns why `null` is the wrong sentinel.

### When to reach for it, and when not

The second answer, and the one most codebases actually reach for — a no-argument constructor plus JavaBeans setters — is worse than either the telescoping constructor or the builder, and it is worth being precise about why, because neither [02c-unsafe-immutables-builders-and-interning.md](02c-unsafe-immutables-builders-and-interning.md) nor [02b-records-jmm-and-builders.md](02b-records-jmm-and-builders.md) covers it. Setters solve readability (the component name is at the call site) and optionality (skip the setter you do not need) at one specific price: **the object is legally observable in a half-built, invariant-violating state, and there is no point at which it is guaranteed complete.** A `PaymentRun` with `itemIds` set and `totalAmount` still zero is a valid instance of the type as far as the compiler is concerned; any code that receives the reference between two setter calls sees a run whose total does not match its items. And because there is no `build()`, no line of code can be pointed at as "here the object becomes valid" — which also means the fields cannot be `final`, so the immutability argument of [02-immutability.md](02-immutability.md) is abandoned wholesale, and the safe-publication guarantee of [02b-records-jmm-and-builders.md](02b-records-jmm-and-builders.md) §3 goes with it.

Three-way, on the axes that matter:

| | Telescoping constructor | No-arg constructor + setters | Builder |
|---|---|---|---|
| Component name visible at call site | No | Yes | Yes |
| Transposition of two same-typed components | Compiles silently — wrong object | Impossible (each setter is named) | Impossible (each method is named) |
| Optional components | Up to 2^N overloads, or `null` sentinels | Free — skip the setter | Free — skip the method |
| Result immutable, fields `final` | Yes | No | Yes |
| Half-built state observable | No | **Yes, and unavoidable** | No — only the `Builder` is mutable, and it is never published |
| Missing required component detected | At compile time, by the overload chosen | Never | At `build()`, at run time — or at compile time with the factory entry point below |

Reach for the builder when the component count is past roughly four, *or* when two components share a type, *or* when any component is optional. Reach for a plain canonical constructor or a record below that. A builder for a two-field type is pure ceremony — `RestrictionKey.builder().type(STAKE_BLOCKED).source(ADMIN).build()` in place of `new RestrictionKey(STAKE_BLOCKED, ADMIN)` is nine extra lines of class for nothing — and exactly where the line falls is leaf 2.14.12's business: [04a-composition-and-cross-index.md](04a-composition-and-cross-index.md) settles it.

### How it works

The builder is a mutable companion object that accumulates components, then hands them to the immutable target's private constructor in one call. The mechanism is unremarkable; the two design choices that matter are (1) the setters return `this` so calls chain, and (2) `build()` is the single place validation runs, so an invalid combination fails once, loudly, at a named line. [02c-unsafe-immutables-builders-and-interning.md](02c-unsafe-immutables-builders-and-interning.md) ships the full seven-component `PaymentRun.Builder`, including the `List.copyOf` defensive copy of `itemIds` and the cross-component check that `approvedAt` is not before `createdAt` — read the code there rather than a second copy here.

### Diagram

No diagram is assigned here. The load-bearing content is a three-way comparison across six axes and one measured transposition, both of which a table renders more precisely than a picture — a box-and-arrow of "builder to build() to object" says nothing the signature does not.

### A concrete example

What that file does not ship, and what a strong candidate actually writes: the **static-factory-plus-builder entry point**, which composes §1 and §2. Instead of `new PaymentRun.Builder(runRef)`, a static factory on the target returns a builder that already holds every *required* component, so `build()` cannot fail on a missing required field — the requirement is enforced by the entry point's own signature at compile time rather than by a run-time check inside `build()`.

```java
public final class PaymentRun {
    private final String runRef;
    private final List<String> itemIds;
    private final Instant createdAt;
    private final Instant approvedAt;

    private PaymentRun(Builder builder) {
        this.runRef = builder.runRef;
        this.itemIds = List.copyOf(builder.itemIds);
        this.createdAt = builder.createdAt;
        this.approvedAt = builder.approvedAt;
    }

    public static Builder builder(String runRef, Instant createdAt) {
        return new Builder(Objects.requireNonNull(runRef, "runRef must not be null"),
            Objects.requireNonNull(createdAt, "createdAt must not be null"));
    }

    public String runRef() { return runRef; }
    public List<String> itemIds() { return itemIds; }
    public Instant createdAt() { return createdAt; }
    public Optional<Instant> approvedAt() { return Optional.ofNullable(approvedAt); }

    public static final class Builder {
        private final String runRef;
        private final Instant createdAt;
        private List<String> itemIds = List.of();
        private Instant approvedAt;

        private Builder(String runRef, Instant createdAt) {
            this.runRef = runRef;
            this.createdAt = createdAt;
        }

        public Builder itemIds(List<String> itemIds) {
            this.itemIds = Objects.requireNonNull(itemIds, "itemIds must not be null");
            return this;
        }

        public Builder approvedAt(Instant approvedAt) {
            this.approvedAt = approvedAt;
            return this;
        }

        public PaymentRun build() {
            if (approvedAt != null && approvedAt.isBefore(createdAt)) throw new IllegalStateException(
                "approvedAt " + approvedAt + " precedes createdAt " + createdAt);
            return new PaymentRun(this);
        }
    }
}
```

Two properties worth naming. The required components are `final` fields on the `Builder`, assigned only by the private `Builder` constructor that only `PaymentRun.builder` can call — so there is no reachable code path that produces a `Builder` missing `runRef` or `createdAt`, and `build()` needs no null check for either. And `build()`'s only remaining job is the *cross-component* invariant, `approvedAt` not preceding `createdAt` — which is precisely the check the telescoping constructor's transposition defeated, now expressible because both values are present in one place at one time.

### The gotcha

**Insight:** the builder's real product is not readability, it is that **the mutable phase and the published phase are two different objects.** A setter-based type has one object that is mutable forever; a builder has a mutable `Builder` that is never handed to anyone and an immutable `PaymentRun` that is handed to everyone. The half-built state does not become unobservable by convention — it becomes unobservable because it lives in an object that never escapes the calling expression.

**Pitfall:** reusing a `Builder` after `build()`. The `Builder` is still mutable and still holds every component, so `var b = PaymentRun.builder(ref, now); var first = b.build(); b.approvedAt(later); var second = b.build();` produces two `PaymentRun` objects — which is fine — but a builder captured in a field and shared across the 7k/day withdrawal batching threads produces interleaved, arbitrary combinations of components with no synchronisation anywhere. **Fix:** treat a `Builder` as a single-use, stack-local object; never store one in a field or pass one to another thread.

> **Definition.** The builder pattern replaces a telescoping constructor with a mutable companion object whose named methods accumulate components and whose single `build()` call validates them and constructs the immutable target — it is the answer to same-typed parameters transposing silently and to N optional components needing 2^N overloads, and unlike a no-argument constructor plus setters it never leaves the target observable in a half-built state, because the mutable phase lives in a separate object that is never published.

---

## 3. Four singletons, and which to use (2.14.3) `[PROVE]` `[X-REF 05]`

The mental model: "exactly one instance" is not one requirement, it is a family of four, and the four differ on whether the instance is created eagerly or lazily, on what stops two threads from creating two, and on what stops serialization or reflection from manufacturing a second one behind your back. Pick by which of those you actually need, not by which one you saw first.

### Why it exists

`BonusRateTable` loads the currency-by-currency bonus percentages and the cap of 100 from configuration. It is read on every one of the 3.1k bonus grants/day, it is expensive to build once, and two copies in memory with different contents would grant different bonuses to two clients depending on which instance their thread happened to reach. Exactly one instance, visible correctly to every thread, is the requirement. Everything below is a different way of getting it.

### When to reach for each, and when not

| | Eager static | Holder class | DCL with `volatile` | Enum |
|---|---|---|---|---|
| Lazy? | No — built at outer class init | **Yes** | Yes | No |
| Thread-safety mechanism | JVM class-init lock (JVMS 5.5) | JVM class-init lock on the holder | `volatile` + `synchronized` block | JVM class-init lock |
| Serialization behaviour | Deserializes to a **second** instance unless `readResolve` is written | Same — needs `readResolve` | Same — needs `readResolve` | **Identity preserved for free** |
| Reflection-proof? | No — `setAccessible(true)` reaches the private constructor | No | No | **Yes** — `Constructor.newInstance` refuses |
| Supports a parameterised or resettable instance? | No | No | **Yes** | No |
| Lines of code | 1 | 3 | a dozen or so | 1 |

**Eager static.** `private static final BonusRateTable INSTANCE = new BonusRateTable();` — one line, and thread-safe with no `synchronized` and no `volatile`, because static initialisers run inside the class's `<clinit>`, which the JVM executes exactly once under a per-class initialisation lock (JVMS 5.5). Every thread that reads `INSTANCE` has either waited for `<clinit>` to complete or arrived after it did; either way there is a happens-before edge and no thread can observe a partly-built table. Cost: the table is built the first time *anything* touches the class, including a call to an unrelated static method.

**Double-checked locking with `volatile`.** A dozen or so lines, correct, and the only one of the four that supports an instance whose construction takes *parameters* discovered at run time, or one that can be reset (a bonus rate table reloaded when configuration changes). It is also the one everybody gets wrong, which is §4's entire subject.

**The enum singleton.** `enum BonusRateTable { INSTANCE; }` — one line, and it wins on two axes nothing else does. Serialization: measured on JDK 21.0.7, serialising `BonusRateTableEnum.INSTANCE` and reading it back printed `deserialized == INSTANCE: true` in 79 bytes, with no `readResolve` written — enum instances are serialised by name and resolved through `Enum.valueOf`, so identity survives by construction. Reflection: measured, `Constructor.newInstance("X", 0)` on the enum's declared constructor after `setAccessible(true)` printed

```
enum-no-constants -> java.lang.IllegalArgumentException: Cannot reflectively create enum objects
```

`Constructor.newInstance` checks the `ENUM` class modifier and refuses unconditionally — there is no flag, no module opening and no security policy that permits it. This is why *Effective Java*'s item titled *Enforce the singleton property with a private constructor or an enum type* recommends the enum form as the default. [../enums/01c-production-patterns-and-guarantees.md](../enums/01c-production-patterns-and-guarantees.md) owns the enum singleton's guarantees in full.

The decision, as a decision rather than a preference: **enum unless you need laziness; the holder class if you need laziness; double-checked locking only if you need something neither gives you** — a parameterised instance, or a resettable one.

### How it works

`[PROVE]` — **the holder class is both lazy and lock-free, and both halves need arguing, not asserting.**

*Why it is lazy.* `Holder` is a separate class from `BonusRateTable`. JVMS 5.5 initialises a class on the first *active use* of that class — a `getstatic` of one of its non-constant fields, among the other triggers. `BonusRateTable.schemaVersion()` is an active use of `BonusRateTable`, not of `Holder`; only the `getstatic Holder.INSTANCE` inside `getInstance()` is an active use of `Holder`. So the expensive construction is deferred past outer-class initialisation. Measured on JDK 21.0.7:

```
calling BonusRateTable.schemaVersion() -- outer use, no instance
  [class init] BonusRateTable
  [class init] BonusRateTable outer body done
  -> bonus-rates-2026-08
calling BonusRateTable.getInstance() -- first time
  [class init] BonusRateTable$Holder
calling BonusRateTable.getInstance() -- second time
  -> same instance: true
```

`BonusRateTable`'s own `<clinit>` ran at the `schemaVersion()` call. `BonusRateTable$Holder`'s `<clinit>` did **not** — it ran only at the first `getInstance()`, and did not run again at the second. That is laziness demonstrated on the page rather than claimed.

*Why it needs no `volatile` and no `synchronized`.* The initialisation of `Holder` is performed by the JVM under `Holder`'s own per-class initialisation lock. JVMS 5.5's procedure has every thread that finds the class in the "being initialised by another thread" state block on that lock until initialisation completes, and the JMM gives the completion of `<clinit>` a happens-before edge to every subsequent read of the class's static fields. So the `static final INSTANCE = new BonusRateTable()` store, and every field store inside that constructor, are ordered before any thread's read of `Holder.INSTANCE` — the exact guarantee `volatile` is added for in §4, supplied here for free by machinery you did not write. There is no fast-path lock to pay for either, because after initialisation completes the JIT compiles `getstatic Holder.INSTANCE` to a plain field read with no barrier at all. [../classes-and-initialization/03a-internals-class-init-locking-and-failure.md](../classes-and-initialization/03a-internals-class-init-locking-and-failure.md) owns the locking protocol and what happens when `<clinit>` throws; [../classes-and-initialization/01d-class-initialization-triggers.md](../classes-and-initialization/01d-class-initialization-triggers.md) owns the trigger list. Guide 05 owns happens-before.

### Diagram

No diagram is assigned here, and the picture that belongs to this concept already exists elsewhere: **D-039** in [../classes-and-initialization/01d-class-initialization-triggers.md](../classes-and-initialization/01d-class-initialization-triggers.md) renders what triggers class initialisation, which is exactly the mechanism behind the holder idiom's laziness. The four-way comparison above is a table because it is six independent properties across four implementations — no picture carries that.

### A concrete example

The holder idiom, complete, exactly as measured above:

```java
final class BonusRateTable {
    private final Map<Ccy, BigDecimal> ratesByCurrency;
    private final BigDecimal capMinorUnits;

    private BonusRateTable() {
        this.ratesByCurrency = Map.of(Ccy.GBP, new BigDecimal("0.10"),
            Ccy.EUR, new BigDecimal("0.10"), Ccy.USD, new BigDecimal("0.10"));
        this.capMinorUnits = new BigDecimal("100.00");
    }

    private static final class Holder {
        static final BonusRateTable INSTANCE = new BonusRateTable();
    }

    static BonusRateTable getInstance() { return Holder.INSTANCE; }

    static String schemaVersion() { return "bonus-rates-2026-08"; }

    BigDecimal grantFor(Money firstDeposit) {
        BigDecimal rate = ratesByCurrency.get(firstDeposit.currency());
        return firstDeposit.amount().multiply(rate)
            .setScale(2, RoundingMode.DOWN)
            .min(capMinorUnits);
    }
}
```

`Holder` is `private static final class` on all three counts deliberately: `private` so no other class can trigger its initialisation and defeat the laziness, `static` so it holds no reference to an enclosing instance, `final` because it exists to hold one field and has no reason to be extended.

### The gotcha

**Insight:** the meta-point is worth more than all four implementations. A singleton is usually a **dependency-injection problem wearing a static field.** `BonusRateTable.getInstance()` hard-codes, at every call site, that there is exactly one table for the whole process — which makes a test that wants a different rate table impossible without static mutation, and makes a future multi-jurisdiction deployment with two rate tables a rewrite of every caller. A container-managed singleton-scoped bean gives the same one-instance-per-process behaviour with the instance *injected* rather than reached for, so a test supplies a different one by constructing the collaborator differently. Guide 07 owns Spring's singleton scope and why it is not this pattern. Leaf 2.14.6 picks the argument up properly in [04a-composition-and-cross-index.md](04a-composition-and-cross-index.md).

**Pitfall:** believing any of the first three forms guarantees one instance. They guarantee one instance *per class loader*, against *ordinary* construction. Two class loaders loading `BonusRateTable` produce two classes, two `<clinit>` runs and two instances; `setAccessible(true)` on the private constructor produces as many more as you like. Only the enum form is proof against reflection, and nothing except a single class loader is proof against the loader case.

> **Definition.** A singleton is a type with exactly one instance per class loader; the four implementations are eager static (one line, not lazy), the holder class (lazy and lock-free, both properties supplied by the JVM's per-class initialisation lock), double-checked locking with `volatile` (the only form supporting a parameterised or resettable instance, and the only one whose correctness you have to reason about yourself), and the enum (one line, serialization-identity-preserving and reflection-proof for free) — choose the enum unless laziness is required, the holder when it is, and double-checked locking only when neither will do.

---

## 4. Double-checked locking without `volatile` is broken (2.14.4) `[TRAP]` `[PROVE]` `[X-REF 05]`

The mental model: the reference and the object are two separate pieces of state, and publishing the reference is a different event from finishing the object. Double-checked locking's fast path reads the reference *without holding the lock* — so unless something explicitly orders "object finished" before "reference published", a reader can win the race to a non-null reference that points at an object whose fields have not been written yet. `volatile` is that something. Without it there is nothing.

### Why it exists

`LimitSet(dailyDeposit, maxStake, monthlyLoss)` is loaded once and consulted on every deposit and every stake — 95k card deposits and 2.8M stake reservations a day. The idiom exists because the naive lazy singleton, `synchronized static LimitSet getInstance()`, acquires a monitor on all 2.8M of those reads to protect one write that happens once. Double-checked locking's promise is to pay the lock only on the first call: check the field, and only if it is null take the lock and check again. The promise is real. The correctness is not free.

### When to reach for it, and when not

Do not reach for it. The holder class of §3 gets lazy, lock-free initialisation with three lines and no reasoning required, and it covers every case where the instance takes no run-time parameters. Reach for double-checked locking only when the instance genuinely cannot be built by a class initialiser — it needs a value discovered at run time, or it must be replaceable — and then use `volatile`, and then write a comment saying why the holder idiom was not enough. It stays on the syllabus because it is asked in interviews constantly, not because it is the right answer to a production problem.

### How it works

`[PROVE]` — the broken version, in full:

```java
final class LimitSetRegistryBroken {
    private static LimitSetRegistryBroken instance;   // no volatile

    private final int dailyDeposit;
    private final int maxStake;

    private LimitSetRegistryBroken() { this.dailyDeposit = 2000; this.maxStake = 250; }

    static LimitSetRegistryBroken getInstance() {
        if (instance == null) {                       // fast path, no lock
            synchronized (LimitSetRegistryBroken.class) {
                if (instance == null) {
                    instance = new LimitSetRegistryBroken();
                }
            }
        }
        return instance;
    }

    int dailyDeposit() { return dailyDeposit; }
    int maxStake() { return maxStake; }
}
```

`instance = new LimitSetRegistryBroken()` is not one action. It is three: allocate storage, run the constructor's field stores, store the reference into the static field. **JLS 17.4 orders two actions only via happens-before, and there is no happens-before edge between thread A's stores inside the `synchronized` block and thread B's read of `instance` on the fast path — because thread B never acquires the monitor.** Absent that edge, nothing forbids either the compiler from sinking the constructor's stores below the publication, or the reader from observing the two stores in the opposite order to the one the writer performed. The schedule below is one legal execution:

| Step | Thread | Action | State visible to B |
|---|---|---|---|
| 1 | A | reads `instance` on the fast path, sees `null` | `instance == null` |
| 2 | A | `monitorenter` on `LimitSetRegistryBroken.class` | `instance == null` |
| 3 | A | reads `instance` again inside the lock, still `null` | `instance == null` |
| 4 | A | allocates the object; header written; `dailyDeposit` and `maxStake` hold their default `0` | `instance == null` |
| 5 | A | **stores the reference into `instance`** — the publication has moved *above* the constructor's field stores, which is legal because no happens-before edge orders a plain store to `instance` against the plain stores to `dailyDeposit` and `maxStake` | `instance != null`, both fields `0` |
| 6 | B | reads `instance` on the fast path, sees non-`null`, **does not enter the lock**, returns it | `instance != null`, both fields `0` |
| 7 | B | calls `maxStake()` on that reference | returns `0` |
| 8 | A | performs the constructor's field stores: `dailyDeposit = 2000`, `maxStake = 250` | — |
| 9 | A | `monitorexit` | — |

Step 5 is the exact reordering the leaf asks for: **the publication of the reference is ordered before the constructor's writes to the object's fields**, either because the JIT emitted them in that order or because thread B's cache observed them in that order. Both are permitted; the JMM makes no promise either way in the absence of the edge.

**The two symptoms, and why they make this undiagnosable.** First, a `NullPointerException` on a field of an object that is definitively non-`null` — if `LimitSet` held a `Money maxStake` reference rather than an `int`, thread B at step 7 would read the field's default `null` and dereference it, producing an NPE inside a method called on a reference the same method just proved non-null. No amount of null-checking at the call site helps, because the reference *is* non-null; the field inside it is not. Second, and worse, **no exception at all** — an `int` field reads as `0`, and a `maxStake` of `0` is a perfectly plausible-looking limit. A stake of 4.20 is rejected against a maximum of 0, or a `dailyDeposit` of `0` blocks every deposit for however long the window lasts. There is no stack trace, no log line, and no repeatability, because the window is a handful of nanoseconds on the very first call after start-up.

*No measurement is offered for this schedule, deliberately.* Reproducing it requires a JIT compilation and a memory-ordering combination that neither aarch64 nor x86-64 will hand you on demand, and a run that fails to reproduce it proves nothing — the argument above is derived from JLS 17.4's happens-before rules, which is the only form of proof that applies to a permission the specification grants rather than a behaviour it mandates.

**The fix, and why it works.** Declare the field `volatile`. Under the JSR-133 memory model a `volatile` write is a release and a `volatile` read is an acquire: every store thread A performed *before* the write to `instance` — which includes every one of the constructor's field stores — is ordered before that write and is visible to any thread that reads `instance` and sees the new value. So step 5 can no longer float above step 8, and a reader that sees a non-null reference is guaranteed to see a fully constructed object.

`[VERSION-TRAP]` **Before Java 5, `volatile` did not carry that guarantee and double-checked locking was genuinely unfixable.** The pre-JSR-133 model ordered `volatile` accesses with respect to each other but not with respect to surrounding non-volatile accesses, so the constructor's plain field stores could still be reordered across the volatile publication. In **Java 5 and later, including 21, `volatile` fixes it** — the release/acquire semantics above are specified. Every "double-checked locking is broken" article written before 2004 describes a language that no longer exists; the modern correct answer is *"it works, with `volatile`, and you still should not reach for it because the holder class is simpler."* Interviewers ask the old form, so know both. Guide 05 owns the memory model.

### Diagram

No diagram is assigned here. The evidence is a nine-step two-thread schedule, which is a worked table by nature — the ordering, the thread and the state visible to the reader are three columns, and a picture of two vertical timelines with arrows would carry strictly less (it cannot show the field values at each step, which is the whole point).

### A concrete example

The correct version, with the local-variable read the idiom is always written with:

```java
final class LimitSetRegistry {
    private static volatile LimitSetRegistry instance;

    private final int dailyDeposit;
    private final int maxStake;

    private LimitSetRegistry() { this.dailyDeposit = 2000; this.maxStake = 250; }

    static LimitSetRegistry getInstance() {
        LimitSetRegistry local = instance;
        if (local == null) {
            synchronized (LimitSetRegistry.class) {
                local = instance;
                if (local == null) {
                    local = new LimitSetRegistry();
                    instance = local;
                }
            }
        }
        return local;
    }

    int dailyDeposit() { return dailyDeposit; }
    int maxStake() { return maxStake; }
}
```

`[BYTECODE]` The `local` variable is not style. A `volatile` read is a real barrier on the fast path, and the naive form reads the field twice — once for the null test, once for the return. Measured, `javap -c -p` on JDK 21.0.7, the fast path of the version above:

```
  static LimitSet getInstance();
    Code:
       0: getstatic     #7                  // Field instance:LLimitSet;
       3: astore_0
       4: aload_0
       5: ifnonnull     49
```

and its tail:

```
      49: aload_0
      50: areturn
```

**One** `getstatic` at offset 0, stored into local slot 0 at offset 3, tested at offset 5, and returned from that same local at offset 49 — so the already-initialised path performs exactly one volatile read, not two. That is the entire reason the idiom is written with the local.

### The gotcha

**Pitfall:** believing `final` fields rescue the non-`volatile` version. `dailyDeposit` and `maxStake` *are* `final` in the broken code above, and JLS 17.5's final-field freeze does guarantee that a thread which sees a reference to a *correctly published* object sees its `final` fields fully initialised. The guarantee does not apply here, because the field doing the publishing — `instance` — is not `final`, and the freeze orders the constructor's writes relative to the *end of the constructor*, not relative to a later racy read of a mutable static field that happens to hold the reference. [02b-records-jmm-and-builders.md](02b-records-jmm-and-builders.md) §3 covers the freeze and what it does buy; [../classes-and-initialization/04-internals-final-and-constant-folding.md](../classes-and-initialization/04-internals-final-and-constant-folding.md) owns `final` semantics. The two guarantees look adjacent and are not interchangeable.

**Interview:** "Is double-checked locking broken?" The answer that lands: it was, before Java 5, because `volatile` did not order surrounding non-volatile accesses and there was no fix within the language. Since Java 5 it is correct *provided* the field is `volatile`, because the volatile write is a release that orders the constructor's stores before the publication — and the reason not to use it is not correctness, it is that the holder class gets the same laziness in three lines with no reasoning required.

> **Definition.** Double-checked locking reads a lazily initialised field without a lock, and only on seeing `null` takes a lock and re-reads it; without `volatile` on that field it is broken, because no happens-before edge orders the constructor's field stores against the store publishing the reference, so a reader on the unlocked fast path can obtain a non-`null` reference to an object whose fields still hold their defaults — producing either a `NullPointerException` on a field of a non-`null` object or, worse, a silent zero. `volatile` fixes it from Java 5 onward by making the publication a release and the fast-path read an acquire; before Java 5 no fix existed.

---

## 5. The utility class with a private constructor that throws (2.14.5)

The mental model: a class holding nothing but static members has no instance state, so an instance of it is a meaningless object — and the only construct in Java that makes a class uninstantiable is a `private` constructor. This is the smallest concept in the file and the honest treatment is short.

### Why it exists

`javac` supplies a public no-argument constructor to any class that declares no constructor at all, so a utility class written the obvious way is instantiable by accident and by IDE autocomplete. `abstract` is the common wrong fix, and it is wrong in a specific, demonstrable way: `abstract` blocks `new LedgerCodes()` but not a subclass, and an anonymous subclass is one expression away. Measured on JDK 21.0.7 — compiles clean, then:

```
instantiated a subclass of an abstract utility class: AbstractProbe$1
CLIENT_CASH_AVAILABLE
```

`new LedgerCodes() { }` produced an instance of a subclass of the "uninstantiable" class, and `abstract` also implies to every reader that the class is *meant* to be extended, which is the opposite of the intent.

### When to reach for it, and when not

Reach for a private constructor on any class whose every member is `static` — a math helper, a constant holder, a factory-methods-only class. Do not reach for a utility class at all where the behaviour belongs on a domain type: `MoneyMath.bonusGrant(deposit)` is a utility because the bonus rule belongs to the promotion rather than to `Money`, but a `MoneyUtils.add(a, b)` alongside a `Money` that could carry `plus` is a method in the wrong place. Four uninstantiable forms exist and they are not equivalent:

| Form | Uninstantiable by `new`? | Uninstantiable reflectively? | Subclassable? | Cost |
|---|---|---|---|---|
| `private` constructor that throws | Yes | No — `setAccessible(true)` reaches it, but the throw defeats it | No — no accessible `super()` | None |
| `final class` + `private` constructor | Yes | Same | No, twice over | None; `final` is redundant but documents intent |
| `enum` with no constants | Yes | **Yes** — `Constructor.newInstance` refuses outright | No | Reads as a misuse of `enum` to anyone who has not seen the trick |
| `interface` with only `static` methods (Java 8+) | Yes — interfaces have no constructor | Yes | **Yes, pointlessly** — `implements` compiles and adds nothing | Cannot be `final`; members are implicitly `public`, so no package-private helpers |

The `enum` with no constants is the strongest form and worth knowing as a trick rather than adopting as a habit: measured, `StatusCodes.values().length = 0`, and the reflective attempt printed `IllegalArgumentException: Cannot reflectively create enum objects`. The `interface` form needs no constructor at all, which is its only advantage, and pays for it by permitting `class Whatever implements MoneyMath { }` — legal, meaningless, and not preventable.

### How it works

Three facts, and the third is the one people miss. **A private constructor makes the class uninstantiable and unsubclassable at once**, because a subclass constructor must invoke a superclass constructor and `private` means no accessible one exists — measured, `javac` on a non-`final` class with a private constructor:

```
SubProbe2.java:4: error: StatusCodesUtil2() has private access in StatusCodesUtil2
class Attempt2 extends StatusCodesUtil2 { }
^
1 error
```

One modifier, two properties; [../classes-and-initialization/01c-class-anatomy-and-constructors.md](../classes-and-initialization/01c-class-anatomy-and-constructors.md) owns the implicit `super()` rule behind it. **Reflection reaches the private constructor anyway** — `setAccessible(true)` makes it invocable unless a module declaration or a security policy forbids it, so the access modifier alone is a compile-time convention rather than an enforced rule, and [../reflection/02-reflection.md](../reflection/02-reflection.md) owns those mechanics. **And the `throw` inside the constructor is not decoration, though its real job is not reflection**: it closes the hole `private` structurally cannot, which is the class's **own** members and its nested classes — `MoneyMath` calling `new MoneyMath()` from inside one of its own static methods compiles without complaint, and so does a nested class doing it, because private access in Java is class-scoped and includes the nesting boundary. The `throw` turns that into a run-time failure a test will catch, and defeats the reflective route as a bonus.

### Diagram

No diagram is assigned here, and the concept does not want one: the payload is a four-row form comparison and three `javac`/run outputs, with no state, ordering or timeline to draw.

### A concrete example

```java
final class MoneyMath {
    private MoneyMath() { throw new AssertionError("MoneyMath is not instantiable"); }

    static BigDecimal bonusGrant(BigDecimal firstDeposit) {
        BigDecimal tenPercent = firstDeposit.multiply(new BigDecimal("0.10"))
            .setScale(2, RoundingMode.DOWN);
        return tenPercent.min(new BigDecimal("100.00"));
    }
}
```

Measured on JDK 21.0.7:

```
bonusGrant(420.00) = 42.00
bonusGrant(4200.00) = 100.00
ctor modifiers: private
reflection -> java.lang.reflect.InvocationTargetException
  cause -> java.lang.AssertionError: MoneyMath is not instantiable
```

`bonusGrant(420.00)` gives `42.00`, the domain's average bonus grant; `bonusGrant(4200.00)` gives `100.00`, the cap. The reflective call did reach the constructor — `setAccessible(true)` worked — and the `AssertionError` arrived wrapped in `InvocationTargetException`, which is `Constructor.newInstance`'s contract for anything the constructor throws. **The `AssertionError` is what enforces the rule; the `private` modifier only documents it.** Java's own `java.lang.Math` is exactly this form — `private Math() {}` on a `final` class of nothing but static members — which is the citation that settles the argument in a code review; `Math` omits the throw, defensible for a JDK class whose members are audited, while *Effective Java*'s item titled *Enforce noninstantiability with a private constructor* argues for including it.

### The gotcha

**Pitfall:** a private constructor that throws breaks 100% line coverage, because no test can execute its body through any legitimate path. The reflex fix — a test that reflectively invokes it and asserts the `AssertionError` — is a test asserting that the language works, which is the wrong kind of test. **Fix:** exclude the constructor from the coverage requirement, or accept the one uncovered line, rather than writing a test whose only purpose is to satisfy a tool.

> **Definition.** A utility class holds only `static` members and is made uninstantiable by a single `private` constructor, which simultaneously makes it unsubclassable because no subclass has an accessible `super()` to invoke — `abstract` does not achieve this, since an anonymous subclass is instantiable — and the `throw new AssertionError` in that constructor's body closes the remaining hole, which is the class's own members and nested classes calling `new` on it from inside where `private` is no barrier, while also defeating the reflective `setAccessible(true)` route the access modifier alone cannot.

---

## Pitfalls

### A long constructor parameter list is only a readability problem

**Wrong**

```java
Instant createdAt = Instant.parse("2026-08-29T09:00:00Z");
Instant approvedAt = Instant.parse("2026-08-29T17:30:00Z");
var wrong = new PaymentRun("PR-2026-08-29", List.of("W-1", "W-2"), approvedAt, createdAt);
```

Measured with `javac -Xlint:all` on JDK 21.0.7 — no diagnostics — then:

```
wrong: PaymentRun[runRef=PR-2026-08-29, itemIds=[W-1, W-2], createdAt=2026-08-29T17:30:00Z, approvedAt=2026-08-29T09:00:00Z]
wrong compiled with zero warnings; approvedAt is before createdAt: true
```

A payment run approved eight and a half hours before it was created. Nothing in the toolchain objects, because both parameters are `Instant`.

**Right**

```java
var right = PaymentRun.builder("PR-2026-08-29", createdAt)
    .itemIds(List.of("W-1", "W-2"))
    .approvedAt(approvedAt)
    .build();
```

Each component's name appears at the call site, so a transposition becomes a visible mistake rather than an invisible one, and `build()`'s cross-component check (`approvedAt` must not precede `createdAt`) catches the inverted pair even if a caller assigns the wrong local to the right method.

**Why people believe it:** the compiler's silence is mistaken for a guarantee. Java's type checking is genuinely strong, so "it compiles" feels like "the arguments are right" — but two parameters of the same type carry no distinguishing information at all, and the strength of the type system is exactly what makes its blind spot here so easy to miss.

### A no-argument constructor plus setters is a fine substitute for a builder

**Wrong**

```java
public final class PaymentRunBean {
    private String runRef;
    private List<String> itemIds;
    private Instant createdAt;
    private Instant approvedAt;

    public PaymentRunBean() { }

    public void setRunRef(String runRef) { this.runRef = runRef; }
    public void setItemIds(List<String> itemIds) { this.itemIds = itemIds; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public void setApprovedAt(Instant approvedAt) { this.approvedAt = approvedAt; }

    public String runRef() { return runRef; }
    public Instant createdAt() { return createdAt; }
}
```

```java
PaymentRunBean run = new PaymentRunBean();
run.setRunRef("PR-2026-08-29");
run.setItemIds(List.of("W-1", "W-2"));
bankWithdrawalQueue.submit(run);       // legal, and approvedAt is still null
run.setCreatedAt(Instant.now());
```

Named components at the call site, optional fields free — and a fully valid instance of the type, handed to the withdrawal queue, with `createdAt` still `null`. No field can be `final`, so nothing in the class can even state which combination is complete, and there is no line anywhere that a reader can point at and say "after this the object is valid".

**Right**

```java
PaymentRun run = PaymentRun.builder("PR-2026-08-29", Instant.now())
    .itemIds(List.of("W-1", "W-2"))
    .build();
bankWithdrawalQueue.submit(run);
```

The mutable phase lives entirely in the `Builder`, which is never published; the object that reaches the queue has `final` fields, passed every `build()` check, and cannot be mutated by whoever holds it. Required components are `final` fields on the `Builder` set only by `PaymentRun.builder`, so no reachable path produces a builder missing one.

**Why people believe it:** setters do solve the two problems people notice — unreadable call sites and optional components — and they are what every JavaBeans-era framework, every ORM tutorial and every IDE's "generate setters" command trains you to write. The problem they do not solve is the one that has no visible symptom until concurrency or a mid-construction hand-off exposes it.

### `volatile` is a performance detail on the double-checked-locking field

**Wrong**

```java
private static LimitSetRegistryBroken instance;   // no volatile

static LimitSetRegistryBroken getInstance() {
    if (instance == null) {
        synchronized (LimitSetRegistryBroken.class) {
            if (instance == null) {
                instance = new LimitSetRegistryBroken();
            }
        }
    }
    return instance;
}
```

The fast path reads `instance` without ever acquiring the monitor, so there is no happens-before edge between the constructor's stores and that read. A reader can see a non-`null` reference whose `maxStake` field still holds `0` — surfacing either as a `NullPointerException` on a field of a definitively non-`null` object, or as a silent limit of zero blocking every stake, with no stack trace and no repeatability.

**Right**

```java
private static volatile LimitSetRegistry instance;

static LimitSetRegistry getInstance() {
    LimitSetRegistry local = instance;
    if (local == null) {
        synchronized (LimitSetRegistry.class) {
            local = instance;
            if (local == null) {
                local = new LimitSetRegistry();
                instance = local;
            }
        }
    }
    return local;
}
```

The `volatile` write to `instance` is a release: every store before it, including all of the constructor's, is ordered before it and visible to any thread whose acquiring read sees the new value. The `local` variable is why the already-initialised path performs one volatile read rather than two — measured, `javap -c -p` shows a single `getstatic` at offset 0 and an `areturn` from local slot 0 at offset 50. Better still, drop the idiom for §3's holder class.

**Why people believe it:** the `synchronized` block is right there, visibly guarding the write, and the assumption is that a mutual-exclusion construct also supplies ordering to code outside it. It does — but only to threads that *enter* it, and the whole point of double-checked locking is that the common path does not.

---

## Cheat sheet

| Thing | The one-line answer |
|---|---|
| Why static factories | Four constructor restrictions lifted: can be named, can return a cached instance, can return a subtype/interface, can share a parameter shape |
| The strong form | A constructor is bound to one concrete class, so a static factory is what makes an interface-typed API possible at all |
| Factory naming convention | `of`, `from`, `valueOf`, `getInstance` (may cache), `newInstance` (must not cache), `copyOf` |
| Static factory costs | Invisible to constructor-reflecting frameworks (JPA, guide 08; Spring, guide 07); bypassed entirely by deserialization; not in the Javadoc constructor summary |
| Measured wrapper cache boundary | `Integer.valueOf(127) == Integer.valueOf(127)` → `true`; at 128 → `false`; `AutoBoxCacheMax = 128` |
| `List.of()` implementations | `ListN` (empty, shared singleton), `List12` (1–2), `ListN` (3+); measured on JDK 21.0.7 |
| Telescoping constructor, failure (a) | Two adjacent same-typed parameters transpose silently — measured, zero `-Xlint:all` warnings, `approvedAt` before `createdAt` |
| Telescoping constructor, failure (b) | N optional components need up to 2^N overloads, or `null` sentinels the constructor cannot tell from "not supplied" |
| Setters vs builder | Setters fix readability and optionality but abandon `final` fields and leave a half-built object legally observable, with no line where it becomes valid |
| Builder's real product | The mutable phase and the published phase are two different objects |
| Factory + builder entry point | `PaymentRun.builder(runRef, createdAt)` returns a builder holding the required components, so `build()` cannot fail on a missing one |
| Builder ceremony line | A builder for a two-field type is pure ceremony; leaf 2.14.12 in `04a-composition-and-cross-index.md` settles where the line falls |
| Four singletons | Eager static (1 line, not lazy) / holder class (lazy, lock-free) / DCL + `volatile` (only one supporting parameters or reset) / enum (1 line, serialization- and reflection-proof) |
| The singleton decision | Enum unless you need laziness; holder class if you do; DCL only if neither will do |
| Why the holder is lazy | `Holder` is a separate class; JVMS 5.5 initialises it only on first active use of `Holder.INSTANCE`. Measured: outer `<clinit>` ran at `schemaVersion()`, holder's did not |
| Why the holder needs no `volatile` | The JVM's per-class initialisation lock supplies the happens-before edge; after init the `getstatic` compiles to a plain read |
| Enum singleton, measured | `deserialized == INSTANCE: true` with no `readResolve`, 79 bytes; reflection → `IllegalArgumentException: Cannot reflectively create enum objects` |
| Singleton meta-point | Usually a dependency-injection problem wearing a static field (guide 07; leaf 2.14.6) |
| The DCL reordering | The store publishing the reference is ordered *before* the constructor's field stores — legal, because no happens-before edge orders a plain store to `instance` against the plain stores to the object's fields |
| DCL symptoms | NPE on a field of a definitively non-`null` object, or a silent `0` where a limit should be |
| DCL version trap | Before Java 5 (JSR-133), `volatile` did not order surrounding non-volatile accesses and DCL was unfixable. Java 5–21: correct with `volatile` |
| Why the `local` variable | Measured: one `getstatic` on the fast path instead of two volatile reads |
| `final` does not rescue DCL | The freeze orders writes relative to the end of the constructor; the field publishing the reference is not `final` |
| Utility class | Only `static` members; one `private` constructor makes it uninstantiable **and** unsubclassable (no accessible `super()`) |
| Why `abstract` fails | Measured: `new LedgerCodes() { }` produced `AbstractProbe$1`; `abstract` also signals "meant to be extended" |
| Why the constructor throws | Closes the hole `private` cannot — the class's own members and nested classes calling `new` from inside. Also defeats `setAccessible(true)`; measured, `InvocationTargetException` wrapping `AssertionError` |
| Strongest uninstantiable form | `enum` with no constants — reflectively uninstantiable too; measured `values().length = 0` |
| The code-review citation | `java.lang.Math` is `private Math() {}` |

---

## Self-test

**Q1.** Name the four constructor restrictions a static factory lifts, and give the strongest single argument for the idiom.

<details><summary>Answer</summary>

A constructor cannot be named; it cannot decline to return a fresh object, because `new` is specified to allocate; it cannot return a subtype, because its invocation syntax names one concrete class; and it cannot be overloaded against a sibling with the same erased parameter shape. A static factory lifts all four at once — the method name carries meaning (`Money.ofMinorUnits` versus `Money.ofMajorUnits`, both `(long, Currency)`, which as two constructors is a compile error: measured, `constructor MoneyClash(long,Ccy2) is already defined`); it may return a cached instance (`Money.zero(GBP) == Money.zero(GBP)` printed `true`, and `Integer.valueOf(127) == Integer.valueOf(127)` is `true` for the same reason, with the boundary at `AutoBoxCacheMax = 128`); it may declare an interface as its return type and vary the implementation (`List.of()` returned `ImmutableCollections$ListN` for empty and `List12` for one and two elements on JDK 21.0.7, all behind a declared `List<E>`); and two factories may share a parameter shape because their names differ. The strongest argument is the third restriction stated as a necessity rather than a convenience: **a constructor and an interface cannot appear in the same expression**, so every interface-typed entry point in the JDK is a static method — there is no alternative, which makes the static factory structural rather than stylistic.

</details>

**Q2.** A colleague argues the telescoping constructor is "ugly but correct." Rebut it with the two concrete failures.

<details><summary>Answer</summary>

Failure (a) is silent transposition. `PaymentRun` has `createdAt` and `approvedAt`, both `Instant`, adjacent in the parameter list. Swapping them at the call site is not a compile error, not a warning, and not detectable by `javac -Xlint:all` — measured on JDK 21.0.7, zero diagnostics, and the resulting object printed `createdAt=2026-08-29T17:30:00Z, approvedAt=2026-08-29T09:00:00Z`, a payment run approved eight and a half hours before it was created. `approvedBy` and `bankFileRef` are both `String` and transpose the same way, landing an operator's identity in the bank file reference. At 7k bank withdrawals/day under operator sign-off that is an audit-trail defect a regulator finds and the compiler never will. Failure (b) is the combinatorics of optional components: three optional components need up to eight overloads to express every combination a caller might want, and the telescoping form supplies only the four prefix combinations, so a caller wanting `bankFileRef` but not `approvedBy` has to pass `null` — which the constructor cannot distinguish from "deliberately not supplied". Generalising, N optional components need up to 2^N overloads or a sentinel vocabulary every caller must memorise. Neither failure is about aesthetics; the first produces wrong objects and the second produces either an unmaintainable API or `null` semantics.

</details>

**Q3.** Why is a no-argument constructor plus setters worse than both the telescoping constructor and the builder?

<details><summary>Answer</summary>

Setters do fix the two visible problems: the component name appears at the call site, so nothing transposes, and skipping a setter is a free way to omit an optional component. The price is that the object is legally observable in a half-built, invariant-violating state, and there is no point at which it is guaranteed complete. A `PaymentRunBean` with `runRef` and `itemIds` set and `createdAt` still `null` is a perfectly valid instance of its type as far as the compiler is concerned, and anything that receives the reference between two setter calls — a queue, a logger, another thread — sees it. Because there is no `build()`, no line of code can be named as the point where the object becomes valid, which also means no field can be `final`: immutability is abandoned wholesale, and with it the safe-publication guarantee that `final` fields carry. The builder gets both benefits at neither cost, because the mutable phase and the published phase are *two different objects* — the `Builder` is mutable and never escapes the calling expression, and the `PaymentRun` it produces has `final` fields and has already passed every check `build()` runs.

</details>

**Q4.** Prove that the holder-class singleton is lazy, and prove that it needs neither `volatile` nor `synchronized`.

<details><summary>Answer</summary>

Laziness first. `Holder` is a separate class from the enclosing `BonusRateTable`, and JVMS 5.5 initialises a class only on the first *active use* of that class. Calling `BonusRateTable.schemaVersion()` is an active use of `BonusRateTable`, not of `Holder`; only the `getstatic Holder.INSTANCE` inside `getInstance()` is an active use of `Holder`. Measured on JDK 21.0.7 with tracing static initialisers: calling `schemaVersion()` printed `[class init] BonusRateTable` and `[class init] BonusRateTable outer body done` but nothing for the holder; the first `getInstance()` printed `[class init] BonusRateTable$Holder`; the second printed nothing and returned the same reference. The expensive construction is therefore deferred past outer-class initialisation, which is exactly what laziness means. Thread safety second. `Holder.INSTANCE`'s assignment happens inside `Holder`'s `<clinit>`, which the JVM runs exactly once under a per-class initialisation lock. JVMS 5.5's procedure blocks any thread finding the class already being initialised until initialisation completes, and the memory model gives the completion of `<clinit>` a happens-before edge to every subsequent read of that class's static fields — so the store to `INSTANCE` and every field store inside the constructor are ordered before any thread's read, which is precisely the guarantee `volatile` is needed for in double-checked locking, supplied here by machinery you did not write. And there is no ongoing lock cost, because once initialisation has completed the JIT compiles `getstatic Holder.INSTANCE` to a plain field read with no barrier.

</details>

**Q5.** Give the exact reordering that breaks double-checked locking without `volatile`, as a thread schedule, and name the two symptoms.

<details><summary>Answer</summary>

`instance = new LimitSetRegistryBroken()` is three actions: allocate, run the constructor's field stores, store the reference into the static field. JLS 17.4 orders two actions only via happens-before, and there is no happens-before edge between thread A's stores inside the `synchronized` block and thread B's read of `instance` on the fast path, because B never acquires the monitor. So this execution is legal: A reads `instance`, sees null, enters the lock, re-reads null, allocates the object with `dailyDeposit` and `maxStake` at their default `0`, and then **stores the reference into `instance` before performing the constructor's field stores** — either because the JIT sank those stores or because B's cache observed them in that order. B now reads `instance` on the fast path, sees non-null, does not enter the lock, returns the reference and reads `maxStake()` as `0`. Only afterwards does A write `2000` and `250` and release the monitor. That step-five inversion — publication of the reference ordered before the writes to the object's fields — is the reordering. Two symptoms, and both are why it is undiagnosable: if the field were a reference type, B dereferences a `null` field on an object it just proved non-`null`, producing a `NullPointerException` that no call-site null check can prevent; and if the field is a primitive, there is no exception at all, just a `maxStake` of `0` silently rejecting every stake or a `dailyDeposit` of `0` blocking every deposit, with no stack trace and no repeatability, because the window is nanoseconds on the first call after start-up.

</details>

**Q6.** "Double-checked locking is broken." True on Java 21? What changed, and when?

<details><summary>Answer</summary>

It depends on `volatile`, and the folklore predates the fix. Before Java 5, the memory model ordered `volatile` accesses with respect to each other but not with respect to surrounding non-volatile accesses, so even a `volatile` field did not stop the constructor's plain field stores being reordered across the publication — double-checked locking was genuinely unfixable within the language, which is what every "DCL is broken" article written before 2004 is describing. JSR-133, shipped in **Java 5**, gave `volatile` release/acquire semantics: a `volatile` write is a release, so every store preceding it — including all of the constructor's — is ordered before it, and a `volatile` read is an acquire, so a thread that sees the new reference sees every one of those stores. From Java 5 through 21 the idiom is therefore correct *provided the field is `volatile`*, and broken without it. The complete modern answer is: "it works, with `volatile`, and you still should not reach for it" — the holder class gets the same lazy, lock-free initialisation in three lines with no reasoning required, and double-checked locking earns its place only when the instance needs a run-time parameter or must be resettable, which a class initialiser cannot express.

</details>

**Q7.** The fields in the broken DCL example are `final`. Does the final-field freeze rescue it?

<details><summary>Answer</summary>

No, and the reason is worth being exact about because the two guarantees look adjacent. JLS 17.5's freeze guarantees that a thread which sees a reference to a *correctly published* object sees that object's `final` fields fully initialised — the constructor's writes to `final` fields are ordered before the end of the constructor, and cannot be seen out of order by a thread that obtained the reference through a properly ordered publication. The broken DCL case fails the precondition: the publication itself is not properly ordered, because the field carrying the reference — `instance` — is a plain, non-`volatile`, non-`final` static field read on an unlocked fast path. The freeze orders the constructor's writes relative to the *end of the constructor*; it says nothing about the order in which a racing reader observes the end of the constructor versus the racy store into a mutable static field. Fix the publication and the freeze becomes relevant; leave the publication racy and it never applies. `02b-records-jmm-and-builders.md` §3 covers what the freeze does buy, and `../classes-and-initialization/04-internals-final-and-constant-folding.md` owns `final` semantics.

</details>

**Q8.** Why is `abstract` the wrong way to make a utility class uninstantiable, and what does the `throw` inside a private constructor actually buy that `private` alone does not?

<details><summary>Answer</summary>

`abstract` blocks `new LedgerCodes()` and nothing else. Measured on JDK 21.0.7, `new LedgerCodes() { }` compiled clean and produced an instance of `AbstractProbe$1`, a subclass of the supposedly uninstantiable class — an anonymous subclass is one expression away. `abstract` also actively misleads, because it signals to every reader that the class is *meant* to be extended, which is the opposite of the intent. A `private` constructor is the only construct that works, and it buys two properties from one modifier: uninstantiable, and unsubclassable, because a subclass constructor must call a superclass constructor and none is accessible — measured, `error: StatusCodesUtil2() has private access in StatusCodesUtil2`. What `private` cannot close is the class's **own** members and its nested classes calling `new` on it from inside, because private access in Java is class-scoped and includes the nesting boundary; that call compiles without complaint. `throw new AssertionError("no instances")` turns it into a run-time failure a test will catch. It also defeats the reflective route as a bonus — measured, `setAccessible(true)` followed by `newInstance()` produced `InvocationTargetException` wrapping `AssertionError: MoneyMath is not instantiable` — so the thrown error, not the access modifier, is what actually enforces the rule.

</details>

**Q9.** Four ways to write an uninstantiable class. Rank them, and say which is genuinely uninstantiable even reflectively.

<details><summary>Answer</summary>

A `private` constructor that throws is the default: uninstantiable by `new`, unsubclassable, reflectively reachable but the throw defeats it, no cost. Adding `final` to the class is the same thing with the intent documented twice — redundant, harmless, and what `java.lang.Math` does (`private Math() {}` on a final class), which is the citation that ends the code-review argument. An `enum` with no constants is the strongest form and the only one that is genuinely uninstantiable reflectively: `Constructor.newInstance` checks the class's `ENUM` modifier and refuses unconditionally — measured on JDK 21.0.7, `IllegalArgumentException: Cannot reflectively create enum objects`, with `values().length = 0` — and no flag, module opening or security policy permits it. Its cost is legibility: it reads as a misuse of `enum` to anyone who has not met the trick. An `interface` with only `static` methods needs no constructor at all, which is its single advantage, and pays for it twice: it cannot be `final`, so `class Whatever implements MoneyMath { }` compiles, is meaningless and is not preventable; and its members are implicitly `public`, so there is no way to keep a helper package-private. Ranking for production code: private constructor that throws, then `final` plus private constructor, then the `enum` when reflective abuse is a real threat, and the `interface` form essentially never.

</details>

---

## Open questions

- **Effective Java item numbers.** Four items are cited in this file by title only — *Consider static factory methods instead of constructors*, *Consider a builder when faced with many constructor parameters*, *Enforce the singleton property with a private constructor or an enum type*, and *Enforce noninstantiability with a private constructor*. The title-to-number mapping is on the standing unverified list and is not asserted here; a copy of the third edition would settle it.
- **The double-checked-locking reordering is argued, not measured.** The nine-step schedule in §4 is derived from JLS 17.4's happens-before rules, which grant the JVM *permission* to reorder rather than mandating that it does. No run is offered, because reproducing the inversion needs a specific JIT-compilation and memory-ordering combination that neither aarch64 nor x86-64 supplies on demand, and a run that fails to reproduce it would prove nothing. A formal model checker over the JMM (a JCStress test with the appropriate acceptable-result annotations) is what would demonstrate the outcome as reachable rather than merely permitted.

---

**Leaves covered:** 2.14.1, 2.14.2, 2.14.3, 2.14.4, 2.14.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 891
