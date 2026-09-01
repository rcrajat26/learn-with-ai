# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.3.10–2.3.11)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/01b-map-views-and-arrays-aslist.md](01b-map-views-and-arrays-aslist.md) · Next: [immutable-collections/01d-arrays-aslist.md](01d-arrays-aslist.md)

The three-way **view / copy / snapshot** distinction is defined in
[01-views-copies-snapshots.md](01-views-copies-snapshots.md); the three `Map` accessors are in
[01b-map-views-and-arrays-aslist.md](01b-map-views-and-arrays-aslist.md). This file covers the
two families of *ordered* views: `TreeMap`'s range views, and the reversed views
(`descendingMap` / `descendingSet` / `reversed()`). `Arrays.asList` continues in
[01d-arrays-aslist.md](01d-arrays-aslist.md).

All transcripts below are real output from **JDK 21.0.7+8-LTS-245, macOS arm64**.

---

## The ordered views at a glance

Every entry here is a *view* — no copying, no snapshot, writes propagate — but they differ in
which writes are allowed, and in whether repeated calls hand back the same object.

| Accessor | Returned class (JDK 21, measured) | Writes through the view | Same object on repeat call? |
|---|---|---|---|
| `TreeMap.headMap/tailMap/subMap` | `java.util.TreeMap$AscendingSubMap` | yes, **only in range** — outside throws | no, new view per call |
| `TreeMap.descendingMap()` | `java.util.TreeMap$DescendingSubMap` | yes, unrestricted | **yes**, cached |
| `TreeMap.reversed()` | `java.util.TreeMap$DescendingSubMap` | yes, unrestricted | **yes** — it *is* `descendingMap()` |
| `TreeSet.descendingSet()` | `java.util.TreeSet` | yes, unrestricted | **no**, new `TreeSet` per call |
| `LinkedHashMap.reversed()` | `java.util.LinkedHashMap$ReversedLinkedHashMapView` | yes | n/a |
| `ArrayList.reversed()` | `java.util.ReverseOrderListView$Rand` | yes, coordinates flipped | n/a |

That last column is not trivia — it is the whole of §2.3.11's identity story, and it is
inconsistent across the JDK on purpose. The reasons are in the source, below.

---

## `TreeMap` range views (§2.3.10)

### Mental model

A range view is not a sub-map. It is the *same* red-black tree plus a pair of fenceposts. The
view object stores no entries — only `lo`, `hi`, and four booleans saying whether each bound
exists and whether it is inclusive. Every operation on the view first asks "is this key inside
my fence?" and then forwards to the real map.

### Why it exists, and when to use it

`SortedMap` needs a way to express "the part of this map between two keys" without paying
O(k) to materialise it. `headMap`/`tailMap`/`subMap` are O(1) to *construct* — the cost is
deferred to iteration, which descends the tree to the fence and walks. That is what makes
`treeMap.subMap(from, to).clear()` an efficient range delete, and
`tailMap(now).firstEntry()` an efficient "next scheduled event" query.

When not to use one: if you need the range to survive independent of the source, or you plan
to insert keys outside it, take a copy — `new TreeMap<>(t.subMap(a, b))`.

### The mechanism

```java
// TreeMap.java:1674
final boolean fromStart, toEnd;

// TreeMap.java:1719-1730
final boolean inRange(Object key) {
    return !tooLow(key) && !tooHigh(key);
}

final boolean inClosedRange(Object key) {
    return (fromStart || m.compare(key, lo) >= 0)
        && (toEnd || m.compare(hi, key) >= 0);
}

final boolean inRange(Object key, boolean inclusive) {
    return inclusive ? inRange(key) : inClosedRange(key);
}
```

`fromStart`/`toEnd` mean "this side is unbounded", short-circuiting the comparison. `inRange`
is the half-open test used by mutators; `inClosedRange` is the laxer test used when a
*new* sub-range's own bound is exclusive and may therefore sit exactly on the parent's bound.

Then every mutator gates on it:

```java
// TreeMap.java:1828-1843
public final V put(K key, V value) {
    if (!inRange(key))
        throw new IllegalArgumentException("key out of range");
    return m.put(key, value);
}

public V putIfAbsent(K key, V value) {
    if (!inRange(key))
        throw new IllegalArgumentException("key out of range");
    return m.putIfAbsent(key, value);
}

public V merge(K key, V value, BiFunction<? super V, ? super V, ? extends V> remappingFunction) {
    if (!inRange(key))
        throw new IllegalArgumentException("key out of range");
    return m.merge(key, value, remappingFunction);
}
```

Every one of the three: check the fence, throw `IllegalArgumentException("key out of range")`
if outside, otherwise forward to `m` — the *whole* map, unfenced. So an in-range write through
the view lands in the source map, permanently.

The readers do **not** throw:

```java
// TreeMap.java:1871-1875
public V get(Object key) {
    return !inRange(key) ? null :  m.get(key);
}

public V remove(Object key) {
    return !inRange(key) ? null : m.remove(key);
}
```

Out of range, `get` and `remove` return `null` silently. `remove` in particular: an
out-of-range `remove` is a **no-op that reports "there was no such key"**, and the key it
declined to touch may well exist in the source map. **The syllabus states only the throwing
half of this leaf.** The silent half is the more dangerous one, because a nulled-out return
value reads as "nothing to do" rather than "I refused".

Narrowing re-checks the bounds, so you cannot widen by re-derivation: `AscendingSubMap.subMap`
guards both new bounds with `inRange(key, inclusive)` and throws
`IllegalArgumentException("fromKey out of range")` / `("toKey out of range")`
(`TreeMap.java:2213-2216`). Because that is the two-argument form, an exclusive new bound gets
the laxer `inClosedRange` test and may legally sit exactly on the parent's bound.

For the diagram of the fenced tree and the full internals of `inRange`, `AscendingSubMap` and
`DescendingSubMap` — including the memory cost of a chain of nested views — see
[../tree-map/03b2-internals-b2b-views-and-memory.md](../tree-map/03b2-internals-b2b-views-and-memory.md).

### Runnable

```java
import java.util.*;

public class Ranges {
    public static void main(String[] args) {
        TreeMap<Integer, String> t = new TreeMap<>();
        for (int i = 10; i <= 50; i += 10) t.put(i, "v" + i);

        SortedMap<Integer, String> head = t.headMap(30);
        System.out.println("headMap(30) class = " + head.getClass().getName());
        System.out.println("headMap(30)       = " + head);

        t.put(15, "v15");                       // source write shows up in the view
        System.out.println("after source put(15) view = " + head);
        head.remove(10);                        // view write shows up in the source
        System.out.println("after view remove(10) source = " + t);

        try {
            head.put(99, "nope");
        } catch (IllegalArgumentException e) {
            System.out.println("out-of-range put caught: " + e.getMessage());
        }
        try {
            head.put(30, "boundary");           // exclusive upper bound
        } catch (IllegalArgumentException e) {
            System.out.println("put at exclusive bound caught: " + e.getMessage());
        }

        System.out.println("head.remove(99)      = " + head.remove(99));
        System.out.println("head.get(99)         = " + head.get(99));
        System.out.println("head.containsKey(99) = " + head.containsKey(99));
        System.out.println("source untouched     = " + t);

        SortedMap<Integer, String> tail = t.tailMap(30);
        System.out.println("tailMap(30).put(30,..) old = " + tail.put(30, "v30b")
                + "  (inclusive lower bound, allowed)");
    }
}
```

Real output:

```
headMap(30) class = java.util.TreeMap$AscendingSubMap
headMap(30)       = {10=v10, 20=v20}
after source put(15) view = {10=v10, 15=v15, 20=v20}
after view remove(10) source = {15=v15, 20=v20, 30=v30, 40=v40, 50=v50}
out-of-range put caught: key out of range
put at exclusive bound caught: key out of range
head.remove(99)      = null
head.get(99)         = null
head.containsKey(99) = false
source untouched     = {15=v15, 20=v20, 30=v30, 40=v40, 50=v50}
tailMap(30).put(30,..) old = v30  (inclusive lower bound, allowed)
```

**Pitfall:** the wrong belief is that a range view behaves like a small independent map you
may fill freely, and that only *wildly* out-of-range keys are rejected. The symptoms are two.
First, `headMap(30).put(30, v)` throws — `headMap(k)` is exclusive at `k`, so the bound key
itself is out of range, while `tailMap(30).put(30, v)` succeeds because `tailMap(k)` is
inclusive. Second, the *reads* do not throw: `head.remove(99)` quietly returns `null` and
leaves key `99` alive in the source, so cleanup code written against a range view can appear
to succeed while deleting nothing. The fix: treat a range view as strictly a query and
in-range-edit device; do range deletes with `subMap(a, b).clear()`, which is fenced by
construction, and never route arbitrary user keys through one.

**Interview:** "You hold `t.subMap(10, 20)` and call `put(25, x)`. What happens?" —
`IllegalArgumentException("key out of range")` from `TreeMap.java:1829`; the view is
range-restricted on write, but `get`/`remove` outside the range return `null` instead of
throwing.

> A `TreeMap` range view is the same tree behind a pair of fenceposts: reads outside the fence
> return `null`, writes outside it throw `IllegalArgumentException`, and writes inside it land
> in the source map.

---

## `descendingMap`, `descendingSet`, `reversed()` (§2.3.11)

### Two generations of the same idea

`descendingMap()` / `descendingSet()` arrived in **Java 6** with `NavigableMap` and
`NavigableSet`. `reversed()` arrived in **Java 21** with `SequencedCollection` /
`SequencedMap` (JEP 431), which finally gave `List`, `Deque`, `LinkedHashMap` and the sorted
types one shared vocabulary for "has a defined encounter order".

On the sorted types the two are literally the same call. `NavigableMap` supplies a default:

```java
// NavigableMap.java:445-447
default NavigableMap<K, V> reversed() {
    return this.descendingMap();
}
```

and `NavigableSet` mirrors it at `NavigableSet.java:374-376`. `TreeMap` does not override
`reversed()`, so `t.reversed()` *is* `t.descendingMap()` — and since `descendingMap()` caches
(`TreeMap.java:1207-1213`), the two calls return the identical object.

`LinkedHashMap` had no `descendingMap`, so `reversed()` there is genuinely new:

```java
// LinkedHashMap.java:1224-1226
public SequencedMap<K, V> reversed() {
    return base;
}
```

That is `ReversedLinkedHashMapView.reversed()`. Reversing a reversed view returns the
**original map object**, not a view of a view. So `m.reversed().reversed() == m` is `true` for
a `LinkedHashMap` — verified elsewhere in this note set and reconfirmed below.

Double reversal is **not** universally identity-preserving, and that is the sharp part.
`DescendingSubMap.descendingMap()` builds a fresh `AscendingSubMap` over the backing map:

```java
// TreeMap.java:2325-2332
public NavigableMap<K,V> descendingMap() {
    NavigableMap<K,V> mv = descendingMapView;
    return (mv != null) ? mv :
        (descendingMapView =
         new AscendingSubMap<>(m,
                               fromStart, lo, loInclusive,
                               toEnd,     hi, hiInclusive));
}
```

`descendingMapView` is this view's own one-slot cache, so a *given* descending view keeps
returning the same re-ascended object. But the object it constructs is
`new AscendingSubMap<>(m, ...)` — a new unbounded ascending view wrapping `m`, never `m`
itself. So for a `TreeMap`, `t.descendingMap().descendingMap() == t` is `false`: the result is
`equals` to `t` but is one extra wrapper deep. This **bounds** the `LinkedHashMap`
double-reversal identity rather than contradicting it — that fact is real, it just does not
generalise to the sorted types.

`TreeSet` goes further and does not cache at all:

```java
// TreeSet.java:201-203
public NavigableSet<E> descendingSet() {
    return new TreeSet<>(m.descendingMap());
}
```

A brand-new `TreeSet` per call, wrapping the backing map's cached descending view. So
`ts.reversed() == ts.descendingSet()` is `false` even though `reversed()` is *defined* as
`descendingSet()` — the two calls each allocate. Note the returned class is plain
`java.util.TreeSet`: it is a real `TreeSet` whose backing map happens to be a descending view,
which is why it is still a live view of the original set despite the class name.

| | `descendingMap()` / `descendingSet()` | `reversed()` |
|---|---|---|
| Since | Java 6 (`NavigableMap`/`NavigableSet`) | Java 21 (JEP 431, `SequencedMap`/`SequencedCollection`) |
| Available on | `TreeMap`, `TreeSet`, `ConcurrentSkipListMap/Set` | also `List`, `Deque`, `LinkedHashMap`, `LinkedHashSet` |
| On a `TreeMap` | the real implementation | the default — `return this.descendingMap()` |
| Identity on repeat call | `TreeMap.descendingMap()` cached; `TreeSet.descendingSet()` new each time | follows whichever it delegates to |
| Double reversal returns source object | `TreeMap`: **no** (extra `AscendingSubMap`) | `LinkedHashMap`: **yes** (`return base;`) |
| Range restriction on write | none — writes forward to the whole map | none |

### Runnable

```java
import java.util.*;

public class Reversed {
    public static void main(String[] args) {
        TreeMap<Integer, String> t = new TreeMap<>();
        t.put(1, "a"); t.put(2, "b"); t.put(3, "c");
        System.out.println("descendingMap class = " + t.descendingMap().getClass().getName());
        System.out.println("reversed()   class  = " + t.reversed().getClass().getName());
        System.out.println("reversed() == descendingMap()          -> "
                + (t.reversed() == t.descendingMap()));
        System.out.println("descendingMap() == descendingMap()     -> "
                + (t.descendingMap() == t.descendingMap()));
        System.out.println("descendingMap().descendingMap() == t   -> "
                + (t.descendingMap().descendingMap() == t));
        System.out.println("reversed = " + t.reversed());

        LinkedHashMap<String, Integer> lhm = new LinkedHashMap<>();
        lhm.put("a", 1); lhm.put("b", 2); lhm.put("c", 3);
        SequencedMap<String, Integer> rev = lhm.reversed();
        System.out.println("lhm reversed class = " + rev.getClass().getName());
        System.out.println("lhm      = " + lhm + "   reversed = " + rev);
        System.out.println("reversed().reversed() == lhm -> " + (rev.reversed() == lhm));

        TreeSet<String> ts = new TreeSet<>(List.of("a", "b", "c"));
        System.out.println("descendingSet class = " + ts.descendingSet().getClass().getName());
        System.out.println("reversed() == descendingSet() -> "
                + (ts.reversed() == ts.descendingSet()));

        List<String> src = new ArrayList<>(List.of("A", "B", "C"));
        List<String> lrev = src.reversed();
        System.out.println("list reversed class = " + lrev.getClass().getName());
        lrev.addFirst("X");
        System.out.println("after rev.addFirst(\"X\") src = " + src);
        List<String> src2 = new ArrayList<>(List.of("A", "B", "C"));
        src2.reversed().add("Y");
        System.out.println("after rev.add(\"Y\")      src = " + src2);
    }
}
```

Real output:

```
descendingMap class = java.util.TreeMap$DescendingSubMap
reversed()   class  = java.util.TreeMap$DescendingSubMap
reversed() == descendingMap()          -> true
descendingMap() == descendingMap()     -> true
descendingMap().descendingMap() == t   -> false
reversed = {3=c, 2=b, 1=a}
lhm reversed class = java.util.LinkedHashMap$ReversedLinkedHashMapView
lhm      = {a=1, b=2, c=3}   reversed = {c=3, b=2, a=1}
reversed().reversed() == lhm -> true
descendingSet class = java.util.TreeSet
reversed() == descendingSet() -> false
list reversed class = java.util.ReverseOrderListView$Rand
after rev.addFirst("X") src = [A, B, C, X]
after rev.add("Y")      src = [Y, A, B, C]
```

**Insight:** the last two lines are the mental trap in `reversed()` on a `List`.
`addFirst` on the reversed view appends to the **source's tail** — `[A,B,C]` becomes
`[A,B,C,X]` — because "first" in reversed coordinates is "last" in source coordinates. A plain
`add` through the view, which means "append in view order", lands at the source's **front**:
`[Y,A,B,C]`. Both are correct; both read as backwards until you fix the coordinate flip in
your head. Say the operation out loud in the *view's* frame, then translate.

Writes through a descending map or set are unrestricted — unlike range views, there is no
fence to fail — and the coordinate flip applies to *bounds*, not just to ends:

```java
import java.util.*;

public class Desc {
    public static void main(String[] args) {
        TreeMap<Integer, String> t = new TreeMap<>();
        t.put(1, "a"); t.put(2, "b"); t.put(3, "c");
        NavigableMap<Integer, String> d = t.descendingMap();
        d.put(4, "d");
        System.out.println("after descendingMap().put(4,\"d\") source = " + t);
        d.remove(1);
        System.out.println("after descendingMap().remove(1) source  = " + t);
        System.out.println("descendingMap firstEntry = " + d.firstEntry());
        System.out.println("d.equals(t) = " + d.equals(t));
        System.out.println("d.subMap(4,true,2,true) = " + d.subMap(4, true, 2, true));
    }
}
```

Real output:

```
after descendingMap().put(4,"d") source = {1=a, 2=b, 3=c, 4=d}
after descendingMap().remove(1) source  = {2=b, 3=c, 4=d}
descendingMap firstEntry = 4=d
d.equals(t) = true
d.subMap(4,true,2,true) = {4=d, 3=c, 2=b}
```

`TreeSet.descendingSet()` behaves the same way — measured,
`ts.descendingSet().add("d")` on `[a, b, c]` leaves the source as `[a, b, c, d]`, and
`ds.equals(ts)` is `true`.

Read `d.subMap(4, true, 2, true)` carefully: on a descending view, `fromKey` must be the
**larger** key, because "from" means "earlier in this view's order". Measured,
`d.subMap(2, true, 4, true)` throws `IllegalArgumentException: fromKey > toKey`.
`d.equals(t)` being `true` while
`d != t` is the other half of the same idea — order is not part of `Map.equals`.

**Interview:** "`reversed()` vs `descendingMap()`?" — on a `NavigableMap` they are the same
call (`NavigableMap.java:446` is `return this.descendingMap()`); `reversed()` is the Java 21
`SequencedMap` name and extends the idea to `List`, `Deque` and `LinkedHashMap`, which never
had a `descending*`.

> `descendingMap`/`descendingSet` (Java 6) and `reversed()` (Java 21, JEP 431) are the same
> reversed-order live view under two generations of naming — identical on the sorted types,
> and only on `LinkedHashMap` does double reversal hand back the original object.

---

## Pitfalls

### Writing an out-of-range key through a `TreeMap` range view

**Wrong**

```java
TreeMap<Integer, String> t = new TreeMap<>(Map.of(10, "a", 20, "b", 30, "c"));
SortedMap<Integer, String> head = t.headMap(30);
try {
    head.put(30, "boundary");
} catch (IllegalArgumentException e) {
    System.out.println("head.put(30,..) -> " + e.getClass().getSimpleName()
            + ": " + e.getMessage());
}
System.out.println("head.remove(99) -> " + head.remove(99)
        + ", key 99 in source? " + t.containsKey(99));
```

```
head.put(30,..) -> IllegalArgumentException: key out of range
head.remove(99) -> null, key 99 in source? false
```

**Right**

```java
TreeMap<Integer, String> t = new TreeMap<>(Map.of(10, "a", 20, "b", 30, "c"));
t.put(30, "boundary");                     // write to the map, not the view
t.subMap(10, 30).clear();                  // range delete, fenced by construction
System.out.println(t);                     // {30=boundary}
```

**Why people believe it:** the view prints like a small map and reads like one, and the
mutators are asymmetric — `put` throws (`TreeMap.java:1829`) while `get`/`remove` return
`null` (`:1871`, `:1875`). Half your out-of-range operations fail loudly and half fail
silently, so the boundary never gets learned from one bug.

### Assuming double reversal always returns the original object

**Wrong**

```java
TreeMap<Integer, String> t = new TreeMap<>(Map.of(1, "a", 2, "b"));
System.out.println(t.descendingMap().descendingMap() == t);       // false
System.out.println(t.descendingMap().descendingMap().equals(t));  // true

TreeSet<String> ts = new TreeSet<>(List.of("a", "b"));
System.out.println(ts.reversed() == ts.descendingSet());          // false
```

**Right**

```java
LinkedHashMap<String, Integer> lhm = new LinkedHashMap<>();
lhm.put("a", 1);
System.out.println(lhm.reversed().reversed() == lhm);   // true — LinkedHashMap.java:1224

TreeMap<Integer, String> t = new TreeMap<>(Map.of(1, "a", 2, "b"));
System.out.println(t.reversed() == t.descendingMap());  // true — cached, same object
// For the sorted types, compare with equals(), or keep a reference to the original.
```

**Why people believe it:** `LinkedHashMap`'s `ReversedLinkedHashMapView.reversed()` really is
`return base;` (`LinkedHashMap.java:1224`), so the identity holds there and the rule feels
general. It is not: `DescendingSubMap.descendingMap()` (`TreeMap.java:2325-2332`) constructs
`new AscendingSubMap<>(m, ...)` rather than returning `m`, and `TreeSet.descendingSet()`
(`TreeSet.java:201-203`) allocates a `new TreeSet<>` on every single call. Reference identity
across reversal is per-implementation; `equals` is the portable comparison.

### Reading `addFirst` on a reversed `List` in source coordinates

**Wrong**

```java
List<String> src = new ArrayList<>(List.of("A", "B", "C"));
src.reversed().addFirst("X");
System.out.println(src);   // [A, B, C, X]  — not [X, A, B, C]
```

**Right**

```java
List<String> src = new ArrayList<>(List.of("A", "B", "C"));
src.addFirst("X");                    // Java 21 SequencedCollection, on the source
System.out.println(src);              // [X, A, B, C]

List<String> src2 = new ArrayList<>(List.of("A", "B", "C"));
src2.reversed().add("Y");             // "append in view order" == source's front
System.out.println(src2);             // [Y, A, B, C]
```

**Why people believe it:** the method name is absolute-sounding but the receiver is not. On
`java.util.ReverseOrderListView$Rand`, "first" means first *in the view*, which is last in the
source. Every positional method on a reversed view is expressed in the view's coordinate
system — including `subMap`'s `fromKey` on a `descendingMap`, which must be the larger key.

---

## Cheat sheet

| Claim | Truth (JDK 21) | Source |
|---|---|---|
| `headMap(k)` upper bound | **exclusive** — `put(k, v)` through it throws | `TreeMap.java:1829` |
| `tailMap(k)` lower bound | **inclusive** — `put(k, v)` through it is allowed | `TreeMap.java:1829` |
| range view out-of-range `put`/`putIfAbsent`/`merge` | `IllegalArgumentException("key out of range")` | `TreeMap.java:1829/1835/1841` |
| range view out-of-range `get`/`remove` | returns `null`, **no throw**, source untouched | `TreeMap.java:1871`, `:1875` |
| range view out-of-range `containsKey` | `false` | `TreeMap.java:1825` |
| in-range write through a range view | forwards to `m` — lands in the source map | `TreeMap.java:1831` |
| range view construction cost | O(1); cost is deferred to iteration | `TreeMap.java:1678` |
| range delete idiom | `t.subMap(a, b).clear()` | — |
| `subMap` of a range view | re-checked against the parent's fence | `TreeMap.java:2213-2216` |
| `headMap`/`tailMap` repeat call | new view object each time | `TreeMap.java:2202` |
| `t.descendingMap()` repeat call | **same** object — one-slot cache | `TreeMap.java:1207-1213` |
| `t.reversed() == t.descendingMap()` | `true` | `NavigableMap.java:445-447` |
| `t.descendingMap().descendingMap() == t` | `false` — a fresh `AscendingSubMap`; `equals` is `true` | `TreeMap.java:2325-2332` |
| `lhm.reversed().reversed() == lhm` | `true` — `return base;` | `LinkedHashMap.java:1224` |
| `ts.reversed() == ts.descendingSet()` | `false` — a new `java.util.TreeSet` per call | `TreeSet.java:201-203` |
| writes through `descendingMap`/`descendingSet` | unrestricted, land in the source | measured |
| `d.subMap(hi, true, lo, true)` on a descending view | `fromKey` must be the **larger** key | measured |
| `list.reversed()` | `ReverseOrderListView$Rand`; `addFirst` hits the source's **tail**, `add` its **front** | measured |
| version split | `descending*` Java 6; `reversed()` Java 21 (JEP 431) | — |

---

## Self-test

**Q1.** `t` is a `TreeMap` with keys 10..50. What happens for `t.headMap(30).put(30, "x")`, and for `t.headMap(30).remove(99)`?

<details><summary>Answer</summary>

`put(30, "x")` throws `IllegalArgumentException("key out of range")`. `headMap(k)` is
exclusive at `k`, so `30` fails `inRange` (`TreeMap.java:1719`) and the guard at `:1829`
throws. (`tailMap(30).put(30, ...)` would succeed — that bound is inclusive.)

`remove(99)` returns `null` and changes nothing:
`public V remove(Object key) { return !inRange(key) ? null : m.remove(key); }` at
`TreeMap.java:1875`. The readers fail silently while the writers throw — that asymmetry is
the trap, because cleanup code through a range view can appear to succeed while deleting
nothing. The syllabus for this leaf states only the throwing half.

</details>

**Q2.** How much does `t.subMap(a, b)` cost to construct, and where did the cost go?

<details><summary>Answer</summary>

O(1). The constructor (`TreeMap.java:1678-1679`) stores `m`, `lo`, `hi` and four booleans —
`fromStart`, `loInclusive`, `toEnd`, `hiInclusive` — and copies no entries. The cost is
deferred to use: iteration descends the tree to `absLowest()` and walks until it passes the
high fence, and every `get`/`put` pays one `inRange` comparison on top of the normal
O(log n) tree work. That is why `t.subMap(from, to).clear()` is the efficient range-delete
idiom, and why `tailMap(now).firstEntry()` is a cheap "next scheduled event" query.

</details>

**Q3.** For a `TreeMap` `t`, is `t.reversed() == t.descendingMap()`? Is `t.descendingMap().descendingMap() == t`?

<details><summary>Answer</summary>

First: **`true`**. `TreeMap` does not override `reversed()`, so it uses
`NavigableMap.java:445-447`, `default NavigableMap<K,V> reversed() { return this.descendingMap(); }`
— and `descendingMap()` caches its result (`TreeMap.java:1207-1213`), so both calls return the
same `TreeMap$DescendingSubMap`.

Second: **`false`**. `DescendingSubMap.descendingMap()` (`TreeMap.java:2325-2332`) builds a
new unbounded `AscendingSubMap` over the backing map, never returns the map object itself. The
result is `equals` to `t` but one wrapper deeper. Contrast `LinkedHashMap`, where
`ReversedLinkedHashMapView.reversed()` is literally `return base;`
(`LinkedHashMap.java:1224`), making `lhm.reversed().reversed() == lhm` `true`. Reference
identity across reversal is per-implementation, not a guarantee.

</details>

**Q4.** `ts.reversed()` is defined as `ts.descendingSet()`. Why is `ts.reversed() == ts.descendingSet()` false?

<details><summary>Answer</summary>

Because `descendingSet()` does not cache:
`public NavigableSet<E> descendingSet() { return new TreeSet<>(m.descendingMap()); }`
(`TreeSet.java:201-203`). Every call allocates a fresh `TreeSet` — so `reversed()`, which
delegates to it via `NavigableSet.java:374-376`, allocates a second one. Note the returned
class really is `java.util.TreeSet`, not a view class: it is a genuine `TreeSet` whose backing
map is the source map's cached descending view, which is why it is still live despite the
class name. Contrast `TreeMap.descendingMap()` (`:1207-1213`), which stores its result in a
`descendingMap` field and returns the same object forever.

</details>

**Q5.** `List<String> src = new ArrayList<>(List.of("A","B","C")); src.reversed().addFirst("X");` — what is `src`?

<details><summary>Answer</summary>

`[A, B, C, X]`. The reversed view is `java.util.ReverseOrderListView$Rand`, whose coordinate
system is flipped: "first" in the view is "last" in the source, so `addFirst` on the view
appends to the source's tail. Symmetrically, a plain `add` through the view means "append in
view order", which is the source's **front**: `src.reversed().add("Y")` on `[A,B,C]` gives
`[Y, A, B, C]`. Both measured on JDK 21.0.7.

</details>

**Q6.** Can you insert a key through `t.descendingMap()` that you could not insert through `t.headMap(30)`?

<details><summary>Answer</summary>

Yes — any key at all. A descending map has no fence: it is an unbounded `DescendingSubMap`
constructed with `fromStart = true` and `toEnd = true` (`TreeMap.java:1210-1212`), so
`inRange` always passes and the `put` guard at `:1829` never fires. Measured:
`t.descendingMap().put(4, "d")` on `{1=a, 2=b, 3=c}` gives `{1=a, 2=b, 3=c, 4=d}`. A range
view is the only one of these that restricts writes. What *does* flip on a descending view is
the coordinate system for bounds: `d.subMap(4, true, 2, true)` is the valid form, with the
larger key as `fromKey`.

</details>

**Q7.** Why does `NavigableSubMap` need both `inRange(key)` and `inClosedRange(key)`?

<details><summary>Answer</summary>

`inRange(key)` is `!tooLow(key) && !tooHigh(key)` (`TreeMap.java:1719-1721`) — the strict
half-open test that mutators use, so a key exactly on an exclusive bound is rejected.
`inClosedRange(key)` (`:1723-1726`) treats both bounds as inclusive. The two-argument
`inRange(key, inclusive)` (`:1728-1730`) picks between them, and it exists for deriving
*sub*-ranges: when you call `subMap` on an existing range view, the guards at `:2213-2216`
pass the new sub-range's own inclusivity flag. If the new bound is exclusive it is allowed to
sit exactly on the parent's bound, because the resulting range is still entirely inside the
parent. Using the strict test there would reject legal narrowings.

</details>

---

**Leaves covered:** 2.3.10–2.3.11 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 656
