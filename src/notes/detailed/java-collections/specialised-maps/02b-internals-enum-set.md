# 02 Java Collections — Specialised maps and sets — INTERNALS (§3.10.8–3.10.14)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [specialised-maps/02-internals-enum-map-set.md](02-internals-enum-map-set.md) · Next: [specialised-maps/03-identity-and-weak.md](03-identity-and-weak.md)

This file covers `EnumSet` internals (leaves 3.10.8–3.10.12), ordinal dependence as it affects
both `EnumMap` and `EnumSet` (3.10.13), and why an enum-keyed `HashMap` is the worse choice
(3.10.14). `EnumMap`'s own internals — fields, `SharedSecrets`, the `NULL` sentinel, the
`EntryIterator` correction and the memory arithmetic — are in the previous file.

Every source line quoted below is from the JDK 21 sources at
`java.base/java/util/{EnumSet,RegularEnumSet,JumboEnumSet}.java`, cited as `File:line`. Every
`[PROVE]` / `[NUM]` claim is backed by real output from programs compiled and run on this
machine (`javac 21`, HotSpot 21, macOS/aarch64). Two syllabus claims in this range turned out
to be wrong against the source and one turned out not to reproduce at all; each correction is
marked **Correction** at the point of the claim.

## The `EnumSet` hierarchy

| Type | Storage | `size()` cost | Membership cost | Chosen when | Visibility |
|---|---|---|---|---|---|
| `EnumSet<E>` | abstract: `Class elementType` + `Enum[] universe` only | abstract | abstract | never instantiated directly | `public abstract sealed` |
| `RegularEnumSet<E>` | one `long elements` | `Long.bitCount` — recomputed | one shift + AND | `universe.length <= 64` | package-private `final` |
| `JumboEnumSet<E>` | `long[] elements` + cached `int size` | field read | one array read + shift + AND | `universe.length > 64` | package-private `final` |

The superclass holds exactly two fields, `EnumSet.java:91` and `:96`:

```java
    final transient Class<E> elementType;    // :91  which enum this set is over
    final transient Enum<?>[] universe;      // :96  "All of the values comprising E.  (Cached for performance.)"
```

Both are `transient`, so serialization goes through a proxy rather than the fields; both are
`final`, so an `EnumSet` can never change which enum type it is over. `universe` comes from the
same uncloned shared array `EnumMap` uses — `EnumSet.java:408-409` is
`SharedSecrets.getJavaLangAccess().getEnumConstantsShared(elementType)`, so creating an
`EnumSet` copies zero constant references no matter how large the enum.

`EnumSet` itself is abstract and, since Java 17, **sealed** — `EnumSet.java:81-82`:

```java
public abstract sealed class EnumSet<E extends Enum<E>> extends AbstractSet<E>
    implements Cloneable, java.io.Serializable permits JumboEnumSet, RegularEnumSet
```

Before Java 17 it was a plain `abstract class` whose two subclasses happened to be
package-private, which made "you cannot subclass `EnumSet`" a convention enforced only by
access control. Since 17 it is enforced by the language: the `permits` clause is closed, so no
third implementation can ever exist, and the two package-private abstract hooks `addAll()`
(`:143`) and `complement()` (`:393`) can never be implemented by a third party — which is
exactly why the public factories can safely call them. Version note: asked "could I write
`MyEnumSet extends EnumSet`?", the answer on Java 8–16 is "not from outside `java.util`", and
on Java 17+ it is "not at all".

---

## `EnumSet` is a bit vector with a type check

### Mental model

A single 64-bit register where bit *k* means "constant *k* is present". Union is `|`.
Intersection is `&`. Difference is `& ~`. Complement is `~` followed by clearing the bits above
the universe. Set algebra becomes machine arithmetic, and the collection is one field.

### Why it exists, and the sibling to beat

`HashSet<Day>` costs a `HashMap` plus a `Node` per element and a hash per lookup. For a domain
with at most 64 members and a dense integer identity, all of that is avoidable. The prior art
is an `int` or `long` used as a flag word with hand-written `1 << CONSTANT` — the C idiom that
`EnumSet`'s javadoc explicitly offers to replace, with the type safety and `Set` API restored.

Reach for `EnumSet` for any set of enum constants. Do **not** reach for it when you need a
`null` element, a mixture of enum types, or safe concurrent mutation — `EnumSet` is
unsynchronized and its bit fields are plain (non-volatile), so `Collections.synchronizedSet`,
an `AtomicLong` bitmask, or an immutable-and-replace pattern are the alternatives.

### Implementation choice `[SOURCE]` `[RESEARCH]` — `EnumSet.java:112-121`

```java
    public static <E extends Enum<E>> EnumSet<E> noneOf(Class<E> elementType) {
        Enum<?>[] universe = getUniverse(elementType);   // :113 SharedSecrets again, uncloned
        if (universe == null)
            throw new ClassCastException(elementType + " not an enum");   // :115

        if (universe.length <= 64)                       // :117
            return new RegularEnumSet<>(elementType, universe);   // :118
        else
            return new JumboEnumSet<>(elementType, universe);      // :120
    }
```

`<= 64`, evaluated once at creation, on the count of declared constants — not on the set's
size. Every other factory funnels through here: `allOf` is `noneOf` + `addAll()` (`:133-137`),
`of(e)` is `noneOf` + `add` (`:217-221`), `complementOf` is `copyOf` + `complement()` (`:197-201`).
The two `abstract` hooks that make that work are `addAll()` (`:143`) and `complement()` (`:393`)
— package-private, no-argument, mutate-in-place methods that exist purely so the public
factories can be written once in the superclass.

`[PROVE]` The boundary, with enums of exactly 5, 64 and 65 constants:

```
=== 8. EnumSet implementation choice at the 64/65 boundary ===
Day (5 constants)     -> RegularEnumSet
Big (64 constants)    -> RegularEnumSet
Jumbo (65 constants)  -> JumboEnumSet
```

Note what this does **not** mean: a 65-constant enum does not make `EnumSet` unusable or slow,
and there is no 64-element ceiling on set *size*. The threshold picks a representation, nothing
more, and it is fixed for the lifetime of the set the moment it is created.

### `RegularEnumSet` `[SOURCE]` `[PROVE]` — `RegularEnumSet.java`

```java
final class RegularEnumSet<E extends Enum<E>> extends EnumSet<E> {   // :36
    private long elements = 0L;                                      // :43
```

One `long`. `size()` is `Long.bitCount(elements)` (`:123`) — a single `POPCNT`-class instruction
on any modern CPU, computed on demand rather than cached, because it is cheap enough not to be
worth a field. `isEmpty()` is `elements == 0` (`:132`).

`contains` (`:141-149`):

```java
    public boolean contains(Object e) {
        if (e == null)
            return false;                                              // :143 null is never a member
        Class<?> eClass = e.getClass();
        if (eClass != elementType && eClass.getSuperclass() != elementType)
            return false;                                              // :146 wrong enum type -> absent, not an error
        return (elements & (1L << ((Enum<?>)e).ordinal())) != 0;        // :148
    }
```

The `getSuperclass()` clause covers constants with bodies (`MON { ... }` is an instance of an
anonymous subclass of the enum). `add` (`:161-167`) is `elements |= (1L << ordinal)` with a
before/after comparison to produce the `boolean` return; `remove` (`:175-185`) is
`elements &= ~(1L << ordinal)`. Note that `1L << ordinal` needs no masking of the shift
distance because the universe is already known to be `<= 64`.

Working the membership arithmetic through by hand for `EnumSet.of(MON, WED, FRI)` over
`Day { MON, TUE, WED, THU, FRI }`: ordinals 0, 2, 4, so
`elements = (1<<0) | (1<<2) | (1<<4) = 1 + 4 + 16 = 21 = 0b10101`. Reading the private field
reflectively confirms it:

```
=== 9. RegularEnumSet: the single long, read out of the object ===
EnumSet.of(MON,WED,FRI) elements = 21  = 0b10101
expected 1<<0 | 1<<2 | 1<<4      = 21
size() == Long.bitCount(elements)= true
contains(WED) hand-computed      = true
```

The iterator (`:79-115`) is worth reading for the bit trick: `unseen = elements` at
construction (a snapshot, hence "will never throw `ConcurrentModificationException`", `:69-71`),
then `next()` does `lastReturned = unseen & -unseen` (`:104`) to isolate the lowest set bit,
`unseen -= lastReturned` (`:105`) to clear it, and
`universe[Long.numberOfTrailingZeros(lastReturned)]` (`:106`) to convert bit to constant.
Iteration is therefore O(size), not O(universe) — the opposite of `EnumMap`'s iterator, which
scans one slot per constant.

**Tradeoff, not fact:** membership is one AND and iteration is O(size), **but** the whole
structure is a snapshot-iterating, non-thread-safe mutable `long`, **and** every bulk operation
silently falls back to the generic `AbstractSet` path the moment the argument is not an
`EnumSet` (`:218`, `:243`, `:263`, `:200`) — which is precisely why passing a `List` where an
`EnumSet` was expected quietly turns a one-instruction union into an element-by-element loop.

### `addAll` is one OR `[SOURCE]` `[PROVE]` — `RegularEnumSet.java:216-231`

```java
    public boolean addAll(Collection<? extends E> c) {
        if (!(c instanceof RegularEnumSet<?> es))
            return super.addAll(c);                        // :218 fall back to element-by-element
        if (es.elementType != elementType) {
            if (es.isEmpty())
                return false;                              // :222 empty foreign set: no-op
            else
                throw new ClassCastException(
                    es.elementType + " != " + elementType); // :224-225
        }
        long oldElements = elements;
        elements |= es.elements;                           // :229  <-- the whole union
        return elements != oldElements;                    // :230
    }
```

The structural argument, which is what the "one instruction" claim actually means: after the
`instanceof` pattern guard and the type comparison, the body that performs the union is a
single `|=` on a primitive `long`. There is no loop, so the work does **not** scale with either
set's size. A 32-element union with a 32-element set costs exactly as much as a 1-element union
with a 1-element set: `getfield`, `lor`, `putfield`. That is a claim about the source and the
generated bytecode shape, not a timing claim, and no benchmark is offered for it here.
`removeAll` is `elements &= ~es.elements` (`:249`), `retainAll` is `elements &= es.elements`
(`:272`), `containsAll` is `(es.elements & ~elements) == 0` (`:205`), `equals` is
`es.elements == elements` (`:298`) — the entire bulk API is five bit expressions.

```
=== 10. addAll(EnumSet) is one OR: elements |= es.elements ===
u1    = 0000000000000000000000000000000011111111111111111111111111111111
u2    = 0000000000000000111111111111111111111111111111110000000000000000
union = 0000000000000000111111111111111111111111111111111111111111111111
bu == (b1 | b2) ? true   sizes: 32 + 32 -> 48
```

The type-mismatch handling is deliberately **asymmetric** across the bulk operations, and this
is a favourite interview detail:

| Operation | Foreign-`elementType` behaviour | Source line | Rationale |
|---|---|---|---|
| `addAll` | throws `ClassCastException` (unless the other set is empty) | `:220-226` | adding foreign elements would corrupt the set |
| `removeAll` | returns `false`, no change | `:245-246` | nothing to remove — a foreign set shares no members |
| `retainAll` | clears this set, returns whether it changed | `:265-269` | intersection with a disjoint set is empty |
| `containsAll` | returns `es.isEmpty()` | `:202-203` | vacuously true only for the empty set |
| `equals` | `elements == 0 && es.elements == 0` | `:296-297` | two empty sets of different types are equal |

`[PROVE]` all five, driven through raw types to defeat generics. The throwing call is inside a
try/catch so the program runs to completion:

```
=== 14. type-mismatch asymmetry in RegularEnumSet bulk ops ===
removeAll(other type)  = false, days = [MON, TUE]
containsAll(other type)= false
addAll(other type)     threw ClassCastException: class Proofs$Big != class Proofs$Day
retainAll(other type)  = true, days = []
```

### `complement` and the `>>> -n` trick `[SOURCE]`

**Correction:** the syllabus states `complementOf` = `~elements & mask`. There is no field
named `mask` anywhere in `RegularEnumSet`. The mask is recomputed inline from
`universe.length`. `RegularEnumSet.java:53-63`:

```java
    void addAll() {
        if (universe.length != 0)
            elements = -1L >>> -universe.length;           // :55
    }

    void complement() {
        if (universe.length != 0) {                        // :59
            elements = ~elements;                          // :60
            elements &= -1L >>> -universe.length;  // Mask unused bits   :61
        }
    }
```

`-1L` is all 64 bits set. `>>>` is unsigned right shift. Why does a *negative* shift distance
work? Because JLS §15.19 specifies that for a `long` left operand, only the **low six bits** of
the right operand are used — the distance is taken mod 64. For `universe.length == 5`,
`-5` in two's complement is `...11111011`; its low six bits are `111011` = 59; so
`-1L >>> -5` is `-1L >>> 59` = 31 = `0b11111` — exactly five low bits set, one per constant.
The `universe.length != 0` guard exists precisely because `-0 == 0` and `-1L >>> 0` is `-1L`,
which would set all 64 bits for an enum with no constants.

Working the complement of `{MON, WED, FRI}` through by hand: `~21` is
`...1111101010`; `& 31` keeps the low five bits, `0b01010` = 10 = `(1<<1) | (1<<3)` = `{TUE, THU}`.

```
=== 11. complement(): ~elements then mask with -1L >>> -universe.length ===
mask  -1L >>> -5   = 31 = 0b11111
-1L >>> 59 equal?  = true
~bits              = 0b1111111111111111111111111111111111111111111111111111111111101010
~bits & mask       = 10
actual complement  = 10 -> [TUE, THU]
allOf mask         = 31
```

`EnumSet.complementOf` (`EnumSet.java:197-201`) is just `copyOf(s)` then `result.complement()`,
which is why complementing is O(1) for a regular set: clone the object, flip one `long`, mask.

Supporting fact — `addRange` (`RegularEnumSet.java:49-51`) is the same family of trick:
`elements = (-1L >>> (from.ordinal() - to.ordinal() - 1)) << from.ordinal()`. The right-shift
distance is `-(count)` mod 64 where `count = to - from + 1`, producing `count` low bits; the
left shift slides them into place. `EnumSet.range` rejects `from > to` before reaching here.

### `JumboEnumSet` `[SOURCE]` — `JumboEnumSet.java`

```java
final class JumboEnumSet<E extends Enum<E>> extends EnumSet<E> {   // :36
    private long elements[];        // :45 "The ith bit of the jth element ... represents universe[64*j + i]"
    // Redundant - maintained for performance
    private int size = 0;           // :48

    JumboEnumSet(Class<E>elementType, Enum<?>[] universe) {
        super(elementType, universe);
        elements = new long[(universe.length + 63) >>> 6];   // :52 ceil(length / 64)
    }
```

Two differences from the regular case, both forced by the array. First, `size` is a **cached
field** (`:48`, returned directly at `:163`) rather than a recomputed `bitCount`, because
summing `Long.bitCount` over every word would make `size()` O(words); the comment calls it
"Redundant - maintained for performance", and every mutator has to keep it in step, which is
why `JumboEnumSet`'s bulk methods are visibly longer. Second, an ordinal is split: word index
is `ordinal >>> 6`, bit index is `ordinal & 63`. `contains` (`:189`) is
`(elements[eOrdinal >>> 6] & (1L << eOrdinal)) != 0` — note it does **not** mask the shift
distance either, relying on the same mod-64 rule so that `1L << 70` is `1L << 6`.

The bulk ops become word loops: `addAll` is `for (...) elements[i] |= es.elements[i];` (`:284`),
`removeAll` is `elements[i] &= ~es.elements[i]` (`:304`), `retainAll` is `&=` (`:327`),
`complement` flips every word then masks only the last (`:78-81`):

```java
    void complement() {
        for (int i = 0; i < elements.length; i++)
            elements[i] = ~elements[i];                             // :80
        elements[elements.length - 1] &= (-1L >>> -universe.length); // :81 same trick, last word only
    }
```

So the "one instruction" property degrades to "one instruction per 64 constants" — still
`ceil(N/64)` operations for an arbitrarily large union, versus O(size) hashing for a `HashSet`.

```
=== 12. JumboEnumSet: long[] words + cached size ===
words.length       = 2   ((65 + 63) >>> 6) = 2
words[0]           = 0b1000000000000000000000000000000000000000000000000000000000000001
words[1]           = 0b1
cached size field  = 3, size() = 3
C64 word index     = 1, bit = 0
```

`[NUM]` The word arithmetic, shown: for a 65-constant enum, `(65 + 63) >>> 6 = 128 >>> 6 = 2`
words — 16 bytes of payload plus a 16-byte array header, 32 bytes, versus a 65-`Node` `HashSet`.
`Jumbo.C64` has ordinal 64, so word `64 >>> 6 = 1` and bit `64 & 63 = 0`: the lone set bit in
`words[1]`, exactly as printed. `Jumbo.C63` has ordinal 63, so word 0, bit 63 — the top bit of
`words[0]`, also as printed.

> **Definition.** `EnumSet` is an abstract, sealed `Set` over one enum type, realised as
> `RegularEnumSet`'s single `long` bit vector for universes of at most 64 constants and
> `JumboEnumSet`'s `long[]` plus cached size above that, so that membership is one mask test and
> every bulk set operation is a bitwise operation per 64 constants.

---

## Ordinal dependence `[TRAP]`

Supporting fact, but a load-bearing one. Everything above — `vals[key.ordinal()]` in `EnumMap`,
`1L << e.ordinal()` in `RegularEnumSet`, `ordinal >>> 6` in `JumboEnumSet`, the order the
iterators walk, and the range `EnumSet.range(A, B)` denotes — is a function of `ordinal()`, and
`ordinal()` is assigned by the compiler from source declaration order. So editing the order of
constants in an enum silently changes:

- `EnumMap` and `EnumSet` iteration order, with no compile error;
- which constants `EnumSet.range(A, B)` covers, and whether it throws at all;
- the meaning of every previously-persisted ordinal, in a database column, a binary wire
  format, a cache key, or a golden test file.

`EnumMap` and `EnumSet` are safe consumers of `ordinal()` because they only ever hold it *in
memory, within one process, alongside the very class file that assigned it*. The bug appears the
moment an ordinal outlives that class file.

**Pitfall:** the wrong belief is that `ordinal()` is a stable identifier because it is public,
`int`-shaped, and the JDK's own enum collections are built on it. The symptom is silent data
corruption with nothing thrown — insert one constant, and every persisted `2` now denotes a
different member, every `EnumSet.range(A, B)` covers a different span, and any test that pinned
iteration order starts asserting the wrong sequence. The fix is to let ordinals live only inside
one process: persist and compare `name()` / `valueOf(String)`, and treat any ordinal that crosses
a process, a wire, or a disk boundary as a bug. The pitfall entry below shows this in code.

---

## Why an enum-keyed `HashMap` is worse

### Mental model

Both maps know exactly where the key goes. `EnumMap` asks the key ("what is your ordinal?")
and gets a compile-time-assigned answer. `HashMap` asks the JVM ("what address-ish number did
you invent for this object?") and gets an answer that has nothing to do with the enum's
declaration — then reduces it modulo a table size to a bucket. The first is a lookup; the
second is a guess that happens to be consistent within one process.

### The mechanism `[PROVE]` `[RESEARCH]`

**Correction:** the syllabus says `java.lang.Enum` "does not override `hashCode()`". Verified
by reflection, it *does* declare one — `public final int hashCode()` — whose body is
`return super.hashCode();`. The distinction matters for one reason: because it is `final`, you
**cannot** give an enum a value-based hash code, so the identity hash is not merely the default,
it is mandatory.

```
=== 13. Enum.hashCode declaration ===
Enum declares hashCode()? yes
modifiers = public final
Day.MON.hashCode() == System.identityHashCode(Day.MON) ? true
```

The identity hash is produced lazily on first request by HotSpot's identity-hash generator and
stashed in the object header. So the per-key cost of `HashMap.get(someEnum)` is: header read,
`h ^ (h >>> 16)` spreading, `& (table.length - 1)` masking, array read, then a `==`-or-`equals`
walk of the bucket. `EnumMap.get` is: `ordinal()` field read, array read. And `HashMap` pays a
`Node` allocation per mapping, which `EnumMap` does not pay at all.

**Pitfall:** the wrong belief is not the usual "enum hash codes are random per run" — it is the
*opposite* one people reach after testing it. Run an enum-keyed `HashMap` twice on default
HotSpot 21 and the iteration order is identical (proven below), so the order looks like a
guarantee and someone commits it to a wire format, a database ordering or a golden test file.
The symptom is that the ordering breaks later for no visible reason: any upstream change that
consumes a different number of identity hashes — a logging framework initialising, a lazily
built cache, a config flag taking a different branch — silently reorders the whole map, and the
diff that caused it never touched the map. The fix is to treat the order as **unspecified**
rather than random: use `EnumMap` when you need declaration order, or `LinkedHashMap` when you
need insertion order, and never let an enum-keyed `HashMap`'s iteration order escape the process.

**The order claim, tested honestly.** The usual phrasing is "identity hash codes vary per run,
so `HashMap` iteration order is irreproducible". Two runs of the same program in two separate
JVMs, default flags:

```
$ java -cp out OrderRun
identityHashCode(TRACE) = 1163157884
HashMap  order = [DEBUG, NOTICE, CRIT, TRACE, EMERG, ERROR, ALERT, INFO, WARN, FATAL]
EnumMap  order = [TRACE, DEBUG, INFO, NOTICE, WARN, ERROR, CRIT, ALERT, EMERG, FATAL]

$ java -cp out OrderRun
identityHashCode(TRACE) = 1163157884
HashMap  order = [DEBUG, NOTICE, CRIT, TRACE, EMERG, ERROR, ALERT, INFO, WARN, FATAL]
EnumMap  order = [TRACE, DEBUG, INFO, NOTICE, WARN, ERROR, CRIT, ALERT, EMERG, FATAL]
```

**The two runs agree, exactly.** Saying so honestly matters more than manufacturing a
difference. The reason: HotSpot's default identity-hash mode (`-XX:hashCode=5`) is a
*thread-local* Marsaglia xor-shift whose seed is fixed, so for a fully deterministic program
the *n*th identity hash requested on a given thread is the same number in every run. The claim
"varies per run" is therefore not a property of the JVM's clock or address space — it is a
property of the *program's* determinism.

Break the determinism in the smallest possible way — vary how many identity hashes are
requested before the enum constants are hashed — and the order moves:

```java
int warmup = Integer.parseInt(args[0]);
for (int i = 0; i < warmup; i++)
    System.identityHashCode(new Object());   // consumes hash-generator state

Map<Level, Integer> hm = new HashMap<>();
for (Level l : Level.values())
    hm.put(l, l.ordinal());
System.out.println("warmup=" + warmup + "  TRACE.hashCode()=" + Level.TRACE.hashCode()
    + "  HashMap order=" + hm.keySet());
```

```
$ java -cp out OrderRun2 0
warmup=0  TRACE.hashCode()=366712642   HashMap order=[INFO, ERROR, CRIT, WARN, FATAL, EMERG, TRACE, DEBUG, NOTICE, ALERT]
$ java -cp out OrderRun2 1
warmup=1  TRACE.hashCode()=1829164700  HashMap order=[DEBUG, WARN, ERROR, NOTICE, EMERG, ALERT, TRACE, INFO, FATAL, CRIT]
```

One extra `identityHashCode` call anywhere earlier in the thread — a logging framework
initialising, a lazily-built cache, a different code path taken because a config flag flipped —
reorders the whole map. And under a non-default hash mode the instability is unconditional:

```
$ java -XX:+UnlockExperimentalVMOptions -XX:hashCode=0 -cp out OrderRun
identityHashCode(TRACE) = 977028725
HashMap  order = [FATAL, INFO, DEBUG, NOTICE, EMERG, TRACE, CRIT, ALERT, WARN, ERROR]
$ java -XX:+UnlockExperimentalVMOptions -XX:hashCode=0 -cp out OrderRun
identityHashCode(TRACE) = 823009757
HashMap  order = [TRACE, DEBUG, ERROR, WARN, EMERG, NOTICE, INFO, FATAL, CRIT, ALERT]
```

`EnumMap`'s order is identical in all six runs above, because it is `ordinal()` order and
nothing else.

![Two JVM runs side by side: the enum constants receive different identity hash codes, so the HashMap's bucket assignment and resulting iteration order differ between runs, while the EnumMap's ordinal-indexed array produces byte-identical iteration order in both](../diagrams/D-116-enum-hashmap-vs-enummap-order.svg)

The thing to look at is which column changed between the two runs: only the bucket indices and
the resulting key order on the `HashMap` side. The `EnumMap` side is pinned by the ordinals
printed down its left edge.

### Minimal runnable example

```java
enum Level { TRACE, DEBUG, INFO, NOTICE, WARN, ERROR, CRIT, ALERT, EMERG, FATAL }

Map<Level, Integer> hm = new HashMap<>();
Map<Level, Integer> em = new EnumMap<>(Level.class);
for (Level l : Level.values()) {
    hm.put(l, l.ordinal());
    em.put(l, l.ordinal());
}
System.out.println("identityHashCode(TRACE) = " + System.identityHashCode(Level.TRACE));
System.out.println("TRACE.hashCode()        = " + Level.TRACE.hashCode());
System.out.println("HashMap  order = " + hm.keySet());
System.out.println("EnumMap  order = " + em.keySet());
```

That is the whole program behind the transcripts above — run it twice under default flags, then
twice under `-XX:+UnlockExperimentalVMOptions -XX:hashCode=0`, and compare the two `order` lines.

### The gotcha

**Insight:** the correct precise claim to make in an interview is not "identity hash codes are
random per run" — on default HotSpot with a deterministic program they demonstrably are not.
It is "identity hash codes are **unspecified**, so `HashMap` iteration order over enum keys is
not a guarantee you may depend on, and it does in fact shift the moment anything upstream of
you allocates or hashes differently." Anything you commit to disk, a wire format, a golden test
file or a UI ordering, based on that order, is a latent bug.

**Interview:** "Why prefer `EnumMap` over `HashMap` for enum keys?" — one line: worst-case O(1)
with no hashing and no `Node` per entry, plus deterministic declaration-order iteration, which a
`HashMap` cannot promise because an enum's hash is the unspecified identity hash and
`Enum.hashCode()` is `final` so you cannot fix it.

> **Definition.** An enum-keyed `HashMap` re-derives a location from an unspecified identity
> hash code and allocates a `Node` per mapping, giving unreproducible iteration order and more
> work per operation, where `EnumMap` reads the ordinal the compiler already assigned and gets
> declaration-order iteration for free.

---

## Pitfalls

### Persisting or comparing `ordinal()`

**Wrong**

```java
enum Status { NEW, ACTIVE, CLOSED }
// Someone stores ordinals in a column, and later inserts a constant alphabetically:
enum Status { ACTIVE, CLOSED, NEW }
// Every persisted 0 now reads back as ACTIVE instead of NEW, and every EnumMap /
// EnumSet built from those rows silently maps the wrong values. Nothing throws.
```

**Right**

```java
// Persist the name, which is stable under reordering.
String stored = status.name();
Status back = Status.valueOf(stored);   // throws IllegalArgumentException if the name is gone
```

**Why people believe it:** `ordinal()` is public, `int`-shaped and looks like a stable primary
key, and `EnumMap`/`EnumSet` themselves depend on it — so it feels sanctioned. The difference is
that `EnumMap` and `EnumSet` only ever hold ordinals *in memory, within one process, alongside
the class that defined them*; the moment an ordinal outlives the class file it was computed
against, its meaning is gone. Reordering constants also silently changes `EnumMap`/`EnumSet`
iteration order and the meaning of `EnumSet.range(A, B)`, which is a behavioural change with no
compile error to warn you.

### Believing `EnumSet` cannot hold more than 64 elements

**Wrong**

```java
// The belief: "EnumSet is a long, so it maxes out at 64 elements."
// Someone therefore hand-rolls a HashSet for a 200-constant enum.
Set<Permission> granted = new HashSet<>();   // 200-constant Permission enum
```

**Right**

```java
// EnumSet.noneOf picks the representation for you; there is no ceiling on set size.
Set<Permission> granted = EnumSet.noneOf(Permission.class);   // -> JumboEnumSet
granted.addAll(EnumSet.range(Permission.P000, Permission.P199));
System.out.println(granted.size());   // 200
// Storage: long[(200 + 63) >>> 6] = long[4] = 32 bytes + header, vs 200 HashMap Nodes.
```

**Why people believe it:** the 64 in `EnumSet.java:117` is real and widely quoted, and
`RegularEnumSet`'s single `long` is the implementation everyone reads first. What the 64 selects
is which of two `permits`-ed subclasses gets instantiated (`:117-120`) — `JumboEnumSet` exists
precisely to remove the ceiling, and `EnumSet.noneOf` is the only door into either, so a caller
never chooses wrongly.

### Assuming a bulk operation stays a bit operation

**Wrong**

```java
EnumSet<Day> workdays = EnumSet.range(Day.MON, Day.FRI);
List<Day> fromConfig = List.of(Day.WED, Day.THU);
workdays.removeAll(fromConfig);   // NOT elements &= ~other -- falls through to :243 super.removeAll
```

**Right**

```java
// Convert at the boundary, once, then every set operation is a bit operation.
EnumSet<Day> exclusions = EnumSet.copyOf(fromConfig);   // one pass, then O(1) forever
workdays.removeAll(exclusions);                          // elements &= ~es.elements   (:249)
```

**Why people believe it:** the fast paths are invisible at the call site. Every bulk method
opens with `if (!(c instanceof RegularEnumSet<?> es)) return super.xxx(c);` (`:218`, `:243`,
`:263`, `:200`), so the same source line is one instruction or an element-by-element
`AbstractSet` loop depending purely on the runtime type of the argument. The result is correct
either way, which is why it never shows up as a bug — only as a profile.

---

## Cheat sheet

| Fact | Value / source |
|---|---|
| `EnumSet` declaration | `public abstract sealed class ... permits JumboEnumSet, RegularEnumSet` (`EnumSet.java:81-82`) — sealed since Java 17 |
| `EnumSet` fields | `final transient Class elementType` (`:91`), `final transient Enum[] universe` (`:96`) |
| `universe` source | `SharedSecrets...getEnumConstantsShared` (`:408-409`) — shared, uncloned, zero-copy |
| Impl choice | `universe.length <= 64` -> `RegularEnumSet`, else `JumboEnumSet` (`:117-120`); on constant count, not set size |
| Abstract hooks | `addAll()` (`:143`), `complement()` (`:393`) — package-private, mutate in place |
| Factories | `allOf` = `noneOf`+`addAll()` (`:133`); `of` = `noneOf`+`add` (`:217`); `complementOf` = `copyOf`+`complement()` (`:197`) |
| `RegularEnumSet` state | `private long elements = 0L` (`:43`) |
| `size()` / `isEmpty()` | `Long.bitCount(elements)` (`:123`) — recomputed; `elements == 0` (`:132`) |
| Membership | `(elements & (1L << e.ordinal())) != 0` (`:148`) |
| `add` / `remove` | `\|= (1L << ord)` (`:165`); `&= ~(1L << ord)` (`:183`) |
| Union / diff / intersect | `elements \|= es.elements` (`:229`), `&= ~` (`:249`), `&=` (`:272`) — no loop |
| `containsAll` / `equals` | `(es.elements & ~elements) == 0` (`:205`); `es.elements == elements` (`:298`) |
| Non-`EnumSet` argument | every bulk op falls back to `super.xxx(c)` (`:218`, `:243`, `:263`, `:200`) |
| `allOf` mask | `elements = -1L >>> -universe.length` (`:55`); N=5 -> 31 |
| `complement()` | `~elements`, then `&= -1L >>> -universe.length` (`:60-61`) — no `mask` field exists |
| `>>> -n` | JLS §15.19: `long` shift distance is mod 64, so `>>> -5` == `>>> 59` |
| `addRange` | `(-1L >>> (from - to - 1)) << from` (`:50`) |
| `RegularEnumSet` iterator | snapshot `unseen`; `unseen & -unseen` + `numberOfTrailingZeros` (`:104-106`); O(size), never CME |
| `JumboEnumSet` state | `long[] elements` sized `(N + 63) >>> 6` (`:52`) + cached `int size` (`:48`) |
| Jumbo indexing | word `ordinal >>> 6`, bit `ordinal & 63` (`:189`); shift distance unmasked, mod 64 |
| Jumbo bulk ops | word loops: `\|=` (`:284`), `&= ~` (`:304`), `&=` (`:327`); `complement` masks last word only (`:81`) |
| Type-mismatch bulk ops | `addAll` throws CCE; `removeAll` false; `retainAll` clears; `containsAll` -> `es.isEmpty()`; `equals` both-empty |
| Ordinal dependence | reordering constants changes iteration order, `range()` meaning, and every persisted ordinal — silently |
| `Enum.hashCode()` | declared `public final`, body `super.hashCode()` — identity hash, unoverridable |
| `HashMap` order over enums | unspecified; stable across runs of a *deterministic* program on default `-XX:hashCode=5`, shifts as soon as upstream hashing differs |

---

## Self-test

**Q1.** `RegularEnumSet.complement()` masks with `-1L >>> -universe.length`. Explain why a negative shift distance compiles and works, and compute the mask for a 5-constant enum.

<details><summary>Answer</summary>

JLS §15.19: when the left operand of a shift is a `long`, only the low six bits of the right
operand are used, i.e. the distance is taken mod 64. `-5` is `...11111011`; its low six bits are
`111011` = 59. So `-1L >>> -5` is `-1L >>> 59`. `-1L` is all 64 bits set, shifted right by 59
leaves the low 5 bits set: `0b11111` = 31 — exactly one bit per constant, verified by output
(`mask -1L >>> -5 = 31`, `-1L >>> 59 equal? = true`).

The idiom is used in three places: `addAll()` (`:55`) to set every valid bit, `complement()`
(`:61`) to clear the bits above the universe after flipping, and `JumboEnumSet.complement()`
(`:81`) on the last word only. Both `RegularEnumSet` call sites guard with
`universe.length != 0`, because `-0 == 0` and `-1L >>> 0` is `-1L`, which would set all 64 bits
for an empty universe. Note also that there is no field named `mask` in the class — the syllabus
phrasing `~elements & mask` describes the effect, not the code; the mask is recomputed inline
every time.

</details>

**Q2.** Prove from the source that `EnumSet.addAll(EnumSet)` does not scale with the size of either set, without running a benchmark.

<details><summary>Answer</summary>

`RegularEnumSet.addAll` (`:216-231`) is: an `instanceof RegularEnumSet<?> es` pattern guard
falling back to `super.addAll(c)` for non-`EnumSet` arguments (`:218`); an `elementType`
comparison that throws `ClassCastException` for a non-empty foreign set (`:220-226`); then
`long oldElements = elements; elements |= es.elements; return elements != oldElements;`
(`:228-230`). The mutating body contains no loop and no per-element call — it is one `getfield`,
one `lor`, one `putfield` on a primitive `long`. Since nothing in the body reads either set's
cardinality, the work is constant regardless of how many bits are set on either side. Verified
structurally against output: a 32-element set unioned with a 32-element set produced
`bu == (b1 | b2) ? true` and size 48.

`JumboEnumSet.addAll` (`:284`) loops once per 64-bit word, so the bound there is `ceil(N/64)`
operations, still independent of the number of elements. That is what "one instruction for an
arbitrarily large union" means — a structural property of the code, not a measured time. No
timing is offered here, and none is needed.

</details>

**Q3.** Two JVM runs of a program that builds a `HashMap<Level, Integer>` print the same iteration order. Does that refute "enum-keyed `HashMap` order is irreproducible"?

<details><summary>Answer</summary>

No — it refutes the *sloppy version* of the claim. Measured on HotSpot 21 with default flags,
two separate JVMs produced byte-identical output including `identityHashCode(TRACE) = 1163157884`
in both, because the default identity-hash generator (`-XX:hashCode=5`) is a thread-local
xor-shift with a fixed seed: the *n*th identity hash on a thread is deterministic, so a
deterministic program reproduces it.

The correct claim is that the order is **unspecified**, and it moves as soon as anything about
the hashing sequence changes. Requesting one extra `System.identityHashCode(new Object())`
before populating the map changed `TRACE.hashCode()` from 366712642 to 1829164700 and reordered
the whole key set. Under `-XX:hashCode=0` (a global RNG) two runs differed outright: 977028725
vs 823009757, with different orders. `EnumMap`'s order was identical in all six runs, because
it is `ordinal()` order. Practical upshot: never persist, wire-format, or golden-test the
iteration order of an enum-keyed `HashMap`.

</details>

**Q4.** Does `java.lang.Enum` override `hashCode()`, and why does the answer matter?

<details><summary>Answer</summary>

Yes — and the widely-repeated "it doesn't override it, it just inherits `Object.hashCode()`" is
wrong in letter if right in effect. Reflection on JDK 21 reports
`Enum.class.getDeclaredMethod("hashCode")` exists with modifiers `public final`, and its body is
`return super.hashCode();`. Verified:
`Day.MON.hashCode() == System.identityHashCode(Day.MON)` is `true`.

Why it matters: the `final` is load-bearing. Because the method is declared `final` on `Enum`,
no enum type can give itself a value-based or stable hash code — the identity hash is not merely
the default you could replace, it is mandatory. That closes the only escape hatch a developer
might reach for to make an enum-keyed `HashMap`'s iteration order reproducible, and it is the
underlying reason `EnumMap`/`EnumSet` exist as ordinal-indexed structures instead of specialised
hash tables.

</details>

**Q5.** Why does `retainAll` clear the set when the argument is an `EnumSet` of a different enum type, while `removeAll` returns `false` and leaves it alone?

<details><summary>Answer</summary>

Because both answers are the mathematically correct one for a **disjoint** argument, and two
`EnumSet`s of different element types can share no members. `RegularEnumSet.retainAll`
(`:265-269`) keeps only the intersection, and the intersection with a disjoint set is empty, so
it sets `elements = 0` and returns whether that changed anything. `removeAll` (`:245-246`)
removes the intersection, which is empty, so there is nothing to do and it returns `false`.
`containsAll` (`:202-203`) returns `es.isEmpty()` — "contains all of nothing" is vacuously true,
"contains all of something disjoint" is false. `addAll` (`:220-226`) is the only one that
*throws*, because there is no correct empty-answer: actually inserting foreign constants would
corrupt the bit vector, so a non-empty foreign set is a `ClassCastException` while an empty one
is a no-op returning `false`. Verified for all four in one run:
`removeAll = false`, `containsAll = false`, `addAll` threw `ClassCastException: class Proofs$Big != class Proofs$Day`,
`retainAll = true` leaving `days = []`.

</details>

**Q6.** A colleague says `EnumSet` tops out at 64 elements. Where does the 64 actually come from, and what does it select?

<details><summary>Answer</summary>

From `EnumSet.java:117`, inside `noneOf`: `if (universe.length <= 64) return new RegularEnumSet<>(...)`
`else return new JumboEnumSet<>(...)` (`:117-120`). It is tested against `universe.length` — the
number of constants *declared* in the enum — not against the number of elements in the set, and
it is evaluated once, at creation, so the representation is fixed for the object's lifetime.

What it selects is which of the two `permits`-ed subclasses is instantiated. `RegularEnumSet`
stores one `long` (`:43`); `JumboEnumSet` stores `long[(N + 63) >>> 6]` plus a cached `int size`
(`:52`, `:48`). Verified: a 64-constant enum yields `RegularEnumSet`, a 65-constant enum yields
`JumboEnumSet` with `words.length == 2`. There is no size ceiling in either. Since every public
factory funnels through `noneOf`, a caller can never pick the wrong one.

</details>

**Q7.** Why does `JumboEnumSet` cache `size` in a field when `RegularEnumSet` recomputes it, and what does that cost?

<details><summary>Answer</summary>

`RegularEnumSet.size()` is `Long.bitCount(elements)` (`:123`) — one instruction on one word, so
caching would add a field and an invariant for no gain. `JumboEnumSet` would have to sum
`Long.bitCount` across `ceil(N/64)` words, making `size()` O(words); so it keeps
`private int size = 0` (`:48`) and returns it directly (`:163`). The source comment is explicit:
"Redundant - maintained for performance".

The cost is that every mutator must keep the field in step, which is why `JumboEnumSet`'s
`add`, `remove`, `addAll`, `removeAll`, `retainAll` and `complement` are all visibly longer than
their `RegularEnumSet` counterparts — each one recomputes or adjusts `size` after touching the
words, rather than just returning `elements != oldElements`. Verified: for
`EnumSet.of(C00, C63, C64)` the cached field reads 3 and `size()` returns 3.

</details>

---

**Leaves covered:** 3.10.8–3.10.14 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** D-116
**Target version:** Java 21 LTS
**Lines:** 770
