# Verified facts — java.util.ArrayList, JDK 21

Everything here was verified in this session against **real JDK 21.0.7 source**
(extracted from `src.zip`) and **real program runs on 21.0.7**. Treat it as
authoritative and prefer it over anything you recall or read online. Where you
quote an output, quote it exactly as it appears here — it is real output, not a
reconstruction.

You MAY read the extracted primary sources directly:

- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/util/ArrayList.java` (JDK 21.0.7, 1814 lines)
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/util/AbstractList.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/util/AbstractCollection.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/util/List.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/util/Collection.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/util/RandomAccess.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/java/lang/Iterable.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src/java.base/jdk/internal/util/ArraysSupport.java`
- `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk21src_sc/java.base/java/util/SequencedCollection.java`
- JDK 8 comparison: `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/jdk8src/java/util/ArrayList.java`
- JDK 11 / 17 comparison: `/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/j11/...`, `tmp/j17/...`

You may ALSO run your own experiments. A real JDK 21 is at
`/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/java`. Use
`/Users/rajat.chikkodikar/Desktop/My-files/rough/tmp/` as scratch. Reading real
capacity needs `--add-opens java.base/java.util=ALL-UNNAMED`.

You must **NOT** read anything under `src/notes/detailed/`, `src/topics/`,
`src/syllabus/`, or `src/scenario/` — the domain material you need is already in
your packet.

---

## 1. The field set — complete and exact

From JDK 21.0.7 `ArrayList.java`, with real line numbers:

| Line | Declaration | Role |
|---|---|---|
| 113 | `private static final long serialVersionUID = 8683452581122892189L;` | Serialization compatibility |
| 118 | `private static final int DEFAULT_CAPACITY = 10;` | Capacity on first growth of a default-constructed list |
| 123 | `private static final Object[] EMPTY_ELEMENTDATA = {};` | Shared sentinel for an explicitly zero-capacity list |
| 130 | `private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = {};` | Shared sentinel for a default-constructed list, kept distinct so `grow` knows to inflate to 10 |
| 138 | `transient Object[] elementData;` | The backing array. Package-private, not private, "to simplify nested class access". `transient` because serialization writes only the live elements. |
| 145 | `private int size;` | The number of live elements |

Plus **`protected transient int modCount`, declared in `AbstractList`, not in
`ArrayList`.** Verified: `ArrayList.class.getDeclaredField("modCount")` throws
`java.lang.NoSuchFieldException: modCount`.

**There is no `capacity` field.** Capacity *is* `elementData.length`.

The two empty sentinels being distinct is the whole trick, and it is
**observable**:

```
new ArrayList<>()  then one add  ->  capacity 10
new ArrayList<>(0) then one add  ->  capacity 1
```

---

## 2. `grow` in JDK 21 — the exact source

```java
private Object[] grow(int minCapacity) {
    int oldCapacity = elementData.length;
    if (oldCapacity > 0 || elementData != DEFAULTCAPACITY_EMPTY_ELEMENTDATA) {
        int newCapacity = ArraysSupport.newLength(oldCapacity,
                minCapacity - oldCapacity, /* minimum growth */
                oldCapacity >> 1           /* preferred growth */);
        return elementData = Arrays.copyOf(elementData, newCapacity);
    } else {
        return elementData = new Object[Math.max(DEFAULT_CAPACITY, minCapacity)];
    }
}

private Object[] grow() {
    return grow(size + 1);
}
```

And in `jdk.internal.util.ArraysSupport`:

```java
public static final int SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8;

public static int newLength(int oldLength, int minGrowth, int prefGrowth) {
    // preconditions not checked because of inlining
    // assert oldLength >= 0
    // assert minGrowth > 0

    int prefLength = oldLength + Math.max(minGrowth, prefGrowth); // might overflow
    if (0 < prefLength && prefLength <= SOFT_MAX_ARRAY_LENGTH) {
        return prefLength;
    } else {
        // put code cold in a separate method
        return hugeLength(oldLength, minGrowth);
    }
}

private static int hugeLength(int oldLength, int minGrowth) {
    int minLength = oldLength + minGrowth;
    if (minLength < 0) { // overflow
        throw new OutOfMemoryError(
            "Required array length " + oldLength + " + " + minGrowth + " is too large");
    } else if (minLength <= SOFT_MAX_ARRAY_LENGTH) {
        return SOFT_MAX_ARRAY_LENGTH;
    } else {
        return minLength;
    }
}
```

### CRITICAL — the thing most sources get wrong

**JDK 21 `ArrayList` has NO `MAX_ARRAY_SIZE` field and NO `hugeCapacity` method.**
The clamp lives in `ArraysSupport.SOFT_MAX_ARRAY_LENGTH`. Any note claiming
`ArrayList` has a private `MAX_ARRAY_SIZE` is describing pre-JDK-13 code. Do not
write it. Do call it out as a version trap where the file plan asks for that.

Note also that the clamp is **soft**: `hugeLength` can return `minLength` even
when that exceeds `SOFT_MAX_ARRAY_LENGTH`, so an array longer than
`Integer.MAX_VALUE - 8` is reachable if the caller genuinely needs it. It is a
preferred ceiling, not a hard limit — and that is why the constant is named
`SOFT_MAX`.

### Growth is 1.5x, never doubling

`prefGrowth` is `oldCapacity >> 1`, so the preferred new length is
`oldCapacity + (oldCapacity >> 1)`. Verified real sequence from a
default-constructed list on 21.0.7, reading `elementData.length` by reflection
after each of 400 appends:

```
0 -> 10 15 22 33 49 73 109 163 244 366 549
```

(The leading `0` is the lazily-allocated state straight after the constructor.)
Integer truncation makes each step slightly under 1.5x: `22 = 15 + 7`, not 22.5.

---

## 3. `add` and the inlining detail

```java
/**
 * This helper method split out from add(E) to keep method
 * bytecode size under 35 (the -XX:MaxInlineSize default value),
 * which helps when add(E) is called in a C1-compiled loop.
 */
private void add(E e, Object[] elementData, int s) {
    if (s == elementData.length)
        elementData = grow();
    elementData[s] = e;
    size = s + 1;
}

public boolean add(E e) {
    modCount++;
    add(e, elementData, size);
    return true;
}
```

That comment is real and is in the JDK source. Verified on 21.0.7:

```
intx C1MaxInlineSize = 35   {C1 product} {default}
intx MaxInlineSize   = 35   {C2 product} {default}
intx FreqInlineSize  = 325  {C2 pd product} {default}
```

`add(int index, E element)`:

```java
public void add(int index, E element) {
    rangeCheckForAdd(index);
    modCount++;
    final int s;
    Object[] elementData;
    if ((s = size) == (elementData = this.elementData).length)
        elementData = grow();
    System.arraycopy(elementData, index,
                     elementData, index + 1,
                     s - index);
    elementData[index] = element;
    size = s + 1;
}
```

---

## 4. Removal

```java
public boolean remove(Object o) {
    final Object[] es = elementData;
    final int size = this.size;
    int i = 0;
    found: {
        if (o == null) {
            for (; i < size; i++)
                if (es[i] == null)
                    break found;
        } else {
            for (; i < size; i++)
                if (o.equals(es[i]))
                    break found;
        }
        return false;
    }
    fastRemove(es, i);
    return true;
}

private void fastRemove(Object[] es, int i) {
    modCount++;
    final int newSize;
    if ((newSize = size - 1) > i)
        System.arraycopy(es, i + 1, es, i, newSize - i);
    es[size = newSize] = null;
}

public void clear() {
    modCount++;
    final Object[] es = elementData;
    for (int to = size, i = size = 0; i < to; i++)
        es[i] = null;
}
```

`remove(Object)` uses `o.equals(es[i])` — so the **argument's** `equals` is
called, and a null-hostile `equals` in an element type is not the deciding side.

`clear()` nulls every live slot but **does not shrink the array.** Verified:
capacity 100 after `trimToSize()` at size 100, then `clear()` leaves capacity
**100** with size 0.

`batchRemove`, which backs both `removeAll` and `retainAll`:

```java
boolean batchRemove(Collection<?> c, boolean complement,
                    final int from, final int end) {
    Objects.requireNonNull(c);
    final Object[] es = elementData;
    int r;
    // Optimize for initial run of survivors
    for (r = from;; r++) {
        if (r == end)
            return false;
        if (c.contains(es[r]) != complement)
            break;
    }
    int w = r++;
    try {
        for (Object e; r < end; r++)
            if (c.contains(e = es[r]) == complement)
                es[w++] = e;
    } catch (Throwable ex) {
        // Preserve behavioral compatibility with AbstractCollection,
        // even if c.contains() throws.
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

Two things worth teaching: it is a **single-pass read/write compaction** (`r` read
cursor, `w` write cursor), so `removeAll` is O(n) times the cost of
`c.contains`, not O(n²) — which is exactly why passing a `HashSet` rather than a
`List` as `c` matters. And the `catch` block preserves the un-scanned tail so the
list is left structurally valid even when `contains` throws.

`removeIf` uses a `long[]` bitset (`nBits`, `setBit`, `isClear` helpers) to mark
survivors in one pass and then compact once, rather than calling `remove` per
match, which would be O(n²).

---

## 5. `equals` and `hashCode` — both overridden, both can throw CME

```java
public boolean equals(Object o) {
    if (o == this) {
        return true;
    }

    if (!(o instanceof List)) {
        return false;
    }

    final int expectedModCount = modCount;
    // ArrayList can be subclassed and given arbitrary behavior, but we can
    // still deal with the common case where o is ArrayList precisely
    boolean equal = (o.getClass() == ArrayList.class)
        ? equalsArrayList((ArrayList<?>) o)
        : equalsRange((List<?>) o, 0, size);

    checkForComodification(expectedModCount);
    return equal;
}

public int hashCode() {
    int expectedModCount = modCount;
    int hash = hashCodeRange(0, size);
    checkForComodification(expectedModCount);
    return hash;
}

int hashCodeRange(int from, int to) {
    final Object[] es = elementData;
    if (to > es.length) {
        throw new ConcurrentModificationException();
    }
    int hashCode = 1;
    for (int i = from; i < to; i++) {
        Object e = es[i];
        hashCode = 31 * hashCode + (e == null ? 0 : e.hashCode());
    }
    return hashCode;
}
```

The `o.getClass() == ArrayList.class` test picks an array-to-array fast path
(`equalsArrayList`) and falls back to an iterator walk (`equalsRange`) for any
other `List`, including an `ArrayList` subclass.

Equality is **cross-implementation**, as the `List` contract requires. Verified:

```
ArrayList.equals(LinkedList) = true ; hash equal = true ; equals(List.of) = true
```

Both `equals` and `hashCode` can throw `ConcurrentModificationException` — a
genuinely surprising fact worth a callout.

---

## 6. The fail-fast iterator, and the case it misses

```java
private class Itr implements Iterator<E> {
    int cursor;       // index of next element to return
    int lastRet = -1; // index of last element returned; -1 if no such
    int expectedModCount = modCount;

    Itr() {}

    public boolean hasNext() {
        return cursor != size;
    }

    public E next() {
        checkForComodification();
        int i = cursor;
        if (i >= size)
            throw new NoSuchElementException();
        Object[] elementData = ArrayList.this.elementData;
        if (i >= elementData.length)
            throw new ConcurrentModificationException();
        cursor = i + 1;
        return (E) elementData[lastRet = i];
    }

    public void remove() {
        if (lastRet < 0)
            throw new IllegalStateException();
        checkForComodification();
        try {
            ArrayList.this.remove(lastRet);
            cursor = lastRet;
            lastRet = -1;
            expectedModCount = modCount;
        } catch (IndexOutOfBoundsException ex) {
            throw new ConcurrentModificationException();
        }
    }

    final void checkForComodification() {
        if (modCount != expectedModCount)
            throw new ConcurrentModificationException();
    }
}
```

**`hasNext()` is `cursor != size` and never consults `modCount`.** That single
line is why fail-fast is best-effort. Verified real outcomes on 21.0.7, list
`[AO-100, AO-400, AA-700]` iterated with a for-each:

| Action | Real result |
|---|---|
| remove `"AA-700"` (the **last** element) | `java.util.ConcurrentModificationException` |
| remove `"AO-400"` (the **second-to-last**) | **no exception.** Loop exits early; `AA-700` is never visited; list ends `[AO-100, AA-700]` |
| remove via `Iterator.remove()` | no exception, list ends `[AO-100, AA-700]` |
| `l.add(...)` inside `l.forEach(...)` | `java.util.ConcurrentModificationException` |

The second row is the mechanism: after removing the second-to-last element
`size` becomes 2 and `cursor` is already 2, so `hasNext()` returns false, `next()`
is never called again, and `checkForComodification` never runs.

---

## 7. `subList`

Returns `java.util.ArrayList$SubList` — a **private static nested class extending
`AbstractList` and implementing `RandomAccess`** — with fields `root`, `parent`,
`offset`, `size`. Verified behaviour on 21.0.7, base
`[DEP-301, DEP-400, BDP-100, BDP-200, BDP-300]`, `sub = base.subList(1, 4)`:

```
subList(1,4) = [DEP-400, BDP-100, BDP-200] class=java.util.ArrayList$SubList
sub.set(0, "DEP-999")  ->  base = [DEP-301, DEP-999, BDP-100, BDP-200, BDP-300]
base.add(...) then read sub  ->  java.util.ConcurrentModificationException
b2.subList(1,4).clear()  ->  b2 = [DEP-301, BDP-300]
```

The view holds a strong reference to the parent's whole array, so caching a
small view of a large list retains the large list.

---

## 8. Serialization

`elementData` is `transient`, and `writeObject`/`readObject` are custom. The list
writes its element count and then only the **live** elements, so the reserved
capacity is never serialized — a capacity-10 list holding 4 elements writes 4.
`readObject` calls
`SharedSecrets.getJavaObjectInputStreamAccess().checkArray(s, Object[].class, size)`
before allocating, which is a deserialization-bomb guard.
`serialVersionUID = 8683452581122892189L`. `writeObject` captures `modCount`
first and throws `ConcurrentModificationException` if it changed during writing.

---

## 9. Java 21 — `SequencedCollection`

`List<E> extends SequencedCollection<E>` in Java 21 (JEP 431). `SequencedCollection`
declares:

```java
SequencedCollection<E> reversed();          // abstract
default void addFirst(E e)
default void addLast(E e)
default E getFirst()
default E getLast()
default E removeFirst()
default E removeLast()
```

`ArrayList` **overrides** `getFirst`, `getLast`, `addFirst`, `addLast`,
`removeFirst`, `removeLast`, each tagged `@since 21` in the source. It does
**not** override `reversed()` — that arrives as a `List` default. Verified:

```
getFirst=AO-100 getLast=AA-700
reversed=[AA-700, AO-400, AO-100] reversed class=java.util.ReverseOrderListView$Rand
after rev.set(0,..) original=[AO-100, AO-400, AA-800]   -> reversed() is a VIEW
empty getFirst throws java.util.NoSuchElementException
```

`reversed()` is a **view**, not a copy — writes propagate to the original.

---

## 10. The complete surface — declaring types, mechanically extracted

### Declared (or overridden) in `ArrayList` itself — the full list

`trimToSize`, `ensureCapacity`, `size`, `isEmpty`, `contains`, `indexOf`,
`lastIndexOf`, `clone`, `toArray()`, `toArray(T[])`, `get`, `getFirst`,
`getLast`, `set`, `add(E)`, `add(int,E)`, `addFirst`, `addLast`, `remove(int)`,
`removeFirst`, `removeLast`, `equals`, `hashCode`, `remove(Object)`, `clear`,
`addAll(Collection)`, `addAll(int,Collection)`, `removeRange` (protected),
`removeAll`, `retainAll`, `listIterator(int)`, `listIterator()`, `iterator`,
`subList`, `forEach`, `spliterator`, `removeIf`, `replaceAll`, `sort`.

`trimToSize` and `ensureCapacity` are the only two with **no supertype
declaration** — they exist because the class is array-backed and nothing above it
has a capacity concept.

### Inherited and NOT overridden by `ArrayList`

| Member | Comes from | Note |
|---|---|---|
| `containsAll(Collection)` | `AbstractCollection` | O(n·m) — one `contains` per element of the argument |
| `toString()` | `AbstractCollection` | Builds via the iterator |
| `reversed()` | `List` (default, since 21) | Returns a `ReverseOrderListView` |
| `stream()`, `parallelStream()` | `Collection` (defaults) | Built on `spliterator()`, which **is** overridden |
| `toArray(IntFunction)` | `Collection` (default, since 11) | The generator form |

### Declaring-type facts specifically worth double-checking, all confirmed

- `replaceAll` — declared as a `default` in `List`, **overridden in `ArrayList`** (line 1784). Also overridden in JDK 8.
- `equals` / `hashCode` — declared in `Object`, specified in `List`, **overridden in `ArrayList`** in JDK 21 (lines 598, 662). **Not overridden in JDK 8** — inherited from `AbstractList` there.
- `listIterator()` (no-arg) — **overridden in `ArrayList`** (line 1017), in JDK 21 and JDK 8 alike.
- `sort` — declared as a `default` in `List`, **overridden in `ArrayList`** (line 1802).
- `spliterator` — `default` in both `Iterable` and `Collection` and re-declared as a `default` in `List`; **overridden in `ArrayList`** (line 1615).
- `removeIf` — `default` in `Collection`; **overridden in `ArrayList`** (line 1742).
- `forEach` — `default` in `Iterable`; **overridden in `ArrayList`** (line 1590).
- `iterator`, `listIterator(int)`, `subList`, `indexOf`, `lastIndexOf`, `clear`, `addAll(int,Collection)`, `removeRange`, `equals`, `hashCode`, `add(E)`, `add(int,E)`, `set`, `remove(int)` — all also declared in `AbstractList`, so in `ArrayList` these are **overrides of `AbstractList`**, not first declarations.
- `isEmpty`, `contains`, `toArray()`, `toArray(T[])`, `remove(Object)`, `addAll(Collection)`, `removeAll`, `retainAll` — also declared in `AbstractCollection`, so these are **overrides of `AbstractCollection`**.
- `size` — abstract in `AbstractCollection`, implemented in `ArrayList`.
- `clone` — declared in `Object`, overridden in `ArrayList`. It is a **shallow** copy: a new array, the same element references. It also resets `modCount` to 0 on the clone.

### `AbstractList` declares

`add(E)`, `get` (abstract), `set`, `add(int,E)`, `remove(int)`, `indexOf`,
`lastIndexOf`, `clear`, `addAll(int,Collection)`, `iterator`, `listIterator()`,
`listIterator(int)`, `subList`, `equals`, `hashCode`, `removeRange` (protected),
and the `protected transient int modCount` field.

### `AbstractCollection` declares

`iterator` (abstract), `size` (abstract), `isEmpty`, `contains`, `toArray()`,
`toArray(T[])`, `add(E)`, `remove(Object)`, `containsAll`, `addAll(Collection)`,
`removeAll`, `retainAll`, `clear`, `toString`.

### `Collection` defaults

`toArray(IntFunction)`, `removeIf`, `spliterator`, `stream`, `parallelStream`.

### `Iterable` defaults

`forEach`, `spliterator`.

### `RandomAccess`

Completely empty — a marker only. Its contract is that positional access is
roughly constant time, and library code branches on it: `Collections.binarySearch`,
`Collections.shuffle`, `Collections.reverse` and friends choose an index-based
algorithm for `RandomAccess` lists and an iterator-based one otherwise.

---

## 11. Version history — pinned by differential source reading

| JDK | Growth code | `MAX_ARRAY_SIZE` / `hugeCapacity` | `equals`/`hashCode` overridden? |
|---|---|---|---|
| 8 | `grow` inline, plus `ensureCapacityInternal` / `ensureExplicitCapacity` | **present** in `ArrayList` | **no** — inherited from `AbstractList` |
| 11 | `grow(int)` + private `newCapacity(int)` split | **present** | **yes**, with `equalsArrayList` fast path |
| 12 | same as 11 | **present** | yes |
| **13** | `grow(int)` delegates to `ArraysSupport.newLength` | **removed** | yes |
| 17 | same as 13 | removed | yes |
| 21 | same as 13, plus the `SequencedCollection` overrides | removed | yes |

**The `ArraysSupport.newLength` refactor landed in JDK 13**, not JDK 9 and not
JDK 18. Evidence: `jdk-12-ga` has 6 occurrences of `MAX_ARRAY_SIZE` and zero of
`ArraysSupport.newLength`; `jdk-13-ga` has zero and one. Local JDK 11 source
still has `MAX_ARRAY_SIZE` and `hugeCapacity`; local JDK 17 has neither.

For reference, the JDK 8 code that most online sources still describe:

```java
private static final int MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8;

private void grow(int minCapacity) {
    // overflow-conscious code
    int oldCapacity = elementData.length;
    int newCapacity = oldCapacity + (oldCapacity >> 1);
    if (newCapacity - minCapacity < 0)
        newCapacity = minCapacity;
    if (newCapacity - MAX_ARRAY_SIZE > 0)
        newCapacity = hugeCapacity(minCapacity);
    elementData = Arrays.copyOf(elementData, newCapacity);
}

private static int hugeCapacity(int minCapacity) {
    if (minCapacity < 0) // overflow
        throw new OutOfMemoryError();
    return (minCapacity > MAX_ARRAY_SIZE) ?
        Integer.MAX_VALUE :
        MAX_ARRAY_SIZE;
}
```

The JDK 11 intermediate form:

```java
private int newCapacity(int minCapacity) {
    // overflow-conscious code
    int oldCapacity = elementData.length;
    int newCapacity = oldCapacity + (oldCapacity >> 1);
    if (newCapacity - minCapacity <= 0) {
        if (elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA)
            return Math.max(DEFAULT_CAPACITY, minCapacity);
        if (minCapacity < 0) // overflow
            throw new OutOfMemoryError();
        return minCapacity;
    }
    return (newCapacity - MAX_ARRAY_SIZE <= 0)
        ? newCapacity
        : hugeCapacity(minCapacity);
}
```

**Open item, do not overstate:** the exact JDK that added the `equals`/`hashCode`
overrides was not separated between 9, 10 and 11 — the `jdk-10-ga` tag does not
exist in the `openjdk/jdk` repo and `bugs.openjdk.org` returned HTTP 403. State
the verified bracket: absent in JDK 8, present in JDK 11 and later.

---

## 12. Other verified behaviours and outputs

| What | Real result on 21.0.7 |
|---|---|
| `new ArrayList<>(4)` initial capacity | 4 |
| the same after 5 adds | **6** (`4 + (4>>1) = 6`) |
| `trimToSize()` at size 100, capacity 109 | capacity becomes 100 |
| `clear()` after that | capacity stays 100, size 0 |
| `List<Integer> l = [10,20,30]; l.remove(1)` | `[10, 30]` — removed **index** 1 |
| `l.remove(Integer.valueOf(20))` | `[10, 30]` — removed the **value** |
| `toArray(new String[0])` on a `List<Object>` holding `"DEP-301"` and `42` | `java.lang.ArrayStoreException: arraycopy: element type mismatch: can not cast one of the elements of java.lang.Object[] to the type of the destination array, java.lang.String` |
| `Arrays.asList("DEP-301","DEP-400").add(...)` | `java.lang.UnsupportedOperationException` |
| `Arrays.asList("DEP-301","DEP-400").set(0,"X")` | succeeds → `[X, DEP-400]` |
| `List.of("DEP-301","DEP-400").set(0,"X")` | `java.lang.UnsupportedOperationException` |
| `Arrays.asList("DEP-301").toArray().getClass()` | `[Ljava.lang.Object;` |
| `new ArrayList<>(Arrays.asList("DEP-301")).toArray().getClass()` | `[Ljava.lang.Object;` |
| `modCount` across operations | `sort` **increments** it; `set` does **not**; `add` does |
| `sort(null)` where the element type is not `Comparable` | `java.lang.ClassCastException` |
| `Comparator.comparingLong(LedgerEntry::postedAt).thenComparing(LedgerEntry::direction)` over ids E5,E1,E3,E2 | sorted ids `[E3, E1, E5, E2]` |
| `UseCompressedOops`, `ObjectAlignmentInBytes`, `UseCompressedClassPointers` | `true`, `8`, `true` |

**Do not overstate TimSort contract detection.** A comparator returning a
constant `1` over 40 elements did **not** throw
`IllegalArgumentException: Comparison method violates its general contract!` on
21.0.7. The exception is real but requires a particular run structure. Present it
as a detection that *may* fire, not one that always does.

---

## 13. Footprint arithmetic — assumptions stated

With `UseCompressedOops = true`, `UseCompressedClassPointers = true`,
`ObjectAlignmentInBytes = 8` (all verified above):

- Object header: 8 B mark + 4 B compressed klass = **12 B**
- `ArrayList` shell: 12 B header + 4 B `elementData` ref + 4 B `size` + 4 B `modCount` = **24 B**
- `Object[]` of capacity `n`: 12 B header + 4 B length + 4n B, rounded up to a multiple of 8
  - capacity 4 → 32 B; capacity 10 → 56 B; capacity 16 → 80 B
- A capacity-10, size-4 list therefore costs **24 + 56 = 80 B** for the list itself, excluding the elements.

Present this as arithmetic under those stated flags, which is honest, rather than
as a measured JOL figure, which was not run.
