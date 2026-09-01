# 05 Multithreading and Concurrency — A copy-on-write list and a mini CHM — BUILD IT (§4.4, leaves 4.4.9–4.4.10)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [A striped counter, measured](04d-striped-counter-and-measurement.md) · Next: [The non-blocking consolidated diff](04f-non-blocking-consolidated-diff.md)

## 4.4.9 A copy-on-write list from scratch — `[BUILD]`

### Mental model

`NotificationService` keeps a list of listeners to fan a `SETTLEMENT_COMPLETE` event out to —
registered rarely (a handful of times at startup, occasionally at runtime), read constantly (once
per settlement, 3,400/sec at burst). A copy-on-write list treats the backing array as **immutable
once published**: every mutation builds a brand-new array with the change baked in, then swaps a
single reference to point readers at it. Readers never see a half-built array and never take a lock
— they just read whichever array reference was current when they looked, the way a photograph taken
at 3,400 frames a second still shows a clean, unblurred building even while renovation crews are
inside it.

### Why it exists

A `synchronized ArrayList` or a `ReentrantReadWriteLock`-guarded list makes every read acquire a
lock, which is wasted work when reads vastly outnumber writes and writes are rare. Copy-on-write
inverts the cost: reads are lock-free and see a stable snapshot for the whole iteration, writes pay
an O(n) copy plus a lock, and that trade only pays off when writes really are rare — which is
exactly `NotificationService`'s registration pattern.

### When to reach for it, and when not

Reach for it when the read:write ratio is extreme (registries, listener lists, routing tables) and
iteration needs a torn-free snapshot without a lock. Do not reach for it when writes are frequent —
2.8M stake reservations/day into a `CopyOnWriteArrayList` would mean 2.8M full-array copies, an O(n)
cost per write turning into O(n²) total work as the list grows, which is precisely the disaster
scenario this domain's own numbers are built to illustrate. `ConcurrentHashMap`-style structures or
plain `synchronized` collections win once writes are routine.

### How it works

The single field is `volatile Object[] array`. Every reader takes one plain read of that reference
(the `volatile` gives it a happens-before edge against the write that installed it — Day-3's JMM
material) and iterates the array it got with no further coordination; `size()` and `get(i)` are
just array length and indexing. Every mutator — `add`, `remove`, `set` — acquires a private
`ReentrantLock`, snapshots the current array, builds a new array of the right size with the change
applied, and only then assigns the new array to the `volatile` field, releasing the lock. Because
the swap is a single reference write, a reader either sees the whole old array or the whole new one,
never a mix. The iterator captures the array reference at construction time and never re-reads the
field, so it is immune to `ConcurrentModificationException` by construction — and, as the direct
consequence, its `remove`/`set`/`add` are unsupported: mutating a snapshot the live list has already
moved past would silently do nothing useful.

```java
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Consumer;

/**
 * A copy-on-write list of settlement-event listeners for NotificationService.
 * Registration is rare; delivery iterates once per settled stake (3,400/sec at burst).
 */
public final class CowListenerList<E> implements Iterable<E> {

    private volatile Object[] array = new Object[0];
    private final ReentrantLock mutationLock = new ReentrantLock();

    public int size() {
        return array.length;
    }

    @SuppressWarnings("unchecked")
    public E get(int index) {
        Object[] snapshot = array;
        if (index < 0 || index >= snapshot.length) {
            throw new IndexOutOfBoundsException(
                    "index " + index + " out of bounds for length " + snapshot.length);
        }
        return (E) snapshot[index];
    }

    public boolean add(E listener) {
        mutationLock.lock();
        try {
            Object[] current = array;
            Object[] grown = new Object[current.length + 1];
            System.arraycopy(current, 0, grown, 0, current.length);
            grown[current.length] = listener;
            array = grown; // single volatile write publishes the whole new array atomically
            return true;
        } finally {
            mutationLock.unlock();
        }
    }

    public boolean remove(Object listener) {
        mutationLock.lock();
        try {
            Object[] current = array;
            int index = indexOf(current, listener);
            if (index < 0) {
                return false;
            }
            Object[] shrunk = new Object[current.length - 1];
            System.arraycopy(current, 0, shrunk, 0, index);
            System.arraycopy(current, index + 1, shrunk, index, current.length - index - 1);
            array = shrunk;
            return true;
        } finally {
            mutationLock.unlock();
        }
    }

    private static int indexOf(Object[] elements, Object target) {
        for (int i = 0; i < elements.length; i++) {
            if (elements[i] == null ? target == null : elements[i].equals(target)) {
                return i;
            }
        }
        return -1;
    }

    /** Delivers a settlement event to every registered listener, snapshot-consistent. */
    public void forEachSnapshot(Consumer<? super E> action) {
        for (E listener : this) {
            action.accept(listener);
        }
    }

    @Override
    public Iterator<E> iterator() {
        return new SnapshotIterator(array);
    }

    /**
     * Iterates a fixed array captured at construction time. Structural methods are
     * unsupported by construction: mutating a snapshot the live list has already
     * replaced would silently discard the change.
     */
    private final class SnapshotIterator implements Iterator<E> {
        private final Object[] snapshot;
        private int cursor;

        SnapshotIterator(Object[] snapshot) {
            this.snapshot = snapshot;
        }

        @Override
        public boolean hasNext() {
            return cursor < snapshot.length;
        }

        @Override
        @SuppressWarnings("unchecked")
        public E next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            return (E) snapshot[cursor++];
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException(
                    "snapshot iterator: mutate the list directly, not the iteration in progress");
        }
    }
}
```

**Insight:** the lock in `add`/`remove` protects mutators from each other — two threads registering
listeners at once must not both read the same base array and each publish a version missing the
other's addition — but it never touches readers at all. Readers and writers never contend for
anything; only writer-vs-writer contention exists, and by hypothesis writers are rare.

**Pitfall:** assuming a `CowListenerList` iterator reflects listeners added mid-iteration. It never
does, by design — the iterator pins the array reference it was constructed with, so a listener
registered from inside a callback that is itself firing during `forEachSnapshot` will not be invoked
until the *next* delivery. This is the "weakly consistent" behavior the real `CopyOnWriteArrayList`
javadoc documents explicitly, and it is a feature (no `ConcurrentModificationException`, ever) as
much as a limitation.

> A copy-on-write list makes every write pay for a full-array copy so that every read is lock-free
> and iterates a torn-free snapshot — a trade that only wins when writes are rare and reads are not.

## 4.4.10 A `ConcurrentHashMap`-shaped mini map — `[BUILD]`

### Mental model

`ClientRestrictions` looks up a `ClientId` (one of 2.4M) to a mutable `ClientRestrictionSet` under
heavy concurrent read and write traffic — every deposit, stake and withdrawal check consults it.
The real `ConcurrentHashMap` shape: a power-of-two array of bins, where an **empty** bin is claimed
with a single CAS (cheapest possible path, no lock needed because there is nothing to protect yet),
and a **populated** bin — already a linked chain from a prior insert or a hash collision — is
protected by `synchronized` on that bin's head node only. Two threads touching different bins never
block each other at all; two threads touching the same bin serialize, but only for that one bin,
not the whole map.

### Why it exists

A single `synchronized` around the whole map (`Hashtable`, or a naively wrapped `HashMap`)
serializes every operation regardless of which key is touched — a stake-reservation check on client
A blocks a restriction lookup on client B for no reason. Per-bin locking narrows the blast radius of
contention to "same bin", and CAS-on-empty-bin narrows it further to "nothing to lock at all" for
the common case of inserting into a bin nobody else is touching.

### When to reach for it, and when not

Reach for this shape whenever concurrent readers and writers share a hash table keyed by something
with a good, well-spread hash — exactly `ClientId`'s `UUID`-backed identity. Do not reach for it (or
this teaching version specifically) when you need sorted iteration order (`ConcurrentSkipListMap`),
when the table must never resize under load because resize pauses are unacceptable (a
fixed-capacity table sized up front avoids the resize path entirely), or, for this file's mini
version specifically, when you need `size()` to be either cheap or exact under concurrent
modification — see the honesty note below.

### How it works

The table is a plain `Node<K,V>[]` sized to a power of two so `hash & (table.length - 1)` replaces
an expensive modulo with a mask. `putIfAbsentOrUpdate` computes a spread hash (mixing high and low
bits, the same idea `HashMap`/`ConcurrentHashMap` use, so a poor `hashCode()` does not collapse
every key into one bin), reads the bin via a `VarHandle` **acquire** (never a plain read — this is
the one place a plain volatile-array read is not enough, because array-element access has no
built-in `volatile` semantics the way a `volatile` field does), and then either CASes a brand-new
node into a genuinely empty bin, or falls to `synchronized(firstNode)` to walk/mutate the chain
under a populated bin. `get` never locks at all — it walks the chain reading `volatile` fields end
to end, tolerating a concurrent insert appearing or not appearing depending on timing, which is
exactly the weakly-consistent guarantee `ConcurrentHashMap.get` documents.

```java
import java.lang.invoke.MethodHandles;
import java.lang.invoke.VarHandle;
import java.util.function.BiFunction;

/**
 * A ConcurrentHashMap-shaped map from ClientId to ClientRestrictionSet, sized for
 * roughly 2.4M registered clients. Deliberately omits treeification and cooperative
 * resize — see the honesty note at the end of this section.
 */
public final class MiniConcurrentMap<K, V> {

    static final class Node<K, V> {
        final int hash;
        final K key;
        volatile V value;
        volatile Node<K, V> next;

        Node(int hash, K key, V value, Node<K, V> next) {
            this.hash = hash;
            this.key = key;
            this.value = value;
            this.next = next;
        }
    }

    private volatile Node<K, V>[] table;

    private static final VarHandle ARRAY_HANDLE =
            MethodHandles.arrayElementVarHandle(Node[].class);

    @SuppressWarnings("unchecked")
    public MiniConcurrentMap(int initialCapacityHint) {
        int capacity = Integer.highestOneBit(Math.max(16, initialCapacityHint) - 1) << 1;
        this.table = (Node<K, V>[]) new Node[capacity];
    }

    private static int spread(int h) {
        return (h ^ (h >>> 16)) & 0x7fffffff;
    }

    @SuppressWarnings("unchecked")
    private Node<K, V> tabAt(Node<K, V>[] tab, int i) {
        return (Node<K, V>) ARRAY_HANDLE.getAcquire(tab, i);
    }

    private boolean casTabAt(Node<K, V>[] tab, int i, Node<K, V> expect, Node<K, V> update) {
        return ARRAY_HANDLE.compareAndSet(tab, i, expect, update);
    }

    /** Reads with no locking at all; tolerates a concurrently-in-flight insert either way. */
    public V get(K key) {
        int hash = spread(key.hashCode());
        Node<K, V>[] tab = table;
        Node<K, V> node = tabAt(tab, hash & (tab.length - 1));
        while (node != null) {
            if (node.hash == hash && node.key.equals(key)) {
                return node.value;
            }
            node = node.next;
        }
        return null;
    }

    /**
     * Installs or updates the restriction set for a client. Empty bin: single CAS,
     * no lock. Populated bin: synchronized on the bin's head node, scoped to that
     * bin only — a lookup or update on a different bin never waits on this call.
     */
    public V compute(K key, BiFunction<K, V, V> remapper) {
        int hash = spread(key.hashCode());
        for (;;) {
            Node<K, V>[] tab = table;
            int index = hash & (tab.length - 1);
            Node<K, V> first = tabAt(tab, index);
            if (first == null) {
                V newValue = remapper.apply(key, null);
                if (newValue == null) {
                    return null;
                }
                Node<K, V> node = new Node<>(hash, key, newValue, null);
                if (casTabAt(tab, index, null, node)) {
                    return newValue;
                }
                continue; // another thread won the CAS; retry from scratch
            }
            synchronized (first) {
                if (tabAt(tab, index) != first) {
                    continue; // bin changed under us (resize, or a race we lost); retry
                }
                Node<K, V> node = first;
                Node<K, V> previous = null;
                while (node != null) {
                    if (node.hash == hash && node.key.equals(key)) {
                        V newValue = remapper.apply(key, node.value);
                        if (newValue == null) {
                            unlink(tab, index, first, node, previous);
                        } else {
                            node.value = newValue;
                        }
                        return newValue;
                    }
                    previous = node;
                    node = node.next;
                }
                V newValue = remapper.apply(key, null);
                if (newValue != null) {
                    // Append under the same lock that guards the whole chain.
                    Node<K, V> tail = first;
                    while (tail.next != null) {
                        tail = tail.next;
                    }
                    tail.next = new Node<>(hash, key, newValue, null);
                }
                return newValue;
            }
        }
    }

    private void unlink(Node<K, V>[] tab, int index, Node<K, V> first,
                         Node<K, V> target, Node<K, V> previous) {
        if (previous == null) {
            // Removing the head: publish the rest of the chain (or null) as the new head.
            ARRAY_HANDLE.setRelease(tab, index, target.next);
        } else {
            previous.next = target.next;
        }
    }

    /**
     * Grows the table to twice its size and rehashes every entry. Not resizable
     * concurrently in this mini version — callers must hold an external lock or
     * only call this when quiescent. See the honesty note on resize below.
     */
    @SuppressWarnings("unchecked")
    public synchronized void resize() {
        Node<K, V>[] old = table;
        Node<K, V>[] grown = (Node<K, V>[]) new Node[old.length << 1];
        for (Node<K, V> bin : old) {
            Node<K, V> node = bin;
            while (node != null) {
                Node<K, V> next = node.next;
                int newIndex = node.hash & (grown.length - 1);
                Node<K, V> existingHead = grown[newIndex];
                grown[newIndex] = new Node<>(node.hash, node.key, node.value, existingHead);
                node = next;
            }
        }
        table = grown;
    }
}
```

**Honesty note on what this omits, explicitly, not hidden.** The real `ConcurrentHashMap` does two
things this mini version does not attempt:

1. **Treeification.** When a single bin's chain grows past a threshold (8 entries, with the table
   at least 64 bins), the real map converts that bin from a linked list to a red-black tree,
   bounding worst-case lookup at O(log n) instead of O(n) under a pathological hash collision. This
   mini version leaves every bin a plain chain — fine for `ClientId`'s well-spread `UUID` hash,
   dangerous for an attacker-controlled key.
2. **Cooperative, incremental resize.** The real map lets multiple threads help move bins from the
   old table to the new one concurrently, using a forwarding-node sentinel so readers and writers
   can keep operating on a table that is mid-resize — no stop-the-world pause even at 2.4M entries.
   This mini version's `resize()` is `synchronized` on the whole map and must run when no other
   thread is calling `get`/`compute` on it, which is a real limitation, not a simplification of no
   consequence: at 2.4M clients, a naive full-table rehash under a global lock is exactly the kind
   of pause a production system cannot accept mid-peak.

**Pitfall:** assuming `get()` on this map (or the real `ConcurrentHashMap`) always sees the most
recent `compute()` from another thread. It reads via acquire semantics against a specific bin
snapshot at the moment it runs — a `compute` racing concurrently may or may not be visible depending
on ordering, which is the same weakly-consistent contract `ConcurrentHashMap.get` documents. Never
build a check-then-act invariant ("if absent, then insert") outside of `compute`/`computeIfAbsent`
itself; that is precisely the atomicity `compute` exists to provide.

**Interview:** "why CAS on an empty bin but `synchronized` on a populated one?" — because CAS only
protects a single word (the array slot), which is all an empty-to-first-node transition touches;
once a bin holds a chain, an insert/remove/update needs to walk and possibly mutate multiple `next`
pointers as one atomic-looking step, which a single CAS cannot express, so the JDK (and this mini
version) falls back to a monitor scoped to just that bin's head node.

> A per-bin hash map replaces one map-wide lock with as many independent locks as there are
> populated bins, and skips locking altogether for the cheapest case — installing the first node in
> an empty bin — trading none of `HashMap`'s time complexity for a large reduction in what
> contends with what.

## Pitfalls

### Assuming the copy-on-write iterator will throw like `ArrayList`'s

**Wrong**
```java
CowListenerList<SettlementListener> listeners = new CowListenerList<>();
listeners.add(auditListener);
for (SettlementListener listener : listeners) {
    listeners.add(newlyRegisteredListener); // expecting ConcurrentModificationException here
}
```
No exception is thrown. The `for` loop keeps iterating the array snapshot it started with;
`newlyRegisteredListener` is simply invisible to this particular iteration, silently, and the
developer who copied `ArrayList` habits gets no signal that anything unusual happened.

**Right**
```java
for (SettlementListener listener : listeners) {
    pendingRegistrations.add(newlyRegisteredListener); // queue it, apply after the loop
}
pendingRegistrations.forEach(listeners::add);
```
Treat "modify the list while iterating it" as a design smell regardless of exception behavior:
queue the mutation and apply it once the current delivery pass is done.

**Why people believe it:** every other `java.util` list throws `ConcurrentModificationException` on
structural modification during iteration, so the absence of that exception reads as "it must be
safe to do this here" rather than "this collection made a different, silent trade-off".

## Cheat sheet

| Aspect | Copy-on-write list | Mini `ConcurrentHashMap` |
|---|---|---|
| Read path | lock-free, snapshot array read | lock-free, per-bin chain walk (acquire read) |
| Write path | full-array copy under a lock | CAS on empty bin, `synchronized(bin)` on populated bin |
| Iterator consistency | snapshot at construction, structural methods unsupported | no dedicated iterator here; `get`/`compute` are weakly consistent |
| Best for | rare writes, frequent reads (listener registries) | frequent concurrent reads and writes keyed by a well-spread hash |
| Worst case | O(n) copy per write; O(n²) total for n sequential writes | O(n) per bin if hashes collide badly (no treeify in this version) |
| Omits vs the real JDK class | — (this file's version is close to complete) | treeification, cooperative incremental resize |

## Self-test

**Q1.** Why does `CowListenerList`'s iterator not support `remove()`?

<details><summary>Answer</summary>

The iterator holds a reference to the array snapshot captured when it was created. The live list may
already have replaced that array with a different one by the time `remove()` would be called, so
mutating through the iterator would either operate on a stale, already-discarded array (a no-op
with no effect on the real list) or require re-deriving the live list's current state mid-iteration,
which defeats the entire snapshot guarantee. Making it unsupported is the honest choice.

</details>

**Q2.** Why is the `array` field `volatile` rather than protected only by the mutation lock?

<details><summary>Answer</summary>

Readers never acquire the mutation lock — that is the whole point of the design. Without
`volatile`, a reader on another core could keep observing a stale cached copy of the reference
indefinitely, with no happens-before edge to the write that published the new array. `volatile`
gives every plain read of the field a happens-before relationship to the write that last stored
into it.

</details>

**Q3.** Why would putting 2.8M stake reservations through a `CopyOnWriteArrayList` be a
performance disaster?

<details><summary>Answer</summary>

Every single write copies the entire backing array, so the total cost across n sequential
appends is 1 + 2 + 3 + ... + n array-cell copies, which is O(n²) overall rather than the O(n)
amortized cost of a growable `ArrayList`. At 2.8M appends the array being copied on the final write
alone is 2.8M references, and that full-size copy happens on every earlier write too, not just the
last one.

</details>

**Q4.** In `MiniConcurrentMap.compute`, why does the code re-check `tabAt(tab, index) != first`
immediately after entering the `synchronized (first)` block?

<details><summary>Answer</summary>

Between reading `first` outside the lock and acquiring the monitor on it, another thread could have
already changed the bin — for example, a resize replaced the whole table, or another thread's
insert/remove ran between the read and the lock acquisition. Re-checking that the head is still the
same node confirms the lock actually protects the bin state this thread is about to act on; if it
does not match, the code retries from scratch rather than mutating a chain that is no longer live.

</details>

**Q5.** Why can `get()` on the mini map skip locking entirely, while `compute()` cannot?

<details><summary>Answer</summary>

`get()` only needs to observe a consistent view of already-published state — it walks `volatile`-
linked nodes end to end, and every node it can reach was fully constructed before being published,
so a torn read of a single node is impossible. `compute()` needs to perform a read-modify-write
(check whether a key exists, then either insert, update, or remove) as one atomic-looking step,
which requires excluding other writers on the same bin for the duration, hence the lock.

</details>

**Q6.** What real-world consequence follows from this mini map having no treeification?

<details><summary>Answer</summary>

If keys hash unevenly — a poor `hashCode()`, or an adversary who can choose keys designed to
collide — a single bin's chain can grow arbitrarily long, degrading that bin's lookup/update cost to
O(n) instead of the O(log n) the real `ConcurrentHashMap` guarantees once a bin treeifies past 8
entries (with the table at least 64 bins). For `ClientId`'s `UUID`-derived hash this is a low-risk
gap; for attacker-controlled keys it would be a denial-of-service vector.

</details>

**Q7.** Why is `resize()` on this mini map marked as a real limitation rather than a harmless
simplification?

<details><summary>Answer</summary>

At 2.4M entries, a synchronized full-table rehash blocks every concurrent `get`/`compute` call for
however long the rehash takes, which for a table that size is not a negligible pause. The real
`ConcurrentHashMap` avoids this by letting resize proceed incrementally with forwarding nodes so
readers and writers keep operating on a table that is only partially migrated — omitting that is a
genuine capability gap, not just missing polish.

</details>

---

**Leaves covered:** 4.4.9, 4.4.10 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 550
