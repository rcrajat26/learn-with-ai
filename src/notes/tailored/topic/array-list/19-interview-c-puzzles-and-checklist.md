# `ArrayList` — 19 Interview C: puzzles and checklist

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: files 01 through 18 in full.
Previous: [18 Interview B — questions 20 to 38](18-interview-b-questions.md)

This file introduces nothing. Eight adversarial snippets — predict the
output before scrolling past the fold, then check the mechanism against the
file that taught it. The checklist at the end is a flat recall pass over
files 01–18; a failed line points back to its file, not a fact to
re-memorise here.

## The eight puzzles

### P1. A `for-each` removal that throws, and an identical one that doesn't

```java
record Restriction(String type, String source, Instant appliedAt,
                    Instant expiresAt, boolean manualOverride) {}

static List<Restriction> fourRestrictions() {
    return new ArrayList<>(List.of(
        new Restriction("STAKE_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false),
        new Restriction("WITHDRAWAL_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false),
        new Restriction("DEPOSIT_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false),
        new Restriction("COOLING_OFF", "CLIENT", Instant.now(), null, false)));
}

List<Restriction> active = fourRestrictions();
for (Restriction r : active) {
    if (r.type().equals("WITHDRAWAL_BLOCKED")) active.remove(r);
}

List<Restriction> alsoActive = fourRestrictions();
for (Restriction r : alsoActive) {
    if (r.type().equals("DEPOSIT_BLOCKED")) alsoActive.remove(r);
}
System.out.println(alsoActive.stream().map(Restriction::type).toList());
```

**Predict the output before reading on.**

**What it prints**

```
java.util.ConcurrentModificationException
[STAKE_BLOCKED, WITHDRAWAL_BLOCKED, COOLING_OFF]
```

**Why.** `active` removes index 1 of 4; `cursor` becomes 2, `size` drops to
3, and `hasNext()` evaluates `2 != 3` — true — so the loop re-enters
`next()`, which checks `modCount` and throws. `alsoActive` removes index 2
of 4 — the second-to-last; `cursor` becomes 3, `size` drops to 3, and
`hasNext()` evaluates `3 != 3` — false — the loop exits before the check
runs again. File 08 walks `Itr`'s fields and `hasNext() { return cursor !=
size; }`.

**What they are really testing.** Whether you know fail-fast checks on the
*next* call, not the mutation itself — so whether it fires depends on which
index you removed, not on whether the removal was safe.

### P2. Two exceptions from a one-element list, and a third from an empty one

```java
List<Restriction> queue = new ArrayList<>(List.of(
        new Restriction("STAKE_BLOCKED", "SYSTEM_ONBOARDING", Instant.now(), null, false)));

try {
    queue.get(3);
} catch (IndexOutOfBoundsException e) {
    System.out.println(e.getMessage());
}
try {
    queue.add(3, queue.get(0));
} catch (IndexOutOfBoundsException e) {
    System.out.println(e.getMessage());
}
try {
    new ArrayList<Restriction>().getFirst();
} catch (NoSuchElementException e) {
    System.out.println(e.getClass().getName());
}
```

**Predict the output before reading on.**

**What it prints**

```
Index 3 out of bounds for length 1
Index: 3, Size: 1
java.util.NoSuchElementException
```

**Why.** `get` routes through `Objects.checkIndex(index, size)`, rejecting
`index == size`, message "length N". `add(int, E)` routes through
`ArrayList`'s own `rangeCheckForAdd`, one comparison wider — it must
**accept** `index == size` for append-by-position — message "Index: N,
Size: N". `getFirst()` on empty has no position to name at all, so it throws
`NoSuchElementException` instead. File 06 walks both bounds checks.

**What they are really testing.** Whether "same class, same list, same
argument value 3" is mistaken for "same bounds check" — `add` and `get`
disagree on whether `index == size` is legal.

### P3. `ensureCapacity` that changes nothing, right next to one that works

```java
import java.lang.reflect.Field;

Field ed = ArrayList.class.getDeclaredField("elementData");
ed.setAccessible(true);   // run with --add-opens java.base/java.util=ALL-UNNAMED

List<Restriction> a = new ArrayList<>();
a.ensureCapacity(5);
System.out.println(((Object[]) ed.get(a)).length);

List<Restriction> b = new ArrayList<>();
b.ensureCapacity(11);
System.out.println(((Object[]) ed.get(b)).length);
```

**Predict the output before reading on.**

**What it prints**

```
0
11
```

**Why.** `ensureCapacity`'s guard is `minCapacity > elementData.length &&
!(elementData == DEFAULTCAPACITY_EMPTY_ELEMENTDATA && minCapacity <=
DEFAULT_CAPACITY)`. On a fresh default list the sentinel matches and `5 <=
10`, so the guard is false and `grow` never runs — the list gets capacity 10
on its first real `add` anyway. `11 > 10` fails that clause, so `grow(11)`
runs and lands exactly on 11. Either list, filled one `add` at a time from
empty, still walks the same default sequence: **0 → 10 → 15 → 22 → 33 → 49 →
73 → 109 → 163 → 244**. File 05 derives the guard from the sentinel check.

**What they are really testing.** Whether "ensureCapacity" is read as an
unconditional pre-sizing hint rather than a guarded call that can be a
deliberate no-op.

### P4. `reversed().add` that never touches the reversed view

```java
List<String> instrumentIds = new ArrayList<>(List.of("AA-610", "AA-620", "AA-630"));
List<String> flipped = instrumentIds.reversed();

flipped.add("AA-999");

System.out.println(instrumentIds);
System.out.println(flipped.getClass().getName());
```

**Predict the output before reading on.**

**What it prints**

```
[AA-999, AA-610, AA-620, AA-630]
java.util.ReverseOrderListView$Rand
```

**Why.** `reversed()` is the one `SequencedCollection` member `ArrayList`
does not override — a live, write-through view, not a copy. `add` behaves
like `addLast` on the *view's own* frame, which maps to `add(0, ...)` on the
backing list — the "append" lands at the **start** of `instrumentIds`. File
03 names `reversed()` as the lone unoverridden member.

**What they are really testing.** Whether "reversed view" is assumed to mean
"a reversed copy" — it's a window with its own front and back mapped onto
the original's back and front, and mutating through it mutates the original.

### P5. `set` that mutates your own array, `add` that refuses to

```java
String[] instrumentIds = {"AA-610", "AA-620"};
List<String> wrapped = Arrays.asList(instrumentIds);

wrapped.set(0, "AA-611");
System.out.println(Arrays.toString(instrumentIds));

try {
    wrapped.add("AA-630");
} catch (UnsupportedOperationException e) {
    System.out.println(e.getClass().getName());
}
```

**Predict the output before reading on.**

**What it prints**

```
[AA-611, AA-620]
java.lang.UnsupportedOperationException
```

**Why.** `Arrays.asList(arr)`'s runtime class is `java.util.Arrays$ArrayList`
— a thin wrapper directly over the caller's own array, not a copy. `set`
writes straight into that array; `add`/`remove` would need to change the
array's length, which the wrapper refuses by throwing
`UnsupportedOperationException`. Files 02 and 04 flag this as fixed-size,
not immutable — the test is exactly whether `set` succeeds.

**What they are really testing.** Whether "immutable" and "fixed-size" are
conflated — `Arrays.asList` is the JDK's own counter-example that they are
not the same guarantee.

### P6. Three ways to hand a list a `null`, two different answers

```java
try {
    List.of("AA-700", null);
} catch (NullPointerException e) {
    System.out.println(e.getClass().getName());
}

List<String> mutable = new ArrayList<>();
mutable.add("AA-700");
mutable.add(null);
System.out.println(mutable);

List<String> viaStream = Stream.of("AA-700", null).toList();
System.out.println(viaStream);
System.out.println(viaStream.getClass().getName());
```

**Predict the output before reading on.**

**What it prints**

```
java.lang.NullPointerException
[AA-700, null]
[AA-700, null]
java.util.ImmutableCollections$ListN
```

**Why.** `List.of(...)` rejects `null` at construction, so "absent" can
never be confused with "present and null" — the factory call itself throws.
`ArrayList` places no restriction on `null` anywhere in `add`.
`Stream.of(...).toList()` is a separate factory — it does **not** reject
`null`, despite returning the same `ImmutableCollections$ListN` class
`List.of` would; immutability and null-rejection are independent
properties. File 01 covers the first two.

**What they are really testing.** Whether "immutable factories reject null"
is over-generalised — `Stream.toList()` returns an immutable list perfectly
happy to hold a `null`.

### P7. Two collectors, one word apart, two different runtime classes

```java
List<String> approvedRunIds = new ArrayList<>(List.of("BR-9910", "BR-9911"));

List<String> a = approvedRunIds.stream().toList();
List<String> b = approvedRunIds.stream().collect(Collectors.toList());

System.out.println(a.getClass().getName());
System.out.println(b.getClass().getName());

try {
    a.add("BR-9912");
} catch (UnsupportedOperationException e) {
    System.out.println(e.getClass().getName());
}
b.add("BR-9912");
System.out.println(b);
```

**Predict the output before reading on.**

**What it prints**

```
java.util.ImmutableCollections$ListN
java.util.ArrayList
java.lang.UnsupportedOperationException
[BR-9910, BR-9911, BR-9912]
```

**Why.** `stream().toList()`, added in JDK 16, deliberately returns an
unmodifiable snapshot. `Collectors.toList()` predates it and has always
returned a genuinely mutable `java.util.ArrayList` — a fact about the
implementation, not a contractual guarantee, which is why code that
structurally needs `ArrayList` should call
`Collectors.toCollection(ArrayList::new)` instead. File 13 names this a
JDK-16 delta.

**What they are really testing.** Whether the two calls are assumed
interchangeable because they read as "give me a `List` from this stream" —
one throws on the very next line the other accepts.

### P8. One source line, four JDKs, two different answers

```java
String[] instrumentIds = {"AA-610", "AA-620"};
Object[] viaAsList = Arrays.asList(instrumentIds).toArray();
viaAsList[0] = Integer.valueOf(7);
```

**Predict the output before reading on — but pick your JDK first.**

**What it prints**

| JDK | `viaAsList.getClass()` | The store `viaAsList[0] = Integer.valueOf(7)` |
|---|---|---|
| **1.8.0_202** | `[Ljava.lang.String;` | `java.lang.ArrayStoreException: java.lang.Integer` |
| **11.0.27** | `[Ljava.lang.Object;` | succeeds |
| **17.0.15** | `[Ljava.lang.Object;` | succeeds |
| **21.0.7** | `[Ljava.lang.Object;` | succeeds |

**Why.** `Arrays$ArrayList.toArray()` was `return a.clone();` on JDK 8,
preserving the array's exact covariant component type — a `clone()` of a
`String[]` is still a `String[]`, and the array-store check refuses to store
an `Integer` into it. JDK-6260652 changed the body, from JDK 9, to
`Arrays.copyOf(a, a.length, Object[].class)`, sanitising the component type
— the store succeeds on every later JDK. File 15 walks the mechanism; file
13 carries this as the fourth stale claim.

**What they are really testing.** Whether a candidate treats
`Arrays.asList(arr).toArray()`'s behaviour as a language fact rather than a
version-specific implementation detail — one line of source, two correct
answers depending on the JDK.

---

## Pitfalls

### "I got the puzzle's output right, so I understand the mechanism"

**Wrong.** Memorising "removing the second-to-last element in a for-each is
safe" and applying that to a five-element list at the same absolute index —
it still throws, because "second-to-last" is relative to *that* list's
current `size`, not a fixed index.

**Right.** Re-derive the arithmetic every time: after `next()` returns index
`i`, `cursor == i + 1`; removal drops `size` by one. The loop escapes the
exception exactly when `i + 1 == size - 1` after removal.

**Why people believe it:** the puzzle's answer is one memorable fact, and
memorable facts get generalised past the exact condition that makes them
true.

### "The puzzle's exception name is the whole answer"

**Wrong.** Answering P8 with "`ArrayStoreException`" and stopping, without
naming which JDK produces it.

**Right.** Every version-sensitive fact here is only half the answer without
naming which JDK it holds for — "true on 8, false since 9" is more valuable
than either half alone.

**Why people believe it:** most JDK behaviour is stable across versions, so
answering with no version qualifier is right almost everywhere except the
handful of places — like this one — where it matters.

## Cheat sheet

| Puzzle | The one-line mechanism |
|---|---|
| P1 | `hasNext()` is `cursor != size`, no `modCount` check — the escape depends on which index was removed |
| P2 | `checkIndex` rejects `index==size`; `rangeCheckForAdd` must accept it — two checks, two messages |
| P3 | `ensureCapacity`'s guard no-ops when the sentinel is default-capacity and the request is `<= 10` |
| P4 | `reversed()` is a live view; its front is the original's back, so `add` there is `add(0, …)` on the root |
| P5 | `Arrays.asList` wraps your array directly — `set` writes through, `add`/`remove` can't resize it |
| P6 | `List.of` rejects `null` at construction; `ArrayList` and `Stream.toList()` both accept it |
| P7 | `stream().toList()` is immutable (JDK 16+); `Collectors.toList()` is mutable, by convention not contract |
| P8 | `Arrays$ArrayList.toArray()`: covariant `clone()` on JDK 8, sanitising `copyOf(..., Object[].class)` from JDK 9 |

## Self-test

**Q1.** In P1, would a five-element list with the same *relative* removal
(index 3 of 5, the actual second-to-last) still stay silent?

<details><summary>Answer</summary>

Yes — the rule is never "index 2" or "four elements," it is "does the
post-removal `cursor` equal the post-removal `size`." For five elements that
condition holds at index 3, not index 2.

</details>

**Q2.** Name a JDK-supplied `List<String>` where `.add(null)` throws
`NullPointerException`, and one where it simply succeeds.

<details><summary>Answer</summary>

Neither `List.of(...)` nor `Arrays.asList(arr)` gets that far — `add` is
unsupported on both regardless of the argument. `new ArrayList<>().add(null)`
simply succeeds.

</details>

**Q3.** P7's `b.add(...)` succeeds. Six months later the same line starts
throwing `UnsupportedOperationException`, though `Collectors.toList()`'s
return type never changed. What's the likely cause?

<details><summary>Answer</summary>

The upstream call was refactored to `.toList()`, or `b`'s source became an
immutable list upstream — not a JDK behaviour change, since
`Collectors.toList()`'s current mutability has been stable, only ever
unguaranteed.

</details>

**Q4.** Which single JDK transition explains why JDK 11, 17, and 21 all
agree in P8's table?

<details><summary>Answer</summary>

JDK 9, JDK-6260652: `Arrays$ArrayList.toArray()`'s body changed from
`a.clone()` to `Arrays.copyOf(a, a.length, Object[].class)`.

</details>

**Q5.** A candidate says P2's two exceptions carry the same message "since
it's the same class." Disprove that without running code.

<details><summary>Answer</summary>

`get`/`set`/`remove(int)` use `Objects.checkIndex(index, size)`, which
rejects `index == size`; `add(int, E)` uses `rangeCheckForAdd`, which must
accept `index == size` for append-by-position. Different acceptance rules
cannot share one message.

</details>

---

## Atomic concept checklist

- [ ] States the positional contract: stable index 0 to `size()-1`, insertion order (01)
- [ ] States all four non-guarantees and the opt-in mechanism for each (01)
- [ ] States `ArrayList`'s null policy versus `List.of`'s rejection and `HashMap`'s one-null-key rule (01)
- [ ] States that `get(0)` on empty throws `IndexOutOfBoundsException` but `getFirst()` throws `NoSuchElementException` (01)
- [ ] States that `size()` is contractual and capacity is not, with no accessor for the latter (01)
- [ ] Names the interface spine in order: `Iterable → Collection → SequencedCollection → List` (02)
- [ ] Names the abstract-class spine: `AbstractCollection → AbstractList → ArrayList` (02)
- [ ] Names what survives unoverridden from `AbstractList` (`modCount`, `subListRangeCheck`, `SubList`) and `AbstractCollection` (`containsAll`, `toString`) (02)
- [ ] States that `RandomAccess` has zero members and is a performance promise, not behavioural (02)
- [ ] Names at least four named JDK consumers that branch on `instanceof RandomAccess`, and three `RandomAccess` types that are not `ArrayList` (02)
- [ ] States the one-sentence distinguishing job of each of the six `ArrayList` siblings (02)
- [ ] States that `containsAll` is O(n·m) on an `ArrayList` receiver and names the fix (02, 03)
- [ ] States the member-lineage rule: a call resolves to whichever rung last supplied a body (03)
- [ ] Names the two `ArrayList` methods with no ancestor to override: `trimToSize`, `ensureCapacity` (03)
- [ ] States that `reversed()` is the one `SequencedCollection` member `ArrayList` doesn't override, and its class (02, 03, 04)
- [ ] States that `addFirst`/`removeFirst` are O(n) despite their `Deque`-like names, while `removeLast` is O(1) (03, 05, 06)
- [ ] Defines "optional operation" and names where `UnsupportedOperationException` is declared to come from (03)
- [ ] Lists the nine call-site expressions typed `List<X>` and which five hand back a real mutable `ArrayList` (04)
- [ ] States the three constructors' capacities: `()` → 0→10, `(int)` → exactly n, `(Collection)` → `c.size()` (04)
- [ ] States the collection constructor's exact-class test and why `==`, not `instanceof` (04)
- [ ] States that an empty source in the collection constructor lands on `EMPTY_ELEMENTDATA`, not the default sentinel (04)
- [ ] States that `Collectors.toList()`'s mutability is an implementation fact, not a contract, and names the guaranteed alternative (04)
- [ ] States that `clone()`/deserialization bypass all constructors, allocate shrink-to-fit at `size` (04)
- [ ] Names the three fields and declaring types: `elementData`/`size` (ArrayList), `modCount` (AbstractList) (05)
- [ ] States that capacity is `elementData.length` with no field or accessor of its own (01, 05)
- [ ] Names both empty sentinels, that they are value-equal but identity-distinct, the two `==`/`!=` read sites, and why the split exists (05)
- [ ] States the growth formula `oldCapacity + (oldCapacity >> 1)` and that it has never been 2× (05, 13)
- [ ] States what `Math.max(minGrowth, prefGrowth)` rescues, and at which capacities (05)
- [ ] States that `addAll` resizes to exactly `size + numNew` with zero headroom, and recites the default sequence 0→10→15→22→33→49→73→109→163→244 (05, 09)
- [ ] States that `SOFT_MAX_ARRAY_LENGTH` caps speculative growth only, and the real ceiling is `Integer.MAX_VALUE` (05)
- [ ] States that `trimToSize()`/`ensureCapacity()` can each bump `modCount` with zero element change (05)
- [ ] States why `add(E)` splits into a public one-liner and a private helper, naming `MaxInlineSize` (06, 10)
- [ ] States that `add(int, E)` is one `System.arraycopy` widening a gap, cost `O(size - index)` (06)
- [ ] States the two-jobs-one-statement fact about `es[size = newSize] = null`, and the GC consequence of omitting it (06)
- [ ] States that `remove(Object)` uses the argument's `equals`, not the element's (06)
- [ ] Names the two out-of-bounds message shapes and which check produces each (06)
- [ ] States why `add(int, E)` must accept `index == size` while `get`/`set`/`remove(int)` must reject it, and that `set` never bumps `modCount` (06)
- [ ] Describes `removeIf`'s two-pass design and the reason the JDK gives for it (07)
- [ ] States the `deathRow` bitset's per-candidate cost, one bit per candidate (07)
- [ ] States that `removeAll`/`retainAll` share one engine, `batchRemove`, differing by one flag (07)
- [ ] States the cost asymmetry of `removeAll(aList)` vs `removeAll(aSet)` and what `batchRemove`'s `catch`/`finally` repairs when `contains` throws (07, 10)
- [ ] States that `sort` runs TimSort on the backing array with no defensive copy, bumping `modCount` (07)
- [ ] States `Itr`'s three fields and that `hasNext()` is `cursor != size` with no `modCount` check (08)
- [ ] States that `Iterator.remove()`/`ListIterator.add()` resync `expectedModCount` (08)
- [ ] States that `Itr.forEachRemaining` checks `modCount` once, at the end (08)
- [ ] States that `SubList` copies no elements, re-derives `offset + index`, and desyncs under a root mutation (08)
- [ ] States that `SubList`'s runtime class is not `ArrayList` and not `Serializable` (08)
- [ ] States why the for-each loop is fail-fast and an index loop is not (02, 08)
- [ ] States that `ArrayListSpliterator`'s fence is lazily initialised, and that `trySplit` copies no elements (09)
- [ ] States the spliterator characteristics `ORDERED|SIZED|SUBSIZED` = 16464 and why `LinkedList` lacks two (03, 09, 11)
- [ ] States that `elementData` is `transient`, serialization writes `size` elements only, and the "capacity" int in the stream is `size` again, discarded on read (05, 09)
- [ ] Names at least six operations from the full cost table with complexity and named cause, including that `remove(Object)` is two O(n) walks (06, 10)
- [ ] Cites the measured for-each gap (~3.2×) and the `get(i)` gap (~3500×) versus `LinkedList` (02, 10, 11)
- [ ] States the amortised copy bound `f/(f-1)` at f=1.5 and f=2.0 (05, 10)
- [ ] States when `ArrayDeque` wins over `ArrayList`/`LinkedList`, and the one case `LinkedList` genuinely wins (02, 11)
- [ ] States why `CopyOnWriteArrayList` fits read-mostly listener lists and nothing write-heavy (02, 11)
- [ ] Names the failure modes: unbounded accumulation as OOM, the retained-capacity leak, and undefined behaviour under concurrent mutation (01, 12)
- [ ] States the "view that outlives its root" failure and connects it to `SubList`/`reversed()` (08, 12)
- [ ] Names at least three of the seven cross-JDK deltas with their JDK numbers (05, 13)
- [ ] States and refutes all four stale claims: doubling, `MAX_ARRAY_SIZE`, ten wasted slots, `toArray` covariance (05, 13)
- [ ] States the specified `List.equals`/`hashCode` algorithm and that an `ArrayList` can equal a `LinkedList` (01, 14)
- [ ] States that `equals`/`hashCode` snapshot and recheck `modCount`, and can throw CME (14)
- [ ] States what `list.sort(comparator)` actually runs and why it needs no defensive copy (07, 14)
- [ ] States `Comparator` composition (`comparing`/`thenComparing`/`reversed`) and why `a - b` is wrong (14)
- [ ] States that `toArray()` always returns `Object[]`, and what `toArray(T[])` does depending on `a.length` (10, 15)
- [ ] States the array covariance/store-check mechanism, the exact JDK transition behind it, and one erasure consequence in `ArrayList`'s own source (15)
- [ ] Names at least one thing that does not survive an `ArrayList`'s serialization round trip (09, 15)
- [ ] States the three-way distinction between fixed-size, immutable, and mutable view, with one type each (02, 04, 15)
- [ ] States what a from-scratch minimal `ArrayList` needs to implement to be correct, and cites one measured number from file 16 (16)
- [ ] States that a `List<X>`-typed reference guarantees nothing about mutability — only the runtime class decides (02, 03, 04)

---

**Questions answered:** Q-47, Q-48
**Sets up:** Next: nothing — this is the last file. Re-read path is in the map.
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 514
