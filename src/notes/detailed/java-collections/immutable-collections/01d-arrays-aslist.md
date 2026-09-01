# 02 Java Collections — Immutability and views — INTERMEDIATE (§2.3.12–2.3.13)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/01c-treemap-range-and-reversed-views.md](01c-treemap-range-and-reversed-views.md) · Next: [immutable-collections/02-immutable-factories.md](02-immutable-factories.md)

The three-way **view / copy / snapshot** distinction is defined in
[01-views-copies-snapshots.md](01-views-copies-snapshots.md). The `Map` views are in
[01b-map-views-and-arrays-aslist.md](01b-map-views-and-arrays-aslist.md) and the ordered views
in [01c-treemap-range-and-reversed-views.md](01c-treemap-range-and-reversed-views.md). This
file finishes §2.3 with the oldest view in the JDK and the one people get wrong most often:
`Arrays.asList`.

All transcripts below are real output from **JDK 21.0.7+8-LTS-245, macOS arm64**.

---

## Array-to-`List` bridges at a glance

Three routes from an array to a `List`, and they differ on every axis that matters. Pick from
this table before reading the mechanism.

| Route | Returned class | Aliases the array? | `set`/`sort` | `add`/`remove` | Accepts `null` element |
|---|---|---|---|---|---|
| `Arrays.asList(arr)` | `java.util.Arrays$ArrayList` | **yes** — same array | allowed, **writes the array** | throw `UnsupportedOperationException` | yes |
| `new ArrayList<>(Arrays.asList(arr))` | `java.util.ArrayList` | no — copied | allowed, local only | allowed | yes |
| `Arrays.stream(arr).toList()` | `java.util.ImmutableCollections$ListN` | no — copied | throw | throw | yes (`toList`, unlike `List.of`) |
| `List.of(arr)` | `java.util.ImmutableCollections$ListN` | no — copied | throw | throw | **no** — `NullPointerException` |

Note row one's class name. `Arrays$ArrayList` is **not** `java.util.ArrayList`. That name
collision is the single largest source of confusion about this method, and everything below
follows from it.

---

## `Arrays.asList` (§2.3.12–2.3.13)

### Mental model

`Arrays.asList(arr)` does not build a list. It puts a `List` faceplate on the array you passed
in. There is one array in memory, addressed two ways. That is the whole thing — and it makes
the size fixed for free, because arrays have fixed length.

### Why it exists, and the name that ruins it

It predates `List.of` by two decades and was the only concise array-to-`List` bridge.
Its return class:

```java
// Arrays.java:4220-4224
@SafeVarargs
@SuppressWarnings("varargs")
public static <T> List<T> asList(T... a) {
    return new ArrayList<>(a);
}

// Arrays.java:4229-4239
private static class ArrayList<E> extends AbstractList<E>
    implements RandomAccess, java.io.Serializable
{
    @SuppressWarnings("serial") // Conditionally serializable
    private final E[] a;

    ArrayList(E[] array) {
        a = Objects.requireNonNull(array);
    }
}
```

`new ArrayList<>(a)` inside `Arrays` resolves to `Arrays.ArrayList` — a `private static`
nested class, unrelated to `java.util.ArrayList`, sharing only the simple name. It extends
`AbstractList` and stores exactly one field: `final E[] a`, the caller's array, not a copy
(`Objects.requireNonNull` validates and assigns; nothing is cloned). **This naming collision
is the root of nearly every misconception about `asList`** — people read "ArrayList" in a
stack trace or debugger and assume the resizable one.

It also implements `RandomAccess` and `Serializable`, which is why it behaves correctly in
`Collections.binarySearch` and friends. The `@SuppressWarnings("serial")` on the field is the
JDK acknowledging that `E[]` is only *conditionally* serializable — it serializes iff the
elements do.

### When to reach for it, and when not

Reach for it when you *want* the aliasing: a `List` façade for sorting or `set`-ing an array
in place, or `Collections.fill(Arrays.asList(arr), x)`. Since Java 9, if all you want is an
immutable list of literals, `List.of(...)` is better — it rejects `null`, is genuinely
immutable, and has compact specialisations. If you want a mutable, growable list, the sibling
that wins is `new ArrayList<>(Arrays.asList(arr))`, or `Arrays.stream(arr).toList()` for an
unmodifiable copy.

### The mechanism

```java
// Arrays.java:4241-4274
@Override
public int size() {
    return a.length;
}

@Override
public E get(int index) {
    return a[index];
}

@Override
public E set(int index, E element) {
    E oldValue = a[index];
    a[index] = element;
    return oldValue;
}
```

`size()` reads `a.length` — no independent count, so the size is the array's size, forever.
`get` and `set` index straight into `a`. `set` assigns `a[index] = element`: **that is the
write-through**. There is no copy and no defensive check.

Now the absences. `Arrays.ArrayList` overrides `size`, `toArray`, `get`, `set`, `indexOf`,
`contains`, `spliterator`, `forEach`, `replaceAll`, `sort` and `iterator`. It overrides
**neither `add` nor `remove`**, so both come from `AbstractList`:

```java
// AbstractList.java:154-170
public void add(int index, E element) {
    throw new UnsupportedOperationException();
}

public E remove(int index) {
    throw new UnsupportedOperationException();
}
```

Unconditional throws, with no message. That is where "fixed-size" comes from — again by
omission, not by a guard. The single-argument form throws for the same reason: `AbstractList`'s
`public boolean add(E e) { add(size(), e); return true; }` (`AbstractList.java:112-115`)
funnels straight into the throwing two-argument overload.

And note what *is* overridden:

```java
// Arrays.java:4318-4321
@Override
public void sort(Comparator<? super E> c) {
    Arrays.sort(a, c);
}
```

`sort` sorts the backing array in place. So does `replaceAll` (`:4309-4316`), which loops
`a[i] = operator.apply(a[i])`. **`Arrays.asList` is fixed-*size*, not read-only, and its
write-through goes well beyond `set`** — the syllabus for this leaf mentions only `set`. A
list you handed to a caller can reorder your array from under you.

**Pitfall:** (§2.3.12) the wrong belief is that "fixed-size" implies "safe to hand out", because
`add` and `remove` are the two methods people test and both throw. The symptom is a caller
`sort`-ing or `replaceAll`-ing through the list and silently rewriting an array you still own
and still read — corruption with no exception and no stack trace pointing at the list. The fix
is to pick the guarantee you actually want: `Collections.unmodifiableList(Arrays.asList(arr))`
for a read-only live view, `List.copyOf(...)` for an immutable snapshot, and
`new ArrayList<>(Arrays.asList(arr))` when the caller needs to mutate freely.

`toArray`, by contrast, *does* copy:

```java
// Arrays.java:4246-4249
@Override
public Object[] toArray() {
    return Arrays.copyOf(a, a.length, Object[].class);
}
```

`Arrays.copyOf` allocates. So `toArray()` is your escape hatch back to an unaliased array —
one of the few methods on this class that is not a straight redirect.

### The varargs story (§2.3.13)

`asList` is `static <T> List<T> asList(T... a)` — a varargs method whose element type is the
type variable `T`. Two rules collide:

1. A type variable **cannot** bind to a primitive type. `T` may be `Integer`; it may never be `int`.
2. At a varargs call site, the compiler tries first to pass the argument through as the array
   `T[]` itself; only if that fails does it wrap the argument as a one-element array.

Call `Arrays.asList(new int[]{1,2,3})`. For rule 2's first attempt, `T[]` would have to be
`int[]`, i.e. `T = int` — forbidden by rule 1. So that inference fails, and the compiler
falls back to wrapping: the whole `int[]` becomes the single element. `T` binds to `int[]`,
the method is `asList(int[]... a)`, and you get a `List<int[]>` of `size() == 1`.

With `Integer[]`, rule 1 does not bite: `T = Integer` works, `T[] = Integer[]` matches the
argument directly, and you get a three-element `List<Integer>`. **The difference is entirely a
compile-time typing outcome** — the two calls compile to different method shapes. Nothing at
runtime distinguishes them, and nothing warns you: both compile clean under `-Xlint:all`.

The same trap fires for every primitive array — `long[]`, `double[]`, `char[]`, `boolean[]` —
and for exactly the same reason. `String[]`, `Integer[]` and any other reference array are
fine.

**Pitfall:** (§2.3.13) the wrong belief is that `asList` flattens any array, so
`Arrays.asList(intArray)` must give you a `List<Integer>`. The symptom is that it compiles
clean with no warning even under `-Xlint:all`, and then fails far from the call site — a loop
that runs exactly once, a `size()` of 1 where you expected `n`, or an inference error where
you consume the list as `List<Integer>`. The fix is to box explicitly with a stream:
`Arrays.stream(intArray).boxed().toList()`, or `IntStream.of(intArray).boxed().toList()`.

### Runnable

```java
import java.util.*;
import java.util.stream.IntStream;

public class AsList {
    public static void main(String[] args) {
        String[] arr = {"p", "q", "r"};
        List<String> al = Arrays.asList(arr);
        System.out.println("class = " + al.getClass().getName());
        System.out.println("is a java.util.ArrayList? " + (al instanceof java.util.ArrayList<?>));

        al.set(0, "MUTATED");
        System.out.println("after list.set(0,..) array = " + Arrays.toString(arr));
        arr[2] = "FROM_ARRAY";
        System.out.println("after arr[2]=..      list  = " + al);

        try {
            al.add("s");
        } catch (UnsupportedOperationException e) {
            System.out.println("add    caught: " + e.getClass().getSimpleName());
        }
        try {
            al.remove(0);
        } catch (UnsupportedOperationException e) {
            System.out.println("remove caught: " + e.getClass().getSimpleName());
        }
        al.sort(Comparator.naturalOrder());
        System.out.println("sort() allowed, array now = " + Arrays.toString(arr));

        int[] prim = {1, 2, 3};
        List<int[]> bad = Arrays.asList(prim);
        System.out.println("asList(int[]).size()      = " + bad.size());
        System.out.println("element 0 class           = " + bad.get(0).getClass().getName());
        System.out.println("element 0 == prim         -> " + (bad.get(0) == prim));

        Integer[] boxed = {1, 2, 3};
        System.out.println("asList(Integer[])         = " + Arrays.asList(boxed));
        System.out.println("fix, Arrays.stream        = " + Arrays.stream(prim).boxed().toList());
        System.out.println("fix, IntStream.of         = " + IntStream.of(prim).boxed().toList());
    }
}
```

Real output:

```
class = java.util.Arrays$ArrayList
is a java.util.ArrayList? false
after list.set(0,..) array = [MUTATED, q, r]
after arr[2]=..      list  = [MUTATED, q, FROM_ARRAY]
add    caught: UnsupportedOperationException
remove caught: UnsupportedOperationException
sort() allowed, array now = [FROM_ARRAY, MUTATED, q]
asList(int[]).size()      = 1
element 0 class           = [I
element 0 == prim         -> true
asList(Integer[])         = [1, 2, 3]
fix, Arrays.stream        = [1, 2, 3]
fix, IntStream.of         = [1, 2, 3]
```

Read `element 0 class = [I` — that is the JVM's descriptor for `int[]` — together with
`element 0 == prim -> true`: the primitive array did not become three elements, it became
*the* element, by reference. The `Integer[]` line one below, printing three elements from the
same method call, is the control. And note `sort() allowed, array now = [FROM_ARRAY, MUTATED, q]`:
the caller's `arr` was reordered by a method call on the list.

**Interview:** "`Arrays.asList(new int[]{1,2,3}).size()`?" — `1`. `asList` is generic over
`T`, `T` cannot be a primitive, so the compiler cannot treat `int[]` as `T[]` and wraps it
instead: `T = int[]`, one element.

> `Arrays.asList` returns `java.util.Arrays$ArrayList` — a `List` faceplate holding the
> caller's array by reference, so `set`/`sort`/`replaceAll` write through and `add`/`remove`
> throw; and because `T` cannot bind to a primitive, a primitive array binds as the single
> element.

---

## Pitfalls

### Treating `Arrays.asList` as `java.util.ArrayList`

**Wrong**

```java
String[] arr = {"r", "p", "q"};
List<String> l = Arrays.asList(arr);
l.sort(Comparator.naturalOrder());
System.out.println("after view sort, arr = " + Arrays.toString(arr));
try {
    l.add("s");
} catch (UnsupportedOperationException e) {
    System.out.println("l.add -> " + e.getClass().getSimpleName());
}
```

```
after view sort, arr = [p, q, r]
l.add -> UnsupportedOperationException
```

**Right**

```java
String[] arr = {"p", "q", "r"};
List<String> l = new ArrayList<>(Arrays.asList(arr));   // real, growable copy
l.add("s");
System.out.println(l + " | " + Arrays.toString(arr));   // [p, q, r, s] | [p, q, r]
```

**Why people believe it:** the returned class is *named* `ArrayList` —
`java.util.Arrays$ArrayList`, a `private static` nested class at `Arrays.java:4229` with one
field, `final E[] a`. Debuggers, `toString` and half the internet show "ArrayList" and the
reader supplies the wrong class from memory.

### Believing "fixed-size" means "read-only"

**Wrong**

```java
int[] scores = {5, 3, 9};
Integer[] boxed = {5, 3, 9};
List<Integer> shared = Arrays.asList(boxed);   // handed to a caller as "read-only"
shared.replaceAll(v -> 0);                     // caller does this
System.out.println(Arrays.toString(boxed));    // [0, 0, 0] — your array is gone
System.out.println(Arrays.toString(scores));   // [5, 3, 9] — untouched, different array
```

**Right**

```java
Integer[] boxed = {5, 3, 9};
List<Integer> shared = List.copyOf(Arrays.asList(boxed));  // genuine snapshot
try {
    shared.replaceAll(v -> 0);
} catch (UnsupportedOperationException e) {
    System.out.println("replaceAll -> " + e.getClass().getSimpleName());
}
System.out.println(Arrays.toString(boxed));                // [5, 3, 9] — safe
```

```
replaceAll -> UnsupportedOperationException
[5, 3, 9]
```

**Why people believe it:** the two throwing methods (`add`, `remove`) are the ones people
test, so the list feels locked down. But `Arrays$ArrayList` deliberately overrides `set`
(`Arrays.java:4269-4274`), `sort` (`:4318-4321`) and `replaceAll` (`:4309-4316`) to write the
backing array, while `add`/`remove` throw only because they were left un-overridden and fall
through to `AbstractList.java:154-170`. Fixed-size and immutable are different properties.

### Passing a primitive array to `Arrays.asList`

**Wrong**

```java
int[] prim = {1, 2, 3};
List<int[]> bad = Arrays.asList(prim);          // compiles clean under -Xlint:all
System.out.println("size = " + bad.size());     // 1
System.out.println("[0] class = " + bad.get(0).getClass().getName());   // [I
System.out.println("[0] == prim -> " + (bad.get(0) == prim));           // true
```

**Right**

```java
int[] prim = {1, 2, 3};
List<Integer> good = Arrays.stream(prim).boxed().toList();
System.out.println("size = " + good.size() + ", list = " + good);   // size = 3, list = [1, 2, 3]
```

**Why people believe it:** `Arrays.asList("a", "b", "c")` and
`Arrays.asList(new String[]{"a","b","c"})` both give three elements, so the method looks like
it flattens any array. It flattens only when the argument can bind to `T[]`, and `T` cannot be
a primitive — so `int[]` binds as `T` itself and the compiler produces a one-element list with
no warning. The failure surfaces far from the call site.

---

## Cheat sheet

| Claim | Truth (JDK 21) | Source |
|---|---|---|
| `Arrays.asList(arr).getClass()` | `java.util.Arrays$ArrayList` | `Arrays.java:4229` |
| ...is it a `java.util.ArrayList`? | **no** — unrelated class, same simple name | `Arrays.java:4229` |
| backing storage | the caller's array by reference, not a copy | `Arrays.java:4237-4239` |
| `size()` | `a.length` — no independent count, size is fixed | `Arrays.java:4242-4244` |
| `get(i)` | `a[i]` | `Arrays.java:4265-4267` |
| `set(i, v)` | writes `a[i]` — **write-through** | `Arrays.java:4269-4274` |
| `sort(c)` | `Arrays.sort(a, c)` — reorders the caller's array | `Arrays.java:4318-4321` |
| `replaceAll(op)` | rewrites `a` in place | `Arrays.java:4309-4316` |
| `add(x)` / `remove(i)` | `UnsupportedOperationException`, no message | `AbstractList.java:154-170` |
| why they throw | not overridden — inherited from `AbstractList` | `Arrays.java:4229` |
| `toArray()` | **copies** — `Arrays.copyOf(a, a.length, Object[].class)` | `Arrays.java:4246-4249` |
| interfaces implemented | `RandomAccess`, `Serializable` | `Arrays.java:4229-4231` |
| mutating `arr` directly | visible through the list immediately | measured |
| fixed-size vs immutable | fixed-**size** only; `set`/`sort`/`replaceAll` all write | `Arrays.java:4269/4319/4310` |
| `Arrays.asList(new int[]{1,2,3})` | `List<int[]>`, `size() == 1`, element `==` the array | `Arrays.java:4222` |
| `Arrays.asList(new Integer[]{1,2,3})` | `List<Integer>`, `size() == 3` | `Arrays.java:4222` |
| why the difference | `T` cannot bind to a primitive, so `int[]` binds as `T` | JLS varargs + type-variable bounds |
| warning at compile time | none, even under `-Xlint:all` | measured |
| primitive fix | `Arrays.stream(arr).boxed().toList()` / `IntStream.of(arr).boxed().toList()` | — |
| want a mutable list | `new ArrayList<>(Arrays.asList(arr))` | — |
| want an immutable list | `List.of(...)`, or `Arrays.stream(arr).toList()` if `null`s allowed | — |
| `List.of` vs `Arrays.stream(arr).toList()` | `List.of` rejects `null`; `toList()` accepts it | — |

---

## Self-test

**Q1.** Why is `Arrays.asList(new int[]{1,2,3}).size()` equal to 1, while `Arrays.asList(new Integer[]{1,2,3}).size()` is 3?

<details><summary>Answer</summary>

Compile-time typing. The signature is
`public static <T> List<T> asList(T... a)` (`Arrays.java:4222`). At a varargs call site the
compiler first tries to pass the argument straight through as `T[]`. For `int[]` that needs
`T = int`, and a type variable cannot bind to a primitive — so inference fails and the
compiler falls back to wrapping the argument as a one-element array: `T = int[]`, giving
`List<int[]>` with `size() == 1`, whose sole element is `==` the original array. For
`Integer[]`, `T = Integer` binds fine, `T[]` matches the argument directly, and you get three
elements. Nothing warns you — both compile clean under `-Xlint:all`. Fix for primitives:
`Arrays.stream(arr).boxed().toList()` or `IntStream.of(arr).boxed().toList()`.

</details>

**Q2.** `Arrays.asList` gives a fixed-size list. Does that make it read-only?

<details><summary>Answer</summary>

No — fixed-*size*, not read-only, and it can mutate memory you own. `Arrays$ArrayList`
overrides `set` to write the backing array (`Arrays.java:4269-4274`), `sort` to
`Arrays.sort(a, c)` (`:4318-4321`) and `replaceAll` to rewrite `a` in place (`:4309-4316`).
It does **not** override `add(int, E)` or `remove(int)`, so those come from `AbstractList`
(`AbstractList.java:154-170`) and throw `UnsupportedOperationException` unconditionally.
Measured: `Arrays.asList(arr).sort(naturalOrder())` reorders `arr` itself. For an actually
immutable list use `List.of(...)` or `Arrays.stream(arr).toList()`.

</details>

**Q3.** Is `Arrays.asList(arr)` a view, a copy, or a snapshot?

<details><summary>Answer</summary>

A **view**, in both directions. The constructor is
`ArrayList(E[] array) { a = Objects.requireNonNull(array); }` (`Arrays.java:4237-4239`) — it
stores the reference and clones nothing. So `list.set(0, x)` writes `arr[0]`, and
`arr[2] = y` is immediately visible through `list.get(2)`. Measured:
`after list.set(0,..) array = [MUTATED, q, r]` and then
`after arr[2]=.. list = [MUTATED, q, FROM_ARRAY]`. It is not a snapshot in any sense; the only
copying method on the class is `toArray()`, which goes through
`Arrays.copyOf` (`:4246-4249`).

</details>

**Q4.** Why does `add` throw on `Arrays$ArrayList` when `set` does not, given both mutate?

<details><summary>Answer</summary>

Because `set` was overridden and `add` was not. `Arrays$ArrayList` overrides `size`,
`toArray`, `get`, `set`, `indexOf`, `contains`, `spliterator`, `forEach`, `replaceAll`, `sort`
and `iterator` — all of which can be expressed against a fixed-length array. `add(int, E)` and
`remove(int)` cannot, so they are simply left inherited, and `AbstractList`'s versions
(`AbstractList.java:154-170`) are bare `throw new UnsupportedOperationException();` with no
message. There is no explicit "fixed size" flag or guard anywhere in the class; the restriction
is an artefact of which methods the JDK chose to implement.

</details>

**Q5.** You need to hand a caller a read-only view of a `String[]` you will keep mutating. Does `Arrays.asList` do the job?

<details><summary>Answer</summary>

No, twice over. It is not read-only — the caller can `set`, `sort` or `replaceAll` through it
and rewrite your array. And "view" cuts the wrong way for the other side of the contract: if
you want the caller to *see* your later mutations, the aliasing is right but the writability
is a hole; if you want them to see a frozen state, you need a copy. Use
`Collections.unmodifiableList(Arrays.asList(arr))` for a genuinely read-only live view, or
`List.copyOf(Arrays.asList(arr))` for an immutable snapshot. Note `List.copyOf` and `List.of`
both reject `null` elements; `Arrays.stream(arr).toList()` does not.

</details>

**Q6.** Does `Arrays.asList` warn you about the primitive-array trap at compile time?

<details><summary>Answer</summary>

No. `Arrays.asList(new int[]{1,2,3})` compiles clean under `-Xlint:all` on JDK 21 — measured.
It is a perfectly legal call: `T` infers to `int[]`, and `asList` is annotated `@SafeVarargs`
with `@SuppressWarnings("varargs")` (`Arrays.java:4220-4221`), so even the usual
generic-varargs warning is silenced. The declared result type is `List<int[]>`, so the mistake
is only caught if you assign it to `List<Integer>` — which is why the failure typically
surfaces as a surprising `size() == 1` far from the call site rather than as a compile error.

</details>

---

**Leaves covered:** 2.3.12–2.3.13 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 507
