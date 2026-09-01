# 02 Java Collections — `LinkedHashMap` — INTERNALS (§4.6.2 The hand-rolled LRU, part 2 — the broken version, the proof, and the bill)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-hash-map/02-build-lru-by-hand.md](02-build-lru-by-hand.md) · Next: [linked-hash-map/03-build-lfu-sketch.md](03-build-lfu-sketch.md)

---

The class is written. This file is about whether it is *right*, and what it costs — the two questions that separate a cache you would ship from a cache that merely compiles. A hand-rolled LRU is easy to write in a way that looks correct: forward iteration prints a plausible order, `get` returns plausible values, and the bug shows up three thousand operations later as a heap that will not stop growing. So the deliverables here are a broken implementation with its symptom on the page, a differential test against `java.util.LinkedHashMap` that runs 300,000 operations and checks every one, and the byte arithmetic that says what those 150 lines cost you.

**Code on this page.** Two labelled `java` blocks, two files, one block each, in order: `BrokenLruCache.java` (the bug, deliberately) and `LruProofDemo.java` (the case study plus the property test). Both depend on `LruCache.java` from [02-build-lru-by-hand.md](02-build-lru-by-hand.md) and are compiled together with it under `javac -Xlint:all`, zero warnings; every printed line below is real output of `java LruProofDemo`. Section numbering continues from that file, which is why the output starts at `== 3.`.

**No diagram on this page.** The structure was drawn once, in D-148 in [02-build-lru-by-hand.md](02-build-lru-by-hand.md), and nothing here changes the shape — the broken version's failure is that the map and the list *disagree*, which is a picture of the same two boxes with a missing arrow removal, better read as output than drawn.

---

## §4.6.2e The one-line bug: unlink without `map.remove`

### Mental model

Two indexes over one pile of nodes means two chances to forget one. Eviction is the only operation that starts from the *list* — it picks `head.next`, a node, not a key — so it is the only operation where the map is easy to forget. Forget it and the cache silently changes species: it stops being bounded, in both indexes, and it does so quietly, because the two indexes never compare notes.

### Why it exists as a mistake

Because eviction *reads* naturally as a list operation. "Drop the least recently used entry" is spatially a list statement — remove the front — and the map does not appear in that sentence at all. The node holds the key precisely so that the sentence can be completed, and the completion is one extra line that no compiler will ask for.

### When it bites

Immediately, and invisibly. Every test that checks `get` on a *live* key passes. Every test that prints the list passes. What fails is a long-running process: the map grows without bound, holding hard references to keys and values that the policy declared dead, so it presents as a slow heap leak with no obvious owner — the worst shape of production bug there is.

### How it works — the broken class

```java
// BrokenLruCache.java
import java.util.HashMap;
import java.util.Map;

/** The classic bug: eviction unlinks the node but never removes the key from the map. */
final class BrokenLruCache<K, V> {

    private static final class Node<K, V> {
        K key;
        V value;
        Node<K, V> prev;
        Node<K, V> next;

        Node(K key, V value) {
            this.key = key;
            this.value = value;
        }
    }

    private final Map<K, Node<K, V>> map = new HashMap<>();
    private final int capacity;
    private final Node<K, V> head = new Node<>(null, null);
    private final Node<K, V> tail = new Node<>(null, null);

    BrokenLruCache(int capacity) {
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    V get(K key) {
        Node<K, V> node = map.get(key);
        if (node == null) {
            return null;
        }
        unlink(node);
        linkBeforeTail(node);
        return node.value;
    }

    void put(K key, V value) {
        Node<K, V> existing = map.get(key);
        if (existing != null) {
            existing.value = value;
            unlink(existing);
            linkBeforeTail(existing);
            return;
        }
        if (map.size() == capacity) {
            unlink(head.next);          // BUG: no map.remove(head.next.key)
        }
        Node<K, V> node = new Node<>(key, value);
        map.put(key, node);
        linkBeforeTail(node);
    }

    int size() {
        return map.size();
    }

    int listLength() {
        int n = 0;
        for (Node<K, V> cur = head.next; cur != tail; cur = cur.next) {
            n++;
        }
        return n;
    }

    private void unlink(Node<K, V> n) {
        n.prev.next = n.next;
        n.next.prev = n.prev;
    }

    private void linkBeforeTail(Node<K, V> n) {
        n.prev = tail.prev;
        n.next = tail;
        tail.prev.next = n;
        tail.prev = n;
    }
}
```

One statement is missing from `put`, and the class is otherwise the same code as `LruCache`. `listLength()` exists only so the two indexes can be printed side by side, which is the whole diagnosis.

```text
== 3. the bug: unlink without map.remove, capacity 2 ==
  put A -> size()=1 listLength=1
  put B -> size()=2 listLength=2
  put C -> size()=3 listLength=2
  put D -> size()=4 listLength=3
  put E -> size()=5 listLength=4
  get(A) after A was evicted from the list: vA
  size()=5 listLength=5 capacity=2
```

Read it line by line, because the failure cascades in a specific order.

- `put C` is the first eviction. `A` is unlinked, so `listLength` stays at 2 — the list is still correctly bounded. But `size()` is 3, because the map kept `A`.
- `put D` finds `map.size() == 3`, which is not `== capacity`, so **the eviction branch is never entered again**. `listLength` climbs to 3. The bound is gone entirely, not just off by one: a single leaked key permanently disables eviction for a cache that tests `map.size() == capacity`.
- `get("A")` returns `vA` for a key the policy evicted three operations earlier — a correctness failure visible to callers, not just a leak.
- Worse, that `get` *resurrects* `A`: `unlink` followed by `linkBeforeTail` puts the orphaned node straight back into the list, which is why the final `listLength` is 5. Both indexes now hold five entries in a cache of capacity 2.

`LruCache.evict()` prevents all four symptoms with four statements that must never be separated:

```java
map.remove(victim.key);
unlink(victim);
victim.prev = null;
victim.next = null;
```

Nulling the departing pointers is the defence against the resurrection specifically: a stale reference relinked through a nulled node throws `NullPointerException` at the moment of the mistake instead of corrupting the list.

**Pitfall:** using `map.size() == capacity` as the fullness test *and* leaking map entries is what turns an off-by-one into an unbounded cache. `>=` instead of `==` would have kept evicting and hidden the leak for longer, which is worse: the list would stay bounded, the map would grow forever, and nothing in the cache's own output would ever look wrong.

### Definition

> An eviction is a two-index operation: it must remove the victim from the hash index *and* the order index, in one method, with no path between them that can fail.

---

## §4.6.2f The property test — 300,000 operations against the JDK

### Mental model

Do not test what the cache *should* do; test that it does what a known-correct implementation does. `java.util.LinkedHashMap` in access-order mode with `removeEldestEntry` **is** an LRU cache, written by people who had to defend it in the JDK. So run both, feed them the identical random operation stream, and compare everything observable after every single operation. This is differential (or model-based) testing, and it is why the class has `keys()` and `toString()` at all.

### Why it exists

Because "LRU-shaped" and "LRU" are different things, and unit tests written by the same person who wrote the bug tend to encode the bug. A hand-written test asserts the cases the author thought of. A differential test asserts *agreement on everything*, across a random walk the author did not design, and it finds the case where a re-`put` should have counted as an access but did not.

### When to reach for it, and when not

Reach for it whenever a known-correct reference exists in the same process — caches, collections, parsers, encoders. Do not reach for it when the reference is the thing you are replacing *because it is wrong*, and do not confuse it with a benchmark: this test says nothing at all about speed.

**No diagram here either.** A test is a control flow, not a structure.

### How it works

Three things make the comparison meaningful, and each is a decision:

- **A key space much smaller than the operation count** — eight keys, capacity five. The point is to make collisions, evictions, re-`put`s of live keys, and removals of absent keys all common. A large key space would produce a stream of misses and test nothing.
- **A fixed seed.** `new Random(20260828L)` makes the transcript on this page reproducible, and a failure re-runnable.
- **Everything observable, after every operation** — the return value of the operation itself, `size()`, `containsKey` for all eight keys in the space (which detects a key held by one index and not the other, the exact signature of the previous section's bug), and the *full recency order* as a list. Order is the assertion that matters: two caches can agree on membership and disagree on who dies next.

`LinkedHashMap`'s `keySet()` iterates eldest-first, and `LruCache.keys()` returns least-recently-used first, so the two orders are directly comparable with no adaptation. That is not a coincidence — it is why `keys()` was specified that way round.

```java
// LruProofDemo.java
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public final class LruProofDemo {

    /** The 10-line reference LRU we are checking ourselves against. */
    static final class AccessOrderBound<K, V> extends LinkedHashMap<K, V> {
        private static final long serialVersionUID = 1L;
        private final int maxEntries;

        AccessOrderBound(int maxEntries) {
            super(16, 0.75f, true);
            this.maxEntries = maxEntries;
        }

        @Override
        protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
            return size() > maxEntries;
        }
    }

    public static void main(String[] args) {
        brokenEviction();
        propertyTest();
    }

    private static void brokenEviction() {
        System.out.println();
        System.out.println("== 3. the bug: unlink without map.remove, capacity 2 ==");
        BrokenLruCache<String, String> b = new BrokenLruCache<>(2);
        for (String k : List.of("A", "B", "C", "D", "E")) {
            b.put(k, "v" + k);
            System.out.println("  put " + k + " -> size()=" + b.size() + " listLength=" + b.listLength());
        }
        System.out.println("  get(A) after A was evicted from the list: " + b.get("A"));
        System.out.println("  size()=" + b.size() + " listLength=" + b.listLength() + " capacity=2");
    }

    private static void propertyTest() {
        System.out.println();
        System.out.println("== 4. property test against java.util.LinkedHashMap(accessOrder=true) ==");
        final int capacity = 5;
        final int keySpace = 8;
        final int operations = 300_000;

        LruCache<Integer, String> mine = new LruCache<>(capacity);
        AccessOrderBound<Integer, String> ref = new AccessOrderBound<>(capacity);
        Random rnd = new Random(20260828L);

        long gets = 0;
        long puts = 0;
        long removes = 0;
        for (int op = 1; op <= operations; op++) {
            int key = rnd.nextInt(keySpace);
            int choice = rnd.nextInt(100);
            if (choice < 55) {
                gets++;
                String a = mine.get(key);
                String b = ref.get(key);
                check(op, "get(" + key + ") value", String.valueOf(a), String.valueOf(b), mine, ref);
            } else if (choice < 95) {
                puts++;
                String v = "v" + op;
                String a = mine.put(key, v);
                String b = ref.put(key, v);
                check(op, "put(" + key + ") previous", String.valueOf(a), String.valueOf(b), mine, ref);
            } else {
                removes++;
                String a = mine.remove(key);
                String b = ref.remove(key);
                check(op, "remove(" + key + ") previous", String.valueOf(a), String.valueOf(b), mine, ref);
            }

            check(op, "size", String.valueOf(mine.size()), String.valueOf(ref.size()), mine, ref);
            if (mine.size() > capacity) {
                throw new AssertionError("op " + op + ": size " + mine.size() + " exceeds capacity " + capacity);
            }
            for (int k = 0; k < keySpace; k++) {
                check(op, "containsKey(" + k + ")",
                        String.valueOf(mine.containsKey(k)), String.valueOf(ref.containsKey(k)), mine, ref);
            }
            List<Integer> refOrder = new ArrayList<>(ref.keySet());
            check(op, "recency order", mine.keys().toString(), refOrder.toString(), mine, ref);
        }
        System.out.println("  operations : " + operations + " (" + gets + " get, " + puts + " put, " + removes + " remove)");
        System.out.println("  capacity   : " + capacity + ", key space 0.." + (keySpace - 1));
        System.out.println("  checks     : size, containsKey x " + keySpace + ", full recency order, return value - after every operation");
        System.out.println("  final mine : " + mine.keys());
        System.out.println("  final ref  : " + new ArrayList<>(ref.keySet()));
        System.out.println("  RESULT     : agreed on every assertion, 0 divergences");
    }

    private static void check(int op, String what, String mineValue, String refValue,
                              LruCache<Integer, String> mine, Map<Integer, String> ref) {
        if (!mineValue.equals(refValue)) {
            throw new AssertionError("op " + op + " " + what + ": mine=" + mineValue + " ref=" + refValue
                    + "\n  mine order=" + mine.keys() + "\n  ref  order=" + new ArrayList<>(ref.keySet()));
        }
    }
}
```

The `check` helper compares `String.valueOf` of both sides so that `null` and `"null"` collapse to one comparison, and its failure message prints both recency orders — the only two facts that make a divergence diagnosable.

```text
== 4. property test against java.util.LinkedHashMap(accessOrder=true) ==
  operations : 300000 (165240 get, 119792 put, 14968 remove)
  capacity   : 5, key space 0..7
  checks     : size, containsKey x 8, full recency order, return value - after every operation
  final mine : [5, 2, 6, 0, 7]
  final ref  : [5, 2, 6, 0, 7]
  RESULT     : agreed on every assertion, 0 divergences
```

Three hundred thousand operations — 165,240 gets, 119,792 puts, 14,968 removes — with 11 assertions each (one return value, `size()`, eight `containsKey`, one full order) for 3,300,000 in total, and no disagreement on any of them. That is the difference between "I wrote an LRU cache" and "this is an LRU cache".

**Insight:** the test also pins down the policy choices from the previous file. It only passes because `containsKey` does **not** record an access on either side, because a re-`put` of an existing key **does** on both, and because evict-first and insert-then-evict are observationally identical from outside `put`. Change any one of those three decisions in `LruCache` and this transcript turns into a divergence report inside the first few hundred operations.

### The gotcha

Passing this test does not mean the class is a drop-in `LinkedHashMap`. It compares only what the test reads. `LruCache` has no `entrySet`, no `Map` interface, no `equals`/`hashCode`, no serialisation, no fail-fast iteration, no null-key semantics defined, and no thread safety. A differential test proves agreement *on the compared surface* and is silent about everything outside it — so state that surface explicitly, as here, rather than concluding "equivalent".

### Definition

> A property test against a reference implementation asserts agreement on every observable, after every operation, over a random operation stream — trading the tester's imagination for the reference's correctness.

---

## §4.6.2g The bill: 64 bytes per entry against 40

### Mental model

You did not remove `LinkedHashMap`'s fusion; you replaced it with two objects and an arrow. The arrow is a field, the second object has a header, and headers are 12 bytes each. That is the entire memory story, and it goes the wrong way.

### The arithmetic

All figures are 64-bit HotSpot with **compressed oops**, which is the default whenever the heap is under 32 GB: object header 12 bytes, every reference 4 bytes, `int` 4 bytes, and every object's size rounded up to a multiple of 8.

`LinkedHashMap`, per entry, allocates one `LinkedHashMap.Entry`:

| Field | Bytes |
|---|---|
| header | 12 |
| `hash` (`int`) | 4 |
| `key` (ref) | 4 |
| `value` (ref) | 4 |
| `next` (ref, bucket chain) | 4 |
| `before` (ref) | 4 |
| `after` (ref) | 4 |
| raw total | 36 |
| **aligned to 8** | **40** |

`LruCache`, per entry, allocates two objects. The `HashMap.Node` the map needs:

| Field | Bytes |
|---|---|
| header | 12 |
| `hash` (`int`) | 4 |
| `key` (ref) | 4 |
| `value` (ref → your `Node`) | 4 |
| `next` (ref, bucket chain) | 4 |
| raw total | 28 |
| **aligned to 8** | **32** |

plus your own `Node`:

| Field | Bytes |
|---|---|
| header | 12 |
| `key` (ref) | 4 |
| `value` (ref) | 4 |
| `prev` (ref) | 4 |
| `next` (ref) | 4 |
| raw total | 28 |
| **aligned to 8** | **32** |

**32 + 32 = 64 bytes per entry, against `LinkedHashMap.Entry`'s 40.** That is **60% more memory per entry than the class it replaces** — 24 extra bytes, of which 12 are the second object's header and 4 is the map's `value` reference now pointing at a node instead of at the value. The bucket array costs 4 bytes per slot in both designs and cancels out; the two sentinels cost 64 bytes once, for the whole cache, and are noise.

| Design | Objects per entry | Bytes per entry | 100,000 entries |
|---|---|---|---|
| `LinkedHashMap` (access-order) | 1 `Entry` | 40 | 4.0 MB |
| `LruCache` (hand-rolled) | 1 `HashMap.Node` + 1 `Node` | 64 | 6.4 MB |
| `HashMap` with no order at all | 1 `Node` | 32 | 3.2 MB |

Entry-overhead figures and the wider memory context are in [01c1-internals-c2-memory-set-and-caffeine.md](01c1-internals-c2-memory-set-and-caffeine.md). Note that all of this counts *overhead only* — keys and values are the same objects in both designs, so at 200-byte values the difference shrinks to a few percent of the total, and at boxed-`Integer`-key scale it dominates. The ratio matters when entries are small and numerous, which is exactly when people build caches.

There is a second cost the table cannot show: two objects per entry means two pointer dereferences on the hot path (bucket → `HashMap.Node` → your `Node`) and two independent allocation sites, so the entry's data is less likely to share a cache line. No timing figures are published here — a single-shot wall clock on this machine would be worse than no number at all, and a JMH-grade comparison is out of scope for this file.

### The honest conclusion

**You would ship `LinkedHashMap`.** Ten lines, 40 bytes an entry, in the JDK, already debugged, and its access-order mode is the same policy. You write the hand-rolled version for exactly two reasons: to understand what the fused `Entry` is doing, and because you need a policy `removeEldestEntry` cannot express — a per-entry TTL stored on the node, a weighted bound, an eviction listener, a second index over the same nodes. Under concurrency you would ship neither and use Caffeine, because an access-order structure mutates on read and a single lock therefore serialises every reader ([01c1-internals-c2-memory-set-and-caffeine.md](01c1-internals-c2-memory-set-and-caffeine.md), and [../concurrent-collections/01-thread-safety-and-wrappers.md](../concurrent-collections/01-thread-safety-and-wrappers.md)).

**Interview:** "Design an LRU cache" is one of the most-asked design questions there is, and the whole answer is one sentence — **a `HashMap<K, Node>` plus a sentinel-terminated doubly-linked list, both O(1): the map finds the node, the list moves it.** Say that first, then offer the two follow-ups that show you have actually built it: eviction must remove from both indexes, and `LinkedHashMap` already does all of this at 40 bytes an entry instead of your 64.

### Definition

> The hand-rolled LRU trades 24 bytes per entry and ~150 lines for a policy hook, and buys nothing else that `LinkedHashMap` does not already provide.

---

## Pitfalls

### Trusting forward iteration as a correctness check

**Wrong**

```java
// the only check the author wrote
System.out.println(cache);   // prints head.next .. tail.prev, left to right
```

A cache with a broken back chain, a leaked map entry, or a resurrected node prints a plausible order for a long time. Every symptom in section 3 above is invisible to this line except the last one.

**Right**

```java
if (cache.size() != cache.keys().size()) {
    throw new AssertionError("map/list divergence: size=" + cache.size()
            + " listLength=" + cache.keys().size());
}
```

`size()` reads the map and `keys()` walks the list, so comparing them is a two-index consistency check — the cheapest real assertion available, and the one that catches the leak on the operation that causes it.

**Why people believe it:** the list *is* the interesting structure, and printing it is the only debugging tool most people build. It reads the very index that stays correct longest.

### Reading the property test as a performance result

**Wrong**

```java
long start = System.nanoTime();
propertyTest();                    // 300,000 mixed operations plus 3.3 M assertions
System.out.println("mine: " + (System.nanoTime() - start) / 1_000_000 + " ms");
```

Single-shot wall clock in a loop that also runs 3.3 million assertions, on an un-warmed JIT, with the reference implementation interleaved into the same loop and the same caches. The number produced is a measurement of the test harness.

**Right**

Report the correctness result and the byte arithmetic, and if a throughput claim is genuinely needed, write a JMH benchmark with warmup, forks, and a named CPU and JDK build — then quote it with those details attached. Absent that, publish no number.

**Why people believe it:** the loop is right there and `System.nanoTime()` costs one line, so the number feels free. It is not free; it is wrong, and it will be quoted back at you.

---

## Cheat sheet

| Item | Value |
|---|---|
| The eviction rule | `map.remove(victim.key)` **and** `unlink(victim)`, one method, always together |
| Symptom of forgetting the map | `size()` > `capacity`, then eviction stops entirely |
| Second symptom | `get` on an evicted key returns a value *and* relinks the dead node |
| Cheap invariant check | `size() == keys().size()` (map vs list) |
| Defence against resurrection | null the departing node's `prev`/`next` |
| Reference implementation | `LinkedHashMap(16, 0.75f, true)` + `removeEldestEntry: size() > max` |
| Order comparison | `LinkedHashMap.keySet()` is eldest-first; `LruCache.keys()` is LRU-first — directly comparable |
| Test shape | 8 keys, capacity 5, 300,000 ops, fixed seed, assert after every op |
| What is asserted | return value, `size()`, `containsKey` × 8, full recency order |
| Result | 0 divergences over 3.3 M assertions |
| `LinkedHashMap.Entry` | 12 + 4 + 4 + 4 + 4 + 4 + 4 = 36 → **40 B** |
| `HashMap.Node` | 12 + 4 + 4 + 4 + 4 = 28 → **32 B** |
| Hand-rolled `Node` | 12 + 4 + 4 + 4 + 4 = 28 → **32 B** |
| Hand-rolled total | **64 B/entry — 60% more than 40** |
| Assumption | 64-bit HotSpot, compressed oops (heap < 32 GB), 8-byte alignment |
| Sentinel cost | 64 B once, not per entry |
| Ship which one | `LinkedHashMap`, unless you need a hook it cannot express |
| Interview one-liner | `HashMap<K, Node>` + sentinel-terminated doubly-linked list, both O(1) |

---

## Self-test

**Q1.** A hand-rolled cache with `capacity = 2` reports `size() = 5`. Name the bug and both of its downstream symptoms.

<details><summary>Answer</summary>

Eviction unlinked the victim from the list but never called `map.remove(victim.key)`, and `size()` reads the map. Downstream: (1) the fullness test `map.size() == capacity` is never true again, so eviction stops permanently and the list also grows without bound; (2) `get` on an evicted key finds the orphaned node, returns its stale value, and — because `moveToTail` unlinks and relinks unconditionally — splices the dead node back into the list.

</details>

**Q2.** Why is `>=` a *worse* fullness test than `==` in the presence of that leak?

<details><summary>Answer</summary>

With `==`, the leak disables eviction immediately, so the list grows and the bug is visible in the cache's own output within a handful of operations. With `>=`, eviction keeps working, the list stays correctly bounded, and only the map grows — a pure heap leak with no functional symptom, which can survive every test and every code review and only present in production as unexplained retention.

</details>

**Q3.** Why compare against `java.util.LinkedHashMap` rather than writing assertions about expected recency orders by hand?

<details><summary>Answer</summary>

Because hand-written assertions only cover the cases the author imagined, and the author is the same person who wrote the bug. A differential test compares *everything observable after every operation* against an implementation that is already known-correct, over a random walk nobody designed — so it finds the case the author did not think of, such as a re-`put` of an existing key needing to count as an access.

</details>

**Q4.** Why is the key space (8) deliberately much smaller than the operation count (300,000)?

<details><summary>Answer</summary>

To make the interesting events common: hits, evictions, re-`put`s of live keys, removals of absent keys, and repeated recency reordering all occur constantly at capacity 5 over 8 keys. A large key space would produce an almost pure stream of misses and insertions, exercising eviction but never the access-order paths that are the hard part.

</details>

**Q5.** Derive the 64 bytes per entry, and say what the comparable `LinkedHashMap` figure is.

<details><summary>Answer</summary>

Compressed oops, 64-bit HotSpot: `HashMap.Node` is 12 (header) + 4 (`hash`) + 4 (`key`) + 4 (`value`) + 4 (`next`) = 28, aligned to 32. The hand-rolled `Node` is 12 + 4 (`key`) + 4 (`value`) + 4 (`prev`) + 4 (`next`) = 28, aligned to 32. Total 64 per entry. `LinkedHashMap.Entry` adds `before` and `after` to `HashMap.Node`: 28 + 8 = 36, aligned to 40. So 64 against 40 — 60% more, of which 12 bytes is the second object's header.

</details>

**Q6.** What does passing the property test *not* prove?

<details><summary>Answer</summary>

Anything outside the compared surface. `LruCache` implements no `Map` interface, has no `entrySet`, no `equals`/`hashCode`, no serialisation, no fail-fast iteration, no defined null-key semantics, and no thread safety; the test reads only return values, `size()`, `containsKey`, and recency order. It also proves nothing about performance — the loop is dominated by its own assertions.

</details>

**Q7.** Why null out `victim.prev` and `victim.next` after evicting, when the node is unreachable anyway?

<details><summary>Answer</summary>

It is not unreachable if anything still holds a reference to it — a leaked map entry, a caller-held node, a debugger, a partially-updated data structure. Relinking a node whose pointers still name live neighbours splices a dead entry back into the list silently; relinking one whose pointers are null throws `NullPointerException` at the site of the mistake. Nulling converts a class of silent corruption into an immediate, located failure.

</details>

---

**Leaves covered:** 4.6.2 (part 2 of 2, continued from 02) (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none new — the map-plus-linked-list structure (D-148) is embedded in [02-build-lru-by-hand.md](02-build-lru-by-hand.md)
**Target version:** Java 21 LTS
**Lines:** 520
