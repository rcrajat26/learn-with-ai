# 02 Java Collections — Specialised maps and sets — INTERMEDIATE (§2.9.1–2.9.6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [sets/03-bitset.md](../sets/03-bitset.md) · Next: [specialised-maps/02-internals-enum-map-set.md](02-internals-enum-map-set.md)

All output pasted below is real, from `openjdk 21.0.7`. Source citations are against the JDK 21 `java.base` sources.

## The family before the details

Enum keys have a property no other key type has: the JVM already assigned each constant a dense integer, `ordinal()`, in `[0, n)`, with `n` fixed at class-init time. That single fact makes hashing pointless, and both classes in this family exploit it — in two different ways.

| Class | Backing store | Lookup | Order | Null keys | Null values | Chosen when |
|---|---|---|---|---|---|---|
| `EnumMap<K,V>` | `Object[] vals` indexed by `ordinal()` | array index, no hash, no equals | ordinal (declaration) order | no — `NullPointerException` | yes, via a `NULL` sentinel | enum → value mapping |
| `RegularEnumSet<E>` | one `long elements` | one bit test | ordinal order | no | n/a | enum set, `n <= 64` |
| `JumboEnumSet<E>` | `long[] elements` | word index + bit test | ordinal order | no | n/a | enum set, `n > 64` |
| `HashMap` / `HashSet` (for contrast) | `Node[]` + hash | hash, `equals` | unspecified | one null key | yes | non-enum keys |

`EnumSet` itself is abstract and, since Java 17, **sealed**:

```java
// EnumSet.java:81-83
public abstract sealed class EnumSet<E extends Enum<E>> extends AbstractSet<E>
    implements Cloneable, java.io.Serializable permits JumboEnumSet, RegularEnumSet
```

You can never subclass it and you never name the two implementations — you get one back from a factory.

---

## EnumMap: the map that is really an array

### Mental model

Picture a coat rack bolted to the wall with one numbered hook per enum constant, installed the moment the map is constructed. `put(WED, 3)` walks to hook 2 and hangs the value there. There is no search, no bucket, no chain, no `hashCode()` call, no `equals()` call. `get` is a single array load. The "map" is a naming convention over an array whose indices happen to have names.

### Why it exists

Before Java 5 you kept enum-like constants as `int` finals and mapped them with a plain array — fast, but the index was untyped, so nothing stopped you indexing with the wrong constant family. `HashMap<MyEnum, V>` restored type safety but paid for a hash table it did not need: a `Node` per mapping, a table, and a pointer chase on every lookup. `EnumMap` gives the array's speed with the `Map` interface's type safety.

### When to reach for it, and when not

Reach for it whenever the key type is an enum and you want a `Map`. Do not reach for it when: you need a **null key** (`EnumMap.put(null, v)` throws `NullPointerException` from `typeCheck`; `HashMap` accepts one); you need **insertion-order** iteration (use `LinkedHashMap`); keys come from **several enum types** in one map (an `EnumMap` is pinned to one `keyType` — use `HashMap`); the enum is **huge and the map near-empty** (see the density trap below, where `HashMap` genuinely wins on footprint); or you need **thread safety** (there is no `ConcurrentEnumMap` — wrap with `Collections.synchronizedMap`, or use `ConcurrentHashMap` and give up ordinal ordering).

### How it works

Three fields carry the whole design:

```java
// EnumMap.java:89
private final Class<K> keyType;
// EnumMap.java:94
private transient K[] keyUniverse;
// EnumMap.java:101
private transient Object[] vals;
```

- `keyType` is the runtime class used by `typeCheck` to reject a foreign enum.
- `keyUniverse` is the `values()` array. It is **not copied** — `getKeyUniverse` (EnumMap.java:748-751) goes through `SharedSecrets.getJavaLangAccess().getEnumConstantsShared(keyType)`, which returns the single cached, uncloned array the JVM already holds for the enum class. Every `EnumMap` of the same key type shares that one array, so it costs nothing per map. `vals` is the only per-map allocation.
- `vals` is allocated once in the constructor: `vals = new Object[keyUniverse.length]` (EnumMap.java:139). Its length never changes. There is no resize, no load factor, no rehash.

`put` is the whole story:

```java
// EnumMap.java:266-275
public V put(K key, V value) {
    typeCheck(key);

    int index = key.ordinal();
    Object oldValue = vals[index];
    vals[index] = maskNull(value);
    if (oldValue == null)
        size++;
    return unmaskNull(oldValue);
}
```

Line by line: `typeCheck(key)` throws `ClassCastException` if the key's class is not `keyType` (and `NullPointerException` for `null`, because it dereferences `key.getClass()`). `key.ordinal()` **is** the index — no hash mixing, no `& (n-1)` bucket masking, no probing. `oldValue` is read to decide whether `size` grows, which is why `size` is a maintained counter rather than something derived. `maskNull(value)` (EnumMap.java:121-123) substitutes the private `NULL` sentinel object for a null value, so that a `null` slot means "absent" and a `NULL` slot means "present, mapped to null" — that distinction is what lets `containsKey` be a single non-null test:

```java
// EnumMap.java:221-223
public boolean containsKey(Object key) {
    return isValidKey(key) && vals[((Enum<?>)key).ordinal()] != null;
}
```

**Insight:** everything expensive about a hash map — hashing, collision resolution, resizing, `equals` comparison — is absent because `ordinal()` is already a *perfect, minimal, dense* hash of the key space. The full walk of `keyUniverse`, `SharedSecrets` and the entry-set views is in [02-internals-enum-map-set.md](02-internals-enum-map-set.md).

### Footprint arithmetic `[NUM]`

Assuming the standard 64-bit HotSpot layout with compressed oops (12-byte object header, 4-byte references, 16-byte array header, 8-byte alignment). For an enum with `n` constants and `k` mappings present:

- `EnumMap` instance: 12 header + 4 (`keyType`) + 4 (`keyUniverse`) + 4 (`vals`) + 4 (`size`) = 28 → padded to **32 bytes**.
- `vals` array: 16 + 4n, padded to a multiple of 8.
- `keyUniverse`: **0 bytes charged** — shared with the enum class, as shown above.

So a 7-constant enum, fully populated: 32 + (16 + 28 → 48) = **80 bytes**, independent of `k`.

The same 7 mappings in a `HashMap`: ~48 bytes for the `HashMap` instance, `Node[16]` = 16 + 64 = 80 bytes, plus 7 `Node`s at 32 bytes each (12 header + hash 4 + key 4 + value 4 + next 4 = 28 → 32) = 224 bytes. Total ≈ **352 bytes**, four-plus times the `EnumMap`.

The syllabus phrases the cost as "~2 words per slot". **Correction:** per slot the map itself pays exactly one compressed reference, 4 bytes — half a word. The "2 words" figure only holds if you charge the shared `keyUniverse` reference too (4 + 4 = 8 bytes = 1 word) and round up; since `keyUniverse` is shared and uncloned (EnumMap.java:748-751), the honest per-slot figure for the map is **4 bytes**, and the per-constant figure amortised across every `EnumMap` of that type is also 4 bytes. Treat "~2 words per slot" as folklore.

### The density trap `[TRAP]`

`vals` has one slot per constant, allocated eagerly, whether you use it or not.

```
size() = 1, vals.length = 65
non-null slots = 1, null slots = 64
```

That is real output. One mapping, 65 slots. **Pitfall:** the belief that `EnumMap` is always the cheaper choice. Symptom: an enum with a few hundred constants (a generated error-code or country enum), one `EnumMap` per request or per row, each holding two or three mappings — allocation and GC pressure scale with the *enum size*, not the data. A 400-constant enum costs 32 + 16 + 1600 = 1648 bytes per map regardless of content; a `HashMap` with 3 entries costs about 200. Fix: for `k << n`, use `HashMap`; `EnumMap` wins when the map is dense or when `n` is small enough that 4n bytes is noise.

### Minimal example

```java
enum Day { MON, TUE, WED, THU, FRI, SAT, SUN }

EnumMap<Day, Integer> m = new EnumMap<>(Day.class);
m.put(Day.SUN, 7);
m.put(Day.MON, 1);
m.put(Day.WED, 3);
System.out.println(m);                       // {MON=1, WED=3, SUN=7} - ordinal order
System.out.println(m.containsKey(Day.TUE));  // false
m.put(Day.TUE, null);
// true / null - the NULL sentinel distinguishes "absent" from "mapped to null"
System.out.println(m.containsKey(Day.TUE) + " / " + m.get(Day.TUE));
try {
    m.put(null, 0);
} catch (NullPointerException e) {
    System.out.println("null key rejected: " + e.getClass().getSimpleName());
}
```

The puts went in SUN, MON, WED and came out MON, WED, SUN — that is real output, and it is `vals` being scanned in index order by the entry-set iterator, not any recorded insertion sequence.

> **Definition:** `EnumMap<K,V>` is a `Map` implementation backed by a single `Object[]` indexed directly by `K.ordinal()`, giving unconditional O(1) unhashed access and ordinal iteration order, at the cost of allocating one array slot per enum constant regardless of how many mappings exist.

---

## EnumSet: the set that is really a bit vector

### Mental model

A row of `n` light switches, one per enum constant, packed into the bits of a single `long`. Membership is "is switch `k` on". Union, intersection and difference are what they are in a digital circuit: OR, AND, AND-NOT — one instruction each, for the whole set at once, regardless of how many elements it holds.

### Why it exists

The pre-Java-5 idiom was hand-rolled bit flags: `static final int READ = 1, WRITE = 2, EXEC = 4;` then `int perms = READ | WRITE;`. Fast and compact, but untyped (nothing stops `perms | FLAG_FROM_ANOTHER_FAMILY`), unprintable (`println(perms)` gives `3`), and silently capped at 32 or 64 flags. `EnumSet` keeps the bit arithmetic and puts a `Set<E>` and a real `toString()` on top — Bloch's *Effective Java* rule "use `EnumSet` instead of bit fields" is exactly this trade.

### When to reach for it, and when not

Reach for it for any set of enum constants: flags, permitted state transitions, feature toggles, day-of-week masks. Do not reach for it when: you need **insertion order** (ordinal order only, and there is no linked variant); you need an **immutable** set (`EnumSet` has no immutable form — see 2.9.6 below; `Set.of(...)` gives immutability but loses the bitwise bulk ops); you need **thread safety** or atomic flag flipping (use an `AtomicLong` of your own bits, or `Collections.synchronizedSet`); or the elements are **not** enum constants (dense ints are `BitSet`'s territory — see [sets/03-bitset.md](../sets/03-bitset.md) — anything else is `HashSet`'s).

### How it works

`noneOf` is the single choke point every factory funnels through, and it is where the implementation is chosen:

```java
// EnumSet.java:112-121
public static <E extends Enum<E>> EnumSet<E> noneOf(Class<E> elementType) {
    Enum<?>[] universe = getUniverse(elementType);
    if (universe == null)
        throw new ClassCastException(elementType + " not an enum");

    if (universe.length <= 64)
        return new RegularEnumSet<>(elementType, universe);
    else
        return new JumboEnumSet<>(elementType, universe);
}
```

`getUniverse` is the same `SharedSecrets` shared-array trick as `EnumMap`. The branch is `<= 64`, inclusive — 64 constants still fit one `long`. Verified `[RESEARCH]` `[NUM]`:

```
E64 constants = 64 -> java.util.RegularEnumSet
E65 constants = 65 -> java.util.JumboEnumSet
Day constants = 7 -> java.util.RegularEnumSet
```

`RegularEnumSet`'s entire state is one primitive:

```java
// RegularEnumSet.java:43
private long elements = 0L;
```

Footprint `[NUM]`: 12-byte header + 4 (`elementType`) + 4 (`universe`) + 8 (`elements`) = 28 → padded to **32 bytes**, for any number of elements from 0 to 64. A `HashSet` holding the same 64 constants would cost a `HashMap` with a 128-slot table plus 64 `Node`s: roughly 48 + (16 + 512) + 64×32 = **2624 bytes**. That is the 80× figure people quote, and it checks out arithmetically.

`JumboEnumSet` generalises to a word array:

```java
// JumboEnumSet.java:45
private long elements[];
// JumboEnumSet.java:48
private int size = 0;
// JumboEnumSet.java:50-53
JumboEnumSet(Class<E>elementType, Enum<?>[] universe) {
    super(elementType, universe);
    elements = new long[(universe.length + 63) >>> 6];
}
```

`(n + 63) >>> 6` is `ceil(n / 64)` — the standard round-up-then-divide, with `>>> 6` as the divide by 64. Note the extra `size` field: `RegularEnumSet.size()` is `Long.bitCount(elements)` (RegularEnumSet.java:123), a single `POPCNT`, so no counter is needed; `JumboEnumSet` would have to popcount every word, so it caches `size` and maintains it — the comment at line 47 says exactly that: `// Redundant - maintained for performance`.

The core operations on `RegularEnumSet` are all single expressions: `contains` is `(elements & (1L << ordinal)) != 0` (line 148), `add` is `elements |= (1L << ordinal)` (line 165), `remove` is `elements &= ~(1L << ordinal)` (line 183), `clear` is `elements = 0` (line 280). No loops, no allocation, no bounds arithmetic — `ordinal()` is guaranteed `< 64` because `noneOf` already chose this class on that basis.

![D-51: EnumSet as a bit vector, over a 7-day enum declared SUN..SAT so bit 0 is SUN. Read the three panels in order: (1) add sets exactly one bit, elements |= 1L << ordinal, leaving 57 high bits at zero; (2) addAll ORs two whole vectors in one operation, elements |= other.elements, subject to the instanceof guard printed under it; (3) complement inverts all 64 bits and then ANDs away everything above universe.length, which is why the mask expression exists at all](../diagrams/D-51-enumset-bit-vector.svg)

### The complement mask `[NUM]`

```java
// RegularEnumSet.java:58-63
void complement() {
    if (universe.length != 0) {
        elements = ~elements;
        elements &= -1L >>> -universe.length;  // Mask unused bits
    }
}
```

`~elements` flips all 64 bits, including the `64 - n` bits above the universe that must stay zero — hence the mask. **There is no named `mask` field**; the mask is the expression `-1L >>> -universe.length`. The syllabus's "`~elements & mask`" is conceptually right but do not look for a field.

Why `>>> -n` works: for a `long` shift, JLS §15.19 says the shift distance is the right operand **masked with `0x3f`**, i.e. taken mod 64. So `-n & 0x3f == 64 - n` for `1 <= n <= 64`, and `-1L >>> -n` is exactly `-1L >>> (64 - n)` — `n` low one-bits. The `if (universe.length != 0)` guard exists because at `n == 0`, `64 - 0 = 0 mod 64`, so the mask would be all-ones instead of all-zeros: the one case where the trick breaks. Verified:

```
n= 1  -1L>>>-n = 1                    equal to -1L>>>(64-n)? true  bitCount=1
n= 7  -1L>>>-n = 1111111              equal to -1L>>>(64-n)? true  bitCount=7
n=64  -1L>>>-n = 1111111111111111111111111111111111111111111111111111111111111111  equal to -1L>>>(64-n)? true  bitCount=64
```

`EnumSet.complementOf` (EnumSet.java:197-201) is `EnumSet<E> result = copyOf(s); result.complement(); return result;`, and `copyOf` delegates to `clone()` (EnumSet.java:154-156), so `s` is untouched — `complementOf` is non-destructive.

### Minimal example

```java
enum Day { MON, TUE, WED, THU, FRI, SAT, SUN }

EnumSet<Day> weekend = EnumSet.of(Day.SAT, Day.SUN);
EnumSet<Day> weekdays = EnumSet.complementOf(weekend);
System.out.println(weekend + " / " + weekdays);
System.out.println(weekend.size() + weekdays.size());

EnumSet<Day> s = EnumSet.noneOf(Day.class);
s.add(Day.FRI);
s.add(Day.MON);
s.add(Day.WED);
System.out.println(s);
System.out.println(EnumSet.range(Day.TUE, Day.FRI));
```

Output: `[SAT, SUN] / [MON, TUE, WED, THU, FRI]`, then `7` — the complement plus the original exactly cover the 7-constant universe, so no phantom bits above `universe.length` leaked in — then `[MON, WED, FRI]` (added FRI first, came back in ordinal order) and `[TUE, WED, THU, FRI]`.

### The gotcha

`contains` and `remove` do **not** throw on a foreign type — they return `false`:

```java
// RegularEnumSet.java:142-146, inside contains(Object e)
if (e == null)
    return false;
Class<?> eClass = e.getClass();
if (eClass != elementType && eClass.getSuperclass() != elementType)
    return false;
```

Line 1-2: a null argument is not an error, just absent. Line 3-5: the type check. The `getSuperclass()` half is there for constant-specific class bodies — `FRI { ... }` compiles to an anonymous subclass, so `e.getClass()` is `Day$1`, not `Day`, and without that clause every such constant would report absent. The silent `false` is standard `Collection` contract behaviour, but it means a typo mixing two enum types is a permanently-empty query rather than an exception.

> **Definition:** `EnumSet<E>` is an abstract, sealed `Set` whose two implementations represent membership as bits of a single `long` (`RegularEnumSet`, `n <= 64`) or of a `long[]` (`JumboEnumSet`, `n > 64`), making membership a bit test, `size` a popcount, and set algebra a word-wise bitwise operation.

---

## Bulk operations are one bitwise op — when the guard passes `[SOURCE]` `[PROVE]`

### Mental model

Two sets, two `long`s. Their union is `a | b`. There is nothing to iterate. But the method signature is `addAll(Collection<? extends E>)`, and a `Collection` in general is not a bit vector — so every bulk method opens with a guard that decides whether the fast path is even reachable.

### The three method bodies, in full

```java
// RegularEnumSet.java:216-231
public boolean addAll(Collection<? extends E> c) {
    if (!(c instanceof RegularEnumSet<?> es))
        return super.addAll(c);

    if (es.elementType != elementType) {
        if (es.isEmpty())
            return false;
        else
            throw new ClassCastException(
                es.elementType + " != " + elementType);
    }

    long oldElements = elements;
    elements |= es.elements;
    return elements != oldElements;
}
```

```java
// RegularEnumSet.java:241-251
public boolean removeAll(Collection<?> c) {
    if (!(c instanceof RegularEnumSet<?> es))
        return super.removeAll(c);

    if (es.elementType != elementType)
        return false;

    long oldElements = elements;
    elements &= ~es.elements;
    return elements != oldElements;
}
```

```java
// RegularEnumSet.java:261-274
public boolean retainAll(Collection<?> c) {
    if (!(c instanceof RegularEnumSet<?> es))
        return super.retainAll(c);

    if (es.elementType != elementType) {
        boolean changed = (elements != 0);
        elements = 0;
        return changed;
    }

    long oldElements = elements;
    elements &= es.elements;
    return elements != oldElements;
}
```

### Working the argument through

**Guard 1 — same implementation class.** `c instanceof RegularEnumSet<?> es` is the Java 16+ pattern form of `instanceof` + cast + bind. It fails for a `List`, a `HashSet`, an `EnumSet` over a >64-constant enum (that is a `JumboEnumSet`), *and* for a `Collections.unmodifiableSet(enumSet)` wrapper — so wrapping your operand silently demotes you to `super.addAll(c)`, the `AbstractCollection` loop calling `add` once per element. Same answer, O(k) instead of O(1). This is the most common way people lose the fast path without noticing.

**Guard 2 — same `elementType`.** Two `RegularEnumSet`s of *different* enums both hold a `long`, and `a | b` over them would be meaningless: bit 0 means `Day.MON` in one and `Other.X` in the other. So each method needs a fallback, and — this is the part interviewers probe — **the three fallbacks are deliberately different**, derived from what the set-theoretic answer is when the two universes are disjoint:

| Method | Type mismatch behaviour | Why that is the correct answer |
|---|---|---|
| `addAll` | `ClassCastException`, unless `c` is empty → `false` | you cannot store foreign constants; but adding nothing is a legal no-op |
| `removeAll` | `return false`, set untouched | disjoint universes share no elements, so nothing to remove |
| `retainAll` | `elements = 0`, returns whether it changed | intersection with a disjoint universe is empty, so keep nothing |
| `containsAll` | `return es.isEmpty()` (line 203) | only the empty set is a subset of a disjoint set |

Run output confirming all four branches:

```
removeAll(other-type) changed=false set=[MON, TUE]
retainAll(other-type) changed=true set=[]   <-- silently emptied
addAll(other-type) threw ClassCastException: class EnumProof$Other != class EnumProof$Day
addAll(EMPTY other-type) changed=false set=[MON, TUE]   <-- no exception, empty escapes the check
```

Reaching those branches requires raw types (`((Set) daySet).retainAll(otherSet)`) — generics stop it at compile time in straight code. It happens for real when the sets flow through `Set<?>`, reflection, or a legacy non-generic API.

**Guard 3 — nothing else.** Once both guards pass, the body is `elements |= es.elements`, one expression, no loop, no allocation.

### The "single instruction" claim, proved structurally

This is a claim about the code shape, not a timing. `javap -c -p java.util.RegularEnumSet`, the tail of `addAll` (offset 78 onward is the post-guard body):

```
      78: aload_0
      79: getfield      #7                  // Field elements:J
      82: lstore_3
      83: aload_0
      84: dup
      85: getfield      #7                  // Field elements:J
      88: aload_2
      89: getfield      #7                  // Field elements:J
      92: lor
      93: putfield      #7                  // Field elements:J
```

Offsets 78-82 load `this.elements` and stash it in local 3 — that is `oldElements`, kept only so the method can return a `boolean`. Offsets 83-89 push `this`, duplicate it, and load both `this.elements` and `es.elements` onto the stack. Offset 92 is the union: **one `lor`**. Offset 93 stores it back. The remaining bytecodes of the method (96-110, elided as they are just `lcmp` against local 3 and the two `boolean` constants) compute the return value. The set union itself is exactly one bytecode, and one machine instruction after JIT — independent of how many elements either set holds. Contrast `HashSet.addAll`: a loop, `k` hash computations, `k` `equals` calls worst case, possibly a resize.

**Tradeoff:** O(1) set algebra, **but** only for `n <= 64` (a `JumboEnumSet` is O(n/64) word ops — still excellent, no longer constant), **and** only when both operands are the *same* implementation class of the *same* enum. Wrap either side in `unmodifiableSet`, or hand in a `List`, and you are back to the O(k) `AbstractCollection` loop. Verified that the slow path still gives the right answer:

```
fast = [MON, TUE, WED]  slow = [MON, TUE, WED]  same result? true
```

> **Definition:** `RegularEnumSet`'s bulk operations reduce to a single `long` `|`, `&~` or `&` — but only after an `instanceof RegularEnumSet` guard and an `elementType` identity check both pass; on either failure they fall back to per-element `AbstractCollection` loops or to method-specific disjoint-universe semantics.

---

## Factories: `noneOf`, `allOf`, `of`, `range`, `copyOf`, `complementOf` (§2.9.5)

Supporting facts. Every one of these funnels through `noneOf` for the allocation, then mutates.

| Factory | Source | Mechanism |
|---|---|---|
| `noneOf(Class)` | EnumSet.java:112 | allocates; picks Regular vs Jumbo on `length <= 64` |
| `allOf(Class)` | EnumSet.java:133-137 | `noneOf` then `addAll()` (no-arg, package-private) → `elements = -1L >>> -universe.length` (RegularEnumSet.java:55) |
| `of(e)` … `of(e1..e5)` | EnumSet.java:217, 238, 261, 286, 313 | five fixed-arity overloads, each `noneOf` + N `add` calls, **no array allocated** |
| `of(E first, E... rest)` | EnumSet.java:339-346 | `@SafeVarargs`; six-plus arguments allocate an `E[]` for `rest` — the javadoc at line 329 says it "is likely to run slower" |
| `range(from, to)` | EnumSet.java:362-368 | throws `IllegalArgumentException` if `from.compareTo(to) > 0`, else `addRange` → `elements = (-1L >>> (from.ordinal() - to.ordinal() - 1)) << from.ordinal()` (RegularEnumSet.java:50) |
| `copyOf(EnumSet)` | EnumSet.java:154-156 | `s.clone()` — shallow, and for `RegularEnumSet` that is enough since state is one primitive |
| `copyOf(Collection)` | EnumSet.java:172-185 | if it is an `EnumSet`, clone; else **throws `IllegalArgumentException` on an empty collection**, because with no element there is no way to learn the enum type |
| `complementOf(EnumSet)` | EnumSet.java:197-201 | `copyOf` then `complement()`; source set untouched |

The arity-1-to-5 overloads exist purely to avoid the varargs array on the common cases: `of(MON,TUE,WED,THU,FRI)` binds the 5-arity method, and adding a sixth argument silently switches you to the varargs form and allocates a `Day[5]`. Verified output for both is identical (`[MON, TUE, WED, THU, FRI]` / `[MON, TUE, WED, THU, FRI, SAT]`) — one allocation apart, no behavioural difference.

**Gotcha on `range`:** `EnumSet.range(Day.FRI, Day.TUE)` throws `IllegalArgumentException: FRI > TUE` rather than returning empty (verified). And `range` is defined by *ordinal*, so reordering the constants in the enum declaration silently changes what every `range` call in your codebase means — a real refactoring hazard.

**Interview:** "How would you model the legal state transitions of a workflow?" — `EnumMap<State, EnumSet<State>>`: the `EnumMap` is the transition table, each `EnumSet` is the allowed-target bitmask, and `allowed.get(from).contains(to)` is two array loads and a bit test.

---

## `EnumSet` is mutable and not thread-safe (§2.9.6) `[TRAP]`

Supporting fact with a large blast radius. `EnumSet` *feels* like a constant — you write `EnumSet.of(SAT, SUN)` once at class init and it reads like a literal. It is not. There is no immutable `EnumSet` in the JDK, and `final` protects the reference, not the bits.

**Pitfall:** believing `private static final EnumSet<Day> WEEKEND = EnumSet.of(SAT, SUN);` is safe to hand out. Symptom: some caller does `weekend.add(MON)` — or, far more often, `weekend.retainAll(x)` / `removeAll(x)` believing those return a new set — and every other user of the shared constant now sees corrupted data, with no exception and no obvious culprit. Under concurrency it is worse: `elements |= bit` is a read-modify-write on a non-volatile `long`, so concurrent `add`s lose updates silently, and `JumboEnumSet`'s cached `size` field can drift out of agreement with its own bits. Fix: expose `Collections.unmodifiableSet(...)`, or return `.clone()` per caller, or use `Set.of(SAT, SUN)` if you do not need the bulk-op fast path.

Real output:

```
before  = [SAT, SUN]
after   = [MON, SAT, SUN]   <-- final did not protect it
unmodifiableSet wrapper rejects add: UnsupportedOperationException
```

Note the cost of the fix: wrapping in `unmodifiableSet` also destroys the `instanceof RegularEnumSet` guard for anyone passing the wrapper as the *argument* to a bulk op, as shown above. Immutability and the one-instruction union are, in the current JDK, mutually exclusive.

---

## Pitfalls

### Assuming `EnumMap` is always cheaper than `HashMap`

**Wrong**

```java
// 400-constant generated enum, three mappings per request
EnumMap<ErrorCode, String> details = new EnumMap<>(ErrorCode.class);
details.put(ErrorCode.E001, "bad request");
details.put(ErrorCode.E042, "timeout");
details.put(ErrorCode.E399, "upstream");
```

Allocates `Object[400]` — 16 + 1600 = 1616 bytes, plus the 32-byte map — to hold three references. Measured shape of the same problem at n=65: `size() = 1, vals.length = 65, non-null slots = 1, null slots = 64`.

**Right**

```java
Map<ErrorCode, String> details = new HashMap<>(4);
details.put(ErrorCode.E001, "bad request");
details.put(ErrorCode.E042, "timeout");
details.put(ErrorCode.E399, "upstream");
```

Roughly 200 bytes, and `Enum.hashCode()` is identity-based so the hashing is cheap and collision-free in practice. Use `EnumMap` when `k` is a large fraction of `n`, or when `n` is small.

**Why people believe it:** every article compares `EnumMap` and `HashMap` on a fully-populated 5-constant enum, where `EnumMap` wins on every axis. The comparison is real; it just does not generalise to sparse maps over large enums.

### Treating a `static final EnumSet` as immutable

**Wrong**

```java
public static final EnumSet<Day> WEEKEND = EnumSet.of(Day.SAT, Day.SUN);
// somewhere far away:
WEEKEND.add(Day.MON);
System.out.println(WEEKEND);   // [MON, SAT, SUN]
```

**Right**

```java
private static final EnumSet<Day> WEEKEND_BITS = EnumSet.of(Day.SAT, Day.SUN);
public static final Set<Day> WEEKEND = Collections.unmodifiableSet(WEEKEND_BITS);
// or, if you need a mutable copy per caller:
public static EnumSet<Day> weekend() { return WEEKEND_BITS.clone(); }
```

`unmodifiableSet` throws `UnsupportedOperationException` on `add`. Accept that the wrapper is no longer a `RegularEnumSet`, so it will not trigger the bulk-op fast path as an argument.

**Why people believe it:** `EnumSet.of(...)` reads like a literal and `final` looks like it seals it, and the sibling `Set.of(...)` genuinely is immutable — so the two get conflated.

---

## Cheat sheet

| Fact | Value / source |
|---|---|
| `EnumMap` backing store | `Object[] vals`, indexed by `ordinal()`; no hashing, no `equals` (EnumMap.java:101, 271) |
| `EnumMap` iteration order | ordinal (declaration) order |
| `EnumMap` null key / null value | NPE / allowed, via private `NULL` sentinel (EnumMap.java:111-123) |
| `EnumMap` cost | ~32 bytes + (16 + 4n), eager, never resized; 4 bytes/slot, `keyUniverse` shared |
| Regular/Jumbo boundary | `universe.length <= 64` → `RegularEnumSet` (EnumSet.java:117) |
| `RegularEnumSet` state | one `long elements` (line 43); whole object ~32 bytes |
| `JumboEnumSet` state | `long[(n+63)>>>6]` + cached `int size` (lines 45-52) |
| `contains` / `add` / `remove` | `(elements & bit) != 0` / `elements \|= bit` / `elements &= ~bit` |
| `size` | `Long.bitCount(elements)` — Regular; cached field — Jumbo |
| `addAll` / `removeAll` / `retainAll` fast path | `\|=` / `&= ~` / `&=` — one bytecode (`lor` etc.) |
| Fast path conditions | arg `instanceof RegularEnumSet` **and** same `elementType` |
| Type mismatch | `addAll`: CCE (empty arg → `false`) · `removeAll`: `false`, unchanged · `retainAll`: **silently empties** · `containsAll`: `arg.isEmpty()` |
| complement mask | `-1L >>> -universe.length` == `-1L >>> (64-n)`; no `mask` field |
| Why `>>> -n` works | JLS §15.19: `long` shift distance masked with `0x3f` |
| `of` overloads | 1–5 fixed arity (no array); 6+ hits `@SafeVarargs`, allocates |
| `range(from, to)` | IAE if `from > to`; defined by ordinal, so reordering constants changes meaning |
| `copyOf(Collection)` | IAE on empty non-`EnumSet` — cannot infer the enum type |
| Mutability | mutable, not thread-safe, no immutable variant; `final` protects only the reference |
| Sealed since | Java 17: `permits JumboEnumSet, RegularEnumSet` |

---

## Self-test

**Q1.** Why does `EnumMap` need no `hashCode()` call, and what property of enums makes that safe?

<details><summary>Answer</summary>

`ordinal()` is already a perfect, minimal, dense hash of the key space: it returns a distinct value in `[0, n)` for each of the `n` constants, and `n` is fixed at class-initialisation time. So `vals[key.ordinal()]` (EnumMap.java:269-271) *is* the bucket index, with no possibility of collision and therefore no need for chaining, probing, `equals` comparison or resizing. `EnumMap` still calls `typeCheck(key)` first, to guarantee the ordinal came from the right enum — that check is what replaces the hash-and-compare.

</details>

**Q2.** An enum has 400 constants. You create one `EnumMap` per HTTP request holding 3 mappings. What is the per-request footprint, and what should you use instead?

<details><summary>Answer</summary>

The `EnumMap` object is ~32 bytes and `vals = new Object[400]` is 16 + 4×400 = 1616 bytes, so ~1648 bytes regardless of the 3 mappings — `vals` is allocated eagerly in the constructor (EnumMap.java:139) and never shrinks. A `HashMap` with 3 entries is roughly 48 + (16+64) + 3×32 = ~224 bytes. Use `HashMap` when `k << n`. `EnumMap`'s density is a feature when the map is dense and a leak-shaped cost when it is not.

</details>

**Q3.** What exactly is the boundary between `RegularEnumSet` and `JumboEnumSet`, and which side does an enum with exactly 64 constants land on?

<details><summary>Answer</summary>

`EnumSet.noneOf` (EnumSet.java:117) tests `universe.length <= 64`, inclusive, so 64 constants gives a `RegularEnumSet` — all 64 bits of one `long` are usable. 65 constants gives a `JumboEnumSet` backed by `new long[(65+63)>>>6]` = `long[2]`. Verified: `E64 -> java.util.RegularEnumSet`, `E65 -> java.util.JumboEnumSet`.

</details>

**Q4.** `RegularEnumSet.complement()` writes `elements &= -1L >>> -universe.length`. Explain the negative shift distance, and explain the `if (universe.length != 0)` guard.

<details><summary>Answer</summary>

JLS §15.19: for a `long` shift, the shift distance is the right operand masked with `0x3f`, i.e. taken mod 64. For `1 <= n <= 64`, `-n & 0x3f == 64 - n`, so `-1L >>> -n` produces `n` low one-bits — exactly the universe mask. The guard exists because at `n == 0` the mod-64 wrap gives a shift distance of 0, so `-1L >>> 0` is all ones rather than the all-zeros mask you want; that single case would leave 64 phantom bits set. Note there is no field called `mask` — the mask is this expression, computed inline each time.

</details>

**Q5.** Under what precise conditions does `enumSetA.addAll(enumSetB)` become a single bitwise OR, and name two realistic ways to lose that.

<details><summary>Answer</summary>

Both guards in `RegularEnumSet.addAll` (lines 217-226) must pass: the argument must be `instanceof RegularEnumSet`, and `es.elementType` must be reference-equal to `this.elementType`. Then the body is `elements |= es.elements` — one `lor` bytecode at offset 92 of the compiled method.

Two realistic ways to lose it: (1) pass `Collections.unmodifiableSet(enumSetB)` — the wrapper is not a `RegularEnumSet`, so the first guard fails and you get `AbstractCollection.addAll`'s per-element loop; (2) the enum has more than 64 constants, so both sets are `JumboEnumSet`s — the fast path there is a loop over `ceil(n/64)` words, still fast but no longer one instruction.

</details>

**Q6.** `((Set) daySet).removeAll(otherEnumSet)` and `((Set) daySet).retainAll(otherEnumSet)` are both called with a set of a *different* enum type. What happens in each case, and why do they differ?

<details><summary>Answer</summary>

`removeAll` returns `false` and leaves the set untouched (RegularEnumSet.java:245-246). `retainAll` sets `elements = 0`, emptying the set, and returns whether that changed anything (lines 265-269). Both are set-theoretically correct for disjoint universes: nothing can be removed from a set by a collection sharing no elements with it, and the intersection with such a collection is empty. Real output: `removeAll ... changed=false set=[MON, TUE]` and `retainAll ... changed=true set=[]`. `addAll` in the same situation throws `ClassCastException` — three methods, three different mismatch behaviours, all derived from the same disjointness fact.

</details>

**Q7.** `private static final EnumSet<Day> WEEKEND = EnumSet.of(SAT, SUN);` — is this a safe constant to expose from a public API?

<details><summary>Answer</summary>

No. `final` freezes the reference, not the `long elements` field behind it. Any caller can `add`, `remove`, `clear` or `retainAll` on it and permanently corrupt the shared value with no exception. There is no immutable `EnumSet` in the JDK. Demonstrated: `[SAT, SUN]` became `[MON, SAT, SUN]` after a single `add` through a `Set<Day>` parameter. Fix with `Collections.unmodifiableSet`, or hand out `.clone()` per caller, or use `Set.of(SAT, SUN)` — accepting in the first and third cases that you lose the `instanceof RegularEnumSet` bulk-op fast path.

</details>

**Q8.** `EnumSet.copyOf(someCollection)` throws `IllegalArgumentException` on an empty `ArrayList` but not on an empty `EnumSet`. Why?

<details><summary>Answer</summary>

`copyOf(Collection<E> c)` (EnumSet.java:172-185) needs the runtime `Class` of the enum to size the universe and pick Regular vs Jumbo. If `c` is an `EnumSet`, that class is already stored in its `elementType` field, so `clone()` works even when the set is empty. Otherwise the only way to learn the type is `c.iterator().next().getDeclaringClass()` — which requires at least one element, hence `if (c.isEmpty()) throw new IllegalArgumentException("Collection is empty")`. Use `EnumSet.noneOf(Day.class)` when you want an empty set.

</details>

**Q9.** Why does `EnumSet.of` have five fixed-arity overloads before the varargs one, and does the behaviour differ?

<details><summary>Answer</summary>

Purely to avoid the varargs array allocation on the common small cases: `of(e1..e5)` are five separate methods (EnumSet.java:217, 238, 261, 286, 313), each doing `noneOf` plus N `add` calls with no array. A sixth argument selects `@SafeVarargs of(E first, E... rest)` (line 340), which allocates an `E[]` for `rest` and loops — the javadoc at line 329 warns it "is likely to run slower". Behaviour is identical; only allocation differs. Verified: `of(MON..FRI)` gives `[MON, TUE, WED, THU, FRI]` and `of(MON..SAT)` gives `[MON, TUE, WED, THU, FRI, SAT]`.

</details>

---

**Leaves covered:** 2.9.1–2.9.6 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** D-51
**Target version:** Java 21 LTS
**Lines:** 593
