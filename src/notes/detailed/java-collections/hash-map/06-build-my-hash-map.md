# 02 Java Collections — `HashMap` — INTERNALS (§4.3 `MyHashMap<K,V>` — `Node`, the field set, and the two bit tricks)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [hash-map/05c-internals-e4-hashtable-and-prime-modulus.md](05c-internals-e4-hashtable-and-prime-modulus.md) · Next: [hash-map/06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md)

---

Six files from here you will have three source files on disk that compile with `javac -Xlint:all`, produce zero warnings, and agree with `java.util.HashMap` on every return value across 200,000 randomised mixed operations. This file lays the first layer: the class declaration and what it buys, the node, the constant set, the field set, and the two bit tricks that everything else stands on.

**How the code blocks assemble.** `MyHashMap.java` is the concatenation, in order, of every code block labelled `// MyHashMap.java` in this file followed by every such block in [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), [07](07-build-my-hash-map-b-put-get-resize.md), [08](08-build-my-hash-map-c-treeify-and-defaults.md) and [09](09-build-my-hash-map-d-views-and-iterator.md); file 09 closes the class. `MyHashSet.java` and `MyLinkedHashMap.java` are single blocks in [10](10-build-my-hash-map-e-set-linked-and-diff.md). `LruCache.java` is a single block in 10; `Demo.java` is in [10a](10a-build-my-hash-map-f-the-demo-harness.md) and `Bench.java` in [10b](10b-build-my-hash-map-g-diff-and-collision-dos.md). Type them in file order and it runs.

Everything printed on these pages is real output from the code as published, captured on **Apple M4 Pro, `javac 21.0.7` / `java 21.0.7+8-LTS-245`, arm64**.

---

## 1. The class declaration, and what you get for free

### Why `extends AbstractMap<K,V> implements Map<K,V>`

**Mental model.** A `Map` implementation has two halves: a *storage engine* (buckets, hashing, resizing) and a *collections façade* (`equals`, `hashCode`, `toString`, `putAll`, `isEmpty`). Only the first half is interesting. `AbstractMap` is a pre-built façade that derives the whole second half from one method — `entrySet()`. You write the engine; you inherit the façade.

**Why it exists.** Before `AbstractMap` (JDK 1.2), every `Map` re-implemented `equals` and `toString`, and they disagreed. `AbstractMap.equals` defines map equality once — same size, and every entry of `this` present-and-equal in the other map — so `myMap.equals(javaUtilMap)` works across implementations. That cross-implementation contract is why `Demo` can assert `x.equals(java.util.Map.of("a",1,"b",2)) == true` about a hand-rolled map.

**When to reach for it, and when not.** Extend `AbstractMap` when you are writing a general-purpose `Map` and want the contract right by construction. Do *not* extend it when every inherited method would be O(n) and callers will hit them hot — a fixed-key enum map is better off implementing `Map` directly and overriding everything.

**How it works.** `java.util.HashMap` declares itself exactly this way, line 137 of `/tmp/jdk21src/java.base/java/util/HashMap.java`:

```
public class HashMap<K,V> extends AbstractMap<K,V>
    implements Map<K,V>, Cloneable, Serializable
```

The `implements Map<K,V>` is redundant — `AbstractMap` already implements it — and Josh Bloch has called it a mistake that stayed for documentation value. We mirror it, minus `Cloneable` and `Serializable`: both add surface without adding mechanism, and `Serializable` would drag in `writeObject`/`readObject` and the `serialVersionUID` discipline.

**What we inherit and deliberately do not override:**

| Inherited from `AbstractMap` | Cost as inherited | Our decision |
|---|---|---|
| `equals(Object)` | O(n) over `entrySet()`, one `get` per entry | keep — correct and rarely hot |
| `hashCode()` | O(n), sums entry hash codes | keep — same as the JDK |
| `toString()` | O(n) | keep — same as the JDK |
| `putAll(Map)` | O(m) `put` calls | keep — the JDK overrides only to pre-size |
| `isEmpty()` | `size() == 0`, and `size()` is `entrySet().size()` | **override** — return `size == 0` |
| `size()` | `entrySet().size()`, which walks an iterator | **override** — return the `size` field |
| `containsValue(Object)` | O(n) via an `entrySet()` iterator, allocating an `Entry` view per step | **override** in file 09 — direct table scan, no iterator |
| `keySet()` / `values()` | lazily built from `entrySet()`, cached in `AbstractMap`'s own fields | **override** in file 09 — see below |

`size()` and `isEmpty()` must be overridden or every `map.size()` is a full iteration; that is not an optimisation, it is a correctness-of-cost requirement. `containsValue` we override for the reason the JDK does (line 882): the inherited version allocates one `Entry` view per element.

**Pitfall:** `AbstractMap`'s `keySet` and `values` cache fields are **package-private** in `java.util`, not `protected`. From outside `java.util` you cannot use them, so you must declare your own cache fields. This is the first of two places in this build where the JDK's own extension surface is unavailable to you; the second is `comparableClassFor` in [file 08](08-build-my-hash-map-c-treeify-and-defaults.md). Read the JDK's design as "how it works", not as "what you can call".

> **Definition.** `AbstractMap<K,V>` is a skeletal `Map` implementation that derives the whole `Map` contract — equality, hashing, printing, bulk operations, and the key and value views — from a single abstract method, `entrySet()`.

---

## 2. `Node<K,V>` and the cached hash

**Mental model.** A node is a four-field record that happens to be mutable in two fields: `(hash, key, value, next)`. Think of `hash` not as metadata but as *the key's coordinate*, computed once at insertion and never recomputed. Every later comparison against this node starts by comparing two `int`s, and only if those match does anyone touch `equals`.

**Why it exists.** Without the cached hash, every chain step would call `key.hashCode()`. For a `String` that is a memoised field read, so cheap; for a `List` key it is a full traversal. Worse, resize would have to rehash every key in the table. Caching turns resize from "n `hashCode()` calls" into "n bitwise ANDs" — the single largest reason `HashMap` resize is fast.

**When it does not help.** If keys are `Integer`, `hashCode()` is a field read and the cached `int` costs 4 bytes per entry for nothing. `HashMap` pays it anyway because it cannot know. A specialised `IntMap` would not.

**How it works.** JDK 21 `HashMap.Node`, line 281:

```
static class Node<K,V> implements Map.Entry<K,V> {
    final int hash;
    final K key;
    V value;
    Node<K,V> next;
```

`hash` and `key` are `final`, `value` and `next` are not. That is exactly right: an entry's identity never changes, its payload and its chain position do. Ours is identical, plus the `Map.Entry` methods written out.

```java
// MyHashMap.java
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.AbstractCollection;
import java.util.AbstractMap;
import java.util.AbstractSet;
import java.util.Arrays;
import java.util.Collection;
import java.util.ConcurrentModificationException;
import java.util.Iterator;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Set;
import java.util.function.BiFunction;
import java.util.function.Function;

public class MyHashMap<K, V> extends AbstractMap<K, V> implements Map<K, V> {

    static final int DEFAULT_INITIAL_CAPACITY = 1 << 4;   // 16
    static final int MAXIMUM_CAPACITY = 1 << 30;
    static final float DEFAULT_LOAD_FACTOR = 0.75f;
    static final int TREEIFY_THRESHOLD = 8;
    static final int MIN_TREEIFY_CAPACITY = 64;

    static class Node<K, V> implements Map.Entry<K, V> {
        final int hash;
        final K key;
        V value;
        Node<K, V> next;

        Node(int hash, K key, V value, Node<K, V> next) {
            this.hash = hash;
            this.key = key;
            this.value = value;
            this.next = next;
        }

        public final K getKey()   { return key; }
        public final V getValue() { return value; }

        public final V setValue(V newValue) {
            V old = value;
            value = newValue;
            return old;
        }

        public final int hashCode() {
            return Objects.hashCode(key) ^ Objects.hashCode(value);
        }

        public final String toString() { return key + "=" + value; }

        public final boolean equals(Object o) {
            return o == this
                || (o instanceof Map.Entry<?, ?> e
                    && Objects.equals(key, e.getKey())
                    && Objects.equals(value, e.getValue()));
        }
    }
```

Three details worth pausing on. `Node.hashCode()` is `key.hashCode() ^ value.hashCode()` — the `Map.Entry` contract — and is **not** the cached `hash` field; they are different numbers for different purposes, and conflating them is a classic reading error. Every `Map.Entry` method is `final`, so a subclass (`SortedBin` in file 08, `MyLinkedHashMap.Entry` in file 10) cannot accidentally change entry semantics while changing storage. And `equals` uses `instanceof Map.Entry<?,?> e` pattern matching, the Java 21 idiom for what the JDK still writes as a cast.

**Pitfall:** our `Node` has no `transient` modifiers where the JDK's fields do. `transient` is only meaningful for `Serializable` classes; the JDK needs it because `HashMap` serialises entries by hand rather than dumping a half-empty array. We are not `Serializable`, so it would be noise.

**Interview:** *"Why is `Map.Entry.setValue` allowed but there is no `setKey`?"* — Changing the value is a payload write with no structural consequence. Changing the key would change `hash`, which would put the entry in the wrong bucket with no way to find it again; the entry would have to be removed and reinserted, which is exactly what `Map.remove` + `Map.put` is for.

> **Definition.** A `Node` is a bucket-chain link holding an immutable `(hash, key)` identity and a mutable `(value, next)` payload, where `hash` is the spread key hash cached at insertion so that no lookup, chain walk or resize ever recomputes it.

---

## 3. The five constants, and the fields

Supporting facts, so three beats each rather than eight.

| Constant | Value | JDK 21 line | Why this value |
|---|---|---|---|
| `DEFAULT_INITIAL_CAPACITY` | `1 << 4` = 16 | 238 | Power of two so `(n-1) & hash` replaces `%`. 16 is the smallest size where 12 entries (16 × 0.75) fit with no immediate resize. |
| `MAXIMUM_CAPACITY` | `1 << 30` | 245 | `1 << 31` is negative; this is the largest power-of-two positive `int` array length. |
| `DEFAULT_LOAD_FACTOR` | `0.75f` | 250 | The Poisson trade-off point: mean bin occupancy 0.75 gives P(bin length ≥ 8) ≈ 6 × 10⁻⁸. |
| `TREEIFY_THRESHOLD` | 8 | 260 | A bin reaching 8 is so improbable under a good hash that it signals an adversary or a broken `hashCode`. |
| `MIN_TREEIFY_CAPACITY` | 64 | 275 | Below this, a long bin more likely means "table too small" than "hash collision", so resize first. |

We omit `UNTREEIFY_THRESHOLD` (JDK line 267, value 6). Our simplified bin never untreeifies — stated as a diff in file 08 and again in file 10b.

Now the fields.

```java
// MyHashMap.java
    Node<K, V>[] table;
    int size;
    int modCount;
    int threshold;
    final float loadFactor;

    boolean treeifyEnabled = true;

    private Set<Map.Entry<K, V>> entrySetView;
    private Set<K> keySetView;
    private Collection<V> valuesView;
```

**Visibility decision, stated once and held for all seven files: `table`, `size`, `modCount` and `threshold` are package-private, exactly as in `java.util.HashMap` (lines 390–428).** That is the JDK's choice too — `HashMap` and `LinkedHashMap` share a package, so package-private suffices. The consequence you must accept: **`MyLinkedHashMap.java` has to sit in the same package as `MyHashMap.java`.** In this build all files are in the default package, so it works. If you wanted out-of-package extension you would need `protected`, and you would then be committing to those four fields as public API forever — which is precisely why the JDK did not.

`loadFactor` is `final`; there is no setter, and there never was one in `java.util.HashMap` either. `treeifyEnabled` is ours alone, not a JDK field — file 10b's collision-DoS measurement needs to run the same map with the sorted bin on and off, and a flag is honest about that being a test affordance rather than pretending the JDK has one.

**Insight:** `size` and `modCount` are separate counters that move together on structural change and diverge otherwise. `clear()` on an already-empty map bumps `modCount` and leaves `size` at 0; `put` on an existing key bumps neither. Getting that pair right is most of what "fail-fast" means, and file 09 depends on it entirely.

---

## 4. `spread` — the 16-bit XOR fold

**Mental model.** The table index is `(n - 1) & hash`, and for a 16-slot table that is `hash & 0b1111` — only the bottom four bits survive. Every bit above bit 3 is thrown away. `spread` fixes that by folding the top 16 bits down onto the bottom 16 with an XOR, so high-bit structure in a key's hash code still influences which bucket it lands in.

**Why it exists.** A hash function whose entropy lives in the high bits — an object identity hash, a hash built as `id * 31^k`, a `Float.hashCode` — would collide catastrophically under pure masking. The alternative is a stronger hash function, which costs cycles on every operation. Doug Lea's comment (line 330) says it plainly: because the table uses power-of-two masking, *and* because trees catch the residual damage, "we just XOR some shifted bits in the cheapest possible way".

**When it is not enough.** `spread` is a fold, not a mix. It cannot rescue a `hashCode()` that returns a constant, and it cannot rescue two keys whose raw hash codes are already equal. `"Aa"` and `"BB"` both hash to 2112 raw and both spread to 2112. That is the whole basis of the collision-DoS attack measured in file 10b.

**How it works.** JDK 21 line 336:

```
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

Two behaviours in one expression. A `null` key returns 0 unconditionally, which is *why* `null` always lands in bucket 0 and why `HashMap` supports a null key with no special case anywhere else. A non-null key gets `h ^ (h >>> 16)`: `>>>` is the unsigned shift, so the top 16 bits move down and the vacated top bits fill with zero, meaning the high half of the result is unchanged and the low half becomes `high ^ low`.

We rename it `spread` because `hash` reads like a field and collides with `Node.hash` in every reader's head on first pass. The behaviour is identical.

```java
// MyHashMap.java
    static int spread(Object key) {
        int h;
        return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
    }
```

Real output, `Demo` section 1:

```
spread(null)                = 0
spread("Aa")                = 2112  (raw 2112)
spread("BB")                = 2112  (raw 2112)
```

**Pitfall:** `h >> 16` instead of `h >>> 16` is the classic typo. For a negative hash code the signed shift fills with ones, so `h ^ (h >> 16)` flips the high half rather than preserving it, and negative-hash keys cluster. It compiles, it passes small tests, and it degrades quietly at scale.

**Interview:** *"Why does `HashMap` XOR the hash with itself shifted right 16?"* — Because indexing masks off all but the low `log2(capacity)` bits, so high-order entropy would be discarded; the XOR folds it down for one cycle instead of paying for a stronger hash on every operation.

> **Definition.** `spread` is a one-instruction avalanche step, `h ^ (h >>> 16)`, that mixes a hash code's high 16 bits into its low 16 so power-of-two masking does not discard them — and that maps `null` to 0, putting the null key in bucket 0 by construction.

---

## 5. `tableSizeFor` — rounding up to a power of two

**Mental model.** Take the requested capacity, subtract one, then smear the highest set bit rightwards until every lower bit is set; add one and you have the next power of two at or above the request. The JDK gets the smear for free from a single intrinsic.

**Why it exists.** The whole table design depends on capacity being a power of two, so `new HashMap<>(100)` cannot honour 100 literally. Something must round, and rounding *up* is the only choice that does not silently under-provision.

**When you would not need it.** A prime-modulus table — `Hashtable`, and the design compared in [05c](05c-internals-e4-hashtable-and-prime-modulus.md) — takes any capacity and pays a `%` on every operation instead. That is the trade this function encodes.

**How it works.** JDK 21 line 377:

```
static final int tableSizeFor(int cap) {
    int n = -1 >>> Integer.numberOfLeadingZeros(cap - 1);
    return (n < 0) ? 1 : (n >= MAXIMUM_CAPACITY) ? MAXIMUM_CAPACITY : n + 1;
}
```

`-1` is all thirty-two bits set. `Integer.numberOfLeadingZeros(cap - 1)` is a HotSpot intrinsic compiling to a single `clz` on arm64 and `lzcnt` on x86. Shifting all-ones right by that count leaves exactly a run of ones as wide as `cap - 1`'s bit length — the smear — and `n + 1` is the power of two above it. The `cap - 1` is what makes an exact power of two map to itself rather than doubling.

`cap == 0` gives `numberOfLeadingZeros(-1) == 0`, so `n == -1`, so the `n < 0` guard returns 1. Before JDK 8 this was a five-line shift-and-or sequence; the intrinsic replaced it.

```java
// MyHashMap.java
    static int tableSizeFor(int cap) {
        int n = -1 >>> Integer.numberOfLeadingZeros(cap - 1);
        return (n < 0) ? 1 : (n >= MAXIMUM_CAPACITY) ? MAXIMUM_CAPACITY : n + 1;
    }
```

Real output, `Demo` section 1:

```
tableSizeFor(0)              = 1
tableSizeFor(1)              = 1
tableSizeFor(2)              = 2
tableSizeFor(5)              = 8
tableSizeFor(16)             = 16
tableSizeFor(17)             = 32
tableSizeFor(1000)           = 1024
```

**Pitfall:** `tableSizeFor` does **not** account for the load factor. `new HashMap<>(1000)` gives capacity 1024 and threshold 768, so it resizes at the 769th entry despite the reader having "asked for 1000". The fix, since JDK 19, is `HashMap.newHashMap(int numMappings)` (line 2580), which routes through `calculateHashMapCapacity` (line 2563) — `(int) Math.ceil(numMappings / 0.75d)`. **Version trap:** every pre-JDK-19 write-up tells you to write `new HashMap<>((int)(n / 0.75f) + 1)` by hand; on 19+ that is `HashMap.newHashMap(n)`.

> **Definition.** `tableSizeFor(cap)` returns the smallest power of two ≥ `cap`, clamped to `[1, 2^30]`, computed by smearing `cap - 1`'s leading bit rightwards with one `numberOfLeadingZeros` intrinsic.

This file has no diagram — the `put` trace D-146 belongs with the `put` walk and is embedded in [06a](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md).

---

## Pitfalls

### Believing `spread` prevents collisions

**Wrong**

```java
System.out.println(MyHashMap.spread("Aa") == MyHashMap.spread("BB"));   // true
```

**Right**

```java
// spread only redistributes existing entropy; it cannot create any.
// Equal raw hash codes stay equal. Bound the damage elsewhere:
//   - a good hashCode() on your key type, or
//   - treeification (file 08), which caps a poisoned bin at O(log n) lookup.
System.out.println("Aa".hashCode() + " == " + "BB".hashCode());   // 2112 == 2112
```

**Why people believe it:** "hash spreading" sounds like a mixing function of the kind that decorrelates inputs. It is one XOR; it is a fold, not a mix.

### Reading `Node.hashCode()` as the bucket hash

**Wrong**

```java
// "the entry knows its bucket, so I can find it":
int bucket = (map.table.length - 1) & entry.hashCode();   // wrong number
```

**Right**

```java
// Map.Entry.hashCode() is keyHash ^ valueHash, per the Map.Entry contract.
// The bucket comes from the cached spread key hash:
int bucket = (map.table.length - 1) & MyHashMap.spread(entry.getKey());
```

**Why people believe it:** both are called "the hash", both are `int`, and for an entry whose value happens to be `null` they even coincide (`h ^ 0 == h`) — so the mistake survives half your tests.

### Assuming a power-of-two capacity request is honoured verbatim

**Wrong**

```java
MyHashMap<String, Integer> m = new MyHashMap<>(1000);
// "capacity 1000, so 1000 entries fit"
```

**Right**

```java
// tableSizeFor(1000) == 1024, threshold == 1024 * 0.75 == 768.
// It resizes at the 769th entry. On JDK 19+ use the intent-revealing factory:
java.util.Map<String, Integer> sized = java.util.HashMap.newHashMap(1000);
```

**Why people believe it:** the parameter is named `initialCapacity` and 1000 is a plausible array length. Nothing at the call site mentions the load factor.

---

## Cheat sheet

| Item | Value / rule | JDK 21 line |
|---|---|---|
| `DEFAULT_INITIAL_CAPACITY` | 16 | 238 |
| `MAXIMUM_CAPACITY` | 2^30 | 245 |
| `DEFAULT_LOAD_FACTOR` | 0.75f | 250 |
| `TREEIFY_THRESHOLD` | 8 | 260 |
| `UNTREEIFY_THRESHOLD` | 6 (not used in this build) | 267 |
| `MIN_TREEIFY_CAPACITY` | 64 | 275 |
| `Node` fields | `final int hash; final K key; V value; Node next;` | 281 |
| `Node.hashCode()` | `key.hashCode() ^ value.hashCode()` — not the cached `hash` | 281 |
| spread | `(k == null) ? 0 : (h = k.hashCode()) ^ (h >>> 16)` | 336 |
| null key | spread 0 → always bucket 0, no special case anywhere else | 336 |
| `tableSizeFor` | `-1 >>> numberOfLeadingZeros(cap - 1)`, then `+1` | 377 |
| Index | `(capacity - 1) & hash` | 631 |
| Pre-size correctly (19+) | `HashMap.newHashMap(n)`, not `new HashMap<>(n)` | 2580 |
| Field visibility | package-private in `java.util` → subclass must share the package | 390–428 |
| Must override from `AbstractMap` | `size`, `isEmpty`, `containsValue`, `keySet`, `values` | — |
| Free from `AbstractMap` | `equals`, `hashCode`, `toString`, `putAll` | — |

---

## Self-test

**Q1.** Why is `Node.hash` `final` but `Node.value` not?

<details><summary>Answer</summary>

`hash` is derived from `key`, and `key` is `final` because an entry's identity must not change while it sits in a bin — moving a key would put it in the wrong bucket with no way to find it again. `value` is the mutable payload: `put` on an existing key and `Map.Entry.setValue` both write it in place, with no structural change and no `modCount` bump. `next` is non-final for the same reason: chain position changes on insert, remove and resize.

</details>

**Q2.** `Node.hashCode()` returns `Objects.hashCode(key) ^ Objects.hashCode(value)`, not the cached `hash` field. Why two different numbers?

<details><summary>Answer</summary>

They serve different contracts. The cached `hash` field is the *spread key hash*, used only for bucket selection and for the cheap first-stage comparison in a chain walk. `Node.hashCode()` implements `Map.Entry.hashCode()`, whose specification is `keyHash ^ valueHash` — it must include the value, because two entries with the same key and different values are not equal entries. `AbstractMap.hashCode()` sums these to produce the map's hash code, and that sum has to interoperate with every other `Map` implementation.

</details>

**Q3.** Why does `tableSizeFor` compute `numberOfLeadingZeros(cap - 1)` rather than `numberOfLeadingZeros(cap)`?

<details><summary>Answer</summary>

So an exact power of two maps to itself. With `cap == 16`, `cap - 1 == 15` has bit length 4, the smear produces `0b1111 == 15`, and `+1` gives 16. Using `cap` directly, 16 has bit length 5, the smear gives 31, and `+1` gives 32 — the function would double every already-correct capacity.

</details>

**Q4.** Where does the null key go, and how many `if (key == null)` branches does the rest of the map need?

<details><summary>Answer</summary>

Bucket 0, and zero extra branches. `spread(null)` returns 0, so `(n - 1) & 0 == 0` for every capacity. Everywhere else, the comparison `p.key == key || (key != null && key.equals(p.key))` handles it: `null == null` succeeds on the reference test and never reaches `equals`. This is why `HashMap` supports a null key while `Hashtable` and `ConcurrentHashMap` do not — those needed `null` free as a sentinel for other purposes.

</details>

**Q5.** Which `AbstractMap` methods *must* you override in a serious `Map`, and which can you safely inherit?

<details><summary>Answer</summary>

Must override: `size()` and `isEmpty()`, because the inherited versions run `entrySet().size()`, a full iteration — inheriting them makes an O(1) query O(n). Should override for allocation reasons: `containsValue`, `keySet`, `values`. Safe to inherit: `equals`, `hashCode`, `toString`, `putAll` — all O(n) by nature, all rarely hot, and `equals`/`hashCode` are the ones you *want* inherited because they define cross-implementation `Map` equality.

</details>

**Q6.** You want a map holding exactly 1,000 entries that never resizes. What do you write on JDK 21, and what did people write before JDK 19?

<details><summary>Answer</summary>

On JDK 19+, `HashMap.newHashMap(1000)`: it computes `(int) Math.ceil(1000 / 0.75d) == 1334`, rounds to capacity 2048, and gives threshold 1536. Before that you wrote `new HashMap<>((int)(1000 / 0.75f) + 1)` by hand. Writing `new HashMap<>(1000)` gives capacity 1024 and threshold 768 — it resizes at the 769th entry.

</details>

**Q7.** Why does the JDK cap capacity at `1 << 30` rather than `Integer.MAX_VALUE`?

<details><summary>Answer</summary>

Capacity must be a power of two so the index can be `(n - 1) & hash`. The next power of two after `1 << 30` is `1 << 31`, which as a signed `int` is `Integer.MIN_VALUE` — negative, and unusable as an array length. `1 << 30` is therefore the largest legal power-of-two capacity, roughly 1.07 billion slots. Past that the table stops growing, `threshold` is pinned to `Integer.MAX_VALUE`, and bins simply get longer.

</details>

---

**Leaves covered:** 4.3.1, 4.3.2 (2 leaves)
**Leaves deferred:** none — 4.3.3 and the extension surface are in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md), 4.3.4–4.3.6 in [07-build-my-hash-map-b-put-get-resize.md](07-build-my-hash-map-b-put-get-resize.md), 4.3.7–4.3.8 in [08-build-my-hash-map-c-treeify-and-defaults.md](08-build-my-hash-map-c-treeify-and-defaults.md), 4.3.9–4.3.10 in [09-build-my-hash-map-d-views-and-iterator.md](09-build-my-hash-map-d-views-and-iterator.md), 4.3.11–4.3.12 in [10-build-my-hash-map-e-set-linked-and-diff.md](10-build-my-hash-map-e-set-linked-and-diff.md), 4.3.13–4.3.14 in [10b-build-my-hash-map-g-diff-and-collision-dos.md](10b-build-my-hash-map-g-diff-and-collision-dos.md)
**Diagrams included:** none new — the `put` trace (D-146, frames a–d) is embedded in [06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md](06a-build-my-hash-map-a2-lazy-allocation-and-hooks.md)
**Target version:** Java 21 LTS
**Lines:** 431
