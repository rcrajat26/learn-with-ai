# 02 Java Collections — Specialised maps and sets — INTERMEDIATE (§2.9.7–2.9.9)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [specialised-maps/02b-internals-enum-set.md](02b-internals-enum-set.md) · Next: [specialised-maps/03b-weak-hash-map.md](03b-weak-hash-map.md)

`EnumMap` won its place by exploiting a closed key universe. The two maps that follow
win theirs by changing what "the same key" means — one swaps `equals` for `==`, the
other lets the garbage collector delete your entries behind your back. Both are correct
tools for a narrow job and disasters everywhere else.

**This file covers `IdentityHashMap` only.** `WeakHashMap`, the reference strength ladder
and the value-holds-key leak continue in
[03b-weak-hash-map.md](03b-weak-hash-map.md); `Hashtable` vs `HashMap` vs
`ConcurrentHashMap` and `Properties` are in
[03c-legacy-maps-and-properties.md](03c-legacy-maps-and-properties.md). The filename says
"identity-and-weak" because this file was split after it was written and renaming it would
orphan the path the index already records.

## The family map before the streets

| Map | Key identity test | Key reachability | Value reachability | Table shape | Since |
|---|---|---|---|---|---|
| `HashMap` | `equals`/`hashCode` | strong | strong | `Node[]`, chained, treeified | 1.2 |
| `IdentityHashMap` | `==` (`System.identityHashCode`) | strong | strong | flat `Object[]`, interleaved, linear probe | 1.4 |
| `WeakHashMap` | `equals`/`hashCode` | **weak** | strong | `Entry[]`, chained, `Entry extends WeakReference` | 1.2 |
| `EnumMap` | ordinal | strong | strong | `Object[]` indexed by ordinal | 1.5 |
| `Hashtable` | `equals`/`hashCode` | strong | strong | `Entry[]`, chained, all methods `synchronized` | 1.0 |

Two orthogonal knobs. `IdentityHashMap` turns the *identity* knob — this file.
`WeakHashMap` turns the *reachability* knob — [03b-weak-hash-map.md](03b-weak-hash-map.md).
Nothing in `java.util` turns both: if you need weak identity keys you build it yourself
out of `WeakReference` subclasses, or you use Caffeine's `weakKeys()`, which is
identity-based precisely because a weak key you can re-create by `equals` is a key you can
never reason about.

---

## `IdentityHashMap` — the map that admits it is not a `Map`

### Mental model first

Forget buckets and chains. Picture one flat `Object[]` where slot 0 is a key, slot 1
is its value, slot 2 is the next key, slot 3 its value, and so on. A lookup hashes
the key to an **even** index, compares with `==`, and on a miss steps forward two
slots at a time — wrapping to 0 at the end — until it either matches or hits a null
key slot, which means "not present". There is no `Entry` object anywhere. That is the
whole data structure.

### Why it exists

Graph algorithms need a "have I seen this node?" table where two structurally equal
but distinct nodes must count as two nodes. Serialization is the canonical case: if
you deep-copy an object graph and your visited-set uses `equals`, two equal-but-distinct
nodes collapse into one and you silently change the topology of the output. Before
`IdentityHashMap` (Java 1.4) you wrote a wrapper class whose `equals` delegated to `==`
and whose `hashCode` delegated to `System.identityHashCode`, and paid one allocation
per node for the privilege.

The javadoc does not hedge about the contract break (`IdentityHashMap.java:45-50`):

```java
 * <p><b>This class is <i>not</i> a general-purpose {@code Map}
 * implementation!  While this class implements the {@code Map} interface, it
 * intentionally violates {@code Map's} general contract, which mandates the
 * use of the {@code equals} method when comparing objects.  This class is
 * designed for use only in the rare cases wherein reference-equality
 * semantics are required.</b>
```

Every clause matters. "Implements the `Map` interface" — so it type-checks anywhere a
`Map` is accepted, which is exactly how it leaks into code that did not ask for it.
"Intentionally violates" — this is not a bug report, it is a design statement; nobody
will ever fix it. "Mandates the use of the `equals` method" — names the specific clause
of `Map`'s contract being broken. "Only in the rare cases" — the javadoc's own estimate
of how often you should reach for this.

The intended uses are named a few lines later (`IdentityHashMap.java:56-63`):
*topology-preserving object graph transformations* such as serialization and deep
copying, and maintaining *proxy objects* — a debugger keeping one shadow object per
live object.

### When to reach for it, and when not

| Situation | Use | Why |
|---|---|---|
| Cycle detection / visited-set in graph traversal | `IdentityHashMap` (or its key set) | distinct-but-equal nodes must stay distinct |
| Deep copy / serialization node table | `IdentityHashMap` | preserves topology, and never calls user `equals` (which may be expensive or recursive) |
| Keys are `enum` | `EnumMap` | ordinal indexing beats identity hashing, and enums are already identity-unique |
| Keys are value objects and you want value lookup | `HashMap` | you want `equals` |
| Keys are mutable and their `hashCode` changes | `IdentityHashMap` **works**, `HashMap` does not | identity hash never changes for an object's lifetime |
| Concurrent access | neither — wrap or use `ConcurrentHashMap` | `IdentityHashMap` is unsynchronized |

That fifth row is the underrated one. A `HashMap` key whose `hashCode` changes after
insertion is unfindable. An `IdentityHashMap` key can mutate freely: `System.identityHashCode`
is stable for the whole lifetime of the object, so the key can never get lost.

### How it works — sizing, arithmetic shown `[NUM]`

Three constants (`IdentityHashMap.java:160`, `:168`, `:179`):

```java
    private static final int DEFAULT_CAPACITY = 32;
    private static final int MINIMUM_CAPACITY = 4;
    private static final int MAXIMUM_CAPACITY = 1 << 29;
```

The table is declared as a bare object array — no `Entry` type exists
(`IdentityHashMap.java:184`):

```java
    transient Object[] table; // non-private to simplify nested class access
```

and `init` allocates **twice** the capacity, because each mapping occupies two slots
(`IdentityHashMap.java:266`):

```java
        table = new Object[2 * initCapacity];
```

So the default constructor gives `table.length == 2 * 32 == 64` slots holding at most
32 mappings' worth of storage.

The growth check lives inline in `put` (`IdentityHashMap.java:452-456`):

```java
            final int s = size + 1;
            // Use optimized form of 3 * s.
            // Next capacity is len, 2 * current capacity.
            if (s + (s << 1) > len && resize(len))
                continue retryAfterResize;
```

Line by line. `s = size + 1` is the size *after* the insertion that is pending — the
check is forward-looking, not on the current size. `s + (s << 1)` is `s + 2s = 3s`,
written as an add plus a shift because that was cheaper than a multiply when this was
written in 2003. `len` is `table.length`, which is `2 * capacity`, so `3s > 2*capacity`
is the load-factor-2/3 test written without a division. And `resize(len)` passes the
*current table length* as the *new capacity* — since length is twice capacity, passing
`len` doubles the capacity, which `resize` then doubles again into `newLength = newCapacity * 2`
(`IdentityHashMap.java:474`). `continue retryAfterResize` re-runs the whole probe against
the fresh table, because every index computed against the old length is now garbage.

**Insight:** the syllabus and most blog posts state the condition as `size * 3 > len`.
The real code is `(size + 1) * 3 > len`. It matters at the boundary: with `len == 64`,
`3 * (size + 1) > 64` first holds when `size + 1 >= 22`, i.e. `size >= 21`. So 21
mappings fit in the default table and the **22nd** `put` resizes. That is exactly what
the `DEFAULT_CAPACITY` javadoc claims (`IdentityHashMap.java:155-158`): "The value 32
corresponds to the (specified) expected maximum size of 21, given a load factor of 2/3."
Check: 21/32 = 0.656, and 22/32 = 0.6875 > 2/3.

Ceiling arithmetic: `MAXIMUM_CAPACITY = 1 << 29 = 536,870,912`, so the largest table is
`2 * (1 << 29) = 1 << 30 = 1,073,741,824` slots. At 4 bytes per reference under compressed
oops that is a 4 GiB array. The class caps usable mappings at `MAXIMUM_CAPACITY - 1 =
536,870,911`, and the reason is stated in the source (`IdentityHashMap.java:175-178`): the
table must retain "at least one slot with the key == null in order to avoid infinite
loops in get(), put(), remove()" — a full linear-probe table has no probe-terminating
sentinel, so the loop would spin forever. `resize` enforces it by throwing
(`IdentityHashMap.java:478-482`):

```java
        if (oldLength == 2 * MAXIMUM_CAPACITY) { // can't expand any further
            if (size == MAXIMUM_CAPACITY - 1)
                throw new IllegalStateException("Capacity exhausted.");
            return false;
        }
```

Sizing from an expected count uses `capacity` (`IdentityHashMap.java:248-254`), whose
final branch is `Integer.highestOneBit(expectedMaxSize + (expectedMaxSize << 1))` —
again `3 * expectedMaxSize`, then the largest power of two not exceeding it. For
`expectedMaxSize = 21` that is `highestOneBit(63) = 32`, matching the javadoc's
"smallest power of two greater than `(3 * expectedMaxSize) / 2`". Those two phrasings look
contradictory — one takes the largest power of two *below* `3e`, the other the smallest
*above* `1.5e` — but they are the same function: if `3e` lies in `[2^k, 2^(k+1))` then
`1.5e` lies in `[2^(k-1), 2^k)`, so both yield `2^k`. Do not "fix" one against the other.

Two one-liners you need to predict behaviour; the full walk is in
[04-internals-identity-weak.md](04-internals-identity-weak.md). `hash`
(`IdentityHashMap.java:305-309`) multiplies the identity hash by −254 via
`((h << 1) - (h << 8))` and masks with `length - 1` — the point of the even multiplier
is that the result is always **even**, so it always lands on a key slot. `nextKeyIndex`
(`:314-316`) is `(i + 2 < len ? i + 2 : 0)` — step two, wrap to zero. And null keys are
not special-cased in the table; they are swapped for a sentinel on the way in
(`:201`, `:206-207`), `static final Object NULL_KEY = new Object()` with
`maskNull`/`unmaskNull`, so `null` is a legal key and a legal value.

![D-52: the flat interleaved Object[] — key at even index i, value at i+1, and the probe stepping i += 2 with wraparound. Follow the resize box: the condition drawn is the real one, on size+1, with 3*s computed as s + (s << 1).](../diagrams/D-52-identityhashmap-flat-table.svg)

### A minimal concrete example

```java
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;

public class IdentityDemo {
    public static void main(String[] args) {
        String a = new StringBuilder("key").toString();
        String b = new StringBuilder("key").toString();
        System.out.println("a.equals(b) = " + a.equals(b));
        System.out.println("a == b      = " + (a == b));

        Map<String, Integer> hm = new HashMap<>();
        hm.put(a, 1);
        System.out.println("HashMap.get(b)         = " + hm.get(b));
        System.out.println("HashMap.size()         = " + hm.size());

        Map<String, Integer> ihm = new IdentityHashMap<>();
        ihm.put(a, 1);
        System.out.println("IdentityHashMap.get(b) = " + ihm.get(b));
        ihm.put(b, 2);
        System.out.println("IdentityHashMap.size() after put(b) = " + ihm.size());
        System.out.println("IdentityHashMap.get(a) = " + ihm.get(a));
        System.out.println("IdentityHashMap        = " + ihm);

        Integer boxedLow1 = 127, boxedLow2 = 127;
        Integer boxedHigh1 = 128, boxedHigh2 = 128;
        Map<Integer, String> cache = new IdentityHashMap<>();
        cache.put(boxedLow1, "low");
        cache.put(boxedHigh1, "high");
        System.out.println("get(127-again) = " + cache.get(boxedLow2)
                + "  (Integer cache: same instance)");
        System.out.println("get(128-again) = " + cache.get(boxedHigh2)
                + "  (outside Integer cache: distinct instance)");

        Map<Object, Object> nulls = new IdentityHashMap<>();
        nulls.put(null, "null key is allowed");
        System.out.println("null key -> " + nulls.get(null) + ", size=" + nulls.size());
    }
}
```

Real output, JDK 21.0.7+8-LTS-245:

```
a.equals(b) = true
a == b      = false
HashMap.get(b)         = 1
HashMap.size()         = 1
IdentityHashMap.get(b) = null
IdentityHashMap.size() after put(b) = 2
IdentityHashMap.get(a) = 1
IdentityHashMap        = {key=1, key=2}
get(127-again) = low  (Integer cache: same instance)
get(128-again) = null  (outside Integer cache: distinct instance)
null key -> null key is allowed, size=1
```

### The gotcha `[TRAP]`

**Pitfall:** *wrong belief* — "my key type has a good `equals`, so lookups will work."
*Symptom* — `get` returns `null` for a key that `equals` a key you inserted, `size()`
climbs past the number of logically distinct keys, and `toString()` prints what looks
like a duplicated key (`{key=1, key=2}` above). No exception, ever. *Fix* — treat
`IdentityHashMap` as an identity set/table only, never as a lookup map keyed by value;
if a `Map`-typed field is populated from a factory, assert the concrete type, because
the substitution type-checks silently.

The `Integer` rows are the nastiest form. `cache.get(boxedLow2)` finds the entry because
`Integer.valueOf` returns a cached instance for −128..127, so the two `127`s are the
same object. `128` is outside the cache, so the two `128`s are distinct objects and the
lookup misses. Your identity map's correctness now depends on the autoboxing cache size,
which is tunable via `-XX:AutoBoxCacheMax`. Never key an `IdentityHashMap` on a boxed
primitive or a `String`.

**Insight:** the contract violation reaches `equals` and `hashCode` on the map itself, not
just on lookups. `IdentityHashMap.equals` (`:660-679`) has three branches: against another
`IdentityHashMap` it compares mappings by reference; against any other `Map` it falls back
to `entrySet().equals(m.entrySet())`, and its own entry set compares by identity
(`:906`). So `ihm.equals(hashMap)` can be `false` while `hashMap.equals(ihm)` is `true` —
`equals` is not symmetric across the two types. And `hashCode` (`:703-715`) sums
`System.identityHashCode(k) ^ System.identityHashCode(v)`, so two `IdentityHashMap`s
holding equal-but-distinct keys have different hash codes. Never use an
`IdentityHashMap` as a key in another map, or compare one to a `HashMap`.

> **`IdentityHashMap`** is a linear-probing hash table over a single interleaved
> `Object[]` that compares keys with `==` and `System.identityHashCode`, deliberately
> violating `Map`'s `equals`-based contract in exchange for topology-preserving,
> mutation-proof, allocation-free identity lookup.

---

## Pitfalls

### Assuming `IdentityHashMap` will use your key's `equals`

**Wrong**

```java
Map<String, Integer> ihm = new IdentityHashMap<>();
String a = new StringBuilder("key").toString();
ihm.put(a, 1);
System.out.println(ihm.get("key"));   // prints: null
System.out.println(ihm.get(new StringBuilder("key").toString())); // prints: null
```

Two lookups for a key that `equals` the stored key, both `null`, no exception.

**Right**

```java
Map<String, Integer> hm = new HashMap<>();
hm.put(a, 1);
System.out.println(hm.get("key"));    // prints: 1
```

Reach for `IdentityHashMap` only when `==` *is* the semantics you want — a visited-set
in a graph walk, or a node table in a deep copy.

**Why people believe it:** it implements `Map<K,V>`, so it substitutes for a `HashMap`
with no compiler complaint and no runtime error — only wrong answers.

### Reading the constructor argument as an initial capacity

**Wrong**

```java
// "I want a table of 100 slots"
Map<Node, Info> seen = new IdentityHashMap<>(100);
```

The argument is `expectedMaxSize`, not capacity, and not table length.
`capacity(100)` returns `Integer.highestOneBit(300) == 256`, so the table is
`2 * 256 == 512` slots — five times what the caller pictured — and it holds 170 mappings
before resizing (`3 * 171 = 513 > 512`).

**Right**

```java
// Size from the number of mappings you expect, and let the class do the arithmetic.
Map<Node, Info> seen = new IdentityHashMap<>(expectedNodeCount);
```

**Why people believe it:** every other `java.util` hash container takes an initial
*capacity*. `IdentityHashMap` is the outlier, and its javadoc says so
(`:75-80`) — "This class has one tuning parameter … *expected maximum size*" — while
also warning that "the precise relationship between the expected maximum size and the
number of buckets is unspecified", so do not encode the 3x-then-round rule in your code.

### Comparing an `IdentityHashMap` to another `Map`

**Wrong**

```java
// The asymmetry needs the SAME key identity and an equal-but-distinct VALUE.
// Integer.valueOf(1000) is outside the Integer cache, so these are two objects.
String k = "key";
Map<String, Integer> ihm = new IdentityHashMap<>();
Map<String, Integer> hm  = new HashMap<>();
ihm.put(k, Integer.valueOf(1000));
hm.put(k, Integer.valueOf(1000));
System.out.println(ihm.equals(hm));   // false: the IHM entry set compares VALUES by identity
System.out.println(hm.equals(ihm));   // true:  AbstractMap.equals does get(k) then value.equals
```

Two distinct-but-*equal* **keys** do **not** show this. That gives `false` in both directions —
the identity map holds two mappings where the `HashMap` holds one, and once the sizes match the
reverse lookup `ihm.get(b)` fails on identity anyway. Verified on JDK 21.0.7:
`false`/`false` for the two-key form, `false`/`true` for the form above.

An asymmetric `equals`, which breaks every collection that stores maps.

**Right**

```java
// Compare the logical contents explicitly, on your own terms.
System.out.println(new HashMap<>(ihm).equals(hm));   // true, both sides equals-based
```

**Why people believe it:** the documented violation is usually described as being about
*keys*, so people assume the map-level `equals` is inherited unchanged from
`AbstractMap`. It is overridden (`:660-679`), and one of its three branches routes
through an identity-based `entrySet`.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Key test | `==`, hash from `System.identityHashCode` |
| Contract | intentionally violates `Map` (javadoc `:45-50`) |
| Since | 1.4 (Doug Lea, Josh Bloch) |
| Collision strategy | linear probing, no chaining, no treeify |
| `DEFAULT_CAPACITY` / table length | 32 / `2 * 32 = 64` slots |
| `MINIMUM_CAPACITY` / `MAXIMUM_CAPACITY` | 4 / `1 << 29`; max mappings `(1 << 29) - 1` |
| Largest table | `2 * (1 << 29) = 1 << 30` slots ≈ 4 GiB at 4 B/ref |
| Resize condition (`put`, `:452-456`) | `s = size + 1; s + (s << 1) > len` — i.e. `3*(size+1) > table.length` |
| Default resize point | on the 22nd `put` (21 mappings fit) |
| `resize` argument | `resize(len)` — the *length* is passed as the new *capacity* |
| Constructor argument | `expectedMaxSize`, **not** capacity |
| Layout | key at even `i`, value at `i+1`, one flat `Object[]` |
| `hash` | `((h << 1) - (h << 8)) & (len-1)` = `-254 * h`, always even |
| Probe step | `nextKeyIndex`: `i + 2`, wrapping to 0 |
| Nulls | `null` key and `null` value both legal, via `NULL_KEY` sentinel |
| `equals` | asymmetric vs other `Map`s (`:660-679`) |
| `hashCode` | sum of `identityHashCode(k) ^ identityHashCode(v)` (`:703-715`) |
| Thread safety | none; wrap with `Collections.synchronizedMap` |
| Iterators | fail-fast, `ConcurrentModificationException` |
| Iteration cost | proportional to **table length**, not `size` |
| Never key on | `String`, boxed primitives, any interned or cached type |

---

## Self-test

**Q1.** With a default `IdentityHashMap`, which `put` call triggers the first resize, and why is the common "`size * 3 > len`" formulation off by one?

<details><summary>Answer</summary>

The 22nd `put`. The real condition (`IdentityHashMap.java:452-456`) is
`final int s = size + 1; if (s + (s << 1) > len && resize(len))` — it tests the size
*after* the pending insert. With `DEFAULT_CAPACITY = 32`, `len = 2 * 32 = 64`, so it
first holds when `3 * (size + 1) > 64`, i.e. `size + 1 >= 22`, i.e. `size >= 21`. Twenty-one
mappings fit; the 22nd resizes. The loose form `size * 3 > len` would predict resizing when
`size >= 22`, one insertion late. The javadoc on `DEFAULT_CAPACITY` confirms the real
answer: capacity 32 "corresponds to the (specified) expected maximum size of 21, given a
load factor of 2/3".

</details>

**Q2.** Why is `IdentityHashMap`'s table `2 * capacity` long, and why must the map always keep at least one empty key slot?

<details><summary>Answer</summary>

Keys and values interleave in one flat `Object[]` — key at even index `i`, value at `i + 1`
— so each mapping needs two slots (`init`, `:266`: `table = new Object[2 * initCapacity]`).
The javadoc's `@implNote` says the interleaving is for locality on large tables versus two
separate arrays. The empty-slot requirement is a property of linear probing: the probe loop
terminates on a `null` key slot, so a completely full table would make `get`, `put` and
`remove` spin forever. Hence `MAXIMUM_CAPACITY - 1` usable mappings, enforced by the
`IllegalStateException("Capacity exhausted.")` in `resize` (`:478-482`).

</details>

**Q3.** `hash` computes `((h << 1) - (h << 8)) & (length - 1)`. What is that arithmetic, and what property of the result is load-bearing?

<details><summary>Answer</summary>

`h << 1` is `2h` and `h << 8` is `256h`, so the expression is `2h - 256h = -254h` — the
source comment says exactly that: "Multiply by -254 to use the hash LSB and to ensure
index is even." The load-bearing property is **evenness**. Because `-254` is even, the
product is even, and masking with `length - 1` (where `length` is a power of two) preserves
the low bit, so the index always lands on a *key* slot rather than a value slot. Multiplying
by an even constant also drags the low bit of `h` up into a position the mask keeps, which
is why the multiplier is not simply `2`.

</details>

**Q4.** `new IdentityHashMap<>(100)` — how long is the table, and how many mappings fit before the first resize?

<details><summary>Answer</summary>

`capacity(100)` (`:248-254`) takes the last branch:
`Integer.highestOneBit(100 + (100 << 1)) = highestOneBit(300) = 256`. So capacity is 256 and
`init` allocates `2 * 256 = 512` slots. The first resize fires when `3 * (size + 1) > 512`,
i.e. `size + 1 >= 171`, i.e. `size >= 170` — so 170 mappings fit and the 171st grows the
table. Note the argument is `expectedMaxSize`, not an initial capacity: asking for 100 gets
you a 512-slot array. The javadoc explicitly declines to specify this relationship
(`:79-80`), so do not hard-code the 3x rule.

</details>

**Q5.** You have a key class whose `hashCode` depends on mutable fields. Explain why an `IdentityHashMap` tolerates this and a `HashMap` does not.

<details><summary>Answer</summary>

`HashMap` files the entry in a bucket chosen from `hashCode()` at insertion time. Mutating a
field that `hashCode` reads changes which bucket the key would now hash to, so every
subsequent `get`, `containsKey` and `remove` probes the wrong bucket and the entry becomes
unreachable — a silent leak, findable only by full iteration. `IdentityHashMap` never calls
`hashCode()`; it uses `System.identityHashCode`, which is derived from the object's identity
(stored in the mark word or computed once and cached) and is fixed for the object's entire
lifetime. So mutation cannot move the key. This is a genuine, non-obvious reason to reach
for `IdentityHashMap` outside graph traversal.

</details>

**Q6.** Is `IdentityHashMap.equals` symmetric with `HashMap.equals`? Show the consequence.

<details><summary>Answer</summary>

No. `IdentityHashMap.equals` (`:660-679`) branches three ways: `o == this`; `o instanceof
IdentityHashMap`, compared mapping-by-mapping with reference equality; and `o instanceof
Map`, delegated to `entrySet().equals(m.entrySet())` — where the `IdentityHashMap`'s own
entry set compares **keys and values** by identity (`:906`). The asymmetry needs the same key
identity and an equal-but-distinct value: with `k` shared, `ihm.put(k, Integer.valueOf(1000))`
and `hm.put(k, Integer.valueOf(1000))` give `ihm.equals(hm) == false` but
`hm.equals(ihm) == true`, because `AbstractMap.equals` does `get(k)` — an identity *key* lookup
that succeeds — then compares the value with `.equals`. Two distinct-but-equal *keys* give
`false` in **both** directions, not an asymmetry. Consequence: never
store an `IdentityHashMap` in a `Set`, use one as a key in another map, or compare one to a
`HashMap` — `hashCode` is identity-based too (`:703-715`), so the hash contract is broken on
both halves.

</details>

**Q7.** Iterating an `IdentityHashMap` is described as costing time proportional to the number of buckets, not the number of entries. Why, and when does that bite?

<details><summary>Answer</summary>

There are no chains to follow and no entry objects to link — iteration is a scan over the
flat `Object[]`, stepping `i += 2` and skipping null key slots. So the cost is
`table.length / 2` regardless of how many mappings are present. The javadoc warns about it
directly (`:86-89`): "iteration over collection views requires time proportional to the
number of buckets in the hash table, so it pays not to set the expected maximum size too
high if you are especially concerned with iteration performance or memory usage." It bites
when you size generously and then iterate in a hot loop — e.g. a serialization node table
constructed with a large `expectedMaxSize` but usually holding a handful of nodes. Note the
same is true of `HashMap`, but `IdentityHashMap`'s table is twice as long for the same
capacity, so the constant is doubled.

</details>

---

**Leaves covered:** 2.9.7–2.9.9 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-52
**Target version:** Java 21 LTS
**Lines:** 522
