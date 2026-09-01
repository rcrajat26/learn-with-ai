# 04 Modern Java — Lambdas — INTERNALS (§3.2)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Lambdas — internals translation](03-internals-translation.md) · Next: [Method references — basics](../method-references/01-basics.md)

---

## Scope of this file

The previous file (03) walked the mechanics of `invokedynamic` and
`LambdaMetafactory`: a lambda expression compiles to a private synthetic method
plus a bootstrap call, and at first execution the JVM spins a hidden class that
implements the target functional interface, with one constructor parameter per
captured variable. This file picks up exactly where that leaves off: **what
capture does to program behaviour**, not how the bytecode gets there.

Two families of leaf sit in this file:

- **Capture semantics** (3.2.1–3.2.4): what "copied into a field" actually means
  for a primitive versus a reference, why the compiler enforces
  effectively-final, why reading a field captures `this` instead of the field,
  and the object-lifetime consequence of that — the listener-registry leak.
- **Identity, equality, and JIT behaviour** (3.2.5–3.2.10): what `==`, `equals`,
  `hashCode`, `toString`, and reflection actually see when pointed at a lambda
  instance, and how the JIT treats a lambda call site under mono- versus
  megamorphic dispatch.

Four primary concepts carry the eight-beat treatment:

1. Capture-by-value into a spun field, and why `this`-capture is different in
   kind from value-capture (3.2.1–3.2.3).
2. The listener-registry leak (3.2.4).
3. Lambda identity and why `==` is meaningless (3.2.5–3.2.6).
4. The JIT's treatment of monomorphic versus megamorphic lambda call sites
   (3.2.10).

3.2.7–3.2.9 (`equals`/`hashCode`, `toString`, reflection) are supporting facts:
each is a direct, low-drama consequence of "a lambda is an ordinary object of a
hidden class" — no sibling to weigh, no cost claim, no diagram. They get three
beats each.

---

## 1. Capture is by value, into a field of the spun instance

### Mental model first

Forget "the lambda captures the variable." A lambda captures **a snapshot**.
When the JVM spins the hidden class for a capturing lambda — the class file 03
showed you being materialised by `LambdaMetafactory.metafactory` — every
variable the lambda body reads from its enclosing scope becomes a
**constructor parameter of that hidden class**, and the constructor's only job
is to copy each parameter into a same-named `private final` field. The lambda
body, translated to the synthetic instance method, then reads `this.thatField`
instead of the original local. From the moment the hidden instance is
constructed, it has its own copy. The enclosing frame can disappear — the
method can return, the stack can unwind — and the lambda's copy is untouched,
because it was never a reference to the frame slot. It is a value baked into a
field at construction time, the same as any other constructor argument.

### Why it exists

Java's locals live on the stack (or in registers), one frame per method
invocation. A lambda that escapes its enclosing method — returned, stored in a
field, handed to another thread — outlives the frame that declared the
variables it uses. Without a copy, "capturing a local" would mean holding a
pointer into a stack frame that has already been popped, which is exactly the
class of bug C and C++ programmers know as capturing a stack address after
the function returns. Java's designers avoided the whole class of dangling-
reference bug by making the copy mandatory and by refusing to let you write
code where the copy could visibly diverge from the original (that refusal is
effectively-final, covered next). Anonymous inner classes solved the same
problem the same way fifteen years earlier — an anonymous class capturing a
local also gets a synthetic `final` field and a constructor parameter, visible
in `javap` output as a mangled field name. Lambdas did not invent copy-
capture; they inherited it, and `invokedynamic` just replaced the boilerplate
class file with one generated at first call.

### When to reach for it, and when not

This is not a knob you choose — every lambda that reads an enclosing local,
parameter, or effectively-final field-of-a-local captures by value, always. The
choice that exists is at the call site: if you need a value that changes over
time, do not try to capture a mutable local (the compiler will not let you);
instead capture a reference to a mutable **holder** — an `AtomicInteger`, a
single-element array, a small mutable record field on an object you do
capture — and mutate through the reference. That trades a compile error for a
concurrency hazard you now own, which is exactly why holders should be a last
resort and not a habit. The genuinely correct alternative in almost every
QuizStakes-shaped case is to pass the value as a **method parameter** into
whatever consumes the lambda, rather than capturing it from an enclosing
scope at all — capture is for values that are fixed for the life of the
lambda, not for threading state through it.

### How it works

Reusing the class file evidence from file 03: for a lambda expression
`x -> ledgerId + x`, where `ledgerId` is a captured local of type `String`,
`javac` does not touch `ledgerId`'s storage at all. It rewrites the lambda
body into a private synthetic instance method with `ledgerId` promoted to an
**extra leading parameter**:

```java
private static String lambda$reserveStake$3(String ledgerId, int x) {
    return ledgerId + x;
}
```

At the `invokedynamic` call site, the bootstrap arguments to
`LambdaMetafactory.metafactory` include this method handle, and the
**dynamic call site's argument list is exactly the set of captured
variables** — here, `ledgerId` — evaluated **at the point the lambda
expression is reached**, not at the point the lambda is later invoked. That
argument becomes the sole constructor parameter of the hidden class the
metafactory spins on first execution. The constructor body the JVM generates
is mechanical:

```java
// pseudocode for the hidden class the metafactory spins
final class LambdaImpl implements IntFunction<String> {
    private final String arg$0;               // one field per capture
    LambdaImpl(String arg$0) { this.arg$0 = arg$0; }
    public String apply(int x) {
        return LambdaHost.lambda$reserveStake$3(arg$0, x); // reads the field
    }
}
```

Every read of `ledgerId` inside the lambda body compiles, in the synthetic
method, to a read of the corresponding parameter — which, once the hidden
instance exists, is backed by that `private final` field. There is exactly one
assignment to the field, performed once, at construction. `[PROVE]` — walk a
concrete case: suppose `reserveStake` builds ten `Supplier<String>` lambdas in
a loop, one per stake in a batch, each closing over a **different** local
`String ledgerId` computed inside that loop iteration. Because each loop
iteration is a fresh declaration of `ledgerId` (even though it is textually
the same variable name, effectively-final applies per-execution of the
declaration, not per-name — file 03 covers this loop-capture distinction in
depth), each lambda gets its own hidden-class instance with its own field
value, and the ten suppliers, invoked later, return ten different strings. If
capture were by reference to a shared frame slot instead, all ten would
observe whatever `ledgerId` held at the moment of the last loop iteration —
the classic C-style closure-in-a-loop bug. Copy-capture is precisely the
mechanism that makes the ten-different-suppliers behaviour correct rather
than accidental.

**Insight:** "capture" is not a runtime relationship between the lambda and the
enclosing frame at all. It is a compile-time rewrite (extra parameter) plus a
one-time runtime copy (constructor call) that happens once, when the lambda
expression is evaluated. After that instant, the lambda and the enclosing
method share no storage.

### A minimal concrete example

```java
import java.math.BigDecimal;
import java.util.List;
import java.util.function.Function;

final class StakeReservationFactory {

    List<Function<BigDecimal, StakeSplit>> buildSplitters(List<String> roundIds) {
        return roundIds.stream()
                .map(roundId -> (Function<BigDecimal, StakeSplit>) stakeAmount ->
                        splitStake(roundId, stakeAmount))
                .toList();
    }

    // roundId is captured by value into each lambda's hidden-class field;
    // BONUS_RATE is a captured compile-time constant, inlined, not even a field.
    private static final BigDecimal BONUS_RATE = new BigDecimal("0.10");

    private StakeSplit splitStake(String roundId, BigDecimal stakeAmount) {
        BigDecimal bonusPortion = stakeAmount.multiply(BONUS_RATE)
                .setScale(2, java.math.RoundingMode.DOWN);
        BigDecimal cashPortion = stakeAmount.subtract(bonusPortion);
        System.out.println("round " + roundId + " split " + stakeAmount);
        return new StakeSplit(new Money(bonusPortion, java.util.Currency.getInstance("GBP")),
                               new Money(cashPortion, java.util.Currency.getInstance("GBP")));
    }
}

record Money(BigDecimal amount, java.util.Currency currency) {}
record StakeSplit(Money bonusPortion, Money cashPortion) {}
```

Each `Function<BigDecimal, StakeSplit>` produced by `buildSplitters` closes
over a **different** `roundId` — one per element of `roundIds` — because
`roundId` is the stream lambda's parameter, freshly bound on every
invocation of the outer `map` lambda. Ten round IDs produce ten splitter
lambdas, each permanently reporting its own round ID, because each got its
own copy at construction.

### The gotcha

The copy is shallow. If the captured variable is a **reference type**, the
field holds the same reference the local held — a copy of the pointer, not a
deep copy of the object. Mutating the referenced object's fields after
capture is visible inside the lambda, because the lambda's copy of the
reference still points at the same mutable object. This is not a contradiction
of "capture is by value" — the *reference* was captured by value, and
references are values. It is the source of a large fraction of "why did my
lambda see a stale/live value" confusion, and it is precisely the seam
3.2.2 and 3.2.3 dig into next.

> **Definition.** Capturing a local variable, parameter, or effectively-final
> field-of-a-local means the compiler promotes it to a constructor parameter
> of the lambda's hidden class, and the JVM copies its value — the primitive
> value, or the reference value for an object — into a `private final` field
> of the hidden instance exactly once, at the moment the lambda expression is
> evaluated.

---

## 2. Effectively-final: why the copy can never diverge

### Mental model first

Effectively-final is not a style preference the compiler nags you about. It is
the **proof obligation** that makes the copy in section 1 safe to make at all.
If the compiler let you write to a captured local after the lambda captured
it, there would be two live copies of "the same variable" — the frame's slot
and the lambda's field — and no rule for which one is authoritative when they
disagree. Effectively-final closes that question by construction: it never
arises, because there is only ever one value to copy.

### Why it exists

Anonymous inner classes had the identical rule from Java 1.1 onward — a local
captured by an anonymous class had to be declared `final`, full stop, no
"effectively" about it, because the compiler could not otherwise prove the
captured field-init snapshot matched every later read of the local. Java 8
relaxed the **syntax** — you no longer have to write the keyword `final` — but
kept the **semantics** exactly as strict: the compiler still requires that the
variable's value never change after initialization anywhere in its scope. It
computes this itself (hence "effectively" final rather than requiring the
annotation) and refuses to compile if it cannot prove it.

### When to reach for it, and when not

This is not optional and not a call you make — every captured local must
qualify, or the file does not compile. The decision surface is what you do
when you discover a local you want to capture is *not* effectively-final,
typically because a loop or conditional reassigns it. Three routes exist, in
order of preference: (1) introduce a new, genuinely-final local right before
the lambda, holding the "final" value you actually want captured — the
standard `final int captured = counter;` pattern; (2) restructure so the
value that varies becomes a parameter of the functional interface method
itself, rather than something you capture at all; (3) only as a last resort,
capture a mutable holder (`AtomicInteger`, a one-element array, a small
mutable object) and mutate through the reference — which sidesteps
effectively-final because the *reference* to the holder is what is captured,
and that reference genuinely never changes, even though the holder's
contents do. Route 3 reintroduces exactly the shared-mutable-state hazard
effectively-final exists to prevent, so it is correct only when you have
already reasoned about concurrent access to the holder.

### How it works

`[PROVE]` — work the compiler's actual test through. Effectively-final is
defined (JLS §4.12.4) as: a variable whose declaration has an initializer, or
which is assigned exactly once, and which is never subsequently used as the
target of a compound assignment (`+=`), an increment/decrement (`++`, `--`),
or as the left side of a plain assignment anywhere within its scope, from the
point of declaration to the end of that scope — including inside the lambda
body itself. The compiler is not asking "does the value happen to change" at
runtime; it is a **static, syntactic** check over every assignment site in the
scope, performed once at compile time, independent of which branch actually
executes.

```java
int retryBudget = 3;                      // one initializer, never reassigned
Runnable r = () -> System.out.println(retryBudget); // OK: effectively final

int attempts = 0;
Runnable bad = () -> {
    attempts++;                            // compile error, right here:
    System.out.println(attempts);          // "variable attempts is accessed
};                                          // from within a lambda expression;
attempts = attempts + 1;                   // needs to be final or effectively
                                            // final"
```

`[X-REF 03]` — file 03 covers the specific loop-capture case in full: a
`for (int i = 0; i < n; i++)` index is never effectively-final (the `i++` is
itself a reassignment inside its own scope), which is exactly why you cannot
capture a C-style loop counter directly and must go through an enhanced
`for`, a `.forEach`, or a fresh `final` local per iteration — see that file
for the bytecode-level walkthrough of why an enhanced-for's per-iteration
binding *is* effectively-final while the counter is not.

The proof this buys the compiler: because the variable is assigned exactly
once (as far as the static rule can see) before the lambda expression is
reached, the value copied into the hidden class's field at construction is
**provably** the same value every subsequent read of the local — if any
existed — would see, for the remainder of the scope. There is no runtime
check because none is needed; the syntactic restriction makes the divergence
this rule worries about — the copy going stale relative to a "live" original —
structurally impossible.

### The diagram

Not applicable to this concept in this file — D-130 belongs to §3, the
listener-registry leak, where the retained-object picture earns its keep. A
"final local, one field, one value" picture would be redundant with the class
diagram already in file 03.

### A minimal concrete example

```java
import java.util.List;
import java.util.function.Predicate;

final class StakeFilterFactory {

    // limitSet is effectively final: one parameter, never reassigned.
    Predicate<BigDecimalStake> underDailyLimit(LimitSet limitSet) {
        BigDecimal cap = limitSet.dailyDeposit();          // also effectively final
        return stake -> stake.amount().compareTo(cap) <= 0;
    }
}

record LimitSet(BigDecimal dailyDeposit, BigDecimal maxStake, BigDecimal monthlyLoss) {}
record BigDecimalStake(BigDecimal amount) {}
```

Both `limitSet` and `cap` are captured. Neither is reassigned anywhere in
`underDailyLimit`, so both qualify without the `final` keyword ever
appearing. Try adding `limitSet = null;` anywhere after the lambda and before
the method's end, and the file stops compiling with the same diagnostic shown
above — the point being that the check considers the **entire scope**, not
just the code that lexically precedes the lambda.

### The gotcha

Effectively-final governs the **local variable or parameter binding**, not
the object it refers to. A captured reference to a mutable object — a
`List<StakeReservation>` you keep calling `.add()` on after the lambda
captures it — is completely legal, because the *reference* never changes,
only the referent's contents. That is the seam the next concept, 3.2.3,
turns into a full trap: capturing `this` (always legal, `this` is never
reassignable) gives the lambda a live view onto every field of the enclosing
object, defeating any intuition that "the lambda only sees old values."

> **Definition.** A local variable or parameter is effectively final when it
> is assigned exactly once — by initializer or by a single subsequent
> assignment — and never reassigned or mutated via `++`/`--`/compound
> assignment anywhere in its scope; lambdas and anonymous classes may capture
> only variables meeting this test, because the compiler's guarantee that the
> captured copy can never diverge from "the" value depends on there being
> only one value to begin with.

---

## 3. Reading a field captures `this`, not the field

### Mental model first

There is a trap hiding in the word "field" that the previous two concepts
don't warn you about: `this.someField` inside a lambda body is **two** things
syntactically fused into one — a capture of `this`, followed by a normal
field read through that captured reference. The lambda does not, and cannot,
capture `someField`'s value directly, because instance fields are not local
variables and effectively-final is a rule about locals. What actually gets
promoted to a constructor parameter is `this` — the enclosing object — and
every apparent "field capture" is silently rewritten to a field read on that
captured object, performed **fresh, every time the lambda runs**.

### Why it exists

This isn't a deliberate design choice with an alternative that was rejected —
it falls straight out of how instance field access already worked before
lambdas existed. `someField` inside any instance method, lambda or not, has
always been sugar for `this.someField`; the compiler has bytecode for
`aload_0` (push `this`) followed by `getfield` at every unqualified field
reference in an instance context, lambda or otherwise. Lambdas didn't get a
special carve-out from that rule, and giving them one — synthesizing a
snapshot of the field's value at lambda-creation time instead — would have
been a much larger, much stranger special case: it would mean a lambda's view
of `this`'s state silently forks from the object's real state the moment the
lambda is created, which is the opposite of what an instance method closure
should mean.

### When to reach for it, and when not

You want `this`-capture, and should let it happen without fighting it, when
the lambda's job is to observe or act on the enclosing object's **current**
state at the time the lambda actually runs — a listener that should report
whatever the object looks like when the event fires, not what it looked like
when the listener was registered. You want to avoid it, and instead capture
an explicit **local snapshot** of just the field you need, when the lambda
will be stored and invoked much later or on another thread, and a stale-vs-
live distinction would be a correctness bug rather than the intended
behaviour — which is exactly the situation section 4's leak walks through.
The rule of thumb: if the lambda reads two or more fields off `this`, or
calls another instance method, you are almost certainly capturing `this` on
purpose (or by oversight) rather than picking one value; make the choice
explicit by naming a local.

### How it works

`[PROVE]` — trace what the compiler actually emits. Take an instance method
on `ProfileService` that reads its own field inside a lambda:

```java
final class ProfileService {
    private volatile RiskTier currentRiskTier;              // instance field

    Runnable buildRiskLogger(ClientId clientId) {
        return () -> System.out.println(clientId + " tier=" + currentRiskTier);
        //                                            ^^^^^^^^^^^^^^^^
        //                          sugar for: this.currentRiskTier
    }
}
enum RiskTier { STANDARD, ELEVATED, RESTRICTED }
record ClientId(java.util.UUID value) {}
```

`currentRiskTier` inside the lambda desugars, at parse time, to
`ProfileService.this.currentRiskTier` — a field read on the enclosing
instance. Because a field read is not a local-variable capture, the
compiler's synthetic method for this lambda does **not** take
`currentRiskTier`'s value as a parameter. It takes `this` — the
`ProfileService` instance — as its (only, in this example, since `clientId`
also needs capturing so really two) constructor parameter, and the lambda
body's translated method reads the field off that stored reference every time
it runs:

```java
// pseudocode for the spun hidden class
final class LambdaImpl implements Runnable {
    private final ProfileService outer;   // captured `this`, not the field
    private final ClientId clientId;      // captured local, by value
    LambdaImpl(ProfileService outer, ClientId clientId) {
        this.outer = outer; this.clientId = clientId;
    }
    public void run() {
        System.out.println(clientId + " tier=" + outer.currentRiskTier); // fresh read
    }
}
```

The consequence, stated as the leaf demands: because `outer.currentRiskTier`
is read fresh on every invocation of `run()`, any write to
`currentRiskTier` on the real `ProfileService` instance **after** the lambda
was created and **before** it runs is visible to the lambda. The lambda did
not see "the tier at capture time" — there is no such snapshot — it sees
whatever the field holds at call time, subject to the usual Java Memory
Model visibility rules for that field (here, `volatile`, so every reader sees
every writer's most recent write; without `volatile` or other synchronization
the visibility guarantee would be weaker, a concern that is guide 05's
territory in full).

**Insight:** the difference between 3.2.1's capture-by-value and this leaf is
not "sometimes Java copies and sometimes it doesn't." It always copies —
copying is what capture means. The difference is **what** gets copied: a
local's *value*, versus `this`'s *reference*. A reference copy, followed by a
field read through it, looks exactly like "the field changed underneath the
lambda" to someone who has only internalized "capture is by value" without
noticing that `this` is the thing actually captured.

### A minimal concrete example

```java
import java.util.function.Supplier;

final class ProfileService {
    private volatile RiskTier currentRiskTier = RiskTier.STANDARD;

    Supplier<String> statusReporter(ClientId clientId) {
        return () -> clientId + " currently " + currentRiskTier;
    }

    void escalate() {
        this.currentRiskTier = RiskTier.ELEVATED;
    }
}
```

```java
ProfileService profileService = new ProfileService();
Supplier<String> reporter = profileService.statusReporter(new ClientId(java.util.UUID.randomUUID()));
System.out.println(reporter.get());   // "... currently STANDARD"
profileService.escalate();
System.out.println(reporter.get());   // "... currently ELEVATED" — same lambda, later write is visible
```

The second call to `reporter.get()` proves the point on the page: nothing
about `reporter` changed between the two calls — no reassignment, no new
lambda — yet its output changed, because it never held a copy of the field;
it held (and always held) a reference to the object the field lives on.

### The gotcha

**Pitfall:** believing "capture is by value" extends to fields, then writing
a listener that is supposed to fire with the state *as of registration time*
and getting the state *as of firing time* instead. The wrong belief:
"the lambda took a snapshot of `currentRiskTier` when I registered it, so it
will always report STANDARD." The symptom: a stale-looking bug report where a
notification says ELEVATED for a client who was STANDARD when the
notification was supposedly queued. The fix: if you actually want the
value-at-registration-time, capture a **local** holding that value
explicitly — `RiskTier tierAtRegistration = currentRiskTier;` — before
building the lambda, and reference the local, not the field, inside it. That
local is effectively-final, gets copied by value under 3.2.1's rule, and now
genuinely is a snapshot.

> **Definition.** An unqualified instance field reference inside a lambda body
> is sugar for `this.field`; the lambda captures `this` (the enclosing
> instance, by reference, in the field-of-the-hidden-class sense of "capture")
> and re-reads the field through that reference on every invocation, so the
> lambda observes every write to the field made after the lambda was created,
> not a snapshot taken at creation time.

---

## 4. The listener-registry leak

### Mental model first

Picture a static registry — a `List` or `Map` living for the lifetime of the
JVM process — and a lambda handed to it that, per section 3, secretly holds a
reference to `this`. The registry does not know or care that it captured
`this`; it just sees "an object implementing `Runnable`" or whatever the
functional interface is. But the garbage collector's reachability trace does
not stop at "an object implementing `Runnable`" — it walks every field of
every reachable object, and the lambda's hidden field pointing back at the
enclosing instance is exactly as strong a reference as any other field. The
registry keeps the lambda alive forever (or until explicit removal); the
lambda keeps the enclosing object alive forever; the enclosing object's own
field graph — everything *it* points to — comes along for the ride. One
`registerListener(this::onSomething)` call, made once and never undone, can
pin down a client's entire aggregated profile view for the life of the
process.

### Why it exists

This is not a defect specific to lambdas — it is the identical failure mode
Java programmers have hit with anonymous inner classes since 1996, because an
anonymous class capturing an enclosing instance also holds a synthetic
`this$0` field, visible in `javap` output on any anonymous class compiled
from an instance context. What changed with lambdas is not the hazard but its
**visibility**: an anonymous class announces the capture syntactically —
`new Runnable() { ... }` sitting inside an instance method visibly nests
inside that method's `this` scope, and a careful reviewer can at least see
the anonymous class body and ask "does this touch an outer field?" A lambda
`() -> currentRiskTier` gives no visual cue that it is holding a whole
`ProfileService` hostage; the capture is implicit in a single identifier, and
the terseness that makes lambdas pleasant to write is exactly what hides the
leak from review. Static analysis and heap-dump review are the practical
defenses, not source-level vigilance alone.

### When to reach for it, and when not

There is no version of "reach for this leak" — the goal is always to avoid
it. The actual decision is which of three fixes to apply, and they trade off
differently: (1) capture only the specific field value you need into a local
before building the lambda, breaking the `this` reference entirely — cheapest,
and the right default whenever the lambda's logic only needs one or two
values; (2) if the lambda genuinely needs to call back into several methods
of the enclosing object, use a `WeakReference<ProfileService>` inside a
static nested holder so the registry's reference does not by itself keep the
object alive — more machinery, appropriate when the registration truly must
outlive uncertain unregistration; (3) make unregistration a first-class part
of the enclosing object's lifecycle contract — an explicit
`unregisterListener(this)`-shaped call in a `close()`/`shutdown()`/`@PreDestroy`
path — which is the standard fix in a Spring-managed bean's lifecycle and the
one guide 07 covers for bean destruction callbacks. Option 1 is preferred
whenever it is available at all, because it removes the leak by construction
rather than by remembering to clean it up.

### How it works

`[PROVE]` — trace reachability explicitly rather than asserting "it leaks."
Take the domain shape the packet specifies: a static `NotificationService`
holds a registry of listeners; a `ProfileService` instance registers a lambda
that reads one of its own fields.

```java
final class NotificationService {
    // static: lives for the process lifetime, GC-root reachable always
    private static final List<Runnable> listeners = new java.util.concurrent.CopyOnWriteArrayList<>();

    static void register(Runnable listener) { listeners.add(listener); }
    static void fireAll() { listeners.forEach(Runnable::run); }
}

final class ProfileService {
    private final ClientId clientId;
    private volatile RiskTier currentRiskTier;
    // a large aggregated view, per QuizStakes §7.3: assembled from up to eight owners
    private final List<AggregatedFieldSnapshot> aggregatedView;

    ProfileService(ClientId clientId, List<AggregatedFieldSnapshot> aggregatedView) {
        this.clientId = clientId;
        this.aggregatedView = aggregatedView;
        NotificationService.register(() -> logIfElevated());   // captures `this`
    }

    private void logIfElevated() {
        if (currentRiskTier == RiskTier.ELEVATED) {
            System.out.println(clientId + " is elevated, aggregated fields=" + aggregatedView.size());
        }
    }
}
record AggregatedFieldSnapshot(String owner, Object value) {}
```

Reachability, traced by hand: `NotificationService.listeners` is a `static`
field, so it is a GC root by definition — always reachable, for the whole
process. It holds a `Runnable` — the lambda instance. Per section 3, that
lambda's hidden class has a field holding `this` — the `ProfileService`
instance that called `register`. That `ProfileService` instance has a field
`aggregatedView`, a `List<AggregatedFieldSnapshot>` potentially holding, per
the domain's own description of `ProfileService` (§4/§7.3 of the scenario:
"aggregated client view assembled from many owners"), fields sourced from up
to eight different owning services — personal details, agreements, documents,
restrictions, balances. Every one of those objects is now reachable from a
GC root, transitively, through a chain that is four hops long:
`static field → lambda instance → captured this → aggregatedView list → every
element`. None of it is eligible for collection, ever, unless something calls
an explicit unregister — and `NotificationService.register` as written above
offers no such method.

The diagram makes the retained subgraph and its fix concrete.

![D-130 — A captured `this` keeps the enclosing object alive](../diagrams/D-130-captured-this-keeps-enclosing.svg)

**D-130** — A captured `this` keeps the enclosing object alive

The left half of D-130 is the leak as built above: the static
`NotificationService` registry, one arrow to the lambda instance, one arrow
labelled "captured `this`" from the lambda to the `ProfileService` instance,
and then the fan-out from `ProfileService` into its aggregated fields, with
the whole retained subgraph's bytes labelled as a single number — everything
past that `this` arrow is retained, not just the one field the lambda reads.
The right half is the fix: the same registration, but the lambda captures
only the one value it actually needs (a plain `ClientId`, or a
`RiskTier`-reporting local snapshot), with the reduced retained set drawn
beside it — the `ProfileService` instance and its aggregated fields are no
longer reachable through the registry at all, and can be collected as soon as
nothing else holds them.

**[NUM]** — sizing the leak, using the packet's fixed 8-core-box numbers where
they apply and the domain's own figures otherwise: QuizStakes runs 380k
monthly active clients (Appendix A). If even a fraction of `ProfileService`
instantiations register a `this`-capturing listener this way and the
registry is never drained, the registry's live set grows with every
distinct client who has ever triggered a `ProfileService` construction in
the process's lifetime, each retaining its full aggregated-view fan-out —
this is not bounded by *concurrent* sessions (14k steady, 55k peak) at all,
because the registry does not release entries when a session ends; it is
bounded only by however many `ProfileService` instances have ever been
constructed since the JVM started, which over the platform's lifetime is a
number that keeps climbing past the 2.4M registered-client count.

### A minimal concrete example

Already given above (the `NotificationService`/`ProfileService` pair) — this
concept's example and its proof share the same code, because the proof *is*
the example walked through by hand.

### The gotcha

**Pitfall:** assuming a `Runnable` or listener lambda is "just a function" and
therefore cheap to leave registered. The wrong belief: "it's a lambda, not a
whole object graph, so registering one costs nothing." The symptom: heap
growth that a profiler traces to a static collection field, whose entries'
retained size (not shallow size) is enormous, disproportionate to the small
number of bytes the lambda body itself would suggest. The fix: capture a
narrow, explicit local instead of relying on implicit `this`-capture, or add
an explicit unregister call tied to the enclosing object's own lifecycle
end. **Why people believe it:** the lambda's own syntax is a few characters —
`() -> logIfElevated()` — and nothing about reading it suggests it is
carrying an entire `ProfileService` instance and its eight-owner aggregated
view along for the ride; the cost is invisible at the call site and only
shows up in a heap dump.

> **Definition.** A lambda registered into a longer-lived structure that
> captures the enclosing instance's `this` — whether directly or via an
> unqualified instance-method or instance-field reference — keeps that entire
> instance, and everything reachable from its fields, alive for as long as
> the registry holds the lambda; this is the anonymous-inner-class listener
> leak, unchanged in mechanism by lambdas, only less visible in source.

---

## 5. Lambda identity: why `==` is meaningless

### Mental model first

A lambda expression is not a value with a defined identity the way `42` or
`"AA-610"` is (interned or not, at least deterministically comparable). It is
an **instruction to construct an object**, executed at a particular point in
the running program, and every fresh execution of that instruction is free to
hand back a different object. The specification's silence on identity is not
an oversight — it is a deliberate refusal to make a promise the implementation
would then be locked into forever. Treat every lambda expression as producing
"some object of some class implementing this interface, of no fixed identity
across evaluations," and every identity-based operation on it — `==`,
default `hashCode`, default `equals` — stops looking useful the moment you
say it that way.

### Why it exists

Before lambdas, the closest analogue was an anonymous inner class instance,
and nobody expected two `new Runnable() { ... }` expressions, even
textually identical ones, to produce `==`-equal objects — `new` obviously
allocates. The reason lambda identity became a question worth asking at all
is that lambdas are *not* always translated as "allocate a new object every
time," per file 03's translation walkthrough: for a **non-capturing** lambda,
`LambdaMetafactory` is free to cache the single hidden-class instance and
hand back the same object on every subsequent evaluation of that expression,
because a non-capturing lambda has no per-evaluation state to differ by. The
JDK's actual implementation does this as an optimisation. But the
specification never mandates it — it is JDK-implementation behavior, not a
guaranteed contract — precisely so a future JVM, or a different vendor's JDK,
remains free to allocate fresh every time without becoming spec-non-
compliant, or to change caching strategy across releases without breaking
anyone who didn't rely on identity.

### When to reach for it, and when not

There is no scenario where relying on lambda `==` or default-`equals`/
`hashCode` is the right tool, so this beat inverts: name what actually solves
the problems people reach for lambda identity to solve. Need to remove a
specific registered listener later? Keep an explicit handle — store the
lambda in a field or a `Map<SomeKey, Runnable>` keyed by something with real
identity, and remove by that key, not by re-supplying "the same" lambda
expression. Need to deduplicate a set of behaviours? Compare by an explicit
key you define (a `String` intent name, an `enum`), not by the lambda object.
Need to cache based on "have I seen this callback before?" Do not use a
lambda as the cache key at all; use a value type that actually has value
semantics.

### How it works

`[PROVE]` — the specification's actual silence, then the demonstration.
JLS §15.27.4 ("Run-Time Evaluation of Lambda Expressions") states that
evaluation of a lambda expression "may either create a new instance ... or
reuse a previously-created instance," and explicitly notes this determination
is made at the discretion of the implementation and may vary between
different lambda expressions, and even between different **executions** of
the same lambda expression. The JLS deliberately does **not** say "reuse
happens exactly when the lambda captures nothing" as a promise — it says
implementations may reuse or not, subject only to the constraint that a
freshly-created instance of a capturing lambda cannot be reused between
executions that would supply different captured values (a capturing lambda's
"identity" is meaningless in a stronger sense: even *within one run*, calling
the enclosing method twice with different captured values necessarily
produces two objects, because the constructor arguments differ).

`[SOURCE]` — the relevant clause, quoted:

> "It is unspecified whether or when lambda expressions are evaluated to the
> same or different instances of the associated functional interface. [...]
> Evaluation of a lambda expression is distinct from execution of the lambda
> body associated with the lambda expression. [...] The Java programming
> language does not require that different lambda expressions that happen to
> have the same body be represented by instances of the same class."

Reading each clause: "unspecified whether or when ... same or different
instances" is the identity guarantee's absence, stated as directly as a spec
can state a non-guarantee. "Evaluation of a lambda expression is distinct
from execution of the lambda body" separates *evaluating the expression*
(which produces an object — possibly a cached one) from *invoking the
functional method on that object later* — two different events at two
different times, and identity questions only make sense about the first.
"Does not require that different lambda expressions ... be represented by
instances of the same class" closes off an even weaker fallback hope —
you cannot even rely on two lambdas with textually identical bodies sharing
a hidden class, let alone an instance.

`[PROVE]` — demonstrate the observable consequence on this machine, `javac
--release 21`:

```java
import java.util.function.Supplier;

final class LambdaIdentityDemo {
    static Supplier<String> nonCapturing() {
        return () -> "AA-801";                    // reads no enclosing state
    }
    static Supplier<String> capturing(String statusCode) {
        return () -> statusCode;                  // captures statusCode
    }
    public static void main(String[] args) {
        System.out.println(nonCapturing() == nonCapturing());
        System.out.println(capturing("AA-801") == capturing("AA-801"));
    }
}
```

```
$ javac --release 21 LambdaIdentityDemo.java && java LambdaIdentityDemo
true
false
```

The first line prints `true` on this JDK build because the non-capturing
lambda's hidden-class instance is cached by `LambdaMetafactory` and handed
back on both calls — **this JDK's current behaviour**, not a specification
promise. The second prints `false` because each call to `capturing` supplies
a fresh constructor argument, so a fresh instance is unavoidable regardless
of caching policy. **[VERSION-TRAP]** — do not present line one's `true` as
guaranteed across JDK releases or vendors; treat it as "true today, on this
build, because of an optimisation the spec explicitly declines to promise,"
which is the entire point of quoting the JLS clause above alongside the demo
rather than instead of it.

### The gotcha

**Pitfall:** writing test assertions or production logic of the shape
`assertSame(supplier1, supplier2)` or `if (registeredLambda == candidate)`
and having it pass in a unit test (small program, likely cached
non-capturing case) and then fail unpredictably in production once the
lambda captures something, or once a JIT tier change or a different JDK
build changes caching behaviour. **Why people believe it:** the demo above
really does print `true` for the non-capturing case on the JDK most engineers
run locally, so a quick manual check "confirms" identity stability, and
nobody re-runs the check after changing the lambda body to capture a value.

> **Definition.** Whether two evaluations of the same lambda expression
> produce the same object is unspecified by the JLS and left to
> implementation discretion; a non-capturing lambda is commonly (not
> guaranteedly) represented by a single cached instance on current OpenJDK
> builds, while a capturing lambda's evaluations are, by construction,
> distinct objects whenever the captured values differ.

---

## 6. `==` on lambdas is meaningless, and `removeListener(x -> ...)` never removes anything

### Mental model first

This concept is section 5's direct, practical fallout, given its own eight
beats because it is the shape almost every engineer actually meets the
identity question in: calling a `removeListener` (or `unsubscribe`,
`removeCallback`, `deregister`) method with a freshly-written lambda
expression, expecting it to cancel a previously-registered one, and watching
it silently do nothing.

### Why it exists

The registration/deregistration pattern is copied wholesale from
`ActionListener`/`PropertyChangeListener`-era Swing and AWT APIs, where the
convention "call `removeListener` with an object `==` to what you added"
already worked, because those callers typically kept an explicit reference to
the anonymous-class or named-class instance they had registered, precisely
because writing that instance was already a multi-line affair that
encouraged holding a variable. Lambdas make registering a listener a single
inline expression, which invites writing the *removal* call the same
inline way — `registry.removeListener(evt -> handle(evt))` — without
noticing that this expression is a **different lambda expression** from the
one passed to `addListener`, evaluated at a different point in the program,
with no promise of producing an `==`-equal object even if the two expressions
are character-for-character identical.

### When to reach for it, and when not

Never reach for `==`-based removal with an inline lambda. The only working
pattern is: keep an explicit reference to the exact object handed to
`addListener` — store it in a local or a field — and pass that same
reference, not a freshly-written lambda expression, to `removeListener`.

```java
Runnable listener = () -> System.out.println("fired");
registry.addListener(listener);
// ... later ...
registry.removeListener(listener);   // same object reference: works
```

versus the broken version that motivated this leaf:

```java
registry.addListener(() -> System.out.println("fired"));
// ... later ...
registry.removeListener(() -> System.out.println("fired")); // different object: no-op
```

### How it works

`[PROVE]` — this follows directly from section 5's demonstrated `false` for
capturing lambdas, and from the fact that even the "commonly cached"
non-capturing case is implementation behaviour, not a contract: a
`removeListener` implementation that does `list.remove(candidate)` relies on
`List.remove(Object)`, which by contract calls `.equals()` on each element —
and per the next leaf (3.2.7), a lambda's `equals` is `Object`'s, i.e.
reference identity. So `removeListener(freshLambda)` only ever succeeds if
`freshLambda == theOriginallyRegisteredInstance`, and per section 5 there is
no specification path that guarantees that for two textually-identical but
separately-evaluated lambda expressions — and for anything capturing state,
it is provably `false`, not merely unspecified.

### The diagram

Not applicable as a separate diagram — this leaf is the direct behavioural
consequence of D-130's identity story and section 5's proof; a second
picture would repeat the same object-identity idea with a different label
rather than teach anything new.

### A minimal concrete example

```java
import java.util.List;
import java.util.function.Consumer;

final class RestrictionChangeNotifier {
    private final List<Consumer<RestrictionKey>> listeners = new java.util.ArrayList<>();

    void addListener(Consumer<RestrictionKey> listener) { listeners.add(listener); }
    boolean removeListener(Consumer<RestrictionKey> listener) { return listeners.remove(listener); }
    void fire(RestrictionKey key) { listeners.forEach(l -> l.accept(key)); }
}
record RestrictionKey(String type, String source) {}
```

```java
RestrictionChangeNotifier notifier = new RestrictionChangeNotifier();
notifier.addListener(key -> System.out.println("restriction changed: " + key));
boolean removed = notifier.removeListener(key -> System.out.println("restriction changed: " + key));
System.out.println("removed=" + removed);   // removed=false, always, on any JDK
```

`removed` prints `false` unconditionally — not flakily, not "usually" — because
the two `Consumer<RestrictionKey>` expressions are separate lambda
expressions evaluated at two different call sites, and `List.remove` finds no
element `.equals()` (⇒ `==`, per the next leaf) to the second one.

### The gotcha

**Pitfall:** shipping a `removeListener` call that silently no-ops, discovered
only when a listener that was "removed" months ago keeps firing — which is
also, notably, a second and independent path into section 4's leak, since a
listener nobody can successfully remove behaves exactly like one nobody ever
tried to remove. The wrong belief: "I wrote the exact same lambda, so
removing it should cancel the one I added." The fix: retain the reference
from registration, as shown above, and treat `removeListener(lambda ->
...)` written inline as a compile-time-legal but always-broken pattern to
flag in review.

> **Definition.** Because a lambda's `equals` is identity-based (next leaf)
> and its identity across separate evaluations is unspecified or provably
> distinct (this and the previous leaf), a `removeListener`/`unsubscribe`
> call passed a freshly-written lambda expression — rather than a retained
> reference to the exact object originally registered — never successfully
> removes anything, on any JDK, by any specified guarantee.

---

## 7. `equals` and `hashCode` on a lambda are `Object`'s

**Mechanism.** `LambdaMetafactory` does not generate an `equals` or
`hashCode` override for the hidden class it spins — the hidden class extends
nothing but implements only the target functional interface (plus,
optionally, `Serializable` and marker interfaces if the call site's
`invokedynamic` bootstrap requested them), and inherits `Object.equals` and
`Object.hashCode` untouched. `Object.equals` is `this == other`;
`Object.hashCode` is (in the OpenJDK HotSpot implementation) derived from the
object's identity, not its content.

**Gotcha.** Putting lambdas into a `HashSet` or as `HashMap` keys with the
expectation of "same behaviour, dedupe" produces a set that grows without
bound — every distinct evaluation is a distinct key, hash-and-equals both
say so, and there is no override anywhere in the chain to change that. This
directly reuses the machinery just proven in sections 5 and 6: dedup by
`equals` fails for exactly the same reason `removeListener` fails.

> **Definition.** A lambda instance's `equals` and `hashCode` are the
> unmodified `Object` implementations — identity comparison and an
> identity-derived hash — because `LambdaMetafactory` generates no override
> for either.

---

## 8. `toString()` on a lambda is useless in a log

**Mechanism.** `Object.toString()`'s default form is
`getClass().getName() + "@" + Integer.toHexString(hashCode())`. For a lambda's
hidden class, `getClass().getName()` is a synthesized name of the shape
`EnclosingClass$$Lambda/0x00000008000c0440`, or similar — the exact hex
payload is a VM-internal identifier (in current HotSpot builds it encodes an
internal object/class table offset, not anything a caller should parse) that
changes between runs and between class loads of the same program. Printed
whole, a typical value looks like
`ProfileService$$Lambda/0x00007f6e8c0a1130@1b6d3586`.

**Pitfall:** logging a lambda directly — `log.info("handler={}", handler)` —
expecting to see which behaviour it represents, and getting a string that
carries zero information about intent and is not even stable across JVM
restarts for correlating log lines. The fix is to log the **intent**, not the
object: pass a `String` describing what the lambda does alongside it, or
wrap listener registration in a small named record/class that carries a
human-readable label and delegates to the lambda, and log that wrapper.

> **Definition.** A lambda's `toString()` is `Object`'s default form applied
> to a JVM-synthesized hidden-class name and an identity hash, carrying no
> information about the lambda's captured state or behaviour, and unstable
> across runs — never log it as a substitute for a human-readable description
> of intent.

---

## 9. Reflection on a lambda: interfaces are visible, the implementing method is not where you expect, and the source form cannot be recovered

**Mechanism.** `someLambda.getClass().getInterfaces()` does return the
functional interface(s) the lambda was constructed against — that part of
the object's shape is genuinely inspectable, because the hidden class really
does `implements` that interface, the same as any other object. What does
**not** work the way reflection on an ordinary class works: the method body a
reader would expect to find — the actual lambda logic — does not live as a
method *on* the hidden class in any form a `Class.getDeclaredMethods()` call
usefully surfaces as "the lambda's code"; the hidden class's functional
method typically just forwards (via a `private static synthetic` method
handle bound at spin-time) to the **synthetic method on the enclosing class**
that file 03 showed `javac` generating from the lambda body
(`lambda$methodName$N`), and that synthetic method is intentionally not part
of any supported public reflective contract — its name, its existence, and
its signature are compiler-generated implementation detail, not API.
`[RESEARCH]` — there is no supported JDK API, as of the jdk-21+35 tag, that
recovers a lambda's original source text or a stable, documented handle to
"the method this lambda calls"; `LambdaMetafactory`, `MethodHandles`, and the
serialized-lambda machinery (`SerializedLambda`, reachable only if the
functional interface extends `Serializable`) expose *some* internal detail —
`SerializedLambda` in particular does surface the implementation class and
method name via `writeReplace` — but that mechanism exists to support
lambda **serialization**, is explicitly documented as unstable across
compiler versions, and is not a general-purpose "decompile this lambda" tool.

**Gotcha.** Debuggers and profilers that walk a stack trace through a lambda
call show the synthetic method name (`lambda$reserveStake$3`) and the hidden
class's synthesized name, not a name a reader chose — which is why a stack
trace through a deeply nested stream pipeline of lambdas is one of the
least readable artifacts in ordinary Java debugging, and why extracting
non-trivial lambda bodies into named private methods (referenced via method
reference) is a debugging-friendliness argument independent of any
performance concern.

> **Definition.** Reflection on a lambda instance exposes the functional
> interface(s) it implements, but not a stable, documented path to its
> original source, its enclosing synthetic method, or a decompiled body —
> that information is compiler- and JVM-internal and unsupported for
> reflective recovery.

---

## 10. The JIT and the lambda call site: monomorphic inlines, megamorphic deoptimises

### Mental model first

Every call through a functional interface reference —
`someFunction.apply(x)` — is, from the JIT's point of view, exactly the same
kind of call as any interface method call: a virtual dispatch that has to
find the right implementation at the call site. HotSpot's inline caches
handle this the same way for lambdas as for any other interface call: the
call site remembers what concrete type it last dispatched to, and if it keeps
seeing the same type, the JIT eventually **inlines** the target method
directly into the caller, erasing the dispatch entirely. If the call site
instead sees a rotating cast of different concrete types, the cache cannot
commit to one target, dispatch falls back to a full virtual call every time,
and any inlining decisions already made get **thrown away** (deoptimised).

### Why it exists

Inline caching predates lambdas by decades — it is the mechanism that makes
polymorphic OOP call sites in HotSpot fast in the common case, where a given
call site in practice almost always calls the same concrete type even though
the static type is an interface. Lambdas did not get a special JIT path; they
ride the exact same call-site profiling machinery every other interface call
uses, because a lambda instance genuinely *is* an ordinary object implementing
an ordinary interface, and the JIT has no separate notion of "lambda call"
distinct from "interface call." What is specific to lambda-heavy code is
merely that it is very easy to accidentally create *many distinct concrete
types* backing what looks, in source, like "the same kind of call" — every
distinct lambda expression in the source is a distinct class, so a method
that accepts a `Function<...>` parameter and gets called from ten call sites
passing ten different lambda expressions is, from HotSpot's point of view,
being called with ten different concrete implementing types.

### When to reach for it, and when not

This is not a knob to tune directly — you cannot tell the JIT "please stay
monomorphic here." What you *can* control is the **shape** of the call site:
keep a hot call site fed a small, stable set of concrete lambda types (ideally
one) if it is on a genuinely hot path, and accept megamorphic dispatch
without worrying about it on cold or infrequently-executed paths, where the
inlining decision was never going to matter to overall throughput. Reach for
this concern specifically when profiling (not guessing) shows a hot loop
built around a `Function`/`Predicate`/`Consumer` parameter that receives
different lambda expressions across iterations or calls — the classic shape
is a generic "apply this stream of strategies" dispatcher where the strategy
varies per call. The escape hatch when it matters is to reduce to a bounded,
small `sealed`-style set of concrete strategies (real classes or a fixed
palette of lambdas assigned to `static final` fields, so the same instances
recur) rather than constructing a fresh lambda per call.

### How it works

`[PROVE]`/`[X-REF 06]` — the mechanism, at the depth this file owns, then a
pointer to guide 06 for the full inline-cache internals. HotSpot's inline
cache at a call site starts **monomorphic-optimistic**: the very first
resolution records the concrete receiver type and patches the call site to a
direct, guarded call — a type check followed by a direct jump, which the JIT
can then further inline (copy the callee's bytecode into the caller) once
the method is hot enough to compile. If a second, different concrete type
ever reaches that call site, HotSpot's cache widens: first to
**bimorphic** (two cached targets, one extra branch), and beyond two
distinct types it gives up on caching by type entirely and falls back to a
**megamorphic** dispatch — a full virtual table lookup on every call, with no
inlining, and no residual guard to *un*inline if the mix later narrows back
down; a call site that has gone megamorphic does not spontaneously recover
monomorphic status on its own within the same compilation, and if the JIT had
already speculatively inlined a formerly-monomorphic target, discovering the
second type at runtime triggers a **deoptimization** — the compiled code is
discarded, execution falls back to the interpreter for that method, and
recompilation (if it happens again) starts the profiling process over.

For a lambda-heavy pipeline specifically, the failure mode the leaf names is
common in stream code: a `Stream<StakeReservation>.map(fn)` inside a shared
utility method, called from many call sites in the codebase each supplying
its own distinct lambda expression for `fn`, but all funneled through **one**
compiled copy of the utility method (because Java does not monomorphize
generics or specialize per call site the way, say, Rust's generics do) — that
one shared compiled method's internal call to `fn.apply(...)` sees every
distinct lambda type that ever reaches it, and if the shared method is hot
enough to matter, it can go megamorphic and stay there, silently costing
throughput with no exception, no log line, and no visible symptom besides a
profiler showing time in `itable`/`vtable` stub code at that call site.
`[X-REF 06]` — the inline-cache state machine (monomorphic → bimorphic →
megamorphic), C2's deoptimization bookkeeping, and how to read a JIT log
(`-XX:+PrintInlining`) for these transitions belong to guide 06's JVM
internals territory in full; this file gives enough to recognise and reason
about the symptom, not to read a compilation log end to end.

### The diagram

Not applicable as a separate diagram in this file — the inline-cache state
machine is guide 06's diagram to own; reproducing it here would duplicate a
sibling's chapter, which the `[X-REF 06]` contract explicitly forbids.

### A minimal concrete example

```java
import java.util.List;
import java.util.function.Function;
import java.math.BigDecimal;

final class SettlementPipeline {

    // one shared, potentially hot call site inside a widely-reused utility
    static BigDecimal applyAdjustment(BigDecimal stakeAmount, Function<BigDecimal, BigDecimal> adjustment) {
        return adjustment.apply(stakeAmount);   // dispatch site under discussion
    }

    // call site A: always the same lambda expression -> monomorphic-friendly
    static BigDecimal settleAtFace(BigDecimal stakeAmount) {
        return applyAdjustment(stakeAmount, amount -> amount);
    }

    // call site B, C, D...: distinct lambda expressions reaching the same
    // shared applyAdjustment call site -> pushes it toward megamorphic
    static BigDecimal settleWithHouseFee(BigDecimal stakeAmount, BigDecimal feeRate) {
        return applyAdjustment(stakeAmount, amount -> amount.multiply(BigDecimal.ONE.subtract(feeRate)));
    }

    static BigDecimal settleWithChargebackReversal(BigDecimal stakeAmount, BigDecimal reversedAmount) {
        return applyAdjustment(stakeAmount, amount -> amount.subtract(reversedAmount));
    }
}
```

If `applyAdjustment` is called from many more such call sites across a large
codebase, each supplying its own distinct `Function<BigDecimal, BigDecimal>`
lambda expression, the single compiled `applyAdjustment` method's
`adjustment.apply(stakeAmount)` call site is the one place all of that
diversity converges — exactly the shared-utility shape the mechanism section
describes.

### The gotcha

**Pitfall:** treating "lambdas are just sugar for anonymous classes, and
interface calls are always this fast" as a reason not to look here at all
when a hot path underperforms. The wrong belief: because a single lambda
invocation is a normal virtual call, lambda-heavy code cannot have a
JIT-specific performance story worth profiling for. The symptom: a hot
generic utility that looks trivial in isolation, benchmarks fine in a
microbenchmark that only ever exercises it with one lambda shape, and then
underperforms in the full application, where dozens of call sites feed it
distinct lambda types. The fix: when profiling shows this, either narrow the
call site's type diversity (route different behaviours through different,
dedicated methods instead of one polymorphic utility) or accept the
megamorphic cost as the price of the abstraction on a path where it is not
actually hot enough to matter — do not "fix" it by guessing without a
profiler in hand.

> **Definition.** HotSpot's inline cache at a lambda (or any interface) call
> site starts monomorphic and inlines through the interface call when the
> concrete receiver type stays stable; once more than a small, bounded number
> of distinct concrete types reach the same call site the cache goes
> megamorphic, dispatch falls back to a full virtual lookup with no inlining,
> and any prior speculative inlining at that site is deoptimized.

---

## Version behaviour recap

| Behaviour | Java 8–20 | Java 21 | Note |
|---|---|---|---|
| Capture mechanism (`invokedynamic` + spun hidden class) | Present since 8 | Unchanged | Covered fully in file 03; this file assumes it |
| Effectively-final capture rule | Present since 8 (relaxing the pre-8 mandatory `final`) | Unchanged | JLS §4.12.4, stable since introduction |
| Lambda identity guarantee | Unspecified since 8 | Still unspecified | JLS §15.27.4 wording unchanged; only the caching heuristic is JDK-version-dependent, not the spec |
| `equals`/`hashCode`/`toString` on a lambda | `Object`'s defaults since 8 | Unchanged | No override generated in any release |
| Inline-cache monomorphic/megamorphic behaviour | Present since HotSpot's inception, applies to lambdas since 8 | Unchanged | Not lambda-specific; guide 06's general JIT mechanism |

Nothing in this file's ten leaves changed behaviour at Java 21 itself — the
version-sensitive material this file's packet corrections concern (virtual
thread scheduler defaults, `ForkJoinPool` internals, structured concurrency's
two shapes, the enum-switch synthetic default's exception type) belongs to
other files' leaves, not §3.2's. Where this file references those facts
(the 8-core worked numbers in section 4, and `[X-REF]`s into guides 05/06),
it defers to the verified figures rather than restating stale ones.

---

## Pitfalls

### Assuming a captured field is a snapshot, not a live view

**Wrong**

```java
final class ProfileService {
    private volatile RiskTier currentRiskTier = RiskTier.STANDARD;
    Supplier<RiskTier> tierAtRegistration() {
        return () -> currentRiskTier;   // looks like a snapshot, isn't one
    }
}
// caller:
Supplier<RiskTier> snapshot = profileService.tierAtRegistration();
profileService.escalate();              // sets currentRiskTier = ELEVATED
System.out.println(snapshot.get());     // prints ELEVATED, not STANDARD
```

**Right**

```java
Supplier<RiskTier> tierAtRegistration() {
    RiskTier snapshotValue = currentRiskTier;   // captured local: copied by value
    return () -> snapshotValue;
}
```

**Why people believe it:** "capture is by value" is the correct rule for
locals, and most tutorials illustrate it only with locals, never mentioning
that an unqualified field read is sugar for `this.field` and therefore
captures the whole object by reference instead.

### Removing a listener by passing a freshly-written lambda

**Wrong**

```java
notifier.addListener(key -> System.out.println("changed: " + key));
notifier.removeListener(key -> System.out.println("changed: " + key)); // silent no-op
```

**Right**

```java
Consumer<RestrictionKey> listener = key -> System.out.println("changed: " + key);
notifier.addListener(listener);
notifier.removeListener(listener);  // same reference: succeeds
```

**Why people believe it:** the two lambda expressions are character-for-
character identical, and it feels natural to assume "the same code" means
"the same object" — an assumption that held, loosely, for interned literals
and autoboxed small integers, but was never true for object allocation in
general and is not true here.

### Leaving a `this`-capturing lambda registered forever

**Wrong**

```java
ProfileService(ClientId clientId, List<AggregatedFieldSnapshot> aggregatedView) {
    this.clientId = clientId;
    this.aggregatedView = aggregatedView;
    NotificationService.register(() -> logIfElevated());  // no way to undo this
}
```

**Right**

```java
ProfileService(ClientId clientId, List<AggregatedFieldSnapshot> aggregatedView) {
    this.clientId = clientId;
    this.aggregatedView = aggregatedView;
    this.registeredListener = () -> logIfElevated();
    NotificationService.register(registeredListener);
}
void close() {
    NotificationService.unregister(registeredListener);  // explicit lifecycle hook
}
```

**Why people believe it:** registration reads as a cheap, local statement,
and nothing in the syntax hints that it pins the entire enclosing object
(and its whole aggregated-field graph) in memory for as long as the registry
exists.

### Believing lambda `==` is stable because a quick manual test said so

**Wrong**

```java
// "I checked, non-capturing lambdas are always == on my machine, so this is safe":
if (registeredCallback == someFreshLambda) { ... }
```

**Right**

```java
// keep and compare the actual reference, never re-derive it from a fresh expression
if (registeredCallback == retainedReferenceFromRegistration) { ... }
```

**Why people believe it:** running the section-5 style demo really does print
`true` for the non-capturing case on common OpenJDK builds today, and a
single manual confirmation feels like proof of a guarantee when it is only
evidence of current, unspecified, implementation behaviour.

---

## Cheat sheet

| Fact | One line |
|---|---|
| Capture mechanism | Value copied into a `private final` field of the spun hidden class, once, at lambda-expression evaluation time |
| Effectively-final | Assigned exactly once in scope, never reassigned/mutated after — the proof that the one-time copy can never diverge |
| Field read inside a lambda | Sugar for `this.field`; captures `this` by reference, re-reads the field fresh on every invocation |
| Listener-registry leak | A `this`-capturing lambda held by a longer-lived registry keeps the whole enclosing object graph reachable |
| Lambda identity | Unspecified by JLS §15.27.4; non-capturing lambdas are commonly (not guaranteedly) cached as one instance on current OpenJDK |
| `==` on lambdas | Meaningless — never reach for it; `removeListener(freshLambda)` never removes a prior registration |
| `equals`/`hashCode` | `Object`'s defaults — identity-based, no override generated |
| `toString()` | `EnclosingClass$$Lambda/0x...@hash` — carries no intent information, unstable across runs |
| Reflection | `getClass().getInterfaces()` works; the implementing method and source form are not supported to recover |
| JIT behaviour | Monomorphic call site inlines through the interface call; too many distinct concrete lambda types at one shared call site goes megamorphic and deoptimises |
| Fix for stale-vs-live field confusion | Capture an explicit local snapshot, not the field, when you want value-at-creation-time |
| Fix for the leak | Capture a narrow local, or add an explicit unregister tied to lifecycle |

---

## Self-test

**Q1.** A lambda closes over a local `String ledgerId`. Where does `ledgerId`'s value actually live once the lambda is constructed, and when is it written there?

<details><summary>Answer</summary>

It lives in a `private final` field of the lambda's spun hidden class, one
field per captured variable. The write happens exactly once, in the hidden
class's constructor, at the moment the lambda expression is evaluated —
not when the lambda is later invoked, and not as a reference back to the
original stack slot.

</details>

**Q2.** Why must a captured local be effectively final, in terms of what the compiler is trying to prove?

<details><summary>Answer</summary>

Effectively-final guarantees, by a static syntactic check (assigned exactly
once, never reassigned or mutated anywhere in scope), that there is only one
value the variable ever holds. That makes the one-time copy into the
lambda's field provably identical to whatever value any other read of the
local would see — if a reassignment were allowed, the copy could diverge
from a "live" value with no rule for which one is authoritative.

</details>

**Q3.** `ProfileService` has an instance field `currentRiskTier`. A lambda inside an instance method reads `currentRiskTier` unqualified. Is that a capture of the field's value or of something else, and what follows from the answer?

<details><summary>Answer</summary>

It captures `this` — the unqualified field read is sugar for
`this.currentRiskTier`, and `this` (not the field) is what gets promoted to
the hidden class's constructor parameter. It follows that the lambda re-reads
the field fresh on every invocation, so it observes any write made to
`currentRiskTier` after the lambda was created and before it runs — it is
not a snapshot, even though the field itself is not a captured local.

</details>

**Q4.** Explain the listener-registry leak in terms of GC reachability, using a static `NotificationService` registry and a `ProfileService` instance as the example.

<details><summary>Answer</summary>

`NotificationService`'s registry field is `static`, making it a GC root that
is reachable for the whole process lifetime. If it holds a lambda that
captures `this` from a `ProfileService` instance (directly, or via an
unqualified field/method reference), the chain is: GC root → registry list →
lambda instance → captured `this` field → the `ProfileService` instance →
everything reachable from its own fields (its aggregated view, potentially
sourced from up to eight owning services). None of that subgraph is
collectible while the registry holds the lambda, regardless of whether
anything else in the program still needs the `ProfileService` instance.

</details>

**Q5.** Two evaluations of the lambda expression `() -> "AA-801"` (non-capturing) are compared with `==`. What does the JLS guarantee about the result, and what does a typical OpenJDK build actually do?

<details><summary>Answer</summary>

The JLS guarantees nothing — JLS §15.27.4 explicitly states it is
unspecified whether lambda evaluations produce the same or different
instances, and that this may vary by implementation and even between
evaluations. In practice, current OpenJDK builds commonly cache the single
hidden-class instance for a non-capturing lambda and hand back the same
object on both evaluations, so the demo prints `true` today — but that is
implementation behaviour, not something correct code may rely on.

</details>

**Q6.** A method `notifier.removeListener(evt -> handle(evt))` is called with a lambda expression identical in source to the one passed to `addListener` earlier. Does it remove the earlier registration? Why or why not?

<details><summary>Answer</summary>

No, never. `removeListener` typically relies on `List.remove(Object)`, which
uses `.equals()`; a lambda's `equals` is `Object`'s default, i.e. reference
identity. The freshly written lambda expression is evaluated at a different
point in the program from the original registration and is not guaranteed
(and for capturing lambdas, is provably not) the same object, so the
equals-based removal always fails to match.

</details>

**Q7.** Why are `equals`, `hashCode`, and `toString` on a lambda all `Object`'s defaults rather than something content-aware?

<details><summary>Answer</summary>

`LambdaMetafactory` spins a hidden class that implements only the target
functional interface (and optionally `Serializable`/markers); it generates no
override for `equals`, `hashCode`, or `toString`. All three are therefore
inherited from `Object` unmodified: `equals` is reference identity,
`hashCode` is identity-derived, and `toString` is the default
`ClassName@hexHash` form, here rendered with a JVM-synthesized hidden class
name.

</details>

**Q8.** What can reflection actually tell you about a lambda instance, and what can it not?

<details><summary>Answer</summary>

`getClass().getInterfaces()` correctly reports the functional interface(s)
the lambda implements, because the hidden class genuinely implements them.
What reflection does not give you is a supported, stable way to see the
lambda's original source or recover a documented handle to "the method it
runs" — the functional method typically forwards to a compiler-generated
synthetic method on the enclosing class whose name and existence are
implementation detail, not a public reflective contract.

</details>

**Q9.** A shared utility method `applyAdjustment(BigDecimal amount, Function<BigDecimal, BigDecimal> fn)` is called from many places in a codebase, each passing a different lambda expression for `fn`. Why can this hurt performance even though each individual call to `fn.apply(...)` is a normal interface call?

<details><summary>Answer</summary>

HotSpot's inline cache at the `fn.apply(...)` call site inside the one
compiled copy of `applyAdjustment` tracks the concrete types it has seen.
Because every distinct lambda expression is backed by a distinct class, many
different call sites in source funneling through this one shared method can
present many different concrete types to the same runtime call site. Once
that exceeds the small bound the cache can track, the site goes megamorphic:
dispatch falls back to a full virtual lookup on every call, inlining stops,
and any earlier speculative inlining at that site is deoptimized — a cost
that is invisible in source and only visible in a profiler.

</details>

**Q10.** A reviewer sees `return () -> someInstanceField;` inside an instance method and says "that's fine, it just captures the field's current value." What is wrong with that description, and what is the accurate one?

<details><summary>Answer</summary>

It is not a capture of the field's value at all — `someInstanceField` is
sugar for `this.someInstanceField`, so the lambda captures `this` by
reference and re-reads the field fresh on every invocation. The accurate
description: the lambda will observe whatever the field holds at call time,
including any write made after the lambda was created, not the value at the
moment the lambda expression was written or evaluated.

</details>

---

## Deferred

None.

---

**Leaves covered:** 3.2.1–3.2.10 (10 leaves)
**Leaves deferred:** none
**Diagrams included:** D-130
**Target version:** Java 21 LTS
**Lines:** 1506
