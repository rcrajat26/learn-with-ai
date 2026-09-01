# 03 Java Core — Cast expressions and comparison — BASICS (§1.6, 1.6.14, 1.6.15)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Compound assignment, short-circuit and bitwise operators](02a-assignment-and-bitwise.md) · Next: [The conditional operator and pattern instanceof](02c-conditional-operator.md)

Every bytecode listing and every printed value in this file was captured by compiling with `javac --release 21` and disassembling with `javap -c` on JDK 25 (`--release 21` fixes the class-file version and the language level, and none of these instructions changed between 21 and 25). Where a listing is reconstructed rather than captured, the text says so.

This part covers the two pieces of syntax that look like one operation each and are not: the three unrelated mechanisms hiding behind cast syntax, and the three meanings of `==`. The precedence ladder these operators sit on is in [02-operators-and-expressions.md](02-operators-and-expressions.md); compound assignment's hidden cast — the same narrowing conversion, inserted without you writing it — is in [02a-assignment-and-bitwise.md](02a-assignment-and-bitwise.md).

---

## 1. Cast expressions: three different operations, one syntax (1.6.14)

**Concept.** `(T) x` is one piece of syntax covering three unrelated mechanisms. Which one you get depends entirely on the static types, and they have three different failure modes: none, a runtime exception, and silent data loss.

**How it works.**

| Cast kind | Example | Checked | Failure mode |
|---|---|---|---|
| Reference upcast (widening) | `LedgerEvent e = (LedgerEvent) deposit;` | at compile time only | none; the cast is redundant |
| Reference downcast (narrowing) | `Deposit d = (Deposit) event;` | at run time, `checkcast` | `ClassCastException` |
| Primitive widening | `long minorUnits = (long) attemptCount;` | neither | none for integral widening; `int`→`float` and `long`→`float`/`double` can lose precision |
| Primitive narrowing | `byte retries = (byte) 310;` | neither | silent truncation to 54 |
| Boxing/unboxing cast | `Integer boxed = (Integer) 3;` | at run time for the unbox direction | `NullPointerException` when unboxing null |

The reference downcast emits a `checkcast` instruction; if the runtime type is not assignable, the JVM throws `ClassCastException` at that instruction, not later. The primitive narrowing cast emits `i2b`, `i2c`, `i2s`, `l2i`, `d2i` or similar, and none of those instructions can fail — they simply discard bits. That asymmetry is the whole safety story: **reference casts are checked, primitive casts are not.**

```java
sealed interface Instrument permits Card, BankAccount {}
record Card(String panLast4, String scheme) implements Instrument {}
record BankAccount(String sortCode, String accountNumber) implements Instrument {}

final class CastDemo {
    static String panOf(Instrument instrument) {
        Card card = (Card) instrument;   // downcast: checked, may throw
        return card.panLast4();
    }

    public static void main(String[] args) {
        Instrument card = new Card("4242", "VISA");
        System.out.println(panOf(card));                      // 4242

        Instrument bank = new BankAccount("20-00-00", "55779911");
        try {
            System.out.println(panOf(bank));
        } catch (ClassCastException e) {
            System.out.println("CCE: " + e.getMessage());
            // class BankAccount cannot be cast to class Card
        }

        Object upcast = (Object) card;                        // upcast: always safe, always redundant
        System.out.println(upcast instanceof Card);           // true

        System.out.println((byte) 310);                       // 54  -- silent, unchecked
        System.out.println((int) 3.99);                       // 3   -- truncates toward zero
        System.out.println((int) -3.99);                      // -3
        System.out.println((char) 98);                        // b

        Integer nullCount = null;
        try {
            int n = (int) nullCount;                          // unboxing cast
            System.out.println(n);
        } catch (NullPointerException e) {
            System.out.println("unboxing cast of null: NPE");
        }
    }
}
```

**Pitfall:** treating a primitive cast as a safety measure. `(byte) wireValue` never complains; it just returns the wrong number. On a `byte retries` field it turns 310 into 54 and 200 into -56. Use `Math.toIntExact`, an explicit range check, or a wider field — the cast is an assertion you are making, not one the runtime checks. The full conversion rules are in [03-conversions-and-contexts.md](03-conversions-and-contexts.md).

**Interview:** "Which casts can fail at runtime?" — reference downcasts (`ClassCastException`) and unboxing casts of null (`NullPointerException`). Primitive casts never throw; they truncate.

> A cast expression performs a reference conversion checked at run time, an unchecked primitive conversion that may truncate, or a boxing/unboxing conversion — determined entirely by the static types involved.

---

## 2. `==` on primitives, references, and mixed operands (1.6.15)

**Concept.** `==` has two meanings and a third, dangerous, hybrid. On two primitives it compares values. On two references it compares identity — the same object, not an equal one. When one side is a primitive and the other a wrapper, the wrapper is unboxed and you silently get the value comparison, which is usually right and occasionally throws.

**How it works.** JLS 15.21 splits into three cases. If either operand is of numeric type, it is a *numeric equality* comparison: binary numeric promotion applies, so a wrapper operand is unboxed. If both are `boolean`/`Boolean`, likewise. Otherwise both must be reference types and it is a *reference equality* comparison, no conversion.

Captured behaviour:

```
Integer x = 1000, y = 1000;   x == y      ->  false   (two distinct objects)
Integer p = 100,  q = 100;    p == q      ->  true    (both from the Integer cache)
int prim = 1000;              x == prim   ->  true    (x is unboxed; value comparison)
Integer nul = null;           nul == prim ->  NullPointerException
```

The `100` versus `1000` split is `Integer.valueOf`'s cache, which by specification covers at least -128 to 127. The lesson is not the boundary; it is that the boundary exists at all, so `==` on wrappers gives a data-dependent answer. The cache's exact shape and its configuration are in [../wrappers-and-boxing/01-basics.md](../wrappers-and-boxing/01-basics.md).

**Pitfall:** comparing two `Money`, `ClientId` or `IdempotencyKey` values with `==` and having it work in tests because the same instance was threaded through. Record types get a value-based `equals` for free, but `==` still compares identity. Symptom: an idempotency check that passes locally and lets a duplicate `DEP-301 CAPTURED` through in production, because the deserialised key is a different object. Fix: `equals` for every reference type, `==` only for primitives, enum constants and deliberate identity checks.

```java
import java.math.BigDecimal;
import java.util.Currency;

final class EqualityDemo {
    record IdempotencyKey(String value) {}
    record Money(BigDecimal amount, Currency currency) {}

    public static void main(String[] args) {
        IdempotencyKey a = new IdempotencyKey("dep-2026-08-29-0001");
        IdempotencyKey b = new IdempotencyKey("dep-2026-08-29-0001");
        System.out.println(a == b);          // false: distinct objects
        System.out.println(a.equals(b));     // true: record equals compares components

        Money m1 = new Money(new BigDecimal("3.33"), Currency.getInstance("GBP"));
        Money m2 = new Money(new BigDecimal("3.330"), Currency.getInstance("GBP"));
        System.out.println(m1.equals(m2));   // false: BigDecimal.equals compares scale too

        Integer big1 = 1000, big2 = 1000;
        System.out.println(big1 == big2);    // false
        Integer small1 = 100, small2 = 100;
        System.out.println(small1 == small2); // true: Integer cache
        int primitive = 1000;
        System.out.println(big1 == primitive); // true: big1 unboxed

        Integer missing = null;
        try {
            System.out.println(missing == primitive);
        } catch (NullPointerException e) {
            System.out.println("mixed == with null wrapper: NPE");
        }

        double nan = 0.0 / 0.0;
        System.out.println(nan == nan);      // false: IEEE-754 NaN is unequal to itself
        System.out.println(-0.0 == 0.0);     // true, though Double.equals says otherwise
    }
}
```

**Insight:** `m1.equals(m2)` returning false for 3.33 versus 3.330 is not an `==` problem at all — it is `BigDecimal.equals` comparing unscaled value *and* scale. In a `Money` record, `equals` is component-wise, so it inherits that. Use `compareTo() == 0` when 3.33 and 3.330 must be the same amount. The canonical QuizStakes split of a 3.33 stake into 0.33 bonus plus 3.00 cash relies on scale being preserved end to end, which is exactly why `Money` wraps `BigDecimal` rather than `double`.

**Interview:** "Why does `Integer a = 127, b = 127; a == b` differ from the same at 128?" — `Integer.valueOf` caches at least -128 to 127 and returns the same instance; above the cache each boxing creates a new object, and `==` compares identity.

The NaN and negative-zero behaviour of `==` on floating-point operands is developed in [01c-floating-point.md](01c-floating-point.md).

> `==` compares primitive values, unboxes when exactly one operand is numeric and the other a wrapper, and otherwise compares reference identity.

---

## Pitfalls

### A cast is how you check that a value fits

**Wrong**

```java
final class RetryCounterWrong {
    record Reservation(String roundId, byte attempt) {}

    static Reservation fromWire(String roundId, int attemptFromHeader) {
        // "the cast makes sure it fits in a byte"
        return new Reservation(roundId, (byte) attemptFromHeader);
    }

    public static void main(String[] args) {
        System.out.println(fromWire("round-42", 310).attempt());   // 54
        System.out.println(fromWire("round-42", 200).attempt());   // -56
        // the cap-at-3 check now passes forever on a counter reading -56
    }
}
```

**Right**

```java
final class RetryCounterRight {
    static final int MAX_ATTEMPTS = 3;

    record Reservation(String roundId, int attempt) {
        Reservation {
            if (attempt < 0 || attempt > MAX_ATTEMPTS) {
                throw new IllegalArgumentException("attempt out of range: " + attempt);
            }
        }
    }

    static Reservation fromWire(String roundId, int attemptFromHeader) {
        return new Reservation(roundId, attemptFromHeader);   // loud on bad input
    }

    public static void main(String[] args) {
        System.out.println(fromWire("round-42", 2).attempt());   // 2
        try {
            fromWire("round-42", 310);
        } catch (IllegalArgumentException e) {
            System.out.println("rejected: " + e.getMessage());   // attempt out of range: 310
        }
    }
}
```

**Why people believe it:** reference downcasts *are* checked — `(Card) instrument` throws `ClassCastException` when the type is wrong — so cast syntax reads as a runtime assertion. Primitive narrowing casts compile to `i2b`, `i2c`, `i2s`, `l2i` or `d2i`, none of which can fail; they discard bits and return a plausible number. The cast is a claim you are making on the compiler's behalf, and nothing verifies it. `Math.toIntExact`, `BigDecimal.longValueExact` or an explicit range check in the record's compact constructor are the checked equivalents.

### `==` is fine for value types like records

**Wrong**

```java
import java.util.HashSet;
import java.util.Set;

final class IdempotencyWrong {
    record IdempotencyKey(String value) {}

    static boolean alreadyCaptured(IdempotencyKey incoming, Set<IdempotencyKey> seen) {
        for (IdempotencyKey key : seen) {
            if (key == incoming) { return true; }    // identity, not value
        }
        return false;
    }

    public static void main(String[] args) {
        Set<IdempotencyKey> seen = new HashSet<>();
        IdempotencyKey stored = new IdempotencyKey("dep-2026-08-29-0001");
        seen.add(stored);
        // the deserialised copy of the same key is a different object
        IdempotencyKey redelivered = new IdempotencyKey("dep-2026-08-29-0001");
        System.out.println(alreadyCaptured(redelivered, seen));   // false: duplicate DEP-301 CAPTURED
    }
}
```

**Right**

```java
import java.util.HashSet;
import java.util.Set;

final class IdempotencyRight {
    record IdempotencyKey(String value) {}

    static boolean alreadyCaptured(IdempotencyKey incoming, Set<IdempotencyKey> seen) {
        return seen.contains(incoming);   // uses equals and hashCode
    }

    public static void main(String[] args) {
        Set<IdempotencyKey> seen = new HashSet<>();
        seen.add(new IdempotencyKey("dep-2026-08-29-0001"));
        IdempotencyKey redelivered = new IdempotencyKey("dep-2026-08-29-0001");
        System.out.println(alreadyCaptured(redelivered, seen));   // true: rejected as a duplicate
    }
}
```

**Why people believe it:** records advertise themselves as value classes and generate a component-wise `equals`, so "value semantics" gets over-generalised to the `==` operator. JLS 15.21.3 is unconditional: when neither operand is of numeric or boolean type, `==` is reference equality, and no amount of record-ness changes that. The bug hides in tests because a single instance is usually threaded through the whole test, so identity and equality coincide; it appears in production the first time the key arrives over the wire and is deserialised into a fresh object.

### `==` on two boxed integers compares their values

**Wrong**

```java
final class ReconciliationWrong {
    record LedgerEntry(String position, long minorUnits) {}

    // Counts arrive boxed from the store's aggregate query.
    static boolean countsAgree(Integer expected, Integer actual) {
        return expected == actual;                       // "both sides are numbers"
    }

    public static void main(String[] args) {
        System.out.println(countsAgree(127, 127));       // true  -- the fixture-sized test passes
        System.out.println(countsAgree(128, 128));       // false -- the production batch "fails" reconciliation

        Integer actual = 128;
        int expectedPrimitive = 128;
        System.out.println(actual == expectedPrimitive); // true  -- the asymmetry that hides the bug
    }
}
```

Captured output: `true`, `false`, `true`.

**Right**

```java
import java.util.Objects;

final class ReconciliationRight {
    record LedgerEntry(String position, long minorUnits) {}

    static boolean countsAgree(Integer expected, Integer actual) {
        return Objects.equals(expected, actual);         // value comparison, null-tolerant
    }

    static boolean countsAgree(int expected, int actual) {
        return expected == actual;                       // on primitives == already compares values
    }

    public static void main(String[] args) {
        System.out.println(countsAgree(Integer.valueOf(128), Integer.valueOf(128)));   // true
        System.out.println(countsAgree(null, Integer.valueOf(128)));                   // false, no NPE
        System.out.println(countsAgree(128, 128));                                     // true

        Integer left = 128, right = 128;
        System.out.println(left.equals(right));                   // true
        System.out.println(left.intValue() == right.intValue());  // true
        System.out.println(Integer.compare(left, right) == 0);    // true
    }
}
```

Captured output: `true`, `false`, `true`, `true`, `true`, `true`. Four fixes, in descending preference: keep the primitive so `==` means what you wanted; take the count as an `int` at the boundary and let the compiler unbox once; compare with `Objects.equals`, which never unboxes and treats a missing count as unequal rather than throwing; or unbox deliberately with `intValue()` or `Integer.compare(left, right) == 0` when you want the numeric comparison spelled out on the page.

**Why people believe it:** the same expression works and then stops working, and nothing in between changed except the data. `Integer.valueOf` is specified to cache instances for at least -128 to 127, so every count a hand-written fixture uses boxes to a shared instance and `==` reports identity that happens to coincide with equality. The first batch of 128 entries boxes to two distinct objects and the comparison flips to false — a reconciliation failure with no bad data behind it, on a code path with green tests. The rule is also genuinely hard to remember because it is asymmetric: `==` on two wrappers is reference equality (JLS 15.21.3, no conversion applied), but as soon as *one* operand is a primitive the comparison becomes numeric equality (JLS 15.21.1), the wrapper is unboxed, and the values *are* compared — which is why `actual == expectedPrimitive` above is true at 128 while `expected == actual` is false. So the wrapper-to-wrapper form is the broken one, the mixed form is the working one, and the mixed form is the one that throws on null. Neither reading generalises to the other.

### Mixing a wrapper and a primitive in `==` is just a value comparison

**Wrong**

```java
import java.util.HashMap;
import java.util.Map;

final class BonusCapWrong {
    enum Position { CLIENT_BONUS_RESERVED, CLIENT_CASH_AVAILABLE }
    static final int BONUS_CAP = 100;

    public static void main(String[] args) {
        Map<Position, Integer> reserved = new HashMap<>();
        Integer bonusReserved = reserved.get(Position.CLIENT_BONUS_RESERVED);   // null
        // "== unboxes, so this is a value comparison"
        System.out.println(bonusReserved == BONUS_CAP);   // NullPointerException
    }
}
```

**Right**

```java
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

final class BonusCapRight {
    enum Position { CLIENT_BONUS_RESERVED, CLIENT_CASH_AVAILABLE }
    static final int BONUS_CAP = 100;

    public static void main(String[] args) {
        Map<Position, Integer> reserved = new HashMap<>();
        Integer bonusReserved = reserved.get(Position.CLIENT_BONUS_RESERVED);   // null

        // Option A: give the absent case a value at the boundary.
        int settled = reserved.getOrDefault(Position.CLIENT_BONUS_RESERVED, 0);
        System.out.println(settled == BONUS_CAP);                   // false

        // Option B: compare without unboxing.
        System.out.println(Objects.equals(bonusReserved, BONUS_CAP)); // false, no NPE
    }
}
```

**Why people believe it:** the mixed form usually works, which is worse than never working. JLS 15.21.1 says that when *either* operand is of numeric type the comparison is numeric equality, so the wrapper is unboxed by an `Integer.intValue()` call — and that call throws on null. The two safe habits are to remove the nullability at the boundary with `getOrDefault`, or to compare two references with `Objects.equals`, which is null-tolerant and never unboxes. Note that `Objects.equals(bonusReserved, BONUS_CAP)` autoboxes the `int` argument rather than unboxing the wrapper, so a null simply compares unequal.

---

## Cheat sheet

| Item | Rule | Value / gotcha |
|---|---|---|
| Cast: reference up | compile-time only, emits nothing | always redundant |
| Cast: reference down | `checkcast`, runtime-checked | `ClassCastException` at that instruction |
| Cast: primitive widen | unchecked | `int`→`float`, `long`→`float`/`double` lose precision |
| Cast: primitive narrow | `i2b`/`i2c`/`i2s`/`l2i`/`d2i`, unchecked | silent truncation |
| `(byte) 310` | keeps low 8 bits | 54 |
| `(byte) 200` | keeps low 8 bits, sign bit set | -56 |
| `(int) 3.99` / `(int) -3.99` | truncate toward zero | 3 / -3 |
| Cast: unbox | `intValue()` style `invokevirtual` | `NullPointerException` on null |
| Checked range instead | `Math.toIntExact`, `longValueExact`, compact ctor | fails loud |
| `==` two primitives | value comparison | JLS 15.21.1 |
| `==` mixed prim/wrapper | wrapper unboxed (JLS 15.21.1) | null wrapper → NPE |
| `==` two wrappers | identity (JLS 15.21.3) | `Integer` cache covers at least -128..127 |
| `==` two records | identity, not components | use `equals` / `Objects.equals` |
| `==` on `double` | IEEE-754 | `NaN == NaN` false; `-0.0 == 0.0` true |
| `Double.equals` | bitwise-ish, not IEEE | disagrees with `==` on NaN and `-0.0` |
| `BigDecimal.equals` | compares scale too | 3.33 != 3.330; use `compareTo() == 0` |

---

## Self-test

**Q1.** Which cast expressions can fail at run time, and which fail silently? Give the instruction each compiles to.

<details><summary>Answer</summary>

Two kinds can throw. A reference downcast compiles to `checkcast`; if the object's runtime type is not assignable to the target, the JVM throws `ClassCastException` at that exact instruction, not at some later use of the variable. An unboxing cast compiles to an `intValue`/`doubleValue` style `invokevirtual`, which throws `NullPointerException` when the wrapper reference is null.

Primitive casts never throw. Narrowing compiles to `i2b`, `i2c`, `i2s`, `l2i`, `d2i` and friends, all of which simply discard bits or truncate toward zero: `(byte) 310` is 54, `(int) 3.99` is 3, `(int) -3.99` is -3. Primitive *widening* casts are redundant on integral types and can still lose precision on `int`→`float`, `long`→`float` and `long`→`double`, again with no diagnostic.

Reference upcasts are checked at compile time only and emit nothing at all — they are always redundant. The rule to carry away is the asymmetry: reference casts are checked, primitive casts are assertions the runtime never verifies, so a `(byte)` on wire data needs an explicit range check or `Math.toIntExact` beside it.

</details>

**Q2.** Two `IdempotencyKey` records with the same string compare `false` under `==` but `true` under `equals`. Two `Integer` values of 100 compare `true` under `==`, but two of 1000 compare `false`. Explain both.

<details><summary>Answer</summary>

Both are reference-equality comparisons under JLS 15.21.3: neither operand is of numeric or boolean type, so `==` compares object identity, not contents. Two separately constructed `IdempotencyKey` instances are distinct objects, so `==` is false; the record's generated `equals` compares components, so it is true.

For the `Integer` case, autoboxing routes through `Integer.valueOf`, which is specified to cache instances for at least the range -128 to 127. Both `100` literals therefore box to the *same* object and `==` is true. `1000` is outside the guaranteed cache, so each boxing allocates a new object and `==` is false. The lesson is not the boundary value but that `==` on wrappers gives a data-dependent answer — use `equals`, or unbox deliberately.

</details>

**Q3.** A wire frame carries an `int attempt` for a `Reservation`, and the retry counter is capped at 3. A colleague writes `(byte) attemptFromHeader` to "make sure it fits". Give two concrete values that break the cap check, and the checked alternative.

<details><summary>Answer</summary>

`(byte) 310` is 54 and `(byte) 200` is -56. Neither raises anything: the cast compiles to `i2b`, which keeps the low eight bits of the promoted `int`. 310 is `0000 0000 0000 0000 0000 0001 0011 0110`, whose low byte `0011 0110` is 54 with a clear sign bit. 200 is `1100 1000`, whose top bit is the byte's sign bit, so the value read back is 200 - 256 = -56.

The -56 case is the dangerous one, because a cap check written as `attempt > MAX_ATTEMPTS` passes for every negative value. A retry loop guarded that way never terminates on the retry count, and the audit trail shows a negative attempt number that looks like a serialisation bug rather than a cast.

The checked alternatives, in increasing strength: keep the field an `int` and range-check it in the record's compact constructor, which rejects 310 and -56 alike; use `Math.toIntExact` when narrowing from `long`, which throws `ArithmeticException` on overflow; or validate at the deserialisation boundary so the domain type can never hold an out-of-range attempt at all.

</details>

**Q4.** `double nan = 0.0 / 0.0;` — what do `nan == nan`, `Double.valueOf(nan).equals(Double.valueOf(nan))`, `-0.0 == 0.0` and `Double.valueOf(-0.0).equals(Double.valueOf(0.0))` each return?

<details><summary>Answer</summary>

`nan == nan` is **false**, `equals` on two NaN wrappers is **true**, `-0.0 == 0.0` is **true**, and `equals` on the two zero wrappers is **false**. Every pair disagrees.

`==` on floating-point operands implements IEEE-754 numeric comparison: NaN is unordered and compares unequal to everything including itself, while `+0.0` and `-0.0` are numerically equal. `Double.equals` is specified in terms of `doubleToLongBits`, which collapses all NaN encodings to one canonical bit pattern and keeps the sign bit of zero. So `equals` gives you reflexivity and a usable hash — which is what a `HashMap` key or a `List.contains` needs — at the price of no longer matching the operator.

The practical consequences: never write `if (rate == rate)` as a NaN test, use `Double.isNaN`; and be aware that a `Money`-adjacent value stored as a `double` in a collection can be findable by `equals` and not by `==`, or vice versa. This is one more reason the `Money` record wraps `BigDecimal`. The full IEEE-754 treatment is in [01c-floating-point.md](01c-floating-point.md).

</details>

**Q5.** `new Money(new BigDecimal("3.33"), GBP).equals(new Money(new BigDecimal("3.330"), GBP))` is false. Is that an `==` problem, and what should the code do instead?

<details><summary>Answer</summary>

It is not an `==` problem at all — both operands are the same reference here only incidentally; the call is `equals`. A record's generated `equals` compares components with `Objects.equals`, so the `Money` comparison delegates straight to `BigDecimal.equals`, which is documented to compare unscaled value *and* scale. `3.33` has unscaled value 333 at scale 2; `3.330` has unscaled value 3330 at scale 3. Different components, so unequal, even though both denote the same amount.

When two amounts must compare equal regardless of scale, compare with `amount().compareTo(other.amount()) == 0` and compare the currency separately, or normalise the scale at construction — for GBP, `setScale(2, RoundingMode.UNNECESSARY)`, which throws rather than silently rounding if the value carries more precision than the currency allows.

Normalising at construction is usually the right answer in this domain, because the canonical QuizStakes split of a 3.33 stake into 0.33 bonus plus 3.00 cash has to reconcile against ledger rows end to end, and a `StakeSplit` whose two `Money` components arrived at different scales will fail an equality-based reconciliation check while summing correctly. Scale is data here, not formatting.

</details>

---

## Open questions

- `Integer.valueOf`'s cache is specified to cover *at least* -128 to 127; the actual upper bound on HotSpot is settable via the `java.lang.Integer.IntegerCache.high` system property, and the effective default on the exact target JDK build is not verified here. `java -XX:+PrintFlagsFinal -version` does not report it because it is a Java-level property rather than a VM flag; reading `Integer.valueOf(i) == Integer.valueOf(i)` in a loop on the target build would settle it. No number in this file depends on the answer — every example uses 100 (inside the guaranteed range) and 1000 (outside it).
- *Effective Java* (3rd edition), Item 61 "Prefer primitive types to boxed primitives", is the standard reference for section 2. The item number is cited alongside its title so a wrong number is self-correcting against the book's table of contents.

---

**Leaves covered:** 1.6.14, 1.6.15 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 458
