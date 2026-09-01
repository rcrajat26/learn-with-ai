# 02 Java Collections — `PriorityQueue` — INTERNALS (§4.5 `MyPriorityQueue<E>` — fields, growth, the sifts and `heapify`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [priority-queue/02-internals-b-traps.md](02-internals-b-traps.md) · Next: [priority-queue/04-build-my-priority-queue-b-operations-and-iterator.md](04-build-my-priority-queue-b-operations-and-iterator.md)

Reading a heap teaches you the invariant. Writing one teaches you that almost every line exists to keep the invariant true across an exception, an equal comparison, or a removal from the middle.

**The class is presented in two parts, with two companion classes in a third.** `MyPriorityQueue.java` is the concatenation, in order, of every code block labelled **`MyPriorityQueue.java`** in this file followed by every such block in [04](04-build-my-priority-queue-b-operations-and-iterator.md). `StablePriorityQueue.java` and `BoundedTopK.java` are two further standalone files, built in [05](05-build-my-priority-queue-c-variants-and-diff.md), which also carries the diff table and the full compile-and-run transcript. All four build under JDK 21.0.7 with `-Xlint:all` and zero warnings.

This file covers the class head, the fields, the four-plus-one constructors, `grow`, both sift methods in both variants, and `heapify`.

---

## The class head, the constants and the fields

```java
// MyPriorityQueue.java
import java.util.AbstractQueue;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Collection;
import java.util.Comparator;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.NoSuchElementException;
import java.util.SortedSet;

/**
 * A reimplementation of java.util.PriorityQueue: a min-heap embedded in an
 * Object[] as a complete binary tree, breadth-first.
 */
public class MyPriorityQueue<E> extends AbstractQueue<E> {

    private static final int DEFAULT_INITIAL_CAPACITY = 11;
    private static final int MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8;

    /** The heap. Occupies [0, size); every other slot is null. */
    Object[] queue;

    int size;

    /** null means natural ordering. Final: the ordering never changes. */
    private final Comparator<? super E> comparator;

    transient int modCount;
```

`extends AbstractQueue<E>` is doing real work, and it is the reason this class has only three entry points. `AbstractQueue` implements `add` as "`offer`, or throw `IllegalStateException` if it returned false", `remove()` as "`poll`, or throw `NoSuchElementException`", `element()` as "`peek`, or throw", and `addAll` as an `add` loop. `AbstractCollection` above it supplies `isEmpty`, `toArray`, `containsAll`, `removeAll`, `retainAll` and `toString` in terms of `iterator()` and `size()`. So implementing `offer`, `poll`, `peek`, `size()` and `iterator()` yields the whole `Queue` surface — which is exactly what the JDK does, and it is why an `addAll` on a `PriorityQueue` is an offer loop rather than a `heapify` (see [01](01-internals-a-heap.md)).

`comparator` is **`final`**. That is not decoration: it means the ordering that decided every element's position can never change under the heap. A `setComparator` would invalidate the entire array in one call, and there would be no cheap way to detect it — the same failure mode as mutating an element's priority, but applied to every element at once. Making the field final removes the possibility.

`queue` and `size` are package-private rather than `private`, matching the JDK, so the nested `Itr` reaches them without a synthetic accessor method on a hot path.

`modCount` is present here, unlike in [`MyArrayDeque`](../array-deque/02-build-my-array-deque.md). The reason is that a heap's mutations *move other elements*: an `offer` can relocate every element on one root-to-leaf path, and a `removeAt` can relocate one arbitrarily far. There is no cheap structural check like `ArrayDeque`'s "is this slot null" that would catch that, so a counter is the only workable detection.

`MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8` = 2,147,483,639, the eight-word slack some VMs reserve for the array header. The real `PriorityQueue` gets this from `ArraysSupport.newLength`, which is `jdk.internal` and unavailable outside the JDK, so this build carries its own copy — the same reason `ArrayDeque` does.

---

## The constructors, and the one that skips `heapify`

```java
// MyPriorityQueue.java
    public MyPriorityQueue() {
        this(DEFAULT_INITIAL_CAPACITY, null);
    }

    public MyPriorityQueue(int initialCapacity) {
        this(initialCapacity, null);
    }

    public MyPriorityQueue(Comparator<? super E> comparator) {
        this(DEFAULT_INITIAL_CAPACITY, comparator);
    }

    public MyPriorityQueue(int initialCapacity, Comparator<? super E> comparator) {
        if (initialCapacity < 1)
            throw new IllegalArgumentException("initialCapacity < 1: " + initialCapacity);
        this.queue = new Object[initialCapacity];
        this.comparator = comparator;
    }

    /** Takes the O(n) heapify path, or skips it when the input is already ordered. */
    public MyPriorityQueue(Collection<? extends E> c, Comparator<? super E> comparator) {
        this.comparator = comparator;
        Object[] es = c.toArray();
        if (c.getClass() != java.util.ArrayList.class)
            es = Arrays.copyOf(es, es.length, Object[].class);
        for (Object e : es)
            if (e == null)
                throw new NullPointerException("MyPriorityQueue prohibits null elements");
        this.queue = (es.length == 0) ? new Object[1] : es;
        this.size = es.length;
        boolean alreadyOrdered =
            (c instanceof SortedSet<?> ss && ss.comparator() == comparator)
            || (c instanceof MyPriorityQueue<?> pq
                && pq.getClass() == MyPriorityQueue.class
                && pq.comparator == comparator);
        if (!alreadyOrdered)
            heapify();
    }

    public Comparator<? super E> comparator() {
        return comparator;
    }
```

Four delegating constructors funnelling into one, plus the interesting one.

`initialCapacity < 1` throws. There is no reserved slot here — unlike `ArrayDeque`, a heap occupies `[0, size)` and needs no sentinel — so a zero-length array would make `queue[0]` throw `ArrayIndexOutOfBoundsException` on the first `peek()`, and `grow`'s `oldCapacity + max(min - old, old + 2)` from 0 would be arithmetically fine but pointless. Rejecting is cleaner than special-casing.

**The `Collection` constructor is where the O(n) build lives, and it is the only route to it.** Four things happen in order, and each is a defence:

`c.toArray()` then `Arrays.copyOf(es, es.length, Object[].class)` **unless** `c` is exactly an `ArrayList`. `toArray()` is not contractually required to return an `Object[]` — `Arrays.asList("x").toArray()` historically returned a `String[]` — so without the re-typing, the heap would be backed by a narrow array and a later `offer` of an incompatible element would throw `ArrayStoreException` from inside `siftUp`, with nothing in the message connecting it to the constructor. The `getClass() != ArrayList.class` exemption is the JDK's own: `ArrayList` is known to return a genuine `Object[]`, so the copy is skipped for the common case. Exactly one array copy in the worst case; zero in the common one. This is the same covariance hole as [D-02](../diagrams/D-02-array-covariance-hole.svg).

The null scan runs unconditionally here, where the JDK's runs only when `len == 1` or a comparator is present. The JDK can afford the shortcut because `heapify`'s first `compareTo` will throw `NullPointerException` on a null anyway; this build pays one extra linear pass to get a *diagnosable* exception instead of one thrown from inside a sift loop. Legibility over a pass that is dwarfed by the `heapify` that follows.

`(es.length == 0) ? new Object[1] : es` — an empty input must still leave a non-empty array, or `peek()` indexes out of bounds. The JDK calls this `ensureNonEmpty`.

`alreadyOrdered` is the fast path, and it is stricter than the JDK's in one useful way. A `SortedSet` qualifies **only if its comparator is the same one** — `ss.comparator() == comparator`, reference identity. The JDK's `initElementsFromCollection` takes any `SortedSet` on the `PriorityQueue(SortedSet)` constructor and trusts the caller, which is sound there because that constructor also *adopts* the set's comparator. Here, where the comparator is a separate argument, a `TreeSet` ordered by name handed to a queue ordered by priority is ascending in the wrong dimension, and skipping `heapify` would produce a queue whose invariant is false from birth. The `MyPriorityQueue` arm uses `getClass() == MyPriorityQueue.class` rather than `instanceof` for the JDK's reason: a subclass could have overridden `toArray`.

**Insight:** both fast paths reduce to the same question — "is this array already a valid heap under *my* comparator?" — and both answer it by identity, never by checking. Checking would be O(n), which is what `heapify` costs anyway, so a check would buy nothing.

**Pitfall:** the wrong belief is that `addAll` gets you the O(n) build. It does not: `AbstractQueue.addAll` is an `add` loop, so it is `O(n log n)`. The symptom is a startup path that is a log-factor slower than expected and shows `siftUp` at the top of a profile. The fix is to use the `Collection` constructor, which is the only entry point to `heapify` — and note that means you cannot combine "build from a collection in O(n)" with "add more later" cheaply; the later additions are `O(log n)` each regardless.

---

### `grow`, and the arithmetic `ArraysSupport` hides

**Mental model.** A heap never wraps and never fragments, so growth is one `Arrays.copyOf` and nothing else. All the subtlety is in choosing the new length without overflowing an `int`.

**How it works.**

```java
// MyPriorityQueue.java
    private void grow(int minCapacity) {
        int oldCapacity = queue.length;
        int preferred = (oldCapacity < 64) ? (oldCapacity + 2) : (oldCapacity >> 1);
        int newCapacity = oldCapacity + Math.max(minCapacity - oldCapacity, preferred);
        if (newCapacity - MAX_ARRAY_SIZE > 0) {
            if (minCapacity < 0) throw new OutOfMemoryError("queue too big");
            newCapacity = Math.max(minCapacity, MAX_ARRAY_SIZE);
        }
        queue = Arrays.copyOf(queue, newCapacity);
    }
```

The real `PriorityQueue.grow` is three lines because it delegates:

```java
    // java.util.PriorityQueue, JDK 21, lines 291-299
    int newCapacity = ArraysSupport.newLength(oldCapacity,
            minCapacity - oldCapacity, /* minimum growth */
            oldCapacity < 64 ? oldCapacity + 2 : oldCapacity >> 1
                                       /* preferred growth */);
```

`ArraysSupport.newLength(oldLength, minGrowth, prefGrowth)` computes `oldLength + Math.max(minGrowth, prefGrowth)` and, if that exceeds `SOFT_MAX_ARRAY_LENGTH`, falls back to a `hugeLength` helper. This build inlines the same shape. Three details are load-bearing.

`Math.max(minCapacity - oldCapacity, preferred)` is why a bulk demand overrides the growth factor. `offer` always calls `grow(size + 1)`, so `minCapacity - oldCapacity` is 1 and `preferred` wins — the queue grows by the policy. But a caller who needs 10,000 slots at once gets exactly what they asked for rather than a dozen successive resizes.

`preferred` is the growth *amount*, not the target, and the threshold is capacity 64: `oldCapacity + 2` below it, `oldCapacity >> 1` at or above. Below 64, `old + 2` is slightly more than doubling, which walks a small queue up quickly; at and above 64 the factor is 1.5, chosen for its allocator behaviour rather than its copy count.

**Note which class this policy is shared with, because the helper and the policy are different things.** `PriorityQueue` and `ArrayDeque` have the same *policy* — the two-phase `< 64 ? +2 : ×1.5` jump. `ArrayList` does not: it passes a flat `oldCapacity >> 1` as its preferred growth, with no doubling-while-small phase. What all three share is the *helper*, `ArraysSupport.newLength`, along with `Vector`, `AbstractStringBuilder` and the `java.io` streams. So the 1.5× allocator argument in [array-list/04](../array-list/04-amortised-analysis.md) transfers to the large-capacity phase here, but the amortised constant does not transfer unchanged — that file derives 3 credits per `add` at `g = 2` and 4 at `g = 1.5`, and the doubling-while-small phase changes the series over the first few resizes. Below capacity 64 this queue is not growing at 1.5× at all.

```
capacity ladder     = 11 -> 24 -> 50 -> 102 -> 153 -> 229 -> 343 -> 514 -> 771
```

11 + 13 = 24, 24 + 26 = 50, 50 + 52 = 102 — then 102 is at or above 64, so 102 + 51 = 153, 153 + 76 = 229, and 1.5× onward.

`newCapacity - MAX_ARRAY_SIZE > 0` rather than `newCapacity > MAX_ARRAY_SIZE` is the JDK's "overflow-conscious code" idiom. If `oldCapacity + preferred` has already wrapped past `Integer.MAX_VALUE` it is negative, and a negative value is not `> MAX_ARRAY_SIZE`, so the plain comparison waves the overflow straight through into `new Object[negative]`. Written as a subtraction, the wraparound is detected. `minCapacity < 0` then distinguishes "we genuinely cannot represent this" (`OutOfMemoryError`) from "we are above the soft cap but the request is representable" (clamp and let the allocation decide).

**Pitfall:** the wrong belief is that `if (newCapacity > MAX_ARRAY_SIZE)` is equivalent and clearer. It is clearer and it is wrong: for `oldCapacity` near 1.4 billion, `oldCapacity + (oldCapacity >> 1)` overflows to a negative number, the guard does not fire, and `Arrays.copyOf` throws `NegativeArraySizeException` — a confusing failure for a program that was simply running out of heap. The fix is the subtraction form, and it is worth recognising on sight: it appears in `ArrayList`, `Vector`, `ArrayDeque`, `AbstractStringBuilder` and here.

> Growing a heap is one `Arrays.copyOf`; the only subtlety is computing the new length as `old + max(minGrowth, prefGrowth)` with the overflow test written as a subtraction so it survives `int` wraparound.

---

### The sifts, duplicated on purpose

**Mental model.** Both sifts move a *hole*, not an element. `siftUp` is handed an index and a value; it walks toward the root pulling each too-large parent down into the hole, and writes the value once, at the end. `siftDown` walks toward the leaves pulling the smaller child up. The element being placed lives in a local the whole time. One array write per level plus one, instead of two per level for a swap loop.

**Why the duplication.** Each sift exists twice, character for character identical except for the comparison. It is the single clearest JIT-driven duplication in `java.util`, and the JDK's own comment at lines 626–632 of `PriorityQueue.java` states the reason: "To simplify and speed up coercions and comparisons, the Comparable and Comparator versions are separated into different methods that are otherwise identical."

**How it works.**

```java
// MyPriorityQueue.java
    private void siftUp(int k, E x) {
        if (comparator != null) siftUpUsingComparator(k, x, queue, comparator);
        else siftUpComparable(k, x, queue);
    }

    @SuppressWarnings("unchecked")
    private static <T> void siftUpComparable(int k, T x, Object[] es) {
        Comparable<? super T> key = (Comparable<? super T>) x;
        while (k > 0) {
            int parent = (k - 1) >>> 1;
            Object e = es[parent];
            if (key.compareTo((T) e) >= 0) break;
            es[k] = e;
            k = parent;
        }
        es[k] = key;
    }

    @SuppressWarnings("unchecked")
    private static <T> void siftUpUsingComparator(int k, T x, Object[] es,
                                                 Comparator<? super T> cmp) {
        while (k > 0) {
            int parent = (k - 1) >>> 1;
            Object e = es[parent];
            if (cmp.compare(x, (T) e) >= 0) break;
            es[k] = e;
            k = parent;
        }
        es[k] = x;
    }
```

`while (k > 0)` is what makes `(k - 1) >>> 1` safe: at `k == 0` the expression evaluates to 2147483647, which is not a valid index, so the guard must come first. `>>>` rather than `>>` keeps the value non-negative for every input rather than relying on the guard alone.

`>= 0` breaks the loop, so **equal stops the climb**. That single character is half of why the heap is unstable — [02](02-internals-b-traps.md) works it through, and [05](05-build-my-priority-queue-c-variants-and-diff.md) fixes it by making equality impossible.

The methods are `static` and take `es` as a parameter. Both matter. Static means no receiver to reason about, so the JIT sees a pure function of its arguments; taking the array as a parameter means the caller has already loaded `queue` into a local and the loop does not re-read a field it cannot prove unchanged. The `<T>` shadows the class's `E` — necessary, because a static method cannot see the class type parameter — and is what the JDK does too.

```java
// MyPriorityQueue.java
    private void siftDown(int k, E x) {
        if (comparator != null) siftDownUsingComparator(k, x, queue, size, comparator);
        else siftDownComparable(k, x, queue, size);
    }

    @SuppressWarnings("unchecked")
    private static <T> void siftDownComparable(int k, T x, Object[] es, int n) {
        Comparable<? super T> key = (Comparable<? super T>) x;
        int half = n >>> 1;
        while (k < half) {
            int child = (k << 1) + 1;
            Object c = es[child];
            int right = child + 1;
            if (right < n && ((Comparable<? super T>) c).compareTo((T) es[right]) > 0)
                c = es[child = right];
            if (key.compareTo((T) c) <= 0) break;
            es[k] = c;
            k = child;
        }
        es[k] = key;
    }

    @SuppressWarnings("unchecked")
    private static <T> void siftDownUsingComparator(int k, T x, Object[] es, int n,
                                                   Comparator<? super T> cmp) {
        int half = n >>> 1;
        while (k < half) {
            int child = (k << 1) + 1;
            Object c = es[child];
            int right = child + 1;
            if (right < n && cmp.compare((T) c, (T) es[right]) > 0)
                c = es[child = right];
            if (cmp.compare(x, (T) c) <= 0) break;
            es[k] = c;
            k = child;
        }
        es[k] = x;
    }
```

`half = n >>> 1` is the index of the first leaf, so `k < half` reads "still a non-leaf" and removes the need for any bounds check on `child` — a node before `half` always has at least a left child. `n` is passed in rather than read from `size`, which is essential: `heapify` and `poll` both call `siftDown` with an `n` that is not the current `size` at the moment of the call.

The two lines that people leave out when writing a heap from memory:

```java
            int right = child + 1;
            if (right < n && ((Comparable<? super T>) c).compareTo((T) es[right]) > 0)
                c = es[child = right];
```

`right < n` because the last non-leaf may have only a left child. Then the two children are compared and `c`/`child` reassigned to the right one if the left is larger. **That is one comparison to pick the child and a second to decide whether to descend — two per level**, against `siftUp`'s one, which is why `poll` is roughly twice as comparison-heavy per level as `offer`.

`c = es[child = right]` assigns `child` inside the array index, so the loop's next `k = child` is already correct. Terse, and it is what the JDK writes.

The sifts do not touch `modCount`, do not touch `size`, and do not allocate. Every state change lives in the caller, which is what makes exception safety possible: if a comparison throws mid-sift, the array holds a partially-shifted path but `size` and the caller's bookkeeping are untouched, so the queue is left with a valid — if differently-shaped — heap rather than a corrupt one.

> Both sifts move a hole rather than swapping, take the array and the length as parameters so nothing is re-read from a field, and exist twice so that each call site sees one comparison implementation and stays monomorphic.

---

### `heapify`: Floyd's construction, backwards

```java
// MyPriorityQueue.java
    /** Floyd's O(n) construction: sink from the last non-leaf back to the root. */
    @SuppressWarnings("unchecked")
    private void heapify() {
        final Object[] es = queue;
        final int n = size;
        for (int i = (n >>> 1) - 1; i >= 0; i--) {
            if (comparator == null) siftDownComparable(i, (E) es[i], es, n);
            else siftDownUsingComparator(i, (E) es[i], es, n, comparator);
        }
    }
```

`(n >>> 1) - 1` is the last non-leaf. For `n = 9` that is index 3; indices 4 through 8 are leaves and are already trivially valid heaps of one node, so there is nothing to do to them.

**Backwards is not a stylistic choice — it is the precondition.** `siftDown(i, es[i], es, n)` assumes both subtrees of `i` are already valid heaps and only the root of the combined subtree might be out of place. Running the loop forwards would sink into unheapified subtrees, and the "smaller child" it picked would be meaningless. Descending `i` guarantees that by the time index `i` is processed, every index above `i` — which is where all of `i`'s descendants live, since children are always at higher indices — has been processed.

The JDK hoists the comparator test outside the loop and writes two loops; this build tests inside. Functionally identical; the JDK's form is one fewer branch per iteration and keeps each `siftDown` call site monomorphic, which is the same argument as the sift duplication itself, applied one level up. Worth knowing which is which if you are reading a profile.

**The O(n) argument, worked.** Index the levels by height `h`, leaves at `h = 0`. A complete tree of `n` nodes has at most `⌈n / 2^{h+1}⌉` nodes at height `h`, and a node at height `h` sinks at most `h` levels. So

```
work  ≤  Σ_{h=0}^{log n} (n / 2^{h+1}) · h  =  (n/2) · Σ_{h=0}^{log n} h / 2^h
```

and `Σ_{h≥0} h/2^h = 2`, from `Σ h x^h = x/(1-x)²` evaluated at `x = 1/2`: `(1/2)/(1/4) = 2`. The bound is `(n/2) · 2 = n`.

The inversion against the offer loop is the whole point. In an offer loop each element enters at a *leaf* and climbs, and half of all nodes are leaves — so the longest possible movement applies to the largest group, and the sum is `Θ(n log n)`. In `heapify` the longest movement applies to the *fewest* nodes. Same tree, same cost per level, opposite distribution. [array-list/04](../array-list/04-amortised-analysis.md) owns leaf 3.2.13 and this series; it is the authority if the two derivations ever drift apart.

Measured against the JDK on the same nine-element input:

```
heapify array       = [1, 3, 2, 4, 8, 7, 6, 9, 5]
jdk heapify array   = [1, 3, 2, 4, 8, 7, 6, 9, 5]
heapify drain       = [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

Byte-identical layout, not just an equivalent heap — which is expected, since the code is the same algorithm with the same tie-breaking, but it is worth checking rather than assuming. Note that this equality is *not* something you should rely on in a test; a valid heap is not unique, and [01b](01b-internals-removeat-and-iteration.md) has the pitfall entry for asserting on it.

> `heapify` sinks from `(size >>> 1) - 1` down to 0 — backwards, because `siftDown` requires both subtrees to be valid already — and is O(n) because the nodes that can sink furthest are the rarest, with `Σ h/2^h` converging to 2.

---

## Pitfalls

### Reading `size` inside `siftDown` instead of passing `n`

**Wrong**

```java
// as an instance method, reading the field instead of taking a parameter
private <T> void siftDownComparable(int k, T x, Object[] es) {
    int half = size >>> 1;                  // the field, not a parameter
    while (k < half) {
        int child = (k << 1) + 1;
        Object c = es[child];
        int right = child + 1;
        if (right < size && compare(c, es[right]) > 0)   // the field again
            c = es[child = right];
        if (compare(x, c) <= 0) break;
        es[k] = c;
        k = child;
    }
    es[k] = x;
}
```

Made an instance method reading the field, it compiles and then fails in two places. `poll` decrements `size` *before* sifting, so reading the field would be correct there by accident; `heapify` calls `siftDown` repeatedly with the full `n` while `size` is already the final value, which is also fine — but `removeAt` decrements `size` and then sifts within the *new* bounds, and any future caller that sifts a sub-range gets silent corruption. Passing `n` makes the contract explicit and lets the method be static.

**Right**

```java
private static <T> void siftDownComparable(int k, T x, Object[] es, int n)
```

**Why people believe it:** the field is right there and three of the four call sites happen to want its current value. The fourth is the one that matters, and the failure is a heap that quietly violates its invariant.

### Running `heapify` forwards

**Wrong**

```java
for (int i = 0; i <= (n >>> 1) - 1; i++)
    siftDownComparable(i, (E) es[i], es, n);
```

Compiles, runs, and produces a structure that is not a heap. Input `[9, 4, 7, 1, 8, 2, 6, 3, 5]` gives `[1, 3, 2, 4, 8, 7, 6, 9, 5]` backwards and something else forwards — the forward pass sinks index 0 through subtrees that are themselves still unordered, so the "smaller child" it selects is not the smaller element of that subtree, and elements are left above smaller descendants. The queue then polls out of order with no exception anywhere.

**Right**

```java
for (int i = (n >>> 1) - 1; i >= 0; i--)
    siftDownComparable(i, (E) es[i], es, n);
```

**Why people believe it:** `for (i = 0; i < n; i++)` is the default shape of every array loop, and the backwards direction looks like an arbitrary preference rather than a precondition. `siftDown`'s contract — both subtrees are already heaps — is what forces it, and that contract is nowhere in the method signature.

### Writing the sifts as swap loops

**Wrong**

```java
private void siftUp(int k) {
    while (k > 0) {
        int parent = (k - 1) >>> 1;
        if (compare(queue[k], queue[parent]) >= 0) break;
        Object t = queue[k]; queue[k] = queue[parent]; queue[parent] = t;
        k = parent;
    }
}
```

Correct, and it does twice the array writes: three per level (read, two writes) against the hole-moving version's one, plus a final single write. For a `poll`-heavy workload at depth 20 that is 40 stores per operation instead of 21. It also forces the element into the array before the sift completes, which means an exception thrown by a comparison mid-loop leaves the new element visible at a position it has not earned.

**Right**

```java
    while (k > 0) {
        int parent = (k - 1) >>> 1;
        Object e = es[parent];
        if (key.compareTo((T) e) >= 0) break;
        es[k] = e;            // pull the parent down; the hole moves up
        k = parent;
    }
    es[k] = key;              // one write, at the end
```

**Why people believe it:** every textbook presentation of a heap describes it as "swap with parent", because swapping is easier to draw. The JDK's version is the same algorithm with the redundant half of each swap elided.

---

## Cheat sheet

| Piece | This build |
|---|---|
| Base class | `AbstractQueue<E>` — `add`/`remove()`/`element()`/`addAll` derive from `offer`/`poll`/`peek` |
| Must implement | `offer`, `poll`, `peek`, `size()`, `iterator()` |
| Fields | `Object[] queue`, `int size` (both package-private), `final Comparator comparator`, `transient int modCount` |
| `DEFAULT_INITIAL_CAPACITY` | 11 |
| `MAX_ARRAY_SIZE` | `Integer.MAX_VALUE - 8` = 2,147,483,639 |
| Why `comparator` is final | a change would invalidate every element's position at once, undetectably |
| Why `modCount` exists here | heap mutations relocate other elements; no cheap structural check exists |
| `initialCapacity < 1` | `IllegalArgumentException` — no reserved slot, so a 0-length array breaks `peek` |
| `Collection` ctor defences | re-type unless exactly `ArrayList`; null scan; `ensureNonEmpty`; ordered fast path |
| Fast path | `SortedSet` **with the same comparator**, or `getClass() == MyPriorityQueue.class` with the same comparator |
| `addAll` | an offer loop, `O(n log n)` — only the `Collection` ctor reaches `heapify` |
| `grow` | `old + max(minCapacity - old, old < 64 ? old + 2 : old >> 1)` |
| Capacity ladder | 11 → 24 → 50 → 102 → 153 → 229 → 343 → 514 → 771 (identical to the JDK) |
| Overflow guard | `newCapacity - MAX_ARRAY_SIZE > 0`, never `>` — survives `int` wraparound |
| Sifts | `static`, take `es` and `n` as parameters, move a hole, one write per level plus one |
| Sift duplication | four methods; each call site monomorphic per receiver type |
| `siftUp` break | `>= 0` — equal stops the climb, hence no stability |
| `siftDown` break | `<= 0`; plus `right < n` and the smaller-child pick — two comparisons per level |
| `half = n >>> 1` | first leaf index; `k < half` means "still a non-leaf", no bounds check needed |
| `heapify` | `for (i = (n >>> 1) - 1; i >= 0; i--)` — **backwards**, because `siftDown` needs valid subtrees |
| O(n) proof | `Σ (n/2^{h+1})·h = (n/2)·Σ h/2^h`, and `Σ h/2^h = 2` |
| Verified | heap layout and capacity ladder byte-identical to `java.util.PriorityQueue` |

---

## Self-test

**Q1.** `AbstractQueue` requires only `offer`, `poll`, `peek`, `size()` and `iterator()`. What do you get for free, and which freebie is a trap?

<details><summary>Answer</summary>

`AbstractQueue` gives `add` (as `offer` plus a throw), `remove()` (as `poll` plus a throw), `element()` (as `peek` plus a throw) and `addAll` (as an `add` loop). `AbstractCollection` above it gives `isEmpty`, `toArray`, `containsAll`, `removeAll`, `retainAll` and `toString`, all built on `iterator()` and `size()`. The trap is `addAll`: because it is an `add` loop, it is `O(n log n)`, so the only route to the O(n) `heapify` build is the `Collection` constructor. Nothing in the API hints at that asymmetry.

</details>

**Q2.** Why is `comparator` declared `final`?

<details><summary>Answer</summary>

Because every element's position in the array was decided by comparisons made under that comparator, and there is no record of them. Replacing the comparator would invalidate the whole heap in one call — every element potentially in the wrong place — with no cheap way to detect it and no way to repair it short of a full `heapify`. It is the same failure as mutating an element's priority, scaled to the entire array. Declaring the field final removes the possibility rather than documenting against it, which is why the JDK has no `setComparator` either.

</details>

**Q3.** Why do the sift methods take `Object[] es` and `int n` as parameters instead of reading `queue` and `size`?

<details><summary>Answer</summary>

Two reasons. For the JIT: a `static` method with no receiver and no field access is a pure function of its arguments, trivially inlinable, and the loop cannot be forced to re-read a field it cannot prove unchanged — the caller has already hoisted `queue` into a local. For correctness: `n` is genuinely not always `size`. `heapify` sifts with the full `n` across many calls, and `removeAt` decrements `size` before sifting within the new bounds. Making the length an explicit parameter puts that in the signature instead of in a comment.

</details>

**Q4.** Explain why `heapify` must run backwards, in terms of `siftDown`'s contract.

<details><summary>Answer</summary>

`siftDown(i, x, es, n)` assumes that both subtrees rooted at `2i+1` and `2i+2` are *already valid heaps*, and that only the element being placed at `i` might be out of position. Its smaller-child selection is only meaningful under that assumption. All of `i`'s descendants live at indices greater than `i`, so iterating `i` downwards from the last non-leaf guarantees every descendant has been processed before `i` is. Forwards, index 0 would be sunk through subtrees that are still arbitrary, the "smaller child" would not be the smaller element of that subtree, and elements would be left sitting above smaller descendants — a structure that polls out of order with no exception.

</details>

**Q5.** Why is the overflow guard `newCapacity - MAX_ARRAY_SIZE > 0` rather than `newCapacity > MAX_ARRAY_SIZE`?

<details><summary>Answer</summary>

Because at large capacities `oldCapacity + (oldCapacity >> 1)` overflows `int` and becomes negative, and a negative number is not `> MAX_ARRAY_SIZE`, so the plain comparison lets it through and `Arrays.copyOf` throws `NegativeArraySizeException` — a baffling failure for a program that was simply running out of heap. The subtraction form detects the wraparound. It is the JDK's "overflow-conscious code" idiom and appears in `ArrayList`, `Vector`, `ArrayDeque`, `AbstractStringBuilder` and `ArraysSupport.newLength`; worth recognising on sight.

</details>

**Q6.** The `Collection` constructor's `SortedSet` fast path checks `ss.comparator() == comparator`. The JDK's does not. Who is right?

<details><summary>Answer</summary>

Both, for their own signatures. The JDK's fast path lives on `PriorityQueue(SortedSet<? extends E> c)`, which *adopts* the set's comparator — so by construction the queue and the set order by the same rule, and the set's ascending order is trivially a valid heap. This build takes the comparator as a separate argument, so a `TreeSet` ordered by name could be handed to a queue ordered by priority: the input is sorted, but in the wrong dimension, and skipping `heapify` would give a queue whose invariant is false from the first `peek()`. The identity check is what makes the fast path sound for the signature it has.

</details>

**Q7.** Why does this build null-scan the whole collection when the JDK only scans conditionally?

<details><summary>Answer</summary>

The JDK scans only when `len == 1` or a comparator is present, because otherwise `heapify`'s first `compareTo` throws `NullPointerException` on a null anyway — the scan would be redundant work on the common path. The two exceptions are a single element, where `heapify` does nothing at all so no comparison happens, and a user comparator that might tolerate a null and let it into the heap. This build pays the unconditional linear pass to get a *diagnosable* exception, thrown from the constructor and naming the class, rather than one thrown from inside a static sift method with no context. The cost is one pass, dwarfed by the `heapify` that follows.

</details>

**Q8.** How many array writes does a `d`-level `siftUp` perform, and how many would a swap loop perform?

<details><summary>Answer</summary>

`d + 1` against `2d`. The hole-moving version writes the parent down into `es[k]` once per level — `d` writes — and then writes the incoming element once at the end. A swap loop writes both slots at every level: `2d`. At depth 20 that is 21 stores against 40. There is a second benefit beyond the count: the incoming element never appears in the array until the sift completes, so if a comparison throws mid-loop, the queue is left with a valid heap of the elements it already had rather than with a new element visible at an unearned position.

</details>

---

**Leaves covered:** 4.5.1, 4.5.2, 4.5.4, 4.5.5 (4 leaves)
**Leaves deferred:** none — 4.5.3 and 4.5.6 are in [04-build-my-priority-queue-b-operations-and-iterator.md](04-build-my-priority-queue-b-operations-and-iterator.md); 4.5.7, 4.5.8 and 4.5.9 are in [05-build-my-priority-queue-c-variants-and-diff.md](05-build-my-priority-queue-c-variants-and-diff.md)
**Diagrams included:** none new — the heap layout, `siftUp`, `siftDown` and `heapify` pictures (D-80 to D-83) are embedded in [01-internals-a-heap.md](01-internals-a-heap.md)
**Target version:** Java 21 LTS
**Lines:** 525
