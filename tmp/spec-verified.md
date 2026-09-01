## Verified figures and corrections — use these, not what older material says

Everything in this block was re-verified from primary source or by running it on this machine
before you were dispatched. Where it contradicts the syllabus leaf text, **this block wins** and
you say so in the notes.

### 1. The virtual-thread scheduler's defaults — verified, and the flat "256" is wrong

`VirtualThread.createDefaultScheduler()`, OpenJDK at the **jdk-21+35** tag
(`raw.githubusercontent.com/openjdk/jdk/jdk-21+35/src/java.base/share/classes/java/lang/VirtualThread.java`),
quoted verbatim:

```java
int parallelism, maxPoolSize, minRunnable;
String parallelismValue = System.getProperty("jdk.virtualThreadScheduler.parallelism");
String maxPoolSizeValue = System.getProperty("jdk.virtualThreadScheduler.maxPoolSize");
String minRunnableValue = System.getProperty("jdk.virtualThreadScheduler.minRunnable");
if (parallelismValue != null) {
    parallelism = Integer.parseInt(parallelismValue);
} else {
    parallelism = Runtime.getRuntime().availableProcessors();
}
if (maxPoolSizeValue != null) {
    maxPoolSize = Integer.parseInt(maxPoolSizeValue);
    parallelism = Integer.min(parallelism, maxPoolSize);
} else {
    maxPoolSize = Integer.max(parallelism, 256);
}
if (minRunnableValue != null) {
    minRunnable = Integer.parseInt(minRunnableValue);
} else {
    minRunnable = Integer.max(parallelism / 2, 1);
}
Thread.UncaughtExceptionHandler handler = (t, e) -> { };
boolean asyncMode = true; // FIFO
return new ForkJoinPool(parallelism, factory, handler, asyncMode,
             0, maxPoolSize, minRunnable, pool -> true, 30, SECONDS);
```

What that establishes, and what you must write:

- Default parallelism is `Runtime.getRuntime().availableProcessors()`.
- **`maxPoolSize` defaults to `Integer.max(parallelism, 256)` — 256 is a floor, not a flat
  default.** On a machine with more than 256 available processors, `maxPoolSize` equals
  parallelism. Anyone who says "the default is 256" is right only for machines below 257 cores;
  say it the way the source says it.
- Setting `jdk.virtualThreadScheduler.maxPoolSize` below the processor count also **clamps
  parallelism down** to it — one property silently moves two numbers.
- `minRunnable` defaults to `max(parallelism / 2, 1)`. This is a third tuning property most
  material never mentions: `jdk.virtualThreadScheduler.minRunnable`.
- The scheduler is a `ForkJoinPool` constructed with `asyncMode = true`, and the source's own
  comment on that line is `// FIFO`. That comment is the evidence for the FIFO claim — quote it.
- The pool has a 30-second worker keep-alive (`30, SECONDS`) and a `pool -> true` saturation
  predicate.

### 2. `LEAF_TARGET` and `suggestTargetSize` — verified, and "rounded up" is wrong

`AbstractTask`, same tag, verbatim:

```java
private static final int LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2;

/**
 * Default target of leaf tasks for parallel decomposition.
 * To allow load balancing, we over-partition, currently to approximately
 * four tasks per processor, which enables others to help out
 * if leaf tasks are uneven or some processors are otherwise busy.
 */
public static int getLeafTarget() {
    Thread t = Thread.currentThread();
    if (t instanceof ForkJoinWorkerThread) {
        return ((ForkJoinWorkerThread) t).getPool().getParallelism() << 2;
    }
    else {
        return LEAF_TARGET;
    }
}

public static long suggestTargetSize(long sizeEstimate) {
    long est = sizeEstimate / getLeafTarget();
    return est > 0L ? est : 1L;
}
```

What that establishes:

- `LEAF_TARGET` is exactly as the syllabus states: the common pool's parallelism shifted left by
  two, i.e. ×4.
- **`suggestTargetSize` is floored integer division, clamped to a minimum of 1 — not rounded
  up.** Correct the syllabus wording where you restate it.
- The target is **not** fixed to the common pool. `getLeafTarget()` reads the *current* pool's
  parallelism when the calling thread is a `ForkJoinWorkerThread`, which is the mechanism behind
  the "submit the terminal operation into your own pool" trick: the decomposition width follows
  the pool the task actually runs in.
- The javadoc gives the intent in the JDK's own words — "we over-partition, currently to
  approximately four tasks per processor" — quote it rather than asserting "four per core".

### 3. The OpenJDK LVTI style guide — verified, printable

`openjdk.org/projects/amber/guides/lvti-style-guide` returned 200 on re-fetch, so the identifiers
are safe to print.

Principles:

- **P1** Reading code is more important than writing code.
- **P2** Code should be clear from local reasoning.
- **P3** Code readability shouldn't depend on IDEs.
- **P4** Explicit types are a tradeoff.

Guidelines:

- **G1** Choose variable names that provide useful information.
- **G2** Minimize the scope of local variables.
- **G3** Consider `var` when the initializer provides sufficient information to the reader.
- **G4** Use `var` to break up chained or nested expressions with local variables.
- **G5** Don't worry too much about "programming to the interface" with local variables.
- **G6** Take care when using `var` with diamond or generic methods.
- **G7** Take care when using `var` with literals.

### 4. The exhaustive enum switch expression's synthetic default — the syllabus has it inverted

Syllabus leaf 3.12.7 says `IncompatibleClassChangeError` is what an exhaustive enum switch
expression's synthetic default throws on Java 21, and that it "replaced the older
`NoSuchFieldError`/`MatchException` shapes". **That is backwards.** Verified on this machine by
compiling the enum and the switch separately, adding a constant, and recompiling only the enum:

```
release 14 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 17 -> Exception in thread "main" java.lang.IncompatibleClassChangeError
release 21 -> Exception in thread "main" java.lang.MatchException
```

and in `javap -c` on the `--release 21` class file:

```
36: new           #19    // class java/lang/MatchException
42: invokespecial #21    // Method java/lang/MatchException."<init>":(Ljava/lang/String;Ljava/lang/Throwable;)V
45: athrow
```

So the correct statement, which is itself the version trap: the synthetic default exists at every
release, but the type it throws **changed at 21** — `IncompatibleClassChangeError` through Java
20, `java.lang.MatchException` from Java 21, constructed with the `(String, Throwable)`
constructor. Write it that way, give both, and name the release that changed it.

### 5. A record's compact constructor cannot assign the field — the real diagnostic

Verified by compiling it:

```
T.java:4: error: cannot assign a value to final variable bonusPortion
        this.bonusPortion = bonusPortion.setScale(2);
            ^
1 error
```

Not "invalid explicit assignment" and not "impossible to explicitly assign a field of a record
class". The component field is `final`, and that is the whole reason: inside a compact constructor
you reassign the *parameter*, and the compiler emits the field write for you at the end.

### 6. Corrections the prompt requires be carried through from the previous guide

1. **Pinning is dated at every mention.** `synchronized` pins a virtual thread on Java 21. JEP 491
   makes object monitors continuation-aware in **Java 24** and removes that cause. Native and
   foreign frames still pin, so the `jdk.VirtualThreadPinned` JFR event survives and the
   diagnostic does not disappear. "Use `ReentrantLock`" is therefore a **version-scoped** answer,
   correct on 21 and unnecessary from 24.
2. **The common pool's width is stated in both halves.** `ForkJoinPool.commonPool()`'s default
   parallelism is `availableProcessors() - 1`, **and** the thread that submits the terminal
   operation participates in the computation, so the **effective width equals the core count**.
   Never state only one half.
3. **Structured concurrency is named at both shapes, never as "still evolving".**
   Java 21 (JEP 453, **preview**, needs `--enable-preview`): `StructuredTaskScope` with public
   constructors, `fork` returning `Subtask<T>` (not `Future<T>`), the policies
   `ShutdownOnFailure` and `ShutdownOnSuccess`, `join`/`joinUntil`/`shutdown`/`close`, all on the
   owning thread inside try-with-resources. The package moved from `jdk.incubator.concurrent` to
   `java.util.concurrent` at 21.
   Java 25 (JEP 505): public constructors replaced by static `open()` factories, and the two
   shutdown policies replaced by a composable `Joiner`.

### 7. `Collectors.summingInt` accumulates into `int[1]` and overflows — the syllabus says `long[]`

Syllabus leaf 3.6.8 says "`averagingInt`/`summingInt` accumulate into a `long[]`, so no
compensation is needed". Half right. Verified against `java.util.stream.Collectors` at the
**jdk-21+35** tag, the accumulator arrays are:

| Collector | Accumulator array | What the slots hold |
|---|---|---|
| `summingInt` | `new int[1]` | the running sum, **as an `int`** |
| `summingLong` | `new long[1]` | the running sum |
| `summingDouble` | `new double[3]` | Kahan: high-order sum, compensation, simple sum |
| `averagingInt` | `new long[2]` | sum, count |
| `averagingLong` | `new long[2]` | sum, count |
| `averagingDouble` | `new double[4]` | Kahan sum, compensation, count, simple sum |

So `summingInt` has **exactly the same silent-overflow trap as `IntStream.sum()`**, which is
worth a `**Pitfall:**` of its own and is not what most material claims. Proved on this machine
(`javac --release 21`), summing 1,000,000,000 three times:

```
summingInt : -1294967296
summingLong: 3000000000
expected   : 3000000000
```

`averagingInt` genuinely is safe, because it accumulates the sum into a `long[2]` slot — that is
the part the syllabus got right. Write both halves, and be precise about which.

### 8. One machine, one set of core numbers — use these consistently

Several diagrams and several files work the parallel-decomposition arithmetic. So that the notes
never contradict themselves, **every worked example assumes one 8-core box**:

- `Runtime.getRuntime().availableProcessors()` = **8**
- `ForkJoinPool.getCommonPoolParallelism()` = `availableProcessors() - 1` = **7**, and the
  submitting thread also participates, so the **effective width is 8**
- `LEAF_TARGET` = `7 << 2` = **28**
- over 2,800,000 stake reservations, `suggestTargetSize` = `2_800_000 / 28` = **100,000** exactly,
  giving **28 leaf tasks** of 100,000 elements
- the virtual-thread scheduler's parallelism = `availableProcessors()` = **8**, and its
  `maxPoolSize` = `Integer.max(8, 256)` = **256**, `minRunnable` = `max(8 / 2, 1)` = **4**

If you need a second machine size to make a point, say so explicitly on the page and keep the
8-core figures as the default one.

### 9. `AbstractPipeline`'s two messages — both exist, but only one is reachable from user code

Verified in `AbstractPipeline` at the **jdk-21+35** tag:

```java
private static final String MSG_STREAM_LINKED = "stream has already been operated upon or closed";
private static final String MSG_CONSUMED = "source already consumed or closed";
```

`MSG_STREAM_LINKED` is thrown from eight sites — every public entry point that first checks
`linkedOrConsumed`. `MSG_CONSUMED` is thrown from exactly two: the `else` branch of
`sourceSpliterator(int)` and of `spliterator()`, reached only when **both** `sourceStage
.sourceSpliterator` and `sourceStage.sourceSupplier` are already `null`, i.e. the source has
already been handed out:

```java
else if (sourceStage.sourceSupplier != null) {
    Spliterator<E_OUT> s = (Spliterator<E_OUT>) sourceStage.sourceSupplier.get();
    sourceStage.sourceSupplier = null;
    return s;
}
else {
    throw new IllegalStateException(MSG_CONSUMED);
}
```

Tested on this machine (`javac --release 21`), five candidate reproductions:

```
double terminal                                    -> IllegalStateException: stream has already been operated upon or closed
spliterator twice                                  -> IllegalStateException: stream has already been operated upon or closed
supplier-source: spliterator then traverse twice    -> no throw
supplier-source: sorted().spliterator() twice       -> no throw
supplier-source: trySplit after exhaustion          -> no throw
```

So the honest statement, and the one worth making because it is a mechanism point rather than a
trivia point: **`MSG_CONSUMED` is effectively unreachable from ordinary user code.** The
`linkedOrConsumed` flag is checked on every public entry before the source is ever asked for, so
reuse is always reported as `MSG_STREAM_LINKED`. `MSG_CONSUMED` guards an internal invariant — a
second attempt to take a source that a pipeline already took — not a user mistake. Quote both
strings from the source, name which sites throw which, and say plainly that only the first one is
what you will ever see in a stack trace. Do not fabricate a reproduction for the second.
