# 03 Java Core — Wrappers and autoboxing — BASICS (§1.9, 1.9.1, 1.9.2)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [`try` as control flow, and unreachable code](../control-flow/01e-try-and-unreachable-code.md) · Next: [The wrapper caches](01a-the-wrapper-caches.md)

Java has two type systems bolted together: the primitive system — eight machine-shaped values with
no header, no identity, no methods, described in
[the primitives file](../primitives-and-conversions/01-basics.md) — and the reference system,
everything that can sit in an `Object` variable, be a collection element, be a generic type
argument, be `null`. The eight wrapper classes are the welded seam, and almost every wrapper
surprise a working engineer meets is a consequence of the weld being visible.

This file establishes two things: the shape of the family and the two irregularities in it, and what
`javac` actually emits for `Integer stakeMinorUnits = 420;`. The files after it are the traps that
follow from the second.

## The family, before the details

Every fact in this table is quoted from the JDK 21.0.7 class declarations or measured by
reflection on that JDK.

| Wrapper | Primitive | `extends Number`? | Implements | Note |
|---|---|---|---|---|
| `Byte` | `byte` | yes | `Comparable<Byte>`, `Constable` | 8-bit signed; `valueOf` needs no bounds check |
| `Short` | `short` | yes | `Comparable<Short>`, `Constable` | 16-bit signed |
| `Integer` | `int` | yes | `Comparable<Integer>`, `Constable`, `ConstantDesc` | the only wrapper with a tunable cache bound |
| `Long` | `long` | yes | `Comparable<Long>`, `Constable`, `ConstantDesc` | 24 bytes on a 64-bit VM, not 16 |
| `Float` | `float` | yes | `Comparable<Float>`, `Constable`, `ConstantDesc` | no cache of any kind |
| `Double` | `double` | yes | `Comparable<Double>`, `Constable`, `ConstantDesc` | no cache; `equals` is not `==` semantics |
| `Character` | `char` | **no** | `Serializable`, `Comparable<Character>`, `Constable` | a UTF-16 code unit, not a number |
| `Boolean` | `boolean` | **no** | `Serializable`, `Comparable<Boolean>`, `Constable` | no cache class; two eager statics `TRUE`/`FALSE` |

All eight are `final`. All eight carry `@jdk.internal.ValueBased`. All eight are `Comparable` to
their own type and to no other type. The six numeric ones inherit `Serializable` through `Number`;
`Character` and `Boolean` declare it themselves, which is the visible scar left by their exclusion.

Measured on JDK 21.0.7:

```
Integer.class.getSuperclass()      : class java.lang.Number
Character.class.getSuperclass()    : class java.lang.Object
Number.class.isAssignableFrom(Boolean.class) : false
Integer.class.getInterfaces()      : [interface java.lang.Comparable, interface java.lang.constant.Constable, interface java.lang.constant.ConstantDesc]
Character.class.getInterfaces()    : [interface java.io.Serializable, interface java.lang.Comparable, interface java.lang.constant.Constable]
Boolean.class.getInterfaces()      : [interface java.io.Serializable, interface java.lang.Comparable, interface java.lang.constant.Constable]
Byte.class.getInterfaces()         : [interface java.lang.Comparable, interface java.lang.constant.Constable]
Integer.class.getAnnotations()     : [@jdk.internal.ValueBased()]
```

Note that `ConstantDesc` lands on exactly four wrappers — `Integer`, `Long`, `Float`, `Double` —
and `Constable` on all eight. That split is not arbitrary: the class file's loadable-constant kinds
are `int`, `long`, `float`, `double` and `String`, so those four wrappers can *be* a constant
description, while `Byte`, `Short`, `Character` and `Boolean` can only be *described* by one. The
class-file side of that is in
[the `javac` and class file file](../language-substrate/03-internals-javac-and-class-file.md).

### Where the rest of this family lives

| File | Owns |
|---|---|
| [The wrapper caches](01a-the-wrapper-caches.md) | `IntegerCache`, the 256-entry array, the index arithmetic, the tunable `high` and the fixed `low` |
| [The archived cache](01a2-the-archived-cache.md) | the CDS archived subgraph, `archivedCache`, `-Xshare`, the flag-versus-archive interaction |
| [Cache coverage and reference equality](01b-cache-coverage-and-reference-equality.md) | which wrapper caches what, the measured 127-versus-128 flip, `==` on wrappers as a reference comparison |
| [Unboxing null](01c-unboxing-null.md) | the unboxing `NullPointerException` at a line with no visible call, and mixed `==` between a primitive and a wrapper |
| [Wrapper `equals` and `hashCode`](01d-wrapper-equals-and-hashcode.md) | `equals` across wrapper types always false; the four wrapper `hashCode` algorithms |
| [`valueOf` and the deprecated constructors](01e-valueof-and-the-deprecated-constructors.md) | the terminally deprecated `new Integer(int)` constructors; `parseInt` versus `valueOf(String)` |
| [Parsing traps and the statics](01f-parsing-traps-and-the-statics.md) | the statics inventory; the `Double.parseDouble` and `Boolean.parseBoolean` traps |
| [The cost of boxing](01g-the-cost-of-boxing.md) | boxing in a loop, and wrapper memory cost |
| [When boxing is unavoidable](01h-when-boxing-is-unavoidable.md) | where boxing is forced, and the primitive-specialised escape hatches |

Those nine plus this file are the BASICS tier. Seven INTERNALS files follow them, walking
`Integer.valueOf` and `IntegerCache` line by line, the boxing bytecode, escape analysis, wrapper
memory, and the monitor and Valhalla story; this file builds the model they assume.

---

## 1. The eight wrappers, and what the family shape tells you (§1.9.1)

`[SOURCE]` Picture a wrapper as a one-field, sealed-shut box: a 12-byte object header, the
primitive laid in beside it, and nothing else — no mutator, no subclass hook, no second field. Its
entire reason to exist is that a reference slot cannot hold an `int`, and enormous parts of Java
are reference slots: `Object[]`, every `Map` value, every type argument, every `Optional`, every
`null`. The box is the adapter that lets a 4-byte machine integer sit in a 4-byte machine reference.

Two members of the family are wired differently from the other six, and that difference is the most
useful thing in the hierarchy table. `Character` and `Boolean` do not extend `Number`. That is not
an oversight and it is not a historical accident anyone regrets — it falls straight out of what
`Number` promises.

### Why it exists

Java 1.0 made a permanent bargain. Primitives exist so that arithmetic on a `long` compiles to a
`ladd` and not a virtual call, and so that an `int[]` is a contiguous block of 4-byte cells; the
type system, meanwhile, wanted a single root, `Object`, so that collections and reflection could be
written once. Those two goals are incompatible without a bridge. The wrappers are the bridge. Before
generics they were also the only way to get a number into a `Vector`.

`Number` is that bridge's numeric contract, and it is a narrow one. Measured on JDK 21.0.7,
`java.lang.Number` declares exactly six instance methods and is `abstract` and `Serializable`:

```
abstract double doubleValue()
abstract float  floatValue()
abstract int    intValue()
abstract long   longValue()
concrete byte   byteValue()
concrete short  shortValue()
```

Ask what `intValue()` should return for `Boolean.TRUE`. There is no answer the platform could pick
without inventing a convention (`1`? `-1`? C's nonzero?), and any convention it picked would leak
into every `Number`-typed API. Ask what `doubleValue()` should return for `Character.valueOf('A')`.
There *is* a mechanical answer — 65.0, the code unit — and that is precisely the problem: it is a
plausible number that means nothing arithmetically. Averaging a list of characters is never what
anybody wanted. So the platform declines to offer the operation rather than offer a misleading one.

**Insight:** `Character` not extending `Number` is a *deliberate refusal to widen a bad conversion
into an interface*. `char` widens to `int` at the language level all day long — `(int)
Character.MAX_VALUE` is 65535, measured — but the language makes you write that widening. Putting
`doubleValue()` on `Character` would have made it implicit and invisible everywhere a `Number` was
accepted.

### The mechanism

Four structural facts do the work.

**`final` on all eight.** You cannot subclass `Integer`. There is no `AuditedInteger extends
Integer` to log every read, and no place to hook a custom cache. Anything you want to add to a
wrapper you add beside it (a `record` of your own, a static helper), never underneath it.

**`Comparable<T>` to its own type only.** `Integer implements Comparable<Integer>` — not
`Comparable<Number>`. This single decision is why cross-type numeric comparison does not compile,
measured on JDK 21.0.7:

```
CmpFail.java:3: error: incompatible types: Long cannot be converted to Integer
        return stakeMinorUnits.compareTo(ledgerCount);
                                         ^
```

The same self-typing at the `equals` level is why `Integer.valueOf(1).equals(Long.valueOf(1))` is
**false** — each wrapper's `equals` begins with an `instanceof` against its own class. That trap,
with all three measured directions, belongs to
[wrapper `equals` and `hashCode`](01d-wrapper-equals-and-hashcode.md).

**`TYPE`, the back-pointer to the primitive.** Every wrapper has a `public static final Class<T>
TYPE` holding the `Class` object for the primitive it wraps, and it is the same object the `int.class`
literal denotes. Measured: `Integer.TYPE == int.class` is **true**, `Boolean.TYPE` prints `boolean`,
`Character.TYPE` prints `char`. This matters in reflection: `Method.getParameterTypes()` on
`reserve(int)` hands you `int.class`, and `Integer.class` will not match it.

**`@jdk.internal.ValueBased`.** All eight carry it, measured. It is the platform's declaration that
these instances have *no meaningful identity* — you must not depend on `==` between two of them,
must not depend on `identityHashCode`, and must not synchronize on one. The identity consequence is
[cache coverage and reference equality](01b-cache-coverage-and-reference-equality.md)'s subject; the
monitor consequence is that `synchronized (someInteger)` locks whatever object the cache happened to
hand you, process-wide, and `javac` emits a `[synchronization]` warning for it. Relatedly, `valueOf`
is the only correct way to construct a wrapper — the `new Integer(int)`-family constructors are
terminally deprecated, and their history and measurements are in
[`valueOf`, parsing and factories](01e-valueof-and-the-deprecated-constructors.md).

### When to reach for the wrapper

| Situation | Use | Why |
|---|---|---|
| A local, a loop counter, a field with a natural zero | primitive | no header, no allocation, no null state to reason about |
| A column that is genuinely absent, not zero (`Integer bonusCapMinorUnits`) | wrapper | `null` distinguishes "no cap configured" from "cap of 0" |
| A collection element or `Map` key/value | wrapper | generics have no primitive instantiation before Valhalla |
| A generic type argument (`Comparator<Integer>`, `Optional<Long>`) | wrapper | same reason |
| A JSON/JPA-mapped DTO field that may be omitted | wrapper | the framework needs to write `null` |
| An accumulator over 2.8M stake reservations | primitive | one box per `+=` otherwise — see [the cost file](01g-the-cost-of-boxing.md) |

The rule that survives contact: **a wrapper is for a value that might not be there or that has to
live in a reference slot. It is never for a value you are about to do arithmetic on.** The cases
where the reference slot is forced on you anyway, and the primitive-specialised escape hatches that
get you back out, are [when boxing is unavoidable](01h-when-boxing-is-unavoidable.md).

### Diagram

No diagram for this concept: the manifest's wrapper diagrams belong to the cache and cost files;
the hierarchy table above is the map this concept needs.

### A concrete example

`Number` as a parameter type is exactly as wide as the six numeric wrappers and no wider. A
QuizStakes audit sink typed on `Number` silently excludes the two flag-shaped values you most want
to audit.

```java
import java.util.ArrayList;
import java.util.List;

final class LedgerAudit {

    private final List<Number> numericFacts = new ArrayList<>();
    private final List<Object> allFacts = new ArrayList<>();

    /** Compiles: int boxes to Integer, which is a Number. */
    void recordStakeMinorUnits(int stakeMinorUnits) {
        numericFacts.add(stakeMinorUnits);
    }

    /** Compiles: long boxes to Long, which is a Number. */
    void recordLedgerEntryCount(long ledgerEntryCount) {
        numericFacts.add(ledgerEntryCount);
    }

    /**
     * Does NOT compile against numericFacts. Character is not a Number,
     * so a StatusCode variant letter has nowhere to go on that list.
     */
    void recordStatusVariant(char variant) {
        allFacts.add(variant);          // Object, not Number
    }

    void recordCouponValid(boolean couponValid) {
        allFacts.add(couponValid);      // Object, not Number
    }

    /** The only totalling this sink can do, and only over the numeric list. */
    long totalMinorUnits() {
        long total = 0L;
        for (Number fact : numericFacts) {
            total += fact.longValue();  // Number's contract, no cast needed
        }
        return total;
    }
}
```

Swap `allFacts` for `numericFacts` in `recordStatusVariant` and JDK 21.0.7 says, measured:

```
NumFail.java:5: error: incompatible types: char cannot be converted to Number
        AUDIT.add(variant);
                  ^
```

The `boolean` case gives the same shape, measured:
`error: incompatible types: boolean cannot be converted to Number`.

`total += fact.longValue()` is worth a second look. Because the list element type is `Number`, the
loop pays a virtual dispatch per element plus, for the `Integer` elements, an `i2l` widening inside
`Integer.longValue()`. Over the 2.8M stake reservations per day this sink would see, that is real —
which is why the same tally over an `int[]` costs nothing and allocates nothing. Both figures are
measured in [the cost file](01g-the-cost-of-boxing.md).

### The gotcha

The two irregularities are not symmetric in how they bite. `Boolean` failing to be a `Number` almost
never surprises anyone. `Character` failing to be one surprises people constantly, because `char`
*behaves* numerically everywhere else: it participates in `+`, it widens to `int`, it indexes arrays,
`Character.MIN_VALUE` and `MAX_VALUE` exist and are 0 and 65535. Every arithmetic intuition you have
about `char` is correct at the primitive level and wrong at the wrapper level. The primitive is a
16-bit unsigned integer; the wrapper is a text element.

**Interview:** "Which wrappers are not `Number`s, and why?" — `Character` and `Boolean`. `Number`'s
whole contract is `intValue`/`longValue`/`floatValue`/`doubleValue`; there is no honest
implementation for a boolean, and the honest one for a `char` (its code unit) is a number that means
nothing arithmetically, so exposing it implicitly through a `Number`-typed API would do more harm
than good.

> **Definition.** The eight wrapper classes are `final`, immutable, value-based reference types whose
> single field holds one primitive, so that a primitive can occupy a reference slot; the six numeric
> ones extend `Number`, and `Character` and `Boolean` do not, because `Number`'s conversion methods
> have no meaningful implementation for a boolean and only a misleading one for a UTF-16 code unit.

---

## 2. Autoboxing and unboxing are a compiler rewrite, and you can see it (§1.9.2) `[BYTECODE]`

There is no runtime magic in autoboxing. There is no JVM instruction for it, no VM hook, no special
casing in the interpreter. `javac` reads your source, notices that a primitive is sitting where a
reference is required (or the reverse), and **inserts a method call**. Boxing becomes
`invokestatic Wrapper.valueOf`. Unboxing becomes `invokevirtual wrapperValue()`. That is the whole
mechanism, and once you hold it, every trap in the next four files becomes predictable rather than
mysterious: they are all consequences of a method call you did not write being where you cannot see it.

### Why it exists

Autoboxing arrived in **Java 5** (JSR 201), alongside generics, and the two were commissioned
together for the same reason. Before Java 5 the code was written by hand, every time:

```java
// Java 1.4 and earlier — what autoboxing replaced
Map reservationsByRound = new HashMap();
reservationsByRound.put(roundId, new Integer(stakeMinorUnits));
int reserved = ((Integer) reservationsByRound.get(roundId)).intValue();
```

Two allocations spelled out, one cast, one `intValue()`, and a `Map` with no element type. Generics
removed the cast; autoboxing removed the `new Integer` and the `.intValue()`. The cost of removing
them was that the calls stopped being visible — which is exactly the trade the language made, and
exactly why an interviewer asks about it.

### The mechanism

JLS 21 §5.1.7 (boxing conversion) and §5.1.8 (unboxing conversion) define the rewrite, and §5.2,
§5.3, §5.5 and §5.6 define **where** it is permitted. The four contexts worth memorising:

| Context | Example (QuizStakes) | Direction |
|---|---|---|
| Assignment | `Integer bonusCapMinorUnits = 100;` | boxing |
| Method invocation | `numericFacts.add(stakeMinorUnits)` | boxing |
| Casting | `(Integer) stakeMinorUnits`, `(int) boxedUnits` | either |
| Numeric promotion in an operator | `boxedUnits + 1`, `boxedUnits++` | unboxing then reboxing |

One rule from that neighbourhood is worth stating here because it catches people who think boxing
is a free pass: **assignment context allows a boxing conversion, and it allows a widening primitive
conversion, but it does not allow a widening primitive conversion followed by boxing.** So
`Long ledgerCount = 3;` does not compile, even though `long ledgerCount = 3;` and
`Long ledgerCount = 3L;` both do. `javac` would have to widen `int` to `long` and *then* box, and
that composite is not on the permitted list. The full context rules, the inference interaction and
the rest of that family live in
[promotion, boxing and inference](../primitives-and-conversions/03a-promotion-boxing-and-inference.md).

Each primitive maps to one specific `valueOf` overload, and you can read the whole mapping off one
`javap` listing. Source — an audit array is the cheapest way to force all eight boxings in one method:

```java
static Object boxAll(byte b, short s, int i, long l,
                     float f, double d, char c, boolean z) {
    Object[] audit = { b, s, i, l, f, d, c, z };
    return audit;
}
```

Measured with `javap -p -c` on JDK 21.0.7, the eight inserted calls:

```
       8: invokestatic  #7                  // Method java/lang/Byte.valueOf:(B)Ljava/lang/Byte;
      15: invokestatic  #13                 // Method java/lang/Short.valueOf:(S)Ljava/lang/Short;
      22: invokestatic  #18                 // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
      29: invokestatic  #23                 // Method java/lang/Long.valueOf:(J)Ljava/lang/Long;
      37: invokestatic  #28                 // Method java/lang/Float.valueOf:(F)Ljava/lang/Float;
      45: invokestatic  #33                 // Method java/lang/Double.valueOf:(D)Ljava/lang/Double;
      54: invokestatic  #38                 // Method java/lang/Character.valueOf:(C)Ljava/lang/Character;
      63: invokestatic  #43                 // Method java/lang/Boolean.valueOf:(Z)Ljava/lang/Boolean;
```

Every one is `invokestatic`, every one takes the primitive descriptor and returns the wrapper. The
unboxing direction is the mirror: `byteValue()`, `shortValue()`, `intValue()`, `longValue()`,
`floatValue()`, `doubleValue()`, `charValue()`, `booleanValue()`, all `invokevirtual`.

`Integer.valueOf(int)` is annotated `@IntrinsicCandidate` in JDK 21.0.7 source, meaning the JIT is
permitted to replace the call with its own compiled idiom rather than inlining the Java body. That
is one of two reasons a non-escaping box can end up costing literally zero; the other is escape
analysis, whose measurements and failure modes are in
[the escape-analysis internals file](03d-internals-escape-analysis.md).

### Diagram

No diagram for this concept: the `javap` listings below *are* the picture, read instruction by
instruction, and a box-and-arrow rendering of them would say less.

### A concrete example

The minimal pair, compiled and disassembled on JDK 21.0.7. Source:

```java
static Integer boxRetryCount(int n) {
    return n;                       // autoboxing
}
static int unboxRetryCount(Integer n) {
    return n;                       // auto-unboxing
}
```

Measured bytecode:

```
  static java.lang.Integer boxRetryCount(int);
    Code:
       0: iload_0
       1: invokestatic  #7                  // Method java/lang/Integer.valueOf:(I)Ljava/lang/Integer;
       4: areturn

  static int unboxRetryCount(java.lang.Integer);
    Code:
       0: aload_0
       1: invokevirtual #13                 // Method java/lang/Integer.intValue:()I
       4: ireturn
```

Read `boxRetryCount` one instruction at a time. `iload_0` pushes local slot 0 as an `int` — the `i`
prefix is the JVM's type tag, so the verifier already knows a primitive is on the stack.
`invokestatic #7` resolves constant-pool entry 7, whose descriptor `(I)Ljava/lang/Integer;` consumes
that `int` and leaves a reference. `areturn` returns a *reference* — `a` for address. Three
instructions, and the middle one is a call that does not appear in the source.

`unboxRetryCount` is the exact mirror. `aload_0` pushes a reference. `invokevirtual #13` — virtual,
not static, because `intValue()` is an instance method dispatched on the receiver, which is the
single reason a `null` wrapper throws here and not at the assignment. Its descriptor `()I` consumes
the reference and leaves an `int`. `ireturn` returns a primitive.

**Insight:** `invokevirtual` on the receiver is the entire explanation of the unboxing
`NullPointerException`. Unboxing is not a conversion that inspects the reference and decides; it is
a method call on it. A `null` receiver fails at `invokevirtual` like any other `null` receiver, which
is why JDK 21 can tell you exactly which call it was: measured, an absent `Map` entry produces
`Cannot invoke "java.lang.Integer.intValue()" because the return value of
"java.util.Map.get(Object)" is null`. The full treatment is in
[unboxing null](01c-unboxing-null.md).

### The gotcha

The rewrite is invisible at the source level, and everything downstream follows from that. Four
consequences, each owned by a sibling file:

- Boxing goes through `valueOf`, which **returns a shared instance** for small values, so `==`
  between two wrappers is a reference comparison whose answer changes at 127/128 —
  [cache coverage and reference equality](01b-cache-coverage-and-reference-equality.md), with the
  cache mechanism itself in [the wrapper caches](01a-the-wrapper-caches.md).
- Unboxing is an `invokevirtual`, so a `null` wrapper throws at a line where you wrote no call —
  [unboxing null](01c-unboxing-null.md).
- A mixed `==` between a primitive and a wrapper unboxes the wrapper and compares numerically, so
  the *same operator* means two different things depending on the static types of its operands. The
  operator's own rules are in
  [casts and comparison](../primitives-and-conversions/02b-casts-and-comparison.md); the measured
  pairs are in [unboxing null](01c-unboxing-null.md). Measured on JDK 21.0.7, with 1000 on both
  sides: wrapper-to-wrapper is **false**, wrapper-to-primitive is **true**.
- A boxing inside a loop body allocates once per iteration and nothing in the source says so —
  [the cost file](01g-the-cost-of-boxing.md).

A fifth, milder one: the conditional operator has its own typing rules and can unbox an operand you
did not expect, so `flag ? 1 : nullInteger` throws. That is
[the conditional operator's file](../primitives-and-conversions/02c-conditional-operator.md).

**Interview:** "What does autoboxing compile to?" — `invokestatic Integer.valueOf(I)` for boxing and
`invokevirtual Integer.intValue()` for unboxing, inserted by `javac`; there is no JVM support and no
runtime component. Say the two instruction names and you have answered it; add "which is why a null
wrapper throws at the `invokevirtual`" and you have answered the follow-up too.

> **Definition.** Autoboxing and auto-unboxing are purely compile-time rewrites introduced in Java 5:
> in a context where JLS 21 §5.1.7 permits it `javac` inserts `invokestatic Wrapper.valueOf(prim)`,
> and where §5.1.8 permits it, `invokevirtual wrapper.primValue()`.

---

## The rest of the shared surface — supporting facts

**`Number` is `abstract` and `Serializable`.** Measured on JDK 21.0.7: `Modifier.isAbstract` on
`Number.class` is true, and `Serializable.class.isAssignableFrom(Number.class)` is true. You cannot
instantiate a `Number`, and the six numeric wrappers get their serializability from it rather than
declaring it, which is why the hierarchy table shows `Serializable` only on `Character` and
`Boolean`. `byteValue()` and `shortValue()` are the only two concrete methods on `Number`; they are
implemented as narrowing casts of `intValue()`, which means they can silently lose data — a
`Number` holding 1200 answers `byteValue()` with a truncated result, by the two's-complement rules
in [integral arithmetic](../primitives-and-conversions/01a-integral-arithmetic.md).

**`TYPE` is the primitive's `Class` object, not the wrapper's.** `Integer.TYPE == int.class` is
measured true; `Integer.TYPE == Integer.class` is not. The gotcha is reflective lookup: to find
`reserve(int)` you must pass `int.class` (or `Integer.TYPE`) to `getDeclaredMethod`, and passing
`Integer.class` throws `NoSuchMethodException` even though the call site boxes happily.

**`MIN_VALUE` / `MAX_VALUE` exist on seven of the eight.** `Boolean` has none — measured,
`Boolean.class.getField("MIN_VALUE")` throws. `Character.MIN_VALUE` and `MAX_VALUE` are `char`
values, not `int`s: measured, `(int) Character.MAX_VALUE` is 65535 and `(int) Character.MIN_VALUE`
is 0, so a `Character` bound is unsigned while every other wrapper's is signed. `Integer.MIN_VALUE`
is -2147483648 and `MAX_VALUE` is 2147483647, measured. `SIZE` and `BYTES` accompany them:
`Integer.SIZE = 32`, `Integer.BYTES = 4`, `Long.SIZE = 64`, `Long.BYTES = 8` — all measured, and all
describing the *primitive's* width, never the wrapper object's footprint, which is 16 and 24 bytes
respectively. That decomposition is in
[the cost of boxing](01g-the-cost-of-boxing.md), byte by byte in
[the wrapper-memory internals file](03e-internals-wrapper-memory.md), and at the header level in
[the object-layout file](../objects-equality-and-lifecycle/05-internals-object-layout.md).

**Wrapper caches are initialised by a holder class.** `IntegerCache` and its siblings are private
static nested classes whose `<clinit>` builds the array, so nothing is built until the first
`valueOf` in the cached range touches the holder. What triggers a `<clinit>` at all is
[class initialization triggers](../classes-and-initialization/01d-class-initialization-triggers.md);
the wrapper-specific mechanics are [the wrapper caches](01a-the-wrapper-caches.md), and the CDS
archive that lets the JVM skip the loop entirely is
[the archived cache](01a2-the-archived-cache.md).

**The wrapper caches are one of the JDK's two identity caches.** The other is the string pool, where
`intern()` plays the role `valueOf` plays here, and the resulting `==` surprises rhyme exactly. See
[the string pool file](../strings/01b-the-string-pool.md).

---

## Pitfalls

### Treating `Character` or `Boolean` as a `Number`

**Wrong**

```java
// A LedgerAudit sink typed on Number, intended to take "every numeric fact".
static final List<Number> AUDIT = new ArrayList<>();

static void recordStatusVariant(char variant) {
    AUDIT.add(variant);            // char is numeric, surely?
}
```

Measured on JDK 21.0.7:

```
NumFail.java:5: error: incompatible types: char cannot be converted to Number
        AUDIT.add(variant);
                  ^
```

The same shape with `boolean couponValid` gives
`error: incompatible types: boolean cannot be converted to Number`, measured. Worse than the
compile error is the *silent* version: a `void record(Number fact)` overload sitting next to a
`void record(Object fact)` overload sends every `char` and `boolean` to the `Object` one, and the
numeric path is quietly never taken for those two.

**Right**

```java
static final List<Number> NUMERIC_FACTS = new ArrayList<>();
static final List<Object> ALL_FACTS = new ArrayList<>();

static void recordStakeMinorUnits(int stakeMinorUnits) {
    NUMERIC_FACTS.add(stakeMinorUnits);        // Integer is a Number
}

// A status-code variant letter is text, not a quantity. Widen explicitly
// if you truly want the code unit as a number, and say so at the call site.
static void recordStatusVariant(char variant) {
    ALL_FACTS.add(variant);                    // Character, held as Object
    NUMERIC_FACTS.add((int) variant);          // explicit: the UTF-16 code unit
}
```

**Why people believe it:** every arithmetic intuition about the *primitive* `char` is correct — it
participates in `+`, widens to `int` without a cast, indexes arrays, and has `MIN_VALUE`/`MAX_VALUE`
bounds. Nothing at the primitive level hints that the wrapper sits outside `Number`, and the
exclusion is a deliberate design choice about what `Number`'s four conversion methods should be
allowed to mean, not a property of `char` itself.

### Believing unboxing "is just a cast", because you can write it as one

**Wrong**

```java
// Two methods that look like the same operation. They are not.
static int narrowLedgerCount(long ledgerCount) {
    return (int) ledgerCount;          // a real cast
}
static int unboxLedgerCount(Integer ledgerCount) {
    return (int) ledgerCount;          // NOT a cast — a virtual call
}
```

Measured with `javap -p -c` on JDK 21.0.7:

```
  static int narrowLedgerCount(long);
    Code:
       0: lload_0
       1: l2i
       2: ireturn

  static int unboxLedgerCount(java.lang.Integer);
    Code:
       0: aload_0
       1: invokevirtual #7                  // Method java/lang/Integer.intValue:()I
       4: ireturn
```

A genuine narrowing cast is `l2i` — one instruction, no call, no receiver, and it cannot throw; it
just truncates. The `(int)` on a wrapper compiles to `invokevirtual Integer.intValue:()I`, an
instance-method call on a receiver that has to be non-null. Same three characters in the source, two
completely different operations in the class file. Both consequences follow: this line can throw
`NullPointerException`, and in a loop it is a call per iteration rather than a free instruction.

**Right**

```java
// If the value is nullable, treat it as nullable — the cast syntax hides nothing.
static int unboxLedgerCount(Integer ledgerCount) {
    if (ledgerCount == null) {
        throw new IllegalTransitionException("ledger count absent");
    }
    return ledgerCount.intValue();     // spelled out: it is a call, so say so
}

// Or keep the primitive and never enter the wrapper world at all.
static int narrowLedgerCount(long ledgerCount) {
    return (int) ledgerCount;          // still one instruction, l2i
}
```

**Why people believe it:** the source syntax is identical, and JLS 21 §5.5 really does call the
wrapper form a *casting conversion* — so the word "cast" is not even wrong at the language level. The
mistake is inferring the *implementation* from the syntax. Casting conversion is an umbrella that
covers primitive narrowing (`l2i`), reference checks (`checkcast`) and unboxing (`invokevirtual`),
and only the middle two involve a reference at all. Read the bytecode and the three stop looking
alike. The throwing half of this is [unboxing null](01c-unboxing-null.md); the per-iteration cost is
[the cost of boxing](01g-the-cost-of-boxing.md).

### Assuming `reserve(int)` and `reserve(Integer)` are the same method

**Wrong**

```java
// Existing API, one overload. Every call site binds here.
static String reserve(int stakeMinorUnits) { return "reserve(int)"; }

// Someone adds a "convenience" boxed overload in a later release.
static String reserve(Integer stakeMinorUnits) { return "reserve(Integer)"; }
```

Measured on JDK 21.0.7 by compiling and running both shapes:

```
only reserve(int) exists, passed an Integer : reserve(int)
both overloads exist,     passed an int     : reserve(int)
both overloads exist,     passed an Integer : reserve(Integer)
```

Read the first and third lines together. A call site holding an `Integer` used to bind to
`reserve(int)` by unboxing; adding the boxed overload silently re-binds that same, unchanged call
site to a different method. Nothing in the caller changed, no warning was issued, and if the two
bodies differ at all — say the boxed one tolerates `null` and returns early — the caller's behaviour
changed on recompilation. This is a source-compatible, binary-incompatible, **behaviour-changing**
addition.

The reason is JLS 21 §15.12.2's three phases: phase 1 considers applicability by strict invocation
with no boxing or unboxing, phase 2 adds method invocation conversion (boxing and unboxing), phase 3
adds varargs. With only `reserve(int)` present, an `Integer` argument fails phase 1 and is resolved
in phase 2 by unboxing. Once `reserve(Integer)` exists, the `Integer` argument is applicable in
phase 1, and phase 1 wins outright — phase 2 is never reached.

The same phase ordering explains a second measured result: with `reserveWide(long)` and
`reserveWide(Integer)` both present, an `int` argument selects **`reserveWide(long)`**, because
widening `int` to `long` is a phase-1 conversion while boxing `int` to `Integer` is not.

**Right**

```java
// Pick one shape per name and keep it. If nullability matters, say so
// in the name rather than in an overload.
static String reserve(int stakeMinorUnits) { return "reserve(int)"; }

static String reserveOptionalCap(Integer bonusCapMinorUnits) {
    if (bonusCapMinorUnits == null) {
        return "reserve(no cap)";
    }
    return reserve(bonusCapMinorUnits);       // unbox once, explicitly, here
}
```

**Why people believe it:** autoboxing makes `int` and `Integer` feel interchangeable at every call
site, and for a *single* method they very nearly are. Overload resolution is the one place where the
distinction is load-bearing, and it is load-bearing at compile time in the caller's translation
unit, so the surprise shows up in a downstream project rather than in the one that added the
overload. The `List<Integer>` `remove(int)` versus `remove(Object)` split is the same mechanism, and
the collections guide (02) covers that instance.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Wrapper count | 8, one per primitive |
| Extend `Number` | `Byte`, `Short`, `Integer`, `Long`, `Float`, `Double` |
| Do not extend `Number` | `Character`, `Boolean` |
| `Number` abstract methods | `intValue`, `longValue`, `floatValue`, `doubleValue` |
| `Number` concrete methods | `byteValue`, `shortValue` (narrowing casts of `intValue`) |
| `Number` modifiers | `abstract`, `Serializable` (measured) |
| All eight are | `final`, immutable, `@jdk.internal.ValueBased` (measured) |
| `Comparable` target | own type only — `Integer implements Comparable<Integer>` |
| Cross-type `compareTo` | does not compile: `Long cannot be converted to Integer` |
| Cross-type `equals` | compiles, returns `false` (see `01d`) |
| `Constable` | all eight |
| `ConstantDesc` | `Integer`, `Long`, `Float`, `Double` only (measured) |
| `Serializable` declared directly | `Character`, `Boolean` (the rest inherit it from `Number`) |
| Autoboxing introduced | Java 5 (JSR 201), with generics |
| Boxing bytecode | `invokestatic Wrapper.valueOf(prim)` |
| Unboxing bytecode | `invokevirtual wrapper.primValue()` |
| Boxing contexts | assignment, method invocation, casting, numeric promotion |
| `Long ledgerCount = 3;` | does not compile — widen-then-box is not an assignment conversion |
| `Integer.valueOf(int)` annotation | `@IntrinsicCandidate` |
| Governing spec | JLS 21 §5.1.7 (boxing), §5.1.8 (unboxing), §5.5 (casting conversion) |
| The eight boxing descriptors | `Byte(B)`, `Short(S)`, `Integer(I)`, `Long(J)`, `Float(F)`, `Double(D)`, `Character(C)`, `Boolean(Z)` (measured) |
| The eight unboxing methods | `byteValue`, `shortValue`, `intValue`, `longValue`, `floatValue`, `doubleValue`, `charValue`, `booleanValue` |
| `(int) someLong` | `l2i` — one instruction, no call, cannot throw (measured) |
| `(int) someInteger` | `invokevirtual Integer.intValue:()I` — a call, and it can throw (measured) |
| `return n;` boxing an `int` | 3 instructions: `iload_0`, `invokestatic`, `areturn` |
| `return n;` unboxing an `Integer` | 3 instructions: `aload_0`, `invokevirtual`, `ireturn` |
| Why a null wrapper throws | unboxing is `invokevirtual`, which needs a non-null receiver |
| Constructing a wrapper | `valueOf` only; the `new Integer(int)` family is terminally deprecated (see `01e`) |
| `Number.byteValue()` / `shortValue()` | narrowing casts of `intValue()` — silently truncate |
| `Integer.TYPE` | `int.class` — measured `==` true |
| `Boolean.MIN_VALUE` | does not exist |
| `Character.MIN_VALUE` / `MAX_VALUE` | `char` 0 and 65535 (unsigned) |
| `Integer.SIZE` / `BYTES` | 32 / 4 — the primitive's width, not the object's |
| `Integer` / `Long` object size | 16 / 24 bytes with compressed oops |
| Overload resolution | phase 1 (no box/unbox) beats phase 2 (box/unbox); adding `reserve(Integer)` re-binds `Integer` call sites |
| `reserveWide(long)` vs `reserveWide(Integer)`, given `int` | picks `long` — widening is phase 1, boxing is not |

---

## Self-test

**Q1.** Why are `Character` and `Boolean` not `Number`s, and what would break if they were?

<details><summary>Answer</summary>

`Number` is an abstract class whose contract is four abstract conversion methods — `intValue`,
`longValue`, `floatValue`, `doubleValue` — plus two concrete narrowing helpers, `byteValue` and
`shortValue`. For `Boolean` there is no honest implementation of any of the four; the platform would
have to invent a convention such as `true == 1`, and that convention would then be silently
available everywhere a `Number` is accepted. For `Character` there *is* a mechanical answer — the
UTF-16 code unit, so `'A'` would answer 65 — and that is worse, because it is a plausible-looking
number that means nothing arithmetically. Making `Character` a `Number` would let you take the mean
of a list of characters, or sum a status-code variant letter into a monetary total, with no cast and
no warning. So both classes sit directly under `Object` and declare `Serializable` themselves, which
is the visible scar of the exclusion: measured, `Character.class.getSuperclass()` is
`class java.lang.Object` and `Number.class.isAssignableFrom(Boolean.class)` is false.

</details>

**Q2.** What exactly does `Integer stakeMinorUnits = 420;` compile to, and what does the reverse
compile to?

<details><summary>Answer</summary>

Boxing compiles to `invokestatic java/lang/Integer.valueOf:(I)Ljava/lang/Integer;` — `javac` inserts
a static call whose descriptor consumes an `int` and yields a reference. Measured, the whole method
`static Integer boxRetryCount(int n) { return n; }` is three instructions: `iload_0`,
`invokestatic #7`, `areturn`. Unboxing compiles to
`invokevirtual java/lang/Integer.intValue:()I`, so `static int unboxRetryCount(Integer n) { return
n; }` is `aload_0`, `invokevirtual #13`, `ireturn`. There is no JVM instruction for boxing and no
runtime support: it is entirely a compile-time rewrite defined by JLS 21 §5.1.7 and §5.1.8, added in
Java 5. The `invokevirtual` on the unboxing side is the important half, because a virtual call needs
a non-null receiver, which is exactly why a `null` wrapper throws there.

</details>

**Q3.** `return (int) ledgerCount;` where `ledgerCount` is a `long`, and the same line where it is
an `Integer`. Same syntax — what is the difference in the class file?

<details><summary>Answer</summary>

Completely different operations. Measured with `javap -p -c` on JDK 21.0.7, the `long` version is
`lload_0`, `l2i`, `ireturn` — a single narrowing instruction that truncates the top 32 bits, needs
no receiver and cannot throw. The `Integer` version is `aload_0`, `invokevirtual
Integer.intValue:()I`, `ireturn` — an instance-method call on a receiver that must be non-null. JLS
21 §5.5 calls both of them a *casting conversion*, so the word "cast" is defensible at the language
level, but casting conversion is an umbrella over primitive narrowing (`l2i`), reference checks
(`checkcast`) and unboxing (`invokevirtual`), and inferring the implementation from the shared
syntax is the mistake. Two consequences follow from the wrapper form being a call: it can throw
`NullPointerException`, and inside a loop it is a call per iteration rather than a free instruction.

</details>

**Q4.** You are reviewing a pull request that adds `reserve(Integer)` beside an existing
`reserve(int)`. What do you say?

<details><summary>Answer</summary>

That it is a source-compatible, behaviour-changing addition, and it needs a reason stronger than
convenience. JLS 21 §15.12.2 resolves overloads in three phases: phase 1 allows no boxing or
unboxing, phase 2 adds it, phase 3 adds varargs. Measured on JDK 21.0.7: with only `reserve(int)`
present, a call site passing an `Integer` fails phase 1 and resolves in phase 2 by unboxing, so it
binds to `reserve(int)`. Once `reserve(Integer)` exists, that same unchanged call site is applicable
in phase 1 and binds to `reserve(Integer)` instead — a different method, silently, on recompilation.
If the two bodies differ at all, for instance if the boxed one null-checks and returns early,
downstream callers change behaviour with no warning. The related measured case is
`reserveWide(long)` versus `reserveWide(Integer)` given an `int`, which picks the `long` overload,
because widening is a phase-1 conversion and boxing is not.

</details>

**Q5.** `Integer.TYPE` — what is it, and where does it bite?

<details><summary>Answer</summary>

`TYPE` is a `public static final Class` field on each wrapper holding the `Class` object for the
**primitive**, and it is the same object the class literal denotes: measured, `Integer.TYPE ==
int.class` is true, `Boolean.TYPE` prints `boolean`, `Character.TYPE` prints `char`. It is not
`Integer.class`. It bites in reflection: to look up `reserve(int)` you must pass `int.class` or
`Integer.TYPE` to `getDeclaredMethod`, and passing `Integer.class` throws `NoSuchMethodException`
even though ordinary call sites box happily. The same asymmetry shows up reading
`Method.getParameterTypes()` back — a primitive parameter reports as `int`, never as
`java.lang.Integer`.

</details>

**Q6.** Which wrappers implement `ConstantDesc`, and why is it not all eight?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: all eight implement `Constable`, but only `Integer`, `Long`, `Float` and
`Double` implement `ConstantDesc`. `Constable` means "an instance of this class can be described by
a nominal constant descriptor"; `ConstantDesc` means "an instance of this class *is* such a
descriptor". The class file's loadable-constant kinds are `int`, `long`, `float`, `double` and
`String` (plus the method-handle and method-type kinds), so only those four wrapper types can stand
in as the descriptor for a constant-pool entry. `Byte`, `Short`, `Character` and `Boolean` have no
class-file constant kind of their own — a `boolean` constant is an `int` in the constant pool — so
they can be described but cannot be a description.

</details>

**Q7.** When should a QuizStakes field be `Integer` rather than `int`?

<details><summary>Answer</summary>

When absence is a distinct, meaningful state from zero, or when the value has to sit in a reference
slot. `Integer bonusCapMinorUnits` earns the wrapper because "no cap configured" is genuinely
different from "a cap of 0", and a JPA or JSON mapping needs somewhere to put `null`. A collection
element, a `Map` key or value, and a generic type argument all force the wrapper, because generics
have no primitive instantiation before Valhalla. Everywhere else the primitive wins: a local, a loop
counter, a field with a natural zero, and above all an accumulator. The accumulator case is not a
style preference — measured, a `Long sum` folding 1,000,000 elements allocates 24,000,000 bytes
where the `long` version allocates 0, because the loop body unboxes with `longValue()`, adds, and
reboxes with `Long.valueOf` on every iteration. Over the 2.8M stake reservations a day this platform
handles, that is the difference between free and not.

</details>

---

## Open questions

- **Whether the `Character`/`Boolean` exclusion from `Number` is documented anywhere as a design
  decision.** Established: the exclusion is measured fact on JDK 21.0.7, and `Number`'s six methods
  have no honest implementation for `boolean` and only a misleading one for `char`. The reasoning in
  this file is my derivation from that contract, not a quotation. Would settle it: an archived Java
  1.0 design note or a JDK bug entry on the question.

---

**Leaves covered:** 1.9.1, 1.9.2 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 834
