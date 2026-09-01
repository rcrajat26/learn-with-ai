# 03 Java Core — The eighty questions, 17–32 — INTERVIEW (§5.1, 5.1.17–5.1.32)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [The eighty questions, 1–16](94-interview-questions-and-drills.md) · Next: [The eighty questions, 33–48](94b-interview-questions-33-48.md)

## The questions, continued

Sixteen more of the eighty — how to use this file, and the shared house rules, are in [`94-interview-questions-and-drills.md`](94-interview-questions-and-drills.md).

### Q17. "Why is `finalize` deprecated and what replaces it?"

**The 30-second answer.** `finalize` has three independent structural defects: it runs on the object being finalized, so it is trivial to smuggle `this` back into a live root and resurrect the object; a finalizable object cannot be reclaimed on the GC pass that first finds it unreachable, so it costs a guaranteed extra collection cycle; and it gives no guarantee about when — or even whether before process exit — it runs at all. `Object.finalize()` was marked `@Deprecated(since = "9", forRemoval = true)` when `java.lang.ref.Cleaner` shipped as the structural fix, and JEP 421 (Java 18) formalized the intent to remove finalization entirely, adding `--finalization=disabled` as an opt-out flag. The replacement is chosen by resource kind: native memory uses `Cleaner` or the `Arena` API; files and sockets use try-with-resources over `AutoCloseable`; anything else with a lifecycle gets an explicit open/close pair on the type itself.

**The 5-minute answer.** Trace the extra-cycle cost as a state machine rather than asserting it. An object of a class overriding `finalize` with a non-trivial body is registered at allocation time with the JVM's finalization machinery. State progression: (1) allocated, registered; (2) first found unreachable — an ordinary object would be reclaimed here, but a finalizable one is instead marked finalizable and queued; (3) a finalizer thread runs `finalize()`, with `this` passed as an ordinary, fully strongly-reachable argument — nothing restricts what the body does with it, and if it stores `this` into a `static` field or any other GC root, the object is resurrected; (4) the collector must re-run reachability determination, because step 3 could have resurrected it — that second pass is unavoidable and structural, independent of whether any given object actually resurrects. JLS §12.6 and the javadoc guarantee `finalize` runs **at most once** per object, so an object that resurrects once and then goes unreachable a second time gets no cleanup hook at all on its second death — "use `finalize` as a backstop that always eventually cleans up" is false the moment resurrection has happened once. `Cleaner` fixes the capture defect by construction: `Cleaner.register(Object obj, Runnable action)` wraps `obj` in a phantom reference the `Cleaner`'s own background thread polls, and the cleaning action must not — cannot, if written correctly — hold a reference back to `obj`, because the phantom reference itself is the only path keeping the registration alive once `obj` is otherwise unreachable. On JDK 21, `--finalization=disabled` is accepted and starts the VM normally, but removal has not shipped — `finalize()` still runs by default.

```java
final class LedgerFileHandle implements AutoCloseable {
    private static final java.lang.ref.Cleaner CLEANER = java.lang.ref.Cleaner.create();

    private final java.lang.ref.Cleaner.Cleanable cleanable;
    private final State state;

    // The action must not capture `this` — only fields the compiler can reach
    // through a captured reference to `this` would keep the handle alive forever.
    private static final class State implements Runnable {
        private final java.nio.channels.FileChannel channel;

        State(java.nio.channels.FileChannel channel) {
            this.channel = channel;
        }

        @Override
        public void run() {
            try {
                channel.close();
            } catch (java.io.IOException ignored) {
                // The Cleaner thread has nowhere useful to report this; log at the call site instead.
            }
        }
    }

    LedgerFileHandle(java.nio.channels.FileChannel channel) {
        this.state = new State(channel);
        this.cleanable = CLEANER.register(this, state);
    }

    @Override
    public void close() {
        cleanable.clean(); // idempotent: Cleaner.Cleanable.clean() runs the action at most once
    }
}
```

**The follow-up they will ask** — "why can't the `Cleaner` action reference the object it's cleaning up?" Because the `Cleaner` holds the action strongly for the entire registration lifetime; if the action also held `obj` strongly, the phantom reference the `Cleaner` uses to detect unreachability would never fire, since `obj` would never actually become unreachable.

**Where this is written** — [`objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md`](objects-equality-and-lifecycle/03a-finalization-cleanup-and-leaks.md), [`objects-equality-and-lifecycle/01c-object-methods.md`](objects-equality-and-lifecycle/01c-object-methods.md).

### Q18. "Walk me through the exact initialization order of a `new` on a subclass."

**The 30-second answer.** For `new Reservation(entryId)` where `Reservation extends LedgerRecord`: allocation zeros every field on every class in the hierarchy in one shot; then constructors are invoked bottom-up (`Reservation`'s constructor immediately delegates to `LedgerRecord`'s, which delegates to `Object`'s) but constructor **bodies** execute top-down as the recursion unwinds — `Object`'s body (empty) runs first, then `LedgerRecord`'s field initializers and instance-init blocks (merged, textual order) followed by its constructor body, and only then `Reservation`'s own field initializers/instance blocks followed by its constructor body.

**The 5-minute answer.** JLS §12.5 gives five steps; the ordering comes from steps 3–5. Step 3: if the constructor is for a class other than `Object`, it begins with an explicit or implicit `super(...)` call — recurse into the superclass constructor using these same five steps before doing anything else. Step 4: execute this class's instance initializers and instance variable initializers, interleaved, in left-to-right textual order — this is one merged sequence, not "fields first, then blocks." Step 5: execute the rest of the constructor body. Because step 3 recurses to completion before step 4 of the *same* level runs, the recursion for `new Reservation(entryId)` bottoms out at `Object` (steps 4–5 both empty), unwinds through `LedgerRecord` (its initializers, then its body), and only then reaches `Reservation` (its initializers, then its body). The general rule: constructor **invocations** go bottom-up, constructor **bodies** run top-down, and within one level initializers always precede that level's body — so a constructor-body assignment always overwrites whatever a field initializer set. A field initializer cannot see a constructor parameter: `javac` rejects any reference to a constructor parameter from a field initializer, because the initializer expression is not in the constructor's scope even though it executes inside the constructor's frame.

```java
class LedgerRecord {
    private final java.util.UUID entryId;

    LedgerRecord(java.util.UUID entryId) {
        System.out.println("2. LedgerRecord constructor body");
        this.entryId = entryId;
    }
}

final class Reservation extends LedgerRecord {
    private static final Money CANONICAL_STAKE = Money.gbp("3.33");

    private final StakeSplit split = splitOf(CANONICAL_STAKE);

    {
        System.out.println("4. Reservation instance initializer block, split already = " + split);
    }

    Reservation(java.util.UUID entryId) {
        super(entryId);
        System.out.println("5. Reservation constructor body");
    }

    private static StakeSplit splitOf(Money stake) {
        System.out.println("3. Reservation field initializer for split");
        Money bonusPortion = new Money(
                stake.amount().multiply(new java.math.BigDecimal("0.10"))
                        .setScale(2, java.math.RoundingMode.DOWN),
                stake.currency());
        return new StakeSplit(bonusPortion, stake.minus(bonusPortion));
    }
}
```

The measured output for `new Reservation(id)` is `1. allocation` → `2. LedgerRecord constructor body` → `3. Reservation field initializer for split` → `4. Reservation instance initializer block, split already = StakeSplit[bonusPortion=0.33 GBP, cashPortion=3.00 GBP]` → `5. Reservation constructor body` — line 3 precedes line 4 purely because `split`'s declaration sits textually above the block; swap the two and the printed order swaps too, because step 4 is one merged left-to-right walk.

**The follow-up they will ask** — "what happens if the superclass constructor calls an overridable method?" It dispatches to the subclass override on an object whose subclass fields are still zeroed, because `invokevirtual` resolves against the runtime class fixed at allocation — that is Q19.

**Where this is written** — [`classes-and-initialization/01b-initialization-order.md`](classes-and-initialization/01b-initialization-order.md), [`classes-and-initialization/01c-class-anatomy-and-constructors.md`](classes-and-initialization/01c-class-anatomy-and-constructors.md).

### Q19. "What is wrong with calling an overridable method from a constructor?"

**The 30-second answer.** The object's runtime class is fixed at allocation — before a single line of user code runs — but its subclass fields are still zeroed until that subclass's own step 4 runs, which happens strictly after any superclass constructor body has finished executing. A superclass constructor that calls an overridable method dispatches, via `invokevirtual`, to the subclass override — because Java fixes one runtime class for the object's whole life and never changes dispatch rules during construction, unlike C++ — so the override runs against subclass fields that provably have not been initialized yet, typically producing a `NullPointerException` or silently wrong behavior with a default value.

**The 5-minute answer.** JLS §12.5, stated explicitly right after the five steps: "Unlike C++, the Java programming language does not specify altered rules for method dispatch during the creation of a new class instance. If methods are invoked that are overridden in subclasses in the object being initialized, then these overriding methods are used, even before the new object is completely initialized." C++ changes an object's dynamic type as each base-class constructor runs, so a base-class virtual call there dispatches to the base implementation; Java refuses that — one object, one runtime class, fixed forever — which buys uniform `getClass()`/`instanceof` semantics everywhere else and pays for it exactly here. Mechanically: `javac` compiles the call inside the superclass constructor to `invokevirtual` against the superclass's own method reference, but `invokevirtual` only uses that reference to select a vtable slot — the actual target resolves against the runtime class of the receiver on the stack, which is already the subclass. Prove the field is provably `null`, not just "usually" `null`, by ordering: the override reads a subclass instance field initialized in the subclass's step 4; the call happens in the superclass's step 5; the superclass's step 5 runs from inside the subclass's step 3, and step 3 completes before step 4 begins — so the subclass's step 4 has provably not run when the override executes, guaranteed on every JVM, every run, not a race.

```java
class WithdrawalTransaction {
    protected final Money amount;

    WithdrawalTransaction(Money amount) {
        this.amount = amount;
        validate(); // calls the overridden method before BankWithdrawalTransaction's fields exist
    }

    void validate() {
        if (amount.compareTo(Money.gbp("0.00")) <= 0) {
            throw new IllegalArgumentException("withdrawal amount must be positive");
        }
    }
}

final class BankWithdrawalTransaction extends WithdrawalTransaction {
    private static final LimitSet BANK_LIMITS =
            new LimitSet(Money.gbp("500.00"), Money.gbp("50.00"), Money.gbp("1000.00"));

    private final Money dailyCap = BANK_LIMITS.dailyDeposit(); // not yet assigned during super's validate()

    BankWithdrawalTransaction(Money amount) {
        super(amount);
    }

    @Override
    void validate() {
        // dailyCap is still null here: BankWithdrawalTransaction's step 4 has not run yet.
        if (dailyCap.compareTo(amount) < 0) {
            throw new IllegalStateException("exceeds bank daily cap");
        }
    }
}
```

`new BankWithdrawalTransaction(Money.gbp("260.00"))` throws `NullPointerException` inside `validate()`, on `dailyCap.compareTo(amount)`, deterministically, every run.

**The follow-up they will ask** — "how do you avoid this?" Never call an overridable (non-private, non-final, non-static) method from a constructor; if subclass-specific setup must run during construction, use a static factory method that constructs, then calls a `postConstruct`-style hook explicitly after the object is fully built, or make the called method `final`/`private`.

**Where this is written** — [`inheritance-and-dispatch/01-basics.md`](inheritance-and-dispatch/01-basics.md), [`classes-and-initialization/01b-initialization-order.md`](classes-and-initialization/01b-initialization-order.md), [`build-it/05a-construction-and-init-harnesses.md`](build-it/05a-construction-and-init-harnesses.md).

### Q20. "When is a class initialized? Does reading a constant initialize it?"

**The 30-second answer.** JVMS §5.5 gives a closed list of six triggers, and a compile-time constant read is deliberately not one of them. The dominant one in practice: `new`, `getstatic`/`putstatic`, or `invokestatic` referencing the class, plus reflective lookups, subclass initialization, and being the JVM's launch class. Reading a `static final int MAX_BONUS = 100` — a genuine JLS §4.12.4 constant variable — never triggers initialization, because §13.1 *requires* `javac` to inline the value and leave no reference to the field in the compiled binary at all; there is no `getstatic` instruction left to execute.

**The 5-minute answer.** JVMS §5.5's six bullets: execution of `new`/`getstatic`/`putstatic`/`invokestatic` referencing the class; first invocation of certain `MethodHandle` kinds (`REF_getStatic`, `REF_putStatic`, `REF_invokeStatic`, `REF_newInvokeSpecial`); certain reflective calls (`Class.forName` etc.); initializing a subclass initializes its superclass (one-directional — never the reverse); initializing a class implementing an interface initializes that interface **only if it declares a non-abstract, non-static (default) method**; and designation as the JVM's launch class. The trigger is *execution*, not presence — a `getstatic` in an untaken branch triggers nothing. Proof that a constant read emits no instruction at all: `javap -c` on a method returning `BonusRules.MAX_BONUS` (a `static final int` set to the literal `100`) shows only `bipush 100; ireturn` — no `getstatic`, no symbolic reference to `BonusRules` anywhere in the constant pool. A method returning the non-constant `BonusRules.grantsIssued` shows the real `getstatic BonusRules.grantsIssued:I`. `GRANT_CAP`, declared `static final BigDecimal GRANT_CAP = new BigDecimal("100.00")`, is **not** a constant variable — `BigDecimal` is neither primitive nor `String`, and `new` is not a constant expression — so reading it does emit `getstatic` and does trigger `<clinit>`. `**Insight:**` the closed list is closed over *bytecode*, not source: a lambda, a record's generated `hashCode`, or a sealed `switch` compiles to `invokedynamic`, whose bootstrap-method resolution can initialize a class your source never mentions with `new`/`getstatic`/`invokestatic`. `**Pitfall:**` `int unused = BonusRules.MAX_BONUS;` written to "warm up" the class does nothing — it compiles to `bipush` and is dead-code-eliminated, leaving the class uninitialized; the correct warm-up is `MethodHandles.lookup().ensureInitialized(BonusRules.class)` or `Class.forName("BonusRules")`.

```java
public final class BonusRules {
    public static final int MAX_BONUS = 100;                              // constant variable: no trigger on read
    public static final java.math.BigDecimal GRANT_CAP =
            new java.math.BigDecimal("100.00");                           // NOT a constant variable: triggers <clinit>
    public static int grantsIssued = 0;

    static {
        System.out.println("BonusRules <clinit> ran");
    }

    public static int grantFor(long depositMinorUnits) {
        grantsIssued++;
        return (int) Math.min(MAX_BONUS, depositMinorUnits / 10);
    }
}

final class ConstantReadProbe {
    static int readConstant() {
        return BonusRules.MAX_BONUS; // compiles to bipush 100 — no reference to BonusRules survives
    }
}
```

**The follow-up they will ask** — "what if the static initializer itself throws?" The class is permanently marked erroneous and the first caller sees the real exception wrapped; every caller after that gets `NoClassDefFoundError` — Q21.

**Where this is written** — [`classes-and-initialization/01d-class-initialization-triggers.md`](classes-and-initialization/01d-class-initialization-triggers.md), [`classes-and-initialization/03-internals-class-loading-and-init.md`](classes-and-initialization/03-internals-class-loading-and-init.md), [`classes-and-initialization/04-internals-final-and-constant-folding.md`](classes-and-initialization/04-internals-final-and-constant-folding.md).

### Q21. "What is `ExceptionInInitializerError` and why does the next call throw `NoClassDefFoundError`?"

**The 30-second answer.** A class gets exactly one chance to initialize. If its `<clinit>` throws anything that is not itself an `Error`, the JVM wraps it in `ExceptionInInitializerError` and marks the `Class` object permanently **erroneous** — there is no retry, because `<clinit>` may have already run half its side effects and re-running it is not idempotent. The first caller gets the diagnosable wrapped exception with the real cause; every subsequent caller gets `NoClassDefFoundError: Could not initialize class X`, because JVMS §5.5 says any touch of an erroneous class throws that, unconditionally, regardless of what actually failed.

**The 5-minute answer.** JVMS §5.5's abrupt-completion step: "If the class of E is not `Error` or one of its subclasses, then create a new instance of `ExceptionInInitializerError` with E as the argument... Acquire LC, label the `Class` object for C as erroneous, notify all waiting threads, release LC, and complete this procedure abruptly." Two things to extract: the wrap is **conditional** on E not being an `Error` — a `StackOverflowError` or `OutOfMemoryError` thrown from a static initializer propagates completely unchanged, with no `ExceptionInInitializerError` anywhere, which breaks a `catch (ExceptionInInitializerError e)` handler built assuming it catches everything; and the erroneous label is permanent — nothing in the spec ever un-labels it. Every later touch hits "If the `Class` object for C is in an erroneous state, then initialization is not possible. Release LC and throw a `NoClassDefFoundError`." **Version fact:** on JDK 18+ (backported to 17.0.7, 11.0.19-oracle, 8u341), fixed under JDK-8048190, the second and later `NoClassDefFoundError`s carry a reconstructed `Caused by: ExceptionInInitializerError` with the original stack trace and `[in thread "..."]` naming the first thread that lost the initialization race — HotSpot records this in a per-class side table (`InstanceKlass::add_initialization_error`). Before that fix, later callers saw a bare `NoClassDefFoundError: Could not initialize class X` with no `Caused by:` at all — that is still what an older JDK 11 community build or JDK 8 produces, and it's the classic "root cause is gone" shape most interviewers describe from memory. Diagnosis rule either way: search for the **earliest** `ExceptionInInitializerError` in the whole log, not the most recent `NoClassDefFoundError`.

```java
public final class BonusRules {
    public static final int COUPON_VALIDITY_DAYS;

    static {
        String configured = System.getProperty("quizstakes.bonus.couponValidityDays");
        COUPON_VALIDITY_DAYS = Integer.parseInt(configured); // throws NumberFormatException if misconfigured
    }

    private BonusRules() {
    }
}

final class BonusService {
    int grant() {
        return BonusRules.COUPON_VALIDITY_DAYS; // first call: ExceptionInInitializerError, cause NumberFormatException
                                                  // every later call: NoClassDefFoundError: Could not initialize class BonusRules
    }
}
```

**The follow-up they will ask** — "does catching `NoClassDefFoundError` fix the call site?" No — it hides a permanently broken class; the fix is to fix the misconfiguration and restart the JVM, since nothing un-erroneouses a `Class` object at runtime.

**Where this is written** — [`classes-and-initialization/03a-internals-class-init-locking-and-failure.md`](classes-and-initialization/03a-internals-class-init-locking-and-failure.md), [`classes-and-initialization/01d-class-initialization-triggers.md`](classes-and-initialization/01d-class-initialization-triggers.md).

### Q22. "`ClassNotFoundException` vs `NoClassDefFoundError`."

**The 30-second answer.** They sit in different hierarchies and answer different questions: `ClassNotFoundException extends ReflectiveOperationException extends Exception` — checked, thrown by an explicit lookup you wrote (`Class.forName`, `ClassLoader.loadClass`) when no class with that name is visible to the loader you asked. `NoClassDefFoundError extends LinkageError extends Error` — unchecked, thrown by the JVM itself when resolving a symbolic reference the compiler already validated but the runtime classpath doesn't satisfy. JVMS §5.3.1 states the relationship directly: a loader lookup failure produces `ClassNotFoundException`; if the JVM was performing that lookup on behalf of linkage, it wraps the result into `NoClassDefFoundError` whose cause is that `ClassNotFoundException`.

**The 5-minute answer.** There are genuinely **three** situations, and conflating them is the trap. (1) `ClassNotFoundException` — an explicit reflective lookup found nothing; checked, catchable, and a legitimate response is to handle it. (2) `NoClassDefFoundError` from **linkage** — the JVM resolving a constant-pool reference from a class that compiled fine but whose dependency is missing at runtime (a missing/shaded/version-skewed jar, `provided` scope, a module not on the path); its cause, per §5.3.1, is a `ClassNotFoundException` thrown from inside the loader — visible in the trace's `Caused by:` line, whose frames belong to the loader, not your code. (3) `NoClassDefFoundError` from a **failed initialization** — the class is physically present and linked, but its `<clinit>` already threw once (Q21); every later touch gets this, and its cause on JDK 18+ is a reconstructed `ExceptionInInitializerError`, not a `ClassNotFoundException`. The field diagnostic: a linkage `NoClassDefFoundError` whose cause is `ClassNotFoundException` in `BuiltinClassLoader.loadClass` is a deployment problem; one whose cause is anything else is a failed-initialization problem. `**Pitfall:**` "I `catch (ClassNotFoundException e)` around this, so a missing class is handled" — false the moment the missing class is reached through a normal `new`/field/method reference rather than a reflective lookup: `NoClassDefFoundError` propagates straight past that `catch`, because it is an `Error`, not the checked exception the `catch` names, and `javac` will not even let you write `catch (ClassNotFoundException e)` around code with no reflective call in it (it does not compile — nothing there throws it).

```java
final class RuleSetLoader {
    Class<?> loadOptionalRuleSet(String binaryName) {
        try {
            return Class.forName(binaryName); // an explicit lookup: ClassNotFoundException is the honest failure here
        } catch (ClassNotFoundException e) {
            return null; // legitimate: this call site genuinely decided to treat absence as optional
        }
    }

    void loadRequiredRuleSet() {
        BonusRules rules = new BonusRules(); // compiled-in dependency: absence surfaces as NoClassDefFoundError,
                                              // an Error, uncatchable by any surrounding catch (ClassNotFoundException e)
    }
}
```

**The follow-up they will ask** — "does `ClassLoader.loadClass` initialize the class?" No — only `Class.forName(String)` (and `forName` with `initialize=true`) initializes; `loadClass` resolves `resolve=false`, so the returned `Class` object's static fields are still at their default values and `<clinit>` has never run, which is the classic surprise when it's substituted for `forName`.

**Where this is written** — [`classes-and-initialization/03b-internals-class-loaders-and-identity.md`](classes-and-initialization/03b-internals-class-loaders-and-identity.md), [`classes-and-initialization/03-internals-class-loading-and-init.md`](classes-and-initialization/03-internals-class-loading-and-init.md).

### Q23. "Checked vs unchecked exceptions — which would you use and why?"

**The 30-second answer.** Bloch's rule, applied honestly: use a checked exception for a condition the **immediate** caller can reasonably be expected to recover from with a specific action; use unchecked for everything else, including violated preconditions, which are always the caller's bug. In QuizStakes, `InsufficientFundsException`, `RestrictedActionException`, `IllegalTransitionException`, `LedgerImbalanceException` and `BonusIneligibleException` are all unchecked, because at every call site between detection and the HTTP boundary, the only correct behavior is propagation — no intermediate frame has a specific response available, so a `throws` clause climbing through all of them would be pure ceremony. A PSP timeout on card capture is the case that genuinely earns checked: a caller of that path that ignores the timeout possibility is shipping a bug, since the 30-second watchlist timeout against a documented p99 of 38s means it *will* happen in production.

**The 5-minute answer.** Java is the only mainstream language that shipped compiler-checked exceptions as a first-class mechanism — C# considered and rejected it, Kotlin has none at the language level despite running on the same JVM and interoperating with Java's own checked exceptions. Telling evidence from inside the JDK itself: `java.util.stream`'s functional interfaces (`Function.apply`, `Consumer.accept`, `Predicate.test`) declare no `throws` clause at all; `java.time` throws only the unchecked `DateTimeException`; `Optional` carries no exception, treating absence as a value. Three concrete design failure modes drive the modern lean toward unchecked: **signature pollution** — a checked exception in a method signature is a binary/source compatibility commitment propagated to every caller regardless of whether they care, so `SQLException` climbing from a persistence method through two layers of business logic couples both layers to an implementation detail neither otherwise depends on; **the functional-interface wall** — `throws` clauses are part of a method's static type, fixed once when `java.util.function` shipped, so a checked-throwing lambda has nowhere to declare to when plugged into `Function.apply`, forcing a wrap-unchecked, "sneaky throw," custom functional interface, or `Result<T, E>`; and **empty catch blocks** — faced with a checked exception "that cannot really happen," the path of least compiler-satisfying resistance is `catch (SomeException e) {}`, because the compiler enforces *acknowledgment*, not correct handling. The honest counterweight: unchecked exceptions buy composability by making the exception invisible in the signature, which means discoverability moves entirely from the compiler to `@throws` javadoc and code review — that is a real cost, not a free improvement.

```java
// Unchecked: no call site between detection and the HTTP boundary has a specific response.
final class InsufficientFundsException extends RuntimeException {
    InsufficientFundsException(ClientId clientId, Money requested, Money stakeable) {
        super("client " + clientId + " requested " + requested + " against stakeable " + stakeable);
    }
}

// Checked: the caller of card capture has an action available — retry, fail the deposit, alert — and
// ignoring the possibility at compile time would be shipping a bug against a documented p99 of 38s.
final class PspTimeoutException extends Exception {
    PspTimeoutException(String pspReference, java.time.Duration elapsed) {
        super("PSP timeout on reference " + pspReference + " after " + elapsed);
    }
}
```

**The follow-up they will ask** — "how does Spring resolve this in practice?" It translates the single checked `SQLException` into a hierarchy of unchecked `DataAccessException` subtypes (`DuplicateKeyException`, `CannotAcquireLockException`) via `SQLExceptionTranslator`, so callers `catch` the specific category they can act on with no `throws` pollution.

**Where this is written** — [`exceptions/02-in-practice.md`](exceptions/02-in-practice.md), [`exceptions/02b-designing-an-exception-hierarchy.md`](exceptions/02b-designing-an-exception-hierarchy.md), [`exceptions/01-basics.md`](exceptions/01-basics.md).

### Q24. "How does try-with-resources work, and what is a suppressed exception?"

**The 30-second answer.** Every declared resource must implement `AutoCloseable`; the compiler desugars the block so resources close in **reverse declaration order**, and closing happens before any `catch` or `finally` runs. If the body throws and a `close()` also throws, the body's exception becomes the **primary** and the compiler calls `primary.addSuppressed(closeException)` instead of losing either one — retrievable via `Throwable.getSuppressed()`. If the body does not throw but a `close()` does, that close failure **becomes** the primary itself, and any further close failures from other resources are suppressed under it.

**The 5-minute answer.** Mechanically: the try-with-resources block tracks the body's exception, if any, as the in-flight primary `Throwable`. On each resource's `close()` (reverse declaration order), if there is already a primary in flight, a thrown close exception is attached via `addSuppressed` rather than replacing the primary or propagating on its own; with no primary yet, the first close failure *is* promoted to primary, and subsequent close failures from other resources get suppressed under that one, in the order the resources closed. `addSuppressed` populates a completely separate array from the `cause` chain that `initCause`/the four-arg constructor populates — a `Throwable` can carry both a cause chain and suppressed exceptions with no interaction between them, and `printStackTrace()` renders them under distinct labels (`Caused by:` recurses `getCause()`, `Suppressed:` recurses `getSuppressed()`). `**Insight:**` a suppressed exception is exactly as visible as your log formatter makes it — `printStackTrace()` prints `Suppressed:` blocks by default, but a JSON-structured logger that serializes only `message` and `stackTrace` without specifically walking `getSuppressed()` silently drops the close failure, indistinguishable from a clean close. For a close failure that is itself operationally significant — a `PaymentRunFileWriter.close()` failing to flush a batch feeding the banking partner's ingest window — log or alert on it explicitly at the catch point in addition to letting it ride along suppressed.

```java
final class LedgerConnection implements AutoCloseable {
    @Override
    public void close() {
        throw new IllegalStateException("ledger connection already released");
    }
}

final class PaymentRunFileWriter implements AutoCloseable {
    @Override
    public void close() throws java.io.IOException {
        throw new java.io.IOException("payment-run file handle already released");
    }
}

final class TwrSuppressionDemo {
    static void run() {
        try (LedgerConnection ledger = new LedgerConnection();
             PaymentRunFileWriter file = new PaymentRunFileWriter()) {
            throw new LedgerImbalanceException("run PR-2026-08-29 debits 4820.00 credits 4819.67");
        }
        // Reverse close order: file.close() runs first, then ledger.close().
        // Primary: LedgerImbalanceException. Both close() failures land as suppressed, in that order.
    }
}
```

**The follow-up they will ask** — "what if two resources both fail to close and the body threw nothing?" The first close failure (in reverse declaration order) becomes the primary; every subsequent close failure is suppressed under that one — `getSuppressed()` is non-empty even with no body exception at all.

**Where this is written** — [`exceptions/01c-try-with-resources-and-suppression.md`](exceptions/01c-try-with-resources-and-suppression.md), [`exceptions/03a-internals-finally-and-twr-desugaring.md`](exceptions/03a-internals-finally-and-twr-desugaring.md).

### Q25. "What happens if you return inside `finally`?"

**The 30-second answer.** A `return` in `finally` unconditionally discards whatever the `try` block was in the middle of doing — a computed return value or an in-flight exception being thrown — with no trace: not caught, not suppressed, not chained. This holds even with no exception anywhere in the program: `try { return x; } finally { return y; }` always returns `y`.

**The 5-minute answer.** JLS §14.20.2: a `return` completing a `finally` block abruptly supersedes whatever completion the corresponding `try` block was already attempting, whether that was returning a value or propagating a `Throwable`. Measured on JDK 21.0.7, `javap -c` on `static int swallow(int x) { try { throw new InsufficientFundsException(...); } finally { return -1; } }` shows the `try` body as offsets 0–9 (`new`, `dup`, `ldc`, `invokespecial`, `athrow`), then an exception table with one row: `from 0 to 11 target 10 type any`. `type any` — not a specific exception class — is the bytecode-level realization of `finally`: it catches everything unconditionally, because `finally` has to run regardless of what, if anything, is in flight. At offset 10, `astore_1` stores the live, fully-populated `InsufficientFundsException` object into a local slot — and that is the last thing that ever touches that slot. Offsets 11–12 are `iconst_m1; ireturn`: the method returns `-1` right there, and the `try` block's `athrow` never gets to finish propagating. The identical mechanism discards a **computed** value with no exception at all: `try { return stakeMinor; } finally { return -1; }` measured returning `-1` for every input, with the `try` block's `ireturn stakeMinor` never completing because control transfers into the `finally` block's own code first. This shape has been byte-identical across JDK 8, 17, and 21 — it has not moved in over a decade and has no reason to.

```java
static int swallow(int stakeMinor) {
    try {
        throw new InsufficientFundsException("CLIENT_CASH_AVAILABLE too low"); // discarded, no trace
    } finally {
        return -1; // wins unconditionally
    }
}

static int stake(int stakeMinor) {
    try {
        return stakeMinor; // computed, then discarded — never observed by anything
    } finally {
        return -1; // wins unconditionally, no exception was ever involved
    }
}
```

**The follow-up they will ask** — "how do you catch this in review?" Enable a static-analysis rule that flags `return`/`break`/`continue` inside `finally` as a build failure — Error Prone's `Finally` check or SonarQube `S1143` — because the failure mode ("this method always returns -1 no matter what I do to the `try` body") is easy to spend an hour debugging before anyone thinks to look at `finally`.

**Where this is written** — [`exceptions/01d-finally-traps.md`](exceptions/01d-finally-traps.md), [`build-it/03i-finally-return-harness.md`](build-it/03i-finally-return-harness.md), [`build-it/03l-finally-destroys-the-primary.md`](build-it/03l-finally-destroys-the-primary.md).

### Q26. "Is `finally` always executed?"

**The 30-second answer.** No — the guarantee is "every way the *program* can exit the `try` block," not "every way the process can end." `finally` does not run when `System.exit(n)` is called inside the `try` (the process's shutdown sequence never re-enters or unwinds through that frame), does not run on `Runtime.getRuntime().halt(n)` (which skips even registered shutdown hooks), and does not run if the JVM crashes or the thread never leaves the `try` (an infinite loop, a killed process). It does run on a normal return, on an uncaught exception propagating past `main`, and — critically, and often assumed otherwise — when a `catch` block that handled the original exception itself throws.

**The 5-minute answer.** Measured on JDK 21.0.7 across four exit mechanisms: a `try`/`finally` where the body calls `System.exit(1)` prints only the body's line — `"finally: cleanup done"` never prints, not delayed, never executed. Wrapping the identical body in try-with-resources over an `AutoCloseable` gives the same result — no `close()` line at all — because try-with-resources' compiler-generated cleanup is a `finally`-equivalent, and `System.exit` defeats `finally`-equivalents by the same mechanism regardless of syntax. A registered `Runtime.getRuntime().addShutdownHook(...)` **does** run — `Runtime.exit` runs every registered hook, each in its own thread, as part of the JVM's normal shutdown sequence, which is the only cleanup mechanism a process retains once `System.exit` has been called. `Runtime.getRuntime().halt(n)`, by contrast, skips even the shutdown hook — it is specified to forcibly terminate the JVM and exists for the case where the shutdown sequence itself is misbehaving (a hung hook), never as a routine "skip cleanup for speed" call. Underlying bytecode reason `finally` survives a `catch` that throws: for `try { return x/10; } catch (ArithmeticException e) { return 0; } finally { audit(x); }`, the exception table has a row `from 11 to 14 target 20 type any` guarding the **catch block's own code**, offsets 11–14 — so the `any` handler that runs `finally` fires even if the `catch` block itself throws, which is why `audit` is called three times in the compiled method: once on the normal-exit path, once on the catch path, once inside the `any`-handler copy.

| Exit mechanism | `finally` runs | try-with-resources `close()` runs | Shutdown hook runs |
|---|---|---|---|
| `System.exit(n)` | No | No | Yes |
| `Runtime.getRuntime().halt(n)` | No | No | No |
| Normal return from `main` | Yes | Yes | Yes |
| Uncaught exception from `main` | Yes | Yes | Yes |

```java
static void closeRedeal() {
    LedgerConnection ledger = new LedgerConnection();
    try {
        System.out.println("body: fatal condition detected, exiting");
        System.exit(1);
    } finally {
        ledger.close();
        System.out.println("finally: cleanup done"); // never printed
    }
}
```

**The follow-up they will ask** — "so how do you guarantee cleanup on a fatal shutdown?" Register a `Runtime.getRuntime().addShutdownHook`, since it is the only mechanism a `System.exit` call preserves — never call `System.exit` from inside a framework-managed component (a Spring bean, a servlet, a pooled worker thread) in the first place, because it terminates the whole JVM process for everyone else it is serving.

**Where this is written** — [`exceptions/01d-finally-traps.md`](exceptions/01d-finally-traps.md), [`exceptions/01e-catch-discipline-and-top-level-handling.md`](exceptions/01e-catch-discipline-and-top-level-handling.md).

### Q27. "What does catching `InterruptedException` and ignoring it break?"

**The 30-second answer.** A blocking call (`Thread.sleep`, `Object.wait`, `BlockingQueue.take`) throws `InterruptedException` as part of *clearing* the thread's per-thread interrupt flag back to `false` — the throw is the only durable record that cancellation was requested. Catching it and continuing with neither restoring the flag nor propagating the checked exception erases that record entirely: `Thread.currentThread().isInterrupted()` reads `false` immediately afterward, so the executor's shutdown bookkeeping, any later `isInterrupted()` check, and any cooperative cancellation loop become blind to the fact that a stop was ever requested.

**The 5-minute answer.** `InterruptedException` is not a failure report in the ordinary sense — it is a **transferred obligation**: the platform is handing the catching code the job of making the thread actually stop, not just informing it that something went wrong. There are exactly two structurally correct responses, chosen by the enclosing method's signature, not by taste: **propagate** — add `throws InterruptedException` to the enclosing method and don't catch it at all (or catch only to add context before rethrowing), correct whenever the signature is free to declare it; or **restore-and-return** — `Thread.currentThread().interrupt(); return;` (or `break`), the only option inside `Runnable.run()` or any other signature that cannot add a checked `throws`. A third response — catch, log, and continue with neither restore nor propagate — is correct in essentially no application code. QuizStakes frame: a `PaymentRun` worker runs as a `Runnable` submitted to an `ExecutorService`, so `run()` cannot declare `throws InterruptedException`; its inner loop calls `queue.take()` waiting for the next batched withdrawal, and `Thread.currentThread().interrupt(); return;` in the `catch` block both stops the worker immediately and leaves the flag set for the executor's own shutdown bookkeeping to see. Measured: an empty `catch (InterruptedException e) {}` here leaves `isInterrupted()` reading `false` immediately afterward — the shutdown request becomes invisible to everything downstream that would otherwise check it, including the pool's own decision about whether the thread should be discarded rather than returned for reuse.

```java
final class PaymentRunWorker implements Runnable {
    private final java.util.concurrent.BlockingQueue<WithdrawalTransaction> queue;

    PaymentRunWorker(java.util.concurrent.BlockingQueue<WithdrawalTransaction> queue) {
        this.queue = queue;
    }

    @Override
    public void run() {
        while (!Thread.currentThread().isInterrupted()) {
            WithdrawalTransaction next;
            try {
                next = queue.take();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt(); // restore: run()'s signature cannot declare throws
                return;                              // and cannot propagate the checked exception
            }
            process(next);
        }
    }

    private void process(WithdrawalTransaction transaction) {
        // settle against the batched PaymentRun
    }
}
```

**The follow-up they will ask** — "what's the difference between `Thread.interrupted()` and `isInterrupted()`?" `Thread.interrupted()` is `static`, checks the *current* thread, and clears the flag as a side effect of reading it; `isInterrupted()` is an instance method on any `Thread` reference and never clears anything — mixing them up is a common source of the exact same lost-signal bug.

**Where this is written** — [`exceptions/02e-resources-interrupts-and-testing.md`](exceptions/02e-resources-interrupts-and-testing.md).

### Q28. "Why do some production NPEs have no stack trace?"

**The 30-second answer.** This is almost always HotSpot's C2 fast-throw substitution, not a missing flag or a hand-rolled stackless exception. `OmitStackTraceInFastThrow` is **on by default** on JDK 21 (confirmed on 21.0.7): once an implicit exception site — a null check, an array-bounds check, a failing cast — has trapped back to the interpreter often enough at one bytecode location to prove itself statistically hot, C2 stops compiling a path that constructs a fresh exception on every hit and instead throws one preallocated, stackless instance forever, for that compiled version of the method. Helpful NPE messages (JEP 358) have been default-on since Java 15 — so an NPE that has **both** no message and no trace is the fast-throw path, not a "missing `-XX:+ShowCodeDetailsInExceptionMessages`" symptom people sometimes reach for.

**The 5-minute answer.** HotSpot's C2 tracks per-bytecode and per-method trap counters — `PerBytecodeTrapLimit = 4` and `PerMethodTrapLimit = 100` confirmed at these defaults on 21.0.7 — as inputs to its trap-recompilation bookkeeping; there is no documented "substitute after N throws" constant, the substitution point is a heuristic outcome, not a fixed threshold. Once a site is judged to have trapped too often, HotSpot stops emitting the slow path that would `new` and construct a real exception, and throws a single preallocated, stackless instance instead — `null` message, zero-length trace, by construction, because no construction actually ran on that hit. Measured on a tight loop striking one implicit-NPE site (`reservation.split().bonusPortion()` where `split()` returns `null`), the trace length flips between a real captured trace and zero-length at unpredictable iteration counts across repeated runs — the collapse point is **not deterministic**, and no specific iteration count should be quoted as a threshold to plan around. `**Insight:**` the substitution is a property of the *compiled version of the method*, not the exception type — if the method deoptimizes for any reason (a different trap firing, a recompilation), the interpreter has no fast-throw substitution of its own, so the full trace comes back for as long as the method runs interpreted or under C1, then vanishes again once C2 recompiles and the site re-crosses its own reset counters. That "vanished, came back for a few minutes, vanished again" shape in an incident channel with no deploy in between is this exact deoptimize/recompile cycle, not a flaky logging pipeline. The confirmed set of exception types this applies to on this build: `NullPointerException`, `ArrayIndexOutOfBoundsException`, `ClassCastException`, `ArithmeticException`, and `ArrayStoreException` — all reproduced collapsing to a zero-length trace in a tight loop. `-XX:-OmitStackTraceInFastThrow` restores full construction at every implicit-exception site process-wide and is a diagnostic flag to confirm the hypothesis, never a standing production setting, since it reintroduces the full `fillInStackTrace` cost at every hot implicit-exception site in the process.

```java
record StakeSplit(long bonusMinor, long cashMinor) {
    long bonusPortion() { return bonusMinor; }
}

record Reservation(String clientId, StakeSplit split0) {
    StakeSplit split() { return split0; } // returns null for a partially-built Reservation
}

final class FastThrowDemo {
    static long touch(Reservation r) {
        return r.split().bonusPortion(); // implicit NPE site; C2 may substitute a stackless instance here
    }
}
```

**The follow-up they will ask** — "how do you tell this apart from a hand-written stackless exception or `writableStackTrace = false`?" You can't from the trace alone — check whether the throwing method's source contains a `throw` statement for that type at all (fast-throw is implicit-only), whether the exception class overrides `fillInStackTrace()` or routes through the four-arg constructor, and whether `-XX:-OmitStackTraceInFastThrow` restores the trace on a canary before spending a real deploy on the wrong hypothesis.

**Where this is written** — [`exceptions/03c-internals-fast-throw-and-truncation.md`](exceptions/03c-internals-fast-throw-and-truncation.md).

### Q29. "How expensive is throwing an exception?"

**The 30-second answer.** It depends entirely on stack depth, and any answer that states one ratio without naming a depth is wrong. Measured on JDK 21.0.7: a stackless exception's construction is **10.97× cheaper at depth 1** but only **6.42× cheaper at depth 500**; for a full `throw`+`catch`, the multiplier is **11.15× at depth 1**, collapses to **1.47× at depth 100**, and to **1.40× at depth 500**. The cost that goes stackless removes — `fillInStackTrace` — is about **15 ns per captured frame**; the cost it cannot remove — the unwind itself — is about **36.5 ns per frame crossed**, and at depth 500 that unwind alone (~18,248 ns) swamps the entire capture saving (~7,496 ns).

**The 5-minute answer.** The cost lives in `Throwable`'s constructor, not in `throw` or `try` entry. `java.lang.Throwable` initializes `stackTrace` to a shared zero-length sentinel `UNASSIGNED_STACK`, and every public constructor except the four-argument one calls `fillInStackTrace()` unconditionally, which native-walks the stack and populates `backtrace`/`depth` — `StackTraceElement` objects are only materialized lazily, on first `getStackTrace()` read. The four-argument `Throwable(message, cause, enableSuppression, writableStackTrace)` constructor with `writableStackTrace = false` sets `stackTrace = null` and skips the native call entirely — zero stack walk, ever. Measured with real recursion (one Java frame per level, best-of-five timing, five warm-up passes): at **depth 1**, `new` a normal exception costs **276.11 ns/op**, a stackless one costs **25.16 ns/op** — 10.97×; a preallocated singleton costs **2.21 ns/op** for `throw`+`catch`. At **depth 500**, `new normal` costs **8,716.63 ns/op** against `new stackless` at **1,356.59 ns/op** (6.42×) — but `throw+catch normal` is **27,497.91 ns/op** against `throw+catch stackless` at **19,604.74 ns/op**, only 1.40× — and the preallocated singleton, which allocates nothing, is *indistinguishable* from the stackless one at **19,710.80 ns/op**, because both are now dominated by the same unwind. Arithmetic: `fillInStackTrace` costs 250.95 ns at depth 1 and 7,495.78 ns at depth 500 — about 15 ns/frame; the unwind alone (`throw+catch stackless` minus `new stackless`) costs ~18,248 ns over 500 frames — about 36.5 ns/frame. Both scale with depth, but the unwind (which going stackless does *not* remove) grows faster in absolute terms than the capture (which it does remove), so the ratio compresses toward 1 as depth grows. **Do not repeat the claim, found as an open defect in `exceptions/03b-internals-stack-trace-capture.md`, that "the harness never observes anything close to 10× at any depth"** — that file's own published depth-1 row (`normal=237.0ns stackless-ctor=4.8ns`) is itself close to an order of magnitude, and `build-it/03h-stackless-exception.md` independently measures 10.97×/11.15× at depth 1 on the same build; the correct statement is that the 10×+ ratio is real and depth-1-specific, and the well-known ~1.3–1.6× band both files agree on is a depth-100-and-up finding, not a universal one. Bottom line: entering a `try` costs nothing at runtime — the exception table is metadata consulted only when something is actually thrown — the cost is entirely in construction plus (for a real `throw`) the unwind, and at realistic production stack depths (dozens to hundreds of frames), a stackless exception saves real but modest money, while at shallow depth it is genuinely an order of magnitude.

```java
/** Byte-for-byte identical to InsufficientFundsException except for the super call. */
final class StacklessInsufficientFundsException extends QuizStakesException {
    StacklessInsufficientFundsException(ClientId clientId, Money requested, Money stakeable) {
        super("client " + clientId + " requested " + requested + " against stakeable " + stakeable,
                null, false, false); // writableStackTrace = false: no native stack walk ever runs
    }
}

sealed class QuizStakesException extends RuntimeException permits StacklessInsufficientFundsException {
    QuizStakesException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
        super(message, cause, enableSuppression, writableStackTrace);
    }
}
```

**The follow-up they will ask** — "when should you actually go stackless in QuizStakes?" Only for a hot, deliberately-boring control-flow signal at shallow effective depth and where the trace is never read for diagnosis — never for a domain exception a support engineer needs to debug, and never as a blanket policy applied without measuring the depth it actually throws from in production.

**Where this is written** — [`exceptions/03b-internals-stack-trace-capture.md`](exceptions/03b-internals-stack-trace-capture.md) (its "never anything close to 10x" prose is the known open defect — do not cite it), [`build-it/03h-stackless-exception.md`](build-it/03h-stackless-exception.md), [`exceptions/02c-cost-and-control-flow.md`](exceptions/02c-cost-and-control-flow.md).

### Q30. "What is type erasure and what are its consequences?"

**The 30-second answer.** `javac` type-checks generic code against the full parameterized type, then replaces every type variable with the erasure of its leftmost bound in every emitted descriptor, inserts a `checkcast` at every point a caller narrows the erased type back to something specific, and keeps the original generic signature only in an optional `Signature` attribute that only reflection reads — the JVM's linker and verifier never see it. Consequences fall out directly: one runtime class per generic declaration regardless of parameterization, no `new T[n]`, no `new T()`, no `instanceof List<CashEntry>`, no overloading on erased signatures, and static fields/state shared across every parameterization of the same raw class.

**The 5-minute answer.** JLS §4.6 defines erasure recursively: a parameterized type erases to its raw type (`Repository<CashEntry>` → `Repository`, argument discarded entirely, not inspected); a type variable erases to the erasure of its **leftmost** bound (`T extends LedgerEntry` erases to `LedgerEntry`; an unbounded `<T>` erases to `Object`; an intersection bound `<T extends Comparable<T> & Serializable>` erases to `Comparable`, the first listed type); an array type `T[]` erases to `|T|[]`; everything else is the identity. Measured with `javap -p -v` on `Repository<T extends LedgerEntry>` declaring `T find(UUID id)`: the real descriptor is `(Ljava/util/UUID;)LLedgerEntry;` — `T` is gone, replaced by its bound — and that is what the JVM links against and dispatches on at every call site, regardless of whether the caller holds a `Repository<CashEntry>` or `Repository<BonusEntry>` reference. A separate `Signature` attribute in the constant pool (`(Ljava/util/UUID;)TT;`) preserves the pre-erasure generic form as a string — not consulted by the verifier or `invokevirtual`, read only by `Method.getGenericReturnType()` and friends. On the caller side, `CashEntry entry = repo.find(id);` compiles `repo.find(id)` to `invokevirtual Repository.find:(Ljava/util/UUID;)LLedgerEntry;` — the erased descriptor, returning plain `LedgerEntry` — immediately followed by a `checkcast #CashEntry` bytecode inserted by `javac` at the assignment, not inside `Repository` at all. **The cast the reader never wrote lives in the caller's bytecode, not the callee's** — which is exactly where a `ClassCastException` surfaces if a raw-type call or reflective trickery has smuggled the wrong element type in earlier, at a call site that looks unrelated to the actual bug.

```java
class Repository<T extends LedgerEntry> {
    T find(java.util.UUID id) { return null; }
}

final class Caller {
    static CashEntry fetch(Repository<CashEntry> repo, java.util.UUID id) {
        CashEntry entry = repo.find(id); // invokevirtual against erased (UUID)LedgerEntry; then javac-inserted checkcast
        return entry;
    }
}
```

**The follow-up they will ask** — "does erasure mean generics have zero runtime footprint?" No — the `Signature` attribute is real bytes in the class file and reflection genuinely reconstructs `ParameterizedType`/`TypeVariable` from it, so a class's own declared generic shape is recoverable at runtime even though a given *instance*'s type argument never was.

**Where this is written** — [`generics/01a-erasure-and-its-consequences.md`](generics/01a-erasure-and-its-consequences.md), [`generics/03-internals-erasure.md`](generics/03-internals-erasure.md).

### Q31. "Why can't you do `new T[10]`?"

**The 30-second answer.** `anewarray`'s operand is a constant-pool reference resolved once to one concrete class at link time — it cannot take a type variable, because `T` erases to a different bound per instantiation site and there is no single constant-pool entry that could mean all of them at once. `javac` enforces this at the source level with the literal diagnostic `error: generic array creation`. `ArrayList<E>` gets around it the way every generic collection does: it backs itself with a raw `Object[]` (`transient Object[] elementData`) and relies on the compiler's `checkcast` at the *read* side, exactly as any other erased generic type does.

**The 5-minute answer.** The deeper reason isn't just the mechanical `anewarray` constraint — it's array covariance. Java arrays are covariant (`CashEntry[]` is-a `LedgerEntry[]`), and that covariance is made safe *only* by a runtime check on every store: `aastore` checks the array's actual, runtime component type — baked into the array object at creation and never erased — and throws `ArrayStoreException` on a mismatch. If `new T[n]` were legal and erased the way every other generic construct erases, to `new Object[n]`, then every `aastore` into that array would check against the array's real component type, which is now `Object`, not `T` — `Object` accepts anything, so the one guarantee arrays exist to provide would silently vanish for every generic array, with the `ClassCastException` that *should* have fired at the illegal store instead firing later, at some unrelated read, against some caller who did nothing wrong. That's strictly worse than erasure's other compromises — a raw-typed `List` failure is contained to the very next read via a `checkcast` — so the language closes the hole at the only place it can be closed for free: compile time, by refusing the source form outright. Four measured forms on JDK 21.0.7: `new T[n]` — illegal, `generic array creation`; `(T[]) new Object[n]` — legal with a suppressible `[unchecked]` warning, but the array object's real component type stays `Object` forever, the cast is purely a compile-time fiction on the *reference*; `new List<?>[n]` — legal, **no** warning, because `List<?>`'s unbounded wildcard makes it reifiable and `anewarray` can name `java/util/List` directly (confirmed: the disassembly shows `anewarray #7 // class java/util/List`); `new List<Money>[n]` — illegal, same failure as the first row, one level down, because `List<Money>` is not reifiable. `ArrayList<E>`'s real answer, from JDK 21 source: `transient Object[] elementData` — `transient` because `ArrayList` hand-writes its own serialized form — with every accessor doing an internal unchecked cast at the point an `E` is handed back to the caller.

```java
class GenArr<T> {
    T[] illegal(int n) {
        return new T[n]; // error: generic array creation
    }

    @SuppressWarnings("unchecked")
    T[] fiction(int n) {
        return (T[]) new Object[n]; // compiles; the array object's real component type stays Object forever
    }

    java.util.List<?>[] reifiable(int n) {
        return new java.util.List<?>[n]; // legal, no warning: List<?> is reifiable
    }
}
```

**The follow-up they will ask** — "how would you actually build a generic array safely at runtime?" `java.lang.reflect.Array.newInstance(componentType, n)` with an explicit `Class<T>` token, cast once with `@SuppressWarnings` at the single point of creation and never let the raw array escape past that boundary — `ArrayList` avoids the whole problem by never exposing an `E[]`-typed field at all.

**Where this is written** — [`generics/03b-internals-reifiable-types-and-generic-arrays.md`](generics/03b-internals-reifiable-types-and-generic-arrays.md), [`generics/02b-generic-arrays-and-self-types.md`](generics/02b-generic-arrays-and-self-types.md).

### Q32. "Why are generics invariant when arrays are covariant?"

**The 30-second answer.** Arrays predate generics by a decade and needed covariance so pre-generic utilities like sort routines could operate over any `Object[]`-compatible array by simple upcast; they can afford it because the JVM keeps a runtime-checkable component type on every array object and enforces it on every `aastore`. Generics arrived specifically to move cast failures from a confusing runtime `ClassCastException` at an unrelated line to a compile-time error, and erasure throws away exactly the per-element runtime type information that would make a runtime check possible — so generics close the hole the only way left: by forbidding the covariant assignment at compile time instead.

**The 5-minute answer.** Prove invariance is necessary, not arbitrary, by contradiction. Suppose `List<CashEntry> cashEntries = new ArrayList<>(); List<LedgerEntry> entries = cashEntries;` were legal. `entries` and `cashEntries` reference the *same* object; only the compiler's belief about the reference's static type changed. Because `entries` is statically `List<LedgerEntry>`, `entries.add(new BonusEntry(...))` now type-checks — `BonusEntry` is-a `LedgerEntry`. But the underlying `ArrayList` is the one `cashEntries` still holds and is documented to contain only `CashEntry`. The next read, `CashEntry first = cashEntries.get(0);`, fails at runtime with a `ClassCastException` on a line that has nothing wrong with it — the actual bug is in an unrelated `add` call, possibly in a different method. That's precisely the failure class generics exist to eliminate, so JLS §4.10 makes parameterized types invariant regardless of any subtype relationship between their arguments, and `javac` rejects the assignment outright: `error: incompatible types: List<CashEntry> cannot be converted to List<LedgerEntry>` — read literally, "cannot be *converted*": `List<CashEntry>` and `List<LedgerEntry>` are unrelated types, full stop, independent of `CashEntry` being a `LedgerEntry`. Arrays take the opposite position by JLS §10.10: if `S` is a subtype of `T`, `S[]` is a subtype of `T[]`, so `LedgerEntry[] entries = new CashEntry[2];` compiles with zero warnings. The difference is what happens next: `entries[0] = new BonusEntry(...)` also compiles (statically type-checks against `LedgerEntry`), but every `aastore` is specified by JVMS §6.5 to compare the value against the array's *actual* runtime component type, set once at `new CashEntry[2]` and never erased — so this throws `ArrayStoreException: BonusEntry` at the store, and `javap` confirms there's no separate `checkcast`; the type check is folded directly into the `aastore` opcode. Putting the two proofs together explains a third fact for free: `new List<CashEntry>[3]` is illegal too (Q31) — if it were allowed, array covariance would make it assignable to `List<LedgerEntry>[]`, and by the `aastore` proof above a `List<BonusEntry>` store into that reference would need the same runtime check to fail safely — but erasure has already destroyed the distinction between `List<CashEntry>` and `List<LedgerEntry>` by the time any `aastore` runs, so there is no component type left to check against. Covariance's safety net depends on a runtime-checkable component type; erasure removes exactly that for any parameterized type — which is why generic array creation is illegal by rule, not merely inconvenient.

```java
List<CashEntry> cashEntries = new java.util.ArrayList<>();
List<LedgerEntry> entries = cashEntries; // compile error: incompatible types

LedgerEntry[] ledgerEntries = new CashEntry[2]; // compiles: array covariance
ledgerEntries[0] = new BonusEntry(java.util.UUID.randomUUID(), Money.gbp("1.50"));
// throws ArrayStoreException: BonusEntry — caught at the aastore, per-store, every time
```

**The follow-up they will ask** — "how do you get useful substitutability back for generics without breaking safety?" Bounded wildcards — `List<? extends LedgerEntry>` for read-only producer positions, `List<? super CashEntry>` for write-only consumer positions (PECS) — grant a controlled, asymmetric slice of the substitutability invariance forbids outright, without ever reintroducing the aliasing hole the invariance proof above closes.

**Where this is written** — [`generics/01b-variance-and-wildcards.md`](generics/01b-variance-and-wildcards.md), [`arrays/01a-covariance-and-mutability.md`](arrays/01a-covariance-and-mutability.md).

---

**Leaves covered:** 5.1.17–5.1.32 (16 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 532
