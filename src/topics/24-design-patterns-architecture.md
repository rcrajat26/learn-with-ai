# 24 — Design Patterns & Application Architecture

Scope: patterns as **forces and consequences**, and the architectures that fall out of applying them at
module scale. Guide 22 owns distributed composition (CAP, partitioning, capacity arithmetic); guide 07
owns Spring's proxy machinery; this guide owns *why a structure exists, what tension it resolves, and
what it costs you afterwards*.

Pattern questions fail candidates in a specific way: the answer names a pattern. "I'd use a factory."
That scores nothing, because a pattern name is a *label for a resolved force*, and the interviewer is
testing whether you can see the force. The scoring answer is always shaped: **"the varying thing here
is X, the thing that must stay stable is Y, so I'd introduce Z, and the cost is W."** Everything below
is organised to make that sentence available for each pattern.

---

## 1. What a pattern actually is

Four parts, and only the first two are interesting in an interview:

| Part | Content | Interview weight |
|---|---|---|
| **Problem** | The recurring situation. "New payment providers arrive every quarter." | High |
| **Forces** | The competing constraints that make it hard. "Adding one must not touch the order service, but they share no interface." | Highest |
| **Structure** | The classes/interfaces. Diagrammable. | Low — memorisable, so it proves nothing |
| **Consequences** | What you now pay: indirection, more types, harder stack traces, runtime instead of compile-time errors. | High |

**Mechanism of why patterns work at all:** every one of them converts a *variation* into a *substitution
point*. You take the axis along which requirements change and put a polymorphic boundary exactly there.
If you pick the wrong axis, the pattern makes the code worse — you now have indirection with no
variation flowing through it.

**Trap:** "pattern matching" as an interview strategy — hearing "many providers" and answering
"Strategy". Named without the force, it reads as recall. Worse, the interviewer's follow-up ("why not
just a switch?") has no answer if you never articulated the force. A `switch` is correct when the set
is closed and owned by you; a Strategy earns its indirection when the set is open, or when each branch
carries state/dependencies of its own.

**Trap:** claiming a pattern makes code "more flexible" or "more maintainable". Both are unfalsifiable.
Say instead which *specific future change* becomes a one-file change, and which becomes harder. Patterns
buy flexibility on one axis by *freezing* the others: Strategy makes new algorithms cheap and makes
changing the strategy *interface* expensive (every implementation must change).

**When not to use a pattern:** rule of three. One case — write it inline. Two — duplicate and wait. Three
— now you can see the axis of variation, and only now do you know where the seam goes. Introducing the
seam at one case is guessing, and a wrong seam is more expensive than duplication because it is load-bearing.

---

## 2. Creational patterns

### 2.1 Factory method vs abstract factory vs static factory

**Force:** the caller must obtain an object without knowing its concrete type, or the construction step
itself needs a name / a decision / validation that a constructor cannot express.

**Static factory method** (not a GoF pattern, most useful in practice): a named static method replacing
`new`. Mechanism benefits that a constructor cannot give you: it can return a *subtype*, it can return a
*cached* instance, it can have a *name* (two constructors with the same signature are impossible;
`Money.ofMinor(1250)` vs `Money.ofMajor(12.50)` are not), and it can fail before allocation.

**Factory method (GoF):** an *instance* method, overridden by subclasses, that decides the concrete type.
The variation point is a subclass of the creator.

**Abstract factory:** one object producing a *family* of related products that must be used together.
The force is consistency across products, not just substitutability of one.

```java
public interface PayoutProviderFactory {                 // abstract factory
    PayoutClient client();                               // family member 1
    PayoutWebhookVerifier verifier();                    // family member 2 — must match member 1
}

@Component
class StripePayoutProviderFactory implements PayoutProviderFactory {
    public PayoutClient client() { return new StripePayoutClient(); }
    public PayoutWebhookVerifier verifier() { return new StripeSignatureVerifier(); }
}
```

The whole point: you cannot accidentally pair the Stripe client with the Adyen verifier, because they
are never obtainable separately.

| | Chooses | Variation axis | Use when |
|---|---|---|---|
| Static factory | Caller-visible named construction | None (just ergonomics/caching) | Naming, validation, caching, returning subtypes |
| Factory method | Subclass of the creator | One product type | A framework class must let you swap what it instantiates |
| Abstract factory | Injected factory object | A *family* of products | Products must be mutually consistent |
| Spring `@Bean` method | The container | Anything | Almost always — Spring is the factory; hand-rolling one is often redundant |

**Trap:** writing an abstract factory when DI already solves it. If Spring can inject the right
`PayoutClient` by profile or `@Qualifier`, a factory interface adds a layer that only exists to do what
the container does. The factory earns its place when the choice is made **per request** (from a tenant
ID, currency, or provider column on the row) rather than per deployment — that is exactly the case DI
cannot cover, and see § 4.1 for the `Map<String, T>` idiom that handles it.

### 2.2 Builder — and why records did not kill it

**Force:** many parameters, several optional, and the object must be immutable and valid on completion.
A constructor with 9 parameters is unreadable at the call site and unsafe (two adjacent `String`s are
swappable without a compile error); a setter-based bean is mutable and can be observed half-built.

**Mechanism:** the builder accumulates into mutable fields, then a single `build()` performs
cross-field validation and constructs the immutable target in one shot. The invariant check has exactly
one home. Telescoping constructors cannot do this; each one either duplicates the validation or delegates
and validates twice.

```java
public record WagerSettlement(String wagerId, Money stake, Money payout,
                              Instant settledAt, String ruleVersion) {
    public WagerSettlement {                                  // compact constructor = the invariant gate
        if (payout.isNegative()) throw new IllegalArgumentException("payout < 0");
    }
    public static Builder builder() { return new Builder(); }
    public static final class Builder {
        private String wagerId; private Money stake = Money.ZERO; /* ... */
        public Builder stake(Money s) { this.stake = s; return this; }
        public WagerSettlement build() { return new WagerSettlement(wagerId, stake, /*...*/ null, null); }
    }
}
```

Records give you the *immutable carrier* and a validation hook (the compact constructor), but the
canonical constructor is still positional and all-args. So: **record = the product, builder = the
assembly ergonomics for products with ≥5 fields or optional fields.** They compose; they do not compete.
For 2–3 fields, a record alone with static factories is better — a builder there is ceremony.

**Trap:** a builder that can produce an invalid object because validation lives in the setters instead
of `build()`. Per-setter validation cannot check cross-field rules ("payout must be 0 when status is
VOID") because it runs before the other field is set.

**Trap:** a mutable builder shared across threads or reused after `build()`. If `build()` hands the
builder's own collection reference to the product, later `builder.addLeg(...)` mutates the already-built
object. `build()` must copy collections (`List.copyOf`) — see the defensive-copy discussion in
`03-java-core.md`.

### 2.3 Singleton at the JVM level

**Force:** exactly one instance, and controlled/lazy initialisation.

Four implementations, and the interview is entirely about the memory-model reasoning:

```java
// 1. Eager static final — thread-safe by the class-initialisation lock, JVM-guaranteed.
final class RateTable { static final RateTable INSTANCE = new RateTable(); }

// 2. Initialization-on-demand holder — lazy AND lock-free after first use.
final class RateTable {
    private RateTable() {}
    private static class Holder { static final RateTable INSTANCE = new RateTable(); }
    static RateTable get() { return Holder.INSTANCE; }
}

// 3. Enum singleton — serialization- and reflection-proof.
enum ScoringClock { INSTANCE; Instant now() { return Instant.now(); } }
```

**Mechanism of the holder idiom:** class initialisation in the JVM is guarded by a per-class
initialisation lock (JLS 12.4.2), and the nested `Holder` class is not initialised until first
*referenced*. So you get laziness from the classloader and thread safety from a lock the JVM already
takes and then never takes again — zero synchronisation cost on subsequent reads. This is strictly better
than any hand-written lazy init.

**Double-checked locking** is the classic trap:

```java
private static volatile RateTable instance;      // volatile is NOT optional
static RateTable get() {
    if (instance == null) {                      // 1st check, unsynchronised
        synchronized (RateTable.class) {
            if (instance == null) instance = new RateTable();   // 2nd check
        }
    }
    return instance;
}
```

**Trap:** DCL without `volatile`. `instance = new RateTable()` is not atomic: allocate, run constructor,
publish reference. Without `volatile` there is no happens-before edge between the constructor's writes
and another thread's unsynchronised first read, so thread B can see a **non-null reference to a
partially constructed object** — final fields readable as their default values. `volatile` on the field
creates the release/acquire pair that forbids this. Mechanism detail in `05-multithreading-concurrency.md`.
Say this and then say "which is why I'd use the holder idiom instead" — DCL is 6 lines of subtlety to
avoid a lock that is taken once.

**Why enum:** `readObject` deserialization and `Constructor.setAccessible(true)` both break the other
forms (deserialization creates a second instance; reflection calls the private constructor). The JVM
special-cases enums against both.

**Trap:** treating singleton-as-pattern and singleton-as-global-state as the same thing. A Spring
singleton *scoped bean* is an injected dependency with one instance per container — testable, mockable,
swappable. A `static getInstance()` is a hard-coded global dependency that no test can substitute and
that hides coupling from the type signature. When asked "is singleton an anti-pattern", the answer is:
the *lifecycle* is fine and common; the *global static access* is the anti-pattern. See § 6.7.

### 2.4 Prototype and copy semantics

**Force:** creating a new object is expensive or requires configuration you already have on an existing
instance; you want "one like that, but changed".

Java's `Cloneable`/`clone()` is broken by design: it is a marker interface with no `clone` method,
`Object.clone()` bypasses constructors (so invariants and `final` fields set in the constructor are not
re-established), and the default is a **shallow** copy — nested mutable state is shared with the
original. Deep vs shallow copy mechanics are in `03-java-core.md`.

Modern replacement: a **copy constructor** or a `with`-style method on a record.

```java
public record ScoringConfig(String ruleVersion, Map<String, Integer> weights, Duration window) {
    public ScoringConfig { weights = Map.copyOf(weights); }        // deep-ish: unmodifiable snapshot
    public ScoringConfig withWindow(Duration w) { return new ScoringConfig(ruleVersion, weights, w); }
}
```

**Trap:** calling a record "immutable" when it holds a `List` or a `Date`. Records give shallow
immutability — the *reference* is final, the referent is not. `Map.copyOf` in the compact constructor is
what actually closes it.

### 2.5 Object pool — and when pooling is a pessimization

**Force:** object creation involves a non-heap resource with a real setup cost — a TCP connection, a TLS
handshake, an OS thread, an off-heap buffer.

**Mechanism:** the pool keeps live instances, hands them out on borrow, and returns them on release,
converting a setup cost into a queue wait. It only wins when *setup cost ≫ borrow/return coordination
cost*.

Pooling is a **pessimization** for plain heap objects. A modern JVM allocates in the TLAB by bumping a
pointer (a few ns) and young-generation collection of dead objects is nearly free — dead objects cost
nothing to reclaim in a copying collector. A pool replaces that with: synchronisation on borrow, objects
surviving into the old generation (so they get *traced* on every GC cycle instead of being dropped), and
the risk of state leaking between users of a reused object. Detail in `06-jvm-internals.md`.

So: pool connections, threads, and off-heap buffers. Never pool DTOs, entities, or `StringBuilder`s.

**Trap:** a pool sized larger than the downstream can serve. A 200-connection pool against a Postgres
with `max_connections=100` just moves the failure from your app to the database and makes it harder to
see. Pool sizing is a *bottleneck* decision, not a throughput dial — see `10-networking.md`.

**Trap:** returning a dirty object to the pool. Any pooled object with mutable state needs an explicit
reset on release, or the next borrower inherits it — the classic cross-request data leak (a pooled
`ThreadLocal`-carrying object leaking one user's tenant ID into another's request; see the ThreadLocal
leak section in `05-multithreading-concurrency.md`).

---

## 3. Structural patterns

### 3.1 Adapter vs facade vs proxy vs decorator

These four have nearly identical *structure* — an object holding a reference to another and forwarding
calls. The distinction is **intent**, and interviewers probe exactly this boundary because it separates
people who read the catalogue from people who have designed something.

| | Interface vs target | Purpose | Composable/stackable | Typical trigger |
|---|---|---|---|---|
| **Adapter** | **Different** (converts) | Make an incompatible API usable | No | Third-party SDK doesn't fit your port |
| **Facade** | **New, simpler, narrower** | Hide a complex subsystem behind one entry point | No | 6-call ceremony that always happens together |
| **Proxy** | **Identical** | Control *access* to the target — lazy, remote, security, caching, transactions | Rarely, and transparently | Cross-cutting concern, or target is expensive/remote |
| **Decorator** | **Identical** | Add *behaviour* to the target, chosen by the caller at wiring time | Yes, by design, N-deep | Optional features in combination |

The mechanical discriminators, in the order to state them:

1. **Does the wrapper's interface equal the target's?** No → Adapter or Facade. Yes → Proxy or Decorator.
2. **Adapter vs Facade:** an adapter targets *one* object and translates; a facade orchestrates *several*
   and simplifies. An adapter has an existing client interface it must satisfy; a facade invents one.
3. **Proxy vs Decorator:** who decides it is there, and does the client know? A decorator is *chosen by
   the assembling code* to add a feature and is meant to stack (`new RetryingClient(new MeteredClient(real))`).
   A proxy is *transparent* — the client believes it holds the real thing — and controls access rather than
   enriching behaviour. A proxy typically also *owns the target's lifecycle* (it may create it lazily);
   a decorator is always handed a fully constructed target.

```java
// Decorator: caller opts in, stacks, same interface.
public final class RetryingPayoutClient implements PayoutClient {
    private final PayoutClient delegate; private final int attempts;
    public Receipt payout(PayoutRequest r) {
        for (int i = 1; ; i++) {
            try { return delegate.payout(r); }
            catch (TransientGatewayException e) { if (i == attempts) throw e; backoff(i); }
        }
    }
}
```

**Trap:** "a decorator and a proxy are the same thing, the difference is academic." They differ in the
one thing an interviewer cares about: **intent visible in the wiring**. Also concretely: a decorator that
skips the delegate is a bug; a proxy that skips the delegate (cache hit, access denied, lazy no-op) is
doing its job.

**Trap:** calling `@Transactional` a decorator. It is a proxy — you did not ask for it at the call site,
you cannot stack two of them meaningfully, and it controls whether/how the target is invoked.

### 3.2 Dynamic proxy vs CGLIB, and what neither can intercept

Spring's proxy mechanics live in `07-spring-core.md`; here is only the pattern-level consequence.

| | Mechanism | Requires | Cannot intercept |
|---|---|---|---|
| **JDK dynamic proxy** | `Proxy.newProxyInstance` generates a class implementing the *interfaces*; calls land in an `InvocationHandler` | Target must implement an interface | Anything not on the interface; concrete-class injection fails with a cast error |
| **CGLIB / ByteBuddy subclass** | Generates a **subclass** at runtime and overrides methods | Non-final class, non-private constructor | `final` methods, `private` methods, `static` methods, fields |
| **Both** | Interception happens on the *external* call through the proxy reference | — | **Self-invocation**: `this.method()` inside the target bypasses the proxy entirely |

**Trap:** the self-invocation bypass is the single most-asked Spring/pattern crossover. Any proxy-based
concern — `@Transactional`, `@Cacheable`, `@Async`, `@Retryable`, custom AOP — is silently *absent* when
one method of a bean calls another on `this`, because `this` is the raw target, not the proxy. It does not
error; it just does nothing. Fixes: move the method to a different bean (correct), inject self, or use
`AopContext.currentProxy()` (both smells). AspectJ load-time weaving avoids it entirely by rewriting the
bytecode rather than wrapping.

**Trap:** thinking `final` classes are safe from proxying and therefore "faster". They just fail to
proxy — often silently degrading a feature rather than throwing.

### 3.3 Composite

**Force:** clients must treat a single item and a group of items identically, and groups nest arbitrarily.

**Mechanism:** leaf and container implement the same interface; the container's implementation delegates
to children and aggregates. Recursion lives in the container, not in every client.

```java
public sealed interface FeeRule { Money apply(Money base);
    record Percentage(BigDecimal pct) implements FeeRule { public Money apply(Money b) { return b.times(pct); } }
    record Composite(List<FeeRule> parts) implements FeeRule {          // container is also a FeeRule
        public Money apply(Money b) { return parts.stream().map(p -> p.apply(b)).reduce(Money.ZERO, Money::plus); }
    }
}
```

**Trap:** a composite whose interface has leaf-only operations (`addChild` on the shared interface), which
forces leaves to throw `UnsupportedOperationException`. That is an LSP violation (§ 5.3) baked into the
pattern: the "transparency" version puts child management on the shared type, the "safety" version puts it
only on the container and loses uniformity. Name the trade-off; there is no free version.

### 3.4 Bridge

**Force:** two dimensions vary independently, and inheritance can only express one. `NotificationType ×
Transport` as a class hierarchy gives you `EmailOrderConfirmation`, `SmsOrderConfirmation`,
`EmailPayoutAlert`, ... — an M×N class explosion.

**Mechanism:** split into an abstraction hierarchy (notification kinds) holding a reference to an
implementor hierarchy (transports). M+N classes, composed at runtime. Bridge is structurally like Strategy;
the difference is that a bridge is a *deliberate two-hierarchy split established up front*, whereas Strategy
swaps one algorithm inside an otherwise fixed class.

### 3.5 Flyweight

**Force:** an enormous number of objects whose state is mostly identical; memory, not CPU, is the constraint.

**Mechanism:** split state into **intrinsic** (shared, immutable, held once in a pool) and **extrinsic**
(passed in per call). Only intrinsic state is deduplicated.

Real flyweights in the JDK, worth naming because they are also traps:
- **`Integer.valueOf` cache**, −128..127 — which is why `Integer a=127, b=127; a==b` is `true` and the same
  with `128` is `false`. See `03-java-core.md`.
- **String pool / interning** — compile-time constants are pooled, `new String("x")` is not.
- **`Boolean.valueOf`**, `Character` cache 0..127.

**Trap:** claiming flyweight "makes things faster". It trades a hash lookup for allocation and cache
locality. It wins when the object count is in the millions; below that the pool lookup is a net loss.

---

## 4. Behavioural patterns

### 4.1 Strategy, and the Spring idiom that matters

**Force:** one step of an algorithm varies, the surrounding workflow does not, and the choice must be made
at runtime rather than at compile time.

**Mechanism:** extract the varying step behind an interface; the context holds a reference and delegates.
Selection is *composition*, so it can change per request, per tenant, per row.

The interview-relevant Java form is registry-by-key, because Spring builds the map for you:

```java
public interface ScoringStrategy { String key(); Points score(Answer a, Question q); }

@Service
public class ScoringService {
    private final Map<String, ScoringStrategy> byKey;
    public ScoringService(List<ScoringStrategy> all) {          // Spring injects every bean of the type
        this.byKey = all.stream().collect(toMap(ScoringStrategy::key, identity()));
    }
    public Points score(Answer a, Question q) {
        var s = byKey.get(q.scoringMode());
        if (s == null) throw new UnknownScoringModeException(q.scoringMode());
        return s.score(a, q);
    }
}
```

Adding a mode = adding one `@Component`. No existing file changes — that is OCP (§ 5.2) with a mechanism
behind it. Spring can inject `Map<String, ScoringStrategy>` directly too, keyed by *bean name*; keying by
an explicit `key()` method is better because bean names are refactoring-fragile and not domain values.

**Trap:** "Strategy replaces the switch." It relocates it. Something still maps a string to an
implementation — the map lookup *is* the switch, moved to wiring time. The gain is that the mapping is
data and the branches are independently testable/deployable units; the cost is that an unknown key is now
a **runtime** failure where a `switch` over a sealed enum was a **compile-time** exhaustiveness check.
If the set is closed and small, a pattern-matching switch over a sealed interface (§ 4.7) is genuinely
better, and saying so is a strong signal.

### 4.2 Template method vs strategy vs state

**Template method force:** the *skeleton* is fixed and steps vary — and the variation is per-subclass, not
per-invocation. Mechanism: a `final` public method in the base class calls `protected abstract` hooks. The
`final` is load-bearing; without it a subclass can override the skeleton and the invariant ordering is gone.

```java
public abstract class SettlementJob {
    public final Report run(BatchId id) {                  // final: the sequence is the invariant
        var rows = load(id);
        var valid = validate(rows);
        var result = settle(valid);                        // the varying step
        audit(id, result);
        return report(result);
    }
    protected abstract SettleResult settle(List<Row> rows);
    protected List<Row> validate(List<Row> r) { return r; }   // overridable default hook
}
```

| | Binding time | Coupling | Multiple varying steps | Runtime swap |
|---|---|---|---|---|
| **Template method** | Compile time (subclass) | Tight — inherits base internals, fragile base class (§ 5.7) | Natural (several hooks) | No |
| **Strategy** | Runtime (injected object) | Loose — interface only | Awkward (one object per step, or a wide interface) | Yes |
| **State** | Runtime, and **self-transitioning** | Loose, but states know each other | N/A — behaviour keyed on a lifecycle stage | Yes, and it changes itself |

**State vs strategy** is the sharpest distinction: a strategy is chosen *from outside* and does not change
itself; a state object *decides its own successor*. If the transition logic lives in the object, it is
State.

### 4.3 State machine vs boolean-flag sprawl

**Force:** an entity has a lifecycle, and the legal transitions are a business rule that must be enforced
in exactly one place.

The anti-pattern it replaces: `boolean paid, boolean shipped, boolean cancelled, boolean refunded`. Four
booleans is 16 representable combinations of which maybe 6 are legal, so *every* method must defensively
re-check the combination and the illegal states are representable at all. The mechanism of the fix is
**making illegal states unrepresentable**: one `status` enum plus an explicit transition table.

```java
enum WagerStatus {
    OPEN(Set.of("SETTLED", "VOID")), SETTLED(Set.of()), VOID(Set.of());
    private final Set<String> allowed;
    WagerStatus(Set<String> a) { this.allowed = a; }
    void assertCanMoveTo(WagerStatus next) {
        if (!allowed.contains(next.name())) throw new IllegalStateTransitionException(this, next);
    }
}
```

**Trap:** enforcing transitions in the service layer instead of on the entity. Then a second service, a
batch job, or a data-fix script bypasses it. The transition guard belongs inside the aggregate's
invariant boundary (§ 7.5).

### 4.4 Observer, and why in-process observers bite

**Force:** one thing happens; an open set of other things must react, and the source must not know them.

**Mechanism:** subject keeps a listener list and iterates it on event. The coupling inverts — listeners
depend on the subject's event type, not vice versa.

The three real failure modes, all of which come from the listeners running **synchronously on the
publisher's thread, inside the publisher's transaction**:

1. **Latency coupling.** A slow listener slows the publisher. Ten listeners at 50 ms each add 500 ms to a
   request that "just saves an order".
2. **Failure coupling.** A listener throwing propagates back into the publisher and, with Spring's default
   synchronous `ApplicationEventPublisher`, rolls back the publisher's transaction. "Sending the email
   failed, so the order was not placed."
3. **Deadlock / reentrancy.** A listener that calls back into the subject while the subject holds a lock,
   or that registers/removes listeners during iteration →
   `ConcurrentModificationException`. Classic in-process deadlock: publish while holding a lock, listener
   acquires locks in the opposite order (see `05-multithreading-concurrency.md`).
4. **Listener leak.** A registered listener is a strong reference from the (long-lived) subject to the
   (short-lived) observer. Never-deregistered listeners are a textbook heap leak.

The correct production shape: publish **after commit**, **asynchronously**, and **durably** for anything
that must not be lost — `@TransactionalEventListener(phase = AFTER_COMMIT)` for in-process, the transactional
outbox for cross-process. Outbox mechanics in `14-messaging-queues.md`.

**Trap:** treating in-process events as a substitute for messaging. An in-process event is lost on crash,
has no retry, no ordering guarantee, and no consumer visibility. It is a decoupling tool inside one
transaction boundary, not a delivery mechanism.

### 4.5 Command

**Force:** an operation must be treated as a value — queued, logged, retried, undone, or authorised —
rather than executed at the call site.

**Mechanism:** reify the invocation (receiver + parameters) into an object with an `execute()`. Once the
operation is data, everything that operates on data becomes available: serialisation (so it survives a
restart), a queue (so it can be deferred), a log (so it can be replayed → event sourcing, § 7.9), and an
inverse (`undo()`).

Java 21 shape: a `sealed interface Command` of records, dispatched by pattern-matching switch. `Runnable`,
`Callable`, and every message in a queue are commands.

### 4.6 Chain of responsibility

**Force:** a request must pass a sequence of independent handlers, each of which may handle it, transform
it, or pass it on — and the sequence must be reconfigurable without editing the handlers.

**Mechanism:** each handler holds the next and decides whether to call it. Crucially the handler controls
*both sides* of the delegation, which is what allows pre- and post-processing and short-circuiting.

The real instance every backend engineer has already used: the **servlet filter chain**. `chain.doFilter()`
is the "pass it on" call; code before it is request processing, code after it is response processing, and
*not* calling it short-circuits the request (how an auth filter returns 401 without ever reaching the
controller). Spring Security is a filter chain, which is why filter *order* is a security property.

**Trap:** confusing it with decorator. Both nest, both wrap. A decorator always delegates and adds
behaviour on the same interface; a chain handler may *refuse to delegate* — termination is the point.

### 4.7 Visitor, double dispatch, and its modern replacement

**Force:** many operations over a stable set of types, where you want to add operations without touching
the types.

**Mechanism — double dispatch:** Java dispatches on the runtime type of the *receiver* only. Visitor
manufactures a second dispatch: the client calls `node.accept(visitor)` (dispatch 1, on the node type),
and the node's `accept` calls `visitor.visitPercentageFee(this)` (dispatch 2, on the visitor type, with
the static type of `this` now known). Two virtual calls give you a virtual dispatch on a *pair* of types.

Consequences, stated as the "expression problem": visitor makes **adding operations cheap** and **adding
types expensive** (every visitor must change). A plain interface method does the reverse. Choose based on
which axis actually changes.

**Java 21 replacement:** sealed interfaces plus pattern-matching switch. The compiler's exhaustiveness
check gives you the "every visitor must handle every type" guarantee *without* the accept/visit boilerplate,
and adding a type breaks compilation at every switch — the same safety, visible in one place.

```java
static Money fee(FeeRule r, Money base) {
    return switch (r) {                                     // exhaustive; no accept()/visit() needed
        case FeeRule.Percentage p -> base.times(p.pct());
        case FeeRule.Composite c  -> c.parts().stream().map(x -> fee(x, base)).reduce(Money.ZERO, Money::plus);
    };
}
```

Sealed-type and switch-pattern mechanics are in `04-modern-java.md`. Saying "visitor is what you write
when the language has no exhaustive pattern matching" is the senior-level framing.

### 4.8 Iterator, mediator, memento, interpreter

**Iterator.** Force: traverse a collection without exposing its representation. Mechanism: externalise
cursor state into a separate object, so multiple simultaneous traversals are possible and the collection's
internals stay private. Java's `Iterator` also carries the **fail-fast** contract: a `modCount` field
compared on each `next()`, throwing `ConcurrentModificationException` — a best-effort bug detector, not a
thread-safety guarantee. See `02-java-collections.md`.

**Mediator.** Force: N components that all talk to each other — N² coupling. Mechanism: components talk
only to a mediator, which encodes the interaction rules; coupling drops to N, but the mediator accumulates
all the logic and can become a god object (§ 6.1). Trade N² edges for one high-risk node.

**Memento.** Force: capture and restore an object's state without exposing its internals. Mechanism: the
object itself produces an opaque snapshot only it can interpret. Real instances: DB savepoints, editor
undo stacks, and **event-sourcing snapshots** (§ 7.9).

**Interpreter.** Force: a recurring problem is best expressed in a small language. Mechanism: model the
grammar as a composite of expression nodes and evaluate recursively. In practice you reach for it when
business users need to author rules (fee expressions, eligibility rules); the cost is that you now own a
language, including its errors, tooling, and versioning. Usually the right answer is an existing engine,
not a hand-written interpreter.

---

## 5. SOLID, with mechanisms instead of slogans

### 5.1 SRP — one reason to change

Not "a class does one thing" (unfalsifiable). **One axis of change / one set of stakeholders.** The
operational test: if a pricing-rule change and a report-format change both edit the same class, two teams
now contend on one file, and their releases are coupled. That is the concrete cost — merge conflicts and
coupled deployments, not aesthetics.

### 5.2 OCP — extension without modification

Mechanism: the extension point must be a *polymorphic boundary that already exists*. OCP is not achievable
retroactively for free; you get it only where you predicted the variation axis correctly. § 4.1's
`Map<String, ScoringStrategy>` is OCP made real: new behaviour is a new file.

**Trap:** presenting OCP as "never modify existing code". You modify existing code constantly; OCP says
adding a *known kind of variation* should not require it.

### 5.3 LSP — the violations that compile

A subtype must be usable wherever the supertype is, *including its contracts*. Compiling is not the test.
Concrete violations that compile fine:

- **Strengthening a precondition.** Base accepts any `Money`; the override throws on amounts over a limit.
  Existing callers now fail on valid input.
- **Weakening a postcondition.** Base guarantees a sorted result; the override does not.
- **Throwing a new unchecked exception** the base never documented.
- **`UnsupportedOperationException`.** `List.of(...)` returning an immutable list from the `List` interface
  is *the* JDK example — every mutating method violates LSP. `Arrays.asList` is worse: `set` works,
  `add` throws.
- **Covariant arrays.** `Object[] a = new String[1]; a[0] = 42;` compiles and throws
  `ArrayStoreException` at runtime — Java's own LSP hole, and why generics are invariant
  (see `03-java-core.md` on erasure and PECS).

The consequence to name: LSP violations turn into `instanceof` checks in the *caller*, and once callers
type-test, the polymorphism is gone and the abstraction is fake.

### 5.4 ISP — fat interfaces force dummy implementations

Mechanism: an implementor must supply *every* method, so a wide interface forces stubs, and each stub is a
lie that callers can invoke. Symptom: a class whose half the methods are `return null` or `throw new
UnsupportedOperationException`. Splitting the interface changes nothing at runtime and everything about
what compiles. Wide interfaces also break OCP for the *interface owner*: adding a method breaks every
implementor (which is exactly what `default` methods on interfaces were introduced to soften —
`04-modern-java.md`).

### 5.5 DIP — the principle hexagonal architecture is made of

**Statement:** high-level policy must not depend on low-level detail; both depend on an abstraction owned
by the high-level module. That last clause is the whole mechanism and the part everyone drops.

Concretely: the `interface WagerRepository` lives in the **domain** package, not in the persistence
package. Then the compile-time dependency arrow points *from* the JPA adapter *into* the domain, and the
domain can be compiled, tested, and reasoned about with no JPA on the classpath. Move that interface into
the persistence package and you have a plain layered app wearing hexagonal vocabulary.

**Mechanism of the inversion:** at compile time, domain → interface ← adapter. At runtime, the container
injects the adapter, so control flows domain → adapter while *dependency* flows adapter → domain. Two
arrows in opposite directions is what "inversion" names.

**Trap:** "we use interfaces, so we follow DIP." Interfaces owned by the implementation side invert
nothing. The test is one question: **which module would you have to delete the other to compile?**

### 5.6 Law of Demeter

`a.getB().getC().doThing()` — each dot is a dependency on a *structural* fact you did not declare. Change
`B`'s internals and this line breaks even though it never mentions `B`'s purpose. Mechanism of the fix:
`a.doThing()` — tell, don't ask. The train wreck is also the clearest symptom of an anemic model (§ 6.2):
the behaviour lives at the end of the chain in the *caller* instead of on the object that owns the data.

Exception: fluent builders and streams are deliberate chains on *the same* object; they are not Demeter
violations because each call returns the same conceptual thing.

### 5.7 Composition over inheritance, and the fragile base class

Inheritance is the strongest coupling in the language: the subclass depends on the superclass's
*implementation*, including which of its own public methods it calls internally.

**Fragile base class, mechanically:** `HashSet.addAll` internally calls `add`. Subclass `CountingSet`
overrides both to increment a counter. Now `addAll` of 3 elements counts 6, because the base's `addAll`
routes through the overridden `add`. Nothing in the base's public contract told you it self-calls; a later
JDK version could change it and silently break you. Fixes: make the self-call policy part of the documented
contract, `final`ise, or **use composition** — hold a `Set` and forward, which is immune because you control
every entry point.

Other consequences to name: single inheritance is a budget you spend once; inheritance is fixed at compile
time while composition is swappable at runtime; a subclass inherits its parent's *entire* public surface
including methods that make no sense for it (an LSP hazard).

Inheritance is still correct for genuine `is-a` with a stable, `sealed`, or `abstract`-designed base —
template method (§ 4.2) is the legitimate case.

### 5.8 DRY, YAGNI, KISS as trade-offs

**DRY** is about duplicated *knowledge*, not duplicated characters. Two identical validation blocks that
encode two *different* rules which currently agree must stay separate — merging them creates false coupling
and the next requirement change breaks both callers. The worst DRY failure is deduplicating across bounded
contexts (§ 7.7): a shared `Customer` class binds two teams' release cycles forever.

**YAGNI** vs extensibility: the cost of a wrong abstraction exceeds the cost of duplication, because
duplication is *local and deletable* while a wrong abstraction is *load-bearing and referenced*. Hence the
rule of three (§ 1).

**KISS**'s operational meaning: complexity is paid at 3 a.m. by whoever is on call. A design you cannot
explain in five minutes cannot be debugged under pressure.

---

## 6. Anti-patterns, with the failure mechanism

### 6.1 God object / god service

A class with 3,000 lines and 40 dependencies. Mechanism of harm: every change touches it, so every team
touches it → constant merge conflicts, an untestable unit (40 mocks), and a class no one can hold in their
head so all changes are made defensively by adding rather than editing. Detection: dependency count, file
churn in git (`17-git-craft.md`), and fan-in/fan-out metrics.

### 6.2 Anemic domain model

Entities are field bags with getters/setters; all behaviour lives in `*Service` classes. Mechanism of harm:
invariants cannot be enforced, because any caller can set any field into any combination. Validation is
therefore duplicated in every service, and one path always forgets. The object has *data* but no
*guarantees*, so you cannot reason locally about whether an instance is valid.

Rich model instead: private setters, state changes as intention-revealing methods that check invariants
(`wager.settle(payout)` rather than `wager.setStatus(SETTLED); wager.setPayout(p);`), and construction that
cannot produce an invalid instance.

**Trap:** presenting an anemic model as good layered design ("entities are just persistence, logic belongs
in the service layer"). This is the most common senior-interview false confidence. The honest position:
anemic + transaction script is a *legitimate deliberate choice* for CRUD-shaped domains with thin rules,
and it is *wrong* for domains with real invariants. What loses points is not knowing you chose it.

### 6.3 Service layer as transaction script

Every use case is a procedural method: load rows, mutate, save. Fine and simple at small scale. The
mechanism of decay: business rules accumulate as conditionals inside the script rather than as domain
concepts, so the same rule appears in three scripts with drifting details, and there is no place to put
the *concept*. Symptom to name in an interview: a 400-line `@Transactional` method with nested `if`s over
a status string.

### 6.4 Circular dependencies

Package `order` → `billing` → `order`. Mechanism of harm: neither can be compiled, tested, deployed, or
understood in isolation; the cycle is the real module, and it is bigger than either package. At bean level
Spring may resolve a constructor cycle only by failing (or by lazy proxying), and field injection hides it
(`07-spring-core.md`). Breaking it always means the same move: extract the shared concept into a third
module both depend on, or invert one direction with a domain event (§ 4.4) so `billing` reacts instead of
being called.

### 6.5 Primitive obsession

`String customerId, String currency, BigDecimal amount` everywhere. Mechanism of harm: the compiler cannot
distinguish a `customerId` from an `orderId`, so argument transposition is a runtime bug; and validation
("currency is a 3-letter ISO code") has no home, so it is re-done or skipped at each boundary. Fix: value
objects (§ 7.4) — `record CustomerId(String value)` with validation in the compact constructor. The
transposition bug becomes a compile error.

### 6.6 Feature envy and leaky abstraction

**Feature envy:** a method that reads mostly another object's data. The mechanism: behaviour is on the
wrong side of a boundary, so every change to the data's shape ripples to the envious method. The move is
to push the method onto the data's owner.

**Leaky abstraction:** the abstraction's *interface* is clean but its *failure modes and performance* are
not, so callers must know the implementation anyway. Canonical examples: a `Repository` returning entities
that throw `LazyInitializationException` outside the session (`08-spring-data-jpa.md`), and a "transparent"
cache whose staleness callers must reason about (`15-caching.md`). Hyrum's law: with enough consumers,
every observable behaviour becomes part of the contract, documented or not.

### 6.7 Singleton as global state, and over-engineering

Static mutable state defeats DI, is invisible in constructor signatures, makes tests order-dependent
(state leaks between tests), and is a shared-mutable-state concurrency hazard by construction.

**Over-engineering with patterns** is its own anti-pattern: an abstract factory producing a strategy
consumed by a decorator chain, for one implementation that has never changed. Mechanism of harm: each layer
of indirection costs a hop when reading the code, so "where does this actually happen" takes 20 minutes
instead of 20 seconds, and stack traces stop naming your logic. The interview-safe stance: **indirection
must be paid for by a variation that exists**.

---

## 7. Application architecture

### 7.1 Layered / n-tier

Controller → service → repository → DB, with dependencies pointing down. Mechanism: each layer may only
call the one beneath, so a change in one layer's internals is contained.

What it actually gets you and what it does not: it does contain *technology* change (swap the web framework
without touching services). It does **not** contain *feature* change — a new field touches all four layers,
which is why layering plus package-by-layer (§ 7.3) produces "shotgun surgery". Its real failure mode is
that the domain ends up depending on persistence (entities are JPA entities, so the domain cannot compile
without Hibernate), which is precisely what DIP (§ 5.5) forbids.

### 7.2 Hexagonal (ports & adapters), clean, onion

All three are the same idea with different diagrams: **the domain is at the centre and depends on nothing;
every dependency arrow points inward.**

- **Port** = an interface *owned by the domain*. Inbound ports are use cases the outside calls; outbound
  ports are what the domain needs (`WagerRepository`, `PayoutGateway`).
- **Adapter** = an implementation of a port that speaks a technology (REST controller, JPA repository,
  Kafka consumer). Adapters depend on ports; ports never depend on adapters.

| | Centre | Rings/layers | Testing consequence | Main cost |
|---|---|---|---|---|
| **Layered** | Database (in practice) | Controller/service/repo/DB | Service tests need a DB or heavy mocks | Domain couples to persistence |
| **Hexagonal** | Domain | Domain / ports / adapters (2 rings) | Domain tests are plain JUnit, no Spring | Mapping code between domain and entities |
| **Clean / Onion** | Entities | Entities / use cases / interface adapters / infrastructure (4 rings) | Same, plus explicit use-case objects | Most ceremony; can double the class count |

**Trap:** the hexagon drawn on the whiteboard while dependencies still point outward — the domain imports
`jakarta.persistence`, the "port" interface lives in the infrastructure package, or the use case returns a
JPA entity to the controller. The verification is mechanical and worth stating: **the domain module's build
file should have no framework dependencies**, and ArchUnit can assert it in a test (`16-testing.md`).

**Trap:** treating the domain/entity mapping as pure overhead. It is the price of the isolation, and it is
real — for a CRUD service with no invariants, layered is the correct, cheaper answer. Say which you would
choose and why, rather than defending hexagonal universally.

### 7.3 Package-by-layer vs package-by-feature

```
com.app.controller.*  com.app.service.*  com.app.repository.*     // by layer
com.app.wager.*  com.app.payout.*  com.app.scoring.*              // by feature
```

Mechanism of the difference: **Java's access modifiers are package-scoped.** With package-by-layer, every
class must be `public` for the layer above to reach it, so *nothing* can be hidden and every class is a
potential dependency of every other. With package-by-feature, the feature's internals can be
package-private and only the deliberately exposed entry point is `public` — the compiler now enforces the
module boundary.

Secondary consequences: a feature change touches one directory (readable diffs, low merge contention, easy
code ownership); the package structure names the domain rather than the framework; and extracting a feature
into a separate service later is a directory move rather than an archaeology project. This is why
package-by-feature wins for modularity — it is not taste, it is which structure the compiler can police.

### 7.4 DDD tactical patterns

- **Entity** — identity that persists through state change. Equality is by ID, not by fields. Two `Wager`
  rows with identical amounts are different wagers.
- **Value object** — no identity, equality by value, immutable. `Money`, `CustomerId`, `DateRange`. A record
  is the exact Java shape. This is the direct cure for primitive obsession (§ 6.5).
- **Repository** — a collection-like interface for aggregates, *owned by the domain* (§ 5.5). It returns
  aggregates, not rows, and never leaks query language into the domain.
- **Domain service** — behaviour that genuinely belongs to no single entity (e.g. a transfer spanning two
  accounts). A legitimate escape hatch; a *dumping ground* if everything lands there (§ 6.2).
- **Application service** — orchestration: transaction boundary, load aggregates, call domain, publish
  events. Contains no business rules. This is the layer `@Transactional` belongs on.
- **Domain event** — a fact in past tense (`WagerSettled`), immutable, carrying IDs and the occurrence
  time. Its purpose is to decouple *reaction* from *cause* (§ 4.4).
- **Ubiquitous language** — the code uses the domain's words exactly. Not decoration: a mismatch between
  code names and business names is where requirements get mistranslated, and every conversation pays a
  translation tax.

### 7.5 Aggregate and the invariant boundary

This is the load-bearing DDD concept and the one most often mis-stated.

An **aggregate** is a cluster of objects with a single **root** through which all external access goes. Its
boundary is defined by the **invariants that must be true at the end of every transaction** —
"a wager's legs' stakes must sum to the wager's total" means legs are inside the wager aggregate.

Mechanisms that follow directly:
- **One aggregate = one transaction.** Consistency inside the boundary is immediate; consistency *between*
  aggregates is eventual, via domain events. This is the design decision, not a compromise.
- **Aggregates reference each other by ID, never by object reference.** `Wager` holds a `CustomerId`, not a
  `Customer`. That is what keeps the transaction and the object graph small.
- **The aggregate is the concurrency unit.** Optimistic locking with a `@Version` on the root protects the
  whole invariant set with one check (`08-spring-data-jpa.md`).

**Trap:** designing aggregates by data ownership or by UI screen ("Customer owns everything about a
customer"). Large aggregates mean large transactions, long-held locks, and write contention on one row.
Prefer the smallest cluster that keeps the invariant, and make everything else eventual.

### 7.6 Bounded context

A boundary within which a term has one meaning and one model. "Order" in fulfilment (a shipment plan) and
"Order" in billing (an invoiceable amount) are *different models*, deliberately, and the mechanism that
makes this correct is that a single shared `Order` class would have to satisfy both sets of invariants and
would therefore satisfy neither. Contexts integrate via translation (an anti-corruption layer — which is
just Adapter, § 3.1, at module scale) rather than by sharing types. Bounded contexts are the natural
seam for service boundaries; see § 7.8.

### 7.7 CQRS and event sourcing at mechanism level

**CQRS force:** the write model needs normalisation and invariants; the read model needs denormalisation
and speed. One schema cannot be optimal for both. Mechanism: separate the paths — writes go through
aggregates, reads go against a projection built for the query (a materialised view, a denormalised table, a
search index).

The cost is **projection lag**: the read model is updated asynchronously, so a user's own write may not be
visible to their next read. Mitigations: read-your-writes routing (serve that user from the write model or
pin them to a version), or a client-supplied version to wait on. Say "eventual consistency window of ~X ms"
with a number, not "it's eventually consistent". Replication and read-model mechanics are in `22-system-design.md`.

**Event sourcing force:** the *history* is itself a business asset (audit, dispute resolution, temporal
queries, retroactive rule changes). Mechanism: the event log is the system of record; current state is a
fold over events.

Consequences you must be able to name:
- **Replay** rebuilds state — which is what makes new projections and bug fixes in projections possible.
- **Snapshotting** bounds replay cost: persist state at version N so replay starts there. Without it,
  loading a 100k-event aggregate becomes a 100k-row read.
- **Schema evolution is forever.** You must still be able to deserialise a v1 event written three years
  ago — versioned events plus upcasters.
- **You cannot delete data**, which collides with GDPR erasure. The usual answer is crypto-shredding
  (encrypt PII per subject, discard the key).
- **Queries are impossible on the log**, so projections are mandatory, so CQRS is not optional here.

**Trap:** proposing event sourcing because "it's event-driven". Event-driven communication (§ 8) and event
sourcing (a persistence strategy) are unrelated decisions. Adopting event sourcing without an audit/history
requirement buys a large operational cost for nothing.

### 7.8 Modular monolith vs microservices

| | Deployment | Enforcement of boundaries | Cross-module call | Failure mode | Real prerequisite |
|---|---|---|---|---|---|
| **Layered monolith** | 1 unit | None (everything is `public`) | Method call, in-transaction | Change amplification, coupled releases | None |
| **Modular monolith** | 1 unit | Compiler + ArchUnit + package-private | Method call or in-process event | Boundary erosion if unpoliced | Discipline only |
| **Microservices** | N units | Network (absolute) | RPC / message — can fail, is slow | Distributed monolith, cascading failure | CI/CD, tracing, on-call, service ownership |

The arithmetic that decides it:
- **Latency.** An in-process call is ~10 ns; a same-AZ RPC is ~0.5–1 ms — five orders of magnitude. A use
  case that touched 4 modules now costs 4 network hops in serial.
- **Availability.** Serial dependencies multiply. Six 99.99% services in a request path give 99.94%
  (`22-system-design.md`).
- **Transactions.** A single ACID transaction across modules becomes a saga with compensations and
  intermediate states that are visible to users (`14-messaging-queues.md`).
- **Ops.** N services means N pipelines, N dashboards, N alert sets, and distributed tracing goes from nice
  to mandatory (`20-observability-operations.md`).

The reason to split is therefore never "cleaner code" — the compiler gives you that in a modular monolith
for free. It is **independent deployability and independent scaling**, usually driven by team autonomy
(Conway's law) or by one component's wildly different resource profile.

**Trap:** the **distributed monolith** — services split by layer or by entity table rather than by bounded
context, so every use case fans out across five services, they share a database, and they must be deployed
together. You have paid every microservices cost and bought none of the benefit. Diagnostics: do two
services write the same table? Does a feature require a coordinated release? Is there a service whose only
job is to read another's data? Any yes means the boundary is wrong. **Shared database is the definitive
tell** — it makes the schema a public API that no one owns.

**Trap:** "start with microservices to avoid a rewrite later." Boundaries are wrong on the first attempt
and fixing a boundary is a refactor in a monolith and a migration across services. Start modular-monolith,
extract along seams that have proven stable.

---

## 8. Concurrency and resilience patterns

Each of these was invented for one named failure. State the failure, not the pattern.

| Pattern | Failure it was invented for | Mechanism | Key parameter / trap |
|---|---|---|---|
| **Producer–consumer** | Fast producer overwhelming a slow consumer | Bounded queue between them; producer blocks when full | **Trap:** an unbounded queue converts backpressure into an OOM. `ThreadPoolExecutor` with an unbounded `LinkedBlockingQueue` never creates extra threads and hides the overload (`05-multithreading-concurrency.md`) |
| **Reactor / event loop** | Thread-per-connection exhausting memory at 10k connections | One (few) thread(s) multiplex ready sockets via `epoll`, handlers must never block | **Trap:** one blocking JDBC call on the event loop stalls all connections on that thread |
| **Circuit breaker** | A dead dependency consuming all caller threads on timeouts, cascading the outage upstream | Count failures in a window; **open** → fail fast without calling; after a cooldown **half-open** → allow probes; success → **closed** | **Trap:** a breaker with no fallback just converts a slow failure into a fast one — decide what the open state *returns* (cached value, degraded response, 503) |
| **Bulkhead** | One slow dependency exhausting a shared thread pool and taking down unrelated endpoints | Separate pool / semaphore per dependency, so damage is contained to one compartment | Sizing: each bulkhead must be small enough that all of them together fit the box |
| **Retry with backoff + jitter** | Transient blips; and the retry storm the naive fix causes | Exponential backoff, plus **random jitter** to break synchronisation of retry waves | **Trap:** retrying non-idempotent operations (double charge) or retrying a 400. Retry only idempotent ops on transient errors, with a total attempt budget |
| **Timeout** | Waiting forever, holding a thread and a connection | Bound every remote call; timeout budget must *shrink* down the call chain | **Trap:** an inner timeout longer than the outer one is dead code |
| **Idempotency key** | At-least-once delivery / client retries producing duplicate side effects | Client sends a unique key; server stores it with the result under a unique constraint and replays the stored response on repeat | **Trap:** checking existence then inserting (race). The unique index *is* the mechanism (`12-api-design.md`) |
| **Rate limiter / load shedding** | Overload degrading everyone rather than rejecting some | Token bucket per key; shed lowest-priority load first | Shedding beats queueing: a queued request past its deadline is wasted work |
| **Sidecar / ambassador** | Cross-cutting concerns reimplemented in every language/service | Co-located process handles TLS, retries, discovery, telemetry out of the app | Cost: an extra hop, extra memory per pod, and a second thing to debug (`19-docker-kubernetes.md`) |

**Trap:** listing resilience patterns without their interaction. Retry *inside* a circuit breaker multiplies
load on a struggling dependency; the breaker must count the *retried* attempts, and retries must be bounded
before the breaker sees them. Timeout + retry + breaker are one policy, tuned together.

---

## 9. Refactoring toward patterns

The interview version of this is a three-part move, and candidates who skip part 3 lose the point.

| Smell | Smallest safe move | The test that protects it |
|---|---|---|
| `switch`/`if-else` on a type or mode, repeated in 3+ places | Extract each branch to a class behind an interface; keep the switch as the map lookup (§ 4.1) | A parameterised test over all keys asserting old and new produce identical output |
| Constructor with 8+ params, several optional | Introduce a builder (§ 2.2); keep the old constructor delegating, deprecate it | Existing tests unchanged — they still call the old constructor |
| Duplicated wrapping logic (retry/log/metrics) at every call site | Extract a decorator (§ 3.1) and wire it once | Test the decorator in isolation with a mock delegate; assert delegate call counts |
| Entity with public setters and rules in services (§ 6.2) | Make one setter private and add one intention-revealing method with its invariant | A test asserting the illegal transition now throws |
| Boolean flag combinations (§ 4.3) | Add the enum, derive it from the booleans, migrate readers, then drop the booleans | Golden-master test over all flag combinations before the change |
| Train-wreck chains (§ 5.6) | Add the delegating method on the owner; inline it at one call site | Existing behaviour test at the outer boundary |

Two disciplines to name explicitly: **change behaviour or structure, never both in one commit** (so a
bisect can tell you which), and **write the characterisation/golden-master test first** when the legacy
behaviour is unknown — you are protecting what it *does*, not what it should do. Approval testing and
seam-finding tie into `16-testing.md`; commit hygiene into `17-git-craft.md`.

---

## 10. Interview delivery

**"Which pattern would you use here?"** — answer in the fixed four-part shape:

1. **Name the force.** "The set of payout providers changes quarterly and each has its own credentials and
   webhook format."
2. **Name what must stay stable.** "The order-settlement flow must not change when one is added."
3. **Name the pattern and where the seam goes.** "An outbound port `PayoutGateway` in the domain, one
   adapter per provider, selected per row by provider code via a `Map<String, PayoutGateway>`."
4. **Name the cost.** "An unknown provider code is now a runtime failure instead of a compile error, so I
   add a startup assertion that every code in the DB has a registered adapter."

**How to reject a pattern** — this scores higher than applying one, because it demonstrates the force-first
reasoning. Templates: "there is only one implementation and no roadmap for a second, so the indirection has
nothing flowing through it — I'd inline it and extract on the third case"; "the set is closed and I own it,
so a sealed interface with an exhaustive switch gives me compile-time safety that a registry cannot";
"event sourcing would give me audit, but we already have an audit table and the replay/GDPR cost is not
worth it."

**Trade-off vocabulary** to use literally: coupling and cohesion; binding time (compile vs deploy vs
runtime); *where* an error surfaces (compile / startup / request); change amplification (files touched per
feature); testability without a container; who owns the interface (§ 5.5); blast radius; and cognitive
load / indirection depth.

**Trap:** proposing the most sophisticated option available. Interviewers read "hexagonal + CQRS + event
sourcing + microservices" on a CRUD problem as inability to size a solution. The strongest answer is
usually the simplest structure that meets the stated forces, plus one sentence naming the trigger that
would make you upgrade: "modular monolith now; I'd extract the scoring module when its CPU profile forces
independent scaling or when a second team owns it."

---

## Atomic concept checklist

- [ ] I can state any pattern as problem → forces → structure → consequences, and I lead with the force.
- [ ] I know every pattern converts an axis of variation into a substitution point, and a wrong axis makes code worse.
- [ ] I apply the rule of three rather than introducing a seam at the first case.
- [ ] I can say what a static factory does that a constructor cannot (name, subtype, caching, pre-allocation failure).
- [ ] I can distinguish factory method (subclass decides) from abstract factory (consistent product family).
- [ ] I know when DI makes a hand-rolled factory redundant, and when per-request selection makes it necessary.
- [ ] I know why a builder's validation must live in `build()` and not in the setters.
- [ ] I can explain why records and builders coexist rather than compete.
- [ ] I know `build()` must copy collections or the built object is mutable through the builder.
- [ ] I can write the initialization-on-demand holder idiom and explain the class-initialisation lock.
- [ ] I can explain why DCL without `volatile` can publish a partially constructed object.
- [ ] I know why enum singletons survive serialization and reflection attacks.
- [ ] I separate singleton-as-lifecycle (fine) from singleton-as-global-static-state (anti-pattern).
- [ ] I know why `Cloneable`/`clone()` is broken (no method, bypasses constructors, shallow by default).
- [ ] I know records are shallowly immutable and what closes that gap.
- [ ] I can explain why pooling plain heap objects is a pessimization on a modern JVM.
- [ ] I know a pool must be sized to the downstream bottleneck and must reset borrowed state.
- [ ] I can separate adapter/facade/proxy/decorator by interface-equality then by intent.
- [ ] I know a decorator always delegates and stacks; a proxy is transparent and may skip the target.
- [ ] I know what JDK dynamic proxies require and what CGLIB subclassing cannot intercept.
- [ ] I can explain the self-invocation bypass and why it fails silently.
- [ ] I know composite's transparency-vs-safety trade-off and that the transparent form violates LSP.
- [ ] I know bridge exists to avoid an M×N class explosion across two independent axes.
- [ ] I can name the JDK's real flyweights and connect the Integer cache to `==` behaviour.
- [ ] I can write the `Map<String, Strategy>` Spring idiom and explain why an explicit key beats bean names.
- [ ] I know Strategy relocates the switch to wiring time and moves an error from compile time to runtime.
- [ ] I know why a template method's skeleton must be `final`.
- [ ] I can distinguish strategy (chosen from outside) from state (transitions itself).
- [ ] I know why boolean-flag sprawl makes illegal states representable, and that the guard belongs on the aggregate.
- [ ] I can name all four in-process observer failure modes: latency, failure/rollback coupling, deadlock/CME, listener leak.
- [ ] I know in-process events are not a delivery mechanism, and that after-commit + async + outbox is the production shape.
- [ ] I know command reifies an invocation so it can be queued, logged, replayed, or undone.
- [ ] I know the servlet filter chain is chain-of-responsibility, and that not calling `doFilter` is the short-circuit.
- [ ] I can explain visitor's double dispatch and the expression-problem trade-off it makes.
- [ ] I know sealed interfaces + exhaustive switch replace visitor with compile-time checking.
- [ ] I know the fail-fast iterator uses `modCount` and is a bug detector, not a thread-safety guarantee.
- [ ] I know mediator trades N² coupling for one node that risks becoming a god object.
- [ ] I state SRP as one axis of change, with coupled releases as the concrete cost.
- [ ] I can give three LSP violations that compile, including `UnsupportedOperationException` and covariant arrays.
- [ ] I know a fat interface breaks OCP for the interface owner, which is what `default` methods soften.
- [ ] I know DIP requires the *high-level module to own the interface*, and I use the "which deletes to compile" test.
- [ ] I can explain the fragile base class via `HashSet.addAll` calling `add`.
- [ ] I know DRY is about duplicated knowledge, and that deduplicating across bounded contexts is the worst case.
- [ ] I can state why a wrong abstraction costs more than duplication.
- [ ] I can explain why an anemic model cannot enforce invariants, and when it is still a defensible choice.
- [ ] I can name the mechanism of harm for god object, circular dependency, primitive obsession, feature envy, and leaky abstraction.
- [ ] I know Hyrum's law and can give a leaky-abstraction example from JPA or caching.
- [ ] I know why package-by-feature wins: Java's access modifiers are package-scoped, so the compiler polices the boundary.
- [ ] I can define port and adapter precisely, including which side owns the interface.
- [ ] I know the mechanical test for real hexagonal: no framework dependency in the domain module's build file.
- [ ] I can distinguish entity, value object, aggregate, repository, domain service, application service, and domain event.
- [ ] I know an aggregate's boundary is its transactional invariant set, that aggregates reference each other by ID, and that it is the optimistic-locking unit.
- [ ] I know bounded contexts integrate by translation, not by sharing a type.
- [ ] I can explain CQRS projection lag and a read-your-writes mitigation with a number attached.
- [ ] I know event sourcing's costs: snapshotting, event versioning/upcasting, GDPR erasure, mandatory projections.
- [ ] I know event-driven communication and event sourcing are independent decisions.
- [ ] I can do the monolith-vs-microservices arithmetic: 10 ns vs 0.5 ms, multiplied availability, saga instead of ACID, N× ops surface.
- [ ] I can diagnose a distributed monolith, with shared database as the definitive tell.
- [ ] I know the failure each resilience pattern was invented for, and that retry/timeout/breaker must be tuned as one policy.
- [ ] I know an unbounded queue converts backpressure into an OOM.
- [ ] I know a circuit breaker without a defined open-state response only makes failure faster.
- [ ] I know an idempotency key is enforced by a unique index, not by check-then-insert.
- [ ] For each refactoring I can name the smell, the smallest safe move, and the test that protects it.
- [ ] I never change behaviour and structure in the same commit.
- [ ] I answer "which pattern" as force → stable thing → seam location → cost.
- [ ] I can reject a pattern out loud, and I can name the trigger that would make me adopt it later.
