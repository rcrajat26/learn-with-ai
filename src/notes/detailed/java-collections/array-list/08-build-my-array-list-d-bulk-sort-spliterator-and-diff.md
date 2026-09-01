# 02 Java Collections — `ArrayList` — INTERNALS (§4.1 `MyArrayList<E>` — bulk operations and sorting)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/07-build-my-array-list-c-sublist-and-equality.md](07-build-my-array-list-c-sublist-and-equality.md) · Next: [array-list/09-build-my-array-list-e-spliterator-diff-and-benchmark.md](09-build-my-array-list-e-spliterator-diff-and-benchmark.md)

Part four of five. [05](05-build-my-array-list.md) built the storage core, [06](06-build-my-array-list-b-iterators.md) the iterators, [07](07-build-my-array-list-c-sublist-and-equality.md) the view and the value semantics. This file adds the four bulk operations and `sort`; [09](09-build-my-array-list-e-spliterator-diff-and-benchmark.md) finishes the class with the `Spliterator`, the diff table against `java.util.ArrayList` and the JMH harness. The complete compiling class is the concatenation of the code blocks in 05 through 09, in order.

---

## The bulk entry points, by pass count and cost

| Entry point | Delegates to | Passes over the range | Per-element call | Cost |
|---|---|---|---|---|
| `addAll(Collection)` | `grow(s + numNew)` then one `arraycopy` | 0 (bulk copy) | none | O(n + m), one growth at most |
| `addAll(int, Collection)` | as above plus a right shift | 0 (two bulk copies) | none | O(n + m) |
| `removeAll(Collection)` | `batchRemove(c, false, 0, size)` | 1 | `c.contains` | O(n) x cost of `contains` |
| `retainAll(Collection)` | `batchRemove(c, true, 0, size)` | 1 | `c.contains` | O(n) x cost of `contains` |
| `removeIf(Predicate)` | `removeIf(filter, 0, size)` | 2 (predicate, then compaction) | `filter.test`, exactly once | O(n) plus one `long[]` of `n/64` |
| `removeRange` / `subList.clear()` | `shiftTailOverGap` | 0 (bulk copy) | none | O(n − hi) |
| `sort(Comparator)` | `Arrays.sort` in place | TimSort's own | `compare` | O(n log n), no copy of the list |

Everything in the first six rows ends at `shiftTailOverGap` from [05](05-build-my-array-list.md), which is the single place the trailing-null invariant is enforced for ranges. The pass count is the interesting column: `batchRemove` gets away with one, `removeIf` needs two, and the reason is the difference between calling into a collection and calling into arbitrary user code.

---

### `addAll`, `removeAll`, `retainAll` and the read-write cursor (4.1.12, part one)

**Mental model.** Naive bulk removal is quadratic: each `remove` shifts the whole tail, so deleting *k* elements from *n* costs O(n·k). The fix is a single **read-write cursor pass** — walk with a read pointer `r`, copy survivors down to a write pointer `w`, then null everything from `w` to the old end. One pass, O(n), one `arraycopy` at the tail.

**Why `addAll` is not just a loop of `add`.** A loop would consult the capacity check *n* times and could trigger several growths. `addAll` computes the final size once and calls `grow(s + numNew)`, so a 50-element insert into a fresh list allocates exactly once.

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

`batchRemove` unifies both operations behind one boolean. `complement == false` keeps elements *not* in `c`; `complement == true` keeps elements in `c`. The initial skip loop means a call that removes nothing performs zero writes and returns `false` without dirtying a cache line.

The `catch (Throwable)` block is the subtle one. If `c.contains` throws partway through — a `TreeSet` with an incompatible comparator will — the array is half-compacted, survivors below `w` and untested elements from `r` to `end`. Rather than leave a corrupt list, the handler slides the untested tail down and lets the `finally` run the normal fixup, so the exception propagates from a *consistent* list. `java.util.ArrayList` documents this as preserving behavioural compatibility with `AbstractCollection` (`java.base/java/util/ArrayList.java`, JDK 21, line 913).

`modCount += end - w` in the `finally` counts the number of elements actually removed rather than incrementing by one. It is the only place in the class where `modCount` moves by more than 1.

**Interview:** *Why is `list.removeAll(otherList)` sometimes catastrophically slow?* Because `batchRemove` calls `c.contains` once per element, and `List.contains` is O(m). Total O(n·m). Wrapping the argument in a `HashSet` first makes it O(n + m).

---

### `removeIf` and the bitset compaction (4.1.12, part two)

**Mental model.** Two passes and a death row. Pass one asks the predicate about every element of the untouched array and records the verdicts as bits. Pass two compacts using only the bits, calling nothing.

**Why not one pass.** `removeIf` calls arbitrary user code. A single-pass compaction mutates the array as it walks, so a predicate that *reads* the list — legal, since reads do not bump `modCount` — would observe a half-compacted array with duplicated elements below the write cursor. Two passes also guarantee each predicate is evaluated exactly once, which matters when the predicate is expensive or non-idempotent.

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

`nBits(n)` is `((n - 1) >> 6) + 1` — ceiling division by 64 with no division instruction. For n = 64 it gives 1; for n = 65, 2. The bitset covers only the range from the *first* condemned element onward, so a `removeIf` whose first million elements all survive allocates a bitset for the remainder, not for the million.

`setBit` and `isClear` use `bits[i >> 6] |= 1L << i` with **no mask on the shift**. That looks like a bug and is not: Java's `<<` on a `long` uses only the low 6 bits of the shift distance, so `1L << 70` is `1L << 6` — exactly the within-word position that `i >> 6` word-indexing needs. Two operations instead of three, on a loop that runs once per element.

`deathRow[0] = 1L` pre-condemns the element that broke the skip loop, so the second loop starts at `beg + 1` and never re-evaluates the predicate on it.

The comodification check between the two passes catches a predicate that *wrote* to the list; reads are tolerated. `modCount++` comes after that check, so the compaction pass is the only structural change recorded.

**Verified.** From the demo run (full output in [09](09-build-my-array-list-e-spliterator-diff-and-benchmark.md)):

```
removeIf(even)   -> true [1, 3, 5, 7, 9]
removeAll([b,d]) -> [a, c]
addAll(1,[x,y])  -> [a, x, y, c]
retainAll([a,y]) -> [a, y]
```

**Insight:** the two-pass structure costs one `long[]` of `size/64` words — 16 bytes for a thousand-element list — and buys both single-evaluation of the predicate and a coherent view for reentrant reads. That is why `removeIf` is not simply a loop over `batchRemove`.

> Bulk removal is a read-write cursor compaction; `removeIf` splits it into a predicate pass recorded in a bitset and a copy pass that calls nothing, so user code never sees a partially compacted array.

---

### `sort(Comparator)` in place (4.1.13)

**Mental model.** The list does not sort itself. It hands its own backing array to `Arrays.sort` over the live range and then audits what happened.

**Why in place matters.** A sort that copied out, sorted, and copied back would double the transient footprint of a large list and touch every cache line three times instead of once. Because `elementData` is a plain `Object[]` and `size` bounds the live region exactly, the list can pass the real array with a range and let TimSort work directly on it.

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

`Arrays.sort(array, from, to, comparator)` sorts the live backing array over the first `size` slots. The cast `(E[]) elementData` is unchecked and safe under erasure — the array's runtime type is `Object[]`, and the comparator only ever sees elements this list put there.

The `expectedModCount` check runs **after** the sort, because the interference it looks for is a comparator that mutates the list mid-sort. TimSort will already have thrown `IllegalArgumentException: Comparison method violates its general contract!` in most such cases, but a comparator that merely *adds* without breaking transitivity would slip through — and `size` would then be stale, leaving a list whose tail is unsorted and whose invariants are broken. The post-check turns that into `ConcurrentModificationException`.

`modCount++` at the end is contentious and the JDK does it too. Sorting is not structural by the strict definition — the size does not change. But every live iterator's position now refers to a different element, exactly the silent wrongness fail-fast exists to prevent, so `sort` is classified structural. `replaceAll` bumps it for the same reason (line 1795, where the JDK's own comment flags it under bug 8203662).

**Verified:** `[pear, fig, apple, kiwi]` by natural order gives `[apple, fig, kiwi, pear]`; re-sorted by `comparingInt(String::length).reversed()` gives `[apple, kiwi, pear, fig]` — `kiwi` before `pear` because TimSort is stable and they were in that order after the first sort.

```
sort(naturalOrder) -> [apple, fig, kiwi, pear]
sort(byLengthDesc) -> [apple, kiwi, pear, fig]
```

**Interview:** *Why is stability worth caring about?* Because it lets you sort by several keys with several passes: sort by the least significant key first, then by the most significant, and the earlier ordering survives inside each group. An unstable sort makes that technique silently wrong.

> `sort` is `Arrays.sort` over the live array with a post-hoc comodification check, and it bumps `modCount` because reordering invalidates cursors even though it does not change size.

---

## Pitfalls

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

### Writing a comparator as a subtraction

**Wrong**

```java
list.sort((a, b) -> a.score() - b.score());
// with scores 2_000_000_000 and -2_000_000_000 the subtraction overflows to a
// positive value, so the comparator claims the smaller element is the larger one
```

**Right**

```java
list.sort(Comparator.comparingInt(Item::score));
// or, equivalently and explicitly:
list.sort((a, b) -> Integer.compare(a.score(), b.score()));
```

`a - b` on `int` wraps around whenever the difference exceeds `Integer.MAX_VALUE`, so the comparator becomes non-transitive on wide-ranging values. TimSort detects the inconsistency partway through a large sort and throws `IllegalArgumentException: Comparison method violates its general contract!` — from a call site that has nothing obviously wrong with it. On a small list it does not detect anything and you get a silently mis-ordered result. See [D-14](../diagrams/D-14-subtract-comparator-overflow.svg).

**Why people believe it:** the subtraction returns a negative, zero or positive `int`, which is exactly the contract's shape, and it works perfectly for every small non-negative value anyone tests with.

### Mutating the list from inside a `removeIf` predicate

**Wrong**

```java
list.removeIf(s -> {
    if (s.isBlank()) {
        rejected.add(s);
        list.add("audit:" + s);   // structural write to the list being filtered
        return true;
    }
    return false;
});
// ConcurrentModificationException, thrown between the two passes
```

**Right**

```java
List<String> doomed = list.stream().filter(String::isBlank).toList();
rejected.addAll(doomed);
list.removeIf(String::isBlank);        // predicate is now pure
list.addAll(doomed.stream().map(s -> "audit:" + s).toList());
```

The predicate pass snapshots `modCount` before it starts and rechecks it before compaction begins. *Reads* from inside a predicate are deliberately tolerated — that is one of the reasons the implementation uses two passes — but any structural write is caught. The exception is a feature: a single-pass implementation would have silently compacted an array the predicate had already lengthened.

**Why people believe it:** collecting a side list while filtering feels natural, and adding to a *different* collection is genuinely fine. The failure only appears when the write lands on the list being filtered.

---

## Cheat sheet

| Item | Value / rule |
|---|---|
| `batchRemove` | one boolean unifies `removeAll` (false) and `retainAll` (true) |
| `batchRemove` `modCount` | `+= end - w`, the only multi-increment in the class |
| `batchRemove` early exit | nothing to remove → zero writes, returns `false` |
| `batchRemove` on throw | slides the untested tail down, then rethrows from a consistent list |
| `removeAll`/`retainAll` cost | O(n) x cost of `c.contains` — pass a `HashSet` |
| `addAll` growth | one `grow(s + numNew)`, never a growth per element |
| `addAll(int, c)` copies | two `arraycopy` calls: right shift, then bulk insert |
| Empty argument collection | `addAll` returns `false` and makes no copy |
| `removeIf` passes | 1: predicate → bitset; 2: bitset → compaction |
| `removeIf` predicate calls | exactly once per element, always |
| `removeIf` reentrancy | reads tolerated; structural writes → `ConcurrentModificationException` |
| `nBits(n)` | `((n - 1) >> 6) + 1` — ceiling divide by 64 |
| `setBit` | `bits[i >> 6] \|= 1L << i` — no mask; `<<` uses the low 6 bits |
| Bitset extent | sized from the first condemned index, not from 0 |
| `sort` | `Arrays.sort` in place, post-hoc CME check, then `modCount++` |
| `sort` algorithm | TimSort — stable, O(n log n), adaptive to existing runs |
| Subtraction comparators | overflow; use `Integer.compare` or `Comparator.comparingInt` |
| Shared tail cleanup | every bulk removal ends at `shiftTailOverGap` |

---

## Self-test

**Q1.** `setBit` is `bits[i >> 6] |= 1L << i` with no `& 63` on the shift distance. Why is that correct?

<details><summary>Answer</summary>

Java specifies that for a `long` left shift, only the low six bits of the right-hand operand are used — the shift distance is implicitly `i & 63`. So `1L << 70` is exactly `1L << 6`. Since `i >> 6` selects the 64-bit word and `i & 63` is the position within it, the implicit masking gives precisely the intended bit, and writing `1L << (i & 63)` would be redundant. This saves one AND instruction on a loop that runs once per element. The identical trick appears in `java.util.BitSet` and in the JDK's own `ArrayList.setBit` (line 1731). Note the asymmetry with `int` shifts, which mask to the low *five* bits — a hand-written `int[]` bitset needs `>> 5`, not `>> 6`.

</details>

**Q2.** Why does `removeIf` use two passes and a bitset when `batchRemove` gets away with a single read-write cursor pass?

<details><summary>Answer</summary>

Because `removeIf` calls arbitrary user code. A single-pass compaction mutates the array as it walks, so a predicate that reads the list — legally, since reads do not bump `modCount` — would observe a half-compacted array with duplicated elements below the write cursor. The two-pass form evaluates every predicate against the untouched array, records verdicts in the bitset, checks `modCount` to catch a predicate that *wrote*, and only then compacts using nothing but the bitset. It also guarantees each predicate is evaluated exactly once, which matters for expensive or non-idempotent predicates. `batchRemove`'s `c.contains` is a call into a collection rather than a closure over the list, so the JDK accepts the single-pass risk there — and still wraps it in a `catch (Throwable)` that repairs the array if `contains` throws.

</details>

**Q3.** `batchRemove` catches `Throwable`, does an `arraycopy`, and rethrows. What state would the list be in without that catch?

<details><summary>Answer</summary>

Corrupt. At the moment `c.contains` throws, survivors occupy indices `from` to `w - 1`, indices `w` to `r - 1` hold stale duplicates already copied down, and indices `r` to `end - 1` hold elements that were never tested. The `finally` clause would then run `shiftTailOverGap(es, w, end)`, which discards everything from `w` onward — silently deleting every untested element, including ones the caller wanted to keep. The catch block slides the untested tail from `r` down to `w` and advances `w` past it first, so those elements survive and only the genuinely removed ones are dropped. The exception still propagates; the difference is that it propagates from a list satisfying its invariants. `java.util.ArrayList` calls this preserving behavioural compatibility with `AbstractCollection` (line 913).

</details>

**Q4.** `sort` checks `modCount` after `Arrays.sort` rather than before. What could a before-check possibly miss?

<details><summary>Answer</summary>

A comparator that mutates the list during the sort. Before the sort there is nothing to detect — `modCount` trivially equals itself. The interference happens *inside* `Arrays.sort`, when TimSort calls back into `compare`. If that comparator adds to the list, `size` changes and `elementData` may be replaced, so the sort finishes having partially ordered an array that no longer describes the list. TimSort catches the subset of these that break its transitivity assumptions and throws `IllegalArgumentException: Comparison method violates its general contract!`, but a mutating-yet-consistent comparator slips past. The post-check converts that into `ConcurrentModificationException`. The trailing `modCount++` is separate: it marks the reorder as structural so that any iterator created before the sort fails, since its cursor now names a different element.

</details>

**Q5.** `batchRemove` increments `modCount` by `end - w` rather than by 1. Why does the amount matter, given that fail-fast only ever compares for equality?

<details><summary>Answer</summary>

For fail-fast alone it does not — any change would trip an iterator. The amount matters because `modCount` is a *counter of structural modifications*, and code outside the iterator reads it as such. `SubList.updateSizeAndModCount` copies the parent's value into its mirror, and the spliterator captures it as a version token; both compare rather than count, so they are indifferent. The real reason is fidelity to the field's documented meaning in `AbstractList`, plus the practical benefit that a debugger or a `jol`-style inspection of two lists can tell "one bulk call that removed 40 elements" from "one call that removed 1". It also makes the increment naturally zero when nothing was removed, which is exactly what the early-exit path wants — though that path returns before the `finally` can run at all.

</details>

**Q6.** `removeIf` sets `deathRow[0] = 1L` immediately after allocating the bitset. What is that line doing and what would break without it?

<details><summary>Answer</summary>

It condemns the element at `beg` — the one whose `filter.test` returned `true` and thereby broke the initial skip loop. The bitset is indexed relative to `beg`, so bit 0 *is* that element. Without the line, the second loop would start at `beg + 1` and never record a verdict for `beg`, so the compaction pass would see bit 0 clear and copy that element down as a survivor: the one element you definitely wanted removed would be the one that stayed. The alternative fix — starting the predicate loop at `beg` instead of `beg + 1` — is correct but calls `filter.test` twice on that element, which violates the exactly-once guarantee that matters for expensive or side-effecting predicates. One assignment buys the guarantee.

</details>

**Q7.** `addAll(int, Collection)` performs two `System.arraycopy` calls. Describe each, and say why the order cannot be reversed.

<details><summary>Answer</summary>

The first, `arraycopy(es, index, es, index + numNew, numMoved)`, shifts the existing tail right by `numNew` slots to open the gap. The second, `arraycopy(a, 0, es, index, numNew)`, fills that gap from the argument's array. Reversing them would write the new elements over the tail before the tail had been moved out of the way, destroying `numNew` existing elements. The right shift is also the reason the capacity check must run first: `grow(s + numNew)` may replace `elementData` entirely, so `es` is re-read from the return value before either copy. Note the guard `if (numMoved > 0)` — appending at `index == size` makes the first copy zero-length, and skipping it avoids a pointless call.

</details>

**Q8.** Both `batchRemove` and `removeIf` begin by skipping an initial run of survivors. What does that buy, and in what case does it buy nothing?

<details><summary>Answer</summary>

It buys the common case where nothing near the front is removed. Until the first condemned element is found, the read and write cursors coincide, so copying each survivor to its own index would be a stream of pointless self-assignments that dirty every cache line in the array. Skipping means a call that removes nothing performs zero writes — `batchRemove` returns `false` without touching the array at all, and `removeIf` allocates no bitset. It also lets `removeIf` size its bitset for `end - beg` rather than `end`, so filtering the tail of a million-element list allocates a handful of words. It buys nothing when the very first element is condemned: `beg` equals the start, the bitset spans the whole range, and the skip loop exits after one test. The cost of the attempt is that single test, which the algorithm needs anyway.

</details>

---

**Leaves covered:** 4.1.12–4.1.13 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 422
