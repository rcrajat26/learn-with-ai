# 03 Java Core — Enums in use — BASICS (§1.18, 1.18.11–1.18.13)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [The implicit members and enum identity](01a-implicit-members-and-identity.md) · Next: [Production patterns and the guarantees](01c-production-patterns-and-guarantees.md)

The previous two files established what an enum *is*. This one is what you do with it: the two collections built specifically for enum keys, and why they are not merely faster but a different complexity class; `switch`, and the choice between an exhaustive expression and a `default`, which is the single most consequential style decision in an enum-heavy codebase; and the interface-plus-strategy pattern that turns an enum into a dispatch table. [`01c-production-patterns-and-guarantees.md`](01c-production-patterns-and-guarantees.md) continues with the persisted-code pattern, the serialization and reflection guarantees, and the hand-written ancestor Java 5 automated.

[`01-basics.md`](01-basics.md) owns the enum as a class, constant bodies and the uniqueness guarantee. [`01a-implicit-members-and-identity.md`](01a-implicit-members-and-identity.md) owns `values()`, `valueOf`, `ordinal()` and `hashCode()`. The bytecode underneath `switch` — the synthetic `$SwitchMap` holder class and its swallowed `NoSuchFieldError` — is [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md); the bit-vector and array layouts of `EnumSet`/`EnumMap` are [`03c-internals-enumset-enummap.md`](03c-internals-enumset-enummap.md).

All bytecode, compiler diagnostics and runtime results below were measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, with version comparisons against **Oracle JDK 17.0.15** and **Oracle JDK 11.0.27**. Quoted library source is from JDK 21.0.7's `lib/src.zip`. The enum under test is the ten-constant `RestrictionType` from [`01-basics.md`](01-basics.md).

---

## 1. `EnumMap` and `EnumSet` — an array and a bit, not a hash table (1.18.11)

The mental model is the whole concept: **an enum constant already carries a small dense integer, so a collection keyed on it does not need to hash anything.** `EnumSet` is one `long` with a bit per constant. `EnumMap` is one `Object[]` with a slot per constant. No hashing, no buckets, no collisions, no load factor, no resize, no `Node` objects, and — because the index is the ordinal — iteration in declaration order for free.

### Why it exists

A `HashMap<RestrictionType, V>` works, but it pays for generality it does not need. Every `get` computes `hashCode()` (an identity-hash read), spreads it, masks it to a bucket, follows a chain and calls `equals`. Every `put` may allocate a `Node` and may trigger a resize-and-rehash. And the iteration order it gives you is a function of that run's identity hashes, which [`01a`](01a-implicit-members-and-identity.md) concept 5 shows is not reproducible. Since the key set is closed, finite, and already numbered 0..n−1 at compile time, all of that is avoidable: index an array directly. `EnumSet` goes further — for a set, the value is one bit, so the whole set fits in a machine word and set algebra becomes single bitwise instructions.

### The mechanism

`[SOURCE]` `EnumSet` is abstract with two implementations, chosen by constant count:

```java
public static <E extends Enum<E>> EnumSet<E> noneOf(Class<E> elementType) {
    Enum<?>[] universe = getUniverse(elementType);
    if (universe == null)
        throw new ClassCastException(elementType + " not an enum");

    if (universe.length <= 64)
        return new RegularEnumSet<>(elementType, universe);
    else
        return new JumboEnumSet<>(elementType, universe);
}
```

Measured on JDK 21.0.7 with purpose-built enums: 64 constants gave `java.util.RegularEnumSet`; 65 gave `java.util.JumboEnumSet`. The boundary is `<= 64`, exactly as the source says, because `RegularEnumSet`'s state is one `long`.

`RegularEnumSet`'s entire state, and the three operations that matter:

```java
private long elements = 0L;

public boolean add(E e) {
    typeCheck(e);
    long oldElements = elements;
    elements |= (1L << ((Enum<?>)e).ordinal());
    return elements != oldElements;
}

public boolean contains(Object e) {
    if (e == null)
        return false;
    Class<?> eClass = e.getClass();
    if (eClass != elementType && eClass.getSuperclass() != elementType)
        return false;

    return (elements & (1L << ((Enum<?>)e).ordinal())) != 0;
}

public int size() {
    return Long.bitCount(elements);
}
```

Read `add`: one shift, one OR, one comparison. `contains`: one shift, one AND, one comparison. `size()`: `Long.bitCount`, which HotSpot intrinsifies to a single `POPCNT` instruction on any modern x86-64 or aarch64 — so `size()` on an `EnumSet` is O(1) with a constant of one instruction, whereas `HashSet.size()` is a field read and `TreeSet.size()` is a field read but `Collections.frequency`-style counting is not. Note the double class test in `contains`: `eClass.getSuperclass() != elementType` is there for constants with bodies, whose `getClass()` is `E$n` rather than `E` — the same accommodation `Enum.compareTo` makes, for the same reason.

Bulk operations become one instruction each:

```java
public boolean containsAll(Collection<?> c) {
    if (!(c instanceof RegularEnumSet<?> es))
        return super.containsAll(c);

    if (es.elementType != elementType)
        return es.isEmpty();

    return (es.elements & ~elements) == 0;
}
```

`containsAll` between two `RegularEnumSet`s of the same type is `(other & ~this) == 0` — a NOT, an AND and a compare, regardless of set sizes. The equivalent on `HashSet` iterates the argument and hashes each element. `addAll` is an OR, `retainAll` an AND, `removeAll` an AND-NOT, `complement` a NOT plus a mask that clears the bits above `universe.length`:

```java
void complement() {
    if (universe.length != 0) {
        elements = ~elements;
        elements &= -1L >>> -universe.length;  // Mask unused bits
    }
}
```

`-1L >>> -universe.length` is a small piece of shift-masking cleverness: the shift distance is masked to 6 bits for a `long`, so `>>> -10` is `>>> 54`, which turns `-1L` (all ones) into ten low ones. Shift masking is in [`../primitives-and-conversions/01b-shifts-and-unsigned.md`](../primitives-and-conversions/01b-shifts-and-unsigned.md).

`EnumMap`'s state, and its two operations:

```java
private transient K[] keyUniverse;
/**
 * Array representation of this map.  The ith element is the value
 * to which universe[i] is currently mapped, or null if it isn't
 * mapped to anything, or NULL if it's mapped to null.
 */
private transient Object[] vals;
private transient int size = 0;

public V get(Object key) {
    return (isValidKey(key) ?
            unmaskNull(vals[((Enum<?>)key).ordinal()]) : null);
}

public V put(K key, V value) {
    typeCheck(key);

    int index = key.ordinal();
    Object oldValue = vals[index];
    vals[index] = maskNull(value);
    if (oldValue == null)
        size++;
    return unmaskNull(oldValue);
}
```

`get` is one array load. `put` is one array store plus a counter. `keyUniverse` is the shared array — `getKeyUniverse` is `SharedSecrets.getJavaLangAccess().getEnumConstantsShared(keyType)`, so it is not cloned per map, which is why constructing an `EnumMap` does not pay a `values()` clone.

**Insight:** the `NULL` sentinel is the detail that makes `EnumMap` a correct `Map` rather than an approximation.

```java
private static final Object NULL = new Object() {
    public int hashCode() {
        return 0;
    }

    public String toString() {
        return "java.util.EnumMap.NULL";
    }
};

private Object maskNull(Object value) {
    return (value == null ? NULL : value);
}
```

A single `Object[]` cannot distinguish "not mapped" from "mapped to null" if both are `null`, so a null *value* is stored as the `NULL` singleton and unmasked on the way out. Measured, confirming it works: putting `SELF_EXCLUDED -> "self"` and `DEPOSIT_BLOCKED -> null` gave `size = 2`, `containsKey(DEPOSIT_BLOCKED) = true`, `get(DEPOSIT_BLOCKED) = null`, and `toString` of `{DEPOSIT_BLOCKED=null, SELF_EXCLUDED=self}`. Null *keys* are rejected: measured `NullPointerException` from `put(null, "x")`, and from `EnumSet.add(null)`.

The three-way comparison, which is the shape of the answer to "why not just use a `HashMap`":

| | `EnumSet` / `EnumMap` | `HashSet` / `HashMap` | `TreeSet` / `TreeMap` |
|---|---|---|---|
| Lookup | one shift+AND, or one array load | hash, spread, mask, chain walk, `equals` | O(log n) comparisons |
| `add`/`put` | one OR, or one array store | may allocate a `Node`, may resize and rehash | O(log n), may rebalance |
| Bulk set ops | one bitwise instruction (`RegularEnumSet`) | iterate and hash each element | iterate |
| `size()` | `Long.bitCount` — one `POPCNT` | field read | field read |
| Memory | one `long`, or 4 bytes per **declared** constant | per-entry `Node` plus a table | per-entry node plus two child links |
| Iteration order | **declaration order**, guaranteed | this run's identity hashes — not reproducible | comparator order |
| Null key | `NullPointerException` | one null key permitted (`HashMap`) | `NullPointerException` |
| Null value | permitted, via the `NULL` sentinel | permitted | permitted |
| Cost profile | flat in occupancy, linear in **declared constants** | linear in occupancy | linear in occupancy |

The last row is the trade-off, and it is the only one that ever argues against `EnumMap`: an `EnumMap` over a 200-constant enum holding one entry still allocates a 200-slot array. The arithmetic is in [`03b`](03c-internals-enumset-enummap.md).

### Diagram

The memory layouts — the labelled bit positions in `RegularEnumSet`'s `long`, `add` as `elements |= 1L << ordinal`, a union as one `|`, and `EnumMap`'s ordinal-indexed `vals` with its `keyUniverse` and `NULL` sentinel — are drawn as D-119 in [`03c-internals-enumset-enummap.md`](03c-internals-enumset-enummap.md), where the byte arithmetic that goes with them lives.

### A concrete example

The restriction check, written the way it should be. `ClientRestrictions` holds an `EnumSet` per source, so a lift is a bitwise operation and a "what blocks a stake" query never allocates:

```java
public final class ClientRestrictions {

    private final EnumMap<RestrictionSource, EnumSet<RestrictionType>> bySource;

    public ClientRestrictions() {
        this.bySource = new EnumMap<>(RestrictionSource.class);
    }

    public void apply(RestrictionType type, RestrictionSource source) {
        bySource.computeIfAbsent(source, key -> EnumSet.noneOf(RestrictionType.class))
                .add(type);
    }

    /** AA-801 ACTIVATED lifts every SYSTEM_ONBOARDING restriction and nothing else. */
    public void onActivation() {
        bySource.remove(RestrictionSource.SYSTEM_ONBOARDING);
    }

    /** One OR per source. No allocation beyond the result set. */
    public EnumSet<RestrictionType> active() {
        EnumSet<RestrictionType> all = EnumSet.noneOf(RestrictionType.class);
        for (EnumSet<RestrictionType> fromOneSource : bySource.values()) {
            all.addAll(fromOneSource);
        }
        return all;
    }

    public boolean blocks(RestrictionType.MoneyAction action) {
        for (RestrictionType type : active()) {
            if (type.blocks(action)) {
                return true;
            }
        }
        return false;
    }

    /** Only an operator-reversible restriction may be lifted by an operator. */
    public boolean lift(RestrictionType type, RestrictionSource source) {
        if (!source.reversibleByOperator()) {
            return false;
        }
        EnumSet<RestrictionType> fromOneSource = bySource.get(source);
        return fromOneSource != null && fromOneSource.remove(type);
    }
}
```

`bySource.remove(SYSTEM_ONBOARDING)` is the whole activation lift, and it is correct precisely because restriction identity is the (type, source) pair: `STAKE_BLOCKED` from `SYSTEM_ONBOARDING` disappears while the same type from `ADMIN` survives, with no filtering logic at all. `active()` is one OR per populated source.

The factory methods worth knowing, all measured:

```java
EnumSet.noneOf(RestrictionType.class)                  // empty
EnumSet.allOf(RestrictionType.class)                   // all ten, no values() clone
EnumSet.of(SELF_EXCLUDED, COOLING_OFF)                 // varargs and 1..5-arg overloads
EnumSet.range(DEPOSIT_BLOCKED, DEPOSIT_LIMITED)        // a declaration-order slice
EnumSet.complementOf(selfServiceSet)                   // one NOT plus a mask
EnumSet.copyOf(anotherEnumSet)                         // one field copy
```

Measured results on `RestrictionType`:

```
EnumSet.of(SELF_EXCLUDED, COOLING_OFF).getClass()      -> java.util.RegularEnumSet
range(DEPOSIT_BLOCKED, DEPOSIT_LIMITED)                -> [DEPOSIT_BLOCKED, STAKE_BLOCKED,
                                                            WITHDRAWAL_BLOCKED, DEPOSIT_LIMITED]
complementOf(of(SELF_EXCLUDED, COOLING_OFF))           -> the other eight, in declaration order
```

`range` takes ordinal bounds, both inclusive, so it is a *declaration-order* slice and its meaning changes if the declaration is reordered. It is the one `EnumSet` factory that makes the ordinal load-bearing in your source; use it only when declaration order is itself meaningful (a lifecycle, a severity ladder), and prefer `EnumSet.of` listing the constants explicitly otherwise.

### The gotcha

**Pitfall:** `EnumSet.copyOf(Collection)` throws on an empty non-`EnumSet` collection. Measured:

```
EnumSet.copyOf(new ArrayList<RestrictionType>())
  ->  java.lang.IllegalArgumentException: Collection is empty
```

The reason is structural: `EnumSet` needs the element *type* to size and type-check itself, and it obtains that from the first element when the argument is a plain `Collection`. An empty `EnumSet` argument is fine — the type is carried in the set's own `elementType` field — but an empty `List` carries no type at runtime, because of erasure. Symptom: a method that builds an `EnumSet` from a filtered list works in every test with data and throws `IllegalArgumentException` the first time the filter matches nothing, which in a restrictions model is the *normal* case for an unrestricted client. Fix: `EnumSet.copyOf` only when you know the collection is non-empty, otherwise

```java
EnumSet<RestrictionType> set = EnumSet.noneOf(RestrictionType.class);
set.addAll(maybeEmptyList);
```

which is unconditionally safe and costs one extra object. Erasure's role here is in [`../generics/03-internals-erasure.md`](../generics/03-internals-erasure.md).

> **Definition.** `EnumMap` is an ordinal-indexed `Object[]` with a `NULL` sentinel for null values, and `EnumSet` is a `long` bit vector (`RegularEnumSet`, up to 64 constants) or a `long[]` (`JumboEnumSet`, above 64); both iterate in declaration order and both cost space proportional to the number of *declared* constants rather than to occupancy.

---

## 2. Enums in `switch` — unqualified labels, and the `default` decision (1.18.12)

The switch is where the enum's closed-set property becomes a compiler feature rather than a documentation claim. Two things are worth getting exactly right: what a case label may be spelled as, which changed in Java 21; and whether to write a `default`, which is the single most consequential style decision in an enum-heavy codebase because it decides whether adding a constant is a compile error or a silent behaviour change.

### Why it exists

A `switch` over `int` constants cannot know it has covered everything. A `switch` over an enum can, because the constant set is fixed in the class file — so the compiler can check exhaustiveness, and a switch *expression* must produce a value on every path and therefore must be exhaustive. That turns "did I handle the new constant?" from a code-review question into a compiler diagnostic. The unqualified-label rule exists because the selector expression's type already names the enum, so repeating it was redundant — and because in the original design the label had to be resolvable to a constant of exactly that type, which qualification made ambiguous with a field access.

### The mechanism

**Label spelling — and this changed in 21.** Historically an enum case label *had* to be the unqualified constant name. Measured on JDK 17.0.15, compiling `case RestrictionType.SELF_EXCLUDED ->` in a switch whose selector is a `RestrictionType`:

```
error: an enum switch case label must be the unqualified name of an enumeration constant
            case RestrictionType.SELF_EXCLUDED -> "self";
                                ^
```

The same source compiles clean on **JDK 21.0.7**. JEP 441 (*Pattern Matching for switch*, final in 21) relaxed the rule so a qualified enum constant is permitted as a case label — which it had to, because a pattern switch's selector may be `Object`, where an unqualified name has no type to resolve against. Measured on 21, a pattern switch over `Object`:

```java
static String qualified(Object o) {
    return switch (o) {
        case RestrictionType.SELF_EXCLUDED -> "qualified label worked";
        case RestrictionType t -> "other restriction " + t;
        default -> "not a restriction";
    };
}
```

Measured output: `SELF_EXCLUDED` → `"qualified label worked"`, `ALL_BLOCKED` → `"other restriction ALL_BLOCKED"`, `"x"` → `"not a restriction"`. So the current rule in 21 is: **unqualified is always legal when the selector's type is the enum; qualified is legal too, and is required when the selector is a supertype.** The **version trap** is the direction of the change — every pre-21 book, blog and Stack Overflow answer states the unqualified form as a hard rule, and a candidate who quotes it as still absolute is a version behind. State it as: unqualified was mandatory through 20; qualification became permitted in 21.

**Exhaustiveness.** A switch *statement* over an enum has never required exhaustiveness — an unhandled constant simply falls through and does nothing (or hits `default`). A switch *expression* must be exhaustive, and for an enum selector the compiler accepts "every constant is covered" as exhaustive with **no `default` needed**:

```java
public String route(RestrictionType type) {
    return switch (type) {
        case DEPOSIT_BLOCKED, DEPOSIT_LIMITED -> "DEPOSIT";
        case STAKE_BLOCKED -> "STAKE";
        case WITHDRAWAL_BLOCKED, WITHDRAWAL_HELD -> "WITHDRAWAL";
        case SOURCE_OF_FUNDS_REQUIRED -> "SOF";
        case ALL_BLOCKED -> "ALL";
        case SELF_EXCLUDED, COOLING_OFF -> "SELF_SERVICE";
        case DORMANT_FROZEN -> "DORMANT";
    };
}
```

Add an eleventh constant and this **fails to compile**: `the switch expression does not cover all possible input values`. That is the property you want, and it is why the `default` decision matters.

**The `default` trade-off, stated as a decision rather than a preference:**

| | Exhaustive, no `default` | With a `default` |
|---|---|---|
| Adding a constant | **compile error** at every switch — you are forced to decide | silently routes to `default` |
| Removing a constant | compile error at the switch (the label names a constant that is gone) | same |
| Old class + new enum at **runtime** | throws `MatchException` on the new constant (JDK 21) or `IncompatibleClassChangeError` (17) | falls to `default` |
| Reordering constants | no effect — the `$SwitchMap` absorbs it | no effect |
| Reads as | "these are all the cases; the compiler agrees" | "these are the cases I thought of" |

So: **for a switch you own over an enum you own, omit `default`** — the compile error is the entire benefit of using an enum. Where you genuinely cannot enumerate (an enum from a library that may grow, a value decoded from a wire), keep a `default` and make it *loud*: log with the offending value and fail the operation, rather than picking a benign-looking fallback. The one shape to avoid is a `default` that silently does the safe-sounding thing, because that converts "we added `WAGERING_HELD` and forgot to handle it" from a build failure into a production behaviour nobody notices.

There is a runtime dimension too, and it is the reason a `default`-free exhaustive switch is not *entirely* free. If the enum is recompiled with a new constant but the switching class is not, the exhaustiveness the compiler proved no longer holds, and the JVM has to do something. Measured on **JDK 21.0.7**, exactly that scenario against the exhaustive switch above with `WAGERING_HELD` appended to the enum:

```
  WAGERING_HELD -> THREW java.lang.MatchException: null
```

and on **JDK 17.0.15**, the same experiment:

```
  WAGERING_HELD -> THREW java.lang.IncompatibleClassChangeError: null
```

Both have a `null` message, which is unhelpful, and neither is catchable in any useful sense. The full experiment and the bytecode that produces it are in [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md).

Two more rules that catch people:

- **A `case null` label is legal in a pattern switch (Java 21) but not in a plain enum switch.** An enum switch with a `null` selector throws `NullPointerException` at the `invokevirtual ordinal()` — measured behaviour that predates and survives every version here. So `switch (type)` on a possibly-null `type` needs a null check first, unless you make it a pattern switch with `case null`.
- **The `default` in a switch *statement* is optional and its absence is not an error**, which is why upgrading a statement to an expression is the cheap way to get the exhaustiveness check retroactively.

### Diagram

The `$SwitchMap` mechanism underneath every enum switch — the synthetic holder class, its `<clinit>` with one swallowed `NoSuchFieldError` per entry, the `tableswitch` over the mapped index, and the binary-compatibility experiment — is D-118, embedded in [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md). The language-side treatment of `String` and enum switch is in [`../control-flow/01b-string-and-enum-switch.md`](../control-flow/01b-string-and-enum-switch.md).

### A concrete example

The two shapes side by side, in the place where the choice has consequences:

```java
public final class RestrictionRouter {

    /**
     * Exhaustive, no default. Adding a RestrictionType is a compile error here,
     * which is exactly what we want: a new restriction must be routed deliberately.
     */
    public static Queue route(RestrictionType type) {
        return switch (type) {
            case DEPOSIT_BLOCKED, DEPOSIT_LIMITED -> Queue.PAYMENTS;
            case STAKE_BLOCKED -> Queue.TRADING;
            case WITHDRAWAL_BLOCKED, WITHDRAWAL_HELD -> Queue.PAYMENTS;
            case SOURCE_OF_FUNDS_REQUIRED -> Queue.COMPLIANCE;
            case ALL_BLOCKED -> Queue.COMPLIANCE;
            case SELF_EXCLUDED, COOLING_OFF -> Queue.SELF_SERVICE;
            case DORMANT_FROZEN -> Queue.LIFECYCLE;
        };
    }

    /**
     * A default is right here, because the code arrived over the wire and may name
     * a restriction this deployment has never heard of. Note it is loud, not benign.
     */
    public static Queue routeFromWire(String code) {
        RestrictionType type = RestrictionType.fromCode(code).orElse(null);
        if (type == null) {
            throw new IllegalArgumentException("unroutable restriction code from wire: " + code);
        }
        return route(type);
    }

    public enum Queue { PAYMENTS, TRADING, COMPLIANCE, SELF_SERVICE, LIFECYCLE }
}
```

`routeFromWire` is the honest version of "handle the unknown": the tolerance lives at the parse boundary, where the string is still available to put in the message, and the switch itself stays exhaustive. That separation is the pattern — **tolerate unknown values at the edge, be exhaustive in the core** — and it is why the `default` question usually has a structural answer rather than a stylistic one.

### The gotcha

**Pitfall:** a `default` branch that returns a plausible fallback.

```java
default -> Queue.COMPLIANCE;   // "compliance can triage anything"
```

It compiles, it is defensible in a design review, and it means that the day someone adds `WAGERING_HELD` the build stays green and every wagering-hold restriction quietly lands in the compliance queue — a queue staffed at 40 operators steady handling 22 cases per operator per hour, now receiving traffic it has no procedure for. Symptom: no error anywhere, a queue's volume rising, and a discovery weeks later that a restriction type has never been actioned. Fix: omit the `default` so the compiler stops you, or — where you cannot — `default -> throw new IllegalStateException("unrouted restriction: " + type);`. A `default` that throws still gives you a runtime failure rather than a compile-time one, but a loud runtime failure on the first request beats silence.

> **Definition.** An enum case label may be the unqualified constant name in any enum switch, and since Java 21 (JEP 441) may also be qualified; a switch *expression* over an enum is exhaustive without a `default` when every constant is covered, which makes adding a constant a compile error at every such switch — the property that is the reason to omit `default` wherever you own the enum.

---

## 3. Enums implementing an interface, and the strategy-enum pattern (1.18.13)

An enum cannot extend a class, but it can implement any number of interfaces — and because each constant may carry its own body, an enum is a natural closed set of *implementations*. That is the strategy-enum: a fixed, named, exhaustively-switchable family of behaviours, each a singleton, with a compiler-checked registry (`values()`) and free serialization safety.

### Why it exists

The classic strategy pattern needs an interface, one class per strategy, and a registry to look them up by name or key — three files and a map for what is conceptually a closed list. If the list really is closed, an enum collapses all of it: the interface stays, the implementations become constants, and the registry becomes `values()` or a static `Map` built from it. You also gain the things an enum gives for free and a class hierarchy does not: guaranteed single instances, a stable `name()` for logging and persistence, declaration-order iteration, and `EnumMap`/`EnumSet` for any collection keyed on the strategy.

### The mechanism

Two shapes, and they compose.

**Form one: the enum implements the interface, each constant supplies the behaviour.** Every constant is an implementation, and `values()` is the registry. The interface may be one you own or a standard one — `Comparator`, `Predicate`, `Supplier`, `BiFunction` are all legitimate, and an enum implementing `Comparator<T>` is the idiomatic way to ship a fixed set of orderings as named singletons.

**Form two: the enum is a *key* into behaviour held elsewhere**, usually an `EnumMap` built in a holder class. Reach for this when the behaviour has dependencies (a service, a clock, a repository) that an enum constant cannot inject — an enum constant is created in `<clinit>` with no access to your container, so any strategy needing collaborators has to be looked up rather than embodied.

The distinction is worth naming because getting it wrong is the most common way an enum-based design goes bad: **behaviour that is pure and dependency-free belongs on the constant; behaviour that needs collaborators belongs in a map keyed by the constant.** An enum constant that reaches for a static service locator to get its dependencies has reinvented the global-state problem that made service locators unfashionable.

One further property, only available to enums: because an enum implementing an interface is still an enum, a `switch` over it is still exhaustiveness-checked, so you can have polymorphic dispatch *and* a compiler-checked total function over the same type. A sealed interface with record implementations gives you the exhaustiveness (see [`../records-and-sealed/01-basics.md`](../records-and-sealed/01-basics.md)) but not the singleton-ness or the `EnumSet`; an enum gives you both, at the cost of the implementations being stateless.

### Diagram

No diagram for this concept: the content is two code shapes and the rule for choosing between them, and the code below is the clearer rendering.

### A concrete example

The stake-split strategy. The domain's rule is that a stake draws `min(BONUS_AVAILABLE, 10% of stake)` from bonus and the remainder from cash, with the bonus portion **rounding down** to the minor unit — the canonical case being a stake of **3.33** splitting as **0.33 bonus + 3.00 cash**, because rounding the other way would produce 0.34 + 3.00 = 3.34 and create money. Different promotions need different splits, the list is closed, and the behaviour is pure arithmetic:

```java
public enum StakeSplitPolicy implements BiFunction<Money, Money, StakeSplit> {

    /** The standard rule: up to 10% of the stake from bonus, rounded down. */
    PROPORTIONAL_TEN_PERCENT {
        @Override public StakeSplit apply(Money stake, Money bonusAvailable) {
            BigDecimal cap = stake.amount()
                                  .multiply(new BigDecimal("0.10"))
                                  .setScale(2, RoundingMode.DOWN);
            BigDecimal fromBonus = cap.min(bonusAvailable.amount());
            return split(stake, fromBonus);
        }
    },

    /** Promotions that let bonus cover the whole stake, still rounded down. */
    BONUS_FIRST {
        @Override public StakeSplit apply(Money stake, Money bonusAvailable) {
            BigDecimal fromBonus = stake.amount()
                                        .min(bonusAvailable.amount())
                                        .setScale(2, RoundingMode.DOWN);
            return split(stake, fromBonus);
        }
    },

    /** Restricted clients: cash only, bonus untouched. */
    CASH_ONLY {
        @Override public StakeSplit apply(Money stake, Money bonusAvailable) {
            return split(stake, BigDecimal.ZERO.setScale(2, RoundingMode.UNNECESSARY));
        }
    };

    /** Shared helper. The invariant is that the two portions sum exactly to the stake. */
    private static StakeSplit split(Money stake, BigDecimal fromBonus) {
        BigDecimal fromCash = stake.amount().subtract(fromBonus);
        StakeSplit result = new StakeSplit(
            new Money(fromBonus, stake.currency()),
            new Money(fromCash, stake.currency()));
        if (result.bonusPortion().amount().add(result.cashPortion().amount())
                  .compareTo(stake.amount()) != 0) {
            throw new IllegalStateException("stake split does not sum to the stake: " + result);
        }
        return result;
    }
}
```

Three properties this has that three separate strategy classes would not. The invariant check lives in one `private static` helper that every constant routes through, so no implementation can violate it. `StakeSplitPolicy.valueOf(configuredName)` is the whole configuration story — no registry, no bean scanning, no reflection. And a `switch` over `StakeSplitPolicy` elsewhere in the codebase is still exhaustiveness-checked, so adding a fourth policy is a compile error at every place that must decide about it.

For `PROPORTIONAL_TEN_PERCENT` with a stake of 3.33 and 10.00 bonus available: `3.33 × 0.10 = 0.333`, `setScale(2, DOWN)` gives `0.33`, `min(0.33, 10.00)` is `0.33`, cash covers `3.33 − 0.33 = 3.00`. The invariant holds exactly, and it holds because the cash portion is computed by subtraction rather than by a second rounding. `BigDecimal` scale and `RoundingMode` are in [`../numbers-and-money/02-numbers-and-money.md`](../numbers-and-money/02-numbers-and-money.md).

Now form two, where the behaviour needs a collaborator:

```java
public enum GateCheck {
    AGE_ELIGIBILITY, JURISDICTION, DUPLICATE_IDENTITY, WEALTH, SCREENING, DOCUMENTS;

    public interface Check {
        Verdict evaluate(Application application);
    }
}

@Component
public final class GateSet {

    private final Map<GateCheck, GateCheck.Check> checks;

    public GateSet(AssessmentService assessment,
                   ScreeningService screening,
                   DocumentVerification documents) {
        EnumMap<GateCheck, GateCheck.Check> map = new EnumMap<>(GateCheck.class);
        map.put(GateCheck.AGE_ELIGIBILITY, application ->
            application.applicantAge() >= 18
                ? Verdict.pass()
                : Verdict.fail("AO-119"));
        map.put(GateCheck.JURISDICTION, application ->
            application.jurisdiction().isPermitted()
                ? Verdict.pass()
                : Verdict.fail("AO-129"));
        map.put(GateCheck.DUPLICATE_IDENTITY, application ->
            assessment.isDuplicate(application.personId())
                ? Verdict.fail("AO-139")
                : Verdict.pass());
        map.put(GateCheck.WEALTH, application -> assessment.assessWealth(application));
        map.put(GateCheck.SCREENING, application -> screening.screen(application));
        map.put(GateCheck.DOCUMENTS, application -> documents.verify(application));

        // Every declared gate must have a check. Fail at startup, not at first request.
        for (GateCheck gate : GateCheck.values()) {
            if (!map.containsKey(gate)) {
                throw new IllegalStateException("no check registered for gate " + gate);
            }
        }
        this.checks = Collections.unmodifiableMap(map);
    }

    public Optional<GateCheck> firstFailing(Application application) {
        for (Map.Entry<GateCheck, GateCheck.Check> entry : checks.entrySet()) {
            if (!entry.getValue().evaluate(application).passed()) {
                return Optional.of(entry.getKey());
            }
        }
        return Optional.empty();
    }
}
```

Two details do real work. The completeness loop over `values()` turns "somebody added a gate and forgot to wire it" into a startup failure naming the gate — the runtime equivalent of the compile error an exhaustive switch would have given, and the best available substitute when the dispatch table is built at runtime. And because `checks` is an `EnumMap`, `firstFailing` evaluates gates in **declaration order**, which is the onboarding journey's order: age and jurisdiction before duplicate checks before wealth before screening before documents. Reordering the enum reorders the journey, deliberately and visibly, in one place.

### The gotcha

**Pitfall:** an enum constant that acquires dependencies through a static holder.

```java
// Wrong.
SCREENING {
    @Override public Verdict evaluate(Application application) {
        return ServiceRegistry.get(ScreeningService.class).screen(application);
    }
}
```

The constant is created during `<clinit>`, so it cannot be given collaborators; reaching for a static registry is the only way to make this shape work, and it brings back everything a container exists to avoid. Symptom: the class cannot be unit-tested without initialising the registry; a test that stubs the service leaks the stub into every later test in the JVM, because the constant is a `static final` field that outlives the test; and the order of class initialisation between the enum and the registry becomes load-bearing, which is how you get an `ExceptionInInitializerError` that reproduces only in CI. Fix: form two — keep the enum as a pure key and put the behaviour in an `EnumMap` built by the constructor of an ordinary injected component, with the `values()` completeness check to keep the two in step.

> **Definition.** An enum may implement any number of interfaces, making each constant a named singleton implementation; put dependency-free behaviour in constant bodies, and hold behaviour with collaborators in an `EnumMap` keyed by the constant, guarded by a `values()` completeness check at construction.

---

## Pitfalls

### `EnumSet.copyOf` on a possibly-empty list

**Wrong**

```java
public EnumSet<RestrictionType> blockingRestrictions(List<Restriction> all,
                                                     MoneyAction action) {
    List<RestrictionType> blocking = all.stream()
        .map(Restriction::type)
        .filter(type -> type.blocks(action))
        .toList();
    return EnumSet.copyOf(blocking);
}
```

For an unrestricted client — the *normal* case — `blocking` is empty and this throws. Measured: `java.lang.IllegalArgumentException: Collection is empty`. `EnumSet` needs the element type to size and type-check itself, and for a plain `Collection` it takes that from the first element; erasure means an empty `List<RestrictionType>` carries no type at runtime.

**Right**

```java
public EnumSet<RestrictionType> blockingRestrictions(List<Restriction> all,
                                                     MoneyAction action) {
    EnumSet<RestrictionType> blocking = EnumSet.noneOf(RestrictionType.class);
    for (Restriction restriction : all) {
        if (restriction.type().blocks(action)) {
            blocking.add(restriction.type());
        }
    }
    return blocking;
}
```

The `Class` literal supplies the type unconditionally, so the empty case is the cheap case. The stream form works too, with an explicit collector: `.collect(Collectors.toCollection(() -> EnumSet.noneOf(RestrictionType.class)))`.

**Why people believe it:** `EnumSet.copyOf(EnumSet)` accepts an empty argument happily, because an `EnumSet` carries its own `elementType`. The overload that fails is the `Collection` one, and the two are spelled identically at the call site.

### A `default` branch that quietly absorbs new constants

**Wrong**

```java
public Queue route(RestrictionType type) {
    return switch (type) {
        case STAKE_BLOCKED -> Queue.TRADING;
        case SELF_EXCLUDED, COOLING_OFF -> Queue.SELF_SERVICE;
        case SOURCE_OF_FUNDS_REQUIRED, ALL_BLOCKED -> Queue.COMPLIANCE;
        default -> Queue.COMPLIANCE;
    };
}
```

Green build forever. Add `WAGERING_HELD` and every wagering hold silently joins the compliance queue, which has no procedure for it — 40 operators steady at 22 cases/hour receiving a case type they cannot action.

**Right**

```java
public Queue route(RestrictionType type) {
    return switch (type) {
        case DEPOSIT_BLOCKED, DEPOSIT_LIMITED -> Queue.PAYMENTS;
        case STAKE_BLOCKED -> Queue.TRADING;
        case WITHDRAWAL_BLOCKED, WITHDRAWAL_HELD -> Queue.PAYMENTS;
        case SOURCE_OF_FUNDS_REQUIRED -> Queue.COMPLIANCE;
        case ALL_BLOCKED -> Queue.COMPLIANCE;
        case SELF_EXCLUDED, COOLING_OFF -> Queue.SELF_SERVICE;
        case DORMANT_FROZEN -> Queue.LIFECYCLE;
    };
}
```

No `default`, every constant listed, so the switch expression is exhaustive and adding a constant produces `error: the switch expression does not cover all possible input values` at this line. Where a `default` is genuinely unavoidable — an enum owned by a library — make it `default -> throw new IllegalStateException("unrouted restriction: " + type);`.

**Why people believe it:** defensive programming is a good instinct, and a `default` looks like defence. It is the opposite here: the enum's closed set is a *guarantee*, and a `default` is the code telling the compiler to stop enforcing it.

### An enum constant that fetches its own dependencies

**Wrong**

```java
public enum GateCheck {
    SCREENING {
        @Override public Verdict evaluate(Application application) {
            return ServiceRegistry.get(ScreeningService.class).screen(application);
        }
    };
    public abstract Verdict evaluate(Application application);
}
```

The constant is created in `<clinit>` and cannot be injected, so a static locator is the only way to make it work. Now the enum cannot be initialised without the registry, a stubbed service leaks into every subsequent test in the JVM because the constant is a `static final` field, and the class-init order between the enum and the registry is load-bearing.

**Right**

```java
public enum GateCheck { AGE_ELIGIBILITY, JURISDICTION, WEALTH, SCREENING, DOCUMENTS }

@Component
public final class GateSet {
    private final Map<GateCheck, Check> checks;

    public GateSet(AssessmentService assessment, ScreeningService screening,
                   DocumentVerification documents) {
        EnumMap<GateCheck, Check> map = new EnumMap<>(GateCheck.class);
        map.put(GateCheck.SCREENING, screening::screen);
        map.put(GateCheck.WEALTH, assessment::assessWealth);
        map.put(GateCheck.DOCUMENTS, documents::verify);
        map.put(GateCheck.AGE_ELIGIBILITY, application ->
            application.applicantAge() >= 18 ? Verdict.pass() : Verdict.fail("AO-119"));
        map.put(GateCheck.JURISDICTION, application ->
            application.jurisdiction().isPermitted() ? Verdict.pass() : Verdict.fail("AO-129"));
        for (GateCheck gate : GateCheck.values()) {
            if (!map.containsKey(gate)) {
                throw new IllegalStateException("no check registered for gate " + gate);
            }
        }
        this.checks = Collections.unmodifiableMap(map);
    }

    public interface Check { Verdict evaluate(Application application); }
}
```

The enum is a pure key. The behaviour lives in an injected component, the `EnumMap` gives declaration-order evaluation for free, and the `values()` completeness loop turns a forgotten wiring into a startup failure naming the gate.

**Why people believe it:** constant-specific bodies are genuinely the elegant answer when the behaviour is pure, and the strategy-enum pattern is widely and correctly recommended. The line the recommendation usually omits is that it only holds for dependency-free behaviour.

---

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `EnumSet` implementation split | `universe.length <= 64` → `RegularEnumSet` (one `long`); `> 64` → `JumboEnumSet` (`long[]`). Measured at 64 and 65 |
| `RegularEnumSet` state | `private long elements = 0L;` plus inherited `elementType` and the shared `universe` |
| `RegularEnumSet.add` | `elements \|= (1L << ordinal)` |
| `RegularEnumSet.contains` | `(elements & (1L << ordinal)) != 0`, after a two-way class check for body constants |
| `RegularEnumSet.size()` | `Long.bitCount(elements)` — a HotSpot intrinsic, not an iteration |
| Bulk set ops | `addAll` = OR, `retainAll` = AND, `removeAll` = AND-NOT, `containsAll` = `(other & ~this) == 0`, `complement` = NOT + mask |
| `complement`'s mask | `elements &= -1L >>> -universe.length` — shift masking to 6 bits does the work |
| `EnumSet`/`EnumMap` universe | `getEnumConstantsShared()` — the shared array, **no** `values()` clone |
| `EnumMap` state | `Object[] vals` indexed by ordinal, plus a shared `keyUniverse` and an `int size` |
| `EnumMap.get` / `put` | one array load / one array store plus a counter — no hashing at all |
| `EnumMap` null value | stored as the `NULL` sentinel singleton, so "mapped to null" differs from "not mapped" |
| Null key | `NullPointerException` from both `EnumMap.put` and `EnumSet.add` — measured |
| Iteration order | **declaration order**, both. The reason to prefer them over `HashMap`/`HashSet` in any output path |
| Cost profile | flat in occupancy, linear in **declared** constants. A 1-entry `EnumMap` over 200 constants still allocates 200 slots |
| `EnumSet.copyOf(Collection)` | throws `IllegalArgumentException: Collection is empty` on an empty non-`EnumSet`. Use `noneOf` + `addAll` |
| `EnumSet.copyOf(EnumSet)` | safe when empty — the argument carries its own `elementType` |
| `EnumSet.range(a, b)` | inclusive **ordinal** slice, so declaration-order dependent. Prefer `EnumSet.of` unless order is meaningful |
| Enum case label, through Java 20 | must be the **unqualified** constant name. JDK 17 error: "an enum switch case label must be the unqualified name of an enumeration constant" |
| Enum case label, Java 21 | qualified constants permitted (JEP 441); **required** when the selector is a supertype. Version trap |
| Switch statement | exhaustiveness **not** required; an unhandled constant falls through |
| Switch expression | exhaustiveness **required**; every constant covered is accepted with **no `default`** |
| Adding a constant, no `default` | **compile error** at every exhaustive switch — the reason to omit `default` |
| Adding a constant, with `default` | silent routing to `default` — the reason not to write one |
| Old class, new enum, at runtime | `MatchException` (JDK 21) / `IncompatibleClassChangeError` (JDK 17), both with a `null` message |
| `switch` on a null enum | `NullPointerException` at `ordinal()`. `case null` is legal only in a pattern switch |
| Where to be tolerant | at the parse boundary, where the offending string is still available. Keep the switch itself exhaustive |
| Strategy enum, pure behaviour | constant bodies implementing an interface; `values()` is the registry, `valueOf` is the configuration |
| Strategy enum, with collaborators | enum as key, behaviour in an `EnumMap` built by an injected component, plus a `values()` completeness check |
| Why not a constant body with dependencies | the constant is built in `<clinit>` with no container access; a static locator brings back global state |
| Class-file cost of bodies | one extra class file per constant with a body — irrelevant at 3 constants, measurable at 200 |

---

## Self-test

**Q1.** Why is `EnumSet.containsAll` a different complexity class from `HashSet.containsAll`, and what is the exact expression?

<details><summary>Answer</summary>

Because both sets are a single `long`, so containment is a bit-mask test rather than an iteration. The JDK 21 source is `return (es.elements & ~elements) == 0;` — guarded by `if (!(c instanceof RegularEnumSet<?> es)) return super.containsAll(c);` so it only applies between two `RegularEnumSet`s, and by `if (es.elementType != elementType) return es.isEmpty();` so a set of a different enum type is only "contained" if it is empty. Read the expression: `~elements` is everything this set lacks; ANDing with the other set's bits gives the other set's members that this set lacks; `== 0` means there are none. That is a NOT, an AND and a compare — three instructions, independent of either set's size. `HashSet.containsAll` iterates the argument and does a hash lookup per element, so it is O(size of argument) with a hash and an `equals` per step. Same for the other bulk operations: `addAll` is one OR, `retainAll` one AND, `removeAll` one AND-NOT. Above 64 constants `JumboEnumSet` uses a `long[]`, so these become a loop over words — still far cheaper than hashing, but no longer a single instruction.

</details>

**Q2.** `EnumMap` allows a null value but `HashMap` and `EnumMap` differ on how. Explain the mechanism and prove it works.

<details><summary>Answer</summary>

`EnumMap` is a single `Object[] vals` indexed by ordinal, so a raw `null` in a slot is ambiguous between "no mapping" and "mapped to null". The JDK resolves it with a sentinel: `private static final Object NULL = new Object() { public int hashCode() { return 0; } public String toString() { return "java.util.EnumMap.NULL"; } };`, plus `maskNull(value)` on the way in (`value == null ? NULL : value`) and `unmaskNull` on the way out. `put` therefore does `vals[index] = maskNull(value)` and increments `size` only when the old slot was raw `null`. Measured proof on JDK 21.0.7: putting `SELF_EXCLUDED -> "self"` and `DEPOSIT_BLOCKED -> null` gave `size = 2`, `containsKey(DEPOSIT_BLOCKED) = true`, `get(DEPOSIT_BLOCKED) = null`, and `toString` of `{DEPOSIT_BLOCKED=null, SELF_EXCLUDED=self}` — so the map distinguishes the two cases correctly. Null *keys* are a different story and are rejected outright: measured `NullPointerException` from `EnumMap.put(null, "x")` and from `EnumSet.add(null)`, because both need `key.ordinal()` and there is no slot for "no key". `HashMap`, by contrast, permits one null key (bucket 0 by convention) and needs no sentinel for null values because it stores an actual `Node` whose presence is the mapping.

</details>

**Q3.** A colleague adds `default -> Queue.COMPLIANCE;` to an exhaustive enum switch "for safety". Argue against it.

<details><summary>Answer</summary>

It removes the only compiler-enforced guarantee the enum was giving you. Without a `default`, a switch expression over an enum is exhaustive only if every constant is covered, so adding an eleventh constant produces `error: the switch expression does not cover all possible input values` at every such switch in the codebase — a complete, mechanical list of the places that must decide about the new value. With a `default`, adding the constant compiles clean and routes silently to the fallback. In the routing example that means every `WAGERING_HELD` restriction lands in the compliance queue, which is staffed at 40 operators handling 22 cases/hour and has no procedure for it; nothing throws, nothing logs, and the discovery is weeks later. The "safety" the `default` buys is against a case the type system says cannot happen. There is one residual runtime risk it does cover: if the enum is recompiled with a new constant and the switching class is not, the exhaustiveness no longer holds at runtime and the JVM throws — measured as `java.lang.MatchException: null` on JDK 21.0.7 and `java.lang.IncompatibleClassChangeError: null` on JDK 17.0.15. But that is a deployment error, and a loud failure is the correct response to it. Where a `default` genuinely cannot be avoided — an enum owned by a library that may grow — write `default -> throw new IllegalStateException("unrouted restriction: " + type);` so it is still loud.

</details>

**Q4.** State the enum case-label rule for Java 21 and say what changed.

<details><summary>Answer</summary>

In Java 21 an enum case label may be either the unqualified constant name or a qualified one. Through Java 20 it had to be unqualified; measured on JDK 17.0.15, `case RestrictionType.SELF_EXCLUDED ->` in a switch whose selector is a `RestrictionType` produces `error: an enum switch case label must be the unqualified name of an enumeration constant`, and the identical source compiles clean on JDK 21.0.7. The change came with JEP 441 (*Pattern Matching for switch*, final in 21), and it was forced by the feature: a pattern switch's selector may be `Object`, where an unqualified constant name has no type to resolve against, so qualification had to become legal — and once legal there it was made legal everywhere. Measured on 21, a pattern switch over `Object` with `case RestrictionType.SELF_EXCLUDED` alongside `case RestrictionType t` and a `default` dispatched all three inputs correctly. This is a **version trap** in the awkward direction: every pre-21 source states the unqualified rule as absolute, so quoting it as still absolute marks you as a version behind. State it as: mandatory through 20, relaxed in 21, and qualification is *required* when the selector is a supertype of the enum.

</details>

**Q5.** When should behaviour go in a constant body, and when in an `EnumMap` keyed by the constant?

<details><summary>Answer</summary>

Constant body when the behaviour is pure and dependency-free; `EnumMap` when it needs collaborators. The reason is a hard constraint, not a preference: an enum constant is created during `<clinit>` with no access to any container, so a constant body cannot be injected with a service, a clock or a repository. Making it work anyway requires a static service locator, and that brings back global mutable state — the enum cannot be initialised without the registry, a stubbed service leaks into every later test in the JVM because the constant is a `static final` field, and the class-initialisation order between enum and registry becomes load-bearing, which produces an `ExceptionInInitializerError` that reproduces only in CI. The `EnumMap` shape keeps the enum a pure key and puts the dispatch table in the constructor of an ordinary injected component. It also gives you two things for free: declaration-order iteration, which for a gate set means the onboarding journey's order is the enum's declaration order in one visible place; and a natural spot for a completeness check — loop over `values()` at construction and throw naming any constant with no registered behaviour, which is the runtime substitute for the compile error an exhaustive switch would have given. The secondary consideration is class count: each constant body is an extra class file, so a 200-constant enum with bodies is 201 classes to load and verify.

</details>

**Q6.** Why does `RegularEnumSet.contains` test `eClass.getSuperclass() != elementType` as well as `eClass != elementType`?

<details><summary>Answer</summary>

For constants with class bodies. The source is `if (eClass != elementType && eClass.getSuperclass() != elementType) return false;`. A constant with a constant-specific body is compiled as an anonymous subclass, so `RestrictionSource.CLIENT.getClass()` is `RestrictionSource$1`, not `RestrictionSource` — measured. Without the second test, `contains(CLIENT)` on an `EnumSet<RestrictionSource>` would return `false` for a constant that is genuinely in the set, which would be a silent correctness bug in the collection. Checking the *superclass* works because the body subclass is exactly one level below the enum class and is itself `final`, so there is no deeper hierarchy to walk. The same accommodation appears in `Enum.compareTo` — `if (self.getClass() != other.getClass() && self.getDeclaringClass() != other.getDeclaringClass()) throw new ClassCastException();` — where the JDK comment labels the first, cheap test `// optimization`. The general lesson is the one from [`01-basics.md`](01-basics.md): `getClass()` is not the enum type for a body constant, `getDeclaringClass()` is, and JDK code that deals with enums has to accommodate both. Your code should skip the accommodation and just use `getDeclaringClass()`.

</details>

---

---

## Open questions

- **Unverified:** whether `EnumSet`'s 64-constant boundary is a specified guarantee or an implementation detail. Measured on JDK 21.0.7 that 64 constants yields `java.util.RegularEnumSet` and 65 yields `java.util.JumboEnumSet`, and the `noneOf` source reads `if (universe.length <= 64)`, so it is certainly true on this build. Both implementation classes are package-private, which suggests they are not contractual, but the `java.util.EnumSet` class-level javadoc was not read closely enough to establish whether the threshold itself is. What would settle it: that javadoc read in full. Nothing here depends on the answer beyond the class *names*, which are reported as measured output rather than as API.
- **Unverified:** whether `Long.bitCount` is intrinsified on this specific aarch64 build. The claim that `RegularEnumSet.size()` costs one instruction rests on `Long.bitCount` being a HotSpot intrinsic — it is on x86-64 via `POPCNT` and on aarch64 via `CNT` plus `ADDV` — but whether the aarch64 intrinsic is enabled by default on Oracle JDK 21.0.7 was not checked. What would settle it: `-XX:+UnlockDiagnosticVMOptions -XX:+PrintIntrinsics` on a loop calling `size()`, or reading `vmIntrinsics.hpp` for the build. The weaker claim — that `size()` is O(1) and does not iterate the set — holds unconditionally from the source quoted above.
- **Unverified:** whether the JLS specifies that an exhaustive enum switch expression must throw at runtime when the enum has gained a constant, and if so which throwable. Measured that JDK 21.0.7 throws `MatchException` and JDK 17.0.15 throws `IncompatibleClassChangeError` for the identical experiment, so the behaviour changed; whether 21's choice is normative or a `javac` implementation decision was not established. What would settle it: JLS 21 §14.11.3 ("Execution of a `switch` Statement or Expression") and the `java.lang.MatchException` javadoc, which states when the runtime throws it.

---

**Leaves covered:** 1.18.11, 1.18.12, 1.18.13 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-118 is embedded in [`03b-internals-guarantees-and-switch.md`](03b-internals-guarantees-and-switch.md) and D-119 in [`03c-internals-enumset-enummap.md`](03c-internals-enumset-enummap.md)
**Target version:** Java 21 LTS
**Lines:** 795
