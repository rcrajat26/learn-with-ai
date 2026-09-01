# 02 Java Collections — Choosing a concurrent collection — INTERNALS (§3.14.34, §3.14.35, §3.14.37 the failure catalogue, the choosing table and virtual threads)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [concurrent-collections/05b-lock-free-queues-and-choosing.md](05b-lock-free-queues-and-choosing.md) · Next: [utilities/01-collections-and-arrays.md](../utilities/01-collections-and-arrays.md)

---

## The unsafe-collection failure catalogue

House rule: a race that fires proves a bug exists; a race that does not fire proves
nothing. None of the rows below rely on a hammer-loop that got lucky once — each
failure mode is derived from the unguarded read/write sequence in the real source, the
same way an earlier file's `LinkedHashMap` corruption analysis worked. The one place a
program is shown, the interleaving is performed by hand on a single thread via
reflection — deterministic, and it reproduces the exact observable symptom with no
race at all.

| Collection | Failure mode | Mechanism | Symptom in production |
|---|---|---|---|
| `HashMap` | Resize race — lost/duplicated entries | `resize()` reads the old table and builds bucket lists (`loHead`/`hiHead`, `HashMap.java:744,748`) without any lock; a concurrent `put` on another thread can observe a half-migrated table, land in the wrong or a stale bucket | Entries silently vanish, or appear duplicated across buckets, under concurrent writes with no exception thrown |
| `HashMap` (JDK 7 only) | Infinite loop during resize | Old (`transfer`) resize rebuilt each bucket by **head-insertion**, which could reverse a bucket's node order; two threads racing the same resize could each observe the other's half-built list and link a node to itself, forming a cycle a subsequent `get` would loop on forever | 100% CPU, thread stuck — **version-stale as a current risk**: JDK 8 replaced head-insertion with tail-insertion (`HashMap.java:744,748`, `loHead`/`hiHead` preserve original order), which removes *this specific* cycle-forming mechanism. Saying "`HashMap` under concurrency can infinite-loop" as a live JDK 8+ risk is wrong; saying "`HashMap` under concurrency is unsafe" remains true |
| `ArrayList` | `ArrayIndexOutOfBoundsException`, interior nulls, wrong `size()` | `add(E e, Object[] elementData, int s)` performs `elementData[s] = e; size = s + 1;` as two separate, non-atomic, non-volatile writes (`ArrayList.java:481–486`) — a reader can observe the size bump before the slot write becomes visible | `get()` throws `AIOOBE` on a slot that was counted but never written, or a completed `toString()`/iteration shows a `null` in the middle of otherwise non-null elements |
| `ArrayList` / any unsynchronized collection | `size` drift | Any compound operation (check-then-act, `size()` then `get(size()-1)`) is not atomic with respect to concurrent structural modification | Off-by-one or stale reads that "usually" work and fail under load, notoriously hard to reproduce in a debugger |
| `SimpleDateFormat`-style shared mutable state | Corrupted formatted output | Not a collection at all, but the same root cause: an instance field (`Calendar` inside `SimpleDateFormat`) mutated in place by every call, shared across threads with no synchronization | Two threads formatting different dates on a shared `SimpleDateFormat` instance can each see the other's partially-mutated `Calendar` state and produce a wrong or garbled string |

**Insight:** Java 8's tail-insertion resize fixed a cycle, not a class of bugs — the
lost-entry, duplicated-entry, and general corruption modes in the first row are exactly
as live on JDK 21 as they were on JDK 7. Concluding "it's safe now" from the infinite
loop's disappearance is precisely the version-stale mistake this table exists to
correct: the fix removed one symptom, not the underlying lack of synchronization.

**Deterministic proof of the `ArrayList` mechanism** — the two writes performed by hand,
one thread, no race:

```java
import java.lang.reflect.Field;
import java.util.ArrayList;

public class Demo {
    public static void main(String[] args) throws Exception {
        ArrayList<String> list = new ArrayList<>();
        list.add("a"); list.add("b"); list.add("c");

        Field elementData = ArrayList.class.getDeclaredField("elementData");
        Field size = ArrayList.class.getDeclaredField("size");
        elementData.setAccessible(true);
        size.setAccessible(true);

        Object[] backing = (Object[]) elementData.get(list);
        int s = (int) size.get(list);

        size.set(list, s + 1);          // simulate "size = s + 1" landing first
        System.out.println("size bumped before slot write: size=" + list.size()
            + " get(3)=" + backing[3]);  // interior null, wrong-looking size

        backing[3] = "d";                // the slot write that should have come first
        System.out.println("after slot write: size=" + list.size()
            + " get(3)=" + list.get(3));
    }
}
```
Requires `--add-opens java.base/java.util=ALL-UNNAMED`. Actual output on JDK 21:
```
size bumped before slot write: size=4 get(3)=null
after slot write: size=4 get(3)=d
```
That is exactly the "size says 4, slot 3 is still null" symptom a genuine race between
two threads calling `add` can produce — reproduced deterministically instead of chased
with a hammer loop that might not fire on this run of this machine.

**Probabilistic reproduction was deliberately not shipped for the `HashMap`/`ArrayList`
races above.** A hammer loop that corrupts a `HashMap` on one run proves the bug is
real, but a clean run proves nothing — the race window can be microseconds wide and
scheduling noise routinely hides it. Publishing a "passing" transcript as safety
evidence would be misleading, so the mechanism is derived from the source instead.

---

## Choosing table

| Need | Choose | Why | Wrong when |
|---|---|---|---|
| Read-mostly, small collection, rare writes | `CopyOnWriteArrayList`/`Set` | Readers never block, never see a torn list — a stale-but-consistent snapshot | Frequent writes: every write copies the whole backing array, O(n) per write |
| General-purpose concurrent map | `ConcurrentHashMap` | O(1) lookup, fine-grained internal locking only on writes, no external synchronization needed | Need sorted iteration or range queries — CHM has neither |
| Sorted map/set under concurrency | `ConcurrentSkipListMap`/`Set` | Only concurrent sorted option in the JDK | Don't need ordering — CHM is faster and O(1) `size()` |
| Producer-consumer with a bound (backpressure) | `ArrayBlockingQueue` / `LinkedBlockingQueue` | Blocks producers when full, blocks consumers when empty — the bound is the backpressure | No bound needed, or need non-blocking `poll`/`offer` semantics |
| Producer-consumer, unbounded, non-blocking | `ConcurrentLinkedQueue` | Lock-free, no thread ever parks | Need a bound, or need to know an item was actually received (see `LinkedTransferQueue`) |
| Handoff where producer must know consumer received it | `LinkedTransferQueue` (`transfer`) | Only JDK queue whose `put`-analogue can block until receipt | Don't need the receipt guarantee — plain `put`/`offer` on any queue is cheaper |
| Single-writer, occasional readers | `synchronized` block around the write, plain collection | Simplest correct tool when contention is genuinely low | High contention, or virtual threads in the mix on JDK 21 — see below |
| Immutable snapshot swap | `AtomicReference<List<T>>`, replace whole reference | Readers always see a fully-built, immutable list; no partial state ever visible | Frequent small mutations — rebuilding the whole list every time is wasteful; use CHM/CSLM instead |
| Bounded pipeline specifically | `ArrayBlockingQueue` | Fixed-capacity array, no resizing, tightest memory footprint of the blocking queues | Need to grow dynamically — use `LinkedBlockingQueue` with a capacity instead |
| Concurrent set with no ordering need | `ConcurrentHashMap.newKeySet()` | A real `Set<E>` backed by CHM — same characteristics, no separate class to reason about | Need sorted order — use `ConcurrentSkipListSet` |

**Insight:** a bound is not primarily a memory saver — it is a rate limiter.
`ArrayBlockingQueue`'s fixed capacity converts a producer that outpaces its consumer
into a producer that *blocks*, which is the only thing standing between a temporary
backlog and an unbounded one; that is why the bounded/unbounded column above decides
more than how much heap the queue is allowed to consume. **Interview:** "When would
you not use `ConcurrentHashMap`?" — when you need sorted iteration or range views
(`ConcurrentSkipListMap`), or when a producer needs proof a consumer actually received
an item (`LinkedTransferQueue`'s `transfer`), since a plain concurrent map gives you
neither.

**Decision tree, in prose:** need a map? — sorted → `ConcurrentSkipListMap`; unsorted →
`ConcurrentHashMap`. Need a set? — same split, `ConcurrentSkipListSet` versus
`ConcurrentHashMap.newKeySet()`. Need a queue? — bounded → blocking queue family
(earlier file); unbounded, no receipt guarantee → `ConcurrentLinkedQueue`; unbounded
and *do* need receipt guarantee → `LinkedTransferQueue` (previous file). Read-mostly
and small → skip all of that, use copy-on-write. Only one writer ever → a plain
`synchronized` block wins on simplicity, mind the virtual-thread caveat below.

> **There is no universal "concurrent collection" — the choice is driven by exactly
> three questions: does it need to be sorted, does it need a bound, and does a writer
> need proof the reader actually received the item.**

---

## Virtual threads and collections — version-scoped, handle with care

**On JDK 21 (this file's target version): `synchronized` pins a virtual thread to its
carrier for the duration of any blocking operation performed inside the monitor.** If
many virtual threads contend on a `synchronized` block — including one wrapped around
a `Collections.synchronizedMap`/`synchronizedList` — each one blocking on the monitor,
or blocking on I/O *while holding* it, occupies a platform carrier thread for that
whole duration, enough with enough virtual threads to starve a small carrier pool
(`ForkJoinPool`, sized to cores by default) and stall unrelated work. `ReentrantLock`
does **not** pin — it parks via `LockSupport.park`, which the scheduler unmounts
around. **Actionable JDK 21 advice: prefer `ReentrantLock` over `synchronized` in code
paths many virtual threads run through**; diagnose with `-Djdk.tracePinnedThreads=full`.
**Pitfall:** treating the `ReentrantLock` swap as the whole fix for virtual-thread
scalability — pinning is only one contributor to carrier starvation, and a virtual
thread blocked on synchronous I/O or a native call with no lock involved at all still
occupies its carrier for that duration; swapping the lock type doesn't touch that.

**Interview:** "Why does `synchronized` behave differently under virtual threads?" —
on JDK 21 the monitor is tied to the carrier thread, so a virtual thread blocked
inside one pins it; JEP 491 (JDK 24) re-associates the monitor with the virtual thread
itself, removing the pin.

**The change:** confirmed via web search against the JEP itself — **JEP 491,
"Synchronize Virtual Threads without Pinning,"** re-associates a monitor with the
virtual thread rather than its carrier, so a blocked virtual thread can unmount and
free its carrier instead of pinning it. Proposed to target, and shipped in, **JDK 24**
— matching the leaf's "Java 24+." After that, the advice above becomes obsolete for
*this specific* reason (`ReentrantLock` keeps its other advantages regardless of
version). Everything above the JEP paragraph is true and actionable on JDK 21, this
note set's target; the JEP paragraph exists so the advice doesn't quietly go stale.

**Not deterministically demonstrable here:** whether a `synchronized` block actually
pins depends on carrier pool sizing and scheduler timing — a short program cannot
reliably manufacture and observe starvation on demand, and a "successful" demo on one
run would prove nothing in general. This file states documented JDK behaviour instead
of fabricating a run.

---

## Pitfalls

### Treating "`HashMap` under concurrency can infinite-loop" as a current JDK 8+ risk

**Wrong belief:** "The infinite loop was a Java 7 thing, fixed now" — stated as if the
other half (corruption) were fixed too.

**Right:** the *specific cycle-forming mechanism* (head-insertion during resize) was
removed by Java 8's tail-insertion resize (`HashMap.java:744,748`). Lost/duplicated
entries and other resize-race corruption were **not** fixed — `HashMap` remains
unsafe for concurrent mutation on every version. "It can infinite-loop" is version-
stale; "it is unsafe" is still exactly true.
**Why people believe it:** the Java 7 incident is famous, and "fixed in 8" gets
over-applied to the whole safety story instead of just that one symptom.

### Using `synchronized` in virtual-thread-heavy code on JDK 21

**Wrong**
```java
// JDK 21, run under a virtual-thread executor with many concurrent callers
Map<String, Session> sessions = Collections.synchronizedMap(new HashMap<>());
// every synchronized block a virtual thread blocks inside pins its carrier
```

**Right (on JDK 21)**
```java
ReentrantLock lock = new ReentrantLock();
Map<String, Session> sessions = new HashMap<>();
lock.lock();
try {
    sessions.put("id", new Session());
} finally {
    lock.unlock(); // parks, does not pin, on JDK 21
}
```
**Why people believe it:** `synchronized` is simpler and more familiar, and pinning is
invisible until carrier starvation shows up under real load — and on JDK 24+ (JEP 491)
this specific reason to avoid it disappears, so risky-on-21 code stops being risky two
LTS releases later.

---

## Cheat sheet

| Fact | Value |
|---|---|
| `HashMap` infinite loop | Java 7 only (head-insertion resize); Java 8+ tail-insertion removes the cycle, corruption remains |
| `ArrayList.add` race window | `elementData[s] = e; size = s + 1;` — two non-atomic writes |
| Virtual threads + `synchronized`, JDK 21 | Pins the carrier while blocked inside the monitor |
| Virtual threads + `synchronized`, JDK 24+ | No longer pins — JEP 491 |
| Sorted + concurrent | `ConcurrentSkipListMap`/`Set` — the only option |
| Unbounded + non-blocking queue | `ConcurrentLinkedQueue` |
| Bounded pipeline | `ArrayBlockingQueue` |
| Concurrent set, unsorted | `ConcurrentHashMap.newKeySet()` |

---

## Self-test

**Q1.** Is "`HashMap` under concurrent modification can infinite-loop" still accurate? What remains true?

<details><summary>Answer</summary>

No — the cycle-forming mechanism (head-insertion resize) was removed by Java 8's
tail-insertion resize (`HashMap.java:744,748`). `HashMap` remains completely unsafe for
concurrent mutation on every version; a resize race can still lose or duplicate
entries, it just won't spin forever doing it.

</details>

**Q2.** What non-atomicity in `ArrayList.add` causes an interior null and wrong `size()`, and how was it shown deterministically here?

<details><summary>Answer</summary>

`elementData[s] = e; size = s + 1;` are two separate, non-volatile writes
(`ArrayList.java:481–486`). This file reproduced the corruption by reflectively
performing the size bump before the slot write on one thread — deterministic, because a
race that doesn't fire on a given run proves nothing.

</details>

**Q3.** Why does `ReentrantLock` avoid virtual-thread pinning on JDK 21, and what changes on JDK 24?

<details><summary>Answer</summary>

`synchronized` ties the monitor to the carrier thread, so a blocked virtual thread pins
it. `ReentrantLock.lock()` parks via `LockSupport.park`, which the scheduler unmounts
around. JEP 491 (shipped JDK 24) re-associates the monitor with the virtual thread
itself, removing this reason to avoid `synchronized`.

</details>

**Q4.** The choosing table recommends `LinkedTransferQueue` only for one specific case. What is it, and what should be used otherwise?

<details><summary>Answer</summary>

Only when a producer needs proof a consumer actually received the item (`transfer`).
If "eventually consumed" is enough, plain `offer`/`put` on any queue — including
`ConcurrentLinkedQueue` for the unbounded, non-blocking case — is cheaper, since it
skips the handoff-matching machinery entirely.

</details>

**Q5.** Why does the failure catalogue include `SimpleDateFormat`'s shared-mutable-state bug alongside collection failure modes, even though it isn't a collection?

<details><summary>Answer</summary>

Because the root cause is identical: an instance field (`Calendar`) mutated in place
by every call, shared across threads with no synchronization — the same "unguarded
shared mutable state" pattern behind the `HashMap` and `ArrayList` rows, just without a
`java.util.Collection` in the picture. Two threads formatting different dates on the
same `SimpleDateFormat` instance can each observe the other's partially-mutated
`Calendar` and produce a garbled string.

</details>

---

**Leaves covered:** 3.14.34, 3.14.35, 3.14.37 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 279
