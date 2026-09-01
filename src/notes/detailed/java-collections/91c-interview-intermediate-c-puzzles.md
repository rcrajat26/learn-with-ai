# 02 Java Collections — Interview, INTERMEDIATE tier — predict-the-output puzzles (§5.1)

**Target version: Java 21 LTS.** | [Index](00-index.md)
Previous: [91b-interview-intermediate-b-questions-19-36.md](91b-interview-intermediate-b-questions-19-36.md) · Next: [92-interview-internals.md](92-interview-internals.md)

Five puzzles at INTERMEDIATE depth. These are design questions in disguise: each one is a
mechanism you would be asked to *build* on a whiteboard, reduced to a program whose output you
should be able to predict.

**Every transcript on this page was produced by compiling and running the exact code shown.**
Toolchain: `javac`/`java` 21.0.7+8-LTS-245 (`/Library/Java/JavaVirtualMachines/jdk-21.jdk`),
Apple M4 Pro, arm64, `-Xlint:all`, zero warnings, zero errors. Puzzle 1 reads private `HashMap`
fields, so it is run with
`java --add-opens java.base/java.util=ALL-UNNAMED -cp out Sizing`; the other four need no flags.
No wall-clock figure appears anywhere on this page, which is what makes every line reproducible.

## Puzzle 1 — what capacity did you actually ask for? (§5.1.44)

```java
// Sizing.java

import java.lang.reflect.Field;
import java.util.*;

public class Sizing {
    public static void main(String[] args) throws Exception {
        System.out.println("new HashMap<>()             " + report(new HashMap<>(), 0));
        System.out.println("new HashMap<>(100)          " + report(new HashMap<>(100), 0));
        System.out.println("HashMap.newHashMap(100)     " + report(HashMap.newHashMap(100), 0));
        System.out.println("new HashMap<>(100) + 100    " + report(new HashMap<>(100), 100));
        System.out.println("newHashMap(100)    + 100    " + report(HashMap.newHashMap(100), 100));

        Map<Integer, Integer> m = new HashMap<>(100);
        int resizedAt = -1;
        int previous = -1;
        for (int i = 0; i < 200; i++) {
            m.put(i, i);
            int len = tableLength(m);
            if (previous != -1 && len != previous) {
                resizedAt = i + 1;
                break;
            }
            previous = len;
        }
        System.out.println("new HashMap<>(100) resizes on insert #" + resizedAt);

        int folk = (int) (100 / 0.75f) + 1;
        System.out.println("folk formula for 100 = " + folk + "  " + report(new HashMap<>(folk), 0));

        int folk6144 = (int) (6144 / 0.75f) + 1;
        System.out.println("n=6144 newHashMap           " + report(HashMap.newHashMap(6144), 1));
        System.out.println("n=6144 folk (" + folk6144 + ")         " + report(new HashMap<>(folk6144), 1));
    }

    static String report(Map<Integer, Integer> map, int fill) throws Exception {
        for (int i = 0; i < fill; i++) {
            map.put(i, i);
        }
        int len = tableLength(map);
        return "table=" + (len == -1 ? "null" : Integer.toString(len))
                + " threshold=" + threshold(map) + " size=" + map.size();
    }

    static int tableLength(Map<?, ?> map) throws Exception {
        Field f = HashMap.class.getDeclaredField("table");
        f.setAccessible(true);
        Object[] table = (Object[]) f.get(map);
        return table == null ? -1 : table.length;
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
new HashMap<>()             table=null threshold=0 size=0
new HashMap<>(100)          table=null threshold=128 size=0
HashMap.newHashMap(100)     table=null threshold=256 size=0
new HashMap<>(100) + 100    table=256 threshold=192 size=100
newHashMap(100)    + 100    table=256 threshold=192 size=100
new HashMap<>(100) resizes on insert #97
folk formula for 100 = 134  table=null threshold=256 size=0
n=6144 newHashMap           table=8192 threshold=6144 size=1
n=6144 folk (8193)         table=16384 threshold=12288 size=1
```

**Nothing is allocated until the first `put`.** All three constructors leave `table == null`. The
`threshold` field is doing double duty: while `table` is null it holds the *pending capacity*, and
once the table exists it holds the resize threshold. That is why `new HashMap<>(100)` shows
`threshold=128` — `tableSizeFor(100)` rounded up to a power of two — and then `threshold=192` after
the table exists (256 × 0.75).

**`new HashMap<>(100)` does not hold 100 entries.** It asks for a 128-slot table, which resizes when
size exceeds 96. The program measures it: **the resize happens on insert #97.** So the argument is a
capacity, not a count, and the map you asked to hold 100 things rehashes before it gets there.

**`HashMap.newHashMap(100)` is the fix (Java 19+).** It computes
`(int) Math.ceil(100 / 0.75d) = 134`, which `tableSizeFor` rounds to 256, so 100 entries fit with no
resize. Both maps end at `table=256` after 100 inserts — but the first one got there by rehashing
128 entries' worth of table, and the second never resized.

**The folk formula is usually right and sometimes exactly wrong.** `(int)(n / 0.75f) + 1` gives 134
for n = 100, identical to `newHashMap`. But at `n = 3 × 2^k` it tips over a power-of-two boundary:
for n = 6144 it produces 8193, which rounds up to a **16,384**-slot table where 8,192 was
sufficient — twice the array for nothing. `newHashMap` gets it right because `Math.ceil` in
`double` does not overshoot the way `+ 1` does.

**The one-line answer to the interview question:** `HashMap.newHashMap(n)` on Java 19+, or
`new HashMap<>((int) (n / 0.75f) + 1)` before it — and never `new HashMap<>(n)`. The same
`newXxx` factory exists for `LinkedHashMap`, `HashSet` and `LinkedHashSet`, all four delegating to
`calculateHashMapCapacity`. There is no `newTreeMap`, no `newArrayList`, and no
`newConcurrentHashMap`.

</details>

## Puzzle 2 — O(1) insert, delete, and getRandom (§5.1.45)

```java
// RandomizedSet.java

import java.util.*;

public class RandomizedSet<E> {
    private final List<E> values = new ArrayList<>();
    private final Map<E, Integer> index = new HashMap<>();
    private final Random random;

    public RandomizedSet(long seed) {
        this.random = new Random(seed);
    }

    public boolean add(E e) {
        if (index.containsKey(e)) {
            return false;
        }
        index.put(e, values.size());
        values.add(e);
        return true;
    }

    public boolean remove(E e) {
        Integer i = index.remove(e);
        if (i == null) {
            return false;
        }
        int last = values.size() - 1;
        E moved = values.get(last);
        values.set(i, moved);            // overwrite the hole with the last element
        if (!moved.equals(e)) {
            index.put(moved, i);         // and tell the map where it went
        }
        values.remove(last);             // O(1): removing the tail copies nothing
        return true;
    }

    public E getRandom() {
        return values.get(random.nextInt(values.size()));
    }

    public int size() {
        return values.size();
    }

    List<E> layout() {
        return List.copyOf(values);
    }

    public static void main(String[] args) {
        RandomizedSet<String> s = new RandomizedSet<>(42L);
        for (String v : List.of("a", "b", "c", "d", "e")) {
            s.add(v);
        }
        System.out.println("after adds:        " + s.layout());
        System.out.println("add duplicate \"c\": " + s.add("c"));

        System.out.println("remove(\"b\"):       " + s.remove("b") + " layout=" + s.layout());
        System.out.println("remove(\"zz\"):      " + s.remove("zz"));
        System.out.println("remove(last \"c\"):  " + s.remove("c") + " layout=" + s.layout());

        StringJoiner draws = new StringJoiner(" ");
        for (int i = 0; i < 8; i++) {
            draws.add(s.getRandom());
        }
        System.out.println("8 draws, seed 42:  " + draws);
        System.out.println("size:              " + s.size());
    }
}
```

<details><summary>Output and why</summary>

```
after adds:        [a, b, c, d, e]
add duplicate "c": false
remove("b"):       true layout=[a, e, c, d]
remove("zz"):      false
remove(last "c"):  true layout=[a, e, d]
8 draws, seed 42:  d a a d a e d d
size:              3
```

**The whole design is the `remove` method, and the output shows why.** `getRandom` needs a dense
array so it can pick an index; `remove` needs O(1), but removing from the middle of an `ArrayList`
is O(n). The resolution is **swap with the last element**: overwrite the hole with the tail, update
the map to say where the tail went, then remove the tail — which is the one `ArrayList` removal that
copies nothing.

That is exactly what `remove("b")` printed: `[a, b, c, d, e]` became `[a, e, c, d]`. `"b"` was at
index 1, `"e"` was the tail, `"e"` moved into index 1, and the array shrank. **Order is destroyed —
that is the price, and it is fine, because a set has no order to preserve.**

**The `if (!moved.equals(e))` guard is the bug everyone writes.** When you remove the element that
*is* the tail, `moved` and `e` are the same object; without the guard you would re-insert the key you
just removed, and `index` would name a slot that no longer exists. The transcript's third removal
exercises exactly that path: after the second removal, `"c"` sits at index 2 of `[a, e, c, d]`… but
the tail is `"d"`, so this is still the general case, and `"d"` moves into `"c"`'s slot giving
`[a, e, d]`. Try it with `remove("d")` instead and the guard is what saves you.

**The draws are reproducible, not arbitrary.** `new Random(42)` is a specified linear congruential
generator, so `d a a d a e d d` is the same on any JVM — which is the only reason a random-looking
line can appear in a transcript at all. Note the repeats: eight draws with replacement from three
elements. If the interviewer asks for *distinct* random elements you need a different structure, or
a partial Fisher-Yates shuffle.

**Costs to state out loud:** `add`, `remove` and `getRandom` are all O(1) expected — `add` amortised
by `ArrayList`, `remove` because it never shifts, `getRandom` because the array is dense. Memory is
roughly `HashMap` entry plus one array slot per element, so about 36 bytes per element on top of the
elements themselves.

</details>

## Puzzle 3 — a rate limiter and a tier lookup, both on `TreeMap` (§5.1.46)

```java
// RateLimiter.java

import java.util.*;

public class RateLimiter {
    private final NavigableMap<Long, Integer> hits = new TreeMap<>();
    private final long windowMillis;
    private final int limit;

    RateLimiter(long windowMillis, int limit) {
        this.windowMillis = windowMillis;
        this.limit = limit;
    }

    boolean allow(long nowMillis) {
        hits.headMap(nowMillis - windowMillis, false).clear();   // evict the whole prefix
        int inWindow = 0;
        for (int c : hits.values()) {
            inWindow += c;
        }
        if (inWindow >= limit) {
            return false;
        }
        hits.merge(nowMillis, 1, Integer::sum);
        return true;
    }

    int distinctTimestamps() {
        return hits.size();
    }

    public static void main(String[] args) {
        RateLimiter limiter = new RateLimiter(1000, 3);
        long[] arrivals = {0, 100, 100, 500, 900, 1050, 1600, 1600, 1600};
        for (long t : arrivals) {
            System.out.println("t=" + t + " allow=" + limiter.allow(t)
                    + " buckets=" + limiter.distinctTimestamps());
        }

        NavigableMap<Integer, String> tiers = new TreeMap<>();
        tiers.put(0, "free");
        tiers.put(100, "bronze");
        tiers.put(1000, "silver");
        tiers.put(10000, "gold");
        for (int spend : new int[] {0, 99, 100, 5000, 10000, 999999}) {
            System.out.println("spend=" + spend + " tier=" + tiers.floorEntry(spend).getValue());
        }
        System.out.println("ceiling(101)=" + tiers.ceilingKey(101)
                + " higher(1000)=" + tiers.higherKey(1000)
                + " lower(0)=" + tiers.lowerKey(0));

        NavigableMap<Integer, String> window = new TreeMap<>(tiers);
        System.out.println("headMap(1000) = " + window.headMap(1000));
        System.out.println("headMap(1000).remove(10000) = " + window.headMap(1000).remove(10000)
                + " ; key 10000 still present? " + window.containsKey(10000));
        try {
            window.headMap(1000).put(10000, "platinum");
        } catch (IllegalArgumentException e) {
            System.out.println("headMap(1000).put(10000, \"platinum\") -> IllegalArgumentException: "
                    + e.getMessage());
        }
    }
}
```

<details><summary>Output and why</summary>

```
t=0 allow=true buckets=1
t=100 allow=true buckets=2
t=100 allow=true buckets=2
t=500 allow=false buckets=2
t=900 allow=false buckets=2
t=1050 allow=true buckets=2
t=1600 allow=true buckets=2
t=1600 allow=true buckets=2
t=1600 allow=false buckets=2
spend=0 tier=free
spend=99 tier=free
spend=100 tier=bronze
spend=5000 tier=silver
spend=10000 tier=gold
spend=999999 tier=gold
ceiling(101)=1000 higher(1000)=10000 lower(0)=null
headMap(1000) = {0=free, 100=bronze}
headMap(1000).remove(10000) = null ; key 10000 still present? true
headMap(1000).put(10000, "platinum") -> IllegalArgumentException: key out of range
```

**The rate limiter is three `NavigableMap` operations and nothing else.**
`headMap(now - window, false).clear()` deletes every timestamp older than the window in one
range-delete through a live view — that is the operation no other `java.util` map can perform.
`merge(now, 1, Integer::sum)` counts arrivals that share a millisecond, which is why the second
`t=100` does not create a new bucket and `buckets` stays at 2. Trace it: at `t=500` the window
holds three hits (one at 0, two at 100), so the limit of 3 is reached and the call is refused; at
`t=1050` the entry at 0 has aged out, leaving two, so it is allowed again.

**Two design notes worth saying.** This is a *sliding* window, not a fixed one, so it does not have
the burst-at-the-boundary problem a per-second counter has. And the summing loop is O(k) over
distinct timestamps in the window; if that mattered you would keep a running total, but then you
must decrement it in `clear()`, which is exactly the "two structures must be updated together" bug
from the LRU question.

**`floorEntry` is the tier lookup, and the boundaries are the point.** `spend=99` is `free` and
`spend=100` is `bronze`, because `floor` includes the exact match. This is also the "as-of"
time-series pattern: `floorEntry(timestamp)` gives you the last value at or before that instant.
`lower(0)` is `null` because `lower` is strict and 0 is the smallest key — always null-check the
strict variants at the ends.

**The last three lines are the range-view trap, and they are asymmetric.** Through `headMap(1000)`:
`remove(10000)` returns `null` and **leaves key 10000 alive in the source map**, while
`put(10000, ...)` throws `IllegalArgumentException: key out of range`. So a range view enforces its
bounds on writes and silently ignores them on reads and removals. A caller who trusts `remove` to
report failure keeps the entry forever, and nothing in the syllabus's usual "range views throw"
summary warns you about the quiet half.

</details>

## Puzzle 4 — what a `Spliterator` promises (§5.1.49)

```java
// Splits.java

import java.util.*;
import java.util.stream.*;

public class Splits {
    public static void main(String[] args) {
        List<Integer> arrayList = IntStream.range(0, 1000).boxed()
                .collect(Collectors.toCollection(ArrayList::new));
        List<Integer> linkedList = new LinkedList<>(arrayList);

        describe("ArrayList ", arrayList.spliterator());
        describe("LinkedList", linkedList.spliterator());
        describe("HashSet   ", new HashSet<>(arrayList).spliterator());
        describe("TreeSet   ", new TreeSet<>(arrayList).spliterator());
        describe("List.of   ", List.copyOf(arrayList).spliterator());

        Spliterator<Integer> s = arrayList.spliterator();
        Spliterator<Integer> left = s.trySplit();
        System.out.println("ArrayList split: left=" + left.estimateSize()
                + " right=" + s.estimateSize());
        System.out.println("left is a prefix? first=" + first(left));

        Spliterator<Integer> t = linkedList.spliterator();
        Spliterator<Integer> tl = t.trySplit();
        System.out.println("LinkedList split: left=" + tl.estimateSize()
                + " right=" + t.estimateSize() + " (BATCH_UNIT = 1024, so one batch took all)");

        Spliterator<Integer> leaf = List.of(7).spliterator();
        System.out.println("single-element trySplit() returns " + leaf.trySplit());

        System.out.println("SIZED=" + Spliterator.SIZED
                + " SUBSIZED=" + Spliterator.SUBSIZED
                + " ORDERED=" + Spliterator.ORDERED
                + " DISTINCT=" + Spliterator.DISTINCT
                + " SORTED=" + Spliterator.SORTED
                + " IMMUTABLE=" + Spliterator.IMMUTABLE);

        System.out.println("sequential sum  = " + arrayList.stream()
                .mapToInt(Integer::intValue).sum());
        System.out.println("parallel sum    = " + arrayList.parallelStream()
                .mapToInt(Integer::intValue).sum());
        System.out.println("parallel forEach is unordered, forEachOrdered is not:");
        System.out.print("  forEachOrdered:");
        List.of(1, 2, 3, 4, 5).parallelStream().forEachOrdered(i -> System.out.print(" " + i));
        System.out.println();
    }

    static void describe(String label, Spliterator<Integer> sp) {
        System.out.println(label + " estimateSize=" + sp.estimateSize()
                + " SIZED=" + sp.hasCharacteristics(Spliterator.SIZED)
                + " SUBSIZED=" + sp.hasCharacteristics(Spliterator.SUBSIZED)
                + " ORDERED=" + sp.hasCharacteristics(Spliterator.ORDERED)
                + " SORTED=" + sp.hasCharacteristics(Spliterator.SORTED)
                + " IMMUTABLE=" + sp.hasCharacteristics(Spliterator.IMMUTABLE));
    }

    static Integer first(Spliterator<Integer> sp) {
        Integer[] holder = new Integer[1];
        sp.tryAdvance(v -> holder[0] = v);
        return holder[0];
    }
}
```

<details><summary>Output and why</summary>

```
ArrayList  estimateSize=1000 SIZED=true SUBSIZED=true ORDERED=true SORTED=false IMMUTABLE=false
LinkedList estimateSize=1000 SIZED=true SUBSIZED=true ORDERED=true SORTED=false IMMUTABLE=false
HashSet    estimateSize=1000 SIZED=true SUBSIZED=false ORDERED=false SORTED=false IMMUTABLE=false
TreeSet    estimateSize=1000 SIZED=true SUBSIZED=false ORDERED=true SORTED=true IMMUTABLE=false
List.of    estimateSize=1000 SIZED=true SUBSIZED=true ORDERED=true SORTED=false IMMUTABLE=false
ArrayList split: left=500 right=500
left is a prefix? first=0
LinkedList split: left=1000 right=0 (BATCH_UNIT = 1024, so one batch took all)
single-element trySplit() returns null
SIZED=64 SUBSIZED=16384 ORDERED=16 DISTINCT=1 SORTED=4 IMMUTABLE=1024
sequential sum  = 499500
parallel sum    = 499500
parallel forEach is unordered, forEachOrdered is not:
  forEachOrdered: 1 2 3 4 5
```

**`trySplit` returns the left half and keeps the right.** `ArrayList` splits at
`(lo + hi) >>> 1` in constant time — no elements move — and `first(left)` printing `0` confirms the
returned half is a *prefix*. That is the contract: the two halves must be disjoint, and together
they must cover exactly what the original covered.

**The `LinkedList` line is the whole lesson about parallel streams.** Both halves report a size, but
`left=1000, right=0`: `LinkedList`'s spliterator cannot index, so `trySplit` *walks* the list and
copies a prefix into an `Object[]`, sized `BATCH_UNIT = 1024` and growing per call. A
1,000-element list is smaller than the first batch, so the first split takes everything and the
"parallel" stream has one chunk and no parallelism at all. On a larger list each split costs a walk.
This is why `linkedList.parallelStream()` is reliably slower than the sequential version, and why
the decision rule for parallelism is *large N × high per-element cost Q, **and** a cheap split*.

**`SUBSIZED` is the characteristic worth memorising.** `SIZED` says "I know my size";
`SUBSIZED` says "and so will both halves after a split" — which is what lets fork/join pre-size its
output arrays. `ArrayList` and `List.of` have it; `HashSet` and `TreeSet` do not, because a split by
table-index range cannot promise how many elements each range holds.

**Two surprises in that table.** `LinkedList` *does* advertise `SUBSIZED` in JDK 21, even though its
split is O(n) — the characteristic is about knowing sizes, not about the split being cheap. And
`List.of(...)`'s spliterator reports `IMMUTABLE=false`, because `AbstractImmutableList` does not
override `spliterator()`; the default `List.spliterator()` builds one with
`Spliterator.ORDERED` and the framework adds `SIZED | SUBSIZED`, so the immutability the class
actually has is never advertised.

**`trySplit` returning `null` means "stop splitting"** — it is the leaf signal, not an error, and a
one-element spliterator gives it immediately.

**And the last two lines:** parallel and sequential sums agree because addition is associative,
which is the real precondition for a parallel reduction. `forEachOrdered` re-imposes encounter
order at a cost; plain `forEach` on a parallel stream is explicitly unordered, which is why it is
not used here — an unordered transcript could not be published as an expected output.

</details>

## Puzzle 5 — `computeIfAbsent` and the null-means-remove family (§5.1.50)

```java
// ComputeIfAbsent.java

import java.util.*;
import java.util.concurrent.*;

public class ComputeIfAbsent {
    public static void main(String[] args) {
        Map<String, List<String>> multimap = new HashMap<>();
        multimap.computeIfAbsent("fruit", k -> new ArrayList<>()).add("apple");
        multimap.computeIfAbsent("fruit", k -> new ArrayList<>()).add("pear");
        System.out.println("multimap: " + multimap);

        Map<String, String> m = new HashMap<>();
        System.out.println("computeIfAbsent -> null: " + m.computeIfAbsent("a", k -> null)
                + " map=" + m + " containsKey=" + m.containsKey("a"));

        m.put("b", "1");
        System.out.println("compute -> null:         " + m.compute("b", (k, v) -> null)
                + " map=" + m + " containsKey=" + m.containsKey("b"));

        m.put("c", "1");
        System.out.println("merge -> null:           " + m.merge("c", "2", (o, n) -> null)
                + " map=" + m);
        System.out.println("merge on absent key:     " + m.merge("d", "seed", (o, n) -> "never")
                + " map=" + m);

        Map<String, String> nulls = new HashMap<>();
        nulls.put("k", null);
        System.out.println("getOrDefault over a stored null: " + nulls.getOrDefault("k", "dflt")
                + " containsKey=" + nulls.containsKey("k"));
        System.out.println("putIfAbsent over a stored null:  " + nulls.putIfAbsent("k", "v")
                + " map=" + nulls);

        Map<String, String> hm = new HashMap<>();
        try {
            hm.computeIfAbsent("x", k -> {
                hm.put("y", "added from inside");
                return "x-value";
            });
            System.out.println("HashMap recursive update: no exception, map=" + hm);
        } catch (ConcurrentModificationException e) {
            System.out.println("HashMap recursive update: ConcurrentModificationException, map=" + hm);
        }

        Map<String, String> chm = new ConcurrentHashMap<>();
        chm.computeIfAbsent("alpha", k -> {
            chm.put("beta", "2");
            return "1";
        });
        System.out.println("CHM different bin: succeeded, map=" + new TreeMap<>(chm));

        Map<String, String> chm2 = new ConcurrentHashMap<>();
        try {
            chm2.computeIfAbsent("k", k -> chm2.computeIfAbsent("k", k2 -> "inner"));
            System.out.println("CHM same key: no exception");
        } catch (IllegalStateException e) {
            System.out.println("CHM same key: " + e);
        }

        Map<String, String> lru = new LinkedHashMap<>(16, 0.75f, true);
        lru.put("a", "1");
        lru.put("b", "2");
        lru.put("c", "3");
        lru.computeIfAbsent("a", k -> "never called");
        System.out.println("access-order after computeIfAbsent(\"a\"): " + lru.keySet());
        lru.containsKey("b");
        System.out.println("access-order after containsKey(\"b\"):     " + lru.keySet());
    }
}
```

<details><summary>Output and why</summary>

```
multimap: {fruit=[apple, pear]}
computeIfAbsent -> null: null map={} containsKey=false
compute -> null:         null map={} containsKey=false
merge -> null:           null map={}
merge on absent key:     seed map={d=seed}
getOrDefault over a stored null: null containsKey=true
putIfAbsent over a stored null:  null map={k=v}
HashMap recursive update: ConcurrentModificationException, map={y=added from inside}
CHM different bin: succeeded, map={alpha=1, beta=2}
CHM same key: java.lang.IllegalStateException: Recursive update
access-order after computeIfAbsent("a"): [b, c, a]
access-order after containsKey("b"):     [b, c, a]
```

**The multimap idiom, first.** `computeIfAbsent(k, x -> new ArrayList<>()).add(v)` returns the
value — existing or freshly computed — so the `.add` lands in the right list either way, with one
hash lookup instead of the `containsKey`/`get`/`put` trio. The mapping function is not called on the
second line, because `"fruit"` is present.

**`null` means different things to different methods, and the transcript sorts them out.**
`computeIfAbsent` returning `null` inserts nothing — the key is still absent. `compute` and `merge`
returning `null` **remove** the entry, which is how you write "decrement, and drop at zero" in one
call. And `merge` on an *absent* key stores the given value **without calling the function at all**,
which is why `merge(k, 1, Integer::sum)` is the counter idiom rather than `compute`.

**"Absent" means no *value*, not no *key*.** With `"k"` mapped to `null`, `getOrDefault` returns the
stored `null` rather than the default — the default is only for an absent key — and `putIfAbsent`
**overwrites** it, returning `null`. That pair is the reason `containsKey` still has a job.

**Recursive update gives three different failures, and this is the interview-grade part.** On a
plain `HashMap`, mutating the map from inside the mapping function throws
`ConcurrentModificationException` — and note the map: `{y=added from inside}`. The inner `put`
persisted and `"x"` was never inserted, so the exception is not a rollback. On a
`ConcurrentHashMap`, inserting a key that lands in a **different** bin **succeeds** — and is still a
documented contract violation ("must not attempt to update any other mappings of this map"), so it
is a latent bug that happens to work. Re-entering on the **same** key throws
`IllegalStateException: Recursive update`, deterministically, on one thread: `computeIfAbsent` on an
empty bin installs a `ReservationNode` and holds its monitor, and a re-entrant call landing on a
reserved bin is detected and thrown. **It does not deadlock** — the folklore is wrong, because
`synchronized` is reentrant, which is exactly why the single-thread case cannot self-block. A
genuine deadlock needs two threads each holding one bin's monitor and needing the other's, and that
is constructible but not deterministically demonstrable.

**The last two lines cost people offers.** On an access-order `LinkedHashMap`,
`computeIfAbsent("a")` on an **already-present** key computes nothing — and still relinks `"a"` to
the most-recent end, giving `[b, c, a]`. `containsKey("b")` does not relink, so the order is
unchanged. `afterNodeAccess` has eight call sites in JDK 21's `HashMap`, and `putIfAbsent` (via
`putVal`) and `computeIfAbsent` are two of them; `containsKey`, `forEach`, iteration and
`Entry.setValue` are not. So the set of operations that count as an "access" is wider than the
javadoc's `get`/`getOrDefault` suggests.

</details>

## Pitfalls

### Using `compute` where you meant `merge`

**Wrong**

```java
Map<String, Integer> counts = new HashMap<>();
counts.compute(key, (k, v) -> v + 1);        // NullPointerException on the first occurrence
```

`v` is `null` for an absent key, and `null + 1` unboxes to an NPE.

**Right**

```java
Map<String, Integer> counts = new HashMap<>();
counts.merge(key, 1, Integer::sum);          // stores 1 when absent, sums when present
```

**Why people believe it:** `compute` reads like the general-purpose one, and it is — but its
function is called with a `null` second argument for an absent key, so every `compute` needs a null
branch. `merge` has the absent case built in and never calls the function for it.

### Reasoning about `HashMap` capacity from the constructor argument

**Wrong**

```java
Map<String, String> m = new HashMap<>(1_000_000);   // "no resizes"
```

It resizes when size exceeds 786,432 — the argument is a capacity, rounded up to `1 << 20`, and the
threshold is 75% of that.

**Right**

```java
Map<String, String> m = HashMap.newHashMap(1_000_000);   // Java 19+; ceil(n / 0.75)
```

**Why people believe it:** `new ArrayList<>(n)` really does mean "room for n". `HashMap` is the
outlier, which is precisely why Java 19 added the `newHashMap`/`newLinkedHashMap`/`newHashSet`/
`newLinkedHashSet` factories that take the count you actually mean.

## Cheat sheet

| Puzzle shape | What it prints | The rule |
|---|---|---|
| `new HashMap<>()`, before any `put` | `table=null threshold=0` | lazy allocation; `threshold` holds the pending capacity |
| `new HashMap<>(100)` | `threshold=128`, resizes on insert **#97** | the argument is a capacity, not a count |
| `HashMap.newHashMap(100)` | `threshold=256`, no resize at 100 | `ceil(n / 0.75)` then `tableSizeFor` |
| folk formula at `n = 3·2^k` | 6144 → 16384-slot table | `+ 1` tips over a power-of-two boundary |
| Sized factories that exist | `HashMap`, `LinkedHashMap`, `HashSet`, `LinkedHashSet` (all `@since 19`) | no `newTreeMap`, no `newArrayList` |
| O(1) insert/delete/getRandom | `ArrayList` + `HashMap<E,Integer>` index | remove = swap with the tail, then drop the tail |
| Removing the tail element itself | needs an `if (!moved.equals(e))` guard | otherwise you re-insert the key you removed |
| `new Random(42)` | `d a a d a e d d` here | specified LCG, so reproducible across JVMs |
| Sliding-window rate limit | `headMap(now - window, false).clear()` | one range-delete through a live view |
| Counting arrivals in the same millisecond | `merge(now, 1, Integer::sum)` | bucket count stays flat |
| Tier / as-of lookup | `floorEntry(probe)` | `floor` includes the exact match; `lower` is strict |
| Range view, out-of-range `put` | `IllegalArgumentException: key out of range` | writes are fenced |
| Range view, out-of-range `remove`/`get` | `null`, silently, source untouched | reads are **not** fenced — the dangerous half |
| `trySplit()` | returns the **left** prefix, keeps the right | halves must be disjoint and cover the whole |
| `ArrayList.trySplit` | 500/500 at `(lo + hi) >>> 1` | O(1), no elements moved |
| `LinkedList.trySplit` on 1000 elements | 1000/0 | copies a prefix, `BATCH_UNIT = 1024` takes it all |
| `trySplit()` on one element | `null` | the leaf signal, not an error |
| `SUBSIZED` | `ArrayList`/`List.of` yes, `HashSet`/`TreeSet` no | "both halves will know their size too" |
| `List.of(...).spliterator()` | `IMMUTABLE=false` | no override; the default builds it with `ORDERED` only |
| Parallel decision rule | large N × high Q **and** a cheap split | `linkedList.parallelStream()` fails the third test |
| `computeIfAbsent` → `null` | inserts nothing | key remains absent |
| `compute`/`merge`/`computeIfPresent` → `null` | **removes** the entry | how "drop at zero" is written |
| `merge` on an absent key | stores the value, function not called | why `merge` is the counter idiom |
| `getOrDefault` over a stored `null` | returns `null` | default is for an absent key only |
| `putIfAbsent` over a stored `null` | **overwrites** it | "absent" means no value, not no key |
| Recursive update on `HashMap` | `ConcurrentModificationException`, inner mutation persists | not a rollback |
| Recursive update on CHM, different bin | **succeeds**, still a contract violation | latent bug that happens to work |
| Recursive update on CHM, same key | `IllegalStateException: Recursive update` | `ReservationNode` detected; it does **not** deadlock |
| Access-order `computeIfAbsent` on a present key | relinks to the most-recent end | 8 `afterNodeAccess` call sites, not 3 |
| Access-order `containsKey` | does not relink | genuine read |

## Self-test

**Q1.** Puzzle 1 shows `new HashMap<>(100)` resizing on insert 97. Derive that number.

<details><summary>Answer</summary>

`tableSizeFor(100)` is 128, the smallest power of two at least 100, and it is parked in `threshold`
while `table` is null. On the first `put` the table is allocated at 128 slots and `threshold`
becomes `128 × 0.75 = 96`. `putVal` resizes when `++size > threshold`, so the insert that makes
size 97 triggers it. The map you asked to "hold 100" therefore rehashes 96 entries on the way there.
`HashMap.newHashMap(100)` computes `ceil(100 / 0.75) = 134`, rounds to 256, and never resizes.

</details>

**Q2.** In puzzle 2, why must `values.remove(last)` come *after* `values.set(i, moved)`?

<details><summary>Answer</summary>

Because the order is what makes the removal O(1). Setting the hole to the tail element first, then
truncating the tail, means the only structural change is removing the *last* index — which for
`ArrayList` copies nothing, it just nulls one slot and decrements `size`. Reverse the two and you
would be removing from the middle, which is an O(n) `arraycopy`, defeating the whole design. It also
keeps the array dense at every step, which `getRandom` depends on: `random.nextInt(size)` is only a
uniform draw if every index in `[0, size)` holds a live element.

</details>

**Q3.** Rewrite the rate limiter to be O(1) per call instead of O(k), and say what new bug you have
introduced.

<details><summary>Answer</summary>

Keep a running `int inWindow` field, increment it on each accepted arrival, and decrement it by the
counts you discard. The catch is that `headMap(...).clear()` no longer tells you what it removed, so
you must walk the evicted prefix yourself before clearing it — or use `pollFirstEntry()` in a loop
while the first key is too old, subtracting each entry's count as you go. The bug you have
introduced is the classic two-structures-must-agree bug: the running total and the map are now
separate state, and any path that removes an entry without adjusting the total silently corrupts
the limiter — the same shape as forgetting `map.remove(victim.key)` in a hand-rolled LRU.

</details>

**Q4.** `linkedList.parallelStream()` on a 5,000,000-element list. Better or worse than sequential,
and why?

<details><summary>Answer</summary>

Almost always worse, and the size does not rescue it. `LinkedList`'s `trySplit` cannot index — it
walks the chain and copies a prefix into an array, so *every* split costs a traversal and an
allocation, and the splits are uneven batches (`BATCH_UNIT = 1024`, growing per call) rather than
halves. On top of that, each element is a separate 24-byte node with no spatial locality, so the
traversal itself is a chain of cache misses. Parallelism pays when N is large **and** the
per-element work Q is high **and** the split is cheap; a `LinkedList` fails the third condition
structurally. Copy to an `ArrayList` first if you genuinely need parallelism.

</details>

**Q5.** A colleague says the fix for the recursive-`computeIfAbsent` CME is to switch to
`ConcurrentHashMap`. Are they right?

<details><summary>Answer</summary>

No — they have changed the failure, not fixed the bug. On a `ConcurrentHashMap` the same code either
throws `IllegalStateException: Recursive update` (when the inner key lands on the same reserved bin)
or *succeeds while still violating the documented contract* (when it lands on a different bin),
which is worse, because it will keep working until a rehash changes which bin a key falls in. The
actual fix is not to mutate the map from inside the mapping function: compute the value first, then
do the puts, or use `merge`/`putAll` after the function returns. Worth knowing that the same mistake
produces three different symptoms — CME on `HashMap`, `IllegalStateException` on
`ConcurrentHashMap`, and a silent race under a synchronized wrapper — which makes it a good
comparison question in its own right.

</details>

---

**Leaves covered:** 5.1.44, 5.1.45, 5.1.46, 5.1.49, 5.1.50 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 771
