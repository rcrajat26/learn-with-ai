# 02 Java Collections — `ArrayList` — INTERNALS (§3.1 `ArrayList` source walk — single-element mutation, scanning and capacity)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/01-internals-a-growth.md](01-internals-a-growth.md) · Next: [array-list/02b-internals-bulk-removal.md](02b-internals-bulk-removal.md)

Every mutating method on `ArrayList` is one of five shapes. Fix the map before the streets.

| Shape | Methods | Element moves | `modCount` bumps |
|---|---|---|---|
| Append | `add(E)`, `addLast(E)` | 0 (amortised over `grow`) | 1 per call |
| Positional insert | `add(int,E)`, `addFirst(E)` | `size - index` right | 1 per call |
| Positional delete | `remove(int)`, `remove(Object)`, `removeFirst()`, `removeLast()` | `size - index - 1` left | 1 per call |
| Capacity management | `ensureCapacity`, `trimToSize`, `clear` | one copy, one copy, n nulls | 1 per call |
| Bulk delete | `removeIf`, `removeAll`, `retainAll`, `removeRange` | one compaction sweep | 1 per call, not per element |

This file walks the first four rows. The last row is a genuinely different algorithm and is walked
in [02b-internals-bulk-removal.md](02b-internals-bulk-removal.md).

---

## `add(E)` and `add(int, E)` — insertion is one `arraycopy`

### Mental model

An `ArrayList` insert is not "make room by nudging elements one at a time". It is a **block move**:
the CPU is handed a source address, a destination address and a length, and it slides the whole
tail in one instruction stream. Picture a bookshelf where you shove every book right of a gap
with one sweep of your forearm, then drop the new book in the hole. The cost is the *width of the
sweep*, not the number of books.

### Why it exists

`add(int,E)` exists so `List` can promise positional semantics on top of a flat array. Before
`System.arraycopy` was intrinsified, library authors wrote the shift loop by hand and paid a bounds
check plus a store barrier per element. The JDK now hands the whole shift to the VM.

### When to reach for it

Use `add(E)` freely — it is amortised O(1). Use `add(0, e)` **only** on lists you know are small.
The sibling that wins for head insertion is `ArrayDeque` (O(1) `addFirst`); `LinkedList` also gives
O(1) at the head but loses so badly on iteration and memory that it is almost never the answer.

### How it works

`add(E)` is deliberately split into two methods:

> `java.base/java/util/ArrayList.java`, JDK 21, lines 477–497

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

**Insight:** that comment (line 477) is the best evidence in the class that the JDK is written *for
the JIT*. `-XX:MaxInlineSize` defaults to 35 bytecodes; C1 (the client compiler used at tiers 1–3)
will not inline a method above it. Keeping `add(E)` tiny means a hot loop calling `list.add(x)` gets
the whole call inlined at C1 before C2 ever sees the loop, with the grow path parked in the helper,
out of the inlining budget.

`add(int,E)` does the bounds check first, then grows, then shifts once:

> `java.base/java/util/ArrayList.java`, JDK 21, lines 509–520

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

Note the *same array* is both source and destination. `System.arraycopy` is specified to behave as
if the source range were copied to a temporary first, so overlapping forward moves are safe — it is
a `memmove`, not a `memcpy`.

![add(1, X) on [A,B,C,D] with size 4: one System.arraycopy(elementData, 1, elementData, 2, 3) block move, giving [A,X,B,C,D] with size 5 and modCount incremented](../diagrams/D-66-arraylist-add-index-shift.svg)

### Concrete example

```java
import java.util.ArrayList;
import java.util.List;

public final class AddShift {
    public static void main(String[] args) {
        List<String> xs = new ArrayList<>(List.of("A", "B", "C", "D"));
        xs.add(1, "X");
        System.out.println(xs);        // [A, X, B, C, D]

        // addFirst is literally add(0, e) since Java 21 (SequencedCollection).
        xs.addFirst("HEAD");
        System.out.println(xs);        // [HEAD, A, X, B, C, D]

        // The pathological loop: n head-inserts move n(n-1)/2 elements.
        List<Integer> head = new ArrayList<>();
        for (int i = 0; i < 5; i++) head.add(0, i);
        System.out.println(head);      // [4, 3, 2, 1, 0]
    }
}
```

`addFirst(E)` and `addLast(E)` are new in Java 21 (JEP 431, `SequencedCollection`) and are pure
delegations — `addFirst` to `add(0, element)`, `addLast` to `add(element)`
(`java.base/java/util/ArrayList.java`, JDK 21, lines 528–537). They add convenience, not speed:
`addFirst` is still O(n).

### Gotcha

**Pitfall:** `add(index, e)` accepts `index == size` (that is an append), while `get(index)` does
not. Two different checks: `rangeCheckForAdd` uses `index > size || index < 0`
(`ArrayList.java`, JDK 21, lines 836–839), whereas `Objects.checkIndex` rejects `index == size`.

> **Definition.** `ArrayList.add(int,E)` performs a single `System.arraycopy` right-shift of the
> `size - index` element suffix, then stores into the vacated slot — O(n − index), O(1) at the tail.

---

## `remove(int)`, `fastRemove` and the trailing null

### Mental model

Deletion is the insert film run backwards, plus one extra frame that people forget: **the vacated
tail slot must be nulled**. The array is longer than the list; a stale reference sitting past `size`
is invisible to every API yet perfectly visible to the garbage collector.

### Why it exists

`fastRemove` was carved out so that `remove(Object)`, which has already scanned and therefore
already knows the index is valid, does not pay a second bounds check and does not build a return
value it will throw away.

### When to reach for it

`remove(int)` is the right tool at or near the tail. Away from the tail, prefer a bulk form — one
`removeIf` call beats a loop of `remove(int)` by a factor of n — or a different structure entirely:
`ArrayDeque` for head removal, `LinkedHashSet` when you are really doing membership deletion.

### How it works

> `java.base/java/util/ArrayList.java`, JDK 21, lines 550–557 and 715–724

```java
public E remove(int index) {
    Objects.checkIndex(index, size);
    final Object[] es = elementData;

    @SuppressWarnings("unchecked") E oldValue = (E) es[index];
    fastRemove(es, index);

    return oldValue;
}

/**
 * Private remove method that skips bounds checking and does not
 * return the value removed.
 */
private void fastRemove(Object[] es, int i) {
    modCount++;
    final int newSize;
    if ((newSize = size - 1) > i)
        System.arraycopy(es, i + 1, es, i, newSize - i);
    es[size = newSize] = null;
}
```

Read the guard carefully — it is the proof of leaf 3.1.14. If `i == size - 1` then
`newSize == i`, the condition `newSize > i` is false, and **no `arraycopy` runs at all**. The
method degenerates to `modCount++` plus one null store: O(1). If `i == 0`, `newSize - i` is
`size - 1` elements moved: O(n). There is no branch tuning, no special case — the cost falls
straight out of `size - index - 1`.

`es[size = newSize] = null` is a compound assignment doing three jobs at once: assign `newSize`
to the field `size`, use that value as the index, store `null`. Without it the slot at the old
`size - 1` would keep pinning the removed object (and, after a shift, the *duplicate* of the last
element that the shift left behind) for as long as the list lives.

![remove(1) left-shifts with one arraycopy then executes elementData[--size] = null so the vacated slot stops pinning the object; the second panel shows remove(size-1) doing zero copying](../diagrams/D-67-arraylist-remove-shift-null.svg)

`remove(Object)` (lines 695–712) is the scanning sibling: the same hoisted null-versus-`equals`
split as `indexOf`, a labelled break on the first hit, then the identical `fastRemove` — a scan
*plus* a shift.

**Version note.** In Java 8 the signature was `private void fastRemove(int index)`, reading
`elementData` from the field and ending with `elementData[--size] = null; // clear to let GC do its
work` (JDK 8u202, `java/util/ArrayList.java`, lines 544–551). JDK 9 made it take the array as a
parameter so callers that already loaded the field do not reload it — the same "help the JIT" motive
as the `add` split. The `shiftTailOverGap` helper used by the bulk paths is also post-Java-8: in 8,
`removeRange` and `batchRemove` each inlined their own shift-and-null logic.

### Concrete example

```java
import java.util.ArrayList;
import java.util.List;

public final class RemoveCost {
    public static void main(String[] args) {
        List<String> xs = new ArrayList<>(List.of("A", "B", "C", "D"));

        String gone = xs.remove(1);          // shifts C,D left by one, then nulls slot 3
        System.out.println(gone + " " + xs); // B [A, C, D]

        String tail = xs.remove(xs.size() - 1);  // zero arraycopy
        System.out.println(tail + " " + xs);     // D [A, C]

        // remove(Object) scans, then delegates to the same fastRemove.
        System.out.println(xs.remove("A") + " " + xs);   // true [C]

        // Java 21 SequencedCollection forms; removeLast is the O(1) one.
        List<Integer> ys = new ArrayList<>(List.of(1, 2, 3));
        System.out.println(ys.removeLast() + " " + ys.removeFirst());  // 3 1
    }
}
```

### Gotcha

**Pitfall:** `remove(int)` and `remove(Object)` are different methods, and on a `List<Integer>`
the literal `list.remove(1)` picks the `int` overload — position 1, not the value 1. Force the
object form with `list.remove(Integer.valueOf(1))`.

> **Definition.** `fastRemove` performs at most one left-shifting `arraycopy` of the
> `size - i - 1` element suffix and always nulls the newly-vacated last slot, so removal is
> O(n − index) with O(1) at the tail and no retained reference.

---

## `ensureCapacity` — the highest-value single-line `ArrayList` optimisation

### Mental model

Growth is not one copy, it is a *cascade* of copies, each larger than the last. Presizing does not
save you one allocation — it collapses the whole geometric staircase into a single step.

### Why it exists

The lazy default-capacity design (an empty `ArrayList` allocates no array at all until the first
`add`) is right for the millions of tiny lists in a typical heap and wrong for the one list you
are about to fill with a million rows. `ensureCapacity` is the escape hatch for that second case
when the size only becomes known after construction; `new ArrayList<>(n)` is the same escape hatch
when it is known up front.

### When to reach for it

Any time you know, or can cheaply bound, the final size: JDBC result sets with a count, file line
counts, `List` built from a sized stream. Do **not** reach for it speculatively — over-presizing
wastes exactly as much memory as the growth slack you were trying to avoid.

### How it works

> `java.base/java/util/ArrayList.java`, JDK 21, lines 215–221

```java
public void ensureCapacity(int minCapacity) {
    if (minCapacity > elementData.length
        && !(elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA
             && minCapacity <= DEFAULT_CAPACITY)) {
        modCount++;
        grow(minCapacity);
    }
}
```

The second clause is the interesting one: on a still-lazy default-constructed list, asking for
capacity ≤ `DEFAULT_CAPACITY` (10, line 118) is a no-op, because the first `add` would allocate 10
anyway and materialising it early only loses the "empty list costs nothing" property.

**Version note.** Java 8's `ensureCapacity` computed a `minExpand` local and delegated to
`ensureExplicitCapacity` (JDK 8u202, `java/util/ArrayList.java`, lines 210–221) — same semantics,
one fewer method in JDK 9+, growth arithmetic moved out to `ArraysSupport.newLength`. No diagram
belongs here: the growth staircase is drawn in [01-internals-a-growth.md](01-internals-a-growth.md),
and the point of this section is the arithmetic below.

### The arithmetic it skips

Growth uses `ArraysSupport.newLength(oldCapacity, minCapacity - oldCapacity, oldCapacity >> 1)`
(line 234), i.e. preferred new length = `old + (old >> 1)` — the 1.5x sequence, starting at 10.
Appending 1,000,000 elements to `new ArrayList<>()` walks:

`10, 15, 22, 33, 49, 73, 109, 163, 244, 366, 549, 823, 1234, 1851, 2776, 4164, 6246, 9369, 14053,
21079, 31618, 47427, 71140, 106710, 160065, 240097, 360145, 540217, 810325, 1215487`

- **`grow` calls: 30.** The first (0 → 10) allocates without copying; the other 29 each `Arrays.copyOf` the whole current array.
- **Elements copied: 2,430,972.** That is the sum of the first 29 capacities: 10 through 810325, inclusive — roughly 2.43 copies per element stored, which is the expected `1/(r−1) = 1/0.5 = 2` plus start-up overhead.
- **Slots allocated in total: 3,646,459** across 30 arrays = 13.9 MiB of `Object[]` payload churned at 4 bytes per reference with compressed oops, against a live need of 3.8 MiB.
- **Final capacity: 1,215,487** — 215,487 slots (0.82 MiB) of permanent waste unless you `trimToSize()`.

With `new ArrayList<>(1_000_000)` (or `ensureCapacity(1_000_000)` on an empty one): **0 `grow`
calls, 0 elements copied, 1 allocation of exactly 1,000,000 slots, 0 waste.** The 29 intermediate
arrays also never become garbage, so the young-generation pressure disappears with them.

### Concrete example

```java
import java.util.ArrayList;

public final class Presize {
    public static void main(String[] args) {
        int n = 1_000_000;
        ArrayList<Integer> lazy = new ArrayList<>();
        for (int i = 0; i < n; i++) lazy.add(i);   // 30 grows, 2,430,972 copies
        ArrayList<Integer> late = new ArrayList<>();
        late.ensureCapacity(n);                    // 0 grows, 0 copies
        for (int i = 0; i < n; i++) late.add(i);
        System.out.println(lazy.equals(late));     // true
    }
}
```

### Gotcha

**Pitfall:** `ensureCapacity` bumps `modCount` even though no element changed. An iterator created
before the call fails with `ConcurrentModificationException` on its next step. Presize *before*
you start iterating, never mid-traversal.

**Interview:** "How do you speed up building a large `ArrayList`?" — presize it; you delete ~2.4n
element copies and 29 array allocations, and the result is a single contiguous 3.8 MiB block
instead of a 13.9 MiB allocation trail.

> **Definition.** `ensureCapacity(n)` performs the one `grow` that the append sequence would
> otherwise perform incrementally, eliminating the entire geometric copy cascade.

---

## Supporting mechanics

**`indexOf` / `contains` and the null-vs-equals split loop.** `contains(o)` is
`indexOf(o) >= 0`; `indexOf` delegates to `indexOfRange(o, 0, size)`
(`ArrayList.java`, JDK 21, lines 285–300), which branches on `o == null` **once, outside the loop**,
then runs either `es[i] == null` or `o.equals(es[i])` for the whole range. `Objects.equals(o, es[i])`
inside the loop would re-test nullness n times and make the loop body bigger than the inliner likes.
`lastIndexOfRange` is the mirror image, counting down from `end - 1`. **Gotcha:** it is
`o.equals(es[i])`, not `es[i].equals(o)` — the *argument's* `equals` decides, so an asymmetric
`equals` gives different answers than you expect.

> **Definition.** `indexOf` is a hoisted-null-check linear scan, O(n), using the argument's `equals`.

**`elementData(int)` and the unchecked cast.** Two helpers exist
(`ArrayList.java`, JDK 21, lines 409–417):

```java
@SuppressWarnings("unchecked")
E elementData(int index) { return (E) elementData[index]; }

@SuppressWarnings("unchecked")
static <E> E elementAt(Object[] es, int index) { return (E) es[index]; }
```

The backing store is `Object[]`, never `E[]`, precisely so it can be reallocated by
`Arrays.copyOf` without array-store checks against a reified component type. The `(E)` cast erases
to nothing at runtime; the real check happens at the call site when the caller assigns to `E`.
**Gotcha:** heap pollution via a raw `List` reference is therefore caught not here but at the
caller's implicit checkcast — which is why such a `ClassCastException` points at your code, not at
`ArrayList`.

> **Definition.** `elementData(int)` is the erasure-safe accessor that hides the `Object[]`-to-`E`
> unchecked cast in one place.

**`Objects.checkIndex` / `rangeCheckForAdd` and the redundant bounds check.** Read paths use
`Objects.checkIndex(index, size)` (`get`, `set`, `remove(int)`); the add paths use the wider
`rangeCheckForAdd` (line 836) because `index == size` is legal for insertion.
`Objects.checkIndex` is annotated `@IntrinsicCandidate` in `java.util.Objects` and C2 recognises it,
so after the explicit check the *array* access `elementData[index]` has a provably in-range index
and HotSpot removes the JVM-mandated bounds check on the array load. You pay one comparison, not
two. `outOfBoundsMsg` (line 843) is deliberately "outlined" into its own method — its comment says
this "performs best with both server and client VMs", because inlining the string concatenation
would inflate the hot method's bytecode size.

> **Definition.** `checkIndex` is an intrinsified range check whose success lets the JIT elide the
> subsequent implicit array bounds check.

**`System.arraycopy` as an intrinsic.** It is declared `native` and `@IntrinsicCandidate`; C2
replaces the call with an inlined `memmove`-equivalent stub, unrolled and vectorised, copying by
machine word rather than by element and emitting one card-mark range for the GC write barrier
instead of one per store. That is why a 1,000,000-element shift is fast in absolute terms while
still being O(n) — the constant factor is tiny, the complexity is not. **Gotcha:** benchmarks that
shift small arrays measure the intrinsic's fixed setup cost, not its throughput, and mislead people
into thinking `add(0, e)` is cheap.

> **Definition.** `System.arraycopy` is a JIT intrinsic lowered to a vectorised native block move
> with overlap-safe (`memmove`) semantics.

**`trimToSize()`** (`ArrayList.java`, JDK 21, lines 199–206) bumps `modCount`, and if
`size < elementData.length` replaces the array with `Arrays.copyOf(elementData, size)`, or with the
shared `EMPTY_ELEMENTDATA` when `size == 0`. It costs one full copy plus one allocation, so it pays
only for a **long-lived, heavily over-allocated** list — the 1,000,000-element list above sits at
capacity 1,215,487 and trimming reclaims 0.82 MiB permanently. On a short-lived list it is waste:
you allocate to avoid garbage that was about to be collected anyway.

> **Definition.** `trimToSize` reallocates the backing array to exactly `size`, trading one copy
> for the reclaimed slack.

**`clear()`** (`ArrayList.java`, JDK 21, lines 731–736):

```java
public void clear() {
    modCount++;
    final Object[] es = elementData;
    for (int to = size, i = size = 0; i < to; i++)
        es[i] = null;
}
```

**Pitfall (version trap):** `clear()` nulls every slot but **keeps the array**. A list that once
held ten million elements still holds a ten-million-slot `Object[]` afterwards — tens of megabytes
of compressed-oop references, retained. `list.clear()` on a pooled or long-lived object is a classic
slow leak; call `trimToSize()` after, or allocate a fresh `ArrayList`. Identical in Java 8
(lines 557–565) — only the loop's shape changed.

> **Definition.** `clear()` is O(n) reference-nulling with capacity preserved.

Bulk removal — `removeIf`, `removeAll`, `retainAll`, `removeRange` — does not use any of the
machinery above; it is a two-cursor compaction with its own exception-safety contract, walked in
[02b-internals-bulk-removal.md](02b-internals-bulk-removal.md).

---

## Pitfalls

### Removing while iterating with an index loop

**Wrong**

```java
List<String> xs = new ArrayList<>(List.of("a", "x", "x", "b"));
for (int i = 0; i < xs.size(); i++) {
    if (xs.get(i).equals("x")) xs.remove(i);
}
System.out.println(xs);   // [a, x, b]  — the second "x" was skipped
```

Each `remove(i)` shifts the tail left, so the element that slides into index `i` is never tested.

**Right**

```java
List<String> xs = new ArrayList<>(List.of("a", "x", "x", "b"));
xs.removeIf("x"::equals);
System.out.println(xs);   // [a, b]
```

`removeIf` marks every match before moving anything, so nothing is skipped — and it is O(n) rather
than the index loop's O(n²).

**Why people believe it:** the loop *looks* like it visits every element, and on inputs whose
matches are all at the tail it produces the right answer by luck.

### Believing `remove(0)` is cheap because "it's just one arraycopy"

**Wrong**

```java
List<Integer> q = new ArrayList<>();
for (int i = 0; i < 1_000_000; i++) q.add(i);
while (!q.isEmpty()) q.remove(0);      // ~5x10^11 element moves
```

**Right**

```java
Deque<Integer> q = new ArrayDeque<>(1_000_000);
for (int i = 0; i < 1_000_000; i++) q.addLast(i);
while (!q.isEmpty()) q.pollFirst();    // O(1) each
```

**Why people believe it:** one `arraycopy` call sounds like constant work. It is one *call* whose
length argument is `size - 1`; the loop above sums to n(n−1)/2 element moves.

### Assuming `clear()` releases memory

**Wrong**

```java
ArrayList<byte[]> cache = new ArrayList<>();
for (int i = 0; i < 100_000; i++) cache.add(new byte[1]);
cache.clear();          // the ~131k-slot Object[] is still reachable from `cache`
```

**Right**

```java
cache.clear();
cache.trimToSize();     // backing array swapped for EMPTY_ELEMENTDATA when size == 0
```

**Why people believe it:** `size()` returns 0 and every element is unreachable, so the list
*behaves* empty. Capacity is invisible through the `List` API.

---

## Cheat sheet

| Operation | Source anchor (JDK 21) | Element moves | `modCount` | Notes |
|---|---|---|---|---|
| `add(E)` | line 494 | 0 amortised | +1 | split at line 481 to stay under `MaxInlineSize` 35 |
| `add(int,E)` | line 509 | `size - index` | +1 | `rangeCheckForAdd` allows `index == size` |
| `addFirst` / `addLast` | lines 528, 536 | n / 0 | +1 | Java 21, `SequencedCollection` |
| `remove(int)` | line 550 → `fastRemove` 719 | `size - index - 1` | +1 | `remove(size-1)` copies nothing |
| `remove(Object)` | line 695 → `fastRemove` 719 | scan n + shift | +1 | uses `o.equals(es[i])` |
| `removeFirst` / `removeLast` | lines 566, 584 | n / 0 | +1 | Java 21, `SequencedCollection` |
| `indexOf` / `contains` | lines 285, 274 | scan n | 0 | null check hoisted out of loop |
| `elementData(int)` | line 409 | — | 0 | unchecked `(E)` cast, erased at runtime |
| `Objects.checkIndex` | `get`/`set`/`remove` | — | 0 | intrinsic; lets JIT drop the array bounds check |
| `ensureCapacity(n)` | line 215 | one copy | +1 | no-op if `n <= 10` on a lazy list |
| `trimToSize()` | line 199 | one copy | +1 | `EMPTY_ELEMENTDATA` when `size == 0` |
| `clear()` | line 731 | n nulls | +1 | **capacity kept** |
| Growth constants | `DEFAULT_CAPACITY = 10` line 118; `old + (old >> 1)` line 234 | — | — | 1.5x sequence |
| 1M appends unpresized | — | 2,430,972 copies, 30 grows, final cap 1,215,487 | — | vs 0 copies, 0 grows presized |

## Self-test

**Q1.** Why is `add(E)` split into a public method and a private three-argument helper?

<details><summary>Answer</summary>

To keep the public `add(E)` bytecode under 35 bytes, the `-XX:MaxInlineSize` default. C1 refuses to
inline methods larger than that, and `add` is overwhelmingly called from hot loops. The rare `grow`
path is pushed into the helper so it does not count against the public method's inlining budget.
The comment stating this is at `java.base/java/util/ArrayList.java`, JDK 21, lines 477–480.

</details>

**Q2.** Prove from the source that `remove(size - 1)` performs no array copy.

<details><summary>Answer</summary>

`fastRemove` (line 719) guards the copy with `if ((newSize = size - 1) > i)`. For `i == size - 1`,
`newSize == i`, so `newSize > i` is false and `System.arraycopy` is skipped entirely. Only
`modCount++` and `es[size = newSize] = null` run — O(1). For `i == 0` the copy length is
`newSize - i == size - 1`, giving O(n).

</details>

**Q3.** What exactly does `es[size = newSize] = null` accomplish, and what breaks without it?

<details><summary>Answer</summary>

It writes `newSize` into the `size` field, uses that value as the array index, and stores `null`
there. Without it the slot beyond the new `size` keeps a strong reference — either to the removed
object (tail removal) or to a duplicate of the last element left behind by the left shift. The list
would behave correctly through every API while leaking one object per removal.

</details>

**Q4.** How many `grow` calls and element copies does appending 1,000,000 items to
`new ArrayList<>()` cost, and how does presizing change it?

<details><summary>Answer</summary>

30 `grow` calls (capacities 10, 15, 22, 33, up through 810325 and 1215487) of which 29 copy; the
copies total 2,430,972 element moves (the sum of the first 29 capacities), and 3,646,459 slots are
allocated across the 30 arrays. `new ArrayList<>(1_000_000)` costs 0 grows, 0 copies, one
allocation of exactly 1,000,000 slots, and leaves no 215,487-slot tail of waste.

</details>

**Q5.** `Objects.checkIndex(index, size)` already compares; the array load compares again. Why is
that not two costs?

<details><summary>Answer</summary>

`Objects.checkIndex` is an `@IntrinsicCandidate` that C2 recognises. Once it has passed, the
compiler knows `0 <= index < size <= elementData.length`, so the implicit bounds check on
`elementData[index]` is provably redundant and is eliminated. One comparison executes.

</details>

---

**Leaves covered:** 3.1.11–3.1.21 (11 leaves)
**Leaves deferred:** none
**Diagrams included:** D-66, D-67
**Target version:** Java 21 LTS
**Lines:** 597
