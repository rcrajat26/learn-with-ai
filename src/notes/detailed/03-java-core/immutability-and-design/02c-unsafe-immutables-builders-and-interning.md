# 03 Java Core — Immutability and design — Unsafe immutables, builders, and interning — INTERMEDIATE (§2.3, 2.3.14–2.3.16)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Records, the final-field freeze, and the cached derived field](02b-records-jmm-and-builders.md) · Next: [Java is pass-by-value](03-pass-by-value.md)

---

`02b-records-jmm-and-builders.md` ended on the single exception in the entire memory model: the JLS 21 §17.5 `final`-field freeze, which makes a correctly constructed immutable object safe to publish through a plain data race, with no lock, no `volatile` and no happens-before edge. This file is the three things that follow from that guarantee being *conditional*. First, the two ways a class that looks immutable — `final` class, private fields, no setters, never mutated — gets none of it: a field that is not `final`, and a `this` that escapes its own constructor. Second, the builder, which makes a many-component immutable writable to *construct* without being writable afterwards, and which is the answer to the N-`withX` problem `02a-shallow-deep-and-building-blocks.md` left open. Third, when handing out a shared instance of such a value instead of allocating a fresh one is worth anything, and the three costs it brings with it.

Every measured output below was produced on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245), macOS aarch64**, compiled and run from a scratch directory under `/tmp/`. Library source is quoted from that build's `lib/src.zip`.

---

## 1. The immutable class that is still unsafe: a non-final field, and `this` escaping (2.3.14)

`[TRAP]` `[X-REF 05]` — Two classes with no setters, never mutated after construction, that fail anyway. Both are `MoneyThawed`-shaped: perfect under single-threaded reading, perfect in every test, broken under a racy publication or a subclass. They are the two ways the `final`-field freeze of `02b-records-jmm-and-builders.md` §3 is forfeited, and they are worth separating because the first is a missing keyword and the second is a missing habit.

### Why it exists

Neither failure is a coding error in the ordinary sense — there is no wrong line to point at. They exist as a category because that guarantee is *conditional*, and the conditions ("the fields are `final`" and "the object is correctly constructed before publication") are exactly the two things these classes violate. Naming them as a pair is what stops a reviewer from reading "no setters, private fields, no mutation" and signing off.

### When to reach for it, and when not

There is nothing to reach for; this section is a checklist. Two questions to ask of any type you are about to call immutable: **is every field `final`?** and **can `this` reach any code before the constructor returns?** A no to the first is a one-keyword fix. A yes to the second is a restructure, usually to a static factory.

### How it works

**(a) A non-final field forfeits the freeze entirely.**

Take the `LimitSet` of the brief's value types — a `dailyDeposit`, a `maxStake` and a `monthlyLoss`, all `private`, all assigned in the constructor with `Objects.requireNonNull`, none ever reassigned, class declared `final`, no setter anywhere — and declare the three fields **without** `final`. The first entry under `## Pitfalls` below carries the code in full. `ClientRestrictions` publishing one of these into a plain `static` field gets **no** guarantee, because the freeze covers `final` fields and these are not `final` — see `02b-records-jmm-and-builders.md` §3 for the mechanism being forfeited. The schedule:

| Step | Thread | Operation | What thread R can observe |
|---|---|---|---|
| 1 | W | allocate the `LimitSetThawed`; all three fields hold `null` | — |
| 2 | W | write `dailyDeposit`, `maxStake`, `monthlyLoss` | — |
| 3 | W | write the reference into the plain `static` field | — |
| 4 | R | read the plain `static` field, get non-null | the object |
| 5 | R | call `maxStake()` | **`null` is permitted** |

Steps 2 and 3 may be reordered — by the compiler, by the CPU's store buffer, or by the JIT choosing to sink the field stores — because nothing in the model forbids it for a plain field. So step 5 can read `null` from a field the constructor demonstrably assigned, and `Objects.requireNonNull` in the constructor does not help at all: it verified the *argument*, and what the reader sees is the *field*, at a moment the write had not yet reached it.

Be honest about the frequency, because that is why this survives review: it is **rare and catastrophic**. On x86-64, stores are not reordered with other stores at the hardware level, so the CPU will not produce it and only a JIT reordering will — and the JIT usually has no reason to. On **aarch64** stores may be reordered, so the same code that ran clean for two years on Intel hosts can produce a null on the first Graviton or Apple-silicon node. The fix is one keyword — `private final Money dailyDeposit;` — and it costs nothing, which is the whole argument for making every field `final` by default rather than only where you notice you need it.

**(b) `this` escaping the constructor forfeits "correctly constructed".** The freeze guarantee (`02b-records-jmm-and-builders.md` §3) is about a thread that obtains the reference of a *correctly constructed* object. Hand the reference out before the constructor finishes and no clause of §17.5 applies, because the freeze has not happened. Four ways it happens, all worth naming:

| Form | The escape | Who sees a half-built object |
|---|---|---|
| Listener registration | `registry.register(this)` in the constructor body | anything the registry dispatches to, possibly on another thread, possibly immediately |
| Starting a thread | `new Thread(() -> consume(this)).start()` in the constructor | the new thread, from its first instruction |
| Handing `this` to a collaborator | `ledger.attach(this)` where `attach` stores it | any later reader of what the collaborator stored |
| **An overridable instance method call** | `describe()` in a superclass constructor, overridden in the subclass | the *same* thread, deterministically, with no concurrency at all |

The fourth is the subtlest and the one that gets asked, because it needs no second thread: it is a pure consequence of Java's initialization order. A superclass constructor runs to completion before the subclass's field initialisers and constructor body run; a virtual call from the superclass constructor dispatches to the subclass's override; so the override executes against an instance whose own fields — including its `final` ones — are still at their defaults.

### Diagram

No diagram is assigned to this concept. The freeze timeline that both failures forfeit is **D-122** in `../classes-and-initialization/04-internals-final-and-constant-folding.md`; form (b)'s initialization order is drawn as D-038 in `../classes-and-initialization/01b-initialization-order.md`. The schedule table above is the correct fallback for (a).

### A concrete example

Form (b)'s fourth shape, complete and compiling, with the printed output.

```java
abstract class Restriction {
    private final String type;
    private final String source;

    Restriction(String type, String source) {
        this.type = Objects.requireNonNull(type);
        this.source = Objects.requireNonNull(source);
        System.out.println("  [super ctor] about to call describe()");
        System.out.println("  [super ctor] describe() -> " + describe());   // this escapes
    }

    public String type()   { return type; }
    public String source() { return source; }
    public abstract String describe();
}

final class DepositLimit extends Restriction {
    private final BigDecimal dailyCap;
    private final Set<String> rails;

    DepositLimit(BigDecimal dailyCap, Set<String> rails) {
        super("DEPOSIT_LIMITED", "SYSTEM_COMPLIANCE");
        this.dailyCap = Objects.requireNonNull(dailyCap);
        this.rails = Set.copyOf(rails);
        System.out.println("  [sub ctor]   fields now assigned");
    }

    @Override public String describe() {
        return type() + " from " + source() + " cap=" + dailyCap + " rails=" + rails
             + " railCount=" + (rails == null ? "n/a" : String.valueOf(rails.size()));
    }
}
```

Measured:

```
constructing DepositLimit(500.00, [CARD, BANK]):
  [super ctor] about to call describe()
  [super ctor] describe() -> DEPOSIT_LIMITED from SYSTEM_COMPLIANCE cap=null rails=null railCount=n/a
  [sub ctor]   fields now assigned
after construction: DEPOSIT_LIMITED from SYSTEM_COMPLIANCE cap=500.00 rails=[CARD, BANK] railCount=2
```

Line 3 is the whole point: `dailyCap` reads as **`null` on a `final` field**, in a single thread, deterministically, in a class with no mutation anywhere — because the superclass constructor's virtual call reached the override before the subclass's field writes. `type()` and `source()` return correct values on the same line, because *their* constructor had already run. Remove the `rails == null` guard and it is not a wrong value but a crash, with a stack trace that names the field:

```
Exception in thread "main" java.lang.NullPointerException: Cannot invoke "java.math.BigDecimal.toPlainString()" because "this.dailyCap" is null
	at DepositLimit2.describe(Escape2.java:12)
	at Restriction2.<init>(Escape2.java:5)
	at DepositLimit2.<init>(Escape2.java:11)
	at Escape2.main(Escape2.java:14)
```

Read the frames bottom-up: `main` calls the subclass constructor, which calls the superclass constructor, which calls the subclass's `describe()`. Three frames, and the `final` field in the middle one is null. `../inheritance-and-dispatch/01-basics.md` owns the fragile-base-class problem this is a special case of; `../classes-and-initialization/01b-initialization-order.md` owns the exact ordering of a `new` that produces it.

**The fix, for all four forms:** never let `this` out of the constructor. A superclass constructor calls only `private`, `static` or `final` methods. Where a framework genuinely requires registration, construct first and register after, in a static factory:

```java
public static DepositLimit register(BigDecimal dailyCap, Set<String> rails, RestrictionRegistry registry) {
    DepositLimit limit = new DepositLimit(dailyCap, rails);   // constructor completes; freeze happens
    registry.register(limit);                                 // publication is now of a complete object
    return limit;
}
```

That is `02-immutability.md` §2's static-factory idiom earning its keep a second time, for a reason that has nothing to do with interning: a factory has a point in time *after* the constructor has returned, and a constructor does not.

**A third, quieter case.** A `final` field holding a mutable object that was already published elsewhere before the constructor ran. The freeze of `02b-records-jmm-and-builders.md` §3 orders the *reference* write, and covers reachable state that was complete before the freeze — but if another thread still holds the referent and writes to it after the freeze, those writes are ordinary racing writes and covered by nothing. So `new Movement(id, amount, postedAt, callerList)` with no copy is not only `02a`'s encapsulation leak; it is a data race, and the copy is what makes the freeze's transitive clause applicable.

### The gotcha

**Pitfall:** believing that "no setters and never mutated" is the same as immutable, so `final` on the fields is a stylistic preference. Symptom: exactly the schedule above — a `LimitSetThawed` published into a plain field whose `maxStake()` returns `null` under load, on aarch64, after two clean years on x86-64, with a stack trace that points at a field the constructor assigned and a code review that finds nothing wrong. Fix: `final` on every field, always, with no exception for "we never write it anyway" — the keyword is not documentation, it is the thing that makes the `02b-records-jmm-and-builders.md` §3 freeze apply.

**Interview:** "Here is a class with no setters, private fields, and no mutation. Is it immutable?" The strong answer asks two questions back: are the fields `final`, and does `this` escape the constructor? Without `final` you get no freeze, so a racy reader can see defaults; if `this` escapes — a listener registration, a started thread, a stored reference, or an overridable method called from the constructor — the object was never correctly constructed and the freeze does not apply at all. Guide 05 owns publication in full.

> **Definition.** A class with no mutators is still unsafe if any field is non-`final` (the JLS 17.5 freeze covers `final` fields only, so a racy reader may observe a default the constructor demonstrably overwrote) or if `this` escapes the constructor — by listener registration, thread start, being handed to a collaborator, or an overridable instance method call that a subclass overrides — because the freeze happens at the end of the constructor and anything reached before it sees a half-built object, including its own `final` fields at their defaults.

---

## 2. The builder for immutables with many components (2.3.15)

`[BUILD]` — `02a` left this thread loose: a type with N components needs N `withX` methods to be usable, and the alternative — one constructor taking all N — is worse. A builder is the third option, and its actual contribution is not fluency. It is that a builder is a **mutable staging area with exactly one exit**, so the mutation happens where mutation is safe (a local object, one thread, before anything is published) and the immutable object is constructed once, complete, with every invariant checked.

### Why it exists

Two problems, and the second is the one that costs money.

**The telescoping constructor is unreadable.** `PaymentRun`'s seven components include a `String runRef`, a `String operatorId`, an `Instant createdAt`, a `Money total` and a `RunStatus status`. A call reading `new PaymentRun("PR-2026-08-29-W1", ids, createdAt, "OP-4471", total, status, limits)` conveys nothing at the call site, and adding an eighth component means touching every existing call.

**Two same-typed parameters can be transposed and it still compiles.** `runRef` and `operatorId` are both `String`. `new PaymentRun("OP-4471", ids, createdAt, "PR-2026-08-29-W1", total, status, limits)` is a valid program that produces a payment run whose reference is an operator id, and the failure surfaces four hours later as a banking-partner payout file the partner rejects, or worse, accepts. No compiler catches it and no unit test catches it unless someone wrote the test for exactly that transposition. A builder makes the argument names appear at the call site, where a reviewer reads them.

### When to reach for it, and when not

Reach for a builder at roughly four-or-more components, or fewer if two share a type, or whenever there are genuine optional components with defaults. Do not reach for one for a two-field `Money` or a one-field `ClientId` — `Money.of(amount, currency)` is unambiguous, shorter and cheaper, and a builder there is pure ceremony. Do not reach for one where a record's canonical constructor already reads well. `04-design-idioms.md` in this batch owns the builder as an *idiom*, including the over-application question, the generic-builder-with-inheritance shape and the comparison with named-argument alternatives; what is settled here is only how a builder interacts with the five rules.

### How it works

Four design decisions, each argued rather than copied.

**The immutable's constructor is `private` and takes the builder.** One parameter instead of seven, so adding a component touches the record of fields and the builder, and nothing else. It is `private`, which is `02-immutability.md` §2's substitute for rule 1 — a builder-constructed type gets rule 1 free as a side effect of the constructor being unreachable.

**The copy and the validity check both live in `build()`, in that order.** This is where `02-immutability.md` §3's TOCTOU discipline lands in real code, and it lands twice, because **the builder is a second TOCTOU surface — it is mutable by design.** A caller holds the builder, `build()` reads its fields, and if `build()` validated the builder's list and then copied it, another thread holding the same builder could add `WD-7777` in between, exactly as the two-thread schedule in `02-immutability.md` §3 showed. So the order is: copy inside the private constructor, then validate the constructed object. After that, the thing validated *is* the thing stored.

**Required components are checked in `build()`, not trusted to the caller.** There is no way to make a fluent setter mandatory, so the compiler cannot help. `build()` is the single choke point, so it is where `Objects.requireNonNull` per required component belongs, with a message naming the component. Optional components get a field initialiser in the builder (`status = RunStatus.DRAFT`) and no check.

**`build()` returns a new instance every call, so the builder is reusable — and must therefore copy.** If the private constructor aliases `b.itemIds` instead of copying it, two objects built from one builder share a list, and the first object mutates when the builder is touched again. This is the single most common builder bug and it is measured below.

### Diagram

No diagram is assigned to this concept. The builder's shape is a class listing rather than a picture, and the ordering discipline inside `build()` is already drawn as D-070's frames in `02-immutability.md` §3 — the copy-then-validate figure applies unchanged, with `build()` standing in for the constructor.

### A concrete example

`[BUILD]`. Complete and compiling. Seven components, of which two share a type.

```java
enum RunStatus { DRAFT, AWAITING_SIGNOFF, SIGNED_OFF, SENT }

public final class PaymentRun {
    private final String runRef;
    private final List<WithdrawalId> itemIds;
    private final Instant createdAt;
    private final String operatorId;
    private final Money total;
    private final RunStatus status;
    private final LimitSet limits;

    private PaymentRun(Builder b) {
        this.runRef     = b.runRef;
        this.itemIds    = List.copyOf(b.itemIds);          // copy, never alias
        this.createdAt  = b.createdAt;
        this.operatorId = b.operatorId;
        this.total      = b.total;
        this.status     = b.status;
        this.limits     = b.limits;
    }

    public String runRef()               { return runRef; }
    public List<WithdrawalId> itemIds()  { return itemIds; }
    public Instant createdAt()           { return createdAt; }
    public String operatorId()           { return operatorId; }
    public Money total()                 { return total; }
    public RunStatus status()            { return status; }
    public LimitSet limits()             { return limits; }

    public static Builder builder() { return new Builder(); }

    public static final class Builder {
        private String runRef;
        private final List<WithdrawalId> itemIds = new ArrayList<>();
        private Instant createdAt;
        private String operatorId;
        private Money total;
        private RunStatus status = RunStatus.DRAFT;          // optional, defaulted
        private LimitSet limits;                             // optional, conditionally required

        private Builder() {}

        public Builder runRef(String runRef)                     { this.runRef = runRef; return this; }
        public Builder addItem(WithdrawalId id)                  { this.itemIds.add(id); return this; }
        public Builder items(Collection<WithdrawalId> ids)       { this.itemIds.clear(); this.itemIds.addAll(ids); return this; }
        public Builder createdAt(Instant createdAt)              { this.createdAt = createdAt; return this; }
        public Builder operatorId(String operatorId)             { this.operatorId = operatorId; return this; }
        public Builder total(Money total)                        { this.total = total; return this; }
        public Builder status(RunStatus status)                   { this.status = status; return this; }
        public Builder limits(LimitSet limits)                    { this.limits = limits; return this; }

        public PaymentRun build() {
            Objects.requireNonNull(runRef, "runRef is required");
            Objects.requireNonNull(createdAt, "createdAt is required");
            Objects.requireNonNull(operatorId, "operatorId is required");
            Objects.requireNonNull(total, "total is required");
            Objects.requireNonNull(status, "status is required");
            PaymentRun run = new PaymentRun(this);              // 1. copy, inside the private ctor
            validate(run);                                      // 2. validate the copy
            return run;
        }

        private static void validate(PaymentRun run) {
            if (run.itemIds().isEmpty()) {
                throw new IllegalArgumentException("a payment run needs at least one withdrawal");
            }
            if (new HashSet<>(run.itemIds()).size() != run.itemIds().size()) {
                throw new IllegalArgumentException("duplicate withdrawal in run " + run.runRef());
            }
            if (run.total().amount().signum() <= 0) {
                throw new IllegalArgumentException("run total must be positive");
            }
            if (run.status() == RunStatus.SIGNED_OFF && run.limits() == null) {
                throw new IllegalArgumentException("a signed-off run must carry the operative LimitSet");
            }
        }
    }
}
```

Measured — one builder, built twice with an item and a total changed in between, then three failure paths:

```
first  = PaymentRun[PR-2026-08-29-W1 AWAITING_SIGNOFF items=[WD-9001, WD-9002] total=1820.00 GBP operator=OP-4471]
second = PaymentRun[PR-2026-08-29-W1 AWAITING_SIGNOFF items=[WD-9001, WD-9002, WD-9003] total=2080.00 GBP operator=OP-4471]
first unchanged after reuse? true
lists aliased? false
duplicate -> duplicate withdrawal in run PR-2026-08-29-W1
missing required -> createdAt is required
signed-off without limits -> a signed-off run must carry the operative LimitSet
```

Lines 3 and 4 are the payoff of `List.copyOf` in the private constructor: the first `PaymentRun` did not change when the builder was reused, and the two lists are distinct instances. Lines 5–7 are the three checks `build()` centralises — a domain rule (no duplicate withdrawal in a run), a required-component check with a message naming the component, and a cross-component rule (`SIGNED_OFF` implies a `LimitSet`) that no per-setter validation could express because it depends on two components at once. That last one is the real argument for validating in `build()` rather than in the setters: a setter cannot check an invariant over components that have not been set yet.

**The aliasing bug, measured, because it is the one that ships.** Identical class, one line changed — `this.itemIds = b.itemIds;` instead of `List.copyOf(b.itemIds)`:

```
first  = PR-2026-08-29-W1 [WD-9001, WD-9002]
first  = PR-2026-08-29-W1 [WD-9001, WD-9002, WD-9003]
second = PR-2026-08-29-W1 [WD-9001, WD-9002, WD-9003]
same list instance? true
```

Lines 1 and 2 are the *same object* printed before and after `b.addItem("WD-9003").build()`. `first` gained a withdrawal it was not built with, because the builder still owns the list it handed over. In `PaymentRun` terms: run W1 is signed off by an operator with two withdrawals in it and later contains three, and the ledger and the payout file disagree.

### The gotcha

**Pitfall:** treating a builder as thread-safe because the thing it builds is immutable. A builder is mutable by definition, so a `static final Builder` shared across the operators on shift is a bug of exactly the `SimpleDateFormat` shape `02a` catalogued — two threads interleaving `addItem` calls and `build()` produce runs containing each other's withdrawals, with no exception thrown and no way to tell from the output which items belonged to which run. Symptom: intermittent duplicate-withdrawal rejections from `build()`'s own validation on a run whose caller added no duplicates, which is the *lucky* case; the unlucky case is two runs each holding half of both. Fix: a builder is a local variable, created and discarded within one method on one thread. If you want a reusable template, make the *template* an immutable `PaymentRun` and add a `toBuilder()` that seeds a fresh builder from it.

**Records and builders compose.** `build()` can call a record's canonical constructor, and then the record's compact constructor — the mechanism of `02b-records-jmm-and-builders.md` §1, including the assignment to the *parameter* name — does the copy-in and the null checks, so the builder's `build()` only has to carry the cross-component rules:

```java
public Movement build() {
    return new Movement(id, amount, postedAt, entries);   // compact ctor copies and validates
}
```

That is the shape to prefer when the type is a record: one place doing per-component validation (the compact constructor, which every construction path goes through, including deserialization) and one doing multi-component validation (`build()`).

> **Definition.** A builder for an immutable type is a mutable, single-threaded staging object with one exit: fluent setters accumulate components, `build()` performs the null checks for required components, hands the builder to the immutable type's `private` constructor which defensively copies every mutable component, and only then validates the constructed object — so the mutation happens where it is safe, the copy precedes the validation as `02-immutability.md` §3 requires, and every invariant including cross-component ones is checked exactly once at the single point of construction.

---

## 3. Interning and caching immutable values, and when to do it in your own type (2.3.16)

An immutable value has no identity worth preserving — two `Money(4.20, GBP)` instances are interchangeable in every observable respect except `==`. That is a licence: the platform is free to hand out the same instance twice, and it does, in three places you meet daily. It is also a trap for anyone who mistakes the licence for a guarantee, and that trap is exactly why `==` on boxed values is the most-asked Java puzzle there is.

### Why it exists

Three payoffs, in descending order of how often they are the real reason. **Clarity**: `Money.ZERO` reads better at a call site than `Money.of(BigDecimal.ZERO, GBP)`, and `BigDecimal.ZERO` exists mostly for this. **Comparison speed**: `==` on an interned instance is one instruction where `equals` on a `BigDecimal` compares scale and unscaled value. **Allocation**: the historical motivation, and — as priced below — usually the weakest.

### How it works

Three JDK caches, side by side. All rows measured on JDK 21.0.7.

| | `Integer.valueOf(int)` | `Boolean.valueOf(boolean)` | `BigDecimal.valueOf(long)` |
|---|---|---|---|
| What is cached | `IntegerCache.cache`, an `Integer[]` covering `low..high` | the two constants `Boolean.TRUE` and `Boolean.FALSE` | `ZERO_THROUGH_TEN`, a `BigDecimal[]` of 0–10 at scale 0 |
| Range specified? | **Only −128..127** is mandated by JLS 21 §5.1.7. `high` is configurable upward via `java.lang.Integer.IntegerCache.high`; the JIT's `AutoBoxCacheMax` is 128 on this build | **Yes, exhaustively** — `Boolean` has exactly two instances by specification | **No** — an implementation detail with no javadoc guarantee |
| What breaks if you rely on `==` | Everything above 127 or below −128, and everything at all if the property is set | Nothing — but see below | Anything outside 0–10, and anything built with `new BigDecimal(...)` rather than `valueOf` |

`Integer.valueOf`'s mechanism is three lines, from `java.base/java/lang/Integer.java`, JDK 21.0.7:

```java
    public static Integer valueOf(int i) {
        if (i >= IntegerCache.low && i <= IntegerCache.high)
            return IntegerCache.cache[i + (-IntegerCache.low)];
        return new Integer(i);
    }
```

In range, return the array element at `i + 128` (since `low` is `-128`, `-low` is `128`); out of range, allocate. The nested class's static initialiser fixes `low = -128`, defaults `high = 127`, permits a system property to raise `high` but never lower it — `h = Math.max(parseInt(...), 127)` — and closes with the comment that names the specification: `// range [-128, 127] must be interned (JLS7 5.1.7)`. So the boundary is not folklore, it is the array's last index.

`Boolean.valueOf` is one line and needs no cache class:

```java
    public static Boolean valueOf(boolean b) {
        return (b ? TRUE : FALSE);
    }
```

`BigDecimal`'s is a table lookup guarded by a range test, and `ZERO`, `ONE`, `TWO` and `TEN` are aliases into it — `public static final BigDecimal ZERO = ZERO_THROUGH_TEN[0];`.

Measured:

```
Integer.valueOf(127) == Integer.valueOf(127)   : true
Integer.valueOf(128) == Integer.valueOf(128)   : false
Integer.valueOf(-128) == Integer.valueOf(-128) : true
Integer.valueOf(-129) == Integer.valueOf(-129) : false
Boolean.valueOf(true) == Boolean.TRUE          : true
BigDecimal.valueOf(0) == BigDecimal.ZERO       : true
BigDecimal.valueOf(10) == BigDecimal.TEN       : true
BigDecimal.valueOf(11) == BigDecimal.valueOf(11): false
new BigDecimal("0") == BigDecimal.ZERO         : false
new BigDecimal("0").equals(BigDecimal.ZERO)    : true
new BigDecimal("0.00").equals(BigDecimal.ZERO) : false
autoboxed 127 ==                              : true
autoboxed 128 ==                              : false
```

The last two lines matter because they are the form a loop counting bonus grants per identity actually writes — `Integer grants = 128;` compiles to `Integer.valueOf(128)`, so autoboxing inherits the cache and its boundary exactly. Line 11 is the separate `BigDecimal` trap and belongs to `../numbers-and-money/02-numbers-and-money.md`: `equals` on `BigDecimal` compares *scale as well as value*, so `0.00` is not equal to `0` — which means interning cannot save you there either, and `compareTo` is the comparison you wanted.

### Diagram

No diagram is assigned to this concept. The picture is **D-025**, the `IntegerCache` array laid out on the heap with the two shared references pointing into it and the two independent 128-boxes beside it, and it is carried by `../wrappers-and-boxing/01-basics.md`, which owns the wrapper caches in full.

### A concrete example

The decision rule for your own type, which is what this section is actually for. Cache when the value set is **small, bounded, frequently constructed and cheap to key**. All four, not three.

| Candidate | Small | Bounded | Frequent | Cheap key | Cache? |
|---|---|---|---|---|---|
| `Money.zero(GBP)` | 1 value | yes | yes — most `StakeSplit` bonus portions are zero | yes, the currency | **Yes** |
| The eleven `LedgerPosition` values | 11 | yes | 19.8M/day | yes | **Yes — and make it an `enum`, which is a cache the language maintains** |
| `StatusCode` — the 40-odd `AO-`/`AA-` codes | ~40 | yes | yes | yes | **Yes** |
| `Money(4.20, GBP)` | no | **no** | yes | yes | **No** — the key space is unbounded and the map holding it becomes the leak |
| `MovementId(UUID)` | no | no | 19.8M/day | yes | **No** — every value is distinct by construction; a cache would be a pure memory leak with a 0% hit rate |

**Price it before you build it.** Against `../cost-model/02-master-cost-table.md`: a non-escaping allocation is frequently eliminated entirely by C2's escape analysis and scalar replacement (`DoEscapeAnalysis = true` and `EliminateAllocations = true` on this build), and a surviving TLAB allocation is a pointer bump. A `ConcurrentHashMap.get` to *find* a cached instance is a hash, a bounds-masked array load, a reference compare and usually an `equals` — measurably dearer than the allocation it replaces. So caching to avoid an allocation is often a **pure loss**: you pay a lookup to save a pointer bump, and you pay it on every call rather than on the calls that would have allocated. **Unverified:** C2 publishes no guarantee about when escape analysis fires or when scalar replacement follows, so "frequently eliminated" is the honest phrasing and the planning number must assume the allocation happens.

Where a cache does earn its keep, prefer a **fixed table populated once** over a growing map. `Money.ZERO_GBP` as a `static final` field is a table of one, has no lookup at all (a `getstatic`), and cannot leak. An `enum` is the same idea with the language maintaining the table, which is why `LedgerPosition` should be an `enum` and not an interned `String` — `../enums/01c-production-patterns-and-guarantees.md` owns the guarantees that buys.

### The gotcha

Three real costs, plainly.

**An unbounded cache is a memory leak.** A `ConcurrentHashMap<BigDecimal, Money>` interning every `Money` ever constructed grows without limit at 2.8M stake reservations a day and is unreachable-free by construction, because the map is a strong root. If you must cache an unbounded key space, the reference strength ladder is the tool and `../objects-equality-and-lifecycle/03-lifecycle-and-references.md` owns it — but the correct answer is almost always not to cache.

**A cache introduces a `==`-versus-`equals` trap for your callers.** The instant `Money.zero(GBP)` returns a shared instance, someone writes `if (split.bonusPortion() == Money.zero(GBP))` and it works — until the currency is USD, or until someone constructs the zero a different way, and then it silently reports false and a stake splits wrongly. `IntegerCache` created this trap for the entire platform and it is the most-asked Java puzzle there is; your own cache creates a private version of it. Document the cache as an optimisation and never as a guarantee, exactly as `BigDecimal`'s javadoc declines to.

**A cached value-based instance invites `synchronized` on it.** A shared instance looks like a natural lock, and locking on one is a cross-application bug: every holder of that cached `Integer` or `Money` is contending on the same monitor. `javac` warns:

```
Sync.java:4: warning: [synchronization] attempt to synchronize on an instance of a value-based class
        synchronized (bonusGrantsToday) { System.out.println("locked on a cached Integer"); }
        ^
1 warning
```

and the JVM will turn it into a hard error on request — `java -XX:+UnlockDiagnosticVMOptions -XX:DiagnoseSyncOnValueBasedClasses=1`:

```
#  Internal Error (synchronizer.cpp:462), pid=97364, tid=4355
#  fatal error: Synchronizing on object 0x00000007ffcc7828 of klass java.lang.Integer at Sync.main(Sync.java:4)
```

That flag is diagnostic and off by default in production, so the only routine defence is the compiler warning and not ignoring it. `../objects-equality-and-lifecycle/01-basics.md` owns value-based classes and the `@jdk.internal.ValueBased` annotation that marks the types this applies to; the same reasoning will apply to your `Money` when Valhalla lands, which is a reason to annotate the intent in your own javadoc now.

**Interview:** "Why does `Integer.valueOf(127) == Integer.valueOf(127)` return true and `128` return false?" The strong answer is the mechanism, not the range: `valueOf` returns `IntegerCache.cache[i + 128]` when `i` is between `IntegerCache.low` and `IntegerCache.high`, and allocates otherwise; JLS 21 §5.1.7 mandates only −128..127, `low` is fixed at −128 and `high` defaults to 127 but can be raised by a system property and never lowered — so 127 is the last cached index and 128 is the first allocation. Then volunteer that the correct conclusion is not "remember 127" but "never use `==` on a boxed value", because the boundary is configurable and the range above it is unspecified.

> **Definition.** Interning an immutable value returns a shared instance instead of allocating one, and is worth doing when the value set is small, bounded, frequently constructed and cheap to key — for clarity and comparison speed, and as a fixed `static final` table or an `enum` rather than a growing map — at the cost of an unbounded cache being a memory leak, a `==`-versus-`equals` trap for callers who mistake the optimisation for a guarantee, and an invitation to `synchronized` on a shared value-based instance.

Cache immutable values for identity and clarity — `Money.ZERO` reads better and compares faster — not for allocation cost, which the JIT has usually already removed.

---

## Pitfalls

### No setters and never mutated means immutable, so `final` on the fields is style

**Wrong**

```java
final class LimitSetThawed {
    private Money dailyDeposit;               // private. never reassigned. NOT final.
    private Money maxStake;

    LimitSetThawed(Money dailyDeposit, Money maxStake) {
        this.dailyDeposit = Objects.requireNonNull(dailyDeposit, "dailyDeposit must not be null");
        this.maxStake = Objects.requireNonNull(maxStake, "maxStake must not be null");
    }

    Money dailyDeposit() { return dailyDeposit; }
    Money maxStake()     { return maxStake; }
}
```

Published into a plain `static` field and read by the settlement path, `maxStake()` may return **`null`** — the constructor's write and the reference write are both plain stores and nothing in the model forbids reordering them, so a racy reader can obtain the reference before the field write reaches it. No exception, no wrong line, and it will not reproduce on x86-64, where the hardware does not reorder stores; it reproduces on aarch64, or after a JIT decision changes.

**Right**

```java
final class LimitSet {
    private final Money dailyDeposit;
    private final Money maxStake;

    LimitSet(Money dailyDeposit, Money maxStake) {
        this.dailyDeposit = Objects.requireNonNull(dailyDeposit, "dailyDeposit must not be null");
        this.maxStake = Objects.requireNonNull(maxStake, "maxStake must not be null");
    }                                         // <-- JLS 17.5 freeze on both fields

    Money dailyDeposit() { return dailyDeposit; }
    Money maxStake()     { return maxStake; }
}
```

`final` triggers the JLS 21 §17.5 freeze at the end of the constructor, which forbids the field writes being reordered past the publication of `this`. A reader that obtains the reference — through a data race, with no `volatile` and no lock — is guaranteed to see both fields correctly. One keyword, zero runtime cost.

**Why people believe it:** the reasoning "there are no writes after construction, therefore there is nothing to race on" is very nearly right, and it is what every informal account of immutability says. What it omits is that the *constructor's* writes are writes, and that the guarantee forbidding them to be reordered past publication is conditional on the keyword. The failure also never appears in testing — single-threaded tests construct then read, and multi-threaded tests on x86-64 hosts get the ordering from the hardware for free — so the belief is never contradicted until the platform changes underneath it.

### A builder is safe to share because the thing it builds is immutable

**Wrong**

```java
final class BankWithdrawal {
    private static final PaymentRun.Builder SHARED = PaymentRun.builder()
        .createdAt(Instant.parse("2026-08-29T09:15:00Z"))
        .status(RunStatus.AWAITING_SIGNOFF);

    static PaymentRun runFor(String runRef, String operatorId, List<WithdrawalId> ids, Money total) {
        return SHARED.runRef(runRef).operatorId(operatorId).items(ids).total(total).build();
    }
}
```

Two operators on shift call `runFor` at once and the two calls interleave inside the shared builder's fields and its `itemIds` list. The lucky outcome is `build()`'s own validation firing — `duplicate withdrawal in run PR-2026-08-29-W1` for a caller that supplied no duplicates. The unlucky outcome is two runs that each pass validation and each hold half of both operators' withdrawals, signed off, and sent to the banking partner.

**Right**

```java
final class BankWithdrawal {
    static PaymentRun runFor(String runRef, String operatorId, List<WithdrawalId> ids, Money total) {
        return PaymentRun.builder()                       // a fresh builder, local to this call
            .runRef(runRef)
            .operatorId(operatorId)
            .items(ids)
            .total(total)
            .createdAt(Instant.parse("2026-08-29T09:15:00Z"))
            .status(RunStatus.AWAITING_SIGNOFF)
            .build();
    }
}
```

A builder is a local variable with a lifetime shorter than one method call, so there is no sharing to race on. If a template is genuinely wanted, make the template an immutable `PaymentRun` and give it a `toBuilder()` that seeds a fresh builder from its components.

**Why people believe it:** the builder's whole purpose is described as "producing an immutable object", and the word *immutable* attaches to the pattern rather than to the two objects in it. The static field also looks like ordinary configuration reuse — the same instinct that produces a `static final SimpleDateFormat`, which `02a` catalogued as the same bug. And it works perfectly under any test that exercises one thread.

### Interning my own value type pays for itself in saved allocations

**Wrong**

```java
public final class Money {
    private static final ConcurrentHashMap<String, Money> INTERNED = new ConcurrentHashMap<>();

    private final BigDecimal amount;
    private final String currency;

    private Money(BigDecimal amount, String currency) {
        this.amount = Objects.requireNonNull(amount, "amount must not be null");
        this.currency = Objects.requireNonNull(currency, "currency must not be null");
    }

    public static Money of(BigDecimal amount, String currency) {
        String key = currency + ':' + amount.toPlainString();
        return INTERNED.computeIfAbsent(key, k -> new Money(amount, currency));
    }

    public BigDecimal amount() { return amount; }
    public String currency()   { return currency; }
}
```

Two failures, both of which get worse with traffic. The key space is unbounded — `Money` values run over every stake, every deposit and every fee, at 2.8M stake reservations a day with an average value of 4.20 — and `INTERNED` is a `static final` field, so it is a strong root and nothing in it is ever collectable. The heap grows for the lifetime of the process. And the lookup that was supposed to save an allocation *costs* two: the string concatenation and the `toPlainString()` both allocate, before the hash, the masked array load and the `equals` that follow. The cache is dearer than the allocation it replaces, and it is paid on every call rather than on the calls that would have allocated.

**Right**

```java
public final class Money {
    private static final Money ZERO_GBP = new Money(BigDecimal.ZERO, "GBP");

    private final BigDecimal amount;
    private final String currency;

    private Money(BigDecimal amount, String currency) {
        this.amount = Objects.requireNonNull(amount, "amount must not be null");
        this.currency = Objects.requireNonNull(currency, "currency must not be null");
    }

    public static Money of(BigDecimal amount, String currency) {
        return new Money(amount, currency);          // allocate; C2 often elides it entirely
    }

    public static Money zeroGbp() { return ZERO_GBP; }

    public BigDecimal amount() { return amount; }
    public String currency()   { return currency; }
}
```

A table of one, populated once, with no lookup at all — `zeroGbp()` compiles to a `getstatic` — and no way to leak, because the table cannot grow. That is the shape a cache should take when it earns its keep: small, bounded, fixed at class initialization, or an `enum` where the language maintains the table for you. Everything outside that bound allocates, and `DoEscapeAnalysis` and `EliminateAllocations` are both on by default, so the non-escaping ones frequently cost nothing.

**Why people believe it:** allocation *was* the historical motivation for `IntegerCache`, and the existence of a cache in `java.lang` reads as an endorsement of caching in general rather than as a decision about one small bounded set of values. The lookup's own cost never appears in the comparison, because a `ConcurrentHashMap.get` feels like "O(1), therefore free" against an allocation that feels like "the GC, therefore expensive" — when the allocation is a TLAB pointer bump and the lookup is a hash plus an `equals`. A microbenchmark that hammers one key makes it worse by measuring a 100% hit rate the production key space cannot deliver.

---

## Cheat sheet

| Claim | Fact (JDK 21.0.7) |
|---|---|
| Non-final field, racy publish | Reader may see the default. Rare on x86-64 (no store-store reordering), real on aarch64. Fix is one keyword |
| Why `requireNonNull` does not help | It verifies the *argument*; the racy reader reads the *field*, before the write reached it |
| `this` escape, four forms | listener registration; thread start; handed to a collaborator; **overridable method called from a constructor**. Measured: a `final BigDecimal` reads `null` |
| The escape that needs no second thread | A superclass constructor's virtual call dispatches to the subclass override, which runs before the subclass's field writes |
| Escape fix | Constructor calls only `private`/`static`/`final` methods; register in a static factory *after* construction |
| The quiet third case | A `final` field holding a mutable object another thread already holds — the freeze orders the reference, not the referent's later writes. Copy in |
| Builder ordering | `build()`: null-check required → private ctor **copies** → validate the constructed object. Cross-component rules can only live in `build()` |
| Builder: two properties missed | It is mutable, so never `static` and never shared; `build()` must copy, not alias, or two objects share a list |
| Builder threshold | ~4+ components, or fewer if two share a type (transposition compiles). Not for two-field `Money` |
| Builder plus record | `build()` calls the record's canonical constructor; the compact constructor (`02b-records-jmm-and-builders.md` §1) does per-component copy and null checks, `build()` does cross-component rules |
| `Integer` cache | `cache[i + 128]` for `low..high`; `low = -128` fixed, `high = 127` default, raisable by property, never lowerable. JLS §5.1.7 mandates **only** −128..127; `AutoBoxCacheMax = 128` |
| `Boolean` / `BigDecimal` caches | `Boolean`: exactly two instances, by specification. `BigDecimal`: `ZERO_THROUGH_TEN[0..10]`, `ZERO`/`ONE`/`TWO`/`TEN` alias into it, undocumented. Use `==` on neither |
| `new BigDecimal("0.00").equals(ZERO)` | **false** — `equals` compares scale too. Use `compareTo` |
| Cache your own type when | Small **and** bounded **and** frequent **and** cheap to key. All four. Prefer a `static final` field or an `enum` over a growing map |
| Do not cache for allocation cost | A `ConcurrentHashMap.get` costs more than the TLAB pointer bump it saves, and is paid on every call |
| Three cache costs | Unbounded → leak; shared instance → `==`-versus-`equals` trap for callers; shared instance → invites `synchronized` on a value-based class (`javac` warning; fatal VM error under `-XX:+UnlockDiagnosticVMOptions -XX:DiagnoseSyncOnValueBasedClasses=1`) |

---

## Self-test

**Q1.** Here is a `final class` with private fields, no setters, and no mutation anywhere. Is it immutable?

<details><summary>Answer</summary>

Two questions back. **Are the fields `final`?** If not, you get no JLS 17.5 freeze, and a reader that obtains the reference through a racy publication may see the fields at their defaults — `null`, `0` — even though the constructor demonstrably assigned them, because nothing forbids reordering a plain field write past the publication of `this`. It will not reproduce on x86-64, where the hardware does not reorder stores with stores; it will on aarch64, or after a JIT decision changes. The fix is one keyword at zero runtime cost.

**Can `this` escape the constructor?** Four forms: `registry.register(this)` in the constructor body; starting a thread that captures `this`; handing `this` to any method that stores it; and — the one that needs no concurrency at all — an overridable instance method call from a superclass constructor. Any of them publishes a reference before the freeze, so §17.5 does not apply. The fix: constructors call only `private`, `static` or `final` methods, and where a framework demands registration, use a static factory that constructs first and registers after.

</details>

**Q2.** A `final BigDecimal dailyCap` field reads as `null` inside a method of the object that owns it, in a single thread, with no reflection and no mutation. How?

<details><summary>Answer</summary>

`describe()` was called from the *superclass* constructor and overridden in the subclass. A superclass constructor runs to completion before the subclass's field initialisers and constructor body, and a virtual call from it dispatches to the subclass's override — so the override executes against an instance whose own fields, `final` included, are still at their defaults. Measured:

```
  [super ctor] describe() -> DEPOSIT_LIMITED from SYSTEM_COMPLIANCE cap=null rails=null railCount=n/a
  [sub ctor]   fields now assigned
after construction: DEPOSIT_LIMITED from SYSTEM_COMPLIANCE cap=500.00 rails=[CARD, BANK] railCount=2
```

`type()` and `source()` on the same line return correct values, because *their* constructor had already run — which is what makes the failure look so arbitrary. Unguarded it is not a wrong value but an NPE whose message names the field: `Cannot invoke "java.math.BigDecimal.toPlainString()" because "this.dailyCap" is null`, with three frames — `main`, the subclass constructor, the superclass constructor, the override. This is `this` escaping the constructor in its fourth form, and the fix is that a constructor calls only `private`, `static` or `final` methods.

</details>

**Q3.** In a builder for an immutable type, where do the defensive copy and the validity check go, and why is a builder a second TOCTOU surface?

<details><summary>Answer</summary>

`build()` does the required-component null checks, then hands the builder to the immutable type's `private` constructor which does the defensive copy of every mutable component, and *then* validates the constructed object. Copy before validate, exactly as `02-immutability.md` §3 established — because a check performed on the builder's still-mutable list is a statement about a past instant, and anything holding the builder can invalidate it before the copy lands.

The builder is a second TOCTOU surface precisely because it is **mutable by design**: the caller holds it, `build()` reads it, and there is an interval between. Two further properties usually missed. A builder is not thread-safe, so a `static` shared builder is the same bug as a `static final SimpleDateFormat` — two operators' withdrawals interleaving into one run, with `build()`'s duplicate check firing as the *lucky* outcome. And `build()` must copy rather than alias, or two objects built from one builder share a list: measured on the aliasing form, the first `PaymentRun` gained a withdrawal after it had already been built, and `first.itemIds() == second.itemIds()` was `true`.

</details>

**Q4.** Should you intern `Money` values in your own code to avoid allocation?

<details><summary>Answer</summary>

Almost never for that reason. Cache when the value set is small **and** bounded **and** frequently constructed **and** cheap to key — `Money.zero(GBP)`, the eleven ledger positions (which should be an `enum`, a cache the language maintains), the forty-odd status codes. `Money(4.20, GBP)` fails "bounded", and the map holding the cache becomes the leak; `MovementId(UUID)` fails it with a 0% hit rate.

The allocation argument specifically is usually a loss. `DoEscapeAnalysis` and `EliminateAllocations` are both on by default, so a non-escaping allocation is frequently eliminated to nothing, and a surviving one is a TLAB pointer bump; a `ConcurrentHashMap.get` to *find* a cached instance is a hash, a masked array load, a reference compare and usually an `equals` — dearer than what it replaces, and paid on every call. (C2 publishes no guarantee about when escape analysis or scalar replacement fires, so the planning number assumes the allocation happens.)

Cache for **clarity and comparison speed** instead — `Money.ZERO` as a `static final` field reads better and is a `getstatic` with no lookup. And accept the three costs: an unbounded cache leaks, a shared instance creates a `==`-versus-`equals` trap for your callers exactly as `IntegerCache` does for the whole platform, and a shared value-based instance invites `synchronized` on it, which `javac` warns about and `-XX:DiagnoseSyncOnValueBasedClasses=1` turns into a fatal VM error.

</details>

**Q5.** Why is `Integer.valueOf(127) == Integer.valueOf(127)` true and `128` false, and what is the right conclusion to draw?

<details><summary>Answer</summary>

`valueOf` is three lines: if `i` is between `IntegerCache.low` and `IntegerCache.high`, return `IntegerCache.cache[i + (-IntegerCache.low)]`; otherwise `return new Integer(i)`. `low` is fixed at `-128`, so the index is `i + 128`, and `high` defaults to 127 — so 127 is the last cached index and 128 is the first allocation. JLS 21 §5.1.7 mandates caching for **−128..127 only**; the JDK's own source carries the comment `// range [-128, 127] must be interned (JLS7 5.1.7)`. `high` can be raised by the system property `java.lang.Integer.IntegerCache.high` and, by `Math.max(parseInt(...), 127)`, never lowered. Autoboxing compiles to `valueOf`, so `Integer grants = 128;` inherits the boundary exactly — measured `true` at 127 and `false` at 128 in both the explicit and the autoboxed form.

The right conclusion is not "remember 127". It is **never use `==` on a boxed value**: the boundary is configurable at startup, the range above it is unspecified, and the same reasoning applies to `BigDecimal`'s undocumented `ZERO_THROUGH_TEN` table and to any cache you write yourself.

</details>

---

## Open questions

- **Escape analysis and scalar replacement heuristics.** §3 prices interning against allocation on the basis that a non-escaping allocation is frequently eliminated. C2 publishes no documented guarantee about when `DoEscapeAnalysis` leads to `EliminateAllocations` actually firing for a given allocation site; only a `-XX:+PrintEliminateAllocations` (debug-build) trace or a JMH allocation-rate profile per site would settle it for a specific case.
- **The `BigDecimal` small-value cache is an implementation detail.** `ZERO_THROUGH_TEN` and the `valueOf` range check are visible in the JDK 21.0.7 source and the `==` results are measured, but no javadoc guarantee covers them, so the behaviour may differ on another vendor's 21 or a later release. Only a specification statement, which does not exist, would make it safe to rely on.
- **The *Effective Java* item-number mapping.** §2 is the material of Item 2: *Consider a builder when faced with many constructor parameters*; the title is cited rather than the number alone because the number mapping is on the standing unverified list. A copy of the third edition would settle the numbers.

---

**Leaves covered:** 2.3.14, 2.3.15, 2.3.16 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none — D-122 (`../classes-and-initialization/04-internals-final-and-constant-folding.md`) and D-025 (`../wrappers-and-boxing/01-basics.md`) are the adjacent figures for §1 and §3
**Target version:** Java 21 LTS
**Lines:** 657
