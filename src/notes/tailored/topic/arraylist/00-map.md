# ArrayList — Map

**Topic:** `java.util.ArrayList`
**Slug:** `arraylist`
**Shape:** **S1 Type / API**, with a secondary **S6 Practice** (capacity sizing, choosing an implementation) and a thin **S4 Model** strand (the `List` contract, and `equals`/`hashCode` across implementations).
**Target version:** Java 21 (verified against JDK 21.0.7 `src.zip` and real runs on 21.0.7).
**Date:** 2026-08-31

## What this arc teaches, and in what order

The set moves from **contract to position to surface to mechanism to cost to judgement.**

It opens with what `ArrayList` actually promises and refuses to promise (01), then places it in the Java 21 type graph — where `SequencedCollection` is a new layer most readers have not met (02), then lays out the complete member surface with the declaring type of every method (03), which is the file that turns a vague sense of "list methods" into a map with lineage.

From there the reader gets construction and the observable difference between `new ArrayList<>()` and `new ArrayList<>(0)` (04), then descends into mechanism: the field set and the backing array (05), append and growth (06), positional insert/remove and the bulk operations (07), the fail-fast iterator and the case where it silently fails to fire (08), `subList` aliasing (09), and the object protocols `equals`/`hashCode`/serialization (10).

Sorting arrives at 11 as a **backbone file** — `Comparable` and `Comparator` taught in place, because you cannot discuss `list.sort` without them. Then the cost model and memory arithmetic collected in one place now that every mechanism behind a number has been explained (12), the alternatives each `ArrayList` must be chosen against (13), the version history and the specific stale claim interviewers still expect (14), interoperation with streams and concurrency (15), a build-it-yourself proof (16), and the mandatory interview file (17).

**Depth is monotonic.** File 01 names no JVM constant and shows no bytecode. Files 05–10 walk real source with real field names. File 12 is the first place a full cost table appears, because every entry in it has already been earned.

---

## Question inventory

36 questions across all 14 coverage-frame rows. **No frame row is empty for this topic** — `ArrayList` is the shape the frame was designed around.

Harvest verdict legend: `covered` = an existing repo note answers it well enough to carry over; `partial` = answered but thin or stale; `gap` = nowhere in the repo.

| id | Frame row | Question | Verdict | Owner |
|---|---|---|---|---|
| Q-01 | 1 Identity | What is an `ArrayList` and what does it guarantee — insertion order, duplicates, nulls, mutability? | partial | 01 |
| Q-02 | 1 Identity | What does it explicitly *not* guarantee — thread safety, and why fail-fast is best-effort rather than a promise? | partial | 01 |
| Q-03 | 1 Identity | What does `RandomAccess` actually mean, given it declares no methods? | gap | 01 |
| Q-04 | 2 Position | What is the full type graph — `Iterable` → `Collection` → `SequencedCollection` → `List`, and `AbstractCollection` → `AbstractList` → `ArrayList`? | partial | 02 |
| Q-05 | 2 Position | What does each layer contribute, and what did Java 21's `SequencedCollection` add? | gap | 02 |
| Q-06 | 2 Position | Who are its siblings, and what is the shape of the `List` family? | covered | 02, 13 |
| Q-07 | 3 Surface | The complete public member table — every method, its declaring type, since-version, return, complexity. | gap | 03 |
| Q-08 | 3 Surface | Which members does `ArrayList` *declare itself* versus inherit versus override, and where does an override change cost or behaviour? | gap | 03 |
| Q-09 | 4 Entry points | Every way to obtain an `ArrayList` — three constructors, `clone`, `List.copyOf`, stream collectors — and what each costs. | partial | 04 |
| Q-10 | 4 Entry points | Why does `new ArrayList<>()` behave observably differently from `new ArrayList<>(0)`? | gap | 04 |
| Q-11 | 5 Lifecycle | What is legal during iteration, and how do you observe capacity from outside the class? | gap | 04, 08 |
| Q-12 | 5 Lifecycle | Which `List`-related things are views and which are copies, and how do you tell? | partial | 04, 09 |
| Q-13 | 6 Mechanism | The complete field set and the exact role of each: `elementData`, `size`, `DEFAULT_CAPACITY`, `EMPTY_ELEMENTDATA`, `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`, inherited `modCount`, `serialVersionUID`. | partial | 05 |
| Q-14 | 6 Mechanism | How does `add(E)` work step by step, and why is there a private three-argument `add` helper? | gap | 06 |
| Q-15 | 6 Mechanism | How does `grow` work in JDK 21 — `ArraysSupport.newLength`, the 1.5x factor, `SOFT_MAX_ARRAY_LENGTH`? | partial (stale) | 06 |
| Q-16 | 6 Mechanism | How do `add(int, E)` and `remove(int)` shift the tail, and why is the vacated slot nulled? | partial | 07 |
| Q-17 | 6 Mechanism | How does `remove(Object)` / `fastRemove` work, and what is the labelled `break found:` doing? | gap | 07 |
| Q-18 | 6 Mechanism | How do `removeAll` / `retainAll` work through `batchRemove`, and what happens if `contains` throws mid-scan? | gap | 07 |
| Q-19 | 6 Mechanism | How does `removeIf` work, and why does it use a long-array bitset instead of repeated `remove`? | gap | 07 |
| Q-20 | 6 Mechanism | How does the fail-fast iterator work, and exactly when does it *not* fire? | partial | 08 |
| Q-21 | 6 Mechanism | How does `subList` work, and what aliasing does it create? | gap | 09 |
| Q-22 | 6 Mechanism | How do `equals` and `hashCode` work, and why can they throw `ConcurrentModificationException`? | gap | 10 |
| Q-23 | 6 Mechanism | How is an `ArrayList` serialized, and why is `elementData` `transient`? | gap | 10 |
| Q-24 | 6 Mechanism | How does `sort` work, and does it bump `modCount`? | gap | 11 |
| Q-25 | 7 Cost | The cost of every operation, with the named cause and the constant factor — not a bare O(). | partial | 12 |
| Q-26 | 7 Cost | What does amortised O(1) actually mean here, and why 1.5x rather than 2x? | partial | 06, 12 |
| Q-27 | 7 Cost | The memory footprint arithmetic — shell, backing array, per-element, and the waste from over-capacity. | partial | 12 |
| Q-28 | 8 Version | What changed across JDK 8 → 9 → 13 → 21, and which widely-repeated claim is now stale? | gap | 14 |
| Q-29 | 9 When to reach | `ArrayList` versus each alternative, with the deciding factor named rather than "it depends". | covered | 13 |
| Q-30 | 10 Failure modes | The misuses that compile and pass tests: `remove(int)` vs `remove(Object)`, CME, `subList` retention, `Arrays.asList`, `toArray`, unsynchronised sharing. | partial | 07, 08, 09, 13 |
| Q-31 | 11 Backbone | `Comparable` versus `Comparator`, and how sorting an `ArrayList` uses them. | partial | 11 |
| Q-32 | 11 Backbone | What do `System.arraycopy` and `Arrays.copyOf` actually do, and why are they fast? | gap | 05 |
| Q-33 | 11 Backbone | How does erasure affect `ArrayList` — the `Object[]` backing, `toArray`, heap pollution? | gap | 12 |
| Q-34 | 12 Interop | How does it compose with streams, spliterators, records, the `Collections` wrappers, and concurrency? | partial | 15 |
| Q-35 | 13 Prove it | Build a minimal `ArrayList` from scratch; observe real capacity by reflection. | gap | 16 |
| Q-36 | 14 Interview | How is it actually asked — the traps and the predict-the-output puzzles. | partial | 17 |

**Frame row coverage check:** rows 1 (Q-01..03), 2 (Q-04..06), 3 (Q-07..08), 4 (Q-09..10), 5 (Q-11..12), 6 (Q-13..24), 7 (Q-25..27), 8 (Q-28), 9 (Q-29), 10 (Q-30), 11 (Q-31..33), 12 (Q-34), 13 (Q-35), 14 (Q-36). No empty rows.

---

## Source ledger

### Primary sources — read directly, not recalled

| Source | Version read | What was taken |
|---|---|---|
| `java/util/ArrayList.java` from JDK 21 `src.zip` | **21.0.7** | Field set, all three constructors, `grow`, `add` + the private three-arg helper and its `MaxInlineSize` comment, `fastRemove`, `batchRemove`, `equals`/`equalsArrayList`/`equalsRange`, `hashCode`/`hashCodeRange`, `clear`, `trimToSize`, `ensureCapacity`, `Itr`, `ListItr`, `SubList`, `writeObject`/`readObject`, `removeIf` bitset helpers, the Java 21 `getFirst`/`getLast`/`addFirst`/`addLast`/`removeFirst`/`removeLast` with their `@since 21` tags |
| `jdk/internal/util/ArraysSupport.java` from JDK 21 `src.zip` | 21.0.7 | `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8`, `newLength`, `hugeLength` |
| `java/util/AbstractList.java`, `AbstractCollection.java`, `List.java`, `Collection.java`, `SequencedCollection.java`, `Iterable.java`, `RandomAccess.java` | 21.0.7 | The declaring type of every inherited member; which `List`/`Collection` members are `default`; `List extends SequencedCollection` |
| `java/util/ArrayList.java` from JDK 8 `src.zip` | 1.8.0_202 | The pre-refactor `grow`, `MAX_ARRAY_SIZE`, `hugeCapacity`; confirmation that `equals`/`hashCode` are **not** overridden in 8 |
| `java/util/ArrayList.java` from JDK 11 and JDK 17 `src.zip` | 11.0.27, 17.0.15 | Bracketing the refactor: 11 still has `MAX_ARRAY_SIZE` + `hugeCapacity`; 17 has neither and calls `ArraysSupport.newLength` |
| OpenJDK tagged sources `jdk-12-ga` … `jdk-17-ga` | tags | **Pinned the refactor to JDK 13.** `jdk-12-ga` has `MAX_ARRAY_SIZE=6` occurrences and no `newLength`; `jdk-13-ga` has zero and one |

### Verified experiments — real output, quoted in the notes as real output

| Experiment | Result recorded |
|---|---|
| Capacity sequence, default constructor, 400 appends, `elementData` read by reflection on 21.0.7 | `0 → 10 15 22 33 49 73 109 163 244 366 549` |
| `new ArrayList<>(0)` then one `add` | capacity **1** — proves `EMPTY_ELEMENTDATA` and `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` are behaviourally distinct |
| `new ArrayList<>()` then one `add` | capacity **10** |
| `new ArrayList<>(4)` then five adds | capacity 4 → **6** |
| `trimToSize` at size 100 | capacity 109 → 100 |
| `clear()` after that | capacity stays **100**, size 0 — `clear` does not shrink |
| Remove **last** element in a for-each | `ConcurrentModificationException` |
| Remove **second-to-last** element in a for-each | **no exception**, loop exits early, final element never visited |
| Mutate inside `forEach` | `ConcurrentModificationException` |
| `subList(1,4)` then `sub.set(0, …)` | writes through to parent index 1 |
| structural `add` to parent, then read the view | `ConcurrentModificationException` |
| `subList(1,4).clear()` | deletes those three from the parent |
| `List<Integer>.remove(1)` vs `remove(Integer.valueOf(20))` | index vs value — the overload trap, both confirmed |
| `toArray(new String[0])` on a `List<Object>` holding an `Integer` | `ArrayStoreException` |
| `Arrays.asList(...).add` / `List.of(...).set` | `UnsupportedOperationException`; `Arrays.asList(...).set` succeeds |
| `modCount` before/after `sort`, `set`, `add` | `sort` **does** bump it; `set` does not; `add` does |
| `ArrayList.class.getDeclaredField("modCount")` | `NoSuchFieldException` — proves `modCount` is inherited from `AbstractList`, not declared |
| `java -XX:+PrintFlagsFinal` on 21.0.7 | `MaxInlineSize = 35`, `C1MaxInlineSize = 35`, `UseCompressedOops = true`, `ObjectAlignmentInBytes = 8` |
| `sort(null)` on a non-`Comparable` element type | `ClassCastException` |
| `reversed()` on 21 | returns `java.util.ReverseOrderListView$Rand`, and it is a **view** — writes propagate |
| empty `getFirst()` | `NoSuchElementException` |

### Repo sources harvested

See `## Harvest result` below — recorded after the harvest pass returned.

### External sources consulted

| Source | Verdict |
|---|---|
| Web search on the `ArraysSupport.newLength` refactor version | **Contradicted by primary source and rejected.** One blog dates the change to "Java 18"; local JDK 17 source already has it and `jdk-13-ga` is where it lands. The notes state JDK 13. |
| `bugs.openjdk.org` for JDK-8230744 / JDK-8161372 | HTTP 403, not readable. Version attribution was pinned by differential source reading instead, which is stronger evidence than a bug record anyway. |

---

## Diagram manifest

Nine diagrams — one per thing a reader would draw on a whiteboard. **Every embed in this set is `diagrams/D-NN-slug.svg` with no `../` prefix**, because every note file sits at the topic root alongside `diagrams/`.

| id | File | Type | Must show | Owning note |
|---|---|---|---|---|
| D-01 | `D-01-hierarchy.svg` | Layered type hierarchy | The interface spine `Iterable → Collection → SequencedCollection → List` with `SequencedCollection` highlighted and version-pilled `21`; the class spine `AbstractCollection → AbstractList → ArrayList`; the three marker interfaces in one grouped panel; a per-layer contribution panel | 02 |
| D-02 | `D-02-memory-layout.svg` | Memory layout / object graph | The 24 B shell with `elementData`/`size`/`modCount` rows; the 56 B capacity-10 `Object[]` with slots 4–9 shown as reserved nulls; four separate `LedgerEntry` heap objects; the list owns the array but not the elements | 05 |
| D-03 | `D-03-growth.svg` | Before/after state pair | Capacity 10 full → capacity 15; the call chain `add → grow → ArraysSupport.newLength(10,1,5)`; the arithmetic `10 + max(1,5) = 15`; `SOFT_MAX_ARRAY_LENGTH`; the real measured sequence; the abandoned old array and the `Arrays.copyOf` O(n) copy | 06 |
| D-04 | `D-04-shift.svg` | Two stacked array-slot frames | `add(2, …)` shifting the tail right as one `System.arraycopy`; `remove(1)` shifting left; the vacated slot explicitly nulled with `es[--size] = null`; the asymmetric-cost panel | 07 |
| D-05 | `D-05-fail-fast.svg` | Two side-by-side step timelines | Case A removing the last element → CME; Case B removing the second-to-last → **no exception, loop exits early**; running `cursor`/`size`/`modCount`/`expectedModCount` at each step; the mechanism panel stating `hasNext()` is `cursor != size` and never checks `modCount` | 08 |
| D-06 | `D-06-sublist-aliasing.svg` | Object graph, one shared array | Parent `ArrayList` and `ArrayList$SubList` with `root`/`parent`/`offset`/`size`; exactly **one** `Object[]`; the bracket over slots 1–3; the aliasing-cost panel including whole-array retention | 09 |
| D-07 | `D-07-choosing-a-list.svg` | Decision tree | Immutable → `List.of`; shared + read-mostly → `CopyOnWriteArrayList`; shared + write-heavy → `synchronizedList`; front/middle churn → `ArrayDeque`/`LinkedList`; otherwise `ArrayList`; a legacy node for `Vector`/`Stack`; an `Arrays.asList` fixed-size node | 13 |
| D-08 | `D-08-amortised-cost.svg` | Step chart + computation panel | Capacity steps 10, 15, 22, 33, 49, 73, 109 drawn orthogonally; per-riser copy cost; the total `10+15+22+33+49+73 = 202` against 109 appends; `g/(g-1) = 3n`; the escape hatch that presizing removes every copy | 12 |
| D-09 | `D-09-growth-code-history.svg` | Version timeline, four panels | JDK 8 / JDK 9–12 / JDK 13–20 / JDK 21 states of the growth code; the `MAX_ARRAY_SIZE` removal boundary between 9–12 and 13–20; the "stale answer" panel naming what is false from JDK 13 on | 14 |

---

## File plan

Seventeen note files. Multi-file because the topic has a genuine dependency arc: the fail-fast iterator cannot be explained before `modCount`, `modCount` cannot be explained before the field set, and the cost table is meaningless before the mechanisms that produce the numbers.

### 01-what-it-guarantees.md

| Column | Contents |
|---|---|
| Teaches | State precisely what an `ArrayList` promises, what it refuses to promise, and what `RandomAccess` means. |
| Frame rows | 1 |
| Questions | Q-01, Q-02, Q-03 |
| Primary concepts | The ordered-sequence contract; the resizable-array premise; `RandomAccess` as a marker; the absence of thread safety |
| Sources | JDK 21 `ArrayList` class javadoc; `RandomAccess.java`; `List.java` contract text |
| Diagrams | none — the picture belongs to 02, and a first file that reaches for a diagram of the hierarchy has skipped a step |
| Examples | `Movement.entries` as `List<LedgerEntry>` — order matters, duplicates are legal (two identical-amount entries in one movement), the append-only invariant |
| Assumes | `Assumes: no prior knowledge of ArrayList.` |
| Sets up | `Next: where ArrayList sits in the Java 21 type graph, and what each layer above it contributes.` |
| Previous | — |
| Next | `02-where-it-sits.md` |
| Est. lines | 300 |
| Status | done |
| Lines | 437 |

### 02-where-it-sits.md

| Column | Contents |
|---|---|
| Teaches | Place `ArrayList` in the full Java 21 type graph and say what each supertype contributes, including the `SequencedCollection` layer that is new in 21. |
| Frame rows | 2 |
| Questions | Q-04, Q-05, Q-06 (shape of the family only; the choosing decision is file 13) |
| Primary concepts | The interface spine and the abstract-class spine; what `AbstractList` and `AbstractCollection` each contribute; `SequencedCollection` and the six new methods; the marker interfaces |
| Sources | JDK 21 `List.java` declaration `List<E> extends SequencedCollection<E>`; `SequencedCollection.java` full member list; `AbstractList.java`/`AbstractCollection.java` declarations; `ArrayList` declaration line |
| Diagrams | **D-01** — caption: *ArrayList's full type graph in Java 21; SequencedCollection is the new layer between Collection and List.* |
| Examples | `Movement.entries` and `PaymentRun.itemIds` — `getFirst()`/`getLast()` on a payment run's items reads naturally, which is the point of the 21 addition |
| Assumes | `Assumes: the ArrayList contract (file 01).` |
| Sets up | `Next: the complete member surface, with the type that declares each method.` |
| Previous | `01-what-it-guarantees.md` |
| Next | `03-the-complete-surface.md` |
| Est. lines | 360 |
| Status | done |
| Lines | 534 |

### 03-the-complete-surface.md

| Column | Contents |
|---|---|
| Teaches | Read the whole member surface with lineage — which type declares each method, which ones `ArrayList` overrides, and where an override changes cost. |
| Frame rows | 3 |
| Questions | Q-07, Q-08 |
| Primary concepts | The declared-in-`ArrayList` set; the overridden-from-`AbstractList`/`AbstractCollection` set; the inherited-and-not-overridden set; the `default` methods that arrive from interfaces |
| Sources | Mechanically extracted declaration lists from JDK 21 `ArrayList.java`, `AbstractList.java`, `AbstractCollection.java`, `List.java`, `Collection.java`, `SequencedCollection.java`, `Iterable.java` — pasted into the packet |
| Diagrams | none — this file *is* the table; a diagram would duplicate D-01 |
| Examples | Operations on `Movement.entries` and a `List<Restriction>` used to name what each method is for |
| Assumes | `Assumes: the type graph (file 02).` |
| Sets up | `Next: every way to construct one, and why an initial capacity of zero behaves differently from no argument at all.` |
| Previous | `02-where-it-sits.md` |
| Next | `04-creating-and-obtaining.md` |
| Est. lines | 430 |
| Status | done |
| Lines | 549 |

### 04-creating-and-obtaining.md

| Column | Contents |
|---|---|
| Teaches | Choose a construction route deliberately, and explain the observable difference between the two empty-array sentinels. |
| Frame rows | 4, 5 (partly) |
| Questions | Q-09, Q-10, Q-11 (the capacity-observation half), Q-12 (copy vs view) |
| Primary concepts | The three constructors; the two empty-array sentinels and lazy allocation; copy-vs-view among `List` sources; observing capacity from outside |
| Sources | JDK 21 `ArrayList(int)`, `ArrayList()`, `ArrayList(Collection)` bodies; `EMPTY_ELEMENTDATA` / `DEFAULTCAPACITY_EMPTY_ELEMENTDATA` declarations and the comment distinguishing them; the verified `new ArrayList<>(0)` → capacity 1 experiment |
| Diagrams | none — D-02 and D-03 are the pictures and they belong to 05 and 06 |
| Examples | Presizing `Movement.entries` to 4 (a movement has 2–4 entries per Appendix A.3); bulk-loading the 40k-record daily bank statement file, 500k at month end |
| Assumes | `Assumes: the member surface (file 03).` |
| Sets up | `Next: the fields behind all of this — what an ArrayList actually is in memory.` |
| Previous | `03-the-complete-surface.md` |
| Next | `05-fields-and-the-backing-array.md` |
| Est. lines | 340 |
| Status | done |
| Lines | 595 |

### 05-fields-and-the-backing-array.md

| Column | Contents |
|---|---|
| Teaches | Name every field, say what it is for, and read `get`/`set` off the backing array — including why there is no `capacity` field. |
| Frame rows | 6 |
| Questions | Q-13, Q-32 |
| Primary concepts | The field set and each role; capacity as `elementData.length` rather than a field; `modCount` as inherited state; `System.arraycopy` and `Arrays.copyOf` as intrinsics |
| Sources | JDK 21 field declarations with line numbers; `get`/`set`/`elementData(int)`/`elementAt` bodies; the `NoSuchFieldException` experiment proving `modCount` is inherited |
| Diagrams | **D-02** — caption: *An ArrayList of four LedgerEntry objects at capacity 10 — the shell, the backing array, and the elements are three separate allocations.* |
| Examples | A `Movement`'s four `LedgerEntry` objects living in a capacity-10 array; `Money` as the value type inside them |
| Assumes | `Assumes: the construction routes and the two empty sentinels (file 04).` |
| Sets up | `Next: what happens on the append that finds the array full.` |
| Previous | `04-creating-and-obtaining.md` |
| Next | `06-append-and-growth.md` |
| Est. lines | 360 |
| Status | done |
| Lines | 419 |

### 06-append-and-growth.md

| Column | Contents |
|---|---|
| Teaches | Walk `add(E)` and `grow` in JDK 21 exactly, compute the next capacity by hand, and explain amortisation at the mechanism level. |
| Frame rows | 6, 7 (partly) |
| Questions | Q-14, Q-15, Q-26 (the mechanism half; the arithmetic is collected in 12) |
| Primary concepts | `add(E)` and the private three-arg helper kept under `MaxInlineSize`; `grow` delegating to `ArraysSupport.newLength`; the soft max clamp; amortised O(1) |
| Sources | JDK 21 `add(E)`, the private `add(E, Object[], int)` **with its verbatim source comment about the 35-byte `MaxInlineSize` limit**, `grow()`, `grow(int)`; `ArraysSupport.newLength` and `hugeLength` in full; `MaxInlineSize = 35` from `PrintFlagsFinal`; the measured capacity sequence |
| Diagrams | **D-03** — caption: *The eleventh add on a capacity-10 list allocates a capacity-15 array and copies; growth is 1.5x via ArraysSupport.newLength.* |
| Examples | `PaymentRun.itemIds` growing to the 1.8k records of a payout file (Appendix A.5); the 40k-record statement file as the presize case |
| Assumes | `Assumes: the field set and the backing array (file 05).` |
| Sets up | `Next: the operations that move existing elements — positional insert, removal, and the bulk operations.` |
| Previous | `05-fields-and-the-backing-array.md` |
| Next | `07-insert-remove-and-bulk.md` |
| Est. lines | 420 |
| Status | done |
| Lines | 450 |

### 07-insert-remove-and-bulk.md

| Column | Contents |
|---|---|
| Teaches | Explain every mutation that is not a plain append, and why `removeIf` is not a loop of `remove`. |
| Frame rows | 6, 10 (partly) |
| Questions | Q-16, Q-17, Q-18, Q-19, Q-30 (the `remove` overload trap) |
| Primary concepts | Positional insert and the tail shift; `fastRemove` and the nulled slot; `batchRemove` and its exception-safety `finally`; `removeIf`'s bitset |
| Sources | JDK 21 `add(int,E)`, `remove(int)`, `remove(Object)` with the labelled `break found:`, `fastRemove`, `shiftTailOverGap`, `clear`, `removeAll`/`retainAll`/`batchRemove` in full, `removeIf` with `nBits`/`setBit`/`isClear`; the verified `remove(1)` vs `remove(Integer.valueOf(20))` output |
| Diagrams | **D-04** — caption: *Inserting at index 2 and removing index 1 both cost one System.arraycopy of the tail; only removal nulls the vacated slot.* |
| Examples | A client's `List<Restriction>` — 38k applied and lifted per day (Appendix A.5); lifting one restriction by value versus by index is exactly the overload trap in production shape |
| Assumes | `Assumes: append and growth (file 06).` |
| Sets up | `Next: how iteration detects that one of these mutations happened underneath it — and the case where it does not.` |
| Previous | `06-append-and-growth.md` |
| Next | `08-iteration-and-fail-fast.md` |
| Est. lines | 430 |
| Status | done |
| Lines | 446 |

### 08-iteration-and-fail-fast.md

| Column | Contents |
|---|---|
| Teaches | Trace the fail-fast mechanism through `modCount`, and predict correctly whether a given mutation throws — including the case that silently does not. |
| Frame rows | 5, 6 |
| Questions | Q-11 (the iteration half), Q-20, Q-30 (the CME half) |
| Primary concepts | `modCount` versus `expectedModCount`; `hasNext()` as `cursor != size`; the second-to-last removal that does not throw; `Iterator.remove` as the legal mutation |
| Sources | JDK 21 `Itr` in full including `forEachRemaining`, `ListItr`, `ArrayList.forEach`; the four verified CME experiments with their real outcomes |
| Diagrams | **D-05** — caption: *hasNext() compares cursor to size and never checks modCount, so removing the second-to-last element exits the loop early instead of throwing.* |
| Examples | Iterating a client's restrictions while lifting one; the §9.2 restriction lifecycle |
| Assumes | `Assumes: the mutation operations and modCount (file 07).` |
| Sets up | `Next: the view that shares the same array and the same modCount — subList.` |
| Previous | `07-insert-remove-and-bulk.md` |
| Next | `09-sublist-and-aliasing.md` |
| Est. lines | 400 |
| Status | done |
| Lines | 450 |

### 09-sublist-and-aliasing.md

| Column | Contents |
|---|---|
| Teaches | Use `subList` correctly, and recognise the three ways its aliasing bites — write-through, parent invalidation, and retention. |
| Frame rows | 6, 10 (partly) |
| Questions | Q-21, Q-12 (the view half), Q-30 (the retention trap) |
| Primary concepts | `ArrayList$SubList`'s `root`/`parent`/`offset`/`size`; write-through; CME on parent structural change; whole-array retention |
| Sources | JDK 21 `subList`, the `SubList` static nested class declaration and its constructors, `SubList.set`/`get`/`size`/`removeRange`; the four verified subList experiments |
| Diagrams | **D-06** — caption: *subList returns an ArrayList$SubList holding an offset and size over the parent's own array — one array, two objects, writes visible both ways.* |
| Examples | §7.3 "show me all my withdrawals" — paginating a withdrawal list with `subList`, and the memory leak when a page is cached and the full list is retained |
| Assumes | `Assumes: fail-fast and modCount (file 08).` |
| Sets up | `Next: the object protocols — equality, hashing, and what actually crosses a serialization boundary.` |
| Previous | `08-iteration-and-fail-fast.md` |
| Next | `10-equality-and-serialization.md` |
| Est. lines | 340 |
| Status | done |
| Lines | 450 |

### 10-equality-and-serialization.md

| Column | Contents |
|---|---|
| Teaches | State the `List` equality contract across implementations, and explain the serialized form and why the backing array is `transient`. |
| Frame rows | 6, 8 (partly) |
| Questions | Q-22, Q-23 |
| Primary concepts | The cross-implementation `List` equality contract; the `equalsArrayList` fast path and the CME it can throw; `hashCode` as the 31-multiplier fold; the custom serialized form |
| Sources | JDK 21 `equals`, `equalsArrayList`, `equalsRange`, `checkForComodification`, `hashCode`, `hashCodeRange`, `writeObject`, `readObject`, the `transient elementData` declaration, `serialVersionUID = 8683452581122892189L`; the verified `ArrayList.equals(LinkedList) == true` result; the JDK 8 versus 11 override delta |
| Diagrams | none — the mechanism is arithmetic and a stream format, both better as code and a table than a picture |
| Examples | Comparing two `List<LedgerEntry>` reconstructions during §14.3 reconciliation; serializing a `Movement` |
| Assumes | `Assumes: subList and the shared-array views (file 09).` |
| Sets up | `Next: ordering — the backbone concepts sorting depends on, taught in place.` |
| Previous | `09-sublist-and-aliasing.md` |
| Next | `11-sorting-comparable-and-comparator.md` |
| Est. lines | 330 |
| Status | done |
| Lines | 435 |

### 11-sorting-comparable-and-comparator.md

| Column | Contents |
|---|---|
| Teaches | Sort an `ArrayList` correctly, and choose between `Comparable` and `Comparator` on the right grounds. **This is the backbone file** — both interfaces are taught here, at the depth this topic needs. |
| Frame rows | 6, 11 |
| Questions | Q-24, Q-31 |
| Primary concepts | `Comparable` as intrinsic order versus `Comparator` as imposed order; `List.sort` and the `modCount` bump; TimSort and stability; the comparator contract and how violating it is detected |
| Sources | JDK 21 `ArrayList.sort`, `List.sort` default, `Arrays.sort(T[], Comparator)` entry; the verified `modCount` before/after `sort`; the verified `sort(null)` `ClassCastException`; the verified `Comparator.comparingLong(...).thenComparing(...)` output |
| Diagrams | none — the ordering story is a table of comparator chains, and the two existing cost diagrams already carry the numeric side |
| Examples | Sorting `LedgerEntry` by `postedAt` then `direction` (the real verified run); ordering `PaymentRun` items by `Money` amount; `Money` deliberately *not* `Comparable` across currencies |
| Assumes | `Assumes: equality and hashing (file 10).` |
| Sets up | `Next: the full cost model and the memory arithmetic, now that every mechanism behind a number has been explained.` |
| Previous | `10-equality-and-serialization.md` |
| Next | `12-cost-and-memory.md` |
| Est. lines | 350 |
| Status | done |
| Lines | 448 |

### 12-cost-and-memory.md

| Column | Contents |
|---|---|
| Teaches | Give the cost of every operation with its named cause, and compute a real footprint including the waste from over-capacity. |
| Frame rows | 7, 11 |
| Questions | Q-25, Q-26 (the arithmetic half), Q-27, Q-33 |
| Primary concepts | The per-operation cost table with causes; amortisation arithmetic and the `g/(g-1)` bound; footprint arithmetic under compressed oops; erasure's consequences for the `Object[]` backing and `toArray` |
| Sources | Verified `UseCompressedOops = true` and `ObjectAlignmentInBytes = 8` from `PrintFlagsFinal`; the measured capacity sequence; the verified `ArrayStoreException` from `toArray(new String[0])`; Appendix A.3 volumes |
| Diagrams | **D-08** — caption: *Capacity steps 10, 15, 22, 33, 49, 73, 109 — the total copy work to reach n is bounded by about 3n, which is what amortised O(1) means.* |
| Examples | 19.8M ledger entries/day at ~180 bytes/row (Appendix A.3); the default-constructed `Movement.entries` wasting six slots per movement, multiplied across ~4.95M movements/day |
| Assumes | `Assumes: growth (file 06), the mutation costs (file 07), and sorting (file 11).` |
| Sets up | `Next: the implementations ArrayList must be chosen against, and the deciding factor for each.` |
| Previous | `11-sorting-comparable-and-comparator.md` |
| Next | `13-choosing-and-alternatives.md` |
| Est. lines | 400 |
| Status | done |
| Lines | 437 |

### 13-choosing-and-alternatives.md

| Column | Contents |
|---|---|
| Teaches | Pick the right `List` for a given situation and defend the choice by naming the deciding factor. |
| Frame rows | 9, 10 (partly) |
| Questions | Q-06 (the choosing half), Q-29, Q-30 (`Arrays.asList` and sharing traps) |
| Primary concepts | `ArrayList` versus `LinkedList` on cache behaviour rather than big-O; the immutable factories; the concurrent options; the fixed-size `Arrays.asList` view |
| Sources | Verified `Arrays.asList(...).add` → `UnsupportedOperationException` and `.set` → success; `List.of(...).set` → `UnsupportedOperationException`; JDK 21 `CopyOnWriteArrayList` and `Collections.synchronizedList` contracts |
| Diagrams | **D-07** — caption: *A decision tree for picking a List implementation; ArrayList is the default and LinkedList almost never wins.* |
| Examples | The `BalanceView` hot read path at 1,200 stake reservations/sec (Appendix A.2) as the read-mostly snapshot case; the agreement cache from Appendix C.6; `Movement.entries` as the immutable-list case |
| Assumes | `Assumes: the cost model (file 12).` |
| Sets up | `Next: what changed across JDK versions, and the one stale claim interviewers still expect to hear.` |
| Previous | `12-cost-and-memory.md` |
| Next | `14-version-history.md` |
| Est. lines | 380 |
| Status | planned |
| Lines | |

### 14-version-history.md

| Column | Contents |
|---|---|
| Teaches | State what changed in each JDK, and answer the growth-internals question in a way that is correct for 21 while showing awareness of the version the interviewer probably read. |
| Frame rows | 8 |
| Questions | Q-28 |
| Primary concepts | The JDK 9 `grow`/`newCapacity` split; the **JDK 13** move to `ArraysSupport.newLength` and the removal of `MAX_ARRAY_SIZE`; the JDK 9-era `equals`/`hashCode` overrides; the Java 21 `SequencedCollection` additions |
| Sources | Differential reading of JDK 8, 11, 12, 13, 17 and 21 `ArrayList.java` — the exact occurrence counts that pin the refactor to JDK 13; the JDK 8 `grow`/`hugeCapacity` body in full; the JDK 11 `newCapacity` body in full; the JDK 21 `grow` body in full |
| Diagrams | **D-09** — caption: *The growth code changed twice — the grow/newCapacity split in JDK 9, then delegation to ArraysSupport.newLength in JDK 13 which removed MAX_ARRAY_SIZE from ArrayList entirely.* |
| Examples | The same `PaymentRun.itemIds` growth walked under JDK 8 rules and JDK 21 rules to show the code differs and the resulting capacities do not |
| Assumes | `Assumes: growth (file 06) and the choosing criteria (file 13).` |
| Sets up | `Next: how ArrayList composes with the rest of the platform — streams, spliterators, and concurrency.` |
| Previous | `13-choosing-and-alternatives.md` |
| Next | `15-interop-streams-and-concurrency.md` |
| Est. lines | 320 |
| Status | planned |
| Lines | |

### 15-interop-streams-and-concurrency.md

| Column | Contents |
|---|---|
| Teaches | Compose an `ArrayList` with streams and share one across threads without being wrong about it. |
| Frame rows | 12 |
| Questions | Q-34 |
| Primary concepts | `ArrayListSpliterator` and its characteristics; why splitting an array-backed list parallelises well; the `Collections` wrappers and what they do not fix; safe-publication and the happens-before gap |
| Sources | JDK 21 `spliterator()`, the `ArrayListSpliterator` nested class, `Collection.stream`/`parallelStream` defaults; the verified `forEach` CME; `Collections.synchronizedList` javadoc on iteration |
| Diagrams | none — the two ideas here are a characteristics bitmask (a table) and a happens-before argument that D-05 already frames |
| Examples | Streaming a day's `LedgerEntry` list to reconcile per §14.3; two threads reserving stakes on one client at the §15.1 race-condition row |
| Assumes | `Assumes: iteration and fail-fast (file 08), and the alternatives (file 13).` |
| Sets up | `Next: build one from scratch, which is the only real test of whether the mechanism landed.` |
| Previous | `14-version-history.md` |
| Next | `16-prove-it.md` |
| Est. lines | 350 |
| Status | planned |
| Lines | |

### 16-prove-it.md

| Column | Contents |
|---|---|
| Teaches | Build a working minimal `ArrayList` with the same growth policy, and instrument the real one to confirm the numbers first-hand. |
| Frame rows | 13 |
| Questions | Q-35 |
| Primary concepts | The build-it-yourself list with `elementData`/`size`/`modCount`; reproducing 1.5x growth and the soft clamp; a fail-fast iterator; the reflection probe that reads real capacity |
| Sources | The reflection capacity probe used to produce this set's measured sequence, given verbatim with its `--add-opens` flag; JDK 21 `grow` as the reference implementation to match |
| Diagrams | none — this file's artefact is runnable code, and the pictures it would draw are D-02, D-03 and D-05, already embedded upstream |
| Examples | `LedgerEntryList` — a minimal typed list holding `LedgerEntry`, presized to 4 |
| Assumes | `Assumes: everything from files 05 through 08 — the fields, growth, the mutation operations, and fail-fast.` |
| Sets up | `Next: the interview surface — how all of this is actually asked.` |
| Previous | `15-interop-streams-and-concurrency.md` |
| Next | `17-interview.md` |
| Est. lines | 380 |
| Status | planned |
| Lines | |

### 17-interview.md

| Column | Contents |
|---|---|
| Teaches | Answer the real questions out loud, survive the predict-the-output puzzles, and self-check coverage. |
| Frame rows | 14 |
| Questions | Q-36, plus a recall pass over all 36 |
| Primary concepts | The summary table; the answers said out loud; the puzzles; the atomic concept checklist |
| Sources | Every verified experiment in this map's ledger — each puzzle's stated output must be one of them |
| Diagrams | none — the interview file recalls, it does not re-teach; it links back to D-01, D-03, D-05 |
| Examples | Reuses the domain slices already established, so nothing new needs setting up |
| Assumes | `Assumes: the whole set, files 01 through 16.` |
| Sets up | — (last file) |
| Previous | `16-prove-it.md` |
| Next | — |
| Est. lines | 460 |
| Status | planned |
| Lines | |

**Counts required in 17:** 17 note files, so files beyond the sixth = 11. Q&As required = 12 + (2 x 11) = **34 minimum**. Puzzles = **8** (5 is the floor; this topic has more verified surprises than that). Plus a flat `## Atomic concept checklist` as the final section.

**Seal check.** Every one of Q-01..Q-36 appears in at least one row and no concept straddles two rows (Q-06, Q-11, Q-12, Q-26 and Q-30 are deliberately split across two files each, with the split stated in the owning rows). Every manifest id D-01..D-09 is embedded in exactly one row. Every row names two to six primary concepts. No `Assumes` line references a later file. The `Previous`/`Next` chain runs unbroken from 01 to 17.

---

## Reading order

**Front to back:** 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17.

The natural pause points are after **04** (you can now use the class correctly), after **09** (you now know the internals that produce surprises), and after **13** (you can now defend a design choice).

**Night before the interview:**

1. `17-interview.md` — the summary table and all puzzles.
2. `03-the-complete-surface.md` — the declaring-type table only; it is the single densest recall asset.
3. `06-append-and-growth.md` — the `grow` walk and the capacity arithmetic. Be able to compute the next capacity out loud.
4. `14-version-history.md` — the stale-claim panel. This is the highest-leverage page in the set for a growth-internals question.
5. `08-iteration-and-fail-fast.md` — D-05 and the two cases.
6. `12-cost-and-memory.md` — the cheat-sheet table.
7. `13-choosing-and-alternatives.md` — D-07, so the "why not LinkedList" answer is one sentence.

---

## Open questions

Appended as envelopes return.

- **Exact JDK version that added the `equals`/`hashCode` overrides to `ArrayList`.** Verified absent in JDK 8 and present in JDK 11; the `jdk-10-ga` tag does not exist in the `openjdk/jdk` repository and `bugs.openjdk.org` returns HTTP 403, so 9 versus 10 versus 11 was not separated. The notes state the verified bracket — absent in 8, present from 11 — rather than guessing. Settled by reading a JDK 9 or JDK 10 `src.zip` directly.
- **TimSort comparator-contract detection.** A deliberately inconsistent comparator returning a constant `1` over 40 elements did **not** throw `IllegalArgumentException: Comparison method violates its general contract!` on 21.0.7. The exception is real but requires a specific run structure, so file 11 must present it as a possible detection rather than a guaranteed one.
