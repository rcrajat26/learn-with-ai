# `ArrayList` — 09 Internals: spliterator and serialization

**Target version: Java 21 LTS.** | [Map](00-map.md)
Assumes: Itr's cursor/modCount protocol and the view structure (file 08).
Previous: [08 Iteration, fail-fast and views](08-iteration-fail-fast-and-views.md) · Next: [10 Cost and memory](10-cost-and-memory.md)

## The map before the streets

Two machines share this file because both read `elementData` outside the
public API, behind a capability used constantly without anyone looking
underneath: `stream()`, and `ObjectOutputStream.writeObject(list)`.

| Machine | Entry point | What it bypasses |
|---|---|---|
| `ArrayListSpliterator` | `spliterator()`, `stream()`, `parallelStream()` | `Iterator`'s inability to split; walks `elementData`/`size`/`modCount` by index |
| `writeObject`/`readObject` | Java serialization | `elementData`'s `transient` declaration, which would otherwise skip it entirely |

Q-23 is the first machine; Q-25 is the second.

## `ArrayListSpliterator`

A `Spliterator` is a cursor over `[lo, hi)` that knows how to cut itself in
half — arithmetic on two `int`s, not a copy: an `ArrayListSpliterator` is
just `index`, `fence`, `expectedModCount`, and splitting hands the caller a
new object owning `[lo, mid)` while the original keeps `[mid, hi)`. It
exists because `Itr` (file 08) cannot be split — `hasNext()`/`next()` gives
no way to hand half the work to another thread; `Spliterator`, added in
Java 8 for streams, is built to be split, sized, and driven by a fork-join
pool. It applies wherever storage is index-addressable with a known size up
front — `ArrayList`'s situation — and stops paying off where there is no
O(1) way to find a midpoint, `LinkedList`'s situation (see Characteristics).

The lazy fence is the design:

```java
public Spliterator<E> spliterator() {
    return new ArrayListSpliterator(0, -1, 0);
}

final class ArrayListSpliterator implements Spliterator<E> {
    private int index; // current index, modified on advance/split
    private int fence; // -1 until used; then one past last index
    private int expectedModCount; // initialized when fence set

    private int getFence() { // initialize fence to size on first use
        int hi;
        if ((hi = fence) < 0) { expectedModCount = modCount; hi = fence = size; }
        return hi;
    }
```

`spliterator()` builds with `fence = -1` — uninitialised. `getFence()` is
where `fence = size` and `expectedModCount = modCount` are actually
assigned, the **first** time anyone asks. The class's 30-line design comment
states why: to "lazily initialize fence and expectedModCount until the
latest point that we need to commit to the state we are checking against;
thus improving precision." Building a spliterator over a `List<LedgerEntry>`
batch, adding one more entry, then traversing, is legal and sees the extra
entry — the snapshot commits at first traversal, not at `spliterator()`.
Contrast `Itr`'s immediate, constructor-time snapshot (file 08). **Insight:**
lazy does not mean "no guarantee" — the commit point moves to first use,
which suits an object routinely built and handed off before anyone
traverses it. `trySplit` itself is one allocation, two `int`s, zero copies:

```java
public ArrayListSpliterator trySplit() {
    int hi = getFence(), lo = index, mid = (lo + hi) >>> 1;
    return (lo >= mid) ? null : // divide range in half unless too small
        new ArrayListSpliterator(lo, index = mid, expectedModCount);
}
```

`mid = (lo + hi) >>> 1` uses an **unsigned** shift, overflow-safe against the
sign flip a plain `/2` would suffer on overflow. `index = mid` **mutates the
receiver in place**, shrinking it to `[mid, hi)`; the **returned** object
covers `[lo, mid)` — the half just carved off. `null` comes back when
`lo >= mid`: the "too small to split further" signal fork-join needs to stop
recursing.

![Splitting moves two ints. The array is never copied, which is why `ArrayList` parallelises well and `LinkedList` does not.](diagrams/D-12-spliterator-trysplit.svg)

No element is read, copied, or boxed during a split — only the two
spliterators' `index`/`fence` fields differ, over one shared backing array,
which is the whole reason splitting an `ArrayList` is cheap: preparing work
for N threads is O(log N) small allocations, not O(size). **Measured:** on
a 4-element list, `estimateSize()` reports 4; after one `trySplit()`, both
halves report 2.

**`forEachRemaining` — exactly one check, at the end.**

```java
public void forEachRemaining(Consumer<? super E> action) {
    int i, hi, mc; Object[] a;
    if (action == null) throw new NullPointerException();
    if ((a = elementData) != null) {
        if ((hi = fence) < 0) { mc = modCount; hi = size; } else mc = expectedModCount;
        if ((i = index) >= 0 && (index = hi) <= a.length) {
            for (; i < hi; ++i) {
                @SuppressWarnings("unchecked") E e = (E) a[i];
                action.accept(e);
            }
            if (modCount == mc) return;
        }
    }
    throw new ConcurrentModificationException();
}
```

The design comment names this method's role directly: it performs "only a
single `ConcurrentModificationException` check at the end of forEach (the
most performance-sensitive method)... in the common case of
`list.stream().forEach(a)`, no checks or other computation occur anywhere
other than inside forEach itself." Contrast `tryAdvance`, which checks
`modCount != expectedModCount` **after every element**, since it returns
control to the caller between elements and a mutation could land in the gap
— **the less-used path pays a per-element tax the hot path does not.** This
is the same `modCount`/`expectedModCount` comparison `Itr` uses (file 08);
only *when* it runs differs. `ArrayList.forEach(Consumer)` itself, reachable
directly without a spliterator, checks in its **loop condition** every
iteration instead — a third check cadence on the same class.

```java
public int characteristics() {
    return Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED;
}
```

**Measured on JDK 21.0.7:** exactly **16464** == `ORDERED | SIZED | SUBSIZED`.

| Flag | Asserts | Buys |
|---|---|---|
| `ORDERED` | Encounter order (array index order) is meaningful | `findFirst`/`limit`/`skip` are well-defined; parallel `forEachOrdered` must reassemble in this order |
| `SIZED` | `estimateSize()` is exact, not an estimate | Fork-join computes a real split threshold up front instead of probing |
| `SUBSIZED` | Every split child is also `SIZED` | Exactness survives recursive splitting |

Absent, and worth naming: no `IMMUTABLE`, `CONCURRENT`, `NONNULL`
(`ArrayList` allows `null`), `DISTINCT`, or `SORTED`. `LinkedList`'s
spliterator has **neither** `SIZED` nor `SUBSIZED` — its `estimateSize()`
cannot be exact without walking nodes, and a split cannot promise its half
is sized either. **Interview:** that is the concrete, mechanical reason a
parallel stream over a `LinkedList` is a bad trade — not "linked lists are
slow" but "it reports neither flag, so fork-join loses its sizing signal on
top of having no O(1) midpoint to split on."

`Collection.stream()`, a default `ArrayList` does **not** override, is
`StreamSupport.stream(spliterator(), false)` — every `stream()`/
`parallelStream()` pipeline runs on exactly this spliterator, which is why
`findFirst()` means "first in index order," not "whichever thread finished
first." **Cost and escape hatch:** splitting is cheap to *set up*, but
fork-join submission and result joining are real overhead, and a stream
over a few thousand cheap elements reliably loses to sequential — the
escape hatch is measuring actual per-element cost, not counting elements.

QuizStakes, walking the split tree over a settlement burst (Appendix A.2 —
settlements peak at **3 400/sec**, plausibly fanned out via fork-join):

```java
record LedgerEntry(String movementId, String position, String direction,
                    BigDecimal amount, Instant postedAt) {}

public final class SpliteratorWalk {
    public static void main(String[] args) {
        List<LedgerEntry> burst = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            burst.add(new LedgerEntry("MOV-" + i, "CASH_AVAILABLE",
                    i % 2 == 0 ? "CREDIT" : "DEBIT", new BigDecimal("4.20"), Instant.now()));
        }
        Spliterator<LedgerEntry> root = burst.spliterator();
        Spliterator<LedgerEntry> left = root.trySplit();
        System.out.println("characteristics=" + root.characteristics()
                + " left=" + left.estimateSize() + " right=" + root.estimateSize());
    }
}
```

```
characteristics=16464 left=2 right=2
```

> An `ArrayListSpliterator` is a lazily-fenced index range over `elementData`
> that splits by bisecting two integers, never copying elements, and reports
> `ORDERED | SIZED | SUBSIZED` so fork-join can plan its work without probing.

## Serialization

`ArrayList`'s most important field, `elementData`, is `transient` — normally
that means "skip entirely." `ArrayList` does not skip it; a custom
`writeObject`/`readObject` pair writes a hand-picked subset instead: not
"dump the fields" but "dump exactly the live elements, and rebuild a fresh
array sized to fit." Without `transient`, default serialization would write
the array's full **capacity**, unused trailing slots included, as nulls — a
list at capacity 1 000 000 holding 3 elements would serialize roughly a
million nulls. `transient` (file 01: `transient Object[] elementData;`)
suppresses that entirely; the custom methods write only what matters.

The wire format, read from the source — `@serialData` says exactly this:
"the length of the array backing the ArrayList instance is emitted (int),
followed by all of its elements... in the proper order."

```java
private void writeObject(java.io.ObjectOutputStream s) throws java.io.IOException {
    int expectedModCount = modCount;
    s.defaultWriteObject();
    s.writeInt(size); // "capacity", for behavioral compatibility with clone()
    for (int i = 0; i < size; i++) s.writeObject(elementData[i]);
    if (modCount != expectedModCount) throw new ConcurrentModificationException();
}
```

Four things go onto the stream: (1) `defaultWriteObject()` writes every
non-`transient` field — just `size`; (2) `s.writeInt(size)` writes `size`
**again**, labelled "capacity" purely for historical compatibility with
`clone()`'s allocation behaviour, the same value, not a second number; (3)
exactly `size` objects, `elementData[0..size-1]`, never the unused trailing
slots; (4) a `modCount` snapshot taken before step 1 is compared after step
3, throwing CME on mismatch — detection of a torn write, with no lock
anywhere in the method.

```java
private void readObject(java.io.ObjectInputStream s) throws java.io.IOException, ClassNotFoundException {
    s.defaultReadObject();
    s.readInt(); // ignored
    if (size > 0) {
        SharedSecrets.getJavaObjectInputStreamAccess().checkArray(s, Object[].class, size);
        Object[] elements = new Object[size]; // like clone(): sized to size, not capacity
        for (int i = 0; i < size; i++) elements[i] = s.readObject();
        elementData = elements;
    } else if (size == 0) {
        elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new java.io.InvalidObjectException("Invalid size: " + size);
    }
}
```

`s.readInt()` reads the "capacity" int back and discards it (`// ignored`).
**A deserialized list therefore has capacity exactly `size` — zero slack** —
the same discipline `clone()` uses; the very next `add()` pays a `grow()`
call. `checkArray(s, Object[].class, size)` runs **before** the allocation,
enforcing any `jdk.serialFilter` limit — a hostile stream claiming
`size == Integer.MAX_VALUE` cannot force a huge allocation before any
element arrives. A negative `size` throws `InvalidObjectException`;
`size == 0` resolves to the shared `EMPTY_ELEMENTDATA` sentinel (file 04).
`serialVersionUID = 8683452581122892189L`, unchanged since 1.2, is why a
JDK 21 reader accepts a stream a 1.2 writer produced decades ago — the JVM
compares this field, not the class's shape, buying long-term compatibility
at the cost of any freedom to casually change the format.

`ArrayList$SubList` (file 08) extends `AbstractList` and is not
`Serializable` — serializing `list.subList(a, b)` throws
`NotSerializableException: java.util.ArrayList$SubList` (file 15 owns the
fuller interoperation-hazard set). A non-`Serializable` element surfaces the
same exception naming the **element's** class, not `ArrayList`'s — a list
is only as serializable as what is in it.

QuizStakes: `PaymentRun.itemIds: List<Id>` (Appendix C.2), collected once a
run reaches `SENT_TO_BANK` (§13.2), sized to the **1 800-record** bank payout
file (Appendix A.5). Reflecting on the backing array's length before and
after a round trip proves capacity comes back as exactly `size`:

```java
public final class PaymentRunSerializationDemo {
    private static int backingCapacity(ArrayList<?> list) throws Exception {
        Field f = ArrayList.class.getDeclaredField("elementData");
        f.setAccessible(true);
        return ((Object[]) f.get(list)).length;
    }

    public static void main(String[] args) throws Exception {
        ArrayList<UUID> itemIds = new ArrayList<>(2000); // over-allocated, run under construction
        for (int i = 0; i < 1800; i++) itemIds.add(UUID.randomUUID());

        var bytes = new ByteArrayOutputStream();
        try (var out = new ObjectOutputStream(bytes)) { out.writeObject(itemIds); }
        ArrayList<UUID> restored;
        try (var in = new ObjectInputStream(new ByteArrayInputStream(bytes.toByteArray()))) {
            @SuppressWarnings("unchecked") var read = (ArrayList<UUID>) in.readObject();
            restored = read;
        }
        System.out.println("before=" + backingCapacity(itemIds) + " after=" + backingCapacity(restored));
    }
}
```

```
before=2000 after=1800
```

> `ArrayList` serialization writes `size` and exactly `size` live elements
> through a custom `writeObject`/`readObject` pair that bypasses the
> `transient` backing array entirely, and reconstructs capacity at exactly
> `size` — never the original headroom.

## Pitfalls

### Assuming serialized size tells you the original capacity

**Wrong:** treating `restored.ensureCapacity(5000)` as redundant after a
round trip, on the belief that serialization preserves capacity. It does
not — `restored`'s capacity is exactly its `size` without that call.

**Right:** treat capacity as never part of the serialized contract; call
`ensureCapacity` explicitly after deserializing if headroom is needed.

**Why people believe it:** the wire format contains a field the source
comments "capacity" — reading that without `readObject`'s next line
(`s.readInt(); // ignored`) leaves the impression the number is used.

### Believing a mid-traversal mutation from another thread always throws

**Wrong:** mutating a shared `ArrayList` from one thread while
`parallelStream().forEach(...)` reads it on another, on the belief that a
CME reliably surfaces the race. Depending on interleaving it throws from an
unpredictable split-tree fragment, or completes silently with an
inconsistent view if the mutation lands before some sub-spliterator commits
its fence.

**Right:** never mutate an `ArrayList` while any stream reads it elsewhere;
snapshot with `List.copyOf(shared)` first, or synchronize externally.

**Why people believe it:** `Itr`'s CME (file 08) feels reliable because its
snapshot happens once, at construction; `ArrayListSpliterator`'s fences are
distributed across however many pieces `trySplit` produced, each
committing independently.

## Cheat sheet

| Fact | Value / behaviour |
|---|---|
| Fence/`expectedModCount` committed | On first `getFence()` call, not construction |
| `trySplit()` cost / split point | One allocation, two `int`s; `mid = (lo + hi) >>> 1`, unsigned |
| `trySplit()` returns `null` when | `lo >= mid` — too small to split |
| `characteristics()` | `16464` = `ORDERED \| SIZED \| SUBSIZED` (measured) |
| `LinkedList` spliterator has | Neither `SIZED` nor `SUBSIZED` |
| CME check frequency | `forEachRemaining` once at end; `tryAdvance` every element; `ArrayList.forEach` every loop iteration |
| `stream()` implementation | `StreamSupport.stream(spliterator(), false)` |
| Serialized via `defaultWriteObject` | `size` only — `elementData` is `transient` |
| Extra int in `writeObject` | `size` again, labelled "capacity," discarded by `readObject` |
| Capacity after deserialization | Exactly `size` — zero slack, like `clone()` |
| `writeObject`/`readObject` guards | `modCount` compare (CME on mismatch); `checkArray(...)` before allocating |
| `serialVersionUID` | `8683452581122892189L`, unchanged since Java 1.2 |
| `ArrayList$SubList` serializable? | No — `NotSerializableException` |

## Self-test

**Q1.** Why does `spliterator()` construct with `fence = -1` instead of `size` directly?

<details><summary>Answer</summary>

To defer the `modCount`/size snapshot to first traversal or split rather
than fixing it at construction — `getFence()` is the only place `fence` and
`expectedModCount` get real values, so a caller can build the spliterator,
mutate the list, and still traverse correctly against state at traversal time.

</details>

**Q2.** Decode `16464` and state what each flag buys the fork-join framework.

<details><summary>Answer</summary>

`ORDERED | SIZED | SUBSIZED`. `ORDERED` makes `findFirst`/`limit`/`skip`
well-defined; `SIZED` lets fork-join compute a real split threshold up
front; `SUBSIZED` guarantees every split child is also `SIZED`.

</details>

**Q3.** Why does `forEachRemaining` check `modCount` once while `tryAdvance` checks every element?

<details><summary>Answer</summary>

`forEachRemaining` owns the whole remaining range for one call, so nothing
can interleave a mutation between elements — one check at the end suffices.
`tryAdvance` returns control between elements, so it must check every time
to stay fail-fast.

</details>

**Q4.** Why is `elementData` `transient`, and what does `writeObject` write in its place?

<details><summary>Answer</summary>

Default serialization would otherwise write the whole backing array,
unused trailing slots as nulls included — a capacity-1,000,000 list holding
3 elements would write roughly a million nulls. The custom `writeObject`
writes `size`, `size` again labelled "capacity," then exactly `size` elements.

</details>

**Q5.** What capacity does a deserialized `ArrayList` have, and why does `checkArray` matter?

<details><summary>Answer</summary>

Exactly `size` — zero slack — because `readObject` allocates
`new Object[size]`, discarding the "capacity" int it read. `checkArray`
runs before that allocation and enforces any `jdk.serialFilter` limit, so
a hostile stream claiming an enormous `size` cannot force a huge allocation
before any element arrives.

</details>

---

**Questions answered:** Q-23, Q-25
**Sets up:** Next: what all of this costs — in nanoseconds, in bytes, and in the latency one unlucky request pays.
**Diagrams included:** D-12
**Target version:** Java 21 LTS
**Lines:** 407
