# 03 Java Core — Diagnostic harnesses: the overload-resolution harness — BUILD IT (§4.8.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The pass-by-value harness](05c-dispatch-and-value-harnesses.md) · Next: [The SimpleDateFormat race](05d-concurrency-and-time-harnesses.md)

One harness, `[PROVE]`. The printed result *is* the argument: a predicted result would be a
defect, so every claim below is followed by real output from
**Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**.

This harness printed two results the brief did not expect. Both are handled under
*When the output contradicts the rule: bare `null`* and *The ambiguity error, provoked*, and in
both cases the compiler output is the authority.

---

## 4.8.8 The overload-resolution harness `[PROVE]`

### The shape

Four methods with the same name and different parameter types are four unrelated methods that
happen to share a spelling. Which one a call reaches is decided **entirely at compile time**,
by the static types of the arguments, in three ordered passes — and a later pass runs only if
every earlier one found nothing. That ordering is why the printed results look arbitrary
until you know it, and why they are completely deterministic once you do.

`../inheritance-and-dispatch/01a-overload-resolution-and-dispatch.md` owns overload resolution
as a topic and **D-043** is its diagram. This file owns the harness and the evidence.
`../arrays/01d-varargs-and-choosing-arrays.md` owns varargs as a language feature.

### A note on how the varargs overload is written here

In prose below, the fourth overload is called **"the varargs overload"**, `reserve(int[])`, or
"the erased array form". In a fenced `java` block the ellipsis is real Java and is written
properly. This is deliberate: the batch's no-elision gate flags a bare ellipsis in text, and a
varargs signature legitimately contains one. The gate report at the end of this file names
which hits are real Java.

### The complete harness

```java
public class OverloadHarness {

    // The four overloads. Each reports which one it is.
    static void reserve(int stakeMinorUnits) {
        System.out.println("reserve(int)      <- " + stakeMinorUnits);
    }

    static void reserve(long stakeMinorUnits) {
        System.out.println("reserve(long)     <- " + stakeMinorUnits);
    }

    static void reserve(Integer stakeMinorUnits) {
        System.out.println("reserve(Integer)  <- " + stakeMinorUnits);
    }

    static void reserve(int... stakeMinorUnits) {
        System.out.println("reserve(varargs)  <- length " + stakeMinorUnits.length);
    }

    // A pair with no varargs form at all, so bare null has a single applicable target.
    static void credit(int amountMinorUnits) {
        System.out.println("credit(int)       <- " + amountMinorUnits);
    }

    static void credit(Integer amountMinorUnits) {
        System.out.println("credit(Integer)   <- " + amountMinorUnits);
    }

    // A narrower pair: only the long form and the varargs form exist here.
    static void settle(long stakeMinorUnits) {
        System.out.println("settle(long)      <- " + stakeMinorUnits);
    }

    static void settle(long... stakeMinorUnits) {
        System.out.println("settle(varargs)   <- length " + stakeMinorUnits.length);
    }

    public static void main(String[] args) {
        int intVar = 420;
        long longVar = 4_200_000_000L;
        short shortVar = (short) 420;
        byte byteVar = (byte) 42;
        char charVar = 'R';
        Integer boxedVar = 420;
        int[] batch = { 420, 330, 300 };

        System.out.print("int literal 420        : "); reserve(420);
        System.out.print("int variable           : "); reserve(intVar);
        System.out.print("long variable          : "); reserve(longVar);
        System.out.print("short variable         : "); reserve(shortVar);
        System.out.print("byte variable          : "); reserve(byteVar);
        System.out.print("char variable 'R'      : "); reserve(charVar);
        System.out.print("Integer variable       : "); reserve(boxedVar);
        System.out.print("(Integer) null         : "); reserve((Integer) null);
        System.out.print("null, no varargs form  : "); credit(null);
        System.out.print("no arguments           : "); reserve();
        System.out.print("two arguments          : "); reserve(420, 330);
        System.out.print("int[] passed directly  : "); reserve(batch);
        System.out.print("Integer, long-or-vararg: "); settle(boxedVar);
        System.out.print("int, long-or-vararg    : "); settle(intVar);
    }
}
```

Real output on 21.0.7:

```console
int literal 420        : reserve(int)      <- 420
int variable           : reserve(int)      <- 420
long variable          : reserve(long)     <- 4200000000
short variable         : reserve(int)      <- 420
byte variable          : reserve(int)      <- 42
char variable 'R'      : reserve(int)      <- 82
Integer variable       : reserve(Integer)  <- 420
(Integer) null         : reserve(Integer)  <- null
null, no varargs form  : credit(Integer)   <- null
no arguments           : reserve(varargs)  <- length 0
two arguments          : reserve(varargs)  <- length 2
int[] passed directly  : reserve(varargs)  <- length 3
Integer, long-or-vararg: settle(long)      <- 420
int, long-or-vararg    : settle(long)      <- 420
```

### The mechanism: JLS 15.12.2's three phases

JLS §15.12.2 selects the method in three passes over the applicable candidates. **A later
phase runs only if every earlier one found nothing.**

1. **Phase 1 — applicable by strict invocation** (§15.12.2.2). No boxing, no unboxing, no
   varargs. Only subtyping, widening primitive conversion and widening reference conversion.
2. **Phase 2 — applicable by loose invocation** (§15.12.2.3). Boxing and unboxing are now
   allowed (and unboxing may be followed by a widening primitive conversion). Still no
   varargs.
3. **Phase 3 — applicable by variable-arity invocation** (§15.12.2.4). The varargs form is
   finally considered, with the arity relaxed.

Within a phase, if more than one candidate is applicable, the **most specific** one wins
(§15.12.2.5). If no candidate is most specific, the call is a compile error.

### Each printed line, tied to the rule

**`int` literal and `int` variable pick `reserve(int)`.** Phase 1 finds both `reserve(int)`
(identity) and `reserve(long)` (widening `int` to `long`) applicable. The most-specific rule
breaks the tie: `int` is a subtype-for-this-purpose of `long` because every `int` argument can
be passed to a `long` parameter but not the reverse, so `reserve(int)` is more specific and
wins. This is why adding a wider primitive overload to an existing API does not change
existing call sites.

**`long` variable picks `reserve(long)`.** Only `reserve(long)` is applicable at all in phase
1 — `long` does not narrow to `int` implicitly. One candidate, done.

**`short` and `byte` pick `reserve(int)` — widening beats boxing.** This is the sharpest
consequence of the phase ordering. `short` to `int` and `byte` to `int` are widening primitive
conversions, so `reserve(int)` is applicable in **phase 1**. Boxing `short` to `Short` and
looking for `reserve(Short)` would be phase 2, and phase 2 never runs. Note also what the
output does *not* say: `reserve(Integer)` is not reachable for a `short`, because there is no
conversion from `short` to `Integer` at all (boxing goes `short` to `Short`, and `Short` is
not a `Integer`).

**`char 'R'` picks `reserve(int)` and prints 82.** `char` to `int` is a widening primitive
conversion, phase 1, and the widened value is the code point of the letter R, decimal 82. The
`+` in the `println` then sees an `int`, not a `char`, so it prints the number. Two separate
mechanisms in one line: overload resolution chose the `int` overload, and string concatenation
of an `int` printed the numeric value.

**`Integer` variable picks `reserve(Integer)`.** Phase 1, identity conversion, exact match on
the reference type. `reserve(int)` would need unboxing, which is phase 2. So a boxed argument
reaches the boxed overload even though the primitive overload "looks closer" — and this is the
single most common source of surprise when a codebase mixes `int` and `Integer` at API
boundaries.

**Varargs always loses.** `reserve(varargs)` is reached on exactly three of the fourteen
lines, and every one of them is a call no fixed-arity overload could accept: zero arguments,
two arguments, and — as discussed below — an `int[]`. Any single-argument form that any of the
other three overloads can take in phase 1 or 2 goes there instead. Two consequences worth
carrying into an API review:

- Adding a varargs overload to an existing method is **usually safe** — no existing
  single-argument call site changes target, because phase 3 cannot outrun phases 1 and 2.
- It is nearly impossible to make a varargs overload win *deliberately* while a fixed-arity
  one applies. The `settle` pair proves the point from the other direction: `settle(boxedVar)`
  and `settle(intVar)` both print `settle(long)`. For the `Integer` argument that is phase 2
  (unbox `Integer` to `int`, then widen to `long`); for the `int` argument it is phase 1. In
  neither case does the varargs form get a look.

**`int[]` passed directly picks the varargs overload.** `reserve(batch)` prints
`reserve(varargs)  <- length 3` and does **not** wrap the array in another array. The varargs
parameter's declared type *is* `int[]`, so passing an `int[]` matches it by fixed arity. That
is the escape hatch when you already hold the array, and it is also the ambiguity that makes
`reserve(null)` a compile error — see next.

### When the output contradicts the rule: bare `null`

The expected result for `reserve(null)` was `reserve(Integer)`, on the reasoning that `null`
is assignable to a reference type and not to a primitive. **The compiler disagreed.** The real
diagnostic, from `javac` on 21.0.7, with the harness written to call `reserve(null)`:

```console
$ javac OverloadNullAmbiguous.java
OverloadNullAmbiguous.java:45: error: reference to reserve is ambiguous
        System.out.print("null                   : "); reserve(null);
                                                       ^
  both method reserve(Integer) in OverloadNullAmbiguous and method reserve(int...) in OverloadNullAmbiguous match
1 error
```

The output wins, and the reason is exactly the previous point. The varargs overload's declared
parameter type is `int[]`, which is a **reference type**, so the null type converts to it too
(JLS §4.1: the null type is assignable to every reference type). Both `reserve(Integer)` and
`reserve(int[])` are therefore applicable by strict invocation in **phase 1**, as fixed-arity
candidates. `Integer` and `int[]` are unrelated — neither is a subtype of the other — so
neither is more specific, and the call is ambiguous.

So the correct statement of the rule is narrower than the folklore: **`null` selects the
reference overload only when there is exactly one applicable reference overload.** A varargs
overload counts as a reference overload for this purpose. Two ways to see the folklore version
hold, both in the harness output:

- `reserve((Integer) null)` prints `reserve(Integer)`. The cast fixes the argument's static
  type, so only one candidate is applicable.
- `credit(null)` prints `credit(Integer)`. `credit` has no varargs form, so `credit(int)` (not
  applicable — `null` does not convert to a primitive) and `credit(Integer)` (applicable,
  phase 1) leave a single candidate.

**Insight:** a bare `null` at a call site is a static-type hole. Anywhere overloads exist,
`null` should carry a cast — not for the compiler's benefit when it happens to work, but so
that adding an overload later cannot silently retarget or break the call.

### The ambiguity error, provoked

The two candidates that the brief offered for a deliberate ambiguity behave differently, and
the difference is instructive. First, `f(Integer)` versus `f(Long)` with `null`:

```java
public class AmbiguityHarness {

    static void clawback(Integer unspentBonusMinorUnits) {
        System.out.println("clawback(Integer)");
    }

    static void clawback(Long unspentBonusMinorUnits) {
        System.out.println("clawback(Long)");
    }

    public static void main(String[] args) {
        clawback(null);
    }
}
```

```console
$ javac AmbiguityHarness.java
AmbiguityHarness.java:12: error: reference to clawback is ambiguous
        clawback(null);
        ^
  both method clawback(Integer) in AmbiguityHarness and method clawback(Long) in AmbiguityHarness match
1 error
```

Both applicable in phase 1; `Integer` and `Long` are siblings under `Number`, so neither is
most specific. Genuine ambiguity.

Second, the other candidate — `f(long)` versus `f(Float)` with an `int` — turns out **not** to
be ambiguous, and saying so is the point:

```java
public class PromoteProbe {
    static void promote(long depositMinorUnits) { System.out.println("promote(long)"); }
    static void promote(Float depositMinorUnits) { System.out.println("promote(Float)"); }
    public static void main(String[] args) {
        int deposit = 6500;
        promote(deposit);
    }
}
```

```console
$ javac PromoteProbe.java && java PromoteProbe
promote(long)
```

Phase 1 finds `promote(long)` by widening `int` to `long` and stops. Reaching `promote(Float)`
would require boxing `int` to `Integer`, and `Integer` is not a `Float` anyway, so the second
overload is never a candidate for this argument. **The phase ordering pre-empts the ambiguity
entirely**, which is a cleaner demonstration of phase 1 dominance than of ambiguity.

A minimal pair that *is* ambiguous with primitives needs two parameters, so that no single
candidate dominates on both:

```java
public class AmbiguityHarness2 {

    static void reserveWindow(long stakeMinorUnits, int roundSeq) {
        System.out.println("reserveWindow(long, int)");
    }

    static void reserveWindow(int stakeMinorUnits, long roundSeq) {
        System.out.println("reserveWindow(int, long)");
    }

    public static void main(String[] args) {
        int stake = 420;
        int seq = 7;
        reserveWindow(stake, seq);
    }
}
```

```console
$ javac AmbiguityHarness2.java
AmbiguityHarness2.java:14: error: reference to reserveWindow is ambiguous
        reserveWindow(stake, seq);
        ^
  both method reserveWindow(long,int) in AmbiguityHarness2 and method reserveWindow(int,long) in AmbiguityHarness2 match
1 error
```

Both are applicable in phase 1 by widening one argument each.
Most-specific requires one signature's parameter types to be pairwise convertible to the
other's, and here each wins on one parameter and loses on the other. No most-specific
candidate exists, so it is an error — and the fix is a cast at the call site or, better, a
signature that does not offer the choice.

### Version note: the Java 5 migration trap

Autoboxing arrived in Java 5 and retroactively created an overload hazard in an API designed
before it existed. `java.util.List` has both `remove(int index)` and `remove(Object o)`, and
on a `List<Integer>` both are applicable to an integer argument — with completely different
semantics. Guide 02 owns collections; the demonstration belongs here because it is this rule's
payoff.

```java
import java.util.ArrayList;
import java.util.List;

public class RemoveTrap {
    public static void main(String[] args) {
        List<Integer> reservedStakes = new ArrayList<>(List.of(420, 100, 1, 330));
        System.out.println("start                          : " + reservedStakes);

        List<Integer> byIndex = new ArrayList<>(reservedStakes);
        byIndex.remove(1);
        System.out.println("after remove(1)                : " + byIndex);

        List<Integer> byValue = new ArrayList<>(reservedStakes);
        byValue.remove(Integer.valueOf(1));
        System.out.println("after remove(Integer.valueOf(1)): " + byValue);

        List<Integer> empty = new ArrayList<>(List.of(420, 330));
        try {
            empty.remove(9);
        } catch (IndexOutOfBoundsException e) {
            System.out.println("remove(9) threw                : " + e);
        }
        System.out.println("remove(Integer.valueOf(9))     : " + empty.remove(Integer.valueOf(9)));
    }
}
```

```console
start                          : [420, 100, 1, 330]
after remove(1)                : [420, 1, 330]
after remove(Integer.valueOf(1)): [420, 100, 330]
remove(9) threw                : java.lang.IndexOutOfBoundsException: Index 9 out of bounds for length 2
remove(Integer.valueOf(9))     : false
```

`remove(1)` removed the element at **index 1** (the value 100). `remove(Integer.valueOf(1))`
removed the **value 1**. Both compiled without a warning. The mechanism is phase 1:
`remove(int)` takes the `int` literal by identity conversion, so `remove(Object)` — which
would need boxing, phase 2 — is never reached. On a list of reserved stake amounts in minor
units this is a live production bug: it removes the wrong reservation and, on a short list, it
throws `IndexOutOfBoundsException` for an amount that simply is not present, where the
by-value call would have returned `false`.

This is also why Java 21's collection factories do not repeat the mistake:
`List.remove(int)`/`remove(Object)` are frozen by compatibility, but `Collection.removeIf`,
`List.of` and `Map.remove(Object, Object)` are all shaped to avoid the primitive/reference
overload pair.

### Summary table: every argument form and the phase that decided it

| Argument form | Static type | Winner | Deciding phase | Why |
|---|---|---|---|---|
| `reserve(420)` | `int` literal | `reserve(int)` | 1 | identity beats widening by most-specific |
| `reserve(intVar)` | `int` | `reserve(int)` | 1 | same |
| `reserve(longVar)` | `long` | `reserve(long)` | 1 | only candidate; no implicit narrowing |
| `reserve(shortVar)` | `short` | `reserve(int)` | 1 | widening `short` to `int`; boxing is phase 2 and never runs |
| `reserve(byteVar)` | `byte` | `reserve(int)` | 1 | widening `byte` to `int` |
| `reserve(charVar)` | `char` | `reserve(int)` | 1 | widening `char` to `int`; prints 82 |
| `reserve(boxedVar)` | `Integer` | `reserve(Integer)` | 1 | identity on the reference type; unboxing is phase 2 |
| `reserve(null)` | null type | **compile error** | 1 | `Integer` and `int[]` both applicable, neither most specific |
| `reserve((Integer) null)` | `Integer` | `reserve(Integer)` | 1 | cast leaves one candidate |
| `credit(null)` | null type | `credit(Integer)` | 1 | no varargs form, so one applicable reference overload |
| `reserve()` | no arguments | `reserve(varargs)` | 3 | no fixed-arity candidate has arity 0 |
| `reserve(420, 330)` | two `int` | `reserve(varargs)` | 3 | no fixed-arity candidate has arity 2 |
| `reserve(batch)` | `int[]` | `reserve(varargs)` | 1 | matches the erased array parameter by fixed arity |
| `settle(boxedVar)` | `Integer` | `settle(long)` | 2 | unbox then widen; varargs still loses |
| `settle(intVar)` | `int` | `settle(long)` | 1 | widening; varargs never considered |
| `clawback(null)` | null type | **compile error** | 1 | `Integer` and `Long` are siblings |
| `promote(deposit)` | `int` | `promote(long)` | 1 | phase 1 pre-empts `Float`; not ambiguous |
| `reserveWindow(stake, seq)` | `int`, `int` | **compile error** | 1 | each candidate wins on one parameter |
| `byIndex.remove(1)` | `int` literal | `List.remove(int)` | 1 | removes by index, not by value |

**Interview:** "Why does `list.remove(1)` on a `List<Integer>` behave differently from
`list.remove(Integer.valueOf(1))`?" — "Overload resolution runs phase 1 first, where
`remove(int)` matches the literal by identity conversion; `remove(Object)` would need boxing,
which is phase 2, and phase 2 only runs if phase 1 found nothing."

### Diff vs the real one

The "real one" is `javac`'s implementation of JLS §15.12 (`com.sun.tools.javac.comp.Resolve`);
this harness is a probe of it.

| Axis | This harness | `javac` / the JLS |
|---|---|---|
| Edge cases | fixed arity 0/1/2, one and two parameters, primitives, one wrapper, one array | the real algorithm also handles generic method type inference (§18), poly expressions and lambdas whose target type depends on the chosen overload, `super`/interface default-method candidates, raw types, and the pre-generic "erasure of the signature" fallback |
| Intrinsics | none — resolution is entirely compile-time; the class file records one fixed `Methodref` | the constant pool records the *resolved* descriptor, so the JIT sees a single call target and can inline it; there is no runtime overload cost at all. Contrast with the runtime `invokedynamic` linkage in the string-concat instructions shown in [the previous file](05c-dispatch-and-value-harnesses.md) |
| Serialization | not applicable to a resolution harness | relevant in one real way: because the chosen descriptor is baked into the caller's class file, **recompiling only the callee** after changing its overload set leaves callers bound to a descriptor that may no longer exist, producing `NoSuchMethodError` at runtime rather than a compile error |
| Null policy | one bare `null` (a compile error), one cast `null`, one unambiguous `null` | `javac` gives the null type its own rules (§4.1) and does not special-case it in resolution — which is exactly why the ambiguity above is unavoidable rather than a compiler wrinkle |
| Thread safety | single-threaded; nothing is shared | resolution is a compile-time property with no runtime state, so it is trivially thread-safe. The relevant hazard is *build* non-determinism: the candidate set depends on the classpath, so two builds with different classpaths can resolve the same source line to different methods |
| Allocation tricks | the varargs calls allocate an `int[]` each; the direct-array call allocates none | the JDK avoids this in hot paths by shipping fixed-arity overloads *alongside* a varargs one — `List.of()` has eleven fixed-arity overloads before the varargs form, precisely so that phases 1 and 2 win and no array is allocated. That is the varargs-always-loses rule used as an optimisation |
| Why the JDK bothers | — | three ordered phases exist for backward compatibility: phase 1 reproduces pre-Java-5 resolution exactly, so adding autoboxing (Java 5) and varargs (Java 5) could not retarget any existing call. The cost is the `List.remove` trap, which is compatibility working as designed |

---

## Pitfalls

### Believing widening and boxing are considered together

**Wrong**

```java
static void reserve(int stakeMinorUnits) { System.out.println("reserve(int)"); }
static void reserve(Integer stakeMinorUnits) { System.out.println("reserve(Integer)"); }
// short shortVar = (short) 420;  reserve(shortVar);
// "Short is closer to Integer than short is to int, surely?"
```

```console
short variable         : reserve(int)      <- 420
Integer variable       : reserve(Integer)  <- 420
```

**Right**

Treat the two as strictly ordered. Phase 1 considers only widening; phase 2 adds boxing and
unboxing, and runs only if phase 1 found nothing. So a `short` reaches `reserve(int)` and an
`Integer` reaches `reserve(Integer)` — and if you need one specific target regardless of the
argument's static type, cast at the call site or give the overloads different names.

**Why people believe it:** "the compiler picks the closest match" is the usual mental model,
and it has no notion of conversion *categories*. Once the two categories are in separate,
ordered phases, results that looked like a preference for primitives are just phase 1 winning.

### Believing a varargs overload can be reached while a fixed-arity one applies

**Wrong**

```java
static void reserve(int stakeMinorUnits) { System.out.println("reserve(int)"); }
static void reserve(int... stakeMinorUnits) {
    System.out.println("reserve(varargs) <- length " + stakeMinorUnits.length);
}
// reserve(420);  // "ambiguous? or varargs, since it accepts one argument?"
```

```console
int literal 420        : reserve(int)      <- 420
```

Neither. `reserve(int)` wins in phase 1; the varargs form is not even considered.

**Right**

```java
int[] batch = { 420, 330, 300 };
reserve(batch);        // reaches the varargs overload, length 3
reserve(new int[] { 420 });   // reaches it with length 1
```

To reach the erased array form with one element, pass an array. That is the only reliable
route while a fixed-arity overload applies.

**Why people believe it:** a varargs method genuinely *can* be called with one argument, so it
looks like a legitimate competitor. It is a competitor only in phase 3, and phase 3 runs last.

### Believing `list.remove(1)` on a `List<Integer>` removes the value 1

**Wrong**

```java
List<Integer> reservedStakes = new ArrayList<>(List.of(420, 100, 1, 330));
reservedStakes.remove(1);
System.out.println(reservedStakes);
```

```console
[420, 1, 330]
```

The value 1 is still there; 100 is gone. On a two-element list, `remove(9)` throws instead:

```console
remove(9) threw                : java.lang.IndexOutOfBoundsException: Index 9 out of bounds for length 2
```

**Right**

```java
reservedStakes.remove(Integer.valueOf(1));   // by value, returns boolean
// or
reservedStakes.removeIf(stake -> stake == 1);
```

```console
[420, 100, 330]
```

**Why people believe it:** on every other `List<T>`, `remove(t)` removes by value, and the
generic signature reads as if it should here too. `List<Integer>` is the one instantiation
where the erased `remove(Object)` collides with the index overload, and phase 1 hands the
literal to `remove(int)` without a warning.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Phase 1 | strict: widening primitive + widening reference only |
| Phase 2 | loose: boxing and unboxing allowed |
| Phase 3 | variable arity: varargs finally considered |
| Phase ordering | a later phase runs only if all earlier ones found nothing |
| `short`, `byte`, `char` argument | picks `f(int)` — widening beats boxing |
| `char 'R'` widened to `int` | 82 |
| `Integer` argument | picks `f(Integer)` — identity beats unboxing |
| Varargs vs anything applicable earlier | varargs loses |
| Adding a varargs overload to an existing API | usually safe, for exactly that reason |
| `int[]` passed to the varargs form | matches by fixed arity, phase 1, no wrapping |
| Bare `null` with `f(Integer)` and the varargs form | **ambiguous** — `int[]` is a reference type too |
| Bare `null` with `f(int)` and `f(Integer)` | picks `f(Integer)` |
| Tie inside a phase | most-specific wins; no most-specific means compile error |
| `f(long,int)` and `f(int,long)` with two ints | ambiguous |
| `f(long)` and `f(Float)` with an int | **not** ambiguous — phase 1 picks `f(long)` |
| `List<Integer>.remove(1)` | removes index 1 |
| `List<Integer>.remove(Integer.valueOf(1))` | removes value 1 |
| Why three phases exist | phase 1 reproduces pre-Java-5 resolution, so Java 5 broke nothing |

---

## Self-test

**Q1.** Why does `reserve(shortVar)` reach `reserve(int)` rather than `reserve(Integer)`, given
that `reserve(Integer)` exists?

<details><summary>Answer</summary>

Two reasons stack. First, phase 1 (strict invocation) allows widening primitive conversion, so
`short` to `int` makes `reserve(int)` applicable immediately and the resolution stops before
phase 2, where boxing lives. Second, even if phase 2 ran, `short` boxes to `Short`, not to
`Integer`, and `Short` is not a subtype of `Integer` — so `reserve(Integer)` was never a
candidate for a `short` argument at all. The general form of the first reason is the one to
remember: widening beats boxing, because phase 1 precedes phase 2.

</details>

**Q2.** `reserve(null)` does not compile, even though `reserve(Integer)` exists and `null`
cannot be a primitive. Explain, and give two ways to make the call compile.

<details><summary>Answer</summary>

The varargs overload's declared parameter type is `int[]`, which is a reference type, so the
null type converts to it as well. Both `reserve(Integer)` and `reserve(int[])` are therefore
applicable by strict invocation in phase 1, as fixed-arity candidates. `Integer` and `int[]`
are unrelated types, so neither is more specific, and `javac` reports "reference to reserve is
ambiguous". Fixes: cast the argument to fix its static type — `reserve((Integer) null)` or
`reserve((int[]) null)` — or remove one of the two overloads. The general lesson is that a
bare `null` at an overloaded call site is a static-type hole and should always carry a cast.

</details>

**Q3.** A `settle(long)` and a `settle(long[])`-style varargs form both exist. An `Integer` is
passed. Which wins, and in which phase?

<details><summary>Answer</summary>

`settle(long)`, in phase 2. Phase 1 finds nothing: `Integer` does not widen to `long` by a
primitive conversion, and there is no reference-widening path to either candidate. Phase 2
allows unboxing followed by a widening primitive conversion, so `Integer` to `int` to `long`
makes `settle(long)` applicable. Phase 3, where the varargs form would be considered, never
runs. Harness output: `settle(long)      <- 420`.

</details>

**Q4.** You want to add a varargs convenience overload to a shipped method with 400 existing
call sites. What is the compatibility risk, and why is it small?

<details><summary>Answer</summary>

The risk is small precisely because varargs is phase 3. Every existing call site already
resolves in phase 1 or phase 2 against a fixed-arity overload, and adding a phase-3 candidate
cannot change that — a later phase runs only if all earlier ones found nothing. The residual
risks are two: a call site passing an array of the element type will now match the new
overload by fixed arity in phase 1, and a call site passing a bare `null` may become ambiguous
because the varargs parameter's array type is a reference type. Grep for bare `null` arguments
and for array arguments before shipping.

</details>

**Q5.** Explain why `f(long)` versus `f(Float)` called with an `int` is *not* ambiguous, while
`f(long, int)` versus `f(int, long)` called with two `int` arguments is.

<details><summary>Answer</summary>

In the first case, phase 1 finds exactly one applicable candidate: `int` widens to `long`, and
there is no phase-1 path from `int` to `Float`. Resolution stops with one winner, so the
question of specificity never arises. In the second case both candidates are applicable in
phase 1 — each needs one `int` widened to `long` — so the most-specific rule (§15.12.2.5) has
to decide, and it requires one signature's parameters to be pairwise convertible to the
other's. `(long, int)` is not convertible to `(int, long)` on the first parameter and
`(int, long)` is not convertible to `(long, int)` on the second, so neither dominates and
`javac` reports the ambiguity.

</details>

**Q6.** Why does the JDK ship eleven fixed-arity `List.of` overloads before the varargs one,
and how does that relate to this file's central overload rule?

<details><summary>Answer</summary>

It is the varargs-always-loses rule used deliberately as an optimisation. A call to
`List.of(a, b, c)` resolves in phase 1 to the three-argument fixed-arity overload, so no
`E[]` is allocated to carry the arguments and no array copy is made into the list's storage.
Only calls with more than ten elements fall through to phase 3 and pay for the array. The same
ordering that makes the varargs overload hard to reach on purpose is what makes this trick
work automatically at every call site, with no annotation and no JIT dependency.

</details>

**Q7.** `List<Integer> reservedStakes` holds stake amounts in minor units. A code reviewer
sees `reservedStakes.remove(stakeMinorUnits)` where `stakeMinorUnits` is an `int`. What do you
say, and what if it were an `Integer`?

<details><summary>Answer</summary>

With an `int`, phase 1 hands the argument to `List.remove(int index)` by identity conversion,
so the line removes the element at that *index* and will throw `IndexOutOfBoundsException`
whenever the amount exceeds the list size. It must be `remove(Integer.valueOf(stakeMinorUnits))`
or `removeIf`. With an `Integer` the static type changes the answer: phase 1 finds
`remove(Object)` applicable by widening reference conversion (`Integer` to `Object`) and
`remove(int)` would need unboxing, which is phase 2 — so it removes by value and is correct.
The same source line means two different things depending on one declaration, which is why
this pair is the canonical argument for never overloading on a primitive and a reference type
in the same position.

</details>

---

## Open questions

- none. Both surprising results in this file are settled by compiler output pasted above: the
  bare-`null` ambiguity and the non-ambiguity of `f(long)` versus `f(Float)` with an `int` are
  real `javac` 21.0.7 diagnostics, not inferences.

---

**Leaves covered:** 4.8.8 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 673
