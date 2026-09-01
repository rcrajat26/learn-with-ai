# ArrayList — 15 Interoperation: Streams and Concurrency

**Target version: Java 21.** | [Map](00-map.md)
Assumes: iteration and fail-fast (file 08), and the alternatives (file 13).
Previous: [14-version-history.md](14-version-history.md) · Next: [16-prove-it.md](16-prove-it.md)

### `ArrayListSpliterator` and its characteristics

Picture a **cuttable range**: a `[index, fence)` window over the backing
array that can hand back its front half and keep the back half, repeatedly,
until pieces are small enough to give one to each thread. That cuttability is
why the type exists — `Iterator` has no way to say "give me half of yourself."

Before `Spliterator` (Java 8), parallelising a collection meant each type
invented its own partitioning, or callers fell back to `toArray()` plus
manual chunking. `Spliterator` standardised the protocol — `tryAdvance`,
`trySplit`, `forEachRemaining`, `estimateSize`, `characteristics` — so
`Stream` could drive any source uniformly.

`ArrayList` overrides `spliterator()`; without it, `Collection`'s default
wraps the plain `Iterator` in a generic `Spliterators.IteratorSpliterator`,
which can split but must guess at size and cannot pre-size a `toList`
collector. The override is a pure constant-factor win, never a complexity
change — there is no case where it loses.

Real source, `ArrayList.java` lines 1615–1723:

```java
public int characteristics() {
    return Spliterator.ORDERED | Spliterator.SIZED | Spliterator.SUBSIZED;
}
```

Each flag is a promise a pipeline stage exploits: **`SIZED`** — exact
remaining count, so `toList()`/collectors allocate once instead of growing
(file 02's `grow` cost) across repeated inserts. **`SUBSIZED`** — every split
is itself `SIZED`, so fork-join decides splitting depth by arithmetic, no
probing pass needed. **`ORDERED`** — encounter order is defined, which
constrains reordering and is why `findFirst()` means something specific.

Absent flags matter too: no `DISTINCT` (duplicates legal), no `SORTED` (no
intrinsic order), no `IMMUTABLE`/`CONCURRENT` — the list can change under the
spliterator, which is why it must instead be **late-binding** and fail-fast.
Late-binding: `getFence()` is called lazily, only once traversal starts, so a
`stream()` built and left unconsumed takes no snapshot.

```java
List<String> ids = new ArrayList<>(List.of("DEP-301", "DEP-400"));
Stream<String> s = ids.stream();   // no read yet
ids.add("BDP-100");
s.forEach(System.out::println);    // DEP-301, DEP-400, BDP-100 — sees the add
```

The comodification check runs once, at the **end** of a `forEachRemaining`
batch, not per element — the same batching trade file 08 showed for
`Itr.forEachRemaining`: one branch amortised over the whole batch, at the
cost of only detecting interference after it happened.

**Insight:** `characteristics()` is not documentation — `Collectors` and
`StreamOpFlag` branch on the returned bitmask at runtime to choose allocation
and merge strategy.

**Pitfall:** treating a `Stream` over an `ArrayList` as a snapshot. Late
binding means it is not — it is a live view until a terminal operation runs.

> A `Spliterator` is a splittable, late-binding cursor that additionally
> declares, via a characteristics bitmask, which structural guarantees a
> traversal algorithm may rely on.

### Why an array-backed list parallelises well

Parallel stream execution is fork-join recursion over a binary split tree. An
array-backed spliterator finds the exact midpoint of any range in O(1), so the
tree is balanced by construction — no pass is needed to discover the middle.

Before `Spliterator`, parallelising a collection meant materialising it into
an array (`toArray()`) purely to get index-splittable structure — an O(n)
copy paid up front regardless of source. `trySplit()` lets an already
array-backed source skip that copy.

```java
public ArrayListSpliterator trySplit() {
    int hi = getFence(), lo = index, mid = (lo + hi) >>> 1;
    return (lo >= mid) ? null :
        new ArrayListSpliterator(lo, index = mid, expectedModCount);
}
```

This mutates `this` to keep `[mid, hi)` and returns a new spliterator over
`[lo, mid)`. No element moves. Because `hi` is exact (`SIZED`), every split is
within one element of even. Contrast `LinkedList`: it cannot locate a midpoint
without walking node-by-node, so a split costs O(n) just to find the cut, and
that cost is why `LinkedList` streams rarely parallelise usefully — the
splitting overhead eats the gain it was meant to buy.

**Tradeoff, not fact:** `parallelStream()` wins only when `N × per-element
work` clears the fixed cost of submitting to the common `ForkJoinPool`,
splitting, running sub-tasks, and merging. For trivial per-element work, the
crossover is commonly tens of thousands of elements. For blocking per-element
work (I/O, a lock wait), the common pool is the wrong tool entirely: parallel
streams share one process-wide pool by default, so a blocking task there
starves every other parallel stream and `CompletableFuture.supplyAsync` call
relying on the same pool.

**Escape hatch:** measure with realistic size and per-element cost before
reaching for `parallelStream()`; default to `stream()`.

**Interview:** "does `parallelStream()` always help on an `ArrayList`?" — no;
splitting is cheap and balanced *because* it's array-backed, but that only
pays off once element count and per-element cost clear fork-join overhead,
and blocking work never pays off on the shared pool.

> Balanced parallelism here comes from O(1) exact-midpoint splitting, a
> property linked-structure spliterators cannot match.

### The `Collections` wrappers and what they do not fix

Each wrapper in `java.util.Collections` is a thin delegating proxy — same
backing storage, extra checks or locking bolted on the outside — never a copy,
never a redesign of what the list guarantees.

They predate generics and `java.util.concurrent`: retrofitting safety onto an
already-typed `List` reference without a new type was the answer to "share
this without letting the caller corrupt it, race on it, or insert the wrong
type," one wrapper per concern.

| Wrapper | Mechanism | Guarantees | Leaves open |
|---|---|---|---|
| `unmodifiableList` | Delegates reads, throws on writes | Calls through *this reference* can't mutate | Backing list still mutable via any other reference — not a defensive copy |
| `synchronizedList` | Every method body `synchronized` | Each call is atomic | Compound ops and iteration are not covered — external sync required |
| `checkedList` | Runtime type check on insertion | Heap pollution throws `ClassCastException` at the insert site | Nothing about mutability or threads — a diagnostic only |

```java
List<String> live = new ArrayList<>(List.of("AO-100", "AO-400"));
List<String> ro = Collections.unmodifiableList(live);
live.add("AA-700");
ro.get(2);          // "AA-700" — ro changed; it never copied anything
ro.add("AA-800");   // UnsupportedOperationException
```

`List.copyOf` (file 13) takes a real snapshot; `unmodifiableList` only removes
one path to mutation.

```java
List<String> sync = Collections.synchronizedList(new ArrayList<>());
if (!sync.contains(id)) sync.add(id);   // two locked calls, still racy between them

synchronized (sync) {
    for (String id : sync) { /* required by contract for the whole loop */ }
}
```

**Pitfall:** wrapping with `synchronizedList` then iterating with a plain
for-each — each `next()` is locked individually, nothing stops another
thread's `add` between calls, and the plain fail-fast `Itr` still throws.

**Insight:** a thread-safe collection makes each individual operation atomic
and does nothing for an invariant spanning more than one operation — that is
always the caller's problem.

> `synchronizedList`, `unmodifiableList`, and `checkedList` each add one
> narrow guarantee — per-call atomicity, a write barrier through one
> reference, or a type check at insertion — none of which composes across a
> sequence of operations.

### Safe publication and the happens-before gap

Handing an `ArrayList` reference to another thread is not "the other thread
now sees the list." Visibility of its internals — `size`, `elementData`, every
element write behind it — requires a **happens-before edge** between the
writes that built the list and the read that uses it. Without one, a thread
may observe a stale `size` or a stale array reference, even with zero
concurrent mutation happening.

Before the JMM was formalised (JSR-133, Java 5), "just hand off the
reference" was assumed to work because it appears to on most hardware most of
the time — reordering- and cache-dependent failures are rare and
non-reproducible, exactly the kind that survive review and single-threaded
tests.

This applies to any cross-thread handoff, even one nothing later mutates. It
does **not** apply to a list a single thread builds and consumes without ever
exposing the reference — confinement sidesteps the problem entirely.

Mechanisms that establish the edge, any one sufficing: a `volatile` field or
`AtomicReference`; a `final` field of a properly constructed object (no `this`
escaping the constructor); a `synchronized` block both threads use; a
`BlockingQueue` handoff; or thread `start()`/`join()`.

```java
public final class DailyLedgerSnapshot {
    private final List<LedgerEntry> entries;   // final field, safely published
    public DailyLedgerSnapshot(List<LedgerEntry> raw) {
        this.entries = List.copyOf(raw);       // build fully, then freeze
    }
    public List<LedgerEntry> entries() { return entries; }
}
```

Three practical patterns: **build-then-publish-immutably** — finish with
`List.copyOf` before any other thread sees the reference, safe because an
immutable list has nothing left to race on; **thread confinement** — never let
the reference leave its building thread; or **a genuinely concurrent
structure**, designed for handoff, instead of retrofitting one onto
`ArrayList`.

**Pitfall, most-skipped:** absence of `ConcurrentModificationException` is not
evidence of thread safety. `CME` is best-effort and single-threaded (file 08
showed it fires from ordinary single-threaded misuse and also misses some
broken interleavings). A real race can show no `CME` at all and instead a
stale `size`, a silently lost or overwritten element, or — because two
threads racing inside `add`'s `if (s == elementData.length) elementData =
grow();` can both see the pre-grow state — an
`ArrayIndexOutOfBoundsException` thrown from inside `add` itself.

**Interview:** "is `ArrayList` thread-safe if I only add, never remove?" — no;
add-only does not remove the need for a happens-before edge, and concurrent
`add` calls alone can corrupt `elementData` or `size`.

> Safe publication is the happens-before edge that makes a list built on one
> thread visible, in full, to a thread that did not build it; its absence is a
> race regardless of whether any exception surfaces it.

---

Records: a record's generated `equals`/`hashCode` (file 10) make
`List<SomeRecord>` equality correct out of the box, field-by-field. But a
record holding a `List` field is **not** transitively immutable — the field
reference is final, but the referenced list is still mutable unless the
compact constructor wraps it: `this.entries = List.copyOf(entries);`.

Collectors: `Stream.toList()` (16+) — unmodifiable, permits null.
`Collectors.toList()` — mutability unspecified by contract, never rely on it
being an `ArrayList`. `Collectors.toCollection(ArrayList::new)` — the only form
guaranteeing the concrete type.

`Collections.nCopies(n, value)` and `Collections.emptyList()` are
allocation-free stand-ins for a fixed repeated-value list and an empty list —
both immutable views over shared state.

## Pitfalls

### Reaching for `parallelStream()` on small or blocking work

**Wrong**
```java
positions.parallelStream()
    .map(p -> pspClient.fetchBalance(p.accountId()))  // blocking network call
    .toList();
```
Submits blocking work to the shared common pool, starving every other
parallel stream and `CompletableFuture` in the process.

**Right** Use a dedicated executor with `CompletableFuture` for I/O-bound
per-element work; reserve `parallelStream()` for measured, CPU-bound, large-N
work.

**Why people believe it:** it reads as a free performance switch — one word,
no visible cost.

### Treating an absent CME as proof of thread safety

**Wrong** Two threads call `pending.add(r)` concurrently; no exception ever
appears, yet `size` drifts or `add` intermittently throws
`ArrayIndexOutOfBoundsException`.

**Right** Reason about safety from the happens-before edges actually present,
never from whether an exception happened to show up in testing.

**Why people believe it:** `CME` is the only concurrency-flavoured signal
`ArrayList` emits, so silence reads as "nothing went wrong" rather than "this
detector wasn't looking."

### `Collections.unmodifiableList` as a defensive copy

**Wrong**
```java
public List<LedgerEntry> entries() {
    return Collections.unmodifiableList(this.entries);  // still the live backing list
}
```
Anyone still holding `this.entries` directly can mutate it, visibly, through
the "read-only" view.

**Right** `return List.copyOf(this.entries);` when the caller must never see a
later mutation.

**Why people believe it:** the name reads as "immutable," and the thrown
`UnsupportedOperationException` on write feels like proof, when it only shows
that one path is blocked.

### Iterating a `synchronizedList` without external synchronization

**Wrong** `for (String id : sync) { process(id); }` — each `next()` is locked
individually, the loop as a whole is not.

**Right** `synchronized (sync) { for (String id : sync) { process(id); } }`.

**Why people believe it:** every individual call on the wrapper genuinely is
synchronized, so the safety appears to compose across the whole loop.

### Assuming a record with a `List` field is deeply immutable

**Wrong**
```java
record Movement(Id id, List<LedgerEntry> entries) {}
var m = new Movement(id, mutableEntries);
mutableEntries.add(rogueEntry);   // m.entries() now returns the mutated list too
```

**Right**
```java
record Movement(Id id, List<LedgerEntry> entries) {
    Movement { entries = List.copyOf(entries); }
}
```

**Why people believe it:** records are marketed as immutable, and the
reference field genuinely is final — only the referenced list's own
mutability is left open unless the compact constructor closes it.

## Cheat sheet

| Thing | Key fact |
|---|---|
| `ArrayList.spliterator()` characteristics | `ORDERED \| SIZED \| SUBSIZED` — no `DISTINCT`, `SORTED`, `IMMUTABLE`, `CONCURRENT` |
| `SIZED` buys | Exact size upfront — one-shot allocation for collectors |
| `SUBSIZED` buys | Every split also `SIZED` — balanced forking, no probing |
| `ORDERED` buys | Encounter order defined; makes `findFirst` meaningful |
| Late-binding | No array read until traversal starts — an unconsumed `stream()` is not a snapshot |
| CME check point | End of `forEachRemaining` batch, not per element |
| `trySplit()` cost | O(1) exact midpoint — size known exactly |
| `LinkedList` split cost | O(n) walk to find the midpoint — unbalanced |
| `parallelStream()` crossover | Pays off once `N × per-element cost` clears fork-join overhead — measure |
| Blocking work + parallel streams | Wrong tool — shares the common pool with everything else in the process |
| `unmodifiableList` | View, blocks writes through itself, not a defensive copy |
| `synchronizedList` | Per-call atomicity only — not compound ops, not iteration |
| `checkedList` | Runtime element type check at insertion — a diagnostic |
| Safe publication mechanisms | `volatile`/`AtomicReference`, `final` field of a properly built object, `synchronized`, `BlockingQueue`, `start()`/`join()` |
| CME as a race detector | Invalid — best-effort, single-threaded; a race may show none |
| Record + `List` field | Reference final; list mutable unless wrapped with `List.copyOf` |
| `Stream.toList()` (16+) | Unmodifiable, permits null |
| `Collectors.toList()` | Mutability unspecified by contract |
| `Collectors.toCollection(ArrayList::new)` | Guaranteed concrete `ArrayList` |

## Self-test

**Q1.** Why does `ArrayList.spliterator()` report `SUBSIZED`, and what breaks without it?

<details><summary>Answer</summary>

Every spliterator from `trySplit()` also reports an exact size, so fork-join
decides splitting depth by arithmetic alone. Without it, the framework would
have to estimate or probe each half's size, adding cost and risking unbalanced
partitions — the situation `LinkedList`'s spliterator is already in.

</details>

**Q2.** A thread builds a `List<LedgerEntry>`, stores it in a plain (non-`volatile`, non-`final`) field, and a second thread reads that field later with no lock or start/join relationship. What can go wrong?

<details><summary>Answer</summary>

No happens-before edge connects the writes to the read. The second thread may
never see the updated field at all, or may see the reference but a stale
`size` or an `elementData` whose element writes are not yet visible. No
exception is guaranteed — it can simply be wrong silently.

</details>

**Q3.** Why does `ArrayList`'s spliterator split faster and more evenly than `LinkedList`'s?

<details><summary>Answer</summary>

`trySplit()` computes `mid = (lo + hi) >>> 1` in O(1) because `hi` is an
already-known exact index. `LinkedList` elements aren't index-addressable, so
finding a midpoint means walking node-by-node from an end — O(n) per split,
and often uneven because the walk itself is where the cost lives.

</details>

**Q4.** Why is `if (!sync.contains(id)) sync.add(id);` still racy on a `synchronizedList`?

<details><summary>Answer</summary>

Each call is individually atomic, but the two calls are two separate critical
sections. Between `contains` returning and `add` acquiring the lock, another
thread can run its own `contains`/`add` pair and insert the same id — the
combined check-then-act is not atomic even though each half is.

</details>

**Q5.** What does the absence of a `ConcurrentModificationException` prove about code mutating an `ArrayList` from two threads?

<details><summary>Answer</summary>

Nothing. `CME` is a best-effort, single-threaded detector comparing
`modCount`; it is not built to catch races and easily misses them. A real race
can instead produce a stale `size`, a silently lost element, or an
`ArrayIndexOutOfBoundsException` from inside `add` when two threads see the
pre-grow array simultaneously.

</details>

**Q6.** Two threads each read a client's `CASH_AVAILABLE` position of 100, then each reserve 100 (one stake, one withdrawal) against a `synchronizedList` of reservation records. Does the wrapper prevent the invariant violation?

<details><summary>Answer</summary>

No. `synchronizedList` only makes each individual list call atomic. The
violation happens because the check (is 100 available) and the act (record
the reservation) span two separate operations and both threads can pass the
check before either acts. Preventing it needs atomicity across the whole
check-then-act — a lock held for both steps, or an atomic update on the
position — not atomicity of the list's own methods.

</details>

**Q7.** Given roughly 19.8 million `LedgerEntry` records for a day, grouped by `movementId` to check each group sums to zero, is `parallelStream()` a reasonable default here?

<details><summary>Answer</summary>

Plausibly yes: the element count clears typical fork-join overhead, the
per-element work is CPU-bound and non-blocking, and the source is an
`ArrayList`, whose spliterator splits in O(1) with balanced partitions. Still
worth measuring against `stream()` rather than assumed — but this is the shape
of workload where parallel plausibly wins, unlike the blocking PSP-lookup
example above.

</details>

---

**Questions answered:** Q-34
**Sets up:** Next: build one from scratch, which is the only real test of whether the mechanism landed.
**Diagrams included:** none
**Target version:** Java 21
**Lines:** 436
