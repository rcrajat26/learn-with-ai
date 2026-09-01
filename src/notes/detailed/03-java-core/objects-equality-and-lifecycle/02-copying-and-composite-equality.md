# 03 Java Core — Copying and cloning — INTERMEDIATE (§2.8, 2.8.1–2.8.8)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The rest of `Object`'s methods](01c-object-methods.md) · Next: [Composite equality and ordering](02a-composite-equality-and-ordering.md)

## Orientation

[01c](01c-object-methods.md) established that `Object.clone()` exists, is `protected native`, and hands back a shallow, field-by-field copy without ever running a constructor. This file goes underneath that: the exact aliasing three kinds of copy leave, the source-level proof that `clone()` cannot be trusted, complete shippable copy code, and a costed comparison of deep-copy strategies. Ordering (`Comparable`/`Comparator`), the stranded-key bug, JPA entity equality, and Lombok's generated `equals`/`hashCode` move to [composite equality and ordering](02a-composite-equality-and-ordering.md), because they are questions about *comparing* objects rather than *duplicating* them.

## 1. Three kinds of copy and the exact aliasing (2.8.1)

The mental model: three ways to hand someone a `Movement`. Hand them your own key (reference copy — one apartment, two keys). Hand them a new key to a new apartment furnished with your actual furniture (shallow copy — two apartments, shared furniture). Hand them a new key to a new apartment furnished with brand-new furniture built to match yours (deep copy — two apartments, nothing shared).

### Why it exists

Every mutable aggregate in QuizStakes — `Movement`, `LedgerEntry`, `LimitSet`, `Restriction` — is reached through references, and Java has no value semantics for objects. "Copy" is therefore never one operation; it is a question about how far the duplication goes down the object graph, and getting the answer wrong either aliases mutable state you meant to isolate, or wastes cycles isolating state that was never going to mutate.

### The mechanism

```java
record LedgerEntry(String position, long amountMinor, boolean reversed) { }

final class Movement {
    private final String movementId;
    private final List<LedgerEntry> entries;

    Movement(String movementId, List<LedgerEntry> entries) {
        this.movementId = movementId;
        this.entries = entries;
    }

    List<LedgerEntry> entries() {
        return entries;
    }
}
```

`LedgerEntry` is a record over primitives and a `String` — both effectively immutable, so any copy of a `LedgerEntry` is automatically deep with respect to its own fields. `Movement` holds a `List<LedgerEntry>` field, which is a reference to a separately allocated `ArrayList`. That one field is where the three copy strategies diverge.

| Copy kind | What is duplicated | Mutation through the original visible via the copy? | Mutation of a shared child visible both ways? |
|---|---|---|---|
| Reference copy (`Movement m2 = m1;`) | Nothing — one object, two variable names | Yes, always — there is only one object | Yes — there is only one child too |
| Shallow copy (`new Movement(m1.movementId, m1.entries())`, or `Object.clone()`) | The `Movement` shell only | No for the shell's own fields — `m2.movementId` is a distinct field slot with its own copied value | Yes — both shells' `entries` fields hold **the same** `List` reference, so `m1.entries().add(x)` is visible through `m2.entries()` too |
| Deep copy (`new Movement(m1.movementId, new ArrayList<>(m1.entries().stream().toList()))` with each `LedgerEntry` itself copied) | The `Movement` shell and a fresh `List` and fresh elements | No | No — the two `entries` lists are disjoint objects; mutating one never touches the other |

Because `LedgerEntry` is a record with only immutable components, copying the `List<LedgerEntry>` shallowly (`new ArrayList<>(other)`) already achieves the same externally-observable isolation as copying it deeply — the list is a fresh container, and its elements can never be mutated in place because records have no setters. This is exactly why 2.8.8 below calls that particular shallow copy "deep enough in this domain": the aliasing question only bites when a child is itself mutable. If `LedgerEntry` were a mutable class with a settable `reversed` flag, the shallow list copy would leave every element aliased, and flipping `reversed` on one `Movement`'s entry would flip it on the other's.

**Insight:** "shallow versus deep" is not a property of a copy operation in isolation — it is a property of a copy operation **relative to a specific field**. A single copy call can be deep with respect to one field (an `int`, a `String`, a record) and shallow with respect to another (a `List`, an array, a mutable nested object) in the same call. Always name the field when you claim depth.

## 2. `Object.clone`, source and mechanics (2.8.2, 2.8.3)

### The declaration, quoted

`javap -p java.lang.Object` on Oracle JDK 21.0.7 (macOS aarch64):

```
protected native java.lang.Object clone() throws java.lang.CloneNotSupportedException;
```

`protected` — a class outside `Object`'s package cannot call `clone()` on an arbitrary object, only on one it already has visibility into (and, to call `super.clone()`, only from inside a subclass). `native` — the field-by-field copy is done by the JVM, not by bytecode you can read; there is no Java-level loop over fields to inspect. `throws CloneNotSupportedException` — a **checked** exception, which every override must either declare or swallow, and it fires unless the receiver's class implements the `Cloneable` marker interface.

The javadoc's own wording, paraphrased at the clauses that matter: `clone()` "creates and returns a copy of this object", the copy's class is the same as the original's, and the general intent is that the fields of the new object are set "as if by assignment" — a bitwise field copy, not a call to any constructor, and specifically **no constructor of the object being cloned is called**. `Cloneable` itself declares no methods; it exists purely so `Object.clone()` can test `this instanceof Cloneable` internally and throw `CloneNotSupportedException` when it is absent — a marker interface used as an out-of-band flag, the same pattern as `Serializable`.

### The mechanism

```java
public class Object {
    protected native Object clone() throws CloneNotSupportedException;
}
```

There is no more source to read — this is where "internals" for `clone()` stops being a source walk and becomes a contract to test against, because the operation itself is opaque native code. What is verifiable is the *behaviour* the contract promises: allocate a new instance of the exact runtime class of `this` (not the declared type — this is why `clone()` naturally has a covariant return once overridden), without invoking any constructor, then copy every field's bits into the corresponding slot of the new instance.

### Proof the contract is broken, four ways

**(a) A constructor invariant is not re-checked.** `StakeSplit` must always have `bonusPortion + cashPortion == stake`. A hand-rolled `Cloneable` version:

```java
final class StakeSplit implements Cloneable {
    private Money bonusPortion;
    private Money cashPortion;

    StakeSplit(Money bonusPortion, Money cashPortion) {
        if (bonusPortion.amount().add(cashPortion.amount())
                .compareTo(bonusPortion.amount().add(cashPortion.amount())) != 0) {
            // the real check compares against the stake; elided here for brevity
        }
        this.bonusPortion = bonusPortion;
        this.cashPortion = cashPortion;
    }

    void adjustCashPortion(Money newCashPortion) {
        this.cashPortion = newCashPortion; // no re-validation against bonusPortion
    }

    @Override
    public StakeSplit clone() {
        try {
            return (StakeSplit) super.clone();
        } catch (CloneNotSupportedException e) {
            throw new AssertionError(e); // Cloneable is implemented, so this cannot fire
        }
    }
}
```

`adjustCashPortion` is a bug on its own — but the point stands even with a perfectly disciplined class: `clone()` runs no constructor, so if any code path (a setter, a deserializer, reflection) ever produces an object whose invariant is already violated, cloning it faithfully reproduces the violation. A constructor is the one place invariant checking is guaranteed to run; `clone()` bypasses that place by contract, not by accident.

**(b) Shallow-ness aliases a mutable child.** `Movement.clone()` implemented as `super.clone()` alone hands back a shell whose `entries` field points at the **same** `ArrayList` as the original. `clone.entries().add(rogueEntry)` mutates `original.entries()` too — the double-entry ledger's invariant (each `Movement` sums to zero across its own entries) can be violated from a completely different `Movement` reference.

**(c) A `final` field cannot be reassigned inside `clone()`.** Suppose `Movement.movementId` should be a fresh identity on every clone — a genuinely new ledger record. `movementId` is `final`, assigned once in the constructor; `clone()` runs no constructor, so the cloned object is stuck with the source object's id unless you resort to reflection (`Field.setAccessible(true)`) to punch through `final`, which defeats the entire purpose of declaring it final in the first place. Any class with a `final` field that should differ per-copy — a fresh `UUID`, a fresh timestamp — cannot express that difference through `clone()` at all.

**(d) A superclass that omits `Cloneable` poisons every subclass.** If `LedgerEntry`'s hierarchy had a base class that did not implement `Cloneable`, then `super.clone()` from any subclass throws `CloneNotSupportedException` unconditionally, because the check `this instanceof Cloneable` is done once, natively, against the actual runtime object — and it will be `true` (the concrete subclass implements it) — so this specific case actually *does* work up the chain as long as the concrete class implements `Cloneable`, regardless of its ancestors. The real poisoning case is the reverse: if an ancestor implements `Cloneable` but a class in between deliberately overrides `clone()` to throw (to opt back out), every further subclass inherits that throw and there is no way to opt back in without overriding `clone()` again at each level — the flag is not composable, only invertible, and once a class in the hierarchy decides "not cloneable" there is no `super.clone()` route around it. Either way, `clone()`'s cloneability is a property that leaks through the whole hierarchy rather than being decided once at the concrete class, which is exactly backwards for how inheritance is supposed to compose capabilities.

**Pitfall:** believing `implements Cloneable` plus overriding `clone()` gives you a normal, safe copy operation because "the JDK does it that way too" (`ArrayList`, `HashMap`, `Date` all do). Those classes' `clone()` methods are shallow in ways their own javadoc has to call out defensively, they were written before the copy-constructor convention was established, and *Effective Java*, "Override clone judiciously" — the canonical treatment — recommends copy constructors and static factories over `Cloneable` for new code precisely because of (a)–(d) above. The fix: never implement `Cloneable` on a new type; use a copy constructor.

## 3. The replacements, shipped (2.8.4, 2.8.5)

### If you are forced into `clone()` anyway

Some frameworks or legacy interfaces still demand `Cloneable`. Done correctly it needs a covariant return, a call to `super.clone()` for the shell, and a deep copy of every mutable field:

```java
final class LimitSet implements Cloneable {
    private final Money dailyDeposit;
    private final Money maxStake;
    private final Money monthlyLoss;
    private final List<String> overrideNotes; // mutable child that must not alias

    LimitSet(Money dailyDeposit, Money maxStake, Money monthlyLoss, List<String> overrideNotes) {
        this.dailyDeposit = dailyDeposit;
        this.maxStake = maxStake;
        this.monthlyLoss = monthlyLoss;
        this.overrideNotes = new ArrayList<>(overrideNotes);
    }

    @Override
    public LimitSet clone() {
        try {
            LimitSet shell = (LimitSet) super.clone();
            // super.clone() gave `shell.overrideNotes` the SAME list reference as `this`.
            // Field reassignment inside clone() is legal for non-final fields —
            // this is the one thing clone() can still do that a constructor call cannot skip.
            Field field = LimitSet.class.getDeclaredField("overrideNotes");
            field.setAccessible(true);
            field.set(shell, new ArrayList<>(this.overrideNotes));
            return shell;
        } catch (CloneNotSupportedException e) {
            // Cloneable is implemented on this exact class, so the native check
            // inside Object.clone() always passes; this branch is unreachable but
            // must be handled because the checked exception is declared on clone().
            throw new AssertionError("Cloneable implemented but clone() still threw", e);
        } catch (ReflectiveOperationException e) {
            throw new AssertionError(e);
        }
    }
}
```

Note the reflection is only needed here because `overrideNotes` is declared `final`; if it were a plain mutable field, `shell.overrideNotes = new ArrayList<>(this.overrideNotes);` inside `clone()` would suffice — reassignment of a *non-final* field is exactly what `clone()` permits and a constructor-free path forces you into. This is deliberately the worst-looking code in this file: it demonstrates that a "correct" `clone()` on a class with any `final` mutable-child field requires reflection to fully deep-copy, which is the strongest argument against ever choosing this route.

### The copy constructor and static copy factory

```java
final class LimitSetV2 {
    private final Money dailyDeposit;
    private final Money maxStake;
    private final Money monthlyLoss;
    private final List<String> overrideNotes;

    LimitSetV2(Money dailyDeposit, Money maxStake, Money monthlyLoss, List<String> overrideNotes) {
        this.dailyDeposit = dailyDeposit;
        this.maxStake = maxStake;
        this.monthlyLoss = monthlyLoss;
        this.overrideNotes = List.copyOf(overrideNotes); // deep enough: List<String>, String is immutable
    }

    // Copy constructor
    LimitSetV2(LimitSetV2 source) {
        this(source.dailyDeposit, source.maxStake, source.monthlyLoss, source.overrideNotes);
    }

    // Static copy factory
    static LimitSetV2 copyOf(LimitSetV2 source) {
        return new LimitSetV2(source);
    }

    // Copy factory with one field changed — the common real-world shape
    static LimitSetV2 withMaxStake(LimitSetV2 source, Money newMaxStake) {
        return new LimitSetV2(source.dailyDeposit, newMaxStake, source.monthlyLoss, source.overrideNotes);
    }
}
```

Every constructor call runs the ordinary constructor body — there is no separate "cloning path" to keep in sync, so an invariant check added to the primary constructor automatically protects every copy too. `final` fields are simply constructor parameters, so there is no reflection anywhere. The copy can freely return a different implementation of an interface, or wrap the data in a stricter subtype, because a static factory's return type only has to be assignment-compatible, not identical to the runtime class of the source — `clone()` cannot do this by contract (it must return the same runtime class as the source).

### The conversion constructor

A conversion constructor takes a *different* type and produces this one — the same mechanism, aimed at translation rather than duplication:

```java
final class Movement {
    private final String movementId;
    private final List<LedgerEntry> entries;

    // Conversion constructor: builds a Movement from a Reservation
    Movement(Reservation reservation) {
        this.movementId = "MOV-" + reservation.reservationId();
        this.entries = List.of(
            new LedgerEntry("CLIENT_CASH_RESERVED", reservation.amountMinor(), false),
            new LedgerEntry("SUSPENSE", -reservation.amountMinor(), false)
        );
    }

    List<LedgerEntry> entries() {
        return entries;
    }
}

record Reservation(String reservationId, long amountMinor) { }
```

Advantages of the constructor/factory family over `Cloneable`, stated plainly: works unchanged with `final` fields; runs every invariant check the primary constructor runs; can return a different implementation class or even an interface type; is never tied to matching the source's exact runtime class; and — since it is an ordinary static method — can be declared on an interface (`Cloneable` cannot contribute a usable `clone()` to an interface because `Object.clone()` is `protected`).

## 4. Deep-copy strategies compared (2.8.6)

Four ways to produce a disjoint copy of a `Movement` and its four `LedgerEntry` children.

| Strategy | Handles cycles? | Runs constructors/validation? | Maintenance as fields are added | Relative cost |
|---|---|---|---|---|
| Hand-written `copy()` per type | Yes, if written to (must track visited objects) | Yes — every field copy goes through a constructor | High — every new field must be added to `copy()` by hand, and a forgotten field silently stays shallow | Lowest — a few field assignments, comparable to normal object construction |
| Java serialization round-trip (`ObjectOutputStream`/`ObjectInputStream` to a byte buffer, then back) | Yes, automatically — the stream tracks object identity | **No** — `readObject`'s default path reconstructs fields directly, bypassing every constructor (`[X-REF]` [`../serialization/02-serialization.md`](../serialization/02-serialization.md)) | Low — new fields are picked up automatically if `Serializable` | Orders of magnitude higher — full graph reflection, stream framing, and allocation per object, easily 100 to 1000 times a field assignment |
| Jackson round-trip (serialize to JSON, deserialize into a new instance) | No, by default — a cycle produces infinite recursion or a `StackOverflowError` unless annotated | Partially — deserialization typically goes through a constructor or setters, so validation in a canonical constructor does run | Low — reflection-based, new fields picked up automatically | High — reflection plus text encoding, cheaper than Java serialization's native protocol but still far above field assignment |
| Records all the way down (every type in the graph is a record or otherwise unconditionally immutable) | Trivially yes — there is nothing to copy; sharing a reference to an immutable object is indistinguishable from copying it | N/A — nothing to copy means nothing to validate on copy | Lowest — adding a field to a record changes nothing about copying | Zero marginal cost — "copying" is just handing out the existing reference |

The serialization round-trip carries two disqualifiers beyond speed. First, deserializing untrusted bytes with Java's native serialization is a documented remote-code-execution surface: a crafted stream can drive arbitrary `readObject` methods and gadget chains during reconstruction before your code ever sees the result (`[X-REF 13]`, [`../web-security/`](../web-security/) covers the exploitation shape and mitigations). Second, `readObject`'s default field-restoring path does not call your canonical constructor, so any validation you wrote there — including `StakeSplit`'s bonus-plus-cash-equals-stake invariant — is silently skipped on the deserialized copy unless you also implement a custom `readObject` that re-validates, which is exactly the discipline a copy constructor already gives you for free.

Anchor the cost in the domain. Ledger writes run at 230/sec sustained and 13,600/sec peak; a `Movement` with four `LedgerEntry` children is the unit being written. A hand-written `copy()` — a handful of field reads and constructor calls — costs on the order of a few hundred nanoseconds to a few microseconds, reasoning purely from orders of magnitude and not from a benchmark run for this note: at 13,600 copies/sec that is at most tens of milliseconds of aggregate CPU per second, negligible against a multi-core service. A serialization round-trip at a few hundred microseconds to low milliseconds per copy, at the same peak rate, is potentially **seconds of CPU per second of wall time** — a multiple of the machine's own throughput — which turns a supporting operation (defensive-copying a `Movement` before returning it from a repository, say) into the dominant cost of the write path. This is a statement about orders of magnitude, not a specific millisecond figure; the right way to settle it for a real deployment is a JMH benchmark on the actual `Movement` shape, not this paragraph.

**Unverified:** exact per-copy latency for any of the four strategies on this domain's object shapes — no benchmark was run for this note. Treated in `## Open questions`.

## Supporting facts

### Arrays: `clone`, `Arrays.copyOf`, `System.arraycopy` (2.8.7)

All three copy the array's own storage into a new array, and all three are shallow with respect to what the array holds references to. A one-dimensional array of primitives is the one case where "shallow" and "deep" coincide, because there is nothing beneath a primitive to alias — `int[] a = {1, 2}; int[] b = a.clone();` gives `b` genuinely independent storage. An array of references (`String[]`, `LedgerEntry[]`) or any multi-dimensional array is shallow in the ordinary aliasing sense: `int[][] grid` is really an array of references to `int[]` rows, so `grid.clone()` copies the outer array of row-references but every row object is shared — `grid.clone()[0][0] = 99;` also changes `grid[0][0]`. `Arrays.copyOf(array, newLength)` and `System.arraycopy(src, 0, dest, 0, length)` copy at exactly the same depth as `clone()` — one level, references included as-is.

**Pitfall:** treating `array.clone()` as proof of independence because "arrays support clone and clone means deep copy." Verified: `int[] a = {1, 2}; a.equals(a.clone())` is `false` (arrays never override `equals`, so this is identity comparison and `a != a.clone()`), while `Arrays.equals(a, a.clone())` is `true` (element-wise comparison of two distinct but equal-content arrays). The fix for a reference-typed array is the same as for any other composite: copy each element explicitly if the elements are mutable.

### Collections: `new ArrayList<>(other)` and `List.copyOf` (2.8.8)

`new ArrayList<>(other)` allocates a new backing array and copies every reference from `other` into it — a new list, same elements, so structural changes (add/remove) to one list never affect the other, but mutating a shared mutable element is visible through both. `List.copyOf(other)` does the same reference copy and additionally returns an unmodifiable view — but "unmodifiable" describes the list's own structure only. An unmodifiable list of mutable elements is not an immutable list: `List.copyOf(entries).get(0)` still hands back the same mutable object `entries.get(0)` refers to, and mutating it through that reference is entirely legal and entirely invisible to any check on the list itself. `[X-REF 02]` — `List.copyOf`'s exact class and its interaction with `null` elements (it throws `NullPointerException`, unlike `ArrayList`) belongs in [`../collections/02-`](../collections/); the fact that matters here is only the depth of the copy.

The stranded-key bug, the JPA entity-equality problem, and Lombok's generated `equals`/`hashCode` all turn on the same underlying question — what identity should a composite object present to a collection or a comparison — but they are questions about *comparing*, not *copying*, and are covered in full in [composite equality and ordering](02a-composite-equality-and-ordering.md).

## Pitfalls

### `Cloneable` gives you a normal copy operation

**Wrong**

```java
final class StakeSplit implements Cloneable {
    private Money bonusPortion;
    private Money cashPortion;
    // constructor enforces bonusPortion + cashPortion == stake

    @Override
    public StakeSplit clone() {
        try {
            return (StakeSplit) super.clone();
        } catch (CloneNotSupportedException e) {
            throw new AssertionError(e);
        }
    }
}
```

The surprise: `super.clone()` never runs the constructor, so a `StakeSplit` that already violates its invariant (through a setter bug, deserialization, or reflection) clones the violation faithfully instead of catching it. There is no hook in `clone()` to re-run validation short of writing that validation a second time inside the override.

**Right**

```java
final class StakeSplitV2 {
    private final Money bonusPortion;
    private final Money cashPortion;

    StakeSplitV2(Money bonusPortion, Money cashPortion, Money stake) {
        if (bonusPortion.amount().add(cashPortion.amount()).compareTo(stake.amount()) != 0) {
            throw new IllegalStateException("bonus + cash must equal stake");
        }
        this.bonusPortion = bonusPortion;
        this.cashPortion = cashPortion;
    }

    static StakeSplitV2 copyOf(StakeSplitV2 source, Money stake) {
        return new StakeSplitV2(source.bonusPortion, source.cashPortion, stake);
    }
}
```

**Why people believe it:** `ArrayList`, `HashMap`, and `Date` all implement `Cloneable` and it "just works" for them, so the pattern looks endorsed by the standard library rather than tolerated as a historical artifact from before the copy-constructor convention existed.

### Assignment (`=`) is "good enough" as a copy

**Wrong**

```java
Movement original = new Movement("MOV-1", entries);
Movement snapshotForAudit = original; // "copied" for the audit trail

original.entries().add(new LedgerEntry("SUSPENSE", -500, false));
// snapshotForAudit.entries() now has the extra entry too — it was never a copy
```

The surprise: `snapshotForAudit` is not a second `Movement` at all — it is a second name for the exact same object. There was never a copy to begin with, so every field, including `entries`, is trivially "shared" because there is only one object. Any later mutation through `original` is immediately visible through `snapshotForAudit`, which defeats the entire purpose of taking an audit snapshot before a mutation.

**Right**

```java
Movement snapshotForAudit = new Movement(original.movementId(), new ArrayList<>(original.entries()));
```

**Why people believe it:** in spreadsheets, shell variables, and several scripting languages, `b = a` genuinely does produce an independent value for primitives and often for whole records; carrying that intuition into Java, where `=` on a reference type only ever copies the reference, is the single most common source of "but I copied it" bug reports.

### `grid.clone()` on a two-dimensional array is a deep copy of every cell

**Wrong**

```java
int[][] stakeMatrix = { {1, 2}, {3, 4} };
int[][] snapshot = stakeMatrix.clone();
snapshot[0][0] = 99; // believed to be isolated from stakeMatrix
```

The surprise: `stakeMatrix[0][0]` is also `99` afterward. `int[][]` is really an `Object[]` whose elements are references to `int[]` rows; `clone()` on the outer array copies only those row references one level deep. `snapshot` and `stakeMatrix` end up as two distinct outer arrays pointing at the *same* two row objects, so mutating a cell through either name mutates the shared row.

**Right**

```java
int[][] snapshot = java.util.Arrays.stream(stakeMatrix)
    .map(int[]::clone)
    .toArray(int[][]::new); // clone each row individually — now genuinely disjoint
```

**Why people believe it:** the one-dimensional case (`int[] a = {1, 2}; int[] b = a.clone();`) really is a full, independent copy, because there is nothing beneath a primitive element to alias; the belief generalizes correctly right up until the array's element type itself becomes a reference type, at which point "one level deep" stops being "the whole array."

## Cheat sheet

| Item | Value |
|---|---|
| Reference copy | One object, two names; every mutation visible both ways |
| Assignment (`=`) | Not a copy at all — a second name for the same object |
| Shallow copy | New shell, shared children; child mutation visible both ways, shell-level changes are not |
| Deep copy | New shell, disjoint children; nothing visible either way |
| `Object.clone()` | `protected native Object clone() throws CloneNotSupportedException` |
| `clone()` and constructors | Never calls one — fields set "as if by assignment" |
| `Cloneable` | Marker interface, no methods; flips the internal `instanceof` check inside `Object.clone()` |
| `clone()` breakage, 4 ways | Skips invariant checks; shallow by default; can't reassign `final` fields; ancestor can permanently disable it |
| Preferred replacement | Copy constructor / static copy factory — runs real constructor, works with `final`, can change type |
| Conversion constructor | Constructor/factory that takes a *different* type (`Movement(Reservation)`) |
| Copy constructor + invariant | Every copy runs the ordinary constructor body, so invariant checks can never be skipped |
| Deep-copy cost order | hand-written `copy()` < Jackson round-trip < Java serialization round-trip; records cost ~zero |
| Serialization round-trip risk | Skips `readObject`'s constructor validation; RCE surface on untrusted bytes |
| Array copies | `clone()`, `Arrays.copyOf`, `System.arraycopy` all shallow beyond one level |
| Verified array fact | `a.equals(a.clone())` false; `Arrays.equals(a, a.clone())` true |
| 2-D array `clone()` | Shallow one level down — outer array copied, row arrays still shared |
| `new ArrayList<>(other)` | Shallow — new list, same element references |
| `List.copyOf(other)` | Shallow + unmodifiable structure; elements can still be mutable |

## Self-test

**Q1.** A `Movement` holds a `List<LedgerEntry>` where `LedgerEntry` is a record. Is `new Movement(m.movementId(), new ArrayList<>(m.entries()))` a shallow copy or a deep copy, and does the distinction matter here?

<details><summary>Answer</summary>

Structurally it is a shallow copy: the new list holds references to the same `LedgerEntry` instances as the original, not freshly constructed ones. But because `LedgerEntry` is a record with only immutable components, there is no mutation path that could ever make that aliasing observable — a record has no setters, so "sharing a `LedgerEntry` reference" and "having an independent copy of a `LedgerEntry`" are externally indistinguishable. The distinction stops mattering the moment every reachable child is itself immutable; it starts mattering again the instant any child type gains a mutator.

</details>

**Q2.** Why can't `Object.clone()` reassign a `final` field to a new value during cloning?

<details><summary>Answer</summary>

`clone()` never runs a constructor — it is native code that copies the source object's fields bit for bit "as if by assignment" into a newly allocated instance of the same runtime class. A `final` field's single assignment already happened, permanently, when the original object's constructor ran; `clone()` has no constructor invocation of its own in which a different value could be supplied, and outside a constructor `final` fields cannot be reassigned by ordinary Java code at all. The only way around it is reflection (`Field.setAccessible(true)`), which is exactly the kind of workaround that signals `clone()` is the wrong tool.

</details>

**Q3.** `List.copyOf(entries)` is described as "shallow and immutable." Explain the apparent contradiction.

<details><summary>Answer</summary>

There is no contradiction once "immutable" is scoped correctly: `List.copyOf` guarantees the *list itself* cannot be structurally changed — no `add`, `remove`, `set`, or `sort` will succeed on the returned list. It says nothing about the objects the list holds references to. If those elements are mutable, `List.copyOf(entries).get(0).mutate()` still succeeds and is visible through every reference to that same element, including the original `entries` list — the copy is shallow with respect to the elements even though it is genuinely immutable with respect to its own structure. Only when every element is itself immutable (as `LedgerEntry` is here, being a record) does "structurally immutable" collapse into "fully immutable."

</details>

**Q4.** A stake of 3.33 must split into a bonus portion and a cash portion that sum exactly to 3.33. Why is this a `clone()`-relevant example rather than just a rounding example?

<details><summary>Answer</summary>

The rounding rule (bonus rounds down to the minor unit: 3.33 to 0.33 bonus + 3.00 cash, never 0.34 + 3.00 = 3.34) is enforced as an invariant inside `StakeSplit`'s constructor. `clone()`'s defining property is that it never calls a constructor, so if a `StakeSplit` were ever produced or mutated through any path that skipped that check — a setter, reflection, or a deserialization route with the same gap — cloning it would faithfully reproduce a `StakeSplit` where bonus plus cash no longer equals the stake, silently creating or destroying money on paper. The example is chosen specifically because it has a checkable numeric invariant, which makes "the invariant was skipped" a demonstrable failure rather than an abstract claim.

</details>

**Q5.** Rank the four deep-copy strategies (hand-written `copy()`, Java serialization round-trip, Jackson round-trip, records all the way down) from cheapest to most expensive, and explain why the serialization round-trip is a security concern beyond its cost.

<details><summary>Answer</summary>

Cheapest to most expensive: records all the way down (zero marginal cost — sharing a reference to an immutable object is indistinguishable from copying it), then hand-written `copy()` (a handful of field reads and constructor calls, comparable to ordinary object construction), then Jackson's JSON round-trip (reflection plus text encoding), then Java's native serialization round-trip (full graph reflection and stream framing, easily 100 to 1000 times a field assignment). Beyond cost, Java's native serialization is a documented remote-code-execution surface when deserializing untrusted bytes: a crafted stream can drive arbitrary `readObject` methods and gadget chains during reconstruction before the caller's own code ever inspects the result, and separately, `readObject`'s default path reconstructs fields directly without calling the canonical constructor, so any invariant validation written there is silently bypassed on the deserialized copy.

</details>

**Q6.** Why does `int[][] snapshot = matrix.clone();` fail to give an independent copy, even though `int[] a = {1, 2}; int[] b = a.clone();` does?

<details><summary>Answer</summary>

`int[]` holds primitive `int` values directly, so there is nothing beneath an element to alias — cloning the array copies the only data that exists, giving a genuinely independent copy. `int[][]` is a different shape: it is really an array of *references* to `int[]` row objects. `matrix.clone()` copies only the outer array — one level deep — duplicating the row references themselves but not the row objects they point at. `snapshot` and `matrix` therefore end up as two distinct outer arrays that both point at the identical row objects, so `snapshot[0][0] = 99` mutates the row that `matrix[0]` also refers to. A genuinely independent 2-D copy requires cloning each row individually.

</details>

## Open questions

- Exact per-copy latency (hand-written `copy()` versus Java serialization round-trip versus Jackson round-trip) for a `Movement` with four `LedgerEntry` children on this domain's actual object shapes. No benchmark was run for this note; the ordering and orders-of-magnitude claims in section 4 follow from the well-known relative costs of field assignment versus reflection-based (de)serialization, not from a measurement taken here. Settled by a JMH benchmark (`@Benchmark` methods for each strategy, `Blackhole` consumption, `-prof gc` to also capture allocation) run on the real classes.
- Whether a superclass that overrides `clone()` to throw `CloneNotSupportedException` unconditionally can be worked around from a subclass other than by overriding `clone()` again at that subclass. Stated in section 2(d) as "no route around it without re-overriding," which follows from `clone()` being an ordinary overridable method rather than a sealed contract point, but no test against a real multi-level `Cloneable` hierarchy was run for this note. Settled by constructing the three-level hierarchy and calling `super.clone()` from the bottom.

---

**Leaves covered:** 2.8.1, 2.8.2, 2.8.3, 2.8.4, 2.8.5, 2.8.6, 2.8.7, 2.8.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 432
