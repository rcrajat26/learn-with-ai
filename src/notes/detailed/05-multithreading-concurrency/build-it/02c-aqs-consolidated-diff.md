# 05 Multithreading and Concurrency — The consolidated AQS diff table — BUILD IT (§4.2, leaf 4.2.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [AQS fairness and conditions](02b-aqs-fairness-and-conditions.md) · Next: [Bounded blocking queue, three ways](03-bounded-blocking-queue.md)

## What was built where

`02` built `SimpleMutex` and `CountingSemaphore` (leaves 4.2.1–4.2.2). `02a` built `OneShotLatch` and the
reentrant `ReentrantAqsMutex` (leaves 4.2.3–4.2.4). `02b` built `FairReentrantAqsMutex` and the
`Condition` added to `ReentrantAqsMutex` (leaves 4.2.5–4.2.6). This file is the payoff page for all of
§4.2: one table, row per synchronizer, against the real `java.util.concurrent.locks.ReentrantLock`.
Verified against `ReentrantLock.java` and `AbstractQueuedSynchronizer.java`, `jdk-21` tag,
`raw.githubusercontent.com/openjdk/jdk`.

## The consolidated diff table

| Synchronizer | Built in | `tryLock(timeout)` | `lockInterruptibly` | Serialization | `toString` for dumps | `getOwner`/`getQueuedThreads` | Fairness |
|---|---|---|---|---|---|---|---|
| `SimpleMutex` | `02` | not implemented — add via `tryAcquireNanos` | not implemented — add via `acquireInterruptibly` | not `Serializable` | inherited `Object.toString` — useless in a thread dump | not exposed | non-fair only |
| `CountingSemaphore` | `02` | not implemented | not implemented | not `Serializable` | inherited `Object.toString` | not exposed | non-fair only |
| `OneShotLatch` | `02a` | N/A — a latch has no "timeout to acquire" beyond `await(timeout)` | supported via `acquireSharedInterruptibly` if added | not `Serializable` | inherited `Object.toString` | not exposed | N/A (shared, one-shot) |
| `ReentrantAqsMutex` | `02a` | supported via `tryAcquireNanos` if added | supported via `acquireInterruptibly` if added | not `Serializable` | inherited `Object.toString` | not exposed | non-fair only |
| `FairReentrantAqsMutex` | `02b` | implemented | implemented | not `Serializable` | inherited `Object.toString` | not exposed | fair only |
| `Condition` on `ReentrantAqsMutex` | `02b` | N/A (`Condition` has its own `await(timeout, unit)` via `ConditionObject`) | `await()` is interruptible by default in `ConditionObject` | not `Serializable` independently of its lock | inherited `Object.toString` | N/A | follows owning lock |
| `java.util.concurrent.locks.ReentrantLock` | JDK | implemented — delegates to `AbstractQueuedSynchronizer.tryAcquireNanos` | implemented — delegates to `acquireInterruptibly` | **`Serializable`**; custom `readObject` calls `s.defaultReadObject()` then `sync.setState(0)` — a deserialized lock always comes back **unlocked** regardless of the state at serialization time | overridden to print the owning thread's name or `"[Unlocked]"` | both implemented — `getOwner()` and `getQueuedThreads()` (protected on AQS, exposed publicly by `ReentrantLock`) walk the AQS queue directly | selectable — constructor takes a `boolean fair`, backed by `Sync.FairSync` or `Sync.NonfairSync` |

## Why the JDK bothers with each column

**`tryLock(timeout)`.** None of the hand-built classes in this series implement it by default; the JDK
does, because production code must be able to give up on a stuck lock rather than hang a thread forever.
A downstream service wedged inside a critical section — a stalled database call holding
`FundsLedger`'s mutex — must not be allowed to silently propagate that stall into every caller waiting
on the same lock with no way out. `tryAcquireNanos`, inherited from AQS, is what makes this a one-line
addition to any of the hand-built classes: the mechanism was always there, only the public entry point
was missing.

**`lockInterruptibly`.** Without it, a thread parked on `acquire()` cannot be cancelled — an
`interrupt()` call is recorded but not acted on until the lock is eventually granted. For a
`settlement-ingest-N` thread that a shutdown sequence needs to stop promptly, that is the difference
between a clean shutdown and one that hangs waiting for a lock that may never free up. `acquireInterruptibly`
is, again, already present on AQS; the hand-built classes in this series simply never called it.

**Serialization: `readObject` resets `state` to 0.** A lock's held/unlocked state is a property of a
live JVM's thread scheduling — the specific `Thread` object holding it, the specific threads parked on
its queue. None of that survives a serialization boundary: the receiving process has no matching
threads at all. If `ReentrantLock` shipped its held state across the wire, the first thread in the
receiving process to call `lock()` on the deserialized object would find `state != 0` with no owner
thread that could ever call `unlock()` — a permanent, un-recoverable deadlock baked into the very act of
deserializing. Resetting to `state = 0` on `readObject` is the only contract that keeps a deserialized
lock usable at all; it also means anyone relying on serialization to snapshot-and-restore lock state
across a JVM boundary is relying on behaviour the class explicitly refuses to provide.

**`toString` for thread dumps.** `ReentrantLock.toString()` prints the owning thread's name inline —
something like a `settlement-ingest-3` reference — or `"[Unlocked]"` when free. At 3 a.m. reading a
thread dump of a stalled settlement pool, this is the difference between immediately seeing "thread
`settlement-ingest-3` holds this lock, and every other `settlement-ingest-N` thread is blocked entering
`reserveStake`" and having to cross-reference raw object identities across dozens of stack traces by
hand. None of this series' hand-built classes override `toString`, so a dump of one just prints a
default `ClassName@hashcode` with no owner information at all.

**`getOwner`/`getQueuedThreads`.** `getOwner()` returns the thread currently holding the lock, or `null`
if unheld; `getQueuedThreads()` returns a best-effort snapshot collection of the threads currently
parked waiting to acquire it. Both are explicitly documented as intended for **monitoring and
diagnostic purposes only** — the collection is a point-in-time snapshot with no synchronization
guarantee against concurrent changes, so it must never be used to make a control-flow decision (for
example, "if the queue is empty, skip locking entirely" is not a safe optimisation built on
`getQueuedThreads().isEmpty()`, because the queue can change the instant after the check). What it is
safe for: feeding a metrics exporter or an admin diagnostic endpoint that answers "who's holding the
reserve-stake lock right now, and how many settlement threads are backed up behind it" without
attaching a debugger to a production process.

**The `Sync`/`FairSync`/`NonfairSync` hierarchy.** `ReentrantLock` does not put `tryAcquire`/`tryRelease`
directly on itself; it declares a private abstract static inner class `Sync extends
AbstractQueuedSynchronizer` holding the shared re-entrant logic — hold count in `state`, owner via
`setExclusiveOwnerThread`/`getExclusiveOwnerThread` — the exact same shape as this series'
`ReentrantAqsMutex`. Two concrete subclasses extend it: `NonfairSync` (barging `tryAcquire`, matching
`ReentrantAqsMutex`) and `FairSync` (the `hasQueuedPredecessors()` check, matching
`FairReentrantAqsMutex`). `ReentrantLock` itself is a thin public facade holding one `Sync sync` field,
chosen once at construction time by the `fair` boolean and never swapped after construction. The reason
the JDK bothers with this split rather than shipping two separate top-level lock classes, the way this
series does: it makes fairness a **constructor argument** on a single public type, so library and
application code can accept a `Lock` or a `ReentrantLock` without caring which internal `Sync` backs it,
and a caller can flip fairness without changing a single call site's type.

## Pitfalls

### Using `getQueuedThreads()` to decide whether it's safe to skip locking

**Wrong**

```java
ReentrantLock ledgerLock = new ReentrantLock();
// ...
if (ledgerLock.getQueuedThreads().isEmpty()) {
    // "nobody's waiting, so reading balances without the lock is fine"
    return readBalancesUnlocked();
}
```

**Right**

```java
ReentrantLock ledgerLock = new ReentrantLock();
// ...
ledgerLock.lock();
try {
    return readBalances();
} finally {
    ledgerLock.unlock();
}
```

`getQueuedThreads()` is documented as a best-effort snapshot for monitoring, not a synchronization
primitive — the set of queued threads can change in the instant between the check and the decision made
from it, and nothing about an empty queue implies the lock itself is currently unheld by some other
thread that never needed to queue at all (e.g. one that acquired it via barging before this check ran).

**Why people believe it:** the method name reads like a live, authoritative answer to "is anyone
waiting right now," and the fact that it compiles and returns a real, non-stale-looking collection makes
it feel safe to branch on.

### Assuming a serialized-then-deserialized `ReentrantLock` remembers who held it

**Wrong**

```java
ReentrantLock lock = new ReentrantLock();
lock.lock();
byte[] snapshot = serialize(lock);
// ... later, possibly in a different JVM ...
ReentrantLock restored = deserialize(snapshot);
restored.lock(); // assumed: still contended by the original holder, or already held by it
```

**Right**

```java
ReentrantLock lock = new ReentrantLock();
lock.lock();
byte[] snapshot = serialize(lock);
// ...
ReentrantLock restored = deserialize(snapshot);
// restored.isLocked() == false here — readObject reset state to 0
restored.lock(); // acquires cleanly; treat the restored lock as brand new
```

**Why people believe it:** most `Serializable` classes are written to preserve exactly the fields they
had at serialization time, so the specific, deliberate exception here — `readObject` overwriting
`state` rather than restoring it — looks like a bug rather than the only sane contract for a
lock crossing a JVM boundary with none of the original threads.

## Cheat sheet

| Column | Hand-built classes (`02`/`02a`/`02b`) | `ReentrantLock` |
|---|---|---|
| `tryLock(timeout)` | mostly absent; trivial to add via `tryAcquireNanos` | present |
| `lockInterruptibly` | mostly absent; trivial to add via `acquireInterruptibly` | present |
| Serialization | none are `Serializable` | `Serializable`; `readObject` resets `state` to 0 |
| `toString` | inherited `Object.toString` | prints owner thread name or `"[Unlocked]"` |
| `getOwner`/`getQueuedThreads` | not exposed | both public, monitoring-only, best-effort snapshot |
| Fairness | one non-fair class, one separate fair class | one class, `fair` boolean picks `FairSync`/`NonfairSync` |
| Internal split | none — logic lives directly on the class | `Sync` (shared) → `FairSync` / `NonfairSync` |

## Self-test

**Q1.** Which single field on `ReentrantLock` determines whether it behaves like this series'
`ReentrantAqsMutex` or its `FairReentrantAqsMutex`, and when is it set?

<details><summary>Answer</summary>

The `sync` field, of static type `Sync` but holding either a `NonfairSync` or `FairSync` instance. It is
chosen once, at construction time, by the `boolean fair` constructor argument (`new ReentrantLock()`
defaults to non-fair; `new ReentrantLock(true)` selects fair), and it is never swapped afterward — a
`ReentrantLock`'s fairness is fixed for its lifetime.

</details>

**Q2.** Why does `ReentrantLock.readObject` reset `state` to 0 instead of trying to preserve the lock's
held/unheld status across serialization?

<details><summary>Answer</summary>

Because a lock's state is meaningless without the specific thread objects that hold and wait on it, and
none of those threads exist in whatever process deserializes the object. If the held state were
preserved, the first thread to call `lock()` after deserialization would see `state != 0` with no path
to ever decrementing it back to 0 — a permanent deadlock manufactured purely by deserializing. Resetting
to unlocked is the only contract that leaves the restored object in a usable state.

</details>

**Q3.** A production incident shows a `settlement-ingest` thread pool stalled. What two `ReentrantLock`
features, neither present on this series' hand-built mutexes by default, would help diagnose it fastest
from a thread dump alone?

<details><summary>Answer</summary>

`toString()`, because it names the specific thread currently holding the lock (or reports
`"[Unlocked]"`) directly in the dump without cross-referencing object identities by hand; and
`getOwner()`/`getQueuedThreads()`, because they let a diagnostic tool or metrics exporter report exactly
who holds a given lock and how many threads are piled up behind it, again without attaching a debugger.

</details>

**Q4.** Why is `getQueuedThreads()` explicitly unsafe to use as the basis of a "skip locking if nobody's
waiting" optimisation?

<details><summary>Answer</summary>

It returns a best-effort, point-in-time snapshot with no synchronization guarantee against concurrent
changes — the JDK documents it for monitoring and diagnostics only. The set of queued threads (and
whether the lock itself is held at all, by a thread that barged in without ever queuing) can change in
the instant between reading the snapshot and acting on it, so any control-flow decision built on it is
racing the very thing it is trying to observe.

</details>

**Q5.** Of the six hand-built synchronizers across `02`, `02a`, and `02b`, which ones are `Serializable`,
and how does that compare to `ReentrantLock`?

<details><summary>Answer</summary>

None of them — `SimpleMutex`, `CountingSemaphore`, `OneShotLatch`, `ReentrantAqsMutex`,
`FairReentrantAqsMutex`, and the `Condition` built on `ReentrantAqsMutex` are all plain classes with no
`Serializable` implementation. `ReentrantLock` is `Serializable`, specifically so that it can be
embedded as a field inside some other `Serializable` class without that containing class having to
special-case excluding the lock field — the trade-off is the `readObject` reset-to-0 behaviour discussed
above, which the containing class's code must be written to tolerate.

</details>

**Q6.** Why does the JDK split `ReentrantLock`'s acquire logic into a `Sync` base class plus
`FairSync`/`NonfairSync` subclasses, rather than writing two separate top-level lock classes the way
this series does with `ReentrantAqsMutex` and `FairReentrantAqsMutex`?

<details><summary>Answer</summary>

So that fairness is a constructor argument on one public type instead of a choice between two distinct
classes. Application and library code that accepts a `Lock` (or even a `ReentrantLock` specifically)
never needs to know or care which concrete `Sync` subclass backs a given instance; a caller can flip the
`fair` boolean at construction without changing any call site's declared type. This series' split into
two top-level classes is simpler to read for teaching purposes but pushes that choice onto every call
site's type instead of hiding it behind one constructor argument.

</details>

---

**Leaves covered:** 4.2.7 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 280
