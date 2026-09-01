# 03 Java Core — The `Arrays` utilities and `System.arraycopy` — BASICS (§1.22, 1.22.8–1.22.10)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Array covariance and mutability](01a-covariance-and-mutability.md) · Next: [Array memory layout and bounds checking](01c-memory-layout-and-bounds.md)

This file covers the seventeen-method `java.util.Arrays` surface (§1.22.8), the two traps hiding inside `Arrays.asList` (§1.22.9), and `System.arraycopy` as the intrinsic that the whole surface bottoms out into (§1.22.10). It hands off array covariance and `ArrayStoreException` as subjects, `clone()`'s shallowness, and "arrays are always mutable" to `01a-covariance-and-mutability.md`; array memory arithmetic and bounds-check elimination to `01c-memory-layout-and-bounds.md`; varargs mechanics and the `f(Object)`/`f(Object[])` ambiguity to `01d-varargs-and-choosing-arrays.md`; and `equals`/`hashCode` contracts, `Comparable`/`Comparator`, wrapper boxing costs, and the master cost model to their owning files, linked at the point each is touched.

Seventeen methods is not seventeen things worth an interview answer — most of the surface is a convenience wrapper with no tradeoff. The reference table below is the thing to memorize; the three sections after it are the parts that actually bite.

## Reference table — the full §1.22.8 surface

| Method | Copies or views? | Shallow/deep | Cost | Note |
|---|---|---|---|---|
| `copyOf(T[], int)` | Copies | Shallow | O(n) | Truncates or null-pads to `newLength` |
| `copyOf(U[], int, Class)` | Copies | Shallow | O(n) | Lets the copy have a different runtime array type |
| `copyOfRange(T[], from, to)` | Copies | Shallow | O(to−from) | Half-open `[from, to)`; `to` may exceed length, zero/null-fills the tail |
| `fill(T[], val)` | Mutates in place | — | O(n) | Every slot gets the *same reference* for object arrays |
| `setAll(T[], IntFunction)` | Mutates in place | — | O(n) | Generator runs per index → distinct references |
| `sort(T[])` | Mutates in place | — | O(n log n) | Dual-pivot quicksort on primitives, TimSort (stable) on references |
| `parallelSort(T[])` | Mutates in place | — | O(n log n), parallel above a threshold | Falls back to sequential below `MIN_ARRAY_SORT_GRAN` |
| `binarySearch(T[], key)` | Reads only | — | O(log n) | Requires sorted input; miss returns `-(insertion point) - 1` |
| `equals(T[], T[])` | Reads only | **Shallow** | O(n) | Element `equals`; for `T[][]` this is reference equality per row |
| `deepEquals(Object[], Object[])` | Reads only | **Deep** | O(n) recursive | Recurses into nested arrays and element `equals` |
| `hashCode(T[])` | Reads only | **Shallow** | O(n) | Combines element hash codes one level deep |
| `deepHashCode(Object[])` | Reads only | **Deep** | O(n) recursive | Recurses into nested arrays |
| `toString(T[])` | Reads only | **Shallow** | O(n) | One level of `[e1, e2, e3]`-style output; nested arrays print as a raw `@hash` descriptor |
| `deepToString(Object[])` | Reads only | **Deep** | O(n) recursive | Recurses, cycle-safe |
| `mismatch(T[], T[])` | Reads only | — | O(n) | Java 9+. First differing index, or `-1` if one is a prefix of the other |
| `compare(T[], T[])` | Reads only | — | O(n) | Java 9+. Lexicographic; shorter-but-equal-prefix array is "less" |
| `asList` (varargs) | **Views**, fixed-size | Shallow | O(1) alloc, O(n) if varargs boxed an array | `[TRAP]` — see below |
| `stream(T[])` | Views (lazily) | — | O(1) to build | `Stream<T>` for references, `IntStream`/`LongStream`/`DoubleStream` for primitives |

The shallow/deep split repeats three times — `equals`/`deepEquals`, `hashCode`/`deepHashCode`, `toString`/`deepToString` — because it is one design decision applied consistently, not three unrelated pairs. That decision is worth its own concept.

## 1. The shallow/deep pairs, and why the JDK needed both (1.22.8)

Picture a `PaymentRun`'s withdrawal batches, one array of `LedgerEntry[]` per settlement window, four windows a day. Comparing two of these structurally — "did window 1 today produce the same batches as window 1 yesterday" — needs to walk *into* the rows. Comparing them the naive way only compares the row references, and two structurally identical grids built from two separate loops come back unequal. That gap is exactly why `Arrays` ships two families instead of one.

### Why it exists

Before Java 5's `Arrays.deepEquals`/`deepHashCode`/`deepToString` (added alongside generics-era collection work), comparing nested arrays for structural equality meant hand-writing a recursive walk every time — the same walk, over and over, at every call site that needed it. The JDK folded a name for "recurse into arrays specifically, everything else use its own `equals`" into three static methods rather than leaving every caller to reinvent it, and kept the shallow originals because callers who *want* reference-per-row semantics still exist (interning, deduplication by row identity).

### The mechanism

`Arrays.equals(Object[], Object[])` iterates by index and calls `Objects.equals(a[i], b[i])` per slot, which delegates to `a[i].equals(b[i])`. For a `LedgerEntry[][]`, each slot is itself a `LedgerEntry[]`, and `LedgerEntry[]`'s `equals` is **inherited from `Object`** — arrays never override `equals`, `hashCode`, or `toString`. So `Arrays.equals` on the outer grid ends up asking "are these two row-arrays `==`", which is false for two separately-built rows even when every element inside them matches. `deepEquals` breaks that by checking, per slot, whether both elements are themselves arrays and recursing if so; only at a non-array leaf does it fall through to the leaf's own `equals`. `deepHashCode` and `deepToString` follow the identical shape: check "is this an array", recurse if yes, delegate to the element's own method if no.

No diagram: the manifest assigns this section none; the compiled output below is the picture.

The following is real output from JDK 21.0.7 (`21.0.7+8-LTS-245`), compiled with `javac -Xlint:all` and run with `java`, from a top-level `record LedgerEntry(UUID id, BigDecimal amount) {}`:

```java
record LedgerEntry(UUID id, BigDecimal amount) {}

public class DeepPairs {
    public static void main(String[] args) {
        LedgerEntry[][] window1 = {
            { new LedgerEntry(UUID.fromString("00000000-0000-0000-0000-000000000001"), new BigDecimal("180.00")) },
            { new LedgerEntry(UUID.fromString("00000000-0000-0000-0000-000000000002"), new BigDecimal("260.00")) }
        };
        LedgerEntry[][] window2 = {
            { new LedgerEntry(UUID.fromString("00000000-0000-0000-0000-000000000001"), new BigDecimal("180.00")) },
            { new LedgerEntry(UUID.fromString("00000000-0000-0000-0000-000000000002"), new BigDecimal("260.00")) }
        };

        System.out.println("Arrays.equals:      " + Arrays.equals(window1, window2));
        System.out.println("Arrays.deepEquals:  " + Arrays.deepEquals(window1, window2));
        System.out.println("Arrays.toString:    " + Arrays.toString(window1));
        System.out.println("Arrays.deepToString:" + Arrays.deepToString(window1));

        LedgerEntry[] batch = window1[0];
        System.out.println("batch.toString():   " + batch.toString());
        System.out.println("batch.equals(clone):" + batch.equals(batch.clone()));
    }
}
```

Real output:

```
Arrays.equals:      false
Arrays.deepEquals:  true
Arrays.toString:    [[LLedgerEntry;@681a9515, [LLedgerEntry;@3af49f1c]
Arrays.deepToString:[[LedgerEntry[id=00000000-0000-0000-0000-000000000001, amount=180.00]], [LedgerEntry[id=00000000-0000-0000-0000-000000000002, amount=260.00]]]
batch.toString():   [LLedgerEntry;@681a9515
batch.equals(clone):false
```

`Arrays.equals` on the outer `LedgerEntry[][]` is `false` even though every leaf `LedgerEntry` compares structurally equal, because it never got past comparing the two row references. `deepEquals` is `true` because it recursed one level and then let `LedgerEntry`'s generated record `equals` — which does compare field-by-field — take over. `batch.toString()` prints the raw descriptor form `[LLedgerEntry;@681a9515` — array-of-`LedgerEntry`, `@`, identity hash — because `LedgerEntry[]` never overrode `Object.toString`; it is not a `LedgerEntry`, it is an array, and arrays get `Object`'s default. `batch.equals(batch.clone())` is `false` for the same reason: `clone()` on an object array makes a new array with the same element references (`01a-covariance-and-mutability.md` owns `clone()`'s shallowness in full), but array `equals` is `==`, and a clone is never `==` its source.

**Insight:** arrays do not override `equals`, `hashCode`, or `toString` — every array, primitive or reference, one-dimensional or not, uses `Object`'s identity-based versions unless you route through `Arrays.equals`/`hashCode`/`toString` (or `deepEquals`/`deepHashCode`/`deepToString` for the nested case) explicitly. `Arrays.equals(long[], long[])` fixes the leaf case; `deepEquals` fixes the nested case; neither retrofits the array class itself.

**Interview:** "Why does `Arrays.equals` return `false` for two structurally identical `int[][]` grids?" — because at the outer level `equals` is comparing row *references*, and rows are never `==` across two independently built arrays; use `deepEquals` to recurse.

Full contract for `equals`/`hashCode` on ordinary objects — reflexivity, the hash-code rule, `equals` and `hashCode` staying in sync — lives at `../objects-equality-and-lifecycle/01b-equals-hashcode-and-object-methods.md`; the record-generated form used above (field-by-field, in declaration order) is part of that file's territory, not this one's.

> `Arrays.equals`/`hashCode`/`toString` stop at one level and treat a nested array as an opaque reference; `deepEquals`/`deepHashCode`/`deepToString` recurse into it — because arrays themselves never override `Object`'s identity-based `equals`/`hashCode`/`toString`.

## 2. `Arrays.asList` — a view, and a primitive trap `[TRAP]` (1.22.9)

`Arrays.asList` looks like "give me a `List` from this array" and is actually two separate surprises stacked on one method name: the `List` it hands back is not a copy, and the varargs signature can silently swallow a whole primitive array as a single element.

### Why it exists

Before Java 5's autoboxing and generics matured, bridging an array to the Collections Framework meant a manual copy loop every time. `Arrays.asList` gave a zero-copy adapter — wrap the array, don't duplicate it — for the common case of "I have an array, an API wants a `List`." Zero-copy was the entire point, and it is also the entire trap: callers read "gives me a `List`" and expect list semantics, not array-backed-view semantics.

### The mechanism

`Arrays.asList` — declared with a varargs parameter that erases to `T[] a` — returns `new Arrays.ArrayList<>(a)` — a private static nested class inside `java.util.Arrays`, distinct from `java.util.ArrayList`. `[X-REF 02]` `Arrays$ArrayList` stores the array directly as its backing field and implements `set(i, v)` as a direct write into that array (so writes go through both ways) but does not implement `add`/`remove` at all — it inherits `AbstractList`'s versions, which throw `UnsupportedOperationException` unconditionally. That is a structural fact about the collections library — a *fixed-size* list is a distinct, first-class shape from a *resizable* one, not a special case bolted onto `ArrayList` — and guide `02 Java collections` owns the rest of that hierarchy (`AbstractList`, `RandomAccess`, where `List.of` sits relative to both).

No diagram: the manifest assigns this section none; the compiled output below is the picture.

Real output from JDK 21.0.7:

```java
String[] refs = {"CASH_AVAILABLE", "BONUS_AVAILABLE"};
List<String> view = Arrays.asList(refs);
System.out.println("view before: " + view);
refs[0] = "CASH_RESERVED";
System.out.println("view after array write: " + view);
view.set(1, "BONUS_RESERVED");
System.out.println("array after view.set: " + Arrays.toString(refs));
view.add("SUSPENSE");   // throws
```

```
view before: [CASH_AVAILABLE, BONUS_AVAILABLE]
view after array write: [CASH_RESERVED, BONUS_AVAILABLE]
array after view.set: [CASH_RESERVED, BONUS_RESERVED]
Exception in thread "main" java.lang.UnsupportedOperationException
	at java.base/java.util.AbstractList.add(AbstractList.java:153)
```

`view.getClass().getName()` printed `java.util.Arrays$ArrayList`, confirming it is not the class you think when you read "ArrayList."

**Pitfall:** Trap 2 of 2, the leaf's headline. `Arrays.asList` on a primitive array does not give a `List` of the elements at all. Its varargs parameter — spelled with a varargs ellipsis in the real source, erased form `T[] a` — cannot be instantiated with a primitive type — there is no `T = long`. So when you pass a `long[]`, the compiler cannot spread it as varargs elements; it infers `T = long[]` and wraps the *whole array* as the single element of a one-element list.

```java
long[] amounts = {180L, 260L, 92L};   // three of QuizStakes' card withdrawals
List<long[]> boxedWrong = Arrays.asList(amounts);
System.out.println("size(): " + boxedWrong.size());
System.out.println("get(0).getClass(): " + boxedWrong.get(0).getClass());
```

Real output:

```
size(): 1
get(0).getClass(): class [J
```

One element, and that element's class is `[J` — array-of-`long`. `boxedWrong` is a `List<long[]>` of size 1, exactly as the leaf states, not the `List<Long>` of size 3 that the call site visually suggests.

The fix depends on what you actually wanted:

| Goal | Fix | Trade |
|---|---|---|
| A resizable copy of a reference array | `new ArrayList<>(Arrays.asList(refs))` | Extra O(n) copy, but real independence from the source array |
| A genuinely immutable list | `List.of(refs)` | Rejects `null` elements (verified below); throws on mutation attempts rather than silently no-oping |
| A stream pipeline over a reference array | `Arrays.stream(refs).toList()` | Same immutability as `List.of`, plus stream operations in between |
| A `List<Long>` from a primitive `long[]` | `Arrays.stream(amounts).boxed().toList()` | Every element boxes — see the cost note below |

Verified `null` handling: `List.of("a", null)` threw `NullPointerException` on JDK 21.0.7; `Arrays.asList("a", null)` returned `[a, null]` without complaint. `Arrays.asList` permits `null` elements because it is just wrapping whatever the array already contains; `List.of` explicitly rejects them as part of being a "no surprises" immutable list.

The boxing route (`Arrays.stream(amounts).boxed().toList()`) has a real cost: every `long` primitive becomes a heap-allocated `Long` (outside `Long.valueOf`'s cache range, since QuizStakes' card withdrawal amounts run well above 180 on average — the JDK's `Long` cache only covers −128..127, unlike `Integer`'s `AutoBoxCacheMax = 128` cache which is also −128..127). Boxing 95k card deposits' worth of amounts a day is 95k individual `Long` allocations that a primitive `long[]` never pays. The wrapper-cache mechanics and the arithmetic for what that costs at scale belong to `../wrappers-and-boxing/01-basics.md` (a later batch) — this file names the cost, that file derives it.

`[X-REF 02]` `Arrays.asList`'s place in the collections library, in full: it returns a private `Arrays$ArrayList`, a fixed-size `RandomAccess` list that is neither `java.util.ArrayList` nor immutable, sitting alongside `List.of`'s genuinely-immutable list and `java.util.ArrayList`'s genuinely-resizable one as a third, distinct shape. Guide `02 Java collections` owns the full `List` implementation hierarchy and where each of these three sits in it.

The reason this reads as surprising rather than obvious: the method is named `asList`, singular and unqualified, and every other "as-a-list-of-my-elements" API in day-to-day use — `List.of(1, 2, 3)`, a stream's `.toList()` — really does give one element per argument. Nothing in the call site `Arrays.asList(amounts)` visually signals that varargs type inference just picked `T[]` over spreading, because the array and the varargs parameter share the same square-bracket syntax.

> `Arrays.asList` returns a fixed-size, array-backed view (mutation of one side is visible through the other; `add`/`remove` throw, `set` succeeds), and on a primitive array it silently wraps the entire array as one element instead of spreading it, because `asList`'s varargs type parameter `T` (erased to `T[] a`) cannot be instantiated with a primitive.

## 3. `System.arraycopy` — the intrinsic behind everything (1.22.10)

Nearly every array-copying method in the JDK — `Arrays.copyOf`, `copyOfRange`, `ArrayList`'s internal grow-and-shift, `String`'s internal char-array operations — bottoms out in exactly one native method. `Arrays.copyOf` is not fast because `Arrays` is clever; it is fast because it delegates to the one method the JVM special-cases at the bytecode level.

### Why it exists

A hand-written `for` loop copying element by element works, but it is a loop: bounds-checked per iteration (until BCE removes the checks — `01c-memory-layout-and-bounds.md` owns that), one store instruction per element, no vectorization guarantee. Every array-shuffling operation in the platform needed the same bulk-move primitive, so the JDK exposed it once, natively, and let the JIT recognize the call shape and replace it with a real bulk-memory-move instruction rather than a Java-level loop.

### The mechanism

The signature, verified against JDK 21.0.7 with `javap -p java.lang.System`:

```
public static native void arraycopy(java.lang.Object, int, java.lang.Object, int, int)
```

Read as `arraycopy(Object src, int srcPos, Object dest, int destPos, int length)` — **the leaf's actual point.** Source pair first (`src`, `srcPos`), then destination pair (`dest`, `destPos`), then length last. This is deliberately *not* the parameter order any `Arrays` method uses (`copyOfRange(original, from, to)` puts both bounds on one array; `arraycopy` puts one position each on two different arrays), which is exactly why it gets swapped under pressure — remember it as "read the two pairs left to right, source then destination, count last."

`[SOURCE]` `Arrays.copyOf` delegates straight through it. Quoted from `java.base/java/util/Arrays.java` in this machine's JDK 21.0.7 `src.zip`:

```java
public static <T,U> T[] copyOf(U[] original, int newLength, Class<? extends T[]> newType) {
    @SuppressWarnings("unchecked")
    T[] copy = ((Object)newType == (Object)Object[].class)
        ? (T[]) new Object[newLength]
        : (T[]) Array.newInstance(newType.getComponentType(), newLength);
    System.arraycopy(original, 0, copy, 0,
                     Math.min(original.length, newLength));
    return copy;
}
```

Line by line: `newType == Object[].class` is checked because allocating via reflection is not free, so the common case (copying to a plain `Object[]`) takes the direct `new Object[newLength]` path; every other target type — including `copyOf(T[], int)`'s own delegation to this method with `original.getClass()` as `newType` — goes through `Array.newInstance`, which is the only way to allocate an array of a runtime type not known at compile time (`../generics/02b-generic-arrays-and-self-types.md` owns `Array.newInstance` as a generic-arrays idiom in full). Then the actual copy is one `System.arraycopy` call, length clamped to `Math.min(original.length, newLength)` so a *shrinking* copy does not try to read past the source's end. `newLength` beyond `original.length` leaves the tail at the copy's zero-value default (`null` for references) because `Array.newInstance` and `new Object[n]` both zero-fill on allocation, and `arraycopy` only ever touches the first `Math.min(original.length, newLength)` slots.

No diagram: the manifest assigns this section none; the source excerpt and the exception traces below are the picture.

The runtime checks, each triggered and quoted, real output from JDK 21.0.7:

```java
// NullPointerException — null array
System.arraycopy(null, 0, new long[3], 0, 1);
// java.lang.NullPointerException

// ArrayStoreException — incompatible component types
Object[] src = new String[]{"a", "b"};
Object[] dst = new Long[2];
System.arraycopy(src, 0, dst, 0, 2);
// java.lang.ArrayStoreException: arraycopy: type mismatch: can not copy java.lang.String[] into java.lang.Long[]

// IndexOutOfBoundsException — bad range
System.arraycopy(new long[3], 0, new long[3], 0, 5);
// java.lang.ArrayIndexOutOfBoundsException: arraycopy: last source index 5 out of bounds for long[3]

// ArrayStoreException — reference-to-primitive mismatch
Object srcP = new long[]{1L, 2L};
Object dstP = new int[2];
System.arraycopy(srcP, 0, dstP, 0, 2);
// java.lang.ArrayStoreException: arraycopy: type mismatch: can not copy long[] into int[]
```

The first `ArrayStoreException` is the same species of failure `01a-covariance-and-mutability.md` covers for element-by-element covariant writes — a `Long[]` cannot receive `String` elements — but here it fires as a bulk pre-check on the whole call rather than one element at a time. The fourth case is a distinct flavor the leaf calls out explicitly: `long[]` and `int[]` are both arrays, neither is `null`, the range is in bounds, and it still throws, because a primitive array's component type must match the destination's exactly — there is no primitive widening across an `arraycopy` boundary the way there is in an assignment expression.

`System.arraycopy` handles **overlapping ranges within the same array correctly** — the Javadoc states the copy behaves as if the source region were first copied to a temporary array, so shifting elements toward the front or back of the same array never corrupts the read side with data the write side just clobbered. Demonstrated by a self-overlapping shift removing withdrawal batch index 1 in place:

```java
long[] amounts = {180L, 260L, 92L, 400L};
System.out.println("before: " + Arrays.toString(amounts));
System.arraycopy(amounts, 2, amounts, 1, 2);   // shift [92,400] left over index 1
System.out.println("after:  " + Arrays.toString(amounts));
```

```
before: [180, 260, 92, 400]
after:  [180, 92, 400, 400]
```

The last slot is a stale duplicate on purpose — this call only moved two elements into a four-slot array, so index 3 keeps its old value until a caller truncates or overwrites it — but indices 1 and 2 came out correctly as `92, 400` with no corruption from the source and destination sharing memory. This overlap guarantee is exactly what makes `arraycopy` usable for in-place `List.remove` and array-based queue compaction; most callers rely on it without ever having checked that it is a guarantee rather than an accident.

The cost, honestly: `arraycopy` is `native` and marked as a JIT intrinsic (`@IntrinsicCandidate` appears on several `Arrays` copy methods in the source above and on `System.arraycopy` itself), so on a warmed-up path the JIT replaces the call with a bulk memory-move instruction rather than compiling a Java-level element loop — that is the mechanism, and it is why a hand-written per-element copy loop is generally slower than `arraycopy` for anything but a tiny array. **Unverified:** the exact throughput delta between a hand-written copy loop and `System.arraycopy` on this machine — no benchmark was run for this file, and printing a number without measuring it would violate the unverified-claims bar. Guide `06 JVM internals` owns intrinsics and JIT compilation in general; `../cost-model/02-master-cost-table.md` (a later batch) owns the master per-operation cost table this claim would eventually feed.

**Interview:** "What does `Arrays.copyOf` actually do under the hood?" — allocate a new array of the target size (via `Array.newInstance` when the runtime type isn't a plain `Object[]`), then one `System.arraycopy` call for the overlap length, with the tail left zero/null-filled if growing.

> `System.arraycopy(Object src, int srcPos, Object dest, int destPos, int length)` is the single native, JIT-intrinsified copy primitive every array-copying method in the JDK bottoms out in; it checks null, component-type compatibility, and range before copying, and its overlap-safe guarantee within a single array is what makes in-place shifts correct.

## Supporting facts

### `fill` versus `setAll` — shared reference versus distinct references

`Arrays.fill(T[] a, T val)` writes the *same* reference into every slot; `Arrays.setAll(T[] a, IntFunction<? extends T> generator)` calls the generator once per index and can therefore produce a distinct object per slot. Verified on JDK 21.0.7: `Arrays.fill(shared, new Object())` left `shared[0] == shared[1]` (`true`); `Arrays.setAll(distinct, i -> new StringBuilder("W" + i))` left `distinct[0] == distinct[1]` (`false`). Filling an array of mutable objects (a `StringBuilder[]` meant to hold four independent per-window buffers) with `fill` is a real bug source — every "independent" slot is the same object, and mutating one mutates all four.

> `fill` shares one reference across every slot it writes; `setAll` invokes its generator per index, so only `setAll` is safe when the element type is mutable and the slots must stay independent.

### `sort` versus `parallelSort` — algorithm and threshold

Primitive-array `sort` is a **dual-pivot quicksort** (stated in the `Arrays.sort` Javadoc `@implNote`, confirmed against `java.base/java/util/Arrays.java`); reference-array `sort` is **TimSort**, an adaptive stable merge sort adapted from Python's list sort (confirmed in the same source, `Arrays.java` around the `sort(T[], Comparator)` overload). The observable consequence: sorting `LedgerEntry[]` by settlement date is stable — entries with equal dates keep their relative order, which is what a caller relies on for a stable multi-key sort ("sort by date, then by amount" only works if the date-sort didn't scramble ties) — while sorting an `int[]` of raw amounts gives no such guarantee, because quicksort has no stability concept for primitive values that carry no identity beyond their numeric value. `parallelSort` on JDK 21.0.7 delegates to `DualPivotQuicksort.sort(a, ForkJoinPool.getCommonPoolParallelism(), fromIndex, toIndex)` for primitives, which internally falls back to sequential sorting below `MIN_ARRAY_SORT_GRAN = 1 << 13` (8192, confirmed by reading the constant in `Arrays.java`) — an array of QuizStakes' ~2.8M daily stake amounts is well above that threshold and would actually parallelize; a four-element `PaymentRun` window array never would. Guide `01 DSA fundamentals` owns quicksort/mergesort mechanics; guide `02 Java collections` owns `Comparator` composition; `Comparable`/`Comparator` themselves are `../objects-equality-and-lifecycle/02a-composite-equality-and-ordering.md`.

> Primitive `sort` is an unstable dual-pivot quicksort; reference `sort` is a stable TimSort; `parallelSort` only actually parallelizes above `MIN_ARRAY_SORT_GRAN` (8192 elements), sorting sequentially below it.

### `binarySearch` — the miss arithmetic

Requires the array already be sorted; behavior on an unsorted array is unspecified, not merely slow. A hit returns the index. A miss returns `-(insertion point) - 1` — negative, so a caller can distinguish hit from miss with one `>= 0` check, and recover the insertion point by negating and subtracting one. Verified: searching `{42, 65, 92, 180, 260}` for `100` (which would sort between `92` and `180`, index 3) returned `-4`, and `-(-4) - 1 = 3`, the correct insertion point.

> A `binarySearch` miss encodes the insertion point as `-(insertion point) - 1`, which is what makes the same call double as "is it there" and "where would it go."

### `mismatch` and `compare` — Java 9

Both are Java 9+ additions; do not use them if the code must run on 8. `mismatch(a, b)` returns the index of the first pair of differing elements, or `-1` if every compared position matches (arrays of different lengths where one is a prefix of the other still return the length of the shorter one, not `-1`, unless fully equal). `compare(a, b)` returns lexicographic ordering — negative, zero, or positive — treating a shorter-but-otherwise-equal-prefix array as smaller. Verified: for `a = {180, 260, 92}` and `b = {180, 260, 400}`, `mismatch` returned `2` (the first differing index) and `compare` returned `-1` (`a` sorts before `b`, since `92 < 400` at the first difference).

> `mismatch` locates *where* two arrays first differ; `compare` says *which one* is lexicographically smaller — both Java 9+, both O(n) worst case.

### `Arrays.stream` — two families

`Arrays.stream(T[] array)` returns `Stream<T>` for a reference array; `Arrays.stream(int[])`, `(long[])`, `(double[])` return the matching primitive stream type (`IntStream`, `LongStream`, `DoubleStream` — there is no primitive stream for `byte`, `short`, `char`, `float`, which get widened to `int`/`double` if streamed at all through this route). Every overload has a range-limited form, `stream(array, from, to)`. Guide `04 Modern Java` owns streams in full.

> `Arrays.stream` splits into `Stream<T>` for references and `IntStream`/`LongStream`/`DoubleStream` for `int`/`long`/`double`; there is no primitive stream type for the others.

### `copyOfRange` — half-open, and it zero-fills past the end

The range is half-open, `[from, to)`, matching `String.substring`'s convention. `to` is permitted to exceed `array.length`; the returned array is padded with the component type's default value (`null` for references, `0`/`0L`/`false` for primitives) rather than throwing. Verified: `Arrays.copyOfRange(new int[]{1,2,3}, 1, 6)` returned `[2, 3, 0, 0, 0]` — three requested-but-absent slots silently became `0`, not an exception. `01-basics.md` owns zero-fill on ordinary array creation; this is the same default-value rule applying to the padded tail of a range copy.

> `copyOfRange(a, from, to)` is half-open and permits `to > a.length`, zero/null-filling the tail instead of throwing.

## Pitfalls

### `Arrays.equals` on a nested array checks structural equality

**Wrong**

```java
LedgerEntry[][] window1 = { { entry("00000000-0000-0000-0000-000000000001", "180.00") } };
LedgerEntry[][] window2 = { { entry("00000000-0000-0000-0000-000000000001", "180.00") } };
System.out.println(Arrays.equals(window1, window2));
```
```
false
```

**Right**

```java
System.out.println(Arrays.deepEquals(window1, window2));
```
```
true
```

**Why people believe it:** `Arrays.equals` is documented as "returns true if the two arrays are equal", and nothing in that sentence signals that "equal" stops at comparing row references for a two-dimensional array — the method name gives no hint that a `deep` sibling exists until you go looking for it.

### `Arrays.asList` gives you a resizable copy of the array

**Wrong**

```java
List<String> view = Arrays.asList(new String[]{"CASH_AVAILABLE", "BONUS_AVAILABLE"});
view.add("SUSPENSE");
```
```
Exception in thread "main" java.lang.UnsupportedOperationException
	at java.base/java.util.AbstractList.add(AbstractList.java:153)
```

**Right**

```java
List<String> mutable = new ArrayList<>(Arrays.asList(new String[]{"CASH_AVAILABLE", "BONUS_AVAILABLE"}));
mutable.add("SUSPENSE");   // succeeds — independent, resizable copy
```

**Why people believe it:** the method returns something that satisfies the `List` interface and prints exactly like an `ArrayList` would, and most call sites only ever read from the result, so the fixed-size restriction never surfaces until someone later tries to `add` to a list they assumed was a normal collection.

### `Arrays.asList(primitiveArray)` gives a `List` of the elements

**Wrong**

```java
long[] amounts = {180L, 260L, 92L};
List<Long> boxed = (List<Long>) (List<?>) Arrays.asList(amounts);   // compiles by accident with a raw cast; the real inferred type is List<long[]>
System.out.println(boxed.size());
```
```
1
```

**Right**

```java
long[] amounts = {180L, 260L, 92L};
List<Long> boxed = Arrays.stream(amounts).boxed().toList();
System.out.println(boxed.size());
```
```
3
```

**Why people believe it:** `Arrays.asList(referenceArray)` behaves exactly as expected for every reference type, so the mental model "wrap an array as a list" generalizes fine right up until the array happens to hold a primitive component type, at which point varargs type inference silently substitutes "wrap the array as one element" instead — with no compiler warning, because `T = long[]` is a perfectly legal instantiation of `Arrays.asList`'s type parameter.

## Cheat sheet

| Need | Call | Watch out for |
|---|---|---|
| Copy, possibly resized | `Arrays.copyOf(a, n)` | Truncates or null/zero-pads; shallow |
| Copy a sub-range | `Arrays.copyOfRange(a, from, to)` | Half-open; `to` may exceed length, zero-fills tail |
| Fill every slot, same object | `Arrays.fill(a, v)` | All slots share one reference for object arrays |
| Fill every slot, distinct objects | `Arrays.setAll(a, generatorFn)` | Generator runs per index |
| Sort in place | `Arrays.sort(a)` | Dual-pivot quicksort (primitives, unstable) / TimSort (references, stable) |
| Parallel sort | `Arrays.parallelSort(a)` | Sequential below `MIN_ARRAY_SORT_GRAN` (8192) |
| Find in sorted array | `Arrays.binarySearch(a, key)` | Requires sorted; miss = `-(insertion point) - 1` |
| Shallow structural equality | `Arrays.equals(a, b)` | One level only; nested arrays compare by reference |
| Deep structural equality | `Arrays.deepEquals(a, b)` | Recurses; needed for `T[][]`+ |
| First difference (Java 9+) | `Arrays.mismatch(a, b)` | `-1` means fully equal |
| Lexicographic order (Java 9+) | `Arrays.compare(a, b)` | Shorter equal-prefix array is "less" |
| Array → `List` view | `Arrays.asList(a)` | Fixed-size; `add`/`remove` throw; primitive array → one-element `List<T[]>` |
| Array → real mutable `List` | `new ArrayList<>(Arrays.asList(a))` | Extra copy, but independent |
| Array → real immutable `List` | `List.of(a)` | Rejects `null` elements |
| Array → stream | `Arrays.stream(a)` | `Stream<T>` vs `IntStream`/`LongStream`/`DoubleStream` |
| Bulk copy primitive | `System.arraycopy(src, sp, dst, dp, len)` | Source pair, dest pair, length — that order, always |

## Self-test

**Q1.** Why does `Arrays.equals` return `false` when comparing two `long[][]` grids that are structurally identical, and what fixes it?

<details><summary>Answer</summary>

Because `Arrays.equals(Object[], Object[])` compares element by element, and at the outer level of a two-dimensional array each "element" is itself a `long[]` row. Arrays never override `equals`, so comparing two rows falls through to `Object.equals`, which is reference identity — two independently built rows are never `==` even with identical contents. `Arrays.deepEquals` fixes it by recursing: at each slot it checks whether both elements are arrays and, if so, recurses into them instead of calling `equals` directly, only bottoming out at non-array leaves.

</details>

**Q2.** What does `Arrays.asList` actually return, and name the two operations that behave differently from a normal `ArrayList`.

<details><summary>Answer</summary>

It returns an instance of the private nested class `Arrays$ArrayList`, which wraps the given array directly rather than copying it — it's a fixed-size, array-backed view, not `java.util.ArrayList`. `set(index, value)` writes through to the backing array and succeeds normally. `add` and `remove` are not implemented by that class at all; they inherit `AbstractList`'s default, which unconditionally throws `UnsupportedOperationException`, because the list cannot resize without breaking the one-array backing.

</details>

**Q3.** You write `Arrays.asList(amounts)` where `amounts` is a `long[]` of withdrawal totals, expecting a `List<Long>`. What do you actually get, and why?

<details><summary>Answer</summary>

A `List<long[]>` containing exactly one element, and that element is the whole `amounts` array. `Arrays.asList` is declared as a varargs method (spelled with a varargs ellipsis in the real source) whose parameter erases to `T[]`. Because `T` cannot be instantiated with a primitive type — there is no `T = long` — the compiler cannot spread the primitive array's elements as the varargs arguments; instead it infers `T = long[]` and treats the single array reference as the sole varargs argument. The fix is `Arrays.stream(amounts).boxed().toList()`, which boxes each `long` explicitly into a real `List<Long>` of the expected size.

</details>

**Q4.** State the parameter order of `System.arraycopy` from memory, and explain why it's easy to get wrong.

<details><summary>Answer</summary>

`arraycopy(Object src, int srcPos, Object dest, int destPos, int length)` — the source array and its starting position, then the destination array and its starting position, then the number of elements to copy. It's easy to get wrong because it's the only widely-used array method with this shape; every `Arrays` method that takes a range puts both bounds on a single array (like `copyOfRange(original, from, to)`), so the instinct under pressure is to reach for a "from, to" pattern instead of "two separate position arguments on two separate arrays, count last."

</details>

**Q5.** Does `System.arraycopy` handle the case where the source and destination are the same array and the ranges overlap? What guarantees that?

<details><summary>Answer</summary>

Yes — the Javadoc guarantees that overlapping copies within the same array behave as though the source region were first copied to a temporary array before the write happens, so a copy can never read data that its own write has already clobbered. That's what makes it safe to use for in-place shifts, such as removing an element from the middle of an array by copying everything after it one slot to the left over the removed slot; without that guarantee, a naive forward-iterating copy loop would overwrite source elements before it had read them.

</details>

**Q6.** Why is sorting a `LedgerEntry[]` by settlement date stable, but sorting an `int[]` of raw amounts is not — and why would that matter?

<details><summary>Answer</summary>

Reference-array `Arrays.sort` uses TimSort, an adaptive merge sort that is explicitly stable — elements that compare equal keep their original relative order. Primitive-array `Arrays.sort` uses a dual-pivot quicksort, which has no stability concept, partly because primitive values carry no identity beyond their numeric value, so "original order" for two equal ints isn't even a meaningful thing to preserve. It matters for a multi-key sort: if you sort `LedgerEntry[]` by date and then need entries with the same date to stay in whatever order a prior sort (say, by amount) put them in, that only works if the date sort is stable. Doing the same trick with primitive amounts wouldn't preserve any such secondary order.

</details>

**Q7.** What does `Arrays.copyOfRange(array, from, to)` do if `to` is larger than `array.length`?

<details><summary>Answer</summary>

It doesn't throw. The method allocates a new array of length `to - from` and fills the slots beyond the original array's end with the component type's default value — `null` for a reference array, `0`/`0L`/`0.0`/`false` for the matching primitive type. Verified directly: `Arrays.copyOfRange(new int[]{1,2,3}, 1, 6)` returns `[2, 3, 0, 0, 0]` rather than an `ArrayIndexOutOfBoundsException`.

</details>

**Q8.** A junior engineer fills a `StringBuilder[]` of four per-window buffers with `Arrays.fill(buffers, new StringBuilder())` and then appends different text to each slot in a loop. What goes wrong?

<details><summary>Answer</summary>

`Arrays.fill` writes the exact same object reference into every slot — it evaluates `new StringBuilder()` once and stores that one reference four times, it does not construct four separate builders. So appending to `buffers[0]` and then appending to `buffers[1]` both mutate the same underlying `StringBuilder`, and every slot ends up holding the same accumulated text. The fix is `Arrays.setAll(buffers, i -> new StringBuilder())`, which invokes the generator once per index and so produces four genuinely distinct objects.

</details>

---

**Leaves covered:** 1.22.8, 1.22.9, 1.22.10 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 461
