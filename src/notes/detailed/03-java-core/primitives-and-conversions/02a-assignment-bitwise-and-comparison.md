# 03 Java Core — Assignment, bitwise operators and comparison — BASICS (§1.6, 1.6.6–1.6.9, 1.6.14, 1.6.15)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Operators: precedence, evaluation order and constant expressions](02-operators-and-expressions.md) · Next: [The conditional operator, instanceof and string concatenation](02b-conditional-and-string-concatenation.md)

Every bytecode listing and every printed value in this file was captured by compiling with `javac --release 21` and disassembling with `javap -c` on JDK 25 (`--release 21` fixes the class-file version and the language level, and none of these instructions changed between 21 and 25). Where a listing is reconstructed rather than captured, the text says so.

This part covers assignment and bit work: the cast that compound assignment inserts behind your back, the difference between skipping an operand and evaluating it anyway, the flags idiom, the three unrelated mechanisms hiding behind cast syntax, and the three meanings of `==`. The precedence ladder those operators sit on, and the left-to-right evaluation guarantee they rely on, are in [02-operators-and-expressions.md](02-operators-and-expressions.md).

---

## 1. Compound assignment hides a narrowing cast (1.6.6, 1.6.7)

**Concept.** `retries += 300` and `retries = retries + 300` look like the same statement written two ways. They are not. The compound form inserts a cast back to the left-hand side's type that you never wrote, so it compiles where the explicit form is rejected — and silently truncates.

**Why it exists.** Without the implicit cast, `+=` would be useless on every type narrower than `int`, because binary numeric promotion turns `byte + int` into `int`. `byte b = 0; b += 1;` would not compile. The language designers chose "always compiles, may truncate" over "never compiles on small types". The cost is a compile-time safety net removed exactly where narrow types live: wire-format fields, byte parsers, `char` cursors.

**How it works.** JLS 21 §15.26.2, *Compound Assignment Operators*:

> "A compound assignment expression of the form `E1 op= E2` is equivalent to `E1 = (T) ((E1) op (E2))`, where `T` is the type of `E1`, except that `E1` is evaluated only once."

Every clause matters. `(T)` is the hidden cast. `op` runs under normal binary numeric promotion, so both operands widen to at least `int` — the promotion rules themselves are in [03a-promotion-boxing-and-inference.md](03a-promotion-boxing-and-inference.md). "`E1` is evaluated only once" is what makes `positions[nextIndex()] += movement` safe — `nextIndex()` runs once, not twice — and it is the direct consequence of JLS 15.7.1's rule that evaluating the left-hand operand of a compound assignment both remembers the variable and saves its old value, quoted in [02-operators-and-expressions.md](02-operators-and-expressions.md).

Work the QuizStakes case through. A `byte retries` field comes off a wire format that packs a retry count into one octet.

- `retries = 10`, so bits `0000 1010`.
- `retries += 300` expands to `retries = (byte)(retries + 300)`.
- Promotion: `(int) 10 + 300 = 310`.
- 310 in 32 bits: `0000 0000 0000 0000 0000 0001 0011 0110`.
- `(byte)` keeps the low 8 bits: `0011 0110`.
- `0011 0110` = 32 + 16 + 4 + 2 = **54**. And the sign bit of that byte is 0, so the result is +54, not negative.

The explicit form `retries = retries + 300;` produces, captured verbatim from `javac --release 21`:

```
Bad.java:4: error: incompatible types: possible lossy conversion from int to byte
        retries = retries + 300;
                          ^
```

![D-017 — compound assignment's hidden narrowing cast](../diagrams/D-017-compound-assignment-cast.svg)

**D-017** — Left column: `retries += 300` expanded to `retries = (byte)(retries + 300)`, with 310's bit pattern and the low eight bits `0011 0110` boxed as 54. Right column: the same arithmetic written out longhand and rejected by the compiler. Second row: `rung += 1` on a `char`, yielding `'b'`. Look at the low-8-bits box first — that is the whole difference.

The bytecode makes the hidden cast visible as a single `i2b` instruction. Captured:

```
static byte compound();
  Code:
       0: bipush    10     // push 10
       2: istore_0         // retries == 10
       3: iload_0          // push retries, widened to int on the stack
       4: sipush    300    // push 300
       7: iadd             // 310
       8: i2b              // <-- the cast you did not write: int -> byte, keeps low 8 bits -> 54
       9: istore_0
      10: iload_0
      11: ireturn
```

`char` behaves identically with `i2c` instead of `i2b`. The stack has no `byte` or `char` slots — every integral value narrower than `int` lives on the stack as an `int`, and `i2b`/`i2c`/`i2s` are the explicit re-narrowing steps. Captured:

```
static char rung();
  Code:
       0: bipush    97     // 'a'
       2: istore_0
       3: iload_0
       4: iconst_1
       5: iadd             // 98
       6: i2c              // int -> char
       7: istore_0
       8: iload_0
       9: ireturn          // 'b'
```

```java
final class CompoundAssignmentDemo {
    static byte truncatingRetries() {
        byte retries = 10;
        retries += 300;        // == (byte)(10 + 300) == (byte) 310 == 54
        return retries;
    }

    static byte explicitFormRejected() {
        byte retries = 10;
        // retries = retries + 300;  // error: possible lossy conversion from int to byte
        retries = (byte) (retries + 300);   // legal once you accept the truncation in writing
        return retries;
    }

    static char nextRung() {
        char rung = 'a';
        rung += 1;             // == (char)(97 + 1) == 'b'
        // rung = rung + 1;    // error: possible lossy conversion from int to char
        return rung;
    }

    static int evaluatedOnce(int[] positions) {
        int cursor = 0;
        positions[cursor++] += 5;   // index expression runs ONCE: positions[0] += 5
        return cursor;              // 1, not 2
    }

    public static void main(String[] args) {
        System.out.println(truncatingRetries());        // 54
        System.out.println(explicitFormRejected());     // 54
        System.out.println(nextRung());                 // b
        int[] positions = { 100, 200 };
        System.out.println(evaluatedOnce(positions));   // 1
        System.out.println(positions[0] + "," + positions[1]); // 105,200
    }
}
```

**Pitfall:** "`x += y` is shorthand for `x = x + y`." It is shorthand for `x = (T)(x + y)`. On a `byte retries` parsed from a wire frame, `retries += deltaFromHeader` will wrap past 127 into negatives with no warning at all, so a retry counter reads `-102` in the audit trail and the cap-at-3 check passes forever. The fix on narrow types is to widen the field to `int` and range-check explicitly, or to write the cast by hand so a reader sees it.

**Insight:** the same hidden cast is why `int stakeCount = 0; stakeCount += 3.7;` compiles and leaves `stakeCount` at 3. The `double` result is cast back with `d2i`, which truncates toward zero. `+=` on an integral left-hand side will happily swallow a floating-point right-hand side.

**Interview:** "Why does `byte b = 10; b += 300;` compile when `b = b + 300;` does not?" — JLS 15.26.2 defines `E1 op= E2` as `E1 = (T)((E1) op (E2))`. The implicit `(byte)` cast satisfies assignment; the explicit form has no cast and fails the lossy-conversion check. The value is 54.

> Compound assignment expands to an assignment with an implicit cast back to the left-hand operand's type, and evaluates the left-hand operand exactly once.

---

## 2. Short-circuit versus eager boolean operators (1.6.8)

**Concept.** `&&` and `||` are the only Java operators that may leave an operand unevaluated. `&` and `|` on `boolean` operands compute the same truth table but always evaluate both sides. When the right-hand side is `ClientRestrictions.isBlocked(clientId, STAKE_BLOCKED)` — a call that hits the restrictions store — the difference is not stylistic.

**Why it exists.** Short-circuiting makes guard clauses expressible as a single expression: `account != null && account.isActive()` is safe only because the right side is skipped when the left is false. The eager forms survive on `boolean` for the rare case where you genuinely want both side effects, and because `&`/`|` must exist anyway for integral operands.

**How it works.** JLS 15.23 and 15.24: for `A && B`, `A` is evaluated; if it is `false`, the result is `false` and `B` **is not evaluated**. For `A || B`, if `A` is `true`, `B` is not evaluated. `A & B` and `A | B` on `boolean` fall under JLS 15.22.2 and evaluate both operands unconditionally. There is no `^^`; `^` on booleans is inherently eager because both operands are always needed.

The cost model at QuizStakes scale: stake reservations run 2.8M/day with a 1,200/sec peak. If the restrictions lookup is on the critical path of every reservation and the cheap in-memory check already answers "no restriction" for the vast majority of clients, ordering the operands cheap-first and using `&&` removes that call from the hot path entirely. The escape hatch — and the reason this is a tradeoff, not a free win — is that short-circuiting makes the number of calls data-dependent, so your latency histogram grows a long tail whenever the cheap predicate starts returning true more often, and any metric you increment inside the expensive predicate now under-counts.

| Form | Operands | Evaluates right side | Legal on `int` | Typical use |
|---|---|---|---|---|
| `&&` | `boolean` only | only if left is `true` | no | guard chains, cheap-first predicate ordering |
| `\|\|` | `boolean` only | only if left is `false` | no | early-accept chains |
| `&` | `boolean` or integral | always | yes | flag masking on integral; forced both-side evaluation on `boolean` |
| `\|` | `boolean` or integral | always | yes | flag setting on integral |
| `^` | `boolean` or integral | always | yes | flag toggling; "exactly one of" on booleans |

```java
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

final class ShortCircuitDemo {
    enum RestrictionType {
        DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED,
        WITHDRAWAL_HELD, SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED, SELF_EXCLUDED,
        COOLING_OFF, DORMANT_FROZEN
    }

    record ClientId(java.util.UUID value) {}

    static final class ClientRestrictions {
        private final Map<ClientId, Set<RestrictionType>> store;
        private int lookups = 0;

        ClientRestrictions(Map<ClientId, Set<RestrictionType>> store) { this.store = store; }

        boolean isBlocked(ClientId clientId, RestrictionType type) {
            lookups++;   // stands in for the network round trip
            return store.getOrDefault(clientId, Set.of()).contains(type);
        }

        int lookups() { return lookups; }
    }

    static boolean canStakeShortCircuit(boolean accountActive, ClientId id, ClientRestrictions r) {
        return accountActive && !r.isBlocked(id, RestrictionType.STAKE_BLOCKED);
    }

    static boolean canStakeEager(boolean accountActive, ClientId id, ClientRestrictions r) {
        return accountActive & !r.isBlocked(id, RestrictionType.STAKE_BLOCKED);
    }

    public static void main(String[] args) {
        ClientId id = new ClientId(java.util.UUID.randomUUID());
        ClientRestrictions cheap = new ClientRestrictions(
                Map.of(id, EnumSet.of(RestrictionType.STAKE_BLOCKED)));
        System.out.println(canStakeShortCircuit(false, id, cheap)); // false
        System.out.println("lookups after short-circuit: " + cheap.lookups()); // 0

        ClientRestrictions eager = new ClientRestrictions(
                Map.of(id, EnumSet.of(RestrictionType.STAKE_BLOCKED)));
        System.out.println(canStakeEager(false, id, eager));        // false
        System.out.println("lookups after eager: " + eager.lookups()); // 1

        // The classic guard: the eager form dereferences null.
        Set<RestrictionType> maybeNull = null;
        System.out.println(maybeNull != null && maybeNull.isEmpty()); // false, no NPE
        try {
            System.out.println(maybeNull != null & maybeNull.isEmpty());
        } catch (NullPointerException e) {
            System.out.println("eager & on a null guard: NPE");
        }
    }
}
```

**Pitfall:** "`&` and `&&` differ only in speed." They differ in *whether the right operand runs at all*, which changes correctness whenever the right operand can throw or mutate. `restriction != null & restriction.isActive()` throws `NullPointerException` on every null. Conversely, writing `&&` when you needed both side effects — `advanced = cursor.next() && cursor.next()` — silently skips the second advance. Fix: use `&&`/`||` for every predicate, and if you need both side effects, put them on separate statements where the intent is visible.

**Insight:** short-circuiting is why operand *order* is a performance decision, and JLS 15.7's left-to-right guarantee is what makes that decision reliable. Put the cheap, high-selectivity predicate on the left; the guarantee means the compiler cannot undo your choice.

**Interview:** "When is `&` on booleans not a bug?" — when both operands have side effects you need, or when you are deliberately avoiding a branch in extremely hot numeric code. In predicate chains it is a defect waiting for a null.

> `&&` and `||` skip their right operand when the left already decides the result; `&`, `|` and `^` on booleans always evaluate both.

---

## 3. Bitwise operators and the restriction-flags idiom (1.6.9)

**Concept.** QuizStakes has exactly ten `RestrictionType` values. Ten booleans fit in ten bits of one `int`, and "does this client have any blocking restriction" becomes one AND instruction instead of ten map lookups. `&` tests and intersects, `|` sets and unions, `^` toggles and diffs, `~` inverts a whole mask.

**Why it exists.** Before `EnumSet`, a bitmask was the only compact way to carry a set of flags across a boundary — a database column, a wire frame, a JNI call. It survives because the operations are single instructions and the representation is one machine word. `java.lang.reflect.Modifier`, `java.nio.channels.SelectionKey` and `Pattern`'s flags all still use it.

**How it works.** All four operate on `int` or `long` after unary numeric promotion; `byte`, `short` and `char` operands are promoted to `int` first. `~x` is `-x - 1` in two's complement, so `~0b1010` is `-11`, not `0b0101` — the inversion covers all 32 bits including the sign bit. Idioms:

| Intent | Expression | Note |
|---|---|---|
| define flag *n* | `1 << n` | `n` is masked to its low 5 bits for `int`, low 6 for `long` |
| set a flag | `flags \|= STAKE_BLOCKED` | idempotent |
| clear a flag | `flags &= ~STAKE_BLOCKED` | the `~` is why clearing reads awkwardly |
| toggle a flag | `flags ^= COOLING_OFF` | `x ^ x == 0`, so applying twice restores |
| test a flag | `(flags & STAKE_BLOCKED) != 0` | parentheses mandatory (level 8 beats level 9) |
| test all of a set | `(flags & set) == set` | not `!= 0`, which tests *any* |
| test none of a set | `(flags & set) == 0` | |
| symmetric difference | `a ^ b` | which flags changed between two snapshots |

The tradeoff: a mask is 4 bytes and one instruction, versus an `EnumSet` which is 1 object header plus a `long` plus a reference to the universe array. At 2.4M registered clients, a per-client `int` mask costs about 9.6 MB of primitive data against roughly 100 MB for `EnumSet` instances — but the mask has no type safety (nothing stops you OR-ing a `Movement` type constant into a restriction mask), no `toString`, and no iteration without hand-written bit scanning. The escape hatch is `EnumSet`, which is itself a `long` bitmask behind an interface: use `EnumSet` in the domain model and convert to an `int` only at the persistence or wire boundary. `EnumSet`'s internals are in guide **02 Java collections**.

```java
import java.util.EnumSet;
import java.util.Set;

final class RestrictionMaskDemo {
    enum RestrictionType {
        DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED,
        WITHDRAWAL_HELD, SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED, SELF_EXCLUDED,
        COOLING_OFF, DORMANT_FROZEN;

        int bit() { return 1 << ordinal(); }
    }

    static final int STAKE_BLOCKING_SET =
            RestrictionType.STAKE_BLOCKED.bit()
          | RestrictionType.ALL_BLOCKED.bit()
          | RestrictionType.SELF_EXCLUDED.bit()
          | RestrictionType.COOLING_OFF.bit();

    static int toMask(Set<RestrictionType> types) {
        int mask = 0;
        for (RestrictionType t : types) { mask |= t.bit(); }
        return mask;
    }

    static EnumSet<RestrictionType> fromMask(int mask) {
        EnumSet<RestrictionType> out = EnumSet.noneOf(RestrictionType.class);
        for (RestrictionType t : RestrictionType.values()) {
            if ((mask & t.bit()) != 0) { out.add(t); }
        }
        return out;
    }

    static boolean stakeBlocked(int mask)  { return (mask & STAKE_BLOCKING_SET) != 0; }
    static int     clear(int mask, RestrictionType t) { return mask & ~t.bit(); }
    static int     toggle(int mask, RestrictionType t) { return mask ^ t.bit(); }
    static int     changed(int before, int after) { return before ^ after; }

    public static void main(String[] args) {
        int mask = toMask(EnumSet.of(RestrictionType.DEPOSIT_LIMITED,
                                     RestrictionType.STAKE_BLOCKED));
        System.out.println(Integer.toBinaryString(mask));        // 1010
        System.out.println(stakeBlocked(mask));                  // true
        System.out.println(Integer.bitCount(mask));              // 2

        int cleared = clear(mask, RestrictionType.STAKE_BLOCKED);
        System.out.println(stakeBlocked(cleared));                // false
        System.out.println(fromMask(cleared));                   // [DEPOSIT_LIMITED]

        System.out.println(fromMask(changed(mask, cleared)));     // [STAKE_BLOCKED]
        System.out.println(toggle(toggle(mask, RestrictionType.COOLING_OFF),
                                  RestrictionType.COOLING_OFF) == mask); // true

        System.out.println(~0b1010);                             // -11, not 5
        System.out.println(1 << 32);                             // 1: shift count is 32 & 31 == 0
    }
}
```

**Pitfall:** "`~mask` gives me the complement of my ten flags." It gives the complement of all 32 bits, so bits 10 through 31 come back set and `(flags & ~STAKE_BLOCKED) != 0` starts reporting restrictions that do not exist. Fix: keep a `UNIVERSE` constant equal to the OR of every declared flag and write `~mask & UNIVERSE`.

**Insight:** the shift count is masked, not clamped — `1 << 32` is `1 << (32 & 31)` = `1 << 0` = 1, and `1L << 64` is `1L`. Any code that computes a shift amount from data must range-check it, because an out-of-range count fails silently rather than throwing. The bit-level details of shifting live in [01a-integral-arithmetic.md](01a-integral-arithmetic.md).

**Interview:** "How do you test whether *all* of a set of flags is present?" — `(flags & set) == set`. `(flags & set) != 0` tests whether *any* is present; confusing the two is the standard bug.

> `&`, `|`, `^` and `~` operate bitwise on `int` or `long` after promotion, and `~` inverts every bit of the promoted width, not just the bits you declared.

---

## 4. Cast expressions: three different operations, one syntax (1.6.14)

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

## 5. `==` on primitives, references, and mixed operands (1.6.15)

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

> `==` compares primitive values, unboxes when exactly one operand is numeric and the other a wrapper, and otherwise compares reference identity.

---

## Pitfalls

### `x += y` is just shorthand for `x = x + y`

**Wrong**

```java
byte retries = 10;
retries += 300;
System.out.println(retries);   // 54, and no warning
```

**Right**

```java
int retries = 10;                       // widen the field to match the arithmetic
retries = Math.addExact(retries, 300);  // 310, and throws ArithmeticException on overflow
System.out.println(retries);            // 310
```

**Why people believe it:** the expansion is true for `int` and `long`, which is where 95% of `+=` usage lives. JLS 15.26.2's actual expansion is `x = (T)(x + y)`, and the `(T)` only bites when `T` is narrower than the promoted arithmetic type.

### `&` and `&&` differ only in speed

**Wrong**

```java
Set<RestrictionType> restrictions = null;
if (restrictions != null & restrictions.isEmpty()) {   // NPE
    System.out.println("clear to stake");
}
```

**Right**

```java
Set<RestrictionType> restrictions = null;
if (restrictions != null && restrictions.isEmpty()) {  // false, no NPE
    System.out.println("clear to stake");
}
```

**Why people believe it:** the truth tables are identical, so the operators look interchangeable. JLS 15.23 makes `&&` skip its right operand entirely when the left is false; `&` (JLS 15.22.2) always evaluates both, so any right operand that can throw or hit the network does so unconditionally.

### `~mask` gives me the complement of my ten declared flags

**Wrong**

```java
final class RestrictionComplementWrong {
    static final int STAKE_BLOCKED = 1 << 1;     // RestrictionType ordinal 1
    public static void main(String[] args) {
        int complement = ~STAKE_BLOCKED;         // 11111111111111111111111111111101
        System.out.println(Integer.bitCount(complement));   // 31, not 9
        System.out.println(complement < 0);                 // true: the sign bit flipped too
    }
}
```

**Right**

```java
final class RestrictionComplementRight {
    static final int STAKE_BLOCKED = 1 << 1;
    static final int UNIVERSE = (1 << 10) - 1;   // ten declared RestrictionType values
    public static void main(String[] args) {
        int complement = ~STAKE_BLOCKED & UNIVERSE;
        System.out.println(Integer.toBinaryString(complement)); // 1111111101
        System.out.println(Integer.bitCount(complement));       // 9
        System.out.println(complement < 0);                     // false: inside the universe
    }
}
```

**Why people believe it:** `~` is described as "complement", and mentally the set being complemented is the set of flags you declared. The operator has no idea a `RestrictionType` exists — it complements all 32 bits of the promoted `int`, including the sign bit, so the result is negative and carries 22 phantom flags. Masking with a `UNIVERSE` constant restores the intended domain.

---

## Cheat sheet

| Item | Rule | Value / gotcha |
|---|---|---|
| `x op= y` | `x = (T)(x op y)`, `x` evaluated once | JLS 15.26.2 |
| `byte b=10; b+=300` | compiles, `i2b` | **54**; `b = b + 300` is a compile error |
| `char c='a'; c+=1` | compiles, `i2c` | `'b'`; `c = c + 1` is a compile error |
| `&&` / `\|\|` | right operand may not run | order cheap predicate first |
| `&` / `\|` on boolean | both operands always run | null-guard chains break |
| Test any flag | `(f & set) != 0` | parentheses mandatory |
| Test all flags | `(f & set) == set` | not `!= 0` |
| `~x` | `-x - 1`, all 32/64 bits | mask with a `UNIVERSE` constant |
| Shift count | masked to 5 bits (`int`) / 6 (`long`) | `1 << 32` == 1 |
| Cast: reference down | `checkcast`, runtime-checked | `ClassCastException` |
| Cast: primitive narrow | `i2b`/`i2c`/`i2s`/`l2i`/`d2i`, unchecked | silent truncation |
| `==` mixed prim/wrapper | wrapper unboxed (JLS 15.21.1) | null wrapper → NPE |
| `==` two wrappers | identity (JLS 15.21.3) | `Integer` cache covers at least -128..127 |

---

## Self-test

**Q1.** Why does `byte retries = 10; retries += 300;` compile while `retries = retries + 300;` does not, and what does `retries` hold?

<details><summary>Answer</summary>

JLS 15.26.2 defines `E1 op= E2` as `E1 = (T)((E1) op (E2))` with `E1` evaluated once, where `T` is the type of `E1`. The compound form therefore carries an implicit `(byte)` cast, which satisfies assignment conversion. The explicit form has no cast, and `10 + 300` is an `int` expression of value 310 which does not fit a `byte`, so `javac` reports `incompatible types: possible lossy conversion from int to byte`. The value is 54: 310 is `0000 0001 0011 0110`, the cast keeps the low eight bits `0011 0110` = 54. In bytecode the cast appears as a single `i2b` instruction.

</details>

**Q2.** `flags & STAKE_BLOCKED != 0` does not compile. Explain the error and give the two correct forms for "any of this set" and "all of this set".

<details><summary>Answer</summary>

`!=` is at precedence level 8 and `&` is at level 9, so `!=` binds tighter. The expression parses as `flags & (STAKE_BLOCKED != 0)`, which is `int & boolean` — no such operator, so `javac` rejects it. In C the same line compiles because the comparison yields an `int`, and the result is silently wrong; Java's stricter typing turns the precedence trap into a compile error.

For "any of these flags is present": `(flags & set) != 0`. For "all of these flags are present": `(flags & set) == set`. Substituting one for the other is the standard flags bug — `!= 0` on a multi-bit mask reports true when just one bit matches.

</details>

**Q3.** Two `IdempotencyKey` records with the same string compare `false` under `==` but `true` under `equals`. Two `Integer` values of 100 compare `true` under `==`, but two of 1000 compare `false`. Explain both.

<details><summary>Answer</summary>

Both are reference-equality comparisons under JLS 15.21.3: neither operand is of numeric or boolean type, so `==` compares object identity, not contents. Two separately constructed `IdempotencyKey` instances are distinct objects, so `==` is false; the record's generated `equals` compares components, so it is true.

For the `Integer` case, autoboxing routes through `Integer.valueOf`, which is specified to cache instances for at least the range -128 to 127. Both `100` literals therefore box to the *same* object and `==` is true. `1000` is outside the guaranteed cache, so each boxing allocates a new object and `==` is false. The lesson is not the boundary value but that `==` on wrappers gives a data-dependent answer — use `equals`, or unbox deliberately.

</details>

**Q4.** Which cast expressions can fail at run time, and which fail silently? Give the instruction each compiles to.

<details><summary>Answer</summary>

Two kinds can throw. A reference downcast compiles to `checkcast`; if the object's runtime type is not assignable to the target, the JVM throws `ClassCastException` at that exact instruction, not at some later use of the variable. An unboxing cast compiles to an `intValue`/`doubleValue` style `invokevirtual`, which throws `NullPointerException` when the wrapper reference is null.

Primitive casts never throw. Narrowing compiles to `i2b`, `i2c`, `i2s`, `l2i`, `d2i` and friends, all of which simply discard bits or truncate toward zero: `(byte) 310` is 54, `(int) 3.99` is 3, `(int) -3.99` is -3. Primitive *widening* casts are redundant on integral types and can still lose precision on `int`→`float`, `long`→`float` and `long`→`double`, again with no diagnostic.

Reference upcasts are checked at compile time only and emit nothing at all — they are always redundant. The rule to carry away is the asymmetry: reference casts are checked, primitive casts are assertions the runtime never verifies, so a `(byte)` on wire data needs an explicit range check or `Math.toIntExact` beside it.

</details>

**Q5.** What does `1 << 32` evaluate to, and what does that imply for a shift amount computed from data?

<details><summary>Answer</summary>

`1 << 32` is 1. For an `int` left operand the shift distance is masked to its low five bits, so 32 becomes `32 & 31 == 0` and the shift is a no-op. For a `long` left operand the mask is six bits, so `1L << 64` is likewise `1L`.

The distance is *masked, not clamped*, and no exception is thrown, which makes this one of the quieter failure modes in the language. Any code that derives a shift amount from data — an ordinal read off a wire frame, a bit index parsed from a config string, a loop bound computed from a `RestrictionType` count — must range-check the amount itself, because an out-of-range value produces a plausible-looking wrong answer rather than a diagnostic. The related trap is precedence: `1 << ordinal + 1` is `1 << (ordinal + 1)`, since shift sits below additive on the ladder.

</details>

---

## Open questions

- `Integer.valueOf`'s cache is specified to cover *at least* -128 to 127; the actual upper bound on HotSpot is settable via the `java.lang.Integer.IntegerCache.high` system property, and the effective default on the exact target JDK build is not verified here. `java -XX:+PrintFlagsFinal -version` does not report it because it is a Java-level property rather than a VM flag; reading `Integer.valueOf(i) == Integer.valueOf(i)` in a loop on the target build would settle it. No number in this file depends on the answer — every example uses 100 (inside the guaranteed range) and 1000 (outside it).
- *Effective Java* (3rd edition), Item 61 "Prefer primitive types to boxed primitives", is the standard reference for section 5. The item number is cited alongside its title so a wrong number is self-correcting against the book's table of contents.

---

**Leaves covered:** 1.6.6, 1.6.7, 1.6.8, 1.6.9, 1.6.14, 1.6.15 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** D-017
**Target version:** Java 21 LTS
**Lines:** 0
