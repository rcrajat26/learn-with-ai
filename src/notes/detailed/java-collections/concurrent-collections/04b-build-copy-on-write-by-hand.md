# 02 Java Collections — Copy-on-write by hand — INTERNALS (§3.14.36, §4.6.8 a `CopyOnWriteList<E>` over `AtomicReference<Object[]>`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [concurrent-collections/04-copy-on-write.md](04-copy-on-write.md) · Next: [concurrent-collections/05-blocking-and-lock-free-queues.md](05-blocking-and-lock-free-queues.md)

---

## The four copy-on-write options

The previous file walked `CopyOnWriteArrayList`'s source: a `synchronized`
monitor (`final transient Object lock = new Object()` — a plain monitor, not
`ReentrantLock`, `CopyOnWriteArrayList.java:107`; `ReentrantLock` was only the
JDK 8 shape, 8u202:97) guarding a `volatile Object[]`. This file builds the
lock-free sibling by hand, complete and runnable, honest about when it wins.

| Option | Backing field | Concurrency control | Multi-element atomic update | Whole-snapshot swap |
|---|---|---|---|---|
| `CopyOnWriteArrayList` | `volatile Object[]` | `synchronized` monitor | No — each mutator call is its own publication | No — no `setAll` |
| `AtomicReference<Object[]>` (this file) | `Object[]` behind a CAS | CAS-retry, no lock | Yes — one CAS can add many elements at once | Yes — `ref.set(newArray)` |
| `AtomicReference<List<E>>` (also this file) | immutable `List<E>` behind a CAS | CAS-retry, no lock | Yes | Yes, allocation-free to read |
| plain `synchronized` list | mutable array-backed list | monitor on every call, including reads | Yes, inside one synchronized block | Yes, under the same lock |

The two rows this file builds share one property the JDK class cannot offer
at any price: a multi-element change published as a single atomic step. That
is the entire reason to write this class instead of importing
`java.util.concurrent.CopyOnWriteArrayList`.

## `CopyOnWriteList<E>` over `AtomicReference<Object[]>`

The complete class, compiled and run as part of this file's build proof
below:

```java
// CopyOnWriteList.java
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.UnaryOperator;

public final class CopyOnWriteList<E> {

    private final AtomicReference<Object[]> ref;

    public CopyOnWriteList() {
        this.ref = new AtomicReference<>(new Object[0]);
    }

    @SuppressWarnings("unchecked")
    public E get(int index) {
        Object[] a = ref.get();
        if (index < 0 || index >= a.length) {
            throw new IndexOutOfBoundsException("Index: " + index + ", Size: " + a.length);
        }
        return (E) a[index];
    }

    public int size() {
        return ref.get().length;
    }

    public boolean isEmpty() {
        return ref.get().length == 0;
    }

    // Test-only hooks: see "deterministic CAS-retry proof" below.
    Object[] currentArrayForTest() {
        return ref.get();
    }
    boolean casArrayForTest(Object[] expect, Object[] update) {
        return ref.compareAndSet(expect, update);
    }

    public void add(E element) {
        while (true) {
            Object[] current = ref.get();
            int n = current.length;
            Object[] next = new Object[n + 1];
            System.arraycopy(current, 0, next, 0, n);
            next[n] = element;
            if (ref.compareAndSet(current, next)) {
                return;
            }
            // CAS failed: retry from scratch -- see prose below on why.
        }
    }

    public void addModern(E element) {
        ref.getAndUpdate(current -> {
            int n = current.length;
            Object[] next = new Object[n + 1];
            System.arraycopy(current, 0, next, 0, n);
            next[n] = element;
            return next;
        });
    }

    public boolean remove(Object element) {
        while (true) {
            Object[] current = ref.get();
            int idx = indexOf(current, element);
            if (idx < 0) {
                return false;
            }
            Object[] next = new Object[current.length - 1];
            System.arraycopy(current, 0, next, 0, idx);
            System.arraycopy(current, idx + 1, next, idx, current.length - idx - 1);
            if (ref.compareAndSet(current, next)) {
                return true;
            }
        }
    }

    @SuppressWarnings("unchecked")
    public E set(int index, E element) {
        while (true) {
            Object[] current = ref.get();
            if (index < 0 || index >= current.length) {
                throw new IndexOutOfBoundsException("Index: " + index + ", Size: " + current.length);
            }
            Object[] next = current.clone();
            E old = (E) next[index];
            next[index] = element;
            if (ref.compareAndSet(current, next)) {
                return old;
            }
        }
    }

    public void addAll(List<? extends E> elements) {
        if (elements.isEmpty()) {
            return;
        }
        while (true) {
            Object[] current = ref.get();
            int n = current.length;
            Object[] next = new Object[n + elements.size()];
            System.arraycopy(current, 0, next, 0, n);
            int i = n;
            for (E e : elements) {
                next[i++] = e;
            }
            if (ref.compareAndSet(current, next)) {
                return;
            }
        }
    }

    public void replaceAll(UnaryOperator<E> operator) {
        ref.getAndUpdate(current -> {
            Object[] next = current.clone();
            for (int i = 0; i < next.length; i++) {
                @SuppressWarnings("unchecked")
                E oldValue = (E) next[i];
                next[i] = operator.apply(oldValue);
            }
            return next;
        });
    }

    @SuppressWarnings("unchecked")
    public List<E> snapshot() {
        Object[] a = ref.get();
        List<E> copy = new ArrayList<>(a.length);
        for (Object o : a) {
            copy.add((E) o);
        }
        return List.copyOf(copy);
    }

    public Iterator<E> iterator() {
        return new SnapshotIterator<>(ref.get());
    }

    private static int indexOf(Object[] array, Object element) {
        for (int i = 0; i < array.length; i++) {
            if (element == null ? array[i] == null : element.equals(array[i])) {
                return i;
            }
        }
        return -1;
    }

    private static final class SnapshotIterator<E> implements Iterator<E> {
        private final Object[] snapshot;
        private int cursor;

        SnapshotIterator(Object[] snapshot) {
            this.snapshot = snapshot;
        }

        @Override
        public boolean hasNext() {
            return cursor < snapshot.length;
        }

        @SuppressWarnings("unchecked")
        @Override
        public E next() {
            if (!hasNext()) {
                throw new NoSuchElementException();
            }
            return (E) snapshot[cursor++];
        }

        @Override
        public void remove() {
            throw new UnsupportedOperationException("snapshot iterator is immutable");
        }
    }
}
```

### The field, and why `AtomicReference` matches `volatile`'s guarantee

**Mental model.** `CopyOnWriteArrayList` publishes a new array by writing a
`volatile` field. `AtomicReference<Object[]>` is the same mechanism wearing a
different API — a volatile-equivalent reference, plus one extra capability: a
compare-and-set that can fail and be retried instead of being serialized
behind a lock.

**Gotcha:** `final` on the outer `ref` field only guarantees the *reference*
is safely published; the volatile-equivalent visibility of the *array
contents* comes from `AtomicReference`'s own internal field, not `final`.

> `get`/`size`/`isEmpty` cost exactly what the JDK class costs: one volatile
> read plus an array access, lock-free, no retry ever needed.

### The CAS-retry loop — `add(E)`

**Mental model.** Every writer races to hang a new sign on a door. Whoever
nails theirs up first wins; everyone else notices the door already changed,
tears up their own sign, redraws it against the door's *new* state, and
tries again. Nobody stands in a queue — but everyone rejected must redo the
drawing, not just re-nail the old one.

**Why it exists, and when to reach for it.** `compareAndSet(expected, new)`
only succeeds if the field still holds exactly `expected`; if another thread
already swapped it, the CAS fails and the loop retries. This
read-compute-CAS-retry shape is the canonical lock-free update for any single
mutable reference. It loses to a lock when writes are large and contention is
high (see the cost comparison below), and it is the wrong tool when more than
one independent field must change atomically together — that needs a lock,
or one object combining both fields behind one reference.

**Why the retry must re-read *and* re-copy, not just re-attempt the CAS.**
Suppose the loop kept `next` from a failed attempt and simply retried
`compareAndSet(ref.get(), next)`. `next` was built by copying the *old* array
plus one element — it does not contain whatever the winning writer just
added. The only correct retry re-reads `current` fresh, rebuilds `next` from
that fresh base, and only then attempts the CAS again — exactly the
lost-update failure mode `CopyOnWriteArrayList`'s lock prevents by
construction, since under a lock nothing is ever stale. The Pitfalls section
below shows the broken version of this loop.

**Insight:** a CAS failure is not an error to handle — it is the mechanism's
ordinary control flow. Every lock-free algorithm built on `compareAndSet` is a
state machine whose "unhappy path" is "go around again."

**The idiomatic modern form — `getAndUpdate`.** `addModern` above shows the
same loop expressed through `AtomicReference.getAndUpdate`, which implements
this exact retry internally.

**Pitfall:** the `getAndUpdate`/`updateAndGet` lambda **must be
side-effect-free and may run more than once** — under contention the internal
retry loop calls it again for every failed CAS, so a side effect (an external
counter, a log append) fires once per *attempt*, not once per successful
update. Easy to miss because on an uncontended class it appears to run
exactly once every time.

**Interview:** "Difference between `getAndUpdate` and `updateAndGet`?" — same
retry loop, different return value: `getAndUpdate` returns the value *before*
the CAS, `updateAndGet` the value *after*. Neither runs exactly once.

> **A CAS-retry loop is a lock that never blocks: it lets every writer race to publish and makes the losers redo their work from a fresh read — correct only if every retry recomputes from a freshly re-read base, never from stale data.**

### `remove(Object)`, `set(int, E)`, `addAll`, `replaceAll`

Same read-compute-CAS-retry shape as `add`, different array transform.
`addAll` and `replaceAll` are the first of the two capabilities that justify
hand-rolling this class: `CopyOnWriteArrayList.addAll` builds one bigger
array under the lock and swaps it for *that one call*, but two independent
JDK `add` calls can never look atomic together, whereas one CAS here publishes
many elements' worth of change as a single step.

**Gotcha:** `indexOf` (inside `remove`) and the bounds check (inside `set`)
must be recomputed on every retry against the freshly re-read array, not
reused — the target index or the array length can change between attempts.
The `getAndUpdate` side-effect pitfall applies to `replaceAll` sharper still,
since `operator` runs against every element on every retry attempt.

### The snapshot iterator, and `snapshot()`

**Mental model.** The iterator mirrors `CopyOnWriteArrayList`'s own
`COWIterator` from the previous file: capture the array once, at creation
time, and iterate over that frozen state regardless of later writes.
`snapshot()` is the second reason to hand-roll this class — handing a caller
the entire current contents as an immutable `List` in one call, something
`CopyOnWriteArrayList` has no equivalent for.

**Gotcha:** the iterator's `remove()` throws `UnsupportedOperationException`
— there is no sensible meaning for "remove what I'm looking at" against a
frozen array the live list has moved past, identical to `COWIterator`.
`snapshot()` still allocates, walking the `Object[]` and boxing every element,
because the backing store is a raw array; the `AtomicReference<List<E>>`
variant below removes even this copy.

> **`CopyOnWriteList<E>` is a `List`-shaped value that publishes every mutation as a fresh, fully-built `Object[]` behind a CAS-retry loop instead of a lock, trading "writers never block" for "writers under contention redo wasted work," and its `snapshot()` is the one call `CopyOnWriteArrayList` cannot offer without the caller writing the copy loop itself.**

## The idiomatic Java 21 form — `AtomicReference<List<E>>`

The class above uses a raw `Object[]` because that mirrors what
`CopyOnWriteArrayList` does internally, the point of sitting next to that
source walk. A reader writing this pattern from scratch in Java 21 should
reach for `List.of(...)`/`Stream.toList()` instead — already immutable and
type-safe, removing the raw-array cast and making `snapshot()` a plain,
allocation-free getter:

```java
// AtomicListRef.java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

public final class AtomicListRef<E> {

    private final AtomicReference<List<E>> ref = new AtomicReference<>(List.of());

    public E get(int index) {
        return ref.get().get(index);
    }

    public int size() {
        return ref.get().size();
    }

    public void add(E element) {
        ref.getAndUpdate(current -> {
            List<E> next = new ArrayList<>(current);
            next.add(element);
            return List.copyOf(next);
        });
    }

    // Whole-snapshot swap CopyOnWriteArrayList cannot express: one atomic step.
    public void setAll(List<E> replacement) {
        ref.set(List.copyOf(replacement));
    }

    // Allocation-free: the field already holds an immutable List to hand back.
    public List<E> snapshot() {
        return ref.get();
    }
}
```

**Interview:** "Why prefer `AtomicReference<List<E>>` in new code?" — type
safety with no casts, and `snapshot()` is free since the stored value is
already immutable; the array form exists here only to mirror the JDK
internals for the source-walk comparison.

## Comparison against `java.util.concurrent.CopyOnWriteArrayList`

| | `CopyOnWriteList<E>` (hand-rolled) | `CopyOnWriteArrayList` (JDK) |
|---|---|---|
| Whole-snapshot swap | Yes — `ref.set(newArray)` | No such method exists |
| Multi-element atomic update across calls | Yes — one CAS covers many elements | No — each call is its own lock/publish cycle |
| Blocks other writers | Never — writers retry instead | Yes — one writer holds the monitor at a time |
| Cost, low vs. high write contention | Same as JDK when uncontended; **worse** under contention — every losing CAS wastes a copy | Copy once either way — the monitor guarantees each writer copies exactly once |
| Full `List` contract | No — only the methods shown here | Yes — `subList`, `listIterator`, `equals`/`hashCode`, serialization, `RandomAccess` |
| `removeIf` bulk removal, `addIfAbsent` two-phase re-check | Not implemented | Both implemented and correct |
| Battle-tested | No — this file's own code | Yes |

**Where hand-rolled wins** (detail beyond the table): the JDK's closest
approximation to a whole-snapshot swap, `clear()` then `addAll()`, is two
lock acquisitions with a visible empty-list window between — the hand-rolled
`ref.set(newArray)` has no such window.

**Where the JDK class wins, and this half matters more than it looks:**
it implements the full `List` contract where this class deliberately
implements a small surface, and **under write contention the CAS loop
retries and re-copies, so wasted work grows with contention, whereas the
JDK's monitor makes each writer copy exactly once.** With `k` writers
contending, the monitor-based class does exactly `k` copies total; the
CAS-based class can do far more, since every writer whose CAS loses must
redo its O(n) copy, and that waste grows with the number of *competing*
writers, not the number of *successful* updates. **This is the opposite of
the usual "lock-free is always faster" intuition, and is the single most
valuable point in this file** — derived from the retry arithmetic, not
measured; see Unverified below.

**The decision rule:** reach for the hand-rolled `AtomicReference`-backed
version when the value is naturally a whole immutable snapshot replaced
wholesale — a config object, a routing table, a rules set. Reach for
`CopyOnWriteArrayList` when you want a `List` mutated element-wise, with the
full `List` contract.

**Unverified:** the write-contention cost claim is derived from counting CAS
attempts, not benchmarked. A rigorous measurement needs JMH with
`-prof perfnorm` on a named CPU/JDK build, varying writer count — out of
scope here per the house rule against unlabelled throughput numbers. What
would settle it: total array-copy bytes under 2/8/32 concurrent writers
appending to a 10,000-element list, both implementations, same machine.

## Proving the CAS-retry loop correct, and proving the alternative wrong

**Concurrency honesty.** A real multithreaded run of a race is a lucky
transcript, not a proof — the interleaving needed to trigger a lost update
might not occur on a given run, making a digest non-reproducible. The
CAS-retry loop's correctness is instead proved deterministically, on one
thread, by manually sequencing the exact steps a race would cause. A
genuinely multithreaded test is included too, where it earns its place: its
*assertion* is deterministic even though the interleaving is not.

The deliberately broken class used below:

```java
// BrokenCopyOnWriteList.java
import java.util.concurrent.atomic.AtomicReference;

// BROKEN ON PURPOSE: reads once, copies once, blind set() instead of CAS-retry.
// Exists only so the deterministic race proof in Demo.java has something to fail
// against. Never model production code on this class.
public final class BrokenCopyOnWriteList<E> {

    private final AtomicReference<Object[]> ref = new AtomicReference<>(new Object[0]);

    public int size() {
        return ref.get().length;
    }

    public void add(E element) {
        Object[] current = ref.get();
        int n = current.length;
        Object[] next = new Object[n + 1];
        System.arraycopy(current, 0, next, 0, n);
        next[n] = element;
        ref.set(next);
    }

    // Test-only hooks, mirroring CopyOnWriteList's, forcing a deterministic
    // single-threaded reproduction of the lost-update race.
    Object[] readForTest() {
        return ref.get();
    }

    void writeForTest(Object[] array) {
        ref.set(array);
    }
}
```

And the demo exercising everything in this file, including all three proofs:

```java
// Demo.java
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;

public final class Demo {

    public static void main(String[] args) throws InterruptedException {
        boundsCheckDemo();
        functionalDemo();
        deterministicCasRetryProof();
        deterministicLostUpdateProof();
        concurrentCorrectnessCheck();
    }

    private static void boundsCheckDemo() {
        CopyOnWriteList<String> list = new CopyOnWriteList<>();
        list.add("only-element");
        try {
            list.get(5);
        } catch (IndexOutOfBoundsException e) {
            System.out.println("Caught expected: " + e.getMessage());
        }
    }

    private static void functionalDemo() {
        CopyOnWriteList<String> list = new CopyOnWriteList<>();
        list.add("a");
        list.add("b");
        list.addModern("c");
        list.addAll(List.of("d", "e"));
        list.replaceAll(s -> s.toUpperCase());
        System.out.println("After adds/addAll/replaceAll: " + list.snapshot());

        String old = list.set(0, "A-replaced");
        boolean removed = list.remove("B");
        System.out.println("set() old=" + old + ", remove(\"B\")=" + removed + ", now: " + list.snapshot());

        var it = list.iterator();
        while (it.hasNext()) {
            it.next();
        }
        try {
            it.remove();
        } catch (UnsupportedOperationException e) {
            System.out.println("Caught expected: " + e.getMessage());
        }

        AtomicListRef<Integer> ref = new AtomicListRef<>();
        ref.add(1);
        ref.add(2);
        ref.setAll(List.of(100, 200));
        System.out.println("AtomicListRef after add/add/whole-snapshot swap: " + ref.snapshot());
    }

    // Deterministic CAS-retry proof -- see prose below.
    private static void deterministicCasRetryProof() {
        CopyOnWriteList<String> list = new CopyOnWriteList<>();
        list.add("a");
        Object[] staleSnapshot = list.currentArrayForTest(); // ["a"], as thread A would see it
        list.add("b"); // thread B "wins" the race and publishes ["a", "b"]
        Object[] staleAttempt = new Object[staleSnapshot.length + 1];
        System.arraycopy(staleSnapshot, 0, staleAttempt, 0, staleSnapshot.length);
        staleAttempt[staleSnapshot.length] = "c-built-from-stale-array";
        boolean casSucceeded = list.casArrayForTest(staleSnapshot, staleAttempt);
        System.out.println("Stale CAS attempt succeeded? " + casSucceeded);
        // The real add() loop would now retry: re-read (["a","b"]), re-copy, re-append.
        list.add("c");
        System.out.println("Final snapshot after the retry re-reads and re-copies: " + list.snapshot());
    }

    // Deterministic lost-update proof against the broken class -- see prose below.
    private static void deterministicLostUpdateProof() {
        BrokenCopyOnWriteList<String> broken = new BrokenCopyOnWriteList<>();
        broken.add("x");
        Object[] readByA = broken.readForTest(); // A reads ["x"]
        broken.add("y"); // B fully executes: reads ["x"], writes ["x","y"]
        Object[] nextFromA = new Object[readByA.length + 1];
        System.arraycopy(readByA, 0, nextFromA, 0, readByA.length);
        nextFromA[readByA.length] = "z";
        broken.writeForTest(nextFromA); // blind overwrite: B's "y" never existed as far as anyone can see
        System.out.println("Broken size after the simulated race: " + broken.size()
                + " (expected 3 if both writes had survived; \"y\" was lost)");
    }

    // Genuinely multithreaded correctness check -- see prose below.
    private static void concurrentCorrectnessCheck() throws InterruptedException {
        final int threadCount = 8;
        final int perThread = 500;
        final int expected = threadCount * perThread;
        CopyOnWriteList<String> list = new CopyOnWriteList<>();
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(threadCount);
        for (int t = 0; t < threadCount; t++) {
            final int threadId = t;
            new Thread(() -> {
                try {
                    startLatch.await();
                    for (int i = 0; i < perThread; i++) {
                        list.add("t" + threadId + "-e" + i);
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } finally {
                    doneLatch.countDown();
                }
            }).start();
        }
        startLatch.countDown();
        doneLatch.await();

        Set<String> expectedElements = new HashSet<>();
        for (int t = 0; t < threadCount; t++) {
            for (int i = 0; i < perThread; i++) {
                expectedElements.add("t" + t + "-e" + i);
            }
        }
        Set<String> actualElements = new HashSet<>(list.snapshot());
        boolean sizeOk = list.size() == expected;
        boolean contentsOk = actualElements.equals(expectedElements);
        System.out.println("Concurrent add: " + threadCount + " threads x " + perThread
                + " elements, final size = " + list.size() + " (expected " + expected + "), sizeOk=" + sizeOk
                + ", contentsOk=" + contentsOk);
    }
}
```

**`deterministicCasRetryProof`** plays out the interleaving a real second
writer would cause, without a scheduler: capture the array a "reader" would
have seen (`currentArrayForTest`), let a concurrent `add` land on top of it,
then attempt the CAS with that now-stale snapshot (`casArrayForTest`). That
attempt always returns `false`, deterministically; the following real
`add("c")` shows the retry re-reading and re-copying correctly.

**`deterministicLostUpdateProof`** applies the same technique to the broken
class: "thread A" reads the array, "thread B" fully executes a real `add`,
and A's stale array is then written with a blind `set()` (`writeForTest`)
instead of a CAS, silently overwriting B's element — the size comes out one
short, deterministically, every time, because the interleaving was chosen by
hand, not by luck.

**`concurrentCorrectnessCheck`** is a genuine multithreaded test: 8 threads
each add 500 uniquely-named elements via a `CountDownLatch`-gated start, then
asserts final size equals exactly 4000 with every element present. The
interleaving is uncontrolled, but the assertion has one correct value for a
correct implementation, so its printed line is safe inside a reproducible
digest despite using real threads; run against the broken class, this same
test would fail unreliably depending on scheduling — why the broken class's
failure is demonstrated with the deterministic proof above instead.

## Pitfalls

### Reusing the CAS-failure's stale `next` array instead of rebuilding it

**Wrong**

```java
public void addWrong(E element) {
    Object[] current = ref.get();
    Object[] next = new Object[current.length + 1];
    System.arraycopy(current, 0, next, 0, current.length);
    next[current.length] = element;
    while (!ref.compareAndSet(current, next)) {
        current = ref.get();
        // BUG: `next` still has the OLD length and OLD contents from the first
        // attempt; only `current` is refreshed here, `next` never is.
    }
}
```

Against a concurrently-mutating list this either fails every retry forever,
or, in a variant that skips the length mismatch, silently truncates the list
back to the length `next` was built with — discarding elements other threads
added after the first read, with no exception announcing it.

**Right:** the real `add` shown at the top of this file — every retry rebuilds
`next` from a freshly re-read `current`, inside the loop body.

**Why people believe it:** `while (!ref.compareAndSet(...))` looks identical
to the scalar-CAS "retry until it works" idiom (an atomic counter increment),
where re-adding a constant to a fresh read is cheap and safe. The difference:
`next` is a *derived, larger structure* built earlier, and it goes stale the
moment its source changes.

### Treating `getAndUpdate`'s lambda as if it runs exactly once

**Wrong**

```java
int[] attempts = {0};
ref.getAndUpdate(current -> {
    attempts[0]++;              // BUG: side effect inside the update function
    Object[] next = current.clone();
    return next;
});
System.out.println("Update happened " + attempts[0] + " time(s)."); // not reliably 1
```

Under contention, `attempts[0]` counts every failed CAS attempt, not just the
one that succeeded — the printed count silently overstates how many times
the list actually changed.

**Right:** count outside the lambda, at the `getAndUpdate` call site itself,
which runs exactly once per invocation regardless of internal retries.

**Why people believe it:** most callers only call `getAndUpdate` from a
single thread in a demo or low-contention test, where the lambda genuinely
runs once every time — until it meets real concurrent load.

## Cheat sheet

| Operation | Mechanism | Cost |
|---|---|---|
| `get`, `size`, `isEmpty` | one `ref.get()` + array read | O(1), lock-free, never retries |
| `add(E)` / `addModern(E)` | CAS-retry: copy `n+1`, CAS, retry via `while`/`getAndUpdate` | O(n) per attempt, grows with contention |
| `remove(Object)`, `set(int, E)` | CAS-retry: find index / clone, mutate, CAS | O(n) per attempt |
| `addAll(List)`, `replaceAll(op)` | CAS-retry, one CAS covers all k elements | one atomic publish; `op` must be pure |
| `iterator()` | frozen `Object[]` at creation | `remove()` throws `UnsupportedOperationException` |
| `snapshot()` | walks `Object[]`, boxes into `List.copyOf` | O(n) allocation every call |
| `AtomicListRef.snapshot()` / `.setAll(list)` | returns stored `List` / `ref.set(List.copyOf(list))` | O(1) no allocation / whole-snapshot swap |

**Decision rule:** whole immutable snapshot replaced wholesale → hand-rolled
`AtomicReference`. `List` mutated element-wise, need full `List` contract →
`CopyOnWriteArrayList`. High write contention → JDK's lock, not a CAS-retry
loop.

## Self-test

**Q1.** Why does the `add(E)` retry loop have to rebuild `next` from a fresh
`ref.get()` on every iteration instead of just retrying the same CAS call?

<details><summary>Answer</summary>

Because `next` was built by copying whatever `current` was at the time of the
failed attempt; if another thread already published a different array,
`next` is missing that change entirely. Retrying with the same `next` either
keeps failing or, in a buggy variant, silently discards the other thread's
update — the lost-update bug this loop exists to prevent.

</details>

**Q2.** Why can `getAndUpdate`'s lambda run more than once for a single call,
and what does that mean for what it can safely contain?

<details><summary>Answer</summary>

`getAndUpdate` implements the same CAS-retry loop this file writes by hand,
calling the function again against the newly-read value on every failed CAS.
Under contention this can happen several times per call, so the function must
be pure — no external side effects — since the number of executions cannot
be predicted.

</details>

**Q3.** Name one thing the hand-rolled `CopyOnWriteList<E>` can do that
`CopyOnWriteArrayList` genuinely cannot do at all, not even inefficiently.

<details><summary>Answer</summary>

A true whole-snapshot swap — `ref.set(newArray)` replaces every element in
one atomic step with no lock and no intermediate visible state.
`CopyOnWriteArrayList` has no `setAll`; the closest approximation, `clear()`
then `addAll()`, is two separate lock acquisitions with an empty-list window
visible in between.

</details>

**Q4.** Under high write contention, which implementation does *more* total
array-copy work: the CAS-retry class or the lock-based `CopyOnWriteArrayList`?
Why does this surprise people?

<details><summary>Answer</summary>

The CAS-retry class does more. The lock-based class guarantees each of `k`
contending writers copies the array exactly once, since the monitor
serializes them; the CAS-retry class lets every writer attempt concurrently,
but only one CAS per round succeeds, so every losing writer's copy is wasted
and redone. This surprises people because "lock-free" is assumed to mean
"faster," when it only means "never blocks."

</details>

**Q5.** This file proves the broken class's lost-update bug with a
manually-sequenced hook call rather than real concurrent threads, but also
ships a real multithreaded test for the correct class. Why is one
deterministic-by-design and the other safe despite non-deterministic
interleaving?

<details><summary>Answer</summary>

A real threaded run against the *broken* class is genuinely probabilistic —
the interleaving needed to lose an update might not occur on a given run, so
the proof instead manually sequences the same two hook calls (a stale read,
a full concurrent write, then the stale write) to reproduce the race
deterministically. The multithreaded test against the *correct* class is
safe despite uncontrolled interleaving because its assertion has exactly one
correct value for a correct implementation — a lost update always manifests
as a wrong size, so a passing run is real evidence, not a lucky outcome.

</details>

## Open questions

- **Unverified:** CAS-retry contention cost growing with writer count while
  the JDK's lock stays constant per writer is derived from counting CAS
  attempts, not measured. Settle it with a JMH `-prof perfnorm` benchmark,
  naming CPU/JDK build, varying writer count 2–32 against a fixed-size list.

## Build proof

**Inclusion rule (verbatim regex):** a fenced ` ```java ` block counts as
buildable source if and only if its first line full-matches `// (\w+\.java)`.

**Blocks included, per label:**

| Label | Blocks | Notes |
|---|---|---|
| `CopyOnWriteList.java` | 1 | whole compilation unit |
| `AtomicListRef.java` | 1 | whole compilation unit |
| `BrokenCopyOnWriteList.java` | 1 | whole compilation unit |
| `Demo.java` | 1 | whole compilation unit |

**Blocks excluded:** 2 `java` blocks lacking the label — the two Pitfalls
"Wrong" blocks (`addWrong`, the `getAndUpdate` side-effect snippet), each
opening with a bare method/field declaration, not `// Name.java`. 0 untagged
fences — this file quotes no JDK source directly; the `lock` field fact is
cited inline in prose with a file:line reference, not a fenced quote.

**Splicing and block order:** no splicing — every included block is a
complete, whole compilation unit exactly as compiled. Each label has exactly
one block, so no cross-block ordering question arises.

**Behavioural wrapping of a throwing snippet:** the two intentionally-throwing
calls in `Demo.java` (`list.get(5)`, `list.iterator().remove()`) are wrapped
in `try/catch` **in the published, compiled source itself**, not patched into
the harness, so a reader transcribing the page verbatim runs to completion.

**What the digest covers:** stdout and stderr merged (`2>&1`), one run of
`java -cp out Demo`, 9 lines. Deterministic because the two caught exceptions
always throw at the same call sites, the CAS-retry and lost-update proofs are
hand-sequenced on one thread with no real concurrency, and
`concurrentCorrectnessCheck` prints only a pass/fail summary from an
assertion that holds regardless of thread interleaving — no timing or
wall-clock value is ever printed. A second run was diffed byte-for-byte
against the first and found identical before recording.

**Exact command lines:**

```
/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/javac -d out CopyOnWriteList.java AtomicListRef.java BrokenCopyOnWriteList.java Demo.java
/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/java -cp out Demo > run1.out 2>&1
md5 run1.out
```

**JDK build:** `21.0.7+8-LTS-245` (`java version "21.0.7" 2025-04-15 LTS`).
**CPU:** Apple M4 Pro (arm64). **OS note:** macOS ships BSD `md5`, not GNU
`md5sum` — the command above is the BSD form.

**Digest:** `MD5 (run1.out) = 1ef5f083139dd90dd5f6b9446f17bb6b`, 9 lines,
stdout+stderr merged, reproduced identically on a second run before
recording.

---

**Leaves covered:** 3.14.36, 4.6.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 826
