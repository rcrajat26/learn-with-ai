# 03 Java Core — Records — BASICS (§1.19, 1.19.1–1.19.3)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Enum evolution](../enums/03d-internals-enum-evolution.md) · Next: [Generated methods, sealed types, and where a record fits](01a-object-methods-sealed-and-fit.md)

Records and sealed types are **owned by guide 04 (Modern Java)**, which covers the language design, the pattern-matching story, and the API surface. This file owes you the *substrate* half — the part a Java Core interview asks about and a modern-Java tutorial skips. This file covers what `javac` actually puts in the class file for a record, exactly which immutability guarantees a record gives you and which two it does not, and why an array or an unnormalised `BigDecimal` component silently breaks value semantics. [`01a-object-methods-sealed-and-fit.md`](01a-object-methods-sealed-and-fit.md) continues with the `invokedynamic` generated methods, the two structural facts about sealing, and where a record is the wrong choice.

Read guide 04 for the full treatment of records, sealed interfaces, pattern matching and deconstruction patterns. Read [`../../08-spring-data-jpa/`](../00-index.md) for why records are wrong for entities, which is stated here in one paragraph and argued there. This file states each mechanism once, self-contained, and points onward.

All bytecode, attributes and runtime results below were measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**. Library source is quoted from that build's `lib/src.zip`. The types under test come straight from the QuizStakes type sketch:

```java
record Money(BigDecimal amount, Currency currency) { }

record StakeSplit(Money bonusPortion, Money cashPortion) {
    StakeSplit {
        if (bonusPortion == null || cashPortion == null) {
            throw new IllegalArgumentException("null portion");
        }
    }
}

record LedgerBatch(String runId, byte[] signature, List<String> entryIds) { }

sealed interface Verdict permits DocumentVerdict, ScreeningVerdict { }

record DocumentVerdict(String statusCode, String reason) implements Verdict { }

record ScreeningVerdict(String statusCode, boolean prohibited) implements Verdict { }
```

`Money` is the plain case. `StakeSplit` has a compact constructor — and its domain invariant is that **the two portions sum exactly to the stake**. `LedgerBatch` has an array component and a collection component, which is where records get dangerous. `Verdict` is the domain's sealed verdict hierarchy.

---

## 1. A record is a final class with a fixed component list (1.19.1)

`[X-REF 04]` The mental model: a record declaration is a *nominal tuple*. You name the type, you name and type the components in order, and the compiler derives everything that can be derived from that list — the fields, the constructor, the accessors, and the three `Object` methods. What you get is not a new kind of type; it is a `final class` whose superclass is `java.lang.Record` and whose component list is recorded in the class file so reflection and pattern matching can read it back.

### Why it exists

Hand-written value classes are 90% mechanical and 10% wrong. The mechanical part — a field, a constructor parameter, an accessor, an `equals` clause, a `hashCode` term, a `toString` fragment per component — is five edits per component, and adding a seventh component to a six-component class means finding all six places. The wrong part is that `equals` and `hashCode` drift: someone adds a field and updates `equals` but not `hashCode`, and the object becomes unfindable in the `HashMap` it was just put into. Records make the derivation the compiler's job, so the two can never disagree.

### The mechanism

`[SOURCE]` The class header, measured with `javap -p -v Money.class`:

```
final class Money extends java.lang.Record
  minor version: 0
  major version: 65
  flags: (0x0030) ACC_FINAL, ACC_SUPER
  this_class: #8                          // Money
  super_class: #2                         // java/lang/Record
  interfaces: 0, fields: 2, methods: 6, attributes: 4
```

**Note the flags carefully: `0x0030` is `ACC_FINAL | ACC_SUPER` and nothing else.** There is **no `ACC_RECORD` access flag** — the JVMS 21 class access-flag table has `PUBLIC`, `FINAL`, `SUPER`, `INTERFACE`, `ABSTRACT`, `SYNTHETIC`, `ANNOTATION`, `ENUM` and `MODULE`, and no record entry. Record-ness in the class file *is* an attribute:

```
Record:
  java.math.BigDecimal amount;
    descriptor: Ljava/math/BigDecimal;

  java.util.Currency currency;
    descriptor: Ljava/util/Currency;
```

That is the `Record` attribute, and it holds the component list in declaration order with each component's name, descriptor, and any generic signature or annotations. It is what `Class.getRecordComponents()` reads, and it is what makes deconstruction patterns possible. Measured:

```
Money.class.isRecord()          ->  true
Money.class.getSuperclass()     ->  class java.lang.Record
Money.class.getRecordComponents() ->
    [java.math.BigDecimal amount, java.util.Currency currency]
```

`Class.isRecord()` is therefore determined by the superclass being `java.lang.Record` plus the presence of the attribute — the same two-condition shape as `Class.isEnum()`, and for the same reason: no single flag carries it. Compare the enum case in [`../enums/03-internals-enums.md`](../enums/03-internals-enums.md), where there *is* an `ACC_ENUM` flag; sealing and record-ness are both attribute-only, which is the newer design and the one the class file format has settled on.

The generated members, measured:

```
final class Money extends java.lang.Record {
  private final java.math.BigDecimal amount;
  private final java.util.Currency currency;
  Money(java.math.BigDecimal, java.util.Currency);
  public final java.lang.String toString();
  public final int hashCode();
  public final boolean equals(java.lang.Object);
  public java.math.BigDecimal amount();
  public java.util.Currency currency();
}
```

Six things to read off that listing.

**The fields are `private final`.** Not package-private, not `protected` — there is no way to reach them except through the accessors, and no way to change them at all. That is the first immutability guarantee, and concept 2 says exactly how far it goes.

**The canonical constructor's parameters are the components, in order.** Measured body:

```
  Money(java.math.BigDecimal, java.util.Currency);
    Code:
       0: aload_0
       1: invokespecial #1    // Method java/lang/Record."<init>":()V
       4: aload_0
       5: aload_1
       6: putfield      #7    // Field amount:Ljava/math/BigDecimal;
       9: aload_0
      10: aload_2
      11: putfield      #13   // Field currency:Ljava/util/Currency;
      14: return
```

`invokespecial Record.<init>` then one `putfield` per component. Nothing else — no validation, no copying. `java.lang.Record` is an abstract class with a `protected` no-arg constructor and abstract `equals`, `hashCode` and `toString` declarations, which exists purely as the common supertype the attribute-plus-superclass test needs.

**The accessors are named after the components, not `getX`.** `amount()`, not `getAmount()`. That is deliberate and it is a real interoperability cost: JavaBeans-convention tooling — older Jackson without `-parameters` or a `@JsonProperty`, some template engines, some validation frameworks — looks for `getAmount()` and finds nothing. Modern Jackson handles records natively; older tooling does not, and that is one of the two practical reasons concept 6 says a record is sometimes the wrong choice.

**`equals`, `hashCode` and `toString` are `final`.** So a subclass cannot override them — which is moot, since the class is `final` — but more usefully, *you* cannot accidentally half-override them. You *may* declare any of the three explicitly and the compiler will use yours instead of generating one, but you cannot override the generated one.

**The accessors are not `final`.** `public java.math.BigDecimal amount()` carries no `ACC_FINAL`, unlike the three `Object` methods. Irrelevant in practice because the class is `final`, but it tells you the compiler treats them as ordinary methods you may also declare yourself — and you may, to change what an accessor returns (concept 2's defensive-copy fix does exactly that).

**Six methods, and three of them are one instruction long.** That is concept 4.

### Diagram

No diagram for this concept. §1.19's manifest carries none, and the generated-member listing above is the artefact that would otherwise be drawn.

### A concrete example

The domain's `StakeSplit`, with the compact constructor that enforces its invariant. The compact form omits the parameter list and the field assignments — the compiler appends the `putfield`s after your body:

```java
public record StakeSplit(Money bonusPortion, Money cashPortion) {

    /** Compact constructor: no parameter list, no assignments. Validation only. */
    public StakeSplit {
        Objects.requireNonNull(bonusPortion, "bonusPortion");
        Objects.requireNonNull(cashPortion, "cashPortion");
        if (!bonusPortion.currency().equals(cashPortion.currency())) {
            throw new IllegalArgumentException(
                "mixed currencies in stake split: " + bonusPortion.currency()
                    + " and " + cashPortion.currency());
        }
    }

    /** The domain invariant: the two portions sum exactly to the stake. */
    public Money total() {
        return new Money(
            bonusPortion.amount().add(cashPortion.amount()),
            bonusPortion.currency());
    }

    /**
     * The canonical split: min(BONUS_AVAILABLE, 10% of stake) from bonus,
     * rounded DOWN to the minor unit; cash covers the remainder by subtraction,
     * so the two portions sum exactly and no money is created.
     *
     * A stake of 3.33 with bonus available becomes 0.33 + 3.00.
     * Rounding the other way gives 0.34 + 3.00 = 3.34, which creates money.
     */
    public static StakeSplit proportional(Money stake, Money bonusAvailable) {
        BigDecimal cap = stake.amount()
                              .multiply(new BigDecimal("0.10"))
                              .setScale(2, RoundingMode.DOWN);
        BigDecimal fromBonus = cap.min(bonusAvailable.amount());
        BigDecimal fromCash = stake.amount().subtract(fromBonus);
        return new StakeSplit(
            new Money(fromBonus, stake.currency()),
            new Money(fromCash, stake.currency()));
    }
}
```

`[BYTECODE]` The compact constructor's generated body, measured, showing that your validation runs *before* the field assignments:

```
  StakeSplit(Money, Money);
    Code:
       0: aload_0
       1: invokespecial #1    // Method java/lang/Record."<init>":()V
       4: aload_1
       5: ifnull        12
       8: aload_2
       9: ifnonnull     22
      12: new           #7    // class java/lang/IllegalArgumentException
      15: dup
      16: ldc           #9    // String null portion
      18: invokespecial #11   // Method java/lang/IllegalArgumentException."<init>":(Ljava/lang/String;)V
      21: athrow
      22: aload_0
      23: aload_1
      24: putfield      #14   // Field bonusPortion:LMoney;
      27: aload_0
      28: aload_2
      29: putfield      #20   // Field cashPortion:LMoney;
      32: return
```

Offsets 4–21 are the validation from the source. Offsets 22–29 are the two `putfield`s the compiler appended. **Insight:** because the assignments come last, the compact constructor's body operates on the *parameters*, not the fields — so assigning to a parameter inside the body changes what gets stored. That is not a hack, it is the specified mechanism, and it is how normalisation is written:

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        Objects.requireNonNull(currency, "currency");
        // Reassigning the parameter normalises what is stored.
        amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.UNNECESSARY);
    }
}
```

Every `Money` now carries a canonical scale, which — as concept 3 shows — is the difference between `equals` working and `equals` being a trap. Writing `this.amount = amount.setScale(2, RoundingMode.UNNECESSARY)` in a compact constructor is a compile error, precisely so that the "assign the parameter" idiom is the only one available.

### The gotcha

**Pitfall:** believing a record cannot have a constructor that differs from the component list. It can — any number of *additional* constructors, each of which must delegate to the canonical one:

```java
public record Money(BigDecimal amount, Currency currency) {

    /** Convenience for the common case. Must delegate. */
    public Money(String amount, String currencyCode) {
        this(new BigDecimal(amount), Currency.getInstance(currencyCode));
    }
}
```

What you cannot do is declare a constructor whose signature *matches* the canonical one alongside the compact form — that is a duplicate. And you cannot declare an additional constructor that does not delegate: a record's non-canonical constructor must begin with a `this(…)` call, so there is exactly one place fields are assigned. Symptom of not knowing this: a codebase that adds `static of` factories everywhere because "records only have one constructor", which is fine style but is being done for a wrong reason and forecloses the normalising compact constructor. Fix: use the compact constructor for validation and normalisation, additional constructors for convenience, and `static` factories only when the operation genuinely is not construction — `StakeSplit.proportional` above, which computes rather than adapts.

> **Definition.** A record is a `final class` extending `java.lang.Record` with a `private final` field, a canonical-constructor parameter and a same-named accessor per component, `final` generated `equals`/`hashCode`/`toString`, and a `Record` class-file attribute holding the component list — with no `ACC_RECORD` access flag, because none exists.

---

## 2. Records give immutability rules 1 to 3, and not the rest (1.19.2)

`[TRAP]` The claim "records are immutable" is true of the record and false of the object graph it points at. The record's *fields* cannot change. What they point at can, and the compiler will not mention it.

### Why it exists

The compiler can only enforce what it can see. It can make the fields `final` and withhold setters, because those are properties of the record's own declaration. It cannot know whether `List<String>` means "an immutable list" or "a list the caller still holds a reference to", because both have the same type. So the guarantee stops at the field boundary — which is exactly the boundary of what the declaration says.

### The mechanism

The five immutability rules, as they are stated in [`../immutability-and-design/02-immutability.md`](../immutability-and-design/02-immutability.md), against what a record supplies:

| Rule | Record gives it? | Why |
|---|---|---|
| 1. Make every field `final` | **yes** | measured `private final` on every component field |
| 2. Provide no mutators | **yes** | no setters generated, and none can reach the `private` fields |
| 3. Prevent subclassing | **yes** | the class is `ACC_FINAL` |
| 4. Defensively copy mutable components **in** | **no** | the canonical constructor is `putfield` only |
| 5. Defensively copy mutable components **out** | **no** | the accessor is `getfield` only |

`[PROVE]` Rules 4 and 5 measured. The leaky record and the caller's mutation:

```java
record LeakyLimitSet(String clientId, List<String> restrictionKeys) { }

List<String> mutable = new ArrayList<>(List.of("STAKE_BLOCKED"));
var leaky = new LeakyLimitSet("c-1", mutable);
mutable.add("SELF_EXCLUDED");            // the caller still holds the list
```

Measured:

```
leaky.restrictionKeys()  ->  [STAKE_BLOCKED, SELF_EXCLUDED]
```

The record changed. Its field did not — the field still references the same `ArrayList` — but the value the record *represents* changed after construction, which is the only sense of immutability anyone cares about. The bytecode makes it inevitable: the constructor's body for that component is `aload_0; aload_2; putfield`, which stores the reference, and the accessor is `aload_0; getfield; areturn`, which hands it back. No copy on either side.

The fix is a compact constructor, and it is one line per mutable component:

```java
record LimitSet(String clientId, List<String> restrictionKeys) {
    LimitSet {
        restrictionKeys = List.copyOf(restrictionKeys);
    }
}
```

Measured, with the same caller:

```
safe.restrictionKeys().add("SELF_EXCLUDED")
  ->  java.lang.UnsupportedOperationException
```

`List.copyOf` does both jobs at once, which is why it is the right tool: it copies (closing rule 4) *and* returns an unmodifiable list (closing rule 5, since handing out an unmodifiable view needs no copy on the way out). `Set.copyOf` and `Map.copyOf` behave identically. Note that `List.copyOf` also rejects null elements, which is usually what you want and is occasionally a surprise.

**Insight:** `List.copyOf` on an argument that is *already* an immutable `List.of` result returns the same instance rather than copying — the implementation checks — so the defensive copy is free in the common case where the caller passed an immutable list. That removes the usual objection to defensive copying (an allocation per construction) for every well-behaved caller, and charges it only to the callers who actually needed it.

For a component that has no immutable equivalent, the two rules have to be closed separately:

```java
record LedgerBatch(String runId, byte[] signature, List<String> entryIds) {

    LedgerBatch {
        Objects.requireNonNull(runId, "runId");
        signature = signature.clone();              // rule 4
        entryIds = List.copyOf(entryIds);           // rules 4 and 5
    }

    /** Rule 5 for the array: the generated accessor would hand out the field. */
    @Override
    public byte[] signature() {
        return signature.clone();
    }
}
```

Both copies are necessary and neither is sufficient alone. Without the constructor `clone()`, the caller who passed the array can still write into it. Without the accessor override, any caller who *reads* it can. And the accessor override is legal precisely because the generated accessors are not `final` — see concept 1.

There is a fourth guarantee a record does *not* give, and it is worth naming because it is the one people assume most confidently: **a record is not thread-safe by virtue of being a record.** It is safely publishable, because all its fields are `final` and the final-field freeze guarantees a thread that sees the reference sees fully-initialised fields — that is real and it is why records are good for cross-thread value passing. But if a component is a mutable object, two threads sharing the record share that object with no synchronisation at all. The `final`-field freeze is in [`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md); the memory model is guide 05.

### Diagram

No diagram for this concept: the mechanism is a five-row rule table and two measured mutations, both above.

### A concrete example

The QuizStakes `LimitSet`, done properly, with the accessor pattern for a genuinely mutable component:

```java
public record LimitSet(Money dailyDeposit,
                       Money maxStake,
                       Money monthlyLoss,
                       Set<RestrictionType> suppressedChecks) {

    public LimitSet {
        Objects.requireNonNull(dailyDeposit, "dailyDeposit");
        Objects.requireNonNull(maxStake, "maxStake");
        Objects.requireNonNull(monthlyLoss, "monthlyLoss");
        // EnumSet.copyOf would fail on an empty non-EnumSet argument, so build
        // the set explicitly and hand out an unmodifiable view.
        EnumSet<RestrictionType> copy = EnumSet.noneOf(RestrictionType.class);
        copy.addAll(suppressedChecks);
        suppressedChecks = Collections.unmodifiableSet(copy);
    }

    public boolean permits(RestrictionType check) {
        return !suppressedChecks.contains(check);
    }
}
```

Three details. `EnumSet.noneOf` plus `addAll` rather than `EnumSet.copyOf`, because `copyOf` on an empty non-`EnumSet` collection throws `IllegalArgumentException: Collection is empty` — the trap from [`../enums/01b-collections-patterns-and-guarantees.md`](../enums/01b-collections-patterns-and-guarantees.md). `Collections.unmodifiableSet` over the copy rather than `Set.copyOf`, because that preserves the `EnumSet`'s bit-vector performance and its declaration-order iteration, which `Set.copyOf` would discard for a hash-based immutable set. And `Money` needs no copying, because `Money` is itself a record over `BigDecimal` and `Currency`, both immutable — the guarantee composes, which is the whole reason to build a domain out of value types.

### The gotcha

**Pitfall:** believing a record with only "immutable-looking" components is safe. `LocalDate`, `String`, `BigDecimal`, `UUID`, `Instant` and the wrappers genuinely are immutable. `Date`, `Calendar`, `byte[]`, any array, any `Collection` interface type, `StringBuilder`, `AtomicLong`, and any interface you declared yourself are not — and the interface case is the one that slips through, because `record PricingRule(PricingPolicy policy)` looks like a value even when `PricingPolicy` is an interface someone will implement mutably. Symptom: a record used as a `HashMap` key or cached in an immutable collection that stops being findable, because a component mutated and `hashCode` changed — concept 3 has the mechanism. Fix: for each component, ask whether the *type* forbids mutation, not whether the value you happen to be passing is currently unmodified. If the type is an interface or an array, copy in the compact constructor and hand out a copy or a view from an overridden accessor.

> **Definition.** A record supplies immutability rules 1 to 3 — `final` fields, no mutators, no subclassing — automatically and unconditionally, and supplies neither defensive copy: a mutable component is stored by reference and handed back by reference unless a compact constructor and an overridden accessor close both directions.

---

## 3. `equals` is component-wise, so an array component compares by identity (1.19.3)

`[TRAP]` The generated `equals` compares components pairwise. That is exactly right for every component whose type has value semantics, and exactly wrong for every component whose type does not — and an array is the case where the wrongness is invisible, because arrays inherit `Object.equals`.

### Why it exists

The compiler has one general rule available: compare each component with the best comparison the component's type offers. For a reference type that is `Objects.equals`, which delegates to the component's own `equals`. That is the right choice — it is exactly what a hand-written `equals` would do — and it inherits whatever semantics the component type has, including the absence of any. An array's `equals` is `Object.equals`, which is `==`, so a record with an array component gets identity comparison for that component and there is nothing the compiler could do about it without special-casing arrays, which would surprise in the other direction.

### The mechanism

`[SOURCE]` The comparison chosen per component, from `java.lang.runtime.ObjectMethods` on JDK 21:

```java
/** Get the method handle for combining two values of a given type */
private static MethodHandle equalator(Class<?> clazz) {
    return (clazz.isPrimitive()
            ? primitiveEquals.get(clazz)
            : OBJECTS_EQUALS.asType(MethodType.methodType(boolean.class, clazz, clazz)));
}
```

So: a primitive component gets a primitive comparison, and **every reference component gets `Objects.equals`**. That single line is the whole rule, and every consequence below follows from it.

The primitive comparisons are worth reading, because two of them are not `==`:

```java
private static boolean eq(Object a, Object b) { return a == b; }
private static boolean eq(byte a, byte b) { return a == b; }
private static boolean eq(short a, short b) { return a == b; }
private static boolean eq(char a, char b) { return a == b; }
private static boolean eq(int a, int b) { return a == b; }
private static boolean eq(long a, long b) { return a == b; }
private static boolean eq(float a, float b) { return Float.compare(a, b) == 0; }
private static boolean eq(double a, double b) { return Double.compare(a, b) == 0; }
private static boolean eq(boolean a, boolean b) { return a == b; }
```

**`float` and `double` components use `Float.compare`/`Double.compare`, not `==`.** That inverts two floating-point behaviours inside a record relative to bare primitives: `Double.compare(NaN, NaN) == 0`, so **two records with `NaN` components are equal**, whereas `NaN == NaN` is false; and `Double.compare(0.0, -0.0) > 0`, so **a record with `0.0` is not equal to one with `-0.0`**, whereas `0.0 == -0.0` is true. Both are the *right* choice — they make `equals` consistent with `hashCode`, since `Double.hashCode(NaN)` is a fixed value — and both will surprise anyone who reasons about a record's `equals` as a chain of `==`. The three-way floating-point inconsistency itself is in [`../primitives-and-conversions/01c-floating-point.md`](../primitives-and-conversions/01c-floating-point.md).

The overall `equals` shape, from the same file:

```java
return MethodHandles.guardWithTest(isSameObject,
                                   instanceTrue,
                                   MethodHandles.guardWithTest(isInstance, accumulator.asType(ro), instanceFalse));
```

Reference-equal short-circuits to `true`; not an instance of the record class short-circuits to `false`; otherwise the accumulated per-component chain runs, short-circuiting on the first unequal component. Note it is `Class.isInstance`, not `getClass() == other.getClass()` — which is equivalent here only because the class is `final`, and is the reason records sidestep the `getClass()`-versus-`instanceof` argument of [`../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`](../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md) entirely.

`hashCode` combines with the classic multiplier:

```java
private static int hashCombiner(int x, int y) {
    return x*31 + y;
}
```

accumulated from zero over the components in declaration order, with each component hashed by `Objects.hashCode` for a reference or the boxed type's `hashCode` for a primitive. So a record's hash is `((0*31 + h1)*31 + h2)*31 + h3` — the same shape as `Arrays.hashCode` and as `List.hashCode`, but **not** identical to either, so do not expect a record's hash to match a `List.of` of its components. Note the leading `0*31`, which means the first component's hash is used directly; two records whose only difference is a swapped pair of equal-hashing components will collide, which is inherent to the 31-multiplier family and not a record-specific defect.

`toString` uses `Objects.toString` per reference component and the primitive `String.valueOf` overloads otherwise, wrapped in `RecordName[name1=value1, name2=value2]`.

`[PROVE]` Now the array. Measured:

```java
record LedgerBatchLike(String runId, byte[] signature) { }

var x = new LedgerBatchLike("PR-2026-08-29", new byte[]{1, 2, 3});
var y = new LedgerBatchLike("PR-2026-08-29", new byte[]{1, 2, 3});
```

Result:

```
equals = false
hashCode equal = false
toString = LedgerBatchLike[runId=PR-2026-08-29, signature=[B@5f4da5c3]
```

Two records with identical *contents* are unequal, their hashes differ, and `toString` prints `[B@5f4da5c3` — an identity hash in hex, which is also unstable across runs. All three follow from `equalator` choosing `Objects.equals` for the reference component and `byte[]`'s `equals` being `Object.equals`.

The same problem in a less obvious dress: `BigDecimal`. Measured:

```java
var a = new Money2(new BigDecimal("100.00"), "GBP");
var b = new Money2(new BigDecimal("100.0"),  "GBP");
```

```
equals = false          (a.amount().compareTo(b.amount()) == 0)
hashCodes: 9680419 vs 1031388
new HashSet<>(List.of(a, b)).size() = 2
```

Here the component type *does* have value semantics — `BigDecimal.equals` is well defined — but it includes the **scale**, so `100.00` and `100.0` are unequal `BigDecimal`s representing the same number. The record faithfully inherits that, and a `Set<Money>` that should hold one element holds two. This is not a record defect; it is `BigDecimal.equals`'s documented behaviour, treated in [`../numbers-and-money/02-numbers-and-money.md`](../numbers-and-money/02-numbers-and-money.md) with D-073. But a record is where it *bites*, because a hand-written `Money.equals` would have used `compareTo` and the generated one cannot.

The three fixes, in preference order:

1. **Normalise in the compact constructor**, so unequal-but-equivalent values cannot exist. `amount = amount.setScale(2, RoundingMode.UNNECESSARY);`. This is the right answer for `BigDecimal` money: pick the minor unit's scale at the boundary and every `Money` is canonical thereafter.
2. **Change the component type** to one with the semantics you want. `List<Byte>` instead of `byte[]`; `long minorUnits` instead of `BigDecimal`.
3. **Declare `equals`, `hashCode` and `toString` explicitly.** Legal — you may replace any of the generated three — but then you own all three and you have given up the guarantee that they cannot drift apart, which was the reason to use a record. Do it only when the component type is genuinely fixed, as with an array you cannot replace:

```java
public record LedgerBatch(String runId, byte[] signature) {

    public LedgerBatch {
        Objects.requireNonNull(runId, "runId");
        signature = signature.clone();
    }

    @Override
    public byte[] signature() {
        return signature.clone();
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof LedgerBatch that
            && runId.equals(that.runId)
            && Arrays.equals(signature, that.signature);
    }

    @Override
    public int hashCode() {
        return 31 * runId.hashCode() + Arrays.hashCode(signature);
    }

    @Override
    public String toString() {
        return "LedgerBatch[runId=" + runId
            + ", signature=" + HexFormat.of().formatHex(signature) + ']';
    }
}
```

All three overridden together, with `Arrays.equals`/`Arrays.hashCode` and a hex `toString` — note that `signature` inside `equals` reads the *field* directly rather than calling the copying accessor, which avoids an allocation per comparison. `HexFormat` is Java 17+.

### Diagram

No diagram for this concept. §1.19's manifest carries none; the `BigDecimal` scale asymmetry it describes is drawn as D-073 in [`../numbers-and-money/02-numbers-and-money.md`](../numbers-and-money/02-numbers-and-money.md).

### A concrete example

The normalising `Money`, which is the one that should exist in the domain:

```java
public record Money(BigDecimal amount, Currency currency) implements Comparable<Money> {

    public Money {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        // Canonical scale, so two Money values that represent the same amount
        // are equal, hash alike, and deduplicate in a Set.
        amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.UNNECESSARY);
    }

    public static Money of(String amount, String currencyCode) {
        return new Money(new BigDecimal(amount), Currency.getInstance(currencyCode));
    }

    public Money add(Money other) {
        requireSameCurrency(other);
        return new Money(amount.add(other.amount), currency);
    }

    public Money subtract(Money other) {
        requireSameCurrency(other);
        return new Money(amount.subtract(other.amount), currency);
    }

    @Override
    public int compareTo(Money other) {
        requireSameCurrency(other);
        return amount.compareTo(other.amount);
    }

    private void requireSameCurrency(Money other) {
        if (!currency.equals(other.currency)) {
            throw new IllegalArgumentException(
                "currency mismatch: " + currency + " and " + other.currency);
        }
    }
}
```

With that compact constructor, `Money.of("100.00", "GBP").equals(Money.of("100.0", "GBP"))` is `true`, because both normalise to scale 2 before the field is assigned. `RoundingMode.UNNECESSARY` rather than `HALF_UP` is deliberate: it throws `ArithmeticException` if the incoming value has *more* precision than the currency's minor unit, which turns "someone constructed a `Money` of 3.333" into a failure at the boundary rather than a silent rounding somewhere downstream. And note `add` and `subtract` return new instances — the `StakeSplit.proportional` computation of concept 1 relies on `subtract` for the cash portion precisely so that the two portions sum exactly.

### The gotcha

**Pitfall:** using a record with an unnormalised `BigDecimal`, an array, or a `Date` component as a `HashMap` key or a `Set` element. Measured: two `Money2` records over `100.00` and `100.0` produced hashes `9680419` and `1031388` and a `HashSet` of size 2; two records over equal-content `byte[]` were unequal with unequal hashes. Symptom: a deduplicating `Set` that does not deduplicate; a `Map.get` that misses for a key you just built from the same data; a cache with a 0% hit rate that looks correctly implemented. Worse with a mutable component: put the record in a `HashSet`, mutate the component, and the record is now in the wrong bucket — unreachable by `contains`, and still there taking up space. Fix: normalise in the compact constructor, or choose a component type with the value semantics you need, and treat "is every component type's `equals` the equality I mean?" as a required review question for any record used as a key.

> **Definition.** A record's generated `equals` compares components pairwise using `Objects.equals` for every reference type and a primitive comparison otherwise — with `Float.compare`/`Double.compare` for the floating types — so it inherits each component type's equality exactly, which gives identity comparison for an array component and scale-sensitive comparison for a `BigDecimal`.

---

## Pitfalls

### A record with a mutable component

**Wrong**

```java
public record LimitSet(String clientId, List<String> restrictionKeys) { }

List<String> keys = new ArrayList<>(List.of("STAKE_BLOCKED"));
LimitSet limits = new LimitSet("c-1", keys);
keys.add("SELF_EXCLUDED");                    // the caller still holds it
```

Measured: `limits.restrictionKeys()` is `[STAKE_BLOCKED, SELF_EXCLUDED]`. The record's *field* never changed — the constructor is `putfield` only and the accessor is `getfield` only — but the value it represents did, after construction. Put it in a `HashSet` first and it is now in the wrong bucket: unreachable by `contains`, still occupying space.

**Right**

```java
public record LimitSet(String clientId, List<String> restrictionKeys) {
    public LimitSet {
        Objects.requireNonNull(clientId, "clientId");
        restrictionKeys = List.copyOf(restrictionKeys);
    }
}
```

Measured: `safe.restrictionKeys().add("SELF_EXCLUDED")` throws `UnsupportedOperationException`. `List.copyOf` closes both directions at once — it copies (so the caller's later mutation is invisible) and returns an unmodifiable list (so no copy is needed on the way out). It also returns the *same* instance when handed an already-immutable `List.of` result, so the defensive copy is free for well-behaved callers. For a component with no immutable equivalent, such as `byte[]`, the two directions need closing separately: `signature = signature.clone()` in the compact constructor, plus an overridden `signature()` that returns `signature.clone()`.

**Why people believe it:** "records are immutable" is repeated without its scope. The record is immutable; the graph it references is whatever it was. The compiler enforces rules 1 to 3 of immutability and cannot enforce 4 and 5, because it cannot tell from `List<String>` whether the caller intends to keep the reference.

### A record with an array component used as a key

**Wrong**

```java
public record LedgerBatch(String runId, byte[] signature) { }

Set<LedgerBatch> seen = new HashSet<>();
seen.add(new LedgerBatch("PR-2026-08-29", signatureBytes()));
boolean duplicate = seen.contains(new LedgerBatch("PR-2026-08-29", signatureBytes()));
```

Measured with two arrays of identical content: `equals = false`, `hashCode equal = false`, `toString = LedgerBatchLike[runId=PR-2026-08-29, signature=[B@5f4da5c3]`. So `duplicate` is `false` and the set grows without bound. The cause is one line of `ObjectMethods`: `equalator` returns `Objects.equals` for every reference component, and `byte[]`'s `equals` is `Object.equals`, which is `==`.

**Right**

```java
public record LedgerBatch(String runId, byte[] signature) {

    public LedgerBatch {
        Objects.requireNonNull(runId, "runId");
        signature = signature.clone();
    }

    @Override
    public byte[] signature() {
        return signature.clone();
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof LedgerBatch that
            && runId.equals(that.runId)
            && Arrays.equals(signature, that.signature);
    }

    @Override
    public int hashCode() {
        return 31 * runId.hashCode() + Arrays.hashCode(signature);
    }

    @Override
    public String toString() {
        return "LedgerBatch[runId=" + runId
            + ", signature=" + HexFormat.of().formatHex(signature) + ']';
    }
}
```

All three overridden together, because overriding one and not the others is the drift the record was supposed to prevent. Note `equals` reads the *field* rather than calling the copying accessor, so a comparison does not allocate. Where the component type is negotiable, the better fix is to change it — `List<Byte>` has value semantics, and for a signature a `String` in hex or base64 is usually what you actually want on the wire anyway.

**Why people believe it:** the generated `equals` is described as "component-wise", which sounds like content comparison. It is content comparison *delegated to each component type*, and an array type has no content comparison to delegate to. `toString` printing `[B@5f4da5c3` is the visible tell, and it is easy to dismiss as cosmetic.

### An unnormalised `BigDecimal` component

**Wrong**

```java
public record Money(BigDecimal amount, Currency currency) { }

var a = new Money(new BigDecimal("100.00"), Currency.getInstance("GBP"));
var b = new Money(new BigDecimal("100.0"),  Currency.getInstance("GBP"));
```

Measured: `a.equals(b)` is `false`, the hashes are `9680419` and `1031388`, and `new HashSet<>(List.of(a, b)).size()` is `2` — while `a.amount().compareTo(b.amount())` is `0`. `BigDecimal.equals` includes the scale, and the record inherits that faithfully. Two amounts that are the same money are two different `Money` objects, so a deduplicating set does not deduplicate and a `Map<Money, ?>` lookup misses depending on which parse produced the key.

**Right**

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        amount = amount.setScale(currency.getDefaultFractionDigits(),
                                 RoundingMode.UNNECESSARY);
    }
}
```

Every `Money` now carries the currency's canonical scale before the field is assigned, so `equals` and `hashCode` agree with the arithmetic. `RoundingMode.UNNECESSARY` rather than `HALF_UP` is the load-bearing choice: it throws `ArithmeticException` if the incoming value has more precision than the minor unit, turning "somebody constructed a `Money` of 3.333" into a failure at the boundary instead of a silent rounding somewhere downstream. Normalising in the compact constructor is the general fix for any component type whose `equals` is finer-grained than the equality you mean.

**Why people believe it:** `BigDecimal` is the recommended type for money and is genuinely immutable, so it passes every "is this component safe" check except the one that matters — whether its `equals` is the equality the domain means. The failure needs two differently-scaled parses of the same amount to show up, which a single-path test never produces.

---

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Ownership | records and sealed types are **guide 04's** subject. This file owns the class-file substrate |
| Record class header | `final class E extends java.lang.Record`, `flags: (0x0030) ACC_FINAL, ACC_SUPER` |
| `ACC_RECORD` | **does not exist.** Record-ness in the class file *is* the `Record` attribute |
| `Class.isRecord()` | superclass is `java.lang.Record` **and** the `Record` attribute is present |
| `Record` attribute | component name, descriptor, generic signature and annotations, in declaration order |
| Read it with | `Class.getRecordComponents()` — measured `[BigDecimal amount, Currency currency]` |
| `java.lang.Record` | abstract, `protected` no-arg constructor, abstract `equals`/`hashCode`/`toString` |
| Generated members | `private final` field, canonical-constructor parameter and same-named accessor per component; `equals`, `hashCode`, `toString` |
| Canonical constructor body | `invokespecial Record.<init>` then one `putfield` per component. No validation, no copying |
| Accessor naming | `amount()`, **not** `getAmount()` — a real cost with JavaBeans-convention tooling |
| Which generated members are `final` | `equals`, `hashCode`, `toString`. The accessors are **not**, so they can be overridden |
| Compact constructor | omits the parameter list and the assignments; the compiler appends the `putfield`s **after** your body |
| Consequence of that ordering | the body operates on the *parameters*, so assigning a parameter normalises what is stored |
| Assigning `this.x` in a compact constructor | compile error, deliberately — the parameter-assignment idiom is the only one |
| Additional constructors | allowed, any number, each **must** begin with a `this(…)` delegation |
| Immutability rules 1–3 | given: `final` fields, no mutators, `final` class |
| Immutability rules 4–5 | **not** given: no defensive copy in, none out |
| Rule 4 + 5 in one line | `x = List.copyOf(x)` in the compact constructor — copies *and* returns unmodifiable |
| `List.copyOf` on an immutable argument | returns the same instance, so the defensive copy is free for well-behaved callers |
| Array component | needs `x = x.clone()` in the constructor **and** an overridden accessor returning `x.clone()` |
| Thread safety | safely publishable (all fields `final`, so the freeze applies), **not** thread-safe if a component is mutable |
| `equals` per-component rule | `Objects.equals` for every reference type; a primitive comparison otherwise |
| `float` / `double` components | `Float.compare` / `Double.compare`, **not** `==`. So `NaN` records are equal and `0.0` ≠ `-0.0` |
| `equals` overall shape | reference-equal → true; `Class.isInstance` fails → false; else the component chain, short-circuiting |
| Not `getClass()` comparison | it is `isInstance`, equivalent only because the class is `final` |
| `hashCode` combiner | `x*31 + y`, folded from 0 over components in declaration order |
| Not the same as | `List.hashCode` or `Arrays.hashCode` — same family, different result. Do not expect a match |
| Array component equality | **identity**, because `byte[]`'s `equals` is `Object.equals`. Measured `equals = false` on equal content |
| Array component `toString` | `[B@5f4da5c3` — an identity hash in hex, unstable across runs |
| `BigDecimal` component | `equals` includes **scale**. `100.00` ≠ `100.0`; measured `HashSet` size 2 |
| Fix order of preference | 1. normalise in the compact constructor; 2. change the component type; 3. override all three methods |

---

## Self-test

**Q1.** Where does record-ness live in the class file, and what is the analogous fact about sealing?

<details><summary>Answer</summary>

In an attribute, not a flag — for both. Measured on JDK 21.0.7, `Money`'s class header is `final class Money extends java.lang.Record` with `flags: (0x0030) ACC_FINAL, ACC_SUPER` and nothing else: **there is no `ACC_RECORD` access flag**, and the JVMS 21 class access-flag table has no record entry. What carries it is the `Record` attribute, which lists each component's name, descriptor, generic signature and annotations in declaration order — that is what `Class.getRecordComponents()` reads and what makes deconstruction patterns possible. `Class.isRecord()` is therefore a two-condition test: superclass is `java.lang.Record` **and** the attribute is present. Sealing is exactly the same shape: `Verdict`'s header is `flags: (0x0600) ACC_INTERFACE, ACC_ABSTRACT` with no `ACC_SEALED`, and the sealing *is* the `PermittedSubclasses` attribute, which the JVM enforces at link time by rejecting an unlisted subtype. Worth contrasting with the older enum design, where there *is* an `ACC_ENUM` flag — though even there `Class.isEnum()` needs a second condition (`getSuperclass() == java.lang.Enum.class`) because a constant-body subclass carries the flag's absence. The general trend is that newer class-file features are attributes, which is more extensible: an attribute can carry structure, whereas a flag is one bit.

</details>

**Q2.** A record's `equals` is described as component-wise. Derive from the JDK source what happens with a `byte[]` component and with a `double` component.

<details><summary>Answer</summary>

Both from one method in `java.lang.runtime.ObjectMethods`: `equalator(Class<?> clazz)` returns `clazz.isPrimitive() ? primitiveEquals.get(clazz) : OBJECTS_EQUALS.asType(adapted)`. So a `byte[]` component — a reference type — gets `Objects.equals`, which delegates to `byte[]`'s own `equals`, which is inherited `Object.equals`, which is `==`. Measured: two records with `runId` equal and `byte[]{1,2,3}` each were `equals = false` with different hashes, and `toString` printed `signature=[B@5f4da5c3`. A `double` component gets a primitive comparison, and the primitive comparisons are not all `==`: the source has `private static boolean eq(double a, double b) { return Double.compare(a, b) == 0; }` and the same for `float`. That inverts two floating-point behaviours inside a record — `Double.compare(NaN, NaN) == 0`, so two records with `NaN` components are **equal** even though `NaN == NaN` is false; and `Double.compare(0.0, -0.0) > 0`, so a record with `0.0` is **not** equal to one with `-0.0` even though `0.0 == -0.0` is true. Both are the right choice, because they make `equals` consistent with `hashCode` (`Double.hashCode(NaN)` is a fixed value), but neither is what a reader who models record `equals` as a chain of `==` expects. The general rule: a record inherits each component type's equality exactly, so the review question for any record used as a key is "is every component type's `equals` the equality I mean?"

</details>

**Q3.** A record's fields are `final`. Explain precisely what that does and does not guarantee.

<details><summary>Answer</summary>

It guarantees immutability rules 1 to 3 and neither of rules 4 and 5. Rule 1 (every field `final`) and rule 2 (no mutators) are measured directly: the fields are `private final` and no setter is generated, so there is no path to the field at all. Rule 3 (no subclassing) is `ACC_FINAL` on the class. What it does not give is defensive copying, in either direction, because the canonical constructor's body for each component is `aload_0; aload_n; putfield` — storing the reference — and the accessor is `aload_0; getfield; areturn` — handing it back. Measured: a record over a caller-supplied `ArrayList`, with the caller then calling `add`, reported the new element from its accessor. The record's *field* never changed; the value it represents did, which is the only sense of immutability that matters. The fix is one line per mutable component in a compact constructor — `x = List.copyOf(x)` closes both rules at once, because it copies *and* returns an unmodifiable list, and it returns the same instance when handed an already-immutable argument so it is free for well-behaved callers. For a component with no immutable equivalent, such as an array, the two directions need closing separately: `clone()` in the constructor plus an overridden accessor returning `clone()`. One more thing the `final` fields *do* give, worth volunteering: safe publication. The final-field freeze means a thread that sees the record reference sees fully-initialised fields, which is why records are good for cross-thread value passing — but that is publication safety, not thread safety, and two threads sharing a record share any mutable component with no synchronisation at all.

</details>

**Q4.** What does a compact constructor compile to, and why can you not write `this.x = …` in one?

<details><summary>Answer</summary>

To your body followed by the field assignments. Measured on `StakeSplit`, whose compact constructor null-checks both components: `invokespecial Record.<init>` at offset 1, then offsets 4–21 are the validation from the source (`aload_1; ifnull; aload_2; ifnonnull; new IllegalArgumentException; …; athrow`), then offsets 22–29 are the two `putfield`s the compiler appended, then `return`. So the compiler takes the parameter list from the component list, runs your body, and assigns the fields last. That ordering has a consequence that is not a hack but the specified mechanism: **the body operates on the parameters, not the fields**, so assigning to a parameter changes what gets stored. That is how normalisation is written — `amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.UNNECESSARY);` in the body means every constructed `Money` carries a canonical scale, which is the difference between `equals` working and `equals` being a trap. Writing `this.amount = …` is a compile error precisely so the parameter-assignment idiom is the only one available: if both were legal, a reader could not tell whether a compact constructor was validating or overwriting. Two related facts worth volunteering: a record may have any number of *additional* constructors, each of which must begin with a `this(…)` delegation, so there is exactly one place fields are assigned; and you cannot declare a constructor whose signature matches the canonical one alongside the compact form, because that is a duplicate.

</details>

**Q5.** A record's accessors are not `final` but its `equals`, `hashCode` and `toString` are. What does that asymmetry let you do, and what does it not?

<details><summary>Answer</summary>

It lets you override an accessor — which is how the defensive-copy fix for a mutable component is written. Measured member flags on `Money`: `public final java.lang.String toString()`, `public final int hashCode()`, `public final boolean equals(java.lang.Object)`, but `public java.math.BigDecimal amount()` with no `ACC_FINAL`. So `@Override public byte[] signature() { return signature.clone(); }` is legal and is the only way to close immutability rule 5 for an array component, since the generated accessor is `aload_0; getfield; areturn` and hands out the field. What it does *not* do is change the generated `equals`, `hashCode` or `toString`. The bootstrap's static arguments are `REF_getField` method handles — measured `#44 REF_getField Money.amount:Ljava/math/BigDecimal;` — so the three methods read the **fields** directly, never the accessors. That is correct behaviour (comparing two records should not allocate two array copies) but it means the accessor and the generated methods can disagree about what a component "is", and if you override an accessor to return something semantically different you must override all three methods too. Note that the `final` on the three is belt-and-braces given the class is `ACC_FINAL`: its real effect is that you cannot half-replace them by accident, though you *may* declare any of the three explicitly and the compiler will then not generate that one — which is the escape hatch the array case uses. See [`01a-object-methods-sealed-and-fit.md`](01a-object-methods-sealed-and-fit.md) concept 1 for the linkage detail.

</details>
## Open questions

- **Unverified:** whether the JVMS 21 class access-flag table genuinely has no record entry, as concept 1 asserts. The measurement is solid — `Money` compiled to `flags: (0x0030) ACC_FINAL, ACC_SUPER` with a separate `Record` attribute, so on this compiler no such flag is emitted. But "this compiler does not emit it" and "the specification defines no such flag" are different claims, and an `ACC_RECORD` value did appear in early preview drafts. What would settle it: JVMS 21 Table 4.1-B read directly. Nothing here depends on the difference — the attribute is what `Class.isRecord()` actually consults, which is measured.
- **Unverified:** whether `List.copyOf` is *specified* to return the same instance when handed an already-immutable list, or merely does so in this implementation. Concept 2 relies on it for the claim that the defensive copy is free for well-behaved callers. The `List.copyOf` javadoc documents that the returned list is unmodifiable and that the argument's elements are copied, and the implementation checks for an existing immutable list — but whether identity return is contractual was not established. What would settle it: the `java.util.List.copyOf` javadoc read in full, plus `ImmutableCollections` source. The correctness of the defensive copy does not depend on the answer; only the "free" claim does.
- **Unverified:** the exact set of component types whose `equals` is finer-grained than the equality a domain usually means. Concept 3 names `BigDecimal` (scale-sensitive) and arrays (identity) with measurements for both, and concept 2's pitfall lists `Date`, `Calendar`, `StringBuilder`, `AtomicLong` and self-declared interfaces as mutable. That list is not exhaustive and was assembled from the type semantics rather than by enumeration. What would settle it, for a given codebase: a review pass over every record component type asking whether its `equals` is the intended equality. Offered as a review question rather than a closed list.

---

**Leaves covered:** 1.19.1, 1.19.2, 1.19.3 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — §1.19 carries no diagram in the manifest
**Target version:** Java 21 LTS
**Lines:** 760
