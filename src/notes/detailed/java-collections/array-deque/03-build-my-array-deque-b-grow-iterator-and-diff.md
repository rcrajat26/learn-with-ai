# 02 Java Collections — `ArrayDeque` — INTERNALS (§4.4 `MyArrayDeque<E>` — growth, the two-slice iterator and the diff)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-deque/02-build-my-array-deque.md](02-build-my-array-deque.md) · Next: [priority-queue/01-internals-a-heap.md](../priority-queue/01-internals-a-heap.md)

Part two of `MyArrayDeque<E>`. `MyArrayDeque.java` is the concatenation, in order, of every code block labelled **`MyArrayDeque.java`** in [02](02-build-my-array-deque.md) followed by every such block in this file — typing out either file alone gives you a class that does not compile.

This file covers growth with the un-wrap slide, the two-slice iterator and the shifting removal it has to compensate for, the diff against `java.util.ArrayDeque`, and the compile-and-run transcript.

---

### Growth: the jump, and the slide that puts the ring back together

**Mental model.** Growing a linear array is one `Arrays.copyOf`. Growing a *circular* one is a `copyOf` followed by a repair, because the new slots all appear at the physical end of the array, and if the logical sequence was wrapped, they appear right in the middle of it. The repair slides the head-side leg to the far end so the sequence is contiguous again, and the new free space ends up in one block between `tail` and `head`, where it belongs.

**Why it exists.** The deque only ever grows at the instant it becomes full, and "full" is exactly the state in which every slot is occupied — so the sequence is wrapped unless `head` happens to be 0. The repair is the common case, not the exception.

**When it matters.** Whenever you size a deque. `new MyArrayDeque<>(expectedSize)` costs one allocation; letting a deque grow from 17 to hold 10,000 elements costs a dozen allocations and copies every element between two and three times over. It matters twice as much for a deque as for a list, because the un-wrap slide moves a second block of elements on top of the `copyOf`.

**How it works.**

```java
// MyArrayDeque.java
    // ---- growth ---------------------------------------------------------

    private void grow(int needed) {
        final int oldCapacity = elements.length;
        int jump = (oldCapacity < 64) ? (oldCapacity + 2) : (oldCapacity >> 1);
        int newCapacity;
        if (jump < needed || (newCapacity = oldCapacity + jump) - MAX_ARRAY_SIZE > 0)
            newCapacity = newCapacity(needed, jump);
        final Object[] es = elements = Arrays.copyOf(elements, newCapacity);
        if (tail < head || (tail == head && es[head] != null)) {
            int newSpace = newCapacity - oldCapacity;
            System.arraycopy(es, head, es, head + newSpace, oldCapacity - head);
            for (int i = head, to = (head += newSpace); i < to; i++)
                es[i] = null;
        }
    }

    private int newCapacity(int needed, int jump) {
        final int oldCapacity = elements.length;
        final int minCapacity = oldCapacity + needed;
        if (minCapacity - MAX_ARRAY_SIZE > 0) {
            if (minCapacity < 0) throw new IllegalStateException("Sorry, deque too big");
            return Integer.MAX_VALUE;
        }
        if (needed > jump) return minCapacity;
        return (oldCapacity + jump - MAX_ARRAY_SIZE < 0) ? oldCapacity + jump : MAX_ARRAY_SIZE;
    }
```

`jump` is the growth *amount*, not the target capacity: `oldCapacity + 2` below 64, `oldCapacity >> 1` at or above it. Below the threshold that is slightly more than doubling, which is deliberate — a deque constructed with `new MyArrayDeque<>(0)` starts at 1 slot, and `+2` gets it to a useful size in a handful of steps (1 → 4 → 10 → 22 → 46 → 92) instead of crawling. At and above 64 the factor is 1.5, the same as `ArrayList` and `PriorityQueue`, chosen for its memory profile rather than its copy count; the argument is worked through in [array-list/04](../array-list/04-amortised-analysis.md).

The two escape clauses. `jump < needed` catches a bulk insert whose demand exceeds the preferred growth. `(oldCapacity + jump) - MAX_ARRAY_SIZE > 0` is the overflow-conscious spelling of `oldCapacity + jump > MAX_ARRAY_SIZE` — written as a subtraction so it still gives the right answer when the sum has already wrapped negative, which a plain `>` comparison would not. `MAX_ARRAY_SIZE` is `Integer.MAX_VALUE - 8` = 2,147,483,639, the eight-word slack some VMs reserve for the array header.

`newCapacity` is the slow path. Above `MAX_ARRAY_SIZE` it returns `Integer.MAX_VALUE` and lets the allocation itself fail with `OutOfMemoryError: Requested array size exceeds VM limit`, which is the right error; only a genuinely overflowed, negative `minCapacity` produces `IllegalStateException`. `java.util.ArrayDeque` carries this same private helper rather than delegating to `jdk.internal.util.ArraysSupport.newLength` the way `ArrayList` and `PriorityQueue` do.

**The wrap test is the subtle line.** `tail < head` is the ordinary wrapped case. The second clause exists because `grow` is only ever reached from `addFirst`/`addLast` at the moment the two hands collide, and a collision with `head == 0` gives `tail == head` on a *full* buffer. Everywhere else in the class `head == tail` means empty; here it means the opposite, and `es[head] != null` is what tells them apart — an empty deque's head slot is null by invariant, a full one's is not.

`newSpace = newCapacity - oldCapacity` is how many slots just appeared at the end. The head-side leg is the `oldCapacity - head` elements from `head` to the old end; it moves forward by exactly `newSpace`, landing flush against the new end. The vacated slots must then be nulled — every non-element cell is null, by invariant, and the iterator's comodification check depends on it. The loop does the nulling and the `head` update in one expression: `to = (head += newSpace)` advances `head` and captures the old value as the bound in the same step.

![ArrayDeque grow in three frames: a full wrapped buffer with tail < head, Arrays.copyOf breaking the wrap across the middle, and the head-side segment slid to the end of the new array, with jump = (oldCapacity < 64) ? oldCapacity + 2 : oldCapacity >> 1](../diagrams/D-79-arraydeque-grow-unwrap.svg)

The middle frame is the one to look at. Immediately after `copyOf` the deque is *wrong* — the logical sequence has a run of nulls through the middle of it. The slide is not an optimisation; it is what restores the invariant, and until it runs, `size()` would still be right but iteration would not be.

Measured, from the demo below:

```
16 elements, wrapped  = capacity 17, head 9, tail 8, size 16
  raw array           = [0, 1, 2, 3, 4, 5, 6, 7, null, -8, -7, -6, -5, -4, -3, -2, -1]
after grow            = capacity 36, head 28, tail 9, size 17
  logical order       = [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 99]
```

Trace it against the code. `oldCapacity` 17, `jump` = 17 + 2 = 19, `newCapacity` 36, `newSpace` 19. The head-side leg is indices 9..16, eight elements, which slide to 28..35. `head` becomes 9 + 19 = 28. Indices 9..27 are nulled — that is the nineteen new free slots, one of which, index 9, is now `tail`. Size is `sub(9, 28, 36)` = `9 - 28 = -19`, `+36` = 17.

**Pitfall:** the wrong belief is that a `copyOf` is sufficient, because "the array is bigger and all the elements are still in it." The symptom is that the deque keeps the right `size()` but iteration returns nulls and then throws `ConcurrentModificationException` from `nonNullElementAt`, on a single-threaded program with no concurrent anything. The fix is the slide — and the reason the bug is easy to ship is that it never appears until the deque both wraps *and* grows, which a small test does not do.

**Interview:** "Why is growing a circular buffer harder than growing an array list?" — Because the new capacity appears at the physical end, which is the middle of the logical sequence whenever the buffer is wrapped. You have to slide the head-side leg to the far end afterwards. And the wrap test has to special-case `head == tail`, since `grow` is called at exactly the one moment when that means full rather than empty.

> `grow` allocates `oldCapacity + jump`, where `jump` is `oldCapacity + 2` below 64 and `oldCapacity >> 1` at or above it, then — if the sequence was wrapped — slides the head-side leg forward by the amount of new space so the ring is contiguous again.

---

### The two-slice iterator, and the removal that shifts underneath it

**Mental model.** Iterating a circular buffer is iterating at most two contiguous slices. The complication is not the wrap, it is `remove()`: removing from the middle of a ring shifts *whichever side is shorter*, so an element the iterator has not yet visited can slide backwards into a slot the cursor has already passed. The iterator has to be told which way the shift went, and step back when it went the wrong way.

**Why it exists.** `AbstractCollection` implements `contains`, `remove(Object)`, `containsAll`, `removeAll`, `retainAll`, `toArray` and `toString` in terms of `iterator()`. A wrong iterator is not one broken method, it is seven.

**How it works.**

```java
// MyArrayDeque.java
    // ---- the two-slice iterator ----------------------------------------

    @Override public Iterator<E> iterator() {
        return new DeqIterator();
    }

    private class DeqIterator implements Iterator<E> {
        int cursor = head;
        int remaining = size();
        int lastRet = -1;

        @Override public boolean hasNext() {
            return remaining > 0;
        }

        @Override public E next() {
            if (remaining <= 0) throw new NoSuchElementException();
            final Object[] es = elements;
            E e = nonNullElementAt(es, cursor);
            cursor = inc(lastRet = cursor, es.length);
            remaining--;
            return e;
        }

        @Override public void remove() {
            if (lastRet < 0) throw new IllegalStateException();
            if (delete(lastRet)) cursor = dec(cursor, elements.length);
            lastRet = -1;
        }
    }
```

The state is three ints. `cursor` is the array index of the next element to return — an *array* index, not a logical position, so it wraps. `remaining` is the count still to come, and it, not a comparison against `tail`, is the termination condition: comparing `cursor != tail` would be wrong the moment a removal moved `tail`. `lastRet` is the array index of the element `next()` last returned, or `-1` when there is nothing removable.

`nonNullElementAt` is the whole of this class's concurrent-modification detection. With no `modCount`, the iterator can only notice interference when interference happens to have nulled the slot it is about to read. This is genuinely weaker than `ArrayList`'s counter comparison: some concurrent changes go undetected and simply produce wrong results. The JDK's `ArrayDeque` has the same property and its Javadoc says so — "This check doesn't catch all possible comodifications, but does catch ones that corrupt traversal." A deque shared between threads needs `ConcurrentLinkedDeque` or `LinkedBlockingDeque`, not this.

`next()` does `cursor = inc(lastRet = cursor, es.length)` — one expression that records the returned index in `lastRet` and advances `cursor` past it.

Now the removal it has to survive:

```java
// MyArrayDeque.java
    /**
     * Removes the element at array index i, shifting whichever side is shorter.
     * @return true if the elements after i moved backwards
     */
    boolean delete(int i) {
        final Object[] es = elements;
        final int capacity = es.length;
        final int h = head, t = tail;
        final int front = sub(i, h, capacity);
        final int back = sub(t, i, capacity) - 1;
        if (front < back) {
            if (h <= i) {
                System.arraycopy(es, h, es, h + 1, front);
            } else {
                System.arraycopy(es, 0, es, 1, i);
                es[0] = es[capacity - 1];
                System.arraycopy(es, h, es, h + 1, front - (i + 1));
            }
            es[h] = null;
            head = inc(h, capacity);
            return false;
        } else {
            tail = dec(t, capacity);
            if (i <= tail) {
                System.arraycopy(es, i + 1, es, i, back);
            } else {
                System.arraycopy(es, i + 1, es, i, capacity - (i + 1));
                es[capacity - 1] = es[0];
                System.arraycopy(es, 1, es, 0, t - 1);
            }
            es[tail] = null;
            return true;
        }
    }
```

`front` is how many elements sit before index `i`; `back` is how many sit after it. The method shifts the smaller side, so a removal near either end is cheap and a removal from the exact middle costs `n/2` — the same profile as `ArrayList.remove(int)` but with half the worst case, because a list can only ever shift right-to-left.

Each branch has a wrapped sub-case. Take the front-shift branch. When `h <= i` the front leg is contiguous and one `arraycopy` moves it right by one. When `h > i` the front leg is split across the array end, so it takes three steps: shift `es[0..i)` right by one, carry `es[capacity - 1]` across the seam into `es[0]`, then shift the part from `h` to the old end right by one. The back-shift branch is the mirror image, shifting left and carrying `es[0]` back into `es[capacity - 1]`.

**The return value is the point.** `false` means the front elements moved *forwards* — everything at or before `i` shifted up by one, and `head` advanced. `true` means the back elements moved *backwards* — everything after `i` shifted down by one, which pulls an unvisited element into the slot the cursor is standing on. So `remove()` reads it:

```java
        if (delete(lastRet)) cursor = dec(cursor, elements.length);
```

Without that line, one element is silently skipped per back-shifting removal. This is the same class of problem as `PriorityQueue`'s `forgetMeNot` deque — a structural fix-up moving an unvisited element into visited territory — and the two solutions are worth comparing: `ArrayDeque` can step the cursor back because the displacement is always exactly one position in a known direction, whereas a heap's `siftUp` can move an element arbitrarily far, so `PriorityQueue` has to stash it instead. See [priority-queue/02](../priority-queue/02-internals-b-traps.md).

The demo exercises it across a wrap, removing every even element from a deque whose head is at index 29 of a 36-slot array:

```
iterator walked       = -7 -6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6 7
after removing evens  = [-7, -5, -3, -1, 1, 3, 5, 7] (size 8)
```

Fifteen elements walked, none skipped, seven removed, eight left. Delete the `dec` compensation and the walk comes back short.

The last two overrides:

```java
// MyArrayDeque.java
    @Override public boolean contains(Object o) {
        if (o == null) return false;
        final Object[] es = elements;
        for (int i = head, end = tail, to = (i <= end) ? end : es.length;
             ; i = 0, to = end) {
            for (; i < to; i++)
                if (o.equals(es[i])) return true;
            if (to == end) break;
        }
        return false;
    }

    @Override public boolean remove(Object o) {
        Objects.requireNonNull(o);
        for (Iterator<E> it = iterator(); it.hasNext(); )
            if (o.equals(it.next())) { it.remove(); return true; }
        return false;
    }

    /** Test hook: the raw backing array, so the demo can show the wrap. */
    Object[] backingArray() {
        return elements;
    }
}
```

`contains` returns `false` for a null argument rather than throwing, matching the JDK: since no null can be stored, the answer is unambiguously "no", and throwing would make `containsAll` on a collection that happens to contain a null needlessly fatal. It uses the two-slice loop — unconditional outer `for`, plain counted inner `for` — which runs the inner loop once for a contiguous deque and twice for a wrapped one, with one loop body either way. That shape is what lets HotSpot treat it as an ordinary counted array loop and eliminate the range checks; the JDK's class comment gives the reasoning verbatim, quoted in [array-deque/01](01-internals.md).

`remove(Object)` deliberately routes through the iterator rather than doing its own scan and calling `delete` directly, so that the cursor compensation is exercised on the one path that most needs it. It is O(n) — there is no index to exploit, and `MyArrayDeque` is not a `List`.

> A circular-buffer iterator must track a wrapping array index and a remaining *count*, not a comparison against `tail`; and because middle removal shifts whichever side is shorter, `delete` has to report which way it shifted so the cursor can step back when an unvisited element slid past it.

---

## Diff vs `java.util.ArrayDeque`

| Aspect | `java.util.ArrayDeque` (JDK 21) | `MyArrayDeque` | Why the JDK bothers |
|---|---|---|---|
| Interfaces | `Deque<E>`, `Cloneable`, `Serializable` | `AbstractCollection<E>` only | `Deque` is 20+ methods; the build implements the shapes that matter and skips the aliases (`offerFirst`, `pollLast`'s `removeLastOccurrence` family) |
| `Deque.reversed()` | inherited default from `SequencedCollection`, returns a write-through `ReverseOrderDequeView` | absent | comes free once you implement `Deque`; needs no `ArrayDeque` code at all |
| Null policy | bare `NullPointerException`, no message | `NullPointerException` naming the reason and the alternatives | `java.base` keeps exception construction allocation-free and relies on the stack frame naming the method; application code should not |
| Comodification | `nonNullElementAt` only; no `modCount` | identical | a `modCount` costs a write per mutation on a structure whose entire point is cheap mutation; the JDK took partial detection over that cost |
| `descendingIterator` | `DescendingIterator extends DeqIterator`, walking `dec` | absent | one more nested class; the mechanism is the same three ints run backwards |
| `Spliterator` | `DeqSpliterator` with `SIZED \| SUBSIZED \| ORDERED \| NONNULL`, midpoint `trySplit` over the linearised index space | inherited from `AbstractCollection`, i.e. `IteratorSpliterator` | a real spliterator lets `parallelStream()` split evenly and pre-size the output; the inherited one batches arithmetically and reports only `SIZED` |
| `forEach` / `removeIf` | overridden with the two-slice loop and a comodification re-check at the end | inherited, iterator-based | one hot counted loop beats a virtual `next()` per element |
| `toArray(T[])` | overridden, two `arraycopy` calls | inherited, element-by-element through the iterator | `arraycopy` is an intrinsic — one vectorised block move instead of n virtual calls |
| `clone()` | shallow copy of the array, wrap preserved | absent | trivial to add, and rarely what a caller wants |
| Serialization | `writeObject` walks the two slices in logical order; `readObject` allocates exactly `size + 1`, `head = 0` | absent | round-tripping normalises the wrap and trims the slack — the only trimming `ArrayDeque` offers |
| `readObject` array guard | routes the length through `SharedSecrets…checkArray` before allocating | absent | enforces `-Djdk.serialFilter` array-size limits; a deserialization bomb otherwise allocates first and asks later |
| Bounds checks | none in the hot path — the invariants make them unnecessary | identical | both rely on `inc`/`dec` preconditions rather than `Objects.checkIndex` |
| `addAll(Collection)` | overridden: computes `needed`, grows once, then a bulk copy | inherited, one `add` per element | avoids repeated growth checks; a bulk insert of 10,000 elements grows once instead of a dozen times |
| Growth policy | `< 64 ? +2 : ×1.5`, own `newCapacity` helper | identical, same helper | |
| `MAX_ARRAY_SIZE` | own private copy, `Integer.MAX_VALUE - 8` | identical | `ArrayDeque` predates `ArraysSupport.newLength` and still has not been migrated |

The honest summary: the algorithmic core here *is* the JDK's, line for line. What is missing is breadth — the full `Deque` surface, the spliterator, the bulk-operation overrides and serialization — and every one of those is a performance or integration concern rather than a correctness one. The one place the JDK is doing something you could not guess from the algorithm is the `SharedSecrets` array-size check in `readObject`.

---

## Compile and run

```
$ javac -Xlint:all MyArrayDeque.java PowerOfTwoDeque.java DequeDemo.java
$ java DequeDemo
```

JDK 21.0.7, zero warnings, zero errors. Full output:

```
fresh capacity        = 17
16 elements, wrapped  = capacity 17, head 9, tail 8, size 16
  raw array           = [0, 1, 2, 3, 4, 5, 6, 7, null, -8, -7, -6, -5, -4, -3, -2, -1]
after grow            = capacity 36, head 28, tail 9, size 17
  logical order       = [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 99]
jdk ArrayDeque        = [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 99]
orders match          = true
pollFirst / pollLast  = -8 / 99
peekFirst / peekLast  = -7 / 7
iterator walked       = -7 -6 -5 -4 -3 -2 -1 0 1 2 3 4 5 6 7
after removing evens  = [-7, -5, -3, -1, 1, 3, 5, 7] (size 8)
stack iteration       = [c, b, a]  pop -> c
request 1000: pow2    = 1024, java21-style = 1001
after 1000 adds: pow2 = 1024, java21-style = 1001, sizes 1000/1000
after 1001 adds: pow2 = 1024, java21-style = 1501
java21-style ladder   = 17 -> 36 -> 74 -> 111 -> 166 -> 249 -> 373 -> 559 -> 838
power-of-two ladder   = 16 -> 32 -> 64 -> 128 -> 256 -> 512 -> 1024
```

The `orders match = true` line is the one that matters: the same insertion sequence through `MyArrayDeque` and through `java.util.ArrayDeque` produces the identical logical order, including across the wrap and the grow.

The demo source is 90 lines of `main` and is not reproduced here; every line of it is exercised by the output above, and the two classes it drives are complete in these two files.

**Unverified:** no throughput figures are published for this build. A meaningful comparison against `java.util.ArrayDeque` needs a JMH harness with a named CPU, a named JDK build and `-prof perfnorm` output; a wall-clock loop in a `main` measures JIT warm-up and little else. The functional equivalence above is verified; the performance equivalence is not.

---

## Pitfalls

### Terminating the iterator on `cursor != tail`

**Wrong**

```java
@Override public boolean hasNext() {
    return cursor != tail;
}
```

Output: correct until the first `remove()`. `delete` moves `tail` backwards when it shifts the back leg, so a cursor that was two positions short of `tail` can find itself exactly on it, and the loop exits early — or, if `head` moved instead, `cursor` sails past `tail` and the loop runs a full lap before hitting it again, returning nulls that trip `nonNullElementAt`.

**Right**

```java
int remaining = size();          // captured at construction

@Override public boolean hasNext() {
    return remaining > 0;
}
```

A count is stable against the mutations the iterator itself performs, and `next()` decrements it exactly once per element.

**Why people believe it:** for a linear structure, `cursor != size` is the standard and correct form — it is what `ArrayList.Itr` does. It fails here because both endpoints of a circular buffer move.

### Ignoring `delete`'s return value

**Wrong**

```java
@Override public void remove() {
    if (lastRet < 0) throw new IllegalStateException();
    delete(lastRet);
    lastRet = -1;
}
```

Output: the demo's removal pass returns `-7 -6 -5 -4 -3 -2 -1 0 2 4 6` instead of the full fifteen — every back-shifting removal pulls an unvisited element into the cursor's slot, and the next `next()` steps straight over it. No exception, no warning, just a short walk and elements left behind that `removeIf` was supposed to delete.

**Right**

```java
    if (delete(lastRet)) cursor = dec(cursor, elements.length);
```

**Why people believe it:** `delete` returning a `boolean` looks like the `Collection.remove` convention — "did anything change?" — and it is easy to read it as always-true and discard it. Its Javadoc says what it actually means: "true if elements near tail moved backwards".

### Growing before the write instead of after

**Wrong**

```java
public void addLast(E e) {
    if (size() == elements.length - 1) grow(1);   // check first
    elements[tail] = e;
    tail = inc(tail, elements.length);
}
```

This is *correct*, and it is slower, which is a worse failure than being wrong because nothing will ever tell you. It calls `size()` — an array-header read, a subtract and a branch — on every single insertion, to answer a question the collision test answers for free.

**Right**

```java
    es[tail] = e;
    if (head == (tail = inc(tail, es.length))) grow(1);
```

**Why people believe it:** checking capacity before writing is the universal habit from bounded buffers, and it is the only option when you have no reserved slot. The reserved slot is precisely what makes the after-the-fact test safe: there is always somewhere to put the element, so you can write first and discover fullness afterwards.

---

## Cheat sheet

| Piece | This build |
|---|---|
| `grow(needed)` | `jump = oldCapacity < 64 ? oldCapacity + 2 : oldCapacity >> 1`; capacity becomes `oldCapacity + jump` |
| Slow path | `newCapacity(needed, jump)` when `jump < needed` or the sum passes `MAX_ARRAY_SIZE` |
| `MAX_ARRAY_SIZE` | `Integer.MAX_VALUE - 8` = 2,147,483,639 |
| Overflow style | `a - LIMIT > 0`, never `a > LIMIT` — correct after wraparound |
| Un-wrap test | `tail < head \|\| (tail == head && es[head] != null)` |
| Un-wrap action | slide `es[head..oldCapacity)` forward by `newCapacity - oldCapacity`, null the vacated slots, advance `head` |
| Growth ladder from 17 | 17 → 36 → 74 → 111 → 166 → 249 → 373 → 559 → 838 |
| Iterator state | `cursor` (array index), `remaining` (count), `lastRet` |
| Termination | `remaining > 0`, never `cursor != tail` |
| CME detection | `nonNullElementAt` only — partial, no `modCount` |
| `delete(i)` | shifts the shorter side; O(min(front, back)), worst case n/2 |
| `delete` return | `true` = back elements moved backwards ⟹ iterator must `dec(cursor)` |
| `contains(null)` | returns `false`, does not throw |
| Two-slice loop | unconditional outer `for`, counted inner `for`, `if (to == end) break` |
| Missing vs the JDK | `Deque` surface, `descendingIterator`, `Spliterator`, bulk overrides, `clone`, serialization |
| Verified | identical logical order to `java.util.ArrayDeque` across wrap and grow |
| Not verified | throughput — no JMH figures published |

---

## Self-test

**Q1.** After `Arrays.copyOf`, why is the deque temporarily incorrect, and what makes it correct again?

<details><summary>Answer</summary>

Because the new slots all appear at the physical end of the array, but a wrapped sequence runs "head to end, then 0 to tail" — so the new slots land in the middle of the logical order. Immediately after the copy, walking from `head` gives you the head-side leg, then a run of nulls, then the tail-side leg. The un-wrap slide fixes it by moving the head-side leg to the far end of the new array, which pushes the free space into one contiguous block between `tail` and `head`, where the invariant wants it.

</details>

**Q2.** Why is the overflow guard written `(oldCapacity + jump) - MAX_ARRAY_SIZE > 0` rather than `oldCapacity + jump > MAX_ARRAY_SIZE`?

<details><summary>Answer</summary>

Because when `oldCapacity + jump` has already overflowed it is negative, and a negative value is not `> MAX_ARRAY_SIZE`, so the plain comparison would wave the overflow through and the code would call `new Object[negative]`. Subtracting first keeps the test correct: an overflowed sum minus `MAX_ARRAY_SIZE` stays negative-or-wraps in a way the JDK's "overflow-conscious code" idiom relies on being consistently detected by the slow path that follows. It is the same idiom `ArrayList` and `AbstractStringBuilder` use.

</details>

**Q3.** A deque is at capacity 17, wrapped, with `head = 9`. It grows. Where does the element at index 9 end up, and what is the new `head`?

<details><summary>Answer</summary>

`jump = 17 + 2 = 19`, so `newCapacity = 36` and `newSpace = 19`. The head-side leg is indices 9 through 16 — `oldCapacity - head = 8` elements — and it slides forward by 19, so index 9 lands at index 28 and index 16 lands at 35, flush against the new end. `head` becomes `9 + 19 = 28`. Indices 9 through 27 are nulled. Measured values, from the demo transcript.

</details>

**Q4.** Why does the iterator track `remaining` rather than comparing `cursor` to `tail`?

<details><summary>Answer</summary>

Because `delete` moves both endpoints. Removing from the back half decrements `tail`; removing from the front half increments `head`. A `cursor != tail` termination test is therefore comparing against a moving target: it can become true a step early and end the walk short, or the cursor can step past a retreating `tail` and run a full lap through null slots. A count captured at construction and decremented once per `next()` is immune, because the iterator's own removals are the only thing changing the deque and each of them removes exactly one element it has already counted.

</details>

**Q5.** `delete(i)` returns a boolean. What does it mean, and what goes wrong if the caller ignores it?

<details><summary>Answer</summary>

`true` means the elements *after* index `i` shifted backwards by one — the back leg was the shorter side. That pulls an element the iterator has not yet visited into the slot the cursor is currently standing on, so the next `next()` skips it. `false` means the front elements shifted forwards and `head` advanced, which does not disturb anything ahead of the cursor. Ignoring the value silently skips one element per back-shifting removal; the demo's removal pass would return eleven elements instead of fifteen, with no exception anywhere.

</details>

**Q6.** Why does `contains(null)` return `false` instead of throwing `NullPointerException`?

<details><summary>Answer</summary>

Because the answer is knowable and unambiguous: no null can ever be stored, so a null is definitely not contained. Throwing would also break `containsAll` for any argument collection that happens to hold a null — the caller would get an exception where a plain `false` is the correct answer. The asymmetry with `addLast(null)`, which does throw, is deliberate: an insertion attempt is a programming error the caller must see, a membership query is not.

</details>

**Q7.** What would a real `Spliterator` buy over the one inherited from `AbstractCollection`?
<details><summary>Answer</summary>

Even splits and a pre-sized output. `AbstractCollection.spliterator()` returns an `IteratorSpliterator`, which knows only `SIZED` and splits by pulling arithmetically growing batches — `BATCH_UNIT = 1024`, doubling up to `MAX_BATCH = 1 << 25` — off the front of the iterator, so the first tasks are tiny and the split tree is lopsided. A real `DeqSpliterator` splits the linearised index range at its midpoint, reports `SIZED | SUBSIZED | ORDERED | NONNULL`, and therefore gives fork-join exact sizes at every node, which lets a `toArray`-style terminal operation allocate once instead of growing a buffer. See [iteration/03](../iteration/03-internals-spliterator.md).

</details>

**Q8.** The build grows *after* writing rather than checking capacity first. Is that safe, and why is it faster?

<details><summary>Answer</summary>

Safe, because the reserved slot guarantees there is always somewhere to put the element: the deque is never full in the physical sense, only in the "one more and the hands collide" sense. So the write can always proceed, and fullness is discovered by the collision test that was going to run anyway. Faster because the alternative — `if (size() == elements.length - 1) grow(1)` before the write — calls `size()`, which is an array-header read plus a subtract plus a branch, on every single insertion, to compute something the pointer update reveals for free.

</details>

---

**Leaves covered:** 4.4.4, 4.4.7, 4.4.8 (3 leaves)
**Leaves deferred:** none — 4.4.1, 4.4.2, 4.4.3, 4.4.5 and 4.4.6 are covered in [02-build-my-array-deque.md](02-build-my-array-deque.md)
**Diagrams included:** D-79 (re-embedded from [01-internals.md](01-internals.md); no new diagram in this row)
**Target version:** Java 21 LTS
**Lines:** 464
