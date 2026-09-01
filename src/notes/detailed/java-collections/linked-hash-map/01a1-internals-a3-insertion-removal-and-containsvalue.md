# 02 Java Collections — `LinkedHashMap` — INTERNALS (§3.7 `LinkedHashMap` source walk — `afterNodeInsertion`, `afterNodeRemoval`, `containsValue` and `removeEldestEntry`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [linked-hash-map/01a-internals-a2-hooks-and-access-order.md](01a-internals-a2-hooks-and-access-order.md) · Next: [linked-hash-map/01b-internals-b-lru-and-sequenced.md](01b-internals-b-lru-and-sequenced.md)

---

## Where this picks up

[`01-internals.md`](01-internals.md) covered the overlay and the four allocation overrides — how the chain gets built. [`01a-internals-a2-hooks-and-access-order.md`](01a-internals-a2-hooks-and-access-order.md) covered `afterNodeAccess` and what counts as an access — how the chain gets reordered.

This file covers the remaining two hooks and the two methods that hang off them: what happens when an entry is added (and possibly evicted), what happens when one is removed, and the one method `LinkedHashMap` overrides for *speed* rather than for ordering.

The `linkNodeAtEnd` half of leaf 3.7.3 — including the JDK 8 `linkNodeLast` rename and its three-version table — is in [`01-internals.md`](01-internals.md), because it is meaningless without the four allocation overrides that call it. This file takes the leaf's other half, `afterNodeInsertion`.

---

## `afterNodeInsertion` — the eviction trigger (leaf 3.7.3)

### Mental model

`HashMap` ends every successful insertion by asking a question it does not care about the answer to: "anything you want to do about that?" `LinkedHashMap` answers by evicting the head, if you told it to.

### Why it exists

Bounded caches. Without this hook, capping a map means checking the size yourself after every write and finding the oldest key — which on a plain `HashMap` is an O(n) scan, because nothing records order. The hook plus the overlay makes eviction O(1) and, more importantly, makes it *impossible to forget*: it runs on every insertion path, including the ones you did not think about (`computeIfAbsent`, `merge`, `putAll`).

### When to rely on it, and when not

Rely on it for a single-threaded bounded cache with a simple policy. Do not rely on it for anything with concurrency, TTL, weight-based sizing, refresh-ahead or hit statistics — the sibling that wins there is Caffeine, and leaf 3.7.17 in [`01b-internals-b-lru-and-sequenced.md`](01b-internals-b-lru-and-sequenced.md) makes that case properly. The intermediate option, `Collections.synchronizedMap` around an access-order `LinkedHashMap`, buys correctness but serialises every read.

### The mechanism

```java
    void afterNodeInsertion(boolean evict) { // possibly remove eldest
        LinkedHashMap.Entry<K,V> first;
        if (evict && (first = head) != null && removeEldestEntry(first)) {
            K key = first.key;
            removeNode(hash(key), key, null, false, true);
        }
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 322. (leaf 3.7.3, second half)

Called from `putVal`'s last statement, `afterNodeInsertion(evict)` (`HashMap.java`:670), and from `computeIfAbsent`/`compute`/`merge` with a hard-coded `true` (lines 1246, 1344, 1415).

Three guards, in order: eviction is enabled; the map is non-empty; and the user's policy says yes. Then one `removeNode` on the head. It re-derives the hash from the key rather than reading `first.hash` — a redundant but harmless recomputation. `removeNode` in turn calls `afterNodeRemoval`, which unlinks the evicted entry from the chain.

**Where `evict` comes from, and why it matters.** `putVal` receives it from its caller. `put` passes `true`. `putAll` calls `putMapEntries(m, true)` (`HashMap.java`:791). The **copy constructor** calls `putMapEntries(m, false)` (`HashMap.java`:492), and so does `clone` (line 1473). So a bounded LRU subclass built by copy constructor **does not evict while being built** and can exceed its own bound.

A picture would help here — the control flow from `put` down through `putVal` to `afterNodeInsertion` to `removeNode` back up to `afterNodeRemoval` — but there is no diagram in the manifest for it; follow the citations in order instead.

### Concrete, and it is surprising

```java
import java.util.*;

public class EvictPaths {
    static final class Bounded<K,V> extends LinkedHashMap<K,V> {
        private final int cap;
        Bounded(int cap) { super(16, 0.75f, false); this.cap = cap; }
        Bounded(int cap, Map<? extends K, ? extends V> src) { super(src); this.cap = cap; }
        @Override protected boolean removeEldestEntry(Map.Entry<K,V> eldest) { return size() > cap; }
    }

    public static void main(String[] a) {
        Map<Integer,String> source = new LinkedHashMap<>();
        for (int i = 0; i < 10; i++) source.put(i, "v" + i);

        Bounded<Integer,String> byPut = new Bounded<>(3);
        source.forEach(byPut::put);
        System.out.println("built with put()             size=" + byPut.size() + " " + byPut.keySet());

        Bounded<Integer,String> byPutAll = new Bounded<>(3);
        byPutAll.putAll(source);
        System.out.println("built with putAll()          size=" + byPutAll.size() + " " + byPutAll.keySet());

        Bounded<Integer,String> byCopy = new Bounded<>(3, source);
        System.out.println("built with copy constructor  size=" + byCopy.size() + " " + byCopy.keySet());

        byCopy.put(99, "late");
        System.out.println("  after one more put()       size=" + byCopy.size() + " " + byCopy.keySet());
        for (int k : new int[]{98, 97, 96, 95, 94, 93, 92}) byCopy.put(k, "late");
        System.out.println("  after 8 puts total         size=" + byCopy.size() + " " + byCopy.keySet());
    }
}
```

Real output, JDK 21.0.7+8-LTS-245:

```
built with put()             size=3 [7, 8, 9]
built with putAll()          size=3 [7, 8, 9]
built with copy constructor  size=10 [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  after one more put()       size=10 [1, 2, 3, 4, 5, 6, 7, 8, 9, 99]
  after 8 puts total         size=10 [8, 9, 99, 98, 97, 96, 95, 94, 93, 92]
```

Two calls people treat as interchangeable — `new Bounded<>(3, source)` and `new Bounded<>(3)` followed by `putAll(source)` — differ by more than a factor of three in resulting size. (There is a second, independent reason the copy-constructor case cannot work: `super(src)` runs before `this.cap = cap`, so `removeEldestEntry` would read `cap == 0` even if it were called. Both problems have the same fix: never populate a bounded map through the copy constructor.)

**One eviction per insertion, and no recursion.** `afterNodeInsertion` calls `removeNode`, which calls `afterNodeRemoval` — but never `afterNodeInsertion`. There is no loop, and exactly one entry leaves per insertion. The trace above shows the operational consequence: an over-bound map **drains one entry per subsequent `put`**, not all at once. After eight extra puts the map is still at 10, not 3, because each put removes one and adds one. If you shrink a cache's bound at runtime, the excess bleeds off over the next N writes rather than immediately — and if writes stop, it never bleeds off at all.

### Gotcha

`removeEldestEntry` is consulted only on *insertion of a new key*. Updating an existing key goes down `putVal`'s update branch and returns at line 663 — before line 670 — so a cache that only ever overwrites existing keys never evicts, however far over its bound a prior mistake left it.

> **Definition.** `afterNodeInsertion(boolean evict)` is the post-insert hook where `LinkedHashMap` consults `removeEldestEntry` and, if it says yes, removes exactly one entry from the head — the entire eviction mechanism of `java.util`.

---

## Supporting facts

### `afterNodeRemoval` (leaf 3.7.5)

```java
    void afterNodeRemoval(Node<K,V> e) { // unlink
        LinkedHashMap.Entry<K,V> p =
            (LinkedHashMap.Entry<K,V>)e, b = p.before, a = p.after;
        p.before = p.after = null;
        if (b == null)
            head = a;
        else
            b.after = a;
        if (a == null)
            tail = b;
        else
            a.before = b;
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 308. (leaf 3.7.5)

The mirror of `afterNodeAccess`'s first half, with both endpoint cases handled instead of one: `b == null` means the removed node was the head, `a == null` means it was the tail, and removing the only entry hits both and leaves `head == tail == null`. `HashMap.removeNode` calls it after unlinking from the bin ([`../hash-map/05a-internals-e1-removal-and-iteration-order.md`](../hash-map/05a-internals-e1-removal-and-iteration-order.md), leaf 3.6.41). It does **not** bump `modCount` — `removeNode` already did that, since removal is structural under anyone's definition.

The gotcha worth naming is `p.before = p.after = null`: it nulls the departing node's own links, so a removed entry held by a stale `Map.Entry` reference does not keep its former neighbours — and through them the rest of the map — reachable. GC help, not correctness.

> **Definition.** `afterNodeRemoval` splices a node out of the overlay and nulls its own links, leaving the chain and both endpoints consistent.

### `containsValue` (leaf 3.7.7)

```java
    public boolean containsValue(Object value) {
        for (LinkedHashMap.Entry<K,V> e = head; e != null; e = e.after) {
            V v = e.value;
            if (v == value || (value != null && value.equals(v)))
                return true;
        }
        return false;
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 510. (leaf 3.7.7)

Both this and `HashMap`'s version are O(n) — so why override? Three reasons:

1. **It visits `size` nodes, not `capacity` slots.** `HashMap.containsValue` scans the whole table array. A map that grew to a million entries and then shrank to three still has a million-slot table, because `HashMap` never shrinks ([`../hash-map/05a-internals-e1-removal-and-iteration-order.md`](../hash-map/05a-internals-e1-removal-and-iteration-order.md)).
2. **It returns in encounter order**, so "the first entry with this value" is well defined.
3. **It never touches the table**, so it is immune to bin structure — no `TreeNode` branch, no per-bin list walk.

Reason 1 measured. Both maps filled to 1,000,000 then reduced to 3; timing a miss (`containsValue("absent")`, the worst case), 3 warmup rounds of 200 calls, then 500 timed calls. Apple M4 Pro, JDK 21.0.7+8-LTS-245, `-Xmx3g`:

```java
static long timeMissingValue(Map<Integer,String> m, int reps) {
    long t0 = System.nanoTime();
    boolean sink = false;
    for (int i = 0; i < reps; i++) sink ^= m.containsValue("absent");
    long t1 = System.nanoTime();
    if (sink) System.out.print("");
    return (t1 - t0) / reps;
}
static void fillThenShrink(Map<Integer,String> m) {
    for (int i = 0; i < 1_000_000; i++) m.put(i, "v" + i);
    for (int i = 0; i < 1_000_000 - 3; i++) m.remove(i);
}
public static void main(String[] a) {
    Map<Integer,String> hm = new HashMap<>();
    Map<Integer,String> lhm = new LinkedHashMap<>();
    fillThenShrink(hm); fillThenShrink(lhm);
    System.out.println("both maps size = " + hm.size() + " / " + lhm.size());
    for (int w = 0; w < 3; w++) { timeMissingValue(hm, 200); timeMissingValue(lhm, 200); }
    System.out.println("HashMap.containsValue        " + timeMissingValue(hm, 500) + " ns/call");
    System.out.println("LinkedHashMap.containsValue  " + timeMissingValue(lhm, 500) + " ns/call");
}
```

```
both maps size = 3 / 3
HashMap.containsValue        569930 ns/call
LinkedHashMap.containsValue  39 ns/call
```

**Unverified:** absolute figures are a single unpinned run on a laptop, not a JMH benchmark; the ~14,000x ratio is the claim, not the nanoseconds. See [Open questions](#open-questions).

**Insight:** this is the *only* place the overlay makes an operation faster rather than slower. Every other method pays 8 bytes and four pointer writes for ordering; `containsValue` gets a genuine algorithmic win, O(size) instead of O(capacity).

Note the identity-then-equals test, `v == value || (value != null && value.equals(v))`: it finds a stored `null` when you search for `null`, via the `==` arm, and never calls `equals` on the search argument if it is `null`. `values().contains(v)` delegates here, so it inherits both the speed and the null handling — and, per the access-surface table in [`01a-internals-a2-hooks-and-access-order.md`](01a-internals-a2-hooks-and-access-order.md), neither counts as an access.

> **Definition.** `LinkedHashMap.containsValue` walks the encounter chain rather than the table, making it proportional to `size` rather than to `capacity`.

### `removeEldestEntry` (leaf 3.7.9)

```java
    protected boolean removeEldestEntry(Map.Entry<K,V> eldest) {
        return false;
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 604. (leaf 3.7.9)

Nine words of code that are the entire caching API of `java.util`. `protected`, so overriding it is the sanctioned extension point; returning `false` by default, so a plain `LinkedHashMap` never evicts.

The parameter is the payload: it hands you the **eldest entry**, not just a signal. The decision can therefore depend on the key, the value, or a timestamp stored in the value — `return eldest.getValue().expiredAt() < now()` is as legal as `return size() > MAX`, and you can pin entries by key. Most write-ups only ever show the size form, which hides the hook's real range.

Two gotchas. First, it is invoked *after* the new entry is already in the map, so `size()` inside it is the post-insert size: a bound of N is written `size() > N`, not `size() >= N`. Second, it is only ever asked about the head, so it is a "should the oldest go?" question, not a general sweep — you cannot use it to evict a specific mid-chain entry.

The word "eldest" comes straight from the `head` field's javadoc, *"The head (eldest) of the doubly linked list"* (leaf 3.7.2, in [`01-internals.md`](01-internals.md)). On an access-order map, eldest means least recently used, and that identity is the whole LRU idea. The ten-line LRU built on this, and the four bugs people put in it, are leaf 3.7.10 in [`01b-internals-b-lru-and-sequenced.md`](01b-internals-b-lru-and-sequenced.md); an LRU built by hand from `HashMap` plus your own doubly-linked list is §4.6.2 in [`02-build-lru-by-hand.md`](02-build-lru-by-hand.md).

> **Definition.** `removeEldestEntry` is a protected policy hook, consulted after every eviction-enabled insertion, that decides whether the head entry should be dropped.

### `clear`

```java
    public void clear() {
        super.clear();
        head = tail = null;
    }
```
— `java.base/java/util/LinkedHashMap.java`, JDK 21, line 558.

`HashMap.clear` nulls the table slots but knows nothing about the chain, so the two endpoints must be dropped here or the whole cleared graph stays reachable through `head`. `reinitialize()` (line 275) does the same for the deserialization path. There is no per-node unlinking: dropping `head` and `tail` orphans the entire chain at once, and the nodes' surviving `before`/`after` links only point at each other.

> **Definition.** `clear` delegates the table wipe to `HashMap` and drops the two overlay endpoints, releasing the chain in one write.

---

## Version behaviour of these members

| Member | JDK 8 line | JDK 17 | JDK 21 | Changed? |
|---|---|---|---|---|
| `afterNodeInsertion` | 297 | same | 322 | identical body |
| `afterNodeRemoval` | 283 | same | 308 | identical body |
| `containsValue` | 414 | same | 510 | identical body |
| `clear` | 462 | same | 558 | identical body |
| `removeEldestEntry` | 508 | 509 | 604 | identical body |

Every member in this file is **byte-identical across JDK 8, 17 and 21** — only the line numbers moved. Nothing here was touched by the Java 21 `SequencedMap` work, which is confined to `putMode`, `linkNodeAtEnd`, `afterNodeAccess`, `putFirst`/`putLast` and the reverse-order view. Confirmed by comparing the extracted method bodies from `/tmp/jdk8src`, `/tmp/jdk17src` and `/tmp/jdk21src`.

---

## Pitfalls

### Populating a bounded LRU with the copy constructor

**Wrong**
```java
class Bounded<K,V> extends LinkedHashMap<K,V> {
    private final int cap;
    Bounded(int cap, Map<K,V> src) { super(src); this.cap = cap; }
    @Override protected boolean removeEldestEntry(Map.Entry<K,V> e) { return size() > cap; }
}
new Bounded<>(3, tenEntries).size();   // 10
```

**Right**
```java
var b = new Bounded<Integer,String>(3);
b.putAll(tenEntries);                  // putMapEntries(m, true) -> evicts as it goes
b.size();                              // 3
```

**Why people believe it:** `putAll` and the copy constructor look like the same operation. They differ in one boolean — `putMapEntries(m, true)` at `HashMap.java`:791 versus `putMapEntries(m, false)` at :492 — and a field initialiser cannot run before `super(...)`, so the bound is still `0` during the copy anyway.

### Expecting an over-bound cache to snap back to size

**Wrong**
```java
// bound lowered from 100 to 10 at runtime; map currently holds 100
for (int i = 0; i < 5; i++) cache.put(newKey(i), v);
// "five puts, so it should be draining fast"  -> still 100
```

**Right** — `afterNodeInsertion` evicts exactly one entry per insertion and never recurses, so each `put` of a new key adds one and removes one and the size never falls. Drain explicitly:
```java
while (cache.size() > bound) cache.remove(cache.keySet().iterator().next());
```

**Why people believe it:** "evict until under the bound" is what every cache library does. `LinkedHashMap` evicts *at most one entry per insertion*, which is a different policy.

### Writing `size() >= cap` in `removeEldestEntry`

**Wrong**
```java
@Override protected boolean removeEldestEntry(Map.Entry<K,V> e) { return size() >= 3; }
// bounded at 3 -> map actually settles at 2
```
The hook runs *after* the new entry is in the map, so on the insert that brings the map to 3, `size()` is already 3, `>=` fires, and one is evicted — leaving 2.

**Right**
```java
@Override protected boolean removeEldestEntry(Map.Entry<K,V> e) { return size() > 3; }
```

**Why people believe it:** every other capacity check in Java is written against the size *before* the add. This one is not, because the hook's whole point is to inspect the map's post-insert state.

### Assuming an overwrite can trigger eviction

**Wrong**
```java
// map is over its bound; only existing keys are ever written
for (var k : hotKeys) cache.put(k, refresh(k));   // never evicts anything
```
`putVal`'s update branch returns at line 663, before `afterNodeInsertion(evict)` at line 670. Only insertion of a *new* key reaches the hook.

**Right** — if you need eviction on write regardless of novelty, check the size yourself after the write, or remove-then-put (which makes the second call an insertion). Note that remove-then-put also moves the entry to the tail on an insertion-order map, which may not be what you want.

**Why people believe it:** `put` is `put`. The method comment on `afterNodeAccess`, *"Called after update, but not after insertion"*, is the exact mirror of this — the two hooks partition `put` between them and neither fires twice.

### Reaching for `containsValue` as though it were cheap on either map type

**Wrong**
```java
if (bigMap.containsValue(needle)) respond(200);   // in a request path
```
O(n) on both types. On a `HashMap` it is O(capacity), which on a shrunken map is far worse than O(size) — 570 µs versus 39 ns measured.

**Right** — maintain a reverse index (`Map<V, Set<K>>`) if you need value lookups, or use a `BiMap`-style structure. If you only need it occasionally and the map is a `LinkedHashMap`, the chain walk at least scales with live entries.

**Why people believe it:** `containsKey` is O(1), and the two method names are one word apart.

---

## Cheat sheet

| Thing | Fact |
|---|---|
| `afterNodeInsertion` | `LinkedHashMap.java`:322 — the eviction trigger |
| Its three guards | `evict` is true, `head != null`, `removeEldestEntry(head)` returns true |
| Called from | `putVal`:670; `computeIfAbsent`:1246, `compute`:1344, `merge`:1415 (all hard-coded `true`) |
| `evict == true` | `put`, `putAll` (`putMapEntries(m, true)`, `HashMap.java`:791) |
| `evict == false` | copy constructor (`putMapEntries(m, false)`, :492) and `clone` (:1473) |
| Copy-constructor consequence | a bounded LRU built by copy exceeds its own bound — measured 10 against a cap of 3 |
| Eviction rate | exactly one entry per insertion; no recursion, so over-bound maps never drain |
| Eviction trigger | **new-key insertion only** — pure overwrites return at `putVal`:663 and never reach the hook |
| `removeEldestEntry` | `LinkedHashMap.java`:604 — `protected`, returns `false`, nine words |
| Its argument | the eldest **entry**, so policies can read key, value or an embedded timestamp |
| `size()` inside it | post-insert — a bound of N is `size() > N`, not `>=` |
| Its scope | asked only about the head; cannot evict a mid-chain entry |
| `afterNodeRemoval` | `LinkedHashMap.java`:308 — four-branch unlink, mirror of `afterNodeAccess`'s first half |
| Does it bump `modCount`? | no — `removeNode` already did |
| `p.before = p.after = null` | GC help: a removed entry held by a stale `Map.Entry` does not retain its neighbours |
| `containsValue` | `LinkedHashMap.java`:510 — walks `head`/`after`, so O(size) not O(capacity) |
| Measured | 569,930 ns (`HashMap`) vs 39 ns (`LinkedHashMap`) on a 1M-grown map holding 3 entries |
| Why it is the odd one out | the only method where the overlay makes something *faster* |
| Its null handling | `v == value \|\| (value != null && value.equals(v))` — finds a stored `null`, never calls `equals` on a null argument |
| `clear` | `LinkedHashMap.java`:558 — `super.clear()` then `head = tail = null`; no per-node unlinking |
| `reinitialize` | :275 — same endpoint reset, for the deserialization path |
| Version status | every member in this file is byte-identical across JDK 8, 17 and 21 |

---

## Self-test

**Q1.** A bounded LRU with `removeEldestEntry` returning `size() > 3` currently holds 10 entries because it was built by copy constructor. How many puts until it is back to 3?

<details><summary>Answer</summary>

It never gets back to 3 by putting new keys. `afterNodeInsertion` evicts exactly one entry per insertion and does not recurse, so each `put` of a new key adds one and removes one — size stays at 10 forever. Only explicit `remove` calls will bring it down. Measured: after eight further puts the map is still size 10.

The root cause is that the copy constructor calls `putMapEntries(m, false)` (`HashMap.java`:492), so `evict` is `false` throughout construction. (`this.cap` is also still 0 during `super(src)`, so the policy could not have fired correctly anyway.)

</details>

**Q2.** What is the point of `p.before = p.after = null` in `afterNodeRemoval`?

<details><summary>Answer</summary>

GC help. Once the node is out of the chain, its own outgoing links would otherwise keep both neighbours — and transitively the whole map — reachable from any stale reference to the removed entry (for example a `Map.Entry` held by application code after an `entrySet().iterator().remove()`). Nulling them bounds the retained set to the single dead node.

</details>

**Q3.** Both `HashMap.containsValue` and `LinkedHashMap.containsValue` are O(n). Why override it?

<details><summary>Answer</summary>

The two n's differ. `HashMap`'s scans the table array, so it is O(capacity); `LinkedHashMap`'s walks `head`/`after`, so it is O(size). Since `HashMap` never shrinks its table, a map that held a million entries and now holds three still costs a million-slot scan — measured at 570 µs versus 39 ns on JDK 21. Secondary reasons: the chain walk returns in encounter order, so "the first matching value" is well defined, and it never touches the table, so it is immune to bin structure.

This is also the only override in the whole class where the overlay makes an operation *faster*.

</details>

**Q4.** `removeEldestEntry` takes a `Map.Entry`, not an `int size`. What does that buy you, and what does it not?

<details><summary>Answer</summary>

It buys policies that depend on the entry, not just the count: `return eldest.getValue().expiredAt() < System.currentTimeMillis()` is as legal as `return size() > MAX`, and you can pin specific keys. Nearly every tutorial only shows the size form, which hides the range.

It does not buy a general sweep. The hook is consulted only on new-key insertion, only about the *head* entry, and at most once per insertion — so it answers "should the oldest go?" and cannot be used to evict a specific mid-chain entry or to drain multiple entries at once.

</details>

**Q5.** Your cache is over its bound and every write from now on is an overwrite of an existing key. Does it ever shrink?

<details><summary>Answer</summary>

No. `putVal` returns from its update branch at `HashMap.java`:663 — after calling `afterNodeAccess(e)` — and never reaches `afterNodeInsertion(evict)` at line 670. The eviction hook is only consulted when a *new* key is inserted. Overwrites are invisible to it, so the map stays over bound indefinitely. The two hooks partition `put` between them: `afterNodeAccess` for updates ("Called after update, but not after insertion"), `afterNodeInsertion` for insertions.

</details>

**Q6.** Why does a bounded map written with `return size() >= cap` settle at `cap - 1`?

<details><summary>Answer</summary>

`afterNodeInsertion` runs after the new entry is already installed and `size` already incremented. On the insert that takes the map to `cap`, `size()` reads `cap`, `>=` is true, and the head is evicted — leaving `cap - 1`. The next insert repeats it. Correct form is `size() > cap`, which lets the map hold exactly `cap` and evicts only on the insert that would take it to `cap + 1`.

</details>

**Q7.** Trace the call chain from `cache.put(k, v)` on a full bounded LRU through to the evicted entry leaving the chain.

<details><summary>Answer</summary>

`put` → `putVal(hash, k, v, false, true)`. The key is new, so `newNode` allocates a `LinkedHashMap.Entry` and `linkNodeAtEnd` appends it to the tail. `putVal` increments `size`, possibly resizes, then calls `afterNodeInsertion(true)` at line 670. That reads `head`, calls `removeEldestEntry(head)`, gets `true`, and calls `removeNode(hash(headKey), headKey, null, false, true)`. `removeNode` unlinks the node from its bin, bumps `modCount`, decrements `size`, and calls `afterNodeRemoval(e)`, which splices the node out of the overlay (`head = a`, since it was the head) and nulls its own `before`/`after`. No recursion: `removeNode` never calls `afterNodeInsertion`.

</details>

**Q8.** `map.containsValue(null)` on a `LinkedHashMap` holding a `null` value — does it find it, and does it risk an NPE?

<details><summary>Answer</summary>

It finds it, and there is no NPE risk. The test is `v == value || (value != null && value.equals(v))`. With `value == null`, the `==` arm matches any stored `null` and returns `true`; the second arm short-circuits on `value != null` so `equals` is never called on the null argument. With a non-null `value` and a stored `null`, `==` is false and `value.equals(null)` is a legal call that returns false. `values().contains(null)` delegates here and inherits both properties.

</details>

---

## Open questions

- **The `containsValue` timings.** 569,930 ns (`HashMap`) versus 39 ns (`LinkedHashMap`) is a single unpinned run on an Apple M4 Pro under JDK 21.0.7+8-LTS-245 with `-Xmx3g`, warmed with three rounds of 200 calls and averaged over 500 — not JMH, no forks, no CPU pinning, no GC isolation. The ~14,000x ratio is robust to all of that (it is `capacity/size` = 1,048,576/3 modulo constant factors); the absolute nanoseconds are **Unverified**. **What would settle it:** a JMH benchmark with `@Fork(3)`, `@BenchmarkMode(AverageTime)` and an explicit `Blackhole`, on a pinned core.

---

**Leaves covered:** 3.7.3, 3.7.5, 3.7.7, 3.7.9 (4 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — the overlay (D-100) is in [01-internals.md](01-internals.md) and the relink walk (D-101) is in [01a-internals-a2-hooks-and-access-order.md](01a-internals-a2-hooks-and-access-order.md)
**Target version:** Java 21 LTS
**Lines:** 442
