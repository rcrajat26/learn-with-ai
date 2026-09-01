# 02 Java Collections — Interview, INTERNALS tier — predict-the-output puzzles (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [92b-interview-internals-b-questions-19-36.md](92b-interview-internals-b-questions-19-36.md) · Next: [92d-interview-internals-d-atomic-concept-checklist.md](92d-interview-internals-d-atomic-concept-checklist.md)

Five puzzles at INTERNALS depth. Four of them read private `java.util` fields by reflection,
because that is the only honest way to *show* a table length, a threshold or a bin's node class —
the alternative is asserting it. The flat atomic concept checklist that closes the set is in
[92d](92d-interview-internals-d-atomic-concept-checklist.md).

**Every transcript on this page was produced by compiling and running the exact code shown.**
Toolchain: `javac`/`java` 21.0.7+8-LTS-245 (`/Library/Java/JavaVirtualMachines/jdk-21.jdk`),
Apple M4 Pro, arm64, `-Xlint:all`, zero warnings, zero errors. All five are run with
`--add-opens java.base/java.util=ALL-UNNAMED`, and puzzle 1 with `-Xmx2g` because it builds a
million-entry map:

```
javac -Xlint:all -d out <File>.java
java --add-opens java.base/java.util=ALL-UNNAMED -cp out <File>
```

**One line of one transcript is not deterministic and is marked as such**: the `Set.of` iteration
order in puzzle 5 is salted per JVM start, so the published value is one instance and the *invariant*
is printed on the line below it (items 46 and 75 of the index's open-questions log). Every other line
on this page is byte-identical across runs. No wall-clock figure appears anywhere, which is what
makes that true.

## Puzzle 1 — what does a million-entry `HashMap<Integer,Integer>` cost? (§5.1.40)

```java
// MapBytes.java

import java.lang.reflect.Field;
import java.util.*;

public class MapBytes {
    static final int N = 1_000_000;

    public static void main(String[] args) throws Exception {
        Map<Integer, Integer> map = new HashMap<>();
        for (int i = 0; i < N; i++) {
            map.put(i, i);
        }

        int tableLen = tableLength(map);
        int threshold = threshold(map);
        System.out.println("entries         = " + map.size());
        System.out.println("table.length    = " + tableLen + " (2^" + Integer.numberOfTrailingZeros(tableLen) + ")");
        System.out.println("threshold       = " + threshold);
        System.out.println("resizes so far  = " + (Integer.numberOfTrailingZeros(tableLen) - 4));

        long nodes = 32L * N;
        long boxes = 16L * (N - 128) * 2 + 0;   // -128..127 are shared cache instances
        long table = 4L * tableLen + 16;
        System.out.println("nodes  32 B x N = " + nodes + " B");
        System.out.println("boxes  16 B x 2 = " + boxes + " B (the 256 cached Integers are shared)");
        System.out.println("table  4 B/slot = " + table + " B");
        System.out.println("total           = " + (nodes + boxes + table) + " B = "
                + ((nodes + boxes + table) / (1024 * 1024)) + " MiB");
        System.out.println("per entry       = " + ((nodes + boxes + table) / N) + " B for 8 B of payload");

        long intArrays = 2L * (4L * N + 16);
        System.out.println("two int[N]      = " + intArrays + " B = " + (intArrays / (1024 * 1024)) + " MiB");
        System.out.println("ratio           = " + (10 * (nodes + boxes + table) / intArrays) / 10.0 + "x");

        System.out.println("Integer cache:  valueOf(127) == valueOf(127) ? "
                + (Integer.valueOf(127) == Integer.valueOf(127))
                + " ; valueOf(128) == valueOf(128) ? "
                + (Integer.valueOf(128) == Integer.valueOf(128)));

        map.clear();
        System.out.println("after clear():  size=" + map.size()
                + " table.length=" + tableLength(map) + " threshold=" + threshold(map));
    }

    static int tableLength(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] t = (Object[]) f.get(map);
        return t == null ? -1 : t.length;
    }

    static int threshold(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("threshold");
        f.setAccessible(true);
        return f.getInt(map);
    }
}
```

<details><summary>Output and why</summary>

```
entries         = 1000000
table.length    = 2097152 (2^21)
threshold       = 1572864
resizes so far  = 17
nodes  32 B x N = 32000000 B
boxes  16 B x 2 = 31995904 B (the 256 cached Integers are shared)
table  4 B/slot = 8388624 B
total           = 72384528 B = 69 MiB
per entry       = 72 B for 8 B of payload
two int[N]      = 8000032 B = 7 MiB
ratio           = 9.0x
Integer cache:  valueOf(127) == valueOf(127) ? true ; valueOf(128) == valueOf(128) ? false
after clear():  size=0 table.length=2097152 threshold=1572864
```

**The table is 2²¹ = 2,097,152 slots for a million entries — 2.1 slots per entry, not 1.33.**
That is the number people get wrong. Load factor 0.75 implies `1M / 0.75 = 1,333,334` slots, but the
capacity must be a power of two, so it rounds up to 2²¹ and the array is **57% larger** than the load
factor suggests. Seventeen resizes got it there from 16.

**So the per-entry cost is about 72 bytes here, where the idealised figure is 69.** The idealised
number assumes the ideal 1.33 slots per entry (`4 / 0.75 ≈ 5.33` bytes of slot); the real table at
this `n` gives 8.39 bytes of slot. Both numbers are right for what they measure, and knowing why they
differ is the better answer: **the table array's cost depends on where `n` falls relative to a power
of two.** At `n` just above 2²⁰ × 0.75 you pay for a table nearly twice as big as you need.

**Where the 72 bytes go:** a 32-byte `Node` (12-byte header + cached `hash` + key ref + value ref +
`next` ref = 28, padded), plus two 16-byte `Integer` boxes, plus the slot. Only 256 of those boxes
are shared — `Integer.valueOf` caches `−128..127`, which the last-but-one line demonstrates — so at a
million entries the cache is a rounding error.

**Nine times the memory of two `int[]` arrays holding the same data**, which is the sentence to
deliver. For a map keyed and valued by `int`, the answer to "how do I make this smaller" is a
primitive-specialised map (fastutil, Eclipse Collections) or parallel arrays, not tuning the load
factor.

**And `clear()` freed nothing structural**: `size` went to 0, the 8 MB reference array stayed, and so
did the threshold. Iterating that map is now O(capacity) over two million empty slots.

</details>

## Puzzle 2 — what Java 21 actually changed (§5.1.41)

```java
// Sequenced.java

import java.util.*;

public class Sequenced {
    public static void main(String[] args) {
        List<String> list = new ArrayList<>(List.of("A", "B", "C"));
        List<String> view = list.reversed();
        System.out.println("list=" + list + " view=" + view);
        System.out.println("view.getClass()=" + view.getClass().getName());
        System.out.println("view.reversed() == list ? " + (view.reversed() == list));

        view.addFirst("X");
        System.out.println("after view.addFirst(\"X\"): list=" + list + " view=" + view);
        view.add("Y");
        System.out.println("after view.add(\"Y\"):      list=" + list + " view=" + view);

        SequencedMap<String, Integer> lhm = new LinkedHashMap<>();
        lhm.put("a", 1);
        lhm.put("b", 2);
        lhm.put("c", 3);
        System.out.println("lhm keys=" + lhm.keySet()
                + " firstEntry=" + lhm.firstEntry() + " lastEntry=" + lhm.lastEntry());
        lhm.putFirst("c", 30);
        System.out.println("after putFirst(\"c\", 30): " + lhm);
        System.out.println("firstEntry().getClass()=" + lhm.firstEntry().getClass().getName());
        try {
            lhm.firstEntry().setValue(99);
        } catch (UnsupportedOperationException e) {
            System.out.println("firstEntry().setValue -> UnsupportedOperationException");
        }
        System.out.println("lhm.reversed() == lhm.reversed() ? " + (lhm.reversed() == lhm.reversed()));
        System.out.println("lhm.reversed().reversed() == lhm ? " + (lhm.reversed().reversed() == lhm));

        Map<String, Integer> lru = new LinkedHashMap<>(16, 0.75f, true);
        lru.put("a", 1);
        lru.put("b", 2);
        lru.put("c", 3);
        lru.get("a");
        System.out.println("access-order after get(a):    " + lru.keySet());
        ((SequencedMap<String, Integer>) lru).putFirst("a", 1);
        System.out.println("access-order after putFirst(a): " + lru.keySet() + "  <- least recent now");

        NavigableMap<String, Integer> tm = new TreeMap<>(Map.of("a", 1, "b", 2));
        System.out.println("treemap=" + tm + " firstEntry=" + tm.firstEntry());
        try {
            tm.putFirst("z", 9);
        } catch (UnsupportedOperationException e) {
            System.out.println("TreeMap.putFirst -> UnsupportedOperationException");
        }
        System.out.println("tm.reversed() == tm.descendingMap() ? " + (tm.reversed() == tm.descendingMap()));
        System.out.println("tm.descendingMap() == tm.descendingMap() ? "
                + (tm.descendingMap() == tm.descendingMap()));
        System.out.println("tm.descendingMap().descendingMap() == tm ? "
                + (tm.descendingMap().descendingMap() == tm)
                + " ; .equals(tm) ? " + tm.descendingMap().descendingMap().equals(tm));

        SequencedSet<String> lhs = new LinkedHashSet<>(List.of("p", "q", "r"));
        System.out.println("lhs.getFirst=" + lhs.getFirst() + " lhs.reversed()=" + lhs.reversed());
        Deque<String> dq = new ArrayDeque<>(List.of("1", "2"));
        System.out.println("Deque is a SequencedCollection ? " + (dq instanceof SequencedCollection));
        System.out.println("HashSet is a SequencedCollection ? "
                + (new HashSet<String>() instanceof SequencedCollection));
    }
}
```

<details><summary>Output and why</summary>

```
list=[A, B, C] view=[C, B, A]
view.getClass()=java.util.ReverseOrderListView$Rand
view.reversed() == list ? true
after view.addFirst("X"): list=[A, B, C, X] view=[X, C, B, A]
after view.add("Y"):      list=[Y, A, B, C, X] view=[X, C, B, A, Y]
lhm keys=[a, b, c] firstEntry=a=1 lastEntry=c=3
after putFirst("c", 30): {c=30, a=1, b=2}
firstEntry().getClass()=jdk.internal.util.NullableKeyValueHolder
firstEntry().setValue -> UnsupportedOperationException
lhm.reversed() == lhm.reversed() ? false
lhm.reversed().reversed() == lhm ? true
access-order after get(a):    [b, c, a]
access-order after putFirst(a): [a, b, c]  <- least recent now
treemap={a=1, b=2} firstEntry=a=1
TreeMap.putFirst -> UnsupportedOperationException
tm.reversed() == tm.descendingMap() ? true
tm.descendingMap() == tm.descendingMap() ? true
tm.descendingMap().descendingMap() == tm ? false ; .equals(tm) ? true
lhs.getFirst=p lhs.reversed()=[r, q, p]
Deque is a SequencedCollection ? true
HashSet is a SequencedCollection ? false
```

**`addFirst` on the reversed view appends to the source.** `view.addFirst("X")` gave
`list=[A, B, C, X]` — "first" in the view is "last" in the source, and the view is live, so the write
lands at the source's tail. A plain `view.add("Y")` appends to the view and therefore lands at the
source's **front**. Both are correct and both surprise people; the class name,
`ReverseOrderListView$Rand`, tells you the `Rand` subclass preserves `RandomAccess`.

**Double reversal is identity for a `List` and for `LinkedHashMap`** — `view.reversed() == list` and
`lhm.reversed().reversed() == lhm` are both `true`, because the view's `reversed()` returns its base
by identity (`LinkedHashMap.java:1224` is literally `return base;`, and
`ReverseOrderListView.of` unwraps). But `lhm.reversed() == lhm.reversed()` is **`false`**: the view
itself is not cached, so every call allocates one.

**`TreeMap` is the exception on every line.** `putFirst` throws
`UnsupportedOperationException`, because a comparator decides position and the caller does not.
`reversed()` **is** `descendingMap()` and *that* is one-slot cached — so
`descendingMap() == descendingMap()` is `true` — but `descendingMap().descendingMap()` builds a fresh
`AscendingSubMap`, so it is `equals` to the original and **not `==`**. Three different identity
answers on one class.

**`firstEntry()` is not a live entry.** `LinkedHashMap` does not override the `SequencedMap`
defaults, so `firstEntry()` returns a `jdk.internal.util.NullableKeyValueHolder` — an unmodifiable
snapshot whose `setValue` throws. If you need to write through, use
`map.entrySet().iterator().next()`.

**And the line that costs people money in production:** on an **access-order** map,
`putFirst(k, v)` moves the key to the *head*, which is the **eviction** end. After
`get("a")` the order was `[b, c, a]` with `a` newest; after `putFirst("a", 1)` it is `[a, b, c]` with
`a` oldest. So a "keep hot keys at the front" refactor on an LRU marks them for eviction first.

</details>

## Puzzle 3 — four collection leak shapes (§5.1.47)

```java
// LeakShapes.java

import java.lang.reflect.Field;
import java.util.*;

public class LeakShapes {

    static final class BadKey {
        final String name;
        int version;

        BadKey(String name, int version) {
            this.name = name;
            this.version = version;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof BadKey b && b.name.equals(name) && b.version == version;
        }

        @Override
        public int hashCode() {
            return Objects.hash(name, version);   // reads a MUTABLE field
        }
    }

    public static void main(String[] args) throws Exception {
        // Shape 1: a map that grew and was cleared
        Map<Integer, Integer> grown = new HashMap<>();
        for (int i = 0; i < 200_000; i++) {
            grown.put(i, i);
        }
        System.out.println("shape 1: grown        size=" + grown.size()
                + " table=" + tableLength(grown));
        grown.clear();
        System.out.println("shape 1: after clear  size=" + grown.size()
                + " table=" + tableLength(grown) + "  <- array retained");
        int slots = tableLength(grown);
        System.out.println("shape 1: retained     " + (4L * slots + 16) + " B of references for 0 entries");

        // Shape 2: a mutated key
        Map<BadKey, String> byKey = new HashMap<>();
        BadKey k = new BadKey("config", 1);
        byKey.put(k, "payload");
        System.out.println("shape 2: get before mutation = " + byKey.get(k));
        k.version = 2;                                  // hashed field changes
        System.out.println("shape 2: get after mutation  = " + byKey.get(k));
        System.out.println("shape 2: containsKey(k)      = " + byKey.containsKey(k));
        System.out.println("shape 2: remove(k)           = " + byKey.remove(k));
        System.out.println("shape 2: size                = " + byKey.size()
                + " ; visible to iteration = " + byKey.values());

        // Shape 3: the map-of-empty-lists shape
        Map<Integer, List<String>> multimap = new HashMap<>();
        for (int i = 0; i < 3; i++) {
            multimap.computeIfAbsent(i, x -> new ArrayList<>()).add("v");
            multimap.get(i).clear();                    // drained, but the list object stays
        }
        System.out.println("shape 3: keys=" + multimap.size()
                + " every value empty? " + multimap.values().stream().allMatch(List::isEmpty));
        System.out.println("shape 3: cost per key = 32 B Node + 4 B slot + 24 B empty ArrayList shell");

        // Shape 4: a subList pinning its parent
        List<Integer> parent = new ArrayList<>();
        for (int i = 0; i < 500_000; i++) {
            parent.add(i);
        }
        List<Integer> window = parent.subList(0, 10);
        System.out.println("shape 4: window.size=" + window.size()
                + " window.getClass=" + window.getClass().getName());
        System.out.println("shape 4: pins the parent's Object[" + 500_000 + "] = "
                + (4L * 500_000 + 16) + " B");
        List<Integer> detached = List.copyOf(window);
        System.out.println("shape 4: List.copyOf(window).getClass=" + detached.getClass().getName()
                + " -> parent now collectable");
    }

    static int tableLength(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] t = (Object[]) f.get(map);
        return t == null ? -1 : t.length;
    }
}
```

<details><summary>Output and why</summary>

```
shape 1: grown        size=200000 table=524288
shape 1: after clear  size=0 table=524288  <- array retained
shape 1: retained     2097168 B of references for 0 entries
shape 2: get before mutation = payload
shape 2: get after mutation  = null
shape 2: containsKey(k)      = false
shape 2: remove(k)           = null
shape 2: size                = 1 ; visible to iteration = [payload]
shape 3: keys=3 every value empty? true
shape 3: cost per key = 32 B Node + 4 B slot + 24 B empty ArrayList shell
shape 4: window.size=10 window.getClass=java.util.ArrayList$SubList
shape 4: pins the parent's Object[500000] = 2000016 B
shape 4: List.copyOf(window).getClass=java.util.ImmutableCollections$ListN -> parent now collectable
```

Four shapes, and each has a distinct signature in a heap dump.

**Shape 1 — the retained table.** `clear()` set `size` to 0 and kept a 524,288-slot array: 2 MB of
references for zero entries. In MAT this is `collection_fill_ratio` near 0. The fix is to replace the
map object, not to clear it — `map = HashMap.newHashMap(expected)`.

**Shape 2 — the mutated key, and it is the nastiest because the map lies about it.** After mutating a
field that `hashCode` reads, `get` returns `null`, `containsKey` is `false` and `remove` returns
`null` — but `size()` is still 1 and iteration still shows the value. The entry is
**unreachable by key and fully alive**, so no amount of "remove it when we're done" code can ever
clean it up. In MAT the signature is a growing map whose `map_collision_ratio` may look fine; the
tell is that `size()` disagrees with what your own bookkeeping expects.

**Shape 3 — the map of empty collections.** Three keys, all values drained, and each key still costs
a 32-byte `Node`, a table slot, and a 24-byte `ArrayList` shell. At a million keys that is roughly
144 bytes per key against about 48 for a flat `Map<K,V>`. MAT's
`collections_grouped_by_size` query finds it immediately: a huge count of size-0 collections.

**Shape 4 — the tiny view pinning a big array.** A 10-element `SubList` keeps the parent's
500,000-element `Object[]` — 2 MB — reachable, because its only fields are `root`, `offset` and
`size`. `List.copyOf(window)` produces a `ListN` holding ten references and the parent becomes
collectable. This is the one that shows up as "why is this cache 4 GB": a small object at the top of
the dominator tree with an enormous retained size.

**The workflow to state alongside the shapes:** `jcmd <pid> GC.heap_dump`, then in MAT the dominator
tree by retained heap, `collection_fill_ratio` for shape 1, `collections_grouped_by_size` for shape
3, `map_collision_ratio` for a broken `hashCode`, and JOL if you need exact bytes for one object.

</details>

## Puzzle 4 — when does a bin actually become a tree?

```java
// Treeify.java

import java.lang.reflect.Field;
import java.util.*;

public class Treeify {

    /** Every instance collides: one bin, forever. */
    static final class Collide implements Comparable<Collide> {
        final int id;

        Collide(int id) {
            this.id = id;
        }

        @Override
        public int hashCode() {
            return 42;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Collide c && c.id == id;
        }

        @Override
        public int compareTo(Collide other) {
            return Integer.compare(id, other.id);
        }
    }

    /** Identical, minus Comparable. */
    static final class CollideNC {
        final int id;

        CollideNC(int id) {
            this.id = id;
        }

        @Override
        public int hashCode() {
            return 42;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof CollideNC c && c.id == id;
        }
    }

    public static void main(String[] args) throws Exception {
        System.out.println("default-sized map, Comparable keys:");
        report(new HashMap<Collide, String>(), i -> new Collide(i), 12);

        System.out.println("pre-sized to 64 slots, Comparable keys:");
        report(new HashMap<Collide, String>(64), i -> new Collide(i), 12);

        System.out.println("pre-sized to 64 slots, NON-Comparable keys:");
        report(new HashMap<CollideNC, String>(64), i -> new CollideNC(i), 12);
    }

    static <K> void report(Map<K, String> map, java.util.function.IntFunction<K> keys, int upTo)
            throws Exception {
        String firstTree = null;
        int firstTreeAt = -1;
        for (int i = 1; i <= upTo; i++) {
            map.put(keys.apply(i), "v" + i);
            String cls = binHeadClass(map);
            if (firstTree == null && cls != null && cls.contains("TreeNode")) {
                firstTree = cls;
                firstTreeAt = i;
            }
        }
        System.out.println("  table.length after " + upTo + " puts = " + tableLength(map));
        System.out.println("  bin head class            = " + binHeadClass(map));
        System.out.println("  first TreeNode at entry # = " + firstTreeAt);
        System.out.println();
    }

    static int tableLength(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] t = (Object[]) f.get(map);
        return t == null ? -1 : t.length;
    }

    static String binHeadClass(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] t = (Object[]) f.get(map);
        if (t == null) {
            return null;
        }
        for (Object o : t) {
            if (o != null) {
                return o.getClass().getName();
            }
        }
        return null;
    }
}
```

<details><summary>Output and why</summary>

```
default-sized map, Comparable keys:
  table.length after 12 puts = 64
  bin head class            = java.util.HashMap$TreeNode
  first TreeNode at entry # = 11

pre-sized to 64 slots, Comparable keys:
  table.length after 12 puts = 64
  bin head class            = java.util.HashMap$TreeNode
  first TreeNode at entry # = 9

pre-sized to 64 slots, NON-Comparable keys:
  table.length after 12 puts = 64
  bin head class            = java.util.HashMap$TreeNode
  first TreeNode at entry # = 9

```

**Nine, not eight — and eleven if the map started at its default size.** Both numbers fall out of
two mechanisms most answers collapse into one.

The **nine** comes from `binCount`, which counts `next` hops from an already-rejected head (the
source comment on the test is `// -1 for 1st`), and the test
`binCount >= TREEIFY_THRESHOLD - 1` is evaluated after the new node is linked. Eight existing nodes
plus the newcomer.

The **eleven** comes from `MIN_TREEIFY_CAPACITY = 64`. A default map starts with a 16-slot table, so
when the bin hits nine nodes `treeifyBin` sees `tab.length < 64`, calls `resize()` and treeifies
**nothing**. That happens twice — 16→32 at the 9th insert, 32→64 at the 10th — and the tree finally
appears at the 11th. Pre-size the map to 64 slots and it treeifies at the 9th, exactly as the
constants suggest.

**The third block is the trap that matters.** Non-`Comparable` keys treeify at the 9th insert too —
the bin head is a `TreeNode` all the same. Treeification is **not** conditional on `Comparable`; only
its *benefit* is. `putTreeVal` orders such keys with `tieBreakOrder` (class name, then
`System.identityHashCode`), which is not an order a lookup key shares, so `TreeNode.find` must search
both subtrees. Measured elsewhere in this set at 20,000 identical-hash keys: a plain chain 312 ms, a
treeified `Comparable` bin 2.06 ms, a treeified non-`Comparable` bin **529 ms — worse than no tree at
all**. So "does it treeify?" and "does treeifying help?" are two different questions, and this
transcript answers the first `yes` for both key types.

**What you cannot see from the class name alone:** whether the tree is balanced usefully. That is why
the `Comparable` screen (`comparableClassFor`, requiring the class to declare
`implements Comparable<Self>` directly) is the fact to quote rather than the node type.

</details>

## Puzzle 5 — which iteration orders are real?

```java
// OrderIllusion.java

import java.lang.reflect.Field;
import java.util.*;

public class OrderIllusion {
    public static void main(String[] args) throws Exception {
        Map<Integer, String> small = new HashMap<>();
        for (int i = 0; i < 10; i++) {
            small.put(i, "v" + i);
        }
        System.out.println("keys 0..9      : " + small.keySet() + "  (looks sorted)");
        System.out.println("table.length   : " + tableLength(small));

        small.put(100, "v100");
        small.put(-1, "v-1");
        System.out.println("plus 100 and -1: " + small.keySet() + "  (illusion broken)");
        System.out.println("slot of 100    : " + slotOf(100, tableLength(small)));
        System.out.println("slot of -1     : " + slotOf(-1, tableLength(small)));
        System.out.println("spread(-1)     : " + spread(-1));

        Map<Integer, String> resized = new HashMap<>();
        for (int i = 0; i < 12; i++) {
            resized.put(i, "v" + i);
        }
        System.out.println("12 keys, table=" + tableLength(resized) + " order=" + resized.keySet());
        resized.put(12, "v12");
        System.out.println("13 keys, table=" + tableLength(resized) + " order=" + resized.keySet());

        Set<String> immutable = Set.of("a", "b", "c", "d", "e", "f");
        Set<String> again = Set.of("a", "b", "c", "d", "e", "f");
        System.out.println("Set.of order (VARIES per run): " + immutable);
        System.out.println("invariant: sorted contents   : " + immutable.stream().sorted().toList());
        System.out.println("same order twice in one JVM? : " + immutable.toString().equals(again.toString()));
        System.out.println("contains(\"d\") both          : " + immutable.contains("d") + " " + again.contains("d"));
        System.out.println("equals despite order         : " + immutable.equals(again));

        Set<String> hashSet = new LinkedHashSet<>(List.of("a", "b", "c", "d", "e", "f"));
        System.out.println("LinkedHashSet (guaranteed)   : " + hashSet);
        System.out.println("TreeSet (guaranteed)         : " + new TreeSet<>(immutable));
    }

    static int spread(Object key) {
        int h = key.hashCode();
        return h ^ (h >>> 16);
    }

    static int slotOf(Object key, int tableLength) {
        return (tableLength - 1) & spread(key);
    }

    static int tableLength(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] t = (Object[]) f.get(map);
        return t == null ? -1 : t.length;
    }
}
```

<details><summary>Output and why</summary>

```
keys 0..9      : [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  (looks sorted)
table.length   : 16
plus 100 and -1: [0, -1, 1, 2, 3, 4, 100, 5, 6, 7, 8, 9]  (illusion broken)
slot of 100    : 4
slot of -1     : 0
spread(-1)     : -65536
12 keys, table=16 order=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
13 keys, table=32 order=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
Set.of order (VARIES per run): [b, c, d, e, f, a]
invariant: sorted contents   : [a, b, c, d, e, f]
same order twice in one JVM? : true
contains("d") both          : true true
equals despite order         : true
LinkedHashSet (guaranteed)   : [a, b, c, d, e, f]
TreeSet (guaranteed)         : [a, b, c, d, e, f]
```

**The `Set.of` line is the one non-deterministic line on this page, and it is deliberately here.**
Three consecutive runs of this exact program on this exact JDK printed `[f, e, d, c, b, a]`,
`[a, b, c, d, e, f]` and `[b, c, d, e, f, a]` — three different orders, while **every other line was
byte-identical**. `ImmutableCollections` initialises `SALT32L` from `System.nanoTime()` at class load
and its `SetN`/`MapN` iterators use it to choose a starting slot and a direction, precisely to break
code that came to depend on order. The invariant, printed on the next line, is the contents; the
order is not a fact about the program.

Note what does **not** vary: `contains("d")` is `true` in both sets in every run, because `probe`
placement and lookup are entirely unsalted. Only iteration is salted.

**Why small `Integer` keys look sorted, and where the illusion dies.** `Integer.hashCode()` is the
value; `h ^ (h >>> 16)` is the identity below 65,536; and `v & (n − 1) == v` while `v` is below the
capacity. So keys 0–9 in a 16-slot table land in slots 0–9 and iteration reads them in order. Add
100 and it lands in **slot 4** (`100 & 15`), landing between 3 and 5. Add −1 and `spread(-1)` is
`-65536`, whose low four bits are 0, so it lands in **slot 0** — before key 0's own chain position.
That is the entire mechanism behind "my `HashMap` was sorted and then it wasn't".

**A resize rearranges everything.** The 12-key map (table 16) and the 13-key map (table 32) both
happen to print in ascending order here, because these keys are all below 16 and each one either
stays at `j` or moves to `j + 16` — but keys that shared a slot before now interleave differently,
and with non-trivial keys the order changes wholesale. `HashMap` order is deterministic per JDK build
and key set, unspecified by contract, and rearranged by every resize.

**The two guaranteed orders are the last two lines**: `LinkedHashSet` (encounter order) and
`TreeSet` (comparator order). If your test asserts on order, one of those is the type you should be
holding.

</details>

## Cheat sheet

| Fact | Value |
|---|---|
| Table for 1M entries at 0.75 | `2^21` = 2,097,152 slots — **2.1 slots/entry**, not 1.33 |
| Why | capacity must be a power of two, and `1M / 0.75 = 1.33M` rounds up |
| `HashMap<Integer,Integer>` per entry | ~72 B measured at n = 10⁶; ~69 B at the idealised 1.33 slots/entry |
| Versus two `int[]` | ~9× the memory |
| `Integer` cache | `−128..127` shared; `valueOf(127) == valueOf(127)` true, `128` false |
| `clear()` on a grown map | keeps the array **and** the threshold |
| `list.reversed()` class | `java.util.ReverseOrderListView$Rand` |
| `view.addFirst(x)` | lands at the **source's tail**; `view.add(x)` lands at its front |
| Double reversal | identity for `List` and `LinkedHashMap`; the view itself is **not** cached |
| `TreeMap.putFirst` | `UnsupportedOperationException` |
| `tm.reversed() == tm.descendingMap()` | `true`, and `descendingMap()` is one-slot cached |
| `tm.descendingMap().descendingMap()` | `equals` but **not** `==` — a fresh `AscendingSubMap` |
| `LinkedHashMap.firstEntry()` | `jdk.internal.util.NullableKeyValueHolder`; `setValue` throws |
| `putFirst` on an access-order map | moves the key to the **eviction** end |
| Mutated key | `get`/`containsKey`/`remove` all miss; `size()` and iteration still show it |
| Map of drained lists | ~144 B/key against ~48 B for a flat map |
| `SubList` retention | 3 fields pin the whole parent array; `List.copyOf` detaches |
| First `TreeNode`, default-sized map | entry **11** (16→32 at 9, 32→64 at 10, tree at 11) |
| First `TreeNode`, pre-sized to 64 | entry **9** |
| Non-`Comparable` keys | **still treeify** at 9 — only the benefit is conditional |
| Small `Integer` keys look sorted because | `hashCode` is the value, spread is identity below 65,536, `v & (n−1) == v` |
| Where it breaks | `100 & 15 = 4`; `spread(-1) = -65536` → slot 0 |
| `Set.of` iteration order | salted from `System.nanoTime()` per JVM run — iterators only |
| `Set.of` lookup | unsalted and fully deterministic |
| Guaranteed orders | `LinkedHashSet` (encounter), `TreeSet` (comparator) |

## Self-test

**Q1.** A `HashMap` holds 1,000,000 entries. How big is the table, and why is it not 1,333,334?

<details><summary>Answer</summary>

2²¹ = 2,097,152 slots. The load factor implies `ceil(1M / 0.75) = 1,333,334`, but capacity must be a
power of two — `hash & (n − 1)` depends on it — so `tableSizeFor` rounds up to the next power, 2²¹.
The array is therefore about 57% larger than the load factor suggests, and the real per-entry table
cost is 8.39 bytes rather than the idealised 5.33. Where `n` falls relative to a power of two is the
single biggest lever on a large map's array cost, and it is why "tune the load factor" is usually the
wrong answer to a memory problem — at n = 1,000 and n = 1,000,000, load factors 0.5 and 0.75 produce
the *same* table size.

</details>

**Q2.** After `clear()`, a `HashMap` reports `size() == 0` and iterating it is still slow. Why?

<details><summary>Answer</summary>

Because iteration is O(capacity + size), and `clear()` does not touch the capacity. `HashIterator`
scans the table from slot 0 looking for a non-null head, so an empty map in a 524,288-slot table
walks half a million slots to produce nothing. The array and the `threshold` are both retained; the
only method that nulls `table` is the package-private `reinitialize()`, called from `clone()` and
`readObject()`. Replace the map object to reclaim it.

</details>

**Q3.** Your LRU cache got slower and its hit rate dropped after someone added
`cache.putFirst(hotKey, value)` to "prioritise" hot keys. Explain.

<details><summary>Answer</summary>

`putFirst` moves the entry to the **head** of the encounter order, and on an access-order
`LinkedHashMap` the head is the *least* recently used end — the one `removeEldestEntry` evicts from.
So every "prioritised" key was marked for immediate eviction. The transcript shows it: after
`get("a")` the order is `[b, c, a]` with `a` newest; after `putFirst("a", 1)` it is `[a, b, c]` with
`a` oldest. Mechanically, `putFirst` sets `putMode = PUT_FIRST`, which bypasses the `accessOrder`
conjunct in `afterNodeAccess`'s guard and relinks to the head instead of the tail. On an
*insertion*-order map `putFirst` is harmless and useful; on an access-order map it is an
anti-optimisation. Worse, `putFirst` of an *absent* key on a full LRU inserts at the head and
immediately self-evicts, returning `null` and leaving the map unchanged.

</details>

**Q4.** A colleague pre-sizes a map to 64 slots specifically so that a colliding-key bin will
treeify "and get the O(log n) protection". Their keys are a custom class with `equals` and
`hashCode` but no `Comparable`. What actually happens?

<details><summary>Answer</summary>

The bin treeifies exactly as they expect — the transcript confirms a `HashMap$TreeNode` head at the
9th insert for non-`Comparable` keys — and it does not protect them. `putTreeVal` can only use
`compareTo` when `comparableClassFor(key)` returns non-null, which requires the class to declare
`implements Comparable<Self>` directly; otherwise it orders nodes by `tieBreakOrder`, i.e. class name
then `System.identityHashCode`. A lookup key does not share that ordering, so `TreeNode.find` searches
the left subtree and then recurses into the right as well. Measured at 20,000 identical-hash keys:
312 ms for a plain chain, 2.06 ms treeified with `Comparable` keys, and 529 ms treeified without —
so the "protection" is *worse than no tree*. Implement `Comparable` on the key, or fix the
`hashCode`.

</details>

**Q5.** Which of these can you safely assert on in a unit test: `HashMap.keySet()` order,
`Set.of(...)` order, `LinkedHashSet` order, `TreeSet` order?

<details><summary>Answer</summary>

Only the last two. `LinkedHashSet` guarantees encounter order and `TreeSet` guarantees comparator
order; both are specified. `HashMap.keySet()` order is *deterministic* for a given JDK build and key
set but **unspecified** — it changes on every resize, on a different key set, and potentially on a
JDK upgrade, so a passing assertion is luck with a long fuse. `Set.of(...)` is actively worse: its
iteration order is salted from `System.nanoTime()` per JVM start, so the same test passes and fails
on alternate runs. Assert on contents (`assertEquals(Set.of(...), actual)`) or impose an order
(`actual.stream().sorted().toList()`).

</details>

---

**Leaves covered:** 5.1.40, 5.1.41, 5.1.47 (3 leaves)
**Leaves deferred:** none — leaf 5.3.8, the flat atomic concept checklist, moved to
[92d-interview-internals-d-atomic-concept-checklist.md](92d-interview-internals-d-atomic-concept-checklist.md) when this row was split; see
`## Folds recorded` in the index
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 784
