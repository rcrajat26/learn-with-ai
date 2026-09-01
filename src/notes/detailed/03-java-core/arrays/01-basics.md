# 03 Java Core — Arrays are objects — BASICS (§1.22, 1.22.1–1.22.4)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Why erasure, and super type tokens](../generics/03e-internals-why-erasure-and-super-type-tokens.md) · Next: [Array covariance and mutability](01a-covariance-and-mutability.md)

This file opens the arrays chapter: what an array *is* in the type system before any syntax — a real heap object whose class the JVM synthesises on demand, with a `length` that is not a field, a creation step that is a guarantee rather than an implementation detail, and a "multi-dimensional" shape that does not actually exist as a single object. It covers the declaration and creation forms and the arrays-of-arrays model, and hands off covariance, mutability and `clone()`'s shallow-copy semantics to `01a-covariance-and-mutability.md`; the `java.util.Arrays` surface and `System.arraycopy` to `01b-array-utilities-and-arraycopy.md`; byte-level memory layout, `SOFT_MAX_ARRAY_LENGTH` and bounds-check elimination to `01c-memory-layout-and-bounds.md`; and varargs to `01d-varargs-and-choosing-arrays.md`.

## 1. Arrays are objects with a synthesised class (1.22.1)

Every array in Java — `int[]`, `LedgerEntry[]`, `long[][]` — is a real object on the heap. It has an object header, a real `Class` you can query at runtime, and it goes through the same allocation path as any ordinary `new PaymentIntent(reservationId)` call. But nobody wrote `LedgerEntry[].class`'s source. There is no `.java` file for it, no `.class` file on disk that `javac` emitted, and no line in any source tree that declares it. The JVM manufactures that class the first time the type is needed — the moment a method signature, a `checkcast`, or an `anewarray` instruction mentions `[LLedgerEntry;` — and every array of that component type and dimension shares the single synthesised `Class` object thereafter.

### Why it exists

Java needed arrays to be first-class values usable anywhere an `Object` is expected — passed to `Object` parameters, stored in `Object[]`, checked with `instanceof`, compared for identity — without inventing an entirely separate kind of runtime value alongside objects. The cheapest way to get that is to make an array *be* an object: give it a `Class`, a place in the single-rooted class hierarchy (so `Object` methods and reflection work on it uniformly), and a small set of interfaces (`Cloneable`, `Serializable`) so generic frameworks that already know how to handle those interfaces handle arrays too. The alternative — a distinct "array" runtime kind with its own dispatch and reflection rules — would have doubled every piece of infrastructure that needs to reason about "is this a value I can store in an `Object` slot."

### The mechanism

`length` is the sharpest evidence that "array" is not merely "object with syntactic sugar." Every Java tutorial says arrays "have a `length` field." Compile the read and look at the bytecode.

```java
public class LedgerEntry {
    public static void main(String[] args) {
        LedgerEntry[] batch = new LedgerEntry[3];
        int n = batch.length;
        System.out.println(n);
    }
}
```

`javac -Xlint:all LedgerEntry.java && javap -c LedgerEntry.class` on JDK 21.0.7:

```
public static void main(java.lang.String[]);
    Code:
       0: iconst_3
       1: anewarray     #7                  // class LedgerEntry
       4: astore_1
       5: aload_1
       6: arraylength
       7: istore_2
       8: getstatic     #9                  // Field java/lang/System.out:Ljava/io/PrintStream;
      11: iload_2
      12: invokevirtual #15                 // Method java/io/PrintStream.println:(I)V
      15: return
```

Offset 6 is `arraylength` — a dedicated bytecode instruction with no operand, defined by JVMS §6.5, that pops an array reference and pushes its length. There is no `getfield` anywhere in this method, and there could not be: `LedgerEntry[].class.getDeclaredFields()` returns an empty array (verified below). JLS §10.7 (Array Members) calls `length` "the `public` `final` field" that "contains the number of components," but the field is a specification fiction for how source code reads `array.length` — the actual bytecode never resolves a field reference for it, and reflection cannot find it because there is nothing to find. The reflective route that does exist is `java.lang.reflect.Array.getLength(Object)`, which internally dispatches to the same primitive the JVM uses, not to `Field.get`.

**Insight:** the gap between "the spec's field-shaped description" and "the bytecode's dedicated instruction" is exactly why frameworks that walk `getDeclaredFields()` to serialize or reflect over a type never see `length` — and why a naive reflective copy of "every field" of an array class silently does nothing, because there are zero declared fields to iterate.

Running `ClassMeta.java` (constructs `LedgerEntry[3]`, then queries its `Class`) on JDK 21.0.7:

```
getName()=[LLedgerEntry;
getSimpleName()=LedgerEntry[]
getComponentType()=class LedgerEntry
getSuperclass()=class java.lang.Object
getInterfaces()=[interface java.lang.Cloneable, interface java.io.Serializable]
declaredFields=[]
long[].class.getName()=[J
long[][].class.getName()=[[J
java.lang.reflect.Array.getLength(batch)=3
clone type=[LLedgerEntry;
```

JLS §10.8 (`Class` Objects for Arrays) states it plainly: "Although an array type is not a class, the `Class` object of every array acts as if" the direct superclass of every array type is `Object`, and as if every array type implements the interfaces `Cloneable` and `java.io.Serializable`. That is not a convenience description — `getSuperclass()` and `getInterfaces()` above return exactly that, on a class nobody compiled.

`getName()` is the practical payoff: it returns the JVM's internal descriptor, not a readable type name, and that descriptor is what shows up in a `ClassCastException` message or a heap dump. The descriptor letters, verified by compiling `Descriptors.java` and printing `.class.getName()` for each on JDK 21.0.7:

| Descriptor | Component kind |
|---|---|
| `[Z` | `boolean` |
| `[B` | `byte` |
| `[C` | `char` |
| `[S` | `short` |
| `[I` | `int` |
| `[J` | `long` |
| `[F` | `float` |
| `[D` | `double` |
| `[LMoney;` | reference type (`L`, fully-qualified name, `;`) |
| `[[I` | nested — `int[][]`, an array of `int[]` |

Real captured output: `boolean[] -> [Z`, `byte[] -> [B`, `char[] -> [C`, `short[] -> [S`, `int[] -> [I`, `long[] -> [J`, `float[] -> [F`, `double[] -> [D`, `int[][] -> [[I`, and a nested test record `Descriptors$Money[]` printed `[LDescriptors$Money;` — the reference-type descriptor form, an `L`, the class's binary name, then a `;`, which for a top-level `Money` in the domain reads `[LMoney;`.

The `Cloneable`/`Serializable` implementation is real, not just interface membership: an array's `clone()` method is `public` (unlike `Object.clone()`, which is `protected`) and it is covariantly typed — `LedgerEntry[].clone()` returns `LedgerEntry[]`, not `Object`, confirmed above (`clone type=[LLedgerEntry;`). The shallow-copy semantics that make that clone dangerous for a `LedgerEntry[][]` are `01a-covariance-and-mutability.md`'s subject — here the fact worth keeping is only the type: no cast needed on the result.

Where the header and the element storage physically sit in memory is `01c-memory-layout-and-bounds.md` (owns diagram D-058) and `../objects-equality-and-lifecycle/05-internals-object-layout.md` — this file stops at "it is an object with a header," not the byte offsets.

One more fact this section only names: an *array component* — `batch[2]` — is one of the seven kinds of variable in JLS §4.12.3, distinct from a field, a local, and a method parameter. `../primitives-and-conversions/01-basics.md` owns that enumeration and what makes each kind's default-value and definite-assignment rules different; §3 below leans on the array-component half of that distinction without re-deriving it.

No diagram: the manifest assigns this section none; the `javap` and reflection output above is the picture.

```java
import java.util.Arrays;

public final class LedgerAudit {
    public static Class<?> batchType(LedgerEntry[] batch) {
        return batch.getClass();
    }

    public static void main(String[] args) {
        LedgerEntry[] batch = new LedgerEntry[]{
                new CashEntry(java.util.UUID.randomUUID(), new Money(java.math.BigDecimal.valueOf(4.20), java.util.Currency.getInstance("GBP"))),
                new BonusEntry(java.util.UUID.randomUUID(), new Money(java.math.BigDecimal.valueOf(0.33), java.util.Currency.getInstance("GBP")))
        };
        Class<?> type = batchType(batch);
        System.out.println(type.getName() + " superclass=" + type.getSuperclass()
                + " interfaces=" + Arrays.toString(type.getInterfaces())
                + " fields=" + Arrays.toString(type.getDeclaredFields()));
    }

    sealed interface LedgerEntry permits CashEntry, BonusEntry {
        java.util.UUID id();
        Money amount();
    }
    record CashEntry(java.util.UUID id, Money amount) implements LedgerEntry {}
    record BonusEntry(java.util.UUID id, Money amount) implements LedgerEntry {}
    record Money(java.math.BigDecimal amount, java.util.Currency currency) {}
}
```

**Gotcha:** `instanceof LedgerEntry[]` and `getClass() == LedgerEntry[].class` both work exactly like ordinary type checks, which tempts you into forgetting there is no source file backing that class — until you need to look one up by name with `Class.forName("[LLedgerEntry;")` (it works, using the descriptor, not `"LedgerEntry[]"`) or until a stack trace prints the descriptor form and you have to mentally decode `[[Lcom.quizstakes.LedgerEntry;` as "array of array of `LedgerEntry`."

> An array is a genuine object — heap-allocated, `Object`-rooted, `Cloneable` and `Serializable` — whose `Class` the JVM synthesises on first use and whose `length` is read by a dedicated instruction, never a field.

## 2. Creation and the zero-fill guarantee (1.22.3)

Creating an array is not "allocate memory of the right size." It is a guarantee: every component, all the way to the last one, ends up holding a specific, spec-mandated default value before your code ever sees it. That guarantee is why you can loop `for (int i = 0; i < a.length; i++) sum += a[i]` on a freshly created array without ever writing to some of its slots and never read garbage — and it is also why allocating a large array always costs the zeroing, not just the allocation.

### Why it exists

C and C++ arrays (and, in Java's own design space, uninitialized stack memory generally) can hand you whatever bytes happened to be there before — a source of an entire class of security and correctness bugs where a program reads memory it never wrote. Java's designers closed that off for every kind of variable with a default, and arrays got the same treatment as fields: since a component cannot have "definite assignment" tracked the way a local variable can (the number of components is a runtime value, not something `javac` can enumerate at compile time), the only sound choice was to mandate that creation itself zero every slot.

### The mechanism

Three ways to get an array into existence, and only two produce a *reference to a new heap object* in different surface syntax versus the third being pure declaration sugar for one of the first two:

| Form | Example | Where it may appear |
|---|---|---|
| Explicit size, `new` | `new LedgerEntry[10]` | Anywhere an expression is legal |
| Explicit initialiser, `new` | `new LedgerEntry[]{a, b}` | Anywhere an expression is legal — an argument, a return, a field initialiser |
| Declaration shorthand | `LedgerEntry[] batch = {a, b};` | **Only** the initialiser of a local variable or field declaration — not as a method argument, not after `var`, not as a return expression |

The shorthand is pure sugar for the explicit-initialiser form and the compiler rejects it everywhere else; `var batch = {a, b};` does not compile because `var` needs an inferable type from an expression, and `{a, b}` is not an expression, only a declaration-initialiser token sequence.

Zero-fill is the half worth internalising as a guarantee, not a detail. JLS §10.6 (Array Initializers) states that when an array is created without an explicit initialiser, "a one-dimensional array is created of the specified length, and each component of the array is initialized to its default value (§4.12.5. Initial Values of Variables)" — the same default-value table that governs uninitialized fields: `0` for the integral types, `0.0f`/`0.0d` for the floating types, the NUL character for `char`, `false` for `boolean`, `null` for a reference type. Running `CreationZeroFill.java` on JDK 21.0.7 confirms every case:

```
new long[5] = [0, 0, 0, 0, 0]
new double[3] = [0.0, 0.0, 0.0]
new boolean[3] = [false, false, false]
new char[3] codepoints = 0,0,0
new Object[3] = [null, null, null]
new LedgerEntry[0] == null? false length=0
array component default long = 0
NegativeArraySizeException message = -1
```

That zeroing is real work proportional to the array's size — the JVM has to touch every one of those slots (whether that is a dedicated zero-fill pass or the allocator handing back pre-zeroed pages depends on the collector and is not something measured here) — so allocating `new long[10_000]` pays for the zeroing on top of the allocation itself, every single time, even if the very next line overwrites every element. A hot path that allocates a fresh buffer per call — QuizStakes's `PaymentRun` sizing a fresh withdrawal buffer for each of the 7k/day batched bank withdrawals — pays that cost per run; reusing one buffer across runs (and tracking a logical "used length" separately from the array's physical length) avoids re-paying it. The exact per-element cost is a JIT/GC-dependent number this file does not measure; `../cost-model/02-master-cost-table.md` (a later batch) owns the settled figure.

**Insight:** the contrast that makes zero-fill a guarantee and not folklore is the *local variable* rule sitting right next to it. A local `long x;` has no default at all — `javac` tracks definite assignment and refuses to compile a read before a write. An array component, however many components there are, always has one, decided entirely at creation time and unrelated to what the surrounding code has or hasn't written yet:

```java
public class LocalNoDefault {
    public static void main(String[] args) {
        long x;
        System.out.println(x);
    }
}
```

`javac -Xlint:all LocalNoDefault.java` on JDK 21.0.7:

```
LocalNoDefault.java:4: error: variable x might not have been initialized
        System.out.println(x);
                           ^
1 error
```

against `new long[10][0]`, which reads `0` with no compiler objection whatsoever, confirmed above (`array component default long = 0`). `../classes-and-initialization/01-basics.md` owns definite assignment in full; `../primitives-and-conversions/01-basics.md` owns the default-value table this section borrows.

A zero-length array — `new LedgerEntry[0]` — is legal, is **not** `null` (confirmed above: `== null? false`), and is the idiomatic "nothing here" return value precisely because it needs no null-check at the call site; it is the return type `Collection.toArray(T[])` expects when the collection is empty, and it is the shape a varargs call takes when zero arguments are passed (`01d-varargs-and-choosing-arrays.md`). A **negative** size, by contrast, compiles cleanly — `new long[n]` with `n` an `int` variable is legal at compile time regardless of sign — and throws `NegativeArraySizeException` at runtime, with the message being the offending size itself, confirmed above: message `-1` for a size of `-1`.

No diagram: the manifest assigns this section none; the printed defaults above are the evidence.

```java
public final class WithdrawalBuffer {
    public static long[] zeroFilled(int size) {
        return new long[size];
    }

    public static long[] explicit(long first, long second) {
        return new long[]{first, second};
    }

    public static long[] shorthand() {
        long[] batch = {100L, 250L, 4200L};
        return batch;
    }

    public static long[] empty() {
        return new long[0];
    }
}
```

**Pitfall:** treating `new long[n]` as "cheap because it's just a size" and calling it in a tight loop — the zeroing is proportional to `n` every single call, so a `PaymentRun` that allocates a fresh withdrawal buffer per settlement window instead of reusing one buffer across the day's 4 banking-partner windows pays the zero-fill cost repeatedly for no correctness benefit.

> Array creation is not allocation alone: the JLS mandates that every component be initialised to its type's default value (§10.6, cross-referencing §4.12.5) before the array reference is handed back, and that zeroing is real, size-proportional work.

## 3. Multi-dimensional arrays are arrays of arrays (1.22.4)

Java has no rectangular multi-dimensional array type. There is no single object that is "a 3×4 grid." `long[][]` is, in full, an array whose component type is `long[]` — a reference type like any other reference type — so a "2-D array" is a tree exactly one level deep: one outer array of references, each pointing at its own independently-sized `long[]`. That single fact is the entire explanation for jaggedness, for why `new long[3][]` is legal and `new long[][4]` is not, for the memory layout, and for why iteration order affects cache behaviour.

### Why it exists

A genuinely rectangular multi-dimensional array — one contiguous block indexed by `row * width + col` — is exactly what C gives you, and it is faster to index and denser in memory when the data really is rectangular. Java's designers instead built multi-dimensional arrays entirely out of the one-dimensional array primitive plus reference types, which meant zero new runtime machinery: the same `Class` synthesis, the same `length`, the same zero-fill guarantee, the same `Cloneable`/`Serializable` story from §1 all apply to every level of nesting for free, at the cost of true rectangularity and of the extra indirection per dimension.

### The mechanism

Creating `new long[3][4]` allocates the outer `long[3][]`-shaped array of references *and* three `long[4]` row arrays in one expression, but they remain four separate objects, and nothing enforces that they stay the same length after creation:

```java
long[][] grid = new long[3][4];
System.out.println("grid.length=" + grid.length + " grid[0].length=" + grid[0].length);
grid[1] = new long[7];
System.out.println("after reassign grid[1].length=" + grid[1].length + " grid[0].length=" + grid[0].length);
```

Run on JDK 21.0.7:

```
grid.length=3 grid[0].length=4
after reassign grid[1].length=7 grid[0].length=4
grid.getClass().getComponentType()=class [J
grid[0].getClass()=class [J
new long[3][] rows[0]=null rows.length=3
```

`grid[1] = new long[7]` compiles and runs without complaint — row 1 is now length 7 while row 0 is still length 4, and the "rectangle" was only ever a convention the initial creation happened to establish, never a constraint the language enforces. `grid.getClass().getComponentType()` confirms the outer array's component type is `long[]` (descriptor `[J`), not `long`; `grid[0].getClass()` confirms each row really is its own `long[]` object.

`new long[3][]` is legal and produces three `null` rows (confirmed above: `rows[0]=null`, `rows.length=3`); `new long[][4]` is not legal at all — it does not even compile:

```java
long[][] bad = new long[][4];
```

`javac -Xlint:all IllegalDim.java` on JDK 21.0.7:

```
IllegalDim.java:3: error: ']' expected
        long[][] bad = new long[][4];
                                  ^
1 error
```

The mechanism behind that asymmetry is the JVM instruction each shape compiles to. Two methods, one per shape:

```java
static long[][] full() {
    return new long[3][4];
}

static long[][] partial() {
    return new long[3][];
}
```

`javap -c` on JDK 21.0.7:

```
static long[][] full();
    Code:
       0: iconst_3
       1: iconst_4
       2: multianewarray #7,  2             // class "[[J"
       6: areturn

static long[][] partial();
    Code:
       0: iconst_3
       1: anewarray     #9                  // class "[J"
       4: areturn
```

`full()` compiles to `multianewarray`, a JVMS §6.5 instruction that takes an explicit *dimension count* (`2` here) and pops that many size operands off the stack, left to right — it needs every dimension supplied because it allocates every level in one instruction. `partial()` compiles to plain `anewarray`, the same one-dimensional-array instruction from §1, creating a single array of `long[]` references, every slot `null` per the zero-fill guarantee in §2 (a reference type's default is `null`). The two forms genuinely emit *different instructions* — this is not a surface-syntax coincidence, it is why the rule is "supply dimensions from the left, and a dimension can only be omitted after every dimension to its left has been supplied": `multianewarray` has no way to express "skip this dimension, fill it in later" for anything other than the trailing ones, because it materialises every array it is given eagerly, left-to-right, in one bytecode step.

No diagram: the manifest assigns this section none; the `javap` excerpt above is the picture.

Jagged arrays are the ordinary case of a genuinely irregular real quantity, not a special trick. QuizStakes's banking partner runs four payout windows a day, and each window settles a different number of withdrawals:

```java
public final class WithdrawalWindows {
    public static long total(long[][] withdrawalWindows) {
        long sum = 0;
        for (long[] window : withdrawalWindows) {
            for (long amount : window) {
                sum += amount;
            }
        }
        return sum;
    }

    public static void main(String[] args) {
        long[][] withdrawalWindows = new long[4][];
        withdrawalWindows[0] = new long[]{18_000, 22_000, 9_500};
        withdrawalWindows[1] = new long[]{31_000};
        withdrawalWindows[2] = new long[]{12_000, 8_000, 15_500, 4_200};
        withdrawalWindows[3] = new long[]{27_000, 19_000};
        System.out.println("total withdrawals across windows=" + total(withdrawalWindows));
    }
}
```

Run on JDK 21.0.7: `total withdrawals across windows=166200`. Four rows, four different lengths, no wasted padding — this is exactly why `new long[4][]` followed by per-row assignment is the idiomatic shape when the row lengths are not known (or not equal) up front, versus `new long[4][someFixedWidth]` when they are.

The cost this buys: `long[3][4]` is **four objects**, not one — one outer array plus three row arrays — so it costs four object headers and one extra pointer indirection per element access (`grid[i][j]` dereferences `grid[i]` first, then indexes into that result) compared with a flat `long[12]` plus manual index arithmetic `i * 4 + j`, which is one object and one indirection. The exact header-byte arithmetic is `01c-memory-layout-and-bounds.md`'s subject; the practical escape hatch — flattening to one array with manual row-major indexing — is worth it specifically when the shape really is rectangular, the array is large or hot enough that the extra indirections and the extra header bytes show up in profiling, and the manual index arithmetic's readability cost is worth paying; for small or genuinely jagged data (like the withdrawal windows above), the arrays-of-arrays form is the right default.

**Pitfall:** assuming `grid.length` tells you the number of *columns* — it tells you the number of *rows* (the outer array's length); the column count is `grid[0].length`, which is only meaningful, and only equal across rows, if nothing has reassigned a row to a different length.

```java
public final class GridShapeGotcha {
    public static void main(String[] args) {
        long[][] grid = new long[3][4];
        System.out.println("rows=" + grid.length + " columns=" + grid[0].length);
    }
}
```

**Pitfall:** assuming a `long[3][4]` is one contiguous block of 12 `long`s — it is four separate heap objects, and there is no guarantee the three row arrays are even adjacent in memory, which matters for cache-friendly iteration order (row-major traversal stays within one row array at a time; the byte-level reasoning for why that matters is `01c-memory-layout-and-bounds.md`'s).

> A multi-dimensional array is not a rectangular primitive; it is a tree of one-dimensional arrays built entirely from the single-dimension `anewarray`/`multianewarray` instructions, which is why rows can differ in length, why `new long[3][]` is legal while `new long[][4]` is not, and why every level pays its own object header.

## Supporting facts

### Declaration forms: `T[] name` versus `T name[]` (1.22.2)

`LedgerEntry[] batch` and `LedgerEntry batch[]` declare exactly the same type — the trailing-bracket form is inherited C syntax and is discouraged in modern Java style precisely because of the gotcha below. The same trailing form exists for method returns too: `LedgerEntry find()[]` is legal-but-awful Java, verified by compiling it directly:

```java
static LedgerEntry[] findLeading() { return null; }
static LedgerEntry findTrailing()[] { return null; }
```

Both compile and both run identically (`javac`/`java` output on JDK 21.0.7: `findLeading()=null`, `findTrailing()=null`) — the trailing form is exactly as legal as the leading one, just unread by any style guide written after 1996.

**Gotcha:** in a multi-variable declaration, the two forms bind differently. `LedgerEntry[] a, b;` declares **two arrays** — the bracket belongs to the type and applies to every variable in the list. `LedgerEntry a[], b;` declares **one array and one plain reference** — the bracket belongs to the individual variable name, not the type, so it only modifies `a`. Compiling and running both against `getClass()`:

```java
static LedgerEntry[] a1, b1;      // both arrays
static LedgerEntry a2[], b2;      // a2 is an array, b2 is a plain reference
```

Output on JDK 21.0.7:

```
a1 class=[LLedgerEntry;
b1 class=[LLedgerEntry;
a2 class=[LLedgerEntry;
b2 class=LedgerEntry
```

`b1` really is an array (`[LLedgerEntry;`) while `b2`, declared in the trailing-bracket list, is a bare `LedgerEntry` — the single strongest reason the trailing form is discouraged beyond taste. Multi-dimensional declaration forms (`long[][] grid`, `long grid[][]`, and the mixed `long[] grid[]`) follow the same binding rule and belong to §3 above.

> `T[] name` and `T name[]` are the same type for a single declaration, but in a comma-separated multi-variable declaration only the leading form applies the bracket to every name in the list.

## Pitfalls

### "Arrays have a `length` field, so I can find it with reflection"

**Wrong**

```java
LedgerEntry[] batch = new LedgerEntry[3];
java.lang.reflect.Field f = batch.getClass().getDeclaredField("length");
// java.lang.NoSuchFieldException: length
```

**Right**

```java
LedgerEntry[] batch = new LedgerEntry[3];
int n = batch.length;                                  // arraylength bytecode, no reflection needed
int reflective = java.lang.reflect.Array.getLength(batch); // the actual reflective route
```

**Why people believe it:** the JLS itself describes `length` in field-shaped language ("the `public` `final` field `length`," §10.7), and the syntax `array.length` looks identical to `object.fieldName`, so it reads as a field everywhere except the one place — `getDeclaredFields()` — that would tell you otherwise; `getDeclaredFields()` on any array class returns an empty array, confirmed on JDK 21.0.7 above.

### "`new long[][4]` makes a 2-D array with the outer size decided later"

**Wrong**

```java
long[][] bad = new long[][4];
// IllegalDim.java:3: error: ']' expected
```

**Right**

```java
long[][] bad = new long[3][4];   // supply every dimension from the left
long[][] rows = new long[3][];   // or omit only trailing dimensions
```

**Why people believe it:** `new long[3][]` (omitting the *trailing* dimension) is legal and common, so it looks symmetrical to assume the *leading* dimension can be omitted too — but `multianewarray` allocates every dimension it is given in one instruction, left to right, and has no way to defer an earlier dimension while supplying a later one; the asymmetry is verified above via `javap`, where the legal form compiles to `multianewarray #7, 2` and the illegal form never reaches bytecode at all.

### "A `long[3][4]` is one contiguous block, just like a flat `long[12]`"

**Wrong**

```java
long[][] grid = new long[3][4];
grid[1] = new long[7];   // compiles and runs fine — rows are independent objects
System.out.println(grid[1].length + " " + grid[0].length);  // 7 4
```

**Right**

```java
long[] flat = new long[12];              // one object, contiguous, if rectangularity is guaranteed
long value = flat[row * 4 + col];        // manual row-major indexing
```

**Why people believe it:** every other language's "2-D array" syntax that reads like `long[3][4]` genuinely is one rectangular block, and Java's bracket syntax looks the same — but Java built its multi-dimensional arrays entirely out of one-dimensional arrays of references, so `grid[1] = new long[7]` reassigning row 1 to a different length is not a bug, it is the language working exactly as specified; the memory-layout consequence (four separate headers, no forced adjacency) is `01c-memory-layout-and-bounds.md`'s subject.

### "Every variable in Java gets a default value if I don't initialise it"

**Wrong**

```java
public static void main(String[] args) {
    long x;
    System.out.println(x);
}
// LocalNoDefault.java:4: error: variable x might not have been initialized
```

**Right**

```java
long[] grid = new long[10];
System.out.println(grid[0]);   // 0 — array components always have a default
```

**Why people believe it:** fields and array components really do get JLS §4.12.5 defaults automatically, so it is easy to generalise "uninitialised means zero/null in Java" to every variable — but locals are the one variable kind the compiler tracks with definite-assignment analysis instead of giving a default, precisely because a local's "slot" is reused stack space with no zero-fill guarantee at all; `javac` refuses to compile the read specifically to close that gap, confirmed above.

## Cheat sheet

| Fact | Detail |
|---|---|
| Array superclass | `Object` (JLS §10.8) |
| Array interfaces | `Cloneable`, `java.io.Serializable` (JLS §10.8) |
| `length` access | `arraylength` bytecode instruction; no declared field; reflective route is `Array.getLength(Object)` |
| Declared fields on an array class | Always empty (`getDeclaredFields().length == 0`) |
| Descriptor letters | `Z` boolean, `B` byte, `C` char, `S` short, `I` int, `J` long, `F` float, `D` double, `L` name `;` for a reference type, leading `[` per dimension |
| `T[] name` vs `T name[]` | Same type, single declaration; **differ** in a multi-variable list — leading form applies to every name, trailing form only to the one it's attached to |
| Method return trailing brackets | `T find()[]` compiles, legal, discouraged |
| `new T[n]` | Zero-fills every component (JLS §10.6 → §4.12.5); cost proportional to `n` |
| `new T[]{a, b}` | Explicit initialiser; legal anywhere an expression is legal |
| `T[] a2 = {a, b}` | Declaration-shorthand initialiser only; illegal as an argument, after `var`, or as a return expression |
| `new T[0]` | Legal, not `null`, idiomatic "empty" |
| `new T[-1]` | Compiles; throws `NegativeArraySizeException` at runtime |
| Local variable default | None — definite assignment enforced at compile time |
| `new long[3][4]` | `multianewarray`, 2 dimensions, one instruction, 4 objects total |
| `new long[3][]` | `anewarray`, rows default to `null` |
| `new long[][4]` | Does not compile — leading dimension cannot be deferred |
| Jagged rows | Independent objects; reassigning one row's length never affects another's |
| `grid.length` | Row count, **not** column count |

## Self-test

**Q1.** Why does `LedgerEntry[].class.getDeclaredFields()` return an empty array if arrays "have a `length` field"?

<details><summary>Answer</summary>

Because `length` is not actually a declared field on the synthesised array class — it is a specification fiction for how source code is allowed to read `array.length`. The compiler emits a dedicated `arraylength` bytecode instruction for that read, which pops the array reference and pushes its length directly; there is no field for reflection to enumerate. The reflective equivalent is `java.lang.reflect.Array.getLength(Object)`, which reaches the same value through a different route entirely, not through `Field.get`.

</details>

**Q2.** What are `LedgerEntry[].class.getSuperclass()` and `getInterfaces()` on JDK 21, and where does that come from?

<details><summary>Answer</summary>

`getSuperclass()` returns `java.lang.Object`, and `getInterfaces()` returns `Cloneable` and `java.io.Serializable`. This is mandated by JLS §10.8, "Class Objects for Arrays": every array type's `Class` object behaves as if its direct superclass were `Object` and as if it implemented exactly those two interfaces, even though an array type is not, strictly speaking, a class with a source declaration anywhere.

</details>

**Q3.** What does `LedgerEntry[].class.getName()` print, and why is that worth knowing for reading a stack trace?

<details><summary>Answer</summary>

It prints `[LLedgerEntry;` — the JVM's internal descriptor, not a human-readable name. The leading `[` means one array dimension, `L` starts a reference-type descriptor, and `;` ends it. Knowing this matters because `ClassCastException` messages and heap dump tooling report exactly this descriptor form, so `[[Lcom.quizstakes.LedgerEntry;` in an exception message decodes as "an array of arrays of `LedgerEntry`," which is not obvious if you've never seen the descriptor grammar.

</details>

**Q4.** `LedgerEntry[] a, b;` versus `LedgerEntry a[], b;` — what's the type of `b` in each?

<details><summary>Answer</summary>

In `LedgerEntry[] a, b;`, the bracket is attached to the type, so it applies to every name in the comma-separated list — both `a` and `b` are `LedgerEntry[]`. In `LedgerEntry a[], b;`, the bracket is attached to the individual variable name `a`, not the type, so only `a` is an array; `b` is a plain `LedgerEntry` reference. I've verified this by compiling both forms and printing `getClass()` on JDK 21 — `b` in the second form prints `LedgerEntry`, not `[LLedgerEntry;`.

</details>

**Q5.** Is `new long[n]` with zero-fill actually free, or does it cost something proportional to `n`?

<details><summary>Answer</summary>

It costs something proportional to `n`. The JLS mandates that every component be initialised to its default value at creation (§10.6, cross-referencing §4.12.5), and that is real work the JVM has to do for every element — whether that shows up as an explicit zeroing loop or as handing back pages the allocator has already zeroed depends on the collector, but either way you pay for it on every allocation, even if the next line of code overwrites every element. That's why a hot path — like sizing a fresh withdrawal buffer per settlement window — is better off reusing one buffer than allocating a fresh one each time.

</details>

**Q6.** Why does `new long[][4]` fail to compile while `new long[3][]` compiles fine?

<details><summary>Answer</summary>

Because the two forms compile to different bytecode instructions with different capabilities. `new long[3][]` is a single-dimension `anewarray` creating one array of `long[]` references, each defaulting to `null` — it never needed the second dimension at all. `new long[3][4]` is `multianewarray` with a dimension count of 2, which allocates every dimension it's given in one instruction, strictly left to right, popping that many size operands off the stack. There's no instruction form that lets you supply a later dimension while deferring an earlier one, so `new long[][4]` isn't a runtime restriction — it's rejected by `javac` before it ever becomes bytecode.

</details>

**Q7.** After `long[][] grid = new long[3][4]; grid[1] = new long[7];`, what is `grid[0].length` and what is `grid[1].length`?

<details><summary>Answer</summary>

`grid[0].length` is still 4, and `grid[1].length` is now 7. The rows of a Java multi-dimensional array are independent objects — reassigning one row to a differently-sized array has zero effect on the others, because there was never a single rectangular object enforcing a shared row length in the first place, only a convention that the initial `new long[3][4]` happened to establish.

</details>

**Q8.** Does `grid.length` for a `long[3][4]` give you the row count or the column count?

<details><summary>Answer</summary>

The row count — the length of the outer array, which is 3 here. The column count is `grid[0].length`, and that number is only meaningful across all rows if nothing has reassigned an individual row to a different length; in general it's only "the length of that particular row."

</details>

**Q9.** Why does a local `long x;` fail to compile on an uninitialised read, while `new long[10][0]` compiles and reads `0` with no complaint?

<details><summary>Answer</summary>

Because locals and array components are different kinds of variable under JLS §4.12.3, with different initialisation rules. A local variable's storage is compiler-tracked stack space with no zero-fill guarantee, so `javac` runs definite-assignment analysis and refuses to compile a read before a write — that's a compile-time-only safety net, not a runtime default. An array component, by contrast, always gets its type's default value the moment the array is created, regardless of how many components there are or whether the surrounding code has written to any of them yet; that's the zero-fill guarantee from JLS §10.6/§4.12.5, and it applies uniformly to every slot at creation time.

</details>

## Open questions

None.

---

**Leaves covered:** 1.22.1, 1.22.2, 1.22.3, 1.22.4 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 555
