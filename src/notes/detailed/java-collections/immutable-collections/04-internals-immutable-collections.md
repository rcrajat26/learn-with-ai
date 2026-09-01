# 02 Java Collections — Immutability and views — INTERNALS (§3.12.1–3.12.5)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/03c-null-queries-and-guava.md](03c-null-queries-and-guava.md) · Next: [immutable-collections/04b-internals-open-addressing-and-salt.md](04b-internals-open-addressing-and-salt.md)

Bare `:NNN` citations are `java.util.ImmutableCollections` from JDK 21.0.7. Transcripts: `openjdk
21.0.7 2025-04-15 LTS` (build `21.0.7+8-LTS-245`, HotSpot 64-bit Server VM), macOS arm64.

---

## The family map, before the streets

`List.of`, `Set.of` and `Map.of` are eleven-armed factory ladders that all funnel into one
package-private class, `java.util.ImmutableCollections`. Nothing in that class is public; you
can never name `List12` in source. The shape is three abstract bases and six concrete leaves:

| Type | Extends | Concrete subclasses | Role |
|---|---|---|---|
| `AbstractImmutableCollection<E>` | `AbstractCollection<E>` (`:145`) | — | Throws `uoe()` from `add`, `addAll`, `clear`, `remove`, `removeAll`, `removeIf`, `retainAll` (`:147-153`) |
| `AbstractImmutableList<E>` | `AbstractImmutableCollection<E>`, `implements List<E>, RandomAccess` (`:254-255`) | `List12`, `ListN`, `SubList`, `ListItr` support | Adds the `List`-only mutators to the throw set; supplies `equals`/`hashCode`/`contains`/`subList`/`reversed` |
| `AbstractImmutableSet<E>` | `AbstractImmutableCollection<E>`, `implements Set<E>` (`:752-753`) | `Set12`, `SetN` | Set-contract `equals`/`hashCode` |
| `AbstractImmutableMap<K,V>` | `AbstractMap<K,V> implements Serializable` (`:1073`) | `Map1`, `MapN` | Throws from all thirteen `Map` mutators (`:1074-1086`) plus an optimised `getOrDefault` |

`AbstractImmutableCollection`, `AbstractImmutableList`, `AbstractImmutableSet`, `List12`,
`ListN`, `Set12` and `SetN` all carry `@jdk.internal.ValueBased`. `Map1` and `MapN` do not, and
`:1103` says why: `// Not a jdk.internal.ValueBased class; disqualified by fields in superclass AbstractMap`.
`AbstractMap` carries the mutable cached `keySet`/`values` fields, so the map implementations
cannot promise the identity-agnosticism `@ValueBased` asserts. Practical consequence: never
synchronize on or identity-compare a `List.of`/`Set.of` result.

The mutator-throwing story, `CollSer` serialization and the view classes are the next file's:
[04c-internals-mutators-serialization-and-views.md](04c-internals-mutators-serialization-and-views.md).
Open addressing, `probe()` and `SALT32L` are
[04b-internals-open-addressing-and-salt.md](04b-internals-open-addressing-and-salt.md).

---

## The overload ladder and the trusted-array contract (3.12.1, 3.12.4)

### Mental model first

Think of `List.of` as a **coat check with three counters**. Arity 0–2 needs no hanger at all —
the coats hang on hooks built into the counter itself (fields). Arity 3–10 gets one hanger, and
because the factory built that hanger itself and nobody else has the ticket, it can keep it
forever. The `of(E...)` counter is the one where **you** brought your own hanger — so the clerk
transfers the coats onto a fresh hanger before filing it, because you could walk off with yours
and swap what is on it. That third counter is the whole reason the first eleven exist.

### Why it exists

Before Java 9 the idiom was `Collections.unmodifiableList(Arrays.asList(a, b, c))` — three
objects for a three-element constant, plus a *live view* onto an array the caller still held.
`List.of` (Java 9, JEP 269) set out to allocate nothing it did not need and alias nothing the
caller can reach. The overload ladder is the allocation half; `listFromTrustedArray` versus
`listFromArray` is the aliasing half.

### The syllabus claim, corrected

Leaf 3.12.1 says the overloads exist "to avoid array allocation for small lists". **That is only
true for arity 0–2.** `List.java:971` and its siblings up to `:1129` delegate to
`ImmutableCollections.listFromTrustedArray(Object... input)` at `:212` — and *that method is itself
varargs*. An `Object[n]` is still allocated, just at the library call site instead of the user's.
What arity 3–10 avoids is the **second** array. The honest three-way arithmetic `[NUM]`:

| Path | Source | Arrays allocated | Retained |
|---|---|---|---|
| `List.of()` | `List.java:922` → `EMPTY_LIST` singleton | **0** | nothing new at all |
| `List.of(a)`, `List.of(a,b)` | `List.java:936`, `:953` → `new List12<>(…)` | **0** | one `List12` object, two fields |
| `List.of(a,b,c)` … `of(a..j)` | `List.java:971-1129` → `listFromTrustedArray` (`:212`) | **1** (the varargs array) | that same array, no copy |
| `List.of(E... )` with ≥3 elements | `List.java:1161` → `listFromArray` (`:187`) | **2** (caller's + `tmp`) | only `tmp` |

So: 0 arrays, 1 array, 2 arrays. Not "no array below 11".

### How it works — the two factory bodies

The untrusted path, in full (`:186-195`):

```java
    @SafeVarargs
    static <E> List<E> listFromArray(E... input) {
        // copy and check manually to avoid TOCTOU
        @SuppressWarnings("unchecked")
        E[] tmp = (E[])new Object[input.length]; // implicit nullcheck of input
        for (int i = 0; i < input.length; i++) {
            tmp[i] = Objects.requireNonNull(input[i]);
        }
        return new ListN<>(tmp, false);
    }
```

Line by line. `@SafeVarargs` suppresses the unchecked-generic-array warning at every call site.
`new Object[input.length]` dereferences `input`, which is where the NPE for `List.of((E[])null)`
comes from — the comment "implicit nullcheck" means no explicit `requireNonNull(input)` is needed
because the length read already throws. The array is created as `Object[]` and cast to `E[]`: at
runtime the component type must be `Object`, never `String`, or `ListN` could later throw
`ArrayStoreException` on internal writes. The loop does **two things at once** — it copies
`input[i]` into `tmp[i]` *and* null-checks it, and that single-read-per-slot is the TOCTOU defence.
Finally `false` is `allowNulls`; see 3.12.3.

**Why a library that trusted the caller's array would be exploitable** `[PROVE]`. Suppose
`listFromArray` instead did `for (e : input) requireNonNull(e); return new ListN<>(input, false);`
— check, then adopt. Between the check and the adopt, another thread holding the same array
writes `input[0] = null`, and the list is now a `ListN` with `allowNulls == false` containing a
null. Not a cosmetic lie: `ListN.indexOf` at `:722` short-circuits `o == null` to an NPE *because
it has been promised no slot is null*, and `AbstractImmutableList.contains` at `:329-331` is
`indexOf(o) >= 0`, so `list.contains(null)` throws while `list.get(0)` returns null. Worse,
`listCopy` at `:169` uses exactly this flag to decide whether `List.copyOf` may **return the
argument unchanged**:

```java
        if (coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)) {
            return (List<E>)coll;
```

A forged `allowNulls == false` list propagates through every `List.copyOf` in the process. The fix
is not a second check — check-then-check is still TOCTOU — but to copy first and validate the copy,
which nobody else can write to. Reading each slot exactly once is the point.

The trusted path (`:210-224`):

```java
    @SuppressWarnings("unchecked")
    static <E> List<E> listFromTrustedArray(Object... input) {
        assert input.getClass() == Object[].class;
        for (Object o : input) { // implicit null check of 'input' array
            Objects.requireNonNull(o);
        }

        return switch (input.length) {
            case 0  -> (List<E>) ImmutableCollections.EMPTY_LIST;
            case 1  -> (List<E>) new List12<>(input[0]);
            case 2  -> (List<E>) new List12<>(input[0], input[1]);
            default -> (List<E>) new ListN<>(input, false);
        };
    }
```

Three things to notice. First, the parameter is `Object...`, not `E...`, and the Javadoc at
`:198-208` says why: "so that a varargs call doesn't accidentally create an array of some class
other than `Object[].class`." Declare it `E...` and `listFromTrustedArray(s1, s2, s3)` on `String`s
would synthesize a `String[3]`, which `ListN` cannot safely hold; the `assert` documents that
invariant. Second, there is **no copy** — `input` becomes `ListN`'s backing store directly, legal
precisely because the varargs array was synthesized at the call site and no reference escapes.
Third, this method still re-specialises to `List12` for arity 1 and 2, so the arity-3-and-up arms
share one code path with the small cases.

The untrusted entry point `List.of(E... elements)` (`List.java:1159-1174`) re-specialises the same
way: `switch (elements.length)` with `case 0` returning `EMPTY_LIST`, `case 1`/`case 2`
constructing `List12` from `elements[0]`/`elements[1]`, and only `default` calling
`listFromArray(elements)`. So `List.of(someArrayOfLength2)` yields a `List12` and allocates **no**
internal array even though the caller's array is untrusted — copying two fields out of it *is* the
copy. Only `default` pays for a defensive array.

**Insight:** `Set.of(E...)` (`Set.java:695-708`) needs no trusted/untrusted split at all — its
`default` arm is plain `new SetN<>(elements)`, because `SetN`'s constructor (`:917-931`) allocates
its own `EXPAND_FACTOR * input.length` table and reads each input slot exactly once into it. The
caller's array is never retained, so there is nothing to defend. Same TOCTOU rule, different
storage strategy.

### A minimal concrete example

```java
import java.util.*;

public class Aliasing {
    public static void main(String[] args) {
        String[] mine = { "a", "b", "c" };
        List<String> untrusted = List.of(mine);   // List.of(E...) -> listFromArray -> copy
        mine[0] = "MUTATED";
        System.out.println("caller array now = " + Arrays.toString(mine));
        System.out.println("List.of(array)   = " + untrusted + "   (defensive copy held)");

        List<String> trusted = List.of("a", "b", "c");
        System.out.println("toArray twice, same array? "
                + (trusted.toArray() == trusted.toArray()));

        try {
            List.of("a", null);                              // List12 constructor
        } catch (NullPointerException e) {
            System.out.println("List.of(a,null)          -> NPE from List12 ctor");
        }
        try {
            List.of("a", "b", null);                         // listFromTrustedArray loop
        } catch (NullPointerException e) {
            System.out.println("List.of(a,b,null)        -> NPE from listFromTrustedArray");
        }
        try {
            List.of(new String[] { "a", "b", "c", null });    // listFromArray loop
        } catch (NullPointerException e) {
            System.out.println("List.of(new String[]{..null}) -> NPE from listFromArray");
        }
    }
}
// Real output:
//   caller array now = [MUTATED, b, c]
//   List.of(array)   = [a, b, c]   (defensive copy held)
//   toArray twice, same array? false
//   List.of(a,null)          -> NPE from List12 ctor
//   List.of(a,b,null)        -> NPE from listFromTrustedArray
//   List.of(new String[]{..null}) -> NPE from listFromArray
```

The real output is the trailing comment. The fuller run also contrasted `Arrays.asList(other)`, a
*view*, which printed `[MUTATED, y, z]` in step with the caller's array. Every throwing call sits
inside `try`/`catch`, so the program runs to completion; the caught exception *is* the lesson.
Note the three distinct NPE origins — one per arity band.

### The gotcha

`toArray()` on a `ListN` is `Arrays.copyOf(elements, elements.length)` (`:704-707`) — a fresh array
every call, as the `false` above shows. The no-copy guarantee is strictly inbound; there is no
supported way to obtain the internal array, which is what makes trusting it safe.

### Definition

> The `List.of` overload ladder exists so that arity 0–2 allocates no array at all and arity
> 3–10 allocates exactly one — the varargs array itself, adopted as backing store by
> `listFromTrustedArray` — while the untrusted `of(E...)` arm must route through
> `listFromArray`, which copies-and-checks in a single pass to close a TOCTOU hole.

**Interview:** "Does `List.of(a,b,c)` allocate an array?" — Yes, one: the varargs array, which
becomes `ListN`'s backing store with no defensive copy. Only arity 0–2 allocates none, and only
the explicit-array form allocates two.

---

## `List12`: two fields and a real sentinel (3.12.2)

### Mental model first

`List12` is a **list with no list in it**. No array, no length, no capacity — just two
reference-sized slots on the object itself, and a marker object meaning "the second slot is not in
use". Size is not stored; it is *computed* by comparing the second slot against that marker.

### Why it exists

One- and two-element immutable lists are overwhelmingly the common case (a pair of headers, a
singleton config value, a two-key composite), and each would otherwise cost a second heap object
with its own header and length field. `List12` collapses that to one object.

### How it works — the source

Fields (`:552-561`):

```java
    @jdk.internal.ValueBased
    static final class List12<E> extends AbstractImmutableList<E>
            implements Serializable {

        @Stable
        private final E e0;

        @Stable
        private final Object e1;
```

Exactly two fields, no array, no `size`. `@Stable` (`jdk.internal.vm.annotation.Stable`) tells
C2 that once the field is written non-default it will never change, licensing constant-folding of
reads through a constant `List12` — the reason `List.of("x").get(0)` can fold away entirely in
JIT-compiled code.

**`e0` is typed `E`; `e1` is typed `Object`.** Not sloppiness: `e1` must hold the sentinel, and the
sentinel is a bare `java.lang.Object`, not an `E`. Typing the field `E` would force an unchecked
cast on every *write* of the sentinel and make the declared type a lie. The JDK pushes the cast to
the one place a caller can observe an element instead — `get`.

The sentinel itself is declared `private static final Object EMPTY;` at `:95` and initialised
`EMPTY = new Object();` at `:104`. The constructors (`:563-572`):

```java
        List12(E e0) {
            this.e0 = Objects.requireNonNull(e0);
            // Use EMPTY as a sentinel for an unused element: not using null
            // enables constant folding optimizations over single-element lists
            this.e1 = EMPTY;
        }

        List12(E e0, E e1) {
            this.e0 = Objects.requireNonNull(e0);
            this.e1 = Objects.requireNonNull(e1);
        }
```

The comment states the reason outright, and it is the interesting part: **`null` is the default
value of a reference field, and `@Stable` only licenses folding of a *non-default* value.** Had the
marker been `null`, `e1` would sit at its default for every single-element list, `@Stable` would
give C2 nothing, and `size()` could not fold to the constant 1. A distinct non-null object keeps
`e1` always non-default and therefore always foldable. `EMPTY` is also CDS-archived alongside the
empty singletons (`:109-116`), so it survives into the shared archive.

Note `List12(E e0, E e1)` narrows the second parameter to `E` even though the field is `Object`,
so user code physically cannot pass the sentinel in. Everything else reads the sentinel by
**identity**, never `equals` (`:574-592`):

```java
        @Override
        public int size() {
            return e1 != EMPTY ? 2 : 1;
        }

        @Override
        public boolean isEmpty() {
            return false;
        }

        @Override
        @SuppressWarnings("unchecked")
        public E get(int index) {
            if (index == 0) {
                return e0;
            } else if (index == 1 && e1 != EMPTY) {
                return (E)e1;
            }
            throw outOfBounds(index);
        }
```

`size()` is a single reference comparison. `isEmpty()` is a constant `false` — a `List12` can never
be empty, because both constructors `requireNonNull(e0)`. `get(1)` on a one-element list falls
through both branches to `outOfBounds(index)` (`:339-340`), which builds `"Index: 1 Size: 1"` by
calling `size()`. `(E)e1` is the deferred cast: erased to a checkcast against `Object`, free at
runtime, the syntactic price of the `Object`-typed field. `EMPTY` is consulted at `:589` (`get`),
`:600`/`:610` (`indexOf`, `lastIndexOf`), `:626`, `:635` — all `==`, never `.equals`.

### The diagram

![List12 as a single object with fields e0 and e1 and no backing array at all, against an ArrayList object plus its separate Object[], with the byte arithmetic on both](../diagrams/D-121-listof-vs-arraylist-memory.svg)

Look at the object count, not the byte totals: the left side is **one** heap object, the right
side is **two** with an indirection between them.

The arithmetic, assuming **64-bit HotSpot with compressed oops** (the default under 32 GB heap;
12-byte object header, 4-byte references, 8-byte alignment) `[NUM]`:

- `List.of(a, b)` → `List12`: 12 B header + 4 B `e0` + 4 B `e1` = 20 B, padded to **24 B**. No
  second object.
- `new ArrayList<>(List.of(a, b))`: the collection constructor at `ArrayList.java:180-192` runs
  `elementData = Arrays.copyOf(a, size, Object[].class)` with `size == 2`, so the array is sized to
  **exactly 2**. `ArrayList` object = 12 B header + 4 B `modCount` (from `AbstractList`) + 4 B
  `size` + 4 B `elementData` = 24 B. Array = 12 B header + 4 B length + 2 × 4 B = 24 B.
  **Total 48 B, zero slack.**
- `var l = new ArrayList<String>(); l.add(a); l.add(b);` is a *different* expression: the first
  `add` grows the array to `DEFAULT_CAPACITY = 10` (`ArrayList.java:118`). Array = 12 + 4 + 10 × 4
  = 56 B. **Total 80 B, eight slots of slack.**

So 24 B versus 48 B for the copy-construction form, 24 B versus 80 B for empty-then-`add`. Layout
computations, not measurements — no `Runtime` reading was taken.

### The gotcha

`List12` has no `size` field, so `size()` is fast but `List.of(x)` and `List.of(x, y)` are the
*same class* — `getClass()` cannot tell you the size, `instanceof` cannot distinguish them, and any
reflective inspection must read `e1` and compare it to a sentinel it cannot name.

### Definition

> `List12<E>` is the immutable one-or-two element list: a single heap object holding `e0`
> (typed `E`) and `e1` (typed `Object` so it can hold the shared `EMPTY` sentinel from `:95`),
> with `size()` derived by `e1 != EMPTY` and no backing array anywhere.

**Interview:** "Why is `List12.e1` not typed `E`?" — Because the absent-element sentinel is a plain
`Object`, not an `E`; the field must be `Object` to hold it, and the unchecked cast is paid once in
`get` rather than on every write.

---

## `ListN`: an array plus one boolean (3.12.3)

### Mental model first

`ListN` is an array wrapper carrying **one bit of provenance** — whether the array it was handed
may contain nulls. All its null behaviour follows from that bit, which the factory sets, not the
data.

### How it works — the source

```java
    @jdk.internal.ValueBased
    static final class ListN<E> extends AbstractImmutableList<E>
            implements Serializable {

        @Stable
        private final E[] elements;

        @Stable
        private final boolean allowNulls;

        // caller must ensure that elements has no nulls if allowNulls is false
        private ListN(E[] elements, boolean allowNulls) {
            this.elements = elements;
            this.allowNulls = allowNulls;
        }
```

**Correction to the index row and leaf 3.12.3:** the field is declared `private final E[] elements`
at `:663`, not `Object[] elements`. The runtime component type is always `Object` — every caller
constructs `new Object[…]` and casts — but the *declaration* is `E[]`, which is why `get` needs no
cast. Reflection confirms both halves: the erased type prints as `[Ljava.lang.Object;`.

There is **no null-checking loop in the constructor.** The comment at `:669` says so explicitly:
"caller must ensure that elements has no nulls if `allowNulls` is false". Validation lives in the
factories — `listFromArray`'s copy loop (`:191-193`) and `listFromTrustedArray`'s check loop
(`:214-216`) — and the constructor is `private`, so those factories plus the static initialiser are
the only ways in. Leaf 3.12.3's implied "constructor's null-checking loop" does not exist; `ListN`
trusts, and the trust boundary is the factory.

`get` at `:681-684` is bare array indexing — the whole body is `return elements[index];`, so the
`IndexOutOfBoundsException` you see is the JVM's own from the array access, not a hand-thrown one.
`allowNulls` gates exactly two methods, `indexOf` (`:720-731`) and `lastIndexOf` (`:733-744`):

```java
        @Override
        public int indexOf(Object o) {
            if (!allowNulls && o == null) {
                throw new NullPointerException();
            }
            Object[] es = elements;
            for (int i = 0; i < es.length; i++) {
                if (Objects.equals(o, es[i])) {
                    return i;
                }
            }
            return -1;
        }
```

Since `AbstractImmutableList.contains` is `indexOf(o) >= 0` (`:329-331`), `contains(null)` throws on
an `allowNulls == false` list and answers on an `allowNulls == true` one. The same gate is
re-implemented for slices in `SubList.allowNulls()` at `:497-499`, reaching through to the root:
`root instanceof ListN && ((ListN<?>)root).allowNulls` — so a `SubList` of a `List12` reports
`false`, because `List12` is not a `ListN`. The full behavioural matrix across every immutable
list, set and map lives in [03c-null-queries-and-guava.md](03c-null-queries-and-guava.md).

**Insight:** `allowNulls` creates **two distinct canonical empty lists**, built side by side in the
static initialiser at `:105-106` — `EMPTY_LIST = new ListN<>(new Object[0], false);` and
`EMPTY_LIST_NULLS = new ListN<>(new Object[0], true);`. `List.of()` returns the first; `Stream.empty().toList()` routes through
`listFromTrustedArrayNullsAllowed` (`:241-249`) and returns the second. They are `equals` and not
`==`. That method has **no size specialisation** — its only branch is `length == 0` — so
`Stream.toList()` yields a `ListN` at *every* size, while `collect(toUnmodifiableList())` goes
through `listFromTrustedArray` and yields a `List12` at size ≤ 2. `Stream.toList()` arrived in
**Java 16**; before that `collect(toList())` gave you a mutable `ArrayList`, so which variant you
get is a Java 16+ concern.

### Proof, by reflection

```java
import java.lang.reflect.Field;
import java.util.*;
import java.util.stream.Stream;

public class Fields {
    static void show(String label, Object c, String... fields) throws Exception {
        System.out.print(label + " -> " + c.getClass().getSimpleName());
        for (String name : fields) {
            Field f = c.getClass().getDeclaredField(name);
            f.setAccessible(true);
            Object v = f.get(c);
            System.out.print("  " + name + "=" + (v instanceof Object[] a ? Arrays.toString(a) : v));
        }
        System.out.println();
    }

    static Object read(Object c, String name) throws Exception {
        Field f = c.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(c);
    }

    public static void main(String[] args) throws Exception {
        show("List.of(a)     ", List.of("a"), "e0", "e1");
        show("List.of(a,b)   ", List.of("a", "b"), "e0", "e1");
        show("List.of(a,b,c) ", List.of("a", "b", "c"), "elements", "allowNulls");
        show("Stream toList  ", Stream.of("a", null, "c").toList(), "elements", "allowNulls");
        show("Set.of(1,2,3)  ", Set.of(1, 2, 3), "size");

        Object sentinel = read(List.of("a"), "e1");
        System.out.println("sentinel is null? " + (sentinel == null)
                + "   class = " + sentinel.getClass().getName()
                + "   shared with Set12? " + (sentinel == read(Set.of("z"), "e1")));
        System.out.println("Set.of(1,2,3) elements.length = "
                + ((Object[]) read(Set.of(1, 2, 3), "elements")).length);
    }
}
// Real output:
//   List.of(a)      -> List12  e0=a  e1=java.lang.Object@53d8d10a
//   List.of(a,b)    -> List12  e0=a  e1=b
//   List.of(a,b,c)  -> ListN  elements=[a, b, c]  allowNulls=false
//   Stream toList   -> ListN  elements=[a, null, c]  allowNulls=true
//   Set.of(1,2,3)   -> SetN  size=3
//   sentinel is null? false   class = java.lang.Object   shared with Set12? true
//   Set.of(1,2,3) elements.length = 6
```

Run with the module opened — mandatory since Java 16, when strong encapsulation became the default:
`java --add-opens java.base/java.util=ALL-UNNAMED -cp out Fields`.

That settles four claims at once: the sentinel is a real `java.lang.Object`, not `null`; it is one
shared instance across `List12` *and* `Set12`; `ListN`'s backing array really does hold a `null`
when `allowNulls` is true; and `allowNulls` is `false` for `List.of` and `true` for
`Stream.toList`. `elements.length = 6` for a 3-element `SetN` is `EXPAND_FACTOR = 2` (`:140`) in
action — mechanism deferred to
[04b-internals-open-addressing-and-salt.md](04b-internals-open-addressing-and-salt.md).

### The gotcha

`--add-opens` is a diagnostic tool, not a design. Reading `allowNulls` reflectively in production
binds you to a private field of an internal class, and it has already changed shape once — the flag
was added in Java 16 for `Stream.toList`.

### Definition

> `ListN<E>` is the array-backed immutable list: a single `@Stable E[] elements` field with an
> `Object` runtime component type, plus an `allowNulls` flag set by the factory that decides
> whether `indexOf`/`lastIndexOf`/`contains` reject a `null` query with NPE or answer it.

**Interview:** "Is `List.of() == Stream.empty().toList()`?" — No. Both are `ListN` of length 0 and
they are `equals`, but they are the distinct singletons `EMPTY_LIST` and `EMPTY_LIST_NULLS`,
differing in `allowNulls` and therefore in `contains(null)`.

---

## The six siblings, side by side (3.12.5)

The picture generalises: for lists and sets, a fields-only class for sizes 1–2 and an array-backed
class for everything else, plus a CDS-archived empty singleton. **Maps break the pattern**, and
that is this leaf's payload.

| Class | Fields | Chosen at | Allocates an array? | Data layout |
|---|---|---|---|---|
| `List12<E>` (`:553`) | `E e0`, `Object e1` | size 1–2 | **No** | two object fields; `size()` = `e1 != EMPTY ? 2 : 1` |
| `ListN<E>` (`:660`) | `E[] elements`, `boolean allowNulls` | size 0, and size ≥ 3 | Yes — 1, adopted from the factory | dense array, index = position, `size()` = `elements.length` |
| `Set12<E>` (`:780`) | `E e0`, `Object e1` | size 1–2 | **No** | two object fields; ctor rejects `e0.equals(e1)` with `IllegalArgumentException("duplicate element")` (`:797-800`) |
| `SetN<E>` (`:906`) | `E[] elements`, `int size` | size 0, and size ≥ 3 | Yes — its own, `EXPAND_FACTOR * n` | open-addressed hash table, **half empty by construction**; needs a separate `size` field because `elements.length` is 2n |
| `Map1<K,V>` (`:1104`) | `K k0`, `V v0` | **exactly 1 pair only** | **No** | two object fields; `get` is `o.equals(k0) ? v0 : null` |
| `MapN<K,V>` (`:1171`) | `Object[] table`, `int size` | 0 pairs, and **≥ 2 pairs** | Yes — `EXPAND_FACTOR * input.length`, forced even by `(len + 1) & ~1` | one flat array of *interleaved* key,value pairs — index `2i` key, `2i+1` value — not an array of `Entry` |

Three consequences worth naming.

1. **There is no `Map2`.** `Map.java:1384` sends a two-pair map straight to
   `new ImmutableCollections.MapN<>(k1, v1, k2, v2)`. For a two-entry map you get a 4-element
   varargs `Object[]` plus an 8-element `table`, where `Set.of(a, b)` would have given a field-only
   `Set12`. The map ladder is one arm shallower than the list and set ladders.
2. **`ofEntries` re-specialises where `of` cannot.** `Map.ofEntries(one)` (`Map.java:1663-1672`)
   *does* produce a `Map1`, because it inspects the entry count at runtime. It also does not store
   the `Entry` objects — the Javadoc at `:1641` says "The entries themselves are not stored in the
   map"; `MapN` extracts key and value and drops the entry.
3. **`MapN`'s `table` is `Object[]`, not `Entry[]`.** And `Map1.entrySet()` is literally
   `Set.of(new KeyValueHolder<>(k0, v0))` (`:1117-1119`) — asking a one-entry immutable map for its
   entry set builds a `Set12` wrapping a fresh holder.

The open-addressing mechanism — `probe()`, the `EXPAND_FACTOR` load factor, `SALT32L`-driven
iteration start, `REVERSE` — belongs to
[04b-internals-open-addressing-and-salt.md](04b-internals-open-addressing-and-salt.md). The one
thing to carry forward: `SALT32L` and `REVERSE` affect **iteration order only**; `probe()` itself
is unsalted.

### Proving the table rather than asserting it

```java
import java.util.*;

public class ClassPick {
    static String n(Object o) { return o.getClass().getName(); }

    public static void main(String[] args) {
        System.out.println("list 0  -> " + n(List.of()));
        System.out.println("list 2  -> " + n(List.of(1, 2)));
        System.out.println("list 3  -> " + n(List.of(1, 2, 3)));
        System.out.println("set  2  -> " + n(Set.of(1, 2)));
        System.out.println("set  3  -> " + n(Set.of(1, 2, 3)));
        System.out.println("map 1 pair   -> " + n(Map.of("a", 1)));
        System.out.println("map 2 pairs  -> " + n(Map.of("a", 1, "b", 2)));
        System.out.println("ofEntries(1) -> " + n(Map.ofEntries(Map.entry("a", 1))));
    }
}
// Real output, all names prefixed java.util.ImmutableCollections$ :
//   list 0 -> ListN   list 2 -> List12   list 3 -> ListN   set 2 -> Set12   set 3 -> SetN
//   map 1 pair -> Map1   map 2 pairs -> MapN   ofEntries(1) -> Map1
// The fuller run also covered sizes 1, 10, 11: every size >= 3 was ListN/SetN/MapN.
```

Size 0 being `ListN` is the detail people get wrong: the empty list is an array-backed `ListN`
with a zero-length array, not a special `EmptyList` class.

**Definition (survey):** the six leaves split two ways — `List12`/`Set12`/`Map1` store data in
object fields and allocate nothing else; `ListN`/`SetN`/`MapN` store data in one array, dense for
`ListN` and hash-probed at `EXPAND_FACTOR = 2` slack for `SetN`/`MapN`.

**Interview:** "How many overloads does `List.of` have?" — Eleven fixed-arity, `of()` through
`of(e1..e10)` at `List.java:920-1129`, plus `of(E...)` at `:1161` = twelve entry points. `Set.of`
matches it (`Set.java:454-662`, `:695`). `Map.of` has eleven fixed-arity arms taking 0, 2, 4 … 20
arguments — 0 through 10 *pairs* (`Map.java:1347-1624`) — plus `ofEntries(Entry...)` at `:1663`.

---

## Pitfalls

### Believing `List.of(a, b, c)` allocates no array

**Wrong**

```java
List<String> three = List.of("a", "b", "c");   // "no array below arity 11". Zero allocations?
```

**Right**

```java
// List.java:971 -> listFromTrustedArray(e1, e2, e3), declared Object... (:212), so an Object[3]
// is synthesized at the call site and then ADOPTED as ListN.elements. One array, retained.
// What arity 3-10 avoids is the *second* array that listFromArray would make.
```

**Why people believe it:** the ladder really was introduced to cut allocation, and for arity
0–2 (`List12`) the claim is exactly true. The generalisation to all eleven arms is the error.

### Assuming the absent second element of `List12` is `null`

**Wrong**

```java
Field f = List.of("a").getClass().getDeclaredField("e1");
f.setAccessible(true);
System.out.println(f.get(List.of("a")) == null);   // expecting true
```

**Right**

```java
// prints false. e1 == ImmutableCollections.EMPTY, a shared `new Object()` created at :104,
// and size() at :576 is `e1 != EMPTY ? 2 : 1`, an identity comparison against that object.
// Reason (comment at :564): null is a reference field's DEFAULT value, and @Stable only
// licenses constant folding of a NON-default value. A distinct sentinel keeps e1 foldable.
```

**Why people believe it:** every other "unused slot" in the JDK is `null`, the sentinel is invisible
without reflection, and the performance reason is not discoverable from the API.

### Expecting `Map.of` to have a `Map2` the way `Set.of` has `Set12`

**Wrong**

```java
System.out.println(Map.of("a", 1, "b", 2).getClass().getSimpleName());  // "Map2"?
```

**Right**

```java
// prints MapN. Map.java:1384 is:
//     return new ImmutableCollections.MapN<>(k1, v1, k2, v2);
// Map1 (:1104) is the ONLY field-based map, and only for exactly one pair.
// A 2-entry immutable map costs a MapN object + an Object[8] table (EXPAND_FACTOR * 4).
```

**Why people believe it:** `List12` and `Set12` both cover sizes 1–2, so the symmetry is expected.
Maps have twice the fields per entry — a hypothetical `Map2` would be four fields wide — and the
JDK stopped at one pair.

### Treating `List.of()` and `Stream.empty().toList()` as interchangeable

**Wrong**

```java
List<String> a = List.of();
List<String> b = Stream.<String>empty().toList();
System.out.println(a == b);   // expecting true; prints false
```

**Right**

```java
// Two distinct singletons: EMPTY_LIST (allowNulls=false, :105) and EMPTY_LIST_NULLS
// (allowNulls=true, :106). Both ListN, both equals(), never ==.
// b.contains(null) returns false; a.contains(null) throws NPE (ListN.indexOf, :722).
// Compare only with equals(), and never rely on identity for empty collections.
```

**Why people believe it:** `Collections.emptyList()` really is a single interned singleton, so
prior JDK habits suggest empties are canonical. `Stream.toList()` (Java 16) introduced a second.

---

## Cheat sheet

| Question | Answer |
|---|---|
| Class chosen | `List.of` 0/1–2/≥3 → `ListN` (`EMPTY_LIST`, `:105`)/`List12`/`ListN` · `Set.of` 1–2/≥3 → `Set12`/`SetN` · `Map.of` 1 pair/≥2 → `Map1`/`MapN`, **no `Map2`** |
| Fixed-arity overload count | `List.of` 11, `Set.of` 11, `Map.of` 11 (0–10 pairs); +1 varargs each |
| Arrays allocated: arity 0–2 / 3–10 / `of(E...)` ≥3 | **0** / **1** (varargs array adopted, no copy) / **2** (caller's + `tmp`) |
| Why `listFromArray` copies | TOCTOU: copy-and-check in one pass so no slot is read twice (`:188`) |
| Why `listFromTrustedArray` takes `Object...` not `E...` | so a varargs call cannot synthesize a `String[]` etc. (`:198-208`) |
| `List12.e1` declared type | `Object` — must hold the `EMPTY` sentinel, which is not an `E` |
| `EMPTY` sentinel | `static final Object EMPTY = new Object()` at `:95`/`:104`; shared with `Set12`; CDS-archived |
| Why a sentinel and not `null` | `null` is the field default; `@Stable` only folds non-default values (`:564-565`) |
| `List12.size()` / `isEmpty()` | `e1 != EMPTY ? 2 : 1` (`:576`) — identity compare, no `size` field / constant `false` (`:581`) |
| `ListN` fields; where it null-checks | `E[] elements` (runtime `Object[]`), `boolean allowNulls`; nowhere — private ctor trusts the factory (`:669`) |
| What `allowNulls` gates | `indexOf`, `lastIndexOf` (`:722`, `:736`) → hence `contains` (`:329-331`) |
| `allowNulls=true` producer | `listFromTrustedArrayNullsAllowed` (`:242`), used by `Stream.toList()` (Java 16+) |
| Class at size 1: `Stream.toList()` vs `collect(toUnmodifiableList())` | `ListN` (no size specialisation) vs `List12` (via `listFromTrustedArray`) |
| `EXPAND_FACTOR` | `2` (`:140`) — reciprocal of load factor, `SetN`/`MapN` tables half empty |
| `MapN.table` layout | flat `Object[]`, key at `2i`, value at `2i+1`; length forced even by `(len+1) & ~1` |
| Bytes, compressed oops | `List12` 12+4+4 → **24 B** (1 object) · `new ArrayList<>(List.of(a,b))` 24 + `Object[2]` 24 = **48 B** · `new ArrayList<>()` + 2 `add` 24 + `Object[10]` 56 = **80 B** |
| Reflection flag; `@ValueBased` on maps? | `--add-opens java.base/java.util=ALL-UNNAMED`; no — `Map1`/`MapN` disqualified by `AbstractMap`'s cached fields (`:1103`) |

---

## Self-test

**Q1.** Why is `listFromArray`'s loop written as copy-and-null-check in a single pass, rather
than validate-then-adopt?

<details><summary>Answer</summary>

To close a TOCTOU window. Validate-then-adopt reads each slot twice — once to check, once when
the list later serves it — and the caller still holds the array between those reads, so another
thread can write `null` into a validated slot. The resulting `ListN` would have
`allowNulls == false` while containing a null, which breaks `indexOf` (`:722` throws NPE on a
null query *because* it was promised no nulls) and, worse, makes `listCopy` at `:169` return
that forged list unchanged from `List.copyOf`. Copying into a fresh `tmp` that no other thread
can reach, and validating the copy, reads each caller slot exactly once.

</details>

**Q2.** Why is `List12`'s `e1` field typed `Object` when `e0` is typed `E`?

<details><summary>Answer</summary>

`e1` must be able to hold `ImmutableCollections.EMPTY` (`:95`), a bare `new Object()` that is not
an `E`. Declaring the field `E` would require an unchecked cast at every write of the sentinel and
would make the declared type false. The cast is deferred instead to the single read site where a
caller can observe an element: `get(int)` at `:583-591`, `@SuppressWarnings("unchecked")` and
`return (E)e1`. After erasure that checkcast is against `Object` and costs nothing.

</details>

**Q3.** Why not just use `null` as `List12`'s absent-second-element marker?

<details><summary>Answer</summary>

Because `null` is the *default* value of a reference field, and `@Stable` (on `e1` at `:559`) only
licenses C2 to constant-fold a field whose value is non-default. With `null` as the marker, `e1`
would be at its default for every single-element list, so `size()` — `e1 != EMPTY ? 2 : 1` at
`:576` — could not fold to a constant. The comment at `:564-565` says exactly this: "not using
null enables constant folding optimizations over single-element lists".

</details>

**Q4.** Where does `ListN` null-check its elements?

<details><summary>Answer</summary>

It does not. Its constructor at `:670-673` assigns both fields and nothing else; the comment above
it reads "caller must ensure that elements has no nulls if `allowNulls` is false". The constructor
is `private`, so the only entrances are `listFromArray` (checks in its copy loop, `:191-193`),
`listFromTrustedArray` (checks in its scan loop, `:214-216`),
`listFromTrustedArrayNullsAllowed` (deliberately does not check, `:242-249`), and the static
initialiser. The trust boundary is the factory, not the class.

</details>

**Q5.** Why does `Stream.of("x").toList()` give a `ListN` when
`Stream.of("x").collect(Collectors.toUnmodifiableList())` gives a `List12`?

<details><summary>Answer</summary>

Different factory. `Stream.toList()` (Java 16+) routes through
`listFromTrustedArrayNullsAllowed` (`:241-249`), whose only branch is `input.length == 0`; every
non-empty length falls to `new ListN<>((E[])input, true)`, so there is no size specialisation —
`List12` cannot hold nulls and this path must allow them. `toUnmodifiableList` routes through
`listFromTrustedArray` (`:212`), whose switch has `case 1` and `case 2` arms returning `List12`.

</details>

**Q6.** How many entries does `Map.of` specialise for, and what does a 2-entry immutable map
actually cost in objects?

<details><summary>Answer</summary>

One. `Map1` (`:1104`) is used for exactly one pair; `Map.java:1384` sends two pairs to
`new ImmutableCollections.MapN<>(k1, v1, k2, v2)`. So a 2-entry map costs the varargs `Object[4]`
(transient), the `MapN` object, and its `table` — `EXPAND_FACTOR * 4 = 8` slots, forced even by
`len = (len + 1) & ~1` at `:1186`. `Map.ofEntries` can still reach `Map1` at count 1
(`Map.java:1663-1672`) because it inspects the runtime length. There is no `Map2`, which is the
one place the map ladder is shallower than the list and set ladders.

</details>

---

**Leaves covered:** 3.12.1–3.12.5 (5 leaves)
**Leaves deferred:** none
**Diagrams included:** D-121
**Target version:** Java 21 LTS
**Lines:** 795
