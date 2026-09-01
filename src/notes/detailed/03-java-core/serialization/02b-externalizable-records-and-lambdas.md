# 03 Java Core — Serialization: `Externalizable`, records and lambdas — INTERMEDIATE (§2.10, 2.10.8, 2.10.9, 2.10.14)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [The magic methods and the constructor bypass](02a-magic-methods-and-constructor-bypass.md) · Next: [The attack surface, filters and the practical rule](02c-attack-surface-filters-and-the-practical-rule.md)

`02-serialization.md` owns the marker interface, `serialVersionUID`, `transient` and
compatibility. `02a` owns the five hooks, the constructor bypass, and the serialization proxy —
all of that is still the *default* protocol, just with escape hatches bolted on. This file owns
the three serial forms that are not the default protocol at all: `Externalizable`, records, and
lambdas. Each of them replaces field injection with something else — hand-written bytes, a real
constructor call, or a runtime-generated recipe — and each replacement has a different cost.
`02c` closes the tier with the security case and the practical rule for which of all this you
should actually use. The question this file answers, in bold: **which classes do NOT go through
the default protocol, and what does each of them do instead?**

## 1. `Externalizable` and why it is worse, not better (§2.10.8)

`Externalizable` looks like the grown-up option. You write the bytes yourself with
`writeExternal`/`readExternal`, so surely it is faster, smaller, and safer than letting
`ObjectOutputStream` walk your fields by reflection. It is none of those things by default, and it
is actively worse on the one axis QuizStakes cares about most: it makes immutable value types
impossible. `Externalizable` does not remove the implicit contract of `02a`'s five hooks — it
replaces it with a different implicit contract that is *harder* to get right, because now the
object is built by a constructor that is not allowed to know anything, and then mutated field by
field after the fact from a stream you have to parse by hand.

### Why it exists

Before `Externalizable`, the only way to control the wire format at all was `writeObject` /
`readObject`, and those still ride on top of the default field descriptors and `defaultWriteObject`
plumbing. `Externalizable` exists for the case where you want to own the byte layout completely —
no per-class field descriptors, no field names in the stream, just the bytes you chose to write, in
the order you chose to write them. That is a real win for wire size when a type is serialized at
volume. The cost is that everything the default protocol did for you — object creation, superclass
handling, field reconciliation across versions — now has to be reinvented by hand, and the JDK
gives you exactly one hook to do it with.

### How it works

An `Externalizable` type must expose two methods, and both are **`public`**, unlike the `private`
hooks of `02a`:

```java
public void writeExternal(ObjectOutput out) throws IOException;
public void readExternal(ObjectInput in) throws IOException, ClassNotFoundException;
```

Deserialization does this, and only this: allocate the object by calling its **public no-arg
constructor**, then call `readExternal` on the freshly constructed instance and let it fill in the
fields from the stream. There is no field descriptor reconciliation, no `defaultReadObject`, no
superclass walk. Whatever `readExternal` does not set stays at the constructor's default.

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```java
static class Ext implements Externalizable {
    int stakeMinor; String clientId; static int calls;
    public Ext() { calls++; }                      // public no-arg REQUIRED
    Ext(int s, String c) { stakeMinor = s; clientId = c; }
    public void writeExternal(ObjectOutput o) throws IOException { o.writeInt(stakeMinor); o.writeUTF(clientId); }
    public void readExternal(ObjectInput i) throws IOException { stakeMinor = i.readInt(); clientId = i.readUTF(); }
}
```

A round trip printed `Ext[420,c-1]`, and `calls` was `1` — the **public no-arg constructor ran
exactly once** during deserialization, doing nothing useful, before `readExternal` overwrote
everything it touched. Drop the public no-arg constructor:

```java
static class ExtNoCtor implements Externalizable {
    int v;
    ExtNoCtor(int v) { this.v = v; }
    public void writeExternal(ObjectOutput o) throws IOException { o.writeInt(v); }
    public void readExternal(ObjectInput i) throws IOException { v = i.readInt(); }
}
```

failed not at compile time but at deserialization time, verbatim:

```
java.io.InvalidClassException: Ver5$ExtNoCtor; no valid constructor
```

That is the shape of the trade: a compile-time-shaped requirement (does this class have a public
no-arg constructor?) enforced only when a stream is actually read, in production, against whatever
object graph happened to be persisted.

Four consequences follow directly from "public no-arg constructor, then public setter-by-stream":

- **`final` fields are impossible in practice.** `readExternal` runs after the constructor and
  assigns fields; `final` fields can only be assigned inside a constructor (guide 04 covers the
  exact rule; `02a` uses the same fact for why the constructor bypass matters). An
  `Externalizable` value type cannot be immutable. That alone rules it out for `Money`,
  `StakeSplit`, `ClientId` and every other QuizStakes value type that is supposed to be immutable.
- **No superclass field handling.** The default protocol walks the class hierarchy from
  `Object` downward, one `writeObject`/`readObject` pair per class. `Externalizable` does not —
  your `readExternal` is on the hook for the superclass's state too, with no `defaultReadObject`
  to delegate to. Miss it, and the superclass silently keeps whatever its no-arg constructor set.
- **No field-set evolution for free.** The default protocol's `serialVersionUID` plus field
  descriptors let you add a field and have old streams reconcile safely (`02-serialization.md`).
  `Externalizable` has thrown that reconciliation away in exchange for compactness — you have
  hand-rolled a positional binary format, so adding a field without a version marker silently
  misaligns every read that follows it.
- **A public mutator on a value type.** `readExternal` must be `public`, so it is part of the
  type's API forever, not an implementation detail the JDK reaches into privately. Any caller can
  invoke `readExternal` on a live, already-constructed object and overwrite its state — a
  `PaymentRun` in flight can be rewritten by any code holding a reference to it.

Honest case *for* `Externalizable`, since it is not purely bad: it is the only serial form that
lets you write a genuinely compact positional encoding while staying inside `ObjectOutputStream`
— no per-class field descriptors, no field names on the wire, just the bytes you chose. That
matters at QuizStakes's ledger-entry volume (~19.8M/day, `02-serialization.md`'s numbers). The
escape hatch that makes even that not worth it: if you are hand-writing bytes anyway, write them
to a `DataOutputStream` or a real schema format (Avro, Protobuf) and skip `ObjectOutputStream`
entirely — no marker interface, no magic hooks, no `InvalidClassException` at 2 a.m. That
conclusion belongs to `02c`.

If you must use it — a `PaymentRun` batch header, genuinely mutable, genuinely bulk, with a
version byte so field evolution does not silently corrupt:

```java
public final class PaymentRunHeader implements Externalizable {

    private static final byte FORMAT_VERSION = 2;

    private String runId;
    private int itemCount;
    private long totalMinor;
    private String operatorSignOffId;   // added in FORMAT_VERSION 2

    public PaymentRunHeader() { }        // public no-arg, required by the contract

    public PaymentRunHeader(String runId, int itemCount, long totalMinor, String operatorSignOffId) {
        this.runId = runId;
        this.itemCount = itemCount;
        this.totalMinor = totalMinor;
        this.operatorSignOffId = operatorSignOffId;
    }

    @Override
    public void writeExternal(ObjectOutput out) throws IOException {
        out.writeByte(FORMAT_VERSION);
        out.writeUTF(runId);
        out.writeInt(itemCount);
        out.writeLong(totalMinor);
        out.writeUTF(operatorSignOffId == null ? "" : operatorSignOffId);
    }

    @Override
    public void readExternal(ObjectInput in) throws IOException {
        byte version = in.readByte();
        runId = in.readUTF();
        itemCount = in.readInt();
        totalMinor = in.readLong();
        if (version >= 2) {
            String signOff = in.readUTF();
            operatorSignOffId = signOff.isEmpty() ? null : signOff;
        } else {
            operatorSignOffId = null;   // field did not exist in version 1 streams
        }
    }
}
```

Every field the reader sees is public, mutable after construction, and hand-versioned by a single
`byte` the author must remember to bump. That is the whole cost surface `Externalizable` hides
behind "you write the bytes."

| Serial form | Creates the instance via | `final` fields possible | Validation runs | Superclass state handled | Field-set evolution | Public API surface added |
|---|---|---|---|---|---|---|
| `Serializable`, default protocol | allocation, no constructor (`02a`) | yes | no | yes, automatically | UID + field descriptors | none |
| `Serializable` + `writeObject`/`readObject` | allocation, no constructor (`02a`) | yes, but risky to trust before validation | only if you write it | yes, via `defaultReadObject` | UID + field descriptors, plus your logic | `private`, invisible outside the class |
| `Serializable` + serialization proxy | real constructor, via `readResolve` (`02a`) | yes | yes, in the proxy's `readResolve` | n/a — proxy owns the whole shape | you control the proxy's shape | `private` proxy class only |
| `Externalizable` | public no-arg constructor, then field-by-field overwrite | no | only what `readExternal` writes by hand | no — you own it entirely | none built in; you hand-roll a version byte | `public writeExternal`/`readExternal` |

**Insight:** `Externalizable` does not remove magic, it relocates it — from "the JDK secretly
bypasses your constructor" to "the JDK forces a constructor to exist that is guaranteed to be
useless, then bypasses *it* with a public setter." The bypass problem `02a` describes never went
away; `Externalizable` just makes the bypass method public.

**Gotcha:** the requirement is enforced only against the *runtime* class present at deserialization
time — if a later refactor removes the no-arg constructor because "nothing calls it," the compiler
agrees, and the break surfaces only when the next stream is read.

> `Externalizable` replaces the default field-by-field protocol with a hand-written one, at the
> cost of a mandatory public no-arg constructor, no `final` fields, and no automatic superclass or
> field-evolution handling.

## 2. Record serialization: components serialized and reconstructed through the canonical constructor (§2.10.9) `[RESEARCH]` `[X-REF 04]`

A record's serial form is not its fields — it is its **components**, in declaration order, matched
by name. And reconstruction on the way back is not field injection at all: it is a call to the
**canonical constructor** with the values read from the stream. That one substitution — a real
constructor call instead of `Unsafe.allocateInstance` plus reflection — is what makes record
serialization the one serial form in this whole tier that cannot be forged past validation.

### Why it exists

Records were finalized in Java 16 (JEP 395); their whole pitch is that the canonical constructor is
the single, unavoidable gate for constructing a valid instance — that is the entire value
proposition guide 04 covers for records as a language feature (`../records-and-sealed/01-basics.md`,
`../records-and-sealed/01a-object-methods-sealed-and-fit.md`). Serialization existed for fourteen
years before records did, built entirely around bypassing constructors (`02a`). If records had
inherited that behavior unchanged, every record's invariant would have been serialization-bypassable,
which would have made records strictly worse than the serialization proxy pattern they were
supposed to make unnecessary. The Java Object Serialization Specification therefore gives records a
dedicated serial form that routes through the canonical constructor instead of around it.

### How it works

Per the Java Object Serialization Specification's treatment of records: the serial form of a
record is derived from its record components. If a record declares `serialPersistentFields`,
`writeObject`, `readObject`, or `readObjectNoData`, those declarations are **ignored** — a record
cannot customize the write or read side the way an ordinary class can. `writeReplace` and
`readResolve`, by contrast, **are** honored if declared, since both operate on whole objects rather
than on field layout. Be precise about that split: ignored are the four field/stream-shape hooks;
honored are the two whole-object substitution hooks.

Deserialization reads the stream's field values, maps each to a record component **by name**, and
invokes the canonical constructor with those values. A stream field with no matching component is
discarded; a component the stream does not carry receives its type's default value (zero, `false`,
or `null`). That name-based, tolerant mapping is what makes adding a component a compatible change
and removing one a lossy-but-still-readable one — the opposite of the position-sensitive fragility
`Externalizable` has above.

Because the canonical constructor genuinely runs, its **compact constructor's validation runs
too**, and any exception it throws is wrapped. Measured:

```java
record Rec1(int bonusMinor, int cashMinor, int stakeMinor) implements Serializable {}

record Rec2(int bonusMinor, int cashMinor, int stakeMinor) implements Serializable {
    Rec2 {
        if (bonusMinor + cashMinor != stakeMinor)
            throw new IllegalArgumentException("split " + bonusMinor + "+" + cashMinor + " != " + stakeMinor);
    }
}
```

A stream written from `new Rec1(34, 300, 333)` — a forged split claiming a 0.34 bonus + 3.00 cash
against a 3.33 stake — read back as `Rec2` produced verbatim:

```
java.io.InvalidObjectException: split 34+300 != 333
   cause: java.lang.IllegalArgumentException: split 34+300 != 333
```

**The compact constructor ran.** A valid `new Rec2(33, 300, 333)` round-tripped cleanly to
`Rec2[bonusMinor=33, cashMinor=300, stakeMinor=333]`. Contrast, from the same harness: two ordinary
classes of identical shape, same forgery, gave `Split2[34+300=333]` with **no exception at all** —
the constructor was never called, because the default protocol allocates and injects fields (`02a`
owns that half of the measurement). This is the single most interesting fact in §2.10: the record
and the ordinary class look identical in source, and only one of them can protect its invariant on
the deserialization path.

A record with no declared `serialVersionUID` reports UID **0**, not a computed hash. Measured:
`ObjectStreamClass.lookup(Rec1.class).getSerialVersionUID()` returned `0`. `02-serialization.md`
measured the ordinary-class equivalent at `760042420889516798` for a comparably shaped class in the
same harness — a real SHA-1-derived value. Consequence: because reconciliation for a record is
already name-based rather than shape-hash-based, the strict `serialVersionUID` mismatch check that
protects ordinary classes is not the mechanism doing the work here. Declaring a UID on a record is
still worth doing if you want that stricter check as a second line of defense, but its absence is
not the same gap it would be on an ordinary class.

The catch, and it is real: **the canonical constructor is the only reconstruction hook a record
has.** There is no `readObject` to defensively copy into afterward. A component that is a mutable
array or mutable collection must be copied *inside* the canonical (or compact) constructor, or a
forged stream can hand the deserialized record an alias to internal state:

```java
public record PaymentRunLedger(RunId runId, List<Movement> movements) implements Serializable {
    public PaymentRunLedger {
        movements = List.copyOf(movements);   // protects the `new` path and the deserialization path identically
    }
}
```

That single line is the payoff of routing through a real constructor: it is not special
serialization-defense code, it is the same defensive copy `../objects-equality-and-lifecycle/02-copying-and-composite-equality.md`
already requires for the `new PaymentRunLedger(runId, movements)` path, and deserialization gets it for free
because it goes through the identical constructor.

Honest limits:

- A record cannot be `Externalizable` — it has no no-arg constructor to satisfy the requirement in
  §1, and its fields are `final`, which `readExternal`'s post-construction mutation model cannot
  honor.
- A record component typed `Optional<T>` is a problem, not a convenience. Measured:
  `java.io.Serializable.class.isAssignableFrom(Optional.class)` returned `false`;
  `Optional.class.getInterfaces()` returned `[]`. `Optional.empty() instanceof java.io.Serializable`
  does not even compile on JDK 21 — `javac` rejects it with `incompatible types: Optional<Object>
  cannot be converted to Serializable`. A serializable record with an `Optional` component fails
  whenever a value is actually serialized, not at declaration time.
- Component *names* are now part of the wire format. Renaming a component is a breaking rename in
  a way renaming a `private` field on an ordinary class never was, because the name is what the
  reconciliation in this section matches against.

**Interview:** "Can you bypass a record's invariant through serialization?" — no, because
deserialization reconstructs a record through its canonical constructor, so any validation in a
compact constructor runs exactly as it would for `new`; contrast this explicitly with an ordinary
class's default protocol, which never calls a constructor at all.

Design rule for QuizStakes: **if a value type must be serializable, make it a record.** You get
`02a`'s serialization-proxy guarantee — construction always goes through validated code — without
writing a proxy class, a `writeReplace`, or a `readResolve` by hand. See `02a` for the proxy this
makes unnecessary, and `../records-and-sealed/01a-object-methods-sealed-and-fit.md` for the
generated-member rules (`equals`, `hashCode`, `toString`, accessor naming) that come with choosing
a record in the first place. Version note: this behavior is part of the Java 16 finalization of
records (JEP 395); the two preview iterations (Java 14, 15) are worth naming only to flag that
material describing "records" from before Java 16 may predate this serial-form guarantee entirely.

> A record is serialized by its components and deserialized by invoking its canonical constructor
> with the stream's values matched by name, so compact-constructor validation runs on every
> deserialization exactly as it runs on every `new`.

## 3. Serializing a lambda: possible, fragile, and dependent on `invokedynamic` metadata (§2.10.14) `[TRAP]` `[RESEARCH]`

A lambda has no class you wrote. `javac` compiles a lambda expression to an `invokedynamic` call
site; the JVM's bootstrap machinery (`LambdaMetafactory`) spins an anonymous implementation class
the first time that call site executes, and that class's name embeds a runtime address. Serializing
"the lambda" cannot mean serializing that class, because there is no guarantee it exists, or has
the same name, the next time the JVM runs. What actually gets written to the stream is a *recipe*
for finding the target method again, plus the values the lambda captured. That recipe's type is
`java.lang.invoke.SerializedLambda`.

### Why it exists

Ordinary object serialization identifies a type by class name and relies on that class being
loadable identically at both ends. A lambda's synthesized class cannot serve that role — its name
is not stable across JVM runs, so writing it directly to a stream would make every serialized
lambda unreadable outside the exact process that created it. `SerializedLambda` exists to record
the durable coordinates instead: which class captured the lambda, which functional interface and
method it implements, and which compiler-generated method actually holds the body — so the
*target* can be re-resolved on read, even though the anonymous implementation class cannot be.

### How it works

The functional interface itself must extend `Serializable`, or the lambda assigned to it is not
serializable at all:

```java
interface SerRule extends Serializable {
    boolean test(int stakeMinor);
}

SerRule lam = stakeMinor -> stakeMinor <= 420;
```

The other way to get there is an intersection-type cast — `(Predicate<Integer> & Serializable) stakeMinor -> stakeMinor <= 420` —
useful when you do not control the functional interface's declaration.

`javac` emits a synthetic `private static Object $deserializeLambda$(SerializedLambda)` method on
the lambda's **capturing class** (`Javadoc, java.lang.invoke.SerializedLambda`), and the stream's
`readResolve` routes through that method to rebuild a working lambda instance. `SerializedLambda`
itself carries: the capturing class's name, the functional interface's name, the implemented
method's name and signature, the implementation method's kind/owner/name/signature, the
instantiated method type, and the captured argument values. Every one of those is a name matched by
string at read time — nothing in that list is a class reference the JVM can check structurally.

Measured, for `lam` above:

- The serialized stream was **504 bytes** — for a one-expression predicate with a single captured
  primitive comparison, effectively all of that is the recipe, not the payload.
- The stream **contained the text `SerializedLambda`**.
- Deserialization succeeded, and `back.test(420)` returned **`true`**.
- The deserialized object's runtime class was **`Ver5$$Lambda/0x0000007001164000`**; the original
  lambda's runtime class was **`Ver5$$Lambda/0x000000700115abf0`**. Different classes — the
  implementation class is re-synthesized fresh on the reading side by `LambdaMetafactory`, its name
  embedding a fresh runtime address, so it cannot be and is not the same class as the one that wrote
  the stream. The round trip works despite that, because equality of the *implementation class* was
  never the contract — only re-resolution of the *target method* was.

**Pitfall:** the implementation method backing a lambda body is a synthetic method the compiler
names, typically `lambda$<enclosingMethodName>$<ordinal>` — an auto-incrementing ordinal per
enclosing method, not a stable identifier the source names. Add a second lambda earlier in the same
enclosing method, or reorder two existing lambdas, and `lambda$grantBonus$0` now points at a
different method body than the one that existed when the stream was written. The stream still
deserializes without error. It calls the wrong code. Silently — no exception, no log line, just the
wrong behavior running under a plausible-looking predicate name.

Further fragility, each a distinct failure mode:

- Refactoring the lambda into a method reference, inlining it, or extracting the enclosing method
  into a different method removes the synthetic `lambda$grantBonus$0`-shaped method entirely, producing
  `IllegalArgumentException` or `NoSuchMethodError`-class failures at read time, not at write time.
- A different compiler build can choose different synthetic names for the same source, even with no
  source change at all.
- The capturing class must be loadable and structurally identical on the reading side, since the
  recipe names it explicitly — a serialized lambda is coupled to a specific build of a specific
  class, not to an interface contract.
- Captured values are serialized along with the recipe, so a lambda that captures `this` drags the
  entire enclosing object into the stream — the same accidental-reachability failure
  `02-serialization.md`'s object-graph walk produces, and the same capture shape as the `Cleaner`
  trap in `../objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`, where a
  lambda passed to `Cleaner.register` must not capture the object being cleaned.

QuizStakes framing: a `BonusService` persists a serialized eligibility predicate against each
`Bonus` row, alongside its 30-day expiry (`../numbers-and-money/02-numbers-and-money.md` for the
bonus rules; the exact numbers are the domain's own). At 3.1k bonus grants/day, a 30-day live
window holds roughly 93,000 rows at any time. Deploy twice inside that window — entirely routine —
and every row whose `lambda$grantBonus$N` ordinal shifted now holds a code pointer into a build
that no longer exists on any running instance. The failure is not a crash; it is either a read-time
`NoSuchMethodError` during a bonus-consumption check, or worse, a silently different predicate than
the one that was actually approved for that client.

**Wrong**

```java
Bonus bonus = new Bonus(bonusId, stakeMinor -> stakeMinor <= 420);  // captured, serialized, stored
byte[] persisted = serialize(bonus.eligibilityRule());
// two deploys later, the enclosing method gained an earlier lambda: grantBonus() now declares
// a logging predicate above this one, shifting this lambda from ordinal 0 to ordinal 1
SerRule restored = (SerRule) deserialize(persisted);
restored.test(420);   // no exception — but may now invoke a different lambda body than intended
```

**Right**

```java
enum BonusEligibilityRule implements SerRule {
    FIRST_DEPOSIT_CAP_420 { public boolean test(int stakeMinor) { return stakeMinor <= 420; } };
}

Bonus bonus = new Bonus(bonusId, BonusEligibilityRule.FIRST_DEPOSIT_CAP_420);
byte[] persisted = serialize(bonus.eligibilityRule());   // serial form is the enum NAME, not a code pointer
BonusEligibilityRule restored = (BonusEligibilityRule) deserialize(persisted);
```

**Why people believe it:** the round trip visibly works in a quick local test — same JVM run, same
build, one lambda in the method — so the fragility never shows up until a real deploy happens
between the write and the read, which is exactly the gap a unit test does not exercise.

The rule: never persist a serialized lambda across a build boundary, and never send one over a wire
between two independently deployed services. The one legitimate use is single-JVM, single-build,
in-memory — and even there, a named method reference to a stable `public` method is safer than an
inline lambda, because a method reference's identity is the method's declared signature, not an
auto-numbered synthetic name. The enum-based replacement above ties back to `02a`'s conclusion that
enum constants are the one type the serialization protocol treats as identity-preserving rather
than state-preserving — the enum's serial form is its `name()`, a stable string, never a code
pointer (`../enums/03d-internals-enum-evolution.md` covers the bytecode side of why that holds
across evolution). A sealed interface with record implementations is the equivalent shape when the
rule needs per-branch data rather than a fixed enumeration.

Version note: serializable lambdas have worked this way since lambdas and `invokedynamic` shipped
in Java 8; nothing about the mechanism changed by 21. What did change is the surrounding
recommendation — `../language-substrate/04a-internals-version-history-18-onward.md` covers the
broader move away from relying on Java serialization at all, and `02c` closes this tier with that
argument made explicit as the practical rule.

**Insight:** the two different address-suffixed `Ver5$$Lambda` class names measured for the same
source lambda are not a bug in the measurement — they are the proof that `SerializedLambda` never
depended on class identity in the first place. If it had, the round trip above could not have
worked at all.

> Serializing a lambda writes a `SerializedLambda` recipe naming the capturing class, the target
> method, and the captured values, not the lambda's synthesized class, and that recipe is only as
> stable as the compiler-generated method name it depends on.

---

## Pitfalls

### `Externalizable` gives you `final` fields for free because you control the constructor

**Wrong**

```java
static class ExtStake implements Externalizable {
    final int stakeMinor;   // will not compile as written below
    public ExtStake() { this.stakeMinor = 0; }
    public void readExternal(ObjectInput in) throws IOException {
        // cannot assign `stakeMinor` here — it is not the constructor
    }
    public void writeExternal(ObjectOutput out) throws IOException { out.writeInt(stakeMinor); }
}
```

**Right**

```java
static final class ExtStake implements Externalizable {
    private int stakeMinor;             // mutable — the honest cost of Externalizable
    public ExtStake() { }
    public void readExternal(ObjectInput in) throws IOException { stakeMinor = in.readInt(); }
    public void writeExternal(ObjectOutput out) throws IOException { out.writeInt(stakeMinor); }
    // for real immutability, use a record instead — see §2
}
```

**Why people believe it:** `writeExternal`/`readExternal` look like ordinary object lifecycle
methods, and it is easy to assume "I wrote the constructor, so I control everything the constructor
controls" — when in fact `readExternal` runs strictly *after* construction, on a mutable object,
so `final` is off the table for anything it needs to set.

### A record's `serialVersionUID` protects it the same way an ordinary class's does

**Wrong**

```java
record Rec1(int bonusMinor, int cashMinor, int stakeMinor) implements Serializable { }
// assuming ObjectStreamClass.lookup(Rec1.class).getSerialVersionUID() is a computed shape hash
```

**Right**

```java
record Rec1(int bonusMinor, int cashMinor, int stakeMinor) implements Serializable {
    private static final long serialVersionUID = 1L;   // declare it if you want the strict check
}
// undeclared, ObjectStreamClass.lookup(Rec1.class).getSerialVersionUID() measured as 0 on JDK 21.0.7,
// because record reconciliation is name-based, not shape-hash-based, regardless of the UID
```

**Why people believe it:** `02-serialization.md` teaches that an undeclared `serialVersionUID` on
an ordinary class computes a SHA-1-derived hash from the class shape, and it is natural to assume
records inherit that same computation — but the measured value for a record with no declared UID
is `0`, not a computed hash, because reconciliation for records already happens by component name.

### Serializing a lambda twice in the same running process always calls the same code

**Wrong**

```java
BonusService.persistRule(bonusId, (SerRule) stakeMinor -> stakeMinor <= 420);
// redeploy the service: grantBonus() now declares an earlier lambda above this one, shifting
// this lambda's synthetic name from lambda$grantBonus$0 to lambda$grantBonus$1
SerRule restored = BonusService.loadRule(bonusId);
restored.test(420);   // silently resolves lambda$grantBonus$1, not lambda$grantBonus$0 — wrong body, no exception
```

**Right**

```java
enum BonusEligibilityRule implements SerRule {
    FIRST_DEPOSIT_CAP_420 { public boolean test(int stakeMinor) { return stakeMinor <= 420; } };
}
BonusService.persistRule(bonusId, BonusEligibilityRule.FIRST_DEPOSIT_CAP_420);
// serial form is the constant NAME — stable across redeploys, ordinal shifts, and recompiles
```

**Why people believe it:** the failure mode is invisible in development, where the write and the
read happen in the same JVM run with no code changes in between — the ordinal-shift problem
requires a real deploy boundary to surface, which most local testing never crosses.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Externalizable` constructor | must be `public` and no-arg; enforced at deserialization time via `InvalidClassException`, not at compile time |
| `Externalizable` and `final` | incompatible — `readExternal` runs after construction and cannot assign `final` fields |
| `Externalizable` superclass handling | none automatic — `readExternal` must handle it, unlike the default protocol's per-class walk |
| Record serial form | the record's components, by name, not its raw fields |
| Record deserialization | invokes the **canonical constructor** with stream values — validation in a compact constructor runs |
| Record hooks ignored | `serialPersistentFields`, `writeObject`, `readObject`, `readObjectNoData` |
| Record hooks honored | `writeReplace`, `readResolve` |
| Record `serialVersionUID`, undeclared | measured `0`, not a computed shape hash |
| Record + `Optional` component | fails — `Optional` does not implement `Serializable` (`isAssignableFrom` measured `false`) |
| Record defensive copy | must happen in the canonical/compact constructor — no `readObject` hook exists on a record |
| Lambda serializability | requires the functional interface to extend `Serializable`, or an intersection-type cast |
| Lambda serial form | `java.lang.invoke.SerializedLambda` — a recipe (class, method, captured args), not the lambda's class |
| Lambda deserialize hook | synthetic `$deserializeLambda$(SerializedLambda)` on the capturing class, called via `readResolve` |
| Lambda implementation method name | compiler-synthesized `lambda$<method>$<ordinal>` — shifts if lambdas are added/reordered/removed |
| Lambda class identity across a round trip | not preserved — measured two distinct address-suffixed runtime classes for one source lambda |
| Safe persisted "lambda" | an enum constant or sealed-interface record implementing the functional interface, never an inline lambda |

## Self-test

**Q1.** Why does `Externalizable` require a public no-arg constructor, and what happens if the class does not have one?

<details><summary>Answer</summary>

Deserialization of an `Externalizable` type allocates the instance by calling its public no-arg
constructor, then calls `readExternal` on that instance to fill in the fields — there is no
`Unsafe`-style allocation-without-construction as there is for the default protocol. If no public
no-arg constructor exists, deserialization fails at read time with `InvalidClassException: <class>;
no valid constructor` — measured verbatim on JDK 21.0.7 — not at compile time, since the compiler
has no way to know a class will later be deserialized.

</details>

**Q2.** Why can an `Externalizable` type not have `final` fields, in practice?

<details><summary>Answer</summary>

`final` fields can only be assigned inside a constructor. `Externalizable` deserialization
constructs the object with the public no-arg constructor — which by definition cannot know the
field values yet — and then assigns fields afterward, inside `readExternal`, which is an ordinary
method, not a constructor. Any field `readExternal` needs to set therefore cannot be `final`.

</details>

**Q3.** What actually gets serialized for a record, and what gets called on the way back?

<details><summary>Answer</summary>

A record's serial form is its components, in declaration order, matched by name on the wire — not
its raw fields as the default protocol would treat them. Deserialization reads the stream's values
and invokes the record's canonical constructor with them, rather than allocating the object and
injecting fields by reflection. That is a real constructor call, so any validation the compact
constructor performs executes on deserialization exactly as it would on `new`.

</details>

**Q4.** Which serialization hooks does a record's declaration of `writeObject`/`readObject` affect, and which does `writeReplace`/`readResolve` affect?

<details><summary>Answer</summary>

A record's `serialPersistentFields`, `writeObject`, `readObject`, and `readObjectNoData` are
ignored by the serialization runtime even if declared — a record cannot customize its field-level
read/write shape the way an ordinary class can. `writeReplace` and `readResolve` are honored if
declared, because they operate on whole-object substitution rather than on field layout, and that
mechanism is orthogonal to how components are read and mapped to the constructor.

</details>

**Q5.** A stream written from `new Rec1(34, 300, 333)` is read back as `Rec2`, whose compact constructor requires `bonusMinor + cashMinor == stakeMinor`. What happens, and what is the equivalent behavior for two ordinary classes of the same shape?

<details><summary>Answer</summary>

Reading the forged stream as `Rec2` invokes `Rec2`'s canonical constructor with the mismatched
values, the compact constructor's `if` check fails, and deserialization throws
`java.io.InvalidObjectException: split 34+300 != 333` wrapping the original
`IllegalArgumentException` — measured verbatim on JDK 21.0.7. For two ordinary classes of identical
shape and the same forged split, the measured result was `Split2[34+300=333]` with no exception at
all, because the default protocol allocates the object and injects fields directly, never calling
any constructor, so no validation logic anywhere in the class runs.

</details>

**Q6.** Why is defensive copying of a mutable record component only safe if it happens inside the canonical or compact constructor?

<details><summary>Answer</summary>

A record has no `readObject` hook to run extra logic after field injection, because there is no
field injection — the only code path that ever produces a record instance, whether via `new` or via
deserialization, is the canonical constructor. Placing the defensive copy (for example,
`movements = List.copyOf(movements)`) inside that constructor protects both paths identically with
one line; placing it anywhere else (a factory method, a caller-side copy) leaves the deserialization
path unprotected, since deserialization never goes through that other code.

</details>

**Q7.** What is actually written to the stream when a lambda is serialized, and why can it not be the lambda's own class?

<details><summary>Answer</summary>

The stream holds a `java.lang.invoke.SerializedLambda`, which records the capturing class name, the
functional interface and method being implemented, the implementation method's owner/name/signature,
and the captured argument values — a recipe for re-resolving the target method, not a class
reference. It cannot be the lambda's own class because that class is synthesized at runtime by
`LambdaMetafactory` the first time the `invokedynamic` call site executes, and its name embeds a
runtime address that has no guarantee of matching between the writing run and any later reading run
— measured as two different runtime class names (`Lambda/0x0000007001164000` versus
`Lambda/0x000000700115abf0`) for the same source lambda across one round trip.

</details>

**Q8.** Why can adding or reordering lambdas in a method silently break a previously serialized lambda from that same method, with no exception at read time?

<details><summary>Answer</summary>

The implementation method backing a lambda's body is a compiler-synthesized method named
`lambda$<enclosingMethod>$<ordinal>`, where the ordinal is assigned per lambda in declaration order
within the enclosing method. `SerializedLambda` records that name as part of its recipe. If a new
lambda is added earlier in the same method, or two lambdas are reordered, the ordinals shift, so the
name stored in an old stream now resolves to a different method body than the one that existed when
the stream was written. Deserialization does not fail, because the name still resolves to *some*
valid synthetic method — it just resolves to the wrong one, producing wrong behavior with no error.

</details>

**Q9.** Why does the practical rule say never to persist a serialized lambda, and what should replace it for something like a `BonusService` eligibility rule stored against a 30-day-lived `Bonus` row?

<details><summary>Answer</summary>

A persisted serialized lambda is coupled to the exact compiler-generated method name active at
write time, and any redeploy between write and read — routine at QuizStakes's scale, with roughly
93,000 live `Bonus` rows in a 30-day window at 3.1k grants/day — can shift or remove that name,
causing either a read-time failure or, worse, silent execution of the wrong logic. The replacement
is an enum constant (or a sealed interface with record implementations) implementing the same
functional interface: its serial form is a stable name (`name()` for an enum), not a compiler-
generated code pointer, so it survives recompiles, reorderings, and redeploys unchanged.

</details>

## Open questions

None.

---

**Leaves covered:** 2.10.8, 2.10.9, 2.10.14 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 696
