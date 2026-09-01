# 02 Java Collections — Immutability and views — INTERNALS (§3.12.6–3.12.8)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/04-internals-immutable-collections.md](04-internals-immutable-collections.md) · Next: [immutable-collections/04b2-internals-salt-cds-and-null-hostility.md](04b2-internals-salt-cds-and-null-hostility.md)

All source citations are against `java.base/java/util/ImmutableCollections.java`
from `jdk-21.jdk/Contents/Home/lib/src.zip`, JDK 21.0.7+8-LTS-245. Bare `:NNN`
line numbers refer to that file. All transcripts are from that build on
macOS/aarch64 (Darwin 25.5.0).

This file covers **the open-addressed table only** — how `SetN` and `MapN` store
and find their contents. The salt (`SALT32L`/`REVERSE`), the CDS interaction and
null hostility continue in
[`04b2-internals-salt-cds-and-null-hostility.md`](04b2-internals-salt-cds-and-null-hostility.md).
The filename still says "and-salt" from before that split; the staleness is
deliberate, since renaming a published file breaks inbound links.

---

## The shape of the table

The previous file walked the class hierarchy — `AbstractImmutableCollection` down
to `List12`, `ListN`, `Set12`, `SetN`, `Map1`, `MapN`. This file is about the one
data structure inside the two `*N` classes.

| Class | Backing field | Slot count | Load factor | Salt used for placement? |
|---|---|---|---|---|
| `SetN<E>` | `E[] elements` (`:910`) | `EXPAND_FACTOR * n` = `2n` (`:920`) | ≤ 0.5 | No |
| `MapN<K,V>` | `Object[] table` (`:1174`) | `EXPAND_FACTOR * 2n`, made even = `4n` (`:1185-1187`) | ≤ 0.5 of pair slots | No |
| `Set12`, `Map1`, `Map2` | two/four `final` fields | n/a | n/a | No |
| iterators only | — | — | — | **Yes** — `SALT32L`, `REVERSE` (see `04b2`) |

Hold on to the last column. It is the single most-misstated fact about these
classes: **the salt never touches where an element is stored or how it is looked
up. It only picks where the iterator starts and which way it walks.** Everything in
this file is therefore deterministic and reproducible across JVM runs.

---

## Concept 1 — The open-addressed table: `SetN`, `probe`, and `MapN`'s interleaving

*Leaves 3.12.6, 3.12.7, 3.12.8.*

### Mental model

A row of six pigeonholes and three letters. Each letter has a "home" hole computed
from its hash. Post it into its home; if the home is taken, walk right until you
find an empty hole and drop it there. To find a letter later, go to its home and
walk right — you either meet the letter (found) or you meet an empty hole
(definitively absent, because a walk-right insert would have stopped there too).

No linked nodes, no `Node.next`, no tree bins. One flat `Object[]`, twice as long
as it needs to be. That is the entire structure.

### Why it exists

Every entry in a `HashMap` costs a separate `HashMap.Node` — header, `hash`, `key`,
`value`, `next`, ~32 bytes with compressed oops — plus a bucket-array slot.
Pre-Java-9, a small immutable set meant
`Collections.unmodifiableSet(new HashSet<>(Arrays.asList(...)))`: three levels of
indirection before you reach a table, and every `Node` still on the heap. `SetN`
collapses that to one object and one six-slot array for three elements.

**Insight:** the deep reason open addressing is *safe* here, not merely compact, is
that these collections cannot shrink. Open addressing's classic defect is deletion —
removing an element from the middle of a probe run breaks the run for everything
after it, so real open-addressed tables must write a tombstone instead of a `null`,
and tombstones then accumulate and must be rehashed away. `SetN` has no `remove`;
every mutator on `AbstractImmutableCollection` throws
`UnsupportedOperationException` (see `04c`). No deletion means no tombstones, so
`null` in a slot carries exactly one meaning: "empty, and therefore the probe run
ends here". Immutability is what buys the simplicity.

### When to reach for it, and when not

`Set.of` picks `SetN` for you at four or more elements (one and two go to
`Set12`). The sibling comparison is what an interview wants:

| Need | Winner | Why |
|---|---|---|
| Small, fixed, read-mostly set | `Set.of` → `SetN` | one array, no `Node`s, cache-resident |
| Any mutation after construction | `HashSet` | `SetN`'s mutators throw |
| Stable iteration order | `LinkedHashSet`, or `List.of` | `SetN`'s order varies per JVM run (`04b2`) |
| Nulls stored or queried | `HashSet` | `SetN` NPEs on both (`04b2`) |
| Thousands of elements | `HashSet` | `2n` slots is real memory at scale, and linear probing clusters worse than chaining under adversarial hashes |

The tradeoff shape: **O(1) average membership with no per-element object, but it
costs `2n` reference slots, its iteration order is deliberately unstable, and it
is hostile to null.**

### How it works — the source

`SetN`'s constructor, `:917-930`:

```java
        @SafeVarargs
        @SuppressWarnings("unchecked")
        SetN(E... input) {
            size = input.length; // implicit nullcheck of input

            elements = (E[])new Object[EXPAND_FACTOR * input.length];
            for (int i = 0; i < input.length; i++) {
                E e = input[i];
                int idx = probe(e); // implicit nullcheck of e
                if (idx >= 0) {
                    throw new IllegalArgumentException("duplicate element: " + e);
                } else {
                    elements[-(idx + 1)] = e;
                }
            }
        }
```

- `size = input.length` — `size` (`:913`, `@Stable final int`) is the *logical*
  count, deliberately not `elements.length`. Reading `input.length` is also the
  implicit null check on the varargs array: `Set.of((Object[]) null)` NPEs here.
- `new Object[EXPAND_FACTOR * input.length]` — the allocation. `EXPAND_FACTOR` is
  `static final int EXPAND_FACTOR = 2` at `:140`, documented at `:136-139` as "The
  reciprocal of load factor. Given a number of elements to store, multiply by this
  factor to get the table size." Reciprocal of 2 is 0.5, so the table is at most
  half full. **[NUM]** n = 3 → 6 slots; n = 10 → 20 slots.
- `probe(e)` — computes the slot. `// implicit nullcheck of e` is load-bearing:
  `probe` calls `pe.hashCode()` with no guard, so a null element NPEs there rather
  than in an explicit `requireNonNull`. That is leaf 3.12.12's mechanism, worked
  through in `04b2`.
- `if (idx >= 0) throw new IllegalArgumentException` — a non-negative return means
  an `equals`-matching element is already present. This is where `Set.of("a","a")`
  fails. (`Set.copyOf` does not fail: it routes through `new HashSet<>(coll)` and
  deduplicates — established in `03b`.)
- `elements[-(idx + 1)] = e` — a negative return is `-(freeSlot + 1)`, so
  `-(idx + 1)` recovers `freeSlot`. The expression is its own inverse.

`size`, `isEmpty`, `contains` at `:932-946`:

```java
        @Override
        public int size() {
            return size;
        }

        @Override
        public boolean isEmpty() {
            return size == 0;
        }

        @Override
        public boolean contains(Object o) {
            Objects.requireNonNull(o);
            return size > 0 && probe(o) >= 0;
        }
```

- `size()` returns the field, not the array length; otherwise every `Set.of`
  would report double its real size.
- `contains` has an **explicit** `Objects.requireNonNull(o)`, unlike the
  constructor's implicit one. Both NPE; the throw site differs, and that
  difference is the whole of "NPEs on some paths" — see `04b2`.
- `size > 0 &&` short-circuits before `probe`. It has to: `EMPTY_SET = new SetN<>()`
  (`:107`) has `elements.length == 0` and `Math.floorMod(h, 0)` throws
  `ArithmeticException`. Note the ordering, though — `requireNonNull` runs *first*,
  so `Set.of().contains(null)` NPEs rather than returning `false`.

`probe`, `:1009-1025` — leaf 3.12.7:

```java
        // returns index at which element is present; or if absent,
        // (-i - 1) where i is location where element should be inserted.
        // Callers are relying on this method to perform an implicit nullcheck
        // of pe
        private int probe(Object pe) {
            int idx = Math.floorMod(pe.hashCode(), elements.length);
            while (true) {
                E ee = elements[idx];
                if (ee == null) {
                    return -idx - 1;
                } else if (pe.equals(ee)) {
                    return idx;
                } else if (++idx == elements.length) {
                    idx = 0;
                }
            }
        }
```

- `Math.floorMod(pe.hashCode(), elements.length)` — the home slot. **No `SALT32L`
  here.** No hash spreading either: no `h ^ (h >>> 16)` as `HashMap` does, because
  `floorMod` against an arbitrary (non-power-of-two) length already mixes the high
  bits in, unlike `HashMap`'s `(n - 1) & h` mask which only ever sees the low bits.
  `floorMod` rather than `%` because `hashCode()` can be negative and `%` would
  yield a negative index.
- `ee == null → return -idx - 1` — the miss encoding. The empty slot *is* the proof
  of absence: an insertion walking this run would have stopped here too.
- `pe.equals(ee) → return idx` — the hit encoding. Note the probe key is the
  receiver: user `equals` is called as `query.equals(stored)`.
- `++idx == elements.length → idx = 0` — linear probing, stride 1, wrapping. Stride
  1 is chosen for locality: the next slot is almost always the same cache line.
- **`while (true)` with no bound.** No loop counter, no give-up. Termination rests
  entirely on the load factor, which is why `EXPAND_FACTOR` matters.

Return value `r`:

| `r` | Meaning | Recover the slot with |
|---|---|---|
| `r >= 0` | present, at slot `r` | `r` |
| `r < 0` | absent; `r` encodes the first free slot | `-(r + 1)` |

Zero is unambiguous: a hit at slot 0 returns `0`, a miss at slot 0 returns `-1`.
Same `-(i+1)` convention as `Arrays.binarySearch`, for the same reason — one `int`
carrying both a boolean and an index.

### [PROVE] The table always has a free slot, so `probe` always terminates

1. `elements.length == EXPAND_FACTOR * size == 2 * size` (`:920`, with
   `EXPAND_FACTOR == 2` at `:140`).
2. The constructor's loop runs exactly `size` times and each iteration writes at
   most one slot (`:927`), and only a slot that held `null`. So after construction
   the number of non-null slots is exactly `size`.
3. Free slots `= 2 * size - size = size`. **[NUM]** For any `size >= 1`, at least
   one free slot exists.
4. `probe` advances `idx` by 1 per iteration and wraps, so within
   `elements.length` iterations it visits every slot.
5. By (3) at least one visited slot is `null`, and the `ee == null` branch returns.
   Therefore `probe` returns after at most `elements.length` iterations. ∎

Worst case is `O(n)` probes, not `O(1)`. The `O(1)` claim is average-case under a
spreading hash; a set of keys all hashing to one home slot degenerates to a linear
scan of a `2n` array, and `SetN` has **no treeify escape hatch** — that is
`HashMap`'s answer, not this one. In practice `Set.of` arities are small enough
that `O(n)` over `2n` cache-line-local slots is still cheap.

**What breaks at `EXPAND_FACTOR = 1`.** Then `elements.length == size`, step (3)
gives zero free slots, and step (5) evaporates. A `contains` for an absent element
would visit every occupied slot, match none, wrap, and loop forever — an infinite
loop, not an exception. The class doc says exactly this at `:900-902`: "The element
array must be strictly larger than the size … so that at least one null is always
present." `MapN`'s doc repeats it at `:1164-1166`. Factor 2 is not a speed/memory
tuning knob; **factor 1 is a hang**, and that makes `EXPAND_FACTOR` a correctness
requirement rather than a tuning constant.

![D-119 — SetN's open-addressed table. Read the left panel first: 3 elements in EXPAND_FACTOR x 3 = 6 slots, so a free slot always exists. Then the probe() panel: `i` returned on a hit, `-(i+1)` on a miss — and note it carries no SALT32L reference. Then the two right-hand panels: two JVM runs, two different iteration orders, attributable to SALT32L and REVERSE alone (that half of the story is in `04b2`).](../diagrams/D-119-setn-open-addressing.svg)

### `MapN`'s interleaved table — leaf 3.12.8

`MapN` holds *one* array, not a key array and a value array. `:1173-1203`:

```java
        @Stable
        final Object[] table; // pairs of key, value

        @Stable
        final int size; // number of pairs

        MapN(Object... input) {
            if ((input.length & 1) != 0) { // implicit nullcheck of input
                throw new InternalError("length is odd");
            }
            size = input.length >> 1;

            int len = EXPAND_FACTOR * input.length;
            len = (len + 1) & ~1; // ensure table is even length
            table = new Object[len];

            for (int i = 0; i < input.length; i += 2) {
                @SuppressWarnings("unchecked")
                    K k = Objects.requireNonNull((K)input[i]);
                @SuppressWarnings("unchecked")
                    V v = Objects.requireNonNull((V)input[i+1]);
                int idx = probe(k);
                if (idx >= 0) {
                    throw new IllegalArgumentException("duplicate key: " + k);
                } else {
                    int dest = -(idx + 1);
                    table[dest] = k;
                    table[dest+1] = v;
                }
            }
        }
```

- `input` arrives already flattened as `k0, v0, k1, v1, …`, so an odd length is a
  JDK bug — hence `InternalError`, not `IllegalArgumentException`.
- `size = input.length >> 1` — pairs, not cells.
- `int len = EXPAND_FACTOR * input.length` multiplies the *flattened* length.
  **[NUM]** For n pairs, `input.length == 2n`, so `len == 4n` cells = `2n` pair
  slots holding `n` pairs — the same 0.5 load factor as `SetN`, measured in pairs.
  State the unit or the number is ambiguous: 3 pairs give `table.length == 12`, not
  6, as the transcript below shows.
- `len = (len + 1) & ~1` rounds up to even. With `EXPAND_FACTOR == 2` the product
  is already even, so this line is **currently dead code**; it is insurance against
  an odd `EXPAND_FACTOR`, and it is load-bearing for `probe`'s exact-equality wrap
  test below, which is only safe on an even-length table.
- `Objects.requireNonNull` on **both** key and value, explicitly. A null value
  would be harmless to the probe mechanism — rejecting it is an API choice, not a
  mechanical necessity.
- `table[dest] = k; table[dest+1] = v;` — the interleaving. Key at an even index,
  its value immediately after. One allocation, and a key and its value sit adjacent
  in memory, so a hitting `get` pulls both in one cache line.

`MapN.probe`, `:1323-1340`:

```java
        private int probe(Object pk) {
            int idx = Math.floorMod(pk.hashCode(), table.length >> 1) << 1;
            while (true) {
                @SuppressWarnings("unchecked")
                K ek = (K)table[idx];
                if (ek == null) {
                    return -idx - 1;
                } else if (pk.equals(ek)) {
                    return idx;
                } else if ((idx += 2) == table.length) {
                    idx = 0;
                }
            }
        }
```

- `floorMod(hash, table.length >> 1) << 1` — reduce modulo the number of *pair
  slots*, then double to get a cell index. The result is always even, so `idx`
  always lands on a key. **This is not `floorMod(hash, table.length)`** — a natural
  mis-remembering, and it would place keys on odd indices half the time.
- Again **no salt**. Identical to `SetN.probe` with stride 2 instead of 1, and the
  same `i` / `-(i+1)` encoding.
- `(idx += 2) == table.length` — an exact-equality wrap test, safe only because
  `table.length` is even and `idx` starts even. That is what `(len + 1) & ~1`
  protects. With an odd length, `idx` would step straight past `table.length` and
  throw `ArrayIndexOutOfBoundsException` instead of wrapping.

`get`, `:1235-1248`, shows why the encoding pays:

```java
        @Override
        @SuppressWarnings("unchecked")
        public V get(Object o) {
            if (size == 0) {
                Objects.requireNonNull(o);
                return null;
            }
            int i = probe(o);
            if (i >= 0) {
                return (V)table[i+1];
            } else {
                return null;
            }
        }
```

One `probe` call yields both "is it here" and the exact cell to read the value
from — `table[i+1]`, no second lookup. Note the asymmetry with `SetN.contains`:
`get` calls `requireNonNull` only in the `size == 0` branch, so on a non-empty map
a null key NPEs inside `probe` at `pk.hashCode()`. `04b2` measures that.

![D-120 — MapN's single interleaved Object[]. Follow one pair: the key lands at an even index 2i, its value at 2i+1. Then follow the collided key: its home index is occupied, so probe steps by 2, not 1, to the next even index.](../diagrams/D-120-mapn-interleaved-table.svg)

### The demonstration — a real table, dumped

Reflection is the only way to see the slots, so the run needs
`--add-opens java.base/java.util=ALL-UNNAMED`. `Fixed` is a record with a
hand-written `hashCode`, so we can force a genuine collision: the table is
`2 * 3 == 6` slots, and hashes 1 and 7 both `floorMod` to slot 1.

```java
import java.lang.reflect.Field;
import java.util.Map;
import java.util.Set;

public class TableDump2 {

    /** A key whose hashCode we control, so we can force a collision. */
    record Fixed(String name, int hash) {
        @Override public int hashCode() { return hash; }
    }

    static Object[] arrayField(Object coll, String name) throws Exception {
        Field f = coll.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return (Object[]) f.get(coll);
    }

    public static void main(String[] args) throws Exception {
        // 3 elements -> 2*3 = 6 slots. Hashes 1 and 7 both floorMod to slot 1.
        Set<Fixed> s = Set.of(new Fixed("A", 1), new Fixed("B", 7), new Fixed("C", 4));
        Object[] el = arrayField(s, "elements");
        System.out.println(s.getClass().getSimpleName() + ": elements.length = " + el.length
                + ", size = " + s.size());
        for (int i = 0; i < el.length; i++) {
            Object e = el[i];
            System.out.printf("  slot %d = %-22s home = %s%n", i, String.valueOf(e),
                    e == null ? "-" : Math.floorMod(e.hashCode(), el.length));
        }
        System.out.println("  contains(B)=" + s.contains(new Fixed("B", 7))
                + "  contains(absent, hash 1)=" + s.contains(new Fixed("Z", 1)));

        Map<String, Integer> m = Map.of("alpha", 1, "beta", 2, "gamma", 3);
        Object[] t = arrayField(m, "table");
        System.out.println(m.getClass().getSimpleName() + ": table.length = " + t.length
                + ", pair slots = " + (t.length >> 1) + ", size = " + m.size());
        for (int i = 0; i < t.length; i += 2) {
            Object k = t[i];
            System.out.printf("  table[%2d]=%-7s table[%2d]=%-5s home = %s%n",
                    i, String.valueOf(k), i + 1, String.valueOf(t[i + 1]),
                    k == null ? "-" : (Math.floorMod(k.hashCode(), t.length >> 1) << 1));
        }
    }
}
```

```
$ java --add-opens java.base/java.util=ALL-UNNAMED -cp out TableDump2
SetN: elements.length = 6, size = 3
  slot 0 = null                   home = -
  slot 1 = Fixed[name=A, hash=1]  home = 1
  slot 2 = Fixed[name=B, hash=7]  home = 1
  slot 3 = null                   home = -
  slot 4 = Fixed[name=C, hash=4]  home = 4
  slot 5 = null                   home = -
  contains(B)=true  contains(absent, hash 1)=false
MapN: table.length = 12, pair slots = 6, size = 3
  table[ 0]=null    table[ 1]=null  home = -
  table[ 2]=null    table[ 3]=null  home = -
  table[ 4]=alpha   table[ 5]=1     home = 4
  table[ 6]=null    table[ 7]=null  home = -
  table[ 8]=beta    table[ 9]=2     home = 8
  table[10]=gamma   table[11]=3     home = 10
```

Everything from the source walk is visible.

- Six slots for three elements, three of them `null`, 50% full — `EXPAND_FACTOR = 2`
  in the flesh.
- Non-colliding elements sit *at* their home slot. No rehashing, no spreading.
- **The collision resolved.** `Fixed("B", 7)` reports home slot 1 but sits in slot
  2. Slot 1 was taken by `A`, so `probe` stepped once and returned `-(2 + 1) == -3`;
  the constructor wrote to `-(-3 + 1) == 2`. `contains(B)` still finds it because
  lookup runs the identical walk. `contains(Fixed("Z", 1))` walks home slot 1 (A,
  no match) → 2 (B, no match) → 3 (`null`) → absent, returning `-4`.
- `MapN` for 3 pairs: `table.length == 12 == 4n`, 6 pair slots, same 0.5 load in
  pair terms. Keys land only on even indices; each value sits one cell after its
  key.
- Run it twice: byte-identical. Placement is deterministic because `probe` has no
  salt.

> **Definition.** `SetN` and `MapN` store their contents in a single flat array of
> `EXPAND_FACTOR * n` slots (`EXPAND_FACTOR == 2`, so at most half full), resolving
> hash collisions by open addressing with linear probing rather than chaining;
> `probe` returns the occupied slot `i` on a hit and `-(i + 1)` for the first free
> slot on a miss, and the guaranteed-free slot — which exists only because the load
> factor is capped at 0.5 — is what makes the unbounded probe loop terminate and
> what lets `null` mean "absent" with no tombstones, since an immutable collection
> never deletes.

---

## Pitfalls

### Believing `EXPAND_FACTOR` is a memory/speed tuning knob

**Wrong**

```java
// "Set.of wastes 2n slots. If EXPAND_FACTOR were 1 it would be half the memory
//  and only a bit slower on collisions."
```

**Right**

```java
        private int probe(Object pe) {
            int idx = Math.floorMod(pe.hashCode(), elements.length);
            while (true) {                       // <-- no iteration bound
                E ee = elements[idx];
                if (ee == null) {
                    return -idx - 1;             // only exit on a miss
                } else if (pe.equals(ee)) {
                    return idx;                  // only exit on a hit
                } else if (++idx == elements.length) {
                    idx = 0;
                }
            }
        }
```

`probe` has exactly two exits: an `equals` match, and a `null` slot. At factor 1 the
table is exactly full, so a query for an absent element matches nothing and never
meets a `null` — it wraps and spins forever. Not slower: **hung**. The class doc
requires the slack explicitly at `:900-902` ("strictly larger than the size … so
that at least one null is always present"), repeated for `MapN` at `:1164-1166`.

**Why people believe it:** every other hash table exposes load factor as a tuning
parameter — `HashMap`'s default 0.75 is genuinely a time/space dial, because
chaining degrades gracefully and never fails to terminate. Open addressing without
a bound does not have that property.

### Reading `MapN`'s `table.length` as `2n`

**Wrong**

```java
// "EXPAND_FACTOR is 2, so Map.of with 3 pairs gives a 6-slot table."
```

**Right**

```
MapN: table.length = 12, pair slots = 6, size = 3
```

`:1185` computes `EXPAND_FACTOR * input.length`, and `input` is the **flattened**
`k0, v0, k1, v1, …` array, so `input.length == 2n`. **[NUM]** `len == 4n` cells =
`2n` pair slots holding `n` pairs. The load factor is still 0.5, but only when
measured in pairs. Always state the unit.

**Why people believe it:** the constant is shared with `SetN`, where
`EXPAND_FACTOR * input.length` really is `2n`, and the field is named `table` in
both.

### Mis-remembering `MapN.probe`'s modulus

**Wrong**

```java
int idx = Math.floorMod(pk.hashCode(), table.length);        // wrong
```

**Right**

```java
int idx = Math.floorMod(pk.hashCode(), table.length >> 1) << 1;   // :1328
```

Reduce modulo the number of *pair slots*, then shift left to land on an even cell.
The wrong version would put keys on odd indices half the time — i.e. into value
cells — and `probe`'s `(idx += 2) == table.length` wrap test at `:1336` would step
past the end rather than wrapping, throwing `ArrayIndexOutOfBoundsException`. That
exact-equality test is also why `(len + 1) & ~1` at `:1186` exists even though it is
currently a no-op.

**Why people believe it:** `SetN.probe` at `:1014` really is the plain
`floorMod(hash, elements.length)`, and the two methods are otherwise line-for-line
parallel.

---

## Cheat sheet

| Thing | Value / fact | Source |
|---|---|---|
| `EXPAND_FACTOR` | `2` — reciprocal of load factor, table ≤ 50% full | `:140` |
| Why 2, not 1 | correctness, not tuning: at factor 1 a miss loops forever | `:900-902` |
| `SetN` table size | `EXPAND_FACTOR * n` = `2n` slots | `:920` |
| `MapN` table size | `EXPAND_FACTOR * 2n`, made even = `4n` cells, `2n` pair slots | `:1185-1187` |
| Measured, 3 pairs | `table.length == 12`, pair slots `== 6` | — |
| `(len + 1) & ~1` | dead code today; protects `probe`'s exact-equality wrap test | `:1186`, `:1336` |
| Collision strategy | open addressing, linear probing, stride 1 (`SetN`) / 2 (`MapN`) | `:1021`, `:1336` |
| Chaining / treeify | none. No `Node`, no tree bins, no `O(log n)` fallback | — |
| Tombstones | never needed — immutable, so no deletion | — |
| `probe` hit / miss | `i` / `-(i + 1)`; recover slot with `-(r + 1)` | `:1020`, `:1018` |
| `probe` home slot | `SetN`: `floorMod(h, len)`; `MapN`: `floorMod(h, len>>1) << 1` | `:1014`, `:1328` |
| Hash spreading | none — `floorMod` on a non-power-of-two length already mixes high bits | `:1014` |
| Salt in `probe`? | **No.** Placement and lookup fully deterministic | `:1013-1024`, `:1327-1338` |
| `MapN` layout | one `Object[]`; key at `2i`, value at `2i+1` | `:1174`, `:1199-1200` |
| `MapN.get` | single `probe`, then `table[i+1]` — no second lookup | `:1244` |
| Worst-case lookup | `O(n)` over `2n` slots; average `O(1)` | — |
| Duplicate input | `Set.of` → `IllegalArgumentException`; `Set.copyOf` dedupes | `:925` |
| Odd `MapN` input | `InternalError` — it is a JDK bug, not user error | `:1180-1182` |
| Introduced | Java 9 | — |

---

## Self-test

**Q1.** Why is `EXPAND_FACTOR` 2 rather than 1, and what exactly goes wrong at 1?

<details><summary>Answer</summary>

`SetN`'s table is `EXPAND_FACTOR * n` slots holding exactly `n` elements, so at
factor 2 there are always `n` free slots — at least one for any `n >= 1`. `probe`
(`:1013-1024`) is a `while (true)` loop with no iteration bound whose only exits
are "found an equal element" and "found a `null` slot". At factor 1 the table is
exactly full: probing for an absent element visits every occupied slot, matches
none, wraps, and spins forever. Not an exception — a hang. The class doc states the
requirement at `:900-902`: "The element array must be strictly larger than the size
… so that at least one null is always present." So `EXPAND_FACTOR` is a correctness
requirement, not a tuning constant.

</details>

**Q2.** `probe` returns `-3`. Where does the element go, and what did `-3` tell you?

<details><summary>Answer</summary>

`-3` is negative, so it is a miss, encoded `-(i + 1)`. Solving `-3 = -(i + 1)`
gives `i = 2`: slot 2 is the first free slot along the probe run from the home slot.
The constructor writes `elements[-(idx + 1)] = e` (`:927`), i.e. `elements[2] = e`.
The encoding is its own inverse. Zero is unambiguous because a hit at slot 0 returns
`0` and a miss at slot 0 returns `-1`. Same convention as `Arrays.binarySearch`.
Confirmed by the transcript: `Fixed("B", 7)` collided at home slot 1 and was written
to slot 2.

</details>

**Q3.** `MapN` for 5 pairs: how long is `table`, and where does a key's value live?

<details><summary>Answer</summary>

`input.length == 10` (flattened), so `len = EXPAND_FACTOR * 10 == 20`, then
`(20 + 1) & ~1 == 20` (`:1185-1186`): 20 cells = 10 pair slots holding 5 pairs,
load 0.5 in pair terms. Keys occupy only even indices; a key's cell is
`floorMod(k.hashCode(), 10) << 1` plus linear probing by 2 on collision. Its value
is always in the immediately following cell, `key_index + 1` — which is what lets
`get` return `table[i+1]` from a single `probe` (`:1244`). There is no positional
"third key": placement is by hash, not by argument order.

</details>

**Q4.** Write `MapN.probe`'s home-index expression from memory. Why is it not
`floorMod(hash, table.length)`?

<details><summary>Answer</summary>

`Math.floorMod(pk.hashCode(), table.length >> 1) << 1` (`:1328`). Reduce modulo the
number of *pair slots* (`table.length >> 1`), then shift left by one to land on an
even cell — the cell that holds a key.

`floorMod(hash, table.length)` would return odd indices half the time, pointing at
*value* cells, so `table[idx]` would compare a value against a key. It would also
break the wrap test `(idx += 2) == table.length` at `:1336`, which relies on `idx`
being even so it hits `table.length` exactly rather than stepping past it into an
`ArrayIndexOutOfBoundsException`. That evenness invariant is also why
`len = (len + 1) & ~1` exists at `:1186`, even though with `EXPAND_FACTOR == 2` the
product is always even already and the line is currently dead code.

</details>

**Q5.** Why is open addressing right here when `HashMap` uses chaining?

<details><summary>Answer</summary>

Three reasons, one of which is the real one. **Memory:** chaining needs a `Node` per
entry — header + `hash` + `key` + `value` + `next`, ~32 bytes with compressed oops —
on top of the bucket array; `SetN` needs one array of `2n` references and no
per-element object. **Locality:** linear probing with stride 1 reads consecutive
cells, usually the same cache line, versus a pointer chase through `Node.next`.
**The actual enabler:** open addressing's usual disqualifier is deletion, which
forces tombstone markers to keep probe runs intact, and tombstones then accumulate
and require rehashing. `SetN` cannot delete — every mutator on
`AbstractImmutableCollection` throws `UnsupportedOperationException` — so `null`
unambiguously means "end of probe run" and the whole tombstone apparatus disappears.
Immutability makes the simple thing correct. Costs: `2n` slots is real memory at
large `n`, worst-case lookup is `O(n)` with no treeify escape hatch, and iteration
order is unstable.

</details>

**Q6.** `SetN.probe` does no hash spreading — no `h ^ (h >>> 16)`. Why does
`HashMap` need it and `SetN` not?

<details><summary>Answer</summary>

`HashMap` indexes with `(n - 1) & h` where `n` is a power of two, so the index is
built from the **low bits of the hash only**; a hash function whose entropy lives in
the high bits would collide catastrophically, hence the `spread` step that XORs the
high half down. `SetN` indexes with `Math.floorMod(h, elements.length)` (`:1014`),
where `elements.length` is `2n` and generally *not* a power of two, so the modulus
already involves the whole hash value. `floorMod` rather than `%` because
`hashCode()` may be negative and `%` would yield a negative index. `MapN` does the
same over pair slots (`:1328`).

</details>

**Q7.** Two runs of the reflective table dump — same or different?

<details><summary>Answer</summary>

Byte-identical. `SetN.probe` (`:1014`) and `MapN.probe` (`:1328`) contain no
`SALT32L` term, so home slots and probe walks are a pure function of `hashCode()`
and the table length, both of which are fixed. The salt affects only iterator start
index and direction (`:958`, `:974`, `:1270`, `:1280`), which is `04b2`'s subject.
This is the practical dividing line: `contains`/`get` are reproducible across JVM
runs; iteration order is not.

</details>

---

**Leaves covered:** 3.12.6–3.12.8 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-119, D-120
**Target version:** Java 21 LTS
**Lines:** 690
