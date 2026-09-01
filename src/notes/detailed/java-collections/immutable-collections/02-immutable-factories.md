# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.3.14–2.3.16)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/01d-arrays-aslist.md](01d-arrays-aslist.md) · Next: [immutable-collections/02a-shallow-immutability-and-boundaries.md](02a-shallow-immutability-and-boundaries.md)

All source citations below are from JDK 21 `lib/src.zip`. All transcripts were produced on
**java 21.0.7+8-LTS-245, HotSpot 64-bit Server VM, macOS/aarch64 (Darwin 25.5.0)**.

---

## The family, before the details

Java has several unrelated mechanisms that all get called "immutable list" in code review, and
they behave differently in ways that cause production bugs. Get the map straight first.

| Factory | Since | Returned type | Independent of source? | Nulls allowed? | `set(i, v)` |
|---|---|---|---|---|---|
| `List.of(a, b, c)` | 9 | `ImmutableCollections.ListN` / `List12` | yes — no source to track | no, NPE | `UnsupportedOperationException` |
| `List.copyOf(c)` | 10 | `ListN` / `List12`, **or `c` itself** | yes (snapshot at call time) | no, NPE | `UnsupportedOperationException` |
| `Collections.unmodifiableList(c)` | 1.2 | `Collections$UnmodifiableRandomAccessList` | **no — live view** | inherited from source | `UnsupportedOperationException` |
| `Collections.singletonList(x)` | 1.3 | `Collections$SingletonList` | yes (1 element, captured) | yes, `[null]` is legal | `UnsupportedOperationException` |
| `Arrays.asList(arr)` | 1.2 | `Arrays$ArrayList` | **no — array-backed view** | yes | **succeeds**, writes through to `arr` |

Two axes hide in that table and they are orthogonal:

1. **Write-blocking** — does calling a mutator throw? All five block *structural* change except
   `Arrays.asList`, which blocks size change but allows `set`.
2. **Isolation** — if somebody mutates the thing you built it from, do you see it? Only
   `List.of`, `List.copyOf` and `singletonList` are isolated. `unmodifiableList` and
   `Arrays.asList` are not.

Confusing axis 1 for axis 2 is the whole content of §2.3.15, and it is the most common
immutability bug in Java code.

This file owns the first three rows (§2.3.14–2.3.16). `singletonList` vs `List.of`, and a
third axis — *depth*, whether the elements themselves can still change — are in
[02a-shallow-immutability-and-boundaries.md](02a-shallow-immutability-and-boundaries.md);
`Arrays.asList`'s write-through `set` is in [01d-arrays-aslist.md](01d-arrays-aslist.md).

---

## `List.of(...)` and the trusted-array optimisation (§2.3.14) `[RESEARCH]`

**Mental model.** `List.of` is not one method. It is eleven fixed-arity overloads plus one
varargs overload, and they exist as separate methods for a single reason: the fixed-arity ones
know that no array exists that anyone else can reach, so they can store their arguments
directly and skip the defensive copy. The varargs one receives an array the caller handed it
and must assume the caller kept a reference. Same public API, two different trust levels
underneath.

**Why it exists.** Before Java 9 the idiom was
`Collections.unmodifiableList(new ArrayList<>(Arrays.asList("a", "b")))` — three objects, two
copies, and a wrapper on every read. `List.of` collapses that to one object with the elements
stored in fields (`List12`) or a single array (`ListN`), no wrapper indirection, and no header
overhead for a backing `ArrayList`.

**When to reach for it.** Any list literal you never intend to mutate: constants, lookup
tables, method arguments, test fixtures. **When not:** when you need nulls (use
`Arrays.asList` or `Collections.unmodifiableList(new ArrayList<>(…))`), when you need a
`List` you will later mutate, or when the elements come from a `Collection` you already hold
(use `List.copyOf`, one pass instead of `toArray` plus `of`).

**Mechanism.** Two internal entry points do the construction, and the difference is exactly
the copy. `[SOURCE]`

```java
// ImmutableCollections.java:186-195 — the UNTRUSTED path
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

Line by line: `tmp` is a **fresh** `Object[]` of the same length — this is the defensive copy.
The loop does two jobs at once: it copies each element and it null-checks it. The comment
"avoid TOCTOU" (time-of-check-to-time-of-use) is the reason the two jobs are fused — if the
JDK checked `input` for nulls and *then* copied, a concurrent writer could slip a null into
`input` between the check and the copy, and the list would end up holding a null it had
already certified as non-null. Copying into `tmp` first and checking `tmp[i]` (which is what
`tmp[i] = requireNonNull(input[i])` does: one read of `input[i]`, checked, stored) closes that
window. `new ListN<>(tmp, false)` — `false` is `allowNulls`, and it matters in §2.3.16.

```java
// ImmutableCollections.java:211-224 — the TRUSTED path
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

No `tmp`. The `default` arm passes `input` **itself** to `ListN`, which stores it in its
`private final E[] elements` field (`ImmutableCollections.java:663-664`). The javadoc above
the method states the contract in one sentence: *"A trusted array has no references retained
by the caller. It can therefore be safely reused as the List's internal storage, avoiding a
defensive copy."* The parameter is declared `Object...` rather than `E...` deliberately —
also documented at `ImmutableCollections.java:203-205` — so that a varargs call site cannot
synthesise a `String[]` where `Object[]` is expected and later blow up with
`ArrayStoreException` on an internal write. The `assert` encodes that invariant.

Which public entry point takes which path:

| Call shape | Declared at | Routes to | Copies the array? |
|---|---|---|---|
| `List.of()` | `List.java:920` | `EMPTY_LIST` constant | n/a |
| `List.of(e1)`, `List.of(e1, e2)` | `List.java:936`, `953` | `new List12<>(…)` directly | n/a — no array exists |
| `List.of(e1 … e3)` … `List.of(e1 … e10)` | `List.java:971-1130` | `listFromTrustedArray` | **no** — compiler-synthesised array, unreachable by the caller |
| `List.of(E... elements)` | `List.java:1161-1174` | `listFromArray` (`default` arm) | **yes** |

The varargs overload is worth reading, because it does not delegate blindly:

```java
// List.java:1159-1174
@SafeVarargs
@SuppressWarnings("varargs")
static <E> List<E> of(E... elements) {
    switch (elements.length) { // implicit null check of elements
        case 0:
            @SuppressWarnings("unchecked")
            var list = (List<E>) ImmutableCollections.EMPTY_LIST;
            return list;
        case 1:
            return new ImmutableCollections.List12<>(elements[0]);
        case 2:
            return new ImmutableCollections.List12<>(elements[0], elements[1]);
        default:
            return ImmutableCollections.listFromArray(elements);
    }
}
```

For 0, 1 and 2 elements it never retains `elements` at all — `List12` copies the values into
two fields, so the array is garbage immediately and no defensive copy is needed. Only the
`default` arm, where `ListN` would store the array by reference, pays for `listFromArray`.
So "`List.of` varargs copies" is true only from three elements up.

**Insight:** the eleven fixed-arity overloads are not API sugar to avoid varargs allocation.
They are there so the *common* case can skip a copy that the *general* case cannot skip.

![D-38: the left half shows Collections.unmodifiableList holding a reference to the source list, so src.add("Z") appears through the wrapper; the right half shows List.copyOf building its own array, so src.add("Z") is invisible. Look at the arrow direction into the source on the left and its absence on the right, and at the callout box noting that copyOf can return the source instance itself.](../diagrams/D-38-unmodifiable-vs-copy.svg)

**Proof of the copy.** Mutating the source array after construction leaves the list unchanged:

```java
String[] src = { "a", "b", "c" };
List<String> list = List.of(src);           // varargs -> listFromArray -> copies
System.out.println("list before  = " + list);
src[0] = "MUTATED";
System.out.println("src   after  = " + Arrays.toString(src));
System.out.println("list  after  = " + list);
System.out.println("list class   = " + list.getClass().getName());
System.out.println("2-arg class  = " + List.of("a", "b").getClass().getName());
System.out.println("3-arg class  = " + List.of("a", "b", "c").getClass().getName());
```

Real output:

```
list before  = [a, b, c]
src   after  = [MUTATED, b, c]
list  after  = [a, b, c]
list class   = java.util.ImmutableCollections$ListN
2-arg class  = java.util.ImmutableCollections$List12
3-arg class  = java.util.ImmutableCollections$ListN
```

Note that `getClass()` alone cannot tell you which path ran — both `List.of(src)` and
`List.of("a","b","c")` produce a `ListN`. Only the mutation test distinguishes them, and it
shows the varargs form is safe.

**Null-hostility.** `List.of` throws `NullPointerException`, not `IllegalArgumentException`,
and it throws at construction, not at read. The throw site is `Objects.requireNonNull` inside
`listFromArray` (`ImmutableCollections.java:192`) or `listFromTrustedArray`
(`ImmutableCollections.java:215`), or `Objects.requireNonNull` in the `List12` constructor
(`ImmutableCollections.java:563`, `570-571`) for the one- and two-element cases.

```java
try {
    List<String> bad = List.of("a", null);
    System.out.println("no throw: " + bad);
} catch (NullPointerException e) {
    System.out.println("List.of(\"a\", null) -> " + e.getClass().getName());
}
try {
    String[] withNull = { "a", "b", null };
    List<String> bad = List.of(withNull);
    System.out.println("no throw: " + bad);
} catch (NullPointerException e) {
    System.out.println("List.of(array-with-null) -> " + e.getClass().getName());
}
```

```
List.of("a", null) -> java.lang.NullPointerException
List.of(array-with-null) -> java.lang.NullPointerException
```

**Gotcha.** `List.of(someArray)` on a `String[]` gives you a `List<String>` of the elements.
`List.of(someIntArray)` on an `int[]` gives you a **`List<int[]>` of size 1**, because `int[]`
is not `Object[]` and the compiler wraps it as a single varargs element. Same trap as
`Arrays.asList` (covered in [01d-arrays-aslist.md](01d-arrays-aslist.md)).

> **Definition.** `List.of` returns a structurally immutable, null-hostile `List` whose
> storage is either two fields (`List12`, ≤2 elements) or a private array (`ListN`) that is
> the caller's array only when the JDK constructed that array itself.

---

## Unmodifiable *view* vs immutable *copy* (§2.3.15) `[TRAP]`

**Mental model.** `Collections.unmodifiableList(src)` is a one-way mirror bolted onto `src`.
It refuses your writes. It does nothing at all about anyone else's writes to `src`, because it
does not own the data — it holds a pointer to `src` and forwards every read.

**Why it exists.** Java 1.2 shipped no immutable collection implementations. The wrapper was
the only tool available for "hand this out read-only", and it deliberately did not copy,
because copying a large collection on every getter call was unacceptable in 1998 and is still
sometimes unacceptable now.

**When to reach for it.** When you want to block the *recipient's* writes but the recipient
*should* observe your later updates, and when the collection is large enough that a copy per
call matters. **When not:** when the recipient must get a stable snapshot — then `List.copyOf`
wins, and it is the sibling that beats the wrapper here.

**Mechanism.** The field is the whole story. `[SOURCE]`

```java
// Collections.java:1052-1063
static class UnmodifiableCollection<E> implements Collection<E>, Serializable {
    @java.io.Serial
    private static final long serialVersionUID = 1820017752578914078L;

    @SuppressWarnings("serial") // Conditionally serializable
    final Collection<? extends E> c;

    UnmodifiableCollection(Collection<? extends E> c) {
        if (c==null)
            throw new NullPointerException();
        this.c = c;
    }
```

`final Collection<? extends E> c` is a **reference to the caller's collection**, not a copy.
`final` makes the *field* unreassignable; it says nothing about the object it points at. The
constructor null-checks the collection and stores it. That is all. `UnmodifiableList` adds a
second, more specific reference to the same object:

```java
// Collections.java:1485-1512 (excerpted)
static class UnmodifiableList<E> extends UnmodifiableCollection<E>
                              implements List<E> {
    @SuppressWarnings("serial") // Conditionally serializable
    final List<? extends E> list;

    UnmodifiableList(List<? extends E> list) {
        super(list);
        this.list = list;
    }

    public E get(int index) {return list.get(index);}
    public E set(int index, E element) {
        throw new UnsupportedOperationException();
    }
    public void add(int index, E element) {
        throw new UnsupportedOperationException();
    }
    public E remove(int index) {
        throw new UnsupportedOperationException();
    }
    public int indexOf(Object o)            {return list.indexOf(o);}
    public int lastIndexOf(Object o)        {return list.lastIndexOf(o);}
```

Every **read** delegates to `list`. Every **write** throws. `get(index)` calling
`list.get(index)` is precisely why the view is live: there is no stored copy to go stale.
`super(list)` and `this.list = list` store the same object twice, once as `Collection` for the
inherited read methods and once as `List` for the index-based ones — a size optimisation would
not have been worth the cast on every `get`.

**Proof that `src.add(X)` shows through:**

```java
List<String> backing = new ArrayList<>(List.of("x", "y"));
List<String> view = Collections.unmodifiableList(backing);
System.out.println("view class   = " + view.getClass().getName());
System.out.println("view before  = " + view);
backing.add("Z");
System.out.println("view after backing.add(\"Z\") = " + view);
try {
    view.add("W");
} catch (UnsupportedOperationException e) {
    System.out.println("view.add -> " + e.getClass().getName());
}
List<String> copy = List.copyOf(backing);
backing.add("Q");
System.out.println("copy after backing.add(\"Q\")  = " + copy);
System.out.println("view after backing.add(\"Q\")  = " + view);
```

```
view class   = java.util.Collections$UnmodifiableRandomAccessList
view before  = [x, y]
view after backing.add("Z") = [x, y, Z]
view.add -> java.lang.UnsupportedOperationException
copy after backing.add("Q")  = [x, y, Z]
view after backing.add("Q")  = [x, y, Z, Q]
```

The last two lines are the entire lesson in two prints: the copy froze at `[x, y, Z]`; the
view followed `backing` to `[x, y, Z, Q]`.

The returned class is `UnmodifiableRandomAccessList`, not `UnmodifiableList`, because
`unmodifiableList` picks the `RandomAccess`-implementing subclass when the source implements
`RandomAccess` (`Collections.java:1584-1589`) so that algorithms which branch on
`instanceof RandomAccess` do not silently drop to the slow iterator path.

**Pitfall:** *"I wrapped it in `unmodifiableList`, so it's immutable."* **Symptom:** a caller
holding your "immutable" list observes it changing between two reads — sizes that differ
mid-iteration, `ConcurrentModificationException` from the delegated iterator, or a cached hash
code that no longer matches. **Fix:** if isolation is what you wanted, use `List.copyOf(src)`
(or wrap a private copy the caller cannot reach: `Collections.unmodifiableList(new ArrayList<>(src))`).

**Insight:** `unmodifiableList` is thread-*unsafe* in the same way its source is. It adds no
synchronisation, so a reader on another thread iterating the view while the owner appends to
the source gets a `ConcurrentModificationException` — thrown by the source's iterator, which
the view's iterator wraps (`Collections.java:1073-1078`).

> **Definition.** `Collections.unmodifiableX` returns a write-rejecting *view* that holds a
> reference to the source collection and forwards all reads to it, so the source's later
> mutations are visible through the view.

---

## `copyOf` and the same-instance return (§2.3.16) `[RESEARCH]`

**Mental model.** `copyOf` is a *conditional* copy. Its job is not "always allocate"; its job
is "guarantee the result is immutable and null-free". If the input already provably satisfies
that, the cheapest correct answer is the input itself, and that is what it returns.

**Why it exists.** `List.copyOf` (Java 10) closed the gap `List.of` left: `of` takes elements,
`copyOf` takes a `Collection`. It also let library authors write
`return List.copyOf(field)` in a getter without paying an allocation on every call in the
common case where `field` is already immutable.

**When to reach for it.** Any boundary where you need a snapshot. **When not:** when the
source may contain nulls (it throws), or when you specifically want the caller to see later
changes — that is `unmodifiableList`'s case.

**Mechanism.** `List.copyOf` is a one-line delegation (`List.java:1192-1194`) to: `[SOURCE]`

```java
// ImmutableCollections.java:167-176
@SuppressWarnings("unchecked")
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

**Version/citation note.** This method is often cited as `ImmutableCollections.java:161-174`.
In JDK 21.0.7 `lib/src.zip` the method body is **lines 167-176**; 158-166 is its javadoc. The
behaviour is as described; only the line numbers in the widely-copied citation are off by six.
Cite 167-176.

Line by line. The first branch is the same-instance return: if `coll` is a `List12` it cannot
hold nulls (its constructors call `requireNonNull`, `ImmutableCollections.java:563` and
`570-571`) and cannot be mutated, so it is already exactly what `copyOf` promises — return the
cast. If it is a `ListN`, that is not sufficient: `ListN` carries a
`private final boolean allowNulls` field (`ImmutableCollections.java:666-667`) and a `ListN`
created through `listFromTrustedArrayNullsAllowed` (`ImmutableCollections.java:242-249`, used
by `Stream.toList()`) may hold nulls. The pattern-matching `instanceof ListN<?> c` binds `c`
so `!c.allowNulls` can be read — a null-free `ListN` qualifies, a null-permitting one does not
and falls through to the copy, where `List.of` will reject the nulls.

The second branch: an empty non-immutable input needs no array at all, so return the shared
`EMPTY_LIST`. The comment "implicit nullcheck of coll" flags that `coll.isEmpty()` is where a
null *argument* NPEs — the `instanceof` in the first branch is null-safe and would silently
fall through, so the NPE has to come from a real dereference.

The third branch: `coll.toArray()` produces a fresh array **that no caller retains**, so
handing it to `List.of(E...)` is safe even though that overload defensively copies. (It does
copy — one redundant array per `copyOf` of a mutable source. That is the allocation cost of
`copyOf` versus a wrapper: two arrays, not one.)

**Proof, with `==`:**

```java
List<String> imm = List.of("a", "b", "c");
System.out.println("List.copyOf(List.of(a,b,c)) == source ? " + (List.copyOf(imm) == imm));
List<String> imm2 = List.of("a");
System.out.println("List.copyOf(List12) == source ?         " + (List.copyOf(imm2) == imm2));
System.out.println("List.copyOf(List.of()) == List.of() ?   "
        + (List.copyOf(List.<String>of()) == List.<String>of()));
List<String> viewOfImm = Collections.unmodifiableList(imm);
List<String> copied = List.copyOf(viewOfImm);
System.out.println("List.copyOf(unmodifiableList(imm)) == imm ? " + (copied == imm));
System.out.println("  copied class = " + copied.getClass().getName());
List<String> streamToList = Stream.of("a", "b", "c").toList();
System.out.println("Stream.toList class = " + streamToList.getClass().getName());
System.out.println("List.copyOf(Stream.toList()) == source ? "
        + (List.copyOf(streamToList) == streamToList));
List<String> nullyList = Arrays.asList("a", null, "c").stream().toList();
System.out.println("nully Stream.toList = " + nullyList);
try {
    List<String> c = List.copyOf(nullyList);
    System.out.println("no throw: " + c);
} catch (NullPointerException e) {
    System.out.println("List.copyOf(list-containing-null) -> " + e.getClass().getName());
}
Set<String> immSet = Set.of("a", "b");
System.out.println("Set.copyOf(Set.of) == source ? " + (Set.copyOf(immSet) == immSet));
Map<String,Integer> immMap = Map.of("a", 1);
System.out.println("Map.copyOf(Map.of) == source ? " + (Map.copyOf(immMap) == immMap));
```

```
List.copyOf(List.of(a,b,c)) == source ? true
List.copyOf(List12) == source ?         true
List.copyOf(List.of()) == List.of() ?   true
List.copyOf(unmodifiableList(imm)) == imm ? false
  copied class = java.util.ImmutableCollections$ListN
Stream.toList class = java.util.ImmutableCollections$ListN
List.copyOf(Stream.toList()) == source ? false
nully Stream.toList = [a, null, c]
List.copyOf(list-containing-null) -> java.lang.NullPointerException
Set.copyOf(Set.of) == source ? true
Map.copyOf(Map.of) == source ? true
```

Four results to read carefully. The syllabus form of this leaf — "`copyOf` of an already
immutable collection returns the same instance" — is **too broad**, and the transcript shows
exactly where it fails.

- **Same instance** for `List.of` inputs of every size, including empty. Confirmed by `==`.
  This much of the claim holds.
- **A copy for an unmodifiable *view***, even when the view wraps an immutable list.
  `UnmodifiableRandomAccessList` is not `List12` and not `ListN`, so branch one does not fire.
  This is not a JDK oversight: `listCopy` cannot know the wrapped list is immutable without
  unwrapping, and the wrapper exposes no accessor. Wrapping an immutable list in
  `unmodifiableList` therefore *costs* you the `copyOf` fast path downstream — don't do it.
- **A copy for `Stream.toList()`**, even though the transcript shows it is a `ListN`. That
  `ListN` has `allowNulls == true` (it comes from `listFromTrustedArrayNullsAllowed`,
  reached via `ImmutableCollections.java:1507`), so `!c.allowNulls` is false and it falls
  through. This is the practical consequence of the `allowNulls` guard, and it is why
  `Stream.toList()` and `List.copyOf(stream.toList())` are not interchangeable.
- **NPE on a null element**, thrown from `List.of(coll.toArray())` — the copy path, not the
  fast path. A `Stream.toList()` result containing a null is an immutable list that
  `List.copyOf` will *reject*, which is worth knowing before you put `copyOf` in a hot path
  over stream output.

So the accurate statement is narrower: `copyOf` returns the same instance when the argument is
already a **null-free member of the matching `ImmutableCollections` family** — not merely when
it is "immutable" in the loose sense.

`Set.copyOf` and `Map.copyOf` use a simpler test — `coll instanceof ImmutableCollections.AbstractImmutableSet`
(`Set.java:728-736`) and `map instanceof ImmutableCollections.AbstractImmutableMap`
(`Map.java:1742-1750`) — because no immutable `Set`/`Map` implementation permits nulls, so
there is no `allowNulls` equivalent to guard against. Only `List.copyOf` needs the two-part
condition. `Set.copyOf` also deduplicates via `new HashSet<>(coll)`, so it accepts a `List`
with duplicates where `Set.of` would throw `IllegalArgumentException` — a real behavioural
difference between `Set.of(a, a)` and `Set.copyOf(List.of(a, a))`.

**Gotcha.** "`copyOf`" in the name promises a *value* snapshot, not a *fresh object*. Never
write `if (List.copyOf(a) != a)` to detect mutability, and never rely on
`List.copyOf(x) != x` for identity-based caching or locking.

> **Definition.** `List.copyOf`/`Set.copyOf`/`Map.copyOf` return an immutable, null-free
> collection with the source's contents at call time, returning the source itself when it is
> already a null-free immutable collection of the matching family.

---

## Pitfalls

### Believing `Collections.unmodifiableList` makes a collection immutable

**Wrong**

```java
private final List<String> roles = new ArrayList<>();

public List<String> roles() {
    return Collections.unmodifiableList(roles);   // "immutable"
}

// caller
List<String> snapshot = svc.roles();
int before = snapshot.size();
svc.grant("admin");                                // owner mutates
System.out.println(before + " -> " + snapshot.size());   // prints e.g. 2 -> 3
```

The wrapper only blocks the *caller's* writes. The field is still mutable and the wrapper
forwards every read to it (`Collections.java:1501`, `get` delegates to `list.get`).

**Right**

```java
public List<String> roles() {
    return List.copyOf(roles);   // snapshot: source mutations invisible
}
```

Proven above: `copy` stayed at `[x, y, Z]` while `view` advanced to `[x, y, Z, Q]`.

**Why people believe it:** the method name says "unmodifiable" and the returned object does in
fact reject every mutator, so the belief is confirmed by every test that only tries to write
to the wrapper. Nothing fails until a *second* actor mutates the source.

### Assuming `List.copyOf(x)` always allocates a new object

**Wrong**

```java
List<String> a = List.of("p", "q");
List<String> b = List.copyOf(a);
System.out.println(a == b);           // expected false
cache.put(b, compute(b));             // identity-keyed cache "keyed by the copy"
```

Output is `true`. `listCopy` returns the argument when it is a `List12` or a null-free `ListN`
(`ImmutableCollections.java:169-170`), so `b` *is* `a` and the "copy" is not a distinct key.

**Right**

```java
List<String> b = new ArrayList<>(a);              // guaranteed fresh object
List<String> immutableFresh = List.of(a.toArray(new String[0]));  // fresh and immutable
System.out.println(a == b);                        // false
```

**Why people believe it:** `Arrays.copyOf`, `String.copyValueOf` and every `clone()` in the
JDK do allocate. `copyOf` on the immutable factories is documented as an *implNote* — "calling
copyOf will generally not create a copy" (`List.java:1183-1184`) — which readers skip.

---

## Cheat sheet

| Question | Answer |
|---|---|
| `List.of` fixed-arity 3–10 args | `listFromTrustedArray` — **no** defensive copy (`ImmutableCollections.java:212`) |
| `List.of(E...)` varargs, ≥3 elements | `listFromArray` — **copies** (`ImmutableCollections.java:187`) |
| `List.of(E...)` varargs, 0/1/2 elements | `EMPTY_LIST` / `List12` — array never retained (`List.java:1162-1170`) |
| Why the copy | caller may retain the array; also TOCTOU-safe null check |
| Can `getClass()` tell the two paths apart? | no — both are `ListN`; only mutating the source array can |
| `List.of` + null | `NullPointerException` at construction |
| `List.of(int[])` | a `List<int[]>` of size 1, not a list of ints |
| `Collections.unmodifiableX(c)` | live **view**; field `final Collection<? extends E> c` (`Collections.java:1057`) |
| Source mutated after wrapping / after `copyOf` | visible / invisible |
| Why the view is live | every read forwards: `get(i)` → `list.get(i)` (`Collections.java:1501`) |
| `List.copyOf(List.of(…))` | **same instance** (`ImmutableCollections.java:169-170`) |
| `List.copyOf(unmodifiableList(x))` | copies — wrapper is not `List12`/`ListN` |
| `List.copyOf(stream.toList())` | copies — that `ListN` has `allowNulls == true` |
| Accurate `copyOf` fast-path rule | argument is a **null-free** `List12`/`ListN`, not just "immutable" |
| `Set.copyOf` / `Map.copyOf` fast path | `instanceof AbstractImmutableSet` / `AbstractImmutableMap` — no `allowNulls` guard needed |
| `Set.copyOf(List.of(a, a))` vs `Set.of(a, a)` | dedupes vs `IllegalArgumentException` |
| `List.copyOf` with a null element | `NullPointerException` |
| Cost of `copyOf` on a mutable source | two arrays (`toArray` plus `ListN`), O(n) |

---

## Self-test

**Q1.** `List.of("a", "b", "c")` and `List.of(new String[]{"a","b","c"})` both return a
`ListN`. What is different about how they were built?

<details><summary>Answer</summary>

The fixed-arity overload `List.of(e1, e2, e3)` (`List.java:971-972`) calls
`listFromTrustedArray`, which stores the compiler-synthesised varargs array **directly** in
`ListN.elements` — no defensive copy, because no caller can reach that array. The varargs
overload `List.of(E...)` (`List.java:1161-1174`) falls into its `default` arm and calls
`listFromArray`, which allocates a fresh `Object[]` and copies each element into it while
null-checking, because the caller may have kept a reference to the array it passed. `getClass()`
is identical; only mutating the source array after construction reveals the difference, and it
shows the list is unaffected.

</details>

**Q2.** A getter returns `Collections.unmodifiableList(this.items)`. A caller stores the
result, then calls a method on your object that appends to `items`. What does the caller
observe, and which line of JDK source explains it?

<details><summary>Answer</summary>

The caller observes the appended element. `UnmodifiableList.get(int)` is
`public E get(int index) {return list.get(index);}` (`Collections.java:1501`) — every read is
forwarded to the source list, which is held by reference in
`final List<? extends E> list` (`Collections.java:1491`). Nothing is copied, so there is
nothing to go stale. If the caller was mid-iteration it may instead see
`ConcurrentModificationException`, thrown by the source `ArrayList`'s iterator, which the
view's iterator wraps (`Collections.java:1073-1078`).

</details>

**Q3.** Why does `List.copyOf(Stream.of("a","b","c").toList())` allocate, when
`Stream.toList()` already returns an `ImmutableCollections.ListN`?

<details><summary>Answer</summary>

Because `ListN` can legally hold nulls. `listCopy`'s fast path is
`coll instanceof List12 || (coll instanceof ListN<?> c && !c.allowNulls)`
(`ImmutableCollections.java:169`). `Stream.toList()` builds its list through
`listFromTrustedArrayNullsAllowed` (`ImmutableCollections.java:242-249`, reached from
`ImmutableCollections.java:1507`), which sets `allowNulls = true`. The `!c.allowNulls` guard
therefore fails and execution falls to `List.of(coll.toArray())`, which allocates and rejects
any nulls. Verified: `List.copyOf(streamToList) == streamToList` prints `false`.

</details>

**Q4.** Does `List.copyOf(Collections.unmodifiableList(List.of("a","b")))` return the inner
`List.of` instance? Why is the answer what it is, and what should you conclude for your code?

<details><summary>Answer</summary>

No — it copies, into a fresh `List12`. `listCopy` tests the *runtime class* of its argument,
and the argument is `Collections$UnmodifiableRandomAccessList`, which is neither `List12` nor
`ListN`. The wrapper exposes no way to ask "is what you wrap immutable?", so `listCopy` cannot
see through it. Conclusion: never wrap an already-immutable collection in
`Collections.unmodifiableX` — it adds an indirection on every read *and* destroys the
`copyOf` fast path for every downstream caller. Return the immutable collection directly.

</details>

**Q5.** `Set.of("a", "a")` throws. `Set.copyOf(List.of("a", "a"))` does not. Why, from source?

<details><summary>Answer</summary>

`Set.of` treats duplicates as a programming error and throws `IllegalArgumentException` at
construction, because a set literal with a repeated element almost always indicates a typo.
`Set.copyOf` is converting an arbitrary `Collection` where duplicates are legitimate, so it
normalises instead of complaining: its copy branch is
`(Set<E>)Set.of(new HashSet<>(coll).toArray())` (`Set.java:734`) — the intermediate `HashSet`
deduplicates, and only then does it call `Set.of`, which now sees distinct elements. The
asymmetry is intentional: `of` validates a literal, `copyOf` converts data.

</details>

---

## Open questions

None. Every claim in this file is backed by a JDK 21.0.7 source citation, a run transcript
above, or both.

---

**Leaves covered:** 2.3.14–2.3.16 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** D-38
**Target version:** Java 21 LTS
**Lines:** 673
