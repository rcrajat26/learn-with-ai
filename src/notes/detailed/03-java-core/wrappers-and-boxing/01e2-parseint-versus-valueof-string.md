# 03 Java Core — `parseInt` versus `valueOf(String)` — BASICS (§1.9, 1.9.15)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The deprecated wrapper constructors](01e-valueof-and-the-deprecated-constructors.md) · Next: [Parsing traps and the statics](01f-parsing-traps-and-the-statics.md)

`Integer.parseInt` and `Integer.valueOf(String)` are the two doors into `Integer` from text, and the
question "what is the difference" gets asked in interviews constantly because the honest answer is
almost embarrassingly small — and because the *interesting* material is everything the pair have in
common. They share a parser, they share an exception, and they share a set of behaviours that are
inconsistent with the neighbouring methods in the same class in three separate ways. This file is
mostly about the shared half.

---

## 1. `parseInt` returns a primitive, `valueOf(String)` returns a box, and both throw the same thing (1.9.15)

Picture one parser with two exits. Somewhere inside `Integer` there is a single loop that walks
characters, accumulates digits and range-checks the result. `parseInt` is that loop's output taken
directly: an `int`, sitting in a register. `valueOf(String)` is that same output pushed through the
boxing factory on the way out: an `Integer` reference, pointing at either a cached instance or a
freshly allocated 16-byte object. Neither exit can produce `null` — there is no "absent" in this API,
only "value" and "throw" — so the only decision the caller makes is primitive or box, and the only
thing the caller must plan for is the throw.

### Why it exists

`parseInt` is the older and more fundamental. It predates autoboxing entirely and returns the
primitive that virtually every caller actually wants. `Integer.valueOf(String)` exists because in
pre-Java-5 code, parsing a value straight into a `Vector` or a `Hashtable` was common enough to earn
its own entry point, and because the `Number` subclasses were deliberately given parallel API
surfaces — `Long.valueOf(String)`, `Double.valueOf(String)`, `Short.valueOf(String)` all exist for
symmetry rather than because each was independently needed.

`[SOURCE]` The javadoc claims equivalence modulo the return type. Verified against JDK 21.0.7
`Integer.java`, lines 962 and 988, the bodies are exactly:

```java
public static Integer valueOf(String s, int radix) throws NumberFormatException {
    return Integer.valueOf(parseInt(s,radix));
}

public static Integer valueOf(String s) throws NumberFormatException {
    return Integer.valueOf(parseInt(s, 10));
}
```

Read those two lines closely, because a lot of secondhand material paraphrases them wrong. The body
is `Integer.valueOf(parseInt(s, 10))` — radix 10 is passed **explicitly** to the two-argument
`parseInt`, not delegated to the one-argument overload. And there is no independent parsing logic
whatsoever: `valueOf(String)` is `parseInt` composed with the boxing factory. Every parsing
behaviour, every accepted input, every rejected input and every exception message in the rest of this
file therefore applies identically to both. When an interviewer asks whether they differ in *parsing*
behaviour, the answer is a flat no, and you can quote the one-line body as your evidence.

**When to reach for which.** `parseInt` unless the destination genuinely needs the box. Three
reasons, in decreasing order of how often they bite:

1. `valueOf(String)` boxes **unconditionally**. Callers overwhelmingly assign the result to an `int`
   or use it in arithmetic, which unboxes it immediately, so the object exists for one statement.
2. Once a value is boxed, `==` on it stops meaning what it looks like. Measured on JDK 21.0.7,
   `Integer.valueOf("127") == Integer.valueOf("127")` is **true** and
   `Integer.valueOf("128") == Integer.valueOf("128")` is **false**, because the first is inside the
   default cache and the second is not — see
   [`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md).
   `parseInt` cannot produce that class of bug at all.
3. A boxed result is nullable at the *variable*, which invites `Integer amount = maybeParse(raw);`
   and an unboxing NPE later, at a line with no visible method call — see
   [`01c-unboxing-null.md`](01c-unboxing-null.md).

`[NUM]` The cost, concretely. Measured, `Integer.valueOf("1200").getClass().getName()` is
`java.lang.Integer`, and 1200 is outside the default cache (`IntegerCache.high` is 127), so that call
allocates a 16-byte object. At the card deposit rate of 95k/day, a boundary that parses one amount
per request through `valueOf(String)` and immediately unboxes it produces 95,000 × 16 =
**1,520,000 bytes/day** of pure garbage for no benefit. That is nothing on its own; it is not nothing
when it is the shape of every parse in the codebase, which is the argument
[`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md) makes properly.

### The family, in one table

| Method | Returns | Radix | Prefixes honoured | Whitespace | On `null` | Allocates a box |
|---|---|---|---|---|---|---|
| `parseInt(String)` | `int` | 10, fixed | none | rejected | `NumberFormatException` | no |
| `parseInt(String, int)` | `int` | caller's, 2–36 | none | rejected | `NumberFormatException` | no |
| `parseInt(CharSequence, int, int, int)` | `int` | caller's, 2–36 | none | rejected | **`NullPointerException`** | no |
| `valueOf(String)` | `Integer` | 10, fixed | none | rejected | `NumberFormatException` | **yes, always** |
| `valueOf(String, int)` | `Integer` | caller's, 2–36 | none | rejected | `NumberFormatException` | **yes, always** |
| `decode(String)` | `Integer` | **inferred** | `0x`, `0X`, `#` → hex; leading `0` → **octal** | rejected | **`NullPointerException`** | **yes, always** |
| `parseUnsignedInt(String)` | `int` (reinterpreted) | 10, fixed | none | rejected | `NumberFormatException` | no |
| `parseUnsignedInt(String, int)` | `int` (reinterpreted) | caller's, 2–36 | none | rejected | `NumberFormatException` | no |

Two columns in that table are where all the surprises live: **prefixes** and **on `null`**. Note that
`decode` is the only row that infers a radix, and that three of the eight rows disagree with the
other five about how to report a null.

### The mechanism

All measured on JDK 21.0.7 (21.0.7+8-LTS-245).

```
Integer.parseInt("+12")           = 12
Integer.parseInt("-12")           = -12
Integer.parseInt("-2147483648")   = -2147483648
Integer.parseInt("0017")          = 17
Integer.parseInt("ff", 16)        = 255
Integer.parseInt("zz", 36)        = 1295
Integer.valueOf("-0")             = 0
Integer.valueOf("ff", 16)         = 255      .getClass().getName() = java.lang.Integer
Integer.parseInt(" 12")           -> java.lang.NumberFormatException: For input string: " 12"
Integer.parseInt("12 ")           -> java.lang.NumberFormatException: For input string: "12 "
Integer.parseInt("")              -> java.lang.NumberFormatException: For input string: ""
Integer.parseInt("1_200")         -> java.lang.NumberFormatException: For input string: "1_200"
Integer.parseInt("2147483648")    -> java.lang.NumberFormatException: For input string: "2147483648"
Integer.parseInt("12", 1)         -> java.lang.NumberFormatException: radix 1 less than Character.MIN_RADIX
```

Worth reading rather than skimming:

- **A leading sign is accepted, both of them.** `parseInt("+12")` is 12. If the field is a quantity
  that cannot be negative — a stake, a deposit, a retry count — `parseInt` will happily hand you a
  negative one and say nothing.
- **`-2147483648` parses; `2147483648` does not.** The range check is asymmetric because two's
  complement is asymmetric: `Integer.MIN_VALUE` has no positive counterpart. This is the one piece of
  validation `parseInt` genuinely performs for you, and it performs it correctly — there is no silent
  overflow here, unlike arithmetic (see
  [`../primitives-and-conversions/01a-integral-arithmetic.md`](../primitives-and-conversions/01a-integral-arithmetic.md)).
- **Leading zeros are just leading zeros.** `parseInt("0017")` is **17**. `parseInt` has no concept
  of an octal prefix. Hold that thought for the `decode` walk two subsections down, because `decode`
  disagrees.
- **Whitespace is rejected, both ends.** `parseInt(" 12")` and `parseInt("12 ")` both throw. It is
  not lenient and it never becomes lenient. `Double.parseDouble` *does* trim, which is a genuine
  inconsistency inside the same package — that one belongs to
  [`01f-parsing-traps-and-the-statics.md`](01f-parsing-traps-and-the-statics.md) and is only
  mentioned here so you do not generalise from it.

#### Underscores are a source-code feature, not a parsing feature

`parseInt("1_200")` throws. This is one of the most reliably-held wrong beliefs about the method, and
the reason is structural rather than careless: `int stakeCeiling = 1_200;` compiles, and has compiled
since Java 7. So the reader has typed `1_200` a hundred times and watched it work.

But JLS §3.10.1 permits underscores as separators inside a numeric **literal** — a construct in
source text — and `javac` strips them during lexical analysis, before a single class file byte is
written. There is no underscore left at runtime for anything to strip, and consequently **no parser
anywhere in `java.lang` knows the convention exists**. `Integer.parseInt`, `Long.parseLong`,
`Double.parseDouble`, `Integer.decode`, `new BigDecimal(String)`: none of them accept an underscore,
because none of them are looking at source code.

**Insight:** The general rule this instantiates is worth more than the specific fact. Literal syntax
and runtime parsing are two entirely separate grammars that happen to overlap on the common cases.
Hex literals (`0x1f`), binary literals (`0b1010`), underscore separators and the `L`/`f`/`d` suffixes
are all *literal* grammar. `parseInt` implements none of them. `decode` implements exactly one of
them, which is precisely why `decode` is the confusing method in the class.

#### Three methods in one class, three different answers on `null`

This is the sharpest edge in the file. Measured:

```
Integer.parseInt(null)                  -> java.lang.NumberFormatException: Cannot parse null string
Integer.valueOf((String) null)          -> java.lang.NumberFormatException: Cannot parse null string
Long.parseLong(null)                    -> java.lang.NumberFormatException: Cannot parse null string
Integer.parseInt(null, 0, 3, 10)        -> java.lang.NullPointerException
Integer.decode(null)                    -> java.lang.NullPointerException: Cannot invoke "String.isEmpty()" because "nm" is null
```

`[SOURCE]` The `NumberFormatException` is deliberate, and the reason is visible in the first nine
lines of the method — `Integer.java` lines 614–626:

```java
public static int parseInt(String s, int radix)
            throws NumberFormatException
{
    /*
     * WARNING: This method may be invoked early during VM initialization
     * before IntegerCache is initialized. Care must be taken to not use
     * the valueOf method.
     */

    if (s == null) {
        throw new NumberFormatException("Cannot parse null string");
    }
```

Two separate things in that excerpt, both worth having.

The explicit `s == null` check converts what would otherwise be an NPE from the first `s.length()`
call into a `NumberFormatException`, giving the method a single documented exception type for every
failure. That is a defensible API decision and a terrible diagnostic one, for a reason that has
nothing to do with Java: **the exception type is what every tool shows you first.** The alert subject
line, the log prefix, the exception class at the top of the stack trace, the error-tracker grouping
key — all of them say `NumberFormatException`, and none of them say `Cannot parse null string` unless
somebody reads the message. Reading "format" and reaching for input sanitising is the correct
inference from the type and the wrong inference from the cause.

The comment is a bootstrap constraint, and it closes a loop worth noticing: `parseInt` runs during VM
initialization, before `IntegerCache`'s static initializer has completed, so `parseInt` must never
call `valueOf`. Meanwhile `IntegerCache`'s own static initializer calls `parseInt` to read the
`java.lang.Integer.IntegerCache.high` property. The two are mutually recursive at class-init time,
and the comment is what keeps the recursion from closing. The full story is in
[`03a-internals-cache-configuration-and-cds.md`](03a-internals-cache-configuration-and-cds.md).

The two `NullPointerException` rows have different causes and both are accidents of implementation
rather than design. `parseInt(CharSequence, int, int, int)` — the subrange overload added in Java 9 —
opens with `Objects.requireNonNull(s)` at `Integer.java` line 705, so it throws a bare NPE with no
message. `decode` never checks at all; it calls `nm.isEmpty()` and lets the helpful-NPE machinery
(JEP 358, on by default since Java 15) produce
`Cannot invoke "String.isEmpty()" because "nm" is null`. Ironically that is the most informative of
the three messages, and it comes from the method that put the least thought into it.

The practical consequence: **you cannot catch `NumberFormatException` and conclude the input was
non-null.** Which method you called decides which exception you get, and a refactor from
`parseInt(s)` to `parseInt(s, 0, s.length(), 10)` silently changes the exception type of a null path.

#### `"017"`: three methods, three answers

```
Integer.parseInt("017")   = 17
Integer.valueOf("017")    = 17
Integer.decode("017")     = 15
Integer.decode("0017")    = 15
Long.decode("017")        = 15
```

Walk all three. `parseInt` reads `017` as decimal seventeen, because it has no prefix logic
whatsoever. `valueOf(String)` is `parseInt` plus a box, so it agrees: seventeen. `decode` inspects
the string for a radix marker and finds one — `Integer.java` line 1433:

```java
else if (nm.startsWith("0", index) && nm.length() > 1 + index) {
    index ++;
    radix = 8;
}
```

A leading `0` followed by at least one further character means octal, so `decode` parses `17` in base
8, which is fifteen. The `nm.length() > 1 + index` guard is why `decode("0")` is 0 rather than a parse
of the empty string. `decode("0017")` is also 15 — the branch consumes one zero and base 8 then eats
the rest as `017`, which is still 15.

**Pitfall:** The wrong belief is "`decode` is just a more capable `parseInt`, so use it when input
might be hex." The symptom is that zero-padded external identifiers silently decode wrong — a
fixed-width sequence number in a bank deposit file, a `RoundId` counter, a status variant rendered as
`017` — and only *some* of them, because 8 and 9 in the final position are not valid octal. Measured:

```
Integer.decode("018") -> java.lang.NumberFormatException: For input string: "18" under radix 8
Integer.decode("019") -> java.lang.NumberFormatException: For input string: "19" under radix 8
```

So values ending 0 through 7 come back quietly wrong while values ending 8 or 9 throw, producing a
scatter of failures at roughly 20% of inputs that reads exactly like bad upstream data. The fix is to
use `decode` only where a prefix is genuinely part of the contract, and `parseInt(s, 16)` on a
pre-stripped string everywhere else.

That exception message is unusually good and worth reading as a diagnostic: **`under radix 8` is the
tell.** Nobody asked for radix 8. If you see `under radix 8` in a log line and your protocol is
decimal, you have found a `decode` call and a leading zero, and you have found them in one glance.
Note also that the message quotes `"18"` and not `"018"` — the prefix has already been consumed, so
the string in the message is not the string you passed in.

`decode`'s two other measured edges, for completeness: `decode("-0x1f")` is **-31** (a sign before
the prefix is fine) while `decode("0x-1f")` throws
`java.lang.NumberFormatException: Sign character in wrong position`; and `decode(" 12")` throws
`For input string: " 12"`, so `decode` is no more lenient about whitespace than `parseInt` is.

#### `parseUnsignedInt`, and the round trip that makes it usable

```
Integer.parseUnsignedInt("4294967295")                        = -1
Integer.toUnsignedString(-1)                                  = 4294967295
Integer.parseUnsignedInt(Integer.toUnsignedString(-1))         = -1
Integer.toUnsignedLong(-1)                                    = 4294967295
Integer.parseUnsignedInt("-1")         -> java.lang.NumberFormatException: Illegal leading minus sign on unsigned string -1.
Integer.parseUnsignedInt("4294967296") -> java.lang.NumberFormatException: String value 4294967296 exceeds range of unsigned int.
```

`parseUnsignedInt` accepts the full 0 to 4,294,967,295 range and hands back the `int` whose 32 bits
are that value — so 4,294,967,295 arrives as `-1`, and every subsequent `<`, `>`, `/` and `toString`
on it is wrong unless you also use the `Integer.compareUnsigned`, `divideUnsigned` and
`toUnsignedString` family. **`parseUnsignedInt` is only half of a tool.** Its correct pairing is
`Integer.toUnsignedString` on the way out, and its correct use case is a protocol field that is
genuinely 32 unsigned bits — a wire-format sequence number, an IPv4 address as an integer — where
storing it in a `long` via `toUnsignedLong` is usually the better answer anyway. The unsigned
operations are covered in
[`../primitives-and-conversions/01b-shifts-and-unsigned.md`](../primitives-and-conversions/01b-shifts-and-unsigned.md);
one sentence is all this file needs.

Note the two exception messages are more specific than the generic `For input string:` form, and the
second one is one of very few in `java.lang` that ends with a full stop.

#### The radix asymmetry

`parseInt(String, int)`, `valueOf(String, int)` and `toString(int, int)` all nominally constrain the
radix to `Character.MIN_RADIX = 2` through `Character.MAX_RADIX = 36` (measured on 21.0.7). They do
not agree on what happens when you break that:

```
Integer.parseInt("12", 1)   -> java.lang.NumberFormatException: radix 1 less than Character.MIN_RADIX
Integer.toString(255, 1)    = 255
Integer.toString(255, 99)   = 255
```

The parse side throws. The format side **silently falls back to radix 10**. Both behaviours are
documented in their respective javadocs, so neither is a bug, but the pair is stated here as measured
fact with no invented rationale — I could not find a design discussion for the asymmetry, and it is
recorded in `## Open questions` rather than explained.

One detail on the parse-side exception: it is a `NumberFormatException`, even though the offending
argument is the radix and not the string, and the message does not mention the string at all. That is
only defensible because `NumberFormatException` **is** an `IllegalArgumentException`, which brings us
to the last mechanism.

#### `NumberFormatException` is unchecked

Verified by reflection on JDK 21.0.7:

```
NumberFormatException.class.getSuperclass()                  = java.lang.IllegalArgumentException
NumberFormatException.class.getSuperclass().getSuperclass()  = java.lang.RuntimeException
```

The full chain is `NumberFormatException` → `IllegalArgumentException` → `RuntimeException` →
`Exception` → `Throwable`. Three consequences, and the third is the one people miss.

Nothing forces you to handle it. No compiler error, no warning, and the `throws
NumberFormatException` clause on `parseInt`'s signature is pure documentation — the compiler does not
check it and cannot. That is exactly why an unguarded parse at a request boundary is the single
commonest source of a 500: the code compiles, the tests pass against well-formed fixtures, and the
first client who sends `"4.20"` into a field that wants minor units gets an unhandled
`RuntimeException` off the top of a controller.

It cannot be distinguished from other argument rejections by a broad catch. Measured, a
`catch (IllegalArgumentException e)` around `Integer.parseInt("nope")` catches it and reports
`NumberFormatException` as the concrete class. So a handler you wrote for something else — an enum
`valueOf` on a status code, a validating `Money` constructor, a `checkArgument` — will silently
swallow every parse failure in the same block and report it as whatever that handler reports.

**Insight:** Catching `NumberFormatException` specifically is not pedantry. `IllegalArgumentException`
means "some argument, somewhere in this block, was rejected"; `NumberFormatException` means "this
specific text is not a number". In the domain those map to different client-facing errors and
different operator runbooks, and a broad catch destroys the distinction at the exact moment you need
it.

**Interview:** *"What is the difference between `parseInt` and `valueOf`?"* — `parseInt` returns an
`int`, `valueOf(String)` returns an `Integer`. In JDK 21 source `valueOf(String)` is literally
`return Integer.valueOf(parseInt(s, 10));`, so the parsing behaviour and the exception are identical;
the only difference is the unconditional box on the way out, which for a value outside −128..127 is a
16-byte allocation. Both throw `NumberFormatException`, which is unchecked because it extends
`IllegalArgumentException`, and both throw it — not an NPE — on a `null` input, though `decode` and
the subrange `parseInt` overload throw NPE instead. Prefer `parseInt` unless the destination
genuinely needs the box.

### Diagram

No diagram for this concept: the mechanism is an eight-row method table and four blocks of measured
exception messages, and both of those are already the clearest available rendering. A picture of a
parser loop would add nothing the table does not say.

### A concrete example

The boundary. A stake amount arrives at `ApplicationGateway` as text on an HTTP request, in minor
units. The correct shape is a parse that **fails into a domain error carrying the offending input**,
rather than letting `NumberFormatException` propagate — and that keeps *absent* and *malformed*
distinct, because in the domain those are different client-facing errors with different runbooks.

```java
import java.util.Map;

final class IllegalTransitionException extends RuntimeException {
    IllegalTransitionException(String message) { super(message); }
}

/** Absent, malformed and valid are three outcomes, not two. */
sealed interface StakeAmount {
    record Valid(long minorUnits) implements StakeAmount {}
    record Malformed(String offendingInput, String reason) implements StakeAmount {}
    record Absent() implements StakeAmount {}
}

final class ApplicationGateway {

    /** Domain ceiling: a single stake may not exceed 100.00, i.e. 10_000 minor units. */
    private static final int MAX_STAKE_MINOR_UNITS = 10_000;

    static StakeAmount readStakeMinorUnits(Map<String, String> requestFields) {
        String raw = requestFields.get("stakeMinorUnits");
        if (raw == null || raw.isBlank()) {
            return new StakeAmount.Absent();
        }
        int parsed;
        try {
            // parseInt does not trim; strip explicitly and deliberately.
            // parseInt, not valueOf(String): the destination is a primitive field.
            parsed = Integer.parseInt(raw.strip());
        } catch (NumberFormatException e) {
            return new StakeAmount.Malformed(raw, e.getMessage());
        }
        // A successful parse is the START of validation, not the end.
        if (parsed <= 0) {
            return new StakeAmount.Malformed(raw, "stake must be positive");
        }
        if (parsed > MAX_STAKE_MINOR_UNITS) {
            return new StakeAmount.Malformed(raw, "stake exceeds 10000 minor units");
        }
        return new StakeAmount.Valid(parsed);
    }

    /** The call site. No NumberFormatException can escape this method. */
    static long reserveStake(Map<String, String> requestFields) {
        return switch (readStakeMinorUnits(requestFields)) {
            case StakeAmount.Valid v -> v.minorUnits();
            case StakeAmount.Absent ignored ->
                    throw new IllegalTransitionException("STAKE_BLOCKED: no stake amount supplied");
            case StakeAmount.Malformed m ->
                    throw new IllegalTransitionException(
                            "STAKE_BLOCKED: unparseable stake \"" + m.offendingInput()
                            + "\" (" + m.reason() + ")");
        };
    }
}
```

Run against four inputs on JDK 21.0.7, that produces exactly:

```
readStakeMinorUnits({stakeMinorUnits=" 420 "}) = Valid[minorUnits=420]
readStakeMinorUnits({stakeMinorUnits="4.20"})  = Malformed[offendingInput=4.20, reason=For input string: "4.20"]
readStakeMinorUnits({})                        = Absent[]
readStakeMinorUnits({stakeMinorUnits="1_200"}) = Malformed[offendingInput=1_200, reason=For input string: "1_200"]
```

Four deliberate choices in that code. `parseInt`, not `valueOf(String)`, because the destination is a
primitive `long` on `StakeAmount.Valid` and a box would be allocated and discarded 1,200 times a
second at peak stake-reservation rate. `raw.strip()` is explicit rather than relied upon, because
`parseInt` does not trim and I do not want the code to depend on remembering which parser does.
`Malformed` carries the **offending input verbatim**, because the entire reason this shape beats
letting the exception propagate is that a `NumberFormatException` off a controller tells the client
nothing and the operator only slightly more. And `Absent` is its own case rather than folded into
`Malformed`, because "you omitted the field" and "you sent junk" are different rejections.

`BonusIneligibleException` is the same choice on the bonus path: a coupon code that arrives as text
and fails to parse is a domain rejection with a client-facing reason, not a 500.

### The gotcha

**`parseInt` is not a validator.** It answers exactly one question — "is this string the decimal
rendering of a value in `int` range" — and gets asked to answer four more. Measured, it:

- accepts a leading `+` or `-`, so `parseInt("+12")` is 12 and a non-negative field is unprotected;
- rejects all surrounding whitespace, so `" 12"` and `"12 "` both throw;
- rejects underscores, so `"1_200"` throws even though `1_200` is a valid literal;
- rejects out-of-`int`-range values, so `"2147483648"` throws rather than overflowing — the one
  validation it does perform;
- and **silently accepts anything else that fits**, so `parseInt("999999999")` is a perfectly good
  `int` and a stake of nearly ten million pounds.

A successful parse tells you the text was a number. It tells you nothing about whether the number is
allowed, in range for the domain, correctly signed, or the right order of magnitude. Every one of
those is a guard the boundary above writes for itself, immediately after the `catch`.

`Double.parseDouble` and `Boolean.parseBoolean` have their own and considerably worse traps —
`parseDouble` trims where `parseInt` does not, and `parseBoolean` never throws at all — and both
belong to [`01f-parsing-traps-and-the-statics.md`](01f-parsing-traps-and-the-statics.md).

> **Definition.** `Integer.parseInt(String)` parses text to a primitive `int`;
> `Integer.valueOf(String)` is defined in JDK 21 source as `Integer.valueOf(parseInt(s, 10))` and so
> parses identically but boxes unconditionally, and both signal every failure — including a `null`
> input — with the unchecked `NumberFormatException`.

---

## Supporting facts

**The subrange overload.** `Integer.parseInt(CharSequence s, int beginIndex, int endIndex, int radix)`
arrived in Java 9 and parses a window of a larger `CharSequence` without allocating a substring —
useful when slicing fixed-width fields out of a bank deposit file. Measured,
`Integer.parseInt("AA-400", 3, 6, 10)` is **400**. It differs from its siblings in two ways worth
knowing: it takes `CharSequence` rather than `String`, and it throws `NullPointerException` on a null
input and `IndexOutOfBoundsException` on a bad window — measured,
`Integer.parseInt("400", 0, 9, 10)` throws
`java.lang.IndexOutOfBoundsException: Range [0, 9) out of bounds for length 3`. So it is the one
member of the family for which `catch (NumberFormatException e)` is not a complete guard.

**`valueOf(String, radix)` boxes through the same cache.** It is `Integer.valueOf(parseInt(s, radix))`,
so the result for a value in −128..127 is a shared cached instance. Measured,
`Integer.valueOf("ff", 16)` is 255 with class `java.lang.Integer`, and 255 is outside the default
cache so it allocates. Nothing about the radix changes the caching story; see
[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md).

**`Integer.toString(int)` versus `String.valueOf(int)`.** `String.valueOf(int)` delegates straight to
`Integer.toString(int)`, so they are the same call spelled differently; prefer `String.valueOf` when
the argument's static type may change under you, since it has an overload for every primitive plus
`Object`. Neither ever returns `null` and neither boxes. The one to avoid is `"" + n`, which on JDK 21
compiles to an `invokedynamic` string-concatenation call site rather than the `StringBuilder` chain
older material describes — correct, but it says "concatenate" where you meant "convert".

**`Integer.decode` has no primitive-returning twin.** Its return type is `Integer` and there is no
`decodeInt`. If you want prefix handling without the allocation you either write
`Integer.decode(s).intValue()`, which pays for the box anyway, or strip the prefix yourself and call
`parseInt(stripped, 16)`.

---

## Pitfalls

### Reading `NumberFormatException: Cannot parse null string` and chasing a format problem

**Wrong**

```java
static long readStake(Map<String, String> requestFields) {
    String raw = requestFields.get("stakeMinorUnits");
    try {
        // "It says NumberFormatException, so the client is sending junk. Sanitise harder."
        return Integer.parseInt(raw.replaceAll("[^0-9-]", "").strip());
    } catch (NumberFormatException e) {
        return 0L;      // and now an absent stake is silently a stake of zero
    }
}
```

Measured, `Integer.parseInt(null)` throws `java.lang.NumberFormatException: Cannot parse null
string`. The sanitising fix addresses nothing: if `raw` is `null` the `replaceAll` call NPEs before
`parseInt` is reached, and the `catch` does not cover NPE, so the "fix" converts a
`NumberFormatException` with an accurate message into a `NullPointerException` with none. And mapping
the failure to `0` collapses "the client omitted the field" and "the client sent garbage" into one
outcome, which in this domain are different client-facing rejections.

**Right**

```java
static StakeAmount readStake(Map<String, String> requestFields) {
    String raw = requestFields.get("stakeMinorUnits");
    if (raw == null || raw.isBlank()) {
        return new StakeAmount.Absent();          // distinct outcome, distinct client error
    }
    try {
        return new StakeAmount.Valid(Integer.parseInt(raw.strip()));
    } catch (NumberFormatException e) {
        return new StakeAmount.Malformed(raw, e.getMessage());
    }
}
```

Check for null explicitly and give it its own outcome. `NumberFormatException` then only ever means
what its name says, and the message is never the only thing standing between you and a wrong
diagnosis.

**Why people believe it:** the exception *type* is `NumberFormatException`, and the type — not the
message — is what appears in the alert subject, the log prefix, the error-tracker grouping key and
the top line of the stack trace. Reading "format" and reaching for input sanitising is the correct
inference from the type and the wrong one from the cause. The JDK chose one exception type for
`parseInt` deliberately and encoded the real cause in message text only.

### Assuming `parseInt` trims, because the parser next to it does

**Wrong**

```java
// The bank deposit file arrives space-padded to a fixed column width.
String rawAmount   = "  480";
String rawSequence = "  1200";

double amount   = Double.parseDouble(rawAmount);      // works, silently
int    sequence = Integer.parseInt(rawSequence);      // throws
```

Measured on JDK 21.0.7: `Double.parseDouble(" 1.0 ")` returns **1.0** — leading and trailing
whitespace is trimmed — while `Integer.parseInt(" 12")` throws
`java.lang.NumberFormatException: For input string: " 12"`. Two methods in the same package, on the
same shape of input, with opposite behaviour. The first line working is exactly what makes the second
line's failure look like a data problem rather than a code problem.

**Right**

```java
String rawAmount   = "  480";
String rawSequence = "  1200";

double amount   = Double.parseDouble(rawAmount.strip());
int    sequence = Integer.parseInt(rawSequence.strip());
```

Strip at the boundary, for every parser, always. The code then says what it means and does not depend
on which of the two behaviours a given method happens to have.

**Why people believe it:** `Double.parseDouble` really does trim, and it is often the parser people
meet first when reading money out of a fixed-width file. Generalising from it is a reasonable
inference from an inconsistent API. State the asymmetry as measured fact and resist constructing a
rationale for it — there is no principled reason, only history.

### Using `decode` as "the parser that handles more formats"

**Wrong**

```java
// The deposit file's sequence column is zero-padded to four characters.
// "decode handles hex too, so it is strictly more capable. Use it everywhere."
int sequence = Integer.decode("0017");     // = 15, not 17
int next     = Integer.decode("0018");     // throws
```

Measured: `Integer.decode("017")` and `Integer.decode("0017")` are both **15**, while
`Integer.decode("018")` throws
`java.lang.NumberFormatException: For input string: "18" under radix 8`. A leading `0` followed by at
least one more character selects octal — `Integer.java` line 1433. So values whose final digit is 0
through 7 come back quietly wrong and values ending 8 or 9 throw, giving roughly a 20% failure rate
scattered through data that looks upstream-corrupt.

**Right**

```java
// Decimal is the contract, so use the parser that only does decimal.
int sequence = Integer.parseInt("0017");            // = 17
int next     = Integer.parseInt("0018");            // = 18

// Where a hex prefix genuinely IS part of the wire contract, be explicit about it.
String rawMask = "0x1f";
int restrictionMask = rawMask.startsWith("0x") || rawMask.startsWith("0X")
        ? Integer.parseInt(rawMask.substring(2), 16)
        : Integer.parseInt(rawMask);
```

`parseInt` has no prefix logic at all, which is the property you want when the format is fixed. Reach
for `decode` only when an inferred radix is genuinely in the specification.

**Why people believe it:** `decode`'s javadoc reads like a superset — it accepts everything
`parseInt` accepts plus `0x`, `0X` and `#` forms — and the octal rule is one clause deep in that
list. Nothing in the method name suggests it will reinterpret a leading zero, and the two behaviours
are indistinguishable on any input without one. It also succeeds, silently and wrongly, which means
no test that only checks the happy path on unpadded values will ever catch it.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `parseInt(String)` returns | `int` |
| `valueOf(String)` returns | `Integer`, always boxed |
| `valueOf(String)` body | `return Integer.valueOf(parseInt(s, 10));` (radix passed explicitly) |
| Parsing behaviour difference | **None.** Same parser, same exception |
| Which to prefer | `parseInt`, unless the destination genuinely needs a box |
| `valueOf("1200")` allocates | Yes, 16 bytes; 1200 is outside the default cache |
| `valueOf("127") == valueOf("127")` | **true** (cached) |
| `valueOf("128") == valueOf("128")` | **false** (not cached) |
| `NumberFormatException` supertype | `IllegalArgumentException` → `RuntimeException`: **unchecked** |
| `catch (IllegalArgumentException)` | Catches NFE too — destroys the distinction |
| `parseInt(null)` | `NumberFormatException: Cannot parse null string` |
| `valueOf((String) null)` | `NumberFormatException: Cannot parse null string` |
| `parseInt(null, 0, 3, 10)` | **`NullPointerException`**, no message |
| `decode(null)` | **`NullPointerException`**: `Cannot invoke "String.isEmpty()" because "nm" is null` |
| `parseInt(" 12")` / `("12 ")` | Both throw. **No trimming, either end** |
| `parseDouble(" 1.0 ")` | 1.0 — **does** trim. Inconsistent with `parseInt` |
| `parseInt("1_200")` | Throws; underscores are JLS §3.10.1 *literal* syntax only |
| `parseInt("+12")` / `("-12")` | 12 / -12 — leading sign accepted, either sign |
| `parseInt("2147483648")` | Throws; no silent overflow |
| `parseInt("")` | Throws: `For input string: ""` |
| `parseInt("0017")` | **17** — no octal prefix logic |
| `decode("017")` / `("0017")` | **15** / **15** — leading `0` selects octal |
| `decode("018")` | Throws: `For input string: "18" under radix 8` |
| `decode("0x1f")` / `("0X1F")` / `("#1f")` | 31 / 31 / 31 |
| `decode("-0x1f")` / `("0x-1f")` | -31 / throws `Sign character in wrong position` |
| Radix bounds | `Character.MIN_RADIX = 2`, `Character.MAX_RADIX = 36` |
| Bad radix on `parseInt` | Throws `radix 1 less than Character.MIN_RADIX` |
| Bad radix on `toString(int,int)` | **Silently falls back to 10**: `toString(255, 1)` = `255` |
| `parseUnsignedInt("4294967295")` | `-1` (bit reinterpretation) |
| `parseUnsignedInt("-1")` | Throws `Illegal leading minus sign on unsigned string -1.` |
| `parseUnsignedInt("4294967296")` | Throws `String value 4294967296 exceeds range of unsigned int.` |
| Correct pairing for unsigned | `Integer.toUnsignedString`, or store in a `long` via `toUnsignedLong` |
| Subrange overload | `parseInt(CharSequence, int, int, int)`, Java 9+; no substring allocation |
| `parseInt("400", 0, 9, 10)` | `IndexOutOfBoundsException: Range [0, 9) out of bounds for length 3` |
| `parseInt` as a validator | It is not. A successful parse is where validation starts |

---

## Self-test

**Q1.** What is the difference between `Integer.parseInt("1200")` and `Integer.valueOf("1200")`?

<details><summary>Answer</summary>

The return type, and nothing else. `parseInt` returns the primitive `int` 1200; `valueOf(String)`
returns an `Integer`. In JDK 21.0.7 source, `valueOf(String)`'s entire body is
`return Integer.valueOf(parseInt(s, 10));` — note radix 10 is passed explicitly to the two-argument
`parseInt` — so it is `parseInt` composed with the boxing factory, and every parsing behaviour and
exception message is identical between them. The practical difference is that `valueOf(String)` boxes
unconditionally, and 1200 is outside the default cache range of −128..127, so that call allocates a
16-byte `Integer`. Measured, `Integer.valueOf("1200").getClass().getName()` is `java.lang.Integer`.
Since callers usually assign to an `int` or use the value in arithmetic, that object typically lives
for one statement. Prefer `parseInt` unless the destination genuinely needs the box — a
`Map<String, Integer>` value, for instance.

</details>

**Q2.** A production alert fires with `java.lang.NumberFormatException: Cannot parse null string` from
a deposit boundary. What is the bug, and why is the exception type actively misleading?

<details><summary>Answer</summary>

The input was `null`, not malformed. `Integer.parseInt(String, int)` opens with an explicit
`if (s == null) throw new NumberFormatException("Cannot parse null string");` — JDK 21.0.7
`Integer.java` around line 623 — which converts what would otherwise be an NPE from the first
`s.length()` into a `NumberFormatException`, giving the method a single documented exception type for
every failure. The type is misleading because the type, not the message, is what every tool surfaces
first: the alert subject, the log prefix, the error-tracker grouping key, the top line of the stack
trace. Reading "format" and reaching for input sanitising is the correct inference from the type and
the wrong one from the cause, and the usual "fix" — a `replaceAll` to strip non-digits — actually
makes things worse, because it NPEs before `parseInt` is reached and the existing
`catch (NumberFormatException e)` does not cover NPE. The right fix is a null check at the boundary
giving absent input its own outcome, distinct from malformed, because those are different
client-facing rejections. Worth adding: you cannot invert this rule, because `Integer.decode(null)`
and `Integer.parseInt(null, 0, 3, 10)` both throw `NullPointerException` instead.

</details>

**Q3.** `Integer.parseInt("017")`, `Integer.valueOf("017")` and `Integer.decode("017")` — what does
each return, and why?

<details><summary>Answer</summary>

17, 17 and **15**. `parseInt` has no prefix logic whatsoever, so it reads `017` as decimal seventeen.
`valueOf(String)` is `parseInt` plus a box, so it agrees. `decode` inspects the string for a radix
marker, and `Integer.java` line 1433 says a leading `0` followed by at least one further character
selects radix 8 — so `decode` parses `17` in octal, which is fifteen. The `length > 1 + index` guard
in that branch is why `decode("0")` is 0 rather than a parse of the empty string, and `decode("0017")`
is also 15. It matters because zero-padded external identifiers are extremely common — a fixed-width
sequence number in a bank deposit file, a `RoundId` counter, a status variant — and `decode`
mis-parses them inconsistently: values ending 0 through 7 come back quietly wrong while values ending
8 or 9 throw `For input string: "18" under radix 8`. Roughly 20% loud failures and 80% silent wrong
answers reads exactly like corrupt upstream data.

</details>

**Q4.** Why does `Integer.parseInt` reject `"1_200"` when `int stakeCeiling = 1_200;` compiles?

<details><summary>Answer</summary>

Because underscores in numbers are a source-code feature, not a parsing feature. JLS §3.10.1 permits
underscores as separators inside a numeric *literal*, and `javac` strips them during lexical analysis
— before any class file byte is written, and certainly before any `String` exists at runtime. There
is nothing left to strip, so no parser in `java.lang` knows the convention exists: not `parseInt`,
not `Long.parseLong`, not `Double.parseDouble`, not `Integer.decode`, not `new BigDecimal(String)`.
Measured, `Integer.parseInt("1_200")` throws
`java.lang.NumberFormatException: For input string: "1_200"`. The general rule underneath is worth
more than the fact: literal grammar and runtime parsing are two separate grammars that overlap only
on the common cases. Hex literals, binary literals, underscore separators and the `L`/`f`/`d`
suffixes are all literal grammar. `parseInt` implements none of them; `decode` implements exactly one,
which is why `decode` is the confusing method in the class.

</details>

**Q5.** Nothing forces you to handle `NumberFormatException`. Why, and what is the second-order
consequence for `catch` blocks?

<details><summary>Answer</summary>

Because it is unchecked. Verified by reflection on 21.0.7:
`NumberFormatException.class.getSuperclass()` is `java.lang.IllegalArgumentException`, whose
superclass is `java.lang.RuntimeException`. So the `throws NumberFormatException` clause on
`parseInt`'s signature is documentation only — the compiler neither enforces nor checks it, and no
warning appears if you ignore it. Code that parses untrusted input with no guard compiles cleanly and
passes every test built on well-formed fixtures, which is exactly why an unguarded parse at a request
boundary is the commonest single source of a 500. The second-order consequence is the supertype:
measured, a `catch (IllegalArgumentException e)` around `Integer.parseInt("nope")` catches it. So a
handler written for something else — an enum `valueOf` on a status code, a validating `Money`
constructor, an argument precondition — silently swallows every parse failure in the same block and
reports it as whatever that handler reports. `IllegalArgumentException` means "some argument was
rejected"; `NumberFormatException` means "this text is not a number", and in the domain those map to
different client-facing errors and different operator runbooks.

</details>

**Q6.** `Integer.parseUnsignedInt("4294967295")` returns `-1`. Is that a bug? What is the correct way
to use the method?

<details><summary>Answer</summary>

Not a bug. `parseUnsignedInt` accepts the full unsigned range 0 to 4,294,967,295 and returns the
`int` whose 32 bits encode that value — and 4,294,967,295 is all ones, which as a signed `int` is
`-1`. The method's contract is bit reinterpretation, not magnitude. The consequence is that
`parseUnsignedInt` is only half a tool: every subsequent `<`, `>`, `/` and `toString` on the result is
wrong unless you also use the unsigned family, so the correct pairing on the way out is
`Integer.toUnsignedString`, and measured, the round trip holds —
`Integer.parseUnsignedInt(Integer.toUnsignedString(-1))` is `-1` and `Integer.toUnsignedString(-1)` is
`4294967295`. For most application code the better answer is `Integer.toUnsignedLong(-1)`, which is
4,294,967,295 as a `long` you can then treat normally. It rejects what you would expect: measured,
`parseUnsignedInt("-1")` throws `Illegal leading minus sign on unsigned string -1.` and
`parseUnsignedInt("4294967296")` throws `String value 4294967296 exceeds range of unsigned int.`

</details>

**Q7.** Is `catch (NumberFormatException e)` a complete guard around every parsing method on
`Integer`?

<details><summary>Answer</summary>

No, and there are two escapes. `Integer.decode(null)` throws `NullPointerException` —
measured, `Cannot invoke "String.isEmpty()" because "nm" is null`, because `decode` calls
`nm.isEmpty()` with no prior null check and the helpful-NPE machinery from JEP 358 fills in the
message. And the Java 9 subrange overload `parseInt(CharSequence, int, int, int)` opens with
`Objects.requireNonNull(s)` at `Integer.java` line 705, so it throws a bare `NullPointerException` on
null, plus `IndexOutOfBoundsException` on a bad window — measured,
`Integer.parseInt("400", 0, 9, 10)` throws
`java.lang.IndexOutOfBoundsException: Range [0, 9) out of bounds for length 3`. So three methods in
one class give three different answers about how to report a null input, and the practical rule is
that you cannot catch `NumberFormatException` and conclude the input was non-null. It also means a
refactor from `parseInt(s)` to `parseInt(s, 0, s.length(), 10)` for the allocation saving silently
changes the exception type on the null path.

</details>

**Q8.** `Integer.parseInt("12", 1)` throws but `Integer.toString(255, 1)` does not. What happens, and
what should you conclude?

<details><summary>Answer</summary>

Measured on 21.0.7: `Integer.parseInt("12", 1)` throws
`java.lang.NumberFormatException: radix 1 less than Character.MIN_RADIX`, while
`Integer.toString(255, 1)` and `Integer.toString(255, 99)` both return the string `255` — the format
side silently falls back to radix 10. Both behaviours are documented in their respective javadocs, so
neither is a bug, but the pair is an inconsistency and I would state it as measured fact rather than
rationalise it; I could not find a design discussion for the asymmetry. Two details worth adding.
The legal range is `Character.MIN_RADIX = 2` through `Character.MAX_RADIX = 36`, measured. And the
parse-side exception is a `NumberFormatException` even though the offending argument is the radix
rather than the string, and its message does not mention the string at all — which is only defensible
because `NumberFormatException` is itself an `IllegalArgumentException`. The practical conclusion is
that a computed radix must be validated before it reaches `toString`, because `toString` will not
tell you.

</details>

---

## Open questions

- **Why `Integer.toString(int, int)` silently falls back to radix 10 while `parseInt(String, int)`
  throws on an out-of-range radix.** Both behaviours are measured on 21.0.7 and both are documented in
  their javadocs, so neither is a defect, but no design rationale for the asymmetry was located in the
  JLS, the javadoc or the JDK bug database. What would settle it: an OpenJDK bug entry or a
  `core-libs-dev` thread on the original decision. It is stated in this file as documented behaviour
  and deliberately not explained.
- **Whether the three different null behaviours across `parseInt(String)`, the subrange
  `parseInt(CharSequence, int, int, int)` and `decode(String)` were intentional.** All three are
  measured, and the mechanism for each is visible in the source (an explicit check, an
  `Objects.requireNonNull`, and no check at all respectively), but whether the subrange overload's
  divergence from the older method was a deliberate API choice or an oversight when it was added in
  Java 9 is not something the source or javadoc says. What would settle it: the JDK-9 enhancement
  request or review thread for the `CharSequence` parsing overloads.

---

**Leaves covered:** 1.9.15 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 857
