# 03 Java Core — Assertions and guarded blocks — BASICS (§1.8, 1.8.13, 1.8.14)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [switch expressions and pattern matching](01c-switch-expressions-and-patterns.md) · Next: [try as control flow, and unreachable code](01e-try-and-unreachable-code.md)

Two statement forms that change control flow without looking like control flow. An
`assert` is a statement that usually does not exist — the bytecode is there, guarded
by a flag the JVM sets from the command line. A `synchronized` block is a region the
compiler guarantees you leave, on every path, by emitting a handler you never wrote.
Both are grounded below in JLS 21 §14 and in `javap -c` and `java` runs captured on
JDK 21.

Branching, looping, labels and abrupt completion are in
[Control flow: branches, loops and abrupt completion](01-basics.md); `switch` in all
its forms spans [The classic switch statement and fall-through](01a-switch.md),
[switch on a String, on an enum, and on null](01b-string-and-enum-switch.md) and
[switch expressions and pattern matching](01c-switch-expressions-and-patterns.md);
try/catch/finally and the unreachable-statement rules are in
[try as control flow, and unreachable code](01e-try-and-unreachable-code.md).

---

## 13. `assert`, `-ea`, and why side effects are fatal (1.8.13) [TRAP]

**Concept.** An `assert` is a statement that usually does not exist. The bytecode is
emitted, but it is guarded by a synthetic `static final boolean $assertionsDisabled`
that the JVM sets from the command line at class-init time. Without `-ea` the guard
is true and the body never runs.

**Why it exists.** Java 1.4 added `assert` to give invariants a home that costs
nothing in production. The design decision — off by default — was deliberate: an
assertion is a *developer* check, and a regulated platform cannot have a
`StakeSplit` rounding invariant taking down the stake path at 1,200 reservations/sec
because a test-only assumption drifted. The consequence is the trap: an expression
that is never evaluated in production.

**How it works.** `assert cond : detail;` compiles to
`if (!$assertionsDisabled && !cond) throw new AssertionError(detail);`. Enabling is
per-classloader and per-package: `-ea` for everything, or `-ea:` followed by a package
name and the JVM's package-tree suffix (three dot characters) to cover that tree,
`-da` to disable, `-esa` for system classes. `AssertionError` extends
`Error`, so it is not caught by `catch (Exception e)` — which is what you want.

Observed on JDK 21 with a condition that increments a counter: `java As` prints
`calls=0`; `java -ea As` prints `calls=1`. Same class file, both times.

```java
record StakeSplit(Money bonusPortion, Money cashPortion) {}

final class FundsLedger {

    /** Draws proportionally from bonus before cash. The two portions must sum to the stake exactly. */
    static StakeSplit split(Money stake, Money bonusAvailable) {
        java.math.BigDecimal fromBonus = bonusAvailable.amount().min(stake.amount());
        java.math.BigDecimal fromCash = stake.amount().subtract(fromBonus);
        StakeSplit s = new StakeSplit(
                new Money(fromBonus, stake.currency()),
                new Money(fromCash, stake.currency()));

        // Correct: pure predicate, no state touched.
        assert s.bonusPortion().amount().add(s.cashPortion().amount())
                .compareTo(stake.amount()) == 0
                : "StakeSplit invariant broken: " + s + " != " + stake;
        return s;
    }

    private static int auditedSplits = 0;

    /** WRONG shape, shown to be recognised and deleted, never shipped. */
    static StakeSplit splitWithSideEffect(Money stake, Money bonusAvailable) {
        StakeSplit s = split(stake, bonusAvailable);
        // auditedSplits is incremented ONLY when -ea is on. Production count stays 0.
        assert recordAudit(s) : "audit failed";
        return s;
    }

    private static boolean recordAudit(StakeSplit s) {
        auditedSplits++;
        return true;
    }

    public static void main(String[] args) {
        Money stake = new Money(new java.math.BigDecimal("4.20"), java.util.Currency.getInstance("GBP"));
        Money bonus = new Money(new java.math.BigDecimal("1.50"), java.util.Currency.getInstance("GBP"));
        StakeSplit s = split(stake, bonus);
        System.out.println(s.bonusPortion().amount() + " + " + s.cashPortion().amount());  // 1.50 + 2.70
        splitWithSideEffect(stake, bonus);
        System.out.println("auditedSplits=" + auditedSplits);   // 0 without -ea, 1 with -ea
    }
}
```

**Pitfall:** putting work inside an `assert`. Symptom: a counter, a log line, a cache
warm-up or a lazy initialisation that is present in every local run and every CI run
(both with `-ea`) and absent in production — so the bug only ever appears in prod and
never reproduces. Fix: an assert's expression must be a pure predicate. If the check
must run in production, it is not an assertion — it is an `if` that throws
`LedgerImbalanceException`, and it belongs in the code path.

**Tradeoff:** assertions cost one static boolean read on the disabled path, which the
JIT folds away entirely once the guard is a constant — genuinely free. The cost is
that they are documentation, not enforcement. The escape hatch for an invariant that
must hold in production (the ledger balancing across ~19.8M entries/day) is an
explicit check plus a domain exception, reserving `assert` for assumptions whose
violation means the code is wrong rather than the data.

**Interview:** "Why are Java assertions disabled by default?" — Answer: so that
developer-time invariant checks cost nothing in production; the corollary is that any
side effect inside an `assert` silently disappears in production, so assertion
expressions must be pure.

> `assert` is a conditionally-compiled purity check enabled per-package with `-ea`
> and throwing `AssertionError`; its expression must have no side effects
> (JLS 21 §14.10).

---

## 14. `synchronized` blocks are control flow (1.8.14)

**Mechanism.** A `synchronized` statement is not a call — it is a structured region
with `monitorenter` at the top and `monitorexit` on *every* exit path, normal or
abrupt. `javac` guarantees the pairing by emitting a `catch any` handler around the
body whose only job is to release the monitor and rethrow. Captured on JDK 21:

```
void credit(long);
     1: getfield      #7    // Field lock:Ljava/lang/Object;
     4: dup
     5: astore_3            // stash the monitor object
     6: monitorenter
     7: aload_0
     9: getfield      #13   // Field available:J
    12: lload_1
    13: ladd
    14: putfield      #13
    17: aload_3
    18: monitorexit         // normal path
    19: goto          29
    22: astore        4     // abrupt path: any Throwable
    24: aload_3
    25: monitorexit
    26: aload         4
    28: athrow              // rethrow after releasing
    29: return
  Exception table:
     from    to  target type
         7    19    22   any
        22    26    22   any
```

That is why `synchronized` belongs in a control-flow chapter: it changes what
happens on a `throw` and on a `return` from inside the block, and there is no syntax
for entering without leaving.

```java
final class PositionStore {
    private final Object lock = new Object();
    private long clientCashAvailableMinor;
    private long clientCashReservedMinor;

    /** Reserve for a stake. Atomic against concurrent settles on the same Position. */
    boolean reserve(long minorUnits) {
        synchronized (lock) {
            if (clientCashAvailableMinor < minorUnits) {
                return false;                        // monitorexit still runs
            }
            clientCashAvailableMinor -= minorUnits;
            clientCashReservedMinor += minorUnits;
            return true;
        }
    }
}
```

**Pitfall:** believing `synchronized` only matters for mutual exclusion. It also
publishes: `monitorexit` flushes the writes made inside the block so that a thread
which later acquires the *same* monitor sees them. Symptom: a `Position` field read
without holding the lock returns a stale value even though every *write* was
synchronized. Fix: read under the same monitor, or make the field `volatile`. The
happens-before edges, the same-monitor requirement, and why a different lock object
buys nothing are in **05 Concurrency**.

> A `synchronized` statement is a monitor-scoped region whose exit is guaranteed on
> every path by a compiler-emitted `catch any` handler (JLS 21 §14.19).

---

## Pitfalls

### "Assertions run in production, so I can put bookkeeping in them"

**Wrong**

```java
private static int auditedSplits = 0;
static StakeSplit split(Money stake, Money bonus) {
    StakeSplit s = compute(stake, bonus);
    assert recordAudit(s);      // recordAudit increments auditedSplits
    return s;
}
// Local and CI (both -ea): auditedSplits climbs. Production (no -ea): stays 0 forever.
```

**Right**

```java
private static final java.util.concurrent.atomic.AtomicLong AUDITED = new java.util.concurrent.atomic.AtomicLong();
static StakeSplit split(Money stake, Money bonus) {
    StakeSplit s = compute(stake, bonus);
    AUDITED.incrementAndGet();                    // unconditional: this is real work
    assert s.bonusPortion().amount().add(s.cashPortion().amount())
            .compareTo(stake.amount()) == 0 : "StakeSplit invariant broken";
    return s;
}
```

**Why people believe it:** the code is present in the class file and runs in every
environment a developer ever looks at. `-ea` is set by IDE run configurations and by
Surefire's defaults, so the disabled path is the one nobody observes.

### "`catch (Exception e)` around the reservation path will catch a failed assertion"

**Wrong**

```java
/** The stake path's outermost handler: 1,200 reservations/sec at peak, nothing may escape. */
static boolean reserveSafely(PositionStore store, Money stake) {
    try {
        return store.reserveChecked(stake);   // contains: assert stake.amount().signum() > 0
    } catch (Exception e) {                   // believed to be "everything"
        return false;
    }
}
// Under -ea, a broken invariant throws AssertionError, which extends Error, not
// Exception. It sails past this handler and kills the request thread.
```

**Right**

```java
static boolean reserveSafely(PositionStore store, Money stake) {
    if (stake.amount().signum() <= 0) {
        // A condition that must hold in production is an if, not an assert.
        throw new IllegalArgumentException("stake must be positive: " + stake);
    }
    try {
        return store.reserveChecked(stake);
    } catch (RuntimeException e) {            // name what you actually intend to absorb
        return false;
    }
}
// AssertionError still propagates, deliberately: it means the code is wrong, and a
// request handler is not the place to decide that is recoverable.
```

**Why people believe it:** `catch (Exception e)` is taught as the broad net, and
"assertion failure" sounds like an exceptional condition. The hierarchy says
otherwise: `AssertionError` extends `Error`, and `Error` is the branch reserved for
conditions the application is not expected to handle. That is deliberate — an
assertion failure means the program's own assumptions about itself are wrong, so it
should tear through ordinary error handling rather than be absorbed and retried.
The corollary is that `catch (Throwable t)` in a request handler is worse, not better:
it converts a code-is-wrong signal into a silently degraded response.

### "A `return` from inside a `synchronized` block skips `monitorexit`"

**Wrong**

```java
/** Written by an author who did not trust the block, "just in case the return escapes". */
boolean reserve(long minorUnits) {
    lock.lock();                                   // hand-rolled, because synchronized "leaks"
    if (clientCashAvailableMinor < minorUnits) {
        return false;                              // lock is never released on this path
    }
    clientCashAvailableMinor -= minorUnits;
    clientCashReservedMinor += minorUnits;
    lock.unlock();
    return true;
}
// The early return leaks the lock permanently. The next reserve() on this Position
// blocks forever, and at 1,200 reservations/sec the thread pool is gone in seconds.
```

**Right**

```java
boolean reserve(long minorUnits) {
    synchronized (lock) {
        if (clientCashAvailableMinor < minorUnits) {
            return false;                          // monitorexit runs before the method returns
        }
        clientCashAvailableMinor -= minorUnits;
        clientCashReservedMinor += minorUnits;
        return true;
    }
}
// javac emits monitorexit on the normal path and again in a `catch any` handler,
// so every return, break, continue and throw releases the monitor.
```

**Why people believe it:** a `return` does look like it leaves the method immediately,
and with an explicit `Lock` it effectively does — which is exactly why an explicit
`Lock` must be released in a `finally`. The `synchronized` statement is not in that
category: the return value is computed first, then the compiler-emitted exit code
runs, then the method returns. The captured listing shows both paths — `monitorexit`
at offset 18 on the normal route and again at 25 inside the `any` handler — with two
exception-table rows, the second covering the handler itself so that a throw *while
releasing* retries the release. There is no syntax for entering a monitor without
leaving it.

---

## Cheat sheet

| Thing | Rule |
|---|---|
| `assert cond : detail;` | compiles to `if (!$assertionsDisabled && !cond) throw new AssertionError(detail);` |
| default state | disabled; the guard is a synthetic `static final boolean` set at class init |
| enabling | `-ea` for everything, `-ea:` plus a package and the tree suffix for a subtree, `-da` off, `-esa` system classes |
| scope of enabling | per-classloader and per-package, decided on the `java` command line |
| observed proof | same class file: `java As` prints `calls=0`, `java -ea As` prints `calls=1` |
| `AssertionError` | extends `Error`, so `catch (Exception e)` does not catch it |
| assert expression | must be a pure predicate; any side effect vanishes in production |
| cost when disabled | one static boolean read, folded away by the JIT once the guard is constant |
| production invariant | not an assert — an `if` that throws a domain exception |
| `synchronized` | `monitorenter` at entry, `monitorexit` on every exit path |
| how the pairing is guaranteed | compiler-emitted `catch any` handler that releases and rethrows |
| exception table shape | one row over the body, one over the handler itself |
| `return` from inside | value computed, then `monitorexit`, then the method returns |
| `synchronized` also publishes | `monitorexit` makes prior writes visible to the next acquirer of the **same** monitor |
| explicit `Lock` contrast | must be released in a `finally`; nothing emits the exit for you |

---

## Self-test

**Q1.** Why is `assert recordAudit(s);` a defect even though `recordAudit` returns `true`?

<details><summary>Answer</summary>

Because the expression only runs when assertions are enabled. `assert cond : msg;`
compiles to `if (!$assertionsDisabled && !cond) throw new AssertionError(msg);`, and
`$assertionsDisabled` is set from the command line at class init. Without `-ea` the
guard short-circuits and `cond` is never evaluated. Verified: the same class printed
`calls=0` under `java` and `calls=1` under `java -ea`. Since IDE run configurations and
most test harnesses enable `-ea`, the side effect is present in every environment a
developer observes and absent in production — the worst possible failure profile.
An assertion expression must be a pure predicate; anything that must happen in
production is an unconditional statement, and an invariant that must hold in
production is an `if` that throws a domain exception such as
`LedgerImbalanceException`.

</details>

**Q2.** You return from inside a `synchronized` block. What bytecode guarantees the monitor is released, and what does the exception table look like?

<details><summary>Answer</summary>

`javac` emits `monitorenter` once, after stashing the monitor object in a local via
`dup`/`astore`, and then emits `monitorexit` on *every* exit path. The normal path is
`aload` the stashed monitor, `monitorexit`, `goto` the join — that covers a `return`
from inside the block, because the return value is computed before the exit code runs.
The abrupt path is a compiler-generated handler registered for type `any`, meaning
every `Throwable`: it stores the throwable, reloads the monitor, `monitorexit`, reloads
the throwable and `athrow`s it. In the captured JDK 21 listing the exception table has
two rows: one covering the body (`from 7 to 19 target 22 any`) and one covering the
handler itself (`from 22 to 26 target 22 any`), so a throw *while releasing* still
retries the release. This is why there is no syntax for entering a monitor without
leaving it, and why `synchronized` belongs in a control-flow chapter at all: it changes
what happens on a `throw` and on a `return` from inside the block.

</details>

**Q3.** How do you enable assertions for only one package tree, and will `catch (Exception e)` swallow an `AssertionError`?

<details><summary>Answer</summary>

Enabling is per-classloader and per-package on the `java` command line. `-ea` turns
assertions on for everything the application classloader loads. To scope it, write
`-ea:` followed by a package name and the JVM's package-tree suffix — three dot
characters — which covers that package and everything below it; naming a package with
no suffix covers exactly that package. `-da` (with the same forms) disables, so a
common shape is broad `-ea` plus a narrow `-da` for a noisy subtree. `-esa` and `-dsa`
control assertions in system classes, which are separate because they load through the
bootstrap loader. And no: `AssertionError` extends `Error`, not `Exception`, so
`catch (Exception e)` does not catch it. That is deliberate — an assertion failure means
the code's own assumptions are wrong, so it should tear through the application's
ordinary error handling rather than be absorbed by a broad `catch` in a request handler.

</details>

**Q4.** What does a disabled assertion actually cost at 1,200 stake reservations per second, and how do you decide whether a given check should be an `assert` at all?

<details><summary>Answer</summary>

Effectively nothing. The compiled shape is
`if (!$assertionsDisabled && !cond) throw new AssertionError()`, and `$assertionsDisabled` is a
`static final boolean` written once during class initialisation. Once the interpreter
has run the class initialiser the field is a stable constant, so the JIT constant-folds
the guard and eliminates the whole branch — including the evaluation of `cond`, which
is why the side effect disappears. So the runtime argument for removing assertions
from a hot path is not a real argument. The decision rule is about meaning, not cost.
An `assert` states an assumption the *code* makes about itself: that a `StakeSplit`'s
two portions sum to the stake, that a `FundsLedger` entry's sign matches its type.
If that assumption breaks, the code is wrong and no runtime handling helps. A check on
*data* — a stake that arrives non-positive, a bonus above the cap of 100, a retry count
already at 3 — is a validation, must hold in production, and therefore belongs in an
`if` that throws a domain exception. The test is simple: if you would want the check in
production, it is not an assertion.

</details>

**Q5.** Every write to a `Position`'s available balance happens inside `synchronized (lock)`, but a monitoring endpoint reads the field without the lock and sometimes reports a stale figure. Why, and what are the two fixes?

<details><summary>Answer</summary>

Because `synchronized` does two jobs and the reader opted out of both. Mutual
exclusion is the visible one; the other is publication. `monitorexit` establishes a
happens-before edge such that everything written inside the block is visible to a
thread that subsequently executes `monitorenter` on the *same* monitor. A reader that
never acquires that monitor has no such edge, so the JVM and the CPU are both entitled
to hand it a value cached from before the write — and at 3,400 settlements/sec bursting
through the same `Position` the window is not theoretical. Two fixes. Read under the
same monitor, which gives the edge and also gives you a consistent snapshot across
several fields, at the cost of contending with the write path. Or make the single field
`volatile`, which gives the visibility edge per field with no contention, but no
atomicity across fields — a monitoring endpoint reading available and reserved
separately can still see a pair that never simultaneously existed. Choosing between
them is choosing whether you need a consistent multi-field snapshot. The happens-before
rules and why a *different* lock object buys nothing are in **05 Concurrency**.

</details>

**Q6.** `synchronized` releases on every path automatically. Why does an explicit `java.util.concurrent.locks.Lock` not, and what shape does that force?

<details><summary>Answer</summary>

Because a `Lock` is an ordinary object with ordinary methods. `lock()` and `unlock()`
are `invokeinterface` calls the compiler has no special knowledge of, so nothing emits
a `catch any` handler to pair them — the pairing is entirely the author's problem.
`synchronized` is a *statement* in the grammar, which is what lets `javac` emit
`monitorexit` on the normal path and again inside a compiler-generated handler covering
the body. The shape an explicit `Lock` forces is therefore
`lock.lock(); try { postMovement(entry); } finally { lock.unlock(); }`, with the `lock()` call
*outside* the `try` — inside it, a failure to acquire would run an `unlock()` for a
monitor never held. What you buy for that ceremony is what `synchronized` cannot do:
`tryLock` with a timeout, interruptible acquisition, a lock released in a different
method than it was taken, fairness, and read/write separation. The rule of thumb is to
use `synchronized` whenever the region is lexically scoped and unconditional, because
the compiler then guarantees the exit, and reach for an explicit `Lock` only when you
need one of the capabilities that scoping forbids.

</details>

---

## Open questions

None.

---

**Leaves covered:** 1.8.13, 1.8.14 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 468
