# `ArrayList` — 18 Interview B: questions 20 to 38

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: files 01 through 16 in full, and questions 1 to 19 (file 17).
Previous: [17 Interview A — questions 1 to 19](17-interview-a-questions.md) · Next: [19 Interview C — puzzles and checklist](19-interview-c-puzzles-and-checklist.md)

Nineteen more, numbered on from file 17: iteration and views, spliterator and
serialization, cost and memory, choosing, failure modes, version history,
ordering, and interoperation — plus the discipline for a question whose
premise is simply wrong. Nothing here is new; every answer points back at the
file that taught it first.

### Q20. Walk me through what `iterator()` actually returns — what state does it carry?

**Say this.** It returns an `Itr`, an inner class holding exactly three ints: `cursor`, the index of the next element to hand back; `lastRet`, the index it handed back last, or minus one if nothing has been returned yet; and `expectedModCount`, a snapshot of the list's `modCount` taken at construction. `next()` checks that snapshot against the live `modCount` before it does anything else, then reads `elementData[cursor]` and advances. `hasNext()` never touches `modCount` at all — it is just `cursor != size`.

**The mechanism.** `Itr` is a private inner class in `ArrayList` itself, so it reaches `ArrayList.this.elementData` directly with no synthetic accessor.

```java
int cursor;
int lastRet = -1;
int expectedModCount = modCount;
public boolean hasNext() { return cursor != size; }
public E next() {
    checkForComodification();
    int i = cursor;
    if (i >= size) throw new NoSuchElementException();
    cursor = i + 1;
    return (E) ArrayList.this.elementData[lastRet = i];
}
```

`checkForComodification()` runs at the top of `next()`, before the bounds check and before the read — the ordering matters, because a stale `modCount` is reported as a `ConcurrentModificationException`, not a `NoSuchElementException`, even on a list that also happens to be exhausted.

**Follow-up they will ask.** "Why doesn't `hasNext()` check `modCount`?" Because it doesn't need to for its own contract — it only reports whether there is another index to visit; the check that protects against structural change lives in `next()`, which is the call that actually reads and returns an element (file 08).

### Q21. If I remove an element while iterating with a for-each loop, does it always throw `ConcurrentModificationException`?

**Say this.** No, and that gap is the whole reason the Javadoc calls fail-fast best-effort rather than guaranteed. Removing the second-to-last element of a list inside its own for-each loop does not throw. On a four-element list, removing index 2 sets `size` to 3, and the iterator's `cursor` is already 3 from the `next()` call that returned that element — `hasNext()` evaluates `3 != 3` as false, the loop exits normally, and `checkForComodification()` is never reached again. Removing any earlier index does throw, because `cursor` and the new `size` still disagree on the next `hasNext()` call.

**The mechanism.** The AA-700 review-queue demonstration: `batchA` removes index 1 of 4 and throws; `batchB` removes index 2, the second-to-last, and finishes silently as `[RC-1001, RC-1002, RC-1004]` — one element quietly missing evaluation, not a crash.

```java
for (ReviewCase rc : batchB) if (rc.assignedOperatorId() != null) batchB.remove(rc);
// no exception; batchB == [RC-1001, RC-1002, RC-1004]
```

**Follow-up they will ask.** "What's the safe way to remove while iterating, and what does it cost?" `Iterator.remove()`, which resyncs `expectedModCount` after its own change — but it still calls `ArrayList.this.remove(lastRet)` underneath, the same `arraycopy` shift as any positional removal, so it is O(n) per call, O(n·k) for k removals; `removeIf(Predicate)` is the one-pass O(n) alternative when you are removing more than a couple of elements.

### Q22. Why does calling `remove()` twice in a row on a `ListIterator` throw `IllegalStateException`?

**Say this.** `lastRet` starts at minus one and both `Iterator.remove()` and `ListIterator.add()` reset it to minus one after they run, because nothing has been returned since. `remove()`'s first line is `if (lastRet < 0) throw new IllegalStateException()`, so the second consecutive call always trips it — you have to call `next()` or `previous()` again to give it something to act on. The same rule is why `set()` right after `add()` throws too.

**The mechanism.**

```java
public void remove() {
    if (lastRet < 0) throw new IllegalStateException();
    checkForComodification();
    try {
        ArrayList.this.remove(lastRet);
        cursor = lastRet; lastRet = -1; expectedModCount = modCount;
    } catch (IndexOutOfBoundsException ex) {
        throw new ConcurrentModificationException();
    }
}
```

The `catch` block is doing real work: if some other unsynchronized mutation already shrank the list past `lastRet` between `next()` and `remove()`, the underlying `ArrayList.this.remove(lastRet)` throws `IndexOutOfBoundsException`, and `Itr` translates it into the more informative `ConcurrentModificationException` rather than letting a confusing bounds exception surface from inside an iterator call.

**Follow-up they will ask.** "Does `set(e)` have the same resync requirement as `remove()`?" No — `set` overwrites a slot without touching `size`, and `ArrayList.set` never bumps `modCount`, so there is nothing to resync; `set` still checks `lastRet >= 0` and still checks comodification, it just never needs to update `expectedModCount` afterward.

### Q23. What happens if I hold onto a `subList()` view and then mutate the original list directly, not through the view?

**Say this.** The view's next access throws `ConcurrentModificationException`, and the Javadoc's own word for this state is "undefined" — stronger than "throws," because an alternate implementation is free to do something else entirely, including silently returning a stale answer. `SubList` is four ints and two references — `root`, an optional `parent`, `offset`, `size`, and an inherited `modCount` — with no element ever copied; every read is `root.elementData(offset + index)`. A structural change made through the root updates `root.modCount` but not the view's own cached copy, so `checkForComodification()` mismatches on the view's next call.

**The mechanism.**

```java
List<String> pageOne = mergedWithdrawalIds.subList(0, 3);
mergedWithdrawalIds.add("WD-9007");   // mutation through the root
pageOne.get(0);                       // ConcurrentModificationException
```

A change made *through the view instead* is the case the type is actually designed for: it calls `updateSizeAndModCount`, which walks the `parent` chain so every nested `subList().subList()` above it stays consistent, and the root's own `modCount` moves too — so the root and every live view of it agree afterward. It is only when the root is touched directly, bypassing every view watching it, that the views are left holding a stale `modCount` snapshot with no way to find out until their next access.

**Follow-up they will ask.** "Does wrapping it in `Collections.unmodifiableList` fix that?" No — it fixes the wrong problem. The wrapper still delegates reads to the same write-through view, so it still throws the moment the root changes; only detaching with `List.copyOf(view)` or `new ArrayList<>(view)` removes the coupling to the root entirely.

### Q24. What does `list.reversed()` return, and is it a copy?

**Say this.** It's a live, write-through view, not a copy — `ArrayList` is the one `SequencedCollection` member it does not override, so it inherits `List`'s default, whose measured runtime class is `java.util.ReverseOrderListView$Rand`. Index 0 of the reversed view is index `size - 1` of the original, and nothing is ever copied — only the direction of the index arithmetic flips. Structural changes through it write straight through to the backing array.

**The mechanism.** `ArrayList` overrides `getFirst`/`getLast`/`addFirst`/`addLast`/`removeFirst`/`removeLast` directly for performance, but leaves `reversed()` to the interface default rather than hand-writing its own reversed storage.

```java
List<String> mostRecentFirst = queuedCaseIds.reversed();  // [C, B, A]
mostRecentFirst.add("Z");
// queuedCaseIds is now [Z, A, B, C]
```

**Follow-up they will ask.** "Why does `add` on the reversed view land at the front of the original, not the back?" Appending at the reversed view's logical end means inserting immediately before the original's logical start — the view's index 0 is the original's last index, so its "append" direction points at the original's index 0.

### Q25. What does `Spliterator.trySplit()` actually move between the two halves?

**Say this.** Two ints, nothing else. `trySplit()` computes the midpoint between the current position and the fence, mutates the receiver's own `index` field to that midpoint, and returns a brand-new spliterator covering the lower half — the receiver keeps the upper half. No element is copied and no array is touched; the whole operation is arithmetic on two integer fields. That is the concrete reason `ArrayList` parallelizes cheaply.

**The mechanism.**

```java
public ArrayListSpliterator trySplit() {
    int hi = getFence(), lo = index, mid = (lo + hi) >>> 1;
    return (lo >= mid) ? null :
        new ArrayListSpliterator(lo, index = mid, expectedModCount);
}
```

**Follow-up they will ask.** "Does the fence get computed eagerly, at construction?" No — `fence` is lazily initialised on first use, at `getFence()`, precisely so it captures `size` as late as possible rather than the moment `spliterator()` was called; `expectedModCount` is set in that same lazy call, which is what lets `list.stream().forEach(a)` in the common single-threaded case run with no `modCount` check anywhere except inside `forEach` itself.

### Q26. What does `ArrayList.spliterator().characteristics()` return, and why does it matter for parallel streams?

**Say this.** Sixteen thousand four hundred sixty-four, measured on JDK 21.0.7 — that's `ORDERED` bitwise-or `SIZED` bitwise-or `SUBSIZED`. `SIZED` tells the fork-join framework the exact element count up front without visiting a single element, which is why `list.stream().count()` can be free when nothing size-altering intervenes. `SUBSIZED` promises that every child produced by `trySplit()` is itself `SIZED`, so the framework can plan the whole split tree in advance rather than discovering sizes as it goes.

**The mechanism.**

```java
public int characteristics() {
    return Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED;
}
```

**Follow-up they will ask.** "Why does `LinkedList` parallelize badly by comparison?" Its spliterator reports neither `SIZED` nor `SUBSIZED` — it has no array to count against in O(1), so the framework cannot pre-size splits and falls back to a much more conservative, less predictable splitting strategy, on top of the pointer-chasing cost per element that already hurts sequential traversal.

### Q27. Why is `ArrayList.elementData` marked `transient`, and what does that mean for a deserialized list's capacity?

**Say this.** It's `transient` so the default serialization machinery never writes the array directly — `ArrayList` hand-writes `writeObject`/`readObject` instead, which write only `size` followed by exactly `size` elements, never the trailing empty slots. A list at capacity one million holding three elements serializes three objects, not a million nulls. On the way back in, `readObject` allocates `new Object[size]` — exactly `size`, no slack — so a deserialized list's capacity always comes back equal to its element count.

**The mechanism.**

```java
s.writeInt(size);                       // written as "capacity", for clone() parity
for (int i = 0; i < size; i++) s.writeObject(elementData[i]);
// readObject: s.readInt(); // ignored — then new Object[size]
```

**Follow-up they will ask.** "What happens if I pre-sized a list to absorb a burst and then serialize it?" The pre-sizing is silently discarded — round-tripping `new ArrayList<>(10_000)` through serialization returns something with capacity exactly equal to whatever it held, not 10,000, so the next burst of adds resizes again from scratch. `writeObject` is also fail-fast: it snapshots `modCount` before writing and throws `ConcurrentModificationException` if a concurrent mutation changed it mid-write, same discipline as every other structural-change guard in the class.

### Q28. Give me the exact byte cost of a one-element `ArrayList` built with `new ArrayList<>()` versus `new ArrayList<>(1)`.

**Say this.** Eighty bytes for the default constructor plus one add, forty-eight for the presized-to-one constructor plus one add, measured on JDK 21.0.7 with compressed oops. The default path allocates a ten-slot array on the first add — a twelve-byte array header, a four-byte length field, and ten four-byte references, which is fifty-six bytes, on top of the twenty-four-byte list object itself. The presized path allocates a one-slot array, twelve plus four plus four padded to eight-byte alignment, twenty-four bytes, on top of the same twenty-four-byte list object.

**The mechanism.** `new ArrayList<>()`, empty, is twenty-four bytes on its own: a twelve-byte object header plus `modCount` (4) plus `size` (4) plus the `elementData` reference (4) — the backing array itself costs nothing extra because it points at a shared static zero-length array.

**Follow-up they will ask.** "Why does knowing your size up front matter here?" Because the ten-slot default allocation isn't a guess your code controls — it fires unconditionally on first add for a default-constructed list, wasting nine of ten slots if you only ever hold one element, while `new ArrayList<>(1)` wastes none. `LinkedList` plus one element measures at 56 bytes, between the two `ArrayList` numbers — 32 for the list object's own fields (`modCount`, `size`, `first`, `last`) plus one 24-byte `Node`, which the next question breaks down further.

### Q29. Compare the per-element footprint of `ArrayList` and `LinkedList` at steady state.

**Say this.** An `ArrayList` slot costs four bytes — one compressed object reference — plus up to thirty-three percent slack from the one-point-five-times growth factor. A `LinkedList` element costs a full twenty-four-byte `Node` object on top of the element itself: a twelve-byte header, a four-byte `item` reference, and four-byte `next` and `prev` references. That's roughly six times the per-element overhead, with no slack at all on the array side to offset it, because `LinkedList` has no array.

**The mechanism.** Measured on JDK 21.0.7: `new ArrayList<>()` plus one element is 80 bytes; `LinkedList` plus one element is 56 bytes — 32 for the list object itself (`modCount`, `size`, `first`, `last`) plus a 24-byte `Node`.

**Follow-up they will ask.** "Does that gap widen or shrink as the list grows?" It stays roughly proportional — every additional element on `LinkedList` costs another full `Node`, while `ArrayList`'s marginal cost per element trends toward the bare four bytes once amortised slack is spread across enough elements.

### Q30. When `ArrayList` doubles its backing array, how many total copies happen inserting a million elements?

**Say this.** It's never doubled, in any released JDK, Java 8 included — the growth arithmetic has always been `oldCapacity + (oldCapacity >> 1)`, a nominal one-point-five times, rounded down at odd capacities. `Vector` is the type that genuinely doubles. At one-point-five, the amortised bound is `f / (f - 1)` copies per element, which works out to three copies per element, so roughly three million total for a million inserts — doubling would actually mean fewer copies overall, about two million, because you resize less often; the tradeoff for doubling is more wasted slack sitting idle between resizes, not fewer copies.

**The mechanism.** `growth = oldCapacity >> 1` inside `grow(int)`; `Math.max(minGrowth, prefGrowth)` is what rescues capacity 0 and 1, where the shift alone would compute zero and never grow.

**Follow-up they will ask.** "So what does 'amortised O(1)' actually promise, and what does it not promise?" It promises the total cost over n calls divides out to O(1) per call on average — it says nothing about any single call. The one `add` that triggers a resize is genuinely O(n): it copies every existing element via `Arrays.copyOf`, live alongside the old array until the copy finishes. A latency-sensitive path — the 3,400-per-second settlement burst is the concrete example — can have one particular append cost far more than its neighbours even though the amortised bound holds overall; that same reasoning is why unbounded accumulation of a large external input into a default-constructed `ArrayList` degrades before it OOMs, rather than failing cleanly.

### Q31. What does presizing an `ArrayList` constructor actually save, in measured numbers?

**Say this.** Growing an empty default-constructed list to 100,000 elements takes 24 separate `grow` calls, lands at a final capacity of 106,710 — 6,710 wasted slots — and copies 213,413 elements in total across all those resizes, which is 2.13 copies per element. Timed, that's 584 microseconds for 100,000 unguided adds against 358 microseconds when the constructor is told the size up front — a 39 percent saving from one constructor argument, because the presized path never resizes at all.

**The mechanism.** The default growth sequence measured to eight resizes: 10, 15, 22, 33, 49, 73, 109, 163 — each number is the previous one plus its own `>> 1`, rounded down. Continued to 244 across the full 24-call sequence to 100,000 elements, ending at capacity 106,710.

```java
List<PaymentItemId> itemIds = new ArrayList<>(1_800);   // Appendix A.5's known run size
```

**Follow-up they will ask.** "Does `addAll` behave the same way?" No — `addAll` computes `grow(s + numNew)` directly, so `minGrowth` swamps the preferred one-point-five-times growth and capacity lands on exactly `size + numNew` with zero headroom; that's deliberate for a load-once-then-read bulk add, but it means the very next single `add` after an `addAll` resizes again immediately.

### Q32. When does `LinkedList` actually beat `ArrayList`, given `ArrayList` wins the obvious benchmarks?

**Say this.** `ArrayList` wins for-each by a factor of 3.2 — 103 microseconds against 329 for 200,000 elements, identical O(n) on both sides, purely a cache-locality effect. `ArrayList` wins indexed access even more decisively — walking the first 20,000 of 200,000 `LinkedList` elements by `get(i)` takes 352 milliseconds, against 101 microseconds to scan the entire 200,000-element `ArrayList` the same way, roughly 3,500 times worse for less than a tenth of the work, because `LinkedList.get(i)` is itself O(n). The one honest condition where `LinkedList` wins: you're holding a `ListIterator` already positioned mid-list, doing repeated inserts or removes at that exact cursor with no positional indexing anywhere in the loop and no hot traversal elsewhere — and even then, most code that thinks it's in this position is actually computing an index and calling `add(index, e)`, which is O(n) on `LinkedList` too.

**The mechanism.** `ArrayList` packs 16 references per 64-byte cache line at a fixed stride the prefetcher can follow; `LinkedList`'s 24-byte nodes are scattered in allocation order, not traversal order, so each `next` hop risks a cache miss the prefetcher cannot predict.

```java
List<PaymentIntent> intents = new LinkedList<>(paymentIntents); // 200_000
for (int i = 0; i < 20_000; i++) touch(intents.get(i));         // O(n) per call — the trap
```

`List`'s own Javadoc recommends checking `RandomAccess` before writing an index loop precisely because of this trap; `Collections.binarySearch`, `.reverse`, and `.shuffle` all branch on it internally rather than assuming every `List` supports cheap indexing.

**Follow-up they will ask.** "What if the need is really just fast insertion and removal at both ends?" Reach for `ArrayDeque` before `LinkedList` even in that narrow case — see the next question.

### Q33. `ArrayDeque` versus `LinkedList` for head-insertion — which one, and why?

**Say this.** `ArrayDeque`, essentially always. `ArrayList.addFirst(e)` is literally `add(0, e)` — a full O(n) `arraycopy` shift, no fast path exists despite the modern-looking name added in Java 21. `LinkedList.addFirst` is a genuine O(1) — allocate one node, rewire two pointers — but `ArrayDeque` matches that same O(1)-at-both-ends behaviour with a circular array, no per-element node at all, and better cache locality than `LinkedList` on every other operation. The only case `ArrayDeque` cannot serve is one where you also need `get(int)`, because it isn't a `List`.

**The mechanism.** 100,000 `add(0, e)` calls measured at 314 milliseconds on `ArrayList`, under 1 millisecond on `LinkedList`; `ArrayDeque` matches that `LinkedList` number without the 24-byte node tax.

```java
Deque<BankDepositRecord> ingestionQueue = new ArrayDeque<>();
void onRecordRead(BankDepositRecord r) { ingestionQueue.addLast(r); }
BankDepositRecord nextForMatching() { return ingestionQueue.pollFirst(); }
```

Appendix A.5's bank-deposit feed — 40,000 records a day, 500,000 at month-end, consumed strictly FIFO and never indexed — is exactly this shape: `ArrayList.remove(0)` per record is O(n²) to drain the whole file, while `ArrayDeque.pollFirst()` stays amortised O(1) regardless of volume.

**Follow-up they will ask.** "Does `ArrayDeque` have any surprising restriction?" It rejects `null` outright with `NullPointerException`, because `null` is its internal sentinel meaning "empty" in `peek`/`poll` — a genuinely absent element needs `Optional` or a distinct marker state, never a stored `null`.

### Q34. Two threads call `add()` on the same `ArrayList` with no synchronization. What actually happens?

**Say this.** Not a clean, reliable exception — measured across five consecutive runs of four threads each appending 25,000 elements, roughly 70 percent of the appends were silently lost every single time, which is the normal outcome under this much contention, not a rare edge case. Nulls showed up inside the live `[0, size)` range in every run, ranging from about 300 to nearly 3,000 depending on the run. `ArrayIndexOutOfBoundsException` from inside `add` appeared in only two of the five runs — the loudest symptom is also the least reliable one, which means the silent corruption in the other three runs is the genuinely dangerous case, because nothing signalled a problem occurred.

**The mechanism.** `add(E)` is `modCount++`, read `elementData`/`size`, maybe `grow()`, store, then `size = s + 1` — four separate unsynchronized field operations with no `volatile` anywhere, so one thread's writes are not guaranteed visible to another's reads at all.

```java
List<String> shared = new ArrayList<>();
// four threads, 25_000 adds each, released together via a CountDownLatch
// run 1: expected 100000, actual 30313 (lost 69687), nulls inside [0,size) = 832
```

Confining the list to one thread and publishing it via `List.copyOf(list)` once is the cheapest fix; `Collections.synchronizedList` makes each individual call atomic but its iterator is still unsynchronized, and `CopyOnWriteArrayList` copies the entire backing array on every write, which is catastrophic at 3,400 writes a second.

**Follow-up they will ask.** "Is `ConcurrentModificationException` a thread-safety mechanism I can rely on here?" No — it's a best-effort single-thread detector that can already miss even without concurrency (Q21); under genuine multi-threaded misuse a race may throw it, may not, or may produce any of the corruption symptoms above with no exception at all. Never catch it as a substitute for actual synchronization.

### Q35. A coordinator's `ArrayList` field shows `size() == 0` in a heap dump, but the backing array is huge. What leaked?

**Say this.** Capacity, not an unreachable object. `clear()` nulls every element slot and sets `size` to zero, but it never touches `elementData` at all — the array stays retained at whatever the largest run it ever absorbed was. A `PaymentRun` coordinator that grows a working-set list to its biggest-ever batch, then just `clear()`s it between runs and keeps the field, keeps that peak-sized array alive for the life of the field, even though every `size()` call afterward reports zero.

**The mechanism.**

```java
public void clear() {
    modCount++;
    for (int to = size, i = size = 0; i < to; i++) es[i] = null;
    // elementData itself is never reassigned
}
```

**Follow-up they will ask.** "How do you actually fix it?" `trimToSize()` right after `clear()` reallocates down to `EMPTY_ELEMENTDATA` at zero cost, but pays for a fresh `Arrays.copyOf` on the next `addAll`; replacing the field outright is cheaper only if the old array is about to be garbage anyway, and worse if the coordinator is mid-reuse at a reasonable size. A 500,000-reference array retained at 4 bytes a slot under compressed oops is roughly 2 MB held for every ordinary run afterward, for a field whose logical content is empty — invisible to `size()`, visible only in a heap dump or in `trimToSize()`'s before-and-after.

### Q36. What's `ArrayList.MAX_ARRAY_SIZE`, and what's the actual cap on how big a list can grow?

**Say this.** There is no such field on `ArrayList` from JDK 13 onward — it moved into a shared helper, `jdk.internal.util.ArraysSupport`, renamed `SOFT_MAX_ARRAY_LENGTH`, same numeric value, `Integer.MAX_VALUE` minus eight. And even when it lived on `ArrayList`, up to JDK 12, it was never a hard cap — it's a ceiling on speculative growth only; `hugeLength` deliberately returns a value above it when the caller's actual minimum requirement demands more, and throws `OutOfMemoryError` only on genuine `int` overflow. The real, unmovable cap is `Integer.MAX_VALUE`, because `size` is declared as a plain `int`.

**The mechanism.**

```java
public static final int SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8;

int prefLength = oldLength + Math.max(minGrowth, prefGrowth);
if (0 < prefLength && prefLength <= SOFT_MAX_ARRAY_LENGTH) return prefLength;
return hugeLength(oldLength, minGrowth);   // can legitimately exceed SOFT_MAX_ARRAY_LENGTH
```

`ArraysSupport.newLength` itself replaced `ArrayList`'s own cap logic in JDK 13 — bisected against the actual openjdk tags: absent at `jdk-12+33`, where the old field still had six references; present at `jdk-13+33`, where it's gone entirely.

**Follow-up they will ask.** "Is this the kind of thing where 'which JDK' matters before you answer?" Sometimes — a codebase genuinely pinned to JDK 12 or earlier really does have `MAX_ARRAY_SIZE` as a live field on `ArrayList`, so the premise isn't universally wrong, it's version-scoped; asking which JDK first is the right move whenever the two true answers actually diverge, not a stall tactic.

### Q37. Can an `ArrayList` ever equal a `LinkedList`, and can `hashCode()` on a list throw an exception?

**Say this.** Yes to both, and neither is a bug. `List.equals` is specified structurally — the other object must be a `List`, sizes must match, and every corresponding pair must satisfy `Objects.equals` — with no mention of concrete class, so an `ArrayList` and a `LinkedList` holding the same elements in the same order are equal by spec, which is exactly why the implementation tests `instanceof List` rather than `getClass() == ArrayList.class`. And yes, `hashCode()` can throw `ConcurrentModificationException` — it snapshots `modCount` before running the specified `31 * hash + e.hashCode()` loop and checks it again after, so a concurrent structural change during a `HashMap` lookup can throw from inside what looks like a pure query.

**The mechanism.**

```java
new ArrayList<>(List.of("a","b")).equals(new LinkedList<>(List.of("a","b"))); // true
```

`ArrayList` does keep a private fast path, `equalsArrayList`, taken only when the other object's class is exactly `ArrayList` — it indexes both backing arrays directly instead of driving an iterator, but produces the identical result the general spec-driven path would.

**Follow-up they will ask.** "What does `list.sort(c)` actually run underneath, and what happens with a broken comparator?" `Arrays.sort` on the backing array itself, no copy, which runs TimSort; TimSort's response to a comparator that violates antisymmetry or transitivity is `IllegalArgumentException: Comparison method violates its general contract!`, thrown by the sort — not the list, not the comparator — and only sometimes, since detection is a merge-invariant check tripped by that particular input's run structure, not an upfront check against every pair. `sort` itself is bracketed by the same `modCount` snapshot-and-recheck used everywhere else in the class, and it still bumps `modCount` at the end even though `size()` never changes, so it invalidates any live iterator exactly as an insertion would.

### Q38. What are the different forms of "turn a stream into a `List`," and does `Arrays.asList(arr).toArray()` give back an array of your original type?

**Say this.** Three distinct forms, and they are not interchangeable. `stream().toList()`, since Java 16, returns an immutable list where `add` throws; `stream().collect(Collectors.toList())` returns a genuinely mutable `ArrayList`, with no documented guarantee it will always be that class, just today's behaviour; `stream().collect(Collectors.toUnmodifiableList())` is immutable and additionally null-hostile, unlike `toList()`, which permits null even though both land in the exact same `ImmutableCollections` runtime class for the same element count. On the second question — no, not anymore. `Arrays.asList(arr).toArray()` returned an array of your original component type on Java 8, because the implementation was `return a.clone()`; from Java 9 it's `Arrays.copyOf(a, a.length, Object[].class)`, always `Object[]`, dated to JDK-6260652.

**The mechanism.**

```java
String[] instrumentIds = {"AA-610", "AA-620"};
Object[] viaAsList = Arrays.asList(instrumentIds).toArray();   // Object[] on 9+, String[] on 8
Object[] viaCopy   = new ArrayList<>(Arrays.asList(instrumentIds)).toArray(); // always Object[]
viaAsList[0] = Integer.valueOf(7);   // ArrayStoreException on 8, fine on 9+
```

`new ArrayList<>(c).toArray()` has returned `Object[]` on every JDK ever released, unlike the `Arrays.asList` case — `elementData` is declared `Object[]`, and the collection constructor's non-`ArrayList` branch runs `Arrays.copyOf(a, size, Object[].class)` precisely to sanitise any covariant array a caller hands in.

**Follow-up they will ask.** "What's the right idiom for `toArray(T[])`, and why?" `entries.toArray(new T[0])` or `entries.toArray(T[]::new)` since Java 11 — never `new T[list.size()]`, because if the list shrinks between reading `size()` and calling `toArray`, the pre-sized array leaves a stray null tail instead of failing loudly, surfacing as an unrelated NPE far from the cause. This rests on erasure: `new E[n]` is illegal because there's no `E` left at runtime to allocate from, which is also why `(E) elementData[i]` inside `ArrayList` is a no-op cast at runtime and a real `ClassCastException` from heap pollution fires at the caller's narrowing, not inside `ArrayList` itself.

### The stale-premise move

Three of the questions above — 30, 36, and 38 — embed a claim that used to be true, is not true today, or was never true. Treat the question as two bundled questions: is the premise correct, and what is the real answer. Answer the real question first, in the form that is true for the target version, and name the version boundary as supporting evidence, not as a correction aimed at the interviewer. Never stop to point out the premise is wrong before answering, and never agree with it just to keep moving — both read as weaker than answering straight. The one genuine exception: a codebase pinned to a specific old JDK can make an otherwise-stale premise simply correct for that codebase — `MAX_ARRAY_SIZE` really is a live field through JDK 12, and `Arrays.asList(arr).toArray()` really did preserve the array's type through JDK 8. When the two true answers genuinely diverge by version, asking "which JDK is this running on" first is the right move, not a stall.

Worked, for the doubling premise:

> Interviewer: "So when `ArrayList` doubles, how many array copies happen by the time you've inserted a million elements?"
>
> You: "It's actually never doubled — the growth factor has been 1.5× in every released JDK, Java 8 included; `Vector` is the one that doubles. At 1.5× the amortised cost per element is bounded by `f/(f-1)`, which for 1.5 is 3 copies per element — so roughly three million copies total, not the two million you'd get from doubling. Doubling would actually mean *fewer* total copies, not more, because you resize less often — the tradeoff is the wasted slack in between."

That answer never says "you're wrong." It answers "how many copies" using the true growth factor and volunteers the correction as the reason the number differs from what a doubling assumption would predict — the discipline that keeps a stale-premise question from turning into either agreement or a lecture.

## Pitfalls

### "My for-each loop didn't throw, so nothing was silently missed"

**Wrong**
```java
for (ReviewCase rc : batchB) if (rc.assignedOperatorId() != null) batchB.remove(rc);
// no exception — the removal at the second-to-last index was silently accepted
```

**Right**
```java
batchB.removeIf(rc -> rc.assignedOperatorId() != null); // one O(n) pass, no iterator race
```

**Why people believe it:** `ConcurrentModificationException` fires for most removal positions, which reads like a completeness guarantee. It is best-effort precisely because it structurally cannot fire for the last one or two positions.

### "I answered the `LinkedList`-versus-`ArrayList` question from big-O alone"

**Wrong**
```java
// "both O(n) for a full scan, so it doesn't matter which one I pick"
```

**Right** Cite the measured constant-factor gap: 103 microseconds versus 329 for a 200,000-element for-each, a 3.2× difference at identical complexity, driven by cache locality, not algorithmic cost — and separately, `get(i)` in a loop over `LinkedList` is a different complexity class entirely, O(n²), not merely a slower O(n).

**Why people believe it:** big-O is what gets taught as "the" answer to performance questions, and it is genuinely the right first filter — but two operations at the same big-O can differ by orders of magnitude in wall-clock time, and an interviewer testing depth is listening for whether you know that.

### "Catching `ConcurrentModificationException` handles the concurrent-modification case"

**Wrong**
```java
try {
    for (String s : shared) process(s);
} catch (ConcurrentModificationException e) {
    // "handled" — retry, log, move on
}
```

**Right** Confine the list to one thread and publish it immutably (`List.copyOf`), or use a structure built for concurrent access (`CopyOnWriteArrayList`, a `BlockingQueue`, `Collections.synchronizedList` with the caller holding its monitor for the whole traversal). CME is a best-effort single-thread detector — under genuine concurrent misuse the same race can just as easily corrupt state silently with no exception at all, so catching it fixes nothing about the underlying data race.

**Why people believe it:** the exception has "concurrent" in its name and looks like exactly the signal a concurrency bug should raise, so catching it feels like handling the concurrency problem rather than merely handling one of several possible symptoms of it.

### "The two lists have different classes, so `equals` must be false"

**Wrong**
```java
assertFalse(arrayListOfIds.equals(linkedListOfIds));  // fails — they're both [A, B, C]
```

**Right**
```java
assertTrue(arrayListOfIds.equals(linkedListOfIds));   // List.equals is structural, not class-based
assertNotEquals(arrayListOfIds.getClass(), linkedListOfIds.getClass()); // this is the check they meant
```

**Why people believe it:** `Object.equals` defaults to identity, and most hand-written `equals` overrides do check `getClass()` — `List.equals`'s spec choosing `instanceof List` instead, deliberately, to make every conforming `List` implementation interchangeable by value, cuts against that habit.

## Cheat sheet

| Topic | Fact |
|---|---|
| `Itr` state | `cursor`, `lastRet` (−1 if none), `expectedModCount` |
| `hasNext()` checks `modCount`? | No — only `next()` does |
| The one silent CME escape | Removing the second-to-last element in a for-each |
| `Iterator.remove()` cost | O(n) per call — same `arraycopy` shift as `remove(int)` |
| `ListIterator.set()` resyncs? | No — never bumps `modCount`, nothing to resync |
| `SubList` fields | `root`, `parent`, `offset`, `size`, inherited `modCount` — zero copies |
| Mutate root, hold the view | View's next access throws CME — Javadoc says "undefined" |
| `reversed()` runtime class | `ReverseOrderListView$Rand` — write-through, not a copy |
| `reversed().add(x)` lands | At the front of the original |
| `trySplit()` moves | Two ints — `index`/`mid` — zero element copies |
| `characteristics()` | `16464` = `ORDERED \| SIZED \| SUBSIZED` |
| Why `LinkedList` parallelizes badly | Its spliterator has neither `SIZED` nor `SUBSIZED` |
| `elementData` serialization | `transient`; deserialized capacity == `size`, zero slack |
| Empty default `ArrayList` + 1 elem | 80 bytes; presized(1) + 1 elem: 48 bytes |
| Per-element cost | `ArrayList` 4 B + ≤33% slack; `LinkedList` 24-B `Node`, ~6× |
| Real growth factor | `oldCapacity + (oldCapacity >> 1)` — 1.5×, never doubles |
| `MAX_ARRAY_SIZE` today | Gone since JDK 13; real cap is `Integer.MAX_VALUE` |
| 100k default adds vs presized | 584 µs vs 358 µs — 39% saved, 2.13 copies/element |
| for-each / `get(i)` on `LinkedList` | 3.2× slower / ~3500× slower than `ArrayList` |
| Honest `LinkedList`-wins case | Held `ListIterator` cursor, no indexing, no hot scan |
| Head insertion, right answer | `ArrayDeque` — beats `LinkedList` on every other axis too |
| Concurrent `add`, measured | ~70% of appends lost per run — the normal outcome, not rare |
| Retained-capacity leak | `clear()` nulls elements, never shrinks `elementData` |
| `newLength` arrives | JDK 13 |
| `toArray` covariance changes | JDK 9 (`Arrays.asList` result stops being covariant) |
| `SequencedCollection` retrofit | JDK 21 |
| `ArrayList` equals `LinkedList`? | Yes — `List.equals` is structural, spec-defined |
| `hashCode()` can throw CME? | Yes — snapshots and rechecks `modCount` |
| `stream().toList()` vs `Collectors.toList()` | Immutable, permits null / mutable `ArrayList` |
| Right `toArray(T[])` idiom | `new T[0]` or `T[]::new` — never `new T[list.size()]` |

## Self-test

<details><summary><strong>Q1.</strong> Why does `ListIterator.previousIndex()` return −1 on a freshly created `listIterator(0)`, and is that an error state?</summary>

No — it is a valid sentinel, not an error. `previousIndex()` is defined as `cursor - 1`, and a fresh iterator at position 0 has nothing before it, so −1 correctly signals "there is no previous element." Guard with `hasPrevious()` before calling `previous()`, not by treating a −1 return from `previousIndex()` as a fault.

</details>

<details><summary><strong>Q2.</strong> A parallel stream over an `ArrayList` and one over a `LinkedList` of the same size are given the same fork-join pool. Name the concrete spliterator fact that makes one split cheaply and the other not.</summary>

`ArrayList.spliterator()` reports `SIZED | SUBSIZED` (measured 16464 with `ORDERED`), so the framework knows the exact count up front and can plan a whole split tree with zero element copying — `trySplit()` only moves two ints. `LinkedList`'s spliterator reports neither, so the framework has no size information to plan splits against and each `next` hop still pays the pointer-chasing cost besides.

</details>

<details><summary><strong>Q3.</strong> A list is presized with `new ArrayList<>(10_000)`, filled, then serialized and deserialized. What is its capacity after the round trip, and why?</summary>

Exactly its element count, with zero slack — the presizing is completely discarded. `writeObject` writes only `size` and the live elements; `readObject` allocates `new Object[size]`, ignoring the capacity value it wrote (labelled "capacity" only for historical parity with `clone()`), so nothing about the original capacity survives.

</details>

<details><summary><strong>Q4.</strong> Why is "amortised O(1)" not the same promise as "every call is fast," and where does that distinction actually bite in production?</summary>

Amortised O(1) bounds the total cost over n calls divided by n — it says nothing about any single call. The specific `add` that triggers a `grow()` is genuinely O(n): a full copy of every existing element. It bites on a latency-sensitive path — a single append during the 3,400/sec settlement burst can land on that resizing call and take far longer than its neighbours even though the long-run average holds.

</details>

<details><summary><strong>Q5.</strong> Two threads run `add()` on one shared `ArrayList`, and no exception is ever thrown across five runs. What is the strongest conclusion you can draw about correctness?</summary>

None — the absence of an exception proves nothing. The measured five-run reproduction shows roughly 70% of appends silently lost in every run with zero exceptions in three of the five; `ConcurrentModificationException` is a best-effort, single-thread-oriented detector that can already miss under ordinary single-threaded misuse, so its absence under genuine concurrent misuse is not evidence of safety.

</details>

<details><summary><strong>Q6.</strong> Why does a heap dump showing `size() == 0` alongside a very large retained `Object[]` not mean the array is unreachable?</summary>

`clear()` nulls every element slot and resets `size` to zero but never reassigns `elementData`, so the array stays reachable through the still-live field — it just holds nulls at every slot up to its old peak size. Only `trimToSize()` or replacing the field reclaims it; `size()` alone never reports it because capacity is `elementData.length`, not a tracked field.

</details>

<details><summary><strong>Q7.</strong> Why does naming JDK 9 for the `MAX_ARRAY_SIZE`-to-`ArraysSupport` move read as a weaker answer than naming JDK 13, even though both are "recent-ish"?</summary>

Because it's simply the wrong release — this run bisected the actual openjdk source and found `ArraysSupport.newLength` absent at tag `jdk-12+33` and present at `jdk-13+33`. JDK 9 is where `grow()`'s signature changed to return an array and `Arrays.asList(...).toArray()` lost its covariance — a different, real change in the same neighbourhood that gets confused with the JDK 13 one specifically because both are "something moved out of `ArrayList` into a shared helper."

</details>

<details><summary><strong>Q8.</strong> A `List<WithdrawalTransaction>` is used as a `HashMap` key, then one of its elements is mutated in place after the map insert. What breaks, and is that `ArrayList`'s fault?</summary>

The lookup breaks — the map computed and stored the entry using the hash at insertion time, but the key's live `hashCode()` now reflects the mutated contents while the map's bucket placement still reflects the old hash, so a later lookup with an equal-by-value key checks the wrong bucket and the entry becomes permanently unfindable. Not `ArrayList`'s fault: `hashCode()` is correctly computed from current contents every time, exactly as specified — the bug is using a mutable object as a map key at all. `List.copyOf(list)` before insertion is the fix.

</details>

<details><summary><strong>Q9.</strong> `entries.toArray(new LedgerEntry[entries.size()])` is offered as an optimisation over `entries.toArray(new LedgerEntry[0])`. Is it actually faster, and what is the real risk?</summary>

It is not a reliable optimisation and it carries a real risk: if `entries` shrinks between the `size()` call and the `toArray()` call, the pre-sized array is left with a stray `null` at the tail instead of the method allocating a correctly-sized replacement, and that `null` surfaces as an `NullPointerException` far from this call site rather than failing loudly here. The zero-length form is sized exactly right by the JDK itself with no such window.

</details>

<details><summary><strong>Q10.</strong> Why does the disciplined response to "when `ArrayList` doubles..." name `Vector` rather than just saying "it doesn't double"?</summary>

Because naming the type the premise actually describes turns a correction into an answer — the interviewer's mental model of "some JDK collection doubles" is not wrong, it is misattributed, and `Vector`'s `newCapacity = 2 * oldCapacity` (when `capacityIncrement` is 0) is exactly that behaviour. Saying only "it doesn't double" answers half the bundled question and leaves the interviewer without the actual mechanism they were reaching for.

</details>

---

**Questions answered:** Q-46 (second half)
**Sets up:** Next: eight predict-the-output puzzles and the atomic concept checklist.
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 468
