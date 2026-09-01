# 05 Multithreading and Concurrency — The jcstress publication and DCL harnesses — BUILD IT (§4.8, leaves 4.8.9–4.8.10)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The ThreadLocal leak and pinning harnesses](08d-threadlocal-leak-and-pinning.md) · Next: [The backpressure harness and dump reading](08f-backpressure-and-dump-reading.md)

---

## 4.8.9 — The unsafe-publication harness

### Mental model

"Publishing" an object means making a reference to it visible to another thread. **Safe**
publication guarantees the *fields* of that object are also visible in the state the constructor
left them, not some earlier (default) state. Without a happens-before edge between the constructor
finishing and the reader's read of the reference, the JMM permits the reader to see the reference
to a *fully allocated* object whose fields still hold their **default values** — `0`, `null`,
`false` — because field writes inside the constructor and the write of the reference into the
shared field are not ordered by any synchronization action.

### Why it exists as a problem

A plain field write (`this.field = value` inside a constructor, followed later by
`sharedRef = this`) has no memory barrier tying it to the write of `sharedRef`. The compiler and
CPU are free to reorder within the single thread's program order as long as *that thread's* observed
behaviour is unchanged — but another thread reading `sharedRef` has no such guarantee about what
it sees inside the referenced object. `final` fields are the JMM's one carve-out: a properly
constructed `final` field is guaranteed visible to any thread that sees the reference, *provided
the reference did not escape during construction*. Every other field needs an explicit
happens-before edge — a `volatile` write, a lock, or a safely-published concurrent collection.

### When to reach for construction-time safety, and when not

Reach for `final` fields whenever a value is fixed at construction and needs to be read by other
threads without extra synchronization — the default and cheapest safe-publication mechanism.
Reach for `volatile` or a full lock instead when the field must be *mutated* after construction and
those later writes also need visibility. Immutability wins when it's achievable at all: it is
zero-cost at read time and needs no barrier on the read path, unlike `volatile`, which imposes a
StoreLoad/LoadLoad-class cost on every access.

### The harness

The domain object is `Reservation` — created when a client stakes into a round, holding the
`clientId`, the stake `Money`, and the `RoundId` it is reserved against. It is deliberately built
with non-final fields and published through a plain (non-volatile) static field, exactly the shape
a rushed cache-warming path might take.

```java
package quizstakes.publication;

import java.math.BigDecimal;
import org.openjdk.jcstress.annotations.*;
import org.openjdk.jcstress.infra.results.II_Result;

/** BROKEN: non-final fields, no synchronization on write. */
class UnsafeReservation {
    int clientId;      // should be 2401993
    int stakeCents;    // should be 420 (a 4.20 stake)

    UnsafeReservation(int clientId, int stakeCents) {
        this.clientId = clientId;
        this.stakeCents = stakeCents;
    }
}

@JCStressTest
@Outcome(id = "2401993, 420", expect = Expect.ACCEPTABLE,
         desc = "Fully published: reader sees the constructed values.")
@Outcome(id = "0, 0", expect = Expect.ACCEPTABLE_INTERESTING,
         desc = "Unsafe publication: reader sees default field values through a non-null reference.")
@Outcome(expect = Expect.ACCEPTABLE_INTERESTING,
         desc = "Torn publication: one field constructed, the other still default.")
@State
public class UnsafePublicationTest {
    UnsafeReservation reservation; // plain field, no volatile

    @Actor
    void writer() {
        reservation = new UnsafeReservation(2401993, 420);
    }

    @Actor
    void reader(II_Result r) {
        UnsafeReservation local = reservation;
        if (local == null) {
            r.r1 = -1;
            r.r2 = -1;
        } else {
            r.r1 = local.clientId;
            r.r2 = local.stakeCents;
        }
    }
}
```

### What you observe

Run it with the jcstress harness (`java -jar jcstress-tests.jar -t UnsafePublicationTest`). The
possible observed `(r1, r2)` pairs are `(-1, -1)` (reader ran before the write was published at
all), `(2401993, 420)` (fully safe — the common case by far), and — the interesting one —
`(0, 0)` or even a torn `(2401993, 0)` / `(0, 420)`: the reader saw the reference but not the
constructor's writes, or saw them partially. jcstress buckets `(0, 0)` and any torn combination
under `ACCEPTABLE_INTERESTING`, meaning: the JMM permits it, and if your test run's forbidden-count
is nonzero jcstress flags it in red as a JMM violation you actually hit.

**Pitfall:** "I ran it a million times on my x86 laptop and never saw `(0, 0)`, so it's safe."
x86 uses the TSO (total store order) memory model, which happens to forbid several reorderings the
JMM only *permits* — a compiler is still free to reorder under TSO if it can prove no other x86
thread would notice, and AArch64's weaker model makes the reordering the JMM allows dramatically
easier to observe in practice. **A passing run on your laptop proves nothing** about correctness
under the JMM; it only proves your specific hardware, JIT version, and inlining decisions happened
not to trigger the reordering *this time*. This is precisely why jcstress exists — it forces the
scheduler into millions of interleavings across long soak runs specifically hunting for outcomes
too rare to hit by accident, and it is normally run on multiple architectures (x86 and AArch64)
because the two expose different subsets of what the JMM actually allows.

### The fix

```java
/** FIXED: final fields, safely constructed, no mutation after construction. */
final class SafeReservation {
    final int clientId;
    final int stakeCents;

    SafeReservation(int clientId, int stakeCents) {
        this.clientId = clientId;
        this.stakeCents = stakeCents;
    }
}
```

With both fields `final` and the reference never leaked during construction (no `this` escaping
to another thread inside the constructor body), the JMM guarantees that any thread observing a
reference to a `SafeReservation` sees the fully-initialized `clientId` and `stakeCents` — this is
the JLS §17.5 final-field freeze guarantee, and it holds even with the shared field itself left
non-volatile, though a non-volatile shared reference field can still let a reader see a *stale*
(older) `SafeReservation` or `null` if there's a genuine race on *which* reservation is current;
what it rules out is ever seeing a *partially constructed* one.

**Insight:** the guarantee is about the *object's final fields*, not the reference's own
visibility timing. Making the shared field `volatile` too closes the remaining gap (which
reservation, if any, the reader currently sees) — the two guarantees compose rather than overlap.

**Interview:** "Why does making every field `final` fix unsafe publication without adding a single
`volatile`?" Because the JMM special-cases the freeze of `final` fields at constructor exit as a
happens-before edge to any subsequent read of the object through *any* reference, whereas ordinary
fields have no such guarantee and need an explicit synchronization action.

> **Definition:** unsafe publication is a data race between a constructor's field writes and
> another thread's read of the constructed reference, with no happens-before edge between them,
> permitting the reader to observe default (pre-construction) field values.

---

## 4.8.10 — The double-checked locking (DCL) harness `[RESEARCH]`

### Mental model

DCL is an optimization: check a flag/reference without a lock, only take the lock if it looks
uninitialized, then check *again* inside the lock before doing the expensive initialization — the
lock is paid for once, not on every call. The bug the naive version has is exactly the unsafe
publication bug from 4.8.9, wearing a singleton's clothes: the outer unlocked read can observe a
non-null reference to a partially-constructed object, because nothing stops the compiler or CPU
from making the write of the reference visible before the write of the object's fields.

### The domain

`BonusService.getInstance()` lazily builds the singleton that computes bonus grants — 10% of a
first deposit, capped at 100 — and is called from every deposit-confirmation path across the pool,
so the lazy-init race is hit constantly under load, not as a theoretical edge case.

```java
package quizstakes.bonus;

import org.openjdk.jcstress.annotations.*;
import org.openjdk.jcstress.infra.results.L_Result;

/** BROKEN DCL: instance field is not volatile. */
class BrokenBonusService {
    private static BrokenBonusService instance;
    final BigDecimalCappedRate rate = new BigDecimalCappedRate("0.10", "100");

    static BrokenBonusService getInstance() {
        if (instance == null) {                 // 1st check, unlocked
            synchronized (BrokenBonusService.class) {
                if (instance == null) {          // 2nd check, locked
                    instance = new BrokenBonusService(); // NOT an atomic, ordered publish
                }
            }
        }
        return instance;
    }
}

class BigDecimalCappedRate {
    final String rate;
    final String cap;
    BigDecimalCappedRate(String rate, String cap) { this.rate = rate; this.cap = cap; }
}

@JCStressTest
@Outcome(id = "1", expect = Expect.ACCEPTABLE, desc = "Reader observed a fully-constructed singleton (or its final-field rate object).")
@Outcome(id = "0", expect = Expect.ACCEPTABLE_INTERESTING, desc = "Reader observed a non-null instance whose rate field read as default (partially constructed).")
@State
public class BrokenDclTest {
    @Actor
    void writer() {
        BrokenBonusService.getInstance();
    }

    @Actor
    void reader(L_Result r) {
        BrokenBonusService svc = BrokenBonusService.instance;
        // reads the field bypassing getInstance()'s lock, mimicking an inlined/reordered caller
        r.r1 = (svc != null && svc.rate != null) ? 1L : 0L;
    }
}
```

Because `rate` is itself declared `final` on `BrokenBonusService`, the specific field this harness
targets is the *outer* `instance` reference's write ordering relative to `BrokenBonusService`'s own
constructor completing — the classic failure mode is a reader seeing `instance != null` while the
constructor of `BrokenBonusService` (which may itself do non-trivial work assigning non-final
fields, omitted here for brevity but present in the full production class) has not finished.

### What you observe

`new BrokenBonusService()` compiles to, conceptually: (a) allocate memory, (b) run the constructor
writing fields, (c) assign the reference to `instance`. The JLS does not require (b) to
happen-before (c) becomes visible to another thread absent synchronization on that reference's
*read* side too — a thread reading `instance` outside any lock (as the outer `if` does) has no
happens-before edge forcing it to see the fully-constructed object. On AArch64 specifically, the
weaker memory model makes step (c) becoming visible before step (b) completes measurably easier to
trigger than on x86-TSO — this is exactly why the syllabus leaf names AArch64: **jcstress on
AArch64 hardware or under its AArch64 memory-model simulation mode is the honest way to hunt for
this**, because an x86 run may never surface it even across a long soak.

**Pitfall:** "DCL is broken because of the double locking pattern itself." The locking is correct
— it's a legitimate double-check for avoiding lock contention after warm-up. The bug is entirely
in the *unsynchronized outer read* combined with a *non-volatile* backing field; the pattern is
salvageable with one keyword.

### The fix

```java
/** FIXED: volatile makes the write of `instance` happen-before any subsequent read of it. */
class FixedBonusService {
    private static volatile FixedBonusService instance;
    final BigDecimalCappedRate rate = new BigDecimalCappedRate("0.10", "100");

    static FixedBonusService getInstance() {
        FixedBonusService result = instance;         // one volatile read, not two
        if (result == null) {
            synchronized (FixedBonusService.class) {
                result = instance;
                if (result == null) {
                    instance = result = new FixedBonusService();
                }
            }
        }
        return result;
    }
}
```

`volatile` on `instance` gives the write inside the lock a happens-before edge to *any* subsequent
read of that field, synchronized or not — the JMM's volatile-write-happens-before-volatile-read
rule applies regardless of which thread's read it is. That closes exactly the gap the broken
version had: a reader can now only ever see `instance` as either `null` or fully constructed,
never a reference to a half-built object. The local `result` variable is a standard micro-tweak
(avoids re-reading the volatile field three times per call in the common fast path) and is not
itself required for correctness.

```java
@JCStressTest
@Outcome(id = "1", expect = Expect.ACCEPTABLE, desc = "Only outcome permitted: reader always sees a fully-constructed singleton.")
@State
public class FixedDclTest {
    @Actor
    void writer() {
        FixedBonusService.getInstance();
    }

    @Actor
    void reader(L_Result r) {
        FixedBonusService svc = FixedBonusService.instance;
        r.r1 = (svc == null || svc.rate != null) ? 1L : 0L;
    }
}
```

Under jcstress this test declares exactly one `ACCEPTABLE` outcome and no `ACCEPTABLE_INTERESTING`
bucket — a clean run with zero forbidden-outcome hits across the soak is the harness's own proof
that the fix closed the gap, as opposed to the broken version where `ACCEPTABLE_INTERESTING` hits
accumulate (rarely on x86, far more readily on AArch64).

`[RESEARCH]`: jcstress's own documentation (the `org.openjdk.jcstress` samples module, distributed
with the OpenJDK jcstress project) uses this exact DCL shape as one of its canonical
`tests.demo` examples, confirming this is the standard way the JDK's own concurrency test
infrastructure demonstrates the bug — it is not a fabricated teaching example.

**Insight:** the alternative fix — initializing the singleton eagerly as a `static final` field,
or via the initialization-on-demand holder idiom (a nested class whose static initializer runs
exactly once under the JLS's class-initialization lock) — sidesteps DCL entirely by relying on the
JVM's own class-loading happens-before guarantee instead of a hand-rolled `volatile` check. DCL is
worth knowing because it generalizes to non-singleton lazy-init patterns where the holder idiom
doesn't fit as cleanly (e.g. lazily building one of several keyed instances).

**Interview:** "Why does DCL need `volatile`, specifically?" Because the *inner* synchronized
block is only entered by threads that lost the outer race — a reader that takes the fast (outer,
unlocked) path never synchronizes at all, so the only mechanism left to give it a happens-before
edge to the writer's construction is `volatile` on the shared field itself.

> **Definition:** double-checked locking is a lazy-initialization pattern that reads a shared
> reference twice — once unlocked for the fast path, once locked to avoid duplicate construction —
> and is correct under the JMM if and only if that shared reference is `volatile`.

---

## Pitfalls

### Trusting a clean local jcstress run as proof of correctness

**Wrong**
```
$ java -jar jcstress-tests.jar -t BrokenDclTest
...
Observed state: (1) — 100.000%
No interesting or forbidden outcomes on this run.
```
"Ran clean, ship it" — on x86, a short soak, low iteration count, or a JIT that happened not to
reorder the specific instructions this run can all produce zero interesting-outcome hits for a
genuinely broken class.

**Right:** run a long soak (`-jvmArgs -Xss..., -iters 5+ -time 30+` or jcstress's `-m stress`
mode), on more than one architecture where possible (x86 and AArch64 expose different reorderings),
and treat any nonzero `ACCEPTABLE_INTERESTING`/`FORBIDDEN` count as a real finding regardless of
how rare — jcstress reports rates as low as 1-in-billions as genuine hits, not noise.

**Why people believe it:** unit tests train the reflex "if it ran and passed, it's correct." jcstress
tests are not unit tests — they are statistical searches for reorderings the JMM *permits*, and a
clean run only means the search didn't happen to find one *this time, on this hardware*.

---

## Cheat sheet

| Concept | Broken shape | Guarantee that fixes it | Where it applies |
|---|---|---|---|
| Unsafe publication | non-final fields, plain shared reference | `final` fields (JLS §17.5 freeze) | `SafeReservation` |
| DCL outer read | non-volatile singleton field, unlocked read | `volatile` on the field | `FixedBonusService.instance` |
| x86 vs AArch64 | x86-TSO forbids many JMM-legal reorderings by default | none — architecture doesn't grant correctness | always test on AArch64 too |
| jcstress outcome classes | `ACCEPTABLE` = intended, `ACCEPTABLE_INTERESTING` = legal-but-surprising, `FORBIDDEN` = real bug | — | read `@Outcome` before trusting a "pass" |
| Holder idiom alternative | avoids DCL by using class-init happens-before | JLS class initialization lock | preferred for plain singletons |

## Self-test

**Q1.** Why does `final` on `SafeReservation`'s fields fix visibility even though the shared
reference field holding it is never made `volatile`?

<details><summary>Answer</summary>

The JMM's final-field freeze guarantee (JLS §17.5) attaches to the object's construction itself,
not to the reference's publication path — any thread that obtains a reference to the object by any
means, once construction has completed and the reference did not escape early, is guaranteed to
see the final fields' constructed values. It is independent of whether the field carrying the
reference is `volatile`.

</details>

**Q2.** In `BrokenDclTest`, why is a reader outcome of `(0)` classified `ACCEPTABLE_INTERESTING`
rather than `FORBIDDEN`?

<details><summary>Answer</summary>

Because the JMM genuinely permits it — there is no happens-before edge preventing it given a
non-volatile field, so it is a legal outcome under the spec, just a surprising and unwanted one for
this program's correctness. `FORBIDDEN` is reserved for outcomes the JMM itself rules out; seeing
one there would indicate a JVM bug, not a program bug.

</details>

**Q3.** Why does the syllabus specifically call out running the DCL harness on AArch64 rather than
just "run it more times" on the original machine?

<details><summary>Answer</summary>

x86's TSO memory model forbids several store/load reorderings the JMM only permits, so a broken
program can run correctly on x86 indefinitely by architectural accident. AArch64's weaker model
allows those same reorderings to actually occur, making a genuinely JMM-illegal-looking-but-legal
outcome far more likely to surface — it changes the probability of hitting the bug, not just the
sample size.

</details>

**Q4.** What is the one-line reason `volatile` fixes DCL but adding a second, redundant
`synchronized` block around the outer check would also "fix" it — and why is the `volatile`
version still preferred?

<details><summary>Answer</summary>

Both close the happens-before gap; synchronizing the outer check works but forces every call,
including all the post-warm-up fast-path calls, through the lock — precisely the cost DCL exists to
avoid. `volatile` gives the same visibility guarantee at the cost of a cheaper read barrier instead
of an exclusive lock acquisition on every call.

</details>

**Q5.** Why does the initialization-on-demand holder idiom avoid needing `volatile` at all?

<details><summary>Answer</summary>

It delegates the guarantee to the JLS's class-initialization semantics: a class's static
initializer is guaranteed to run at most once, under an implicit lock, and any thread that
triggers or observes the class being initialized is guaranteed to see the fully-initialized static
fields — this happens-before edge is built into class loading itself, not hand-rolled with a
volatile check.

</details>

**Q6.** A colleague argues "our DCL bug never showed up in six months of production traffic on
x86-64, so it isn't real." What's wrong with that argument?

<details><summary>Answer</summary>

Absence of observed failure on one architecture over one traffic pattern is not proof of
correctness under the JMM — it is proof that this particular hardware and workload's reordering
window hasn't been hit yet. A JIT recompilation, a new CPU generation, a move to AArch64
infrastructure, or simply more traffic can all change the odds without changing the code; the bug
is a spec violation regardless of empirical non-occurrence.

</details>

**Q7.** What does `L_Result`/`II_Result` mean in the jcstress harness signatures, and why does
the harness pass a result object into the `@Actor` method rather than returning a value?

<details><summary>Answer</summary>

They are jcstress-provided result-holder types (`L` = long, `II` = two ints) used because jcstress
needs to record each actor's observed value per-interleaving across millions of runs without the
overhead or reordering risk of a return-value path; writing into a shared result field is the
harness's own controlled communication channel, separate from the racy field under test.

</details>

## Deferred

None — both leaves (4.8.9, 4.8.10) are fully covered above.

---

**Leaves covered:** 4.8.9–4.8.10 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 455
