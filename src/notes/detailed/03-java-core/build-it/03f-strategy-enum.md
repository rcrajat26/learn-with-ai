# 03 Java Core — Enum-shaped builds — the strategy enum — BUILD IT (§4.5.3)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The persisted-code enum](03k-persisted-code-enum.md) · Next: [The enum state machine](03a-enum-state-machine-and-singleton.md)

---

## What gets built here

The same four settlement rails, three ways, so the differences between the three ways are visible
rather than asserted:

| Build | Style | What it proves |
|---|---|---|
| `StakeSplitPolicy` | An abstract method declared on the enum, overridden per constant | The override is compulsory — a constant with no body does not compile |
| `SettlementRail` | `enum implements Rail`, each constant supplying the interface bodies | One anonymous subclass per constant, on disk and in `javap`, and everything that breaks because of it |
| `SettlementRailInjected` | A constructor-injected `Function` field | No extra class files, the enum class stays `final`, `getClass()` stays honest |

The two rail enums produce byte-identical plans, so the comparison isolates the dispatch mechanism
from the behaviour. Preceded by [the persisted-code enum](03k-persisted-code-enum.md); followed by
[the enum state machine](03a-enum-state-machine-and-singleton.md), which drives transitions between
the `AA-` codes with an `EnumMap`.

Everything here is `[BUILD]`: complete, compiling Java 21, compiled and run on
**Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64 (Apple silicon)**, with real output
pasted.

---

## 4.5.3 A strategy enum: per-constant bodies and an interface

### The shape

Four constants, four genuinely different settlement plans. The four rails —
`CARD_DEPOSIT`, `BANK_DEPOSIT`, `CARD_WITHDRAWAL`, `BANK_WITHDRAWAL` — differ in how many ledger
movements they produce, which positions those movements touch, whether an operator has to sign
off, and whether they post immediately or wait for one of four daily windows. The behaviour lives
*on the constant*, so adding a fifth rail cannot compile until its behaviour is supplied.

The alternative is a `switch` in `PaymentService` that decides what to do per rail. That
compiles fine when someone adds `CRYPTO_DEPOSIT` and forgets the case, and fails at runtime in the
`default` branch. A strategy enum moves that failure from runtime to compile time, which is the
entire argument.

### The three styles, compared

| Style | How the behaviour attaches | Class files produced | `getClass()` on a constant | When to use it |
|---|---|---|---|---|
| A: abstract method on the enum | `public abstract T op(arguments)`, overridden in each constant's body | one per constant with a body, named `Outer$1`, `Outer$2`, … | the anonymous subclass, not the enum | behaviour is intrinsic to the constant and has no reusable name |
| B: enum implements an interface, per-constant bodies | `enum X implements Rail`, each constant overrides the interface methods | same: one anonymous subclass per constant | the anonymous subclass | the abstraction is worth naming, and non-enum implementations of it exist or will |
| C: constructor-injected function field | a `Function`/`Supplier` field assigned per constant, usually a method reference | none extra for the constants; lambdas become `invokedynamic` call sites | the enum class itself | the behaviours are independently testable, shareable, or come from outside |

Style B is the default: it names the abstraction, so `PaymentService` can depend on `Rail` and a
test can supply a fake rail that is not an enum constant at all. Style C is what you reach for
when the behaviours want to exist on their own — and, as the class-file column says, when you do
not want four extra classes loaded.

### The supporting types

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Currency;

public record Money(BigDecimal amount, Currency currency) {

    private static final Currency GBP = Currency.getInstance("GBP");

    public static Money gbp(String value) {
        return new Money(new BigDecimal(value).setScale(2, RoundingMode.UNNECESSARY), GBP);
    }

    public Money plus(Money other)  { return new Money(amount.add(other.amount), currency); }
    public Money minus(Money other) { return new Money(amount.subtract(other.amount), currency); }

    public Money percentFloor(int percent) {
        return new Money(amount.multiply(BigDecimal.valueOf(percent))
                .movePointLeft(2)
                .setScale(2, RoundingMode.DOWN), currency);
    }

    public Money min(Money other) { return amount.compareTo(other.amount) <= 0 ? this : other; }

    @Override public String toString() { return currency.getSymbol(java.util.Locale.UK) + amount.toPlainString(); }
}
```

```java
/** One leg of a double-entry ledger entry. Positions come from the ledger position set. */
public record Movement(String position, char side, Money amount) {
    @Override public String toString() { return side + " " + position + " " + amount; }
}
```

```java
import java.util.List;

/** A mechanism for moving money. Implemented by the settlement rail constants. */
public interface Rail {

    /** The ledger movements this rail produces for the given amount. */
    List<Movement> plan(Money amount);

    /** Whether a PaymentRun operator must sign off before the movements are posted. */
    boolean requiresOperatorSignOff();

    /** Windows per day; 0 means the rail posts immediately. */
    int settlementWindowsPerDay();

    default String describe() {
        return (settlementWindowsPerDay() == 0 ? "immediate" : settlementWindowsPerDay() + " windows/day")
                + (requiresOperatorSignOff() ? ", operator sign-off" : ", no sign-off");
    }
}
```

### Style A, complete: an abstract method on the enum

```java
/** Invariant: the two portions sum exactly to the stake. */
public record StakeSplit(Money bonusPortion, Money cashPortion) {
    public Money total() { return bonusPortion.plus(cashPortion); }

    @Override public String toString() {
        return bonusPortion + " bonus + " + cashPortion + " cash";
    }
}
```

```java
/** Style A: an abstract method declared on the enum itself, overridden per constant. */
public enum StakeSplitPolicy {

    /** Domain default: min(BONUS_AVAILABLE, 10% of stake), bonus portion rounds DOWN. */
    PROPORTIONAL_BONUS_FIRST {
        @Override public StakeSplit split(Money stake, Money bonusAvailable) {
            Money bonusPortion = stake.percentFloor(10).min(bonusAvailable);
            return new StakeSplit(bonusPortion, stake.minus(bonusPortion));
        }
    },

    /** Used while a bonus is CLAWED_BACK: the stake draws cash only. */
    CASH_ONLY {
        @Override public StakeSplit split(Money stake, Money bonusAvailable) {
            return new StakeSplit(Money.gbp("0.00"), stake);
        }
    };

    public abstract StakeSplit split(Money stake, Money bonusAvailable);
}
```

The abstract method is what makes the enum work: `StakeSplitPolicy` has no body for `split`, so
every constant *must* supply one, and a new constant that forgets is a compile error. Note the
bonus portion rounding **down** — 10% of 3.33 is 0.333, floored to 0.33, cash covers 3.00.
Rounding up gives 0.34 + 3.00 = 3.34 and creates money.

### Style B, complete: an interface with per-constant bodies

```java
import java.util.List;

/** Style B: the enum implements an interface and every constant supplies its own body. */
public enum SettlementRail implements Rail {

    CARD_DEPOSIT {
        @Override public List<Movement> plan(Money amount) {
            return List.of(
                    new Movement("PSP_RECEIVABLE", 'D', amount),
                    new Movement("CLIENT_CASH_AVAILABLE", 'C', amount));
        }
        @Override public boolean requiresOperatorSignOff() { return false; }
        @Override public int settlementWindowsPerDay()     { return 0; }
    },

    BANK_DEPOSIT {
        @Override public List<Movement> plan(Money amount) {
            // Arrives unattributed: parks in SUSPENSE, then moves out once matched.
            return List.of(
                    new Movement("BANK_SETTLEMENT", 'D', amount),
                    new Movement("SUSPENSE", 'C', amount),
                    new Movement("SUSPENSE", 'D', amount),
                    new Movement("CLIENT_CASH_AVAILABLE", 'C', amount));
        }
        @Override public boolean requiresOperatorSignOff() { return false; }
        @Override public int settlementWindowsPerDay()     { return 4; }
    },

    CARD_WITHDRAWAL {
        @Override public List<Movement> plan(Money amount) {
            // Closed loop, and the PSP payout fee is the client's.
            Money fee = amount.percentFloor(1);
            return List.of(
                    new Movement("CLIENT_CASH_AVAILABLE", 'D', amount),
                    new Movement("CLIENT_CASH_RESERVED", 'C', amount),
                    new Movement("CLIENT_CASH_RESERVED", 'D', amount),
                    new Movement("PSP_RECEIVABLE", 'C', amount.minus(fee)),
                    new Movement("FEES", 'C', fee));
        }
        @Override public boolean requiresOperatorSignOff() { return false; }
        @Override public int settlementWindowsPerDay()     { return 0; }
    },

    BANK_WITHDRAWAL {
        @Override public List<Movement> plan(Money amount) {
            // Reserved now, released into a PaymentRun at the next window.
            return List.of(
                    new Movement("CLIENT_CASH_AVAILABLE", 'D', amount),
                    new Movement("CLIENT_CASH_RESERVED", 'C', amount),
                    new Movement("CLIENT_CASH_RESERVED", 'D', amount),
                    new Movement("BANK_SETTLEMENT", 'C', amount));
        }
        @Override public boolean requiresOperatorSignOff() { return true; }
        @Override public int settlementWindowsPerDay()     { return 4; }
    };

    /** Shared, non-overridden: the balance check every rail runs before planning. */
    public final boolean balances(Money amount) {
        java.math.BigDecimal debits = java.math.BigDecimal.ZERO;
        java.math.BigDecimal credits = java.math.BigDecimal.ZERO;
        for (Movement movement : plan(amount)) {
            if (movement.side() == 'D') debits = debits.add(movement.amount().amount());
            else                       credits = credits.add(movement.amount().amount());
        }
        return debits.compareTo(credits) == 0;
    }
}
```

`balances` is the point of putting behaviour on the enum rather than in a `switch`: a concrete
`final` method on the enum calls the abstract one, so every constant gets the double-entry check
for free and no constant can opt out of it.

### Style C, complete: constructor-injected functions

```java
import java.util.List;
import java.util.function.Function;

/** Style C: one constructor-injected function field, no per-constant bodies. */
public enum SettlementRailInjected implements Rail {

    CARD_DEPOSIT     (SettlementRailInjected::cardDeposit,     false, 0),
    BANK_DEPOSIT     (SettlementRailInjected::bankDeposit,     false, 4),
    CARD_WITHDRAWAL  (SettlementRailInjected::cardWithdrawal,  false, 0),
    BANK_WITHDRAWAL  (SettlementRailInjected::bankWithdrawal,  true,  4);

    private final Function<Money, List<Movement>> planner;
    private final boolean operatorSignOff;
    private final int windowsPerDay;

    SettlementRailInjected(Function<Money, List<Movement>> planner, boolean operatorSignOff, int windowsPerDay) {
        this.planner = planner;
        this.operatorSignOff = operatorSignOff;
        this.windowsPerDay = windowsPerDay;
    }

    @Override public List<Movement> plan(Money amount)   { return planner.apply(amount); }
    @Override public boolean requiresOperatorSignOff()   { return operatorSignOff; }
    @Override public int settlementWindowsPerDay()       { return windowsPerDay; }

    private static List<Movement> cardDeposit(Money amount) {
        return List.of(
                new Movement("PSP_RECEIVABLE", 'D', amount),
                new Movement("CLIENT_CASH_AVAILABLE", 'C', amount));
    }

    private static List<Movement> bankDeposit(Money amount) {
        return List.of(
                new Movement("BANK_SETTLEMENT", 'D', amount),
                new Movement("SUSPENSE", 'C', amount),
                new Movement("SUSPENSE", 'D', amount),
                new Movement("CLIENT_CASH_AVAILABLE", 'C', amount));
    }

    private static List<Movement> cardWithdrawal(Money amount) {
        Money fee = amount.percentFloor(1);
        return List.of(
                new Movement("CLIENT_CASH_AVAILABLE", 'D', amount),
                new Movement("CLIENT_CASH_RESERVED", 'C', amount),
                new Movement("CLIENT_CASH_RESERVED", 'D', amount),
                new Movement("PSP_RECEIVABLE", 'C', amount.minus(fee)),
                new Movement("FEES", 'C', fee));
    }

    private static List<Movement> bankWithdrawal(Money amount) {
        return List.of(
                new Movement("CLIENT_CASH_AVAILABLE", 'D', amount),
                new Movement("CLIENT_CASH_RESERVED", 'C', amount),
                new Movement("CLIENT_CASH_RESERVED", 'D', amount),
                new Movement("BANK_SETTLEMENT", 'C', amount));
    }
}
```

**Pitfall:** a method reference to a *private static* method of the enum works in the constant
argument list; a method reference to an *instance* method does not. `this::cardDeposit` is
`error: non-static variable this cannot be referenced from a static context`, because a constant's
argument list is a static context; and the unbound form `SettlementRailInjected::cardDeposit` on an
instance method has an extra receiver parameter, so it is
`error: incompatible types: invalid method reference` against a one-argument `Function`. Keep
injected planners `static`. Both errors are captured in the pitfalls below.

### Running both, and the 3.33 case

```console
CARD_DEPOSIT  (immediate, no sign-off)  amount £65.00
    D PSP_RECEIVABLE £65.00
    C CLIENT_CASH_AVAILABLE £65.00
    balances = true
BANK_DEPOSIT  (4 windows/day, no sign-off)  amount £65.00
    D BANK_SETTLEMENT £65.00
    C SUSPENSE £65.00
    D SUSPENSE £65.00
    C CLIENT_CASH_AVAILABLE £65.00
    balances = true
CARD_WITHDRAWAL  (immediate, no sign-off)  amount £180.00
    D CLIENT_CASH_AVAILABLE £180.00
    C CLIENT_CASH_RESERVED £180.00
    D CLIENT_CASH_RESERVED £180.00
    C PSP_RECEIVABLE £178.20
    C FEES £1.80
    balances = true
BANK_WITHDRAWAL  (4 windows/day, operator sign-off)  amount £180.00
    D CLIENT_CASH_AVAILABLE £180.00
    C CLIENT_CASH_RESERVED £180.00
    D CLIENT_CASH_RESERVED £180.00
    C BANK_SETTLEMENT £180.00
    balances = true
injected shape agrees with per-constant shape:
    CARD_DEPOSIT     movements equal=true signOff equal=true
    BANK_DEPOSIT     movements equal=true signOff equal=true
    CARD_WITHDRAWAL  movements equal=true signOff equal=true
    BANK_WITHDRAWAL  movements equal=true signOff equal=true
stake split, the canonical 3.33 case:
    PROPORTIONAL_BONUS_FIRST   £0.33 bonus + £3.00 cash  total=£3.33  exact=true
    CASH_ONLY                  £0.00 bonus + £3.33 cash  total=£3.33  exact=true
```

The amounts are the domain's own averages: 65 for a card deposit, 180 for a card withdrawal.
Four rails, four different movement counts (2, 4, 5, 4), two different position sets, and one
that requires operator sign-off. Both shapes produce byte-identical plans, so the choice between
them is about structure and class loading, not behaviour.

### What per-constant bodies actually cost `[BYTECODE]`

```console
classes actually behind the constants:
    SettlementRail.class                    = SettlementRail
    CARD_DEPOSIT     getClass()=SettlementRail$1         ==enum? false  declaringClass=SettlementRail
    BANK_DEPOSIT     getClass()=SettlementRail$2         ==enum? false  declaringClass=SettlementRail
    CARD_WITHDRAWAL  getClass()=SettlementRail$3         ==enum? false  declaringClass=SettlementRail
    BANK_WITHDRAWAL  getClass()=SettlementRail$4         ==enum? false  declaringClass=SettlementRail
    CARD_DEPOSIT     getClass()=SettlementRailInjected   ==enum? true
    BANK_DEPOSIT     getClass()=SettlementRailInjected   ==enum? true
    CARD_WITHDRAWAL  getClass()=SettlementRailInjected   ==enum? true
    BANK_WITHDRAWAL  getClass()=SettlementRailInjected   ==enum? true
    SettlementRail is final? false
    SettlementRailInjected is final? true
    CARD_DEPOSIT superclass = SettlementRail
    switch still works: queue into PaymentRun
    getDeclaredClasses().length = 0 (generated subclasses are anonymous, so they are not member classes)
```

`values()[i].getClass() == SettlementRail.class` is **false** for every constant of the
per-constant-body enum, and **true** for every constant of the injected one. The evidence on disk
confirms why — `javac` emitted one class file per body:

```console
2880 Money.class
1725 Movement.class
1099 Rail.class
 835 SettlementRail$1.class
 910 SettlementRail$2.class
1069 SettlementRail$3.class
 922 SettlementRail$4.class
2012 SettlementRail.class
3552 SettlementRailInjected.class
1728 StakeSplit.class
 595 StakeSplitPolicy$1.class
 545 StakeSplitPolicy$2.class
1154 StakeSplitPolicy.class
 736 StrategyEnumDemo$1.class
6467 StrategyEnumDemo.class
```

Four `SettlementRail$N` files, two `StakeSplitPolicy$N` files, and **none** for
`SettlementRailInjected` — the method references become `invokedynamic` call sites, not class
files on disk. `javap` on the enum itself and on one generated subclass:

```console
public abstract class SettlementRail extends java.lang.Enum<SettlementRail> implements Rail {
  public static final SettlementRail CARD_DEPOSIT;
  public static final SettlementRail BANK_DEPOSIT;
  public static final SettlementRail CARD_WITHDRAWAL;
  public static final SettlementRail BANK_WITHDRAWAL;
  private static final SettlementRail[] $VALUES;
  public static SettlementRail[] values();
  public static SettlementRail valueOf(java.lang.String);
  private SettlementRail();
  public final boolean balances(Money);
  private static SettlementRail[] $values();
  static {};
}
```

```console
final class SettlementRail$1 extends SettlementRail {
  private SettlementRail$1(java.lang.String, int);
    Code:
       0: aload_0
       1: aload_1
       2: iload_2
       3: invokespecial #1                  // Method SettlementRail."<init>":(Ljava/lang/String;I)V
       6: return

  public java.util.List<Movement> plan(Money);
    Code:
       0: new           #7                  // class Movement
       3: dup
       4: ldc           #9                  // String PSP_RECEIVABLE
       6: bipush        68
       8: aload_1
       9: invokespecial #11                 // Method Movement."<init>":(Ljava/lang/String;CLMoney;)V
      12: new           #7                  // class Movement
      15: dup
      16: ldc           #14                 // String CLIENT_CASH_AVAILABLE
      18: bipush        67
      20: aload_1
      21: invokespecial #11                 // Method Movement."<init>":(Ljava/lang/String;CLMoney;)V
      24: invokestatic  #16                 // InterfaceMethod java/util/List.of:(Ljava/lang/Object;Ljava/lang/Object;)Ljava/util/List;
      27: areturn

  public boolean requiresOperatorSignOff();
    Code:
       0: iconst_0
       1: ireturn

  public int settlementWindowsPerDay();
    Code:
       0: iconst_0
       1: ireturn
}
```

Read the important lines. `public abstract class SettlementRail` — the enum with bodies is
**`abstract`**, not `final`; `SettlementRailInjected` is `final`. `final class SettlementRail$1
extends SettlementRail` — the generated subclass is `final` and anonymous, with a synthetic
constructor whose two parameters are exactly the name and the ordinal `javac` injects into
`Enum`'s constructor. `bipush 68` and `bipush 67` are the `char` literals `D` and `C`; they are
`int` constants in the bytecode because `char` is an `int` on the operand stack. The two flag
methods compile to `iconst_0; ireturn` each — a constant per subclass, where the injected shape
reads a field.

### The consequences that bite

`switch` still works, as the output shows: switching over an enum with per-constant bodies
dispatches on `ordinal()`, and the constant's dynamic type is irrelevant to it. Four things do
not survive:

```console
what a getClass()-based check sees:
    bodyClass.isEnum()             = false
    bodyClass.getEnumConstants()   = null
    SettlementRail.class.isEnum()  = true
    EnumSet.noneOf(bodyClass)     -> java.lang.ClassCastException: class SettlementRail$1 not an enum
    EnumSet.noneOf(declaringClass) = []
```

- **`getClass()`-based `equals`** — the very shape `Object.equals` contracts are usually written
  with, `other.getClass() == getClass()` — treats `CARD_DEPOSIT` as a different type from
  `BANK_DEPOSIT`. `Enum.equals` is `final` and identity-based, so the enum itself is fine; the
  breakage is in *your* code that wraps or validates a constant with a `getClass()` check.
- **`Class.isEnum()` is `false`** on the subclass, and `getEnumConstants()` returns `null`.
- **`EnumSet.noneOf(constant.getClass())`** throws `ClassCastException: class SettlementRail$1 not
  an enum`. Always use `getDeclaringClass()`, which returns the enum class for constants with and
  without bodies alike — that is precisely what it exists for.
- **Serialization assumptions built on `getClass().getName()`** — a common shape in custom
  serializers and in framework type registries — record `SettlementRail$1`, a name that is
  positional. Insert a constant with a body ahead of it and `$1` now means a different rail. Java
  serialization itself is unaffected, because it writes the constant's `name()` via `TC_ENUM`, not
  the class name.

Also, `StrategyEnumDemo$1` in the class-file listing is `javac`'s `$SwitchMap` holder for the
`switch` over `SettlementRail` — a synthetic class with one `static final int[]` field.
[The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md) owns `$SwitchMap` and `$VALUES` in full;
`../enums/01c-production-patterns-and-guarantees.md` and `../enums/03a-internals-enum-members.md`
own the production patterns and the member-level internals.

> **Definition.** A strategy enum is a closed set of named strategies: the abstraction is an
> abstract method or an interface, the implementation is either a per-constant body — which costs
> one anonymous subclass per constant, makes the enum class `abstract`, and makes
> `getClass()` and `isEnum()` lie — or a constructor-injected function, which costs a field and
> keeps the enum class `final`.

### Diff vs the real one — this enum vs a `switch` in a service

| Axis | This build | The `switch`-in-`PaymentService` alternative |
|---|---|---|
| Edge cases | A new rail without behaviour does not compile | A new rail without a case falls into `default` at runtime, in production, on a payout |
| Intrinsics | None. `plan` is a virtual call on a four-implementation site, so the JIT usually leaves it megamorphic-free but polymorphic | The `switch` becomes a `tableswitch` on `$SwitchMap[ordinal()]`, branch-predictable and slightly cheaper |
| Serialization | Behaviour is not serialized; the constant's `name()` is, and behaviour is re-attached by class loading | Same, since the behaviour was never in the enum |
| Null policy | `plan(null)` throws `NullPointerException` from `Money` deref; a null rail throws before dispatch | A null rail hits `default` or `NullPointerException` on `.ordinal()` |
| Thread safety | Constants are immutable and safely published by `<clinit>`; `Movement` and `Money` are records with `final` fields, so plans are shareable | Same, if the service is stateless |
| Allocation tricks | One `List.of` per `plan` call plus the `Movement`s and, for card withdrawal, one extra `Money` for the fee. Nothing cached; a fixed plan per rail could be, at the cost of parameterisation | Identical allocation; the difference is only where the code lives |
| Why the JDK bothers | The JDK does not ship strategy enums, but it uses the pattern itself — `java.time.temporal.ChronoField` and `ChronoUnit` are strategy enums with per-constant bodies, and `RoundingMode` is the injected-value shape | — |

**Interview:** *"Per-constant body or a field holding a lambda?"* — Per-constant bodies read
better and enforce the override, but generate one anonymous subclass per constant, make the enum
class `abstract`, and make `getClass()`, `isEnum()` and `EnumSet.noneOf(getClass())` behave
unexpectedly; an injected function keeps the enum `final` and the behaviours independently
testable. Use `getDeclaringClass()`, never `getClass()`, when you need the enum type.

The §4.5-wide **diff vs the compiler's generated enum** — `$VALUES`, `$SwitchMap`, the `Enum`
superclass, and the constructor injection of name and ordinal — is leaf 4.5.7, in
[The values() cache and the §4.5 diff table](03b-enum-values-cache-and-diff.md).

---

## Pitfalls

### Believing a constant with a per-constant body has the enum's own class

**Wrong**

```java
Class<?> bodyClass = SettlementRail.CARD_DEPOSIT.getClass();
EnumSet.noneOf((Class) bodyClass);
```

```console
bodyClass.isEnum()             = false
bodyClass.getEnumConstants()   = null
EnumSet.noneOf(bodyClass)     -> java.lang.ClassCastException: class SettlementRail$1 not an enum
```

**Right**

```java
EnumSet.noneOf(SettlementRail.CARD_DEPOSIT.getDeclaringClass());
```

```console
EnumSet.noneOf(declaringClass) = []
```

**Why people believe it:** for enums without bodies `getClass()` *is* the enum class, which is the
majority of enums anyone writes, so the habit forms on the cases where it happens to work. It then
fails the first time someone adds a per-constant body to an existing enum — a change that looks
purely additive and breaks reflective code elsewhere.

### Keeping the per-rail decision in a `switch` in the service

**Wrong**

```java
/** Behaviour-free rails: the decision lives in the service. */
public enum DepositRail { CARD_DEPOSIT, BANK_DEPOSIT, CRYPTO_DEPOSIT }
```

```java
public final class PaymentServiceSwitch {

    /** A statement switch with a default. CRYPTO_DEPOSIT was added; this was not updated. */
    static String creditPosition(DepositRail rail) {
        switch (rail) {
            case CARD_DEPOSIT: return "PSP_RECEIVABLE -> CLIENT_CASH_AVAILABLE";
            case BANK_DEPOSIT: return "BANK_SETTLEMENT -> SUSPENSE -> CLIENT_CASH_AVAILABLE";
            default:           return "SUSPENSE";
        }
    }

    public static void main(String[] args) {
        for (DepositRail rail : DepositRail.values()) {
            System.out.printf("%-15s -> %s%n", rail, creditPosition(rail));
        }
    }
}
```

```console
CARD_DEPOSIT    -> PSP_RECEIVABLE -> CLIENT_CASH_AVAILABLE
BANK_DEPOSIT    -> BANK_SETTLEMENT -> SUSPENSE -> CLIENT_CASH_AVAILABLE
CRYPTO_DEPOSIT  -> SUSPENSE
```

It compiled, it ran, and every crypto deposit now parks in `SUSPENSE` forever instead of crediting
the client. The `default` branch was written as a safety net and became the bug.

**Right**

An abstract method on the enum makes the omission a compile error:

```java
public enum DepositRailStrategy {
    CARD_DEPOSIT {
        @Override public String creditPosition() { return "PSP_RECEIVABLE -> CLIENT_CASH_AVAILABLE"; }
    },
    BANK_DEPOSIT {
        @Override public String creditPosition() { return "BANK_SETTLEMENT -> SUSPENSE -> CLIENT_CASH_AVAILABLE"; }
    },
    CRYPTO_DEPOSIT;   // added, no body supplied

    public abstract String creditPosition();
}
```

```console
p3b/DepositRailStrategy.java:8: error: DepositRailStrategy is abstract; cannot be instantiated
    CRYPTO_DEPOSIT;   // added, no body supplied
    ^
1 error
```

The failure moved from a production payout to `javac`. If the decision genuinely must live in a
service, use a `switch` **expression** over the enum with no `default` — Java 21 requires
exhaustiveness there, so adding a constant breaks the build for the same reason.

**Why people believe it:** a `switch` keeps the enum a plain list of names, which looks like good
separation — the enum is data, the service is logic — and it puts the behaviour next to the other
service code that uses it. The cost is invisible until the day someone adds a constant, and the
`default` branch that was added defensively is precisely what hides it.

### Injecting an instance method reference into a constant's argument list

**Wrong**

```java
public enum SettlementRailBadInjection {

    CARD_DEPOSIT(SettlementRailBadInjection::cardDeposit),   // instance method reference
    BANK_DEPOSIT(SettlementRailBadInjection::bankDeposit);

    private final Function<String, List<String>> planner;

    SettlementRailBadInjection(Function<String, List<String>> planner) { this.planner = planner; }

    private List<String> cardDeposit(String amount) {
        return List.of("D PSP_RECEIVABLE " + amount, "C CLIENT_CASH_AVAILABLE " + amount);
    }

    private List<String> bankDeposit(String amount) {
        return List.of("D BANK_SETTLEMENT " + amount, "C SUSPENSE " + amount);
    }
}
```

```console
p3c/SettlementRailBadInjection.java:6: error: incompatible types: invalid method reference
    CARD_DEPOSIT(SettlementRailBadInjection::cardDeposit),   // instance method reference
                 ^
    unexpected instance method cardDeposit(String) found in unbound lookup
p3c/SettlementRailBadInjection.java:7: error: incompatible types: invalid method reference
    BANK_DEPOSIT(SettlementRailBadInjection::bankDeposit);
                 ^
    unexpected instance method bankDeposit(String) found in unbound lookup
Note: Some messages have been simplified; recompile with -Xdiags:verbose to get full output
2 errors
```

Reaching for `this` instead fails differently and more clearly:

```console
p3d/SettlementRailThisInjection.java:6: error: non-static variable this cannot be referenced from a static context
    CARD_DEPOSIT(this::cardDeposit),   // instance method reference
                 ^
p3d/SettlementRailThisInjection.java:7: error: non-static variable this cannot be referenced from a static context
    BANK_DEPOSIT(this::bankDeposit);
                 ^
2 errors
```

**Right**

Make the planners `static`, as `SettlementRailInjected` does:

```java
    CARD_DEPOSIT     (SettlementRailInjected::cardDeposit,     false, 0),

    private static List<Movement> cardDeposit(Money amount) {
        return List.of(
                new Movement("PSP_RECEIVABLE", 'D', amount),
                new Movement("CLIENT_CASH_AVAILABLE", 'C', amount));
    }
```

```console
    CARD_DEPOSIT     movements equal=true signOff equal=true
```

**Why people believe it:** `Enum::method` and `Outer::method` look interchangeable, because for a
static method they are, and the unbound-receiver form of a method reference is exactly how
`Comparator.comparing(Money::amount)` is written everywhere else. What differs here is the context:
a constant's argument list is evaluated inside `<clinit>`, which is static, and there is no
receiver to bind. If a planner genuinely needs per-constant state, take it as a parameter or use a
per-constant body instead.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| Style A | `public abstract T op(arguments)` on the enum, overridden per constant. Omitting a body: `error: X is abstract; cannot be instantiated` |
| Style B | `enum X implements Iface`, each constant supplies the interface bodies. Use when the abstraction is worth naming and a non-enum implementation exists |
| Style C | A constructor-injected `Function` field, assigned from a `static` method reference. Use when the behaviours want to exist on their own or extra classes are unwanted |
| Cost of a per-constant body | One anonymous class file per constant — `SettlementRail$1` … `$4` on disk |
| Effect on the enum class | With bodies: `public abstract class`. Without: `public final class` |
| `getClass()` on a constant with a body | The anonymous subclass. `isEnum()` false, `getEnumConstants()` null |
| `EnumSet.noneOf(constant.getClass())` | `ClassCastException: class SettlementRail$1 not an enum` |
| Correct accessor | `getDeclaringClass()`, always — correct for constants with and without bodies |
| `getDeclaredClasses()` | Length 0; the generated subclasses are anonymous, not member classes |
| `switch` over an enum with bodies | Works. Dispatch is on `ordinal()` through a synthetic `$SwitchMap$X` holder class |
| Java serialization | Unaffected by bodies: `TC_ENUM` carries `name()`, never the class name |
| Custom serializers keyed on `getClass().getName()` | Break: `$1` is positional, so inserting a constant with a body reassigns it |
| Injected planners | Must be `static`. `this::plan` is rejected as a non-static variable referenced from a static context; unbound `Enum::plan` has the wrong arity |
| Style C's one weakness | Nothing forces a constant to supply a strategy; a `null` planner compiles |
| Strategy enums in the JDK | `ChronoField` and `ChronoUnit` (per-constant bodies); `RoundingMode` (plain constants) |
| Stake split, 3.33 | `0.33` bonus + `3.00` cash. Bonus portion rounds **down**; rounding up creates money |
| §4.5 diff table | Leaf 4.5.7, in `03b-enum-values-cache-and-diff.md` |

---

## Self-test

**Q1.** `values()[0].getClass() == SettlementRail.class` is `false`. Explain, and name two APIs
that break because of it.

<details><summary>Answer</summary>

`CARD_DEPOSIT` has a per-constant body, so `javac` emitted `final class SettlementRail$1 extends
SettlementRail` and the constant is an instance of that anonymous subclass — which also makes
`SettlementRail` itself `abstract` rather than `final`. Breakage: `Class.isEnum()` returns `false`
on the subclass and `getEnumConstants()` returns `null`; `EnumSet.noneOf(constant.getClass())`
throws `ClassCastException: class SettlementRail$1 not an enum`; and any `equals` or type-registry
check written as `other.getClass() == getClass()` treats two constants of the same enum as
different types. Use `getDeclaringClass()`, which returns `SettlementRail` for constants with and
without bodies.

</details>

**Q2.** `switch` over an enum with per-constant bodies still works. Why does the anonymous
subclass not matter to it?

<details><summary>Answer</summary>

Enum `switch` does not dispatch on the constant's dynamic type. `javac` emits a synthetic holder
class with a `static final int[] $SwitchMap$SettlementRail` indexed by `ordinal()`, mapping each
constant's ordinal to a small dense case index, and then a `tableswitch` on that index. Both
`ordinal()` and the map are properties of the enum class, not of the subclass, so a per-constant
body is invisible to the whole mechanism. The indirection exists so that recompiling the enum
without recompiling the switch does not silently reassign cases.

</details>

**Q3.** When would you choose a constructor-injected function over a per-constant body?

<details><summary>Answer</summary>

When the behaviours want to exist independently of the constants — because they are shared between
constants, tested on their own, or supplied from configuration; when you do not want one extra
loaded class per constant, which matters for a large enum in a startup-time-sensitive service; or
when reflective code elsewhere depends on `getClass()` being the enum class and on the enum class
staying `final`. The cost is that nothing forces a constant to supply a real strategy — a
`null` planner compiles — whereas an abstract method makes the omission a compile error. Keep
injected planners `static`: a constant's argument list is a static context, so `this::plan` is
rejected outright and the unbound `Enum::plan` form has the wrong arity for a one-argument
`Function`.

</details>

**Q4.** `SettlementRail` and `SettlementRailInjected` produce byte-identical plans. On what grounds
do you choose between them?

<details><summary>Answer</summary>

Not behaviour — the demo proves the plans are equal for all four rails. The grounds are:

Class loading. The per-constant-body version emits `SettlementRail$1` through `$4`; the injected
version emits none, because the method references become `invokedynamic` call sites. For a
four-constant enum this is noise; for a large enum in a startup-sensitive service it is four to
forty extra classes to load and verify.

Reflection honesty. Bodies make the enum class `abstract` and make `getClass()`, `isEnum()`,
`getEnumConstants()` and `EnumSet.noneOf(getClass())` misbehave. If anything in the system
reflects over constants, the injected shape avoids the whole class of problem.

Enforcement. An abstract method makes a missing strategy a compile error. An injected field does
not — a `null` planner compiles and fails at first call.

Testability. Injected planners are `static` methods you can unit-test directly and share between
constants; a per-constant body is reachable only through its constant.

Default to per-constant bodies for readability and enforcement; switch to injection when class
count, reflection, or independent testing of the strategies matters.

</details>

**Q5.** Why does `balances` work as a `final` method on `SettlementRail` even though `plan` is
different for every constant?

<details><summary>Answer</summary>

Because `balances` calls `plan` virtually. `SettlementRail` is the superclass of each generated
anonymous subclass, so an `invokevirtual` on `plan` from `balances` dispatches to the constant's
own override at run time. That is the structural advantage of putting behaviour on the enum rather
than in a service: a concrete `final` method on the enum can invoke the abstract one, so every
constant inherits the double-entry check and no constant can opt out of it — declaring it `final`
means a per-constant body cannot override `balances` even by accident. The same shape works in the
injected version, where `balances` would call `planner.apply` instead.

</details>

---

## Open questions

- none

---

**Leaves covered:** 4.5.3 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 826
