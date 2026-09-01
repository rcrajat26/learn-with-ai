# 03 Java Core — The drills and the retention schedule — INTERVIEW (§5.3, 5.3.1–5.3.8)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The version-stale claims and the expensive mistakes](94e2-interview-version-stale-and-mistakes.md) · Next: [The atomic concept checklist](94g-interview-atomic-concept-checklist.md)

These six drills are not a first read. They assume Parts 1 through 4 are already
behind you and the eighty questions of §5.1 have already been attempted once.
Each drill is timed against yourself, not against a clock printed here: read
the prompt, answer out loud before you look at the answer column, and log
where you stalled. A drill you pass silently in your head but cannot say in a
sentence has not been passed — an interview is conducted out loud, under a
person watching your face, and the gap between "I recognise this" and "I can
explain this cold" is exactly what these drills are built to expose. Run them
in order once, then run only the rows you stalled on.

## D-139 — The numbers drill card

**D-139** — Every constant this guide names, with its value and the mechanism it belongs to.

Recite the value from the constant name alone, then the mechanism, then where it lives. All
values confirmed on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245, macOS aarch64) unless the
"Where" column names a different provenance.

| Constant | Value | The mechanism it belongs to | Where |
|---|---|---|---|
| `Integer` cache range | `-128..127` | JLS §5.1.7's mandated floor for `Integer.valueOf` boxing; a conforming JVM must intern at least this range | `wrappers-and-boxing/03-internals-boxing.md` |
| `String.hashCode` multiplier | `31` | `s[0]*31^(n-1) + s[1]*31^(n-2) + … + s[n-1]`; odd and prime, and `31*i == (i<<5) - i` | `strings/03a-internals-hash-and-equality.md` |
| `Integer` object size | `16 bytes` | 12-byte header + 4-byte `int value`, already 8-aligned | `wrappers-and-boxing/03e-internals-wrapper-memory.md` |
| `Long` object size | `24 bytes` | 12-byte header, 4 bytes of forced padding so the 8-byte `long value` lands on an 8-byte boundary, then the 8-byte field | `wrappers-and-boxing/03e-internals-wrapper-memory.md` |
| `StringBuilder` growth | `2 * oldLength + 2` | `AbstractStringBuilder.newCapacity`'s preferred growth, feeding `ArraysSupport.newLength` | `strings/04-internals-stringbuilder-and-concat.md` |
| Class-file magic | `0xCAFEBABE` | first 4 bytes (`u4`) of every `.class` file, JVMS §4.1 | `language-substrate/03a-internals-class-file-format.md` |
| Class-file major version, Java 21 | `65` | `major = 44 + N`; the loader rejects a version-65 file outright on a JDK 17 runtime, before verification | `language-substrate/03a-internals-class-file-format.md` |
| Other class-file majors | `52`=8, `55`=11, `61`=17, `65`=21, `69`=25 | the same `major = 44 + N` ladder across LTS releases | `language-substrate/03a-internals-class-file-format.md` |
| Object header (compressed oops) | `12 bytes` | 8-byte mark word + 4-byte compressed class pointer | `objects-equality-and-lifecycle/05-internals-object-layout.md` |
| Array header | `16 bytes` | the 12-byte object header plus a 4-byte `int` length field | `objects-equality-and-lifecycle/05-internals-object-layout.md` |
| `Boolean.hashCode(true)` | `1231` | javadoc-specified, stable across every conforming JDK | `wrappers-and-boxing/01d-wrapper-equals-and-hashcode.md` |
| `Boolean.hashCode(false)` | `1237` | javadoc-specified, the paired constant | `wrappers-and-boxing/01d-wrapper-equals-and-hashcode.md` |
| `ArraysSupport.SOFT_MAX_ARRAY_LENGTH` | `Integer.MAX_VALUE - 8` = `2,147,483,639` | the JDK library's self-imposed growth ceiling beneath the true, implementation-dependent VM array limit; backs `ArrayList`, `StringBuilder`, and stream collectors | `arrays/01c-memory-layout-and-bounds.md` |
| `float` significand | `24 bits` | exact integers only up to `2^24 = 16,777,216`; above that, `long → float` and `int → float` can lose precision silently | `primitives-and-conversions/03-conversions-and-contexts.md` |
| `double` significand | `53 bits` (52 stored mantissa bits + 1 implicit leading bit) | exact integers up to `2^53 = 9,007,199,254,740,992`; binary64's 11-bit exponent and 52 explicit mantissa bits are the JLS/IEEE-754 layout | `numbers-and-money/04-internals-floating-point.md` |
| `BigDecimal.INFLATED` | `Long.MIN_VALUE` = `-9223372036854775808` | the one `long` value whose negation overflows, so it can never be a legitimate compact significand — used as the sentinel meaning "significand does not fit in a `long`, consult `intVal`" | `numbers-and-money/03-internals-bigdecimal.md` |
| `BigDecimal.MAX_COMPACT_DIGITS` | `18` | conservative cutoff below `Long.MAX_VALUE`'s 19 digits, deciding compact-vs-inflated representation | `numbers-and-money/03-internals-bigdecimal.md` |
| `String` coder `LATIN1` | `0` | the compact-strings byte-per-char encoding tag | `strings/03-internals-string.md` |
| `String` coder `UTF16` | `1` | the two-bytes-per-char fallback tag, chosen the moment any character exceeds U+00FF | `strings/03-internals-string.md` |
| `StringDeduplicationAgeThreshold` | `3` | G1's object-age gate: a `String`'s backing array becomes a dedup candidate at the collection where its survivor age equals exactly this value | `strings/03b-internals-stringtable-and-interning.md` |
| `BigInteger.valueOf` cache | `-16..16` inclusive | `MAX_CONSTANT = 16`; `posConst[MAX_CONSTANT+1]` and `negConst[MAX_CONSTANT+1]` — narrower than `Integer`'s cache and easy to over-generalise from | `numbers-and-money/02d-storage-biginteger-and-cost.md` |
| `StringTableSize` | `65536` buckets | `StringTable`'s starting bucket count; a `ConcurrentHashTable` since JDK 10, so this is a start size, not a ceiling | `strings/03b-internals-stringtable-and-interning.md` |
| `StringTable` growth trigger | first growth past `131,072` live entries | `items / StringTableSize > PREF_AVG_LIST_LEN (2.0)` | `strings/03b-internals-stringtable-and-interning.md` |
| `MaxJavaStackTraceDepth` | `1024` | the frame cap on `fillInStackTrace()`; a logical throw of depth 1500 still decodes to exactly 1024 frames | `exceptions/03b-internals-stack-trace-capture.md` |
| `AutoBoxCacheMax` | `128` | the `intx` flag whose value floors the `Integer` cache's upper bound at `Math.max(value, 127)` — raising it widens the cache, lowering it below 127 has no effect | `wrappers-and-boxing/03-internals-boxing.md` |
| `ObjectAlignmentInBytes` | `8` | every object's total size is rounded up to a multiple of this; it is why a bare `new Object()` is 16 bytes, not 12 | `objects-equality-and-lifecycle/05-internals-object-layout.md` |
| tzdb version bundled with this build | `2025a` | `$JAVA_HOME/lib/tzdb.dat`, 101,803 bytes, dated 21 Feb 2025, confirmed via `ZoneRulesProvider.getVersions("UTC").keySet()` | `date-and-time/03a-internals-zonerules-and-tzdb.md` |
| `HashMap.TREEIFY_THRESHOLD` | `8` | bin entry count at which a linked bin converts to a red-black tree | `strings/03a-internals-hash-and-equality.md` |
| `HashMap.MIN_TREEIFY_CAPACITY` | `64` | table size floor below which a flooded bin resizes the table instead of treeifying | `strings/03a-internals-hash-and-equality.md` |
| Shift-distance mask width | `5 bits` (`int`), `6 bits` (`long`) | why `1 << 32 == 1` and `1L << 64 == 1L` — the distance is masked, never clamped, and never throws | `primitives-and-conversions/02a-assignment-and-bitwise.md` |

## The conversion drill

Fifteen expressions, drawn verbatim from material already worked through in Parts 1 to 3. State
the result before reading the worked answer.

| # | Expression | Result | Why |
|---|---|---|---|
| 1 | `float w = 7_200_000_001L;` (a `long` ledger entry id) | `7.2000004E9` (rounds to `7,200,000,000`) | `long → float` is widening but lossy above `2^24` |
| 2 | `(int)(4.35 * 100)` | `434` | binary64 cannot hold `4.35` exactly; the product is a hair under `435.0` |
| 3 | `byte b = 200;` | compile error | `200` is outside `byte`'s constant-narrowing range |
| 4 | `(float) 16_777_217` | `1.6777216E7` (`== 16777216.0f`) | `16,777,217` exceeds the 24-bit significand's exact range by one |
| 5 | `(int) 1e20` | `2147483647` | float-to-integral casts saturate at the target's `MAX_VALUE` |
| 6 | `(long) 1e20` | `9223372036854775807` | same saturation rule, `long` ceiling |
| 7 | `Math.round(-0.9)` vs `(int) -0.9` | `-1` vs `0` | `Math.round` is floor(x + 0.5); a cast truncates toward zero |
| 8 | `(byte) 1e20` | `-1` | float-to-byte is a two-step conversion via `int`; the saturated `int` then narrows |
| 9 | `long window = 24 * 60 * 60 * 1000 * 1000;` | `500654080` | all five factors are `int` literals; the product overflows before the assignment widens it |
| 10 | `Long ledgerCount = 3;` | compile error | boxing is fixed per type (`int → Integer`); there is no widen-then-box composite to `Long` |
| 11 | `"ref " + charArray` (a `char[]`) | `ref [C@<hash>` | string-context conversion calls `toString()`; `char[]` inherits `Object.toString()` |
| 12 | `String.valueOf((char[]) null)` vs `String.valueOf((Object) null)` | `NullPointerException` vs `"null"` | the two overloads disagree on how they treat a null argument |
| 13 | `byte retries = 10; retries += 300;` | `54` | `+=` inserts an implicit `(byte)` cast that the expanded form does not have |
| 14 | `true ? Integer.valueOf(1) : Double.valueOf(2.0)` | `1.0` (as a `Double`) | numeric conditional promotes both operands to `double` before either is boxed back |
| 15 | `int n = flag() ? 0 : nullBonusCount;` with `flag()` false | `NullPointerException` | `int` + `Integer` collapses the expression type to `int`, so the selected `Integer` branch unboxes regardless of the declared target's nullability |

### Worked answers

**1.** `long → float` is one of the three widening conversions the JLS itself flags as potentially
lossy. `float`'s 24-bit significand is exact only to `2^24 = 16,777,216`; a ledger entry id of
7,200,000,001 sits in `[2^32, 2^33)`, where the representable spacing is `2^(32-23) = 512`, so the
value rounds to the nearest multiple of 512. Two distinct ledger ids can compare equal after
passing through a `float`. `double` is exact for the same value.

**2.** `4.35` is not exactly representable in binary64; the nearest double is a hair below the
mathematical value. Multiplying by 100 and truncating with `(int)` lands on 434, not 435 —
the textbook reason money must never be a `double`.

**3.** Assignment-context narrowing only fires for a *constant expression* of type `byte`,
`short`, `char` or `int` whose value fits the target. `200` does not fit a signed `byte`
(`-128..127`), so this is a compile-time range check failure, not a runtime wrap.

**4.** `16,777,217` is one past the last integer `float` can hold exactly; casting it to `float`
rounds to the nearest representable value, `16,777,216.0f`, silently losing the `+1`.

**5.** Floating-to-integral casts never throw. JLS §5.1.3 specifies saturation: a value above the
target type's range clamps to `MAX_VALUE`, so `(int) 1e20` is `2147483647`, not undefined and not
a wraparound.

**6.** Same saturation rule, evaluated against `Long.MAX_VALUE` instead: `9223372036854775807`.
`Math.round(1e20)` returns the identical value because `Math.round(double)` itself returns a
`long`.

**7.** `Math.round` computes `floor(x + 0.5)`; `-0.9 + 0.5 = -0.4`, whose floor is `-1`. A plain
`(int)` cast truncates toward zero, so `-0.9` becomes `0`. The two operations disagree on every
negative fraction whose magnitude is under 0.5.

**8.** `float → byte` is not a single instruction; it goes through `int` first. `(int) 1e20`
saturates to `2147483647`, and `(byte) 2147483647` keeps only the low eight bits of that value,
which happen to be all-ones — `-1`. The surprise is entirely in the intermediate `int`, invisible
at the `(byte)` cast site.

**9.** All five literals are `int`; four multiplications happen entirely in 32-bit arithmetic
before the result is ever widened to `long`. `86,400,000,000` does not fit in an `int`, wraps
modulo `2^32`, and lands on `500,654,080` — positive, so nothing looks obviously wrong. Fix by
making the first literal `24L`.

**10.** For a primitive source and reference target, §5.2 permits boxing then optionally a
widening *reference* conversion. `int` boxes only to `Integer`; `Integer`'s supertypes
(`Number`, `Comparable<Integer>`, `Serializable`, `Object`) do not include `Long`, a sibling
final class. There is no "widen the primitive, then box" composite either, so no path exists.

**11.** `PrintStream.println(char[])` writes characters directly and is not a conversion at all;
putting the same array in string concatenation invokes string conversion, which calls
`toString()` on a reference type. `char[]` inherits `Object`'s identity-hash-based `toString()`,
giving the `[C@…` form rather than the characters.

**12.** `String.valueOf(Object)` returns the literal string `"null"` for a null `Object`
argument; `String.valueOf(char[])`'s body dereferences the array's length and throws. The two
overloads look identical at the call site and diverge completely on null.

**13.** `E1 op= E2` desugars to `E1 = (T)((E1) op (E2))` per JLS §15.26.2, with `T` the
declared type of `E1`. The implicit `(byte)` cast keeps the low 8 bits of `310` (`0000 0001
0011 0110`), giving `0011 0110 = 54`. The expanded form has no such cast and is a compile
error.
​
**14.** JLS §15.25's numeric-conditional table classifies `int`/`double` mixes (after unboxing
the `Integer`) as promoting to `double`. The taken `Integer` branch is unboxed, widened to
`1.0d`, then reboxed to `Double` for the `Object`-typed result — the `Integer` you wrote never
survives past the expression's static type computation.

**15.** The expression type is computed from the two operand types alone, before either branch
is evaluated: `int` and `Integer` collapse to `int` under §15.25. The selected branch — the
boxed `Integer` — is therefore unboxed regardless of what the assignment target's type is; making
the target `Integer` instead of `int` does not save you, because the target type plays no role in
§15.25's table.

## The mechanism drill

Fifteen mechanisms, one sentence each — the sentence that would actually satisfy an interviewer,
not a label.

| Mechanism | The one-sentence explanation | Where |
|---|---|---|
| Erasure | Every generic type and type variable is replaced with a single runtime representation — a parameterized type's own erasure, or a type variable's leftmost bound's erasure — so the JVM never sees a type argument, only whatever `checkcast` or `Signature` metadata the compiler chose to leave behind. | `generics/03-internals-erasure.md` |
| Bridge method | A compiler-synthesized `ACC_BRIDGE ACC_SYNTHETIC` method with the erased superclass descriptor that forwards to the real override, because `invokevirtual` dispatches by exact name-and-descriptor match and an erased caller and a concretely-typed override are two different descriptors sharing a name. | `generics/03a-internals-bridge-methods.md` |
| `$VALUES` | The private static synthetic array field holding every enum constant in declaration order, assigned last in `<clinit>` after every constant's own `putstatic`, and cloned on every call to `values()` so callers cannot mutate the canonical array. | `enums/03-internals-enums.md` |
| `$SwitchMap` | A per-switching-class synthetic holder (`Outer$1`) with one `int[]` field per enum type switched over, indexed by ordinal, that lets an enum `switch` compile to a dense `tableswitch` instead of a chain of `invokevirtual`-and-compare. | `enums/03b-internals-guarantees-and-switch.md` |
| `this$0` | The compiler-injected `final` field on an inner (non-static) class instance holding a live reference to its enclosing instance, written by `putfield` before `Object`'s own constructor runs, and emitted only if the body actually uses it. | `inheritance-and-dispatch/04-internals-nested-classes.md` |
| `val$x` | One synthetic `final` field per captured effectively-final local, value-copied at construction time from an appended constructor parameter, because there is no other way to keep a heap-allocated closure and a stack frame's local slot in step. | `inheritance-and-dispatch/04-internals-nested-classes.md` |
| `<clinit>` | The class or interface initializer, uncallable by any JVM instruction, run exactly once at one of JVMS §5.5's six specified trigger points and responsible for every `static` field assignment that is not itself a compile-time constant. | `classes-and-initialization/03-internals-class-loading-and-init.md` |
| `invokedynamic` concat | Since Java 9 (JEP 280), string concatenation compiles to a single `invokedynamic` call site bootstrapped through `StringConcatFactory.makeConcatWithConstants`, replacing the pre-9 `new StringBuilder`/`append`/`toString` chain with a linked, cached method-handle tree. | `strings/04-internals-stringbuilder-and-concat.md` |
| `IntegerCache` | A private static holder class nested in `Integer` that pre-allocates and caches boxed instances for at least `-128..127` per JLS §5.1.7, so `Integer.valueOf` inside that range returns a shared object and `==` on two such boxes is true by accident of caching rather than by any language guarantee outside the range. | `wrappers-and-boxing/03-internals-boxing.md` |
| `hashIsZero` | A `String` field added in Java 13 that records "the true hash really is zero" separately from the lazy-cache field defaulting to zero, so a string whose genuine hash is `0` (the empty string, or any string that happens to hash there) does not recompute its hash on every call. | `strings/03a-internals-hash-and-equality.md` |
| `intCompact` | `BigDecimal`'s `final transient long` fast-path significand, holding the actual value when it fits in a `long` and the sentinel `INFLATED` (`Long.MIN_VALUE`) when it does not, sparing most arithmetic from touching the heavier `BigInteger`-backed `intVal`. | `numbers-and-money/03-internals-bigdecimal.md` |
| Exception table | The `Code` attribute's `(start_pc, end_pc, handler_pc, catch_type)` rows, JVMS §4.7.3, that `athrow` consults in source order to find the first range-and-type match, implementing every `catch`, `finally`, and synchronized-block unlock with zero cost on the path that enters the guarded region. | `exceptions/03-internals-exception-mechanics.md` |
| `fillInStackTrace` | The native method that walks the current call stack at throw-construction time and records it into the `Throwable`'s opaque `backtrace` field, capped at `MaxJavaStackTraceDepth` frames, and the single most expensive step in constructing a normal (non-stackless) exception at shallow depth. | `exceptions/03b-internals-stack-trace-capture.md` |
| Final field freeze | JLS §17.5's guarantee that once a constructor writing a `final` field exits — normally or abruptly — any thread that later obtains a reference to that object only through a properly published channel is guaranteed to see the correctly initialized `final` fields, a guarantee that is voided entirely, not weakened, if the constructor lets `this` escape early. | `classes-and-initialization/04-internals-final-and-constant-folding.md` |
| Nestmates | JEP 181's model, live since Java 11, where all classes compiled from one top-level source file share one `NestHost`/`NestMembers` relationship and the JVM itself enforces private-member access between them via direct `invokevirtual`/`getfield`, replacing the pre-11 synthetic `access$NNN` package-widening forwarders. | `inheritance-and-dispatch/04-internals-nested-classes.md` |

## The code-reading drill

Ten snippets, captured output, real mechanism. Say the output before reading it.

### 1 — `i = i++`

```java
static void selfAssignedIncrement() {
    int reservationsScanned = 0;
    reservationsScanned = reservationsScanned++;
    System.out.println(reservationsScanned);
}
```

<details><summary>What it prints, and why</summary>

Prints `0`. JLS §15.26.1 fixes the order inside a simple assignment: the target location is
determined first, the right-hand side is evaluated in full, then the value is stored last.
Postfix `++` yields the pre-increment value and increments as a side effect on the *slot*, not
on the value already pushed to the operand stack — bytecode is `iload_0` (pushes `0`), `iinc 0,1`
(slot becomes `1`, stack still holds `0`), `istore_0` (the stale `0` overwrites the slot). The
store always wins over the side effect.

</details>

### 2 — `char` arithmetic

```java
static void charPlusIntPromotes() {
    char phaseLetter = 'A';
    System.out.println(phaseLetter + 1);
}
```

<details><summary>What it prints, and why</summary>

Prints `66`, not `B`. Binary numeric promotion (JLS §5.6.2) widens the `char` to `int` before `+`
runs, and nothing in the rule returns the result to `char`; the expression's type is `int`, so
concatenation renders it as a decimal number. `(char)(phaseLetter + 1)` would print `B`; so would
`phaseLetter += 1`, because compound assignment inserts an implicit narrowing cast the plain form
lacks.

</details>

### 3 — Ternary unboxing that does not throw

```java
static void ternaryGuardTrueNoThrow() {
    Integer unknownStakeCount = null;
    boolean stakeBlocked = true;
    int stakes = stakeBlocked ? 0 : unknownStakeCount;
    System.out.println(stakes);
}
```

<details><summary>What it prints, and why</summary>

Prints `0` — it does **not** throw. The widely-repeated claim is that a numeric ternary with a
boxed `null` operand always throws once the expression type is `int`. JLS §15.25 says only one
operand is evaluated; the unboxing conversion applies to the value the taken branch produced, not
to both branches speculatively. Bytecode confirms it: the `invokevirtual Integer.intValue`
instruction sits only on the else-arm's path, unreachable when the guard takes the then-arm.

</details>

### 4 — The `Integer` cache boundary

```java
static void integerCacheBoundary() {
    Integer a = 127, b = 127;
    Integer c = 128, d = 128;
    System.out.println((a == b) + " " + (c == d));
}
```

<details><summary>What it prints, and why</summary>

Prints `true false`. `Integer.valueOf` returns a shared cached instance for `-128..127` per
JLS §5.1.7, so both `127`s are literally the same object and `==` is true by construction; `128`
is one past the guaranteed cache, so each boxing allocates a fresh `Integer` and `==` is false.
`equals` would print `true true` in both cases — the cache affects identity, never value equality.

</details>

### 5 — `Math.abs(Integer.MIN_VALUE)`

```java
static void absOfMostNegative() {
    int ledgerDelta = Integer.MIN_VALUE;
    System.out.println(Math.abs(ledgerDelta) < 0);
}
```

<details><summary>What it prints, and why</summary>

Prints `true`. Two's complement over 32 bits covers `-2^31..2^31-1`, one value asymmetric because
zero occupies a non-negative slot, so `+2147483648` is not representable as an `int`. `Math.abs`
is specified to return `Integer.MIN_VALUE` unchanged for exactly this input, meaning it returns a
negative number and a magnitude check written `Math.abs(delta) < limit` silently passes for the
one value that most needs rejecting. `Math.absExact` throws `ArithmeticException` instead.

</details>

### 6 — `split` on a bare dot

```java
static void splitTakesARegex() {
    String schemaVersion = "3.2.1";
    System.out.println(schemaVersion.split(".").length);
}
```

<details><summary>What it prints, and why</summary>

Prints `0`, not `3`. `String.split(String)` treats its argument as a regular expression, and `.`
is the any-character metacharacter, so every character of `"3.2.1"` is a delimiter and every
resulting field is empty; the zero-limit default then strips all trailing empty strings, leaving a
zero-length array. The fix is `split("\\.")` or `split(Pattern.quote("."))`, both of which print
`[3, 2, 1]`.

</details>

### 7 — `0.1 + 0.2` as a balance

```java
static void binaryFloatingPointSum() {
    double bonusBalance = 0.1 + 0.2;
    System.out.println(bonusBalance == 0.3);
}
```

<details><summary>What it prints, and why</summary>

Prints `false`. Binary64 stores only rationals whose denominator is a power of two; `0.1` and
`0.2` are each the nearest representable neighbour, not the exact decimal, and their sum rounds a
second time, landing one ulp above the double nearest `0.3`. `new BigDecimal(0.1 + 0.2)` reveals
the exact stored value as `0.3000000000000000444089209850062616169452667236328125`. A stake
balance must be `BigDecimal` at a fixed scale or a `long` of minor units — never `double`.

</details>

### 8 — `BigDecimal.equals` and scale

```java
static void bigDecimalEqualsIsScaleSensitive() {
    BigDecimal grantedBonus = new BigDecimal("2.0");
    BigDecimal reportedBonus = new BigDecimal("2.00");
    System.out.println(grantedBonus.equals(reportedBonus) + " " + (grantedBonus.compareTo(reportedBonus) == 0));
}
```

<details><summary>What it prints, and why</summary>

Prints `false true`. `BigDecimal` is the pair (unscaled value, scale): `"2.0"` is `(20, 1)` and
`"2.00"` is `(200, 2)`. `equals` requires both components to match, so it is false; `compareTo`
compares numeric value only and reports `0`. This is a documented, deliberate violation of the
`Comparable`-agrees-with-`equals` convention — a `HashSet<BigDecimal>` misses a value a
`TreeSet<BigDecimal>` finds, for the identical pair of objects.

</details>

### 9 — Concatenating `null`

```java
static void concatenatingNull() {
    String missingCoupon = null;
    String rendered = "coupon=" + missingCoupon;
    System.out.println(rendered.length());
}
```

<details><summary>What it prints, and why</summary>

Prints `11`. JLS §15.18.1 converts a null reference operand of `+` to the four-character string
`"null"`; `"coupon="` is 7 characters, plus 4 is 11. Since Java 9 (JEP 280) this compiles to a
single `invokedynamic` call to `StringConcatFactory.makeConcatWithConstants`, not a
`StringBuilder` chain — the bootstrap's method-handle tree calls `String.valueOf` on the argument,
and `String.valueOf(Object)` is what supplies the literal `"null"`.

</details>

### 10 — Static methods are hidden, not overridden

```java
static class WithdrawalRail {
    static String railName() { return "bank-withdrawal"; }
    String describe() { return "rail=" + railName(); }
}

static class CardWithdrawalRail extends WithdrawalRail {
    static String railName() { return "card-withdrawal"; }
}

static void staticMethodsAreHidden() {
    WithdrawalRail asBase = new CardWithdrawalRail();
    System.out.println(asBase.describe());
}
```

<details><summary>What it prints, and why</summary>

Prints `rail=bank-withdrawal`, not `rail=card-withdrawal`. JLS §8.4.8.2: a `static` method
with a matching signature in a subclass *hides* the superclass method rather than overriding it.
`describe()` is declared in `WithdrawalRail`, so its unqualified call to `railName()` compiles to
`invokestatic WithdrawalRail.railName`, a target fixed at compile time with no receiver lookup —
the object's real runtime class, `CardWithdrawalRail`, is never consulted.

</details>

## The "which construct" drill

Fifteen QuizStakes situations, each answered in one or two words.

| # | Scenario | The construct |
|---|---|---|
| 1 | A type defined entirely by its components, with no identity beyond their values (`Money`, `StakeSplit`) | `record` |
| 2 | A closed, known set of implementations that a `switch` must handle exhaustively (`Verdict`) | `sealed interface` |
| 3 | A fixed, closed set of named values with per-constant behaviour (`RestrictionType`) | `enum` |
| 4 | A compile-time literal limit that never changes without a release (`BONUS_CAP_MINOR = 100`) | `static final` primitive |
| 5 | A failure the immediate caller can act on and that must carry a reason as data through a pipeline | `Result` type (sealed) |
| 6 | A failure that is genuinely exceptional and not expected to be handled at this call frame | unchecked exception |
| 7 | A rare I/O-boundary failure with a real, available fallback at the call site | checked exception |
| 8 | An amount of money held at a fixed, explicit scale | `BigDecimal` |
| 9 | An amount of money represented without allocation, at the wire boundary | `long` of minor units |
| 10 | A supplied credential that must be erasable from the heap at a moment you choose | `char[]` |
| 11 | A payload whose byte encoding is not yours to decide, verified by an HMAC over raw bytes | `byte[]` |
| 12 | A point on the UTC timeline with no notion of a calendar or a zone | `Instant` |
| 13 | A wall-clock reading whose arithmetic must respect daylight-saving transitions | `ZonedDateTime` |
| 14 | Copying a mutable container whose elements are themselves immutable | shallow copy (`List.copyOf`) |
| 15 | A single-method callback with no need to name or reuse the type | lambda |

## The traps drill

Ten symptom-to-mechanism pairs. Given the symptom alone, name the mechanism before reading the
diagnosis.

| The symptom you are handed | The mechanism to name | The one-line diagnosis |
|---|---|---|
| A shared date formatter produces garbled or wrong values only under concurrent load | `SimpleDateFormat` mutable internal `Calendar` state | It is not a visibility bug a `volatile` field fixes — the whole multi-step `format()` call is unsynchronized state mutation; use one `static final DateTimeFormatter`, which is genuinely immutable. |
| `NullPointerException` on a line with no visible method call | compiler-inserted unboxing (`invokevirtual intValue()`) | An `Integer`/`int` mix in a numeric context — a ternary, an arithmetic expression, an autoboxed collection read — hides an `intValue()`/`longValue()` call the source never spells out. |
| `ClassCastException` whose top frame names a real method, at the class's declaration line rather than a statement | a synthetic bridge method | The `checkcast` lives inside a compiler-generated bridge in the *callee's* class, not at any statement you wrote; distinguish it from erasure's caller-side cast, which sits on a real statement line in the *caller*. |
| A limit changed in source, passed review, and is still the old number in production | inlined constant variable | `javac` copies a `static final` primitive or `String`'s value directly into every caller's class file at compile time; a partial rebuild leaves un-recompiled callers permanently on the old value with no linkage error. |
| A stack trace on a hot method is empty with a null message | `-XX:+OmitStackTraceInFastThrow` | HotSpot substitutes a preallocated, stackless instance for a hot implicit exception (NPE/AIOOBE/CCE); it is a JIT optimisation, not a broken logging pipeline. |
| A `.equals()`-based lookup silently misses a value that a `.compareTo()`-based lookup finds, on the same two objects | `BigDecimal.equals` comparing scale | `equals` requires unscaled value **and** scale to match; `compareTo` compares numeric value only — a documented divergence from the `Comparable` convention. |
| A raw-typed generic reference method call throws a hard compile error where the same call through a parameterized reference compiles fine | erasure of every member, not just the class's own type parameter | JLS §4.8: using a raw type erases the whole class, including an unrelated generic method's own type variable — `totalsBy("KEY", entry)` through a raw `Repository` returns raw `Map`, and `.get("KEY")` returns `Object`. |
| `AbstractMethodError` appears in production on a module whose own jar was never touched | binary-incompatible interface change | Adding an `abstract` method to a published interface compiles cleanly against any implementor already compiled against the old shape, but is binary-incompatible; the failure surfaces only once that un-rebuilt jar loads. |
| A previously-serialized stream deserializes without error but now calls a different method body | lambda ordinal shift | A lambda's synthetic name (`lambda$method$0`) is an auto-incrementing ordinal tied to source position; adding or reordering an earlier lambda in the same method shifts the number silently. |
| A caught-and-rethrown exception's message is just the literal string the `catch` block wrote, with no trace of the original failure | discarded cause chain | Translating an exception without passing the original as the `cause` argument throws away everything the original — including a helpful NPE message — could have told you. |

## The spaced-repetition schedule

| Day | What you do | How long it takes | What it proves |
|---|---|---|---|
| 1 | Read this file end to end once, out loud where a drill asks for a spoken answer | 60–90 min | You can follow the material; it says nothing yet about retention |
| 3 | Run the atomic concept checklist in `94g-interview-atomic-concept-checklist.md` cover-to-cover | 30–40 min | Recognition survives 48 hours without a reread |
| 7 | Run the numbers drill (D-139) and the conversion drill from memory, no peeking until you commit an answer | 25–35 min | Precise values and expression results survive a week — the two categories most likely to have quietly decayed |
| 14 | Run the code-reading drill: predict every output before opening the `<details>` block | 20–30 min | You can still trace bytecode-level reasoning, not just recall a punchline |
| 21 | Build two working, compiling items pulled from Part 4 — a diagnostic harness and one build-it artefact — from a blank file, no copy-paste | 60–120 min | You can produce the mechanism, not just recognise it when shown |

Run days 1, 3 and 7 exactly as scheduled even if they feel too soon — the value of spaced
repetition is in catching decay before it becomes forgetting, and a concept that still feels
fresh on day 3 is cheap to confirm and expensive to silently lose by day 14. Day 7 is the
heaviest single day: numbers and conversions are the two categories with no narrative thread to
hang a wrong answer on, so a slip here is silent — you say a confident wrong number, not an
obvious "I don't know."

Day 21 is qualitatively different from the other four, and it is the only one worth protecting if
your calendar forces a choice. Days 1 through 14 test recognition: can you read a mechanism and
say what it is. Day 21 tests production: can you sit at a blank file and make the JVM do the thing
without a scaffold to fill in. An engineer who aces every recognition drill and has never once
written a stackless-exception harness, a bridge-method probe, or an `IntegerCache` boundary test
from scratch has a gap that recognition drills cannot find, because recognition drills never ask
you to generate the code. Build the two items honestly — no looking at `build-it/` while you
write — and only then compare against the original.

## The atomic concept checklist

Leaf 5.3.8 is carried by the single, flat, file-set-wide checklist that closes the guide in
[`94g-interview-atomic-concept-checklist.md`](94g-interview-atomic-concept-checklist.md) — 350
bullets, one per atomic concept across all five parts. It sits in its own file rather than at the
foot of this one because the drills above already fill this file, and because a checklist that
downstream tooling parses should be the whole of what it is read for. It is not repeated anywhere
else: a second copy would give every reader two lists to reconcile, and reconciliation is exactly
the kind of quiet disagreement a checklist exists to prevent.

To drill against it: cover the page so only the bullet text shows, read each assertion in turn,
say the mechanism behind it out loud in one sentence before uncovering any elaboration, and mark
the ones you stall on with a tally rather than erasing and re-reading. A bullet you can state but
not explain the mechanism of is not yet passed — that gap is precisely what the mechanism drill
above exists to close for the fifteen most commonly stalled-on cases.

## Part 5 summary table

| Section | What it gives you | When to use it | Where |
|---|---|---|---|
| §5.1 — the eighty questions | Full spoken-length model answers across every tier of the guide, ordered by difficulty | First pass through Part 5, or refreshing one specific area before a loop | [`94-interview-questions-and-drills.md`](94-interview-questions-and-drills.md), [`94a`](94a-interview-questions-17-32.md), [`94b`](94b-interview-questions-33-48.md), [`94c`](94c-interview-questions-49-64.md), [`94d`](94d-interview-questions-65-80.md) |
| §5.2 — the trap index and version-stale claims | Every wrong-belief-to-symptom-to-fix triple in the guide, plus the folklore that was true once and is not true on 21 | The week before a loop, and any time a claim you are about to repeat "sounds like something I read a while ago" | [`94e-interview-trap-index.md`](94e-interview-trap-index.md), [`94e2-interview-version-stale-and-mistakes.md`](94e2-interview-version-stale-and-mistakes.md) |
| §5.3 — the drills and retention schedule | Timed, out-loud drills across numbers, conversions, mechanisms, surprising output, construct choice and traps, plus the spaced-repetition plan that keeps all of the above from decaying | Second and third readings; the last file to run before a loop, and the only one with a build step | This file |

## Interview Q&As

### 1. How do you keep up with new Java versions without re-learning everything from scratch every six months?

Java's six-month cadence means most releases add a handful of genuinely new mechanisms and a
larger number of small library additions. I track the JEP index for the two categories that
actually change how I reason about code: language and class-file features (pattern matching,
sealed types, virtual threads), and JVM-flag or default changes that silently alter behaviour
(compressed oops thresholds, `OmitStackTraceInFastThrow`, the JEP 400 UTF-8 default). I do not try
to memorise every JEP; I keep a short list of "what changed under me" per LTS boundary — 8→11→17→21
in my case — because most production code sits on an LTS for years and the gap between LTS
releases is the gap I actually have to bridge. When I hit an unfamiliar behaviour, my first move is
to check which release introduced it before assuming it is new folklore or an old fact I misremember
— `strictfp` becoming a no-op in 17, or helpful NPE messages defaulting on in 15, are exactly the
kind of thing that is easy to get backwards if you last checked five years ago.

### 2. How do you know whether a Java claim you read online is still true on the version you actually run?

I do not trust a claim's confidence level — folklore about `String` interning, `StringBuilder`
doubling, or private-method dispatch is repeated with total confidence and dead wrong on current
JDKs. My default is to reproduce it: `javap -c -p -v` on a class compiled with `--release <N>`
shows exactly what the compiler emitted, with no interpretation layer between me and the bytes.
For a runtime-flag claim I run `java -XX:+PrintFlagsFinal -version | grep <Flag>` on the actual
JDK build in question, because ergonomic defaults depend on heap size and platform and a number
quoted from someone else's machine may not be my number. For a behavioural claim about the
compiler's decisions specifically — "generics are erased," "strings intern automatically" — I
treat "I read it" and "I ran it" as different confidence levels and say so explicitly rather than
presenting a remembered claim as a verified one.

### 3. How would you find out what the compiler actually generated for a piece of code you're unsure about?

`javap -c -p -v` on the compiled `.class` file, always — not a decompiler. A decompiler
reconstructs source-like text from bytecode and is useful for *navigating* a large class you don't
know, but it actively hides the things worth knowing: it will render an enhanced-for loop back as
`for (Movement m : movements)`, making it look like no `Iterator` was ever allocated, when the
bytecode underneath clearly shows `invokeinterface List.iterator` and a synthetic loop. If someone
asks "did this get erased, boxed, or bridged," the only tool that cannot be wrong is the
disassembler reading the exact bytes the JVM will load — nothing is inferred, and the trailing
comments next to each instruction are `javap` resolving constant-pool indices for you, not a guess.
I reach for the decompiler to get oriented in an unfamiliar class and for `javap` the moment the
question becomes "what did the compiler actually do here."

### 4. What would you check before believing a microbenchmark number, whether it's yours or someone else's?

First, whether it's JMH or a hand-rolled timing loop — a loop with no warmup, no dead-code-elimination
guard, and no fork risks measuring JIT warmup noise or having the whole computation optimised away.
Second, the depth or scale at which the number was measured, because several of the ratios in this
guide are depth-dependent and quoting them without the depth is actively misleading — the
stackless-exception speedup is roughly 49x at depth 1 and collapses to under 1.5x by depth 100,
and either number alone, presented as "the" number, is wrong. Third, whether the benchmark isolates
one thing or conflates several — a `StringBuilder` growth benchmark that also allocates a
`BigDecimal` per iteration is measuring something else entirely. And fourth, whether it was run on
the JVM build and platform I actually care about; absolute nanosecond figures are not portable off
the machine that produced them, only the relative comparison within one run usually is.

### 5. How do you decide between two language constructs — say, a `record` versus a plain `class`, or a checked versus an unchecked exception — under interview time pressure?

I ask the question the construct is actually answering, not which one "feels more modern." For a
data-shape decision: is this type defined entirely by its components with no identity of its own —
if yes, `record`; if the object has a lifecycle or identity beyond its field values, `class`. For
error handling: can the *immediate* calling frame act on this failure, and does a reason need to
travel with it as typed data — if the immediate caller has a real fallback, checked; if it's
genuinely exceptional and no frame nearby can act on it, unchecked; if it's a per-element outcome in
a batch or stream, a sealed `Result` type. The trap under time pressure is deciding by a proxy
signal — "how often does this fail" instead of "can the caller act on it" — which produces a
codebase where every frequent failure got demoted to a return code (including ones that needed a
real fallback) and every rare one got promoted to checked (including ones nobody can handle).

### 6. What do you do in an interview when you genuinely don't know the answer to a Java internals question?

Say so directly, then reason from what I do know rather than guessing at a specific number I'm not
sure of. If I'm asked, say, the exact default of a JVM flag I haven't personally confirmed, I say
that I don't have that number memorised, then describe how I'd get it — `-XX:+PrintFlagsFinal
-version`, or `jcmd <pid> VM.flags` for a live process, since ergonomic defaults depend on heap size
and platform and a memorised number from a different machine could be wrong anyway. I would rather
give a confident, correct method for finding the answer than a confident, wrong number — a candidate
who says "128, I think, but let me be honest I'm recalling that from `AutoBoxCacheMax`'s printed
default rather than deriving it" reads as more reliable than one who states a number with no
hedge and no path to verifying it.

### 7. How do you verify a claim about object memory layout — like "this object is N bytes" — rather than just quoting a rule of thumb?

I use JOL (Java Object Layout) to print an actual instance's layout — header, field offsets, and
padding — combined with `-XX:+PrintFlagsFinal` to confirm the alignment and compressed-oops
settings the arithmetic depends on, since the same object is a different size with compressed oops
on versus off. The rule-of-thumb version — "add up the header and the fields" — misses the two
things that actually decide the number: field reordering (HotSpot fills the 4-byte gap after a
12-byte header with the first available 4-byte field, ignoring declaration order) and 8-byte
alignment rounding up the total. A `Long` being 24 bytes rather than a naively expected 20 is the
canonical example: the 4 extra bytes are alignment padding forced in front of the `long` field, not
part of the payload, and no rule of thumb catches that without actually measuring it.

### 8. What's your process for debugging a `ClassCastException` or `NullPointerException` that doesn't seem to match any cast or method call in the visible source?

First I read the exception's message closely — helpful NPE messages, default-on since Java 15, name
the exact null expression, which usually settles it immediately. If the trace's top frame names a
real method at a line number that looks like a class declaration rather than a statement, I suspect
a synthetic bridge method: the cast lives inside a compiler-generated forwarder in the callee's
class, invisible from the caller's source. If the CCE instead sits on a real statement line, I
suspect erasure's caller-side `checkcast`, inserted where the caller's type argument promises more
than the callee's erased return type. For an NPE with no visible dereference, I check for
autoboxing — a numeric ternary or an arithmetic expression mixing `int` and `Integer` inserts an
`intValue()` call the source never spells out. In every case, `javap -c -p -v` on the class in
question resolves the ambiguity in under a minute rather than guessing from the stack trace alone.

### 9. Why does the guide insist on citing a version number every time it states a "fact" about the language, and how does that show up in an actual interview?

Because a large fraction of confidently-repeated Java folklore was true on some past version and
is false on 21, and stating it without a version is how the wrong half survives. `strictfp` used to
matter and is a no-op since 17; private instance methods used to compile to `invokespecial` and
compile to `invokevirtual` since 11; the default charset used to be platform-dependent and has been
UTF-8 since 18. In an interview, the strongest answer to a version-sensitive question isn't just the
current-version fact — it's the fact plus what changed and when, because that demonstrates the
claim was verified against a specific build rather than recalled from a training set with no
timestamp. It also protects against the interviewer's own folklore: if they expect the pre-11
`invokespecial` answer and I state the 21 behaviour with the version boundary named, that reads as
precision, not disagreement for its own sake.

### 10. If you had one day left before a Staff-level Java interview, what would you actually do with it?

Not a full reread. I'd run the day-7 and day-14 drills from this file's spaced-repetition schedule —
the numbers drill, the conversion drill, and the code-reading drill — because those are the three
categories where a wrong answer is silent: I'd say a confident, precise-sounding wrong number with
no hesitation to signal it. Then I'd skim the trap index for anything I've personally been bitten by
in real code, since a trap tied to a memory sticks far better than one read cold. I would
deliberately skip re-deriving mechanisms I can already explain fluently — object layout, erasure,
exception mechanics — because a day-before cram is for catching decay in facts with no narrative
thread, not for re-building understanding that's already solid. I would not attempt the day-21
build step the night before; writing a correct diagnostic harness from a blank file under time
pressure the day before an interview is more likely to seed doubt than confidence.

## Predict the output

### 1

```java
static void wrapperEqualsVsDoubleEquals() {
    Double first = Double.NaN;
    Double second = Double.NaN;
    double primitiveA = Double.NaN;
    double primitiveB = Double.NaN;
    System.out.println(first.equals(second));
    System.out.println(primitiveA == primitiveB);
}
```

**Output**
```text
true
false
```

**Why** `Double.equals` compares the results of `doubleToLongBits`, a bit-pattern comparison, and
every `NaN` bit pattern this method produces canonicalizes to the same value, so two boxed `NaN`s
compare equal under `equals`. The primitive `==` follows IEEE 754 directly, where `NaN` is by
specification unequal to every value including itself. `Double.equals` and `==` are not the same
relation on `double`, and `NaN` and `-0.0`/`0.0` are exactly the two values where they visibly
diverge.

### 2

```java
static void arrayCovarianceThrows() {
    Object[] restrictions = new String[3];
    restrictions[0] = "STAKE_BLOCKED";
    restrictions[1] = 42;
}
```

**Output**
```text
Exception in thread "main" java.lang.ArrayStoreException: java.lang.Integer
```

**Why** Arrays are covariant at compile time — `String[]` is assignable to `Object[]` — but a
`String[]` object still carries its actual component type at runtime, and every `aastore`
instruction checks the stored value against it. The first assignment succeeds because a `String`
fits; the second fails, because the array's real element type is `String`, not `Object`, and
generics deliberately forbid this exact hole by banning generic array creation outright.

### 3

```java
static void enumValuesInStaticBlock() {
    System.out.println(RestrictionSource.values().length);
}

enum RestrictionSource {
    SYSTEM_ONBOARDING, SYSTEM_COMPLIANCE, SYSTEM_LIFECYCLE, ADMIN, CLIENT;
    static { System.out.println("during <clinit>: " + values().length); }
}
```

**Output**
```text
during <clinit>: 5
5
```

**Why** `$VALUES` is the last field written by an enum's `<clinit>`, at an offset after every
constant's own constructor call — but a `static { }` block that runs *after* the constant
declarations still executes inside the same `<clinit>`, after `$VALUES` is fully populated. Calling
`values()` from a constructor (before any constant has finished constructing) would `NullPointerException`,
but calling it from a trailing static initializer block is safe, because ordering within `<clinit>`
is source order and the block comes last.

### 4

```java
static void stringSwitchOnCoderMismatch() {
    String status = "AA-801";
    String cafeStatus = "café-801";
    System.out.println(status.equals(cafeStatus.substring(0, 6)));
}
```

**Output**
```text
false
```

**Why** This is not a content mismatch you can eyeball — `cafeStatus.substring(0, 6)` is
`"café-8"`, which visibly differs from `"AA-801"` in every character, so the answer looks
unremarkable until you notice the deeper rule it's obscuring: `String.equals` short-circuits on
`coder` before comparing any bytes. `"AA-801"` is `LATIN1`-encoded and fits in one byte per
character; `"café-801"` contains `é` (U+00E9), forcing the whole string to `UTF16`. Two strings
with different coders are **never** equal regardless of content, which matters far more once the
prefixes genuinely do look alike — a compact-strings-encoded status code and a UTF-16 one differing
only in one invisible character will fail `equals` before a single character is inspected.

### 5

```java
static void tryFinallyOverridesReturn() {
    System.out.println(reserveWithFinally());
}

static int reserveWithFinally() {
    try {
        return 1;
    } finally {
        return 2;
    }
}
```

**Output**
```text
2
```

**Why** A `return` inside a `finally` block discards any in-flight return (or thrown exception)
from the `try` block outright — the `finally`'s abrupt completion by `return` supersedes the
`try`'s, per JLS §14.20.2. The bytecode for the `try`'s `return 1` never reaches an `ireturn`; the
`finally`'s own `return 2` runs first, on the guaranteed-execution path, and is the value actually
returned. This is exactly why a `finally` block should never itself return or throw — doing so
silences whatever the `try` or `catch` was trying to communicate, with no compiler warning.

---

**Leaves covered:** 5.3.1–5.3.7 (7 leaves; 5.3.8 is carried by `94g-interview-atomic-concept-checklist.md`)
**Leaves deferred:** none
**Diagrams included:** D-139 (Markdown table)
**Target version:** Java 21 LTS
**Lines:** 737
