# 03 Java Core — Part 3 interview wrap-up — INTERNALS (§3.1–§3.18)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](00-index.md)
Previous: [Part 2 interview wrap-up](91-interview-intermediate.md) · Next: [Part 4 interview wrap-up](93-interview-build-it.md)

## Summary table

| Section | The mechanism it owns | The constant or name you must be able to recite | Where it is written |
|---|---|---|---|
| §3.1 javac pipeline and class file | Six-phase compiler pipeline (parse→enter→annotate→attribute→flow→desugar→generate) and the binary class-file layout it emits | Magic `0xCAFEBABE`; major version 65 for Java 21 (`major = 44 + N`) | [javac pipeline](language-substrate/03-internals-javac-and-class-file.md) |
| §3.2 String internals | `String`'s compact-string field layout, hash memoisation, and the native intern pool | `@Stable final byte[] value`; `hashIsZero` (Java 13); `StringTableSize = 65536` | [String internals](strings/03-internals-string.md) |
| §3.3 StringBuilder and indified concat | `AbstractStringBuilder` growth arithmetic and `invokedynamic` string concatenation | Growth `2 * old + 2`; `StringConcatFactory.makeConcatWithConstants` (JEP 280) | [StringBuilder and concat internals](strings/04-internals-stringbuilder-and-concat.md) |
| §3.4 boxing internals | `Integer.valueOf`'s cache fill path, the other five wrapper caches, and escape analysis's effect on boxing | `AutoBoxCacheMax = 128`; `IntegerCache.low = -128` | [boxing internals](wrappers-and-boxing/03-internals-boxing.md) |
| §3.5 erasure internals | Type-variable and parameterized-type erasure, bridge methods, and heap pollution | `Signature` attribute; `ACC_BRIDGE = 0x0040` | [erasure internals](generics/03-internals-erasure.md) |
| §3.6 class loading and initialization | The loading→linking→initialization pipeline and the per-class initialization lock | `<clinit>`; the twelve-step JVMS §5.5 procedure | [class loading and init](classes-and-initialization/03-internals-class-loading-and-init.md) |
| §3.7 method dispatch | The five invoke instructions, resolution vs. selection, and inline caches | `invokevirtual`/`invokespecial`/`invokeinterface`/`invokestatic`/`invokedynamic` | [dispatch internals](inheritance-and-dispatch/03-internals-dispatch.md) |
| §3.8 object layout | The object header, mark word, and field-reordering algorithm | 12-byte header (compressed oops); `ObjectAlignmentInBytes = 8` | [object layout](objects-equality-and-lifecycle/05-internals-object-layout.md) |
| §3.9 exception mechanics | The exception table, `fillInStackTrace`, fast-throw substitution, and helpful NPE messages | `MaxJavaStackTraceDepth = 1024`; `OmitStackTraceInFastThrow = true` | [exception mechanics](exceptions/03-internals-exception-mechanics.md) |
| §3.10 enum internals | The compiler-synthesized enum shape: `$VALUES`, the injected constructor, and `$SwitchMap` | `$VALUES`; `ACC_ENUM = 0x4000` | [enum internals](enums/03-internals-enums.md) |
| §3.11 nested-class internals | Captured-local fields, the enclosing-instance field, and nestmate access | `this$0`; `NestMembers` (JEP 181, Java 11) | [nested-class internals](inheritance-and-dispatch/04-internals-nested-classes.md) |
| §3.12 final semantics and constant folding | Constant variables, the final-field freeze, and `@Stable` | `ConstantValue` attribute; JLS §17.5 freeze | [final and constant folding](classes-and-initialization/04-internals-final-and-constant-folding.md) |
| §3.13 hashCode internals | The mark word's identity-hash bits and a record's `hashCode` bootstrap | `hash:31` bits in the mark word; `TREEIFY_THRESHOLD = 8` | [hashCode internals](objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md) |
| §3.14 BigDecimal/BigInteger internals | The unscaled-value/scale representation and Karatsuba/Toom-Cook multiplication thresholds | `INFLATED = Long.MIN_VALUE`; `KARATSUBA_THRESHOLD = 80` words | [BigDecimal internals](numbers-and-money/03-internals-bigdecimal.md) |
| §3.15 floating-point internals | IEEE 754 binary64/32 layout, ulp, and compensated summation | 52 stored mantissa bits; canonical NaN `0x7FF8000000000000` | [floating-point internals](numbers-and-money/04-internals-floating-point.md) |
| §3.16 java.time internals | `Instant`/`LocalDate` field layout and `ZoneRules`'s gap/overlap resolution | `Instant` = `long seconds` + `int nanos`; tzdb `2025a` | [java.time internals](date-and-time/03-internals-java-time.md) |
| §3.17 version history | The Java 1.0–25 feature timeline and which release changed which default | JEP 254 (9), JEP 280 (9), JEP 358 (15), JEP 400 (18) | [version history](language-substrate/04-internals-version-history.md) |
| §3.18 observability toolkit | The `javap`/`jcmd`/JFR/async-profiler toolkit for verifying every claim above | `javap -c -p -v`; `jcmd <pid> VM.flags` | [observability](language-substrate/05-internals-observability.md) |

## The twenty numbers of Part 3

| Number | What it is | Section |
|---|---|---|
| `0xCAFEBABE` | The class file's fixed four-byte magic number | §3.1 |
| 65 | The class-file major version for Java 21 (`44 + N`) | §3.1 |
| 65536 | `StringTableSize`, the default number of buckets in the native intern pool | §3.2 |
| `2 * old + 2` | `AbstractStringBuilder`'s growth formula, not plain doubling | §3.3 |
| 128 | `AutoBoxCacheMax`, the default configurable ceiling of `IntegerCache` | §3.4 |
| 256 | `IntegerCache`'s default array length, `(127 - (-128)) + 1` | §3.4 |
| `0x0040` | `ACC_BRIDGE`, the class-file flag marking a compiler-synthesized bridge method | §3.5 |
| 12 | The number of ordered steps in JVMS §5.5's class-initialization procedure | §3.6 |
| 5 | The number of method-invocation instructions in the JVM instruction set | §3.7 |
| 12 bytes | The object header under compressed oops (8-byte mark word + 4-byte class pointer) | §3.8 |
| 8 | `ObjectAlignmentInBytes`, the alignment every object size rounds up to | §3.8 |
| 1024 | `MaxJavaStackTraceDepth`, the default cap on frames `fillInStackTrace()` captures | §3.9 |
| `true` | `OmitStackTraceInFastThrow`'s default value, substituting stackless hot exceptions | §3.9 |
| `0x4000` | `ACC_ENUM`, the class-file flag marking an enum class or constant | §3.10 |
| Java 11 | The release that added `NestMembers` and retired the `access$000` accessor bridge (JEP 181) | §3.11 |
| JLS §17.5 | The clause specifying the final-field freeze at constructor exit | §3.12 |
| 31 bits | The width of the identity-hash field inside the object mark word | §3.13 |
| 80 words | `KARATSUBA_THRESHOLD`, `BigInteger`'s schoolbook-to-Karatsuba multiplication cutover | §3.14 |
| 52 | The stored mantissa bits of a `double` (53 effective, with the implicit leading bit) | §3.15 |
| `2025a` | The tzdb version bundled with this build, covering 603 available zone ids | §3.16 |

## Interview Q&As

### "Walk me through what javac actually does, phase by phase, and draw the line between what's decided at compile time and what's decided at run time."

javac runs a fixed six-phase pipeline, always in the same order: parse, enter, annotation processing, attribute, flow, desugar, generate. Annotation processing runs to a fixed point across multiple rounds, with `processingOver()` true only on the final one. What's decided purely at compile time: overload resolution from the static argument types, erasure of every generic type, definite-assignment and reachability checking, constant folding of compile-time constant expressions, and insertion of every boxing/unboxing call and narrowing `checkcast`. What's decided at run time: which overridden method body actually executes (dispatch, from the receiver's runtime class), class initialization order and timing, garbage collection, and every JIT compilation decision.

A concrete boundary makes this vivid: a `static final int` initialized with a literal becomes a `ConstantValue` attribute, and every caller's read is folded to a `bipush`/`ldc` with zero `getstatic` and zero reference to the declaring class anywhere in the caller's binary — changing that value later requires recompiling every caller, because nothing at run time ever re-reads it. Contrast `static final BigDecimal GRANT_CAP = new BigDecimal("100.00")`: not a constant expression (a `new` call, not a literal), so it stays a real field, the caller emits a genuine `getstatic`, and that instruction triggers class initialization of the declaring class the first time it executes.

```java
final class BonusRules {
    static final int MAX_BONUS = 100;                       // ConstantValue, inlined everywhere
    static final java.math.BigDecimal GRANT_CAP =
            new java.math.BigDecimal("100.00");              // real field, real getstatic
}
```

`javap -c` on a caller reading `MAX_BONUS` shows `bipush 100` with no `Fieldref` in the constant pool at all; the same caller reading `GRANT_CAP` shows `getstatic #7 // Field BonusRules.GRANT_CAP:Ljava/math/BigDecimal;`. The follow-up interviewers ask next is "what does javac never do" — inlining across method calls, loop optimization, or any constant propagation beyond JLS §15.29's narrow definition of a constant expression; every one of those is C1/C2's job at run time, not javac's.

### "What fields does String actually carry, and why does it need both `hash` and `hashIsZero`?"

`String` on Java 21 has exactly four instance fields: `@Stable final byte[] value` holding the compact-string payload, `final byte coder` recording whether that payload is Latin-1 (`0`) or UTF-16 (`1`), a mutable `int hash` memoising the computed hash code, and a `boolean hashIsZero`, added in Java 13, that disambiguates "hash not computed yet" from "hash genuinely computed to zero." Before that field existed, any string whose true polynomial hash happened to land on exactly zero — the empty string always, and any sufficiently unlucky non-empty string — recomputed its full hash on every single call, because the guard could not tell the two zero states apart.

```java
public int hashCode() {
    int h = hash;
    if (h == 0 && !hashIsZero) {
        h = isLatin1() ? StringLatin1.hashCode(value) : StringUTF16.hashCode(value);
        if (h == 0) hashIsZero = true; else hash = h;
    }
    return h;
}
```

The write is a benign race under the Java Memory Model: two threads computing the hash concurrently both derive the identical value from the same immutable `value` array, and the guard writes exactly one of the two fields, never both, so no torn or partial state is ever observable regardless of interleaving. `"".hashCode()` is `0` and sets `hashIsZero` to `true`; `"AA-801".hashCode()` measures `1922319628`, computed by the recurrence `sum of s[i] * 31^(n-1-i)` and delegated in practice to a vectorized intrinsic, `ArraysSupport.vectorizedHashCode` (JDK 21, JDK-8302163). The follow-up worth naming unprompted: `"polygenelubricants".hashCode()` is `Integer.MIN_VALUE`, not zero — a widely repeated folklore example that is simply wrong about which string actually triggers the sentinel.

### "How does `+` string concatenation actually compile on modern Java, and where does that optimization stop applying?"

Since Java 9 (JEP 280), a concatenation expression like `"AA-" + phase + disposition` compiles to a single `invokedynamic` call into `java.lang.invoke.StringConcatFactory.makeConcatWithConstants`, not a chain of `StringBuilder.append` calls the way Java 8 and earlier compiled it. The bootstrap method receives a "recipe" string with a reserved control-character placeholder marking each dynamic argument and any literal text folded directly into the recipe, then links once per call site to a strategy that knows the exact final size and coder up front, so the whole concatenation happens in one allocation with zero intermediate buffers.

```java
String status = "AA-" + phase + disposition; // one expression, one indy call site
```

`javap -v` shows a `BootstrapMethods` entry naming `StringConcatFactory.makeConcatWithConstants` with the recipe and static arguments attached, and the call site itself as an `invokedynamic` whose exact descriptor depends on which arguments are dynamic versus baked into the recipe as constants. This beats the old `StringBuilder` desugaring for a single expression because the result's size and Latin-1/UTF-16 coder are both known before any bytes are copied — no growth-and-copy sequence at all, just one exactly-sized allocation.

The critical distinction interviewers probe next: this applies only within one concatenation *expression*, never across loop iterations — `stake += "…"` inside a loop still compiles to one `invokedynamic` call per iteration, and each call still allocates and copies the whole accumulated string fresh, so the loop form remains O(n²) in every Java version regardless of the underlying single-expression strategy. There's also a documented escape hatch, `-Djava.lang.invoke.stringConcat=BC_SB`, that restores the Java 8 `StringBuilder`-chain strategy at JVM startup, useful only for diagnosing whether a regression is strategy-specific.

### "Trace `Integer.valueOf` end to end — what actually fills the cache array on JDK 21?"

`Integer.valueOf(int)` does exactly four things: check against `IntegerCache.low` (a hardcoded `-128`), check against `IntegerCache.high` (a blank final defaulting to `127`, raisable via `-XX:AutoBoxCacheMax` or the `java.lang.Integer.IntegerCache.high` system property), and if in range, index directly into a private static `Integer[] cache`; otherwise allocate a fresh `new Integer(i)`. What actually fills that `cache` array on a default JDK 21 JVM is not the Java construction loop most people picture — it's a native call, `CDS.initializeFromArchive(IntegerCache.class)`, run unconditionally on every startup path, writing the array's contents directly from the Class-Data Sharing archive rather than executing 256 `new Integer` allocations in a Java loop.

```java
private static class IntegerCache {
    static final int low = -128;
    static final int high;      // set once in <clinit> from the property/flag
    static final Integer[] cache;
    static Integer[] archivedCache; // written natively by CDS, NOT final
}
```

`archivedCache` is deliberately not `final`, because a JVM-side native write to a genuinely `final` field would be a lie to the JIT, which is licensed to treat `final` fields as immutable for constant-folding purposes. The array reference Java code actually reads and holds forever, `cache`, is assigned once at the end of the static block and marked `@Stable`, which extends constant-folding trust down into the array's *elements* — something plain `final` never does. Both configuration paths write to the exact same underlying value, and measurement confirms that when both the flag and the property are set, the `-XX` flag wins.

The number to have ready: the default array holds exactly 256 instances, `(127 - (-128)) + 1`, and the index arithmetic `i + (-IntegerCache.low)` folds at compile time to the literal `i + 128` — deliberately written the indirect way so it stays correct by construction if `low` were ever made configurable, even though today it never is.

### "What does erasure actually erase, and why do bridge methods have to exist?"

Erasure means a parameterized type like `Repository<CashEntry>` and its type variable both collapse to a single class-file descriptor: the raw type for a parameterized type, and the erasure of the leftmost bound (or `Object` if unbounded) for a type variable. That's why `Map<UUID,T>.get` and a raw `Map.get` compile to the byte-identical descriptor `(Ljava/lang/Object;)Ljava/lang/Object;` — the compiler inserts a `checkcast` at whichever call site actually needs the narrower static type back, never inside the generic method itself.

Bridge methods exist specifically to make virtual dispatch work correctly across that erasure boundary. When a subclass overrides a generic method with a more specific parameter or return type than the erased signature promises, the compiler synthesizes an extra method carrying the *erased* signature that simply forwards to the real override — flagged `ACC_BRIDGE` (`0x0040`) and `ACC_SYNTHETIC` (`0x1000`) together.

```java
abstract class AbstractStore<E extends LedgerEntry> {
    abstract void save(E entry);
}
final class CashEntryStore extends AbstractStore<CashEntry> {
    @Override void save(CashEntry entry) { /* real body */ }
    // compiler-synthesized: void save(LedgerEntry entry) {
    //     save((CashEntry) entry);   // bridge — can throw ClassCastException here
    // }
}
```

The reason the JVM can't just "dispatch by name": the vtable slot for `AbstractStore.save` has descriptor `(LLedgerEntry;)V`, and `CashEntryStore`'s real override has descriptor `(LCashEntry;)V` — genuinely different signatures at the class-file level, so without the bridge, a caller invoking through the erased `AbstractStore` reference would find no matching method at all. `Method.isBridge()`, not `isSynthetic()`, is the correct reflective filter, because `isSynthetic()` also matches unrelated compiler-generated members. The follow-up worth pre-empting: a bridge-cast `ClassCastException` frame sits at the *class declaration's* line number inside a synthetic method of the callee's class, while an ordinary heap-pollution cast sits on a real statement line in caller code — that's how you tell the two apart in a stack trace.

### "Explain loading, linking, and initialization, and why `synchronized (SomeClass.class)` isn't a safe substitute for the initialization lock."

A class goes through three phases, strictly in order: loading (bytes become an in-memory representation), linking (verification, preparation, and *optional* resolution — JVMS §5.5 explicitly says resolution may happen eagerly at link time or lazily on first use, and HotSpot chooses lazy), and initialization (running `<clinit>` exactly once). "Linking resolves all references" is folklore, not platform behavior — on HotSpot almost every symbolic reference resolves lazily, on first actual use.

Initialization is protected by a unique per-class initialization lock, `LC`, whose concrete identity JVMS deliberately leaves to the implementation's discretion — the `Class` object's own monitor is one example, not the contract, which is exactly why `synchronized (SomeClass.class)` has no documented interaction with it and can introduce a real, detector-visible deadlock of its own.

```
Step 1: acquire LC
Step 2 (another thread already initializing): release LC, block uninterruptibly, retry
Step 3 (this thread already initializing — recursive): release LC, complete normally
Step 6: record in-progress, release LC, set ConstantValue fields in class-file order
Step 9: execute <clinit>
Step 10: acquire LC, mark fully initialized, notify all waiters, release LC
Step 12 (abrupt failure): acquire LC, mark erroneous, notify all waiters, release LC
```

Step 3's recursion case is the one interviewers probe hardest: a thread re-entering initialization of a class it is already initializing — through a static-field cycle, for instance — does not deadlock against itself; it releases the lock and completes normally immediately, observing whatever the fields held at that moment, which is preparation-time defaults if `<clinit>` hasn't reached that field's assignment yet. Two *different* threads on a genuine initialization cycle, however, can hang forever, because each blocks waiting for the other's `LC` with no timeout and no deadlock detector watching class-initialization locks specifically — `Thread.State` reports `RUNNABLE`, not `BLOCKED`, because the block happens inside native JVM machinery outside ordinary monitor semantics. Once a class is marked erroneous after a failed `<clinit>`, every later touch throws `NoClassDefFoundError` permanently — there is no retry.

### "Name the five invoke instructions, what each one decides, and how inline caches build on top of that."

There are exactly five method-invocation instructions, each answering a different question about how the call is bound. `invokestatic` calls a static method with no receiver, resolved once per constant-pool entry with no further selection step. `invokespecial`, on Java 11 and 21, means only a constructor call or an explicit `super.method()` call — deliberately non-virtual, bypassing any override. `invokevirtual` calls an instance method through a class-typed receiver expression, and since Java 11 (JEP 181, nestmates) also covers private instance methods, which compiled to `invokespecial` on Java 8. `invokeinterface` calls an instance method through an interface-typed receiver expression. `invokedynamic` covers lambdas, method references, string concatenation, and record `equals`/`hashCode`/`toString` — its bootstrap runs once per call site and yields a `CallSite` that subsequent calls reuse directly.

```java
class WithdrawalTransaction {
    String label() { return "card withdrawal"; }   // invokevirtual at the call site
    static String rail() { return "generic"; }      // invokestatic at the call site
}
```

`javap -c` on a caller shows `invokevirtual #37 // WithdrawalTransaction.label` and, right next to it, `invokestatic #33 // WithdrawalTransaction.rail` — the same object, two different instructions, chosen purely by the receiver expression's static type and the method's own modifiers, never by anything discovered at run time. This is resolution (JVMS §5.4.3.3, a symbolic reference to a declared member, computed once per constant-pool entry from static types) versus selection (JVMS §5.4.6, resolved method plus the actual receiver's runtime class to the body that actually runs, computed per invocation, and only for `invokevirtual`/`invokeinterface`).

Inline caches are HotSpot's optimization on top of selection, not part of the specification: a monomorphic call site (one profiled receiver class ever observed) collapses to a single class check plus an inlined body; a bimorphic site (two receivers) keeps two checks, both still inlinable; beyond that it's megamorphic — real virtual-table dispatch, no inlining, and any optimization built on the assumption of inlining is lost. Marking a method `final` or `private` doesn't itself make dispatch faster on modern JITs — class hierarchy analysis and the receiver-type profile already devirtualize the monomorphic case; the keyword just removes the *possibility* of a wider receiver set, it doesn't further speed up a call site that was already monomorphic.

### "What's actually in an object's header, and how does the JVM decide where each field lands?"

Every Java object carries a header before any of its declared fields: an 8-byte mark word plus, under the default compressed-oops configuration, a 4-byte compressed class pointer, for 12 bytes total (16 bytes without compressed class pointers). The mark word's bit layout on JDK 21 is `unused:25 hash:31 unused_gap:1 age:4 unused_gap:1 lock:2`, summing to the full 64 bits — the 31-bit slot is exactly why `System.identityHashCode` can never return a negative value, and the 4-bit GC-age field is exactly why `MaxTenuringThreshold` can never exceed 15.

One correction that bites specifically on Java 21: biased locking, which used to occupy part of that mark word, was disabled by default starting in Java 15 (JEP 374) and its code was removed entirely in Java 18 — describing the mark word as if it still holds a bias bit on 21 is stale. The unused gap next to the age bits is literally biased locking's old slot, left unused rather than reclaimed.

```java
class LedgerEntry {
    long postedAtEpochSecond;   // 8-byte field
    int amountMinor;            // 4-byte field
    byte coder;                 // 1-byte field
}
```

Field layout inside the object is not source-declaration order — HotSpot's field-layout builder (rewritten in JDK 15, JDK-8237767) reorders declared fields to minimize padding: it fills any small gap left right after the 12-byte header first with a same-or-smaller field if one exists, then places 8-byte fields, then 4-byte, then 2-byte, then 1-byte, and puts every reference field last. There is no field-layout guarantee at any Java version — the old `-XX:FieldsAllocationStyle` flag that once let you influence it was removed alongside the JDK 15 rewrite. A lone `int` field measures at offset 12 (right after the header, no gap needed), while a lone `long` field measures at offset 16, because an 8-byte field needs an 8-byte-aligned start and offset 12 isn't one — HotSpot inserts 4 bytes of padding rather than leaving the `long` misaligned. Every object's final size then rounds up to a multiple of 8 via `ObjectAlignmentInBytes`.

The follow-up worth pre-empting: does `UseCompactObjectHeaders` change any of this on 21? No — that flag doesn't exist on JDK 21 at all; it's an experimental JDK 24 feature (JEP 450) that became a product feature only in JDK 25 (JEP 519).

### "Explain how a `try`/`catch` actually works at the bytecode level, and what `fillInStackTrace` really costs."

Every `try` block compiles to zero bytecode instructions of its own — the guarded region is just a range of ordinary instructions — plus one or more rows in the method's `Code` attribute exception table, each row a fixed `(start_pc, end_pc, handler_pc, catch_type)` quadruplet. When an `athrow` executes (or an implicit runtime exception like a null dereference fires), the JVM scans that method's exception table in source order for the first row whose range covers the current program counter and whose `catch_type` is assignable from the thrown exception's actual class; `catch_type == 0` matches every `Throwable` and is how `finally` blocks and synchronized-monitor unlocking are implemented under the hood. If no row matches, the frame is popped, any held monitor is released, and the same search repeats in the caller at its own call program counter.

`fillInStackTrace()` is the part of the cost story that actually dominates: it's `synchronized`, delegates to a native method, and is called from *every* `Throwable` constructor by default, walking the entire live call stack up to `MaxJavaStackTraceDepth` (1024 frames by default) into an opaque native `backtrace` field. The public-facing `StackTraceElement[]` is only materialized lazily, on the first call to `getStackTrace()`.

```java
static final class FastReject extends RuntimeException {
    FastReject() { super(null, null, false, false); } // writableStackTrace = false
    @Override public synchronized Throwable fillInStackTrace() { return this; }
}
```

The four-argument `Throwable` constructor's last parameter, when `false`, sets `stackTrace` directly to `null` and skips `fillInStackTrace()` at construction entirely — overriding `fillInStackTrace()` to `return this` achieves the same observable effect through a different mechanism, useful when the exception type isn't yours to construct with the four-argument super call. Measured cost: constructing a normal exception at a realistic depth of five frames costs roughly 278 nanoseconds, almost entirely inside the stack walk, while throwing and catching that already-constructed exception adds only about six more nanoseconds — the capture, not the throw-catch machinery, is where the cost lives. The ratio between a stackless and a normal exception is depth-dependent, never a flat number: roughly 49 times cheaper at depth 1, collapsing toward roughly 1.4–1.5 times cheaper by depth 100, because the shared recursion-and-unwind cost, paid by both forms equally, comes to dominate as depth grows — always cite a depth alongside any ratio (`build-it/03h-stackless-exception.md` measures 11.15× at depth 1 and 1.47× at depth 100).

### "What are `$VALUES` and `$SwitchMap`, and why is adding a new enum constant binary-compatible for callers who haven't recompiled?"

`$VALUES` is a compiler-synthesized private static final array field — flags `ACC_PRIVATE, STATIC, FINAL, SYNTHETIC` — holding every declared enum constant in declaration order, assigned in `<clinit>` right after the last constant is constructed. `values()` itself, despite being generated, is *not* synthetic (`ACC_PUBLIC, STATIC` only) because the JLS implicitly declares it as real, callable-by-name API; its body is four instructions: `getstatic $VALUES`, `invokevirtual clone()`, `checkcast`, `areturn`. Every call to `values()` allocates a fresh clone of that array — `values() == values()` is always `false` — so a hot path should cache the result once in a `static final` field, or better, use `EnumSet`/`EnumMap`, which read the shared internal `getEnumConstantsShared()` array directly with no cloning.

```java
enum RestrictionType { DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED }
```

Compiled: 11 fields for three constants (three constant fields plus `$VALUES`), and five methods for a source file declaring none (`values`, `valueOf`, `<init>`, the private `$values()` helper — present from Java 17 onward, absent on 8 and 11 — and `<clinit>`).

`$SwitchMap` is a completely separate mechanism a `switch` statement over an enum compiles to: a synthetic `int[]` holder, named `$SwitchMap$<EnclosingClass>$<EnumType>`, living in the *switching* class's own generated nested holder class, indexed by `ordinal()` and populated lazily on first use to map each ordinal to the dense `case`-label index the `tableswitch` bytecode actually needs. This indirection is exactly why adding a new enum constant is binary-compatible for existing compiled callers: the `$SwitchMap` array is sized from `values().length` at the switching class's own next initialization, so a caller recompiled against the new constant gets a correctly sized map, while an unrecompiled caller's stale map simply routes the new ordinal to slot zero, the default, with no error — assuming the switch has a `default` clause at all. On Java 21, an exhaustive `switch` expression compiled against an older enum shape that later encounters a genuinely new, unhandled constant throws `MatchException` with a `null` message — the bytecode builds that exception from two `aconst_null` pushes, because the branch had been proved statically unreachable at compile time.

## Predict the output

```java
public class BonusCacheCheck {
    public static void main(String[] args) {
        Integer a = 127, b = 127;
        Integer c = 128, d = 128;
        System.out.println(a == b);
        System.out.println(c == d);
        Integer e = Integer.valueOf(128);
        Integer f = Integer.valueOf(128);
        System.out.println(e == f);
    }
}
```

**Output**
```
true
false
false
```

**Why** Every one of these assignments and calls autoboxes through `Integer.valueOf(int)`, never `new Integer(int)` — autoboxing always uses `valueOf`. `IntegerCache` holds one shared instance for every value from `-128` to `127`, indexed by `i + (-IntegerCache.low)`, so both `a` and `b` land on `cache[255]` and `==` compares the same reference. `128` falls one past `IntegerCache.high` (`127` by default), so `valueOf(128)` allocates a fresh `Integer` on every call — `c` and `d` are two distinct objects, and so are `e` and `f`, even though `e` and `f` were boxed by the identical `valueOf(128)` call written twice. The cache boundary is a property of the *value*, not of how many times a particular call site executes.

```java
public class ZeroHashProbe {
    public static void main(String[] args) {
        String zero = "";
        System.out.println(zero.hashCode());
        String pg = "polygenelubricants";
        System.out.println(pg.hashCode());
    }
}
```

**Output**
```
0
-2147483648
```

**Why** The empty string's hash is genuinely `0` by the recurrence `sum of s[i] * 31^(n-1-i)` over zero characters, and computing it sets `hashIsZero = true` so the next call skips recomputation via the `h == 0 && !hashIsZero` guard. `"polygenelubricants"` is the widely misquoted example of a *non-empty* string whose hash happens to land on a boundary value — its actual measured `hashCode()` is `-2147483648`, exactly `Integer.MIN_VALUE`, not `0` as folklore often claims; the two examples get conflated because both are commonly cited near `hashIsZero`, but only the empty string actually triggers that flag.

```java
public enum RestrictionType { DEPOSIT_BLOCKED, STAKE_BLOCKED, WITHDRAWAL_BLOCKED }

public class ValuesCloneProbe {
    public static void main(String[] args) {
        System.out.println(RestrictionType.values() == RestrictionType.values());
        System.out.println(RestrictionType.values()[0] == RestrictionType.DEPOSIT_BLOCKED);
    }
}
```

**Output**
```
false
true
```

**Why** `values()` compiles to `getstatic $VALUES; invokevirtual clone(); checkcast; areturn` — every call clones the shared `$VALUES` array into a brand-new array instance, so two separate calls never return the same array reference and `==` between them is always `false`. The *elements* inside each cloned array are the same canonical enum constant objects every time, because `clone()` on a reference-type array copies references, not the objects they point to — so indexing into either clone and comparing against `RestrictionType.DEPOSIT_BLOCKED` by identity is `true`. The array identity and the element identity are two entirely different questions.

```java
public class ConstantTriggerProbe {
    static final class BonusRules {
        static { System.out.println("BonusRules initialising"); }
        static final int MAX_BONUS = 100;
        static final int GRANT_RATE = computeRate();
        static int computeRate() { return 14; }
    }

    public static void main(String[] args) {
        System.out.println("before");
        int cap = BonusRules.MAX_BONUS;
        System.out.println("read MAX_BONUS = " + cap);
        int rate = BonusRules.GRANT_RATE;
        System.out.println("read GRANT_RATE = " + rate);
    }
}
```

**Output**
```
before
read MAX_BONUS = 100
BonusRules initialising
read GRANT_RATE = 14
```

**Why** `MAX_BONUS` is a constant variable — `final`, primitive, initialized with a compile-time constant expression — so JLS §13.1 forbids any reference to it from appearing in a compiled binary at all; `javac` inlines the read as a literal `bipush 100` at the call site with no `getstatic` and no reference to `BonusRules`, so this line never touches the class and never triggers its initialization. `GRANT_RATE` is `final` but not a constant variable, because its initializer is a method call rather than a constant expression, so reading it emits a genuine `getstatic`, which is one of the six triggers in JVMS §5.5 and initializes `BonusRules` on the spot — running the static block, then the two field initializers in `<clinit>`, before the read returns `14`.

```java
public class FastRejectProbe {
    static final class FastReject extends RuntimeException {
        FastReject() { super(null, null, false, false); }
        @Override public synchronized Throwable fillInStackTrace() { return this; }
    }
    static final FastReject REJECT = new FastReject();

    public static void main(String[] args) {
        try {
            throw REJECT;
        } catch (FastReject e) {
            System.out.println(e.getStackTrace().length);
            System.out.println(e.getMessage());
        }
        RuntimeException normal = new RuntimeException("stake reservation failed");
        System.out.println(normal.getStackTrace().length > 0);
    }
}
```

**Output**
```
0
null
true
```

**Why** The four-argument `Throwable` constructor with `writableStackTrace = false` sets the `stackTrace` field directly to `null` at construction and skips `fillInStackTrace()` entirely; the overridden `fillInStackTrace()` returning `this` is redundant belt-and-braces here, since either mechanism alone already suffices. `getStackTrace()` sees `stackTrace == null` and `backtrace == null` inside `getOurStackTrace()` and returns the shared empty `UNASSIGNED_STACK` array rather than attempting any decode, so the length is `0`. `getMessage()` is `null` because the message parameter passed to the four-argument constructor was `null`, and nothing since construction has set it. `normal`, built through the ordinary single-argument constructor, runs the full native `fillInStackTrace()` walk unconditionally, so its captured trace has real frames and the length check is `true`.

---

**Leaves covered:** none — Part 3 wrap-up over §3.1–§3.18, whose leaves are owned by the files linked in the summary table
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 344
