# 02 Java Collections — `PriorityQueue` — INTERNALS (§4.5 the stable variant, the bounded top-k, and the diff vs the real one)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [priority-queue/04-build-my-priority-queue-b-operations-and-iterator.md](04-build-my-priority-queue-b-operations-and-iterator.md) · Next: [hash-map/01-internals-a-constants-and-hash.md](../hash-map/01-internals-a-constants-and-hash.md)

Part three, and the last of the `MyPriorityQueue` build. `MyPriorityQueue.java` is complete as the concatenation of the labelled blocks in [03](03-build-my-priority-queue.md) and [04](04-build-my-priority-queue-b-operations-and-iterator.md). This file adds two standalone companion classes that fix the two things a plain heap cannot do — deliver equal priorities in arrival order, and stay bounded — then diffs the whole build against `java.util.PriorityQueue` and gives the compile-and-run transcript.

---

### The stable variant: making equality impossible

**Mental model.** You cannot make a heap stable by adjusting the sift loops, because both of them halt on equality by construction (`>= 0` climbing, `<= 0` sinking) and there is nowhere for arrival order to live. So you do not make the heap stable — you make the *comparator* total, so that no two elements ever compare equal and the equality case never arises. Wrap each element with a monotonically increasing arrival number and compare on `(priority, arrivalNumber)`.

**Why it exists.** Because "priority queue" means FIFO-within-a-priority in most textbook descriptions and in several other standard libraries, so the expectation is nearly universal and the JDK does not meet it. The measured evidence, from [02](02-internals-b-traps.md) and reproduced in the transcript below: seven tasks all of priority 1, inserted `a b c d e f g`, drain as `agfedcb`.

**When to reach for it, and when not.** Use it when the ordering *between equals* is observable — a work queue whose tasks have side effects, a request scheduler, anything where a flaky test would result. Do not use it when the elements already carry a natural unique tiebreak (a monotonic timestamp, a database id, a sequence from upstream), because then you should put that field in the comparator directly and skip the wrapper's 32 bytes per element.

**How it works.**

```java
// StablePriorityQueue.java  —  a standalone second file
import java.util.AbstractQueue;
import java.util.Comparator;
import java.util.Iterator;
import java.util.Objects;

/**
 * A stable priority queue: equal priorities come out in insertion order.
 * Works by making equality impossible, with a monotonic sequence number as the
 * secondary key.
 */
public final class StablePriorityQueue<E> extends AbstractQueue<E> {

    /** An element paired with its arrival number. */
    private record Stamped<E>(E value, long seq) {}

    private final MyPriorityQueue<Stamped<E>> heap;
    private long counter;

    public StablePriorityQueue(Comparator<? super E> byPriority) {
        Objects.requireNonNull(byPriority);
        this.heap = new MyPriorityQueue<>(
            Comparator.<Stamped<E>, E>comparing(Stamped::value, byPriority)
                      .thenComparingLong(Stamped::seq));
    }

    @Override public boolean offer(E e) {
        return heap.offer(new Stamped<>(Objects.requireNonNull(e), counter++));
    }

    @Override public E poll() {
        Stamped<E> s = heap.poll();
        return (s == null) ? null : s.value();
    }

    @Override public E peek() {
        Stamped<E> s = heap.peek();
        return (s == null) ? null : s.value();
    }

    @Override public int size() {
        return heap.size();
    }

    @Override public Iterator<E> iterator() {
        Iterator<Stamped<E>> it = heap.iterator();
        return new Iterator<>() {
            @Override public boolean hasNext() { return it.hasNext(); }
            @Override public E next()          { return it.next().value(); }
            @Override public void remove()     { it.remove(); }
        };
    }
}
```

Five details, each a real decision.

**The comparator, not the elements.** `Comparator.comparing(Stamped::value, byPriority).thenComparingLong(Stamped::seq)` — the two-argument `comparing` takes a key extractor *and* a comparator for that key, which is what lets an arbitrary caller-supplied `Comparator<? super E>` be used on the unwrapped value. The alternative, requiring `E extends Comparable<E>`, would exclude every element type the caller does not own.

**`thenComparingLong`, not `thenComparing`.** The boxing form would allocate a `Long` on every comparison, and `poll` performs roughly `2 log₂ n` of them — so at a million elements that is around 40 allocations per `poll`, all immediately garbage. `thenComparingLong` takes a `ToLongFunction` and compares primitives.

**`counter` is a plain `long`, not an `AtomicLong`.** The class is not thread-safe and does not pretend to be — `MyPriorityQueue` is not either, so an `AtomicLong` would add a CAS per insertion while leaving the heap itself racy, which is worse than useless: it would look safe. If you need a thread-safe stable queue, wrap the whole thing, or use `PriorityBlockingQueue` with the same stamped comparator.

**`long`, not `int`.** At 2³¹ insertions an `int` counter wraps to `Integer.MIN_VALUE`, and every element inserted after the wrap compares as *earlier* than everything before it — the queue silently reverses within equal priorities. A `long` at a million insertions per second lasts about 292,000 years. This is the same class of bug as `a - b` used as a comparator ([D-14](../diagrams/D-14-subtract-comparator-overflow.svg)), and the fix is the same: use a width the arithmetic cannot escape, and compare rather than subtract — which `thenComparingLong` does, via `Long.compare`.

**The wrapper `record` is `private`.** `Stamped` never appears in the public signature, so callers see a plain `Queue<E>`. That is what makes the class a drop-in replacement rather than a leaky abstraction — and it is only possible because `offer`/`poll`/`peek`/`iterator` all wrap and unwrap at the boundary.

The cost, stated plainly: one `Stamped` object per element — 16 bytes of header, a 4-byte compressed reference, an 8-byte `long`, padded to 32 bytes — on top of the element itself and the 4-byte array slot. Roughly 36 bytes per element of overhead where the plain heap costs 4. Plus one extra comparison, but only on the ties that used to be ambiguous.

Measured:

```
unstable drain      = agfedcb
stable drain        = a b c d e f g
stable mixed drain  = lo1 lo2 mid hi1 hi2
```

The third line is the one that shows it is a *stable priority* queue and not merely a FIFO: five tasks inserted `hi1(3) lo1(1) hi2(3) lo2(1) mid(2)` come out strictly by priority, and within each priority strictly by arrival — `lo1` before `lo2`, `hi1` before `hi2`.

**Pitfall:** the wrong belief is that the sequence number belongs on the element. The symptom is that you cannot use the class with element types you do not own, and that two logically-equal elements now compare unequal *everywhere*, including in any `HashSet` or `TreeMap` the element also lives in. The fix is to keep the stamp in a private wrapper visible only to this queue's comparator, so the element's own `equals`, `hashCode` and `compareTo` are untouched.

**Interview:** "How do you make a `PriorityQueue` stable?" — You cannot, from inside; both sift loops break on equality. You make the comparator total instead: wrap each element with a monotonic `long` arrival number and add `thenComparingLong` as the secondary key, so equality never occurs. Costs about 32 bytes per element and one extra comparison per tie.

> A heap cannot be made stable, because both sifts halt on equality; you eliminate equality instead, with a monotonic `long` sequence number as a secondary comparison key held in a private wrapper.

---

### The bounded top-k, and the heap that points the wrong way on purpose

**Mental model.** To keep the k *greatest* elements of a stream, you need cheap access to the *weakest element you are currently keeping* — the threshold a new arrival must beat. That is the minimum of the kept set. So you use a **min**-heap, and evict its root. A max-heap puts the largest at the root, which is precisely the element you never want to touch.

**Why it exists.** `PriorityQueue` is unbounded: there is no capacity, `offer` always returns `true`, and nothing rejects an insertion. For a stream of `n` elements where you want the top 10, an unbounded heap costs `O(n)` memory and `O(n log n)` time; a bounded one costs `O(k)` and `O(n log k)`. At `n` in the billions and `k` = 10, that is the difference between feasible and not.

**How it works.**

```java
// BoundedTopK.java  —  a standalone third file
import java.util.AbstractCollection;
import java.util.Comparator;
import java.util.Iterator;
import java.util.Objects;

/**
 * Keeps the k greatest elements seen, in O(n log k) time and O(k) memory.
 * Uses a MIN-heap under the greatest-first comparator, so the root is the
 * weakest element currently kept -- the one a new arrival must beat.
 */
public final class BoundedTopK<E> extends AbstractCollection<E> {

    private final int k;
    private final MyPriorityQueue<E> weakestFirst;
    private final Comparator<? super E> order;

    /** @param order the ordering whose GREATEST k elements are kept */
    public BoundedTopK(int k, Comparator<? super E> order) {
        if (k < 1) throw new IllegalArgumentException("k < 1: " + k);
        this.k = k;
        this.order = Objects.requireNonNull(order);
        this.weakestFirst = new MyPriorityQueue<>(k, order);
    }

    /** @return true if the element was kept */
    @Override public boolean add(E e) {
        Objects.requireNonNull(e);
        if (weakestFirst.size() < k) {
            weakestFirst.offer(e);
            return true;
        }
        if (order.compare(e, weakestFirst.peek()) > 0) {
            weakestFirst.poll();
            weakestFirst.offer(e);
            return true;
        }
        return false;
    }

    /** The weakest element currently kept, or null while under capacity. */
    public E threshold() {
        return (weakestFirst.size() < k) ? null : weakestFirst.peek();
    }

    @Override public Iterator<E> iterator() { return weakestFirst.iterator(); }
    @Override public int size()             { return weakestFirst.size(); }
}
```

The field is named `weakestFirst` deliberately: it is a min-heap under the *same* comparator the caller gave, and the caller's comparator describes the ordering whose greatest elements are wanted. No `reversed()` anywhere — the inversion is in which end you evict from, not in the comparator.

**The `else if` guard is what makes it `O(n log k)` rather than `O(n log k)` with a constant factor of two.** Without it, every arriving element does an `offer` and then a `poll` — two `O(log k)` operations — even when it loses immediately. With it, a losing element costs one comparison against `peek()` and nothing else. On a stream where most elements lose, which is the whole point of top-k, that is the difference between `2n log k` and `n + (winners · 2 log k)`. Measured on a shuffled `1..100` with `k = 10`: only 32 of 100 elements were ever admitted, so 68 cost a single comparison each.

**`add` returns whether the element was kept**, which departs from `Collection.add`'s "true if this collection changed as a result of the call" only in spirit — it is in fact exactly that contract, since a rejected element does not change the collection. It happens to be the useful signal too, which is why the demo counts it.

**`threshold()` returns `null` while under capacity**, not the current minimum. The distinction matters to a caller doing early rejection upstream: "there is no threshold yet, admit everything" and "the threshold is `x`" are different states, and returning the minimum of a half-full heap would cause the caller to reject elements that should be kept.

`AbstractCollection` gives `isEmpty`, `contains`, `toArray`, `toString` and `addAll` from `iterator()` and `size()`. Note that iteration is the underlying heap's — so **unsorted**, and the transcript sorts before printing. That is the honest shape: the class's job is to *select* k elements, not to order them, and sorting k elements at the end is `O(k log k)` on a set that is already tiny.

**Insight:** the min-heap-for-max-k inversion catches almost everyone once, and the reason it is counterintuitive is that we describe the goal by what we keep rather than by what we discard. Restate the goal as "cheaply find and discard the weakest of my current keepers" and the min-heap is immediate.

Measured:

```
topK(10) of 1..100  = [91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
threshold           = 91, size 10, admitted 32 of 100
```

**Pitfall:** the wrong belief is "I want the largest, so I want a max-heap". The symptom, from [02](02-internals-b-traps.md), is measurable and total: the same loop against a max-heap keeps `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` — the ten *smallest* — because `poll` on a max-heap discards the biggest thing you have. Nothing throws; the result is simply the exact opposite of what was intended. The fix is the min-heap plus root eviction.

> To keep the k greatest elements, use a min-heap of size k and evict its root, because the element you need O(1) access to is the weakest of your keepers, not the strongest.

---

## Diff vs `java.util.PriorityQueue`

| Aspect | `java.util.PriorityQueue` (JDK 21) | `MyPriorityQueue` | Why the JDK bothers |
|---|---|---|---|
| Interfaces | `AbstractQueue<E>`, `java.io.Serializable` | `AbstractQueue<E>` only | serialization needs a `writeObject`/`readObject` pair; the algorithm needs neither |
| Bounds checks | none in the hot path; `// assert i >= 0 && i < size` as a comment on `removeAt` | identical | the invariants make them unnecessary, and an array store check catches the rest |
| `grow` | delegates to `jdk.internal.util.ArraysSupport.newLength` | inlines the same arithmetic | `ArraysSupport` is `jdk.internal` and unavailable outside the JDK; sharing centralises the `SOFT_MAX_ARRAY_LENGTH` clamp across `ArrayList`, `Vector`, `AbstractStringBuilder` and the `java.io` streams |
| Empty test in `poll` | `(result = (E) ((es = queue)[0])) != null` — one array load, doubles as the fetch | explicit `size == 0` | one fewer load on the hottest method; costs the null ban as a hard requirement |
| Null policy | bare `NullPointerException`, no message | `NullPointerException` naming the reason | `java.base` keeps exception construction allocation-free and relies on the frame naming the method; application code should not |
| Comparator dispatch in `poll` | inlined, bypassing the private `siftDown(int, E)` wrapper | calls the wrapper | one less frame on the hottest path; measurable only under a profiler |
| `heapify` comparator test | hoisted outside the loop, two separate loops | tested inside the loop | one fewer branch per iteration, and each `siftDown` call site stays monomorphic — the same argument as the sift duplication, one level up |
| Sift duplication | four methods, `Comparable` and `Comparator` variants | identical | JIT monomorphism; a merged version goes megamorphic across an application's several comparator types |
| Collection ctor null scan | conditional: `len == 1 \|\| comparator != null` | unconditional | the JDK relies on `heapify`'s first `compareTo` to throw; this build pays one pass for a diagnosable exception |
| `SortedSet` fast path | on the `PriorityQueue(SortedSet)` ctor, which adopts the set's comparator | requires `ss.comparator() == comparator` | the JDK's signature makes the check unnecessary; a separate comparator argument makes it essential |
| `Spliterator` | `PriorityQueueSpliterator` (line 843), `SIZED \| SUBSIZED`, midpoint index split | inherited `IteratorSpliterator` | exact sizes at every split node let fork-join pre-size the output array; the inherited one batches arithmetically from `BATCH_UNIT = 1024` |
| `forEach` | inherited | inherited | neither overrides it; both pay a virtual `next()` per element |
| `toArray(T[])` | overridden, two `arraycopy` calls | inherited, element-by-element | `arraycopy` is an intrinsic — one block move instead of n virtual calls |
| Serialization | `queue` transient; `writeObject` writes `size` then the elements in array order | absent | the array's slack is not written, so a queue at capacity 771 holding 3 elements serializes 3 elements |
| Serialization gotcha | `@SuppressWarnings("serial")` on `comparator` — a lambda comparator makes the queue unserializable *at runtime* | not applicable | the compiler cannot detect it; see [01](01-internals-a-heap.md) |
| `clone()` | absent in both | absent | `PriorityQueue` is not `Cloneable`; `new PriorityQueue<>(other)` is the copy route |
| Thread safety | none | none | `PriorityBlockingQueue` is the answer, and it reuses the same sift code under one `ReentrantLock` — see [02](02-internals-b-traps.md) |
| Stability | none | none, plus `StablePriorityQueue` as a companion | nothing in the `Queue` contract requires it and the JDK cannot add a hidden field to an element type it does not own |
| Bounded | no | no, plus `BoundedTopK` as a companion | bounding is a policy, not a data-structure property |
| `decreaseKey` | absent | absent | would be O(n) without a side index, so the API would advertise a bound it cannot meet |

The honest summary: the algorithmic core here **is** the JDK's, and the measured layouts prove it — identical heap arrays, identical capacity ladder, identical behaviour on the awkward `removeAt` case. What is missing is breadth (serialization, a real spliterator, the bulk-operation overrides) and a handful of micro-optimisations on the hottest paths (the folded empty test in `poll`, the hoisted comparator test in `heapify`, the bypassed sift wrapper). None of those is a correctness difference. The two genuine *design* differences are the unconditional null scan and the stricter `SortedSet` fast-path check, and both were chosen deliberately — the first trading a linear pass for a diagnosable error, the second forced by taking the comparator as a separate constructor argument.

---

## Compile and run

```
$ javac -Xlint:all MyPriorityQueue.java StablePriorityQueue.java \
        BoundedTopK.java PQDemo.java
$ java PQDemo
```

JDK 21.0.7, zero warnings, zero errors. Full output:

```
fresh capacity      = 11
heap array          = [1, 3, 2, 5, 9, 8, 7]
jdk heap array      = [1, 3, 2, 5, 9, 8, 7]
layouts match       = true
drain order         = [1, 2, 3, 5, 7, 8, 9]
heapify array       = [1, 3, 2, 4, 8, 7, 6, 9, 5]
jdk heapify array   = [1, 3, 2, 4, 8, 7, 6, 9, 5]
heapify drain       = [1, 2, 3, 4, 5, 6, 7, 8, 9]
capacity ladder     = 11 -> 24 -> 50 -> 102 -> 153 -> 229 -> 343 -> 514 -> 771
tricky heap         = [6, 12, 46, 33, 18, 80, 73, 47, 34, 95, 25]
visited (rm step 5) = [6, 12, 46, 33, 18, 80, 73, 47, 34, 95, 25] count 11
after removal       = [6, 12, 25, 33, 18, 46, 73, 47, 34, 95] size 10
all 10 survivors    = true
contains(46)        = true, remove(46) = true, size 9
mutate while iterating = ConcurrentModificationException
offer(null)         = NPE: MyPriorityQueue prohibits null elements: queue[0] == null is the emptiness test
unstable drain      = agfedcb
stable drain        = a b c d e f g
stable mixed drain  = lo1 lo2 mid hi1 hi2
topK(10) of 1..100  = [91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
threshold           = 91, size 10, admitted 32 of 100
```

Four lines carry the verification. `layouts match = true` and the two identical `heapify array` lines say the build reproduces `java.util.PriorityQueue`'s array layout exactly, not merely an equivalent heap. The `capacity ladder` matches the JDK's measured ladder. And `all 10 survivors = true` says the iterator delivered eleven elements from an eleven-element heap with one removal, on the specific input where `removeAt` returns non-null — the case the `forgetMeNot` machinery exists for.

The demo source is 115 lines of `main` and reflection-free (`backingArray()` is the package-private test hook), so it is not reproduced here; every line of the output above traces to one of the three classes, which are complete across [03](03-build-my-priority-queue.md), [04](04-build-my-priority-queue-b-operations-and-iterator.md) and this file.

**Unverified:** no throughput figures are published for this build. A meaningful comparison against `java.util.PriorityQueue` — where the differences are a folded array load, a hoisted branch and a bypassed frame — needs a JMH harness with a named CPU, a named JDK build and `-prof perfnorm`, because those three differences are exactly the size that a wall-clock loop in a `main` cannot resolve from JIT warm-up noise. Functional equivalence is verified; performance equivalence is not.

---

## Pitfalls

### Putting the sequence number on the element

**Wrong**

```java
record Task(String name, int prio, long seq) {}
var q = new MyPriorityQueue<Task>(
    Comparator.comparingInt(Task::prio).thenComparingLong(Task::seq));
```

Works, and leaks. Two consequences. The class now only works for element types you can modify, so it is useless for `String`, `Integer`, or anything from a library. And `Task`'s generated `equals` and `hashCode` now include `seq`, so two logically-identical tasks are unequal in every `HashSet`, `HashMap` key position and `distinct()` call in the program — a change made for the queue's benefit, paid for everywhere.

**Right**

```java
private record Stamped<E>(E value, long seq) {}     // private to the queue
```

The stamp is visible only to this queue's comparator; the element's own `equals`, `hashCode` and `compareTo` are untouched, and the public signature is a plain `Queue<E>`.

**Why people believe it:** it is fewer objects and less indirection, and the tiebreak field genuinely is a property of "this task's arrival". It is a property of the *queueing*, not of the task.

### An `int` sequence number

**Wrong**

```java
private int counter;                            // int, not long

@Override public boolean offer(E e) {
    return heap.offer(new Stamped<>(Objects.requireNonNull(e), counter++));
}
```

Correct for 2,147,483,647 insertions, then silently inverted. At the wrap, `counter` becomes `Integer.MIN_VALUE`, so every element inserted afterwards compares as *earlier* than everything inserted before — within each priority, the queue reverses. On a service inserting a thousand events per second that is about 25 days to the bug, which is long enough to reach production and short enough to happen.

**Right**

```java
private long counter;                               // and thenComparingLong
```

A `long` at a million insertions per second lasts roughly 292,000 years. Note also that `thenComparingLong` uses `Long.compare` rather than subtraction, so even at the extremes there is no overflow in the comparison itself — the same reason `a - b` is never a valid comparator ([D-14](../diagrams/D-14-subtract-comparator-overflow.svg)).

**Why people believe it:** `int` is the default counter type, and "we will never insert two billion things" is usually true of a single request and usually false of a long-lived process.

### Doing `offer` then `poll` unconditionally in top-k

**Wrong**

```java
@Override public boolean add(E e) {
    weakestFirst.offer(e);
    if (weakestFirst.size() > k) weakestFirst.poll();
    return true;
}
```

Correct results, twice the work, and a wrong return value. Every element — including the 68 out of 100 that lose immediately in the measured run — pays a full `O(log k)` `siftUp` and a full `O(log k)` `siftDown` instead of one comparison. And `add` now always returns `true`, so a caller cannot tell whether the element was kept.

**Right**

```java
    if (weakestFirst.size() < k) { weakestFirst.offer(e); return true; }
    if (order.compare(e, weakestFirst.peek()) > 0) {
        weakestFirst.poll(); weakestFirst.offer(e); return true;
    }
    return false;
```

**Why people believe it:** "add then trim" is the obvious shape and it is what most top-k snippets on the internet do. The guard is free — `peek()` is an array read — and it turns the common case from two logarithmic operations into one comparison.

---

## Cheat sheet

| Piece | This build |
|---|---|
| Stable queue strategy | make equality impossible; do not touch the sifts |
| Wrapper | `private record Stamped<E>(E value, long seq)` — private, so the element is untouched |
| Comparator | `comparing(Stamped::value, byPriority).thenComparingLong(Stamped::seq)` |
| Two-arg `comparing` | key extractor **plus** a comparator for the key — what allows an arbitrary `Comparator<? super E>` |
| `thenComparingLong` | not `thenComparing` — the boxing form allocates a `Long` per comparison, ~`2 log₂ n` per `poll` |
| Counter type | `long`. An `int` inverts the order within each priority after 2³¹ insertions |
| Counter, not atomic | the heap is not thread-safe either; an `AtomicLong` would only look safe |
| Stable cost | ~32 bytes per element for the wrapper, plus one comparison per former tie |
| Measured | `agfedcb` unstable → `a b c d e f g` stable; mixed priorities `lo1 lo2 mid hi1 hi2` |
| Top-k strategy | **min**-heap of size k, evict the root |
| Why min-heap | the root must be the weakest keeper — the threshold a new arrival must beat |
| No `reversed()` | the inversion is in which end you evict from, not in the comparator |
| The `else if` guard | a losing element costs one comparison, not `offer` + `poll` |
| Measured | 32 of 100 admitted; the other 68 cost one comparison each |
| `threshold()` | `null` while under capacity — "no threshold yet" is a distinct state from a value |
| Top-k cost | `O(n log k)` time, `O(k)` memory, versus `O(n log n)` and `O(n)` for a full sort |
| Top-k iteration | the heap's, so **unsorted**; sort the k results if order matters, `O(k log k)` |
| Verified | heap layout, capacity ladder and awkward-`removeAt` behaviour identical to the JDK |
| Not verified | throughput — no JMH figures published |

---

## Self-test

**Q1.** Why can a heap not be made stable by changing the sift loops?

<details><summary>Answer</summary>

Because both loops halt on equality — `siftUp` breaks on `compareTo(parent) >= 0`, `siftDown` on `compareTo(child) <= 0` — and there is nothing to break the tie with. Changing `>=` to `>` would make equal elements keep swapping past each other, which is not stability, it is churn, and it would not terminate consistently. Recording arrival order would require a field on the element, which the heap does not own: the JDK cannot add a hidden `long` to `String` or to a caller's `Task`. The only route is to make the comparator total so equality never occurs — which is a change to the caller's ordering, not to the data structure.

</details>

**Q2.** Why is the sequence number in a private wrapper record rather than on the element?

<details><summary>Answer</summary>

Two reasons. Portability: a field on the element means the queue only works for types you can modify, so `String`, `Integer` and anything from a library are excluded. Contamination: adding `seq` to a record changes its generated `equals` and `hashCode`, so two logically-identical elements become unequal in every `HashSet`, every `HashMap` key position and every `distinct()` in the program — a cost paid everywhere for the queue's benefit. A `private record Stamped<E>` is visible only to this queue's comparator, keeps the public signature a plain `Queue<E>`, and leaves the element's own contracts untouched.

</details>

**Q3.** What breaks if the arrival counter is an `int`?

<details><summary>Answer</summary>

After 2,147,483,647 insertions it wraps to `Integer.MIN_VALUE`, and every element inserted after the wrap compares as *earlier* than everything inserted before it. Within each priority the queue silently reverses. On a service inserting a thousand events a second, that is around 25 days — long enough to reach production, short enough to actually happen. A `long` at a million per second lasts about 292,000 years. Note the second half of the defence: `thenComparingLong` uses `Long.compare`, not subtraction, so the comparison itself cannot overflow even at the extremes — the same reason `a - b` is never a valid comparator.

</details>

**Q4.** To keep the k greatest elements, which heap and why?

<details><summary>Answer</summary>

A **min**-heap of size k, evicting its root. The operation that has to be cheap is "find and discard the weakest element I am currently keeping", because that is the threshold a new arrival must beat — and the weakest keeper is the minimum. A min-heap puts it at the root, so `peek()` is the comparison and `poll()` is the eviction. A max-heap puts the *largest* at the root, so `poll()` throws away exactly what you were trying to keep: measured, the same loop against a max-heap keeps `[1..10]` from a shuffled `1..100` instead of `[91..100]`. Restating the goal as "discard the weakest keeper" rather than "keep the largest" makes the min-heap immediate.

</details>

**Q5.** What does the `else if (order.compare(e, weakestFirst.peek()) > 0)` guard buy?

<details><summary>Answer</summary>

It turns the common case from two logarithmic operations into one comparison. Without the guard, every arriving element pays a full `siftUp` on `offer` and a full `siftDown` on the subsequent `poll` — `2 log k` comparisons — even when it loses immediately. With it, a losing element costs one `peek()` (an array read) and one comparison. On a top-k stream most elements lose, which is the entire premise: measured on a shuffled `1..100` with `k = 10`, only 32 elements were ever admitted, so 68 took the cheap path. It also gives `add` a meaningful return value — whether the element was kept — which the unconditional form cannot provide.

</details>

**Q6.** Why does `threshold()` return `null` while the heap is under capacity, instead of the current minimum?

<details><summary>Answer</summary>

Because "there is no threshold yet, admit everything" and "the threshold is `x`" are different states, and a caller doing early rejection upstream needs to tell them apart. Returning the minimum of a half-full heap would make the caller reject elements that ought to be kept — the heap has spare capacity, so *every* element should be admitted until it is full, regardless of how it compares to what is already there. Returning `null` communicates "no constraint" unambiguously, and the `add` method's own first branch mirrors it: `size() < k` admits without comparing.

</details>

**Q7.** Name the two genuine design differences between this build and `java.util.PriorityQueue`, as opposed to the micro-optimisations.

<details><summary>Answer</summary>

The unconditional null scan in the `Collection` constructor, and the stricter `SortedSet` fast-path check. The JDK scans for nulls only when `len == 1` or a comparator is present, because otherwise `heapify`'s first `compareTo` throws anyway — this build pays a whole extra linear pass to get an exception thrown from the constructor and naming the class, rather than one thrown from inside a static sift method. And the JDK's `SortedSet` fast path lives on a constructor that *adopts* the set's comparator, so the orderings agree by construction; this build takes the comparator separately, so it must check `ss.comparator() == comparator` or risk building a heap whose invariant is false from birth. Everything else — the folded empty test in `poll`, the hoisted comparator test in `heapify`, the bypassed sift wrapper, `ArraysSupport` delegation — is a micro-optimisation or an access restriction, not a design difference.

</details>

**Q8.** The transcript's `layouts match = true` line compares array layouts against the JDK. Should a test do that?

<details><summary>Answer</summary>

No — and the line is evidence, not an assertion to copy. A valid heap is not unique: the same input can produce different valid layouts, and nothing in `PriorityQueue`'s javadoc specifies the array order. The layouts agree here because the build reproduces the JDK's algorithm with the same tie-breaking, so the comparison is a useful check that the reimplementation is faithful *to this JDK* — exactly the right thing for a study build to measure and exactly the wrong thing for a production test to assert. A test should assert on drained order, which is the specified behaviour. [01b](01b-internals-removeat-and-iteration.md) has the pitfall entry.

</details>

---

**Leaves covered:** 4.5.7, 4.5.8, 4.5.9 (3 leaves)
**Leaves deferred:** none — 4.5.1, 4.5.2, 4.5.4 and 4.5.5 are in [03-build-my-priority-queue.md](03-build-my-priority-queue.md); 4.5.3 and 4.5.6 are in [04-build-my-priority-queue-b-operations-and-iterator.md](04-build-my-priority-queue-b-operations-and-iterator.md)
**Diagrams included:** none new — the `PriorityQueue` pictures D-80 to D-84 are embedded in [01-internals-a-heap.md](01-internals-a-heap.md) and [01b-internals-removeat-and-iteration.md](01b-internals-removeat-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 437
