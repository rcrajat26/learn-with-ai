# 03 Java Core — Value-object builds: the diff against what a `record` gives you for free — BUILD IT (§4.7.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Clock injection and testable time](04f-clock-injection.md) · Next: [The fifteen-snippet puzzler harness](05-diagnostic-harnesses.md)

Five files of §4.7 built `Money`, `MoneyMinor`, `StakeSplit`, `BonusGrant` and `PaymentRun` — every one
a `record`, every one needing hand-written code on top. A `record` is not "an immutable class"; it is a
**shorthand with a fixed set of guarantees**, smaller than the set of things a value object needs.
Three buckets, and the third is where every bug in those five files lived.

| Bucket | Contents | Consequence |
|---|---|---|
| **Given, and specified** | canonical constructor, one accessor per component, `equals`, `toString`, `Class.isRecord`, `getRecordComponents`, deserialization through the canonical constructor, implicit `final`, superclass `java.lang.Record` | you may rely on the semantics, not on the algorithm |
| **Given, deliberately unspecified** | `hashCode`, the precise `equals` algorithm, the exact `toString` text | correct within a run; **not** stable across JVMs or releases |
| **Not given at all** | defensive copy in, copy out, validation, null rejection, cross-component invariants, deep copy, component immutability, currency agreement, scale normalisation | you write all of it, or you ship a mutable "immutable" object |

The language feature itself — declaration forms, record patterns, local records — is guide 04's.

---

## What is generated, and exactly what it means

### Why it exists

Hand-written `equals`, `hashCode` and `toString` rot: a component is added, the six-line `equals` is
not updated, two different `StakeSplit` values compare equal, and a `HashMap` keyed on them collapses
two reservations into one. A record derives all three from the component list, so they cannot drift.

### How it works

`javac` emits `equals`, `hashCode` and `toString` as `final` methods whose entire body is a single
`invokedynamic` to `java.lang.runtime.ObjectMethods.bootstrap`, handing it one direct field-getter
method handle per component. The call site links once (JVMS 6.5) and thereafter runs the method-handle
chain the bootstrap built.

The equality rule is specified. `java.lang.Record`'s `equals` javadoc, `@implSpec` (the parenthetical
naming `Integer` as the wrapper for `int` is dropped here):

```text
<li> If the component is of a reference type, the component is
considered equal if and only if Objects.equals(this.c, r.c)
would return true.

<li> If the component is of a primitive type, using the
corresponding primitive wrapper class PW, the component is
considered equal if and only if PW.compare(this.c, r.c) would
return 0.
```

So a `double` component is compared with `Double.compare(a, b) == 0`, **not** with `==`. JDK 21's
implementation matches, in `java/lang/runtime/ObjectMethods.java`:

```java
private static boolean eq(Object a, Object b) { return a == b; }
private static boolean eq(int a, int b) { return a == b; }
private static boolean eq(long a, long b) { return a == b; }
private static boolean eq(float a, float b) { return Float.compare(a, b) == 0; }
private static boolean eq(double a, double b) { return Double.compare(a, b) == 0; }
```

Read those lines one by one. The `Object` overload is identity — never reached for a component, because
`equalator(Class)` routes non-primitives to `Objects.equals` and only primitives to this table. `int`
and `long` use `==`, agreeing with `Integer.compare(a,b) == 0` on every input. `float` and `double` do
**not**: `Double.compare` orders `NaN` above everything and `-0.0` below `+0.0`, the opposite of `==`.

### Code

`AssessmentService` scores a prospect for affordability into a `double` monthly disposable figure. An
unparsable income declaration yields `NaN`; a tiny negative rounded toward zero yields `-0.0`. Both
reach a dedupe cache keyed on the score.

```java
record AffordabilityScore(double monthlyDisposable, String band) { }

record LimitSet(BigDecimal dailyDeposit, BigDecimal maxStake) { }

static void show(String label, Object value) {
    System.out.printf("%-30s %s%n", label, value);
}

public static void main(String[] args) {
    var unscored1 = new AffordabilityScore(Double.NaN, "WEALTH_REFERRED");
    var unscored2 = new AffordabilityScore(Double.NaN, "WEALTH_REFERRED");
    show("NaN: record equals", unscored1.equals(unscored2));
    show("NaN: == on the components",
            unscored1.monthlyDisposable() == unscored2.monthlyDisposable());
    show("NaN: hashCodes equal", unscored1.hashCode() == unscored2.hashCode());
    var positiveZero = new AffordabilityScore(0.0d, "WEALTH_ACCEPTABLE");
    var negativeZero = new AffordabilityScore(-0.0d, "WEALTH_ACCEPTABLE");
    show("zeroes: record equals", positiveZero.equals(negativeZero));
    show("zeroes: == on components",
            positiveZero.monthlyDisposable() == negativeZero.monthlyDisposable());
    show("zeroes: hashCodes equal", positiveZero.hashCode() == negativeZero.hashCode());
    show("null components: equals",
            new LimitSet(null, null).equals(new LimitSet(null, null)));
    show("500.00 versus 500.0", new LimitSet(new BigDecimal("500.00"), new BigDecimal("25.00"))
            .equals(new LimitSet(new BigDecimal("500.0"), new BigDecimal("25.0"))));
    var score = new AffordabilityScore(1850.75d, "WEALTH_ACCEPTABLE");
    int folded = 0;
    folded = folded * 31 + Double.hashCode(score.monthlyDisposable());
    folded = folded * 31 + Objects.hashCode(score.band());
    show("record hashCode", score.hashCode());
    show("31-fold from zero", folded);
    show("identical", score.hashCode() == folded);
    show("toString shape",
            new LimitSet(new BigDecimal("500.00"), new BigDecimal("25.00")));
}
```

Real output, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245), macOS aarch64:

```console
NaN: record equals             true
NaN: == on the components      false
NaN: hashCodes equal           true
zeroes: record equals          false
zeroes: == on components       true
zeroes: hashCodes equal        false
null components: equals        true
500.00 versus 500.0            false
record hashCode                1765406516
31-fold from zero              1765406516
identical                      true
toString shape                 LimitSet[dailyDeposit=500.00, maxStake=25.00]
```

Two `NaN` scores are equal as records and unequal as `double`s; `+0.0` and `-0.0` are unequal as records
and equal as `double`s. The dedupe cache therefore folds every unscorable prospect into one entry and
splits zero-disposable prospects into two. `500.00` against `500.0` is `false` because the component
comparison is `BigDecimal.equals`, which includes scale — order 21's scale pinning is what makes a
record's generated `equals` usable for money at all.

`hashCode` is a plain fold, `h = h * 31 + Objects.hashCode(component)` from zero — the block above
reproduces `1765406516` exactly. That is `makeHashCode` in `ObjectMethods`, **an observed
implementation detail, not a promise**. The javadoc says so:

```text
The precise algorithm used in the implicitly provided implementation
is unspecified and is subject to change within the above limits.
The resulting integer need not remain consistent from one
execution of an application to another execution of the same
application, even if the hashes of the component values were to
remain consistent in this way.
```

**Pitfall:** persisting a record's `hashCode` as a shard key, dedupe column or cache filename. The
symptom is a mis-sharded lookup after a JDK upgrade, with no error anywhere; the fix is under
`## Pitfalls` below.

### The generated members read fields, not accessors

Non-obvious, and it decides whether an accessor override is safe.

```java
record StakeReservation(long units) {
    @Override public long units() { return -999L; }
}

public static void main(String[] args) {
    var reservation = new StakeReservation(420L);
    System.out.println("accessor            = " + reservation.units());
    System.out.println("toString            = " + reservation);
    System.out.println("hashCode            = " + reservation.hashCode());
    System.out.println("Long.hashCode(420)  = " + Long.hashCode(420L));
    System.out.println("Long.hashCode(-999) = " + Long.hashCode(-999L));
    System.out.println("equals a fresh 420  = " + reservation.equals(new StakeReservation(420L)));
}
```

```console
accessor            = -999
toString            = StakeReservation[units=420]
hashCode            = 420
Long.hashCode(420)  = 420
Long.hashCode(-999) = 998
equals a fresh 420  = true
```

`javap -v -p` explains it — the bootstrap's method-handle arguments are field reads:

```text
final class AccessorOverrideProbe$StakeReservation extends java.lang.Record {
  private final long units;

  public final int hashCode();
    Code:
       0: aload_0
       1: invokedynamic #19,  0             // InvokeDynamic #0:hashCode:(LAccessorOverrideProbe$StakeReservation;)I
       6: ireturn

  #43 = MethodHandle       1:#7   // REF_getField AccessorOverrideProbe$StakeReservation.units:J
  #44 = MethodHandle       6:#45  // REF_invokeStatic java/lang/runtime/ObjectMethods.bootstrap
```

`REF_getField`, not `REF_invokeVirtual`. **Insight:** this makes order 23's copy-out accessor override
free — the copy runs only when a caller reads the component, so a record in a `HashMap` does not
allocate a `Date` per lookup. It is also the hazard: an accessor that *normalises* rather than copies
disagrees with `equals`. Keep an override to copying only.

> **A record's generated members are a fixed, component-derived contract computed from the fields:
> semantics you may rely on, an algorithm you may not.**

---

## Serialization: the one thing a record does strictly better

### Why it exists

Order 24 showed the ordinary-class hazard: `readObject` reconstructs an object without running any
constructor, so every invariant a constructor enforces is bypassed on the deserialization path, and a
`transient` field silently arrives as its default. Hence the serialization proxy, or a hand-written
`readObject` repeating the validation.

### How it works

A record's serial form is **restricted**: the stream carries the component values, and deserialization
reconstructs the object by invoking the **canonical constructor** with them. There is no field-poking
path, so a compact constructor's validation runs on read.

### Code

The same tampering attack against both shapes. `StakeSplitMinor` is `StakeSplit` in minor units: the
canonical bonus split of a **3.33** stake is 33 bonus units + 300 cash units, and the invariant is that
the bonus portion never exceeds the rounded-down 10%. The attack rewrites the serialized `33` to `34`.

```java
/** The domain rule, shared so the record and the class enforce exactly the same thing. */
static void check(String who, long bonusUnits, long cashUnits) {
    System.out.println("   [" + who + " constructor ran: bonus=" + bonusUnits
            + " cash=" + cashUnits + "]");
    long ceiling = (bonusUnits + cashUnits) / 10;
    if (bonusUnits > ceiling) {
        throw new IllegalArgumentException("bonus " + bonusUnits
                + " exceeds the rounded-down 10% of stake " + (bonusUnits + cashUnits)
                + " (" + ceiling + "): this split creates money");
    }
}

record StakeSplitMinor(long bonusUnits, long cashUnits) implements Serializable {
    StakeSplitMinor { check("canonical", bonusUnits, cashUnits); }
}

static final class StakeSplitMinorPlain implements Serializable {
    private static final long serialVersionUID = 1L;
    private final long bonusUnits;
    private final long cashUnits;
    StakeSplitMinorPlain(long bonusUnits, long cashUnits) {
        check("class", bonusUnits, cashUnits);
        this.bonusUnits = bonusUnits;
        this.cashUnits = cashUnits;
    }
    @Override public String toString() {
        return "StakeSplitMinorPlain[bonusUnits=" + bonusUnits
                + ", cashUnits=" + cashUnits + "]";
    }
}

// Does a record's readObject run? Does readResolve?
record BonusExpiryWindow(int days) implements Serializable {
    private void readObject(ObjectInputStream in) throws IOException {
        throw new AssertionError("a record's readObject was invoked");
    }
    private Object readResolve() {
        System.out.println("   [readResolve ran, replacing " + days + " with 30]");
        return new BonusExpiryWindow(30);
    }
}

static byte[] write(Object o) throws IOException {
    var bytes = new ByteArrayOutputStream();
    try (var out = new ObjectOutputStream(bytes)) { out.writeObject(o); }
    return bytes.toByteArray();
}

static Object read(byte[] b) throws Exception {
    try (var in = new ObjectInputStream(new ByteArrayInputStream(b))) { return in.readObject(); }
}

/** Rewrite the last byte of the first big-endian 8-byte long equal to `from`. */
static byte[] tamper(byte[] stream, int from, int to) {
    for (int i = 7; i < stream.length; i++) {
        if (stream[i] == from && stream[i - 1] == 0 && stream[i - 7] == 0) {
            byte[] copy = stream.clone();
            copy[i] = (byte) to;
            System.out.printf("   [patched byte at offset %d: 0x%02x -> 0x%02x]%n", i, from, to);
            return copy;
        }
    }
    throw new IllegalStateException("no long equal to " + from + " in the stream");
}

static long uid(Class<?> c) { return ObjectStreamClass.lookup(c).getSerialVersionUID(); }

public static void main(String[] args) throws Exception {
    System.out.println("serialVersionUID: record=" + uid(StakeSplitMinor.class)
            + "  class(declared 1L)=" + uid(StakeSplitMinorPlain.class)
            + "  BonusExpiryWindow=" + uid(BonusExpiryWindow.class));

    System.out.println("write a valid 33-bonus + 300-cash split, both shapes:");
    byte[] recordStream = write(new StakeSplitMinor(33L, 300L));
    byte[] classStream = write(new StakeSplitMinorPlain(33L, 300L));
    System.out.println("   stream lengths: record=" + recordStream.length
            + "B class=" + classStream.length + "B");

    System.out.println("tamper 33 -> 34, which makes the split create money:");
    byte[] tamperedRecord = tamper(recordStream, 33, 34);
    byte[] tamperedClass = tamper(classStream, 33, 34);

    System.out.println("read the tampered ordinary class:");
    System.out.println("   " + read(tamperedClass) + "   <-- invariant bypassed");

    System.out.println("read the tampered record:");
    try {
        System.out.println("   " + read(tamperedRecord));
    } catch (Exception e) {
        System.out.println("   " + e.getClass().getName() + ": " + e.getMessage()
                + "\n   caused by " + e.getCause().getClass().getName());
    }

    System.out.println("readObject ignored, readResolve honoured:");
    System.out.println("   read back: " + read(write(new BonusExpiryWindow(99))));
}
```

```console
serialVersionUID: record=0  class(declared 1L)=1  BonusExpiryWindow=0
write a valid 33-bonus + 300-cash split, both shapes:
   [canonical constructor ran: bonus=33 cash=300]
   [class constructor ran: bonus=33 cash=300]
   stream lengths: record=94B class=99B
tamper 33 -> 34, which makes the split create money:
   [patched byte at offset 85: 0x21 -> 0x22]
   [patched byte at offset 90: 0x21 -> 0x22]
read the tampered ordinary class:
   StakeSplitMinorPlain[bonusUnits=34, cashUnits=300]   <-- invariant bypassed
read the tampered record:
   [canonical constructor ran: bonus=34 cash=300]
   java.io.InvalidObjectException: bonus 34 exceeds the rounded-down 10% of stake 334 (33): this split creates money
   caused by java.lang.IllegalArgumentException
readObject ignored, readResolve honoured:
   [readResolve ran, replacing 99 with 30]
   read back: BonusExpiryWindow[days=30]
```

Read the trace, not the summary. On the class path there is **no** `[class constructor ran: bonus=34]`
line — deserialization produced an object whose constructor never executed, holding a split that creates
a penny. On the record path the canonical constructor did run, with the tampered values, and threw.

Three further facts. A record's undeclared `serialVersionUID` is **0**, so the "adding a field changes
the computed UID and breaks old streams" reflex does not transfer; declaring it explicitly is still the
disciplined choice. `readObject` is **ignored** — the `AssertionError` it throws never fires.
`readResolve` is **honoured** — the 99-day window came back as the domain's 30-day bonus expiry.

**Interview:** "Strongest argument for making a domain value object a record?" — deserialization goes
through the canonical constructor, so invariants cannot be bypassed by a crafted stream, which for an
ordinary class needs a serialization proxy.

> **A record's serial form is restricted to its components and rebuilt through the canonical
> constructor, so validation is unbypassable on read; `readObject` is ignored, `readResolve` is not.**

---

## Thread safety, layout, and cost

**Thread safety.** A record's fields are `final`, so a fully constructed record whose components are
all immutable is safely publishable: the final-field freeze at the end of the constructor guarantees
that any thread reading the reference sees the fields fully written, with no synchronisation. A record
with a **mutable** component gives you nothing here — `final` freezes the reference, not the interior,
so `stakeSettlementWorker` can observe a half-populated `ArrayList` reachable through an "immutable"
record. Safe publication is
[`../immutability-and-design/02-immutability.md`](../immutability-and-design/02-immutability.md)'s; the
memory model is guide 05's.

**Layout.** A record is an ordinary class: the `javap` output above shows `extends java.lang.Record`
and `private final long units`, nothing else. No flattening, no special layout, no runtime reflection,
no wrapper. Project Valhalla's value classes would alter this; in 21 there is none.

Measured with the house method — `getThreadAllocatedBytes` deltas over 2,800,000 iterations (one day
of stake reservations) after a 200,000-iteration warm-up, Oracle JDK 21.0.7 (build 21.0.7+8-LTS-245),
macOS aarch64, compressed oops on:

```console
=== -XX:-DoEscapeAnalysis ===
BigDecimal.valueOf(333, 2) alone                40 B/iteration
new BigDecimal("3.33") alone (parses a char[])  64 B/iteration
Money, basis = a pre-built BigDecimal           24 B/iteration
Money, basis = a fresh BigDecimal per call      88 B/iteration
MoneyMinor(long, Currency) record               24 B/iteration
MoneyMinorPlain(long, Currency) final class     24 B/iteration
```

The arithmetic, explicitly. `MoneyMinor` is a 12-byte header + `long units` 8 + compressed `Currency`
reference 4 = 24 B exactly, and the hand-written `final class` with the same two fields measures the
same 24 B — **a record costs nothing over the class you would have written**. `Money` is a 24-byte
record shell plus its `BigDecimal`: 24 + 40 = **64 B** on a `BigDecimal.valueOf` basis, order 22's
figure, and 24 + 64 = **88 B** when the `BigDecimal` is parsed from a `String`, because
`new BigDecimal(String)` also allocates a `char[4]`. Both JIT configurations reported identical
numbers, because the harness's `volatile Object sink` makes every object genuinely escape, so
`-XX:-DoEscapeAnalysis` changes nothing when the escape is real. **This is not JMH**: no forking, no
`Blackhole`, allocation counting only, and the canonical harness is
[`../cost-model/02-master-cost-table.md`](../cost-model/02-master-cost-table.md)'s.

---

## Eligibility: what the compiler simply refuses

Each of these is a real `javac` 21 error, one file per case:

| You wanted | `javac` 21 says | Where it bites |
|---|---|---|
| an extra instance field | `error: field declaration must be static`, then `(consider replacing field with record component)` | a cached derived value, such as `Money` memoising its minor units — make it a method, or a `static` cache keyed on the record |
| to extend a class | `error: '{' expected`, pointing at `extends` | `MovementRecord extends LedgerEntry` is not expressible; a record's superclass is always `java.lang.Record`. Use a sealed interface for the hierarchy instead |
| to subclass a record | `error: cannot inherit from final ParentReservation` | records are implicitly `final`: no partial mocking, no proxy subclass, so a CGLIB-style AOP proxy over a record is impossible |
| a no-arg constructor | `error: constructor is not canonical, so its first statement must invoke another constructor of class NoArgCtor` | JPA and reflective binders want a no-arg constructor plus setters. `NoArgCtor() { this(0L); }` compiles — but a *setter* never will |
| to reassign a component | `error: cannot assign a value to final variable units` | no mutable state at all, which is why a record is wrong for a JPA `@Entity`; guide 08 owns that |
| to hide a component | no error — a public accessor is generated unconditionally | a record cannot have a private component. If a field must not be exposed, the type is not a record |

The last row has no compile error and decides most designs: **every** component of a record is public
API, forever. Nor can a record be a builder target, which is why order 8's builder is a companion class.

---

## The diff table

Seven axes, as Part 4 requires, in two grids because the halves answer different questions.

### What a record gives you

| Member | Edge cases | Intrinsics | Serialization | Null policy | Thread safety | Allocation tricks | Why the JDK bothers |
|---|---|---|---|---|---|---|---|
| **Canonical constructor** | always generated unless declared; a compact constructor's parameter assignments become the field writes | no intrinsic; a plain `<init>` doing one `putfield` per component after `Record.<init>` | **is** the deserialization entry point, so validation is unbypassable | none — accepts `null` in any reference component silently | fields are `final`, so it gets the final-field freeze | none; ordinary allocation | the field-assignment boilerplate is 100% derivable from the component list |
| **Accessors** | one per component, `public`, named exactly as the component; overridable | no intrinsic; a one-line `getfield` that C2 inlines like any getter | not involved — the serial form reads fields | returns the field as-is, `null` included | safe from any thread on an immutable component | none; **but** a copying override costs nothing on `equals`/`hashCode`/`toString`, which read fields (`REF_getField`) | naming and visibility are mechanical, and frameworks need a predictable accessor name |
| **`equals`** | `Objects.equals` per reference component, `PW.compare(a,b) == 0` per primitive: `NaN` equals `NaN`, `+0.0` does not equal `-0.0` | no intrinsic; `invokedynamic` to `ObjectMethods.bootstrap`, linked once per call site | not involved | null-safe by construction | pure read of `final` fields | the method-handle chain is built once at first execution, then reused | a hand-written `equals` rots the moment a component is added |
| **`hashCode`** | **algorithm unspecified**; JDK 21's observed fold is `h*31 + Objects.hashCode(c)` from 0 | no intrinsic; same bootstrap | not involved; never persist it | null-safe (`Objects.hashCode`) | pure read; **not** cached, unlike `String.hash` | none; no memoised hash field, so a record used as a hot `HashMap` key recomputes on every lookup | consistency with the refined `equals` contract is the only promise worth making |
| **`toString`** | `Name[c1=v1, c2=v2]`, component order as declared | no intrinsic; `invokedynamic`, and the bootstrap builds a `StringConcatFactory` chain | not involved | prints the four characters `null` | pure read | the concatenation shape is built once at link time | debuggability, and a documented format rather than an object hash |
| **`isRecord` / `getRecordComponents`** | reflects the class file's `Record` attribute; `getGenericType` retains `List<String>` where `getType` gives erased `List` | not an intrinsic; ordinary reflection | frameworks use it to find the canonical constructor for binding | throws nothing; an empty array for a non-record | thread-safe reads of class metadata | none | canonical-constructor binding needs the component list in declaration order, which no other reflection API gives |

### What a record does not give you — the rows that matter

| Missing guarantee | Edge cases | Intrinsics | Serialization | Null policy | Thread safety | Allocation tricks | Why the JDK does not do it |
|---|---|---|---|---|---|---|---|
| **Defensive copy in** (order 23) | the canonical constructor stores the reference it was handed: `Date`, `List`, `byte[]`, any aggregate | no intrinsic | the copy runs on read too, because deserialization uses the same constructor — one fix covers both paths | must `requireNonNull` before copying, or the copy throws `NullPointerException` | absent: `final` freezes the reference, not the interior | put the copy in the compact constructor; `List.copyOf` returns its argument unchanged when already immutable | the compiler cannot know which components are mutable, and copying every reference would be both wrong and expensive |
| **Copy out of the accessor** | the generated accessor returns the field; the caller can then mutate your state | no intrinsic | not involved | returns `null` if the component is `null` | absent | free relative to `equals`/`hashCode`, which use field getters, so only real reads pay | same reason; an unconditional copy would destroy `record` as a cheap carrier type |
| **Validation** (order 21) | scale from `Currency.getDefaultFractionDigits()`, and the `-1` pseudo-currency case | no intrinsic | re-runs on deserialization; **the record's one clear win** | you write the `requireNonNull` | none needed | none | domain rules are not derivable from types |
| **Null rejection** | `new Money(null, gbp)` compiles and, with no compact constructor, succeeds | no intrinsic | a stream can carry `null` for any reference component | entirely yours; `Objects.requireNonNull` naming the component | none | none | `null` is a legal value of every reference type; a blanket ban would exclude legitimate optional components |
| **Cross-component invariants** (order 21's `StakeSplit`) | the bonus portion must not exceed the rounded-down 10% | no intrinsic | re-checked on read | reject nulls first, then compare | none | none — but modelling `stake()` as the *sum* rather than a third component discharges the invariant structurally, free | the compiler has no vocabulary for a relation between components |
| **Deep copy** (order 24) | a nested graph, shared nodes, cycles; needs an `IdentityHashMap` seen-map | no intrinsic | a serialization round-trip deep-copies, but bypasses the constructor for classes and loses `transient` fields | each node's nulls are yours | absent | none; a deep copy is the expensive option, which is why the shallow-copy limit matters | unbounded, type-specific, and often wrong |
| **Component immutability** | shallow, always: `record PaymentRun(String runId, List<String> withdrawalIds)` is mutable if the list is | no intrinsic | not involved | not involved | absent | none | Java cannot express "this type is deeply immutable" |

`no intrinsic` is the true answer on that axis for every row in both tables: nothing about records is
intrinsified in HotSpot 21. The only runtime machinery is `invokedynamic` linkage, once per call site.

---

## The decision, as a rule you could apply

**A record is right when the type *is* its components and every component is immutable.** `Money` is
its amount and currency; `StakeSplit` is its two portions; `ClientId` is its `UUID`. Nothing to hide,
nothing to mutate, no supertype to extend, and the generated `equals` is the equality the domain wants.

**A plain `final` class is right when any one of these holds:** a component must be hidden; a mutable
component must be held and you would rather not copy it on every read; the type must extend something;
or the public API differs from the component list. Two QuizStakes types either side of that line:

```java
// Record: the type IS its components.
record RestrictionKey(RestrictionType type, RestrictionSource source) { }
```

Restriction identity is the pair `(type, source)` — `STAKE_BLOCKED` from `SYSTEM_ONBOARDING` lifts
automatically at `AA-801`, the same type from `ADMIN` does not. Both components are enums, so
immutable; both are public API by definition; and the generated `equals` is precisely the key semantics
a `Map<RestrictionKey, Restriction>` needs.

```java
// Plain final class: the public API is not the component list.
final class PaymentRun {
    private final String runId;
    private final List<String> withdrawalIds;
    private final byte[] operatorSignature;   // must never be handed out

    PaymentRun(String runId, List<String> withdrawalIds, byte[] operatorSignature) {
        this.runId = Objects.requireNonNull(runId, "PaymentRun.runId is null");
        this.withdrawalIds = List.copyOf(withdrawalIds);
        this.operatorSignature = operatorSignature.clone();
    }

    String runId() { return runId; }
    List<String> withdrawalIds() { return withdrawalIds; }
    boolean signedBy(byte[] candidate) { return Arrays.equals(operatorSignature, candidate); }
}
```

The sign-off signature is state the type must hold and never expose: the API is `signedBy(byte[])`, a
predicate, not `operatorSignature()`. A record cannot express that, and a generated `equals` over a
`byte[]` component would compare it by identity through `Objects.equals`, wrong for a signature.

---

## `Money`, with every gap closed

The constructive payoff: `Money` with all of §4.7's obligations discharged, plus `BonusGrant` on top,
because `Money`'s own components are immutable and so have no copy to demonstrate. `BonusGrant` carries
the mutable pair, a `Date` and a `List<String>`. `ClientId` is order 23's restatement, unchanged.

```java
// Validation, pseudo-currency rejection, scale enforcement, null rejection, and a
// normalising static factory alongside the canonical constructor. No accessor override:
// BigDecimal and Currency are immutable, so there is nothing to copy out.
record Money(BigDecimal amount, Currency currency) implements Comparable<Money> {

    Money {
        Objects.requireNonNull(amount, "Money.amount is null");
        Objects.requireNonNull(currency, "Money.currency is null");
        int digits = currency.getDefaultFractionDigits();
        if (digits < 0) {
            throw new IllegalArgumentException(
                    "Money cannot represent pseudo-currency " + currency.getCurrencyCode()
                    + ": getDefaultFractionDigits() returned " + digits);
        }
        if (amount.scale() != digits) {
            throw new IllegalArgumentException(
                    "Money in " + currency.getCurrencyCode() + " requires scale " + digits
                    + " but was handed scale " + amount.scale() + " (" + amount + ")");
        }
    }

    static Money of(String amount, Currency currency) {
        Objects.requireNonNull(amount, "Money.of amount text is null");
        Objects.requireNonNull(currency, "Money.of currency is null");
        return new Money(new BigDecimal(amount), currency);
    }

    static Money normalising(BigDecimal raw, Currency currency, RoundingMode mode) {
        Objects.requireNonNull(raw, "Money.normalising raw is null");
        Objects.requireNonNull(currency, "Money.normalising currency is null");
        Objects.requireNonNull(mode, "Money.normalising mode is null");
        int digits = currency.getDefaultFractionDigits();
        if (digits < 0) {
            throw new IllegalArgumentException(
                    "Money cannot represent pseudo-currency " + currency.getCurrencyCode());
        }
        return new Money(raw.setScale(digits, mode), currency);
    }

    @Override public int compareTo(Money other) {
        if (!currency.equals(other.currency)) {
            throw new IllegalArgumentException("cannot compareTo "
                    + other.currency.getCurrencyCode() + " and " + currency.getCurrencyCode());
        }
        return amount.compareTo(other.amount);
    }

    @Override public String toString() {
        return amount.toPlainString() + " " + currency.getCurrencyCode();
    }
}

// The leaky version, for contrast: two mutable components, no compact constructor.
record BonusGrantLeaky(ClientId clientId, Money amount, Date grantedAt,
                       List<String> couponCodes) { }

// The closed version: copy in, copy out, validate, and a static factory carrying the
// 10%-capped-at-100 grant rule.
record BonusGrant(ClientId clientId, Money amount, Date grantedAt,
                  List<String> couponCodes) {

    BonusGrant {
        Objects.requireNonNull(clientId, "BonusGrant.clientId is null");
        Objects.requireNonNull(amount, "BonusGrant.amount is null");
        Objects.requireNonNull(grantedAt, "BonusGrant.grantedAt is null");
        Objects.requireNonNull(couponCodes, "BonusGrant.couponCodes is null");
        if (amount.compareTo(Money.of("100.00", amount.currency())) > 0) {
            throw new IllegalArgumentException(
                    "BonusGrant.amount " + amount + " exceeds the 100 cap");
        }
        grantedAt = new Date(grantedAt.getTime());     // copy in
        couponCodes = List.copyOf(couponCodes);        // copy in, and unmodifiable
    }

    @Override public Date grantedAt() {
        return new Date(grantedAt.getTime());          // copy out
    }

    Date expiresAt() {
        return new Date(grantedAt.getTime() + java.time.Duration.ofDays(30).toMillis());
    }

    static BonusGrant granted(ClientId clientId, Money deposit, Date at, List<String> coupons) {
        Money tenPercent = Money.normalising(
                deposit.amount().multiply(new BigDecimal("0.10")),
                deposit.currency(), RoundingMode.DOWN);
        Money cap = Money.of("100.00", deposit.currency());
        return new BonusGrant(clientId, tenPercent.compareTo(cap) > 0 ? cap : tenPercent,
                at, coupons);
    }

    @Override public String toString() {
        return "BonusGrant[" + clientId + ", " + amount + ", grantedAt="
                + grantedAt.getTime() + ", expiresAt=" + expiresAt().getTime()
                + ", couponCodes=" + couponCodes + "]";
    }
}
```

The driver builds one of each from a `Date` at epoch millisecond `1700000000000` and a mutable
`ArrayList` holding `WELCOME10`, then runs four attacks: mutate the caller's `Date`, add to the
caller's list, `setTime` on whatever the accessor returns, and `add` on whatever the accessor returns.

```console
-- a record with mutable components leaks both ways --
after construction  : grantedAt=1700000000000 coupons=[WELCOME10]
caller mutated its own references, nothing called on the record
now                 : grantedAt=1600000000000 coupons=[WELCOME10, STAFF_ONLY]
via the accessors   : grantedAt=1500000000000 coupons=[WELCOME10, STAFF_ONLY, VIA_ACCESSOR]

-- the closed version refuses both --
after construction  : BonusGrant[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], 42.00 GBP, grantedAt=1700000000000, expiresAt=1702592000000, couponCodes=[WELCOME10]]
after caller mutate : BonusGrant[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], 42.00 GBP, grantedAt=1700000000000, expiresAt=1702592000000, couponCodes=[WELCOME10]]
after accessor stab : BonusGrant[ClientId[8f14e45f-ceea-467a-9e2b-1c3d4a5b6c70], 42.00 GBP, grantedAt=1700000000000, expiresAt=1702592000000, couponCodes=[WELCOME10]]
couponCodes().add() -> java.lang.UnsupportedOperationException
grant of 10% of 420.00 capped at 100 = 42.00 GBP
grant of 10% of 3400.00              = 100.00 GBP

-- equals still works after the accessor override --
equals              = true
hashCodes equal     = true
copy via accessors equals the original = true
```

The leaky record's grant timestamp moved twice with no mutating method existing on the type; the closed
one is unmoved by all four attacks. The last line is the `Record.equals` javadoc's copy requirement
holding under the accessor override: passing each accessor's result back into the canonical constructor
still yields an equal record, because the copy-out accessor returns an equal `Date`, not the same one.

**Gotcha:** the copying accessor and `toString` cannot diverge here, because the generated `toString`
would also read the field — but they would under a normalising override.

### Diff vs the real one

There is no `Money` in the JDK, so the comparison is against the two JDK types this build is made of.

| Axis | `Money` as built here | `java.math.BigDecimal` | `java.util.Currency` |
|---|---|---|---|
| Edge cases | rejects wrong scale, pseudo-currency, mixed-currency `compareTo` | negative scales legal, `2.00` unequal to `2.0`, ordering inconsistent with `equals` | `getDefaultFractionDigits()` returns **−1** for `XAU`, `XDR` and the other pseudo-currencies; ISO 4217 codes only |
| Intrinsics | none | none for `add`; `BigInteger.multiplyToLen` has one, reached only on the inflated path | none |
| Serialization | record serial form; canonical constructor re-runs every check on read | a hand-written `readObject` that calls `readFields`, throws `StreamCorruptedException` on a missing `intVal`, and installs the fields through an `UnsafeHolder` — the constructor never runs | a `readResolve` returning `getInstance(currencyCode)`, so identity survives a round trip |
| Null policy | `Objects.requireNonNull` naming the component | `NullPointerException`, component unnamed | `getInstance(null)` throws `NullPointerException` |
| Thread safety | immutable; both components immutable; safely published by final fields | immutable, but the `stringCache` field is a benign non-`volatile` race | immutable, and instances are interned per currency code |
| Allocation tricks | none; a 24 B shell, 64 B with a `valueOf`-built `BigDecimal`, 88 B with a `String`-parsed one | `intCompact` keeps small values in a `long` and skips the `BigInteger`; `INFLATED = Long.MIN_VALUE` is the sentinel | interned: one instance per code, so a `Currency` reference costs 4 B and no allocation |
| Why the JDK bothers | it does not — the JDK ships arbitrary-precision arithmetic and an ISO code table and stops, which is why every payments codebase grows this type | correctness of decimal arithmetic is a language-library obligation | the ISO 4217 table with its fraction digits has to live somewhere, and interning makes currency comparison a pointer compare |

`BigDecimal`'s field set and `intCompact` are
[`../numbers-and-money/03-internals-bigdecimal.md`](../numbers-and-money/03-internals-bigdecimal.md)'s.
**Unverified:** whether JSR-354 (`javax.money`) specifies its serial form, null policy or equality rule
— Moneta is not on this machine, so nothing about `MonetaryAmount` is asserted here.

---

## Pitfalls

### Believing a record is immutable regardless of its components

**Wrong**

```java
record PaymentRunLeaky(String runId, List<String> withdrawalIds) { }

List<String> ids = new ArrayList<>(List.of("BW-1", "BW-2"));
var run = new PaymentRunLeaky("PR-2026-08-29", ids);
ids.add("BW-3");
run.withdrawalIds().add("BW-4");
System.out.println("leaky : " + run.withdrawalIds());
```

```console
leaky : [BW-1, BW-2, BW-3, BW-4]
```

A `PaymentRun` that went to the operator for sign-off with two withdrawals now carries four, and no
method on the record was called.

**Right**

```java
record PaymentRunCopyOf(String runId, List<String> withdrawalIds) {
    PaymentRunCopyOf {
        Objects.requireNonNull(runId, "PaymentRun.runId is null");
        withdrawalIds = List.copyOf(withdrawalIds);
    }
}
```

```console
copyOf: [BW-1, BW-2]
```

`List.copyOf` snapshots the caller's list and returns an unmodifiable view, so one line closes copy-in
and copy-out — and because deserialization runs the same constructor, the stream path too.

**Why people believe it:** the fields genuinely are `final`, the class genuinely is `final`, there are
no setters, and every immutability checklist scores that as immutable. The checklist is about the fence
posts; the component is the gap in the fence.

### Persisting a record's `hashCode`

**Wrong**

```java
record RestrictionKey(RestrictionType type, RestrictionSource source) { }

int shard = Math.abs(new RestrictionKey(RestrictionType.STAKE_BLOCKED,
        RestrictionSource.SYSTEM_ONBOARDING).hashCode()) % 16;
// stored in the restrictions table as shard_id, and used to route reads
```

Stable within a run and across runs on this JDK, which is what makes it dangerous: the bug appears only
after a JDK upgrade, as reads routed to a shard where nothing was written, with no exception anywhere.

**Right**

```java
static int shardOf(RestrictionKey key) {
    return Math.floorMod(
            (key.type().name() + '|' + key.source().name()).hashCode(), 16);
}
```

```console
shardOf(key) = 6
```

`String.hashCode` **is** specified, as `s[0]*31^(n-1)` plus each remaining character times its own power
of 31, so a key derived from the component names is reproducible across JVMs and releases. `floorMod`
rather than `Math.abs`, because `Math.abs(Integer.MIN_VALUE)` is negative.

**Why people believe it:** the value looks like a hash function's output, and hash functions are
normally stable. `Record`'s javadoc says the opposite: the algorithm "is unspecified and is subject to
change", and the result "need not remain consistent from one execution of an application to another".

### Expecting `readObject` to bypass a record's validation

**Wrong** — "add a `readObject` to `StakeSplitMinor` to relax the check for legacy streams":

```java
private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
    in.defaultReadObject();
}
```

It compiles, is never called, and the compact constructor rejects the legacy stream anyway. A
`readResolve` does not help either — re-running the tamper against a `StakeSplitMinor` that declares one
printing `[readResolve reached]` produces no such line, because the constructor throws first:

```console
patched offset 74 from 33 to 34
reading the tampered stream of a record that HAS readResolve:
   java.io.InvalidObjectException: bonus 34 exceeds the rounded-down 10% of stake 334 (33): this split creates money
```

**Right** — read the legacy stream into a tolerant carrier and convert:

```java
// The wire shape: no invariant, so any legacy stream loads.
record StakeSplitMinorWire(long bonusUnits, long cashUnits) implements Serializable {
    StakeSplitMinor repaired() {
        long stake = bonusUnits + cashUnits;
        long ceiling = stake / 10;
        long bonus = Math.min(bonusUnits, ceiling);
        return new StakeSplitMinor(bonus, stake - bonus);
    }
}
```

```console
wire repair of 34/300 = StakeSplitMinor[bonusUnits=33, cashUnits=301]
wire repair of 33/300 = StakeSplitMinor[bonusUnits=33, cashUnits=300]
```

The repair clamps the bonus and gives the penny to cash, so the stake is preserved, and `repaired()` is
the single place the migration rule lives.

**Why people believe it:** for an ordinary class `readObject` *is* the deserialization path and does
bypass the constructor, as the output earlier shows for `StakeSplitMinorPlain`. Everything a reader
knows about `Serializable` was learned on ordinary classes, and records changed the rule.

### Trusting a record's accessor to return a copy

**Wrong**

```java
Date when = grantLeaky.grantedAt();
when.setTime(0L);                      // "it is my own copy"
System.out.println(grantLeaky.grantedAt().getTime());   // prints 0
```

The bonus is `EXPIRED` as of 1970 and reverses to `PROMOTIONAL_EXPENSE`; the `via the accessors` line
of the worked example's output is this attack landing.

**Right**

```java
@Override public Date grantedAt() {
    return new Date(grantedAt.getTime());
}
```

Cheap, because the generated members read the field through `REF_getField` handles, so the copy runs
only on a genuine read.

**Why people believe it:** the accessor is generated, generated code is assumed correct, and the record
is described everywhere as immutable. The generated accessor is `return this.f;` and nothing more.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Generated members | canonical constructor, one public accessor per component, `final` `equals`/`hashCode`/`toString` |
| `equals` on a reference component | `Objects.equals`, null-safe |
| `equals` on a primitive component | `PW.compare(a,b) == 0`; so `NaN` equals `NaN` is **true**, `+0.0` equals `-0.0` is **false** |
| `hashCode` algorithm | unspecified; JDK 21's observed fold is `h*31 + Objects.hashCode(c)` from 0. Never persist it |
| Where the members live | one `invokedynamic` to `java.lang.runtime.ObjectMethods.bootstrap`, linked once per call site |
| Do generated members call the accessor? | No — `REF_getField` handles read the fields, so an accessor override does not affect them |
| Deserialization | goes through the canonical constructor; validation cannot be bypassed |
| `readObject` / `readResolve` on a record | ignored / honoured, but only after the canonical constructor has accepted the values. Undeclared `serialVersionUID` is `0` |
| Copy in, copy out, validate, null-reject, deep copy | none of it is generated; all of it is the compact constructor's and an accessor override's job |
| Immutability | shallow only, always |
| Footprint | ordinary class, `final` fields, no flattening. `MoneyMinor` 24 B, identical to the hand-written class; `Money` 24 + 40 = 64 B |
| Cannot | extend a class, be subclassed, add an instance field, mutate, hide a component, be a JPA entity |
| Can | implement interfaces, declare static members and instance methods, override an accessor, declare a delegating no-arg constructor, be generic, implement a sealed interface |
| Right for a value object when | the type **is** its components and every component is immutable |
| Wrong when | a component must be hidden, held mutable, or the public API differs from the component list |

---

## Self-test

**Q1.** A record has one `double` component. Two instances both hold `Double.NaN`. Are they `equals`? What about `+0.0` and `-0.0`?

<details><summary>Answer</summary>

`NaN` instances are equal; `+0.0` and `-0.0` are not. The `Record.equals` javadoc specifies that a primitive component is compared with `PW.compare(a, b) == 0`, and JDK 21's `ObjectMethods.eq(double, double)` is literally `Double.compare(a, b) == 0`. `Double.compare` treats `NaN` as equal to itself and orders `-0.0` below `+0.0`. Both results are the exact opposite of `==` on the raw `double`s, which is what makes it a trap: a dedupe cache keyed on an affordability score folds every unscorable prospect into one entry and splits zero-disposable prospects into two.

</details>

**Q2.** Why is it a bug to store a record's `hashCode` in a database column?

<details><summary>Answer</summary>

Because the algorithm is deliberately unspecified. `Record.hashCode`'s javadoc says the precise algorithm "is unspecified and is subject to change", that the value "need not remain consistent from one execution of an application to another execution of the same application", and that a primitive component "may contribute its bits to the hash code differently than the `hashCode` of its primitive wrapper class". JDK 21 happens to fold `h*31 + Objects.hashCode(c)` from zero, stable enough to hide the bug through years of testing and then break on a JDK upgrade with no error — just reads routed to a shard where nothing was written. Derive persisted keys from the components with an algorithm you own; `String.hashCode` is one of the few specified ones.

</details>

**Q3.** A crafted stream carries a `StakeSplit` whose bonus portion exceeds 10% of the stake. What happens on deserialization, for a record and for an ordinary final class with the same check in its constructor?

<details><summary>Answer</summary>

The record rejects it and the class accepts it. A record's serial form is restricted to its component values and deserialization invokes the canonical constructor, so the compact constructor's check runs on the tampered values and the `IllegalArgumentException` surfaces wrapped in `java.io.InvalidObjectException`. An ordinary class is reconstructed by writing fields directly — its constructor is never invoked, which the captured trace shows by the absence of the constructor's own print line — so the invalid split lands in a live object. Closing that hole for the class needs a serialization proxy or a `readObject` that repeats the validation. This is the single strongest argument for records in a domain model.

</details>

**Q4.** You override a record's accessor to return a defensive copy. What does that cost on the `equals`/`hashCode`/`toString` path?

<details><summary>Answer</summary>

Nothing. `javac` passes `ObjectMethods.bootstrap` one method handle per component, and `javap -v` shows them as `REF_getField` — direct field reads, not `REF_invokeVirtual` on the accessor. The probe confirms it behaviourally: a record whose `units()` accessor returns `-999` still has `toString` printing `units=420` and `hashCode` equal to `Long.hashCode(420)`. So the copy runs only when a caller genuinely reads the component. The flip side is that an accessor which *normalises* rather than copies will silently disagree with `equals`, so restrict overrides to copying.

</details>

**Q5.** A record has a `List<String>` component. Name every place the reference can escape and what closes each.

<details><summary>Answer</summary>

Three places. **In**, through the canonical constructor, which stores the caller's reference — closed by `withdrawalIds = List.copyOf(withdrawalIds)` in the compact constructor. **Out**, through the generated accessor, which returns the field — closed by the same `List.copyOf`, since that copy is already unmodifiable, or otherwise by an accessor override. **Through the elements**, if the element type were itself mutable — a shallow copy does not close that one at all, and only a deep copy does. Deserialization is not a fourth hole for a record, because it runs the canonical constructor and therefore the copy.

</details>

---

## Open questions

- Whether JSR-354 (`javax.money` / Moneta) specifies a serial form, a null policy or a
  `MonetaryAmount` equality rule. Moneta is not on this machine, so the diff table compares only
  against `BigDecimal` and `Currency`. The JSR-354 specification plus Moneta's `FastMoney` source
  would settle it.
- Whether a record-versus-non-record class descriptor mismatch on deserialization throws
  `InvalidClassException` in JDK 21. The tamper experiment patches values inside a record-written
  stream and never crosses the shapes. `ObjectInputStream.readSerialData` plus the serialization
  specification's record section would settle it.

---

**Leaves covered:** 4.7.8 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 899
