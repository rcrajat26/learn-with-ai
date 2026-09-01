# 03 Java Core — Immutability and design — Records, the cached derived field and the JMM freeze — INTERMEDIATE (§2.3, 2.3.11–2.3.13)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Shallow versus deep immutability](02a-shallow-deep-and-building-blocks.md) · Next: [Unsafe immutables, builders, and interning](02c-unsafe-immutables-builders-and-interning.md)

---

`02-immutability.md` established the five rules, the static-factory substitute for rule 1, the copy-then-validate ordering and the copy-versus-view decision; `02a-shallow-deep-and-building-blocks.md` took that from one level deep to arbitrarily deep, catalogued the mutable JDK types that break a naive `final`, and priced the allocation. This file settles three things. What a record gives you free and what it does not; why a mutable cache field written after construction, from any thread, with no synchronisation, does not break immutability; and the one JLS guarantee that makes a correctly constructed immutable object publishable through a plain data race with no lock and no `volatile`. The two ways that guarantee is forfeited, the builder that answers `02a`'s N-`withX` problem, and when to intern your own values are `02c-unsafe-immutables-builders-and-interning.md`.

Every measured output below was produced on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245), macOS aarch64**, compiled and run from a scratch directory under `/tmp/`. Library source is quoted from that build's `lib/src.zip`.

---

## 1. Records: rules 1–3 for free, a compact constructor for 4, an accessor override for 5 (2.3.11)

`[BUILD]` `[X-REF 04]` — Picture a record as a sealed envelope with a fixed set of labelled slots printed on the outside. What the labels name is the whole of what is inside: there is no back pocket, no hidden compartment, and no way to add one later. The labels are also the envelope's identity — two envelopes with the same slot contents *are* the same envelope, as far as anything that asks is concerned.

That picture is the semantics. A record is not "a class with less typing"; it is a **declaration that this type's state is exactly its components** — nothing more is stored, nothing else identifies it. Every syntactic saving falls out of that one semantic claim as a consequence the compiler is obliged to enforce, rather than a convention you have to keep enforcing in review. That distinction is the whole value: in a hand-written `final class Money` the immutability is a property of the code as currently written and one careless commit away from being false; in a `record Money` three of the five rules are properties of the *language* and a commit that breaks them does not compile.

### Why it exists

Because rules 1, 2 and 3 are pure boilerplate with a 100% failure-detection gap. Nothing in a hand-written immutable class tells a reader that the author *intended* `final class`, `private final` fields and no mutators, so nothing stops a later change from adding a setter to `Money` and nothing but a reviewer's attention catches it. A record makes the intent part of the type's declaration, so the compiler becomes the reviewer. What it does not and cannot do is decide what a component's *type* means: `List<LedgerEntry>` is a mutable type and no amount of language support changes that, which is why rules 4 and 5 stay yours.

### When to reach for it, and when not

Reach for a record for every value type in `02-immutability.md`'s list — `Money`, `ClientId`, `StatusCode`, `StakeSplit`, `RestrictionKey`, `AgreementRef`, `LimitSet` — and for aggregates whose identity genuinely *is* their contents. Do not reach for one when you need a superclass (a record can extend nothing but `java.lang.Record`), when you need a lazily cached field (§2 — a record forbids instance fields outright, shown below), when the type is a JPA `@Entity` or `@Embeddable` (guide 08: the provider needs a no-arg constructor and mutable field access, and neither is expressible), or when the type has components that should not participate in equality — a record's `equals` is over *all* components, and there is no way to exclude one without overriding `equals` by hand and thereby throwing away the reason you reached for a record.

### How it works

The five rules mapped onto the record, one line each. The first three are language guarantees; the last two are still your job.

| Rule | Record status | Mechanism |
|---|---|---|
| 1. No subclass | **Free** | A record class is implicitly `final` (JLS 21 §8.10 — "A record class is implicitly `final`."; §8.10.1 is *Record Components* and does not carry this); its direct superclass is always `java.lang.Record` and it can extend nothing else |
| 2. `private final` fields | **Free, and stronger** | Each component becomes a `private final` field. You cannot add *any* instance field, final or not — so there is no field to forget to make `final` |
| 3. No mutators | **Free** | No setter is generated, and a compact constructor cannot assign to `this.component` |
| 4. Copy in | **Not free** | The canonical constructor stores the reference it was handed. A record over a `List` is exactly `02a`'s shallow leak |
| 5. Copy out | **Not free** | The generated accessor returns the field directly |

Rule 2's "stronger" is worth measuring, because it is the one place a record beats a careful hand-written class rather than merely matching it. An instance field declaration in a record body is a compile error, not a warning:

```java
record Reservation4(String ref) {
    private int cachedHash;
}
```

```
Bad.java:2: error: field declaration must be static
    private int cachedHash;
                ^
  (consider replacing field with record component)
1 error
```

Note what the error actually says: **`must be static`**, not "must be final". Records forbid *all* instance state outside the components, which is the point — the components *are* the state, and an extra field would make that claim false. The immediate consequence is that §2's lazy hash cache, which `String` relies on, is not expressible in a record at all. Rule 3's enforcement is equally blunt:

```java
record Reservation5(String ref) {
    Reservation5 {
        this.ref = ref.trim();
    }
}
```

```
Bad2.java:3: error: cannot assign a value to final variable ref
        this.ref = ref.trim();
            ^
1 error
```

**Insight:** that error is the mechanism most readers get wrong, so read it carefully. Inside a compact constructor `ref` is the **parameter**, and `this.ref` is the final field — which is not yet assigned and cannot be assigned by you. The way a compact constructor changes what gets stored is by **assigning to the parameter name**, and the compiler then emits the field write from the (possibly reassigned) parameter after your body runs. `javap -c -p` on the `Reservation2` declared in *Pitfalls* below — `record Reservation2(String ref, List<WithdrawalId> itemIds)`, whose compact constructor does `itemIds = List.copyOf(itemIds)` — makes the ordering unambiguous (constructor only; the generated `equals`/`hashCode`/`toString`/accessors are elided):

```
  Reservation2(java.lang.String, java.util.List<WithdrawalId>);
    Code:
       0: aload_0
       1: invokespecial #1                  // Method java/lang/Record."<init>":()V
       4: aload_2
       5: invokestatic  #7                  // InterfaceMethod java/util/List.copyOf:(Ljava/util/Collection;)Ljava/util/List;
       8: astore_2
       9: aload_0
      10: aload_1
      11: putfield      #13                 // Field ref:Ljava/lang/String;
      14: aload_0
      15: aload_2
      16: putfield      #19                 // Field itemIds:Ljava/util/List;
      19: return
```

Offsets 0–1 are the implicit `super()` into `Record`. Offsets 4–8 are the compact constructor body: load parameter slot 2, call `List.copyOf`, `astore_2` — **store the result back into the parameter slot**. Offsets 9–16 are the compiler-generated field writes, and offset 15 loads slot 2, which now holds the copy rather than the caller's list. That single `astore_2` is the entire difference between a safe record and a leaky one. Omit the assignment — write `List.copyOf(itemIds);` as a bare statement — and the `astore_2` is not emitted, the copy is computed and discarded, and offset 15 stores the caller's list. Measured, three record variants over the same `ArrayList`, with `WD-7777` added by the caller after all three were constructed:

```
no assignment    : [WD-9001, WD-9002, WD-7777]  class=ArrayList
assigned param   : [WD-9001, WD-9002]  class=List12
accessor override: [WD-9001, WD-9002, WD-7777]  class=ListN
override, same instance twice? false
assigned, same instance twice? true
```

Line 1: the copy happened and was thrown away. Line 2: the copy was assigned, so the field is an `ImmutableCollections$List12` the caller cannot reach. Line 3 is the honest limit of the accessor-override fix, and it corrects the tempting summary that the two fixes are equivalent alternatives: an accessor override satisfies **rule 5 only**. It copies on the way out, so a caller cannot mutate through the accessor — but the field still aliases the caller's list, so the caller's own `add` is still visible, and every call allocates (line 4: two calls, two instances). The compact constructor satisfies **rule 4, and gets rule 5 free** because the stored value's own type refuses mutation (line 5: identity stable, zero allocation per read), which is `02-immutability.md` §4's decision rule arriving at the same answer. So they are not a pair and not interchangeable: the compact constructor is strictly better, and the accessor override earns its keep only when you deliberately keep a mutable field, which in a record you have chosen not to do.

### Diagram

No diagram is assigned to this concept; §2.3's two figures (D-069, the five rules as gates, and D-070, the copy ordering) are both embedded in `02-immutability.md` and both apply here unchanged — a record simply pre-closes gates 1, 2 and 3. `../records-and-sealed/01a-object-methods-sealed-and-fit.md` owns the record's own figures.

### A concrete example

`[BUILD]`. The complete safe form. This compiles and runs as written.

```java
record MovementId(UUID value) {}

record Money(BigDecimal amount, String currency) {}

record LedgerEntry(String position, BigDecimal amount) {
    @Override public String toString() { return position + ":" + amount; }
}

record Movement(MovementId id, Money amount, Instant postedAt, List<LedgerEntry> entries) {
    Movement {
        Objects.requireNonNull(id, "id must not be null");
        Objects.requireNonNull(amount, "amount must not be null");
        Objects.requireNonNull(postedAt, "postedAt must not be null");
        Objects.requireNonNull(entries, "entries must not be null");
        entries = List.copyOf(entries);                       // rule 4 — assign the PARAMETER
        if (entries.size() < 2) {                             // then validate the copy
            throw new IllegalArgumentException("a movement needs at least two entries");
        }
    }
}
```

The ordering inside that compact constructor is `02-immutability.md` §3's discipline verbatim: null check, copy, validate the copy. The one thing that looks different is that the validation reads the *parameter* and not `this.entries` — because in a compact constructor you cannot read `this.entries` either, it is not assigned yet. After the `entries = List.copyOf(entries)` line the parameter *is* what will be stored, so validating it is validating the copy, and the TOCTOU window is closed by the same argument. Measured, with a `MovementLeaky` declared identically but with no compact constructor, both handed the same `ArrayList`, and `HOUSE_REVENUE:99.00` appended by the caller afterwards:

```
leaky.entries() = [CLIENT_CASH_AVAILABLE:-4.20, CLIENT_CASH_RESERVED:4.20, HOUSE_REVENUE:99.00]
safe.entries()  = [CLIENT_CASH_AVAILABLE:-4.20, CLIENT_CASH_RESERVED:4.20]
leaky hashCode stable? false
safe.entries() class = java.util.ImmutableCollections$List12
safe.entries().add -> UnsupportedOperationException
safe.entries() same instance every call? true
record class final? true
record superclass = java.lang.Record
field id modifiers = private final
field amount modifiers = private final
field postedAt modifiers = private final
field entries modifiers = private final
```

Lines 1–2 are rule 4, present and absent. Line 3 is the consequence nobody costs in: a record's generated `hashCode` folds every component's hash, so a mutable component means a **drifting hash**, and `leaky` filed into a `HashMap` before the caller's `add` can no longer find itself afterwards — the same failure `02-immutability.md` §5 measured for a mutable list key, now reached through the record's own generated method. `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` owns the contract that is being broken. Lines 4–6 are rule 5 arriving free. Lines 7–11 are rules 1 and 2 confirmed reflectively rather than asserted.

### The gotcha

**Pitfall:** believing "records are immutable". Records are *shallowly* immutable by construction and that is a different claim. Symptom: a `record Movement(..., List<LedgerEntry> entries)` reviewed as a value type, whose `entries()` a caller mutates in place, whose `equals` then reports two previously-equal movements unequal, and whose `hashCode` drifts out from under every `HashSet` and `HashMap` it was filed into — with no method on `Movement` ever having been called. Fix: a compact constructor that copies every mutable component and assigns the result to the parameter, plus `02a`'s discipline that "mutable component" is judged transitively, so a component that is itself a record of immutables is fine and a component holding a `Date`, an array, a `Calendar` or a `SimpleDateFormat` is not.

**Interview:** "Do records give you immutability?" The weak answer is yes. The strong 60-second answer: rules 1, 2 and 3 free and compiler-enforced — implicitly `final`, components are `private final`, and instance fields are a compile error, which is stronger than a hand-written class gives you; rules 4 and 5 not free, because the canonical constructor stores the reference it was handed and the accessor returns the field; the fix is a compact constructor assigning `component = List.copyOf(component)`, and the tell that a candidate has actually written one is that they know the assignment is to the *parameter*.

Records as a language feature — the canonical/compact/alternative constructor forms, local records, records in pattern matching — belong to guide 04. The generated `equals`, `hashCode` and `toString`, sealed hierarchies, and the full "when to reach for a record" decision belong to `../records-and-sealed/01a-object-methods-sealed-and-fit.md`. Serialization of records, which bypasses the accessor path and goes through the canonical constructor instead — the one place records are a genuine improvement over hand-written classes — belongs to `../serialization/02-serialization.md`.

> **Definition.** A record declares that a type's state is exactly its components, which makes rules 1–3 compiler-enforced consequences (implicitly `final`, components stored as `private final` fields, no instance fields permitted at all, no mutators generated and no assignment to `this.component`) while leaving rules 4 and 5 to a compact constructor that assigns a defensive copy **to the parameter name** and, only if a field is deliberately left mutable, an accessor override.

---

## 2. The lazily computed, cached derived field, and why it does not break immutability (2.3.12)

`[PROVE]` — `String` is the canonical immutable class in the entire platform, and it has a **non-final `int` field that it writes to after construction**, from any thread, with no synchronisation, no `volatile`, and no lock. Both halves of that sentence are true simultaneously, and the reason is that `02-immutability.md` §1's definition is about *observable state*, not about fields. A field that is a pure function of immutable state is not state; it is a memo, and a memo can be filled in later without anyone being able to tell.

### Why it exists

Because `hashCode` on a long `String` is O(n) and gets called repeatedly. A `HashMap<String, Position>` keyed on `CLIENT_BONUS_RESERVED` recomputes a 21-character fold on every `get` unless something remembers it, and at 19.8M ledger entries a day each touching several such lookups, that fold is not free. The cache converts an O(n) call into an O(1) field read after the first call. The reason it is worth studying rather than just using is that it is the one immutability pattern where the *memory model* is load-bearing, and where the argument for safety has to be made rather than assumed.

### When to reach for it, and when not

Reach for it when all four conditions hold, and the fourth is the one people skip:

| Condition | Why | `String.hash` |
|---|---|---|
| The value is **derived** from state that never changes | Every writer computes the same value | Yes — folds `value` and `coder`, both final |
| Computing it is **idempotent and side-effect-free** | A racing recompute costs time only | Yes |
| The field is **`int`, `boolean`, or a reference** | The JMM guarantees these writes are atomic | Yes — `int` and `boolean` |
| A **sentinel** distinguishes "not computed" from a legitimate value | Otherwise the cache silently never engages | Yes — `hashIsZero` |

Do not reach for it when the derived value is a `long` or `double` (the JMM's atomicity exemption applies, and a reader can see a torn value — worked below), when it is a mutable object (two threads can publish two different instances that later diverge — worked below), when computing it is expensive enough that redundant computation under contention matters more than the cache saves, or when the type is a record, which as §1 measured cannot hold an instance field at all.

### How it works

`[PROVE]`. The claim to be established: **a plain, non-final, non-volatile field written after construction by any number of racing threads does not break immutability, provided the four conditions above hold.** Three legs, all of which must stand.

**(a) The field is not part of the observable state.** The value cached is a pure function of state that cannot change. So every thread that computes it computes *the same* `int`. A reader therefore sees one of exactly two things: the sentinel (and recomputes, correctly), or the one correct value (and returns it, correctly). There is no third possibility — no stale-but-different value exists to be seen, because no different value was ever written. This is what makes the race *benign*: a race is only a bug when the possible outcomes differ observably, and here they do not.

**(b) The write cannot be seen half-done.** JLS 21 §17.7 (*Non-Atomic Treatment of `double` and `long`*) grants an atomicity exemption to exactly two types: a single write to a non-volatile `long` or `double` may be treated as two separate 32-bit writes, and a read may see the first half of one write and the second half of another. **Every other type is exempt from the exemption** — writes and reads of `int`, `boolean`, `short`, `char`, `byte`, `float` and references are atomic whether or not the field is `volatile`. `String.hash` is an `int`, so no reader can observe a half-written hash. Note what this leg does *not* claim: it says nothing about *visibility* or ordering, only about indivisibility. A reader may see the old value indefinitely — leg (a) is what makes that harmless.

**(c) Redundant work is not incorrectness.** If four settlement threads all miss the cache on the same `String` at once, all four compute the fold and all four write the same `int`. The cost is three wasted folds; the outcome is identical. Performance loss, not correctness loss.

All three legs are needed. Drop (a) and racing writers disagree. Drop (b) and a reader sees a value nobody wrote. Drop (c) and the pattern is still correct but no longer worth it.

`[SOURCE]`. The JDK makes this argument in a comment, and the comment is a better statement of the invariant than most textbooks manage. From `java.base/java/lang/String.java`, JDK 21.0.7, lines 172–180:

```java
    /** Cache the hash code for the string */
    private int hash; // Default to 0

    /**
     * Cache if the hash has been calculated as actually being zero, enabling
     * us to avoid recalculating this.
     */
    private boolean hashIsZero; // Default to false;
```

Two fields, both `private`, and — measured reflectively — **neither `final`**:

```
field modifiers hash       = private
field modifiers hashIsZero = private
```

Why the second field exists is the part that is usually skipped. `hash == 0` has to mean "not yet computed", because 0 is what a fresh field holds. But `0` is also a legitimate hash: `"".hashCode()` is 0, and so — non-trivially — is `"f5a5a608".hashCode()`. Non-empty zero-hash strings are not a curiosity of one lucky literal; they exist in quantity, and they start short. Measured, a search over the lowercase-alphanumeric alphabet `[0-9a-z]` by increasing length — exhaustive for lengths 1–6, and by meet-in-the-middle on the 31-multiplier fold for length 7, since 36^7 = 78,364,164,096 candidates is not brute-forceable (two runs, output concatenated):

```
length 1: candidates=36 zero-hash=0
length 2: candidates=1296 zero-hash=0
length 3: candidates=46656 zero-hash=0
length 4: candidates=1679616 zero-hash=0
length 5: candidates=60466176 zero-hash=0
length 6: candidates=2176782336 zero-hash=0
length 7 zero-hash count = 2 -> [zsjpxah, zsl2xah]
"f5a5a608".hashCode() = 0 length=8
```

So over this alphabet the shortest non-empty zero-hash strings are seven characters long — `"zsjpxah"` and `"zsl2xah"`, and no shorter one exists — and `"f5a5a608"` is an eight-character example. The reason none appear below seven is arithmetic, not luck. The fold is `c0*31^(n-1) + ... + cn-1`, and over this alphabet every character is between `'0'` (48) and `'z'` (122), so at length 6 the unreduced sum lies in `[48 * 29583456, 122 * 29583456]` = `[1420005888, 3609181632]` — where `29583456 = (31^6 - 1)/30`. A hash of 0 requires that sum to be an exact multiple of 2^32, and the only candidate in range would be 4294967296, which is above the maximum. At length 7 the range becomes `[44020182576, 111884630714]`, which straddles sixteen multiples of 2^32, and zero becomes reachable. Without a second field, every call on such a string would miss the cache, recompute the whole fold, get 0, write 0, and miss again next time, for ever. `hashIsZero` disambiguates: `hash == 0 && !hashIsZero` means not computed; `hashIsZero == true` means computed, and it was zero.

**Version trap.** `hashIsZero` was added in **JDK 13** (JDK-8221836). On **Java 8 through 12** the field does not exist and `String.hashCode` is `if (h == 0 && value.length > 0)` — which handles `""` by the length test but still recomputes for ever on any non-empty zero-hash string. Older material describing the two-field form as always having been there is wrong, and older material describing the length-test form as current is also wrong. Both forms are correct; only the second is present in 21.

Now the method, from the same file, and it must be read line by line because every line is doing memory-model work:

```java
    public int hashCode() {
        // The hash or hashIsZero fields are subject to a benign data race,
        // making it crucial to ensure that any observable result of the
        // calculation in this method stays correct under any possible read of
        // these fields. Necessary restrictions to allow this to be correct
        // without explicit memory fences or similar concurrency primitives is
        // that we can ever only write to one of these two fields for a given
        // String instance, and that the computation is idempotent and derived
        // from immutable state
        int h = hash;
        if (h == 0 && !hashIsZero) {
            h = isLatin1() ? StringLatin1.hashCode(value)
                           : StringUTF16.hashCode(value);
            if (h == 0) {
                hashIsZero = true;
            } else {
                hash = h;
            }
        }
        return h;
    }
```

The comment names the race outright ("benign data race") and states the two restrictions that make it benign — legs (a) and (c) of the proof, in the JDK's own words, plus a third the comment adds that is easy to miss: *"we can ever only write to one of these two fields for a given String instance."* That is why the `if (h == 0)` branch is exclusive. If both fields could be written for one instance, a reader could see `hashIsZero == true` set by one thread and `hash == someNonZero` set by another, and the two would contradict. Writing exactly one of them makes the pair internally consistent under any interleaving.

`int h = hash;` reads the field **once** into a local. This is not a stylistic choice: reading `hash` twice would allow the two reads to return different values (the write can land between them), and the method could then test one value and return another. One read, one decision, one return.

`if (h == 0 && !hashIsZero)` is the two-field miss test, and short-circuits so the common non-zero-hash case reads `hashIsZero` not at all.

The fold itself branches on `isLatin1()` because a JDK 21 `String` stores either one byte or two per character (`CompactStrings = true`, measured on this build); `../strings/03a-internals-hash-and-equality.md` owns both fold implementations, the 31-multiplier choice and the vectorised intrinsic.

`return h;` returns the local, so a reader whose write lost the race still returns the correct value it computed itself.

Measured, on strings built at runtime with a `StringBuilder` so they are not interned literals something else has already touched, reading the private fields reflectively before and after the first call:

```
s = f5a5a608
  before 1st call: hash=0 hashIsZero=false
  hashCode()     = 0
  after  1st call: hash=0 hashIsZero=true
  hashCode()     = 0
t = CLIENT_BONUS_RESERVED
  before 1st call: hash=0 hashIsZero=false
  hashCode()     = -1851020708
  after  1st call: hash=-1851020708 hashIsZero=false
```

The first block is exactly the case `hashIsZero` exists for: a genuine zero hash, `hash` left at 0 for ever, `hashIsZero` flipped so the fold never runs again. The second is the common case: `hash` populated, `hashIsZero` untouched — one field written per instance, as the comment requires.

**Aside, since it is the famous fact and the folklore has it wrong:** `"polygenelubricants"` does **not** hash to 0. Measured on 21.0.7, `"polygenelubricants".hashCode()` is `-2147483648`, i.e. `Integer.MIN_VALUE` — it is the celebrated string whose hash is the most-negative `int`, not zero. `"f5a5a608"` is a real non-empty zero-hash string.

### Diagram

No diagram is assigned to this concept. The mechanism is a five-line method and a two-field state machine, and the state machine is better read as the measured before/after field dump above than as a picture; `../strings/03a-internals-hash-and-equality.md` carries the `String` internals figures.

### A concrete example

The boundary, stated as the two counterexamples the pattern does *not* cover.

**A cached `long`.** A `LedgerTotals` caching a running total in minor units cannot use this pattern, because JLS 17.7's exemption applies:

```java
final class LedgerTotals {
    private long cachedRunningTotalMinorUnits;   // plain long: NOT atomic under the JMM

    void write(long v) { cachedRunningTotalMinorUnits = v; }
    long read()        { return cachedRunningTotalMinorUnits; }
}
```

A racing reader is *permitted* to observe the high 32 bits of one write and the low 32 bits of another, producing a total nobody ever wrote — leg (b) of the proof fails outright, so the whole argument collapses. The fix is `volatile`, which JLS 17.7 explicitly restores atomicity for, or a lock, or `AtomicLong`.

**Unverified:** this tearing could not be demonstrated on the measurement machine. A writer thread alternating a plain `long` field between `0x0000000000000000` and `0xFFFFFFFFFFFFFFFF` against a reader spinning for three seconds produced `reads=376625806 torn=0`. That is the expected result, not a refutation: aarch64 and x86-64 both implement aligned 64-bit loads and stores atomically in hardware, so the spec's permission is not exercised by these CPUs. The claim is a **specification** claim about what a conforming implementation may do, and the honest statement is that it is not observable on this machine and must not be relied on as unobservable on another.

**A cached mutable derived object.** Suppose `Movement` cached a derived `List<Position>` of the positions it touches. Leg (b) holds — a reference write is atomic — but leg (a) fails: two threads racing produce two *different* list instances, and there is no guarantee about which one any given reader sees. While both are immutable that is merely wasteful (the same trap `String.hash` accepts). The moment either is mutable, two callers hold two objects that can diverge, and `movement.touchedPositions()` can report different contents to two threads for ever after. If you must cache a derived object, cache an **immutable** one, and accept that the identity of the cached instance is not stable across threads — so never let a caller use `==` on it.

### The gotcha

**Pitfall:** believing that because `String` gets away with a plain non-volatile cache field, any lazily initialised field is safe without synchronisation. The belief generalises leg (b) and quietly drops leg (a). Symptom: a lazily built `LimitSet` or a lazily parsed `Jurisdiction` cached in a plain field, where thread A publishes a half-initialised object (its constructor's field writes reordered past the reference write — §3's limits) and thread B reads it and sees a `LimitSet` with a null `maxStake`. `String.hash` is safe because the cached thing is an `int` computed by a pure function; a cached *object* is a publication, and publication needs either `final` fields (§3), `volatile`, or the holder idiom, which `../classes-and-initialization/01d-class-initialization-triggers.md` owns.

**Interview:** "`String` is immutable but it mutates its `hash` field — how is that not a contradiction?" The strong answer is the three legs, in order, in about forty seconds: the field is a pure function of immutable state so every writer writes the same value and a reader sees either the sentinel or that value; a 32-bit write is atomic under JLS 17.7 even without `volatile`, so no torn read; and a redundant recompute is a performance loss, not a correctness one. Then volunteer `hashIsZero` and *why* it exists — that is the part that distinguishes someone who has read the source from someone who has read about it.

> **Definition.** A lazily computed, cached derived field does not break immutability when the cached value is a pure function of immutable state (so every writer writes the same value and no stale-but-different value can exist), when the field's type is one the JMM writes atomically without `volatile` — anything but `long` and `double` — and when a sentinel distinguishes "not yet computed" from a legitimate value; under those conditions the data race on the field is benign, because no possible interleaving produces an observable difference.

---

## 3. The JMM `final`-field freeze that makes an immutable object safe to publish by a data race (2.3.13)

`[X-REF 05]` — Everything you have been told about sharing objects between threads says: publish through a `volatile` field, or a lock, or a concurrent collection, or you get no guarantee. There is exactly one exception in the entire memory model, and it is the reason `String`, `Integer`, `Instant` and `BigDecimal` can be flung around a 3,400/sec settlement path with no synchronisation anywhere: **if an object's fields are `final`, a thread that sees the object's reference at all is guaranteed to see those fields correctly, even if the reference reached it through a plain unsynchronised data race.**

### Why it exists

Without it, immutability would buy far less than advertised. "No writes, therefore no races" is intuitive but not, on its own, a memory-model argument: the constructor's field writes *are* writes, and absent a rule forbidding it, a compiler or CPU could reorder the publication of `this` ahead of them, letting another thread see the reference before the fields. Every immutable object would then need a safe-publication ceremony, and `Money.ZERO` in a plain `static` field would be a bug. JLS 21 §17.5 exists precisely so that the intuition is *made* true, and so that immutable value types are cheap to share.

### When to reach for it, and when not

Rely on it whenever every field you need a reader to see is `final` and the object is fully constructed before publication. Do not rely on it for a plain field alongside the `final` ones, for the *contents* of a mutable object a `final` field points at (unless those contents were fully written before the constructor returned and are never written again), or as an answer to "will the reader see the reference at all" — it answers *what*, never *whether*. And note the shape of the guarantee: it is not something you enable, it is something the compiler and JVM are obliged to give you whether you asked or not. The only way to lose it is to drop the `final` keyword or to let `this` escape, and both are worked in `02c-unsafe-immutables-builders-and-interning.md` §1 — (a) and (b) of that section respectively.

### How it works

One self-contained mechanism paragraph, because this must be answerable without opening guide 05.

JLS 21 §17.5 (*`final` Field Semantics*) specifies that a **freeze action** occurs on each `final` field at the end of the constructor in which it is set. The model then forbids a reordering that would let a read of that field, reached through a reference obtained after the constructor completed, observe a value from before the freeze. Concretely: the compiler may not sink a `final` field write below the store that publishes `this`, and on a weakly ordered CPU the JIT is obliged to emit whatever barrier makes that ordering real: a `StoreStore` before the publishing store. **Unverified:** the shape that barrier takes in generated code — on aarch64, plausibly folded into a release-flavoured store (`stlr`) rather than emitted as a standalone `dmb ishst` — is a HotSpot codegen detail this file does not measure, and nothing in §17.5 specifies it. What the spec obliges is the *ordering*; how a given backend buys it is the backend's business. So the two events "the `final` fields are written" and "the reference becomes visible" cannot be observed out of order. There is no runtime flag, no annotation and no cooperation from the reader — a reader doing an ordinary plain load of an ordinary plain field gets it, which is what makes it usable.

Work the concrete case. `MoneyCache` computes the zero-`ExplicitMoney` for GBP once and parks it in a plain `static` field; 3,400 settlement threads per second read it. `ExplicitMoney` is declared under *A concrete example* below: it is §1's `record Money` written out longhand as a `final class` with two explicitly `final` fields, because the point of this section needs a class whose `final` keywords you can *delete* to see the guarantee lost — and a record's component fields are implicitly final with no keyword to remove.

```java
final class MoneyCache {
    static ExplicitMoney cachedZeroGbp;             // plain. NOT volatile. NOT final.

    static void warm() {                            // one thread, at startup
        cachedZeroGbp = new ExplicitMoney(BigDecimal.ZERO, "GBP");
    }

    static ExplicitMoney zeroGbp() {                // 3,400 threads/sec
        ExplicitMoney m = cachedZeroGbp;
        return m == null ? new ExplicitMoney(BigDecimal.ZERO, "GBP") : m;
    }
}
```

`cachedZeroGbp` is a plain static and its write races with every read. What §17.5 buys: **if** a reader's load returns non-null, the `ExplicitMoney` it points at has its `amount` and `currency` correctly visible — not null, not a default — because both are `final` and the freeze at the end of `ExplicitMoney`'s constructor precedes the publication. The `m == null` fallback is there because §17.5 says nothing about *whether* the reader sees the write; that part is a genuine race and a reader may see null for an unbounded time. But it cannot see a non-null reference to a broken `ExplicitMoney`. That is the exact guarantee, no more and no less, and it is the whole reason a JDK value type needs no publication ceremony.

Three limits, each stated precisely, because each is where the guarantee gets misquoted:

**It covers `final` fields only.** A class with three `final` fields and one plain field gets the freeze for three of them. The fourth can be read as its default by a racy reader even though the constructor assigned it. Mixing is the trap, because the class *looks* covered.

**It covers reachability through `final` fields transitively — conditionally.** §17.5 extends to objects reachable from a `final` field, so a `final List<LedgerEntry> entries` field means a racy reader sees not just the list reference but the list's *elements* — **provided** the list was fully populated before the freeze and is never written afterwards. `List.copyOf(entries)` in the constructor satisfies both: the copy is built inside `copyOf` and is immutable, so there is no later write to be unordered. A `final ArrayList` field populated by a method called *after* the constructor returns satisfies neither, and its elements are not covered. That conditional is why `02-immutability.md` §3's copy-in discipline is a *concurrency* fix and not only an encapsulation one.

**It says nothing about whether.** A reader may observe `null` forever. The guarantee is conditional on obtaining the reference: *if* you see it, the `final` fields are right. Code that needs the reference to become visible needs `volatile`, a lock, or class initialization (the holder idiom), and code that merely needs to be correct when it does see it needs neither.

### Diagram

No diagram is assigned to this concept. The picture belongs to `../classes-and-initialization/04-internals-final-and-constant-folding.md`, which carries **D-122**, the `final`-field freeze timeline — the constructor's field writes, the freeze action, the publishing store, and the reader's load, drawn against the two reorderings the model forbids. That figure is exactly this section's illustration; read it there rather than duplicating it here.

### A concrete example

The class that gets the guarantee, with the freeze marked. This is §1's `record Money(BigDecimal amount, String currency)` written out longhand and renamed to keep the two distinct: identical state, identical immutability, but the two `final` keywords are written by hand, which is what makes the negative experiment below expressible at all.

```java
public final class ExplicitMoney {
    private final BigDecimal amount;
    private final String currency;

    public ExplicitMoney(BigDecimal amount, String currency) {
        this.amount = Objects.requireNonNull(amount, "amount must not be null");
        this.currency = Objects.requireNonNull(currency, "currency must not be null");
    }                                          // <-- JLS 17.5 freeze on both fields here

    public BigDecimal amount() { return amount; }
    public String currency()   { return currency; }
}
```

This `ExplicitMoney` may be published through a plain field, an unsynchronised `HashMap`, a non-`volatile` static, a data race of any shape — a reader that gets the reference gets correct fields. Delete the two `final` keywords and the class is identical in every observable single-threaded respect — no setters, never mutated, same `equals`, same `hashCode`, every test still passes — and broken under a racy publication. `02c-unsafe-immutables-builders-and-interning.md` §1(a) works exactly that schedule, step by step.

### The gotcha

**Pitfall:** quoting the guarantee as "immutable objects are thread-safe" and stopping. That drops all three limits at once, and the one that bites is the third: a team concludes that because `ExplicitMoney` is immutable, `cachedZeroGbp` needs no `volatile` **and** that a reader is therefore guaranteed to observe the warm-up. Symptom: a `zeroGbp()` with no null fallback, working in every test (single-threaded warm-up, then reads) and NPE-ing in production the one time a settlement thread reaches the field before the warm-up write becomes visible to it. Fix: separate the two questions. *What* the reader sees, given the reference, is settled by §17.5 for `final` fields. *Whether* the reader sees the reference is a plain visibility question and needs `volatile`, a lock, or class initialization.

**Interview:** "Can you safely share an immutable object between threads without synchronisation?" Yes, and the strong answer names the rule: JLS 17.5's `final`-field freeze guarantees a thread that obtains a correctly constructed object's reference sees its `final` fields correctly, even through a data race, because the freeze at the end of the constructor forbids reordering the field writes past the publication of `this`. Then volunteer the three limits — `final` fields only, transitive reachability only if the reachable state was complete before the freeze, and no guarantee that the reference is seen at all. Guide 05 owns happens-before, safe publication and the full catalogue of publication idioms; `../classes-and-initialization/04-internals-final-and-constant-folding.md` owns the freeze itself.

> **Definition.** The `final`-field freeze (JLS 21 §17.5) is a memory-model action at the end of every constructor that guarantees a thread obtaining a correctly constructed object's reference — even through a data race with no lock, no `volatile` and no happens-before edge — observes the correct values of that object's `final` fields and of state transitively reachable from them that was complete before the freeze; it covers neither plain fields nor later writes, and it does not guarantee the reference becomes visible at all.

---

## Pitfalls

### Records are immutable

**Wrong**

```java
record Movement(MovementId id, Money amount, Instant postedAt, List<LedgerEntry> entries) {}
```

```
leaky.entries() = [CLIENT_CASH_AVAILABLE:-4.20, CLIENT_CASH_RESERVED:4.20, HOUSE_REVENUE:99.00]
leaky hashCode stable? false
```

The caller kept the `ArrayList` it passed in and appended `HOUSE_REVENUE:99.00`. The record's accessor reports it, and — the part nobody costs in — the record's *generated* `hashCode` folds every component, so the hash drifted and the movement can no longer find itself in any `HashMap` or `HashSet` it was filed into.

**Right**

```java
record Movement(MovementId id, Money amount, Instant postedAt, List<LedgerEntry> entries) {
    Movement {
        Objects.requireNonNull(entries, "entries must not be null");
        entries = List.copyOf(entries);        // assign the PARAMETER, not this.entries
        if (entries.size() < 2) {
            throw new IllegalArgumentException("a movement needs at least two entries");
        }
    }
}
```

```
safe.entries()  = [CLIENT_CASH_AVAILABLE:-4.20, CLIENT_CASH_RESERVED:4.20]
safe.entries() class = java.util.ImmutableCollections$List12
safe.entries().add -> UnsupportedOperationException
safe.entries() same instance every call? true
```

The compact constructor's assignment to the parameter is what changes the field write (`astore_2` at offset 8 of the `javap` output in §1), so the field holds a `List12` the caller cannot reach — which satisfies rule 4 and, because the stored type refuses mutation, rule 5 for free at zero cost per read.

**Why people believe it:** the language *does* deliver rules 1, 2 and 3 by construction and enforces them at compile time — a record is implicitly `final`, its components are `private final`, and even a `private int` instance field is a compile error. Three of five arriving free, with the compiler as enforcer, reads as the whole job done; and every introductory record example uses `int`, `String` and other records as components, where shallow immutability and deep immutability coincide and the gap never surfaces.

### A compact constructor that calls `List.copyOf` is enough

**Wrong**

```java
record Reservation1(String ref, List<WithdrawalId> itemIds) {
    Reservation1 {
        List.copyOf(itemIds);              // copy made, result discarded
    }
}
```

```
no assignment    : [WD-9001, WD-9002, WD-7777]  class=ArrayList
```

The copy was computed and thrown away. The field still holds the caller's `ArrayList` — the class name in the output proves it — and `WD-7777`, a withdrawal carrying `WITHDRAWAL_BLOCKED` from `SYSTEM_COMPLIANCE`, is inside a reservation that never accepted it.

**Right**

```java
record Reservation2(String ref, List<WithdrawalId> itemIds) {
    Reservation2 {
        itemIds = List.copyOf(itemIds);    // copy assigned to the parameter
    }
}
```

```
assigned param   : [WD-9001, WD-9002]  class=List12
```

Assigning to the parameter changes the value the compiler-generated `putfield` stores, because that `putfield` loads the parameter slot after your body has run. Without the assignment there is no `astore_2` and the field write reads the original.

**Why people believe it:** in an ordinary constructor `this.itemIds = List.copyOf(itemIds)` is the idiom, and in a compact constructor that exact line is a **compile error** — `cannot assign a value to final variable itemIds`. Having been told they must not write `this.`, readers drop the assignment entirely rather than moving it to the bare parameter name, and the result compiles cleanly, allocates a real immutable list, and does nothing.

### If `String` can cache its hash in a plain non-volatile field, any lazily computed field is safe in one

**Wrong**

```java
final class LedgerTotals {
    private final List<LedgerEntry> entries;
    private long cachedRunningTotalMinorUnits;      // plain long: NOT atomic under the JMM

    LedgerTotals(List<LedgerEntry> entries) {
        this.entries = List.copyOf(entries);
    }

    long runningTotalMinorUnits() {
        long total = cachedRunningTotalMinorUnits;
        if (total == 0) {
            for (LedgerEntry entry : entries) {
                total += entry.amount().movePointRight(2).longValueExact();
            }
            cachedRunningTotalMinorUnits = total;
        }
        return total;
    }
}
```

The field is derived, idempotent and sentinel-guarded — three of the four conditions — and it is still not the `String` pattern, because it is a `long`. JLS 21 §17.7 permits a non-volatile `long` write to be treated as two 32-bit writes, so a racy reader is permitted to observe the high half of one write and the low half of another and return a running total nobody ever computed. Two ledger totals differing by 2^32 minor units, from a method with no branch that could produce them.

**Right**

```java
final class LedgerTotals {
    private final List<LedgerEntry> entries;
    private volatile long cachedRunningTotalMinorUnits;   // volatile restores 64-bit atomicity

    LedgerTotals(List<LedgerEntry> entries) {
        this.entries = List.copyOf(entries);
    }

    long runningTotalMinorUnits() {
        long total = cachedRunningTotalMinorUnits;
        if (total == 0) {
            for (LedgerEntry entry : entries) {
                total += entry.amount().movePointRight(2).longValueExact();
            }
            cachedRunningTotalMinorUnits = total;
        }
        return total;
    }
}
```

`volatile` is the one thing JLS 17.7 names as restoring atomicity to `long` and `double`, and it costs a barrier on a write that happens once per instance. A lock or an `AtomicLong` does the same job. Note what did *not* need fixing: the race itself stays benign, because legs (a) and (c) of §2's proof still hold — every writer computes the same total, and a redundant recompute is a performance loss only.

**Why people believe it:** `String.hashCode` is the most-read caching code in the platform and the lesson people take from it is "a benign race needs no synchronisation", which is leg (a) generalised with leg (b) silently dropped. The field type never enters the summary. It is also unfalsifiable by testing: aarch64 and x86-64 both implement aligned 64-bit loads and stores atomically in hardware, so a tearing harness measures `torn=0` — the permission is in the specification, not in the CPU you happen to be on.

---

## Cheat sheet

| Claim | Fact (JDK 21.0.7) |
|---|---|
| Record: rules 1–3 | Free and compiler-enforced. Implicitly `final`; superclass always `java.lang.Record`; components are `private final`; no mutators generated |
| Record: instance field | **Compile error** — `field declaration must be static`. *Any* instance field, final or not — so §2's lazy cache is inexpressible |
| Record: `this.component = x` in compact ctor | **Compile error** — `cannot assign a value to final variable` |
| Record: how to change the stored value | Assign the **parameter name**: `entries = List.copyOf(entries);` → an `astore_2` before the compiler's `putfield` |
| Record: rules 4 and 5 | Not free. Compact ctor fixes 4 and gets 5 free; accessor override fixes 5 **only**, and allocates per call |
| Record `hashCode` | Folds all components → a mutable component means a drifting hash, so the record cannot find itself in a `HashMap` |
| `String` cache fields | `private int hash` and `private boolean hashIsZero`, **neither `final`**. `hashIsZero` added JDK 13 (JDK-8221836); Java 8–12 used `h == 0 && value.length > 0` |
| Why `hashIsZero` | 0 is both the sentinel and a legitimate hash (`""`, and — measured — `"f5a5a608"`; over `[0-9a-z]` the shortest are the 7-char `"zsjpxah"` and `"zsl2xah"`). `hashCode()` writes one field **or** the other, never both |
| Benign-race conditions | Derived from immutable state + idempotent + atomic field type + a sentinel. All four |
| JMM atomicity (JLS 17.7) | All types atomic without `volatile` **except** non-volatile `long` and `double` — which is the leg a cached `long` fails |
| `"polygenelubricants".hashCode()` | `-2147483648`, i.e. `Integer.MIN_VALUE` — **not** 0. Folklore corrected |
| `final`-field freeze (JLS 17.5) | Obtain a correctly constructed object's reference by any means, including a data race → its `final` fields are correct |
| The three freeze limits | (1) `final` fields only — a plain field beside them is uncovered. (2) Transitive through a `final` field **only if** that state was complete before the freeze. (3) Covers *what*, never *whether* — a racy reader may see `null` for ever |
| The two ways the freeze is forfeited | A non-`final` field, and `this` escaping the constructor — both worked in `02c-unsafe-immutables-builders-and-interning.md` §1 |

---

## Self-test

**Q1.** A `record Movement(MovementId id, Money amount, Instant postedAt, List<LedgerEntry> entries)` has a compact constructor whose body is the single line `List.copyOf(entries);`. What does the field hold, and why?

<details><summary>Answer</summary>

The caller's original list. The copy is computed and the result discarded. In a compact constructor the compiler emits the field writes *after* your body, loading each parameter slot — so the only way to change what gets stored is to assign to the parameter name: `entries = List.copyOf(entries);`. The `javap -c -p` difference is a single `astore_2` at offset 8, storing the copy back into the parameter slot that offset 15's `aload_2` then reads. Measured, the no-assignment form reports `class=ArrayList` for the field and shows the caller's later `add`; the assigned form reports `class=List12` and does not. Note also that you cannot write `this.entries = ...` in a compact constructor at all — that is `cannot assign a value to final variable entries`, and being told not to write `this.` is exactly what leads people to drop the assignment rather than move it.

</details>

**Q2.** `String` is the platform's canonical immutable class and it writes to a non-final `int hash` field after construction, from any thread, with no synchronisation. Prove that this does not break immutability, and say precisely which of your legs fails if the cached value were a `long` instead.

<details><summary>Answer</summary>

Three legs. (a) The cached value is a pure function of state that never changes, so every writer computes the same `int`; a reader therefore sees either the sentinel — and recomputes correctly — or that one correct value. No stale-but-different value exists to be seen, which is what makes the race benign. (b) JLS 21 §17.7 grants an atomicity exemption to non-volatile `long` and `double` only; every other type, including `int`, is written and read atomically whether or not it is `volatile`, so no reader can observe a half-written hash. (c) Two threads both missing the cache duplicate the fold and write the same value — a performance loss, not a correctness one.

With a `long`, leg (b) fails outright: the write may be treated as two 32-bit writes, and a reader may see the high half of one and the low half of another, producing a value nobody wrote. The whole argument then collapses, because (a) only guarantees that every *complete* value written is the same. (This is a specification claim, not one demonstrable on typical hardware — a plain-`long` tearing harness on aarch64 produced `reads=376625806 torn=0`, because aarch64 implements aligned 64-bit accesses atomically. The permission exists and must not be relied on as unexercised elsewhere.)

</details>

**Q3.** Why does `String` carry a second field, `hashIsZero`, and what did Java 8 do instead?

<details><summary>Answer</summary>

Because `hash == 0` has to mean "not yet computed" — 0 is what a fresh field holds — but 0 is also a legitimate hash. `"".hashCode()` is 0, and so is `"f5a5a608".hashCode()`, measured. Without a second field, every call on such a string would recompute the entire fold, get 0, store 0 and miss again, for ever. `hashIsZero` distinguishes "not computed" (`hash == 0 && !hashIsZero`) from "computed, and it was zero". The method writes `hash` **or** `hashIsZero`, never both, which is what keeps the pair internally consistent under any interleaving — the JDK's own comment states that restriction explicitly.

`hashIsZero` arrived in **JDK 13** (JDK-8221836). Java 8 through 12 used `if (h == 0 && value.length > 0)`, which handles the empty string by the length test but still recomputes for ever on any non-empty zero-hash string. Both forms are correct; only the second is present in 21.

</details>

**Q4.** `MoneyCache` writes an `ExplicitMoney` — a `final class` with two `private final` fields — into a plain, non-volatile `static` field at startup; 3,400 settlement threads a second read it. What exactly is guaranteed, and what exactly is not?

<details><summary>Answer</summary>

Guaranteed by JLS 21 §17.5: **if** a reader's load returns non-null, the `ExplicitMoney`'s `final` fields — its `amount` and its `currency` — are correctly visible. A freeze action at the end of the constructor forbids the field writes being reordered past the publication of `this`, so a reader that obtains the reference cannot have obtained it before the writes. No `volatile`, no lock and no happens-before edge is needed for that part.

Not guaranteed, three ways. First, any *non-final* field of the `ExplicitMoney` — the freeze covers `final` fields only. Second, the *contents* of a mutable object a `final` field points at, unless those contents were complete before the freeze and are never written again (which `List.copyOf` in the constructor is what makes true). Third — and this is the one that produces production NPEs — **whether the reader sees the write at all**. §17.5 answers *what*, never *whether*; a racy reader may observe `null` indefinitely, so the reader needs a fallback, or the publication needs `volatile`, a lock, or class initialization.

</details>

**Q5.** You want to give `Money` a lazily computed, cached `hashCode` in exactly the shape `String` uses. `Money` is a record. What happens, what does the compiler say, and what are your options?

<details><summary>Answer</summary>

It does not compile. A record body may not declare an instance field at all, and the error names the reason rather than the rule: `field declaration must be static`, with the note `(consider replacing field with record component)`. Not "must be final" — records forbid *all* instance state outside the components, because the components *are* the declared state and an extra field would make that claim false. That is rule 2 arriving in a stronger form than any hand-written class can offer, and §2's cache field is the price of it.

Three options, in order of preference. First, do nothing: a record's generated `hashCode` folds the components' hashes, and for a two-component `Money` over a `BigDecimal` and a `String` that fold is cheap — the O(n) fold that motivates `String`'s cache is over characters, and `Money` has two components, not twenty-one. Second, make the cache `static`: a bounded `Map` from the component tuple to a precomputed hash is legal in a record body, and is a cache with all of §3 of `02c-unsafe-immutables-builders-and-interning.md`'s costs, including being a memory leak if the key space is unbounded. Third, give up the record and hand-write a `final class` with `private final` components plus the `private int hash` / `private boolean hashIsZero` pair — which buys you the cache and costs you the compiler-enforced rules 1, 2 and 3 you reached for the record to get.

</details>

---

## Open questions

- **`long` tearing is not observable on the measurement machine.** JLS 21 §17.7 permits a non-volatile `long` write to be treated as two 32-bit writes, but a three-second harness against a writer alternating `0x0000000000000000` and `0xFFFFFFFFFFFFFFFF` measured `reads=376625806 torn=0` on macOS aarch64, because aarch64 implements aligned 64-bit loads and stores atomically. The claim in §2 is therefore a specification claim, not a measured one. A 32-bit JVM, or a platform without atomic aligned 64-bit access, would settle it empirically.
- **The generated barrier for the §17.5 freeze on aarch64.** §3 marks as unverified the claim that the `StoreStore` the JIT owes before a publishing store is, on aarch64, typically folded into a release-flavoured store (`stlr`) rather than emitted as a standalone `dmb ishst`. Two things would settle it: a `-XX:+PrintAssembly` (or `-XX:CompileCommand=print`) run of the `MoneyCache.warm` publication on this machine, and the OpenJDK aarch64 backend source for the `release_store` / membar nodes. Guide 06 owns both; this file measures neither.

---

**Leaves covered:** 2.3.11, 2.3.12, 2.3.13 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-122 (`../classes-and-initialization/04-internals-final-and-constant-folding.md`) is the adjacent figure for §3, and D-069/D-070 are in `02-immutability.md`
**Target version:** Java 21 LTS
**Lines:** 625
