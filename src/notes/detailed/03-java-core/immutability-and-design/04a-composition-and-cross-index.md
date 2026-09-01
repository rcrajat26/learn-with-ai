# 03 Java Core — Immutability and design — Composition, the small mandates, and where the idioms are over-applied — INTERMEDIATE (§2.14, 2.14.6–2.14.12)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Design idioms the interview expects](04-design-idioms.md) · Next: [Which construct do I reach for](05-which-construct.md)

---

[04-design-idioms.md](04-design-idioms.md) settled the constructive idioms: static factories against constructors, the builder against the telescoping constructor, the four ways to write a singleton, double-checked locking, and the non-instantiable utility class. It deliberately left two threads hanging — the question of *when each of those idioms is the wrong tool*, and the observation that a singleton and a hand-injected single instance are answers to different questions. This file picks both up. Between them sit the coupling rules: dependency injection, composition and the forwarding class, the six small mandates that are all secretly about coupling, primitives against boxes, and a cross-index into *Effective Java* so the vocabulary lines up with the book an interviewer is quoting from. Measured figures quoted here come from **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**; the forwarding-class outputs below were compiled and run on that build in a scratch directory under `/tmp/`.

---

## 1. Dependency injection over hardwired resources (2.14.6) `[X-REF 07]`

`[X-REF 07]` — Dependency injection is not Spring, and it is not a framework feature at all. It is a **statement about who chooses a collaborator**. A class whose body contains `new PostgresFundsLedger()` has made that choice itself, permanently, on behalf of every caller it will ever have; a class that takes a `FundsLedger` as a constructor parameter has moved the choice out to whoever assembles the object. Everything DI is credited with — testability, swappable rails, honest documentation — is a consequence of that single relocation, and none of it requires a container.

### Why it exists

A hardwired collaborator is an invisible parameter. `PaymentService` that constructs its own `PostgresFundsLedger` has a dependency on Postgres that appears nowhere in its API: not in its constructor signature, not in its method signatures, not in its javadoc. The only way to discover it is to read the method bodies, and the only way to change it is to edit them. That is the same defect [04-design-idioms.md](04-design-idioms.md) §2 diagnosed in JavaBeans setters — a class whose real contract is not visible in its declared shape — arriving from a different direction. The second reason is that hardwiring destroys the substitutability the type system was already offering. `FundsLedger` as an interface is worth nothing if every consumer instantiates a specific implementation of it internally; the abstraction exists but nobody can supply a different value for it.

### When to reach for it, and when not

Reach for constructor injection for every collaborator that is a **service** — something with behaviour, an out-of-process dependency, or a policy that might differ between environments. Do not inject values that are genuinely part of the object's identity: a `Money` amount, a `ClientId`, an `IdempotencyKey` are data, passed as method arguments or constructor state, not dependencies to be resolved. Do not reach for a container below a few dozen objects. Plain constructor injection assembled by hand — in `main`, in a factory method, in a test's setup — is the whole idiom, and it is what most of the JDK does: `InputStreamReader` takes the `InputStream` it decodes rather than opening a file itself, `PriorityQueue` takes the `Comparator` rather than fixing an ordering. That is dependency injection with no annotations anywhere. Three limits worth stating out loud, because a candidate who names them separates from one who recites "testability":

- **A constructor with eight dependencies is a design report, not a DI problem.** It is telling you the class does eight things. DI made the eight visible; it did not reduce them. The fix is to split the class, not to hide the parameters behind field injection.
- **Field injection defeats immutability.** A `@Autowired` field cannot be `final`, so the object exists in a legally-constructed but not-yet-usable state between `new` and the injection — the exact "constructed but not valid" window [04-design-idioms.md](04-design-idioms.md) §2 rejected for setters. Constructor injection has no such window: if the object exists, its dependencies are present, and [02-immutability.md](02-immutability.md)'s rule 2 (private final fields) still holds.
- **Service-locator lookup is DI's opposite wearing its clothes.** `FundsLedger ledger = ServiceRegistry.lookup(FundsLedger.class)` inside a method body has not moved the choice out; the class still chooses, it just chooses indirectly, and the dependency is once again invisible in the signature.

**The singleton thread, closed.** [04-design-idioms.md](04-design-idioms.md) §3 left this open: **a singleton is usually a DI problem wearing a static field.** Two claims get conflated. "There is exactly one instance of this in the process" is often a genuine requirement — one connection pool, one `FundsLedger` client. "It is reachable from anywhere by a static field" is a separate, additional claim, and it is the one that causes the damage: it makes every consumer's dependency on it invisible, it makes substitution in a test impossible without static mutation, and it makes initialization order a global concern. A single instance created once in `main` (or by a container's default singleton scope) and passed into the three classes that need it satisfies the first claim and declines the second.

### How it works

Mechanically there is nothing to it: a `final` field, assigned in the constructor from a parameter, typed as the interface. The interesting part is what that does to the class's *set of possible collaborators*, which becomes "every implementation of the interface, present and future" instead of "the one named in the body".

### Diagram

No `D-NNN` is assigned to this concept. The picture worth having is the class-shape one — a constructor signature as the class's declared dependency list — and it is a signature, not a figure: the two code blocks below carry it directly.

### A concrete example

The hardwired version, and the injected one, differing in exactly two lines:

```java
public interface FundsLedger {
    void append(LedgerEntry entry);
    Money availableCash(ClientId clientId);
}

// Hardwired: PaymentService has chosen Postgres on behalf of every caller.
public final class HardwiredPaymentService {
    private final FundsLedger ledger = new PostgresFundsLedger("jdbc:postgresql://ledger/quizstakes");

    public void reserve(ClientId clientId, Money stake) {
        if (ledger.availableCash(clientId).compareTo(stake) < 0) {
            throw new InsufficientFundsException(clientId, ledger.availableCash(clientId), stake);
        }
        ledger.append(new LedgerEntry("CLIENT_CASH_RESERVED", stake));
    }
}

// Injected: the choice belongs to whoever assembles PaymentService.
public final class PaymentService {
    private final FundsLedger ledger;

    public PaymentService(FundsLedger ledger) {
        this.ledger = Objects.requireNonNull(ledger, "ledger must not be null");
    }

    public void reserve(ClientId clientId, Money stake) {
        Money available = ledger.availableCash(clientId);
        if (available.compareTo(stake) < 0) {
            throw new InsufficientFundsException(clientId, available, stake);
        }
        ledger.append(new LedgerEntry("CLIENT_CASH_RESERVED", stake));
    }
}
```

Assembled by hand, no container in sight:

```java
public final class QuizStakesAssembly {
    public static PaymentService paymentService() {
        return new PaymentService(new PostgresFundsLedger("jdbc:postgresql://ledger/quizstakes"));
    }

    public static PaymentService paymentServiceForTest(Map<ClientId, Money> balances) {
        return new PaymentService(new InMemoryFundsLedger(balances));
    }
}
```

Three specific things the second version buys, as capabilities rather than slogans. First, `paymentServiceForTest` runs with **no database, no Spring context, no `@MockBean`** — an in-memory `FundsLedger` seeded with the balances the test cares about, in one line; the seam exists because of the constructor parameter, not because of a testing library (guide 16 owns the test-double taxonomy). Second, the card and bank rails share the class: two `FundsLedger` implementations, one `PaymentService`, no subclass and no `if (rail == CARD)` in the method body. Third, `new PaymentService(FundsLedger)` **is** the dependency list — one line tells a reader what the class touches, which no number of `new` calls buried in method bodies ever does. Note also that the hardwired version calls `ledger.availableCash(clientId)` twice, once for the comparison and once for the exception, which the injected version fixes with a local. That is not cosmetic: two calls to a remote ledger can return different values, so the exception can report a balance that never failed the check. Hardwiring tends to come with that class of sloppiness, because a collaborator you did not have to declare feels free.

### The gotcha

**Pitfall:** believing that annotating fields with `@Autowired` is what makes a class dependency-injected. Symptom: the class cannot be instantiated at all outside a Spring context — `new PaymentService()` compiles and returns an object whose `ledger` field is null, so every unit test either boots a context or reaches for reflection to poke the field. The class is *container-coupled*, which is strictly worse than being Postgres-coupled, because at least Postgres was replaceable. Fix: constructor injection with `final` fields. Spring binds a single-constructor class with no annotation at all since Spring 4.3, so the framework coupling drops to zero and the class remains a plain Java object that `new` can build. Guide 07 (Spring core) owns the container, its scopes and its resolution rules.

> **Definition.** Dependency injection is the discipline of taking a collaborator as a constructor parameter typed to its interface rather than instantiating or looking it up inside the class, so that the choice of implementation belongs to the code that assembles the object; a container automates the assembly but is no part of the idiom.

---

## 2. Composition and delegation over inheritance: the forwarding class (2.14.7) `[X-REF 02]`

`[X-REF 02]` — `extends` is the tightest coupling the Java language offers, and the reason is precise and usually mis-stated. A subclass does not depend on its superclass's **contract**; it depends on its superclass's **self-use pattern** — which of its own public methods each public method happens to call internally. That pattern is an implementation detail. No javadoc is obliged to record it, no compiler checks it, and every release is free to change it. A subclass that overrides a method is silently betting on a fact it cannot see and was never promised.

### Why it exists

Interface inheritance is safe because an interface has no implementation to have a self-use pattern. Implementation inheritance is unsafe because the superclass's internal call graph becomes part of the subclass's correctness argument. The canonical demonstration is a counter, and it is worth running rather than describing, because the interesting part is that the *same* wrapper code produces two different wrong answers over two different superclasses. A counting collection that overrides both `add` and `addAll` — the obvious, careful thing to write, since you want both entry points counted — behaves like this on JDK 21.0.7:

```java
static class CountingLedgerEntrySet extends HashSet<LedgerEntry> {
    private int appended = 0;

    @Override public boolean add(LedgerEntry e) {
        appended++;
        return super.add(e);
    }

    @Override public boolean addAll(Collection<? extends LedgerEntry> c) {
        appended += c.size();
        return super.addAll(c);
    }

    public int appended() { return appended; }
}
```

A second class, `CountingLedgerEntryArrayList`, is byte-for-byte the same declaration with `extends HashSet<LedgerEntry>` replaced by `extends ArrayList<LedgerEntry>` — nothing else differs, not a field, not a method body. Measured, adding one `List.of` of three ledger entries (`CLIENT_CASH_AVAILABLE:420`, `CLIENT_BONUS_AVAILABLE:33`, `HOUSE_REVENUE:300`) to each with a single `addAll` call:

```
extends HashSet   : size=3 appended=6
extends ArrayList : size=3 appended=3
```

`HashSet` counts **6** for three entries. `ArrayList`, from identical wrapper code, counts **3** — correctly, by luck. The mechanism is entirely in the superclasses: `HashSet` does not override `addAll`, so it inherits `AbstractCollection.addAll`, which loops calling `add(e)` — and `add` is overridden, so each element is counted twice, once by `addAll`'s `c.size()` and once by the delegated `add`. `ArrayList` **does** override `addAll`, and its implementation copies in bulk with `System.arraycopy` rather than calling `add` at all, so only `c.size()` counts.

**Insight:** neither number is a bug in `HashSet` or in `ArrayList`. Both superclasses are behaving as documented. The bug is that the subclass's correctness depends on which of two undocumented internal strategies its superclass happens to use — and the direction of the error flips with the superclass. A JDK release that changed `AbstractCollection.addAll` to a bulk path, or `ArrayList.addAll` to a loop over `add`, would silently change the answer of code that had not been edited. That is the **fragile base class** problem; `../inheritance-and-dispatch/01-basics.md` owns it in full and carries **D-046**, the picture of exactly this dependency.

### When to reach for it, and when not

The decision rule, stated so a reviewer can apply it without judgement calls: **inherit only when the subclass is genuinely a subtype in the substitution sense *and* the superclass was designed for inheritance and documents its self-use. Compose in every other case.** Both halves are required. `AbstractList` passes — it exists to be extended and its javadoc states which methods call which. `ArrayList` fails the second half: it is a concrete class with no documented self-use pattern, so extending it is a bet. The counter-case for composition: do not compose when the wrapper would have to forward a large interface *and* the concrete type is genuinely fixed and your own — a `sealed` hierarchy you control, where every subclass is in the same file and the self-use pattern is visible at a glance, is a legitimate place to inherit. The three options, compared:

| Option | Coupling | What breaks on a superclass change | Verbosity | SELF problem |
|---|---|---|---|---|
| `extends` a concrete class (`ArrayList`, `HashSet`) | Tightest — depends on the superclass's undocumented internal call graph | Overridden methods can be called a different number of times, or stop being called; new superclass methods bypass your override entirely | Lowest — inherit everything, override two methods | No — `this` really is the object |
| `extends` an abstract class designed for it (`AbstractList`) | Tight, but on a *documented* self-use pattern | Only a documented change breaks you, which is a breaking change the JDK would announce | Low — implement `get`/`size`, inherit the rest | No |
| Compose and forward | Loosest — depends only on the interface | Nothing. A new implementation of the interface is a constructor argument, not a recompile | Highest — every interface method needs a one-line forwarder | **Yes** |

### How it works

The forwarding class holds the delegate as a private field, implements the interface, and forwards every method as a one-liner. The counting behaviour then extends the *forwarding class*, not the collection. What that buys is exact: the forwarding class's self-use pattern is **trivial and stable by construction** — every method forwards exactly once to the delegate and calls no other method of the wrapper — so an override of `add` can never be reached from `addAll`, and no future change to `ArrayList` or `HashSet` can reach the counter at all. The wrapper's dependency is on `List`, the interface, so the same wrapper works over `ArrayList`, `LinkedList`, the result of `List.copyOf`, or an implementation that does not exist yet. That is the whole payoff, and it costs one line per interface method.

### Diagram

No `D-NNN` is assigned to this file. The picture this section needs is **D-046**, the fragile base class, and it is owned by `../inheritance-and-dispatch/01-basics.md` — go there rather than reading a second rendering of the same dependency here. The measured `appended=6` against `appended=3` above is the same fact in numbers.

### A concrete example

The complete forwarding class, every method of `List<LedgerEntry>` present, plus the default methods forwarded deliberately rather than inherited — because `Collection`'s defaults (`stream`, `removeIf`, `forEach`, `spliterator`) would otherwise be computed over the *wrapper's* iterator rather than the delegate's optimised implementation, losing the delegate's `Spliterator` characteristics:

```java
public class ForwardingLedgerEntryList implements List<LedgerEntry> {
    private final List<LedgerEntry> delegate;

    public ForwardingLedgerEntryList(List<LedgerEntry> delegate) {
        this.delegate = Objects.requireNonNull(delegate, "delegate must not be null");
    }

    public int size() { return delegate.size(); }
    public boolean isEmpty() { return delegate.isEmpty(); }
    public boolean contains(Object o) { return delegate.contains(o); }
    public Iterator<LedgerEntry> iterator() { return delegate.iterator(); }
    public Object[] toArray() { return delegate.toArray(); }
    public <T> T[] toArray(T[] a) { return delegate.toArray(a); }
    public boolean add(LedgerEntry e) { return delegate.add(e); }
    public boolean remove(Object o) { return delegate.remove(o); }
    public boolean containsAll(Collection<?> c) { return delegate.containsAll(c); }
    public boolean addAll(Collection<? extends LedgerEntry> c) { return delegate.addAll(c); }
    public boolean addAll(int index, Collection<? extends LedgerEntry> c) { return delegate.addAll(index, c); }
    public boolean removeAll(Collection<?> c) { return delegate.removeAll(c); }
    public boolean retainAll(Collection<?> c) { return delegate.retainAll(c); }
    public void replaceAll(UnaryOperator<LedgerEntry> op) { delegate.replaceAll(op); }
    public void sort(Comparator<? super LedgerEntry> c) { delegate.sort(c); }
    public void clear() { delegate.clear(); }
    public LedgerEntry get(int index) { return delegate.get(index); }
    public LedgerEntry set(int index, LedgerEntry element) { return delegate.set(index, element); }
    public void add(int index, LedgerEntry element) { delegate.add(index, element); }
    public LedgerEntry remove(int index) { return delegate.remove(index); }
    public int indexOf(Object o) { return delegate.indexOf(o); }
    public int lastIndexOf(Object o) { return delegate.lastIndexOf(o); }
    public ListIterator<LedgerEntry> listIterator() { return delegate.listIterator(); }
    public ListIterator<LedgerEntry> listIterator(int index) { return delegate.listIterator(index); }
    public List<LedgerEntry> subList(int from, int to) { return delegate.subList(from, to); }
    public boolean removeIf(Predicate<? super LedgerEntry> filter) { return delegate.removeIf(filter); }
    public Spliterator<LedgerEntry> spliterator() { return delegate.spliterator(); }
    public Stream<LedgerEntry> stream() { return delegate.stream(); }
    public Stream<LedgerEntry> parallelStream() { return delegate.parallelStream(); }
    public void forEach(Consumer<? super LedgerEntry> action) { delegate.forEach(action); }

    @Override public boolean equals(Object o) { return o == this || delegate.equals(o); }
    @Override public int hashCode() { return delegate.hashCode(); }
    @Override public String toString() { return delegate.toString(); }
}

public final class CountingLedgerEntryList extends ForwardingLedgerEntryList {
    private int appended = 0;

    public CountingLedgerEntryList(List<LedgerEntry> delegate) { super(delegate); }

    @Override public boolean add(LedgerEntry e) {
        appended++;
        return super.add(e);
    }

    @Override public boolean addAll(Collection<? extends LedgerEntry> c) {
        appended += c.size();
        return super.addAll(c);
    }

    public int appended() { return appended; }
}
```

Measured on JDK 21.0.7, the same three entries via `addAll` over an `ArrayList` delegate, and then over a `LinkedList` delegate with one further single `add`:

```
forwarding wrapper: size=3 appended=3
same wrapper over LinkedList: size=4 appended=4
```

Both correct, and correct for the same reason rather than by luck. Swapping `ArrayList` for `LinkedList` — two collections whose `addAll` implementations differ — changed nothing, because the wrapper never depended on either implementation. `equals` is worth its own line: `o == this || delegate.equals(o)` keeps the wrapper equal to any `List` with the same contents, which is what `List`'s own `equals` contract requires — a `List` equals any other `List` with equal elements in the same order, regardless of class. `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` owns the contract; guide 02 owns the collections API and the `AbstractList` alternative to writing all of the above by hand.

### The gotcha

**Pitfall:** believing the forwarding wrapper is transparent. It is not, and there are exactly two places it leaks.

The first is the **SELF problem**. If the delegate ever hands out `this` — registering itself as a listener, passing itself to a callback, returning itself from a builder-style method — the recipient holds the *delegate*, not the wrapper, and every call it makes bypasses the counter entirely. The wrapper is invisible to anything that obtained a reference from inside the delegate. Symptom: a counter that reads low, or a validating wrapper that lets through exactly the writes that arrive through a callback. There is no fix within the idiom; the delegate must not publish `this`, which is a property of the delegate you have to verify.

The second is **type identity**. `instanceof ArrayList` is false for the wrapper, `getClass()` returns the wrapper class, and any code that reflects over the concrete type — a serializer keyed on class name, a framework that special-cases `ArrayList` for a fast path — sees something it does not recognise. `../reflection/02-reflection.md` and `../serialization/02-serialization.md` own those two consumers. Fix: neither leak is a reason to inherit instead; both are reasons to check what the delegate and the surrounding framework do before wrapping.

> **Definition.** Composition with delegation replaces `extends C` with a private field of type `I` — the interface `C` implements — and a forwarding method per interface method, so the wrapper's correctness depends only on the interface's documented contract rather than on the superclass's undocumented self-use pattern; the forwarding class is the reusable half of that pattern, and the SELF problem and concrete-type identity are its two genuine limits.

---

## 3. The small mandates, which are all about coupling (2.14.8, 2.14.10)

Six rules that read like style advice and are not. Every one of them is about limiting what a caller can come to depend on, which is the same subject as §§1 and 2 at a smaller grain: an accessible member, a concrete return type, a `null` return and an undocumented thread-safety property are all things callers will build on if you let them, and cannot be withdrawn afterwards.

### Why it exists

The cost of a decision in an API is not paid when it is made; it is paid when it has to be reversed. Each of these six mandates is a cheap decision now that prevents an expensive reversal later, and each has a specific failure mode rather than a general appeal to tidiness.

### When to reach for it, and when not

All six are defaults, not absolutes, and two of them have real exceptions that a careless reading loses. Those exceptions are stated inline below rather than as a footnote, because reciting the rule without its exception is how "program to interfaces" turns into discarding the guarantee you chose a type for.

### How it works

| Mandate | What a caller can otherwise come to depend on | Failure mode if you skip it | The default, and its exception |
|---|---|---|---|
| Program to interfaces | Operations specific to the concrete type | The implementation cannot be swapped without breaking callers | Declare the interface — unless the concrete type's *specific* guarantee is why you chose it (`Deque`, `LinkedHashMap`) |
| Minimise accessibility | Every accessible member, permanently | A change that should have been local becomes a breaking change | `private`, widened one level at a time, each widening with a reason |
| Make classes immutable when you can | Nothing — there is no mutator to depend on | Aliasing and thread-safety bugs; [02-immutability.md](02-immutability.md) owns the five rules and the copy ordering, [02a-shallow-deep-and-building-blocks.md](02a-shallow-deep-and-building-blocks.md) the shallow-versus-deep question | Immutable unless identity or size genuinely changes over time |
| Return empty collections, not `null` | A `null` return the compiler cannot check for you | One missing branch out of many is a production `NullPointerException` | `List.of()` — never `null`, never `Optional<List<…>>` |
| Validate parameters | An unchecked argument reaching a stored field | The NPE surfaces frames deeper, naming no argument | `Objects.requireNonNull` at every public boundary; private helpers may skip |
| Document thread safety | Whatever the caller guessed, in either direction | Redundant synchronization, or a shipped race | State one of the four categories below, in the javadoc |

**Program to interfaces.** Declare the variable, the parameter and — most importantly — the return type as `List`, `Map`, `FundsLedger`, not `ArrayList`, `HashMap`, `PostgresFundsLedger`. The mechanism is that a declared type is the set of operations a caller may use, so a concrete declared type silently permits `ArrayList`-specific calls that make the implementation unswappable. `Movement.entries()` returning `List<LedgerEntry>` can switch from `List.copyOf` to an immutable `record`-backed view without touching a caller; returning `ArrayList<LedgerEntry>` cannot. **The exception, spelled out:** `ArrayDeque` declared as `Deque` is fine; declared as `Collection` it is not, because the stack semantics were the reason. `LinkedHashMap` declared as `LinkedHashMap` (or documented as insertion-ordered) is correct when the iteration order is load-bearing — declaring it `Map` throws away the property you selected it for and invites a future maintainer to swap in `HashMap`.

**Minimise accessibility.** Every accessible member is a promise you cannot withdraw without breaking a caller, so the mechanism is simply that accessibility decides whether a future change is local or breaking. **Package-private is the underused one:** it gives a whole package internal cohesion — `PaymentService` reaching a package-private `LedgerWriter` directly — while exposing nothing to any other module or team. `protected` is the one to be most suspicious of, because it is a commitment to subclasses about internals, which is §2's self-use pattern made permanent. `../classes-and-initialization/02a-access-and-other-modifiers.md` owns the four levels in full and carries **D-041**.

| Access level | Who can see it | When to reach for it | What it commits you to |
|---|---|---|---|
| `private` | This top-level class and its nested classes | Every member, by default | Nothing outside the one file |
| package-private (no modifier) | This package only | Cohesion inside a package — one class calling a helper the outside world must not see | Every class in the package, which is a team-sized audience |
| `protected` | This package, plus every subclass anywhere | Only a class designed *and documented* for inheritance | A permanent promise about internals to subclasses you will never see |
| `public` | Everywhere the module exports the type to | A genuine API surface, decided deliberately | Every caller, in every future version, forever |

**Return empty collections, not nulls.** The mechanism, not the manners: a `null` return makes **every** call site carry a branch that the type system does not require and the compiler will not check, and exactly one missing branch is a production `NullPointerException`. There is no cost argument on the other side, because `List.of()` allocates nothing — it returns the shared `ImmutableCollections.EMPTY_LIST` instance — and neither does `Collections.emptyList()`, which returns its own shared `EMPTY_LIST`. Use **`List.of()`** in new code: it is the modern spelling and its result is genuinely immutable rather than an unmodifiable view. Do not reach for `Optional<List<LedgerEntry>>` — `Optional` models a *single* absent value, and an `Optional` wrapping a collection gives a caller two ways to spell "nothing" (`Optional.empty()` and an empty list) where the empty list already had one. `../null-discipline/02-null-discipline.md` owns `Optional` and where it belongs.

**Validate parameters.** `Objects.requireNonNull(clientId, "clientId must not be null")` at the top of every public method and every constructor that stores the reference. The mechanism is locality: without the check, the null surfaces as an NPE several frames deeper, at whichever dereference happens first, with no indication of which of the method's arguments was wrong. `Objects.requireNonNull` returns its argument, so it composes into a field assignment; `Objects.checkIndex(index, length)` is the same idea for bounds, throwing an `IndexOutOfBoundsException` that names both the index and the bound. A **private** method may reasonably skip the check, because all its callers are in the same file and are already covered by the public boundary's checks — and a codebase that opens every private helper with five `requireNonNull` calls trains readers to skip past all of them, including the one that mattered. `../exceptions/02b-designing-an-exception-hierarchy.md` §3 owns the API in full. The tie-back worth making: [02-immutability.md](02-immutability.md) §3's ordering — **null check, then defensive copy, then validity check on the copy** — is this rule composed with the TOCTOU rule, and the ordering is why the constructor's postcondition is a guarantee rather than a wish.

**Document thread safety.** Thread safety is the one property a caller **cannot** determine by reading the class — not from its signatures, not from its name, and not reliably from its body, since safety depends on the object graph it reaches. An undocumented class is therefore assumed unsafe by careful callers, who add synchronization that may be redundant, and assumed safe by careless ones, who do not. The case where the documentation is the entire difference between correct and silently-wrong code is `SimpleDateFormat` against `DateTimeFormatter`: `SimpleDateFormat` is mutable and not thread-safe, and shared as a `static` field it produces wrong dates rather than an exception; `DateTimeFormatter` is documented immutable and thread-safe and is designed to be a `static final` constant. `../date-and-time/02-date-and-time.md` owns `java.time`; guide 05 owns the concurrency vocabulary.

| Category | What the class promises | What a caller may assume | Example |
|---|---|---|---|
| Immutable | No observable state changes after construction | No synchronization, ever; publish and share freely, `static final` included | `DateTimeFormatter`, `String`, `List.of(…)`; `ClientRestrictions` below |
| Thread-safe | Every individual method is safe under concurrent use | Nothing to lock for a single call — but a **compound** operation still needs external locking or an atomic method | `ConcurrentHashMap`, `AtomicLong` |
| Conditionally thread-safe | Safe except for named sequences, which the javadoc must name | Safe per call; must hold the documented lock for the documented sequence | `Collections.synchronizedList` — iteration must hold the returned list's monitor |
| Not thread-safe | Nothing at all; the caller synchronizes or confines | Confine to one thread, or guard every access externally | `SimpleDateFormat`, `ArrayList`; `BoxedLedgerIndex` in §4 |

### Diagram

No `D-NNN` here. The adjacent picture is **D-041**, the access-modifier reachability matrix, owned by `../classes-and-initialization/02a-access-and-other-modifiers.md` — the right place for the accessibility mandate's figure.

### A concrete example

Four of the six mandates in one method — with the copy-depth decision made explicitly, because the obvious first draft of this class has a javadoc that lies:

```java
public record Restriction(RestrictionType type, RestrictionState state, Instant appliedAt) { }
public record RestrictionKey(ClientId clientId, RestrictionType type) { }

public final class ClientRestrictions {
    private final Map<RestrictionKey, Restriction> byKey;                // private, minimised

    public ClientRestrictions(Map<RestrictionKey, Restriction> byKey) {
        Objects.requireNonNull(byKey, "byKey must not be null");         // validate
        this.byKey = Map.copyOf(byKey);            // shallow — and deep enough, see below
    }

    /**
     * Active restrictions for a client, never null.
     * <p>This class is immutable and therefore thread-safe: {@code Map.copyOf} returns an
     * immutable map and every value is a record over immutable components, so nothing
     * reachable from the field can be mutated by anyone, the caller included.
     */
    public List<Restriction> activeFor(ClientId clientId) {              // interface return type
        Objects.requireNonNull(clientId, "clientId must not be null");
        return byKey.entrySet().stream()
                .filter(e -> e.getKey().clientId().equals(clientId))
                .map(Map.Entry::getValue)
                .filter(r -> r.state() == RestrictionState.ACTIVE)
                .toList();                                               // empty, not null
    }
}
```

**The copy-depth decision, stated rather than buried.** The first draft of this class held a `Map<ClientId, List<Restriction>>` and copied it with `Map.copyOf` — and its "immutable and therefore thread-safe" javadoc was **false**, because `Map.copyOf` is *shallow*: it copies the entries, not the objects they point at, so the caller's `List<Restriction>` values stayed aliased and stayed mutable, and the caller could add a restriction to an "immutable" object after construction. Two ways out. Deepen the copy — `List.copyOf` every value on the way in, and the javadoc then has to say which layers are guaranteed. Or remove the mutability, so the shallow copy is deep enough: that is the version above, one immutable `Restriction` per `RestrictionKey`, whose components are two enums and an `Instant`, all immutable, leaving nothing for a shallow copy to miss. The second is chosen because it makes the javadoc unconditionally true, and a caller can still write `for (Restriction r : restrictions.activeFor(clientId))` with no null branch. Match the copy depth to the mutability depth, or delete the mutability; [02a-shallow-deep-and-building-blocks.md](02a-shallow-deep-and-building-blocks.md) owns that argument and the `Map.copyOf` trap in full.

### The gotcha

**Pitfall:** returning `Collections.emptyList()` from a method whose declared return type is `List<Restriction>` and then treating the result as mutable somewhere upstream. Symptom: `UnsupportedOperationException` at a call site that worked for every non-empty result and fails only for clients with no restrictions — the worst possible distribution of a bug, because the failing path is the rare one. The fix is not to go back to returning `null`; it is to make the *contract* uniform, returning an immutable list in every case (`.toList()` above returns an unmodifiable list, so both branches agree) and documenting it. A method that returns a mutable list sometimes and an immutable one otherwise has a type that lies about it either way.

> **Definition.** The six small mandates — program to interfaces, minimise accessibility, prefer immutability, return empty collections rather than `null`, validate parameters at public boundaries, and document the thread-safety category — are all instances of one rule: expose the smallest surface a caller can build on, because everything exposed becomes a commitment and everything undocumented becomes a guess.

---

## 4. Primitives over boxes, and unnecessary objects (2.14.9) `[NUM]`

`[NUM]` — A `long` is eight bytes of value. A `Long` is an object: a header, the same eight bytes of value, alignment padding, and a reference somewhere pointing at it. The interesting part is that the memory arithmetic and the *time* arithmetic point in opposite directions on a modern JVM, and a candidate who quotes only one of them is repeating folklore.

### Why it exists

Generics cannot hold primitives before Valhalla, so any collection of numbers is a collection of boxes. At QuizStakes's ledger volumes that choice is a real memory decision, and knowing which part of the cost is real is the difference between a justified `long[]` and a superstitious one.

### When to reach for it, and when not

Reach for the primitive whenever the value is a value: local variables, fields, method parameters, arrays, and `IntStream`/`LongStream` over `Stream<Integer>`/`Stream<Long>`. Reach for the box only where the language forces it — a type argument, a `null` that means "absent", a `Map` key. `../wrappers-and-boxing/01-basics.md` owns the boxing rules and carries **D-028**, `Integer` versus `int` in bulk, which is this section's picture. Do not extend the rule to "avoid allocating small objects": that version costs readability for nothing, as the time arithmetic below shows.

### How it works

**The memory arithmetic, worked.** Under compressed oops on JDK 21 (`UseCompressedOops = true`, ergonomic default on this build): the object header is 12 bytes — an 8-byte mark word plus a 4-byte compressed class pointer — a reference field is 4 bytes, and every object's size rounds up to a multiple of 8 (`ObjectAlignmentInBytes = 8`). **The array header derives from those, it is not a separate fact:** an array is an object, so it carries the same 12-byte header, plus a 4-byte `int length` field, giving **16 bytes** — already a multiple of 8, so alignment adds no padding on top. `../objects-equality-and-lifecycle/05-internals-object-layout.md` owns object layout, measured on this build; this section only consumes its numbers.

A single `Long` holding a ledger-entry id:

```
header                12 bytes
long value             8 bytes
                      --------
                      20 bytes -> rounds up to 24 bytes
plus the reference in the backing array   4 bytes
                      --------
total per element     28 bytes
```

Against 8 bytes per element in a `long[]`. That is **28 / 8 = 3.5x**. Scaled to the 1024-element window the cost harness in `../cost-model/02-master-cost-table.md` uses:

```
long[1024]        : 16 (array header) + 1024 * 8  =  8,208 bytes  ~=  8.0 KB
List<Long>, 1024  : 16 + 1024 * 4 (references)    =  4,112 bytes
                  + 1024 * 24 (Long objects)      = 24,576 bytes
                                                  = 28,688 bytes  ~= 28.0 KB
```

28,688 / 8,208 = **3.50x**, the same ratio, as it must be once the array headers wash out. Scaled to a day of ledger entries — 19.8M/day — holding one `long` id each:

```
long[19,800,000]        : 19,800,000 * 8  = 158,400,000 bytes ~= 158 MB
List<Long>, 19.8M       : 19,800,000 * 28 = 554,400,000 bytes ~= 554 MB
difference                                = 396,000,000 bytes ~= 396 MB
```

**The cost the arithmetic misses, and it usually matters more.** A `long[]` is one contiguous run of memory: a scan touches consecutive cache lines and the hardware prefetcher predicts it perfectly. A `Long[]` (or a `List<Long>`'s backing array) is an array of *pointers* to 24-byte objects that were allocated at different times and sit at scattered addresses. Scanning it dereferences a pointer per element, and each dereference is a candidate cache miss. The 3.5x is the number you can compute; the indirection is the effect you have to measure, so it was measured — summing every element of a `long[]` against a `Long[]` of the same length on JDK 21.0.7, warmed, three agreeing runs, with the boxed array's references shuffled so the objects are not visited in allocation order. The `long[]` scan cost **0.207–0.227 ns/element at every length tested**, flat, because it is one contiguous run the prefetcher predicts perfectly. The `Long[]` scan cost **0.219 ns/element at 1,024 elements (1.06x — indistinguishable, because the references and all 1,024 `Long` objects fit in cache together), 0.80–0.90 ns at 1M (3.6–4.0x), and 3.15 ns at 8M elements (13.9x)**. So the claim is true but conditional, and the condition is the one worth carrying: **the indirection costs nothing while the working set fits in cache and dominates once it does not** — at a day's ledger volume it is a 13.9x scan penalty, four times larger than the 3.5x the byte arithmetic predicts. Harness shape as in `../cost-model/02-master-cost-table.md`: not JMH, a `volatile` sink, warmup then a timed loop, so the ratios within a run are meaningful and the absolute figures are not portable.

**The honest correction, quoted from measurement.** On JDK 21.0.7, a boxing round-trip in a tight loop where the box **does not escape** measured **0.312 ns**, and **2.512 ns** with `-XX:-DoEscapeAnalysis`. Both figures are from `../cost-model/02-master-cost-table.md`, which owns the harness and its caveats; `../wrappers-and-boxing/01g-the-cost-of-boxing.md` owns the boxing chapter. Read what those two numbers say: with escape analysis on — the default, `DoEscapeAnalysis = true` and `EliminateAllocations = true` on this build — C2 proved the `Integer` could not be observed outside the method and removed the allocation entirely, leaving a figure at the harness floor. **"Boxing is expensive" is a claim about *escaping* boxes, not about `Integer.valueOf` appearing in your source.** The same table records that in-cache and out-of-cache boxing measured indistinguishably for exactly this reason: the allocation the cache would have saved did not happen either way. **Unverified:** C2 documents no guarantee about when escape analysis or scalar replacement applies, so this is a measurement of one build's behaviour on one shape of loop, not a rule you can rely on for a specific method.

**Avoid creating unnecessary objects, correctly bounded.** The version worth keeping is about objects that are **expensive to create** or **long-lived**, not about small short-lived ones. The standing example is a `Pattern` recompiled on every call:

```java
// Wrong: compiles the regex on every invocation.
public static boolean isValidCoupon(String couponCode) {
    return couponCode.matches("[A-Z]{4}-[0-9]{4}");
}

// Right: compile once, reuse forever. Pattern is immutable and thread-safe.
public final class CouponCodes {
    private static final Pattern VALID = Pattern.compile("[A-Z]{4}-[0-9]{4}");

    public static boolean isValidCoupon(String couponCode) {
        return VALID.matcher(couponCode).matches();
    }
}
```

`String.matches` calls `Pattern.matches`, which compiles the pattern and throws it away, every call. The `Pattern` escapes into a `static final` field in the second version, so nothing can eliminate it — and nothing needs to, because it is created once. `../strings/02-performance-and-text.md` owns `String` and regex performance. Note that `Matcher` is *not* thread-safe and must not be hoisted alongside the `Pattern`; a fresh `matcher` per call is a small, short-lived object, which is exactly the kind this rule does not ask you to avoid.

**When object pooling is wrong.** Pooling made sense when allocation was slow and every collection was a stop-the-world pause for the whole heap. Neither is true on a modern JVM. Allocation is a bump-pointer increment inside a thread-private TLAB (`UseTLAB = true`, `TLABSize = 0` meaning adaptive on this build) — no lock, no free-list search — and a young-generation object that dies before the next young collection is never copied, never traced, and costs essentially nothing to collect. Against that, a pool **adds** three costs. It needs a thread-safe data structure of its own, so every borrow and return is a contended concurrent operation replacing an uncontended pointer bump. It forces promotion: pooled objects live by design, so they survive young collections and reach the old generation, where they genuinely do cost something to trace and eventually collect — pooling converts free garbage into expensive long-lived data. And it introduces a bug class with no diagnostic signature: an object handed out again before its previous holder finished with it corrupts state with no stack trace pointing at the cause, which is the action-at-a-distance failure `../objects-equality-and-lifecycle/02-copying-and-composite-equality.md` describes for aliasing, now scheduled by a pool. Pooling still wins for exactly one shape of resource: **something expensive to create with a hard external limit**, where what is pooled is not memory but a scarce handle — database connections, OS threads, an `HttpClient`'s connections. The scarcity is outside the JVM, so the JVM's cheap allocation is irrelevant. Guide 06 (JVM internals) owns GC and TLAB behaviour in full.

### Diagram

No `D-NNN` is assigned to this file. The picture is **D-028**, `Integer` versus `int` in bulk, owned by `../wrappers-and-boxing/01-basics.md`, and it renders exactly the 28-against-8 layout derived above.

### A concrete example

The two representations of a day's ledger-entry ids, both real:

```java
// 28 bytes per element, one pointer dereference per read, and each Long escapes
// into the list so no compiler optimisation can remove it.
public final class BoxedLedgerIndex {
    private final List<Long> entryIds = new ArrayList<>();

    public void record(long entryId) { entryIds.add(entryId); }   // autoboxes

    public long sum() {
        long total = 0;
        for (Long entryId : entryIds) { total += entryId; }       // unboxes, per element
        return total;
    }
}

// 8 bytes per element, one contiguous run, no boxes at all.
public final class PrimitiveLedgerIndex {
    private long[] entryIds = new long[1024];
    private int size = 0;

    public void record(long entryId) {
        if (size == entryIds.length) {
            entryIds = Arrays.copyOf(entryIds, entryIds.length * 2);
        }
        entryIds[size++] = entryId;
    }

    public long sum() {
        long total = 0;
        for (int i = 0; i < size; i++) { total += entryIds[i]; }
        return total;
    }
}
```

The boxed version is the one where the folklore is *right*, and it is worth naming why: every `Long` here escapes into the list, so escape analysis has nothing to eliminate, and the 396 MB and the per-element indirection are both real. `../arrays/01-basics.md` owns arrays and their growth; `../generics/02-in-anger.md` owns why the generic version cannot hold a primitive at all.

### The gotcha

**Pitfall:** believing "boxing is expensive" as an unconditional fact and rewriting readable code to avoid `Integer` in places where the box never escapes. Symptom: a hand-unrolled, primitive-only rewrite of a small helper that measures identically to the original, because C2 had already removed the allocation — and a reviewer who now has to read the ugly version forever. Fix: the rule is about **escaping** boxes and **bulk** storage. A box that goes into a collection, a field, a returned value or another thread is real and the 3.5x applies; a box that lives and dies inside one method is frequently free, and the only way to know which case you are in is to measure. `../cost-model/02a-measurement-and-amortisation.md` owns the measurement discipline.

> **Definition.** Prefer primitives because a boxed `Long` costs 28 bytes per element against a `long[]`'s 8 — a derived 3.5x — plus a pointer dereference per element on a scan; but the *time* cost of boxing applies only to boxes that escape, since a non-escaping box+unbox measured 0.312 ns against 2.512 ns with escape analysis disabled, and "avoid unnecessary objects" means expensive or long-lived objects such as a recompiled `Pattern`, never small short-lived ones — which is also why object pooling, on a JVM whose allocation is a TLAB pointer bump, usually costs more than it saves unless what is pooled is a scarce external handle.

---

## 5. The *Effective Java* cross-index (2.14.11) `[RESEARCH]`

`[RESEARCH]` — An interviewer quoting a rule at you will usually quote it in *Effective Java*'s vocabulary, and the fastest way to sound fluent is to answer in the same vocabulary and then add the mechanism. This section is the mapping from this topic's Part 2 to Bloch's third-edition items.

### Why it exists

Two vocabularies for the same rule is a real cost in an interview: "make defensive copies when needed" and "copy in the constructor after the null check and before the validity check" are the same instruction, and a candidate who cannot connect them looks like they learned one and not the other.

### When to reach for it, and when not

Use the item title as the handle and the mechanism as the answer; never lead with an item number, because a wrong one is worse than none.

### How it works

**The item-number mapping below was corroborated against published tables of contents for the third edition, not against the physical book. The title is authoritative; the number is the cross-check.** A reader who finds a mismatch should trust the title. **Unverified:** the item numbering throughout this table, for that reason.

| *Effective Java* (3rd ed.) item | Where this topic's Part 2 covers it |
|---|---|
| Item 1: *Consider static factory methods instead of constructors* | [04-design-idioms.md](04-design-idioms.md) §1; [02-immutability.md](02-immutability.md) §2 |
| Item 2: *Consider a builder when faced with many constructor parameters* | [04-design-idioms.md](04-design-idioms.md) §2; [02b-records-jmm-and-builders.md](02b-records-jmm-and-builders.md) |
| Item 3: *Enforce the singleton property with a private constructor or an enum type* | [04-design-idioms.md](04-design-idioms.md) §3; `../enums/01c-production-patterns-and-guarantees.md` |
| Item 4: *Enforce noninstantiability with a private constructor* | [04-design-idioms.md](04-design-idioms.md) §5 |
| Item 5: *Prefer dependency injection to hardwiring resources* | §1 of this file |
| Item 6: *Avoid creating unnecessary objects* | §4 of this file; `../strings/02-performance-and-text.md` |
| Item 10: *Obey the general contract when overriding `equals`* | `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` |
| Item 11: *Always override `hashCode` when you override `equals`* | `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md` |
| Item 15: *Minimize the accessibility of classes and members* | §3 of this file; `../classes-and-initialization/02a-access-and-other-modifiers.md` |
| Item 17: *Minimize mutability* | [02-immutability.md](02-immutability.md) §1 |
| Item 18: *Favor composition over inheritance* | §2 of this file |
| Item 19: *Design and document for inheritance or else prohibit it* | §2 of this file; `../inheritance-and-dispatch/01-basics.md` |
| Item 20: *Prefer interfaces to abstract classes* | §3 of this file; `../inheritance-and-dispatch/01b-interfaces.md` |
| Item 49: *Check parameters for validity* | §3 of this file; `../exceptions/02b-designing-an-exception-hierarchy.md` §3 |
| Item 50: *Make defensive copies when needed* | [02-immutability.md](02-immutability.md) §3; [02a-shallow-deep-and-building-blocks.md](02a-shallow-deep-and-building-blocks.md) |
| Item 54: *Return empty collections or arrays, not nulls* | §3 of this file; `../null-discipline/02-null-discipline.md` |
| Item 61: *Prefer primitive types to boxed primitives* | §4 of this file; `../wrappers-and-boxing/01-basics.md` |
| Item 69: *Use exceptions only for exceptional conditions* | `../exceptions/02c-cost-and-control-flow.md` |
| Item 82: *Document thread safety* | §3 of this file; `../date-and-time/02-date-and-time.md` |

### Diagram

No `D-NNN`. A cross-index is a table by nature; a figure would restate it with worse alignment.

### A concrete example

The mapping used as intended: asked "why is `Movement` immutable?" — *"Item 17, minimize mutability: final class, private final fields, no mutators, copy in, copy out; and the copy-in is Item 50, make defensive copies when needed, where the ordering matters — null check, copy, then validate the copy, or the constructor validates one object and stores another."*

### The gotcha

**Interview:** "Which *Effective Java* items apply here?" Name titles and decline numbers you are unsure of — "that is 'favor composition over inheritance', I believe item 18" is honest, while a confidently wrong number invites a correction you cannot recover from, and nobody scores the number.

> **Definition.** The *Effective Java* cross-index is a translation table between this note set's mechanism-first framing and Bloch's item titles, useful because an interviewer's phrasing usually comes from the book — cite the title, treat the number as a cross-check, and follow either with the mechanism.

---

## 6. Where each idiom is over-applied (2.14.12) `[TRAP]`

`[TRAP]` — Every idiom in §§1–4 and in [04-design-idioms.md](04-design-idioms.md) makes the same trade: **concrete simplicity for flexibility you may never use.** The trade is worth it exactly when the flexibility is exercised. Which means the failure mode of good advice is not that the advice is wrong — it is applying it somewhere nothing varies, and paying the flexibility premium forever on a value that never changes.

### Why it exists

Because "when would you *not* use pattern X" is the question that separates a candidate who read a list from one who has maintained the result, and because the three over-applications below are the ones a reviewer actually sees every week.

### When to reach for it, and when not

The test is one sentence, and it is worth memorising: **apply the idiom when the thing it makes variable actually varies.** A builder makes construction order and optionality variable; if there is no optionality, there is nothing to vary. An interface makes the implementation variable; with one implementation, there is nothing to vary. A defensive copy makes the field independent of the caller's object; if the caller's object is immutable, there is nothing to be independent of.

### How it works

**A builder for a two-field type.** Thirty-odd lines of nested static class, one setter per field, a `build()` method and a validation block — to replace `new StakeSplit(bonusPortion, cashPortion)`. Both of the builder's reasons to exist are absent. The telescoping-constructor problem cannot arise with two required fields, because there is exactly one constructor. And the transposition problem the named setters solve does not arise either where the components are *differently* typed — `StatusCode(String domain, int phase)` transposed does not compile — while where they share a type, as `StakeSplit`'s two `Money` portions do, a static factory removes the risk more cheaply than a builder: `StakeSplit.of(stake, bonusAvailable)` derives both portions from the stake and offers no place to transpose them, which is [02-immutability.md](02-immutability.md) §2's factory idiom doing the builder's job in one line. **The line: roughly four or more components, or any optional component.** Below it, a record's canonical constructor or a named static factory covers everything.

**An interface with one implementation.** A `FundsLedgerService` interface whose only implementation is `FundsLedgerServiceImpl`, in the same package, forever. What it buys: nothing. A test can subclass or mock the class directly; a second implementation, when it arrives, is an "extract interface" refactor the IDE performs mechanically in one keystroke, and the callers do not change because they were already calling the methods that become the interface. What it costs: a permanent extra hop on every navigation — every "go to implementation" is now two steps, every stack trace has a name that is not where the code is, and every reader has to confirm there is still only one implementation. The `Impl` suffix is itself the tell: a name that adds no information is a name for a class that exists only because something else needed a name. **The honest exceptions**, and they are real: a genuine module boundary (a `module-info.java` that exports the interface and not the implementation), a published contract other teams compile against and you must not break, and a framework that requires an interface — a JDK dynamic proxy can only proxy interfaces, so Spring AOP with `proxyTargetClass = false` genuinely needs one. That last exception is also why the shape is so common: a decade of Spring material was written when JDK dynamic proxies, not CGLIB, were the default, so the interface really was mandatory. It mostly is not any more, and "program to interfaces" was always a rule about *declared types at call sites*, not a mandate to declare an interface per class.

**Defensive copies in a hot path.** [02-immutability.md](02-immutability.md) rule 4 mandates copying a mutable constructor argument, and rule 5 mandates copying or wrapping on the way out. Both are real allocations. At the ledger's **13,600/sec peak write rate**, a per-write `List.copyOf` of a movement's entries is a measurable, avoidable expense — *when the source is already immutable*, in which case the copy is defending against nothing. The fix is **not** "skip the copy": that reintroduces the aliasing bug the rule exists for. The fix is to make the field's type immutable so the copy is free — a field declared `List<LedgerEntry>` and assigned from `List.copyOf` at the boundary needs no second copy on the way out, which is [02-immutability.md](02-immutability.md) §4's decision rule exactly: *if the field was copied in per rule 4, it is already immutable, so return it directly and pay nothing.* And the decision is made by measurement, not by reflex — `../cost-model/02a-measurement-and-amortisation.md` owns the harness.

### Diagram

No `D-NNN`. Over-application is a judgement about a specific class in a specific codebase; the artefact is the decision line ("four-plus components", "one implementation", "already-immutable source"), and the cheat sheet below carries all three.

### A concrete example

The builder over-application, both spellings side by side:

```java
// Over-applied: a builder for a type that cannot be built wrong.
public final class OverBuiltStatusCode {
    private final String domain;
    private final int phase;

    private OverBuiltStatusCode(Builder builder) {
        this.domain = builder.domain;
        this.phase = builder.phase;
    }

    public static Builder builder() { return new Builder(); }

    public static final class Builder {
        private String domain;
        private int phase;

        public Builder domain(String domain) { this.domain = domain; return this; }

        public Builder phase(int phase) { this.phase = phase; return this; }

        public OverBuiltStatusCode build() {
            Objects.requireNonNull(domain, "domain must not be null");
            return new OverBuiltStatusCode(this);
        }
    }
}

// The whole thing, correctly.
public record StatusCode(String domain, int phase) {
    public StatusCode {
        Objects.requireNonNull(domain, "domain must not be null");
    }
}
```

Thirty-two lines against six, for a type where `new StatusCode("AA", 8)` cannot be written wrong — the arguments are a `String` and an `int`, so transposing them does not compile.

### The gotcha

**Pitfall:** believing that applying more idioms makes a design better, so an unused abstraction is at worst neutral. It is not neutral, and the asymmetry is what makes this hard to see: **the cost of over-applying is paid every day, by every reader, forever; the cost of under-applying is paid once, in a refactor an IDE can usually do for you.** Symptom: a codebase where every service has an interface with one implementation, every value type has a builder, and every accessor copies — and where a new joiner takes three weeks to become productive because nothing is where its name says it is. Fix: apply the idiom when the thing it makes variable actually varies, and be willing to add it later, because "later" is a mechanical refactor and "always" is a permanent reading tax. An idiom you cannot state the failure mode of is one you are applying by reflex.

> **Definition.** Every design idiom trades concrete simplicity for flexibility, so each one is over-applied wherever the flexibility it buys is never exercised — a builder below four components or with no optional component, an interface with one implementation and no module or framework boundary, a defensive copy of an already-immutable source in a hot path — and the governing rule is to apply the idiom when the thing it makes variable actually varies, accepting that adding it later is a mechanical refactor while carrying it needlessly is a permanent cost to every reader.

---

## Pitfalls

### "A singleton and a single injected instance are the same thing"

**Wrong**

```java
public final class PaymentService {
    public void reserve(ClientId clientId, Money stake) {
        FundsLedger ledger = PostgresFundsLedger.getInstance();   // static singleton
        Money available = ledger.availableCash(clientId);
        if (available.compareTo(stake) < 0) {
            throw new InsufficientFundsException(clientId, available, stake);
        }
        ledger.append(new LedgerEntry("CLIENT_CASH_RESERVED", stake));
    }
}
```

There is one instance, which was the requirement. But `PaymentService`'s dependency on the ledger appears nowhere in its API, a test cannot substitute an in-memory ledger without mutating static state, and the initialization of `PostgresFundsLedger` is now a global ordering concern rather than a step in an assembly function.

**Right**

```java
public final class PaymentService {
    private final FundsLedger ledger;

    public PaymentService(FundsLedger ledger) {
        this.ledger = Objects.requireNonNull(ledger, "ledger must not be null");
    }

    public void reserve(ClientId clientId, Money stake) {
        Money available = ledger.availableCash(clientId);
        if (available.compareTo(stake) < 0) {
            throw new InsufficientFundsException(clientId, available, stake);
        }
        ledger.append(new LedgerEntry("CLIENT_CASH_RESERVED", stake));
    }
}
```

Assembled once — `new PaymentService(theOneLedger)` in an assembly function or as a container-scoped bean — there is still exactly one ledger instance, and the dependency is now declared, substitutable and locally initialized.

**Why people believe it:** both phrases contain "one instance", and for the narrow question "how many of these exist in the process" they genuinely give the same answer. The conflation is between *cardinality* (one instance) and *reachability* (a static field anyone can call), and only the second causes the damage: it is what makes the dependency invisible and the substitution impossible.

### "Extending `ArrayList` to add behaviour is fine — it is a normal subclass"

**Wrong**

```java
static class CountingLedgerEntrySet extends HashSet<LedgerEntry> {
    private int appended = 0;

    @Override public boolean add(LedgerEntry e) {
        appended++;
        return super.add(e);
    }

    @Override public boolean addAll(Collection<? extends LedgerEntry> c) {
        appended += c.size();
        return super.addAll(c);
    }

    public int appended() { return appended; }
}
```

Measured on JDK 21.0.7, a single `addAll` of three ledger entries:

```
extends HashSet   : size=3 appended=6
extends ArrayList : size=3 appended=3
```

Three entries went in and the counter says six, because `HashSet` inherits `AbstractCollection.addAll`, which loops calling the overridden `add`. Identical wrapper code over `ArrayList` says three, because `ArrayList.addAll` copies in bulk and never calls `add`. Neither superclass documents which strategy it uses, and either is free to change it.

**Right**

```java
public final class CountingLedgerEntryList extends ForwardingLedgerEntryList {
    private int appended = 0;

    public CountingLedgerEntryList(List<LedgerEntry> delegate) { super(delegate); }

    @Override public boolean add(LedgerEntry e) {
        appended++;
        return super.add(e);
    }

    @Override public boolean addAll(Collection<? extends LedgerEntry> c) {
        appended += c.size();
        return super.addAll(c);
    }

    public int appended() { return appended; }
}
```

Measured, same three entries, then the same wrapper over a `LinkedList` with one extra single `add`:

```
forwarding wrapper: size=3 appended=3
same wrapper over LinkedList: size=4 appended=4
```

Correct, and correct *because* the forwarding class's self-use pattern is trivial by construction — every method forwards exactly once and calls no other wrapper method, so `addAll` can never reach the overridden `add`.

**Why people believe it:** `extends ArrayList<LedgerEntry>` compiles, the IDE offers it, and the subclass really does pass `instanceof List`, so every type-level signal says this is ordinary and supported. What no signal shows is the superclass's internal call graph, which is the thing the subclass's correctness actually depends on.

### "Boxing is expensive, so avoid `Integer` everywhere"

**Wrong**

```java
// Contorted so that no Integer or Long is ever created, because "boxing allocates".
// "No movements" is now carried by a parallel boolean instead of a null box, so one
// piece of state lives in two variables that can disagree.
public static long peakStakeMinorUnits(List<Movement> movements) {
    boolean found = false;
    long peak = Long.MIN_VALUE;
    for (int i = 0; i < movements.size(); i++) {
        long minor = movements.get(i).amountMinorUnits();
        if (!found || minor > peak) {
            peak = minor;
            found = true;
        }
    }
    return found ? peak : 0L;
}
```

Nothing in that loop ever escaped the method, so the contortion buys nothing and costs a reader the invariant that `found` and `peak` must be updated together — a hand-rolled two-variable encoding of one optional value, which is a bug shape the box was preventing.

**Right**

```java
// `peak` is a Long solely so that null can spell "no movements". It is created and
// consumed inside this method, is never stored, returned or published, so C2 proves
// non-escape and removes the allocation: the two versions measure the same.
public static long peakStakeMinorUnits(List<Movement> movements) {
    Long peak = null;
    for (Movement m : movements) {
        long minor = m.amountMinorUnits();
        if (peak == null || minor > peak) {
            peak = minor;                          // autoboxes, then is eliminated
        }
    }
    return peak == null ? 0L : peak;               // unboxes
}
```

Measured on JDK 21.0.7, a non-escaping box+unbox round trip in a tight loop cost **0.312 ns** — at the harness floor, because C2 proved non-escape and removed the allocation entirely — against **2.512 ns** with `-XX:-DoEscapeAnalysis`, which is not how anything runs in production. Both figures are quoted from `../cost-model/02-master-cost-table.md`. The rewrite worth doing is the *other* one: boxes that escape into a `List<Long>` field outliving every method, where the derived 28-against-8 bytes per element is real — 3.5x, 396 MB across a day's 19.8M ledger entries, and a measured 13.9x scan penalty at 8M elements.

**Why people believe it:** the memory arithmetic is correct and easy to compute, so it feels like it must dominate — and for a decade of JVMs before escape analysis matured, it did. The measurement that corrects it is one number most people have never run, and the folklore predates the optimisation that invalidates half of it. **Unverified:** C2 offers no documented guarantee about when escape analysis applies, so the correction is "frequently free", never "always free".

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| DI, in one sentence | A statement about *who chooses* a collaborator — the class, or whoever assembles it |
| DI without a framework | Constructor parameter, `final` field, assembled by hand in `main` or a factory. Sufficient below a few dozen objects |
| What DI buys, concretely | Test with an in-memory double and no container; two rails, one class; the constructor *is* the dependency list |
| DI's limits | Eight dependencies means eight responsibilities; field injection defeats `final`; service locator is DI inverted |
| Singleton vs injected instance | Cardinality (one instance) and reachability (static field) are separate claims. Take the first, decline the second |
| Why `extends` is the tightest coupling | The subclass depends on the superclass's **self-use pattern**, which is undocumented and free to change |
| Measured fragile base class | `extends HashSet` + override `add`/`addAll` → `appended=6` for 3 entries; identical code over `ArrayList` → `appended=3`, because `HashSet` inherits `AbstractCollection.addAll`, which loops calling `add`, while `ArrayList.addAll` copies in bulk |
| Forwarding class, and why it is safe | Private delegate field typed to the interface, one-line forwarder per method; subclass *that*. Its self-use pattern is trivial by construction — one forward per method, no wrapper-internal calls |
| Measured forwarding wrapper | `appended=3` over `ArrayList`, `appended=4` over `LinkedList` after 3 + 1 — implementation-independent |
| Forwarding's two real leaks | SELF problem (delegate publishes `this`, bypassing the wrapper) and concrete-type identity (`instanceof`, reflection, serializers) |
| Inheritance decision rule | Inherit only if genuine subtype **and** superclass designed and documented for inheritance. Otherwise compose |
| Program to interfaces | Declare `List`/`Map`/`FundsLedger`. Exception: keep the concrete type when its specific guarantee is the point (`ArrayDeque`, `LinkedHashMap`) |
| Minimise accessibility | Default `private`; four levels `private` < package-private < `protected` < `public`; package-private is underused, `protected` is a self-use commitment |
| Empty over null | `List.of()` returns a shared instance and allocates nothing, so there is no cost argument for `null`. `Optional` is for one absent value, not a collection |
| Validate parameters | `Objects.requireNonNull(x, "x")` and `Objects.checkIndex` at every public boundary; private methods may skip |
| Immutability ordering | Null check → defensive copy → validate the copy (that is validation and TOCTOU composed) |
| Document thread safety | Four categories: immutable, thread-safe, conditionally thread-safe, not thread-safe. `SimpleDateFormat` vs `DateTimeFormatter` is the case |
| Boxed `Long` vs `long[]` | 12-byte header + 8-byte value = 20 → 24 rounded, + 4-byte reference = **28 bytes/element**, against **8**. Ratio **3.5x** |
| Scaled: 1024 elements | `long[]` 8,208 bytes vs `List<Long>` 28,688 bytes = 3.50x |
| Scaled: 19.8M/day | 158 MB vs 554 MB — a 396 MB difference |
| The cost the bytes miss, measured | Scan: `long[]` **0.21–0.23 ns/element at every length**; `Long[]` **1.06x at 1,024 elements, 3.6–4.0x at 1M, 13.9x at 8M**. Indirection costs nothing in cache, dominates out of it |
| Measured boxing time | Non-escaping box+unbox **0.312 ns**; **2.512 ns** with `-XX:-DoEscapeAnalysis`. Boxing is expensive only when the box **escapes** |
| Unnecessary objects | Means **expensive or long-lived** — a per-call `Pattern.compile` hoisted to `static final`. Not small short-lived objects |
| Why pooling is usually wrong | TLAB allocation is a pointer bump; young objects die free. A pool adds contention, forces promotion, and enables reuse-before-release bugs |
| When pooling wins | Scarce **external** handles with a hard limit: DB connections, threads, `HttpClient` connections |
| Over-applied builder | Below ~4 components, or with no optional component. A record's canonical constructor or a static factory covers it |
| Over-applied interface | One implementation, no module/API/framework boundary. "Extract interface" later is one IDE keystroke |
| Over-applied defensive copy | Copying an already-immutable source in a hot path (13,600/sec ledger peak). Fix the field's *type*, do not skip the copy |
| The meta-rule, and the asymmetry behind it | Apply the idiom when the thing it makes variable **actually varies** — over-applying costs every reader every day, under-applying costs one mechanical refactor once |
| *Effective Java* handles | Cite the **title**, treat the number as a cross-check (Item 5 DI, 6 unnecessary objects, 15 accessibility, 17 immutability, 18 composition, 20 interfaces, 49 validate, 50 defensive copies, 54 empty collections, 61 primitives, 82 thread safety) |

---

## Self-test

**Q1.** Define dependency injection without using the words "Spring", "container" or "framework", then name the three concrete things constructor injection buys over a hardwired `new` inside a method body.

<details><summary>Answer</summary>

Dependency injection is a statement about *who chooses a collaborator*. A class that writes `new PostgresFundsLedger()` in its own body has made that choice permanently on behalf of every caller; a class that takes a `FundsLedger` as a constructor parameter has moved the choice out to whoever assembles the object. That single relocation is the entire idiom, and plain constructor injection assembled by hand — in `main`, in a factory, in a test's setup — is a complete implementation of it. The JDK does this everywhere: `InputStreamReader` takes the `InputStream` rather than opening a file, `PriorityQueue` takes the `Comparator` rather than fixing an ordering.

Three concrete gains, none of them the word "testability" on its own. First, a test constructs `new PaymentService(new InMemoryFundsLedger(balances))` — no database, no context to boot, no mocking library needed, because the seam is a constructor parameter rather than something a testing tool has to create. Second, one class serves both the card rail and the bank rail with two implementations of the interface, with no subclass and no `if (rail == CARD)` branch inside the method body. Third, and most underrated, the constructor signature *is* the dependency list: a reader who wants to know what `PaymentService` touches reads one line, where no number of `new` calls buried in method bodies would ever tell them.

</details>

**Q2.** Why is `extends` described as the tightest coupling in the language? Answer at the mechanism level, not by analogy.

<details><summary>Answer</summary>

Because a subclass depends not on its superclass's *contract* but on its superclass's **self-use pattern** — which of its own public methods each public method calls internally. That pattern is an implementation detail: no javadoc is obliged to record it, no compiler checks it, and every release is free to change it. So a subclass that overrides a method is betting on a fact it cannot see and was never promised.

Measured on JDK 21.0.7: a counting collection that overrides both `add` (incrementing by one) and `addAll` (incrementing by `c.size()`) — the careful thing to write, since you want both entry points counted — reports `appended=6` for a single `addAll` of three ledger entries when it extends `HashSet`, and `appended=3` from identical code when it extends `ArrayList`. `HashSet` does not override `addAll`, so it inherits `AbstractCollection.addAll`, which loops calling the overridden `add`, double-counting every element. `ArrayList` does override `addAll`, and copies in bulk with `System.arraycopy` without ever calling `add`. Neither superclass is buggy and neither documents its choice. The direction of the subclass's error flips with the superclass, and a JDK release changing either strategy would silently change the answer of code nobody had edited. That is the fragile base class problem; interface inheritance does not have it, because an interface has no implementation to have a self-use pattern.

</details>

**Q3.** What exactly does the forwarding class fix, and what are its two genuine limits?

<details><summary>Answer</summary>

It fixes the dependency. The forwarding class holds a private delegate typed to the *interface* — `private final List<LedgerEntry> delegate` — implements the interface, and forwards each method as a one-liner. The counting behaviour then extends the forwarding class rather than the collection, and what that buys is exact: the forwarding class's self-use pattern is trivial and stable **by construction**, since every method forwards exactly once to the delegate and calls no other method of the wrapper. So an override of `add` can never be reached from `addAll`, and no future change to `ArrayList` or `HashSet` can reach the counter at all. Measured on JDK 21.0.7 the same wrapper reported `appended=3` over an `ArrayList` delegate and `appended=4` over a `LinkedList` delegate after three plus one — implementation-independent, unlike either subclass.

The two limits. First, the **SELF problem**: if the delegate ever hands out `this` — registering itself as a listener, passing itself to a callback — the recipient holds the delegate, not the wrapper, and every call it makes bypasses the wrapper entirely; there is no fix inside the idiom, the delegate simply must not publish `this`. Second, **type identity**: `instanceof ArrayList` is false for the wrapper and `getClass()` returns the wrapper's class, so anything that reflects over the concrete type or special-cases a known implementation for a fast path — a serializer keyed on class name, for instance — no longer recognises it. The cost, separately, is verbosity: every interface method needs a forwarder, which is why the JDK ships `AbstractList` and why this is tedious without an IDE.

</details>

**Q4.** "Program to interfaces" — state the rule and then its honest exception, with an example of each.

<details><summary>Answer</summary>

The rule is about *declared* types: declare the variable, the parameter and above all the return type as the interface — `List<LedgerEntry>`, `Map<ClientId, Restriction>`, `FundsLedger` — not as `ArrayList`, `HashMap`, `PostgresFundsLedger`. The mechanism is that a declared type is the set of operations a caller may use, so a concrete declared type silently permits implementation-specific calls that make the implementation unswappable. `Movement.entries()` declared as `List<LedgerEntry>` can change from a `List.copyOf` result to an immutable view without touching a caller; declared as `ArrayList<LedgerEntry>` it cannot.

The exception is that the concrete type is correct when its *specific* guarantee is the reason you chose it. `ArrayDeque` used as a stack should be declared `Deque`, because the LIFO operations are the point — declaring it `Collection` throws the guarantee away. `LinkedHashMap` used for its insertion-ordered iteration should be declared `LinkedHashMap`, or at minimum have the ordering documented as part of the contract; declaring it a bare `Map` invites a future maintainer to substitute `HashMap` and silently lose the property the whole choice was about. "Program to interfaces" means "declare the weakest type that still expresses every guarantee your callers depend on" — not "declare the weakest type available".

</details>

**Q5.** Do the memory arithmetic for a day of ledger-entry ids held as `List<Long>` against `long[]`, on JDK 21 with compressed oops, and then say which cost the arithmetic misses.

<details><summary>Answer</summary>

Under compressed oops on JDK 21 — `UseCompressedOops = true`, ergonomic on this build — the object header is 12 bytes (8-byte mark word plus 4-byte compressed class pointer), a reference field is 4 bytes, an array header is 16 bytes, and every object rounds up to a multiple of 8 (`ObjectAlignmentInBytes = 8`). A `Long` is therefore 12 + 8 = 20 bytes, rounded to **24**; plus the 4-byte reference in the backing array that points at it, giving **28 bytes per element**. A `long[]` costs **8 bytes per element**. That is 28 / 8 = **3.5x**.

Scaled to the 1024-element window the cost harness uses: `long[1024]` is 16 + 1024 × 8 = 8,208 bytes, about 8.0 KB; a 1024-element `List<Long>` is 16 + 1024 × 4 for the references (4,112) plus 1024 × 24 for the `Long` objects (24,576) = 28,688 bytes, about 28.0 KB — 28,688 / 8,208 = 3.50x, the same ratio once the array headers wash out. Scaled to a day's 19.8M ledger entries: 158 MB against 554 MB, a difference of 396 MB.

The cost the arithmetic misses, and it usually matters more, is **indirection**. A `long[]` is one contiguous run of memory, so a scan walks consecutive cache lines and the hardware prefetcher predicts it perfectly. A `List<Long>`'s backing array is an array of pointers to 24-byte objects allocated at different times and sitting at scattered addresses, so a scan dereferences a pointer per element and each dereference is a candidate cache miss. The 3.5x is the number you can compute on paper; the pointer chase is the effect you measure — and measured on JDK 21.0.7 (warmed, three runs, boxed references shuffled) the `long[]` scan is flat at 0.21–0.23 ns/element while the `Long[]` scan is **1.06x slower at 1,024 elements, 3.6–4.0x at 1M, and 13.9x at 8M**. The indirection therefore costs nothing while everything fits in cache and dominates once it does not, exceeding the arithmetic's 3.5x by four times at ledger scale.

</details>

**Q6.** "Boxing is expensive." Correct the statement using the measured figures, and say what the corrected version implies for code review.

<details><summary>Answer</summary>

The claim is true only of boxes that **escape**. Measured on JDK 21.0.7, a box-and-unbox round trip in a tight loop where the box does not escape cost **0.312 ns**, which is at the harness floor — and **2.512 ns** with `-XX:-DoEscapeAnalysis`. With escape analysis on, which is the default (`DoEscapeAnalysis = true`, `EliminateAllocations = true` on this build), C2 proved the `Integer` could not be observed outside the method and removed the allocation entirely. The same source records that in-cache and out-of-cache boxing measured indistinguishably for exactly this reason: the allocation the wrapper cache would have saved never happened either way, so the cache is about *identity* (`==`) rather than about this figure.

So the corrected statement is: **boxing is expensive when the box escapes** — into a collection, a field, a returned value, or another thread — and frequently free when it lives and dies inside one method. For code review that means the finding "you boxed here" is not, by itself, a finding. `List<Long>` as a field holding 19.8M ledger ids is a real 396 MB and a real pointer chase and is worth rewriting as a `long[]`. An `Integer` created and consumed inside a five-line helper is very likely to cost nothing, and rewriting it costs a reader clarity forever in exchange for a measurement nobody took. The caveat that keeps this honest: C2 documents no guarantee about when escape analysis or scalar replacement applies, so the correct phrasing is "frequently eliminated", never "always eliminated" — the only way to know is to measure the specific method.

</details>

**Q7.** Why is object pooling usually wrong on a modern JVM, and what is the one shape of resource for which it is still right?

<details><summary>Answer</summary>

Pooling was designed against two conditions that no longer hold. Allocation is no longer slow: on HotSpot it is a bump-pointer increment inside a thread-private TLAB (`UseTLAB = true`, `TLABSize = 0` meaning adaptively sized on this build) — no lock, no free-list search. And collection is no longer a stop-the-world sweep of everything: a young-generation object that dies before the next young collection is never copied, never traced, and costs essentially nothing to collect.

Against that, a pool adds three costs. It needs its own thread-safe data structure, so every borrow and return is a contended concurrent operation replacing an uncontended pointer bump — on a hot path that is a straight loss. It forces promotion: pooled objects live by design, so they survive young collections and reach the old generation, where they genuinely do cost something to trace and eventually collect; pooling converts free garbage into expensive long-lived data. And it introduces a bug class with no diagnostic signature: an object handed out again before its previous holder has finished with it corrupts state with no stack trace pointing at the cause.

The one shape still worth pooling is a resource that is **expensive to create and externally limited**, where what is pooled is not memory but a scarce handle outside the JVM: database connections, OS threads, an `HttpClient`'s connections. The JVM's cheap allocation is irrelevant to those, because the constraint was never heap.

</details>

**Q8.** Give the decision line for each of the three over-applied idioms, and the meta-rule that generates all three.

<details><summary>Answer</summary>

The builder: roughly **four or more components, or any optional component**. Below that, a record's canonical constructor or a named static factory covers it, and thirty lines of nested builder replace `new StakeSplit(bonusPortion, cashPortion)` for nothing — where the components are differently typed, transposition is a compile error and the builder's named setters solve a problem that cannot occur; where they are the same type, a static factory such as `StakeSplit.of(stake, bonusAvailable)` derives both portions and cannot transpose them at all, which is cheaper than a builder.

The interface: **one implementation and no module, published-API or framework boundary**. A `FundsLedgerService` with a single `FundsLedgerServiceImpl` buys nothing — a test can mock or subclass the class directly, and a second implementation later is an "extract interface" refactor the IDE does mechanically with no caller changes — while costing a permanent extra navigation hop on every read. The real exceptions are a `module-info.java` that exports the interface but not the implementation, a contract other teams compile against, and a framework that requires one (a JDK dynamic proxy can only proxy interfaces).

The defensive copy: **an already-immutable source in a hot path**. At the 13,600/sec peak ledger write rate, a per-write `List.copyOf` of a field that is already a `List.copyOf` result is a measurable allocation defending against nothing. The fix is not to skip the copy — that restores the aliasing bug — it is to make the field's type immutable so the copy on the way out is free, and to let measurement rather than reflex decide.

The meta-rule that generates all three: **apply the idiom when the thing it makes variable actually varies.** Every idiom trades concrete simplicity for flexibility, and the trade pays only when the flexibility is exercised. The asymmetry that makes this hard to see is that over-applying is paid every day by every reader, while under-applying is paid once, in a refactor an IDE can usually do for you. An idiom you cannot state the failure mode of is one you are applying by reflex.

</details>

**Q9.** Why is "document thread safety" a rule about something a caller genuinely cannot discover, unlike the other five small mandates? Name the four categories and the JDK pair where the documentation is the whole difference.

<details><summary>Answer</summary>

Because thread safety is not visible in the class's shape. A caller can read the signatures and see the return types, read the modifiers and see what is accessible, and observe empirically whether a method returns `null`. It cannot determine thread safety from any of that: safety depends on whether every mutable field is guarded, on whether the object graph the class reaches is itself safe, and on which sequences of calls are atomic — none of which the signatures express and none of which single-threaded testing reveals. So an undocumented class is *assumed unsafe* by careful callers, who add synchronization that may be redundant and costly, and *assumed safe* by careless ones, who add nothing and ship a race.

Four categories worth stating explicitly: **immutable** — no synchronization ever needed; **thread-safe** — every method safe under concurrent use; **conditionally thread-safe** — safe except for named sequences that need external locking, of which `Collections.synchronizedList`'s iteration is the JDK's own example; and **not thread-safe** — the caller synchronizes.

The pair where the documentation is the entire difference is `SimpleDateFormat` against `DateTimeFormatter`. `SimpleDateFormat` is mutable and not thread-safe: shared as a `static` field across threads it does not throw, it produces *wrong dates*, which is the worst failure shape available. `DateTimeFormatter` is documented immutable and thread-safe and is explicitly designed to be held in a `static final` constant. Identical usage patterns, opposite correctness, and the only signal distinguishing them is the javadoc.

</details>

---

## Open questions

- **The *Effective Java* item numbering in §5.** The mapping was corroborated against published tables of contents for the third edition rather than the physical book, so every title in the table is authoritative while every number is a cross-check. A copy of *Effective Java*, third edition would settle it; until then, cite titles.
- **When C2's escape analysis and scalar replacement actually apply.** The 0.312 ns non-escaping box+unbox figure quoted in §4 and the 2.512 ns figure with `-XX:-DoEscapeAnalysis` are measurements of one build on one loop shape, and HotSpot documents no guarantee about when either optimisation fires. Only a JIT-level guarantee in the JVMS or a documented C2 heuristic would settle it; in its absence the claim is "frequently eliminated", never "always".

---

**Leaves covered:** 2.14.6, 2.14.7, 2.14.8, 2.14.9, 2.14.10, 2.14.11, 2.14.12 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 900
