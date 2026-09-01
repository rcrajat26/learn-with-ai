# 02 Java Collections — Immutability and views — INTERNALS (§3.12.13–3.12.14)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/04b2-internals-salt-cds-and-null-hostility.md](04b2-internals-salt-cds-and-null-hostility.md) · Next: [immutable-collections/04d-internals-sublist-and-reversed-view.md](04d-internals-sublist-and-reversed-view.md)

This file covers the **mutator wall** (3.12.13) and the **serialization proxy** (3.12.14). The views —
`SubList` and `ReverseOrderListView` — moved to
[04d-internals-sublist-and-reversed-view.md](04d-internals-sublist-and-reversed-view.md), and the layout
arithmetic plus the legacy factories to
[04e-internals-layout-and-legacy-factories.md](04e-internals-layout-and-legacy-factories.md). The
filename still says "and-views" because files in this set are never renamed after a split.

Source citations are against JDK 21 `src.zip`: `java.base/java/util/` `ImmutableCollections.java`,
`Collections.java`, `AbstractList.java`, `ReverseOrderListView.java`. Every transcript below is real
output from **JDK 21.0.7, HotSpot 64-Bit Server VM, aarch64 (macOS)**. Code snippets are shown without
imports or `main` scaffolding.

## The shape of this file

The previous files built the *storage* of `ImmutableCollections` — the class family, the open-addressed
probe, the `SALT32L` shuffle. This one covers what the family does to *stay* immutable and to survive
leaving the JVM.

| Leaf | Mechanism | Summary |
|---|---|---|
| 3.12.13 | mutator wall | Every mutator, including Java 8 **default** methods, overridden to throw |
| 3.12.14 | `writeReplace` → `CollSer` | The wire form is a tagged proxy, never the implementation class |

---

## The mutator wall (3.12.13)

**Mental model.** Two concentric walls. `AbstractImmutableCollection` blocks everything a bare
`Collection` can do; `AbstractImmutableList` inside it blocks the six extra positional mutators `List`
adds. Nothing gets through either — not even the methods the *interface* supplies for free.

**Why it exists.** `AbstractCollection.add` already throws, and its
`remove`/`removeAll`/`retainAll`/`clear` are built on `iterator().remove()`, which also throws by
default. So the overrides look redundant. They are not, and why is the whole point of this leaf.

**Mechanism.** `ImmutableCollections.java:142-154`:

```java
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

- `uoe()` is a **factory, not a shared constant** — each throw allocates, so the stack trace names the
  real call site rather than a frame frozen at class-init time.
- `@jdk.internal.ValueBased` marks the class identity-insensitive: HotSpot may fold, cache or
  duplicate instances, so never lock on or identity-compare a `List.of(...)`.
- `add`, `addAll`, `clear`, `remove`, `removeAll`, `retainAll` override `AbstractCollection` methods
  that would have thrown anyway — but only *after* walking the iterator. Overriding makes failure O(1)
  and unconditional, so `imm.removeAll(List.of())` throws instead of quietly returning `false`.
- `removeIf` is the one that *must* be here: it is a **`Collection` default method** (Java 8) whose
  body loops over `iterator()` calling `it.remove()`. Overriding it makes the contract independent of
  iterator behaviour instead of a consequence of it.

Second wall, `ImmutableCollections.java:253-263`:

```java
@jdk.internal.ValueBased
abstract static class AbstractImmutableList<E> extends AbstractImmutableCollection<E>
        implements List<E>, RandomAccess {

    // all mutating methods throw UnsupportedOperationException
    @Override public void    add(int index, E element) { throw uoe(); }
    @Override public boolean addAll(int index, Collection<? extends E> c) { throw uoe(); }
    @Override public E       remove(int index) { throw uoe(); }
    @Override public void    replaceAll(UnaryOperator<E> operator) { throw uoe(); }
    @Override public E       set(int index, E element) { throw uoe(); }
    @Override public void    sort(Comparator<? super E> c) { throw uoe(); }
```

- `implements RandomAccess` — every immutable list, `SubList` included, is `RandomAccess`, so
  `Collections` algorithms take the indexed path.
- `add(int,E)`, `addAll(int,…)`, `remove(int)`, `set(int,E)` are the four positional `List` mutators.
- `replaceAll` and `sort` are `List` **defaults** (Java 8), covered by no abstract superclass.

**Insight:** `removeIf`, `replaceAll` and `sort` are not inherited from `AbstractCollection`/
`AbstractList` at all — they are interface default methods. `List.sort`'s default body snapshots via
`toArray()`, sorts the array, then writes back through a `ListIterator.set` loop — a mutation path that
never calls `add` or `remove`, so no amount of iterator-level refusal would stop it. That is why `sort`
gets its own line at `ImmutableCollections.java:263`.

**Interview:** *"`AbstractCollection.add` already throws — why override it?"* Fail fast in O(1) rather
than after an iterator walk; and, the real answer, the class must also override the Java 8 **defaults**
(`removeIf`, `replaceAll`, `sort`), which no superclass covers.

Every attempt is wrapped, so this runs to completion:

```java
record Attempt(String label, Runnable body) {}
List<String> imm = List.of("a", "b", "c");
List<Attempt> attempts = List.of(
    new Attempt("add(E)",              () -> imm.add("d")),
    new Attempt("remove(Object)",      () -> imm.remove("a")),
    new Attempt("clear()",             imm::clear),
    new Attempt("removeIf",            () -> imm.removeIf(s -> false)),
    new Attempt("retainAll",           () -> imm.retainAll(List.of("a"))),
    new Attempt("set(int,E)",          () -> imm.set(0, "z")),
    new Attempt("sort",                () -> imm.sort(null)),
    new Attempt("replaceAll",          () -> imm.replaceAll(String::toUpperCase)),
    new Attempt("iterator().remove()", () -> imm.iterator().remove()));
for (Attempt a : attempts) {
    try {
        a.body().run();
        System.out.println(a.label() + " -> NO THROW");
    } catch (RuntimeException e) {
        System.out.println(a.label() + " -> " + e.getClass().getSimpleName());
    }
}
System.out.println("list unchanged: " + imm);
```

Real output — all nine lines read `UnsupportedOperationException`:

```
add(E) -> UnsupportedOperationException
remove(Object) -> UnsupportedOperationException
clear() -> UnsupportedOperationException
removeIf -> UnsupportedOperationException
retainAll -> UnsupportedOperationException
set(int,E) -> UnsupportedOperationException
sort -> UnsupportedOperationException
replaceAll -> UnsupportedOperationException
iterator().remove() -> UnsupportedOperationException
list unchanged: [a, b, c]
```

`removeIf(s -> false)` and `sort(null)` throw even though neither would have changed anything: the
contract is *unconditional refusal*, not *refusal only when a change would happen*. That is exactly
where `Collections.emptyList()` diverges — see
[04e-internals-layout-and-legacy-factories.md](04e-internals-layout-and-legacy-factories.md).

> **Definition.** `AbstractImmutableCollection` and `AbstractImmutableList` are the two abstract layers
> that override **every** mutator — inherited *and* interface-default — to throw a freshly allocated
> `UnsupportedOperationException` in O(1), so immutability never depends on iterator behaviour.

---

## The serialization proxy: `writeReplace` → `CollSer` (3.12.14)

**Mental model.** These collections refuse to appear on the wire at all. When `ObjectOutputStream`
reaches a `List12`, the list hands over a **stunt double** — a `CollSer` carrying an integer tag ("I
was a list") and a flat `Object[]`. On the far side the stunt double calls the public factory and hands
back a real collection. The implementation classes never appear in the stream, and their `readObject`
is a locked door with a sign on it.

**Why it exists.** Default serialization writes field layout. That would (a) freeze `List12`'s
two-field shape and `MapN`'s salted table into a public format forever, (b) let a hostile stream build
instances with arbitrary field values — a `SetN` containing duplicates, a `MapN` violating the probe
invariant — bypassing every constructor check, and (c) make the bytes depend on which of six
implementation classes the factory picked and on this JVM's `SALT32L`. The serial-proxy pattern
(Bloch, *Effective Java*, Item 90) decouples wire form from class layout.

**When not to use the pattern:** it costs an extra object per graph node and defeats back-references
between the collection and its elements, so it suits small value-like objects, not large graphs.

**Mechanism.** `CollSer` is a **package-private top-level class**, not a nested one — it sits at the
bottom of `ImmutableCollections.java`, *outside* `ImmutableCollections`, so its binary name is
`java.util.CollSer`, which is what you see in the bytes below. Lines 1371-1421:

```java
final class CollSer implements Serializable {
    @java.io.Serial
    private static final long serialVersionUID = 6309168927139932177L;

    static final int IMM_LIST       = 1;
    static final int IMM_SET        = 2;
    static final int IMM_MAP        = 3;
    static final int IMM_LIST_NULLS = 4;

    private final int tag;

    private transient Object[] array;

    CollSer(int t, Object... a) {
        tag = t;
        array = a;
    }
}
```

- `serialVersionUID = 6309168927139932177L` is the **only** UID that matters for the family. `List12`,
  `ListN`, `SetN`, `Map1`, `MapN` declare none, because none of them is ever written.
- Four tags. `IMM_LIST_NULLS = 4` arrived when `Stream.toList()` (Java 16) needed a null-tolerant
  unmodifiable list. The javadoc at lines 1387-1392 reserves the **high 24 bits** for future use —
  zero on write, ignored on read — which is why `readResolve` masks with `& 0xff`.
- `array` is `transient`, so `defaultWriteObject` skips it; a hand-rolled `writeObject`/`readObject`
  pair (lines 1438-1474) writes a length int then the elements. The read side calls
  `SharedSecrets.getJavaObjectInputStreamAccess().checkArray(ois, Object[].class, len)` at line 1446
  *before* allocating, so a declared length of `Integer.MAX_VALUE` is rejected against
  `jdk.serialFilter` rather than OOMing the JVM.
- For a map the array is a flat `k1, v1, k2, v2, …` of length `2 × mappings` (javadoc lines 1401-1405).

Each concrete class contributes exactly two methods. `List12`, `ImmutableCollections.java:619-631`:

```java
@java.io.Serial
private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
    throw new InvalidObjectException("not serial proxy");
}

@java.io.Serial
private Object writeReplace() {
    if (e1 == EMPTY) {
        return new CollSer(CollSer.IMM_LIST, e0);
    } else {
        return new CollSer(CollSer.IMM_LIST, e0, e1);
    }
}
```

`writeReplace` reads the `e1 == EMPTY` sentinel set by the one-arg constructor (lines 562-567) to
decide 1- versus 2-element, then builds the proxy through the `Object...` constructor. `readObject`
throwing `InvalidObjectException("not serial proxy")` is **the lock**: a stream naming
`java.util.ImmutableCollections$List12` directly would otherwise reach `defaultReadObject` and build a
`List12` with both fields null. The class is `Serializable` (so `writeReplace` is honoured) yet can
never be read. `ListN` (lines 690-698) is the same shape with null-tolerance folded into the tag:

```java
@java.io.Serial
private Object writeReplace() {
    return new CollSer(allowNulls ? CollSer.IMM_LIST_NULLS : CollSer.IMM_LIST, elements);
}
```

It passes the live internal `elements` array with no copy — safe only because `CollSer` is a
short-lived private object nothing else can reach. Reconstruction, lines 1495-1527:

```java
@java.io.Serial
private Object readResolve() throws ObjectStreamException {
    try {
        if (array == null) {
            throw new InvalidObjectException("null array");
        }

        // use low order 8 bits to indicate "kind"
        // ignore high order 24 bits
        switch (tag & 0xff) {
            case IMM_LIST:
                return List.of(array);
            case IMM_LIST_NULLS:
                return ImmutableCollections.listFromTrustedArrayNullsAllowed(
                        Arrays.copyOf(array, array.length, Object[].class));
            case IMM_SET:
                return Set.of(array);
            case IMM_MAP:
                if (array.length == 0) {
                    return ImmutableCollections.EMPTY_MAP;
                } else if (array.length == 2) {
                    return new ImmutableCollections.Map1<>(array[0], array[1]);
                } else {
                    return new ImmutableCollections.MapN<>(array);
                }
            default:
                throw new InvalidObjectException(String.format("invalid flags 0x%x", tag));
        }
    } catch (NullPointerException|IllegalArgumentException ex) {
        InvalidObjectException ioe = new InvalidObjectException("invalid object");
        ioe.initCause(ex);
        throw ioe;
    }
}
```

- `array == null` guards the transient field when a stream omits the custom payload; `tag & 0xff`
  implements the reserved-high-bits rule; `default` rejects unknown tags.
- `List.of(array)` / `Set.of(array)` go through the **public factories**, so null rejection, duplicate
  rejection and size-based class selection all re-run in the receiving JVM. `Set.of` on a duplicate
  throws `IllegalArgumentException`, which the `catch` at line 1522 converts to
  `InvalidObjectException` — a hostile stream cannot smuggle a `Set` with two equal elements.
- `IMM_LIST_NULLS` re-copies to a fresh `Object[].class` array because the proxy's array may be a
  covariant subtype (`String[]`) and `ListN` requires exact `Object[]`.
- `IMM_MAP` is the only branch constructing implementation classes directly, because `Map.of` has no
  array-taking public overload.

![D-122: follow left to right — writeReplace swaps the immutable collection for a CollSer holding a tag plus a flat element array; the stream carries only java.util.CollSer, never List12/SetN/MapN; readResolve switches on tag & 0xff and rebuilds through the public factory; the dashed arrow is readObject on the collection class itself throwing InvalidObjectException("not serial proxy")](../diagrams/D-122-collser-serial-proxy.svg)

For the wider serialization picture — `serialPersistentFields`, filters, the gadget-chain attack
surface — see [../utilities/06-serialization.md](../utilities/06-serialization.md), which embeds this
same diagram from the other direction. This file covers only the `ImmutableCollections` mechanism.

### Proving the round trip, the lock, and the tag check

```java
static byte[] ser(Object o) throws IOException {
    var bos = new ByteArrayOutputStream();
    try (var oos = new ObjectOutputStream(bos)) { oos.writeObject(o); }
    return bos.toByteArray();
}

static Object deser(byte[] b) throws IOException, ClassNotFoundException {
    try (var ois = new ObjectInputStream(new ByteArrayInputStream(b))) { return ois.readObject(); }
}

/** Substitutes List12's class descriptor for CollSer's, so the stream appears to carry a
 *  real ImmutableCollections$List12 and its readObject is invoked. */
static final class SpoofingIn extends ObjectInputStream {
    SpoofingIn(InputStream in) throws IOException { super(in); }

    @Override
    protected ObjectStreamClass readClassDescriptor() throws IOException, ClassNotFoundException {
        ObjectStreamClass desc = super.readClassDescriptor();
        if (desc.getName().equals("java.util.CollSer")) {
            return ObjectStreamClass.lookup(Class.forName("java.util.ImmutableCollections$List12"));
        }
        return desc;
    }
}
```

Driver:

```java
for (Object o : new Object[]{ List.of(), List.of(1), List.of(1, 2), List.of(1, 2, 3),
                              Set.of("x", "y", "z"), Map.of("k", 1, "j", 2) }) {
    Object back = deser(ser(o));
    System.out.printf("%-38s -> %-38s equal=%s same=%s%n", o.getClass().getName(),
            back.getClass().getName(), o.equals(back), o == back);
}
String wire = new String(ser(List.of(1, 2)), "ISO-8859-1");
System.out.println("names java.util.CollSer=" + wire.contains("java.util.CollSer")
        + " names List12=" + wire.contains("List12") + " bytes=" + ser(List.of(1, 2)).length);

try {                                   // the lock
    try (var in = new SpoofingIn(new ByteArrayInputStream(ser(List.of(1, 2))))) { in.readObject(); }
    System.out.println("spoofed List12 stream -> NO THROW");
} catch (Exception e) {
    System.out.println("spoofed List12 stream -> " + e.getClass().getName() + ": " + e.getMessage());
}

byte[] bad = ser(List.of(1, 2));        // corrupt the tag: first 0x00000001 int becomes 9
for (int i = 0; i + 3 < bad.length; i++) {
    if (bad[i] == 0 && bad[i + 1] == 0 && bad[i + 2] == 0 && bad[i + 3] == 1) {
        bad[i + 3] = (byte) 9;
        break;
    }
}
try {
    System.out.println("tag=9 -> " + deser(bad));
} catch (Exception e) {
    System.out.println("tag=9 -> " + e.getClass().getName() + ": " + e.getMessage());
}

for (Object v : new Object[]{ Map.of("k", 1).keySet(), List.of(1, 2, 3, 4).subList(1, 3),
                              List.of(1, 2, 3).reversed() }) {
    try {
        ser(v);
        System.out.println(v.getClass().getName() + " -> serialized");
    } catch (Exception e) {
        System.out.println(v.getClass().getName() + " -> " + e.getClass().getSimpleName());
    }
}
```

Real output:

```
java.util.ImmutableCollections$ListN   -> java.util.ImmutableCollections$ListN    equal=true same=true
java.util.ImmutableCollections$List12  -> java.util.ImmutableCollections$List12   equal=true same=false
java.util.ImmutableCollections$List12  -> java.util.ImmutableCollections$List12   equal=true same=false
java.util.ImmutableCollections$ListN   -> java.util.ImmutableCollections$ListN    equal=true same=false
java.util.ImmutableCollections$SetN    -> java.util.ImmutableCollections$SetN     equal=true same=false
java.util.ImmutableCollections$MapN    -> java.util.ImmutableCollections$MapN     equal=true same=false
names java.util.CollSer=true names List12=false bytes=142
spoofed List12 stream -> java.io.InvalidObjectException: not serial proxy
tag=9 -> java.io.InvalidObjectException: invalid flags 0x9
java.util.AbstractMap$1                  -> NotSerializableException
java.util.ImmutableCollections$SubList   -> NotSerializableException
java.util.ReverseOrderListView$Rand      -> NotSerializableException
```

Five readings:

1. The class round-trips to the same implementation type — but only because `readResolve` re-runs the
   same size-based factory dispatch, not because the type was in the stream.
2. `List.of()` deserializes to the **identical** object (`same=true`): `readResolve` calls
   `List.of(new Object[0])` → `listFromTrustedArray` `case 0` → the shared `EMPTY_LIST`
   (`ImmutableCollections.java:219`). Nothing else in the family is identity-preserved.
3. The stream contains `java.util.CollSer` and **no mention of `List12`**. Format stability confirmed —
   and note the name: `java.util.CollSer`, *not* `java.util.ImmutableCollections$CollSer`. `CollSer`
   is a package-private **top-level** class declared after `ImmutableCollections` in the same file
   (`ImmutableCollections.java:1371`). Anyone grepping a stream or a serial filter pattern for the
   nested name finds nothing.
4. The lock and the tag check are both genuinely reachable, not merely asserted:
   `InvalidObjectException: not serial proxy` from the descriptor-substituting `SpoofingIn`, and
   `InvalidObjectException: invalid flags 0x9` from patching the tag int to 9. Both inside try/catch.
5. **Pitfall:** serializability covers the *collection*, not views derived from it.
   `Map.of(...).keySet()` fails with `NotSerializableException: java.util.AbstractMap$1` — the key set
   is the anonymous `AbstractSet` inherited from `AbstractMap`, which nobody declared serializable.
   `SubList` and `ReverseOrderListView` are likewise not serializable; both are covered in
   [04d-internals-sublist-and-reversed-view.md](04d-internals-sublist-and-reversed-view.md).
   Relatedly, `KeyValueHolder` (what `Map.entry` returns) is explicitly non-serializable, while
   `AbstractMap.SimpleEntry` and `SimpleImmutableEntry` both are.

### The salt consequence: a round-tripped `Set.of` has the *receiver's* order

Because `readResolve` calls `Set.of(array)` in the receiving JVM, the rebuilt set is hashed and probed
with **that** JVM's `SALT32L` (see [04b-internals-open-addressing-and-salt.md](04b-internals-open-addressing-and-salt.md)),
derived once per process from `System.nanoTime()`. Iteration order therefore does not survive a
serialization boundary — not even for the same bytes read twice in different processes.

```java
static final Path P = Path.of("/tmp/set.ser");

// args[0] == "write"
Set<String> s = Set.of("alpha", "beta", "gamma", "delta", "epsilon");
try (var oos = new ObjectOutputStream(Files.newOutputStream(P))) { oos.writeObject(s); }
System.out.println("wrote  order=" + s);

// otherwise: read
try (var ois = new ObjectInputStream(Files.newInputStream(P))) {
    @SuppressWarnings("unchecked")
    Set<String> back = (Set<String>) ois.readObject();
    System.out.println("read   order=" + back + "  equalsOriginal="
            + back.equals(Set.of("alpha", "beta", "gamma", "delta", "epsilon")));
}
```

One `write` run, then four separate `read` JVMs — real output:

```
wrote  order=[gamma, delta, beta, epsilon, alpha]
read   order=[delta, beta, epsilon, alpha, gamma]  equalsOriginal=true
read   order=[beta, delta, gamma, alpha, epsilon]  equalsOriginal=true
read   order=[gamma, alpha, epsilon, beta, delta]  equalsOriginal=true
read   order=[alpha, epsilon, beta, delta, gamma]  equalsOriginal=true
```

Five orders, all `equals`-identical. The *stream* is order-stable — `writeObject` walks the proxy
array, written in sender-salt order — so this is purely the receiver re-shuffling. `SALT32L`/`REVERSE`
affect iteration order only, never `probe` correctness, so `contains` and `equals` are unaffected.

**Interview:** *"Why can't `List.of(...)` use default serialization?"* The wire form would name one of
six private implementation classes and encode their private field layout, and a crafted stream could
bypass the factory's null/duplicate checks. `CollSer` publishes a tag plus elements, and `readResolve`
rebuilds through `List.of`/`Set.of`, re-checking invariants on the receiving side.

> **Definition.** Immutable collections serialize via `writeReplace()` to a single package-private
> `java.util.CollSer` proxy carrying a `tag` (1 list / 2 set / 3 map / 4 null-tolerant list, low 8
> bits) plus a flat element array; `CollSer.readResolve()` rebuilds through the public factories, and
> each implementation class's own `readObject` throws `InvalidObjectException("not serial proxy")` so
> it can never be deserialized directly.

---

## Pitfalls

### Assuming a round-tripped `Set.of` keeps its iteration order

**Wrong**

```java
oos.writeObject(Set.of("alpha", "beta", "gamma", "delta", "epsilon"));  // process A: [gamma, delta, beta, epsilon, alpha]
Set<String> s = (Set<String>) ois.readObject();                        // process B
assert s.iterator().next().equals("gamma");                            // fails, unpredictably
```

Process B printed `[delta, beta, epsilon, alpha, gamma]`, then `[beta, delta, gamma, alpha, epsilon]`
on the next run. `readResolve` calls `Set.of(array)`, re-hashing with the *receiving* JVM's `SALT32L`.

**Right**

```java
oos.writeObject(List.copyOf(new TreeSet<>(Set.of("alpha", "beta", "gamma", "delta", "epsilon"))));
List<String> s = (List<String>) ois.readObject();   // [alpha, beta, delta, epsilon, gamma], always
```

**Why people believe it:** every other `Serializable` collection in `java.util` — `LinkedHashSet`,
`TreeSet`, `ArrayList` — writes its contents in order and reads them back in order. `Set.of` is the
only one that discards the order deliberately.

### Filtering or grepping for `ImmutableCollections$CollSer`

**Wrong**

```java
// A serial filter meant to allow the immutable-collection proxy through:
ObjectInputFilter f = ObjectInputFilter.Config.createFilter(
        "java.util.ImmutableCollections$CollSer;!*");   // matches nothing
```

`CollSer` is not a nested class. `ImmutableCollections.java:1371` declares
`final class CollSer implements Serializable` at **top level**, after the `ImmutableCollections` class
body closes. Verified: the serialized bytes of `List.of(1,2)` contain `java.util.CollSer` and no
occurrence of the substring `List12`.

**Right**

```java
ObjectInputFilter f = ObjectInputFilter.Config.createFilter("java.util.CollSer;java.lang.Integer;!*");
```

**Why people believe it:** the class lives in `ImmutableCollections.java`, next to six genuinely nested
implementation classes, and every other type in that file *is* nested. The file name is not the
enclosing class.

### Believing an `InvalidObjectException("not serial proxy")` can never fire

**Wrong**

```java
// "readObject on List12 is dead code — writeReplace means the stream never names List12."
```

It is reachable by any stream you did not write. Substituting the class descriptor on the read side is
enough:

```java
try (var in = new SpoofingIn(new ByteArrayInputStream(ser(List.of(1, 2))))) { in.readObject(); }
// java.io.InvalidObjectException: not serial proxy
```

**Right** — treat it as a live security control, and keep the demo inside try/catch:

```java
try {
    try (var in = new SpoofingIn(new ByteArrayInputStream(ser(List.of(1, 2))))) { in.readObject(); }
} catch (Exception e) {
    System.out.println(e.getClass().getName() + ": " + e.getMessage());   // the lesson
}
```

**Why people believe it:** `writeReplace` guarantees *your* streams never name `List12`. It guarantees
nothing about an attacker's.

---

## Cheat sheet

| Thing | Fact |
|---|---|
| `AbstractImmutableCollection` | `add`/`addAll`/`clear`/`remove`/`removeAll`/`removeIf`/`retainAll` → `uoe()` |
| `AbstractImmutableList` adds | `add(int,E)`, `addAll(int,…)`, `remove(int)`, `replaceAll`, `set`, `sort` |
| Why override defaults | `removeIf`/`replaceAll`/`sort` are Java 8 interface defaults, not inherited |
| `List.sort` default body | `toArray` → `Arrays.sort` → `ListIterator.set` writeback; never calls `add`/`remove` |
| `uoe()` | Factory, not a constant — fresh exception so the stack trace is accurate |
| `@jdk.internal.ValueBased` | Identity-insensitive: never lock on or `==` an immutable collection |
| Proxy class | `java.util.CollSer` — package-private **top-level**, NOT `ImmutableCollections$CollSer` |
| Proxy UID | `serialVersionUID = 6309168927139932177L`; the impl classes declare none |
| Tags | 1 `IMM_LIST`, 2 `IMM_SET`, 3 `IMM_MAP`, 4 `IMM_LIST_NULLS`; `tag & 0xff`, high 24 bits reserved |
| `IMM_LIST_NULLS` | Added for `Stream.toList()` (Java 16); re-copies to exact `Object[].class` |
| `array` field | `transient`; custom `writeObject` writes length + elements; `checkArray` gates the length |
| `readObject` on impl classes | `throw new InvalidObjectException("not serial proxy")` — reachable, verified |
| Bad tag | `default` arm → `InvalidObjectException: invalid flags 0x9` |
| `readResolve` | `List.of` / `Set.of` / `Map1`/`MapN`; re-checks nulls + duplicates in the receiver |
| Duplicate in a `Set.of` stream | `IllegalArgumentException` → caught at `:1522` → `InvalidObjectException` |
| `List.of()` round trip | Returns the **identical** shared `EMPTY_LIST` (`same=true`) |
| `Set.of` round trip | Iteration order = **receiver's** `SALT32L`, not sender's; 5 JVMs, 5 orders |
| Not serializable | `Map.of(...).keySet()` (`AbstractMap$1`), `SubList`, `ReverseOrderListView`, `KeyValueHolder` |
| `List.of(1,2)` on the wire | 142 bytes |

---

## Self-test

**Q1.** `AbstractCollection.add` already throws. Name the concrete reason `AbstractImmutableCollection`
still has to override mutators, beyond fail-fast tidiness.

<details><summary>Answer</summary>

`removeIf` (on `Collection`) and `replaceAll`/`sort` (on `List`) are **Java 8 interface default
methods**, not methods of `AbstractCollection`/`AbstractList`. `List.sort`'s default body snapshots via
`toArray()`, sorts, and writes back through a `ListIterator.set` loop — a mutation path that never
calls `add` or `remove`, so no amount of iterator-level refusal would stop it. Overridden at
`ImmutableCollections.java:152` (`removeIf`) and `261`/`263`. Secondary reason: `AbstractCollection`'s
bulk ops only throw *after* walking the iterator, so `imm.removeAll(List.of())` would quietly return
`false`.

</details>

**Q2.** You deserialize an untrusted stream claiming to be a `Set.of` with two equal elements. What
happens, and where?

<details><summary>Answer</summary>

`CollSer.readResolve` reaches `case IMM_SET: return Set.of(array);`
(`ImmutableCollections.java:1509-1510`). `Set.of` rejects duplicates with `IllegalArgumentException`,
caught at line 1522 and rethrown as `InvalidObjectException("invalid object")` with the IAE as cause.
That is the point of rebuilding through the public factory: constructor invariants are re-validated on
the receiving side, so a hostile stream cannot produce a `Set` that violates them. The same `catch`
handles nulls via its `NullPointerException` arm.

</details>

**Q3.** Why does `List.of()` deserialize to the *identical* object while `List.of(1)` does not?

<details><summary>Answer</summary>

`readResolve` calls `List.of(array)`. A zero-length array reaches `listFromTrustedArray`'s
`case 0 -> (List<E>) ImmutableCollections.EMPTY_LIST` (`ImmutableCollections.java:219`), a static
shared instance, so `==` holds. Length 1 reaches `case 1 -> new List12<>(input[0])`, a fresh
allocation. Verified: `same=true` only for `List.of()`. `EMPTY_MAP` is likewise identity-preserved via
the `array.length == 0` branch of `IMM_MAP`.

</details>

**Q4.** `Map.of("k", 1)` is serializable. Is `Map.of("k", 1).keySet()`?

<details><summary>Answer</summary>

No — `NotSerializableException: java.util.AbstractMap$1`. `MapN` does not override `keySet()`, so it
inherits the anonymous `AbstractSet` subclass from `AbstractMap`, which nobody declared
`Serializable`. The `CollSer` proxy covers the *collection*, not views derived from it:
`ImmutableCollections.SubList` and `ReverseOrderListView` are non-serializable for the same reason.
Fix: serialize `Set.copyOf(map.keySet())`.

</details>

**Q5.** Write the serial-filter pattern that allows the immutable-collection proxy through. What is the
trap?

<details><summary>Answer</summary>

`java.util.CollSer` — **not** `java.util.ImmutableCollections$CollSer`. `CollSer` is a package-private
**top-level** class declared at `ImmutableCollections.java:1371`, after the `ImmutableCollections`
class body closes; it just happens to share the file. Proven by the bytes: the serialized form of
`List.of(1,2)` contains the substring `java.util.CollSer` and no occurrence of `List12`. A filter
written against the nested name matches nothing and silently rejects (or silently fails to allow)
every immutable collection on the wire.

</details>

**Q6.** Is `List12.readObject` dead code, given that `writeReplace` means no stream ever names `List12`?

<details><summary>Answer</summary>

No. `writeReplace` controls only the streams *you* write. A stream you did not write can name any class
it likes, and an `ObjectInputStream` subclass overriding `readClassDescriptor` to substitute
`ObjectStreamClass.lookup(ImmutableCollections$List12.class)` for `java.util.CollSer` reaches it —
verified output `java.io.InvalidObjectException: not serial proxy`. Without that method the stream
would reach `defaultReadObject` and produce a `List12` with both fields null, i.e. a `List` whose
`size()` and `get(0)` are nonsense. It is a live security control.

</details>

**Q7.** What does `tag & 0xff` at `ImmutableCollections.java:1503` buy, and what happens on a tag of 9?

<details><summary>Answer</summary>

The javadoc at lines 1387-1392 reserves the **high 24 bits** of `tag` for future implementations: they
are written as zero and ignored on read, so a future JDK can add information there without breaking
older readers. Masking with `0xff` implements "ignore". A tag whose low byte is not 1–4 falls to the
`default` arm and throws `InvalidObjectException(String.format("invalid flags 0x%x", tag))`. Verified
by patching the tag int in real bytes: `java.io.InvalidObjectException: invalid flags 0x9`.

</details>

**Q8.** The `CollSer` field `array` is `transient`, yet the elements clearly cross the wire. Explain,
and name the security check on the read path.

<details><summary>Answer</summary>

`transient` keeps `defaultWriteObject`/`defaultReadObject` out of it; a hand-rolled
`writeObject`/`readObject` pair (`ImmutableCollections.java:1438-1474`) writes a length `int` followed
by the elements one at a time, and reads them back the same way. The check is
`SharedSecrets.getJavaObjectInputStreamAccess().checkArray(ois, Object[].class, len)` at line 1446,
called **before** `new Object[len]` — so a stream declaring `Integer.MAX_VALUE` elements is rejected
against `jdk.serialFilter` instead of OOMing the JVM. `readObject` also rejects a negative length
outright (`InvalidObjectException("negative length " + len)`).

</details>

**Q9.** Same `Set.of` bytes, read in four different JVMs. Same iteration order?

<details><summary>Answer</summary>

No — four different orders, all `equals`-identical. Verified: one `write` JVM produced
`[gamma, delta, beta, epsilon, alpha]`, and four separate `read` JVMs produced
`[delta, beta, epsilon, alpha, gamma]`, `[beta, delta, gamma, alpha, epsilon]`,
`[gamma, alpha, epsilon, beta, delta]`, `[alpha, epsilon, beta, delta, gamma]`. `readResolve` calls
`Set.of(array)` in the *receiving* JVM, so the table is probed under that process's `SALT32L`, derived
once per JVM from `System.nanoTime()`. The stream itself is order-stable; the receiver re-shuffles.
`SALT32L`/`REVERSE` affect iteration order only, never `probe`, so `contains` and `equals` are
unaffected.

</details>

**Q10.** Which classes in the immutable family declare a `serialVersionUID`, and why is that the right
design?

<details><summary>Answer</summary>

Only `CollSer` (`6309168927139932177L`, `ImmutableCollections.java:1373`). `List12`, `ListN`, `SetN`,
`Map1`, `MapN` declare none, because none of them is ever *written* — `writeReplace` substitutes the
proxy first, and their `readObject` refuses to be read. Since the implementation classes never appear
in the stream, their layout is free to change in any release, and only the proxy's single UID and its
documented `@serialData` form constitute the compatibility contract. That is the entire payoff of the
serial-proxy pattern: the wire format is decoupled from the class layout.

</details>

---

**Leaves covered:** 3.12.13–3.12.14 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** D-122
**Target version:** Java 21 LTS
**Lines:** 713
