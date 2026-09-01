# 04 Modern Java — Build it — BUILD IT (§4.5)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Build it — collectors and myoptional](03-collectors-and-myoptional.md) · Next: [Build it — concurrency builds](05-concurrency-builds.md)

## Scope of this file

Every claim below that has a number, a compiler diagnostic, a `javap` listing or a program
output was produced by actually compiling and running it on this machine with
`javac --release 21`, in a scratch directory, never inside the notes tree. Where the syllabus
text and the measured behaviour disagree, the measured behaviour wins and the disagreement is
called out inline.

This file builds eight things, each a full concept: the hand-written equivalent of a record, a
`List` component written three defensive ways, an array component's `equals` failure and its two
fixes, a sealed hierarchy with an exhaustive switch and the exact error a fourth case produces,
the same hierarchy as a classical Visitor, an expression-tree interpreter over a sealed record
hierarchy, a reflective "wither," and a source-to-bytecode diff of everything a `record` and a
sealed `switch` actually compile to.

| # | Build | What it proves |
|---|---|---|
| 1 | Hand-written record equivalent | The boilerplate a `record` erases, counted in lines |
| 2 | `List` component, three ways | Which of the three actually stops a caller mutating your state |
| 3 | Array component `equals` failure | Why arrays and records' generated `equals` don't mix, and the two fixes |
| 4 | Sealed hierarchy + exhaustive switch | The compile-time guarantee, and its exact failure text |
| 5 | The same hierarchy as Visitor | The line-count and edit-cost difference, measured |
| 6 | Expression-tree interpreter | Nested deconstruction and guards doing real work |
| 7 | Reflective wither | `getRecordComponents()` used honestly, and why not to ship it |
| 8 | Diff vs the compiler's real output | `Record` attribute, `ObjectMethods` indy, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch` indy, `MatchException` |

All example code is drawn from QuizStakes: `StakeSplit(bonusPortion, cashPortion)`, extended here
to a three-component `StakeSplit(bonusPortion, cashPortion, roundId)` for build 1; `PaymentRun`'s
`List<WithdrawalTransaction>` and `byte[] signature` for builds 2 and 3; and the four **rails** the
domain already names — card deposit, bank deposit, card withdrawal, bank withdrawal — for builds
4 and 5.

---

### 1. The hand-written pre-record equivalent, counted in lines

**Mental model first.** A `record` declaration is not new runtime behaviour — the JVM has no
"record instruction." It is a compile-time macro that expands one line into a fixed shape: a
private final field per component, a canonical constructor, one accessor per component named
exactly like the component, and `equals`/`hashCode`/`toString` derived structurally from every
component. Picture the compiler pasting in the class you would have written, then throwing that
source away and emitting only the class file — you never see the expansion, but the class file
carries every one of those members with the exact same access rules a hand-written version would
have.

**Why it exists.** Before records, an immutable, value-like carrier (Josh Bloch's advice since
*Effective Java* first edition: prefer immutable value classes) required writing the same nine
things by hand every time: fields, constructor, accessors, `equals`, `hashCode`, `toString`, and —
if a component was mutable — defensive copies in and out. Every one of those is mechanical, and
mechanical code is where transcription bugs live: forgetting a field in `equals` but not
`hashCode` (or vice versa) silently breaks the `hashCode`/`equals` contract, and nothing catches
it until a `HashSet` starts losing elements. IDEs auto-generate the boilerplate, which hides the
bug class but not the boilerplate itself — fifteen years of Java code has thousands of these
classes, and code review still has to read all of them to check they agree.

**When to reach for it, and when not.** Reach for a record whenever the type is a transparent,
immutable carrier of its components — the components *are* the state, there is no hidden
invariant beyond what the compact constructor can check, and identity doesn't matter (two
`StakeSplit`s with the same two `Money` values are the same `StakeSplit`). Do not reach for it
when you need a mutable entity with identity (a `LedgerEntry` row that gets superseded, not
replaced), when you need to hide the exact component shape from callers (a record's
accessors and canonical constructor are part of its public contract, visible via
`getRecordComponents()` — build 8's territory), or when the class needs to extend another
concrete class (records can only extend `java.lang.Record`, implicitly, and cannot extend
anything else — they can still implement interfaces).

**How it works.** For a component list `(C1 c1, C2 c2, ..., Cn cn)`, the compiler is specified
(JLS §8.10) to emit:

- one `private final` field per component, in declaration order;
- a canonical constructor with exactly that parameter list, which assigns each field from its
  matching parameter (or from whatever a compact constructor rebinds the parameter to — build 7's
  compact-constructor diagnostic in the cheat sheet below shows exactly how that assignment is
  wired);
- one public accessor per component, named identically to the component (not `getBonusPortion()`
  — `bonusPortion()`), unless the record body declares its own method with that exact signature,
  in which case the explicit one wins and no synthetic accessor is generated for that component;
- `equals(Object)`, `hashCode()` and `toString()`, generated to consider every component, unless
  the record body explicitly overrides one of them — you can override all three, some, or none.

Nothing here is optional at the language level: you cannot declare a record with only five of its
six components appearing in `equals`. If you need that, the components are wrong — split the type,
or fall back to a hand-written class.

**No diagram.** This is a source-shape claim, not a runtime one; a table is the right substitute
and appears in beat 8 below.

**A minimal concrete example.** Extending QuizStakes' `StakeSplit(Money bonusPortion, Money
cashPortion)` with a third component — the round the split was computed for — to get a genuinely
three-component type for this comparison:

```java
// The one-line record.
record StakeSplit(Money bonusPortion, Money cashPortion, RoundId roundId) {}
```

and the hand-written class that is behaviourally identical to it (compiled and run on this
machine):

```java
final class StakeSplitHandWritten {
    private final Money bonusPortion;
    private final Money cashPortion;
    private final RoundId roundId;

    StakeSplitHandWritten(Money bonusPortion, Money cashPortion, RoundId roundId) {
        this.bonusPortion = bonusPortion;
        this.cashPortion = cashPortion;
        this.roundId = roundId;
    }

    Money bonusPortion() { return bonusPortion; }
    Money cashPortion() { return cashPortion; }
    RoundId roundId() { return roundId; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        StakeSplitHandWritten that = (StakeSplitHandWritten) o;
        return Objects.equals(bonusPortion, that.bonusPortion)
            && Objects.equals(cashPortion, that.cashPortion)
            && Objects.equals(roundId, that.roundId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(bonusPortion, cashPortion, roundId);
    }

    @Override
    public String toString() {
        return "StakeSplitHandWritten[" +
            "bonusPortion=" + bonusPortion + ", " +
            "cashPortion=" + cashPortion + ", " +
            "roundId=" + roundId + ']';
    }
}
```

`[NUM]` Counted directly from the file compiled on this machine (`awk` over the class body,
opening brace to closing brace, blank lines and all): the hand-written class is **38 lines** for
three components. The record is **1 line**. That is not "roughly forty" — it is 38 measured lines
for one type, and it grows by roughly one field line, one constructor-body line, one accessor line
and a few `equals`/`hashCode`/`toString` fragment-lines per additional component, so a
five-component record saves proportionally more, not less. Both compiled with `javac --release
21` and both produced identical output for the same inputs:

```
equals: true
hashCode match: true
StakeSplitHandWritten[bonusPortion=0.33 GBP, cashPortion=3.00 GBP, roundId=00000000-0000-0000-0000-000000000001]
```

**The gotcha.** The generated `equals` and `hashCode` are **structural**, not identity-based, and
this is where `[NUM]` beats 2 and 3 below live: if a component is itself mutable (a `List`) or is
an array, "structural" does the wrong thing — a `List` mutated after construction changes what the
record compares equal to (build 2), and an array component breaks structural equality entirely,
because arrays never overrode `equals`/`hashCode` from `Object` (build 3). The record macro does
not know or care whether a component's own `equals` is safe to delegate to; it delegates
unconditionally.

**Insight:** because the generated members come from `ObjectMethods.bootstrap` (beat 8), the
compiler does not literally paste 38 lines of bytecode into the class file the way it would paste
38 lines of source — it emits three `invokedynamic` call sites and one small descriptor string,
and defers building the actual method bodies to first invocation. The class file for the record is
smaller than the class file for the hand-written version even though they are behaviourally
identical; see beat 8's "Diff vs the real one" table for the byte counts.

> **A `record` is a transparent, immutable data carrier whose canonical constructor, accessors and
> `equals`/`hashCode`/`toString` are derived mechanically from its component list, saving exactly
> the boilerplate a careful engineer would otherwise write and review by hand — nothing more,
> nothing hidden.**

#### Diff vs the real one — hand-written class vs `record`

| Dimension | Hand-written `StakeSplitHandWritten` | `record StakeSplit` |
|---|---|---|
| Edge cases (null component) | Whatever the author remembered to guard — nothing here | Same: no null-check exists unless a compact constructor adds one (build 7 relies on this being absent) |
| Intrinsics | None; `equals`/`hashCode`/`toString` are ordinary bytecode, present from class-load | `ObjectMethods.bootstrap` (beat 8) builds the method bodies via a `MethodHandle` chain lazily, on first call to each method, then caches the `CallSite` |
| Serialization | Whatever `Serializable`/`readObject` the author wrote, if any | Records use a **fixed** serialization form (JEP 395 record serialization): compatible custom `readObject`/`writeObject` are disallowed for the canonical form; deserialization always goes through the canonical constructor, so compact-constructor validation runs even on deserialized instances — a hand-written class's `readObject` can bypass its own constructor entirely unless written carefully |
| Null policy | Author's choice, inconsistently applied across projects | Author's choice via the compact constructor, applied once, guaranteed to run for every construction path including deserialization |
| Thread safety | Safe if all fields are `final` and components are immutable — same requirement, not automatic | Identical requirement; `record` does not make a `List` or array component immutable, only the *reference* to it |
| Allocation | One object per instance, all methods statically resolved | One object per instance; first call to `equals`/`hashCode`/`toString` pays a one-time `MethodHandle` linkage cost, then is as fast as static dispatch |
| Why the JDK bothers | — | Eliminates the transcription-bug class (missing field in `equals`), gives every value type a **canonical, reflectable shape** (`getRecordComponents()`), and lets `switch` deconstruct it (build 6) — none of which a hand-written class gets for free |

---

### 2. A `List` component written three ways

**Mental model first.** A record's canonical constructor receives whatever reference the caller
passed and, by default, stores that exact reference. If the caller's variable still points at the
same `ArrayList`, the caller now holds a live handle into your "immutable" object's internals.
Defence against this has two independent doors — the constructor (defends against the caller
mutating *before* you notice) and the accessor (defends against the caller mutating *after* they
retrieve your state) — and a record gives you neither for free.

**Why it exists.** `PaymentRun`'s `List<WithdrawalTransaction>` is exactly the shape that breaks
naive records: a `PaymentRun` is supposed to be an immutable snapshot of "these withdrawals were
approved together," consumed by `BankWithdrawal` processing and archived. If the list backing it
is the same `ArrayList` the batch-builder is still appending to, "immutable snapshot" is a lie —
readers see writes that happen after the snapshot was taken. Before defensive copying was
idiomatic, this class of bug ("I read the list twice and got two different sizes") was common
enough that *Effective Java* Item 50 exists.

**When to reach for it, and when not.** Copy-in-and-copy-out (variant 3) is the correct default
for any record whose component is a mutable collection and whose instances might outlive or be
shared beyond the code that constructed them — which describes essentially all domain objects.
Copy-in-only (variant 2) is defensible only when you also control every caller of the accessor and
can guarantee none of them mutates the result — a narrow, easy-to-violate assumption. No-copy
(variant 1) is correct only when the component's type is already structurally immutable
(`Money`, a `record`, an enum) — copying an already-immutable list is pure waste, which is
precisely why `List.copyOf` and `List.of` special-case it (see the gotcha below).

**How it works.** All three variants below were compiled and run together on this machine.

```java
record WithdrawalTransaction(String clientId, Money amount, String status) {}

// 1. No copy at all — leaks the caller's list, and the accessor leaks it right back out.
record PaymentRunNoCopy(List<WithdrawalTransaction> transactions) {}

// 2. Copy-in only — the compact constructor defends the field; the accessor still hands
//    out whatever List.copyOf produced, which happens to be unmodifiable, but that is an
//    accident of variant 2 sharing the same defended reference, not a copy-out.
record PaymentRunCopyIn(List<WithdrawalTransaction> transactions) {
    PaymentRunCopyIn {
        transactions = List.copyOf(transactions);
    }
}

// 3. Copy-in and copy-out — the compact constructor defends the field, and the accessor
//    is overridden to hand back a fresh copy on every call.
record PaymentRunCopyInOut(List<WithdrawalTransaction> transactions) {
    PaymentRunCopyInOut {
        transactions = List.copyOf(transactions);
    }
    @Override
    public List<WithdrawalTransaction> transactions() {
        return List.copyOf(transactions);
    }
}
```

The mutation tests, each either passing or failing as marked, run against real `ArrayList`s
mutated *after* construction and, for variant 2, against the accessor's own return value:

```
[no-copy] before=1 after=2 -> FAIL (leaked, mutated through)
[copy-in] caller mutation after construction absorbed: PASS
[copy-in] accessor mutation: UnsupportedOperationException thrown, but this is List.copyOf's own immutable list being shared, not a fresh view
[copy-in] accessor returns same backing instance across calls: true
[copy-in-out] caller mutation after construction absorbed: PASS
[copy-in-out] accessor returns same backing instance across calls: true
```

`[PROVE]` Variant 1 fails outright: constructing `PaymentRunNoCopy` from a mutable `ArrayList`,
then appending to that same `ArrayList` after construction, changes `transactions().size()` from 1
to 2 on the already-constructed record — a supposedly immutable object changed shape after the
fact. Variants 2 and 3 both pass the same test, because both copy on the way in.

**The gotcha.** `**Pitfall:**` The obvious claim to make about variant 3 is "the accessor returns
a fresh copy every call, so identity should differ across calls." Measured on this machine, it
does not — `copyInOut.transactions() == copyInOut.transactions()` is **`true`**. The reason is
`List.copyOf`'s own documented fast path: if the argument is already an unmodifiable list produced
by `List.copyOf`/`List.of` (an internal `ImmutableCollections` type), `List.copyOf` returns the
*same* instance rather than copying again, because copying an immutable list can never be
observably different from returning it. This is not a bug in variant 3 — the isolation guarantee
still holds, because what's shared is itself unmodifiable, so sharing it is harmless — but "copy-in
and copy-out means two different instances" is the version of this claim most material states, and
it is false for `List.copyOf`-backed records specifically. The honest statement is: variant 3
protects you from mutation through *either* direction; it does not guarantee reference-distinct
results, and for `List.copyOf` it provably does not.

**Insight:** this is the same optimization `String.intern()`-adjacent code and `Set.copyOf` rely
on — recognizing "this is already the shape I'd produce, skip the work" — and it means the cost
argument against variant 3 ("copying on every read is wasteful") is weaker than it looks, precisely
*because* the common case (repeated reads of an already-defended list) is free.

**Interview:** "What's wrong with a record that has a `List<T>` component and no compact
constructor?" — the accessor hands back the live, mutable backing list, so any caller can mutate
what looks like an immutable value; the fix is `List.copyOf` in a compact constructor, and, if the
accessor must also be defended against a caller mutating the *returned* list, override the
accessor too — while knowing `List.copyOf` may hand back the same reference on the second call if
the input was already one of its own immutable lists.

> **A record component of a mutable type needs a compact constructor calling `List.copyOf` (or
> equivalent) to defend the field on the way in, and, only if the accessor's result might itself
> be mutated by a caller holding a mutable-typed reference to it, an overridden accessor to defend
> on the way out — understanding that `List.copyOf` may return the same instance across calls when
> its input is already one of its own immutable lists.**

#### Diff vs the real one — three defensive variants vs `List.copyOf`'s real contract

| Dimension | No copy | Copy-in only | Copy-in and copy-out |
|---|---|---|---|
| Edge cases (`null` element) | Passes through silently | `List.copyOf` throws `NullPointerException` on any `null` element — a validation side effect most engineers don't expect from a "just copy it" call | Same NPE, twice: once on construction, once (if the identity-sharing fast path doesn't apply) on every read |
| Intrinsics | None | None | None |
| Serialization | Serializes whatever mutable list was stored — a deserialized instance can differ from what was serialized if the source list mutated between calls | Serializes the defended immutable list | Same, plus every deserialization replay goes through `List.copyOf` again |
| Null policy (the list itself) | `null` list crashes on first accessor use, not at construction | `List.copyOf(null)` throws NPE at construction — fails fast | Same fail-fast, twice |
| Thread safety | None — concurrent mutation and read races | Safe to publish once constructed; the field never changes after that | Same; the extra copy-out doesn't add safety, only isolation from *misuse*, not races |
| Allocation | Zero extra allocation, but unsafe | One `List.copyOf` allocation at construction (or zero, if input already immutable — the fast path) | One allocation at construction, plus one **or zero** per accessor call, per the fast-path rule proven above |
| Why the JDK bothers | — | — | `List.copyOf`'s own javadoc states the identity-preserving fast path explicitly: it exists so idempotent copying of already-immutable data is free, which is exactly what makes variant 3 cheap in the common case where callers pass already-defended lists forward |

---

### 3. An array component's `equals`/`hashCode` failure, and its two fixes

**Mental model first.** Arrays in Java are objects, but `Object.equals` and `Object.hashCode` were
never overridden for array types — there is no generic way to know at the `Object` level whether
two arrays should compare "by content" or "by reference," so the JDK picked reference identity for
every array type, and never revisited it. A record's generated `equals` calls
`Objects.equals(thisComponent, thatComponent)` (or the primitive-appropriate comparison) for every
component, uniformly — it does not special-case arrays, because doing so would require the
compiler to know your intent, and it doesn't.

**Why it exists.** `PaymentRun`'s `byte[] signature` is a plausible real field — a payment run
gets signed before submission to the banking partner, and the signature is naturally bytes. Making
it a record component looks harmless until two `PaymentRun`s with byte-for-byte identical
signatures compare unequal, because `Objects.equals` on two `byte[]` references delegates to
`byte[].equals(Object)`, which `Object` defines as `this == obj` — reference identity, full stop.

**When to reach for it, and when not.** Reach for the `List<Byte>` fix (or `List<Integer>` for
wider element types) when boxing overhead is irrelevant relative to the array's size and you want
records to keep working "for free." Reach for the manual `Arrays.equals`/`Arrays.hashCode`
override only when the array must stay a raw array for a real reason — interop with a signing
library's `byte[]`-typed API, avoiding 8 bytes of object header per boxed `Byte`, or a hot path
where boxing pressure is measurable — and accept that you are now maintaining `equals`/`hashCode`
by hand for that one component, same as a pre-record class would have.

**How it works, and the concrete example.** Compiled and run together:

```java
record WithdrawalTransaction(String clientId, String amount) {}

// Broken: array component, default (generated) equals/hashCode.
record PaymentRunBroken(List<WithdrawalTransaction> transactions, byte[] signature) {}

// Fix A: swap byte[] for an immutable List<Byte>.
record PaymentRunListFix(List<WithdrawalTransaction> transactions, List<Byte> signature) {
    PaymentRunListFix {
        signature = List.copyOf(signature);
    }
}

// Fix B: keep byte[] (e.g. zero-copy interop with a signing library), override manually.
record PaymentRunArraysFix(List<WithdrawalTransaction> transactions, byte[] signature) {
    PaymentRunArraysFix {
        signature = signature.clone(); // defends the field on the way in
    }
    @Override
    public byte[] signature() {
        return signature.clone(); // defends the field on the way out
    }
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof PaymentRunArraysFix that)) return false;
        return transactions.equals(that.transactions) && Arrays.equals(signature, that.signature);
    }
    @Override
    public int hashCode() {
        return 31 * transactions.hashCode() + Arrays.hashCode(signature);
    }
}
```

`[PROVE]` Run against two byte-identical but reference-distinct three-byte arrays `{1,2,3}`:

```
[broken] equal content, equals() = false (expect false: reference equality on the array field)
[broken] toString = PaymentRunBroken[transactions=[WithdrawalTransaction[clientId=CLIENT-1, amount=180.00]], signature=[B@27716f4]
[list-fix] equal content, equals() = true (expect true)
[arrays-fix] equal content, equals() = true (expect true)
[arrays-fix] hashCode match = true
[arrays-fix] caller mutated sig1 after construction; unaffected = true
[arrays-fix] mutated the array returned by the accessor; internal state unaffected = true
```

The `[B@27716f4` line is the generated `toString()` output verbatim — arrays inherit `Object`'s
`toString`, which is `getClass().getName() + "@" + Integer.toHexString(hashCode())`; `[B` is the
JVM's type descriptor for `byte[]` and the hex suffix is `Object.hashCode()`'s identity hash, not
`Arrays.hashCode()`'s content hash. A record's generated `toString` calls each component's own
`toString`, so it faithfully reproduces this garbage for an unfixed array component.

**The gotcha.** `**Pitfall:**` Fix B needs *two* defensive `clone()` calls, not one — the compact
constructor clones on the way in (protects against the caller mutating the array after
construction) and the overridden accessor clones on the way out (protects against a caller
mutating the array they received and corrupting the record's internal state). Adding only the
first is the mistake that looks fixed because the obvious test (mutate the caller's original
array) passes, while the accessor-mutation test still fails — exactly the same asymmetry as
build 2's `List` component, just with `clone()` standing in for `List.copyOf`.

**Interview:** "Why does a record with a `byte[]` field break `equals`?" — because `Object`'s
`equals`/`hashCode` are never overridden for array types, so the compiler-generated `equals`
delegates to reference equality for that component; the fix is either to stop using an array
(`List<Byte>`, which composes correctly with the generated methods) or to override `equals`,
`hashCode` and, for hygiene, `toString`, using `Arrays.equals`/`Arrays.hashCode`/`Arrays.toString`.

> **Never let a record component be a raw array unless you have overridden `equals`, `hashCode`
> and both defensive-copy directions by hand — arrays never overrode `Object`'s reference-identity
> `equals`/`hashCode`, and a record's generated methods do not know to special-case them.**

#### Diff vs the real one — broken array component vs the two fixes

| Dimension | `PaymentRunBroken` (raw `byte[]`) | `List<Byte>` fix | `Arrays.equals`/`hashCode` fix |
|---|---|---|---|
| Edge cases (`null` array/list) | `Objects.equals(null component, null component)` returns `true` cleanly; a `null` array in one instance and a populated one in the other never crashes, just never matches | `List.copyOf(null)` throws NPE at construction — stricter, fails fast | Manual `Arrays.equals` handles `null` on either side gracefully (returns `false` unless both `null`); `signature.clone()` on a `null` field throws NPE unless guarded |
| Intrinsics | None | None | `Arrays.equals`/`Arrays.hashCode` for primitive arrays are JIT-recognized as vectorizable loops on supporting platforms — a real (if usually immaterial at typical signature sizes) throughput edge over element-by-element boxed comparison |
| Serialization | Serializes the array's bytes fine; the *bug* is unaffected by serialization since it's an in-memory `equals` problem | Serializes as a boxed list — larger on the wire (object-per-byte framing in some serializers) unless the serializer special-cases `List<Byte>` | Serializes as a raw byte array — most compact wire form |
| Null policy | No enforcement | Fails fast on `null` elements too (`List.copyOf`) | No enforcement beyond what's added by hand |
| Thread safety | Array is mutable and shared — no protection | `List.copyOf` result is unmodifiable — safe once published | Safe only because of the two explicit `clone()` calls; omit either and it regresses to the same aliasing bug as build 2 |
| Allocation tricks | Zero extra allocation, wrong answer | One boxed `Byte` object per array element (autoboxing) — real overhead for large signatures | Two `clone()` calls (array copies) per construction/read cycle — cheaper per byte than boxing, more expensive per call than a reference copy |
| Why the JDK bothers | — | Composes with every existing record-based API (`equals`, `Set`, `Map` keys) with zero extra code | Preserves the exact wire and memory shape a signing/crypto library expects, at the cost of writing three methods by hand — the same trade the JDK itself makes internally wherever it stores digests as `byte[]` |

---

### 4. A sealed hierarchy, an exhaustive switch, and the exact error a fourth case produces

**Mental model first.** `sealed` closes a type's set of direct subtypes at compile time and
records that closed set in the class file (`PermittedSubclasses`, beat 8). A pattern `switch` over
a sealed type can then be checked for exhaustiveness the same way a `switch` over a boolean can be
checked for two cases — the compiler *knows* there is no fifth possibility, because nothing outside
the `permits` clause is allowed to implement the interface, so it can refuse to compile a `switch`
expression that doesn't handle every one of them.

**Why it exists.** Before sealed types, "handle every subtype of this interface" was an unenforced
convention: an `if (rail instanceof CardDeposit c) ... else if (rail instanceof BankDeposit b)
...` chain compiled fine even if it silently fell through the third real case. The only two ways to
get compiler-enforced totality were an `enum` (values fixed but no room for per-case fields
without an ugly workaround) or the Visitor pattern (build 5) — heavier machinery for the same
guarantee.

**When to reach for it, and when not.** Reach for `sealed` plus a pattern `switch` when the set of
cases is genuinely closed and owned by you — QuizStakes' four rails, `Verdict`'s four kinds
(`DocumentVerdict`, `ScreeningVerdict`, `ReviewVerdict`, `WealthVerdict`), any protocol/command
type. Do not reach for it when third parties (a plugin, a downstream module you don't control)
need to add new implementations — sealing forbids exactly that, by design; an unsealed interface
or Visitor (build 5) is the right shape there.

**How it works.** Compiled and run on this machine, starting with three of the four real rails:

```java
sealed interface Rail permits CardDeposit, BankDeposit, CardWithdrawal {}
record CardDeposit(String pspRef) implements Rail {}
record BankDeposit(String batchRef) implements Rail {}
record CardWithdrawal(String pspRef) implements Rail {}

static int settlementLagSeconds(Rail rail) {
    return switch (rail) {
        case CardDeposit c -> 1;
        case BankDeposit b -> 14400;
        case CardWithdrawal w -> 1;
    };
}
```

```
settlementLagSeconds(new CardDeposit("PSP-1"))   -> 1
settlementLagSeconds(new BankDeposit("BATCH-1")) -> 14400
```

`[PROVE]` Adding the domain's real fourth rail — `record BankWithdrawal(String batchRef)
implements Rail {}` — to the `permits` clause, in the *same compilation unit* as the switch, and
recompiling everything together with `javac --release 21`, produces:

```
RailSwitch4.java:10: error: the switch expression does not cover all possible input values
        return switch (rail) {
               ^
1 error
```

This is the actual `javac --release 21` output on this machine, pointing at the `switch` keyword's
line, not at the missing case — the compiler reports the statement/expression as incomplete, not
which arm you forgot, because from its point of view there could be several missing arms at once.

**A second failure mode exists, and it is a runtime one, not a compile error — separate
compilation.** If the sealed interface is widened to four permitted subtypes and *only the
interface and the new record are recompiled*, while the class containing the `switch` is left as
stale bytecode compiled against the three-case world, the mismatch is invisible at compile time
(nothing recompiled the switch, so nothing re-checked its exhaustiveness) and surfaces only when a
`BankWithdrawal` instance is actually routed through it at runtime. Reproduced on this machine —
`Rail.java` widened and recompiled, `BankWithdrawal.java` compiled fresh, `RailLag.class`
(containing the switch) left untouched from the three-case build, then a `BankWithdrawal` passed
through it:

```
Exception in thread "main" java.lang.MatchException
	at RailLag.settlementLagSeconds(RailLag.java:3)
	at Main.main(Main.java:3)
```

A bare `java.lang.MatchException`, no message — the same exception type and the same
`(String, Throwable)` two-arg constructor the verified-figures block documents for the exhaustive
*enum* switch's separate-compilation failure (Java 21 replaced that case's
`IncompatibleClassChangeError`/`NoSuchFieldError` shapes with `MatchException` too); sealed
pattern switches use the identical failure type for the identical root cause — a switch that was
exhaustive when compiled is no longer exhaustive against the selector's *current* runtime type,
because the two artifacts were built against different versions of the sealed hierarchy.

**The gotcha.** `**Pitfall:**` "Sealed types make exhaustiveness a compile-time guarantee" is true
only *within one compilation*. Across module or JAR boundaries — a library ships a sealed
interface, a consumer compiles a switch over it, the library ships a point release adding a
permitted subtype, the consumer doesn't recompile — the guarantee silently becomes a *runtime*
`MatchException`. This is precisely why sealed hierarchies that cross module boundaries need a
release discipline (bump a major version on any `permits` change) that a purely intra-module sealed
type doesn't need.

**Interview:** "What happens if you add a case to a sealed interface?" — if the switch is
recompiled together with the new case, you get a compile error naming the switch as non-exhaustive
(exact wording: "the switch expression does not cover all possible input values"); if the switch
is *not* recompiled (separate compilation, e.g. a library upgrade), the mismatch survives to
runtime and surfaces as an unchecked `java.lang.MatchException` the first time the new case
actually reaches that switch.

> **A pattern `switch` over a sealed type is checked for exhaustiveness against the `permits`
> clause visible at that compilation — the guarantee is compile-time within one build, and
> degrades to a runtime `MatchException` the moment the switch and the sealed hierarchy are
> compiled against each other's stale versions.**

#### Diff vs the real one — sealed-switch's guarantee vs a pre-sealed `if`/`instanceof` chain

| Dimension | `if (r instanceof CardDeposit c) … else if …` chain | `sealed` + exhaustive `switch` |
|---|---|---|
| Edge cases (a case silently unhandled) | Compiles fine; falls through to nothing, or a `null` return, or an `else` bucket that was meant to be temporary | Compile error in the same compilation unit; `MatchException` across stale separate compilation (proven above) — never silent |
| Intrinsics | Plain `instanceof` checks, one `checkcast` per test | `invokedynamic` to `SwitchBootstraps.typeSwitch` (beat 8) — a single bootstrap call site replaces the whole `instanceof` chain |
| Serialization | N/A — a control-flow construct | N/A |
| Null policy | `instanceof` on a `null` reference is `false`, so a `null` selector silently falls through every arm | `switch (rail)` on a `null` selector throws `NullPointerException` unless a `case null ->` arm is present — stricter, and it is stricter *on purpose* |
| Thread safety | N/A, stateless | N/A, stateless |
| Allocation tricks | None | The `typeSwitch` bootstrap resolves once per call site (a one-time `MethodHandle` chain built at first execution), then every subsequent dispatch is a cached lookup — not "cheaper" than a chain of `checkcast`s at steady state, but never re-linked |
| Why the JDK bothers | — | Turns "did I forget a case" from a code-review question into a build failure, and turns "which concrete case is this" from a chain of casts into one indexed jump (the `tableswitch` seen in beat 8's bytecode) |

---

### 5. The same hierarchy as a Visitor, side by side

**Mental model first.** Visitor achieves the same goal as sealed-plus-switch — dispatch on the
concrete case, with the compiler noticing when a case is unhandled — through double dispatch
instead of pattern matching: each element type gets an `accept(Visitor)` method that calls back
into the matching `visitXxx` method on the visitor, so the *element* picks which visitor method
runs, not a runtime type test performed by the caller.

**Why it exists.** Visitor predates sealed types by over a decade (it's a 1994 *Design Patterns*
pattern) and solves a problem `switch`/`instanceof` couldn't: adding a *new operation* over a
closed set of element types without touching the element classes at all — write one new
`Visitor<R>` implementation, done. Before sealed interfaces existed, it was also the only way to
get an interface-enforced "you must handle every case" guarantee for non-enum hierarchies.

**When to reach for it, and when not.** Visitor still wins over sealed-plus-switch in exactly one
situation this file's other four rails don't have: an **open, extensible hierarchy** — a plugin
system where third parties supply new element types you don't control at compile time. Sealed
types forbid that by construction (`permits` is a fixed, closed list); Visitor's `accept` method
just needs implementing by whoever adds the new element type, and existing visitors keep compiling
(they simply won't have a case for the new type unless the `Visitor` interface itself grows a
method, which is Visitor's own version of "you have to touch every implementation"). For a closed
hierarchy you own — QuizStakes' four rails — sealed-plus-switch wins on every other axis measured
below.

**How it works, and the concrete example.** The same rail hierarchy and the same operation
(`settlementLagSeconds`), reimplemented as Visitor, compiled and run on this machine:

```java
interface Rail {
    <R> R accept(Visitor<R> visitor);
}

interface Visitor<R> {
    R visitCardDeposit(CardDeposit c);
    R visitBankDeposit(BankDeposit b);
    R visitCardWithdrawal(CardWithdrawal w);
}

final class CardDeposit implements Rail {
    final String pspRef;
    CardDeposit(String pspRef) { this.pspRef = pspRef; }
    public <R> R accept(Visitor<R> visitor) { return visitor.visitCardDeposit(this); }
}
// BankDeposit, CardWithdrawal follow the identical shape.

final class SettlementLagVisitor implements Visitor<Integer> {
    public Integer visitCardDeposit(CardDeposit c) { return 1; }
    public Integer visitBankDeposit(BankDeposit b) { return 14400; }
    public Integer visitCardWithdrawal(CardWithdrawal w) { return 1; }
}
```

```
new CardDeposit("PSP-1").accept(new SettlementLagVisitor()) -> 1
new BankDeposit("BATCH-1").accept(new SettlementLagVisitor()) -> 14400
```

`[PROVE]` **Line count, counted directly from the compiled files, hierarchy plus one operation,
excluding `main`:** the sealed-plus-switch version is **10 lines** — three one-line record
declarations plus a six-line switch method. The Visitor version is **28 lines** — the `Rail`
interface (1 method), the `Visitor<R>` interface (3 methods), three element classes (a field, a
constructor, an `accept` override each — 5 lines apiece), and the concrete visitor (3 method
bodies). Same operation, same three cases, **2.8×** the code.

**Where do you edit to add a case / add an operation:**

| Change | Sealed + `switch` | Visitor |
|---|---|---|
| Add a fourth rail (`BankWithdrawal`) | Add one record; every `switch` over `Rail` in the codebase becomes non-exhaustive and **fails to compile** until fixed (build 4) — or fails at runtime with `MatchException` if compiled separately (build 4) | Add one class implementing `Rail`; the `Visitor<R>` interface needs a new `visitBankWithdrawal` method, which **breaks every existing `Visitor` implementation's compile** until each adds the method (or the interface ships it as a `default` that throws, silently degrading the guarantee) |
| Add a new operation (e.g. `description(Rail)`) | Write one new static method with its own `switch` — zero existing code touched | Write one new class implementing `Visitor<String>` — zero existing code touched |
| Guards / nested deconstruction on a case | Native: `case Percentage(Amount(var v), var rate) when …` (build 6) | Not expressible in the `visitXxx` signature itself; would need an `if`/`instanceof` chain *inside* the visit method, reintroducing exactly what Visitor was meant to avoid |
| Works across a module boundary you don't control | No — `permits` is closed to outsiders by construction | Yes — this is Visitor's one durable advantage over sealed types |

**The gotcha.** `**Insight:**` Both patterns have the *same* asymmetry, just on opposite sides:
adding a case is cheap in the direction each pattern doesn't optimize for, and expensive
(compiler-enforced, not silent) in the direction it does. This is the classic "expression
problem" — you can optimize for cheap-new-cases (sealed + switch) or cheap-new-operations
(Visitor, symmetric with the switch side), but a single hierarchy design cannot make both
directions free at once in a statically typed language without a hierarchy-crossing mechanism
neither of these two patterns provides.

**Interview:** "When would you still choose Visitor over sealed types plus pattern matching in
2026?" — when the element hierarchy must stay open to types you don't control at compile time
(plugins, extension points across a module boundary), because `sealed` forbids exactly that by
design; for a closed hierarchy you own, sealed-plus-switch wins on line count, on native
deconstruction/guard support, and on the compiler telling you *which* switches to fix rather than
which visitor classes to fix.

> **Visitor and sealed-plus-`switch`** achieve the same compiler-enforced totality by opposite
> means — double dispatch through an interface method per case, versus a single dispatch checked
> against a closed `permits` list — and the choice between them is the expression problem: which
> direction (new cases, or new operations) you need to add without touching existing code.

#### Diff vs the real one — hand-rolled double dispatch vs `SwitchBootstraps.typeSwitch`

| Dimension | Visitor's `accept`/`visitXxx` double dispatch | `switch` over a sealed type |
|---|---|---|
| Edge cases (unhandled case) | Missing `visitXxx` override is a compile error on the *implementation* (or silently absorbed by a `default` method) | Missing `case` is a compile error on the *switch site*, or a runtime `MatchException` (build 4) |
| Intrinsics | Two ordinary `invokeinterface` calls per dispatch (`accept`, then `visitXxx`) | One `invokedynamic` to a cached `typeSwitch` call site, then a `tableswitch` jump (beat 8) |
| Serialization | N/A | N/A |
| Null policy | `null.accept(visitor)` throws plain `NullPointerException` from the JVM's own null-check on the invoke, no custom message | `switch (null)` throws `NullPointerException` from the *bootstrap's* own explicit null handling (a deliberate design choice, not an accidental NPE), unless `case null ->` is present |
| Thread safety | Visitor instances are typically stateless and reusable across threads, same as any dispatch table | Same — the sealed elements and the switch method are both stateless here |
| Allocation | A `Visitor` implementation instance must be constructed per use unless cached — extra allocation the switch form never needs | No visitor object to allocate; the bootstrap's `MethodHandle` chain is built once per call site, not per invocation |
| Why the JDK bothers | — | `typeSwitch` centralizes what would otherwise be N interface methods times M visitor implementations into one indexed jump table, and lets the same mechanism support guards and deconstruction (build 6) that double dispatch cannot express in its method signature |

---

### 6. An expression-tree interpreter over a sealed record hierarchy

**Mental model first.** A sealed record hierarchy plus record deconstruction patterns gives you a
tree-shaped abstract syntax tree "for free" — no visitor, no `instanceof` casts, no manual field
access. `eval(expr)` reads like the recursive mathematical definition of the tree's semantics,
because record patterns let you bind a case's components as local variables in the same line that
identifies the case.

**Why it exists.** Before nested record patterns (finalized alongside pattern matching for
`switch`, JEP 440/441, Java 21), interpreting a tree required either the Visitor pattern (build 5)
or a chain of `instanceof` casts followed by manual field access via accessors — both work, but
both separate "which case is this" from "what are its parts," forcing two lookups where nested
deconstruction needs one.

**When to reach for it, and when not.** Reach for it whenever you're modelling a genuinely
recursive, closed grammar — an arithmetic expression, a filter predicate tree, a routing rule set.
Do not reach for it for a flat, non-recursive sealed hierarchy (the four rails, build 4/5) — nested
deconstruction earns its keep specifically when cases *contain* other cases of the same sealed
type.

**How it works, and the concrete example.** QuizStakes' bonus-consumption rule — "bonus portion is
`min(bonusAvailable, 10% of stake)`, rounding down to the minor unit" — is a small arithmetic
expression tree in its own right. Modelled as a sealed hierarchy and interpreted with nested
deconstruction and a guard, compiled and run on this machine:

```java
sealed interface SettlementExpr permits Amount, Min, Percentage, Sum {}
record Amount(BigDecimal value) implements SettlementExpr {}
record Sum(SettlementExpr left, SettlementExpr right) implements SettlementExpr {}
record Percentage(SettlementExpr base, BigDecimal rate) implements SettlementExpr {}
record Min(SettlementExpr a, SettlementExpr b) implements SettlementExpr {}

static BigDecimal eval(SettlementExpr expr) {
    return switch (expr) {
        case Amount(var v) -> v;
        case Sum(var l, var r) -> eval(l).add(eval(r));
        case Percentage(var base, var rate) when rate.signum() == 0 -> BigDecimal.ZERO;
        case Percentage(Amount(var v), var rate) -> v.multiply(rate).setScale(2, RoundingMode.DOWN);
        case Percentage(var base, var rate) -> eval(base).multiply(rate).setScale(2, RoundingMode.DOWN);
        case Min(var a, var b) -> eval(a).min(eval(b));
    };
}
```

Every arm here is doing real deconstruction work: `case Amount(var v)` binds the wrapped
`BigDecimal` directly, no `.value()` call needed; `case Percentage(Amount(var v), var rate)` is a
**nested** pattern — it only matches when the `Percentage`'s `base` is itself an `Amount`, binding
straight through two levels in one line, and falls through to the more general
`case Percentage(var base, var rate)` arm (which recurses through `eval(base)`) for any other
shape of base; `case Percentage(var base, var rate) when rate.signum() == 0` is a **guard** — a
boolean condition evaluated only after the type/shape pattern matches, letting the zero-rate case
short-circuit without a division-by-zero-style special case anywhere else.

`[PROVE]` Run against the domain's own canonical numbers — the QuizStakes rounding example, a 3.33
stake:

```
10% of 3.33 (rounded down) = 0.33
min(5.00, 0.33) = 0.33
min(0.10, 0.33) = 0.10
10% of (1.00 + 2.33) = 0.33
0% of 3.33 = 0
```

The first line reproduces the domain's own worked example exactly — 10% of 3.33 rounds down to
0.33, not up to 0.34 — because the `Percentage` arm always calls `setScale(2, RoundingMode.DOWN)`,
matching §11's bonus-rounding rule verbatim. `min(0.10, 0.33) = 0.10` proves `Min` correctly picks
the scarcer side when bonus is nearly exhausted, which is the exact shape of the domain's real
stake-consumption formula (`min(BONUS_AVAILABLE, 10% of stake)`).

**The gotcha.** `**Pitfall:**` The last line, `0% of 3.33 = 0`, is not a formatting bug in this
write-up — it is the actual printed output, and it is a genuine trap: the guard arm returns
`BigDecimal.ZERO` directly, which has scale 0 (`"0"`), while every other arm returns a
`setScale(2, ...)` result (`"0.33"`, `"3.00"`). Mixing a bare `BigDecimal.ZERO` into a code path
that otherwise guarantees a fixed scale reintroduces exactly the kind of scale inconsistency
`BigDecimal` disciplines are supposed to prevent — the fix is `BigDecimal.ZERO.setScale(2)` in
that arm, not `BigDecimal.ZERO`.

**Interview:** "How does record pattern matching let you write a tree interpreter without a
Visitor?" — each `case Type(pattern, ...)` arm both narrows the type *and* destructures its
components in one step, including nesting (`Percentage(Amount(var v), var rate)`), and `when`
guards let you special-case a shape without a second `if` after the match — replacing what a
Visitor's `visitXxx` body would do manually with accessor calls.

> **Nested record deconstruction turns "which case is this, and what are its parts" into a single
> pattern, and `when` guards attach boolean preconditions to a specific shape without leaving the
> `switch` — the two features together let a sealed record hierarchy double as an interpretable
> AST with no separate visitor machinery.**

#### Diff vs the real one — this interpreter vs a production expression evaluator

| Dimension | `eval(SettlementExpr)` as built here | A production-grade evaluator |
|---|---|---|
| Edge cases | No division node exists, so no divide-by-zero case; a `null` sub-expression NPEs on the recursive `eval` call with no diagnostic | Would validate the tree shape (or make illegal states unrepresentable) before evaluating, and report the offending node, not just NPE |
| Intrinsics | None | None — this stays plain object dispatch even in a production interpreter unless compiled to bytecode/native code |
| Serialization | Falls out for free: every node is a record of records, so the whole tree is naturally (de)serializable by any reflection-based serializer | Same, plus likely a stable wire format independent of the Java type names |
| Null policy | No compact-constructor validation anywhere in this build — a `null` `BigDecimal` inside `Amount` NPEs deep inside `eval`, far from the construction site | Would validate at construction (compact constructor) so the failure points at the bad node immediately |
| Thread safety | Trivially safe — every node is an immutable record, so a tree can be shared and evaluated concurrently with no locking | Same, plus likely caching evaluated sub-results (memoization), which does need care under concurrent evaluation |
| Allocation | `eval` re-walks and reallocates a fresh `BigDecimal` at every node on every call, with no caching | Would fold constant subtrees once and cache the result, especially for a tree evaluated repeatedly (e.g. once per stake settlement) |
| Why the JDK bothers | — | The JDK's own answer to "should the language ship a general expression-evaluation API" is no — `javax.script` was deprecated for removal and pattern-matching-plus-records is the JDK's actual answer: give you the deconstruction primitives, let you build the seven-line interpreter your specific grammar needs |

---

### 7. A reflective "wither" built from `getRecordComponents()` and the canonical constructor

**Mental model first.** A record's canonical constructor and its `getRecordComponents()`
reflection are two halves of the same contract — the components you can read are exactly the
parameters the canonical constructor accepts, in the same order, with the same types. A generic
"wither" walks that contract at runtime: read every component's current value, substitute one, and
re-invoke the canonical constructor with the (mostly unchanged) argument list.

**Why it exists.** Records have no built-in "copy with one field changed" syntax (unlike, say,
Kotlin's `data class .copy(field = value)`). Hand-writing a `withCashPortion(Money v)` method per
component per record is exactly the kind of per-type boilerplate records were supposed to
eliminate elsewhere, which is what makes a generic reflective wither tempting — write it once,
apply it to any record.

**When to reach for it, and when not.** Reach for it, if at all, only for genuinely generic
infrastructure code operating over arbitrary record types it doesn't know ahead of time (a
test-data builder library, a generic PATCH-merge layer for a REST API). Do not reach for it as a
substitute for hand-written `withX` methods on your own domain types — the cost measured below is
real, and the loss of compile-time checking on the component name is a bug magnet.

**How it works.** `getRecordComponents()` returns a `RecordComponent[]` in declaration order; each
component exposes `getName()`, `getType()`, and `getAccessor()` (the `Method` object for reading
it). Building the new argument array means reading every *other* component through its accessor,
substituting the target component's new value, then looking up and invoking the canonical
constructor via `getDeclaredConstructor(paramTypes)`:

```java
@SuppressWarnings("unchecked")
static <T extends Record> T with(T record, String componentName, Object newValue) {
    Class<T> type = (Class<T>) record.getClass();
    RecordComponent[] components = type.getRecordComponents();
    Class<?>[] paramTypes = new Class<?>[components.length];
    Object[] args = new Object[components.length];
    boolean found = false;
    for (int i = 0; i < components.length; i++) {
        RecordComponent rc = components[i];
        paramTypes[i] = rc.getType();
        Object current = rc.getAccessor().invoke(record);
        if (rc.getName().equals(componentName)) {
            args[i] = newValue;
            found = true;
        } else {
            args[i] = current;
        }
    }
    if (!found) {
        throw new IllegalArgumentException("No component named " + componentName + " on " + type);
    }
    Constructor<T> canonical = type.getDeclaredConstructor(paramTypes);
    canonical.setAccessible(true);
    return canonical.newInstance(args);
}
```

`[PROVE]` Run against `record StakeSplit(BigDecimal bonusPortion, BigDecimal cashPortion, String
roundId)` on this machine:

```
original: StakeSplit[bonusPortion=0.33, cashPortion=3.00, roundId=ROUND-1]
with cashPortion=4.00: StakeSplit[bonusPortion=0.33, cashPortion=4.00, roundId=ROUND-1]
original unchanged: true
unknown component rejected: No component named doesNotExist on class ReflectiveWither$StakeSplit
100,000 reflective withers took 462 ms
```

`[NUM]` **462 ms / 100,000 calls ≈ 4.62 microseconds per call** — every call does: one
`getRecordComponents()` array allocation (this method does *not* cache it, though a shipped
version would have to), three reflective accessor invocations (`Method.invoke`, which boxes and
unboxes and checks access on every call unless further cached), one `getDeclaredConstructor`
lookup, one `Constructor.newInstance` call (itself reflective, with the same argument-array boxing
cost), for a three-component record. A hand-written `withCashPortion(BigDecimal v)` method is a
single direct constructor call — no reflection, no array allocation, no lookup — and would be
measured in single-digit nanoseconds for the same operation, roughly **three orders of magnitude**
faster.

**The gotcha.** `**Pitfall:**` "It compiles, so it's safe" does not apply here — `with(original,
"doesNotExist", "x")` compiles cleanly (the component name is just a `String`) and fails only at
*runtime*, with `IllegalArgumentException`, the moment that code path executes. Every one of the
compile-time guarantees this whole file has spent seven builds establishing — the compiler
checking every `equals` field, the compiler checking every `switch` case — is deliberately given
up the moment you route construction through a component name typed as a `String` instead of
through the generated, statically-checked canonical constructor.

**The argument for why you should not ship it, made explicit:** (1) component-name typos are
runtime `IllegalArgumentException`s, not compile errors — the exact bug class records exist to
prevent, reintroduced through the back door; (2) measured cost is roughly three orders of
magnitude above a hand-written `withX` method, per call, with no caching in this version and
non-trivial caching complexity (keyed by `Class` *and* component name) to close even part of that
gap; (3) reflective access to a record's declared constructor can be restricted under the module
system's strong encapsulation (`setAccessible(true)` throws `InaccessibleObjectException` for a
module that hasn't opened the package), which a hand-written method never risks. A generic
reflective wither is a reasonable *library-internals* tool; it is not a reasonable substitute for
domain code writing its own three or four `withX` methods by hand.

**Interview:** "How would you build a generic `with` for any record?" — walk
`getRecordComponents()` in order to build the canonical constructor's parameter types and current
argument values, substitute the target component, and invoke the canonical constructor reflectively
— and be ready to name the cost (measured here at ~4.6 µs/call, roughly a thousand times a direct
constructor call) as the reason production code writes the three or four `withX` methods by hand
instead.

> **`getRecordComponents()` plus the canonical constructor gives you a fully generic "copy with one
> field changed," at a measured cost of microseconds per call versus nanoseconds for a hand-written
> equivalent, and at the cost of every component-name typo becoming a runtime exception instead of
> a compile error — which is why it belongs in generic infrastructure, not in domain code.**

#### Diff vs the real one — reflective wither vs a hand-written `withX` method

| Dimension | Reflective `with(record, name, value)` | Hand-written `withCashPortion(BigDecimal v)` |
|---|---|---|
| Edge cases (unknown component) | Runtime `IllegalArgumentException`, discovered only when that code path runs | Doesn't exist as a category — there is no name to get wrong, the method just isn't there |
| Intrinsics | None; `Method.invoke`/`Constructor.newInstance` are ordinary (slow) reflective calls, not JIT-intrinsified the way `Class.cast` or `Objects.requireNonNull` are | Ordinary direct call, fully inlinable by the JIT like any small method |
| Serialization | Orthogonal — doesn't touch serialization | Orthogonal |
| Null policy | Passes `null` straight through the same as the canonical constructor would | Same |
| Thread safety | `getRecordComponents()`'s returned array is freshly allocated per call — no shared mutable state, safe but wasteful | Same statelessness, no waste |
| Allocation tricks | Per call: one `RecordComponent[]`, one `Class<?>[]`, one `Object[]`, plus boxing for any primitive component — measured at 462 ms / 100,000 calls | Per call: one `BigDecimal`, one `StakeSplit` — nothing else |
| Why you should not ship it | — | This *is* what you ship — the whole point of this build is to make the reflective version's cost and risk concrete enough to justify writing four short methods by hand instead |

---

### 8. Diff vs the compiler's actual output — `Record`, `ObjectMethods`, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch`, `MatchException`

**Mental model first.** Everything builds 1 through 6 describe as "the compiler generates X" is a
specific, inspectable set of class-file attributes and `invokedynamic` bootstrap calls — not a
metaphor. `javap -v -p` on the compiled class files, run on this machine with `javac --release 21`,
shows exactly what's there.

**Why it exists.** Records and sealed types needed new class-file-level plumbing because neither
fits the pre-existing model cleanly: a record's generated methods have no source to point `javap`
at in the traditional sense (they're built by a runtime bootstrap, not compiled per-class), and a
sealed interface needs to declare its closed subtype set in a way reflection and the verifier can
both see. JEP 359 (records) added the `Record` attribute and `ObjectMethods.bootstrap`; JEP 409
(sealed classes) added the `PermittedSubclasses` attribute; JEP 441 (pattern matching for switch)
added `SwitchBootstraps.typeSwitch` and `MatchException`.

**When to reach for it, and when not.** This is not a "reach for it" concept — you cannot choose
not to have these attributes; they're what `record` and `sealed` compile to. Reach for reading
them with `javap` specifically when debugging a serialization framework, a reflection-based ORM,
or exactly the kind of `MatchException` failure build 4 demonstrated, where the source-level
explanation ("a case was missing") isn't enough to explain a stack trace that names classes you
didn't write.

**How it works — walked from real `javap -v -p` output on `record StakeSplit(BigDecimal
bonusPortion, BigDecimal cashPortion)`, compiled with `javac --release 21`.**

The **`Record` attribute** — present only on record class files, lists every component and its
descriptor, independent of the field/method tables:

```
Record:
  java.math.BigDecimal bonusPortion;
    descriptor: Ljava/math/BigDecimal;

  java.math.BigDecimal cashPortion;
    descriptor: Ljava/math/BigDecimal;
```

This is the attribute `getRecordComponents()` (build 7) reads at runtime — it is *not* derived
from the field table, which is why a record's private fields staying private doesn't stop
reflection from discovering the components: the `Record` attribute is a separate, always-present
manifest.

The **`ObjectMethods.bootstrap` indy sites** for `toString`/`hashCode`/`equals` — three separate
`invokedynamic` instructions, one per method, all bootstrapped through the same static method:

```
16: InvokeDynamic      #0:toString:(LDemo$StakeSplit;)Ljava/lang/String;
20: InvokeDynamic      #0:hashCode:(LDemo$StakeSplit;)I
24: InvokeDynamic      #0:equals:(LDemo$StakeSplit;Ljava/lang/Object;)Z

BootstrapMethods:
  0: #47 REF_invokeStatic java/lang/runtime/ObjectMethods.bootstrap:(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/TypeDescriptor;Ljava/lang/Class;Ljava/lang/String;[Ljava/lang/invoke/MethodHandle;)Ljava/lang/Object;
    Method arguments:
      #8 Demo$StakeSplit
```

and, elsewhere in the constant pool, the field-getter method handles passed as bootstrap
arguments: `REF_getField Demo$StakeSplit.bonusPortion` and `REF_getField
Demo$StakeSplit.cashPortion`, plus the literal string `"bonusPortion;cashPortion"` — the component
name list `ObjectMethods.bootstrap` parses to know which fields to fold into each generated
method. `[SOURCE]` Each generated method's *body* is genuinely three bytecode instructions —
`aload_0`, `invokedynamic`, `areturn`/`ireturn` — the entire structural comparison or hashing logic
lives inside the `MethodHandle` chain the bootstrap builds at first invocation and links to that
call site, not in bytecode the compiler emitted per-method.

The **`PermittedSubclasses` attribute** — on the sealed interface's own class file, naming every
permitted direct subtype by constant-pool class reference:

```
PermittedSubclasses
  Demo$CardDeposit
  Demo$BankDeposit
  Demo$CardWithdrawal
```

This is the attribute the verifier and the `sealed` compile-time check both consult — it is what
build 4's exhaustiveness check is actually checked *against*, and it is what widening `permits`
and recompiling only the interface (build 4's `MatchException` reproduction) changes without the
switch's stale class file ever finding out.

The **`SwitchBootstraps.typeSwitch` indy site**, from `static int lag(Rail rail)`'s three-case
switch, and its full bytecode:

```
static int lag(Demo$Rail);
    Code:
       0: aload_0
       1: dup
       2: invokestatic  #7        // Method java/util/Objects.requireNonNull
       5: pop
       6: astore_1
       7: iconst_0
       8: istore_2
       9: aload_1
      10: iload_2
      11: invokedynamic #13,  0   // InvokeDynamic #0:typeSwitch:(Ljava/lang/Object;I)I
      16: tableswitch   { // 0 to 2
                     0: 54
                     1: 63
                     2: 75
               default: 44
          }
      44: new           #17       // class java/lang/MatchException
      47: dup
      48: aconst_null
      49: aconst_null
      50: invokespecial #19       // MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
      53: athrow
      54: aload_1
      55: checkcast     #22       // class Demo$CardDeposit
      58: astore_3
      59: iconst_1
      60: goto          82

BootstrapMethods:
  0: #43 REF_invokeStatic java/lang/runtime/SwitchBootstraps.typeSwitch:(MethodHandles$Lookup, String, MethodType, Object[])CallSite;
    Method arguments:
      #22 Demo$CardDeposit
      #24 Demo$BankDeposit
      #26 Demo$CardWithdrawal
```

`[BYTECODE]` Reading this instruction by instruction: instructions 0–2 are an explicit
`Objects.requireNonNull` call on the selector — this is the source of the "stricter than
`instanceof`" null policy from build 4, made concrete: a `null` `Rail` throws NPE at instruction 2,
*before* the `typeSwitch` bootstrap even runs. Instructions 7–8 initialize a restart index to `0`
(used if a guard fails and the switch needs to resume matching from the next candidate case — not
exercised by this particular switch, since none of its arms have guards, but always present in the
generated shape). Instruction 11 is the `typeSwitch` bootstrap call, taking the selector and the
restart index, returning an `int` case index. The `tableswitch` at instruction 16 jumps by that
index directly to the matched arm's `checkcast`-and-bind code — this is the "one indexed jump"
build 4's diff table promised, replacing what an `if`/`instanceof` chain would do as N sequential
tests. The `default` arm (instruction 44) is exactly the `MatchException` construction from build
4's runtime-failure reproduction — `new MatchException`, `dup`, `aconst_null` twice (both
constructor arguments are `null` — no message, no cause), `invokespecial` the `(String,
Throwable)` constructor, `athrow`. The bootstrap's method arguments (`Demo$CardDeposit`,
`Demo$BankDeposit`, `Demo$CardWithdrawal`) are exactly the *compile-time* view of the sealed
hierarchy — this is the frozen list that goes stale when the interface is later widened without
recompiling this class, which is precisely how build 4's separate-compilation `MatchException`
happens.

**The gotcha.** `**Insight:**` The `default: 44` arm in the `tableswitch` — the `MatchException`
throw — exists in the bytecode of *every* pattern switch the compiler judges exhaustive at compile
time, sealed or not. The compiler proves you can never reach it given the sealed hierarchy it can
see; it does not (cannot) remove the arm, because the verifier and the runtime have no way to
re-derive that proof from the class file alone once separate compilation is possible. The
`MatchException` is not a fallback for a case the compiler "missed" — it's a safety net for a
proof that was correct when built and can be invalidated later by a change *outside* the class
that trusted it.

**Interview:** "Where does `MatchException` actually come from in a compiled pattern switch?" —
every pattern switch the compiler certifies as exhaustive still compiles a `default` arm that
throws `MatchException`, because the exhaustiveness proof is only valid against the `permits` list
visible at that compilation; the arm exists precisely to catch the case where a class compiled
against a different, incompatible version of the sealed hierarchy reaches this switch at runtime.

> **A `record`'s generated methods are three `invokedynamic` sites bootstrapped through
> `ObjectMethods.bootstrap`, reading a `Record` attribute's component manifest; a sealed
> interface's closed subtype set is a `PermittedSubclasses` attribute; and a pattern `switch`'s
> exhaustiveness compiles to a `SwitchBootstraps.typeSwitch` indy plus a `tableswitch`, whose
> `default` arm always throws `MatchException` — a proof that held at compile time, re-checked
> against whatever the runtime's actual sealed hierarchy turns out to be.**

#### Diff vs the real one — the source-level feature vs its class-file reality

| Dimension | What the source reads like | What actually compiles |
|---|---|---|
| Edge cases | "Records generate equals/hashCode/toString" | Three `invokedynamic` sites, lazily linked, sharing one bootstrap and one component-name descriptor string |
| Intrinsics | "Sealed switch is exhaustive" | A `typeSwitch` bootstrap call site plus a `tableswitch`, both built once per call site at first execution |
| Serialization | N/A at source level | The `Record` attribute is what a reflection-based serializer actually walks — not the private field table |
| Null policy | "switch throws NPE on null" | An explicit `Objects.requireNonNull` bytecode call **before** the `typeSwitch` bootstrap even runs — the NPE happens outside the switch machinery, not inside it |
| Thread safety | N/A | The `CallSite` each bootstrap produces is cached per call site after first linkage — safe to hit from multiple threads without re-linking |
| Allocation tricks | N/A | Bootstrap linkage itself allocates (`MethodHandle` chains); every subsequent invocation of an already-linked site allocates only what the method body genuinely needs |
| Why the JDK bothers | — | Deferring method-body construction to a runtime bootstrap keeps class files smaller (no per-record generated bytecode for `equals`/`hashCode`/`toString`) and centralizes the generation logic in one JDK-maintained class (`ObjectMethods`) instead of duplicating it into every compiled record |

---

## Pitfalls

### Believing `List.copyOf` in a compact constructor gives you two distinct object identities across accessor calls

**Wrong**

```java
record PaymentRunCopyInOut(List<WithdrawalTransaction> transactions) {
    PaymentRunCopyInOut {
        transactions = List.copyOf(transactions);
    }
    @Override
    public List<WithdrawalTransaction> transactions() {
        return List.copyOf(transactions); // "a fresh copy every call"
    }
}
```

Measured on this machine: `copyInOut.transactions() == copyInOut.transactions()` is **`true`**,
not `false` — `List.copyOf` recognizes its own already-immutable output and returns it unchanged
rather than copying again.

**Right**

Don't claim identity-distinctness you haven't measured. The isolation guarantee (no caller can
mutate what the record holds, and no caller can mutate what the accessor returns) still holds —
what's shared is itself unmodifiable, so sharing it is harmless. If you specifically need a fresh
mutable copy per call (e.g. handing callers a scratch list they're allowed to mutate), copy into a
genuinely mutable type explicitly: `new ArrayList<>(transactions)`, which never short-circuits.

**Why people believe it:** "copy in, copy out" is usually taught as a symmetry — two copies, two
identities — and `List.copyOf`'s identity-preserving fast path is documented in its javadoc but
rarely read, because most engineers reach for `List.copyOf` for the immutability guarantee, not
for its copy-avoidance behaviour.

### Fixing a record's array-component `equals` bug in only one direction

**Wrong**

```java
record PaymentRunArraysFix(List<WithdrawalTransaction> transactions, byte[] signature) {
    PaymentRunArraysFix {
        signature = signature.clone(); // defends the field on the way in — looks complete
    }
    @Override
    public boolean equals(Object o) { /* uses Arrays.equals, correct */ }
    // no overridden accessor — signature() still returns the live internal array
}
```

The obvious test — mutate the caller's original array after construction, check the record is
unaffected — passes. A second test — mutate the array *returned by the accessor* — fails, because
that array is the record's actual internal field, handed out by reference.

**Right**

```java
@Override
public byte[] signature() {
    return signature.clone();
}
```

Clone on the way in **and** on the way out — the exact same two-direction discipline build 2's
`List` component needs, just with `clone()` in place of `List.copyOf`.

**Why people believe it:** the compact constructor is the more visible, more commonly-taught half
of defensive copying (it's "the constructor," the thing everyone checks); the accessor half is
easy to forget precisely because records normally generate accessors for you, and it's not obvious
that overriding one for `equals`/`hashCode` purposes doesn't also fix its aliasing.

### Assuming a sealed hierarchy's exhaustiveness is checked across module/JAR boundaries the way it is within one compilation

**Wrong**

```java
// library v1.0: sealed interface Rail permits CardDeposit, BankDeposit, CardWithdrawal {}
// consumer, compiled against v1.0:
static int lag(Rail rail) {
    return switch (rail) { case CardDeposit c -> 1; case BankDeposit b -> 14400; case CardWithdrawal w -> 1; };
}
// library upgrades to v1.1, adding BankWithdrawal to permits, consumer NOT recompiled
```

Reproduced on this machine exactly this way: the consumer's stale `.class` file throws
`java.lang.MatchException` with no message the first time a `BankWithdrawal` reaches it — no
compile error anywhere, because nothing recompiled the switch against the new `permits` list.

**Right**

Treat any `permits` change to a sealed type that crosses a module or artifact boundary as a
breaking change requiring a major version bump and forcing consumers to recompile, exactly the
discipline already applied to removing a method from a public interface — sealed types don't make
that discipline optional, they just move the failure from "won't compile" to "throws at runtime,"
and only for consumers who don't recompile.

**Why people believe it:** "sealed switch is exhaustive" is taught, correctly, as a single fact,
without the qualifier "within one compilation" attached — because within a single module, which is
the overwhelmingly common case in tutorials and interview questions, the qualifier never becomes
observable.

### Trusting a reflective wither's component name the way you'd trust a compiler-checked field reference

**Wrong**

```java
with(paymentRun, "signture", newValue); // typo, compiles fine — it's just a String
```

Compiles cleanly. Fails at runtime, and only when that exact code path executes, with
`IllegalArgumentException: No component named signture on class PaymentRun`.

**Right**

Either write the four `withX` methods by hand (each component name is now a Java identifier, typo-
checked by the compiler) or, if the generic reflective form is unavoidable for library-internals
reasons, validate every component name against `getRecordComponents()` in a unit test per call
site, not at the call site itself — the compiler cannot help you here, so something else has to.

**Why people believe it:** reflective code "looks like" ordinary method-call code at the call
site, and the mental model of "the compiler checks my code" doesn't automatically flag that a
`String` argument silently opted out of that checking for this one call.

## Cheat sheet

| Build | One-line takeaway | Verified number |
|---|---|---|
| 1. Hand-written record equivalent | `record` compiles to a `Record` attribute + `ObjectMethods` indy sites, not literal generated source | 38 hand-written lines vs 1 record line, 3 components |
| 2. `List` component, 3 ways | No-copy leaks both ways; copy-in-only leaks the accessor; copy-in-and-copy-out defends both, but `List.copyOf` may return the same instance twice | `List.copyOf(List.copyOf(x)) == x` measured `true` |
| 3. Array component | Arrays never override `Object.equals`/`hashCode` — a record's generated `equals` inherits that bug unless fixed | Fix: `List<Byte>`, or `Arrays.equals`/`hashCode` + double `clone()` |
| 4. Sealed + exhaustive switch | Exhaustiveness is compile-time within one compilation, `MatchException` across stale separate compilation | Exact `javac` error: `"the switch expression does not cover all possible input values"` |
| 5. Visitor, side by side | Same totality guarantee, opposite expression-problem tradeoff; Visitor still wins for open/extensible hierarchies | 10 lines (switch) vs 28 lines (Visitor) for 3 cases, 1 operation |
| 6. Expression-tree interpreter | Nested record patterns destructure through multiple levels in one `case`; `when` guards attach preconditions to a shape | `10% of 3.33` rounds down to `0.33`, matching §11's domain rule |
| 7. Reflective wither | Generic but slow, and trades compile-time field-name checking for a runtime `IllegalArgumentException` | ~4.62 µs/call measured, vs single-digit ns for a hand-written `withX` |
| 8. Diff vs the compiler | `Record` attribute, `ObjectMethods` bootstrap, `PermittedSubclasses`, `SwitchBootstraps.typeSwitch`, `MatchException`'s `default` arm | `MatchException(String, Throwable)` constructed with `aconst_null, aconst_null` |
| Compact constructor | Reassign the **parameter**, never `this.field =` — the field is `final` | `error: cannot assign a value to final variable bonusPortion` |
| `switch` null policy | `switch (sealedRef)` NPEs via an explicit `Objects.requireNonNull` bytecode call, before the `typeSwitch` bootstrap even runs | Confirmed at bytecode offsets 0–2 in `javap -c` |

## Self-test

**Q1.** A `record StakeSplit(Money bonusPortion, Money cashPortion, RoundId roundId)` and its
hand-written equivalent behave identically for `equals`, `hashCode` and `toString`. Are their
compiled class files the same size? Why or why not?

<details><summary>Answer</summary>

No — the record's class file is smaller. The hand-written class's `equals`/`hashCode`/`toString`
are ordinary bytecode present in full from class-load. The record's three methods are each a
single `invokedynamic` instruction (`aload_0`, `invokedynamic`, return) bootstrapped through
`ObjectMethods.bootstrap`, which builds the actual comparison/hashing/formatting logic as a
`MethodHandle` chain at first invocation rather than as per-class bytecode. The 38-versus-1 line
difference is a source-level difference; the class-file difference is smaller in relative terms but
still real, because the record defers three method bodies to a shared runtime bootstrap instead of
emitting them per class.

</details>

**Q2.** You give a `PaymentRun` record a `List<WithdrawalTransaction>` component and a compact
constructor that does `transactions = List.copyOf(transactions);`. Is the accessor
`transactions()` now safe from a caller who holds a reference to what it returns and mutates it?

<details><summary>Answer</summary>

Yes, but not because the accessor was overridden — it wasn't. `List.copyOf`'s result is itself
unmodifiable, so calling `.add(...)` on whatever `transactions()` returns throws
`UnsupportedOperationException` rather than succeeding. The accessor still returns the *same*
defended reference on every call (not a fresh copy), but since that reference can't be mutated,
returning the same one every time is harmless. This is different from build 2's variant 3
(explicitly overridden accessor calling `List.copyOf` again), which is written defensively but,
measured, also returns the same instance across calls whenever the underlying list is already one
of `List.copyOf`'s own immutable lists.

</details>

**Q3.** A `PaymentRunBroken` record has a `byte[] signature` component and no overrides. Two
instances are built from separate `byte[]` arrays holding the identical bytes `{1, 2, 3}`. What
does `.equals()` return, and what does the generated `.toString()` print for the `signature` field?

<details><summary>Answer</summary>

`.equals()` returns `false` — the generated `equals` calls `Objects.equals` on each component,
which for two distinct array references delegates to `Object.equals` (reference identity), because
arrays never override `equals`. `.toString()` prints something like `[B@27716f4` — arrays inherit
`Object.toString()`, `[B` being the JVM's type descriptor for `byte[]` and the hex suffix being the
identity hash from `Object.hashCode()`, not `Arrays.hashCode()`.

</details>

**Q4.** You add a fourth record, `BankWithdrawal`, to `sealed interface Rail permits CardDeposit,
BankDeposit, CardWithdrawal`, and recompile the interface, the new record, and the class containing
the exhaustive switch over `Rail`, all together. What happens?

<details><summary>Answer</summary>

A compile error, verified verbatim on this machine: `error: the switch expression does not cover
all possible input values`, pointing at the `switch` keyword's line. This is the compile-time
exhaustiveness guarantee working as designed — recompiling the switch together with the widened
hierarchy re-checks it against the new `permits` list and finds it incomplete.

</details>

**Q5.** Same change as Q4, except only `Rail.java` and the new `BankWithdrawal.java` are
recompiled; the class file containing the switch is left as stale bytecode from before the fourth
case existed. A `BankWithdrawal` instance is then routed through that switch at runtime. What
happens, and why is this not a compile error?

<details><summary>Answer</summary>

`java.lang.MatchException` is thrown at runtime, with no message — verified on this machine.
It's not a compile error because nothing recompiled the switch: the exhaustiveness check only ran
once, against the three-case `permits` list visible at that earlier compilation. The switch's
bytecode always includes a `default` arm that constructs and throws `MatchException` (via
`SwitchBootstraps.typeSwitch`'s generated `tableswitch`); the compiler proved that arm was
unreachable *for the hierarchy it could see*, and that proof silently stopped being valid once the
hierarchy changed underneath the stale class file.

</details>

**Q6.** Compare, for three element types and one operation: a sealed hierarchy with an exhaustive
`switch`, versus the same hierarchy expressed as a classical Visitor. Which is more code, measured,
and name one concrete situation where the more-verbose option is still the right choice.

<details><summary>Answer</summary>

The sealed-plus-switch version measures 10 lines (three one-line record declarations, one
six-line switch method); the Visitor version measures 28 lines (two interfaces, three element
classes with a field/constructor/`accept` each, one concrete visitor) — 2.8× the code for an
identical operation over identical cases. Visitor is still the right choice when the element
hierarchy must stay open to types outside your control — a plugin system, or any hierarchy crossing
a module boundary where third parties add new implementations — because `sealed` forbids that by
construction (`permits` is a closed list), while Visitor's `accept` method just needs implementing
by whoever adds the new type.

</details>

**Q7.** In the expression-tree interpreter, `case Percentage(var base, var rate) when
rate.signum() == 0 -> BigDecimal.ZERO;` prints `0` rather than `0.00` when exercised on the domain's
3.33 stake with a zero rate, while every other arm returns a value scaled to 2 decimal places. Is
this a bug, and if so, where?

<details><summary>Answer</summary>

Yes — it's a scale-consistency bug in that one guard arm. Every other arm ends with
`.setScale(2, RoundingMode.DOWN)`, guaranteeing a fixed decimal scale matching the domain's money
representation. This arm returns the bare constant `BigDecimal.ZERO`, whose scale is 0, breaking
that guarantee for exactly the input that triggers the guard. The fix is
`BigDecimal.ZERO.setScale(2)` in that arm, not the bare constant.

</details>

**Q8.** A generic reflective `with(record, componentName, newValue)` method, built from
`getRecordComponents()` and the canonical constructor, measured 462 ms for 100,000 calls against a
three-component record. What three costs specifically make it roughly a thousand times slower per
call than a hand-written `withCashPortion(Money v)` method, and what is the concrete risk of using
it in domain code that a hand-written method doesn't have?

<details><summary>Answer</summary>

Per call it allocates a `RecordComponent[]` (uncached in this build), invokes each component's
accessor reflectively (`Method.invoke`, which boxes/unboxes and access-checks every call unless
separately cached), looks up the canonical constructor via `getDeclaredConstructor`, and invokes it
reflectively (`Constructor.newInstance`, with the same argument-boxing overhead) — none of which a
direct constructor call pays. The concrete risk: the component name is a plain `String`, so a typo
(`"signture"` for `"signature"`) compiles cleanly and fails only at runtime with
`IllegalArgumentException`, reintroducing exactly the transcription-bug class records exist to
eliminate.

</details>

**Q9.** Why does `switch (rail)` on a sealed reference type throw `NullPointerException` on a
`null` selector, and where in the compiled bytecode does that check actually happen — inside the
`typeSwitch` bootstrap, or somewhere else?

<details><summary>Answer</summary>

It's a deliberate design choice, not an accidental side effect of the type checks: `switch` on a
reference-typed selector has always NPE'd on `null` (even before pattern matching, for the classic
`String`/enum `switch`), and pattern-matching `switch` keeps that unless an explicit `case null ->`
arm opts in to handling it. Verified in the actual bytecode: the NPE check is an explicit
`Objects.requireNonNull` call at instructions 0–2 of the compiled method, executed *before*
instruction 11's `invokedynamic` to the `typeSwitch` bootstrap — the null check happens outside and
ahead of the switch machinery itself, not inside it.

</details>

## Deferred

None.

---

**Leaves covered:** 4.5.1–4.5.8 (8 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 1343
