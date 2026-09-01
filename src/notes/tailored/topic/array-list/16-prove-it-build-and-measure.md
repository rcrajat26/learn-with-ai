# `ArrayList` — 16 Prove it: build and measure

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: everything from files 01 through 15 — this file assembles them rather than introducing anything.
Previous: [15 Interoperation — streams, arrays and generics](15-interoperation-streams-arrays-and-generics.md) · Next: [17 Interview A — questions 1 to 19](17-interview-a-questions.md)

Reading about `elementData`, `grow`, `modCount` and the sentinel trick is not the same as having typed them. This file builds `LedgerEntryList<E>` — sized for the ledger's own volumes, the 1.8k-record bank payout file and the 500k-record month-end bank statement file (Appendix A.5) — then measures it against `java.util.ArrayList` on the numbers the JDK itself produces.

## Part 1 — the build (Q-44)

### Stage 1 — representation and construction

```java
package com.quizstakes.ledger.support;

import java.util.AbstractList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.RandomAccess;
import java.util.ConcurrentModificationException;

public class LedgerEntryList<E> extends AbstractList<E> implements RandomAccess {
    private static final int DEFAULT_CAPACITY = 10;
    private static final Object[] EMPTY = {};
    private static final Object[] DEFAULT_EMPTY = {};
    Object[] elementData;
    private int size;

    public LedgerEntryList() { this.elementData = DEFAULT_EMPTY; }

    public LedgerEntryList(int initialCapacity) {
        if (initialCapacity > 0) this.elementData = new Object[initialCapacity];
        else if (initialCapacity == 0) this.elementData = EMPTY;
        else throw new IllegalArgumentException("Illegal capacity: " + initialCapacity);
    }

    public LedgerEntryList(Collection<? extends E> source) {
        Object[] a = source.toArray();
        if ((size = a.length) != 0) {
            elementData = (source.getClass() == LedgerEntryList.class)
                    ? a : Arrays.copyOf(a, size, Object[].class);
        } else {
            elementData = EMPTY;
        }
    }

    @Override
    public int size() { return size; }
}
```

**Insight:** `DEFAULT_EMPTY` versus `EMPTY` is the two-sentinel trick copied verbatim — it distinguishes "no-arg, inflate to 10 on first add" from "capacity 0, inflate to exactly what's needed," so a `LedgerEntryList` that only ever inspects a 2-to-4-entry movement never pays for a wasted 10-null array. `AbstractList<E>` gives `iterator`, `equals`, `hashCode`, `toString`, `indexOf`, `subList` for free from `get`/`size` — every one is overridden below for speed. `RandomAccess` buys nothing here directly; it is read by `Collections.binarySearch`/`reverse`/`shuffle` to pick the index-loop strategy over the iterator strategy — the payoff lands in *other* code.

### Stage 2 — growth

`jdk.internal.util.ArraysSupport` is unreachable from application code, so `newLength` is reimplemented rather than called:

```java
    static final int SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8;

    static int newLength(int oldLength, int minGrowth, int prefGrowth) {
        int prefLength = oldLength + Math.max(minGrowth, prefGrowth); // may overflow
        return (0 < prefLength && prefLength <= SOFT_MAX_ARRAY_LENGTH)
                ? prefLength : hugeLength(oldLength, minGrowth);
    }
    private static int hugeLength(int oldLength, int minGrowth) {
        int minLength = oldLength + minGrowth;
        if (minLength < 0) throw new OutOfMemoryError("Required length too large: " + minLength);
        return minLength <= SOFT_MAX_ARRAY_LENGTH ? SOFT_MAX_ARRAY_LENGTH : minLength;
    }
    private Object[] grow(int minCapacity) {
        int oldCapacity = elementData.length;
        if (oldCapacity > 0 || elementData != DEFAULT_EMPTY)
            return elementData = Arrays.copyOf(elementData,
                    newLength(oldCapacity, minCapacity - oldCapacity, oldCapacity >> 1));
        return elementData = new Object[Math.max(DEFAULT_CAPACITY, minCapacity)];
    }

    private Object[] grow() { return grow(size + 1); }
```

**Pitfall:** without `Math.max(minGrowth, prefGrowth)`, capacity 1 computes `1 + (1 >> 1) = 1` and never grows again — `>> 1` is `0` at both capacity 0 and 1. `minGrowth` is always at least 1 for an append, so `max` forces one extra slot every time. `SOFT_MAX_ARRAY_LENGTH` is a ceiling on *ambition*, not *need*: `hugeLength` returns past it whenever the caller's minimum demands it, throwing only on genuine `int` overflow.

### Stage 3 — structural mutation

```java
    private void add(E e, Object[] elementData, int s) {
        if (s == elementData.length) elementData = grow();
        elementData[s] = e;
        size = s + 1;
    }

    @Override
    public boolean add(E e) { modCount++; add(e, elementData, size); return true; }
    // JDK splits add(E) this way to keep bytecode under 35 (-XX:MaxInlineSize);
    // verify with `javap -c -p LedgerEntryList.class`, not from prose.

    @Override
    public void add(int index, E element) {
        rangeCheckForAdd(index);
        modCount++;
        Object[] data = elementData;
        int s = size;
        if (s == data.length) data = grow();
        System.arraycopy(data, index, data, index + 1, s - index);
        data[index] = element;
        size = s + 1;
    }

    @Override
    @SuppressWarnings("unchecked")
    public E remove(int index) {
        Objects.checkIndex(index, size);
        E old = (E) elementData[index];
        fastRemove(elementData, index);
        return old;
    }
    private void fastRemove(Object[] es, int i) {
        modCount++;
        int newSize = size - 1;
        if (newSize > i) System.arraycopy(es, i + 1, es, i, newSize - i);
        es[size = newSize] = null;
    }

    @Override
    public boolean remove(Object o) {
        Object[] es = elementData;
        for (int i = 0; i < size; i++) {
            if (Objects.equals(o, es[i])) { fastRemove(es, i); return true; }
        }
        return false;
    }
    @Override
    public void clear() {
        modCount++;
        for (int i = 0; i < size; i++) elementData[i] = null;
        size = 0;
    }
    private void rangeCheckForAdd(int index) {
        if (index > size || index < 0)
            throw new IndexOutOfBoundsException("Index: " + index + ", Size: " + size);
    }
```

**Insight:** `remove(Object)` uses `Objects.equals` instead of the JDK's labelled-`break` null/`equals` split — clearer, one extra null check per element, not worth optimising off the settlement hot path. `add(int, E)` keeps the single `System.arraycopy` shift exactly as the JDK does — a JVM intrinsic that already handles overlapping ranges correctly.

### Stage 4 — the fail-fast iterator

```java
    @Override
    public java.util.Iterator<E> iterator() { return new Itr(); }

    private class Itr implements java.util.Iterator<E> {
        int cursor;
        int lastRet = -1;
        int expectedModCount = modCount;

        @Override
        public boolean hasNext() { return cursor != size; }

        @Override
        @SuppressWarnings("unchecked")
        public E next() {
            checkForComodification();
            int i = cursor;
            if (i >= size) throw new NoSuchElementException();
            if (i >= elementData.length) throw new ConcurrentModificationException();
            cursor = i + 1;
            return (E) elementData[lastRet = i];
        }

        @Override
        public void remove() {
            if (lastRet < 0) throw new IllegalStateException();
            checkForComodification();
            try {
                LedgerEntryList.this.remove(lastRet);
                cursor = lastRet;
                lastRet = -1;
                expectedModCount = modCount;
            } catch (IndexOutOfBoundsException ex) {
                throw new ConcurrentModificationException();
            }
        }

        final void checkForComodification() {
            if (modCount != expectedModCount) throw new ConcurrentModificationException();
        }
    }
```

`hasNext()` is `cursor != size`, copied deliberately rather than `cursor < size` — that is the entire fail-fast escape hatch. Proof it behaves identically to file 08's finding:

```java
List<LedgerEntry> four = new LedgerEntryList<>(List.of(e1, e2, e3, e4));
for (LedgerEntry e : four) if (e.equals(e2)) four.remove(e);
// throws ConcurrentModificationException — removing the 2nd of 4 is caught
List<LedgerEntry> alsoFour = new LedgerEntryList<>(List.of(e1, e2, e3, e4));
for (LedgerEntry e : alsoFour) if (e.equals(e3)) alsoFour.remove(e);
// no exception. alsoFour is now [e1, e2, e4] — the 3rd-of-4 removal escapes
```

**Pitfall:** after `next()` returns `e3`, `cursor == 3`; `remove(e3)` drops `size` to `3`; `hasNext()` computes `3 != 3` → `false`, the loop exits and `checkForComodification()` is never reached — `hasNext()` never consults `modCount` at all, by construction, in either class.

### Stage 5 — a `subList` view

```java
    @Override
    public List<E> subList(int fromIndex, int toIndex) {
        if (fromIndex < 0 || toIndex > size || fromIndex > toIndex)
            throw new IndexOutOfBoundsException("fromIndex: " + fromIndex + ", toIndex: " + toIndex);
        return new Sub<>(this, fromIndex, toIndex);
    }

    private static final class Sub<E> extends AbstractList<E> implements RandomAccess {
        private final LedgerEntryList<E> root;
        private final int offset;
        private int size;

        Sub(LedgerEntryList<E> root, int fromIndex, int toIndex) {
            this.root = root;
            this.offset = fromIndex;
            this.size = toIndex - fromIndex;
            this.modCount = root.modCount;
        }

        private void checkForComodification() {
            if (root.modCount != modCount) throw new ConcurrentModificationException();
        }
        @Override
        public int size() { checkForComodification(); return size; }
        @Override
        @SuppressWarnings("unchecked")
        public E get(int index) {
            Objects.checkIndex(index, size);
            checkForComodification();
            return (E) root.elementData[offset + index];
        }
        @Override
        public E set(int index, E element) {
            Objects.checkIndex(index, size);
            checkForComodification();
            return root.set(offset + index, element);
        }
        @Override
        public void add(int index, E element) {
            checkForComodification();
            root.add(offset + index, element);
            size++;
            modCount = root.modCount;
        }
        @Override
        public E remove(int index) {
            Objects.checkIndex(index, size);
            checkForComodification();
            E old = root.remove(offset + index);
            size--;
            modCount = root.modCount;
            return old;
        }
    }
```

**Pitfall:** `Sub` skips the JDK's `parent` chain — it points straight at the root, never at an enclosing `Sub`. The gap is a sub-sub-list — `list.subList(0, 10).subList(2, 5)` — because `Sub.add`/`remove` resync only *this* view's `size`/`modCount` from `root`, not from a `parent` two levels up, so a `Sub` of a `Sub` reads a stale `size`. The JDK's `updateSizeAndModCount` walks its `parent` chain precisely to avoid that; for a view scoped to "the entries of this one movement," never re-sliced again, the single-level form is enough — the cut corner is named, not hidden.

### Stage 6 — `equals`, `hashCode`, `toString`

```java
    @Override
    public boolean equals(Object o) {
        if (o == this) return true;
        if (!(o instanceof List<?> other)) return false;
        if (other.size() != size) return false;
        var it = other.iterator();
        for (int i = 0; i < size; i++) {
            if (!Objects.equals(elementData[i], it.next())) return false;
        }
        return true;
    }
    @Override
    public int hashCode() {
        int hash = 1;
        for (int i = 0; i < size; i++) {
            Object e = elementData[i];
            hash = 31 * hash + (e == null ? 0 : e.hashCode());
        }
        return hash;
    }
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < size; i++) sb.append(i > 0 ? ", " : "").append(elementData[i]);
        return sb.append(']').toString();
    }
```

The acceptance test — proof the `List` contract was followed, not approximated: both directions of `equals` plus matching `hashCode`, since `List.equals` is specified purely as `instanceof List`, size, pairwise `Objects.equals`.

```java
var mine = new LedgerEntryList<>(List.of(e1, e2, e3));
var jdk = new java.util.ArrayList<>(List.of(e1, e2, e3));
assert mine.equals(jdk) && jdk.equals(mine);
assert mine.hashCode() == jdk.hashCode();
```

### Stage 7 — a test `main`

```java
public final class LedgerEntryListDemo {
    public static void main(String[] args) {
        LedgerEntryList<LedgerEntry> list = new LedgerEntryList<>();
        for (String p : List.of("CLIENT_CASH_AVAILABLE", "CLIENT_CASH_RESERVED",
                "CLIENT_BONUS_AVAILABLE", "CLIENT_BONUS_RESERVED")) list.add(sample(p));
        System.out.println("size=" + list.size() + " -> " + list);

        list.add(1, sample("SUSPENSE"));
        list.remove(0);
        System.out.println("after add(1,x), remove(0): " + list);

        List<LedgerEntry> view = list.subList(0, 2);
        view.set(0, sample("FEES"));
        System.out.println("subList write-through, root now: " + list);

        var jdk = new java.util.ArrayList<>(list);
        System.out.println("equals both ways=" + (list.equals(jdk) && jdk.equals(list))
                + " hashCode match=" + (list.hashCode() == jdk.hashCode()));
    }

    private static LedgerEntry sample(String position) {
        return new LedgerEntry(java.util.UUID.randomUUID(), java.util.UUID.randomUUID(),
                position, Direction.CREDIT, new Money(new java.math.BigDecimal("4.20"), "GBP"),
                java.time.Instant.now());
    }
}

record Money(java.math.BigDecimal amount, String currency) {}
enum Direction { DEBIT, CREDIT }
record LedgerEntry(java.util.UUID id, java.util.UUID movementId, String position,
                    Direction direction, Money amount, java.time.Instant postedAt) {}
```

### The diff table

What the JDK does that this build does not, and what the JDK buys by paying for it:

| What it is | What this build does instead | What the JDK buys |
|---|---|---|
| `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` identity trick | Reproduced (as `DEFAULT_EMPTY`) | Distinguishes "grow to 10" from "grow to exactly what's asked" without a boolean flag |
| `add(E)` helper split at `MaxInlineSize = 35` | Same split, unverified bytecode size | Keeps the hot call sub-inline-threshold so C1/C2 can inline it in a tight loop |
| `removeIf`'s two-pass `deathRow` bitset | Not implemented (Self-test) | Tolerates a predicate that re-reads the list mid-scan; a single pass cannot |
| `batchRemove`'s `catch (Throwable)` repair | Not implemented; `remove(Object)` removes one match only | Leaves the array consistent even if `c.contains` throws mid-scan |
| `equalsArrayList` fast path | Not implemented; always iterator-driven | Indexes two backing arrays directly for the common ArrayList-vs-ArrayList case |
| `ArrayListSpliterator`'s lazy fence, `trySplit` | Not implemented (Self-test) | Zero-copy parallel decomposition; fence fixed at the latest possible moment |
| `transient elementData` + custom `writeObject` | Not implemented; not `Serializable` | Serializes `size` live elements, never the trailing capacity slack |
| `SubList`'s `parent` chain, `updateSizeAndModCount` | Single-level `Sub`, no chain (named above) | Nested sub-sub-lists stay consistent under mutation through any level |
| `Objects.checkIndex` intrinsified, plus two OOB message shapes | Reproduced: `checkIndex` in `get`/`Sub.get` (`"Index %d out of bounds for length %d"`) vs. `add`'s own `"Index: n, Size: n"` | JIT-recognised bounds check; old-message-parsing code keeps working across a version bump |

## Part 2 — the measurements (Q-45)

### 1. The growth trace

```java
java.lang.reflect.Field f = java.util.ArrayList.class.getDeclaredField("elementData");
f.setAccessible(true); // needs --add-opens java.base/java.util=ALL-UNNAMED
var list = new java.util.ArrayList<>();
int last = -1;
for (int i = 0; i < 260; i++) {
    int cap = ((Object[]) f.get(list)).length;
    if (cap != last) { System.out.print(cap + " -> "); last = cap; }
    list.add(i);
}
```

Printed on JDK 21.0.7 (Oracle, aarch64, macOS): default-constructed, `0 -> 10 -> 15 -> 22 -> 33 -> 49 -> 73 -> 109 -> 163 -> 244`; `new ArrayList<>(0)`: `0 -> 1 -> 2 -> 3 -> 4 -> 6 -> 9 -> 13`. A fresh default list's `ensureCapacity(5)` leaves capacity at **0** (5 is under the default 10 anyway); `ensureCapacity(11)` moves it to **11**. `LedgerEntryList` reproduces this identically — `grow`'s recurrence is copied verbatim. This is pure integer arithmetic, so your machine prints the same numbers.

### 2. The copy count

Computed from the exact recurrence in Stage 2, not measured, because the recurrence is exact:

```java
static void simulate(int n) {
    int cap = 0, copied = 0, grows = 0;
    boolean firstAlloc = true;
    while (cap < n) {
        int next = firstAlloc ? Math.max(10, cap + 1) : cap + Math.max(1, cap >> 1);
        if (!firstAlloc) copied += cap;
        cap = next;
        firstAlloc = false;
        grows++;
    }
    System.out.printf("n=%d grows=%d finalCap=%d wasted=%d copied=%d perElement=%.2f%n",
            n, grows, cap, cap - n, copied, copied / (double) n);
}
```

At `n = 100 000` (the packet's own JDK-measured case) this prints **24** grow calls, final capacity **106 710**, **6 710** wasted, **213 413** copied, **2.13** per element — matching the real figures exactly, because the recurrence *is* `grow`'s recurrence. At the QuizStakes volumes this file is scoped to: `n = 1 800` (one bank payout file, A.5) gives **14** grows, capacity **1 851**, **51** wasted, **3 690** copied, **2.05** per element; `n = 500 000` (one month-end bank statement file) gives **28** grows, capacity **540 217**, **40 217** wasted, **1 080 430** copied, **2.16** per element. Both ratios sit under the amortised bound `f / (f - 1)` at `f = 1.5`, which is **3** — the bound caps copies per element as `n → ∞`, it is not a target.

### 3. The footprint

```java
static long footprint(java.util.function.Supplier<List<Object>> ctor) {
    final int N = 200_000;
    List<Object>[] hold = new List[N];
    for (int g = 0; g < 4; g++) System.gc();
    long before = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory();
    for (int i = 0; i < N; i++) { hold[i] = ctor.get(); hold[i].add(new Object()); }
    for (int g = 0; g < 4; g++) System.gc();
    long after = Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory();
    return (after - before) / N;
}
```

Run with `-Xmx2g -Xms2g`. Printed on JDK 21.0.7 (Oracle, aarch64, macOS): `new ArrayList<>()` plus one element **80.2** bytes against arithmetic **80** (12-byte header + `modCount` + `size` + `elementData` ref = 24, plus a 10-slot array header+refs = 56); `new ArrayList<>(1)` plus one element **48.1** against **48**; `LinkedList` plus one element **56.1** against **56**; the empty-list case measured **21.4** against arithmetic **24** — honestly noise at this sample size (a coarse heap-usage delta over 200 000 instances isn't precise to a few bytes), not a refutation, since the other three rows matched within 0.2 bytes. This is a crude, dependency-free stand-in for a real memory tool; the tool that measures this properly is **JOL**, specifically `GraphLayout.parseInstance(list).totalSize()`.

### 4. The timing benchmark

```java
static long timeNanos(Runnable r) {
    long best = Long.MAX_VALUE;
    for (int i = 0; i < 10; i++) {
        long start = System.nanoTime();
        r.run();
        long elapsed = System.nanoTime() - start;
        if (i == 9) best = elapsed; // report the 10th warm iteration
    }
    return best;
}
```

Printed on JDK 21.0.7 (Oracle, aarch64, macOS), tenth warm iteration: 100 000 `add` on `new ArrayList<>()` **584 µs** versus `new ArrayList<>(100000)` **358 µs** — a **39 %** saving, all of it the growth copies §2 counted. A 200 000-element `get(i)` scan is **101 µs**; `ArrayList` for-each over the same list is **103 µs**, essentially the same cost, against **329 µs** for `LinkedList` — **3.2×** slower at identical O(n). `LinkedList.get(i)` over just the **first 20 000** of 200 000 took **352 ms** — roughly **3 500×** the cost of the *entire* 200 000-element `ArrayList` scan, because each call re-walks the node chain from an end.

This is a hand-rolled harness, not JMH: no forking, no dead-code-elimination guard beyond consuming the result, no statistical distribution. Any result inside roughly 2× should be re-run under JMH before it is believed; the 39 % saving is close enough to deserve that. The 3.2× and ~3 500× results are not — large enough, and mechanically explained (a node walk versus a pointer add), to survive the caveat as stated.

## Pitfalls

### Writing `grow` as `oldCapacity + (oldCapacity >> 1)` directly

**Wrong**
```java
private Object[] grow(int minCapacity) {
    int newCapacity = elementData.length + (elementData.length >> 1);
    return elementData = Arrays.copyOf(elementData, newCapacity);
}
```
At capacity 1, `1 + (1 >> 1) = 1 + 0 = 1` — the array is "grown" to the same size it already is. The next `add` sees `s == elementData.length` again, calls `grow` again, gets `1` again: either an infinite loop (if `add` retries) or, more commonly, the caller proceeds to write past the array it thinks just grew, throwing `ArrayIndexOutOfBoundsException` at capacity 1 specifically — a bug that survives every test built at capacity 0 or 10.

**Right**
```java
int newCapacity = newLength(oldCapacity, minCapacity - oldCapacity, oldCapacity >> 1);
```
`newLength`'s `Math.max(minGrowth, prefGrowth)` guarantees at least `minGrowth` (always ≥ 1 for an append) even when the 1.5× preferred growth rounds down to zero.

**Why people believe it:** every write-up of `ArrayList` growth quotes "1.5×" as the whole rule, and 1.5× of a normal-sized capacity never rounds to zero, so the edge case never shows up until someone starts a list from `new LedgerEntryList<>(1)`.

### Omitting the trailing null in `remove`

**Wrong**
```java
private void fastRemove(Object[] es, int i) {
    modCount++;
    int newSize = size - 1;
    if (newSize > i) System.arraycopy(es, i + 1, es, i, newSize - i);
    size = newSize; // no es[newSize] = null
}
```
Every unit test passes — `get`, `size`, `iterator`, `toString` all report the list as if the element were gone, because nothing reads past `size`. The removed `LedgerEntry` object is still referenced from `es[newSize]`, which is still reachable from the still-live `elementData` array.

**Right**
```java
es[size = newSize] = null;
```
One statement, two jobs: install the new `size` and null the now-unused slot so the removed element becomes collectible.

**Why people believe it:** the contract of `remove` is entirely about `size`, `get`, and iteration order — nothing in the `List` interface says anything about GC roots, so it is easy to satisfy every test while quietly pinning memory. It shows up only as a slow heap-usage climb in a long-lived ledger view, days later, in a heap dump.

### Reimplementing `equals` as `getClass() == that.getClass()`

**Wrong**
```java
@Override
public boolean equals(Object o) {
    if (o == this) return true;
    if (getClass() != o.getClass()) return false; // too strict
    LedgerEntryList<?> other = (LedgerEntryList<?>) o;
    return /* pairwise compare */ true;
}
```
It compiles, it passes any test that only ever compares two `LedgerEntryList` instances, and `new LedgerEntryList<>(List.of(e1)).equals(new java.util.ArrayList<>(List.of(e1)))` silently returns `false` even though both hold the identical single element.

**Right:** `if (!(o instanceof List<?> other)) return false;` — `List.equals` is specified across the whole interface, not within one implementation, precisely so an `ArrayList` and a `LinkedList` and a `LedgerEntryList` with the same elements in the same order are all equal to each other.

**Why people believe it:** `getClass() ==` is the textbook-safe pattern for `equals` on a general `Object`, taught to avoid asymmetric `equals` between unrelated types — but `List`, `Set`, and `Map` all specify their `equals` contracts in terms of the interface, not the implementing class, which is the one place the textbook pattern is wrong.

## Cheat sheet

| Piece | JDK's expression | Trap when reimplementing |
|---|---|---|
| Three fields | `elementData`, `size`, `modCount` (inherited) | Forgetting `modCount` lives on `AbstractList`, not on the list itself |
| Sentinel trick | `EMPTY_ELEMENTDATA` vs. `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` | Using one sentinel collapses "capacity 0 forever" into "grow to 10" |
| `grow` / `newLength` | `oldLength + Math.max(minGrowth, prefGrowth)` | Dropping the `Math.max` — capacity 1 never grows again |
| `add(int, E)` | one `System.arraycopy(data, index, data, index+1, s-index)` | Hand-rolling the shift with a loop instead of the overlap-safe intrinsic |
| `fastRemove` | `es[size = newSize] = null` | Skipping the trailing null — no crash, just a pinned reference |
| `Itr` | three ints: `cursor`, `lastRet`, `expectedModCount` | `hasNext()` as `cursor < size` instead of `cursor != size` — hides the fail-fast escape |
| `SubList` | `offset` into the root, no copy | Forgetting the `parent` chain — one-level views only, sub-sub-lists go stale |
| `equals` / `hashCode` | `instanceof List`, pairwise `Objects.equals`; `31*hash + e.hashCode()` | `getClass() ==` — breaks cross-implementation equality |

Measurement commands and the figure each should reproduce (JDK 21.0.7, Oracle, aarch64, macOS):

| Harness | Reproduces |
|---|---|
| Growth trace (reflection on `elementData`) | `0 → 10 → 15 → 22 → 33 → 49 → 73 → 109 → 163 → 244` |
| Copy-count simulation | 24 grows, 213 413 elements copied, 2.13 per element at n = 100 000 |
| Footprint (`totalMemory` − `freeMemory`, 200 000 instances) | 80.2 / 48.1 / 56.1 bytes for default / pre-sized / `LinkedList` + 1 element |
| Timing (`System.nanoTime`, 10 warm iterations) | 584 → 358 µs pre-sizing; 103 vs. 329 µs for-each; 352 ms `LinkedList.get(i)` |

## Self-test

**Q1.** Design `removeIf` for `LedgerEntryList` (diff table: not implemented). What does the JDK's two-pass `deathRow` bitset buy over a naive single-pass compaction, and where do `nBits`/`setBit`/`isClear` fit?

<details><summary>Answer</summary>

A single-pass compaction that shifts on every match is fine only if the predicate never reads the list; the JDK's Javadoc tolerates a predicate that reentrantly reads, and a single pass would show it a half-shrunk array mid-scan. Two passes separate "decide what dies" from "compact." Port it as `removeIf(Predicate<? super E> filter)`: loop `i` from `0` to `size` testing `filter.test(elementData[i])`, setting a bit in `long[] deathRow` sized `((size - 1) >> 6) + 1` instead of mutating; after the scan, bump `modCount` once, then a second loop copies every clear-bit element to a write cursor `w` and nulls the tail from `w` to the old `size`.

</details>

**Q2.** Add `trimToSize()`. What must it do to `modCount`, and why does that surprise people who assume it is a read-only optimisation?

<details><summary>Answer</summary>

```java
public void trimToSize() {
    modCount++;
    if (size < elementData.length) {
        elementData = (size == 0) ? EMPTY : Arrays.copyOf(elementData, size);
    }
}
```

It must bump `modCount` even though no element or `size` value changes, because it replaces the backing array — a live `Itr` checking `elementData.length` in `next()` would otherwise read an orphaned array. Structural-modification tracking is about array identity, not element values.

</details>

**Q3.** Sketch a spliterator with a working `trySplit`. What two fields does it need, and why must the fence be lazy rather than fixed at construction?

<details><summary>Answer</summary>

Two fields beyond `index`: `fence` (`-1` = "not yet fixed") and `expectedModCount` (meaningless until the fence is fixed). `trySplit` computes `mid = (index + fence) >>> 1`, returns `null` if `index >= mid`, else builds a sibling covering `[index, mid)` and mutates this one's `index` to `mid`. Lazy fencing matters because fixing it in `spliterator()` would snapshot `size` before the caller does anything with the stream — `list.add(x); list.stream()...` needs to see that mutation, the documented "late-binding" behaviour, not a stale bound taken too early.

</details>

**Q4.** `Itr.remove()` resyncs `expectedModCount` after calling `LedgerEntryList.this.remove(lastRet)`. What breaks if that resync line is left out, and why does `remove(int)` through the list itself deliberately *not* get the same treatment?

<details><summary>Answer</summary>

`LedgerEntryList.this.remove(lastRet)` bumps `modCount` exactly like any other structural mutation, because `fastRemove` cannot tell whether it was called from the public `remove(int)` or from inside `Itr.remove()`. Without `expectedModCount = modCount;` afterward, the iterator's own next `hasNext()`/`next()` call would see `modCount != expectedModCount` and throw `ConcurrentModificationException` on a removal the iterator itself just performed — the class would reject its own documented use case (`while (it.hasNext()) { ...; it.remove(); }`). `remove(int)` called directly on the list has no `expectedModCount` to resync, because there is no iterator involved — every *other* live iterator on that list is correctly still expected to throw, since a mutation happened that they did not perform and cannot account for.

</details>

**Q5.** Reproduce the two distinct out-of-bounds message shapes in `LedgerEntryList`. Which methods route through which, and why does that split exist rather than one shared message format?

<details><summary>Answer</summary>

```java
new LedgerEntryList<>(List.of("A")).get(3);
// -> IndexOutOfBoundsException: Index 3 out of bounds for length 1
new LedgerEntryList<>(List.of("A")).add(3, "x");
// -> IndexOutOfBoundsException: Index: 3, Size: 1
```

`get`, `set`, and `remove(int)` all route through `Objects.checkIndex(index, size)`, whose message is the JDK-9+ intrinsified `"Index %d out of bounds for length %d"`. `add(int, E)` routes through this class's own `rangeCheckForAdd`, which throws `"Index: " + index + ", Size: " + size` — an older, hand-written format, because the valid range for an insertion index is `[0, size]` inclusive (you can insert *at* `size`), not `[0, size)` like a read, so it cannot reuse `checkIndex`'s length-based check at all. The split is not stylistic: it is two different range predicates that happen to both throw the same exception type.

</details>

---

**Questions answered:** Q-44, Q-45
**Sets up:** Next: the interview surface — how this is actually asked, and the answers said out loud.
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 583
