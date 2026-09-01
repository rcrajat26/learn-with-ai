# 02 Java Collections — Immutability and views — INTERNALS (§3.12.15–3.12.16)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/04c-internals-mutators-serialization-and-views.md](04c-internals-mutators-serialization-and-views.md) · Next: [immutable-collections/04e-internals-layout-and-legacy-factories.md](04e-internals-layout-and-legacy-factories.md)

This file covers the two **views** an immutable list can hand out: `ImmutableCollections.SubList`
(3.12.15) and `ReverseOrderListView` (3.12.16, Java 21). The mutator wall and the `CollSer` serial
proxy they both sit on top of are in
[04c-internals-mutators-serialization-and-views.md](04c-internals-mutators-serialization-and-views.md).

Source citations are against JDK 21 `src.zip`: `java.base/java/util/` `ImmutableCollections.java`,
`ReverseOrderListView.java`, `List.java`, `LinkedHashMap.java`. Every transcript below is real output
from **JDK 21.0.7, HotSpot 64-Bit Server VM, aarch64 (macOS)**. Code snippets are shown without imports
or `main` scaffolding.

## The two views, side by side

Both are **stateless wrappers over a base list** that compute an index rather than copy data. That is
the whole family resemblance; everything else differs.

| | `ImmutableCollections.SubList` | `ReverseOrderListView` |
|---|---|---|
| Since | Java 9 | Java 21 (JEP 431) |
| Fields | `(root, offset, size)`, all `@Stable` | `(base, modifiable)` |
| Index map | `root.get(offset + i)` | `base.get(size - i - 1)` |
| Base type | always `List12` or `ListN`, never a `SubList` | any `List`, including a mutable one |
| Mutators | inherited from `AbstractImmutableList` → always throw | gated on `modifiable`; write through when `true` |
| Composes with itself | **flattens** into one object | **unwraps** — `reversed().reversed() == base` |
| `RandomAccess` | always | via the `Rand` subclass — but **lost** by `subList` |
| Serializable | no | no |

---

## `SubList`: root plus offset (3.12.15)

**Mental model.** Three fields and a pointer — a window frame nailed over the root list. Nothing is
copied.

**Why it exists.** `AbstractList.subList` returns a view that tracks `modCount` for
`ConcurrentModificationException` detection. An immutable root has no `modCount`, so
`ImmutableCollections` ships its own version with no version checking at all. Reach for
`List.copyOf(sub)` instead whenever the root is large and short-lived — see the retention pitfall.

**Mechanism.** `ImmutableCollections.java:265-270` on `AbstractImmutableList`:

```java
@Override
public List<E> subList(int fromIndex, int toIndex) {
    int size = size();
    subListRangeCheck(fromIndex, toIndex, size);
    return SubList.fromList(this, fromIndex, toIndex);
}
```

and lines 434-471:

```java
static final class SubList<E> extends AbstractImmutableList<E>
        implements RandomAccess {

    @Stable
    private final AbstractImmutableList<E> root;

    @Stable
    private final int offset;

    @Stable
    private final int size;

    private SubList(AbstractImmutableList<E> root, int offset, int size) {
        assert root instanceof List12 || root instanceof ListN;
        this.root = root;
        this.offset = offset;
        this.size = size;
    }

    static <E> SubList<E> fromSubList(SubList<E> parent, int fromIndex, int toIndex) {
        return new SubList<>(parent.root, parent.offset + fromIndex, toIndex - fromIndex);
    }

    static <E> SubList<E> fromList(AbstractImmutableList<E> list, int fromIndex, int toIndex) {
        return new SubList<>(list, fromIndex, toIndex - fromIndex);
    }

    public E get(int index) {
        Objects.checkIndex(index, size);
        return root.get(offset + index);
    }
}
```

- `@Stable` on all three fields lets HotSpot treat them as constants after first read, so `get(i)`
  folds to a single indexed load on the root array.
- The `assert` at line 447 pins the invariant: `root` is **always** a `List12` or `ListN`, never
  another `SubList`. `fromSubList` enforces it — a sublist of a sublist **flattens**, adding
  `parent.offset + fromIndex` rather than nesting. So `list.subList(2,6).subList(1,3)` is one `SubList`
  with `offset = 3`. Contrast `ArrayList`, where `SubList.subList` nests and each `get` walks a chain.
- `get` bounds-checks the window once, then `root.get(offset + index)`; the window itself was validated
  at construction.
- Extending `AbstractImmutableList` inherits **both mutator walls** (see
  [04c](04c-internals-mutators-serialization-and-views.md)), so it is fully immutable and
  `RandomAccess`. `allowNulls()` (lines 497-499) asks the root whether nulls are permitted, which is
  why `indexOf(null)` throws NPE on a sublist of `List.of(...)` but returns `-1` on a sublist of a
  `Stream.toList()` result.
- `SubList` does **not** implement `Serializable`, unlike `List12`/`ListN`. Verified below.

```java
List<Integer> root = List.of(0, 1, 2, 3, 4, 5, 6, 7);
List<Integer> s1 = root.subList(2, 6);
List<Integer> s2 = s1.subList(1, 3);
System.out.println("s1=" + s1 + " s2=" + s2 + " class=" + s1.getClass().getName()
        + " RandomAccess=" + (s1 instanceof RandomAccess));
try { s1.set(0, 99); } catch (RuntimeException e) { System.out.println("s1.set -> " + e.getClass().getSimpleName()); }
try { s1.indexOf(null); } catch (RuntimeException e) { System.out.println("s1.indexOf(null) -> " + e.getClass().getSimpleName()); }
```

Real output:

```
s1=[2, 3, 4, 5] s2=[3, 4] class=java.util.ImmutableCollections$SubList RandomAccess=true
s1.set -> UnsupportedOperationException
s1.indexOf(null) -> NullPointerException
```

**Pitfall — retention has exactly the shape of `ArrayList.subList`'s leak.** `SubList` holds a strong
reference to the whole root, so a one-element sublist of a million-element `List.of` keeps all million
alive. This is the same leak documented for the mutable case in
[01-views-copies-snapshots.md](01-views-copies-snapshots.md), and immutability does not help — it makes
the retention permanent rather than merely surprising. Same fix: `List.copyOf(sub)` to detach. What
immutability *does* remove is the other hazard: no `ConcurrentModificationException` is possible,
because there is no `modCount`.

> **Definition.** `ImmutableCollections.SubList` is a three-field `(root, offset, size)` immutable
> `RandomAccess` view that delegates `get(i)` to `root.get(offset + i)`, flattens nested `subList`
> calls into a single offset, and retains the entire root array.

---

## `ReverseOrderListView`: `List.reversed()` in Java 21 (3.12.16)

**Mental model.** An index mirror. Nothing is copied or reordered — `get(i)` becomes
`base.get(size - i - 1)`, and every iterator runs backwards over the base's `ListIterator`.

**Why it exists.** Before Java 21 there was no uniform way to walk a `List` backwards:
`Collections.reverse` mutated in place (and threw on an immutable list), and `descendingIterator`
existed only on `Deque`/`NavigableSet`. **JEP 431 (Sequenced Collections, Java 21)** added
`SequencedCollection` with `reversed()`, `addFirst`/`addLast`/`getFirst`/`getLast`/`removeFirst`/
`removeLast`, and made `List` extend it. `ReverseOrderListView` is the default implementation.

**When to reach for it.** Zero-copy backwards traversal, and `getFirst()`/`getLast()` without index
arithmetic. Not as a cheap "reverse this list": it is a *view*, so later writes to the base show
through, and repeated `get` on a non-`RandomAccess` base is O(n) per call. For an actual reversed
snapshot the sibling that wins is `list.reversed().stream().toList()`.

**Mechanism.** Two entry points — `List.java:903-905` (the interface default) and the immutable
override at `ImmutableCollections.java:334-337`:

```java
default List<E> reversed() {
    return ReverseOrderListView.of(this, true); // we must assume it's modifiable
}

// AbstractImmutableList
@Override
public List<E> reversed() {
    return ReverseOrderListView.of(this, false);
}
```

The second argument is the whole story. The factory, `ReverseOrderListView.java:45-64`:

```java
public static <T> List<T> of(List<T> list, boolean modifiable) {
    if (list instanceof ReverseOrderListView<T> rolv) {
        return rolv.base;
    } else if (list instanceof RandomAccess) {
        return new ReverseOrderListView.Rand<>(list, modifiable);
    } else {
        return new ReverseOrderListView<>(list, modifiable);
    }
}

static class Rand<E> extends ReverseOrderListView<E> implements RandomAccess {
    Rand(List<E> list, boolean modifiable) {
        super(list, modifiable);
    }
}

private ReverseOrderListView(List<E> list, boolean modifiable) {
    this.base = list;
    this.modifiable = modifiable;
}
```

- **The first branch answers the double-reverse question, and the answer is not the one `TreeMap`
  gives.** `of` unwraps, so for a `List` `list.reversed().reversed() == list` is **true** — for both a
  mutable and an immutable list. That matches `LinkedHashMap`, where `LinkedHashMap.java:1224` is
  literally `return base;`, and does **not** match `TreeMap.descendingMap().descendingMap() == t`,
  which is `false` because that path allocates a fresh wrapper instead of unwrapping. Verified below
  for both `new ArrayList<>(...)` and `List.of(...)`.
- The `RandomAccess` branch preserves the marker via the `Rand` subclass, so `List.of(...).reversed()`
  is `ReverseOrderListView$Rand` and still `RandomAccess`.
- `modifiable` is checked by `checkModifiable()`, `ReverseOrderListView.java:75-79`:

```java
void checkModifiable() {
    if (! modifiable) {
        throw new UnsupportedOperationException();
    }
}
```

**Insight:** every mutator calls `checkModifiable()` *first*. Over an immutable list `modifiable` is
`false`, so **the view throws on its own, before ever touching the base** — the base's own mutator wall
is never reached. The class comment at lines 66-73 explains why this is belt-and-braces: bulk ops
inherited from `AbstractList` might not throw when no actual mutation would occur (`addAll` of an empty
collection), so the view throws unconditionally to make the behaviour uniform regardless of base.

The index flip, `ReverseOrderListView.java:338-352`:

```java
public E get(int i) {
    int size = base.size();
    Objects.checkIndex(i, size);
    return base.get(size - i - 1);
}

public int indexOf(Object o) {
    int i = base.lastIndexOf(o);
    return i == -1 ? -1 : base.size() - i - 1;
}

public int lastIndexOf(Object o) {
    int i = base.indexOf(o);
    return i == -1 ? -1 : base.size() - i - 1;
}
```

`indexOf`/`lastIndexOf` swap, which is the general rule for the class. The neatest instance is `sort`
at lines 381-384: `base.sort(Collections.reverseOrder(c))` — sorting the view ascending is sorting the
base descending. And `add(E)` at lines 159-163 is `base.add(0, e)`: appending to the view's end is
inserting at the base's front.

```java
List<Integer> mut = new ArrayList<>(List.of(1, 2, 3));
List<Integer> rMut = mut.reversed();
System.out.println("ArrayList rev=" + rMut.getClass().getName()
        + " RandomAccess=" + (rMut instanceof RandomAccess) + " rev.reversed()==src " + (rMut.reversed() == mut));
List<Integer> src = List.of(1, 2, 3);
List<Integer> rImm = src.reversed();
System.out.println("List.of rev=" + rImm.getClass().getName() + " value=" + rImm
        + " rev.reversed()==src " + (src.reversed().reversed() == src));
for (var e : List.of(Map.entry("add", (Runnable) () -> rImm.add(9)),
                     Map.entry("set", (Runnable) () -> rImm.set(0, 9)),
                     Map.entry("sort", (Runnable) () -> rImm.sort(null)),
                     Map.entry("removeIf", (Runnable) () -> rImm.removeIf(x -> false)),
                     Map.entry("clear", (Runnable) rImm::clear))) {
    try { e.getValue().run(); System.out.println("rImm." + e.getKey() + " -> NO THROW"); }
    catch (RuntimeException ex) { System.out.println("rImm." + e.getKey() + " -> " + ex.getClass().getSimpleName()); }
}
List<Integer> linked = new LinkedList<>(List.of(1, 2, 3));
System.out.println("LinkedList rev=" + linked.reversed().getClass().getName()
        + " RandomAccess=" + (linked.reversed() instanceof RandomAccess));
List<Integer> subOfRev = rMut.subList(0, 2);
System.out.println("rev.subList=" + subOfRev.getClass().getName()
        + " RandomAccess=" + (subOfRev instanceof RandomAccess) + " value=" + subOfRev);
rMut.add(0);
System.out.println("after rev.add(0): source=" + mut);
```

Real output:

```
ArrayList rev=java.util.ReverseOrderListView$Rand RandomAccess=true rev.reversed()==src true
List.of rev=java.util.ReverseOrderListView$Rand value=[3, 2, 1] rev.reversed()==src true
rImm.add -> UnsupportedOperationException
rImm.set -> UnsupportedOperationException
rImm.sort -> UnsupportedOperationException
rImm.removeIf -> UnsupportedOperationException
rImm.clear -> UnsupportedOperationException
LinkedList rev=java.util.LinkedList$ReverseOrderLinkedListView RandomAccess=false
rev.subList=java.util.ReverseOrderListView RandomAccess=false value=[3, 2]
after rev.add(0): source=[0, 1, 2, 3]
```

- Double-reverse is identity for both a mutable and an immutable list, exactly as `List.java:891-893`
  promises: *"The `reversed()` method of the view returns a reference to this List."*
- `LinkedList` does **not** use `ReverseOrderListView` at all — it overrides `reversed()` with its own
  `LinkedList$ReverseOrderLinkedListView`, which is not `RandomAccess`. So "`reversed()` returns a
  `ReverseOrderListView`" is true of `ArrayList`, `List.of` and `Arrays.asList`, but not universally.
- **Pitfall:** `ReverseOrderListView.subList` (lines 393-397) calls the private constructor directly
  instead of the `of` factory, so **the `RandomAccess` marker is silently lost** even when the base has
  it. This is a genuine wart, not a documented choice.
- `rMut.add(0)` appends to the *view*, i.e. inserts at the **front of the source**, which becomes
  `[0, 1, 2, 3]`. A view mutator's orientation is the view's; the write lands in the base.

### Neither view is serializable

`List12`, `ListN`, `SetN`, `Map1` and `MapN` all serialize cleanly through the `CollSer` proxy
([04c](04c-internals-mutators-serialization-and-views.md)). Their views do not.

```java
for (Object v : new Object[]{ Map.of("k", 1).keySet(), List.of(1, 2, 3, 4).subList(1, 3),
                              List.of(1, 2, 3).reversed() }) {
    try {
        ser(v);
        System.out.println(v.getClass().getName() + " -> serialized");
    } catch (Exception e) {
        System.out.println(v.getClass().getName() + " -> " + e.getClass().getSimpleName());
    }
}
```

Real output:

```
java.util.AbstractMap$1                  -> NotSerializableException
java.util.ImmutableCollections$SubList   -> NotSerializableException
java.util.ReverseOrderListView$Rand      -> NotSerializableException
```

`SubList` simply does not declare `Serializable`. `ReverseOrderListView` says so in its own class
javadoc, `ReverseOrderListView.java:38`: *"Provides a reverse-ordered view of a List. Not
serializable."* And `Map.of(...).keySet()` is the anonymous `AbstractMap$1` inherited from
`AbstractMap`. The rule to remember: **the `CollSer` proxy covers the collection, not anything derived
from it.** Fix in all three cases is a defensive copy — `List.copyOf(sub)`, `Set.copyOf(keySet)`,
`view.stream().toList()`.

> **Definition.** `ReverseOrderListView` (Java 21, JEP 431) is the default `List.reversed()`
> implementation: a two-field `(base, modifiable)` wrapper that flips indices as
> `base.get(size - i - 1)`, unwraps on double-reverse so `list.reversed().reversed() == list`,
> preserves `RandomAccess` through the `Rand` subclass, and throws from every mutator when
> `modifiable` is `false` — which is what `AbstractImmutableList.reversed()` passes.

---

## Pitfalls

### Assuming the immutable `subList` is a copy because the list is immutable

**Wrong**

```java
List<byte[]> huge = List.copyOf(loadMillionBuffers());
List<byte[]> firstTwo = huge.subList(0, 2);
huge = null;                 // "the rest can be collected now"
```

Nothing is collected: `SubList` holds `root`, and `root` holds the full million-element array.

**Right**

```java
List<byte[]> firstTwo = List.copyOf(huge.subList(0, 2));   // detached, 2 elements retained
huge = null;
```

**Why people believe it:** immutability is filed mentally under "safe", and the `ArrayList.subList`
leak is usually taught as a consequence of *mutability* (`modCount`, write-through). It is not — it is
a consequence of *delegation*, which both share.

### Expecting `reversed().subList(...)` to stay `RandomAccess`

**Wrong**

```java
List<Integer> v = new ArrayList<>(List.of(1, 2, 3)).reversed();   // Rand, RandomAccess=true
System.out.println(v.subList(0, 2) instanceof RandomAccess);       // false
```

**Right**

```java
List<Integer> s = List.copyOf(v.subList(0, 2));   // ImmutableCollections$List12, RandomAccess=true
```

**Why people believe it:** `ReverseOrderListView.of` carefully preserves the marker via `Rand`, so it
is reasonable to assume `subList` does too. It calls the private constructor directly
(`ReverseOrderListView.java:396`) and skips the factory.

### Serializing a view because the collection it came from is serializable

**Wrong**

```java
try {
    oos.writeObject(List.of(1, 2, 3, 4).subList(1, 3));   // "List.of is Serializable, so..."
} catch (Exception e) {
    System.out.println(e.getClass().getSimpleName());     // NotSerializableException
}
```

**Right**

```java
oos.writeObject(List.copyOf(List.of(1, 2, 3, 4).subList(1, 3)));   // a real List12, goes via CollSer
```

**Why people believe it:** `List12`/`ListN` are `Serializable` and the view *is* a `List` with the same
`equals`. But `Serializable` is not inherited through delegation — `SubList` never declares it, and
`ReverseOrderListView.java:38` says outright it is not serializable. Same trap as
`Map.of(...).keySet()`, which is `AbstractMap$1`.

### Reading `view.add(x)` as "append to the source"

**Wrong**

```java
List<Integer> mut = new ArrayList<>(List.of(1, 2, 3));
mut.reversed().add(0);
System.out.println(mut);          // [0, 1, 2, 3] — NOT [1, 2, 3, 0]
```

**Right** — write through the orientation you actually mean:

```java
mut.add(0);                       // [1, 2, 3, 0]
mut.reversed().add(0);            // [0, 1, 2, 3]: appending to the view = prepending to the base
```

**Why people believe it:** the view looks like a separate list, so `add` looks like it should land at
the view's own end and nowhere else. `ReverseOrderListView.add(E)` is literally
`checkModifiable(); base.add(0, e);` (lines 159-163) — the write goes to the base, at the mirrored
position.

---

## Cheat sheet

| Thing | Fact |
|---|---|
| `SubList` fields | `(root, offset, size)`, all `@Stable`; HotSpot constant-folds them |
| `SubList.get(i)` | `root.get(offset + i)`, one bounds check, one delegation deep |
| Nested `subList` | **Flattens** — `fromSubList` adds `parent.offset + fromIndex` |
| `SubList` root invariant | `assert root instanceof List12 || root instanceof ListN` (`:447`) |
| `SubList` mutators | Inherited from `AbstractImmutableList` → all throw UOE |
| `SubList.indexOf(null)` | NPE over a `List.of` root; `-1` over a `Stream.toList()` root (`allowNulls()`) |
| `SubList` retention | Holds the whole root array — same leak as `ArrayList.subList`. Detach with `List.copyOf` |
| No CME | `SubList` has no `modCount`, so `ConcurrentModificationException` is impossible |
| `List.reversed()` | Java 21, JEP 431. `ReverseOrderListView.of(this, true)` |
| Immutable override | `AbstractImmutableList.reversed()` (`:334-337`) passes `modifiable=false` |
| `checkModifiable()` | Called first by **every** mutator; view throws before touching the base |
| Double reverse | `list.reversed().reversed() == list` → **true** (`of` unwraps to `rolv.base`) |
| Compare | `LinkedHashMap` same (`:1224` `return base;`); `TreeMap.descendingMap()` twice → **false** |
| Index flip | `get(i)` → `base.get(size - i - 1)`; `indexOf`↔`lastIndexOf` swap |
| View orientation | `view.add(x)` → `base.add(0, x)`; `view.sort(c)` → `base.sort(reverseOrder(c))` |
| `RandomAccess` | Preserved by the `Rand` subclass; **lost** by `ReverseOrderListView.subList` (`:396`) |
| `LinkedList.reversed()` | Its own `LinkedList$ReverseOrderLinkedListView`, not `RandomAccess` |
| Serializable | **Neither view.** `SubList` never declares it; ROLV javadoc `:38` says not serializable |
| Also not serializable | `Map.of(...).keySet()` — the anonymous `AbstractMap$1` |
| Snapshot escape hatch | `List.copyOf(view)` or `view.stream().toList()` |

---

## Self-test

**Q1.** `List.of(1,2,3,4,5).subList(1,4).subList(1,3)` — how many objects, and what is the offset?

<details><summary>Answer</summary>

One `SubList`, `offset = 2`, `size = 2`. `SubList.subList` routes to `SubList.fromSubList(this, 1, 3)`
(`ImmutableCollections.java:456-458`), which builds
`new SubList<>(parent.root, parent.offset + fromIndex, toIndex - fromIndex)` = `(root, 1 + 1, 2)`.
Sublists **flatten**: the `assert` at line 447 states `root instanceof List12 || root instanceof ListN`,
so the root is never a `SubList` and `get` is always one delegation deep. `ArrayList.SubList` nests
instead, so its `get` walks a chain.

</details>

**Q2.** Is `myList.reversed().reversed() == myList`? Justify from source, and say whether it
generalises to `TreeMap.descendingMap()`.

<details><summary>Answer</summary>

True for `List`. `ReverseOrderListView.of` begins
`if (list instanceof ReverseOrderListView<T> rolv) return rolv.base;`
(`ReverseOrderListView.java:46-47`), so reversing a view unwraps to the original object.
`List.java:891-893` documents it. Verified true for both `new ArrayList<>(...)` and `List.of(...)`.
`LinkedHashMap` behaves the same way (`LinkedHashMap.java:1224` is `return base;`). It does **not**
generalise: `TreeMap.descendingMap().descendingMap() == t` is **false**, because that path allocates a
fresh wrapper rather than unwrapping. So "double-reverse is identity" is a per-implementation fact you
must check, not a `SequencedCollection` guarantee.

</details>

**Q3.** `var v = new ArrayList<>(List.of(1,2,3)).reversed(); v.add(9);` — what does the backing list
look like, and is `v.subList(0,2)` `RandomAccess`?

<details><summary>Answer</summary>

`ReverseOrderListView.add(E)` is `checkModifiable(); base.add(0, e);`
(`ReverseOrderListView.java:159-163`) — appending to the view's end inserts at the base's **front**, so
the base becomes `[9, 1, 2, 3]` and the view reads `[3, 2, 1, 9]`. And `v.subList(0,2)` is **not**
`RandomAccess`: `ReverseOrderListView.subList` (lines 393-397) calls `new ReverseOrderListView<>(...)`
directly instead of the `of` factory, bypassing the `instanceof RandomAccess` branch that would have
produced a `Rand`. Verified: `rev.subList=java.util.ReverseOrderListView RandomAccess=false`.

</details>

**Q4.** `List.of(1,2,3).reversed().set(0, 9)` throws. Which object throws, and why does that matter?

<details><summary>Answer</summary>

The **view** throws, not the base. `AbstractImmutableList.reversed()`
(`ImmutableCollections.java:334-337`) calls `ReverseOrderListView.of(this, false)`, and every mutator on
the view opens with `checkModifiable()` (`ReverseOrderListView.java:75-79`), which throws
`UnsupportedOperationException` when `modifiable` is `false`. The base's own wall is never reached. It
matters because it makes the behaviour uniform: the class comment at lines 66-73 notes that a bulk op
inherited from `AbstractList` might *not* throw when no actual mutation would occur (`addAll` of an
empty collection), so an unconditional check in the view removes that dependence on the base's
implementation. Verified: all five of `add`/`set`/`sort`/`removeIf`/`clear` throw UOE.

</details>

**Q5.** `List.of(1,2,3,4)` serializes fine. Does `List.of(1,2,3,4).subList(1,3)`?

<details><summary>Answer</summary>

No — `NotSerializableException: java.util.ImmutableCollections$SubList`. `SubList` never declares
`Serializable`, so the `CollSer` proxy never gets a chance to run.
`List.of(1,2,3).reversed()` fails the same way (`NotSerializableException:
java.util.ReverseOrderListView$Rand`), and its javadoc at `ReverseOrderListView.java:38` says so
outright. `Map.of("k",1).keySet()` is a third case (`AbstractMap$1`). The rule: the proxy covers the
*collection*, not views derived from it. Fix with a defensive copy — `List.copyOf(sub)`,
`Set.copyOf(keySet)`.

</details>

**Q6.** Does `reversed()` always return a `ReverseOrderListView`?

<details><summary>Answer</summary>

No. `LinkedList` overrides `reversed()` with its own `LinkedList$ReverseOrderLinkedListView` — verified
class name, and it is **not** `RandomAccess`, which is correct for a linked list. `ReverseOrderListView`
is only the `List` interface *default* (`List.java:903-905`) plus the `AbstractImmutableList` override
(`ImmutableCollections.java:334-337`); any implementation is free to supply its own. So code that
`instanceof`-tests for `ReverseOrderListView` is testing an implementation detail that already has
counterexamples in `java.util`.

</details>

**Q7.** Why does `List.of(1,2,3).subList(0,2).indexOf(null)` throw NPE while the same call on a
sublist of `Stream.of(1,2,3).toList()` returns `-1`?

<details><summary>Answer</summary>

`SubList.allowNulls()` (`ImmutableCollections.java:497-499`) is
`return root instanceof ListN && ((ListN<?>)root).allowNulls;` — it asks the **root**, not itself. Both
`indexOf` and `lastIndexOf` (lines 501-525) then do `if (!allowNulls() && o == null) throw new NullPointerException();`.
`List.of(...)` builds a `ListN`/`List12` with `allowNulls = false`, so NPE. `Stream.toList()` goes
through `listFromTrustedArrayNullsAllowed`, producing a `ListN` with `allowNulls = true`, so the null
query is a legitimate search and returns `-1`. Null-hostility is a property of the root, inherited by
the window.

</details>

**Q8.** What do the two views have in common structurally, and where does the resemblance break?

<details><summary>Answer</summary>

Both are stateless wrappers that compute an index instead of copying: `SubList` maps `i` to
`root.get(offset + i)`, `ReverseOrderListView` maps `i` to `base.get(size - i - 1)`. Both are
non-serializable, and both retain their base strongly. The resemblance breaks on three points. (1)
`SubList`'s base is always a `List12`/`ListN` (`assert` at `:447`) and it **flattens** on nesting;
`ReverseOrderListView`'s base is any `List` and it **unwraps** on double-reverse. (2) `SubList` is
always immutable — its mutators come from `AbstractImmutableList`; `ReverseOrderListView` gates on a
`modifiable` boolean and writes through to the base when `true`. (3) `SubList` is always
`RandomAccess`; `ReverseOrderListView` is only when built via `of` over a `RandomAccess` base, and its
own `subList` loses the marker.

</details>

---

**Leaves covered:** 3.12.15–3.12.16 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 579
