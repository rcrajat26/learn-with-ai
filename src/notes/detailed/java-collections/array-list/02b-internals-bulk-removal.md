# 02 Java Collections — `ArrayList` — INTERNALS (§3.1 `ArrayList` source walk — bulk removal, the deathRow bitset and exception safety)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/02-internals-b-mutation.md](02-internals-b-mutation.md) · Next: [array-list/03-internals-c-views-and-iterators.md](03-internals-c-views-and-iterators.md)

Six ways to delete more than one element from an `ArrayList`. They are not variations on one
another — they run three genuinely different algorithms, and one is quadratic. The map first:

| Entry point | What actually executes | Passes over the range | Cost | `modCount` |
|---|---|---|---|---|
| `removeIf(Predicate)` | `ArrayList.removeIf(filter, 0, size)`, line 1750 | 2 (mark, compact) + tail null | O(n) predicate calls, ≤ n moves | **+1 total**, only if something matched |
| `removeAll(Collection)` | `batchRemove(c, false, 0, size)`, line 896 | 1 (two-cursor) + tail null | O(n × cost of `c.contains`) | `+= end - w`, i.e. one per element removed |
| `retainAll(Collection)` | `batchRemove(c, true, 0, size)`, line 896 | 1 (two-cursor) + tail null | O(n × cost of `c.contains`) | `+= end - w` |
| `removeRange(int,int)` | `shiftTailOverGap(es, lo, hi)`, line 827 | 1 `arraycopy` + tail null | O(size − hi) | +1 |
| `clear()` | its own loop, line 731 | 1 null-out | O(n), capacity kept | +1 |
| **`Collection.removeIf` default** | iterator loop calling `it.remove()` | 1, but each removal shifts | **O(n²)** on an array-backed list | +1 per element removed |

The last row is what `ArrayList` overrides an interface default to avoid. Everything below is that
table, proved from the JDK 21 source.

---

## `removeIf` — a `long[]` deathRow bitset and one compaction pass

### Mental model

Two passes beat one. Pass one only *reads* and marks a bit per victim; pass two only *writes*,
sliding survivors left. Separating them means the predicate never observes a half-compacted array,
and no element is ever moved twice. Think of a proofreader marking deletions in the margin of a
whole page before retyping it once, rather than retyping the page after every struck word.

### Why it exists

`removeIf` arrived in Java 8 as a `default` method on `Collection`. The default body is a plain
iterator loop:

> `java.base/java/util/Collection.java`, JDK 21, lines 578–589

```java
default boolean removeIf(Predicate<? super E> filter) {
    Objects.requireNonNull(filter);
    boolean removed = false;
    final Iterator<E> each = iterator();
    while (each.hasNext()) {
        if (filter.test(each.next())) {
            each.remove();
            removed = true;
        }
    }
    return removed;
}
```

On an `ArrayList` each `each.remove()` routes to `fastRemove`, an O(n) left shift, so the default is
**O(n²)** when many elements match — clearing a 1,000,000-entry list this way moves roughly
5 × 10¹¹ references. `ArrayList` overrides it to collapse that into a single sweep.

### When to reach for it, and when not

`removeIf` is the correct default for "delete by predicate" on any `ArrayList`. Reach for
`removeAll(set)` instead when the criterion is membership in an existing collection — same O(n)
shape, no lambda. Reach for `subList(a,b).clear()` (which routes to `removeRange`) when the
criterion is *positional*: one `arraycopy`, not n predicate invocations. Reach for
`Stream.filter().toList()` when you want a new list and the original is shared — `removeIf` mutates
in place and is unsafe on a list another thread is reading.

### How it works

The bitset is three static one-liners, not a `java.util.BitSet`:

> `java.base/java/util/ArrayList.java`, JDK 21, lines 1726–1736

```java
// A tiny bit set implementation
private static long[] nBits(int n) {
    return new long[((n - 1) >> 6) + 1];
}
private static void setBit(long[] bits, int i) {
    bits[i >> 6] |= 1L << i;
}
private static boolean isClear(long[] bits, int i) {
    return (bits[i >> 6] & (1L << i)) == 0;
}
```

`i >> 6` picks the 64-bit word; `1L << i` relies on the JLS rule that a `long` shift distance is
masked to its low six bits, so `1L << 70` is `1L << 6` and no explicit `i & 63` is needed.
`nBits(n)` is the ceiling division `((n - 1) >> 6) + 1` — 1 word for `n = 64`, 2 for `n = 65`. One
`long` covers 64 indices, so marking a million elements costs 15,625 words, 125 KB, against the
roughly 4 MB a parallel reference array would need.

> `java.base/java/util/ArrayList.java`, JDK 21, lines 1742–1782

```java
@Override
public boolean removeIf(Predicate<? super E> filter) {
    return removeIf(filter, 0, size);
}

/**
 * Removes all elements satisfying the given predicate, from index
 * i (inclusive) to index end (exclusive).
 */
boolean removeIf(Predicate<? super E> filter, int i, final int end) {
    Objects.requireNonNull(filter);
    int expectedModCount = modCount;
    final Object[] es = elementData;
    // Optimize for initial run of survivors
    for (; i < end && !filter.test(elementAt(es, i)); i++)
        ;
    // Tolerate predicates that reentrantly access the collection for
    // read (but writers still get CME), so traverse once to find
    // elements to delete, a second pass to physically expunge.
    if (i < end) {
        final int beg = i;
        final long[] deathRow = nBits(end - beg);
        deathRow[0] = 1L;   // set bit 0
        for (i = beg + 1; i < end; i++)
            if (filter.test(elementAt(es, i)))
                setBit(deathRow, i - beg);
        if (modCount != expectedModCount)
            throw new ConcurrentModificationException();
        modCount++;
        int w = beg;
        for (i = beg; i < end; i++)
            if (isClear(deathRow, i - beg))
                es[w++] = es[i];
        shiftTailOverGap(es, w, end);
        return true;
    } else {
        if (modCount != expectedModCount)
            throw new ConcurrentModificationException();
        return false;
    }
}
```

Four details worth naming.

- The **empty-statement loop** at the top skips the leading run of survivors. A predicate matching
  nothing walks it to `end`, falls into the `else`, checks `modCount`, and returns `false` having
  allocated nothing and written nothing — not even `modCount`.
- The bitset is allocated **only after the first match**, sized `end - beg`, not `size`: a predicate
  whose first match is at index 900,000 of a million allocates 1,563 words, not 15,625.
- `deathRow[0] = 1L` hard-codes the already-known first victim rather than re-invoking the
  predicate on it; predicates are user code and may be expensive.
- `modCount++` happens **exactly once**, between the passes: after the CME check, before any write.
  That ordering is what makes the "predicate may read the list" guarantee real.

![removeIf's three phases: pass one setting bits in a long[] deathRow, pass two compacting survivors left in a single sweep, then the tail nulled with modCount bumped once](../diagrams/D-68-removeif-deathrow.svg)

### Concrete example

```java
import java.util.ArrayList;
import java.util.ConcurrentModificationException;
import java.util.List;

public final class RemoveIfDemo {
    public static void main(String[] args) {
        List<Integer> xs = new ArrayList<>(List.of(1, 2, 3, 4, 5, 6, 7, 8));
        boolean changed = xs.removeIf(n -> n % 2 == 0);
        System.out.println(changed + " " + xs);      // true [1, 3, 5, 7]
        // No match: returns false, allocates no bitset, does not bump modCount.
        System.out.println(xs.removeIf(n -> n > 100));   // false
        // A predicate that only READS the list is tolerated by design.
        List<String> ys = new ArrayList<>(List.of("a", "bb", "ccc"));
        ys.removeIf(s -> s.length() > ys.get(0).length());
        System.out.println(ys);                      // [a]
        // A predicate that WRITES still gets a CME, from the check between passes.
        List<Integer> zs = new ArrayList<>(List.of(1, 2, 3));
        try {
            zs.removeIf(n -> { zs.add(n); return n == 2; });
        } catch (ConcurrentModificationException e) {
            System.out.println("CME as specified");
        }
    }
}
```

### Gotcha

**Pitfall:** a predicate with side effects can be invoked on an element that is then *not* removed —
if the CME check between the passes fires, pass two never runs, yet pass one already tested every
element to `end`. Keep predicates pure. The same asymmetry means the number of predicate
invocations is always exactly `end - beg`, never fewer, even when only the first element matches.

> **Definition.** `ArrayList.removeIf` marks victims in a lazily allocated `long[]` bitset during
> one read-only pass, then compacts survivors leftward in one write pass — O(n) total, with a
> single `modCount` bump taken between the passes.

---

## `batchRemove` — the shared engine, and what its `catch` and `finally` repair

### Mental model

`removeAll` and `retainAll` are the *same* algorithm with one boolean flipped. A read cursor `r`
and a write cursor `w` chase each other down the array; `w` never overtakes `r`, so the compaction
is in place, single pass, and allocation free. The hard part is not the happy path — it is leaving
a *valid list* behind when the caller's `c.contains()` throws halfway through.

### Why it exists

`AbstractCollection.removeAll` is an iterator loop, quadratic on an array-backed list for the same
reason the `Collection.removeIf` default is. `batchRemove` replaces it with one sweep, and takes
`from`/`end` parameters so that `ArrayList.SubList` can share the identical machinery over a window
of the root array instead of reimplementing it.

### When to reach for it, and when not

`removeAll` when you have a set of things to delete; `retainAll` for the intersection. Do not use
either when the argument is a `List` — `contains` on a `List` is O(m), making the whole call O(n·m).
Wrap it: `list.removeAll(new HashSet<>(victims))`. When the criterion is a predicate rather than
membership, `removeIf` is both clearer and free of the `contains` cost.

### How it works

> `java.base/java/util/ArrayList.java`, JDK 21, lines 872–924

```java
public boolean removeAll(Collection<?> c) {
    return batchRemove(c, false, 0, size);
}

public boolean retainAll(Collection<?> c) {
    return batchRemove(c, true, 0, size);
}

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

`complement` is the flip. For `removeAll` it is `false`, so `c.contains(e) == complement` means
"`c` does not contain `e`" — keep it. For `retainAll` it is `true`, so the same expression means
"`c` does contain `e`" — keep it. One body, two published methods.

The opening loop scans past the leading run of survivors so a call that deletes nothing near the
front performs zero writes; and if it reaches `end` without a single hit it returns `false` having
touched nothing at all — not `size`, not `modCount`, not one array slot. `int w = r++` then plants
the write cursor exactly on the first doomed slot.

**The two-part repair.** Both halves matter, and only one of them is obvious.

- The **`catch (Throwable ex)`** fires when `c.contains()` throws — a `ClassCastException` from a
  `TreeSet`'s comparator meeting a foreign type, an NPE from a collection that forbids nulls, a
  user `equals` blowing up. At that instant the array is in three zones: `[from, w)` are confirmed
  survivors already in place, `[w, r)` is scratch whose contents have been copied down or are
  doomed, and `[r, end)` has **never been examined**. The unexamined tail must survive — an
  iterator-based implementation would simply have stopped and left it alone — so the catch block
  moves `[r, end)` down to `w` with one `arraycopy` and advances `w` by `end - r`. Then it rethrows
  the original throwable, unwrapped.
- The **`finally`** runs on both the normal and the exceptional path and does the bookkeeping the
  `try` block deliberately omitted. `modCount += end - w` records one structural modification *per
  element actually removed*, which is exactly what the `AbstractCollection` iterator version would
  have produced — matching it keeps any surviving iterator's failure behaviour identical.
  `shiftTailOverGap(es, w, end)` then slides anything past `end` down to `w` (the `SubList` case,
  where `end < size`) and nulls every freed slot.

Because `shiftTailOverGap` is the only writer of `size` on this path, and it runs in the `finally`,
the list is structurally consistent no matter where the exception landed.

### Concrete example

```java
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

public final class BatchRemoveDemo {
    public static void main(String[] args) {
        List<String> xs = new ArrayList<>(List.of("a", "b", "c", "d", "e"));
        xs.removeAll(Set.of("b", "d"));
        System.out.println(xs);                    // [a, c, e]
        xs.retainAll(Set.of("a", "e", "zz"));
        System.out.println(xs);                    // [a, e]
        // Nothing matches: returns false, no write, no modCount bump.
        System.out.println(xs.removeAll(Set.of("q")));   // false
        // contains() throwing mid-run: the list stays valid and the tail survives.
        List<Object> ys = new ArrayList<>(List.of("k1", "k2", 42, "k3"));
        Set<Object> filter = new TreeSet<>(List.of("k2"));  // natural-order String comparator
        try {
            ys.removeAll(filter);                  // CCE when contains(42) is reached
        } catch (ClassCastException e) {
            System.out.println("threw, list = " + ys);   // threw, list = [k1, 42, k3]
        }
        System.out.println(ys.size());             // 3 — size and array agree
    }
}
```

### Gotcha

**Pitfall:** `removeAll(c)` is O(n × cost of `c.contains`), and nothing in the signature warns you.
Passing an `ArrayList` as `c` makes the call O(n·m); for n = m = 10,000 that is 10⁸ `equals` calls.
`new HashSet<>(c)` costs O(m) once and drops the whole call to O(n).

**Interview:** "What happens if the collection passed to `removeAll` throws from `contains`?" — the
list is left valid: the unexamined tail is preserved by the `catch`, `size` and `modCount` are
fixed by the `finally`, and the original exception propagates.

> **Definition.** `batchRemove` is the shared read-cursor/write-cursor in-place compaction behind
> `removeAll` and `retainAll`, with a `catch` that rescues the unexamined tail and a `finally` that
> alone commits `size`, `modCount` and the null-out.

---

## Supporting mechanics

**`shiftTailOverGap` — the shared tail fixer** (`ArrayList.java`, JDK 21, lines 826–831):

```java
/** Erases the gap from lo to hi, by sliding down following elements. */
private void shiftTailOverGap(Object[] es, int lo, int hi) {
    System.arraycopy(es, hi, es, lo, size - hi);
    for (int to = size, i = (size -= hi - lo); i < to; i++)
        es[i] = null;
}
```

One `arraycopy` closes the gap `[lo, hi)`, then `size -= hi - lo` shrinks the list *inside the loop
initialiser* and the loop nulls every slot from the new `size` to the old one. It is called by
`removeRange`, by `removeIf` and by `batchRemove`'s `finally`, which is why all three have identical
GC behaviour. **Gotcha:** when `hi == size` the `arraycopy` length is 0 — legal and effectively free,
which is why the callers do not guard it.

> **Definition.** `shiftTailOverGap` closes a half-open index gap with one block move, shrinks
> `size`, and nulls the freed slots.

**`removeRange(int,int)`** (`ArrayList.java`, JDK 21, lines 817–824) is `protected` — inherited from
`AbstractList`, not part of the `List` interface — so the public route to it is
`list.subList(from, to).clear()`. It validates only `fromIndex > toIndex` itself (throwing
`IndexOutOfBoundsException` via `outOfBoundsMsg`), bumps `modCount` once, and delegates to
`shiftTailOverGap`. **Gotcha:** deleting a contiguous run this way is O(size − to) regardless of the
run's length, so removing 500,000 middle elements from a 1,000,000-element list is one 500,000-element
block move — dramatically cheaper than 500,000 `remove(int)` calls.

> **Definition.** `removeRange` is the O(size − to) positional bulk delete, reachable publicly
> through `subList(from, to).clear()`.

**Version delta: Java 8's `removeIf` used `java.util.BitSet`.** The Java 8 body allocated
`new BitSet(size)`, counted matches into `removeCount`, then compacted with
`i = removeSet.nextClearBit(i)` inside the copy loop (JDK 8u202, `java/util/ArrayList.java`, lines
1401–1433). JDK 9 replaced it with the raw `long[]` plus `nBits`/`setBit`/`isClear`, dropping the
`BitSet` object header, its internal `long[]`, the growth logic, and a virtual call per survivor.
Java 8 also sized the bitset at `size` and allocated it unconditionally, where JDK 9+ sizes it at
`end - beg` and allocates only after the first match. Observable behaviour is unchanged; the
allocation profile is not.

**Version delta: Java 8's `batchRemove` had no `catch`.** It was
`private boolean batchRemove(Collection<?> c, boolean complement)` — no range parameters — and put
the tail rescue inside the `finally` behind an `if (r != size)` guard, with the null-clearing loop
written out inline behind a second `if (w != size)` guard (JDK 8u202,
`java/util/ArrayList.java`, lines 718–743). JDK 9 split the rescue into an explicit
`catch (Throwable ex)`, extracted the nulling into `shiftTailOverGap`, and added `from`/`end` so
`SubList` could share the method. The semantics are the same; the JDK 9 form simply separates
"exceptional repair" from "always-run bookkeeping" instead of branching on cursor positions.

**`SubList` reuses both engines rather than reimplementing them.** `ArrayList.SubList.removeAll`,
`retainAll` and `removeIf` (`ArrayList.java`, JDK 21, lines 1281–1305) each call
`checkForComodification()`, record `root.size`, invoke the root's ranged method over
`[offset, offset + size)`, and then `updateSizeAndModCount(root.size - oldSize)` to propagate the
shrink up the parent chain. **Gotcha:** this is why bulk removal through a sub-list correctly
invalidates iterators over the *backing* list — the root's `modCount` is what moves.

> **Definition.** The `(from, end)` parameters on `batchRemove` and `removeIf` exist so `SubList`
> can run the identical compaction over a window of the root array.

---

## Pitfalls

### Calling `removeAll` with a `List` argument

**Wrong**

```java
List<String> data = new ArrayList<>(/* 100_000 entries */);
List<String> victims = new ArrayList<>(/* 10_000 entries */);
data.removeAll(victims);        // 100_000 x 10_000 = 10^9 equals() calls
```

**Right**

```java
data.removeAll(new HashSet<>(victims));   // O(m) to build, then O(n) total
```

**Why people believe it:** the parameter type is `Collection<?>`, so every collection looks equally
acceptable. The cost is entirely in the argument's `contains`, which the signature does not reveal.

### Expecting `removeIf` to stop calling the predicate once it has a match

**Wrong**

```java
List<Integer> xs = new ArrayList<>(List.of(1, 2, 3, 4));
List<Integer> seen = new ArrayList<>();
xs.removeIf(n -> { seen.add(n); return n == 1; });
System.out.println(seen);   // [1, 2, 3, 4] — every element was tested
```

The predicate is a filter, not a search: pass one must test everything to build the deathRow.
Worse, the side-effecting predicate above mutates `seen`, not `xs`, and so escapes the CME check
while still being a bug.

**Right**

```java
List<Integer> xs = new ArrayList<>(List.of(1, 2, 3, 4));
int i = xs.indexOf(1);
if (i >= 0) xs.remove(i);        // one scan, stops at the first hit
```

**Why people believe it:** `removeIf` reads like `remove`, which is singular and short-circuits.

### Using the `Collection.removeIf` default by writing your own list

**Wrong**

```java
class MyList<E> extends AbstractList<E> {   // backed by an ArrayList field
    private final List<E> delegate = new ArrayList<>();
    public E get(int i) { return delegate.get(i); }
    public int size()   { return delegate.size(); }
    public E remove(int i) { return delegate.remove(i); }
    // removeIf not overridden -> Collection's iterator-loop default -> O(n^2)
}
```

**Right** — add one forwarding override to the same class:

```java
@Override public boolean removeIf(Predicate<? super E> filter) {
    return delegate.removeIf(filter);         // forwards to ArrayList's O(n) override
}
```

**Why people believe it:** `default` methods feel like free functionality. They are free
*correctness*, never free performance — `Collection.removeIf`'s default is written for the general
case, and `ArrayList` overrides it for exactly this reason.

---

## Cheat sheet

| Item | Source anchor (JDK 21) | Key fact |
|---|---|---|
| `removeIf(Predicate)` | line 1742 | delegates to `removeIf(filter, 0, size)` |
| `removeIf(Predicate,int,int)` | line 1750 | 2 passes; `modCount++` once, between them |
| `nBits(n)` | line 1728 | `new long[((n - 1) >> 6) + 1]` — ceiling divide by 64 |
| `setBit` / `isClear` | lines 1731, 1734 | `bits[i >> 6]`, `1L << i` (shift masked to `i & 63`) |
| deathRow allocation | line 1760 | lazy — only after the first match; sized `end - beg` |
| `deathRow[0] = 1L` | line 1761 | first victim hard-coded, predicate not re-run |
| `Collection.removeIf` default | `Collection.java` lines 578–589 | iterator + `it.remove()` — **O(n²)** on `ArrayList` |
| `removeAll` / `retainAll` | lines 872, 892 | both `batchRemove(c, false/true, 0, size)` |
| `batchRemove` | line 896 | one pass, cursors `r` (read) and `w` (write) |
| `batchRemove` early exit | lines 901–906 | all survivors ⇒ `return false`, zero writes |
| `batchRemove` catch | lines 913–917 | rescues `[r, end)` with one `arraycopy`, then rethrows |
| `batchRemove` finally | lines 918–921 | `modCount += end - w`; `shiftTailOverGap(es, w, end)` |
| `shiftTailOverGap` | line 827 | one `arraycopy`, `size -= hi - lo`, null the freed tail |
| `removeRange(int,int)` | line 817 | `protected`; public route is `subList(a,b).clear()` |
| `SubList` bulk ops | lines 1281–1305 | call the root's ranged forms over `[offset, offset+size)` |
| Java 8 deltas | JDK 8u202 lines 1401, 718 | `removeIf` used `BitSet`; `batchRemove` had no `catch` |

## Self-test

**Q1.** Why does `ArrayList` override `Collection.removeIf` at all?

<details><summary>Answer</summary>

The `default` in `Collection` (`Collection.java`, JDK 21, lines 578–589) is an iterator loop calling
`each.remove()`. On `ArrayList` each such removal is a `fastRemove` left shift, so the default is
O(n²) when many elements match. The override marks victims in a `long[]` bitset in one pass and
compacts once, giving O(n) with a single `modCount` bump.

</details>

**Q2.** Why a raw `long[]` rather than `java.util.BitSet`?

<details><summary>Answer</summary>

Java 8 did use `BitSet` plus `nextClearBit`. JDK 9 replaced it with a bare `long[]` and the three
static helpers `nBits`/`setBit`/`isClear` (lines 1728–1736), removing the `BitSet` object header,
its own internal array, its growth logic and a virtual call per survivor. The array is also
allocated lazily — only after the first matching element — and sized `end - beg` rather than `size`.

</details>

**Q3.** `removeIf`'s comment says predicates may read the collection. What in the code makes that
true, and why do writers still get a CME?

<details><summary>Answer</summary>

Pass one only calls `filter.test` and `setBit`; it does not move a single element, so any read the
predicate performs sees the list exactly as the caller left it. `modCount` is not incremented until
after pass one completes. A predicate that *writes* bumps `modCount` itself, so the check
`if (modCount != expectedModCount) throw new ConcurrentModificationException();` between the passes
catches it before any compaction happens.

</details>

**Q4.** Trace `batchRemove` for `removeAll` on `[a, b, c, d]` with `c = Set.of("b")`. Where are `r`
and `w` at each step?

<details><summary>Answer</summary>

`complement` is `false`. The opening loop tests `r = 0`: `contains("a")` is `false`, which
`!= complement` is false, so it continues; `r = 1`: `contains("b")` is `true`, which `!= false`, so
it breaks. `w = 1`, then `r` becomes 2. The try loop: `r = 2`, `contains("c") == false ==
complement`, so `es[1] = "c"`, `w = 2`; `r = 3`, `contains("d")` likewise, `es[2] = "d"`, `w = 3`.
Loop ends at `r = 4 = end`. The `finally` does `modCount += 4 - 3 = 1` and
`shiftTailOverGap(es, 3, 4)`, which copies 0 elements, sets `size = 3` and nulls slot 3. Result
`[a, c, d]`.

</details>

**Q5.** `batchRemove` has both a `catch` and a `finally`. What does each fix?

<details><summary>Answer</summary>

The `catch (Throwable ex)` handles `c.contains()` throwing mid-scan: elements `[r, end)` have never
been examined and must survive, so it block-moves them down to `w`, advances `w` by `end - r`, and
rethrows. The `finally` runs on every path and is the only place that commits state:
`modCount += end - w` and `shiftTailOverGap(es, w, end)`, which slides any tail past `end` down and
nulls the freed slots (writing `size` inside `shiftTailOverGap`). Together they guarantee a
structurally valid list even on the exceptional path.

</details>

**Q6.** Why is `modCount += end - w` rather than `modCount++`?

<details><summary>Answer</summary>

`end - w` is the number of elements actually removed. `AbstractCollection`'s iterator-based
`removeAll` would bump `modCount` once per `it.remove()`, so matching that count keeps the failure
behaviour of any concurrently held iterator identical between the two implementations. Note the
contrast with `removeIf`, which bumps exactly once — the two methods deliberately differ here.

</details>

**Q7.** What is the public way to invoke `removeRange`, and when is it the right tool?

<details><summary>Answer</summary>

`list.subList(from, to).clear()`. `removeRange` is `protected` on `AbstractList`, so it is not
callable through the `List` interface. It is the right tool whenever the deletion criterion is
positional and contiguous: it costs one `arraycopy` of the `size - to` suffix regardless of how many
elements are being deleted, where `removeIf` would cost n predicate calls and n loop iterations.

</details>

**Q8.** Removing 500,000 elements from the middle of a 1,000,000-element `ArrayList`: rank
`remove(int)` in a loop, `removeIf`, and `subList(a,b).clear()`.

<details><summary>Answer</summary>

`subList(a, b).clear()` wins: one `arraycopy` of the 500,000-element suffix plus 500,000 null
stores. `removeIf` is next: 1,000,000 predicate invocations plus a 500,000-element compaction —
still O(n), but with a per-element lambda call. The loop of `remove(int)` is last by a wide margin:
500,000 removals each shifting an average of ~500,000 elements, on the order of 2.5 × 10¹¹ moves.

</details>

---

**Leaves covered:** 3.1.22, 3.1.23 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-68
**Target version:** Java 21 LTS
**Lines:** 599
