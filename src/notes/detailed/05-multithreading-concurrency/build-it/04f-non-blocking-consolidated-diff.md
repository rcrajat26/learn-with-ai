# 05 Multithreading and Concurrency — The non-blocking consolidated diff — BUILD IT (§4.4, leaf 4.4.11)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [A copy-on-write list and a mini CHM](04e-cow-list-and-mini-chm.md) · Next: [A thread pool from scratch](05-a-thread-pool-from-scratch.md)

## 4.4.11 Diff table — every §4.4 build vs. its JDK counterpart

Five structures were built across this section: `TreiberStack` (04-treiber-stack-and-aba.md),
`MichaelScottQueue` (04c-michael-scott-queue.md), `MiniStriped64` (04d, this section's leaf 4.4.7),
`CowListenerList` (04e, leaf 4.4.9) and `MiniConcurrentMap` (04e, leaf 4.4.10). None of them is a
toy in the sense of being wrong — each implements the real algorithm its JDK counterpart uses. What
they omit is uniformly the same category of thing: the infrastructure a general-purpose library
class needs to be a drop-in `java.util`/`java.util.concurrent` citizen, as opposed to the
concurrency technique itself.

| Aspect | `TreiberStack` vs `ConcurrentLinkedDeque` | `MichaelScottQueue` vs `ConcurrentLinkedQueue` | `MiniStriped64` vs `LongAdder` | `CowListenerList` vs `CopyOnWriteArrayList` | `MiniConcurrentMap` vs `ConcurrentHashMap` |
|---|---|---|---|---|---|
| **`Spliterator` support** | none — no `Iterable` at all in the minimal form | none | not applicable (not a collection) | basic `Iterable`/`Iterator` only; no `Spliterator`, so no `stream()` | none; no `keySet()`/`entrySet()`/`values()` views, hence no stream source |
| **`toArray`** | not implemented | not implemented | not applicable | not implemented — would need a defensive copy of the current snapshot array | not implemented — would need a full-table snapshot walk |
| **Serialization** | not `Serializable`; the JDK class implements a custom `writeObject`/`readObject` that avoids serializing raw node pointers | same gap | not `Serializable`; real `LongAdder` supports it via a `SerializationProxy`-style substitute | not `Serializable`; real class serializes the snapshot array directly | not `Serializable`; real class has custom serial form avoiding raw `Node` graphs |
| **`size()` semantics and cost** | O(n) walk if added (not present here); real `ConcurrentLinkedDeque.size()` is also O(n) and documented as an approximation under concurrent modification | same — Michael–Scott queues have no maintained count; `size()` is O(n) and approximate in both the mini and real version | `sum()` is O(cells), racy, non-linearizable — same contract as the real `LongAdder.sum()` | O(1), exact for the snapshot it reads, but that snapshot may already be stale by the time the caller acts on it | not implemented; real `ConcurrentHashMap.size()`/`mappingCount()` sums per-segment counters and is also only approximate under concurrent mutation |
| **Iterator consistency model** | none provided | none provided | not applicable | weakly consistent by construction — snapshot at iterator creation, never reflects later mutation, never throws `ConcurrentModificationException` | none provided; real `ConcurrentHashMap`'s iterators are weakly consistent (may or may not reflect concurrent puts, never throw CME) |
| **Null policy** | mini version does not guard against `null` elements; real `j.u.c` non-blocking structures explicitly forbid `null` (ambiguous with "absent") | same gap and same reason | not applicable (primitive `long`) | mini version allows `null` listeners; real `CopyOnWriteArrayList` allows `null` elements (it is List-shaped, not Map-shaped) | mini version does not guard; real `ConcurrentHashMap` throws `NullPointerException` on a `null` key or value, precisely because `null` would be ambiguous with "not present" under concurrent `get` |
| **Memory per element** | one `Node` object: object header (12–16 bytes compressed-oops) + item reference + next reference, no padding | same per-node shape, plus the queue keeps one extra dummy node at all times | no per-element cost; cost is per-`Cell` (padded to a cache line, ~64 bytes, up to `NCPU` cells total) | one array slot (a reference) per element, but every mutation allocates a whole new array — transient peak memory is O(n) extra during a write | one `Node` per entry: header + hash + key ref + value ref + next ref, no padding; real `ConcurrentHashMap` is comparable but adds treeified-bin nodes (`TreeNode`, larger) once a bin treeifies |

### What a production-grade version needs that a teaching version omits

Every gap above falls into one of three buckets, and they generalize beyond just these five
classes:

1. **Collection-framework citizenship** — `Spliterator`, `stream()`, `toArray()`, `Serializable`,
   the `AbstractCollection`/`AbstractMap` method implementations that make a class usable
   everywhere a `Collection` or `Map` is expected. None of this changes the concurrency behavior;
   it is the tax every general-purpose library class pays to interoperate with the rest of the
   platform, and a purpose-built internal structure used behind one well-defined API often has no
   need to pay it.
2. **Exact accounting under concurrency** — a maintained, atomically-updated element count is
   expensive to keep exactly right without adding contention back in (which is exactly what
   striping — §4.4.7 — exists to avoid), so both the mini versions and the real JDK classes settle
   for an approximate or O(n) `size()` rather than paying for exactness on every mutation. This is
   a genuine, documented trade-off in the real classes too, not a shortcut unique to a teaching
   version.
3. **Scale-safety mechanisms** — treeification and cooperative incremental resize (04e-cow-list-
   and-mini-chm.md's honesty note) are the two gaps in this table that are not "same trade-off as
   the JDK" but genuine missing capability: at `ClientRestrictions`' 2.4M-client scale, a
   pathological hash distribution or a synchronous full-table resize would be a real production
   incident, not a theoretical one. A production-grade version of `MiniConcurrentMap` needs both
   before it should hold real traffic; a production-grade `TreiberStack`/`MichaelScottQueue` needs
   node pooling or a hazard-pointer scheme to close the ABA/reclamation gap covered in
   04b-why-java-is-aba-safe.md.

**Insight:** every one of these five structures gets the *hard part* — the actual lock-free or
striped algorithm — right and complete. What is missing is uniformly the parts that do not teach
the concurrency technique: framework glue, exactness under load that the real classes also
sacrifice, and the two scale mechanisms (treeify, cooperative resize) that only matter once a
structure is expected to survive adversarial or massive-scale input. Knowing exactly which bucket a
gap falls into is the actual skill this table is testing — "it's missing `Spliterator`" is a
non-issue; "it's missing cooperative resize at 2.4M entries" is a blocker.

## Pitfalls

### Assuming "it compiles and passes a single-threaded test" means it is production-ready

**Wrong**
```java
MiniConcurrentMap<ClientId, ClientRestrictionSet> restrictions = new MiniConcurrentMap<>(1 << 20);
restrictions.compute(clientId, (id, existing) -> newRestrictionSet);
// single-threaded smoke test passes; ships behind ClientRestrictions unchanged
```
A single-threaded test exercises none of the CAS-retry paths, none of the `synchronized`-bin
contention paths, and none of the treeify/resize gaps — it validates that the algorithm's happy
path is correct, not that the structure survives 2.4M clients under concurrent load.

**Right**
Treat every structure in this file as a **teaching-complete, production-incomplete** artifact: the
concurrency technique is real and correct, but before it holds real traffic it needs the gaps in
this diff table triaged against bucket 3 specifically (treeify, cooperative resize, node
reclamation) — the other two buckets are acceptable to defer or never close.

**Why people believe it:** the code in 04, 04c, 04d and 04e is not toy-quality in the way a
`Foo`/`Bar` example would be — it is a faithful, working implementation of the real algorithm, which
makes it easy to conflate "algorithmically correct" with "ready to replace `java.util.concurrent`".

## Cheat sheet

| Structure | Safe to use as-is for | Needs before production | Cross-reference |
|---|---|---|---|
| `TreiberStack` | a bounded free-list of reusable objects, low-to-moderate contention | node pooling or hazard pointers if ABA-sensitive reuse is possible | 04b-why-java-is-aba-safe.md |
| `MichaelScottQueue` | an unbounded work queue, FIFO, moderate contention | same reclamation concern as the stack | 04c-michael-scott-queue.md |
| `MiniStriped64` | a hot write-mostly metric/throughput counter | nothing further — the mini version is close to feature-complete for this use | 04d-striped-counter-and-measurement.md |
| `CowListenerList` | a rarely-mutated registry (listeners, routes) | nothing further for its intended read-heavy niche | 04e-cow-list-and-mini-chm.md |
| `MiniConcurrentMap` | a small-to-moderate table with a well-spread hash and infrequent resizing | treeification (hash-collision safety) and cooperative resize (pause-free growth) before real client-scale load | 04e-cow-list-and-mini-chm.md |

## Self-test

**Q1.** Why do both the mini structures and their real JDK counterparts leave `size()` either
O(n) or approximate, rather than maintaining an exact atomic counter?

<details><summary>Answer</summary>

Maintaining an exact count under concurrent mutation requires every mutating operation to also
update a shared counter, which reintroduces exactly the contention point (a single hot atomic) that
the rest of the structure was designed to avoid. Both the teaching versions and the real classes
choose to sacrifice `size()` exactness or cost rather than reintroduce that bottleneck.

</details>

**Q2.** Which two gaps in the diff table are not "acceptable trade-off, same as the JDK" but
genuine missing production capability, and why do they matter specifically at `ClientRestrictions`'
2.4M-client scale?

<details><summary>Answer</summary>

Treeification and cooperative incremental resize. Without treeification, a poor or adversarial hash
distribution can degrade a single bin to O(n) lookup; without cooperative resize, growing the table
requires a synchronous, map-wide pause that blocks all concurrent readers and writers for its
duration — both become real incidents, not theoretical ones, once the table actually holds on the
order of millions of entries under continuous concurrent traffic.

</details>

**Q3.** Why is `null` forbidden as a key or value in a real `ConcurrentHashMap` but allowed as an
element in a real `CopyOnWriteArrayList`?

<details><summary>Answer</summary>

In a map, `get(key)` returning `null` would be ambiguous between "the key maps to `null`" and "the
key is absent" — a distinction a single-threaded `HashMap` can resolve with a follow-up
`containsKey` call, but a concurrent map cannot, because another thread could insert or remove
between the two calls. A list has no such ambiguity: `get(i)` for a valid index always means "the
element at that position", so `null` as an element carries no double meaning.

</details>

**Q4.** Why does none of the five mini structures implement `Spliterator`, and what would be lost
by leaving it out permanently even in a hardened version?

<details><summary>Answer</summary>

`Spliterator` exists to support `stream()` and parallel decomposition, which is orthogonal to the
concurrency-safety guarantees these structures exist to provide — a structure can be fully
concurrency-safe and still have no stream integration. Leaving it out permanently costs only
`Stream` API ergonomics (callers must iterate manually or wrap the structure), never correctness or
performance of the core operations.

</details>

**Q5.** Why is a weakly-consistent iterator (as in `CowListenerList` and the real
`ConcurrentHashMap`) considered a feature rather than a limitation?

<details><summary>Answer</summary>

The alternative — a strongly consistent iterator that reflects every concurrent mutation exactly —
would require either locking out mutations for the duration of iteration (defeating the point of a
lock-free or copy-on-write structure) or throwing `ConcurrentModificationException`, which forces
callers to defensively copy before iterating anyway. A weakly-consistent iterator never throws and
never blocks a mutator, at the cost of the reader accepting it may see a slightly stale view.

</details>

**Q6.** What single mechanism, if added to `TreiberStack` and `MichaelScottQueue`, would close
their shared reclamation gap, and what does it protect against that node pooling alone does not?

<details><summary>Answer</summary>

Hazard pointers (or an equivalent safe-memory-reclamation scheme). Node pooling prevents the
specific ABA pattern where a freed node is reused with the same identity, but it does not, on its
own, guarantee that a node currently being read by one thread is never concurrently freed and
overwritten by another — hazard pointers add the bookkeeping that makes a thread announce "I am
still reading this node" so no other thread reclaims it out from under the reader.

</details>

---

**Leaves covered:** 4.4.11 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 180
