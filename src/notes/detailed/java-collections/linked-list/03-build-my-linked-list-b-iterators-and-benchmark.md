# 02 Java Collections — `LinkedList` — INTERNALS (§4.2 `MyLinkedList<E>` — the list iterator, the diff and the benchmark)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-list/02-build-my-linked-list.md](02-build-my-linked-list.md) · Next: [array-deque/01-internals.md](../array-deque/01-internals.md)

Part 2 of the class. Concatenate the code blocks of `02-build-my-linked-list.md` with the two below, in order, and you have the file that `javac -Xlint:all` compiled with zero warnings on JDK 21.0.7.

## The map: what each `ListIterator` method touches

Every `ListIterator` bug is a bug about two fields — `lastReturned` and `nextIndex` — plus one counter, `expectedModCount`. The table is the whole contract.

| Method | `lastReturned` after | `nextIndex` after | `expectedModCount` | Throws |
|---|---|---|---|---|
| `next()` | the node just returned | +1 | unchanged | `NoSuchElementException`, `ConcurrentModificationException` |
| `previous()` | the node just returned (also becomes `next`) | −1 | unchanged | `NoSuchElementException`, `ConcurrentModificationException` |
| `add(E)` | **forced to `null`** | +1 | +1 | `ConcurrentModificationException` |
| `set(E)` | unchanged | unchanged | unchanged | `IllegalStateException` if `lastReturned == null` |
| `remove()` | **forced to `null`** | −1, unless `next == lastReturned` | +1 | `IllegalStateException` if `lastReturned == null` |
| `hasNext()` / `hasPrevious()` | unchanged | unchanged | unchanged | never (no comodification check) |
| `nextIndex()` / `previousIndex()` | unchanged | unchanged | unchanged | never |
| `forEachRemaining` | last node consumed | `size` (or where the check trips) | unchanged | `ConcurrentModificationException` |

Read the bold entries together: `add` and `remove` both null `lastReturned`, and that single fact generates every `IllegalStateException` in the contract. `set` and `remove` are only legal immediately after a `next`/`previous`, at most once each.

---

## `ListItr`: the only place `LinkedList` is actually fast [4.2.5]

**Mental model.** `ListItr` is a *cursor sitting in a gap* between two nodes, not a pointer at an element. `next` is the node to the right of the gap; `nextIndex` is how many gaps to the left of it. `add` widens the gap by splicing a node in — four reference writes, no traversal, no shifting. That is the O(1) insert, and it is the only operation where `LinkedList` beats `ArrayList` at any size.

**Why it exists.** `AbstractSequentialList` needs `listIterator(int)` to build `get`, `set`, `add(int, E)`, `remove(int)` and `addAll(int, Collection)`. But the cursor is also the *public* escape hatch from `node(int)`: the index API pays O(n) to locate the splice point on **every** call, whereas a held cursor pays it once and then splices for free. §4.2.8 below measures exactly that difference.

**When to reach for it, and when not.** Reach for it when you are inserting or deleting repeatedly at a position you are already walking past — a merge, an in-place filter with insertion, a run-length encoder. Do not reach for it for random access: `list.listIterator(i)` calls `node(i)`, so building a fresh cursor per index is the O(n²) loop again. The sibling that wins for random insert is `ArrayList`, whose `System.arraycopy` shift is a hardware-speed bulk move rather than a pointer chase.

**How it works — the three decisions.**

**`add` sets `lastReturned = null` before doing anything else.** Not a tidy-up; a correctness requirement. `set` and `remove` are specified to act on "the element returned by `next` or `previous`", and after an `add` there is no such element — the last thing that happened was an insertion, not a return. Nulling `lastReturned` is what converts a subsequent `set`/`remove` into the `IllegalStateException` the interface promises.

**`add` bumps `expectedModCount` instead of re-reading `modCount`.** Both work here, but incrementing states the invariant: this iterator *caused* exactly one structural change and remains valid. Re-reading `modCount` would also silently absorb a change made by someone else between the two statements.

**`remove()` decrements `nextIndex` only when `next != lastReturned`.** The two cases are forward and backward iteration. After `next()`, `lastReturned` is behind the cursor, so removing it shifts the cursor's index down by one — `nextIndex--`. After `previous()`, `lastReturned` *is* `next` (`previous()` assigns them together), so the cursor's index is unchanged and instead `next` must be advanced to `lastNext`, which is why `lastNext` is captured **before** the `unlink` nulls `lastReturned.next`. Get that order wrong and backward removal walks into a null.

**`hasNext()` deliberately does not check for comodification.** `hasNext()` is `nextIndex < size`, and `size` is the live field. So `while (it.hasNext()) it.next()` on a list mutated externally reports `false` early or `true` late rather than throwing — the exception comes from `next()`. Fail-fast is a best-effort heuristic, and this is where the "best-effort" lives.

**Beat 5 (the diagram) has no picture in this file.** The state table above is the picture: read the `add` and `remove` rows side by side and the gap model falls out.

```java
    // ---- ListIterator: the O(1) cursor ----

    @Override
    public ListIterator<E> listIterator(int index) {
        checkPositionIndex(index);
        return new ListItr(index);
    }

    private class ListItr implements ListIterator<E> {
        private Node<E> lastReturned;
        private Node<E> next;
        private int nextIndex;
        private int expectedModCount = modCount;

        ListItr(int index) {
            next = (index == size) ? null : node(index);
            nextIndex = index;
        }

        @Override
        public boolean hasNext() {
            return nextIndex < size;
        }

        @Override
        public E next() {
            checkForComodification();
            if (!hasNext())
                throw new NoSuchElementException();
            lastReturned = next;
            next = next.next;
            nextIndex++;
            return lastReturned.item;
        }

        @Override
        public boolean hasPrevious() {
            return nextIndex > 0;
        }

        @Override
        public E previous() {
            checkForComodification();
            if (!hasPrevious())
                throw new NoSuchElementException();
            lastReturned = next = (next == null) ? last : next.prev;
            nextIndex--;
            return lastReturned.item;
        }

        @Override
        public int nextIndex() {
            return nextIndex;
        }

        @Override
        public int previousIndex() {
            return nextIndex - 1;
        }

        @Override
        public void set(E e) {
            if (lastReturned == null)
                throw new IllegalStateException();
            checkForComodification();
            lastReturned.item = e;
        }

        @Override
        public void add(E e) {
            checkForComodification();
            lastReturned = null;
            if (next == null)
                linkLast(e);
            else
                linkBefore(e, next);
            nextIndex++;
            expectedModCount++;
        }

        @Override
        public void remove() {
            checkForComodification();
            if (lastReturned == null)
                throw new IllegalStateException();
            Node<E> lastNext = lastReturned.next;
            unlink(lastReturned);
            if (next == lastReturned)
                next = lastNext;
            else
                nextIndex--;
            lastReturned = null;
            expectedModCount++;
        }

        @Override
        public void forEachRemaining(Consumer<? super E> action) {
            Objects.requireNonNull(action);
            while (modCount == expectedModCount && nextIndex < size) {
                action.accept(next.item);
                lastReturned = next;
                next = next.next;
                nextIndex++;
            }
            checkForComodification();
        }

        private void checkForComodification() {
            if (modCount != expectedModCount)
                throw new ConcurrentModificationException();
        }
    }

    // ---- descendingIterator and the JEP 431 retrofit ----

    @Override
    public Iterator<E> descendingIterator() {
        return new DescendingIterator();
    }

    private class DescendingIterator implements Iterator<E> {
        private final ListItr itr = new ListItr(size());

        @Override
        public boolean hasNext() {
            return itr.hasPrevious();
        }

        @Override
        public E next() {
            return itr.previous();
        }

        @Override
        public void remove() {
            itr.remove();
        }
    }
```

### `descendingIterator` [4.2.6]

`descendingIterator` is the cheapest method in the class, because it is not an implementation — it is an adapter. `DescendingIterator` holds a `ListItr` constructed at index `size()` (the gap after the last element) and maps `hasNext`→`hasPrevious`, `next`→`previous`, `remove`→`remove`. `java.base/java/util/LinkedList.java`, JDK 21, lines 996–1010 does precisely this, comment included: *"Adapter to provide descending iterators via ListItr.previous"*.

**Insight:** the adapter is only possible because the list is *doubly* linked. `previous()` is `next = next.prev`, one field read. On a singly-linked list a descending iterator costs either O(n) per step or O(n) extra space, which is the practical reason `LinkedList` carries a `prev` pointer at all — 8 extra bytes per node on a 64-bit JVM with compressed oops.

**Gotcha:** `descendingIterator()` is an `Iterator`, not a `ListIterator`, so there is no `add` and no `set`. If you want to insert while walking backwards, use `listIterator(size())` and call `previous()` yourself — then `add` inserts *before* the cursor, i.e. after the element you just returned in reverse order, which reads backwards until you draw the gap.

**Version note.** `descendingIterator()` arrived with `Deque` in Java 6. Java 21's `reversed()` (JEP 431) is the newer spelling and returns a `SequencedCollection`, not an iterator — and for `java.util.LinkedList` it returns a *view* backed by the original (line 1285), so mutations write through. Ours returns a **copy**, which is the honest thing a hand-rolled class can do without a second view class, and it is priced in the diff table below.

```java
    @Override
    public MyLinkedList<E> reversed() {
        MyLinkedList<E> copy = new MyLinkedList<>();
        for (Node<E> x = last; x != null; x = x.prev)
            copy.linkLast(x.item);
        return copy;
    }
}
```

Verified, from the exercise `main` on JDK 21.0.7+8-LTS-245:

```
16 ListItr.add at cursor           : [a, a2, b, c] nextIndex=2
17 set() right after add()         : IllegalStateException
18 remove() before next()          : IllegalStateException
19 ListItr.set                     : [A, a2, b, c]
20 ListItr.remove                  : [A, b, c]
21 remove() twice                  : IllegalStateException
22 fail-fast after external add    : ConcurrentModificationException
23 descendingIterator              : 5 4 3 2 1
24 descendingIterator.remove       : [1, 2, 3, 4]
25 reversed() copy                 : [4, 3, 2, 1]  original=[1, 2, 3, 4]
26 O(1) insert at held cursor      : [1, 2, 99, 3, 4, 5] previousIndex=2 next=3
```

Line 26 is the whole point of the class: the cursor was parked at gap 2, `add(99)` spliced there with no traversal, and `previousIndex()` correctly reports 2 with `next()` still returning the original element 3.

> **Definition.** `ListItr` is a gap cursor over the node chain holding `next`, `nextIndex`, `lastReturned` and `expectedModCount`, which turns insertion and deletion at an already-reached position into a constant number of reference writes.

---

## Diff vs `java.util.LinkedList` [4.2.7]

| Aspect | `MyLinkedList` | `java.util.LinkedList` (JDK 21) | Why the JDK bothers |
|---|---|---|---|
| Bounds checks | one `checkPositionIndex` in `listIterator(int)`; `node(int)` trusts its caller | `isElementIndex`/`isPositionIndex` + `checkElementIndex`/`checkPositionIndex`, and `outOfBoundsMsg(int)` builds the message lazily (line 560) | the message string must not be built on the happy path; splitting element-index from position-index encodes that `add` accepts `size` and `get` does not |
| Intrinsics | none | none in `LinkedList` itself; the whole class is pointer chasing, and there is no `arraycopy` to reach for — unlike `ArrayList`, which is largely `System.arraycopy` (a JIT intrinsic) | there is genuinely nothing to intrinsify: a node walk is data-dependent loads, which is exactly why `ArrayList` wins the benchmark below |
| Serialization | not `Serializable` at all | `implements Serializable`, `size`/`first`/`last` are `transient`, with hand-written `writeObject`/`readObject` that stream `size` then the elements | serialising the node graph would emit two `Node` references per element and rebuild an identical structure at ~3x the bytes; streaming elements and re-linking on read is smaller and version-stable |
| `Spliterator` support | inherited `Collection.spliterator()`, i.e. `Spliterators.spliterator(this, Spliterator.ORDERED)` over the plain iterator | dedicated `LLSpliterator` (line 1188), `spliterator()` at line 1183; `characteristics()` returns `ORDERED \| SIZED \| SUBSIZED` | `SIZED`/`SUBSIZED` let the stream framework size its output arrays exactly. But `trySplit()` (line 1220) does **not** split the chain — it copies a *prefix* of elements into an `Object[]` of `BATCH_UNIT = 1 << 10` growing by one unit per call and capped at `MAX_BATCH = 1 << 25`, then hands that array's spliterator to the other thread. Parallel streams over a `LinkedList` therefore still traverse the chain serially to produce the batches; the parallelism is in the *processing*, not the *splitting*. |
| Null policy | permits `null` throughout; `Objects.equals` in the occurrence scans | identical — permits `null` | `Deque` allows implementations to reject `null`, and `ArrayDeque` does because it uses `null` as its empty-slot marker; a node chain has no such marker, so there is no reason to ban it |
| Allocation tricks | one `Node` per element, `new Node<>(prev, e, next)` | identical; the only "trick" is the absence of sentinel nodes, trading two allocations for null branches | node-per-element is unavoidable; the JDK instead avoids allocating on `clear()`, `unlink*` and iteration, and keeps `Node` package-private and `static` so it carries no outer-`this` field |
| `clear()` | inherited from `AbstractList` — loops the iterator calling `remove()` | overridden (line 459): direct walk nulling `item`, `next`, `prev` on every node | one pass, one `modCount` bump, no `unlink` branch sequence per element |
| `reversed()` | returns a `MyLinkedList<E>` **copy** (O(n) time and space, no write-through) | returns a `LinkedList<E>` **view**: `new ReverseOrderLinkedListView<>(this, super.reversed(), Deque.super.reversed())` (line 1285) | views are O(1) and mutations write through, which is what `SequencedCollection` users expect; a copy silently diverges |
| `Cloneable` | not implemented | `clone()` via `superClone()` then re-linking every element | shallow-copies the elements while building a fresh, independent node chain |
| `indexOf`/`lastIndexOf` | inherited from `AbstractList` — iterator-based | overridden with direct `for (Node<E> x = first; x != null; x = x.next)` walks | skips the iterator's `modCount` checks and virtual calls per element |
| `toArray` | inherited from `AbstractCollection` | overridden with a direct node walk into a pre-sized array | `size` is known, so no growth-and-copy dance |
| Methods inherited rather than written (both) | `get`, `set`, `add(int, E)`, `remove(int)`, `addAll(int, Collection)`, `iterator()` from `AbstractSequentialList`; `equals`, `hashCode`, `subList`, `listIterator()` from `AbstractList`; `contains`, `isEmpty`, `removeAll`, `retainAll` from `AbstractCollection`; `stream`, `forEach`, `removeIf` from the interface defaults | the same skeletons, minus the ones listed above that it overrides for speed | the skeleton is correct everywhere and fast enough almost everywhere; the JDK overrides exactly the methods where one indirection per element is measurable |

**Interview:** "Is a parallel stream over a `LinkedList` worth it?" Rarely. `LLSpliterator.trySplit()` copies a growing prefix into an array rather than splitting the structure, so the traversal that produces work units is inherently serial and cache-hostile. If you need parallelism, copy into an `ArrayList` (or collect to an array) first — the copy is one linear pass and every subsequent split is O(1).

---

## Benchmark: locate versus splice [4.2.8] [PROVE]

**What is being measured.** Two things the leaf deliberately conflates and this benchmark separates:

- **located insert** — `list.add(list.size() >> 1, x)`, repeated. Every call pays `node(i)` to walk to the midpoint, then splices. This is what "mid-list insertion" means in practice.
- **cursor insert** — `ListIterator` parked once at the midpoint, then `it.add(x)` repeated. The walk is paid once, outside the timer; each timed call is only the splice.

Three implementations: `MyLinkedList`, `java.util.LinkedList`, `java.util.ArrayList`. `MyLinkedList` is included to confirm the hand-rolled class has the same cost profile as the real one, which makes it a valid stand-in for the rest of these notes.

**Method, stated plainly.** A plain timed loop with `System.nanoTime()`, not JMH. Warmup is 6 rounds of every (implementation × mode) pair at n = 20 000 to get C2 to compile the hot loops; each reported figure is the **best of 5** fresh-list runs, best-of rather than mean because the machine is not quiesced and the noise is one-sided. `OPS = 2000` insertions per timed run. No blackhole, no dead-code guard beyond a `size()` assertion, no fork isolation — treat the *ratios* as the result and the absolute milliseconds as indicative. **JDK 21.0.7+8-LTS-245, macOS 15 (Darwin 25.5.0), Apple M4 Pro, aarch64, default G1.** No n was dropped; the whole run finishes in about 4.5 s.

```java
    private static final int OPS = 2_000;

    private static List<Integer> fresh(String impl, int n) {
        List<Integer> l = switch (impl) {
            case "ArrayList"  -> new ArrayList<>();
            case "LinkedList" -> new LinkedList<>();
            default           -> new MyLinkedList<>();
        };
        for (int i = 0; i < n; i++) l.add(i);
        return l;
    }


    /** OPS inserts at the midpoint through the index API: locate (O(n)) + splice (O(1)). */
    private static long locatedInsert(List<Integer> l) {
        long t = System.nanoTime();
        for (int i = 0; i < OPS; i++) l.add(l.size() >> 1, i);
        return System.nanoTime() - t;
    }


    /** OPS inserts through a ListIterator already parked at the midpoint: splice only. */
    private static long cursorInsert(List<Integer> l) {
        ListIterator<Integer> it = l.listIterator(l.size() >> 1);
        long t = System.nanoTime();
        for (int i = 0; i < OPS; i++) it.add(i);
        return System.nanoTime() - t;
    }


    private static long best(String mode, String impl, int n) {
        long b = Long.MAX_VALUE;
        for (int r = 0; r < 5; r++) {
            List<Integer> l = fresh(impl, n);
            long ns = mode.equals("located") ? locatedInsert(l) : cursorInsert(l);
            if (l.size() != n + OPS) throw new AssertionError(l.size());
            b = Math.min(b, ns);
        }
        return b;
    }
```

### Results

`n` is the list size before the 2000 insertions.

| n | mode | `ArrayList` | `java.util.LinkedList` | `MyLinkedList` |
|---|---|---|---|---|
| 1 000 | located | 0.110 ms | 2.576 ms | 2.577 ms |
| 1 000 | cursor | 0.068 ms | 0.016 ms | 0.015 ms |
| 10 000 | located | 0.505 ms | 15.362 ms | 15.994 ms |
| 10 000 | cursor | 0.463 ms | 0.013 ms | 0.014 ms |
| 50 000 | located | 2.254 ms | 72.702 ms | 73.088 ms |
| 50 000 | cursor | 2.229 ms | 0.014 ms | 0.017 ms |
| 100 000 | located | 6.487 ms | 136.410 ms | 137.263 ms |
| 100 000 | cursor | 6.445 ms | 0.013 ms | 0.014 ms |

Derived ratios:

| n | located: LL / AL | cursor: AL / LL | located / cursor for LL |
|---|---|---|---|
| 1 000 | 23.4x slower | 4.3x slower | 161x |
| 10 000 | 30.4x slower | 35.6x slower | 1 182x |
| 50 000 | 32.3x slower | 159x slower | 5 193x |
| 100 000 | 21.0x slower | 496x slower | 10 493x |

### What the numbers say

**The splice really is O(1).** The cursor column for `LinkedList` and `MyLinkedList` is flat — 0.013 to 0.017 ms for 2000 insertions at *every* n from 1 000 to 100 000, i.e. roughly 7 ns per insertion, independent of list size. `ArrayList`'s cursor column grows linearly (0.068 → 6.445 ms, a 95x rise over a 100x rise in n) because `ArrayList.listIterator().add` still calls `System.arraycopy` to shift the tail. At n = 100 000 the linked cursor is **496x faster**. This is the one benchmark `LinkedList` wins, and it wins it by nearly three orders of magnitude.

**The located insert really does lose.** The same operation expressed through the index API is 21–32x *slower* than `ArrayList`, and the located/cursor ratio for `LinkedList` climbs from 161x to 10 493x. Every microsecond of that gap is `node(i)`: a dependent chain of pointer loads, one cache miss per hop, no prefetching possible because the next address is unknown until the current line arrives. `ArrayList` moves 200 KB per insert at n = 100 000 and still wins, because a sequential `arraycopy` runs at memory bandwidth while a pointer chase runs at memory *latency*.

**Insight:** the two columns differ only in where the `node(i)` call happens. `LinkedList` is not a fast list; it is a fast *cursor*, and the index API hides the cursor behind an O(n) lookup. Any argument for `LinkedList` that does not name a held `ListIterator` (or a head/tail operation) is an argument for `ArrayList`.

**Cross-check.** `01-internals.md` in this set timed only located inserts and reported 5.2x / 29.9x / 31.1x / 26.6x at the same four sizes on the same machine and JDK. This run's located column, 23.4x / 30.4x / 32.3x / 21.0x, agrees at 10k–100k. It disagrees at n = 1 000 (23.4x here against 5.2x there) — different `OPS` count and different warmup, and at n = 1 000 the whole timed region is a few hundred microseconds where a plain timed loop has no resolution to spare. The 10k+ figures are the trustworthy ones in both runs. An independent re-run of this same harness on the same machine landed 15–20% higher in absolute milliseconds (located `LinkedList`: 2.950 / 19.043 / 85.054 / 164.620 ms) while the located `LinkedList`/`ArrayList` ratio held at 24.0x / 33.3x / 32.7x / 22.0x and the linked cursor column stayed flat at 0.014–0.017 ms — which is what "read the ratios, not the milliseconds" means in practice.

**Unverified:** none of these figures should be read as steady-state throughput; JMH with per-iteration state and a blackhole would be needed to claim that, and the numbers here are a plain timed loop as stated.

> **Definition.** `LinkedList`'s O(1) structural mutation is real but only reachable through a cursor already positioned at the target; reached through an index it is O(n) to locate, and the location cost dominates by one to four orders of magnitude.

---

## Pitfalls

### Believing `LinkedList` is the right choice for "lots of inserts in the middle"

**Wrong**

```java
    static void insertAllAtMiddle(List<Integer> target, List<Integer> toAdd) {
        for (int v : toAdd)
            target.add(target.size() >> 1, v);   // O(n) locate on every call
    }
```

With `target` a `java.util.LinkedList` of 100 000 elements and 2000 insertions this measured **136.410 ms**, against **6.487 ms** for the same code on an `ArrayList` — 21x slower.

**Right**

```java
    static void insertAllAtMiddle(List<Integer> target, List<Integer> toAdd) {
        ListIterator<Integer> cursor = target.listIterator(target.size() >> 1);
        for (int v : toAdd)
            cursor.add(v);                       // locate once, then splice
    }
```

The same 2000 insertions through a held cursor measured **0.013 ms** on `java.util.LinkedList` — 496x *faster* than `ArrayList`, and 10 493x faster than the same list via the index API. One behavioural difference to keep in view: the index version re-locates the midpoint each time and so reverses the inserted run, while the cursor version advances with its own insertions and preserves order — verified as `slow=[1, 2, 8, 7, 3, 4]` against `fast=[1, 2, 7, 8, 3, 4]`. If order matters, the cursor version is also the one that is right.

**Why people believe it:** the complexity table says `LinkedList.add(int, E)` is O(1) insertion and `ArrayList.add(int, E)` is O(n) shifting. Both halves are true and both omit the locate step, which is O(n) for the linked list and O(1) for the array. The table describes the splice, not the call.

### Calling `set()` after `add()` on the same `ListIterator`

**Wrong**

```java
    static void fixupAfterInsert(List<String> l) {
        ListIterator<String> it = l.listIterator();
        it.next();
        it.add("inserted");
        it.set("correction");      // IllegalStateException
    }
```

Real output: `wrong -> java.lang.IllegalStateException`. `add` set `lastReturned` to `null`, so there is no "last returned element" for `set` to overwrite.

**Right**

```java
    static void fixupAfterInsert(List<String> l) {
        ListIterator<String> it = l.listIterator();
        it.next();
        it.add("inserted");
        it.previous();             // re-return the node just added
        it.set("correction");      // now legal
    }
```

`previous()` assigns `lastReturned`, restoring the precondition; on `["x", "y"]` this prints `right -> [x, correction, y]`. The failing variant is run line 17 of the exercise `main`.

**Why people believe it:** `add` moves the cursor, so it feels like it "returned" the new element. It did not — `ListIterator.set` is specified against `next`/`previous` only, and `add` explicitly invalidates that state.

## Cheat sheet

| Item | Value |
|---|---|
| `ListItr` fields | `next`, `nextIndex`, `lastReturned`, `expectedModCount` |
| Cursor model | sits in the *gap*; `next` is the node to its right |
| `add(E)` | `lastReturned = null`; `linkBefore(e, next)` or `linkLast(e)`; `nextIndex++`; `expectedModCount++` |
| `set(E)` | writes `lastReturned.item`; no structural change, no `modCount` bump |
| `remove()` | capture `lastReturned.next` **first**, `unlink`, then `next = lastNext` or `nextIndex--` |
| `IllegalStateException` from | `set`/`remove` when `lastReturned == null` — before any `next`, or right after `add`/`remove` |
| `hasNext()` | `nextIndex < size`; **no** comodification check |
| `descendingIterator()` | adapter over `ListItr(size())`: `hasPrevious`/`previous`/`remove`; `Iterator`, so no `add`/`set` |
| `reversed()` (JDK 21) | real one: O(1) write-through **view** (line 1285). Ours: O(n) **copy** |
| `LLSpliterator.characteristics()` | `ORDERED \| SIZED \| SUBSIZED` |
| `LLSpliterator.trySplit()` | copies a *prefix* into `Object[]`; `BATCH_UNIT = 1 << 10` growing per call, `MAX_BATCH = 1 << 25` |
| Splice cost (measured) | ~7 ns/insert, flat from n = 1 000 to 100 000 |
| Located insert (measured) | 21–32x slower than `ArrayList`; up to 10 493x slower than its own cursor |
| Only reason to pick `LinkedList` | head/tail ops, or a held `ListIterator`, or `null`-tolerant `Deque` |

## Self-test

**Q1.** Why does `ListItr.add` set `lastReturned = null` as its very first statement?

<details><summary>Answer</summary>

Because `set` and `remove` are specified to operate on the element returned by the most recent `next()` or `previous()`, and after an `add` there is no such element. Nulling `lastReturned` is precisely what makes a following `set`/`remove` throw `IllegalStateException`, as the `ListIterator` contract requires. It is a correctness statement, not housekeeping — run line 17 shows the exception it produces.

</details>

**Q2.** In `ListItr.remove()`, why is `Node<E> lastNext = lastReturned.next` captured before the `unlink` call?

<details><summary>Answer</summary>

`unlink` nulls `x.next` (in the branch where a successor existed), so after the call `lastReturned.next` is null. The backward-iteration case needs that successor: when `previous()` was the last call, `next == lastReturned`, and removing it must leave the cursor pointing at the removed node's successor — `next = lastNext`. Reading it after `unlink` would set `next = null`, silently ending the iteration.

</details>

**Q3.** `remove()` sometimes decrements `nextIndex` and sometimes does not. What distinguishes the two cases?

<details><summary>Answer</summary>

The direction of the last move. After `next()`, `lastReturned` lies behind the cursor, so removing it reduces the number of elements to the cursor's left — `nextIndex--`. After `previous()`, `previous()` assigned `lastReturned` and `next` to the same node, so `next == lastReturned`: the removed element was *at* the cursor, the count to its left is unchanged, and instead `next` advances to `lastNext`. The `if (next == lastReturned)` test is exactly a test for "the last move was `previous()`".

</details>

**Q4.** Why does `hasNext()` not call `checkForComodification()`?

<details><summary>Answer</summary>

Deliberate. `hasNext()` is `nextIndex < size` against the live `size` field, so on an externally mutated list it simply reports a possibly-wrong answer rather than throwing; the `ConcurrentModificationException` is raised by `next()`. Fail-fast is documented as best-effort, and keeping `hasNext()` check-free keeps the loop condition to one field compare. `java.util.LinkedList`'s `ListItr` behaves identically (line 895).

</details>

**Q5.** A parallel stream over a 1 000 000-element `java.util.LinkedList` barely speeds up. Why, given that `LLSpliterator` reports `SIZED` and `SUBSIZED`?

<details><summary>Answer</summary>

`characteristics()` returns `ORDERED | SIZED | SUBSIZED` (outside a table cell, so the pipes read literally), so sizing is exact — that is not the problem. `trySplit()` (line 1220) is: it cannot halve a chain in O(1), so it walks the list copying a *prefix* into an `Object[]` and returns that array's spliterator. The batch is `BATCH_UNIT = 1 << 10` elements, growing by one unit per successive call and capped at `MAX_BATCH = 1 << 25`. Producing work units is therefore a serial, cache-missing traversal of the whole list, and only the per-element processing runs in parallel. Copy to an `ArrayList` first if you need real parallelism.

</details>

**Q6.** What does `descendingIterator()` cost, and what does it not give you?

<details><summary>Answer</summary>

It costs one object allocation plus a `ListItr(size())` construction. `ListItr`'s constructor takes the `index == size` fast path — `next = null`, no `node(int)` walk — so construction is O(1), and each `next()` is one `x.prev` read. What it does not give you is `ListIterator`: it is a plain `Iterator`, so there is no `add` and no `set`, only `remove`. For backward insertion use `listIterator(size())` and drive `previous()` yourself.

</details>

**Q7.** Both `MyLinkedList` and `java.util.LinkedList` permit `null`, and both implement `Deque`. Which `Deque` method becomes ambiguous as a result, and what is the fix?

<details><summary>Answer</summary>

The null-returning inspectors and removers — `peek`, `peekFirst`, `peekLast`, `poll`, `pollFirst`, `pollLast`. A `null` return means either "the deque is empty" or "the element at that end is `null`", and the caller cannot tell. The fix is to test emptiness with `isEmpty()`/`size()` and use the throwing variants (`getFirst`, `removeFirst`) when a missing element is genuinely exceptional. `ArrayDeque` avoids the ambiguity by rejecting `null` outright, because it uses `null` as its empty-slot marker.

</details>

**Q8.** Our `reversed()` returns a copy and `java.util.LinkedList`'s returns a view. Write the one-line test that distinguishes them, and say what each prints.

<details><summary>Answer</summary>

`var r = list.reversed(); list.addFirst(x); System.out.println(r.size());` — on `java.util.LinkedList` the view sees the new element and prints `size + 1`; on `MyLinkedList` the copy was materialised at call time and prints the old `size`. Measured on `["a", "b"]` plus `addFirst("z")`: `j.u.LinkedList reversed() size after addFirst = 3 [b, a, z]` against `MyLinkedList reversed() size after addFirst = 2 [b, a]`. The JDK builds `new ReverseOrderLinkedListView<>(this, super.reversed(), Deque.super.reversed())` at line 1285 precisely so `SequencedCollection` users get write-through semantics. Our override exists only because JDK 21 will not compile a class implementing both `List` and `Deque` without it.

</details>

---

**Leaves covered:** 4.2.5, 4.2.6, 4.2.7, 4.2.8 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 497
