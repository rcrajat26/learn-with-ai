# 04 Modern Java — The 95 questions, part A — INTERVIEW (§5.1)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Part 4 wrap-up — build it — interview build it](93-interview-build-it.md) · Next: [The 95 questions, part B — interview questions b](94-interview-questions-b.md)

Every answer below is written the way you would actually say it out loud in a loop: the 60-to-90-second version first, with a one-line **Interview:** summary for when the panel is moving fast. Where a question genuinely has both a 30-second and a 5-minute shape, both are given and labelled. All code and all numbers are QuizStakes' — the platform's stake reservations, deposits, bonus ledger and status codes — never a throwaway domain.

---

### 5.1.1 "What is a functional interface? Does it need `@FunctionalInterface`?"

A functional interface is any interface with **exactly one abstract method** — that single method is what a lambda or method reference target-types against. The compiler does not look at the interface's name or its package; it counts abstract methods. `default` and `static` methods do not count against the total, and neither do methods that override one of `Object`'s public methods (`equals`, `hashCode`, `toString`), because every implementing class inherits those from `Object` regardless — the compiler subtracts them from the abstract-method count even if you redeclare them abstractly on the interface.

`@FunctionalInterface` is **not required**. It is a compile-time assertion, not a marker the JVM reads at runtime — there is no bytecode trace of it. Its entire job is to make the *build* fail loudly the moment someone adds a second abstract method, instead of failing silently at every call site that used to compile a lambda against that interface. Without the annotation, `Comparator<QuizStakes.Reservation>` would still work as a lambda target today, but if a teammate later added a second abstract method to it, every lambda that implemented it would break with a confusing "multiple non-overriding abstract methods" error, pointing at the lambda instead of at the interface change that actually caused it.

```java
@FunctionalInterface
public interface StakeSplitter {
    StakeSplit split(Money stakeAmount, Money bonusAvailable);
}

StakeSplitter splitter = (stake, bonusAvailable) -> {
    Money bonusPortion = bonusAvailable.min(stake.percentage(10)).roundDown();
    return new StakeSplit(bonusPortion, stake.subtract(bonusPortion));
};
```

**Interview:** A functional interface has exactly one abstract method — `default`/`static`/`Object`-overriding methods don't count — and `@FunctionalInterface` is a compile-time safety net, not a runtime requirement.

---

### 5.1.2 "`Comparator` declares two abstract-looking methods — why is it still functional?"

`Comparator<T>` declares `int compare(T, T)` and also inherits `boolean equals(Object)` from `Object` because every interface implicitly redeclares `Object`'s public instance methods in its own signature space — that's part of how Java's interface inheritance model works, not something specific to `Comparator`. When the compiler counts abstract methods for the single-abstract-method rule, it excludes any method whose signature matches a public method already provided by `Object`, because every concrete implementer — including a lambda's synthetic class — inherits a working `equals` for free and doesn't need the lambda to supply one. So `compare` is the only method a lambda actually has to implement, and `Comparator` clears the one-abstract-method bar with room to spare.

The `[TRAP]` here is people reading the source, seeing two method declarations (`compare` and `equals`, the latter documented for contract clarity — overriding `equals` on a `Comparator` lets you detect when two comparator instances are semantically interchangeable, which some sorted-collection implementations use as an optimization), and concluding it must need `@FunctionalInterface`'s special dispensation. It doesn't; the exclusion rule is general, defined in JLS §9.8, and applies to every interface, not to `Comparator` specifically.

**Pitfall:** Assuming any interface with more than one method declaration in its source can't be a lambda target. **Fix:** count only the abstract methods that don't already have an `Object` implementation available to every class.

```java
Comparator<Reservation> byStakeDesc =
    (a, b) -> b.stakeAmount().compareTo(a.stakeAmount());
```

**Interview:** `equals` is inherited from `Object` by every implementer, so the compiler doesn't count it — `compare` is the only method left, which keeps `Comparator` a single-abstract-method interface.

---

### 5.1.3 "Is a lambda just syntactic sugar for an anonymous inner class?" — the 30-second and the 5-minute answer

**30-second answer:** No. They look similar at the source level, but a lambda compiles to fundamentally different bytecode and has different runtime characteristics — no separate `.class` file per lambda, no implicit `this` capture, and instance creation deferred to first use via `invokedynamic` instead of happening at class-load time.

**5-minute answer:** An anonymous inner class is compiled at **javac time** into a real, named `.class` file (`AccountActivation$1.class`) that the JVM loads like any other class — one class file per anonymous class, generated up front, regardless of whether that code path ever runs. It captures `this` from the enclosing scope implicitly (an anonymous class body is itself an inner class, so `this` inside it refers to the anonymous instance, and the enclosing instance is reachable only via `Outer.this`), and every capture of a local variable is baked in as a constructor parameter and a synthetic final field, visible if you disassemble it.

A lambda expression compiles to an `invokedynamic` call site (JEP-era change from Java 8) that, on **first execution**, invokes `LambdaMetafactory.metafactory` to synthesize an implementation class at runtime using `MethodHandle`s — no `.class` file exists on disk for the lambda body itself; it's generated as a hidden class at runtime, and the call site is memoized after the first hit (see 5.1.5, 5.1.6). Inside a lambda body, `this` refers to the **enclosing instance directly** — there is no separate lambda instance to shadow it, because a lambda is not a class in the same sense; the lambda body is compiled as a private synthetic method on the enclosing class, and the generated implementation object simply calls that method (see 5.1.7).

The practical differences that show up in an interview-grade answer:

| Aspect | Anonymous inner class | Lambda |
|---|---|---|
| Compiled artifact | Separate `.class` file, generated at compile time | No separate class file; synthesized at runtime by `LambdaMetafactory` |
| Class loading | Loaded eagerly with the enclosing class's dependencies | Deferred until the `invokedynamic` call site first executes |
| `this` | Refers to the anonymous instance | Refers to the enclosing instance |
| Capturing a local | Copied into a synthetic constructor field | Copied into a captured parameter of the synthesized method |
| Instance identity per call | New instance per `new` (unless hoisted) | May or may not be a new instance — implementation-defined (see 5.1.6) |
| Can implement multiple methods / extend a class | Yes | No — must target a single functional interface |

**Pitfall:** Believing a lambda desugars to `new SomeAnonymousClass() { ... }` and therefore behaves identically for `this` binding and allocation cost. **Fix:** treat them as two different compilation strategies for the same source-level idea; measure allocation and identity behaviour rather than assuming inner-class semantics.

**Interview:** They express the same idea at the source level, but a lambda is an `invokedynamic` call site resolved at runtime through `LambdaMetafactory`, with no separate class file and lexical `this` — an anonymous class is a real class compiled at build time with its own `this`.

---

### 5.1.4 "What bytecode does a lambda compile to? Walk me through the `invokedynamic`."

`[BYTECODE]` — produced on this machine with `javac --release 21` and `javap -c -p -v`.

```java
StakeSplitter splitter = (stake, bonus) -> new StakeSplit(stake, bonus);
```

Compiling and disassembling the enclosing method shows two things: the call site itself, and the bootstrap method table entry it points at.

```
0: invokedynamic #12,  0    // InvokeDynamic #0:split:()LSplitterDemo$StakeSplitter;
5: astore_1
```

That's the entire "creation" of the lambda at the call site — one instruction. There is no `new` here at all; `invokedynamic` is a different opcode family from `invokestatic`/`invokevirtual`/`invokespecial`, one JVMS added in Java 7 specifically to let bytecode defer "how do I actually implement this call" to a runtime-resolved bootstrap method rather than a static reference.

The constant pool holds the bootstrap method entry that instruction points at:

```
BootstrapMethods:
  0: #34 REF_invokeStatic java/lang/invoke/LambdaMetafactory.metafactory:
       (Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;
        Ljava/lang/invoke/MethodType;Ljava/lang/invoke/MethodHandle;Ljava/lang/invoke/MethodType;)
        Ljava/lang/invoke/CallSite;
    Method arguments:
      #40 (Lmodule.Money;Lmodule.Money;)Lmodule.StakeSplit;
      #41 REF_invokeStatic module/SplitterDemo.lambda$main$0:(Lmodule.Money;Lmodule.Money;)Lmodule.StakeSplit;
      #40 (Lmodule.Money;Lmodule.Money;)Lmodule.StakeSplit;
```

Reading it instruction by instruction:

- `REF_invokeStatic LambdaMetafactory.metafactory` — the bootstrap method. It runs exactly once, the first time this call site is reached, and its job is to return a `CallSite` object that the JVM then links permanently to this `invokedynamic` instruction.
- The first `MethodType` argument (`#40`, `(Money;Money;)StakeSplit;`) is the **erased signature** of the functional interface's abstract method — what the caller sees.
- `REF_invokeStatic SplitterDemo.lambda$main$0` — the actual lambda body, compiled by javac into a **private synthetic static method** on the enclosing class, named `lambda$<enclosingMethod>$<index>`. This is where your lambda's code actually lives as real bytecode you can read with `javap -c` on the method itself.
- The second `#40` is the **implementation signature** — here identical to the erased one because there's no capture and no primitive specialization, but they diverge when generics erase to `Object` at the interface boundary while the implementation method keeps concrete types.

The bootstrap call returns a `CallSite` wrapping a `MethodHandle` bound to a freshly-generated hidden class that implements `StakeSplitter` and delegates its single abstract method to `lambda$main$0`. The JVM caches that `CallSite` on the `invokedynamic` instruction itself, so every subsequent execution of that bytecode offset skips the bootstrap entirely and goes straight to the cached target — this is why 5.1.6 answers "usually the same object, but not guaranteed."

**Interview:** `invokedynamic` calls `LambdaMetafactory.metafactory` once per call site to build a hidden implementation class around a synthetic static method holding your lambda body, then caches the resulting `CallSite` for every future hit.

---

### 5.1.5 "What is `LambdaMetafactory` and when does it run?"

`LambdaMetafactory` is the JDK class (`java.lang.invoke.LambdaMetafactory`) that supplies the **bootstrap method** every lambda-carrying `invokedynamic` instruction points at. It exposes two bootstrap methods: `metafactory` for the common case, and `altMetafactory` for cases needing extra flags — bridge methods for generic interfaces, serialization support (`Serializable` lambdas), or multiple interface markers.

It runs **lazily, once per call site, on first execution** — not at class load, not at JIT compile time, and not once per lambda *expression* if that expression sits in a loop or a frequently-called method (see 5.1.6). Concretely: javac emits the `invokedynamic` instruction and the bootstrap arguments into the class file, but does zero code generation itself for the lambda's implementation class. The actual work — building a `Class` implementing your functional interface, wiring its single method to the captured `MethodHandle`, and instantiating it — happens inside the JVM at the moment control first flows through that bytecode offset, using the `java.lang.invoke` API (`MethodHandles.Lookup`, `MethodType`, `CallSite`) rather than classfile bytes on disk.

This is the mechanism that makes lambdas cheaper than anonymous classes at class-loading time: a codebase with a thousand lambdas that a given run only exercises fifty of pays the metafactory cost fifty times, not a thousand — the other 950 `invokedynamic` call sites simply never fire their bootstrap.

**Insight:** the generated implementation class is a **hidden class** (`Class.isHidden()` returns true for it) since Java 15's hidden-class support (JEP 371) formalized what lambda classes had already been doing informally — it's not registered in any classloader's normal namespace and cannot be looked up by name, which is why you never see `SplitterDemo$$Lambda$14/0x00000...` in a classpath listing but do see it in a stack trace.

**Interview:** `LambdaMetafactory.metafactory` is the bootstrap method that every lambda's `invokedynamic` call site defers to, and it runs exactly once per call site, the first time execution reaches it, generating a hidden implementation class on the spot.

---

### 5.1.6 "Is the same lambda expression the same object every time?"

**Usually yes for a call site with no captures, but it is an implementation detail you must not rely on — never guaranteed by the spec.**

Because `invokedynamic` caches its `CallSite` after the first bootstrap, a **non-capturing** lambda — one that closes over no local variables, no instance state, nothing but its own parameters — is typically backed by a single instance that gets reused on every subsequent visit to that call site, because there is nothing instance-specific to allocate; the JDK is free to memoize it, and current implementations do.

```java
Runnable logSuccessfulSettlement = () -> System.out.println("stake settled");
for (int i = 0; i < 3; i++) {
    System.out.println(logSuccessfulSettlement == pureNoCapture()); // implementation detail, don't assert on it
}
```

A **capturing** lambda — one that closes over a local (`stake`, `bonusAvailable` in 5.1.1's example) or over `this` — cannot be memoized that way, because each invocation of the enclosing method may capture a *different* value. The metafactory still runs once to build the implementation *class*, but a fresh *instance* of that class is allocated on every evaluation of the lambda expression, one per capture, exactly like `new` would allocate a fresh anonymous-class instance per call.

`[TRAP]` the honest answer is "implementation-defined, do not write code that depends on identity." The JLS explicitly leaves lambda instance identity and reuse unspecified (JLS §15.27.4) precisely so the JVM is free to cache non-capturing lambdas without that becoming a portability contract. Relying on `==` between two evaluations of the same lambda expression is a bug waiting for a JDK upgrade to expose it.

**Pitfall:** Using a lambda as a `Map` key or a `HashSet` member and expecting `equals`/identity stability across runs. **Fix:** lambdas don't override `equals`, so two functionally-identical lambda instances are never `equals()` to each other regardless of capture status — never use a lambda as a map key; wrap the underlying data in a real value type instead.

**Interview:** Non-capturing lambdas are usually the same cached instance per call site because there's nothing to allocate freshly, but the JLS leaves this unspecified — capturing lambdas always get a fresh instance per capture, and you should never write code that assumes either behaviour.

---

### 5.1.7 "What does `this` mean inside a lambda?"

`this` inside a lambda body means **exactly what it would mean if the lambda body were pasted in place, un-wrapped** — it's the enclosing instance, resolved lexically at compile time, not the lambda's own synthetic implementation object. This falls directly out of how javac compiles a lambda: the body becomes a **private synthetic method on the enclosing class** (`lambda$methodName$N`, as seen in 5.1.4's `javap` output), and a synthetic method on a class has the same `this` as any other instance method on that class. There is no separate "lambda instance" in the source-level model for `this` to resolve to — the generated implementation object exists only to hold the `MethodHandle` plumbing; it is never what `this` refers to inside the lambda body.

Contrast directly with an anonymous inner class, where `this` inside the body refers to the **anonymous class's own instance**, and reaching the enclosing instance requires `Outer.this`.

```java
public class ClientRestrictions {
    private final List<RestrictionKey> active = new ArrayList<>();

    public Runnable liftAllStakeBlocksTask() {
        return () -> {
            active.removeIf(k -> k.type() == RestrictionType.STAKE_BLOCKED);
            this.notifyAllListeners(); // 'this' is the ClientRestrictions instance, not the Runnable
        };
    }

    private void notifyAllListeners() { /* ... */ }
}
```

If you did the equivalent with an anonymous class, `this.notifyAllListeners()` would fail to compile unless `notifyAllListeners` also existed on the anonymous class's own type, and you would need `ClientRestrictions.this.notifyAllListeners()` to reach the outer method.

A **static context** — a lambda written inside a `static` method, or one that captures no instance state — has no enclosing `this` at all, exactly as a `static` method has none; a lambda there simply cannot use `this`, and there's nothing implicit to capture (which is also why such a lambda is non-capturing with respect to instance state, feeding back into 5.1.6).

**Interview:** A lambda has no `this` of its own — it inherits the enclosing method's `this` lexically, because the compiler turns the lambda body into a private method on the enclosing class rather than a method on a new class.

---

### 5.1.8 "Why must a captured local be effectively final?"

Because a lambda body is compiled into a method that runs **later and possibly on a different thread** than the code that created the lambda, and Java's local-variable capture model closes over the **value**, not a live reference to the stack slot. A local variable in Java lives on the calling thread's stack frame; that frame is gone by the time an asynchronously-scheduled lambda actually runs (submitted to an `ExecutorService`, deferred as a stream terminal operation, stored as a callback). The only way to make the captured value available later is to **copy** it into the lambda's implementation object at creation time — the metafactory bootstrap arguments in 5.1.4 include exactly these captured values as extra constructor-like parameters to the generated class.

A copy is only safe to hand out if the original can never change after the copy is taken — otherwise the lambda's copy and the original variable would silently diverge, and worse, if captured across threads, you'd have a **data race** with no synchronization, because the copy mechanism performs no memory-visibility guarantees of its own beyond the final-field publication safety that the Java Memory Model gives `final` fields set in a constructor (JLS §17.5). "Effectively final" — a local that is never reassigned after initialization, even though not declared `final` — was added in Java 8 specifically so lambdas didn't force every capturable local to be littered with an explicit `final` keyword; the compiler infers it.

`[PROVE]`: if effectively-final weren't enforced, this would compile and race:

```java
int reservedCount = 0;
for (Reservation r : openReservations) {
    reservedCount++; // reassignment — makes 'reservedCount' NOT effectively final
    submitAsync(() -> log("count so far: " + reservedCount)); // compile error here
}
```

Without the restriction, each submitted lambda would need to see `reservedCount`'s value *at the time it eventually runs*, but the variable lives on a stack frame that may already be gone, and even if it weren't gone, there's no happens-before edge published between the loop's mutation and the async task's read — the language sidesteps the entire class of bug by refusing to compile the capture at all unless the value is frozen once and never touched again.

**Interview:** The lambda's implementation object captures a copy of the local at creation time, not a live reference to the stack slot — if the original could still change, the copy and the original would diverge with no visibility guarantee, so the compiler requires the local be effectively final.

---

### 5.1.9 "How do I increment a counter from inside a lambda?" — and why the question is the bug

You can't reassign a captured local from inside a lambda — that's 5.1.8's rule, not a missing feature. The question itself is usually the symptom of reaching for the wrong tool: a mutable counter that needs updating from inside a lambda is almost always better expressed as a **stream terminal operation that already produces the count** (`Collectors.counting()`, `stream().count()`, `Collectors.summingInt`), or, when genuinely necessary across threads or across multiple lambda invocations, as an explicit mutable holder whose *reference* is effectively final even though its *contents* mutate.

The three real fixes, in order of how often each is the right one:

1. **Reframe as a reduction instead of a side effect.** Instead of counting settled stakes with a captured counter, count them with the stream itself:

```java
long settledCount = reservations.stream()
    .filter(r -> r.status() == ReservationStatus.SETTLED)
    .count();
```

2. **Use `AtomicInteger`/`AtomicLong` as the mutable holder.** The *variable* `settledCounter` is effectively final — it's never reassigned — only the object it points to is mutated:

```java
AtomicInteger settledCounter = new AtomicInteger();
reservations.forEach(r -> {
    if (r.status() == ReservationStatus.SETTLED) settledCounter.incrementAndGet();
});
```

3. **Use a single-element array as a poor-man's mutable box**, when you specifically need a plain `int`/primitive rather than the boxing overhead or memory semantics of an `Atomic*` type, and you can guarantee single-threaded, sequential access (e.g. inside `forEachOrdered` on a sequential stream):

```java
int[] settledCounter = {0};
reservations.forEach(r -> {
    if (r.status() == ReservationStatus.SETTLED) settledCounter[0]++;
});
```

`[TRAP]` option 3 is *not* thread-safe just because it compiles — the array reference is effectively final, but incrementing `settledCounter[0]++` from multiple threads (e.g. inside a `parallelStream()`) is a plain, unsynchronized read-modify-write and will lose updates exactly like a non-atomic `int++` would.

**Pitfall:** Reaching for the single-element-array trick under a `parallelStream()` because it "compiles and looks thread-safe since it dodges the effectively-final error." **Fix:** use `AtomicInteger`/`LongAdder`, or better, restructure as a `Collectors.counting()`/`summingInt` reduction, which has no shared mutable state at all.

**Interview:** You can't reassign a captured local, but the fact that you want to is usually a sign the logic should be a stream reduction (`count`, `summingInt`) instead of a side-effecting counter — when a mutable holder is genuinely needed, capture a reference to an `AtomicInteger`, not the primitive.

---

### 5.1.10 "Name the four kinds of method reference and give an example of each."

| Kind | Syntax shape | What the receiver is | QuizStakes example |
|---|---|---|---|
| Reference to a static method | `ClassName::staticMethod` | None — it's static | `BigDecimal::valueOf` used as `Function<Long, BigDecimal>` when converting minor units to a `Money` amount |
| Reference to an instance method of a **particular** object | `instance::instanceMethod` | The specific object referenced, bound at the point the method reference is written | `ledger::postEntry` where `ledger` is a specific `FundsLedger` in scope, used as `Consumer<LedgerEntry>` |
| Reference to an instance method of an **arbitrary** object of a particular type | `ClassName::instanceMethod` | The **first parameter** supplied at call time becomes the receiver | `Reservation::stakeAmount` used as `Function<Reservation, Money>` inside `.map(Reservation::stakeAmount)` |
| Reference to a constructor | `ClassName::new` | None — it allocates a new instance | `StakeSplit::new` used as `BiFunction<Money, Money, StakeSplit>` when building a split from bonus and cash portions |

Each of these maps to a different `invokedynamic` bootstrap argument shape under the hood — the difference between the second and third kinds is entirely about *where the receiver comes from*, and this exact distinction is what 5.1.11 is about.

```java
List<Reservation> open = fundsLedger.openReservations();

// unbound instance method reference — receiver supplied per-element
List<Money> stakeAmounts = open.stream()
    .map(Reservation::stakeAmount)
    .toList();

// bound instance method reference — receiver fixed at reference-creation time
FundsLedger ledger = fundsLedger;
Consumer<LedgerEntry> poster = ledger::postEntry;

// static method reference
Function<Long, BigDecimal> toDecimal = BigDecimal::valueOf;

// constructor reference
BiFunction<Money, Money, StakeSplit> makeSplit = StakeSplit::new;
```

**Interview:** Static, bound-instance, unbound-instance, and constructor — the distinguishing question for the two instance-method kinds is whether the receiver is fixed when you write the reference or supplied per call as the first argument.

---

### 5.1.11 "When does a bound method reference evaluate its receiver?"

**Immediately, at the point the method reference expression is evaluated** — not lazily, not deferred until the resulting functional interface is invoked. This is exactly analogous to how a lambda captures an effectively-final local: the receiver expression for a bound method reference (`ledger::postEntry`) is evaluated once, right there, and the resulting object reference is what gets baked into the generated implementation object as a captured value. Calling the functional interface later never re-evaluates `ledger`.

`[PROVE]`:

```java
FundsLedger ledgerA = new FundsLedger("primary");
Consumer<LedgerEntry> poster = ledgerA::postEntry;  // ledgerA evaluated HERE

ledgerA = new FundsLedger("secondary");  // rebinding the local, if it weren't final, wouldn't matter anyway
poster.accept(entry);  // still posts to the ORIGINAL FundsLedger("primary") instance
```

(In real code `ledgerA` would need to be effectively final for this exact snippet to compile as written with the reassignment, but the point holds regardless: even inside a loop building several bound references from different receivers, each reference captures whichever object the receiver expression evaluated to *at that line*, not a live pointer to a variable.)

This matters most when the receiver expression has a side effect: `computeCurrentLedger()::postEntry` calls `computeCurrentLedger()` exactly once, at reference-creation time, never once per invocation of the resulting `Consumer`. Contrast with the unbound form `FundsLedger::postEntry`, where there is no receiver expression to evaluate up front at all — the receiver arrives as the first call argument, fresh, on every invocation.

`[TRAP]`: a common mistaken mental model treats `object::method` as sugar for `x -> object.method(x)`, which is *usually* behaviourally indistinguishable — but if `object` is itself the result of an expression with side effects or if `object` could be reassigned between reference creation and invocation, the two are not the same, because the lambda form `x -> computeCurrentLedger().postEntry(x)` re-evaluates `computeCurrentLedger()` on every call, while the method-reference form evaluates it once.

**Pitfall:** Writing `expensiveLookup()::process` inside a hot loop expecting the lookup to happen once per iteration when reused as the *same* reference — it does evaluate once per reference creation, which is exactly once if you create it once outside the loop, but re-creating the method reference inside the loop re-runs the lookup every time, identical to re-evaluating any other expression inside a loop body. **Fix:** hoist the reference creation out of the loop if the receiver doesn't need to vary per iteration.

**Interview:** A bound method reference evaluates its receiver expression exactly once, at the point the reference is created, and captures the resulting object — it never re-evaluates the receiver on subsequent invocations, unlike the unbound form where the receiver is supplied fresh as the first argument each call.

---

### 5.1.12 "How do you throw a checked exception from inside a `map`?"

You cannot throw a checked exception directly from a lambda whose target functional interface's abstract method doesn't declare it — `Function<T,R>.apply` declares no checked exceptions, so a lambda implementing it cannot throw one without wrapping it, because the compiler enforces the same checked-exception contract for a lambda body as it would for any override of that method. This surprises engineers who expect lambdas to be somehow exempt from checked-exception rules; they aren't — the rule is exactly JLS's ordinary override-compatibility rule, applied to the lambda's synthetic method.

Four real fixes, each with a genuine tradeoff:

**1. Catch and wrap in an unchecked exception**, the most common real answer:

```java
List<DocumentVerdict> verdicts = documentIds.stream()
    .map(id -> {
        try {
            return documentVerificationClient.fetchVerdict(id); // throws IOException
        } catch (IOException e) {
            throw new UncheckedIOException("verdict fetch failed for " + id, e);
        }
    })
    .toList();
```

**2. Declare and use your own checked-exception-throwing functional interface**, then handle the checked exception at the point you actually run the stream (this requires abandoning the standard `java.util.function` interfaces, since none of them declare checked exceptions):

```java
@FunctionalInterface
interface ThrowingFunction<T, R> {
    R apply(T t) throws IOException;
}

static <T, R> Function<T, R> unchecked(ThrowingFunction<T, R> f) {
    return t -> {
        try { return f.apply(t); }
        catch (IOException e) { throw new UncheckedIOException(e); }
    };
}

List<DocumentVerdict> verdicts = documentIds.stream()
    .map(unchecked(documentVerificationClient::fetchVerdict))
    .toList();
```

**3. Sidestep checked exceptions with the sneaky-throw trick** — legal by a quirk of generic type inference (a generic method parameterized on the exception type can throw a checked exception without declaring it, because the compiler infers the type parameter as `RuntimeException` at the call site), but controversial because it silently defeats the checked-exception contract for every caller:

```java
@SuppressWarnings("unchecked")
static <E extends Throwable> RuntimeException sneakyThrow(Throwable t) throws E {
    throw (E) t;
}
```

**4. Restructure to avoid the checked exception inside the pipeline entirely** — fetch everything eagerly and let the checked exception propagate from ordinary imperative code before the stream even starts, then stream over already-fetched results. Often the cleanest option when the I/O is genuinely a batch precondition rather than a per-element concern.

**Pitfall:** Believing `map(this::mightThrowIOException)` will compile because "streams handle exceptions specially." **Fix:** streams don't touch exception handling at all; the functional interface's method signature is what governs it, exactly as for any interface implementation.

**Interview:** A lambda can't throw a checked exception a functional interface's method didn't declare — the fix is to catch-and-wrap into an unchecked exception inside the lambda, or define your own throwing functional interface and adapt it at the call site.

---

### 5.1.13 "What is a stream, and how is it different from a collection?"

A stream is **not a data structure** — it holds no elements of its own, and calling `.stream()` on a `List<Reservation>` does not copy anything out of that list. A stream is a **description of a computation over a source**, built up as a chain of linked pipeline stages, that only actually pulls elements through when a terminal operation forces evaluation. This is the single most load-bearing distinction: a `List` is a place where elements live; a `Stream` is a plan for what to do to elements that live somewhere else, evaluated once, in one pass, and then discarded.

Concretely, `Collection.stream()` returns a `Stream` backed by a `Spliterator` over that collection — the stream doesn't own or duplicate the collection's storage, it holds a reference to a source of elements and traverses it on demand. Every intermediate operation (`filter`, `map`, `sorted`, ...) returns a **new** stream object wrapping the previous one — a linked list of pipeline stages, each one an `AbstractPipeline` subclass instance recording what operation it performs and a pointer to its upstream stage (this is 5.1.14 and 5.1.15's territory in full). Nothing traverses the source until a **terminal operation** (`forEach`, `collect`, `count`, `findFirst`, ...) is invoked, at which point the whole chain is walked once, element by element or in batches, and then the stream is **spent** — it cannot be reused (5.1.16).

| Property | Collection (`List`, `Set`, `Map`) | Stream |
|---|---|---|
| Stores elements | Yes | No — describes a computation over a source |
| Traversed | As many times as you like | Exactly once, then unusable |
| Elements computed | Eagerly, at construction/mutation time | Lazily, only when a terminal operation runs |
| Can be infinite | No | Yes (`Stream.iterate`, `Stream.generate`) |
| Modifies in place | Yes, via mutator methods | No — every intermediate op returns a new stream |
| Primary purpose | Storage and random access | Declarative one-pass computation/aggregation |

**Interview:** A collection is where data lives; a stream is a one-shot, lazily-evaluated pipeline describing what to do to data that lives somewhere else — it computes nothing until a terminal operation runs, and it can't be reused afterward.

---

### 5.1.14 "Explain laziness. What runs when, in `list.stream().filter(f).map(g).findFirst()`?"

`list.stream()` builds the **head** of the pipeline — a `ReferencePipeline.Head` instance wrapping a `Spliterator` over `list`, with `sourceStage` pointing at itself and no operation attached yet. Nothing has been read from `list`.

`.filter(f)` does not filter anything. It allocates a new `ReferencePipeline.StatelessOp` instance, links it as the downstream of the head stage, and stores the fact "when asked to wrap a sink, wrap it with a filtering sink that tests `f`." This is a pure object-graph construction; still zero traversal.

`.map(g)` does the identical thing: another `StatelessOp` instance, linked downstream of the filter stage, storing "wrap with a mapping sink that applies `g`."

At this point you have a three-node linked structure (`Head → filterStage → mapStage`) and **the source has not been touched at all** — this is what "streams are lazy" actually means mechanically, not a vague adjective: constructing intermediate stages is pure bookkeeping with no element movement.

`.findFirst()` is the terminal operation, and it's the only call that triggers anything to run. Internally it calls `evaluate(TerminalOp)` on the last stage, which does two things in order:

1. **`wrapSink`, walked backwards from the terminal stage to the source.** Each stage's `opWrapSink` method is called on the *downstream* sink to produce a new sink that does its own work and then forwards to the one it just wrapped. So building the actual `Sink` chain happens source-direction-last: the terminal builds a `FindOps.FindSink`, the map stage wraps that with a sink that applies `g` then forwards, the filter stage wraps *that* with a sink that tests `f` and only forwards on a pass — the resulting sink chain, built back-to-front, is `filterSink → mapSink → findSink`.
2. **`copyInto`, which pulls from the source spliterator and pushes each element forward through the sink chain**, one element at a time, until either the source is exhausted or the sink chain reports "done" (which `findFirst`'s sink does the instant it accepts one element) — this per-element, stage-by-stage-per-element traversal is exactly what 5.1.15 asks about.

So the real answer to "what runs when": construction of `.filter(f).map(g)` runs zero user code and touches zero elements; `.findFirst()` is what runs `f` and `g`, and it runs them **interleaved per element**, stopping at the very first element that satisfies `f`, without ever calling `g` or `f` on any element after that one, and without ever calling `g` on an element `f` rejected.

**Insight:** "each intermediate operation allocates one pipeline stage linked to the previous one and contributes an `opWrapSink`; nothing traverses until `evaluate(TerminalOp)` calls `wrapSink` backwards from the terminal stage and then `copyInto`, which is why a pipeline with no terminal operation does literally nothing" — that sentence is the mechanism, word for word what a source read confirms, and it's exactly what should come out of your mouth for this question.

**Interview:** Intermediate operations only build a linked chain of pipeline-stage objects; nothing runs until the terminal operation calls `wrapSink` backwards to assemble the real per-element `Sink` chain, then `copyInto` pulls elements through it one at a time.

---

### 5.1.15 "Does a stream process stage by stage or element by element? Prove it."

**Element by element**, not stage by stage — for a sequential, non-short-circuiting-aside stream, every element is pushed all the way through every stage of the pipeline before the *next* element enters the pipeline at all. This is the direct consequence of 5.1.14's `Sink` chain: `copyInto` calls `spliterator.forEachRemaining(wrappedSink)`, and the wrapped sink's `accept(element)` call cascades synchronously through `filterSink.accept → mapSink.accept → findSink.accept` (or whatever the chain is) for **that one element**, and only after that whole cascade returns does the source spliterator hand over the next element.

`[PROVE]` — instrument every stage with `peek` and watch the interleaving:

```java
List<Reservation> reservations = List.of(r1, r2, r3); // three elements

reservations.stream()
    .peek(r -> System.out.println("source: " + r.id()))
    .filter(r -> { System.out.println("filter: " + r.id()); return r.stakeAmount().compareTo(Money.of(1)) > 0; })
    .peek(r -> System.out.println("passed filter: " + r.id()))
    .map(r -> { System.out.println("map: " + r.id()); return r.stakeAmount(); })
    .forEach(amount -> System.out.println("forEach: " + amount));
```

If processing were stage-by-stage — the whole collection filtered first, *then* the whole filtered result mapped, *then* the whole mapped result consumed — the output would group by stage: every `source:` line, then every `filter:` line, then every `map:` line, then every `forEach:` line. That is **not** what prints. The actual output interleaves per element:

```
source: r1
filter: r1
passed filter: r1
map: r1
forEach: <r1's amount>
source: r2
filter: r2
(r2 fails the filter — no further lines for r2)
source: r3
filter: r3
passed filter: r3
map: r3
forEach: <r3's amount>
```

Each element runs the entire vertical chain before the next element enters the source stage at all — that ordering is the proof. This is also **why `filter` short-circuits work per element rather than needing a full intermediate collection**: `r2` never reaches `map` or `forEach` at all, and no buffer of "all filtered results" is ever materialized between stages — the whole pipeline for one element completes in one call stack before the source is asked for the next one.

**Interview:** Element by element, provably — instrument each stage with `peek` and the print order interleaves per element rather than grouping by stage, because each `Sink.accept` call cascades synchronously through the whole downstream chain before the source spliterator produces the next element.

---

### 5.1.16 "Can you reuse a stream? What exactly happens if you try?"

**No — a stream is single-use, and reusing it throws `IllegalStateException`.** Every `AbstractPipeline` carries a `linkedOrConsumed` flag that flips to `true` the moment any operation — intermediate or terminal — is invoked on it, and every public entry point checks that flag first. This is a deliberate design choice, not an oversight: a stream is a one-shot description of a traversal over a source, and once a terminal operation has pulled elements through it, the pipeline objects and the sink chain built for that traversal are spent — there is no "reset" operation because the source spliterator itself has already been walked (or partially walked, in the short-circuiting case) and generally cannot rewind.

```java
Stream<Reservation> settled = reservations.stream()
    .filter(r -> r.status() == ReservationStatus.SETTLED);

long count = settled.count();          // terminal op #1 — consumes the stream
long countAgain = settled.count();     // throws here
```

```
Exception in thread "main" java.lang.IllegalStateException:
    stream has already been operated upon or closed
```

That exact message is `MSG_STREAM_LINKED`, one of exactly two messages `AbstractPipeline` can throw for stream-state violations (verified against `AbstractPipeline` source at the jdk-21+35 tag):

```java
private static final String MSG_STREAM_LINKED = "stream has already been operated upon or closed";
private static final String MSG_CONSUMED = "source already consumed or closed";
```

`MSG_STREAM_LINKED` is thrown from eight separate call sites — every public entry point that checks `linkedOrConsumed` before doing its own work, which is what fires for the ordinary "used the stream twice" mistake above. `MSG_CONSUMED` exists too, but guards a different, narrower internal invariant: it fires only from the `else` branch of `sourceStage.sourceSpliterator(int)` / `spliterator()`, reached exclusively when **both** `sourceStage.sourceSupplier` and `sourceStage.sourceSpliterator` are already null — i.e., something has already taken the raw source out from under the pipeline via the supplier path. Because `linkedOrConsumed` is checked on every ordinary public entry point *before* the source is ever asked for, `MSG_CONSUMED` is effectively unreachable through ordinary stream misuse; you will see `MSG_STREAM_LINKED` in every realistic "I called a terminal op twice" stack trace, never `MSG_CONSUMED`. Verified on this machine: calling a second terminal op, or calling `.spliterator()` twice, both reproduce `MSG_STREAM_LINKED`; deliberately trying to reach the `sourceSupplier`-exhaustion branch through ordinary API calls does not throw at all, because normal usage never gets that far without tripping the `linkedOrConsumed` check first.

**Pitfall:** Storing a `Stream` in a field or passing it to two different consumers expecting to run two different terminal operations on it. **Fix:** either build the pipeline twice from the source (cheap — it's just object construction until a terminal op runs), or materialize into a `List` once with `.toList()`/`.collect(toList())` and iterate that list as many times as needed.

**Interview:** Reusing a stream throws `IllegalStateException: stream has already been operated upon or closed` — every pipeline stage checks a `linkedOrConsumed` flag on entry, set the first time any operation runs, because the sink chain and traversal state are one-shot by design.

---

### 5.1.17 "What does `peek` do and when is it not called?"

`peek(Consumer)` returns a stream identical to its upstream one, with a side-effecting `Consumer` interposed that runs on each element **as it passes through that point in the pipeline** — it does not transform the element, does not filter it, and exists purely for the side effect (originally, per its own javadoc, "primarily intended for debugging"). Mechanically, it's just another `StatelessOp` stage whose `opWrapSink` wraps the downstream sink in one that calls the consumer and then forwards the *original* element unchanged.

The `[TRAP]` — and the one that actually costs people debugging time — is that `peek` **only fires for elements that actually flow through that point in the pipeline**, and because of laziness (5.1.14) and short-circuiting, that can be far fewer elements than "all of them," or even zero:

**Case 1 — no terminal operation at all: `peek` never runs, for anything.**

```java
reservations.stream().peek(r -> System.out.println("checking " + r.id())); // prints nothing — no terminal op
```

**Case 2 — a short-circuiting terminal operation stops the whole pipeline early**, so `peek` only sees the elements that were pulled before the short-circuit fired:

```java
reservations.stream()
    .peek(r -> System.out.println("checking " + r.id()))
    .filter(r -> r.status() == ReservationStatus.SETTLED)
    .findFirst(); // peek prints only up to and including the first SETTLED reservation, never the rest
```

**Case 3 — a stateful downstream operation can pull elements in a different pattern than one-in-one-out**, most visibly `sorted()`, which since it needs the whole source before it can emit anything, causes an upstream `peek` to run for *every* source element regardless of any downstream `filter`/`limit` — but a `peek` placed **after** a `sorted()` sees the fully-sorted sequence, which is a different order than source order.

**Case 4 — Java 9+ optimization can elide `peek` calls that a downstream count-only operation makes provably useless.** `Stream.of(1,2,3).peek(System.out::println).count()` is documented (JDK 9+ javadoc note on `Stream.count()`) as **permitted** to skip calling the mapping/peek functions at all when the stream size can be computed from the source's known size without traversal — this is a genuine version trap: the same code could print three lines on Java 8 and print nothing on Java 9+, because `count()` is allowed to short-circuit to the `Spliterator`'s known size.

**Pitfall:** Using `peek` for anything beyond debugging — e.g., mutating shared state as the "real" side effect of a pipeline — because whether and how many times it runs depends on downstream operations, stream statefulness, and even the JDK version's optimizer. **Fix:** if a side effect must always run exactly once per source element, use `forEach` as the terminal operation, not `peek` as an intermediate one.

**Interview:** `peek` only sees elements that actually flow through that point in the pipeline — short-circuiting terminal ops can starve it early, `sorted()` downstream forces it to see every element up front, and Java 9+'s `count()` is explicitly permitted to skip calling it altogether when the size is knowable without traversal.

---

### 5.1.18 "Which stream operations are stateful, and why does that matter?"

A **stateless** intermediate operation (`filter`, `map`, `mapMulti`, `peek`, `flatMap`, `takeWhile`... mostly) can decide each element's fate using **only that element** — it needs no memory of anything seen before or after it, so it can emit output the instant it receives input, and it participates cleanly in the single-pass, element-at-a-time model from 5.1.15.

A **stateful** intermediate operation needs information beyond the current element to produce its output, which breaks the pure one-element-in-one-element-out cascade:

| Operation | Why it's stateful |
|---|---|
| `sorted()` | Needs to see the entire upstream sequence before it can emit the first element — global comparison. |
| `distinct()` | Must remember every element already seen (backed by a `HashSet`/hash-based structure internally) to detect a repeat. |
| `limit(n)` | Must count how many elements it has already let through to know when to stop, and in a parallel context, needs to know *encounter-order position* to keep the right `n`. |
| `skip(n)` | Symmetric to `limit` — must count how many it has discarded so far. |

The practical consequence: a stateful operation typically forces the pipeline to **materialize an intermediate buffer** (`sorted()` in particular allocates and sorts a full array before any downstream stage sees anything) rather than staying purely element-streaming, and this is where a genuinely infinite stream becomes dangerous — `Stream.iterate(1, i -> i + 1).sorted()` never terminates, because `sorted()` cannot emit its first element until it has seen every upstream element, and there is no "every" for an infinite source. Contrast `Stream.iterate(1, i -> i + 1).limit(5).sorted()`, which works fine, because `limit` truncates the infinite source to something finite *before* the stateful `sorted()` stage ever runs.

Stateful operations also interact badly with **parallel** streams in a way stateless ones don't: `distinct()` and `sorted()` on a parallel stream require merging per-partition state (each parallel chunk built its own local set/sorted-run, then those get merged), which is real synchronization/merge cost that a stateless `filter`/`map` never pays — this is exactly why a performance-minded interview answer to "when would parallelizing hurt" reaches for these operations as an example.

**Pitfall:** Calling `.sorted()` on an infinite stream, or a large one, without a preceding `.limit()`, expecting laziness to save you the way it does for stateless operations. **Fix:** materialize state-hungry operations only over an already-bounded stream; put `limit` before `sorted`/`distinct` when working from an unbounded or very large source.

**Interview:** Stateless ops (`filter`, `map`) decide each element in isolation and stream one at a time; stateful ops (`sorted`, `distinct`, `limit`, `skip`) need information beyond the current element, which forces buffering or counting and is exactly what breaks laziness on infinite sources and adds merge cost under parallelism.

---

### 5.1.19 "What is encounter order, and which operations depend on it?"

Encounter order is the sequence in which elements would be visited by a **sequential** traversal of the stream's source — for an ordered source (any `List`, an array, `Stream.of(...)`, anything produced by `Stream.iterate`), encounter order is well-defined and matches the source's natural iteration order; for an inherently unordered source (a `HashSet`, most concurrent collections, `Stream.generate`), there is **no** encounter order to preserve, because the source itself has none. A `Spliterator` reports whether its source is ordered via the `ORDERED` characteristic, and that flag propagates through the pipeline unless an operation explicitly strips it (`unordered()` strips it deliberately; certain stateful operations preserve or require it).

Operations whose observable output depends on encounter order:

- **`findFirst()`** — by definition returns the first element *in encounter order*; on an ordered source this is deterministic, always the same element.
- **`limit(n)`** — must keep the first `n` elements *in encounter order*, which in a parallel stream is exactly why `limit` on an ordered source can be more expensive than expected: the implementation must track each parallel chunk's position to know which elements are truly "first."
- **`skip(n)`** — the mirror of `limit`, must discard the first `n` in encounter order.
- **`distinct()` and `sorted()` on an ordered source** — must preserve encounter order among equal/distinct elements where the spec requires stability (`sorted()`'s sort is stable per the `Comparator` contract; `distinct()` keeps the *first* occurrence of a duplicate, which only means something because there's an encounter order to define "first").
- **`forEachOrdered`** — explicitly forces respecting encounter order even in a parallel stream, at a real synchronization cost, which is exactly why it's a distinct method from `forEach`.

Operations that explicitly do **not** care about encounter order: **`findAny()`** (5.1.20) is defined to return *any* element, and on a parallel stream will typically return whichever partition's result finishes first, not "the first" in any traversal sense; a plain `forEach` on a parallel stream is explicitly permitted to run out of order for throughput.

**Interview:** Encounter order is the sequential-traversal order of an ordered source; `findFirst`, `limit`, `skip`, and `forEachOrdered` all respect it (at a cost, in parallel), while `findAny` and plain parallel `forEach` are explicitly free to ignore it for speed.

---

### 5.1.20 "Difference between `findFirst` and `findAny`?"

`findFirst()` always returns the first element in **encounter order** if the stream has one, and is fully deterministic on an ordered source regardless of sequential or parallel execution — running the same parallel stream a thousand times against the same ordered source always returns the same element, because the implementation is required to respect encounter order even when it has to do extra coordination across parallel chunks to determine which chunk's element is truly first.

`findAny()` returns **some** element satisfying the pipeline, with **no ordering guarantee whatsoever** — on a sequential stream it happens to behave identically to `findFirst` in most implementations (nothing else to pick from except in traversal order), but on a **parallel** stream it is explicitly permitted, and in practice does, return whichever partition's matching element becomes available first, which can vary run to run and is not required to be the first in encounter order.

The entire reason both methods exist is performance under parallelism: `findFirst` on a parallel stream over an ordered source has to pay a coordination cost to guarantee "the first one, provably" — other partitions that finish earlier with a matching element still have to wait and check whether an earlier partition also found one. `findAny` drops that guarantee specifically so a parallel pipeline can return the instant *any* partition finds a match, without waiting to confirm no earlier partition also matched.

```java
Optional<Reservation> firstOverStake = reservations.parallelStream()
    .filter(r -> r.stakeAmount().compareTo(Money.of(50)) > 0)
    .findFirst();   // deterministic: always the earliest-in-list qualifying reservation

Optional<Reservation> anyOverStake = reservations.parallelStream()
    .filter(r -> r.stakeAmount().compareTo(Money.of(50)) > 0)
    .findAny();     // whichever partition finishes first — may differ between runs
```

**Pitfall:** Using `findAny()` on a sequential stream and assuming that's proof it always returns the "actual first" element — it happens to on today's sequential implementation, but the contract makes no such promise, and switching that same pipeline to `.parallelStream()` later can silently change observed behaviour without a compile error. **Fix:** if determinism matters, always call `findFirst()`, never `findAny()`, regardless of whether the stream happens to be sequential today.

**Interview:** `findFirst` guarantees the first element in encounter order even on a parallel stream, at a coordination cost; `findAny` makes no ordering promise at all, which is exactly what lets a parallel stream return as soon as any partition finds a match, without waiting to rule out an earlier one.

---

### 5.1.21 "What does `allMatch` return on an empty stream?"

**`true`** — and this is not an arbitrary choice, it falls straight out of formal logic and the definition of `allMatch` in terms of universal quantification. `allMatch(predicate)` is defined as "no element fails the predicate" (equivalently: there is no counterexample), and over an empty domain there is, trivially, no counterexample to find, so the statement "every element satisfies the predicate" is vacuously true — this is the same reasoning that makes a universally-quantified statement over the empty set true in mathematical logic generally, not a Java-specific quirk.

Its two siblings follow the same logic to consistent, symmetric conclusions:

| Method | Empty-stream result | Why |
|---|---|---|
| `allMatch(p)` | `true` | Vacuously true — no element exists to violate `p` |
| `anyMatch(p)` | `false` | There's no element for which `p` could hold |
| `noneMatch(p)` | `true` | Vacuously true — no element exists to violate "none satisfy `p`" |

`[PROVE]`:

```java
List<Reservation> empty = List.of();

empty.stream().allMatch(r -> r.stakeAmount().compareTo(Money.ZERO) > 0);  // true
empty.stream().anyMatch(r -> r.stakeAmount().compareTo(Money.ZERO) > 0);  // false
empty.stream().noneMatch(r -> r.stakeAmount().compareTo(Money.ZERO) > 0); // true
```

`[TRAP]` — this is a genuinely dangerous one in real code, not a trivia fact: a validation gate written as `if (openReservations.stream().allMatch(Reservation::isWithinLimit)) proceed();` will silently proceed when `openReservations` is empty, because "all zero reservations are within limit" is vacuously true. If the intended business rule is "there must be at least one reservation, and all of them must be within limit," the `allMatch` check alone does not express that — you need an explicit `!openReservations.isEmpty() &&` guard, or restructure the check entirely, because the emptiness case is exactly where the vacuous-truth logic silently diverges from the everyday English reading of "all."

**Pitfall:** Treating `allMatch` as "there's at least one element and every one of them passes," when it actually means "there is no element that fails" — the empty case is where that distinction bites. **Fix:** explicitly guard for emptiness when the business rule genuinely requires at least one element to exist.

**Interview:** `allMatch` and `noneMatch` both return `true` on an empty stream, and `anyMatch` returns `false` — all three follow the standard vacuous-truth rule for universal statements over an empty domain, and it's a real bug source whenever "all pass" was meant to imply "at least one exists."

---

### 5.1.22 "`map` vs `flatMap` vs `mapMulti`."

All three transform a stream's elements, but they differ in **cardinality** — how many output elements one input element can produce — and in the mechanism used to flatten multiple outputs into the single downstream stream.

`map(Function<T,R>)` is strictly **one-to-one**: each input element produces exactly one output element (which may be `null`, though downstream operations rarely like that), no more, no fewer. It cannot express "this reservation expands into its three constituent ledger movements."

`flatMap(Function<T, Stream<R>>)` is **one-to-many**, by requiring each input element to itself produce a whole `Stream<R>`, which the operation then **concatenates** into the single downstream sequence, discarding the per-element stream boundaries. This is the right tool when you already have (or can cheaply construct) a nested `Stream`/`Collection`/`Optional`-as-stream per element:

```java
List<Movement> allMovements = reservations.stream()
    .flatMap(r -> r.constituentMovements().stream())  // Reservation -> Stream<Movement>
    .toList();
```

Mechanically, `flatMap` allocates one inner `Stream` object per outer element (via the `Function`'s return value) purely to hand it to the flattening machinery, then discards it — real, if usually small, allocation overhead per element, which is exactly what `mapMulti` was added in **Java 16** to avoid.

`mapMulti(BiConsumer<T, Consumer<R>>)` is also **one-to-many**, but instead of requiring you to construct an intermediate `Stream` object per element, it hands your lambda a `Consumer<R>` callback to invoke **zero, one, or many times** directly, with no intermediate stream ever allocated:

```java
List<Movement> allMovements = reservations.stream()
    .<Movement>mapMulti((reservation, sink) -> {
        for (Movement m : reservation.constituentMovements()) sink.accept(m);
    })
    .toList();
```

`mapMulti` is documented as the better choice when the expected number of outputs per input is small (zero, one, or a handful), because it avoids allocating a stream/collection wrapper purely to satisfy `flatMap`'s signature; `flatMap` remains the clearer, more idiomatic choice when you already naturally have a `Stream`/`Collection` in hand (e.g. calling an existing method that returns `List<Movement>`) rather than needing to imperatively push elements one at a time.

| | Cardinality | Needs a `Stream`/`Collection` per element | Added |
|---|---|---|---|
| `map` | 1 → 1 | No | Java 8 |
| `flatMap` | 1 → many | Yes — you return one | Java 8 |
| `mapMulti` | 1 → many (0 included) | No — you push via callback | Java 16 |

**Interview:** `map` is one-to-one; `flatMap` is one-to-many by requiring you to hand back a whole `Stream` per element, which it then concatenates; `mapMulti`, added in Java 16, achieves the same one-to-many shape without allocating an intermediate stream, by giving your lambda a callback to push zero-to-many results directly.

---

### 5.1.23 "`takeWhile` vs `filter`."

Both accept a `Predicate<T>`, but they answer fundamentally different questions and behave completely differently once the predicate first fails. `filter` tests **every** element against the predicate independently and keeps every one that passes, regardless of position — a `false` result for one element has zero effect on any other element. `takeWhile` (Java 9+) tests elements **in encounter order and stops the entire stream the instant the predicate first returns false**, discarding that element and every element after it, even ones that would themselves satisfy the predicate.

```java
List<Reservation> byRecency = List.of(r_settled1, r_settled2, r_open3, r_settled4);

// filter: keeps every SETTLED reservation, regardless of position
List<Reservation> allSettled = byRecency.stream()
    .filter(r -> r.status() == ReservationStatus.SETTLED)
    .toList(); // [r_settled1, r_settled2, r_settled4] — r_settled4 included

// takeWhile: stops the instant it hits the first non-SETTLED element
List<Reservation> leadingSettled = byRecency.stream()
    .takeWhile(r -> r.status() == ReservationStatus.SETTLED)
    .toList(); // [r_settled1, r_settled2] — stops at r_open3, never even looks at r_settled4
```

This makes `takeWhile` a genuine **short-circuiting** operation, unlike `filter`, which must always visit every source element (absent a downstream short-circuit like `findFirst`). On an **infinite** stream, this distinction is the difference between "works" and "hangs forever": `Stream.iterate(1, i -> i + 1).filter(i -> i < 100).toList()` never terminates, because `filter` alone gives the stream no reason to stop pulling — every element after 100 simply fails the predicate and gets dropped, forever. `Stream.iterate(1, i -> i + 1).takeWhile(i -> i < 100).toList()` terminates immediately after 99, because `takeWhile` itself is the short-circuit signal.

`dropWhile` is `takeWhile`'s mirror: it **discards** elements while the predicate holds, then, from the first failure onward, **keeps everything else unconditionally**, including elements that would individually satisfy the original predicate again later — the opposite failure mode from `filter` in the other direction.

**Pitfall:** Reaching for `filter` to "get the leading run while some condition holds" on an infinite or very large stream. **Fix:** `takeWhile` is both semantically correct for that specific question and the only one of the two that terminates on an unbounded source.

**Interview:** `filter` independently tests every element and never stops early; `takeWhile` tests in encounter order and stops the whole pipeline at the first failure, which is exactly what makes it usable — and `filter` unusable — for truncating an infinite stream.

---

### 5.1.24 "How would you batch a stream into windows of 100 on Java 21?"

There's no `Stream.window(n)` in the standard library through Java 21, so the honest answer names the real options and their tradeoffs rather than pretending one exists.

**Option 1 — `Collectors.groupingBy` keyed on integer-divided index**, the most idiomatic pure-streams approach when you can index the source (works cleanly when the source is a `List`, not a lazily-generated stream):

```java
List<Reservation> allSettlements = /* 2,800,000 stake settlements, per Appendix A's daily figure */;
int batchSize = 100;

Map<Integer, List<Reservation>> batched = IntStream.range(0, allSettlements.size())
    .boxed()
    .collect(Collectors.groupingBy(
        i -> i / batchSize,
        Collectors.mapping(allSettlements::get, Collectors.toList())));
// batched.get(0) -> elements 0..99, batched.get(1) -> elements 100..199, ...
```

The gotcha with this one: `groupingBy` returns a `HashMap` by default, so the batches come back **with no guaranteed iteration order** by key — you must sort by key afterward (`new TreeMap<>(batched)`, or stream `.sorted(Map.Entry.comparingByKey())`) if batch order matters, which for a payment-run-style "process settlements in order" requirement it usually does.

**Option 2 — a manual stateful `Collector`** using an `AtomicInteger` (or a plain mutable counter box, since a `Collector`'s accumulator runs single-threaded per container even in parallel use — see 5.1.31) to assign a window index per element, avoiding the `List.get` random-access requirement of Option 1 and working over any `Iterable`-backed source:

```java
static <T> Collector<T, ?, Map<Integer, List<T>>> windowed(int size) {
    AtomicInteger counter = new AtomicInteger();
    return Collectors.groupingBy(t -> counter.getAndIncrement() / size);
}

Map<Integer, List<Reservation>> batched = allSettlements.stream().collect(windowed(100));
```

`[TRAP]`: this specific `Collector` is only safe on a **sequential** stream — `counter.getAndIncrement()` assigning a *position* only means "window index" if elements are consumed in a single, ordered sequence; running it via `.parallelStream()` still produces correct atomicity per increment, but the resulting window membership no longer corresponds to encounter-order chunks of exactly 100, because parallel accumulation interleaves across worker threads.

**Option 3 — since Java 21 introduces no windowing method, but a hand-rolled `Spliterator` or `Stream.iterate` over a chunked `Iterator` is the "closest to library-grade" answer** for a truly infinite or very large source you can't afford to fully materialize: wrap the source `Iterator` in a small stateful iterator that pulls up to 100 elements at a time into a `List` and emits that `List` as one stream element, then build a `Stream` from that iterator via `Spliterators.spliteratorUnknownSize` + `StreamSupport.stream`. This is genuinely more code, and worth naming as "the option you'd actually reach for on a >100M-row batch, over the `groupingBy` approaches, because it never materializes the full source."

**Interview:** No standard `window(n)` exists through Java 21 — group by `index / batchSize` via `Collectors.groupingBy` when you have random access, or thread an `AtomicInteger` through a custom `Collector` when you don't, remembering that `groupingBy`'s `HashMap` result needs re-sorting by key if batch order matters.

---

### 5.1.25 "How would you zip two streams?"

Also no standard `Stream.zip` through Java 21 (it existed briefly as `Stream.zip` in a pre-release JDK 8 lambda build and was removed before GA specifically because pairing two streams cleanly conflicts with parallel decomposition — each side may split differently, making index alignment expensive to guarantee in parallel). The idiomatic approach today goes through an **indexed `IntStream`** over one side, using the other side's random access:

```java
List<Reservation> reservations = /* size N */;
List<Money> settlementAmounts = /* also size N, same order */;

record ReservationSettlement(Reservation reservation, Money amount) {}

List<ReservationSettlement> zipped = IntStream.range(0, reservations.size())
    .mapToObj(i -> new ReservationSettlement(reservations.get(i), settlementAmounts.get(i)))
    .toList();
```

This requires both sides be **sized and randomly accessible** (both `List`s, matched length) — it fails outright, or silently truncates/throws `IndexOutOfBoundsException`, if the two sources have different lengths or if either is a lazily-generated, non-indexable stream.

When one or both sides are **not** random-access — two `Iterator`s, or a stream produced from an I/O source — the mechanism has to shift to a shared `Iterator`-driven approach, most cleanly via a small custom `Spliterator` that advances both underlying iterators in lockstep and stops at whichever exhausts first:

```java
static <A, B, C> Stream<C> zip(Stream<A> as, Stream<B> bs, BiFunction<A, B, C> combiner) {
    Iterator<A> ai = as.iterator();
    Iterator<B> bi = bs.iterator();
    Iterable<C> iterable = () -> new Iterator<>() {
        @Override public boolean hasNext() { return ai.hasNext() && bi.hasNext(); }
        @Override public C next() { return combiner.apply(ai.next(), bi.next()); }
    };
    return StreamSupport.stream(iterable.spliterator(), false);
}

Stream<ReservationSettlement> zipped =
    zip(reservations.stream(), settlementAmounts.stream(), ReservationSettlement::new);
```

`[TRAP]`: this hand-rolled `zip` produces a **sequential-only, ordered, non-splittable** stream (the `Spliterator` from `iterable.spliterator()` with no characteristics declared has none of the useful ones set), so calling `.parallel()` on the result buys nothing — both `Iterator.next()` calls have to happen in strict lockstep on one thread regardless, and there is no library-level shortcut around that, because pairing elements across two independently-partitioned parallel sources is exactly the coordination problem that got the original `Stream.zip` removed before Java 8 shipped.

**Interview:** No standard `zip` exists — with two same-length `List`s, index through an `IntStream.range` and `get` both sides; with genuine iterators or unsized sources, hand-roll a `Spliterator` that advances both in lockstep, accepting that the result is sequential-only because lockstep pairing can't be split for parallelism.

---

### 5.1.26 "`collect(toList())` vs `stream.toList()` — name three differences."

| Aspect | `collect(Collectors.toList())` | `stream.toList()` (Java 16+) |
|---|---|---|
| Mutability of the result | **Unspecified by the `Collectors.toList()` javadoc** — in practice returns a mutable `ArrayList`, but the contract never promises this, so relying on mutability is relying on an implementation detail | **Guaranteed immutable** — the javadoc explicitly documents an unmodifiable list; calling `.add()` on the result throws `UnsupportedOperationException` |
| Nullability of elements | Allows `null` elements in the resulting list, because `ArrayList` permits `null` | **Disallows `null` elements outright** — if the stream contains a `null`, `.toList()` throws `NullPointerException` during collection, not lazily on later access |
| Verbosity / ceremony | Requires importing `java.util.stream.Collectors` and writing the full `collect(Collectors.toList())` call | A direct terminal method on `Stream`, no `Collectors` import, shorter to write and read |
| (bonus) Serializability/thread-safety of the returned type | Whatever `ArrayList` provides (not thread-safe, standard `Serializable`) | The specific immutable-list implementation backing `.toList()`'s result is unspecified beyond "unmodifiable" — don't depend on its concrete class |

`[PROVE]` the mutability and null differences:

```java
List<String> viaCollectors = Stream.of("AA-610", "AA-611").collect(Collectors.toList());
viaCollectors.add("AA-650"); // succeeds today — ArrayList underneath, but not contractually guaranteed

List<String> viaToList = Stream.of("AA-610", "AA-611").toList();
viaToList.add("AA-650"); // throws UnsupportedOperationException

Stream.of("AA-610", null).collect(Collectors.toList()); // succeeds, list contains a null
Stream.of("AA-610", null).toList(); // throws NullPointerException
```

**Pitfall:** Swapping `collect(Collectors.toList())` for `.toList()` as a pure refactor-for-brevity, without checking whether the calling code later mutates the returned list or whether the stream can legitimately contain `null` (e.g. a `map` that intentionally returns `null` for an unmapped status code). **Fix:** treat the swap as a genuine behaviour change to review, not a no-op rename.

**Interview:** `.toList()` is shorter, guarantees an immutable result, and throws on any `null` element; `Collectors.toList()` happens to return a mutable `ArrayList` today but never promises it, and tolerates `null`.

---

### 5.1.27 "What does `Collectors.toMap` do on a duplicate key? On a null value?"

**On a duplicate key: `toMap`'s two-argument and three-argument-without-merge forms throw `IllegalStateException` at the point the duplicate is encountered.** The two-argument form `toMap(keyMapper, valueMapper)` has no way to decide which of two colliding values should win, so it refuses to guess:

```java
Map<RestrictionType, RestrictionKey> byType = restrictions.stream()
    .collect(Collectors.toMap(RestrictionKey::type, Function.identity()));
// throws IllegalStateException: Duplicate key STAKE_BLOCKED
// (fires exactly when two restrictions share a type, e.g. STAKE_BLOCKED from SYSTEM_ONBOARDING
//  and STAKE_BLOCKED from ADMIN — recall from the domain that identity is (type, source), not
//  type alone, which is exactly why grouping only by type is the wrong key choice here)
```

The **three-argument overload** `toMap(keyMapper, valueMapper, mergeFunction)` exists specifically to resolve this — the `BinaryOperator<V>` merge function receives the existing and incoming values and decides the survivor:

```java
Map<RestrictionType, RestrictionKey> byType = restrictions.stream()
    .collect(Collectors.toMap(
        RestrictionKey::type,
        Function.identity(),
        (existing, incoming) -> existing)); // keep first — or throw explicitly if collision must be an error
```

**On a null value: `toMap` throws `NullPointerException`, unconditionally, regardless of the merge function's presence** — the backing map (`HashMap` by default) can technically store a `null` value, but `Collectors.toMap`'s internal accumulator explicitly calls `Objects.requireNonNull` on the mapped value before insertion (this has been the documented behaviour since Java 8; it is **not** a version trap — it has never permitted null values). This bites hardest with a lookup-style `valueMapper` that can legitimately return `null` for a miss:

```java
Map<ClientId, Money> latestDepositByClient = deposits.stream()
    .collect(Collectors.toMap(
        Deposit::clientId,
        d -> priceLookup.currentFxRate(d.currency()))); // returns null for an unsupported currency
// throws NullPointerException the moment any deposit's currency has no FX rate
```

The fix for a genuinely-nullable value is to wrap it — collect into `Optional<Money>` values, or pre-filter deposits whose FX rate lookup would return `null`, or fall back to a sentinel `Money` value that's meaningful in the domain (never a bare `null`) before collecting.

| Situation | Two-arg `toMap` | Three-arg `toMap` (with merge function) |
|---|---|---|
| Duplicate key | `IllegalStateException` | Merge function decides the survivor |
| `null` value from `valueMapper` | `NullPointerException` | `NullPointerException` — merge function does not help, because the value is rejected before the merge function is ever consulted |

**Pitfall:** Assuming a `BinaryOperator` merge function is also the escape hatch for `null` values. **Fix:** it isn't — `toMap` rejects `null` at value-mapping time, before any duplicate-key logic even runs; guard the `valueMapper` itself.

**Interview:** Two-argument `toMap` throws `IllegalStateException` on a duplicate key because it has no policy for picking a winner, and throws `NullPointerException` on any `null` mapped value regardless of whether a merge function is supplied — the merge function only ever resolves collisions, never nulls.

---

### 5.1.28 "What map and list types does `groupingBy` return?"

By default, `Collectors.groupingBy(classifier)` returns a **`HashMap<K, List<V>>`**, with the downstream `List` for each group built by the default downstream collector, `Collectors.toList()` — and per 5.1.26, that inner list's concrete mutability is unspecified in practice but currently an `ArrayList`. Neither the outer map's iteration order nor the inner list's implementation type is part of `groupingBy`'s documented contract when using the one- or two-argument forms — only "a `Map`" and "a `List`" are promised, so code that depends on `LinkedHashMap`-style insertion order from plain `groupingBy` is depending on an accident, not a guarantee.

Both the map type and the downstream collection type are fully overridable via the **three-argument and four-argument overloads**:

```java
// three-argument: classifier + map factory + downstream collector
Map<RestrictionType, Set<RestrictionKey>> byTypeAsSet = restrictions.stream()
    .collect(Collectors.groupingBy(
        RestrictionKey::type,
        Collectors.toSet()));  // downstream collector changes List -> Set

// four-argument (groupingBy's true general form): classifier + map factory + downstream collector
Map<RestrictionType, Set<RestrictionKey>> orderedByType = restrictions.stream()
    .collect(Collectors.groupingBy(
        RestrictionKey::type,
        TreeMap::new,             // map factory — sorted by RestrictionType's natural order
        Collectors.toCollection(LinkedHashSet::new)));  // downstream — insertion-ordered set
```

`groupingByConcurrent` is the parallel-friendly sibling — it returns a `ConcurrentHashMap` (or whatever concurrent map factory you supply) and is safe to use as the collector for a `parallelStream()` without the merge overhead ordinary `groupingBy` incurs under parallelism (ordinary `groupingBy` on a parallel stream still works, but does so by having each parallel partition build its own `HashMap` and then merging maps together at combine time — real allocation and merge cost that `groupingByConcurrent`'s single shared concurrent map avoids, at the cost of losing any encounter-order guarantee entirely).

| Overload | Map type | Downstream collection |
|---|---|---|
| `groupingBy(classifier)` | `HashMap` (unspecified formally) | `List` via `toList()` |
| `groupingBy(classifier, downstream)` | `HashMap` (unspecified formally) | Whatever `downstream` produces |
| `groupingBy(classifier, mapFactory, downstream)` | Exactly the supplied factory | Whatever `downstream` produces |
| `groupingByConcurrent(...)` | `ConcurrentHashMap` (or supplied factory) | Whatever `downstream` produces |

**Interview:** Plain `groupingBy` gives a `HashMap` of `ArrayList`s with neither type contractually guaranteed — the four-argument overload lets you name the exact map factory and downstream collector, and `groupingByConcurrent` swaps in a `ConcurrentHashMap` specifically to avoid the per-partition-merge cost ordinary `groupingBy` pays under a parallel stream.

---

### 5.1.29 "`groupingBy(p)` vs `partitioningBy(p)` — what is different about the empty case?"

`partitioningBy(Predicate)` always returns a `Map<Boolean, List<T>>` with **exactly two keys, `true` and `false`, both always present**, even if one side is empty — because a `Predicate` partitions the universe into exactly those two buckets, and `partitioningBy`'s implementation (backed by a dedicated `Partition` class, not a general `Map`) is built to always materialize both:

```java
Map<Boolean, List<Reservation>> byOverStakeLimit = List.<Reservation>of().stream()
    .collect(Collectors.partitioningBy(r -> r.stakeAmount().compareTo(Money.of(100)) > 0));
// {false=[], true=[]} — both keys present, both lists empty, on an EMPTY source stream
```

`groupingBy(Function)` returns a `Map<K, List<T>>` where **only keys that actually occurred in the source appear at all** — an empty source stream, or a source where a particular classifier value simply never showed up, produces **no entry** for that key, not an entry mapped to an empty list:

```java
Map<RestrictionType, List<RestrictionKey>> byType = List.<RestrictionKey>of().stream()
    .collect(Collectors.groupingBy(RestrictionKey::type));
// {} — completely empty map; RestrictionType.STAKE_BLOCKED never appears as a key at all
```

This difference is a direct consequence of how many possible "keys" each collector's domain has: `partitioningBy` has a fixed, known universe of exactly two possible outcomes (`Boolean` has exactly two values), so it can and does pre-populate both unconditionally; `groupingBy`'s classifier function can return arbitrarily many distinct values, so pre-populating "every possible key" is neither knowable nor desirable — it only ever creates an entry when it has actually seen at least one element that classifies to that key.

`[TRAP]` — downstream code that does `partitionedMap.get(false).isEmpty()` to mean "nothing failed the predicate" is safe and correct; the equivalent `groupedMap.get(SomeType.X) == null` check for groupingBy is the one people get wrong, writing `.get(X).size()` and hitting a `NullPointerException` when key `X` never occurred, instead of `.getOrDefault(X, List.of()).size()`.

**Interview:** `partitioningBy` always yields both `true` and `false` keys, even with empty lists, because a `Predicate` has a fixed two-value universe; `groupingBy` only ever creates an entry for a classifier value it actually saw, so a missing group is a missing key entirely, not an empty list — which is exactly where an unguarded `.get(key)` NPEs.

---

### 5.1.30 "Write a collector that gives the top 3 by salary per department."

Recast into the domain: **top 3 stake reservations by stake amount, per client.** The idiomatic Java 21 approach composes two standard collectors — `groupingBy` for the per-client bucketing, with a downstream `Collectors.collectingAndThen` wrapping a bounded `PriorityQueue`-backed accumulation, or more simply (and this is the answer most interviewers actually want to see you reach for first) `groupingBy` plus a downstream that sorts and truncates:

```java
Map<ClientId, List<Reservation>> top3ByClient = reservations.stream()
    .collect(Collectors.groupingBy(
        Reservation::clientId,
        Collectors.collectingAndThen(
            Collectors.toList(),
            list -> list.stream()
                .sorted(Comparator.comparing(Reservation::stakeAmount).reversed())
                .limit(3)
                .toList())));
```

This is correct and readable, but it materializes **every** reservation per client before truncating — for a client with thousands of reservations, that's a full sort of the whole group just to keep three. The genuinely top-K-aware version keeps a bounded structure the whole way through, which is what you'd escalate to if asked "how do you avoid the full sort":

```java
static <T> Collector<T, ?, List<T>> topN(int n, Comparator<T> comparator) {
    return Collector.of(
        () -> new PriorityQueue<>(n, comparator),                 // supplier — min-heap by the ranking key
        (heap, item) -> {                                         // accumulator
            if (heap.size() < n) {
                heap.offer(item);
            } else if (comparator.compare(item, heap.peek()) > 0) {
                heap.poll();
                heap.offer(item);
            }
        },
        (heapA, heapB) -> {                                       // combiner — merge two partial heaps
            heapB.forEach(item -> {
                if (heapA.size() < n) heapA.offer(item);
                else if (comparator.compare(item, heapA.peek()) > 0) { heapA.poll(); heapA.offer(item); }
            });
            return heapA;
        },
        heap -> heap.stream()
            .sorted(comparator.reversed())
            .toList(),                                            // finisher — order descending for output
        Collector.Characteristics.UNORDERED);

}

Map<ClientId, List<Reservation>> top3ByClient = reservations.stream()
    .collect(Collectors.groupingBy(
        Reservation::clientId,
        topN(3, Comparator.comparing(Reservation::stakeAmount))));
```

Here the heap is a **min-heap of size at most 3** — the smallest of the current top-3 sits at the root, so testing a new candidate against `heap.peek()` and evicting it when beaten is the classic bounded-top-K pattern, giving O(log 3) per element instead of an O(m log m) full sort per group of size `m`.

**Interview:** Compose `groupingBy` for the per-key bucketing with a downstream `collectingAndThen(toList(), sort-then-limit)` for a quick, readable answer — and if pushed on efficiency, escalate to a custom `Collector.of(...)` backed by a bounded min-heap so no group's full list is ever sorted just to keep the top 3.

---

### 5.1.31 "Explain the `Collector` contract's five functions."

`Collector<T, A, R>` — `T` the stream's element type, `A` the mutable accumulation type, `R` the final result type — is defined by exactly five components, all visible on `Collector.of(...)`'s five-argument overload:

1. **`Supplier<A> supplier()`** — creates a **new, empty accumulation container**. Called once per accumulation "unit" — once for a sequential stream, once per parallel partition for a parallel stream — never reused across independent accumulations, which is exactly why the container it returns can be freely mutable without any external synchronization.

2. **`BiConsumer<A, T> accumulator()`** — folds **one element** into the accumulation container, mutating it in place (this is why `A` is typically a mutable type — `ArrayList`, `StringBuilder`, the `PriorityQueue` from 5.1.30 — rather than an immutable one, since building an immutable result element-by-element via full replacement would be O(n²)). Called once per element that reaches this collector.

3. **`BinaryOperator<A> combiner()`** — merges **two** partial accumulation containers into one, and is the piece that exists purely to support **parallel** streams: each parallel partition accumulates its own container independently and in isolation (no shared mutable state, no locking needed inside `accumulator`), then the framework repeatedly calls `combiner` pairwise to fold all the partial containers down to a single one. On a sequential stream, `combiner` is **never called at all** — there's only ever one accumulation container.

4. **`Function<A, R> finisher()`** — transforms the fully-merged accumulation container into the final result type `R`. When `A` and `R` are the same type and no transformation is needed (`Collectors.toList()`'s `A` and `R` are both effectively `List<T>`), the collector declares `Characteristics.IDENTITY_FINISH` and the framework skips calling `finisher` entirely, using the accumulator as the result directly — `Collector.of`'s four-argument overload (no finisher) exists specifically for this case.

5. **`Set<Characteristics> characteristics()`** — a small set of optimization hints, not behavioural requirements: `CONCURRENT` (the accumulator can be safely called from multiple threads on the *same* shared container, letting the stream skip the whole per-partition-then-combine dance and mutate one shared container directly — only safe if the container is genuinely thread-safe, e.g. a `ConcurrentHashMap`), `UNORDERED` (the collector doesn't care what order elements arrive in — lets the stream skip encounter-order-preserving coordination under parallelism), and `IDENTITY_FINISH` (as above).

`Collectors.toMap`'s implementation makes this concrete: `supplier` returns a new `HashMap`, `accumulator` does `map.merge(keyMapper.apply(t), valueMapper.apply(t), mergeFunction)` (or throws per 5.1.27's no-merge-function path), `combiner` merges two `HashMap`s entry by entry through the same merge logic, and — since `A` and `R` are both `Map<K,V>` — it's `IDENTITY_FINISH`, no separate finisher needed.

**Interview:** `supplier` makes an empty mutable container, `accumulator` folds one element in, `combiner` merges two partial containers (used only under parallelism), `finisher` converts the container to the final result (skipped entirely when `IDENTITY_FINISH` is declared), and `characteristics` are hints — `CONCURRENT`, `UNORDERED`, `IDENTITY_FINISH` — that let the stream implementation skip work it doesn't need.

---

### 5.1.32 "When is `reduce` wrong and `collect` right?"

The dividing line is whether the accumulation type is **immutable** (functional fold — `reduce` is right) or **mutable** (imperative-style build-up — `collect` is right), and the reasoning traces straight back to `combiner` cost in 5.1.31.

`reduce`'s accumulation function `BinaryOperator<T> reduce(T identity, BinaryOperator<T> accumulator)` must return a **new value** on every single element — there is no in-place mutation option in `reduce`'s contract, because `T` is not assumed mutable. Folding a running total of `Money` with `reduce(Money.ZERO, Money::add)` is exactly right, because `Money::add` naturally returns a new `Money` rather than mutating one, so each step is O(1) with no wasted allocation beyond what the domain type itself requires.

Building up a `List` with `reduce` is the canonical wrong tool, precisely because a `List` is mutable and `reduce`'s model has no slot for in-place mutation of a shared container — the only way to "grow a list" through `reduce`'s pure-function contract is to allocate a **new** list on every single element:

```java
// WRONG — O(n^2) allocation, and a genuine misuse of reduce's contract
List<Money> stakeAmounts = reservations.stream()
    .reduce(List.<Money>of(),
        (list, r) -> { // must return a NEW list every time — no legal in-place option
            List<Money> next = new ArrayList<>(list);
            next.add(r.stakeAmount());
            return next;
        },
        (a, b) -> { List<Money> merged = new ArrayList<>(a); merged.addAll(b); return merged; });
```

Every single element forces a full copy of everything accumulated so far — this is the concrete O(n²) cost that motivates the rule, not an abstract style preference. `collect` exists precisely for this shape: its `accumulator` mutates one shared (or per-partition) container in place, so growing a list is O(1) amortized per element, exactly `ArrayList.add`'s cost:

```java
// RIGHT
List<Money> stakeAmounts = reservations.stream()
    .collect(Collectors.mapping(Reservation::stakeAmount, Collectors.toList()));
```

The general rule, stated the way an interviewer wants to hear it: **use `reduce` when combining two values of an immutable type produces a new value of that same type at low, fixed cost per step (numeric sums, `Money` totals, string concatenation via `StringBuilder` is the one common exception that's actually mutable underneath); use `collect` whenever the natural accumulator is a mutable container being built up incrementally (`List`, `Map`, `StringBuilder`, a custom running aggregate) — because `collect`'s three-part supplier/accumulator/combiner contract is explicitly designed to let that container mutate in place instead of forcing a fresh copy per element.**

A secondary, related reason `reduce` is sometimes wrong even for a nominally-immutable result type: `reduce` provides no separate `finisher` step (5.1.31's fourth function) — if you need to transform the fully-combined value into a different final shape, `collect`'s `finisher` gives you that hook natively, while `reduce`'s result has to be post-processed as a separate statement.

**Interview:** `reduce` is right for combining immutable values where each step naturally produces a new value at fixed cost — sums, totals; `collect` is right whenever the natural accumulator is a mutable container being built incrementally, because forcing that shape through `reduce` means allocating a full copy of the container on every single element, an O(n²) trap that `collect`'s in-place accumulator was built to avoid.

---

## Pitfalls

### Assuming a lambda is sugar for `new AnonymousClass() { ... }`

**Wrong**

```java
Comparator<Reservation> byStake = (a, b) -> a.stakeAmount().compareTo(b.stakeAmount());
// mental model: "this desugars to an anonymous Comparator class, so 'this' inside
// would refer to the comparator instance, same as an anonymous class"
```

**Right**

```java
public class SettlementReportBuilder {
    private final String reportName = "daily-settlement";

    Comparator<Reservation> byStakeNamingSelf() {
        return (a, b) -> {
            // 'this' here is the SettlementReportBuilder instance, not the Comparator —
            // because the lambda body compiles to a private method ON SettlementReportBuilder
            System.out.println(this.reportName + ": comparing stakes");
            return a.stakeAmount().compareTo(b.stakeAmount());
        };
    }
}
```

**Why people believe it:** the source-level syntax for both — replacing `new Comparator<...>() { public int compare(...) { ... } }` with a lambda — looks like a pure textual substitution, and most tutorials show the two as interchangeable "shorthand," never mentioning that `this` binding, class-file generation, and instantiation timing all diverge underneath.

### Reusing a stream reference across two terminal operations

**Wrong**

```java
Stream<Reservation> openOnes = reservations.stream()
    .filter(r -> r.status() == ReservationStatus.OPEN);

long total = openOnes.count();
List<Reservation> list = openOnes.toList(); // IllegalStateException: stream has already been operated upon or closed
```

**Right**

```java
List<Reservation> openOnes = reservations.stream()
    .filter(r -> r.status() == ReservationStatus.OPEN)
    .toList(); // materialize ONCE into a real collection

long total = openOnes.size();
List<Reservation> list = openOnes; // reuse the LIST as many times as needed, not a Stream
```

**Why people believe it:** a `Stream` looks and feels like a `Collection` reference you can hold onto and query multiple times — nothing about the type name or the fluent API syntax signals "this reference dies after one terminal call," and the exception only surfaces the second time you try, often in a different part of the code from where the mistake was made.

### Trusting `groupingBy(...).get(key)` the same way you'd trust `partitioningBy(...).get(key)`

**Wrong**

```java
Map<RestrictionType, List<RestrictionKey>> byType =
    restrictions.stream().collect(Collectors.groupingBy(RestrictionKey::type));

int selfExcludedCount = byType.get(RestrictionType.SELF_EXCLUDED).size();
// NullPointerException if not a single restriction in this batch happens to be SELF_EXCLUDED
```

**Right**

```java
int selfExcludedCount = byType.getOrDefault(RestrictionType.SELF_EXCLUDED, List.of()).size();
```

**Why people believe it:** `partitioningBy` genuinely does guarantee both keys are always present, and many engineers learn the two collectors as an interchangeable pair ("groupingBy but with a boolean"), carrying the always-present-keys assumption across to `groupingBy`, where it's false.

---

## Cheat sheet

| Question shape | One-line answer |
|---|---|
| Functional interface rule | Exactly one abstract method; `Object`-overriding and `default`/`static` methods don't count |
| Lambda vs anonymous class | `invokedynamic` + `LambdaMetafactory`, no class file, lexical `this` — vs. a real compiled class with its own `this` |
| Lambda `this` | The enclosing instance — lambda body is a synthetic method on the enclosing class |
| Effectively-final capture | Copy taken at creation time; reassignment would break the copy-vs-original guarantee and thread visibility |
| Non-capturing lambda identity | Usually the same cached instance per call site — never guaranteed |
| Bound method reference | Receiver evaluated once, at reference-creation time — not re-evaluated per call |
| Checked exception in `map` | Catch-and-wrap into unchecked, or declare your own throwing functional interface |
| Stream vs collection | Collection stores; stream describes a one-shot lazy computation over a source |
| Laziness mechanism | Intermediate ops build linked stages only; terminal op's `wrapSink` (backwards) + `copyInto` do all the work |
| Stage-by-stage or element-by-element | Element by element — each element cascades through the whole sink chain before the next starts |
| Stream reuse | `IllegalStateException: stream has already been operated upon or closed` — `linkedOrConsumed` flag |
| `peek` reliability | Only sees elements that reach that point; short-circuits, `sorted()`, and Java 9+ `count()` can all starve or skip it |
| Stateful ops | `sorted`, `distinct`, `limit`, `skip` — need more than the current element, break pure streaming, cost more in parallel |
| `findFirst` vs `findAny` | `findFirst` respects encounter order always; `findAny` makes no ordering promise, faster in parallel |
| `allMatch`/`noneMatch` on empty | Both `true` — vacuous truth; `anyMatch` is `false` |
| `map`/`flatMap`/`mapMulti` | 1→1 / 1→many via returned `Stream` / 1→many via callback, no intermediate stream |
| `takeWhile` vs `filter` | `takeWhile` short-circuits at first failure (works on infinite streams); `filter` never stops early |
| Batching / zipping | No standard library method through Java 21 for either — index-based or hand-rolled `Spliterator` |
| `toList()` vs `Collectors.toList()` | `.toList()` is immutable and null-hostile; `Collectors.toList()` is mutable (unspecified) and null-tolerant |
| `toMap` duplicate key / null value | Duplicate key throws unless a merge function is supplied; `null` value always throws, merge function or not |
| `groupingBy` defaults | `HashMap<K, List<V>>`, both unspecified formally — override with the 3-/4-arg forms |
| `groupingBy` vs `partitioningBy` empty case | `partitioningBy` always has both `true`/`false` keys; `groupingBy` omits keys never seen |
| `Collector`'s five parts | supplier, accumulator, combiner (parallel only), finisher (skipped if `IDENTITY_FINISH`), characteristics |
| `reduce` vs `collect` | `reduce` for immutable low-cost combination; `collect` for mutable container build-up (avoids O(n²)) |

---

## Self-test

**Q1.** A teammate adds a `default int priority()` method to a `@FunctionalInterface`-annotated interface that already has one abstract method. Does the build still compile, and why?

<details><summary>Answer</summary>

Yes. `default` methods never count toward the single-abstract-method total the compiler enforces for a functional interface — `@FunctionalInterface` only asserts "exactly one *abstract* method," and a `default` method has a body, so it isn't abstract at all. Existing lambdas targeting the interface are unaffected because they only ever needed to implement the one abstract method; the new `default` method simply becomes available (with its default body) on every lambda-backed instance too, since the JVM's generated implementation class inherits it like any other default method.

</details>

**Q2.** Why does `Stream.iterate(1, i -> i + 1).filter(i -> i % 7 == 0).findFirst()` terminate, while `Stream.iterate(1, i -> i + 1).sorted().findFirst()` never does?

<details><summary>Answer</summary>

`findFirst` is a short-circuiting terminal operation — it stops pulling from the source the instant one element makes it all the way through the sink chain. `filter` is stateless and streams elements one at a time, so as soon as the seventh multiple of 7 passes through, `findFirst`'s sink reports "done" and the whole pipeline stops; only finitely many elements from the infinite source were ever touched. `sorted()`, by contrast, is a stateful operation that must see the **entire** upstream sequence before it can produce even its first output element — it has to buffer everything and sort before emitting anything downstream at all. Against an infinite source, "see everything first" never completes, so `sorted()` blocks the pipeline forever before `findFirst` ever gets a chance to short-circuit anything.

</details>

**Q3.** A `Collector` built with `Collector.of(supplier, accumulator, combiner)` — three arguments, no finisher — is used inside `.collect(...)` on a **sequential** stream. Is `combiner` ever called?

<details><summary>Answer</summary>

No. `combiner` exists solely to merge independently-accumulated partial containers produced by different parallel partitions. A sequential stream never partitions its source, so there is only ever one accumulation container from start to finish — the framework has nothing to merge, and `combiner` is never invoked. It becomes reachable only when the same collector is used with `.parallelStream()` (or `.collect()` is invoked with parallel execution some other way), where each chunk builds its own container via `supplier`/`accumulator` and those containers get folded together pairwise via `combiner`.

</details>

**Q4.** `restrictions.stream().collect(Collectors.groupingBy(RestrictionKey::type)).get(RestrictionType.SELF_EXCLUDED)` returns `null` even though there are zero `SELF_EXCLUDED` restrictions in the batch — while `restrictions.stream().collect(Collectors.partitioningBy(r -> r.type() == RestrictionType.SELF_EXCLUDED)).get(true)` returns an empty list, never `null`, for the same batch. Why the difference?

<details><summary>Answer</summary>

`partitioningBy`'s classifier is a `Predicate`, whose codomain is fixed and exactly two-valued (`true`/`false`) — the collector's implementation is built around a dedicated `Partition` structure that always materializes both keys up front, empty or not, because there's no third possibility to worry about. `groupingBy`'s classifier is an arbitrary `Function<T,K>` whose codomain can be unbounded — the collector has no way to know every possible key value in advance (there could be a hundred `RestrictionType` values or a million distinct `String`s), so it only ever inserts a map entry the first time it actually observes an element that classifies to a given key. A key with zero matching elements never gets an entry at all, hence `.get()` returns `null` rather than an empty list.

</details>

**Q5.** Why does `Comparator<T>` count as a single-abstract-method interface even though its source declares both `compare` and `equals`?

<details><summary>Answer</summary>

The single-abstract-method rule (JLS §9.8) excludes any method whose signature is already provided as a public method by `Object` — `equals(Object)` is exactly such a method, since every class, including every lambda-generated implementation class, inherits a working `equals` from `Object` for free. `Comparator` redeclaring `equals` in its source is purely documentation of contract intent (clarifying when two comparators may be considered interchangeable); it adds no new obligation for an implementer. That leaves `compare(T, T)` as the only method a lambda actually has to supply, which is exactly one abstract method — the rule that excludes `Object`-overriding declarations is completely general, not specific to `Comparator`.

</details>

**Q6.** A `bound::methodReference` is created inside a loop, once per iteration, where `bound` is reassigned to a new object at the top of each iteration. Does each created reference see the object `bound` pointed to when the reference was created, or the object `bound` points to when the reference is later invoked?

<details><summary>Answer</summary>

The object `bound` pointed to **at reference-creation time**, for that specific iteration. A bound method reference evaluates its receiver expression immediately, once, at the point the reference expression executes, and captures the resulting object reference into the generated implementation instance — exactly like a lambda capturing an effectively-final local. Later reassignment of the `bound` variable in subsequent loop iterations has zero effect on references already created in earlier iterations; each one is permanently bound to whatever `bound` referred to at the moment that particular reference was constructed.

</details>

**Q7.** `Stream.of(1, 2, 3).peek(System.out::println).count()` — does this reliably print `1`, `2`, `3`? Under what condition might it print nothing at all?

<details><summary>Answer</summary>

Not reliably, and this is version-sensitive. Since Java 9, the JDK's `count()` implementation is explicitly permitted to skip traversing the stream — and therefore skip calling any intermediate operation, including `peek` — whenever the final size can be determined directly from the source's known size (via the `Spliterator`'s `SIZED` characteristic) without needing to actually visit each element, because no downstream operation in the pipeline changes the element count in a way that isn't already knowable up front. `Stream.of(1,2,3)` is a `SIZED` source and `peek` doesn't filter, so `count()` on Java 9+ is permitted — and in practice does — return `3` immediately without ever invoking the `peek` consumer, printing nothing. On Java 8, no such optimization existed, so this would reliably print all three lines. The takeaway: never rely on `peek` firing when the only downstream operation is `count()`.

</details>

**Q8.** Why is building a `List` with `Stream.reduce` an O(n²) mistake, while summing a `Money` total with `Stream.reduce` is not?

<details><summary>Answer</summary>

`reduce`'s accumulator contract has no slot for in-place mutation — each step must return a fresh combined value of the same type, not mutate a shared one. Combining two `Money` values via `Money::add` naturally produces a new `Money` at fixed, small cost regardless of how large the running total is — no dependency on how many elements have been folded so far, so the total cost across `n` elements is O(n). Building a `List`, by contrast, is inherently about accumulating into a mutable container; forced through `reduce`'s pure-value contract, the only legal way to "add one more element" is to allocate an entirely new list containing everything so far plus the new element, which costs O(k) at step `k` — summing that over `n` steps gives O(n²) total copying. `collect`'s accumulator, unlike `reduce`'s, is explicitly allowed and expected to mutate a shared container in place, making the same list-building operation O(n) overall.

</details>

**Q9.** What is the practical difference in behaviour between `findAny()` called on a sequential stream versus the same `findAny()` call on the equivalent parallel stream?

<details><summary>Answer</summary>

On a sequential stream, there is only one traversal path, so `findAny()` in practice behaves identically to `findFirst()` — the first (and only) element encountered that satisfies the predicate is what gets returned, because there's nothing else it could plausibly return first. On a parallel stream, the source is split into independent partitions processed concurrently, and `findAny()`'s contract explicitly permits returning whichever partition's matching element becomes available first — which partition wins that race can vary from run to run and has no required relationship to encounter order. This means code that happens to pass tests using `findAny()` sequentially can start returning a different, non-deterministic element the moment the same pipeline is switched to `.parallelStream()`, with no compiler warning to flag the change.

</details>

**Q10.** In the eight-beat mental model of stream evaluation, what specifically triggers `wrapSink` to run, and in which direction does it walk the pipeline?

<details><summary>Answer</summary>

`wrapSink` is triggered by a terminal operation's call to `evaluate(TerminalOp)`, which is the entry point that finally does real work after a chain of purely bookkeeping intermediate-operation calls. It walks the pipeline **backwards** — starting from the terminal stage and moving toward the source — because each stage's job is to wrap the *downstream* sink (the one closer to the terminal operation, already built) with its own logic and then forward to it; building the terminal's sink first and wrapping progressively earlier stages around it is the only order that lets each wrapping stage know what it needs to forward matching elements to. Once the full sink chain is assembled this way, `copyInto` runs in the opposite, forward direction — pulling elements from the source and pushing them through the now-complete sink chain from the source end toward the terminal end.

</details>

---

## Deferred

None.

---

**Leaves covered:** 5.1.1–5.1.32 (32 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 1198
