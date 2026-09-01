# 03 Java Core — Cache coverage and reference equality — BASICS (§1.9, 1.9.6–1.9.8)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The archived cache](01a2-the-archived-cache.md) · Next: [Unboxing null](01c-unboxing-null.md)

Two facts sit at the centre of this file, and almost every wrapper bug in production is the pair of
them colliding. First: the eight wrapper classes do **not** all cache, and the ones that do cache
three different shapes of range. Second: `==` between two wrapper references is a reference
comparison, always, with no exceptions and no operator overloading — so the cache silently decides
whether a value comparison written with `==` *looks* correct.

[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md) owns `IntegerCache`'s static block and index
arithmetic, and [`01a2-the-archived-cache.md`](01a2-the-archived-cache.md) owns the CDS archived
subgraph; this file re-derives neither, and instead answers the two questions they left open: *what
about the other seven wrappers*, and *what does the cache actually do to my `==`*.

---

## 1. The coverage map, and why each range is the shape it is (1.9.6)

`[NUM]` Eight wrapper classes. Five caches. Three different shapes. Picture eight boxes on a shelf:
`Byte` holds every value its type can express, so nothing can miss it. `Short`, `Integer` and `Long`
hold a 256-value window punched out of a range billions or quintillions wide, so almost everything
misses. `Character` has only the bottom half — `0..127`, no negative side, because a `char` has no
negative side. `Boolean` is not a box at all but two named constants. `Float` and `Double` have
nothing. Each shape is **forced by the type**, not chosen for taste, and once you see what forces it
you never have to memorise the table.

### Why it exists

JLS 21 §5.1.7 (boxing conversion) mandates that boxing an `int`, `short` or `byte` in `-128..127`, a
`char` in `\u0000..\u007f`, or either `boolean` value must always yield **the same reference** for the
same value. That is a language guarantee, not an optimisation. The JDK's source says so out loud — the
last line of `IntegerCache`'s static block is:

```java
// range [-128, 127] must be interned (JLS7 5.1.7)
assert IntegerCache.high >= 127;
```

Everything wider than that mandate is an implementation choice, and the JDK's choices track what
"small" means for each type:

- For `byte`, "small" is the entire type, and covering it costs 256 objects, so the JDK covers it.
- For `short`, `int` and `long`, the mandate is the whole of the win: counters, dispositions and
  retry attempts cluster near zero, a stake amount in minor units does not.
- For `char`, the mandate is `0..127`, which is exactly ASCII — parsers, status-code prefixes and
  delimiters.
- For `boolean` there is nothing to size: two values, two constants.
- For `float` and `double` there is no useful finite set of "small" values at all, and identity reuse
  is actively hazardous there. More on that below.

**When the shape matters and when it does not:** if you never write `==` on a wrapper and never
`synchronized` on one, coverage is invisible. The moment either appears, coverage is the only thing
deciding your behaviour.

### The mechanism

The whole of it is visible in five `valueOf` methods. Read them for the *bounds check*, not the array
access — its presence, absence and asymmetry is the entire content.

`Byte.valueOf` — there is **no bounds check at all**:

```java
public static Byte valueOf(byte b) {
    final int offset = 128;
    return ByteCache.cache[(int)b + offset];
}
```

Two lines, and the missing `if` is the point. A `byte` ranges `-128..127`; the cache array is
`-(-128) + 127 + 1` = 256 entries; therefore `(int) b + 128` is in `0..255` for **every** `byte` that
can exist, so a bounds check would be dead code and there is no `new Byte(b)` fallback at all.
`Byte.valueOf` cannot allocate.

`Long.valueOf` — the check is back, with the bounds as literals:

```java
public static Long valueOf(long l) {
    final int offset = 128;
    if (l >= -128 && l <= 127) { // will cache
        return LongCache.cache[(int)l + offset];
    }
    return new Long(l);
}
```

`Short.valueOf` is the same shape, differing only in the comment — `// must cache` rather than
`// will cache` — and in widening `short` to `int` first so the comparison and the index arithmetic
happen in `int`:

```java
public static Short valueOf(short s) {
    final int offset = 128;
    int sAsInt = s;
    if (sAsInt >= -128 && sAsInt <= 127) { // must cache
        return ShortCache.cache[sAsInt + offset];
    }
    return new Short(s);
}
```

`Character.valueOf` — one-sided, and therefore **no offset**:

```java
public static Character valueOf(char c) {
    if (c <= 127) { // must cache
        return CharacterCache.cache[(int)c];
    }
    return new Character(c);
}
```

There is no `c >= 0` half to the condition because `char` is the one unsigned primitive in Java, so
the lower bound is structurally satisfied; and because the cached range *starts* at zero, the index is
the code unit itself. `CharacterCache`'s static block sizes the array `int size = 127 + 1;` — 128
entries, not 256.

**Insight:** the three index expressions are the coverage map in miniature:

| Class | Index expression in `valueOf` | Why that expression |
|---|---|---|
| `Byte` | `(int) b + 128` | shifts the full signed byte range onto `0..255`; total coverage, no check needed |
| `Short`, `Long` | `(int) v + 128` guarded by `v >= -128 && v <= 127` | same shift, but the type is wider than the window, so the guard is live |
| `Integer` | `i + (-IntegerCache.low)` guarded by `low`/`high` **fields** | the bounds are fields, not literals — which is why only `Integer` is tunable |
| `Character` | `(int) c` guarded by `c <= 127` only | range starts at 0, so no offset and no lower-bound test |

`Boolean` has **no cache class at all**. There is nothing to index:

```java
public static final Boolean TRUE = new Boolean(true);
public static final Boolean FALSE = new Boolean(false);

public static Boolean valueOf(boolean b) {
    return (b ? TRUE : FALSE);
}
```

Two eagerly-initialised `public static final` fields and a ternary. That absence is independently
visible from outside: `java -Xlog:cds+heap=info -version` on JDK 21.0.7 lists the archived heap
subgraphs the JVM resolves at startup:

```
[0.009s][info][cds,heap] resolve subgraph java.lang.Integer$IntegerCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Long$LongCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Byte$ByteCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Short$ShortCache
[0.009s][info][cds,heap] resolve subgraph java.lang.Character$CharacterCache
```

Five lines, five cache classes, **zero lines matching `Boolean`** (measured) — there is no
`Boolean$BooleanCache` to archive because there is no such class. The archive mechanism itself is
[`01a2-the-archived-cache.md`](01a2-the-archived-cache.md)'s subject; here it is only a witness.

`Float` and `Double` have no cache of any kind — no cache class, no `valueOf` bounds check, no
archived subgraph. Three reasons you can reconstruct rather than memorise. First, there is no useful
finite set of "small" floating-point values: between `0.0` and `1.0` alone there are roughly 2^62
distinct `double` values. Second, the values that *would* collide are a handful of literals — `0.0`,
`1.0`, `4.20` — almost never compared by identity. Third, and decisively, identity reuse on floating
point is hazardous, because IEEE 754 has values whose equality does not behave like a value type's
should. Measured on JDK 21.0.7:

```
Double.valueOf(0.0).equals(-0.0)    : false
```

`0.0 == -0.0` is `true` as a primitive comparison, yet the boxed `equals` is `false`, because
`Double.equals` compares `doubleToLongBits` and the sign bit differs. A cache would have to hard-code
whether `0.0` and `-0.0` share an instance, and both answers are defensible. `NaN` compounds it:
`NaN != NaN` as primitives, while `Double.valueOf(Double.NaN).equals(Double.NaN)` is `true`. Full
treatment in
[`../primitives-and-conversions/01c-floating-point.md`](../primitives-and-conversions/01c-floating-point.md);
the conclusion here is that `Float` and `Double` never share instances, so `==` on them is *always*
wrong for value comparison, with no test-passing range to hide in.

### Diagram

**D-026** — Which wrapper caches what, on Java 21. `Integer` is the only tunable one.

| Wrapper | Cached range (Java 21 default) | Cached instances | Tunable | Flag / property |
|---|---|---|---|---|
| `Byte` | `-128..127` — **the entire type** | **256** = 127 − (−128) + 1 | no | none |
| `Short` | `-128..127` | **256** = 127 − (−128) + 1 | no | none |
| `Integer` | `-128..127` at the default `high` | **256** = 127 − (−128) + 1 at the default | **yes** (upper bound only) | `-XX:AutoBoxCacheMax` or `-Djava.lang.Integer.IntegerCache.high` |
| `Long` | `-128..127` | **256** = 127 − (−128) + 1 | no | none |
| `Character` | `0..127` — no negative half | **128** = 127 − 0 + 1 | no | none |
| `Boolean` | both values, as `Boolean.TRUE` / `Boolean.FALSE` | **2** | no | none |
| `Float` | nothing | **0** | no | none |
| `Double` | nothing | **0** | no | none |

The instance counts are arithmetic, not lore: an inclusive range `low..high` holds `high − low + 1`
values, so `-128..127` is 256 and `0..127` is 128. `Boolean` is 2 because `boolean` has two values.
`Float` and `Double` are 0 because there is no cache class to count.

`Integer`'s tunability is the one row not shaped by its type: its bounds live in `IntegerCache.low`
and `IntegerCache.high` **fields** rather than literals, and the static block reads a saved VM
property to raise `high`. `low` cannot be moved at all, and the
`Math.max(parseInt(integerCacheHighPropValue), 127)` in that block means the property can only
*raise* the bound. How that is built and configured is
[`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md)'s chapter.

### A concrete example

Coverage is not uniform, so a single QuizStakes payload can straddle all three shapes at once. This
audit record boxes five wrapper types from one stake reservation, and only three of the five boxes
are shared instances:

```java
record ReservationAudit(
        Byte verificationAttempts,   // 0..3 — Byte always caches
        Character disposition,       // '0','1','5','9' from XX-Nnn — under 128
        Short activeRestrictions,    // 0..10 restriction types — inside -128..127
        Integer stakeMinorUnits,     // 420 for the average 4.20 stake — OUTSIDE the cache
        Double stakeMajorUnits) {    // 4.20 — no cache exists at all

    static ReservationAudit of(int attempts, char disposition, int restrictions, int minorUnits) {
        return new ReservationAudit(
                (byte) attempts,     // boxes via Byte.valueOf
                disposition,         // boxes via Character.valueOf
                (short) restrictions,// boxes via Short.valueOf
                minorUnits,          // boxes via Integer.valueOf
                minorUnits / 100.0); // boxes via Double.valueOf
    }

    static void probeSharing() {
        ReservationAudit first  = of(2, '1', 3, 420);
        ReservationAudit second = of(2, '1', 3, 420);
        System.out.println(first.verificationAttempts() == second.verificationAttempts());
        System.out.println(first.disposition()          == second.disposition());
        System.out.println(first.activeRestrictions()   == second.activeRestrictions());
        System.out.println(first.stakeMinorUnits()      == second.stakeMinorUnits());
        System.out.println(first.stakeMajorUnits()      == second.stakeMajorUnits());
    }
}
```

`probeSharing` prints `true`, `true`, `true`, `false`, `false`. The first three share instances
because 2, `'1'` (code unit 49) and 3 are inside their respective caches; `420` misses `Integer`'s
window by a wide margin; `4.20` has no window to hit. Five boxes from one domain event, three
different identity answers — which is why "wrappers are cached" is not a usable sentence.

The measured identity results behind that, on JDK 21.0.7:

```
Byte  valueOf((byte)-128) == itself : true      Byte  valueOf((byte)127) == itself : true
Short valueOf((short)127) == itself : true      Short valueOf((short)128) == itself : false
Long  valueOf(127L)       == itself : true      Long  valueOf(128L)       == itself : false
Char  valueOf((char)127)  == itself : true      Char  valueOf((char)128)  == itself : false
Bool  valueOf(true)       == itself : true      Boolean.TRUE == Boolean.valueOf(true) : true
Float valueOf(1.0f)       == itself : false
Double valueOf(1.0)       == itself : false
```

Note `Byte` at both ends: both `true`, as is every value between, because there is no value outside.

### The gotcha

The three shapes mean **the boundary is in a different place for each type**, so a habit learned on
`Integer` misfires elsewhere in three distinct ways:

- On `Character`, "the boundary is ±128" is wrong twice over: there is no negative half, and the top
  of the range is 127 not 128 — measured, `Character.valueOf((char) 128) == itself` is `false`. Any
  code unit above \u007f falls out of the cache, and ASCII fixtures will never show you.
- On `Byte`, the boundary does not exist. `==` on two `Byte` values of equal value is `true` on this
  JDK, always, for every input. A defensive `equals` there looks like paranoia and a careless `==`
  never fails a test.
- On `Float` and `Double`, there is no boundary because there is no cache. `==` on two boxes of the
  same value is `false` even for `0.0`.

**Interview:** *"Which wrappers cache, and what ranges?"* — Six of the eight share instances, five
through a cache class. `Byte` caches all 256 values of the type with no bounds check in `valueOf`;
`Short`, `Integer` and `Long` cache `-128..127`, 256 each; `Character` caches `0..127`, 128 instances,
one-sided because `char` is unsigned; `Boolean` has no cache class, just `TRUE` and `FALSE`; `Float`
and `Double` cache nothing. Only `Integer` is tunable, because only it keeps its bounds in fields.

> **Definition.** Six of the eight wrappers share instances — `Byte` over its whole type,
> `Short`/`Integer`/`Long` over `-128..127`, `Character` over `0..127`, `Boolean` via two constants,
> `Float` and `Double` not at all — and each shape is forced by what "small" can mean for that
> primitive type, with only `Integer`'s upper bound configurable.

---

## 2. `==` on wrappers compares references, and the cache decides whether that looks correct (1.9.7, 1.9.8)

`[TRAP]` `[PROVE]` `==` between two references asks exactly one question: *are these the same
object?* It has never asked anything else, for any reference type, in any version of Java. The cache
makes that question **return the answer you wanted** for precisely the values your fixtures use, then
stops doing so when real traffic arrives with 420 instead of 3. The cache does not make `==` work; it
makes `==` fail to fail.

### Why it exists

There is no bug in the language here, and being precise about that matters, because the usual
framing ("Java's `==` is broken for `Integer`") gets a candidate marked down. Two facts collide:

1. `==` is not overloadable. JLS 21 §15.21.3 defines it for reference operands as *reference
   equality* — same object, or both `null`. `Integer` has no hook to redefine it, and adding one
   would break every identity comparison in the language.
2. `Integer.valueOf` shares instances for small values, because JLS §5.1.7 requires it to.

Each is correct in isolation. Together they produce an operator that appears to compare values over
exactly the range unit tests use.

**When each form is correct:**

| You want | Write | Why |
|---|---|---|
| value comparison of two wrappers | `a.equals(b)` | compares the wrapped value; the wrapper's `equals` is the value comparison |
| value comparison, one side primitive | `a == 5` or `a.intValue() == n` | mixed `==` unboxes the wrapper, so this really is a value comparison |
| ordering | `a.compareTo(b)` or `Integer.compare(x, y)` | `==`/`<` on wrappers is either identity or an unboxing you did not intend |
| deliberate identity check | `a == b`, with a comment saying so | legitimate, and rare: cache probes, sentinel checks, interning assertions |
| the common case | do not box at all — use `int` | no identity question can arise |

For wrappers, **`equals` is the answer**: it compares the value correctly for every value in the
type, cached or not. Its one trap — `equals` is `false` across wrapper types, so
`Integer.valueOf(1).equals(Long.valueOf(1))` is `false` — belongs to
[`01d-wrapper-equals-and-hashcode.md`](01d-wrapper-equals-and-hashcode.md).

### The mechanism

`Integer a = 127;` is not a special form: assignment context applies a boxing conversion, and `javac`
desugars it to `Integer.valueOf(127)` — an `invokestatic`, which [`01-basics.md`](01-basics.md) reads
instruction by instruction. So "is `a == b` true" reduces entirely to "did the two `valueOf` calls
return the same reference", answered by the one bounds check:

```java
@IntrinsicCandidate
public static Integer valueOf(int i) {
    if (i >= IntegerCache.low && i <= IntegerCache.high)
        return IntegerCache.cache[i + (-IntegerCache.low)];
    return new Integer(i);
}
```

Inside the window: an array read, same slot both times, same reference. Outside: `new Integer(i)`,
twice, two distinct objects. `==` reports both situations accurately. Nothing about the number 127 is
special to the JVM; 127 is special only because it is `IntegerCache.high`.

**`[PROVE]` — work it, do not assert it.** Measured on JDK 21.0.7 (21.0.7+8-LTS-245):

```
Integer a = 127, b = 127;  a == b  -> true
  identityHashCode(a) = 692404036   identityHashCode(b) = 692404036
Integer c = 128, d = 128;  c == d  -> false
  identityHashCode(c) = 1670675563  identityHashCode(d) = 723074861
```

Read that in both directions, because `identityHashCode` proves less than it looks like it does.

For the 128 case the evidence is conclusive. `System.identityHashCode` returns the identity hash of
*one* object, and one object has one identity hash for its entire lifetime. `1670675563` and
`723074861` are different numbers, therefore they came from different objects, therefore `c` and `d`
denote different objects, therefore `c == d` must be `false`. Two distinct identity hashes is a
**proof** of non-identity, and the `==` result agrees — two independent witnesses.

For the 127 case it is weaker, and saying so is the honest form of the answer. Both prints are
`692404036`, which is *consistent* with one object but does not prove it: identity hashes are 31-bit
values handed out per object, so two distinct objects colliding is unlikely but permitted. Equal
identity hashes are **necessary but not sufficient** for identity. The 127 case therefore rests on the
`==` result — which *is* the identity test, and returned `true` — with the matching hash as
corroboration. (Mark-word mechanics: [`../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`](../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md).)

Now prove the boundary is the **cache's** and not a property of the number 127. If 127 were
privileged, the flip would sit at 127 in both directions. It does not — measured:

```
Integer.valueOf(-128) == Integer.valueOf(-128)  -> true
Integer.valueOf(-129) == Integer.valueOf(-129)  -> false
```

The flip is at `-128`/`-129` low and `127`/`128` high — exactly `IntegerCache.low` and
`IntegerCache.high`. The boundary tracks the cache in both directions, which is what "`==` is
deciding on shared instances, nothing more" predicts. And the upper flip *moves* when you move the
cache: with `-XX:AutoBoxCacheMax=1000`, `Integer.valueOf(1000) == Integer.valueOf(1000)` is measured
**true** — same source, same operator, different answer, because `high` changed. A property of the
number 127 could not do that. (The flag's full behaviour, including why `-XX:AutoBoxCacheMax=50`
changes nothing, is [`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md).)

### Diagram

No diagram of my own here. `D-025` in [`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md) is the
picture for this concept — the 256-entry array with two references landing in the same slot and two
`new Integer` objects landing outside it — and the **D-026** table above is the map of where the
boundary sits per type. Re-drawing either would duplicate a sibling.

### A concrete example

The `[TRAP]` in 1.9.8 earns its keep here: the failure shape is not a crash but a wrong decision,
taken silently, on a value your fixtures never produced. `ClientRestrictions` decides whether a client
has hit the deposit-limit review threshold; `FundsLedger` matches an open reservation to a settlement.
Both compare boxed integers with `==`, and both pass every test.

```java
final class ReservationMatching {

    // Restriction identity is the pair (type, source); the count is a small integer.
    private final Map<RestrictionKey, Integer> restrictionCounts = new HashMap<>();
    // Stake reservations in MINOR units. Average stake is 4.20 -> 420 minor units.
    private final Map<IdempotencyKey, Integer> openReservationMinorUnits = new HashMap<>();

    void recordRestriction(RestrictionKey key, int count) {
        restrictionCounts.put(key, count);              // boxes via Integer.valueOf
    }
    void openReservation(IdempotencyKey key, int minorUnits) {
        openReservationMinorUnits.put(key, minorUnits); // boxes via Integer.valueOf
    }

    // BUG 1: works for every count a fixture ever uses.
    boolean needsDepositReview(RestrictionKey key, Integer threshold) {
        Integer count = restrictionCounts.get(key);
        return count == threshold;                    // reference comparison
    }

    // BUG 2: never works for a real stake.
    boolean settlesOpenReservation(IdempotencyKey key, Integer settledMinorUnits) {
        Integer open = openReservationMinorUnits.get(key);
        return open == settledMinorUnits;             // reference comparison
    }

    static void demonstrate() {
        var matching = new ReservationMatching();
        var depositLimited = new RestrictionKey(RestrictionType.DEPOSIT_LIMITED,
                                                RestrictionSource.SYSTEM_COMPLIANCE);
        var idempotencyKey = new IdempotencyKey("stake-2f9c-0001");

        matching.recordRestriction(depositLimited, 3);
        matching.openReservation(idempotencyKey, 420);

        // The fixture value. 3 is inside -128..127, so both boxes are cache slot 131.
        System.out.println(matching.needsDepositReview(depositLimited, 3));      // true

        // Production. 420 is outside the cache, so these are two distinct Integers.
        System.out.println(matching.settlesOpenReservation(idempotencyKey, 420)); // false
    }
}
```

`demonstrate` prints `true` then `false`. Both comparisons are the same line of code twice. The
arithmetic is the whole story: `3` is inside `-128..127`, so both `Integer.valueOf(3)` calls return
`IntegerCache.cache[3 + 128]` = slot 131, one object, and `==` is `true`. `420` is outside, so both
calls run `new Integer(420)`, two objects, and `==` is `false` — for a stake of 4.20, the platform's
measured average, on 2.8M reservations a day.

The fix is one word in each method, and the better fix is not to box:

```java
    boolean needsDepositReview(RestrictionKey key, int threshold) {
        Integer count = restrictionCounts.get(key);
        return count != null && count == threshold;   // mixed ==: unboxes, real value comparison
    }

    boolean settlesOpenReservation(IdempotencyKey key, int settledMinorUnits) {
        Integer open = openReservationMinorUnits.get(key);
        return open != null && open.intValue() == settledMinorUnits;
    }
```

Both parameters become `int`, so each `==` is now a **mixed** comparison: one wrapper, one primitive,
which JLS §15.21.1 resolves by unboxing the wrapper and comparing numerically. The `null` guard is not
decoration — unboxing `null` throws, and that is [`01c-unboxing-null.md`](01c-unboxing-null.md)'s
subject. Measured, the mixed form is a real value comparison even far outside the cache:

```
Integer big1 = 1000, big2 = 1000;  int prim = 1000;
big1 == big2   (both wrappers) -> false
big1 == prim   (mixed)         -> true
```

Same value, same operator, opposite results, decided purely by whether both operands are references.

### The gotcha

The failure is **data-dependent and silent**: no stack trace, no log line, no exception, because `==`
returned a perfectly valid `boolean` and merely the wrong one. Downstream you see a wrong decision — a
`DEPOSIT_LIMITED` restriction never matched so a compliance review is never queued; an open
reservation the `FundsLedger` cannot find, so `SettleStake` books against nothing and the
`CLIENT_CASH_RESERVED` position drifts; an idempotency check reporting "not seen before" for a request
already processed, letting a duplicate deposit through.

It is worse than a plain bug, because its visibility is inversely correlated with the value range: it
is invisible for small numbers, which is exactly what fixtures and demos use. Retry counts (0..3),
restriction counts (0..10) and disposition digits all live inside the cache. Money in minor units does
not.

**Insight:** the cache is not what makes `==` correct in the small range — it is what makes `==`
*fail to fail* there. The operator behaves identically at 3 and at 420; only the number of objects
differs. So the code that "worked" was never right, and no amount of testing over small values will
tell you.

**Pitfall:** the wrong belief is "`==` on `Integer` compares values, except for some edge case above
127". The symptom is a comparison that passes every test and silently returns `false` in production for
any value outside `-128..127`. The fix: `equals`, or unbox one side so the comparison is numeric, or
best, keep the value an `int` and never create the identity question.

**Interview:** *"Why is `Integer.valueOf(127) == Integer.valueOf(127)` true but 128 false?"* — Both
calls at 127 return `IntegerCache.cache[127 + 128]`, the same object, so reference equality holds; at
128 the bounds check fails and each call runs `new Integer(128)`, two objects, so it does not.
Measured, the identity hashes are `692404036` for both at 127 and `1670675563`/`723074861` at 128.
The boundary is `IntegerCache.high`, not the number 127 — the same flip happens between `-128` and
`-129`, and raising `high` with `-XX:AutoBoxCacheMax=1000` makes 1000 compare `true`.

**Interview:** *"When is `==` on a wrapper ever correct?"* — When you intend an identity test:
probing whether two references are the same object, comparing against a sentinel you control, or
asserting a cache returned a shared instance. Also when exactly one operand is a primitive, because
JLS §15.21.1 then unboxes the other into a genuine numeric comparison — though it throws if the
wrapper is `null`. For value comparison of two wrappers, never.

> **Definition.** `==` between two wrapper references is reference equality, unconditionally; the
> wrapper cache determines whether two equal values happen to be the same object, which is why the
> comparison appears to work inside `-128..127` and stops working outside it.

---

## Supporting facts

**`Boolean.TRUE` / `Boolean.FALSE` are the mechanism, so name them.** `Boolean.valueOf(b)` is
`(b ? TRUE : FALSE)` over those two `public static final` fields. Prefer `Boolean.TRUE.equals(flag)`
to `flag` in a condition when `flag` may be `null`. Gotcha: `==` against `Boolean.TRUE` genuinely is
safe, because there are only two instances in the JVM — which is exactly why the `==` habit survives
long enough to bite on `Integer`.

**`Integer.TYPE` is the primitive class, not the wrapper class.** Measured: `Integer.TYPE` prints
`int` and `Integer.TYPE == int.class` is `true`. Gotcha: it is *not* `Integer.class`, so reflection
code that conflates them silently fails to match a signature.

**All eight wrappers are `final`, immutable and `@jdk.internal.ValueBased`** — the wrapped value is a
`private final` field with no setter, which is the precondition that makes sharing instances safe at
all. Gotcha: it is also why `synchronized` on a box is a correctness bug, since the monitor may be a
process-wide shared instance; see
[`03f-internals-monitors-and-valhalla.md`](03f-internals-monitors-and-valhalla.md).

> **Definition.** The wrappers are `final`, immutable, value-based classes whose shared instances are
> exposed as cache slots (`Integer` and four others) or as named constants (`Boolean`).

---

## Pitfalls

### Comparing two boxed ledger amounts with `==` because every fixture value was under 128

**Wrong**

```java
// FundsLedger reconciliation. Amounts are Integer minor units.
boolean reservationMatches(Integer openMinorUnits, Integer settledMinorUnits) {
    return openMinorUnits == settledMinorUnits;
}

// The test fixture: a 0.03 bonus portion from the canonical 3.33 stake split.
System.out.println(reservationMatches(3, 3));        // true  -- test passes
// Production: the average stake, 4.20.
System.out.println(reservationMatches(420, 420));    // false -- reservation never matches
```

**Right**

```java
// Best: do not box. Keep minor units as int and the identity question cannot arise.
boolean reservationMatches(int openMinorUnits, int settledMinorUnits) {
    return openMinorUnits == settledMinorUnits;
}

// If the values arrive boxed (a Map value, a nullable column), compare values explicitly.
boolean reservationMatches(Integer openMinorUnits, Integer settledMinorUnits) {
    return Objects.equals(openMinorUnits, settledMinorUnits);   // null-safe value comparison
}

System.out.println(reservationMatches(Integer.valueOf(420), Integer.valueOf(420)));  // true
```

`Objects.equals` is the form for when either side may be `null`: it short-circuits on reference
equality, handles `null` on both sides, and otherwise delegates to `Integer.equals`.

**Why people believe it:** `==` on the primitive `int` is not only correct but idiomatic, and after
autoboxing the source line looks **identical** — nothing at the call site says a conversion happened,
because the `invokestatic Integer.valueOf` only shows up under `javap`. The programmer reads
`openMinorUnits == settledMinorUnits`, recognises the shape of a correct integer comparison, and never
asks what the static types are.

### Assuming the boundary is ±128 for every wrapper, and applying it to `Character` or `Short`

**Wrong**

```java
// Disposition digit from a status code such as AA-650 DOCUMENTS_REFERRED, and a
// delimiter in an address line. "Cached up to 128" is the assumed rule.
boolean isReferredDisposition(Character disposition) {
    return disposition == Character.valueOf('5');   // reference comparison
}

boolean isSeparator(Character candidate) {
    return candidate == Character.valueOf('·');  // MIDDLE DOT, code unit 183
}

System.out.println(isReferredDisposition('5'));        // true  -- '5' is code unit 53
System.out.println(isSeparator('·'));             // false -- 183 is above 127
// And the assumed 128 boundary is itself wrong:
System.out.println(Character.valueOf((char) 128) == Character.valueOf((char) 128)); // false
```

**Right**

```java
boolean isReferredDisposition(char disposition) {
    return disposition == '5';            // primitives: a real value comparison
}

boolean isSeparator(char candidate) {
    return candidate == '·';
}

// If the value must stay boxed:
boolean isSeparatorBoxed(Character candidate) {
    return Character.valueOf('·').equals(candidate);   // null-safe, value-based
}
```

**Why people believe it:** the number 128 is what everyone remembers from the `Integer` example, and
it is remembered as a magnitude rather than as an inclusive upper bound of 127. `Character` breaks
that memory twice: its cached range is `0..127` with **no negative half** (a `char` is unsigned, so
`CharacterCache` sizes itself `127 + 1` = 128 entries and `valueOf` tests only `c <= 127`), and 128
is the first *uncached* value, not the last cached one. Both errors are invisible under ASCII test
data and surface the first time a non-ASCII code unit reaches the comparison.

### Adding a defensive `equals` on `Byte` "because the cache might not cover it"

**Wrong**

```java
// A DocumentVerification retry counter, 0..3, held as Byte. The author reasons
// "Byte caches -128..127 like Integer, so values outside that need equals" --
// incoherent, since no byte exists outside -128..127 -- then inverts it:
boolean sameAttemptCount(Byte left, Byte right) {
    return left == right;   // "safe, Byte always caches" -- true today, guaranteed only to 127
}
```

**Right**

```java
boolean sameAttemptCount(byte left, byte right) {
    return left == right;                 // primitives; no identity question exists
}

boolean sameAttemptCount(Byte left, Byte right) {
    return Objects.equals(left, right);   // contract-guaranteed for every byte value
}
```

The `==` version is not observably broken on JDK 21.0.7 — `Byte.valueOf` has no bounds check, so
every `byte` value comes from the 256-entry `ByteCache` and `==` on equal `Byte` values is *always*
`true`. That is worse than an outright bug: a `==` that will never fail a test, resting on a property
`Byte.valueOf`'s javadoc does not promise (it guarantees caching only over `-128..127`, the JLS
mandate), and immediately wrong when copy-pasted onto `Short` or `Integer`.

**Why people believe it:** `Byte`'s cached range is quoted as `-128..127`, identical to `Integer`'s,
so it reads as "same rule, same risk". Nobody notices that for `byte` those bounds are the type's own
limits and the check is therefore vacuous — the rule generalises in wording while behaving completely
differently.

### Reasoning about "the `Double` cache" at all

**Wrong**

```java
// Comparing the major-unit view of a stake. The author assumes small doubles are cached.
boolean sameStake(Double left, Double right) {
    return left == right;
}
System.out.println(sameStake(4.20, 4.20));   // false -- no Double cache exists
System.out.println(sameStake(0.0, 0.0));     // false -- not even for zero
System.out.println(Double.valueOf(0.0).equals(-0.0));  // false -- and equals surprises too
```

**Right**

```java
// Money is never a double in this domain: Money(BigDecimal amount, Currency currency),
// or int minor units. A genuine double comparison unboxes and states its tolerance.
boolean sameStakeMinorUnits(int left, int right) {
    return left == right;
}
```

**Why people believe it:** "wrappers are cached" is stated as a property of wrappers rather than of
five particular classes, and `4.20` and `0.0` *feel* small in exactly the way `3` does. There is no
cache class for `Float` or `Double`, no bounds check in their `valueOf`, and no archived subgraph in
the CDS log — so `==` on two equal-valued boxes is `false` for every value, with no test-passing range
to hide the mistake in. IEEE 754 makes even the correct form subtle: `-0.0` is `equals`-distinct from
`0.0` while `0.0 == -0.0` is `true` as primitives, and `NaN` inverts it.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Wrappers that cache | `Byte`, `Short`, `Integer`, `Long`, `Character`, `Boolean` — six of eight, five via a cache class |
| Wrappers that never cache | `Float`, `Double` |
| `Byte` cached range | `-128..127` — the entire type; 256 instances |
| `Byte.valueOf` bounds check | none at all; the fallback `new Byte(b)` path does not exist |
| `Short` cached range | `-128..127`; 256 instances; bounds are literals in `valueOf` |
| `Integer` cached range | `-128..127` by default; 256 instances; bounds are `IntegerCache.low`/`high` fields |
| `Long` cached range | `-128..127`; 256 instances; bounds are literals, no property read |
| `Character` cached range | `0..127`; **128** instances; one-sided, no offset in the index |
| `Boolean` cache | no cache class; `public static final Boolean TRUE` / `FALSE`, 2 instances |
| Instance-count arithmetic | inclusive `low..high` holds `high − low + 1`: `-128..127` = 256, `0..127` = 128 |
| Only tunable wrapper | `Integer`, upper bound only |
| The tuning flag | `-XX:AutoBoxCacheMax` (C2 product flag, default 128) or `-Djava.lang.Integer.IntegerCache.high` |
| `IntegerCache.low` | `-128`, not configurable by any means |
| CDS archived cache subgraphs | `Integer`, `Long`, `Byte`, `Short`, `Character` — measured; **no `Boolean` entry** |
| JLS mandate | §5.1.7: `boolean`, `byte`, `char` `\u0000..\u007f`, `short`/`int` `-128..127` must box to shared references |
| JDK's own comment | `// range [-128, 127] must be interned (JLS7 5.1.7)` in `IntegerCache` |
| `==` on two wrappers | reference equality, always; never overloadable (JLS §15.21.3) |
| `==` with one primitive operand | unboxes the wrapper, numeric comparison (JLS §15.21.1); throws NPE if the wrapper is `null` |
| `Integer a = 127, b = 127; a == b` | `true` (measured; `identityHashCode` `692404036` both) |
| `Integer c = 128, d = 128; c == d` | `false` (measured; `1670675563` and `723074861`) |
| `Integer.valueOf(-128) == Integer.valueOf(-128)` | `true` (measured) |
| `Integer.valueOf(-129) == Integer.valueOf(-129)` | `false` (measured) — the low boundary, proving it is the cache |
| `Character.valueOf((char) 128) == itself` | `false` (measured) — 128 is the first uncached code unit |
| `Short`/`Long` `valueOf(128) == itself` | `false` (measured) |
| `Float.valueOf(1.0f) == itself` | `false` (measured) |
| `Double.valueOf(1.0) == itself` | `false` (measured) |
| `Double.valueOf(0.0).equals(-0.0)` | `false` (measured) — `equals` compares `doubleToLongBits` |
| `Integer big=1000; int prim=1000; big == prim` | `true` (measured) — mixed comparison unboxes |
| `Integer big1=1000, big2=1000; big1 == big2` | `false` (measured) |
| Value comparison of two wrappers | `a.equals(b)`, or `Objects.equals(a, b)` when either may be `null` |
| Identity-hash proof strength | different hashes prove different objects; equal hashes do **not** prove identity |
| `Integer.TYPE` | `int.class`; `Integer.TYPE == int.class` is `true`, `Integer.TYPE.equals(Integer.class)` is `false` |
| All eight wrappers | `final`, immutable, `@jdk.internal.ValueBased` |
| Silent-failure range | inside `-128..127` a wrapper `==` bug never fails a test |

---

## Self-test

**Q1.** Which of the eight wrappers cache, and what exactly is the range and instance count for each?

<details><summary>Answer</summary>

Six of the eight produce shared instances, five of them through a dedicated cache class. `Byte`
caches `-128..127`, which is the entire `byte` type, 256 instances. `Short` caches `-128..127`, 256
instances. `Integer` caches `-128..127` at the default, 256 instances, and is the only one whose
upper bound is configurable. `Long` caches `-128..127`, 256 instances. `Character` caches `0..127`,
**128** instances — one-sided, because `char` is unsigned and cannot be negative. `Boolean` has no
cache class at all: `valueOf` is `(b ? TRUE : FALSE)` over two `public static final` fields, so 2
instances. `Float` and `Double` cache nothing whatsoever — no cache class, no bounds check, no
archived subgraph. The counts are arithmetic: an inclusive range `low..high` holds `high − low + 1`
values, so `-128..127` is 256 and `0..127` is 128.

</details>

**Q2.** Why does `Byte.valueOf` have no bounds check when `Short.valueOf` and `Long.valueOf` do?

<details><summary>Answer</summary>

Because for `byte` the check would be dead code. `ByteCache` sizes its array `-(-128) + 127 + 1` =
256 entries, and `valueOf` indexes it with `(int) b + 128`. A `byte` ranges `-128..127`, so that
index is in `0..255` for every value the type can hold — there is no `byte` outside the cached range,
so no fallback is reachable and `Byte.valueOf` is a two-line array read that cannot allocate. `short`
and `long` are far wider than the 256-value window, so their checks are live and their
`new Short(s)` / `new Long(l)` fallbacks run for the overwhelming majority of values. Note the bounds
in `Short.valueOf` and `Long.valueOf` are literals `-128` and `127`, not fields, which is also why
neither is tunable.

</details>

**Q3.** `Integer a = 127, b = 127; a == b` is `true`, but at 128 it is `false`. Walk through why, and
prove the boundary is the cache and not something about 127.

<details><summary>Answer</summary>

`Integer a = 127` is a boxing conversion in assignment context, which `javac` desugars to
`Integer.valueOf(127)`. `valueOf` tests `i >= IntegerCache.low && i <= IntegerCache.high`; 127 passes,
so both calls return `IntegerCache.cache[127 + 128]` — the same array slot, the same object — and `==`,
which is reference equality, is `true`. At 128 the check fails, each call runs `new Integer(128)`, and
the two distinct objects make `==` `false`. Measured on JDK 21.0.7: at 127 both `identityHashCode`
values are `692404036`; at 128 they are `1670675563` and `723074861`.

To show it is the cache and not the number: the same flip happens at the *low* end, where
`Integer.valueOf(-128) == Integer.valueOf(-128)` is `true` and `Integer.valueOf(-129) ==
Integer.valueOf(-129)` is `false`. Those two positions are exactly `IntegerCache.low` and
`IntegerCache.high`. And the upper flip moves: with `-XX:AutoBoxCacheMax=1000`,
`Integer.valueOf(1000) == Integer.valueOf(1000)` is measured `true`. A property of the literal 127
could not produce either of those results.

</details>

**Q4.** What does `System.identityHashCode` actually prove about identity, and what does it not?

<details><summary>Answer</summary>

Two **different** identity hashes prove two different objects, because one object has exactly one
identity hash for its whole lifetime — so the `1670675563` / `723074861` pair at 128 is conclusive
proof of non-identity, independent of the `==` result. Two **equal** identity hashes prove nothing on
their own: the identity hash is a 31-bit value, and two distinct objects colliding is unlikely but
entirely permitted. Equal identity hashes are necessary but not sufficient for identity. So the 127
case rests on the `==` result, which *is* the identity test and returned `true`, with the matching
`692404036` as corroboration rather than as the argument. Quoting the matching hash alone would be a
weaker claim than it sounds.

</details>

**Q5.** A reviewer says "`Java`'s `==` is broken for `Integer`". What is the precise correction?

<details><summary>Answer</summary>

Nothing is broken; two correct rules collide. `==` is not overloadable in Java, and JLS 21 §15.21.3
defines it for reference operands as reference equality — the operands denote the same object, or both
are `null`. `Integer` has no hook to redefine it, and giving it one would break identity comparison
for every reference type. Separately, `Integer.valueOf` must share instances over `-128..127` because
JLS §5.1.7 requires boxing to be reference-stable there. Each rule is right; together they yield an
operator that appears to compare values over exactly the range that appears in test fixtures. The
correction to draw is behavioural, not linguistic: `==` on two wrappers is an identity test, so use
`equals` (or `Objects.equals` for null safety) for value comparison, or keep the value primitive.

</details>

**Q6.** When is `==` on a wrapper genuinely correct?

<details><summary>Answer</summary>

Three cases. First, when you actually mean identity: probing whether two references are the same
object, comparing against a sentinel instance you control, or asserting that a cache handed back a
shared instance. Second, when exactly one operand is a primitive — JLS §15.21.1 makes that a numeric
comparison by unboxing the wrapper, so `big1 == prim` is measured `true` at 1000 while
`big1 == big2` is `false`; the caveat is that it throws `NullPointerException` if the wrapper is
`null`. Third, `Boolean`, where there are only ever two instances in the JVM, so `==` against
`Boolean.TRUE` is safe — and that safety is precisely why the habit survives long enough to bite on
`Integer`. For value comparison of two wrapper references, never.

</details>

**Q7.** Why do `Float` and `Double` have no cache, and why would adding one be a bad idea?

<details><summary>Answer</summary>

There is no useful finite set of "small" floating-point values — between `0.0` and `1.0` alone there
are roughly 2^62 distinct `double` values, so a 256-entry window would capture almost nothing that
real code boxes. The values that would collide are a handful of literals, which are rarely compared
by identity. And identity reuse there is actively hazardous, because IEEE 754 has values whose
equality does not behave like a value type's: measured, `Double.valueOf(0.0).equals(-0.0)` is `false`
even though `0.0 == -0.0` is `true` as primitives, and `NaN` inverts it — `NaN != NaN` as primitives
while `Double.valueOf(Double.NaN).equals(Double.NaN)` is `true`. A cache would have to hard-code
whether `0.0` and `-0.0` share an instance, and both answers are defensible. Consequently `==` on two
`Double` boxes is `false` for every value including zero, with no test-passing range to hide a
mistake in.

</details>

**Q8.** Why is the wrapper `==` bug considered worse than an average bug, and what does it look like
in production?

<details><summary>Answer</summary>

Because its visibility is inversely correlated with the value range, and because it never throws.
`==` returns a valid `boolean`, just the wrong one — no exception, no stack trace, no log line. The
values that live inside `-128..127` are exactly the values fixtures and demos use: retry counts 0..3,
restriction counts 0..10, status dispositions, phase digits. The values that live outside are money
in minor units — a 4.20 average stake is 420. So the test suite is systematically blind to it. In
QuizStakes the symptoms are a `DEPOSIT_LIMITED` restriction that is never matched so a compliance
review is never queued, an open reservation the `FundsLedger` cannot find so `SettleStake` books
against nothing and `CLIENT_CASH_RESERVED` drifts, and an idempotency check that reports "not seen
before" for a request already processed, admitting a duplicate deposit.

</details>

**Q9.** Two engineers hold opposite wrong beliefs about `Byte`. What are they, and what should each
write?

<details><summary>Answer</summary>

One believes `Byte` behaves like `Integer` at a boundary and adds a defensive `equals` for the values
"outside the cache" — an incoherent worry, because there are no `byte` values outside `-128..127`. The
other draws the opposite conclusion from the same premise and writes `==`, reasoning "`Byte` always
caches". On JDK 21.0.7 the second one is not observably broken: `Byte.valueOf` has no bounds check, so
every `byte` value comes from the 256-entry `ByteCache` and `==` on equal `Byte` values is always
`true`. That is worse than a visible bug — a `==` that will never fail a test, resting on a property
`Byte.valueOf`'s javadoc does not promise (it guarantees caching only over `-128..127`, because that
is the JLS mandate), and immediately wrong when copy-pasted onto `Short` or `Integer`. Both should use
`byte` primitives, or `Objects.equals` if the values must stay boxed.

</details>

---

## Open questions

- None. Every claim in this file is either quoted from JDK 21.0.7 source, measured on JDK 21.0.7, or
  cited to the JLS.

---

**Leaves covered:** 1.9.6, 1.9.7, 1.9.8 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-026 (table)
**Target version:** Java 21 LTS
**Lines:** 898
