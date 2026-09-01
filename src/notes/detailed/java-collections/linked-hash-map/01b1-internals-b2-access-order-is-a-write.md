# 02 Java Collections — `LinkedHashMap` — INTERNALS (§3.7 `LinkedHashMap` source walk — on an access-order map, `get` is a write)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-hash-map/01b-internals-b-lru-and-sequenced.md](01b-internals-b-lru-and-sequenced.md) · Next: [linked-hash-map/01c-internals-c-sequenced-and-caching.md](01c-internals-c-sequenced-and-caching.md)

---

## §3.7.11 Access-order `get` is a structural modification `[PROVE]` `[TRAP]`

### Mental model

On an access-order `LinkedHashMap` there is no such thing as a read. `get` is a write with a return value.

Everything in this file follows mechanically from that one sentence, and almost every concurrency bug people hit with this class comes from not believing it. The previous file built a ten-line LRU on exactly this behaviour — `get` relinking the accessed node to the tail is *how* recency is tracked, since there is no timestamp anywhere in the entry. The cost of having no timestamp is that the position in a mutable list has to do the timestamp's job, and moving something in a list is a write.

### Why it matters

`modCount` is `HashMap`'s structural-modification counter, and iterators snapshot it at construction to implement fail-fast (general treatment in [../iteration/02-fail-fast-fail-safe.md](../iteration/02-fail-fast-fail-safe.md) §2.2). The convention across `java.util` is uniform: `add`, `remove`, `clear` and resize bump it; reads do not. `LinkedHashMap` in access-order mode is the one map in `java.util` that breaks that convention, and it breaks it in the direction nobody audits — the read path.

### When this bites, and when it does not

It bites whenever an access-order map is iterated while anything reads it, and whenever an access-order map is shared across threads at all. It does not bite on an insertion-ordered `LinkedHashMap`, where `get` calls nothing; that contrast is the whole content of §3.7.12 below and the reason a FIFO cache is sometimes the better engineering choice.

### The `[PROVE]` — three facts, one conclusion

**Fact 1.** `afterNodeAccess` ends by bumping `modCount`:

```java
            tail = p;
            ++modCount;
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, lines 358–359; the closing two lines of `afterNodeAccess` (declared line 336). The six preceding pointer writes are walked in [01a-internals-a2-hooks-and-access-order.md](01a-internals-a2-hooks-and-access-order.md) §3.7.4 and are cut from this excerpt deliberately, not elided. (leaf 3.7.11)

**Fact 2.** `get` calls it whenever `accessOrder` is true:

```java
    public V get(Object key) {
        Node<K,V> e;
        if ((e = getNode(key)) == null)
            return null;
        if (accessOrder)
            afterNodeAccess(e);
        return e.value;
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 534. (leaf 3.7.11)

`getOrDefault` (line 546) has the same shape and the same `if (accessOrder) afterNodeAccess(e);` line, so it is equally a write. `containsKey` does not — the `get`-versus-`containsKey` asymmetry is §3.7.7 in [01a](01a-internals-a2-hooks-and-access-order.md).

**Fact 3.** The iterator compares the live counter against a snapshot taken at construction:

```java
    abstract class LinkedHashIterator {
        LinkedHashMap.Entry<K,V> next;
        LinkedHashMap.Entry<K,V> current;
        int expectedModCount;
        boolean reversed;

        LinkedHashIterator(boolean reversed) {
            this.reversed = reversed;
            next = reversed ? tail : head;
            expectedModCount = modCount;
            current = null;
        }

        public final boolean hasNext() {
            return next != null;
        }

        final LinkedHashMap.Entry<K,V> nextNode() {
            LinkedHashMap.Entry<K,V> e = next;
            if (modCount != expectedModCount)
                throw new ConcurrentModificationException();
            if (e == null)
                throw new NoSuchElementException();
            current = e;
            next = reversed ? e.before : e.after;
            return e;
        }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 1003; `remove()` and the three concrete subclasses are omitted from this excerpt rather than elided. (leaf 3.7.11)

Two things to notice while it is on the page. First, `nextNode` walks `e.after` (or `e.before` when reversed), never the table — so `LinkedHashMap` iteration is O(size), independent of capacity, unlike `HashMap`'s table scan ([../hash-map/05a1-internals-e1b-iteration-order.md](../hash-map/05a1-internals-e1b-iteration-order.md)). Second, `hasNext()` does *not* check `modCount`; only `nextNode()` does. That is why the failure lands on the call after the offending `get`, and never on the loop condition.

**The chain.** `get` → `afterNodeAccess` → `++modCount` → `modCount != expectedModCount` → `ConcurrentModificationException`. Therefore, on an access-order map, **a single `get` invalidates every live iterator**, including the one you are standing in.

A picture would help here, but the shape is entirely in the three quotes above and adding a diagram would only redraw them; the eviction cycle is the thing worth drawing, and it is D-102 in [01b-internals-b-lru-and-sequenced.md](01b-internals-b-lru-and-sequenced.md).

### The demonstration — deterministic, single-threaded

A loop that only reads. No `put`, no `remove`, no `clear`:

```java
LruCache<String, Integer> cache = new LruCache<>(10);   // accessOrder = true
cache.put("A", 1); cache.put("B", 2); cache.put("C", 3);
int visited = 0;
try {
    for (String k : cache.keySet()) { visited++; cache.get(k); }
    System.out.println("no exception, visited=" + visited);
} catch (ConcurrentModificationException e) {
    System.out.println("threw " + e.getClass().getSimpleName()
            + " after visiting " + visited + " key(s)");
}
```
```
threw ConcurrentModificationException after visiting 1 key(s)
```

One key. The `get` on `"A"` relinked A to the tail and incremented `modCount`; the second `nextNode()` compared 4 against 3 and threw. The identical loop against the insertion-ordered map, same three keys, same JDK:

```
no exception, visited=3 keys
```

**Insight, and it is what makes this bug intermittent rather than obvious.** `afterNodeAccess`'s guard ends with the conjunct `(last = tail) != e` (line 339). If the accessed node is *already* the tail there is nothing to relink, the method returns before touching `modCount`, and no iterator is invalidated. `get`-ing the current tail inside an iteration therefore does not throw:

```
get(tail) in a loop: no exception, visited=3
```

So whether a read-only loop blows up depends on which key happens to be at the tail when the loop starts. A unit test that reads one hot key passes forever. Production, reading a spread of keys, throws on the second iteration step.

### The harder consequence — two readers are two writers

The `ConcurrentModificationException` above is deterministic, which is exactly why it is the right evidence to lead with. The multi-threaded consequence is the one that costs money, and it cannot be demonstrated deterministically.

`afterNodeAccess` writes `head`, `tail`, up to six `before`/`after` fields, and `modCount`. None of those is `volatile`; none is guarded by anything. Two threads calling `get` concurrently are two unsynchronised writers to a shared doubly-linked list, with no happens-before edge between them. The failure modes are the ordinary ones for an unguarded list:

| Corruption | Mechanism | Symptom in production |
|---|---|---|
| Lost link | one thread's write to `b.after` overwrites the other's | entries vanish from iteration while remaining findable by `get`; `size()` disagrees with the number of entries iteration yields |
| Cycle in the `after` chain | interleaved unlink/relink leaves a node pointing back into the region it came from | `nextNode()` never reaches `null` — one thread spins at 100% CPU inside `LinkedHashIterator`, the same shape as the Java 7 `HashMap` resize livelock ([../hash-map/03b-internals-c2-concurrent-resize-and-tree-split.md](../hash-map/03b-internals-c2-concurrent-resize-and-tree-split.md)) |
| Stale `head` | `head` is updated by one thread while the other is mid-unlink of the node it names | eviction removes the wrong key, or `head` names an already-unlinked node so `removeNode` finds nothing and `size` climbs past the bound forever |
| Torn `modCount` | non-atomic `++` from two threads | lost increments; a fail-fast check that should have fired does not, so a corrupt iteration proceeds silently instead of throwing |

I deliberately did not ship a multi-threaded harness for this file. A race demonstration is scheduling-dependent, a passing run proves nothing, and a failing run proves only that this machine's scheduler cooperated on this occasion. The single-threaded proof above is strictly stronger evidence: it establishes from source and from real output that `get` mutates `modCount`, and `modCount` is written by the same unguarded method that performs the six link writes. If you want the race, the harness is two threads in a loop over disjoint halves of the key space — but treat whatever it prints as an anecdote and say so.

### The gotcha, and the four ways out

**Pitfall:** the wrong belief is *"my cache is read-mostly, so I do not need synchronisation."* On an access-order `LinkedHashMap` the premise is false — there are no reads to be mostly. The symptom is a component that works under test and, under load, does one of three things: throws `ConcurrentModificationException` from a background iteration you forgot was iteration (a metrics sweep, an eviction audit, a `toString()` inside a log statement), or hangs one thread at 100% CPU in `LinkedHashIterator.nextNode`, or reports a `size()` that disagrees with what iteration finds. The fix is to pick from this table, knowing what each costs:

| Option | What it costs | Verdict |
|---|---|---|
| `Collections.synchronizedMap(new LruCache<>(n))` | every `get` and `put` takes a monitor, so all traffic serialises. Iteration is **not** covered — the wrapper synchronises individual calls, so you must hold the wrapper object's own lock across the whole loop yourself (§3.14.1–3.14.6, [../concurrent-collections/01-thread-safety-and-wrappers.md](../concurrent-collections/01-thread-safety-and-wrappers.md)) | correct and simple; the default answer |
| `ReadWriteLock`, read lock in `get` | **does not work.** `get` is a write, so it must take the *write* lock; the read lock becomes dead code and the construction degrades to an exclusive lock with two counters of extra bookkeeping | wrong, and measurably slower than the plain mutex it was meant to improve on |
| `accessOrder = false` plus a different eviction policy | loses LRU semantics — no protection against evicting a hot key. In exchange `get` becomes a genuine read (§3.7.12) | correct where FIFO or random eviction is acceptable |
| Caffeine | a dependency and a background maintenance thread; reads go to a striped ring buffer and the recency structure is reordered off the read path, which is precisely the design `LinkedHashMap` cannot have | the right answer for a real concurrent cache (leaf 3.7.17, [01c-internals-c-sequenced-and-caching.md](01c-internals-c-sequenced-and-caching.md)) |

The second row is the trap inside the fix, and it is worth saying twice: a `ReadWriteLock` is the intuitive instrument here and it is strictly counterproductive. The whole value of a `ReadWriteLock` is that readers do not exclude each other, and on this map there are no readers.

The honest contrast on the other side: with `accessOrder = false`, `get` calls nothing at all — it returns `e.value` and touches no field. An insertion-ordered `LinkedHashMap` is therefore exactly as safe to read concurrently as a `HashMap`, which is to say safe only if nobody is writing *and* the map was safely published (via a `final` field, a `volatile`, or an immutable wrapper). That is a real property, not a consolation prize, and it is why the next section exists.

**Interview:** *"Can two threads safely `get` from a `LinkedHashMap`?"* Only if it is not access-ordered. On an access-order map `get` calls `afterNodeAccess`, which relinks six references and bumps `modCount`, so it is a write — two concurrent `get`s can corrupt the chain, and a single `get` invalidates every live iterator.

> **Definition.** In access-order mode, `LinkedHashMap.get` and `getOrDefault` are structural modifications: they relink the accessed entry to the tail and increment `modCount`, so they invalidate live iterators and require exactly the same synchronisation as `put`.

---

## §3.7.12 A FIFO cache is the same class with `accessOrder = false`

**Mechanism.** `super(capacity, 0.75f, false)` — or any constructor that omits the flag, which is all four of the others — leaves `accessOrder` false, so `afterNodeAccess`'s guard `(putMode == PUT_LAST || (putMode == PUT_NORM && accessOrder)) && (last = tail) != e` (line 339) fails on every `get`. Nothing relinks, `head` stays the oldest-inserted surviving entry, and `afterNodeInsertion` evicts exactly that. Insertion-order eviction *is* FIFO, with no code beyond the `removeEldestEntry` override.

**Gotcha.** FIFO buys two things. `get` becomes a genuine read, reversing everything in §3.7.11. And the eviction schedule becomes *predictable*: an entry lives for exactly `maxEntries` subsequent insertions, whatever anyone reads. That makes it the right structure for bounded *staleness* rather than a bounded working set — a stream de-duplication window, a replay-attack nonce cache, a "have I already logged this error signature" filter. What it costs is what bug 3 in [01b](01b-internals-b-lru-and-sequenced.md) demonstrated: no protection whatsoever against evicting the hottest key in the workload.

| | LRU | FIFO | Unbounded |
|---|---|---|---|
| Constructor | `super(cap, 0.75f, true)` | `super(cap, 0.75f, false)`, or any other constructor | any constructor |
| What `get` does | relinks node to tail, `++modCount` | reads the value, nothing else | reads the value, nothing else |
| What is evicted | least recently **accessed** | least recently **inserted** | nothing |
| Is `get` a write? | yes | no | no |
| `removeEldestEntry` | `size() > max` | `size() > max` | not overridden (`return false`) |
| Concurrent readers | unsafe without a mutex | safe if no writers and safely published | safe if no writers and safely published |
| Typical use | hot-set cache, working-set bound | dedup window, nonce cache, bounded staleness | ordered map, not a cache |

> **Definition.** A FIFO cache is a `LinkedHashMap` with `accessOrder = false` and `removeEldestEntry` returning `size() > maxEntries`: identical eviction machinery, but with `get` making no structural modification, so `head` tracks insertion order rather than access order.

---

## Version note — the read path from Java 8 to Java 21

Checked against `/tmp/jdk8src/java/util/LinkedHashMap.java`, not recalled.

| Element | JDK 8 | JDK 21 | Behaviour change? |
|---|---|---|---|
| `get(Object)` | line 438 | line 534 | Cosmetic only: JDK 8 calls `getNode(hash(key), key)`, JDK 21 calls `getNode(key)`. The `if (accessOrder) afterNodeAccess(e);` line is identical |
| `afterNodeAccess` | line 305, guard `if (accessOrder && (last = tail) != e)` | line 336, guard `if ((putMode == PUT_LAST \|\| (putMode == PUT_NORM && accessOrder)) && (last = tail) != e)` | Guard extended for `SequencedMap`. `putMode` defaults to `PUT_NORM` and is only otherwise set inside `putFirst`/`putLast`, so for ordinary traffic the JDK 21 condition reduces exactly to JDK 8's. `++modCount` is present in both |
| `LinkedHashIterator` | line 701 — three fields, no-arg constructor, `next = head`, `next = e.after` | line 1003 — **four** fields including `boolean reversed`, `LinkedHashIterator(boolean)`, `next = reversed ? tail : head`, `next = reversed ? e.before : e.after` | New field and constructor parameter, added in Java 21 for `SequencedMap`'s reversed views. **JDK 8 has no `reversed` field.** The `modCount != expectedModCount` check in `nextNode()` is byte-identical |
| `final boolean accessOrder` | line 217 | line 231 | None |

So the hazard is as old as the class: `get` has been a structural modification in access-order mode since Java 1.4, and nothing about that changed in Java 21. What changed is scaffolding — `putMode` in the guard, `reversed` on the iterator — both introduced by `SequencedMap` (leaves 3.7.13–3.7.14 in [01c](01c-internals-c-sequenced-and-caching.md)). If asked whether Java 21 made `LinkedHashMap` safer to read concurrently, the answer is no; it gave the iterator a direction, not a lock.

---

## Pitfalls

### Treating a read-only loop over an access-order map as safe

**Wrong**
```java
for (String k : cache.keySet()) { cache.get(k); }   // no put, no remove, no clear
```
```
threw ConcurrentModificationException after visiting 1 key(s)
```

**Right** — iterate a snapshot, so the iterator belongs to a different collection and `modCount` is irrelevant:
```java
for (String k : List.copyOf(cache.keySet())) { cache.get(k); }
```
Or, if you must not disturb recency either, walk `entrySet()` and read `Map.Entry::getValue` — that path never calls `afterNodeAccess` (the `get`-versus-`entrySet` asymmetry, §3.7.7 in [01a](01a-internals-a2-hooks-and-access-order.md)):
```java
for (Map.Entry<String, Integer> e : cache.entrySet()) { use(e.getValue()); }
```

**Why people believe it:** `modCount` is documented as a *structural*-modification counter and every other `java.util` collection honours that reading. It is also intermittent — `get`-ing the node that is already the `tail` skips the relink entirely (guard at line 339), so a test that reads one hot key passes.

### Guarding an access-order LRU with a `ReadWriteLock`

**Wrong**
```java
V get(K k) {
    lock.readLock().lock();
    try { return cache.get(k); }        // this is a WRITE under a shared lock
    finally { lock.readLock().unlock(); }
}
```
Two threads in `get` hold the read lock simultaneously and both execute `afterNodeAccess`'s six pointer writes and `++modCount`. Nothing throws; the chain quietly loses a link, gains a cycle, or leaves `head` stale.

**Right** — either take the write lock on `get`, which makes the `ReadWriteLock` pointless and slower than a monitor:
```java
Map<K, V> cache = Collections.synchronizedMap(new LruCache<>(1000));
synchronized (cache) {                 // the wrapper does NOT lock across iteration
    for (K k : cache.keySet()) { report(k, cache.get(k)); }
}
```
or stop trying to make `LinkedHashMap` concurrent and use Caffeine, which moves recency maintenance off the read path onto a striped buffer.

**Why people believe it:** "LRU cache" reads as a read-heavy workload, and read-heavy is the textbook case for `ReadWriteLock`. The premise is right about the workload and wrong about the class — this is the one cache implementation where the read-heavy workload is a write-heavy call pattern.

### Assuming `hasNext()` will catch the modification

**Wrong**
```java
Iterator<String> it = cache.keySet().iterator();
while (it.hasNext()) {                 // never checks modCount
    cache.get("someOtherKey");         // bumps modCount
    String k = it.next();              // throws here
}
```

**Right** — there is no defensive read of `hasNext()` that helps; the check lives only in `nextNode()`. Snapshot, or do not read the map while iterating it:
```java
for (String k : List.copyOf(cache.keySet())) { cache.get("someOtherKey"); }
```

**Why people believe it:** `hasNext()` and `next()` feel like one operation, so people assume the fail-fast check happens "when you ask about the iterator". `hasNext()` is `return next != null;` and nothing else — the `modCount` comparison is the first statement of `nextNode()` (line 1003).

---

## Cheat sheet

| Thing | Behaviour | Source (JDK 21) |
|---|---|---|
| `get` on access-order map | `if (accessOrder) afterNodeAccess(e);` — a structural modification | line 534 |
| `getOrDefault` | same, equally a write | line 546 |
| `containsKey`, `entrySet` walk, `forEach` | never call `afterNodeAccess` — genuine reads | §3.7.7 in [01a](01a-internals-a2-hooks-and-access-order.md) |
| `afterNodeAccess` tail two lines | `tail = p; ++modCount;` | lines 358–359 |
| Relink skipped when | accessed node is already `tail` (`(last = tail) != e` fails) | line 339 |
| Fail-fast check location | first statement of `nextNode()`, **not** in `hasNext()` | line 1003 |
| Iterator snapshot | `expectedModCount = modCount` at construction | line 1003 |
| Iteration cost | O(size) — walks `after`/`before`, never the table | line 1003 |
| Concurrent `get` + `get` | unsafe: 6 unguarded link writes, non-atomic `++modCount`, nothing `volatile` | line 336 |
| `ReadWriteLock` fix | **does not work** — `get` needs the write lock, so the read lock is dead | — |
| Working fixes | `synchronizedMap` (+ your own lock across iteration), `accessOrder = false`, or Caffeine | — |
| `accessOrder = false` `get` | calls nothing; as safe to read as a `HashMap` if safely published and unwritten | line 534 |
| FIFO cache | same class, `accessOrder = false`; evicts least recently *inserted* | line 339 guard fails |
| Changed since Java 8? | no — hazard dates to Java 1.4. Iterator gained `boolean reversed` in 21 | JDK 8 line 701 vs 21 line 1003 |

---

## Self-test

**Q1.** Prove from source that a `get` can throw `ConcurrentModificationException` on a map nobody wrote to.

<details><summary>Answer</summary>

Three links. (1) `afterNodeAccess` ends `tail = p; ++modCount;` (lines 358–359). (2) `get` calls `afterNodeAccess(e)` when `accessOrder` is true (line 534). (3) `LinkedHashIterator.nextNode()` throws `ConcurrentModificationException` when `modCount != expectedModCount`, where `expectedModCount` was snapshotted at iterator construction (line 1003). So `for (K k : map.keySet()) map.get(k);` bumps the counter on the first `get` and fails on the second `nextNode()`. Real output on JDK 21: `threw ConcurrentModificationException after visiting 1 key(s)`.

</details>

**Q2.** The same loop sometimes does not throw. Why?

<details><summary>Answer</summary>

`afterNodeAccess`'s guard ends `&& (last = tail) != e` (line 339). If the accessed node is already the tail there is nothing to move, so the method returns before reaching `++modCount` and no iterator is invalidated. Measured: a loop that repeatedly `get`s the current tail completes normally — `get(tail) in a loop: no exception, visited=3`. This is what makes the bug intermittent: whether it fires depends on which key is at the tail when the loop starts, so a test reading one hot key passes indefinitely.

</details>

**Q3.** A colleague guards an access-order LRU with a `ReadWriteLock`, taking the read lock in `get`. What is wrong, and what is the correct minimal fix?

<details><summary>Answer</summary>

`get` is not a read. It writes `head`, `tail`, up to six `before`/`after` fields and `modCount`, none of them `volatile` or guarded. Under a shared read lock, two concurrent `get`s can lose a link (entries vanish from iteration but remain findable by `get`), build a cycle in the `after` chain (iteration spins at 100% CPU), or leave `head` stale so eviction removes the wrong key. Doing it correctly means taking the *write* lock in `get`, at which point the read lock is dead code and the whole `ReadWriteLock` is strictly slower than a plain monitor. Minimal correct fix: `Collections.synchronizedMap(new LruCache<>(n))`, plus your own `synchronized (map) { ... }` around any iteration, because the wrapper only locks individual calls.

</details>

**Q4.** Why is the single-threaded `ConcurrentModificationException` better evidence of thread-unsafety than a two-thread corruption harness?

<details><summary>Answer</summary>

Because it is deterministic and it isolates the claim. It proves from real output that `get` increments `modCount`, and `modCount` is incremented by the same unguarded method — `afterNodeAccess` — that performs the six link writes. A race harness is scheduling-dependent: a passing run proves nothing at all, and a failing run proves only that this machine's scheduler cooperated on this occasion. If you do run one, report what you observed rather than what you expected, and label it an anecdote.

</details>

**Q5.** Is it safe for several threads to `get` concurrently from an insertion-ordered `LinkedHashMap`?

<details><summary>Answer</summary>

Yes, under the same two conditions as a `HashMap`: nobody is writing, and the map was safely published (assigned to a `final` or `volatile` field, or handed over through an immutable wrapper, before the readers could see it). With `accessOrder = false`, `get` is `getNode` plus `return e.value` — the `if (accessOrder)` branch is not taken, so no field of the map is written. This is a genuine property, and it is the main engineering argument for choosing a FIFO cache over an LRU when the workload does not need recency.

</details>

**Q6.** Distinguish LRU from FIFO in `LinkedHashMap` terms, and name a workload that actively wants FIFO.

<details><summary>Answer</summary>

LRU: `accessOrder = true`, so `get` relinks the accessed node to the tail and `head` is the least recently *accessed* entry. FIFO: `accessOrder = false`, so the guard at line 339 fails, `get` relinks nothing, and `head` is the least recently *inserted* surviving entry. `removeEldestEntry` and `afterNodeInsertion` are identical in both. FIFO wants a workload with bounded *staleness* rather than a bounded working set — a stream de-duplication window, a replay-attack nonce cache, an error-signature log filter — where each entry should live for exactly *N* subsequent insertions regardless of read traffic. It also makes `get` a real read, which is the only way to share a `LinkedHashMap` cache across reader threads with no lock.

</details>

**Q7.** Why does the fail-fast check not live in `hasNext()`?

<details><summary>Answer</summary>

Design, and it has a visible consequence. `hasNext()` is `return next != null;` — nothing more (line 1003). The `modCount != expectedModCount` comparison is the first statement of `nextNode()`. So a `while (it.hasNext())` loop that mutates the map in its body does not fail at the loop condition; it fails on the following `it.next()`. Practically: you cannot add a defensive `hasNext()` call to detect the problem early, and the stack trace always points at `next()` even when the offending `get` is several lines above it.

</details>

**Q8.** Did Java 21 change anything about the concurrency hazard on the read path?

<details><summary>Answer</summary>

No. `get`'s `if (accessOrder) afterNodeAccess(e);` is identical to JDK 8's (line 438 vs 534; only `getNode(hash(key), key)` → `getNode(key)` differs). `afterNodeAccess` still ends `++modCount`, and its guard gained only a `putMode` term that reduces to the JDK 8 condition whenever no `putFirst`/`putLast` is in flight. `nextNode()`'s `modCount` check is byte-identical. The one real change is that JDK 21's `LinkedHashIterator` has a fourth field, `boolean reversed`, and a `LinkedHashIterator(boolean)` constructor, added for `SequencedMap`'s reversed views — JDK 8 (line 701) has neither. Java 21 gave the iterator a direction, not a lock.

</details>

---

**Leaves covered:** 3.7.11, 3.7.12 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — the eviction cycle (D-102, frames a–d) is embedded in [01b-internals-b-lru-and-sequenced.md](01b-internals-b-lru-and-sequenced.md)
**Target version:** Java 21 LTS
**Lines:** 353
