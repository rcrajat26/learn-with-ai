# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.4.6)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/03-immutability-tiers.md](03-immutability-tiers.md) · Next: [immutable-collections/03b-immutability-tiers-b-factory-rules.md](03b-immutability-tiers-b-factory-rules.md)

The five-rung ladder and the source proof for each rung are in
[03-immutability-tiers.md](03-immutability-tiers.md); this file tabulates it and proves
every cell by running it.

---

## The seven-column capability table

### Mental model

The table below is not a memory aid — it is the *definition* of the ladder, since the rungs
have no distinguishing type. `List<String> xs` tells you nothing; only the runtime object
does. Every cell was produced by a program that tried the operation and reported what
happened, not by reading javadoc.

### Why the table exists rather than a rule of thumb

The obvious rule of thumb — "`of` means immutable, `unmodifiable` means immutable, `new`
means mutable" — is wrong in three separate places at once. `EnumSet.of` is mutable.
`Collections.unmodifiableList` is a live view of something mutable. `Arrays.asList` permits
`set` but not `add`. Any mental shortcut short of the full matrix will mislead you on at
least one of those, which is why the leaf asks for seven explicit columns rather than a
sentence.

### When you actually need each column

- **null allowed** decides whether a factory can accept data from a database row or a
  parsed JSON document, where absent fields arrive as `null`.
- **duplicate args allowed** decides whether a `static final` `Set.of(...)` constant can
  blow up at class-init time.
- **`set` / `add` allowed** decide whether library code can normalise your collection in
  place.
- **reflects source changes** is the one that causes production bugs, because it is
  invisible at the call site.
- **serializable** matters at any RPC, cache or session boundary.
- **iteration order stable across JVM runs** decides whether a test that asserts on
  `toString()` is flaky.

### The harness

The `Ladder` program in [03-immutability-tiers.md](03-immutability-tiers.md) fills the
`set` / `add` / null / reflects-source columns. This one fills the remaining three —
duplicate arguments and serialization:

```java
import java.io.*;
import java.util.*;

public class Probe {
    interface Attempt { Object run() throws Exception; }

    static String attempt(String label, Attempt a) {
        try {
            return label + "=OK(" + a.run() + ")";
        } catch (Throwable t) {
            return label + "=" + t.getClass().getSimpleName()
                 + (t.getMessage() == null ? "" : "(" + t.getMessage() + ")");
        }
    }

    static String serial(Object o) {
        return attempt("serial", () -> {
            var bos = new ByteArrayOutputStream();
            try (var oos = new ObjectOutputStream(bos)) {
                oos.writeObject(o);
            }
            try (var ois = new ObjectInputStream(new ByteArrayInputStream(bos.toByteArray()))) {
                return ois.readObject().getClass().getSimpleName();
            }
        });
    }

    public static void main(String[] args) {
        System.out.println(attempt("Set.of dup   ", () -> Set.of("A", "A")));
        System.out.println(attempt("Map.of dupKey", () -> Map.of("A", 1, "A", 2)));
        System.out.println(attempt("List.of dup  ", () -> List.of("A", "A")));
        System.out.println("Map.of        " + serial(Map.of("A", 1)));
        System.out.println("Map.keySet    " + serial(Map.of("A", 1).keySet()));
        System.out.println("List.of       " + serial(List.of("A", "B", "C")));
        System.out.println("nCopies       " + serial(Collections.nCopies(3, "A")));
        System.out.println("unmod(good)   " + serial(
                Collections.unmodifiableList(new ArrayList<>(List.of("A")))));
        System.out.println("unmod(bad)    " + serial(Collections.unmodifiableList(
                new AbstractList<String>() {
                    public String get(int i) { return "A"; }
                    public int size() { return 1; }
                })));
    }
}
```

Every attempt sits inside `try`/`catch`, so the whole program runs to completion even
though most attempts throw. Real output — JDK 21.0.7, HotSpot 64-Bit Server VM,
macOS/aarch64:

```
Set.of dup   =IllegalArgumentException(duplicate element: A)
Map.of dupKey=IllegalArgumentException(duplicate key: A)
List.of dup  =OK([A, A])
Map.of        serial=OK(Map1)
Map.keySet    serial=NotSerializableException(java.util.AbstractMap$1)
List.of       serial=OK(ListN)
nCopies       serial=OK(CopiesList)
unmod(good)   serial=OK(UnmodifiableRandomAccessList)
unmod(bad)    serial=NotSerializableException(Probe$1)
```

### The table

Every cell below traces to a line of that transcript or of the `Ladder` run in
[03-immutability-tiers.md](03-immutability-tiers.md). "n/a" means the operation does not
exist on the type.

| Factory | Rung | null allowed? | duplicate *args* allowed? | `set` allowed? | `add` allowed? | reflects source changes? | serializable? | iteration order stable across JVM runs? |
|---|---|---|---|---|---|---|---|---|
| `new ArrayList<>(c)` | 0 | yes | yes | yes | yes | no (constructor copies) | yes | yes (insertion order) |
| `Arrays.asList(a)` | 1a | yes | yes | **yes** (writes the array) | no — UOE | **yes** — via the array, both directions | yes | yes (array order) |
| `Collections.nCopies(n, x)` | 1b | yes | yes (all elements identical) | **no** — UOE | no — UOE | no source | yes | yes (all equal) |
| `Collections.unmodifiableList(c)` | 2 | yes | yes | no — UOE | no — UOE | **yes** | only if `c` is | follows `c` |
| `List.copyOf(c)` | 3 | **no** — NPE | yes | no — UOE | no — UOE | no (snapshot) | yes (via `CollSer`) | yes (source order) |
| `List.of(...)` | 4 | **no** — NPE | yes | no — UOE | no — UOE | no source | yes (via `CollSer`) | yes (argument order) |
| `Set.of(...)` | 4 | **no** — NPE | **no** — IAE | n/a | no — UOE | no source | yes (via `CollSer`) | **no** |
| `Map.of(...)` | 4 | **no** — NPE (key *and* value) | **no** — IAE on dup key | n/a | no — UOE (`put`) | no source | yes (via `CollSer`); `keySet()` is **not** | **no** |
| `EnumSet.of(...)` | **0** | **no** — NPE | yes (silently collapsed) | n/a | **yes** | no source | yes (`SerializationProxy`) | yes (ordinal order) |

Cells worth arguing about:

- **`Arrays.asList` "reflects source changes" = yes.** The array *is* the source, and the
  traffic runs both ways. Verified: `view.set(0, "ZZ")` leaves the array `[ZZ, B, C]`, and
  `arr[1] = "YY"` leaves the list `[ZZ, YY, C]`.
- **`Map.of(...).keySet()` is not serializable** even though the map is. `Map.of` returns
  `ImmutableCollections$Map1`/`MapN`, whose `keySet()` is the anonymous class
  `java.util.AbstractMap$1` inherited from `AbstractMap` — no `Serializable`. Passing a
  key-set across a serialization boundary throws `NotSerializableException`. Wrap in
  `Set.copyOf(map.keySet())` first. The syllabus does not mention this; the transcript
  above proves it.
- **`Collections.unmodifiableList` serializability is conditional.** The wrapper declares
  `implements Serializable`, but its `c` field is typed `Collection<? extends E>` and
  carries `@SuppressWarnings("serial")` (`Collections.java:1056`). Serializing a wrapper
  over an `ArrayList` works; over a non-serializable `AbstractList` it throws.
- **Duplicate *arguments*.** The column asks about the arguments you pass to the factory,
  not about whether the resulting collection can hold duplicates — a `Set` never can. The
  mechanism behind `Set.of`'s `IllegalArgumentException` is leaf 2.4.7, in
  [03b-immutability-tiers-b-factory-rules.md](03b-immutability-tiers-b-factory-rules.md).
- **`EnumSet.of` with duplicate arguments does not throw.** `EnumSet.of(MON, MON)` returns
  `[MON]`. Same `of` naming as `Set.of`, opposite behaviour. Full treatment in
  [03-immutability-tiers.md](03-immutability-tiers.md).

### [PROVE] The "reflects source changes" column, and why `copyOf` earns its `no`

`List.copyOf` gets `no` in that column, but the mechanism is subtler than "it copies":

```java
// ImmutableCollections.java:168-176
static <E> List<E> listCopy(Collection<? extends E> coll) {
    if (coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)) {
        return (List<E>)coll;
    } else if (coll.isEmpty()) { // implicit nullcheck of coll
        return List.of();
    } else {
        return (List<E>)List.of(coll.toArray());
    }
}
```

Line 169: if the argument is already a `List12` or a null-free `ListN`, **return it
unchanged** — no copy at all. Line 171: an empty input collapses to the shared `EMPTY_LIST`
singleton. Line 174: only otherwise does it snapshot via `toArray()` into a fresh `ListN`.

The column is still honestly `no`, because in every branch the result cannot reflect later
source changes: branches 1 and 2 return objects that are already immutable, and branch 3
takes a real snapshot. But leaf 2.4.4's phrase "unmodifiable independent copy" describes
the *guarantee*, not the *mechanism* — `List.copyOf(x) == x` is often true. Verified:

```
List.copyOf(List.of(...)) same instance = true
List.copyOf(ArrayList) same instance = false
List.copyOf(unmodifiableList) same instance = false
```

The third line is the interesting one: a `Collections.unmodifiableList` wrapper is *not*
recognised by line 169, so `List.copyOf` of one does snapshot — which is exactly the
upgrade path from rung 2 to rung 3.

### [PROVE] Why the last column is `false` for `Set.of` and `Map.of`

`ImmutableCollections` computes a per-JVM salt in a static initialiser:

```java
// ImmutableCollections.java:74-86
long color = 0x243F_6A88_85A3_08D3L; // slice of pi
long seed = CDS.getRandomSeedForDumping();
if (seed == 0) {
  seed = System.nanoTime();
}
SALT32L = (int)((color * seed) >> 16) & 0xFFFF_FFFFL;
// use the lowest bit to determine if we should reverse iteration
REVERSE = (SALT32L & 1) == 0;
```

`color` is a fixed 64-bit constant (a slice of pi, per the JDK's own comment at line 68).
`seed` is `System.nanoTime()` in a normal run — so different on every JVM start. The
product's middle 32 bits become `SALT32L`, masked into `[0, 2^32-1]`. `REVERSE` is its
lowest bit, so **[NUM] the iteration direction flips with probability 0.5 per JVM start**.
The salt then picks a starting offset for the iterator:

```java
// ImmutableCollections.java:957-958
// randomly based on SALT32L
idx = (int) ((SALT32L * elements.length) >>> 32);
```

The comment at lines 71-73 explains the trick: because `SALT32L` is in `[0, 2^32-1]`, the
product shifted right 32 bits lands in `[0, length-1]` with no division.

**The salt touches iteration only.** Lookup is unsalted:

```java
// ImmutableCollections.java:1013-1014
private int probe(Object pe) {
    int idx = Math.floorMod(pe.hashCode(), elements.length);
```

Plain `floorMod` of the element's `hashCode` — no `SALT32L` anywhere in the expression. So
`contains` and `get` return identical answers in every JVM; only the order you *walk* the
collection varies. Do not overstate this as "randomized hashing" — it is randomized
iteration.

Two separate JVMs, same class file, JDK 21.0.7 macOS/aarch64, `-Xshare:off`:

```
$ java -Xshare:off -cp out OrderRun
List.of  = [A, B, C, D, E, F, G, H]
Set.of   = [A, B, C, D, E, F, G, H]
Map.of   = {A=1, B=2, C=3, D=4, E=5, F=6}
lookups  = true 5

$ java -Xshare:off -cp out OrderRun
List.of  = [A, B, C, D, E, F, G, H]
Set.of   = [H, G, F, E, D, C, B, A]
Map.of   = {C=3, B=2, A=1, F=6, E=5, D=4}
lookups  = true 5
```

`List.of` is identical across both runs — lists have no salt, because a list's order is its
contract. `Set.of` reversed and `Map.of` rotated. `lookups` is byte-identical across both
runs, confirming `probe()` is unsalted. `-Xshare:off` is used because with CDS enabled
`CDS.getRandomSeedForDumping()` can supply a build-derived seed (lines 76-80) to keep
archives reproducible, which would mask the effect.

**Insight:** this is deliberate. The JDK randomizes iteration order so that code cannot
accidentally depend on it, the same reasoning behind Python's hash randomization. If your
test asserts on `Set.of(...).toString()`, it passes locally and fails in CI roughly half
the time.

**Interview:** "Does `Set.of` randomize hashing?" — No. It randomizes *iteration* via
`SALT32L`/`REVERSE`, computed once per JVM from `System.nanoTime()`. Bucket placement uses
unsalted `Math.floorMod(hashCode, length)`, so lookups are fully deterministic.

> **Definition.** The seven-column table is the operational specification of the ladder:
> the rung of a collection is fully determined by which of `null`, duplicate arguments,
> `set`, `add`, source-reflection, serialization, and stable iteration order it supports —
> none of which is visible in its declared type.

---

## Pitfalls

### Asserting on `Set.of` iteration order in a test

**Wrong**

```java
assertEquals("[A, B, C]", Set.of("A", "B", "C").toString());
// passes on your laptop, fails in CI about half the time
```

**Right**

```java
Set<String> actual = Set.of("A", "B", "C");
assertEquals(Set.of("A", "B", "C"), actual);                              // order-insensitive
assertEquals(List.of("A", "B", "C"), actual.stream().sorted().toList());  // or impose one
```

**Why people believe it:** small `Set.of` calls very often *do* iterate in argument order,
so the first ten runs agree. `REVERSE` flips on a 50/50 coin at class-init
(`ImmutableCollections.java:86`), so the failure is genuinely intermittent.

### Sending `Map.of(...).keySet()` across a serialization boundary

**Wrong**

```java
import java.io.*;
import java.util.*;

public class KeySetWire {
    public static void main(String[] args) {
        Map<String, Integer> m = Map.of("a", 1);
        try {
            new ObjectOutputStream(new ByteArrayOutputStream()).writeObject(m.keySet());
        } catch (Exception e) {
            System.out.println("keySet -> " + e);
            // keySet -> java.io.NotSerializableException: java.util.AbstractMap$1
        }
    }
}
```

**Right**

```java
Map<String, Integer> m = Map.of("a", 1);
Set<String> wireSafe = Set.copyOf(m.keySet());   // ImmutableCollections$Set12, serializable
// or just send m itself — Map1/MapN serialize via the CollSer proxy
```

**Why people believe it:** the map is serializable, and `keySet()` looks like part of it.
It is not — `MapN` inherits `keySet()` from `AbstractMap`, which returns an anonymous inner
class (`java.util.AbstractMap$1`) that never declares `Serializable`.

### Assuming `Collections.unmodifiableList` is unconditionally serializable

**Wrong**

```java
List<String> odd = new AbstractList<>() {          // not Serializable
    public String get(int i) { return "A"; }
    public int size() { return 1; }
};
List<String> wrapped = Collections.unmodifiableList(odd);
// wrapped.getClass() implements Serializable, so this "must" work
// -> NotSerializableException on the BACKING list, not the wrapper
```

**Right**

```java
List<String> safe = List.copyOf(odd);   // rung 4 ListN — always serializable via CollSer
```

**Why people believe it:** `UnmodifiableList` really does declare `implements Serializable`.
But its `c` field is typed `Collection<? extends E>` and annotated
`@SuppressWarnings("serial")` (`Collections.java:1056`) — the compiler is being told the
field's runtime type may not be serializable. Serialization follows the reference and
fails there.

---

## Cheat sheet

| Column | Who fails it |
|---|---|
| null allowed | `List/Set/Map.of`, `*.copyOf`, `EnumSet.of` all throw NPE |
| duplicate args allowed | `Set.of` / `Map.of` throw IAE; `List.of` and `EnumSet.of` do not |
| `set` allowed | only rung 0 and `Arrays.asList` |
| `add` allowed | only rung 0 — including `EnumSet.of` |
| reflects source changes | `Collections.unmodifiableX` (one-way), `Arrays.asList` (two-way) |
| serializable | all except `Map.of(...).keySet()` and `unmodifiableX` over non-serializable backing |
| iteration stable across JVMs | all except `Set.of` / `Set.copyOf` / `Map.of` / `Map.copyOf` |
| salt scope | iteration only; `probe()` = unsalted `Math.floorMod(hashCode, length)` |
| `REVERSE` odds | 50/50 per JVM start (`SALT32L & 1`) |
| `List.copyOf(x) == x`? | yes when `x` is `List12` or null-free `ListN`; no for `unmodifiableList` |
| test-safe assertion | compare to a `Set`, or `stream().sorted().toList()` |
| wire-safe key set | `Set.copyOf(map.keySet())` |

---

## Self-test

**Q1.** `Set.of("a","b").contains("b")` — is the answer affected by `SALT32L`?

<details><summary>Answer</summary>

No. `SALT32L` and `REVERSE` are consumed by the iterator to pick a start offset and a
direction (`ImmutableCollections.java:957-958` and `86`). Lookup goes through `probe()`,
which is `Math.floorMod(pe.hashCode(), elements.length)`
(`ImmutableCollections.java:1013-1014`) — no salt in the expression. Iteration order varies
per JVM run; lookup results never do. Verified: two `-Xshare:off` JVMs printed `Set.of` as
`[A..H]` and `[H..A]` respectively, with byte-identical lookup output in both.

</details>

**Q2.** `Map.of("a",1).keySet()` is sent over a socket. What happens?

<details><summary>Answer</summary>

`java.io.NotSerializableException: java.util.AbstractMap$1`. The map itself is serializable
via the `CollSer` proxy, but `keySet()` is inherited from `AbstractMap` and returns an
anonymous inner class that does not implement `Serializable`. Send `Set.copyOf(map.keySet())`
or the map itself.

</details>

**Q3.** Is `List.copyOf` always a copy?

<details><summary>Answer</summary>

No. `ImmutableCollections.listCopy` (lines 168-176) returns the argument unchanged if it is
already a `List12` or a null-free `ListN`, and returns the shared `EMPTY_LIST` for empty
input. Only otherwise does it snapshot via `toArray()`. Verified:
`List.copyOf(List.of(...)) == ` the same instance prints `true`, while
`List.copyOf(new ArrayList<>(...))` and `List.copyOf(Collections.unmodifiableList(...))`
both print `false`. The immutability guarantee holds in every branch, so the table's `no`
in the reflects-source column is correct; the leaf's word "copy" describes the guarantee,
not the mechanism.

</details>

**Q4.** Two entries in the table say "yes" under *reflects source changes*. Which, and how do they differ?

<details><summary>Answer</summary>

`Collections.unmodifiableList(c)` reflects changes to `c` **one way** — every read is
forwarded to the wrapped collection, so the caller sees the owner's mutations but cannot
cause any. `Arrays.asList(a)` reflects changes **both ways** — `list.set(0, x)` writes the
caller's array and `a[0] = y` changes the list, because `Arrays$ArrayList` stores the array
without copying (`Arrays.java:4237-4239`).

</details>

**Q5.** Is `Collections.unmodifiableList(x)` serializable?

<details><summary>Answer</summary>

Only if `x` is. The wrapper class declares `implements Serializable`, but its `c` field is
typed `Collection<? extends E>` and carries `@SuppressWarnings("serial")`
(`Collections.java:1056`) — the compiler is explicitly told the field's runtime type may
not be serializable. Verified: a wrapper over an `ArrayList` round-trips as
`UnmodifiableRandomAccessList`; a wrapper over an anonymous non-serializable `AbstractList`
throws `NotSerializableException` naming the *backing* class.

</details>

**Q6.** Why is `List.of`'s iteration order stable across JVM runs when `Set.of`'s is not?

<details><summary>Answer</summary>

A list's iteration order *is* its contract — index 0 first — so there is nothing to
randomize, and `ListN`'s iterator walks the array directly. A set's order is unspecified by
contract, so the JDK deliberately varies it via `SALT32L`/`REVERSE` to stop callers
depending on it. Verified in the two-run transcript: `List.of` printed identically in both
JVMs, `Set.of` reversed.

</details>

---

**Leaves covered:** 2.4.6 (1 leaf)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 459
