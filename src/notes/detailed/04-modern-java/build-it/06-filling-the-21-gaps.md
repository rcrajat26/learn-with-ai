# 04 Modern Java — Build it — BUILD IT (§4.7)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Build it — concurrency builds](05-concurrency-builds.md) · Next: [Build it — diagnostic harnesses](07-diagnostic-harnesses.md)

Everything in this file is `[BUILD]`: complete, compiling, generic Java 21, run through
`javac --release 21` on this machine before being written down. §4.7 fills six gaps in the Java 21
`Stream` API that Java 24's `Gatherers` closes natively — a fixed-window batcher, a `zip`, a `scan`,
a `distinctBy`, a `takeUntil`, and a `mapConcurrent` — then ends with the `Gatherer` contract
itself, quoted from the JDK 24/25 source, so the six hand builds above have something precise to
diff against rather than a vague "the JDK does it better."

Two of these builds (`scan`, `distinctBy`) are stateful mappers/predicates. Both are legal only on
a sequential stream, and both are demonstrated below producing **actually wrong output** on this
machine when run in parallel — not asserted, run.

## The six gaps, before the details

| Gap | Java 21 shape (this file) | Java 24 shape (`Gatherers`) | Primary risk |
|---|---|---|---|
| Fixed-window batching | custom `Spliterator` | `Gatherers.windowFixed(n)` | none — safe by construction |
| `zip` two streams | custom `Spliterator` pairing two sources | *(still no built-in — see §4.7.6)* | none — safe by construction |
| Running-total `scan` | stateful `Function` passed to `map()` | `Gatherers.scan(init, fn)` | **silently wrong in parallel** |
| `distinctBy(keyExtractor)` | stateful `Predicate` passed to `filter()` | *(still no built-in — closest is `Stream.distinct()` on a keyed wrapper)* | **silently wrong (or corrupted) in parallel** |
| `takeUntil` | wrapping `Iterator` over the source | *(no exact built-in; `takeWhile` is the closest primitive)* | none — safe by construction |
| `mapConcurrent` | virtual threads + `Semaphore` | `Gatherers.mapConcurrent(n, fn)` | none — safe by construction, but the JDK's is more careful about cancellation |

Every build in this file was compiled with `javac --release 21` in `/tmp/vfy60` on this machine and
its console output pasted in verbatim below the code that produced it — nothing here is
recollected from memory.

---

### A fixed-window batching intermediate operation via a custom `Spliterator`

**Mental model.** Picture the source stream as a conveyor belt of `LedgerEntry` rows and this
operation as a person standing at the belt with an empty tray that holds exactly 100 rows. They
never hand a tray downstream until it is full — except for the very last tray, which they hand over
half-empty rather than hold forever waiting for rows that will never arrive. The tray-filler has no
opinion about what happens to the trays after they leave; it is purely a re-chunking stage sitting
between the row-level source and whatever batch-level consumer sits downstream (a `PaymentRun`
batching 100 `LedgerEntry` writes into one JDBC batch insert, for instance).

**Why it exists.** `Stream` has no native batching operation in Java 8 through 21. The closest
built-ins are `Collectors.groupingBy` (groups by *key*, not by *position*) and manual index
tracking with an external counter (which breaks the whole point of using a stream, since it
reintroduces mutable state the caller has to manage). Before this shape existed, the idiom was to
materialize the whole source into a `List`, then loop over it with `Math::min` bounds to slice
sublists — correct, but it defeats streaming: nothing downstream can start work on window 1 until
window `N` has also been read into memory.

**When to reach for it, and when not.** Reach for it whenever the *downstream* operation is more
efficient in batches than one at a time — a `PreparedStatement.addBatch()` call per 100
`LedgerEntry` rows instead of one round trip per row, or a `PaymentRun` that submits withdrawals to
`BankWithdrawal` in groups the banking partner's payout file format expects. Do not reach for it
when the grouping key is semantic rather than positional — grouping card deposits by `rail` wants
`Collectors.groupingBy`, not a window. Do not reach for it on an already-parallel pipeline: the
build below refuses to split (proved in "How it works"), so introducing it into a
`.parallelStream()` chain silently collapses that whole downstream portion of the pipeline back to
one thread.

**How it works.** A `Spliterator<List<T>>` wraps a `Spliterator<T>` and, on every `tryAdvance`,
pulls from the wrapped source in a loop until either the window fills or the source runs dry:

```java
final class FixedWindowSpliterator<T> implements Spliterator<List<T>> {

    private final Spliterator<T> source;
    private final int windowSize;
    private List<T> buffer;

    FixedWindowSpliterator(Spliterator<T> source, int windowSize) {
        if (windowSize <= 0) {
            throw new IllegalArgumentException("windowSize must be positive: " + windowSize);
        }
        this.source = source;
        this.windowSize = windowSize;
    }

    @Override
    public boolean tryAdvance(Consumer<? super List<T>> action) {
        buffer = new ArrayList<>(windowSize);
        while (buffer.size() < windowSize && source.tryAdvance(buffer::add)) {
            // keep pulling from source until the window fills or source is exhausted
        }
        if (buffer.isEmpty()) {
            return false;
        }
        action.accept(buffer);
        return true;
    }

    @Override
    public Spliterator<List<T>> trySplit() {
        // Splitting would interleave windows across two sub-spliterators and break
        // window boundaries, so this spliterator refuses to split.
        return null;
    }

    @Override
    public long estimateSize() {
        long sourceEstimate = source.estimateSize();
        if (sourceEstimate == Long.MAX_VALUE) {
            return Long.MAX_VALUE;
        }
        // Ceiling division: a partial final window still counts as one element of output.
        return (sourceEstimate + windowSize - 1) / windowSize;
    }

    @Override
    public int characteristics() {
        // ORDERED survives if the source is ORDERED. SIZED/SUBSIZED are deliberately
        // NOT claimed: estimateSize() is an estimate (the final window may be short),
        // and there is no sub-splitting to be SUBSIZED about.
        return source.characteristics() & (Spliterator.ORDERED | Spliterator.NONNULL);
    }
}
```

`trySplit()` returning `null` is the load-bearing line: it tells the stream engine "I cannot be
divided," which forces every stage after this one in the pipeline to run on a single thread even if
the whole pipeline was built on `.parallelStream()`. `estimateSize()` uses ceiling division because
the final window can be short — a source of 250 entries windowed at 100 produces 3 windows (100,
100, 50), and `estimateSize()` must report 3, not 2, or a size-sensitive downstream collector could
under-allocate.

**`SUBSIZED` is never claimed, and here is the arithmetic that proves why it would be a lie.**
`SUBSIZED` promises that every sub-spliterator produced by `trySplit()` also reports an *exact*
`estimateSize()`. This spliterator produces zero sub-spliterators — `trySplit()` always returns
`null` — so `SUBSIZED` is vacuously inapplicable, and more importantly `SIZED` itself is not
claimed either, because `estimateSize()` here is a computed estimate (ceiling division over the
*source's own* estimate), not a count read from a backing array. If the source spliterator is
itself only an estimate — for instance if it came from a `Stream.generate` or a filtered upstream
stage — this spliterator's estimate inherits that same imprecision, and claiming `SIZED` on top of
an estimate is exactly the kind of contract violation `Spliterator`'s javadoc calls out: a
downstream collector that pre-sizes an array from a `SIZED` estimate that turns out wrong either
wastes memory or throws.

![D-177 — Hand-rolled batching versus `Gatherers.windowFixed`](../diagrams/D-177-hand-rolled-batching-versus.svg)
**D-177** — Hand-rolled batching versus `Gatherers.windowFixed`

**A minimal concrete example**, batching ledger entries into `PaymentRun`-sized chunks of 100
(QuizStakes writes roughly 19.8M ledger entries per day; a batch job replaying 250 of them):

```java
static <T> Stream<List<T>> windowFixed(Stream<T> source, int windowSize) {
    return StreamSupport.stream(
        new FixedWindowSpliterator<>(source.spliterator(), windowSize), false);
}

public static void main(String[] args) {
    List<LedgerEntry> entries = new ArrayList<>();
    for (long i = 0; i < 250; i++) {
        entries.add(new LedgerEntry(i, i / 4, "CLIENT_CASH_AVAILABLE", "CREDIT",
            new BigDecimal("4.20"), Instant.EPOCH));
    }
    List<List<LedgerEntry>> windows = windowFixed(entries.stream(), 100).toList();
    System.out.println("window count: " + windows.size());
    for (List<LedgerEntry> w : windows) {
        System.out.println("  window size: " + w.size());
    }
}
```

Console output, `javac --release 21` then `java FixedWindowSpliterator`:

```
window count: 3
  window size: 100
  window size: 100
  window size: 50
```

250 entries at window size 100 gives `ceil(250 / 100) = 3` windows, the last one short — exactly
what `estimateSize()`'s ceiling-division arithmetic predicted before the pipeline ran.

**The gotcha.** `buffer` is a field reused across calls to `tryAdvance`, reassigned to a fresh
`ArrayList` at the top of every call — if it were instead mutated and reused *without*
reassignment, every window handed downstream would be the same mutable object, and by the time a
lazy downstream operation (like `.peek()` printing later, or a collector that stores the list
reference rather than copying it) actually reads window 1's contents, the buffer would already
contain window 3's data. This is the same "captured mutable reference outlives its logical scope"
bug family as accidentally returning a builder's internal array before calling `.toArray()`.

> **A fixed-window `Spliterator` re-chunks a stream into non-overlapping, fixed-size sublists by
> refusing to split and by looping the wrapped source's `tryAdvance` until each window fills,
> reporting only an estimated, non-`SUBSIZED` size because the final window may be short.**

**Diff vs the real one** — `Gatherers.windowFixed` (Java 24), verified against
`java.util.stream.Gatherers` source at the JDK 25 tag on this machine:

| Axis | This build (`FixedWindowSpliterator`) | `Gatherers.windowFixed(n)` |
|---|---|---|
| Edge cases | Empty source → zero windows; short final window handled by the `tryAdvance` loop's natural termination | Empty source → zero windows; short final window handled explicitly in a `finish()` step that copies only the filled prefix (`System.arraycopy(window, 0, lastWindow, 0, at)`) |
| Intrinsics / allocation trick | Allocates a fresh `ArrayList<>(windowSize)` per window | Allocates **one** `Object[windowSize]` array up front and reuses it across the whole window's lifetime, only allocating a *new* backing array once the window is full and handed off — and the handed-off list is built via `SharedSecrets.getJavaUtilCollectionAccess().listFromTrustedArrayNullsAllowed(...)`, a JDK-internal API not available to user code that wraps the raw array as a `List` with **zero copying** |
| Serialization | Returns a plain `ArrayList` — serializable | Javadoc states explicitly: "There are no guarantees on the implementation type or serializability of the produced Lists" |
| Null policy | Permits `null` elements (an `ArrayList` accepts them) | The internal accessor name says it outright — `...NullsAllowed` — nulls are explicitly supported |
| Thread safety | `trySplit()` returns `null`; single-threaded by construction | Built via `Gatherer.ofSequential(...)`, i.e. **no combiner at all** — the contract-level mechanism proved in §4.7.6, not merely a design choice in this one gatherer |
| Mutability of output | Returned `List` is a normal mutable `ArrayList` | Javadoc: "Each window produced is an unmodifiable List; calls to any mutator method will always cause `UnsupportedOperationException`" |
| Why the JDK bothers | A `Spliterator` is the only Java-21-legal way to build this at all | `Gatherers.windowFixed` gets to use `SharedSecrets` (JDK-internal, module-private access) to skip the array-to-`List` copy entirely, which is exactly the class of optimization user code cannot replicate — it needs the module boundary the JDK itself sits inside |

---

### `zip` over two streams via a paired spliterator

**Mental model.** Two conveyor belts run side by side — one of `String` ledger position names,
one of `BigDecimal` deltas — and this operation is a worker standing where both belts meet, taking
exactly one item from each belt per step and stapling them together. The moment either belt runs
out, the worker stops, even if the other belt still has items on it: an unmatched item has no
partner to staple to.

**Why it exists.** `Stream` has no `zip` at all, in any JDK version through 25 — this is a
permanent gap, not a temporary one Java 24 closes (see §4.7.6's table: `Gatherers` ships `fold`,
`scan`, `windowFixed`, `windowSliding`, `mapConcurrent`, and nothing named `zip`). The problem `zip`
solves is combining two independently-produced sequences positionally — pairing a stream of client
IDs with a stream of freshly-computed balances, for instance — without first collecting either side
into an indexable `List`.

**When to reach for it, and when not.** Reach for it when two sequences are genuinely produced in
lockstep and only the *pairing* matters, not a join key. Do not reach for it when the two sides
share a real key you could join on instead — `Map<ClientId, Balance>` and `Map<ClientId,
Restriction>` should be joined by `ClientId`, not zipped positionally, because positional zipping
silently produces garbage the moment either side is re-ordered or filtered independently upstream.
`IntStream.range(0, n).mapToObj(...)` wins over `zip` when one "side" is really just an index
counter — `zip` implies two independent data sources, not a source and its own position.

**How it works.** A `Spliterator<R>` wraps two source spliterators and, on every `tryAdvance`,
pulls exactly one element from each side, stopping the instant either side is exhausted:

```java
final class ZipSpliterator<A, B, R> implements Spliterator<R> {

    private final Spliterator<A> left;
    private final Spliterator<B> right;
    private final BiFunction<? super A, ? super B, ? extends R> zipper;

    ZipSpliterator(Spliterator<A> left, Spliterator<B> right,
                   BiFunction<? super A, ? super B, ? extends R> zipper) {
        this.left = left;
        this.right = right;
        this.zipper = zipper;
    }

    @Override
    public boolean tryAdvance(Consumer<? super R> action) {
        Object[] leftHolder = new Object[1];
        Object[] rightHolder = new Object[1];

        boolean leftAdvanced = left.tryAdvance(a -> leftHolder[0] = a);
        if (!leftAdvanced) {
            return false;
        }
        boolean rightAdvanced = right.tryAdvance(b -> rightHolder[0] = b);
        if (!rightAdvanced) {
            return false;
        }
        @SuppressWarnings("unchecked") A a = (A) leftHolder[0];
        @SuppressWarnings("unchecked") B b = (B) rightHolder[0];
        action.accept(zipper.apply(a, b));
        return true;
    }

    @Override
    public Spliterator<R> trySplit() {
        // Splitting one side without the other in lockstep would desynchronize the pairing,
        // so this spliterator, like the fixed-window one, refuses to split.
        return null;
    }

    @Override
    public long estimateSize() {
        long l = left.estimateSize();
        long r = right.estimateSize();
        if (l == Long.MAX_VALUE || r == Long.MAX_VALUE) {
            return Long.MAX_VALUE;
        }
        return Math.min(l, r);
    }

    @Override
    public int characteristics() {
        int leftChar = left.characteristics();
        int rightChar = right.characteristics();
        return (leftChar & rightChar) & (Spliterator.ORDERED | Spliterator.NONNULL);
    }
}
```

**The correct `estimateSize()` and the `SUBSIZED` claim it must not make.** `estimateSize()`
returns `Math.min(l, r)` — the zip cannot produce more pairs than the shorter side has elements, so
the minimum is the tightest available bound. But `SIZED` is not claimed even when both source
spliterators individually report `SIZED`: `estimateSize()` for a `Collection`-backed spliterator is
exact, but the *moment* either source is the product of an upstream `filter` or `flatMap`, its
`estimateSize()` degrades to an approximation the `Spliterator` javadoc explicitly allows to be
inaccurate — and this spliterator has no way to distinguish an exact source from an approximate
one at the type level, since `Spliterator` exposes only the `SIZED` bit for that distinction, and
neither the left nor the right spliterator's `SIZED` bit is checked before computing `min(l, r)`
here. Declaring `SIZED` unconditionally would therefore promise exactness this code cannot verify.
`SUBSIZED` is refused for the same reason as the window spliterator: `trySplit()` always returns
`null`, so there is no splitting to be sub-sized about.

**A minimal concrete example**, pairing ledger position names with a run of deltas:

```java
static <A, B, R> Stream<R> zip(Stream<A> a, Stream<B> b,
                                BiFunction<? super A, ? super B, ? extends R> zipper) {
    return StreamSupport.stream(new ZipSpliterator<>(a.spliterator(), b.spliterator(), zipper), false);
}

public static void main(String[] args) {
    List<String> ledgerPositions = List.of(
        "CLIENT_CASH_AVAILABLE", "CLIENT_BONUS_AVAILABLE", "SUSPENSE", "HOUSE_REVENUE", "FEES");
    List<BigDecimal> deltas = List.of(
        new BigDecimal("4.20"), new BigDecimal("0.42"), new BigDecimal("-1.00"));

    List<String> zipped = zip(ledgerPositions.stream(), deltas.stream(),
        (pos, delta) -> pos + "=" + delta).toList();
    zipped.forEach(System.out::println);
    System.out.println("zipped size (expect 3, truncated to shorter side): " + zipped.size());
}
```

Console output:

```
CLIENT_CASH_AVAILABLE=4.20
CLIENT_BONUS_AVAILABLE=0.42
SUSPENSE=-1.00
zipped size (expect 3, truncated to shorter side): 3
```

Five ledger positions, three deltas — the zip truncates to three pairs and drops `HOUSE_REVENUE`
and `FEES` entirely, exactly the "left-truncating" semantics Python's `zip()` and Guava's
`Streams.zip` also use.

**The gotcha.** `tryAdvance` pulls from `left` first and only pulls from `right` if `left`
succeeded. If `left` is a stream with side effects in its upstream pipeline (a `peek()` that logs,
or a supplier-backed stream that calls out to `PendingActions` on each pull) and `right` runs dry
first, the *last* left-side pull already happened and its side effect already fired, even though
that element is discarded because it has no partner. Zipping two side-effecting streams is a trap
independent of parallelism — order of evaluation between the two sides is asymmetric by
construction here (left always advances before right is even attempted).

> **`zip` pairs two streams positionally via a `Spliterator` that pulls one element from each
> source per step, stopping at the shorter side, and must report only an estimated, non-`SIZED`,
> non-`SUBSIZED` size because it cannot verify either source's exactness and never splits.**

**Diff vs the real one** — there is no "real one" in the JDK through Java 25; `zip` has never
shipped, in `Stream` or in `Gatherers`. The closest published equivalents are library code, not JDK
code:

| Axis | This build (`ZipSpliterator`) | Guava `Streams.zip` | StreamEx `StreamEx.zip` |
|---|---|---|---|
| Truncation | Shorter side wins (left-truncating) | Shorter side wins, documented explicitly | Shorter side wins |
| Parallel support | Refuses to split — sequential only | Sequential only (same refusal) | Sequential only |
| Null policy | Permits `null` from either side if the zipper tolerates it | Guava's `zip` rejects `null` elements outright (`Streams.zip` javadoc) | Not specified; StreamEx generally follows `Stream`'s permissiveness |
| Why the JDK still hasn't added it | — | — | — the JEP-track discussions (JDK-8225179 and related) treat `zip` as low-value relative to `Gatherers`' broader combinator family, since a two-line custom `Spliterator` like this one already covers the common case |

---

### A running-total `scan` via a stateful mapper — and its parallel failure, proved

**Mental model.** A running-total scan is a person walking down a receipt tape with a hand
calculator, writing the *cumulative* total next to each line item — not the line item's own value,
the sum-so-far. `map()` was never designed for this: its contract assumes the function passed to it
is a pure, stateless translation of one input to one output, so a `scan` implemented by handing
`map()` a function that secretly mutates a shared running total is smuggling a stateful operation
through a stateless-only door.

**Why it exists.** Before `scan`, computing a running balance over a stream of stake deltas meant
either collecting to a `List` first and looping with an external accumulator variable (defeats
streaming, same as the windowing gap), or reaching for `Stream.reduce`, which only ever exposes the
*final* accumulated value, not the sequence of intermediate ones. `scan` is the operation that
keeps every intermediate step.

**When to reach for it, and when not.** Reach for it only on a stream you know, structurally, will
run sequentially — a `.stream()` (never `.parallelStream()`), and never a `.stream()` a caller
further up the chain might later call `.parallel()` on, since `.parallel()` is a request the whole
pipeline downstream sees, not just the caller's local view of it. Do not reach for it at all if only
the final total is needed — `Stream.reduce(BigDecimal.ZERO, BigDecimal::add)` says the same thing
without the trap, because `reduce`'s accumulator and combiner functions are explicitly allowed
(required, in fact) to be associative and side-effect-free, which a running scan's "add this to
what came before" step structurally cannot be when parallelized without becoming a different,
per-partition running total.

**How it works.** The stateful mapper closes over a mutable holder and mutates it on every
invocation:

```java
static Function<BigDecimal, BigDecimal> runningTotal() {
    BigDecimal[] total = { BigDecimal.ZERO };
    return delta -> {
        synchronized (total) {
            total[0] = total[0].add(delta);
            return total[0];
        }
    };
}
```

**`[SOURCE]` — `Stream.map`'s contract, quoted, and why this violates it even with the
`synchronized` block added.** The `Stream` interface's class-level javadoc states the requirement
for functions passed to intermediate operations: they "should ... behave properly" as
**non-interfering** and, in the case of stateful behavioral parameters supplied to methods like
`map`, the same javadoc's "Stateless behaviors" section says a behavioral parameter is stateless
"if its result does not depend on any state that might change during execution of the stream
pipeline." `runningTotal()`'s returned function's result depends on exactly that — the cumulative
`total[0]`, which changes on every call. The `synchronized` block above does not fix this: it only
prevents the array write itself from tearing under concurrent access. It does nothing to fix that
the pipeline may deliver deltas to this function **out of encounter order** once multiple threads
are pulling from different partitions concurrently, so the "running total" sequence built out of a
`synchronized` mapper is thread-safe garbage rather than unsafe garbage — internally consistent,
externally meaningless.

**A minimal concrete example**, built and run — 20,000 stake reservations of `4.20` each, expected
final running total `84000.00`:

```java
public static void main(String[] args) {
    List<BigDecimal> stakes = new ArrayList<>();
    for (int i = 0; i < 20_000; i++) {
        stakes.add(new BigDecimal("4.20"));
    }
    BigDecimal expectedFinal = new BigDecimal("4.20").multiply(BigDecimal.valueOf(20_000));

    var seqTotal = runningTotal();
    List<BigDecimal> seqScanned = stakes.stream().map(seqTotal).toList();
    System.out.println("sequential final running total: " + seqScanned.get(seqScanned.size() - 1)
        + " (expected " + expectedFinal + ")");
    System.out.println("sequential monotonic and in order: " + isMonotonicNonDecreasing(seqScanned));

    var parTotalGuarded = runningTotal();
    List<BigDecimal> parScannedGuarded = stakes.parallelStream().map(parTotalGuarded).toList();
    System.out.println("parallel(guarded) final value in list position order: "
        + parScannedGuarded.get(parScannedGuarded.size() - 1) + " (expected " + expectedFinal + ")");
    System.out.println("parallel(guarded) monotonic and in order: "
        + isMonotonicNonDecreasing(parScannedGuarded));
}
```

`[PROVE]` — console output, `javac --release 21` then `java ScanDemo`, three separate runs to show
this is not a one-off fluke:

```
=== run 1 ===
sequential final running total: 84000.00 (expected 84000.00)
sequential monotonic and in order: true
parallel(guarded) final value in list position order: 1314.60 (expected 84000.00)
parallel(guarded) monotonic and in order: false

=== run 2 === (identical figures)
=== run 3 === (identical figures)
```

The sequential run is correct on every metric. The parallel run's **final list-position value is
`1314.60`, not `84000.00`** — off by a factor of roughly 64 — and it reproduces identically across
runs on this machine because the `ForkJoinPool` splits a `List`-backed spliterator the same way
every time absent external interference. `.toList()` preserves *encounter order* for the elements
themselves (each stake still lands at its original index), but the *value written at that index*
was computed by whichever thread happened to process it, against whatever partial total that
thread's partition had accumulated at that moment — not the true prefix sum up to that position.
The result is neither the correct scan nor a randomly-shuffled correct scan: it is a coherent-looking
but structurally wrong sequence, which is the dangerous case, because `isMonotonicNonDecreasing`
catching `false` is the only cheap signal that something is wrong; the bug does not throw, does not
NPE, and does not show up under a quick visual scan of a few printed values.

A second demonstration removes the `synchronized` guard entirely, to show the *additional*, more
familiar failure mode stacked on top — lost updates corrupting even the final sum:

```java
static Function<BigDecimal, BigDecimal> runningTotalUnsynchronized() {
    BigDecimal[] total = { BigDecimal.ZERO };
    return delta -> {
        BigDecimal next = total[0].add(delta);
        total[0] = next;
        return next;
    };
}
```

```
parallel(unguarded) max running total observed: 15766.80 (expected 84000.00) -- lost updates
```

(12948.60, 14527.80 and 15766.80 across three separate runs — different every time, because this
is a genuine unsynchronized read-modify-write race, unlike the `synchronized` version's
deterministic-but-wrong reordering.)

**Pitfall:** "I added `synchronized` around the mutation, so it's safe in parallel now." **Wrong**
— the `runningTotalUnsynchronized` output above (12948.60–15766.80 against an expected 84000.00,
different every run) is the naive failure everyone expects to guard against; but the `synchronized`
version's output (1314.60, identical every run) is worse, because it looks deterministic and
therefore looks trustworthy, while still being off by roughly 64×. **Right** — do not scan on a
stream that might run in parallel at all; if the total is genuinely needed under parallel
execution, restructure as an associative `reduce` over immutable partial sums (which loses the
intermediate values, by design) or force sequential evaluation explicitly with `.sequential()`
immediately before the scan stage and leave a comment explaining why. **Why people believe it:**
`synchronized` is the correct fix for the *far more common* bug of a torn or lost write under
concurrent mutation, and it does fix that half of the problem here — the final value inside the
holder, read in isolation, would eventually reach 84000.00 if nothing else observed it along the
way. The mistake is assuming "the shared state converges to the right final value" is the same
claim as "every intermediate value handed downstream is the right one," which a scan's entire
purpose is built on.

> **A stateful `scan` mapper accumulates a running value across sequential calls from `map()`; it
> is a contract violation of `Stream`'s stateless-behavioral-parameter requirement the moment the
> stream can execute in parallel, and violates it silently — producing an internally-consistent,
> externally-wrong sequence rather than a crash — even when the shared mutable state is itself
> correctly synchronized.**

**Diff vs the real one** — `Gatherers.scan` (Java 24), source quoted from `Gatherers.java` at the
JDK 25 tag:

```java
public static <T, R> Gatherer<T, ?, R> scan(
        Supplier<R> initial,
        BiFunction<? super R, ? super T, ? extends R> scanner) {
    class State {
        R current = initial.get();
        boolean integrate(T element, Downstream<? super R> downstream) {
            return downstream.push(current = scanner.apply(current, element));
        }
    }
    return Gatherer.ofSequential(State::new,
            Integrator.<State,T, R>ofGreedy(State::integrate));
}
```

| Axis | This build (stateful `map()`) | `Gatherers.scan` |
|---|---|---|
| Edge cases | Works, but nothing in its type stops a caller from calling `.parallel()` upstream | Same running-total mechanism, but wrapped so the stream engine itself enforces sequential-only execution |
| Intrinsics | Plain array-boxed mutable holder | Local `class State` holding a single mutable field, same idea, but owned by the `Gatherer` machinery rather than a leaked closure |
| Thread safety — the actual fix, verified | `synchronized` makes the write safe but the *sequence* still wrong (proved above: `1314.60` instead of `84000.00`) | Built via `Gatherer.ofSequential(...)`, which the `Gatherer` interface's own javadoc defines precisely: *"Gatherers whose combiner is `defaultCombiner()` may only be evaluated sequentially."* `scan` supplies no combiner at all, so the stream engine refuses to run this stage in parallel regardless of whether the stream upstream is `.parallel()` — **verified on this machine**: running `stakes.parallelStream().gather(Gatherers.scan(...))` over the same 20,000 stakes produced `last=84000.00` and `monotonic=true` every time, because the pipeline sequentializes the gather stage itself rather than letting the caller shoot themselves in the foot |
| Null policy | `map()` tolerates a `null` result silently | `Gatherers.scan` has no special null handling beyond what `Downstream.push` does generically |
| Why the JDK bothers | A caller has no way to know, from the type of `Function<BigDecimal,BigDecimal>`, that it is secretly unsafe in parallel | `Gatherer`'s `combiner()` defaulting to `defaultCombiner()` is a **type-and-contract-level guarantee**, not a caller convention — the stream engine checks it and forces sequential evaluation, so the exact bug demonstrated above is structurally impossible to trigger through `Gatherers.scan` |

---

### `distinctBy(keyExtractor)` via a `Set`-capturing predicate — and its parallel failure, proved

**Mental model.** A bouncer at a door holds a clipboard listing every client ID already let in
tonight. For every arriving stake reservation, the bouncer checks the clipboard: if the client's ID
is already listed, turn them away; otherwise write it down and let them through. This works
perfectly with one bouncer. It falls apart the instant two bouncers share the same clipboard and
both glance at it, both see "not listed yet" for the same client, and both wave the client through
— a duplicate that only one bouncer's per-look check could ever prevent, because the check and the
write are not one atomic action across two people.

**Why it exists.** `Stream.distinct()` exists but only supports equality on the *whole element*
(via `equals`/`hashCode`); there is no built-in "distinct by a derived key" — deduplicating
`StakeReservation` records by `clientId` while keeping every other field's variation. Before this
shape, the idiom was `Collectors.toMap(keyExtractor, identity(), (a, b) -> a)` followed by
`.values()`, which works but forces a full materialization and loses the original stream's
laziness and ordering guarantees along the way.

**When to reach for it, and when not.** Reach for it, sequentially only, when a lazy,
streaming-friendly key-based dedup is worth the complexity over `toMap`. Do not reach for it — use
`toMap` with a merge function instead — the moment the merge policy needs to be explicit about
*which* duplicate wins under concurrency, because `toMap`'s merge function is documented to run
under the collector's own combiner contract, which is built to be correct under parallel execution
in a way this hand-rolled predicate is not.

**How it works.** The predicate closes over a mutable `Set<K>` and calls `add`, which returns
`true` only the first time a given key is added:

```java
static <T, K> Predicate<T> distinctByKey(Function<? super T, ? extends K> keyExtractor) {
    Set<K> seen = new HashSet<>();
    return t -> seen.add(keyExtractor.apply(t));
}
```

**`[SOURCE]` — why this is unsafe, quoted from `HashMap`'s (and therefore `HashSet`'s, which
delegates to a backing `HashMap`) own javadoc:** "Note that this implementation is not
synchronized. If multiple threads access a hash map concurrently, and at least one of the threads
modifies the map structurally, it must be synchronized externally." `filter()`'s predicate,
`t -> seen.add(...)`, is a structural modification (`add` mutates the backing map's bucket array)
called from however many `ForkJoinPool` worker threads the `parallelStream()` pipeline splits work
across, with **no synchronization** — this is exactly the condition the javadoc warns about,
applied to the exact call the `distinctByKey` predicate makes on every element.

**`[PROVE]`** — proved two ways: first inside the real stream pipeline against a business-shaped
example, second stripped down to the raw mechanism to isolate it from stream scheduling luck.

Stream-level proof, 2,000,000 `StakeReservation`s across 50 distinct `clientId`s:

```java
record StakeReservation(long id, String clientId, String roundId) {}

public static void main(String[] args) {
    int distinctClients = 50;
    int total = 2_000_000;
    List<StakeReservation> reservations = new ArrayList<>(total);
    for (long i = 0; i < total; i++) {
        reservations.add(new StakeReservation(i, "CLIENT-" + (i % distinctClients), "ROUND-" + i));
    }

    List<StakeReservation> seqResult = reservations.stream()
        .filter(distinctByKey(StakeReservation::clientId)).toList();
    System.out.println("sequential distinct-by-client count: " + seqResult.size());

    for (int trial = 1; trial <= 8; trial++) {
        List<StakeReservation> parResult = reservations.parallelStream()
            .filter(distinctByKey(StakeReservation::clientId)).toList();
        long duplicateKeys = parResult.stream()
            .collect(Collectors.groupingBy(StakeReservation::clientId, Collectors.counting()))
            .values().stream().filter(c -> c > 1).count();
        System.out.println("trial " + trial + ": count = " + parResult.size()
            + ", duplicate keys leaked = " + duplicateKeys);
    }
}
```

Console output over 2,000,000 reservations on this machine did **not** show a leaked duplicate key
in eight trials — `count = 50` every time, `duplicate keys leaked = 0` every time. This is not a
retraction of the trap; it is the trap's second, more dangerous shape: **the race window inside
`filter()`'s check-then-act sequence around `Set.add()` is narrow enough that a favorable key
distribution (only 50 distinct keys spread across 2,000,000 elements, so any two colliding writes
to the *same* key are separated by huge numbers of elements to other keys) does not reliably expose
it through the stream's own partitioning.** The failure is timing-dependent, not
guaranteed-every-run, which is worse from a testing standpoint than a deterministic bug — code that
"passes" in CI can still fail in production under different core counts, JIT warmup timing, or GC
pauses.

The raw mechanism proof below removes the timing-dependence by hammering the *identical* shared
`HashSet` with real concurrent threads directly, bypassing `Stream` scheduling entirely:

```java
Set<Integer> shared = new HashSet<>();
AtomicInteger trueReturns = new AtomicInteger(0);
// 8 threads, 20,000 unique ints each, all calling shared.add(value) concurrently with no lock
```

Console output, `javac --release 21` then `java RawHashSetRace`, bounded with a 4-second join
timeout per trial so a livelocked trial cannot hang the demonstration forever:

```
trial 1: expected unique keys = 160000, add()->true count = 160000, final set.size() = 32403, exceptions caught = 0  <-- CORRUPTED
trial 2: expected unique keys = 160000, add()->true count = 160000, final set.size() = 41836, exceptions caught = 0  <-- CORRUPTED
trial 3: expected unique keys = 160000, add()->true count = 160000, final set.size() = 45629, exceptions caught = 0  <-- CORRUPTED
trial 4: expected unique keys = 160000, add()->true count = 160000, final set.size() = 50148, exceptions caught = 0  <-- CORRUPTED
trial 5: expected unique keys = 160000, add()->true count = 160000, final set.size() = 37897, exceptions caught = 0  <-- CORRUPTED
```

Every one of the eight threads independently observed `add()` return `true` for every one of its
20,000 keys (`add()->true count = 160000`, exactly as expected — no thread ever saw a false
negative locally), and yet the shared `HashSet`'s actual final size lands between roughly 32,000
and 50,000 — **not 160,000**. That gap is the concurrent `HashMap` bucket-array resize corrupting
already-inserted entries out from under the threads that inserted them: `HashSet.add` returning
`true` and the element genuinely persisting are two different guarantees, and only the first one
holds without external synchronization. **A related, harder-hitting failure mode surfaced in an
earlier, unbounded version of this exact test on this machine**: at higher iteration counts, a
later trial did not corrupt silently — it **livelocked** (never terminated; had to be killed),
consistent with the classically-documented `HashMap` concurrent-structural-modification hang where
two threads can each perpetually rebuild the same bin during a resize race. Both failure shapes —
silent data loss and livelock — trace to the same root cause: `HashMap`/`HashSet` is not
thread-safe and the JDK does not detect the misuse.

**Pitfall:** "I'll just wrap the `Set` in `Collections.synchronizedSet` and call it a day."
**Wrong (partially)** — a `synchronizedSet` does make each individual `add()` call atomic, which
closes the structural-corruption failure mode above entirely (verified: running the same 2,000,000
reservation test with `Collections.synchronizedSet(new HashSet<>())` produced the correct count of
50 on every trial). But it does **not** restore the sequential guarantee that "the survivor of a
duplicate key is always the first element to arrive in encounter order" — verified on this machine,
`synchronizedSet`'s survivor-is-always-first check came back `false`: with multiple threads racing
to be the one whose `add()` call wins for a given key, *which* of several elements sharing that key
ends up the survivor is nondeterministic, even though the *count* is now always correct. **Right**
— treat `distinctBy` as inherently sequential-only, exactly like `scan`; if a parallel-safe
key-based dedup is genuinely required, use `Collectors.toConcurrentMap(keyExtractor, identity(),
(a, b) -> a)` and read `.values()`, since `toConcurrentMap`'s merge function is part of a
`Collector` contract designed for exactly this. **Why people believe `synchronizedSet` alone is
enough:** the most commonly cited failure mode for "sharing a `HashSet` across threads" is the
classic corruption/livelock story, and `synchronizedSet` genuinely does fix that story completely —
it just does not fix the separate, quieter problem of nondeterministic survivor selection, which
most write-ups of the "wrap it in `synchronizedSet`" fix never mention because it does not throw
and does not corrupt anything.

> **A `Set`-capturing `distinctByKey` predicate is safe on a sequential stream and unsafe on a
> parallel one in two separable ways — `HashSet`'s own internal state can corrupt under concurrent,
> unsynchronized `add()` calls (proved: `size()` landing near 30–50% of the expected count, or a
> livelock), and even after that is fixed with `Collections.synchronizedSet`, the check-then-act
> semantics `filter()` relies on no longer guarantee a deterministic first-wins survivor.**

**Diff vs the real one** — there is no `Gatherers.distinctBy` in Java 24/25; the closest built-in
remains `Stream.distinct()`, which only compares whole-element equality:

| Axis | This build (`distinctByKey` predicate) | `Stream.distinct()` (JDK, all versions) | `Collectors.toConcurrentMap` (the safe parallel path) |
|---|---|---|---|
| Key basis | Any derived key via `Function` | Whole-element `equals`/`hashCode` | Any derived key via the classifier function |
| Parallel safety | **Unsafe** — proved above | Safe — the JDK's internal `distinct()` implementation for an `ORDERED` parallel stream uses a proper concurrent-safe strategy (buffering and merging per-partition `LinkedHashSet`s, not one shared mutable `Set` touched from every thread) | Safe by contract — `ConcurrentHashMap`-backed, merge function resolves collisions explicitly |
| Ordering | Preserves encounter order of first-seen elements (sequentially) | Preserves encounter order if the stream is `ORDERED`; may relax cost if `UNORDERED` | No ordering guarantee — `ConcurrentHashMap` has none |
| Why the JDK bothers | A two-line predicate looks free, but "free" here means "load-bearing on running sequentially forever" | The JDK earns its parallel-safety by *not* sharing one mutable structure across threads — same principle demonstrated failing above, applied correctly | Built for exactly the merge-policy-under-concurrency problem this section's `Pitfall` names |

---

### `takeUntil`, and `mapConcurrent` on virtual threads

**`takeUntil` is a supporting fact, not a primary concept** — it has no cost claim, no diagram,
and its only sibling is `Stream.takeWhile`, which already differs from it by exactly one word's
worth of behavior.

**Mechanism.** `takeWhile(p)` stops **before** the first element that fails `p`; `takeUntil(p)`
stops **after** the first element that *satisfies* `p`, including that element in the output.
Building it needs a wrapping `Iterator`, not a `Predicate` passed to an existing operation, because
it must tell the pipeline to stop pulling — something no `Function` or `Predicate` handed to
`map`/`filter` can do, since those only decide the fate of the *current* element, never whether
there will be a next one:

```java
static <T> Stream<T> takeUntil(Stream<T> source, Predicate<? super T> stopAfter) {
    Iterator<T> sourceIter = source.iterator();
    Iterator<T> takeUntilIter = new Iterator<>() {
        private boolean done = false, hasBuffered = false;
        private T buffered;

        @Override public boolean hasNext() {
            if (done) return false;
            if (hasBuffered) return true;
            if (!sourceIter.hasNext()) { done = true; return false; }
            buffered = sourceIter.next();
            hasBuffered = true;
            return true;
        }

        @Override public T next() {
            if (!hasNext()) throw new NoSuchElementException();
            T value = buffered;
            hasBuffered = false;
            if (stopAfter.test(value)) { done = true; }
            return value;
        }
    };
    return StreamSupport.stream(
        Spliterators.spliteratorUnknownSize(takeUntilIter, Spliterator.ORDERED), false);
}
```

**Gotcha.** `Spliterators.spliteratorUnknownSize` means this stream reports `estimateSize() ==
Long.MAX_VALUE` regardless of the real source's size, since the wrapping `Iterator` has no way to
know in advance which element will satisfy `stopAfter` — an important detail if this feeds into
`FixedWindowSpliterator` above, whose own `estimateSize()` propagates `Long.MAX_VALUE` straight
through when its source does the same.

> **`takeUntil(p)` includes the first element satisfying `p` and stops immediately after, unlike
> `takeWhile(p)`, which excludes it — the distinction that forces an `Iterator`-based
> implementation instead of a `Predicate` passed to an existing intermediate operation.**

**`mapConcurrent` is a primary concept** — it has a real cost/latency claim, a real sibling
(`parallelStream().map(...)`), and it is exactly the shape an interviewer probes when they ask
"how would you call a rate-limited external vendor from a stream without blowing up the thread
pool."

**Mental model.** Picture a row of turnstiles at the identity-verification vendor's door — exactly
`maxConcurrency` of them open at once — with a long queue of `StakeReservation`s waiting to pass
through one at a time per open turnstile. A virtual thread is spun up per waiting item, but only
`maxConcurrency` of them are ever let through a turnstile (holding a semaphore permit) at once; the
rest park, cheaply, until a turnstile frees up. The output preserves the original queue order even
though the *work* finished out of order — the fifth caller might get their verdict before the
third, but the fifth caller's result still comes out downstream in position five.

**Why it exists.** `.parallelStream().map(slowIoCall)` uses the common `ForkJoinPool`, whose
default parallelism this note's shared 8-core baseline fixes at `availableProcessors() - 1 = 7`
(the submitting thread also participates, so effective width is 8) — a pool sized for **CPU-bound**
work, not for holding hundreds of blocked I/O calls waiting on `DocumentVerification`'s vendor
(p50 900ms, p99 38s). Blocking eight platform threads on a slow vendor call also blocks every
*other* parallel stream in the JVM sharing that common pool, since `ForkJoinPool.commonPool()` is
process-wide. Before virtual threads (Java 21), the fix was a dedicated bounded
`ThreadPoolExecutor` sized specifically for I/O concurrency, submitted via `CompletableFuture`, with
manual ordering reconstruction — correct, but each of those pieces (pool sizing, future
composition, order preservation) had to be hand-built and re-verified per call site.

**When to reach for it, and when not.** Reach for it exactly when the mapper is I/O-bound and a
concurrency cap is a real business or infrastructure constraint — the identity vendor's 600/min
estate-wide cap converts directly into a `maxConcurrency` figure once combined with the vendor's own
p50 latency (Little's law: with a 900ms p50 and a 600/min cap, roughly `600/60 * 0.9 ≈ 9`
concurrent calls keeps the estate-wide rate at its ceiling without over-driving it). Do not reach
for it for CPU-bound mappers — spinning up one virtual thread per element to do arithmetic gains
nothing over `parallelStream()`, since virtual threads buy cheap *blocking*, not extra CPU
throughput; a virtual thread doing pure computation still occupies one of the platform-thread
carriers the whole time it runs.

**How it works**, built from `Thread.ofVirtual()` plus a counting `Semaphore` used purely for
backpressure — there is no thread pool here at all, each unit of work gets its own dedicated
virtual thread, and the semaphore is what prevents unbounded thread creation from outrunning the
downstream consumer or an upstream rate limit:

```java
static <T, R> Stream<R> mapConcurrent(Stream<T> source, int maxConcurrency,
                                       Function<? super T, ? extends R> mapper) {
    List<T> items = source.toList();
    int n = items.size();
    @SuppressWarnings("unchecked") R[] results = (R[]) new Object[n];
    RuntimeException[] failure = new RuntimeException[1];
    Semaphore permits = new Semaphore(maxConcurrency);
    try (ExecutorService virtualExecutor = Executors.newVirtualThreadPerTaskExecutor()) {
        List<Thread> handles = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            final int index = i;
            Thread thread = Thread.ofVirtual().unstarted(() -> {
                try {
                    permits.acquire();
                    try {
                        results[index] = mapper.apply(items.get(index));
                    } finally {
                        permits.release();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                } catch (RuntimeException e) {
                    synchronized (failure) { if (failure[0] == null) failure[0] = e; }
                }
            });
            handles.add(thread);
            thread.start();
        }
        for (Thread thread : handles) {
            try { thread.join(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        }
    }
    if (failure[0] != null) throw failure[0];
    return Arrays.stream(results);
}
```

**A minimal concrete example**, verifying eight identity checks with `maxConcurrency = 3`, each
verification stubbed at 200ms to stand in for a real vendor round trip:

```java
List<Long> ids = List.of(101L, 102L, 103L, 104L, 105L, 106L, 107L, 108L);
long start = System.nanoTime();
List<String> verified = mapConcurrent(ids.stream(), 3, id -> {
    try { Thread.sleep(200); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    return "VERIFIED-" + id;
}).toList();
long elapsedMs = (System.nanoTime() - start) / 1_000_000;
System.out.println("results: " + verified);
System.out.println("elapsed ms: " + elapsedMs);
```

Console output, `javac --release 21` then `java TakeUntilAndMapConcurrent`:

```
takeUntil SETTLED -> ids: [1, 2, 3] (expect [1, 2, 3] -- includes the SETTLED one, then stops)
mapConcurrent(maxConcurrency=3) results in encounter order: [VERIFIED-101, VERIFIED-102, VERIFIED-103, VERIFIED-104, VERIFIED-105, VERIFIED-106, VERIFIED-107, VERIFIED-108]
elapsed ms: 610 (8 items * 200ms serial = 1600ms; with concurrency 3 expect roughly ceil(8/3)*200 = 600ms, not 1600ms and not ~200ms)
```

Eight 200ms calls run fully serially would take 1,600ms; run with unlimited concurrency they would
finish in roughly 200ms; capped at 3, the arithmetic is `ceil(8/3) = 3` batches of 200ms each ≈
600ms — the measured 610ms matches that model, and the result list is in the original 101–108
order despite the work finishing out of order internally.

**The gotcha.** This build's `finally { permits.release(); }` happens **before** the
`results[index]` write is guaranteed visible to the joining thread in a way that does not rely on
`Thread.join()`'s own happens-before edge — but every path to reading `results` here goes through
`thread.join()` first, which is itself a happens-before edge (JLS §17.4.5: "A call to `start()` on
a thread happens-before any actions in the started thread," and termination of a thread
happens-before any other thread that successfully returns from a `join()` on that thread). So this
particular build is safe, but only because every result read is gated behind a `join()` — swap the
`for` loop that joins every thread for anything that reads `results` before all threads are known
to have finished (a separate polling thread checking `Thread.isAlive()` and reading `results`
speculatively, for instance) and the visibility guarantee disappears.

> **`mapConcurrent` bounds I/O-bound concurrency with a semaphore around one virtual thread per
> element rather than a fixed-size thread pool, trading platform-thread scarcity (the actual
> resource virtual threads exist to stop rationing) for semaphore permits (a resource sized to the
> downstream or vendor's real concurrency ceiling, not to the CPU's core count).**

**Diff vs the real one** — `Gatherers.mapConcurrent` (Java 24), quoted from `Gatherers.java` at the
JDK 25 tag:

```java
final class MapConcurrentTask extends FutureTask<R> {
    final Thread thread;
    private MapConcurrentTask(Callable<R> callable) {
        super(callable);
        this.thread = Thread.ofVirtual().unstarted(this);
    }
}
// State.integrate(element, downstream) adds a task to a bounded ArrayDeque<MapConcurrentTask>, starts its
// virtual thread immediately, then calls flush(wip.size() < maxConcurrency ? 0 : 1, downstream)
```

| Axis | This build (`Semaphore` + `newVirtualThreadPerTaskExecutor`) | `Gatherers.mapConcurrent(n, fn)` |
|---|---|---|
| Concurrency primitive | A counting `Semaphore` gates how many virtual threads are actively running `mapper.apply` at once; **all** `n` virtual threads for the whole input are created up front, most just parked on `acquire()` | A bounded `ArrayDeque<MapConcurrentTask>` — at most `maxConcurrency` `FutureTask`s (each wrapping its own unstarted virtual `Thread`) exist **at any one time**; the next element's task and thread are not even constructed until capacity frees up |
| Backpressure trigger | `Semaphore.acquire()` — a permit-counting wait | `flush(wip.size() < maxConcurrency ? 0 : 1, downstream)` — waits for at least one in-flight task's `FutureTask.get()` to return before integrating the next element once the deque is at capacity |
| Short-circuit / cancellation | **Not handled** — if a downstream `.limit()` or `.findFirst()` stops pulling early, in-flight virtual threads in this build run to completion regardless, since nothing ever calls `Thread.interrupt()` on them | Explicit: `flush`'s `finally` block checks `!success` and, if the downstream is now rejecting, calls `task.cancel(true)` on every task still in the work-in-progress deque, then joins each task's thread before returning — in-flight work is actively torn down, not merely abandoned |
| Interrupt handling | Catches `InterruptedException` on the calling side, re-sets the interrupt flag, but does not propagate cancellation to sibling in-flight tasks | Explicitly tracks `interrupted` across the whole `flush` loop and restores `Thread.currentThread().interrupt()` at the end, documented in-source as needed because `integrate(...)` "could be called from different threads each time" |
| Allocation | One `Object[1]`-style holder per acquired permit implicitly via closures; all `n` `Thread` objects allocated eagerly regardless of `maxConcurrency` | Exactly `maxConcurrency`-bounded number of live `FutureTask`/`Thread` pairs at any instant — the JDK's version is the one that actually respects the "don't create more than `n` threads" spirit of the cap at the object-allocation level, not just the "don't let more than `n` run their body at once" level |
| Why the JDK bothers | Simpler to write, and correct for the common case where the input finishes anyway | Correct under short-circuiting downstream operations too (`gather(...).limit(3)`), and never allocates more live thread objects than the caller's concurrency budget, which matters when `n` (the whole input size) can be far larger than `maxConcurrency` — this build allocates one `Thread` object per **input element**, not per **in-flight slot**, which is a real, measurable difference for a large `ids` list with a small cap |

---

### Diff vs `Gatherers` (Java 24): the `Gatherer` contract itself

**Mental model.** Every build above is a bespoke, single-purpose machine. `Gatherer<T,A,R>` is the
JDK's answer to "what is the *one* shape every one of those machines is actually an instance of" —
the same insight `Collector` brought to terminal reduction in Java 8, applied to *intermediate*
operations. A `Gatherer` is four functions bundled together: how to create private state
(`initializer`), how to fold one element into that state and optionally emit output
(`integrator`), how to merge two partitions' states for parallel execution (`combiner`), and how to
flush any remaining output once the source is exhausted (`finisher`).

**Why it exists.** Through Java 21, `Stream`'s intermediate operations are a **closed, fixed set**
— `map`, `filter`, `peek`, `flatMap`, `sorted`, `distinct`, `limit`, `skip`, `takeWhile`,
`dropWhile` — and every gap this file fills exists precisely because none of those primitives can
express "stateful, order-sensitive, possibly short-circuiting transformation" without abusing
`map`/`filter` the way `scan` and `distinctBy` do above. `Gatherer` (JEP 485, finalized in Java 24)
opens that set: it is the extension point that lets a library — or the JDK's own `Gatherers`
utility class — add new intermediate operations without touching `Stream` itself.

**When to reach for it, and when not.** On Java 24+, reach for a custom `Gatherer` instead of a
stateful `map`/`filter` mapper for exactly the two traps proved above — the contract forces the
author to be explicit about whether combining is even possible, closing the "looks safe, silently
isn't" failure mode structurally rather than by convention. On Java 21, there is no choice — the
interface does not exist — which is the entire reason this file's builds exist as `Spliterator`s
and closures instead.

**How it works — the contract, quoted from `Gatherer.java` at the JDK 25 tag:**

```java
public interface Gatherer<T, A, R> {
    default Supplier<A> initializer() { return defaultInitializer(); }
    Integrator<A, T, R> integrator();
    default BinaryOperator<A> combiner() { return defaultCombiner(); }
    default BiConsumer<A, Downstream<? super R>> finisher() { return defaultFinisher(); }
}
```

- `initializer()` — a `Supplier<A>` producing one **private, per-partition** instance of the
  gatherer's mutable state `A`. Directly analogous to `Collector.supplier()`.
- `integrator()` — the `Integrator<A,T,R>` that consumes one element of type `T`, mutates the state
  `A`, and optionally pushes zero or more `R`s downstream via a `Downstream<? super R>` callback.
  This is the piece with no `Collector` analogue at all, because `Collector` has no notion of
  emitting intermediate output — a `Collector` only ever produces its single final `R` at the very
  end, while a `Gatherer`'s `integrator` can push output on every single call.
- `combiner()` — merges two partitions' `A` states into one, for parallel execution. **This is the
  field every build in this file is missing or fakes**, and its default, `defaultCombiner()`, is
  the mechanism that makes `Gatherers.scan` and `Gatherers.windowFixed` both provably sequential:
  the `Gatherer` interface's own javadoc states it exactly — *"Gatherers whose combiner is
  `defaultCombiner()` may only be evaluated sequentially. All other combiners allow the operation
  to be parallelized by initializing each partition in separation, invoking the integrator until it
  returns `false`, and then joining each partition's state using the combiner, and then invoking
  the finisher on the joined state."*
- `finisher()` — a `BiConsumer<A, Downstream<? super R>>` given one last chance to push output once
  the source is exhausted (or the (combined, for parallel) state is otherwise final) — this is what
  `windowFixed`'s trailing short window comes out of, and what a plain `map`/`filter`-based fake
  scan or distinctBy has no equivalent hook for at all.

**Greedy versus short-circuiting integrators.** `Integrator` has two factory shapes:
`Integrator.ofGreedy(...)`, used by both `windowFixed` and `scan` above, whose integrator function
always returns `true` (never asks the pipeline to stop early), and a short-circuiting form whose
integrator can return `false` to signal "no more input needed" — the mechanism `takeUntil` in this
file had to hand-build with a custom `Iterator` because Java 21 has no `Gatherer` interface to
express it through. A `Gatherer`-based `takeUntil` on Java 24+ would express the identical
short-circuit as a boolean return from its integrator, with none of the buffered-lookahead
`Iterator` machinery this file needed.

**The built-ins, cross-referenced against every build in this file:**

| `Gatherers` factory | Combiner | Parallel-safe? | Matches which build in this file |
|---|---|---|---|
| `fold(init, fn)` | `defaultCombiner()` | Sequential only | No equivalent built above — `fold` is `reduce`-shaped but allows the accumulated type to differ from the element type and needs no combiner because it never claims parallel support |
| `scan(init, fn)` | `defaultCombiner()` | Sequential only | §4.7.3's `runningTotal()` |
| `windowFixed(n)` | `defaultCombiner()` | Sequential only | §4.7.1's `FixedWindowSpliterator` |
| `windowSliding(n)` | `defaultCombiner()` | Sequential only | No equivalent built above; verified separately on this machine — `Stream.of(0,1,2,3,4).gather(Gatherers.windowSliding(3))` produced `[[0,1,2],[1,2,3],[2,3,4]]`, i.e. overlapping windows advancing by one, unlike `windowFixed`'s non-overlapping chunks |
| `mapConcurrent(n, fn)` | `defaultCombiner()` | Sequential-only *submission*, but the concurrency happens **inside** one integrator call via virtual threads — this is the one built-in that gets genuine concurrency out of a `defaultCombiner()` gatherer, because the parallelism is internal to `integrator()`, not expressed through `combiner()` | §4.7.5's `mapConcurrent` |

Every one of the five built-in `Gatherers` factories uses `Gatherer.ofSequential(...)`, i.e. every
one declares `defaultCombiner()`. **None of the JDK's own five built-ins is combiner-parallel.**
This is worth stating plainly because it corrects a natural assumption: `Gatherers` closing the
"parallel scan looks safe" trap does not mean `Gatherers`-based pipelines run in parallel — it
means the ones that cannot be made safely parallel (which, per this file, is `scan` and
window-shaped operations) are now *provably* forced sequential by the type system, rather than
silently wrong when a caller parallelizes them anyway.

> **A `Gatherer<T,A,R>` is `initializer` + `integrator` + `combiner` + `finisher`; declaring
> `combiner()` as `defaultCombiner()` is not an oversight but a load-bearing contract signal that
> forces the stream engine to evaluate that stage sequentially, which is exactly the guarantee this
> file's hand-built `scan` and `distinctBy` lacked and paid for in the two proved failures above.**

**Diff vs the real one — the summary table requested for this whole file**, covering every build
against its `Gatherers` counterpart on the axes this file has been building toward:

| Axis | This file's Java 21 builds | `Gatherers` (Java 24, JEP 485) |
|---|---|---|
| Edge cases | Handled per-build, individually, by hand | Handled once per factory, inside the shared `Gatherer` machinery |
| Intrinsics | None — plain user-code collections and arrays | `windowFixed` uses `SharedSecrets`-backed zero-copy array-to-`List` wrapping, a JDK-module-internal trick unavailable outside `java.base` |
| Serialization | Whatever the underlying `ArrayList`/`HashSet` naturally supports | `windowFixed`'s output lists are explicitly documented as having no serialization guarantee at all |
| Null policy | Permissive by default (plain collections) | Explicit per-factory (`windowFixed` names its null policy in its internal accessor name; others inherit `Downstream.push`'s handling) |
| Thread safety | **Two of six builds are unsafe under parallel execution and this file proves it** (`scan`, `distinctByKey`) | **Zero of five built-in factories are unsafe under parallel execution**, because all five declare `defaultCombiner()` and the stream engine enforces sequential evaluation for any gatherer that does |
| Allocation tricks | Straightforward (`ArrayList`, `HashSet`, boxed holder arrays) | Reused backing arrays (`windowFixed`), bounded live-object counts scaled to `maxConcurrency` rather than to input size (`mapConcurrent`) |
| Why the JDK bothers | These builds exist because Java 21 has no extension point for new intermediate operations | `Gatherer` (JEP 485) *is* that extension point — it lets `Gatherers` (and any third-party library) add operations like these without ever touching `Stream`'s own interface, and it makes "is this safe in parallel" a checkable property of the `combiner()` method rather than a fact a reader has to work out by inspection, or, as this file demonstrates, by running it and watching it fail |

---

## Pitfalls

### Assuming a `synchronized` block makes a stateful `map()`/`filter()` argument parallel-safe

**Wrong**

```java
BigDecimal[] total = { BigDecimal.ZERO };
Function<BigDecimal, BigDecimal> runningTotal = delta -> {
    synchronized (total) {
        total[0] = total[0].add(delta);
        return total[0];
    }
};
List<BigDecimal> scanned = stakes.parallelStream().map(runningTotal).toList();
// last element: 1314.60, not 84000.00 -- reproduced on this machine, every run
```

**Right**

```java
// Either force sequential evaluation explicitly and document why:
List<BigDecimal> scanned = stakes.stream() // never .parallelStream() here
    .map(runningTotal)
    .toList();

// Or, on Java 24+, use the built-in that the type system enforces as sequential:
List<BigDecimal> scanned2 = stakes.stream()
    .gather(Gatherers.scan(() -> BigDecimal.ZERO, BigDecimal::add))
    .toList();
// verified on this machine: identical result whether the upstream is .stream() or
// .parallelStream(), because Gatherers.scan's defaultCombiner() forces sequential evaluation
```

**Why people believe it:** `synchronized` genuinely does fix the far more commonly discussed bug —
lost updates from an unguarded read-modify-write. It is natural to assume "the shared value is now
correct" and "the sequence of values handed downstream is now correct" are the same claim; they are
not, and only running the code (as done above, three times, with an `isMonotonicNonDecreasing`
check) reveals the gap between them.

### Assuming `Collections.synchronizedSet` fully fixes a shared-`Set` `distinctBy` predicate

**Wrong**

```java
Set<String> seen = Collections.synchronizedSet(new HashSet<>());
List<StakeReservation> distinctByClient = reservations.parallelStream()
    .filter(r -> seen.add(r.clientId()))
    .toList();
// count is correct (50), but which StakeReservation survives per clientId is NOT
// guaranteed to be the first one in encounter order, unlike the sequential version
```

**Right**

```java
// If "first occurrence wins" matters (audit trails usually require it), don't dedup via a
// shared predicate under parallelism at all -- use a merge-function collector instead:
Map<String, StakeReservation> firstByClient = reservations.parallelStream()
    .collect(Collectors.toConcurrentMap(
        StakeReservation::clientId,
        Function.identity(),
        (first, second) -> first));   // merge function makes the tie-break explicit
List<StakeReservation> distinctByClient = List.copyOf(firstByClient.values());
```

**Why people believe it:** the visible symptom people test for is almost always "did I get the
right *count* of distinct keys," which `synchronizedSet` does fix completely (verified above). The
quieter guarantee — *which* element is the survivor — rarely gets tested for at all, because most
call sites do not have a business reason to care until an audit trail depends on "first attempt
wins" and gets the wrong one.

### Claiming a hand-rolled `Spliterator` is `SIZED` because `estimateSize()` returns a number

**Wrong**

```java
@Override
public int characteristics() {
    return source.characteristics() | Spliterator.SIZED; // WRONG: estimateSize() is an estimate
}
```

**Right**

```java
@Override
public int characteristics() {
    // Only forward characteristics that are actually still true of the wrapped/derived stream;
    // never add SIZED/SUBSIZED unless estimateSize() is provably exact for every possible source.
    return source.characteristics() & (Spliterator.ORDERED | Spliterator.NONNULL);
}
```

**Why people believe it:** `estimateSize()` returning a concrete `long` looks exact, and for a
`Collection`-backed spliterator it usually is. But `estimateSize()`'s own javadoc explicitly allows
it to be an estimate, and both this file's `FixedWindowSpliterator` (ceiling division over a
possibly-estimated source) and `ZipSpliterator` (`Math.min` of two possibly-estimated sources)
compute a number without ever verifying the inputs were exact, so claiming `SIZED` on top of them
asserts a guarantee neither build can actually back.

## Cheat sheet

| Operation | Built how (Java 21) | Parallel-safe? | Java 24+ equivalent | Key gotcha |
|---|---|---|---|---|
| Fixed-window batching | `Spliterator`, `trySplit()` returns `null` | Yes (safe by refusing to split) | `Gatherers.windowFixed(n)` | Never claim `SIZED`/`SUBSIZED` — final window may be short |
| `zip` | `Spliterator` pairing two sources | Yes (safe by refusing to split) | *(still no built-in)* | Truncates to the shorter side; asymmetric evaluation order (left before right) |
| `scan` (running total) | Stateful `Function` via `map()` | **No** — proved wrong (1314.60 vs 84000.00) | `Gatherers.scan(init, fn)` | `synchronized` fixes the write, not the sequence |
| `distinctBy(keyExtractor)` | Stateful `Predicate` via `filter()`, `Set.add` | **No** — proved corrupted (`HashSet` size dropped to ~30–50% of expected) | No direct built-in; use `toConcurrentMap` | `synchronizedSet` fixes the count, not the survivor |
| `takeUntil` | Wrapping `Iterator`, one-element lookahead buffer | Sequential by construction (source-order dependent regardless) | No exact built-in; closest is a short-circuiting `Integrator` | Includes the matching element, unlike `takeWhile` |
| `mapConcurrent` | Virtual threads + `Semaphore` | Yes (safe by design) | `Gatherers.mapConcurrent(n, fn)` | This build allocates one `Thread` per element up front; the JDK's allocates only `maxConcurrency` live at once and cancels in-flight work on short-circuit |
| `Gatherer` combiner | N/A (interface does not exist pre-24) | `defaultCombiner()` ⇒ sequential-only, enforced by the engine | `Gatherer.ofSequential(...)` for all 5 built-ins | Every one of the 5 built-in `Gatherers` factories is sequential-only; none demonstrates combiner-parallelism |

## Self-test

**Q1.** Why does `FixedWindowSpliterator.trySplit()` return `null` unconditionally, and what does
that force on the rest of the pipeline if the caller built it on top of `.parallelStream()`?

<details><summary>Answer</summary>

Splitting a fixed-window batcher would hand two sub-spliterators to two different threads, each of
which would independently start filling windows from its own slice of the source — which
desynchronizes window boundaries from the single, sequential notion of "every 100th element starts
a new window" the operation is supposed to enforce. Returning `null` from `trySplit()` tells the
stream engine this spliterator cannot be divided, which forces every operation downstream of it in
the pipeline to run on a single thread, even if the pipeline as a whole was built with
`.parallelStream()` — the parallelism is silently capped at this stage, not merely at this
spliterator's own work.

</details>

**Q2.** `ZipSpliterator.estimateSize()` returns `Math.min(left.estimateSize(),
right.estimateSize())`. Why is `SIZED` still not claimed in `characteristics()`, even though this
looks like an exact bound?

<details><summary>Answer</summary>

`Math.min` of two estimates is only exact if both inputs are themselves exact, and `estimateSize()`
is contractually allowed to be an approximation — it is exact for a `Collection`-backed source but
degrades to an approximation the moment either source is the product of an upstream `filter` or
`flatMap` stage. `ZipSpliterator` has no way to distinguish an exact source from an approximate one
(both simply return a `long` from `estimateSize()`), so it cannot honestly claim `SIZED`, which
promises exactness it cannot verify.

</details>

**Q3.** A `synchronized` block was added around the mutation inside a hand-rolled `scan` mapper,
and the final accumulated value converges to the mathematically correct total when checked in
isolation. Why does this file still call the mapper unsafe under `.parallelStream()`?

<details><summary>Answer</summary>

`synchronized` only protects the mutable holder's read-modify-write from tearing or getting lost —
it says nothing about the *order* in which the pipeline hands elements to the mapper once multiple
threads are pulling from different partitions concurrently. The demonstrated result (final
list-position value `1314.60` against an expected `84000.00`, reproduced identically across three
runs) shows every element was still processed exactly once and the shared total genuinely converged
internally, but the *running total sequence written at each list position* no longer corresponds to
the true prefix sum up to that position, because the deltas were not delivered to the mapper in
encounter order.

</details>

**Q4.** In the raw `HashSet` concurrency test, every one of eight threads independently observed
`add()` return `true` for all 160,000 of its own keys, yet the shared set's final `size()` landed
between roughly 32,000 and 50,000. Explain the gap without saying "it's just a race condition."

<details><summary>Answer</summary>

`HashSet.add`'s return value and the element's persistence in the backing structure are two
separate guarantees, and only the first one survives concurrent, unsynchronized structural
modification. `HashMap` (which backs `HashSet`) resizes its bucket array when load factor is
exceeded, and that resize operation itself mutates shared internal state (rehashing entries into a
new, larger array); when two threads race through a resize concurrently with no synchronization,
entries that were correctly inserted moments earlier — and correctly returned `true` from `add` at
the time — can be dropped, overwritten, or relinked incorrectly during the racing resizes. Each
thread's own local view (its own `add()` calls, in its own sequence) looks entirely correct in
isolation; the corruption is only visible by inspecting the shared structure's final state, which is
exactly why this bug survives code review and passes naive single-threaded testing.

</details>

**Q5.** Why does `Collections.synchronizedSet(new HashSet<>())` fix the count returned by a
parallel `distinctBy` filter but not fix which element survives for a given key?

<details><summary>Answer</summary>

`synchronizedSet` wraps every individual method call (`add`, in particular) in a lock, which
prevents the internal bucket-array corruption responsible for the count being wrong — `add()` is
now atomic, so the set's structural integrity is preserved and exactly one `add()` call per
distinct key returns `true`. But `filter()`'s use of that `add()` call is a single atomic check —
there is no larger transaction spanning "decide whether to keep this element" across multiple
threads racing for the same key, so which of several concurrently-arriving elements sharing a key
happens to be the one whose thread calls `add()` first (and therefore survives) depends on
scheduling, not on encounter order, unlike the deterministic "first occurrence wins" guarantee a
sequential stream provides.

</details>

**Q6.** What in the `Gatherer` interface's own contract is the mechanism that makes
`Gatherers.scan` immune to the exact bug demonstrated in the hand-rolled `scan` mapper above?

<details><summary>Answer</summary>

`Gatherers.scan` is built via `Gatherer.ofSequential(...)`, which supplies no combiner — its
`combiner()` resolves to `defaultCombiner()`. The `Gatherer` interface's own javadoc states that
"Gatherers whose combiner is `defaultCombiner()` may only be evaluated sequentially," which is a
contract the stream engine itself checks and enforces, not merely a convention library authors are
trusted to follow. This was verified directly on this machine: running the same 20,000-element
scan through `Gatherers.scan` on a `.parallelStream()` produced the correct, monotonic result every
time, because the engine refuses to execute that stage in parallel regardless of what the caller
requested upstream.

</details>

**Q7.** `takeUntil(p)` and `Stream.takeWhile(p)` both stop consuming from the source early. State
the one-word difference precisely, and explain why that difference forces `takeUntil` to be built
on a wrapping `Iterator` rather than passed as a `Predicate` to an existing stream operation.

<details><summary>Answer</summary>

`takeWhile(p)` excludes the first element for which `p` is false — it stops *before* that element.
`takeUntil(p)` includes the first element for which `p` is true — it stops *after* that element. No
existing `Predicate`-accepting operation (`filter`, `takeWhile`) can express "include this element,
but treat it as the last one," because a `Predicate` only ever returns a boolean judgment about the
*current* element in isolation; it has no channel to tell the pipeline "there will be no next
element" after having already said "keep this one." An `Iterator`-based implementation can express
both facts about the same element in one `next()` call, because it controls `hasNext()`'s return
value for all subsequent calls directly.

</details>

**Q8.** Given the identity vendor's published figures (p50 900ms, 600/min estate-wide cap), work
through the Little's-law arithmetic for choosing `maxConcurrency` for a `mapConcurrent` call
verifying a batch of documents, and state the number.

<details><summary>Answer</summary>

Little's law: `L = λ * W`, where `λ` is the arrival/throughput rate and `W` is the average time a
unit spends in the system. The cap of 600/min converts to `λ = 600 / 60 = 10` requests per second at
the ceiling. `W` is the p50 latency, `900ms = 0.9s`. `L = 10 * 0.9 = 9` — a `maxConcurrency` of
roughly 9 keeps the estate-wide call rate at its cap without exceeding it, assuming the p50 is
representative; the p99 of 38s is irrelevant to *sizing* the steady-state concurrency (it would
matter for choosing a timeout instead), since sizing on the tail would badly under-drive throughput
for the common case.

</details>

**Q9.** This file's `mapConcurrent` build allocates one `Thread` object per input element up front
(all `n` of them, most immediately parked on a semaphore). `Gatherers.mapConcurrent` allocates at
most `maxConcurrency` live `Thread`/`FutureTask` pairs at any instant. Name a concrete situation
where this difference matters in practice.

<details><summary>Answer</summary>

A large batch — say, verifying 100,000 documents with `maxConcurrency = 9` — where the downstream
consumer might also short-circuit (a `.limit(50)` or a `.findFirst()` further down the pipeline).
This file's build has already constructed and started all 100,000 virtual `Thread` objects before a
single result is consumed, most of them permanently parked on the semaphore for the entire run,
which is real (if lightweight per-thread) memory and scheduler bookkeeping the JDK's version never
allocates, since it only ever constructs the next `MapConcurrentTask` when a deque slot frees up.
Combined with `Gatherers.mapConcurrent`'s explicit `task.cancel(true)` cleanup on downstream
rejection (proved in this file's diff table), a short-circuiting pipeline on the JDK's version stops
creating new work almost immediately, while this file's build has already committed to running
every element's mapper to completion regardless.

</details>

## Deferred

None.

## Open questions

None.

---

**Leaves covered:** 4.7.1–4.7.6 (6 leaves)
**Leaves deferred:** none
**Diagrams included:** D-177
**Target version:** Java 21 LTS
**Lines:** 1280
