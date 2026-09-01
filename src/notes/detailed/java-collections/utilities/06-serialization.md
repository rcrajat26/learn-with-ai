# 02 Java Collections — Utility surfaces — INTERMEDIATE (§2.16)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [utilities/05-streams-and-collectors.md](05-streams-and-collectors.md) · Next: [utilities/07-third-party.md](07-third-party.md)

## §2.16 Serialization of collections

Serialization is where the collections framework's internal representation
leaks into a wire format that must survive JVM restarts, JVM version
upgrades, and — if you are not careful — attackers. Four things happen at
once: which collection types even support serialization; how mutable
implementations hand-roll a compact wire format instead of the default
reflective one; how JDK 9+ immutable collections hide their internal
implementation classes behind a single serial proxy; and why
`HashMap.readObject` re-invoking `hashCode()` on every deserialized key is
a foothold for deserialization gadget chains.

---

## Concept 1 — Which collections are `Serializable`, and why the boundary is where it is (2.16.1)

**[BOTH]**

### 1. What it is

`Serializable` is a marker interface (no methods) that `ObjectOutputStream`
checks for via `instanceof` before it will write an object. Most concrete
collection classes implement it directly. Two categories do **not**, on
purpose:

| Type | `Serializable`? | Why |
|---|---|---|
| `ArrayList`, `LinkedList`, `HashMap`, `HashSet`, `TreeMap`, `TreeSet`, `ArrayDeque` | Yes | Concrete, general-purpose containers; serialization is a first-class feature. |
| `Arrays.asList(...)` result (`Arrays$ArrayList`) | Yes | Implements `Serializable`; backed by the caller's array, which is itself serialized. |
| `Collections.unmodifiableList/Set/Map(...)`, `synchronizedList/Map(...)` wrappers | Yes | Wrapper classes implement `Serializable` and delegate to the wrapped collection (plus, for `synchronized*`, the mutex). |
| `List.of(...)`, `Set.of(...)`, `Map.of(...)` (JDK 9+ immutable collections) | Yes, but only via a serial proxy (`CollSer`) — see Concept 4. | Deliberately hides the private implementation class from the stream. |
| `map.keySet()`, `map.values()`, `map.entrySet()` | **No** | These are *views* — live windows onto the backing map, not independent objects, with no independent identity to reconstruct on the far side of a stream. The JDK avoids the ambiguity by not implementing `Serializable` on the view classes at all. |
| `Collections.newSetFromMap(...)`, `Collections.checkedList(...)` view family | Mixed | `Serializable` only if the backing collection is. |

### 2–3. Problem it solves / API surface

Without the marker check, `writeObject` would throw
`NotSerializableException` deep inside a stream that has already partially
written other objects, corrupting the stream. The interface lets the
*caller* find out synchronously, and lets authors declare intent
explicitly rather than accidentally.

```java
public interface Serializable {}
```

Nothing to call — the contract is entirely "implements this or doesn't."
`writeObject`/`readObject`/`writeReplace`/`readResolve` are *hooks*
recognized via reflection when present, not part of the interface itself.

### 4–5. Complexity / thread-safety

Cost lives in whichever `writeObject` is invoked (Concepts 2–3), O(n) in
live elements. Serializing a collection concurrently mutated by another
thread is unsafe unless the collection guards against it (`ArrayList`'s
`ConcurrentModificationException` check, Concept 2) or is inherently
thread-safe (`ConcurrentHashMap`, `CopyOnWriteArrayList`).

### 6–7. When to use / common bugs

Use default `Serializable` collections for caches, session state, or
trusted IPC payloads. Avoid serializing views (`keySet()`, `entrySet()`) —
copy into a concrete collection first. Avoid Java serialization entirely
across trust boundaries (2.16.7). Common bug: `NotSerializableException`
at write time because a value stored inside an otherwise-serializable
`HashMap` doesn't itself implement `Serializable`.

**Pitfall:** Assuming `map.keySet()` is serializable because `map` is. It
is not — the view class never implements the interface.

### 8. Interview angle

**Interview:** "Is `Arrays.asList(1,2,3)` serializable?" — Yes; the L5+
signal is explaining *why the question is a trap*: people confuse it with
`List.of(...)`, whose serialized form is a `CollSer` proxy, not the list
class itself. Follow-up: "is `entrySet()` serializable?" — no, and
explaining view semantics (no independent snapshot contract) is the bar.

---

## Concept 2 — Custom serialization: write only what's live, rebuild structure on read (2.16.2, 2.16.3) `[SOURCE]` `[PROVE]`

**[BOTH]**

### 1. What it is

`ArrayList` and `HashMap` both hand-write their serial form via
`writeObject`/`readObject` instead of relying on the default reflective
mechanism, and both follow the same principle: **serialize the logical
contents, not the physical layout.** `ArrayList`'s backing array
(`elementData`) is over-allocated capacity, most of it unused; `HashMap`'s
backing array is a bucket table whose layout is a function of `hashCode()`
values that may not be stable across JVM versions. Neither field is written
directly — both are `transient` — and both classes provide their own
`writeObject`/`readObject` pair to control exactly what goes on the wire.

### 2. Problem it solves

If `elementData` were serialized by default reflection, an `ArrayList` of
size 3 with capacity 10 would write 10 array slots (7 wasted `null`s) and
tie the serial form to an internal growth policy that has changed across
releases. `HashMap`'s bucket array has a sharper problem: writing the table
directly would freeze in *bucket assignment*, derived from `hashCode()` at
write time. If the reading JVM computes different hash codes for the same
objects (Concept 3), a raw table dump deserializes into a structurally
broken map. Writing entries and re-`put`-ting on read sidesteps this — the
table rebuilds fresh, using whatever hash codes are current at read time.

### 3. API surface — `ArrayList` (JDK 21, `java.util.ArrayList`)

```java
// field declaration
transient Object[] elementData; // non-private to simplify nested class access

@java.io.Serial
private void writeObject(java.io.ObjectOutputStream s)
    throws java.io.IOException {
    // Write out element count, and any hidden stuff
    int expectedModCount = modCount;
    s.defaultWriteObject();

    // Write out size as capacity for behavioral compatibility with clone()
    s.writeInt(size);

    // Write out all elements in the proper order.
    for (int i=0; i<size; i++) {
        s.writeObject(elementData[i]);
    }

    if (modCount != expectedModCount) {
        throw new ConcurrentModificationException();
    }
}
```

Line-by-line: `s.defaultWriteObject()` writes the non-transient fields —
just `size`, since `elementData` is `transient` and skipped. `s.writeInt(size)`
writes the count a second time, deliberately, under the historical name
"capacity" for `clone()`-compatibility with old serial forms. The loop then
writes exactly `size` elements — the live ones — never touching unused
slots beyond `size`. The `modCount` check before/after guards against
another thread structurally mutating the list mid-write; if it changes,
the write fails loudly with `ConcurrentModificationException`.

```java
@java.io.Serial
private void readObject(java.io.ObjectInputStream s)
    throws java.io.IOException, ClassNotFoundException {

    // Read in size, and any hidden stuff
    s.defaultReadObject();

    // Read in capacity
    s.readInt(); // ignored

    if (size > 0) {
        // like clone(), allocate array based upon size not capacity
        SharedSecrets.getJavaObjectInputStreamAccess().checkArray(s, Object[].class, size);
        Object[] elements = new Object[size];

        // Read in all elements in the proper order.
        for (int i = 0; i < size; i++) {
            elements[i] = s.readObject();
        }

        elementData = elements;
    } else if (size == 0) {
        elementData = EMPTY_ELEMENTDATA;
    } else {
        throw new java.io.InvalidObjectException("Invalid size: " + size);
    }
}
```

The `s.readInt()` for the historical "capacity" int is explicitly ignored —
the array is allocated at exactly `size`; there is no over-allocation on
the deserialized instance until the list grows again. `checkArray` is a
JDK-internal guard defending against maliciously huge length values
inflating memory before the real elements are read, validating the
requested size against the stream's available data before allocating.

### 4. API surface — `HashMap` (JDK 21, `java.util.HashMap`)

```java
@java.io.Serial
private void writeObject(java.io.ObjectOutputStream s)
    throws IOException {
    int buckets = capacity();
    // Write out the threshold, loadfactor, and any hidden stuff
    s.defaultWriteObject();
    s.writeInt(buckets);
    s.writeInt(size);
    internalWriteEntries(s);
}
```

`s.defaultWriteObject()` writes `loadFactor` and `threshold` (both
non-transient). `buckets` (current table length) and `size` are then
written explicitly, followed by `internalWriteEntries`, which walks the
live `Node` chain and writes each key then value — not the table array
itself, not any bucket indices.

```java
@java.io.Serial
private void readObject(ObjectInputStream s)
    throws IOException, ClassNotFoundException {

    ObjectInputStream.GetField fields = s.readFields();

    // Read loadFactor (ignore threshold)
    float lf = fields.get("loadFactor", 0.75f);
    if (lf <= 0 || Float.isNaN(lf))
        throw new InvalidObjectException("Illegal load factor: " + lf);

    lf = Math.clamp(lf, 0.25f, 4.0f);
    HashMap.UnsafeHolder.putLoadFactor(this, lf);

    reinitialize();

    s.readInt();                // Read and ignore number of buckets
    int mappings = s.readInt(); // Read number of mappings (size)
    if (mappings < 0) {
        throw new InvalidObjectException("Illegal mappings count: " + mappings);
    } else if (mappings > 0) {
        double dc = Math.min(
            Math.ceil(mappings / (double)lf),
            (double) MAXIMUM_CAPACITY);
        int cap = (dc < DEFAULT_INITIAL_CAPACITY)
            ? DEFAULT_INITIAL_CAPACITY
            : tableSizeFor((int) dc);
        float ft = (float) cap * lf;
        threshold = (cap < MAXIMUM_CAPACITY && ft < MAXIMUM_CAPACITY)
            ? (int) ft : Integer.MAX_VALUE;
        Node<K,V>[] tab = (Node<K,V>[]) new Node[cap];
        table = tab;

        // Read the keys and values, and put the mappings in the HashMap
        for (int i = 0; i < mappings; i++) {
            K key = (K) s.readObject();
            V value = (V) s.readObject();
            putVal(hash(key), key, value, false, false);
        }
    }
}
```

The written *threshold* is read via `GetField` but explicitly ignored; it
is recomputed from `mappings` and `loadFactor` instead, because the correct
table size is a function of how many entries are about to be inserted, not
a stale value from a possibly-different JVM. `s.readInt()` for buckets is
likewise read and discarded. The critical line is the loop: `hash(key)`
and `putVal(...)` are called **fresh**, on the deserializing JVM, for every
entry — this is the mechanism, not a side detail, and it is exactly what
makes the Concept 3 trap and the 2.16.7 gadget-chain foothold possible:
deserialization *executes* `key.hashCode()` for attacker- or
version-controlled objects.

### 5–6. Complexity / thread-safety

Both O(n) in live elements/entries for read and write — no wasted work
proportional to capacity. Neither `writeObject` is synchronized; concurrent
structural modification during serialization is a correctness bug the
caller must avoid (`ArrayList` detects it via `modCount`; `HashMap` has no
equivalent guard).

### 7–8. Insight / interview angle

**Insight:** `HashMap` re-`put`-ting instead of restoring the raw table is
not merely "cleaner code" — it is required correctness. Copied verbatim,
every entry would sit in the bucket matching the writer JVM's hash,
silently wrong if a key type's `hashCode()` differs on the reader (Concept
3). Re-`put`-ting recomputes placement using the *current* JVM's
`hashCode()`, making the map self-healing with respect to hash-code drift,
at the cost of real work (potential resizes) on every deserialization.

**Interview:** "Why is `ArrayList.elementData` transient?" — the L5+ answer
names both reasons: capacity isn't logically part of the list's serialized
identity, *and* writing it directly would leak a growth-factor detail that
has changed across releases. Follow-up: "why does `HashMap` re-`put`
instead of restoring the table?" separates candidates who know the
mechanic from those who understand why it must work that way (Concept 3).

---

## Concept 3 — The cross-JVM `hashCode()` drift trap (2.16.4) `[TRAP]`

**[BOTH]**

### 1. What it is

Because `HashMap.readObject` calls `hash(key)` and `putVal(...)` fresh on
the deserializing JVM (Concept 2), a `HashMap` serialized on one JVM and
deserialized on another is structurally correct only if every key's
`hashCode()` produces the same relative bucket distribution on both JVMs.
Normally true for JDK-provided key types (`String`, boxed numerics). **Not**
guaranteed for: keys whose class overrides `hashCode()` inconsistently
across two builds of *your own* code deployed at different times; keys
relying on `Object.hashCode()` (identity hash), which never survives
serialization meaningfully; or any key type whose `hashCode()` changed
between two library versions present on the two JVMs.

### 2. Problem it solves / why it's a trap

There is no exception thrown. The map deserializes "successfully" —
`readObject` returns a live `HashMap` — but `map.get(key)` on the receiving
JVM can return `null` for a key that is logically present. The re-put
happens at read time using the *reading* JVM's hash function consistently
for all entries, so the map itself is internally self-consistent; the real
failure is when the **caller's own `hashCode()` implementation** differs
between the writer and a later reader for the *same logical key value*
(a key class patched between deploys, or a `hashCode()` that incorporates
JVM-specific state).

**Pitfall:** Wrong — assuming a serialized `HashMap` is "just data," immune
to code changes on the reading side. Right — a custom-`hashCode()` key type
used in a persisted/transmitted `HashMap` is part of that map's
serialization contract; changing the hash algorithm for a key class breaks
any blob written with the old version and read with the new one.

### 3–7. API surface / complexity / thread-safety / when to use / common bugs

Not a standalone API — an emergent property of Concept 2's re-`put`
mechanism. Concrete failure shape: long-lived caches persisted to disk as
serialized `HashMap`s, read back after a library upgrade changed a key
class's `hashCode()`, silently return stale-looking misses instead of
throwing — more dangerous than a crash since it fails silently in prod.

### 8. Interview angle

**Interview:** "You persist a `HashMap<CustomKey, V>` to disk, ship a new
JVM version, and lookups start missing keys clearly present in the file.
What happened?" — expected chain: `readObject` re-`put`s ⇒ re-`put` calls
`hashCode()` fresh ⇒ if `CustomKey.hashCode()` changed between versions,
lookups constructed by the new code diverge from the map's re-hashed
layout. Fix: a stable, versioned `hashCode()` contract for persisted key
types, or avoid Java serialization for durable state entirely.

---

## Concept 4 — The `CollSer` serial proxy for immutable collections (2.16.6) `[SOURCE]` `[RESEARCH]`

**[BOTH]**

### 1. What it is

`List.of(...)`, `Set.of(...)`, and `Map.of(...)` (JDK 9+) are backed by
package-private implementation classes (`ImmutableCollections.List12`,
`ListN`, `Set12`, `SetN`, `Map1`, `MapN`) that the JDK deliberately never
exposes in a serialized stream. Instead, every one of them implements the
**serialization proxy pattern**: `writeReplace()` substitutes a single
shared helper object, `ImmutableCollections.CollSer`, for the actual
instance before the stream ever sees it, and the real class's own
`readObject` is defensively wired to reject direct deserialization.

### 2. Problem it solves

Two things: hiding the choice of implementation class (the JDK is free to
change `List12` vs `ListN` internals across releases without breaking
serial compatibility — the wire format only ever names `CollSer` plus a tag
plus the elements), and preventing a crafted stream from constructing a
`List12`/`MapN` instance directly, bypassing the invariants the `of(...)`
factories normally enforce (no nulls, no duplicate keys/elements).

### 3. API surface (JDK 21, `java.util.ImmutableCollections`, verified against `openjdk/jdk` `master`)

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

    @java.io.Serial
    private void writeObject(ObjectOutputStream oos) throws IOException {
        oos.defaultWriteObject();
        oos.writeInt(array.length);
        for (int i = 0; i < array.length; i++) {
            oos.writeObject(array[i]);
        }
    }

    @java.io.Serial
    private Object readResolve() throws ObjectStreamException {
        try {
            if (array == null) {
                throw new InvalidObjectException("null array");
            }
            switch (tag & 0xff) {
                case IMM_LIST:       return List.of(array);
                case IMM_LIST_NULLS: return /* factory allowing nulls */;
                case IMM_SET:        return Set.of(array);
                case IMM_MAP:
                    if (array.length == 0) return ImmutableCollections.EMPTY_MAP;
                    else if (array.length == 2)
                        return new ImmutableCollections.Map1<>(array[0], array[1]);
                    else return new ImmutableCollections.MapN<>(array);
                default:
                    throw new InvalidObjectException(String.format("invalid flags 0x%x", tag));
            }
        } catch (NullPointerException | IllegalArgumentException ex) {
            InvalidObjectException ioe = new InvalidObjectException("invalid object");
            ioe.initCause(ex);
            throw ioe;
        }
    }
}
```

`array` is itself `transient` on `CollSer` — `defaultWriteObject()` only
writes the `tag` int; the elements are written explicitly right after, so
`CollSer`'s wire format is exactly `tag, length, elements...`.
`readResolve()` — a hook distinct from `readObject`, invoked *after* the
stream has fully reconstructed the `CollSer` instance — is where substitution
back into a real immutable collection happens: it calls the same public
factories (`List.of`, `Set.of`) or a size-specialized constructor (`Map1`
for one mapping, `MapN` otherwise), so all of `of(...)`'s invariant checks
(no nulls, no duplicates) run again on deserialization — a crafted stream
cannot smuggle in an invalid immutable collection.

On the producing side, every immutable implementation class pairs a
`writeReplace()` that returns the `CollSer` with a `readObject()` that
unconditionally refuses direct deserialization. From `List12` (JDK 21,
`ImmutableCollections.java`):

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

`writeReplace()` runs *before* `writeObject` would (substituting the object
to be serialized at the very start of the write), so `List12`'s own
`readObject` throwing is unreachable in normal use — pure defense-in-depth
against a hand-crafted stream naming `List12` directly. `ListN`, `Set12`,
`SetN`, `Map1`, and `MapN` each repeat the identical pattern with their own
tag constant.

![CollSer serial proxy: writeReplace swaps the immutable collection for a CollSer carrying a tag and the elements, the stream contents, readResolve rebuilding via the factory, and readObject on the collection class itself throwing InvalidObjectException("not serial proxy")](../diagrams/D-122-collser-serial-proxy.svg)

### 4–5. Complexity / thread-safety

O(n) in element count for both directions, no structural cost beyond
writing the flat element array plus a tag int. Immutable collections have
no mutable state to race on; serialization is inherently safe to run
concurrently with reads from other threads.

### 6–7. When to use / common bugs

Use `List.of`/`Set.of`/`Map.of` freely even when serialization is in scope
— the proxy is automatic, no opt-in needed. Nothing to avoid on the caller
side; the internal implementation classes are package-private and
unreachable directly. The one observable surprise: `readResolve()`
re-validates invariants, so a hand-tampered stream with duplicate keys for
an `IMM_MAP` tag throws `InvalidObjectException`/`IllegalArgumentException`
rather than silently producing a corrupt map.

### 8. Interview angle

**Interview:** "How does `List.of(1,2,3)` serialize, given its
implementation class isn't public?" — most candidates have never looked.
The complete answer names `writeReplace`, `CollSer`, the tag scheme, and
`readResolve`, and explains *why* the indirection exists (implementation
hiding plus invariant re-validation), not just that it exists.

---

## Supporting facts (2.16.5, 2.16.9, cross-references)

**[SENIOR IC]**

**2.16.5 — `TreeMap`'s comparator must itself be serializable.** `[TRAP]`
`TreeMap` writes its `Comparator<? super K>` field (when non-null) via
default serialization of its own `writeObject` (which, like `HashMap`,
writes entries rather than tree structure directly). If that comparator is
a lambda or an anonymous class capturing a non-serializable enclosing
instance, the whole map fails with `NotSerializableException`, and the
stack trace points at the comparator, not obviously at the `TreeMap`
construction site. **Pitfall:** Wrong — `new TreeMap<>((a, b) -> a.compareTo(b))`,
a synthetic class not `Serializable` by default. Right —
`new TreeMap<>((Comparator<String> & Serializable) (a, b) -> a.compareTo(b))`
via intersection-type cast, or a named class declaring
`implements Comparator<K>, Serializable` explicitly.

**2.16.9 — `serialVersionUID` on a collection subclass you wrote.**
Any class extending a JDK collection (e.g., a custom `ArrayList<T>`
subclass) inherits `Serializable` and should declare its own explicit
`private static final long serialVersionUID`. Without one, the
compiler-derived UID is a hash of the class's structure and changes
silently on any recompilation that alters that structure — even a no-op
refactor — breaking deserialization of previously-persisted instances with
`InvalidClassException: local class incompatible`. The JDK's own collection
classes pin explicit UIDs (`ArrayList`'s is `8683452581122892189L`); apply
the same discipline to your own code.

**2.16.7 — Deserialization gadget chains through `HashMap.readObject`.**
`[X-REF 13]` `[RESEARCH]` `[STAFF]` As shown in Concept 2, `HashMap.readObject`
calls `putVal(hash(key), key, value, ...)` for every deserialized entry, so
deserializing an untrusted byte stream that claims to be a `HashMap` causes
the JVM to invoke `hashCode()` (and, on collision, `equals()`) on every
deserialized key object, using whatever concrete class the attacker named
in the stream. Because Java serialization lets the stream specify arbitrary
classpath classes as the runtime type of any field, an attacker who can
name a class whose `hashCode()`/`equals()` override triggers further
useful behavior (a step in a longer gadget chain) gets that invocation for
free, with no authentication gate — precisely the mechanism exploited by
`ysoserial`-style `HashMap` chains. This file does not cover chain
construction; the web security guide (guide 13) owns that treatment.

**2.16.8 — JSON/Jackson mapping of collection types.** `[X-REF 12]`
`[SENIOR IC]` Type erasure means a field declared `List<String> names` has,
at runtime, only the raw type `List` — the `String` element type is
compile-time-only metadata absent from the `.class` field descriptor.
Jackson's default deserializer, given a raw `Class<?>` target, cannot
recover the intended element type and falls back to `LinkedHashMap`/`Object`
guessing, wrong for anything beyond simple scalars.
`ObjectMapper.readValue(json, new TypeReference<List<String>>(){})` works
around this by capturing the generic signature through the anonymous
subclass's superclass type parameter, which the JVM *does* retain (unlike
a bare generic method call). This file does not cover `TypeReference`
internals or polymorphic type-id strategies — the API design guide
(guide 12) owns that treatment.

---

## Pitfalls

**Pitfall:** Wrong — treating a serialized `HashMap` as portable, opaque
data immune to code changes. Right — any key type with a custom
`hashCode()` used inside a persisted/transmitted `HashMap` is part of that
map's serialization contract; changing the hash algorithm is a breaking
change for old blobs (2.16.4).

**Pitfall:** Wrong — assuming `map.entrySet()` or `map.keySet()` can be
serialized because the backing map can. Right — view classes never
implement `Serializable`; copy into a concrete collection first (2.16.1).

**Pitfall:** Wrong — constructing a `TreeMap` with a lambda comparator and
being surprised by `NotSerializableException` on `writeObject`. Right —
lambdas are not `Serializable` by default; use an intersection-type cast or
a named `Comparator` class implementing `Serializable` (2.16.5).

**Pitfall:** Wrong — leaving a hand-written `Serializable` collection
subclass without an explicit `serialVersionUID`, trusting the compiler's
derived value to stay stable across recompiles. Right — declare it
explicitly; a structurally-triggered UID change breaks every previously
persisted instance (2.16.9).

## Cheat sheet

| Class | `Serializable`? | Custom `writeObject`/`readObject`? | What's `transient` and why |
|---|---|---|---|
| `ArrayList` | Yes | Yes (2.16.2) | `elementData` — avoid writing unused capacity slots; wire format is `size` + live elements only. |
| `HashMap` | Yes | Yes (2.16.3) | Bucket `table` — layout depends on `hashCode()` at write time, which may not match the reading JVM; entries are re-`put` on read instead. |
| `LinkedList` | Yes | Yes | Internal node links — writes size + elements in order, rebuilds the doubly-linked structure on read. |
| `TreeMap`/`TreeSet` | Yes | Yes | Tree node structure — writes comparator + entries in sorted order, rebuilds the red-black tree on read; comparator must itself be `Serializable` (2.16.5). |
| `Collections.unmodifiableList(...)` etc. | Yes | No (delegates) | Nothing — wrapper just serializes the backing collection reference. |
| `map.keySet()` / `.values()` / `.entrySet()` | **No** | N/A | View has no independent snapshot identity (2.16.1). |
| `List.of(...)` / `Set.of(...)` / `Map.of(...)` | Yes, via proxy | `writeReplace` → `CollSer`; own `readObject` throws | Implementation class identity — hidden behind `CollSer` tag + flat element array (2.16.6). |
| Your custom `Serializable` subclass | Depends | Only if you add it | Declare explicit `serialVersionUID` regardless (2.16.9). |

## Self-test

<details><summary>1. Why is `ArrayList.elementData` declared `transient` if `ArrayList` still needs to serialize its elements?</summary>

Because `transient` only exempts the field from *default* reflective
serialization; `ArrayList` supplies its own `writeObject`/`readObject` pair
that writes exactly the live elements (indices `0..size-1`), skipping
unused capacity and decoupling the wire format from the internal growth
policy.

</details>

<details><summary>2. Why does `HashMap.readObject` call `putVal(...)` for every entry instead of restoring the bucket table directly?</summary>

Bucket placement is a function of `hashCode()`, which may differ between
the writing and reading JVM (different hash algorithm versions for a key
class, etc.). Re-`put`-ting recomputes placement fresh using the *current*
JVM's `hashCode()`, keeping the table structurally correct regardless of
hash-code drift.

</details>

<details><summary>3. Is `map.keySet()` serializable if `map` is a `Serializable HashMap`?</summary>

No. Key/value/entry views never implement `Serializable` — they are live
windows onto the backing map with no independent snapshot identity. Copy
into a concrete `HashSet`/`ArrayList` first if a serializable copy is
needed.

</details>

<details><summary>4. What breaks if a `TreeMap`'s comparator is a plain lambda?</summary>

Lambdas are not `Serializable` by default, so serializing the `TreeMap`
throws `NotSerializableException` pointing at the comparator. Fix with an
intersection-type cast `(Comparator<K> & Serializable)` or a named class
implementing both interfaces.

</details>

<details><summary>5. How does `List.of(1, 2, 3)` serialize, given its implementation class (`ImmutableCollections.ListN`) is package-private, and what happens if a hand-crafted stream tries to deserialize `ListN` directly?</summary>

`writeReplace()` substitutes a `CollSer` instance (tag `IMM_LIST` plus the
element array) before the stream sees `ListN`. On read, `CollSer.readResolve()`
calls `List.of(array)` again, re-running invariant checks. `ListN`'s own
`readObject()` unconditionally throws `InvalidObjectException("not serial
proxy")` as a defense-in-depth guard against bypassing the proxy.

</details>

<details><summary>6. Why is deserializing an untrusted `HashMap` byte stream a security risk beyond "it might contain bad data"?</summary>

`readObject` invokes `hashCode()` (and potentially `equals()`) on every
deserialized key, using whatever class the stream names as that key's
runtime type. An attacker who can name a class whose `hashCode()`/`equals()`
triggers further useful behavior gets that invocation for free — the
mechanism behind `ysoserial`-style `HashMap` chains (guide 13).

</details>

<details><summary>7. What's the risk of omitting an explicit `serialVersionUID` on a `Serializable` subclass you wrote?</summary>

The compiler derives one from a structural hash of the class. Any
recompilation that changes that structure — even a behavior-neutral
refactor — silently changes the derived UID, and deserializing an older
persisted instance then fails with `InvalidClassException: local class
incompatible`.

</details>

---

**Leaves covered:** 2.16.1-2.16.9 (9 leaves)
**Leaves deferred:** none
**Diagrams included:** D-122
**Target version:** Java 21 LTS
**Lines:** 663
