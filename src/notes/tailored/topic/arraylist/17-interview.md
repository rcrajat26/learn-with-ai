# ArrayList — 17 Interview

**Target version: Java 21.** | [Map](00-map.md)
Assumes: the whole set, files 01 through 16.
Previous: [16-prove-it.md](16-prove-it.md)

## Summary table

| Field | Value |
|---|---|
| Backing storage | `Object[] elementData` (package-private), plus `int size`; no `capacity` field — capacity is `elementData.length` |
| `modCount` | Declared in `AbstractList`, not `ArrayList` |
| Default first-growth capacity | `DEFAULT_CAPACITY = 10`, only for a no-arg constructed list |
| Two empty sentinels | `EMPTY_ELEMENTDATA` (explicit `0`) vs `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` (no-arg) — distinct so `grow` knows whether to inflate to 10 |
| Growth factor | **1.5x**, `oldCapacity + (oldCapacity >> 1)`, via `ArraysSupport.newLength(old, minGrowth, oldCapacity>>1)` |
| Real sequence | `0 -> 10 15 22 33 49 73 109 163 244 366 549` |
| Growth ceiling | `ArraysSupport.SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` — a **soft** clamp, not a hard one |
| No `MAX_ARRAY_SIZE`/`hugeCapacity` in `ArrayList` since | **JDK 13** |
| `equals`/`hashCode` overridden since | JDK 11 (absent in JDK 8) |
| `remove(int)` vs `remove(Object)` | index vs value — the classic overload trap |
| Fail-fast trigger | `next()` checks `modCount`; `hasNext()` never does — `cursor != size` only |
| `subList` | `ArrayList$SubList`, write-through, shares the parent's array |
| Java 21 additions | `getFirst`/`getLast`/`addFirst`/`addLast`/`removeFirst`/`removeLast` (overridden, `@since 21`); `reversed()` is a `List` default returning `ReverseOrderListView$Rand`, a **view** |
| Version trap | "private `MAX_ARRAY_SIZE` field" and "doubles" are both false for 21 |

## Questions and answers

### Contract and hierarchy

**Q1. What does `ArrayList` guarantee that a bare array does not?**
Resizability, and the full `List` contract — ordered, index-addressable, duplicates allowed, nulls allowed. It does not guarantee thread safety or that a concurrent structural change during iteration will always be caught.
**Follow-up they will ask:** Is it synchronized? No — wrap with `Collections.synchronizedList` or use `CopyOnWriteArrayList` if you need that.

**Q2. Why is `ArrayList` not thread-safe by default?**
Because none of its mutating operations are synchronized and `modCount` is a plain `int`, not volatile or atomic — two threads mutating concurrently can corrupt `size`/`elementData` visibility, not just trip fail-fast.

**Q3. What does `RandomAccess` actually buy you, given it has no methods?**
It's a pure marker. Algorithms like `Collections.binarySearch`, `shuffle`, and `reverse` branch on `instanceof RandomAccess` to pick an index-loop instead of an iterator walk, because positional access here is O(1), unlike `LinkedList`.

**Q4. Where does `ArrayList` sit in the Java 21 type graph?**
`Iterable -> Collection -> SequencedCollection -> List`, and separately `AbstractCollection -> AbstractList -> ArrayList`. `SequencedCollection` is new in 21 (JEP 431) and sits between `Collection` and `List`.

**Q5. What did `SequencedCollection` add?**
`reversed()` (abstract) plus defaults `addFirst`/`addLast`/`getFirst`/`getLast`/`removeFirst`/`removeLast`. `ArrayList` overrides all of these except `reversed()`, which it inherits as a `List` default.
**Follow-up they will ask:** Is `reversed()` a copy? No, a view — writes propagate back.

**Q6. Who are `ArrayList`'s siblings in the `List` family?**
`LinkedList`, `Vector`/`Stack` (legacy, synchronized), `CopyOnWriteArrayList`, the immutable `List.of(...)`, and the fixed-size `Arrays.asList(...)` view.

### Construction and capacity

**Q7. What are the three constructors and what does each cost?**
No-arg: O(1), defers allocation to `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`. `int` capacity: O(1) if positive, allocates immediately; `0` uses the other empty sentinel. `Collection`: O(n), copies via `toArray()`.

**Q8. Why does `new ArrayList<>()` behave differently from `new ArrayList<>(0)`?**
Both start with a zero-length array, but they're different sentinel objects. `grow` checks `elementData != DEFAULTCAPACITY_EMPTY_ELEMENTDATA` to decide whether to jump straight to capacity 10. So one add on `new ArrayList<>()` yields capacity 10; one add on `new ArrayList<>(0)` yields capacity 1.

**Q9. How do you observe an `ArrayList`'s real capacity from outside the class?**
There's no public API — you need reflection on `elementData` (with `--add-opens java.base/java.util=ALL-UNNAMED`) or an indirect trick like watching allocation via a profiler. There is no `capacity()` method, unlike `Vector`.

**Q10. What's the cost of `new ArrayList<>(existingList)`?**
O(n) — the constructor calls `c.toArray()` and stores that array directly (with a defensive check for wrong-typed results), so it's one array allocation plus one copy, not n individual `add` calls.

### Growth internals

**Q11. Walk me through what happens when `add` finds the array full.**
`add(E)` increments `modCount`, then calls a private three-argument helper. That helper checks `s == elementData.length`; if so it calls `grow()`, which computes `minCapacity = size + 1` and delegates to `ArraysSupport.newLength(oldCapacity, 1, oldCapacity >> 1)`. The result is `Arrays.copyOf` into a new array, then the element is stored and `size` incremented.

**Q12. Why is there a private three-arg `add` helper instead of inlining everything in `add(E)`?**
A real comment in the JDK source says it keeps `add(E)`'s bytecode under `MaxInlineSize` (default 35 bytes), so the JIT (C1/C2) can still inline the hot call site even when the cold growth path is present.

**Q13. Why 1.5x growth and not 2x?**
It's `oldCapacity + (oldCapacity >> 1)`, a deliberate JDK design tradeoff: doubling wastes more memory per resize on average; 1.5x keeps the amortized copy cost at O(1) (bounded by about 3n total copies to reach size n) while over-allocating less.

**Q14. What is `ArraysSupport.SOFT_MAX_ARRAY_LENGTH` and why "soft"?**
`Integer.MAX_VALUE - 8`, the preferred growth ceiling. It's soft because `hugeLength` can still return a larger `minLength` if the caller genuinely needs more — it's a preference, not a hard cap, so an array can exceed it when required.

**Q15. Does growing ever run in `O(n)` per call?**
Yes, individually — one `grow` call is one `Arrays.copyOf`, which is O(n). It's the *amortized* cost across n appends that's O(1), because copies get geometrically rarer as capacity rises.

### Mutation and cost

**Q16. How does `add(int index, E element)` differ in cost from `add(E)`?**
Both may trigger `grow`, but `add(int, E)` also does a `System.arraycopy` to shift every element from `index` to the end one slot right — O(n-index) versus amortized O(1) for a tail append.

**Q17. What does `remove(int index)` actually do?**
Shifts the tail left by one via `System.arraycopy`, then nulls the last live slot (`es[--size] = null`) so the removed reference doesn't outlive the logical list — otherwise it's a silent memory leak.

**Q18. How does `remove(Object o)` differ from `remove(int index)` mechanically?**
It linear-scans (`o == null` uses `==`, otherwise `o.equals(es[i])` — note it's the **argument's** `equals`), finds the first match via a labelled `break found:`, then calls the same `fastRemove` tail-shift.

**Q19. Why is passing a `HashSet` to `removeAll` better than passing a `List`?**
`removeAll` is backed by `batchRemove`, a single-pass O(n) compaction that calls `c.contains(...)` once per element. If `c` is a `List`, each `contains` is itself O(m), making the whole call O(n·m); a `HashSet` makes each `contains` O(1).

**Q20. What happens if `contains` throws partway through `batchRemove`?**
The `catch` block copies the un-scanned tail back into place before rethrowing, so the list is left structurally valid (no gap, no duplicated slots) even though the throw propagates.

**Q21. Why does `removeIf` use a bitset instead of calling `remove` per match?**
Calling `remove` per match would be O(n) shifts each, so O(n^2) overall. `removeIf` marks survivors in a `long[]` bitset in one linear pass, then compacts once — O(n) total.

**Q22. Does `clear()` shrink the backing array?**
No. It nulls every live slot (for GC) and sets `size = 0`, but capacity is unchanged — verified: capacity 100 stays 100 after `clear()`.

### Iteration and fail-fast

**Q23. How does the fail-fast iterator detect concurrent modification?**
`Itr` captures `expectedModCount = modCount` at creation. `next()` calls `checkForComodification()`, comparing `modCount` to `expectedModCount` and throwing `ConcurrentModificationException` on mismatch.

**Q24. Why doesn't removing the second-to-last element in a for-each throw?**
Because `hasNext()` is just `cursor != size` — it never checks `modCount`. Removing the second-to-last drops `size` to equal `cursor`, so `hasNext()` returns false and the loop exits before `next()` (where the check lives) ever runs again. Removing the *last* element leaves a trailing `hasNext()` that's still true, so `next()` does run and throws.

**Q25. Is fail-fast a guaranteed safety net?**
No — the javadoc calls it best-effort. It exists to fail fast on bugs, not to provide correctness under concurrency.

**Q26. What is the one legal way to remove elements during iteration?**
`Iterator.remove()`. It calls the internal `ArrayList.remove(lastRet)` then resyncs `expectedModCount = modCount`, so the iterator's own view stays consistent.

### Views and aliasing

**Q27. What object does `subList` return, and what does it share with the parent?**
`java.util.ArrayList$SubList`, a private static nested class holding `root`/`parent`/`offset`/`size`. It shares the parent's actual backing array — no copy is made.

**Q28. What happens if you structurally modify the parent, then use the subList view?**
`ConcurrentModificationException` — the view tracks the parent's `modCount` the same way an iterator does.

**Q29. What's the danger of caching a small `subList` of a large list?**
The view holds a strong reference to the parent's whole backing array, so the small view keeps the entire large array reachable — a retention leak disguised as a small object.

**Q30. What does `subList(1,4).clear()` do to the parent?**
Deletes exactly those three elements from the parent list — the view's mutations write through, they aren't local to the view.

### Equality and serialization

**Q31. How does `ArrayList.equals` work across different `List` implementations?**
Per the `List` contract, equality is cross-implementation: same size, same elements in the same order via `equals` element-wise. `ArrayList` has a fast path (`equalsArrayList`) when the argument's exact class is `ArrayList`, and falls back to an iterator-based `equalsRange` otherwise — including for an `ArrayList` subclass.

**Q32. Can `equals` or `hashCode` throw?**
Yes — both capture `modCount` before scanning and call `checkForComodification()` after, so a concurrent structural change during the scan throws `ConcurrentModificationException`. Genuinely surprising the first time you see it.

**Q33. Why is `elementData` marked `transient`?**
So the default serialization mechanism skips it; custom `writeObject`/`readObject` write only the live `size` elements, not the reserved capacity — a capacity-10 list with 4 elements serializes 4, not 10.

**Q34. What guards `readObject` against a maliciously huge stream?**
It calls a shared-secrets array-size check before allocating the backing array — a deserialization-bomb guard against claiming a huge element count with a small actual stream.

### Sorting

**Q35. Does `ArrayList.sort` bump `modCount`?**
Yes — verified: `sort` increments `modCount`, but `set` does not. That matters for fail-fast reasoning: sorting inside an active iteration will trip a CME on the next `next()`, a plain `set` will not.

**Q36. When would `sort(null)` throw a `ClassCastException`?**
When the element type doesn't implement `Comparable` — passing `null` means "use natural ordering," and there is none to fall back on.

### Choosing an implementation

**Q37. When would you reach for `LinkedList` instead of `ArrayList`?**
Almost never for general use — its node-per-element layout means poor cache locality and higher per-element overhead. The one case where it can win is heavy insert/remove at both ends without random access, and even then `ArrayDeque` usually wins.

**Q38. `Arrays.asList` versus `List.of` versus `ArrayList` — what actually differs?**
`Arrays.asList` is a fixed-size *view* over an existing array — `set` succeeds and writes through, `add`/`remove` throw `UnsupportedOperationException`. `List.of` is fully immutable — `set` also throws. `ArrayList` is the only one of the three that's freely mutable and independently backed.

### Versions

**Q39. What changed about growth internals between JDK 8 and JDK 21?**
JDK 8: `grow` was inline with a private static `MAX_ARRAY_SIZE` field and a `hugeCapacity` helper. JDK 13 replaced the whole clamp with a delegation to `ArraysSupport.newLength`, using `SOFT_MAX_ARRAY_LENGTH` outside the class entirely — `MAX_ARRAY_SIZE` and `hugeCapacity` no longer exist in `ArrayList`.

**Q40. When were `equals`/`hashCode` first overridden in `ArrayList`?**
Absent in JDK 8 (inherited from `AbstractList`), present from JDK 11 onward. The exact version among 9/10/11 isn't separable from available sources — state the verified bracket, not a guess.

### Concurrency and streams

**Q41. Is `ArrayList.spliterator()` inherited or overridden, and why does it matter?**
Overridden — `ArrayListSpliterator` splits by index range, which parallelizes cleanly because the backing array supports fast random access; that's why `ArrayList.parallelStream()` tends to scale better than a linked structure's.

**Q42. Does wrapping with `Collections.synchronizedList` make iteration safe?**
It synchronizes individual calls, but iteration still needs external synchronization on the wrapper itself — otherwise a concurrent structural change during a for-each still throws `ConcurrentModificationException` or corrupts state.

## Predict the output

**P1.**
```java
List<String> l = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
for (String s : l) {
    if (s.equals("AA-700")) l.remove(s);
}
```
<details><summary>Answer</summary>

`java.util.ConcurrentModificationException`

</details>
Mechanism: removing the **last** element leaves `hasNext()` true (`cursor` still less than the old `size`), so `next()` runs again and its `checkForComodification()` trips.

**P2.**
```java
List<String> l = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
for (String s : l) {
    if (s.equals("AO-400")) l.remove(s);
}
System.out.println(l);
```
<details><summary>Answer</summary>

No exception. Loop exits early, `AA-700` is never visited. Prints `[AO-100, AA-700]`.

</details>
Mechanism: removing the **second-to-last** element drops `size` to 2, matching `cursor`, so `hasNext()` returns false before `next()` ever re-checks `modCount`.

**P3.**
```java
List<Integer> l = new ArrayList<>(List.of(10, 20, 30));
l.remove(1);
System.out.println(l);
```
<details><summary>Answer</summary>

`[10, 30]`

</details>
Mechanism: `remove(int)` is chosen by overload resolution for a primitive `1`, removing by **index**, not value.

**P4.**
```java
List<Integer> l = new ArrayList<>(List.of(10, 20, 30));
l.remove(Integer.valueOf(20));
System.out.println(l);
```
<details><summary>Answer</summary>

`[10, 30]`

</details>
Mechanism: an explicit `Integer` argument resolves to `remove(Object)`, removing by **value**.

**P5.** (reflection probe reading real `elementData.length`)
```java
var a = new ArrayList<>();      // no-arg
var b = new ArrayList<>(0);     // explicit zero
a.add("x"); b.add("x");
// capacity(a), capacity(b) via reflection on elementData
```
<details><summary>Answer</summary>

`capacity(a) = 10`, `capacity(b) = 1`

</details>
Mechanism: the two empty-array sentinels are distinct objects; `grow` only inflates to `DEFAULT_CAPACITY` when the current array is `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`, which only the no-arg constructor produces.

**P6.**
```java
List<Object> l = new ArrayList<>();
l.add("DEP-301");
l.add(42);
String[] arr = l.toArray(new String[0]);
```
<details><summary>Answer</summary>

`java.lang.ArrayStoreException: arraycopy: element type mismatch: can not cast one of the elements of java.lang.Object[] to the type of the destination array, java.lang.String`

</details>
Mechanism: the runtime array-store check fires when the internal `arraycopy` tries to place the `Integer` into a `String[]` — generics erasure means the compiler never caught this.

**P7.**
```java
List<String> fixed = Arrays.asList("DEP-301", "DEP-400");
fixed.set(0, "X");         // (a)
fixed.add("DEP-500");      // (b)
List<String> immutable = List.of("DEP-301", "DEP-400");
immutable.set(0, "X");     // (c)
```
<details><summary>Answer</summary>

(a) succeeds, `fixed` becomes `[X, DEP-400]`. (b) throws `UnsupportedOperationException`. (c) also throws `UnsupportedOperationException`.

</details>
Mechanism: `Arrays.asList` is a fixed-size array-backed view — writes through `set` are legal, structural changes are not; `List.of` forbids both.

**P8.**
```java
List<String> base = new ArrayList<>(List.of("DEP-301", "DEP-400", "BDP-100", "BDP-200", "BDP-300"));
List<String> sub = base.subList(1, 4);
sub.set(0, "DEP-999");
System.out.println(base);
base.add("EXTRA");
sub.get(0);   // after the parent's structural change
```
<details><summary>Answer</summary>

After `sub.set(0, "DEP-999")`: `base` prints `[DEP-301, DEP-999, BDP-100, BDP-200, BDP-300]`. The subsequent `sub.get(0)` after `base.add("EXTRA")` throws `java.util.ConcurrentModificationException`.

</details>
Mechanism: `subList` writes through to the shared array; a structural change to the parent invalidates the view's cached `modCount`.

**P9.**
```java
List<String> l = new ArrayList<>(List.of("AO-100", "AO-400", "AA-700"));
List<String> rev = l.reversed();
rev.set(0, "AA-800");
System.out.println(l);
System.out.println(rev.getClass());
List<String> empty = new ArrayList<>();
empty.reversed().getFirst();
```
<details><summary>Answer</summary>

`l` becomes `[AO-100, AO-400, AA-800]`. `rev.getClass()` is `java.util.ReverseOrderListView$Rand`. The final call throws `java.util.NoSuchElementException`.

</details>
Mechanism: `reversed()` returns a live view, not a copy, so writing through index 0 of the reversed view (the original's last element) mutates the original; an empty list's `getFirst()` has nothing to return.

**P10.**
```java
List<Integer> l = new ArrayList<>(List.of(1, 2, 3));
l.trimToSize();
l.clear();
// capacity via reflection before and after clear()
l.sort(Comparator.naturalOrder());
l.set(0, 9);
// modCount deltas
```
<details><summary>Answer</summary>

Capacity stays at whatever `trimToSize()` left it (matching size at the time), unchanged by `clear()` — `clear()` only nulls slots and resets `size`, never shrinks the array. `sort` increments `modCount`; the subsequent `set` does not.

</details>
Mechanism: `clear()` and `set` never touch `modCount`-relevant structure beyond what's coded; `sort` is treated as structural because it reorders live slots, `set` overwrites in place.

## The version trap

The single highest-leverage page in this set. Two claims that were once accurate are now wrong, and interviewers frequently still expect the old answer.

**Claim 1 — "`ArrayList` has a private `MAX_ARRAY_SIZE` field."** True through JDK 12. **False from JDK 13 on.** In JDK 21, that constant does not exist inside `ArrayList` at all — it moved to `jdk.internal.util.ArraysSupport.SOFT_MAX_ARRAY_LENGTH`, and it is now a **soft** ceiling rather than a hard one: `hugeLength` can still return a length beyond it if the caller genuinely needs more.

The sentence to say out loud, correct for 21 without contradicting someone who learned the JDK 8 form: *"In older JDKs `ArrayList` had its own private `MAX_ARRAY_SIZE` and a `hugeCapacity` method; since JDK 13 that logic was pulled out into `ArraysSupport.newLength`, so `ArrayList` itself doesn't declare that constant anymore — the effective ceiling, `SOFT_MAX_ARRAY_LENGTH`, is the same value, `Integer.MAX_VALUE - 8`, just relocated and now explicitly soft."*

**Claim 2 — "it doubles."** Never true for `ArrayList`. Growth is `oldCapacity + (oldCapacity >> 1)` — 1.5x, with integer truncation making each step slightly under exact 1.5 (`22` is `15 + 7`, not `22.5`). The verified real sequence from a default-constructed list: `10 15 22 33 49 73 109 163 244 366 549`.

**The refactor landed in JDK 13, not JDK 9 and not JDK 18.** JDK 9 through 12 still have `grow`/`newCapacity` with `MAX_ARRAY_SIZE` inline; `jdk-13-ga` is the first tag with zero occurrences of `MAX_ARRAY_SIZE` and the delegation to `ArraysSupport.newLength` in place.

## Pitfalls

### "I can remove elements in a for-each as long as I only remove one"

**Wrong**
```java
for (String s : list) {
    if (s.equals("AO-400")) list.remove(s);   // "it's just one removal"
}
```
Sometimes throws `ConcurrentModificationException`, sometimes silently skips an element, depending on which index you removed.

**Right**
Use `Iterator.remove()`, or build the result in a separate collection, or use `removeIf`.

**Why people believe it:** the exception doesn't fire for every position, so a quick manual test on the wrong index looks like proof it's safe.

### "Doubling capacity is the standard growth strategy"

**Wrong**
```java
// mental model: "10 becomes 20 becomes 40..."
```
Real measured sequence is `10 15 22 33 49 73 109 163 244 366 549` — never doubles.

**Right**
It's 1.5x via `oldCapacity + (oldCapacity >> 1)`, chosen to trade a slightly higher amortized copy count for less wasted memory per resize than 2x would leave.

**Why people believe it:** many other languages' default dynamic arrays (some `Vector`/`ArrayList` folklore, some other ecosystems' growable arrays) really do double, and the "doubling" heuristic is the one taught first in most algorithms courses.

### "`ArrayList` is synchronized because I've never seen it fail under light load"

**Wrong**
```java
List<String> shared = new ArrayList<>();
// multiple threads call shared.add(...) with no external synchronization
```
Works fine in a demo, then corrupts `size`/`elementData` or throws under real concurrent load.

**Right**
Wrap with `Collections.synchronizedList(new ArrayList<>())` (and synchronize externally for iteration), or use `CopyOnWriteArrayList` for read-heavy, write-light sharing.

**Why people believe it:** absence of an observed failure under low contention is mistaken for a guarantee; `ArrayList`'s javadoc explicitly disclaims thread safety, but that's easy to skip.

### "A stale `subList` reference is harmless once I'm done reading it"

**Wrong**
```java
List<String> page = hugeList.subList(0, 20);   // cached for "later"
```
`hugeList`'s entire backing array stays reachable through `page` even though only 20 elements are used.

**Right**
Copy out what you need — `new ArrayList<>(hugeList.subList(0, 20))` — if the view will outlive the parent's usefulness.

**Why people believe it:** a "sub" list reads as smaller, and nothing in the API signature hints that it retains the parent's whole array.

## Cheat sheet

| Topic | Fact |
|---|---|
| Backing storage | `Object[] elementData` + `int size`; capacity = `elementData.length` |
| `modCount` | in `AbstractList`, inherited |
| Default capacity on first growth | 10 (no-arg constructor only) |
| Growth factor | 1.5x, `old + (old>>1)`, via `ArraysSupport.newLength` |
| Growth ceiling | `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8`, soft |
| `MAX_ARRAY_SIZE`/`hugeCapacity` in `ArrayList` | removed in JDK 13 |
| `equals`/`hashCode` overridden | since JDK 11, absent in JDK 8 |
| `remove(int)` | by index |
| `remove(Object)` | by value, uses argument's `equals` |
| `hasNext()` | `cursor != size`, never checks `modCount` |
| `next()` | checks `modCount`, throws CME on mismatch |
| `clear()` | nulls slots, resets `size`; capacity unchanged |
| `sort` | bumps `modCount` |
| `set` | does not bump `modCount` |
| `subList` | shares parent array, write-through, CME on parent structural change |
| `Arrays.asList` | fixed-size view, `set` OK, `add`/`remove` throw |
| `List.of` | fully immutable, `set` throws |
| `reversed()` (Java 21) | `List` default, returns `ReverseOrderListView$Rand`, a view |
| `getFirst`/`getLast`/... | overridden in `ArrayList`, `@since 21` |
| `toArray(T[])` type mismatch | `ArrayStoreException` |
| Serialization | `elementData` transient, writes only live elements, deserialize-bomb guard |

## Self-test

**Q1.** Why does `hasNext()` never need to check `modCount`, even though `next()` does?

<details><summary>Answer</summary>

`hasNext()` only answers "is there a next index to visit" — a purely positional question answered by comparing `cursor` to `size`. `modCount` detection is only meaningful at the point you actually try to read an element, which is `next()`'s job. This split is exactly why the fail-fast contract is best-effort: a mutation that happens to make `cursor == size` true early hides from `hasNext()` entirely.

</details>

**Q2.** Why does `grow()` need to distinguish `EMPTY_ELEMENTDATA` from `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` instead of using one shared empty array?

<details><summary>Answer</summary>

Because the two constructors that produce them have different growth intents: an explicit `new ArrayList<>(0)` means "start truly empty, grow normally from there," while `new ArrayList<>()` means "defer the decision, but grow to 10 the first time you must." If both used the same sentinel, `grow` couldn't tell which behavior the caller wanted on first growth.

</details>

**Q3.** Why can `equals` and `hashCode` throw `ConcurrentModificationException` when neither is an iteration API in the everyday sense?

<details><summary>Answer</summary>

Both scan the backing array end to end internally (via `equalsRange`/`equalsArrayList` and `hashCodeRange`), and both capture `modCount` before the scan and check it after with `checkForComodification()`. Structurally, that scan is iteration even though it's not exposed through `Iterator` — so the same fail-fast machinery applies.

</details>

**Q4.** Why does `batchRemove`'s `catch` block do a `System.arraycopy` of the tail before rethrowing?

<details><summary>Answer</summary>

`batchRemove` compacts in place using read cursor `r` and write cursor `w`. If `c.contains()` throws partway through, the elements from `r` onward haven't been scanned yet and would be lost if left where the write cursor stopped. Copying that unscanned tail back to `w` preserves every element that wasn't determined to be removed, keeping the list structurally valid for `AbstractCollection`-compatible behavior even on a thrown exception.

</details>

**Q5.** Why is the private three-argument `add` helper split out of the public `add(E)` at all?

<details><summary>Answer</summary>

Because the JVM's C1/C2 compilers only inline call sites under a byte-size threshold (`MaxInlineSize`, default 35). If `add(E)`'s bytecode included the full growth-check-and-store logic inline, it could exceed that threshold and lose inlining at hot call sites; splitting the store logic into a small helper keeps `add(E)` itself compact enough to inline in tight loops.

</details>

**Q6.** Why does removing an element by `Iterator.remove()` never throw, while removing the same element via the list's own `remove(Object)` inside a for-each sometimes does?

<details><summary>Answer</summary>

`Iterator.remove()` calls the list's internal remove and then explicitly resynchronizes `expectedModCount = modCount` on the same iterator instance, so the iterator's own bookkeeping never drifts from reality. Calling `list.remove(...)` directly bumps `modCount` with no iterator involved to resync — the for-each's hidden iterator is left holding a stale `expectedModCount`, which is exactly the mismatch fail-fast is built to catch.

</details>

## Atomic concept checklist

- [ ] `ArrayList` guarantees ordering, duplicates, and nulls; it does not guarantee thread safety
- [ ] Fail-fast is documented as best-effort, not a correctness guarantee
- [ ] `RandomAccess` declares zero methods and is purely a marker interface
- [ ] Library algorithms branch on `instanceof RandomAccess` to choose index-based vs iterator-based strategies
- [ ] `List<E> extends SequencedCollection<E>` as of Java 21 (JEP 431)
- [ ] `SequencedCollection` declares abstract `reversed()` plus six default methods
- [ ] `ArrayList` overrides `getFirst`/`getLast`/`addFirst`/`addLast`/`removeFirst`/`removeLast`, each `@since 21`
- [ ] `ArrayList` does not override `reversed()` — it uses the `List` default
- [ ] `reversed()` returns `ReverseOrderListView$Rand`, a live view, not a copy
- [ ] An empty list's `getFirst()` throws `NoSuchElementException`
- [ ] `trimToSize` and `ensureCapacity` are the only two members with no supertype declaration
- [ ] `containsAll`, `toString`, `stream`, `parallelStream`, `toArray(IntFunction)` are inherited, not overridden
- [ ] The no-arg constructor is O(1) and defers allocation via `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`
- [ ] `new ArrayList<>(Collection)` is O(n), built from `c.toArray()`
- [ ] `EMPTY_ELEMENTDATA` and `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` are two distinct empty-array objects
- [ ] `new ArrayList<>()` then one add yields capacity 10
- [ ] `new ArrayList<>(0)` then one add yields capacity 1
- [ ] There is no public `capacity()` method; capacity must be read via reflection
- [ ] `elementData` is package-private (not private) "to simplify nested class access"
- [ ] There is no dedicated `capacity` field — capacity is `elementData.length`
- [ ] `modCount` is declared in `AbstractList`, not `ArrayList`
- [ ] `ArrayList.class.getDeclaredField("modCount")` throws `NoSuchFieldException`, proving the inheritance
- [ ] `add(E)` increments `modCount` before delegating to the private three-arg helper
- [ ] The private three-arg `add` helper exists to keep bytecode under `MaxInlineSize` (35 bytes)
- [ ] `grow()` calls `grow(size + 1)`
- [ ] `grow(int)` delegates to `ArraysSupport.newLength(oldCapacity, minGrowth, oldCapacity >> 1)`
- [ ] Growth is 1.5x: `oldCapacity + (oldCapacity >> 1)`, never doubling
- [ ] The real measured capacity sequence is `10 15 22 33 49 73 109 163 244 366 549`
- [ ] Integer truncation makes each growth step slightly under exact 1.5x
- [ ] `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` lives in `ArraysSupport`, not `ArrayList`
- [ ] The ceiling is soft — `hugeLength` can exceed it if `minLength` genuinely requires it
- [ ] `ArrayList` has no `MAX_ARRAY_SIZE` field and no `hugeCapacity` method as of JDK 13+
- [ ] The `ArraysSupport.newLength` refactor landed in JDK 13, not 9 or 18
- [ ] `add(int index, E)` shifts the tail via `System.arraycopy`, costing O(n - index)
- [ ] `remove(int)` shifts the tail left and nulls the vacated last slot
- [ ] `remove(Object)` scans linearly and removes by the argument's `equals`, not the element's
- [ ] `remove(int)` vs `remove(Integer.valueOf(x))` is the classic index-vs-value overload trap
- [ ] `batchRemove` backs both `removeAll` and `retainAll` with a single-pass read/write compaction
- [ ] Passing a `HashSet` to `removeAll` is O(n); passing a `List` degrades toward O(n·m)
- [ ] `batchRemove`'s `catch` preserves the unscanned tail if `contains` throws mid-scan
- [ ] `removeIf` uses a `long[]` bitset to mark survivors in one pass, avoiding O(n²)
- [ ] `clear()` nulls every live slot but does not shrink the backing array
- [ ] `hasNext()` is `cursor != size` and never checks `modCount`
- [ ] `next()` checks `modCount` via `checkForComodification()` before returning an element
- [ ] Removing the last element in a for-each throws `ConcurrentModificationException`
- [ ] Removing the second-to-last element in a for-each silently skips the last element, no exception
- [ ] `Iterator.remove()` resynchronizes `expectedModCount` after removing, avoiding the CME
- [ ] Mutating a list inside its own `forEach` throws `ConcurrentModificationException`
- [ ] `subList` returns `ArrayList$SubList`, sharing the parent's actual array
- [ ] Writes through a `subList` view are visible in the parent at the corresponding offset
- [ ] A structural change to the parent invalidates an existing `subList` view, causing CME on next access
- [ ] `subList(a,b).clear()` deletes that exact range from the parent
- [ ] A cached small `subList` retains the parent's entire backing array in memory
- [ ] `List` equality is defined across implementations — an `ArrayList` can equal a `LinkedList` or `List.of(...)`
- [ ] `ArrayList.equals` has a same-class fast path (`equalsArrayList`) and a generic fallback (`equalsRange`)
- [ ] `equals` and `hashCode` both capture and re-check `modCount`, and can throw CME
- [ ] `hashCode` folds elements with the `31 * hash + elementHash` pattern
- [ ] `elementData` is `transient`; serialization writes only live elements, not reserved capacity
- [ ] `readObject` performs an array-size sanity check before allocating, guarding against deserialization bombs
- [ ] `writeObject` captures `modCount` and throws CME if it changes mid-write
- [ ] `List.sort` bumps `modCount`; `set` does not
- [ ] `sort(null)` on a non-`Comparable` element type throws `ClassCastException`
- [ ] A constant-returning comparator is not guaranteed to trigger the "violates its general contract" exception on every run
- [ ] `ArrayList` is the default choice; `LinkedList` rarely wins due to poor cache locality
- [ ] `Arrays.asList` is a fixed-size view: `set` succeeds, `add`/`remove` throw `UnsupportedOperationException`
- [ ] `List.of(...)` is fully immutable: even `set` throws `UnsupportedOperationException`
- [ ] `CopyOnWriteArrayList` suits read-heavy, write-light concurrent sharing
- [ ] `Collections.synchronizedList` synchronizes individual calls but not iteration by itself
- [ ] JDK 8's growth clamp used a private `MAX_ARRAY_SIZE` field and `hugeCapacity` method
- [ ] JDK 11–12 split growth into `grow(int)` plus a private `newCapacity(int)`, still with `MAX_ARRAY_SIZE`
- [ ] JDK 13 removed `MAX_ARRAY_SIZE`/`hugeCapacity` entirely, delegating to `ArraysSupport.newLength`
- [ ] `equals`/`hashCode` are absent (inherited) in JDK 8, present (overridden) from JDK 11 onward
- [ ] The exact JDK (9, 10, or 11) that first added the `equals`/`hashCode` override is unverified in this set
- [ ] `ArrayListSpliterator` splits by index range, enabling efficient parallel streams
- [ ] `toArray(new String[0])` on a `List<Object>` holding a non-`String` throws `ArrayStoreException`
- [ ] A capacity-10, size-4 list costs about 80 bytes for the list shell plus array, excluding elements, under compressed oops

---

**Questions answered:** Q-36, plus a recall pass over Q-01 through Q-35
**Sets up:** — (last file in the set)
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 558
