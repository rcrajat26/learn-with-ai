# 03 Java Core — Monitors on a box, and Valhalla — INTERNALS (§3.4, 3.4.13, 3.4.14)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Wrapper memory arithmetic](03e-internals-wrapper-memory.md) · Next: [`String`: the API surface](../strings/01-basics.md)

Two concepts, and they are the same concept read in two directions. `synchronized` on a boxed value is a bug today because the wrapper caches give the box a *shared* identity you did not create. It is also a bug tomorrow because the wrappers are on a published path to having *no* identity at all. The `@jdk.internal.ValueBased` annotation on all eight wrappers and the `javac` warning that reads it are the same platform mechanism serving both readings: a live migration signal, shipped in Java 16, pointing at a language change that had not landed when Java 21 was cut.

Everything measured below was produced on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)**, `UseCompressedOops` on, `ObjectAlignmentInBytes = 8`. Library source is quoted from that JDK's `lib/src.zip`.

The second leaf is about a feature that does not exist in Java 21, so the evidence discipline is stricter, not looser. Where a claim comes from a JEP it is attributed with the JEP's number, title and status as read from `openjdk.org/jeps` on **2026-08-29**. Where a claim is an arithmetic consequence of the layout rules [`03e-internals-wrapper-memory.md`](03e-internals-wrapper-memory.md) measured, it is labelled a derivation about a hypothetical. Nothing about syntax, timing or API shape is stated as settled; all of that is in `## Open questions`.

---

## 1. Locking a box locks an object you do not own (3.4.13)

`[TRAP]` `[RESEARCH]` `[X-REF 05]` The picture: `synchronized (retryCount)`, where `retryCount` is a boxed small integer, does not create a lock. It **joins** one. The monitor you acquire belongs to `IntegerCache.cache[retryCount + 128]` — a single process-wide object that every class in the JVM reaches when it boxes the same number. You wrote what looks like a private lock and got a global one. And if the value drifts past 127, you get the opposite failure: a fresh object per acquisition, which is no lock at all.

### Why it exists

It does not "exist" as a feature. It exists as a hole, and the hole is old: every Java object carries a monitor, so `synchronized` accepts any expression of reference type, and `javac` has no way to know that the object behind the reference is one the platform is handing out from a table. Before Java 16 there was not even a warning. `java.util.concurrent.locks` and the explicit-lock-object idiom were the answer for everything else, but boxing puts an ordinary-looking `Integer` local in front of `synchronized` and the code compiles.

Two independent things are wrong with it, and they fail differently. Keep them apart, because a candidate who blends them gets a follow-up question they cannot answer.

**Today, a correctness bug.** The instance is shared, so lock scope is not what the code says it is. Two unrelated subsystems that both box the value 1 serialise against each other — you have coupled `PaymentService` to `BonusService` through the number one. Worse, the *same source line* provides genuine (if absurdly over-broad) exclusion for a value inside the cache and **no exclusion whatsoever** for a value outside it, because `Integer.valueOf` returns `new Integer(i)` on the miss path. The bug's behaviour is a function of the data.

**Tomorrow, a forward-compatibility bug.** A value class has no identity, and an object with no identity has nothing to lock. That is why the wrappers carry `@jdk.internal.ValueBased` and why `javac` warns — concept 2.

When to reach for `synchronized` on an object at all: when the object is one **you** allocated for the purpose, whose reference no other component can obtain. Every boxed value fails that test, and so does every interned `String`, every `Class` object, and every `enum` constant. The sibling that wins is a plain `new Object()`, or a `ReentrantLock`, or — most often for per-entity serialisation — no explicit lock at all, because `ConcurrentHashMap.compute` already owns a per-bin lock. The example below shows all three.

### The mechanism

`[X-REF 05]` What a monitor actually is, in one paragraph, so you can answer without leaving the page. Every Java object's header begins with a **mark word**, and the mark word is where the lock state lives. On HotSpot an uncontended `monitorenter` historically CAS'd a pointer to a stack-allocated lock record into the mark word — a *thin* lock — and inflated to a heavyweight `ObjectMonitor` (a real OS-level wait queue, with the mark word then pointing at it) only under contention. *Biased* locking, which skipped even the CAS by stamping an owning thread into the mark word, was disabled by default in Java 15 (JEP 374) and the code removed in Java 18, so on JDK 21 the progression is thin then inflated. The consequence that matters here: a monitor is **per-object state stored in that object's header**, so acquiring the monitor of an object you did not allocate mutates a header shared with every other holder of that reference, and inflating it installs an `ObjectMonitor` that outlives your critical section. That is why locking a cached box is a *design* error and not merely a slow path — you are writing into the header of a JVM-owned singleton. The memory model, `happens-before`, and the full taxonomy of locks belong to guide **05 Concurrency**; the mark word's other tenant, the identity hash, is [`../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`](../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md).

`[SOURCE]` The compiler's side. Compiling

```java
public class Warn {
    static Integer legacy() { return new Integer(3); }
    static final Integer STAKE_LOCK = 1;
    static void reserve() { synchronized (STAKE_LOCK) { } }
}
```

with `javac -Xlint:all` on JDK 21.0.7 produced exactly:

```
src/Warn.java:2: warning: [removal] Integer(int) in Integer has been deprecated and marked for removal
    static Integer legacy() { return new Integer(3); }
                                     ^
src/Warn.java:4: warning: [synchronization] attempt to synchronize on an instance of a value-based class
    static void reserve() { synchronized (STAKE_LOCK) { } }
                            ^
2 warnings
```

Three measured facts about that output. Both diagnostics fire with **no compiler flags at all** — `[removal]` and `[synchronization]` are on by default, unlike ordinary deprecation warnings, so you have almost certainly seen this warning scroll past in a build log. Both are **warnings, not errors**: the class compiled and ran. And `-Werror` promotes them, producing `error: warnings found and -Werror specified`. The lint category name is `synchronization`, which is what you would suppress and what you should not.

The warning's input is an annotation, measured:

```
Integer.class.getAnnotations() = [@jdk.internal.ValueBased()]
```

and every one of the eight wrappers carries it (see [`01-basics.md`](01-basics.md) for the family's declarations).

`[BYTECODE]` The JVM's side, which is where the "there is no runtime check" claim comes from. `javap -p -c` on the same `synchronized` block:

```
  static void reserveStake();
    Code:
       0: getstatic     #16                 // Field STAKE_LOCK:Ljava/lang/Integer;
       3: dup
       4: astore_0
       5: monitorenter
       6: aload_0
       7: monitorexit
       8: goto          16
      11: astore_1
      12: aload_0
      13: monitorexit
      14: aload_1
      15: athrow
      16: return
    Exception table:
       from    to  target type
           6     8    11   any
          11    14    11   any
```

Instruction by instruction. `getstatic` loads the reference; `dup` and `astore_0` stash a second copy in a local, because the *same* reference must be used for the matching `monitorexit` and the source expression must not be re-evaluated; `monitorenter` acquires. The body here is empty, so offset 6 is straight into the exit path. Offsets 11–15 are the compiler-generated handler: catch anything, `monitorexit`, rethrow — which is how `synchronized` releases on an exceptional exit.

The **second** exception-table row, `11 14 11 any`, is the one worth pausing on: it covers the handler itself, and its target is *itself*. That is deliberate. If the `monitorexit` at offset 13 throws — which it can, with `IllegalMonitorStateException`, if the monitor state has been corrupted — the handler re-enters at 11 and tries again. It is the JVMS-blessed idiom for "the unlock must not be skipped", and its presence is a good tell when reading unfamiliar bytecode.

Now the point. There is **no** `[synchronization]` check anywhere in that listing. No type test, no annotation read, no guard. `monitorenter` on a `java/lang/Integer` reference is an ordinary `monitorenter`, and the JVM does exactly what it was told. The entire protection is one `javac` warning that a build can ignore and one annotation that no runtime consults. On JDK 21 the platform's position is *advisory*.

`[PROVE]` The proof that the monitor is shared, and then the proof that it sometimes is not a monitor at all. Measured:

```
StakeReservationService.RETRY_LOCK == BonusGrantService.RETRY_LOCK : true
StakeReservationService.RETRY_LOCK == Integer.valueOf(1)          : true
identityHashCode(stake) = 1554874502   identityHashCode(bonus) = 1554874502
```

Two unrelated service classes, each with its own `static final Integer RETRY_LOCK = 1`, holding the *same object* — same reference, same identity hash, therefore same mark word, therefore same monitor. Neither class knows the other exists.

And the failure itself, which is the measurement this folder does not have anywhere else. Two threads, each standing in for a subsystem, both calling one method that locks on a box derived from a stripe key:

```java
public class MonitorProbe {

    static long reservationCount = 0;

    static void reserveStake(int stripeKey) {
        Integer lock = stripeKey;                 // Integer.valueOf(stripeKey)
        synchronized (lock) {
            long seen = reservationCount;
            for (int spin = 0; spin < 40; spin++) { Thread.onSpinWait(); }
            reservationCount = seen + 1;
        }
    }

    static long race(int stripeKey, int iterationsPerThread) throws Exception {
        reservationCount = 0;
        Runnable subsystem = () -> {
            for (int i = 0; i < iterationsPerThread; i++) { reserveStake(stripeKey); }
        };
        Thread stakes = new Thread(subsystem, "stake-reservations");
        Thread bonuses = new Thread(subsystem, "bonus-grants");
        stakes.start(); bonuses.start();
        stakes.join(); bonuses.join();
        return reservationCount;
    }

    public static void main(String[] args) throws Exception {
        int n = 200_000;
        int expected = 2 * n;
        for (int stripeKey : new int[] { 1, 127, 128, 500 }) {
            long got = race(stripeKey, n);
            boolean cached = Integer.valueOf(stripeKey) == Integer.valueOf(stripeKey);
            System.out.printf("stripeKey=%-4d cached=%-5b expected=%d  actual=%d  lost=%d%n",
                stripeKey, cached, expected, got, expected - got);
        }
    }
}
```

Measured output on JDK 21.0.7:

```
stripeKey=1    cached=true  expected=400000  actual=400000  lost=0
stripeKey=127  cached=true  expected=400000  actual=400000  lost=0
stripeKey=128  cached=false expected=400000  actual=300408  lost=99592
stripeKey=500  cached=false expected=400000  actual=268275  lost=131725
```

Read the four rows. For stripe keys 1 and 127 the read-modify-write is perfectly serialised — the code *works*, which is the trap, because it works for the wrong reason: both threads are queueing on a cached singleton. At 128 the cache ends, `Integer.valueOf` takes its `return new Integer(i)` branch, each acquisition takes a different monitor, and **99,592 increments are lost**. At 500, 131,725. Same source line, same threads, same iteration count. The only thing that changed is the number, and the number decided whether the lock existed. A striped-lock design keyed on a client-derived integer will pass every test written with small fixtures and lose money in production, because real stripe keys are not 1.

**Pitfall:** believing `synchronized (someBoxedInt)` gives you per-value exclusion. It gives you *process-wide* exclusion below 128 — coupling every subsystem that boxes the same number — and **no exclusion at all** at or above 128, measured at 99,592 lost updates out of 400,000. Symptom: a concurrency bug whose reproducibility depends on the *magnitude* of an id, which is the least likely hypothesis anyone forms. Fix: lock on an object you allocated (`new Object()` per stripe, or a `ReentrantLock`), or drop the explicit lock and let `ConcurrentHashMap.compute` serialise the key. The code is below.

**Insight:** the cache is what makes this dangerous rather than merely useless. Without a shared instance, `synchronized` on a box would be a uniformly broken no-op lock — bad, but bad *consistently*, and it would fail the first test anyone wrote. The cache converts it into a construct that is correct-looking on small values and silently absent on large ones, and simultaneously into an invisible cross-subsystem coupling. One optimisation, two failure modes, both of them worse than the honest bug.

One more measured wrinkle, and it points the same way. Locking on a box the JIT can prove is thread-local does not stop scalar replacement:

```java
static int stakeTotalMinorUnitsLocked(int cashMinorUnits, int bonusMinorUnits) {
    Integer cash = cashMinorUnits;            // well outside -128..127
    synchronized (cash) {
        return cash + bonusMinorUnits;
    }
}
```

5,000,000 warmed iterations with values around 4,200, allocation read from `com.sun.management.ThreadMXBean.getThreadAllocatedBytes`:

| Run | Allocated | Per iteration |
|---|---|---|
| default | **0** bytes | 0.0 |
| `-XX:-EliminateLocks` | **80,000,000** bytes | 16.0 |
| `-XX:-DoEscapeAnalysis` | **80,000,000** bytes | 16.0 |

Zero by default. **Lock elision runs first**: C2 proves the monitor is thread-local, deletes the `monitorenter`/`monitorexit` pair, and only then can escape analysis scalar-replace the box — and turning `EliminateLocks` off restores exactly 16 bytes per iteration, one `Integer`, which is an independent confirmation of the 16-byte figure from [`03e-internals-wrapper-memory.md`](03e-internals-wrapper-memory.md). The mechanics of that elimination are [`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md). The implication for this file: a lock the JIT can prove nobody else can see is *deleted outright*. The platform does not treat locking a box as something to preserve.

### Diagram

No diagram for this concept: the evidence is one bytecode listing, one `javac` transcript and a four-row measured table where the lost-update column is the whole argument, and a picture of a monitor adds nothing the table does not already say.

### A concrete example

The realistic path into this bug in QuizStakes. `PaymentService` wants per-client serialisation of stake reservations so that two concurrent `ReserveStake` calls for the same client cannot both pass the affordability check. Somebody derives a stripe from the `ClientId`, boxes it, and locks on it — a shape that looks exactly like a striped lock:

```java
import java.util.Map;
import java.util.WeakHashMap;

public final class StakeReservationGuard {

    private final Map<Integer, Long> lastReservationByStripe = new WeakHashMap<>();

    private static Integer stripeOf(String clientId) {
        return Math.floorMod(clientId.hashCode(), 512);
    }

    public boolean reserve(String clientId, long stakeMinorUnits) {
        Integer stripe = stripeOf(clientId);
        synchronized (stripe) {                                  // (1)
            Long previous = lastReservationByStripe.get(stripe);
            Integer replayed = previous == null ? null : Integer.valueOf(previous.intValue());
            if (replayed == stripe) {                             // (2)
                return false;
            }
            lastReservationByStripe.put(stripe, stakeMinorUnits); // (3)
            return true;
        }
    }

    public int lockTag(String clientId) {
        return System.identityHashCode(stripeOf(clientId));       // (4)
    }
}
```

Four identity-dependent constructs, numbered. Measured `javac -Xlint:all` output on JDK 21.0.7 for that file:

```
src/StakeReservationGuard.java:14: warning: [synchronization] attempt to synchronize on an instance of a value-based class
        synchronized (stripe) {                                  // (1)
        ^
1 warning
```

**One** warning for **four** defects. `javac` on JDK 21 finds the `synchronized`; the `==` on boxes at (2), the `WeakHashMap` keyed on boxes at (3), and the `System.identityHashCode` at (4) are all silent. Do not treat a clean-but-for-one-warning build as an audit. With 512 stripes, `Math.floorMod` returns 0–511, so roughly a quarter of clients land inside the cache and get real locking while three quarters get none — the worst possible distribution, because the bug is not reproducible per-client.

The fix, complete and compiling clean under `-Xlint:all -Werror` (measured: no diagnostics):

```java
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public final class StripedReservationGuard {

    private static final int STRIPES = 512;

    /** One real lock object per stripe, allocated once. The identity is ours, not the platform's. */
    private final Object[] stripeLocks = new Object[STRIPES];

    /** Keyed on the stripe, boxed only as a map key, never locked on. */
    private final ConcurrentMap<Integer, Long> lastReservationByStripe = new ConcurrentHashMap<>();

    public StripedReservationGuard() {
        for (int i = 0; i < STRIPES; i++) {
            stripeLocks[i] = new Object();
        }
    }

    private static int stripeOf(String clientId) {
        return Math.floorMod(clientId.hashCode(), STRIPES);
    }

    public boolean reserve(String clientId, long stakeMinorUnits) {
        int stripe = stripeOf(clientId);
        synchronized (stripeLocks[stripe]) {
            Long previous = lastReservationByStripe.get(stripe);
            if (previous != null && previous.longValue() == stakeMinorUnits) {
                return false;
            }
            lastReservationByStripe.put(stripe, stakeMinorUnits);
            return true;
        }
    }

    /** No explicit lock at all: the map's own per-bin lock serialises the key. */
    public boolean reserveLockFree(String clientId, long stakeMinorUnits) {
        int stripe = stripeOf(clientId);
        Long settled = lastReservationByStripe.compute(stripe,
            (key, current) -> current != null && current.longValue() == stakeMinorUnits
                ? current
                : Long.valueOf(stakeMinorUnits));
        return settled.longValue() == stakeMinorUnits;
    }

    public int lockTag(String clientId) {
        return stripeOf(clientId);
    }
}
```

Three things changed and each is load-bearing. `stripeOf` returns `int`, not `Integer`, so there is no box to lock on by accident. The lock is `stripeLocks[stripe]` — 512 objects the class allocated in its own constructor, whose references leave the instance never, so nothing outside can contend and elision remains legal where it is provably safe. And `previous.longValue() == stakeMinorUnits` compares a primitive to a primitive rather than two `Long` references, which for 4.20-average stakes in minor units (420) would have been outside the cache and therefore always false. `reserveLockFree` is the version to prefer at 1,200 reservations per second: `compute` holds only the bin's lock, so unrelated stripes never serialise, whereas the array-of-locks version serialises everything that hashes to the same stripe. Guide **02 Java collections** owns `ConcurrentHashMap`'s bin locking.

`String` interning has the identical trap for the identical reason — the pool is a JDK-managed identity cache, so `synchronized (someInternedName)` acquires a monitor shared with every other holder of that literal; see [`../strings/01b-the-string-pool.md`](../strings/01b-the-string-pool.md).

**Interview:** *"What is wrong with `synchronized` on an `Integer`?"* Two things. The instance is shared — measured, `Integer.valueOf(1)` from two unrelated classes is `==`, so you are locking a process-wide singleton and coupling every subsystem that boxes that number. And above 127 `Integer.valueOf` allocates, so each acquisition takes a *different* monitor and there is no mutual exclusion at all: measured, 99,592 lost increments out of 400,000 at stripe key 128, zero lost at 127. `javac -Xlint` warns because the wrappers are `@jdk.internal.ValueBased` and a future value class cannot be locked at all. Fix: lock an object you allocated, or use `ConcurrentHashMap.compute`.

### The gotcha

Suppressing the warning. Measured: `@SuppressWarnings("synchronization")` on the enclosing method makes the file compile clean under `-Xlint:all -Werror`, and changes nothing whatsoever about the bytecode or the bug. The `monitorenter` is still there, the monitor is still the cache's, the lost updates are still lost. If you find that annotation in a code review, the correct response is to look at the monitor, not at the annotation.

Three neighbours of the same mistake, one sentence each. `wait`/`notify` on a box is worse than `synchronized`, because a `notify` from any thread that happens to hold the same cached instance can wake your waiter spuriously — measured, `STAKE_LOCK.wait(10)` inside `synchronized (STAKE_LOCK)` on the shared `Integer.valueOf(1)` returns normally, so nothing stops you (and outside the block it throws `IllegalMonitorStateException: current thread is not owner`, which is a different and unrelated complaint). A boxed value as a `ReentrantLock` *map key* is fine — that is `equals`, not identity — but a boxed value as the thing you intended to be one-lock-per-entity is the same bug wearing a `Map`. And a boxed value as a `WeakHashMap` key or `WeakReference` referent leans on identity and reachability, which the cache breaks in the opposite direction; it is the third entry in `## Pitfalls`, with the measurement.

> **Definition.** `synchronized` on a boxed value acquires the monitor in the mark word of whichever object `valueOf` returned — a process-wide cached singleton for −128..127, giving over-broad cross-subsystem exclusion, and a fresh instance per call outside that range, giving none at all — which `javac` flags as `[synchronization]` because the wrappers are `@jdk.internal.ValueBased` and a value class has no identity to lock.

---

## 2. Value classes remove the identity, and the numbers collapse (3.4.14)

`[RESEARCH]` The picture: today an `Integer` is a *reference to* a 16-byte heap object whose payload is 4 bytes, and every element of a `List<Integer>` costs a 4-byte compressed reference plus that 16-byte object — measured, 20 bytes per element. A class with no identity does not need the object. The JVM is free to encode the field values *into the reference itself* — in the array slot, in the field, in the register — because there is nothing left for the pointer to distinguish. Boxing stops being a representation change and becomes, at the limit, a bookkeeping change.

### Why it exists

Every file in this folder has been documenting the cost of one 1995 decision and one 2004 decision. The 1995 decision was two disjoint worlds, primitives and objects, with no unified type. The 2004 decision was generic erasure, which meant `List<int>` could not exist. Everything since has been a workaround for the gap between them: the wrapper classes themselves; `IntegerCache` and its CDS archive, so that at least the small values are not re-allocated; escape analysis and scalar replacement, so that at least the *provably local* boxes cost nothing; `IntStream`, `LongAdder`, `OptionalInt`, `Arrays.sort(int[])` and the whole primitive-specialised half of the JDK, so that at least the hot paths can avoid boxing at the cost of a duplicated API surface. Read the folder that way and the parts stop looking like separate topics: [`01a-the-wrapper-caches.md`](01a-the-wrapper-caches.md), [`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md) and [`01h-when-boxing-is-unavoidable.md`](01h-when-boxing-is-unavoidable.md) are three mitigations of one design gap.

Project Valhalla's stated aim is to remove the *reason* the costs exist rather than to keep optimising around them. **JEP 401, "Value Objects (Preview)"** — status **Integrated**, Release **28**, owner Dan Smith, updated 2026/08/07 — states its Summary as: *"Introduce value objects, which are immutable and lack object identity. Value objects are distinguished solely by the values of their fields, and can be represented by Java Virtual Machines in ways that improve performance. This is a preview language and VM feature."* Its second Goal is explicit about the wrappers: *"Support the compatible migration of existing classes that represent immutable data to this model. Migrate suitable existing classes in the Java Platform API, such as `Integer` and `LocalDate`, to have value object instances."*

**Unverified:** JEP 401's *Release* field reads 28 and its status reads Integrated as of 2026-08-29, and secondary reporting places JDK 28 in March 2027 as a preview feature; a release date is not a JEP field and preview features can slip or change, so treat "Java 28, preview" as the current plan rather than a fact. Nothing in this file depends on it.

### The mechanism

The strongest thing that can be said about Valhalla from inside Java 21 is not about Valhalla. It is that **the migration is already in flight, and you can measure it.**

`[SOURCE]` `@jdk.internal.ValueBased` exists today on all eight wrappers — measured, `Integer.class.getAnnotations()` returns `[@jdk.internal.ValueBased()]`, and the declarations quoted in [`01-basics.md`](01-basics.md) carry it on every one. Its documented meaning is precisely the contract a value class will require of its clients: do not depend on identity, do not synchronize, treat `==` as unspecified, construct via the factory rather than the constructor. That annotation and the `[synchronization]` warning it drives arrived together in **JEP 390, "Warnings for Value-Based Classes"**, delivered in **Java 16** — whose stated goals are *"to designate the primitive wrapper classes as value-based and deprecate their constructors for removal, prompting new deprecation warnings"* and to provide *"warnings about improper attempts to synchronize on instances of any value-based classes in the Java Platform"*. So the terminal deprecation of `new Integer(int)` in Java 9 (see [`01e-valueof-and-the-deprecated-constructors.md`](01e-valueof-and-the-deprecated-constructors.md)) and the synchronization warning in Java 16 are not tidiness. They are two steps of a migration whose third step is the language change. JEP 401 says so in its own migration section: *"As an example, in Java 9 we deprecated the constructors of `Integer`, `Long`, etc., recommending the use of the corresponding factory methods `Integer.valueOf`, `Long.valueOf`, etc., instead."*

**Insight:** the deprecation and the warning are the interesting part, not the future syntax. A platform that intends to remove identity from a class cannot simply remove it — it has to spend years making every reliance on that identity produce a diagnostic first. `@jdk.internal.ValueBased` is the marker for "this class's identity is on notice", `[removal]` closes the route that hands out guaranteed-distinct instances, and `[synchronization]` closes the commonest identity dependency. Read in that order, the two warnings in this folder's `javac` transcript are a decade-long deprecation of the concept of an `Integer` having an address.

What Java 21 does **not** have, measured on 21.0.7:

```
Objects.hasIdentity ABSENT on 21.0.7+8-LTS-245
Objects.requireIdentity ABSENT on 21.0.7+8-LTS-245
java.lang.IdentityException ABSENT
```

and `javac --enable-preview --release 21` on a source file containing a `value class` declaration produced `error: class, interface, enum, or record expected`. Nothing about value classes is in preview in Java 21. There is no flag that turns it on.

JEP 401 does specify what the failure will look like once the wrappers are value classes, and quoting it is legitimate because it is the JEP's own transcript rather than an inference. The compile-time form, on a statically-typed value class:

```
| Error:
| unexpected type
| required: a type with identity
| found: java.time.LocalDate
```

and the run-time form, when the static type is `Object` and the compiler cannot tell:

```
| Exception java.lang.IdentityException: Cannot synchronize on an instance of value class java.time.LocalDate
```

That is the direct answer to why concept 1's bug is also a forward-compatibility bug: the JEP's own migration-risk list says *"If existing clients synchronize on instances of the class then after migration they will fail, either with a compile-time error or an `IdentityException` at run time."* The `[synchronization]` warning you are ignoring today is the compile error you will get later.

JEP 401 also names two API changes that turn identity into something you can test — *"Two new methods in the `java.util.Objects` class, `hasIdentity` and `requireIdentity`, allow you to distinguish between identity objects and value objects"* — and states that *"The garbage collection APIs in the `java.lang.ref` package and the `java.util.WeakHashMap` class cannot be used with value objects. Attempting to create `Reference` objects for value objects will cause an `IdentityException` to be thrown."* It adds: *"Since JDK 25, `javac` has issued identity warnings when value-based classes are used with these APIs."* That is the mechanical answer to the audit gap concept 1 measured — the three defects JDK 21's `javac` missed are diagnosed by a later compiler, not by a better lint flag on this one.

The other Valhalla JEPs, read on 2026-08-29:

| JEP | Title | Status | Release |
|---|---|---|---|
| 390 | Warnings for Value-Based Classes | Closed / Delivered | **16** |
| 401 | Value Objects (Preview) | Integrated | 28 |
| 539 | Strict Field Initialization in the JVM (Preview) | Integrated | 28 |
| 402 | Enhanced Primitive Boxing (Preview) | **Draft** | — |
| 8303099 | Null-Restricted and Nullable Types (Preview) | **Draft** | — |
| 8316779 | Null-Restricted Value Class Types (Preview) | **Draft** | — |
| 8340476 | Warnings for Identity-Sensitive Libraries | **Closed / Withdrawn** | — |

JEP 539 is JEP 401's dependency: it *"provides the mechanism to require, via bytecode verification, that value object fields be initialized during the early construction phase."* JEP 402, "Enhanced Primitive Boxing", is the one whose goals bear on generics — *"Support primitive types as type arguments, implemented via boxing at the boundaries with generic code"* — and it is a **Draft** with no release. The two null-restriction drafts matter for the arithmetic below. 8340476, which would have added the library warnings, is **withdrawn**; JEP 401's own text says the warnings landed anyway, in JDK 25 for value-based classes and JDK 28 for value classes.

`[NUM]` **What "flattened" would mean for the measured numbers — a derivation about a hypothetical, not a fact about a shipped feature.** The layout rules are the ones [`03e-internals-wrapper-memory.md`](03e-internals-wrapper-memory.md) measured, so the arithmetic is sound; what is hypothetical is the premise that flattening applies.

Start from the measured baseline, at the QuizStakes volume of 2,800,000 stake reservations per day:

| Shape | Measured bytes | Per element |
|---|---|---|
| `int[]` of 2,800,000 | 11,200,712 (10.68 MiB) | **4.000** |
| `List<Integer>` (presized `ArrayList`) of 2,800,000 | 56,000,376 (53.41 MiB) | **20.000** |

Ratio exactly **5.00×**. The 20 bytes decompose as a 4-byte compressed reference in the backing `Object[]` plus a 16-byte `Integer` (12-byte header, 4-byte `int`, already 8-aligned).

Now the naive derivation: remove the identity, and the header and the pointer both become unnecessary, so an element costs its payload — 4 bytes — and 2,800,000 × 4 = 11,200,000, i.e. the `int[]` figure, ratio 1×. **That derivation is wrong, and the JEPs say why.** A reference can still be `null`, and a flattened reference has to encode that somewhere. JEP 401 is explicit, in the passage where it flattens an `Integer` array: *"Each `int` value takes up 32 bits, and each null flag requires at least one additional bit. Due to hardware constraints, a JVM will probably encode each flattened `Integer` reference as a 64-bit word. An `Integer` array thus has a larger memory footprint than a plain `int` array, but a significantly smaller total footprint than an array of pointers to `Integer` objects."* Draft JEP 8316779 puts the same figure the other way round: *"a large array of type `int` has half the memory footprint of a flattened array of type `Integer`."*

So the honest derivation, using the JEP's own 64-bit word:

- **8 bytes per element.** 2,800,000 × 8 = **22,400,000** bytes = **21.36 MiB**, plus a 16-byte array header and no `ArrayList` wrapper.
- Against the measured 56,000,376, that is a **2.50×** reduction; against the measured `int[]` 11,200,712 it is still **2.00×**, not parity.
- The measured **5.00×** ratio would become **2.00×**. It would not become 1×.

Parity needs the *second* feature. Draft JEP 8316779, "Null-Restricted Value Class Types (Preview)", exists precisely for this: *"If the Java language had a type representing references to instances of a value class but not null, then there would be no need for a null flag, and the flattened storage could have a footprint no larger than the footprint of the class's fields."* Under a null-restricted `Integer` element type, the derivation returns to **4 bytes per element**, **11,200,000** bytes, ratio **1×** — the `int[]` figure. That JEP is a **Draft** with no release, so the 4-byte number is contingent on a feature that is two steps out.

`Long` is where it gets more interesting, and worse. Measured today: a `Long` is 24 bytes (12-byte header, 4 bytes padding, 8-byte `long`) and a `List<Long>` element is 28 bytes. A flattened *nullable* `Long` needs 64 bits of payload plus a null bit, and JEP 8316779 names that as the atomicity wall: *"Even a boxed `Double` requires at least 65 bits (counting one for a null flag), which exceeds that atomic read/write capabilities of many systems."* It adds that *"the flattened data must be small enough to read and write atomically, or else the encoded data may become corrupted"* and that on common platforms that means 32 or 64 bits. So the derivation for a nullable `Long` is not "24 becomes 8" — it is **"a nullable `Long` may not be flattenable at all in a mutable field or array"**, and only a null-restricted `Long` gets to 8 bytes. The same JEP notes the escape hatch it would add: *"Allow larger value classes to further 'opt in' to non-atomic encodings in fields and arrays that don't store null."*

Three caveats on all of the above, stated plainly because the pipeline forbids overclaiming:

1. **Flattening is not guaranteed in any layout.** JEP 401's wording throughout is permissive — *"a JVM can optimize"*, *"JVM implementors have the freedom"* — and it works a case where the JVM *cannot* flatten: a mutable field whose flattened form would exceed the atomic write width falls back to a pointer, chosen *"silently, at its discretion"*. So no per-element number is a guarantee; they are what a JVM is permitted to achieve.
2. **Generics over value types is a separate and harder problem.** Nothing above gets `List<Integer>` to `int[]` cost, because the backing store is `Object[]` and erasure requires a reference type. JEP 402 lists primitive type arguments among its goals and is a Draft. **Unverified:** whether flattening reaches generic collection element storage at all, and under what conditions.
3. **The 2.00× and 1× figures are derivations, not measurements.** They follow from the measured 16-byte and 4-byte facts plus a JEP's stated encoding. No Valhalla build was run for this file.

`[NUM]` What would **not** change, which is the part that is actionable today. `equals`, `hashCode` and `compareTo` on the wrappers are already value-based by contract — `Integer.valueOf(1).equals(Integer.valueOf(1))` compares the `int`, not the address — so correct code that uses them keeps working unchanged. Every construct that breaks is a construct that leans on identity, and that yields a forward-compatibility checklist you can apply now:

| Construct on a boxed value | Java 21 today | Expected under a value class (per JEP 401) | Do this now |
|---|---|---|---|
| `boxA == boxB` | reference comparison; true only for cached values or the same instance | field comparison; true whenever the values are equal | `equals`, or unbox and compare primitives |
| `boxA.equals(boxB)` | value comparison, correct | unchanged | nothing |
| `hashCode()` / `compareTo` | value-based, correct | unchanged | nothing |
| `synchronized (box)` | `monitorenter` on a shared or fresh instance; `[synchronization]` warning | compile error, or `IdentityException` at run time | lock an object you allocated |
| `box.wait()` / `box.notify()` | works; monitor shared with the whole JVM | JEP 401: *"attempts to call these methods always fail with an `IllegalMonitorStateException`"* | a `Condition` on your own lock |
| `System.identityHashCode(box)` | address-derived, distinct per instance | JEP 401: computes *"a hash from the object's field values"* | `hashCode()`, if you wanted the value |
| `new WeakReference<>(box)` | works; cached instances never clear | JEP 401: *"Attempting to create `Reference` objects for value objects will cause an `IdentityException`"* | key the reference on an identity object |
| `WeakHashMap<Integer, V>` | works; below 128 immortal, above 128 clears unpredictably | JEP 401: *"cannot be used with value objects"* | `ConcurrentHashMap` with explicit eviction |
| `new Integer(1)` | compiles with `[removal]` | removed | `Integer.valueOf` |
| `box instanceof Integer`, `getClass()` | works | works — value objects are still objects with classes | nothing |

**Interview:** *"What is a value-based class, and why does the compiler warn?"* A value-based class is one whose specification tells you its identity is not part of its contract: instances come from factories, `==` between two of them is unspecified, and you must not synchronize on one. On JDK 21 the marker is `@jdk.internal.ValueBased` — measured, `Integer.class.getAnnotations()` returns it, and all eight wrappers carry it. `javac` warns because JEP 390, delivered in Java 16, added the annotation and the `[synchronization]` lint together as the migration path for JEP 401, "Value Objects", which removes identity from those classes; JEP 401 is Integrated for release 28 and says migrated clients that synchronize *"will fail, either with a compile-time error or an `IdentityException` at run time"*. So the warning is a pre-announced compile error, not a style note.

### Diagram

No diagram for this concept: there is none in the manifest for this file, and the two things worth seeing — the byte arithmetic and the identity-construct checklist — are already tables.

### A concrete example

Not speculative code. The audit you can run today, on the broken guard from concept 1, against the checklist above. Every finding is a defect *on JDK 21* and independently a migration blocker.

```java
import java.util.Map;
import java.util.WeakHashMap;

public final class StakeReservationGuard {

    private final Map<Integer, Long> lastReservationByStripe = new WeakHashMap<>();   // finding C

    private static Integer stripeOf(String clientId) {                                 // finding D
        return Math.floorMod(clientId.hashCode(), 512);
    }

    public boolean reserve(String clientId, long stakeMinorUnits) {
        Integer stripe = stripeOf(clientId);
        synchronized (stripe) {                                                        // finding A
            Long previous = lastReservationByStripe.get(stripe);
            Integer replayed = previous == null ? null : Integer.valueOf(previous.intValue());
            if (replayed == stripe) {                                                  // finding B
                return false;
            }
            lastReservationByStripe.put(stripe, stakeMinorUnits);
            return true;
        }
    }

    public int lockTag(String clientId) {
        return System.identityHashCode(stripeOf(clientId));                            // finding E
    }
}
```

The mechanical half of the audit — run it, it takes one command:

```
$ javac -Xlint:all -Werror -d out src/StakeReservationGuard.java
src/StakeReservationGuard.java:14: warning: [synchronization] attempt to synchronize on an instance of a value-based class
        synchronized (stripe) {                                  // (1)
        ^
error: warnings found and -Werror specified
1 error
1 warning
```

That is real measured output. It finds **finding A only**. `-Werror` is what makes it a gate rather than a line in a log nobody reads.

The five findings and their replacements:

| # | Construct | Broken today because | Replacement |
|---|---|---|---|
| A | `synchronized (stripe)` | shared monitor below 128; **no monitor** above it — measured 99,592 lost updates of 400,000 at stripe 128 | `synchronized (stripeLocks[stripe])` on a `new Object()`, or `ConcurrentHashMap.compute` |
| B | `replayed == stripe` | reference comparison; a 420-minor-unit stake is outside the cache, so always false | `previous.longValue() == stakeMinorUnits` |
| C | `WeakHashMap<Integer, Long>` | keys 120–127 are immortal cached instances and never clear; 128+ clear unpredictably — measured below | `ConcurrentHashMap` with explicit size-bounded eviction |
| D | `stripeOf` returns `Integer` | hands callers a box to lock on and a reference to compare | return `int` |
| E | `System.identityHashCode(box)` | address-derived; two calls with the same stripe above 127 return different tags | return the `int` stripe, which is the identifier you meant |

The corrected class is `StripedReservationGuard` in concept 1, and it compiles clean under `-Xlint:all -Werror` (measured, no diagnostics). Note what the audit is *not*: it is not a Valhalla-readiness exercise you do once. Findings A through E are all live bugs on JDK 21, and fixing them is worth doing on today's terms alone.

### The gotcha

Two, in opposite directions, and both are common.

Treating Valhalla as a reason to defer. Every fix on the list above is an improvement now, independent of any future release: `long` instead of `Long` removes 24 bytes per iteration of a boxed accumulator (measured in [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md)); a real lock object removes an actual lost-update bug; `equals` instead of `==` removes a bug whose trigger is the magnitude of a number. "We will get it free in a later JDK" is a plan to keep the bugs.

And the inverse: assuming value classes make boxing free everywhere, so `List<Integer>` becomes `int[]`. It does not follow. The nullable flattened encoding the JEP itself expects is 64 bits, so the derived per-element cost is 8 bytes and not 4 — twice `int[]`, not equal to it — parity needs a null-restricted type from a Draft JEP, flattening is explicitly at the JVM's discretion, and generic element storage depends on JEP 402, which is also a Draft. The safe summary: the *representation* penalty is on a credible path to shrinking substantially; the *generic collection* penalty is a separate, harder, unfinished problem.

> **Definition.** A value class, per JEP 401 ("Value Objects (Preview)", Integrated, release 28), is a class whose instances are immutable and *lack identity*, so `==` compares field values, `synchronized` is rejected at compile time or throws `IdentityException`, and the JVM may flatten or scalarize a reference to it into the referring field, array slot or frame instead of allocating a heap object — which on Java 21 is visible only as the `@jdk.internal.ValueBased` annotation and the `[synchronization]` warning that JEP 390 added in Java 16.

---

## Closing the subject

Seventeen files, and the through-line was never really the wrapper API. It was one gap: primitives and objects are separate worlds, and every crossing between them costs something specific and measurable. The BASICS tier established what the crossings are — the eight wrappers, autoboxing as a `javac` rewrite to `valueOf`, the 256-entry caches and the 127-versus-128 flip they produce, the unboxing NPE at a line containing no visible call, `equals` across types always false, the parsing traps, and the 5.00× memory ratio. The INTERNALS tier went to the source and the bytecode for each: `Integer.valueOf`'s two branches, the CDS archived subgraph, the five cache classes and `Long`'s missing tunable, `invokestatic valueOf` and `invokevirtual intValue`, scalar replacement measured at literally zero bytes when the box does not escape and 16 per iteration when it does, and the 12-byte header arithmetic that makes an `Integer` 16 bytes and a `Long` 24. This file closes it with the one place where the cache turns from an optimisation into a correctness hazard, and with the reason the whole edifice is provisional.

Once value classes land the shape of this subject changes rather than disappearing. The wrappers keep their API and their `equals`/`hashCode` semantics; they lose their addresses. `==` starts comparing values, which fixes the 127-versus-128 trap by removing the concept it depends on. `synchronized` on a box becomes a compile error rather than a warning. `IntegerCache` becomes an implementation detail with no observable consequences, since there is nothing left for two cached instances to differ in. And the memory arithmetic improves by a derived factor of 2.50× for a nullable flattened `Integer`, or to `int[]` parity if the null-restricted work lands — while `List<Integer>` remains a separate, unfinished problem. Until then the practical advice is unchanged and is what it always was: prefer the primitive, box only where the API forces it, never compare boxes with `==`, and never lock one.

Next: [`String`](../strings/01-basics.md), which is the other class whose identity the JDK manages on your behalf — and, per JEP 401, the one class on this list that is explicitly *not* becoming a value class, *"due to some dependencies on object identity in its API and implementation"*.

---

## Pitfalls

### Locking on a boxed id or counter to get per-entity serialisation

**Wrong**

```java
private static Integer stripeOf(String clientId) {
    return Math.floorMod(clientId.hashCode(), 512);
}

public boolean reserve(String clientId, long stakeMinorUnits) {
    Integer stripe = stripeOf(clientId);
    synchronized (stripe) {                       // looks like a striped lock
        long seen = reservationCount;
        reservationCount = seen + 1;
        return true;
    }
}
```

Two measured proofs that this is not a lock. Sharing: `StakeReservationService.RETRY_LOCK == BonusGrantService.RETRY_LOCK` is **true** for two unrelated classes each declaring `static final Integer RETRY_LOCK = 1`, with `identityHashCode` 1554874502 for both — one monitor, every subsystem in the JVM. Absence: two threads, 200,000 iterations each, incrementing under `synchronized (Integer.valueOf(stripeKey))`:

```
stripeKey=1    cached=true  expected=400000  actual=400000  lost=0
stripeKey=127  cached=true  expected=400000  actual=400000  lost=0
stripeKey=128  cached=false expected=400000  actual=300408  lost=99592
stripeKey=500  cached=false expected=400000  actual=268275  lost=131725
```

At 127 it works; at 128 it silently stops working, because `Integer.valueOf` takes its `return new Integer(i)` branch and each acquisition gets a private monitor. With 512 stripes, a quarter of clients are protected and three quarters are not.

**Right**

```java
private static final int STRIPES = 512;
private final Object[] stripeLocks = new Object[STRIPES];
private final ConcurrentMap<Integer, Long> lastReservationByStripe = new ConcurrentHashMap<>();

public StripedReservationGuard() {
    for (int i = 0; i < STRIPES; i++) { stripeLocks[i] = new Object(); }
}

private static int stripeOf(String clientId) {
    return Math.floorMod(clientId.hashCode(), STRIPES);
}

public boolean reserve(String clientId, long stakeMinorUnits) {
    int stripe = stripeOf(clientId);
    synchronized (stripeLocks[stripe]) {
        Long previous = lastReservationByStripe.get(stripe);
        if (previous != null && previous.longValue() == stakeMinorUnits) { return false; }
        lastReservationByStripe.put(stripe, stakeMinorUnits);
        return true;
    }
}

/** Better still at 1,200 reservations/sec: no explicit lock, only the map's own bin lock. */
public boolean reserveLockFree(String clientId, long stakeMinorUnits) {
    int stripe = stripeOf(clientId);
    Long settled = lastReservationByStripe.compute(stripe,
        (key, current) -> current != null && current.longValue() == stakeMinorUnits
            ? current
            : Long.valueOf(stakeMinorUnits));
    return settled.longValue() == stakeMinorUnits;
}
```

`stripeOf` returns `int`, so there is no box to lock on by accident; the 512 lock objects are allocated by this class and their references never leave it; and `compute` serialises only the one bin, so unrelated stripes never contend. Measured: compiles clean under `javac -Xlint:all -Werror`.

**Why people believe it:** the shape is right. Striped locking *is* the correct pattern for per-entity serialisation, and "one lock per stripe key" is the correct sentence — the error is only that a boxed `int` is not a per-stripe object. It reinforces itself because it demonstrably works in a unit test, where stripe keys are 0, 1 and 2 and every one of them is in the cache.

### Suppressing the `[synchronization]` warning

**Wrong**

```java
public final class SuppressProbe {
    static final Integer STAKE_LOCK = 1;

    @SuppressWarnings("synchronization")
    static void reserveStake() {
        synchronized (STAKE_LOCK) { }
    }
}
```

Measured: compiles clean under `javac -Xlint:all -Werror`, no diagnostics. And measured, unchanged: `STAKE_LOCK == Integer.valueOf(1)` is **true**, and the bytecode still contains

```
       0: getstatic     #16                 // Field STAKE_LOCK:Ljava/lang/Integer;
       3: dup
       4: astore_0
       5: monitorenter
```

The annotation moved the warning, not the `monitorenter`. There is no runtime check anywhere in that listing, so nothing else will ever tell you.

**Right**

```java
public final class StakeReservationCounter {
    /** A lock this class allocated, whose reference nothing else can reach. */
    private static final Object RESERVATION_LOCK = new Object();

    private static long reservationCount;

    static void reserveStake() {
        synchronized (RESERVATION_LOCK) {
            reservationCount++;
        }
    }
}
```

One line changed, and now the monitor belongs to this class. Note the second effect: under JEP 401 the suppressed version becomes a compile error or an `IdentityException` at run time — *"If existing clients synchronize on instances of the class then after migration they will fail"* — and `@SuppressWarnings` will not silence an error.

**Why people believe it:** the warning names a *language* concern ("value-based class") rather than a bug, and it fires on code that visibly works, so it reads like pedantry about a future feature. `@SuppressWarnings` is also the correct response to several other true-but-unhelpful lints, which trains the reflex. The tell that this one is different: it is on by default with no flags, which the JDK reserves for things it means.

### Using a boxed value as a `WeakHashMap` key or a `WeakReference` referent

**Wrong**

```java
Map<Integer, String> restrictionsByStripe = new WeakHashMap<>();

for (int stripe = 120; stripe < 135; stripe++) {
    restrictionsByStripe.put(stripe, "STAKE_BLOCKED");
}
```

Measured on JDK 21.0.7 — fifteen entries put, then three `System.gc()` calls with a `size()` afterwards to force `expungeStaleEntries`:

```
entries after put              : 15
entries after 3 System.gc()    : 8
surviving keys                 : [120, 121, 122, 123, 124, 125, 126, 127]
```

The boundary is the cache boundary, exactly. Keys 120–127 are `IntegerCache` instances, strongly reachable from a `static final` array for the life of the JVM, so those entries are **immortal** — a weak map that never releases them. Keys 128–134 were fresh objects, cleared as soon as the local box went out of scope, so those entries vanished on the first GC, possibly before anything read them. One map, two opposite lifetime semantics, split at 127.

**Right**

```java
/** Bounded by policy, not by reachability. Eviction is a decision, not a GC side effect. */
private final ConcurrentMap<Integer, String> restrictionsByStripe = new ConcurrentHashMap<>();

public void applyRestriction(int stripe, String restrictionType) {
    if (restrictionsByStripe.size() >= 512) {
        restrictionsByStripe.clear();          // or a real LRU / expiry policy
    }
    restrictionsByStripe.put(stripe, restrictionType);
}
```

If the entries genuinely must be weak, key them on an object whose lifetime you control — the `Reservation` aggregate, say — and store the stripe as a value. JEP 401 makes this permanent rather than merely inadvisable: *"The garbage collection APIs in the `java.lang.ref` package and the `java.util.WeakHashMap` class cannot be used with value objects. Attempting to create `Reference` objects for value objects will cause an `IdentityException` to be thrown."*

**Why people believe it:** `WeakHashMap<K, V>` is generic over `K`, so `Integer` is a legal type argument and the code compiles with no diagnostic on JDK 21 (measured: `javac -Xlint:all` said nothing about it). The documented contract is about reachability, which reads like a property of the *map*, when it is a property of the *key object* — and nothing in the API hints that the JDK is holding a permanent strong reference to 256 of your possible keys.

### Waiting for Valhalla instead of using `int` and `long` now

**Wrong**

```java
/** Deferred: value classes will make this free. */
static long sumStakeMinorUnitsBoxed(int[] stakeMinorUnits) {
    Long sum = 0L;
    for (int minorUnits : stakeMinorUnits) {
        sum += minorUnits;
    }
    return sum;
}
```

Measured over a 1,000,000-element `int[]` with `getThreadAllocatedBytes`: **24,000,000 bytes** allocated, exactly 24 per iteration, one `Long` per `+=`, against **0 bytes** for the identical primitive loop. The cache does not help — the running total leaves −128..127 on the second iteration. And the deferral is built on a misreading: JEP 402 ("Enhanced Primitive Boxing"), the JEP whose goals cover primitive type arguments, is a **Draft** with no release; JEP 401 is Integrated for 28 as a *preview* feature requiring `--enable-preview`; and the derived flattened cost of a nullable `Integer` element is 8 bytes, not 4, per JEP 401's own encoding.

**Right**

```java
static long sumStakeMinorUnitsPrimitive(int[] stakeMinorUnits) {
    long sum = 0L;
    for (int minorUnits : stakeMinorUnits) {
        sum += minorUnits;
    }
    return sum;
}
```

Zero allocation, measured, on the JDK you are already running. Where the accumulator must be shared, `LongAdder`; where the pipeline must be a stream, `Arrays.stream(int[]).asLongStream().sum()`, measured at **256 bytes total** independent of length. [`01h-when-boxing-is-unavoidable.md`](01h-when-boxing-is-unavoidable.md) has the full set of escape hatches.

**Why people believe it:** the direction of travel is real, the JEP text is genuinely encouraging, and "the platform is fixing this" is true. What does not follow is that the fix is imminent, unconditional, or complete — flattening is explicitly at the JVM's discretion, the parity number needs a Draft JEP, and generic element storage is a separate problem. Meanwhile every fix costs one keyword.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| `synchronized (box)` below 128 | `monitorenter` on the shared `IntegerCache` instance — process-wide exclusion, cross-subsystem coupling |
| `synchronized (box)` at or above 128 | `valueOf` allocates, so a fresh monitor per acquisition — **no exclusion**. Measured 99,592 lost of 400,000 |
| Proof of sharing | `STAKE_LOCK == Integer.valueOf(1)` → **true**; two unrelated classes' `RETRY_LOCK` fields → `==` true, same `identityHashCode` |
| The warning | `warning: [synchronization] attempt to synchronize on an instance of a value-based class` |
| Flags needed for it | **none** — on by default, like `[removal]` and unlike ordinary deprecation |
| `-Werror` | promotes it: `error: warnings found and -Werror specified` |
| `@SuppressWarnings("synchronization")` | measured: silences it under `-Xlint:all -Werror`, changes no bytecode and no behaviour |
| Runtime check | **none** on JDK 21. The bytecode is a plain `monitorenter`; only `javac` objects |
| `synchronized` bytecode | `getstatic` / `dup` / `astore_0` / `monitorenter`, body, `monitorexit`, then a catch-any handler that unlocks and rethrows |
| The `dup` | the same reference must reach `monitorexit`; the source expression is not re-evaluated |
| Second exception-table row | `11 14 11 any` — the handler guards **itself**, so a throwing `monitorexit` retries the unlock |
| Monitor location | the object's **mark word**; thin lock then inflated `ObjectMonitor` on JDK 21 |
| Biased locking | disabled by default in Java 15 (JEP 374), code removed in Java 18 |
| `synchronized` on a local box | measured **0** bytes/iteration; `-XX:-EliminateLocks` restores **16.0**. Lock elision runs before scalar replacement |
| `wait`/`notify` on a box | works; the monitor is shared with the whole JVM, so a foreign `notify` can wake you |
| `WeakHashMap<Integer, V>` | measured: keys 120–127 survive 3 GCs (immortal cache instances), 128–134 all cleared |
| Correct per-entity lock | `new Object()` per stripe, or `ConcurrentHashMap.compute` (bin lock only), or `ReentrantLock` |
| `String` interning | identical trap for the identical reason — the pool is the other JDK-managed identity cache |
| `@jdk.internal.ValueBased` | measured on all eight wrappers; `Integer.class.getAnnotations()` → `[@jdk.internal.ValueBased()]` |
| JEP 390 | "Warnings for Value-Based Classes" — **delivered in Java 16**; added the annotation and the `[synchronization]` lint |
| JEP 401 | "Value Objects (Preview)" — **Integrated, release 28**. Migrates `Integer`, `Long` and 28 more to value classes |
| JEP 539 | "Strict Field Initialization in the JVM (Preview)" — Integrated, 28; JEP 401's dependency |
| JEP 402 | "Enhanced Primitive Boxing (Preview)" — **Draft**. Primitive type arguments live here |
| Null-restriction drafts | 8303099 "Null-Restricted and Nullable Types", 8316779 "Null-Restricted Value Class Types" — both **Draft** |
| In Java 21 | nothing. Measured: no `Objects.hasIdentity`, no `java.lang.IdentityException`, `value class` is a syntax error |
| Failure after migration | compile error `required: a type with identity`, or `IdentityException: Cannot synchronize on an instance of value class …` |
| Measured baseline | `int[]` 2.8M = 11,200,712 B (4.000/elt); `List<Integer>` 2.8M = 56,000,376 B (20.000/elt); ratio **5.00×** |
| Derived, nullable flattened | JEP 401: 32 payload bits + ≥1 null bit → *"probably … a 64-bit word"* → **8 B/elt** = 22,400,000 B, **2.00×** `int[]` |
| Derived, null-restricted | JEP 8316779: footprint *"no larger than the footprint of the class's fields"* → **4 B/elt**, ratio **1×**. Draft JEP |
| Derived, `Long` | nullable needs 65 bits, exceeding atomic width on common hardware — may not flatten at all; null-restricted → 8 B |
| Flattening guarantee | none. JEP 401: *"a JVM can optimize"*; an over-wide mutable field falls back to a pointer *"silently, at its discretion"* |
| `List<Integer>` parity with `int[]` | not implied by any of the above — backing store is `Object[]`; depends on JEP 402, a Draft |
| Unchanged by migration | `equals`, `hashCode`, `compareTo`, `instanceof`, `getClass` — already value-based |
| Broken by migration | `==`, `synchronized`, `wait`/`notify`, `System.identityHashCode`, `WeakReference`, `WeakHashMap` |
| `String` | per JEP 401, explicitly **not** a value class, *"due to some dependencies on object identity"* |
| The audit command | `javac -Xlint:all -Werror` — measured: finds the `synchronized` case and **only** that one of five defects on JDK 21 |
| Later compilers | JEP 401: *"Since JDK 25, javac has issued identity warnings"* for `java.lang.ref` and `WeakHashMap` misuse |

---

## Self-test

**Q1.** What is wrong with `synchronized (retryCount)` where `retryCount` is an `Integer`? Give the two independent failures and the evidence for each.

<details><summary>Answer</summary>

Two failures that behave differently. First, over-broad sharing: the monitor belongs to whatever `Integer.valueOf` returned, and for −128..127 that is a process-wide `IntegerCache` entry. Measured on JDK 21.0.7, two unrelated classes each declaring `static final Integer RETRY_LOCK = 1` hold the same object — `==` is true and both report `identityHashCode` 1554874502 — so `PaymentService` and `BonusService` serialise against each other through the number one, and neither knows the other exists. Second, and sharper, no exclusion at all above the cache: `Integer.valueOf` falls through to `return new Integer(i)`, so each acquisition takes a private monitor. Measured, two threads doing 200,000 read-modify-writes each under `synchronized (Integer.valueOf(stripeKey))`: at stripe key 1 and 127, 400,000 of 400,000 increments landed; at 128, 99,592 were lost; at 500, 131,725. Same source line — the *value* decided whether the lock existed, which is why this passes unit tests with small fixtures and fails in production. The mechanism is visible in the bytecode: `getstatic`, `dup`, `astore_0`, `monitorenter` — an ordinary monitor acquisition with no runtime type check anywhere, so the JVM does exactly what it was told and only `javac` objects, with `warning: [synchronization] attempt to synchronize on an instance of a value-based class`. Third, forward compatibility: the wrappers are `@jdk.internal.ValueBased`, and under JEP 401 a value class has no identity to lock, so the same code becomes a compile error or an `IdentityException`. Fix: lock an object you allocated, or use `ConcurrentHashMap.compute` and let the bin lock do it.

</details>

**Q2.** Read the two rows of the exception table in a compiled `synchronized` block and say what each is for.

<details><summary>Answer</summary>

Measured `javap -p -c` output for `synchronized (STAKE_LOCK) { }` on JDK 21.0.7 gives `from 6 to 8 target 11 any` and `from 11 to 14 target 11 any`. The first row covers the *body*: catch anything thrown between the `monitorenter` at offset 5 and the normal `monitorexit`, jump to 11, which does `astore_1` (stash the throwable), `aload_0` (the duplicated reference from the `dup`/`astore_0` pair at the top), `monitorexit`, `aload_1`, `athrow`. That is how `synchronized` guarantees release on an exceptional exit — the language has no `finally` in the source but the compiler emits one. The second row is the interesting one: its range covers the handler itself, 11 to 14, and its target is **11** — itself. If the `monitorexit` inside the handler throws, which it can with `IllegalMonitorStateException` if the monitor state has been corrupted, control re-enters the handler and retries the unlock. It is the standard idiom for "this unlock must not be skipped", and its presence is a good tell when you are reading unfamiliar bytecode and trying to decide whether a `monitorexit` is the normal path or the handler. The other detail worth naming is the `dup`/`astore_0` at offsets 3–4: `monitorexit` must be given the *same* reference `monitorenter` received, and the source expression must not be re-evaluated, so the compiler stashes a copy in a local rather than reloading the field.

</details>

**Q3.** Does `synchronized` on a boxed local defeat scalar replacement? What does the answer tell you?

<details><summary>Answer</summary>

No. Measured on JDK 21.0.7, 5,000,000 warmed iterations of a method that does `Integer cash = cashMinorUnits; synchronized (cash) { return cash + bonusMinorUnits; }` with values around 4,200, well outside the cache: **0 bytes** allocated by default. Turning off lock elision with `-XX:-EliminateLocks` restores **80,000,000 bytes**, exactly 16.0 per iteration — one `Integer`, which independently confirms the 16-byte figure from the memory file. `-XX:-DoEscapeAnalysis` gives the same 16.0. Read the ordering: lock elision runs *first*. C2 proves the monitor is thread-local, deletes the `monitorenter`/`monitorexit` pair outright, and only then can escape analysis see a plain non-escaping allocation and scalar-replace it. What that tells you is a design signal rather than a performance fact: a lock the JIT can prove nobody else can observe is not preserved, it is deleted. The platform does not treat locking a box as an operation with meaning worth keeping. It also means you cannot infer from a zero-allocation profile that your locking is fine — the lock that got elided was the one nobody could contend, and the lock that matters in production is on a *shared* cached instance, which escapes by construction and is never elided.

</details>

**Q4.** A `WeakHashMap` is keyed on boxed stripe numbers 120 through 134. Predict what survives a GC, then justify it.

<details><summary>Answer</summary>

Keys 120–127 survive; 128–134 are gone. Measured on JDK 21.0.7 — fifteen entries put, three `System.gc()` calls, then `size()` to force `expungeStaleEntries` — the map reported 15 entries, then 8, with surviving keys `[120, 121, 122, 123, 124, 125, 126, 127]`. The boundary is the cache boundary exactly. Boxing 120–127 returns entries from `IntegerCache.cache`, which is a `static final Integer[]` reachable for the life of the JVM, so those keys can never become weakly reachable and those entries are effectively **immortal** — a weak map that never releases them, which is a slow leak if the key space is large and a correctness surprise if you were relying on eviction. Boxing 128 and up allocates a fresh `Integer` each time, so once the local box goes out of scope the only reference is the map's `WeakReference` and the entry is cleared on the next GC, possibly before anything reads it. One map, two opposite lifetime semantics, split at 127, with no diagnostic: measured, `javac -Xlint:all` says nothing about a `WeakHashMap<Integer, V>`. The fix is to bound the map by policy — a `ConcurrentHashMap` with explicit eviction — or, if weakness is genuinely required, to key on an object whose lifetime you control and store the stripe as a value. JEP 401 makes this permanent rather than merely inadvisable: it states that `java.lang.ref` and `WeakHashMap` *"cannot be used with value objects"* and that creating a `Reference` to one throws `IdentityException`, and it notes that since JDK 25 `javac` issues identity warnings for exactly this misuse.

</details>

**Q5.** What is a value-based class, why does `javac` warn about synchronizing on one, and what evidence for it exists in Java 21?

<details><summary>Answer</summary>

A value-based class is one whose specification declares that its identity is not part of its contract: instances come from factory methods rather than constructors, `==` between two instances is unspecified, and clients must not synchronize on one. All eight primitive wrappers are value-based. The Java 21 evidence is an annotation, measured: `Integer.class.getAnnotations()` returns `[@jdk.internal.ValueBased()]`, and every one of the eight class declarations in `java.lang` carries it. `javac` reads that annotation and emits `warning: [synchronization] attempt to synchronize on an instance of a value-based class` — measured to fire with no compiler flags at all, like `[removal]` and unlike ordinary deprecation warnings, and promoted by `-Werror` to `error: warnings found and -Werror specified`. The annotation and the warning arrived together in **JEP 390, "Warnings for Value-Based Classes", delivered in Java 16**, whose stated goals were to designate the wrapper classes as value-based, deprecate their constructors for removal, and warn about improper attempts to synchronize on value-based instances. The reason is **JEP 401, "Value Objects (Preview)"** — Integrated, release 28 — which removes identity from those classes; its migration-risk list says clients that synchronize *"will fail, either with a compile-time error or an `IdentityException` at run time"*. So the warning is a pre-announced compile error, and the terminal deprecation of `new Integer(int)` in Java 9 was the first step of the same migration. Nothing of Valhalla is in Java 21 itself: measured, `Objects.hasIdentity` and `Objects.requireIdentity` are absent, `java.lang.IdentityException` does not exist, and `javac --enable-preview --release 21` rejects a `value class` declaration as a syntax error.

</details>

**Q6.** "Value classes will make `List<Integer>` as cheap as `int[]`." Take that apart with numbers.

<details><summary>Answer</summary>

It is two claims and both need qualifying. Start from the measured baseline on JDK 21.0.7: an `int[]` of 2,800,000 costs 11,200,712 bytes, 4.000 per element; a presized `ArrayList<Integer>` of the same 2,800,000 costs 56,000,376 bytes, 20.000 per element — a 4-byte compressed reference plus a 16-byte `Integer` — for a ratio of exactly 5.00×. The naive derivation says removing the identity removes the header and the pointer, so an element costs its 4-byte payload and the ratio goes to 1×. That is wrong, and JEP 401 says why in the passage where it flattens an `Integer` array: *"Each `int` value takes up 32 bits, and each null flag requires at least one additional bit. Due to hardware constraints, a JVM will probably encode each flattened `Integer` reference as a 64-bit word."* Draft JEP 8316779 states it inversely: *"a large array of type `int` has half the memory footprint of a flattened array of type `Integer`."* So the honest derived figure is **8 bytes per element** — 22,400,000 bytes for 2.8M, a 2.50× reduction from the measured 56,000,376 but still 2.00× the `int[]` figure. Getting to 4 bytes needs a null-restricted element type, which is draft JEP 8316779: *"there would be no need for a null flag, and the flattened storage could have a footprint no larger than the footprint of the class's fields."* That JEP is a Draft with no release. Three further caveats: flattening is never guaranteed — JEP 401's language is *"a JVM can optimize"* and it works an example where an over-wide mutable field falls back to a pointer *"silently, at its discretion"*; `Long` is worse, because a nullable flattened `Long` needs 65 bits, which JEP 8316779 says exceeds the atomic read/write width of many systems, so it may not flatten at all; and none of it touches `List<Integer>` specifically, whose backing store is an `Object[]` under erasure. Primitive type arguments are a goal of JEP 402, "Enhanced Primitive Boxing", which is a Draft. Honest summary: the representation penalty is on a credible path to a derived 2.50× improvement; the generic-collection penalty is a separate, harder, unfinished problem.

</details>

**Q7.** You are asked to make a class Valhalla-ready. What do you actually change, and what does the compiler find for you?

<details><summary>Answer</summary>

Every change is a live bug fix on JDK 21, which is the point — there is nothing speculative to do. The checklist is derivable from what `@jdk.internal.ValueBased` already promises. Replace `==` between boxes with `equals` or a primitive comparison; replace `synchronized (box)` with a lock object you allocated; replace `wait`/`notify` on a box with a `Condition` on your own lock; replace `System.identityHashCode(box)` with the value you actually wanted; remove boxed keys from `WeakHashMap` and boxed referents from `WeakReference`; replace `new Integer(1)` with `Integer.valueOf(1)`. Untouched: `equals`, `hashCode`, `compareTo`, `instanceof`, `getClass` — all already value-based, all keep working. The compiler's contribution is smaller than people expect. Measured on JDK 21.0.7, `javac -Xlint:all -Werror` on a class containing five identity-dependent constructs — a `synchronized` on a boxed stripe, a `==` between boxes, a `WeakHashMap<Integer, Long>`, a method returning `Integer` where `int` was meant, and a `System.identityHashCode` on a box — reported exactly one diagnostic, the `[synchronization]` warning, and then `error: warnings found and -Werror specified`. One finding of five. So run `-Xlint:all -Werror` in CI because it mechanically catches the monitor case and turns it into a gate, but do not mistake a clean build for an audit; the other four need reading. JEP 401 notes that later compilers help more — *"Since JDK 25, javac has issued identity warnings when value-based classes are used with these APIs"* for the `java.lang.ref` and `WeakHashMap` cases — and the draft that would have added them separately, JEP 8340476 "Warnings for Identity-Sensitive Libraries", is Closed / Withdrawn because the work moved into JEP 401.

</details>

**Q8.** Why is `String` not on the list of classes becoming value classes, and why does that matter here?

<details><summary>Answer</summary>

Because it depends on identity internally. JEP 401 lists 30 classes now declared as value classes — in `java.lang` the eight wrappers plus `Number` and `Record`, in `java.util` the four `Optional` types, and fourteen `java.time` types — and explicitly excludes `String`: *"The `String` class, due to some dependencies on object identity in its API and implementation, is not a value class, so instances of `String` are always identity objects."* The JEP demonstrates it with `Objects.hasIdentity(s)` returning `true` for a string and `s == t` returning `false` for two equal strings built different ways. Why it matters in this file: `String` interning is the *other* JDK-managed identity cache, and `synchronized` on an interned string is the same bug as `synchronized` on a boxed integer for the same reason — the pool hands the same instance to every holder of the literal, so you acquire a monitor shared with every class in the JVM that mentions that text, and a runtime-computed equal string that was never interned gives you a private monitor and no exclusion. The difference is that the `String` case is *not* on a path to becoming a compile error, because `String` keeps its identity. So `javac` will never warn about it, the class will never gain the `[synchronization]` diagnostic, and it will stay a bug you have to catch by reading. If anything that makes it the more dangerous of the two.

</details>

---

## Open questions

- **Unverified:** JEP 401's target release. Its own header reads *Status: Integrated, Release: 28* as fetched from `openjdk.org/jeps/401` on 2026-08-29 (page Updated 2026/08/07), and secondary reporting places JDK 28 in March 2027 with the feature behind `--enable-preview`. A calendar date is not a JEP field and preview features can change or slip between integration and GA. What would settle it: the JDK 28 release schedule JEP and the eventual `java.lang.Integer` javadoc for that release. Nothing in this file depends on the date; every claim is framed as "what the JEP says" rather than "what will ship when".
- **Unverified:** the exact syntax and API shape of value classes. This file deliberately quotes only the two diagnostic transcripts and the method names JEP 401 states (`Objects.hasIdentity`, `Objects.requireIdentity`, `java.lang.IdentityException`) and does not paraphrase a `value class` declaration, because a preview feature's syntax is not settled and JEP 402's and 8316779's markers are Drafts. What would settle it: the JLS/JVMS preview specifications shipped with the release, and `javap` on a compiled value class from a real build.
- **Unverified:** whether flattening applies to generic collection element storage — the `List<Integer>` question. Erasure means the backing store is `Object[]`, and JEP 402 ("Enhanced Primitive Boxing", **Draft**) lists *"Support primitive types as type arguments, implemented via boxing at the boundaries with generic code"* as a goal without saying what the element layout becomes. Every per-element figure derived in this file is for an `Integer[]`, not for an `ArrayList<Integer>`. What would settle it: a measurement of `List<Integer>` footprint on a Valhalla build, and JEP 402 reaching Candidate with a specification. The measured 20.000 bytes per element on JDK 21 is unaffected either way.
- **Unverified:** the derived byte figures themselves, as distinct from the encodings they rest on. The 8-bytes-per-element nullable figure and the 4-bytes-per-element null-restricted figure are arithmetic over JEP 401's *"probably … a 64-bit word"* and JEP 8316779's *"no larger than the footprint of the class's fields"*, applied to the measured 2,800,000-element baseline. No Valhalla early-access build was run for this file, and JEP 401 is explicit that flattening is at the JVM's discretion. What would settle it: JOL or `getThreadAllocatedBytes` on an `Integer[]` of 2,800,000 on a JDK 28 early-access build with preview enabled, which is the same measurement `03e-internals-wrapper-memory.md` already performs on JDK 21.
- **Unverified:** the precise thin-lock and inflation mechanics quoted in the `[X-REF 05]` paragraph. That biased locking was disabled by default in Java 15 (JEP 374) and removed in Java 18, and that a monitor's state lives in the mark word, are stated from the JEP and JVMS-level model rather than from HotSpot source read for this file; the thin-to-inflated progression is a HotSpot implementation detail, not a specification. What would settle it: `synchronizer.cpp` and `markWord.hpp` in the JDK 21 HotSpot sources, plus guide **05 Concurrency**, which owns this material. Nothing measured here depends on it — the measurements are lost-update counts and allocation totals, neither of which reads the mark word.
- **Unverified:** why `javac -Xlint:all` on JDK 21.0.7 diagnoses the `synchronized` case but not the `==`, `WeakHashMap` or `identityHashCode` cases, given that all four rest on the same annotation. Measured: exactly one warning for the four-defect class. JEP 390's stated scope covers synchronization and constructor deprecation only, and the JEP that would have added the library warnings separately (8340476) is Closed / Withdrawn, with JEP 401 stating the warnings arrived in JDK 25 instead — so the *history* is established but not the design rationale for the Java 16 scope. What would settle it: JEP 390's full text on the lint-category question and the `valhalla-dev` discussion around 8340476.

---

**Leaves covered:** 3.4.13, 3.4.14 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 820
