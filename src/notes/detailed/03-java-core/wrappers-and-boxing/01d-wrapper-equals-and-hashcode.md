# 03 Java Core — Wrapper `equals` and `hashCode` — BASICS (§1.9, 1.9.11, 1.9.18)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Unboxing null](01c-unboxing-null.md) · Next: [`valueOf` and the deprecated constructors](01e-valueof-and-the-deprecated-constructors.md)

The previous file showed a wrapper turning into a primitive without your permission. This one shows
the opposite failure: two wrappers holding the same number and refusing to admit it. Two things are
on the table. First, `equals` between two different wrapper types is *always* false, and the compiler
will not warn you — a bug class that never throws, never logs, and shows up as a missing ledger row.
Second, the eight wrappers use four genuinely different `hashCode` algorithms, and knowing which is
which is the difference between explaining a hash collision and guessing at one.

The `equals`/`hashCode` contracts themselves are owned by
[`../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`](../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md);
this file uses them as premises rather than re-deriving them.

---

## 1. `equals` across wrapper types is always false (1.9.11)

`[TRAP]` Picture the eight wrappers not as a numeric family but as eight unrelated final classes
that happen to have similar `toString` output. `Integer` and `Long` are siblings in the same way
`String` and `LedgerEntry` are siblings: both are classes, both extend something, and that is the
end of the relationship. Every wrapper's `equals` opens with an `instanceof` test against *its own*
type, so the first thing a `Long` asks about the object handed to it is "are you a `Long`", and an
`Integer` fails that question before the numbers are ever looked at.

Measured on JDK 21.0.7:

```
Integer.valueOf(1).equals(Long.valueOf(1))          -> false
Long.valueOf(1).equals(Integer.valueOf(1))          -> false
Integer.valueOf(1).equals(Short.valueOf((short)1))  -> false
```

Both directions are false, which is the tell that this is designed, not an oversight in one class.

### Why it exists

The interesting question is not "why did they forget cross-type equality" but "what breaks if you
add it". Work it through: the relation cannot be made transitive.

Suppose `Integer.valueOf(1).equals(Long.valueOf(1))` returned true. Symmetry — required by the
`equals` contract — forces `Long.valueOf(1).equals(Integer.valueOf(1))` to be true as well.
`Short.valueOf((short) 1)` is numerically the same 1, so the same rule makes it equal to both. So
does `Byte.valueOf((byte) 1)`. So does `Character.valueOf('\u0001')`, whose numeric value is 1.
Transitivity now collapses the six integral wrappers and `Character` into one equivalence class.

Then `Double` arrives. `Double.valueOf(1.0)` is numerically 1, so it joins the class. Now take a
`long` that a `double` cannot represent, measured:

```
2^53+1                  = 9007199254740993
(double) (2^53+1)       = 9.007199254740992E15
(long)(double) (2^53+1) = 9007199254740992
2^53                    = 9007199254740992
```

`Long.valueOf(9007199254740993L)` and `Long.valueOf(9007199254740992L)` are different longs, but
both map to the identical `double`. If each is "numerically equal" to that `Double`, transitivity
forces the two `Long`s to be equal to each other — and they plainly are not. The relation dies at
`2^53`, and no amount of care in `Integer.equals` can rescue it, because the breakage happens between
two `Long`s that never see a `Double`.

The hash side dies faster. The contract says equal objects must have equal hash codes. Measured on
JDK 21.0.7:

```
Integer.hashCode(1)  = 1
Long.hashCode(1L)    = 1
Double.hashCode(1.0) = 1072693248
```

`Integer` and `Long` agree at 1 by luck. `Double` does not, and cannot be made to without abandoning
`doubleToLongBits` or giving every wrapper a branch-heavy hash that first asks whether the value is
integral. Cross-type equality would therefore cost a broken transitive relation *and* a rewrite of
four hash functions, to buy a convenience that a single `longValue()` call already provides.

**Insight:** the asymmetry between `equals` and `compareTo` is the sharpest thing in this concept.
`equals(Object)` accepts anything, so nothing stops you at compile time. `Comparable<T>` is
parameterised to the wrapper's own type — `Integer implements Comparable<Integer>` — so the
comparison method that *is* typed refuses the call. Measured with `javac` on JDK 21.0.7:

```java
public class CmpProbe {
    static int probe() {
        return Integer.valueOf(1).compareTo(Long.valueOf(1));
    }
}
```

```
/tmp/jcD6/src/CmpProbe.java:3: error: incompatible types: Long cannot be converted to Integer
        return Integer.valueOf(1).compareTo(Long.valueOf(1));
                                                        ^
Note: Some messages have been simplified; recompile with -Xdiags:verbose to get full output
1 error
```

The API that silently returns the wrong answer is the untyped one — worth saying out loud in an
interview, because it generalises well beyond wrappers.

### The mechanism

Every wrapper's `equals` has the same three-part shape: an `instanceof` test against its own class,
a cast, and a primitive `==` on the wrapped value. Quoted from JDK 21.0.7 `Integer.java` line 1226:

```java
public boolean equals(Object obj) {
    if (obj instanceof Integer) {
        return value == ((Integer)obj).intValue();
    }
    return false;
}
```

Line by line: the parameter is `Object`, so any reference is accepted, including `null`; the
`instanceof` is false for `null` and every non-`Integer`, so both fall straight to `return false`
without a throw; the cast is guaranteed safe by the test above it; and `intValue()` on a known
`Integer` is a field read the JIT inlines to nothing. `Long.java` line 1453, `Short.java` line 484
and `Boolean.java` line 257 are the same shape with their own type and accessor.

`Double` is the one that differs, quoted from JDK 21.0.7 `Double.java` line 1066:

```java
public boolean equals(Object obj) {
    return (obj instanceof Double)
           && (doubleToLongBits(((Double)obj).value) ==
                  doubleToLongBits(value));
}
```

It compares *bit patterns*, not numbers. Concept 2 shows what that produces, and why the same
function underpins `Double.hashCode`.

The practical question is what to reach for when you genuinely hold two different wrapper types and
need to know whether they denote the same number.

| Approach | Shape | Verdict |
|---|---|---|
| `a.equals(b)` across types | `Integer.equals(Long)` | Never. Always false, no warning, no exception. |
| Unbox and compare primitives | `a.intValue() == b.longValue()` | Works, but the `int` silently widens; fine when you know the ranges. |
| `Long.compare` after widening | `Long.compare(a, b) == 0` | Explicit about the common type. Measured `0` for `Integer 2800000` versus `Long 2800000L`. |
| `Number.longValue()` on both sides | `a.longValue() == b.longValue()` | The honest option when the static type really is `Number`; loses precision for `Double`/`Float`. |
| Fix the type upstream | one boxed type at the boundary | The actual answer. |

The last row is not a cop-out. A conversion sitting at the point of comparison is a symptom: some
boundary — a JSON body, a `ResultSet`, a message payload — handed you an untyped number and nobody
normalised it. Convert once, on the way in, and the problem disappears rather than being papered over
at every call site.

### Diagram

No diagram for this concept. The evidence is three measured boolean results and one six-line source
excerpt, and prose renders both more precisely than a picture would.

### A concrete example

The realistic path to a cross-type comparison is never a two-wrapper `equals` call written by hand.
It is a map keyed by a boxed id where two producers box the same logical number as
different types. `FundsLedger` loads positions keyed by `Long`; the request path hands you an
`Integer`, because `getInt` and a JSON integer both produce one.

```java
import java.util.HashMap;
import java.util.Map;

public class PositionLookup {

    record Position(String name, long minorUnits) {}

    /** Ledger positions keyed by the position id, as loaded from the ledger. */
    static Map<Long, Position> loadPositions() {
        Map<Long, Position> byId = new HashMap<>();
        byId.put(4001L, new Position("CLIENT_CASH_AVAILABLE", 65_00L));
        byId.put(4002L, new Position("CLIENT_BONUS_AVAILABLE", 42_00L));
        byId.put(4003L, new Position("CLIENT_BONUS_RESERVED", 420L));
        return byId;
    }

    /** The JSON body and the JDBC ResultSet both hand us an int, so this is what arrives. */
    static Object positionIdFromRequest() {
        int fromJson = 4003;
        return Integer.valueOf(fromJson);
    }

    public static void main(String[] args) {
        Map<Long, Position> byId = loadPositions();
        Object requested = positionIdFromRequest();

        System.out.println("containsKey(Integer 4003) = " + byId.containsKey(requested));
        System.out.println("get(Integer 4003)         = " + byId.get(requested));
        System.out.println("containsKey(Long 4003)    = " + byId.containsKey(4003L));

        System.out.println("Integer.valueOf(4003).hashCode() = " + Integer.valueOf(4003).hashCode());
        System.out.println("Long.valueOf(4003L).hashCode()   = " + Long.valueOf(4003L).hashCode());
        System.out.println("Integer 4003 equals Long 4003    = " + Integer.valueOf(4003).equals(4003L));
    }
}
```

Measured output on JDK 21.0.7:

```
containsKey(Integer 4003) = false
get(Integer 4003)         = null
containsKey(Long 4003)    = true
Integer.valueOf(4003).hashCode() = 4003
Long.valueOf(4003L).hashCode()   = 4003
Integer 4003 equals Long 4003    = false
```

The `Object` static type on `positionIdFromRequest` is what a real deserialiser gives you, and
`containsKey(Object)`/`get(Object)` are both declared to take `Object`, so even a correctly-typed
`Map<Long, Position>` accepts an `Integer` probe with no cast and no warning.

Look at the two hash codes: both **4003**. A `HashMap` lookup computes the key's hash first to pick a
bucket, then walks that bucket calling `equals`. Here the hashes agree, so the probe lands in the
right bucket and finds the right entry — and then `Integer.equals(Long)` returns false and the lookup
reports a miss anyway. Agreeing hashes do not save you; `equals` is the decider. The bucket
arithmetic, the spreading function and the treeify threshold belong to guide **02 Java collections**.

### The gotcha

`equals` returning false is not an error condition. Nothing throws, nothing logs, and the code
carries on with a `null` or a `false`. In the path above the symptom is a `CLIENT_BONUS_RESERVED`
position that reads as absent, so a `SettleStake` writes a movement against a position it thinks does
not exist, or an idempotency check concludes a reservation was never made and the client's stake is
reserved twice. The bug surfaces days later in a ledger reconciliation, not as a stack trace.

**Interview:** *Is `Integer.valueOf(1).equals(Long.valueOf(1))` true, and why?* False. `Integer.equals`
begins with `obj instanceof Integer`, which a `Long` fails, so it returns false before the values are
compared — and it must, because cross-type numeric equality cannot be kept transitive once `Double`
is involved: `2^53` and `2^53+1` map to the same `double`, which would force two distinct `Long`s to
be equal. Note also that `equals` compiles because it takes `Object`, whereas
`Integer.valueOf(1).compareTo(Long.valueOf(1))` is a compile error, because `Comparable<Integer>` is
typed.

> **Definition.** A wrapper's `equals` is an `instanceof` test against its own class followed by a
> primitive comparison, so `equals` between two different wrapper types is unconditionally false,
> silently, at every value.

---

## 2. Four hash algorithms, and why each is the shape it is (1.9.18)

`[NUM]` `[X-REF 02]` A `hashCode` has 32 bits of output and a fixed amount of input, so each wrapper's
algorithm is determined by how much value it has to compress. `Integer`, `Short`, `Byte` and
`Character` already fit in 32 bits, so they do nothing at all. `Long` has 64 bits and must fold. A
`double` has 64 bits *and* is not an integer, so it first becomes a `long` bit pattern and then
folds. `Boolean` has two values and picks two constants out of the air. Four algorithms, eight
classes.

### Why it exists

The contract requires only one thing: equal objects hash equally. Everything past that is a
distribution decision with a cost, and the JDK consistently picks the cheapest function that spreads
the values real programs actually use. `Integer.hashCode` returning the value is not laziness — it is
a perfect hash over the whole domain, injective by construction, and free. It is the correct answer
whenever your hash table is willing to do its own spreading, which `HashMap` is.

Each choice has a price, and the Consequence column of the table below states all eight. The one
worth flagging before the mechanism is `Integer`'s: an identity hash is perfectly distinct but not at
all *scattered*, so consecutive ledger amounts land in consecutive buckets and a power-of-two table
masking the low bits piles every small value into the bottom of the table.

### The mechanism

Discharge the `[NUM]` obligation by doing the arithmetic rather than quoting results.

**`Integer` — the value itself.** Quoted from JDK 21.0.7 `Integer.java` line 1212:

```java
public static int hashCode(int value) {
    return value;
}
```

Measured: `Integer.valueOf(-7).hashCode() = -7`, `Integer.valueOf(1).hashCode() = 1`. `Short` and
`Byte` do the same — measured `Short.valueOf((short) -7).hashCode() = -7` and
`Byte.valueOf((byte) -7).hashCode() = -7`. All three of the small integral wrappers hash to their
value, sign included, so a negative amount hashes negative.

**`Character` — the code unit as an `int`.** Quoted from `Character.java` line 9038:

```java
public static int hashCode(char value) {
    return (int)value;
}
```

`char` is unsigned 16-bit, so this is always in `0..65535`. Measured:
`Character.valueOf('A').hashCode() = 65`.

**`Long` — the xor fold.** Quoted from `Long.java` line 1439:

```java
public static int hashCode(long value) {
    return (int)(value ^ (value >>> 32));
}
```

Three operations, read right to left. `value >>> 32` is a *logical* shift, so the high 32 bits move
into the low position and zeros fill the top; using `>>` here would sign-extend and destroy the
property that the fold is a pure mixing of the two halves. The `^` then combines the two halves in
the low 32 bits. The `(int)` cast throws away the top 32 bits, which after the xor are just a copy of
the original high half.

Do it for the packet's measured case. `4_294_967_296L` is 2 to the power 32, so in binary its high
half is `0x00000001` and its low half is `0x00000000`:

```
value        = 0x0000_0001_0000_0000
value >>> 32 = 0x0000_0000_0000_0001
xor          = 0x0000_0001_0000_0001
(int) xor    = 0x0000_0001 = 1
```

Measured: `Long.valueOf(4_294_967_296L).hashCode() = 1`. And measured:
`Long.valueOf(1L).hashCode() = 1`, because for a small positive `long` the high half is zero and the
fold is the identity on the low half. Two distinct `long`s, one hash — verifiable by hand in four
lines, which is the honest version of "the fold loses information". It has to: 2 to the 64 values
cannot map injectively into 2 to the 32 slots.

This is not a theoretical worry in QuizStakes. `LedgerEntry` ids and epoch-millisecond timestamps are
exactly the `long`s whose high half varies, and the ledger writes ~19.8M rows a day. A `Long`-keyed
map over entry ids sees the fold doing real work; a `Long`-keyed map over small counters sees it doing
nothing.

**`Double` — bits, then the same fold.** Quoted from `Double.java` lines 1026 and 1038:

```java
public int hashCode() {
    return Double.hashCode(value);
}

public static int hashCode(double value) {
    return Long.hashCode(doubleToLongBits(value));
}
```

It must go through the bit pattern because it must agree with `equals`, and `equals` compares bits.
It cannot go through the numeric value, because there is no 32-bit integer function of a `double`'s
*number* that is both cheap and consistent with a bitwise `equals`. Measured for the domain's average
stake of 4.20:

```
doubleToLongBits(4.20) = 4616414798036126925 = 0x4010cccccccccccd
high 32 bits = 0x4010cccc = 1074842828
low 32 bits  = 0xcccccccd = -858993459
xor, as int  = -1931739135
```

Measured: `Double.valueOf(4.20).hashCode() = -1931739135`. The arithmetic lands exactly.

`Float` needs no fold at all, because `floatToIntBits` already produces 32 bits. Measured:
`floatToIntBits(4.20f) = 1082549862 = 0x40866666`, and `Float.valueOf(4.20f).hashCode() =
1082549862` — the bit pattern, unmodified.

Two consequences of the `doubleToLongBits` route, both of which a reader will meet:

- `doubleToLongBits` **collapses every NaN bit pattern to the single canonical
  `0x7ff8000000000000`**. Measured: feeding it `0x7ff8000000000001` gives back
  `0x7ff8000000000000`, and both NaNs hash to **2146959360**. That is why
  `Double.valueOf(Double.NaN).equals(Double.NaN)` is measured **true** even though `Double.NaN ==
  Double.NaN` is measured **false**.
- It **does not** collapse `0.0` and `-0.0`, whose bit patterns differ in the sign bit only. Measured:
  `Double.valueOf(0.0).hashCode() = 0` and `Double.valueOf(-0.0).hashCode() = -2147483648`, and
  `Double.valueOf(0.0).equals(Double.valueOf(-0.0))` is measured **false** — while `0.0 == -0.0` is
  measured **true**.

So `equals` and `==` disagree in both directions on `Double`, which is the cleanest demonstration
available that `equals` is doing bit comparison and not arithmetic. IEEE 754 itself — why NaN has
many encodings, why there are two zeros — belongs to
[`../primitives-and-conversions/01c-floating-point.md`](../primitives-and-conversions/01c-floating-point.md).

**`Boolean` — 1231 and 1237.** Quoted from `Boolean.java` line 244:

```java
public static int hashCode(boolean value) {
    return value ? 1231 : 1237;
}
```

Measured: `Boolean.TRUE.hashCode() = 1231`, `Boolean.FALSE.hashCode() = 1237`. Both are prime. As far
as the contract goes the specific values are arbitrary — any two distinct ints would satisfy it. What
matters is that they are written into the `Boolean.hashCode` javadoc, which makes them a
**specified part of the API** rather than an implementation detail that a future JDK may change.
Why *those* two primes were chosen is not stated in the javadoc, the JLS, or any primary source
available here; folklore explanations exist and none is sourceable, so this file does not offer one.

All eight, with the arithmetic and the consequence:

| Wrapper | Algorithm | Measured example, worked | Consequence |
|---|---|---|---|
| `Integer` | `value` | `-7` → `-7`; `1` → `1` | Injective over `int`, but unscattered; the table must spread. |
| `Short` | `value` widened to `int` | `(short) -7` → `-7` | Same; range only `-32768..32767`, so all hashes are small. |
| `Byte` | `value` widened to `int` | `(byte) -7` → `-7` | Only 256 distinct hashes exist, ever. |
| `Character` | `(int) value` | `'A'` → `65` | Always `0..65535`; never negative. |
| `Long` | `(int)(v ^ (v >>> 32))` | `0x1_0000_0000` → `0x1 ^ 0x0` = `1` | Provable collisions; `1L` also hashes `1`. |
| `Float` | `floatToIntBits(v)` | `4.20f` → `0x40866666` = `1082549862` | No fold needed; 32 bits in, 32 out. |
| `Double` | `Long.hashCode(doubleToLongBits(v))` | `4.20` → `0x4010cccc ^ 0xcccccccd` = `-1931739135` | NaNs collapse to one; `0.0` and `-0.0` do not. |
| `Boolean` | `1231` / `1237` | `true` → `1231`; `false` → `1237` | Javadoc-specified, so stable across JDKs. |

The *cache* coverage table for these same eight types lives in
[`01b-cache-coverage-and-reference-equality.md`](01b-cache-coverage-and-reference-equality.md); the
table above is about hashing only.

### How this lands in a hash table (`[X-REF 02]`)

Self-contained version, enough to answer the question without opening another guide. `HashMap` does
not use a key's `hashCode` directly. It applies a spreading step — xor the hash with its own
unsigned right shift by 16 — before masking with `table.length - 1`, precisely because functions like
`Integer.hashCode` put all their entropy in the low bits and a power-of-two mask throws the high bits
away. Without spreading, a table of 16 buckets keyed on ledger amounts in minor units would send
every amount ending in the same low nibble to the same bucket; with it, the high half of the value
participates. The second cost is allocation: a boxed key is a separate heap object per distinct
entry, so an `Integer`-keyed map over 2.8M stake reservations pays a 16-byte `Integer` plus a 4-byte
reference per element, measured at 20 bytes against 4 for an `int[]` — see
[`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md) for that measurement.

Bucket structure, resizing, the treeify threshold, and the primitive-keyed alternatives are guide
**02 Java collections**'s chapter. Go there for the table; this file owns the hash functions feeding
it.

### Diagram

No diagram for this concept. The mechanism is four short source excerpts plus hex arithmetic, and the
eight-row table above is the picture.

### A concrete example

A composite hash over domain fields, done properly and then two ways deliberately, so the costs are
visible. A `Reservation` key combines a `long` entry id, a `double` stake amount and a `boolean`
bonus-first flag.

```java
import java.util.Objects;

public class ReservationKey {

    /** The record's generated hashCode; the hand-rolled fold is below for comparison. */
    record Reservation(long entryId, double stakeAmount, boolean bonusFirst) {

        int objectsHash() {
            return Objects.hash(entryId, stakeAmount, bonusFirst);
        }

        int handRolledHash() {
            int h = Long.hashCode(entryId);
            h = 31 * h + Double.hashCode(stakeAmount);
            h = 31 * h + Boolean.hashCode(bonusFirst);
            return h;
        }
    }

    public static void main(String[] args) {
        Reservation r = new Reservation(4_294_967_296L, 4.20, true);

        System.out.println("Long.hashCode(4294967296) = " + Long.hashCode(r.entryId()));
        System.out.println("Double.hashCode(4.20)     = " + Double.hashCode(r.stakeAmount()));
        System.out.println("Boolean.hashCode(true)    = " + Boolean.hashCode(r.bonusFirst()));
        System.out.println("record hashCode()         = " + r.hashCode());
        System.out.println("Objects.hash of the three = " + r.objectsHash());
        System.out.println("hand-rolled fold          = " + r.handRolledHash());

        Reservation collides = new Reservation(1L, 4.20, true);
        System.out.println("entryId=1 hand-rolled     = " + collides.handRolledHash());
        System.out.println("folds collide             = "
                + (r.handRolledHash() == collides.handRolledHash()));
        System.out.println("but the two are equal?    = " + r.equals(collides));
    }
}
```

Measured output on JDK 21.0.7:

```
Long.hashCode(4294967296) = 1
Double.hashCode(4.20)     = -1931739135
Boolean.hashCode(true)    = 1231
record hashCode()         = 245631151
Objects.hash of the three = 245660942
hand-rolled fold          = 245631151
entryId=1 hand-rolled     = 245631151
folds collide             = true
but the two are equal?    = false
```

Three readings.

The last three lines are concept 2's point propagating upward. `Long.hashCode` maps 2 to the 32 and 1
onto the same value, so a composite hash built on top of it inherits the collision exactly, and two
`Reservation`s that are *not* equal share a hash. That is legal — the contract constrains equal
objects, not unequal ones — and it is what hash tables absorb. It is only a problem if you had
assumed the composite hash was injective.

`Objects.hash` differs from the hand-rolled fold (`245660942` versus `245631151`) because it delegates
to `Arrays.hashCode`, which seeds the accumulator at `1` rather than at the first element's hash. Its
real cost is structural: its erased signature is `Objects.hash(Object[] values)` — varargs — so every
call allocates an `Object[]` **and boxes each primitive argument into it**. Here that is one array
plus a `Long` and a `Double` (the `Boolean` is free, since `Boolean.valueOf` returns `Boolean.TRUE`).
At 2.8M stake reservations a day on a hot path that is real garbage; the fold allocates nothing.

The `record hashCode()` matching the fold at `245631151` is a measured coincidence of this JDK's
implementation strategy, not a guarantee: `javac` generates it via a bootstrap method in
`ObjectMethods`, and the JLS specifies only consistency with the record's `equals`, not the combining
function. Do not rely on the two agreeing.

**Interview:** *What is `Long.hashCode`, and why is it not just the value?* It is
`(int)(value ^ (value >>> 32))` — the high 32 bits xored down onto the low 32, then truncated. It is
not the value because the value does not fit: a `long` has 64 bits of state and `hashCode` returns
32, so some function must lose information, and xor-folding the halves is the cheapest one that keeps
both halves contributing. The price is provable collisions — `1L` and `2^32` both hash to 1, measured.

### The gotcha

The trap is relying on a specific `hashCode` **value**: persisting it in a column, sharding on it,
routing a message by it, or asserting it in a unit test. The general rule is that hash codes are not
stable across JVM versions, vendors, or runs. The wrapper hash codes are the exception — every one of
the eight algorithms above is written into its javadoc, so `Boolean.TRUE.hashCode()` really will be
1231 on any conforming JDK — and that exception is exactly what makes the habit dangerous. A
developer verifies it once on `Integer`, concludes hash codes are stable, and then pins a test to a
`record`'s hash or shards a queue on a domain object's hash, where nothing is specified at all.

The line is: specified in javadoc (the eight wrappers, `String`, `List`, `Set`, `Map`, `Arrays`)
versus unspecified (records, enums, everything using `Object.hashCode`). `Object`'s identity hash is
the opposite extreme — it is derived at first request and stored in the mark word, so it varies
between runs of the same program; see
[`../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`](../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md).

> **Definition.** The eight wrappers use four javadoc-specified hash algorithms — identity for the
> small integral types and `Character`, an xor fold of the two halves for `Long`, the same fold over
> `doubleToLongBits` for `Double`, and the constants 1231/1237 for `Boolean` — each the cheapest
> function that satisfies the contract for that type's amount of state.

---

## Supporting facts

**`Objects.equals(a, b)`** is `(a == b) || (a != null && a.equals(b))`, so a `null` on the left does
not throw and reference identity short-circuits first, which makes it free for cached wrappers.
Measured: `Objects.equals(null, null)` is **true**, and
`Objects.equals(Integer.valueOf(2_800_000), 2_800_000L)` is **false** — it delegates to the same
`Integer.equals`. Null-safety and type-correctness are different problems.

**`Integer.compare(x, y)`** returns specifically `-1`, `0` or `1` rather than an arbitrary negative or
positive number — measured `Integer.compare(1, 2) = -1`. It takes two `int`s, so a call with two
`Integer`s unboxes both and will NPE on a null, exactly as
[`01c-unboxing-null.md`](01c-unboxing-null.md) describes. `Long.compare(long, long)` is the useful
cross-type escape hatch: an `Integer` argument unboxes to `int` and then widens to `long` in the same
invocation. Measured for an `Integer` `2800000` against a `Long` `2800000L`: **0**.

**`Number.longValue()`** is the only cross-type comparison the type system endorses. `Number` is
`abstract` and declares exactly six instance methods — `intValue`, `longValue`, `floatValue`,
`doubleValue` abstract, plus concrete `byteValue` and `shortValue`. Six wrappers extend it;
`Character` and `Boolean` do not, so a `Character` can never take part. Measured: for
`Number n1 = Integer.valueOf(1)` and `Number n2 = Long.valueOf(1)`,
`n1.longValue() == n2.longValue()` is **true**. It truncates for `Double` and `Float`, so it is not a
general numeric equality either.

---

## Pitfalls

### Probing a `Map<Long, …>` with an `Integer` key

**Wrong**

```java
Map<Long, Position> byId = FundsLedger.loadPositions();   // keys are Long
Object requested = Integer.valueOf(4003);                 // from the JSON body

System.out.println(byId.containsKey(requested));
System.out.println(byId.get(requested));
```

Measured output on JDK 21.0.7, with `4003L` genuinely present in the map:

```
false
null
```

No exception, no warning, no log line. Downstream, `SettleStake` treats
`CLIENT_BONUS_RESERVED` as absent and the client's stake is reserved a second time.

**Right**

Make the key type explicit at the boundary and convert once, or better, key on a domain value type so
the compiler can refuse the wrong thing:

```java
record PositionId(long value) {
    static PositionId of(Number raw) {
        return new PositionId(raw.longValue());
    }
}

Map<PositionId, Position> byId = FundsLedger.loadPositions();
Number fromJson = Integer.valueOf(4003);
PositionId key = PositionId.of(fromJson);

System.out.println(byId.get(key));
```

Measured:

```
Position[name=CLIENT_BONUS_RESERVED, minorUnits=420]
```

`PositionId` also gives you one place to validate the id, and its record `hashCode` measured `4003`
for id `4003` — the `Long.hashCode` of the field, since a single-component record folds one hash.

**Why people believe it:** `Map.containsKey` and `Map.get` are declared to take `Object`, not `K`, so
there is no compile error even in a fully generic map; `equals(Object)` likewise takes anything; and
both sides print `4003`, so every debugger view and every log line agrees they are the same.

### Comparing a count from JDBC with a count from the domain

**Wrong**

```java
Integer settledFromJdbc = 2_800_000;      // resultSet.getInt("settled_count")
Long settledFromDomain = 2_800_000L;      // Reservation aggregate

System.out.println(settledFromJdbc.equals(settledFromDomain));
System.out.println(java.util.Objects.equals(settledFromJdbc, settledFromDomain));
```

Measured on JDK 21.0.7:

```
false
false
```

In a test this becomes an assertion that fails while both sides print `2800000`, and the usual
reaction is to blame the query. In production it becomes a reconciliation job that reports a
permanent mismatch.

**Right**

Bring both to one primitive type explicitly, and say which one:

```java
Integer settledFromJdbc = 2_800_000;
Long settledFromDomain = 2_800_000L;

System.out.println(settledFromJdbc.longValue() == settledFromDomain.longValue());
System.out.println(Long.compare(settledFromJdbc, settledFromDomain));
```

Measured:

```
true
0
```

`Long.compare(long, long)` is the cleaner of the two: the `Integer` unboxes to `int` and widens to
`long` inside the invocation, so the widening is visible in the chosen overload rather than hidden
behind a method call. The real fix is upstream — have the repository return `long` and stop the
`Integer` existing.

**Why people believe it:** the primitive comparison `settledFromJdbc == settledFromDomain` is a
compile error only when both sides are wrappers; write it with one primitive and it passes, so the
boxed form looks like a harmless refactor of something that already worked. Assertion libraries make
it worse by having both a primitive and an `Object` overload that resolve differently depending on
the declared types.

### Asserting a specific `hashCode`, or persisting one

**Wrong**

```java
// unit test
assert new Reservation(4_294_967_296L, 4.20, true).hashCode() == 245631151;

// routing
int shard = Math.abs(reservation.hashCode()) % 16;   // stored in the ledger row
```

The assertion is pinned to `245631151`, which this JDK 21.0.7 run measured for the record but which
the JLS does not specify — `javac` generates record `hashCode` through a bootstrap method in
`ObjectMethods`, and only consistency with `equals` is guaranteed. The shard number gets written to
disk, and a JDK upgrade or a field reorder silently sends the same reservation to a different shard,
so a `SettleStake` cannot find its own `CLIENT_BONUS_RESERVED` movement.

**Right**

Assert the contract, not the number; and for anything durable use a function that is specified:

```java
// unit test: the contract, not the value
Reservation a = new Reservation(4_294_967_296L, 4.20, true);
Reservation b = new Reservation(4_294_967_296L, 4.20, true);
System.out.println(a.equals(b) && a.hashCode() == b.hashCode());   // true

// routing: an explicitly specified function, stable across versions and vendors
byte[] digest = java.security.MessageDigest.getInstance("SHA-256")
        .digest(Long.toString(a.entryId()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
int shard = Math.floorMod(digest[0], 16);
```

Note `Math.floorMod` rather than `%`, because `%` on a negative hash yields a negative index —
`Integer.hashCode` returning the value means negative amounts hash negative, and `Math.abs` on
`Integer.MIN_VALUE` is itself `Integer.MIN_VALUE`.

**Why people believe it:** the habit is reinforced by the one family where it genuinely works. The
eight wrapper hash codes really are javadoc-specified and really will not change — 1231 for
`Boolean.TRUE` on every conforming JDK — so a developer who checks `Integer` and `Boolean` concludes
hash codes are stable in general, and carries the conclusion to records and domain objects where
nothing is promised.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Integer.valueOf(1).equals(Long.valueOf(1))` | `false`, measured |
| `Long.valueOf(1).equals(Integer.valueOf(1))` | `false`, measured — symmetric |
| `Integer.valueOf(1).equals(Short.valueOf((short) 1))` | `false`, measured |
| Shape of wrapper `equals` | `instanceof <own type>`, cast, primitive `==` |
| `equals(null)` on any wrapper | `false`, never throws — `instanceof` is false for null |
| Why no cross-type equality | transitivity dies at 2^53 once `Double` joins; hashes disagree |
| `Integer.valueOf(1).compareTo(Long.valueOf(1))` | **compile error**: `Long cannot be converted to Integer` |
| Why `equals` compiles but `compareTo` does not | `equals(Object)` is untyped; `Comparable<Integer>` is typed |
| `Integer.hashCode()` | `value`, unchanged |
| `Short` / `Byte` `hashCode()` | value widened to `int`; measured `-7` for value `-7` |
| `Character.hashCode()` | `(int) value`; measured `65` for `'A'` |
| `Long.hashCode()` | `(int)(value ^ (value >>> 32))` |
| `Long.valueOf(1L).hashCode()` | `1`, measured |
| `Long.valueOf(4_294_967_296L).hashCode()` | `1`, measured — collides with `1L` |
| `Double.hashCode()` | `Long.hashCode(doubleToLongBits(value))` |
| `Double.valueOf(4.20).hashCode()` | `-1931739135`, measured (`0x4010cccc ^ 0xcccccccd`) |
| `Float.hashCode()` | `floatToIntBits(value)` — no fold; `4.20f` → `1082549862` |
| `Boolean.TRUE.hashCode()` / `FALSE` | `1231` / `1237`, javadoc-specified |
| `Double.valueOf(0.0).equals(-0.0)` | `false`, measured — while `0.0 == -0.0` is `true` |
| `Double.valueOf(NaN).equals(NaN)` | `true`, measured — while `NaN == NaN` is `false` |
| `doubleToLongBits` on any NaN | canonical `0x7ff8000000000000`; hash `2146959360` |
| `Double.valueOf(0.0).hashCode()` / `-0.0` | `0` / `-2147483648`, measured |
| Which wrapper hash codes are specified | all eight, in javadoc — safe to depend on |
| Which are not specified | records, enums, `Object.hashCode` (identity, per-run) |
| `Objects.equals(null, null)` | `true`; delegates to `equals` otherwise, so no help cross-type |
| `Integer.compare(1, 2)` | `-1`, measured — a sign, not an arbitrary negative |
| `Long.compare(Integer 2800000, Long 2800000L)` | `0`, measured — unbox then widen |
| `Number.longValue()` | the endorsed cross-type route; six wrappers only |
| Wrappers not extending `Number` | `Character`, `Boolean` |
| `Objects.hash` cost | erased `Objects.hash(Object[] values)` — allocates an array, boxes each arg |
| `HashMap` and `Integer.hashCode` | table applies its own spreading step; identity hash is low-entropy |
| Cost of a boxed key | 16-byte `Integer` + 4-byte reference = 20 bytes/element, measured |
| Safe shard function | a named digest, not `hashCode`; use `Math.floorMod`, not `%` |

---

## Self-test

**Q1.** Is `Integer.valueOf(1).equals(Long.valueOf(1))` true? Why is the answer not just an oversight?

<details><summary>Answer</summary>

It is false, measured on JDK 21.0.7, and so is the reverse. `Integer.equals` is
`if (obj instanceof Integer) return value == ((Integer) obj).intValue(); return false;` — the
`instanceof` fails for a `Long` before any number is compared. It is not an oversight, because
cross-type numeric equality cannot satisfy the `equals` contract. If `Integer` 1 equalled `Long` 1,
symmetry pulls in the reverse direction, and the same rule pulls in `Short`, `Byte` and
`Character('\u0001')`; transitivity then collapses them into one class. Add `Double` and it breaks
outright: `2^53+1` and `2^53` both convert to the same `double` (measured, `(double)
9007199254740993L` prints `9.007199254740992E15`), so both `Long`s would be equal to that `Double`
and therefore, by transitivity, to each other. The hash contract fails even sooner —
`Integer.hashCode(1)` and `Long.hashCode(1L)` are both 1, but `Double.hashCode(1.0)` is measured
1072693248.

</details>

**Q2.** Why does `Integer.valueOf(1).equals(Long.valueOf(1))` compile while
`Integer.valueOf(1).compareTo(Long.valueOf(1))` does not?

<details><summary>Answer</summary>

`equals` is inherited from `Object` with the signature `equals(Object)`, so it accepts any reference
whatsoever and the compiler has nothing to object to. `compareTo` comes from `Comparable<T>`, and
`Integer` declares `implements Comparable<Integer>`, so the method it actually has is
`compareTo(Integer)`. Passing a `Long` is a plain type error; `javac` on JDK 21.0.7 says
`error: incompatible types: Long cannot be converted to Integer`. The lesson generalises: the untyped
API is the one that silently returns the wrong answer, and the typed one is the one that protects
you. It is also why static analysis rules exist specifically to flag cross-type `equals` — the
compiler cannot.

</details>

**Q3.** What is `Long.hashCode`, and why is it not just the value?

<details><summary>Answer</summary>

It is `(int)(value ^ (value >>> 32))`. The `>>>` is a logical shift, so the high 32 bits move down
with zero fill; `^` mixes the halves; the `(int)` cast keeps the low 32. It cannot be the value
because a `long` has 64 bits of state and `hashCode` returns 32, so information must be lost, and
xor-folding the halves is the cheapest function in which both halves still contribute. The price is
provable collisions: `Long.valueOf(1L).hashCode()` and `Long.valueOf(4_294_967_296L).hashCode()` are
both measured 1, because 2 to the 32 has high half `0x00000001` and low half `0x00000000`, and
`0x00000001 ^ 0x00000000` is 1 — the same as the identity fold of `1L`. That matters for `long`s whose
high half varies, which is exactly ledger entry ids and epoch-millisecond timestamps.

</details>

**Q4.** Why does `Double.hashCode` go through `doubleToLongBits` instead of the numeric value, and
what two surprises does that produce?

<details><summary>Answer</summary>

Because it has to agree with `Double.equals`, and `Double.equals` is defined as
`(obj instanceof Double) && doubleToLongBits(other.value) == doubleToLongBits(value)` — a bit
comparison. `Double.hashCode(v)` is `Long.hashCode(doubleToLongBits(v))`, so the same 64-bit pattern
goes through the same xor fold. Measured for 4.20: `doubleToLongBits(4.20) = 0x4010cccccccccccd`,
high half `0x4010cccc` = 1074842828, low half `0xcccccccd` = -858993459, xor as `int` =
-1931739135, which is the measured `hashCode`. The two surprises: `doubleToLongBits` collapses every
NaN encoding to the canonical `0x7ff8000000000000`, so `Double.valueOf(NaN).equals(NaN)` is measured
**true** even though `NaN == NaN` is false; and it does not collapse the two zeros, so
`Double.valueOf(0.0).equals(Double.valueOf(-0.0))` is measured **false** even though `0.0 == -0.0` is
true. `equals` and `==` disagree in both directions on `Double`.

</details>

**Q5.** A `Map<Long, Position>` contains the key `4003L`. A caller passes `Integer.valueOf(4003)` to
`containsKey`. What happens, and why did the compiler not stop it?

<details><summary>Answer</summary>

`containsKey` returns false and `get` returns null, both measured, even though the entry is present.
The compiler did not stop it because `Map.containsKey` and `Map.get` are declared to take `Object`,
not `K` — a deliberate choice so that a lookup does not require the caller to hold the exact key
type. Notably the hash codes agree here: `Integer.valueOf(4003).hashCode()` and
`Long.valueOf(4003L).hashCode()` are both measured 4003, so the probe lands in the correct bucket and
finds the correct entry. `equals` is then the decider, and `Integer.equals(Long)` is false, so the
lookup reports a miss. The fix is to normalise at the boundary — one boxed type, converted once — or
to key on a domain value type such as a `PositionId` record, which makes the wrong type a compile
error.

</details>

**Q6.** When is it safe to depend on a specific `hashCode` value?

<details><summary>Answer</summary>

Only where the javadoc specifies the algorithm. That covers the eight wrappers — `Integer` returns
the value, `Long` the xor fold, `Double` the fold over `doubleToLongBits`, `Boolean` 1231 and 1237 —
plus `String`, `List`, `Set`, `Map` and the `Arrays` helpers. For those, the value is part of the API
and will be the same on any conforming JDK. Everything else is unspecified: a record's `hashCode` is
generated through a bootstrap method in `ObjectMethods` and only guaranteed consistent with the
record's `equals`; an enum's and any plain object's default is the identity hash, which is derived on
first request and stored in the mark word, so it differs between runs of the same program. Never
persist an unspecified hash and never route on one. If you need a stable partition function, use a
named digest such as SHA-256 over a canonical string form, and index it with `Math.floorMod` rather
than `%`, because `Integer.hashCode` returning the value means negative inputs hash negative.

</details>

**Q7.** `Objects.hash(entryId, stakeAmount, bonusFirst)` over a `long`, a `double` and a `boolean`.
What does it cost, and what does a hand-rolled fold buy you?

<details><summary>Answer</summary>

`Objects.hash` is varargs — its erased signature is `Objects.hash(Object[] values)` — so every call
allocates an `Object[]` and boxes each primitive argument into it: a `Long`, a `Double`, and for the
`boolean` a reference to the cached `Boolean.TRUE`. That is one array plus two heap objects per call.
It then delegates to `Arrays.hashCode`, whose accumulator starts at 1, which is why its result differs
from a hand-rolled fold seeded on the first field: measured `245660942` versus `245631151` for the
same three values. The hand-rolled version — `Long.hashCode(id)`, then `31 * h +
Double.hashCode(amount)`, then `31 * h + Boolean.hashCode(flag)` — allocates nothing and calls only
static primitive methods. On a lookup path serving 2.8M stake reservations a day the difference is
real garbage; on a cold path `Objects.hash` is fine and more readable. Either way, the composite
inherits `Long.hashCode`'s collisions: measured, entry ids `4294967296` and `1` produce the same fold.

</details>

---

## Open questions

- Why `Boolean.hashCode` uses specifically **1231** and **1237** is not stated in the JDK 21.0.7
  javadoc, the `Boolean.java` source comments, or the JLS. Established: both are prime, both are
  javadoc-specified, and the contract is satisfied by any two distinct `int`s. What would settle it:
  the original JDK 1.0 `java.lang.Boolean` change history; no primary source was available here.
- `record hashCode()` measured `245631151`, identical to the hand-rolled `31`-based fold, on JDK
  21.0.7. Established: that is what `ObjectMethods`' generated implementation produced for these three
  components in this order. Not established: whether the agreement holds for other component types,
  orders, or JDK builds — the JLS specifies only consistency with `equals`. What would settle it:
  reading `java.lang.runtime.ObjectMethods` and its `invokedynamic` bootstrap, beyond this tier.

---

**Leaves covered:** 1.9.11, 1.9.18 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 900
