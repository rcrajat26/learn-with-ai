# 03 Java Core — The eighty questions, 65–80 — INTERVIEW (§5.1, 5.1.65–5.1.80)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The eighty questions, 49–64](94c-interview-questions-49-64.md) · Next: [The trap index and the version-stale table](94e-interview-trap-index.md)

## The questions, concluded

The last sixteen of the eighty questions, 65–80. The how-to-use notes for this file's shape — the 30-second answer, the 5-minute answer, the two-register pattern — live in [`94-interview-questions-and-drills.md`](94-interview-questions-and-drills.md); this file follows that skeleton without repeating it.

### Q65. "Why does `short s = 1; s = s + 1;` not compile?"

**The 30-second answer.** Binary numeric promotion (JLS §5.6) widens both operands of `+` to at least `int`, so `s + 1` is an `int` expression regardless of `s`'s declared type. Assignment context does not narrow a non-constant `int` back to `short` — narrowing without a cast is only permitted for a compile-time constant expression that fits the target type (§5.2), and `s + 1` is not a constant expression because `s` is a variable, not a `final` constant. `s += 1` compiles because compound assignment carries an implicit cast to the left-hand type (§15.26.2): it means `s = (short)(s + 1)`, which truncates silently on overflow rather than failing to compile.

**The 5-minute answer.** There is no sub-`int` arithmetic instruction on the JVM — no `sadd`, only `iadd` — so every arithmetic operator promotes its narrower-than-`int` operands to `int` before the machine can add them, and the result type is `int`, never the narrower operand type. `javac`'s diagnostic is `error: incompatible types: possible lossy conversion from int to short`. The constant-narrowing exception in §5.2 only fires when every one of four conditions holds: the source is a compile-time constant expression (§15.29) of type `byte`/`short`/`char`/`int`; the target is `byte`/`short`/`char`; the value is representable in the target; and — critically — a *`final` local initialised with a constant* is itself a constant expression, so `final short s = 1; short t = s + 1;` compiles without a cast, because `s + 1` is now a constant expression evaluating to 2, in range. A plain (non-`final`) local never qualifies, however small its current value.

```java
final class RetryCounter {
    static short capRetries(short attempted) {
        // short retries = attempted + 1;             // error: possible lossy conversion
        short retries = (short) (attempted + 1);       // explicit: sign for the truncation
        return retries;
    }

    static short capRetriesCompound(short attempted) {
        short retries = attempted;
        retries += 1;                                  // legal: implicit (short) cast
        return retries;
    }

    static short capRetriesConstant() {
        final short base = 1;
        short next = base + 1;                          // legal: base + 1 is a constant expression
        return next;
    }
}
```

**The follow-up they will ask** — "Does the same rule apply to `byte b = 10; b += 300;`?" Yes: `b += 300` compiles to `b = (byte)(b + 300)`, and `300` truncates to 8 low bits, giving `54`, not a range error, because the hidden cast never range-checks.

**Where this is written** — [`primitives-and-conversions/02a-assignment-and-bitwise.md`](primitives-and-conversions/02a-assignment-and-bitwise.md) §1, [`primitives-and-conversions/03a-promotion-boxing-and-inference.md`](primitives-and-conversions/03a-promotion-boxing-and-inference.md) §1.

---

### Q66. "Explain overload resolution when both `f(long)` and `f(Integer)` exist."

**The 30-second answer.** For an `int` argument, `f(long)` wins, always — resolution runs in three ordered phases (JLS §15.12.2), strict (identity/widening only) then loose (adds boxing/unboxing) then variable-arity, and the search stops at the first phase that finds any applicable candidate. `int → long` is a widening primitive conversion, legal in phase 1; `int → Integer` needs boxing, which phase 1 forbids. So `f(long)` is found in phase 1 and `f(Integer)` is never even examined in phase 2.

**The 5-minute answer.** The ordering "widening beats boxing beats varargs" is not a scoring function the compiler runs over one candidate pool — that is the wrong mental model, and it fails on the removal case. Delete `f(int)` from an overload set containing `f(int)`, `f(long)`, `f(Integer)` and call `f(someInt)`: phase 1 still finds `f(long)` applicable (widening), so it wins, even though `f(Integer)` "looks closer" by boxing intuition. Phase 2 (loose invocation, adds boxing/unboxing) only runs if phase 1's candidate set is empty. Most-specific tie-breaking (§15.12.2.5) only ever compares candidates *within* the phase that produced them — never across phases. A bare `null` argument makes every reference-typed overload applicable simultaneously (the null type is a subtype of every reference type); it resolves to the most specific one if the candidates are related by subtyping, and is a compile error (`reference to f is ambiguous`) if they are not — `f(Integer)` vs `f(Long)` with `null` is unrelated-siblings ambiguity, but a varargs `f(int...)` erasing to `int[]` also counts as a reference-typed candidate for `null`, which is the trap: `f(Integer)` and `f(int...)` both apply to `null` and neither is more specific, so it fails to compile even though it "obviously" should pick the boxed form.

```java
public final class StakeReservationService {
    static String reserve(int minorAmount)     { return "int"; }
    static String reserve(long minorAmount)    { return "long"; }
    static String reserve(Integer minorAmount) { return "Integer"; }
    static String reserve(int... minorAmounts) { return "varargs"; }

    public static void main(String[] args) {
        int stakeMinor = 420;
        System.out.println(reserve(stakeMinor));            // int      (phase 1, identity)
        // With reserve(int) deleted, reserve(stakeMinor) prints "long", not "Integer".
        System.out.println(reserve(Integer.valueOf(stakeMinor))); // Integer  (phase 1, identity on Integer)
        // reserve(null) does NOT compile: reserve(Integer) and reserve(int...) both
        // apply in phase 1 (int[] is a reference type too) and neither dominates.
    }
}
```

**The follow-up they will ask** — "What if `f(Integer)` and `f(long)` are the only two, called with a `short`?" `f(long)` wins: `short → int → long` widens in phase 1; `short` never boxes to `Integer` at all (it boxes to `Short`), so `f(Integer)` was never a candidate.

**Where this is written** — [`inheritance-and-dispatch/01a-overload-resolution-and-dispatch.md`](inheritance-and-dispatch/01a-overload-resolution-and-dispatch.md) §1–2, [`build-it/05j-overload-resolution-harness.md`](build-it/05j-overload-resolution-harness.md).

---

### Q67. "Overloading vs overriding — which is resolved when?"

**The 30-second answer.** Overloading is resolved by `javac` at compile time, from the static types of the receiver and arguments, and frozen permanently into the constant pool as one specific `Methodref`. Overriding is resolved by the JVM at every invocation of `invokevirtual`/`invokeinterface`, from the receiver's actual runtime class. Two different questions, two different machines, two different times — collapsing them is the single most common source of confused answers about Java dispatch.

**The 5-minute answer.** Formally: **resolution** (JVMS §5.4.3.3) turns a symbolic `Methodref` into a concrete declared method, once per constant-pool entry, using only the *static* type named in the class file. **Selection** (JVMS §5.4.6) then, only for `invokevirtual`/`invokeinterface`, walks from the receiver's runtime class for the most-derived override — and it happens on *every* call. `invokestatic` and `invokespecial` have no selection step at all: resolution alone decides what runs, which is what makes them non-virtual. Overload resolution lives entirely inside step one and is therefore compile-time-static; overriding lives entirely inside step two and is therefore runtime-dynamic. The trap that combines both in one statement: given `render(WithdrawalTransaction w)` and `render(CardWithdrawal w)`, a call `render(wt)` where `wt` is declared `WithdrawalTransaction` but holds a `CardWithdrawal` picks the *first* overload (static resolution on the declared type) — and then, inside that method, `w.label()` correctly dispatches to `CardWithdrawal.label` (dynamic selection). Half the statement is static, half is dynamic.

```java
class WithdrawalTransaction {
    static String rail() { return "generic"; }
    String label() { return "withdrawal"; }
}
class CardWithdrawal extends WithdrawalTransaction {
    static String rail() { return "card"; }              // hides, does not override
    @Override String label() { return "card withdrawal"; }
}
class DispatchProof {
    public static void main(String[] args) {
        WithdrawalTransaction wt = new CardWithdrawal();
        System.out.println(wt.rail() + " | " + wt.label());   // "generic | card withdrawal"
    }
}
```

`invokestatic WithdrawalTransaction.rail` runs the resolved method itself, `generic` — no selection step exists for a static method, so the subclass `rail()` merely hides it. `invokevirtual WithdrawalTransaction.label` resolves against the static type but *selects* `CardWithdrawal.label` at runtime, `card withdrawal` — same receiver, opposite outcome, because only one of the two instructions has a selection step.

**The follow-up they will ask** — "Why does a private method compile to `invokevirtual` on Java 21 but still behave non-virtually?" Because JEP 181 (nestmates, Java 11) changed the *instruction*, not the semantics: `private` members are never inherited and never overridable, so selection under `invokevirtual` walking from the runtime class has exactly one possible outcome — itself.

**Where this is written** — [`inheritance-and-dispatch/01-basics.md`](inheritance-and-dispatch/01-basics.md) §3, [`inheritance-and-dispatch/03-internals-dispatch.md`](inheritance-and-dispatch/03-internals-dispatch.md) §2.

---

### Q68. "Are fields polymorphic?"

**The 30-second answer.** No. A field access compiles to `getfield`/`putfield` against a `Fieldref` chosen by the *static type* of the qualifying expression, and `getfield` has no runtime selection step — there is nothing in its semantics that consults the object's actual class. So when a subclass declares a field with the same name as a superclass field, it does not override it; it **hides** it, and the object ends up holding two independent, simultaneously live fields. Which one a given expression reads is fixed at compile time and never revisited.

**The 5-minute answer.** Field resolution follows JLS §15.11.1: the meaning of `Primary.name` is determined by the *type* of `Primary`, not its runtime value, so a cast to a supertype — which does zero work at runtime — changes which `Fieldref` `javac` emits and therefore which slot is read. This is provably two real fields, not one field reinterpreted: `javap -p` on both classes shows a `status` entry in *each* class's own field table, at two distinct offsets in the object. Contrast with method overriding, where `invokevirtual` has a selection step that walks from the runtime class, producing exactly one reachable body regardless of the reference's declared type — "fields resolve by static type, methods by dynamic type" is the whole rule. The fix when polymorphism is genuinely wanted is unconditional: make the superclass field `private`, expose an accessor, and override the *accessor* — a method has the selection step a field never can.

```java
class WithdrawalTransaction {
    String state = "PENDING_VERIFICATION";
}
class CardWithdrawal extends WithdrawalTransaction {
    String state = "DEP-301 CAPTURED";                 // hides, does NOT override
}
public class HidingDemo {
    public static void main(String[] args) {
        CardWithdrawal cw = new CardWithdrawal();
        WithdrawalTransaction wt = cw;                  // same object, wider static type
        System.out.println(wt.state);                          // PENDING_VERIFICATION
        System.out.println(cw.state);                          // DEP-301 CAPTURED
        System.out.println(((WithdrawalTransaction) cw).state); // PENDING_VERIFICATION
    }
}
```

Three reads of the same object, two distinct `Fieldref` entries in the constant pool, two live `String` fields inside the one `CardWithdrawal` instance.

**The follow-up they will ask** — "What is the actual production symptom of this bug?" A superclass's own methods (`describe()`, `compareTo()`) were compiled against the superclass slot, so they read `PENDING_VERIFICATION` forever no matter what the subclass sets — a silent divergence between what the client sees and what the ledger reconciliation job reads, surviving every unit test that only exercises the subclass directly.

**Where this is written** — [`inheritance-and-dispatch/01-basics.md`](inheritance-and-dispatch/01-basics.md) §4, [`classes-and-initialization/01a-names-scope-and-var.md`](classes-and-initialization/01a-names-scope-and-var.md) §1.

---

### Q69. "What bytecode instruction does an interface call use, and does it matter?"

**The 30-second answer.** `invokeinterface`, chosen whenever the receiver expression's *compile-time type* is an interface — regardless of the object's actual runtime class. It resolves through a per-class interface method table (an "itable") rather than the fixed-slot method table ("vtable") a class-typed receiver uses, which is structurally more work: the JVM has to scan for the resolved interface before indexing within it. Whether that matters in practice depends entirely on the call site's shape: HotSpot's inline caches make a monomorphic `invokeinterface` site indistinguishable from `invokevirtual` once compiled, so the cost only shows up at a megamorphic site with many receiver classes actually flowing through it.

**The 5-minute answer.** On Oracle JDK 21.0.7, compiling and disassembling settles three folklore claims at once. A `private` **instance** method compiles to `invokevirtual` on 11 and 21 (`invokespecial` only on 8, before JEP 181 nestmates); a `private` **interface** method compiles to `invokeinterface`, following the receiver's static-type rule, not `invokespecial`; `final` methods emit ordinary `invokevirtual`, because `final` is a source-level constraint the class file does not encode as a different instruction. On 21, `invokespecial` means exactly two things: a constructor invocation (`"<init>"`) or an explicit `super.` call — nothing else uses it. The words "vtable" and "itable" appear nowhere in the JVMS; §5.4.3.3 (resolution) and §5.4.6 (selection) specify only the *outcome* — which method must run — and say nothing about data structures. HotSpot's implementation is a per-class array of method pointers where an override overwrites the inherited slot (so a fixed caller-side index always finds the right override), plus a separate per-class table of (interface, offset) pairs that `invokeinterface` searches before indexing, because a class can implement arbitrarily many interfaces with no shared numbering scheme. The genuinely correct answer to "does it matter" is call-site shape, not instruction choice: a monomorphic site gets a class check plus an inlined direct call from either instruction; only a megamorphic site — one where several distinct receiver classes actually flow through that specific bytecode index — pays the real table cost, and that is a property of the *call site*, not of how many implementations the interface has elsewhere in the process.

```java
public sealed interface PaymentRailPort permits CardRailAdapter, BankRailAdapter {
    void settle(RoundId roundId, Money amount);
}
// A settlement loop holding only CardRailAdapter at this call site is monomorphic
// and fully inlined, however many PaymentRailPort implementations exist elsewhere.
// Route both card AND bank settlements through the same loop, and the identical
// source line becomes megamorphic with no character changed.
```

**The follow-up they will ask** — "Does marking the implementing class `final` speed up the call?" No, measurably — a monomorphic site was already devirtualised by profile-guided speculation before `final` could contribute anything, and `final` cannot reduce the receiver population at a megamorphic site either, because the call is dispatched through the *interface* type, which `final` on one implementer does not change.

**Where this is written** — [`inheritance-and-dispatch/03-internals-dispatch.md`](inheritance-and-dispatch/03-internals-dispatch.md) §1, §3, §4.

---

### Q70. "What is `invokedynamic` used for in ordinary code you write?"

**The 30-second answer.** Three everyday cases: every lambda and method reference's creation site, string concatenation via `+` (since Java 9), and a record's generated `equals`/`hashCode`/`toString`. None of those are calls in the ordinary sense — each is a hole in the class file plus a bootstrap method that runs exactly once, on first execution, to decide what actually fills it. After that first run the call site is *linked* to a concrete target and behaves like a direct call from then on.

**The 5-minute answer.** The instruction carries a bootstrap-method index into the class file's `BootstrapMethods` attribute rather than naming a method directly. For a lambda, the bootstrap is `REF_invokeStatic java/lang/invoke/LambdaMetafactory.metafactory`, which spins a hidden class implementing the functional interface and returns a `CallSite`; the lambda's body becomes a private synthetic method on the enclosing class (`lambda$register$0`), compiled as an *instance* method (`REF_invokeVirtual`) if it captures `this` or touches instance state, or a *static* method (`REF_invokeStatic`) if it captures nothing. For string concatenation, the bootstrap is `REF_invokeStatic java/lang/invoke/StringConcatFactory.makeConcatWithConstants` — there is no `StringBuilder` anywhere in the bytecode on Java 9+, and the literal text around each spliced value travels as a static bootstrap argument, while the dynamic value travels in the call-site descriptor. For a record's generated methods, the bootstrap is `java.lang.runtime.ObjectMethods.bootstrap`, spinning the actual comparison/hash/format logic from the record's component list on first use. The measured consequence that trips people up: a **non-capturing** lambda's `CallSite` target is a *constant* — `LambdaMetafactory` can bind one shared instance into the linked site, so `nonCapturing() == nonCapturing()` is `true` and every evaluation after the first allocates nothing at all — while a **capturing** lambda must build a fresh instance per evaluation to carry its captures, so `capturing("DEP-301") == capturing("DEP-301")` is `false`. Neither identity fact is a specified guarantee — `LambdaMetafactory`'s own Javadoc explicitly disclaims it — but it explains real allocation-profile differences.

```java
final class BonusService {
    private final NotificationService notifications;

    void register(ClientId clientId, Money deposit) {
        String note = "DEP-301 CAPTURED bonus=" + deposit.amount();   // invokedynamic: concat
        Runnable audit = () -> notifications.record(clientId, note); // invokedynamic: lambda creation
    }
}
```

**The follow-up they will ask** — "Why didn't `javac` just keep compiling lambdas to anonymous classes, the way it did in early Java 8 betas?" Three reasons: class-count explosion (one loaded class per lambda site, all eager), strategy lock-in (the anonymous-class shape would be frozen into every class file forever, blocking future JDK improvements), and the singleton case above — an anonymous-class translation allocates on every evaluation even when nothing is captured, where `invokedynamic` lets the runtime bind a constant instead.

**Where this is written** — [`strings/04-internals-stringbuilder-and-concat.md`](strings/04-internals-stringbuilder-and-concat.md), [`inheritance-and-dispatch/03-internals-dispatch.md`](inheritance-and-dispatch/03-internals-dispatch.md) §5.

---

### Q71. "How much memory does an `Integer` cost versus an `int`?"

**The 30-second answer.** An `int` is 4 bytes and nothing else. An `Integer` is 16 bytes on a default 64-bit JDK 21: an 8-byte mark word plus a 4-byte compressed class pointer (12 bytes of header) plus the 4-byte payload, already a multiple of 8 so no padding. But the box does not *replace* the 4 bytes — a stored element still needs a 4-byte reference *to* the box, so a `List<Integer>` costs 20 bytes per element against 4 for an `int[]`: a measured, exact **5×**, not the "4×" people guess from counting only the object.

**The 5-minute answer.** `Long` is 24 bytes, not 20, because a `long` field must start on an 8-byte boundary and the 12-byte header ends 4 bytes short of one, forcing 4 bytes of padding before the field — `12 + 4 pad + 8 = 24`. Measured on Oracle JDK 21.0.7 (compressed oops on, `ObjectAlignmentInBytes = 8`): a `List<Integer>` of 2,800,000 elements is 56,000,376 bytes against 11,200,712 for the equivalent `int[]`, a ratio of exactly 5.00×; `List<Long>` of 1,000,000 is 28,000,200 bytes against 8,000,016 for `long[]`, 3.5×. The factor collapses to 1.00× when every value falls inside `IntegerCache` (`-128..127`, `AutoBoxCacheMax = 128`): a million cached-range boxes cost only their shared references, 4.00004 bytes per element, indistinguishable from an `int[]`. It does **not** collapse for a boxed *accumulator*, because the running total leaves the cached range on the second iteration and never returns — a boxed `Long sum` accumulator measured 24 bytes allocated per loop iteration, exactly one fresh `Long`, regardless of how small the input values are. And the box can vanish entirely if it never escapes a hot method: C2's escape analysis scalar-replaces a provably non-escaping box, measuring **zero** bytes allocated — but only under C2 (the interpreter and C1 allocate every box, measured at the full 32 bytes for two boxes/iteration), only if it does not cross an un-inlined method boundary, and never for anything actually stored.

```java
// Measured on JDK 21.0.7, ThreadMXBean.getThreadAllocatedBytes:
int[] primitiveIndex   = new int[2_800_000];              // 11,200,712 bytes  (4.000/element)
List<Integer> boxedIndex = new ArrayList<>(2_800_000);    // 56,000,376 bytes  (20.000/element)
// ratio: exactly 5.00x -- the 4-byte reference is ADDITIONAL, not instead of, the 16-byte Integer
```

**The follow-up they will ask** — "Does that mean I should avoid `Integer` everywhere?" No — below roughly 10⁴ elements the difference is a few kilobytes and readability wins outright; the 5× only matters once a collection reaches the six-figure range, and even then only for values outside the cache.

**Where this is written** — [`wrappers-and-boxing/03e-internals-wrapper-memory.md`](wrappers-and-boxing/03e-internals-wrapper-memory.md), [`wrappers-and-boxing/01g-the-cost-of-boxing.md`](wrappers-and-boxing/01g-the-cost-of-boxing.md), [`objects-equality-and-lifecycle/05-internals-object-layout.md`](objects-equality-and-lifecycle/05-internals-object-layout.md).

---

### Q72. "What is in an object header?"

**The 30-second answer.** Two words, 12 bytes total on a default 64-bit JDK 21 with compressed oops: an 8-byte **mark word** holding the identity hash (once computed), the lock state, and GC age/forwarding bits; and a 4-byte **compressed class pointer** identifying the object's `Klass` for dispatch, `checkcast` and GC tracing. Every object pays this fixed 12-byte tax regardless of how many fields it declares — a `boolean`-only object and an eight-field object both start with the identical header.

**The 5-minute answer.** The mark word's bit layout on JDK 21, for a normal unlocked object: `unused:25 hash:31 unused_gap:1 age:4 unused_gap:1 lock:2`, summing to 64 bits. The 31-bit `hash` field is why `System.identityHashCode` is never negative. The 4-bit `age` field is why `-XX:MaxTenuringThreshold` cannot exceed 15 — it is a field-width fact, not a policy choice. **Biased locking was disabled by default in 15 and removed outright in 18** (JEP 374); the second `unused_gap:1` bit is exactly where the old `biased_lock:1` bit lived, and any diagram still showing it is describing JDK 17 or earlier. A collision worth knowing: once an object's identity hash has been computed and cached in the mark word (via `System.identityHashCode`, `IdentityHashMap`, or the default `toString()`, which calls `hashCode()` internally), it can never again encode a lightweight thin-lock, and any later `synchronized` on it must inflate directly to a heavyweight monitor — a debug log line calling an object's default `toString()` is therefore a real locking-relevant side effect, not a free read. `UseCompactObjectHeaders` **does not exist on JDK 21** — a full flag dump returns nothing; Project Lilliput's compact headers are experimental in JDK 24 (JEP 450) and product (still opt-in) in JDK 25 (JEP 519), dropping the header to 8 bytes by folding the class pointer into the mark word's spare bits.

```
// JOL internals output, JDK 21.0.7:
OFF  SZ TYPE  DESCRIPTION            VALUE
  0   8       (object header: mark)  0x0000000000000001
  8   4       (object header: class) 0x01050400
 12   4  int  Movement.amountMinor   0
Instance size: 16 bytes    // 12-byte header + 4-byte int, no padding
```

**The follow-up they will ask** — "What happens above a ~32 GiB heap?" `UseCompressedOops` turns off ergonomically (measured threshold: `-Xmx31g` stays compressed, `-Xmx32g` does not), doubling every reference field to 8 bytes — the class pointer widens too, so the header can grow to 16 bytes — meaning a heap bump from 31 to 33 GiB can *reduce* effective capacity because every reference in the process doubled.

**Where this is written** — [`objects-equality-and-lifecycle/05-internals-object-layout.md`](objects-equality-and-lifecycle/05-internals-object-layout.md), [`objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`](objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md).

---

### Q73. "How do you serialize safely, and why is Java serialization a security problem?"

**The 30-second answer.** `ObjectInputStream.readObject()` is not a parser, it is an interpreter: the byte stream names classes as text, and the JVM resolves those names, loads the classes, allocates instances *without running their constructors*, and executes every `readObject`/`readResolve`/`validateObject` hook present on every class in the graph — all before your code's cast or `instanceof` ever runs. An attacker who controls the bytes controls what code runs, using only classes already on your classpath (a "gadget chain"). Safety comes from an allow-list filter (JEP 290's `ObjectInputFilter`, terminated with `!*`) on anything that must stay Java serialization, and — the actual fix — never using Java's built-in serialization for persistence or a wire format at all; use JSON/Protobuf/Avro instead.

**The 5-minute answer.** The mechanism, concretely: class resolution happens on attacker-controlled text before any `serialVersionUID` check (an edited class name in a captured stream produced `ClassNotFoundException`, proving resolution runs first); the constructor-bypass allocates via a synthesized path with no invariant checks; and hooks then run on the half-built object. Measured on Oracle JDK 21.0.7 with no filter configured, `ObjectInputFilter.Config.getSerialFilter()` returns `null` — an unconfigured process rejects nothing. `ObjectInputFilter.checkInput` returns `ALLOWED`/`REJECTED`/`UNDECIDED`, and `UNDECIDED` with nothing else deciding **defaults to allow** — which is why every hand-written pattern filter must end in a catch-all `!*`; a filter that only names allowed classes and forgets the terminator is a partial allow-list that silently permits everything else. Filters exist at three scopes — per-stream, process-wide (`jdk.serialFilter`), and, since JDK 17 (JEP 415), a filter *factory* that composes the process filter with a per-stream one instead of one silently overriding the other. The blind spot to name explicitly in an interview: `jdk.serialFilter` covers only calls into `ObjectInputStream.readObject()` — it does nothing for Jackson with polymorphic type handling enabled, SnakeYAML's default loader, or Kryo, all of which face the identical class of vulnerability (attacker data naming a class that gets instantiated) through a completely different API the filter never sees.

```java
final class PaymentRunImportFilter implements ObjectInputFilter {
    private static final Set<String> ALLOWED = Set.of(
        "com.quizstakes.payments.PaymentRun", "com.quizstakes.money.Money",
        "java.math.BigDecimal", "java.util.Currency");
    @Override public Status checkInput(FilterInfo info) {
        if (info.depth() > 20 || info.streamBytes() > 1_000_000L) return Status.REJECTED;
        Class<?> clazz = info.serialClass();
        if (clazz == null) return Status.UNDECIDED;       // non-class checks defer
        return ALLOWED.contains(clazz.getName()) ? Status.ALLOWED : Status.REJECTED;
    }
}
```

**The follow-up they will ask** — "Does casting the result of `readObject()` protect you?" No — `(LedgerEntry) ois.readObject()` checks the *result*, not the side effects; every class in the graph has already been resolved, allocated and had its hooks run before that cast token is even reached.

**Where this is written** — [`serialization/02c-attack-surface-filters-and-the-practical-rule.md`](serialization/02c-attack-surface-filters-and-the-practical-rule.md), [`serialization/02-serialization.md`](serialization/02-serialization.md).

---

### Q74. "What is `serialVersionUID` for?"

**The 30-second answer.** It is a fingerprint of a class's *shape* — name, modifiers, interfaces, field descriptors, method signatures — checked at read time before any expensive field-by-field reconciliation. If you do not declare one, the compiler computes an 8-byte SHA-1-derived digest of that shape at class-load time, and *any* shape change — even adding one unrelated field — produces a completely different UID, silently invalidating every stream already written under the old shape. The fix is to declare it explicitly: `private static final long serialVersionUID = 1L;`, which decouples the UID from the compiler's exact output.

**The 5-minute answer.** Per the Java Object Serialization Specification §4.6, the default UID is the first 8 bytes of a SHA-1 digest over a canonical description: class name, modifiers, sorted interface names, each non-transient non-static field's modifiers and descriptor (sorted by name), `<clinit>` if present, and constructor/method modifiers and descriptors. Measured on JDK 21.0.7: a class with two fields computed `760042420889516798`; adding one unrelated `long` field, nothing else, changed it to `2193869912748673154` — a wholesale change with nothing in the diff resembling a version bump. Class resolution by name happens *before* the UID is compared — a byte-edited class name in a stream produces `ClassNotFoundException`, not `InvalidClassException` — so the ordering is name first, shape second. A UID mismatch produces `InvalidClassException` naming both values, e.g. `local class incompatible: stream classdesc serialVersionUID = 1, local class serialVersionUID = 2`, regardless of whether the actual field values would have been perfectly readable. **Records default to `0L`, not a computed hash** — `ObjectStreamClass.lookup(SomeRecord.class).getSerialVersionUID()` returns `0`, and stream UID matching is not enforced for records at all, because records reconstruct through their canonical constructor rather than raw field reflection. Every `Serializable` class in an inheritance chain needs its *own* declared UID — a subclass does not inherit its superclass's value.

```java
class Led implements Serializable {
    private static final long serialVersionUID = 1L;   // pin the shape fingerprint
    int stakeMinor;
    String clientId;
}
```

**The follow-up they will ask** — "Is changing a field's declared type a compatible change?" No — of the standard compatibility rows, changing a field's type, renaming a field, and changing between `Serializable`/`Externalizable` or class/enum/record are all incompatible and throw `InvalidClassException`; adding a field is compatible (the reader leaves it at its type default) and removing one is compatible-but-lossy (the stream's value for it is silently discarded, no error).

**Where this is written** — [`serialization/02-serialization.md`](serialization/02-serialization.md) §2, §4.

---

### Q75. "What does `readResolve` do, and why do enums not need it?"

**The 30-second answer.** `readResolve()` lets a class substitute a different object — typically a canonical singleton — for the one `ObjectInputStream` just built by reflection, *after* fields have already been populated on a throwaway instance. Enums do not need it because the Java Object Serialization Specification gives enum constants their own fixed protocol: they serialize as their constant *name* (text) and deserialize via `Enum.valueOf(EnumType, name)`, which either returns the existing singleton or throws — there is no field-reflection bypass to construct a competing instance in the first place, so there is nothing for `readResolve` to patch.

**The 5-minute answer.** `readResolve` is a patch applied *after* the bypass has already run, and it is provably vulnerable while doing so: every non-`transient` reference field on a `readResolve`-protected class is a "stolen-reference" hole, because an attacker can craft a stream where a second object's `readObject` runs and captures a reference to one of the throwaway instance's fields *before* `readResolve` swaps that instance out — the fix is that every reference field on such a class must be `transient`, with no exception. `readResolve` is also **inherited** (unlike `writeObject`/`readObject`, which must be exactly `private` and are never inherited), so a subclass silently inherits a superclass's singleton substitution unless it declares its own. Measured proof of the enum contrast on Oracle JDK 21.0.7: an enum with `writeObject`, `readObject`, `writeReplace` and `readResolve` all declared to throw on invocation round-tripped cleanly — none of the four hooks fired, `deserialized == BonusState.CLAWED_BACK` was `true`, and `ObjectStreamClass.lookup(BonusState.class).getFields()` returned an *empty array* — no field data is written for an enum constant at all; the entire wire form is class identity plus the literal constant name. Byte-editing that name in a captured stream produced `InvalidObjectException: enum constant XXPIRED does not exist in class...`, confirming the wire format really is the name and nothing else.

```java
private Object readResolve() {
    return INSTANCE;    // patches the bypass after it already ran -- vulnerable to the stolen-reference attack
}
// versus, structurally immune:
enum BonusState { GRANTED, ACTIVE, CONSUMED, EXPIRED, CLAWED_BACK }   // Enum.valueOf(name) -- no bypass exists
```

**The follow-up they will ask** — "What's the more robust fix than `readResolve` for a non-enum class with real invariants?" The serialization proxy pattern: `writeReplace` swaps in a dumb proxy holding only primitives, the proxy's `readResolve` calls the real class's ordinary validating constructor, and the real class's own `readObject` is overridden to throw — closing the direct-forgery path the proxy alone does not block.

**Where this is written** — [`serialization/02a-magic-methods-and-constructor-bypass.md`](serialization/02a-magic-methods-and-constructor-bypass.md) §3–4.

---

### Q76. "What is `strictfp` and is it still meaningful?"

**The 30-second answer.** It is a no-op since Java 17. It used to force every intermediate floating-point result to round to strict binary32/binary64 at each step, preventing the wider 80-bit x87 intermediates some pre-SSE2 32-bit x86 hardware was otherwise allowed to use, which could make the identical program produce different bits on different machines. JEP 306 (Java 17) made strict evaluation the *only* mode for every platform, so the keyword still compiles — for source compatibility — but changes nothing, and `javac` now warns when it sees it.

**The 5-minute answer.** The proof is a class-file flag, `ACC_STRICT` (`0x0800`), that `javac` used to emit for a `strictfp`-annotated method. Compiling identical source with `--release 21` shows both the `strictfp` method and a plain method with `flags: (0x0000)` — byte-for-byte identical. Recompiling the *same* source with `--release 16` (one release before JEP 306) flips the flag back on for the `strictfp` method only: `flags: (0x0800) ACC_STRICT`. The `--release 21` compile also emits an explicit warning: `as of release 17, all floating-point expressions are evaluated strictly and 'strictfp' is not required`. `0x0800` itself is not retired from the JVMS — `javac` simply stopped emitting it for this purpose once there was no longer a strict-versus-non-strict distinction to record.

```java
public class Sfp {
    strictfp double strictSplit(double stake) { return stake * 0.10; }  // flags: (0x0000) on 21
    double plainSplit(double stake) { return stake * 0.10; }            // flags: (0x0000) -- identical
}
```

**The follow-up they will ask** — "Is `Math` bit-for-bit identical to `StrictMath` then?" No — that is a separate, still-live distinction: `StrictMath` is specified to match the `fdlibm` reference algorithms on every platform; `Math` is bound only to a documented ulp error (typically 1–2 ulp) and may use a faster platform intrinsic, so the two can legitimately diverge even though they agreed on every value tried on this build. Neither has anything to do with `strictfp`, which only ever governed intermediate-precision width, not algorithm choice.

**Where this is written** — [`numbers-and-money/04b-internals-strictfp-strictmath-and-fma.md`](numbers-and-money/04b-internals-strictfp-strictmath-and-fma.md) §1–2.

---

### Q77. "What is `var` and where can't you use it?"

**The 30-second answer.** `var` (Java 10, JEP 286) is local variable type inference — a compile-time-only abbreviation, never dynamic typing. The compiler infers exactly one fixed static type from the initializer, once, at declaration, and that type is what ends up in the class file's local variable table, indistinguishable from a hand-spelled declaration. It is banned wherever the type is part of a contract other code compiles against — fields, method/constructor parameters, return types — and it fails (for a different, semantic reason) wherever the initializer has no standalone type of its own: `null`, a bare lambda or method reference, an array initializer with no explicit type, or no initializer at all.

**The 5-minute answer.** There are two distinct failure families, and knowing which is which is the actual test. `'var' is not allowed here` is a **grammar** rejection — the position is syntactically off-limits because it is part of an API surface (a field, a parameter, a return type) that other compilation units bind against; inferring it there would make the class's API depend on its own body. `cannot infer type for local variable x` is a **semantic** rejection — `var` was syntactically legal, but the initializer is a *poly expression* with no type until a target type is supplied (a bare lambda, a bare method reference, an array initializer) or is the null type, which JLS §4.1 says "has no name" and so cannot be a declared type. The genuinely surprising fact: `var` can capture a type the declaration grammar cannot even *spell*. Assigning `var gate = new StakeGate() { int consulted() { return 1; } };` infers the variable's type as the anonymous class itself (measured `getClass().getName()` → `GateProbe$1`), so `gate.consulted()` resolves — declare the identical body with the interface type `StakeGate gate = ...` instead and the same call fails to compile, `cannot find symbol`. The same applies to an intersection type from a cast, `(Comparator<String> & Serializable)` — no variable declaration syntax can name that type at all, only `var` can hold it.

| Context | Fails as | Family |
|---|---|---|
| field, method/constructor param, return type | `'var' is not allowed here` | grammar |
| `var[] arr` | `not allowed as an element type of an array` | grammar |
| `var a = 1, b = 2;` | `not allowed in a compound declaration` | grammar |
| `var x = null;` | `cannot infer type` — null type has no name | semantic |
| `var f = () -> 1;` | `cannot infer type` — lambda needs a target type | semantic |
| `var z;` (no initializer) | `cannot infer type` — nothing to infer from | semantic |

```java
interface StakeGate { boolean permits(long minorUnits); }

final class GateProbe {
    public static void main(String[] args) {
        var gate = new StakeGate() {
            private int consulted = 0;
            @Override public boolean permits(long minorUnits) {
                consulted++;
                return minorUnits <= 4_200L;
            }
            int consulted() { return consulted; }
        };
        System.out.println(gate.permits(333L));   // true
        System.out.println(gate.consulted());     // 1 -- only reachable because var infers GateProbe$1
    }
}
```

**The follow-up they will ask** — "Is `var stakeCount = 0; stakeCount = "AO-400";` legal?" No — plain `incompatible types` error. `var` fixes the static type at declaration; nothing about it is re-checked or reconsidered on later assignments, which is the whole proof that it is inference, not dynamic typing.

**Where this is written** — [`classes-and-initialization/01a-names-scope-and-var.md`](classes-and-initialization/01a-names-scope-and-var.md) §2.

---

### Q78. "What changed in Java 21 that you actually use?"

**The 30-second answer.** Five things finalized in 21, all engineering-relevant: virtual threads (JEP 444), pattern matching for `switch` (JEP 441), record patterns (JEP 440), sequenced collections (JEP 431), and generational ZGC (JEP 439). String templates (JEP 430) were *preview only* in 21 and were later withdrawn entirely in 23 — a common misattribution to avoid stating as fact.

**The 5-minute answer.** Virtual threads: a `Thread` whose continuation mounts onto a small pool of platform carrier threads and unmounts at every blocking point, so a blocking call parks a heap-allocated continuation rather than holding a ~1 MB OS stack — a service handling 1,200/sec blocking reservations no longer needs 1,200 platform threads to do it. One real caveat worth naming: through Java 23, a virtual thread blocking inside a `synchronized` block *pins* its carrier (JEP 491 removed that pinning only in JDK 24), so the pre-24 advice to rewrite hot `synchronized` sections as `ReentrantLock` for virtual-thread code is still correct on a 21 target. Pattern matching for `switch` plus record patterns together let a `switch` deconstruct a sealed hierarchy exhaustively with no `default`, which is a real correctness win — adding a new sealed subtype without updating every matching `switch` becomes a compile error instead of a silent fall-through. Sequenced collections (`SequencedCollection`, `getFirst()`/`getLast()`/`reversed()`) finally give ordered collections symmetric first/last access without a cast to `LinkedList` or `Deque`. Generational ZGC adds young/old generations to ZGC's low-pause collector — Java 23 makes it the ZGC default, but on 21 it must still be requested.

```java
static StatusCode disposition(Verdict v) {
    return switch (v) {                                             // exhaustive, no default
        case DocumentVerdict(StatusCode code, boolean referred) -> code;   // record pattern
        case ScreeningVerdict(StatusCode code, boolean prohibited) -> code;
        case ReviewVerdict(StatusCode code, String operatorId) -> code;
        case WealthVerdict(StatusCode code, Money income) -> code;
    };
}
static StatusCode latestStatus(SequencedCollection<StatusCode> trail) { return trail.getLast(); }
```

**The follow-up they will ask** — "What's still preview in 21 that people mistakenly cite as final?" String templates (JEP 430, preview 1 in 21, preview 2 in 22, withdrawn in 23 with no replacement) and unnamed patterns/variables (JEP 443, preview 1 in 21, final in 22) — the second one *is* final one release later, which is exactly the kind of off-by-one attribution worth double-checking before an interview answer.

**Where this is written** — [`language-substrate/04a-internals-version-history-18-onward.md`](language-substrate/04a-internals-version-history-18-onward.md).

---

### Q79. "How would you find out whether a boxing allocation is happening in a hot loop?"

**The 30-second answer.** Layer the investigation, cheapest first: JOL to confirm what one box costs in isolation; `jdk.ExceptionStatistics`-style periodic counters or, for allocation specifically, JFR's `jdk.ObjectAllocationSample` to see the rate and which types dominate; async-profiler in `-e alloc` mode to attribute the allocation to a specific call site; and `jcmd <pid> GC.class_histogram` for an exact (but full-GC-forcing) live census. Never trust a microbenchmark's zero at face value — a small, hot, single-implementation method with a discarded result is exactly the shape C2's escape analysis optimizes best, so a benchmark showing zero allocation may be measuring the best case a production call shape can never reach.

**The 5-minute answer.** The reason this needs real instrumentation rather than reasoning from the source: scalar replacement is a **C2-only** phase. The identical boxing bytecode allocates the full amount under the interpreter, under C1, and during any cold/ramp-up period, and allocates zero only once C2 has proven the box never escapes its compilation unit and the JIT has actually promoted the method — measured on JDK 21.0.7, a non-escaping two-box-per-iteration loop allocated 0 bytes by default but 160,000,000 bytes (32 bytes/iteration, the honest cost) under `-XX:-DoEscapeAnalysis`, under `-Xint`, and under `-XX:TieredStopAtLevel=1`. The escape depends on inlining budgets you do not control from the source: a 15-byte `Integer`-returning helper measured 0 bytes when inlined (`PrintInlining` says `inline (hot)`) and the full 16 bytes/iteration once inlining was denied (`too big`) — same source, only the surrounding code's size changed. And it never applies to anything actually *stored*: a box published into a `List<Integer>` audit trail measured 16 bytes/iteration and that figure did not move by a single byte with escape analysis disabled, proof the optimization was never even attempted on it. The correct measurement instrument is `com.sun.management.ThreadMXBean.getThreadAllocatedBytes` — exact, GC-independent, no warmup ambiguity — cross-checked against the same shape under `-XX:-DoEscapeAnalysis` to price what the optimization is worth and under `-XX:TieredStopAtLevel=1` to price the cold-path cost, since that is what every request served before the JIT warms up actually pays.

```java
ThreadMXBean bean = (ThreadMXBean) ManagementFactory.getThreadMXBean();
long before = bean.getThreadAllocatedBytes(Thread.currentThread().getId());
run(reservations);                                    // the real call shape, not a synthetic snippet
long bytes = bean.getThreadAllocatedBytes(Thread.currentThread().getId()) - before;
// Then repeat under -XX:-DoEscapeAnalysis and -XX:TieredStopAtLevel=1 to price both boundaries.
```

**The follow-up they will ask** — "Why does JFR's allocation sample disagree with async-profiler's call-site ranking?" Because they sample differently: `jdk.ObjectAllocationSample` is throttled to a fixed *event rate* (150–300/s), so its type attribution is reliable but its byte totals are not; async-profiler samples per *bytes allocated*, so a rare huge array can outrank a frequent small box. Reconcile with `GC.class_histogram`'s exact live census, at the cost of a full GC pause.

**Where this is written** — [`language-substrate/05-internals-observability.md`](language-substrate/05-internals-observability.md) §4, [`wrappers-and-boxing/03d-internals-escape-analysis.md`](wrappers-and-boxing/03d-internals-escape-analysis.md), [`cost-model/02a-measurement-and-amortisation.md`](cost-model/02a-measurement-and-amortisation.md) §4.

---

### Q80. "Given a stack trace with `Caused by` and `Suppressed`, tell me the sequence of events."

**The 30-second answer.** `Caused by:` is the chain of `cause` fields, set once at construction (or via `initCause`) and printed bottom-up in the sense that the *deepest* `Caused by:` block is almost always the real root cause — everything above it is translation and re-wrapping on the way back to the surface. `Suppressed:` is unrelated to causation: it is exceptions thrown while a `try`-with-resources block was closing resources *during* the unwind of a primary exception, attached via `addSuppressed` so neither is discarded — a suppressed exception is nested *under* the block it happened inside, never a cause of it, and each block can carry its own independent `Caused by:` chain.

**The 5-minute answer.** Construction order: a translating `catch` block builds a new exception with the caught one passed as `cause` (`throw new LedgerImbalanceException(msg, e)`), so `getCause()` on the new exception returns `e`; omitting the cause argument — writing the caught exception's message into a new string instead — permanently and silently deletes it, with no visible sign in the shortened trace that anything is missing. Suppression is populated independently and later: when a `try`-with-resources body has already thrown and a resource's `close()` also throws, the compiler calls `primary.addSuppressed(closeException)` rather than letting the close exception replace the primary (which is exactly what the pre-Java-7 hand-written `finally { r.close(); }` form does — measured, that form loses the original exception outright, with no `Suppressed:` and no `Caused by:` line at all, because JLS §14.20.2 makes an exception thrown from `finally` unconditionally *replace* whatever was already propagating). If the body succeeds and only `close()` fails, the close exception becomes primary directly, with nothing suppressed under it. The `... N more` fold line inside a captured trace is the one legitimate `...` in this note set: `Throwable.printEnclosedStackTrace` walks this exception's own frame array and the *enclosing* trace's frame array backward from the end while `StackTraceElement.equals()` holds (comparing class, line, method, file, and since Java 9 module identity), and reports the count of frames it declined to reprint because they are already printed, verbatim, in the block immediately above — not frames that were dropped or truncated.

```
Exception in thread "main" LedgerImbalanceException: stake settlement failed for round-771
	at TraceDemo.settleStake(TraceDemo.java:28)
	at TraceDemo.main(TraceDemo.java:33)
Caused by: java.lang.IllegalStateException: ledger write failed for connection primary
	at TraceDemo$LedgerConnection.writeMovement(TraceDemo.java:6)
	at TraceDemo.writeLedgerEntries(TraceDemo.java:20)
	at TraceDemo.settleStake(TraceDemo.java:26)
	... 1 more
	Suppressed: java.lang.RuntimeException: close failed for connection primary
		at TraceDemo$LedgerConnection.close(TraceDemo.java:10)
		at TraceDemo.writeLedgerEntries(TraceDemo.java:19)
		... 2 more
```

Read bottom-up for the root cause (`IllegalStateException`, the ledger write itself); read the `Suppressed:` block as a sibling finding from cleanup, nested at greater indentation because it happened while unwinding from the `Caused by:` exception it sits under; the `... 1 more` and `... 2 more` lines name shared frames already printed above, not missing ones.

**The follow-up they will ask** — "What if the two exceptions form a cycle — `A`'s cause is `B` and `B`'s cause is `A`?" The printer guards against it with an identity-keyed visited set and prints `[CIRCULAR REFERENCE: <toString of the repeated throwable>]` instead of recursing forever — reachable only through `initCause`/reflection, since the ordinary chaining constructors never permit building the cycle in the first place.

**Where this is written** — [`exceptions/01a-throwable-api-and-chaining.md`](exceptions/01a-throwable-api-and-chaining.md) §2, [`exceptions/01c-try-with-resources-and-suppression.md`](exceptions/01c-try-with-resources-and-suppression.md) §2–3, [`exceptions/03d-internals-npe-messages-and-diagnostics.md`](exceptions/03d-internals-npe-messages-and-diagnostics.md) §3.

---

## Where to go next

The wrong-but-plausible answers to this exact question set, and the version-stale claims interviewers still expect, are catalogued in [`94e-interview-trap-index.md`](94e-interview-trap-index.md). The spaced-repetition schedule, the atomic-concept checklist, and the puzzle set for rehearsing all eighty questions are in [`94f-interview-drills-and-retention.md`](94f-interview-drills-and-retention.md). Neither is duplicated here.

---

**Leaves covered:** 5.1.65–5.1.80 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 430
