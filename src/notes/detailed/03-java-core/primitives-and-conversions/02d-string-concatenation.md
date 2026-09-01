# 03 Java Core — String concatenation and poly expressions — BASICS (§1.6, 1.6.16–1.6.18)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The conditional operator and pattern instanceof](02c-conditional-operator.md) · Next: [Conversions and contexts: the ladder and the cast](03-conversions-and-contexts.md)

Every bytecode listing and every printed value in this file was captured by compiling with `javac --release 21` and disassembling with `javap -c` on JDK 25 (`--release 21` fixes the class-file version and the language level, and none of these instructions changed between 21 and 25). Where a listing is reconstructed rather than captured, the text says so.

This part covers string concatenation, which is a conversion context of its own, and the classification of `new`, array creation, lambdas and method references into standalone and poly expressions. The precedence ladder is in [02-operators-and-expressions.md](02-operators-and-expressions.md); the conditional operator and pattern `instanceof` are in [02c-conditional-operator.md](02c-conditional-operator.md).

---

## 1. String concatenation is an operator with its own conversion context (1.6.16, 1.6.17)

**Concept.** `+` is overloaded on type, not on syntax. If either operand's static type is `String`, `+` is string concatenation and both operands undergo *string conversion*. If neither is, it is arithmetic — even when one operand is a `char` that looks like text.

**Why it exists.** Concatenation via an operator was a deliberate ergonomic choice; the alternative is `"AA-".concat(String.valueOf(801))` everywhere. The cost is the overload ambiguity in leaf 1.6.17, and a performance model that surprises people in loops.

**How it works.** JLS 21 §5.4, *String Conversion*:

> "There is a string conversion context for every expression that is an operand of the binary `+` operator when at least one of the operands is of type `String`."

String conversion of a reference is `null` for null, and `toString()` otherwise; of a primitive it is the corresponding `String.valueOf`. So `"" + null` is `"null"` — no NPE, because no method is invoked on the null. `'a' + 1` has operands `char` and `int`, neither is `String`, so binary numeric promotion applies: 97 + 1 = **98**, printed as the integer 98. Whereas `"" + 'a' + 1` groups left (level 5, left-associative): `("" + 'a')` is `"a"`, then `"a" + 1` is `"a1"`.

Captured output:

```
('a' + 1)        -> 98
("" + 'a' + 1)   -> a1
("" + (String) null) -> null
("AA-" + 801)    -> AA-801
```

The *implementation* in Java 9 and later is `invokedynamic` against `java.lang.invoke.StringConcatFactory`, which builds a `MethodHandle` chain that sizes the result buffer once and fills it — replacing the `StringBuilder.append` chain that `javac` emitted through Java 8. Per-expression this is faster and allocates less; across a loop it changes nothing, because each iteration is still an independent concatenation, so building a string by `result += entry` inside a loop over 19.8M daily ledger entries is still quadratic and still needs an explicit `StringBuilder`. The bytecode and `StringConcatFactory` mechanics are covered in [../strings/04b-internals-indified-concat.md](../strings/04b-internals-indified-concat.md).

```java
final class ConcatenationDemo {
    static final String PREFIX = "AA-";

    record AccountId(java.util.UUID value) {}

    static String statusCode(int numeric, String label) {
        return PREFIX + numeric + " " + label;
    }

    public static void main(String[] args) {
        System.out.println(statusCode(801, "ACTIVATED"));   // AA-801 ACTIVATED
        System.out.println(statusCode(900, "DECLINED"));    // AA-900 DECLINED

        System.out.println('a' + 1);                        // 98   -- arithmetic
        System.out.println("" + 'a' + 1);                   // a1   -- concatenation
        System.out.println((char) ('a' + 1));               // b    -- arithmetic then cast

        // Precedence trap: + at level 5 beats nothing useful here, so arithmetic groups left.
        System.out.println("attempt " + 1 + 2);             // attempt 12
        System.out.println("attempt " + (1 + 2));           // attempt 3

        AccountId nullAccount = null;
        System.out.println("account=" + nullAccount);       // account=null, no NPE
        System.out.println("" + null);                      // null

        // Building an audit line for one entry: fine.
        String line = PREFIX + 801 + "|" + 2.8 + "|" + true;
        System.out.println(line);                           // AA-801|2.8|true

        // Building 1000 lines: use a StringBuilder, not +=.
        StringBuilder audit = new StringBuilder(1000 * 24);
        for (int entry = 0; entry < 3; entry++) {
            audit.append(PREFIX).append(801).append(':').append(entry).append('\n');
        }
        System.out.print(audit);
    }
}
```

**Pitfall:** "`System.out.println('a' + 1)` prints `b`." It prints 98. Neither operand is a `String`, so `+` is arithmetic under binary numeric promotion, and `println` then binds to the `int` overload. To get `b` you must cast the arithmetic result back: `(char)('a' + 1)`. To get `"a1"` you must force a `String` operand first: `"" + 'a' + 1`.

**Pitfall:** expecting `"total " + a + b` to add. It concatenates both, because `+` is left-associative and the leftmost operand is already a `String` by the time `b` arrives. `"total " + (a + b)` is the fix.

**Insight:** `"" + null` being `"null"` rather than throwing is why logging is safe with nullable fields, and simultaneously why `"null"` shows up in databases. `String.valueOf(charArray)` versus `"" + charArray` also diverge: the former decodes the array as characters, the latter calls `Object.toString()` and prints a type-and-hash string.

**Interview:** "Is `+` on `char` and `int` concatenation?" — no, arithmetic; concatenation requires at least one operand of static type `String` (JLS 5.4). `'a' + 1` is 98.

> Binary `+` is string concatenation exactly when one operand's static type is `String`, in which case both operands undergo string conversion — null becoming the four characters `null` — and is arithmetic otherwise.

---

## 2. `new`, array creation, and poly expressions (1.6.18)

**Concept.** Most expressions have a type you can determine by looking at them alone. A handful cannot: a lambda, a method reference, and a diamond `new` have no meaning until you say what they are being assigned to. JLS 15.2 calls those **poly expressions**; everything else is a **standalone expression**.

**How it works.** `new Reservation(roundId, stake)` is standalone — the class name gives the type. So is an array creation expression: `new LedgerEntry[3]` is a `LedgerEntry[]`, and `new int[]{ 1, 2, 3 }` is an `int[]`. Both forms carry their element type on the page, so `var` works with them. The bare initializer `{ 1, 2, 3 }` is *not* an expression at all — it is legal only in a declaration where the array type is already written.

A lambda has no standalone type. `attempt -> attempt < 3` could be a `Predicate<Integer>`, an `IntPredicate`, or the `StakeRule` interface below. Its type comes from the target type of the context: an assignment, a cast, an argument position, a `return`. With `var` there is no target type, so the compiler has nothing to work from. Captured:

```
Poly2.java:2: error: cannot infer type for local variable rule
    static void f() { var rule = attempt -> attempt < 3; }
                          ^
  (lambda expression needs an explicit target-type)
```

Adding a cast supplies a target type and it compiles: `var rule = (StakeRule) attempt -> attempt < 3;` is accepted.

The multi-dimensional array creation `new Movement[3][]` allocates only the outer array; the inner references are null until assigned. And `new Movement[bonusCount][cashCount]` allocates the whole rectangle eagerly, which at ledger volumes is a real allocation decision, not a syntax detail.

```java
import java.util.Arrays;

interface StakeRule { boolean permits(int attempt); }

final class PolyExpressionDemo {
    record Movement(String position, long minorUnits) {}

    static Movement[] splitOf(long stakeMinor, long bonusAvailableMinor) {
        long bonusPart = Math.min(stakeMinor, bonusAvailableMinor);
        long cashPart = stakeMinor - bonusPart;
        // Array creation expression: standalone type, so var would work here too.
        return new Movement[] {
                new Movement("CLIENT_BONUS_AVAILABLE", -bonusPart),
                new Movement("CLIENT_CASH_AVAILABLE", -cashPart)
        };
    }

    static int applyRule(StakeRule rule, int attempt) {
        return rule.permits(attempt) ? attempt + 1 : attempt;
    }

    public static void main(String[] args) {
        // Canonical split: a 3.33 stake against 0.33 of bonus.
        System.out.println(Arrays.toString(splitOf(333, 33)));
        // [Movement[position=CLIENT_BONUS_AVAILABLE, minorUnits=-33],
        //  Movement[position=CLIENT_CASH_AVAILABLE, minorUnits=-300]]

        // Lambda in an argument position: the target type is the parameter type.
        System.out.println(applyRule(attempt -> attempt < 3, 2));   // 3
        System.out.println(applyRule(attempt -> attempt < 3, 3));   // 3

        // Lambda in an assignment: the declared type is the target type.
        StakeRule capped = attempt -> attempt < 3;
        System.out.println(capped.permits(0));                      // true

        // Lambda with a cast supplying the target type. Works with var.
        var castRule = (StakeRule) attempt -> attempt < 3;
        System.out.println(castRule.permits(4));                    // false

        // Method reference: also a poly expression, target-typed here by StakeRule.
        StakeRule byMethod = PolyExpressionDemo::underCap;
        System.out.println(byMethod.permits(1));                    // true

        // Jagged array: only the outer array is allocated.
        Movement[][] runs = new Movement[3][];
        System.out.println(runs[0]);                                // null
        runs[0] = splitOf(333, 33);
        System.out.println(runs[0].length);                         // 2
    }

    static boolean underCap(int attempt) { return attempt < 3; }
}
```

**Pitfall:** `var` plus a lambda or a method reference. The error message names the cause, but the instinct is to blame `var` for being weak rather than the lambda for having no type of its own. Fix: declare the functional interface type, or cast.

**Interview:** "Why can't you write `var f = () -> compute();`?" — a lambda is a poly expression with no standalone type; it needs a target type, and `var` infers from the initializer instead of providing one.

Overload resolution against poly expressions, generic method inference, `record` patterns and the exhaustiveness rules for `switch` over sealed types are all guide **04 Modern Java**. What belongs here is only the classification: `new` and array creation are standalone; lambdas and method references are not.

> A poly expression has no type of its own and takes its type from the surrounding context; `new` and array-creation expressions are standalone, while lambdas and method references are poly expressions.

---

## Pitfalls

### `System.out.println('a' + 1)` prints `b`

**Wrong**

```java
System.out.println('a' + 1);        // 98
System.out.println("AA-" + 8 + 1);  // AA-81, not AA-9
```

**Right**

```java
System.out.println((char) ('a' + 1));   // b
System.out.println("" + 'a' + 1);       // a1
System.out.println("AA-" + (8 + 1));    // AA-9
```

**Why people believe it:** `char` looks like text, so `+` looks like concatenation. JLS 5.4 makes `+` concatenation only when an operand's *static type* is `String`; otherwise binary numeric promotion turns `char` into `int` and the arithmetic overload of `println` is selected.

### `var` should work with a lambda, since the lambda body says everything

**Wrong**

```java
interface StakeRule { boolean permits(int attempt); }

final class VarLambdaWrong {
    public static void main(String[] args) {
        // error: cannot infer type for local variable rule
        //   (lambda expression needs an explicit target-type)
        // var rule = attempt -> attempt < 3;
        // var byMethod = VarLambdaWrong::underCap;   // same error
        System.out.println("neither line above compiles");
    }

    static boolean underCap(int attempt) { return attempt < 3; }
}
```

**Right**

```java
interface StakeRule { boolean permits(int attempt); }

final class VarLambdaRight {
    public static void main(String[] args) {
        StakeRule declared = attempt -> attempt < 3;         // declared type is the target type
        var cast = (StakeRule) attempt -> attempt < 3;        // cast supplies the target type
        StakeRule byMethod = VarLambdaRight::underCap;        // same fix for method references
        var standalone = new int[] { 3, 3, 3 };               // array creation IS standalone

        System.out.println(declared.permits(2));   // true
        System.out.println(cast.permits(3));       // false
        System.out.println(byMethod.permits(0));   // true
        System.out.println(standalone.length);     // 3
    }

    static boolean underCap(int attempt) { return attempt < 3; }
}
```

**Why people believe it:** the body of `attempt -> attempt < 3` visibly takes one number and returns a boolean, so it looks self-describing. It is not: that shape fits `StakeRule`, `IntPredicate`, `Predicate<Integer>` and any other single-abstract-method interface with a compatible signature, and the choice changes boxing behaviour and the method name you call. JLS 15.2 classes lambdas and method references as *poly expressions* with no standalone type; `var` requires the initializer to have one, so the two features are structurally incompatible. Array creation expressions carry their element type on the page and so remain standalone and `var`-friendly.

### `var` only chokes on lambdas; `var limits = { 1, 2, 3 };` is fine, because `int[] limits = { 1, 2, 3 };` is

**Wrong**

```java
interface StakeRule { boolean permits(int attempt); }

final class InitWrong {
    static void retryLimits() {
        var limits = { 1, 2, 3 };
    }

    static void rules() {
        var capRule = attempt -> attempt < 3;
        var capRef = InitWrong::underCap;
    }

    static boolean underCap(int attempt) { return attempt < 3; }
}
```

All three lines fail, and `javac --release 21` names the same cause three times:

```
InitWrong.java:5: error: cannot infer type for local variable limits
        var limits = { 1, 2, 3 };
            ^
  (array initializer needs an explicit target-type)
InitWrong.java:9: error: cannot infer type for local variable capRule
        var capRule = attempt -> attempt < 3;
            ^
  (lambda expression needs an explicit target-type)
InitWrong.java:10: error: cannot infer type for local variable capRef
        var capRef = InitWrong::underCap;
            ^
  (method reference needs an explicit target-type)
3 errors
```

**Right**

```java
import java.util.Arrays;

interface StakeRule { boolean permits(int attempt); }

final class InitRight {
    public static void main(String[] args) {
        int[] declared = { 1, 2, 3 };                       // type on the left, initializer on the right
        var created = new int[] { 1, 2, 3 };                // array creation IS a standalone expression
        System.out.println(Arrays.toString(declared));      // [1, 2, 3]
        System.out.println(Arrays.toString(created));       // [1, 2, 3]
        System.out.println(created.length == 3);            // true

        StakeRule capRule = attempt -> attempt < 3;         // functional interface named
        StakeRule capRef = InitRight::underCap;             // same fix for a method reference
        var castRule = (StakeRule) attempt -> attempt < 3;  // or a cast supplies the target type
        System.out.println(capRule.permits(2));             // true
        System.out.println(capRef.permits(3));              // false
        System.out.println(castRule.permits(0));            // true
    }

    static boolean underCap(int attempt) { return attempt < 3; }
}
```

Captured output: `[1, 2, 3]`, `[1, 2, 3]`, `true`, `true`, `false`, `true`. Two shapes of fix, and they are the same shape underneath: put the type back where the construct can read it. For the array, either write the type on the left (`int[] declared = { 1, 2, 3 };`) or turn the initializer into a creation expression by spelling the type out on the right (`new int[] { 1, 2, 3 }`) — only the second survives contact with `var` or an argument position. For the lambda and the method reference, declare the functional interface (`StakeRule capRule = attempt -> attempt < 3;`) or cast to it.

**Why people believe it:** the lambda failure gets filed as "lambdas are weird" rather than as an instance of a rule, so the array initializer looks unrelated — and `int[] limits = { 1, 2, 3 };` compiling every day makes `{ 1, 2, 3 }` feel like a self-describing expression that `var` should handle. It is not an expression at all. The diagnostic wording is the tell: `javac` says *needs an explicit target-type* for the initializer in exactly the words it uses for the lambda and the method reference, because all three are the same failure. This section's own point is the general rule: a poly expression has no standalone type and takes its type from the target type of its context, and `var` is the one declaration form that supplies no target type — it derives the variable's type *from* the initializer instead of handing a type *to* it. Remove the target and every construct that depended on one loses its meaning simultaneously. `new int[] { 1, 2, 3 }` is the counterexample that proves the rule rather than an exception to it: the `new int[]` prefix carries the element type on the page, which is what makes the whole thing standalone and `var`-friendly, and it is why the same three elements are legal after `new int[]` and illegal bare.

### `invokedynamic` concatenation made `+=` in a loop fast enough

**Wrong**

```java
final class AuditExportWrong {
    record LedgerEntry(String position, long minorUnits) {}

    static String export(LedgerEntry[] entries) {
        String out = "";
        for (LedgerEntry entry : entries) {
            // One indified concat per iteration; each one copies everything written so far.
            out += "AA-801|" + entry.position() + '|' + entry.minorUnits() + '\n';
        }
        return out;
    }

    public static void main(String[] args) {
        LedgerEntry[] entries = {
                new LedgerEntry("CLIENT_BONUS_RESERVED", -33),
                new LedgerEntry("CLIENT_CASH_AVAILABLE", -300)
        };
        System.out.print(export(entries));
        // correct output, quadratic cost: at 19.8M entries/day this never finishes
    }
}
```

**Right**

```java
final class AuditExportRight {
    record LedgerEntry(String position, long minorUnits) {}

    static String export(LedgerEntry[] entries) {
        // One buffer, sized once, appended to in place.
        StringBuilder out = new StringBuilder(entries.length * 48);
        for (LedgerEntry entry : entries) {
            out.append("AA-801|")
               .append(entry.position())
               .append('|')
               .append(entry.minorUnits())
               .append('\n');
        }
        return out.toString();
    }

    public static void main(String[] args) {
        LedgerEntry[] entries = {
                new LedgerEntry("CLIENT_BONUS_RESERVED", -33),
                new LedgerEntry("CLIENT_CASH_AVAILABLE", -300)
        };
        System.out.print(export(entries));
        // same output, linear cost
    }
}
```

**Why people believe it:** the Java 9 change is real and is usually described as "string concatenation got faster", which invites the conclusion that the old advice about `+` in loops is obsolete. What `StringConcatFactory` optimises is a *single* concatenation expression: the `MethodHandle` chain computes the total length of all operands up front and fills one exactly-sized array, instead of growing a `StringBuilder`. Across a loop there is no single expression to optimise — each iteration is an independent concatenation whose left operand is the entire string built so far, so iteration *n* copies *n* characters and the total is quadratic. An explicit `StringBuilder` is still the only way to make the whole loop linear, and pre-sizing it removes the internal array growth as well.

---

## Cheat sheet

| Item | Rule | Value / gotcha |
|---|---|---|
| `+` is concat when | one operand's static type is `String` (JLS 5.4) | `'a' + 1` == 98 |
| `+` otherwise | binary numeric promotion | `char` becomes `int` |
| `+` associativity | left, level 5 | leftmost `String` infects the rest |
| `"" + 'a' + 1` | left-associative | `a1` |
| `"AA-" + 8 + 1` | left-associative | `AA-81`; parenthesise to add |
| `(char)('a' + 1)` | arithmetic then cast | `b` |
| `"" + null` | `"null"` | four characters, no NPE |
| `"" + charArray` | `Object.toString()` | use `String.valueOf(charArray)` |
| Concat implementation | `invokedynamic` + `StringConcatFactory` (Java 9+) | one expression sized once |
| Concat in a loop | still quadratic | pre-sized `StringBuilder` |
| Poly expressions | lambda, method ref, diamond `new` | `var` cannot infer them |
| Standalone | `new T(a)`, `new T[n]`, `new int[]{1,2}` | `var` works |
| Poly fix | declare the interface, or cast | `var r = (StakeRule) a -> a < 3;` |
| `{ 1, 2, 3 }` bare | not an expression | legal only in a declaration |
| `new Movement[3][]` | outer array only | inner references are null |
| `new Movement[b][c]` | whole rectangle, eagerly | an allocation decision at scale |

---

## Self-test

**Q1.** What does `System.out.println("" + 'a' + 1)` print, and what does `System.out.println('a' + 1)` print? Why do they differ?

<details><summary>Answer</summary>

`"" + 'a' + 1` prints `a1`; `'a' + 1` prints `98`.

Binary `+` is string concatenation exactly when at least one operand's static type is `String` (JLS 5.4), and arithmetic otherwise. In the first expression `+` is left-associative, so `("" + 'a')` evaluates first: the empty string forces string conversion of `'a'`, giving `"a"`. Then `"a" + 1` string-converts the `int` to `"1"`, giving `"a1"`.

In the second expression neither operand is a `String`, so binary numeric promotion applies: `'a'` becomes the `int` 97, plus 1 is 98, and `println` binds to its `int` overload. To print `b` you must cast the arithmetic result: `(char)('a' + 1)`.

</details>

**Q2.** Why does `var rule = attempt -> attempt < 3;` fail to compile, and what are two ways to fix it?

<details><summary>Answer</summary>

A lambda is a *poly expression* (JLS 15.2): it has no standalone type and takes its type from the target type of its context. `var` works the other way round — it infers the variable's type from the initializer — so there is no target type to supply, and `javac` reports `cannot infer type for local variable rule` with the note `(lambda expression needs an explicit target-type)`.

Two fixes: declare the functional interface explicitly, `StakeRule rule = attempt -> attempt < 3;`; or supply a target type with a cast, `var rule = (StakeRule) attempt -> attempt < 3;`. Method references are poly expressions for the same reason and fail and are fixed identically. Array creation expressions, by contrast, are standalone — `var split = new Movement[2];` is fine.

</details>

**Q3.** `AccountId nullAccount = null; System.out.println("account=" + nullAccount);` — what prints, and why is there no `NullPointerException`? What is the analogous trap with a `char[]`?

<details><summary>Answer</summary>

It prints `account=null`, with `null` as four literal characters. String conversion (JLS 5.4) is defined for a reference operand as the four-character string `"null"` when the reference is null, and `toString()` otherwise. No method is invoked on the null reference, so there is nothing to throw. This is why log statements over nullable fields are safe, and simultaneously why the string `"null"` ends up persisted in databases when a concatenated value reaches a write path unchecked.

The `char[]` trap runs the other way. `String.valueOf(charArray)` has a dedicated overload that decodes the array as characters, but `"" + charArray` goes through the reference branch of string conversion and calls `Object.toString()`, producing something like `[C@4b67cf4d` — a type descriptor and an identity hash. The two look interchangeable and are not, so anything holding characters in an array should go through `String.valueOf` or `new String(charArray)` explicitly.

</details>

**Q4.** Java 9 replaced the compiled `StringBuilder` chain with `invokedynamic` against `StringConcatFactory`. Does that make `out += line;` inside a loop over 19.8M ledger entries acceptable? Explain the cost of each form.

<details><summary>Answer</summary>

No. The optimisation applies per concatenation *expression*, and a loop body contains one expression per iteration, not one for the whole loop.

Within a single expression such as `"AA-801|" + position + '|' + minorUnits + '\n'`, the `invokedynamic` call site links to a `MethodHandle` chain that first computes the exact total length of every operand's string form, allocates one byte array of that size, and fills it. That is strictly better than the pre-Java-9 `new StringBuilder().append(position).append(minorUnits).toString()` sequence, which had to grow and copy its internal array as it went and then copy once more at `toString`.

Across iterations nothing improves. Iteration *n* evaluates `out + line`, whose left operand is the whole string accumulated so far, so it allocates and copies roughly the accumulated length every time. Summed over *n* iterations the cost is proportional to *n* squared in characters, plus *n* dead intermediate `String` objects for the collector. At ledger volumes the loop does not merely run slowly; it saturates allocation and never completes.

The linear form is one `StringBuilder` outside the loop with `append` calls inside it, pre-sized from the entry count and an estimated line width so the internal array never grows. If the result is being written out rather than held in memory, appending straight to a `Writer` is better still, because it removes the accumulated buffer entirely.

</details>

**Q5.** Distinguish `new Movement[3][]`, `new Movement[3][2]` and the bare `{ 1, 2, 3 }`. Which of the three are expressions, and which work with `var`?

<details><summary>Answer</summary>

`new Movement[3][]` and `new Movement[3][2]` are both array creation expressions, therefore standalone expressions with a type readable from the page, therefore usable with `var`. The bare `{ 1, 2, 3 }` is not an expression at all: it is an array *initializer*, legal only in a declaration where the element type has already been written, as in `int[] caps = { 1, 2, 3 };`. Writing `var caps = { 1, 2, 3 };` fails, and so does passing `{ 1, 2, 3 }` as an argument — there `new int[] { 1, 2, 3 }` is required, since the `new int[]` prefix is what turns the initializer into an expression.

The two `new` forms differ in what they allocate. `new Movement[3][]` allocates only the outer array of three references, each null until assigned; that is the jagged shape you want when the rows have different lengths or are produced lazily, and `runs[0].length` throws `NullPointerException` until `runs[0]` is filled. `new Movement[3][2]` allocates the outer array *and* all three inner arrays eagerly, six element slots in total, every one initialised to null.

The distinction is an allocation decision rather than a syntax nicety once the dimensions come from data. `new Movement[bonusCount][cashCount]` builds the entire rectangle up front, so a large first dimension commits the whole product of memory before a single row is used; the jagged form lets you allocate rows as they are needed and lets the collector reclaim ones you drop.

</details>

---

## Open questions

- `-XX:StringTableSize` and `-XX:MaxJavaStackTraceDepth` defaults are referenced project-wide as unverified; no number in this file depends on either. `java -XX:+PrintFlagsFinal -version` on the exact target JDK build would settle them.

---

**Leaves covered:** 1.6.16, 1.6.17, 1.6.18 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 463
