# 03 Java Core — The boxing bytecode — INTERNALS (§3.4, 3.4.7)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [The other wrapper caches](03b-internals-the-other-wrapper-caches.md) · Next: [Escape analysis](03d-internals-escape-analysis.md)

There is no boxing instruction. The JVM's opcode table has nothing in it for "convert this `int` to an `Integer`", and nothing for the reverse. What exists instead is `javac` inserting a call — a static factory call one way, an instance method call the other way — at every point in your source where the language says a conversion happens. That is the whole mechanism, and every downstream fact about boxing is a consequence of it.

[`01-basics.md`](01-basics.md) established that autoboxing is a compiler rewrite and showed the two-instruction listing for it. [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md) walked the boxed accumulator's loop and did the allocation arithmetic. Neither is re-derived here. This file owns the other half: the complete catalogue of *where* `javac` puts the call, read instruction by instruction, including the contexts where it turns out to emit nothing at all.

Everything below was captured with `javap -p -c` on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, from QuizStakes-named source, and is pasted verbatim. Where a listing shows a surprising result — the concatenation case and the `switch` case both did — it is reported as measured rather than smoothed.

---

## 1. Every box is one `invokestatic`, every unbox is one `invokevirtual` (3.4.7)

`[BYTECODE]` `[RESEARCH]` The picture: imagine `javac` walking your method's abstract syntax tree with two rubber stamps. Wherever the tree says "a primitive value is standing in a place that wants a reference", it stamps `invokestatic Wrapper.valueOf`. Wherever the tree says "a reference is standing in a place that wants a primitive", it stamps `invokevirtual Wrapper.xxxValue`. It stamps nothing else, it changes nothing else, and the bytecode it produces is indistinguishable from bytecode you would have got by writing those calls out by hand.

Two consequences fall straight out of that, and they are the reason the model is worth holding precisely.

**`invokestatic` has no receiver, so boxing cannot throw.** `Integer.valueOf(int)` takes an `int` on the operand stack and returns a reference. There is no object to be null. The only failure mode is `OutOfMemoryError`, which is not a boxing-specific one.

**`invokevirtual` has a receiver, so unboxing can throw `NullPointerException`.** `Integer.intValue()` needs an `Integer` on the stack to invoke on. If that reference is null, the invoke throws before the method body is entered. That is the entire explanation of the NPE at a source line containing no visible call — the case owned by [`01c-unboxing-null.md`](01c-unboxing-null.md).

**Insight:** because these are ordinary calls into ordinary library methods, boxing gets no special treatment from the JVM and therefore needs none. The cache is a plain array read inside a plain method. Inlining applies to it like any other small static method. Escape analysis applies to the allocation it performs like any other allocation. If boxing were an opcode, the JIT would need bespoke machinery to eliminate it; because it is a method call, the machinery that already exists is sufficient. That is why the boxes in a hot method can vanish entirely, which is [`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md).

### Why it exists

Erasure. A generic type parameter compiles to its bound — `Object` in the unbounded case — so `Map<String, Integer>` is `Map<Object, Object>` at the bytecode level and `Map.get` really does return `Ljava/lang/Object;`. A generic API can therefore only ever traffic in references, and the only way to get an `int` into one is to have some code produce a reference that carries the `int`'s value. A JVM opcode could in principle have done that job, but it would have had to hard-code a policy: which class to instantiate, whether to consult a cache, what the cache bounds are. Putting the conversion in a library method leaves all of that in Java, versionable and tunable — which is exactly what `IntegerCache`'s configurable `high` and its CDS archived subgraph then take advantage of. The mechanism paragraph on erasure you need is the one above; the full treatment is the erasure chapter of this topic, which is not yet written.

So the design is: the language defines the conversion contexts (JLS 21 §5.1.7 boxing, §5.1.8 unboxing), `javac` finds them, and a library method does the work. **When to reach for `javap`, and when not:** reach for it to answer *where* and *whether* a conversion is emitted, which is a compile-time fact and completely determined by the listing. Do not reach for it to answer *what a conversion costs*, which is a runtime fact and not visible in the listing at all — that needs an allocation measurement, and the gotcha below is about people who conflate the two.

### The mechanism

The catalogue, as a table first. Each row was measured; the listings follow.

| Context | Source shape | Emitted | The thing to notice |
|---|---|---|---|
| Assignment, boxing | `Integer retryCount = uploads;` | `invokestatic Integer.valueOf:(I)Ljava/lang/Integer;` | two instructions total including the load |
| Assignment, unboxing | `int uploads = retryCount;` | `invokevirtual Integer.intValue:()I` | the receiver is what makes NPE possible |
| Invocation, boxing | `reserve(uploads)` where `reserve(Integer)` | `invokestatic Integer.valueOf` **before** the call | emitted in the **caller**, not the callee |
| Invocation, unboxing | `settle(retryCount)` where `settle(int)` | `invokevirtual Integer.intValue` before the call | same: caller-side |
| Generic read | `positionsByType.get(code)` used as `int` | `invokeinterface Map.get`, `checkcast Integer`, `invokevirtual intValue` | two separate insertions, two distinct failure modes |
| Generic write | `map.put(code, used + 1)` | `iadd` then `invokestatic Integer.valueOf` | the arithmetic is primitive; only the store boxes |
| Compound assignment | `sum += minorUnits` on a `Long` | `longValue`, `i2l`, `ladd`, `valueOf`, `astore` | four conversion instructions around one arithmetic one |
| `new Integer(3)` | explicit constructor | `new`, `dup`, `iconst_3`, `invokespecial <init>` | a **different opcode**, trivially distinguishable |
| `Integer.valueOf(3)` | explicit factory | `iconst_3`, `invokestatic valueOf` | what autoboxing emits, identically |
| `switch` on `Integer` | `switch (retryCount)` | **one** `invokevirtual intValue`, then `tableswitch` | unboxed once, not per case |
| String concatenation | `"…" + retryCount` | `invokedynamic makeConcatWithConstants:(Ljava/lang/Integer;)…` | **no box, no unbox, no `toString`** |
| `==`, both wrappers | `left == right` | `if_acmpne` | reference comparison, no conversion at all |
| `==`, mixed | `left == right` with `int right` | `invokevirtual intValue`, `if_icmpne` | numeric comparison, and it can throw |

#### The assignment pair, both directions

Source:

```java
static Integer boxRetryCount(int uploads) {
    Integer retryCount = uploads;
    return retryCount;
}
static int unboxRetryCount(Integer retryCount) {
    int uploads = retryCount;
    return uploads;
}
```

Measured:

```
  static java.lang.Integer boxRetryCount(int);
    Code:
       0: iload_0
       1: invokestatic  #7                  // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
       4: astore_1
       5: aload_1
       6: areturn

  static int unboxRetryCount(java.lang.Integer);
    Code:
       0: aload_0
       1: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
       4: istore_1
       5: iload_1
       6: ireturn
```

Read every instruction, because the *prefixes* carry the whole story. In the boxing method: `iload_0` — `i` for integral, load slot 0, the `int` parameter, pushing four bytes of primitive onto the operand stack. `invokestatic #7` — resolve constant-pool entry 7 to `Integer.valueOf:(I)Ljava/lang/Integer;`, pop one `int`, push one reference. The descriptor `(I)Ljava/lang/Integer;` is the conversion, spelled out: `I` in, a reference out. `astore_1` — `a` for reference, store to slot 1, the local `retryCount`. `aload_1`, `areturn` — push it back and return it as a reference. Note that the opcode prefix flips from `i` to `a` exactly at the `invokestatic`: before it the value is a primitive, after it the value is a reference, and the call is the boundary.

In the unboxing method the same flip runs the other way. `aload_0` pushes the `Integer` reference. `invokevirtual #13` pops it as the *receiver*, dispatches `intValue()`, pushes an `int`. Descriptor `()I` — no arguments, an `int` out; the input is the receiver, not a parameter, which is precisely why null is a problem here and not in the boxing direction. Then `istore_1`, `iload_1`, `ireturn`, all `i`-prefixed. The `astore`/`aload` and `istore`/`iload` round trips are the unoptimised locals the compiler emits for the named variables; `javac` does no register coalescing and leaves that to the JIT.

**Interview:** *"What does autoboxing compile to?"* One `invokestatic Wrapper.valueOf` with descriptor `(<primitive>)L<Wrapper>;` at the conversion site; auto-unboxing compiles to one `invokevirtual Wrapper.xxxValue` with descriptor `()<primitive>`. There is no boxing opcode; both are ordinary method calls that `javac` inserts.

#### All eight wrappers, verified rather than recalled

One method assigning eight primitives into eight wrappers and one method doing the reverse, compiled and read on JDK 21.0.7. The boxing side:

```
  static java.lang.Object boxAllEight(int, long, byte, short, char, boolean, float, double);
    Code:
       0: iload_0
       1: invokestatic  #7                  // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
       4: astore        10
       6: lload_1
       7: invokestatic  #17                 // Method java/lang/Long.valueOf:(J)Ljava/lang/Long;
      10: astore        11
      12: iload_3
      13: invokestatic  #22                 // Method java/lang/Byte.valueOf:(B)Ljava/lang/Byte;
      16: astore        12
      18: iload         4
      20: invokestatic  #27                 // Method java/lang/Short.valueOf:(S)Ljava/lang/Short;
      23: astore        13
      25: iload         5
      27: invokestatic  #32                 // Method java/lang/Character.valueOf:(C)Ljava/lang/Character;
      30: astore        14
      32: iload         6
      34: invokestatic  #37                 // Method java/lang/Boolean.valueOf:(Z)Ljava/lang/Boolean;
      37: astore        15
      39: fload         7
      41: invokestatic  #42                 // Method java/lang/Float.valueOf:(F)Ljava/lang/Float;
      44: astore        16
      46: dload         8
      48: invokestatic  #47                 // Method java/lang/Double.valueOf:(D)Ljava/lang/Double;
      51: astore        17
      53: aload         10
      55: areturn
```

Three details in that listing that are not about boxing but are worth having. `byte`, `short`, `char` and `boolean` are all loaded with `iload` — the JVM has no separate load opcode for them, they live in `int`-shaped slots, and the descriptor `(B)`, `(S)`, `(C)`, `(Z)` is the only thing that distinguishes which `valueOf` overload gets picked. `long` and `double` take two local-variable slots each, which is why the parameter slots run 0, 1, 3, 4, 5, 6, 7, 8 rather than 0 through 7. And `astore 10` uses the wide two-byte form because slot 10 is past `astore_0` through `astore_3`.

The unboxing side:

```
  static double unboxAllEight(java.lang.Integer, java.lang.Long, java.lang.Byte, java.lang.Short, java.lang.Character, java.lang.Boolean, java.lang.Float, java.lang.Double);
    Code:
       0: aload_0
       1: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
       4: istore        8
       6: aload_1
       7: invokevirtual #52                 // Method java/lang/Long.longValue:()J
      10: lstore        9
      12: aload_2
      13: invokevirtual #56                 // Method java/lang/Byte.byteValue:()B
      16: istore        11
      18: aload_3
      19: invokevirtual #60                 // Method java/lang/Short.shortValue:()S
      22: istore        12
      24: aload         4
      26: invokevirtual #64                 // Method java/lang/Character.charValue:()C
      29: istore        13
      31: aload         5
      33: invokevirtual #68                 // Method java/lang/Boolean.booleanValue:()Z
      36: istore        14
      38: aload         6
      40: invokevirtual #72                 // Method java/lang/Float.floatValue:()F
      43: fstore        15
      45: aload         7
      47: invokevirtual #76                 // Method java/lang/Double.doubleValue:()D
      50: dstore        16
```

So the full verified set, from those two listings:

| Primitive | Boxing instruction | Unboxing instruction |
|---|---|---|
| `int` | `invokestatic java/lang/Integer.valueOf:(I)Ljava/lang/Integer;` | `invokevirtual java/lang/Integer.intValue:()I` |
| `long` | `invokestatic java/lang/Long.valueOf:(J)Ljava/lang/Long;` | `invokevirtual java/lang/Long.longValue:()J` |
| `byte` | `invokestatic java/lang/Byte.valueOf:(B)Ljava/lang/Byte;` | `invokevirtual java/lang/Byte.byteValue:()B` |
| `short` | `invokestatic java/lang/Short.valueOf:(S)Ljava/lang/Short;` | `invokevirtual java/lang/Short.shortValue:()S` |
| `char` | `invokestatic java/lang/Character.valueOf:(C)Ljava/lang/Character;` | `invokevirtual java/lang/Character.charValue:()C` |
| `boolean` | `invokestatic java/lang/Boolean.valueOf:(Z)Ljava/lang/Boolean;` | `invokevirtual java/lang/Boolean.booleanValue:()Z` |
| `float` | `invokestatic java/lang/Float.valueOf:(F)Ljava/lang/Float;` | `invokevirtual java/lang/Float.floatValue:()F` |
| `double` | `invokestatic java/lang/Double.valueOf:(D)Ljava/lang/Double;` | `invokevirtual java/lang/Double.doubleValue:()D` |

Note the two names that break the pattern people expect. Six of the unboxing methods are `Number`'s — `intValue`, `longValue`, `byteValue`, `shortValue`, `floatValue`, `doubleValue` are declared on `java.lang.Number`, which is where the `xxxValue` convention comes from. `Character.charValue()` and `Boolean.booleanValue()` are **not** on `Number`, because `Character` and `Boolean` do not extend `Number` at all: their declarations are `public final class Character implements java.io.Serializable, Comparable<Character>, Constable` and `public final class Boolean implements java.io.Serializable, Comparable<Boolean>, Constable`. They happen to follow the naming convention, but they are independent methods on unrelated classes, which is why you cannot write a generic unboxer over `Number` that handles all eight.

#### The invocation context, and where the box lives

The box is emitted at the *call site*, in the caller's method body, not in the callee. Measured with two `PaymentService` builds and a `FundsLedger` caller compiled against each, changing nothing in the caller's source. Compiled against a `PaymentService` declaring only `reserve(int)`:

```
  public static void reserveStake(java.lang.Integer);
    Code:
       0: aload_0
       1: invokevirtual #7                  // Method java/lang/Integer.intValue:()I
       4: invokestatic  #13                 // Method PaymentService.reserve:(I)V
       7: return
```

Recompiled against a `PaymentService` that additionally declares `reserve(Integer)`:

```
  public static void reserveStake(java.lang.Integer);
    Code:
       0: aload_0
       1: invokestatic  #7                  // Method PaymentService.reserve:(Ljava/lang/Integer;)V
       4: return
```

**Insight:** adding a boxed overload to a library changes the *caller's* bytecode, and only when the caller is recompiled. The first listing's `invokevirtual intValue` is baked into `FundsLedger.class`; deploying the new `PaymentService` next to the old `FundsLedger.class` keeps the unbox and keeps dispatching to `reserve(I)`, because that is what the constant pool says. This is a source-compatible but behaviour-relevant change that a rebuild silently applies. Overload resolution itself is JLS §15.12.2 and lives in [`../primitives-and-conversions/03a-promotion-boxing-and-inference.md`](../primitives-and-conversions/03a-promotion-boxing-and-inference.md); the point here is only that the conversion is compiled into the caller.

#### The generic call: two insertions on one source line

```java
static int reservedBonus(Map<String, Integer> positionsByType) {
    return positionsByType.get("CLIENT_BONUS_RESERVED");
}
```

```
  static int reservedBonus(java.util.Map<java.lang.String, java.lang.Integer>);
    Code:
       0: aload_0
       1: ldc           #90                 // String CLIENT_BONUS_RESERVED
       3: invokeinterface #92,  2           // InterfaceMethod java/util/Map.get:(Ljava/lang/Object;)Ljava/lang/Object;
       8: checkcast     #8                  // class java/lang/Integer
      11: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
      14: ireturn
```

Be precise about which instruction is which compiler insertion. The `invokeinterface` descriptor is `(Ljava/lang/Object;)Ljava/lang/Object;` — the erased signature, with no trace of `String` or `Integer`. The `checkcast Integer` at offset 8 is the **erasure** artefact: `javac` knows statically that the value is an `Integer` and inserts the cast that the erased return type makes necessary. The `invokevirtual intValue` at offset 11 is the **unboxing** insertion, driven by the `int` return type of the enclosing method. Two distinct insertions, from two distinct language rules, on one source line with no visible cast and no visible call.

That is why the line has two distinct ways to fail. A map that is not really `Map<String, Integer>` — a raw reference, or one that crossed an unchecked boundary — fails at offset 8 with `ClassCastException`. A map that is genuinely `Map<String, Integer>` but has no entry for that key, or has a null value, fails at offset 11 with `NullPointerException`. Measured, calling it with an empty map:

```
java.lang.NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because the return value of "java.util.Map.get(Object)" is null
	at BoxProbe.reservedBonus(BoxProbe.java:24)
```

The helpful message names `intValue()`, a method the source does not mention, and names `Map.get(Object)` with the erased signature. Helpful NPE messages are on by default since Java 15 (JEP 358); before 15 the same line produced a bare `NullPointerException` with no message unless `-XX:+ShowCodeDetailsInExceptionMessages` was passed, which is why older stack traces for this failure are so hard to read.

#### Compound assignment: four conversion instructions around one arithmetic one

```java
static long sumStakeMinorUnitsBoxed(int[] stakeMinorUnits) {
    Long sum = 0L;
    for (int minorUnits : stakeMinorUnits) {
        sum += minorUnits;
    }
    return sum;
}
```

The loop body, offsets 25 to 36 of the measured listing:

```
      25: aload_1
      26: invokevirtual #22                 // Method java/lang/Long.longValue:()J
      29: iload         5
      31: i2l
      32: ladd
      33: invokestatic  #17                 // Method java/lang/Long.valueOf:(J)Ljava/lang/Long;
      36: astore_1
```

`aload_1` pushes the boxed `sum`. `longValue()` unboxes it to a `long` on the stack. `iload 5` pushes the loop's `int` element and `i2l` widens it — a widening primitive conversion, not a boxing one, and free. `ladd` is the one instruction that does the arithmetic the source asked for. `invokestatic Long.valueOf:(J)Ljava/lang/Long;` reboxes the result, and `astore_1` writes the new reference back over the variable. Four conversion instructions bracketing one `ladd`, per iteration, because `sum` is declared `Long` and the JVM cannot add references.

JLS §15.26.2 is what forces this shape: a compound assignment `E1 op= E2` is defined as `E1 = (T)(E1 op E2)` with `T` the type of `E1`, so the unbox-add-rebox round trip is the specification's own reading of the operator and not a compiler choice. What it costs — one `Long` per iteration, and the measured allocation totals behind that — is [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md), which does the arithmetic in full.

#### `new Integer(3)` versus `Integer.valueOf(3)`

Both compiled in the same class, measured:

```
  static java.lang.Integer legacyRetryCount();
    Code:
       0: new           #7                  // class java/lang/Integer
       3: dup
       4: iconst_3
       5: invokespecial #9                  // Method java/lang/Integer."<init>":(I)V
       8: areturn

  static java.lang.Integer modernRetryCount();
    Code:
       0: iconst_3
       1: invokestatic  #12                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
       4: areturn
```

The legacy form: `new` allocates an uninitialised `Integer` and pushes its reference; `dup` copies it because `invokespecial` will consume one copy as the receiver and the other is the method's result; `iconst_3` pushes the argument; `invokespecial <init>:(I)V` runs the constructor, returning nothing. Four instructions and an unconditional heap allocation. The modern form is two instructions and, for a value in the cache, an array read with no allocation at all.

The instruction-level difference matters beyond the allocation. `invokespecial` on `<init>` and `invokestatic` on `valueOf` are **different opcodes with different constant-pool entry kinds** — `Methodref` naming `<init>` versus `Methodref` naming `valueOf` — so a decompiler, a bytecode-rewriting agent, or a static analyser can distinguish them without any type inference or dataflow. A migration tool that wants to find every remaining terminally-deprecated wrapper construction in a large estate does not need source at all; it scans class files for `invokespecial` against `java/lang/Integer."<init>"` and friends. Why those constructors are deprecated for removal, and what the compiler warning looks like, is [`01e-valueof-and-the-deprecated-constructors.md`](01e-valueof-and-the-deprecated-constructors.md).

#### The contexts that emit no box at all

This is the half nobody checks, and two of the three results are not what a guess would produce. All three measured on JDK 21.0.7.

**A `switch` on a boxed selector unboxes once, not per case.**

```java
static String routeRetryCount(Integer retryCount) {
    switch (retryCount) {
        case 0:  return "AA-600 DOCUMENTS_REQUESTED";
        case 1:  return "AA-610 DOCUMENTS_UPLOADED";
        case 2:  return "AA-650 DOCUMENTS_REFERRED";
        default: return "AA-699 DOCUMENTS_EXHAUSTED";
    }
}
```

```
  static java.lang.String routeRetryCount(java.lang.Integer);
    Code:
       0: aload_0
       1: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
       4: tableswitch   { // 0 to 2
                     0: 32
                     1: 35
                     2: 38
               default: 41
          }
      32: ldc           #100                // String AA-600 DOCUMENTS_REQUESTED
      34: areturn
      35: ldc           #102                // String AA-610 DOCUMENTS_UPLOADED
      37: areturn
      38: ldc           #104                // String AA-650 DOCUMENTS_REFERRED
      40: areturn
      41: ldc           #106                // String AA-699 DOCUMENTS_EXHAUSTED
      43: areturn
```

One `invokevirtual intValue` at offset 1, then a plain dense `tableswitch` on the resulting `int`. The selector is unboxed exactly once and the case labels are primitive `int` constants — there is no `Integer.equals` anywhere, and no comparison against a boxed constant. JLS §14.11 is the reason: the switch selector undergoes unboxing conversion, so the switch is an `int` switch by the time the labels are considered. The consequence worth carrying: **a null selector throws at offset 1, before any label is examined, and `default` does not catch it.** Measured with a `HashMap` entry whose value is null:

```
switch  -> java.lang.NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<parameter1>" is null
```

**A boxed value in a string concatenation is neither boxed nor unboxed.** This one is the genuine surprise:

```
  static java.lang.String auditLine(java.lang.Integer);
    Code:
       0: aload_0
       1: invokedynamic #108,  0            // InvokeDynamic #0:makeConcatWithConstants:(Ljava/lang/Integer;)Ljava/lang/String;
       6: areturn

  static java.lang.String auditLinePrimitive(int);
    Code:
       0: iload_0
       1: invokedynamic #112,  0            // InvokeDynamic #0:makeConcatWithConstants:(I)Ljava/lang/String;
       6: areturn
```

The reference goes straight into the `invokedynamic` with descriptor `(Ljava/lang/Integer;)Ljava/lang/String;`. No `intValue`, no `valueOf`, and no `Integer.toString` or `String.valueOf` call in the bytecode either — `java.lang.invoke.StringConcatFactory`'s bootstrap method builds the whole concatenation as a `MethodHandle` chain at first execution, and it handles a reference argument by inserting the `String.valueOf(Object)` step inside that chain, where the class file cannot see it. Two things follow. Concatenating a boxed value is not a boxing cost at all, and the pre-Java-9 folklore that `"" + someInteger` "boxes and calls `toString`" is a version trap: on JDK 21 there is no box because there was already a reference, and the `toString` happens inside the bootstrap. And concatenating a **null** boxed value does not throw:

```
concat  -> AA-650 DOCUMENTS_REFERRED retries=null
```

`String.valueOf(Object)` maps null to the four characters `null`, so a null `Integer` in a log line is silently rendered rather than reported — which makes concatenation the one context where a null box is not a bug report.

**`==` between two wrappers emits no conversion; mixed `==` emits one unbox.**

```
  static boolean sameRetryCountRef(java.lang.Integer, java.lang.Integer);
    Code:
       0: aload_0
       1: aload_1
       2: if_acmpne     9
       5: iconst_1
       6: goto          10
       9: iconst_0
      10: ireturn

  static boolean sameRetryCountMixed(java.lang.Integer, int);
    Code:
       0: aload_0
       1: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
       4: iload_1
       5: if_icmpne     12
       8: iconst_1
       9: goto          13
      12: iconst_0
      13: ireturn
```

`if_acmpne` versus `if_icmpne` — one opcode letter, and the entire semantic difference. The wrapper-to-wrapper form pushes two references and compares them for reference identity; there is no conversion instruction in the method at all, which is why the cache boundary at 127 decides the answer ([`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md)). The mixed form unboxes the left operand and compares numerically, which is why it is always value-correct and why it can throw. Measured on the same null `Integer` that the reference form tolerated:

```
mixed== -> java.lang.NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<parameter1>" is null
ref==   -> true
```

Note the evaluation order in the mixed listing: `aload_0`, then `intValue`, then `iload_1`. The unbox of the left operand happens before the right operand is even pushed, which is JLS §15.7.1 left-to-right evaluation showing through, and it means the NPE fires even when the right operand would have made the comparison irrelevant.

**Interview:** *"Why can unboxing throw but boxing cannot?"* Boxing is `invokestatic Integer.valueOf(int)` — a static call with no receiver, taking a primitive that cannot be null. Unboxing is `invokevirtual Integer.intValue()` — a virtual call whose only input is the receiver, so a null reference throws `NullPointerException` at the invoke, before the method body runs. Hence the guard belongs on the reference side of the conversion, and hence `nullInteger == 5` throws while `nullInteger == otherInteger` compiles to `if_acmpne` and returns false.

### Diagram

No diagram for this concept: the listings are the picture. A drawing of an `invokestatic` would be strictly less informative than the four lines of `javap` it replaced, and the whole method read below is the closest thing to a diagram this material has.

### A concrete example

One `DocumentRequirements` method, read end to end. It is the retry-count path from the document-verification flow: look up how many uploads a requirement has already had, and either start the count, advance it, or report the requirement exhausted at `AA-699`.

```java
public class DocumentRequirements {

    private static final int MAX_RETRIES = 3;

    public static String recordUpload(Map<String, Integer> retriesByRequirement,
                                      String requirementCode) {
        Integer retries = retriesByRequirement.get(requirementCode);
        if (retries == null) {
            retriesByRequirement.put(requirementCode, 1);
            return "AA-610 DOCUMENTS_UPLOADED";
        }
        int used = retries;
        if (used >= MAX_RETRIES) {
            return "AA-699 DOCUMENTS_EXHAUSTED";
        }
        retriesByRequirement.put(requirementCode, used + 1);
        return "AA-610 DOCUMENTS_UPLOADED";
    }

    private static int remaining(Integer retries) {
        return MAX_RETRIES - retries;
    }
}
```

Measured in full with `javap -p -c`:

```
public class DocumentRequirements {
  private static final int MAX_RETRIES;

  public static java.lang.String recordUpload(java.util.Map<java.lang.String, java.lang.Integer>, java.lang.String);
    Code:
       0: aload_0
       1: aload_1
       2: invokeinterface #7,  2            // InterfaceMethod java/util/Map.get:(Ljava/lang/Object;)Ljava/lang/Object;
       7: checkcast     #13                 // class java/lang/Integer
      10: astore_2
      11: aload_2
      12: ifnonnull     30
      15: aload_0
      16: aload_1
      17: iconst_1
      18: invokestatic  #15                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
      21: invokeinterface #19,  3           // InterfaceMethod java/util/Map.put:(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
      26: pop
      27: ldc           #23                 // String AA-610 DOCUMENTS_UPLOADED
      29: areturn
      30: aload_2
      31: invokevirtual #25                 // Method java/lang/Integer.intValue:()I
      34: istore_3
      35: iload_3
      36: iconst_3
      37: if_icmplt     43
      40: ldc           #31                 // String AA-699 DOCUMENTS_EXHAUSTED
      42: areturn
      43: aload_0
      44: aload_1
      45: iload_3
      46: iconst_1
      47: iadd
      48: invokestatic  #15                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
      51: invokeinterface #19,  3           // InterfaceMethod java/util/Map.put:(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
      56: pop
      57: ldc           #23                 // String AA-610 DOCUMENTS_UPLOADED
      59: areturn

  private static int remaining(java.lang.Integer);
    Code:
       0: iconst_3
       1: aload_0
       2: invokevirtual #25                 // Method java/lang/Integer.intValue:()I
       5: isub
       6: ireturn
}
```

Line by line, naming each insertion.

**0–2.** Push the map and the key, `invokeinterface Map.get`. The descriptor is fully erased. No conversion yet.

**7.** `checkcast Integer`. An erasure insertion, not a boxing one. The source contains no cast.

**10–12.** `astore_2` stores the reference into `retries`; `aload_2`, `ifnonnull 30` is the `retries == null` test. **This is the important negative result: comparing a wrapper to `null` emits no unboxing.** JLS §15.21.3 says a comparison where one operand is the null literal and the other is a reference type is a *reference* equality comparison, so `javac` emits a bare `ifnonnull` and there is no `intValue` in sight. If the null check unboxed, it would throw on exactly the input it exists to detect.

**15–18.** The early-return branch. `iconst_1` pushes the literal `1`, then `invokestatic Integer.valueOf` boxes it — the first boxing insertion, forced because `Map.put`'s erased second parameter is `Ljava/lang/Object;`. Constant-pool entry `#15` is `Integer.valueOf`, and it is the *same* entry reused at offset 48.

**21–26.** `invokeinterface Map.put` with three stack words (map, key, value). `pop` discards `put`'s returned previous value, which the source ignored. Note that the discarded value is a reference, so `pop` and not `pop2`.

**27–29.** `ldc` the status string, `areturn`.

**30–34.** The non-null path. `aload_2`, `invokevirtual Integer.intValue`, `istore_3` — this is the `int used = retries;` line, and it is the only unboxing insertion in the method. It is guarded by the `ifnonnull` at offset 12, which is what makes the method null-safe.

**35–37.** `iload_3`, `iconst_3`, `if_icmplt 43`. `MAX_RETRIES` appears as `iconst_3`, not as a `getstatic`, because it is a `static final int` initialised with a constant expression and is therefore a compile-time constant folded into every use site — the mechanism in [`../classes-and-initialization/04-internals-final-and-constant-folding.md`](../classes-and-initialization/04-internals-final-and-constant-folding.md). The source's `>=` became a `<` jump because `javac` branches on the *negation* to fall through into the taken case.

**43–48.** `iload_3`, `iconst_1`, `iadd` — the `used + 1` arithmetic happens entirely in primitives, then `invokestatic Integer.valueOf` boxes only the final result. Nothing boxed the operands. This is worth internalising: `javac` boxes at the boundary, not at each arithmetic step, so `used + 1` costs one box and not three.

**51–59.** The second `put`, `pop`, `ldc`, `areturn`.

Totals for the whole method: **two boxing insertions** (offsets 18 and 48, on mutually exclusive paths, so at most one executes per call), **one unboxing insertion** (offset 31), and **one erasure `checkcast`** (offset 7). That is the complete conversion inventory of a method whose source shows not a single explicit conversion.

And `remaining` shows the smallest possible version of the same thing: `iconst_3` for the folded constant, `aload_0`, `invokevirtual intValue` to unbox, `isub`. Note the operand order — the constant is pushed *before* the receiver, because `isub` computes `first - second` and the source reads `MAX_RETRIES - retries`.

### The gotcha

**Pitfall:** counting `invokestatic Integer.valueOf` occurrences in a `javap` listing and reporting the total as an allocation count. It is not one, for two independent reasons, and both are large.

First, the cache. `Integer.valueOf` allocates nothing for arguments in −128..127; it returns `IntegerCache.cache[i + 128]`, an array read. Measured: a `List<Integer>` of 1,000,000 values all equal to **100** costs **4,000,040 bytes** — 4.00004 per element, identical to an `int[]` — because every value is inside the cache and only the references in the backing array are new. The same list with values of **420** costs **20,000,040**. Same bytecode, same instruction count, a 5× difference in allocation, decided entirely by the *values* flowing through.

Second, escape analysis. C2 can prove a box does not escape its compiling method and eliminate the allocation entirely by scalar replacement. Measured on a method boxing two values and adding them, driven 5,000,000 times with values well outside the cache range, allocation read from `getThreadAllocatedBytes`: **0 bytes** by default, and **160,000,000 bytes** (32.0 per iteration, exactly two 16-byte `Integer`s) with `-XX:-DoEscapeAnalysis`. Two `invokestatic Integer.valueOf` instructions per iteration in the bytecode either way. Zero allocations by default.

So the honest statement: **the bytecode is an upper bound on boxing cost and never a measurement of it.** It tells you the maximum number of conversions the language demands; the cache removes some of them at runtime by value, and the JIT removes some of them at runtime by shape, and neither removal is visible in the class file. This is the standing limitation of all bytecode-level reasoning about cost, and it applies far beyond boxing. For an allocation number, measure allocation: `com.sun.management.ThreadMXBean.getThreadAllocatedBytes` around a warmed loop, which is the technique behind every figure in this file and in [`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md).

> **Definition.** A boxing conversion compiles to exactly one `invokestatic <Wrapper>.valueOf:(<primitive-descriptor>)L<Wrapper>;` and an unboxing conversion to exactly one `invokevirtual <Wrapper>.<xxx>Value:()<primitive-descriptor>`, inserted by `javac` at every JLS §5.1.7 and §5.1.8 conversion site in the *enclosing* method — there is no boxing opcode, which is why boxing cannot throw, unboxing throws `NullPointerException` on a null receiver, and both are subject to ordinary inlining and escape analysis rather than to special JVM machinery.

---

## Reading the listings: three things about the tool

**`javap -c` alone hides private members, so `-p` is not optional.** Measured on the same `DocumentRequirements.class`: with `-p -c` the output includes `private static final int MAX_RETRIES;` and the whole `private static int remaining(java.lang.Integer);` method with its `invokevirtual intValue`. With plain `-c` both are absent — the class header and the public method are identical, and the private method simply does not appear. A conversion catalogue built from `javap -c` output therefore silently omits every conversion in every private method, which in a typical service class is most of them. Always `javap -p -c`, and `-v` when you also want the constant pool, the `Exception table` and the flags.

**A constant-pool index in a listing is resolved lazily, so `invokestatic` in the bytecode does not mean the class is loaded.** JVMS §5.4.3 permits resolution to be deferred until first use of the entry, and HotSpot defers it. Measured: a `BonusService.grantMinorUnits` whose `useLegacyRail` branch carries `invokestatic #7  // Method LegacyBonusRail.grant:(I)Ljava/lang/Integer;`, run with `LegacyBonusRail` absent from the classpath. The `false` path returned `650` normally and the class printed a further line; only when the `true` path executed did it produce `java.lang.NoClassDefFoundError: LegacyBonusRail`. So a listing showing `invokestatic java/lang/Integer.valueOf` proves the *conversion is compiled in*, not that `Integer` or `IntegerCache` has been initialised — which matters when reasoning about when the 256-entry cache array actually gets built ([`03-internals-boxing.md`](03-internals-boxing.md), and the trigger rules in [`../classes-and-initialization/01d-class-initialization-triggers.md`](../classes-and-initialization/01d-class-initialization-triggers.md)).

**For what actually happens at runtime, the tool is not `javap`.** `-XX:+PrintCompilation` shows which methods C2 compiled and when; `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` shows whether `Integer.valueOf` and `Integer.intValue` were inlined into their callers, which is the precondition for the box being eliminable at all. Neither is a bytecode question and neither has a bytecode answer. Guide **06 JVM internals** covers both flags, plus JOL and JFR for the allocation side.

---

## Pitfalls

### Counting `invokestatic Integer.valueOf` in `javap` output as an allocation count

**Wrong**

```java
// The reasoning: "javap shows two Integer.valueOf calls per iteration,
// stake reservations run at 2.8M/day, so that is 5.6M Integer allocations
// per day, 16 bytes each, 89.6 MB of garbage." Reported to the team as a
// memory figure.
static int stakeTotalMinorUnits(int cashMinorUnits, int bonusMinorUnits) {
    Integer cash = cashMinorUnits;      // invokestatic Integer.valueOf
    Integer bonus = bonusMinorUnits;    // invokestatic Integer.valueOf
    return cash + bonus;                // two invokevirtual intValue
}
```

Measured on JDK 21.0.7 over 5,000,000 iterations with values outside −128..127, warmed to C2, allocation read from `getThreadAllocatedBytes`: **0 bytes. Zero.** C2 proves neither box escapes and eliminates both allocations by scalar replacement. The two `invokestatic` instructions are still in the class file and always will be.

**Right**

```java
// Measure allocation, do not count instructions.
static long allocatedBytesFor(Runnable work) {
    var mx = (com.sun.management.ThreadMXBean) java.lang.management.ManagementFactory
                 .getThreadMXBean();
    long id = Thread.currentThread().threadId();
    for (int warmup = 0; warmup < 20_000; warmup++) { work.run(); }   // reach C2
    long before = mx.getThreadAllocatedBytes(id);
    work.run();
    return mx.getThreadAllocatedBytes(id) - before;
}
```

Run against the same method that produced the 0-byte result, and with `-XX:-DoEscapeAnalysis` it produces **160,000,000 bytes** over 5,000,000 iterations — 32.0 per iteration, exactly two 16-byte `Integer`s. That contrast is the measurement; the instruction count is not.

**Why people believe it:** in almost every other case, reading bytecode *is* the rigorous move, and it is the right instinct — a `new` opcode really does allocate, `iadd` really is one addition, and the whole value of `javap` is that it removes guesswork about what the compiler did. Boxing is the exception, because two entirely separate mechanisms sit between the instruction and the allocation: a value-dependent cache inside the library method, and a shape-dependent optimisation inside the JIT. Neither is expressible in a class file, so the class file cannot report on them.

### Putting the null guard on the boxing side of the conversion

**Wrong**

```java
static int retriesFor(DocumentRequirement requirement, Map<String, Integer> retriesByRequirement) {
    int uploads = requirement.uploadCount();
    if (uploads == 0) {                       // "guard the boxing"
        return 0;
    }
    retriesByRequirement.put(requirement.code(), uploads);   // this cannot throw
    return retriesByRequirement.get(requirement.code());     // this can, and does
}
```

The guard protects the `invokestatic Integer.valueOf` on the `put` line, which was never capable of throwing: it is a static call taking an `int`, with no receiver and no reference operand. The `return` line is the dangerous one — its listing is `invokeinterface Map.get`, `checkcast Integer`, `invokevirtual Integer.intValue`, and if the map lookup misses, the `invokevirtual` throws `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because the return value of "java.util.Map.get(Object)" is null`.

**Right**

```java
static int retriesFor(DocumentRequirement requirement, Map<String, Integer> retriesByRequirement) {
    Integer retries = retriesByRequirement.get(requirement.code());
    if (retries == null) {                    // ifnonnull -- emits no unboxing
        return 0;
    }
    return retries;                           // invokevirtual intValue, now guarded
}
```

Hold the value at its *reference* type, test it against `null` — which compiles to a bare `ifnonnull` and emits no conversion at all, by JLS §15.21.3 — and only then let the unboxing conversion happen. Or `retriesByRequirement.getOrDefault(requirement.code(), 0)`, which never yields a null to unbox. The full treatment of this failure is [`01c-unboxing-null.md`](01c-unboxing-null.md).

**Why people believe it:** "conversion" sounds symmetric, so a risk on one side implies a risk on the other, and nothing in the source distinguishes the two directions — both are a bare assignment with no visible call. One look at the descriptors settles it permanently: `(I)Ljava/lang/Integer;` consumes a primitive and `()I` consumes a receiver, and only a receiver can be null.

### Assuming the box is emitted in the callee, so a signature change is invisible to compiled callers

**Wrong**

```java
// PaymentService gains a boxed overload. The reasoning: "the conversion
// happens inside reserve(), so every existing caller picks it up as soon
// as we deploy the new PaymentService jar."
public class PaymentService {
    public static void reserve(int stakeMinorUnits) { }
    public static void reserve(Integer stakeMinorUnits) { }   // new
}
```

Measured. `FundsLedger.reserveStake(Integer)` compiled against the *old* `PaymentService` contains, in its own class file:

```
       0: aload_0
       1: invokevirtual #7                  // Method java/lang/Integer.intValue:()I
       4: invokestatic  #13                 // Method PaymentService.reserve:(I)V
```

Deploying the new `PaymentService` next to that unchanged `FundsLedger.class` changes nothing. The unbox and the `(I)V` target are both baked into the caller's constant pool, so the boxed overload is never reached.

**Right**

```java
// Recompile the caller. Same source, new bytecode:
//        0: aload_0
//        1: invokestatic  #7   // Method PaymentService.reserve:(Ljava/lang/Integer;)V
// Or, better, do not rely on overload resolution to express intent:
public class PaymentService {
    public static void reserve(int stakeMinorUnits) { }
    public static void reserveBoxed(Integer stakeMinorUnits) { }
}
```

Distinct names make the dispatch a compile error rather than a silent choice, and remove the class of bug where a rebuild changes behaviour with no source change. If the overloads must stay, treat adding one as requiring a coordinated rebuild of every caller, and remember that the reverse is also true: with `reserveWide(long)` and `reserveWide(Integer)` both declared, an `int` argument picks `long`, because JLS §15.12.2 resolves widening in phase 1 and boxing only in phase 2.

**Why people believe it:** the callee is where the parameter type is declared, so it feels like the place the conversion belongs, and every other kind of implementation change genuinely is invisible to callers. Overload resolution is a compile-time decision by design, and the conversion is part of that decision, so both live in the caller's class file.

### Expecting a `switch` on a boxed selector, or a boxed value in a concatenation, to emit what you guessed

**Wrong**

```java
// Two common guesses, both measured false on JDK 21.0.7:
//  (a) "switch on an Integer compares boxed constants, so it costs an
//       Integer.equals per case and the cache boundary matters."
//  (b) "a boxed value in a concatenation is boxed, then toString'd."
static String routeRetryCount(Integer retryCount) {
    switch (retryCount) { case 0: return "AA-600 DOCUMENTS_REQUESTED"; default: return "AA-699 DOCUMENTS_EXHAUSTED"; }
}
static String auditLine(Integer retryCount) {
    return "AA-650 DOCUMENTS_REFERRED retries=" + retryCount;
}
```

Both guesses lead somewhere wrong. Believing (a) suggests a null selector will reach `default`; it does not. Believing (b) suggests a null value will throw in a log line; it does not.

**Right**

The measured listings. The switch:

```
       0: aload_0
       1: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
       4: tableswitch   { // 0 to 2
```

One unbox, then a primitive `tableswitch` against `int` labels. No `equals`, no boxed constants, the cache irrelevant — and a null selector throws at offset 1, *before* any label is examined, so `default` never runs: `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<parameter1>" is null`. The concatenation:

```
       0: aload_0
       1: invokedynamic #108,  0            // InvokeDynamic #0:makeConcatWithConstants:(Ljava/lang/Integer;)Ljava/lang/String;
```

The reference is passed as a reference; the descriptor says `(Ljava/lang/Integer;)`. No box, no unbox, and no `toString` call in the class file — `StringConcatFactory`'s bootstrap inserts `String.valueOf(Object)` inside the `MethodHandle` chain it builds at first execution. Measured with a null value: `AA-650 DOCUMENTS_REFERRED retries=null`, no throw.

**Why people believe it:** guess (a) generalises from `switch` on a `String`, which genuinely does use `hashCode` and `equals` in a two-stage desugaring, so a reference-comparison model of `switch` is not baseless. Guess (b) was *true before Java 9*, when `javac` desugared concatenation to `StringBuilder.append` calls and an `append(Object)` really did appear in the listing; JEP 280 replaced that with `invokedynamic` in Java 9 and the folklore outlived the implementation. Both are cheap to measure, and the right habit is to measure rather than reason from the shape of the source.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Boxing opcode | **none exists**. Boxing is a compiler-inserted method call |
| Boxing instruction | `invokestatic <Wrapper>.valueOf:(<prim>)L<Wrapper>;` |
| Unboxing instruction | `invokevirtual <Wrapper>.<xxx>Value:()<prim>` |
| Why boxing cannot throw | `invokestatic`, no receiver, primitive argument |
| Why unboxing can throw | `invokevirtual`, the reference *is* the receiver |
| `int` | `Integer.valueOf:(I)Ljava/lang/Integer;` / `Integer.intValue:()I` |
| `long` | `Long.valueOf:(J)Ljava/lang/Long;` / `Long.longValue:()J` |
| `byte` | `Byte.valueOf:(B)Ljava/lang/Byte;` / `Byte.byteValue:()B` |
| `short` | `Short.valueOf:(S)Ljava/lang/Short;` / `Short.shortValue:()S` |
| `char` | `Character.valueOf:(C)Ljava/lang/Character;` / `Character.charValue:()C` |
| `boolean` | `Boolean.valueOf:(Z)Ljava/lang/Boolean;` / `Boolean.booleanValue:()Z` |
| `float` | `Float.valueOf:(F)Ljava/lang/Float;` / `Float.floatValue:()F` |
| `double` | `Double.valueOf:(D)Ljava/lang/Double;` / `Double.doubleValue:()D` |
| The two odd names | `charValue` and `booleanValue` are **not** `Number` methods — those two classes do not extend `Number` |
| Load opcode for `byte`/`short`/`char`/`boolean` | `iload` — the descriptor `(B)`/`(S)`/`(C)`/`(Z)` is what picks the overload |
| Where the box is emitted | in the **caller**, at the call site. Measured: adding `reserve(Integer)` changes the caller's bytecode only on recompile |
| Generic read, `int` target | 3 instructions: `invokeinterface get`, `checkcast Integer` (erasure), `invokevirtual intValue` (unboxing) |
| Its two failure modes | `ClassCastException` at the `checkcast`; `NullPointerException` at the `invokevirtual` |
| `map.put(k, used + 1)` | `iadd` in primitives, then **one** `valueOf`. Operands are not boxed individually |
| `retries == null` | `ifnonnull`. **Emits no unboxing** — JLS §15.21.3 reference comparison |
| `sum += n` on a `Long` | `longValue`, `i2l`, `ladd`, `valueOf`, `astore` — 4 conversion instructions per `+=`, JLS §15.26.2 |
| `new Integer(3)` | `new`, `dup`, `iconst_3`, `invokespecial <init>:(I)V` — 4 instructions, unconditional allocation |
| `Integer.valueOf(3)` | `iconst_3`, `invokestatic valueOf` — 2 instructions, no allocation when cached |
| Telling them apart in tooling | different opcodes (`invokespecial` vs `invokestatic`) and different `Methodref` names — no dataflow needed |
| `switch (someInteger)` | **one** `invokevirtual intValue` at offset 1, then a primitive `tableswitch`. No `equals`, cache irrelevant |
| `switch` on a null `Integer` | NPE at that `intValue`, before any label. `default` does **not** catch it |
| `"…" + someInteger` | `invokedynamic makeConcatWithConstants:(Ljava/lang/Integer;)…`. **No box, no unbox, no `toString`** in the class file |
| `"…" + null Integer` | prints `null`, does not throw — `String.valueOf(Object)` inside the bootstrap |
| Concatenation version trap | pre-Java-9 it was `StringBuilder.append(Object)`; JEP 280 replaced it with `invokedynamic` |
| `wrapper == wrapper` | `if_acmpne`. No conversion instruction at all; reference identity, so the cache decides |
| `wrapper == primitive` | `invokevirtual intValue` then `if_icmpne`. Numeric, and can throw |
| Mixed `==` evaluation order | left operand unboxed **before** the right is pushed (JLS §15.7.1) |
| `static final int` in a listing | folded to `iconst_3` at the use site, not a `getstatic` |
| `javap -c` without `-p` | **hides all private members** — measured: a private method with an unbox vanished entirely |
| Constant-pool resolution | lazy (JVMS §5.4.3). Measured: `invokestatic` to an absent class ran fine until that branch executed, then `NoClassDefFoundError` |
| Bytecode as a cost measure | an **upper bound only**. The cache removes boxes by value; C2 removes them by shape |
| Cache effect, measured | `List<Integer>` of 1M values of **100**: 4,000,040 bytes. Same list of **420**: 20,000,040 |
| Escape analysis, measured | 2 boxes/iteration × 5M iterations: **0** bytes default, **160,000,000** with `-XX:-DoEscapeAnalysis` |
| The right tool for cost | `getThreadAllocatedBytes` around a warmed loop |
| The right tool for runtime shape | `-XX:+PrintCompilation`, `-XX:+PrintInlining` (needs `-XX:+UnlockDiagnosticVMOptions`) |
| Helpful NPE messages | on by default since Java 15 (JEP 358); before that, `-XX:+ShowCodeDetailsInExceptionMessages` |

---

## Self-test

**Q1.** What does autoboxing compile to, and why is that answer the root of everything else about boxing?

<details><summary>Answer</summary>

One instruction: `invokestatic java/lang/Integer.valueOf:(I)Ljava/lang/Integer;` at the conversion site, with the corresponding `valueOf` for each of the other seven primitives. Auto-unboxing is one `invokevirtual java/lang/Integer.intValue:()I`. The measured listing for `Integer retryCount = uploads; return retryCount;` is `iload_0`, `invokestatic #7`, `astore_1`, `aload_1`, `areturn` — and note the opcode prefix flipping from `i` to `a` exactly at the invoke, which is the conversion made visible. The reason this is the root fact: the JVM has no boxing opcode at all, so boxing is not a JVM feature, it is a `javac` decision plus a library method. Everything else follows. Boxing cannot throw, because `invokestatic` has no receiver and its argument is a primitive. Unboxing can throw `NullPointerException`, because `invokevirtual` needs a non-null receiver. The cache is possible at all because `valueOf` is ordinary Java that can consult an array, and is tunable because it can read a property. And the JIT can erase a box using nothing but the inlining and escape analysis it already applies to every other small static method and every other allocation — no bespoke machinery, which is why a non-escaping box can measure at literally zero bytes.

</details>

**Q2.** Why can unboxing throw when boxing cannot? Answer at the instruction level.

<details><summary>Answer</summary>

Because of where the input sits. Boxing is `invokestatic Integer.valueOf:(I)Ljava/lang/Integer;` — the descriptor takes an `I`, a primitive, and a primitive cannot be null; there is no receiver on the stack at all, since the call is static. So the instruction has nothing to dereference and the only way it can fail is `OutOfMemoryError`, which is not boxing-specific. Unboxing is `invokevirtual Integer.intValue:()I` — the descriptor takes *no* arguments, so the only input is the receiver, which is popped from the stack and dereferenced to dispatch the call. A null receiver throws `NullPointerException` at the invoke instruction, before the method body is entered. Measured message on JDK 21.0.7 for a missing map entry: `Cannot invoke "java.lang.Integer.intValue()" because the return value of "java.util.Map.get(Object)" is null`, naming a method the source never mentions. The practical consequence is where the guard goes: guarding the boxing side is dead code, and the correct shape is to hold the value at its reference type, test it with `if (retries == null)` — which compiles to a bare `ifnonnull` and emits no conversion, by JLS §15.21.3 — and only then let the unbox happen.

</details>

**Q3.** `positionsByType.get("CLIENT_BONUS_RESERVED")` assigned to an `int` compiles to three instructions after the load. Name each one, say which compiler rule inserted it, and say how the line can fail.

<details><summary>Answer</summary>

Measured: `invokeinterface java/util/Map.get:(Ljava/lang/Object;)Ljava/lang/Object;`, then `checkcast java/lang/Integer`, then `invokevirtual java/lang/Integer.intValue:()I`. The `invokeinterface` descriptor is fully erased — no `String`, no `Integer` — because a generic type parameter compiles to its bound. The `checkcast` is an **erasure** insertion: the erased return type is `Object`, `javac` knows statically it is an `Integer`, and the cast is what makes the assignment type-check at the bytecode level. The `invokevirtual intValue` is the **unboxing** insertion, driven by JLS §5.1.8 and the `int` target type. Two separate insertions from two separate language rules on one source line that contains no visible cast and no visible call. Hence two distinct failure modes: if the map is not really a `Map<String, Integer>` — a raw reference, or one that crossed an unchecked boundary — the `checkcast` throws `ClassCastException`; if the key is absent or maps to null, the `invokevirtual` throws `NullPointerException`. The order matters for diagnosis: a `ClassCastException` on that line indicts the map's provenance, an NPE indicts its contents.

</details>

**Q4.** Someone reads `javap` on a hot method, counts two `invokestatic Integer.valueOf` per iteration, multiplies by the iteration count and 16 bytes, and reports a garbage figure. What is wrong, and what should they have done?

<details><summary>Answer</summary>

The bytecode is an upper bound on boxing cost, never a measurement of it, and two independent mechanisms sit between the instruction and the allocation. First the cache: `Integer.valueOf` returns `IntegerCache.cache[i + 128]` for arguments in −128..127 and allocates nothing. Measured, same bytecode throughout: a `List<Integer>` of 1,000,000 values all equal to **100** costs **4,000,040** bytes, identical per element to an `int[]`, while the same list with values of **420** costs **20,000,040**. A 5× difference decided by the values, not the instructions. Second, escape analysis: measured on a method that boxes two values and adds them, driven 5,000,000 times with values well outside the cache range and warmed to C2, allocation read from `getThreadAllocatedBytes` — **0 bytes by default**, and **160,000,000 bytes** with `-XX:-DoEscapeAnalysis`, which is 32.0 per iteration, exactly two 16-byte `Integer`s. C2 proves the boxes do not escape and scalar-replaces them. Neither the cache's value dependence nor the JIT's shape dependence is expressible in a class file, so the class file cannot report on either. What they should have done: measure allocation directly with `getThreadAllocatedBytes` around a warmed loop, and use the bytecode only to answer *where* conversions are emitted, which it does answer definitively.

</details>

**Q5.** A `switch` on an `Integer` selector — how is it compiled, and what happens if the selector is null?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: `aload_0`, then **one** `invokevirtual java/lang/Integer.intValue:()I` at offset 1, then a plain dense `tableswitch { // 0 to 2 }` over primitive `int` case labels, with `ldc`/`areturn` arms. The selector is unboxed exactly once, not once per case, and there is no `Integer.equals` and no comparison against a boxed constant anywhere in the method — so the cache boundary at 127 is completely irrelevant to a `switch`, unlike to `==`. JLS §14.11 is the reason: the selector undergoes unboxing conversion, so by the time labels are considered it is an `int` switch. The null case is the important consequence. The NPE fires at offset 1, at the `intValue` call, **before any case label is examined**, so a `default` branch does not catch it — measured: `java.lang.NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<parameter1>" is null`. The stack trace points at the switch's line with no indication of which value was null. Fix: null-check the selector before the switch, or use `getOrDefault` at the lookup that produced it. Note the parallel with an enum `switch`, which also throws at an `invokevirtual` — `ordinal()` there — one instruction ahead of any label, for exactly the same structural reason.

</details>

**Q6.** Does `"AA-650 DOCUMENTS_REFERRED retries=" + retryCount` box, where `retryCount` is an `Integer`? What about where it is an `int`?

<details><summary>Answer</summary>

Neither case boxes, and the `Integer` case does not unbox either. Measured on JDK 21.0.7, the `Integer` version is `aload_0` then `invokedynamic #108, 0 // InvokeDynamic #0:makeConcatWithConstants:(Ljava/lang/Integer;)Ljava/lang/String;` then `areturn` — the reference is passed straight through as a reference, and the descriptor says so. The `int` version is the same shape with descriptor `(I)Ljava/lang/String;`. There is no `valueOf`, no `intValue`, and no `Integer.toString` or `String.valueOf` call visible in the class file at all: `java.lang.invoke.StringConcatFactory`'s bootstrap method builds the entire concatenation as a `MethodHandle` chain on first execution, and it handles a reference argument by inserting the `String.valueOf(Object)` step inside that chain, below the bytecode's visibility. Two consequences. Concatenating a boxed value is not a boxing cost, so the widespread claim that `"" + someInteger` "boxes and calls `toString`" is a **version trap** — it was true before Java 9, when `javac` desugared concatenation to `StringBuilder.append` calls and an `append(Object)` really did appear in the listing, and JEP 280 replaced that with `invokedynamic` in Java 9. And a null value does not throw: measured, `AA-650 DOCUMENTS_REFERRED retries=null`, because `String.valueOf(Object)` maps null to the four characters `null`. Concatenation is therefore the one context where a null box is silently rendered rather than reported.

</details>

**Q7.** `left == right` where both are `Integer`, versus where `right` is an `int`. Give the bytecode for each and everything that follows.

<details><summary>Answer</summary>

Both-wrappers, measured: `aload_0`, `aload_1`, `if_acmpne` — an *a*-prefixed comparison, so reference identity, and the method contains no conversion instruction whatsoever. Mixed, measured: `aload_0`, `invokevirtual java/lang/Integer.intValue:()I`, `iload_1`, `if_icmpne` — an *i*-prefixed comparison, so numeric, after one unboxing conversion. One opcode letter, and it carries the entire semantic difference. What follows: the wrapper-to-wrapper form is decided by object identity, so it is answered by the cache — measured, `Integer big1 = 1000, big2 = 1000; big1 == big2` is **false** while the same code at 127 is true — and it never throws, since comparing two references, either possibly null, is safe. The mixed form is always value-correct — measured, `big1 == prim` with both 1000 is **true** — but it can throw, because it dereferences. Measured on a null left operand: `NullPointerException: Cannot invoke "java.lang.Integer.intValue()" because "<parameter1>" is null`, while `nullInteger == otherInteger` returns false with no throw. One more detail from the listing: the order is `aload_0`, `intValue`, `iload_1` — the left operand is unboxed before the right operand is even pushed, which is JLS §15.7.1 left-to-right evaluation, so the NPE fires regardless of what the right operand would have been.

</details>

**Q8.** You are cataloguing every boxing conversion in a service class from `javap` output. Name two ways the listing can mislead you.

<details><summary>Answer</summary>

First, **`javap -c` without `-p` hides every private member**, so a catalogue built from it silently omits every conversion in every private method — which in a typical service class is most of them. Measured on one class: with `-p -c` the output includes `private static final int MAX_RETRIES;` and the whole `private static int remaining(java.lang.Integer);` method with its `invokevirtual Integer.intValue`; with plain `-c` the class header and the public method are byte-identical and both private members simply do not appear. There is no warning and no gap in the numbering. Always `javap -p -c`, and `-v` when you also want the constant pool, flags and exception tables.

Second, **the presence of an instruction says nothing about runtime**, in two different directions. A constant-pool entry is resolved lazily (JVMS §5.4.3), so an `invokestatic` in a listing does not mean the target class has been loaded, let alone initialised — measured: a method whose unexecuted branch carries `invokestatic LegacyBonusRail.grant` ran normally and returned `650` with `LegacyBonusRail` absent from the classpath, and only threw `NoClassDefFoundError` when that branch actually executed. So a listing showing `invokestatic java/lang/Integer.valueOf` does not prove `IntegerCache`'s array has been built. And in the cost direction, the instruction count is an upper bound only: the cache removes allocations by value and C2's escape analysis removes them by shape, measured at 0 bytes for a shape whose bytecode contains two `valueOf` calls per iteration. For runtime facts the tools are `-XX:+PrintCompilation`, `-XX:+PrintInlining` and `getThreadAllocatedBytes`, not `javap`.

</details>

---

## Open questions

- **Unverified:** whether the JLS or JVMS *requires* the boxing conversion to be compiled as a call to `Wrapper.valueOf` specifically, or whether that is a `javac` implementation choice permitted by a looser specification. JLS 21 §5.1.7 describes boxing in terms of the resulting value and the mandated caching for −128..127, and the observable identity behaviour it requires is exactly what `valueOf` delivers — but whether a conformant compiler could emit `new Integer(int)` for an uncached value, or an entirely different factory, was not established. Everything in this file reports measured bytecode from a named compiler rather than a specification requirement, so nothing here depends on the answer. What would settle it: JLS 21 §5.1.7's normative text on boxing conversion, read against JVMS 21 §3.x's compilation examples.
- **Unverified:** whether `Integer.valueOf` and `Integer.intValue` are in fact inlined at the call sites in the listings above. Both are small methods on a `final` class, `valueOf` carries `@IntrinsicCandidate`, and inlining is the precondition for the escape analysis result measured here — so the inference is strong. But no compilation log was inspected for these specific methods. What would settle it: `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` over a warmed loop calling them. The claims this file actually relies on — that the instructions are present in the class file, and that the measured allocation is 0 bytes by default and 160,000,000 with `-XX:-DoEscapeAnalysis` — are both measured directly.
- **Unverified:** whether `StringConcatFactory`'s generated `MethodHandle` chain for a reference argument uses `String.valueOf(Object)` or some internal equivalent. What is measured is negative and positive at the ends: the class file contains no conversion call and passes `Ljava/lang/Integer;` in the `invokedynamic` descriptor, and a null argument renders as the four characters `null` rather than throwing, which is `String.valueOf(Object)`'s documented behaviour and not `Object.toString`'s. The intermediate step inside the bootstrap was not inspected. What would settle it: `-Djava.lang.invoke.MethodHandle.DUMP_CLASS_FILES=true` on a run that executes the concatenation, then reading the dumped lambda forms.

---

**Leaves covered:** 3.4.7 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 808
