# 04 Modern Java — Streams — BASICS (§1.6)

**Target version: Java 21 LTS.** | **Part 1 of 5** | [Index](../00-index.md)
Previous: [Streams — basics the model](01-basics-the-model.md) · Next: [Streams — intermediate operations](03-intermediate-operations.md)

A stream has to start somewhere. Everything §1's model describes — the `AbstractPipeline` chain,
the sink-wrapping, the lazy `evaluate(TerminalOp)` — begins with a `Spliterator` that some factory
method built for you. This file is that factory catalogue: every way the JDK hands you a
`Spliterator` wearing a `Stream` interface, what guarantees each one carries into the pipeline
(ordering, size, splittability), which ones own a resource you must close, and the one escape
hatch (`StreamSupport`) for building a source the standard library doesn't provide.

The guarantees matter because they propagate. `IntStream.range`'s `SIZED | SUBSIZED` pair is why
`parallelStream()` over it divides work evenly; `Stream.generate`'s missing `ORDERED` is why
`limit()` on it in parallel is a coin flip; `Stream.iterate`'s missing `SIZED` is why it barely
parallelizes at all despite reporting `ORDERED`. None of this is folklore — every characteristic
claim below is quoted from the `jdk-21+35` source tag, not recalled.

## The source catalogue

Before the detail, the map. Every stream source in the JDK reduces to one of these rows — since
which release it exists, whether it terminates, whether it preserves an encounter order, whether
it knows its size up front, how well it splits for `parallelStream()`, and whether it is holding a
resource that needs a `close()`.

| Source | Since | Finite/Infinite | Ordered | `SIZED`/`SUBSIZED` | Split quality | Needs closing | QuizStakes use |
|---|---|---|---|---|---|---|---|
| `Collection.stream()` / `.parallelStream()` | 8 | Finite | Depends on collection | Depends on collection | Good–excellent | No | `ledgerEntries.stream()` over an in-memory batch |
| `Stream.of(T...)` / `Stream.of(T)` / `Stream.empty()` | 8 | Finite | Yes | Yes/Yes | Excellent (array-backed) | No | wrapping a single `StatusCode` transition |
| `Arrays.stream(T[])` / `(T[], from, to)` / primitive overloads | 8 | Finite | Yes | Yes/Yes | Excellent | No | scanning a fixed `RestrictionKey[]` snapshot |
| `Stream.iterate(seed, next)` | 8 | Infinite | Yes | No/No | Serial in practice | No | never — always needs `limit()` |
| `Stream.iterate(seed, hasNext, next)` | 9 | Finite (self-bounding) | Yes | No/No | Serial in practice | No | walking `PaymentRun` batch windows until a cutoff |
| `Stream.generate(Supplier)` | 8 | Infinite | **No** | No/No | Good (splits by halving estimate) but unordered | No | never for QuizStakes — no legitimate unordered infinite source in this domain |
| `IntStream.range` / `rangeClosed` | 8 | Finite | Yes | Yes/Yes | **Excellent** | No | `IntStream.range(0, 2_800_000)` over a day of stake reservations |
| `Stream.concat(a, b)` | 8 | Finite | Yes | Yes/Yes (if both are) | Degrades sharply when chained | Inherits from `a`/`b` | merging card-deposit and bank-deposit streams for one settlement report |
| `Stream.ofNullable(T)` | 9 | Finite (0 or 1) | Yes | Yes/Yes | Excellent (trivial) | No | `.ofNullable(clientRestrictions.find(clientId))` |
| `Optional.stream()` | 9 | Finite (0 or 1) | Yes | Yes/Yes | Excellent (trivial) | No | `.map(this::findAccount).flatMap(Optional::stream)` |
| `Files.lines(Path[, Charset])` | 8 | Finite | Yes | No/No | Poor (unknown size, IO-bound) | **Yes** | `Files.lines(paymentRunFile)` |
| `Files.walk` / `Files.list` / `Files.find` | 8 | Finite | Yes | No/No | Poor | **Yes** | walking the bank-withdrawal batch drop directory |
| `Files.newDirectoryStream` (via `StreamSupport`) | 7 (NIO.2) | Finite | No | No/No | Poor | **Yes** | — |
| `BufferedReader.lines()` | 8 | Finite | Yes | No/No | Poor | Inherits reader | reading a raw payment-run CSV before parsing |
| `String.lines()` | 11 | Finite | Yes | No/No | Good | No | splitting a multi-line compliance-gate audit note |
| `String.chars()` / `String.codePoints()` | 9 | Finite | Yes | Yes/Yes | Excellent | No | scanning an `IdempotencyKey` for disallowed characters |
| `Pattern.splitAsStream` | 8 | Finite | Yes | No/No | Poor | No | tokenising a `StatusCode` string like `AA-610` |
| `Matcher.results()` | 9 | Finite | Yes | No/No | Poor | No | extracting every `AA-`/`AO-`/`DEP-` code from a log line |
| `Scanner.tokens()` | 9 | Finite | Yes | No/No | Poor | Inherits scanner | — |
| `Random.ints/longs/doubles` | 8 | Infinite or bounded (overload) | No | Depends on overload | Good | No | synthetic load-testing stake amounts |
| `RandomGenerator` stream methods | 17 | Same as above | No | Depends on overload | Good | No | same, on the newer generator hierarchy |
| streaming `Map.entrySet()/keySet()/values()` | 8 | Finite | Depends on `Map` impl | Depends on impl | Good–excellent | No | `ledger.getPositions().entrySet().stream()` |
| `StreamSupport.stream(Spliterator, boolean)` | 8 | Either | Depends on spliterator | Depends on spliterator | Depends on spliterator | Depends on source | the hand-written `ResultSet` bridge |
| `JarFile.stream()` / `ZipFile.stream()` | 8 | Finite | No | No/No | Poor | Inherits archive | — |
| `ServiceLoader.stream()` | 9 | Finite | No | No/No | Poor | No | — |
| `Stream.builder()` | 8 | Finite | Yes | Yes/Yes once built | Excellent once built | No | assembling a variable-length `Movement` list conditionally |

**D-023** — The stream source catalogue.

Two columns deserve a second look before the detail sections unpack them. **Split quality** is not
a vibe — it is a direct read of `SIZED | SUBSIZED`, because the fork/join work-stealing algorithm
that backs `parallelStream()` can only divide a spliterator evenly if it knows the count in
advance; everything else falls back to `trySplit()` heuristics that either buffer batches
(`Spliterators.AbstractSpliterator`, used by `iterate`) or halve an estimate that might be wrong
(`InfiniteSupplyingSpliterator`, used by `generate`). **Needs closing** marks every source built on
top of an OS resource handle — a file descriptor, a directory handle, a `ResultSet` cursor. Miss
the close and you leak the handle for the process lifetime; the language will not remind you,
because `Stream` does not implement `Closeable` the way `InputStream` does — it implements
`AutoCloseable`, and only some sources actually register a close action on it.

---

### `Collection.stream()` and `Collection.parallelStream()` — the default-method escape hatch

`[X-REF 03]` **1.6.1**

**Mechanism.** Before Java 8, adding a `stream()` method to the `Collection` interface would have
broken every one of the thousands of external classes implementing `Collection` without providing
one — a source-incompatible change to the single most widely implemented interface in the
platform. Java 8 solved this at the language level with **default methods**: `Collection` gained

```java
default Stream<E> stream() {
    return StreamSupport.stream(spliterator(), false);
}

default Stream<E> parallelStream() {
    return StreamSupport.stream(spliterator(), true);
}
```

as `default` bodies, so every pre-existing `Collection` implementation inherits a working `stream()`
for free, built from whatever `Spliterator` that implementation supplies — and `ArrayList`,
`HashSet`, `TreeSet`, `ArrayDeque` and friends each override `spliterator()` with a class-specific
one carrying its own characteristics (`ArrayList`'s is `ORDERED | SIZED | SUBSIZED`; `HashSet`'s is
`SIZED | DISTINCT`, no `ORDERED`). The full story of why default methods exist, how they resolve
diamond conflicts against multiple interfaces, and how they're dispatched at the bytecode level
(`invokeinterface`, not `invokevirtual`, verified against the class file) is guide 03's territory —
this paragraph is the interview-sized version: default methods let an interface add a member
without breaking binary or source compatibility for existing implementers, and `stream()`/
`parallelStream()` are the canonical example because they shipped on day one of Java 8 across the
entire collections hierarchy.

**Gotcha.** `parallelStream()` does not mean "runs in parallel." It means "built with
`isParallel = true` on the pipeline," and whether it *actually* forks work depends on the
terminal operation, the source's splittability, and the common pool's state at the time you run
it — three more sub-lessons for `03-intermediate-operations.md` and the internals file.

> **`Collection.stream()`/`parallelStream()`** are `default` methods on `Collection`, added in
> Java 8 specifically so every existing implementer gained streaming for free; both delegate to
> `StreamSupport.stream(spliterator(), <parallel?>)`, so the collection's own `spliterator()`
> override — not the `Stream` API — is what actually determines ordering and split quality.

---

### `Stream.of(T...)`, `Stream.of(T)`, `Stream.empty()`

**1.6.2**

**Mechanism.** `Stream.of(T...)` is varargs sugar over `Arrays.stream(T[])` — the compiler
allocates the backing array and both methods end up wrapping the same array-backed spliterator,
which reports `ORDERED | SIZED | SUBSIZED | IMMUTABLE`. `Stream.of(T)` is a separate single-element
overload that exists purely to avoid the varargs array allocation for the single-value case — an
allocation-avoidance micro-optimization, not a behavioral difference. `Stream.empty()` returns a
cached, shared `Stream` instance backed by `Spliterators.emptySpliterator()`; calling it never
allocates a backing array.

**Gotcha.** `Stream.of((Object[]) null)` throws `NullPointerException` immediately (varargs treats
the null as the array itself, and `Arrays.stream` rejects a null array), while
`Stream.of((Object) null)` produces a one-element stream containing `null` — the two overloads
resolve to genuinely different behavior for the same-looking call, and the compiler's overload
resolution (exact match beats varargs) is what decides which one you got.

> `Stream.of(T...)` is array-backed varargs sugar over `Arrays.stream`; `Stream.of(T)` is a
> single-value overload that skips the array allocation; `Stream.empty()` returns a shared,
> pre-built empty spliterator with no allocation at all.

---

### `Arrays.stream(T[])`, `Arrays.stream(T[], from, to)`, and the primitive overloads

**1.6.3**

**Mechanism.** `Arrays.stream` has an object overload (`Arrays.stream(T[] array)`, and the ranged
`Arrays.stream(T[] array, int startInclusive, int endExclusive)`) plus three primitive overloads —
`int[]`, `long[]`, `double[]` — each returning the matching primitive stream type (`IntStream`,
`LongStream`, `DoubleStream`) rather than a boxed `Stream<Integer>`. Internally every one of these
wraps `Spliterators.spliterator(array, ...)` (or the ranged sibling), which reports
`ORDERED | SIZED | SUBSIZED | IMMUTABLE` because an array's length and contents cannot change
underneath the spliterator by any code path the stream API can see.

**Gotcha.** There is no `Arrays.stream` overload for `char[]`, `short[]`, `byte[]`, `float[]`, or
`boolean[]` — the primitive stream family in `java.util.stream` only has `Int`, `Long`, and
`Double` flavors. To stream a `char[]`, convert it (`new String(charArray).chars()`) or box it
manually; there is no shortcut.

> `Arrays.stream` wraps a `T[]`, an array range, or an `int[]`/`long[]`/`double[]` into a
> `SIZED | SUBSIZED | ORDERED | IMMUTABLE` spliterator — the same guarantee tier as `Stream.of`,
> because both ultimately rest on a fixed-length array.

---

## `Stream.iterate` — the two forms

`[RESEARCH]` **1.6.4**

**Mental model.** `Stream.iterate` is a coroutine, not a collection view: it holds one mutable
slot (`prev`) and a function, and every pull recomputes the next value from the last one it
produced. Picture a single pending calculation frozen mid-loop — `tryAdvance` unfreezes it,
computes one step, and refreezes. There is no backing structure to walk; the "elements" do not
exist until something asks for them.

**Why it exists.** Before Java 8, generating a bounded arithmetic or recursive sequence meant a
hand-written `for` loop building into a `List`, materializing the whole sequence before you could
process any of it — wasteful when you only need a prefix, and impossible when the sequence is
unbounded by construction (a retry backoff schedule, a synthetic id generator). `iterate` lets you
describe the *rule* and let the pipeline pull only as many values as the terminal operation needs.

**When to reach for it, and when not.** Reach for `iterate` when each element is a deterministic
function of the one before it — a recurrence relation, not independent random draws. Reach for
`Stream.generate` instead when elements are independent of each other (each call to a `Supplier`
stands alone — a random id, a clock reading, a queue poll). Reach for `IntStream.range` instead of
either when the sequence is a simple integer count — `range` is fully sized and splits far better
than either infinite-shaped source (see below). Never reach for `iterate(seed, next)` — the
two-argument, unconditionally infinite form — without a `limit()` immediately downstream; there is
no other way to stop it.

**How it works.** Both overloads are implemented as anonymous `Spliterators.AbstractSpliterator`
subclasses. Quoting the `jdk-21+35` source of `java.util.stream.Stream` verbatim:

```java
public static<T> Stream<T> iterate(final T seed, final UnaryOperator<T> f) {
    Objects.requireNonNull(f);
    Spliterator<T> spliterator = new Spliterators.AbstractSpliterator<>(Long.MAX_VALUE,
           Spliterator.ORDERED | Spliterator.IMMUTABLE) {
        T prev;
        boolean started;

        @Override
        public boolean tryAdvance(Consumer<? super T> action) {
            Objects.requireNonNull(action);
            T t;
            if (started)
                t = f.apply(prev);
            else {
                t = seed;
                started = true;
            }
            action.accept(prev = t);
            return true;
        }
    };
    return StreamSupport.stream(spliterator, false);
}
```

Line by line: the size estimate handed to `AbstractSpliterator` is `Long.MAX_VALUE` — the
spliterator is honest that it doesn't know a real bound, which is exactly why `SIZED` is absent
from the characteristics on the next line. `ORDERED | IMMUTABLE` are the only two bits set: it *is*
ordered (each pull is the deterministic successor of the last), but it is not `SIZED`, not
`SUBSIZED`. `tryAdvance` is the entire mechanism — one boolean (`started`) distinguishes "first
pull, emit the seed" from "every subsequent pull, apply `f` to the last value and emit that,"
mutating the closed-over `prev` field each time. There is no `forEachRemaining` override, so the
inherited default just loops `tryAdvance` until it returns `false` — which for this two-argument
form is never, hence the mandatory `limit()`.

The Java 9 three-argument form (JEP-tracked as part of the Java 9 stream enhancements) is the same
shape with a stopping predicate threaded through `tryAdvance`, and it *does* override
`forEachRemaining` for the case where the terminal operation drains the whole stream rather than
short-circuiting:

```java
public static<T> Stream<T> iterate(T seed, Predicate<? super T> hasNext, UnaryOperator<T> next) {
    Objects.requireNonNull(next);
    Objects.requireNonNull(hasNext);
    Spliterator<T> spliterator = new Spliterators.AbstractSpliterator<>(Long.MAX_VALUE,
           Spliterator.ORDERED | Spliterator.IMMUTABLE) {
        T prev;
        boolean started, finished;

        @Override
        public boolean tryAdvance(Consumer<? super T> action) {
            Objects.requireNonNull(action);
            if (finished)
                return false;
            T t;
            if (started)
                t = next.apply(prev);
            else {
                t = seed;
                started = true;
            }
            if (!hasNext.test(t)) {
                prev = null;
                finished = true;
                return false;
            }
            action.accept(prev = t);
            return true;
        }

        @Override
        public void forEachRemaining(Consumer<? super T> action) {
            Objects.requireNonNull(action);
            if (finished)
                return;
            finished = true;
            T t = started ? next.apply(prev) : seed;
            prev = null;
            while (hasNext.test(t)) {
                action.accept(t);
                t = next.apply(t);
            }
        }
    };
    return StreamSupport.stream(spliterator, false);
}
```

The characteristics are identical to the two-argument form — still `ORDERED | IMMUTABLE`, still no
`SIZED` — because the JDK cannot know how many elements satisfy `hasNext` without running the
predicate, so it reports honest ignorance rather than guessing. Read this as the classic
three-argument `for` loop expressed as a stream: `for (T t = seed; hasNext.test(t); t = next.apply(t))`
is exactly what `forEachRemaining` executes. The reason this form needed Java 9 rather than shipping
with Java 8's original `iterate` is that the original signature had no way to express "stop" —
every caller who wanted a bounded sequence had to bolt `limit(n)` onto an infinite `iterate`, which
only works when the bound is a *count*, not a *condition*.

**The diagram.** No diagram is assigned to `iterate` directly — D-024, below, covers `concat`'s
distinct failure mode. The absence is deliberate: `iterate`'s risk is "forgot the terminal
condition," which is a one-line pitfall, not a structural picture.

**Example.** QuizStakes runs bank-withdrawal payouts in `PaymentRun` batches, four settlement
windows per day (Appendix B's four-windows-a-day cadence). Walking every window from the first
payment run of the day until you reach one that has no `nextRun` link is exactly the bounded,
self-terminating shape `iterate(seed, hasNext, next)` was added for:

```java
record PaymentRun(RoundId runId, Instant windowOpenedAt, PaymentRun nextRun) {}

Stream<PaymentRun> settlementWindowsFrom(PaymentRun firstRunOfDay) {
    return Stream.iterate(
        firstRunOfDay,
        run -> run != null,
        PaymentRun::nextRun
    );
}
```

Compare that to the pre-Java-9 idiom, which had to smuggle the same loop through a mutable array
because a lambda cannot reassign a captured local:

```java
Stream<PaymentRun> settlementWindowsFromLegacy(PaymentRun firstRunOfDay) {
    PaymentRun[] cursor = { firstRunOfDay };
    return Stream.iterate(firstRunOfDay, run -> run != null, run -> cursor[0] = run.nextRun())
                 .takeWhile(java.util.Objects::nonNull);
}
```

— which is exactly the workaround the three-argument form made unnecessary.

**Gotcha.** The two-argument `iterate(seed, next)` has **no** stopping condition at all;
`.limit(n)` is not optional, it is the only thing standing between you and an unbounded pipeline
that a short-circuiting terminal op (`findFirst`, `anyMatch`) can still terminate early, but that a
non-short-circuiting one (`forEach`, `collect`) will run forever. `Spliterators.AbstractSpliterator`'s
default `trySplit()` tries to help parallel callers by buffering a batch of elements into an array
and handing that batch off as a separate `ArraySpliterator`, doubling the batch size on each
subsequent split — but because the size estimate is `Long.MAX_VALUE`, this buffering strategy
produces increasingly large batches with no guarantee of even division, which is why the source
catalogue rates `iterate`'s split quality "serial in practice": correctness survives parallel use,
performance rarely benefits from it.

> **`Stream.iterate`** builds an `ORDERED | IMMUTABLE`, non-`SIZED` spliterator around a single
> mutable predecessor slot; the two-argument form runs forever and needs an external `limit()`,
> the three-argument form (Java 9) folds the stopping predicate into `tryAdvance`/`forEachRemaining`
> so the sequence terminates itself, exactly like a three-clause `for` loop.

---

## `Stream.generate` — infinite, unordered, and nondeterministic under `limit()` in parallel

`[TRAP]` **1.6.5**

**Mental model.** Where `iterate` is a recurrence — each value derived from the last — `generate`
is a vending machine: every pull calls the same `Supplier` with no memory of what came before.
Nothing about the sequence is ordered, because nothing about the source claims a "next" relative
to a "previous."

**Why it exists.** `generate` covers the case `iterate` cannot: an infinite sequence whose elements
are independent of each other, not computed from a predecessor — random values, a poll of an
external resource, a clock reading. Before Java 8 this was a `while (true)` loop calling a
producer function directly; `generate` lets that producer feed a stream pipeline so the same
`filter`/`map`/`limit` vocabulary applies to it.

**When to reach for it, and when not.** Reach for `generate` only when elements genuinely do not
depend on each other and you have a `Supplier` already in hand. Never reach for it when you need a
deterministic encounter order preserved under `limit()` in parallel — that is precisely the case
`generate` cannot give you, and `iterate` (sequential-safe) or a `SIZED` source (parallel-safe)
should be used instead. In the QuizStakes domain there is no legitimate production use for an
infinite, order-blind source — every real feed (stake reservations, ledger writes, deposit events)
has an inherent sequence — so treat `generate` here as an interview-mechanics topic, not a pattern
to reach for on this domain's data.

**How it works.** Quoting `java.util.stream.Stream` at `jdk-21+35`:

```java
public static<T> Stream<T> generate(Supplier<? extends T> s) {
    Objects.requireNonNull(s);
    return StreamSupport.stream(
            new StreamSpliterators.InfiniteSupplyingSpliterator.OfRef<>(Long.MAX_VALUE, s), false);
}
```

and the spliterator class it delegates to, from `java.util.stream.StreamSpliterators`:

```java
/**
 * A Spliterator that infinitely supplies elements in no particular order.
 *
 * <p>Splitting divides the estimated size in two and stops when the
 * estimate size is 0.
 *
 * <p>The {@code forEachRemaining} method if invoked will never terminate.
 * The {@code tryAdvance} method always returns true.
 */
...
@Override
public int characteristics() {
    return IMMUTABLE;
}
```

and its split logic:

```java
@Override
public Spliterator<T> trySplit() {
    if (estimate == 0)
        return null;
    return new InfiniteSupplyingSpliterator.OfRef<>(estimate >>>= 1, s);
}
```

Read the class's own javadoc literally: "infinitely supplies elements **in no particular order**."
`characteristics()` returns exactly `IMMUTABLE` — not `ORDERED`, not `SIZED`. This is the direct
source of the trap: a sequential `Stream.generate(supplier).limit(5)` is well-defined (there is
only one thread pulling, so "first five pulls" is unambiguous), but a **parallel**
`Stream.generate(supplier).parallel().limit(5)` is not, because `trySplit()` genuinely does divide
the estimate in half and hand out separate spliterator halves to separate worker threads with no
encounter order tying them together — which five of the infinitely many supplied values end up in
the result, and in what order, depends on how the fork/join scheduler happened to interleave those
workers on that run. `limit()`'s own contract only guarantees "these are the first *n* elements"
when the upstream is ordered; `generate`'s spliterator explicitly opts out of that guarantee.

**Example.** A load-testing harness for the settlement pipeline needs synthetic stake amounts to
throw at a staging `ReserveStake` endpoint — values that don't need to relate to each other, only
to look plausible for QuizStakes' average stake of 4.20:

```java
Stream<Money> syntheticStakeAmounts(RandomGenerator generator) {
    return Stream.generate(() -> Money.of(
            BigDecimal.valueOf(generator.nextDouble(0.50, 20.00))
                      .setScale(2, RoundingMode.HALF_UP),
            Currency.getInstance("GBP")))
        .limit(1_000);
}
```

Run sequentially this deterministically yields the first 1,000 draws from `generator`, in call
order. Add `.parallel()` before `.limit(1_000)` and the *set* of 1,000 values pulled from the
supplier — and their order — is no longer reproducible run to run, because the halving `trySplit()`
hands independent ranges of "how many pulls" to independent threads with no shared ordering.

**Gotcha.**

**Pitfall:** believing `Stream.generate(supplier).parallel().limit(n)` deterministically returns
"the first `n` values the supplier would have produced sequentially." It does not — `generate`'s
spliterator reports no `ORDERED` characteristic, so `limit` under `parallel()` keeps whichever `n`
values happened to arrive from whichever worker finished first, and reruns can disagree with each
other even for a pure, stateless supplier, because the *interleaving* of workers — not the
supplier's own behavior — decides which values survive the cut.

**Right:** if you need `limit` to behave predictably on a `generate`-backed stream, either stay
sequential, or replace `generate` with a `SIZED` source you compute the values from (e.g.
`IntStream.range(0, n).mapToObj(i -> supplier.get())`, which is ordered and sized even though the
supplier itself is stateless), or explicitly document that the sample is unordered and only its
*size*, not its *identity*, is guaranteed.

**Why people believe it:** `iterate().limit(n)` behaves exactly as expected under `parallel()`
because `iterate` *is* `ORDERED`; readers generalize "an infinite source plus `limit` is safe under
parallel" from that one correct case to `generate`, which looks identical at the call site but
carries a different characteristics bitmask underneath.

> **`Stream.generate(Supplier)`** builds an infinite, **unordered** (`IMMUTABLE`-only) spliterator
> that nonetheless supports `trySplit()` by halving its (infinite) size estimate — which is exactly
> why pairing it with `limit()` under `.parallel()` produces a different, non-reproducible subset of
> values on each run.

---

## `IntStream.range` / `rangeClosed` — the best-splitting source in the JDK

`[NUM]` **1.6.6**

**Mental model.** `IntStream.range(a, b)` is not a sequence generator at all under the hood — it is
two integers and an arithmetic rule for cutting the interval `[a, b)` in half, recursively, as many
times as a work-stealing pool asks for a split. There is no element array anywhere; every value is
computed from its position the instant it's needed.

**Why it exists.** Before Java 8, iterating a numeric range meant a `for (int i = a; i < b; i++)`
loop — perfectly fine sequentially, but with no natural way to parallelize the iteration itself
without hand-rolling a fork/join task. `IntStream.range`/`rangeClosed` give the numeric-range
idiom a first-class stream source whose spliterator was designed, from the start, to be the
reference example of clean parallel decomposition.

**When to reach for it, and when not.** Reach for `range`/`rangeClosed` for any counted loop over
an integer domain — array indices, day-of-batch offsets, a fixed count of retries. Prefer it over
`Stream.iterate(0, i -> i + 1).limit(n)`, which produces the same logical sequence but with far
worse split quality (see 1.6.4) — `range` is the sibling that wins whenever the sequence is a
simple arithmetic progression rather than a general recurrence. Do not reach for it when the step
is not `1` or `-1` in the mathematical sense the interval implies, or when the values aren't
integral — for those, `iterate` with an explicit step function is the correct tool despite its
worse splitting.

**How it works.** `range(int, int)` is *exclusive* of the upper bound; `rangeClosed(int, int)` is
*inclusive* — the one-argument-name difference that reproduces `for (i = a; i < b; i++)` versus
`for (i = a; i <= b; i++)` exactly. Both are backed by `Streams.RangeIntSpliterator`, quoted
verbatim from `jdk-21+35`:

```java
@Override
public int characteristics() {
    return Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED |
           Spliterator.IMMUTABLE | Spliterator.NONNULL |
           Spliterator.DISTINCT | Spliterator.SORTED;
}
```

This is a strictly richer bitmask than the syllabus's commonly-quoted "`SIZED | SUBSIZED | ORDERED`"
— the actual source also asserts `IMMUTABLE`, `NONNULL`, `DISTINCT` and `SORTED`, all of which are
true of any contiguous integer range and all of which downstream operations can exploit (a
`distinct()` or `sorted()` stage immediately after a range source can elide its own work entirely
once it sees these bits, because the source already guarantees them). `estimateSize()`:

```java
@Override
public long estimateSize() {
    // Ensure ranges of size > Integer.MAX_VALUE report the correct size
    return ((long) upTo) - from + last;
}
```

computes the count as a `long` specifically so a range wider than `Integer.MAX_VALUE` (possible
since the bounds are `int`s but the arithmetic promotes to `long`) still reports an exact size —
this is the `SIZED` guarantee made concrete, not just claimed. And the split itself:

```java
@Override
public Spliterator.OfInt trySplit() {
    long size = estimateSize();
    return size <= 1
           ? null
           // Left split always has a half-open range
           : new RangeIntSpliterator(from, from = from + splitPoint(size), 0);
}
```

is a clean binary halving of a known-exact interval — no buffering, no batching heuristics, just
arithmetic on `from`/`upTo`. This is the mechanical reason `range`/`rangeClosed` earns "excellent"
in the split-quality column: every `trySplit()` call divides a *known* remaining count exactly in
half, which is the ideal input to fork/join's work-stealing balance, versus `iterate`'s buffering
guesswork over an unknowable `Long.MAX_VALUE` estimate.

**D-023**, above, already places `range`/`rangeClosed` in context against every other source; no
second table is needed here — the point of this section is *why* that one row earns "excellent"
rather than merely stating that it does.

**[NUM]** Work the QuizStakes-scale arithmetic through explicitly, on the one 8-core reference
machine used throughout this note set:

- `Runtime.getRuntime().availableProcessors()` = **8**.
- `ForkJoinPool.commonPool()`'s default parallelism is `availableProcessors() - 1` = **7**, but the
  thread that *submits* the terminal operation also participates in the computation (it does not
  sit idle waiting), so the **effective width is 8**, not 7 — state both halves or the number is
  wrong.
- `AbstractTask.LEAF_TARGET`, quoted from `jdk-21+35`:
  ```java
  private static final int LEAF_TARGET = ForkJoinPool.getCommonPoolParallelism() << 2;
  ```
  `<< 2` is exactly `× 4` — a shift left by two bits multiplies by four — so
  `LEAF_TARGET = 7 << 2 = 28`. The javadoc's own words on `getLeafTarget()` explain the intent:
  "we over-partition, currently to approximately four tasks per processor, which enables others to
  help out if leaf tasks are uneven or some processors are otherwise busy" — over-partitioning by
  4× per core is deliberate load-balancing headroom, not an arbitrary constant.
- `AbstractTask.suggestTargetSize`, same tag:
  ```java
  public static long suggestTargetSize(long sizeEstimate) {
      long est = sizeEstimate / getLeafTarget();
      return est > 0L ? est : 1L;
  }
  ```
  is **floored integer division, clamped to a minimum of `1`** — not "rounded up," which is a
  common misstatement worth correcting explicitly. For `IntStream.range(0, 2_800_000)` — one day
  of QuizStakes stake reservations at 2.8M/day — the target leaf size is
  `2_800_000 / 28 = 100_000` exactly, giving **28 leaf tasks of 100,000 elements each**. Because
  `RangeIntSpliterator.trySplit()` halves an *exact* known size rather than guessing, the fork/join
  decomposition converges on precisely this partition — not an approximation of it.
- `getLeafTarget()` further reads `((ForkJoinWorkerThread) t).getPool().getParallelism()` when the
  calling thread is already inside a `ForkJoinWorkerThread` — the leaf target is **not** pinned to
  the common pool. Submitting the same `IntStream.range(0, 2_800_000).parallel()` pipeline from
  inside a custom `ForkJoinPool` of a different width changes the leaf target to match *that*
  pool's parallelism, which is the mechanism behind the "run the terminal op inside your own pool"
  trick for isolating a stream's parallelism from the shared common pool.

**Example.** A day-end reconciliation job needs to walk all 2.8M of a day's stake-reservation
offsets to bucket them into settlement windows:

```java
long staleReservationCount = IntStream.range(0, 2_800_000)
    .parallel()
    .mapToObj(offset -> stakeReservationLog.at(offset))
    .filter(reservation -> reservation.status() == ReservationStatus.STALE)
    .count();
```

`range`'s `SIZED`/`SUBSIZED` pair is what lets `.parallel()` here actually divide the 2.8M offsets
into the 28 leaf tasks worked out above, rather than falling back to the buffering behavior an
`iterate`-based equivalent would need.

**Gotcha.** `rangeClosed(a, b)` where `a > b` (an already-empty, descending range) returns an
empty stream rather than throwing — the same as `range(a, b)` with `a >= b`. Neither overload
walks backwards; there is no descending-range factory in the JDK, and reversing requires `.boxed()`
plus a manual `sorted(Comparator.reverseOrder())` or building the array yourself.

> **`IntStream.range`/`rangeClosed`** build a `RangeIntSpliterator` reporting
> `ORDERED | SIZED | SUBSIZED | IMMUTABLE | NONNULL | DISTINCT | SORTED` whose `trySplit()` halves
> a known-exact interval — the reason it is the JDK's best-splitting stream source, and the
> reference case every other source's split quality is measured against.

---

## `Stream.concat` — and why chaining it in a loop builds a left-deep tree

`[TRAP]` `[RESEARCH]` **1.6.7**

**Mental model.** A single `Stream.concat(a, b)` call does not merge `a` and `b` into one flat
sequence up front — it wraps their two spliterators inside one `Streams.ConcatSpliterator` that
drains `a` fully, then drains `b`. Call `concat` again on the result — `concat(concat(a, b), c)` —
and you get a `ConcatSpliterator` whose *left* child is itself a `ConcatSpliterator`, not a flat
three-way merge. Do this in a loop and the "tree" of nested spliterators leans entirely to the
left, one level deeper per iteration — exactly a left-deep binary tree, never a balanced one and
never a flat list.

**Why it exists.** Before `concat`, joining two streams meant collecting both into an intermediate
`List` and building a fresh stream over the concatenation of the two lists — an eager
materialization even when the caller only wanted to iterate once and only needed a prefix.
`concat` keeps the join lazy: nothing is copied, the two source spliterators are referenced, not
consumed, until a terminal operation actually walks the combined stream.

**When to reach for it, and when not.** Reach for a single `concat(a, b)` call joining exactly two
streams — that is its designed shape, and it is genuinely lazy and cheap there. Never reach for it
inside a loop accumulating an unbounded number of sources one call at a time; the sibling that
wins there is collecting the sources into a `List<Stream<T>>` first and flat-mapping them in one
flat pass — `list.stream().flatMap(Function.identity())` — which produces one level of nesting
regardless of how many sources you have, not one level *per source*.

**How it works.** Quoting `java.util.stream.Stream` at `jdk-21+35` verbatim:

```java
public static <T> Stream<T> concat(Stream<? extends T> a, Stream<? extends T> b) {
    Objects.requireNonNull(a);
    Objects.requireNonNull(b);

    @SuppressWarnings("unchecked")
    Spliterator<T> split = new Streams.ConcatSpliterator.OfRef<>(
            (Spliterator<T>) a.spliterator(), (Spliterator<T>) b.spliterator());
    Stream<T> stream = StreamSupport.stream(split, a.isParallel() || b.isParallel());
    return stream.onClose(Streams.composedClose(a, b));
}
```

and the method's own javadoc, which states the risk in the JDK's own words: "Use caution when
constructing streams from repeated concatenation. Accessing an element of a deeply concatenated
stream can result in deep call chains, or even `StackOverflowError`." Every line matters: `a` and
`b` are validated non-null, but neither is drained here — only their `Spliterator`s are extracted
and handed to `ConcatSpliterator`. The resulting stream is parallel if *either* input was parallel.
`onClose` chains both inputs' close handlers together via `Streams.composedClose`, which is the
reason `concat`'s row in D-023 says "inherits from `a`/`b`" for closing — if either side is a
resource-backed source like `Files.lines`, closing the concatenated stream closes both.

The `ConcatSpliterator`'s `tryAdvance`/`forEachRemaining` recurse through the left child first:
walking `concat(concat(concat(a, b), c), d)` means calling into the outermost spliterator, which
delegates to *its* left child before touching `d`, which delegates to *its* left child before
touching `c`, and so on — one stack frame per nested `concat` call. A loop that calls
`result = Stream.concat(result, nextChunk)` `n` times builds exactly this: an `n`-deep left-leaning
chain, and traversing it recurses `n` frames deep before it reaches the original left-most source.

**D-024** — `Stream.concat` in a loop builds a left-deep tree.

![D-024 — `Stream.concat` in a loop builds a left-deep tree](../diagrams/D-024-stream-concat-loop-builds.svg)

**D-024** — `Stream.concat` in a loop builds a left-deep tree

**Example.** A settlement report needs one stream over every rail's deposits for a day — card and
bank — and QuizStakes runs bank deposits in batched files, one per settlement window, four windows
a day. Chaining `concat` per window is the trap:

```java
// Builds a 4-deep left-leaning ConcatSpliterator chain — fine at 4, a real trap at scale.
Stream<Movement> allDepositsWrong(List<Stream<Movement>> perWindowBankDeposits,
                                   Stream<Movement> cardDeposits) {
    Stream<Movement> combined = cardDeposits;
    for (Stream<Movement> window : perWindowBankDeposits) {
        combined = Stream.concat(combined, window);
    }
    return combined;
}
```

For four settlement windows this is harmless — four stack frames is nothing. The trap is the shape,
not this specific count: any code that loops `concat` over a data-dependent number of sources (one
`Stream<LedgerEntry>` per hour of a retroactive multi-day reconciliation run, say) turns "harmless
at four" into "`StackOverflowError` at four thousand." The fix flattens instead of nesting:

```java
Stream<Movement> allDepositsRight(List<Stream<Movement>> perWindowBankDeposits,
                                   Stream<Movement> cardDeposits) {
    return Stream.concat(
        cardDeposits,
        perWindowBankDeposits.stream().flatMap(Function.identity())
    );
}
```

`flatMap(Function.identity())` here still recurses once per element as it flattens, but the
recursion depth is bounded by the pipeline's own stage count, not by the number of window streams
being joined — the "levels" in D-024's right-hand side stay flat regardless of how many sources
feed in, because `flatMap` builds one sink, not one nested spliterator per source.

**Gotcha.**

**Pitfall:** accumulating streams with `result = Stream.concat(result, next)` inside any loop whose
iteration count is not a small, fixed, known-safe constant.

**Wrong**
```java
Stream<Movement> combined = Stream.empty();
for (int window = 0; window < settlementWindowCount; window++) {
    combined = Stream.concat(combined, bankDepositWindow(window));
}
combined.forEach(this::record); // StackOverflowError once settlementWindowCount is large enough
```

**Right**
```java
Stream<Movement> combined = IntStream.range(0, settlementWindowCount)
    .mapToObj(this::bankDepositWindow)
    .flatMap(Function.identity());
combined.forEach(this::record); // one flat sink, depth independent of settlementWindowCount
```

**Why people believe it:** `concat` reads, at the call site, exactly like joining two lists with
`addAll` — an operation everyone knows is safe to call repeatedly in a loop because `ArrayList`
just appends into one flat backing array. `Stream.concat` looks identical syntactically but is
building a nested object graph instead of appending into a flat structure, and nothing about the
method signature signals that difference.

> **`Stream.concat(a, b)`** wraps two spliterators in one `Streams.ConcatSpliterator` without
> flattening or copying either input; calling it repeatedly inside a loop nests one
> `ConcatSpliterator` inside the last, producing a left-deep chain whose traversal recursion depth
> equals the number of `concat` calls — the JDK's own javadoc names the resulting risk as
> `StackOverflowError` outright.

---

### `Stream.ofNullable(T)` — a zero-or-one stream, the cleanest null bridge

**1.6.8**

**Mechanism.** Added in Java 9 alongside the three-argument `iterate`, `Stream.ofNullable(T t)`
returns `Stream.empty()` when `t` is `null` and a one-element stream otherwise — internally it is
exactly `t == null ? Stream.empty() : Stream.of(t)`, with the null check folded in so callers don't
have to branch themselves.

**Gotcha.** `ofNullable` is trivially foldable into a `flatMap` step for the extremely common
lookup-then-continue shape — looking up a `ClientRestrictions` row that might not exist and only
continuing the pipeline if it does:

```java
Stream<Restriction> activeRestrictions(Stream<ClientId> clientIds,
                                        Function<ClientId, Restriction> lookup) {
    return clientIds.flatMap(id -> Stream.ofNullable(lookup.apply(id)));
}
```

which quietly drops every client with no restriction on file, rather than requiring a `filter`
step before or a `null`-check inside the downstream operation.

> **`Stream.ofNullable(T)`** returns a zero-element stream for `null` and a one-element stream
> otherwise — a `null`-safe drop-in for `Stream.of(T)` wherever the value might legitimately be
> absent.

---

### `Optional.stream()` — bridging a maybe-value into a pipeline

**1.6.9**

**Mechanism.** Added in Java 9, `Optional<T>.stream()` returns a zero-or-one-element `Stream<T>` —
empty if the `Optional` is empty, one element if present — making `Optional` composable with the
rest of the Streams API instead of requiring an `isPresent()`/`get()` branch to leave the
`Optional` world. The idiom this unlocks, `.map(this::find).flatMap(Optional::stream)`, is the
`Optional` equivalent of the `ofNullable` pattern above — apply a lookup that may fail per element,
then drop the elements where it did.

**Gotcha.** `Optional.stream()` and `Stream.ofNullable` solve the same shape from two different
starting points — reach for `Optional.stream()` when a method already returns `Optional<T>`
(most repository- and finder-style lookups in a well-designed codebase), and `Stream.ofNullable`
when the value in hand is a raw, possibly-`null` reference with no `Optional` wrapper at all.

**Example.**

```java
Stream<Account> findActiveAccounts(Stream<ClientId> clientIds,
                                    Function<ClientId, Optional<Account>> accountLookup) {
    return clientIds.map(accountLookup).flatMap(Optional::stream);
}
```

> **`Optional.stream()`** turns a maybe-value into a zero-or-one-element stream, letting
> `.map(lookupThatReturnsOptional).flatMap(Optional::stream)` express "look up, then keep only the
> hits" without an explicit `isPresent()` branch anywhere in the pipeline.

---

## `Files.lines`, `Files.walk`/`list`/`find`, `Files.newDirectoryStream` — the sources that must be closed

`[TRAP]` **1.6.10**

**Mental model.** Every source in this group is a live cursor over an open OS-level resource — a
file handle for `Files.lines`, a directory-traversal handle for `Files.walk`/`list`/`find` — and
the `Stream` object itself is only the streaming *view* onto that handle. The stream does not own
the file the way a `List` owns its backing array; it is borrowing the file descriptor for as long
as the stream is open, and the JVM will not reclaim that descriptor just because the `Stream`
object becomes unreachable (finalization is not a `close()` substitute, and unlike a `List`, the
descriptor is not garbage-collector-visible memory at all).

**Why it exists.** Reading a file line by line via `BufferedReader` and pushing each line through
manual processing predates streams entirely; `Files.lines(Path)` gave the same access pattern a
lazy, composable `Stream<String>` so filtering, mapping and short-circuiting apply to file content
the same way they apply to an in-memory collection — without reading the whole file into memory
first, which matters directly at QuizStakes' scale (a `paymentRunFile` batching thousands of bank
withdrawals, or a ledger export running into gigabytes).

**When to reach for it, and when not.** Reach for `Files.lines`/`walk`/`list`/`find` specifically
because they're lazy — you want to short-circuit (`findFirst`, `anyMatch`) before reading the whole
file, or you're processing a file too large to hold in memory at once. Do not reach for them when
you're going to consume the entire file's content anyway and want the simplicity of
`Files.readAllLines(Path)` returning a plain `List<String>` that needs no `close()` at all — that
plain, eager alternative is the sibling that wins whenever laziness buys you nothing.

**How it works.** `Files.lines(Path)` and `Files.lines(Path, Charset)` open the file, wrap it in a
`BufferedReader`, and build a stream over `BufferedReader.lines()` (1.6.11) with one addition:
`Files.lines` registers the underlying reader's `close()` as the stream's own close handler via
`Stream.onClose`, so closing the `Stream` closes the file — but *only* if you actually call
`close()` on the stream (directly, or implicitly via try-with-resources, since `Stream` implements
`AutoCloseable`). `Files.walk`, `Files.list`, and `Files.find` are built the same way over a
`DirectoryStream`-backed `Spliterator`, each holding a directory-traversal handle open for the
stream's lifetime. `Files.newDirectoryStream` predates the Streams API (NIO.2, Java 7) and returns
a `DirectoryStream<Path>` — itself `Closeable` — that must be wrapped through
`StreamSupport.stream(directoryStream.spliterator(), false)` if you want stream operators over it;
it is included in the catalogue precisely because it demonstrates that "must be closed" is a
property of the *resource*, not of whether the API happens to hand you a `java.util.stream.Stream`
directly.

None of these characteristics report `SIZED` — the JDK cannot know a file's line count or a
directory's entry count without reading the whole thing, which is also why their split quality is
rated "poor": a work-stealing pool has nothing but IO-bound guesswork to divide the work on.

**Example.** QuizStakes settles bank withdrawals through batched `PaymentRun` files; reading one
to find the first entry that failed reconciliation should never read past that line:

```java
Optional<String> firstFailedLine(Path paymentRunFile) throws IOException {
    try (Stream<String> lines = Files.lines(paymentRunFile)) {
        return lines.filter(line -> line.contains("RECONCILIATION_FAILED"))
                    .findFirst();
    }
}
```

The try-with-resources block is not decoration — without it, the `BufferedReader` `Files.lines`
opened underneath stays open until the JVM exits or the file descriptor limit is exhausted,
whichever comes first, because nothing else in this method's lifecycle will ever call `close()` on
it.

**Gotcha.**

**Pitfall:** treating `Files.lines(Path)` like any other stream factory and letting it go out of
scope without `close()`, because most stream sources (`Collection.stream()`, `IntStream.range`,
`Stream.of`) genuinely need no cleanup and habit generalizes from those to this one.

**Wrong**
```java
Stream<String> lines = Files.lines(paymentRunFile); // file handle opened here
long failureCount = lines.filter(l -> l.contains("RECONCILIATION_FAILED")).count();
// file handle never released — leaked for the life of the process
```

**Right**
```java
long failureCount;
try (Stream<String> lines = Files.lines(paymentRunFile)) {
    failureCount = lines.filter(l -> l.contains("RECONCILIATION_FAILED")).count();
} // file handle closed here, even if filter() or count() throws
```

**Why people believe it:** most of the Streams API's sources are pure in-memory views with nothing
to release, so `Stream` "feels" resource-free by default; the fact that it implements
`AutoCloseable` at all is easy to miss because 90% of streams in ordinary code never need the
`close()` call to matter.

> **`Files.lines`/`walk`/`list`/`find`/`newDirectoryStream`** wrap a live OS file or directory
> handle in a lazy, non-`SIZED` stream and register that handle's release as the stream's
> `onClose` action — the stream must be opened in a try-with-resources block or explicitly closed,
> because nothing else in the JVM will release the underlying handle for you.

---

### `BufferedReader.lines()`, `String.lines()`, `String.chars()`, `String.codePoints()`

`[X-REF 03]` **1.6.11**

**Mechanism.** `BufferedReader.lines()` (Java 8) streams the reader's remaining content one line at
a time, splitting exactly the way `readLine()` does, and — like `Files.lines` — the stream does
**not** close the reader itself; closing the reader is the caller's separate responsibility (this
is the one row in the closing story that is easy to get backwards: `Files.lines` chains the close
for you because it opened the reader itself, but `BufferedReader.lines()` did not open the reader
you handed it, so it has no business closing it on your behalf). `String.lines()` (Java 11) splits
a string on line terminators (`\n`, `\r`, `\r\n`) without the trailing terminator characters and
without a final empty element for a trailing terminator — a direct replacement for the fragile
`split("\\r?\\n")` regex idiom for exactly this purpose, which the guide-03 comparison table covers
in full. `String.chars()` and `String.codePoints()` (Java 9) return `IntStream`s over UTF-16 code
units and Unicode code points respectively — the same distinction that trips up `length()` versus
code-point counting for any string outside the Basic Multilingual Plane, which is guide 03's
territory for the full surrogate-pair mechanics; the interview-sized fact here is that `chars()`
counts UTF-16 units (so a surrogate pair counts as two) while `codePoints()` counts actual Unicode
scalar values (so the same pair counts as one).

**Gotcha.** `BufferedReader.lines()` inherits whatever exception behavior the underlying reader
has — an `IOException` thrown mid-read surfaces from the stream as an `UncheckedIOException`,
because `Stream`'s functional-interface pipeline has no checked-exception channel to propagate a
checked `IOException` through.

> **`BufferedReader.lines()`** streams line-by-line without closing the reader itself;
> **`String.lines()`** (11) is the terminator-aware replacement for splitting on newline regexes;
> **`String.chars()`**/**`codePoints()`** (9) stream UTF-16 units versus Unicode scalar values
> respectively — same string, two different counts whenever a surrogate pair is present.

---

### `Pattern.splitAsStream`, `Matcher.results()`, `Scanner.tokens()`

`[RESEARCH]` **1.6.12**

**Mechanism.** All three are Java 9 additions that gave the regex and tokenizing APIs a streaming
face without changing their underlying scan algorithms. `Pattern.splitAsStream(CharSequence)`
streams the same segments `Pattern.split(CharSequence)` would return as an array, lazily.
`Matcher.results()` streams every non-overlapping match as a `MatchResult` — the streaming
replacement for the classic `while (matcher.find()) { ... }` loop, letting match extraction compose
with `map`/`filter`/`collect` instead of a hand-rolled loop body. `Scanner.tokens()` streams every
token `Scanner.next()` would have returned one at a time, respecting whatever delimiter pattern the
`Scanner` was configured with.

**Gotcha.** None of the three report `SIZED` — a regex match count or a token count is unknowable
without actually scanning, so, like the file-based sources, expect poor parallel split quality and
plan for these as sequential-processing tools.

**Example.** Extracting every status code embedded in a raw compliance audit log line:

```java
List<String> statusCodesIn(String auditLine) {
    return Pattern.compile("[A-Z]{2,3}-\\d{3}")
                   .matcher(auditLine)
                   .results()
                   .map(MatchResult::group)
                   .toList();
}
```

pulled over a line like `"AA-610 recorded, gate AO-400 already cleared"` yields
`["AA-610", "AO-400"]`.

> **`Pattern.splitAsStream`**, **`Matcher.results()`**, and **`Scanner.tokens()`** (all Java 9) give
> the regex-split, regex-match, and tokenizing APIs a lazy `Stream` face over the same scanning
> mechanics they always had — none of them know their element count up front, so none of them split
> well for parallel use.

---

### `Random.ints/longs/doubles` and the Java 17 `RandomGenerator` stream methods

`[RESEARCH]` **1.6.13**

**Mechanism.** `java.util.Random` gained `ints()`, `longs()`, and `doubles()` stream methods in
Java 8, each with a no-argument infinite-stream overload and bounded/sized overloads (a stream
count, or a count plus an inclusive-exclusive range). Java 17's JEP 356 introduced the
`RandomGenerator` interface as the umbrella supertype now implemented by `Random`,
`SecureRandom`, `SplittableRandom`, and every one of the new algorithm implementations that JEP
also added (`Xoshiro256PlusPlus`, `L64X128MixRandom`, and others reachable via
`RandomGeneratorFactory`); `RandomGenerator` declares the same `ints()`/`longs()`/`doubles()`
stream family as default methods, so any generator obtained through
`RandomGeneratorFactory.of(algorithmName).create()` gets the identical streaming surface `Random`
always had, independent of which concrete algorithm backs it.

**Gotcha.** None of these streams are `ORDERED` in any meaningful sense for correctness purposes —
successive draws are independent by design — so treat them the same way as `Stream.generate`:
fine for one-shot sequential consumption, and specifically not a source where `limit()` under
`.parallel()` should be expected to reproduce a specific run's values.

**Example.** Synthetic load-testing values reusing the domain's average stake:

```java
DoubleStream syntheticStakeSizes(RandomGenerator generator, long count) {
    return generator.doubles(count, 0.50, 20.00);
}
```

> **`Random`'s `ints/longs/doubles`** (Java 8) and the **`RandomGenerator`** interface (Java 17,
> JEP 356) expose the same bounded or unbounded stream-of-random-values surface; `RandomGenerator`
> generalizes it across every algorithm the JDK now ships, not just the original `Random` class.

---

### `Map` has no `stream()` — you stream a view

`[TRAP]` `[X-REF 02]` **1.6.14**

**Mechanism.** `Map<K, V>` never gained a `stream()` default method in Java 8, unlike `Collection`
— because `Map` does not extend `Collection` at all (a deliberate design choice dating to Java 2's
collections framework redesign, since a `Map` entry is a pair, not a single element, and retrofitting
`Map` under `Collection` would have forced awkward semantics onto `add`/`remove`). What Java 8 did
give `Map` is three collection-view methods that were already present pre-8 — `entrySet()`,
`keySet()`, `values()` — each of which *does* return a genuine `Collection`, and therefore each of
which *does* have `stream()` available on it. Streaming a `Map` always means streaming one of these
three views, never the map itself. The full story of why `Map` sits outside the `Collection`
hierarchy, how its views are backed live by the map (mutating the map through
`entrySet().iterator().remove()` versus a defensive copy), and `HashMap`'s treeification threshold
that turns an over-populated bucket's linked list into a red-black tree at 8 entries — that
threshold and the surrounding rebalancing mechanics are guide 02's full territory.

**Gotcha.**

**Pitfall:** calling `.stream()` directly on a `Map` reference out of habit built from every other
collection type.

**Wrong**
```java
long positionCount = ledger.getPositions().stream().count(); // does not compile — no stream() on Map
```

**Right**
```java
long positionCount = ledger.getPositions().entrySet().stream().count();
// or, when only the values matter:
long totalCents = ledger.getPositions().values().stream()
    .mapToLong(Money::minorUnits)
    .sum();
```

**Why people believe it:** `List`, `Set`, `Deque`, and every other everyday collection type gained
`stream()` uniformly in Java 8 via `Collection`'s default method, so the muscle memory "any
collection-shaped type has `.stream()`" is correct for everything except the one collection-shaped
type that was never actually a `Collection`.

> **`Map`** has no `stream()` because `Map` does not extend `Collection`; every map is streamed
> through one of its three views — `entrySet()`, `keySet()`, or `values()` — each of which is a
> real `Collection` and inherits `stream()` normally.

---

## `StreamSupport.stream(Spliterator, boolean)` — the general escape hatch

`[NUM]` **1.6.15**

**Mental model.** Every factory method examined so far — `Collection.stream()`,
`IntStream.range`, `Stream.iterate`, `Files.lines` — is, underneath, a thin convenience wrapper
that builds some `Spliterator` and hands it to `StreamSupport.stream(spliterator, parallel)`.
`StreamSupport` is not a separate mechanism from the rest of this file; it is the *single* choke
point every other source in this file funnels through. Reaching for it directly means you are
writing the wrapper the JDK didn't write for you.

**Why it exists.** No factory method can anticipate every resource a program might want to stream
— a `ResultSet` cursor, a message-queue poll loop, a legacy `Iterator`-only API with no
`Iterable` wrapper. `StreamSupport.stream` is the deliberate, public escape hatch: anything that can
be shaped into a `Spliterator` — however specialized — becomes a first-class `Stream` through this
one call, without the JDK needing a bespoke factory for every possible resource shape in existence.

**When to reach for it, and when not.** Reach for it only when no existing factory already covers
the source shape you have — wrapping a legacy `Iterator`, bridging a resource with cursor-style
access (`ResultSet`, a paging API), or adapting a custom data structure that isn't a `Collection`.
Never reach for it to replicate something `Collection.stream()`, `Arrays.stream`, or `Files.lines`
already does — those exist precisely so callers don't have to hand-write a `Spliterator`.

**How it works.** The two-argument overload, `StreamSupport.stream(Spliterator<T> spliterator,
boolean parallel)`, is the one every wrapper method in this file eventually calls — it constructs a
`Stream` whose laziness, characteristics, and split behavior are entirely dictated by whatever
`Spliterator` you hand it; `StreamSupport` itself contributes no guarantees beyond what the
spliterator reports. For sources that only expose a legacy `Iterator` — no `Spliterator`
available at all —
`Spliterators.spliteratorUnknownSize(Iterator<? extends T> iterator, int characteristics)` bridges
the gap: it wraps the `Iterator`'s `hasNext()`/`next()` into a `Spliterator` whose `estimateSize()`
reports `Long.MAX_VALUE` (hence "unknown size") and whose `characteristics()` is exactly the bitmask
you pass in — which means **you** are asserting the guarantees, and if you assert `ORDERED` for an
iterator that doesn't actually preserve one, nothing downstream will catch the lie; it will simply
propagate wrong assumptions to every operator that trusts the bit.

**[NUM]** The two-argument overload's argument order is easy to get backwards under pressure:
`stream(spliterator, parallel)` — the `Spliterator` first, the `boolean` second — matching every
other `StreamSupport`/`Files.lines`-style factory in this file, none of which take the boolean
first. Getting this backwards is a compile error, not a silent bug (the two parameter types don't
overload ambiguously), but it costs a compile cycle to catch, which is worth stating explicitly
since it's the one place in this API surface where argument order carries operational meaning
(sequential vs. parallel from the first call) rather than just being conventional.

**Example.** `ResultSet` has no `stream()` method and no `Spliterator` factory anywhere in
`java.sql` — the JDBC bridge genuinely has to be hand-written, which is exactly the case 1.6.16
names explicitly. A `ResultSet` walking `LedgerEntry` rows for a reconciliation query:

```java
Stream<LedgerEntry> ledgerEntriesFrom(ResultSet resultSet) {
    Spliterator<LedgerEntry> spliterator = new Spliterators.AbstractSpliterator<LedgerEntry>(
            Long.MAX_VALUE, Spliterator.ORDERED | Spliterator.NONNULL) {
        @Override
        public boolean tryAdvance(Consumer<? super LedgerEntry> action) {
            try {
                if (!resultSet.next()) {
                    return false;
                }
                action.accept(new LedgerEntry(
                        new RoundId(UUID.fromString(resultSet.getString("round_id"))),
                        resultSet.getString("position"),
                        Money.of(resultSet.getBigDecimal("amount"), Currency.getInstance("GBP"))
                ));
                return true;
            } catch (SQLException e) {
                throw new UncheckedIOException(new IOException("ledger scan failed", e));
            }
        }
    };
    return StreamSupport.stream(spliterator, false)
            .onClose(() -> {
                try {
                    resultSet.close();
                } catch (SQLException e) {
                    throw new UncheckedIOException(new IOException("failed to close ResultSet", e));
                }
            });
}
```

Every `tryAdvance` call advances the cursor exactly once via `resultSet.next()`; `ORDERED` is
asserted because `ResultSet` traversal follows the query's own result ordering, and `NONNULL`
because the bridge only ever calls `accept` after successfully building a non-null `LedgerEntry`.
The `onClose` registration is deliberate — a hand-rolled bridge over a JDBC resource must chain the
close the same way `Files.lines` does internally, or the `ResultSet` (and the `Statement`,
`Connection` behind it, depending on how the caller structured resource ownership) leaks exactly
like an unclosed `Files.lines` stream would.

**Gotcha.** `Spliterators.spliteratorUnknownSize` and hand-built `AbstractSpliterator` subclasses
both report `estimateSize() == Long.MAX_VALUE`, which is a real value the fork/join framework will
use in its arithmetic (the `suggestTargetSize` division worked through in 1.6.6) — a
`Long.MAX_VALUE`-sized estimate divided by any `LEAF_TARGET` still yields an enormous leaf target,
so a hand-rolled unknown-size spliterator will not meaningfully parallelize even if you call
`.parallel()` on it, for exactly the same underlying reason `iterate`'s split quality is "serial in
practice."

> **`StreamSupport.stream(Spliterator, boolean)`** is the one call every other stream factory
> method in the JDK ultimately delegates to; reach for it directly only when bridging a resource —
> a legacy `Iterator` via `Spliterators.spliteratorUnknownSize`, or a hand-written `Spliterator`
> like a `ResultSet` cursor — that has no existing factory method of its own.

---

### `JarFile.stream()`, `ZipFile.stream()`, `ServiceLoader.stream()`, and `ResultSet`'s missing bridge

`[X-REF 09]` **1.6.16**

**Mechanism.** `JarFile.stream()` and `ZipFile.stream()` (both Java 8) stream the archive's entries
(`JarEntry`/`ZipEntry`) without unpacking any entry's content, and both — like the file-handle
sources above — depend on the archive object itself staying open for the stream's lifetime, since
the entries are metadata views into the still-open archive, not detached copies.
`ServiceLoader.stream()` (Java 9) streams `ServiceLoader.Provider<S>` instances, each wrapping a
lazily-instantiable service implementation — deferring actual instantiation until
`Provider.get()` is called, unlike `ServiceLoader`'s classic `Iterator`, which instantiates eagerly
as it iterates. None of these three report `ORDERED`, because archive-entry order and
service-provider discovery order are both artifacts of underlying file-system or classpath
iteration, not a guarantee either API commits to. `ResultSet` has **no** streaming method at all in
`java.sql` — not `stream()`, not a `Spliterator` factory, nothing — which is precisely why 1.6.15's
hand-written `AbstractSpliterator` bridge exists: the JDBC API predates the Streams API by over a
decade and was never retrofitted with one. The connection-pooling, statement-lifecycle, and
transaction-boundary concerns around that gap — when a `ResultSet`-backed stream must be fully
consumed inside the same transaction, how `Connection` pooling interacts with a lazily-consumed
stream holding a cursor open — are guide 09's full territory; the mechanism-sized fact here is
simply that the bridge must be hand-written, and 1.6.15 already showed the shape of the one you'd
write.

**Gotcha.** A `ServiceLoader.Provider`'s laziness means `.stream().findFirst()` instantiates at
most one provider, while `ServiceLoader.iterator()`'s classic eager iteration would have
constructed the first provider *and* every provider skipped while searching for it, if the
`ServiceLoader` implementation validates providers during discovery — a genuine behavioral
difference between the classic and streamed access paths, not merely a style preference.

> **`JarFile.stream()`**/**`ZipFile.stream()`** (8) stream archive-entry metadata from a still-open
> archive; **`ServiceLoader.stream()`** (9) streams lazily-instantiable provider wrappers instead
> of eagerly-constructed instances; **`ResultSet`** has no stream method of its own at all — every
> JDBC-to-`Stream` bridge in existence is someone's hand-written `Spliterator`, because the JDBC
> API predates `java.util.stream` entirely.

---

### `Stream.builder()` — when it beats collecting into a list first

**1.6.17**

**Mechanism.** `Stream.builder()` returns a `Stream.Builder<T>` — an intermediate, mutable
accumulator with `add(T)` (chainable) and `accept(T)` (`Consumer`-shaped, for method references),
finished off by calling `build()` exactly once, after which the builder itself is spent and adding
further elements throws `IllegalStateException`. Internally it accumulates into a growable
structure (a `SpinedBuffer`, the same backing structure a `collect(Collectors.toList())` uses under
the hood for a sequential stream) and, once built, exposes a `SIZED`/`SUBSIZED`/`ORDERED` stream
over exactly what was added, in add order.

**Gotcha.** `Stream.builder()` earns its keep specifically when the number of elements to include
is conditional and unknown until runtime — assembling a variable-length audit trail of
`Movement`s where some entries are added only if certain gates fired — and the alternative would be
building a `List<Movement>` purely to immediately call `.stream()` on it, an extra, pointless
allocation of a `List` object whose only purpose was to become a stream. When the elements are
already naturally arriving as a `List` from somewhere else, `Stream.builder()` buys nothing —
`list.stream()` is simpler and equally lazy from that point forward.

**Example.**

```java
Stream<Movement> movementsFor(StakeSplit split, boolean chargebackApplies) {
    Stream.Builder<Movement> builder = Stream.builder();
    builder.add(new Movement(CLIENT_BONUS_RESERVED, split.bonusPortion()));
    builder.add(new Movement(CLIENT_CASH_RESERVED, split.cashPortion()));
    if (chargebackApplies) {
        builder.add(new Movement(CHARGEBACK_LOSS, split.cashPortion()));
    }
    return builder.build();
}
```

> **`Stream.builder()`** accumulates a conditionally-sized sequence into a `SpinedBuffer` and
> exposes it as an `ORDERED`/`SIZED` stream on `build()` — it earns its place specifically when
> building a throwaway `List` purely to stream it would be the only alternative.

---

### Any infinite source needs a short-circuiting terminal operation

`[TRAP]` **1.6.18**

**Mechanism.** `Stream.iterate(seed, next)` and `Stream.generate(supplier)` are the two
unconditionally infinite sources in this file — neither has a built-in stopping point. A
short-circuiting intermediate operation (`limit(n)`, `takeWhile(predicate)`) or a
short-circuiting terminal operation (`findFirst`, `findAny`, `anyMatch`) is the *only* thing that
can make a pipeline over one of them terminate; every non-short-circuiting operation —
`forEach`, `collect`, `count`, `reduce`, and critically `sorted()` and `distinct()`, both of which
must see every element before producing any output — will run forever on an infinite source,
because they have no way to know they've seen "enough" without seeing all of it, and "all of it"
never arrives.

**Gotcha.**

**Pitfall:** appending `sorted()` or `distinct()` to an infinite-source pipeline out of habit, the
same way you would on any finite collection stream.

**Wrong**
```java
// Never terminates — sorted() must buffer and see every element before emitting the first one.
Stream.iterate(1, i -> i + 1)
      .sorted()
      .limit(5)
      .forEach(System.out::println);
```

**Right**
```java
// limit() before sorted() bounds the input sorted() has to see.
Stream.iterate(1, i -> i + 1)
      .limit(5)
      .sorted()
      .forEach(System.out::println);
```

**Why people believe it:** operator order on a finite, small collection stream rarely matters for
correctness (only for performance — filtering before sorting touches fewer elements) so the habit
of writing operators "in whatever order reads best" is safe there and silently becomes
catastrophic the moment the source is infinite, since `sorted()`/`distinct()` placed before a
`limit()` changes from "does more work than necessary" to "never completes."

> **Any infinite source** — `Stream.iterate(seed, next)`, `Stream.generate(supplier)` — requires a
> short-circuiting operation (`limit`, `takeWhile`, or a short-circuiting terminal op) somewhere in
> the pipeline; `sorted()` and `distinct()` specifically must buffer the entire input before
> emitting anything, so placing either one before the short-circuit turns "infinite source" into
> "infinite wait."

---

## Pitfalls

### Assuming `Stream.generate(supplier).parallel().limit(n)` is reproducible

**Wrong**
```java
Stream<Money> sample = Stream.generate(() -> Money.of(BigDecimal.valueOf(rng.nextDouble()), GBP))
        .parallel()
        .limit(1_000);
// Different 1,000 values, different order, on every run.
```

**Right**
```java
Stream<Money> sample = IntStream.range(0, 1_000)
        .mapToObj(i -> Money.of(BigDecimal.valueOf(rng.nextDouble()), GBP));
// SIZED source: parallel() and limit() behave predictably because the source is ORDERED.
```

**Why people believe it:** `generate`'s javadoc-visible behavior (infinite supply) looks identical
to `iterate`'s at the call site, and `iterate` genuinely is safe under `parallel().limit(n)` because
it reports `ORDERED`; the difference is a bit in a `characteristics()` method nobody reads before
writing the loop.

### Looping `Stream.concat` to join a data-dependent number of sources

**Wrong**
```java
Stream<Movement> combined = Stream.empty();
for (Stream<Movement> source : sources) {
    combined = Stream.concat(combined, source);
}
```

**Right**
```java
Stream<Movement> combined = sources.stream().flatMap(Function.identity());
```

**Why people believe it:** `concat` reads exactly like `List.addAll` in a loop, which is safe
because `ArrayList` appends into one flat array; `concat` instead nests one spliterator inside the
last, and nothing in the method signature signals the difference.

### Letting a `Files.lines`-backed stream go unclosed

**Wrong**
```java
Stream<String> lines = Files.lines(paymentRunFile);
long failures = lines.filter(l -> l.contains("RECONCILIATION_FAILED")).count();
```

**Right**
```java
long failures;
try (Stream<String> lines = Files.lines(paymentRunFile)) {
    failures = lines.filter(l -> l.contains("RECONCILIATION_FAILED")).count();
}
```

**Why people believe it:** most stream sources need no cleanup at all, so the habit of never
calling `close()` on a `Stream` is correct 90% of the time — until the source is a file handle.

### Calling `.stream()` directly on a `Map`

**Wrong**
```java
long count = ledger.getPositions().stream().count(); // does not compile
```

**Right**
```java
long count = ledger.getPositions().entrySet().stream().count();
```

**Why people believe it:** every other collection type in daily use gained `.stream()` uniformly in
Java 8; `Map` looks collection-shaped but was never actually a `Collection`.

### Appending `sorted()`/`distinct()` to an infinite-source pipeline before the short-circuit

**Wrong**
```java
Stream.generate(() -> pollNextEvent()).distinct().limit(10).forEach(this::record);
```

**Right**
```java
Stream.generate(() -> pollNextEvent()).limit(10).distinct().forEach(this::record);
```

**Why people believe it:** operator order rarely affects correctness on a small finite collection
stream, only performance; the same reordering habit turns catastrophic the instant the source
never ends.

## Cheat sheet

| Source | Since | Characteristics (verified) | Split quality | Needs closing |
|---|---|---|---|---|
| `Collection.stream()`/`parallelStream()` | 8 | inherited from the collection's own `spliterator()` | good–excellent | No |
| `Stream.of`/`empty` | 8 | `ORDERED\|SIZED\|SUBSIZED\|IMMUTABLE` (array-backed) or shared empty | excellent | No |
| `Arrays.stream` (+ `int`/`long`/`double`) | 8 | `ORDERED\|SIZED\|SUBSIZED\|IMMUTABLE` | excellent | No |
| `Stream.iterate(seed, next)` | 8 | `ORDERED\|IMMUTABLE`, no `SIZED` | serial in practice | No |
| `Stream.iterate(seed, hasNext, next)` | 9 | `ORDERED\|IMMUTABLE`, no `SIZED` | serial in practice | No |
| `Stream.generate` | 8 | `IMMUTABLE` only — **not** `ORDERED` | good (halving) but unordered | No |
| `IntStream.range`/`rangeClosed` | 8 | `ORDERED\|SIZED\|SUBSIZED\|IMMUTABLE\|NONNULL\|DISTINCT\|SORTED` | excellent | No |
| `Stream.concat` | 8 | inherits from `a`,`b`; risk is recursion depth, not the bitmask | degrades when chained | inherits |
| `Stream.ofNullable` | 9 | `ORDERED\|SIZED\|SUBSIZED` (0 or 1 element) | excellent | No |
| `Optional.stream()` | 9 | same as `ofNullable` | excellent | No |
| `Files.lines`/`walk`/`list`/`find` | 8 | `ORDERED`, no `SIZED` | poor | **Yes** |
| `BufferedReader.lines()` | 8 | `ORDERED`, no `SIZED` | poor | reader's job, not the stream's |
| `String.lines()` | 11 | `ORDERED` | good | No |
| `String.chars()`/`codePoints()` | 9 | `ORDERED\|SIZED\|SUBSIZED` | excellent | No |
| `Pattern.splitAsStream`/`Matcher.results`/`Scanner.tokens` | 9 | `ORDERED`, no `SIZED` | poor | scanner variant: yes |
| `Random`/`RandomGenerator` streams | 8 / 17 | not `ORDERED` in a meaningful sense | good | No |
| `Map` views (`entrySet`/`keySet`/`values`) | 8 | inherited from the map implementation | good–excellent | No |
| `StreamSupport.stream(Spliterator, boolean)` | 8 | whatever the spliterator asserts | whatever the spliterator asserts | whatever you register |
| `JarFile.stream()`/`ZipFile.stream()` | 8 | not `ORDERED`, no `SIZED` | poor | inherits archive |
| `ServiceLoader.stream()` | 9 | not `ORDERED`, no `SIZED`, lazy `Provider` | poor | No |
| `ResultSet` | — | no built-in bridge; hand-write one via `StreamSupport` | as hand-written | as hand-written |
| `Stream.builder()` | 8 | `ORDERED\|SIZED\|SUBSIZED` once `build()`'d | excellent once built | No |

**Arithmetic to remember:** `LEAF_TARGET = commonPoolParallelism << 2` (×4); `suggestTargetSize` is
floored division clamped to a minimum of `1`, never rounded up; on the 8-core reference machine,
`2_800_000 / 28 = 100_000` per leaf, 28 leaves.

## Self-test

**Q1.** Why does `IntStream.range(0, 2_800_000).parallel()` split far more evenly than
`Stream.iterate(0, i -> i + 1).limit(2_800_000).parallel()`, even though both describe the same
logical sequence of integers?

<details><summary>Answer</summary>

`IntStream.range`'s `RangeIntSpliterator` reports `SIZED | SUBSIZED` and its `trySplit()` halves a
*known-exact* remaining count via simple arithmetic on `from`/`upTo` — every split is exactly even.
`Stream.iterate`'s spliterator is a `Spliterators.AbstractSpliterator` seeded with an
`estimateSize()` of `Long.MAX_VALUE` and no `SIZED` bit; its default `trySplit()` can only buffer a
guessed batch of elements into an array and hand that batch off, with no way to know in advance how
that batch relates to the total 2.8M the `limit()` will eventually cut off at. The `range` version
splits on exact knowledge; the `iterate` version splits on a guess over an unknowable total.

</details>

**Q2.** A `Stream.generate(this::pollNextEvent).parallel().limit(20).forEach(this::process)` call
processes a different set of 20 events on every run, even though `pollNextEvent()` is
deterministic given the queue's actual contents. Why, and what is the fix if a deterministic
sample is required?

<details><summary>Answer</summary>

`StreamSpliterators.InfiniteSupplyingSpliterator.characteristics()` returns exactly `IMMUTABLE` —
no `ORDERED` bit — so `limit(20)` under `.parallel()` has no encounter order to preserve and simply
keeps whichever 20 values arrived from whichever worker thread happened to finish its share first,
which varies with fork/join scheduling on each run. The fix is either to drop `.parallel()`
(sequential `generate` + `limit` is well-defined, one thread pulling in call order) or to replace
`generate` with a `SIZED`, `ORDERED` source — e.g. draining exactly 20 items into a list first, then
streaming the list.

</details>

**Q3.** What specifically does `Stream.concat`'s own javadoc warn about, and what is the mechanical
reason a loop of `concat` calls triggers it while an equivalent `flatMap` over the same sources does
not?

<details><summary>Answer</summary>

The javadoc says, verbatim: "Accessing an element of a deeply concatenated stream can result in
deep call chains, or even `StackOverflowError`." Each `Stream.concat(a, b)` call wraps `a` and `b`'s
spliterators inside one `Streams.ConcatSpliterator`; chaining `concat` calls in a loop nests a new
`ConcatSpliterator` around the previous result each time, producing a left-deep tree whose traversal
recursion depth equals the number of `concat` calls. `sources.stream().flatMap(Function.identity())`
instead builds one flat sink over all the sources — the recursion depth stays bounded by the
pipeline's own stage count, independent of how many sources are being merged.

</details>

**Q4.** Why does `ledger.getPositions().stream()` fail to compile, and what are the three ways to
fix it?

<details><summary>Answer</summary>

`Map<K, V>` does not extend `Collection<E>` — it never gained the `Collection` interface's
`stream()` default method in Java 8, because a map's entries are pairs, not single elements, and
`Map` was deliberately kept outside the `Collection` hierarchy since Java 2. The fix is to stream
one of `Map`'s three collection-view methods instead: `.entrySet().stream()` for key-value pairs,
`.keySet().stream()` for keys alone, or `.values().stream()` for values alone — each of those
return values genuinely is a `Collection` and inherits `stream()` normally.

</details>

**Q5.** `Files.lines(paymentRunFile)` and `BufferedReader.lines()` both stream file content
line-by-line, but only one of the two automatically closes the underlying reader when the stream is
closed. Which one, and why does the other not?

<details><summary>Answer</summary>

`Files.lines(Path)` closes the reader automatically, because `Files.lines` is the one that *opened*
the `BufferedReader` in the first place — it registers that reader's `close()` as the stream's own
`onClose` action, so calling `close()` on the returned stream (directly or via try-with-resources)
closes the file. `BufferedReader.lines()`, called on a reader the caller already owns and opened
themselves, has no such registration — the method didn't create the resource, so it has no business
deciding when to release it; closing that reader remains the caller's separate responsibility.

</details>

**Q6.** Why is `suggestTargetSize`'s division described as "floored, clamped to a minimum of 1" and
not "rounded up," and what would change in the 8-core, 2.8M-element worked example if it *were*
rounded up instead?

<details><summary>Answer</summary>

The verified `jdk-21+35` source is `long est = sizeEstimate / getLeafTarget(); return est > 0L ? est
: 1L;` — integer division truncates toward zero (floors for positive operands) and the only
adjustment made is bumping a result of exactly `0` up to `1`, never rounding a fractional quotient
upward. In the worked example, `2_800_000 / 28` divides evenly to `100_000` with no remainder, so
flooring versus rounding up produces the identical answer here — but for a size that does not
divide evenly by `LEAF_TARGET`, flooring would produce a leaf size one smaller (and therefore one
extra leaf task, with the remainder absorbed into the last task) than rounding up would, which is
exactly the kind of off-by-one that matters when reasoning precisely about task counts.

</details>

**Q7.** What would `Stream.of((Object[]) null)` and `Stream.of((Object) null)` each do, and why do
they differ?

<details><summary>Answer</summary>

`Stream.of((Object[]) null)` throws `NullPointerException` immediately, because the varargs
overload treats the cast expression as the backing array itself, and the underlying
`Arrays.stream(T[])` call rejects a null array outright. `Stream.of((Object) null)` instead resolves
to the single-element overload `Stream.of(T)` (the cast forces overload resolution away from the
varargs form) and produces a genuine one-element stream whose sole element is `null` — the two
calls look nearly identical but resolve to different overloads with materially different behavior.

</details>

**Q8.** A method returns `Stream.iterate(seed, next)` — the unconditionally infinite, two-argument
form — and a caller pipes it through `.sorted()` before `.limit(10)`. What happens, and how would
the three-argument `iterate(seed, hasNext, next)` overload change the analysis if it were used
instead with an always-true `hasNext`?

<details><summary>Answer</summary>

The pipeline never terminates in either case. `sorted()` is a stateful, non-short-circuiting
operation that must buffer and see every upstream element before it can emit the first (smallest)
one downstream; placed before `limit(10)` on an infinite source, it waits forever for "every
element" to arrive, and `limit(10)` never gets a chance to cut anything off because no element ever
reaches it. Using the three-argument `iterate` with an always-true `hasNext` predicate does not
change this — `hasNext` never returning `false` makes it behave identically to the two-argument
form for this purpose. The fix in either case is operator order: `.limit(10).sorted()`, bounding the
input before the buffering operation runs.

</details>

**Q9.** Name the one row in the source catalogue where the underlying resource must be closed but
the object returned to the caller is not itself a `java.util.stream.Stream`, and explain why it's
still listed here.

<details><summary>Answer</summary>

`Files.newDirectoryStream(Path)` (NIO.2, Java 7) returns a `DirectoryStream<Path>` — a `Closeable`
that predates the Streams API entirely and is not a `java.util.stream.Stream` on its own. It only
becomes a genuine `Stream` if the caller explicitly wraps it via
`StreamSupport.stream(directoryStream.spliterator(), false)`. It belongs in this catalogue because
it demonstrates that "needs closing" is a property of the underlying resource (a directory handle),
not of whether the JDK happened to hand back a `java.util.stream.Stream` type — the same handle-
management discipline applies whether or not the Streams API is even involved yet.

</details>

**Q10.** Why does the hand-written `ResultSet`-to-`Stream` bridge in this file assert `ORDERED |
NONNULL` on its spliterator rather than, say, `SIZED`?

<details><summary>Answer</summary>

`ORDERED` is asserted because the bridge's `tryAdvance` walks the `ResultSet` strictly via
successive `resultSet.next()` calls, which follows the query's own result ordering — a real,
defensible guarantee. `NONNULL` is asserted because `tryAdvance` only ever calls `accept` after
successfully constructing a non-null `LedgerEntry` from the current row; it never emits a null
element. `SIZED` is deliberately **not** asserted because a `ResultSet` does not expose its row
count up front (some JDBC drivers require scrolling to the end to even find out, which would defeat
the point of a lazy cursor-backed bridge) — asserting `SIZED` without a real, cheap way to compute
`estimateSize()` accurately would be lying to every downstream operation that trusts the bit, which
is precisely the discipline 1.6.15's gotcha warns against.

</details>

## Deferred

None.

---

**Leaves covered:** 1.6.1–1.6.18 (18 leaves)
**Leaves deferred:** none
**Diagrams included:** D-023, D-024
**Target version:** Java 21 LTS
**Lines:** 1567
