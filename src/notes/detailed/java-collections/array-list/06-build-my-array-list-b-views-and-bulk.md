# 02 Java Collections — `ArrayList` — INTERNALS (§4.1 `MyArrayList<E>` — sublist view, bulk operations and the diff)

> **SUPERSEDED — DO NOT READ, DO NOT CITE.** This file is a dead earlier draft with no row in the index. Leaves 4.1.9-4.1.16 are covered by rows 26c/26d/26e: `07-build-my-array-list-c-sublist-and-equality.md`, `08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md`, `09-build-my-array-list-e-spliterator-diff-and-benchmark.md`. Retained deliberately rather than deleted; excluded from all aggregate files (rows 70-73).

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/05-build-my-array-list.md](05-build-my-array-list.md) · Next: [linked-list/01-internals.md](../linked-list/01-internals.md)

[05](05-build-my-array-list.md) built the storage core: the two sentinels, `grow`, the accessors, removal, the scans, `Itr` and `ListItr`. This file finishes the class — the `SubList` view, capacity management, value semantics, the four bulk operations including `removeIf`'s bitset compaction, `sort`, the midpoint `Spliterator` — then measures the result against `java.util.ArrayList` in a diff table and a JMH harness.

Same rule as before: every block below is copied out of the file that compiles under JDK 21 with `-Xlint:all` and zero warnings. The compile command and the complete runtime output are at the bottom of this file.

---

### The `SubList` view (4.1.9)

**Mental model.** A sublist is not a copy. It is a pair of numbers — an offset and a length — plus a pointer back to the list it is a window onto. Reading through it adds the offset; writing through it writes to the parent's array. There is exactly one array in the whole arrangement.

**Why it exists.** Range operations without copying. `list.subList(3, 7).clear()` deletes four elements in one `arraycopy`; the copying alternative allocates a four-element list, throws it away, and then needs a second loop to delete the originals. Every range-scoped algorithm in the JDK — `Collections.rotate`, `Collections.fill`, `binarySearch` over a window — is written against a sublist for this reason.

**When to reach for it, and when not.** Reach for it for a scoped bulk operation, and for passing a window into a method that should not see the rest. Do *not* store one. A sublist is only valid until the next structural change to the parent made by anything other than that sublist; the moment the parent is touched directly, every read through the view throws `ConcurrentModificationException`. If you need a durable window, copy: `new ArrayList<>(list.subList(3, 7))`.

**How it works.** Three fields and one check. `offset` is the absolute index in the parent's array of this view's element 0. `size` is the window length, maintained independently. The inherited `AbstractList.modCount` field is used as a *mirror* of the parent's counter at the moment the view was last in agreement with it; `checkForComodification` compares mirror to parent. `parent` chains nested sublists so that a structural change through a deep view propagates size and mirror updates outward to every enclosing view.

```java
    @Override
    public List<E> subList(int fromIndex, int toIndex) {
        subListRangeCheck(fromIndex, toIndex, size);
        return new SubList(fromIndex, toIndex);
    }

    static void subListRangeCheck(int fromIndex, int toIndex, int size) {
        if (fromIndex < 0) {
            throw new IndexOutOfBoundsException("fromIndex = " + fromIndex);
        }
        if (toIndex > size) {
            throw new IndexOutOfBoundsException("toIndex = " + toIndex);
        }
        if (fromIndex > toIndex) {
            throw new IllegalArgumentException(
                "fromIndex(" + fromIndex + ") > toIndex(" + toIndex + ")");
        }
    }

    private class SubList extends AbstractList<E> implements RandomAccess {
        private final SubList parent;
        private final int offset;
        private int size;

        SubList(int fromIndex, int toIndex) {          // window onto the root list
            this.parent = null;
            this.offset = fromIndex;
            this.size = toIndex - fromIndex;
            this.modCount = MyArrayList.this.modCount;
        }

        SubList(SubList parent, int fromIndex, int toIndex) {  // window onto a window
            this.parent = parent;
            this.offset = parent.offset + fromIndex;
            this.size = toIndex - fromIndex;
            this.modCount = parent.modCount;
        }

        @Override
        public int size() {
            checkForComodification();
            return size;
        }

        @Override
        public E get(int index) {
            Objects.checkIndex(index, size);
            checkForComodification();
            return elementAt(MyArrayList.this.elementData, offset + index);
        }

        @Override
        public E set(int index, E element) {
            Objects.checkIndex(index, size);
            checkForComodification();
            return MyArrayList.this.set(offset + index, element);
        }

        @Override
        public void add(int index, E element) {
            rangeCheckForAdd(index, size);
            checkForComodification();
            MyArrayList.this.add(offset + index, element);
            updateSizeAndModCount(1);
        }

        @Override
        public E remove(int index) {
            Objects.checkIndex(index, size);
            checkForComodification();
            E result = MyArrayList.this.remove(offset + index);
            updateSizeAndModCount(-1);
            return result;
        }

        @Override
        protected void removeRange(int fromIndex, int toIndex) {
            checkForComodification();
            MyArrayList.this.removeRange(offset + fromIndex, offset + toIndex);
            updateSizeAndModCount(fromIndex - toIndex);
        }

        @Override
        public boolean addAll(Collection<? extends E> c) {
            return addAll(size, c);
        }

        @Override
        public boolean addAll(int index, Collection<? extends E> c) {
            rangeCheckForAdd(index, size);
            int cSize = c.size();
            if (cSize == 0) {
                return false;
            }
            checkForComodification();
            MyArrayList.this.addAll(offset + index, c);
            updateSizeAndModCount(cSize);
            return true;
        }

        @Override
        public int indexOf(Object o) {
            checkForComodification();
            int index = MyArrayList.this.indexOfRange(o, offset, offset + size);
            return index >= 0 ? index - offset : -1;
        }

        @Override
        public int lastIndexOf(Object o) {
            checkForComodification();
            int index = MyArrayList.this.lastIndexOfRange(o, offset, offset + size);
            return index >= 0 ? index - offset : -1;
        }

        @Override
        public boolean removeIf(Predicate<? super E> filter) {
            checkForComodification();
            int oldSize = MyArrayList.this.size;
            boolean modified = MyArrayList.this.removeIf(filter, offset, offset + size);
            if (modified) {
                updateSizeAndModCount(MyArrayList.this.size - oldSize);
            }
            return modified;
        }

        @Override
        public List<E> subList(int fromIndex, int toIndex) {
            subListRangeCheck(fromIndex, toIndex, size);
            return new SubList(this, fromIndex, toIndex);
        }

        private void updateSizeAndModCount(int sizeChange) {
            SubList slist = this;
            do {
                slist.size += sizeChange;
                slist.modCount = MyArrayList.this.modCount;
                slist = slist.parent;
            } while (slist != null);
        }

        private void checkForComodification() {
            if (MyArrayList.this.modCount != this.modCount) {
                throw new ConcurrentModificationException();
            }
        }
    }
```

The decisions worth naming.

**`subListRangeCheck` throws two different exception types.** Out-of-range endpoints give `IndexOutOfBoundsException`; a reversed range gives `IllegalArgumentException`. That is the `List.subList` contract, not an accident, and `java.util.ArrayList` does the same at line 1181.

**`updateSizeAndModCount` walks the `parent` chain.** Without it, a nested `subList(subList(list))` would update its own size but leave the enclosing view believing the old length, and the enclosing view's next read would either be out of bounds or silently wrong. The `do/while` runs at least once so the view that made the change is itself updated first, then propagates outward. The root list's own `size` was already adjusted by the delegated call.

**The mirror is only refreshed by changes made *through* a view.** A direct `parent.add(x)` bumps `MyArrayList.this.modCount` and touches no mirror, so the very next `view.size()` throws. That is the intended, documented behaviour, and it is what makes sublists unsafe to cache.

**`removeIf` is overridden but `iterator`, `listIterator`, `contains`, `equals`, `hashCode` and `toString` are not.** The `AbstractList` versions of those are already correct here, because they are written in terms of `get`, `set`, `size` and `add`, all of which run `checkForComodification`. So the view is fail-fast even in the methods nobody wrote. `removeIf` gets an override only because delegating to the parent's ranged `removeIf` turns an O(n) `AbstractCollection` loop with per-element shifting into a single compaction pass.

**Verified.** From the demo run:

```
subList(1,4)                          -> [b, c, d]
view.set(0,"B") writes through        -> [a, B, c, d, e]
view.remove(0) shrinks parent         -> [a, c, d, e] view=[c, d]
view read after parent structural change -> ConcurrentModificationException
stream via sublist                    -> a|c
```

`view.remove(0)` shrank the *parent* from five elements to four and the view from three to two, in one call, with no copy. The subsequent `base.add("f")` invalidated the view immediately.

**Pitfall:** `subList` returning a `List` makes it look like a value. It is a live view with a shorter lifetime than the object it came from — closer to an iterator than to a list. Returning one from a public method is a bug factory; wrap it in `new ArrayList<>(...)` or `List.copyOf(...)` at the boundary.

**Interview:** *How does `list.subList(a, b).clear()` delete a range in O(n) with one copy?* `AbstractList.clear()` calls `removeRange(0, size)`, `SubList.removeRange` translates by the offset and delegates to `MyArrayList.removeRange`, which calls `shiftTailOverGap` — a single `System.arraycopy` plus the trailing-null loop.

> A sublist is an offset, a length, a parent pointer and a mirrored `modCount` — a window that reads and writes the parent's array directly and is invalidated by any structural change it did not itself make.

---

### `ensureCapacity`, `trimToSize`, `clear` (4.1.10)

Three supporting facts about capacity, one mechanism each.

```java
    public void ensureCapacity(int minCapacity) {
        if (minCapacity > elementData.length
                && !(elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA
                     && minCapacity <= DEFAULT_CAPACITY)) {
            modCount++;
            grow(minCapacity);
        }
    }

    public void trimToSize() {
        modCount++;
        if (size < elementData.length) {
            elementData = (size == 0) ? EMPTY_ELEMENTDATA : Arrays.copyOf(elementData, size);
        }
    }

    @Override
    public void clear() {
        modCount++;
        final Object[] es = elementData;
        for (int to = size, i = size = 0; i < to; i++) {
            es[i] = null;
        }
    }
```

`ensureCapacity`'s second clause is the sentinel test again: on a defaulted empty list, a request for 10 or fewer is a no-op, because the first `add` would allocate 10 anyway and growing now would waste a copy. The `!` in front of the whole conjunction reads awkwardly; it says "grow, unless the only reason to grow is a request the default allocation already covers".

`trimToSize` bumps `modCount` unconditionally, before it knows whether it will do anything. That is deliberate: replacing `elementData` with a shorter array is exactly the situation `Itr.next`'s `i >= es.length` check exists to catch, so any live iterator must be invalidated even in the borderline cases. Note it can also *reset the sentinel* — trimming an empty list installs `EMPTY_ELEMENTDATA`, so a defaulted list that is trimmed loses its "inflate to 10" privilege permanently.

`clear` nulls every live slot but does **not** shrink the array. Capacity survives. That is right for the common reuse-the-buffer case and wrong if the list was briefly enormous; `clear()` then `trimToSize()` is the pair that actually releases the memory. The loop `for (int to = size, i = size = 0; i < to; i++)` sets `size` to 0 in the initialiser, so a concurrent reader sees an empty list from the first instant rather than a half-nulled one.

**Verified:** `ensureCapacity(100)` on a fresh list gives capacity 100; adding one element and calling `trimToSize()` gives capacity 1; `clear()` gives `[] size=0 capacity=1`.

> Capacity and size are independent: `ensureCapacity` and `grow` raise capacity, `trimToSize` lowers it, and `clear` touches only size.

---

### `equals`, `hashCode`, `toString` (4.1.11)

**Mental model.** `List` equality is a contract on the *interface*, not on the class. Any two `List` implementations holding equal elements in the same order must be equal and must hash the same. `MyArrayList` must therefore agree with `java.util.ArrayList`, `LinkedList`, `List.of` and every other implementation.

**Why it is not `Objects.equals` on the array.** Two lists can have the same elements and different capacities, and `Arrays.equals` on `elementData` would compare the trailing nulls too. The contract is over the first `size` elements only.

```java
    @Override
    public boolean equals(Object o) {
        if (o == this) {
            return true;
        }
        if (!(o instanceof List<?> other)) {
            return false;
        }
        final int expectedModCount = modCount;
        boolean equal = (o instanceof MyArrayList<?> that)
                ? equalsArrayList(that)
                : equalsRange(other, 0, size);
        if (modCount != expectedModCount) {
            throw new ConcurrentModificationException();
        }
        return equal;
    }

    private boolean equalsRange(List<?> other, int from, int to) {
        final Object[] es = elementData;
        var oit = other.iterator();
        for (; from < to; from++) {
            if (!oit.hasNext() || !Objects.equals(es[from], oit.next())) {
                return false;
            }
        }
        return !oit.hasNext();
    }

    private boolean equalsArrayList(MyArrayList<?> other) {
        final int otherModCount = other.modCount;
        final int s = size;
        boolean equal;
        if (equal = (s == other.size)) {
            final Object[] otherEs = other.elementData;
            final Object[] es = elementData;
            for (int i = 0; i < s; i++) {
                if (!Objects.equals(es[i], otherEs[i])) {
                    equal = false;
                    break;
                }
            }
        }
        if (other.modCount != otherModCount) {
            throw new ConcurrentModificationException();
        }
        return equal;
    }

    @Override
    public int hashCode() {
        int expectedModCount = modCount;
        int hash = hashCodeRange(0, size);
        if (modCount != expectedModCount) {
            throw new ConcurrentModificationException();
        }
        return hash;
    }

    private int hashCodeRange(int from, int to) {
        final Object[] es = elementData;
        int hashCode = 1;
        for (int i = from; i < to; i++) {
            Object e = es[i];
            hashCode = 31 * hashCode + (e == null ? 0 : e.hashCode());
        }
        return hashCode;
    }

    @Override
    public String toString() {
        final int s = size;
        if (s == 0) {
            return "[]";
        }
        final Object[] es = elementData;
        StringBuilder sb = new StringBuilder(2 + s * 4);
        sb.append('[');
        for (int i = 0; i < s; i++) {
            if (i > 0) {
                sb.append(", ");
            }
            Object e = es[i];
            sb.append(e == this ? "(this Collection)" : e);
        }
        return sb.append(']').toString();
    }
```

The two-path `equals` is the same optimisation the real one uses (`java.base/java/util/ArrayList.java`, JDK 21, line 1000): against another instance of the same class, compare arrays index-by-index and skip iterator allocation entirely; against any other `List`, fall back to walking the other side's iterator, because that is the only access it is guaranteed to offer cheaply. Both paths check the *other* list's `modCount` too, so comparing against a concurrently mutating list fails loudly rather than returning a stale answer.

`hashCode` is the `List` contract's exact formula, `31 * h + e.hashCode()`, seeded at 1. It is not negotiable — deviating breaks `Set<List<T>>` and `Map<List<T>, V>` against any other implementation.

`toString` is overridden rather than inherited from `AbstractCollection` only to avoid the iterator allocation; the `(this Collection)` guard preserves `AbstractCollection`'s self-reference behaviour so a list containing itself prints instead of overflowing the stack.

**Verified** against the real one:

```
mine.equals(theirs) -> true
theirs.equals(mine) -> true
hashCodes match     -> true
toString            -> true [a, b]
```

`theirs.equals(mine)` returning `true` is the symmetry test: `java.util.ArrayList.equals` takes the generic `List` path against our class and still agrees.

**Pitfall:** overriding `equals` on a mutable collection means its hash code changes when its contents do. A `MyArrayList` used as a `HashMap` key and then mutated is stranded — the map can no longer find it. See [D-16](../diagrams/D-16-mutable-key-stranding.svg).

> `List` equality and hashing are interface-level contracts over the first `size` elements in order; a correct implementation must agree with every other `List`, in both directions.

---

### The bulk operations and the bitset compaction (4.1.12)

**Mental model.** Naive bulk removal is quadratic: each `remove` shifts the whole tail, so deleting *k* elements from *n* costs O(n·k). The fix is a single **read-write cursor pass** — walk with a read pointer `r`, copy survivors down to a write pointer `w`, then null everything from `w` to the old end. One pass, O(n), one `arraycopy` at the tail.

**Why `removeIf` needs more than that.** `removeAll` and `retainAll` ask a `Collection.contains`, which is a read. `removeIf` calls arbitrary user code. If that predicate reads the list, a single-pass compaction would show it a half-compacted array. So `removeIf` does **two** passes: pass one evaluates the predicate against the untouched array and records verdicts in a bitset; pass two compacts using only the bitset, calling nothing. The predicate never observes a torn list.

**When each is the right tool.** `removeIf` for a predicate. `removeAll`/`retainAll` for set-shaped filtering — and pass a `HashSet`, never a `List`, because `c.contains` runs once per element. `addAll` for bulk insertion, which sizes the array once via `grow(s + numNew)` instead of growing repeatedly.

```java
    @Override
    public boolean addAll(Collection<? extends E> c) {
        Object[] a = c.toArray();
        modCount++;
        int numNew = a.length;
        if (numNew == 0) {
            return false;
        }
        Object[] es = elementData;
        final int s = size;
        if (numNew > es.length - s) {
            es = grow(s + numNew);
        }
        System.arraycopy(a, 0, es, s, numNew);
        size = s + numNew;
        return true;
    }

    @Override
    public boolean addAll(int index, Collection<? extends E> c) {
        rangeCheckForAdd(index, size);
        Object[] a = c.toArray();
        modCount++;
        int numNew = a.length;
        if (numNew == 0) {
            return false;
        }
        Object[] es = elementData;
        final int s = size;
        if (numNew > es.length - s) {
            es = grow(s + numNew);
        }
        int numMoved = s - index;
        if (numMoved > 0) {
            System.arraycopy(es, index, es, index + numNew, numMoved);
        }
        System.arraycopy(a, 0, es, index, numNew);
        size = s + numNew;
        return true;
    }

    @Override
    public boolean removeAll(Collection<?> c) {
        return batchRemove(c, false, 0, size);
    }

    @Override
    public boolean retainAll(Collection<?> c) {
        return batchRemove(c, true, 0, size);
    }

    boolean batchRemove(Collection<?> c, boolean complement, final int from, final int end) {
        Objects.requireNonNull(c);
        final Object[] es = elementData;
        int r;
        for (r = from;; r++) {            // skip the initial run of survivors
            if (r == end) {
                return false;             // nothing to remove: array untouched
            }
            if (c.contains(es[r]) != complement) {
                break;
            }
        }
        int w = r++;
        try {
            for (Object e; r < end; r++) {
                if (c.contains(e = es[r]) == complement) {
                    es[w++] = e;
                }
            }
        } catch (Throwable ex) {
            // c.contains threw: salvage the untested tail so the list stays consistent
            System.arraycopy(es, r, es, w, end - r);
            w += end - r;
            throw ex;
        } finally {
            modCount += end - w;
            shiftTailOverGap(es, w, end);
        }
        return true;
    }
```

`batchRemove` unifies `removeAll` and `retainAll` behind one boolean. `complement == false` keeps elements *not* in `c`; `complement == true` keeps elements in `c`. The initial skip loop means a call that removes nothing performs zero writes and returns `false` without dirtying a cache line.

The `catch (Throwable)` block is the subtle one. If `c.contains` throws partway through — a `TreeSet` with an incompatible comparator will — the array is half-compacted, with survivors below `w` and untested elements from `r` to `end`. Rather than leave a corrupt list, the handler slides the untested tail down and lets the `finally` run the normal fixup, so the exception propagates from a *consistent* list. `java.util.ArrayList` documents this as preserving behavioural compatibility with `AbstractCollection` (line 913).

`modCount += end - w` in the `finally` counts the number of elements actually removed rather than incrementing by one. That is the only place in the class where `modCount` moves by more than 1.

Now the bitset:

```java
    private static long[] nBits(int n) {
        return new long[((n - 1) >> 6) + 1];
    }

    private static void setBit(long[] bits, int i) {
        bits[i >> 6] |= 1L << i;
    }

    private static boolean isClear(long[] bits, int i) {
        return (bits[i >> 6] & (1L << i)) == 0;
    }

    @Override
    public boolean removeIf(Predicate<? super E> filter) {
        return removeIf(filter, 0, size);
    }

    boolean removeIf(Predicate<? super E> filter, int i, final int end) {
        Objects.requireNonNull(filter);
        int expectedModCount = modCount;
        final Object[] es = elementData;
        for (; i < end && !filter.test(elementAt(es, i)); i++) {
            // skip the initial run of survivors: nothing to copy yet
        }
        if (i < end) {
            final int beg = i;
            final long[] deathRow = nBits(end - beg);
            deathRow[0] = 1L;                       // element at beg is already condemned
            for (i = beg + 1; i < end; i++) {
                if (filter.test(elementAt(es, i))) {
                    setBit(deathRow, i - beg);
                }
            }
            if (modCount != expectedModCount) {
                throw new ConcurrentModificationException();
            }
            modCount++;
            int w = beg;
            for (i = beg; i < end; i++) {
                if (isClear(deathRow, i - beg)) {
                    es[w++] = es[i];
                }
            }
            shiftTailOverGap(es, w, end);
            return true;
        } else {
            if (modCount != expectedModCount) {
                throw new ConcurrentModificationException();
            }
            return false;
        }
    }
```

`nBits(n)` is `((n - 1) >> 6) + 1` — ceiling division by 64 without a division instruction. For n = 64 it gives 1; for n = 65, 2. The bitset is allocated only for the range from the *first* condemned element onward, so `removeIf` over a list whose first million elements all survive allocates a bitset sized for the remainder, not for the million.

`setBit` and `isClear` use `bits[i >> 6] |= 1L << i` with **no mask on the shift**. That looks like a bug and is not: Java's `<<` on a `long` uses only the low 6 bits of the shift distance, so `1L << 70` is `1L << 6` — exactly the within-word position that `i >> 6` word-indexing needs. Two operations instead of three, on a loop that runs once per element.

`deathRow[0] = 1L` pre-condemns the element that broke the skip loop, so the second loop can start at `beg + 1` and never re-evaluate the predicate on it. Predicates are user code and may be expensive or non-idempotent; evaluating each element exactly once is a contract, not an optimisation.

The comodification check between the two passes is what catches a predicate that mutated the list. Reads are tolerated; writes are caught. `modCount++` comes *after* that check, so the compaction pass itself is the only structural change recorded.

**Verified:**

```
removeIf(even)      -> true [1, 3, 5, 7, 9]
removeAll([b,d])    -> [a, c]
addAll(1,[x,y])     -> [a, x, y, c]
retainAll([a,y])    -> [a, y]
```

**Insight:** the two-pass structure costs one `long[]` allocation of `size/64` words — 16 bytes for a thousand-element list — and buys both single-evaluation of the predicate and a coherent view for reentrant reads. That is the trade the JDK made, and it is why `removeIf` is not simply a loop over `batchRemove`.

**Interview:** *Why is `list.removeAll(otherList)` sometimes catastrophically slow?* Because `batchRemove` calls `c.contains` once per element, and `List.contains` is O(m). Total O(n·m). Wrapping the argument in a `HashSet` first makes it O(n + m).

> Bulk removal is a read-write cursor compaction; `removeIf` splits it into a predicate pass recorded in a bitset and a copy pass that calls nothing, so user code never sees a partially compacted array.

---

### `sort(Comparator)` in place (4.1.13)

```java
    @Override
    @SuppressWarnings("unchecked")
    public void sort(Comparator<? super E> c) {
        final int expectedModCount = modCount;
        Arrays.sort((E[]) elementData, 0, size, c);
        if (modCount != expectedModCount) {
            throw new ConcurrentModificationException();
        }
        modCount++;
    }
```

Four lines, three decisions.

`Arrays.sort(array, from, to, comparator)` sorts the live backing array *in place* over the first `size` slots. No copy, no intermediate list. The cast `(E[]) elementData` is unchecked and safe under erasure — the array's runtime type is `Object[]`, and the comparator only ever sees elements this list put there.

The `expectedModCount` check runs **after** the sort, not before, because the interference it is looking for is a comparator that mutates the list mid-sort. `Arrays.sort` uses TimSort, which will already have thrown `IllegalArgumentException: Comparison method violates its general contract!` in most such cases, but a comparator that merely *adds* to the list without breaking transitivity would slip through — and `size` would then be stale, leaving a list whose tail is unsorted and whose invariants are broken. The post-check turns that into a `ConcurrentModificationException`.

`modCount++` at the end is contentious and the JDK does it too. Sorting is not a structural change by the strict definition — the size does not change. But every live iterator's position now refers to a different element, which is exactly the kind of silent wrongness fail-fast exists to prevent, so `sort` is classified structural. `replaceAll` bumps it for the same reason (`java.base/java/util/ArrayList.java`, JDK 21, line 1795, where the JDK's own comment flags it as tracked under bug 8203662).

**Verified:** `[pear, fig, apple, kiwi]` sorted by natural order gives `[apple, fig, kiwi, pear]`; re-sorted by `comparingInt(String::length).reversed()` gives `[apple, kiwi, pear, fig]` — `kiwi` before `pear` because TimSort is stable and they were in that order after the first sort.

> `sort` is `Arrays.sort` over the live array with a post-hoc comodification check, and it bumps `modCount` because reordering invalidates cursors even though it does not change size.

---

### `spliterator()` with late binding and midpoint `trySplit` (4.1.14)

**Mental model.** A spliterator is an iterator that can hand you half of itself. `trySplit` cuts the remaining range at its midpoint, returns the left half as a new spliterator, and keeps the right half. Recursively applied by the fork-join framework, this produces a balanced tree of leaf tasks — see [D-124a](../diagrams/D-124a-arraylist-split.svg) and [D-123](../diagrams/D-123-tryspt-recursion.svg).

**Why array-backed lists are the best case for parallel streams.** Splitting is O(1) integer arithmetic. Every subtask knows its exact element count in advance, which is what `SIZED` and `SUBSIZED` advertise, so the framework can size output arrays without buffering. Contrast `LinkedList`, which must walk to find a midpoint and reports `SIZED` but not `SUBSIZED`.

```java
    @Override
    public Spliterator<E> spliterator() {
        return new MySpliterator(0, -1, 0);
    }

    final class MySpliterator implements Spliterator<E> {
        private int index;            // current position
        private int fence;            // -1 until bound; then one past the last index
        private int expectedModCount; // set when the fence is set

        MySpliterator(int origin, int fence, int expectedModCount) {
            this.index = origin;
            this.fence = fence;
            this.expectedModCount = expectedModCount;
        }

        private int getFence() {
            int hi;
            if ((hi = fence) < 0) {
                expectedModCount = modCount;
                hi = fence = size;
            }
            return hi;
        }

        @Override
        public MySpliterator trySplit() {
            int hi = getFence(), lo = index, mid = (lo + hi) >>> 1;
            return (lo >= mid) ? null : new MySpliterator(lo, index = mid, expectedModCount);
        }

        @Override
        public boolean tryAdvance(Consumer<? super E> action) {
            Objects.requireNonNull(action);
            int hi = getFence(), i = index;
            if (i < hi) {
                index = i + 1;
                action.accept(elementAt(elementData, i));
                if (modCount != expectedModCount) {
                    throw new ConcurrentModificationException();
                }
                return true;
            }
            return false;
        }

        @Override
        public void forEachRemaining(Consumer<? super E> action) {
            Objects.requireNonNull(action);
            final Object[] es = elementData;
            int i, hi, mc;
            if ((hi = fence) < 0) {
                mc = modCount;
                hi = size;
            } else {
                mc = expectedModCount;
            }
            if ((i = index) >= 0 && (index = hi) <= es.length) {
                for (; i < hi; i++) {
                    action.accept(elementAt(es, i));
                }
                if (modCount == mc) {
                    return;
                }
            }
            throw new ConcurrentModificationException();
        }

        @Override
        public long estimateSize() {
            return getFence() - index;
        }

        @Override
        public int characteristics() {
            return Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED;
        }
    }
```

Three decisions, all about *when* state is captured.

**`fence == -1` means unbound.** The spliterator returned by `spliterator()` has not yet decided what range it covers or what `modCount` it expects. It commits on the first call to `getFence()`. This is **late binding**, and it is the reason `list.stream()` can be built, elements added, and *then* traversed, picking up the additions. Capturing `size` in the constructor would break that and is the single most common mistake in a hand-rolled spliterator. `java.util.ArrayList` documents the rationale at line 1631.

**`mid = (lo + hi) >>> 1`, unsigned shift.** `(lo + hi)` can overflow into a negative `int` on very large ranges; `>>> 1` treats the sum as unsigned and recovers the correct midpoint. `(lo + hi) / 2` would give a negative index. This is the same fix as the famous binary-search overflow bug.

**`trySplit` returns `null` when `lo >= mid`.** A range of 0 or 1 elements cannot be usefully halved, and returning a spliterator over an empty range would make the fork-join framework recurse forever. `null` means "I am a leaf".

`forEachRemaining` sets `index = hi` *before* the loop and checks `modCount` only *after* it, so the hot loop is a bare array walk with no per-element bookkeeping — the reason `list.stream().forEach(...)` is close to a raw `for` loop in throughput. `tryAdvance` cannot make that trade and checks per element.

**Verified:**

```
parallel sum 1..1000 -> 500500
trySplit halves      -> 500 + 500 characteristics=SIZED:true SUBSIZED:true
```

**Pitfall:** `SUBSIZED` is a promise that *every* child of a split is also `SIZED`. Advertising it when `trySplit` cannot guarantee exact child sizes causes the stream framework to allocate wrong-sized arrays and produce corrupt results with no exception. Only claim it when splitting is pure index arithmetic, as it is here.

> An array-backed spliterator binds its range and `modCount` lazily on first use, splits at the unsigned midpoint in O(1), and can honestly advertise `SIZED | SUBSIZED` because every child's exact count is known before traversal.

---

## Diff vs `java.util.ArrayList` (4.1.15)

| Aspect | `MyArrayList` | `java.util.ArrayList` (JDK 21) | Why the JDK bothers |
|---|---|---|---|
| Superclass | `extends AbstractList<E>` — inherits `containsAll`, `AbstractCollection` helpers, and the `modCount` field | Same (line 119) | Reuse; `AbstractList` also supplies the `ListIterator`-based defaults that `SubList` relies on |
| Methods inherited, not written | `containsAll`, `AbstractList`'s `iterator`/`listIterator` for `SubList`, `AbstractCollection.retainAll` shape | Same set inherited, but `ArrayList` additionally overrides `replaceAll`, `clone`, `readObject`/`writeObject` | Every override in the JDK exists to remove an iterator allocation or a redundant bounds check |
| Bounds checks | `Objects.checkIndex` for reads; hand-written `rangeCheckForAdd` for inserts | Identical, plus `outOfBoundsMsg` shared message builder | `Objects.checkIndex` is a HotSpot intrinsic candidate; the JIT can fold it into the array's own implicit check |
| Growth arithmetic | `newLength`/`hugeLength` **copied into the class** | Calls `jdk.internal.util.ArraysSupport.newLength` (line 237) | `ArraysSupport` is in a package not exported to the unnamed module, so third-party code *cannot* call it and must duplicate the logic — a real, unavoidable divergence |
| Array copying | `System.arraycopy`, `Arrays.copyOf` | Same | Both are HotSpot intrinsics compiled to vectorised block moves, not element loops |
| Serialization | **None.** Not `Serializable` | `implements java.io.Serializable`, `serialVersionUID = 8683452581122892189L`, custom `writeObject`/`readObject` writing only the live elements | Default serialization would write the whole backing array including trailing `null`s; the custom form writes `size` elements and rebuilds capacity on read |
| `Cloneable` | Not implemented | `implements Cloneable`, `clone()` does `Arrays.copyOf(elementData, size)` and resets `modCount` to 0 | Shallow copy at array speed; resetting `modCount` gives the clone a fresh iterator generation |
| `RandomAccess` | Implemented (marker) | Same | `Collections.binarySearch`, `shuffle`, `reverse` branch on it to pick index-based over iterator-based algorithms |
| Null policy | Nulls permitted everywhere; scans split on nullness; `equals` uses `Objects.equals`; `hashCode` maps null to 0 | Identical | `List` permits nulls by contract; only `List.of` and `Map.of` reject them |
| `Spliterator` | `ORDERED \| SIZED \| SUBSIZED`, late-bound fence, midpoint split | Identical (line 1620); additionally `ArrayList.SubList` supplies its own `ArrayListSpliterator` over the offset range | The JDK's sublist spliterator splits in O(1) too; ours inherits `AbstractList`'s `IteratorSpliterator`, which batches instead — correct but slower to split |
| `SubList` | Nested inner class, `offset`/`size`/`parent`, mirror `modCount` | Nested class with `root` *and* `parent` pointers (line 1194), so root access is one hop from any depth | With deep nesting our `MyArrayList.this` is still one hop, so the difference is stylistic; the JDK's form is what lets `SubList` be a static-ish class over any root |
| `removeIf` on `SubList` | Overridden, delegates to the parent's ranged `removeIf` | Same (`ArrayList.SubList.removeIf`) | Turns an O(n·k) `AbstractCollection` loop into one compaction pass |
| Allocation tricks | Two shared `{}` sentinels; bitset sized from the first condemned index; `StringBuilder` pre-sized `2 + size * 4` | Same three | An empty `ArrayList` costs 40 bytes of header and fields and **zero** array bytes — see [D-137](../diagrams/D-137-object-array-header-layout.svg) |
| Iterator `forEachRemaining` | Not overridden on `Itr` | Overridden (line 1074) to hoist `cursor`/`lastRet` writes out of the loop | Removes two heap writes per element from the hottest traversal path |
| `elementAt` helper | `static <E> E elementAt(Object[], int)` with `@SuppressWarnings` | Same shape, package-private | Confines the unchecked cast to one method the JIT inlines to nothing |
| `capacity()` | Public, for the demo | **Absent** | Publishing capacity would freeze the growth policy into the API contract permanently |
| `replaceAll`, `toArray(IntFunction)`, `Collections`-facing `sort` fast paths | Not implemented (inherited or absent) | Implemented | Each removes one iterator allocation from a commonly-called path |

**Insight:** almost every divergence in this table is either a module-boundary constraint (`ArraysSupport`) or an optimisation the JDK can afford because it is compiled once and run everywhere. None of them is a correctness difference — `MyArrayList` passes `equals` in both directions against `java.util.ArrayList` and produces identical `hashCode` and `toString`.

---

## A JMH sketch: append and mid-insert (4.1.16)

JMH is the only credible way to measure this. A `System.nanoTime()` loop will measure dead-code elimination, not your list. Current coordinates, verified against Maven Central: `org.openjdk.jmh:jmh-core:1.37` and the annotation processor `org.openjdk.jmh:jmh-generator-annprocess:1.37`.

```xml
<dependency>
  <groupId>org.openjdk.jmh</groupId>
  <artifactId>jmh-core</artifactId>
  <version>1.37</version>
</dependency>
<dependency>
  <groupId>org.openjdk.jmh</groupId>
  <artifactId>jmh-generator-annprocess</artifactId>
  <version>1.37</version>
  <scope>provided</scope>
</dependency>
```

```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;
import org.openjdk.jmh.infra.Blackhole;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 10, time = 1)
@Fork(value = 3, jvmArgsAppend = {"-XX:+UseParallelGC", "-Xms2g", "-Xmx2g"})
@State(Scope.Benchmark)
public class ListBenchmark {

    @Param({"1000", "100000"})
    private int n;

    private List<Integer> boxed;

    @Setup(Level.Trial)
    public void setUpTrial() {
        boxed = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            boxed.add(i);          // reused as source data; boxing happens once, not per invocation
        }
    }

    @Benchmark
    public MyArrayList<Integer> appendMine() {
        MyArrayList<Integer> l = new MyArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(boxed.get(i));
        }
        return l;                  // returned, so JMH's implicit Blackhole keeps it alive
    }

    @Benchmark
    public ArrayList<Integer> appendReal() {
        ArrayList<Integer> l = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(boxed.get(i));
        }
        return l;
    }

    @State(Scope.Thread)
    public static class MidInsertState {
        MyArrayList<Integer> mine;
        ArrayList<Integer> real;

        @Setup(Level.Invocation)   // fresh lists per invocation: insertion is destructive
        public void setUp() {
            mine = new MyArrayList<>();
            real = new ArrayList<>();
            for (int i = 0; i < 10_000; i++) {
                mine.add(i);
                real.add(i);
            }
        }
    }

    @Benchmark
    public void midInsertMine(MidInsertState s, Blackhole bh) {
        for (int i = 0; i < 1_000; i++) {
            s.mine.add(s.mine.size() / 2, i);
        }
        bh.consume(s.mine);
    }

    @Benchmark
    public void midInsertReal(MidInsertState s, Blackhole bh) {
        for (int i = 0; i < 1_000; i++) {
            s.real.add(s.real.size() / 2, i);
        }
        bh.consume(s.real);
    }
}
```

Run it with `java -jar target/benchmarks.jar ListBenchmark -prof gc`, and read the `gc.alloc.rate.norm` column as carefully as the time column — for append, allocation *is* the cost.

Five things this harness gets right that a hand-rolled timer does not.

`@Fork(3)` runs three separate JVMs. A single JVM's JIT profile is shaped by whichever benchmark ran first; forking exposes that as run-to-run variance instead of hiding it.

`@Setup(Level.Invocation)` on the mid-insert state is mandatory, because the benchmark mutates the list. Reusing one across invocations would make each iteration operate on a longer list than the last, and the numbers would drift upward with no explanation. JMH warns that `Level.Invocation` has its own timing overhead — that warning is acceptable here because the measured unit is a thousand inserts, orders of magnitude above the setup granularity.

Returning the list, or passing it to a `Blackhole`, is what stops the JIT from proving the whole loop dead and deleting it. This is the single most common way benchmarks lie.

Boxing is hoisted into `@Setup`. Without that, `appendMine` would be measuring `Integer.valueOf` — and the `IntegerCache` for values under 128 would make small-`n` runs look artificially fast. See [D-22](../diagrams/D-22-integer-cache.svg).

Fixed heap and a simple collector remove GC-sizing noise from a benchmark whose whole point is allocation behaviour.

**Unverified:** the actual throughput numbers this harness produces on any given machine. Running it here would report figures specific to this laptop's CPU and thermal state, which would be worse than no number at all. What the harness *is* expected to show, from the code alone: append times within noise of each other, since both classes execute the same `grow` arithmetic and the same `System.arraycopy` intrinsic; and mid-insert times within noise, dominated by the identical `arraycopy` shift. A published figure would need a specified CPU model, JDK build and `-prof perfnorm` output to be meaningful.

---

## Pitfalls

### Storing a `subList` and using it after touching the parent

**Wrong**

```java
MyArrayList<String> base = new MyArrayList<>(List.of("a", "b", "c", "d", "e"));
List<String> window = base.subList(1, 4);
base.add("f");                 // structural change to the parent, not through the view
System.out.println(window);    // ConcurrentModificationException
```

**Right**

```java
List<String> snapshot = List.copyOf(base.subList(1, 4));  // detached, immutable
base.add("f");
System.out.println(snapshot);                             // [b, c, d]
```

Or keep the view and route *all* mutation through it, which keeps the mirror in sync.

**Why people believe it:** `subList` returns a `List`, and every other `List` in the language is a value you can hold indefinitely. Nothing in the return type says "expires on the parent's next structural change".

### Passing a `List` to `removeAll` or `retainAll`

**Wrong**

```java
List<String> keep = someOtherList;      // 10 000 elements, a List
big.retainAll(keep);                    // 100 000 * 10 000 equals() calls
```

**Right**

```java
Set<String> keep = new HashSet<>(someOtherList);
big.retainAll(keep);                    // 100 000 hash lookups
```

`batchRemove` calls `c.contains(element)` once per element of the receiver. `ArrayList.contains` is a linear scan, so the pair is O(n·m). A `HashSet` makes it O(n + m) for the cost of one up-front copy.

**Why people believe it:** the signature is `Collection<?>`, which accepts both without complaint, and the asymptotic difference only shows up at scale — the unit test with five elements passes instantly either way.

### Capturing `size` in a hand-rolled spliterator's constructor

**Wrong**

```java
MySpliterator(int origin) {
    this.index = origin;
    this.fence = size;                  // bound eagerly at construction
    this.expectedModCount = modCount;
}
// Stream<E> s = list.stream();  list.add(x);  s.count();  -> misses x, or throws CME
```

**Right**

```java
private int getFence() {
    int hi;
    if ((hi = fence) < 0) {             // -1 means "not yet bound"
        expectedModCount = modCount;
        hi = fence = size;
    }
    return hi;
}
```

`Spliterator` is specified as *late-binding*: it binds to the source's contents at the point of first traversal or first split, not at construction. Binding early both violates the spec and turns a legal add-then-traverse into a spurious failure.

**Why people believe it:** a constructor is the natural place to capture state, and the eager version passes every test where the stream is consumed on the line it is created.

---

## Cheat sheet

| Item | Value / rule |
|---|---|
| `SubList` fields | `parent`, `offset`, `size`, mirrored `modCount` |
| `SubList` invalidation | any structural change to the parent not made through this view |
| `subList` bad range | `IndexOutOfBoundsException`; reversed range → `IllegalArgumentException` |
| `subList(a,b).clear()` | `AbstractList.clear` → `removeRange` → one `shiftTailOverGap` |
| `ensureCapacity(n)` on defaulted empty | no-op when `n <= 10` |
| `trimToSize()` on empty list | installs `EMPTY_ELEMENTDATA`, losing the inflate-to-10 default |
| `clear()` | nulls all live slots, keeps capacity |
| `hashCode` formula | `h = 1; h = 31*h + (e == null ? 0 : e.hashCode())` |
| `equals` fast path | same class → array walk; otherwise → other list's iterator |
| `batchRemove` | one boolean unifies `removeAll` (false) and `retainAll` (true) |
| `batchRemove` `modCount` | `+= end - w`, the only multi-increment in the class |
| `removeIf` passes | 1: predicate → bitset; 2: bitset → compaction. Predicate called exactly once per element |
| `nBits(n)` | `((n - 1) >> 6) + 1` — ceiling divide by 64 |
| `setBit` | `bits[i >> 6] \|= 1L << i` — no mask needed, `<<` uses low 6 bits |
| `sort` | `Arrays.sort` in place, post-hoc CME check, then `modCount++` |
| Spliterator characteristics | `ORDERED \| SIZED \| SUBSIZED` |
| Spliterator binding | late: `fence == -1` until first `getFence()` |
| `trySplit` midpoint | `(lo + hi) >>> 1`, unsigned to survive overflow; `null` when `lo >= mid` |
| Not implemented vs the real one | `Serializable`, `Cloneable`, `replaceAll`, `Itr.forEachRemaining`, `SubList` spliterator |
| JMH coordinates | `org.openjdk.jmh:jmh-core:1.37` + `jmh-generator-annprocess:1.37` |

---

## Self-test

**Q1.** A `SubList` keeps its own `size` field even though the parent's `size` is one dereference away. Why not compute it?

<details><summary>Answer</summary>

Because the view's length is not derivable from the parent's. A window `subList(1, 4)` onto a five-element list has length 3; if the parent grows to eight elements by an append, the window is still length 3, not 7. Only structural changes made *through* the view — or through a view nested inside it — should change its length, and `updateSizeAndModCount` applies exactly that delta and propagates it up the `parent` chain. A computed size would also make the fail-fast behaviour impossible: the whole point of the mirrored `modCount` is to notice that the parent changed *without* the view's knowledge, which requires the view to hold state that can disagree with the parent.

</details>

**Q2.** `trimToSize()` increments `modCount` before checking whether it will actually shorten the array. Is that a bug?

<details><summary>Answer</summary>

No, and the real one does the same (`java.base/java/util/ArrayList.java`, JDK 21, line 199). `trimToSize` may replace `elementData` with a *shorter* array. Any live iterator holds an `expectedModCount` and, in `next()`, checks `i >= elementData.length` specifically to catch a shortened array. If `modCount` were only bumped in the branch that actually reallocates, an iterator over a list where `size == elementData.length` — where the trim is a no-op — would be fine, but the unconditional bump costs one increment and removes the need to reason about that case at all. It also invalidates iterators after a trim that merely swapped in `EMPTY_ELEMENTDATA`, which is correct, since that reference change is exactly the one the length check is guarding against.

</details>

**Q3.** `setBit` is `bits[i >> 6] |= 1L << i` with no `& 63` on the shift distance. Why is that correct?

<details><summary>Answer</summary>

Java specifies that for a `long` left shift, only the low six bits of the right-hand operand are used — the shift distance is implicitly `i & 63`. So `1L << 70` is exactly `1L << 6`. Since `i >> 6` selects the 64-bit word and `i & 63` is the position within it, the implicit masking gives precisely the intended bit, and writing `1L << (i & 63)` would be redundant. This saves one AND instruction on a loop that runs once per element of the list. The identical trick appears in `java.util.BitSet` and in the JDK's own `ArrayList.setBit` (line 1731).

</details>

**Q4.** Why does `removeIf` use two passes and a bitset, when `batchRemove` gets away with a single read-write cursor pass?

<details><summary>Answer</summary>

Because `removeIf` calls arbitrary user code. A single-pass compaction mutates the array as it walks, so a predicate that reads the list — legally, since reads do not bump `modCount` — would observe a half-compacted array with duplicated elements below the write cursor. The two-pass form evaluates every predicate against the untouched array, records verdicts in the bitset, checks `modCount` to catch a predicate that *wrote*, and only then compacts using nothing but the bitset. It also guarantees each predicate is evaluated exactly once, which matters for expensive or non-idempotent predicates. `batchRemove`'s `c.contains` is a call into a collection, not into a closure over the list, so the JDK accepts the single-pass risk there — and still wraps it in a `catch (Throwable)` that repairs the array if `contains` throws.

</details>

**Q5.** `sort` checks `modCount` after `Arrays.sort` rather than before. What could a before-check possibly miss that the after-check catches?

<details><summary>Answer</summary>

A comparator that mutates the list during the sort. Before the sort there is nothing to detect — `modCount` is trivially equal to itself. The interference happens *inside* `Arrays.sort`, when TimSort calls back into `compare`. If that comparator adds to the list, `size` changes and `elementData` may be replaced, so the sort finishes having partially ordered an array that no longer describes the list. TimSort catches the subset of these cases that break its transitivity assumptions and throws `IllegalArgumentException: Comparison method violates its general contract!`, but a mutating-yet-consistent comparator slips past it. The post-check converts that into `ConcurrentModificationException`. The trailing `modCount++` is separate: it marks the reorder as structural so that any iterator created before the sort fails, since its cursor now names a different element.

</details>

**Q6.** What breaks if `trySplit` returns a spliterator over an empty range instead of `null`?

<details><summary>Answer</summary>

The fork-join framework recurses without bound. `AbstractTask` splits until `trySplit` returns `null`, treating that as the signal that a node is a leaf. An empty-range spliterator would be split again, yielding another empty one, forever — the symptom is a `StackOverflowError` or an unbounded growth in task objects, arriving well after the code looks correct in a sequential test. The guard `lo >= mid` covers ranges of 0 and 1 elements: for a range of 1, `lo` and `mid` coincide, so there is no way to produce two non-empty halves and the node correctly declares itself a leaf.

</details>

**Q7.** The diff table says `MyArrayList` cannot reproduce one specific JDK behaviour for reasons of module access rather than effort. Which, and what is the workaround?

<details><summary>Answer</summary>

Calling `jdk.internal.util.ArraysSupport.newLength`. `ArraysSupport` lives in the `jdk.internal.util` package of the `java.base` module, which is not exported to the unnamed module, so any third-party class referencing it fails to compile without `--add-exports`. The workaround used here is to copy `newLength` and `hugeLength` verbatim into `MyArrayList` as private static methods, along with the `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` constant. The logic is identical, so the growth sequence matches exactly; what is lost is any future JDK improvement to that method, and the possibility that HotSpot special-cases the internal version. This is the only entry in the diff table that is a hard constraint rather than a choice.

</details>

**Q8.** The JMH sketch uses `@Setup(Level.Trial)` for the append benchmark's source data but `@Setup(Level.Invocation)` for the mid-insert state. Why the different levels?

<details><summary>Answer</summary>

`Level.Trial` runs once per fork, before any warmup. The append benchmark's `boxed` list is read-only source data, so building it once is both correct and keeps `Integer.valueOf` boxing out of the measured region — otherwise the benchmark would partly measure the `IntegerCache`. The mid-insert benchmark *mutates* its lists, so reusing one across invocations would leave each invocation starting from a longer list than the last, and the measured time would climb steadily for reasons that have nothing to do with the code under test. `Level.Invocation` rebuilds a fresh 10 000-element list per invocation. JMH explicitly warns that `Level.Invocation` setup is itself timed at low granularity and can distort short benchmarks; that is acceptable here only because the measured work is a thousand mid-inserts into a ten-thousand-element list, far above the noise floor of the setup.

</details>

---

## The compile and run, verbatim

```
JAVA_HOME=$(/usr/libexec/java_home -v 21)
"$JAVA_HOME/bin/javac" -Xlint:all -d /tmp/jc-build-arraylist/out /tmp/jc-build-arraylist/*.java
"$JAVA_HOME/bin/java" -cp /tmp/jc-build-arraylist/out Demo
```

`javac 21.0.7`, zero errors and zero warnings under `-Xlint:all`. Full output of `Demo`:

```
default capacity before first add -> 0
default capacity after first add -> 10
capacity after 11 adds -> 15
zero-arg capacity before add -> 0
zero-arg capacity after 1 add -> 1
zero-arg capacity after 2 adds -> 2
zero-arg capacity after 3 adds -> 3
zero-arg capacity after 4 adds -> 4
add(2,"c") -> [a, b, c, d]
after remove(1) -> [a, c] size=2 capacity=3
slot past size is nulled -> true
remove(Object) missing -> false
for-each + add mid-iteration -> ConcurrentModificationException
Itr.remove drained without CME -> [a, c, d]
ListItr.add after 'a' -> [a, b, c] nextIndex=2
ListItr.previous -> b
ListItr.set on previous -> [a, B, c]
ListItr.set right after add -> IllegalStateException
subList(1,4) -> [b, c, d]
view.set(0,"B") writes through -> [a, B, c, d, e]
view.remove(0) shrinks parent -> [a, c, d, e] view=[c, d]
view read after parent structural change -> ConcurrentModificationException
removeIf(even) -> true [1, 3, 5, 7, 9]
sort(naturalOrder) -> [apple, fig, kiwi, pear]
sort(byLengthDesc) -> [apple, kiwi, pear, fig]
parallel sum 1..1000 -> 500500
trySplit halves -> 500 + 500 characteristics=SIZED:true SUBSIZED:true
mine.equals(theirs) -> true
theirs.equals(mine) -> true
hashCodes match -> true
toString -> true [a, b]
ensureCapacity(100) -> 100
trimToSize with 1 element -> 1
clear -> [] size=0 capacity=1
removeAll([b,d]) -> [a, c]
addAll(1,[x,y]) -> [a, x, y, c]
retainAll([a,y]) -> [a, y]
stream via sublist -> a|c
get(9) on size-3 list -> IndexOutOfBoundsException
IOOBE message -> Index 5 out of bounds for length 1
negative initial capacity -> IllegalArgumentException
```

---

**Leaves covered:** none — SUPERSEDED. This footer previously claimed 4.1.9-4.1.16; those leaves belong to rows 26c/26d/26e.
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 1069
