# 02 Java Collections — Concurrent collections — INTERNALS (§3.14.1–3.14.6 thread safety and the synchronized wrappers)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/04c-internals-mutators-serialization-and-views.md](../immutable-collections/04c-internals-mutators-serialization-and-views.md) · Next: [concurrent-collections/02-internals-chm-a.md](02-internals-chm-a.md)

---

## 0. The `Collections.synchronizedX` family

Every general-purpose collection in `java.util` (`ArrayList`, `HashMap`, `HashSet`, `TreeMap`, ...) is documented as **not thread-safe**. `Collections` offers one cheap way to bolt on safety: wrap the collection in a class that puts a single lock around every method.

| Factory | Returns | Backing field(s) | Extra behaviour |
|---|---|---|---|
| `Collections.synchronizedCollection(c)` | `SynchronizedCollection<E>` | `final Collection<E> c`, `final Object mutex` | base of the family |
| `Collections.synchronizedSet(s)` | `SynchronizedSet<E> extends SynchronizedCollection<E>` | inherits `c`/`mutex` | adds `equals`/`hashCode` under the lock |
| `Collections.synchronizedSortedSet(s)` | `SynchronizedSortedSet<E>` | adds `SortedSet<E> ss` | `first()`, `last()`, `headSet()` etc. wrapped |
| `Collections.synchronizedList(list)` | `SynchronizedRandomAccessList<E>` if `list instanceof RandomAccess`, else `SynchronizedList<E>` | adds `final List<E> list` | index ops wrapped; `subList` propagates the mutex |
| `Collections.synchronizedMap(m)` | `SynchronizedMap<K,V>` | `final Map<K,V> m`, `final Object mutex` | caches `keySet`/`entrySet`/`values` views |
| `Collections.synchronizedSortedMap(m)` | `SynchronizedSortedMap<K,V>` | adds `SortedMap<K,V> sm` | `subMap`/`headMap`/`tailMap` propagate the mutex |
| `Collections.synchronizedNavigableMap(m)` | `SynchronizedNavigableMap<K,V>` | adds `NavigableMap<K,V> nm` | `navigableKeySet`, `descendingMap`, ... propagate the mutex |

All of these live in `Collections.java` as package-private static nested classes. None of them is a distinct public type — the public API only ever hands you the interface (`List<E>`, `Map<K,V>`, ...), so you cannot tell by type alone whether a collection is synchronized.

---

## 1. What "not thread-safe" actually costs (§3.14.1)

**Mental model.** An unsynchronized `ArrayList` or `HashMap` is a plain Java object with plain fields (`elementData`, `size`, `table`, `modCount`, ...). Nothing about "not thread-safe" is exotic or JVM-magic — it means: two threads can read and write those fields without any ordering guarantee between them, and several of the mutating operations are not single machine instructions. Concurrent misuse produces four distinct failure shapes, not one generic "corruption."

**Why this matters, and why the old cop-out ("it usually works") is dangerous.** A single-threaded program never observes the absence of synchronization — the JVM memory model, cache lines, and instruction reordering only become visible to *other threads*. So the entire class of bug is invisible in the code you write and the tests you run single-threaded, and it stays invisible under low contention. It costs nothing until the one week traffic doubles.

**When to reach for a synchronized wrapper vs. `ConcurrentHashMap`/`CopyOnWriteArrayList`.** Covered in file 02 of this set — this file only establishes *why* the plain collections need help at all.

**How it works — deriving each failure mode from the unguarded operations, not from folklore:**

1. **Lost update.** `ArrayList.add(E e)` is, in source, `elementData[size] = e; size++;` guarded by a capacity check — two separate field reads/writes, not one atomic operation. If thread A and thread B both read `size == 5`, both write their element to index 5, and both then write `size = 6`, one element is silently overwritten and `size` undercounts by one. This is a **read-modify-write race on the `size` field**, not a JIT bug — it is exactly what "two non-atomic statements, no lock" always does.
2. **Torn state.** `HashMap.resize()` allocates a new bucket array and re-links every node into it *before* publishing the new array to the `table` field. If a second thread calls `get(key)` while resize is mid-flight, it can observe a `table` reference that has already been swapped but a bucket chain that is only partially relinked — a torn view where some entries have moved and others have not, from the reader's perspective, not because any single write itself is non-atomic.
3. **Infinite loop.** In the Java 7 `HashMap`, `resize()`'s `transfer()` method rebuilds each bucket by **head-insertion**, reversing the chain's order. Two threads racing through `transfer()` concurrently can each partially reverse the same source bucket and hand each other's half-built chains back and forth, producing a node whose `next` pointer points to a node earlier in the same chain — a cycle. A subsequent single-threaded `get()` on that bucket then loops forever. Java 8+ replaced head-insertion with **tail-insertion during resize** specifically to remove this failure mode from `HashMap`, but it never made `HashMap` thread-safe — it only removed one specific symptom.
4. **Visibility failure.** Even where no field is torn and no update is lost, there is no **happens-before edge** between an unguarded write on thread A and a subsequent unguarded read on thread B. Per the JLS's memory model, without a `synchronized` block, a `volatile` field, or another such edge, the reader is not guaranteed to ever see the writer's value — it may keep reading a JIT-cached stale value indefinitely, or see it after an arbitrary delay. This is a *pure ordering/caching* problem, independent of 1–3 above; it can happen even for a single `boolean done` field.

**Unverified — deliberately not demonstrated.** None of the four above is shown as a running harness in this file. A race condition that depends on interleaving timing is fundamentally not something a fixed transcript can prove: run the racy code once, get lucky, and it prints clean output — which would make a reader conclude the opposite of the truth. A harness that *does* eventually trip one of these needs many iterations under real thread contention (tens of thousands of `put`/`get` calls across multiple threads, and even then success is probabilistic and JIT/CPU-dependent), and a single clean run afterward proves nothing — it only means the race did not fire *this time*. The correct proof here is the one given above: derive the failure mode mechanically from the unguarded fields and operations in the source, which is deterministic even though the failure's *manifestation* is not.

> **Definition.** "Not thread-safe" means the class's fields can be read and written by multiple threads with no atomicity guarantee on multi-step operations and no happens-before edge between threads — producing lost updates, torn reads, corrupted internal structures, or invisible writes, none of which are guaranteed to appear on any given run.

---

## 2. Unsafe publication (§3.14.2)

**Supporting fact — mechanism.** "Unsafe publication" is the narrower case where a collection is built to completion on one thread, then handed to another thread (through a field, a queue, a static, whatever) *without* a mechanism that establishes a happens-before edge — no `final` field set in the constructor, no `volatile`, no lock, no `Thread.start()`/`join()` boundary, no concurrent-collection publish. Building the object safely on thread A does not, by itself, guarantee thread B sees the fully-built state; B may see a partially-initialized object (default field values interleaved with real ones) or a fully built object but through a stale cached reference.

**Gotcha.** This is why "I built the whole `HashMap` before starting the worker threads" is not automatically safe — if the reference is published through a plain (non-`volatile`, non-`final`) field and the worker threads were *already running* and polling that field, there is no ordering guarantee they see the fully-constructed map rather than a torn one. Passing the reference through `Thread`'s constructor before `start()`, through a `final` field, through a properly locked structure, or through a `java.util.concurrent` queue/executor *does* establish the edge.

**Unverified — deliberately not demonstrated**, for the identical reason as §1: unsafe publication is a timing-dependent visibility bug. A demo that "happens to work" on one JVM/CPU proves nothing about correctness; the fix is to publish through a construct with a documented happens-before guarantee, not to test until failures stop appearing.

> **Definition.** Unsafe publication is handing a reference to a mutable object across threads through a channel that provides no happens-before guarantee, leaving the receiving thread free to observe a partially- or never-updated view of that object.

---

## 3. `Collections.synchronizedX`: one mutex, every method wrapped (§3.14.3)

**Mental model.** Picture the backing collection sitting inside a single-room house with exactly one door. The wrapper is that door: every public method acquires the same lock (`mutex`), calls straight through to the backing collection, and releases the lock. There is one door for the whole house — every method serializes through it, so calls never interleave *inside* a single wrapped method.

**Why it exists.** Before `java.util.concurrent` (pre-Java 5), the only concurrent collection available was `Hashtable`/`Vector`, which hardcode `synchronized` on every method. `Collections.synchronizedX` generalized that pattern to *any* collection: instead of a hand-written thread-safe class per collection type, one small wrapper class retrofits mutual exclusion onto whatever you already have (`ArrayList`, `HashMap`, `TreeMap`, ...).

**When to reach for it, and when not.** Reach for it when you have legacy code built around a plain collection and need "good enough" mutual exclusion with minimal code change, or when you specifically need `null` keys/values and total ordering under a lock (things `ConcurrentHashMap` restricts or handles differently). Do **not** reach for it under real read/write contention: every operation — including reads — takes the *same* single lock, so `synchronizedMap` has zero read parallelism, unlike `ConcurrentHashMap`'s lock striping (file 02 of this set). Do not reach for it either for a workload dominated by iteration under concurrent mutation — `CopyOnWriteArrayList` (file 03) is the better sibling there.

**How it works — source walk, `Collections.java` (JDK 21):**

`SynchronizedCollection<E>` (line 2281) declares:

```
final Collection<E> c;  // Backing Collection
final Object mutex;     // Object on which to synchronize
```

Two constructors (lines 2290–2298):

```
SynchronizedCollection(Collection<E> c) {
    this.c = Objects.requireNonNull(c);
    mutex = this;
}

SynchronizedCollection(Collection<E> c, Object mutex) {
    this.c = Objects.requireNonNull(c);
    this.mutex = Objects.requireNonNull(mutex);
}
```

The public factory `Collections.synchronizedCollection(c)` (line 2270) always uses the first form, so `mutex == this` — you lock on the wrapper object itself. The package-private overload taking an explicit `mutex` (line 2274) exists purely so that **views derived from a synchronized collection can share the outer lock** instead of getting their own — see §6 below, which is exactly what closes leaf 3.14.6.

Every ordinary mutating/reading method follows the same shape (lines 2300–2347):

```
public int size() {
    synchronized (mutex) {return c.size();}
}
...
public boolean add(E e) {
    synchronized (mutex) {return c.add(e);}
}
```

`SynchronizedList` (line 2690) adds the same treatment for index-based operations (`get`, `set`, `add(int,E)`, `remove(int)`, `indexOf`, `addAll(int,Collection)`, `replaceAll`, `sort`) at lines 2717–2763. `SynchronizedMap` (line 2859) does the same for `get`/`put`/`remove`/`putAll`/`clear` and the Java 8 default methods `getOrDefault`, `compute*`, `merge`, `replace*`, `putIfAbsent` (lines 2879–2996) — every one of those newer default methods is explicitly overridden and wrapped, so `computeIfAbsent` is just as mutex-protected as `put`.

`Collections.synchronizedList` picks the concrete wrapper class based on the backing list's capability (lines 2675–2679):

```
public static <T> List<T> synchronizedList(List<T> list) {
    return (list instanceof RandomAccess ?
            new SynchronizedRandomAccessList<>(list) :
            new SynchronizedList<>(list));
}
```

`SynchronizedRandomAccessList` (line 2788) only exists so that a `RandomAccess` marker survives the wrap — `Collections.binarySearch` and similar utilities branch on `instanceof RandomAccess` to pick an algorithm, and without this the wrapper would silently downgrade an `ArrayList` to linked-list-style iteration for those utilities. `subList` on `SynchronizedList` (lines 2749–2754) and on `SynchronizedRandomAccessList` (lines 2800–2805) both construct their returned sublist with the **same `mutex`** passed through — a sublist view shares the parent's lock, so locking either one excludes the other.

> **Definition.** `Collections.synchronizedX` is a thin decorator that wraps every interface method of a backing collection in `synchronized (mutex) { ... }`, where `mutex` defaults to the wrapper instance itself unless an explicit shared lock object is supplied through the package-private overload.

---

## 4. Synchronized wrappers do not make iteration safe (§3.14.4)

**Mental model.** The single-door-house picture from §3 has one exception nobody notices until it bites: the *iterator* is not a room inside the house — it's a key that was copied and handed out through a window before the door closed. Once you have that key, walking through the rooms with it never touches the door's lock again.

**Why it exists (this way).** `Iterator.hasNext()`/`next()` are called in a hot loop, once per element. If `synchronized (mutex)` wrapped the returned iterator itself, you'd re-acquire the same lock on every single `next()` call inside the loop body — that would neither be atomic across the whole iteration (another thread could still interleave a mutation *between* two `next()` calls) nor free of overhead. So the JDK does not try: it hands back the **raw backing iterator**, unguarded, and documents that the *caller* must wrap the whole loop in one `synchronized` block instead.

**Source walk — the mechanical proof, `Collections.java` (JDK 21), `SynchronizedCollection.iterator()`, line 2319:**

```
public Iterator<E> iterator() {
    return c.iterator(); // Must be manually synched by user!
}
```

No `synchronized` keyword, no wrapping — `c.iterator()` is the plain, unsynchronized iterator of the backing collection, returned straight through. The same pattern repeats for every other traversal entry point in the same class: `spliterator()` (line 2358), `stream()` (line 2362), and `parallelStream()` (line 2366) all carry the identical `// Must be manually synched by user!` comment and return the raw delegate's traversal object with zero synchronization. `SynchronizedList.listIterator()` and `listIterator(int)` (lines 2741–2747) do the same for list-specific iteration. This is the entire mechanical reason 3.14.4 is true — it is a **deliberate design choice visible in the source**, not an oversight, and the class-level javadoc for `synchronizedCollection` states the required pattern explicitly:

```
Collection c = Collections.synchronizedCollection(myCollection);
    ...
synchronized (c) {
    Iterator i = c.iterator(); // Must be in the synchronized block
    while (i.hasNext())
        foo(i.next());
}
```

**A deterministic, single-threaded proof — no race required.** Because the returned iterator is exactly the backing `ArrayList`'s ordinary iterator, mutating the *same* wrapper through its own `add`/`remove` methods while iterating trips the ordinary single-threaded `ConcurrentModificationException` — no second thread needed, because the wrapper's own mutating call bumps `modCount` underneath the live iterator:

```java
import java.util.*;

public class SynchronizedIterationTrap {
    public static void main(String[] args) {
        List<Integer> list = Collections.synchronizedList(new ArrayList<>(List.of(1, 2, 3, 4)));
        try {
            for (Integer i : list) {
                if (i == 2) {
                    list.remove(i); // mutating through the SAME wrapper mid-iteration
                }
            }
            System.out.println("no exception (should not happen)");
        } catch (ConcurrentModificationException e) {
            System.out.println("caught: " + e);
        }
    }
}
```

Run against JDK 21 (`javac`/`java`), this prints exactly:

```
caught: java.util.ConcurrentModificationException
```

This is deterministic — it needs no thread, no timing, no luck — because `list.remove(i)` inside the loop takes the wrapper's mutex, calls straight through to the backing `ArrayList.remove`, which increments `modCount`, and the *raw* iterator's `next()` compares `modCount` against its cached `expectedModCount` and throws. The bug this proves is real is stronger, not weaker, than the single-threaded case: with two threads both holding no lock during iteration, the same `modCount` check fires *nondeterministically* (sometimes it catches the interleaving, sometimes the two operations happen to not overlap in a way that trips it, and sometimes on non-`ArrayList` backings you get silent corruption instead of a clean exception) — which is exactly why "wrap the whole loop, not just the calls" is the rule, not "add try/catch around next()".

**Pitfall:** Believing that because `get`, `add`, and `remove` are individually synchronized, a `for` loop over the wrapper is automatically thread-safe. It is not — the loop's `iterator()` call returns before any lock is held across the loop body, so another thread's `add`/`remove` between two `next()` calls under-locks exactly like the demo above, except concurrently and nondeterministically. Fix: `synchronized (wrapper) { for (var x : wrapper) { ... } }`, taking the lock for the *whole* traversal, not per-element.

**Insight:** The javadoc's advice and the source's behavior are two views of the same fact — `iterator()` cannot be made safe by locking inside it without breaking the atomicity the caller actually needs (freedom from concurrent mutation for the *entire* traversal), so the JDK pushes the lock scope up to the caller instead of trying (and failing) to solve it inside the method.

**Interview:** "Does wrapping a `HashMap` in `Collections.synchronizedMap` make `for (var e : map.entrySet())` thread-safe?" — No: `entrySet()` returns a view whose `iterator()` bypasses the mutex entirely (source: `SynchronizedCollection.iterator()`, line 2319); the whole loop must sit inside `synchronized (map) { ... }`.

> **Definition.** A synchronized wrapper's `iterator()`, `listIterator()`, `spliterator()`, `stream()`, and `parallelStream()` all return the backing collection's raw, unsynchronized traversal object — the mutex only protects individual method calls, never a caller-controlled traversal, so the entire loop must be placed inside an explicit `synchronized (wrapper)` block.

---

## 5. Synchronized wrappers do not make compound actions atomic (§3.14.5)

**Supporting fact — mechanism.** Every *single* method on a synchronized wrapper is atomic with respect to every other single method — `containsKey` cannot interleave with the middle of a `put`. But a **sequence of two separate calls** — `if (!m.containsKey(k)) m.put(k, v);` — is two separate lock acquisitions: `containsKey` takes the mutex, checks, and *releases* the mutex before `put` ever tries to acquire it. Between those two calls, any other thread is free to acquire the same mutex and run its own `put(k, someOtherValue)`, so the check performed by `containsKey` can be stale by the time `put` runs. This is the classic **check-then-act race**, and no amount of per-method locking removes it — only holding the lock across the *entire* sequence does.

**Gotcha.** This is provable straight from §3's source: `SynchronizedMap.containsKey` (line 2886) and `SynchronizedMap.put` (line 2896) are each wrapped in their *own* `synchronized (mutex) { ... }` block — two separate `synchronized` statements, not one. Nothing in the wrapper's source ties them together; the atomicity boundary is per-call, and the caller who writes `if (!m.containsKey(k)) m.put(k, v)` is implicitly assuming a boundary the wrapper never promised.

**The correct, deterministic fix — provable without any race, by holding the *same* mutex the wrapper already exposes:**

```java
import java.util.*;

public class CompoundActionFix {
    public static void main(String[] args) {
        Map<String, Integer> m = Collections.synchronizedMap(new HashMap<>());
        // Correct: the wrapper's own instance IS its mutex (Collections.synchronizedMap
        // uses the single-arg SynchronizedCollection/-Map constructor, mutex = this),
        // so synchronizing on the wrapper reference excludes every other call to it,
        // including calls made from inside its own containsKey/put.
        synchronized (m) {
            if (!m.containsKey("k")) {
                m.put("k", 1);
            }
        }
        System.out.println("k=" + m.get("k"));
    }
}
```

This prints `k=1` deterministically on every run — not because the race can't happen (it demonstrably can, on the unguarded version, under real thread contention), but because holding `m`'s own mutex across the whole `if`/`put` sequence means no other thread can acquire that same mutex to run its own `put` in between, by construction of the wrapper in §3. Provable directly from the fact that `Collections.synchronizedMap(m)` sets `mutex = this` (§3, `SynchronizedMap` constructor) — synchronizing on the returned reference is synchronizing on the exact object every wrapped method locks internally.

**Unverified — the failure itself is not shown racing.** Actually observing the lost-update outcome of the *unguarded* `if (!m.containsKey(k)) m.put(k, v)` requires two threads racing on a shared key, and — per the honesty rule in §1 — a lucky clean run would prove nothing. What is provable deterministically is (a) the two separate lock acquisitions in the source, and (b) that the documented fix removes the gap by construction, both shown above.

**Interview:** "I wrapped my `HashMap` with `Collections.synchronizedMap` — is `putIfAbsent` still necessary, or can I just check-then-put?" — `putIfAbsent` (or an explicit `synchronized (map) { ... }` around the whole sequence) is necessary; a bare `containsKey` + `put` is two independent lock acquisitions with a window between them, regardless of the wrapper.

> **Definition.** A synchronized wrapper guarantees atomicity per method call, never across a sequence of calls — any check-then-act idiom built from two or more wrapper calls needs its own explicit `synchronized (wrapper) { ... }` block (or a single atomic method such as `putIfAbsent`/`computeIfAbsent`) to be race-free.

---

## 6. The `synchronizedMap(...).keySet()` view mutex question (§3.14.6)

**Supporting fact — mechanism, answered directly from source rather than folklore.** `SynchronizedMap` (line 2859) caches its three collection views in transient fields (line 2908–2910: `keySet`, `entrySet`, `values`) and constructs each one, on first access, by passing the **same outer `mutex`** through to the view's own wrapper constructor:

```
public Set<K> keySet() {
    synchronized (mutex) {
        if (keySet==null)
            keySet = new SynchronizedSet<>(m.keySet(), mutex);
        return keySet;
    }
}

public Set<Map.Entry<K,V>> entrySet() {
    synchronized (mutex) {
        if (entrySet==null)
            entrySet = new SynchronizedSet<>(m.entrySet(), mutex);
        return entrySet;
    }
}

public Collection<V> values() {
    synchronized (mutex) {
        if (values==null)
            values = new SynchronizedCollection<>(m.values(), mutex);
        return values;
    }
}
```

(`Collections.java`, JDK 21, lines 2912–2934.) All three constructors go through the package-private `SynchronizedSet(Set, Object mutex)` / `SynchronizedCollection(Collection, Object mutex)` overload from §3 — the overload whose entire purpose, as noted there, is to let a derived view share its parent's lock instead of getting `mutex = this` of its own. `SynchronizedSortedMap`/`SynchronizedNavigableMap` (lines 3056–3265) follow the identical pattern for `navigableKeySet()`, `descendingKeySet()`, `descendingMap()`, and every `subMap`/`headMap`/`tailMap` variant — every one of those `new SynchronizedXxx<>(..., mutex)` calls threads the *same* mutex object through.

**Version diff — checked directly, JDK 8u202 (`/tmp/jc53src8/java/util/Collections.java`) vs. JDK 21.** JDK 8's `SynchronizedMap.keySet()`/`entrySet()`/`values()` (lines 2604–2623 of that source tree) construct their views with the identical shape — `new SynchronizedSet<>(m.keySet(), mutex)`, `new SynchronizedSet<>(m.entrySet(), mutex)`, `new SynchronizedCollection<>(m.values(), mutex)` — passing the same shared `mutex`, not a fresh one. There is no divergence between JDK 8 and JDK 21 on this point.

**Finding — leaf 3.14.6 is wrong as written.** The syllabus leaf claims the `keySet()` view "is *not* synchronized on the same mutex in all JDK versions." Both JDK 8u202 and JDK 21 pass the outer mutex through to every derived view, with no version gap in the `Collections.synchronizedX` family itself. The class javadoc for `synchronizedMap` (lines 2828–2842) reinforces this by explicitly telling callers to synchronize on `m`, not on the view — `synchronized (m) { ... }`, "Synchronizing on m, not s!" — which only makes sense as advice if the view *does* answer to the same lock as a shared resource; if it had its own independent lock, synchronizing on `m` would not protect `s` at all, and the advice would be actively wrong. The "not in all JDK versions" caveat does not hold up against either source tree checked here; treat it as folklore that predates or misremembers a different collection family (`Hashtable.keySet()` predates the generic wrapper mechanism and has its own long history, which is a plausible source of the confusion, but that is a different code path from `Collections.synchronizedMap`).

**Pitfall:** Assuming that because `keySet()` "is just a view," it must be a plain unsynchronized `Set` requiring its *own* separate lock. It is not — it is a `SynchronizedSet` sharing the parent map's exact mutex object; a second, independent lock on the view would not even compile against the constructor shown above, since the view is never given one.

**Interview:** "If I call `synchronizedMap(m).keySet()`, do I need to synchronize on the keySet or on the map to iterate it safely?" — Either works because they are the same lock object (source: `SynchronizedMap.keySet()`, `Collections.java` line 2915, passing the same `mutex` field the map itself locks on), but the JDK's own javadoc convention is to synchronize on the map.

> **Definition.** Every collection view (`keySet`, `entrySet`, `values`, `navigableKeySet`, `descendingMap`, `subMap`/`headMap`/`tailMap`) returned by a `Collections.synchronizedX` map shares the exact same mutex object as its parent, in both JDK 8 and JDK 21 — locking either the map or the view excludes the other.

---

## Pitfalls

### Assuming per-method locking makes a `for` loop over a synchronized wrapper safe

**Wrong**
```java
List<Integer> list = Collections.synchronizedList(new ArrayList<>(List.of(1, 2, 3)));
for (Integer i : list) {          // iterator() returns the RAW backing iterator
    System.out.println(i);        // safe from a torn read of a single element,
}                                  // but not safe from another thread's add/remove mid-loop
```

**Right**
```java
List<Integer> list = Collections.synchronizedList(new ArrayList<>(List.of(1, 2, 3)));
synchronized (list) {
    for (Integer i : list) {
        System.out.println(i);
    }
}
```

**Why people believe it:** every other method on the wrapper — `get`, `add`, `size` — really is individually synchronized, so it is a reasonable (but wrong) inductive leap to assume the object returned by `iterator()` inherits the same protection, when the source (`Collections.java` line 2319) shows it is handed back completely raw.

### Assuming `containsKey` + `put` on a synchronized map is atomic because both calls are synchronized

**Wrong**
```java
Map<String, Integer> m = Collections.synchronizedMap(new HashMap<>());
if (!m.containsKey("k")) {   // lock acquired, checked, RELEASED
    m.put("k", 1);           // separate lock acquisition — window between the two calls
}
```

**Right**
```java
Map<String, Integer> m = Collections.synchronizedMap(new HashMap<>());
m.putIfAbsent("k", 1);   // single wrapped call, atomic by construction
// or, for a multi-step compound action putIfAbsent can't express:
synchronized (m) {
    if (!m.containsKey("k")) {
        m.put("k", 1);
    }
}
```

**Why people believe it:** "every method is synchronized" is true and gets generalized incorrectly to "every *sequence* of methods is synchronized" — but each `synchronized (mutex) { ... }` block in the source (`SynchronizedMap.containsKey`, line 2886; `SynchronizedMap.put`, line 2896) is its own independent critical section.

---

## Cheat sheet

| Claim | True? | Source anchor |
|---|---|---|
| Wrapper adds one mutex, wraps every interface method | Yes | `SynchronizedCollection`, `Collections.java` 2281–2373 |
| Default mutex is the wrapper instance itself | Yes | constructor, line 2292 (`mutex = this`) |
| `iterator()`/`spliterator()`/`stream()` are synchronized | **No** | lines 2319, 2358, 2362, 2366 — raw delegate returned |
| Caller must wrap the whole loop in `synchronized (wrapper)` | Yes | class javadoc + iterator source, both above |
| Two synchronized calls in sequence are atomic together | **No** | `containsKey`/`put` are separate `synchronized` blocks, lines 2886, 2896 |
| `putIfAbsent`/`computeIfAbsent` are atomic | Yes | each wrapped in one `synchronized` block, lines 2962–2996 |
| `keySet()`/`entrySet()`/`values()` share the map's mutex | Yes, in both JDK 8 and JDK 21 | lines 2912–2934 (21), 2604–2623 (8) |
| `subList`/`subMap`/`headMap`/`tailMap` share the parent's mutex | Yes | lines 2749–2754, 3228–3264 |
| `RandomAccess` marker survives the wrap | Yes, via `SynchronizedRandomAccessList` | lines 2675–2679, 2788 |
| Lost update / torn state / infinite loop / visibility failure are all one bug | **No** — four distinct mechanisms | §1 |

---

## Self-test

**Q1.** Why does `SynchronizedCollection.iterator()` return `c.iterator()` directly instead of wrapping it in a synchronized iterator class?

<details><summary>Answer</summary>

Because per-call synchronization inside `next()`/`hasNext()` would not give the caller what they actually need — atomicity across the *whole* traversal — while adding lock overhead per element. Another thread could still mutate the collection between two `next()` calls even if each call itself were individually locked. So the JDK pushes the responsibility up: hand back the raw iterator and require the caller to hold the lock for the entire loop (`synchronized (wrapper) { for (...) {...} }`), which is the only scope that actually delivers the atomicity guarantee.

</details>

**Q2.** A synchronized `ArrayList` wrapper throws `ConcurrentModificationException` when you call `list.remove(x)` from inside a `for-each` over the same list, with no second thread involved. Does this prove the wrapper is broken?

<details><summary>Answer</summary>

No — it proves the iterator is unsynchronized and unprotected, which is expected and documented (§3.14.4), not a defect. The exception is the ordinary single-threaded `modCount` check firing because the wrapper's `remove` call passes straight through to the backing `ArrayList`'s `remove`, which bumps `modCount` under the live iterator. The real, harder-to-catch danger is a second thread doing the same mutation concurrently, which does not reliably throw at all — it can just as easily corrupt state silently.

</details>

**Q3.** Why does `if (!m.containsKey(k)) m.put(k, v)` on a `Collections.synchronizedMap` still race, given that both `containsKey` and `put` are synchronized?

<details><summary>Answer</summary>

Because each method's `synchronized (mutex) { ... }` block is its own separate critical section — `containsKey` acquires the mutex, checks, and releases it before `put` acquires the mutex again. Between those two acquisitions, any other thread holding no reference to an in-progress operation is free to run its own fully synchronized `put` on the same key. The fix is to hold one lock across the entire sequence (`synchronized (m) { ... }`) or use a single atomic method (`putIfAbsent`).

</details>

**Q4.** Does `Collections.synchronizedMap(m).keySet()` need its own separate `synchronized` block distinct from `synchronized (m)`?

<details><summary>Answer</summary>

No. `SynchronizedMap.keySet()` constructs its cached view with `new SynchronizedSet<>(m.keySet(), mutex)`, passing the exact same `mutex` field the outer map locks on (`Collections.java` line 2915, confirmed identical in JDK 8 at line 2607). Synchronizing on the map and synchronizing on the keySet view are synchronizing on the same object.

</details>

**Q5.** What are the four distinct ways an unsynchronized `HashMap`/`ArrayList` can misbehave under concurrent access, and which one did Java 8 specifically fix (without making the class thread-safe)?

<details><summary>Answer</summary>

Lost update (non-atomic read-modify-write, e.g. `ArrayList.size++`), torn state (a reader observing a partially-published internal array during resize), infinite loop (the Java 7 `HashMap` head-insertion resize cycle creating a circular bucket chain), and visibility failure (no happens-before edge, so a writer's update may never become visible to a reader). Java 8 changed `HashMap`'s resize to tail-insertion, which removes the infinite-loop failure mode specifically — it did not address lost updates, torn state, or visibility, and `HashMap` remains just as unsynchronized as before.

</details>

**Q6.** Why is `Collections.synchronizedList(list)` sometimes a `SynchronizedRandomAccessList` and sometimes a plain `SynchronizedList` — what would break if it always returned the plain one?

<details><summary>Answer</summary>

`Collections.synchronizedList` checks `list instanceof RandomAccess` and picks `SynchronizedRandomAccessList` when true (`Collections.java` lines 2675–2679), purely so the `RandomAccess` marker interface survives the wrap. If it always returned the plain `SynchronizedList`, an `ArrayList` wrapped this way would stop being recognized as `RandomAccess` by utilities like `Collections.binarySearch`, which branch on that marker to choose an O(log n) index-based algorithm instead of an O(n) iterator-walk algorithm — silently degrading performance for wrapped random-access lists.

</details>

**Q7.** A caller writes `synchronized (list.subList(0, 5)) { ... }` on a `Collections.synchronizedList`-wrapped list, believing this excludes concurrent modification of the parent list. Is that correct?

<details><summary>Answer</summary>

Yes, because `SynchronizedList.subList()` (and `SynchronizedRandomAccessList.subList()`) construct the returned sublist wrapper with the exact same `mutex` object as the parent (`Collections.java` lines 2749–2754, 2800–2805) rather than a fresh lock — so synchronizing on the sublist view and synchronizing on the parent list exclude each other, the same sharing pattern as the map views in §6.

</details>

**Q8.** Why does this file not include a multi-threaded harness that demonstrates the lost-update or visibility-failure bugs from §1 actually firing?

<details><summary>Answer</summary>

Because a race condition's manifestation is inherently non-deterministic: a harness run that happens to trip the bug proves it exists, but a harness run that does not trip it proves nothing — the bug can still be there, just not observed on that run, on that JVM, on that CPU, under that scheduling. Publishing a "successful" racy transcript risks a reader re-running it once, seeing clean output, and concluding the danger is overstated. The reliable proof is instead derived mechanically from the unguarded fields and operations in the source (§1), which does not depend on timing at all.

</details>

---

## Open questions

1. Leaf 3.14.6's "not synchronized on the same mutex in all JDK versions" claim did not hold against JDK 8u202 or JDK 21 — both pass the identical mutex through every derived view. Settling whether *any* JDK version ever diverged (pre-Java-5 `Collections` predates generics and the `mutex`-overload pattern entirely) would require pulling JDK 1.4 or earlier source, which was not available in this environment; absent that, treat the "not all versions" caveat as unconfirmed folklore rather than a documented historical fact.

---

**Leaves covered:** 3.14.1, 3.14.2, 3.14.3, 3.14.4, 3.14.5, 3.14.6 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 415
