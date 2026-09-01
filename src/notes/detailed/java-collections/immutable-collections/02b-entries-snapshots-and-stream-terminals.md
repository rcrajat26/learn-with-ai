# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.3.20–2.3.24)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/02a-shallow-immutability-and-boundaries.md](02a-shallow-immutability-and-boundaries.md) · Next: [immutable-collections/03-immutability-tiers.md](03-immutability-tiers.md)

All transcripts below are from **JDK 21.0.7+8-LTS-245, aarch64 (macOS)**.

---

## The map before the streets

§2.3 has been about the three ways a collection can relate to another collection: a **view** (window onto live state), a **copy** (independent, made once), a **snapshot** (a copy taken implicitly at a moment in time). This file closes §2.3 by applying that trichotomy to the three places it is least obvious — a single map entry, a concurrent iterator, and a stream terminal op — then hands you the decision table for the whole section.

| Thing | View, copy, or snapshot? | Immutable? | Introduced |
|---|---|---|---|
| `HashMap.Entry` from `entrySet().iterator()` (`HashMap$Node`) | **view** onto the map's node | no — `setValue` writes through | 1.2 |
| `AbstractMap.SimpleEntry` | **copy**, detached | no — mutable, but writes nowhere | 1.6 |
| `AbstractMap.SimpleImmutableEntry` | **copy**, detached | yes | 1.6 |
| `Map.entry(k,v)` → `KeyValueHolder` | **copy**, detached | yes, and null-hostile | 9 |
| `Map.Entry.copyOf(e)` | **snapshot** of any entry | yes (returns a `KeyValueHolder`) | 17 |
| `CopyOnWriteArrayList.iterator()` → `COWIterator` | **snapshot** of the backing array | read-only iterator | 5 |
| `EnumSet.copyOf` / `EnumSet.clone` | **copy** | no — result is a mutable `EnumSet` | 5 |
| `Stream.toList()` | **copy** into a fresh unmodifiable list | yes, nulls allowed | 16 |
| `collect(Collectors.toList())` | **copy** into an unspecified list | no (an `ArrayList` today) | 8 |
| `collect(Collectors.toUnmodifiableList())` | **copy** into an unmodifiable list | yes, null-hostile | 10 |

---

## 2.3.20 Three (really four) entry types — `Map.entry`, `SimpleEntry`, `Map.Entry.copyOf`

### Mental model

A `Map.Entry` is not a data class. It is a **cursor position that happens to expose two getters**. When a `HashMap` iterator hands you an entry, you are holding a pointer into the table; when `Map.entry("a", 1)` hands you one, you are holding a two-field box that has never met a map. Both satisfy the same interface, and nothing in the interface tells you which one you have. Everything in this leaf follows from that ambiguity.

### Why the types exist

`Map.Entry` came with the framework in 1.2, and `setValue` was specified as a write-through into the backing map — genuinely useful for `for (var e : map.entrySet()) e.setValue(f(e.getValue()));`. But that made entries unusable as return values: hand one out and you have leaked write access to your map, and it may go stale or dangle after the next `put`. Java 6 added `SimpleEntry`/`SimpleImmutableEntry` as detached alternatives you could build by hand. Java 9 added `Map.entry(k,v)` so `Map.ofEntries(...)` had something concise to consume. Java 17 finally added `Map.Entry.copyOf` for the case Java 6 handled clumsily: *I have an entry from somewhere and I do not know whether it is live.*

### When to reach for which

- Returning an entry from a method, or storing one: `Map.entry(k, v)` — final, null-hostile, no write-through.
- The entry came from someone else's `entrySet()` and you want to keep it: `Map.Entry.copyOf(e)`.
- You need it to survive `ObjectOutputStream`: `SimpleImmutableEntry`. **`KeyValueHolder` is not serializable** — this is the one case where the Java 6 type still wins.
- You need a mutable two-field pair with no map behind it: `SimpleEntry`. Rare, and usually a sign you wanted a `record`.

### Mechanism `[SOURCE]`

`Map.entry` returns a package-private `KeyValueHolder`. Its whole contract lives in three places — `/tmp/jc49src/java.base/java/util/KeyValueHolder.java`:

```java
// KeyValueHolder.java:54-63
final class KeyValueHolder<K,V> implements Map.Entry<K,V> {
    @Stable
    final K key;
    @Stable
    final V value;

    KeyValueHolder(K k, V v) {
        key = Objects.requireNonNull(k);
        value = Objects.requireNonNull(v);
    }
```

Line 54: `final class`, and it does **not** implement `Serializable` — contrast `SimpleEntry` at `AbstractMap.java:612-613`, which does. Lines 55–58: `@Stable` tells the JIT these fields are written once, so a read can be constant-folded after the first load; combined with `final` that is why `Map.of` entries cost nothing to re-read in a hot loop. Lines 61–62: **both** key and value go through `requireNonNull`, so `Map.entry(k, null)` throws — not on read, at construction.

```java
// KeyValueHolder.java:91-94
    @Override
    public V setValue(V value) {
        throw new UnsupportedOperationException("not supported");
    }
```

Unconditional throw. Note the message string `"not supported"` — that literal is how you identify a `KeyValueHolder` in a stack trace with no other context.

`Map.Entry.copyOf` — `/tmp/jc49src/java.base/java/util/Map.java:625-633`:

```java
        @SuppressWarnings("unchecked")
        public static <K, V> Map.Entry<K, V> copyOf(Map.Entry<? extends K, ? extends V> e) {
            Objects.requireNonNull(e);
            if (e instanceof KeyValueHolder) {
                return (Map.Entry<K, V>) e;
            } else {
                return Map.entry(e.getKey(), e.getValue());
            }
        }
```

Line 627: null entry rejected. Line 628: the identity fast path — and it tests for **exactly one class**, `KeyValueHolder`. Line 629: same instance returned, unchecked-cast because the wildcards widen safely for an immutable type. Line 631: otherwise, eagerly read both accessors *once* and box them, which is what makes it a snapshot; the `Map.entry` call inside means the copy inherits null-hostility.

**Insight:** this is exactly the `List.copyOf` / `Set.copyOf` / `Map.copyOf` shape — "already one of ours, hand it back; otherwise copy" — but the "ours" test is narrower than a reader expects. `SimpleImmutableEntry` is already immutable and `copyOf` copies it anyway, because it is not a `KeyValueHolder`:

```
  copyOf(Map.entry) same instance? true, class=java.util.KeyValueHolder
  copyOf(SimpleEntry) class = java.util.KeyValueHolder, equals? true
  copyOf(SimpleImmutableEntry) same instance? false, class=java.util.KeyValueHolder
  copyOf(entry with null value): java.lang.NullPointerException
```

The javadoc is careful here — `Map.java:614-616` says only "if the given entry was obtained from a call to `copyOf` or `Map::entry`, calling `copyOf` will generally **not** create another copy." It never promises the general immutable case, and the implementation honours exactly that. `[RESEARCH]` verified against source and run output.

**Insight:** `SimpleEntry.setValue` writes to its own field and nothing else. `AbstractMap.java:671-675`:

```java
        public V setValue(V value) {
            V oldValue = this.value;
            this.value = value;
            return oldValue;
        }
```

`this.value` is a plain private field (line 621) with no map reference anywhere in the class — the javadoc at `AbstractMap.java:598-599` states it outright: "Instances of this class are not associated with any map nor with any map's entry-set view." So `SimpleEntry` is *mutable and useless as a mutator*: the call succeeds, returns the old value, and changes nothing the caller cares about. It is the worst of both worlds unless you specifically wanted a mutable pair.

### The entry-type table

Every cell below is from the harness run, not inference.

| | `HashMap$Node` (live) | `SimpleEntry` | `SimpleImmutableEntry` | `KeyValueHolder` (`Map.entry`) |
|---|---|---|---|---|
| How you get one | `map.entrySet().iterator()` | `new` (1.6) | `new` (1.6) | `Map.entry(k,v)` (9) |
| What it holds | pointer into the map's table | its own `K key`, `V value` | its own final `K`, `V` | its own final `K`, `V` |
| `setValue` | succeeds, **writes through to the map** | succeeds, writes only its own field | `UnsupportedOperationException` | `UnsupportedOperationException("not supported")` |
| Null key/value allowed? | yes (`HashMap` allows both) | yes — both constructors accept null | yes | **no** — `NullPointerException` at construction |
| Serializable? | no (`HashMap$Node` is not) | yes — 175 bytes for `("a",1)` | yes — 184 bytes | **no** — `NotSerializableException` |
| `final` class? | no | no | no | yes |
| Stale after `map.put`? | value re-reads live: yes | no, detached | no, detached | no, detached |

The liveness row is worth dwelling on. From the run:

```
  live entry class = java.util.HashMap$Node
  after setValue, map = {k=99}
  snapshot = k=99, live entry = k=5, map = {k=5}
```

`liveEntry.setValue(99)` mutated the map. Then `Map.Entry.copyOf` froze `k=99`; a subsequent `live.put("k", 5)` moved both the map and the live entry to `5` while the snapshot stayed at `99`. That is the entire reason `copyOf` exists.

**Interview:** "How do you safely return an entry out of a method?" — `Map.Entry.copyOf(e)`, because entries from an `entrySet()` view may be live pointers into the map (`HashMap$Node`) and liveness is per-implementation, not a `Map` guarantee.

### Runnable example

```java
import java.util.*;

public class EntryKinds {
    public static void main(String[] args) {
        Map<String, Integer> map = new HashMap<>();
        map.put("k", 1);

        Map.Entry<String, Integer> live = map.entrySet().iterator().next();
        Map.Entry<String, Integer> frozen = Map.Entry.copyOf(live);
        var detached = new AbstractMap.SimpleEntry<>(live);

        map.put("k", 42);
        System.out.println("live    = " + live);      // k=42  -> tracked the map
        System.out.println("frozen  = " + frozen);    // k=1   -> snapshot
        System.out.println("detached= " + detached);   // k=1   -> snapshot

        detached.setValue(-1);
        System.out.println("after detached.setValue(-1), map = " + map); // {k=42}

        try { frozen.setValue(-1); }
        catch (UnsupportedOperationException e) {
            System.out.println("frozen.setValue -> " + e.getMessage());  // not supported
        }
        try { Map.entry("x", (Integer) null); }
        catch (NullPointerException e) {
            System.out.println("Map.entry(k, null) -> NullPointerException");
        }
    }
}
```

Note the ordering: `Map.entry` rejects nulls at *construction*, not on read (`KeyValueHolder.java:61-62`) — see the fourth entry under [Pitfalls](#pitfalls) for what that does to a stream pipeline.

Related, already established elsewhere in this set: `EnumMap`'s `EntrySet.toArray` builds `SimpleEntry` snapshots while its *iterator* yields live entries, and `HashMap`'s `EntrySet` has no `toArray` override at all. Same interface, opposite liveness. Never assume.

> **Definition.** `Map.entry(k,v)` returns a final, non-serializable, null-hostile `KeyValueHolder` whose `setValue` always throws; `AbstractMap.SimpleEntry` is a serializable, null-tolerant, mutable pair whose `setValue` writes only its own field; and `Map.Entry.copyOf` (Java 17) converts any entry — live or not — into a `KeyValueHolder`, returning the argument unchanged only when it already is one.

---

## 2.3.21 `CopyOnWriteArrayList` iterators are snapshots

### Mental model

An ordinary `ArrayList` iterator is a **cursor into a mutable buffer**, so it must police concurrent structural change with a modification counter. A `COWIterator` is a **cursor into an array nobody will ever write to again** — because every `CopyOnWriteArrayList` mutation installs a brand-new array. There is nothing to police, so `ConcurrentModificationException` cannot happen and `remove` has nothing sensible to mean.

### Mechanism `[SOURCE]`

`/tmp/jc49src/java.base/java/util/concurrent/CopyOnWriteArrayList.java:1161-1170`:

```java
    static final class COWIterator<E> implements ListIterator<E> {
        /** Snapshot of the array */
        private final Object[] snapshot;
        /** Index of element to be returned by subsequent call to next.  */
        private int cursor;

        COWIterator(Object[] es, int initialCursor) {
            cursor = initialCursor;
            snapshot = es;
        }
```

Line 1163: the captured array is a `private final` field literally named `snapshot`. It is assigned once, at construction (line 1169), from whatever `getArray()` returned at `iterator()` time (line 1108). Notice what is *absent*: no reference back to the list, and no `expectedModCount`. There is no channel through which a later mutation could reach this iterator.

```java
// CopyOnWriteArrayList.java:1207-1227
        public void remove() {
            throw new UnsupportedOperationException();
        }
        public void set(E e) {
            throw new UnsupportedOperationException();
        }
        public void add(E e) {
            throw new UnsupportedOperationException();
        }
```

All three mutators throw unconditionally. They must: writing into `snapshot` would mutate an array the list may no longer own, and writing into the list's current array would break the snapshot invariant for the remaining elements.

### Proof `[PROVE]`

```java
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;

public class CowSnapshot {
    public static void main(String[] args) {
        var cow = new CopyOnWriteArrayList<>(List.of("a", "b", "c"));
        Iterator<String> it = cow.iterator();

        cow.add("d");
        cow.set(0, "Z");
        cow.remove("b");

        var seen = new ArrayList<String>();
        while (it.hasNext()) seen.add(it.next());
        System.out.println("iterator saw = " + seen);  // [a, b, c]
        System.out.println("list now     = " + cow);   // [Z, c, d]

        Iterator<String> it2 = cow.iterator();
        it2.next();
        try { it2.remove(); }
        catch (UnsupportedOperationException e) {
            System.out.println("COWIterator.remove -> UnsupportedOperationException");
        }

        var al = new ArrayList<>(List.of("a", "b", "c"));
        Iterator<String> ait = al.iterator();
        al.add("d");
        try { ait.next(); }
        catch (ConcurrentModificationException e) {
            System.out.println("ArrayList iterator -> ConcurrentModificationException");
        }
        System.out.println("spliterator IMMUTABLE? "
            + cow.spliterator().hasCharacteristics(Spliterator.IMMUTABLE));
    }
}
```

Real output:

```
iterator saw = [a, b, c]
list now     = [Z, c, d]
COWIterator.remove -> UnsupportedOperationException
ArrayList iterator -> ConcurrentModificationException
spliterator IMMUTABLE? true
```

Three structural mutations landed mid-iteration and the iterator reported the original three elements with no exception, while the equivalent `ArrayList` sequence threw. `[NUM]` `spliterator()` reports `Spliterator.IMMUTABLE | Spliterator.ORDERED` (line 1158) — the `IMMUTABLE` bit is the JDK asserting the snapshot contract to the stream framework, which is why a stream over a `CopyOnWriteArrayList` never needs late-binding.

**Tradeoff, not fact:** snapshot iteration is free of `ConcurrentModificationException` **but** the read is stale by construction, and every write is O(n) with a full array allocation. The cost model, sizing arithmetic, and when CoW beats a lock live in [../concurrent-collections/04-copy-on-write.md](../concurrent-collections/04-copy-on-write.md) — this leaf owns only the snapshot semantics.

> **Definition.** `CopyOnWriteArrayList.iterator()` captures the backing array in a `private final Object[] snapshot` at creation time and never consults the list again, so it never throws `ConcurrentModificationException`, never observes later writes, and rejects `remove`/`set`/`add` with `UnsupportedOperationException`.

---

## 2.3.22 `EnumSet.copyOf` and `EnumSet.clone`

### Mental model

An `EnumSet` is a **bitmask plus a `Class<E>`**. Copying one is therefore a field copy, not an element walk — which is why `copyOf(EnumSet)` is a one-liner delegating to `clone()`. But copying an arbitrary `Collection` of enums has no bitmask to copy and, worse, **no enum type to read**, so it must extract the type from the first element. That single asymmetry generates all three behaviours below.

### Mechanism `[SOURCE]`

`/tmp/jc49src/java.base/java/util/EnumSet.java:154-185` — both overloads:

```java
    public static <E extends Enum<E>> EnumSet<E> copyOf(EnumSet<E> s) {
        return s.clone();
    }
```

Line 155: nothing but `clone()`. Static overload resolution decides which of the two `copyOf` methods you get, at **compile time**, from the static type of the argument.

```java
    public static <E extends Enum<E>> EnumSet<E> copyOf(Collection<E> c) {
        if (c instanceof EnumSet) {
            return ((EnumSet<E>)c).clone();
        } else {
            if (c.isEmpty())
                throw new IllegalArgumentException("Collection is empty");
            Iterator<E> i = c.iterator();
            E first = i.next();
            EnumSet<E> result = EnumSet.of(first);
            while (i.hasNext())
                result.add(i.next());
            return result;
        }
    }
```

Line 173: a **runtime** recovery of the fast path, for when the static type was `Collection` but the object is an `EnumSet`. Lines 176–177: the `IllegalArgumentException` — with no element, `EnumSet.of(first)` on line 180 has no `Class<E>` to hand to `noneOf`, so there is no set to build. Lines 178–182: the slow path is an ordinary element-by-element `add` loop, O(n) not O(1), and it inherits `add`'s null-hostility.

`clone()` is defined at `EnumSet.java:381-388` as `(EnumSet<E>) super.clone()` — a shallow `Object.clone`. For `RegularEnumSet` that is complete, because its state is one primitive: `private long elements = 0L` (`RegularEnumSet.java:43`). A shallow copy of a `long` field *is* an independent bitmask.

**Insight:** for enums with more than 64 constants the state is `private long elements[]` (`JumboEnumSet.java:45`), and a shallow clone would **share the array**. So `JumboEnumSet` overrides clone (`JumboEnumSet.java:370-372`):

```java
    public EnumSet<E> clone() {
        JumboEnumSet<E> result = (JumboEnumSet<E>) super.clone();
        result.elements = result.elements.clone();
```

Line 371 does the shallow copy, line 372 immediately un-shares the bitmask array. Without line 372, `copyOf` on a 65-constant enum would return an alias, and every `EnumSet.copyOf` in the JDK would be silently broken above 64 constants. Verified: `EnumSet.of(Big.E00, Big.E65)` on a 70-constant enum is a `java.util.JumboEnumSet`, its `clone()` stayed at size 2 while the source grew to 3.

### The three paths

| | `copyOf(EnumSet<E>)` | `copyOf(Collection<E>)`, arg is an `EnumSet` | `copyOf(Collection<E>)`, arg is not | `clone()` |
|---|---|---|---|---|
| Selected by | static type at compile time | runtime `instanceof` (line 173) | fallthrough | direct call on an `EnumSet` |
| Cost | O(1) field copy | O(1) field copy | O(n) `add` loop | O(1) field copy |
| Result type | same class as source (`RegularEnumSet`/`JumboEnumSet`) | same as source | `RegularEnumSet` or `JumboEnumSet` per universe size | same as source |
| Result mutable? | **yes** | yes | yes | yes |
| Shares bitmask with source? | no — `long` copied, `long[]` cloned | no | no | no |
| Empty argument | fine — empty copy | fine — empty copy | **`IllegalArgumentException("Collection is empty")`** | fine |
| Null element | n/a (`EnumSet` cannot hold null) | n/a | `NullPointerException` | n/a |
| Iteration order of result | ordinal order | ordinal order | **ordinal order**, not the source's order | ordinal order |

Run output for the interesting rows:

```
  copyOf(EnumSet) class = java.util.RegularEnumSet, same instance? false, equals? true
  after source.add(FRI): source=[MON, WED, FRI] copy=[MON, WED]
  copyOf(List) class = java.util.RegularEnumSet -> [TUE, THU]
  EnumSet.copyOf(List.of()): java.lang.IllegalArgumentException (Collection is empty)
  EnumSet.copyOf(empty EnumSet): OK
  EnumSet.copyOf(List with null): java.lang.NullPointerException
  copyOf(reversed list) = [A, B, C]
  copyOf(unmodifiableSet(EnumSet)) = [A] class=java.util.RegularEnumSet
```

Two traps in there. `copyOf(List.of(Day.C, Day.B, Day.A))` returns `[A, B, C]` — the bitmask has no room to remember your order. And `Collections.unmodifiableSet(enumSet)` is **not** an `EnumSet`, so it takes the slow branch; that works, but it means wrapping an *empty* `EnumSet` in `unmodifiableSet` and passing it to `copyOf` throws `IllegalArgumentException` where the unwrapped set would have succeeded.

**Pitfall:** `EnumSet.copyOf` looks like `List.copyOf` and is not. `List.copyOf` returns an **immutable** list; `EnumSet.copyOf` returns a **mutable** `EnumSet`. There is no immutable-`EnumSet` factory — for that you need `Collections.unmodifiableSet(EnumSet.copyOf(...))`, at the cost of losing the `EnumSet` static type and the fast path on any downstream `copyOf`.

> **Definition.** `EnumSet.copyOf` has two overloads: the `EnumSet` one and the runtime-`instanceof` branch of the `Collection` one both delegate to `clone()` for an O(1) bitmask copy, while the general `Collection` branch does an O(n) `add` loop and throws `IllegalArgumentException` on an empty argument because it has no element from which to infer the enum type — and all three, like `clone()` itself, return a **mutable** set.

---

## 2.3.23 Stream terminal ops and mutability `[TRAP]`

### Mental model

Three ways to turn a stream into a `List`, added in three different decades of Java's life, each reflecting the fashion of its moment: `Collectors.toList()` (Java 8) deliberately promised **nothing**; `Collectors.toUnmodifiableList()` (Java 10) promised immutability and adopted the `List.of` null-hostility along with it; `Stream.toList()` (Java 16) promised immutability **but not** null-hostility, because it had to work for streams that legitimately contain nulls. The matrix is not arbitrary — it is three snapshots of an evolving opinion.

### Why the third one exists

`collect(Collectors.toList())` is eight characters of boilerplate around the most common operation in the language, and its result is an `ArrayList` only by accident of implementation. `Stream.toList()` was added to be shorter *and* to make the accident impossible to depend on. It could not simply reuse `toUnmodifiableList`, because `map(Map::get).collect(toUnmodifiableList())` would start throwing `NullPointerException` on data that previously worked — so it took a different immutable path that tolerates nulls.

### Mechanism `[SOURCE]`

`Collectors.toList()` — `/tmp/jc49src/java.base/java/util/stream/Collectors.java:241-246`:

```java
    public static <T>
    Collector<T, ?, List<T>> toList() {
        return new CollectorImpl<>(ArrayList::new, List::add,
                                   (left, right) -> { left.addAll(right); return left; },
                                   CH_ID);
    }
```

`ArrayList::new` is the container supplier, `List::add` the accumulator, and `CH_ID` marks the collector `IDENTITY_FINISH` — no finisher runs, so the `ArrayList` is handed straight out. That is why the type is an `ArrayList` today. But the javadoc immediately above, at `Collectors.java:232-235`, is explicit: *"There are no guarantees on the type, mutability, serializability, or thread-safety of the `List` returned."* **The type is unspecified by contract.** `CH_ID` is an implementation choice, and code that casts is relying on it.

`Collectors.toUnmodifiableList()` — `Collectors.java:260-272`:

```java
    Collector<T, ?, List<T>> toUnmodifiableList() {
        return new CollectorImpl<>(ArrayList::new, List::add,
                                   (left, right) -> { left.addAll(right); return left; },
                                   list -> {
                                       if (list.getClass() == ArrayList.class) { // ensure it's trusted
                                           return SharedSecrets.getJavaUtilCollectionAccess()
                                                               .listFromTrustedArray(list.toArray());
                                       } else {
                                           throw new IllegalArgumentException();
                                       }
                                   },
                                   CH_NOID);
```

Same accumulation, but `CH_NOID` means a **finisher** runs. The finisher calls `listFromTrustedArray` — the `List.of` entry point — which produces a `List12` for size ≤ 2 and a `ListN` with `allowNulls == false` above that, and rejects nulls. The `getClass() == ArrayList.class` guard exists so a subclass cannot smuggle in an array it still holds a reference to.

`Stream.toList()` takes a third path. As established elsewhere in this set: it builds an `ImmutableCollections.ListN` via `listFromTrustedArrayNullsAllowed` (`ImmutableCollections.java:242`, exposed at line 126), which sets the `private final boolean allowNulls` field (`ImmutableCollections.java:667`) to `true`. That flag is the whole mechanism behind the null column — `ListN.contains` and `indexOf` guard on it (`ImmutableCollections.java:722, 736`):

```java
            if (!allowNulls && o == null) {
```

With `allowNulls == true` the guard falls through and `contains(null)` answers honestly instead of throwing. It also means `List.copyOf` will not short-circuit on a `Stream.toList()` result, because `listCopy`'s guard (`ImmutableCollections.java:169`) is:

```java
        if (coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)) {
```

`!c.allowNulls` is false, so the `instanceof` fails and a real copy happens. Verified: `List.copyOf(Stream.of("p","q","r").toList()) == that list` is **false**, while `List.copyOf(List.of("p","q","r")) == that list` is **true**.

### D-61 — Stream-to-collection mutability and nullability

Every cell below was produced by the harness (`getClass().getName()` for the type column, a try/catch per mutator, a stream containing an explicit `null` for the null column). **Read the last column first:** only two of the three rows are contractual, and the middle row's type is folklore.

| Terminal op | Concrete type today (JDK 21.0.7) | Mutable? | `set` allowed? | Nulls allowed? | Specified by contract? |
|---|---|---|---|---|---|
| `Stream.toList()` (16) | `java.util.ImmutableCollections$ListN` — **always `ListN`**, even for 1 element | no — `add` → `UnsupportedOperationException` | no — `UnsupportedOperationException` | **yes** — `Stream.of("x", null).toList()` → `[x, null]`, `contains(null)` → `true` | **yes** — javadoc specifies "unmodifiable" and that nulls are permitted |
| `collect(Collectors.toList())` (8) | `java.util.ArrayList` | **yes** — `add` succeeds | **yes** — `set` succeeds | yes — `[x, null]` | **no** — "no guarantees on the type, mutability, serializability, or thread-safety" (`Collectors.java:232-235`) |
| `collect(Collectors.toUnmodifiableList())` (10) | `ImmutableCollections$List12` for size ≤ 2, `$ListN` for size ≥ 3 | no — `UnsupportedOperationException` | no — `UnsupportedOperationException` | **no** — `NullPointerException` from the finisher | **yes** — javadoc specifies unmodifiable and null-rejecting |

Raw evidence:

```
  Stream.toList()                 -> java.util.ImmutableCollections$ListN
  collect(toList())               -> java.util.ArrayList
  collect(toUnmodifiableList())   -> java.util.ImmutableCollections$List12
  toList().set: java.lang.UnsupportedOperationException
  collect(toList()).set: OK
  toUnmodifiableList().set: java.lang.UnsupportedOperationException
  null via Stream.toList: OK                          -> [x, null]
  null via collect(toList()): OK                      -> [x, null]
  null via collect(toUnmodifiableList()): java.lang.NullPointerException
  cast collect(toList()) to ArrayList: OK
  cast Stream.toList() to ArrayList: java.lang.ClassCastException
  Stream.toList() serialize: serializable, 63 bytes
  collect(toList()) serialize: serializable, 71 bytes
```

`[NUM]` Note the type asymmetry the syllabus does not mention: `Stream.of("x").toList()` is a `ListN` of one element, whereas `Stream.of("x").collect(toUnmodifiableList())` is a `List12`. Both are immutable; they are not the same class, and a `getClass()` comparison between them fails. And `.parallel()` changes nothing — parallel `toList()` is still `ListN`, parallel `collect(toList())` is still `ArrayList`.

### Edge row — the two canonical empty lists

Also established elsewhere in this set and directly relevant here: there are **two** canonical empty immutable lists, `EMPTY_LIST` (`allowNulls == false`, returned by `List.of()`) and `EMPTY_LIST_NULLS` (returned by `Stream.empty().toList()`). Verified:

```
  List.of() == Stream.empty().toList()? false
  List.of().equals(Stream.empty().toList())? true
  List.of().contains(null): java.lang.NullPointerException
  Stream.empty().toList().contains(null): false
```

Two objects that are `equals`, both empty, both immutable, both `ListN` — and they disagree about whether `contains(null)` is a legal question. Any code that reasons about empty-list identity or does `contains(null)` on a maybe-empty result must know which one it holds.

### The gotcha

**Pitfall:** believing `Stream.toList()` is a drop-in replacement for `collect(Collectors.toList())`.

- **Wrong belief:** "`toList()` is just the short form."
- **Symptom:** an `UnsupportedOperationException` at runtime, weeks later, from a `sort`/`add`/`removeIf` far from the collection site — or a `ClassCastException` from a cast to `ArrayList` that used to work.
- **Fix:** if the result is mutated, say so at the collection site: `collect(Collectors.toCollection(ArrayList::new))`. That is the only one of the four that *contractually* gives you an `ArrayList`.

The mirror-image pitfall is real too: migrating `collect(toUnmodifiableList())` to `toList()` silently *stops* rejecting nulls, so a null that used to fail fast now flows downstream to blow up somewhere less informative.

**Interview:** "Difference between `stream.toList()` and `stream.collect(Collectors.toList())`?" — `toList()` is contractually unmodifiable and null-tolerant; `Collectors.toList()` guarantees nothing about type or mutability and happens to return a mutable `ArrayList`. Say "happens to" out loud; that is the answer they are listening for.

> **Definition.** `Stream.toList()` is contractually unmodifiable and null-permitting (an `ImmutableCollections.ListN` with `allowNulls == true`); `Collectors.toUnmodifiableList()` is contractually unmodifiable and null-rejecting (a `List12`/`ListN` with `allowNulls == false`); and `Collectors.toList()` guarantees nothing at all about type, mutability, serializability or thread-safety, returning a mutable `ArrayList` purely as today's implementation choice.

---

## 2.3.24 The mutability decision table

This closes §2.3. It is organised by **intent**, because that is the only thing you know at the call site — you do not start from an API and wonder what it does; you start from a sentence about what you need.

| I need… | Use | Why not the neighbour |
|---|---|---|
| a defensive copy the caller cannot change; nulls impossible | `List.copyOf(c)` / `Set.copyOf` / `Map.copyOf` | `Collections.unmodifiableList` returns a **view** — the source can still change under it ([01-views-copies-snapshots.md](01-views-copies-snapshots.md)) |
| a defensive copy that may contain nulls | `Collections.unmodifiableList(new ArrayList<>(c))` | `List.copyOf` throws `NullPointerException` on a null element |
| a small fixed literal collection | `List.of(...)` / `Set.of(...)` / `Map.of(...)` ([02-immutable-factories.md](02-immutable-factories.md)) | `Arrays.asList` is fixed-size but `set`-able and null-tolerant ([01d-arrays-aslist.md](01d-arrays-aslist.md)) |
| to expose a read-only window that **should** track later writes | `Collections.unmodifiableList(live)` | a copy freezes; that is the opposite requirement |
| a mutable list from a stream | `collect(Collectors.toCollection(ArrayList::new))` | `Collectors.toList()` returns a mutable list **today** but promises nothing |
| an unmodifiable list from a stream, nulls possible | `stream.toList()` | `toUnmodifiableList()` throws on a null element |
| an unmodifiable list from a stream, nulls are a bug | `collect(Collectors.toUnmodifiableList())` | `toList()` would let the null through silently |
| a single key/value pair to return or store | `Map.entry(k, v)` | `SimpleEntry` is mutable; a live `entrySet` entry may write through |
| a serializable key/value pair | `new AbstractMap.SimpleImmutableEntry<>(k, v)` | `KeyValueHolder` from `Map.entry` is **not** serializable |
| to keep an entry obtained from someone else's map | `Map.Entry.copyOf(e)` | the entry may be a live `HashMap$Node` that follows the map |
| an independent mutable enum set | `EnumSet.copyOf(src)` or `src.clone()` | `Set.copyOf` loses the bitmask representation and returns an immutable `SetN` |
| an immutable enum set | `Collections.unmodifiableSet(EnumSet.copyOf(src))` | there is no immutable-`EnumSet` factory; `EnumSet.copyOf` is mutable |
| iteration that never throws `ConcurrentModificationException` under concurrent writes | `CopyOnWriteArrayList` | `ArrayList` iterators are fail-fast; synchronised wrappers still need external locking during iteration |
| a range of a `TreeMap`/`TreeSet` that tracks the source | `subMap` / `headSet` / `tailSet` ([01c-treemap-range-and-reversed-views.md](01c-treemap-range-and-reversed-views.md)) | `new TreeMap<>(m.subMap(..))` freezes it |
| a map's keys or values as a live window | `keySet()` / `values()` / `entrySet()` ([01b-map-views-and-arrays-aslist.md](01b-map-views-and-arrays-aslist.md)) | copying them breaks write-through removal |
| an immutable collection whose **elements** cannot be mutated either | nothing in `java.util` — see [02a-shallow-immutability-and-boundaries.md](02a-shallow-immutability-and-boundaries.md) | every factory here is shallow; `List.of(mutableThing)` freezes the list, not the thing |

**Insight:** the table has exactly one structural rule behind it. Ask two questions — *must it track later changes to the source?* (view vs copy) and *may the holder mutate it?* (mutable vs immutable) — and the four quadrants are: view+mutable = `subMap`/`keySet`; view+immutable = `unmodifiableX`; copy+mutable = `new ArrayList<>(c)`/`EnumSet.copyOf`; copy+immutable = `List.copyOf`/`Stream.toList()`. Everything else is null-handling and serializability detail.

---

## Pitfalls

### Assuming `Collectors.toList()` returns an `ArrayList`

**Wrong**

```java
ArrayList<String> names = (ArrayList<String>) people.stream()
        .map(Person::name)
        .collect(Collectors.toList());
names.trimToSize();
```

Compiles, passes today, and rests entirely on `Collectors.java:245`'s `CH_ID` flag. The javadoc at `Collectors.java:232-235` says "no guarantees on the type"; a future release may add a finisher exactly as `toUnmodifiableList` did, and this becomes a `ClassCastException`.

**Right**

```java
ArrayList<String> names = people.stream()
        .map(Person::name)
        .collect(Collectors.toCollection(ArrayList::new));
names.trimToSize();
```

`toCollection` takes the supplier from you, so the type is yours by contract, not by luck.

**Why people believe it:** it has been an `ArrayList` since Java 8, every blog post says so, and the identity-finish design means it is *very* likely to stay one. Likely is not specified.

### Assuming `Stream.toList()` and `Collectors.toUnmodifiableList()` are interchangeable

**Wrong**

```java
List<String> vals = keys.stream()
        .map(lookup::get)          // may return null
        .collect(Collectors.toUnmodifiableList());
```

Throws `NullPointerException` from the collector's finisher the moment one key is missing, with a stack trace that points at the collector rather than the missing key.

**Right**

```java
List<String> vals = keys.stream()
        .map(lookup::get)
        .toList();                 // ListN with allowNulls == true
System.out.println(vals.contains(null));   // legal question, answers honestly
```

Or, if a null genuinely is a bug, keep `toUnmodifiableList()` and let it fail fast — but choose deliberately.

**Why people believe it:** both are described as "unmodifiable list", and the null difference is a one-clause aside in the javadoc rather than a difference in the method name.

### Expecting `EnumSet.copyOf` to give you an immutable set

**Wrong**

```java
EnumSet<Day> weekend = EnumSet.of(Day.SAT, Day.SUN);
public EnumSet<Day> weekend() { return EnumSet.copyOf(weekend); }
```

The caller receives a fully mutable `RegularEnumSet`. Independent of your field, yes — so the field is safe — but "copyOf" reads like `List.copyOf` and a reader will assume the *result* is frozen and pass it on.

**Right**

```java
private static final Set<Day> WEEKEND =
        Collections.unmodifiableSet(EnumSet.of(Day.SAT, Day.SUN));
public Set<Day> weekend() { return WEEKEND; }
```

One allocation ever, and `add` throws.

**Why people believe it:** `List.copyOf`, `Set.copyOf` and `Map.copyOf` (Java 10) all return immutable results, and `EnumSet.copyOf` (Java 5) predates that convention by five releases.

### Calling `Map.entry(k, v)` on data that may be null

**Wrong**

```java
List<Map.Entry<String, String>> pairs = keys.stream()
        .map(k -> Map.entry(k, config.get(k)))
        .toList();
```

`KeyValueHolder`'s constructor runs `Objects.requireNonNull` on **both** arguments (`KeyValueHolder.java:61-62`), so one missing config key throws inside the `map` at entry-construction time. The top of the stack trace is `Objects.requireNonNull` and the offending key appears nowhere in the message — a rejection at construction, not on read.

**Right**

```java
List<Map.Entry<String, String>> pairs = keys.stream()
        .map(k -> new AbstractMap.SimpleImmutableEntry<>(k, config.get(k)))
        .toList();
```

`SimpleImmutableEntry` (Java 6) is immutable *and* null-tolerant *and* serializable — per the entry-type table above, the only one of the four that is all three. If a null value really is a bug, keep `Map.entry` and let it fail fast, but filter first so the message names the key: `.filter(k -> config.get(k) != null)`.

**Why people believe it:** `Map.entry` is the modern-looking API, and `HashMap` tolerates both null keys and null values — so the entry type feels like it should inherit that tolerance. It does not; it inherits `List.of`'s null-hostility instead.

---

## Cheat sheet

| | Immutable | Nulls | Serializable | Concrete type (JDK 21) |
|---|---|---|---|---|
| `Map.entry(k,v)` (9) | yes | **rejected at construction** | **no** | `java.util.KeyValueHolder` (final) |
| `new SimpleEntry(k,v)` (1.6) | no — `setValue` writes own field only | allowed | yes | `AbstractMap$SimpleEntry` |
| `new SimpleImmutableEntry(k,v)` (1.6) | yes | allowed | yes | `AbstractMap$SimpleImmutableEntry` |
| `Map.Entry.copyOf(e)` (17) | yes | rejected | no | `KeyValueHolder`; same instance **only if** arg already is one |
| `HashMap` entry from iterator | no — writes through | allowed | no | `HashMap$Node` |
| `Stream.toList()` (16) | yes | **allowed** | yes | `ImmutableCollections$ListN`, always |
| `collect(toList())` (8) | **no** | allowed | yes today | `ArrayList` — **unspecified by contract** |
| `collect(toUnmodifiableList())` (10) | yes | **rejected (NPE)** | yes | `List12` (≤2) / `ListN` (≥3) |
| `collect(toCollection(ArrayList::new))` | no | allowed | yes | `ArrayList` — **by contract** |
| `EnumSet.copyOf` / `.clone()` (5) | **no — mutable** | n/a | yes | same class as source |

Fast facts: `EnumSet.copyOf(nonEmptyEnumSet)` = O(1) `clone`; `EnumSet.copyOf(plainCollection)` = O(n), and **`IllegalArgumentException` if empty**. `COWIterator` fields: `private final Object[] snapshot` + `int cursor`; `remove`/`set`/`add` all throw `UnsupportedOperationException`; no `modCount`, so no `ConcurrentModificationException`. `List.of() != Stream.empty().toList()` though they are `equals`. `RegularEnumSet` ≤ 64 constants (one `long`), `JumboEnumSet` > 64 (`long[]`, clone overridden to un-share it).

---

## Self-test

**Q1.** `Map.Entry.copyOf` is documented to avoid copying when the argument is already immutable. Why does it copy an `AbstractMap.SimpleImmutableEntry`?

<details><summary>Answer</summary>

Because the guard at `Map.java:628` is `if (e instanceof KeyValueHolder)`, not a test for immutability in general. `SimpleImmutableEntry` is immutable but is a different class, so it falls to line 631 and gets boxed into a fresh `KeyValueHolder`. The javadoc is precisely worded and does not overpromise — `Map.java:614-616` says only that entries "obtained from a call to `copyOf` or `Map::entry`" avoid the copy. Verified: `copyOf(simpleImmutableEntry) == simpleImmutableEntry` is `false`.

</details>

**Q2.** Why can a `COWIterator` never throw `ConcurrentModificationException`, and why must its `remove()` throw?

<details><summary>Answer</summary>

It captures the backing array once into `private final Object[] snapshot` (`CopyOnWriteArrayList.java:1163, 1169`) and holds no reference to the list and no `expectedModCount`. Every list mutation installs a *new* array, so the captured one is never written to — there is no inconsistency to detect, hence no fail-fast check. `remove()` must throw (line 1207) because there is no coherent target: writing into `snapshot` would mutate an array the list may no longer own, and writing into the list's current array would desynchronise the remaining elements of the iteration.

</details>

**Q3.** `EnumSet.copyOf(someList)` throws `IllegalArgumentException`. Same call on `EnumSet.noneOf(Day.class)` does not. Why?

<details><summary>Answer</summary>

`EnumSet` stores a `Class<E>` alongside its bitmask; a plain `Collection` does not. The `Collection` overload (`EnumSet.java:172-185`) recovers the enum type from the first element via `EnumSet.of(first)` on line 180, so an empty non-`EnumSet` collection leaves it with no type to work from — lines 176–177 throw `IllegalArgumentException("Collection is empty")` rather than fail later. An empty `EnumSet` already carries its type, so line 173's `instanceof` sends it to `clone()`, which copies the type field and the empty bitmask. Corollary trap: `Collections.unmodifiableSet(emptyEnumSet)` is not an `EnumSet`, so it takes the throwing branch.

</details>

**Q4.** Which of `Stream.toList()`, `collect(toList())`, `collect(toUnmodifiableList())` accept a stream containing null, and which are contractually guaranteed to?

<details><summary>Answer</summary>

`Stream.toList()` accepts nulls **and is specified to** — it builds a `ListN` through `listFromTrustedArrayNullsAllowed` with `allowNulls == true`, and `ListN.contains` skips its null guard when that flag is set (`ImmutableCollections.java:722`). `collect(toList())` accepts nulls today because it is a bare `ArrayList`, but the javadoc guarantees nothing about the returned list at all. `collect(toUnmodifiableList())` throws `NullPointerException` from its finisher (`Collectors.java:263-270`), which routes through `listFromTrustedArray` — the null-hostile `List.of` path — and that rejection is specified.

</details>

**Q5.** `List.of() == Stream.empty().toList()` is `false` while `.equals()` is `true`. What is the practical consequence?

<details><summary>Answer</summary>

They are two distinct canonical instances: `EMPTY_LIST` with `allowNulls == false` and `EMPTY_LIST_NULLS` with `allowNulls == true`. So `List.of().contains(null)` throws `NullPointerException` while `Stream.empty().toList().contains(null)` returns `false`. Any code doing `contains(null)` — or `remove(null)`, or `indexOf(null)` — on a possibly-empty immutable list has behaviour that depends on which factory produced it, even though both lists are empty, immutable, `ListN`, and `equals`.

</details>

**Q6.** Why does `JumboEnumSet` override `clone()` when `RegularEnumSet` does not?

<details><summary>Answer</summary>

`EnumSet.clone()` (line 382) is just `super.clone()` — `Object.clone`, which is shallow. `RegularEnumSet`'s entire mutable state is `private long elements = 0L` (`RegularEnumSet.java:43`), a primitive, so a shallow field copy already yields an independent bitmask. `JumboEnumSet`'s state is `private long elements[]` (line 45), and a shallow copy would share that array — every "copy" would be an alias. So it overrides at lines 370–372 to do `result.elements = result.elements.clone()`. Without that one line, `EnumSet.copyOf` would be silently broken for every enum with more than 64 constants.

</details>

**Q7.** A colleague replaces `collect(Collectors.toList())` with `.toList()` across the codebase. Name three ways this can break, and say why the compiler will not warn you.

<details><summary>Answer</summary>

(1) Any later `add`/`set`/`sort`/`removeIf`/`Collections.shuffle` on the result throws `UnsupportedOperationException`, possibly far from the collection site. (2) A cast to `ArrayList`, or a `getClass()` comparison, throws `ClassCastException` — verified: `(ArrayList<String>) Stream.of("x","y").toList()` throws. (3) `List.copyOf(result)` stops returning the same instance, because `listCopy`'s guard is `coll instanceof ListN<?> c && !c.allowNulls` (`ImmutableCollections.java:169`) and `toList()`'s `ListN` has `allowNulls == true` — so a copy is allocated where none was before. The compiler is silent because both expressions have static type `List<T>`; every difference is in the runtime class, and the runtime class of `Collectors.toList()` was never part of its contract to begin with.

</details>

---

**Leaves covered:** 2.3.20–2.3.24 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-61 (rendered as a Markdown table)
**Target version:** Java 21 LTS
**Lines:** 693
