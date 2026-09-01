# 02 Java Collections — `PriorityQueue` — INTERNALS (§4.5 `MyPriorityQueue<E>` — the operations, `removeAt` and the `forgetMeNot` iterator)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [priority-queue/03-build-my-priority-queue.md](03-build-my-priority-queue.md) · Next: [priority-queue/05-build-my-priority-queue-c-variants-and-diff.md](05-build-my-priority-queue-c-variants-and-diff.md)

Part two of `MyPriorityQueue<E>`. `MyPriorityQueue.java` is the concatenation, in order, of every code block labelled **`MyPriorityQueue.java`** in [03](03-build-my-priority-queue.md) followed by every such block in this file — typing out either file alone gives you a class that does not compile. This file ends with the closing brace.

Covered here: `offer`, `poll`, `peek`, `size`, `clear`, the linear-scan lookups, `removeAt` with its moved-element return, and the iterator that has to survive it.

---

### The three entry points

**Mental model.** Everything the queue can do reduces to: put an element at the end and let it climb; take the root and let the last element sink into the hole it left; read the root. Each is four or five lines, and the *order* of those lines is where the correctness lives.

**How it works.**

```java
// MyPriorityQueue.java
    @Override public boolean offer(E e) {
        if (e == null)
            throw new NullPointerException("MyPriorityQueue prohibits null elements: "
                + "queue[0] == null is the emptiness test");
        modCount++;
        int i = size;
        if (i >= queue.length) grow(i + 1);
        siftUp(i, e);
        size = i + 1;
        return true;
    }

    @Override @SuppressWarnings("unchecked")
    public E poll() {
        if (size == 0) return null;
        modCount++;
        final Object[] es = queue;
        final E result = (E) es[0];
        final int n = --size;
        final E last = (E) es[n];
        es[n] = null;
        if (n > 0) siftDown(0, last);
        return result;
    }

    @Override @SuppressWarnings("unchecked")
    public E peek() {
        return (size == 0) ? null : (E) queue[0];
    }

    @Override public int size() {
        return size;
    }

    @Override public void clear() {
        modCount++;
        for (int i = 0; i < size; i++) queue[i] = null;
        size = 0;
    }
```

**The order in `offer` is five decisions, not one.**

The null check is first, and it carries the reason in its message. `null` is not a rejected value here, it is a *reserved* one: `queue[0] == null` is how the JDK's `poll` recognises emptiness, so a stored null would make `poll()` returning `null` ambiguous. This build tests `size == 0` explicitly rather than relying on the sentinel — which means it *could* tolerate nulls — but keeps the ban anyway, because the `Queue` contract's `poll`-returns-null idiom depends on it and a queue that accepted nulls would not be a drop-in substitute. That is a deliberate design decision, and it is worth being explicit that it is one.

`modCount++` before the grow and before the sift. Any live iterator must fail fast whether or not the insertion succeeds, because the array *was* touched: `grow` may have replaced it, and `siftUp` may have shifted a whole path before throwing.

`siftUp(i, e)` receives the element as a value. `queue[i]` is deliberately **not** written first — the sift places the element itself, which is what lets it move a hole instead of swapping (see [03](03-build-my-priority-queue.md)).

`size = i + 1` is **last**, and this is the exception-safety line. `siftUp` calls `compareTo` or `compare`, either of which can throw: `ClassCastException` on a non-`Comparable` element, `NullPointerException` from a comparator, or anything a user comparator chooses to throw. If `size` had already been incremented, the queue would claim an element that is sitting somewhere arbitrary with the invariant broken, and every later operation would read a corrupt heap. Set last, an exception leaves `size` unchanged and the heap valid — the array holds a partially-shifted path, but every element on it is one that was already there, and the shift preserved the ordering among them.

**`poll` in six lines.** `size == 0` returns `null` — this build's explicit test where the JDK folds the check into `(result = (E) ((es = queue)[0])) != null`, one array load doing double duty. `n = --size` both decrements and names the last index. `es[n] = null` releases the slot, so the moved element is not reachable from two places at once; skipping it is the retention leak that `ArrayList.fastRemove` and `LinkedList.unlink` also guard against. `if (n > 0)` covers the one-element case, where the last element *is* the root and there is nothing to sink.

**`clear()` nulls every occupied slot and does not shrink the array.** A queue that briefly held a million elements keeps its 4 MB `Object[]` until the queue itself is unreachable; there is no `trimToSize`. The `modCount++` is required by the `Iterator` contract even though the array's *contents* are all being discarded — an iterator mid-walk must fail rather than return elements from a cleared queue.

Measured against the JDK, same seven insertions in the same order:

```
fresh capacity      = 11
heap array          = [1, 3, 2, 5, 9, 8, 7]
jdk heap array      = [1, 3, 2, 5, 9, 8, 7]
layouts match       = true
drain order         = [1, 2, 3, 5, 7, 8, 9]
```

The layout is byte-identical, not merely an equivalent heap — expected, since it is the same algorithm with the same tie-breaking, but worth confirming rather than assuming. And note the two lines together: the *array* is `[1, 3, 2, 5, 9, 8, 7]` while the *drain* is `[1, 2, 3, 5, 7, 8, 9]`. Only index 0 agrees.

**Pitfall:** the wrong belief is that `size` should be incremented before the sift, "so the queue knows about the element". The symptom is a queue permanently corrupted by one bad comparator call: a `ClassCastException` propagates out of `offer`, the caller catches and continues, and from then on `size` counts an element that is in an arbitrary slot, so `poll` returns wrong values and the invariant never recovers. The fix is to make every state change that the caller can observe happen only after the operation that can throw has succeeded.

**Interview:** "In what order does `PriorityQueue.offer` do its work, and why?" — Null check, `modCount++`, grow if needed, `siftUp`, then set `size`. `modCount` first so a live iterator fails fast even on a failed insertion; `size` last so a throwing comparator leaves a consistent heap.

> `offer` bumps `modCount` first and `size` last, with the throwing operation between them, so that a failed comparison invalidates iterators without corrupting the heap.

---

## The linear-scan lookups

```java
// MyPriorityQueue.java
    private int indexOf(Object o) {
        if (o != null) {
            final Object[] es = queue;
            for (int i = 0, n = size; i < n; i++)
                if (o.equals(es[i])) return i;
        }
        return -1;
    }

    @Override public boolean contains(Object o) {
        return indexOf(o) >= 0;
    }

    @Override public boolean remove(Object o) {
        int i = indexOf(o);
        if (i < 0) return false;
        removeAt(i);
        return true;
    }

    /** Identity-based removal, for elements taken off forgetMeNot. */
    private boolean removeEq(Object o) {
        final Object[] es = queue;
        for (int i = 0, n = size; i < n; i++)
            if (o == es[i]) { removeAt(i); return true; }
        return false;
    }
```

`indexOf` is O(n) and cannot be better. Pruning a search needs to answer "the value cannot be in this subtree", and the heap invariant gives only "everything in this subtree is `>=` its root" — which rules out subtrees whose root already exceeds the target, but never lets you choose *between* two children. So a search must descend into both whenever both roots are `<=` the target, and in the worst case that is every node. A flat array scan is simpler and has better locality than a tree walk that visits the same nodes.

`if (o != null)` returns `-1` for a null argument rather than throwing. Since no null can be stored, the answer is unambiguously "not present", and throwing would make `containsAll` fatal for any argument collection that happens to hold a null.

`o.equals(es[i])`, not `es[i].equals(o)`. The argument order matters: the query object's `equals` is called, so a `null` *stored* element — impossible here, but the pattern is worth internalising — would be handled by the caller's implementation rather than throwing. It is also one less null check per element than `Objects.equals` would cost.

**`removeEq` is `remove(Object)` with `==` in place of `equals`,** and it exists solely for the iterator. When the iterator hands back an element it took off `forgetMeNot`, that element has no array index the iterator knows about, so removal has to search for it — and it must find *that object*, not an object equal to it. `PriorityQueue` permits duplicates, so an `equals`-based search could delete a different, equal element and leave the intended one in the heap.

| Operation | Cost | Reason |
|---|---|---|
| `peek` | O(1) | `queue[0]` |
| `offer` | O(log n), `log₂ n` comparisons | one path to the root |
| `poll` | O(log n), ~`2 log₂ n` comparisons | one path down, two comparisons per level |
| `contains` / `indexOf` | **O(n)** | no subtree can be excluded |
| `remove(Object)` | **O(n)** find + O(log n) repair | the find dominates |
| `clear` | O(n) | nulls each slot; array not shrunk |
| iteration | O(n), **unsorted** | bare array walk |

Measured:

```
contains(46)        = true, remove(46) = true, size 9
```

---

### `removeAt`, and the moved element

**Mental model.** Removing from the middle moves the last element into the hole and repairs. The repair might sink it *or* climb it — slot `i` is somewhere in the middle, and the last element could easily be smaller than `i`'s parent. If it climbs, it has just moved to a position *before* `i`, which is behind any iterator that has already passed `i`. That element would then never be returned.

**How it works.**

```java
// MyPriorityQueue.java
    /**
     * Removes queue[i].
     * @return null if nothing before i moved; otherwise the element that was
     *         relocated from the end to a position before i.
     */
    @SuppressWarnings("unchecked")
    E removeAt(int i) {
        final Object[] es = queue;
        modCount++;
        int s = --size;
        if (s == i) {
            es[i] = null;
        } else {
            E moved = (E) es[s];
            es[s] = null;
            siftDown(i, moved);
            if (es[i] == moved) {
                siftUp(i, moved);
                if (es[i] != moved) return moved;
            }
        }
        return null;
    }
```

Three outcomes, one return value.

1. `s == i` — the element being removed *was* the last one. Null the slot; nothing to repair, nothing moved.
2. Otherwise move the last element into slot `i` and `siftDown`. If it sank, `es[i]` now holds something else, `es[i] == moved` is false, and the method returns `null` — nothing at an index below `i` changed.
3. If it did not sink, `es[i] == moved` still holds, so try `siftUp`. If that moved it, `es[i] != moved`, and the moved element is now at some index strictly less than `i`. Return it.

**Both tests are `==`, not `equals`, and that is not laziness.** The question is "is the object I just placed at index `i` still the object at index `i`", which is an identity question. With `equals`, a different-but-equal element that had sunk into the slot would satisfy the test, `siftUp` would be called on the wrong element, and the return value would name an element that never moved. `PriorityQueue` permits duplicates, so this is a reachable bug and not a theoretical one.

The `siftDown` **then** `siftUp` order is required. At most one of them can move the element — if it belongs lower it sinks, if it belongs higher it climbs, and it cannot do both — but you cannot know which without trying. Sinking first is the right guess because it is the common case: the last element of a heap is by construction one of the largest, so it usually belongs at or below wherever slot `i` is.

`modCount++` fires in all three cases, including the trivial `s == i` one, because `size` changed and any live iterator's `cursor < size` test is now reading a different bound.

---

### The iterator, and the deque inside it

```java
// MyPriorityQueue.java
    @Override public Iterator<E> iterator() {
        return new Itr();
    }

    private final class Itr implements Iterator<E> {
        private int cursor;
        private int lastRet = -1;
        private ArrayDeque<E> forgetMeNot;
        private E lastRetElt;
        private int expectedModCount = modCount;

        @Override public boolean hasNext() {
            return cursor < size || (forgetMeNot != null && !forgetMeNot.isEmpty());
        }

        @Override @SuppressWarnings("unchecked")
        public E next() {
            if (expectedModCount != modCount) throw new ConcurrentModificationException();
            if (cursor < size) return (E) queue[lastRet = cursor++];
            if (forgetMeNot != null) {
                lastRet = -1;
                lastRetElt = forgetMeNot.poll();
                if (lastRetElt != null) return lastRetElt;
            }
            throw new NoSuchElementException();
        }

        @Override public void remove() {
            if (expectedModCount != modCount) throw new ConcurrentModificationException();
            if (lastRet != -1) {
                E moved = MyPriorityQueue.this.removeAt(lastRet);
                lastRet = -1;
                if (moved == null) {
                    cursor--;
                } else {
                    if (forgetMeNot == null) forgetMeNot = new ArrayDeque<>();
                    forgetMeNot.add(moved);
                }
            } else if (lastRetElt != null) {
                MyPriorityQueue.this.removeEq(lastRetElt);
                lastRetElt = null;
            } else {
                throw new IllegalStateException();
            }
            expectedModCount = modCount;
        }
    }

    /** Test hook: the raw backing array, so a demo can show heap order. */
    Object[] backingArray() {
        return queue;
    }
}
```

Five fields, and each one is forced by something.

`cursor` and `lastRet` are the ordinary array-iterator pair; `lastRet = -1` means "nothing removable", which is what makes a `remove()` before any `next()` throw `IllegalStateException`.

`forgetMeNot` is **lazily allocated** — `null` until the first awkward removal — because the JDK's own comment observes that "most iterations, even those involving removals, will not need to store elements in this field". Allocating an `ArrayDeque` (a 17-slot `Object[]` plus the object header, so around 100 bytes) on every `iterator()` call to serve a rare case would be a real cost on a `for (E e : queue)` loop.

`lastRetElt` distinguishes "the last element I returned came from the array at index `lastRet`" from "it came off `forgetMeNot` and has no index". Only one of the two is ever set: `next()` sets `lastRet` on the array path and sets `lastRet = -1` before taking from the stash. `remove()` branches on which is live, and throws `IllegalStateException` when neither is.

`expectedModCount` is the fail-fast counter, re-synced at the end of every `remove()` so the iterator's own mutations do not trip its own check.

`hasNext()` is `cursor < size || (forgetMeNot != null && !forgetMeNot.isEmpty())`. The second clause is the whole reason the mechanism works: after the array walk finishes, the iteration is not over if anything was stashed.

**`remove()`'s two branches are the payoff of `removeAt`'s return value.** `moved == null` means something sank into `lastRet`, so `cursor--` steps back to visit it. `moved != null` means the element went *behind* the cursor, where a cursor adjustment cannot reach it, so the element itself is carried on the stash. Compare with `MyArrayDeque`: there, `delete` displaces by exactly one slot in a direction it reports as a boolean, so `dec(cursor)` suffices. A heap repair can lift an element several levels at once, to an index the iterator has no way to compute — so it has to be handed the element. Same bug, two shapes of fix, and the deciding factor is how far the displacement can reach.

Measured on the case from [01b](01b-internals-removeat-and-iteration.md), which was found by searching random heaps because it is rare enough that a hand-picked example usually misses it:

```
tricky heap         = [6, 12, 46, 33, 18, 80, 73, 47, 34, 95, 25]
visited (rm step 5) = [6, 12, 46, 33, 18, 80, 73, 47, 34, 95, 25] count 11
after removal       = [6, 12, 25, 33, 18, 46, 73, 47, 34, 95] size 10
all 10 survivors    = true
```

Trace it. The sixth `next()` returns `80` at index 5; `remove()` calls `removeAt(5)`. The last element, `25`, moves into slot 5 and cannot sink — index 5's children would be 11 and 12, past the new size of 10 — so `es[5] == moved` holds and `siftUp` runs. `25` is smaller than its parent `46` at index 2, so `46` shifts down into slot 5 and `25` lands at index 2, behind the cursor, which had already returned `46` as its third element. `removeAt` returns `25`; the iterator stashes it; the walk continues through the array (`73`, `47`, `34`, `95`) and finishes by draining the stash. Eleven elements delivered, ten survivors. Drop the stash and `25` is silently never returned.

And the fail-fast check itself:

```
mutate while iterating = ConcurrentModificationException
offer(null)         = NPE: MyPriorityQueue prohibits null elements: queue[0] == null is the emptiness test
```

**Insight:** `forgetMeNot` being an `ArrayDeque` is the JDK's own choice, and it is quietly circular — `PriorityQueue`'s iterator depends on `ArrayDeque`, whose null prohibition the code then relies on: `lastRetElt = forgetMeNot.poll(); if (lastRetElt != null)` reads a null poll as "the stash is empty", which is only sound because a stored null is impossible. Two classes' null bans, both arising from the same array-slot-sentinel representation, reinforcing each other.

> The heap iterator needs five fields, not three: a lazily-allocated stash for elements a repair pushed behind the cursor, and a flag saying whether the last returned element came from the array or from the stash.

---

## Pitfalls

### Comparing with `equals` in `removeAt`

**Wrong**

```java
siftDown(i, moved);
if (moved.equals(es[i])) {          // equals, not ==
    siftUp(i, moved);
    if (!moved.equals(es[i])) return moved;
}
```

Passes every test built from distinct elements. Fails as soon as the heap holds duplicates — which `PriorityQueue` permits. If a different-but-equal element sank into slot `i`, `moved.equals(es[i])` is true, `siftUp` runs on an element that is no longer at `i`, and the method may return an element that never moved. The iterator then stashes an element that is still in the array and delivers it twice.

**Right**

```java
if (es[i] == moved) {
    siftUp(i, moved);
    if (es[i] != moved) return moved;
}
```

**Why people believe it:** `equals` is the default habit for comparing objects, and IDE inspections actively suggest replacing `==` with `equals` on reference types. Here the question genuinely is identity.

### Terminating the iterator on `cursor < size` alone

**Wrong**

```java
@Override public boolean hasNext() {
    return cursor < size;
}
```

Output: correct for every iteration that performs no removal, and for most that do. It fails exactly when `removeAt` returns non-null — the stashed element is never delivered, `removeIf` silently skips it, and no exception is thrown. Measured on the tricky heap above, the walk returns ten elements instead of eleven and the element `25` is never seen.

**Right**

```java
@Override public boolean hasNext() {
    return cursor < size || (forgetMeNot != null && !forgetMeNot.isEmpty());
}
```

**Why people believe it:** it is the right form for every array-backed collection whose removal shifts in one direction. The heap is the case where a repair can move an element backwards past the cursor, and the situation is rare enough that a hand-written test almost never hits it.

### Allocating `forgetMeNot` eagerly

**Wrong**

```java
private final ArrayDeque<E> forgetMeNot = new ArrayDeque<>();

@Override public boolean hasNext() {
    return cursor < size || !forgetMeNot.isEmpty();
}
```

Correct, simpler, and it allocates a 17-slot `Object[]` plus an `ArrayDeque` header — roughly 100 bytes — on every single `iterator()` call, including every `for (E e : queue)` loop and every `toString`, to serve a case that almost never arises. On a hot path that iterates a small queue repeatedly, the iterator's own garbage can exceed the work it does.

**Right**

```java
private ArrayDeque<E> forgetMeNot;              // null until needed

@Override public boolean hasNext() {
    return cursor < size || (forgetMeNot != null && !forgetMeNot.isEmpty());
}

// inside remove(), on the moved != null branch:
    if (forgetMeNot == null) forgetMeNot = new ArrayDeque<>();
    forgetMeNot.add(moved);
```

**Why people believe it:** eager final fields are the cleaner default, and the null checks are noise. The JDK's own comment is the justification for the noise: "We expect that most iterations, even those involving removals, will not need to store elements in this field."

---

## Cheat sheet

| Piece | This build |
|---|---|
| `offer` order | null check → `modCount++` → grow → `siftUp` → **`size` last** |
| Why `size` last | a throwing comparator must leave a valid heap, not a phantom element |
| Why `modCount` first | a live iterator must fail even on a *failed* insertion — the array was touched |
| `poll` | `size == 0` → null; `n = --size`; `es[n] = null`; `if (n > 0) siftDown(0, last)` |
| Why `es[n] = null` | otherwise the moved element stays reachable twice; retention leak |
| `peek` | `(size == 0) ? null : queue[0]` — no comparison |
| `clear` | nulls `[0, size)`, `size = 0`, `modCount++`; **array not shrunk**, no `trimToSize` |
| Null policy | rejected, with the reason in the message |
| `indexOf` | O(n) flat scan; `o.equals(es[i])`, argument order deliberate |
| `contains(null)` | `false`, does not throw |
| `remove(Object)` | O(n) find + O(log n) repair |
| `removeEq` | identity scan; needed because a `forgetMeNot` element has no index |
| `removeAt` returns | `null` = nothing before `i` moved; non-null = that element climbed past `i` |
| `removeAt` order | `siftDown` first (the common case), then `siftUp` — at most one can move it |
| `removeAt` tests | `es[i] == moved` / `!=` — identity, never `equals`, because duplicates are legal |
| Iterator fields | `cursor`, `lastRet`, `forgetMeNot`, `lastRetElt`, `expectedModCount` |
| `hasNext()` | `cursor < size \|\| (forgetMeNot != null && !forgetMeNot.isEmpty())` |
| `forgetMeNot` | lazily allocated — most iterations never need it |
| `remove()` branches | `moved == null` → `cursor--`; else stash on `forgetMeNot` |
| vs `MyArrayDeque` | there the displacement is one slot in a known direction, so `dec(cursor)` suffices |
| Verified | heap layout identical to the JDK; 11 visits and 10 survivors on the tricky case |

---

## Self-test

**Q1.** `offer` sets `size` after `siftUp` and bumps `modCount` before it. Explain both.

<details><summary>Answer</summary>

`modCount++` first because the array is about to be touched — `grow` may replace it, `siftUp` may shift an entire root-to-leaf path — so any live iterator must be invalidated whether or not the insertion ultimately succeeds. `size = i + 1` last because `siftUp` calls a comparison that can throw: `ClassCastException` on a non-`Comparable`, `NullPointerException` from a comparator, or anything a user comparator raises. If `size` were already incremented, a caught exception would leave the queue counting an element sitting at an arbitrary index with the invariant broken, and it would never recover. Set last, the failure leaves a valid heap of the elements that were already there.

</details>

**Q2.** Why does `removeAt` try `siftDown` before `siftUp`, and can both ever move the element?

<details><summary>Answer</summary>

No, at most one can. The element either belongs below slot `i` in its subtree, in which case it sinks, or above it on the path to the root, in which case it climbs — the heap invariant makes both impossible simultaneously. But you cannot tell which without trying, and there is no cheap predicate for it. Sinking first is the right guess: the element being moved is the *last* element of the heap, which is by construction one of the largest, so it usually belongs at or below wherever slot `i` sits. The `es[i] == moved` test after the sink is how the code discovers that the guess was wrong.

</details>

**Q3.** Why `==` and not `equals` in `removeAt`?

<details><summary>Answer</summary>

Because the question is "is the object I placed at index `i` still the object at index `i`", which is identity, not equality. `PriorityQueue` permits duplicates, so a different-but-equal element could sink into slot `i` during the `siftDown` — under `equals` the test would report true, `siftUp` would run on an element that is no longer there, and the method could return an element that never moved. The iterator would then stash an element that is still in the array and deliver it twice. The same reasoning gives `removeEq` its `==`: deleting a `forgetMeNot` element must delete *that* object, not an equal one.

</details>

**Q4.** What are the five fields of `Itr` and why is three not enough?

<details><summary>Answer</summary>

`cursor` and `lastRet` are the ordinary array-iterator pair, and `expectedModCount` is the fail-fast counter — that is the three any array-backed iterator needs. The two extra exist because a heap repair can relocate an element *behind* the cursor: `forgetMeNot` is a lazily-allocated `ArrayDeque` holding such elements for delivery after the array walk, and `lastRetElt` records that the last element returned came from that stash rather than from an array index, so `remove()` knows to use the identity scan `removeEq` instead of `removeAt(lastRet)`. Without them the `Iterator` contract of "each element exactly once" is silently violated.

</details>

**Q5.** `removeIf` on this queue deletes half the elements. Is the heap still valid, and was every element tested?

<details><summary>Answer</summary>

Yes to both. `removeIf` is inherited from `Collection`: it walks `iterator()` and calls `it.remove()` on each match. Every `remove()` routes through `removeAt`, which repairs the invariant by sifting, so the heap is valid after each individual deletion and therefore throughout. And every element is tested exactly once because the iterator either steps `cursor` back (when something sank into the vacated slot) or stashes the displaced element for later delivery. Remove either compensation and the predicate is silently not applied to some elements — with no exception to tell you.

</details>

**Q6.** Why does `contains(null)` return `false` while `offer(null)` throws?

<details><summary>Answer</summary>

Because they are different kinds of question. `offer(null)` is an attempt to do something the structure cannot support — `null` is the reserved marker for an unoccupied slot — so it is a programming error the caller must be told about. `contains(null)` is a query whose answer is knowable and unambiguous: since no null can be stored, a null is definitely not contained, so `false` is correct information rather than a failure. Throwing would also make the inherited `containsAll` fatal for any argument collection that happens to hold a null, where `false` is the right answer for that element.

</details>

**Q7.** `clear()` bumps `modCount` even though every element is being discarded. Why does that matter?

<details><summary>Answer</summary>

Because an iterator created before the `clear` is still walking, and without the bump its `expectedModCount` would still match, `cursor < size` would be `0 < 0` and false, and `hasNext()` would simply return false — the loop would end quietly as though the collection had always been empty. That is a silent behaviour change where the contract calls for a failure: the collection was structurally modified outside the iterator, so `ConcurrentModificationException` is the specified outcome. The bump is also what makes a mid-walk `clear` followed by `next()` throw rather than read a nulled slot.

</details>

**Q8.** `forgetMeNot` is an `ArrayDeque`, and the code treats a null `poll()` as "empty". Why is that safe?

<details><summary>Answer</summary>

Because nothing null can ever get into it. `MyPriorityQueue.offer` rejects nulls, so no element in the heap is null, so `removeAt` can never return a null element for the stash — and `ArrayDeque.add` would throw on one anyway. Both prohibitions arise from the same representation: each class uses a `null` array slot as the marker for "no element here". So `lastRetElt = forgetMeNot.poll(); if (lastRetElt != null) return lastRetElt;` reading a null as "the stash is drained" is sound, and it is a small example of two classes' null bans reinforcing each other rather than each being an independent style choice.

</details>

---

**Leaves covered:** 4.5.3, 4.5.6 (2 leaves)
**Leaves deferred:** none — 4.5.1, 4.5.2, 4.5.4 and 4.5.5 are in [03-build-my-priority-queue.md](03-build-my-priority-queue.md); 4.5.7, 4.5.8 and 4.5.9 are in [05-build-my-priority-queue-c-variants-and-diff.md](05-build-my-priority-queue-c-variants-and-diff.md)
**Diagrams included:** none new — D-84 (`removeAt` and `forgetMeNot`) is embedded in [01b-internals-removeat-and-iteration.md](01b-internals-removeat-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 479
