# 03 Java Core — Primitive types: the eight kinds — BASICS (§1.3, 1.3.1–1.3.4, 1.3.17–1.3.19)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Observability toolkit](../language-substrate/05-internals-observability.md) · Next: [Two's complement, overflow and integer division](01a-integral-arithmetic.md)

---

## 1. The primitive set, and what the JVM actually carries (1.3.1, 1.3.2, 1.3.19)

**Concept.** A primitive is a fixed-width bit pattern with an agreed interpretation, stored where you put it — in a local slot, in a field, in an array cell — with no header, no identity, no null. When `FundsLedger` holds `long ledgerEntryId`, the 64 bits *are* the entry id. There is no arrow to follow. That is the whole reason primitives exist: at 2.8M stake reservations a day, a `long` counter costs 8 bytes and one `ladd`, while a `Long` counter costs an object header, a pointer, and a cache miss.

The language has eight. The JVM has a slightly different set, and the mismatch is where the surprising behaviour comes from.

**Why it exists.** Java's 1996 design goal was "the same arithmetic answer on every machine". C left `int` width, signedness of `char`, and the direction of integer division to the implementation; a payout file parsed on SPARC and on x86 could disagree. Java fixed every width and every rounding rule in the specification, and paid for it by refusing to give you unsigned types at all (§5 of [Integral arithmetic, shifts and the unsigned story](01a-integral-arithmetic.md)) and by making `int` 32 bits forever, even on 64-bit hardware.

**How it works.** JVMS 21 §2.2 lists the Java Virtual Machine's primitive types as the *numeric types*, the *`boolean` type*, and the *`returnAddress` type*. Two of those three are not language types:

- **`returnAddress`** is a pointer to a bytecode opcode. It is the operand type of `jsr`/`jsr_w` and `ret`, the old subroutine instructions that `javac` used to emit for `finally` blocks. JVMS 21 §2.3.3 states it "is not associated with any Java programming language type", and there is no way to declare, print or store one from source. Class files at major version 50 (Java 6) and above are verified by type-checking with a `StackMapTable`, and `jsr`/`ret` are rejected outright there — so on Java 21 you will only meet `returnAddress` reading very old class files. `javac` has inlined `finally` bodies instead since 1.4.2.
- **`boolean` has no dedicated instructions.** JVMS 21 §2.3.4: "the Java Virtual Machine does have limited support for `boolean`", and that "`boolean` values are compiled to use values of the Java Virtual Machine `int` data type." So `boolean stakeBlocked = true` becomes `iconst_1; istore_1`. There is no `bload`, no `bstore`, no `band`. Arrays are the one exception and get their own encoding — see §4 below.

[NUM] So: eight language primitives, ten JVM value kinds if you count `returnAddress` and reference separately, and exactly **four** bytecode arithmetic families — `i` (int), `l` (long), `f` (float), `d` (double). `byte`, `short`, `char` and `boolean` have **no** arithmetic instructions at all; every operation on them runs at `int` width and is truncated back on store. That single fact generates leaves 1.3.12 and 1.3.21, worked in [Integral arithmetic, shifts and the unsigned story](01a-integral-arithmetic.md).

| Type | Bits | Min | Max | Field default | Local gets a default? | QuizStakes use |
|---|---|---|---|---|---|---|
| `byte` | 8 | -128 | 127 | `0` | no | wire format only — one byte of the banking partner's payout file |
| `short` | 16 | -32768 | 32767 | `0` | no | wire format only — a 2-byte record-type tag in the same file |
| `char` | 16 (unsigned) | `'\u0000'` (0) | `'\uffff'` (65535) | `'\u0000'` | no | **never** for money; UTF-16 code units in a client's name |
| `int` | 32 | -2147483648 | 2147483647 | `0` | no | `Reservation.retryCount`, capped at 3; loop counters; restriction bit masks |
| `long` | 64 | -9223372036854775808 | 9223372036854775807 | `0L` | no | `ledgerEntryId`; epoch-milli timestamps; minor-unit money accumulators |
| `float` | 32 | ±1.4E-45 (min positive) | ±3.4028235E38 | `0.0f` | no | none. Never a balance, never a stake |
| `double` | 64 | ±4.9E-324 (min positive) | ±1.7976931348623157E308 | `0.0d` | no | none for money; fine for a p99 latency histogram |
| `boolean` | unspecified by JVMS | `false` | `true` | `false` | no | `Restriction.active` flags |

**D-006** — Read the "Local gets a default?" column first: it is "no" on every single row, which is the one column people get wrong. Then read the `long` row against the `int` row — that 2.147-billion max is the number that decides `ledgerEntryId`'s type in §2 of [Integral arithmetic, shifts and the unsigned story](01a-integral-arithmetic.md).

**Insight:** `char`'s row is the only unsigned one in the table, and that asymmetry is not a rounding of the design — it is the *only* unsigned integer arithmetic Java has. `char` is a 16-bit unsigned integer that happens to print as a glyph.

```java
final class PrimitiveWidths {

    // Field defaults: never written, still well-defined.
    private byte  wireByte;
    private short recordTag;
    private char  initial;
    private int   retryCount;
    private long  ledgerEntryId;
    private float unusedFloat;
    private double unusedDouble;
    private boolean stakeBlocked;

    void report() {
        System.out.println("wireByte      = " + wireByte);
        System.out.println("recordTag     = " + recordTag);
        System.out.println("initial       = " + (int) initial + " (as int)");
        System.out.println("retryCount    = " + retryCount);
        System.out.println("ledgerEntryId = " + ledgerEntryId);
        System.out.println("unusedFloat   = " + unusedFloat);
        System.out.println("unusedDouble  = " + unusedDouble);
        System.out.println("stakeBlocked  = " + stakeBlocked);
    }

    public static void main(String[] args) {
        new PrimitiveWidths().report();

        System.out.println("int  bits = " + Integer.SIZE  + ", bytes = " + Integer.BYTES);
        System.out.println("long bits = " + Long.SIZE     + ", bytes = " + Long.BYTES);
        System.out.println("char bits = " + Character.SIZE);
        System.out.println("char max  = " + (int) Character.MAX_VALUE);
        System.out.println("float  min positive = " + Float.MIN_VALUE);
        System.out.println("double min positive = " + Double.MIN_VALUE);
    }
}
```

Output:

```
wireByte      = 0
recordTag     = 0
initial       = 0 (as int)
retryCount    = 0
ledgerEntryId = 0
unusedFloat   = 0.0
unusedDouble  = 0.0
stakeBlocked  = false
int  bits = 32, bytes = 4
long bits = 64, bytes = 8
char bits = 16
char max  = 65535
float  min positive = 1.4E-45
double min positive = 4.9E-324
```

**Gotcha.** `Integer.SIZE` is 32 and `Boolean` has no `SIZE` constant at all — because there is no answer. Any code that computes a memory footprint by summing `SIZE` constants is guessing about `boolean` and about padding.

### Choosing one (1.3.19)

**Insight:** the choice is not "how big can the value get" — it is "how big can the *accumulator* get, and does the field cross a wire".

| Situation in QuizStakes | Type | Reason |
|---|---|---|
| `retryCount` on a `Reservation`, capped at 3 | `int` | fits in `byte`, but `int` is the arithmetic width anyway; a narrower field saves nothing outside arrays |
| `ledgerEntryId` | `long` | see the arithmetic in §2 of [Integral arithmetic](01a-integral-arithmetic.md) — `int` runs out in about 108 days |
| Epoch-milli timestamp on a `Movement` | `long` | milliseconds since 1970 passed 2^31 ms in 1970 + 25 days |
| Money | `long` of minor units, or `BigDecimal` | never `double`; see [Floating point: IEEE 754, NaN and negative zero](01c-floating-point.md) |
| One byte of the payout file | `byte` | the format says one byte; see §5 of [Integral arithmetic](01a-integral-arithmetic.md) |
| A `boolean[]` of 10 restriction flags | `int` bit mask | 10 booleans in a `boolean[]` is 10 bytes plus a 16-byte header; a mask is 4 bytes and supports set algebra — §4 of [Integral arithmetic](01a-integral-arithmetic.md) |
| A 40-million-element numeric column | `int[]` / `short[]` | in arrays, narrowing is real: `short[]` is genuinely half of `int[]` |

Outside arrays, a `byte` field does not reliably save memory: HotSpot packs fields but pads the object to `ObjectAlignmentInBytes = 8`, so shrinking one field often buys padding instead of space. Field layout, padding and `@Contended` are worked through in **06 JVM internals**.

> A primitive type is one of the eight built-in value types whose width and arithmetic are fixed by the specification, stored inline with no object header and no `null`.

---

## 2. Field defaults versus locals, and definite assignment (1.3.3)

**Concept.** Two different mechanisms are commonly mistaken for one. Fields are *zeroed by the memory system* — the JVM hands out pre-cleared memory, so a field is readable before you assign it. Locals are *checked by the compiler* — the frame's slot is uninitialised garbage as far as the language is concerned, so `javac` refuses to let you read it.

**Why it exists.** Zeroing fields is a safety guarantee: a freshly allocated `Account` cannot expose whatever a previous, garbage-collected `Reservation` left in that memory. Zeroing locals too would mean writing zeros to every stack slot on every method entry — 2.8M times a day per settlement path — for no safety benefit, since the compiler can prove a local is written before it is read. So the language pays with a compile error instead of a runtime cost.

**How it works.** JLS 21 §4.12.5 gives the default values: `0` for `byte`/`short`/`int`, `0L`, `0.0f`, `0.0d`, `'\u0000'` for `char`, `false` for `boolean`, `null` for every reference type. These apply to instance fields, static fields, and *array components* — including array components you never touch. Locals are governed by JLS 21 §16, "definite assignment": every read must be preceded, on every path, by a write.

[TRAP] The `char` default is the code unit zero. Written as source text it is the six characters `'\u0000'` — a NUL. Printing it with `System.out.println(c)` emits a zero byte to your terminal and looks like nothing happened; `(int) c` prints `0`, which is what you want in a log line.

```java
final class DefaultsAndDefiniteAssignment {

    static final class ReservationSlot {
        int retryCount;          // 0
        long ledgerEntryId;      // 0L
        char statusInitial;      // '\u0000'
        boolean voided;          // false
        String idempotencyKey;   // null
    }

    static int retriesRemaining(int retryCount) {
        int remaining;                      // no default, not readable yet
        if (retryCount < 3) {
            remaining = 3 - retryCount;
        } else {
            remaining = 0;
        }
        return remaining;                   // definitely assigned on both paths
    }

    public static void main(String[] args) {
        var slot = new ReservationSlot();
        System.out.println("retryCount      = " + slot.retryCount);
        System.out.println("statusInitial   = " + (int) slot.statusInitial);
        System.out.println("idempotencyKey  = " + slot.idempotencyKey);

        // Array components get defaults too, including the ones never written.
        int[] retriesByShard = new int[4];
        retriesByShard[0] = 3;
        System.out.println("shard 3 retries = " + retriesByShard[3]);   // 0

        System.out.println("remaining(1) = " + retriesRemaining(1));
        System.out.println("remaining(9) = " + retriesRemaining(9));
    }
}
```

Output:

```
retryCount      = 0
statusInitial   = 0
idempotencyKey  = null
shard 3 retries = 0
remaining(1) = 2
remaining(9) = 0
```

**Pitfall:** believing a local `int` starts at zero. The symptom is not a wrong answer, it is a compile error people misread as a compiler bug — `variable remaining might not have been initialized` on a method where the human eye can see every branch assigns it. Definite assignment is a *conservative flow analysis*, not a proof engine: `if (x > 0) r = 1; if (x <= 0) r = 0; return r;` fails, because the rules in JLS §16 do not relate the two conditions. The fix is to make the assignment structurally total — `if/else`, a `switch` with a `default`, or an initialiser at the declaration.

**Interview:** "What is the default value of a local variable?" — There isn't one; reading an unassigned local is a compile error under definite assignment, while fields and array components are zeroed by the JVM.

> Fields and array components are initialised to a type-specific zero value by the JVM; locals have no default and must be definitely assigned on every path before any read.

---

## 3. `char` is a code unit, not a character (1.3.4)

**Concept.** A `char` is 16 unsigned bits. Unicode has 1,114,112 code points. The arithmetic does not work, and Java resolved it in 1996 by choosing UTF-16: a `char` holds one *code unit*, and code points above `\uffff` occupy two of them — a high surrogate in `\ud800`–`\udbff` followed by a low surrogate in `\udc00`–`\udfff`.

**Why it exists.** Java 1.0 shipped when Unicode was a 16-bit standard and `char` genuinely was a character. Unicode 2.0 (1996) introduced supplementary planes; changing `char` to 32 bits would have broken every `String`, so Java kept the 16-bit code unit and moved *code point* handling into API methods (`String.codePointAt`, `Character.isSurrogatePair`, `String.codePoints()`).

**How it works.** `"€".length()` is 1. `"𝄞".length()` is 2, because U+1D11E encodes as the surrogate pair `𝄞`. `charAt(0)` on that string returns a lone high surrogate, which is not a character in any script.

[TRAP] **Pitfall:** treating `s.length()` as a character count when validating a client's name in `PersonalDetails`. Symptom: a name containing an emoji or a supplementary-plane script passes a 2-char minimum with one visible character, or fails a 35-char maximum at 20 visible characters — and reversing the string by `charAt` swaps the surrogates and produces mojibake. The fix is `s.codePointCount(0, s.length())` for counting, and `s.codePoints()` for iterating; for user-visible units you need grapheme clusters, which needs `java.text.BreakIterator`.

```java
final class ClientNameUnits {
    public static void main(String[] args) {
        String name = "Zoé 𝄞";     // "Zoé " plus U+1D11E

        System.out.println("length()        = " + name.length());
        System.out.println("codePointCount  = " + name.codePointCount(0, name.length()));
        System.out.println("charAt(5) high? = " + Character.isHighSurrogate(name.charAt(5)));

        char c = name.charAt(5);
        System.out.println("charAt(5) as int = " + (int) c);   // 55348 = 0xD834

        name.codePoints().forEach(cp ->
            System.out.printf("U+%04X isSupplementary=%b%n",
                cp, Character.isSupplementaryCodePoint(cp)));

        char digit = '7';
        System.out.println("'7' - '0'       = " + (digit - '0'));  // unsigned char arithmetic
    }
}
```

Output:

```
length()        = 6
codePointCount  = 5
charAt(5) high? = true
charAt(5) as int = 55348
U+005A isSupplementary=false
U+006F isSupplementary=false
U+00E9 isSupplementary=false
U+0020 isSupplementary=false
U+01D11E isSupplementary=true
'7' - '0'       = 7
```

**Insight:** `digit - '0'` returning `7` is the unsigned-16-bit arithmetic showing through — both operands are promoted to `int`, and because `char` widens by *zero*-extension rather than sign-extension, a `char` never becomes negative on promotion. It is the only primitive with that property.

Code unit versus code point versus grapheme cluster, and where encoding actually happens, are the subject of **02 Java collections**' string sections and of the strings guide in this same topic.

> A `char` is an unsigned 16-bit UTF-16 code unit; a Unicode code point is one code unit in the Basic Multilingual Plane and a surrogate pair of two code units above it.

---

## 4. `boolean` has no defined width (1.3.17)

**Mechanism.** [NUM] JVMS 21 §2.3.4 gives `boolean` no size and no arithmetic instructions; `boolean` locals, fields and expressions are all carried as `int` with `0` for `false` and `1` for `true`, so a `boolean` local occupies one 4-byte frame slot. Arrays are the exception: JVMS 21 §2.3.4 states that "arrays of type `boolean` are accessed and modified using the `byte` array instructions", and `newarray` with `T_BOOLEAN` allocates one byte per component. So a `boolean[10]` of restriction flags is 10 bytes of payload. A `boolean` *field* is laid out as one byte by HotSpot's field layout, after which the whole object is padded to `ObjectAlignmentInBytes = 8` — so ten `boolean` fields in a `Restriction` may cost the same as one, and may not, depending on what else is in the object. That is why the bit mask in §4 of [Integral arithmetic, shifts and the unsigned story](01a-integral-arithmetic.md) wins on 10 flags: 4 bytes, no layout guesswork, and set operations for free.

**[RESEARCH] note:** the one-byte-per-`boolean`-field figure is HotSpot field-layout behaviour, not a specification guarantee — the JVMS deliberately declines to give `boolean` a width, and another JVM may choose differently. Measure with JOL rather than assume. Object layout and the padding rules are worked in **06 JVM internals**.

**Gotcha.** Because `boolean[]` is byte-backed but `boolean` fields are int-carried in bytecode, `boolean[] a; a[0] = true;` compiles to `iconst_1; bastore` — a `byte` store instruction writing a `boolean` array. `Arrays.fill(boolean[], boolean)` therefore fills bytes, and a corrupted `boolean` byte (only reachable via `Unsafe`) can produce a value that is neither `true` nor `false` in an `if`.

> `boolean` has no width in the JVM specification: it is carried as `int` in bytecode, stored one byte per component in arrays, and laid out as one byte per field by HotSpot before object alignment padding.

---

## 5. `void` and `Void` (1.3.18)

**Mechanism.** `void` is a keyword in the method-return-type position and nothing else. You cannot declare a `void` variable, parameter, field or array; JLS 21 §8.4.5 allows it only as a `Result`. `java.lang.Void` is a real class with a `private` constructor and exactly one member, the `public static final Class<Void> TYPE` field, which holds `void.class`. It exists so generics can express "no result": `Future<Void>`, `Callable<Void>`, `CompletableFuture<Void>`.

```java
final class VoidPlaceholder {

    /** A stake settlement that produces no value, only a side effect on the ledger. */
    static java.util.concurrent.Callable<Void> settle(String roundId) {
        return () -> {
            System.out.println("SettleStake for " + roundId);
            return null;                        // the only legal Void value
        };
    }

    public static void main(String[] args) throws Exception {
        Void result = settle("round-42").call();
        System.out.println("result       = " + result);
        System.out.println("Void.TYPE    = " + Void.TYPE);
        System.out.println("void.class   = " + void.class);
        System.out.println("same?        = " + (Void.TYPE == void.class));
        System.out.println("constructors = " + Void.class.getDeclaredConstructors().length);
    }
}
```

Output:

```
SettleStake for round-42
result       = null
Void.TYPE    = void
void.class   = void
same?        = true
constructors = 1
```

**Gotcha.** The only legal value of type `Void` is `null`, so a `Callable<Void>` must `return null` — there is no `Void.INSTANCE`. Prefer `Runnable` or `CompletableFuture<Void>` over `Callable<Void>` when you control the interface; use `Void` only when a generic signature forces a type argument. Note `getDeclaredConstructors().length` is `1`: the private one is declared and reflectively visible, just not callable.

> `void` is a keyword usable only as a method result type; `java.lang.Void` is an uninstantiable class whose only value is `null`, existing so generic signatures can name "no result".

---

## Pitfalls

### "A local `int` starts at zero, like a field does"

**Wrong**

```java
static int retriesRemaining(int retryCount) {
    int remaining;
    if (retryCount > 0) remaining = 3 - retryCount;
    if (retryCount <= 0) remaining = 3;
    return remaining;
}
// error: variable remaining might not have been initialized
```

Every human-visible path assigns `remaining`, and it still will not compile.

**Right**

```java
static int retriesRemaining(int retryCount) {
    int remaining = retryCount > 0 ? 3 - retryCount : 3;
    return remaining;
}
// or an if/else, or a switch with a default
```

Definite assignment (JLS 21 §16) is a conservative flow analysis that does not relate two independent `if` conditions. Making the assignment structurally total — one expression, or `if/else` — satisfies it. Fields, by contrast, really are zeroed by the JVM (JLS §4.12.5), which is where the wrong belief comes from.

**Why people believe it:** because fields, static fields and array components genuinely *are* zero-initialised, and most people meet a field before they meet a local flow error.

### "`s.length()` is the number of characters in a client's name"

**Wrong**

```java
static boolean nameLengthOk(String name) {
    return name.length() >= 2 && name.length() <= 35;
}
// nameLengthOk("𝄞")  -> true, one visible character passes a 2-char minimum
```

**Right**

```java
static boolean nameLengthOk(String name) {
    int codePoints = name.codePointCount(0, name.length());
    return codePoints >= 2 && codePoints <= 35;
}
// nameLengthOk("𝄞")  -> false, one code point fails the minimum
```

`String.length()` returns the number of UTF-16 *code units*, and every code point above `\uffff` occupies two of them. A supplementary-plane name therefore counts double against a maximum and half against a minimum. `codePointCount` counts code points; for user-visible units you need grapheme clusters and `java.text.BreakIterator`.

**Why people believe it:** `length()` is named as if it returned a character count, and it did return one in Java 1.0, when Unicode was a 16-bit standard and `char` genuinely was a character.

### "A `boolean` costs one bit, so ten `boolean` fields are cheaper than an `int` mask"

**Wrong**

```java
static final class RestrictionFlags {
    boolean depositBlocked;
    boolean stakeBlocked;
    boolean withdrawalBlocked;
    boolean depositLimited;
    boolean withdrawalHeld;
    boolean sourceOfFundsRequired;
    boolean allBlocked;
    boolean selfExcluded;
    boolean coolingOff;
    boolean dormantFrozen;

    boolean blocksStaking() {
        return stakeBlocked || allBlocked || selfExcluded;
    }
}
```

**Right**

```java
static final class RestrictionMaskHolder {
    private final int mask;

    RestrictionMaskHolder(int mask) {
        this.mask = mask;
    }

    boolean blocksStaking() {
        int blocking = (1 << 1) | (1 << 6) | (1 << 7);   // STAKE_BLOCKED, ALL_BLOCKED, SELF_EXCLUDED
        return (mask & blocking) != 0;
    }
}
```

JVMS 21 §2.3.4 gives `boolean` no width at all. HotSpot lays out a `boolean` field as one byte, so ten of them are ten bytes before the object is padded up to `ObjectAlignmentInBytes = 8` — and there is no `Boolean.SIZE` constant precisely because the specification declines to answer. The `int` mask is four bytes on every JVM and gives union, intersection and "any of" in one instruction each.

**Why people believe it:** `boolean` holds one bit of information, and the C `_Bool`-with-bitfields idiom really does pack. Java has no bitfields, and the JVM has no `boolean` instructions.

### "`Void` must have an instance, since it is a class"

**Wrong**

```java
java.util.concurrent.Callable<Void> settle = () -> {
    System.out.println("SettleStake for round-42");
    return Void.TYPE;                 // does not compile: Class<Void> is not Void
};
```

**Right**

```java
java.util.concurrent.Callable<Void> settle = () -> {
    System.out.println("SettleStake for round-42");
    return null;                      // the only legal Void value
};
```

`java.lang.Void` has one `private` constructor and no factory, so `null` is its only value. `Void.TYPE` is a `Class<Void>`, not a `Void` — it is the reflective handle for `void.class`. When you own the interface, `Runnable` or `CompletableFuture<Void>` says "no result" without the placeholder.

**Why people believe it:** every other wrapper class — `Integer`, `Boolean`, `Character` — has values and a `valueOf`, so `Void` looks like it should have exactly one.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Widths (bits) | `byte` 8, `short` 16, `char` 16 unsigned, `int` 32, `long` 64, `float` 32, `double` 64, `boolean` unspecified |
| `Integer.MIN_VALUE` / `MAX_VALUE` | -2147483648 / 2147483647 |
| `Long.MIN_VALUE` / `MAX_VALUE` | -9223372036854775808 / 9223372036854775807 |
| `char` range | 0 to 65535, default `'\u0000'`, the only unsigned integer type |
| Field defaults | `0`, `0L`, `0.0f`, `0.0d`, `'\u0000'`, `false`, `null` |
| Array component defaults | same as fields, including components never written |
| Local defaults | none — definite assignment, compile error on read |
| `Integer.SIZE` / `Integer.BYTES` | 32 / 4; there is no `Boolean.SIZE` |
| JVM value kinds | numeric, `boolean`, `returnAddress`, reference — `returnAddress` is not a language type |
| Bytecode arithmetic families | four: `i`, `l`, `f`, `d`. `byte`/`short`/`char`/`boolean` have none |
| `boolean` storage | `int` in bytecode; 1 byte per array component; 1 byte per field in HotSpot |
| `s.length()` vs code points | code units, not characters; use `codePointCount(0, length())` |
| Surrogate ranges | high `\ud800`–`\udbff`, low `\udc00`–`\udfff` |
| `'7' - '0'` | `7` — `char` widens by zero-extension, never goes negative |
| `void` | keyword, method result type only; no `void` variable, parameter, field or array |
| `Void` | uninstantiable, only value `null`, holds `Void.TYPE == void.class` |
| Type choice | `int` default; `long` for ids/timestamps/accumulators; `byte`/`short` in arrays and wire formats; never `float` |
| Field narrowing | unreliable — object padded to `ObjectAlignmentInBytes = 8`; array narrowing is real |

---

## Self-test

**Q1.** Why can a `byte` field not be counted on to save memory, while a `short[]` reliably does?

<details><summary>Answer</summary>

In arrays, the component width is real: `newarray` with `T_SHORT` allocates 2 bytes per element, so a 40-million-element `short[]` is about 80 MB against 160 MB for an `int[]`, and the array header is paid once. In an object's fields, HotSpot packs fields by size to minimise gaps but then pads the whole object up to `ObjectAlignmentInBytes = 8` (confirmed default on Oracle JDK 21). Shrinking one `int` field to a `byte` frees 3 bytes that very often go straight into that padding, so the object footprint does not change at all. On top of that, `byte`/`short`/`char`/`boolean` have no arithmetic instructions — every operation promotes to `int` and truncates on store — so a narrow field costs you correctness risk (sign extension, worked in §4 and §5 of [Integral arithmetic, shifts and the unsigned story](01a-integral-arithmetic.md)) for a memory saving that may be zero. The rule from leaf 1.3.19 follows: narrow types belong in arrays and wire formats, `int` elsewhere. Field layout and padding are worked in detail in **06 JVM internals**.

</details>

**Q2.** What is `returnAddress`, and can you observe it on Java 21?

<details><summary>Answer</summary>

`returnAddress` is one of the JVM's primitive types (JVMS 21 §2.2, §2.3.3): a pointer to a bytecode opcode, used as the operand type of the `jsr`, `jsr_w` and `ret` instructions. The spec states explicitly that it "is not associated with any Java programming language type", so there is no way to declare, assign or print one from source — it exists only on the operand stack and in local variable slots inside a class file. `javac` used to emit `jsr`/`ret` to share a single copy of a `finally` block between the normal and exceptional paths; it stopped doing so in 1.4.2 and inlines the `finally` body instead. Class files at major version 50 (Java 6) or above are verified by the type-checking verifier with a `StackMapTable`, which rejects `jsr`/`ret` outright. So on Java 21 you can only encounter `returnAddress` by reading a class file compiled for an older target, and never from Java source. It is worth knowing because it is the answer to "name a JVM type that is not a Java type" — the other being `boolean`, which has no instructions of its own and is carried as `int`.

</details>

**Q3.** `BonusService` stores an expiry as `int epochSeconds` to save 4 bytes per row across 3.1k grants a day. Assess.

<details><summary>Answer</summary>

Two problems, one certain and one arithmetic. The certain one: 3.1k rows a day is about 1.1M a year, so the saving is roughly 4.5 MB a year — nothing, and it will be swallowed by row overhead in a table whose entries average ~180 bytes anyway. The arithmetic one: `int` epoch seconds overflow at 2,147,483,647 seconds after 1970-01-01, which is 2038-01-19T03:14:07Z. A bonus granted with 30-day expiry is safe for now, but the same field will be copy-pasted into a retention timestamp or a 7-year archive date, and 2038 is inside a 7-year retention window computed from any date after January 2031. Use `long` epoch millis, or better an `Instant`, and let the column be `TIMESTAMP`. This is exactly leaf 1.3.19's rule: `long` for timestamps, unconditionally, because the width question is about the range of the *arithmetic* and not the range of today's values.

</details>

**Q4.** Explain the two different mechanisms behind "a field is zero" and "a local has no default", and why Java chose two rather than one.

<details><summary>Answer</summary>

They are unrelated mechanisms that happen to be described with the same word. Fields — instance, static and array components — are zeroed by the *memory system*: the JVM hands out pre-cleared memory, and JLS 21 §4.12.5 fixes the value per type (`0`, `0L`, `0.0f`, `0.0d`, `'\u0000'`, `false`, `null`). That is a safety guarantee, not a convenience: a freshly allocated `Reservation` must not be able to read whatever a garbage-collected object left in that memory, so the zeroing is mandatory and cannot be skipped. Locals are handled by the *compiler* instead, under JLS 21 §16 definite assignment: `javac` proves that every read is preceded on every path by a write, and rejects the program otherwise. Nothing zeroes the frame slot. The reason for the split is cost: zeroing every stack slot on every method entry would run 2.8M times a day per settlement path and buy no safety, because the compiler can already prove the local is written first. So the language pays a compile error rather than a runtime cost. The practical consequence is that definite assignment is conservative — `if (x > 0) r = 1; if (x <= 0) r = 0; return r;` is rejected even though a human can see it is total, because §16 does not relate two independent conditions.

</details>

**Q5.** A client's name is stored as a `String`. Reversing it with a `charAt` loop produces mojibake for some clients but not others. Explain, and give the correct reversal.

<details><summary>Answer</summary>

`char` is a 16-bit UTF-16 *code unit*, not a character. Code points above `\uffff` — emoji, supplementary-plane scripts, musical symbols such as U+1D11E — are encoded as a surrogate *pair*: a high surrogate in `\ud800`–`\udbff` followed by a low surrogate in `\udc00`–`\udfff`. A `charAt` loop that walks indices backwards emits the low surrogate before the high one, which is not a valid UTF-16 sequence, so the terminal or the browser renders a replacement glyph. Names in the Basic Multilingual Plane — which is most Latin, Cyrillic and CJK text — survive, which is why the bug is intermittent and passes review. The correct reversal is `new StringBuilder(name).reverse()`, which is specified to keep surrogate pairs together, or iterate `name.codePoints()` and rebuild. Even that is not the end of it: combining marks and emoji ZWJ sequences make a code point smaller than a user-visible character, so a genuinely user-facing reversal needs grapheme clusters via `java.text.BreakIterator.getCharacterInstance()`.

</details>

**Q6.** Why does `Callable<Void>` force a `return null`, and what should you use instead when you own the interface?

<details><summary>Answer</summary>

`void` is a keyword, allowed by JLS 21 §8.4.5 only in the method result position — you cannot write `void x;`, a `void` parameter, a `void` field or a `void[]`. So `void` cannot be a type argument, and a generic signature that must name "no result" needs a real class. `java.lang.Void` is that class: it has a single `private` constructor, no factory, and exactly one member, `public static final Class<Void> TYPE`, which holds `void.class`. With no way to construct it, the only value of type `Void` is `null`, so a `Callable<Void>` body must `return null`; there is no `Void.INSTANCE`, and `Void.TYPE` will not compile in that position because its type is `Class<Void>`, not `Void`. Note `Void.class.getDeclaredConstructors().length` is `1` — the private constructor is declared and reflectively visible, just not callable. When you control the interface, use `Runnable` (which is `void run()`) or `CompletableFuture<Void>`, both of which express the same thing without the placeholder return; reserve `Void` for the cases where an existing generic signature forces a type argument on you.

</details>

---

## Open questions

- The claim that a `boolean` **field** occupies one byte in HotSpot's field layout is observed behaviour of HotSpot's `FieldLayoutBuilder`, not a JVMS guarantee (JVMS 21 §2.3.4 deliberately assigns `boolean` no width). Settled definitively only by a JOL `ClassLayout` dump on the target JVM, or by reading `hotspot/share/classfile/fieldLayoutBuilder.cpp`; treat the figure as HotSpot-specific.
- Whether `javac` 1.4.2 is the exact release that stopped emitting `jsr`/`ret` for `finally` is from the commonly cited history rather than a release note quoted here. The verifier consequence (rejected at class-file major version 50 and above) is specified in JVMS 21 §4.9.1 and §4.10.1 and is not in doubt.

---

**Leaves covered:** 1.3.1, 1.3.2, 1.3.3, 1.3.4, 1.3.17, 1.3.18, 1.3.19 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** D-006
**Target version:** Java 21 LTS
**Lines:** 508
