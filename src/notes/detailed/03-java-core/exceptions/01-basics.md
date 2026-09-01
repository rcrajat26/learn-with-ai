# 03 Java Core — The exception model — BASICS (§1.20)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Generated methods, sealed types, fit](../records-and-sealed/01a-object-methods-sealed-and-fit.md) · Next: [`Throwable`'s API and exception chaining](01a-throwable-api-and-chaining.md)

Every method call in QuizStakes is a promise with an escape hatch: `PaymentService.reserveStake` promises to reserve funds, but it also has to say what it does when it cannot. Java's exception model is the type system's answer to "what happens when this promise fails" — and unlike most of the type system, half of it is enforced by the compiler and half of it is enforced by nothing at all except code review. Knowing which half you are in, for any given exception, is the single most load-bearing fact in this file.

Everything below is measured against **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**.

---

## 1. The `Throwable` hierarchy, and checked vs unchecked as a JLS rule (1.20.1, 1.20.2)

Picture four shelves stacked on top of each other. `Throwable` is the shelf unit itself — anything that can be thrown or caught lives somewhere on it. `Error` and `Exception` are the two top-level compartments. Inside `Exception` there is one more compartment, `RuntimeException`. The rule the compiler enforces is not "which compartment am I in" — it is "am I inside the `RuntimeException` compartment, or the `Error` compartment, or neither." Everything in neither compartment is **checked**. Everything in either compartment is **unchecked**. That single sentence is the entire rule, and it is stated formally in JLS 21 §11.1.1.

### Why it exists

Before checked exceptions, C-style error handling relied on return codes (`-1`, `NULL`, `errno`) that a caller could silently ignore — and did, constantly, because nothing forced acknowledgment. Java's designers wanted a category of failure that a caller is *statically* forced to handle or admit to propagating: a caller of `FundsLedger.append` cannot pretend `SQLException` does not exist, because the code will not compile until they catch it or declare it. The second category — unchecked — exists because forcing that same discipline onto programmer-error signals (`NullPointerException`, `IndexOutOfBoundsException`) would mean every method calling `array[i]` or `x.getY()` needs a `throws` clause, which the language designers judged as pure noise: bugs, not conditions a caller could sensibly plan a recovery path around at every call site.

### When to reach for which, and when not

This file states the *language rule* only — where a `Throwable` sits determines whether `javac` enforces catch-or-declare. The *design decision* — which of your own exceptions, like `InsufficientFundsException` or `RestrictedActionException`, should be checked versus unchecked, and why virtually everything QuizStakes defines is unchecked by policy — belongs to [`02-in-practice.md`](02-in-practice.md) (INTERMEDIATE tier). Do not look for that judgment here; this file only tells you how the compiler classifies what already exists.

### How it works

Four families, one rule.

| Family | Root | Checked or unchecked | Who throws it |
|---|---|---|---|
| JVM-fatal | `Error` | Unchecked | The JVM itself, almost never application code |
| Recoverable, forced acknowledgment | `Exception` minus `RuntimeException` | Checked | I/O, SQL, threading, reflection — external failure modes |
| Recoverable, programmer discretion | `RuntimeException` | Unchecked | Application code and the JDK's own precondition checks |
| Everything else under `Exception` directly | `Exception` (direct subclasses) | Checked | `ClassNotFoundException`, `CloneNotSupportedException` |

The rule in JLS 21 §11.1.1, verbatim in effect: *an exception is unchecked if it is `RuntimeException` or a subclass, or `Error` or a subclass; every other `Throwable` is checked.* Note what the rule does **not** say — it does not say "`Exception` is checked, `RuntimeException` is unchecked", because that phrasing would wrongly imply the split happens at the `Exception`/`RuntimeException` boundary alone. It happens at the `RuntimeException` boundary and, separately, at the `Error` boundary. Anything under `Exception` that is not under `RuntimeException` is checked, whether or not it happens to sit directly under `Exception` (`ClassNotFoundException`, `CloneNotSupportedException`) or several levels down inside a checked branch (`SQLTimeoutException` under `SQLException`).

![D-053 — The `Throwable` hierarchy](../diagrams/D-053-throwable-hierarchy.svg)

**D-053** — The four families fanning out from `Throwable`: the `Error` branch (five JVM-fatal types), the checked branch split across two panels (`ClassNotFoundException` and `CloneNotSupportedException` sitting directly under `Exception`; `IOException`, `SQLException`, `InterruptedException`, `TimeoutException` also checked but grouped separately as the I/O-and-concurrency family), and `RuntimeException`'s two unchecked panels — the ten JDK exceptions and the five QuizStakes domain exceptions extending it directly. The annotation panel states the actual rule the figure encodes: checked is everything under `Throwable` except the `Error` subtree and the `RuntimeException` subtree — which is exactly why `ClassNotFoundException` and `CloneNotSupportedException`, sitting directly under `Exception`, are checked despite looking like siblings of `RuntimeException` rather than descendants of it.

QuizStakes declares five domain exceptions, and the hierarchy dictates where each sits and what compiler obligation it carries:

```java
public class InsufficientFundsException extends RuntimeException {
    public InsufficientFundsException(String message) {
        super(message);
    }
}

public class RestrictedActionException extends RuntimeException {
    private final RestrictionType type;

    public RestrictedActionException(RestrictionType type, String message) {
        super(message);
        this.type = type;
    }

    public RestrictionType type() {
        return type;
    }
}

public class IllegalTransitionException extends RuntimeException {
    public IllegalTransitionException(String fromStatus, String toStatus) {
        super("cannot transition from " + fromStatus + " to " + toStatus);
    }
}

public class LedgerImbalanceException extends RuntimeException {
    public LedgerImbalanceException(String message) {
        super(message);
    }
}

public class BonusIneligibleException extends RuntimeException {
    public BonusIneligibleException(String reason) {
        super(reason);
    }
}
```

All five extend `RuntimeException` directly, which makes all five unchecked — a stake rejected for `InsufficientFundsException` or an activation blocked by `RestrictedActionException` never forces a `throws` clause onto `PaymentService.reserveStake` or any caller above it. That is a deliberate policy choice specific to QuizStakes, argued for in [`02-in-practice.md`](02-in-practice.md); the language itself is indifferent to which choice you make, and would have enforced catch-or-declare with equal rigor had these five extended `Exception` directly instead.

**Interview:** "Is `RuntimeException` a subclass of `Exception`?" Yes — `RuntimeException extends Exception extends Throwable`. The unchecked/checked line is drawn *inside* the `Exception` subtree, at the `RuntimeException` boundary, not at the `Exception`/`Throwable` boundary. Candidates who answer "checked exceptions extend `Exception`, unchecked extend `RuntimeException`" are half right and the sloppy half is exactly `ClassNotFoundException`.

> **Definition.** The `Throwable` hierarchy is a tree with two children of the root, `Error` and `Exception`; `RuntimeException` is a subtree of `Exception`; and a `Throwable` is checked, by JLS 21 §11.1.1, precisely when it is neither an `Error` nor a `RuntimeException` — a rule the compiler enforces statically, independent of what actually happens at runtime.

---

## 2. The catch-or-declare requirement, and how it propagates through every intermediate signature (1.20.3)

The mental model: a checked exception is a red thread the compiler ties to a method the moment that method can throw it, and the thread does not come untied on its own. It runs up the call stack, method to method, until either something catches it (cuts the thread) or every intermediate method's signature admits carrying it (`throws SQLException`). A checked exception with no `throws` clause anywhere above the point that throws it, and no `catch` anywhere either, is a compile error — there is no third option.

### Why it exists

The compiler cannot verify that a caller *handles* an exception meaningfully — only that the caller has acknowledged its existence, either by catching it or by admitting responsibility upward. That acknowledgment is what "catch or declare" buys: a reviewer looking at `PaymentService.reserveStake`'s signature can see, without reading its body, that it can fail with a `SQLException` it did not itself decide to swallow.

### When it applies, and when it does not

It applies only to checked exceptions. An unchecked exception — `RestrictedActionException`, `IllegalStateException`, any `Error` — never needs to appear in a `throws` clause and never forces a caller to do anything. This is the exact reason unchecked propagation is silent: nothing in `StakeController.post`'s signature warns a caller that `RestrictedActionException` might come flying out of it, because nothing requires it to.

### How it works

Consider `FundsLedger.append`, which does a JDBC write and therefore can throw the checked `SQLException`:

```java
public class FundsLedger {
    private final DataSource dataSource;

    public FundsLedger(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public void append(LedgerEntry entry) throws SQLException {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(
                 "INSERT INTO ledger_entry (position, amount, currency, round_id) VALUES (?, ?, ?, ?)")) {
            statement.setString(1, entry.position().name());
            statement.setBigDecimal(2, entry.amount().amount());
            statement.setString(3, entry.amount().currency().getCurrencyCode());
            statement.setObject(4, entry.roundId());
            statement.executeUpdate();
        }
    }
}
```

`append` declares `throws SQLException`. Every method that calls it now has exactly two choices, enforced at compile time — catch it, or declare it themselves:

```java
public class PaymentService {
    private final FundsLedger fundsLedger;

    public PaymentService(FundsLedger fundsLedger) {
        this.fundsLedger = fundsLedger;
    }

    public Reservation reserveStake(ClientId clientId, Money stake) throws SQLException {
        if (isRestricted(clientId)) {
            throw new RestrictedActionException(RestrictionType.STAKE_BLOCKED,
                "client " + clientId + " is stake-blocked");
        }
        LedgerEntry entry = new LedgerEntry(LedgerPosition.CLIENT_CASH_RESERVED, stake, clientId);
        fundsLedger.append(entry);
        return new Reservation(clientId, stake);
    }

    private boolean isRestricted(ClientId clientId) {
        return false;
    }
}
```

`reserveStake` declares `throws SQLException` too — not because it does JDBC work itself, but purely because it calls something that does and chose not to catch it. One more level up, `StakeController.post` inherits the same obligation:

```java
public class StakeController {
    private final PaymentService paymentService;

    public StakeController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    public ResponseEntity<Reservation> post(ClientId clientId, Money stake) throws SQLException {
        return ResponseEntity.ok(paymentService.reserveStake(clientId, stake));
    }
}
```

`SQLException` has now polluted three method signatures — `append`, `reserveStake`, `post` — none of which is the layer actually equipped to decide what a database failure *means* to an HTTP caller. That pollution is a real cost, not a hypothetical one, and it is exactly why real Spring Boot code almost never writes what is shown above; [`02-in-practice.md`](02-in-practice.md) covers the standard fix, which is to catch `SQLException` at the boundary closest to where it is thrown and translate it into an unchecked, domain-meaningful exception.

Contrast with `RestrictedActionException`, thrown from the same `reserveStake` method a few lines above `fundsLedger.append`. It never appears in any `throws` clause, propagates through `PaymentService.reserveStake` and `StakeController.post` without either method's signature changing at all, and a caller three frames up can be entirely unaware it exists until it reaches them at runtime. Same call stack, same distance travelled, opposite compiler treatment — because one is checked and one is not.

**Pitfall:** declaring `throws Exception` to make a compile error go away. It compiles, but it also silently swallows the specific-exception information every caller needs — a caller of a method declared `throws Exception` cannot distinguish "this can throw `SQLException`" from "this can throw `InterruptedException`" without reading the implementation, which defeats the entire point of catch-or-declare. The fix is either to declare the specific checked exception, or — the far more common real answer — to translate it to an unchecked exception at the boundary, as `02-in-practice.md` shows.

**Insight:** catch-or-declare is a purely syntactic, compile-time obligation with zero connection to whether the exception is actually likely, actually recoverable, or actually meaningful to the caller three frames up. The compiler is checking that a `throws` clause or a `catch` block exists on the path — it has no opinion on whether the catch block does anything sensible with what it catches. An empty `catch (SQLException e) {}` block satisfies the compiler completely and is a production incident waiting to happen.

> **Definition.** Catch-or-declare requires every method on the call path from where a checked exception is thrown to where it is finally caught to either catch it or add it to its own `throws` clause — a purely compile-time obligation that has no equivalent for unchecked exceptions, which can propagate through any number of stack frames leaving every intermediate signature untouched.

---

## 3. `Error`: JVM-level, and why you do not catch it (1.20.4)

The mental model: an `Error` is not the application telling you something went wrong — it is the platform underneath the application telling you it can no longer guarantee the platform works. Catching an `IOException` means "I know how to recover from a network hiccup." Catching an `OutOfMemoryError` means "I believe I know how to recover from the heap being unable to satisfy an allocation," which is a belief that is usually wrong, because the failure to allocate can strike the very code inside your `catch` block trying to build a log message about it.

### Why it exists as a separate family

`Exception` models failures the *program's logic* can anticipate and route around. `Error` models failures in the *substrate the program runs on* — a full heap, an exhausted native stack, a corrupt or absent class file, a version-mismatched class hierarchy. None of those are things a `catch` block written in ordinary Java can meaningfully repair, because the JVM's ability to execute the recovery code is exactly what is in doubt. Making `Error` unchecked (JLS 21 §11.1.1 places it outside the checked set alongside `RuntimeException`) reflects the same judgment: forcing every method to declare `throws OutOfMemoryError` would be pure noise, since there is no sensible per-call-site handling strategy to declare.

### When you might touch it, and when you never should

You almost never catch `Error` types, full stop. The narrow exception is `AssertionError` in test frameworks, which is not JVM-fatal at all — it is a deliberate, programmer-triggered signal from the `assert` keyword or a testing library's assertion method, and it happens to extend `Error` for historical reasons rather than fatality. Everything else in this family — `OutOfMemoryError`, `StackOverflowError`, `NoClassDefFoundError`, `LinkageError` — you let propagate to the top of the stack and crash the JVM, or the thread, because papering over it hides a substrate problem that will resurface somewhere worse.

### How it works — one mechanism paragraph, pointed at guide 06

Each of the five `Error` types corresponds to a specific point where the JVM's own bookkeeping fails. `StackOverflowError` fires when a thread's call stack — a fixed-size region reserved at thread creation — exceeds its bound, typically from unbounded recursion; `OutOfMemoryError` fires when the garbage collector cannot free enough heap to satisfy an allocation even after a full collection; `NoClassDefFoundError` fires when a class that resolved successfully at compile time is missing at the classloader lookup that happens at first use; `LinkageError` (parent of `NoClassDefFoundError` and several others) fires when a class's binary form is incompatible with what a dependent class expected, usually from redeploying one artifact without recompiling another; `AssertionError` alone is not substrate failure, just a thrown signal from `assert` or a test framework. The heap regions, generations, and classloader delegation that back the first four are guide 06's territory (JVM internals) — see it for GC internals, the JIT, and the classloader hierarchy in full; this file only states what each `Error` means and why you do not catch it.

A recursive `Movement` tree walk without a depth guard is the canonical `StackOverflowError` in QuizStakes — walking a chain of linked ledger movements (a stake's reservation, its settlement, a correction) recursively rather than iteratively:

```java
public class MovementWalker {
    public Money total(Movement movement) {
        Money own = movement.amount();
        if (movement.parent() == null) {
            return own;
        }
        return own.plus(total(movement.parent()));
    }
}
```

If a `Movement` chain is ever accidentally cyclic — a correction whose `parent()` loops back to itself through a data bug — `total` recurses until the thread's stack is exhausted and `StackOverflowError` is thrown, at whatever recursion depth the platform's default stack size (`-Xss`, commonly 512 KB–1 MB depending on platform and JDK) permits. Rewriting `total` iteratively with an explicit `Deque<Movement>` removes the failure mode entirely, independent of chain length.

`OutOfMemoryError` shows up at the other end of the ledger's scale numbers: the ledger's hot window is 90 days at roughly 19.8M entries per day, so loading the full hot window as one in-memory `List<LedgerEntry>` means materializing on the order of 1.78 billion rows — a number nobody should hold in one collection, and exactly the case where `OutOfMemoryError: Java heap space` is not a bug to patch around with a bigger `-Xmx` but a signal that the access pattern needs to be a paginated or streaming query against the ledger store instead.

`NoClassDefFoundError` and `LinkageError` show up together at `AccountActivation` startup in the failure mode every team eventually hits after a partial deploy: `AccountActivation` was compiled against a version of `ScreeningService` with a method that the JAR actually on the classpath at runtime does not have, or does not have at that JAR's version. The class resolved fine at compile time — the compiler saw the method — but the classloader at runtime finds a binary-incompatible `ScreeningService.class` and refuses to link it, throwing `LinkageError` (or its `NoClassDefFoundError` subclass, if the class is simply absent rather than merely mismatched) the first time `AccountActivation` touches it. **Forward link:** a related failure — a *static initializer* throwing during class loading, which the JVM then wraps and remembers as a permanently broken class — is `ExceptionInInitializerError`, covered where it belongs in [`../classes-and-initialization/01d-class-initialization-triggers.md`](../classes-and-initialization/01d-class-initialization-triggers.md).

**Pitfall:** `catch (Exception e)` in a request-handling boundary, believed to be a safety net for "anything that goes wrong." It is not a net for `Error` at all — `Error` does not extend `Exception`, so a `catch (Exception e)` block never intercepts `OutOfMemoryError` or `StackOverflowError`, both of which will still propagate past it and crash the thread (or, for `OutOfMemoryError` on certain allocation paths, potentially the JVM). Believing `Exception` is a superset of every throwable is the exact misreading of the hierarchy this file's first concept exists to correct. The rare, narrow, and controversial exception is `catch (Throwable t)` at the very top of a request-handling thread pool, purely to log and reject the request before the thread pool loses a worker — even there, the block does not attempt recovery, only observation, because the underlying substrate problem is unrepaired by any code in the catch block.

**Interview:** "Why don't you catch `OutOfMemoryError`?" Because the JVM throwing it has already told you the code inside your `catch` block might not be able to run either — allocating a `String` for a log message, or even unwinding the stack for the catch block itself, can compete for the same exhausted heap. Catching it does not fix the shortage; it just delays the crash to a worse, harder-to-diagnose moment.

> **Definition.** `Error` and its subclasses signal a failure of the JVM's own execution guarantees — exhausted memory, exhausted native stack, or a broken class-loading contract — rather than a failure of application logic, which is why the family is unchecked and, with the narrow exception of `AssertionError`, is never a `catch` target.

---

## 4. The ten common unchecked exceptions, and what each actually means (1.20.5)

The mental model: each of these ten is a compiler-and-runtime-verified precondition failure, and the ten map cleanly onto ten different *kinds* of precondition — a null reference, a bad argument, a bad object state, a bad cast, a bad index, a bad arithmetic operation, an unsupported operation, a concurrent mutation, a bad string format, and a bad array covariance. Confusing which precondition a given exception encodes is a fast way to write a `catch` block that hides the wrong bug.

| Exception | What it actually means | QuizStakes trigger |
|---|---|---|
| `NullPointerException` | A reference expected to be non-null was null at the point of dereference | Calling `.type()` on an absent `Restriction` fetched from a cache miss |
| `IllegalArgumentException` | The caller passed an argument that is syntactically acceptable to the type system but semantically invalid | A coupon code like `SUMMR25` failing a checksum in `BonusService.grant` |
| `IllegalStateException` | The *object* is not in a state that permits this operation right now — the argument may be fine | Staking against an account still at `AO-400 SUBMITTED`, not yet `AA-801 ACTIVATED` |
| `ClassCastException` | A reference was cast to a type it is not actually an instance of at runtime | Casting a `DocumentVerdict` retrieved from a generic `Verdict` list to `ScreeningVerdict` |
| `IndexOutOfBoundsException` | A numeric index fell outside a collection's or array's valid range | Reading `movements.get(movements.size())` off a `Reservation`'s movement history |
| `ArithmeticException` | An arithmetic operation is mathematically undefined for its operands, most commonly integer division by zero | Computing a 10% bonus split in integer minor units with a zero divisor from a misconfigured tier |
| `UnsupportedOperationException` | The operation exists on the type but this particular instance refuses to support it | Calling `.add(restriction)` on the immutable `List<Restriction>` returned by `ClientRestrictions.active()` |
| `ConcurrentModificationException` | A collection's structure changed while an iterator over it was in progress | Removing a `Restriction` from a `List<Restriction>` inside its own enhanced-`for` loop while computing a gate |
| `NumberFormatException` | A string could not be parsed as the numeric type requested | Parsing a minor-unit amount off a malformed PSP callback field |
| `ArrayStoreException` | An array's runtime element type rejected a store that its static type permitted | Storing a `RestrictedActionException` into a `LedgerImbalanceException[]` through a `RuntimeException[]`-typed reference |

Measured proof of two of the sharper ones, on JDK 21.0.7. `NumberFormatException` genuinely extends `IllegalArgumentException` — `Integer.parseInt("12.50")` inside a `catch (IllegalArgumentException e)` block reports `e.getClass().getName()` as `java.lang.NumberFormatException`, confirming a narrower catch clause for `IllegalArgumentException` silently also catches every `NumberFormatException`. And `ArrayStoreException` is real covariant-array enforcement, not a cast check at compile time: assigning `new LedgerImbalanceException[2]` to a `RuntimeException[]`-typed variable compiles cleanly (arrays are covariant), but writing a `RestrictedActionException` into element `0` throws `ArrayStoreException` at the store, because the array's *runtime* component type is still `LedgerImbalanceException`.

`ClientRestrictions.active()` returning an immutable view is the concrete `UnsupportedOperationException` case, and it is worth seeing in full because the failure surfaces one call away from where the mistake was made:

```java
public class ClientRestrictions {
    private final List<Restriction> restrictions = new ArrayList<>();

    public List<Restriction> active() {
        return restrictions.stream()
            .filter(r -> r.status() == RestrictionStatus.ACTIVE)
            .toList();
    }
}
```

`Stream.toList()` (Java 16+) returns an unmodifiable list, same contract as the static factory `List.of(String[] elements)` (the varargs form, erased to an array). A caller who writes `clientRestrictions.active().add(restriction)`, expecting to accumulate a new restriction onto the view, gets `UnsupportedOperationException` with no message — measured: `java.lang.UnsupportedOperationException` with a null message, thrown from `java.util.ImmutableCollections$AbstractImmutableList.add`. The gotcha compounds because the failure is at the call site consuming the list, not inside `ClientRestrictions`, so the stack trace points at the wrong file for the fix.

`ConcurrentModificationException` from mutating a restriction list while iterating it to compute a stake gate, measured directly:

```java
List<String> restrictionTypes = new ArrayList<>(
    List.of("STAKE_BLOCKED", "ALL_BLOCKED", "SELF_EXCLUDED"));
for (String type : restrictionTypes) {
    if (type.equals("STAKE_BLOCKED")) {
        restrictionTypes.remove(type);
    }
}
```

Running this on JDK 21.0.7 throws `java.util.ConcurrentModificationException` from the iterator's next `hasNext()`/`next()` call, because `ArrayList`'s iterator tracks a `modCount` snapshot taken at iterator creation and fails fast the moment it detects the backing list changed underneath it. **Pitfall:** removing the *first* of a two-element list sometimes does not throw, because the iterator's post-removal `hasNext()` check can coincidentally see there is nothing left to iterate and never calls the failing `next()` — which is why "it worked in my quick test" is not evidence of correctness here; the fix is `Iterator.remove()` or a `CopyOnWriteArrayList` when concurrent mutation is a legitimate requirement, not a bug.

**Pitfall:** `catch (NullPointerException e)` used as normal control flow to detect "this field was not set" instead of checking for null explicitly. It works, but it also silently swallows every *other* `NullPointerException` in the same try block — a genuine bug two lines away gets treated as "field not set" and the actual defect is never seen. Since Java 15, helpful NPE messages (JEP 358, on by default) name the exact null expression — `Cannot invoke "String.length()" because "<local1>" is null`, measured on JDK 21.0.7 — which is a debugging aid, not a reason to rely on the exception type as a signal; [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md) covers the full catch-discipline argument and the helpful-message mechanics.

**Interview:** "Why is `NumberFormatException` catchable by `catch (IllegalArgumentException e)`?" Because it extends `IllegalArgumentException` directly in the JDK source — a malformed number string *is* a special case of an invalid argument, and the JDK models the inheritance rather than making it a sibling.

> **Definition.** These ten unchecked exceptions each encode a distinct kind of precondition failure — null dereference, bad argument, bad state, bad cast, bad index, bad arithmetic, unsupported operation, concurrent structural change, bad number format, or bad array store — and none of them require a `throws` clause, because the JDK's design stance is that programmer-error signals should not force every caller up the stack to acknowledge them syntactically.

---

## 5. The six common checked exceptions (1.20.6)

The mental model: each of these six names a specific external system QuizStakes cannot fully control — a filesystem, a database, a thread scheduler, a classloader, the object-cloning machinery, or a downstream vendor with a deadline. The checked designation is the language forcing an explicit decision at every call site that touches one of those externals, rather than letting the failure surface unannounced three layers up.

| Exception | External system it signals | QuizStakes trigger |
|---|---|---|
| `IOException` | Filesystem or stream I/O failure | Reading or writing the payment-run file that feeds `PaymentRun`'s batched bank withdrawals |
| `SQLException` | JDBC / relational database failure | `FundsLedger.append` failing a ledger write — the propagation example in concept 2 |
| `InterruptedException` | A thread was interrupted while blocked (sleep, wait, join, blocking queue take) | A `PaymentRun` worker thread blocked pulling the next batched withdrawal, interrupted during shutdown |
| `ClassNotFoundException` | A class named by string (`Class.forName`) could not be located by the classloader | Loading a plugin-style `Verdict` decoder registered by fully-qualified name from configuration |
| `CloneNotSupportedException` | `Object.clone()` called on a class that does not implement `Cloneable` | A `LedgerEntry` value type that intentionally does not implement `Cloneable`, so a stray `clone()` call fails loudly rather than performing a shallow copy nobody asked for |
| `TimeoutException` | An operation exceeded a caller-imposed deadline | The identity vendor call in `DocumentVerification`, p99 38s against a 30s watchlist timeout |

`InterruptedException` deserves one extra sentence here even though its full handling policy belongs elsewhere: it is checked specifically because ignoring an interrupt is a correctness bug, not a convenience choice, and the language forces every blocking call's caller to confront that. The batched `PaymentRun` worker blocking on `BlockingQueue.take()` while waiting for the next approved bank withdrawal must decide, syntactically, what to do when interrupted — swallow it (wrong), propagate it (usually right), or restore the interrupt flag and continue (right, when the method cannot itself declare `throws InterruptedException`). The full policy — why swallowing is a production hazard, `Thread.currentThread().interrupt()`, and how it interacts with `Thread.UncaughtExceptionHandler` and shutdown hooks — is [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md)'s territory; this file only places `InterruptedException` in the checked family and says why.

`TimeoutException` is the sharpest of the six for QuizStakes specifically, because the numbers make the checked-ness matter rather than being an abstraction: the identity vendor's p50 latency is 900ms, but its p99 is 38 seconds, against a 30-second watchlist timeout `DocumentVerification` imposes. A caller of the vendor client cannot compile code that ignores `TimeoutException` — it must decide, at the call site, whether a timed-out identity check means "retry", "fall to `AA-650 DOCUMENTS_REFERRED` for human review", or "fail the whole application" — and the compiler is what forces that decision to be made explicitly rather than discovered in production the first time the p99 tail is hit.

```java
public class DocumentVerification {
    private static final Duration WATCHLIST_TIMEOUT = Duration.ofSeconds(30);

    private final ScreeningService screeningService;

    public DocumentVerification(ScreeningService screeningService) {
        this.screeningService = screeningService;
    }

    public ScreeningVerdict verify(ApplicationId applicationId) throws TimeoutException, InterruptedException {
        Future<ScreeningVerdict> future = screeningService.submit(applicationId);
        try {
            return future.get(WATCHLIST_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
        } catch (ExecutionException e) {
            throw new IllegalStateException("watchlist check failed for " + applicationId, e);
        }
    }
}
```

Both `TimeoutException` and `InterruptedException` are declared, because `Future.get(long, TimeUnit)` can throw either, and neither can be caught here without deciding what a caller should do about it — swallowing `TimeoutException` silently and returning `null` would mean an application sails past a check that should have routed to `AA-650 DOCUMENTS_REFERRED`.

**Pitfall:** treating `ClassNotFoundException` as dead code because "the class is always on the classpath." It fires the moment a class is looked up reflectively by string — `Class.forName("com.quizstakes.verdict.ScreeningVerdictDecoderV2")` — and a typo, a missing JAR in one deployment environment, or a class deliberately excluded from a slimmed-down artifact all produce it identically at runtime, with nothing at compile time to catch the mistake, because the compiler cannot verify a string.

**Interview:** "Name a checked exception that is not I/O-related." `CloneNotSupportedException` and `ClassNotFoundException` are the two clean answers — both signal a failure with no filesystem, network, or database involved, which is useful for correcting the common but wrong shorthand "checked exceptions are just for I/O."

> **Definition.** The six common checked exceptions each mark a boundary with an external system — filesystem, database, thread scheduler, classloader, the `Cloneable` contract, or a caller-imposed deadline — where the language forces every caller to explicitly acknowledge the possibility of failure rather than letting it surface silently.

---

## Pitfalls

### Believing checked vs unchecked is a runtime distinction

**Wrong**

```java
try {
    fundsLedger.append(entry);
} catch (RuntimeException e) {
    // "this catches everything checked exceptions don't, right?"
    log.warn("ledger append issue", e);
}
```

Written believing `RuntimeException` and "checked" are opposite runtime behaviors — that a checked exception somehow behaves differently *at the moment it is thrown* than an unchecked one. It does not compile as written above if `append` is declared `throws SQLException`, because `catch (RuntimeException e)` does not satisfy the checked exception's catch-or-declare obligation — the compiler still demands a `catch (SQLException e)` or a `throws SQLException` on the enclosing method, and no runtime behavior difference is what would fix that.

**Right**

```java
try {
    fundsLedger.append(entry);
} catch (SQLException e) {
    throw new LedgerImbalanceException("ledger append failed for " + entry.roundId());
}
```

Checked vs unchecked is entirely a compile-time classification — JLS 21 §11.1.1, checked exactly to the extent a `Throwable` is neither `Error` nor `RuntimeException`. At the moment either kind is actually thrown, the JVM's `athrow` instruction and stack unwinding behave identically; there is no runtime flag distinguishing them, no different exception-table entry shape, nothing. The only difference is what `javac` demanded before the program was allowed to compile.

**Why people believe it:** the two behave so differently in day-to-day coding — one forces a `throws` clause everywhere, one does not — that it feels like a deep runtime property. It is purely `javac` enforcement layered on top of an ordinary `Throwable` object that the runtime treats uniformly.

### Assuming `catch (Exception e)` is a safety net for everything

**Wrong**

```java
public ResponseEntity<Reservation> post(ClientId clientId, Money stake) {
    try {
        return ResponseEntity.ok(paymentService.reserveStake(clientId, stake));
    } catch (Exception e) {
        return ResponseEntity.status(500).build();
    }
}
```

Written believing this handles "anything that can go wrong" in `reserveStake`. It handles every checked and unchecked exception under `Exception` — but an `OutOfMemoryError` thrown mid-reservation, or a `StackOverflowError` from a runaway recursive gate check, sails straight past this `catch` block because `Error` does not extend `Exception`. The request thread dies with an uncaught `Error` the handler never saw.

**Right**

```java
public ResponseEntity<Reservation> post(ClientId clientId, Money stake) {
    try {
        return ResponseEntity.ok(paymentService.reserveStake(clientId, stake));
    } catch (RestrictedActionException | InsufficientFundsException e) {
        return ResponseEntity.status(422).build();
    }
    // Errors are not caught here by design — see concept 3.
}
```

Catch specific, expected, recoverable exceptions by name — the catch-clause ordering and multi-catch mechanics for doing this cleanly are [`01b-catch-multicatch-and-precise-rethrow.md`](01b-catch-multicatch-and-precise-rethrow.md)'s territory. Let unrecognized exceptions and every `Error` propagate to a top-level handler — `Thread.UncaughtExceptionHandler` or the framework's global exception handler — which is where [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md) picks up.

**Why people believe it:** `Exception` reads as the general word for "something went wrong," and most everyday failures do live under it. The five JVM-fatal `Error` types are rare enough in normal development that the gap in the mental model goes untested until a production incident exposes it.

### Declaring `throws Exception` to make a checked-exception compile error disappear

**Wrong**

```java
public void reserveStake(ClientId clientId, Money stake) throws Exception {
    fundsLedger.append(new LedgerEntry(LedgerPosition.CLIENT_CASH_RESERVED, stake, clientId));
}
```

Compiles cleanly — `throws Exception` covers `SQLException` and anything else. But now every caller of `reserveStake`, all the way up to `StakeController.post`, must catch or declare the maximally broad `Exception`, which also silently permits any *other* checked exception someone adds inside `reserveStake` later without the signature telling anyone what changed.

**Right**

```java
public void reserveStake(ClientId clientId, Money stake) throws SQLException {
    fundsLedger.append(new LedgerEntry(LedgerPosition.CLIENT_CASH_RESERVED, stake, clientId));
}
```

Or, more idiomatically for a service boundary, catch `SQLException` immediately and translate to an unchecked `LedgerImbalanceException`, removing the checked exception from the signature entirely — the approach [`02-in-practice.md`](02-in-practice.md) argues for as the default QuizStakes policy.

**Why people believe it:** it is the fastest way to silence a compile error while under deadline pressure, and it does technically satisfy catch-or-declare. The cost — losing the specific-exception information every caller needs to react correctly — is invisible until a caller actually needs to distinguish `SQLException` from some other checked exception the method later grows.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Checked/unchecked rule | JLS 21 §11.1.1: checked = everything under `Throwable` except the `Error` subtree and the `RuntimeException` subtree |
| Common wrong phrasing | "checked = `Exception`, unchecked = `RuntimeException`" — wrong because `ClassNotFoundException`, `CloneNotSupportedException` sit directly under `Exception` and are checked |
| Catch-or-declare | Applies to checked exceptions only; compiler enforced; propagates through every intermediate signature that neither catches nor declares |
| Unchecked propagation | Silent — no signature change required at any intermediate frame |
| `Error` vs `Exception` | `Error` does not extend `Exception`; `catch (Exception e)` never intercepts an `Error` |
| `Error` family | `OutOfMemoryError`, `StackOverflowError`, `NoClassDefFoundError`, `LinkageError`, `AssertionError` — first four are JVM-fatal, `AssertionError` is a deliberate signal |
| `NumberFormatException` | Extends `IllegalArgumentException`. Measured: caught by `catch (IllegalArgumentException e)` on JDK 21.0.7 |
| `ArrayStoreException` | Runtime array covariance check. Measured: compiles at the assignment, throws at the store |
| `UnsupportedOperationException` | `List.of(String[] elements)` (varargs, erased to an array) / `Stream.toList()` results throw it with a null message on any mutator |
| `ConcurrentModificationException` | `ArrayList` iterator fail-fast via `modCount`; fix is `Iterator.remove()` or a concurrent collection |
| Helpful NPE messages | On by default since Java 15 (JEP 358) — names the exact null expression. Full mechanics: [`01e-catch-discipline-and-top-level-handling.md`](01e-catch-discipline-and-top-level-handling.md) |
| Checked exceptions here | `IOException`, `SQLException`, `InterruptedException`, `ClassNotFoundException`, `CloneNotSupportedException`, `TimeoutException` |
| `InterruptedException` checked because | Ignoring an interrupt is a correctness bug; full policy in `01e-catch-discipline-and-top-level-handling.md` |
| `athrow` / runtime distinction | None — checked and unchecked throw and unwind identically at the bytecode level; the split is `javac`-only |

---

## Self-test

**Q1.** Is `RuntimeException` a checked or unchecked exception, and is it a subclass of `Exception`?

<details><summary>Answer</summary>

Unchecked, and yes, it is a subclass of `Exception` — the hierarchy is `RuntimeException extends Exception extends Throwable`. The checked/unchecked line is drawn inside the `Exception` subtree, at the `RuntimeException` boundary specifically, not at the `Exception`/`Throwable` boundary. This is why "checked extends `Exception`, unchecked extends `RuntimeException`" is a sloppy half-truth: it is technically consistent for most exceptions but obscures that `RuntimeException` itself is a kind of `Exception`, and that direct subclasses of `Exception` that are not `RuntimeException` subclasses — `ClassNotFoundException`, `CloneNotSupportedException` — are checked despite sitting at the same tree depth as `RuntimeException`.

</details>

**Q2.** `FundsLedger.append` throws a checked `SQLException`. `PaymentService.reserveStake` calls it without a try-catch. What must be true of `reserveStake`'s signature, and what happens if that condition is not met?

<details><summary>Answer</summary>

`reserveStake` must itself declare `throws SQLException` (or a supertype of it). If it does not, the code fails to compile with an error in the shape measured on JDK 21.0.7: `unreported exception SQLException; must be caught or declared to be thrown`, pointing at the call to `append()`. This is catch-or-declare in its plainest form — the obligation does not stop at the method that directly throws the exception, it climbs the call chain until some frame either catches it in a try-catch or admits it in its own `throws` clause, and every frame in between must add the declaration even though none of them does the actual JDBC work.

</details>

**Q3.** `RestrictedActionException` is thrown from deep inside `PaymentService.reserveStake` and propagates all the way to `StakeController.post` uncaught. What, if anything, needs to change in the signatures of `reserveStake` and `post` for this to compile?

<details><summary>Answer</summary>

Nothing. `RestrictedActionException` extends `RuntimeException` directly, which makes it unchecked, and unchecked exceptions carry no catch-or-declare obligation at all. It can propagate through any number of stack frames — `reserveStake`, `post`, and beyond — without a single one of their signatures mentioning it. This is the direct contrast with `SQLException` in Q2: identical distance traveled up the call stack, opposite compiler treatment, purely because one sits under `RuntimeException` and the other does not.

</details>

**Q4.** Why is `NumberFormatException` catchable by `catch (IllegalArgumentException e)`?

<details><summary>Answer</summary>

Because `NumberFormatException` extends `IllegalArgumentException` directly in the JDK source — a malformed numeric string is modeled as a special case of "the caller passed an invalid argument," not as a sibling exception. Measured on JDK 21.0.7: calling `Integer.parseInt("12.50")` inside a `catch (IllegalArgumentException e)` block reports the caught object's actual class as `java.lang.NumberFormatException`. Practically, this means a broad `catch (IllegalArgumentException e)` around a block that both validates arguments and parses numbers will catch both failure modes identically, which is convenient when the response is the same either way and a trap when it needs to differ — the exception's message is then the only way to distinguish them.

</details>

**Q5.** Why do you not write `catch (OutOfMemoryError e)` and attempt to free memory and continue?

<details><summary>Answer</summary>

Because the JVM throwing `OutOfMemoryError` has already told you that its ability to satisfy an allocation is compromised, and the code inside your catch block — building a log message, allocating a cleanup data structure, even unwinding the stack to reach the catch block itself — competes for the same exhausted heap. `OutOfMemoryError` is unchecked and sits under `Error`, not `Exception`, specifically because the language's design stance is that JVM-substrate failures are not things ordinary application code can reliably reason its way out of. The QuizStakes-shaped version of this: loading all ~1.78 billion rows of the 90-day ledger hot window (19.8M entries/day) into one `List<LedgerEntry>` is the kind of access pattern that produces this error, and the fix is never "catch it and retry with less" — it is redesigning the access as a paginated or streaming query so the error condition cannot arise.

</details>

**Q6.** A method calls `Future.get(30, TimeUnit.SECONDS)` against the identity vendor client. Name the two checked exceptions it must catch or declare, and explain in one sentence each why both are checked rather than unchecked.

<details><summary>Answer</summary>

`TimeoutException` and `InterruptedException`. `TimeoutException` is checked because a caller-imposed deadline being exceeded is a condition the calling code specifically needs to decide how to handle — retry, route to human review, or fail — and the language forces that decision to be explicit rather than letting a slow p99 (38 seconds, against QuizStakes' identity vendor, versus a 30-second watchlist timeout) surface as an unhandled failure discovered only in production. `InterruptedException` is checked because silently ignoring a thread interrupt is a correctness bug — it breaks cooperative cancellation and graceful shutdown — and the language wants every blocking call's caller to confront that possibility rather than let it be swallowed by omission.

</details>

**Q7.** Someone writes `Restriction[] restrictions = new LedgerImbalanceException[3]` accessed through a `RuntimeException[]`-typed variable, then stores a `RestrictedActionException` into it. Does this fail at compile time or runtime, and what is the exception?

<details><summary>Answer</summary>

Compiles cleanly, fails at runtime with `ArrayStoreException`. Java arrays are covariant — a `LedgerImbalanceException[]` can be assigned to a `RuntimeException[]`-typed reference because `LedgerImbalanceException` is a `RuntimeException` — but the array object itself remembers its actual runtime component type. Measured on JDK 21.0.7: assigning the array to the broader-typed variable is accepted by `javac`, and the store of a `RestrictedActionException` (a `RuntimeException`, and therefore assignable to the variable's *static* element type) throws `ArrayStoreException` at the point of the store, because the array's *runtime* component type is still `LedgerImbalanceException`, which `RestrictedActionException` is not. This is the one place in ordinary Java where a store that type-checks statically still fails at runtime because of erasure-adjacent array covariance rather than generics erasure.

</details>

**Q8.** What is the practical difference between `IllegalArgumentException` and `IllegalStateException`, and give a QuizStakes example of each.

<details><summary>Answer</summary>

`IllegalArgumentException` faults the *argument* passed to a call — the object receiving the call could be in a perfectly fine state, but what was handed to it is invalid, such as a coupon code like `SUMMR25` failing a checksum inside `BonusService.grant`. `IllegalStateException` faults the *object's current state* — the arguments might be entirely well-formed, but the object cannot honor this call right now, such as attempting to stake against an account still sitting at `AO-400 SUBMITTED` rather than having reached `AA-801 ACTIVATED`; the stake amount itself might be perfectly valid, but the account's lifecycle state rejects the call regardless. The distinction matters for retries: a caller who gets `IllegalArgumentException` should not retry with the same argument, while a caller who gets `IllegalStateException` might legitimately retry later once the object's state has changed.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.20.1–1.20.6 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** D-053
**Target version:** Java 21 LTS
**Lines:** 520
