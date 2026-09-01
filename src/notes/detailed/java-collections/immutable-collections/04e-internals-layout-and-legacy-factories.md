# 02 Java Collections — Immutability and views — INTERNALS (§3.12.17–3.12.18)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [immutable-collections/04d-internals-sublist-and-reversed-view.md](04d-internals-sublist-and-reversed-view.md) · Next: [concurrent-collections/01-thread-safety-and-wrappers.md](../concurrent-collections/01-thread-safety-and-wrappers.md)

This file closes `immutable-collections/`. It covers the **memory layout** of the small immutable lists
against `ArrayList` (3.12.17) and the **pre-Java-9 legacy factories** `Collections.emptyList()` /
`singletonList()` (3.12.18). The mutator wall and the `CollSer` serial proxy are in
[04c-internals-mutators-serialization-and-views.md](04c-internals-mutators-serialization-and-views.md);
the two views in [04d-internals-sublist-and-reversed-view.md](04d-internals-sublist-and-reversed-view.md).

Source citations are against JDK 21 `src.zip`: `java.base/java/util/` `ImmutableCollections.java`,
`Collections.java`, `ArrayList.java`, `AbstractList.java`. Every transcript below is real output from
**JDK 21.0.7, HotSpot 64-Bit Server VM, aarch64 (macOS)**. Code snippets are shown without imports or
`main` scaffolding.

## The four single-and-empty list options

| | `List.of()` / `List.of(x)` | `Collections.emptyList()` | `Collections.singletonList(x)` | `Arrays.asList(x)` |
|---|---|---|---|---|
| Since | 9 | 1.3 (`EMPTY_LIST` 1.2) | 1.3 | 1.2 |
| Class | `ListN` / `List12` | `Collections$EmptyList` | `Collections$SingletonList` | `Arrays$ArrayList` |
| Allocates per call | no / yes | **no** | **yes** | yes |
| Rejects `null` | **yes** | n/a | no | no |
| Silent no-op mutators | none | `clear`, `sort`, `removeIf`, `replaceAll` | `sort` | — |

---

## Layout arithmetic: `List.of(a,b)` vs `new ArrayList<>` (3.12.17)

**Mental model.** `List.of(a, b)` is one object with two reference fields. There is no array and no
capacity concept, so there is nothing to be slack. An `ArrayList` is always **two** objects — list plus
backing array — and the array's size depends on *how it was built*.

**Why it matters.** Small lists dominate real code: request headers, two-element key tuples, an
enum-pair whitelist. At a million live instances the difference between 24 B and 80 B is 56 MB.

**Mechanism.** `ImmutableCollections.java:553-572`:

```java
@jdk.internal.ValueBased
static final class List12<E> extends AbstractImmutableList<E>
        implements Serializable {

    @Stable
    private final E e0;

    @Stable
    private final Object e1;

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

Two `@Stable` reference fields and nothing else — no `size`, no `modCount`, no array pointer. `size()`
at line 575 is `e1 != EMPTY ? 2 : 1`, and the comment says why the sentinel is `EMPTY` rather than
`null`: `e1 != EMPTY` constant-folds, which `e1 != null` would not for a `@Stable` field that may
legitimately hold null.

**[NUM] The arithmetic.** Assume **compressed oops** — the HotSpot default below a ~32 GB heap; above
that, or with `-XX:-UseCompressedOops`, every reference and the class word become 8 B and all three
figures grow. Object header 12 B (8 mark + 4 class), array header 16 B (12 + 4 length), reference 4 B,
`int` 4 B, everything padded to a multiple of 8.

| Expression | Objects | Field arithmetic | Total |
|---|---|---|---|
| `List.of(a, b)` → `List12` | 1 | 12 hdr + 4 (`e0`) + 4 (`e1`) = 20 → pad **24** | **24 B** |
| `new ArrayList<>(List.of(a, b))` | 2 | list 12 + 4 `modCount` + 4 `size` + 4 `elementData` = **24**; array len **2** = 16 + 8 = **24** | **48 B** |
| `new ArrayList<>()` then 2× `add` | 2 | list **24**; array len **10** = 16 + 40 = **56** | **80 B** |

`ArrayList`'s three fields are `modCount` (`AbstractList.java:630`), `size` (`ArrayList.java:145`) and
`elementData` (`ArrayList.java:138`).

**[PROVE] Why rows 2 and 3 differ.** Different capacity paths, and the leaf names only the first — the
distinction is the interesting part:

- `ArrayList.java:180-192` — `Object[] a = c.toArray(); if ((size = a.length) != 0) { if (c.getClass() == ArrayList.class) elementData = a; else elementData = Arrays.copyOf(a, size, Object[].class); }`.
  `List12.toArray()` returns `new Object[]{e0, e1}`, already `Object[].class`, but the guard tests
  `c.getClass() == ArrayList.class`, which is false — so it copies to an array of length **exactly
  `size` = 2**. Sized to fit, **zero slack**.
- `new ArrayList<>()` starts on the shared `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` and on the first `add`
  grows to `DEFAULT_CAPACITY = 10` (`ArrayList.java:118`). Two elements in ten slots leaves **8 slots =
  32 B of slack**.

So the honest statement is: `List.of(a,b)` is **2× cheaper than the copy-constructor form** and
**3.33× cheaper than the default-constructor-plus-`add` form**. The often-quoted "10-slot array, 8
slots wasted" figure describes only row 3 — it is not what `new ArrayList<>(List.of(a,b))` does.

Single-shot corroboration — a `Runtime` delta over 1,000,000 live instances, with the two `String`s
hoisted out because they are the same objects every iteration:

```java
static final int N = 1_000_000;

static long measure(String label, Supplier<Object> f) {
    Object[] keep = new Object[N];
    Runtime rt = Runtime.getRuntime();
    for (int i = 0; i < 3; i++) System.gc();
    long before = rt.totalMemory() - rt.freeMemory();
    for (int i = 0; i < N; i++) keep[i] = f.get();
    for (int i = 0; i < 3; i++) System.gc();
    long after = rt.totalMemory() - rt.freeMemory();
    long per = (after - before) / N;
    System.out.printf("%-34s ~%d B/instance%n", label, per);
    if (keep[N - 1] == null) throw new AssertionError();
    return per;
}

String a = "a", b = "b";
long l12 = measure("List.of(a,b)", () -> List.of(a, b));
long al = measure("new ArrayList<>(List.of(a,b))", () -> new ArrayList<>(List.of(a, b)));
long al10 = measure("new ArrayList<>() + 2 add", () -> {
    List<String> x = new ArrayList<>();
    x.add(a);
    x.add(b);
    return x;
});
System.out.printf("ratios: copy/List12=%.2f  grown/List12=%.2f%n", (double) al / l12, (double) al10 / l12);
```

Run as `java -Xmx3g -cp out Footprint`. Real output:

```
List.of(a,b)                       ~24 B/instance
new ArrayList<>(List.of(a,b))      ~48 B/instance
new ArrayList<>() + 2 add          ~80 B/instance
ratios: copy/List12=2.00  grown/List12=3.33
```

This is a **single-shot heap-delta reading, not a measurement tool**: claim the **ratios** (2.00 and
3.33) and treat the absolute bytes as confirmation of the arithmetic above, not independent evidence.
For real layout inspection use JOL (`ClassLayout.parseInstance(x).toPrintable()`); reflective
inspection of `java.util` internals needs `--add-opens java.base/java.util=ALL-UNNAMED`.

**Pitfall:** the 24 B figure covers sizes 1 and 2 only. `List.of(a, b, c)` is a `ListN`
(`ImmutableCollections.java:222`) and is back to two objects: `ListN` is 12 + 4 (`elements`) + 1
(`allowNulls`) = 17 → **24 B**, plus a length-3 array at 16 + 12 = 28 → **32 B** = **56 B**. The
single-object trick is a 1–2 element special case — exactly the sizes that dominate real code, which is
why the JDK bothered with a dedicated class for them.

**Interview:** *"Is `List.of` cheaper than `new ArrayList<>`?"* For 1–2 elements yes, and by a factor
you should be able to derive: one 24-byte object with no array, versus 48 B for the copy constructor
(exactly-sized array) or 80 B for the no-arg constructor plus `add` (10-slot array). From size 3 up it
is two objects again and the gap narrows to the `modCount`/`size` fields plus slack.

> **Definition.** Under compressed oops, `List.of(a,b)` is a single 24-byte `List12` with two reference
> fields and no backing array; `new ArrayList<>(List.of(a,b))` is 48 bytes (24 B list + 24 B
> exactly-sized array), and `new ArrayList<>()` plus two `add` calls is 80 bytes (24 B list + 56 B
> ten-slot array).

---

## The legacy factories today (3.12.18)

**Mental model.** `Collections.emptyList()` and `singletonList()` were the 1999-era "don't allocate for
the degenerate case" path. `emptyList()` still wins on identity — it is a shared constant — but its
*semantics* are looser than `List.of()`, and the looseness is a bug factory.

**Why they exist.** `Collections.EMPTY_LIST` is Java **1.2**; `emptyList()` and `singletonList()` are
Java **1.3** (`Collections.java:4748`, `4771`, `5150`). They predate generics and any general
immutable-collection factory. `List.of()` is Java **9**.

**Which is cheaper?** `Collections.java:4748` and `4771-4772`:

```java
public static final List EMPTY_LIST = new EmptyList<>();

public static final <T> List<T> emptyList() {
    return (List<T>) EMPTY_LIST;
}
```

versus `ImmutableCollections.java:105` (`EMPTY_LIST = new ListN<>(new Object[0], false)`) reached via
`listFromTrustedArray`'s `case 0` at line 219. **Both return a shared singleton; neither allocates.**
There is no allocation difference at all, and "use `emptyList()` to avoid allocation" has been obsolete
since Java 9. They are *different* singletons: `Collections.emptyList() == List.of()` is `false`, and
the classes are `Collections$EmptyList` and `ImmutableCollections$ListN`.

`singletonList` is the opposite: `Collections.java:5150-5151` is `return new SingletonList<>(o);` — a
**fresh allocation every call**, like `List.of(x)`'s fresh `List12`. Sizes tie: `List12` is 24 B, and
`SingletonList` is 12 hdr + 4 (`element`) + 4 (`modCount`, inherited from `AbstractList`) = 20 → 24 B.
So the real answer to "which is cheaper" is **neither — choose on semantics.**

**Where they genuinely differ.** `SingletonList` extends `AbstractList` (`Collections.java:5157-5159`)
and overrides only some defaults, `Collections.java:5188-5198`:

```java
@Override
public boolean removeIf(Predicate<? super E> filter) {
    throw new UnsupportedOperationException();
}
@Override
public void replaceAll(UnaryOperator<E> operator) {
    throw new UnsupportedOperationException();
}
@Override
public void sort(Comparator<? super E> c) {
}
```

`sort` is an **empty body** — a *silent no-op*, not a throw. It is trivially correct for one element,
but it is a behavioural divergence. `EmptyList` is looser still: `Collections.java:4793` is
`public void clear() {}`, and lines 4816-4827 are

```java
@Override
public boolean removeIf(Predicate<? super E> filter) {
    Objects.requireNonNull(filter);
    return false;
}
@Override
public void replaceAll(UnaryOperator<E> operator) {
    Objects.requireNonNull(operator);
}
@Override
public void sort(Comparator<? super E> c) {
}
```

Four silent no-ops — `clear`, `removeIf`, `replaceAll`, `sort` — where
`AbstractImmutableList.sort`/`clear` (`ImmutableCollections.java:263`, `149`) throw. `EmptyList` also
carries `readResolve()` at lines 4839-4842 returning `EMPTY_LIST`, which is how the singleton survives
a serialization round trip; `List.of()` gets the same property for free from `readResolve`'s
`case 0` (see [04c](04c-internals-mutators-serialization-and-views.md)).

| Operation | `Collections.emptyList()` | `Collections.singletonList(x)` | `List.of()` / `List.of(x)` | `Arrays.asList(x)` |
|---|---|---|---|---|
| Identity across calls | shared singleton | new object each call | shared singleton / new object | new each call |
| `add` | UOE | UOE | UOE | UOE |
| `set(0, y)` | IndexOutOfBounds | **UOE** | UOE | **succeeds** |
| `clear()` | **silent no-op** | UOE | **UOE** | UOE |
| `sort(null)` | **silent no-op** | **silent no-op** | **UOE** | succeeds |
| `removeIf` | **silent `false`** | UOE | **UOE** | UOE |
| accepts `null` element | n/a | yes → `[null]` | **NPE** | yes |
| `contains(null)` | `false` | `false` | **NPE** | `false` |
| Serializable | yes (`readResolve` keeps singleton) | yes (if element is) | yes (via `CollSer`) | yes |
| `reversed()` (Java 21) | `Rand`, modifiable=**true** | same | `Rand`, modifiable=**false** | `Rand`, true |

Real output confirming every surprising cell — every throwing call inside try/catch, so it runs to
completion:

```
emptyList() identical across calls: true
List.of() identical across calls  : true
emptyList()==List.of()            : false
singletonList identical           : false
emptyList class=java.util.Collections$EmptyList  List.of class=java.util.ImmutableCollections$ListN
emptyList.clear -> NO THROW
emptyList.sort -> NO THROW
emptyList.removeIf -> NO THROW
emptyList.add -> UnsupportedOperationException
List.of().clear -> UnsupportedOperationException
List.of().sort -> UnsupportedOperationException
singletonList.sort -> NO THROW
singletonList.set -> UnsupportedOperationException
singletonList.removeIf -> UnsupportedOperationException
asList.set -> NO THROW
singletonList(null)=[null]
List.of(null) -> NullPointerException
emptyList().contains(null)=false
List.of().contains(null) -> NullPointerException
```

The harness, for transcription:

```java
record Attempt(String label, Runnable body) {}
List<String> el = Collections.emptyList();
List<String> sl = Collections.singletonList("a");
for (Attempt a : List.of(
        new Attempt("emptyList.clear",        el::clear),
        new Attempt("emptyList.sort",         () -> el.sort(null)),
        new Attempt("emptyList.removeIf",     () -> el.removeIf(s -> true)),
        new Attempt("emptyList.add",          () -> el.add("x")),
        new Attempt("List.of().clear",        () -> List.of().clear()),
        new Attempt("List.of().sort",         () -> List.<String>of().sort(null)),
        new Attempt("singletonList.sort",     () -> sl.sort(null)),
        new Attempt("singletonList.set",      () -> sl.set(0, "b")),
        new Attempt("singletonList.removeIf", () -> sl.removeIf(s -> true)),
        new Attempt("asList.set",             () -> Arrays.asList("a").set(0, "b")))) {
    try { a.body().run(); System.out.println(a.label() + " -> NO THROW"); }
    catch (RuntimeException e) { System.out.println(a.label() + " -> " + e.getClass().getSimpleName()); }
}
```

**Pitfall:** a widely repeated claim says `Collections.singletonList` is "mutable via `set`". It is
**not**. `SingletonList` extends `AbstractList` without overriding `set`, so `AbstractList.set` throws
`UnsupportedOperationException` (`AbstractList.java:137-139`). The single-element list that *is*
mutable via `set` is `Arrays.asList(x)` — see [01d-arrays-aslist.md](01d-arrays-aslist.md).

**Verdict.** Prefer `List.of()` / `List.of(x)` in new code — not for allocation reasons, there are none
for the empty case, but because it **throws instead of silently doing nothing**, which turns "sorting a
list you thought was mutable" from silent into loud. Use `Collections.singletonList(x)` only when you
must hold a `null`, and `emptyList()` only when matching an existing API's exact return identity.

**Interview:** *"`Collections.emptyList()` or `List.of()`?"* `List.of()` — both are allocation-free
shared singletons, so it is not a performance question; `List.of()` rejects `null` and throws from
`sort`/`clear`/`removeIf` where `emptyList()` silently no-ops.

> **Definition.** `Collections.emptyList()` returns the shared `EMPTY_LIST` singleton and
> `singletonList(x)` allocates a fresh `SingletonList`; both are as cheap as their Java 9 counterparts
> but implement several mutators as silent no-ops and accept `null`, which is why `List.of()` —
> fail-loud and null-hostile — is the better default.

---

## Pitfalls

### Believing `List.of(a,b)` beats `ArrayList` by "the ten-slot array"

**Wrong**

```java
var a = new ArrayList<>(List.of("a", "b"));   // "56-byte array, 8 slots wasted"
```

`new ArrayList<>(Collection)` sizes the array to exactly `size` (`ArrayList.java:186`). Measured 48 B
total, not 80 B.

**Right**

```java
var a = new ArrayList<String>();  a.add("a");  a.add("b");   // THIS path grows to DEFAULT_CAPACITY = 10 -> 80 B
```

**Why people believe it:** `DEFAULT_CAPACITY = 10` is the most-quoted constant in `ArrayList`, and it
does apply — just only to the no-arg constructor path.

### Reaching for `Collections.emptyList()` "to avoid the allocation"

**Wrong**

```java
return items.isEmpty() ? Collections.emptyList() : List.copyOf(items);   // "List.of() would allocate"
```

**Right**

```java
return List.copyOf(items);   // empty input already yields the shared EMPTY_LIST singleton
```

Verified: `List.of() == List.of()` is `true`, and so is `Collections.emptyList() == Collections.emptyList()`.
Both are shared constants — `Collections.java:4748` and `ImmutableCollections.java:105`, the latter
reached via `listFromTrustedArray`'s `case 0` at line 219. They are, however, *different* objects:
`Collections.emptyList() == List.of()` is `false`.

**Why people believe it:** it was true advice in 2005, when the alternative was `new ArrayList<>(0)`.
Nothing updated the folklore when Java 9 shipped an equally shared empty singleton.

### Expecting `Collections.emptyList().clear()` to throw

**Wrong**

```java
List<String> l = maybeEmpty();          // sometimes Collections.emptyList()
l.clear();                              // silently succeeds — no signal that l was immutable
l.sort(Comparator.naturalOrder());      // silently succeeds too
```

**Right**

```java
List<String> l = maybeEmpty();          // now always List.of() when empty
try {
    l.clear();
} catch (UnsupportedOperationException e) {
    System.out.println("caught: immutable, as designed");   // the bug surfaces here, in a test
}
```

`Collections.java:4793` is literally `public void clear() {}`, and lines 4816-4827 make `removeIf`
return `false`, `replaceAll` a no-op and `sort` a no-op. All silent. Verified: `emptyList.clear`,
`emptyList.sort`, `emptyList.removeIf` all print `NO THROW`, while the `List.of()` equivalents throw.

**Why people believe it:** the javadoc calls the list "immutable", and immutable collections elsewhere
in `java.util` throw. `EmptyList` reasons that a no-op on an empty list changes nothing, so it is
vacuously correct — which is true, and useless for catching the bug.

### Believing `singletonList` is mutable via `set`

**Wrong**

```java
List<String> l = Collections.singletonList("a");
try { l.set(0, "b"); } catch (RuntimeException e) { System.out.println(e.getClass().getSimpleName()); }
// UnsupportedOperationException
```

**Right** — the fixed-size-but-mutable single-element list is `Arrays.asList`:

```java
List<String> l = Arrays.asList("a");
l.set(0, "b");          // succeeds, writes through to the backing array
System.out.println(l);  // [b]
```

**Why people believe it:** `singletonList` and `Arrays.asList` are both "fixed size", both from the
1.2/1.3 era, and both `RandomAccess` — so the `set` behaviour gets conflated. `SingletonList` extends
`AbstractList` without overriding `set` (`Collections.java:5157-5159`), so `AbstractList.set` throws
(`AbstractList.java:137-139`).

---

## Cheat sheet

| Thing | Fact |
|---|---|
| Compressed-oops units | header 12 B, array header 16 B, ref 4 B, `int` 4 B, pad to 8 |
| `List12` fields | `e0`, `e1` only — no `size`, no `modCount`, no array |
| `List12` size trick | `size()` is `e1 != EMPTY ? 2 : 1`; `EMPTY` sentinel so it constant-folds |
| `List.of(a,b)` | one object, 12 + 4 + 4 = 20 → **24 B** |
| `new ArrayList<>(List.of(a,b))` | 24 B list + exactly-sized 2-array (16 + 8) = **48 B**, 0 slack |
| Why exactly sized | `Arrays.copyOf(a, size, Object[].class)` at `ArrayList.java:186` |
| `new ArrayList<>()` + 2 `add` | 24 B list + 10-slot array (16 + 40 = 56) = **80 B**, 8 slots slack |
| `DEFAULT_CAPACITY` | 10 (`ArrayList.java:118`) — **no-arg constructor path only** |
| Ratios (measured) | copy/`List12` = **2.00**; grown/`List12` = **3.33** |
| `List.of(a,b,c)` | `ListN` — two objects again, 24 + 32 = **56 B** |
| `ArrayList` fields | `modCount` (`AbstractList:630`), `size` (`:145`), `elementData` (`:138`) |
| `emptyList()` vs `List.of()` | Both shared singletons, both allocation-free, **different objects** |
| `emptyList()` silent no-ops | `clear` (`:4793`), `removeIf`/`replaceAll`/`sort` (`:4816-4827`) |
| `singletonList(x)` | Allocates every call; `set` **throws**; `sort` is a **silent no-op** (`:5196-5198`) |
| `singletonList` size | 12 + 4 `element` + 4 `modCount` = **24 B** — ties with `List12` |
| Mutable 1-element list | `Arrays.asList(x)` — `set` succeeds. **Not** `singletonList` |
| Nulls | `singletonList(null)` → `[null]`; `List.of(null)` → NPE; `List.of().contains(null)` → NPE |
| Which is cheaper | **Neither.** Choose on semantics: fail-loud (`List.of`) vs null-tolerant (legacy) |
| Version map | `EMPTY_LIST` 1.2, `emptyList`/`singletonList` 1.3, `List.of` 9 |

---

## Self-test

**Q1.** `new ArrayList<>(List.of("a","b"))` — how many bytes, and why is it not 80?

<details><summary>Answer</summary>

48 B under compressed oops: a 24 B `ArrayList` (12 hdr + 4 `modCount` + 4 `size` + 4 `elementData`)
plus a 24 B array of length exactly 2 (16 hdr + 2×4). Not 80, because the collection constructor
(`ArrayList.java:180-192`) does `Arrays.copyOf(a, size, Object[].class)` — sized to `size`, zero slack.
`DEFAULT_CAPACITY = 10` (`ArrayList.java:118`) applies only to the *no-arg* constructor plus `add`
path, which is the 80 B case (24 + 56). `List12` itself is 24 B with no array, so the measured ratios
are 2.00× and 3.33×.

</details>

**Q2.** Which is cheaper today, `Collections.emptyList()` or `List.of()`? Which should you write?

<details><summary>Answer</summary>

Neither is cheaper — both return a shared singleton and allocate nothing.
`Collections.emptyList()` returns `EMPTY_LIST` (`Collections.java:4748`, `4771-4772`); `List.of()`
returns `ImmutableCollections.EMPTY_LIST` via `listFromTrustedArray` `case 0`
(`ImmutableCollections.java:219`, backed by `:105`). They are *different* objects, so
`Collections.emptyList() == List.of()` is `false`. Write `List.of()`, for semantics not speed:
`Collections.emptyList().clear()`, `.sort(null)` and `.removeIf(p)` are **silent no-ops**
(`Collections.java:4793`, `4816-4827`), while `List.of()` throws from all three.

</details>

**Q3.** True or false: `Collections.singletonList("a").set(0, "b")` succeeds, because a singleton list
has a fixed size but a mutable slot.

<details><summary>Answer</summary>

False, and it is a widely repeated error. `SingletonList` extends `AbstractList`
(`Collections.java:5157-5159`) and never overrides `set`, so `AbstractList.set` throws
`UnsupportedOperationException` (`AbstractList.java:137-139`). Verified. The fixed-size-but-mutable
list *is* `Arrays.asList("a")`, whose `set` writes through to the backing array. What `SingletonList`
does let through silently is `sort(Comparator)` — `Collections.java:5196-5198` is an empty body —
trivially correct for one element, but a behavioural divergence from `List.of("a").sort(null)`, which
throws.

</details>

**Q4.** Why is `List12.e1` initialised to a sentinel called `EMPTY` rather than to `null` in the
one-argument constructor?

<details><summary>Answer</summary>

Because a `null` there would defeat constant folding — and the JDK says so in the constructor itself.
`ImmutableCollections.java:562-566`:

```java
        List12(E e0) {
            this.e0 = Objects.requireNonNull(e0);
            // Use EMPTY as a sentinel for an unused element: not using null
            // enables constant folding optimizations over single-element lists
            this.e1 = EMPTY;
        }
```

The same comment is repeated for sets at `ImmutableCollections.java:789-793`, with a typo in the JDK
that is worth quoting as written rather than silently corrected — `enable`, not `enables`:

```java
        Set12(E e0) {
            this.e0 = Objects.requireNonNull(e0);
            // Use EMPTY as a sentinel for an unused element: not using null
            // enable constant folding optimizations over single-element sets
            this.e1 = EMPTY;
        }
```

What the comment means is visible in the field declarations two lines up,
`ImmutableCollections.java:556-560`:

```java
        @Stable
        private final E e0;

        @Stable
        private final Object e1;
```

`@Stable` permits the JIT to fold a field's value as a constant after first read, but only for
**non-default** values: `null` *is* the default for a reference field, so the JIT cannot distinguish
"initialised to null" from "not yet initialised" and declines to fold it. A non-null sentinel keeps
`e1` foldable, so `size()` (`e1 != EMPTY ? 2 : 1`, line 575) and `get(1)` can fold to constants for a
one-element list. There are 18 `@Stable` annotations in the file, and `List12` is additionally
`@jdk.internal.ValueBased` at line 552 — the adjacent reason the class is written to be foldable at
all, and the reason you must never lock on or `==` one.

</details>

**Q5.** `List.of(a, b, c)` — is it still one object? Give the bytes.

<details><summary>Answer</summary>

No. `listFromTrustedArray`'s `default` arm (`ImmutableCollections.java:222`) builds a `ListN`, which is
two objects: the `ListN` itself is 12 hdr + 4 (`elements` ref) + 1 (`allowNulls` boolean) = 17 → padded
to **24 B**, plus a length-3 `Object[]` at 16 hdr + 3×4 = 28 → padded to **32 B** = **56 B** total. The
single-object trick is a size-1-and-2 special case only — which is why a dedicated `List12` class
exists at all, since those are the sizes that dominate real code.

</details>

**Q6.** You need an immutable single-element list that may hold `null`. What are your options?

<details><summary>Answer</summary>

`Collections.singletonList(null)` — verified to yield `[null]` — or `Stream.of((T) null).toList()`,
which goes through `listFromTrustedArrayNullsAllowed` and produces a `ListN` with `allowNulls = true`
(tagged `IMM_LIST_NULLS = 4` on the wire). `List.of(null)` throws `NullPointerException`: every
`List.of` overload runs `Objects.requireNonNull` per element (`ImmutableCollections.java:192`, `215`).
Note the knock-on: `List.of().contains(null)` also throws NPE, while
`Collections.emptyList().contains(null)` returns `false`. Both verified.

</details>

**Q7.** Your service returns 2 million small lists per request cycle. Which construction do you pick,
and what is the saving?

<details><summary>Answer</summary>

`List.of(a, b)` — 24 B per instance versus 48 B for `new ArrayList<>(List.of(a,b))` and 80 B for
`new ArrayList<>()` plus two `add` calls. At 2 M live instances that is 48 MB versus 96 MB versus 160 MB
of retained heap for the list objects alone (elements shared and excluded). Measured ratios 2.00× and
3.33×. Caveats to state in the same breath: the figures assume **compressed oops** and grow with
`-XX:-UseCompressedOops` or a >32 GB heap; and the advantage collapses at size 3, where `ListN` is
two objects again (56 B). If the caller needs to mutate the result, none of this applies — you would
be trading a copy for the saving.

</details>

**Q8.** `Collections.emptyList()` survives a serialization round trip as the *same* object. How, and
does `List.of()` do the same?

<details><summary>Answer</summary>

`EmptyList` declares `private Object readResolve() { return EMPTY_LIST; }` (`Collections.java:4839-4842`)
— the comment there is literally *"Preserves singleton property"*. `List.of()` gets the equivalent for
free through the `CollSer` proxy: `readResolve`'s `case IMM_LIST` calls `List.of(array)`, and a
zero-length array reaches `listFromTrustedArray`'s `case 0 -> ImmutableCollections.EMPTY_LIST`
(`ImmutableCollections.java:219`), the shared instance. Verified: round-tripping `List.of()` gives
`same=true`, and it is the only member of the immutable family that does. See
[04c-internals-mutators-serialization-and-views.md](04c-internals-mutators-serialization-and-views.md).

</details>

---

## Where next

That closes `immutable-collections/`. Everything so far assumed a single thread, or immutability strong
enough that threads did not matter. The next folder drops both assumptions:
[concurrent-collections/01-thread-safety-and-wrappers.md](../concurrent-collections/01-thread-safety-and-wrappers.md)
starts from `Collections.synchronizedList` — the same view-delegation shape as `SubList` and
`ReverseOrderListView` in [04d](04d-internals-sublist-and-reversed-view.md), but wrapping every call in
a monitor — and shows why that is not enough.

---

**Leaves covered:** 3.12.17–3.12.18 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 606
