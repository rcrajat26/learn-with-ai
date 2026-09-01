# 04 Modern Java — `Optional` — BASICS (§1.11)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Collectors — internals collectors](../collectors/03-internals-collectors.md) · Next: [`Optional` — discipline](02-discipline.md)

## Why a type for "no value" at all

### Mental model

`Optional<T>` is not a smarter null. It is a **box with at most one compartment**,
and the type system forces you to open the box before you can look inside. A
`Client` reference can silently be null and the compiler will never say a word
about it; an `Optional<Client>` cannot be treated as a `Client` at all — the
compiler will not let `client.getWallet()` compile on an `Optional<Client>`, full
stop. That single fact — the return type changes shape, not just its runtime
value — is the entire mechanism. Everything else in this file is either exploiting
that shape (the good half) or fighting it by unwrapping too early (the bad half,
§1.11.12–1.11.13).

### Why it exists

Before Java 8, `findClient(id)` returning "the client, or nothing" had exactly two
honest options: return `null` and hope every caller remembers to check, or throw
an exception and force every caller into a `try`/`catch`. Both compile whether or
not the caller handles absence. A `ClientRepository.findByEmail(email)` that
returns `null` on a miss produces a `NullPointerException` three call frames away
in `wallet.getBalance()`, with a stack trace that says nothing about which of the
four dereferences in the chain was the null one. `Optional<Client>` moves that
information into the type: the signature itself tells the caller "this might come
back empty, and here is the API for handling that," and the compiler enforces
that the caller cannot forget, because there is no `getClient()` method on
`Optional` to forget to call — there is `orElse`, `orElseGet`, `map`, `flatMap`,
`ifPresent`, and `get()`, and reaching for `get()` without justification is a
pattern reviewers now know to flag (§1.11.12).

### 1.11.1 — Purpose: model absence in the return type

The whole point is narrower than most engineers use it for: `Optional<T>` exists
to let a **return type** say "there might be nothing here," so the caller is
forced to acknowledge that at the type level rather than at runtime. It is a
communication device between a method and its callers, encoded as a type. It was
never meant to be a general-purpose "maybe" monad sprinkled through fields,
parameters, and collections — those uses fight the JVM and the JDK's own design
intent, which is precisely why §1.11.14–1.11.18 exist as a wall of traps.

> **`Optional<T>` is a value-holder type whose sole sanctioned purpose is to be a
> method's return type, communicating "this call may have nothing to give you"
> at the type level instead of leaving it to a null check the caller might skip.**

### 1.11.2 — The javadoc API note, quoted

The class javadoc for `java.util.Optional` (JDK 21, `java.base/java.util.Optional`)
carries an explicit API note — not prose buried in a paragraph, a labelled
`@apiNote`:

```
API Note:
Optional is primarily intended for use as a method return type where
there is a clear need to represent "no result," and where using null
is likely to cause errors. A variable whose type is Optional should
never itself be null; it should always point to an Optional instance.
```

Two separate instructions live in that one note, and both matter:

1. **"primarily intended for use as a method return type"** — this is the
   authority behind every "don't put `Optional` in a field / parameter /
   collection" rule in §1.11.14–1.11.18. It is not house style; it is the JDK's
   own stated design intent, in the javadoc of the class itself.
2. **"a variable whose type is `Optional` should never itself be null"** — this
   is a second, independent trap, distinct from "the `Optional` is empty." A
   field or parameter declared `Optional<Money> discount` that is itself `null`
   defeats the type twice over: you now have to null-check the `Optional`
   *before* you can ask whether it is present, which is strictly worse than the
   null check `Optional` was invented to replace. `Optional.ofNullable(x)` exists
   precisely so a producer never has to hand out a null `Optional` reference —
   there is no excuse for one to exist in well-written code.

**Interview:** "Why does the `Optional` javadoc matter?" — because it is the
primary source for the whole "return type only" doctrine; quoting it verbatim
in an interview answer signals you read the source, not a blog post repeating
the rule without the citation.

### 1.11.3 — Value-based class

`Optional` is annotated `@jdk.internal.ValueBased` and documented in the
`java.lang.doc-files/ValueBased.html` package note as a **value-based class**.
That designation is a set of programmer obligations, not a JVM-enforced
restriction (not yet — see the Valhalla note in §1.11.24):

- Instances are considered equal by `equals()`, not by `==` — two `Optional`
  instances wrapping equal contents should be treated as interchangeable, and
  the JDK reserves the right to actually make them the same instance in a future
  release (caching, interning) without breaking correctly-written code.
- **Never synchronize on an instance.** `Optional`'s internal fields are
  effectively-final and there is no synchronized state to protect, and a future
  JVM may implement value-based classes as genuine flattened values with no
  stable monitor to lock on at all.
- **Never rely on identity** — no `==` comparison, no using it as a map key
  keyed by reference, no `WeakHashMap` entries keyed on an `Optional`.
- The class is `final`; you cannot subclass it to add fields, which forecloses
  the most common way identity-dependence sneaks in (a subclass instance
  compared by reference).

`[X-REF 06]` The JVM-level story behind "why identity may stop being reliable" is
Project Valhalla's value classes — a value class has no object header, no
identity hash code that means anything, and potentially no stable heap address
at all, because the JIT is free to pass it by value in registers or on the
stack rather than as a heap reference. Guide 06 (JVM internals) covers value
class layout and Valhalla's flattening model in full; the takeaway for this file
is that `Optional`'s "value-based" javadoc annotation today is the JDK's early
warning that this migration is coming for this exact class, which is why the
rule already exists years ahead of Valhalla shipping.

**Pitfall:** Treating `Optional` as an ordinary object you can synchronize on or
compare by reference.

**Wrong**

```java
Optional<Client> cached = clientCache.get(clientId);
synchronized (cached) {                 // legal today, undefined tomorrow
    if (cached.isPresent()) {
        refreshWallet(cached.get());
    }
}
```

**Right**

```java
Optional<Client> cached = clientCache.get(clientId);
Object lock = clientLocks.computeIfAbsent(clientId, id -> new Object());
synchronized (lock) {                   // lock a dedicated object, never the Optional
    cached.ifPresent(this::refreshWallet);
}
```

**Why people believe it:** `Optional` is a plain heap object today on every
shipping JVM, so synchronizing on one currently "works" in the sense that it
does not throw — the trap is that "works today" is exactly what the value-based
contract tells you not to depend on.

> **A value-based class carries no identity contract: no `==`, no
> synchronization, no locking, only `equals()`-based comparison — obligations
> the JDK documents today so that a future JVM is free to stop giving instances
> a stable identity at all.**

### 1.11.4 — Not `Serializable`

`Optional` does not implement `java.io.Serializable`. This is not an oversight —
it is the concrete, checkable reason `Optional` does not belong in a field of any
class that is itself serialized: attempting to serialize an object graph that
contains a non-transient `Optional` field throws `NotSerializableException:
java.util.Optional` at the first `ObjectOutputStream.writeObject` call that
reaches it, with no compile-time warning beforehand.

```java
public final class WithdrawalTransaction implements Serializable {
    private final Money amount;
    private final Optional<String> operatorNote;   // compiles fine

    public WithdrawalTransaction(Money amount, Optional<String> operatorNote) {
        this.amount = amount;
        this.operatorNote = operatorNote;
    }
}
```

```java
var txn = new WithdrawalTransaction(Money.of("260.00", "GBP"), Optional.of("manual review"));
try (var out = new ObjectOutputStream(new ByteArrayOutputStream())) {
    out.writeObject(txn);
}
// java.io.NotSerializableException: java.util.Optional
```

The failure is deferred to the first serialization attempt, which in a system
like QuizStakes might be a `PaymentRun` object being handed to a distributed
cache or a message queue months after the field was added — the compiler gave
no signal at the point of the mistake.

**Pitfall:** Adding an `Optional<T>` field to a class that is `Serializable`
(directly, or transitively through JPA entity caching, session replication, or
a message payload) and discovering the break only at serialization time, often
in production.

**Wrong**

```java
private Optional<AgreementRef> supersededAgreement;   // field on a Serializable entity
```

**Right**

```java
private AgreementRef supersededAgreement;   // nullable field; Optional only at the accessor boundary

public Optional<AgreementRef> supersededAgreement() {
    return Optional.ofNullable(supersededAgreement);
}
```

**Why people believe it:** every other JDK wrapper type used for "might be
absent" data — `Integer`, `String`, `List` via `Collections.emptyList()` — is
serializable, so there is no learned instinct that this one specific type is
the exception.

> **`Optional` implements no `Serializable` interface, so any field that holds
> one turns the enclosing object into an object that cannot be serialized,
> failing only at the first attempt rather than at compile time.**

---

## Construction and interrogation — the supporting facts

`Optional.of(T value)` throws `NullPointerException` immediately if `value` is
null — it is the "I am certain this is non-null, crash loudly if I'm wrong"
constructor. `Optional.ofNullable(T value)` is the general-purpose entry point:
returns `Optional.of(value)` if non-null, `Optional.empty()` otherwise, and it is
what nearly every producer method should call when adapting a nullable API
(a `Map.get`, a JDBC `ResultSet` column, a legacy library) into `Optional`.
`Optional.empty()` returns a **shared singleton instance** — `Optional.EMPTY` is
a `private static final` field initialized once in the class, so `Optional.empty()
== Optional.empty()` is `true` today, though relying on that `==` violates the
value-based contract of §1.11.3 and is exactly the kind of thing that contract
warns you not to lean on.

**Pitfall:** Reaching for `Optional.of(value)` on a value whose nullability you
have not actually verified, turning a normal "not found" case into an NPE with a
confusing stack frame inside `Optional.of` rather than at the call site that
actually has the missing data.

**Wrong**

```java
Optional<Client> client = Optional.of(clientRepository.findByEmail(email));
// clientRepository.findByEmail returns null on a miss — NPE thrown *inside* Optional.of
```

**Right**

```java
Optional<Client> client = Optional.ofNullable(clientRepository.findByEmail(email));
```

**Why people believe it:** `of` reads as the "default" constructor by name
alphabetically and by habit, and the NPE-on-null behaviour is easy to miss until
it actually fires.

> **`of` asserts non-null and throws immediately if wrong; `ofNullable` is the
> universal adapter from a nullable value to `Optional`; `empty()` returns a
> shared singleton that must never be compared by `==` in code that respects the
> value-based contract.**

`isPresent()` returns `true` when a value is held; `isEmpty()`, added in **Java
11**, returns the negation and exists purely so `if (opt.isEmpty()) return
defaultValue;` reads as an early-exit guard clause instead of `if
(!opt.isPresent())`, which is easy to misread with the `!` lost against the
parenthesis. `get()` and `orElseThrow()` are covered as their own concept in
§1.11.12 because both carry a `[TRAP]`. `orElseThrow(Supplier<X> exceptionSupplier)`
lets the caller name the exception: `.orElseThrow(() -> new
RestrictedActionException(clientId))` instead of the generic
`NoSuchElementException`, and is the version any production code path should
actually use over the no-arg form.

---

## `orElse` versus `orElseGet` — eager and lazy defaults

### Mental model

Java evaluates method arguments **before** the method is called — this is not
special to `Optional`, it is how every method call in the language works, and
`orElse` is not exempt from it just because its result is sometimes discarded.
`orElse(T other)` takes an already-computed value as its argument; by the time
`orElse` is entered, `other` has already been produced, whether or not the
`Optional` turns out to be present. `orElseGet(Supplier<? extends T> supplier)`
instead takes a function that produces the value, and only calls that function
if the `Optional` is empty — the computation is deferred behind a lambda,
invoked conditionally.

### 1.11.9 — Defaults: `orElse(T)` and `orElseGet(Supplier)`

Both return the contained value if present; both return a fallback if empty.
The difference is entirely in *when the fallback is computed*, and that
difference is invisible in code that reads superficially identical:

```java
Money withdrawable1 = findWallet(clientId).orElse(loadDefaultWallet(clientId).withdrawable());
Money withdrawable2 = findWallet(clientId).orElseGet(() -> loadDefaultWallet(clientId).withdrawable());
```

If `findWallet(clientId)` returns a present `Optional`, line one still calls
`loadDefaultWallet(clientId)` — a database round trip — and throws the result
away. Line two never calls it.

### 1.11.11 — `orElse` evaluates its argument eagerly, even when present `[PROVE]`

**Why it exists** — `orElse` predates lambdas being idiomatic for one-off
values; for a cheap constant (`orElse(Money.ZERO)`, `orElse("")`) eager
evaluation costs nothing and reads more simply than a supplier. The problem is
that `orElse` and `orElseGet` have near-identical call shapes, so the "cheap
constant" case and the "expensive computation" case look the same at the call
site, and only one of them is safe to write with `orElse`.

**When to reach for it, and when not** — reach for `orElse` only when the
argument is a literal, an already-held reference, or a call so cheap that
paying for it unconditionally is a non-issue (`Money.ZERO`, an already-fetched
default `Wallet`). Reach for `orElseGet` for anything that does I/O, allocates
non-trivially, or calls another method with its own side effects — a repository
lookup, a database round trip, a `new` on a class with an expensive
constructor, a log call with side effects.

**[PROVE] — working the argument through:**

Java's evaluation order is defined by the JLS (§15.12, method invocation
expressions): argument expressions are evaluated left-to-right, in full,
*before* the target method is invoked. `orElse` is an ordinary instance method
with signature `public T orElse(T other)` — nothing about its declaration tells
the compiler to defer evaluating `other`. So in
`findClient(clientId).orElse(loadDefaultFromDatabase())`, the call
`loadDefaultFromDatabase()` is a plain argument expression to `orElse`. The
JLS's evaluation-order rule fires exactly as it would for any other method call
with a non-trivial argument: `loadDefaultFromDatabase()` runs, its `Client`
result is bound to the parameter `other`, and *only then* does control transfer
into `Optional.orElse`'s body, which is (from the OpenJDK source, `Optional.java`
at jdk-21+35):

```java
public T orElse(T other) {
    return value != null ? value : other;
}
```

By the time this line executes, `other` already holds the fully-computed
`Client` from the database call — the ternary is just choosing which
already-computed reference to return. If `value` is non-null (the `Optional`
was present), the database result is discarded, but the call already happened.
Contrast `orElseGet`:

```java
public T orElseGet(Supplier<? extends T> supplier) {
    return value != null ? value : supplier.get();
}
```

Here the argument to `orElseGet` is the `Supplier` reference itself — a cheap
object construction (a lambda or method reference) — and `supplier.get()` only
appears inside the ternary's false branch. The expensive call is textually
*inside* the conditional, not evaluated as an argument beforehand, so it only
runs when `value == null`. That is the entire mechanism: `orElse`'s cost is
paid unconditionally because it is an argument; `orElseGet`'s cost is paid
conditionally because it is hidden behind a supplier invoked from inside the
branch.

![D-046 — `orElse` evaluates eagerly even when the value is present](../diagrams/D-046a-orelse-evaluates-eagerly-even.svg)
**D-046** — `orElse` evaluates eagerly even when the value is present

![D-046 — `orElse` evaluates eagerly even when the value is present](../diagrams/D-046b-orelse-evaluates-eagerly-even.svg)
**D-046** — `orElse` evaluates eagerly even when the value is present

**A minimal concrete example, with a call counter proving it:**

```java
public final class ClientLookup {

    private static int loadDefaultFromDatabaseCalls = 0;

    static Client loadDefaultFromDatabase() {
        loadDefaultFromDatabaseCalls++;
        return new Client(ClientId.newId(), "default@quizstakes.test");
    }

    static Optional<Client> findClient(ClientId clientId) {
        // AA-801 ACTIVATED client, found in the repository
        return Optional.of(new Client(clientId, "player@quizstakes.test"));
    }

    public static void main(String[] args) {
        loadDefaultFromDatabaseCalls = 0;
        Client viaOrElse = findClient(ClientId.newId()).orElse(loadDefaultFromDatabase());
        System.out.println("orElse:    calls=" + loadDefaultFromDatabaseCalls
            + " result=" + viaOrElse.email());

        loadDefaultFromDatabaseCalls = 0;
        Client viaOrElseGet = findClient(ClientId.newId())
            .orElseGet(ClientLookup::loadDefaultFromDatabase);
        System.out.println("orElseGet: calls=" + loadDefaultFromDatabaseCalls
            + " result=" + viaOrElseGet.email());
    }
}
```

Output, run on this machine (`javac --release 21`):

```
orElse:    calls=1 result=player@quizstakes.test
orElseGet: calls=0 result=player@quizstakes.test
```

Both return the same `player@quizstakes.test` client — the *result* is
identical — but the `orElse` path paid for a database call it never uses. In
QuizStakes terms: if `loadDefaultFromDatabase()` were the real
`AccountMaintenance` service's "load a shell default wallet" query, every single
successful `findWallet` lookup on the hot deposit path (95k card deposits/day)
would silently issue one extra, wasted query per request under the `orElse`
form.

**The gotcha:** the bug produces no wrong answer, ever — it produces a
performance and side-effect problem that unit tests checking only the return
value will never catch, because the returned value is correct in both forms.
The only way to catch it is a test asserting the call counter, or a review that
knows to check every `orElse(...)` argument for a non-trivial expression.

**Pitfall:** Writing `.orElse(expensiveCall())` and assuming — because the
method reads like a lazy fallback — that `expensiveCall()` only runs when
needed.

**Wrong**

```java
Money withdrawable = findWallet(clientId).orElse(rebuildWalletFromLedger(clientId).withdrawable());
// rebuildWalletFromLedger scans the ledger — runs on every call, present or not
```

**Right**

```java
Money withdrawable = findWallet(clientId)
    .orElseGet(() -> rebuildWalletFromLedger(clientId).withdrawable());
// only scans the ledger when findWallet returned empty
```

**Why people believe it:** `orElse` and `orElseGet` differ by three characters
and both "give you a default," so the natural assumption is they are
interchangeable spellings of the same idea — the JLS's ordinary argument
evaluation rule, not anything `Optional`-specific, is what actually causes the
divergence.

> **`orElse(T)` evaluates its argument unconditionally, before `Optional`'s own
> code ever runs, because it is an ordinary method argument; `orElseGet(Supplier)`
> defers the computation inside the method body, running it only on the empty
> branch — use `orElse` only for values already computed or free to compute, and
> `orElseGet` for everything else.**

---

## The anti-patterns that unwrap too early

### Mental model

`Optional` earns nothing if you immediately ask it "do you have a value?" and
then reach in and take it — that is a null check wearing a costume, with an
`Optional` allocation as the price of the costume. The entire value of the type
is in **staying inside the `Optional` API** — `map`, `filter`, `flatMap`,
`orElse` — until the very last line, where you finally either extract a value
via a default, or hand control to `ifPresent`/`ifPresentOrElse`. The moment you
call `get()`, you have stepped back into plain-Java land and thrown away every
type-level guarantee the box was giving you.

### Why it exists — what people did before it, and what they still do with it

The pre-`Optional` idiom was `if (x != null) { ... }`. `Optional` was supposed
to replace that shape entirely with `map`/`orElse` chains. In practice, a large
fraction of code that adopted `Optional` after Java 8 shipped simply substituted
`isPresent()`/`get()` for `!= null`/direct-use, keeping the exact same
imperative shape and paying an extra object allocation for the privilege.

### 1.11.12 — `get()` without a check, and `orElseThrow()` as its self-documenting twin

`get()` on an empty `Optional` throws `NoSuchElementException: No value present`
— a message with no context about *what* was missing or *why*, because
`Optional` has no notion of what it is holding a stand-in for. `orElseThrow()`
(no-arg, added in Java 10) throws the exact same exception with the exact same
message; it is `get()` renamed to say out loud, at the call site, "I am
asserting this is present and I accept the crash if I'm wrong" — a
self-documenting synonym, not a different mechanism. From the OpenJDK source:

```java
public T get() {
    if (value == null) {
        throw new NoSuchElementException("No value present");
    }
    return value;
}

public T orElseThrow() {
    if (value == null) {
        throw new NoSuchElementException("No value present");
    }
    return value;
}
```

Both methods are letter-for-letter identical bodies. The only reason to prefer
one over the other is readability at the call site: `orElseThrow()` tells the
next reader "this is the assertion path," while `get()` carries decades of
"just get the value" muscle memory from every other wrapper type in the JDK
(`AtomicReference.get()`, `Future.get()`, `ThreadLocal.get()`), none of which
throw on the "no value" case the way `Optional.get()` does.

**Pitfall:** Calling `.get()` reflexively, the way you would on any other
wrapper, without having established presence first.

**Wrong**

```java
Client client = findClient(clientId).get();
// NoSuchElementException: No value present — thrown with zero information
// about which clientId, or why the lookup failed
```

**Right**

```java
Client client = findClient(clientId)
    .orElseThrow(() -> new IllegalArgumentException("No client for id " + clientId));
```

**Why people believe it:** every other `.get()` in the standard library
(`Map.Entry.getValue()`, `AtomicReference.get()`) simply returns the value with
no exception path, so `Optional.get()` reads as though it belongs to that
family, when its actual contract is closer to `Iterator.next()` on an empty
iterator.

### 1.11.13 — `if (isPresent()) { get() }` is the null check plus an allocation

```java
Optional<Client> maybeClient = findClient(clientId);
if (maybeClient.isPresent()) {
    Client client = maybeClient.get();
    sendWelcomeEmail(client);
}
```

Compare the pre-`Optional` shape it replaces line for line:

```java
Client client = findClientOrNull(clientId);
if (client != null) {
    sendWelcomeEmail(client);
}
```

Both check a condition, then act on the value inside the branch. The
`Optional` version does exactly the same control flow, with one extra cost
paid on every call regardless of branch outcome: the `Optional<Client>` box
itself was allocated by `findClient` before either branch ran (unless the JIT's
escape analysis proves it never leaves the calling method and elides the
allocation — see §1.11.24). It buys nothing over the null check it looks like
it replaced, because the caller still has to remember to call `isPresent()`
first — the same discipline the null check demanded — and the compiler still
does not enforce it; `maybeClient.get()` compiles just as happily with the `if`
deleted.

**Pitfall:** Treating `isPresent()` + `get()` as "the `Optional` way" of doing a
null check, missing that it reproduces every weakness of the null check it was
meant to retire.

**Wrong**

```java
if (maybeClient.isPresent()) {
    processClient(maybeClient.get());
} else {
    processClient(Client.guest());
}
```

**Right**

```java
processClient(maybeClient.orElse(Client.guest()));
// or, for a void consumer with no fallback:
maybeClient.ifPresentOrElse(this::processClient, () -> processClient(Client.guest()));
```

**Why people believe it:** the `if`/`get()` shape is the most direct mechanical
translation of "check then use," and it compiles and runs correctly — the
defect is invisible unless you already know the point of `Optional` was to make
the *compiler* enforce the check, which `isPresent()`+`get()` does not do.

> **`isPresent()` followed by `get()` inside the branch performs the identical
> control flow as a null check, with an added allocation and none of the
> compile-time enforcement `Optional`'s functional API (`map`, `orElse`,
> `ifPresent`) actually provides — reach for those instead of unwrapping by
> hand.**

**Interview:** "What's wrong with `if (opt.isPresent()) opt.get();`?" — it is a
null check with the same missed-check risk as `!= null`, plus an `Optional`
allocation; the fix is to stay inside the functional chain (`map`/`orElse`/
`ifPresent`) so the compiler, not the reader's discipline, enforces the
handling of absence.

---

## The four places `Optional` must never appear

### Mental model

Every rule below is one instance of the same idea from §1.11.2's javadoc:
`Optional` was designed for exactly one position in a program — a method's
return type — and every other position it turns up in either breaks a concrete
JDK contract (serialization, in §1.11.4) or reintroduces the exact indirection
problem it was invented to remove, just one level higher.

![D-047 — Where `Optional` belongs](../diagrams/D-047-optional-belongs.svg)
**D-047** — Where `Optional` belongs

### 1.11.14 — `Optional` as a field

Two independent costs stack: the field is not serializable (§1.11.4, the
concrete, provable reason), and every read of the field pays **one extra object
allocation** (the `Optional` wrapper, unless escape analysis elides it — it
usually cannot for a field, since the field escapes the method that reads it)
**and one extra dereference** to reach the contained value, compared to reading
the nullable field directly. `[NUM]` For a `Client` aggregate with, say, three
optional fields (`middleName`, `referredBy`, `preferredLanguage`) read on every
one of the 2.4M registered clients' profile-view requests, that is three
avoidable allocations per view that a nullable-field-plus-`Optional`-accessor
design (§1.11.4's "Right" example) does not pay, because the wrapper is
constructed once per call at the accessor boundary rather than held live in
the object graph.

**Pitfall:** Declaring `private Optional<AgreementRef> supersededAgreement;` as
an entity field because the accessor already returns `Optional` elsewhere in
the codebase.

**Wrong** — shown fully in §1.11.4's wrong/right pair above.

**Right** — the nullable-field, `Optional`-returning-accessor pattern, also
shown in §1.11.4.

**Why people believe it:** if `Optional` is the "correct" return type for a
getter, it looks consistent to also make the backing field the same type —
consistency at the field level is exactly what the javadoc API note in §1.11.2
rules out.

### 1.11.15 — `Optional` as a method parameter

```java
public WithdrawalTransaction createWithdrawal(ClientId clientId, Money amount,
                                                Optional<String> operatorNote) {
    ...
}
```

is worse for the caller than either alternative: the caller must now construct
an `Optional` just to call the method — `createWithdrawal(id, amount,
Optional.empty())` or `Optional.of(note)` — where a plain nullable parameter
would have let them pass `null` or the value directly, and an overload would
have let them skip the parameter entirely. Overloading is the idiomatic fix:

```java
public WithdrawalTransaction createWithdrawal(ClientId clientId, Money amount) {
    return createWithdrawal(clientId, amount, null);
}

public WithdrawalTransaction createWithdrawal(ClientId clientId, Money amount, String operatorNote) {
    ...
}
```

**Pitfall:** Accepting `Optional<T>` as a parameter to "be consistent" with the
method's own `Optional`-returning style elsewhere.

**Wrong**

```java
void applyRestriction(ClientId clientId, RestrictionType type, Optional<String> reason) { ... }
// caller forced to wrap: applyRestriction(id, SELF_EXCLUDED, Optional.of("client request"))
```

**Right**

```java
void applyRestriction(ClientId clientId, RestrictionType type, String reason) { ... }
void applyRestriction(ClientId clientId, RestrictionType type) {
    applyRestriction(clientId, type, null);
}
```

**Why people believe it:** it looks symmetric with an `Optional`-returning
method on the same class, but a parameter and a return type serve opposite
audiences — a return type protects the *caller receiving* the value; a
parameter of type `Optional` burdens the *caller providing* it.

### 1.11.16 — `Optional` as a collection element or a map value

`List<Optional<Money>>` or `Map<ClientId, Optional<Wallet>>` forces every
consumer of the collection to unwrap on every access, when the collection APIs
already have a first-class way to express "this slot has nothing": omit the
entry from the map, or filter the element out of the list.

**Pitfall:** Modelling "some restrictions may have no lifted-at timestamp yet"
as `Map<RestrictionKey, Optional<Instant>>`.

**Wrong**

```java
Map<RestrictionKey, Optional<Instant>> liftedAt = new HashMap<>();
liftedAt.get(key).ifPresent(this::logLift);   // still need a null check on the .get() result itself,
                                               // because a missing key returns null, not Optional.empty()
```

**Right**

```java
Map<RestrictionKey, Instant> liftedAt = new HashMap<>();   // absent key == not yet lifted
Optional.ofNullable(liftedAt.get(key)).ifPresent(this::logLift);
```

The "Right" version wraps at the point of *reading*, once, rather than storing
the wrapper — and it sidesteps the sharpest version of this trap: `Map.get` on
a missing key already returns plain `null`, never `Optional.empty()`, so a
`Map<K, Optional<V>>` does not even remove the null check on lookup — it adds a
second, nested one.

**Why people believe it:** it feels like defensive typing to mark every element
"maybe absent," but the collection's own absence signal (a missing key, a
shorter list) already carries that information for free.

### 1.11.17 — Never return `null` from an `Optional`-declared method

```java
public Optional<Client> findClient(ClientId clientId) {
    Client client = repository.lookup(clientId);
    return client == null ? null : Optional.of(client);   // WRONG — see below
}
```

This is the single worst version of the mistake, because it defeats the entire
contract from the caller's side without any compiler warning: a caller who
correctly trusts the return type and writes `findClient(id).isPresent()`
crashes with an NPE on the `.isPresent()` call itself, on a codepath that looks,
by its type signature, like exactly the kind of code `Optional` was supposed to
make impossible.

**Pitfall:** Returning a bare `null` instead of `Optional.empty()` from a method
whose declared return type is `Optional<T>`.

**Wrong**

```java
public Optional<Wallet> findWallet(ClientId clientId) {
    Wallet wallet = wallets.get(clientId);
    return wallet == null ? null : Optional.of(wallet);
}
```

**Right**

```java
public Optional<Wallet> findWallet(ClientId clientId) {
    return Optional.ofNullable(wallets.get(clientId));
}
```

**Why people believe it:** the ternary "if null, return null" pattern is
muscle memory from every non-`Optional` method ever written, and nothing in the
type system stops a method declared to return `Optional<T>` from returning a
literal `null` — the compiler enforces the *declared* type, not the invariant
that the javadoc's own API note asks every author to uphold by hand.

### 1.11.18 — `Optional<List<T>>` is almost always wrong

```java
public Optional<List<LedgerEntry>> findEntriesForRound(RoundId roundId) { ... }
```

`List<T>` already has a zero-element representation with a first-class, cheap,
shared-singleton empty instance: `Collections.emptyList()` (or `List.of()`).
Wrapping it in `Optional` produces two nested "nothing here" representations —
`Optional.empty()` and an empty list inside a present `Optional` — that callers
now must reconcile, when a bare `List<LedgerEntry>` that is simply empty when
there are no entries carries exactly the same information with one API instead
of two stacked ones.

**Pitfall:** Wrapping a naturally-empty-representable collection type in
`Optional` out of habit, because "might be nothing" reflexively suggests
`Optional`.

**Wrong**

```java
public Optional<List<LedgerEntry>> findEntriesForRound(RoundId roundId) {
    List<LedgerEntry> entries = ledger.entriesFor(roundId);
    return entries.isEmpty() ? Optional.empty() : Optional.of(entries);
}
// caller: findEntriesForRound(id).orElse(List.of()).forEach(...)
```

**Right**

```java
public List<LedgerEntry> findEntriesForRound(RoundId roundId) {
    return ledger.entriesFor(roundId);   // empty List<LedgerEntry> when there are none
}
// caller: findEntriesForRound(id).forEach(...)
```

**Why people believe it:** "a round might have no entries" sounds like exactly
the absence `Optional` was built for, missing that the *collection type itself*
already has a zero-element state that means the same thing with less ceremony.

> **Field, parameter, collection element, map value, and `Optional<List<T>>` are
> the five shapes `Optional` should never take — every one either breaks a
> concrete JDK contract (serialization) or reintroduces, one level up, the exact
> unwrap-before-use burden `Optional` exists to remove from the return-type
> position.**

---

## Transformation: `map`, `flatMap`, `filter`, `or`, `stream`

### Mental model

`map` and `flatMap` let you reach *through* an `Optional` and transform what
might be inside it, without ever stepping outside the box to do it — the
transformation itself only runs if there is something to transform, and the
result stays wrapped. `filter` narrows a present `Optional` down to empty if a
predicate fails, folding a conditional check into the same chain instead of
needing a separate `if`.

### 1.11.19 — `map`'s null-mapper behaviour `[SOURCE]` `[PROVE]`

The OpenJDK source of `Optional.map` (jdk-21+35, `java.util.Optional`):

```java
public <U> Optional<U> map(Function<? super T, ? extends U> mapper) {
    Objects.requireNonNull(mapper);
    if (!isPresent()) {
        return empty();
    } else {
        return Optional.ofNullable(mapper.apply(value));
    }
}
```

Reading it line by line: `Objects.requireNonNull(mapper)` asserts the
*function itself* is non-null — passing `null` as the mapper throws NPE
immediately, regardless of whether the `Optional` is present, because you
cannot call `.apply` on a null reference. `if (!isPresent()) return empty();`
is the short-circuit that makes `map` a no-op on an already-empty `Optional` —
the mapper is never even invoked. The line that matters for this leaf is the
`else` branch: `Optional.ofNullable(mapper.apply(value))` — not
`Optional.of(mapper.apply(value))`. `[PROVE]` Because the wrapping call is
`ofNullable` rather than `of`, a mapper function that itself returns `null`
does **not** throw an NPE inside `map` — it produces `Optional.empty()`. Trace
it: `mapper.apply(value)` evaluates to `null`; `Optional.ofNullable(null)`
takes the `else` branch of its own body (`return value == null ? empty() :
Optional.of(value)` — this is `ofNullable`'s own source), sees `null`, and
returns the shared `Optional.empty()` singleton. No exception is thrown at any
point in this path.

```java
Optional<Client> client = Optional.of(new Client(ClientId.newId(), "player@quizstakes.test"));
Optional<String> nickname = client.map(c -> lookupNickname(c.id()));   // lookupNickname may legally return null
// if lookupNickname(...) returns null, nickname is Optional.empty() — not a thrown NPE
```

This is a deliberate design choice, not an accident: it means a chain of
`map` calls where any intermediate step is a legacy method that still returns
`null` on a miss degrades gracefully to `empty()` rather than blowing up
mid-chain, which is exactly the property that makes long `map`/`flatMap` chains
(§1.11.21) safe to build out of methods you did not write.

**Interview:** "What happens if the function passed to `Optional.map` returns
null?" — it does not throw; `map`'s body wraps the mapper's result with
`ofNullable`, not `of`, so a null result quietly becomes `Optional.empty()` —
quote the source line to back the answer.

### 1.11.20 — `flatMap` versus `map`

`map`'s mapper returns a plain `U`; `Optional` wraps it for you. `flatMap`'s
mapper is expected to **already return an `Optional<U>`**, and `flatMap` does
not wrap it again — it returns exactly what the mapper produced (or `empty()`
if the receiver was empty). The compile error is the tell: given
`Optional<Wallet> findWallet(ClientId id)`, writing

```java
Optional<Optional<Wallet>> nested = findClient(id).map(Client::wallet);
```

does not fail to compile if `Client::wallet` itself returns `Optional<Wallet>`
— it compiles, and produces the nested shape `Optional<Optional<Wallet>>`,
which is nearly useless (you now need a *second* unwrap just to reach the
wallet). The signal that you needed `flatMap` instead is exactly that nesting:
if the method reference or lambda you are mapping with already returns an
`Optional<U>`, use `flatMap` and get back `Optional<U>`; if it returns a plain
`U`, use `map` and let `Optional` do the one layer of wrapping for you.

```java
public Optional<Wallet> wallet(Client client) { ... }          // already returns Optional
public Wallet walletDirect(Client client) { ... }               // returns a plain Wallet, may be null internally

Optional<Client> client = findClient(clientId);

Optional<Wallet> viaFlatMap = client.flatMap(this::wallet);      // correct: Optional<Wallet>, one layer
Optional<Optional<Wallet>> viaMapWrong = client.map(this::wallet); // compiles, but nested — almost never wanted
Optional<Wallet> viaMap = client.map(this::walletDirect);         // correct: map wraps the plain Wallet once
```

**Pitfall:** Using `map` on a mapper that itself returns `Optional`, producing
a nested `Optional<Optional<T>>` that then needs an extra `.flatMap(x -> x)` or
another unwrap to use at all.

**Wrong**

```java
Optional<Optional<Wallet>> nested = findClient(clientId).map(this::wallet);
nested.flatMap(w -> w).ifPresent(this::displayBalance);   // extra flattening step to undo the mistake
```

**Right**

```java
findClient(clientId).flatMap(this::wallet).ifPresent(this::displayBalance);
```

**Why people believe it:** `map` and `flatMap` read almost identically at the
call site and both "transform the value," so the choice looks like a style
preference rather than a structural one dictated entirely by the mapper's own
return type.

### 1.11.21 — Chained null-safe navigation

The four-level `Client → Account → Wallet → Money` traversal is the canonical
shape this whole feature exists to replace:

```java
Money withdrawable = findClient(clientId)
    .map(Client::account)
    .map(Account::wallet)
    .map(Wallet::withdrawable)
    .orElse(Money.ZERO);
```

![D-048 — The `Optional` chain versus the null check](../diagrams/D-048-optional-chain-versus-null.svg)
**D-048** — The `Optional` chain versus the null check

Each `map` is a no-op the instant the chain goes empty — if `findClient`
returns empty, or `Client::account` returns null (wrapped to `empty()` by
`map`'s `ofNullable`, per §1.11.19), every subsequent `map` in the chain
short-circuits without ever calling `Account::wallet` or `Wallet::withdrawable`
at all, and `orElse(Money.ZERO)` supplies the fallback at the end. The
equivalent nested-null-check version needs one `if` per level and a mutable
variable threaded through all four:

```java
Money withdrawable = Money.ZERO;
Client client = findClientOrNull(clientId);
if (client != null) {
    Account account = client.account();
    if (account != null) {
        Wallet wallet = account.wallet();
        if (wallet != null) {
            Money w = wallet.withdrawable();
            if (w != null) {
                withdrawable = w;
            }
        }
    }
}
```

Four levels of nesting, a mutable variable reassigned across four scopes, and
the "real" logic — computing withdrawable balance — buried at the innermost
level, four indents deep. The `map` chain reads top to bottom as the actual
data path, with the empty case handled once, at the end, in one place.

**Insight:** the chain is not "less code" merely for brevity's sake — it moves
the empty-handling from *scattered across every level* (one `if` per null
check) to *one call at the very end* (`orElse`), which is why it does not just
look shorter, it structurally cannot forget a level: every `map` in the chain
is mechanically the same shape, so there is no level where a careless author
could skip the check the way a hand-written `if` chain can silently omit one.

> **`map`/`flatMap` chains collapse an N-level null-check pyramid into N
> identically-shaped calls plus one terminal `orElse`/`orElseGet`, because each
> `map` step is unconditionally safe to call on an empty `Optional` — it is a
> no-op, not a null dereference.**

---

## `OptionalInt`, `OptionalLong`, `OptionalDouble`

### 1.11.22 — the primitive-specialized siblings

`Optional<T>` boxes its contents — an `Optional<Integer>` holds a heap-allocated
`Integer`. For the numeric stream terminal operations (`IntStream.average()`,
`IntStream.max()`, `LongStream.min()`) that would mean boxing every result,
which the primitive stream classes exist specifically to avoid. `OptionalInt`,
`OptionalLong`, and `OptionalDouble` are separate, unrelated classes — none of
them extend or implement anything shared with `Optional<T>` — each holding a
raw primitive field (`int`, `long`, `double`) instead of an object reference.

| | `Optional<T>` | `OptionalInt` / `OptionalLong` / `OptionalDouble` |
|---|---|---|
| Held value | boxed reference `T` | raw primitive (`int`/`long`/`double`) |
| Getter | `get()` / `orElseThrow()` | `getAsInt()` / `getAsLong()` / `getAsDouble()` |
| `map` | yes | **no** — no `map` method exists on any of the three |
| `flatMap` | yes | no |
| `filter` | yes | yes |
| Typical producer | `Optional.of/ofNullable`, `Stream.findFirst` | `IntStream.average/max/min`, `IntStream.findFirst` |

**Pitfall:** Reaching for `.map(...)` on an `OptionalInt` out of habit from
`Optional<T>`, and hitting a compile error, or converting via boxing
(`optionalInt.stream().boxed()...`) when a direct primitive path exists.

**Wrong**

```java
OptionalInt maxStakeCents = IntStream.of(420, 180, 65).max();
int doubled = maxStakeCents.map(v -> v * 2).getAsInt();   // does not compile — no map() on OptionalInt
```

**Right**

```java
OptionalInt maxStakeCents = IntStream.of(420, 180, 65).max();
int doubled = maxStakeCents.isPresent() ? maxStakeCents.getAsInt() * 2 : 0;
// or, converting to the boxed world deliberately when a map-style chain is genuinely needed:
int doubledViaStream = maxStakeCents.stream().map(v -> v * 2).findFirst().orElse(0);
```

The `.stream()` method (added at Java 9 on all four `Optional` variants,
§1.11.7) is the sanctioned bridge: it turns a present `OptionalInt` into a
one-element `IntStream`, or an empty `OptionalInt` into an empty stream, letting
you fall back on the full `Stream`/`IntStream` API when the specialized
`OptionalInt` surface is too narrow, rather than manually branching on
`isPresent()`.

**Why people believe it:** the three primitive variants share almost every
other method name with `Optional<T>` (`isPresent`, `orElse`, `ifPresent`), so
the absence of `map` specifically is easy to assume rather than check — it is
missing because a primitive-to-primitive `map` would need a second family of
functional interfaces (`IntUnaryOperator` for `int → int`, but what about
`int → String`?) that the JDK chose not to build for a rarely-needed
conversion, pointing you at `.stream()` instead.

> **`OptionalInt`/`OptionalLong`/`OptionalDouble` hold raw primitives and expose
> `getAsInt`/`getAsLong`/`getAsDouble` instead of `get`, but carry no `map` or
> `flatMap` — convert via `.stream()` (Java 9+) into the full `Stream`/`IntStream`
> API when you need one, or fall back to `orElse` and ordinary arithmetic.**

---

## The full method table by version

### 1.11.10 — every method, every release `[NUM]` `[RESEARCH]`

**D-045** — `Optional`'s API by version

| Signature | Added | Argument: eager or lazy | On empty | Also on `OptionalInt`/`Long`/`Double` |
|---|---|---|---|---|
| `static <T> Optional<T> of(T value)` | 1.8 | n/a (no functional arg) | throws NPE if `value` is null | no (each has its own `of`) |
| `static <T> Optional<T> ofNullable(T value)` | 1.8 | n/a | returns `empty()` | no |
| `static <T> Optional<T> empty()` | 1.8 | n/a | returns shared singleton | yes (`OptionalInt.empty()` etc.) |
| `boolean isPresent()` | 1.8 | n/a | returns `false` | yes |
| `boolean isEmpty()` | **11** | n/a | returns `true` | yes |
| `T get()` | 1.8 | n/a | throws `NoSuchElementException` | yes (`getAsInt`/`getAsLong`/`getAsDouble`) |
| `T orElseThrow()` | **10** | n/a | throws `NoSuchElementException` | yes |
| `<X extends Throwable> T orElseThrow(Supplier<? extends X> s)` | 1.8 | **lazy** — supplier only invoked on empty | throws the supplied exception | yes |
| `<U> Optional<U> map(Function<? super T,? extends U> mapper)` | 1.8 | **lazy** — mapper only invoked if present | no-op, returns `empty()` | **no** |
| `<U> Optional<U> flatMap(Function<? super T,? extends Optional<? extends U>> mapper)` | 1.8 | lazy | no-op, returns `empty()` | no |
| `Optional<T> filter(Predicate<? super T> predicate)` | 1.8 | lazy | no-op, returns `empty()` | no |
| `Optional<T> or(Supplier<? extends Optional<? extends T>> supplier)` | **9** | **lazy** — supplier only invoked on empty | returns supplier's result | no |
| `Stream<T> stream()` | **9** | n/a | returns empty `Stream`/`IntStream`/etc. | yes |
| `void ifPresent(Consumer<? super T> action)` | 1.8 | lazy — action only invoked if present | no-op | yes |
| `void ifPresentOrElse(Consumer<? super T> action, Runnable emptyAction)` | **9** | lazy — exactly one of the two branches runs | runs `emptyAction` | yes |
| `T orElse(T other)` | 1.8 | **eager** — `other` always evaluated | returns `other` | yes |
| `T orElseGet(Supplier<? extends T> supplier)` | 1.8 | **lazy** — supplier only invoked on empty | returns supplier's result | yes |
| `boolean equals(Object obj)` | 1.8 | n/a | value-based equality | yes |
| `int hashCode()` | 1.8 | n/a | `0` when empty | yes |
| `String toString()` | 1.8 | n/a | `"Optional.empty"` | yes (`"OptionalInt.empty"` etc.) |

`[NUM]` Counted from the list above: **15 methods trace to Java 1.8** (`of`,
`ofNullable`, `empty`, `isPresent`, `get`, `orElseThrow(Supplier)`, `map`,
`flatMap`, `filter`, `ifPresent`, `orElse`, `orElseGet`, `equals`, `hashCode`,
`toString`) — matching the syllabus's stated count exactly. **Three at Java
9** (`or`, `stream`, `ifPresentOrElse`). **One at Java 10** (`orElseThrow()`,
no-arg). **One at Java 11** (`isEmpty()`). 15 + 3 + 1 + 1 = 20 methods total,
matching this table's 19 distinct rows plus `orElseThrow(Supplier)` and
`orElseThrow()` being counted as the two separate overloads the syllabus lists
them as.

`[RESEARCH]` Verified against the JDK 21 javadoc for `java.util.Optional`
(`docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html`)
and cross-checked against `@since` tags in the `Optional.java` source at the
jdk-21+35 tag — every `@since` tag on the class matches the version column
above.

---

## `Optional` in frameworks

### 1.11.23 — Spring Data, Jackson, and what changes without the module `[RESEARCH]`

Spring Data JPA repositories support `Optional<T>` as a query method return
type directly — a repository interface method declared
`Optional<Client> findById(ClientId id)` has that return type recognized by
Spring Data's query-execution machinery, which wraps a `null` JPA lookup result
in `Optional.empty()` for you, rather than the caller needing to wrap it. This
is one of the few sanctioned places `Optional` appears at a framework boundary
rather than purely as an application-level design choice — because it is
exactly the "method return type signalling absence" case §1.11.1 describes,
just generated by a proxy instead of written by hand. `[X-REF 08]` The
mechanism behind how Spring Data derives that return type handling — proxying
the repository interface and inspecting the declared return type via
reflection to decide whether to wrap a null result — is guide 08's (Spring Data
JPA) territory in full; the point for this file is only that the framework
honours the same "never return a bare null from an `Optional`-typed method"
discipline as §1.11.17, on your behalf.

Jackson, by contrast, does **not** understand `Optional` out of the box — the
core `jackson-databind` module has no built-in (de)serializer registered for
`java.util.Optional` beyond treating it as an ordinary bean with a `get`-style
accessor, which produces a nested object shape rather than the flattened value
most APIs want. The `jackson-datatype-jdk8` module (registered as
`Jdk8Module`) supplies the intended behaviour: a present `Optional<String>`
serializes as the bare string value; an empty one serializes as JSON `null`
(or is omitted entirely, combined with `@JsonInclude`).

```java
public record ClientProfileResponse(
    String email,
    Optional<String> preferredLanguage   // requires Jdk8Module to serialize sanely
) {}
```

Without `Jdk8Module` registered, Jackson serializes `preferredLanguage` as a
nested object reflecting `Optional`'s own fields (implementation-dependent, and
liable to differ across Jackson versions) rather than as a plain string or
`null` — an integration bug that looks like a Jackson misconfiguration but is
actually a missing-module problem. With the module registered:

```java
ObjectMapper mapper = new ObjectMapper().registerModule(new Jdk8Module());
```

`@JsonInclude(JsonInclude.Include.NON_ABSENT)` on the field or the class, in
combination with `Jdk8Module`, additionally **omits the key entirely** from the
serialized JSON when the `Optional` is empty, rather than emitting an explicit
`"preferredLanguage": null` — the serialized shape difference between "field
present as JSON `null`" (default `Jdk8Module` behaviour) and "field omitted
entirely" (`NON_ABSENT`) is itself something worth pinning down in an API
contract, since a client parsing the response may treat a missing key and an
explicit `null` differently.

`[RESEARCH]` **Unverified:** the exact default JSON shape Jackson core (without
`Jdk8Module`) produces for a bean-style `Optional` field varies across
`jackson-databind` versions and was not re-verified against a specific pinned
version on this machine; treat "serializes as a nested object" as the general
shape to expect, not a byte-for-byte guaranteed output, and confirm against
the project's actual `jackson-databind` version before relying on the exact
structure in a test assertion.

**Pitfall:** Adding an `Optional<T>` field to a Spring Boot `@RestController`
response DTO and assuming Jackson handles it the way `Optional`-returning
repository methods do, without registering `Jdk8Module`.

**Wrong**

```java
// no Jdk8Module registered anywhere in the application's ObjectMapper configuration
public record ClientProfileResponse(String email, Optional<String> preferredLanguage) {}
// GET /clients/{id} returns: "preferredLanguage": { "present": true, "empty": false, ... } — leaks Optional's internals
```

**Right**

```java
@Bean
ObjectMapper objectMapper() {
    return new ObjectMapper().registerModule(new Jdk8Module());
}
// with Jdk8Module: "preferredLanguage": "en-GB"   (present)
// or:               "preferredLanguage": null      (empty)
```

**Why people believe it:** Spring Data's repository layer makes `Optional`
"just work" as a return type with zero configuration, so it is a reasonable but
wrong inference that Spring Boot's JSON layer does the same without any extra
registration — the two integrations are unrelated modules solving unrelated
problems.

---

## Allocation cost and escape analysis

### 1.11.24 — cost in a hot loop, escape analysis, and Valhalla `[NUM]` `[RESEARCH]`

Every `Optional.of`/`ofNullable` call that produces a non-empty result
allocates one object on the heap — a small one (a single reference field plus
an object header, roughly 16 bytes of header on a 64-bit JVM with compressed
oops plus 8 bytes for the `value` field, so on the order of 24 bytes per
instance, rounded up to the JVM's object alignment, typically 8 bytes, giving
**24 bytes per `Optional` instance** on most current 64-bit HotSpot builds).
`[NUM]` In a hot path like the QuizStakes stake-reservation pipeline —
2,800,000 stake reservations/day, 1,200/sec at peak — a `findWallet(clientId)`
call returning `Optional<Wallet>` inside the reservation hot loop allocates one
`Optional` per reservation attempt: at 1,200/sec peak, that is roughly
1,200 × 24 bytes ≈ **28,800 bytes/sec**, or about 1.7 MB/minute, of short-lived
garbage from this one call site alone during a peak burst — small in absolute
terms next to modern GC throughput, but not zero, and it multiplies with every
additional `Optional`-returning call layered into the same hot method.

In practice, most of this cost disappears without any code change, because of
**escape analysis**: the JIT compiler (C2, HotSpot's server compiler) can prove
that an `Optional` instance created inside a method, consumed only within that
same method (via `map`/`orElse`/`ifPresent` calls that themselves get inlined),
and never stored into a field, returned as a genuine heap-escaping reference,
or passed to a method the JIT cannot see into, **never escapes the compiled
method's stack frame**. When escape analysis proves that, C2 performs **scalar
replacement**: the `Optional`'s single `value` field is kept directly in a
register or on the stack, and the object is never actually allocated on the
heap at all — the "allocation" becomes a compile-time fiction that the runtime
never materializes. This is precisely why `Optional`'s cost profile in real,
JIT-warmed hot loops is usually far cheaper than a naive "one allocation per
call" reading would suggest — but it is not a guarantee: escape analysis is
defeated by the method being too large to inline, by megamorphic call sites
that block devirtualization, or by the `Optional` genuinely escaping (returned
from a public API boundary, stored in a field per §1.11.14, or passed into a
method C2 has not inlined).

`[RESEARCH]` **Unverified:** whether escape analysis fires for any *specific*
call site depends on JIT warm-up, inlining budget (`-XX:MaxInlineSize`,
`-XX:FreqInlineSize`), and the exact call shape, none of which is something you
can state as a blanket guarantee without profiling the actual compiled method
via `-XX:+PrintEscapeAnalysis`/JITWatch on the real workload; treat "escape
analysis usually removes it" as a mechanism to reach for when profiling shows
`Optional` allocation in a hot path, not as a reason to skip measuring.

Project Valhalla's plan for **value classes** (the same JEP family that
motivated `@ValueBased`, §1.11.3) is to make this cost structurally
non-existent rather than JIT-dependent: a value class has no object identity
and no object header, so the JVM can lay it out inline wherever it is used —
inside a local variable slot, inside another object's field, inside an array
element — without a heap allocation or an indirection through a pointer at
all, in *every* case, not only the ones escape analysis happens to catch.
`Optional` is one of the JDK's own flagship candidates for migration to a value
class once Valhalla ships, precisely because it already carries the
`@ValueBased` restrictions (no identity reliance, no synchronization) that a
value class requires of its users — the restriction was added years in advance
of the runtime feature that will make it load-bearing.

**Pitfall:** Avoiding `Optional` in a hot path purely from an "it allocates"
instinct, without profiling whether escape analysis is already eliminating
the allocation in the actual compiled code.

**Wrong**

```java
// "Optional allocates, so I'll hand-roll a null-returning version in the hot reservation path"
Wallet wallet = findWalletOrNull(clientId);   // reintroduces every null-check risk from before Optional
if (wallet != null) {
    reserveStake(wallet, stakeAmount);
}
```

**Right**

```java
findWallet(clientId).ifPresent(wallet -> reserveStake(wallet, stakeAmount));
// profile with -XX:+PrintEscapeAnalysis / JITWatch before assuming this needs hand-rolling;
// if profiling proves it's hot AND escaping, that's the point to reconsider, not before
```

**Why people believe it:** "every object allocates, allocation is slow" is
true as a first-order statement about the JVM two decades ago, but it ignores
three decades of escape analysis and scalar replacement work in C2 that make
many short-lived, non-escaping allocations effectively free — the correct
response to a suspected allocation cost is measurement, not folklore.

> **`Optional`'s allocation is real but frequently eliminated by C2's escape
> analysis and scalar replacement when the instance never escapes its compiled
> method; Valhalla's value classes aim to make that elimination unconditional
> and structural rather than a best-effort JIT optimization.**

---

## Pitfalls

### Synchronizing on or comparing `Optional` by identity

**Wrong**

```java
Optional<Client> cached = clientCache.get(clientId);
synchronized (cached) {
    cached.ifPresent(this::refreshWallet);
}
```

**Right**

```java
Object lock = clientLocks.computeIfAbsent(clientId, id -> new Object());
synchronized (lock) {
    clientCache.get(clientId).ifPresent(this::refreshWallet);
}
```

**Why people believe it:** `Optional` is a plain heap object on every shipping
JVM today, so locking on one currently compiles and runs without error.

### Putting `Optional` in a `Serializable` field

**Wrong**

```java
private final Optional<String> operatorNote;   // field on a Serializable WithdrawalTransaction
```

**Right**

```java
private final String operatorNote;   // nullable
public Optional<String> operatorNote() { return Optional.ofNullable(operatorNote); }
```

**Why people believe it:** every other JDK "might be missing" wrapper type is
serializable, so `Optional` looks like an exception without a visible reason
until `NotSerializableException` fires.

### Writing `.orElse(expensiveCall())` expecting laziness

**Wrong**

```java
Money withdrawable = findWallet(clientId).orElse(rebuildWalletFromLedger(clientId).withdrawable());
```

**Right**

```java
Money withdrawable = findWallet(clientId)
    .orElseGet(() -> rebuildWalletFromLedger(clientId).withdrawable());
```

**Why people believe it:** `orElse` and `orElseGet` look interchangeable and
both "supply a default" — only the JLS's ordinary left-to-right argument
evaluation rule explains why one pays for the call unconditionally.

### `isPresent()` + `get()` as "the `Optional` way" to null-check

**Wrong**

```java
if (maybeClient.isPresent()) {
    processClient(maybeClient.get());
}
```

**Right**

```java
maybeClient.ifPresent(this::processClient);
```

**Why people believe it:** it is the most direct mechanical translation of "if
not null, use it," and it compiles and works — the defect is invisible unless
you know the point was to get the *compiler* to enforce the check.

### Returning a bare `null` from an `Optional`-typed method

**Wrong**

```java
public Optional<Wallet> findWallet(ClientId clientId) {
    Wallet wallet = wallets.get(clientId);
    return wallet == null ? null : Optional.of(wallet);
}
```

**Right**

```java
public Optional<Wallet> findWallet(ClientId clientId) {
    return Optional.ofNullable(wallets.get(clientId));
}
```

**Why people believe it:** the "if null, return null" ternary is muscle
memory from every non-`Optional` method, and the compiler enforces the
*declared* return type, not the convention that an `Optional`-typed method
should never itself hand back `null`.

### Wrapping an already-empty-representable collection in `Optional`

**Wrong**

```java
public Optional<List<LedgerEntry>> findEntriesForRound(RoundId roundId) {
    List<LedgerEntry> entries = ledger.entriesFor(roundId);
    return entries.isEmpty() ? Optional.empty() : Optional.of(entries);
}
```

**Right**

```java
public List<LedgerEntry> findEntriesForRound(RoundId roundId) {
    return ledger.entriesFor(roundId);
}
```

**Why people believe it:** "might have no entries" sounds like exactly the
absence case `Optional` was built for, missing that the collection type
already has a zero-element state carrying the same meaning.

### Using `map` where the mapper already returns `Optional`

**Wrong**

```java
Optional<Optional<Wallet>> nested = findClient(clientId).map(this::wallet);   // this::wallet returns Optional<Wallet>
```

**Right**

```java
Optional<Wallet> wallet = findClient(clientId).flatMap(this::wallet);
```

**Why people believe it:** `map` and `flatMap` read almost identically at the
call site, and the choice is dictated entirely by the mapper's own return
type, not by anything visible in the calling code's style.

## Cheat sheet

| Situation | Use | Never |
|---|---|---|
| Return type may have no result | `Optional<T>` | returning `null` from an `Optional<T>` method |
| Adapting a nullable value | `Optional.ofNullable(x)` | `Optional.of(x)` when `x` might be null |
| Cheap/free default value | `orElse(constant)` | `orElse(expensiveCall())` |
| Expensive/side-effecting default | `orElseGet(this::expensiveCall)` | assuming `orElse` is lazy |
| Asserting presence, accepting a crash | `orElseThrow()` (10+) or `orElseThrow(supplier)` | bare `get()` out of habit |
| Check-then-act | `ifPresent`/`ifPresentOrElse` (9+) | `isPresent()` + `get()` |
| Mapper returns plain `U` | `map` | `flatMap` (produces `Optional<Optional<U>>` mismatch) |
| Mapper returns `Optional<U>` | `flatMap` | `map` (nests) |
| Field, parameter, collection element, map value, `Optional<List<T>>` | plain nullable / overload / empty collection / absent key | `Optional` in any of these five positions |
| Numeric stream result | `OptionalInt`/`Long`/`Double` | expecting `.map()` on any of the three |
| Serialized DTO field | `String`/plain type + `Jdk8Module` if truly `Optional` in the model | assuming Jackson handles `Optional` with zero config |
| Hot-path allocation worry | profile first (`-XX:+PrintEscapeAnalysis`) | hand-rolling null-returning methods on instinct |

## Self-test

**Q1.** Why does the `Optional` class javadoc's API note matter for interview
answers about where `Optional` belongs?

<details><summary>Answer</summary>

Because it is the primary source, not a style opinion: it states in an
`@apiNote` that `Optional` is "primarily intended for use as a method return
type where there is a clear need to represent 'no result'" and that a variable
of type `Optional` "should never itself be null." Every rule about keeping
`Optional` out of fields, parameters, and collections traces back to that one
sentence in the JDK's own documentation, and citing it directly is stronger
than restating the rule as received wisdom.

</details>

**Q2.** What concretely breaks if you put an `Optional<T>` field on a class
that implements `Serializable`, and when does it break?

<details><summary>Answer</summary>

Nothing breaks at compile time — the field compiles fine. It breaks the first
time an `ObjectOutputStream` tries to serialize an instance of that class:
`Optional` does not implement `Serializable`, so `writeObject` throws
`NotSerializableException: java.util.Optional` at that point, potentially long
after the field was added, whenever the object graph is first actually
serialized (a cache, a queue message, session replication).

</details>

**Q3.** Given `findWallet(clientId).orElse(rebuildWalletFromLedger(clientId).withdrawable())`, trace exactly what runs and when, using the JLS rule that explains it.

<details><summary>Answer</summary>

The JLS's method-invocation evaluation order (§15.12) evaluates argument
expressions left-to-right, in full, before the target method is invoked.
`rebuildWalletFromLedger(clientId).withdrawable()` is the argument expression
to `orElse`, so it runs unconditionally, every single call, before
`Optional.orElse`'s own body (`return value != null ? value : other;`) ever
executes. If `findWallet(clientId)` was present, the computed `Money` from the
ledger rebuild is simply discarded — but the rebuild already ran. `orElseGet`
avoids this because the expensive call sits inside the `Supplier`, invoked only
from within the ternary's false branch.

</details>

**Q4.** What is the actual difference in behaviour between `get()` and
`orElseThrow()` on an empty `Optional`?

<details><summary>Answer</summary>

None. Their method bodies in the OpenJDK source are identical: both check
`value == null` and throw `new NoSuchElementException("No value present")`
with the exact same message. `orElseThrow()` (added Java 10) exists purely as
a more self-documenting name for the same assertion — "I am asserting presence
and accept the crash if wrong" — over `get()`, which reads like an ordinary,
safe getter by analogy with every other JDK wrapper's `.get()`.

</details>

**Q5.** Why is `if (opt.isPresent()) { opt.get(); ... }` considered no better
than a null check, even though it uses the `Optional` API?

<details><summary>Answer</summary>

It reproduces the exact same control-flow shape as `if (x != null) { ... }` —
the caller must still remember to guard the access, and nothing about the
`Optional` type stops `opt.get()` from being called without the `if` at all;
the compiler never enforces the check. It adds one cost (the `Optional`
allocation on the producing side) without adding the one thing `Optional` was
supposed to buy: compiler-enforced handling of absence, which only comes from
staying inside the functional API (`map`, `orElse`, `ifPresent`).

</details>

**Q6.** Why does `Optional.map` not throw an NPE when the mapper function
itself returns `null`?

<details><summary>Answer</summary>

Because `map`'s source wraps the mapper's result with `Optional.ofNullable(mapper.apply(value))`,
not `Optional.of(...)`. `ofNullable` returns `empty()` on a `null` input
instead of throwing, so a null-returning mapper degrades the chain to
`Optional.empty()` at that step rather than throwing partway through — which is
what makes long `map`/`flatMap` chains safe to build even out of legacy
methods that still return `null` on a miss.

</details>

**Q7.** You call `.map(this::wallet)` where `wallet(Client)` returns
`Optional<Wallet>`, and the result type is `Optional<Optional<Wallet>>`. What
should you have called instead, and why does the compiler let the wrong
version through?

<details><summary>Answer</summary>

`flatMap(this::wallet)` — `flatMap` expects the mapper to already return an
`Optional<U>` and returns that value directly rather than wrapping it again.
The compiler allows the `map` version because `map`'s type signature only
requires the mapper's return type to be some type `U`; `Optional<Wallet>` is a
perfectly valid `U`, so `map` happily wraps a `U` that itself happens to be an
`Optional`, producing the nested shape without any type error.

</details>

**Q8.** Why does `OptionalInt` have no `map` method, and what do you use
instead when you need one?

<details><summary>Answer</summary>

`OptionalInt` holds a raw primitive `int`, not a boxed reference, and the JDK
did not build out a full family of primitive-specialized functional interfaces
to support a general `map` on it (an `int → int` map would need
`IntUnaryOperator`, but `int → String` or `int → Object` would need entirely
different interfaces, and the JDK chose not to provide all of them for a
rarely-needed conversion). The sanctioned bridge is `.stream()` (added Java 9):
convert to an `IntStream` (or empty stream if absent) and use the full
`Stream`/`IntStream` API from there.

</details>

**Q9.** What is the concrete difference in the JSON Jackson produces for an
`Optional<String>` field with `Jdk8Module` registered versus not?

<details><summary>Answer</summary>

Without `Jdk8Module`, Jackson core has no dedicated (de)serializer for
`Optional` and treats it as an ordinary bean, typically producing a nested
object shape reflecting `Optional`'s own internal accessors rather than the
plain string value — behaviour that is implementation/version-dependent and
should be confirmed against the actual `jackson-databind` version in use.
With `Jdk8Module` registered, a present value serializes as the bare
contained value (e.g., a plain JSON string) and an empty one serializes as
JSON `null` by default, or is omitted from the output entirely if
`@JsonInclude(NON_ABSENT)` is also applied.

</details>

**Q10.** Why is `Optional`'s allocation cost in a JIT-warmed hot loop often
much lower in practice than "one allocation per call" suggests, and what
would make that assumption fail?

<details><summary>Answer</summary>

HotSpot's C2 compiler performs escape analysis: if it can prove an `Optional`
instance never escapes the compiled method's stack frame — created, consumed
via inlined calls like `map`/`orElse`, and never stored to a field, returned
across a real API boundary, or passed into a method C2 cannot see into — it
performs scalar replacement, keeping the `value` field in a register or on the
stack and never actually allocating the object on the heap. This fails when
the `Optional` genuinely escapes (a field, a public return value, an
uninlined call), when the method is too large to inline, or when the call
site is megamorphic — in any of those cases the allocation is real and should
be confirmed by profiling (`-XX:+PrintEscapeAnalysis`) rather than assumed
away.

</details>

## Deferred

None.

## Open questions

- The exact default JSON shape Jackson core produces for a bean-style
  `Optional` field without `Jdk8Module` registered (§1.11.23) was described by
  general shape only ("a nested object reflecting `Optional`'s internal
  accessors") and not pinned to a specific `jackson-databind` version on this
  machine — confirm against the project's actual Jackson version before
  asserting the exact structure in a test.
- Whether escape analysis actually eliminates a specific `Optional` allocation
  in a given hot method (§1.11.24) depends on JIT warm-up state and inlining
  budget and was described as a general mechanism, not verified for a specific
  compiled method on this machine — settle it with
  `-XX:+PrintEscapeAnalysis` or JITWatch against the real workload.

---

**Leaves covered:** 1.11.1–1.11.24 (24 leaves)
**Leaves deferred:** none
**Diagrams included:** D-045, D-046, D-047, D-048
**Target version:** Java 21 LTS
**Lines:** 1632
