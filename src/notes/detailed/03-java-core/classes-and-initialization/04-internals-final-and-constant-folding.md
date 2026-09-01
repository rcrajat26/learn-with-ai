# 03 Java Core — `final` semantics and constant folding — INTERNALS (§3.12, 3.12.1–3.12.11)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Class loaders, identity and startup cost](03b-internals-class-loaders-and-identity.md) · Next: [Inheritance, overriding and interfaces](../inheritance-and-dispatch/01-basics.md)

`final` is four unrelated mechanisms wearing one keyword. On a `static final` primitive or `String` it is a *binary compatibility* rule from JLS chapter 13 that erases the field from every caller's class file. On any `static final` it is a licence HotSpot actually exercises to fold the field's value into compiled code. On an instance field it is a memory-model *freeze action* at the constructor's exit, and nothing else — measurably not a constant-folding win. On a local or a parameter it is a `javac`-only constraint that leaves the `Code` attribute byte-identical. This file separates the four, proves each on a JDK 21.0.7 toolchain, and ends at JEP 500, which closes the one hole that is still open.

## 1. The `final` field freeze (3.12.4, 3.12.5)

Picture the constructor of `Money(BigDecimal amount, Currency currency)` as a small assembly line with a gate at the end. Inside the line, `amount` and `currency` get written. At the gate — the instant the constructor exits — a barrier drops that says: every write to a `final` field of this object is now on the far side of me, and nothing on the near side may be reordered across me. The gate is not a fence you write; it is a *freeze action*, part of the object's construction, and the whole point is that after the gate, the reference can be handed to another thread over a plain, unsynchronised, non-`volatile` write and that thread is still guaranteed to see `3.33` and `GBP`, never `null` and `null`.

### Why it exists

Before Java 5 there was no such guarantee. The original memory model was broken badly enough that the canonical "safe" idiom — publish a fully-built immutable object over a plain field — was formally unsound: a reader could see a non-null reference to an object whose `final` fields still held their default values, because nothing ordered the constructor's writes against the publishing write. The consequence in practice was that *every* cross-thread handoff needed `synchronized` or `volatile`, even for objects that never changed after construction. JSR-133 fixed it by giving `final` fields their own ordering rule, so that immutability alone — with no synchronisation on the handoff — became sufficient for safe reads of those fields. That is why `Money`, `StatusCode`, `ClientId` and every other QuizStakes value type can be flung across threads for free, and it is the single largest practical payoff of writing `final` on an instance field.

### The mechanism

`[SOURCE]` JLS 21 §17.5 defines the action and names it. Verbatim:

> Let *o* be an object, and *c* be a constructor for *o* in which a `final` field *f* is written. A *freeze* action on `final` field *f* of *o* takes place when *c* exits, **either normally or abruptly**.

Read every clause. "A constructor for *o* in which a `final` field *f* is written" — the freeze is per-field, and only fields actually written in that constructor are frozen by it. "When *c* exits" — the freeze is at the *exit*, not at the write, which is why a partially-constructed object has no protection at all. "Either normally or abruptly" — a constructor that throws `BonusIneligibleException` halfway through still freezes the fields it managed to write before the throw. That matters for exactly one situation: an object whose reference escaped before the throw, which is section 1's second half.

The guarantee itself, verbatim:

> A thread that can only see a reference to an object after that object has been completely initialized is guaranteed to see the correctly initialized values for that object's `final` fields.

And the usage rule the specification states as a recipe:

> Set the `final` fields for an object in that object's constructor; and do not write a reference to the object being constructed in a place where another thread can see it before the object's constructor is finished.
> If this is followed, then when the object is seen by another thread, that thread will always see the correctly constructed version of that object's `final` fields.

`[PROVE]` The derivation, which is what proves 3.12.4 — a benchmark cannot, because a benchmark can only fail to observe a violation, never establish that one is impossible. Three facts compose:

1. The freeze action on `amount` and on `currency` takes place when `Money`'s constructor exits (§17.5, quoted above).
2. The publishing write `grantedBonus = m` is in the *caller* of `new Money(amount, currency)`, and a constructor invocation completes before the expression containing it yields a value. So the publishing write is necessarily ordered after the constructor's exit in program order on the writing thread — there is no legal execution in which `bonus-grant-1` writes the reference before its own constructor call returns.
3. Therefore any thread that reads a non-null `grantedBonus` is reading a value written after the freeze. §17.5's guarantee applies to exactly that reader, and it applies with **no synchronisation on the publishing write** — `grantedBonus` may be a plain, non-`volatile`, non-`final` static field.

Now the half that is almost always misread. State exactly what the guarantee does **not** cover:

- **It says nothing about non-`final` fields of the same object.** A `Money` with one `final` field and one mutable field gives you the guarantee on the first and nothing whatever on the second, in the same read of the same reference.
- **It says nothing about *when* the reader sees the reference, or whether it ever does.** The guarantee is conditional: *if* you see the reference, *then* the `final` fields are correct. A plain publishing write may never become visible to the reader at all.

`[PROVE]` That second point is measurable, and it was measured. Two builds of the same probe on Oracle JDK 21.0.7, macOS aarch64, differing only in whether the static publishing field is `volatile`; the reader spins reading the field up to 100,000,000 times, then reports.

- Publishing field `static volatile Money grantedBonus`: the reader printed `balance-view-4 saw amount=3.33 currency=GBP`.
- Publishing field `static Money grantedBonus` (plain): the reader printed `balance-view-4 never saw the reference` on **all three** runs, having exhausted 100 million reads.

The plain-field reader never observed the reference — the JIT is entitled to hoist a non-`volatile` read out of the loop, and did. The `final`-field guarantee was never violated in either run; it simply had nothing to say, because the reader never got as far as holding the reference. `[X-REF 05]` The reference's own visibility is safe-publication territory — `volatile`, `final` static holder, `synchronized`, a concurrent collection, or `Thread.start`/`join` happens-before edges. One paragraph is all it gets here: guide **05 Concurrency** owns happens-before, the difference between `volatile` and final-field semantics, and why a plain write to the *holder* is a separate risk from the *contents* of what it holds.

`[TRAP]` The escape clause, 3.12.5. The guarantee's antecedent is "a thread that can only see a reference to an object **after** that object has been completely initialized." Publish `this` from inside the constructor and you have manufactured a thread that can see the reference *before*, so the antecedent is false and the conclusion is void — not weakened, void. There is no partial guarantee: the reader may observe `null` for `amount`, or `3.33`, on any given run, and no rule constrains which.

![D-122 — The `final` field freeze](../diagrams/D-122-final-field-freeze.svg)

**D-122** — Panel 1 is the honest publication: `bonus-grant-1` walks `new Money(amount, currency)` with all fields zeroed, writes `amount = 3.33`, writes `currency = GBP`, crosses the amber **FREEZE** bar at the constructor's end, and only then performs the plain write `grantedBonus = m`; the guarantee edge runs from the freeze bar into `balance-view-4`'s read, which reports `amount reads 3.33, currency reads GBP — GUARANTEED`. Panel 2 is the same line with `MoneyRegistry.register(this)` inserted before the field writes: the reference is already visible, so when the FREEZE bar arrives it is greyed out and labelled *freeze happens, but the reference was already visible*, and `balance-view-4` reports `amount reads 0.00 — the guarantee is void`. Note what the reader actually observes for a reference-typed field in the escaped case: the field's default, which for `BigDecimal amount` is `null`; the diagram renders it as the un-set amount `0.00` because that is what the field means before it is written.

The correct program, which is Panel 1 exactly:

```java
public class SafePublication {
    record Money(BigDecimal amount, Currency currency) { }

    static volatile Money grantedBonus;   // volatile for the REFERENCE's visibility, not for the fields

    public static void main(String[] args) throws InterruptedException {
        Thread reader = new Thread(() -> {
            Money seen = null;
            for (int i = 0; i < 100_000_000 && seen == null; i++) {
                seen = grantedBonus;
            }
            if (seen == null) {
                System.out.println("balance-view-4 never saw the reference");
                return;
            }
            System.out.println("balance-view-4 saw amount=" + seen.amount()
                    + " currency=" + seen.currency().getCurrencyCode());
        }, "balance-view-4");

        Thread writer = new Thread(() ->
                grantedBonus = new Money(new BigDecimal("3.33"), Currency.getInstance("GBP")),
                "bonus-grant-1");

        reader.start();
        writer.start();
        writer.join();
        reader.join();
    }
}
```

Measured output on JDK 21.0.7: `balance-view-4 saw amount=3.33 currency=GBP`. The `volatile` is doing exactly one job — making the *reference* arrive. Strip it and the reader prints `balance-view-4 never saw the reference`, as measured above. The fields themselves need no help: `Money`'s components are `final` (a record's components always are), the freeze orders them, and a reader that holds the reference reads `3.33` and `GBP`.

The broken program, which is Panel 2 exactly:

```java
public class EscapedThis {
    static final class MoneyRegistry {
        static Money published;
        static void register(Money m) { published = m; }
    }

    static final class Money {
        private final BigDecimal amount;
        private final Currency currency;

        Money(BigDecimal amount, Currency currency) {
            MoneyRegistry.register(this);   // this escapes BEFORE either final field is written
            this.amount = amount;
            this.currency = currency;
        }

        BigDecimal amount() { return amount; }
        Currency currency() { return currency; }
    }

    public static void main(String[] args) throws InterruptedException {
        Thread reader = new Thread(() -> {
            Money seen = null;
            for (int i = 0; i < 100_000_000 && seen == null; i++) {
                seen = MoneyRegistry.published;
            }
            System.out.println("balance-view-4 read the escaped reference, amount = "
                    + (seen == null ? "reference never arrived" : String.valueOf(seen.amount())));
        }, "balance-view-4");

        Thread writer = new Thread(() ->
                new Money(new BigDecimal("3.33"), Currency.getInstance("GBP")),
                "bonus-grant-1");

        reader.start();
        writer.start();
        writer.join();
        reader.join();
    }
}
```

**Unverified:** this program's *failing* outcome was not reproduced on this machine. The plain `MoneyRegistry.published` field has the same visibility problem measured above — across repeated runs the reader either exhausted its spin without seeing the reference or, on a single-threaded-scheduling interleaving, saw the fully-written object. A data race is not obliged to manifest, and "I could not make it fail" is not evidence that it cannot; the specification argument is the evidence, and it is decisive: with `this` escaping at line 1 of the constructor, the reader is a thread that can see the reference before initialization completes, so §17.5's antecedent is unsatisfied and `amount` may legally read `null`. Do not treat an unreproduced race as a safe one.

**Pitfall:** believing the freeze protects an object whose constructor leaked `this`.
*Wrong belief:* "the fields are `final`, so whoever gets the reference is safe." *Symptom:* an intermittent `NullPointerException` or a zero-valued `Money` in a listener, an observer registry, or anything the constructor registered itself with — reproducing on one machine and never on the developer's. *Fix:* never pass `this` out of a constructor. Build the object fully, return it, and let the *caller* register it: a static factory `Money.of(amount, currency)` that constructs and then calls `MoneyRegistry.register(m)` is the whole fix. `[X-REF 05]` `01c-class-anatomy-and-constructors.md` covers the same leak from the initialization-order angle (leaf 1.13.7) — a leaked `this` also exposes fields that a subclass constructor has not initialised yet, which is a distinct bug from this one and happens even single-threaded.

> A freeze action on a `final` field occurs when the constructor that wrote it exits, normally or abruptly, and guarantees that any thread which first sees the reference after that point sees the field's constructed value — a guarantee whose antecedent, and therefore whose entire force, is destroyed by publishing `this` from inside the constructor.

## 2. What the JIT trusts, and what it does not (3.12.6, 3.12.7)

Picture the JIT compiling `BonusService.grant`. It reaches a read of `BonusRules.MAX_BONUS_CAP`, a `static final int`. There is exactly one such field in the whole VM, its class is already initialized, and its value can never change — so the compiler stops treating it as a memory read and writes the number `100` directly into the machine code, then folds it into whatever arithmetic surrounds it. Now it reaches `bonus.cap()`, a read of an instance `final int`. There are 3,100 `Bonus` objects a day and this compiled method will serve all of them; the compiler does not know *which* one it will be handed, so it cannot know the value, so it emits a real load from memory. Same keyword, opposite outcome, and the difference is not about `final` at all — it is about whether the compiler knows the receiver.

### Why it exists

`static final` is the JVM's only source of genuine link-time constants for non-primitive-constant values. A `static final Logger`, a `static final BigDecimal`, a `static final int[]` lookup table — after `<clinit>` runs, these can never change, and folding them lets the compiler devirtualise calls through them, eliminate null checks on them, unroll loops bounded by them, and constant-fold entire expression trees. `@Stable` exists because the JDK's own internals needed the same treatment for fields that are written *once, lazily*, after construction — a cached `MethodHandle`, a lazily-computed table — which `static final` cannot express because a `static final` must be assigned in `<clinit>`.

### The mechanism

`[SOURCE]` `jdk.internal.vm.annotation.Stable`, from the JDK 21 source. Verbatim, the sentences that define the contract:

> A field may be annotated as stable if all of its component variables changes value at most once.

> Since all fields begin with a default value of null for references (resp., zero for primitives), it follows that this annotation indicates that the first non-null (resp., non-zero) value stored in the field will never be changed.

> The HotSpot VM relies on this annotation to promote a non-null (resp., non-zero) component value to a constant, thereby enabling superior optimizations of code depending on such a value (such as constant folding). More specifically, the HotSpot VM will process non-null stable fields (final or otherwise) **in a similar manner to static final fields** with respect to promoting the field's value to a constant.

> It is (currently) undefined what happens if a field annotated as stable is given a third value (by explicitly updating a stable field, a component of a stable array, or a final stable field via reflection or other means). Since the HotSpot VM promotes a non-null component value to constant, it may be that the Java memory model would appear to be broken, if such a constant (the second value of the field) is used as the value of the field even after the field value has changed (to a third value).

And the `@implNote`, verbatim, which is the part that keeps this out of application code entirely:

> This annotation only takes effect for fields of classes loaded by the boot loader. Annotations on fields of classes loaded outside of the boot loader are ignored.

Read those four quotes as one argument. "Changes value at most once" plus "all fields begin with a default value" gives the **two-value contract**: default, then one real value, forever. Violating it is *undefined behaviour*, not a deoptimisation — the third quote says the memory model "would appear to be broken," meaning compiled code may keep using value two after value three is written, with no exception and no diagnostic. And the `@implNote` means that even if you obtain the annotation via `--add-exports java.base/jdk.internal.vm.annotation=ALL-UNNAMED`, annotating your own `Bonus.cap` does nothing at all: your class is on the application loader, not the boot loader, so HotSpot ignores it. `@Stable` is a JDK-internal tool, and there is no supported way to opt an application class into it.

`[TRAP]` `[RESEARCH]` Now leaf 3.12.7, the interview question, measured. The argument from `@Stable`'s existence is already airtight and needs no benchmark: HotSpot would not need an annotation whose documented effect is to process a field "in a similar manner to static final fields" if plain instance `final` were already processed that way. But this one can be measured directly, so it was. The probe, on Oracle JDK 21.0.7, macOS aarch64: three fields — a `static final Integer`, a plain `static Integer`, and an instance `final int` — are read 2,000,000 times each through small static methods so the reads compile; then each field's value is changed *behind the compiler's back* (`sun.misc.Unsafe.putObject` at `staticFieldBase`/`staticFieldOffset` for the two statics, `Field.set` for the instance final, which JDK 21 permits — see section 4); then each is read once more through the same compiled method and once reflectively.

```
warmup sink = 600000000
static final  : compiled read = 100 | reflective get = 150
static (plain): compiled read = 150 | reflective get = 150
instance final: compiled read = 150 | reflective get = 150
```

Read the three lines. Line 1: the write landed — the reflective read reports `150` — and the compiled method still returns `100`. The compiler folded the `static final` read into the constant `Integer(100)` and never went to memory again. Line 2 is the control that proves the probe works at all: the same `Unsafe.putObject`, same warmup, same shape, but on a non-`final` static, and the compiled read reports `150`. So `Unsafe` genuinely mutated memory, and the difference in line 1 is folding, not a failed write. Line 3 is the leaf: the instance `final` field, mutated after 2,000,000 warmed-up reads, reports `150` from the compiled method. It was not folded. **This is HotSpot behaviour on one build, not a specification guarantee** — nothing in the JLS or JVMS obliges any JIT to fold or not fold anything — but the direction is not a coincidence, it is the reason `@Stable` was written.

The dependency worth naming: folding a `static final` requires the declaring class to be **initialized**, because before `<clinit>` runs the field's value is not yet knowable. `[X-REF]` `03-internals-class-loading-and-init.md` and `03a-internals-class-init-locking-and-failure.md` own the initialization state machine; the fact this section needs is only that "trusted" means "trusted once initialized."

**D-123** — `static final` is trusted; instance `final` is not.

| | Inlined into callers at compile time | Constant-folded by the JIT | Any bytecode difference | Mutable by reflection today (JDK 21) | Affected by JEP 500 |
|---|---|---|---|---|---|
| `static final` primitive / `String` **constant** | **Yes** — JLS §13.1 says the reference *must* be resolved at compile time; no `Fieldref` survives anywhere, including the declaring class | Moot — there is no runtime read left to fold; the value is already a literal in the caller's `Code` | **Yes** — a `ConstantValue` attribute on the field, `ACC_FINAL 0x0010` set, and `bipush`/`ldc` instead of `getstatic` at every use site | **No** — measured `IllegalAccessException: Can not set static final int field FinalMutation$BonusRules.MAX_BONUS_CAP to (int)150` | **No** — already non-modifiable per the `setAccessible` javadoc |
| `static final` **object reference** | **No** — not a constant variable, so a real `Fieldref` and `getstatic` remain | **Yes** — measured: after the field held `150`, the compiled read still returned `100` | **Yes** — `ACC_FINAL` on the field, value assigned in `<clinit>`, no `ConstantValue` attribute | **No** — measured `IllegalAccessException: Can not set static final java.lang.Integer field FinalMutation$BonusRules.BOXED_CAP to java.lang.Integer` | **No** — already non-modifiable |
| Instance `final` field | **Only if it is a non-`static` constant variable** (primitive or `String`, constant initializer), per §13.1's third paragraph; otherwise no | **Not unconditionally** — measured: after `Field.set` wrote `150`, the compiled read returned `150`. Folding needs a constant receiver (a `static final` holder, `@Stable`, or an escape-analysed local) | **Yes** — `ACC_FINAL` on the field, plus the JMM freeze action at every constructor's exit | **Yes** — measured success on an ordinary class's instance `final`; **rejected** for a record component: `IllegalAccessException: Can not set final java.math.BigDecimal field FinalMutation$Money.amount to java.math.BigDecimal` | **Yes** — this is the exact row JEP 500 targets |
| `@Stable` field | **No** | **Yes** — HotSpot "will process non-null stable fields (final or otherwise) in a similar manner to static final fields," but **only for boot-loader classes**; ignored everywhere else | **Yes** — a `RuntimeVisibleAnnotations` entry naming `jdk/internal/vm/annotation/Stable`; the annotation is `jdk.internal` and unusable without `--add-exports` | Depends on the field's own category: a `@Stable` non-`final` field is an ordinary mutable field; a `@Stable final` instance field follows the instance-`final` row. Either way, writing a third value is **undefined behaviour** | Insofar as the field is also a `final` instance field: **yes** |
| `final` local | Not a field, so §13.1's field rule does not apply — but a `final` local that is *also* a constant variable (`final int cap = 100;`) has its uses folded by the constant-expression rule | Moot — the JIT works on an SSA form in which a local's finality has no representation | **None** — two compilations differing only by `final` on the local produced **byte-identical** class files, SHA-256 `b26082b2…80b4ccbd` for both | Not applicable — no `Field` object exists for a local | **No** |
| `final` parameter | Not a field; no effect at any call site | Moot, same reason | **None in `Code`** — measured byte-identical `Code` and `LocalVariableTable`. The one trace: the optional `MethodParameters` attribute, emitted only under `javac -parameters`, records the flag — `stake  final` / `percent  final` | Not applicable | **No** |

**Insight:** the two rows that matter for a code review are rows 3 and 6. Row 3 says instance `final` buys you the freeze and a compile-time reassignment check, and does not buy you folding; row 6 says `final` on a parameter buys you a reassignment check and literally nothing else in the compiled method. Neither is a performance decision. `[X-REF 06]` Tiered compilation, escape analysis, `-XX:+PrintCompilation`, `-XX:+PrintInlining` and JMH belong to guide **06 JVM internals**; the mechanism paragraph above is all this file needs.

> HotSpot treats a `static final` field of an initialized class as a true constant and folds its value into compiled code; it does not do the same for an instance `final` field, because the value depends on a receiver the compiler generally does not know — so `final` on an instance field is a correctness and memory-model tool, not a performance one.

## 3. Constant folding into every caller, and the stale-constant hazard (3.12.1, 3.12.2, 3.12.3)

The picture: a `static final int MAX_BONUS_CAP = 100` in `BonusRules` is not a field that callers read. It is a *source-level instruction to `javac`* to stamp the literal `100` into every class file that mentions it, and then to leave no trace behind that anything could later relink. When you change the `100`, you have not changed a value — you have changed a stamp, and every class file already carrying the old stamp keeps it until it is recompiled.

### Why it exists

This is not a compiler optimisation. It lives in JLS **chapter 13, "Binary Compatibility"**, whose entire subject is which source changes preserve the ability of already-compiled binaries to link. The rule is there because the language needs constant expressions usable in places where nothing but a compile-time value will do: `case` labels, array dimensions in some contexts, annotation element values, and the definite-assignment and reachability analyses that let `if (DEBUG_LEDGER) { }` compile away a whole block. All of those require the value at compile time, so the specification requires the value to *be* at compile time.

### The mechanism

`[SOURCE]` The rule for what qualifies, JLS 21 §4.12.4, verbatim:

> A *constant variable* is a final variable of primitive type or type String that is initialized with a constant expression (§15.29). Whether a variable is a constant variable or not may have implications with respect to class initialization (§12.4.1), binary compatibility (§13.1), reachability (§14.22), and definite assignment (§16.1.1).

That second sentence is the hub of this entire note set — it enumerates all four consequences, and three of them are owned by three different files. Class initialization (§12.4.1): reading a constant variable does **not** trigger the declaring class's initialization, because there is no read — `01d-class-initialization-triggers.md`, leaf 1.13.10, diagram D-039. Binary compatibility (§13.1): this section. Definite assignment (§16.1.1) and blank finals: `01-basics.md`. Reachability (§14.22): the `if (CONSTANT_FALSE)` block that compiles away without an unreachable-code error — `../primitives-and-conversions/02-operators-and-expressions.md` owns constant expressions and §15.29 in full.

Note precisely what §4.12.4 does *not* say. It does not say `static`. An instance `final int` with a constant initializer is a constant variable too. And it does not say "any `final` field": a `static final BigDecimal`, a `static final Money`, a `static final int[]` — none of them are constant variables, because the type is not primitive or `String`. Two adjacent lines in `BonusRules` can therefore behave completely differently.

`[SOURCE]` `[BYTECODE]` Now JLS 21 §13.1, all three paragraphs, verbatim:

> A reference to a field that is a constant variable (§4.12.4) **must** be resolved at compile time to the value V denoted by the constant variable's initializer.
>
> If such a field is `static`, then **no reference to the field should be present in the code in a binary file, including the class or interface which declared the field.** Such a field must always appear to have been initialized (§12.4.2); the default initial value for the field (if different than V) must never be observed.
>
> If such a field is non-`static`, then no reference to the field should be present in the code in a binary file, except in the class containing the field. (It will be a class rather than an interface, since an interface has only `static` fields.) The class should have code to set the field's value to V during instance creation (§12.5).

Three clauses nobody covers, and they are this file's value over the BASICS treatment.

**"Must."** Not "may," not "is permitted to." A conforming compiler is *required* to resolve the reference at compile time. This closes the door on the most common wrong mental model — "a smarter linker could fix this at load time" — because there is nothing left in the caller's class file to fix. No `Fieldref`, no `getstatic`, no symbolic name. The information required to relink has been deleted, by specification.

**"Including the class or interface which declared the field."** Even the declaring class's own reads are inlined. `BonusRules.selfCheck()` returning `MAX_BONUS_CAP` compiles to a literal push, not a `getstatic` on its own field.

**The non-`static` paragraph**, which is where the compressed reproduction goes, because `02-modifiers.md` already owns the `static` case end to end. Compiled on Oracle JDK 21.0.7:

```java
final class BonusPolicy {
    final int couponValidityDays = 14;   // non-static constant variable
    final int expiryDays = 30;
    int ownRead() { return couponValidityDays; }
}

final class BonusPolicyReader {
    static int read(BonusPolicy policy) { return policy.couponValidityDays; }
}
```

`javap -v -p BonusPolicy.class`, the parts that matter:

```
  final int couponValidityDays;
    descriptor: I
    ConstantValue: int 14

  final int expiryDays;
    descriptor: I
    ConstantValue: int 30

  BonusPolicy();
    Code:
         0: aload_0
         1: invokespecial #1                  // Method java/lang/Object."<init>":()V
         4: aload_0
         5: bipush        14
         7: putfield      #7                  // Field couponValidityDays:I
        10: aload_0
        11: bipush        30
        13: putfield      #13                 // Field expiryDays:I
        16: return

  int ownRead();
    Code:
         0: bipush        14
         2: ireturn
```

Instruction by instruction. The `ConstantValue: int 14` attribute is present on a non-`static` field — a detail most descriptions of `ConstantValue` get wrong by claiming it only appears on statics. The constructor is §13.1's third paragraph made literal: "The class should have code to set the field's value to V during instance creation" — `aload_0`, `bipush 14`, `putfield #7`, and again for `expiryDays`. And `ownRead()` is `bipush 14; ireturn` — no `getfield` at all, because the declaring class's own read is inlined too, matching the `static` paragraph's "including the class which declared the field."

The caller, `javap -c -p BonusPolicyReader.class`:

```
  static int read(BonusPolicy);
    Code:
       0: aload_0
       1: invokestatic  #7                  // Method java/util/Objects.requireNonNull:(Ljava/lang/Object;)Ljava/lang/Object;
       4: pop
       5: bipush        14
       7: ireturn
```

This is the most instructive four instructions in the file. `aload_0` loads `policy`. `invokestatic Objects.requireNonNull` then `pop` — `javac` *keeps the null check*, because `policy.couponValidityDays` on a null `policy` must still throw `NullPointerException`; the field access has observable behaviour beyond its value, and only the value was folded. Then `bipush 14; ireturn`: the value arrives as a literal. And the confirmation — grepping the caller's full constant pool for `couponValidityDays` returns **0** matches. The caller's binary contains no reference to the field, exactly as §13.1's third paragraph requires.

`[TRAP]` `[PROVE]` Leaf 3.12.3, framed as what it actually is. Change `MAX_BONUS_CAP` from `100` to `150`, recompile `bonus-rules.jar`, deploy only that jar. Every class still links. No `NoSuchFieldError`, no `IncompatibleClassChangeError`, no exception anywhere, no log line — and `BonusService` still grants a cap of `100`. That is the category to name: **binary compatible and behaviourally incompatible**, with no diagnostic at any point. Chapter 13 is explicitly about the first property; it does not promise the second, and the two come apart exactly here. The full two-class reproduction — `BonusRules`/`BonusService`, the `ConstantValue: int 150` in the recompiled declaring class, the caller still printing `100`, the 40-entry constant pool with no `MAX_BONUS` in it, and the `Integer.valueOf(150)` fix that restores a real `Fieldref` — is worked end to end in `02-modifiers.md` (leaves 1.14.7 and 1.14.8, diagram D-042). Go there for the reproduction.

Why a build system hides it: a clean build recompiles both sides, so the caller's stamp is refreshed and the bug does not exist. An incremental build recompiles only what changed and what it believes depends on it — and dependency tracking that keys on *types referenced* rather than *constants inlined* will not mark `BonusService` dirty, because after inlining `BonusService` genuinely does not reference `BonusRules` at all. A per-jar or per-service deploy has the same shape at a coarser grain. The bug is therefore invisible in CI and appears only in the one environment where the two sides were built at different times.

The commercial size, from QuizStakes' own numbers: bonus grants run 3,100/day. A cap stale at `100` when policy says `150` under-grants at most 50 per grant, so the exposure ceiling is 3,100 × 50 = **155,000 per day** of promotional expense that policy intended and the ledger never posted — booked, silently, against `PROMOTIONAL_EXPENSE` at the wrong amount, with every `LedgerEntry` internally consistent and every reconciliation passing. That is what "no diagnostic" costs.

**Pitfall:** treating a `static final` constant as a runtime-readable configuration value.
*Wrong belief:* "it's a field, callers read it, so changing it changes behaviour." *Symptom:* the value changes in one module and not another after a partial deploy, and works perfectly after any clean rebuild — the classic unreproducible-on-my-machine bug. *Fix:* if a value must be changeable independently of its callers' compilation, make it not a constant variable. `static final Integer MAX_BONUS_CAP = 150;`, or a getter, or externalised configuration. `02-modifiers.md` proves the `Integer.valueOf` form drops the `ConstantValue` attribute and restores a real `Fieldref` and `getstatic`.

> A constant variable is a `final` variable of primitive or `String` type with a constant-expression initializer, and JLS §13.1 *requires* every reference to it — including inside its own declaring class — to be resolved to a literal at compile time, which makes changing its value binary-compatible and behaviourally incompatible at the same time, with no runtime diagnostic of any kind.

## 4. Mutating a `final` field, and the closing window (3.12.8, 3.12.9, 3.12.10)

The picture: `final` has never been enforced by the JVM the way `private` is. There are two distinct checks — `javac` refuses to compile a second assignment, and `Field.set` refuses at runtime for *some* categories of field — and for the largest category, an ordinary class's instance `final` field, the runtime check simply does not exist on JDK 21. Deep reflection walks straight through. That hole is the reason Hibernate can hydrate an immutable entity, Jackson can deserialize a class with no setters, and a mocking framework can replace a `final` collaborator field; and it is the hole JEP 500 closes.

### Why it exists

Serialization is the honest case. `ObjectInputStream` reconstructs an object without running its constructor — it allocates, then writes each field from the stream — so if `IdempotencyKey.value` is `final`, there is no legal path to set it. Either `final` fields are reflectively writable or `Serializable` cannot round-trip an immutable class. `readObject` faces the same wall for the same reason. `[X-REF]` `../serialization/02-serialization.md` owns why `readObject` must write finals and what `serialPersistentFields` does about it. The same shape recurs in ORM entity hydration, dependency injection into `final` fields, and any framework that constructs objects it did not design.

### The mechanism

`[SOURCE]` The ground truth for JDK 21 is the `Field.setAccessible` javadoc, verbatim:

> This method cannot be used to enable write access to a non-modifiable final field. The following fields are non-modifiable:
> - `static final` fields declared in any class or interface
> - `final` fields declared in a hidden class
> - `final` fields declared in a record
>
> The accessible flag when `true` suppresses Java language access control checks to only enable read access to these non-modifiable final fields.

Three categories, and the last sentence is precise: for these, `setAccessible(true)` still buys you *reads*, just not writes. `[X-REF]` Hidden classes — classes created by `Lookup.defineHiddenClass`, unnamed in the loader's namespace, not discoverable by `Class.forName` — are `03b-internals-class-loaders-and-identity.md`'s territory; they appear here only as the third non-modifiable category. Records are guide **04 Modern Java**, `[X-REF 04]`: the canonical constructor is the only way in, by design.

`[RESEARCH]` Measured on Oracle JDK 21.0.7, macOS aarch64 — one program, six attempts, output verbatim:

```
java.version = 21.0.7
static final int BonusRules.MAX_BONUS_CAP -> java.lang.IllegalAccessException: Can not set static final int field FinalMutation$BonusRules.MAX_BONUS_CAP to (int)150
static final Integer BonusRules.BOXED_CAP -> java.lang.IllegalAccessException: Can not set static final java.lang.Integer field FinalMutation$BonusRules.BOXED_CAP to java.lang.Integer
record component Money.amount -> java.lang.IllegalAccessException: Can not set final java.math.BigDecimal field FinalMutation$Money.amount to java.math.BigDecimal
   Money after attempt = Money[amount=3.33, currency=GBP]
instance final IdempotencyKey.value -> SUCCEEDED
   IdempotencyKey.value now = dep-2f7a-9999
Field.class.getDeclaredField("modifiers") -> java.lang.NoSuchFieldException: modifiers
```

Line by line. The two `static final` attempts fail regardless of whether the field is a constant variable — the boxed `Integer` is not, and is still rejected. The record component fails, and `Money` still prints `Money[amount=3.33, currency=GBP]`, unchanged. `IdempotencyKey.value` — an ordinary class's `private final String`, exactly the shape of every QuizStakes value type not written as a record — **succeeded**, and the object now reports `dep-2f7a-9999`. An idempotency key that can be reflectively rewritten is not a safety property you can rely on for deduplicating a `PaymentIntent`. And the historical route is closed: `Field.class.getDeclaredField("modifiers")`, the "clear the `ACC_FINAL` bit reflectively" trick that every pre-2019 answer recommends, throws `NoSuchFieldException` because core reflection filters that field. Measured across toolchains on this machine: the field is **found** on JDK 11.0.27 (`private int java.lang.reflect.Field.modifiers`) and **absent** on 17.0.15 and 21.0.7. **Unverified:** the boundary is widely reported to be JDK 12, via `Reflection.filterFields`, which is consistent with these measurements, but 12 through 16 were not available here to test directly.

`[VERSION-TRAP]` The leaf claims this "no longer works for records, hidden classes, and `java.lang` value-based classes." The first two are confirmed above. **The third is wrong on JDK 21**, and the measurement is unambiguous:

```
java.lang value-based: Integer.value -> java.lang.reflect.InaccessibleObjectException: Unable to make field private final int java.lang.Integer.value accessible: module java.base does not "opens java.lang" to unnamed module @214c265e
```

That is a **module** rejection, not a `final` rejection — strong encapsulation, JEP 403, not a non-modifiable-field check. Supply `--add-opens java.base/java.lang=ALL-UNNAMED` and the same call succeeds. The follow-up probe, verbatim, and it is worth reading twice:

```
Integer.valueOf(100) now prints  : 150
cap.intValue()                   : 150
100 + Integer.valueOf(100)       : 250
```

`Integer.valueOf(100)` returns a cached instance shared process-wide, so mutating its `value` field corrupts the box for every holder of the number 100 in the JVM. `java.util.Optional`'s `value` field mutated the same way under `--add-opens java.base/java.util=ALL-UNNAMED`. So on JDK 21, value-based classes' `final` fields are protected by module encapsulation and by nothing else; the leaf's "no longer works" is stale, and this is precisely the gap JEP 500 exists to close.

`[RESEARCH]` `VarHandle` deserves its own line, because it is often listed alongside reflection as an equivalent route and it is not. Measured on 21.0.7: `Lookup.findStaticVarHandle` on a `static final int`, `Lookup.findVarHandle` on an instance `final int`, and `Lookup.unreflectVarHandle` on a `setAccessible(true)` instance `final` `Field` **all** threw `UnsupportedOperationException` on the `set` call. `VarHandle` will not write a `final` field of any category on JDK 21. `Field.set` is the only supported route, and `sun.misc.Unsafe.putObject`/`putInt` at a computed offset is the unsupported one — which does write, including to a `static final`, as section 2's probe used; but the compiled code may keep the folded old value, so the write is not even reliably observable.

`[VERSION-TRAP]` **JEP 500, and the leaf's flag name is wrong.** The JEP is **"Prepare to Make Final Mean Final"** by Ron Pressler and Alex Buckley, issue 8349536, and its status is **Closed / Delivered, Release: 26** — not "proposes," as the leaf says; it shipped. Its summary, verbatim: "Issue warnings about uses of deep reflection to mutate final fields. These warnings aim to prepare developers for a future release that ensures integrity by default by restricting final field mutation, which will make Java programs safer and potentially faster. Application developers can avoid both current warnings and future restrictions by selectively enabling the ability to mutate final fields where essential."

The leaf names the transition switch `--illegal-final-field-access`. **There is no such flag.** The actual option is **`--illegal-final-field-mutation`**, and `java --illegal-final-field-mutation=warn -version` on JDK 21.0.7 reports `Unrecognized option`, confirming nothing about JEP 500 is active on the target version. Its four values, verbatim from the JEP:

| Value | Behaviour | Default in |
|---|---|---|
| `allow` | Allows the mutation to proceed without warning | — (will be **removed** when `deny` becomes default) |
| `warn` | Allows the mutation but issues a warning the first time that code in a particular module performs an illegal final field mutation. At most one warning per module | **JDK 26** — "will be phased out in a future release and, eventually, removed" |
| `debug` | Identical to `warn` except both a warning message and a stack trace are issued for **every** illegal mutation | — |
| `deny` | `Field::set` throws `IllegalAccessException` for every illegal final field mutation | **A future release** |

The warning text, quoted from the JEP with its placeholder class and module names replaced by QuizStakes ones — the three lines and their wording are the JEP's:

```
WARNING: Final field value in com.quizstakes.payments.IdempotencyKey has been mutated by class com.quizstakes.hydration.EntityFiller.fill in module entity.hydration (file:/opt/quizstakes/lib/entity-hydration.jar)
WARNING: Use --enable-final-field-mutation=entity.hydration to avoid a warning
WARNING: Mutating final fields will be blocked in a future release unless final field mutation is enabled
```

The JEP's first line uses the alternation `[mutated/unreflected for mutation]`, meaning the same warning covers both a direct `Field::set` and obtaining a writable handle for later use.

The opt-in side is **`--enable-final-field-mutation`**, and it may be supplied on the command line, indirectly via `JDK_JAVA_OPTIONS`, in an `@argfile`, through an executable JAR manifest entry **`Enable-Final-Field-Mutation`** whose only supported value is **`ALL-UNNAMED`** (any other value causes an exception), or passed to `jlink` via `--add-options`. Two constraints from the JEP, verbatim: "It is illegal for code to mutate a final field via deep reflection if either the code is in a module for which final field mutation is not enabled, or the code is in a module to which the field's package is not open" — note the conjunction of *two* independent gates, module opt-in **and** `opens` — and "The `--enable-final-field-mutation` option can refer to modules in the boot module layer only. It is not possible to enable final field mutation for code in user-defined layers," which rules the escape hatch out for anything running in a dynamically-constructed layer.

`[RESEARCH]` `[X-REF 16]` Leaf 3.12.10 — the consequence for libraries. The JEP's own framing, verbatim: "Code that mutates final fields via deep reflection is usually library code, not application code." The categories it points at, and what migrating each looks like:

| Category | Why it mutates finals | What the migration looks like |
|---|---|---|
| Deep-reflection mocking / test doubles | Replacing a `final` collaborator field on an already-constructed object under test | Constructor injection so the double is passed in; or an interface seam and a real subclass; or a bytecode-instrumenting agent that never touches `Field.set` |
| ORM / entity hydration | Building an entity from a `ResultSet` without a matching constructor | A canonical or all-args constructor the mapper can call; or `MethodHandles.Lookup` obtained via a proper `opens` and used for construction rather than field writes |
| Dependency injection | Injecting into a `final` field annotated for injection | Constructor injection — already the recommended form in Spring Boot 3.x and the only one that keeps the field genuinely `final` |
| Serialization / deserialization | Reconstructing an object without running a constructor | Records with a canonical constructor; or a builder; or a creator method the framework is told to call |

**Verify before naming a version.** Specific library versions that mutate `final` fields were not confirmed against those projects' sources here, so this file names categories rather than versions. **Unverified:** the syllabus leaf's parenthetical "older Mockito, some ORM and DI tooling" is plausible and matches the categories the JEP itself calls out, but no specific Mockito, Hibernate or Spring version was checked. `[X-REF 16]` Guide **16 Testing** owns mocking frameworks, test doubles, and why deep reflection is in the test path at all.

What to do on JDK 21, today, in order: run the test suite and an integration boot under **`--illegal-final-field-mutation=deny`** on a JDK 26 build to enumerate every offender — the JEP's own recommendation, verbatim: "To prepare for the future, we recommend running existing code with the `deny` mode to identify code that mutates final fields via deep reflection." Then migrate each hit to constructor injection or a canonical constructor. Reach for `--enable-final-field-mutation` only where a third-party library gives you no alternative, and treat it as a dated exemption, not a setting. Note also that the `Unsafe` fallback is not a durable escape: `sun.misc.Unsafe`'s memory-access methods are being removed on their own schedule, independent of JEP 500.

> On JDK 21, `Field.set` cannot write a `static final` field, a record component, or a `final` field of a hidden class, but *can* write an ordinary class's instance `final` field with no warning; JEP 500, delivered in JDK 26, adds a per-module warning under `--illegal-final-field-mutation=warn` and will later make `deny` the default, with `--enable-final-field-mutation` as the narrow, module-scoped opt-in.

## Supporting facts

### `final` on a local or a parameter: no bytecode difference at all (3.12.11)

`[PROVE]` `[BYTECODE]` Two source files, same class name `MoneyMath`, same method, compiled into separate output directories on Oracle JDK 21.0.7. They differ only in three `final` keywords:

```java
final class MoneyMath {
    static BigDecimal bonusPortion(BigDecimal stake, int percent) {
        BigDecimal rate = BigDecimal.valueOf(percent).movePointLeft(2);
        return stake.multiply(rate).setScale(2, RoundingMode.DOWN);
    }
}
```

```java
final class MoneyMath {
    static BigDecimal bonusPortion(final BigDecimal stake, final int percent) {
        final BigDecimal rate = BigDecimal.valueOf(percent).movePointLeft(2);
        return stake.multiply(rate).setScale(2, RoundingMode.DOWN);
    }
}
```

Plain `javac`, no flags. Both class files hash to **`b26082b22829a1295b411f6e43e51a2c1a7cf47b5e6bb9804b096c4480b4ccbd`**, and `cmp` reports them byte-identical — not merely equivalent bytecode, the same bytes. The `Code` attribute, from `javap -c -p`:

```
  static java.math.BigDecimal bonusPortion(java.math.BigDecimal, int);
    Code:
       0: iload_1
       1: i2l
       2: invokestatic  #7                  // Method java/math/BigDecimal.valueOf:(J)Ljava/math/BigDecimal;
       5: iconst_2
       6: invokevirtual #13                 // Method java/math/BigDecimal.movePointLeft:(I)Ljava/math/BigDecimal;
       9: astore_2
      10: aload_0
      11: aload_2
      12: invokevirtual #17                 // Method java/math/BigDecimal.multiply:(Ljava/math/BigDecimal;)Ljava/math/BigDecimal;
      15: iconst_2
      16: getstatic     #21                 // Field java/math/RoundingMode.DOWN:Ljava/math/RoundingMode;
      19: invokevirtual #27                 // Method java/math/BigDecimal.setScale:(ILjava/math/RoundingMode;)Ljava/math/BigDecimal;
      22: areturn
```

The reason: there is no `final` flag for a local variable anywhere in the class file format. `LocalVariableTable` records a start PC, a length, a name index, a descriptor index and a slot — no access flags at all — so finality has nowhere to be recorded. `final` on a local or a parameter is a source-level constraint checked by `javac` and discarded. `[X-REF]` `../language-substrate/03a-internals-class-file-format.md` owns the attribute layouts.

Two qualifications. First, a `final` local that is *also* a constant variable — `final int couponValidityDays = 14;` — does have its uses folded to `bipush 14`, but that is §4.12.4 and the constant-expression rule doing the work, not `final`-on-a-local: an effectively-final non-`final` local with the same initializer folds identically. Second, the one place the keyword can leave a trace, verified: under `javac -g -parameters` the two class files **do** differ, and `javap -v` shows why —

```
    MethodParameters:
      Name                           Flags
      stake                          final
      percent                        final
```

versus the non-`final` compilation, which emits the same attribute with the `Flags` column empty. The `MethodParameters` attribute (JVMS 21 §4.7.24) carries an `access_flags` field per parameter, and `ACC_FINAL 0x0010` is one of the flags it can set. The `Code` attribute and the `LocalVariableTable` were still byte-identical between the two `-g -parameters` compilations; only `MethodParameters` differed. So the honest statement is: `final` on a parameter has no effect on any executed instruction, and is observable in the class file only when `-parameters` is on — which is unusual outside projects that rely on runtime parameter names for Jackson or Spring binding. `[X-REF]` The `final`-versus-effectively-final capture rule for lambdas and inner classes is `01a-names-scope-and-var.md`'s.

## Pitfalls

### Marking every instance field `final` for performance

**Wrong**

```java
final class Bonus {
    private final int cap;                    // "final = the JIT folds it = faster"
    Bonus(int cap) { this.cap = cap; }
    int cap() { return cap; }
}
```

The surprise, measured on JDK 21.0.7: after 2,000,000 warmed-up reads through a compiled method, the field was changed reflectively and the compiled method immediately reported the new value.

```
static final  : compiled read = 100 | reflective get = 150
static (plain): compiled read = 150 | reflective get = 150
instance final: compiled read = 150 | reflective get = 150
```

The `static final` read was folded — it kept returning `100` after memory held `150`. The instance `final` read was not folded; it returned `150`, indistinguishable from the non-`final` static control.

**Right**

```java
final class BonusRules {
    static final int MAX_BONUS_CAP = 100;             // constant variable: inlined at compile time
    static final BigDecimal STAKE_BONUS_RATE =        // static final reference: folded by the JIT
            new BigDecimal("0.10");
}

final class Bonus {
    private final int cap;                            // final for the FREEZE and the reassignment check
    Bonus(int cap) { this.cap = cap; }
    int cap() { return cap; }
}
```

Write `final` on an instance field for the two things it actually delivers: the JMM freeze action, which makes the object safely readable across threads without synchronising the read, and a compile-time guarantee that no maintainer reassigns it. Put the value in a `static final` if you want it folded.

**Why people believe it:** `static final` folding is real and well documented, and "final" reads as one keyword with one meaning. The existence of `@Stable` — whose documented job is to process a field "in a similar manner to static final fields" — is the tell that instance `final` alone does not get that treatment; if it did, the annotation would be unnecessary.

### Registering `this` in a constructor and relying on the final-field guarantee

**Wrong**

```java
static final class Money {
    private final BigDecimal amount;
    private final Currency currency;

    Money(BigDecimal amount, Currency currency) {
        MoneyRegistry.register(this);   // reference visible before either final write
        this.amount = amount;
        this.currency = currency;
    }
    BigDecimal amount() { return amount; }
}
```

The surprise: `balance-view-4` can read `amount` as `null` from a reference obtained through `MoneyRegistry`. §17.5's guarantee is stated for "a thread that can only see a reference to an object **after** that object has been completely initialized"; a constructor that publishes `this` creates a thread that can see it before, so the antecedent is false and there is no guarantee at all — not a weaker one. The freeze still happens at the constructor's exit, but by then the reference is already out.

**Right**

```java
static final class Money {
    private final BigDecimal amount;
    private final Currency currency;

    private Money(BigDecimal amount, Currency currency) {
        this.amount = amount;
        this.currency = currency;
    }

    static Money of(BigDecimal amount, Currency currency) {
        Money m = new Money(amount, currency);   // fully constructed; freeze has happened
        MoneyRegistry.register(m);               // published after the freeze
        return m;
    }
    BigDecimal amount() { return amount; }
}
```

The registration moved out of the constructor into a static factory, so the publishing write is provably ordered after the constructor's exit and §17.5 applies.

**Why people believe it:** the fields are `final`, the constructor does assign them, and every assignment finishes before the constructor returns — so it *feels* ordered. The rule is keyed on the constructor's exit, not on the assignments, and `this` escaping earlier is the one thing that defeats it.

### Assuming reflection can always mutate a `final` field

**Wrong**

```java
Field f = BonusRules.class.getDeclaredField("MAX_BONUS_CAP");   // static final int
f.setAccessible(true);
f.setInt(null, 150);
```

The surprise, measured on JDK 21.0.7: `java.lang.IllegalAccessException: Can not set static final int field BonusRules.MAX_BONUS_CAP to (int)150`. The `setAccessible` javadoc names three non-modifiable categories — `static final` in any class or interface, `final` in a hidden class, `final` in a record — and for those, `setAccessible(true)` enables read access only. A record component was rejected the same way, and `Money[amount=3.33, currency=GBP]` printed unchanged afterwards. The old workaround is gone too: `Field.class.getDeclaredField("modifiers")` throws `NoSuchFieldException` on 17 and 21 (it still resolved on 11).

**Right**

```java
// Records are constructed, never patched. The canonical constructor is the only way in.
record Money(BigDecimal amount, Currency currency) { }

Money adjusted = new Money(new BigDecimal("999.99"), original.currency());
```

**Why people believe it:** the one category that *is* still writable on JDK 21 — an ordinary class's instance `final` field — is also the most common shape in real code, so the trick appears to work until it is tried on a `static final` or a record. Measured: `IdempotencyKey.value`, a `private final String` in an ordinary class, was rewritten from `dep-2f7a-0001` to `dep-2f7a-9999` with no error and no warning.

### Assuming `--illegal-final-field-access` is a real flag

**Wrong**

```
java --illegal-final-field-access=deny -cp app.jar com.quizstakes.Bootstrap
```

The surprise: there is no such option. The flag JEP 500 defines is **`--illegal-final-field-mutation`**, and on JDK 21.0.7 even the correct spelling is rejected — `java --illegal-final-field-mutation=warn -version` prints `Unrecognized option: --illegal-final-field-mutation=warn` and fails to start the VM, because JEP 500 is Closed / Delivered for **Release 26**, not 21. Nothing about its warnings or restrictions is active on the target version.

**Right**

```
# On a JDK 26 build, enumerate every offender before they become errors:
java --illegal-final-field-mutation=deny -cp app.jar com.quizstakes.Bootstrap

# And, only where a third-party library leaves no alternative, opt that module in:
java --enable-final-field-mutation=com.some.library -cp app.jar com.quizstakes.Bootstrap
```

**Why people believe it:** the JDK has a family of similarly-shaped flags — `--illegal-access` (JDK 9–16), and the `--add-opens`/`--add-exports` pair — and the name is easy to reconstruct wrongly by analogy. Get the verb right: the flag governs *mutation*, not *access*.

## Cheat sheet

| Item | Value |
|---|---|
| Constant variable (JLS §4.12.4) | A `final` variable of primitive type or `String`, initialized with a constant expression (§15.29) |
| §4.12.4's four named consequences | Class initialization §12.4.1 · binary compatibility §13.1 · reachability §14.22 · definite assignment §16.1.1 |
| Blank final | "A final variable whose declaration lacks an initializer" |
| Implicitly `final` (§4.12.4) | An interface field · a try-with-resources resource variable · a multi-catch exception parameter |
| §13.1 core rule | A reference to a constant variable **must** be resolved at compile time to the value V |
| §13.1, `static` case | "No reference to the field should be present in the code in a binary file, **including the class or interface which declared the field**" |
| §13.1, non-`static` case | No reference in any binary except the declaring class, which "should have code to set the field's value to V during instance creation" |
| Measured, non-`static` constant variable | `ConstantValue: int 14` on the field · `bipush 14; putfield` in `<init>` · `ownRead()` is `bipush 14; ireturn` · caller emits `requireNonNull; pop; bipush 14` and has **0** pool references to the field |
| Stale-constant category | Binary compatible **and** behaviourally incompatible — links fine, behaves wrong, no diagnostic |
| Why builds hide it | A clean build recompiles both sides; an incremental build or per-jar deploy does not |
| Freeze action (JLS §17.5) | Takes place when the constructor that wrote the `final` field exits, **either normally or abruptly** |
| The guarantee | "A thread that can only see a reference to an object after that object has been completely initialized is guaranteed to see the correctly initialized values for that object's `final` fields" |
| What it does **not** cover | Non-`final` fields of the same object · *whether or when* the reader sees the reference at all |
| Measured: plain vs `volatile` publish | `volatile`: reader printed `amount=3.33 currency=GBP`. Plain: `never saw the reference` on 3/3 runs after 100,000,000 spins |
| Escape clause | Publishing `this` from the constructor falsifies the guarantee's antecedent — the guarantee is void, not weakened |
| JIT trust, measured (JDK 21.0.7) | `static final` compiled read `100` while memory held `150` (folded) · plain `static` read `150` · instance `final` read `150` (not folded) |
| `@Stable` contract | Default value, then one non-default value, forever; a third value is **undefined behaviour** |
| `@Stable` effect | HotSpot processes non-null stable fields "in a similar manner to static final fields"; `@implNote` — **boot-loader classes only**, ignored elsewhere |
| Non-modifiable finals on JDK 21 | `static final` in any class or interface · `final` in a hidden class · `final` in a record |
| Still modifiable on JDK 21 | An ordinary class's instance `final` field — measured: `IdempotencyKey.value` rewritten, no error, no warning |
| `java.lang` value-based classes on 21 | Protected by **module encapsulation only** — `Integer.value` mutated successfully under `--add-opens java.base/java.lang=ALL-UNNAMED`, after which `Integer.valueOf(100)` printed `150` |
| `Field.modifiers` trick | `NoSuchFieldException` on 17 and 21; the field still resolved on 11. Reported blocked in JDK 12 via `Reflection.filterFields` |
| `VarHandle` on a `final` field | `UnsupportedOperationException` on `set` for `findStaticVarHandle`, `findVarHandle` and `unreflectVarHandle` alike, JDK 21 |
| JEP 500 | "Prepare to Make Final Mean Final", Pressler & Buckley, issue 8349536, **Closed / Delivered, Release 26** |
| `--illegal-final-field-mutation` values | `allow` (removed when `deny` lands) · `warn` (**default in JDK 26**, one warning per module) · `debug` (warn + stack trace, every mutation) · `deny` (`Field::set` throws `IllegalAccessException`; **future default**) |
| On JDK 21 | `--illegal-final-field-mutation=warn` → `Unrecognized option`; nothing about JEP 500 is active |
| Opt-in | `--enable-final-field-mutation`, or `JDK_JAVA_OPTIONS`, or an `@argfile`, or manifest `Enable-Final-Field-Mutation: ALL-UNNAMED`, or `jlink --add-options`. Boot module layer only |
| Two gates | Mutation is illegal if the module is not enabled **or** the field's package is not `opens`-ed to it |
| `final` local / parameter | **No bytecode difference** — both class files hashed `b26082b2…80b4ccbd`, `cmp` byte-identical |
| The one caveat | Under `javac -parameters`, `MethodParameters` (JVMS §4.7.24) records the flag: `stake  final` / `percent  final`. `Code` and `LocalVariableTable` still identical |

## Self-test

**Q1.** A reader thread holds a reference to a `Money` record published through a plain, non-`volatile` static field. Which of its fields is it guaranteed to read correctly, and what is it not guaranteed at all?

<details><summary>Answer</summary>

It is guaranteed to read the correctly constructed values of every `final` field — for a record, that is every component, so both `amount` and `currency`. The guarantee comes from JLS §17.5's freeze action, which takes place when the constructor exits; because the publishing write is in the caller of `new Money(amount, currency)`, it is necessarily ordered after that exit, so any thread reading a non-null reference is reading a value written after the freeze. No synchronisation on the publishing write is needed for this.

Two things are not guaranteed. First, nothing about non-`final` fields of the same object — if `Money` had a mutable field, reading it through the same reference in the same instant carries no ordering guarantee whatever. Second, and more commonly missed, nothing about *whether or when* the reader sees the reference at all. The guarantee is conditional: if you see the reference, then the finals are correct. Measured on JDK 21.0.7, a reader spinning on a plain non-`volatile` static field 100,000,000 times printed "never saw the reference" on all three runs, while the identical probe with the field marked `volatile` printed `amount=3.33 currency=GBP` immediately. The reference's own visibility is a separate problem requiring separate machinery.

</details>

**Q2.** Why does `final` on an instance field not make reads of it faster, and what is the strongest evidence for that without running a benchmark?

<details><summary>Answer</summary>

Because folding a field read into a constant requires the compiler to know the field's *value* at compile time, and the value of an instance field depends on the receiver. A method compiled once serves every instance, so the compiler generally does not know which object it will be handed and must emit a real memory load. Folding an instance final needs a constant receiver — a `static final` holder, `@Stable`, or an escape-analysed local whose construction the compiler can see inline.

The evidence that needs no benchmark is the existence of `jdk.internal.vm.annotation.Stable`. Its documentation says HotSpot "will process non-null stable fields (final or otherwise) in a similar manner to static final fields with respect to promoting the field's value to a constant." If plain instance `final` were already processed that way, the annotation would carry no information and would not exist. It was measured anyway on JDK 21.0.7: after 2,000,000 warmed-up reads, a `static final Integer` kept returning the folded old value `100` even after memory held `150`, while the instance `final int` returned the new value `150` immediately — the same as a non-`final` static control. What `final` on an instance field does buy is the JMM freeze action and a compile-time reassignment check, both of which are correctness properties.

</details>

**Q3.** You bumped `static final int MAX_BONUS_CAP` from 100 to 150, rebuilt and deployed only the jar that declares it, and the service still grants 100. Nothing threw. Explain the mechanism and name the compatibility category.

<details><summary>Answer</summary>

`MAX_BONUS_CAP` is a constant variable under JLS §4.12.4 — `final`, primitive type, constant-expression initializer. JLS §13.1 then says a reference to such a field **must** be resolved at compile time to the value, and if the field is `static`, "no reference to the field should be present in the code in a binary file, including the class or interface which declared the field." So the calling class's compiled bytecode contains the literal `100` and no `Fieldref` and no `getstatic` naming the field at all. There is nothing left to relink. Recompiling only the declaring jar updates its `ConstantValue` attribute to `int 150`, which the caller never reads, because the caller never reads the field.

The category is **binary compatible and behaviourally incompatible**: every class still links, there is no `NoSuchFieldError` or `IncompatibleClassChangeError`, no exception, no log line, and the behaviour is wrong. JLS chapter 13 is explicitly about the first property only; the two come apart precisely here. A clean build recompiles both sides and the bug vanishes, which is why CI never sees it — an incremental build whose dependency tracking keys on referenced types will not mark the caller dirty, because after inlining the caller genuinely does not reference the declaring class. The fix is to stop it being a constant variable: `static final Integer MAX_BONUS_CAP = 150;` drops the `ConstantValue` attribute and restores a real `Fieldref` and `getstatic` at every use site.

</details>

**Q4.** Which `final` fields can deep reflection still mutate on JDK 21, and which cannot?

<details><summary>Answer</summary>

The `Field.setAccessible` javadoc names exactly three non-modifiable categories: `static final` fields declared in any class or interface, `final` fields declared in a hidden class, and `final` fields declared in a record. For these, `setAccessible(true)` suppresses access control for *read* access only. Everything else — in practice, an ordinary class's instance `final` field — is freely writable with no warning.

Measured on Oracle JDK 21.0.7: `static final int` gave `IllegalAccessException: Can not set static final int field FinalMutation$BonusRules.MAX_BONUS_CAP to (int)150`; `static final Integer` (not a constant variable, so the rejection is not about constant folding) gave the same; a record component gave `IllegalAccessException: Can not set final java.math.BigDecimal field FinalMutation$Money.amount to java.math.BigDecimal` and the record still printed `Money[amount=3.33, currency=GBP]`; and `IdempotencyKey.value`, a `private final String` in an ordinary final class, was rewritten from `dep-2f7a-0001` to `dep-2f7a-9999` and **succeeded**. Two side notes: the old `Field.class.getDeclaredField("modifiers")` workaround throws `NoSuchFieldException` on 17 and 21 (it still resolved on 11), and `VarHandle` refuses outright — `findVarHandle`, `findStaticVarHandle` and `unreflectVarHandle` all threw `UnsupportedOperationException` on `set` for a `final` field.

</details>

**Q5.** Does `final` on a method parameter change anything in the compiled class file? Answer precisely.

<details><summary>Answer</summary>

Not in anything that executes. Two compilations of the same class differing only in `final` on a parameter and a local produced byte-identical class files under plain `javac` — both hashed to `b26082b22829a1295b411f6e43e51a2c1a7cf47b5e6bb9804b096c4480b4ccbd`, and `cmp` reported no difference. There is no `final` flag for a local variable in the class file format at all; `LocalVariableTable` carries a start PC, length, name index, descriptor index and slot, with no access flags, so finality has nowhere to be recorded.

The precise caveat: `MethodParameters` (JVMS 21 §4.7.24) does carry an `access_flags` field per parameter, and `ACC_FINAL 0x0010` is among the flags it can set. Under `javac -g -parameters` the two class files genuinely differ, and `javap -v` shows `stake  final` / `percent  final` in the `MethodParameters` table versus an empty `Flags` column for the non-`final` build. The `Code` attribute and `LocalVariableTable` were still byte-identical between those two builds. So: no effect on any executed instruction; observable in the class file only when `-parameters` is enabled, which matters only to frameworks reading runtime parameter names.

</details>

**Q6.** What is `@Stable`, what exactly is its contract, and why can you not use it to speed up your own class?

<details><summary>Answer</summary>

`jdk.internal.vm.annotation.Stable` marks a field whose component variables change value "at most once." Since every field starts at its default — `null` for references, zero for primitives — the annotation means the first non-default value stored will never change. HotSpot then "will process non-null stable fields (final or otherwise) in a similar manner to static final fields with respect to promoting the field's value to a constant." That is the mechanism that gives a lazily-initialised field the constant-folding treatment a `static final` gets, which a `static final` itself cannot express because it must be assigned in `<clinit>`.

The contract is two values: default, then one real value, forever. Writing a third is explicitly **undefined behaviour**, not a deoptimisation — the source says "it may be that the Java memory model would appear to be broken," meaning compiled code may keep serving value two after value three is written, silently.

You cannot use it because of the `@implNote`: "This annotation only takes effect for fields of classes loaded by the boot loader. Annotations on fields of classes loaded outside of the boot loader are ignored." Even with `--add-exports java.base/jdk.internal.vm.annotation=ALL-UNNAMED` to make the type visible, annotating a field of an application-loader class does nothing at all. There is no supported way to opt an application class into stable-field folding.

</details>

**Q7.** JEP 500 — what does it change, in which release, and what should you do on JDK 21 today?

<details><summary>Answer</summary>

JEP 500, "Prepare to Make Final Mean Final" (Pressler and Buckley, issue 8349536), is **Closed / Delivered for Release 26** — it shipped, it is not a proposal. It issues warnings about deep reflection that mutates `final` fields, ahead of a future release that blocks it. The transition switch is **`--illegal-final-field-mutation`**, with four values: `allow` (no warning, and it will be removed when `deny` becomes the default), `warn` (allows the mutation but warns once per module — the **default in JDK 26**, to be phased out and eventually removed), `debug` (identical to `warn` but a warning and a stack trace for *every* mutation), and `deny` (`Field::set` throws `IllegalAccessException`; this becomes the default in a future release). The opt-in is `--enable-final-field-mutation`, supplied on the command line, via `JDK_JAVA_OPTIONS`, in an `@argfile`, through a manifest `Enable-Final-Field-Mutation: ALL-UNNAMED` entry, or via `jlink --add-options` — and it applies to modules in the boot module layer only, so code in a user-defined layer cannot be enabled at all. Mutation is illegal if either the module is not enabled or the field's package is not `opens`-ed to it.

On JDK 21 nothing of this is active: `java --illegal-final-field-mutation=warn -version` prints `Unrecognized option` and fails to start. So today: run the suite on a JDK 26 build with `--illegal-final-field-mutation=deny` — the JEP's own recommendation — to enumerate every offender, then migrate each to constructor injection, a canonical record constructor, or a `MethodHandles.Lookup` used for construction rather than field writes. The JEP notes the offenders are "usually library code, not application code," so expect the hits in mocking, ORM hydration, DI and serialization layers rather than your own.

</details>

**Q8.** On JDK 21, are the `final` fields of `java.lang` value-based classes like `Integer` protected from reflective mutation?

<details><summary>Answer</summary>

No — only by module encapsulation, not by any `final`-field check, and that is a meaningful difference. `Integer.class.getDeclaredField("value")` followed by `setAccessible(true)` throws `InaccessibleObjectException: Unable to make field private final int java.lang.Integer.value accessible: module java.base does not "opens java.lang" to unnamed module`. That is JEP 403 strong encapsulation talking, not the non-modifiable-final check from the `setAccessible` javadoc — `Integer.value` is an instance `final` field of an ordinary class, which is the one still-mutable category.

Supply `--add-opens java.base/java.lang=ALL-UNNAMED` and the mutation succeeds. Measured on JDK 21.0.7: after writing `150` into the `value` field of `Integer.valueOf(100)`, `Integer.valueOf(100)` printed `150`, `cap.intValue()` returned `150`, and `100 + Integer.valueOf(100)` evaluated to `250` — because `Integer.valueOf(100)` returns a process-wide cached instance, so one write corrupted the box for every holder of the number 100 in the JVM. Any claim that this "no longer works" for value-based classes is stale on 21; this is exactly the gap JEP 500 closes in 26.

</details>

## Open questions

- The failing outcome of the escaped-`this` program (`amount` reading `null` in `balance-view-4`) was not reproduced on this machine — the plain publishing field's own visibility problem prevented a clean observation. The specification argument is decisive, but the race was not demonstrated empirically.
- The exact release that blocked the `Field.class.getDeclaredField("modifiers")` workaround was not confirmed against a primary source. Measured here: the field resolves on JDK 11.0.27 and throws `NoSuchFieldException` on 17.0.15 and 21.0.7; JDK 12 (via `Reflection.filterFields`) is the widely reported boundary, and 12 through 16 were unavailable to test.
- No specific library version that mutates `final` fields was verified against that project's source, so section 4 names categories (deep-reflection mocking, ORM hydration, DI, serialization) rather than versions. The syllabus leaf's "older Mockito, some ORM and DI tooling" is consistent with the categories JEP 500 itself calls out but was not checked.
- The JIT-trust measurement is HotSpot behaviour on one build (Oracle JDK 21.0.7, macOS aarch64), not a specification guarantee. Nothing in the JLS or JVMS obliges any implementation to fold or not fold any field.

---

**Leaves covered:** 3.12.1, 3.12.2, 3.12.3, 3.12.4, 3.12.5, 3.12.6, 3.12.7, 3.12.8, 3.12.9, 3.12.10, 3.12.11 (11 leaves)
**Leaves deferred:** none
**Diagrams included:** D-122, D-123 (rendered as a Markdown table per the manifest)
**Target version:** Java 21 LTS
**Lines:** 716
