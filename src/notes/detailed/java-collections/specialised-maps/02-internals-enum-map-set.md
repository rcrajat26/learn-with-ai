# 02 Java Collections — Specialised maps and sets — INTERNALS (§3.10.1–3.10.7)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [specialised-maps/01-enum-collections.md](01-enum-collections.md) · Next: [specialised-maps/02b-internals-enum-set.md](02b-internals-enum-set.md)

This file covers **`EnumMap` internals only** (leaves 3.10.1–3.10.7): fields, the shared uncloned
`keyUniverse`, `put`, the `NULL` sentinel, iteration order, the `EntryIterator` correction, and
the memory arithmetic. `EnumSet` internals — the `Regular`/`Jumbo` split, the bit arithmetic,
`complement()`, ordinal dependence and the enum-keyed `HashMap` comparison — continue in
[02b-internals-enum-set.md](02b-internals-enum-set.md). The filename here says "enum-map-set"
for continuity with the index; its scope is `EnumMap`.

Every source line quoted below is from JDK 21 `java.base/java/util/EnumMap.java`, cited as
`File:line`. Every `[PROVE]` / `[NUM]` claim is backed by real output from programs compiled and
run on this machine (`javac 21`, HotSpot 21, macOS/aarch64). One syllabus claim in this range is
wrong against the source; the correction is marked **Correction** at the point of the claim.

## The family, before the streets

| Type | Storage | `size()` cost | Membership cost | Ordering | Where covered |
|---|---|---|---|---|---|
| `EnumMap<K,V>` | `Object[] vals`, one slot per enum constant | field read | array read at `ordinal()` | ordinal (declaration) order | this file |
| `HashMap<K,V>` with enum keys | `Node[] table` + a `Node` per mapping | field read | identity hash, spread, mask, bucket walk | unspecified | [02b](02b-internals-enum-set.md) |
| `RegularEnumSet<E>` | one `long elements` | `Long.bitCount` | one shift + AND | ordinal order | [02b](02b-internals-enum-set.md) |
| `JumboEnumSet<E>` | `long[] elements` + cached `int size` | field read | array read + shift + AND | ordinal order | [02b](02b-internals-enum-set.md) |

All four rest on one idea — an enum constant already carries a dense integer identity — and the
design question is whether you use it (`EnumMap`, `EnumSet`) or throw it away and re-derive a
location (`HashMap`). `EnumMap` is the only one of the four that is public and non-`sealed`.

---

## `EnumMap` is an array with an enum-shaped index

### Mental model

Forget maps. Picture a coat-rack bolted to the wall with exactly one numbered peg per enum
constant, in declaration order. `put(WED, x)` does not hash anything, does not search
anything, does not allocate anything: it walks to peg 2 and hangs `x` there. An empty peg
means "no mapping". Iteration is walking left to right and skipping empty pegs. That is the
entire data structure — everything else in the class is bookkeeping to make an array behave
like a `Map`.

### Why it exists

`Map<Day, X>` with `HashMap` works, but you pay for machinery you cannot use. An enum key
already carries a dense, contiguous, compile-time-known integer identity — `ordinal()`. Hashing
throws that away and re-derives a location from an identity hash code, then stores a `Node`
object per mapping to hold key, value, hash and chain pointer. Before `EnumMap` existed
(Java 5 introduced both enums and `EnumMap`), the idiom was a hand-rolled `Object[]` indexed by
an `int` constant from an `interface Constants { int MON = 0; }` — type-unsafe, and every read
site repeated the bounds and cast logic. `EnumMap` is that array with the type safety put back.

### When to reach for it, and when not

Reach for it whenever the key type is a single enum: it is strictly cheaper than `HashMap` on
every axis except memory, and that one exception is why the sibling still wins sometimes —
`EnumMap` allocates one reference slot **per enum constant**, used or not, so for a 500-constant
enum holding 3 mappings `HashMap` wins on footprint by an order of magnitude (arithmetic below,
§3.10.7). `EnumMap` also cannot hold keys from two enum types, cannot hold a `null` key, and is
not concurrent — for that, `ConcurrentHashMap` or an ordinal-indexed `AtomicReferenceArray`.

### How it works — the source walk

**Fields** `[SOURCE]` `[RESEARCH]` — `EnumMap.java:89`, `:94`, `:101`, `:106`:

```java
    private final Class<K> keyType;        // :89  identity of the enum type; the only non-transient field
    private transient K[] keyUniverse;     // :94  "All of the values comprising K.  (Cached for performance.)"
    private transient Object[] vals;       // :101 "The ith element is the value to which universe[i] is
                                           //       currently mapped, or null if it isn't mapped to anything,
                                           //       or NULL if it's mapped to null."
    private transient int size = 0;        // :106 number of mappings
```

Four fields, no `Node` class, no `table`, no `threshold`, no `loadFactor`, no `modCount`.

- `keyType` is `final` and **not** `transient`: it is the only piece of state the default
  serialization writes, which is why `writeObject` (`:766`) has to re-emit the key/value pairs
  by hand and `readObject` rebuilds `keyUniverse` and `vals` from `keyType`.
- `vals` is `Object[]`, not `V[]`, because the array also stores the `NULL` sentinel, which is
  not a `V`.
- There is no `modCount`. That is the mechanical reason the javadoc (`:42-45`) promises
  *weakly consistent* iterators that "will never throw `ConcurrentModificationException`" —
  the class has no counter with which to detect a comodification.

**The constructor** — `EnumMap.java:136-140`:

```java
    public EnumMap(Class<K> keyType) {
        this.keyType = keyType;
        keyUniverse = getKeyUniverse(keyType);
        vals = new Object[keyUniverse.length];
    }
```

Two statements of work. `vals` is sized once, at construction, to the full universe, and is
**never resized** — there is no growth path in the class because there is nothing to grow into.

**`keyUniverse` via `SharedSecrets`** `[SOURCE]` `[RESEARCH]` — `EnumMap.java:28` and `:744-751`:

```java
import jdk.internal.access.SharedSecrets;                       // :28

    /**
     * Returns all of the values comprising K.
     * The result is uncloned, cached, and shared by all callers.   // :746
     */
    private static <K extends Enum<K>> K[] getKeyUniverse(Class<K> keyType) {
        return SharedSecrets.getJavaLangAccess()
                                        .getEnumConstantsShared(keyType);   // :749-750
    }
```

The public route to an enum's constants is `Class.getEnumConstants()`, which **clones** its
cached array on every call — it must, because the array is mutable and handing out the master
copy would let any caller corrupt every future reader. `getEnumConstantsShared` is the internal
back door that returns the master copy itself, reached through `SharedSecrets`, the JDK's
mechanism for one `java.base` package to call a non-exported method in another. The consequence:
constructing an `EnumMap` costs **zero** array copies for the key universe, no matter how large
the enum. `EnumSet` uses the identical trick at `EnumSet.java:408-409`.

Why is sharing a mutable array safe here? Because `EnumMap` only ever **reads** `keyUniverse`
— `keyUniverse[index]` in `KeyIterator.next()` (`:548`), `Entry.getKey()` (`:588`),
`equals` (`:663`), `entryHashCode` (`:713`) — and `keyUniverse.length` for sizing. There is no
write to any element anywhere in the class, so the shared master copy cannot be perturbed
through this route. The copy constructors lean on the same invariant and alias it deliberately
rather than re-fetching (`EnumMap.java:150-152` and the `instanceof` branch at `:171-173`):

```java
    public EnumMap(EnumMap<K, ? extends V> m) {
        keyType = m.keyType;
        keyUniverse = m.keyUniverse;    // :151 alias, not copy — same master array
        vals = m.vals.clone();          // :152 the values ARE copied; this is where the cost is
        size = m.size;
    }
```

`[PROVE]` Reflectively reading the field out of two independently constructed maps, and
comparing against the public API:

```
=== 6. keyUniverse is the SAME array for every EnumMap of that type ===
a.keyUniverse == b.keyUniverse ? true
kuA == Day.values()            ? false
Day.values() == Day.values()   ? false
kuA content                    = [MON, TUE, WED, THU, FRI]
```

Two separate `EnumMap` instances share one array object; `Day.values()` — which compiles to
`$VALUES.clone()` — is a different object every call, and never the same object the map holds.
That is the clone `EnumMap` skips.

**`put`** `[SOURCE]` — `EnumMap.java:266-275`:

```java
    public V put(K key, V value) {
        typeCheck(key);                        // :267 keyClass == keyType || keyClass.getSuperclass() == keyType
        int index = key.ordinal();             // :269 the "hash" — already computed, stored in the constant
        Object oldValue = vals[index];         // :270
        vals[index] = maskNull(value);         // :271
        if (oldValue == null)                  // :272 null slot means "was absent"
            size++;                            // :273
        return unmaskNull(oldValue);           // :274
    }
```

Line by line: `typeCheck` (`:738-742`) compares `key.getClass()` against `keyType`, and also
`getSuperclass()` because an enum constant with a body (`MON { ... }`) is an instance of an
anonymous subclass of the enum. `key.ordinal()` is a field read on the constant — no arithmetic,
no hashing, no `hash ^ (hash >>> 16)` spreading, no bucket index masking. Then one array read,
one array write, one branch. `get` (`:245-248`) and `remove` (`:286-295`) are the same shape.
`containsKey` (`:222`) is literally `isValidKey(key) && vals[ordinal] != null`.

There is no collision path, so no chain walk and no treeify threshold: `EnumMap` is O(1)
**worst case**, not amortised O(1). That is a stronger guarantee than `HashMap` offers, and the
trade-off it buys is the fixed footprint.

**The `NULL` sentinel** `[SOURCE]` `[RESEARCH]` — `EnumMap.java:108-128`:

```java
    /**
     * Distinguished non-null value for representing null values.
     */
    private static final Object NULL = new Object() {
        public int hashCode() {
            return 0;
        }

        public String toString() {
            return "java.util.EnumMap.NULL";
        }
    };

    private Object maskNull(Object value) {
        return (value == null ? NULL : value);
    }

    @SuppressWarnings("unchecked")
    private V unmaskNull(Object value) {
        return (V)(value == NULL ? null : value);
    }
```

The problem being solved: `vals[i] == null` already means "no mapping for `keyUniverse[i]`", so
if a `null` **value** were stored as a raw `null`, `put(TUE, null)` would be indistinguishable
from "TUE absent" and `size` would drift. `NULL` is a private singleton that occupies the slot
instead. It is an anonymous subclass of `Object` for two reasons visible in the body:
`hashCode()` returns 0 so that `entryHashCode` (`:713`) — `keyUniverse[i].hashCode() ^ vals[i].hashCode()`
— produces the key's hash XOR 0, matching the `Map.Entry` contract's
`hashCode(key) ^ hashCode(value)` with `hashCode(null) == 0`; and `toString()` returns a
diagnosable name if the sentinel ever leaks into a stack trace or a debugger.

Note the asymmetric use: `maskNull` is applied on the way **in** (`put:271`, `setValue:599`) and
also to the *query argument* on lookups by value (`containsValue:204`, `removeMapping:301`,
`Values.remove:439`), so `containsValue(null)` becomes `NULL.equals(vals[i])`. `unmaskNull` is
applied on every way **out**.

**Iteration in ordinal order, skipping nulls** `[SOURCE]` — `EnumMap.java:514-559`:

```java
    private abstract class EnumMapIterator<T> implements Iterator<T> {
        int index = 0;                 // :516 "Lower bound on index of next element to return"
        int lastReturnedIndex = -1;    // :519

        public boolean hasNext() {
            while (index < vals.length && vals[index] == null)   // :522 skip empty pegs
                index++;                                          // :523
            return index != vals.length;                          // :524
        }

        public void remove() {
            checkLastReturnedIndex();                  // :528 throws ISE if next() not called
            if (vals[lastReturnedIndex] != null) {     // :530 tolerant of a concurrent removal
                vals[lastReturnedIndex] = null;        // :531
                size--;                                // :532
            }
            lastReturnedIndex = -1;                    // :534
        }
    }
```

`hasNext()` is where the scanning happens — it advances `index` past null slots as a side
effect, which is why `next()` (`:544-548`) can be three lines. Two consequences worth naming.
First, iteration cost is O(number of enum constants), **not** O(size): a 3-entry `EnumMap` over
a 500-constant enum scans 500 slots. Second, `remove()`'s `!= null` guard at `:530` means the
iterator silently tolerates the mapping having already vanished — that is the weak-consistency
promise implemented, in place of a `modCount` check.

Ordinal order is not "usually" declaration order; it *is* declaration order, because
`ordinal()` is assigned by the compiler in source order and `vals` is indexed by it. `[PROVE]`

```
=== 7. iteration is ordinal order regardless of insertion order ===
inserted FRI,MON,THU -> [MON, THU, FRI]
```

**Memory** `[NUM]` `[TRAP]` — the arithmetic, on 64-bit HotSpot with compressed oops (the
default up to a 32 GB heap): object header 12 bytes, array header 16 bytes (12 + 4-byte length),
reference 4 bytes, `int` 4 bytes, everything padded to an 8-byte boundary.

An `EnumMap` over an `N`-constant enum, holding `m` mappings:

```
EnumMap instance : 12 header + 4 keyType + 4 keyUniverse + 4 vals + 4 size = 28 -> 32 bytes
vals array       : 16 header + 4*N, padded up to a multiple of 8
keyUniverse      : 0 bytes charged — shared master array, one per enum type per JVM
```

- `N = 5`,  `m = 3`:   32 + (16 + 20 = 36 -> 40)               = **72 bytes**
- `N = 500`, `m = 3`:  32 + (16 + 2000 = 2016)                 = **2048 bytes**
- `N = 500`, `m = 500`: same **2048 bytes** — footprint is independent of `m`

A `HashMap` with 3 entries, for contrast: map instance 12 header + 4 table + 4 entrySet +
4 keySet + 4 values + 4 size + 4 modCount + 4 threshold + 4 loadFactor = 44 -> 48 bytes; default
`Node[16]` table = 16 + 64 = 80 bytes; three `Node`s at 12 header + 4 hash + 4 key + 4 value +
4 next = 28 -> 32 bytes each = 96 bytes. Total **224 bytes**, and it grows with `m`, not with `N`.

So the crossover is real and computable: `EnumMap` wins below roughly
`N < 4m + 20` constants and loses badly above it. At `N = 500, m = 3` it is 2048 vs 224 — a
9.1x loss. **Pitfall:** "`EnumMap` is always the cheap choice for enum keys." Symptom: a
service with a 400-constant `ErrorCode` enum and a per-request `EnumMap<ErrorCode, Counter>`
holding two entries allocates ~1.6 KB per request and shows up as an allocation-rate
regression, not a latency one. Fix: for a large, sparsely-populated enum universe, use
`HashMap` (or `EnumSet` plus a side array) and reserve `EnumMap` for dense or small universes.

### The picture

![EnumMap internals: keyType plus a shared uncloned keyUniverse reached via SharedSecrets, a vals array indexed directly by ordinal with empty slots for absent keys, and one slot holding the private NULL sentinel that distinguishes a null value from an absent key](../diagrams/D-114-enummap-internals.svg)

Look at three things in that diagram: `keyUniverse` has an arrow *out* of the map instance to
an array owned by the enum class, not a copy inside the map; the index into `vals` is
`ordinal()` with no transformation applied; and the slot holding `NULL` is visibly distinct
from the slots holding a plain empty reference.

### Minimal runnable example

```java
enum Day { MON, TUE, WED, THU, FRI }

EnumMap<Day, String> m = new EnumMap<>(Day.class);
m.put(Day.FRI, "rest");
m.put(Day.MON, "gym");
m.put(Day.TUE, null);           // legal: a null VALUE is stored as the NULL sentinel

System.out.println(m);                       // {MON=gym, TUE=null, FRI=rest}  ordinal order
System.out.println(m.get(Day.TUE));          // null  -- mapped to null
System.out.println(m.get(Day.WED));          // null  -- absent
System.out.println(m.containsKey(Day.TUE));  // true
System.out.println(m.containsKey(Day.WED));  // false
System.out.println(m.size());                // 3

try {
    m.put(null, "x");                        // null KEY is not legal
} catch (NullPointerException e) {
    System.out.println("null key rejected by typeCheck: " + e.getClass().getSimpleName());
}
```

Verified output for the `null`-value half `[PROVE]`:

```
=== 5. NULL sentinel: null value vs absent key ===
get(TUE)            = null
get(THU)            = null
containsKey(TUE)    = true
containsKey(THU)    = false
size                = 1
containsValue(null) = true
```

### The gotcha

`typeCheck` calls `key.getClass()` before any null check, so a `null` key throws
`NullPointerException` from `put`, but `get(null)`, `containsKey(null)` and `remove(null)` route
through `isValidKey` (`:313-319`), which returns `false` for `null` and therefore answer
politely rather than throwing. That asymmetry is deliberate and documented at `:47-49`, and it
means a `null` key bug surfaces at the write site, never the read site.

> **Definition.** `EnumMap` is a `Map` implemented as a single `Object[]` sized to the enum's
> full constant universe and indexed directly by `ordinal()`, giving worst-case O(1) access
> with no hashing, ordinal-order iteration, and a footprint fixed by the size of the enum
> rather than by the number of mappings.

---

## `EntryIterator`: fresh objects that are live views

### Mental model

Every `next()` hands you a **new** two-word object whose only content is an `int index`. It is
not a copy of the mapping; it is a *pointer into the map*, like a cell reference in a
spreadsheet. `A1` is a distinct piece of paper each time you write it down, and it still shows
whatever is in `A1` right now.

### Why the folklore says otherwise

A widely-repeated claim — and the wording of syllabus leaf 3.10.6 — is that `EnumMap`'s
`EntryIterator` reuses a **single** `Entry` instance, so collecting `entrySet()` into a list
gives *n* aliases of one mutating object. **Correction: this is false, and has never been true
in any shipped JDK.** `EnumMap.java:561-577`:

```java
    private class EntryIterator extends EnumMapIterator<Map.Entry<K,V>> {
        private Entry lastReturnedEntry;                       // :562

        public Map.Entry<K,V> next() {
            if (!hasNext())
                throw new NoSuchElementException();
            lastReturnedEntry = new Entry(index++);            // :567  <-- FRESH allocation, every call
            return lastReturnedEntry;                          // :568
        }

        public void remove() {
            lastReturnedIndex =
                ((null == lastReturnedEntry) ? -1 : lastReturnedEntry.index);   // :572-573
            super.remove();                                    // :574
            lastReturnedEntry.index = lastReturnedIndex;       // :575  (now -1)
            lastReturnedEntry = null;                          // :576
        }
```

Line `:567` is `new Entry(index++)`. The same line is present at `EnumMap.java:572` in JDK 8,
`:564` in JDK 17, `:567` in JDK 21 and `:568` in JDK 25 — identical code, different line
numbers. So this is **not** a version trap: there is no release in the 8–25 range where the
reused-instance model holds. The folklore was simply wrong from the start.

`lastReturnedEntry` is a **`remove()`-support field, not an allocation optimisation.** Read
`remove()` at `:571-577`: it needs the index of the entry it just returned, so it reads it off
`lastReturnedEntry` (`:572-573`), stores it in the superclass's `lastReturnedIndex` so that
`super.remove()` (`:574`) knows which `vals` slot to clear, then writes `-1` back into the
retained entry's `index` field (`:575`) to poison it, and finally drops the reference (`:576`).
Its entire job is to carry an index across one method call and then invalidate the handle.

Why is the folklore plausible? Three reasons, all of them true of *something*: (1) the field is
named `lastReturnedEntry`, which sounds like a cache; (2) the closely analogous
`Map.Entry`-reuse trick genuinely exists elsewhere — it is standard in Hadoop/Avro record
readers, in `Int2ObjectMap` fast iterators in fastutil, and in some `Iterator` implementations
in Trove — so an engineer primed on those expects it here; and (3) the *behavioural* symptom
people remember is real, just for a different reason: a retained `Entry` really does change
what it reports, because it is a live view, not because it is shared.

### How the real `Entry` works

`EnumMap.java:579-635`, the inner class:

```java
        private class Entry implements Map.Entry<K,V> {
            private int index;                             // :580  the ONLY field

            private Entry(int index) {
                this.index = index;
            }

            public K getKey() {
                checkIndexForEntryUse();                   // :587
                return keyUniverse[index];                 // :588  read LIVE from the shared universe
            }

            public V getValue() {
                checkIndexForEntryUse();                   // :592
                return unmaskNull(vals[index]);            // :593  read LIVE from the map's array
            }

            public V setValue(V value) {
                checkIndexForEntryUse();
                V oldValue = unmaskNull(vals[index]);
                vals[index] = maskNull(value);             // :599  writes straight THROUGH to the map
                return oldValue;
            }

            private void checkIndexForEntryUse() {
                if (index < 0)                             // :633
                    throw new IllegalStateException("Entry was removed");   // :634
            }
        }
```

One `int` field. No cached key, no cached value. `getKey()` and `getValue()` re-read
`keyUniverse[index]` and `vals[index]` **on every call** — so the entry reflects whatever the
map holds at the moment you ask, and `setValue` mutates the map with no write-back step.
`equals` (`:603-615`), `hashCode` (`:617-622`) and `toString` (`:624-630`) each guard on
`index < 0` and fall back to `Object` identity semantics for a poisoned entry.

![EnumMap.EntryIterator: the folklore model on the left (one Entry instance handed out repeatedly, n aliases) versus the source-verified model on the right (a fresh Entry per next(), each holding only an int index that reads vals[index] live)](../diagrams/D-115-enummap-entryiterator-fresh-entry.svg)

In the right-hand panel, look at the arrows: three distinct `Entry` objects, each with its own
`index`, all pointing back into the *same* `vals` array. Distinct identity, shared state.

### `[PROVE]` — distinct objects, live values

```
=== 1. EntryIterator hands out a FRESH Entry per next() ===
collected           = [MON=gym, WED=run, FRI=rest]
distinct identities = true
e0 class            = java.util.EnumMap$EntryIterator$Entry
e0 == e1 ?          = false

=== 2. but each fresh Entry is a LIVE VIEW on vals[index] ===
held before put     = MON=gym
held after put      = MON=swim   <-- changed without touching held
held after remove   = MON=null   <-- key still resolves, value now null
map                 = {WED=run, FRI=rest}
```

The program that produced it:

```java
EnumMap<Day, String> m = new EnumMap<>(Day.class);
m.put(Day.MON, "gym");
m.put(Day.WED, "run");
m.put(Day.FRI, "rest");

List<Map.Entry<Day, String>> live = new ArrayList<>();
for (Map.Entry<Day, String> e : m.entrySet())     // per-element add -> real Entry views
    live.add(e);

System.out.println(live);                          // [MON=gym, WED=run, FRI=rest]
System.out.println(live.get(0) == live.get(1));    // false -- distinct objects

Map.Entry<Day, String> held = live.get(0);
m.put(Day.MON, "swim");
System.out.println(held);                          // MON=swim   -- live view
m.remove(Day.MON);
System.out.println(held);                          // MON=null   -- slot cleared under it
```

Note what the last two lines mean for correctness: the folklore's *conclusion* ("the collected
list is unreliable") survives the correction, but the *mechanism* is different, and so is the
fix. Aliasing would be fixed by copying entries; liveness is fixed by copying **values**.

**Correction to a second detail:** the syllabus framing "after a `remove()` reshuffle the
retained entry's index no longer means what the caller thinks" is imprecise for `EnumMap`.
There is no reshuffle — `index == ordinal` is stable for the lifetime of the enum type, so
`getKey()` always returns the right key. What actually changes is `vals[index]`, which is why
the retained entry above reports `MON=null` rather than a *different* key's value.

### Two collection routes, two different results

`[PROVE]` `EnumMap`'s `EntrySet` overrides `toArray()` (`:491-511`), and that override does
**not** hand out live `Entry` views:

```java
        private Object[] fillEntryArray(Object[] a) {
            int j = 0;
            for (int i = 0; i < vals.length; i++)
                if (vals[i] != null)
                    a[j++] = new AbstractMap.SimpleEntry<>(         // :508 snapshot type
                        keyUniverse[i], unmaskNull(vals[i]));       // :509 values copied out NOW
            return a;
        }
```

`new ArrayList<>(m.entrySet())` calls `Collection.toArray()`, hits this override, and therefore
produces `AbstractMap.SimpleEntry` snapshots. A manual `for`-loop `add` produces live
`EnumMap$EntryIterator$Entry` views. Same-looking code, different object types, opposite
aliasing behaviour:

```
=== 3. new ArrayList<>(entrySet()) does NOT give live views ===
snap.get(0) class   = java.util.AbstractMap$SimpleEntry
snap before put     = MON=gym
snap after put      = MON=gym   <-- frozen
map                 = {MON=yoga, WED=run, FRI=rest}
```

**Insight:** this is why the folklore is so hard to kill by casual experiment. The most natural
way to "collect `entrySet()` into a list" is `new ArrayList<>(map.entrySet())`, which silently
gives you snapshots and therefore *looks* correct; you only meet the live views if you loop
and `add` by hand, or keep the reference the enhanced-`for` variable held.

### The gotcha

`Iterator.remove()` poisons the entry it just returned by writing `-1` into its `index`
(`:575`), so every subsequent method on that object throws:

```java
Iterator<Map.Entry<Day, String>> it = m2.entrySet().iterator();
Map.Entry<Day, String> first = it.next();
it.remove();
try {
    System.out.println(first.getValue());
} catch (IllegalStateException ex) {
    System.out.println("threw " + ex.getClass().getSimpleName() + ": " + ex.getMessage());
}
```

```
=== 4. EntryIterator.remove() poisons the entry it just returned ===
first.getValue()    threw IllegalStateException: Entry was removed
map after remove    = {TUE=b}
```

> **Definition.** `EnumMap.EntryIterator` allocates a fresh `Entry` on every `next()`; each
> `Entry` holds nothing but an `int index` and reads `keyUniverse[index]` / `vals[index]` live,
> so entries are distinct objects that nonetheless reflect later mutations of the map — and are
> poisoned with `index = -1` if removed through the iterator.

---

## Pitfalls

### Believing `EntryIterator` reuses one `Entry` object

**Wrong**

```java
// The belief: entries collected from an EnumMap are n aliases of one mutating object,
// so this list should print the same entry three times.
List<Map.Entry<Day, String>> live = new ArrayList<>();
for (Map.Entry<Day, String> e : m.entrySet())
    live.add(e);
System.out.println(live);                        // [MON=gym, WED=run, FRI=rest]  -- NOT aliased
System.out.println(live.get(0) == live.get(1));  // false
```

**Right**

```java
// The real hazard is liveness, not aliasing. Each Entry holds only an int index and
// reads vals[index] on every call, so it tracks the map.
Map.Entry<Day, String> held = live.get(0);
m.put(Day.MON, "swim");
System.out.println(held);            // MON=swim -- the map moved under the entry

// Fix: copy the value out, don't retain the Entry.
record Snapshot(Day key, String value) {}
List<Snapshot> safe = m.entrySet().stream()
        .map(e -> new Snapshot(e.getKey(), e.getValue()))
        .toList();
```

**Why people believe it:** the field is called `lastReturnedEntry`, which reads like a cache;
the reuse trick is genuinely real in fastutil, Trove and Hadoop record readers, so engineers
arrive primed for it; and the observable symptom — a retained entry reporting a changed value —
is real, so the folklore's conclusion looks confirmed by experiment even though its mechanism
is wrong. `EnumMap.java:567` is `new Entry(index++)` in JDK 8, 17, 21 and 25 alike.

### Assuming `EnumMap` is always the memory-cheap choice

**Wrong**

```java
// 500-constant ErrorCode enum, two mappings per request.
Map<ErrorCode, Counter> perRequest = new EnumMap<>(ErrorCode.class);
perRequest.put(ErrorCode.E017, c1);
perRequest.put(ErrorCode.E402, c2);
// Footprint: 32 (map) + 16 + 4*500 (vals) = 2048 bytes, for 2 entries.
```

**Right**

```java
// HashMap charges for entries, not for the universe: 48 + 80 + 2*32 = 192 bytes.
Map<ErrorCode, Counter> perRequest = new HashMap<>();
// Keep EnumMap for dense or small universes, where 4*N is small and the O(1)
// worst case and ordinal iteration order are pure profit.
```

**Why people believe it:** every tutorial demonstrates `EnumMap` on a five-constant enum, where
it wins on footprint by 3x, and the "array-backed, extremely compact" phrasing in the javadoc
(`EnumMap.java:34-35`) is true only relative to the universe size, not the entry count.

### Expecting `ConcurrentModificationException` from an `EnumMap` iterator

**Wrong**

```java
for (Day d : m.keySet())
    if (d == Day.WED)
        m.remove(Day.WED);                    // no CME -- EnumMap has no modCount
```

**Right**

```java
m.keySet().removeIf(d -> d == Day.WED);       // or iterator.remove(), the supported route
```

**Why people believe it:** every other `java.util` map fails fast, so the absence of a
`modCount` field in `EnumMap` surprises people. The javadoc states it plainly at
`EnumMap.java:42-45`: the views' iterators are *weakly consistent* and "will never throw
`ConcurrentModificationException`".

---

## Cheat sheet

| Fact | Value / source |
|---|---|
| `EnumMap` fields | `Class keyType` (`:89`), `K[] keyUniverse` (`:94`), `Object[] vals` (`:101`), `int size` (`:106`) |
| Only non-transient field | `keyType` — hence hand-written `writeObject` at `:766` |
| `keyUniverse` source | `SharedSecrets.getJavaLangAccess().getEnumConstantsShared` (`:749`) — shared, **uncloned** |
| `put` body | `vals[key.ordinal()] = maskNull(value)` (`:271`) — O(1) worst case, no hashing |
| Null value | stored as private `NULL` sentinel with `hashCode() == 0` (`:111-119`) |
| Null key | `put` throws NPE; `get`/`containsKey`/`remove` return quietly (`isValidKey`, `:313`) |
| `EnumMap` iteration | ordinal order; cost O(universe), skips nulls in `hasNext()` (`:522`) |
| `EnumMap` CME | never — no `modCount`; iterators weakly consistent (`:42-45`) |
| `EntryIterator.next()` | `new Entry(index++)` (`:567`) — **fresh object every call**, in JDK 8/17/21/25 |
| `Entry` state | one `int index`; `getKey`/`getValue` read live (`:588`, `:593`); `setValue` writes through (`:599`) |
| `lastReturnedEntry` | `remove()` support only: carries the index, then poisons it with `-1` (`:572-576`) |
| Poisoned entry | `index < 0` -> `IllegalStateException("Entry was removed")` (`:633-634`) |
| `new ArrayList<>(entrySet())` | gives `AbstractMap.SimpleEntry` **snapshots** via `fillEntryArray` (`:508`) |
| `EnumMap` bytes | `32 + 16 + 4N` (compressed oops); N=5 -> 72, N=500 -> 2048, independent of size |
| Footprint crossover | `EnumMap` loses to `HashMap` above roughly `N > 4m + 20` constants |
| `containsValue(null)` | works — argument is `maskNull`-ed too (`:204`) |
| `equals`/`hashCode` | walk `keyUniverse` (`:661`, `:703`); `entryHashCode` = `key.hashCode() ^ vals[i].hashCode()` (`:713`) |
| `clone()` | clones `vals`, nulls the cached `entrySet`, aliases `keyUniverse` (`:723-733`) |
| `putAll(EnumMap)` | slot-wise loop over `keyUniverse` (`:341-348`); foreign `keyType` throws CCE (`:338`) |
| `EnumSet` internals | next file: [02b-internals-enum-set.md](02b-internals-enum-set.md) |

---

## Self-test

**Q1.** `EnumMap` never clones the enum's constant array, but `Class.getEnumConstants()` always does. Why is the shortcut safe, and what would break if it were not?

<details><summary>Answer</summary>

`EnumMap.getKeyUniverse` (`EnumMap.java:748-751`) calls
`SharedSecrets.getJavaLangAccess().getEnumConstantsShared(keyType)`, which returns the JDK's
single master array rather than a copy — the javadoc at `:746` says "uncloned, cached, and
shared by all callers". It is safe because `EnumMap` only ever reads that array
(`keyUniverse[index]` at `:548`, `:588`, `:663`, `:713`, plus `.length` for sizing) and never
writes an element. `Class.getEnumConstants()` cannot take the shortcut because it hands the
array to arbitrary callers, any one of which could assign into it and corrupt the constants for
every subsequent reader in the JVM. If `EnumMap` did write, that corruption would propagate to
every `EnumMap`, every `EnumSet` and every `switch` over that enum type in the process. The
payoff: constructing an `EnumMap` over a 500-constant enum copies zero key references, and the
copy constructors at `:151` and `:172` alias `keyUniverse` too, so only `vals` is cloned.

</details>

**Q2.** A colleague says "collect an `EnumMap`'s `entrySet()` into a list and you get n references to one mutating `Entry`". What is actually true, and how would you demonstrate the real hazard in three lines?

<details><summary>Answer</summary>

False. `EnumMap.java:567` is `lastReturnedEntry = new Entry(index++);` — a fresh `Entry` per
`next()`, identically in JDK 8 (`:572`), 17 (`:564`), 21 (`:567`) and 25 (`:568`). The field
`lastReturnedEntry` exists to support `remove()`: it carries the index into
`super.remove()` and is then poisoned with `-1` (`:572-576`).

The real hazard is that each `Entry` holds only an `int index` (`:580`) and reads
`keyUniverse[index]` / `vals[index]` live (`:588`, `:593`), so it is a view:

```java
Map.Entry<Day, String> held = m.entrySet().iterator().next();  // MON=gym
m.put(Day.MON, "swim");
System.out.println(held);   // MON=swim
```

Extra subtlety: `new ArrayList<>(m.entrySet())` will *not* reproduce this, because
`EntrySet.toArray` builds `AbstractMap.SimpleEntry` snapshots (`:508`). You have to add the
entries yourself, or retain the loop variable, to hold a live view.

</details>

**Q3.** Why does `EnumMap` need a `NULL` sentinel when `HashMap` stores a null value as a plain null?

<details><summary>Answer</summary>

Because `EnumMap` has no per-entry object in which to record existence. `HashMap` allocates a
`Node` whose presence means "mapped" and whose `value` field can independently be `null`.
`EnumMap` has only `vals[i]`, and `vals[i] == null` is already the encoding for "no mapping" —
it is what `containsKey` tests (`:222`), what `put` uses to decide whether to increment `size`
(`:272`), and what `hasNext` skips (`:522`). Storing a null value as a raw null would collapse
those two states. `NULL` (`:111-119`) is a private singleton occupying the slot instead;
`maskNull` (`:121`) substitutes it on the way in, `unmaskNull` (`:126`) removes it on the way
out. Its `hashCode()` returns 0 so `entryHashCode` (`:713`) keeps matching the `Map.Entry`
contract, where a null value contributes 0.

</details>

**Q4.** For which enums is `EnumMap` a worse footprint choice than `HashMap`, with the arithmetic?

<details><summary>Answer</summary>

`EnumMap` costs `32 + 16 + 4N` bytes on 64-bit HotSpot with compressed oops (32-byte map
instance: 12-byte header + four 4-byte fields, padded; plus an `Object[N]` at 16-byte header +
4 bytes per reference), and that total is independent of the number of mappings. `HashMap` with
`m` entries and a default 16-slot table costs `48 + (16 + 4·table) + 32m`.

- N=5, m=3: `EnumMap` 32 + 40 = 72 bytes; `HashMap` 48 + 80 + 96 = 224. `EnumMap` wins ~3x.
- N=500, m=3: `EnumMap` 32 + 2016 = 2048 bytes; `HashMap` 224. `EnumMap` loses ~9x.
- N=500, m=500: `EnumMap` still 2048; `HashMap` needs a 1024-slot table plus 500 nodes ≈ 20.2 KB. `EnumMap` wins ~10x.

The crossover is roughly `N > 4m + 20`. So the rule is: `EnumMap` for dense or small universes,
`HashMap` for a large enum you populate sparsely. Everything else — worst-case O(1), no
hashing, no `Node` allocation, declaration-order iteration — favours `EnumMap` unconditionally.

</details>

**Q5.** Trace what `EnumMap.EntryIterator.remove()` does to the `Entry` it last returned, and what a caller sees afterwards.

<details><summary>Answer</summary>

`EnumMap.java:571-577`. First it copies the entry's index into the superclass field:
`lastReturnedIndex = ((null == lastReturnedEntry) ? -1 : lastReturnedEntry.index)` (`:572-573`)
— the `null` branch produces `-1`, which makes `super.remove()`'s `checkLastReturnedIndex`
(`:537-540`) throw `IllegalStateException` when `next()` was never called. Then
`super.remove()` (`:574`) nulls `vals[lastReturnedIndex]`, decrements `size` if the slot was
occupied (`:530-533`), and resets `lastReturnedIndex` to `-1` (`:534`). Then `:575` writes that
`-1` back into the entry's own `index` field, and `:576` drops the iterator's reference.

A caller holding that `Entry` now sees `index < 0`, so `getKey()`, `getValue()` and `setValue()`
all throw `IllegalStateException` via `checkIndexForEntryUse` (`:632-635`), while `equals`
degrades to reference identity (`:604-605`), `hashCode` to `Object.hashCode` (`:618-619`) and
`toString` to `Object.toString` (`:625-626`). Verified:
`first.getValue() threw IllegalStateException: Entry was removed`.

</details>

**Q6.** Why can an `EnumMap` iterator never throw `ConcurrentModificationException`, and what is the cost of iterating one?

<details><summary>Answer</summary>

Because the class has no `modCount` field to compare against — its entire state is `keyType`,
`keyUniverse`, `vals` and `size` (`:89`, `:94`, `:101`, `:106`). With no comodification counter
there is nothing to fail fast on, which is why the javadoc at `:42-45` promises *weakly
consistent* iterators that "will never throw `ConcurrentModificationException`" and "may or may
not show the effects" of concurrent modification. `EnumMapIterator.remove()` even guards with
`if (vals[lastReturnedIndex] != null)` (`:530`) so that a mapping removed underneath it is
tolerated silently rather than reported. Practically: a structural modification during iteration
is a silent bug in an `EnumMap`, not a loud one.

The cost is O(number of enum constants), **not** O(size): `hasNext()` advances `index` past null
slots (`:522-523`), so a 3-entry map over a 500-constant enum touches 500 array slots per full
iteration. That is the opposite of `RegularEnumSet`'s iterator, which snapshots the bit vector
and is O(size). For a large, sparsely-populated enum, iteration cost is another reason to prefer
`HashMap`.

</details>

---

**Leaves covered:** 3.10.1–3.10.7 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** D-114, D-115
**Target version:** Java 21 LTS
**Lines:** 800
