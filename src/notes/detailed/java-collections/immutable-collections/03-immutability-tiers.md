# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.4.1–2.4.5)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/02b-entries-snapshots-and-stream-terminals.md](02b-entries-snapshots-and-stream-terminals.md) · Next: [immutable-collections/03a-immutability-tiers-comparison-table.md](03a-immutability-tiers-comparison-table.md)

"Immutable" is not a boolean in `java.util`. It is a ladder with five rungs, and the JDK
gives you a factory on nearly every one. Almost every production bug in this area comes from
a developer who believed there were two rungs. The seven-column matrix tabulating the
finished ladder is in [03a-immutability-tiers-comparison-table.md](03a-immutability-tiers-comparison-table.md).

## The immutability ladder

### Mental model

Picture a ladder with five rungs. You start at the bottom holding a collection you can do
anything to. Each rung up removes one capability, and once removed it never comes back:

- **Rung 0 → 1:** you lose the ability to change the *size* (`add`, `remove`).
- **Rung 1 → 2:** you lose the ability to change the *contents* (`set`, `sort`, `replaceAll`).
- **Rung 2 → 3:** you lose the *link to the source* — nobody else can change it behind your back.
- **Rung 3 → 4:** you lose *nulls and duplicate arguments*, and gain a purpose-built
  representation that costs less memory and can be value-based.

The critical property of the ladder is that **the rung is a property of the object you are
holding, not of the interface you declared**. `List<String> xs` tells you nothing. Every
rung implements `List`. The compiler will not help you; only the runtime type will.

![The five immutability tiers drawn as a ladder. Look first at Tier 1: it splits into two sub-rungs with different capability strips, because Arrays.asList permits set and Collections.nCopies does not. Look also at where EnumSet sits — Tier 0, alongside new ArrayList, not with List.of.](../diagrams/D-39-immutability-tiers.svg)

Each rung's strip shows which of `add` / `remove` / `set` / reflects-source it still has; the
rest of this file is that picture, proved line by line from the JDK source.

### Why the ladder exists

The `Collection` interfaces were designed in Java 1.2 with *optional operations* —
`add` is declared on `List`, and an implementation is permitted to throw
`UnsupportedOperationException` instead of honouring it. That single design decision is
what makes a ladder possible at all: there is no `ImmutableList` type to declare, so
immutability is expressed by *which methods throw*, discovered at runtime.

Before Java 9 there was no truly immutable factory. Code wanting an immutable list wrote
`Collections.unmodifiableList(new ArrayList<>(Arrays.asList("a", "b")))` — three
allocations and one wrapper indirection per read, to express one idea. Java 9's `List.of`
collapsed that to one call and one object. Java 10's `List.copyOf` closed the remaining
gap: "make me an immutable snapshot of *this* collection".

The rungs span 25 years of API. Note the vintages, because they explain the naming mess:

| Rung | Representative factory | Since |
|---|---|---|
| 0 | `new ArrayList<>()`, `EnumSet.of` | 1.2 (`EnumSet` 1.5) |
| 1a | `Arrays.asList` | 1.2 |
| 1b | `Collections.nCopies` | 1.2 |
| 2 | `Collections.unmodifiableList` | 1.2 |
| 3 | `List.copyOf` | 10 |
| 4 | `List.of`, `Set.of`, `Map.of` | 9 |

### When to reach for which rung

- **Rung 4 (`List.of`) by default.** Cheapest, safest, self-documenting. Loses: cannot hold
  nulls, and `Set.of`/`Map.of` reject duplicate arguments at construction (see
  [03b-immutability-tiers-b-factory-rules.md](03b-immutability-tiers-b-factory-rules.md)).
- **Rung 3 (`List.copyOf`)** when the elements arrive as a collection you do not own and
  want to freeze. It is a snapshot, so caller mutation cannot leak in.
- **Rung 2 (`Collections.unmodifiableList`)** when you *must* tolerate nulls, or when you
  deliberately want a live read-only window onto a collection you keep mutating. This is
  the only rung that reflects source changes — sometimes that is the feature, usually it is
  the bug.
- **Rung 1** essentially never on purpose. `Arrays.asList` is a bridge from arrays, and its
  mutability is a side effect of that bridging, not a design goal.
- **Rung 0** when you are building. Then hand out a higher rung.

### How it works: three distinct mechanisms

The five rungs are produced by three different implementation strategies, and knowing which
one you have tells you every cell of the capability matrix.

**1. Inherit the throwing default (rungs 1a, 1b).** `AbstractList` supplies mutators that
just throw, so any subclass that does not override them is immutable *in that respect*:

```java
// AbstractList.java:137-139
public E set(int index, E element) {
    throw new UnsupportedOperationException();
}
```

`Arrays.asList` returns `Arrays$ArrayList`, which extends `AbstractList` and **does**
override `set`:

```java
// Arrays.java:4269-4274
@Override
public E set(int index, E element) {
    E oldValue = a[index];   // read the current element out of the backing array
    a[index] = element;      // write straight into the caller's array
    return oldValue;         // List.set contract: return the displaced element
}
```

`a` is the array the caller passed in (`Arrays.java:4237-4239` — `a = Objects.requireNonNull(array)`,
no copy). So `set` on this list is a write to the caller's array. It never overrides
`add(int, E)` or `remove(int)`, so those keep `AbstractList`'s throw. That is exactly what
"fixed-size but mutable" means.

`Collections.nCopies` returns `CopiesList` (`Collections.java:5367-5370`), which also
extends `AbstractList` — and **does not override `set` at all**. Scanning
`Collections.java:5367-5500`, the class defines `size`, `contains`, `indexOf`,
`lastIndexOf`, `get`, `forEach`, `toArray`, `subList`, `hashCode`, `equals`, `stream` and
nothing else. It cannot support `set`, because it stores one element reference for `n`
positions:

```java
// Collections.java:5374-5382
final int n;
@SuppressWarnings("serial") // Conditionally serializable
final E element;

CopiesList(int n, E e) {
    assert n >= 0;
    this.n = n;
    element = e;
}
```

There is no per-index storage to write to. `n` and `element` are both `final`.

**[PROVE] Tier 1 is not one tier.** `Arrays.asList("a").set(0, "z")` succeeds because
`Arrays$ArrayList` overrides `set` to write the backing array. `Collections.nCopies(1, "a").set(0, "z")`
throws `UnsupportedOperationException` because `CopiesList` does not override `set` and
inherits `AbstractList.set`. The syllabus leaf 2.4.2 puts both under one heading
"fixed-size"; the source says one is fixed-size-and-writable and the other is fully
unmodifiable. `nCopies`' own javadoc (`Collections.java:5342`) says "Returns an
**immutable** list" — the JDK itself does not classify it as tier 1.

**2. Delegate every read, throw on every write (rung 2).** `UnmodifiableCollection` holds
a reference to the wrapped collection and forwards reads:

```java
// Collections.java:1056-1067
@SuppressWarnings("serial") // Conditionally serializable
final Collection<? extends E> c;

UnmodifiableCollection(Collection<? extends E> c) {
    if (c==null)
        throw new NullPointerException();
    this.c = c;
}

public int size()                          {return c.size();}
public boolean isEmpty()                   {return c.isEmpty();}
public boolean contains(Object o)          {return c.contains(o);}
```

`size()` asks `c` every time — that is *why* rung 2 reflects source changes. `c` is `final`,
so the wrapper can never be re-pointed, but the collection it points at stays fully mutable.
`UnmodifiableList` adds the index-based mutators as throws (`Collections.java:1502-1510`).
The `@SuppressWarnings("serial")` annotation on `c` is the compiler being told "yes, this
serializable class has a non-serializable-typed field" — which is precisely why the wrapper
is serializable *only if the wrapped collection is*.

**3. Purpose-built classes where mutators throw unconditionally (rungs 3, 4).**

```java
// ImmutableCollections.java:142-154
static UnsupportedOperationException uoe() { return new UnsupportedOperationException(); }

@jdk.internal.ValueBased
abstract static class AbstractImmutableCollection<E> extends AbstractCollection<E> {
    // all mutating methods throw UnsupportedOperationException
    @Override public boolean add(E e) { throw uoe(); }
    @Override public boolean addAll(Collection<? extends E> c) { throw uoe(); }
    @Override public void    clear() { throw uoe(); }
    @Override public boolean remove(Object o) { throw uoe(); }
    @Override public boolean removeAll(Collection<?> c) { throw uoe(); }
    @Override public boolean removeIf(Predicate<? super E> filter) { throw uoe(); }
    @Override public boolean retainAll(Collection<?> c) { throw uoe(); }
}
```

Every mutator is overridden explicitly rather than left to inheritance — no gaps possible.
`@jdk.internal.ValueBased` marks these as candidates for Valhalla flattening, which is only
legal because the contents genuinely cannot change. `AbstractImmutableList`
(`ImmutableCollections.java:254-263`) adds `set`, `sort`, `replaceAll`, `add(int,E)`,
`remove(int)` and `addAll(int,…)` to the throw list.

**Rung 3 vs rung 4 is not a behavioural difference — it is a provenance difference.**
`List.copyOf` and `List.of` both return `ListN`/`List12`. What differs is where the elements
came from, and `copyOf` has a shortcut:

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

Line 169: if the argument is already a null-free immutable list, **return it unchanged** —
no copy at all. Line 171: an empty input collapses to the shared `EMPTY_LIST` singleton.
Line 174: otherwise snapshot via `toArray()` into a fresh `ListN`. So leaf 2.4.4's phrase
"unmodifiable independent copy" is right about the *guarantee* and wrong about the
*mechanism*: `List.copyOf(x) == x` when `x` is already a `List.of` result.

Re-read D-39 above: its two Tier 1 sub-rungs are the `Arrays$ArrayList` / `CopiesList` split
just proved, and Tiers 3 and 4 share a strip because they share `ListN`.

### Concrete example: walking the ladder from rung 1

```java
import java.util.*;

public class Ladder {
    public static void main(String[] args) {
        String[] backing = {"A", "B", "C"};

        // Rung 1a — set writes THROUGH to the array; add throws
        List<String> tier1a = Arrays.asList(backing);
        tier1a.set(0, "Z");
        System.out.println("tier1a           = " + tier1a
                + "  backing array now " + Arrays.toString(backing));
        try {
            tier1a.add("D");
        } catch (UnsupportedOperationException e) {
            System.out.println("tier1a.add       -> " + e.getClass().getSimpleName());
        }

        // Rung 1b — same leaf in the syllabus, but set throws too
        List<String> tier1b = Collections.nCopies(3, "A");
        try {
            tier1b.set(0, "Z");
        } catch (UnsupportedOperationException e) {
            System.out.println("tier1b.set       -> " + e.getClass().getSimpleName());
        }

        // Rung 2 — read-only WINDOW, not a snapshot
        List<String> source = new ArrayList<>(List.of("A", "B", "C"));
        List<String> tier2 = Collections.unmodifiableList(source);
        source.add("D");
        System.out.println("tier2 after source.add(\"D\") = " + tier2);

        // Rung 3 — snapshot, immune to source mutation
        List<String> tier3 = List.copyOf(source);
        source.add("E");
        System.out.println("tier3 after source.add(\"E\") = " + tier3);

        // Rung 4 — no nulls at all
        try {
            List.of("A", null);
        } catch (NullPointerException e) {
            System.out.println("tier4 null elem  -> NullPointerException");
        }
    }
}
```

Output — JDK 21.0.7, HotSpot 64-Bit Server VM, macOS/aarch64:

```
tier1a           = [Z, B, C]  backing array now [Z, B, C]
tier1a.add       -> UnsupportedOperationException
tier1b.set       -> UnsupportedOperationException
tier2 after source.add("D") = [A, B, C, D]
tier3 after source.add("E") = [A, B, C, D]
tier4 null elem  -> NullPointerException
```

### The gotcha

Rung 2 is where the "defensive copy" idiom goes wrong. `Collections.unmodifiableList(this.items)`
returned from a getter stops the *caller* mutating, and does nothing about the fact that
your own later `this.items.add(…)` is visible to every caller who kept the reference. If
the caller iterates that reference while you mutate, they get
`ConcurrentModificationException` from a collection they were told was unmodifiable. Rung 3
(`List.copyOf`) is the correct tool for a getter; rung 2 is correct only when a live view
is genuinely what you want.

> **Definition.** Java's immutability ladder has five rungs — mutable, fixed-size,
> unmodifiable view, unmodifiable independent copy, truly immutable factory — distinguished
> not by type but by which optional operations throw `UnsupportedOperationException` and
> whether the object retains a reference to a mutable source.

---

## `EnumSet` sits at rung 0, not rung 4

### Mental model

`EnumSet` looks like it belongs with `List.of` — same `of(...)` factory shape, same
"specialised, allocation-frugal, no public constructor" feel, and the things inside it are
enum *constants*. It is in fact a `long` bitmask with a mutable field.

### Mechanism

```java
// RegularEnumSet.java:43
private long elements = 0L;

// RegularEnumSet.java:161-167
public boolean add(E e) {
    typeCheck(e);

    long oldElements = elements;
    elements |= (1L << ((Enum<?>)e).ordinal());
    return elements != oldElements;
}
```

`elements` is a non-`final` instance field. `add` sets a bit with `|=`, an in-place write,
and returns whether the set actually changed. There is no copy, no new object.
**[NUM]** one `long` covers enums with up to 64 constants; beyond that you get
`JumboEnumSet` with a `long[]`.

`EnumSet` is declared `abstract class EnumSet<E> ... implements Cloneable, java.io.Serializable
permits JumboEnumSet, RegularEnumSet` (`EnumSet.java:82`) — a sealed hierarchy, but nothing
about immutability.

### Proof, and the cost of each fix

```java
import java.util.*;

public class EnumSetTier {
    enum Day { MON, TUE, WED, THU, FRI }

    public static void main(String[] args) {
        EnumSet<Day> es = EnumSet.of(Day.MON, Day.TUE);
        System.out.println("before        = " + es + " size=" + es.size());
        System.out.println("add(WED)      = " + es.add(Day.WED) + " -> " + es);
        es.remove(Day.MON);
        System.out.println("remove(MON)   = " + es);
        System.out.println("dup args      = " + EnumSet.of(Day.MON, Day.MON));

        Set<Day> wrapped = Collections.unmodifiableSet(EnumSet.of(Day.MON, Day.TUE));
        try {
            wrapped.add(Day.WED);
        } catch (UnsupportedOperationException e) {
            System.out.println("wrapped.add   -> UnsupportedOperationException");
        }
        System.out.println("wrapped class = " + wrapped.getClass().getName());

        Set<Day> copied = Set.copyOf(EnumSet.allOf(Day.class));
        System.out.println("copied class  = " + copied.getClass().getName());
        System.out.println("still EnumSet = " + (copied instanceof EnumSet));
    }
}
```

Real output, JDK 21.0.7 macOS/aarch64:

```
before        = [MON, TUE] size=2
add(WED)      = true -> [MON, TUE, WED]
remove(MON)   = [TUE, WED]
dup args      = [MON]
wrapped.add   -> UnsupportedOperationException
wrapped class = java.util.Collections$UnmodifiableSet
copied class  = java.util.ImmutableCollections$SetN
still EnumSet = false
```

Two fixes, two costs:

| Fix | Result | Cost |
|---|---|---|
| `Collections.unmodifiableSet(EnumSet.of(...))` | rung 2 wrapper | keeps the bitmask and its O(1) bulk ops, but is a *view* — whoever holds the inner `EnumSet` can still mutate it, so only safe if you never leak the inner reference |
| `Set.copyOf(EnumSet.of(...))` | rung 4 `SetN` | genuine snapshot, but **loses the bitmask entirely**: hash-probed `Object[]` storage, ordinal iteration order gone, `containsAll`/`retainAll` degrade from one `long` AND to per-element hashing |

**Pitfall:** believing `EnumSet.of(...)` returns an immutable set because it is spelled
`of`. Symptom: a `static final Set<Day> WEEKEND = EnumSet.of(SAT, SUN)` constant that some
distant caller mutates via `add`, and every subsequent read sees the change — with no
exception anywhere to point at. Fix: `Set.copyOf(EnumSet.of(SAT, SUN))` for a true
constant, or keep the `EnumSet` strictly private and expose
`Collections.unmodifiableSet(...)`.

**`EnumSet` is also not thread-safe.** `elements |= …` is a non-atomic read-modify-write on
a non-volatile `long`. Concurrent `add`s lose bits. The javadoc's own suggestion is
`Collections.synchronizedSet(EnumSet.noneOf(MyEnum.class))` (`EnumSet.java:63`).

**Interview:** "Is `EnumSet.of` immutable?" — No. It is a mutable `long` bitmask; the `of`
naming mirrors `List.of` but the semantics are `new ArrayList<>()`. `Set.copyOf` gives you
immutability at the cost of the bitmask representation.

> **Definition.** `EnumSet` is a rung-0 mutable collection with a rung-4 factory-method
> vocabulary — a bitmask over an enum's ordinals, fast and compact, but freely mutable and
> not thread-safe.

---

## Pitfalls

### Treating `Collections.unmodifiableList` as a defensive copy

**Wrong**

```java
class Order {
    private final List<String> items = new ArrayList<>();

    List<String> items() { return Collections.unmodifiableList(items); }
    void add(String s) { items.add(s); }
}

Order o = new Order();
o.add("A");
List<String> snapshot = o.items();
o.add("B");
System.out.println(snapshot);   // [A, B] — the "snapshot" moved
```

**Right**

```java
List<String> items() { return List.copyOf(items); }   // rung 3: real snapshot
// snapshot stays [A]; List.copyOf allocates a fresh ListN over items.toArray()
```

**Why people believe it:** the method name says "unmodifiable", and it is — for the
*caller*. It says nothing about the owner. The wrapper stores a reference, not a copy
(`Collections.java:1057-1063`).

### Assuming `Arrays.asList` and `Collections.nCopies` behave the same

**Wrong**

```java
List<String> a = Arrays.asList("x", "x", "x");
List<String> b = Collections.nCopies(3, "x");
// "both are fixed-size lists, so I can normalise either in place"
a.set(0, "y");   // fine
b.set(0, "y");   // UnsupportedOperationException
```

**Right**

```java
List<String> a = new ArrayList<>(Arrays.asList("x", "x", "x"));
List<String> b = new ArrayList<>(Collections.nCopies(3, "x"));
a.set(0, "y");   // fine
b.set(0, "y");   // fine — both are now rung 0
```

**Why people believe it:** both are 1.2-era `Collections`/`Arrays` helpers returning
`AbstractList` subclasses that reject `add`. But `Arrays$ArrayList` overrides `set`
(`Arrays.java:4269-4274`) and `CopiesList` does not (`Collections.java:5367-5500`).

### Believing `EnumSet.of` rejects duplicate arguments the way `Set.of` does

**Wrong**

```java
enum Day { MON, TUE, WED, THU, FRI }

// A config parser that relies on the factory to catch a duplicated entry:
Set<Day> parsed = EnumSet.of(Day.MON, Day.MON);   // no exception
System.out.println(parsed);                       // [MON] — the duplicate vanished silently
System.out.println(Set.of("MON", "MON"));         // IllegalArgumentException: duplicate element: MON
```

**Right**

```java
EnumSet<Day> set = EnumSet.noneOf(Day.class);
for (Day d : List.of(Day.MON, Day.MON)) {
    // add returns false when the bit was already set — the only place the dup is visible
    if (!set.add(d)) throw new IllegalArgumentException("duplicate day: " + d);
}
```

**Why people believe it:** the two factories are spelled the same. But `EnumSet.of` builds
by OR-ing bits (`elements |= 1L << ordinal`), and OR-ing a bit that is already set is a
no-op that cannot be detected after the fact — so there is nowhere for it to throw.
`RegularEnumSet.add` *does* report it, via its `boolean` return.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Rung 0 | `new ArrayList<>`, `new HashMap<>`, **`EnumSet.of`** |
| Rung 1a | `Arrays.asList` — `set` OK, `add`/`remove` UOE, writes through to the array |
| Rung 1b | `Collections.nCopies` — `set` also UOE; javadoc calls it "immutable" |
| Rung 2 | `Collections.unmodifiableX` — live view, reflects source, nulls OK |
| Rung 3 | `List.copyOf` / `Set.copyOf` / `Map.copyOf` — snapshot, no nulls (Java 10) |
| Rung 4 | `List.of` / `Set.of` / `Map.of` — no nulls, no dup args (Java 9) |
| Only rung that reflects source | 2 (and 1a, via the array) |
| Only rung that rejects nulls | 3 and 4 (NPE); `EnumSet` also NPEs |
| Only rung that rejects dup args | 4, for `Set.of`/`Map.of` (IAE) — `EnumSet.of` collapses silently |
| Rung 3 vs rung 4 | same `ListN` class; provenance differs, not behaviour |
| `AbstractList` default mutators | throw UOE (`AbstractList.java:137-169`) — the whole ladder rests on this |
| `Arrays.asList` `set` | `Arrays.java:4269-4274`, writes the caller's uncopied array |
| `CopiesList` `set` | no override; one `final E element` for all `n` slots, so `set` is impossible |
| Getter should return | `List.copyOf(field)` — never `unmodifiableList(field)` |
| `EnumSet` rung | 0 — mutable `long` bitmask, and not thread-safe |
| Immutable enum set | `Set.copyOf(EnumSet.of(...))` — loses the bitmask |
| Full capability matrix | [03a-immutability-tiers-comparison-table.md](03a-immutability-tiers-comparison-table.md) |

---

## Self-test

**Q1.** `Arrays.asList("a","b").set(0,"z")` succeeds but `Collections.nCopies(2,"a").set(0,"z")` throws. Why?

<details><summary>Answer</summary>

Both extend `AbstractList`, whose `set` throws `UnsupportedOperationException`
(`AbstractList.java:137-139`). `Arrays$ArrayList` overrides `set`
(`Arrays.java:4269-4274`) to write directly into the caller's backing array. `CopiesList`
(`Collections.java:5367-5500`) does not override `set` at all — it cannot, because it stores
a single `final E element` for all `n` positions, so there is no per-index slot to write to.

</details>

**Q2.** You return `Collections.unmodifiableList(this.items)` from a getter. What can still go wrong?

<details><summary>Answer</summary>

The wrapper holds a reference to `items` (`Collections.java:1057-1063`) and forwards every
read, so all your own subsequent mutations are visible through it. The caller's "snapshot"
changes under them, and if they are mid-iteration they get `ConcurrentModificationException`
from a collection labelled unmodifiable. Use `List.copyOf(this.items)` for a real snapshot.

</details>

**Q3.** `Collections.nCopies` is listed under the syllabus's "fixed-size" tier. Argue that it is misplaced.

<details><summary>Answer</summary>

Twice misplaced. First, "fixed-size" implies `set` works and only the size is frozen — but
`CopiesList` throws on `set` too, so it is not merely fixed-size. Second, the JDK's own
javadoc at `Collections.java:5342` opens "Returns an **immutable** list", and the object has
no mutable source to reflect, so behaviourally it belongs at rung 3/4 with `List.copyOf` and
`List.of`, not at rung 1 with `Arrays.asList`. The only thing it shares with rung 1 is its
1.2 vintage and its `AbstractList` superclass.

</details>

**Q4.** `EnumSet.of(MON, TUE)` — immutable?

<details><summary>Answer</summary>

No. `RegularEnumSet` stores a non-final `private long elements`
(`RegularEnumSet.java:43`) and `add` mutates it in place with
`elements |= (1L << e.ordinal())` (`RegularEnumSet.java:161-167`). Verified:
`EnumSet.of(MON, TUE).add(WED)` returns `true` and yields `[MON, TUE, WED]`. It is also not
thread-safe — `|=` is a non-atomic read-modify-write. The `of` naming is what misleads.

</details>

**Q5.** You need an immutable `Set` of enum constants. What are the two options and what does each cost?

<details><summary>Answer</summary>

`Collections.unmodifiableSet(EnumSet.of(...))` keeps the `long` bitmask and its O(1) bulk
operations, but it is a *view* — anyone holding the inner `EnumSet` can still mutate it, so
it is safe only if the inner reference never leaks. `Set.copyOf(EnumSet.of(...))` is a
genuine snapshot but returns an `ImmutableCollections$Set12`/`SetN`, losing the bitmask
entirely: hash-probed `Object[]` storage, no ordinal iteration order, and
`containsAll`/`retainAll` degrade from a single `long` AND to per-element hashing. Verified:
`Set.copyOf(EnumSet.allOf(Day.class)) instanceof EnumSet` prints `false`.

</details>

**Q6.** Why does the compiler give you no protection against calling `add` on a rung-4 list?

<details><summary>Answer</summary>

Because `add` is declared on the `List` interface and immutability is expressed by
*throwing* rather than by type. The 1.2 design made mutators "optional operations", so
`ImmutableCollections.AbstractImmutableCollection` (lines 145-154) overrides every one of
them to `throw uoe()`. There is no `ImmutableList` type to declare a parameter as, so the
failure can only surface at runtime.

</details>

**Q7.** Two rungs "reflect source changes". Name them.

<details><summary>Answer</summary>

Rung 2 (`Collections.unmodifiableX`) reflects changes to the wrapped collection, because
every read is forwarded to the `c` field. Rung 1a (`Arrays.asList`) reflects changes to the
backing array, in *both* directions — `list.set(0, x)` writes the array and `arr[0] = y`
changes the list, since `Arrays$ArrayList` stores the caller's array without copying
(`Arrays.java:4237-4239`).

</details>

---

**Leaves covered:** 2.4.1–2.4.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-39
**Target version:** Java 21 LTS
**Lines:** 600
