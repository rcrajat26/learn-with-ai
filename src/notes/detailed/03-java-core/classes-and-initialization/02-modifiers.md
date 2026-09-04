# 03 Java Core — Modifiers: `static` and `final` — BASICS (§1.14, 1.14.1–1.14.11)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Class initialization triggers and failure](01d-class-initialization-triggers.md) · Next: [Access and the remaining modifiers](02a-access-and-other-modifiers.md)

Two keywords, and between them the single most under-appreciated fact in the language: a `public static final int` is not a field that callers read, it is a value the specification *requires* `javac` to copy into every caller's class file, so raising `BonusRules.MAX_BONUS` from 100 to 150 and deploying only the jar that declares it leaves every bonus grant in the fleet still capped at 100, with no error, no warning and no link failure anywhere. This file establishes that from JLS §13.1 and real `javap -v` output, then does the same for the other three mechanisms that live under these keywords — that `static` dispatch is decided entirely by the compile-time type (so `null.rules()` runs fine), that `final` in its three positions buys three different things and immutability is not any of them, and that `final` fields carry a memory-model freeze that makes safe publication possible without a lock.

**Evidence provenance.** Every `javap` block and every measured output below was produced on this machine with `javac --release 21` (class files at major version 65) executed on Oracle GraalVM 25.0.1+8.1, HotSpot, macOS aarch64. Class-file structure is the JDK 21 target; see `## Open questions` for the one caveat this creates.

## 1. A `static final` constant is copied into every caller (1.14.7, 1.14.8)

Picture two jars on a classpath. `BonusRules` declares `public static final int MAX_BONUS = 100`. `BonusService` reads it. Your mental model almost certainly says: `BonusService` holds a symbolic reference — "the field `MAX_BONUS` of type `int` in class `BonusRules`" — and the JVM resolves that reference at link time by going and looking at whatever `BonusRules.class` is actually on the classpath today. That model is right for almost every field in Java, and it is wrong for this one. There is no symbolic reference. `javac` erased it. `BonusService.class` contains the integer `100` as a literal in its own instruction stream, and the name `MAX_BONUS` appears nowhere in its bytecode at all. Nothing is left to relink, so nothing *can* be relinked.

### Why it exists

Constants must be usable in positions where a runtime field read is not merely slow but syntactically impossible: a `case` label, an array dimension in an annotation-adjacent context, an annotation element value, the compile-time evaluation of `if (DEBUG_MODE)` that lets the compiler drop unreachable code. All of those require the *value*, at compile time, not a promise to fetch it later. Before `static final` compile-time constants, the equivalents were C-style preprocessor macros in other languages and `interface`-full-of-constants patterns in early Java. Java's answer was to define a narrow category of field whose value is guaranteed available to the compiler, and then — because the value is available — to require its use everywhere the field is read. The convenience and the hazard are the same mechanism seen from two sides.

### The mechanism

`[SOURCE]` The category is defined by **JLS 21 §4.12.4**, verbatim:

> A *constant variable* is a final variable of primitive type or type String that is initialized with a constant expression (§15.29). Whether a variable is a constant variable or not may have implications with respect to class initialization (§12.4.1), binary compatibility (§13.1), reachability (§14.22), and definite assignment (§16.1.1).

Three conjuncts, all required: `final`; a primitive or `String`; and a **constant expression** initializer. Drop any one and the field is an ordinary field. What counts as a constant expression is JLS §15.29's job and is worked in full in `../primitives-and-conversions/02-operators-and-expressions.md` — the short version is literals, other constant variables, and the operators applied to them, which is why `"AO-" + 200` folds and `"AO-" + phase` does not when `phase` is a non-final field.

`[PROVE]` Measured, one class, seven declarations, `javap -v` reporting which fields carry a `ConstantValue` attribute:

| Declaration | `ConstantValue` in the class file? | Constant variable? |
|---|---|---|
| `public static final int MAX_BONUS = 100;` | `ConstantValue: int 100` | Yes |
| `public static final String GRANTED = "AO-" + 200;` | `ConstantValue: String AO-200` | Yes — the concatenation is itself a constant expression |
| `public static final String DYNAMIC = "AO-" + phase;` (non-final `static String phase`) | absent | No — initializer is not a constant expression |
| `public static final BigDecimal CAP = new BigDecimal("100");` | absent | No — not a primitive or `String` |
| `public static final int VIA_METHOD = Integer.valueOf(100);` | absent | No — a method call is not a constant expression |
| `public static final long COUPON_DAYS;` assigned `14L` in a `static` block (a blank final) | absent | No — no initializer on the declaration |
| `static String phase = "200";` (not final) | absent | No — not final |

The two rows that carry `ConstantValue` are exactly the two whose declarations satisfy all three conjuncts. Blank finals and definite assignment are `01-basics.md`'s territory; the row is here only to show that "assigned a literal somewhere" is not the test — the initializer must be *on the declaration*.

`[SOURCE]` Now the clause that makes this a hazard rather than a curiosity, **JLS 21 §13.1, "The Form of a Binary"**, verbatim:

> A reference to a field that is a constant variable (§4.12.4) **must** be resolved at compile time to the value V denoted by the constant variable's initializer.
>
> If such a field is `static`, then **no reference to the field should be present in the code in a binary file, including the class or interface which declared the field.** Such a field must always appear to have been initialized (§12.4.2); the default initial value for the field (if different than V) must never be observed.
>
> If such a field is non-`static`, then no reference to the field should be present in the code in a binary file, except in the class containing the field. (It will be a class rather than an interface, since an interface has only `static` fields.) The class should have code to set the field's value to V during instance creation (§12.5).

Read that word by word, because the usual retelling ("the compiler *might* inline small constants as an optimisation") gets every clause wrong.

- **"must be resolved at compile time"** — not may. This is not an optimisation `javac` elects to perform and a different compiler might skip. A conforming compiler that emitted a `getstatic` for a constant variable would be non-conforming. You cannot turn it off; there is no flag.
- **"no reference to the field should be present in the code in a binary file"** — the caller's class file does not contain a weak, stale, or overridable reference to `BonusRules.MAX_BONUS`. It contains *no* reference. Link-time resolution has nothing to work on. This is why the failure is silent: silence is not the JVM failing to notice a mismatch, it is the JVM correctly finding no mismatch to notice.
- **"including the class or interface which declared the field"** — the clause almost every treatment omits. `BonusRules`' own methods reading its own `MAX_BONUS` get the inlined value too. There is no privileged inside view.
- **"must always appear to have been initialized [] the default initial value [] must never be observed"** — you can never catch such a field at `0`, not even mid-initialization. That is the other half of this mechanism, and it is why reading a constant variable does not trigger the declaring class's initialization at all: `01d-class-initialization-triggers.md` owns that consequence and diagram D-039. Same mechanism, opposite-facing conclusion.
- **The third paragraph** — the rule is not `static`-only. A non-`static` `final int` initialized with a constant expression is also a constant variable; every *other* class reading it gets the inlined value, and the declaring class emits code to set the field during instance creation.

`[SOURCE]` **JVMS 21 §5.5** pins down *when* the field itself gets its value, which is what makes the 1.14.8 fix mechanically explicable rather than folkloric. Verbatim, from the class-initialization procedure:

> Otherwise, record the fact that initialization of the Class object for C is in progress by the current thread, and release LC. Then, initialize each `final static` field of C with the constant value in its `ConstantValue` attribute (§4.7.2), in the order the fields appear in the `ClassFile` structure.

So a `ConstantValue`-carrying field is populated by the JVM **before** `<clinit>` runs a single instruction, directly from the attribute, in class-file field order — not by any code you wrote. Field storage exists and holds the right value, and reflection can read it; it is simply that no compiled code ever reads it that way.

![D-042 — A `static final` constant is copied into every caller](../diagrams/D-042-constant-inlining.svg)

**D-042** — Left half, BEFORE: both classes compiled together, `BonusRules.class` carrying `ConstantValue: int 100` and `BonusService.class` already holding that literal in its *own* constant pool, loaded by its own instruction. Right half, AFTER: `BonusRules` recompiled to `ConstantValue: int 150` in green, `BonusService` untouched and still loading `100` in the failure palette. The annotation panel names the deploy that produces it — a partial deploy or an incremental build ships a rebuilt `BonusRules` jar against a `BonusService` jar built earlier, the JVM links cleanly, no error is raised, and every bonus grant silently caps at 100 instead of 150. One reading note: the diagram schematises the caller's load as `#7 = Integer 100` / `ldc #7 // int 100`, which is what you see for a constant outside the `bipush`/`sipush` immediate ranges; for the literal `100` specifically, `javac` emits the shorter `bipush 100` with no constant-pool entry at all, as the real output below shows. That difference is an encoding detail — with `bipush` the value is baked into the instruction's own operand byte, which if anything makes the point harder.

### The program

```java
public final class BonusRules {
    public static final int MAX_BONUS = 100;
    private BonusRules() { throw new AssertionError("no instances"); }
}
```

```java
public final class BonusService {
    public int grant(int firstDepositMinorUnits) {
        int tenPercent = firstDepositMinorUnits / 10;
        return Math.min(tenPercent, BonusRules.MAX_BONUS);
    }

    public static void main(String[] args) {
        System.out.println(new BonusService().grant(100000));
    }
}
```

`[BYTECODE]` Compile both together, then `javap -v -p BonusRules.class`. The declaring side:

```
  public static final int MAX_BONUS;
    descriptor: I
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL
    ConstantValue: int 100
```

and its constant pool carries `#19 = Integer 100` feeding that attribute. Now the caller, `javap -v -p -c BonusService.class`:

```
  public int grant(int);
    descriptor: (I)I
    Code:
      stack=2, locals=3, args_size=2
         0: iload_1
         1: bipush        10
         3: idiv
         4: istore_2
         5: iload_2
         6: bipush        100
         8: invokestatic  #9      // Method java/lang/Math.min:(II)I
        11: ireturn
```

Instruction by instruction. `0: iload_1` pushes the `firstDepositMinorUnits` parameter from local slot 1. `1: bipush 10` pushes the literal divisor — `bipush` is "push a one-byte signed immediate", so the `10` is inside the instruction, not the constant pool. `3: idiv` divides, `4: istore_2` parks the result in `tenPercent`. `5: iload_2` reads it back for the `Math.min` call. Then **`6: bipush 100`** — and that is the whole lesson. There is no `getstatic`. There is no `Fieldref` to `BonusRules.MAX_BONUS` in the constant pool; grep the full 40-entry pool dump for `MAX_BONUS` and it returns nothing. The literal `100` is an operand byte of an instruction in `BonusService`'s own `grant` method. `8: invokestatic #9` calls `Math.min(II)I`, `11: ireturn` returns.

One genuinely surprising residue: `BonusService`'s constant pool *does* contain `#7 = Class BonusRules`, referenced by no instruction in the class. `javac` records the type it read the constant from, but the field access itself is gone. A `Class` entry is not a `Fieldref`; it carries no field name, no descriptor, and nothing the linker resolves against a field. **Unverified:** I could not find a JLS or JVMS clause requiring or forbidding that dangling `Class` entry; it appears to be a `javac` artifact.

`[PROVE]` The full stale-deploy sequence, run end to end:

1. Compile `BonusRules` (100) and `BonusService` together into `out1`. `java -cp out1 BonusService` prints **`100`** — a first deposit of 100000 minor units gives 10% = 10000, capped at 100. Correct against the 100 cap.
2. Copy `out1` to `out2`. Edit the source to `MAX_BONUS = 150` and recompile **`BonusRules.java` only** into `out2` — the incremental build, or the partial deploy that ships one jar.
3. `javap -v -p out2/BonusRules.class` now reports `ConstantValue: int 150`, and its pool holds `#19 = Integer 150`. The declaring class is unambiguously updated.
4. `javap -c -p out2/BonusService.class` still reports `6: bipush 100`. Byte-identical to step 1, because the file was not touched.
5. `java -cp out2 BonusService` prints **`100`**. No exception. No `NoSuchFieldError`, no `IncompatibleClassChangeError`, no warning on stderr. The JVM did nothing wrong: it was never asked to resolve a field.
6. Recompile both into `out3`. `java -cp out3 BonusService` prints **`150`**.

Only step 6 fixes it, and step 6 is "recompile every caller", which in a multi-module build with a published constants artifact means recompiling every module that transitively reads the constant — not just the ones whose source you changed.

### What the stale constant costs, in QuizStakes money

Derive it rather than guess. QuizStakes grants bonuses at 3.1k/day (8/sec, average grant 42). The grant rule is 10% of the first deposit, capped — so raising the cap from 100 to 150 only changes the outcome for grants that were *cap-bound*, meaning 10% of the first deposit was at or above 100, i.e. a first deposit of 1,000 or more. For a grant whose uncapped 10% is 150 or more, the stale cap under-credits by exactly **50**; for one whose uncapped value falls between 100 and 150, it under-credits by less. The upper bound is therefore 3,100 × 50 = **155,000 per day** of promised bonus not granted, about 56.6M a year. The average grant of 42 is well under the 100 cap, which tells us most grants are deposit-bound and unaffected, so the true figure is a fraction of that bound — the deposit-size distribution above 1,000 is not in the published numbers, so the honest statement is the bound plus its direction, not a point estimate. The regulatory exposure is worse than the money: the marketing terms said 150, the platform paid 100, and the discrepancy is invisible in every log line because the code executed exactly as compiled.

**Pitfall:** believing a constant is a field that callers read at runtime, so bumping it and shipping the declaring jar is enough. The wrong belief is "one symbolic reference, resolved at link time". The symptom is the deploy that changes nothing, with a green pipeline, clean logs, and a `javap` of the declaring class that *proves* the new value is there. The fix is either recompile every caller, or stop the field being a constant variable in the first place — next.

### 1.14.8 — the fix, and what it costs

`[RESEARCH]` To keep the value late-bound, break one of §4.12.4's three conjuncts. The cheapest break is the initializer: replace the constant expression with anything that is not one.

```java
public final class BonusRules {
    public static final int MAX_BONUS = Integer.valueOf(150);

    public static int selfRead() { return MAX_BONUS; }

    private BonusRules() { throw new AssertionError("no instances"); }
}
```

`[BYTECODE]` Recompile both classes. Three things change, all measured. First, the field loses its attribute entirely:

```
  public static final int MAX_BONUS;
    descriptor: I
    flags: (0x0019) ACC_PUBLIC, ACC_STATIC, ACC_FINAL
```

No `ConstantValue` line. Per JVMS §5.5 there is now nothing for the JVM to pre-populate, so the value must be assigned by code — and `javac` synthesises exactly that:

```
  static {};
    descriptor: ()V
    flags: (0x0008) ACC_STATIC
    Code:
         0: sipush        150
         3: invokestatic  #20     // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
         6: invokevirtual #26     // Method java/lang/Integer.intValue:()I
         9: putstatic     #1      // Field MAX_BONUS:I
        12: return
```

`sipush 150` (a two-byte immediate, since 150 exceeds `bipush`'s signed-byte range of −128 to 127), box, unbox — the round trip whose only purpose is to stop being a constant expression — then `putstatic` into the real field, inside `<clinit>`. Second, the declaring class's own read is now a real read: `selfRead()` compiles to `0: getstatic #1 // Field MAX_BONUS:I` / `3: ireturn`. Third, and the point of the exercise, the caller:

```
  public int grant(int);
    Code:
         0: iload_1
         1: bipush        10
         3: idiv
         4: getstatic     #7      // Field BonusRules.MAX_BONUS:I
         7: invokestatic  #13     // Method java/lang/Math.min:(II)I
        10: ireturn
```

`getstatic #7`, and `#7 = Fieldref #8.#9 // BonusRules.MAX_BONUS:I` is back in `BonusService`'s constant pool. The symbolic reference exists again, so link-time resolution has something to resolve, so replacing `BonusRules.class` alone changes the caller's behaviour. Note also that the local `4: istore_2` / `5: iload_2` pair vanished — the value is consumed directly — which is unrelated to the fix and just shows `javac`'s local-slot handling.

What the fix costs, stated as a trade rather than a free win:

| | Constant variable (`= 150`) | Non-constant (`= Integer.valueOf(150)`) |
|---|---|---|
| Caller's instruction | `sipush 150` — immediate operand | `getstatic` — a field read through a resolved reference |
| Recompile callers on change? | Required, or they stay stale | Not required |
| Usable as a `case` label, annotation value, array dimension? | Yes | **No** — those positions demand a constant expression |
| Triggers declaring class's initialization on read? | No | Yes |
| Folded into surrounding arithmetic by `javac`? | Yes | No |
| JIT constant propagation through the value | Guaranteed — the value is literally in the code | Not a language guarantee; see below |

The two rows that bite hardest in practice are the third and fourth. Losing constant-expression status means the field can no longer appear in a `switch` label — if `MAX_BONUS` or a `StatusCode` string constant is used in a `case`, this fix does not compile, and you need a different shape (a method, an enum, or a sealed hierarchy). And the read now triggers `BonusRules`' class initialization, which matters if that class has a `static` block with ordering or failure semantics — `01d-class-initialization-triggers.md`.

On the last row, precision matters. HotSpot's JIT does treat a `static final` field as trustworthy for constant folding once the holder class is initialized, because a `static final` field cannot legally change afterwards. That is **JIT behaviour, not a specification guarantee**, and it is not symmetric with instance `final`, which HotSpot does *not* unconditionally trust. Which is trusted, under what conditions, `@Stable`, and the measured effect all belong to `04-internals-final-and-constant-folding.md`; the honest one-line version here is: the constant-variable form gets the folding from the language, the `getstatic` form gets it only from the JIT, and only under the JIT's own conditions.

Better fixes than `Integer.valueOf`, in order of how much they say about intent, since a bare `Integer.valueOf` wrapper is a puzzle for the next reader:

```java
public final class BonusRules {
    // Configuration that must be changeable without recompiling callers.
    private static final int DEFAULT_MAX_BONUS_MINOR_UNITS = 150;
    private static volatile int maxBonusMinorUnits = DEFAULT_MAX_BONUS_MINOR_UNITS;

    public static int maxBonusMinorUnits() { return maxBonusMinorUnits; }

    static void reconfigure(int minorUnits) {
        if (minorUnits < 0) {
            throw new IllegalArgumentException("negative bonus cap: " + minorUnits);
        }
        maxBonusMinorUnits = minorUnits;
    }

    private BonusRules() { throw new AssertionError("no instances"); }
}
```

An accessor method is never a constant expression, so no caller can inline the value; it is also the only form that survives being made genuinely dynamic later. `volatile` is what makes a mid-flight `reconfigure` visible to the 8-per-second grant threads — that keyword is `02a-access-and-other-modifiers.md`'s to explain and guide **05 Concurrency**'s to justify.

> A **constant variable** is a `final` variable of primitive or `String` type initialized with a constant expression; JLS §13.1 *requires* every read of one to be resolved at compile time to its value, so no reference to it survives in any caller's class file — including the declaring class's own.

## 2. Static members are bound at compile time (1.14.1, 1.14.2, 1.14.3)

Picture the `static` keyword as moving a member out of the object and onto the class, and then — the part people miss — moving the *decision about which member* out of runtime and into compile time. An instance method call asks the object at runtime, "what are you really?" A static method call never asks anybody anything: `javac` looks at the declared type of the expression you qualified it with, picks the method, and writes that choice permanently into an `invokestatic` instruction. The object at the other end of the reference is never consulted. It does not need to exist.

### Why it exists

One copy, shared, no `this`: that is the whole of 1.14.1. A `static` field exists once per class (strictly, once per class-loader-and-class pair), lives in the class's own storage rather than in any instance, and is reachable with no instance at all. A `static` method has no `this`, so it cannot read instance fields, cannot be the target of dynamic dispatch, and needs no receiver — which is exactly what a factory (`Money.of`), a pure function (`MoneyMath.splitStake`) or a namespaced utility needs. The dispatch consequence follows mechanically: with no receiver, there is nothing whose runtime type could select an override.

### The mechanism

`invokestatic` names a method by the compile-time type's descriptor and there is no vtable slot involved — no per-class table of overrides is consulted, no runtime type check occurs. That is why a static method in a subclass with the same signature as one in its superclass **hides** rather than overrides it: two independent methods exist, and which one runs is decided by which type the call site named. The five invoke instructions and vtable mechanics are `../inheritance-and-dispatch/03-internals-dispatch.md`; the drawn hiding-versus-overriding contrast is D-044 in `../inheritance-and-dispatch/01-basics.md`, which owns leaf 1.15.5.

Two hard compiler facts, both measured. `@Override` on a static method does not compile — `javac --release 21` reports `error: static methods cannot be annotated with @Override`, which is a rare case of the language refusing to let you express the misunderstanding at all. And crossing the static boundary in either direction is an error, not a hide: an instance method in a subclass with the same signature as a superclass `static` method gives `error: rules() in PromoBonusService cannot override rules() in BonusService` with the note `overridden method is static`.

`[TRAP]` The third leaf is the sharp one. **JLS §15.12.4.1** governs evaluating the qualifying expression of a method invocation: if the method is `static`, the qualifying reference expression is evaluated for its side effects and the resulting value is then **discarded**. No null check, because nothing dereferences it. `obj.staticMethod()` compiles, resolves against `obj`'s *declared* type, and runs happily when `obj` is `null`.

No diagram in the manifest covers static binding at this depth — D-044 covers the hiding-versus-overriding contrast and belongs to the inheritance file.

```java
class BonusService {
    static String rules() { return "BonusService rules: cap 100"; }
    String describe() { return "bonus service"; }
}

class PromoBonusService extends BonusService {
    static String rules() { return "PromoBonusService rules: cap 150"; }

    @Override
    String describe() { return "promo bonus service"; }
}

public class StaticBinding {
    public static void main(String[] args) {
        BonusService viaBase = new PromoBonusService();
        System.out.println(viaBase.rules());     // hidden, not overridden
        System.out.println(viaBase.describe());  // genuinely overridden

        BonusService nullRef = null;
        System.out.println(nullRef.rules());     // no NullPointerException
        System.out.println("no NPE was thrown");
    }
}
```

Measured output:

```
BonusService rules: cap 100
promo bonus service
BonusService rules: cap 100
no NPE was thrown
```

`[BYTECODE]` `javap -c -p StaticBinding.class`, the four interesting fragments of `main`:

```
         0: new           #7      // class PromoBonusService
         3: dup
         4: invokespecial #9      // Method PromoBonusService."<init>":()V
         7: astore_1
         8: getstatic     #10     // Field java/lang/System.out:Ljava/io/PrintStream;
        11: aload_1
        12: pop
        13: invokestatic  #16     // Method BonusService.rules:()Ljava/lang/String;
        16: invokevirtual #22     // Method java/io/PrintStream.println:(Ljava/lang/String;)V
        19: getstatic     #10     // Field java/lang/System.out:Ljava/io/PrintStream;
        22: aload_1
        23: invokevirtual #28     // Method BonusService.describe:()Ljava/lang/String;
        26: invokevirtual #22     // Method java/io/PrintStream.println:(Ljava/lang/String;)V
        29: aconst_null
        30: astore_2
        31: getstatic     #10     // Field java/lang/System.out:Ljava/io/PrintStream;
        34: aload_2
        35: pop
        36: invokestatic  #16     // Method BonusService.rules:()Ljava/lang/String;
        39: invokevirtual #22     // Method java/io/PrintStream.println:(Ljava/lang/String;)V
```

Read `11: aload_1` / `12: pop` / `13: invokestatic`. `aload_1` pushes the receiver — the `PromoBonusService` instance, complete with correct runtime type — onto the operand stack. `pop` throws it away. Then `invokestatic #16` calls `BonusService.rules`, named against the *declared* type `BonusService`, hard-coded in the constant pool at compile time. That `pop` is JLS §15.12.4.1 rendered as a single byte: evaluate the qualifier for side effects, discard it.

Compare `22: aload_1` / `23: invokevirtual #28`. Here the receiver is pushed and *kept*, because `invokevirtual` needs it — the JVM reads the object's actual class and dispatches to `PromoBonusService.describe`, even though the constant pool entry names `BonusService.describe`.

Now the null case at 29. `aconst_null` / `astore_2` puts `null` in slot 2. Then `34: aload_2` pushes null, `35: pop` discards it, `36: invokestatic #16` — the identical instruction as at offset 13, byte for byte. Nothing between 29 and 39 could throw a `NullPointerException`: `aload` of a null reference is legal (it loads a reference, it does not dereference one), `pop` cannot fail, and `invokestatic` takes no receiver. There is no dereference anywhere in the sequence, and no dereference means no NPE.

`javac --release 21 -Xlint:all` warns on both instance-qualified calls: `warning: [static] static method should be qualified by type name, BonusService, instead of by an expression`. That lint is off unless you enable `-Xlint:static` (or `-Xlint:all`), which is why so much production code carries the pattern.

`[TRAP]` The interview trap on the instance-reference form is not the null case, it is the refactoring case. `viaBase.rules()` reads as if it dispatches, so a maintainer who later changes `viaBase`'s declared type from `BonusService` to `PromoBonusService` silently changes which method the *unmodified* line calls — from cap 100 to cap 150 — because the compile-time type is the entire input to the decision.

**Insight:** the `pop` at offset 12 is also why `nextIndex().staticMethod()` still runs `nextIndex()`. The qualifier's side effects happen; only its value is discarded. A static call through a method-call qualifier is not dead code.

> `static` binds a member to the class rather than to any instance — one copy, no `this` — and a `static` method invocation is compiled to `invokestatic` against the *compile-time* type of its qualifier, so subclass statics hide rather than override, and a call through a `null` reference discards the receiver and runs normally.

## 3. `final` in three positions, and what none of them is (1.14.5, 1.14.6)

Picture `final` as a lock on a *slot*, never on the contents of the slot. On a variable, the slot is the storage holding the reference or the primitive: locked, one assignment only. On a method, the slot is the vtable entry: locked, no subclass may replace it. On a class, the slot is the position in the type hierarchy: locked, nothing may extend it. Three different slots, three different guarantees, and in none of the three cases does anything reach past the slot into the object it points at.

### Why it exists

Each position solves a different problem. On a variable, `final` gives the compiler enough information to prove single assignment — which enables definite-assignment analysis, makes lambda capture safe, and enables the memory-model freeze in section 4. On a method, it closes an extension point, which is how a class stops a subclass from breaking an invariant the superclass depends on — the fragile-base-class problem, `../inheritance-and-dispatch/01-basics.md`. On a class, it makes the type a leaf, which is what lets `String` and every value type guarantee its own immutability: a subclass could otherwise add mutable state, and no amount of `final` on the superclass's fields would stop it.

### The mechanism

| Position | Enforced by | What it guarantees | What it does *not* guarantee |
|---|---|---|---|
| Variable (field, local, parameter) | `javac` at compile time; `ACC_FINAL` in the field's flags for fields | Exactly one assignment; the slot never changes value afterwards | Nothing about the referenced object's state |
| Method | `javac`, plus `ACC_FINAL` in the method flags, plus JVM verification at link time | No subclass declares an overriding method | Nothing about performance — inlining is a JIT decision, not a `final` consequence |
| Class | `javac`, plus `ACC_FINAL` in the class flags, plus JVM verification | No class declares it as a superclass | Nothing about the class's own mutability |

For a local variable, enforcement is purely `javac`'s: there is no place in the class file to record it (unless `-parameters` is used for a parameter — see the supporting fact on 1.14.11). For a field, method or class, `ACC_FINAL` is in the class file and the verifier enforces it, which is why you cannot defeat a `final` method by hand-assembling a subclass.

`[TRAP]` 1.14.6, and the reason this section exists. `final` on a reference variable locks the pointer, not the pointee. JLS §4.12.4 says it in the spec's own words, verbatim:

> arrays [] are objects; if a final variable holds a reference to an array, then the components of the array may be changed by operations on the array, but the variable will always refer to the same array.

Substitute "map" for "array" and it is the same sentence.

No diagram in the manifest covers the three positions of `final`; D-033 covers constant folding and belongs to the strings and internals files.

```java
import java.util.HashMap;
import java.util.Map;

public final class ClientRestrictions {
    // final: the field will always point at this same HashMap instance.
    // Not final: anything about that HashMap's contents.
    private final Map<RestrictionKey, Restriction> active = new HashMap<>();

    public void apply(Restriction restriction) {
        active.put(restriction.key(), restriction);   // legal: mutating the pointee
    }

    public void lift(RestrictionKey key) {
        active.remove(key);                          // legal: mutating the pointee
    }

    public boolean stakeBlocked() {
        return active.containsKey(
                new RestrictionKey(RestrictionType.STAKE_BLOCKED, RestrictionSource.ADMIN));
    }

    // Exposing the field is where "final" stops helping at all: the caller
    // receives the same mutable HashMap and can clear it.
    public Map<RestrictionKey, Restriction> leakyView() {
        return active;
    }

    public Map<RestrictionKey, Restriction> safeView() {
        return Map.copyOf(active);   // unmodifiable snapshot; the only honest accessor
    }
}
```

A caller holding `leakyView()` can call `clear()` and lift every restriction on the account, `SELF_EXCLUDED` included — the field is `final` the entire time, and the compiler is entirely satisfied. `Map.copyOf` returns an unmodifiable map, and it is a *snapshot*, so a later `apply` is not reflected in a previously handed-out view; the design discipline around defensive copying, deep versus shallow, and when a snapshot is the wrong contract is `../immutability-and-design/02-immutability.md`'s.

`[PROVE]` The one place `final` on a variable does hold against everything, including reflection — and the place it does not. The **`Field.setAccessible` javadoc, Java 21**, verbatim:

> This method cannot be used to enable write access to a non-modifiable final field. The following fields are non-modifiable: `static final` fields declared in any class or interface / `final` fields declared in a hidden class / `final` fields declared in a record. The accessible flag when `true` suppresses Java language access control checks to only enable read access to these non-modifiable final fields.

Measured against that list, `setAccessible(true)` then `setInt`:

| Field | Result |
|---|---|
| `static final int MAX_BONUS` (non-constant, so the field is genuinely read at runtime) | `IllegalAccessException: Can not set static final int field BonusRules.MAX_BONUS to (int)150` |
| `final int stakeMinor` on an ordinary final class `Reservation` | **Succeeded** — the field changed from 420 to 999 |
| `final int minor` on `record Money(int minor)` | `IllegalAccessException: Can not set final int field Money.minor to (int)1` |

Exactly the javadoc's split: `static final` and record fields are non-modifiable, an ordinary instance `final` is not. So on JDK 21, an instance `final` field is a compile-time guarantee that reflection can break, while a `static final` field and any record component are guarantees the runtime enforces. That asymmetry is being closed: JEP 500's `--illegal-final-field-mutation` makes the ordinary instance case warn by default in JDK 26, with denial planned later — `04-internals-final-and-constant-folding.md` owns the detail and the timeline.

**Pitfall:** reading `private final Map<K, V>` as "an immutable map". The wrong belief is that `final` propagates into the object. The symptom is a mutable collection handed out through an accessor and mutated by a caller — in QuizStakes, a lifted `SELF_EXCLUDED` restriction that `reversibleByOperator = false` was supposed to make impossible. The fix is two independent things: `final` on the field for the pointer, and an unmodifiable type or a copy-on-read accessor for the contents. Neither substitutes for the other.

**Insight:** `final` on a method is not a performance hint. HotSpot inlines virtual calls it can prove monomorphic regardless of `final`, and de-optimises if a later-loaded class invalidates the assumption; `final` changes what a *subclass author* may do, not what the JIT may do. Anyone citing `final` methods as an optimisation is reciting pre-HotSpot folklore.

> `final` locks a slot: one assignment for a variable, no override for a method, no subclass for a class. It never reaches into the object a reference points at, so a `final` field holding a mutable collection is a fixed pointer to freely mutable state.

## 4. `final` fields and the JMM freeze (1.14.9)

`[X-REF 05]` Picture object construction as ending with a stamp. The instant a constructor exits, every `final` field written in it is *frozen* — and the memory model's rule is that no thread can ever observe the object through a reference obtained after that freeze and see a pre-freeze value of a frozen field. That is a guarantee about ordering across threads, obtained without a lock, without `volatile`, and without any cooperation from the publishing code beyond one requirement: do not let `this` escape before the constructor finishes.

### Why it exists

Without it, safe publication of even a trivially immutable object would need synchronisation. A `Reservation` holding a `StakeSplit` could be constructed on `stake-reservation-3` and handed to `payment-run-worker`, and absent a `final`-field rule the second thread could legally see the reference as non-null while seeing `stakeMinor` as 0 — the field write and the reference write being reorderable relative to each other. Every value object in the system would need a lock or a `volatile` around publication. The `final`-field rule removes that cost for the overwhelmingly common case of an object that is fully built and then shared.

### The mechanism

`[SOURCE]` **JLS 21 §17.5, "final Field Semantics"**, verbatim, is the guarantee:

> A thread that can only see a reference to an object after that object has been completely initialized is guaranteed to see the correctly initialized values for that object's `final` fields.

The spec's own term for the boundary is **freeze**, defined verbatim:

> Let *o* be an object, and *c* be a constructor for *o* in which a `final` field *f* is written. A *freeze* action on `final` field *f* of *o* takes place when *c* exits, either normally or abruptly.

"Either normally or abruptly" is worth noticing: the freeze happens even when the constructor throws. And the usage rule, verbatim, is two clauses and one consequence:

> Set the `final` fields for an object in that object's constructor; and do not write a reference to the object being constructed in a place where another thread can see it before the object's constructor is finished.
> If this is followed, then when the object is seen by another thread, that thread will always see the correctly constructed version of that object's `final` fields.

The second clause is the whole precondition. The guarantee is conditional on the reference not escaping early, and nothing in the language enforces that condition.

No diagram here: the drawn freeze timeline is D-122 and belongs to `04-internals-final-and-constant-folding.md`, along with the table of what the JIT trusts.

```java
import java.math.BigDecimal;
import java.util.Currency;

record Money(BigDecimal amount, Currency currency) { }

record StakeSplit(Money bonusPortion, Money cashPortion) { }

/** Safely publishable: both fields final, no reference escapes the constructor. */
final class Reservation {
    private final Money stake;
    private final StakeSplit split;

    Reservation(Money stake, StakeSplit split) {
        this.stake = stake;
        this.split = split;
    }   // freeze on both final fields happens here

    Money stake() { return stake; }
    StakeSplit split() { return split; }
}

/** Broken: the reference escapes before the constructor finishes, so no freeze protects it. */
final class LeakyReservation {
    static LeakyReservation inFlight;   // visible to other threads immediately

    private final Money stake;

    LeakyReservation(Money stake) {
        inFlight = this;      // escapes here, BEFORE the field is written
        this.stake = stake;   // written after another thread could already be reading
    }

    Money stake() { return stake; }
}

public final class ReservationHandoff {
    /** Plain static field, no volatile, no lock. Safe for Reservation. */
    static Reservation published;

    static void publishOn(String threadName, Money stake, StakeSplit split) {
        Thread.ofPlatform().name(threadName).start(() -> {
            published = new Reservation(stake, split);
        });
    }

    static void consumeOn(String threadName) {
        Thread.ofPlatform().name(threadName).start(() -> {
            Reservation r = published;
            if (r != null) {
                // Guaranteed by JLS 17.5: if r is non-null, stake and split
                // are the values the constructor wrote. Never null, never stale.
                System.out.println(r.stake() + " split as " + r.split());
            }
        });
    }
}
```

`published` is a plain `static` field with no `volatile` and no lock, and `consumeOn`'s read is still safe *for the final fields*, because the reference it read could only have been written after the constructor exited — after the freeze. The one thing §17.5 does not promise is that `balance-view-4` sees `published` as non-null at all, promptly or ever; the freeze rule orders the *contents* relative to the reference, it does not make the reference itself visible. Making the handoff itself timely is what `volatile` is for, and that is guide **05**'s subject.

`LeakyReservation` is the counterexample, and it fails for a reason worth stating precisely: `inFlight = this` publishes the reference at a point where `stake` has not been assigned, so a reader thread can obtain a non-null `LeakyReservation` and read `stake` as `null`. No freeze has occurred — the constructor has not exited — so §17.5's guarantee simply does not apply, and the reader can observe a `final` field at its default value. This is the reason `this` must not escape a constructor, and it is why JEP 513's flexible constructor bodies (`01c-class-anatomy-and-constructors.md`) permit statements before `super()` but still do not permit `this` to escape.

**Pitfall:** believing `final` makes an object thread-safe. It does not. `final` freezes the *fields*, so a `final Map` field is safely published — and the `HashMap` it points at is then shared, unsynchronised, mutable state that two threads can corrupt structurally. Safe publication of a reference to a mutable object is not thread safety; it only guarantees you correctly see the reference to the thing you are about to race on.

> A `final` field is *frozen* when its constructor exits, and any thread that obtains the object's reference only after that point is guaranteed to see the constructor's values — safe publication with no synchronisation, conditional entirely on `this` not escaping the constructor.

## Supporting facts

### `static` on nested classes, imports, factories and utility classes (1.14.4)

The syntax is assumed; the mechanism is not. **A static nested class holds no reference to an enclosing instance; a non-static inner class does** — `javac` gives every inner class a synthetic `this$0` field pointing at the outer object, and the compiler-generated constructor requires one. That is a memory-retention fact, not a syntax preference: an inner-class `Comparator` or `Runnable` stored in a long-lived cache pins its entire enclosing `AccountMaintenance` instance, and everything that instance references, for as long as the cache holds it. Static nested is therefore the default, and `private static final class` is the right shape for a helper type. `this$0` retention and the four nested-class kinds are `../inheritance-and-dispatch/02-nested-classes.md`'s; diagram D-050 draws the retention.

**Static imports** create a resolution hazard on overloaded names. `import static` brings a *name* into scope, not a specific signature, so statically importing `min` from two classes that both declare it, or from one class alongside a same-named local method, produces either an ambiguity error or — worse, because it compiles — a silent bind to an overload you did not intend. Import the type and qualify the call (`MoneyMath.splitStake(stake)`) for anything overloaded; reserve static import for unmistakable single-signature names.

**A static utility class needs `private` on its constructor** because the implicit no-arg constructor is otherwise `public` (strictly, it takes the class's own access), and an instantiable utility class invites `new MoneyMath()` in code that then treats it as a service. The `private` constructor blocks `new` from outside, and `final` on the class blocks a subclass from adding a `public` constructor. What still defeats it: **reflection** — `MoneyMath.class.getDeclaredConstructor()` plus `setAccessible(true)` plus `newInstance()` will construct one. `throw new AssertionError("no instances")` in the private constructor body closes that too, because the reflective call then completes by propagating the error wrapped in an `InvocationTargetException`.

```java
public final class MoneyMath {
    private MoneyMath() { throw new AssertionError("no instances"); }

    /** Bonus portion is 10% of the stake, rounded DOWN to the minor unit; cash covers the rest.md. */
    public static StakeSplit splitStake(Money stake, Money bonusAvailable) {
        BigDecimal tenPercent = stake.amount()
                .multiply(new BigDecimal("0.10"))
                .setScale(2, RoundingMode.DOWN);
        BigDecimal bonus = tenPercent.min(bonusAvailable.amount());
        BigDecimal cash = stake.amount().subtract(bonus);
        return new StakeSplit(
                new Money(bonus, stake.currency()),
                new Money(cash, stake.currency()));
    }
}
```

A stake of 3.33 gives `3.33 × 0.10 = 0.333`, `setScale(2, DOWN)` → `0.33` bonus, and `3.33 − 0.33 = 3.00` cash — the canonical split, and the two portions sum exactly to the stake, which is `StakeSplit`'s invariant. `splitStake` is a `static` factory precisely because it has no `this` to need: it is a pure function of its arguments, so making it an instance method of a service would add a receiver that contributes nothing.

### Effectively final, and why lambda capture requires it (1.14.10)

A local variable or parameter is **effectively final** if it is not declared `final` but could have been. `01a-names-scope-and-var.md` owns the full JLS rule, including the interaction with `var`, shadowing and static-block textual order; the three clauses for a local declared with an initializer are, verbatim from JLS 21 §4.12.4: "It is not declared final." / "It never occurs as the left hand side in an assignment expression (§15.26). (Note that the local variable declarator containing the initializer is not an assignment expression.)" / "It never occurs as the operand of a prefix or postfix increment or decrement operator (§15.14, §15.15)."

The mechanism behind the *requirement* is what this file adds. A lambda or anonymous class that references an enclosing local **captures it by value** — the value is copied into the synthetic capture at the point the lambda is created, because the enclosing method's frame may be long gone by the time the lambda runs. Java therefore has no way to make a later reassignment of the local visible inside the lambda, nor a reassignment inside the lambda visible outside. Rather than let the two copies diverge silently, the language requires the variable be effectively final, so the question of which copy is authoritative can never arise. The gotcha: the workaround people reach for — a one-element array, or an `AtomicInteger` — genuinely compiles, because the *variable* is never reassigned even though the object it points at is mutated. That is section 3's "final is not immutability" arriving from the other direction, and it re-opens exactly the divergence the rule was closing, now including a data race if the lambda runs on another thread.

Also implicitly `final`, verbatim from JLS 21 §4.12.4: "Three kinds of variable are implicitly declared final: a field of an interface (§9.3), a local variable declared as a resource of a try-with-resources statement (§14.20.3), and an exception parameter of a multi-catch clause (§14.20). An exception parameter of a uni-catch clause is never implicitly declared final, but may be effectively final." So every interface field is `static final` whether you write it or not — which makes every interface `int`/`String` field initialized with a literal a constant variable, and section 1's hazard applies in full to the "interface full of constants" pattern.

> **Effectively final** — not declared `final`, never assigned after its initializer, never the operand of `++` or `--`. Capture is by value, so the language requires it rather than let two copies of a variable diverge.

### `final` on parameters and locals: bytecode-invisible, and still worth writing (1.14.11)

`[PROVE]` Measured: two classes whose only difference is `final` on both parameters of `public int f(final int stake, final String key)` compile to **byte-identical** `Code` attributes — `iload_1`, `aload_2`, `invokevirtual`, `iadd`, `ireturn` in both — and identical method flags, `(0x0001) ACC_PUBLIC`. There is no `ACC_FINAL` for a parameter in a method's access flags, and no attribute recording it under default compilation. The keyword is erased.

One honest nuance to that "no runtime effect": compile with `-parameters` and `javap -v` shows a `MethodParameters` attribute carrying the flag:

```
    MethodParameters:
      Name                           Flags
      stake                          final
```

So the fact survives as *reflective metadata* — `java.lang.reflect.Parameter.getModifiers()` can report it — but nothing in the instruction stream changes, no verifier check depends on it, and no JIT decision is informed by it. `final` on a parameter or local buys exactly two things: `javac` rejects an accidental reassignment inside the method body, and the variable is trivially capture-eligible for a lambda, which is a readability signal that the value is stable for the method's whole extent. On a parameter it is arguably redundant since the effectively-final rule already covers capture; on a long method with several similarly-typed locals it earns its keystrokes.

## Pitfalls

### Bumping a `static final int` and deploying only the declaring jar

**Wrong**

```java
// BonusRules.java — changed from 100 to 150 and rebuilt. BonusService NOT rebuilt.
public final class BonusRules {
    public static final int MAX_BONUS = 150;
    private BonusRules() { throw new AssertionError("no instances"); }
}
```

`javap -v BonusRules.class` confirms `ConstantValue: int 150`, and the deploy is green. But `javap -c BonusService.class` still reports `6: bipush 100`, and `java -cp out2 BonusService` prints `100`, not `150`. No exception, no `NoSuchFieldError`, no stderr output — the caller's class file never contained a reference to `MAX_BONUS`, so nothing was ever relinked.

**Right**

```java
public final class BonusRules {
    private static final int DEFAULT_MAX_BONUS_MINOR_UNITS = 150;
    private static volatile int maxBonusMinorUnits = DEFAULT_MAX_BONUS_MINOR_UNITS;

    /** A method call is never a constant expression, so no caller can inline the value. */
    public static int maxBonusMinorUnits() { return maxBonusMinorUnits; }

    private BonusRules() { throw new AssertionError("no instances"); }
}
```

Callers now compile to a real `invokestatic` against `maxBonusMinorUnits()`, resolved at link time, so replacing the `BonusRules` jar alone changes behaviour. The cost is real: the value is no longer usable as a `case` label or annotation element, reading it triggers `BonusRules`' class initialization, and `javac` can no longer fold it into surrounding arithmetic. Where the value must stay a compile-time constant, the only correct deploy is a full rebuild of every caller.

**Why people believe it:** every other field in Java *is* resolved at link time, so the model "one definition, many symbolic references" is right about 99% of the language — and `javap` of the declaring class shows the new value in plain sight, which feels like proof the change landed.

### Believing a `final Map` field gives you an immutable map

**Wrong**

```java
public final class ClientRestrictions {
    private final Map<RestrictionKey, Restriction> active = new HashMap<>();

    public Map<RestrictionKey, Restriction> leakyView() { return active; }
}

// Elsewhere, in code that "cannot possibly mutate anything":
clientRestrictions.leakyView().clear();
// Every restriction on the account is gone, SELF_EXCLUDED included.
// The field was final the whole time; javac raised nothing.
```

**Right**

```java
public final class ClientRestrictions {
    private final Map<RestrictionKey, Restriction> active = new HashMap<>();

    /** Unmodifiable snapshot: the caller cannot mutate, and cannot see later writes either. */
    public Map<RestrictionKey, Restriction> safeView() { return Map.copyOf(active); }
}
```

`final` locks the field's pointer; `Map.copyOf` is what locks the contents that leave the class. Two independent guarantees, neither of which substitutes for the other. JLS §4.12.4 says as much for arrays in the spec's own words: the components may be changed by operations on the array, but the variable always refers to the same array.

**Why people believe it:** `final` genuinely does deliver full immutability for `int`, `long` and `String` fields, which is what most examples use — so the model "final field = unchangeable value" survives every encounter until the first reference-typed field.

### `@Override`-ing a static method, or believing you did

**Wrong**

```java
class PromoBonusService extends BonusService {
    @Override
    static String rules() { return "PromoBonusService rules: cap 150"; }
}
// javac --release 21:
//   error: static methods cannot be annotated with @Override
```

Drop the annotation and it compiles — into something that is not an override:

```java
BonusService viaBase = new PromoBonusService();
System.out.println(viaBase.rules());   // prints "BonusService rules: cap 100"
```

`javap -c` shows `aload_1` / `pop` / `invokestatic BonusService.rules` — the receiver is pushed and discarded, and the target was fixed at compile time from `viaBase`'s declared type.

**Right**

```java
// If it must vary by subtype, it must be an instance method.
class BonusService {
    int maxBonusMinorUnits() { return 100; }
}

class PromoBonusService extends BonusService {
    @Override
    int maxBonusMinorUnits() { return 150; }
}
```

`invokevirtual` keeps the receiver on the stack and dispatches on its runtime class, so `((BonusService) new PromoBonusService()).maxBonusMinorUnits()` returns 150.

**Why people believe it:** static hiding uses the identical syntax to overriding — same signature, subclass, superclass — and the call site `viaBase.rules()` is spelled exactly like a virtual call. Nothing at the call site distinguishes the two; only `-Xlint:static`, which is off by default, says anything at all.

### Expecting a `NullPointerException` from a static call through a null reference

**Wrong**

```java
BonusService nullRef = null;
System.out.println(nullRef.rules());       // expected: NullPointerException
System.out.println("no NPE was thrown");
```

Measured output:

```
BonusService rules: cap 100
no NPE was thrown
```

The bytecode is `aconst_null` / `astore_2` / `aload_2` / `pop` / `invokestatic` — nothing in that sequence dereferences anything. Per JLS §15.12.4.1, a `static` method's qualifying expression is evaluated for side effects and its value discarded.

**Right**

```java
// If reaching a service through a possibly-null reference must fail loudly,
// the member has to be an instance member — then invokevirtual dereferences it.
BonusService service = null;
int cap = service.maxBonusMinorUnits();    // NullPointerException, as intended
```

Better still, do not qualify a static call with an expression at all: write `BonusService.rules()` and the question cannot arise. `-Xlint:static` reports every instance-qualified static call as `warning: [static] static method should be qualified by type name`.

**Why people believe it:** "dereferencing null throws NPE" is a correct and load-bearing rule, and `nullRef.rules()` looks exactly like a dereference. The `.` in a static call qualified by an expression is not a dereference operator — it is name resolution the compiler performs and then discards the qualifier.

## Cheat sheet

| Item | Value |
|---|---|
| Constant variable (JLS §4.12.4) | `final` + primitive or `String` + initialized with a constant expression — all three |
| Not a constant variable | non-`final`; `BigDecimal` or any reference type; initializer with a method call; concatenation involving a non-constant; a blank final |
| JLS §13.1 rule | A read of a constant variable **must** be resolved at compile time to its value |
| §13.1, `static` case | "no reference to the field should be present in the code in a binary file, **including the class which declared the field**" |
| §13.1, non-`static` case | Same rule for other classes; the declaring class sets the value during instance creation |
| §13.1, default value | "must never be observed" — the field always appears initialized |
| Class-file marker | `ConstantValue: int 100` on the field; absent for a non-constant `static final` |
| When `ConstantValue` is applied (JVMS §5.5) | By the JVM, **before** `<clinit>` runs, in class-file field order |
| Caller bytecode, constant form | `bipush 100` (or `sipush` / `ldc` by magnitude) — no `getstatic`, no `Fieldref` in the pool |
| Caller bytecode, fixed form | `getstatic #7 // Field BonusRules.MAX_BONUS:I`, plus a real `Fieldref` |
| Declaring class after the fix | `<clinit>`: `sipush 150` / `invokestatic Integer.valueOf` / `invokevirtual intValue` / `putstatic` |
| Stale-deploy proof | `BonusRules` at 150, `BonusService` unrecompiled → prints `100`; full rebuild → `150` |
| Cost of the fix | No `case` labels, no annotation values, triggers class init on read, no `javac` folding |
| `static` dispatch | `invokestatic` against the **compile-time** type; subclass statics **hide**, never override |
| `@Override` on a static | `error: static methods cannot be annotated with @Override` |
| Instance method vs superclass static | `error: cannot override [] overridden method is static` |
| `obj.staticMethod()` when `obj == null` | Runs normally; bytecode is `aload` / `pop` / `invokestatic` (JLS §15.12.4.1) |
| Lint for it | `-Xlint:static` — off unless enabled; `warning: [static] static method should be qualified by type name` |
| `final` on a variable | One assignment; the slot, never the pointee |
| `final` on a method | No subclass override; `ACC_FINAL`, verifier-enforced; **not** a performance hint |
| `final` on a class | No subclass; `ACC_FINAL`, verifier-enforced |
| `final` on a parameter/local | Byte-identical `Code`; only `MethodParameters` under `-parameters` records it |
| Freeze (JLS §17.5) | Occurs when the constructor writing the `final` field exits, normally **or abruptly** |
| Safe publication guarantee | A thread seeing the reference only after complete initialization sees correct `final` values |
| Its one precondition | `this` must not escape the constructor |
| `setAccessible` non-modifiable (JDK 21 javadoc) | `static final` in any class/interface; `final` in a hidden class; `final` in a record |
| Measured: `static final` write | `IllegalAccessException: Can not set static final int field` |
| Measured: instance `final` write | **Succeeds** on JDK 21 (JEP 500 warns by default in JDK 26) |
| Measured: record component write | `IllegalAccessException: Can not set final int field` |
| Interface fields | Implicitly `public static final` — so literal-initialized ones are constant variables |
| Implicitly final locals | try-with-resources resource; multi-catch exception parameter |
| Static nested vs inner | Static nested holds no enclosing reference; inner carries synthetic `this$0` — a retention leak |
| Utility class shape | `final class` + `private` constructor **throwing** `AssertionError` (reflection defeats a silent one) |
| Lambda capture | By value, at creation; hence the effectively-final requirement |
| Stale-cap cost, QuizStakes | ≤ 3,100 × 50 = **155,000/day** upper bound; true figure lower, average grant 42 < cap |

## Self-test

**Q1.** `BonusRules.MAX_BONUS` is bumped from 100 to 150 and only the `BonusRules` jar is redeployed. Nothing changes in production and no error appears anywhere. Explain the mechanism from the specification, not from "the compiler inlines constants".

<details><summary>Answer</summary>

`MAX_BONUS` is a *constant variable* under JLS 21 §4.12.4 — `final`, primitive, initialized with a constant expression. JLS §13.1 then states that a reference to such a field **must** be resolved at compile time to its value, and that if the field is `static`, "no reference to the field should be present in the code in a binary file, including the class or interface which declared the field." That is a requirement on the compiler, not an optimisation it may choose. So `BonusService.class` contains no `Fieldref` to `BonusRules.MAX_BONUS` at all; measured, `grant` compiles to `iload_1` / `bipush 10` / `idiv` / `istore_2` / `iload_2` / **`bipush 100`** / `invokestatic Math.min` / `ireturn`, with the literal `100` as an operand byte of an instruction in `BonusService`'s own method. There is nothing symbolic left for the JVM to relink, so no `NoSuchFieldError` or `IncompatibleClassChangeError` is possible — the silence is the JVM being correct, not the JVM failing to notice. Measured end to end: with `BonusRules` recompiled to `ConstantValue: int 150` and `BonusService` untouched, the program prints `100`; only after recompiling both does it print `150`. The fix is to recompile every caller, or to stop the field being a constant variable.

</details>

**Q2.** Make a `static final int` late-bound so callers pick up changes without recompiling. What exactly changes in the class files, and what do you give up?

<details><summary>Answer</summary>

Break one of §4.12.4's three conjuncts — most cheaply, the initializer: `public static final int MAX_BONUS = Integer.valueOf(150);` or, more readably, replace the field read with an accessor method, since a method call is never a constant expression. Measured, three things change. The field loses its `ConstantValue` attribute, so per JVMS §5.5 the JVM has nothing to pre-populate before `<clinit>`. `javac` synthesises a `<clinit>` that does `sipush 150` / `invokestatic Integer.valueOf` / `invokevirtual intValue` / `putstatic MAX_BONUS:I`. And the caller now compiles to `getstatic #7 // Field BonusRules.MAX_BONUS:I` with a real `Fieldref` back in its constant pool — a symbolic reference that link-time resolution acts on, which is precisely why swapping the declaring jar now works. The declaring class's own read becomes a `getstatic` too. What you give up: the value can no longer appear as a `case` label, an annotation element, or anywhere else demanding a constant expression; reading it now triggers `BonusRules`' class initialization, so any `static` block ordering or failure semantics come into play; `javac` can no longer fold it into surrounding arithmetic; and the guaranteed constant propagation becomes merely likely — HotSpot does trust `static final` fields for folding once the class is initialized, but that is JIT behaviour, not a language guarantee.

</details>

**Q3.** `BonusService nullRef = null; nullRef.rules();` where `rules()` is `static`. What happens, and why?

<details><summary>Answer</summary>

It runs normally and prints `BonusService rules: cap 100`. No `NullPointerException`. JLS §15.12.4.1: when the invoked method is `static`, the qualifying expression is evaluated for its side effects and the resulting value is then discarded. The bytecode makes it literal — `aconst_null` / `astore_2` / `aload_2` / **`pop`** / `invokestatic #16 // Method BonusService.rules:()Ljava/lang/String;`. `aload` loads a reference without dereferencing it, `pop` cannot fail, and `invokestatic` takes no receiver, so no instruction in the sequence dereferences anything. The `invokestatic` at that offset is byte-identical to the one emitted for the same call through a genuine, non-null instance. Note the qualifier's *side effects* do still happen: `nextIndex().staticMethod()` calls `nextIndex()`. `-Xlint:static` warns on the pattern, but it is off by default.

</details>

**Q4.** Given `BonusService` with `static String rules()` and `PromoBonusService extends BonusService` with its own `static String rules()`, what does `((BonusService) new PromoBonusService()).rules()` return, and what is the refactoring hazard?

<details><summary>Answer</summary>

It returns `BonusService`'s version — cap 100 — because a `static` method invocation compiles to `invokestatic` naming the method against the *compile-time* type of the qualifier. There is no vtable slot and no runtime lookup; the receiver is pushed and immediately discarded (`aload_1` / `pop` / `invokestatic BonusService.rules`). Two independent methods exist and the subclass's one *hides* the superclass's rather than overriding it — `@Override` on it is a hard compile error (`static methods cannot be annotated with @Override`), and crossing the boundary the other way is also an error (`cannot override [] overridden method is static`). The refactoring hazard: the entire input to the decision is the declared type of the qualifier, so a maintainer who changes `BonusService viaBase = ` to `PromoBonusService viaBase = ` silently changes which method an *unmodified* call line invokes — cap 100 becomes cap 150 — with no diff on the call site. If the value must vary by subtype it has to be an instance method dispatched via `invokevirtual`.

</details>

**Q5.** `private final Map<RestrictionKey, Restriction> active = new HashMap<>();` — precisely what does `final` guarantee, and what does it not?

<details><summary>Answer</summary>

It guarantees that the field is assigned exactly once and will point at that same `HashMap` instance for the object's entire life, and — via JLS §17.5 — that a thread obtaining the object's reference only after the constructor exits sees that same non-null map rather than `null`. It guarantees nothing whatsoever about the map's contents: `put`, `remove` and `clear` are all legal on it and `javac` raises nothing, because `final` locks the slot and never reaches into the pointee. JLS §4.12.4 states the same thing for arrays verbatim — the components may be changed by operations on the array, but the variable always refers to the same array. It also guarantees nothing about thread safety; the map is now safely *published* shared mutable state, which two threads can still corrupt structurally. The concrete failure: an accessor returning the field directly hands a caller the live map, and `clear()` on it lifts every restriction on the account including `SELF_EXCLUDED`, whose `reversibleByOperator = false` was supposed to make that impossible. Two independent fixes are needed: `final` for the pointer, and an unmodifiable type or a `Map.copyOf` snapshot for whatever leaves the class.

</details>

**Q6.** Can reflection change a `final` field on JDK 21? Answer for all three of: a `static final` field, an instance `final` field of an ordinary class, and a record component.

<details><summary>Answer</summary>

Two of the three, no; one, yes. The `Field.setAccessible` javadoc on Java 21 states that the method cannot be used to enable write access to a non-modifiable final field, and lists exactly three non-modifiable kinds: `static final` fields declared in any class or interface, `final` fields declared in a hidden class, and `final` fields declared in a record — for these, `setAccessible(true)` enables read access only. Measured, matching that list exactly: writing a non-constant `static final int MAX_BONUS` throws `IllegalAccessException: Can not set static final int field BonusRules.MAX_BONUS to (int)150`; writing `final int minor` on `record Money(int minor)` throws `IllegalAccessException: Can not set final int field Money.minor to (int)1`; and writing `final int stakeMinor` on an ordinary `final class Reservation` **succeeds**, changing 420 to 999. So on JDK 21 an instance `final` field of an ordinary class is a compile-time guarantee the runtime does not enforce, while `static final` and record components are enforced. That gap is being closed: JEP 500 adds `--illegal-final-field-mutation`, warning by default in JDK 26 with denial planned later.

</details>

**Q7.** What does the `final`-field freeze guarantee, and what breaks it?

<details><summary>Answer</summary>

JLS 21 §17.5 defines a *freeze* action on a `final` field of an object as taking place when the constructor that writes it exits — "either normally or abruptly", so it happens even when the constructor throws. The guarantee is then: "A thread that can only see a reference to an object after that object has been completely initialized is guaranteed to see the correctly initialized values for that object's `final` fields." Practically: a `Reservation` whose `stake` and `split` are both `final` can be published through a plain non-`volatile` `static` field with no lock, and any thread that reads a non-null reference from it is guaranteed to see the constructor's values rather than `null` or a torn intermediate. The precondition is the spec's own usage rule: set the `final` fields in the constructor, and do not write a reference to the object being constructed anywhere another thread could see it before the constructor finishes. Writing `inFlight = this;` as the first statement of a constructor breaks it exactly — the reference escapes before the field is assigned, no freeze has occurred, and a reader can obtain a non-null object and legitimately observe the `final` field at its default value. Two things the freeze does *not* give you: timely visibility of the *reference* itself (that is `volatile`'s job), and any thread safety at all for the mutable object a `final` field might point at.

</details>

**Q8.** Why does a lambda require a captured local to be effectively final, and why does the one-element-array workaround compile?

<details><summary>Answer</summary>

Capture is **by value**: the value of the local is copied into the lambda's synthetic capture at the moment the lambda instance is created, because the enclosing method's frame may have exited long before the lambda body runs. There is therefore no mechanism by which a later reassignment of the local could be visible inside the lambda, nor a reassignment inside the lambda visible outside — two independent copies would exist and silently diverge. Rather than specify which copy wins, the language forbids the situation: the variable must be effectively final, meaning per JLS §4.12.4 that it is not declared `final`, never appears as the left-hand side of an assignment expression, and is never the operand of `++` or `--`. The `int[] counter = new int[1]` workaround compiles because the *variable* `counter` genuinely is never reassigned — only the array's component is mutated — and the effectively-final rule constrains the variable, not the pointee. That is "final is not immutability" arriving from the capture side, and it reintroduces exactly the divergence the rule was preventing, plus an unsynchronised data race if the lambda runs on another thread. Also implicitly final and therefore always capture-eligible: interface fields, try-with-resources resources, and multi-catch exception parameters.

</details>

**Q9.** Does `final` on a method parameter do anything at runtime?

<details><summary>Answer</summary>

No instruction-level anything. Measured: two classes whose only difference is `final` on both parameters of `public int f(final int stake, final String key)` produce byte-identical `Code` attributes — `iload_1` / `aload_2` / `invokevirtual String.length` / `iadd` / `ireturn` — and identical method access flags, `(0x0001) ACC_PUBLIC`. There is no `ACC_FINAL` bit for a parameter in a method's access flags. One nuance keeps the claim honest: compiled with `-parameters`, `javap -v` shows a `MethodParameters` attribute listing `stake` with flag `final`, so the fact does survive as reflective metadata readable through `java.lang.reflect.Parameter.getModifiers()`. But no verifier check depends on it and no JIT decision is informed by it. What it actually buys: `javac` rejects an accidental reassignment inside the method body, and the parameter is trivially capture-eligible for a lambda — a readability signal that the value is stable for the method's whole extent. On a parameter it is close to redundant, since the effectively-final rule already covers capture; on a long method with several similarly-typed locals it earns itself.

</details>

## Open questions

- No JDK 21 runtime was available on this machine. All class files were produced with `javac --release 21` (major version 65) and executed on Oracle GraalVM 25.0.1+8.1, HotSpot, macOS aarch64. Class-file structure and bytecode are the JDK 21 target and are `--release`-guaranteed; the runtime measurements (the stale-constant output, the `-Xlint:static` warnings, the three `setAccessible` results) were taken on the 25 runtime and match the JDK 21 specification and javadoc text quoted, but were not re-run on a 21 runtime.
- The dangling `#7 = Class BonusRules` entry in `BonusService`'s constant pool, referenced by no instruction after the constant was inlined, is marked **Unverified** above: I could not locate a JLS or JVMS clause that requires or forbids it, so I state it as an observed `javac` artifact rather than specified behaviour.
- The claim that HotSpot's JIT trusts a `static final` field for constant folding once its holder class is initialized, and does not unconditionally trust an instance `final` field, is stated as JIT behaviour rather than a specification guarantee. It is not derived from primary source in this file; `04-internals-final-and-constant-folding.md` owns the evidence.

---

**Leaves covered:** 1.14.1, 1.14.2, 1.14.3, 1.14.4, 1.14.5, 1.14.6, 1.14.7, 1.14.8, 1.14.9, 1.14.10, 1.14.11 (11 leaves)
**Leaves deferred:** none
**Diagrams included:** D-042
**Target version:** Java 21 LTS
**Lines:** 812
