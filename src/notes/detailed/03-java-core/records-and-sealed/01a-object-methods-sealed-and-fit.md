# 03 Java Core — Record `Object` methods, sealed types, and fit — BASICS (§1.19, 1.19.4–1.19.6)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Records — shape, immutability, equality](01-basics.md) · Next: [The exception model](../exceptions/01-basics.md)

Three things [`01-basics.md`](01-basics.md) set up and did not finish. How the generated `equals`, `hashCode` and `toString` are actually linked — one `invokedynamic` each to a shared JDK bootstrap, which explains both why overriding an accessor does not affect them and why a record-heavy application pays a cold-start cost. The two structural facts about sealing that a modern-Java tutorial skips: that there is no `ACC_SEALED` flag, and that a pattern switch over a sealed hierarchy uses a mechanism with nothing in common with an enum switch. And the fit question — the four places a record is the wrong tool, each for a different reason.

Records and sealed types are **owned by guide 04 (Modern Java)**, which covers the language design, pattern matching in full, and the API surface. This file owes the class-file substrate only, and points onward. [`../../08-spring-data-jpa/`](../00-index.md) owns the entity argument, stated here in one paragraph.

All bytecode, attributes and runtime results below were measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with **Oracle JDK 17.0.15** for the one version comparison. Library source is quoted from JDK 21.0.7's `lib/src.zip`. The types under test are the `Money`, `StakeSplit`, `LedgerBatch` and `Verdict` declarations from [`01-basics.md`](01-basics.md).

## 1. The three `Object` methods are `invokedynamic`, not inline bytecode (1.19.4)

`[SOURCE]` `[RESEARCH]` `[X-REF 04]` Each of `equals`, `hashCode` and `toString` compiles to a *single* `invokedynamic` instruction whose bootstrap builds a `MethodHandle` tree the first time it is called. This is the same linkage machinery lambdas and indified string concatenation use, and knowing that is what makes the design intelligible.

### Why it exists

The obvious implementation is to emit the comparison chain inline: a `getfield`/`getfield`/`invokevirtual equals`/`ifeq` group per component. `javac` could have done that. Three reasons it did not.

**Code size.** A twelve-component record's inline `equals` is roughly a dozen groups of six instructions, plus the same again for `hashCode` and a `StringBuilder` sequence for `toString` — on the order of a kilobyte of `Code` attribute for methods nobody reads. The `invokedynamic` form is one instruction each, three constant-pool `NameAndType` entries, and one shared `BootstrapMethods` entry.

**Not paying for what you do not use.** A record whose `toString` is never called never runs the bootstrap and never builds the method-handle tree. An unlinked `invokedynamic` costs nothing but its constant-pool entries.

**Leaving the strategy open.** The bootstrap is a JDK method, so its implementation can change between releases without recompiling anything. `ObjectMethods.bootstrap` could specialise, could reorder comparisons by expected selectivity, could exploit future value-type layouts. Inline bytecode would have frozen the 2020 strategy into every class file ever compiled. This is the same argument that moved string concatenation from `StringBuilder` chains to `StringConcatFactory` in Java 9 — see [`../strings/04-internals-stringbuilder-and-concat.md`](../strings/04-internals-stringbuilder-and-concat.md).

### The mechanism

`[BYTECODE]` Measured on `Money`:

```
  public final java.lang.String toString();
    Code:
       0: aload_0
       1: invokedynamic #17,  0    // InvokeDynamic #0:toString:(LMoney;)Ljava/lang/String;
       6: areturn

  public final int hashCode();
    Code:
       0: aload_0
       1: invokedynamic #21,  0    // InvokeDynamic #0:hashCode:(LMoney;)I
       6: ireturn

  public final boolean equals(java.lang.Object);
    Code:
       0: aload_0
       1: aload_1
       2: invokedynamic #25,  0    // InvokeDynamic #0:equals:(LMoney;Ljava/lang/Object;)Z
       7: ireturn
```

Three methods, three instructions each, and all three `invokedynamic` sites reference **bootstrap method `#0`** — one shared entry:

```
BootstrapMethods:
  0: #46 REF_invokeStatic java/lang/runtime/ObjectMethods.bootstrap:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/TypeDescriptor;Ljava/lang/Class;Ljava/lang/String;[Ljava/lang/invoke/MethodHandle;)Ljava/lang/Object;
    Method arguments:
      #8  Money
      #42 amount;currency
      #44 REF_getField Money.amount:Ljava/math/BigDecimal;
      #45 REF_getField Money.currency:Ljava/util/Currency;
```

Read the four static arguments — they are the entire specification of the record, handed to the bootstrap:

- **`Money`** — the record class, so the bootstrap can build the `isInstance` guard.
- **`"amount;currency"`** — the component *names*, semicolon-separated, in declaration order. Only `toString` uses them, which is why they are a single `String` rather than a `String[]`: one constant-pool entry instead of *n*.
- **Two `REF_getField` method handles**, one per component, in declaration order. Direct field accessors — **not** calls to the `amount()`/`currency()` accessor methods.

That last point has a consequence worth stating plainly: **overriding an accessor does not change `equals`, `hashCode` or `toString`.** The defensive-copy accessor from [`01-basics.md`](01-basics.md) concept 2, `public byte[] signature() { return signature.clone(); }`, is invisible to the generated methods, which read the field through a `REF_getField` handle. Which is *correct* — comparing two records should not allocate two array copies — but it means the accessor and the generated methods can disagree about what a component "is", and if you override an accessor to return something semantically different, you must override the three methods too.

The bootstrap's dispatch, from `ObjectMethods`:

```java
case "hashCode" -> {
    if (methodType != null && !methodType.equals(MethodType.methodType(int.class, recordClass)))
        throw new IllegalArgumentException("Bad method type: " + methodType);
    yield makeHashCode(recordClass, getterList);
}
case "toString" -> {
    if (methodType != null && !methodType.equals(MethodType.methodType(String.class, recordClass)))
        throw new IllegalArgumentException("Bad method type: " + methodType);
    List<String> nameList = "".equals(names) ? List.of() : List.of(names.split(";"));
    if (nameList.size() != getterList.size())
        throw new IllegalArgumentException("Name list and accessor list do not match");
    yield makeToString(lookup, recordClass, getters, nameList);
}
default -> throw new IllegalArgumentException(methodName);
```

The `invokedynamic`'s *name* — `equals`, `hashCode` or `toString` — selects the branch. One bootstrap method serving three call sites, discriminated by name, which is why there is one `BootstrapMethods` entry rather than three. Note also the `names.split(";")` and the size check: the component-name string is parsed at link time, once, and validated against the accessor count.

And `makeHashCode`, which is the clearest of the three builders:

```java
private static MethodHandle makeHashCode(Class<?> receiverClass,
                                        List<MethodHandle> getters) {
    MethodHandle accumulator = MethodHandles.dropArguments(ZERO, 0, receiverClass); // (R)I

    // @@@ Use loop combinator instead?
    for (MethodHandle getter : getters) {
        MethodHandle hasher = hasher(getter.type().returnType()); // (T)I
        MethodHandle hashThisField = MethodHandles.filterArguments(hasher, 0, getter);    // (R)I
        MethodHandle combineHashes = MethodHandles.filterArguments(HASH_COMBINER, 0, accumulator, hashThisField); // (RR)I
        accumulator = MethodHandles.permuteArguments(combineHashes, accumulator.type(), 0, 0); // adapt (R)I to (RR)I
    }

    return accumulator;
}
```

A fold: start from a handle that ignores the receiver and returns 0, then for each component compose "hash this field" into `hashCombiner` with the accumulated handle. The result is a single `MethodHandle` of type `(Money)int` that the call site binds. The `// @@@ Use loop combinator instead?` comment is the JDK author's own note, left in the shipped source — a small reminder that this is ordinary code with ordinary loose ends, not magic.

**Insight — the cost profile.** First call to `Money.hashCode()` on a fresh class: run the bootstrap, build *n* handle compositions, install the `CallSite`. Every call thereafter: an already-linked `invokedynamic`, which after JIT compilation inlines through the handle tree to the same `getfield`/`hashCode`/`imul`/`iadd` sequence inline bytecode would have produced. So the steady state is the same and the startup is worse — measurably so for an application with thousands of records whose `equals` runs once each, which is the shape of a startup-time complaint occasionally levelled at record-heavy codebases. That is the trade the design made deliberately: worse cold, identical warm, and open to future improvement.

The same design decision is visible in the enum case for contrast: `values()` is inline bytecode (`getstatic`, `clone`, `checkcast`, `areturn` — see [`../enums/03-internals-enums.md`](../enums/03-internals-enums.md)) because there was nothing to leave open, whereas a record's `equals` had a real strategy question.

### Diagram

No diagram for this concept. §1.19's manifest carries none; the closest analogue is D-100/D-101 for indified string concatenation in [`../strings/04-internals-stringbuilder-and-concat.md`](../strings/04-internals-stringbuilder-and-concat.md), which is the same machinery for a different problem.

### A concrete example

The observable consequence is what a stack trace looks like when a component's `equals` throws:

```java
public record ClientProfile(ClientId clientId, LimitSet limits) {

    /** A component whose equals can throw is a real thing: this one NPEs. */
    public record LimitSet(Money maxStake) {
        @Override
        public boolean equals(Object other) {
            LimitSet that = (LimitSet) other;         // CCE for a non-LimitSet
            return maxStake.equals(that.maxStake);    // NPE if maxStake is null
        }
    }
}
```

Calling `equals` on two `ClientProfile`s whose `limits` have null `maxStake` produces a trace whose frames are `java.lang.invoke.LambdaForm$MH/0x…` and `ClientProfile.equals(ClientProfile.java:1)` — the method-handle frames are synthetic and the record's own frame reports **line 1**, the record declaration, because the generated method has no source lines of its own. So the trace tells you *which record* failed and gives you no line inside it, and the `LambdaForm$MH` frames are the tell that you are looking at a generated `equals` rather than a hand-written one.

Practical consequence: when a record `equals` throws, the diagnosis is always "which component's `equals` did that" and the trace will not tell you directly — you read the frame *below* the `LambdaForm$MH` group. Which is a good argument for the compact constructor rejecting nulls, so that no component can be null and no component's `equals` can NPE:

```java
public record ClientProfile(ClientId clientId, LimitSet limits) {
    public ClientProfile {
        Objects.requireNonNull(clientId, "clientId");
        Objects.requireNonNull(limits, "limits");
    }
}
```

Two lines that turn a confusing `equals`-time NPE into a construction-time failure naming the field.

### The gotcha

**Pitfall:** expecting a record's generated methods to appear in a profiler or a bytecode-analysis tool as ordinary methods. They are one instruction each, so a line-level profiler attributes all the work to the `invokedynamic` line, and a static-analysis tool that counts branches or measures cyclomatic complexity sees none — a twelve-component record's `equals` scores 1. Symptom: a coverage report claiming a record's `equals` is fully covered by one test that never compares unequal records; a complexity metric that says a record is trivial when its `equals` chain is the hottest code in a request. Fix: for coverage, test records like value types — equal, unequal in each component, reflexive, null, different type — rather than trusting the tool. For profiling, look for `LambdaForm$MH` frames and the component types' own `equals`/`hashCode`, which is where the time actually goes.

> **Definition.** A record's `equals`, `hashCode` and `toString` are each a single `invokedynamic` to the shared bootstrap `java.lang.runtime.ObjectMethods.bootstrap`, whose static arguments are the record class, the semicolon-joined component names, and one `REF_getField` handle per component — so the strategy is chosen at first call, the components are read as *fields* rather than through accessors, and the linkage cost is paid once per class.

---

## 2. Sealed types: `permits`, `PermittedSubclasses`, and exhaustive pattern switches (1.19.5)

`[X-REF 04]` A sealed type is a closed hierarchy the compiler can enumerate — which is the same property an enum has, one level up: instead of a fixed set of *instances*, a fixed set of *implementations*. That gives exhaustiveness checking for pattern switches, which is the whole point.

### Why it exists

`final` says "no subtypes". An open interface says "any subtype, anywhere, forever". Between them sits the case most domain modelling actually needs: *these* subtypes and no others, declared in one place. Without a language feature, that was expressible only by convention — a package-private constructor, a comment, a code-review rule — and the compiler could not use it. With `sealed`, the compiler knows the complete list, so a `switch` covering every permitted subtype is provably total and needs no `default`. That in turn makes adding a subtype a compile error at every switch, which is precisely the property that makes an enum's closed set valuable, extended to hierarchies.

### The mechanism

`[SOURCE]` The sealed interface, measured with `javap -p -v Verdict.class`:

```
interface Verdict
  flags: (0x0600) ACC_INTERFACE, ACC_ABSTRACT
  interfaces: 0, fields: 0, methods: 0, attributes: 2
{
}
SourceFile: "LedgerProbe.java"
PermittedSubclasses:
  DocumentVerdict
  ScreeningVerdict
```

**`0x0600` is `ACC_INTERFACE | ACC_ABSTRACT` and nothing else — there is no `ACC_SEALED` flag.** Sealedness in the class file *is* the `PermittedSubclasses` attribute, exactly as record-ness is the `Record` attribute — [`01-basics.md`](01-basics.md) concept 1. The JVM enforces it at link time: a class claiming to implement `Verdict` that is not named in the attribute fails verification. Compare the enum case in [`../enums/03a-internals-enum-members.md`](../enums/03a-internals-enum-members.md): an enum with constant bodies gets the *same* `PermittedSubclasses` attribute, emitted implicitly, which is why such an enum reports `isSealed() == true`.

JEP 409 finalised sealed classes in **Java 17**; they were preview in 15 and 16. The three declaration forms:

- `sealed interface Verdict permits DocumentVerdict, ScreeningVerdict { }` — explicit.
- `sealed interface Verdict { }` with the implementations in the **same file** — the `permits` clause is inferred, and this is the idiomatic form for a small hierarchy.
- Implementations must be `final`, `sealed`, or explicitly `non-sealed`. A permitted subtype that is none of those is a compile error, which forces the decision rather than defaulting to "open".

Measured on the implementations:

```
final class DocumentVerdict extends java.lang.Record implements Verdict
  flags: (0x0030) ACC_FINAL, ACC_SUPER
```

`final` because it is a record; records are always `final`, which is why records-implementing-a-sealed-interface is the natural pairing and needs no extra modifier.

`[BYTECODE]` The exhaustive pattern switch is where the mechanism differs most sharply from an enum switch. Measured on:

```java
static String describe(Verdict verdict) {
    return switch (verdict) {
        case DocumentVerdict d -> "doc " + d.statusCode();
        case ScreeningVerdict s -> "screen " + s.statusCode();
    };
}
```

the bytecode is:

```
       0: aload_0
       1: dup
       2: invokestatic  #7    // Method java/util/Objects.requireNonNull:(Ljava/lang/Object;)Ljava/lang/Object;
       5: pop
       6: astore_1
       7: iconst_0
       8: istore_2
       9: aload_1
      10: iload_2
      11: invokedynamic #13,  0   // InvokeDynamic #0:typeSwitch:(Ljava/lang/Object;I)I
      16: lookupswitch  { // 2
                     0: 54
                     1: 71
               default: 44
          }
      44: new           #17   // class java/lang/MatchException
      47: dup
      48: aconst_null
      49: aconst_null
      50: invokespecial #19   // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
      53: athrow
      54: aload_1
      55: checkcast     #22   // class DocumentVerdict
      58: astore_3
      59: aload_3
      60: invokevirtual #24   // Method DocumentVerdict.statusCode:()Ljava/lang/String;
```

with the bootstrap:

```
BootstrapMethods:
  0: #75 REF_invokeStatic java/lang/runtime/SwitchBootstraps.typeSwitch:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;
    Method arguments:
      #22 DocumentVerdict
      #32 ScreeningVerdict
```

Five differences from an enum switch worth naming, because this is the comparison an interview reaches for.

**No `$SwitchMap` and no synthetic holder class.** The dispatch is an `invokedynamic` to `java.lang.runtime.SwitchBootstraps.typeSwitch`, whose static arguments are the case types in order. An enum switch is a `getstatic` of a `$SwitchMap$E` array plus `ordinal()` plus `iaload` — see [`../enums/03b-internals-guarantees-and-switch.md`](../enums/03b-internals-guarantees-and-switch.md).

**`lookupswitch`, not `tableswitch`.** The `typeSwitch` call returns the index of the first matching case, so the keys are already 0..n−1 and dense — but `javac` emits `lookupswitch` here rather than `tableswitch`. Both are correct; for two cases the difference is immaterial.

**An explicit `Objects.requireNonNull` at offset 2.** A pattern switch with no `case null` rejects null *up front*, with a proper NPE at a `requireNonNull` frame. An enum switch throws NPE at the `invokevirtual ordinal()` instead — same outcome, worse trace. And adding `case null -> …` removes the `requireNonNull` and makes null a real case, which an enum switch cannot do.

**A restart index is threaded through.** `iconst_0; istore_2` then `iload_2` as the second `typeSwitch` argument: the call site takes the index to *start* matching from, which is the machinery guarded patterns (`when` clauses) need — a failed guard re-enters the switch at the next case rather than falling to default.

**The default branch is `new MatchException` with `aconst_null` twice.** Message and cause both null, by construction, because at compile time the branch was proved unreachable. That is the same shape as a stale exhaustive *enum* switch expression, and the same diagnostic problem: if a new permitted subtype is added and this class is not recompiled, you get `MatchException: null`. Measured behaviour of the switch itself, before any such change:

```
describe(new DocumentVerdict("AA-611", "verified"))  ->  doc AA-611
describe(new ScreeningVerdict("AA-599", true))       ->  screen AA-599
```

**One more thing this buys, which enums cannot.** Java 21 (JEP 441) also permits a **qualified enum constant** as a case label, which was a compile error through Java 20 — measured, `case RestrictionType.SELF_EXCLUDED` compiles on JDK 21.0.7 and produces `error: an enum switch case label must be the unqualified name of an enumeration constant` on JDK 17.0.15. That relaxation exists *because* of pattern switches: when the selector is `Object`, an unqualified constant name has no type to resolve against. The detail is in [`../enums/01b-collections-patterns-and-guarantees.md`](../enums/01b-collections-patterns-and-guarantees.md).

### Diagram

No diagram for this concept. §1.19's manifest carries none, and the `$SwitchMap` mechanism it contrasts with is D-118 in [`../enums/03b-internals-guarantees-and-switch.md`](../enums/03b-internals-guarantees-and-switch.md).

### A concrete example

The domain's verdict hierarchy, which is the case sealed types were designed for — a closed set of outcomes each carrying different data:

```java
public sealed interface Verdict {

    String statusCode();

    Instant decidedAt();

    record DocumentVerdict(String statusCode, String reason,
                           Instant decidedAt, String decidedBy) implements Verdict {
        public DocumentVerdict {
            Objects.requireNonNull(statusCode, "statusCode");
            Objects.requireNonNull(decidedAt, "decidedAt");
        }
    }

    record ScreeningVerdict(String statusCode, boolean prohibited,
                            Instant decidedAt) implements Verdict {
        public ScreeningVerdict {
            Objects.requireNonNull(statusCode, "statusCode");
            Objects.requireNonNull(decidedAt, "decidedAt");
        }
    }

    record ReviewVerdict(String statusCode, String operatorId,
                         Instant decidedAt, String note) implements Verdict {
        public ReviewVerdict {
            Objects.requireNonNull(statusCode, "statusCode");
            Objects.requireNonNull(decidedAt, "decidedAt");
        }
    }

    record WealthVerdict(String statusCode, Money assessedIncome,
                         Instant decidedAt) implements Verdict {
        public WealthVerdict {
            Objects.requireNonNull(statusCode, "statusCode");
            Objects.requireNonNull(decidedAt, "decidedAt");
        }
    }
}
```

and the exhaustive dispatch over it, using record deconstruction patterns so the components are bound directly:

```java
public final class VerdictRouting {

    /**
     * Exhaustive over the sealed hierarchy. No default. Adding a fifth Verdict
     * is a compile error here — the same guarantee an exhaustive enum switch gives,
     * extended to a hierarchy whose arms carry different data.
     */
    public static ApplicationStatus next(Verdict verdict) {
        return switch (verdict) {
            case Verdict.DocumentVerdict(String code, String reason, var at, var by)
                when code.equals("AA-690") ->
                    ApplicationStatus.DOCUMENTS_REJECTED;
            case Verdict.DocumentVerdict(String code, var reason, var at, var by) ->
                    ApplicationStatus.DOCUMENTS_VERIFIED;
            case Verdict.ScreeningVerdict(var code, boolean prohibited, var at)
                when prohibited ->
                    ApplicationStatus.SCREENING_PROHIBITED;
            case Verdict.ScreeningVerdict(var code, var prohibited, var at) ->
                    ApplicationStatus.SCREENING_CLEAR;
            case Verdict.ReviewVerdict(String code, var operatorId, var at, var note) ->
                    code.equals("AA-711")
                        ? ApplicationStatus.REVIEW_APPROVED
                        : ApplicationStatus.REVIEW_DECLINED;
            case Verdict.WealthVerdict(String code, Money income, var at) ->
                    switch (code) {
                        case "AO-141" -> ApplicationStatus.WEALTH_ACCEPTABLE;
                        case "AO-145" -> ApplicationStatus.WEALTH_REFERRED;
                        default -> ApplicationStatus.WEALTH_REJECTED;
                    };
        };
    }

    public enum ApplicationStatus {
        DOCUMENTS_VERIFIED, DOCUMENTS_REJECTED,
        SCREENING_CLEAR, SCREENING_PROHIBITED,
        REVIEW_APPROVED, REVIEW_DECLINED,
        WEALTH_ACCEPTABLE, WEALTH_REFERRED, WEALTH_REJECTED
    }
}
```

Two things this shape gives that a hierarchy of classes with a `nextStatus()` method would not. The routing logic is in *one* place, so reading it tells you the whole state machine — whereas polymorphic dispatch scatters it across four files. And the `when` guards let two arms share a subtype, which polymorphism cannot express without an `if` inside the method. The trade-off is the mirror image: adding a *behaviour* means editing every switch, whereas adding a *subtype* means editing every switch under either design. Choose the switch when the operations outnumber the types and change more often; choose polymorphism when the types outnumber the operations. Note that the guarded arms need the restart-index machinery described above: a failed `when` re-enters the switch at the next case.

The inner `switch` on `code` is a plain `String` switch, which has its own two-stage desugaring — [`../control-flow/01b-string-and-enum-switch.md`](../control-flow/01b-string-and-enum-switch.md).

### The gotcha

**Pitfall:** sealing a hierarchy across module or package boundaries without realising the constraint. A `sealed` type's permitted subtypes must be in the **same module** if it is in a named module, or the **same package** if it is in an unnamed one — and, if the `permits` clause is omitted, the same *source file*. Symptom: a `sealed interface` in an API module and its implementations in a provider module, which does not compile, with an error about the permitted subclass not being in the same module. Fix: keep the sealed hierarchy inside one module, which is usually the right design anyway — a hierarchy that a downstream module needs to extend is not closed and should not be sealed. If the requirement is "closed for now, extensible later", `non-sealed` on one arm reopens exactly that branch, which is the intended escape hatch and is more honest than sealing and then fighting it.

> **Definition.** A `sealed` type declares its complete set of direct subtypes, recorded in the class file as a `PermittedSubclasses` attribute with no corresponding access flag and enforced by the JVM at link time; a pattern switch over it dispatches through `invokedynamic` to `SwitchBootstraps.typeSwitch`, is exhaustive without a `default`, and throws a message-free `MatchException` if a subtype is added without recompiling.

---

## 3. Where a record is right, and where it is not (1.19.6)

`[X-REF 08]` Records are the right default for a value with a fixed component list and no identity. Three cases where they are the wrong choice, and each for a different reason.

### Why it exists

A record trades away three things for its brevity: identity semantics, mutability, and inheritance. Each of those is load-bearing somewhere. Knowing which somewhere is the difference between "records everywhere" — which produces a codebase fighting JPA and a DTO layer that cannot evolve — and using them where they pay.

### The mechanism

**Right: a value with a fixed component list and no identity.** Every case where two instances with the same components *are* the same thing. In the QuizStakes model: `Money`, `ClientId`, `ApplicationId`, `RoundId`, `IdempotencyKey`, `StatusCode`, `Jurisdiction`, `AgreementRef`, `LimitSet`, `StakeSplit`, `RestrictionKey`, every `Verdict` arm. Also: multiple return values, a map key, a query-result row, an event payload, a cache key, a method's local grouping.

**Wrong 1: a JPA entity.** Four independent reasons, and any one is disqualifying.

- **JPA needs a no-arg constructor** to instantiate an entity before populating it. A record has only its canonical constructor, and there is no way to add a no-arg one — a record's additional constructors must delegate to the canonical one, and a no-arg constructor cannot supply the components.
- **JPA needs mutable fields** for dirty checking and for populating lazily-loaded associations. A record's fields are `final`, and reflective writes to `final` instance fields are refused since Java 9 — `IllegalAccessException: Can not set final … field`, measured behaviour discussed in [`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md).
- **An entity's identity is its primary key, not its components.** Two `Account` rows with identical column values are different accounts. A record's `equals` is component-wise, which is the wrong equality — and a JPA entity's `equals`/`hashCode` must be stable across the transient-to-persistent transition, which a component-wise `equals` over a null-then-assigned id cannot be. This is guide 08's subject.
- **Lazy loading needs a proxy**, which needs a non-final class. A record is `ACC_FINAL`.

A record *is* right for a JPA **projection** — a read-only query result — and Spring Data JPA and JPQL constructor expressions both support that directly. The rule is: entity no, projection yes.

**Wrong 2: a DTO that must evolve, or that a mutable-binding framework populates.** Two distinct problems. A record's component list is its public API in a strong sense: adding a component changes the canonical constructor's signature, so every construction site breaks — which is a *feature* for an internal value and a problem for a DTO with many external construction sites. And any framework that constructs-then-populates needs setters: older Jackson without `-parameters` or `@JsonProperty` annotations cannot bind to a record's constructor, because the parameter names are not in the class file unless `javac -parameters` was used. Modern Jackson handles records natively via the `Record` attribute; older versions and some other binders do not. Note the asymmetry: the *component names* are always in the class file (in the `Record` attribute, as concept 1 shows), but the *constructor parameter names* are only there with `-parameters`, and some tools read the latter. What `-parameters` buys is treated in [`../language-substrate/02-packages-modules-annotations.md`](../language-substrate/02-packages-modules-annotations.md).

**Wrong 3: anything that needs inheritance.** A record is `final` and its superclass is fixed at `java.lang.Record`, so it can neither extend nor be extended. It can `implements` any number of interfaces — which is how the sealed-hierarchy pairing of concept 2 works, and covers most of what inheritance would have been used for. But a template-method base class, or a hierarchy with shared state, is not expressible.

**Wrong 4, worth adding: anything with a mutable component you cannot copy.** [`01-basics.md`](01-basics.md) concept 2's rules 4 and 5 are closable for collections and arrays, at the cost of a compact constructor and an overridden accessor. For a component whose type is an open interface — a `PricingPolicy`, a `Clock`, a service — there is no copy to make, so the record's immutability is nominal. That is usually a sign the thing is not a value: a "record" holding a service reference is a parameter object, and a plain final class with a documented lifetime is more honest.

### Diagram

No diagram for this concept: it is a four-case decision list and the prose above is the rendering. The equivalent decision across all constructs is D-089 in [`../immutability-and-design/05-which-construct.md`](../immutability-and-design/05-which-construct.md).

### A concrete example

The same data, three times: as an entity, as a projection, and as a domain value.

```java
/** The entity. A class, mutable, no-arg constructor, id-based equality. */
@Entity
@Table(name = "client_restriction")
public class RestrictionEntity {

    @Id
    private UUID id;

    @Column(name = "client_id", nullable = false)
    private UUID clientId;

    @Column(name = "restriction_type", length = 16, nullable = false)
    private RestrictionType type;

    @Column(name = "restriction_source", length = 24, nullable = false)
    private RestrictionSource source;

    @Column(name = "applied_at", nullable = false)
    private Instant appliedAt;

    /** Required by JPA. A record cannot have one. */
    protected RestrictionEntity() {
    }

    public RestrictionEntity(UUID id, UUID clientId, RestrictionType type,
                             RestrictionSource source, Instant appliedAt) {
        this.id = id;
        this.clientId = clientId;
        this.type = type;
        this.source = source;
        this.appliedAt = appliedAt;
    }

    /** Identity is the key, not the components. */
    @Override
    public boolean equals(Object other) {
        return other instanceof RestrictionEntity that
            && id != null
            && id.equals(that.id);
    }

    @Override
    public int hashCode() {
        return id == null ? 0 : id.hashCode();
    }

    public UUID id() {
        return id;
    }

    public RestrictionType type() {
        return type;
    }

    public RestrictionSource source() {
        return source;
    }

    public Instant appliedAt() {
        return appliedAt;
    }
}

/** The projection. A record is exactly right: read-only, component-wise value. */
public record RestrictionSummary(RestrictionType type,
                                 RestrictionSource source,
                                 Instant appliedAt) { }

/** The domain value. A record, with the (type, source) identity the domain specifies. */
public record RestrictionKey(RestrictionType type, RestrictionSource source) {

    public RestrictionKey {
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(source, "source");
    }

    /**
     * Restriction identity is the pair, not the type alone: STAKE_BLOCKED from
     * SYSTEM_ONBOARDING lifts automatically at AA-801 ACTIVATED, while the same
     * type from ADMIN does not.
     */
    public boolean liftsOnActivation() {
        return source == RestrictionSource.SYSTEM_ONBOARDING;
    }
}
```

and the repository method that produces the projection:

```java
public interface RestrictionRepository extends Repository<RestrictionEntity, UUID> {

    @Query("""
           select new com.quizstakes.restrictions.RestrictionSummary(
                      r.type, r.source, r.appliedAt)
             from RestrictionEntity r
            where r.clientId = :clientId
            order by r.appliedAt desc
           """)
    List<RestrictionSummary> summariesFor(@Param("clientId") UUID clientId);
}
```

The constructor expression in JPQL calls the record's canonical constructor directly, which is why a record is the natural projection type — no no-arg constructor is needed, because JPA constructs it in one call rather than construct-then-populate. `RestrictionKey`, meanwhile, is a genuine value: two keys with the same type and source *are* the same restriction identity, so component-wise equality is exactly the equality the domain means, and it slots straight into an `EnumMap` or a `Set` without further thought.

### The gotcha

**Pitfall:** using a record as a JPA entity because it compiles. Some of it does. `@Entity` on a record is rejected by Hibernate at bootstrap with a message about the missing no-arg constructor — that failure is at least loud. What is quieter is a record used as an `@Embeddable`, or as an `@IdClass`, both of which some provider versions partially accept and then behave oddly around dirty checking and merge. Symptom: an entity that never appears dirty so updates are silently dropped, or a composite key that works for reads and fails on `merge`. Fix: entities and embeddables are mutable classes with no-arg constructors; records are projections, query parameters, and domain values that never enter the persistence context. Guide 08 has the full argument.

> **Definition.** Use a record for a value with a fixed component list and no identity — money, ids, keys, projections, event payloads, sealed-hierarchy arms — and not for a JPA entity (no no-arg constructor, `final` fields, key-based identity, no proxying), a DTO bound by a construct-then-populate framework or with many external construction sites, anything needing inheritance, or anything holding a component that cannot be copied.
---

## Pitfalls

### Overriding an accessor and expecting `equals` to follow

**Wrong**

```java
public record LedgerBatch(String runId, byte[] signature) {

    public LedgerBatch {
        signature = signature.clone();
    }

    /** Closes immutability rule 5. Does nothing for equals. */
    @Override
    public byte[] signature() {
        return signature.clone();
    }
}
```

The accessor override is correct and necessary — without it, any caller reading `signature()` gets the field and can write into it. What it does *not* do is change `equals`, `hashCode` or `toString`, because the bootstrap's static arguments are `REF_getField` handles: measured `#45 REF_getField LedgerBatch.signature:[B`. The three generated methods read the field directly and never call the accessor, so two `LedgerBatch` values with equal content are still unequal, still hash differently, and still print `[B@5f4da5c3`.

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

All three declared explicitly, so the compiler generates none of them and there is no `invokedynamic` left to disagree with the accessor. Note `equals` reads the *field* rather than calling the copying accessor, so a comparison allocates nothing.

**Why people believe it:** the generated methods are described as being built from the components, and the accessors are the components' public face — so it reads as though the accessor is the definition. The bootstrap arguments say otherwise, and reading the `BootstrapMethods` block once settles it permanently.

### Sealing a hierarchy across a module boundary

**Wrong**

```java
// module com.quizstakes.api
public sealed interface Verdict permits DocumentVerdict, ScreeningVerdict { }

// module com.quizstakes.documents
public record DocumentVerdict(String statusCode, String reason) implements Verdict { }
```

Does not compile. A `sealed` type's permitted subtypes must be in the **same module** when the type is in a named module, or the same package when it is in an unnamed one — and, if the `permits` clause is omitted, the same source file. The error names the permitted subclass and the module boundary, which at least points at the cause.

**Right**

Keep the sealed hierarchy in one module, which is almost always the correct design — a hierarchy a downstream module needs to extend is not closed and should not be sealed:

```java
// module com.quizstakes.api — all arms together, permits clause inferred
public sealed interface Verdict {

    String statusCode();

    Instant decidedAt();

    record DocumentVerdict(String statusCode, String reason,
                           Instant decidedAt, String decidedBy) implements Verdict { }

    record ScreeningVerdict(String statusCode, boolean prohibited,
                            Instant decidedAt) implements Verdict { }
}
```

Where the requirement genuinely is "closed for now, extensible later", `non-sealed` on the one arm that must be open reopens exactly that branch and leaves the rest closed — which is more honest than sealing and then fighting the constraint.

**Why people believe it:** sealing looks like a visibility modifier, and visibility modifiers cross module boundaries freely (`public` works everywhere it is exported). Sealing is not visibility — it is an enumerated list the JVM verifies at link time, and the verifier needs the whole list to be resolvable and co-located.

### A record as a JPA `@Embeddable` or `@IdClass`

**Wrong**

```java
@Embeddable
public record MoneyColumn(BigDecimal amount, String currencyCode) { }

@Entity
public class LedgerEntryEntity {
    @Id
    private UUID id;

    @Embedded
    private MoneyColumn amount;
}
```

`@Entity` on a record fails loudly at Hibernate bootstrap with a message about the missing no-arg constructor. `@Embeddable` and `@IdClass` are the quieter cases: some provider versions partially accept them and then behave oddly around dirty checking and `merge`, because the provider cannot write the `final` fields after construction.

**Right**

```java
@Embeddable
public class MoneyColumn {

    @Column(name = "amount", nullable = false, precision = 19, scale = 4)
    private BigDecimal amount;

    @Column(name = "currency", length = 3, nullable = false)
    private String currencyCode;

    /** Required by JPA. */
    protected MoneyColumn() {
    }

    public MoneyColumn(BigDecimal amount, String currencyCode) {
        this.amount = amount;
        this.currencyCode = currencyCode;
    }

    /** Convert to the domain value at the boundary, where the record belongs. */
    public Money toDomain() {
        return new Money(amount, Currency.getInstance(currencyCode));
    }

    public static MoneyColumn from(Money money) {
        return new MoneyColumn(money.amount(), money.currency().getCurrencyCode());
    }
}
```

A mutable class with a no-arg constructor at the persistence boundary, and the record — `Money` — as the domain value on the other side of it, with explicit conversion in both directions. The `precision = 19, scale = 4` on the column is the domain's money storage decision; see [`../../09-sql-databases/`](../00-index.md).

**Why people believe it:** an `@Embeddable` genuinely *is* a value object — component-wise equality, no identity of its own — so a record looks like the perfect fit conceptually. The blocker is mechanical rather than conceptual: the provider constructs then populates, and a record cannot be populated.


---
---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Generated method bytecode | one `invokedynamic` each — 3 instructions per method |
| Bootstrap | `java.lang.runtime.ObjectMethods.bootstrap`, **one shared** `BootstrapMethods` entry for all three |
| Bootstrap static arguments | the record class; the semicolon-joined component names; one `REF_getField` handle per component |
| Components are read as **fields** | not through accessors — so overriding an accessor does **not** change the three methods |
| Which branch runs | selected by the `invokedynamic`'s *name*: `equals`, `hashCode` or `toString` |
| Why `invokedynamic` | code size, pay-per-use linkage, and leaving the strategy open across releases |
| Cost profile | worse cold (bootstrap builds *n* handle compositions per class), identical warm after JIT |
| Stack trace shape | `LambdaForm$MH/0x…` frames, and the record's own frame reports **line 1** |
| Profiler/analysis consequence | a 12-component `equals` scores complexity 1 and one line. Test records as value types instead |
| `ACC_SEALED` | **does not exist.** Sealedness *is* the `PermittedSubclasses` attribute |
| Sealed interface flags | measured `(0x0600) ACC_INTERFACE, ACC_ABSTRACT` — nothing sealing-specific |
| Enforcement | the JVM rejects an unlisted subtype at link time |
| JEP / version | JEP 409, final in **Java 17**; preview in 15 and 16 |
| `permits` inference | omit it and put the implementations in the same **source file** |
| Permitted subtypes must be | `final`, `sealed`, or explicitly `non-sealed` — the decision is forced |
| Scope constraint | same module (named) or same package (unnamed); same file if `permits` is inferred |
| Records + sealed | the natural pairing: records are already `final`, so no extra modifier is needed |
| Enums are implicitly sealed too | an enum with constant bodies gets the same `PermittedSubclasses` attribute |
| Pattern switch dispatch | `invokedynamic` → `java.lang.runtime.SwitchBootstraps.typeSwitch`, case types as static arguments |
| vs an enum switch | no `$SwitchMap`, no synthetic holder class, `lookupswitch` rather than `tableswitch` |
| Null handling | an explicit `Objects.requireNonNull` at the head — better trace than an enum switch's NPE at `ordinal()` |
| `case null` | legal in a pattern switch, removes the `requireNonNull`. Impossible in a plain enum switch |
| Restart index | `iconst_0; istore_2` threaded into `typeSwitch` — the machinery `when` guards need |
| Exhaustive, no `default` | its default branch is `new MatchException` with `aconst_null` twice: message and cause both null |
| Stale after a new subtype | `MatchException: null` at runtime — same failure shape as a stale exhaustive enum switch |
| Java 21 enum-label change | JEP 441 permits a **qualified** enum constant as a case label; a compile error through Java 20 |
| Record: right for | money, ids, keys, projections, query rows, event payloads, multiple returns, sealed-hierarchy arms |
| Record: wrong for a JPA entity | no no-arg constructor; `final` fields block dirty checking; identity is the key, not the components; `final` blocks proxying |
| Record: right for a JPA **projection** | yes — a JPQL constructor expression calls the canonical constructor directly |
| Record: wrong for an evolving DTO | adding a component changes the canonical constructor's signature, breaking every construction site |
| Record + older binders | constructor *parameter* names need `javac -parameters`; the *component* names are always in the attribute |
| Record: wrong when inheritance is needed | `final`, and the superclass is fixed at `java.lang.Record`. Interfaces only |
| Record: wrong with an uncopyable component | an open-interface or service component makes the immutability nominal. That is a parameter object, not a value |

---


---

## Self-test

**Q1.** Why are `equals`, `hashCode` and `toString` `invokedynamic` rather than inline bytecode, and what is the one visible consequence?

<details><summary>Answer</summary>

Three reasons, and each is a real trade. **Code size**: a twelve-component record's inline `equals` is roughly a dozen six-instruction groups, plus the same for `hashCode` and a `StringBuilder` sequence for `toString` — on the order of a kilobyte of `Code` attribute. The measured `invokedynamic` form is three instructions per method, three constant-pool `NameAndType` entries, and **one shared** `BootstrapMethods` entry serving all three call sites, discriminated by the `invokedynamic`'s *name*. **Pay per use**: a record whose `toString` is never called never runs the bootstrap. **Strategy left open**: `ObjectMethods.bootstrap` is a JDK method, so its implementation can change between releases without recompiling anything — the same argument that moved string concatenation to `StringConcatFactory` in Java 9. The visible consequence: the bootstrap's static arguments are the record class, the semicolon-joined component names, and one **`REF_getField`** handle per component — measured `#44 REF_getField Money.amount:Ljava/math/BigDecimal;`. Direct *field* handles, not calls to the accessor methods. So **overriding an accessor does not change `equals`, `hashCode` or `toString`.** The defensive-copy accessor `public byte[] signature() { return signature.clone(); }` is invisible to them, which is correct (comparing two records should not allocate two copies) but means the accessor and the generated methods can disagree about what a component is. If you override an accessor to return something semantically different, you must override all three methods too.

</details>

**Q2.** Contrast the bytecode of a pattern switch over a sealed interface with an enum switch.

<details><summary>Answer</summary>

Different mechanisms entirely. An enum switch is pure `javac` desugaring with no runtime involvement: `getstatic <Switching>$1.$SwitchMap$E:[I`, `invokevirtual E.ordinal()`, `iaload`, then a dense `tableswitch` — with the array built in a synthetic package-private holder class whose `<clinit>` has one swallowed `NoSuchFieldError` guard per case. A sealed pattern switch is `invokedynamic` to `java.lang.runtime.SwitchBootstraps.typeSwitch`, with the case types as bootstrap static arguments (measured: `#22 DocumentVerdict`, `#32 ScreeningVerdict`), followed by a `lookupswitch` on the returned index. Four further differences. The pattern switch opens with an explicit `dup; invokestatic Objects.requireNonNull; pop` at offsets 1–5, so null is rejected up front with a clean NPE frame, whereas an enum switch throws NPE at the `invokevirtual ordinal()` with a worse trace — and adding `case null ->` removes the `requireNonNull` and makes null a real case, which a plain enum switch cannot do. A restart index is threaded in (`iconst_0; istore_2` then `iload_2` as `typeSwitch`'s second argument), which is the machinery `when` guards need: a failed guard re-enters at the next case. Each arm does its own `checkcast` and `astore` to bind the pattern variable. And the two share one failure shape: the exhaustive-without-`default` branch is `new MatchException` with `aconst_null` twice, so if a permitted subtype is added and the switch is not recompiled you get `MatchException: null` — message and cause both null, because at compile time the branch had been proved unreachable.

</details>

**Q3.** Give the four reasons a record is wrong for a JPA entity, and the one JPA role it is right for.

<details><summary>Answer</summary>

**No no-arg constructor.** JPA instantiates an entity and then populates it, so it needs one; a record has only its canonical constructor, and additional constructors must delegate to it, which a no-arg one cannot do. **`final` fields.** Dirty checking and lazy-association population need to write fields after construction, and reflective writes to `final` instance fields have been refused since Java 9 with `IllegalAccessException: Can not set final … field`. **Wrong equality.** An entity's identity is its primary key: two `Account` rows with identical column values are different accounts. A record's `equals` is component-wise, and it additionally cannot be stable across the transient-to-persistent transition, where the id goes from null to assigned. **No proxying.** Lazy loading needs a subclass or a bytecode-generated proxy, and a record is `ACC_FINAL`. The role it *is* right for is a **projection** — a read-only query result. A JPQL constructor expression (`select new com.example.RestrictionSummary(r.type, r.source, r.appliedAt) from …`) calls the canonical constructor in one go, so no no-arg constructor is needed and the component-wise equality is exactly what a value row should have. Worth adding the quiet failure to watch for: `@Entity` on a record is rejected loudly at Hibernate bootstrap, but a record used as an `@Embeddable` or an `@IdClass` is partially accepted by some provider versions and then misbehaves around dirty checking and `merge` — an entity that never appears dirty, so updates are silently dropped.

</details>

**Q4.** You have four known payment rails plus whatever a new PSP integration sends. Why is a sealed interface the right shape and an enum with an `OTHER` constant the wrong one?

<details><summary>Answer</summary>

Because there is only one `OTHER` object. An enum constant is a `static final` field, so a per-instance payload — the actual rail name — has to live in a side channel such as a `static Map<PaymentRail, String>`, which is global mutable state where the last writer wins for every concurrent reader in the process. Every property the enum was chosen for then fails: a `switch` cannot distinguish two different unknown rails, an `EnumMap` collapses them into one slot, `equals` reports them as the same rail, and there is no thread-safe read of the name at all. The sealed shape keeps the closed part closed and lets the open part be genuinely open: an inner `enum Known implements PaymentRail` carrying the four constants with their codes, plus a `record Unknown(String code) implements PaymentRail`. Each unknown rail is then its own value with correct `equals` and `hashCode` for free, because it is a record over a `String`. A pattern switch over `PaymentRail` is exhaustive across `Known` and `Unknown`, so the compiler still forces both to be handled — and enumerating the `Known` constants explicitly inside that switch keeps the property that adding a fifth known rail is a compile error. The closed arm retains every enum guarantee: singleton constants, `EnumSet` and `EnumMap`, serialization by name. Only the part that actually needed to be open pays for being open. The general principle: `sealed` is for a closed set of *implementations* the way an enum is for a closed set of *instances*, and mixing the two is the idiomatic way to model "mostly closed".

</details>

---


**Q5.** How does the pattern switch's default branch differ from an enum switch's, and why does that matter operationally?

<details><summary>Answer</summary>

It does not differ — that is the point. Both compile their unreachable default to `new java/lang/MatchException` with `aconst_null` twice, so the message and the cause are both null by construction. Measured on the sealed switch: offsets 44–53 are `new MatchException; dup; aconst_null; aconst_null; invokespecial MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V; athrow`. The identical shape appears in a stale exhaustive *enum* switch expression — see [`../enums/03b-internals-guarantees-and-switch.md`](../enums/03b-internals-guarantees-and-switch.md). The reason the compiler emits no message is that at compile time it had *proved* the branch unreachable, so there was nothing to say. Operationally that matters in one specific situation: a permitted subtype (or an enum constant) is added, the switching class is not recompiled, and the two artefacts ship separately. Then the branch runs, and you get `java.lang.MatchException: null` in production with no indication of which value hit it and no cause chain. On JDK 17 the enum case threw `java.lang.IncompatibleClassChangeError: null` instead — measured — so the throwable also changed between LTS releases. Two takeaways. Recognising the shape on sight is the whole diagnostic value, because the exception itself tells you nothing. And it is the residual risk of omitting `default`: the compile error protects you when you rebuild, and this is what happens when you do not — a deployment error, correctly loud, unhelpfully silent about specifics.

</details>

**Q6.** Where does a record fit in the QuizStakes domain, and where does the same data need a class?

<details><summary>Answer</summary>

A record fits every value with a fixed component list and no identity — which in this domain is most of the type sketch: `Money`, `ClientId`, `ApplicationId`, `AccountId`, `PersonId`, `RoundId`, `IdempotencyKey`, `StatusCode`, `Jurisdiction`, `AgreementRef`, `LimitSet`, `StakeSplit`, `RestrictionKey`, and every arm of the sealed `Verdict` hierarchy. The test is whether two instances with the same components *are* the same thing: two `RestrictionKey(STAKE_BLOCKED, SYSTEM_ONBOARDING)` values are the same restriction identity — which is exactly what the domain specifies, since restriction identity is the (type, source) pair and not the type alone — so component-wise equality is the equality the domain means. The same data needs a class when it is an *entity*: `RestrictionEntity` has a primary key, and two rows with identical columns are different rows. Four independent reasons force a class there — JPA needs a no-arg constructor a record cannot have; dirty checking needs mutable fields, and reflective writes to `final` fields have been refused since Java 9; identity is the key, so `equals` must be key-based and stable across the transient-to-persistent transition; and lazy loading needs a proxy, which needs a non-final class. The middle ground is the **projection**: `RestrictionSummary(type, source, appliedAt)` as a record, populated by a JPQL constructor expression, which calls the canonical constructor in one go and therefore needs no no-arg constructor. So the same three columns appear three times in a healthy codebase — as a mutable entity, as a record projection, and as a record domain value — and that is not duplication, it is three different jobs.

</details>

---

## Open questions

- **Unverified:** whether the JVMS 21 class access-flag table genuinely has no sealed entry, as concept 2 asserts. The measurement is solid — `Verdict` compiled to `flags: (0x0600) ACC_INTERFACE, ACC_ABSTRACT` with a separate `PermittedSubclasses` attribute, so on this compiler no such flag is emitted. But "this compiler does not emit it" and "the specification defines no such flag" are different claims. What would settle it: JVMS 21 Table 4.1-B read directly. Nothing here depends on the difference — the attribute is what `Class.isSealed()` and `getPermittedSubclasses()` actually consult, which is measured, and it is what the verifier enforces at link time.
- **Unverified:** the claim in concept 1 that a record's generated `equals` inlines, after JIT compilation, to the same instruction sequence inline bytecode would have produced. It is the design intent of the method-handle infrastructure and holds for lambdas and indified concatenation, both measured elsewhere — but no compilation log or benchmark was taken for a record here. What would settle it: `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` on a hot loop comparing two records, or a JMH comparison against a hand-written `equals`. The load-bearing claims — one `invokedynamic` per method, one shared bootstrap entry, `REF_getField` handles rather than accessor calls, and a per-class linkage cost paid at first call — are all measured from the class file.
- **Unverified:** the startup-cost characterisation in concept 1 ("measurably so for an application with thousands of records whose `equals` runs once each"). The mechanism is measured — the bootstrap builds one handle composition per component per method — but no timing was taken, and whether it is measurable against the rest of a Spring Boot startup is precisely the kind of claim that needs a number. What would settle it: a JFR recording or an async-profiler wall-clock profile of a record-heavy application's startup, looking for `ObjectMethods.bootstrap` and `LambdaForm` frames. Stated as a plausible consequence rather than an observation.
- **Unverified:** which specific Jackson versions bind to records without `javac -parameters`. Concept 3 states that modern Jackson handles records natively via the `Record` attribute and that older versions need `-parameters` or `@JsonProperty`, which is the widely-reported behaviour, but no version boundary was checked and no binding was tested. What would settle it: the `jackson-databind` release notes for record support, plus a round-trip test with and without `-parameters` on the versions actually in use. The structural fact underneath it *is* verified: component names are always in the `Record` attribute, while constructor *parameter* names are only in the class file when `-parameters` was passed, and some tools read the latter.

---

**Leaves covered:** 1.19.4, 1.19.5, 1.19.6 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — §1.19 carries no diagram in the manifest
**Target version:** Java 21 LTS
**Lines:** 798
