# 02 Java Collections — `ArrayList` — INTERNALS (§4.1 `MyArrayList<E>` — the spliterator, the diff and the benchmark)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [array-list/08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md) · Next: [linked-list/01-internals.md](../linked-list/01-internals.md)

Part five of five, and the last of the class. [05](05-build-my-array-list.md) built the storage core, [06](06-build-my-array-list-b-iterators.md) the iterators, [07](07-build-my-array-list-c-sublist-and-equality.md) the view and the value semantics, [08](08-build-my-array-list-d-bulk-sort-spliterator-and-diff.md) the bulk operations and `sort`. This file adds the `Spliterator` that closes the class, then measures the finished result against `java.util.ArrayList` in a diff table and a JMH harness. The complete compiling class is the concatenation of the code blocks in 05 through 09, in order; the compile command and the full demo output are at the bottom of this file.

---

## Where `MyArrayList` stands against the real one (4.1.15)

The map first, then the mechanism. Every row below is a place the two classes differ; the last column is why the JDK made the choice it did.

| Aspect | `MyArrayList` | `java.util.ArrayList` (JDK 21) | Why the JDK bothers |
|---|---|---|---|
| Superclass | `extends AbstractList<E>` — inherits `containsAll`, `AbstractCollection` helpers and the `modCount` field | Same (`java.base/java/util/ArrayList.java`, line 119) | Reuse; `AbstractList` also supplies the `ListIterator`-based defaults `SubList` relies on |
| Methods inherited, not written | `containsAll`, `AbstractList`'s `iterator`/`listIterator` for `SubList`, `AbstractCollection`'s bulk shapes | Same set inherited, but it additionally overrides `replaceAll`, `clone`, `readObject`/`writeObject` | Every JDK override exists to remove an iterator allocation or a redundant bounds check |
| Bounds checks | `Objects.checkIndex` for reads; hand-written `rangeCheckForAdd` for inserts | Identical, plus a shared `outOfBoundsMsg` builder | `Objects.checkIndex` is a HotSpot intrinsic candidate; the JIT can fold it into the array's own implicit check |
| Growth arithmetic | `newLength`/`hugeLength` **copied into the class** | Calls `jdk.internal.util.ArraysSupport.newLength` (line 237) | `ArraysSupport` is in a package not exported to the unnamed module, so third-party code *cannot* call it and must duplicate the logic — an unavoidable divergence, not a choice |
| Array copying | `System.arraycopy`, `Arrays.copyOf` | Same | Both are HotSpot intrinsics compiled to vectorised block moves, not element loops |
| Serialization | **None.** Not `Serializable` | `implements Serializable`, `serialVersionUID = 8683452581122892189L`, custom `writeObject`/`readObject` | Default serialization would write the whole backing array including trailing `null`s; the custom form writes `size` elements and rebuilds capacity on read |
| `Cloneable` | Not implemented | `implements Cloneable`; `clone()` does `Arrays.copyOf(elementData, size)` and resets `modCount` to 0 | Shallow copy at array speed; the reset gives the clone a fresh iterator generation |
| `RandomAccess` | Implemented (marker) | Same | `Collections.binarySearch`, `shuffle` and `reverse` branch on it to pick index-based over iterator-based algorithms |
| Null policy | Nulls permitted everywhere; scans split on nullness; `equals` uses `Objects.equals`; `hashCode` maps null to 0 | Identical | `List` permits nulls by contract; only `List.of` and `Map.of` reject them |
| `Spliterator` support | `ORDERED \| SIZED \| SUBSIZED`, late-bound fence, midpoint split | Identical (line 1620), and `ArrayList.SubList` supplies its own spliterator over the offset range | Our `SubList` inherits `AbstractList`'s `IteratorSpliterator`, which batches instead of splitting in O(1) — correct but slower to parallelise |
| `SubList` shape | Inner class, `MyArrayList.this` + `parent`/`offset`/`size`/mirror | Explicit `root` **and** `parent` fields (line 1194) | Both are one hop from any depth; the JDK's form does not depend on being an inner class |
| Allocation tricks | Two shared `{}` sentinels; bitset sized from the first condemned index; `StringBuilder` pre-sized `2 + size * 4` | Same three | An empty `ArrayList` costs 40 bytes of header and fields and **zero** array bytes — [D-137](../diagrams/D-137-object-array-header-layout.svg) |
| `Itr.forEachRemaining` | Not overridden | Overridden (line 1074) to hoist `cursor`/`lastRet` writes out of the loop | Removes two heap writes per element from the hottest traversal path |
| `elementAt` helper | `static <E> E elementAt(Object[], int)` with `@SuppressWarnings` | Same shape, package-private | Confines the unchecked cast to one method the JIT inlines to nothing |
| `capacity()` | Public, for the demo | **Absent** | Publishing capacity would freeze the growth policy into the API contract permanently |
| `replaceAll`, `toArray(IntFunction)` | Not implemented | Implemented | Each removes an iterator allocation from a commonly-called path |

**Insight:** almost every divergence here is either a module-boundary constraint (`ArraysSupport`) or an optimisation the JDK can afford because it is compiled once and run everywhere. None is a correctness difference — `MyArrayList` passes `equals` in both directions against `java.util.ArrayList` and produces identical `hashCode` and `toString`, verified in the demo output below.

The one row worth reading twice is the `Spliterator` row, because that is the mechanism this file exists to build. Everything else in the table is a decision already made; this one still needs its code.

---

### `spliterator()` with late binding and midpoint `trySplit` (4.1.14)

**Mental model.** A spliterator is an iterator that can hand you half of itself. `trySplit` cuts the remaining range at its midpoint, returns the left half as a new spliterator and keeps the right half. Recursively applied by the fork-join framework this builds a balanced tree of leaf tasks — [D-124a](../diagrams/D-124a-arraylist-split.svg) and [D-123](../diagrams/D-123-tryspt-recursion.svg).

**Why it exists.** `Iterator` cannot be parallelised: it exposes one cursor and no way to hand a disjoint portion to another thread. The stream framework needed a source abstraction that could describe *itself* — how many elements remain, whether the count is exact, whether order matters — and could divide. `Spliterator` is that abstraction, and it is why `stream()` is a method on `Collection` rather than a wrapper you build by hand.

**When array-backed lists win, and when they do not.** They are the best case: splitting is O(1) integer arithmetic, and every subtask knows its exact element count in advance, which is what `SIZED` and `SUBSIZED` advertise, so the framework can size output arrays without buffering. `LinkedList` must walk to find a midpoint and reports `SIZED` but not `SUBSIZED`. Against that, none of it helps for a small list or a cheap per-element operation — the fork-join submission overhead is measured in microseconds, and a thousand-element sum finishes faster sequentially.

```java
    @Override
    public Spliterator<E> spliterator() {
        return new MySpliterator(0, -1, 0);
    }

    final class MySpliterator implements Spliterator<E> {
        private int index;            // current position
        private int fence;            // -1 until bound; then one past the last index
        private int expectedModCount; // set when the fence is set

        MySpliterator(int origin, int fence, int expectedModCount) {
            this.index = origin;
            this.fence = fence;
            this.expectedModCount = expectedModCount;
        }

        private int getFence() {
            int hi;
            if ((hi = fence) < 0) {
                expectedModCount = modCount;
                hi = fence = size;
            }
            return hi;
        }

        @Override
        public MySpliterator trySplit() {
            int hi = getFence(), lo = index, mid = (lo + hi) >>> 1;
            return (lo >= mid) ? null : new MySpliterator(lo, index = mid, expectedModCount);
        }

        @Override
        public boolean tryAdvance(Consumer<? super E> action) {
            Objects.requireNonNull(action);
            int hi = getFence(), i = index;
            if (i < hi) {
                index = i + 1;
                action.accept(elementAt(elementData, i));
                if (modCount != expectedModCount) {
                    throw new ConcurrentModificationException();
                }
                return true;
            }
            return false;
        }

        @Override
        public void forEachRemaining(Consumer<? super E> action) {
            Objects.requireNonNull(action);
            final Object[] es = elementData;
            int i, hi, mc;
            if ((hi = fence) < 0) {
                mc = modCount;
                hi = size;
            } else {
                mc = expectedModCount;
            }
            if ((i = index) >= 0 && (index = hi) <= es.length) {
                for (; i < hi; i++) {
                    action.accept(elementAt(es, i));
                }
                if (modCount == mc) {
                    return;
                }
            }
            throw new ConcurrentModificationException();
        }

        @Override
        public long estimateSize() {
            return getFence() - index;
        }

        @Override
        public int characteristics() {
            return Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED;
        }
    }
}
```

That closing brace is the last brace of `MyArrayList`. The class is complete.

Three decisions, all about *when* state is captured.

**`fence == -1` means unbound.** The spliterator returned by `spliterator()` has not yet decided what range it covers or what `modCount` it expects; it commits on the first `getFence()`. This is **late binding**, and it is why `list.stream()` can be built, elements added, and *then* traversed, picking up the additions. Capturing `size` in the constructor would break that and is the most common mistake in a hand-rolled spliterator. The JDK explains the rationale in a long comment at line 1631.

**`mid = (lo + hi) >>> 1`, unsigned shift.** `(lo + hi)` can overflow into a negative `int` on very large ranges; `>>> 1` treats the sum as unsigned and recovers the correct midpoint. `(lo + hi) / 2` would give a negative index — the same fix as the famous binary-search overflow bug.

**`trySplit` returns `null` when `lo >= mid`.** A range of 0 or 1 elements cannot be usefully halved, and returning a spliterator over an empty range would make the framework recurse forever. `null` means "I am a leaf".

`forEachRemaining` sets `index = hi` *before* the loop and checks `modCount` only *after* it, so the hot loop is a bare array walk with no per-element bookkeeping — the reason `list.stream().forEach(...)` is close to a raw `for` loop in throughput. `tryAdvance` cannot make that trade and checks per element. The cost of that choice is a real gap in detection, and it is the subject of the third pitfall below.

**Verified:**

```
parallel sum 1..1000 -> 500500
trySplit halves      -> 500 + 500 characteristics=SIZED:true SUBSIZED:true
```

**Interview:** *Why does `trySplit` return the left half and keep the right?* So the calling thread can keep working on the tail it already holds while the returned prefix is handed to another worker, with no reassignment of the receiver's own state beyond `index = mid`. The convention is fixed by the `Spliterator` contract — the returned spliterator must cover a *strict prefix* of the elements the receiver would otherwise have covered.

> An array-backed spliterator binds its range and `modCount` lazily on first use, splits at the unsigned midpoint in O(1), and can honestly advertise `SIZED | SUBSIZED` because every child's exact count is known before traversal.

---

## A JMH sketch: append and mid-insert (4.1.16)

JMH is the only credible way to measure this; a `System.nanoTime()` loop measures dead-code elimination, not your list. Current coordinates, verified against Maven Central: `org.openjdk.jmh:jmh-core:1.37` and the annotation processor `org.openjdk.jmh:jmh-generator-annprocess:1.37`.

```xml
<dependency>
  <groupId>org.openjdk.jmh</groupId>
  <artifactId>jmh-core</artifactId>
  <version>1.37</version>
</dependency>
<dependency>
  <groupId>org.openjdk.jmh</groupId>
  <artifactId>jmh-generator-annprocess</artifactId>
  <version>1.37</version>
  <scope>provided</scope>
</dependency>
```

```java
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;
import org.openjdk.jmh.infra.Blackhole;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 10, time = 1)
@Fork(value = 3, jvmArgsAppend = {"-XX:+UseParallelGC", "-Xms2g", "-Xmx2g"})
@State(Scope.Benchmark)
public class ListBenchmark {

    @Param({"1000", "100000"})
    private int n;

    private List<Integer> boxed;

    @Setup(Level.Trial)
    public void setUpTrial() {
        boxed = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            boxed.add(i);          // source data; boxing happens once, not per invocation
        }
    }

    @Benchmark
    public MyArrayList<Integer> appendMine() {
        MyArrayList<Integer> l = new MyArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(boxed.get(i));
        }
        return l;                  // returned, so JMH's implicit Blackhole keeps it alive
    }

    @Benchmark
    public ArrayList<Integer> appendReal() {
        ArrayList<Integer> l = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(boxed.get(i));
        }
        return l;
    }

    @State(Scope.Thread)
    public static class MidInsertState {
        MyArrayList<Integer> mine;
        ArrayList<Integer> real;

        @Setup(Level.Invocation)   // fresh lists per invocation: insertion is destructive
        public void setUp() {
            mine = new MyArrayList<>();
            real = new ArrayList<>();
            for (int i = 0; i < 10_000; i++) {
                mine.add(i);
                real.add(i);
            }
        }
    }

    @Benchmark
    public void midInsertMine(MidInsertState s, Blackhole bh) {
        for (int i = 0; i < 1_000; i++) {
            s.mine.add(s.mine.size() / 2, i);
        }
        bh.consume(s.mine);
    }

    @Benchmark
    public void midInsertReal(MidInsertState s, Blackhole bh) {
        for (int i = 0; i < 1_000; i++) {
            s.real.add(s.real.size() / 2, i);
        }
        bh.consume(s.real);
    }
}
```

Run it with `java -jar target/benchmarks.jar ListBenchmark -prof gc`, and read the `gc.alloc.rate.norm` column as carefully as the time column — for append, allocation *is* the cost.

`@Fork(3)` runs three separate JVMs. A single JVM's JIT profile is shaped by whichever benchmark ran first; forking exposes that as run-to-run variance instead of hiding it.

`@Setup(Level.Invocation)` on the mid-insert state is mandatory, because the benchmark mutates the list. Reusing one across invocations would make each iteration operate on a longer list than the last, and the numbers would drift upward with no explanation. JMH warns that `Level.Invocation` has its own timing overhead; that is acceptable here because the measured unit is a thousand inserts, orders of magnitude above the setup granularity.

Returning the list, or passing it to a `Blackhole`, is what stops the JIT proving the whole loop dead and deleting it — the single most common way benchmarks lie.

Boxing is hoisted into `@Setup`. Without that, `appendMine` would be measuring `Integer.valueOf`, and the `IntegerCache` for values under 128 would make small-`n` runs look artificially fast — [D-22](../diagrams/D-22-integer-cache.svg).

Fixed heap and a simple collector remove GC-sizing noise from a benchmark whose whole point is allocation behaviour.

**Unverified:** the actual throughput numbers this harness produces on any given machine. Running it here would report figures specific to one laptop's CPU and thermal state, which is worse than no number. What the harness *is* expected to show, from the code alone: append times within noise of each other, since both classes execute the same `grow` arithmetic and the same `System.arraycopy` intrinsic; and mid-insert times within noise, dominated by the identical `arraycopy` shift. A published figure would need a named CPU model, JDK build and `-prof perfnorm` output to be meaningful.

---

## Pitfalls

### Binding a hand-rolled spliterator's fence in the constructor

**Wrong**

```java
MySpliterator(int origin) {
    this.index = origin;
    this.fence = size;                  // bound eagerly at construction
    this.expectedModCount = modCount;
}
// Stream<E> s = list.stream();  list.add(x);  s.count();  -> misses x, or throws CME
```

**Right**

```java
private int getFence() {
    int hi;
    if ((hi = fence) < 0) {             // -1 means "not yet bound"
        expectedModCount = modCount;
        hi = fence = size;
    }
    return hi;
}
```

`Spliterator` is specified as *late-binding*: it binds to the source's contents at first traversal or first split, not at construction. Binding early both violates the spec and turns a legal add-then-traverse into a spurious failure.

**Why people believe it:** a constructor is the natural place to capture state, and the eager version passes every test where the stream is consumed on the line it is created.

### Expecting a parallel stream to fail fast on interference

**Wrong**

```java
var stream = big.parallelStream();
new Thread(() -> big.add(999)).start();   // concurrent structural change
long n = stream.count();                  // often completes, no exception, wrong answer
```

**Right**

```java
List<Integer> snapshot = List.copyOf(big);   // or synchronize, or use CopyOnWriteArrayList
long n = snapshot.parallelStream().count();
```

`forEachRemaining` — the method the framework uses for the bulk of a parallel traversal — checks `modCount` exactly **once**, after its whole loop. That is deliberate: the check is hoisted out of the hot path so a stream over an uncontended list runs at raw-array speed. The cost is that a modification which lands and is observed within a single subtask's loop may never be reported, and `count()` on a `SIZED` spliterator can be answered from `estimateSize()` without traversing at all. Fail-fast is a debugging aid, not a concurrency control, and parallel traversal weakens it further.

**Why people believe it:** sequential iteration over the same list throws reliably, so the fail-fast behaviour looks like a property of the collection rather than of the particular traversal method being used.

### Trusting a benchmark that never consumes its result

**Wrong**

```java
@Benchmark
public void appendMine() {
    MyArrayList<Integer> l = new MyArrayList<>();
    for (int i = 0; i < n; i++) {
        l.add(boxed.get(i));
    }
}                                        // l is never used: the JIT may delete the whole loop
```

**Right**

```java
@Benchmark
public MyArrayList<Integer> appendMine() {
    MyArrayList<Integer> l = new MyArrayList<>();
    for (int i = 0; i < n; i++) {
        l.add(boxed.get(i));
    }
    return l;                            // JMH consumes the return value
}
```

Escape analysis can prove `l` never escapes, scalar-replace it, and then dead-code-eliminate every `add`. The benchmark reports a suspiciously flat time that does not scale with `n` — the tell that the loop is gone. Returning the value, or `bh.consume(l)`, keeps it alive.

**Why people believe it:** the loop obviously "does work", and the number that comes back is plausible. Nothing in the output says the code was deleted; you have to notice that doubling `n` did not double the time.

---

## Cheat sheet

| Item | Value / rule |
|---|---|
| Spliterator characteristics | `ORDERED \| SIZED \| SUBSIZED` |
| Spliterator binding | late: `fence == -1` until the first `getFence()` |
| What binding captures | the range end (`size`) and `expectedModCount`, together |
| `trySplit` midpoint | `(lo + hi) >>> 1`, unsigned to survive overflow |
| `trySplit` returns | the **left** half (a strict prefix); the receiver keeps the right |
| `trySplit` leaf signal | `null` when `lo >= mid` |
| `forEachRemaining` | sets `index = hi` before the loop, checks `modCount` once after |
| `tryAdvance` | checks `modCount` per element — slower, stricter |
| `estimateSize()` | exact, because `SIZED` is advertised |
| Parallel interference | may go undetected; fail-fast is weaker under `forEachRemaining` |
| `LinkedList` by contrast | **also** `ORDERED \| SIZED \| SUBSIZED` (`LinkedList.java:1271`) — measured `SUBSIZED=true` on JDK 21; splitting is still O(n) because `trySplit` **copies** a prefix (`BATCH_UNIT = 1024`, growing per call, capped at `MAX_BATCH = 1 << 25`). `SUBSIZED` is a promise about *knowing sizes*, not about the split being cheap |
| Not implemented vs the real one | `Serializable`, `Cloneable`, `replaceAll`, `Itr.forEachRemaining`, a `SubList` spliterator |
| Cannot be reproduced at all | `ArraysSupport.newLength` — `jdk.internal.util` is not exported |
| Empty `ArrayList` footprint | 40 bytes of object, zero array bytes |
| `serialVersionUID` (real one) | `8683452581122892189L` |
| `clone()` (real one) | `Arrays.copyOf(elementData, size)`, `modCount` reset to 0 |
| JMH coordinates | `org.openjdk.jmh:jmh-core:1.37` + `jmh-generator-annprocess:1.37` |
| JMH must-haves | `@Fork(3)`, consume the result, `Level.Invocation` for destructive state |

---

## Self-test

**Q1.** `spliterator()` passes `-1` as the fence. What is deferred by that, and what user-visible behaviour depends on the deferral?

<details><summary>Answer</summary>

Two things are deferred together: the end of the range (`size`) and the `expectedModCount` snapshot. Neither is decided until the first call to `getFence()`, which happens on the first `trySplit`, `tryAdvance`, `forEachRemaining` or `estimateSize`. The user-visible behaviour is that `Stream<E> s = list.stream();` followed by `list.add(x);` followed by consuming `s` is legal and sees `x`. The `Spliterator` javadoc calls this *late-binding* and it is the specified default for collection spliterators. Binding in the constructor would make that sequence either miss the element or throw `ConcurrentModificationException`, and both are wrong. Deferring also improves precision in the other direction: the `modCount` captured is the one in effect when traversal actually begins, so changes made between stream creation and traversal are not spuriously reported as interference.

</details>

**Q2.** Why `(lo + hi) >>> 1` rather than `(lo + hi) / 2` or `lo + (hi - lo) / 2`?

<details><summary>Answer</summary>

`(lo + hi)` is `int` addition and can overflow to a negative number when both indices are large — on a list near `Integer.MAX_VALUE` elements, or more realistically on any spliterator whose range was constructed from large offsets. `/ 2` on a negative value gives a negative midpoint, which becomes a negative array index or a nonsense split. `>>> 1` is an unsigned right shift: it treats the 32-bit sum as unsigned, so the overflowed bit pattern shifts back down into the correct positive midpoint. `lo + (hi - lo) / 2` is also correct and is what many codebases use, but it is one more arithmetic operation and the JDK prefers the shift. This is the same class of bug as the binary-search overflow Josh Bloch wrote up in 2006, which sat undetected in `Arrays.binarySearch` for nine years.

</details>

**Q3.** What breaks if `trySplit` returns a spliterator over an empty range instead of `null`?

<details><summary>Answer</summary>

The fork-join framework recurses without bound. `AbstractTask` splits until `trySplit` returns `null`, treating that as the signal that a node is a leaf. An empty-range spliterator would be split again, yielding another empty one, forever — the symptom is a `StackOverflowError` or unbounded growth in task objects, arriving well after the code looks correct in a sequential test. The guard `lo >= mid` covers ranges of 0 and 1 elements: for a range of 1, `lo` and `mid` coincide, so there is no way to produce two non-empty halves and the node correctly declares itself a leaf.

</details>

**Q4.** `characteristics()` returns `SUBSIZED`. What exactly is that promising, and when would claiming it be a lie?

<details><summary>Answer</summary>

`SIZED` promises that `estimateSize()` is the exact remaining count. `SUBSIZED` promises that *every* spliterator produced by `trySplit`, recursively, is also `SIZED` — the whole split tree has exact counts at every node. That lets the stream framework allocate exactly-sized output arrays for a `toArray` or a `collect` without buffering into a growable structure, which is a large part of why parallel streams over `ArrayList` are fast. Claiming it is a lie whenever splitting cannot guarantee exact child sizes: a spliterator over a hash table's buckets knows the total but not how many elements land on each side of a split, and an `IteratorSpliterator` that splits by pulling fixed-size batches does not know how many remain. Advertising `SUBSIZED` falsely produces wrong-sized arrays and corrupt results with no exception. Here it is honest because the split is pure index arithmetic.

</details>

**Q5.** `forEachRemaining` assigns `index = hi` before running its loop, and checks `modCount` only after. Why both, and what is the cost?

<details><summary>Answer</summary>

Assigning `index = hi` up front means the spliterator is logically exhausted from the first instant, so no per-iteration cursor write is needed — the loop runs on a local `i` that lives in a register. Checking `modCount` once at the end removes the other per-element heap read. Together they reduce the inner loop to an array load and a call to the consumer, which is why `list.stream().forEach(...)` gets close to a hand-written `for` loop. The cost is detection latency: interference that occurs and is fully absorbed inside a single subtask's loop is reported only at the end, and the elements already passed to the consumer were passed regardless. `tryAdvance` makes the opposite trade, checking per element, which is why the two methods do not share an implementation. The JDK's comment at line 1631 spells out this deliberate imprecision.

</details>

**Q6.** The diff table says one JDK behaviour cannot be reproduced for reasons of module access. Which, and what is the workaround?

<details><summary>Answer</summary>

Calling `jdk.internal.util.ArraysSupport.newLength`. `ArraysSupport` lives in the `jdk.internal.util` package of the `java.base` module, which is not exported to the unnamed module, so any third-party class referencing it fails to compile without `--add-exports`. The workaround is to copy `newLength` and `hugeLength` verbatim as private static methods, along with `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8`. The logic is identical, so the growth sequence matches exactly; what is lost is any future JDK improvement to that method and any possibility that HotSpot special-cases the internal version. It is the only entry in the diff table that is a hard constraint rather than a design choice — everything else, from serialization to `Itr.forEachRemaining`, is something this class could implement and chose not to.

</details>

**Q7.** `java.util.ArrayList` is `Serializable` but marks `elementData` `transient` and writes the elements by hand. Why not let default serialization handle the array?

<details><summary>Answer</summary>

Because the array's length is capacity, not size. A list holding three elements in a capacity-10 000 array would serialise 10 000 slots, 9 997 of them `null` — a stream tens of kilobytes larger than the data warrants, and on read it would resurrect the wasteful capacity too. The custom `writeObject` emits `size` followed by exactly `size` elements; `readObject` allocates a right-sized array. It also snapshots `modCount` and rechecks it at the end, so serialising a concurrently modified list throws rather than emitting a torn stream. `MyArrayList` implements none of this — it is not `Serializable` at all — which is a deliberate omission rather than an oversight, since serialization mechanics are orthogonal to the data-structure mechanics this class exists to show.

</details>

**Q8.** The JMH sketch uses `@Setup(Level.Trial)` for the append benchmark's source data but `@Setup(Level.Invocation)` for the mid-insert state. Why different levels?

<details><summary>Answer</summary>

`Level.Trial` runs once per fork, before any warmup. The append benchmark's `boxed` list is read-only source data, so building it once is correct and keeps `Integer.valueOf` boxing out of the measured region — otherwise the benchmark would partly measure the `IntegerCache`. The mid-insert benchmark *mutates* its lists, so reusing one across invocations would leave each invocation starting from a longer list than the last, and the measured time would climb steadily for reasons unrelated to the code under test. `Level.Invocation` rebuilds a fresh 10 000-element list per invocation. JMH explicitly warns that `Level.Invocation` setup is itself timed at low granularity and can distort short benchmarks; acceptable here only because the measured work is a thousand mid-inserts into a ten-thousand-element list, far above the noise floor of the setup.

</details>

---

## The compile and run, verbatim

The five files' code blocks, concatenated in order 05, 06, 07, 08, 09, are one compiling class.

```
JAVA_HOME=$(/usr/libexec/java_home -v 21)
"$JAVA_HOME/bin/javac" -Xlint:all -d /tmp/jc-build-arraylist/out /tmp/jc-build-arraylist/*.java
"$JAVA_HOME/bin/java" -cp /tmp/jc-build-arraylist/out Demo
```

`javac 21.0.7`, zero errors and zero warnings under `-Xlint:all`. Full output of `Demo`:

```
default capacity before first add -> 0
default capacity after first add -> 10
capacity after 11 adds -> 15
zero-arg capacity before add -> 0
zero-arg capacity after 1 add -> 1
zero-arg capacity after 2 adds -> 2
zero-arg capacity after 3 adds -> 3
zero-arg capacity after 4 adds -> 4
add(2,"c") -> [a, b, c, d]
after remove(1) -> [a, c] size=2 capacity=3
slot past size is nulled -> true
remove(Object) missing -> false
for-each + add mid-iteration -> ConcurrentModificationException
Itr.remove drained without CME -> [a, c, d]
ListItr.add after 'a' -> [a, b, c] nextIndex=2
ListItr.previous -> b
ListItr.set on previous -> [a, B, c]
ListItr.set right after add -> IllegalStateException
subList(1,4) -> [b, c, d]
view.set(0,"B") writes through -> [a, B, c, d, e]
view.remove(0) shrinks parent -> [a, c, d, e] view=[c, d]
view read after parent structural change -> ConcurrentModificationException
removeIf(even) -> true [1, 3, 5, 7, 9]
sort(naturalOrder) -> [apple, fig, kiwi, pear]
sort(byLengthDesc) -> [apple, kiwi, pear, fig]
parallel sum 1..1000 -> 500500
trySplit halves -> 500 + 500 characteristics=SIZED:true SUBSIZED:true
mine.equals(theirs) -> true
theirs.equals(mine) -> true
hashCodes match -> true
toString -> true [a, b]
ensureCapacity(100) -> 100
trimToSize with 1 element -> 1
clear -> [] size=0 capacity=1
removeAll([b,d]) -> [a, c]
addAll(1,[x,y]) -> [a, x, y, c]
retainAll([a,y]) -> [a, y]
stream via sublist -> a|c
get(9) on size-3 list -> IndexOutOfBoundsException
IOOBE message -> Index 5 out of bounds for length 1
negative initial capacity -> IllegalArgumentException
```

---

**Leaves covered:** 4.1.14–4.1.16 (3 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 520
