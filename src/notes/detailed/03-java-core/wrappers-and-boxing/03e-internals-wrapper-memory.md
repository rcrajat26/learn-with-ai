# 03 Java Core — Wrapper memory arithmetic — INTERNALS (§3.4, 3.4.10–3.4.12)

**Target version: Java 21 LTS.** | **Part 3 of 5** | [Index](../00-index.md)
Previous: [Escape analysis and the box that never allocates](03d-internals-escape-analysis.md) · Next: [Monitors on a box, and Valhalla](03f-internals-monitors-and-valhalla.md)

[`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md) already established the two headline figures and confirmed both by measurement: an `Integer` is **16 bytes**, a `Long` is **24 bytes**, a boxed element in a collection costs **20 bytes** against 4 for an `int`, and a million-element `List<Integer>` costs five times its `int[]` equivalent. That file owns the derivation and embeds D-028. This file does not repeat it.

What it does instead is go one layer down and one layer out. Down: the 12-byte header is not an opaque constant, it is two words with names and contents, laid out by rules that decide where the padding goes, and governed by two flags that most people believe are one flag. Out: nobody stores a bare `Integer`. They store an `Optional<Integer>`, a `HashMap.Node` with a boxed key, a record with boxed components — and the composite arithmetic is where sizing estimates actually go wrong, usually by a factor of three.

Every figure below was measured on **Oracle JDK 21.0.7 (21.0.7+8-LTS-245, macOS aarch64)** with `com.sun.management.ThreadMXBean.getThreadAllocatedBytes`, under `UseCompressedOops = true {ergonomic}` and `ObjectAlignmentInBytes = 8 {default}` unless a flag is named. That instrument measures **allocation, not retention**, which is the honest limit on the whole file; the last section of concept 2 says exactly what that buys and what it does not.

---

## 1. The object header is two words, and the payload is smaller than the bookkeeping (3.4.10, 3.4.11)

`[NUM]` `[PROVE]` An `Integer` is a mark word, a class pointer, and four bytes of actual data. Three quarters of it belongs to the JVM, not to you. `Long` is worse in a different way: its payload is twice as big, yet it is 24 bytes rather than 20 — the extra four bytes are not data, they are alignment padding forced in *front* of the `long` field so that the field lands on an 8-byte boundary. The whole of leaf 3.4.11 is that one padding step.

### Why it exists

Every object on the Java heap must answer two questions that a bare `int` never has to answer. **Who am I** — the identity hash once computed, the lock state if anything ever synchronized on it, the GC age and mark bits. That is the **mark word**, 8 bytes on a 64-bit VM. And **what am I** — a pointer to the `Klass` metadata, which is what `invokevirtual` dispatches through, what a `checkcast` tests against, and what the GC reads to know which of the object's words are references it must trace. That is the **class pointer**, 4 bytes when `UseCompressedClassPointers` is on, 8 when it is not.

There is no way to have a reference to a bare `int`. A reference points at an object; an object has a header. So the moment a generic API forces you to hand it an `Object`, you are paying for identity and type on a value that has neither. That is the entire economic argument for Valhalla, which [`03f-internals-monitors-and-valhalla.md`](03f-internals-monitors-and-valhalla.md) takes up.

**When the layout matters, and when it does not.** Below a few thousand boxes it is noise, and reaching for a primitive-specialised collection to save 16 bytes each is the wrong trade against readability — [`01h-when-boxing-is-unavoidable.md`](01h-when-boxing-is-unavoidable.md) draws that line. It starts mattering when the count reaches six figures, and it dominates every other consideration at seven.

### The mechanism

The two header words, and what each holds:

| Word | Size (compressed, default) | Size (uncompressed) | Contents |
|---|---|---|---|
| Mark word | 8 bytes | 8 bytes | identity hash (once computed), lock/monitor state, GC age and mark bits, forwarding pointer during copying collection |
| Class pointer | 4 bytes | 8 bytes | narrow `Klass` pointer — virtual dispatch, `checkcast`, GC oop maps |
| **Header total** | **12 bytes** | **16 bytes** | |

The mark word is where the identity hash lives, which is why calling `System.identityHashCode` on an object has a side effect on its header — [`../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md`](../objects-equality-and-lifecycle/04-internals-hashcode-and-identity.md) owns that chapter. The general layout rules — field reordering by descending width, `@Contended`, superclass fields first — are [`../objects-equality-and-lifecycle/05-internals-object-layout.md`](../objects-equality-and-lifecycle/05-internals-object-layout.md)'s. Neither is repeated here; this file only needs the two sizes and the alignment rule.

`[NUM]` **The derivation.** Assumptions, both measured from `-XX:+PrintFlagsFinal` on JDK 21.0.7: `UseCompressedOops = true {ergonomic}`, `ObjectAlignmentInBytes = 8 {default}`.

```
Integer:  8 (mark) + 4 (narrow Klass) = 12 header
          + 4 (int value)             = 16
          16 % 8 == 0                 -> no trailing padding.  16 bytes.

Long:     8 (mark) + 4 (narrow Klass) = 12 header
          long must start at an 8-byte boundary; 12 is not one,
          so 4 bytes of padding are inserted BEFORE the field:
          12 + 4 (padding) + 8 (long) = 24
          24 % 8 == 0                 -> no further padding.   24 bytes.
```

That padding step is the only non-obvious arithmetic in the family, and it is why `Long` is 24 and not 20. Naive `12 + 8 = 20` is the single most common wrong answer to "how big is a `Long`".

`[PROVE]` **The measured confirmation, and it is independent of the derivation.** Two separate instruments agree.

From [`03d-internals-escape-analysis.md`](03d-internals-escape-analysis.md)'s measurement, run with `-XX:-DoEscapeAnalysis` so the boxes are actually allocated: a method creating **two** `Integer` boxes per iteration over 5,000,000 iterations allocated **160,000,000 bytes**, which is **32.0 bytes per iteration** = 2 × 16. And the boxed-accumulator loop in [`03c-internals-boxing-bytecode.md`](03c-internals-boxing-bytecode.md), one `Long.valueOf` per `+=` over a 1,000,000-element `int[]`, allocated **24,000,000 bytes** = **24.0 per iteration** = one `Long`.

Second instrument, measured for this file: fill an `Object[]` of 1,000,000 with fresh boxes and subtract the array's own cost. The array of bare references measures **4,000,016 bytes** (16-byte array header + 1M × 4-byte compressed references), so anything above 4.0 per element is the box:

| Wrapper | Payload | Padding | Derived size | Measured per element in an `Object[]` | Implied box size |
|---|---|---|---|---|---|
| `Byte` | 1 byte | 3 trailing | 16 | 20.00002 (via `new Byte`) | **16** |
| `Boolean` | 1 byte | 3 trailing | 16 | 20.00002 (via `new Boolean`) | **16** |
| `Short` | 2 bytes | 2 trailing | 16 | 20.00002 | **16** |
| `Character` | 2 bytes | 2 trailing | 16 | 20.00002 | **16** |
| `Integer` | 4 bytes | none | 16 | 20.00002 | **16** |
| `Float` | 4 bytes | none | 16 | 20.00002 | **16** |
| `Long` | 8 bytes | 4 leading | 24 | 28.00002 | **24** |
| `Double` | 8 bytes | 4 leading | 24 | 28.00002 | **24** |

All eight are measured, not merely derived. Two of them needed care to measure at all, and the reason is instructive: `Byte.valueOf` has **no bounds check** — a `byte` cannot be outside −128..127, so every call is a cache hit — and `Boolean.valueOf` returns one of two eagerly-constructed statics. Measured, `Byte.valueOf((byte) i)` over a million iterations allocated **4,000,016 bytes**, exactly the array and nothing else: zero boxes. The only way to make either wrapper allocate is the terminally-deprecated constructor:

```java
@SuppressWarnings({"deprecation", "removal"})
static Object[] forceByteBoxes(int count) {
    Object[] slots = new Object[count];
    for (int i = 0; i < count; i++) {
        slots[i] = new Byte((byte) i);      // @Deprecated(since="9", forRemoval=true)
    }
    return slots;
}
```

Measured over 1,000,000: **20,000,016 bytes**, 20.00002 per element, so `new Byte` costs 16 bytes. Same shape for `new Boolean`: **20,000,016**. So `Byte` and `Boolean` are 16 bytes as a *measured* fact, at the cost of using a constructor no production code should contain.

**Insight:** `Byte` and `Boolean` are the two wrappers whose `valueOf` can never allocate, which makes them the only two whose object size is invisible to an allocation profiler in ordinary code. That is not a limitation of the tool — it is the correct answer to the question a profiler is asking. If you want the *layout*, you need a layout tool, not an allocation counter.

Which raises the obvious next question, and it is worth recording the refusal rather than asserting a workaround. JOL is not on this classpath. The HotSpot flag that prints field offsets directly was attempted and refused:

```
$ java -XX:+UnlockDiagnosticVMOptions -XX:+PrintFieldLayout -version
Error: VM option 'PrintFieldLayout' is notproduct and is available only in debug version of VM.
```

(The missing space in `notproduct` is HotSpot's own message text, quoted verbatim.) So `PrintFieldLayout` is a debug-VM-only flag and is unavailable on a product build; the arithmetic above stands on allocation measurement plus the alignment rule, not on a printed layout. Guide **06 JVM internals** covers JOL, which is the tool that would print the offsets directly.

`[RESEARCH]` **The compressed-oops caveat, and it is two flags, not one.** This is the arithmetic that most often gets restated wrongly, including in an earlier draft of these notes. On JDK 21.0.7, `UseCompressedOops` and `UseCompressedClassPointers` are **independent** `product lp64_product` flags. Measured: running with `-XX:-UseCompressedOops` alone, `-XX:+PrintFlagsFinal` still reports `UseCompressedClassPointers = true {default}`. The class pointer stays narrow, so the header stays at 12 bytes, so the boxes do not change size at all. What doubles is every *reference*:

| Flags | `Object[]` of 1M, bare | Per element with `Integer` boxes | Per element with `Long` boxes | Header | `Integer` | `Long` |
|---|---|---|---|---|---|---|
| default (both on) | 4,000,016 | **20.0** | **28.0** | 12 | **16** | **24** |
| `-XX:-UseCompressedOops` | 8,000,016 | **24.0** | **32.0** | 12 | **16** | **24** |
| both off | 8,000,024 | **32.0** | **32.0** | 16 | **24** | **24** |

Read the middle row carefully. Turning compressed oops off does **not** make `Integer` 24 bytes. It makes the reference 8 bytes instead of 4, so a boxed element goes from 20 to 24 — not to 28, and not because the object grew. Only the bottom row moves the header to 16, and there `Integer` becomes 16 + 4 = 20, padded to **24**, while `Long` becomes 16 + 8 = **24** with *no padding at all*. With both flags off, `Integer` and `Long` are the same size, and the array header itself grows from 16 to 24 bytes (visible as 4,000,016 versus 8,000,024 for the bare array).

The threshold that turns compressed oops off for you, measured: `-Xmx31g` reports `UseCompressedOops = true {ergonomic}`, `-Xmx32g` reports `UseCompressedOops = false {default}`. A 32-bit offset scaled by the 8-byte object alignment addresses 2^35 bytes = 32 GiB, so above that heap size the encoding cannot reach every object and the VM stops using it. **Interview:** the practical consequence is that raising a heap from 31 GiB to 33 GiB can *reduce* the number of objects that fit, because every reference in the process doubles — a genuinely counter-intuitive result that comes up whenever someone proposes a large single-JVM cache.

**The reference cost, which leaf 3.4.10 names explicitly and people forget.** The box does not *replace* the four bytes of `int`. It **adds** to them. In a collection, the element is a 4-byte compressed reference in the backing array *plus* a 16-byte `Integer` on the heap = **20 bytes**, against **4** for the same value in an `int[]`. Five times, not four. The same arithmetic for `Long`: 4 + 24 = 28 against 8, which is 3.5×.

### Diagram

No diagram of its own. The picture for the bulk `int[]` versus `List<Integer>` comparison is D-028, embedded at the point of explanation in [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md); this file's contribution is the composite arithmetic below it, which is a table rather than a figure.

### A concrete example

The shapes QuizStakes actually holds. Nobody stores a bare `Integer` — they store it inside something, and the container has a header too.

```java
import com.sun.management.ThreadMXBean;
import java.lang.management.ManagementFactory;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;

/** Costs the composite shapes QuizStakes actually holds, not the bare box. */
public final class CompositeFootprint {

    private static final ThreadMXBean BEAN =
            (ThreadMXBean) ManagementFactory.getThreadMXBean();
    private static final int N = 1_000_000;

    /** Held so the JIT cannot scalar-replace the shapes we are costing. */
    private static Object retained;

    record PositionBoxed(Long positionId, Integer stakeMinorUnits) {}
    record PositionPrimitive(long positionId, int stakeMinorUnits) {}

    private static void cost(String label, Supplier<Object> shape) {
        for (int warmup = 0; warmup < 2; warmup++) {
            retained = shape.get();
        }
        long before = BEAN.getThreadAllocatedBytes(Thread.currentThread().threadId());
        retained = shape.get();
        long after = BEAN.getThreadAllocatedBytes(Thread.currentThread().threadId());
        long total = after - before;
        System.out.printf("%-46s %,14d bytes  %8.4f per element%n",
                label, total, (double) total / N);
    }

    public static void main(String[] args) {
        cost("Object[] of references only", () -> new Object[N]);

        cost("Optional<Integer>, uncached value", () -> {
            Object[] slots = new Object[N];
            for (int i = 0; i < N; i++) {
                slots[i] = Optional.of(Integer.valueOf(420 + i));
            }
            return slots;
        });

        cost("Optional<Integer>, cached value 100", () -> {
            Object[] slots = new Object[N];
            for (int i = 0; i < N; i++) {
                slots[i] = Optional.of(Integer.valueOf(100));
            }
            return slots;
        });

        cost("record PositionBoxed(Long, Integer)", () -> {
            Object[] slots = new Object[N];
            for (int i = 0; i < N; i++) {
                slots[i] = new PositionBoxed(9_000_000_000L + i, 420 + i);
            }
            return slots;
        });

        cost("record PositionPrimitive(long, int)", () -> {
            Object[] slots = new Object[N];
            for (int i = 0; i < N; i++) {
                slots[i] = new PositionPrimitive(9_000_000_000L + i, 420 + i);
            }
            return slots;
        });

        cost("HashMap<Long, Object>, presized, 1M entries", () -> {
            Map<Long, Object> reservations = new HashMap<>(2_097_152);
            Object shared = new Object();
            for (int i = 0; i < N; i++) {
                reservations.put(9_000_000_000L + i, shared);
            }
            return reservations;
        });
    }
}
```

Measured output on JDK 21.0.7 with `-Xmx8g`:

```
Object[] of references only                         4,000,016 bytes    4.0000 per element
Optional<Integer>, uncached value                  36,000,016 bytes   36.0000 per element
Optional<Integer>, cached value 100                20,000,016 bytes   20.0000 per element
record PositionBoxed(Long, Integer)                68,000,016 bytes   68.0000 per element
record PositionPrimitive(long, int)                28,000,016 bytes   28.0000 per element
HashMap<Long, Object>, presized, 1M entries        64,388,688 bytes   64.3887 per element
```

Every one of those decomposes exactly, which is the point of showing arithmetic and measurement side by side:

| Shape | Arithmetic | Sum | Measured |
|---|---|---|---|
| `Optional<Integer>`, uncached | 4 ref + `Optional` (12 header + 4 ref = 16) + `Integer` 16 | **36** | 36.0000 |
| `Optional<Integer>`, value 100 | 4 ref + `Optional` 16 + cache hit, 0 | **20** | 20.0000 |
| `PositionBoxed(Long, Integer)` | 4 ref + record (12 header + 4 + 4 refs = 20, padded to 24) + `Long` 24 + `Integer` 16 | **68** | 68.0000 |
| `PositionPrimitive(long, int)` | 4 ref + record (12 header + 8 `long` + 4 `int` = 24) | **28** | 28.0000 |
| `HashMap<Long, Object>` entry | table slot 4 × (2,097,152 / 1,000,000) = 8.389 + `Node` (12 header + 4 hash + 4 key ref + 4 value ref + 4 next ref = 28, padded to 32) + `Long` key 24 + shared value, 0 | **64.389** | 64.3887 |

Three results worth stating out loud. Boxing both components of a two-field record took it from **28 to 68 bytes** — a 2.43× penalty for a change that looks like pure API taste. `Optional` costs a full 16 bytes on top of whatever it wraps, so an `Optional<Integer>` field is 36 bytes to express "maybe a number" that a sentinel `int` expresses in 4. And a `HashMap` entry costs **32 bytes of `Node`** before either the key or the value, plus a fractional table slot that depends on your load factor and presizing — the boxed key is less than half of it.

**Interview:** asked "how big is an `Integer`", the complete answer is three sentences. 16 bytes: a 12-byte header (8-byte mark word plus 4-byte compressed class pointer) plus the 4-byte `int`, already a multiple of the 8-byte object alignment so no padding. In a collection it costs 20, because the 4-byte reference is additional, not instead. And `Long` is 24 rather than 20 because the `long` field must be 8-byte aligned, so 4 bytes of padding go in ahead of it.

### The gotcha

Costing a boxed collection by the box alone. The estimate for "2.8M stake reservations in a `HashMap<Long, Position>`" done as "24 bytes per `Long`, so 67 MB" comes out at roughly a third of the truth: measured, that map costs **93.99 bytes per entry** — 250.99 MiB, not 67 MB. The missing pieces are the 32-byte `Node`, the fractional table slot, and the value object itself.

`ArrayList` adds a fourth trap of its own: it grows by 1.5×, so a list built without presizing is holding a backing array up to a third empty, *and* it has allocated and abandoned every intermediate array on the way. Measured, an `ArrayList<Long>` of 1,000,000 built with `new ArrayList<>(1_000_000)` cost **28,000,040 bytes**; the identical list built with `new ArrayList<>()` cost **38,586,416 bytes** — 38.59 per element against 28.00, a 38% surcharge that is entirely the resize history. Presizing is not micro-optimisation at that scale.

> **Definition.** An `Integer` occupies 16 bytes on a default 64-bit JDK 21 — an 8-byte mark word, a 4-byte compressed class pointer and the 4-byte `int` — and a `Long` occupies 24, because 8-byte field alignment forces 4 bytes of padding between the 12-byte header and the `long`; in either case a stored element also pays a separate 4-byte reference.

---

## 2. The bulk comparison, and what the residue proves (3.4.12)

`[NUM]` `[PROVE]` `[X-REF 02]` At scale the per-element figures swallow everything else, and they land on *exact integers*. That exactness is the evidence. A model fitted to a measurement produces a number like 19.7; a model that is actually correct produces 20.000, with a residue you can name to the byte.

### Why it exists

This is the arithmetic behind every "will this fit in the heap" decision — cache sizing, in-memory index sizing, the choice between a `long[]` and a `List<Long>` for a hot lookup. Leaf 3.4.12 quotes it as `int[]` ≈ 4 MB versus `List<Integer>` ≈ 20 MB for a million elements, which is the figure people repeat. It is worth confirming rather than repeating, because the confirmation reveals a condition on it that the slogan hides entirely.

**When it matters.** Above roughly 10^5 elements, always; below a few thousand, never — a 1,000-element `List<Integer>` wastes 16 KB, which is not a decision worth making. And, as the cache result below shows, sometimes not even at 10^6.

### The mechanism

`[PROVE]` The four measured rows, all `getThreadAllocatedBytes` totals on JDK 21.0.7:

| Shape | Measured bytes | MiB | Per element |
|---|---|---|---|
| `int[]` of 2,800,000 | 11,200,712 | 10.68 | **4.000** |
| `List<Integer>` (presized `ArrayList`) of 2,800,000 | 56,000,376 | 53.41 | **20.000** |
| `long[]` of 1,000,000 | 8,000,016 | — | **8.000** |
| `List<Long>` of 1,000,000 | 28,000,200 | — | **28.000** |

Ratio for the 2.8M case: 56,000,376 / 11,200,712 = **exactly 5.00×**. The decomposition: 20 = 4-byte compressed reference in the backing `Object[]` + 16-byte `Integer`; 28 = 4-byte reference + 24-byte `Long`.

Now the part that makes the whole thing trustworthy rather than merely plausible: **the residue**. Subtract the per-element product and account for what is left.

```
List<Integer>, 1,000,000 elements, presized:
  measured                       20,000,040
  20 x 1,000,000                 20,000,000
  residue                                40  = ArrayList object 24 + Object[] header 16

int[], 2,800,000 elements:
  measured (tight re-run)        11,200,016
  4 x 2,800,000                  11,200,000
  residue                                16  = int[] header exactly

List<Integer>, 2,800,000 elements, presized (tight re-run):
  measured                       56,000,040
  20 x 2,800,000                 56,000,000
  residue                                40  = ArrayList 24 + Object[] header 16
```

Both `ArrayList` constants were measured independently for this file rather than assumed: 1,000,000 fresh `new ArrayList<>(0)` instances cost **28,000,016 bytes** in an `Object[]`, so 28 − 4 = **24 bytes for an `ArrayList` object** (12-byte header + `Object[]` ref + `int size` + `int modCount` from `AbstractList` = 24, no padding); and a bare `Object[]` of 1,000,000 costs 4,000,016, so **16 bytes for the array header** (12 + a 4-byte `length` field). The residue is not a fudge factor — it is two objects whose sizes were measured separately and which add up.

**Insight:** exact-integer per-element figures plus a residue you can decompose to named objects is much stronger evidence than a round number. If the true `Integer` size were 20 bytes, the per-element figure would be 24.000 and the arithmetic would still be tidy — so tidiness alone proves nothing. What proves it is that *two* independent decompositions agree: 20 = 4 + 16 in the bulk case, and 32.0 per iteration = 2 × 16 in the escape-analysis case with no arrays involved at all.

Note the difference between the two runs of the same shape. The earlier figures carry residues of 712 and 376 rather than 16 and 40; the extra ~696 and ~336 bytes are the measuring harness's own allocation on the measured thread — string formatting, lambda capture, autoboxing in the `printf` varargs. Same shape, same JDK, different harness overhead. That is a small demonstration of the instrument's limit, discussed at the end of this concept.

`[NUM]` **Reconciling the leaf's own figures, in both units.** A million `int`s and a million boxed `Integer`s:

```
int[] of 1,000,000            4,000,016 bytes = 4.000 MB (decimal) = 3.81 MiB (binary)
List<Integer> of 1,000,000   20,000,040 bytes = 20.000 MB (decimal) = 19.07 MiB (binary)
```

Both measured. So the leaf's "≈ 4 MB versus ≈ 20 MB" is exactly right in **decimal MB** and slightly off in **MiB** — 3.81 and 19.07. State the unit, because at these sizes the 4.86% gap between MB and MiB is the difference between a container limit being respected and being exceeded.

**The condition the slogan hides — and this is the most useful correction in the file.** Measured on JDK 21.0.7, both lists presized to 1,000,000:

```
List<Integer>, 1,000,000 elements all equal to 100    4,000,040 bytes   4.00004 per element
List<Integer>, 1,000,000 elements all equal to 420   20,000,040 bytes  20.00004 per element
```

**Insight:** the 5× factor is a property of the **data**, not of the type. Every value of 100 is inside `IntegerCache`, so `Integer.valueOf(100)` returns the same shared instance a million times and the only new memory is the million references — 4.00004 bytes per element, indistinguishable from an `int[]`. Change the literal to 420 and the identical code with the identical types costs five times as much. Any benchmark or capacity estimate built on small values is measuring the cache, not the boxing.

The contrast, which stops the cache from being a general excuse: a boxed **accumulator** over 1,000,000 elements all of value 100 still allocated **23,999,976 bytes**, 24.0 per iteration. The boxed value there is the running *total*, which leaves −128..127 on the second iteration and never returns. Element boxing benefits from the cache; accumulator boxing does not. [`03c-internals-boxing-bytecode.md`](03c-internals-boxing-bytecode.md) reads the `longValue` / `ladd` / `Long.valueOf` triple that causes it.

### Diagram

No diagram of its own. The picture for the bulk comparison is D-028, embedded in [`01g-the-cost-of-boxing.md`](01g-the-cost-of-boxing.md) at the point where that file derives the four rows.

### A concrete example

A heap-sizing decision made properly, on QuizStakes' own numbers. The ledger takes **~19.8M entries/day** at ~180 bytes/row with a **90-day hot window**. Cost an in-memory index of one day's position ids three ways against a stated 512 MiB budget for the index alone, then extrapolate to the window.

```java
import com.sun.management.ThreadMXBean;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * QuizStakes writes ~19.8M ledger entries a day and keeps a 90-day hot window.
 * Cost an in-memory index of ONE day's position ids three ways against a
 * 512 MiB budget for the index alone, then extrapolate to the window.
 */
public final class LedgerIndexSizing {

    private static final ThreadMXBean BEAN =
            (ThreadMXBean) ManagementFactory.getThreadMXBean();
    private static final int ENTRIES_PER_DAY = 19_800_000;
    private static final int HOT_WINDOW_DAYS = 90;
    private static final long INDEX_BUDGET_BYTES = 512L * 1024 * 1024;

    private static Object retained;

    record Position(long positionId, long clientId, int minorUnits) {}

    private static void cost(String label, Supplier<Object> shape) {
        for (int warmup = 0; warmup < 2; warmup++) {
            retained = shape.get();
        }
        retained = null;
        long before = BEAN.getThreadAllocatedBytes(Thread.currentThread().threadId());
        retained = shape.get();
        long after = BEAN.getThreadAllocatedBytes(Thread.currentThread().threadId());
        long oneDay = after - before;
        System.out.printf("%-26s %,16d B  %6.2f/entry  %8.2f MiB  %-11s  window %,7.1f GiB%n",
                label, oneDay, (double) oneDay / ENTRIES_PER_DAY,
                oneDay / 1048576.0,
                oneDay <= INDEX_BUDGET_BYTES ? "FITS" : "OVER BUDGET",
                (double) oneDay * HOT_WINDOW_DAYS / (1024L * 1024 * 1024));
    }

    public static void main(String[] args) {
        cost("long[]", () -> {
            long[] ids = new long[ENTRIES_PER_DAY];
            for (int i = 0; i < ids.length; i++) {
                ids[i] = 9_000_000_000L + i;
            }
            return ids;
        });

        cost("List<Long>", () -> {
            List<Long> ids = new ArrayList<>(ENTRIES_PER_DAY);
            for (int i = 0; i < ENTRIES_PER_DAY; i++) {
                ids.add(9_000_000_000L + i);
            }
            return ids;
        });

        cost("HashMap<Long, Position>", () -> {
            Map<Long, Position> byId = new HashMap<>(33_554_432);
            for (int i = 0; i < ENTRIES_PER_DAY; i++) {
                long positionId = 9_000_000_000L + i;
                byId.put(positionId, new Position(positionId, 420L + i, 420));
            }
            return byId;
        });
    }
}
```

Measured output on JDK 21.0.7 with `-Xmx12g`:

```
long[]                          158,400,016 B    8.00/entry    151.06 MiB  FITS         window    13.3 GiB
List<Long>                      554,400,040 B   28.00/entry    528.72 MiB  OVER BUDGET  window    46.5 GiB
HashMap<Long, Position>       1,876,617,792 B   94.78/entry  1789.68 MiB  OVER BUDGET  window   157.3 GiB
```

The decision falls out. Against a 512 MiB index budget, **only the `long[]` fits** — 151.06 MiB, with room for the sorted-search structure on top. `List<Long>` misses by 16.72 MiB, which is the sort of margin that looks survivable in a design review and is not. And the `HashMap<Long, Position>` at 94.78 bytes per entry decomposes exactly as concept 1's table predicts: table slot 4 × (33,554,432 / 19,800,000) = 6.78, plus `Node` 32, plus boxed `Long` key 24, plus `Position` (12 header + 8 + 8 + 4 = 32) = **94.78**.

The extrapolation is the more important finding. Nothing survives the full 90-day window: 13.3 GiB even for the primitive form, 157.3 GiB for the map. So the hot window does not live in a JVM heap at any of these shapes, and the real design is a `long[]` day index in front of an external store — a conclusion the boxed arithmetic alone would have hidden behind an already-fatal number.

**Tradeoff, not fact.** The 5× is real for large collections of numbers, irrelevant below a few thousand elements, and **zero** when the values happen to sit inside the wrapper cache. So the question to carry into a design discussion is not "is boxing expensive" but three narrower ones: *how many elements at steady state*, *what is the value range*, and *is this on the retention path or the allocation path*. A million-element index answers differently from a per-request list of ten. If the answer to the first is under 10^4, the readability of `List<Long>` wins and the arithmetic on this page is irrelevant to you.

`[X-REF 02]` **The collection-side costs, which are usually larger than the boxing.** Three of them, self-contained. `HashMap` stores every mapping in a `HashMap.Node` — 12-byte header, `int hash`, and three references (`key`, `value`, `next`) = 28 bytes, padded to **32** — so a `HashMap<Long, Long>` pays 32 for the node plus 24 for each of two boxed `Long`s plus a fractional table slot, and the two boxes are less than half of it. `ArrayList` grows its backing array by **1.5×** (`newCapacity = oldCapacity + (oldCapacity >> 1)`), so a list that has just grown is holding up to a third of its array as unused slots, and it has allocated and discarded every intermediate array on the way — measured above at 38.59 versus 28.00 bytes per element for an unpresized versus presized `ArrayList<Long>` of a million. And where the key space is a dense enum rather than a number, `EnumMap` and `EnumSet` are the array-backed answer with no node and no boxing at all: `EnumSet` is a single `long` bit vector for up to 64 constants, `EnumMap` a plain `Object[]` indexed by ordinal — see [`../enums/03c-internals-enumset-enummap.md`](../enums/03c-internals-enumset-enummap.md). The full treatment of `HashMap`'s table geometry, `ArrayList`'s growth policy, and the `IntStream` and `LongStream` alternatives that avoid the box entirely belongs to guide **02 Java collections**.

### The gotcha

How the numbers are obtained matters as much as the numbers. Two common instruments give wrong answers in opposite directions.

`Runtime.getRuntime().totalMemory() - freeMemory()` is what most quick scripts use, and it measures *live heap at an arbitrary GC phase*. It moves under you: a young collection between the two reads can make an allocating loop appear to have freed memory. It is noise at the scale where these differences matter, and calling `System.gc()` around it makes it slower without making it correct.

A retained-size profiler is the right tool for the opposite question, but it double-counts in exactly the case this file cares about. Ask it for the retained size of a `List<Integer>` full of values under 128 and it will either attribute a million shared cached `Integer` instances to your list (over-counting five-fold) or attribute none of them (under-counting), depending on how it handles objects reachable from more than one root. Both answers are defensible and neither is the number you wanted.

Every figure in this file comes from `com.sun.management.ThreadMXBean.getThreadAllocatedBytes(long threadId)`, which returns a **monotonically increasing count of bytes allocated by that one thread since it started**, maintained by the allocator itself rather than sampled from the heap. It is exact, cheap, and unaffected by GC timing. And it measures **allocation, not retention**. So it answers "how many bytes did building this shape cost" precisely, and it does not answer "how many bytes does this shape occupy now" at all — a shape that allocates 38,586,416 bytes while growing retains only 28,000,040 of them. Where the two differ, this file has said which one it is quoting. That distinction is the honest limit on every number here.

> **Definition.** At scale a `List<Integer>` costs 20 bytes per element against 4 for an `int[]` — measured exactly 5.00× on 2,800,000 elements, with a 40-byte residue accounted for as one 24-byte `ArrayList` plus a 16-byte `Object[]` header — but the factor collapses to 1.00× when every value falls inside the wrapper cache, so it is a property of the data as much as of the type.

---

## Pitfalls

### Sizing a cache from the primitive figure

**Wrong**

```java
// Capacity plan for the stake-reservation index: "2.8M ints, so about 11 MB."
private final List<Integer> reservedStakeMinorUnits = new ArrayList<>(2_800_000);
// budget filed: 11 MB
```

Measured on JDK 21.0.7, that list costs **56,000,040 bytes = 53.41 MiB** — 20.000 bytes per element, not 4. The plan is short by a factor of five. The failure mode is the worst kind: the service starts, passes a load test at 10% of production volume, and dies of `OutOfMemoryError` at the daily peak, with a heap dump that shows a million `java.lang.Integer` instances and no single obvious culprit.

**Right**

```java
// 2.8M reservations x 4 bytes = 11,200,000 + 16-byte array header = 11,200,016.
// Measured: 11,200,016 bytes = 10.68 MiB.
private final int[] reservedStakeMinorUnits = new int[2_800_000];
```

or, if the API must hand out a `List`, budget from the measured per-element figure rather than the primitive width, and presize:

```java
// 20 bytes/element measured, plus a 40-byte residue. 2.8M -> 53.41 MiB.
private final List<Integer> reserved = new ArrayList<>(2_800_000);
```

**Why people believe it:** `Integer.BYTES` is 4, and it is right there in the JDK as a named constant, so 4 is the number that comes to mind. It is a true statement about the *`int` payload* and says nothing about the object wrapping it or the reference reaching it. The habit is reinforced by C, where `int*` really does cost one pointer and one `int`.

### Assuming `Long` is 20 bytes because 12 + 8 = 20

**Wrong**

```java
// "12-byte header + 8-byte long = 20 bytes per Long.
//  1M position ids in a List<Long> is 24 bytes each -> 24 MB."
long budgetBytes = 1_000_000L * (4 + 12 + 8);   // = 24,000,000
```

Measured: **28,000,040 bytes**, 28.000 per element. The estimate is 14% low, and it is low for a structural reason that repeats in every record and every map node containing a `long`.

**Right**

```java
// A long field must start on an 8-byte boundary. The header ends at offset 12,
// which is not one, so 4 bytes of padding precede the field:
//   12 header + 4 padding + 8 long = 24, already a multiple of 8.
// Plus the 4-byte compressed reference in the backing array = 28.
long budgetBytes = 1_000_000L * (4 + 24);       // = 28,000,000; measured 28,000,040
```

**Why people believe it:** the `Integer` arithmetic works without any padding term — 12 + 4 = 16, a multiple of 8 already — so the rule appears to be "header plus payload" and generalises cleanly to the wrong answer. The padding only becomes visible on an 8-byte-aligned field behind a 12-byte header, which `Integer` never has. Note the mirror-image trap: with **both** compression flags off, the header is 16 bytes, so `Long` needs *no* padding at all and `Integer` needs 4 — measured, both are 24 bytes in that configuration.

### Benchmarking with small values and concluding boxing is cheap in bulk

**Wrong**

```java
// "Measured it. A million boxed values costs the same as a million ints.
//  The 5x figure is folklore."
List<Integer> retryCounts = new ArrayList<>(1_000_000);
for (int i = 0; i < 1_000_000; i++) {
    retryCounts.add(3);                      // retry counter, always small
}
```

Measured: **4,000,040 bytes**, 4.00004 per element — genuinely identical to an `int[]`, and genuinely the wrong conclusion. Every value of 3 is inside `IntegerCache`, so `Integer.valueOf(3)` returns the same shared instance a million times and only the references are new. Change one literal:

```java
    retryCounts.add(420);                    // stake in minor units
```

Measured: **20,000,040 bytes**, 20.00004 per element. Same code, same types, same element count, five times the memory.

**Right**

Benchmark with the value distribution the production data actually has, and say which one you used:

```java
// Stake minor units range roughly 20..50_000 in production; only a vanishing
// fraction lands in the cache, so measure with representative values.
List<Integer> stakeMinorUnits = new ArrayList<>(1_000_000);
for (int i = 0; i < 1_000_000; i++) {
    stakeMinorUnits.add(420 + i);            // measured 20.00004 bytes/element
}
```

**Why people believe it:** the benchmark is honest and the measurement is correct. What is wrong is the generalisation, and the confounder is invisible in the source — nothing about `add(3)` hints that it is exercising a 256-entry array in `java.lang.Integer` rather than the allocator. Small sentinel-ish values (0, 1, −1, small counts, boolean-ish flags) are exactly what people reach for when writing a quick test, and they are exactly the values the cache covers.

### Reasoning that `-XX:-UseCompressedOops` makes `Integer` 24 bytes

**Wrong**

```
# "Heap is going to 40 GiB, so compressed oops turn off, so the header goes
#  to 16 bytes, so Integer becomes 16 + 4 = 20 padded to 24, so a boxed
#  element goes from 20 to 28 bytes."
java -Xmx40g -XX:-UseCompressedOops MyApp
```

Measured on JDK 21.0.7 with `-XX:-UseCompressedOops`: an `Object[]` of 1M full of `Integer` boxes costs **24.0 bytes per element**, not 28. `Integer` stays **16 bytes** and `Long` stays **24**. Nothing about the objects changed.

**Right**

```
# UseCompressedOops and UseCompressedClassPointers are INDEPENDENT flags.
# Measured: with -XX:-UseCompressedOops, -XX:+PrintFlagsFinal still reports
#   bool UseCompressedClassPointers = true {default}
# So the class pointer stays narrow, the header stays 12 bytes, the boxes
# keep their sizes, and only every REFERENCE doubles: 4 -> 8 bytes.
#   boxed element: 8 (ref) + 16 (Integer) = 24, measured 24.0
# Only with BOTH off does the header reach 16 and Integer reach 24:
#   boxed element: 8 (ref) + 24 (Integer) = 32, measured 32.0
java -Xmx40g MyApp     # and check: above ~32 GiB the VM turns oops off itself
```

**Why people believe it:** "compressed oops" is the name everyone knows, and the class pointer is an oop-shaped thing living in the header, so the two feel like one switch. They were also historically coupled in discussions of the 32 GiB threshold. On JDK 21 they are two `product lp64_product` flags and only one of them changes object sizes.

---

## Cheat sheet

| Thing | Fact (Java 21 LTS) |
|---|---|
| Object header, default | 12 bytes = 8-byte mark word + 4-byte compressed class pointer |
| Mark word contents | identity hash (once computed), lock/monitor state, GC age and mark bits, forwarding pointer |
| Class pointer contents | narrow `Klass` pointer — virtual dispatch, `checkcast`, GC oop maps |
| `ObjectAlignmentInBytes` | 8, `{product lp64_product} {default}` — every object size rounds up to a multiple of 8 |
| `Integer` size | **16** = 12 header + 4 `int`, no padding. Measured |
| `Long` size | **24** = 12 header + **4 padding** + 8 `long`. Measured. Not 20 |
| Why `Long` pads | a `long` field must start on an 8-byte boundary; the header ends at 12 |
| `Byte`, `Short`, `Character`, `Boolean`, `Float` | all **16** bytes. Measured |
| `Double` | **24** bytes, same padding rule as `Long`. Measured |
| Measuring `Byte`/`Boolean` | `valueOf` never allocates for either; only the deprecated constructor does. Measured 16 via `new Byte`/`new Boolean` |
| Boxed element in a collection | 4-byte reference **plus** the box. `Integer` 20, `Long` 28. The reference is additional, not instead |
| `int` vs boxed `Integer` element | 4 vs 20 = **5×**, not 4× |
| `long` vs boxed `Long` element | 8 vs 28 = **3.5×** |
| `Object[]` header | 16 bytes = 12 + 4-byte `length`. Measured (4,000,016 for 1M) |
| `ArrayList` object | 24 bytes = 12 header + `Object[]` ref + `int size` + `int modCount`. Measured |
| `HashMap.Node` | 32 bytes = 12 header + `int hash` + 3 refs = 28, padded |
| `Optional<T>` | 16 bytes = 12 header + 1 ref. An `Optional<Integer>` element is 36 |
| `record PositionBoxed(Long, Integer)` | 68 bytes/element measured, against 28 for `(long, int)` — 2.43× |
| `HashMap<Long, Position>` entry | 94.78 bytes measured = table slot 6.78 + `Node` 32 + `Long` 24 + `Position` 32 |
| `int[]` of 2,800,000 | 11,200,712 bytes = 10.68 MiB = **4.000**/element |
| `List<Integer>` of 2,800,000 | 56,000,376 bytes = 53.41 MiB = **20.000**/element. Ratio exactly **5.00×** |
| `long[]` of 1,000,000 | 8,000,016 = **8.000**/element |
| `List<Long>` of 1,000,000 | 28,000,200 = **28.000**/element |
| Residue at 1M elements | exactly **40** = `ArrayList` 24 + `Object[]` header 16 |
| Leaf's "4 MB vs 20 MB" | right in decimal MB; in MiB it is **3.81 MiB vs 19.07 MiB**. State the unit |
| Cached values kill the 5× | `List<Integer>` of 1M values all **100** = 4,000,040 (4.00004/element); all **420** = 20,000,040 |
| But not for accumulators | boxed accumulator over 1M values of 100 still allocated **23,999,976** — the running total leaves the cache |
| Unpresized `ArrayList<Long>` of 1M | 38,586,416 bytes (38.59/element) versus 28,000,040 presized — 38% resize surcharge |
| `ArrayList` growth | 1.5× (`old + (old >> 1)`), so up to a third of the backing array is empty |
| `-XX:-UseCompressedOops` alone | `UseCompressedClassPointers` stays **true {default}**. Header stays 12, `Integer` stays 16, references double: boxed element 20 → **24** |
| Both compression flags off | header 16, `Integer` **24**, `Long` **24** (no padding needed), boxed element **32**, array header 24 |
| Compressed-oops threshold | measured: `-Xmx31g` → `true {ergonomic}`, `-Xmx32g` → `false {default}`. 2^32 × 8-byte alignment = 32 GiB |
| `PrintFieldLayout` | debug-VM only: `Error: VM option 'PrintFieldLayout' is notproduct and is available only in debug version of VM.` |
| Measuring instrument used here | `ThreadMXBean.getThreadAllocatedBytes` — exact, per-thread, GC-independent |
| What it measures | **allocation, not retention**. Says what building a shape cost, not what it occupies now |
| `Runtime.totalMemory() - freeMemory()` | live heap at an arbitrary GC phase — noise at this scale |
| Retained-size profiler | double-counts or drops shared cached instances; wrong tool for values under 128 |
| Escape-analysis cross-check | `-XX:-DoEscapeAnalysis`, 2 boxes/iteration → 32.0 bytes/iteration = 2 × 16. Independent of any array |

---

## Self-test

**Q1.** How big is an `Integer`, and how do you know?

<details><summary>Answer</summary>

16 bytes on a default 64-bit JDK 21. Derivation: an 8-byte mark word plus a 4-byte compressed class pointer gives a 12-byte header, plus the 4-byte `int` field gives 16, which is already a multiple of `ObjectAlignmentInBytes = 8`, so there is no trailing padding. Two independent measurements confirm it on JDK 21.0.7. First, with `-XX:-DoEscapeAnalysis` so the boxes are really allocated, a method creating two `Integer` boxes per iteration over 5,000,000 iterations allocated 160,000,000 bytes = 32.0 per iteration = 2 × 16, with no arrays involved at all. Second, filling an `Object[]` of 1,000,000 with fresh boxes cost 20,000,016 bytes against 4,000,016 for the bare array, so 16 bytes per box. The important extension: in a collection the element costs **20** bytes, not 16, because the 4-byte compressed reference in the backing array is additional rather than instead of the object — so the comparison against 4 bytes for an `int` is 5×, not 4×.

</details>

**Q2.** Why is a `Long` 24 bytes rather than 20?

<details><summary>Answer</summary>

Alignment padding, inserted in front of the field. The header ends at offset 12, and a `long` field must start on an 8-byte boundary, so 4 bytes of padding go between the header and the field: 12 + 4 + 8 = 24, which is already a multiple of the 8-byte object alignment so nothing further is added. Measured on JDK 21.0.7 two ways: the boxed-accumulator loop allocating one `Long` per `+=` over a 1,000,000-element array cost 24,000,000 bytes = 24.0 per iteration, and an `Object[]` of a million fresh `Long`s cost 28.0 per element against 4.0 for the bare array. The naive `12 + 8 = 20` is the standard wrong answer, and it is wrong for a reason that generalises — the same padding appears in any object whose first `long` field sits directly behind a 12-byte header, including records and `HashMap` nodes. Worth adding the mirror image: with both `UseCompressedOops` and `UseCompressedClassPointers` off the header is 16 bytes, so `Long` needs no padding at all (16 + 8 = 24) while `Integer` needs 4 (16 + 4 = 20, padded to 24) — measured, both are 24 bytes in that configuration.

</details>

**Q3.** How much memory does a million boxed `int`s cost compared with an `int[]`, and what makes the answer trustworthy?

<details><summary>Answer</summary>

Measured on JDK 21.0.7: an `int[]` of 1,000,000 is 4,000,016 bytes = 4.000 MB = 3.81 MiB, and a presized `ArrayList<Integer>` of the same million distinct values is 20,000,040 bytes = 20.000 MB = 19.07 MiB. Five times. At 2,800,000 elements the same two shapes measure 11,200,712 and 56,000,376 bytes, a ratio of exactly 5.00×. The decomposition is 4-byte compressed reference in the backing `Object[]` plus 16-byte `Integer` = 20. What makes it trustworthy is not the ratio but the **residue**: subtract 20 × 1,000,000 from 20,000,040 and exactly 40 bytes are left, which is a 24-byte `ArrayList` object plus a 16-byte `Object[]` header — and both of those constants were measured separately, a million fresh `new ArrayList<>(0)` instances costing 28.0 bytes each in an `Object[]` and a bare `Object[]` of a million costing 4,000,016. Exact-integer per-element figures with a fully-named residue is much stronger evidence than a round number, because a wrong model can still produce a tidy number. State the unit when you quote it: the familiar "4 MB versus 20 MB" is decimal MB, and in MiB it is 3.81 versus 19.07.

</details>

**Q4.** Someone measures a million-element `List<Integer>` at 4 bytes per element and concludes the 5× figure is folklore. What happened?

<details><summary>Answer</summary>

Their values were inside `IntegerCache`. Measured on JDK 21.0.7, a presized `ArrayList<Integer>` of 1,000,000 elements all equal to **100** costs 4,000,040 bytes — 4.00004 per element, genuinely indistinguishable from an `int[]` — because `Integer.valueOf(100)` returns the same shared cached instance a million times and the only new memory is the million 4-byte references. The identical code with the value **420** costs 20,000,040 bytes, 20.00004 per element. So the 5× factor is a property of the **data**, not of the type, and any benchmark or capacity estimate is measuring whichever of the two regimes its test values happen to land in. The measurement was honest; the generalisation was not. There is an important counter-case that stops the cache being a general excuse: a boxed **accumulator** over 1,000,000 elements all of value 100 still allocated 23,999,976 bytes, 24.0 per iteration, because the boxed value there is the running total, which leaves −128..127 on the second iteration and never comes back. Element boxing benefits from the cache; accumulator boxing does not. The practical rule is to benchmark with the production value distribution and to say in the write-up which distribution you used.

</details>

**Q5.** Estimate a `HashMap<Long, Position>` holding 19,800,000 entries, then say where a box-only estimate would have gone wrong.

<details><summary>Answer</summary>

Per entry: a fractional table slot, a `HashMap.Node`, the boxed key, and the value object. With the map presized to 33,554,432 the table contributes 4 × (33,554,432 / 19,800,000) = 6.78 bytes per entry; `Node` is 12-byte header + `int hash` + three references (`key`, `value`, `next`) = 28, padded to **32**; the boxed `Long` key is **24**; and a `record Position(long, long, int)` is 12 + 8 + 8 + 4 = **32**. Total 94.78. Measured on JDK 21.0.7: 1,876,617,792 bytes for 19,800,000 entries = **94.78 per entry** = 1789.68 MiB. A box-only estimate — "24 bytes per `Long`, so about 475 MB" — is low by a factor of four, because the node is larger than the key and the value object is not accounted for at all. The comparison that settles the design: a plain `long[]` of the same 19,800,000 ids measures 158,400,016 bytes = 151.06 MiB, and a `List<Long>` measures 554,400,040 = 528.72 MiB. Against a 512 MiB budget for the index only the `long[]` fits. Extrapolated across the 90-day hot window, none of them do — 13.3 GiB, 46.5 GiB and 157.3 GiB respectively — so the honest conclusion is that the window lives in an external store with a primitive day index in front of it.

</details>

**Q6.** Does `-XX:-UseCompressedOops` make `Integer` bigger?

<details><summary>Answer</summary>

No, and this is the arithmetic most often restated wrongly. On JDK 21.0.7, `UseCompressedOops` and `UseCompressedClassPointers` are two independent `product lp64_product` flags. Measured: running with `-XX:-UseCompressedOops`, `-XX:+PrintFlagsFinal` still reports `UseCompressedClassPointers = true {default}`, so the class pointer stays 4 bytes, the header stays 12 bytes, and `Integer` stays **16** while `Long` stays **24**. What doubles is every *reference* — an `Object[]` of 1,000,000 went from 4,000,016 to 8,000,016 bytes — so a boxed element goes from 20 to **24** bytes per element, not to 28. Only with **both** flags off does the header reach 16 bytes, at which point `Integer` becomes 16 + 4 = 20 padded to **24**, `Long` becomes 16 + 8 = **24** with no padding, and a boxed element costs 8 + 24 = **32**; the array header also grows from 16 to 24 bytes. On the threshold: measured, `-Xmx31g` reports `UseCompressedOops = true {ergonomic}` and `-Xmx32g` reports `false {default}`, because a 32-bit offset scaled by the 8-byte object alignment addresses 2^35 bytes = 32 GiB. The counter-intuitive consequence worth volunteering is that raising a heap from 31 GiB to 33 GiB can reduce the number of objects that fit, since every reference in the process doubles.

</details>

**Q7.** What does `getThreadAllocatedBytes` measure, and what would it get wrong?

<details><summary>Answer</summary>

It returns a monotonically increasing count of the bytes **allocated** by one specific thread since that thread started, maintained by the allocator itself rather than sampled from the heap — so it is exact, cheap, and completely unaffected by GC timing. Every figure in this chapter comes from it. What it does not measure is **retention**. It answers "how many bytes did building this shape cost" and not "how many bytes does this shape occupy now", and the two diverge whenever intermediate objects are discarded: an `ArrayList<Long>` of a million built without presizing allocates 38,586,416 bytes because of the 1.5× resize history, while retaining only the 28,000,040 that the presized version allocates. It also charges the measuring harness's own allocation to the same thread, which is visible in this file — two runs of the identical `int[]` of 2,800,000 measured 11,200,712 and 11,200,016, the ~696-byte difference being `printf` formatting and lambda capture on the measured thread. The alternatives are worse for this question in opposite directions: `Runtime.totalMemory() - freeMemory()` reads live heap at an arbitrary GC phase and can show an allocating loop *freeing* memory; a retained-size profiler either attributes a million shared cached `Integer` instances to your list or attributes none of them, so it is the wrong tool precisely where values fall inside the wrapper cache.

</details>

**Q8.** Why can you not measure `Byte`'s object size the way you measure `Integer`'s, and how was it settled?

<details><summary>Answer</summary>

Because `Byte.valueOf` can never miss the cache. A `byte` cannot be outside −128..127, so the JDK 21 source has no bounds check at all — the body is `return ByteCache.cache[(int) b + offset];` — and every call returns a pre-existing instance. Measured: `Byte.valueOf((byte) i)` a million times into an `Object[]` allocated 4,000,016 bytes, exactly the array and zero boxes. `Boolean` has the same property for a different reason: it has no cache class at all, just the two eagerly-constructed `public static final Boolean TRUE` and `FALSE` statics, so `Boolean.valueOf` also never allocates. It was settled with the terminally-deprecated constructors, `@Deprecated(since="9", forRemoval=true)`: a million `new Byte((byte) i)` cost 20,000,016 bytes and a million `new Boolean(true)` cost the same, so both are 16 bytes as a measured fact rather than a derivation. The cleaner instrument would have been a layout printer, and that route was tried and refused — `-XX:+UnlockDiagnosticVMOptions -XX:+PrintFieldLayout` reports `Error: VM option 'PrintFieldLayout' is notproduct and is available only in debug version of VM.`, so it needs a debug build. JOL, covered in guide 06 JVM internals, is the tool that prints field offsets on a product VM.

</details>

---

## Open questions

- **Unverified:** the exact field offsets inside `Integer` and `Long` as HotSpot lays them out. Everything in this file is derived from the alignment rule plus allocation measurement, and the two agree to the byte on all eight wrappers, but no printed layout was obtained. The direct route was attempted and refused: `-XX:+UnlockDiagnosticVMOptions -XX:+PrintFieldLayout` produced `Error: VM option 'PrintFieldLayout' is notproduct and is available only in debug version of VM.` on the product build. What would settle it: JOL (`org.openjdk.jol.info.ClassLayout.parseClass(Long.class).toPrintable()`), which is not on this classpath, or the same flag on a debug VM. Nothing above depends on the offsets, only on the totals, which are measured.
- **Unverified:** whether the 4 bytes of padding in `Long` are placed *before* the `long` field or whether HotSpot instead places the field at offset 16 and leaves offsets 12–15 unused by some other route (for example reserving them for a future header field). The two are indistinguishable from a size measurement, and both give 24 bytes. What would settle it: the JOL output above, or `-XX:+PrintFieldLayout` on a debug VM, either of which prints the field's actual offset.
- **Unverified:** why the earlier measurement run reported an 11,200,712-byte `int[]` and a 56,000,376-byte `List<Integer>` where a tighter re-run of the identical shapes on the same JDK reported 11,200,016 and 56,000,040. The residues of the tighter run decompose exactly (16 = array header; 40 = `ArrayList` 24 + `Object[]` header 16), and the extra ~696 and ~336 bytes are consistent with the harness's own `printf` formatting, lambda capture and varargs boxing being charged to the measured thread — but that was inferred rather than isolated. What would settle it: measuring the harness's per-call allocation on its own with an empty body and subtracting it, which was done for the tighter run (measured 0 bytes for an empty body after warm-up) but not for the earlier one.

---

**Leaves covered:** 3.4.10, 3.4.11, 3.4.12 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 658
