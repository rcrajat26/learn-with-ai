# 03 Java Core — Serialization: the default protocol, `serialVersionUID` and compatibility — INTERMEDIATE (§2.10, 2.10.1–2.10.3, 2.10.13)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Precision, scale and legacy bridging](../date-and-time/03c-internals-precision-scale-and-legacy-bridging.md) · Next: [The magic methods and the constructor bypass](02a-magic-methods-and-constructor-bypass.md)

This file is the landing page for the whole `serialization/` folder, so read it as a map before you read it as content. **This file** owns the `Serializable` marker interface, what "the object graph" means for the default protocol, `serialVersionUID` (what it is, how it is computed, how it breaks), `transient` and `static` field handling, and the compatibility rules that decide whether a class change breaks an existing stream. [02a-magic-methods-and-constructor-bypass.md](02a-magic-methods-and-constructor-bypass.md) owns the hook methods — `writeObject`, `readObject`, `readObjectNoData`, `writeReplace`, `readResolve` — the constructor-bypass mechanism, the serialization proxy pattern, and singleton/enum `readResolve`. [02b-externalizable-records-and-lambdas.md](02b-externalizable-records-and-lambdas.md) owns `Externalizable`, how records serialize differently from ordinary classes, and lambda serialization. [02c-attack-surface-filters-and-the-practical-rule.md](02c-attack-surface-filters-and-the-practical-rule.md) owns deserialization as a remote-code-execution class of bug, JEP 290 filters, and the practical "should you even use this" rule. **The question this file answers: when the JVM writes an object to a stream and reads it back on possibly-different code, what exactly gets written, what gets skipped, and what has to match for the read to succeed?**

## 1. `Serializable` as a marker; the whole reachable graph (2.10.1)

`Serializable` is not an API. It adds no method you must implement, no field you must set. It is a permission slip: implementing it tells `ObjectOutputStream` "you may reach into my private fields with reflective, `Unsafe`-level access and write them to a byte stream, without going through my constructor or any accessor." Nothing in the class body changes. Everything about how the class is treated changes.

### Why it exists

Java needed a way to turn an arbitrary object graph into bytes without every class author hand-writing a `toBytes`/`fromBytes` pair. The marker-interface design (`Serializable` has zero members) lets the JVM's reflection machinery do the walking generically: given permission, it inspects the class's declared fields via `ObjectStreamClass`, and writes each one whose modifiers are not `transient` and not `static`. No method call is required from the class, which is also why the mechanism can bypass your invariants entirely — there is no method of yours in the loop to enforce them. That gap is exactly what `writeObject`/`readObject` in [02a](02a-magic-methods-and-constructor-bypass.md) exist to close.

### How it works

The default protocol is **transitive** over every non-transient, non-static field that is itself a reference type. Serialize a `LedgerEntry` and the stream does not stop at `LedgerEntry`'s own fields — if `LedgerEntry` holds a `Movement`, and `Movement` holds a `Position`, and `Position` holds a reference to a `ClientRestrictions` service object, the writer walks all of it. The first class in that chain that is not `Serializable` throws `NotSerializableException` naming that exact class, not the root object. This is the single most common integration failure with the default protocol: someone marks the aggregate `Serializable` without checking every field's type, transitively.

| Reachability fact | Consequence |
|---|---|
| Reference fields are followed by default | Marking one class `Serializable` obligates every reachable non-transient field's type too |
| Cycles are handled via handles | `ObjectOutputStream` tracks already-written objects by identity and writes a back-reference, so an `Account` that points back to a `Reservation` that points back to the `Account` does not loop forever and does not duplicate data |
| The exception names the leaf, not the root | `NotSerializableException: ClientRestrictions`, not `NotSerializableException: LedgerEntry` |
| Accidental reachability is a real bug class | A `Reservation` that happens to hold an `Executor` or a `Connection` field breaks serializability for everything that references it, even if nobody ever meant to serialize the `Executor` |

```java
class Position implements Serializable {
    RoundId roundId;
    Money amount;
    ClientRestrictions restrictions; // not Serializable — this is the leak
}

class Movement implements Serializable {
    Position position;
    Instant recordedAt;
}

class LedgerEntry implements Serializable {
    Movement movement;
    LedgerPositionType position;
}

// new ObjectOutputStream(out).writeObject(ledgerEntry);
// throws: java.io.NotSerializableException: ClientRestrictions
```

The write cost of the default protocol is proportional to the whole reachable graph, not to the single object you called `writeObject` on — serializing a `LedgerEntry` with a live `Movement`/`Position` chain walks and writes all of it, **but** the escape hatch is twofold: mark the fields you do not want walked `transient` and reconstruct them on read (see Concept 3 and [02a](02a-magic-methods-and-constructor-bypass.md)'s `writeReplace`), or do not use Java's built-in serialization for that boundary at all — [02c](02c-attack-surface-filters-and-the-practical-rule.md) makes the case for the latter on security grounds, and guide 12 (API design) makes it on wire-format-stability grounds.

**Insight:** the marker interface pattern means the compiler cannot stop you from marking a class `Serializable` whose fields are not; the failure only surfaces at first serialization attempt, at runtime, potentially in production the day someone adds a new field.

**Interview:** "What does implementing `Serializable` actually do?" — nothing to the class itself; it authorizes `ObjectOutputStream`/`ObjectInputStream` to use reflective access on the class's declared instance fields, and the default protocol then walks the object graph transitively through every non-transient, non-static reference field.

> `Serializable` is a zero-method marker interface that authorizes the default protocol to reflectively read and write a class's non-transient, non-static instance fields, and that protocol follows every such reference field transitively across the whole reachable object graph.

## 2. `serialVersionUID`: generation, breakage and `InvalidClassException` (2.10.2) [TRAP] [NUM]

The UID is a fingerprint of a class's *shape* — not its behavior, its shape: name, modifiers, interfaces, fields, constructors, methods. If you do not declare one, the compiler and JVM compute it for you at class-load time from that shape, and if the shape changes even by adding one field, the computed value changes completely. Every object of the old shape sitting in a file, a cache, or a message queue becomes unreadable the moment you deploy the new shape, because the reader compares its own freshly-computed UID against the one baked into the stream and refuses to proceed on any mismatch.

### Why it exists

Without a UID, `ObjectInputStream` would have no cheap way to detect "the class on disk and the class in memory disagree about fields" before attempting a field-by-field reconciliation that could silently corrupt data (wrong type read into wrong slot). The UID is a fast, coarse compatibility gate that runs before the expensive field reconciliation ever starts.

### How it works

**Pitfall:** the belief is "if I don't declare `serialVersionUID`, Java just picks a sensible default and nothing changes." What actually happens is the JVM computes an 8-byte digest of the class's shape and bakes it into every stream you write — so an entirely unrelated change (adding a field for a new feature) silently invalidates every object already serialized under the old shape, and the failure only appears months later when someone tries to read old data.

The Java Object Serialization Specification, §4.6 "Stream Unique Identifiers," defines the computed value as **the first 8 bytes of the SHA-1 digest of a canonically-ordered description of the class** — the class name, its modifiers, the names of interfaces it implements (sorted), each non-transient non-static field with its modifiers and field descriptor (sorted by name), the `<clinit>` method if the class has static initializers, and each constructor and non-private method with its modifiers, name, and descriptor. That digest is computed once, at class-load time, unless you supply your own value.

Measured on Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64: for a nested class `Ver3.NoUid` declared as

```java
static class NoUid implements Serializable {
    int stakeMinor; String clientId;
    NoUid(int s, String c) { stakeMinor = s; clientId = c; }
}
```

`ObjectStreamClass.lookup(NoUid.class).getSerialVersionUID()` returned **760042420889516798**. Adding exactly one field and nothing else —

```java
static class NoUidV2 implements Serializable {
    int stakeMinor; String clientId; long roundId;
}
```

— returned **2193869912748673154**, a completely different value. Both declarations were nested inside a harness class `Ver3`, so the digest input included the binary name `Ver3$NoUid`; the specific digits are an artifact of that harness, but the point holds generally: one added field, one unrelated-looking change, a totally different UID, with nothing in the diff that looks like a version bump.

The consequence when two builds disagree: a class `Led implements Serializable` compiled twice, identical fields, `serialVersionUID = 1L` on the writing side and `2L` on the reading side, produced verbatim:

```
java.io.InvalidClassException: Led; local class incompatible: stream classdesc serialVersionUID = 1, local class serialVersionUID = 2
```

That check happens **after** class resolution, not before: byte-editing the class name inside a serialized stream from `Ver3$NoUid` to `Ver3XNoUid` produced a different failure entirely:

```
java.lang.ClassNotFoundException: Ver3XNoUid
```

So the resolution order is name first, UID second — if the class cannot even be found, you never get as far as an `InvalidClassException`.

The recommended declaration form is `private static final long serialVersionUID = 1L;` — `private` because the field is deliberately **not** part of the class's public contract, is not inherited, and must not be confused with a superclass's own UID (each `Serializable` class in a hierarchy carries its own, independent value). Declaring it explicitly is the single change that removes the shape-sensitivity: the value stops depending on the compiler's exact output and starts depending only on what you typed.

Version trap: the SHA-1 digest algorithm itself has been stable since serialization's introduction in JDK 1.1, but its **input** is not stable across compilers or compiler flags — a synthetic accessor method, a bridge method inserted for generics, or a renamed nested class (the `Ver3$NoUid` binary name above) all change the digest input, and therefore the UID, even when your source code is byte-for-byte identical. This is why relying on the computed default is fragile in a way that has nothing to do with the fields you think you changed.

Records get a different rule entirely: a record with no declared `serialVersionUID` measured **0**, not a computed hash — `ObjectStreamClass.lookup(SomeRecord.class).getSerialVersionUID()` returned **0**. The Java Object Serialization Specification's record-serialization rules make `0L` the default for records specifically, and stream UID matching is not required for records the way it is for ordinary classes. [02b](02b-externalizable-records-and-lambdas.md) owns the full record serial-form treatment.

```java
class Led implements Serializable {
    private static final long serialVersionUID = 1L; // pin the shape fingerprint
    int stakeMinor;
    String clientId;
}
```

**Gotcha:** two classes in an inheritance chain each need their own `serialVersionUID` — a subclass does not inherit its superclass's value, and omitting it on the subclass exposes the subclass to the same shape-sensitivity independently.

> `serialVersionUID` is an 8-byte SHA-1-derived fingerprint of a class's shape, computed automatically from field/method/constructor descriptors when not declared explicitly, and compared exactly at read time — any mismatch raises `InvalidClassException` regardless of whether the field values themselves would have been readable.

## 3. `transient`, `static`, and what the default protocol skips (2.10.3)

The stream is a snapshot of *instance state the class admits to* — nothing more. Three categories never appear in it: `static` fields (they belong to the class, not any instance, so there is nothing per-object to snapshot), `transient` fields (you have explicitly opted the field out), and anything that is not a declared field at all (a value computed in a getter, a cache built lazily). What trips people up is not the list — it is what a `transient` field looks like after it comes back.

### Why it exists

Some fields genuinely should not travel: a live `PaymentService` client handle, a `Clock` bound to the machine that created the object, a cached `BigDecimal` total that can be recomputed, or — for QuizStakes specifically — a PSP token that must never touch disk in a serialized ledger snapshot. `transient` is the field-level way to say "this belongs to the runtime instance, not to the durable representation of it."

### How it works

**Pitfall:** the belief is "a `transient` field keeps whatever value my field initializer or constructor gave it, since deserialization is basically like calling `new`." What actually happens is deserialization never runs field initializers or the constructor body — the type default is what a `transient` field gets, always, because `ObjectInputStream` allocates the object without running any of your code, using a synthetic no-arg-constructor-like path.

Measured: for

```java
class Trans implements Serializable {
    private static final long serialVersionUID = 1L;
    int stakeMinor = 420;
    transient String pspToken = "tok-secret";
    static int shared = 99;
}
```

setting `shared = 7`, serializing an instance, then setting `shared = 99` and deserializing yielded `Trans[stakeMinor=420, pspToken=null, shared=99]`. `pspToken` came back `null` — the type default for a reference field — not `"tok-secret"`, because the field initializer never ran. `shared` was never written to the stream at all — it reflects whatever the *class* holds at read time, independent of what it held when the object was written. `ObjectStreamClass.lookup(Trans.class).getFields()` returned exactly one entry, `[I stakeMinor]` — the field descriptor form `I stakeMinor` means "an `int` named `stakeMinor`"; `pspToken` and `shared` are absent from the serial form entirely, not present-but-null.

| Field kind | In the stream? | What the reader sees |
|---|---|---|
| ordinary instance field | yes | the written value |
| `transient` instance field | no | the type default (`null`, `0`, `false`) — never the initializer's value |
| `static` field | no | whatever the *class* currently holds, unrelated to the writer |

The right fix for a `transient` field that must be reconstructed is `readObject` calling `defaultReadObject()` for the ordinary fields and then rebuilding the transient one from context — for example re-resolving a `PaymentService` handle from a registry rather than deserializing it — or, more robustly, the serialization proxy pattern, both of which [02a](02a-magic-methods-and-constructor-bypass.md) covers mechanically.

```java
class Trans implements Serializable {
    private static final long serialVersionUID = 1L;
    int stakeMinor = 420;
    transient String pspToken = "tok-secret";
    static int shared = 99;
}
```

An explicit alternative to letting field declarations dictate the serial form is `serialPersistentFields`:

```java
class Position implements Serializable {
    private static final long serialVersionUID = 1L;
    // serialize only these two, regardless of what other instance fields exist
    private static final ObjectStreamField[] serialPersistentFields = {
        new ObjectStreamField("roundId", RoundId.class),
        new ObjectStreamField("amount", Money.class)
    };
    RoundId roundId;
    Money amount;
    transient ClientRestrictions restrictions;
}
```

This decouples "what fields exist on the class" from "what fields are in the serial form" without relying on every field author remembering to write `transient` correctly — useful once a class has enough fields that the serial form needs to be a deliberate, reviewed contract rather than an accident of field declaration order.

`final transient` is its own trap: a `final` field can only be assigned once, at construction, so `readObject` — which runs after the object already exists — cannot assign it. You are stuck either dropping `final`, using reflection to force the assignment (fragile, and blocked or warned under module strong encapsulation — see [../language-substrate/02-packages-modules-annotations.md](../language-substrate/02-packages-modules-annotations.md)), or switching to the serialization proxy pattern, which builds a genuinely new object through its real constructor and sidesteps the problem entirely. [02a](02a-magic-methods-and-constructor-bypass.md) has the proxy mechanics.

For contrast, `Throwable` — which every checked and unchecked exception extends — declares its `backtrace` field `transient` (the raw stack-walking state cannot and should not survive serialization) while its `stackTrace` array field is not transient (the printable frames are captured once via `fillInStackTrace` and do travel with the exception). [../exceptions/01a-throwable-api-and-chaining.md](../exceptions/01a-throwable-api-and-chaining.md) owns that split in full; it is worth holding in mind here as a real, load-bearing example of exactly this design decision made by the JDK itself.

**Insight:** "not serialized" and "serialized as null/zero" look identical from the outside if you only look at the final field value — the difference only shows up when you inspect `ObjectStreamClass.getFields()` and see the field is simply absent from the serial form, versus present with a default value.

**Interview:** "What happens to a `transient` field across serialization?" — it is skipped entirely on write and comes back as its type's default value on read, because deserialization never invokes field initializers or constructors.

> `transient` and `static` fields are excluded from the default serial form entirely — a `transient` field returns from deserialization at its type's default value rather than any initializer-assigned value, because the reader never re-runs initializer or constructor code.

## 4. Serialization compatibility rules (2.10.13)

Whether a class change is safe to deploy against streams already written under the old shape splits into two independent questions: does the UID still match, and — if it does — can the reader reconcile the field set it finds against the field set it declares. The UID answers the first question in one comparison; the second is resolved name-by-name, field-by-field, at read time.

### Why it exists

A durable stream (a file, a Kafka record, a cache entry) can easily outlive the code that wrote it. QuizStakes writes roughly 19.8M ledger entries a day with a 7-year retention requirement — any `LedgerEntry` serialized today may need to be read by code deployed years from now. The compatibility rules are the contract that determines which of those future code changes are safe and which corrupt or lose data.

### How it works

| Change | Compatible? | What actually happens |
|---|---|---|
| Add a non-transient field | Compatible | reader finds no value in the stream for it; field is left at its type default (`readObjectNoData` exists for exactly this case — see [02a](02a-magic-methods-and-constructor-bypass.md)) |
| Remove a field | Reads without error, semantically lossy | the stream's value for that field is present but silently discarded; nothing on the reader receives it |
| Change a field's declared type | **Incompatible** | `InvalidClassException` |
| Rename a field | Incompatible in effect | treated as removing the old name and adding the new one — old data is lost, not migrated |
| Change primitive ↔ wrapper for a field | Incompatible | this is a type change, same as above |
| Change a field from `static`/`transient` to an ordinary instance field | Adds a field to the serial form | equivalent to the "add a field" row |
| Change a field to `transient` | Removes it from the serial form | equivalent to the "remove a field" row |
| Add a class to the type hierarchy | Compatible | the reader supplies the new superclass's state via `readObjectNoData` since the stream predates it |
| Remove a class from the type hierarchy | Incompatible | |
| Change the declared `serialVersionUID` | Incompatible by construction | this is the mechanism, not an accident |
| Switch `Serializable` ↔ `Externalizable` | Incompatible | the stream formats differ entirely — see [02b](02b-externalizable-records-and-lambdas.md) |
| Change a class to/from an enum, or to/from a record | Incompatible | each has its own, incompatible serial form |
| Add/remove/change `writeObject`/`readObject` | Compatible at the stream-format level | the field set and UID are unaffected, but the *semantics* of what gets written or reconstructed can change |
| Change a field's access modifier (`private`/`protected`/`public`) | Compatible | access modifiers do not affect the serial form |
| Change a method's implementation body | Compatible | the UID digest includes method *signatures*, not bodies, and the reader only checks the UID and the field set |

The rows for adding/removing a field, adding/removing a class in the hierarchy, `readObjectNoData`'s role, type changes causing `InvalidClassException`, and UID changes being incompatible by construction are asserted directly from the Java Object Serialization Specification, Chapter 5, "Versioning of Serializable Objects" (its "Compatible Changes" and "Incompatible Changes" enumerations). The `Serializable`/`Externalizable` switch, the enum/record switch, and the method-body-is-compatible row follow from the same chapter's description of what the UID digest covers (method signatures, not implementations) combined with each type's distinct serial-form rules covered in [02b](02b-externalizable-records-and-lambdas.md). The renamed-field and access-modifier rows are direct consequences of the name-based field matching the specification describes, rather than separately-stated spec text, and are recorded here as reasoned consequences rather than verbatim quotes.

**Insight:** "compatible" in this table means *the read does not throw* — it does not mean *no data was lost*. Removing a field is compatible by that definition and still silently discards whatever was in the stream for it; treating "compiles and reads without exception" as "safe" is the trap the whole table exists to prevent.

**Interview:** "Can you add a field to a class and still read old serialized data?" — yes, that is the textbook compatible change: the reader leaves the new field at its type default because the old stream never wrote it, and `readObjectNoData` is the hook for classes that need to detect and handle that case explicitly.

At QuizStakes' actual scale — 19.8M ledger entries a day, ~7.2B a year, 7-year retention — a `LedgerEntry` written with the default `Serializable` protocol today is a schema you are contractually married to for seven years of future code changes, evaluated row-by-row against exactly this table. [02c](02c-attack-surface-filters-and-the-practical-rule.md) uses that constraint, together with the security case, to make the argument for not using the built-in protocol for durable storage at all.

> Compatibility is decided in two independent passes — an exact `serialVersionUID` equality check, then a name-based field reconciliation where added fields default silently and removed fields' stream values are discarded — and only type changes, renames, UID changes, and hierarchy/kind changes (enum, record, `Externalizable`) actually throw.

## Pitfalls

### A `transient` field keeps its field-initializer value across a round trip

**Wrong**

```java
class Trans implements Serializable {
    private static final long serialVersionUID = 1L;
    transient String pspToken = "tok-secret";
}

// byte[] bytes = serialize(new Trans());
// Trans back = deserialize(bytes);
// back.pspToken  ->  null, not "tok-secret"
```

**Right**

```java
class Trans implements Serializable {
    private static final long serialVersionUID = 1L;
    private transient String pspToken;

    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
        in.defaultReadObject();
        this.pspToken = PaymentService.currentToken(); // rebuild from live context, not the stream
    }
}
```

**Why people believe it:** deserialization looks like "get an object back the way it was," and every other field really does come back with its written value, so it is easy to assume field initializers ran too — they never do, because `ObjectInputStream` allocates the object without executing any constructor or initializer code.

### Not declaring `serialVersionUID` means "Java picks a safe default"

**Wrong**

```java
class NoUid implements Serializable {
    int stakeMinor;
    String clientId;
    // no serialVersionUID — "the JDK will handle it"
}
// add a field later, redeploy, then:
// java.io.InvalidClassException: Ver3$NoUid; local class incompatible:
// stream classdesc serialVersionUID = 760042420889516798,
// local class serialVersionUID = 2193869912748673154
```

**Right**

```java
class NoUid implements Serializable {
    private static final long serialVersionUID = 1L; // pinned, survives future field additions
    int stakeMinor;
    String clientId;
}
```

**Why people believe it:** the compiler never warns loudly enough (IDEs often reduce it to a low-priority hint), and the computed UID does work correctly right up until the exact moment a field is added — so the belief survives untested until the first schema change months or years later.

### Removing a field from a `Serializable` class is safe because deserialization doesn't throw

**Wrong**

```java
// v1
class Position implements Serializable {
    private static final long serialVersionUID = 1L;
    RoundId roundId;
    Money amount;
    LimitSet limitsAtStakeTime; // removed in v2
}

// v2 — reads v1 streams without any exception
class Position implements Serializable {
    private static final long serialVersionUID = 1L;
    RoundId roundId;
    Money amount;
}
// the limitsAtStakeTime value that was on disk is gone, with no error to notice it by
```

**Right**

```java
// keep the field, or migrate the value explicitly during a controlled read-and-rewrite pass
class Position implements Serializable {
    private static final long serialVersionUID = 1L;
    RoundId roundId;
    Money amount;
    LimitSet limitsAtStakeTime; // retained until a migration job has re-read and archived it
}
```

**Why people believe it:** "compatible" is used informally to mean "won't break," and the compatibility table genuinely lists field removal as not throwing — the gap between "does not throw" and "does not lose data" is easy to miss until an audit finds a field that used to be populated and now silently is not.

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `Serializable` | Zero-method marker; authorizes reflective field access; default protocol is transitive over reference fields |
| Missing link in the graph | `NotSerializableException` names the unserializable leaf class, not the root object |
| Cycles | Handled via handles/back-references; no infinite loop, no duplication |
| `serialVersionUID` default | First 8 bytes of SHA-1 of a canonical class-shape description (Spec §4.6) — changes whenever the shape changes |
| Recommended declaration | `private static final long serialVersionUID = 1L;` |
| UID mismatch | `InvalidClassException`, message states both stream and local UID values |
| Class not found in stream | `ClassNotFoundException`, resolved **before** the UID is ever compared |
| Record default UID | `0L` per spec; UID matching not required for records |
| `transient` field on read | Type default (`null`/`0`/`false`) — never the field initializer's value |
| `static` field on read | Never in the stream; reader sees whatever the class currently holds |
| `ObjectStreamClass.getFields()` | Lists only the serializable fields, e.g. `[I stakeMinor]`; transient/static fields are simply absent |
| `serialPersistentFields` | Explicit `ObjectStreamField[]` that decouples the serial form from field declarations |
| `final transient` | Cannot be assigned in `readObject`; needs the serialization proxy ([02a](02a-magic-methods-and-constructor-bypass.md)) |
| Add a field | Compatible; old streams leave it at type default |
| Remove a field | Reads fine; old value silently discarded |
| Change a field's type | Incompatible; `InvalidClassException` |
| `Serializable` ↔ `Externalizable` | Incompatible; different stream format ([02b](02b-externalizable-records-and-lambdas.md)) |
| Method body change | Compatible; UID digest covers signatures, not implementations |

## Self-test

**Q1.** Why does implementing `Serializable` on one class potentially require every field type it references to also be `Serializable`?

<details><summary>Answer</summary>

The default protocol is transitive: `ObjectOutputStream` walks every non-transient, non-static reference field of the object being written, then recurses into each of those objects' own reference fields, continuing until the whole reachable graph has been visited. Any class in that chain that is not itself `Serializable` causes a `NotSerializableException` naming that specific class — not the object you originally called `writeObject` on. This is why marking an aggregate `Serializable` obligates checking the serializability of everything it transitively holds, including fields on service-like dependencies that may not obviously look like "data."

</details>

**Q2.** What exact byte range does the default `serialVersionUID` come from, and per which specification section?

<details><summary>Answer</summary>

The first 8 bytes of the SHA-1 digest of a canonically-ordered description of the class — its name, modifiers, implemented interface names, non-transient non-static field modifiers and descriptors, `<clinit>` if present, and constructor/method modifiers and descriptors — as defined in the Java Object Serialization Specification, §4.6, "Stream Unique Identifiers."

</details>

**Q3.** Two versions of a class differ only by one added field and neither declares `serialVersionUID`. What happens when code built from the new version tries to read a stream written by the old version?

<details><summary>Answer</summary>

`InvalidClassException`, because the computed default UID depends on the class's shape and adding a field changes the digest input, producing a completely different UID value on each side — measured as 760042420889516798 versus 2193869912748673154 for exactly this kind of one-field difference. The exception message states both the stream's UID and the local class's UID explicitly.

</details>

**Q4.** If a stream references a class name that does not exist on the reader's classpath at all, is the failure an `InvalidClassException`?

<details><summary>Answer</summary>

No — it is `ClassNotFoundException`. Class resolution by name happens before the UID is ever compared, so a renamed or missing class fails with `ClassNotFoundException`; only once the class is found does the UID-mismatch check (which would produce `InvalidClassException`) get a chance to run.

</details>

**Q5.** A field is declared `transient String pspToken = "tok-secret";`. After a full serialize/deserialize round trip, what value does `pspToken` hold, and why?

<details><summary>Answer</summary>

`null`, the type default for a reference field — not `"tok-secret"`. `transient` fields are excluded from the stream entirely, and deserialization never runs field initializers or constructor bodies, so there is no code path that would re-assign the initializer's value. This was measured directly: `Trans[stakeMinor=420, pspToken=null, shared=99]` after a round trip on a class where `pspToken` was declared with that initializer.

</details>

**Q6.** Does a `static` field's value travel with a serialized instance?

<details><summary>Answer</summary>

No. `static` fields belong to the class, not the instance, so the default protocol never includes them in the stream. On deserialization, the reader simply observes whatever value the class currently holds for that static field — which may differ from what it held at write time, since there is no snapshot of it at all.

</details>

**Q7.** Is removing a field from a `Serializable` class a compatible change under the Java Object Serialization Specification's versioning rules?

<details><summary>Answer</summary>

It is listed as a compatible change in the sense that reading an old stream against the new class definition does not throw — but the value the old stream held for that field is silently discarded, since nothing on the reading side has a slot for it anymore. "Compatible" here means "does not throw," not "no data is lost," which is the distinction that catches people off guard.

</details>

**Q8.** Why does a record default to `serialVersionUID = 0L` instead of a computed hash?

<details><summary>Answer</summary>

Per the Java Object Serialization Specification's record-serialization rules, records use a fixed default `serialVersionUID` of `0L`, and stream UID matching is not required for records the way it is for ordinary classes — records have their own, different serial-form rules built around their canonical constructor rather than raw field reflection. [02b](02b-externalizable-records-and-lambdas.md) covers the mechanism.

</details>

**Q9.** Why can't a `final transient` field simply be assigned inside `readObject`?

<details><summary>Answer</summary>

A `final` field can only be assigned once, at object construction — but `readObject` runs after `ObjectInputStream` has already allocated the object (bypassing the normal constructor), so by the time `readObject` executes, the window for assigning a `final` field has already closed. The workarounds are either dropping `final`, or moving to the serialization proxy pattern, which builds the real object through its actual constructor and sidesteps the problem; [02a](02a-magic-methods-and-constructor-bypass.md) has the mechanics.

</details>

**Q10.** Is changing a method's implementation body, with the same signature, a compatible or incompatible change to a `Serializable` class?

<details><summary>Answer</summary>

Compatible. The `serialVersionUID` digest input includes method *signatures* (name, modifiers, descriptor), not method bodies, so a behavior-only change does not alter the computed UID, and the reader's compatibility checks only ever look at the UID and the field set — never at what any method actually does.

</details>

## Open questions

None.

---

**Leaves covered:** 2.10.1, 2.10.2, 2.10.3, 2.10.13 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 441
