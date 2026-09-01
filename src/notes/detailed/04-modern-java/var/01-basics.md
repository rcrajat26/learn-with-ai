# 04 Modern Java — `var` — BASICS (§1.12)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [`Optional` — internals optional](../optional/03-internals-optional.md) · Next: [`var` — in practice](02-in-practice.md)

## Why this file exists

`var` looks like the smallest feature in modern Java — one reserved word, no new
runtime behaviour, nothing on the class file that wasn't already there. That is
exactly why it survives on folklore: engineers who learned it from a 2019 blog
post still say "it's like `dynamic` in C#" or "the compiler figures out the type
at runtime," and both are wrong in ways that show up the moment an interviewer
asks a two-line follow-up. This file is the mechanism underneath the convenience:
where the compiler is allowed to infer, where it refuses, why `var x = null`
cannot compile even though `Object x = null` compiles fine, and why the very
first thing `javac` does with `var` is throw the word away.

### The map before the mechanism

Before any mechanism, the legality surface — where `var` is permitted and where
it is flatly rejected, with the exact diagnostic and the reason:

| Position | Legal? | Since | Compile error if illegal | Reason |
|---|---|---|---|---|
| Local with initialiser (`var x = 1;`) | Yes | Java 10 (JEP 286) | — | The initialiser expression gives the compiler a type to copy. |
| Enhanced-`for` variable (`for (var e : list)`) | Yes | Java 10 | — | The element type of the iterated expression is the initialiser. |
| Classic `for` index (`for (var i = 0; ...)`) | Yes | Java 10 | — | The init-clause expression is the initialiser. |
| Try-with-resources resource (`try (var c = ...))`) | Yes | Java 10 | — | The resource expression is the initialiser. |
| Lambda parameter (`(var x) -> ...`) | Yes | Java 11 (JEP 323) | — | The functional interface's descriptor supplies the type; see §5 below. |
| Field (instance or static) | No | — | `'var' is not allowed here` | Fields are part of a class's binary contract; their type must be spellable in a signature other code links against. `var` is not a type name that can appear there. |
| Method parameter (ordinary method, not lambda) | No | — | `'var' is not allowed here` | Same contract reason — a method descriptor needs a real type. |
| Return type | No | — | `'var' is not allowed here` | Same reason again — callers link against the descriptor. |
| `catch` parameter | No | — | `'var' is not allowed here` | The exception type participates in exhaustiveness and multi-catch static checking; it must be a real, denotable type up front. |
| Local without initialiser (`var x;`) | No | — | `cannot infer type for local variable x` / `(cannot use 'var' on variable without initializer)` | There is nothing on the right-hand side to copy a type from. |
| `var x = null;` | No | — | `cannot infer type for local variable x` / `(variable initializer is 'null')` | The null type has no denotable spelling — see §3. |
| Array-initialiser shorthand (`var arr = {1,2,3};`) | No | — | `cannot infer type for local variable arr` / `(array initializer needs an explicit target-type)` | `{1,2,3}` is not an expression with a standalone type; it only means something once an array type gives it context. |
| Generic type argument (`List<var> xs;`) | No | — | `'var' is not allowed here` | `var` is reserved only for the small set of declaration positions above; a type-argument position is not one of them. |

**D-049** — Where `var` is legal and where it is not

Every row above is a real `javac --release 21` compile run on this machine —
this is not a summary of the spec, it is the spec exercised. Keep this table
open mentally while reading the rest of the file: every concept below is one
row of it, worked in depth.

---

## 1. `var` is compile-time-only local type inference — there is no runtime cost

**Mental model.** `var` is a note left for the compiler in the source file, and
the compiler erases the note before anything downstream ever sees it. Think of
it as a sticky note on a whiteboard that says "figure out what goes here from
the next line" — once the whiteboard is photographed (compiled), the sticky
note is gone and only the answer remains. The class file that comes out the
other end of `javac` does not know `var` was ever typed. There is no `Object`
box, no boxing/unboxing indirection, no reflective lookup at first use — the
slot in the method's local variable array has the concrete inferred type from
the first bytecode instruction that touches it.

**Why it exists.** Java shipped fifteen major versions (1995–2016) requiring an
explicit type at every local declaration, even when the right-hand side made
the type visually redundant:

```java
Map<ClientId, List<Restriction>> restrictionsByClient = new HashMap<ClientId, List<Restriction>>();
```

Generics (Java 5) made this worse before the diamond operator (Java 7) made it
slightly better — the type still had to be written twice, once as the
declared type and once (partially) in the constructor call. JEP 286 (delivered
in Java 10, "Local-Variable Type Inference") let the declared type be omitted
wherever the compiler can already recover it from the initialiser, closing the
gap between what a human needs to read and what the compiler is contractually
owed. This is deliberately narrow: Java did not adopt full Hindley-Milner-style
inference or bidirectional inference across a whole method body — only the one
local-declaration site, from one initialiser expression, in one direction
(right-hand side determines left-hand side, never the reverse).

**When to reach for it, and when not.** Reach for `var` when the initialiser
already states the type in a form a reader can see without a hover — a
constructor call, a well-named factory method, an explicit cast. Do **not**
reach for it when the initialiser's return type is opaque (`repository.find(id)`
tells the reader nothing about what comes back), when the concrete type of the
value must be visible for a numeric-width reason, or when omitting the type
would force the reader to open another file to know what a variable holds.
§6 below (`var` and numeric literals) and the closing concept on this file (when
`var` hurts) work through both directions in detail. The sibling that wins where
`var` loses is simply the explicit type — there is no third option in Java for a
local declaration.

**How it works.** Inference happens once, during type-checking, before code
generation, and it happens in exactly one direction. The compiler evaluates the
static type of the initialiser expression under ordinary Java typing rules
(promotions, boxing, generic instantiation, all of it) and then writes that
resolved type into the symbol table entry for the local — as if you had typed
it yourself. From that point on, `var` is not merely invisible, it is *gone*:
every later reference to the variable is type-checked against the resolved
concrete type, and code generation never sees the token `var` at all. This is
why the two class files below are indistinguishable except for the
compilation-unit's own name string.

**D-049** — see the table opening this file for the full legality surface this
concept sits inside; the row relevant here is simply "any position marked
legal, the compiler always resolves to a concrete type before code generation."

**A minimal concrete example — worked, not merely asserted.** Two source files
that differ only in whether the local has an explicit type or `var`:

```java
// T1a.java
import java.math.BigDecimal;
public class T1a {
    public static void main(String[] args) {
        BigDecimal stake = new BigDecimal("4.20");
        System.out.println(stake);
    }
}
```

```java
// T1b.java
import java.math.BigDecimal;
public class T1b {
    public static void main(String[] args) {
        var stake = new BigDecimal("4.20");
        System.out.println(stake);
    }
}
```

`javac --release 21` both, then `javap -c -v` both and diff the two `Code`
bodies (with the class name normalised so the diff isn't polluted by the source
file's own name): the diff is **empty**. `[BYTECODE]` Both classes carry the
identical constant pool shape — a `Methodref` for `BigDecimal(String)`, a
`Fieldref` for `System.out`, a `Methodref` for `println(Object)` — and the
identical instruction stream in `main`:

```
0: aload_0
1: invokespecial #1   // Object."<init>":()V
4: return
```

(the constructor body — the `main` method's own body is likewise
instruction-for-instruction identical between the two files, `new`,
`invokespecial <init>(String)`, `astore_1`, `getstatic System.out`, `aload_1`,
`invokevirtual println(Object)`, `return`, on both). `[PROVE]` The two class
files differ in exactly two bytes on disk — the UTF-8 constant holding the
class's own name (`T1a` vs `T1b`) — and are otherwise byte-for-byte the same
size (477 bytes each on `javac 25.0.1 --release 21`). There is no test you can
write against the running program that distinguishes a `var`-declared local
from an explicitly-typed one, because after compilation the distinction does
not exist.

**The gotcha.** People sometimes reason "`var` must be slower because the JVM
has to figure out the type," reaching for a mental model borrowed from
dynamically-typed languages. **Pitfall:** believing `var` defers type
resolution to runtime. The symptom this produces in an interview is confidently
saying "there's a small JIT warm-up cost the first time a `var` variable is
used" — there is not, because there is nothing at runtime to warm up; the
runtime type was fixed at compile time and the bytecode is identical to the
explicit-type form. **Fix:** the type is resolved once, by `javac`, before a
single class file byte is emitted; runtime performance of `var`-declared and
explicitly-typed locals is identical because the generated code is identical.

**Insight:** because `var` disappears entirely before code generation, every
question of the form "does `var` affect X" (performance, reflection,
serialization, `Class<?>` at runtime, stack traces) has the same answer:
no, because by the time X could observe anything, `var` no longer exists to be
observed.

**Interview:** "Does `var` make Java dynamically typed?" — No. Java remains
statically typed; `var` only changes who writes the type down (the compiler,
from the initialiser, once, at compile time) — it never changes when the type
is fixed or how it's enforced.

> **`var` is local-variable type inference performed once, by the compiler, at
> compile time; the resolved type is baked into the class file exactly as if it
> had been written by hand, and no later stage of compilation, linking, or
> execution can tell a `var`-declared local from an explicitly-typed one.**

---

## 2. `var` is a reserved type name, not a keyword — and not `Object`, not `dynamic`

**Mental model.** Java has three tiers of "words the compiler treats
specially": true keywords (`class`, `if`, `return` — never usable as an
identifier, anywhere, ever), contextual keywords introduced more recently
(`sealed`, `permits`, `yield`, `record` — special only in the syntactic
position where they're meaningful, ordinary identifiers everywhere else), and
`var`, which the JLS puts in a category of its own: a **reserved type name**.
It behaves like a contextual keyword but the restriction is inverted — instead
of being reserved as a *keyword* and free as a type name, `var` is reserved as
a *type name* and free almost everywhere else.

**Why it exists.** JEP 286 needed a way to spell "infer this" that would not
break a single existing Java program. Making `var` a true keyword would have
broken every codebase (and there were many, going back to early Java) with a
field, method, or local literally named `var`. JLS §3.9 solves this precisely:
`var` is not a keyword, so it never breaks existing identifier uses; it is
reserved only as a **type name**, so it cannot be declared as a class, an
interface, or used in the small set of type positions where the compiler needs
to distinguish "the type name `var`" from "the inference marker `var`."

**When to reach for it, and when not.** This is not a tool you reach for — it's
a fact you must have correctly loaded before an interviewer asks "is `var` a
keyword?" The sibling worth contrasting it against is `yield` (Java 14,
contextual keyword for switch expressions) and `sealed`/`permits`/`non-sealed`
(Java 17): all three of those are also non-reserved outside their special
syntax position, but they are keywords *within* that position rather than a
"reserved type name." The distinction matters because it tells you exactly
what remains legal: you can still write `int var = 5;` (a variable named
`var`) and `void var() {}` (a method named `var`), but you can never write
`class var {}` or use `var` as a type argument.

**How it works.** The parser recognises `var` structurally: in a position
where the grammar expects a `LocalVariableType`, `var` is read as the
inference marker if no user-declared type named `var` is in scope (and no user
program can declare a type named `var`, because that declaration itself is
illegal — `var` cannot appear where a class or interface name is expected).
Everywhere else — as the target of a variable declaration's *name*, as a
method name, as a package name element — `var` is just an identifier like any
other, because the reservation applies only to the "this token names a type"
grammar productions.

**D-049** — again the legality table above is the source of truth for exactly
which of those "type name" positions are blocked; this concept is about *why*
those specific positions are blocked and no others.

**A minimal concrete example.** Java 21, compiling cleanly, `var` used as an
identifier in three different roles simultaneously:

```java
public final class RestrictionKey {

    // "var" as a field name is illegal (it's a type-name position issue,
    // not this) — but "var" as a *local variable name* and a *method name*
    // are both fine, because those positions never ask "is this a type?".

    public static int var() {                 // method named "var" — legal
        return 10;                              // e.g. bonus percent, 10%
    }

    public static void main(String[] args) {
        int var = var();                        // local NAMED "var" — legal
        System.out.println("bonus percent = " + var);

        var bonusPortion = java.math.BigDecimal.valueOf(0.33); // "var" the
        // inference marker, in the same method as "var" the identifier —
        // the parser tells them apart purely from grammatical position.
        System.out.println(bonusPortion);
    }
}
```

This compiles under `--release 21` without a warning. The method `var()`
returning the bonus percentage, the local `int var`, and the inferring `var
bonusPortion` all coexist because none of the three positions is a "type name"
position.

**The gotcha.** **Pitfall:** believing `var` is a keyword like `int` or
`class`, which leads people to also assume — wrongly — that `var` behaves like
C#'s `var` (which *is* a keyword there, and CLR still needs a machine-verifiable
type at each site the same way) or JavaScript's `var`/`let` (genuinely
dynamically typed, no compile-time type at all). **Fix:** the correct
technical answer is "`var` is a reserved type name, not a keyword" — it is
reserved only in type-name grammar positions, and a codebase that already used
`var` as a variable, method, or package name before Java 10 continues to
compile unchanged today.

The mechanism-level reason `var` is not `Object` and not `dynamic` deserves its
own sentence, because interviewers ask it as a follow-up to "is it a keyword":
`Object` is a real, denotable reference type that participates in the type
hierarchy and requires casts to recover a narrower type; `dynamic` (C#) defers
member resolution to runtime via the DLR. `var` is neither — it resolves, at
compile time, to the same concrete static type the initialiser already had,
and the variable's type from that point on is exactly that concrete type, not
`Object` and not "resolved later." `[X-REF 03]` The deeper reason this
distinction matters for generics — how a variable's declared type interacts
with erasure and bridge methods at the bytecode level — is guide 03's
territory (Java core: generics and erasure); the one paragraph you need here is
that `var`'s resolved type undergoes exactly the same erasure as if you had
written it by hand, because by the time erasure runs, `var` has already been
replaced by that written-out type.

**Insight:** the "reserved type name, not a keyword" wording is not a semantic
technicality — it is the specific design choice that let a 20-year-old
language add a inference syntax with **zero** source-compatibility breaks. This
is the JLS committee optimising for the one thing every language decision on
Java trades against new syntax: not breaking Fortune-500 codebases that have
had a class member literally named `var` since 1999.

**Interview:** "Can you have a variable called `var`?" — Yes; `var` is a
reserved type name, not a keyword, so it remains a legal identifier for a
local variable, a field, a method, or a package/module name element. It is
illegal only in the type-name positions: declaring a class or interface named
`var`, or using `var` as a generic type argument.

> **`var` is a reserved type name (JLS §3.9), not a keyword: it is illegal only
> where a type name is grammatically expected, and remains a legal identifier
> everywhere else — which is precisely what let JEP 286 ship without breaking
> any pre-Java-10 program that already used `var` as a name.**

---

## 3. The diamond and other no-target-type failures: `var x = null`, the array shorthand, and `var` plus `<>`

**Mental model.** Every one of the four failures grouped here has the same
shape: the initialiser expression on the right of `=` is a **poly
expression** — one whose type is not fixed on its own, but depends on a
*target type* supplied by the context it sits in (a declared type, a method
parameter type, a cast). Ordinarily that target type comes from the left-hand
side of the assignment. `var` removes the left-hand side's type entirely — so
any initialiser that depends on the left-hand side to know its own type has
nowhere left to get one from. Picture handing someone a costume that only fits
once you tell them who they're playing; `var` is refusing to tell them, so
`null`, `{1,2,3}`, and the bare diamond `<>` are all left standing there with
no role to play.

**Why it exists.** This isn't an arbitrary restriction bolted onto `var` — it
follows necessarily from `var`'s one deliberate limitation (§1): inference runs
in exactly one direction, initialiser to declared type, never the reverse.
Every ordinary Java assignment (`List<Position> positions = new ArrayList<>();`)
lets the diamond borrow its type argument from the declared left-hand type.
Take the left-hand type away and the diamond, `null`, and the bare array
initialiser are the three constructs in the language whose type genuinely
cannot be recovered from the right-hand side alone.

**When to reach for it, and when not.** You don't reach for these forms with
`var` — you reach for the fix once you hit the compile error. The pattern that
resolves all three is the same: supply the type explicitly on the one place
that still accepts it. `var x = (Position) null;` compiles (the cast supplies
the target type the initialiser needed). `var arr = new int[]{1,2,3};`
compiles (the array *creation* expression, as opposed to the bare shorthand,
carries its own type). `var positions = new ArrayList<Position>();` compiles
(the diamond now has the type argument on the constructor call itself, not
borrowed from the left).

**How it works — three failures, one mechanism, worked on the page.**

`[PROVE]` **`var x = null;`.** The null type (JLS §4.1) is a real type in the
type system — it is the type of the literal `null`, and it is a subtype of
every reference type — but it has no *denotable form*: there is no spelling of
it a programmer can write (`null` the keyword names the value, not the type).
`Object x = null;` works because the left-hand side supplies `Object` as the
target type and `null` is assignment-compatible with it; `var` supplies no
target type, so the compiler is left trying to write down the null type itself
and cannot, because it has no name:

```
N1.java:1: error: cannot infer type for local variable x
public class N1 { public static void main(String[] a) { var x = null; } }
                                                            ^
  (variable initializer is 'null')
```

`[PROVE]` **The array-initialiser shorthand.** `{1, 2, 3}` on its own is not an
expression with a type — the JLS defines it only as an *array initialiser*,
legal exclusively inside an array *creation* expression (`new int[]{1,2,3}`)
or a declaration whose declared type is already an array type
(`int[] arr = {1,2,3};`). Removing the declared type via `var` removes the only
context that ever gave `{1,2,3}` meaning:

```
N2.java:1: error: cannot infer type for local variable arr
public class N2 { public static void main(String[] a) { var arr = {1,2,3}; } }
                                                            ^
  (array initializer needs an explicit target-type)
```

Spelling out the array type on the right fixes it completely, because now the
expression itself — not the declared local — carries the type:

```java
var arr = new int[]{1, 2, 3};   // compiles: the "new int[]" supplies the type
System.out.println(arr.length); // 3
```

`[PROVE]` **The diamond infers `Object`.** This is the one every engineer who
has used `var` casually has been bitten by at least once, and it is worth
proving rather than asserting, because "infers `Object`" sounds unbelievable
the first time you hear it — surely the compiler could look at what gets
`.add()`-ed later? It cannot, and does not try: type inference for `var` is a
single pass over the initialiser expression alone, and never looks forward at
how the variable is subsequently used.

```java
import java.util.ArrayList;
public class N4 {
    record Position(String marketId, String selection) {}
    public static void main(String[] a) {
        var positions = new ArrayList<>();
        positions.add(new Position("QE-100", "HOME_WIN"));
        Position p = positions.get(0);
        System.out.println(p);
    }
}
```

```
N4.java:7: error: incompatible types: Object cannot be converted to Position
        Position p = positions.get(0);
                                  ^
```

The mechanism: an empty diamond `<>` needs a target type to resolve its
argument against (JLS §15.9, §18.5.2 poly expression inference). In an
ordinary declaration, `List<Position> positions = new ArrayList<>();` gives
the diamond `Position` to copy. With `var` supplying no declared type, the
diamond has nothing to copy from — and rather than refusing to compile (which
would have made every existing `var`-plus-diamond combination a hard error and
was judged too disruptive), the JLS falls back to the diamond's own bound,
which for an unbounded type parameter is `Object`. The compiler happily infers
`ArrayList<Object>`, accepts `positions.add(new Position(...))` (any object is
an `Object`), and only fails at the *retrieval*, `positions.get(0)`, because
that call now returns `Object` and `Object` cannot narrow to `Position`
without an explicit cast.

**D-050** — `var` plus the diamond infers `Object`

![D-050 — `var` plus the diamond infers `Object`](../diagrams/D-050-var-plus-diamond-infers.svg)

**D-050** — `var` plus the diamond infers `Object`

Left half of the diagram: `var positions = new ArrayList<>();` — no declared
type to hand the diamond, so it resolves to `ArrayList<Object>`; the later
`positions.get(0).amount()` (imagine `Position` had a `amount()`-shaped
accessor) is shown as the compile error surfacing three lines downstream of
the actual mistake. Right half: `var positions = new ArrayList<Position>();` —
the type argument is written directly on the constructor call rather than
borrowed from a declared left-hand type, so the diamond has something to
resolve against regardless of what `var` erased, and `positions` is inferred
as `ArrayList<Position>` throughout.

**The gotcha.** **Pitfall:** writing `var list = new ArrayList<>();` out of
habit (it looks exactly like the pre-`var` idiom `List<Position> list = new
ArrayList<>();` minus the redundant left-hand type) and getting a *correctly
compiling*, silently wrong-typed collection — the code compiles, `add` never
complains because everything is an `Object`, and the failure doesn't surface
until the first `get()` call is used somewhere non-trivially, sometimes several
methods away from the declaration. **Fix:** never pair `var` with a bare
diamond; either write the type argument on the constructor
(`var positions = new ArrayList<Position>();`) or don't use `var` for that
declaration at all. §6 (`when var hurts`) returns to this as one of three
named failure patterns for `var` specifically because it is the most common
one in real codebases.

**Insight:** all three failures above are not "special-cased against `var`" —
`var` doesn't contain a list of forbidden initialisers. They are ordinary
consequences of poly-expression typing rules that were already in the language
for other purposes (ternary expressions, generic method invocation, lambda
targeting), and `var` simply removes the one channel (the declared left-hand
type) that those rules had always used to supply a target type. Understanding
poly expressions as "needs a target type from context" explains every one of
these failures from one idea rather than three memorised exceptions.

**Interview:** "What does `var list = new ArrayList<>()` infer, and why?" —
`ArrayList<Object>`, because the empty diamond needs a target type to resolve
its type argument against, `var` supplies none, and the diamond's fallback for
an unbounded type parameter with no target type is `Object`; the failure
doesn't show up until a later call narrows the result to something other than
`Object`.

> **A poly expression — the bare diamond, `null`, or the array-initialiser
> shorthand — has no standalone type of its own; it borrows one from the
> declaration's target type, and `var` removes exactly that target type, which
> is why all three fail to compile (or, for the diamond, silently degrade to
> `Object`) with no declared left-hand type to borrow from.**

---

## 4. `var` and non-denotable types: what `var` can hold that you cannot spell

**Mental model.** Everything in §3 was `var` losing information because it
removed a target type other expressions depended on. This concept is the
mirror image — the one thing `var` can do that an explicit type declaration
categorically cannot: hold a value whose *exact* compile-time type has no
written form in the Java language at all. If §3 is "`var` sometimes has less
to work with than an explicit type," this is "`var` sometimes has *more*
precision available than an explicit type could ever express."

**Why it exists.** Three constructs in Java produce values whose most precise
static type is not spellable as source text:

- an **anonymous class** — `new StakeRule() { ... extra members ... }`
  produces an unnamed subtype with members beyond the interface or superclass
  it's typed against, and that subtype has no name a program can write;
- an **intersection type** — the result of certain conditional expressions or
  bounded type variables (`<T extends Comparable<T> & Serializable>`) can
  produce a type that is simultaneously two or more interfaces, with no single
  spellable name for "both at once";
- a **capture variable** — the compiler's internal stand-in for an unknown
  type hiding behind a wildcard (`List<?>`'s element type, captured as some
  fresh `CAP#1` the compiler invents and never lets you write).

Before Java 10, a local declaration that received one of these had to be
"rounded down" to the nearest *denotable* supertype the interface or class
hierarchy actually offered — losing whatever extra precision the value
carried. `var` is, mechanically, the same inference rule as §1: copy the
initialiser's static type onto the local. When that static type happens to be
non-denotable, `var` is copying it anyway — it doesn't need to spell it, only
the compiler's internal symbol table does.

**When to reach for it, and when not.** Reach for `var` specifically when you
need to call an anonymous class's extra members immediately after
construction, in the same method, before the value escapes to a place that
needs a named type. This is narrow and situational, not a general argument for
`var` — the moment the value needs to be a field, a parameter, or a return
value, it must be widened to a real denotable type anyway, and the anonymous
class's extra members become permanently unreachable outside that one method.

**How it works.** Type-checking computes the anonymous class expression's
"most specific" static type as the anonymous class *itself* — an unnamed type
extending or implementing whatever was written after `new`, plus every member
declared in its body. In an explicitly-typed declaration, the declared type
(the interface name) is what the variable is treated as, so only the
interface's members are visible — the extra ones are erased from view even
though they still exist on the object at runtime and are reachable via
reflection. With `var`, there is no declared type to round down to: the
inferred type *is* the anonymous class's own (non-denotable, compiler-internal)
type, so every member declared in the body remains statically visible.

**D-049** — no additional table row here; this concept is about what `var`
*captures* once a position is already legal, not about a new legal/illegal
position, so the table from the top of this file doesn't need a new entry.

**A minimal concrete example.** `[PROVE]` A `StakeRule` anonymous
implementation with one member beyond the interface it satisfies:

```java
public class A1 {
    interface StakeRule { int cap(); }

    public static void main(String[] args) {
        var rule = new StakeRule() {
            public int cap() { return 100; }          // satisfies StakeRule
            public int bonusPercent() { return 10; }   // NOT on StakeRule
        };
        System.out.println(rule.cap() + rule.bonusPercent());  // 110
    }
}
```

Compiles and runs, printing `110` — `rule.bonusPercent()` resolves statically,
because `rule`'s inferred type is the anonymous class itself, which declares
`bonusPercent()`. Change only the declared type from `var` to `StakeRule` and
recompile the identical body:

```java
StakeRule rule = new StakeRule() {
    public int cap() { return 100; }
    public int bonusPercent() { return 10; }
};
System.out.println(rule.bonusPercent());
```

```
A2.java:8: error: cannot find symbol
        System.out.println(rule.bonusPercent());
                               ^
  symbol:   method bonusPercent()
  location: variable rule of type StakeRule
```

Same object, same runtime members, different compile-time visibility — purely
a function of which static type the variable was declared to have.

**The gotcha.** **Pitfall:** assuming this means `var` "sees more" of an
object at runtime, or that it changes what the object *is*. It does not — the
object on the heap is identical either way, with identical fields and methods
reachable via reflection or `instanceof` in both cases. The only thing that
changes is which members the *compiler* will let you call **without a cast**,
because that is purely a function of the variable's static type, and `var`
picked a more precise static type than the interface would have. **Fix:**
never reason about `var` as changing runtime capability — it only changes
which static type the compiler assigned to the variable, and that only matters
for what the compiler will let you write without a cast.

**Insight:** this is the one place in the language where `var` is not
"convenience sugar for a type you could have written anyway" — for an
anonymous class with extra members, there is genuinely no explicit-type
declaration that achieves the same compile-time visibility, because the type
`var` infers here has no name to write down even if you wanted to write it.
`[X-REF 03]` — generics contribute the intersection-type case to this same
list (a bounded type parameter like `<T extends Comparable<T> & Serializable>`
can make an expression's most specific type an intersection with no single
spellable name), and wildcard capture contributes the third; both are
mechanism-level generics material that belongs to guide 03's full treatment of
erasure and bounded wildcards — the one paragraph owed here is that `var`
copies whatever static type the compiler computed regardless of whether that
type is denotable, and both intersection types and capture variables are
denotable to the compiler's internal symbol table even though no Java source
text can spell them.

**Interview:** "Give an example of a type `var` can hold that you could never
write explicitly." — An anonymous class's own type: `var rule = new
StakeRule() { int bonusPercent() { ... } };` lets you call `bonusPercent()` on
`rule` afterward, because `var` infers the anonymous class's own unnamed type
(which includes `bonusPercent`), whereas any explicit declared type you could
write — `StakeRule rule = ...` — is necessarily a real, spellable supertype
that only exposes what it itself declares.

> **`var` sometimes infers a non-denotable type — an anonymous class's own
> type, an intersection type, or a wildcard capture variable — that no
> explicit declaration could ever spell, which is the one situation where
> `var` is strictly more precise than any explicitly-typed alternative, rather
> than merely shorter to write.**

---

## 5. `var` in lambda parameters (JEP 323, Java 11) — all-or-nothing

**Mental model.** A lambda's parameter list ordinarily has two legal shapes:
fully explicit (`(Integer x, Integer y) -> ...`) or fully implicit
(`(x, y) -> ...`, types inferred from the target functional interface). JEP
323 adds a third shape — `(var x, var y) -> ...` — that behaves like the
implicit form (types still come from the functional interface's descriptor,
not from `var` itself) but reads like the explicit form, and critically
**cannot be mixed** with the other two within the same parameter list. Picture
a light switch with three positions and no half-way notch: all-explicit,
all-implicit, or all-`var` — never two positions at once on the same lambda.

**Why it exists.** Once JEP 286 let ordinary locals drop their type via `var`,
lambda parameters became visually inconsistent — you could write `var x = ...`
for a local but had to fall back to a fully-explicit type the moment you
wanted an annotation on a lambda parameter (annotations require some
syntactic form beyond a bare identifier), because Java's implicit lambda
syntax (bare `x`) has no room for an annotation to attach to. JEP 323 exists
specifically to close that one gap: it lets a lambda parameter carry an
annotation (`(@NonNull var x) -> ...`) while still being inferred, by giving
annotations a syntactic anchor (`var`) to attach to that the fully-implicit
form doesn't offer.

**When to reach for it, and when not.** Reach for `(var x) -> ...` when a
lambda parameter needs an annotation and you still want the type inferred
rather than spelled out, or purely for lexical consistency with `var` used
elsewhere in the same block. Do not reach for it to "modernize" every lambda —
for a short, single-parameter lambda, the bare implicit form (`x -> ...`)
remains the more idiomatic and more common style; JEP 323 exists to close one
specific annotation gap, not to replace implicit lambda syntax generally.

**How it works.** Whether a lambda parameter is written explicitly, bare, or
as `var`, the parameter's *type* always comes from the same place: the
abstract method descriptor of the target functional interface the lambda is
being assigned to or passed as. `var` here is not performing §1's kind of
inference (copying a type from an initialiser expression) — there is no
initialiser to copy from; a lambda parameter is inferred from the **target
type of the whole lambda**, the same mechanism that already drives implicit
lambda parameters. `var` in this position is purely a syntactic marker that
says "yes, infer this one the way you'd infer a bare parameter, but give me a
slot to hang an annotation on." Because of that shared origin, the compiler
enforces JEP 323's headline rule mechanically and early: a lambda's parameter
list must use exactly one of the three forms for **every** parameter in the
list, checked before any type inference is attempted, because a mixed list
would leave the parser unable to decide consistently whether adjacent tokens
are a type followed by a name or a bare name.

**A minimal concrete example.** `[RESEARCH]` — re-verified by compiling all
three combinations against a `BiFunction`, `--release 21`, JEP 323 mechanics
unchanged since Java 11:

```java
import java.util.function.BiFunction;

public class BonusSplit {
    public static void main(String[] args) {
        // all-var: legal — both parameters use "var"
        BiFunction<Integer, Integer, Integer> combineMinorUnits =
            (var bonusMinorUnits, var cashMinorUnits) -> bonusMinorUnits + cashMinorUnits;
        System.out.println(combineMinorUnits.apply(33, 300)); // 3.33 as minor units: 333
    }
}
```

```java
// mixing var with an explicit type — illegal
BiFunction<Integer,Integer,Integer> f = (var x, Integer y) -> x + y;
```

```
JEP1.java:4: error: invalid lambda parameter declaration
        BiFunction<Integer,Integer,Integer> f = (var x, Integer y) -> x + y;
                                                ^
  (cannot mix 'var' and explicitly-typed parameters)
```

```java
// mixing var with an implicit (bare) parameter — also illegal
BiFunction<Integer,Integer,Integer> f = (var x, y) -> x + y;
```

```
JEP2.java:4: error: invalid lambda parameter declaration
        BiFunction<Integer,Integer,Integer> f = (var x, y) -> x + y;
                                                ^
  (cannot mix 'var' and implicitly-typed parameters)
```

Both diagnostics are distinct — `javac` tells you specifically which of the
other two forms you accidentally mixed `var` with, rather than a generic
"inconsistent parameter list" message.

**The gotcha.** **Pitfall:** believing `var` in a lambda parameter is doing
the same kind of inference as `var` on a local variable — i.e. that it's
copying a type from "the expression on the right." There is no expression on
the right for a lambda parameter to copy from; the type comes from the
target functional interface's method descriptor, exactly as it would for a
fully implicit `(x, y) -> ...`. **Fix:** treat lambda-parameter `var` as
syntax for "annotate an inferred parameter," never as a second inference
mechanism — the actual inference is identical to bare implicit parameters,
`var` only adds a place for an annotation (or, more mundanely, visual
consistency with `var` used elsewhere) to attach.

**Insight:** the "all-or-nothing" rule is not a style preference the JLS
authors imposed — it falls directly out of parser design. Java's grammar
distinguishes explicit and implicit lambda parameter lists as two different
productions decided once, for the whole parameter list, before any individual
parameter is examined; allowing `var` to appear on some parameters and not
others inside one list would require the parser to make that
explicit-vs-implicit decision per-parameter rather than once per list, which
JEP 323 deliberately declined to do to keep the grammar (and the reader's
mental model) simple.

**Interview:** "Can you mix `var` and an explicit type across a lambda's
parameters?" — No; JEP 323 requires all parameters in a lambda's parameter
list to use `var`, or none of them do — mixing `var` with an explicit type or
with a bare implicit parameter is a compile error (`cannot mix 'var' and
explicitly-typed parameters` / `cannot mix 'var' and implicitly-typed
parameters`), because the parser commits to one of the three parameter-list
forms for the whole list before looking at individual parameters.

> **`var` in a lambda parameter list (JEP 323, Java 11) is inferred from the
> target functional interface exactly like a bare implicit parameter — it adds
> only a syntactic anchor for an annotation — and the whole parameter list must
> be entirely `var`, entirely explicit, or entirely implicit; no lambda may mix
> the three.**

---

## 6. When `var` hurts: the LVTI style guide's principles, and three named failure patterns

**Mental model.** Every feature in this file so far has been "can the compiler
infer this." This concept is the one the syllabus and the OpenJDK team both
insist gets equal weight: "should a human infer this." `var` never changes
what the compiler knows — §1 proved the bytecode is identical either way — so
every argument for or against `var` in a given line of code is entirely about
the reader standing at that line six months later with no IDE tooltip and no
memory of writing it. Picture `var` as a lossy compression codec for reading
comprehension: it always shrinks the line, and whether that's a win depends
entirely on whether the information it dropped was carrying its weight.

**Why it exists — the style guide, not the language feature.** JEP 286
deliberately shipped **without** style guidance baked into the compiler or
the JLS — there is no lint rule in `javac` that tells you `var` is a bad idea
here and a good one there, because that judgment is not mechanically
decidable. The OpenJDK Amber team filled that gap out-of-band with the LVTI
("local-variable type inference") style guide, published at
`openjdk.org/projects/amber/guides/lvti-style-guide` and re-verified reachable
(HTTP 200) as of this file's writing. `[RESEARCH]` It states four principles
and seven guidelines, and they are safe to cite by their published identifiers:

**Principles**

- **P1** Reading code is more important than writing code.
- **P2** Code should be clear from local reasoning.
- **P3** Code readability shouldn't depend on IDEs.
- **P4** Explicit types are a tradeoff.

**Guidelines**

- **G1** Choose variable names that provide useful information.
- **G2** Minimize the scope of local variables.
- **G3** Consider `var` when the initializer provides sufficient information to the reader.
- **G4** Use `var` to break up chained or nested expressions with local variables.
- **G5** Don't worry too much about "programming to the interface" with local variables.
- **G6** Take care when using `var` with diamond or generic methods.
- **G7** Take care when using `var` with literals.

P4 is the load-bearing principle for everything else in this file: an explicit
type is not free documentation and it is not clutter — it is a **tradeoff**,
information that costs horizontal space and reading friction, purchased in
exchange for local clarity that doesn't depend on the initialiser, an IDE, or
tribal knowledge of the codebase (P2, P3). `var` is the right call exactly
when the initialiser already pays for that same clarity on its own (G3) — a
`new BigDecimal(...)`, a well-named factory, a cast — and the wrong call when
it doesn't.

**When to reach for it, and when not — three named failure patterns.** These
are the concrete shapes P4's tradeoff turns unfavourable, each tied to a
guideline above:

1. **An opaque factory call (violates G3).** `var reservation =
   stakeReservationRepository.load(reservationId);` tells the reader nothing —
   `load` could return `Reservation`, `Optional<Reservation>`,
   `CompletableFuture<Reservation>`, or a DTO wrapper, and only an IDE hover
   (which P3 explicitly says readability must not depend on) resolves it.
   Compare `Reservation reservation = stakeReservationRepository.load(reservationId);`
   — the explicit type is the only thing in the line that answers the
   question, so removing it removes real information.

2. **An accumulator whose width matters (ties to G7, §1.12.10 below).**
   `var totalMinorUnits = 0;` silently commits to `int` — fine until the
   accumulator is summing ledger entries across a day with ~19.8M rows and a
   value that can exceed `Integer.MAX_VALUE` in minor units. The explicit
   type `long totalMinorUnits = 0L;` is not decoration here — the width is
   the whole point of reading the line, and `var` erases the one visual cue
   that would have prompted a reviewer to ask "is `int` wide enough for a
   day's worth of stake settlements?"

3. **Pinning the concrete implementation type into the local's static type
   (violates G5, and interacts with §3's diamond trap).**
   `var restrictions = new ArrayList<Restriction>();` does not merely avoid
   writing `List<Restriction>` — it makes the compile-time type of
   `restrictions` literally `ArrayList<Restriction>`, not `List<Restriction>`.
   Every later line in the same method is now type-checked against
   `ArrayList`, not the interface: passing `restrictions` to a method that
   legitimately wants only `List<Restriction>` still works (widening
   reference conversion), but a teammate who later writes a second local
   `var otherRestrictions = restrictionsService.activeFor(clientId);` and
   expects both locals to be assignable to a common `List<Restriction>`
   variable has silently lost the "program to the interface" discipline G5 is
   about preserving — the *type itself*, not merely the declaration syntax,
   now says `ArrayList`. `[TRAP]`

**How it works — why these three specifically.** All three share the same
underlying cause: `var`'s inferred type is always the initialiser's *exact*
static type (§1), never a supertype chosen for the reader's convenience. An
explicit declared type lets a human deliberately choose a **wider**, more
abstract type than the initialiser's own type (`List<Restriction> x = new
ArrayList<>();` — programming to the interface). `var` removes that choice:
whatever the initialiser's own type is, that is what the local becomes, with
no room to widen. Pattern 3 above is that mechanism directly; patterns 1 and 2
are the same "no widening, no simplification" property showing up as lost
*readability* rather than lost *abstraction*.

**A minimal concrete example — the good and bad case side by side.**

```java
// Good — G3: the initializer is fully self-describing.
var stakeSplit = new StakeSplit(
    Money.of("0.33", Currency.getInstance("GBP")),
    Money.of("3.00", Currency.getInstance("GBP")));

// Bad — pattern 1: opaque factory call, reader learns nothing from the line.
var settlement = settlementResolver.resolve(reservationId);   // resolve() returns what?

// Bad — pattern 2: accumulator width erased.
var totalMinorUnits = 0;                    // silently int — see §1.12.10
for (LedgerEntry entry : dailyEntries) {    // ~19.8M/day possible
    totalMinorUnits += entry.amountMinorUnits();
}

// Bad — pattern 3: concrete type pinned into the static type.
var restrictions = new ArrayList<Restriction>();   // type is ArrayList<Restriction>, not List<Restriction>
```

**The gotcha.** **Pitfall:** treating "`var` is shorter" as sufficient
justification on its own, independent of what the initialiser conveys. This is
precisely the failure P4 warns against — explicit types are a tradeoff, and
"shorter" only wins the tradeoff when the initialiser was already carrying the
type information the explicit declaration would have provided. **Fix:** before
writing `var`, ask G3's question directly — does the initializer, read on its
own, already give a reader enough to know the type? If yes, `var`. If the
answer requires opening another file or hovering in an IDE, write the type.

**Insight:** the LVTI style guide is explicitly **not** "use `var` less" or
"use `var` more" — P4 makes both directions a tradeoff, which is why G3
through G7 are phrased as questions to ask at each site rather than a blanket
rule. A team convention that says "always use `var`" or "never use `var`" is,
by the style guide's own principles, skipping the judgment the guide exists to
require.

**Interview:** "When would you avoid `var`?" — When the initializer's type
isn't obvious from the line itself (an opaque factory or repository call),
when the exact numeric width matters and the explicit type is the visual cue
for it (an accumulator over values that can overflow `int`), or when omitting
the type would silently narrow the variable's static type to a concrete
implementation class rather than the interface you meant to program against —
all three are cases where P4's tradeoff (shorter code, less local information)
comes out against `var`.

> **`var` never changes what the compiler knows (§1); every argument for or
> against it is entirely about whether the initializer already gives a human
> reader — with no IDE, per P3 — the same information an explicit type would
> have, which is P4's tradeoff made concrete, and is worked out per-site with
> G3 through G7, never as a blanket team rule.**

---

## Three supporting facts

These do not carry the eight-beat treatment — no cost/performance claim beyond
a one-line note, no sibling to choose against, and no dedicated diagram — but
each is tagged in the syllabus and each earns a `**Pitfall:**` where marked.

**`var` and numeric literals infer the literal's own primitive type, with no
widening.** `[NUM]` `var x = 1;` infers `int` (an integer literal with no
suffix is `int` by JLS §3.10.1); `var y = 1L;` infers `long` (the `L` suffix);
`var f = 1.0;` infers `double` (a floating literal with no suffix is `double`
by JLS §3.10.2); `var b = (byte) 1;` infers `byte` (the cast is the
initialiser's own type, and `var` copies that exactly). Proved on this
machine: compiling with `javac -g --release 21` and reading the
`LocalVariableTable` back with `javap -v` shows the exact slot descriptors —
`I` for `x`, `J` for `y`, `D` for `f`, `B` for `b` — the JVM's own single-letter
codes for `int`, `long`, `double`, and `byte` respectively. **Pitfall:**
writing `var totalMinorUnits = 0;` as a loop accumulator expecting `long`-sized
headroom and getting silent `int` inference instead — worked in full as
failure pattern 2 in §6 above, because summing stake settlements (2.8M/day,
avg 4.20, so tens of millions of minor units per day) can overflow a 32-bit
accumulator well before a human notices.

> **A bare integer literal infers `int`; an `L`-suffixed literal infers `long`;
> a bare floating literal infers `double`; a cast literal infers the cast's
> own type — `var` never widens a literal's natural type, it only copies it.**

**Enhanced-`for` over a raw or wildcard-typed collection infers the erased
element type, which for a raw type is `Object`.** A `List` (raw, no type
argument) iterated with `for (var item : raw)` infers `item` as `Object`,
because a raw type's element accessors are erased to their raw (`Object`)
form — proved on this machine: `for (var item : raw) { item.toUpperCase(); }`
over a raw `List` fails with `cannot find symbol ... location: variable item
of type Object`, even though every element actually inserted was a `String`
(`raw.add("QE-100")`). Iterating a properly wildcard-typed collection
(`List<?>`) instead infers the wildcard's captured type — a compiler-internal
capture variable per §4, not `Object` — which is why `List<?>` and a raw
`List` behave identically at the `add` call (both reject unchecked additions
of a knowable type, differently) but differently at read time in generic
contexts. This is a narrow, mechanical fact, not a design choice to reach for:
raw types belong to pre-Java-5 interop code, and reaching for one deliberately
in new Java 21 code is itself the mistake `var` merely inherits here.

> **`var` in an enhanced-`for` infers whatever the iterated expression's
> element type erases to — `Object` for a raw type, the captured wildcard type
> for `List<?>` — never something more precise than the collection's own
> static element type already was.**

**`final var` is legal and common; `var` alone is never implicitly final.**
`final var stakeReservationId = reservation.id();` compiles cleanly — `final`
and `var` are answering two unrelated questions (mutability, and who writes
the type down) and compose freely. Without `final`, a `var`-declared local
remains fully reassignable: `var totalMinorUnits = 0; totalMinorUnits = 300;`
compiles and runs, printing `300` — proving `var` carries no implicit
`final`-like restriction the way, for comparison, a lambda-captured effectively-final
local does. The two are unrelated axes: `var` decides who writes the type,
`final` decides whether the variable can be reassigned after initialisation,
and one has no bearing on the other.

> **`var` and `final` compose orthogonally — `final var x = ...;` is legal and
> means exactly what `final <ExplicitType> x = ...;` would mean — and a plain
> `var` local remains freely reassignable unless `final` is added explicitly.**

---

## Pitfalls

### Assuming `var list = new ArrayList<>()` keeps the type you meant

**Wrong**

```java
record Position(String marketId, String selection) {}

var positions = new ArrayList<>();
positions.add(new Position("QE-100", "HOME_WIN"));
Position first = positions.get(0);   // compile error: incompatible types
```

```
error: incompatible types: Object cannot be converted to Position
```

**Right**

```java
var positions = new ArrayList<Position>();   // type argument on the constructor
positions.add(new Position("QE-100", "HOME_WIN"));
Position first = positions.get(0);            // compiles: ArrayList<Position>
```

**Why people believe it:** `var` looks like it should "obviously" pick up
`Position` from the one `.add()` call visible on the next line — but inference
runs once, over the initialiser expression only, before any later statement is
even examined; there is no forward-looking pass that watches how the variable
gets used.

### Believing `var` is resolved at runtime, like a dynamically-typed variable

**Wrong** (the belief, stated as a claim someone would make in an interview)

"`var` figures out the type when the line actually executes, so there's a
small cost the first time." — false; there is no runtime type resolution to
have a cost.

**Right**

```java
BigDecimal stake = new BigDecimal("4.20");   // T1a.java
var stake2 = new BigDecimal("4.20");         // T1b.java
```

`javac --release 21` both, `javap -c` both: the `main` method bodies are
instruction-for-instruction identical. `var` disappears entirely during
compilation; nothing about it exists at class-load time or execution time to
have a cost.

**Why people believe it:** dynamically-typed languages (JavaScript, Python)
genuinely do resolve a variable's type information at runtime, and `var`'s
name and brevity invite the same mental model — but Java's `var` performs
*compile-time* inference only, unlike either of those languages' runtime
mechanisms.

### Declaring `var` as a field, parameter, or return type "because it worked for locals"

**Wrong**

```java
public class BonusService {
    var defaultBonusCap = BigDecimal.valueOf(100);   // error: 'var' is not allowed here
    var currentCap() { return defaultBonusCap; }      // error: 'var' is not allowed here
}
```

**Right**

```java
public class BonusService {
    BigDecimal defaultBonusCap = BigDecimal.valueOf(100);
    BigDecimal currentCap() { return defaultBonusCap; }
}
```

**Why people believe it:** once a team adopts `var` for locals, it's a natural
(wrong) extrapolation to assume the same inference applies everywhere a type
would otherwise be written — but fields, parameters, and return types are part
of a class's binary contract that other compilation units link against without
recompiling the source, and JEP 286 deliberately restricted inference to local
declarations, where the "contract" is invisible outside the method body.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Is `var` a keyword? | No — a reserved type name (JLS §3.9). Legal as a variable, method, or package name. |
| Runtime cost? | None. Compile-time only; bytecode identical to the explicit-type form (proved via `javap`). |
| Legal positions | Local w/ initialiser, enhanced-`for` var, classic `for` index, try-with-resources resource, lambda parameter (all-`var`, JEP 323). |
| Illegal positions | Field, method parameter (non-lambda), return type, `catch` parameter, local w/o initialiser, generic type argument. |
| `var x = null;` | Illegal — null type not denotable. |
| `var arr = {1,2,3};` | Illegal — needs `new int[]{1,2,3}` for a type to attach to. |
| `var list = new ArrayList<>();` | Infers `ArrayList<Object>` — diamond has no target type. Write the type argument explicitly. |
| `var f = (Integer x) -> x+1;` | Illegal — lambdas/method refs are poly expressions, no standalone type. |
| `var x = cond ? 1 : 2;` | Legal — ternary is a poly expr but resolves against its own branch types, not against `var`'s absence. |
| Non-denotable types `var` *can* hold | Anonymous class's own type, intersection types, wildcard captures. |
| `var x = 1` / `1L` / `1.0` / `(byte)1` | `int` / `long` / `double` / `byte` — literal's own type, no widening. |
| Enhanced-`for` over raw `List` | `var item` infers `Object` (raw type erasure). |
| `final var x = 1;` | Legal. Plain `var` is never implicitly final. |
| Lambda param `var` rule | All-or-nothing: every parameter `var`, or none — never mixed with explicit or bare. |
| LVTI style guide | P1–P4 principles, G1–G7 guidelines; core idea (P4): explicit types are a tradeoff, not a virtue. |
| When `var` hurts | Opaque factory call, accumulator whose width matters, pinning a concrete impl type (`ArrayList` vs `List`). |

---

## Self-test

**Q1.** Why does `var x = null;` fail to compile, when `Object x = null;` compiles fine?

<details><summary>Answer</summary>

`null`'s type — the "null type" in JLS §4.1 — is a real type but has no
denotable (writable) form; it's a subtype of every reference type but cannot
be named in source. `Object x = null;` works because the *declared* type,
`Object`, supplies the target the assignment checks `null` against — the
initialiser never needs to name its own type. `var` removes that declared
target type entirely, so the compiler is left trying to write the null type
into the symbol table itself and has no spelling for it, producing "cannot
infer type for local variable x (variable initializer is 'null')".

</details>

**Q2.** What does `var positions = new ArrayList<>();` infer, and why doesn't the compiler wait to see how `positions` is used before deciding?

<details><summary>Answer</summary>

It infers `ArrayList<Object>`. The empty diamond `<>` is a poly expression
that needs a target type to resolve its type argument against; ordinarily
that target type is the declared left-hand type (`List<Position> positions =
new ArrayList<>();` gives the diamond `Position`). `var` supplies no declared
type, so the diamond has nothing to resolve against and falls back to the
type parameter's own bound — `Object` for an unbounded parameter. Inference
for a `var` declaration is a single pass over the initialiser expression
only, made once, before any subsequent statement is examined; there is no
forward-looking analysis of how the variable will later be used, so it cannot
"notice" a later `.add(new Position(...))` and retroactively narrow the type.

</details>

**Q3.** Is `var` a keyword? What can and can't you name `var`?

<details><summary>Answer</summary>

No — JLS §3.9 makes `var` a reserved *type name*, not a keyword. It remains a
legal identifier for a local variable, a field, a method, or an element of a
package/module name (`int var = 5;` and `void var() {}` both compile). It is
illegal only in type-name grammar positions: you cannot declare a class or
interface named `var`, and you cannot use `var` as a generic type argument
(`List<var>`). This design (reserved as a type name, not reserved as a
keyword) is what let JEP 286 ship without breaking any pre-Java-10 codebase
that already used `var` as an identifier.

</details>

**Q4.** Why is `(var x, Integer y) -> x + y` illegal, and what specific message does `javac` give?

<details><summary>Answer</summary>

JEP 323 requires a lambda's entire parameter list to use exactly one of three
forms — fully explicit, fully implicit (bare), or fully `var` — decided once
for the whole list, never mixed within one lambda. `javac --release 21`
rejects `(var x, Integer y) -> x + y` with `invalid lambda parameter
declaration ... (cannot mix 'var' and explicitly-typed parameters)`; mixing
`var` with a bare, untyped parameter instead produces the sibling diagnostic
`(cannot mix 'var' and implicitly-typed parameters)`. The rule exists because
the parser commits to which of the three parameter-list grammar productions
applies before examining individual parameters, so a mixed list would require
a per-parameter decision the grammar was deliberately not designed to make.

</details>

**Q5.** A colleague writes `var totalMinorUnits = 0;` as an accumulator summing a day's worth of stake settlements (2.8M/day, average value 4.20). What's the risk, and how do the LVTI guidelines name it?

<details><summary>Answer</summary>

`var totalMinorUnits = 0;` infers `int` from the bare integer literal `0`
(JLS §3.10.1 — an unsuffixed integer literal is `int`), with no widening.
Summing minor-unit amounts across millions of stake settlements in a day can
exceed `Integer.MAX_VALUE` (~2.1 billion) well before a human reviewer
notices, because the overflow is silent (wraps, doesn't throw). This is
exactly guideline G7's "take care when using `var` with literals" — the
explicit type (`long totalMinorUnits = 0L;`) is not decoration here, it is
the one visual signal in the line that would prompt a reviewer to ask whether
`int` has enough headroom; `var` erases that signal entirely.

</details>

**Q6.** Can `var` hold a type you could never write out explicitly? Give the example.

<details><summary>Answer</summary>

Yes — an anonymous class's own type. `var rule = new StakeRule() { public
int cap() { return 100; } public int bonusPercent() { return 10; } };` infers
`rule`'s type as the anonymous class itself, which is non-denotable (it has
no name any Java source can spell), so `rule.bonusPercent()` resolves
statically even though `bonusPercent()` isn't declared on `StakeRule`.
Declaring the same object as `StakeRule rule = new StakeRule() { ... };`
instead rounds the static type down to `StakeRule`, and `rule.bonusPercent()`
then fails with `cannot find symbol` — even though the underlying object on
the heap is identical either way. Intersection types and wildcard capture
variables are the other two non-denotable types `var` can carry.

</details>

**Q7.** Why does `for (var item : raw)` over a raw `List` infer `item` as `Object`, even if every element inserted was actually a `String`?

<details><summary>Answer</summary>

A raw type (a generic type used with no type argument, e.g. `List` instead of
`List<String>`) erases its element accessors to their raw form — every method
that would otherwise return the type parameter returns `Object` instead, by
design, as the pre-generics compatibility behaviour raw types exist to
preserve. `var` copies whatever static type the iterated expression's element
accessor has, and for a raw `List` that static type is `Object`, regardless
of what's actually been inserted at runtime. Proved on this machine: `for
(var item : raw) { item.toUpperCase(); }` over a raw `List` containing only
strings still fails to compile with `cannot find symbol ... location:
variable item of type Object`.

</details>

**Q8.** What's the difference between `final var x = 1;` and plain `var x = 1;`?

<details><summary>Answer</summary>

`final` and `var` answer two independent questions and compose freely: `var`
decides who writes the *type* down (the compiler infers it from the
initialiser); `final` decides whether the variable can be *reassigned* after
initialisation. `final var x = 1;` infers `int` for `x` exactly as plain `var
x = 1;` would, but additionally forbids `x = 2;` afterward. Plain `var` alone
carries no implicit finality — `var totalMinorUnits = 0; totalMinorUnits =
300;` compiles and runs, proving the variable remains freely reassignable
unless `final` is added explicitly.

</details>

**Q9.** Why does `var f = (Integer x) -> x + 1;` fail to compile, but `var portion = cashOnly ? 3.00 : 0.33;` succeeds — aren't both poly expressions?

<details><summary>Answer</summary>

Both are indeed poly expressions, but they resolve their type differently. A
lambda expression has no standalone type at all — its entire type comes from
the functional-interface target it's assigned to (a lambda body alone cannot
tell the compiler which functional interface, of potentially many
structurally-compatible ones, it's meant to implement), so with `var`
supplying no target, there is nothing for the lambda to resolve against:
"lambda expression needs an explicit target-type." A conditional (ternary)
expression, by contrast, computes its type from its own two branch
expressions' types via the JLS's conditional-expression typing rules (here,
two `double` literals unify to `double`) — it does not need an external
target type the way a lambda or method reference does, so removing the
declared left-hand type via `var` doesn't remove the information the ternary
needed.

</details>

**Q10.** A teammate declares `var restrictions = new ArrayList<Restriction>();` instead of `List<Restriction> restrictions = new ArrayList<>();`. What's actually different about the two, beyond style?

<details><summary>Answer</summary>

With `var`, the local's compile-time static type is exactly the initialiser's
type: `ArrayList<Restriction>`, not `List<Restriction>`. With the explicit
declaration, the programmer deliberately widened the static type to the
interface, `List<Restriction>`, even though the runtime object is still an
`ArrayList`. This isn't cosmetic — every later line in the `var` version is
type-checked against `ArrayList` specifically, so passing `restrictions`
somewhere that legitimately only needs `List<Restriction>` still works
(widening reference conversion), but any code that relies on the variable's
*declared* type being the interface (for "program to the interface"
discipline, or so that a later refactor to `LinkedList` doesn't ripple through
call sites expecting `ArrayList`-specific behaviour) has silently lost that
guarantee. This is guideline G5's territory — `var` removes the deliberate
choice to program to an interface at the declaration site.

</details>

## Deferred

None.

---

**Leaves covered:** 1.12.1–1.12.16 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** D-049, D-050
**Target version:** Java 21 LTS
**Lines:** 1245
