# 02 Java Collections — `HashMap` — INTERNALS (§3.6 `HashMap` source walk — sizing, `newHashMap`, `putMapEntries` and load factors)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/04c-internals-d3-collision-dos.md](04c-internals-d3-collision-dos.md) · Next: [hash-map/05a-internals-e1-removal-and-iteration-order.md](05a-internals-e1-removal-and-iteration-order.md)

`new HashMap<>(100)` reads like a request: *make me a map that holds 100 things*. It is not. The argument is a **capacity** — a count of *array slots* — and the map resizes when the number of *entries* passes `capacity × loadFactor`. Two different quantities, separated by a factor of 0.75, and the constructor does not do the conversion for you. Every sizing bug in this file is that one confusion wearing a different hat. Java 19 finally shipped a factory that takes the number you actually have.

---

## 1. The sizing arithmetic, and why `new HashMap<>(n)` is the wrong call

*Leaf 3.6.37 — `[PROVE]` `[NUM]` `[TRAP]`*

**Mental model.** Picture a car park. `initialCapacity` is the number of *painted bays*. The load factor is the occupancy at which the operator decides the park is too congested and builds a second, twice-as-large park next door — moving every car across. You are not asking for 100 cars' worth of parking when you write `new HashMap<>(100)`; you are asking for 100 bays, which under a 0.75 rule congests at 75 cars. Except the operator also rounds the bay count up to a power of two first, so you get 128 bays and congest at 96.

**Why it exists.** The constructor predates any notion that callers might be thinking in entries. It was written for people implementing hash tables, who think in table lengths, and the `(int, float)` overload makes that framing explicit — you hand it a table size and an occupancy rule. The `(int)` overload just fixes the rule at 0.75 and inherits the framing, which is where the confusion enters: the float disappears from the call site, so nothing reminds you it is still being applied.

**When to reach for it.** Essentially never, on Java 19+. `HashMap.newHashMap(n)` (§2 below) is the same allocation with the arithmetic done correctly. Reach for `new HashMap<>(cap, lf)` only when you genuinely mean a table size and a non-default load factor — see §4, and the answer there is also usually "don't".

**How it works — the source walk.**

```java
    public HashMap(int initialCapacity, float loadFactor) {
        if (initialCapacity < 0)
            throw new IllegalArgumentException("Illegal initial capacity: " +
                                               initialCapacity);
        if (initialCapacity > MAXIMUM_CAPACITY)
            initialCapacity = MAXIMUM_CAPACITY;
        if (loadFactor <= 0 || Float.isNaN(loadFactor))
            throw new IllegalArgumentException("Illegal load factor: " +
                                               loadFactor);
        this.loadFactor = loadFactor;
        this.threshold = tableSizeFor(initialCapacity);
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 445 (javadoc elided). (leaf 3.6.37)

Line by line. The negative check rejects `-1` outright. The clamp silently caps at `MAXIMUM_CAPACITY` (`1 << 30`) rather than throwing — ask for two billion and you get 2^30 with no complaint. `loadFactor <= 0 || Float.isNaN(loadFactor)` rejects zero, negatives and `NaN`, but note what it does *not* reject: `2.0f` is a perfectly legal load factor. The last two lines are the whole story. `loadFactor` is stored as given. And `threshold` — the field that everywhere else in the class means *the entry count at which we resize* — is here assigned `tableSizeFor(initialCapacity)`, which is a **capacity**, not a threshold. `tableSizeFor` is leaf 3.6.15 in [`01b-internals-a2-hash-spread-and-sizing.md`](01b-internals-a2-hash-spread-and-sizing.md); the field's dual meaning is leaf 3.6.8 in [`01-internals-a-constants-and-hash.md`](01-internals-a-constants-and-hash.md). No array is allocated here at all.

So for `new HashMap<>(100)`:

- `tableSizeFor(100)` = 128 (next power of two ≥ 100), stored in `threshold`. `table` is still `null`.
- First `put` calls `resize()`. It sees `table == null` and `oldThr = 128 > 0`, so it takes the "initial capacity was placed in threshold" branch: `newCap = 128`, `newThr = (int)(128 * 0.75f) = 96`. Full walk of that branch is leaf 3.6.23 in [`03-internals-c-resize.md`](03-internals-c-resize.md).
- `putVal` resizes on `if (++size > threshold)`. So entry 96 gives `96 > 96 == false` — fine. Entry 97 gives `97 > 96 == true` — **full rehash into a 256-slot table.**

You asked for 100 and got a resize at 97.

![Sizing a HashMap for 100 entries: new HashMap<>(100) gives capacity 128 and threshold 96 so it resizes at the 97th entry, the manual (int)(100 / 0.75f) + 1 gives 134 and therefore capacity 256 with threshold 192, and HashMap.newHashMap(100) does the same arithmetic for you](../diagrams/D-99-sizing-a-hashmap.svg)

**`[NUM]` The manual fix, computed.** `(int)(100 / 0.75f) + 1`: `100 / 0.75f = 133.33333…`, `(int)` truncates to `133`, `+ 1` gives `134`. Then `tableSizeFor(134) = 256` and `threshold = (int)(256 * 0.75f) = 192`. No resize for 100 entries — but 256 slots for 100 entries is a 2.56× array, because the power-of-two rounding took you from a needed 134 straight to 256.

Run it, with reflection on the private fields:

```
--- A. new HashMap<>(100) walked ---
fresh:        table=0 threshold=128
after 1 put:  table=128 threshold=96
after 96:     table=128 threshold=96 size=96
after 97:     table=256 threshold=192 size=97
```

The three approaches side by side, each loaded with exactly 100 entries:

| Call | ctor arg | table after load | threshold | resizes while loading 100 | slots/entry |
|---|---|---|---|---|---|
| `new HashMap<>(100)` | 100 | 256 | 192 | **2** (→128 on first put, →256 at entry 97) | 2.56 |
| `new HashMap<>((int)(100/0.75f)+1)` | 134 | 256 | 192 | 1 (→256 on first put) | 2.56 |
| `HashMap.newHashMap(100)` | 134 | 256 | 192 | 1 (→256 on first put) | 2.56 |

Note the sting: `new HashMap<>(100)` does not even save memory. It ends at the same 256 slots — it just pays a full rehash of 96 nodes to get there.

**`[PROVE]` Is the `+ 1` superstition?** Take `n = 3`: `3 / 0.75f = 4.0` exactly, `(int) 4.0 = 4`, `tableSizeFor(4) = 4`, `threshold = 3`, and `if (++size > threshold)` gives `3 > 3 == false`. Safe without the `+ 1`. So the `+ 1` does nothing there. Does it ever matter? Rather than assert, sweep `n = 1..200` and print every *n* where dropping it changes the capacity or the resize-safety verdict:

```java
static int tableSizeFor(int cap) {                       // copy of the JDK method
    int n = -1 >>> Integer.numberOfLeadingZeros(cap - 1);
    return (n < 0) ? 1 : (n >= 1 << 30) ? 1 << 30 : n + 1;
}
static boolean safe(int c, int n) {                      // does capacity c hold n without resizing?
    int cap = tableSizeFor(Math.max(c, 1));
    return n <= (int)(cap * 0.75f);
}
public static void main(String[] args) {
    int differCap = 0, unsafeWithout = 0, unsafeWith = 0;
    for (int n = 1; n <= 200; n++) {
        int without = (int)(n / 0.75f), with = without + 1;
        if (tableSizeFor(Math.max(without,1)) != tableSizeFor(with)) differCap++;
        if (!safe(without, n)) { unsafeWithout++; System.out.println("resizes without +1: n=" + n); }
        if (!safe(with, n))    unsafeWith++;
    }
    System.out.println("different capacity: " + differCap);
    System.out.println("resize without +1:  " + unsafeWithout + "   with +1: " + unsafeWith);
}
```

Real output:

```
resizes without +1: n=1
resizes without +1: n=2
different capacity: 9
resize without +1:  2   with +1: 0
```

The honest finding: over `n = 1..200` the `+ 1` only rescues **two** values, `n = 1` and `n = 2`. For `n = 1`, `(int)(1/0.75f) = 1`, `tableSizeFor(1) = 1`, `threshold = (int)(1 * 0.75f) = 0`, and `1 > 0` resizes on the very first `put`. It is a real correctness fix, but a marginal one; the `+ 1` is mostly cargo carried forward from JDK 8's own `putMapEntries`, which used the identical `+ 1.0F` idiom (see §3). It costs nothing and occasionally helps, so keep it — but its reputation exceeds its work.

**Gotcha.** A debugger stopped on a freshly constructed `new HashMap<>(100)` shows `threshold = 128` and `table = null`, which reads as "resizes at 128 entries". It does not. At that moment `threshold` is holding a pending capacity, and the real threshold (96) does not exist until the first `put`.

**Pitfall:** *"`new HashMap<>(100)` pre-sizes the map for 100 entries."* **Symptom:** a hot path that pre-sizes conscientiously and still pays a full rehash partway through loading, plus a heap dump showing a table larger than the number you passed. **Fix:** on Java 19+, `HashMap.newHashMap(100)`. Before 19, `new HashMap<>((int)(n / 0.75f) + 1)`.

> **Definition.** `HashMap`'s `initialCapacity` argument is the requested *table length*, rounded up to a power of two and parked in `threshold` until the first `put`; the map's actual entry capacity is that value times the load factor, so `new HashMap<>(n)` accommodates `0.75n` entries, not `n`.

---

## 2. `HashMap.newHashMap` and its three siblings

*Leaf 3.6.38 — `[SOURCE]` `[RESEARCH]`*

**Mental model.** A thin, correct front door in front of a constructor that everybody was mis-entering. It takes the number you have — mappings, not slots — divides by 0.75 for you, and hands the result to the same old constructor. No new machinery; a naming fix with arithmetic attached.

**Why it exists.** JDK-8281631 and the surrounding cleanup: the `initialCapacity` misreading was endemic enough that the JDK went through its own codebase converting call sites, then shipped the factory in Java 19 rather than leave everyone rewriting `(int)(n/0.75f)+1` by hand. The JDK now says so in the constructors' own javadoc:

> To create a {@code HashMap} with an initial capacity that accommodates an expected number of mappings, use {@link #newHashMap(int) newHashMap}.

— `@apiNote` on both `HashMap(int)` (line 469) and `HashMap(int, float)`, `java.base/java/util/HashMap.java`, JDK 21. (leaf 3.6.38)

That is the library telling you, in its own reference documentation, not to use the constructor you were about to use.

**When to reach for it.** Whenever you know roughly how many mappings are coming and you are on Java 19+. When not: if you are on 17 or 11, it does not exist and you write the manual formula; and if you genuinely want a non-default load factor, there is no factory overload — you are back to the constructor.

**How it works.**

```java
    static int calculateHashMapCapacity(int numMappings) {
        return (int) Math.ceil(numMappings / (double) DEFAULT_LOAD_FACTOR);
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2563. (leaf 3.6.38)

```java
    public static <K, V> HashMap<K, V> newHashMap(int numMappings) {
        if (numMappings < 0) {
            throw new IllegalArgumentException("Negative number of mappings: " + numMappings);
        }
        return new HashMap<>(calculateHashMapCapacity(numMappings));
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 2580, `@since 19`. (leaf 3.6.38)

`calculateHashMapCapacity` is package-private and static, which is why the set classes can share it. It divides in `double` — `(double) DEFAULT_LOAD_FACTOR` widens the `0.75f` constant — and takes `Math.ceil`, so there is no truncation and no compensating `+ 1`. `newHashMap` itself is three lines: reject negatives with a message that names the offending value, then delegate. It does **not** allocate a table; you still get the lazy-allocation behaviour, just with the right pending capacity.

`calculateHashMapCapacity(100) = (int) Math.ceil(100 / 0.75) = (int) Math.ceil(133.333…) = 134` — the same 134 the folk formula produces, hence the same 256-slot table. Confirmed by reflection:

```
--- B. three ways to size for 100 ---
new HashMap<>(100)                     -> table=256 threshold=192
new HashMap<>((int)(100/0.75f)+1)=134  -> table=256 threshold=192
HashMap.newHashMap(100)  cap arg = 134 -> table=256 threshold=192
```

**`[RESEARCH]` Do `ceil(n/0.75)` and `(int)(n/0.75f)+1` ever diverge?** They are not the same function, so this needs checking rather than assuming. Sweeping `n = 1..10000`: the **capacity argument** differs at **3,333** values — every `n` divisible by 3, where the division is exact and `ceil` adds nothing while the folk formula still adds its `+ 1`. Most of those get absorbed by the power-of-two rounding. But the **resulting table size** still differs at **12** values, all of the form `n = 3 × 2^k`:

| n | `ceil(n/0.75)` | `(int)(n/0.75f)+1` | JDK table | folk table | both hold n? |
|---|---|---|---|---|---|
| 3 | 4 | 5 | 4 | **8** | yes / yes |
| 6 | 8 | 9 | 8 | **16** | yes / yes |
| 12 | 16 | 17 | 16 | **32** | yes / yes |
| 24 | 32 | 33 | 32 | **64** | yes / yes |
| 48 | 64 | 65 | 64 | **128** | yes / yes |
| 96 | 128 | 129 | 128 | **256** | yes / yes |
| 192 | 256 | 257 | 256 | **512** | yes / yes |
| 384 | 512 | 513 | 512 | **1024** | yes / yes |
| 768 | 1024 | 1025 | 1024 | **2048** | yes / yes |
| 1536 | 2048 | 2049 | 2048 | **4096** | yes / yes |
| 3072 | 4096 | 4097 | 4096 | **8192** | yes / yes |
| 6144 | 8192 | 8193 | 8192 | **16384** | yes / yes |

**Insight:** at exactly those sizes the folk formula's `+ 1` pushes the capacity one integer past a power of two and costs you a **full extra doubling** — twice the array for no benefit, since both variants hold `n` without resizing. `newHashMap(6144)` allocates 8,192 slots; `new HashMap<>((int)(6144/0.75f)+1)` allocates 16,384. Another reason to use the factory, and a concrete answer to "does it actually matter".

**The four factories.**

| Factory | `@since` | Delegates to | Pre-19 equivalent |
|---|---|---|---|
| `HashMap.newHashMap(int)` | 19 | `new HashMap<>(calculateHashMapCapacity(n))` | `new HashMap<>((int)(n/0.75f)+1)` |
| `LinkedHashMap.newLinkedHashMap(int)` | 19 | `new LinkedHashMap<>(HashMap.calculateHashMapCapacity(n))` | `new LinkedHashMap<>((int)(n/0.75f)+1)` |
| `HashSet.newHashSet(int)` | 19 | `new HashSet<>(HashMap.calculateHashMapCapacity(n))` | `new HashSet<>((int)(n/0.75f)+1)` |
| `LinkedHashSet.newLinkedHashSet(int)` | 19 | `new LinkedHashSet<>(HashMap.calculateHashMapCapacity(n))` | `new LinkedHashSet<>((int)(n/0.75f)+1)` |

All four verified against JDK 21 sources: `LinkedHashMap.java` line 1074, `HashSet.java` line 396, `LinkedHashSet.java` line 221. All four route through the same `HashMap.calculateHashMapCapacity`, all four reject negatives, all four are `@since 19`. The set factories reach the same arithmetic because `HashSet` is a `HashMap` with a shared sentinel value — `HashSet(int initialCapacity)` is literally `map = new HashMap<>(initialCapacity);` (`HashSet.java`, line 153), so the capacity confusion was identical and so is the cure.

**What is not in the family.** There is no `newTreeMap` (a `TreeMap` has no table to size), no `newArrayList` (`new ArrayList<>(n)` already means *n elements* — the argument is a real element count, which is exactly why nobody misreads it), and no `newConcurrentHashMap`. `ConcurrentHashMap` in JDK 21 exposes only `newKeySet()` and `newKeySet(int)` (lines 2187 and 2204), which build a set view, not a sized map; its constructor does its own sizing arithmetic and needs its own discussion — [`../concurrent-collections/02-internals-chm-a.md`](../concurrent-collections/02-internals-chm-a.md) owns it.

**Supporting fact — argument validation.** `HashMap.newHashMap(-1)` and `new HashMap<>(-1)` both throw `IllegalArgumentException`, but with different messages, so a stack trace tells you which path was taken:

```
newHashMap(-1): java.lang.IllegalArgumentException: Negative number of mappings: -1
new HashMap<>(-1): java.lang.IllegalArgumentException: Illegal initial capacity: -1
```

**Gotcha.** `newHashMap` is a static factory on a concrete class, so it cannot be reached through a `Map` reference and it is invisible to code written against the interface. It also gives you a `HashMap<K,V>`, not a `Map<K,V>`, which matters if you were relying on target typing.

> **Definition.** `HashMap.newHashMap(n)` — and its `LinkedHashMap`, `HashSet` and `LinkedHashSet` siblings, all `@since 19` — construct an empty instance sized for **n mappings** by passing `ceil(n / 0.75)` to the ordinary capacity constructor.

---

## 3. `putMapEntries`: pre-sizing on `putAll` and on the copy constructor

*Leaf 3.6.39 — `[SOURCE]`*

**Mental model.** One private method serves two public entry points that look unrelated: `putAll(m)` and `new HashMap<>(m)`. Before copying a single entry it asks "how big is the source, and do I already have a table?" — and takes a different route depending on the answer. If there is no table yet it just writes down the size it will need. If there already is one, it grows first and copies second, so the entries land once instead of being rehomed on the way in.

**Why it exists.** Without it, `new HashMap<>(thousandEntryMap)` would start at 16 slots and rehash its way up, doing seven full table rebuilds during construction — work that is entirely avoidable because the source's `size()` is known before the first insert.

**When it fires.** Both public callers, with one bit of difference:

```java
    public void putAll(Map<? extends K, ? extends V> m) {
        putMapEntries(m, true);
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 790. (leaf 3.6.39)

```java
    public HashMap(Map<? extends K, ? extends V> m) {
        this.loadFactor = DEFAULT_LOAD_FACTOR;
        putMapEntries(m, false);
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 489 (javadoc elided). (leaf 3.6.39)

**How it works.**

```java
    final void putMapEntries(Map<? extends K, ? extends V> m, boolean evict) {
        int s = m.size();
        if (s > 0) {
            if (table == null) { // pre-size
                double dt = Math.ceil(s / (double)loadFactor);
                int t = ((dt < (double)MAXIMUM_CAPACITY) ?
                         (int)dt : MAXIMUM_CAPACITY);
                if (t > threshold)
                    threshold = tableSizeFor(t);
            } else {
                // Because of linked-list bucket constraints, we cannot
                // expand all at once, but can reduce total resize
                // effort by repeated doubling now vs later
                while (s > threshold && table.length < MAXIMUM_CAPACITY)
                    resize();
            }

            for (Map.Entry<? extends K, ? extends V> e : m.entrySet()) {
                K key = e.getKey();
                V value = e.getValue();
                putVal(hash(key), key, value, false, evict);
            }
        }
    }
```
— `java.base/java/util/HashMap.java`, JDK 21, line 502. (leaf 3.6.39)

`int s = m.size()` is read **once**, up front; a source map that changes size during the copy will not re-trigger sizing. `if (s > 0)` guards everything — an empty source falls straight through and the method is a no-op.

*The `table == null` branch.* `Math.ceil(s / (double) loadFactor)` is the same arithmetic `calculateHashMapCapacity` performs, inlined. The `dt < MAXIMUM_CAPACITY` test clamps rather than overflows. Then `if (t > threshold) threshold = tableSizeFor(t)` — the overloaded-field trick again: this writes a *capacity* into `threshold`, exactly as the constructor does, and the first `putVal` will convert it. The `t > threshold` guard means an explicit larger request wins: `var m = new HashMap<Integer,Integer>(10_000); m.putAll(fiftyEntries);` keeps its 16,384 slots.

*The `else` branch.* The source's own comment names the constraint. The table length must stay a power of two, and `resize()` splits each bin by exactly one additional hash bit, so there is no single-step jump from 16 to 2,048 — you double, repeatedly. The loop does all that doubling **before** the insert loop runs, so every entry is placed once into a correctly sized table rather than being rehashed on the way. `table.length < MAXIMUM_CAPACITY` is the termination guard for the pathological case.

**Concrete example and real output.** Loading 1,000 entries three ways:

```java
Map<Integer,Integer> src = new LinkedHashMap<>();
for (int i = 0; i < 1000; i++) src.put(i, i);

HashMap<Integer,Integer> viaCtor = new HashMap<>(src);          // table == null branch

HashMap<Integer,Integer> viaPutAll = new HashMap<>();
viaPutAll.put(-1, -1);                                          // force table allocation
viaPutAll.putAll(src);                                          // else branch, while loop

HashMap<Integer,Integer> grow = new HashMap<>();                // no pre-sizing at all
for (int i = 0; i < 1000; i++) grow.put(i, i);
```

```
--- A. copy constructor pre-sizes; putAll into a live table does not ---
new HashMap<>(src)   -> table=2048 threshold=1536 size=1000
before putAll        -> table=16 threshold=12
after putAll(1000)   -> table=2048 threshold=1536 size=1001

--- B. resize count: growing from 16 one put at a time vs copy ctor ---
one-at-a-time from default: final table=2048, resizes=7, nodes rehashed=1524
copy constructor:           final table=2048, resizes=0, nodes rehashed=0
```

**`[NUM]` The saving, counted.** Growing from 16 to 2,048 is seven doublings — 16→32→64→128→256→512→1024→2048 — and each one walks every node currently present. Summing the sizes at which each resize fires (13, 25, 49, 97, 193, 385, 769) gives **1,524 nodes rehashed** on top of the 1,000 insertions. The copy constructor rehashes **zero**.

**`[NUM]` Version note, JDK 8 → JDK 21.** JDK 8's version of the same method:

```java
            if (table == null) { // pre-size
                float ft = ((float)s / loadFactor) + 1.0F;
                int t = ((ft < (float)MAXIMUM_CAPACITY) ?
                         (int)ft : MAXIMUM_CAPACITY);
                if (t > threshold)
                    threshold = tableSizeFor(t);
            }
            else if (s > threshold)
                resize();
```
— `java/util/HashMap.java`, JDK 8, line 500 (excerpt: the pre-size block only). (leaf 3.6.39)

Two changes. **(a)** The pre-size arithmetic went from `((float)s / loadFactor) + 1.0F` — a `float` division with a manual `+ 1` — to `Math.ceil(s / (double) loadFactor)`. Same intent, cleaner rounding, and it drops the spurious extra doubling at `s = 3 × 2^k` documented in §2. **(b)** The non-null-table branch went from a **single** `if (s > threshold) resize()` to a **`while` loop**. This is a performance change, not a behaviour change — both end at the same final capacity — but the work differs sharply. Simulating `putAll` of 1,000 entries into a map holding 1 entry in a 16-slot table:

```
JDK 21 (while loop):         final cap= 2048  resizes=7  nodes rehashed=7
JDK 8  (single resize):      final cap= 2048  resizes=7  nodes rehashed=1519
```

Seven resizes either way. Under JDK 21 they all happen up front, on a table holding one node, so the seven rebuilds touch **7 nodes total**. Under JDK 8 the single up-front resize takes you to 32, and the remaining six happen mid-insertion on progressively fuller tables — **1,519 nodes rehashed**. Do not overclaim this as a behavioural difference; the maps are identical afterwards. It is a two-orders-of-magnitude reduction in copying work.

**`[SOURCE]` What `evict` actually does.** It is passed straight to `putVal`, which relays it to `afterNodeInsertion(evict)` — an empty method on `HashMap` and, on `LinkedHashMap`, the hook that consults `removeEldestEntry`. The hook itself is covered in [`../linked-hash-map/01-internals.md`](../linked-hash-map/01-internals.md). The consequence is real and testable: **an LRU `LinkedHashMap` built by copy constructor does not evict while being built; the same map built by `putAll` does.**

```java
static final class Lru<K,V> extends LinkedHashMap<K,V> {
    private final int max;
    Lru(int max) { super(16, 0.75f, true); this.max = max; }
    Lru(int max, Map<K,V> src) { super(src); this.max = max; }
    @Override protected boolean removeEldestEntry(Map.Entry<K,V> eldest) { return size() > max; }
}

Map<Integer,Integer> src100 = new LinkedHashMap<>();
for (int i = 0; i < 100; i++) src100.put(i, i);

Lru<Integer,Integer> byCtor   = new Lru<>(10, src100);   // putMapEntries(m, false)
Lru<Integer,Integer> byPutAll = new Lru<>(10);
byPutAll.putAll(src100);                                 // putMapEntries(m, true)
```

```
--- C. evict: copy ctor passes false, putAll passes true ---
new Lru<>(10, src100).size()      = 100   keys: [0, 1, 2, 3, 4, 5]...[97, 98, 99]
new Lru<>(10); lru.putAll(src100) = 10   keys: [90, 91, 92, 93, 94, 95, 96, 97, 98, 99]
```

A 10-entry LRU cache that ends up holding 100 entries. Two calls most people treat as interchangeable, one order of magnitude apart in result.

**Supporting fact — `putAll` of an empty map.** The `if (s > 0)` guard means no allocation, no `modCount` bump, nothing:

```
--- D. putAll(emptyMap) touches nothing ---
modCount before=2 after two empty putAll=2
iterator survived: no ConcurrentModificationException
fresh map after putAll(Map.of()): table=0 threshold=0
```

An open iterator survives an empty `putAll`. Do not rely on it as an API contract, but it is what the code does.

> **Definition.** `putMapEntries(m, evict)` is the shared body of `putAll` and the copy constructor: it reads the source size once, either writes a pending capacity into `threshold` (no table yet) or pre-doubles the existing table until the source fits, then inserts every entry with the caller's `evict` flag relayed to `afterNodeInsertion`.

---

## 4. Non-default load factors

*Leaf 3.6.40 — `[PROVE]`*

**Mental model.** The load factor is a dial between two costs: array bytes on one side, chain length on the other. The intuition — "lower it and lookups get faster, raise it and you save memory" — is directionally right and quantitatively far weaker than people expect, for two reasons this section will demonstrate: the array is a *minority* of a `HashMap`'s footprint, and the power-of-two rounding frequently discards your adjustment entirely.

**Why anyone reaches for it.** Folklore that 0.75 is a compromise someone else chose. It is, but it is a *measured* one — the Poisson case is leaf 3.6.33 in [`04b-internals-d2-poisson-and-hysteresis.md`](04b-internals-d2-poisson-and-hysteresis.md).

**How it works.** Only through `new HashMap<>(cap, lf)`. `loadFactor` is `final`, there is no setter, no system property, and no way to change it after construction. And there is no `newHashMap` overload that takes one.

**`[PROVE]` Measured, 1,000 `Integer` entries, each map constructed with `new HashMap<>((int)Math.ceil(1000/lf), lf)`:**

| lf | requested cap | **actual table** | threshold | `Node[]` bytes | slots/entry | actual load | Poisson P(bin ≥ 8) | array share of footprint | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 0.50 | 2000 | **2048** | 1024 | 8,192 | 2.05 | 0.488 | 5.2e-08 | 20% | identical to 0.75 here |
| 0.75 | 1334 | **2048** | 1536 | 8,192 | 2.05 | 0.488 | 5.2e-08 | 20% | the default |
| 1.00 | 1000 | **1024** | 1024 | 4,096 | 1.02 | 0.977 | 8.7e-06 | 11% | halves array, 170× the long bins |
| 2.00 | 500 | **512** | 1024 | 2,048 | 0.51 | 1.953 | 9.4e-04 | 6% | quarters array, 18,000× the long bins |

**Insight:** at `n = 1000`, load factors 0.5 and 0.75 produce the **identical table** — 2,048 slots, identical memory, identical collision behaviour. `ceil(1000/0.5) = 2000` and `ceil(1000/0.75) = 1334` both round up to the same power of two, so the entire "0.5 gives faster lookups at 2× memory" trade evaporates. It is not always erased — `n = 1500` gives 4,096 at lf 0.5 versus 2,048 at lf 0.75 — but you cannot know which case you are in without doing the rounding arithmetic, and almost nobody does.

**`[NUM]` The memory arithmetic, honestly framed.** A `Node` is 32 bytes (12-byte header + `hash` + three references under compressed oops, padded to 8; see [`../cost-and-memory/02-internals-memory-headers.md`](../cost-and-memory/02-internals-memory-headers.md)). For 1,000 entries the nodes cost **32,000 bytes regardless of load factor**. The array is 4 bytes per slot: 8,192 bytes at lf 0.5 *and* 0.75, 4,096 at 1.0, 2,048 at 2.0. So the array is 20%, 20%, 11% and 6% of the `Node`-plus-array total. Going from the default to lf 1.0 saves 4,096 bytes out of 40,192 — a **10% reduction in total footprint** — while multiplying `P(bin ≥ 8)` by 170×. That is the whole argument in one line: **the load factor moves a minority of the memory and a great deal of the collision probability.**

**`[PROVE]` The lookup side, measured rather than asserted.** One million `Integer` keys per map, four million `get` calls at a 50% hit rate, same probe array for all four maps, three warmup passes, best of five timings.

```java
static HashMap<Integer,Integer> build(int n, float lf) {
    HashMap<Integer,Integer> m = new HashMap<>((int)Math.ceil(n / (double) lf), lf);
    for (int i = 0; i < n; i++) m.put(i, i);
    return m;
}
static int run(HashMap<Integer,Integer> m, int[] probes) {
    int hits = 0;
    for (int p : probes) if (m.get(p) != null) hits++;
    return hits;
}
```

```
n=1000000
lf=0.50  table=2097152  slots/entry=2.10  Node[] bytes=8388608
lf=0.75  table=2097152  slots/entry=2.10  Node[] bytes=8388608
lf=1.00  table=1048576  slots/entry=1.05  Node[] bytes=4194304
lf=2.00  table= 524288  slots/entry=0.52  Node[] bytes=2097152

get() timings, 4,000,000 probes (50% hit rate), best of 5:
lf=0.50    47.4 ms  (11.9 ns/get)
lf=0.75    49.2 ms  (12.3 ns/get)
lf=1.00    57.7 ms  (14.4 ns/get)
lf=2.00    72.7 ms  (18.2 ns/get)
```

**Unverified:** single-shot wall clock, not JMH — the shape is the finding, not the absolute figures. Machine: Apple M4 Pro, arm64. JDK: `21.0.7+8-LTS-245`, HotSpot 64-Bit Server VM, mixed mode.

Reading it honestly. 0.5 versus 0.75 differ by **1.8 ns/get, and they are the same table** — that difference is noise, and it is the most useful line in the table: at a million entries the celebrated "0.5 is faster" tuning did not even allocate a different array. Lowering the load factor below the default bought nothing at all. Going *up* does cost something real: 1.0 is ~17% slower and 2.0 is ~48% slower per lookup, which is the chain-length effect showing up as predicted.

**When it is legitimate to change it.** Two cases, both of the form *you have measured*. A very large, read-mostly, memory-constrained map where you have confirmed chains are short can go to 1.0 and reclaim ~10% of footprint. A map whose keys you know hash poorly, and whose `hashCode` you cannot fix because it is not your class, can go lower — though check the rounding first, since you may get nothing. Everything else is cargo cult; fix the `hashCode` or pre-size instead.

**Interview:** *"When would you change `HashMap`'s load factor?"* — Essentially never. 0.75 is a measured optimum, the knob moves a minority of the memory while moving collision probability by orders of magnitude, and power-of-two rounding often discards the change outright. Fix the `hashCode` or pre-size with `newHashMap` instead.

> **Definition.** The load factor is the `final`, construction-time ratio of entries to table slots at which `HashMap` doubles; the default 0.75 balances a ~20% array-memory share against a `P(bin ≥ 8)` around 1e-06, and moving it trades a small memory change for a large collision-probability change.

---

## Pitfalls

### Believing `new HashMap<>(n)` pre-sizes for n entries

**Wrong**
```java
Map<String,String> m = new HashMap<>(100);       // "sized for 100"
for (int i = 0; i < 100; i++) m.put("k" + i, "v");
// table went 0 -> 128 (first put) -> 256 (entry 97). Two resizes, 96 nodes rehashed.
```

**Right**
```java
Map<String,String> m = HashMap.newHashMap(100);  // Java 19+; ceil(100/0.75) = 134 -> table 256
for (int i = 0; i < 100; i++) m.put("k" + i, "v");
// table went 0 -> 256 on the first put. One allocation, zero rehashes.
```

**Why people believe it:** the parameter is called `initialCapacity`, and in `ArrayList` — the collection everyone learns first — the identically named parameter *is* an element count. `HashMap` reuses the word for a table length.

### Copying an LRU cache with the copy constructor

**Wrong**
```java
Lru<Integer,Integer> cache = new Lru<>(10, sourceOf100);   // super(src) -> putMapEntries(m, false)
System.out.println(cache.size());                          // 100 — the bound is ignored
```

**Right**
```java
Lru<Integer,Integer> cache = new Lru<>(10);
cache.putAll(sourceOf100);                                 // putMapEntries(m, true)
System.out.println(cache.size());                          // 10
```

**Why people believe it:** `new HashMap<>(m)` and `m2.putAll(m)` are documented as producing equal maps, and for a plain `HashMap` they do. The `evict` flag only becomes visible once `afterNodeInsertion` is overridden, which is exactly the `LinkedHashMap` LRU case.

### Lowering the load factor to speed up lookups

**Wrong**
```java
var fast = new HashMap<Integer,Integer>(2_000_000, 0.5f);  // "half the collisions"
// table = 2_097_152 — byte-for-byte identical to the default at 1M entries.
```

**Right**
```java
var fast = HashMap.newHashMap(1_000_000);                  // table = 2_097_152, same thing
// If lookups are slow, the cause is a poor hashCode, not the load factor.
```

**Why people believe it:** the load-factor-to-chain-length relationship is real and taught. What is not taught is that the table length is rounded to a power of two afterwards, which quantises your adjustment away unless it crosses a doubling boundary.

---

## Cheat sheet

| Thing | Value / behaviour |
|---|---|
| `new HashMap<>(n)` holds | `0.75n` entries before resizing |
| `new HashMap<>(100)` | `threshold=128`, `table=null`; after 1st put table=128 thr=96; resizes at entry **97** |
| Correct pre-size, Java 19+ | `HashMap.newHashMap(n)` → `ceil(n/0.75)` |
| Correct pre-size, pre-19 | `new HashMap<>((int)(n/0.75f) + 1)` |
| Folk formula penalty | at `n = 3 × 2^k` it allocates one extra doubling (e.g. n=6144: 16384 vs 8192) |
| `+ 1` actually needed for | only `n = 1` and `n = 2` in the range 1..200 |
| Factory family, all `@since 19` | `HashMap.newHashMap`, `LinkedHashMap.newLinkedHashMap`, `HashSet.newHashSet`, `LinkedHashSet.newLinkedHashSet` |
| All four delegate to | `HashMap.calculateHashMapCapacity(n)` = `(int) Math.ceil(n / 0.75d)` |
| Not in the family | `newTreeMap`, `newArrayList`, `newConcurrentHashMap` — none exist |
| `putMapEntries` callers | `putAll(m)` → `evict=true`; `new HashMap<>(m)` → `evict=false` |
| `evict` reaches | `afterNodeInsertion(evict)` — no-op on `HashMap`, LRU trigger on `LinkedHashMap` |
| `table == null` branch | writes `tableSizeFor(ceil(s/lf))` into `threshold`, no allocation |
| `table != null` branch | `while (s > threshold && ...) resize()` — pre-doubles before inserting |
| JDK 8 → 21 change | pre-size `float +1.0F` → `Math.ceil` in `double`; single `resize()` → `while` loop |
| Cost of that change | 1,000-entry `putAll` into a live 16-slot table: 1,519 nodes rehashed → **7** |
| `putAll(emptyMap)` | `if (s > 0)` guard — no allocation, no `modCount` bump |
| `loadFactor` field | `final`, construction-time only, no setter, no system property |
| lf memory share (1,000 entries) | array is 20% (lf 0.5 and 0.75), 11% (1.0), 6% (2.0) of `Node`+array |
| lf lookup cost (1M keys, M4 Pro) | 11.9 / 12.3 / 14.4 / 18.2 ns per `get` at 0.5 / 0.75 / 1.0 / 2.0 |
| lf 0.5 vs 0.75 at n=1000 and n=1e6 | **identical table** — power-of-two rounding erases the difference |

---

## Self-test

**Q1.** A colleague writes `new HashMap<>(1000)` for a map that will hold exactly 1,000 entries. Walk the table and threshold values from construction to the last insert.

<details><summary>Answer</summary>

Construction: `threshold = tableSizeFor(1000) = 1024`, `table = null`, no allocation. First `put`: `resize()` sees `oldThr = 1024`, allocates `table` of 1024, sets `threshold = (int)(1024 * 0.75f) = 768`. Insert 768 is fine (`768 > 768` is false); insert 769 triggers `resize()` to a 2,048-slot table with `threshold = 1536`, rehashing 768 nodes. Final state: table 2,048, threshold 1,536, size 1,000 — the same table `newHashMap(1000)` would have allocated straight away, reached via one wasted rehash of 768 nodes.

</details>

**Q2.** `HashMap.newHashMap(6144)` and `new HashMap<>((int)(6144/0.75f)+1)` both hold 6,144 entries without resizing. Why prefer the first?

<details><summary>Answer</summary>

`ceil(6144/0.75) = 8192` exactly, so `tableSizeFor(8192) = 8192`. The folk formula computes `(int)(8192.0f) + 1 = 8193`, and `tableSizeFor(8193) = 16384`. The `+ 1` pushes the request one past a power of two and buys a full extra doubling — 16,384 slots instead of 8,192, twice the array bytes, for no benefit. This happens at every `n = 3 × 2^k`; there are 12 such values below 10,000.

</details>

**Q3.** Why does `putMapEntries` use a `while` loop rather than one `resize()` when the table already exists, and what changed from JDK 8?

<details><summary>Answer</summary>

The table length must remain a power of two and each `resize()` splits bins by exactly one more hash bit, so you cannot jump from 16 to 2,048 in one step — you double repeatedly. JDK 8 did a single `if (s > threshold) resize()`; JDK 21 loops. Both reach the same final capacity with the same number of resizes, but JDK 21 performs them all *before* the insert loop, on a nearly-empty table. Simulating a 1,000-entry `putAll` into a map holding one entry in a 16-slot table: JDK 21 rehashes 7 nodes total, JDK 8 rehashes 1,519. Performance only — no behavioural difference.

</details>

**Q4.** An LRU cache built with `new Lru<>(10, hundredEntryMap)` ends up with 100 entries. Explain.

<details><summary>Answer</summary>

The copy constructor calls `putMapEntries(m, false)`. The `evict` flag is relayed through `putVal` to `afterNodeInsertion(evict)`, which on `LinkedHashMap` is the method that consults `removeEldestEntry`. With `evict == false` the hook does nothing, so no eviction happens during construction. `putAll` passes `evict = true` and does evict, ending at 10. Two calls people treat as interchangeable, differing by an order of magnitude in result.

</details>

**Q5.** You set load factor 0.5 on a map that will hold one million entries, expecting shorter chains. What actually happens?

<details><summary>Answer</summary>

Nothing. `ceil(1_000_000 / 0.5) = 2_000_000` and `ceil(1_000_000 / 0.75) = 1_333_334` both round up to `tableSizeFor` = 2,097,152. Byte-for-byte the same table as the default, the same chain distribution, and measured `get` times of 11.9 vs 12.3 ns — noise. The power-of-two rounding quantises the adjustment away unless it crosses a doubling boundary.

</details>

**Q6.** `threshold` on a freshly constructed `new HashMap<>(100)` reads 128 in the debugger. Is the map going to resize at 128 entries?

<details><summary>Answer</summary>

No. Before the first `put`, `threshold` is overloaded to hold the *pending capacity*, not a resize threshold — the constructor assigns `tableSizeFor(initialCapacity)` to it. On the first `put`, `resize()` reads that 128 as the new table length and overwrites `threshold` with `(int)(128 * 0.75f) = 96`. The map resizes at entry 97. Leaf 3.6.8 in `01-internals-a-constants-and-hash.md` covers the dual meaning.

</details>

**Q7.** Does `map.putAll(Collections.emptyMap())` invalidate an open iterator over `map`?

<details><summary>Answer</summary>

No. `putMapEntries` guards everything behind `if (s > 0)`, so with an empty source it allocates nothing, inserts nothing, and never touches `modCount`. Verified: `modCount` unchanged after two empty `putAll` calls, and an iterator opened beforehand completes without `ConcurrentModificationException`. This is what the code does, not a documented contract — do not build on it.

</details>

**Q8.** Why is there no `TreeMap.newTreeMap(int)` or `ArrayList.newArrayList(int)`?

<details><summary>Answer</summary>

`TreeMap` has no backing array to pre-size — it is a red-black tree of nodes allocated one at a time, so there is no capacity concept to get wrong. `ArrayList(int initialCapacity)` already takes a genuine *element* count, with no load factor applied, so the parameter means what a caller assumes it means. The `newXxx` family exists solely to repair the entries-versus-slots confusion, which only the hash-based collections have.

</details>

---

## Open questions

- The `get()` timings in §4 are single-shot wall clock on one machine, not JMH. The ordering (0.5 ≈ 0.75 < 1.0 < 2.0) is stable across five repetitions, but the absolute nanosecond figures should not be quoted as benchmarks.

---

**Leaves covered:** 3.6.37, 3.6.38, 3.6.39, 3.6.40 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** D-99
**Target version:** Java 21 LTS
**Lines:** 585
