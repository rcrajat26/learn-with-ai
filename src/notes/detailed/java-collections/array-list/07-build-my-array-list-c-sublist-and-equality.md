# 02 Java Collections — `ArrayList` — INTERNALS (§4.1 `MyArrayList<E>` — the sublist view and equality)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/06-build-my-array-list-b-iterators.md](06-build-my-array-list-b-iterators.md) · Next: [array-list/08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md)

Part three of four. [05](05-build-my-array-list.md) built the storage core and [06](06-build-my-array-list-b-iterators.md) the iterators; this file adds the `SubList` view, the three capacity methods, and the value semantics. The complete compiling class is the concatenation of the code blocks in 05 through [08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md), in order.

---

## `SubList`'s field set, against the real one

| Field / member | `MyArrayList.SubList` | `java.util.ArrayList.SubList` (line 1194) | What it is for |
|---|---|---|---|
| Root list access | `MyArrayList.this` (inner class) | explicit `final ArrayList<E> root` field | Reaching the one real backing array |
| `parent` | `final SubList parent`, `null` at depth 1 | `final SubList<E> parent`, same | Propagating size changes outward through nested views |
| `offset` | `final int offset`, absolute into the root array | same | Translating view indices to array indices |
| `size` | `int size`, maintained independently | same | The window length; not derivable from the root's size |
| `modCount` | inherited from `AbstractList`, used as a **mirror** | same | Detecting changes the view did not make |
| Superclass | `extends AbstractList<E> implements RandomAccess` | same | Inheriting correct `iterator`, `equals`, `hashCode`, `clear` |
| Spliterator | inherited `AbstractList` default (batching) | own `ArrayListSpliterator` over the offset range (O(1) split) | The one behavioural gap; a diff-table row in [08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md) |

The only structural difference is the root pointer: an inner class reaches the root through `MyArrayList.this`, the JDK holds it in an explicit field. Both are one hop from any nesting depth.

---

### The `SubList` view (4.1.9)

**Mental model.** A sublist is not a copy. It is a pair of numbers — an offset and a length — plus a pointer back to the list it is a window onto. Reading through it adds the offset; writing through it writes the parent's array. There is exactly one array in the whole arrangement.

**Why it exists.** Range operations without copying. `list.subList(3, 7).clear()` deletes four elements in one `arraycopy`; the copying alternative allocates a four-element list, throws it away, and still needs a second loop to delete the originals. Every range-scoped algorithm in the JDK — `Collections.rotate`, `Collections.fill`, a windowed `binarySearch` — is written against a sublist for this reason.

**When to reach for it, and when not.** Reach for it for a scoped bulk operation, and for passing a window into a method that should not see the rest. Do *not* store one. A sublist is valid only until the next structural change to the parent made by anything other than that sublist; the moment the parent is touched directly, every read through the view throws `ConcurrentModificationException`. For a durable window, copy: `List.copyOf(list.subList(3, 7))`.

**How it works.** Three fields and one check. `offset` is the absolute index in the parent's array of this view's element 0. `size` is the window length, maintained independently. The inherited `modCount` is a *mirror* of the parent's counter at the moment the view was last in agreement with it; `checkForComodification` compares mirror to parent. `parent` chains nested sublists so a change through a deep view propagates outward.

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

**`subListRangeCheck` throws two different exception types.** Out-of-range endpoints give `IndexOutOfBoundsException`; a reversed range gives `IllegalArgumentException`. That is the `List.subList` contract, not an accident, and the real one does the same at line 1181.

**`updateSizeAndModCount` walks the `parent` chain.** Without it, a nested `subList(subList(list))` would update its own size and leave the enclosing view believing the old length; the enclosing view's next read would be out of bounds or silently wrong. The `do`/`while` runs at least once, so the view that made the change updates itself first, then propagates outward. The root list's own `size` was already adjusted by the delegated call.

**The mirror is only refreshed by changes made *through* a view.** A direct `parent.add(x)` bumps `MyArrayList.this.modCount` and touches no mirror, so the very next `view.size()` throws. That is intended and documented, and it is what makes sublists unsafe to cache.

**`removeIf` is overridden but `iterator`, `listIterator`, `contains`, `equals`, `hashCode` and `toString` are not.** The `AbstractList` versions are already correct here, because they are written in terms of `get`, `set`, `size` and `add`, every one of which runs `checkForComodification`. The view is therefore fail-fast even in the methods nobody wrote. `removeIf` gets an override only because delegating to the parent's ranged version ([08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md)) turns an O(n·k) `AbstractCollection` loop into a single compaction pass.

**Verified.** From the demo run:

```
subList(1,4)                             -> [b, c, d]
view.set(0,"B") writes through           -> [a, B, c, d, e]
view.remove(0) shrinks parent            -> [a, c, d, e] view=[c, d]
view read after parent structural change -> ConcurrentModificationException
stream via sublist                       -> a|c
```

`view.remove(0)` shrank the *parent* from five elements to four and the view from three to two, in one call, with no copy. The subsequent `base.add("f")` invalidated the view immediately.

**Interview:** *How does `list.subList(a, b).clear()` delete a range in one copy?* `AbstractList.clear()` calls `removeRange(0, size)`, `SubList.removeRange` translates by the offset and delegates to `MyArrayList.removeRange`, which calls `shiftTailOverGap` — one `System.arraycopy` plus the trailing-null loop.

> A sublist is an offset, a length, a parent pointer and a mirrored `modCount` — a window that reads and writes the parent's array directly and is invalidated by any structural change it did not itself make.

---

### `ensureCapacity`, `trimToSize`, `clear` (4.1.10)

Three supporting facts about capacity, one mechanism each. Capacity and size are independent: these three are the only public handles on capacity, and `clear` is not one of them.

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

`ensureCapacity`'s second clause is the sentinel test from [05](05-build-my-array-list.md): on a defaulted empty list, a request for 10 or fewer is a no-op, because the first `add` allocates 10 anyway and growing now would waste a copy. The leading `!` reads awkwardly; it says "grow, unless the only reason to grow is a request the default allocation already covers".

`trimToSize` bumps `modCount` unconditionally, before it knows whether it will do anything. Deliberate: replacing `elementData` with a shorter array is exactly the situation `Itr.next`'s `i >= es.length` check exists to catch ([06](06-build-my-array-list-b-iterators.md)), so any live iterator must be invalidated even in the borderline cases. It can also *reset the sentinel* — trimming an empty list installs `EMPTY_ELEMENTDATA`, so a defaulted list that is trimmed permanently loses its inflate-to-10 privilege and thereafter grows 1, 2, 3, 4.

`clear` nulls every live slot but does **not** shrink the array. Capacity survives, which is right for the reuse-the-buffer case and wrong if the list was briefly enormous; `clear()` then `trimToSize()` is the pair that actually releases the memory. The loop `for (int to = size, i = size = 0; i < to; i++)` sets `size` to 0 in the initialiser, so a reader sees an empty list from the first instant rather than a half-nulled one.

**Verified:** `ensureCapacity(100)` on a fresh list gives capacity 100; adding one element and calling `trimToSize()` gives capacity 1; `clear()` gives `[] size=0 capacity=1`.

> `ensureCapacity` and `grow` raise capacity, `trimToSize` lowers it, and `clear` touches only size.

---

### `equals`, `hashCode`, `toString` (4.1.11)

**Mental model.** `List` equality is a contract on the *interface*, not on the class. Any two `List` implementations holding equal elements in the same order must be equal and must hash the same. `MyArrayList` must therefore agree with `java.util.ArrayList`, `LinkedList`, `List.of` and everything else — in both directions.

**Why it is not `Arrays.equals` on the backing array.** Two lists can hold the same elements at different capacities, and `Arrays.equals` would compare the trailing nulls too. The contract is over the first `size` elements only.

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

The two-path `equals` is the optimisation the real one uses (line 1000): against another instance of the same class, compare arrays index-by-index and allocate no iterator; against any other `List`, walk the other side's iterator, which is the only cheap access it is guaranteed to offer. Both paths also snapshot and recheck the *other* list's `modCount`, so comparing against a concurrently mutating list fails loudly rather than returning a stale answer.

`hashCode` is the `List` contract's exact formula, `31 * h + e.hashCode()` seeded at 1. It is not negotiable — deviating breaks `Set<List<T>>` and `Map<List<T>, V>` against every other implementation.

`toString` is overridden rather than inherited from `AbstractCollection` only to avoid the iterator allocation and to pre-size the `StringBuilder`. The `(this Collection)` guard preserves `AbstractCollection`'s self-reference behaviour, so a list containing itself prints rather than overflowing the stack.

**Verified** against the real one:

```
mine.equals(theirs) -> true
theirs.equals(mine) -> true
hashCodes match     -> true
toString            -> true [a, b]
```

`theirs.equals(mine)` returning `true` is the symmetry test: `java.util.ArrayList.equals` takes its generic `List` path against our class and still agrees.

**Insight:** every one of these three methods snapshots `modCount` and rechecks it at the end. None of them mutates anything, so the check is not protecting the list — it is protecting the *answer*, which would otherwise be a value computed over two different versions of the same list.

> `List` equality and hashing are interface-level contracts over the first `size` elements in order; a correct implementation must agree with every other `List`, in both directions.

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

Or keep the view and route *all* mutation through it, which keeps the mirror in sync. Never return one across an API boundary.

**Why people believe it:** `subList` returns a `List`, and every other `List` in the language is a value you can hold indefinitely. Nothing in the return type says "expires on the parent's next structural change".

### Using a mutable list as a `HashMap` key or `HashSet` element

**Wrong**

```java
MyArrayList<String> key = new MyArrayList<>(List.of("a", "b"));
Map<List<String>, Integer> m = new HashMap<>();
m.put(key, 1);
key.add("c");                  // hashCode changed
System.out.println(m.get(key)); // null -- the entry is stranded in the old bucket
System.out.println(m.size());   // 1 -- it is still in there, just unreachable
```

**Right**

```java
List<String> key = List.copyOf(mutableSource);  // immutable snapshot, stable hash
m.put(key, 1);
```

`hashCode` is computed from the elements, so any structural change moves the object to a different bucket while the map's internal placement stays where it was. The entry becomes unreachable by lookup and undeletable by key — a slow leak that no exception announces. See [D-16](../diagrams/D-16-mutable-key-stranding.svg).

**Why people believe it:** the `Map` signature accepts any `K`, `put` succeeds, and the first `get` right after `put` works. The failure only appears after the key is mutated, often in a distant part of the program.

### Comparing lists with `==` or with `Arrays.equals` on the backing array

**Wrong**

```java
MyArrayList<String> a = new MyArrayList<>();      // capacity 10 after two adds
a.add("x"); a.add("y");
MyArrayList<String> b = new MyArrayList<>(2);     // capacity 2
b.add("x"); b.add("y");
System.out.println(a.elementData == b.elementData);              // false, obviously
System.out.println(Arrays.equals(a.elementData, b.elementData)); // false -- different lengths
```

**Right**

```java
System.out.println(a.equals(b));   // true -- compares the first `size` elements only
```

Capacity is not part of a list's value. `Arrays.equals` compares whole arrays including the trailing nulls, so two lists with identical contents and different growth histories compare unequal. `equals` iterates to `size` and stops.

**Why people believe it:** for a list built with an exact-capacity constructor and never grown, `Arrays.equals` happens to agree, so the shortcut passes its first test and fails once the list has grown even once.

---

## Cheat sheet

| Item | Value / rule |
|---|---|
| `SubList` fields | `parent`, `offset`, `size`, mirrored `modCount` |
| `SubList` invalidation | any structural change to the parent not made through this view |
| `subList` bad endpoint | `IndexOutOfBoundsException` |
| `subList` reversed range | `IllegalArgumentException` |
| `subList(a,b).clear()` | `AbstractList.clear` → `removeRange` → one `shiftTailOverGap` |
| Nested sublists | `offset` composes; `updateSizeAndModCount` walks the `parent` chain outward |
| Inherited by `SubList` | `iterator`, `listIterator`, `contains`, `equals`, `hashCode`, `toString`, `clear` |
| `ensureCapacity(n)` on defaulted empty | no-op when `n <= 10` |
| `trimToSize()` on empty list | installs `EMPTY_ELEMENTDATA`, losing the inflate-to-10 default |
| `trimToSize()` `modCount` | bumped unconditionally, before the size test |
| `clear()` | nulls all live slots, keeps capacity |
| Release memory after a spike | `clear()` then `trimToSize()` |
| `hashCode` formula | `h = 1; h = 31*h + (e == null ? 0 : e.hashCode())` |
| `equals` fast path | same class → array walk; otherwise → the other list's iterator |
| `equals` checks | both lists' `modCount`, snapshotted and rechecked |
| `toString` empty list | `"[]"`, returned before any `StringBuilder` is allocated |
| Self-containing list | prints `(this Collection)` rather than recursing |

---

## Self-test

**Q1.** A `SubList` keeps its own `size` field even though the parent's `size` is one dereference away. Why not compute it?

<details><summary>Answer</summary>

Because the view's length is not derivable from the parent's. A window `subList(1, 4)` onto a five-element list has length 3; if the parent grows to eight by an append, the window is still 3, not 7. Only structural changes made *through* the view — or through a view nested inside it — should change its length, and `updateSizeAndModCount` applies exactly that delta. A computed size would also make fail-fast impossible: the whole point of the mirrored `modCount` is to notice that the parent changed *without* the view's knowledge, which requires the view to hold state that can disagree with the parent. A derived size would silently absorb the disagreement instead of reporting it.

</details>

**Q2.** `subList` throws `IndexOutOfBoundsException` for a bad endpoint but `IllegalArgumentException` for `fromIndex > toIndex`. Why two types?

<details><summary>Answer</summary>

Because they are different kinds of error and the `List.subList` contract specifies both. `fromIndex < 0` or `toIndex > size` means an endpoint falls outside the list — a bounds problem, and `IndexOutOfBoundsException` is the family the rest of the API uses for that. `fromIndex > toIndex` has both endpoints in range; the *relationship* between them is nonsensical, which is an argument problem, not a bounds problem. Callers that catch `IndexOutOfBoundsException` to handle a clamped or off-by-one range should not accidentally swallow a reversed-range bug, which is almost always a genuine logic error rather than an edge case. `java.util.ArrayList.subListRangeCheck` at line 1181 makes the identical distinction.

</details>

**Q3.** `trimToSize()` increments `modCount` before checking whether it will actually shorten the array. Is that a bug?

<details><summary>Answer</summary>

No, and the real one does the same (line 199). `trimToSize` may replace `elementData` with a shorter array, and any live iterator both holds an `expectedModCount` and, in `next()`, checks `i >= elementData.length` specifically to catch a shortened array. Bumping only in the branch that reallocates would leave the no-op case — where `size == elementData.length` — technically safe, but the unconditional bump costs one increment and removes the need to reason about it. It also invalidates iterators after a trim that merely swapped in `EMPTY_ELEMENTDATA`, which is correct, since that reference change is exactly what the length check guards against.

</details>

**Q4.** `equals` has a fast path for `MyArrayList` and a slow path for every other `List`. Why can the fast path not just be used whenever the argument is a `RandomAccess` list?

<details><summary>Answer</summary>

Because the fast path reads the other object's `elementData` field directly, and only another `MyArrayList` has one. `RandomAccess` is a marker interface promising that `get(i)` is cheap, not that a backing array exists or is reachable. A `RandomAccess`-based path using `other.get(i)` would be possible and would avoid the iterator allocation, but it costs a virtual call and a bounds check per element, so the JDK does not bother — the iterator path is already close, and the array-versus-array comparison is where the real win is. Note both paths also snapshot the *other* list's `modCount`; the fast path can do that by field read, and the slow path gets it for free because the other list's own iterator is fail-fast.

</details>

**Q5.** Why does `hashCode` snapshot and recheck `modCount` when it does not modify anything?

<details><summary>Answer</summary>

To protect the answer rather than the list. `hashCodeRange` walks the array accumulating `31 * h + e.hashCode()`. If the list is structurally modified partway through — by another thread, or by a reentrant `hashCode()` on an element that happens to mutate the enclosing list — the returned value is computed over two different versions of the list and corresponds to neither. Silently returning it is worse than failing, because that value will be used to place the list in a bucket it does not belong to, producing a stranded entry with no exception anywhere. The same reasoning applies to `equals` and to `forEach`. All three are read-only and all three are fail-fast.

</details>

**Q6.** What is the difference in memory effect between `list.clear()` and `list.subList(0, list.size()).clear()`?

<details><summary>Answer</summary>

None in the end state, and both are O(n). `list.clear()` nulls every live slot in a direct loop, sets `size` to 0, and keeps the backing array at its current capacity. The sublist form goes `AbstractList.clear()` → `SubList.removeRange(0, size)` → `MyArrayList.removeRange(0, size)` → `shiftTailOverGap(es, 0, size)`, which performs a zero-length `arraycopy` and then nulls the same slots. Capacity survives in both cases; neither releases the array. To actually free the memory after a spike you need `trimToSize()` afterwards. The sublist route does bump `modCount` twice rather than once, which matters only in that it invalidates iterators just as thoroughly.

</details>

**Q7.** `SubList` overrides `removeIf` but not `iterator`. Why is the inherited iterator safe, and why is the inherited `removeIf` not good enough?

<details><summary>Answer</summary>

Safe because `AbstractList`'s iterator is written entirely in terms of `get`, `set`, `size` and `remove`, and every one of those on `SubList` begins with `checkForComodification`. Any change to the parent that the view did not make is therefore caught on the next element access, so the view is fail-fast in code nobody wrote for it. Not good enough for `removeIf` because `AbstractCollection.removeIf` is a loop calling `Iterator.remove()`, and each of those removals shifts the parent's tail — O(n) per deletion, O(n·k) overall, plus a `modCount` bump and a mirror update each time. Delegating to the parent's ranged `removeIf` does the whole thing in one bitset-driven compaction pass ([08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md)), one `modCount` bump and one mirror update.

</details>

**Q8.** A nested `subList` composes offsets at construction: `this.offset = parent.offset + fromIndex`. What would break if it stored the relative offset and added the parent's at read time instead?

<details><summary>Answer</summary>

Correctness would survive but every read would walk the `parent` chain, turning an O(1) `get` into O(depth). Worse, the chain walk would have to happen on the write paths too, and `updateSizeAndModCount` already walks it — so a deeply nested view would pay the walk twice per mutation. Composing at construction makes `offset` an absolute index into the root array, so `get` is one addition and one array read regardless of nesting depth, and the `parent` pointer is needed only for size propagation. The trade is that the offset can never be adjusted after construction, which is fine because a structural change to the parent invalidates the view anyway — the mirror check fires before any stale offset could be used.

</details>

---

**Leaves covered:** 4.1.9–4.1.11 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 545
