# `ArrayList` — Map

**Topic:** `java.util.ArrayList`
**Slug:** `array-list`
**Shape:** **S1 — Type / API.** Secondary: **S1 backbone** on `Comparable` /
`Comparator` (frame row 11), folded in as a late file (`14-`), not a separate topic.
**Target version:** Java 21 LTS. Deltas traced back to JDK 1.2.
**Date:** 2026-08-29

This set teaches `ArrayList` as an arc, not a reference tree. It opens with what
the `List` contract actually promises and what it deliberately refuses to promise,
then places the type in the hierarchy so the reader knows which of its ~50 members
came from where. Only then does it print the complete member surface with
declaring-type lineage, because a method table with no lineage teaches nothing
about why `contains` is O(n) while `get` is O(1). The middle of the set is the
mechanism: three fields, two indistinguishable empty arrays used as a one-bit flag,
one arithmetic expression for growth, one `System.arraycopy` for every structural
mutation, and a `long[]` bitset for bulk removal. Costs and memory arrive after the
mechanism, because a number with no named cause is not an answer. The set then turns
outward — how to choose it, how it fails in production, what changed across seven
JDK releases, the ordering backbone `sort` depends on, and how it composes with
streams, arrays, generics and serialization. It closes with a from-scratch build,
a measurement harness, and the interview surface.

Read front to back. Nothing is used before it is taught.

---

## Topic shape and what that means here

`ArrayList` is shape **S1**: a concrete class you instantiate and call. That fixes
what each coverage-frame row means for this run:

| Frame row | What it means for `ArrayList` |
|---|---|
| 1 Identity and contract | Ordering, duplicates, nulls, mutability, thread-safety, fail-fast, size vs capacity |
| 2 Position in the map | Supertypes, marker interfaces, siblings, the family diagram |
| 3 Surface and knobs | The **complete** public member table with `Declared in` lineage |
| 4 Entry points | Three constructors, the copy paths, and the factories that do *not* give you one |
| 5 Lifecycle and observation | Iteration legality, `ListIterator` rules, view staleness, capacity observability |
| 6 Mechanism | `elementData`/`size`/`modCount`, the sentinels, `grow`, `arraycopy`, `deathRow`, `Itr`, `SubList`, `ArrayListSpliterator`, `writeObject` |
| 7 Cost model | Complexity **and** the constant factor, with the named cause |
| 8 Version history | 1.2, 7, 8, 9, 13, 16, 21 — and the claims that are now stale |
| 9 When to reach for it | Paired with the sibling that wins when it loses |
| 10 Failure modes | The misuse that compiles and passes tests, its production symptom, the fix |
| 11 Backbone concepts | `Comparable`, `Comparator`, `List.equals`/`hashCode` — taught in place |
| 12 Interoperation | Streams, `toArray` covariance, erasure, serialization, `Arrays.asList`/`List.of` |
| 13 Prove it | Build a working array-backed list; measure growth, copies, footprint |
| 14 Interview surface | 38 Q&As, 8 predict-the-output puzzles, atomic concept checklist |

**Empty frame rows: none.** All fourteen rows generated questions for this topic.

---

## Question inventory

48 questions. Every id is assigned to exactly one file.

### Row 1 — Identity and contract

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-01 | What is an `ArrayList`, and what exactly does the `List` contract guarantee about order, index and duplicates? | partial | `01-` |
| Q-02 | What does it explicitly **not** guarantee — thread-safety, stable iteration under mutation, sorted order, capacity? | partial | `01-` |
| Q-03 | What is its null policy, and how does that differ from `List.of` and from `Map` keys? | partial | `01-` |
| Q-04 | What is the relationship between `size` and capacity, and why is capacity absent from the contract? | covered | `01-` |

### Row 2 — Position in the map

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-05 | Where does `ArrayList` sit — `Iterable` → `Collection` → `SequencedCollection` → `List`, and `AbstractCollection` → `AbstractList` → `ArrayList`? | partial | `02-` |
| Q-06 | What does `RandomAccess` mean, who reads it, and what changes when it is absent? | partial | `02-` |
| Q-07 | Who are the siblings — `LinkedList`, `ArrayDeque`, `Vector`, `CopyOnWriteArrayList`, `List.of`, `Arrays.asList` — and what is each one's job? | partial | `02-` |

### Row 3 — Surface and knobs

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-08 | What is the **complete** public and protected member surface, and which type declares each member? | **gap** | `03-` |
| Q-09 | What does each declaring type contribute, and which `ArrayList` overrides change behaviour or cost versus the declaration? | **gap** | `03-` |
| Q-10 | Which members are optional operations, and where does `UnsupportedOperationException` come from? | partial | `03-` |

### Row 4 — Entry points

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-11 | What are the three constructors and what does each cost? | covered | `04-` |
| Q-12 | What are the non-constructor routes to an `ArrayList` — copy constructor, `Collectors.toList`, `clone`, deserialization — and which of them *guarantee* the runtime type? | partial | `04-` |
| Q-13 | Which `List`-producing factories do **not** give you an `ArrayList`, and what do they give instead? | partial | `04-` |

### Row 5 — Lifecycle and observation

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-14 | What is legal during iteration, and what are the exact state rules of `ListIterator`? | covered | `08-` |
| Q-15 | How do you observe capacity, footprint and growth from outside the object? | partial | `10-` |
| Q-16 | What are the view semantics of `subList` and `reversed()`, and when does a view go undefined? | partial | `08-` |

### Row 6 — Mechanism

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-17 | What are the fields and constants, and why are there **two** zero-length empty arrays? | covered | `05-` |
| Q-18 | How does `grow` compute a new capacity, and what is the exact capacity sequence? | covered | `05-` |
| Q-19 | What happens on `add(E)` and `add(int, E)`, statement by statement? | covered | `06-` |
| Q-20 | What happens on `remove(int)` and `remove(Object)`, and what is the trailing null for? | covered | `06-` |
| Q-21 | How does bulk removal work — `removeIf`'s `deathRow` bitset and `batchRemove`'s `catch`/`finally` repair? | covered | `07-` |
| Q-22 | How do `Itr`, `ListItr` and `modCount` implement fail-fast, and where is fail-fast only best-effort? | covered | `08-` |
| Q-23 | How does `ArrayListSpliterator` split, and what characteristics does it report? | covered | `09-` |
| Q-24 | How does `SubList` delegate — `root`, `parent`, `offset` — and what does that cost? | covered | `08-` |
| Q-25 | How does serialization work given `elementData` is `transient`? | partial | `09-` |
| Q-26 | What is the memory layout of an `ArrayList`, byte by byte? | partial | `10-` |

### Row 7 — Cost model

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-27 | What is the complexity **and** the real constant factor of every operation? | partial | `10-` |
| Q-28 | Why is `add` amortised O(1), and what does the amortised bound refuse to promise? | covered | `10-` |
| Q-29 | What does an `ArrayList` cost in bytes versus `LinkedList` and versus a raw array, measured? | partial | `10-` |
| Q-30 | Where does `ArrayList` beat `LinkedList` even where big-O says it should not, and why? | partial | `11-` |

### Row 8 — Version history

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-31 | What changed in `ArrayList` across JDK 1.2, 7, 8, 9, 13, 16 and 21? | partial | `13-` |
| Q-32 | Which widely-repeated claims about `ArrayList` are now version-stale, and what is true today? | partial | `13-` |

### Row 9 — When to reach for it

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-33 | When is `ArrayList` right, and which named alternative wins when it is not? | partial | `11-` |

### Row 10 — Failure modes

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-34 | Which misuses compile, pass tests, and only fail in production — with symptom and fix? | **gap** | `12-` |
| Q-35 | What *actually happens* when an `ArrayList` is shared across threads — beyond "it is not thread-safe"? | **gap** | `12-` |

### Row 11 — Backbone concepts

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-36 | What is the `Comparable` contract, and what does "consistent with `equals`" mean for a list? | covered | `14-` |
| Q-37 | How do `Comparator` factories compose, and what does `list.sort(c)` actually run? | partial | `14-` |
| Q-38 | How are `List.equals` and `List.hashCode` specified, and what does `ArrayList` do differently from the specification's reference algorithm? | partial | `14-` |

### Row 12 — Interoperation

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-39 | How does `ArrayList` compose with streams — `spliterator`, `stream().toList()` vs `Collectors.toList()`, collector sizing? | partial | `15-` |
| Q-40 | What is the `Object[]` covariance trap around `toArray`, and what changed in Java 9? | **gap** | `15-` |
| Q-41 | How does erasure show up in `ArrayList` — heap pollution, `toArray(T[])`, the unchecked casts in the source? | partial | `15-` |
| Q-42 | What are the serialization interop hazards — `serialVersionUID`, and which views are not serializable? | **gap** | `15-` |
| Q-43 | What are the `Arrays.asList` and `List.of` semantics traps when mixed with `ArrayList`? | partial | `15-` |

### Row 13 — Prove it

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-44 | Can you build a working array-backed list from scratch — growth, fail-fast iteration, `subList`? | covered | `16-` |
| Q-45 | Can you measure the growth sequence, the copy count, the footprint, and the `LinkedList` comparison? | partial | `16-` |

### Row 14 — Interview surface

| Id | Question | Verdict | Owner |
|---|---|---|---|
| Q-46 | How is `ArrayList` actually asked in a real loop, with model answers said out loud? | partial | `17-`, `18-` |
| Q-47 | What are the predict-the-output puzzles? | partial | `19-` |
| Q-48 | What is the atomic concept checklist for this topic? | partial | `19-` |

**Coverage totals:** 48 asked · 6 `gap` · 22 `partial` · 20 `covered`.

---

## Source ledger

### Repo files harvested (read-only)

| Path | What was taken | Question ids |
|---|---|---|
| `src/notes/detailed/java-collections/array-list/01-internals-a-growth.md` | Field set, the two sentinels as a one-bit identity flag, `grow`/`newLength`/`hugeLength` walk, the 1.5x sequence, `addAll` no-headroom fact, the "`ArrayList` doubles" version trap, JDK-6989669 lazy-allocation history | Q-17, Q-18, Q-31, Q-32 |
| `src/notes/detailed/java-collections/array-list/02-internals-b-mutation.md` | `add(E)`/`add(int,E)` arraycopy walk, `remove(int)`/`fastRemove` and the trailing null, `ensureCapacity` as the single highest-value tuning knob, the "`clear()` releases memory" pitfall | Q-19, Q-20 |
| `src/notes/detailed/java-collections/array-list/02b-internals-bulk-removal.md` | `removeIf` two-pass `deathRow` bitset, `batchRemove` shared engine and its `catch`/`finally` repair, `removeAll(List)` quadratic trap | Q-21 |
| `src/notes/detailed/java-collections/array-list/03-internals-c-views-and-iterators.md` | `SubList` root/parent/offset structure, `Itr`/`ListItr` three-int state, `ArrayListSpliterator` split, `Vector` and `CopyOnWriteArrayList` as the other two array lists | Q-22, Q-23, Q-24, Q-07 |
| `src/notes/detailed/java-collections/array-list/04-amortised-analysis.md` | Amortised-is-not-average framing, the `f/(f-1)` copy bound, why 1.5 not 2, "amortised O(1) is not a latency budget" | Q-28 |
| `src/notes/detailed/java-collections/array-list/05..09-build-my-array-list*.md` | The from-scratch build shape: growth, iterators, views, bulk, sublist, equality, spliterator, and the diff-against-the-JDK discipline | Q-44, Q-45 |
| `src/notes/detailed/java-collections/cost-and-memory/01-master-cost-table.md` | Cross-collection operation cost table shape and the `RandomAccess` cost distinction | Q-27 |
| `src/notes/detailed/java-collections/cost-and-memory/02-internals-memory-headers.md` | Object header arithmetic, compressed oops, 8-byte alignment | Q-26 |
| `src/notes/detailed/java-collections/cost-and-memory/03-internals-memory-collections.md` | Per-collection footprint arithmetic, empty-collection cost, the map-of-empty-lists trap, JOL as the measuring tool | Q-26, Q-29 |
| `src/notes/detailed/java-collections/cost-and-memory/04-observability.md` | How capacity and footprint are observed from outside | Q-15 |
| `src/notes/detailed/java-collections/iteration/01-basics-iteration.md` | `Iterable`/`Iterator`/`ListIterator` state rules, for-each desugaring | Q-14 |
| `src/notes/detailed/java-collections/iteration/02-fail-fast-fail-safe.md` | `modCount`/`expectedModCount`/`checkForComodification`, what counts as structural, the second-to-last-element escape, CME as best-effort, `forEach`/`removeIf` checking once at the end | Q-22, Q-34 |
| `src/notes/detailed/java-collections/iteration/03-internals-spliterator.md` | Spliterator characteristics, `trySplit` contract, `SIZED`/`SUBSIZED` and why they matter to the fork-join splitter | Q-23, Q-39 |
| `src/notes/detailed/java-collections/contracts/01-ordering.md` | `Comparable` contract, consistent-with-equals, `Comparator.comparing`/`thenComparing`/`reversed`, never-subtract-to-compare, `Double.compare` and `NaN`, primitive specializations | Q-36, Q-37 |
| `src/notes/detailed/java-collections/contracts/02-equals-hashcode-contract.md` | The five clauses and the substitutability argument | Q-38 |
| `src/notes/detailed/java-collections/contracts/03-equals-hashcode-jdk.md` | `List.equals`/`List.hashCode` specified algorithms, `AbstractList` reference implementation | Q-38 |
| `src/notes/detailed/java-collections/contracts/04-generics-and-boxing.md` | Erasure inside collections, boxing cost, `Integer` cache | Q-41 |
| `src/notes/detailed/java-collections/contracts/05-wildcards-and-pecs.md` | PECS, why `ArrayList(Collection<? extends E>)` reads the way it does, heap pollution | Q-41 |
| `src/notes/detailed/java-collections/immutable-collections/01-views-copies-snapshots.md` | View vs copy vs snapshot taxonomy, write-through semantics | Q-13, Q-16, Q-43 |
| `src/notes/detailed/java-collections/immutable-collections/01d-arrays-aslist.md` | `Arrays.asList` fixed-size-not-read-only mechanism, the varargs story, the primitive-array trap | Q-13, Q-43 |
| `src/notes/detailed/java-collections/immutable-collections/02-immutable-factories.md` | `List.of` / `List.copyOf` behaviour, null hostility | Q-03, Q-13, Q-43 |
| `src/notes/detailed/java-collections/immutable-collections/02b-entries-snapshots-and-stream-terminals.md` | `stream().toList()` vs `Collectors.toList()` vs `Collectors.toUnmodifiableList()` | Q-12, Q-39 |
| `src/notes/detailed/java-collections/immutable-collections/04c-internals-mutators-serialization-and-views.md` | Which JDK list views are serializable and which are not | Q-42 |
| `src/notes/detailed/java-collections/sequenced-collections/01-sequenced-collections.md` | JEP 431 retrofit map, `reversed()` as a write-through view, source-compatibility fallout | Q-05, Q-16, Q-31 |
| `src/notes/detailed/java-collections/utilities/01-collections-and-arrays.md` | `Collections`/`Arrays` helper surface, `unmodifiableList`, `synchronizedList`, `nCopies` | Q-12, Q-35 |
| `src/notes/detailed/java-collections/utilities/02-sorting-a-timsort.md` | What `Arrays.sort(Object[], …)` runs — TimSort, its galloping merge and its run detection; `"Comparison method violates its general contract!"` | Q-37 |
| `src/notes/detailed/java-collections/utilities/05-streams-and-collectors.md` | Collector sizing, `toList` collector internals | Q-39 |
| `src/notes/detailed/java-collections/utilities/06-serialization.md` | `serialVersionUID` discipline, custom `writeObject`/`readObject` | Q-25, Q-42 |
| `src/notes/detailed/java-collections/framework/01-basics-why-and-hierarchy.md` | The interface hierarchy and the marker interfaces | Q-05, Q-06 |
| `src/notes/detailed/java-collections/framework/02-interface-method-surfaces.md` | Per-interface method inventories (the closest existing thing to row 3 — but with no `Declared in` lineage for a concrete class) | Q-08, Q-09 |
| `src/notes/detailed/java-collections/framework/03-catalogue-a-lists-and-sets.md` | The list implementations side by side | Q-07, Q-33 |
| `src/notes/detailed/java-collections/framework/06-matrices-and-choosing.md` | The choose-a-collection decision matrices | Q-33 |
| `src/notes/detailed/java-collections/framework/07-legacy-a-vector-stack-hashtable.md` | `Vector` doubling, `Stack`, why they are retained | Q-07, Q-32 |
| `src/notes/detailed/java-collections/framework/07-legacy-b-version-history.md` | Framework-level release timeline | Q-31 |
| `src/notes/detailed/java-collections/framework/08-abstract-skeletons.md` | What `AbstractCollection`/`AbstractList` actually implement and at what cost | Q-09 |
| `src/notes/detailed/java-collections/build-it/01-supporting-builds.md` | Build-it harness conventions and the diff-against-JDK table | Q-44 |
| `src/notes/detailed/03-java-core/arrays/01-basics.md` | Array identity, length, default initialisation | Q-26 |
| `src/notes/detailed/03-java-core/arrays/01a-covariance-and-mutability.md` | Array covariance and `ArrayStoreException`, the store check, `final` is not `const` | Q-40 |
| `src/notes/detailed/03-java-core/arrays/01b-array-utilities-and-arraycopy.md` | `System.arraycopy` as an intrinsic, `Arrays.copyOf` semantics | Q-19, Q-20 |
| `src/notes/detailed/03-java-core/arrays/01c-memory-layout-and-bounds.md` | Array header layout, bounds-check elimination | Q-26, Q-27 |
| `src/scenario/scenario.md` | Every example: §3 glossary and status codes, §4 service catalog, §11 ledger model, §12 payment flows, §13 operational runs, §15 Example Bank, Appendix A figures, Appendix C type sketch | all |

**Repo files drawn on: 41.**

### External sources consulted

| Source | Version it describes | Used for |
|---|---|---|
| `java.base/java/util/ArrayList.java` from `/Library/Java/JavaVirtualMachines/jdk-21.jdk/.../lib/src.zip` | **JDK 21.0.7**, 1814 lines. Verified byte-identical (below the licence header) to `openjdk/jdk` tag `jdk-21+35`. | Every field, constant, and method body quoted anywhere in the set |
| `java.base/jdk/internal/util/ArraysSupport.java`, same `src.zip` | JDK 21.0.7 | `newLength`, `hugeLength`, `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` |
| `java.base/java/util/AbstractList.java`, `AbstractCollection.java`, `List.java`, `SequencedCollection.java`, same `src.zip` | JDK 21.0.7 | The `Declared in` lineage and the specified `equals`/`hashCode` algorithms |
| `javap -protected` on `java.util.{ArrayList, AbstractList, AbstractCollection, List, SequencedCollection, Collection, RandomAccess}`, JDK 21.0.7 | JDK 21.0.7 | The authoritative member inventory for row 3 |
| `openjdk/jdk8u` `jdk/src/share/classes/java/util/ArrayList.java` | JDK 8 | `ensureCapacityInternal`/`ensureExplicitCapacity`, `MAX_ARRAY_SIZE`, `hugeCapacity`, the both-sentinels-present state |
| `openjdk/jdk7u` `jdk/src/share/classes/java/util/ArrayList.java` | JDK 7u | Single `EMPTY_ELEMENTDATA`; lazy allocation introduced but **not** yet split |
| `openjdk/jdk9` `jdk/src/java.base/.../ArrayList.java` | JDK 9 | `grow()` returns `Object[]`; `ensureCapacityInternal` removed |
| `openjdk/jdk` tags `jdk-10+46`, `jdk-11+28`, `jdk-12+33`, `jdk-13+33`, `jdk-14+36`, `jdk-17+35` | JDK 10–17 | Narrowing the `ArraysSupport.newLength` adoption to **JDK 13** (present at 13+33, absent at 12+33) |
| Local execution, `jdk-21.jdk` 21.0.7 (`Probe`, `Mem`, `Bench2`, `Grows`) | JDK 21.0.7 on macOS/aarch64 | Growth sequence, `ensureCapacity` no-op, view runtime classes, CME cases, `reversed()` write-through, spliterator characteristics `16464`, measured footprints, measured timings |
| Local execution, `jdk1.8.0_202`, `jdk-11.jdk` 11.0.27, `jdk-17.jdk` 17.0.15 (`TA`) | JDK 8, 11, 17 | The `Arrays.asList(arr).toArray()` runtime-type delta: `String[]` + `ArrayStoreException` on 8, `Object[]` on 11/17/21 |
| `java -XX:+PrintFlagsFinal -version`, JDK 21.0.7 | JDK 21.0.7 | `MaxInlineSize = 35`, `C1MaxInlineSize = 35`, `UseCompressedOops = true`, `UseCompressedClassPointers = true`, `ObjectAlignmentInBytes = 8` |

---

## Verified figures used across the set

Writers take these verbatim. Every one was produced or read in this run; none is
recalled.

| Fact | Value | How verified |
|---|---|---|
| `DEFAULT_CAPACITY` | `10` | JDK 21.0.7 source, `ArrayList.java` line 118 |
| `SOFT_MAX_ARRAY_LENGTH` | `Integer.MAX_VALUE - 8` = 2 147 483 639 | `ArraysSupport.java` line 692 |
| `serialVersionUID` | `8683452581122892189L` | `ArrayList.java` line 113 |
| Default growth sequence | 0 → 10 → 15 → 22 → 33 → 49 → 73 → 109 → 163 → 244 | measured by reflection on JDK 21.0.7 |
| `new ArrayList<>(0)` sequence | 0 → 1 → 2 → 3 → 4 → 6 → 9 → 13 | derived from `newLength`; first six confirmed |
| `new ArrayList<>().ensureCapacity(5)` | capacity stays **0** | measured |
| `new ArrayList<>().ensureCapacity(11)` | capacity becomes **11** | measured |
| Grows from empty to 100 000 elements | **24** `grow` calls, final capacity **106 710**, **213 413** elements copied = **2.13 copies per element**, **6 710** wasted slots | computed from the exact `newLength` recurrence |
| `new ArrayList<>()` footprint, empty | **24 bytes** (12-byte header + `modCount` 4 + `size` 4 + `elementData` ref 4); backing array is a *shared* static zero-length array | arithmetic under measured flags |
| `ArrayList` + 1 element, default ctor | **80 bytes** (24 + 16-byte array header + 10 × 4-byte refs = 24 + 56) | **measured 80.2 bytes/instance** over 200 000 instances |
| `ArrayList` + 1 element, `new ArrayList<>(1)` | **48 bytes** (24 + 16 + 4 → array padded to 24) | **measured 48.1** |
| `LinkedList` + 1 element | **56 bytes** (32-byte list + 24-byte `Node`) | **measured 56.1** |
| 100 000 `add` calls, default ctor | **584 µs** | measured, 10 warm iterations, JDK 21.0.7 |
| 100 000 `add` calls, `new ArrayList<>(100000)` | **358 µs** — a 39 % saving from one constructor argument | measured |
| 200 000-element scan by `get(i)` | **101 µs** | measured |
| 200 000-element `for-each` on `ArrayList` | **103 µs** | measured |
| 200 000-element `for-each` on `LinkedList` | **329 µs** — 3.2× slower with identical O(n) | measured |
| `LinkedList.get(i)` over the first 20 000 of 200 000 | **352 ms** — 3 500× the cost of the whole `ArrayList` scan | measured |
| `ArrayList.spliterator().characteristics()` | `16464` = `ORDERED \| SIZED \| SUBSIZED` | measured |
| `Objects.checkIndex` failure message | `Index 3 out of bounds for length 1` | measured |
| `rangeCheckForAdd` failure message | `Index: 3, Size: 1` — **a different message shape from the same class** | measured |
| `list.reversed()` runtime class | `java.util.ReverseOrderListView$Rand` | measured |
| `reversed().add("Z")` on `[A, B, C]` | original becomes `[Z, A, B, C]` — write-through, and it lands at the **front** | measured |
| `List.of(x)` runtime class | `ImmutableCollections$List12` | measured |
| `List.of(x,y,z)` runtime class | `ImmutableCollections$ListN` | measured |
| `stream().toList()` runtime class | `ImmutableCollections$ListN`, immutable | measured |
| `stream().collect(Collectors.toList())` runtime class | `java.util.ArrayList`, mutable | measured |
| `subList` runtime class | `java.util.ArrayList$SubList` | measured |
| Removing the second-to-last element in a for-each | **no CME**; `[A,B,C,D]` becomes `[A,B,D]` silently | measured |
| `Arrays.asList(strings).toArray()` runtime type | JDK 8: `String[]`, and a store of an `Integer` throws `ArrayStoreException`. JDK 11/17/21: `Object[]`, store succeeds. | measured on all four JDKs |
| `MaxInlineSize` | `35` — the reason `add(E)` is split into a helper | `-XX:+PrintFlagsFinal` |

---

## Diagram manifest

18 diagrams. Flat, topic-scoped, `diagrams/D-NN-slug.svg`. Note files sit at the
topic root alongside `diagrams/`, so they embed them as `diagrams/D-NN-slug.svg` —
**not** `../diagrams/`, which would resolve above the topic root.

| Id | Title | Type | Must show | Caption | Owner |
|---|---|---|---|---|---|
| D-01 | Size is not capacity | annotated array | One `elementData` array of length 10 holding 4 `LedgerEntry` refs and 6 nulls; `size = 4` and `elementData.length = 10` labelled separately; the `[size]` slot marked as the trailing null; annotation panel stating capacity is not a field and has no accessor | `size` counts elements; `elementData.length` is capacity. Only one of the two is in the `List` contract. | `01-` |
| D-02 | Where `ArrayList` sits | layered hierarchy, centre spine | Straight vertical spine `Iterable` → `Collection` → `SequencedCollection` → `List` → `ArrayList`; `AbstractCollection` → `AbstractList` → `ArrayList` on the class side; `RandomAccess`, `Cloneable`, `Serializable` as markers; `LinkedList`, `Vector`, `CopyOnWriteArrayList` as siblings under `List`; version pill `21` on `SequencedCollection` | The spine is the one relationship that matters: every `ArrayList` is a `List`, and since 21 every `List` is a `SequencedCollection`. | `02-` |
| D-03 | Who declares what | grouped panels | Seven declaring types as panels — `Iterable`, `Collection`, `SequencedCollection`, `List`, `AbstractCollection`, `AbstractList`, `ArrayList` — each with its member count and its two or three signature members; arrows showing which `ArrayList` members are overrides rather than fresh declarations | Roughly fifty callable members; `ArrayList` freshly declares only `trimToSize` and `ensureCapacity`. Everything else is an override or an inherited default. | `03-` |
| D-04 | Every route to a list, and what you actually get | decision fan | Four construction routes (`new ArrayList<>()`, `new ArrayList<>(n)`, `new ArrayList<>(c)`, deserialization) and five factory routes (`List.of`, `List.copyOf`, `Arrays.asList`, `stream().toList()`, `Collectors.toList()`); each terminating in a box giving the **runtime class** and the **initial capacity**; mutable routes green, immutable and fixed-size routes grey | Nine ways to obtain a `List`; five of them hand you a real `ArrayList` — the four construction routes plus `Collectors.toList()`. The runtime class is what decides whether `add` throws. | `04-` |
| D-05 | Two empty arrays, one bit of state | two-object comparison | `new ArrayList<>()` arrow to `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`, `new ArrayList<>(0)` arrow to `EMPTY_ELEMENTDATA`; both boxes labelled `Object[0]` and byte-identical; the `==` test in `grow` shown as the only reader; the two first-add outcomes 10 and 1 | Two heap objects with identical contents at different addresses. `grow` reads the address, never the contents. | `05-` |
| D-06 | The 1.5× sequence | timeline with cost spikes | Capacity steps 10, 15, 22, 33, 49, 73, 109, 163, 244 on a horizontal axis; each step annotated `old + (old >> 1)`; a spike per `Arrays.copyOf` whose height is the elements copied; a running-total annotation reaching 2.13 copies per element at n = 100 000 | Spikes get taller and rarer. The area under them is what "amortised O(1)" measures. | `05-`, `10-` |
| D-07 | `add(int, E)` is one `arraycopy` | before / after frames | `elementData` before, holding `LedgerEntry` refs at 0..3 in a capacity-6 array; the single `System.arraycopy(es, index, es, index+1, s-index)` shown as one wide arrow shifting the tail right; the new element written into the freed slot; `size` incremented; cost annotation `O(n - index)` with the named cause | One `arraycopy` moves the whole tail. Inserting at 0 moves everything; inserting at `size` moves nothing. | `06-` |
| D-08 | `fastRemove` and the trailing null | before / after frames | The `arraycopy(es, i+1, es, i, newSize-i)` collapsing the gap left; `es[size = newSize] = null` shown as an explicit store; annotation panel explaining the null exists to release the reference for GC, and that capacity does not shrink | The shift closes the gap; the explicit null is what lets the removed `LedgerEntry` be collected. Capacity is unchanged. | `06-` |
| D-09 | `removeIf`'s two passes | two-phase diagram | Pass one: predicate evaluated over `Restriction` elements, setting bits in a `long[] deathRow` shown as a 64-bit word with bits at the doomed indices; pass two: the compaction that copies survivors left; the `modCount` check between the passes; annotation naming `nBits`, `setBit`, `isClear` | Two passes, not one: mark in a `long[]` bitset, then compact. The `modCount` check sits between them. | `07-` |
| D-10 | Fail-fast in three ints | state diagram | `Itr` fields `cursor`, `lastRet`, `expectedModCount` alongside the list's `modCount`; the four transitions `next()`, `remove()`, list-side `add`, list-side `remove`; the divergence point where `modCount != expectedModCount` shown in the failure palette throwing `ConcurrentModificationException`; annotation panel for the second-to-last-element escape where `cursor == size` and `hasNext()` returns false before the check ever runs | Three ints and one comparison. The escape hatch at the bottom is why fail-fast is documented as best-effort. | `08-` |
| D-11 | `SubList` is an address book | structure diagram | The root `ArrayList` with its `elementData`; a `SubList` holding `root`, `parent`, `offset`, `size`; a nested `SubList` of that `SubList` with its own `offset` relative to the root; every index access shown as `offset + index` into the root's array; annotation stating no elements are copied and that a structural change through the root leaves the view undefined | A view holds four ints and two references. It never copies an element, and the root can invalidate it. | `08-` |
| D-12 | `trySplit` halves the index range | recursive split | An index range 0..200 000 halving to two `ArrayListSpliterator`s, then again; each node labelled with its `index`, `fence`, `estimateSize()`; the shared `elementData` beneath, untouched; the characteristics `ORDERED \| SIZED \| SUBSIZED = 16464` in an annotation panel | Splitting moves two ints. The array is never copied, which is why `ArrayList` parallelises well and `LinkedList` does not. | `09-` |
| D-13 | An `ArrayList` in bytes | memory layout | The `ArrayList` object: 12-byte header, `modCount` 4, `size` 4, `elementData` ref 4 = 24 bytes; the `Object[10]` array: 12-byte header + 4-byte length + 10 × 4-byte refs = 56 bytes; total 80; a second panel showing the `new ArrayList<>(1)` case at 48; a third showing `LinkedList` + one `Node` at 56; all under compressed oops with 8-byte alignment | 80 bytes to hold one reference, under compressed oops. The measured figure matched the arithmetic to 0.2 bytes. | `10-` |
| D-14 | Amortised is not per-call | cost chart | Per-`add` cost as a bar series with spikes at the resize indices; the running average drawn as a flat line converging to ~2.13 copies per element; one spike highlighted in the failure palette and labelled as the p99.99 latency outlier a single request can hit | The flat line is the amortised bound. The tall bar is what one unlucky request pays. | `10-` |
| D-15 | Which list, and why | decision tree | Root question "do you index by position?"; branches to `ArrayList`, `ArrayDeque`, `LinkedList`, `CopyOnWriteArrayList`, `List.of`, `Collections.synchronizedList`; each leaf carrying the one condition that selects it and the cost it accepts; `LinkedList` leaf annotated with the measured 3.2× for-each penalty and the 3 500× `get(i)` penalty | Six leaves. `LinkedList` is reachable, but the condition that selects it is narrower than most people assume. | `11-` |
| D-16 | Seven releases of one class | version timeline | Horizontal timeline 1.2, 7, 8, 9, 13, 16, 21 with the change at each: introduction and the `Vector` retirement; lazy allocation; the sentinel split; `grow` returning `Object[]` plus `Arrays$ArrayList.toArray` returning `Object[]`; `ArraysSupport.newLength` replacing `MAX_ARRAY_SIZE`; `stream().toList()`; `SequencedCollection`. Version pills on each node; the two stale claims (`ArrayList` doubles, `MAX_ARRAY_SIZE` is the cap) called out in an annotation panel | Growth policy has been 1.5× in every released JDK. What moved is where the arithmetic lives. | `13-` |
| D-17 | The runtime type `toArray` hands back | two-frame comparison | Frame A, JDK 8: `Arrays.asList(instrumentIds).toArray()` returning a `String[]` and an `Integer` store throwing `ArrayStoreException` in the failure palette. Frame B, JDK 9+: the same call returning `Object[]` and the store succeeding. Both frames also showing `new ArrayList<>(c).toArray()` returning `Object[]` in **both** versions, via `Arrays.copyOf(a, size, Object[].class)` in the collection constructor | The same source line, two runtime types, one JDK apart. JDK-6260652 is why. | `15-` |
| D-18 | What `list.sort(c)` actually runs | call chain | `list.sort(c)` → `Arrays.sort((E[]) elementData, 0, size, c)` → TimSort; the `modCount` snapshot before and the check after; a parallel lane showing the composed comparator `Comparator.comparing(LedgerEntry::postedAt).thenComparing(LedgerEntry::id)` as a chain of `compare` delegations; annotation naming `IllegalArgumentException: Comparison method violates its general contract!` as TimSort's response to an inconsistent comparator | `sort` hands the backing array straight to TimSort. A broken comparator is detected by the sort, not by the list. | `14-` |

**Sealed file paths.** Note files embed these as `diagrams/<file>`.

| Id | File | Id | File |
|---|---|---|---|
| D-01 | `diagrams/D-01-size-vs-capacity.svg` | D-10 | `diagrams/D-10-fail-fast-itr-state.svg` |
| D-02 | `diagrams/D-02-hierarchy-spine.svg` | D-11 | `diagrams/D-11-sublist-offsets.svg` |
| D-03 | `diagrams/D-03-who-declares-what.svg` | D-12 | `diagrams/D-12-spliterator-trysplit.svg` |
| D-04 | `diagrams/D-04-construction-routes.svg` | D-13 | `diagrams/D-13-memory-layout-bytes.svg` |
| D-05 | `diagrams/D-05-empty-sentinels.svg` | D-14 | `diagrams/D-14-amortised-vs-per-call.svg` |
| D-06 | `diagrams/D-06-growth-sequence.svg` | D-15 | `diagrams/D-15-which-list-decision-tree.svg` |
| D-07 | `diagrams/D-07-add-at-index-arraycopy.svg` | D-16 | `diagrams/D-16-version-timeline.svg` |
| D-08 | `diagrams/D-08-fastremove-trailing-null.svg` | D-17 | `diagrams/D-17-toarray-runtime-type.svg` |
| D-09 | `diagrams/D-09-removeif-deathrow.svg` | D-18 | `diagrams/D-18-sort-call-chain.svg` |

**Illustrator batches:** B1 = D-01..D-04 · B2 = D-05..D-08 · B3 = D-09..D-12 ·
B4 = D-13..D-16 · B5 = D-17, D-18.

---

## File plan

19 note files. Multi-file because the question inventory holds 48 questions across
all fourteen frame rows, with nine distinct mechanisms each needing a source walk;
a single file could not reach 250 lines per mechanism inside the 600-line hard split.

Interview counts, computed at planning time: 19 note files ⇒ **12 + 2 × 13 = 38
Q&As** required, split 19 and 19 across `17-` and `18-`, plus **8** predict-the-output
puzzles in `19-`.

### `01-what-an-array-list-guarantees.md`

| Column | Contents |
|---|---|
| Teaches | The reader can state what an `ArrayList` promises, what it refuses to promise, and why capacity is not part of either. |
| Frame rows | 1 |
| Questions | Q-01, Q-02, Q-03, Q-04 |
| Primary concepts | The positional-index contract; the four non-guarantees (thread-safety, iteration stability, ordering-by-value, capacity); the null policy; size versus capacity |
| Sources | `ArrayList.java` class Javadoc and `@since 1.2` tag, JDK 21.0.7; `List.java` interface Javadoc; measured probe output for `List.of(null)` NPE and empty-`getFirst()` `NoSuchElementException` |
| Diagrams | D-01 — `size` counts elements; `elementData.length` is capacity. Only one of the two is in the `List` contract. |
| Examples | `Movement.entries` as a `List<LedgerEntry>` (Appendix C.2): order is the posting order, duplicates are legal because two 4.20 stake debits are genuinely two entries, and the sum-to-zero invariant is the list's job to preserve. Nulls illustrated with an unattributed `Position` reference in a suspense movement. |
| Assumes | `Assumes: no prior knowledge of ArrayList.` |
| Sets up | `Next: where ArrayList sits among its supertypes and siblings, and what RandomAccess buys.` |
| Previous | — |
| Next | `02-position-in-the-collections-map.md` |
| Est. lines | 300 |
| Status | written |
| Lines | 476 |

### `02-position-in-the-collections-map.md`

| Column | Contents |
|---|---|
| Teaches | The reader can place `ArrayList` on the hierarchy from memory, say what each marker interface buys, and name every sibling with its one distinguishing job. |
| Frame rows | 2 |
| Questions | Q-05, Q-06, Q-07 |
| Primary concepts | The interface spine `Iterable` → `Collection` → `SequencedCollection` → `List`; the abstract-class spine `AbstractCollection` → `AbstractList`; `RandomAccess` as a behavioural marker; the sibling family |
| Sources | `javap -protected` output for the seven types, JDK 21.0.7; `RandomAccess` Javadoc and its named consumers (`Collections.binarySearch`, `Collections.shuffle`, `Collections.fill`, `Collections.reverse`); `SequencedCollection.java`, JDK 21.0.7 |
| Diagrams | D-02 — The spine is the one relationship that matters: every `ArrayList` is a `List`, and since 21 every `List` is a `SequencedCollection`. |
| Examples | `Movement.entries`, `PaymentRun.itemIds` and the reservation-expiry index (Appendix C.6) as three list-shaped fields that resolve to three different implementations. `ProfileService` assembling from eight owners as the case where the declared type must be `List`, not `ArrayList`. |
| Assumes | `Assumes: the size-versus-capacity distinction and the four non-guarantees (file 01).` |
| Sets up | `Next: the complete member surface, and which of those supertypes each member came from.` |
| Previous | `01-what-an-array-list-guarantees.md` |
| Next | `03-the-complete-member-surface.md` |
| Est. lines | 330 |
| Status | written |
| Lines | 515 |

### `03-the-complete-member-surface.md`

| Column | Contents |
|---|---|
| Teaches | The reader can name the declaring type of any `ArrayList` member and say what that lineage implies about its cost and its optionality. |
| Frame rows | 3 |
| Questions | Q-08, Q-09, Q-10 |
| Primary concepts | The complete member table with `Declared in` lineage; what each declaring type contributes; the overrides that change cost; optional operations and `UnsupportedOperationException` |
| Sources | `javap -protected` for `ArrayList`, `AbstractList`, `AbstractCollection`, `List`, `SequencedCollection`, `Collection`, `Iterable`, `RandomAccess` on JDK 21.0.7 (pasted in full into the writer packet); `AbstractCollection.java` `toArray`/`containsAll`/`toString` bodies; `AbstractList.java` `modCount` declaration |
| Diagrams | D-03 — Roughly fifty callable members; `ArrayList` freshly declares only `trimToSize` and `ensureCapacity`. Everything else is an override or an inherited default. |
| Examples | The table's `Notes` column grounded on `List<LedgerEntry>`: `contains` is O(n) because it calls `LedgerEntry.equals` per slot; `containsAll` inherited from `AbstractCollection` is O(n·m) and that is why lifting 38 000 restrictions a day must not go through it. |
| Assumes | `Assumes: the hierarchy spine and the meaning of RandomAccess (file 02).` |
| Sets up | `Next: how you get one — the three constructors, the copy paths, and the factories that give you something else entirely.` |
| Previous | `02-position-in-the-collections-map.md` |
| Next | `04-constructors-and-factories.md` |
| Est. lines | 420 |
| Status | written |
| Lines | 600 |

### `04-constructors-and-factories.md`

| Column | Contents |
|---|---|
| Teaches | The reader can predict the runtime class and the initial capacity of any list-producing expression, and pick the construction form that costs least. |
| Frame rows | 4 |
| Questions | Q-11, Q-12, Q-13 |
| Primary concepts | The three constructors and their capacities; the collection constructor's `getClass() == ArrayList.class` fast path; the routes that give an `ArrayList` versus the routes that do not; `clone` and deserialization as construction |
| Sources | `ArrayList.java` lines 154–188 (three constructors) and 342–360 (`clone`), JDK 21.0.7; measured runtime classes for all nine routes; measured `new ArrayList<>(0)` capacity 0 and `ensureCapacity(5)` no-op |
| Diagrams | D-04 — Nine ways to obtain a `List`; five of them hand you a real `ArrayList` — the four construction routes plus `Collectors.toList()`. The runtime class is what decides whether `add` throws. |
| Examples | A `Movement` holds 2–4 `LedgerEntry` (Appendix A.3), so `new ArrayList<>(4)` is exactly right and `new ArrayList<>()` over-allocates 6 slots × 19.8M entries/day. A `PaymentRun` file carries 1 800 items (Appendix A.5), so `new ArrayList<>(1800)` versus the default's 24 grow calls. |
| Assumes | `Assumes: the member surface and which members are optional operations (file 03).` |
| Sets up | `Next: the three fields and one arithmetic expression that everything so far actually rests on.` |
| Previous | `03-the-complete-member-surface.md` |
| Next | `05-internals-fields-sentinels-and-growth.md` |
| Est. lines | 340 |
| Status | written |
| Lines | 424 |

### `05-internals-fields-sentinels-and-growth.md`

| Column | Contents |
|---|---|
| Teaches | The reader can recite the field set, explain why two identical empty arrays exist, and compute any capacity in the growth sequence by hand. |
| Frame rows | 6, 7 (growth cost) |
| Questions | Q-17, Q-18 |
| Primary concepts | The three-field representation; the two empty sentinels as one bit of state read by `==`; `grow` delegating to `ArraysSupport.newLength`; the 1.5× sequence and `SOFT_MAX_ARRAY_LENGTH`/`hugeLength` |
| Sources | `ArrayList.java` lines 113–145 (fields), 199–245 (`trimToSize`, `ensureCapacity`, `grow`), JDK 21.0.7; `ArraysSupport.java` lines 692, 735, 749; measured growth sequences for both constructors; the computed 24-grows / 213 413-copies figure |
| Diagrams | D-05 — Two heap objects with identical contents at different addresses. `grow` reads the address, never the contents. · D-06 — Spikes get taller and rarer. The area under them is what "amortised O(1)" measures. |
| Examples | A `PaymentRun.itemIds` list filled from a 1 800-record payout file: the exact capacity walk 10, 15, 22, … 2 481 and the elements copied, versus `new ArrayList<>(1800)`. `trimToSize` after the run closes and the list becomes read-only. |
| Assumes | `Assumes: the three constructors and the capacities they start from (file 04).` |
| Sets up | `Next: what a single add or remove does to that array — one arraycopy, and one deliberate null.` |
| Previous | `04-constructors-and-factories.md` |
| Next | `06-internals-add-remove-and-the-trailing-null.md` |
| Est. lines | 430 |
| Status | written |
| Lines | 437 |

### `06-internals-add-remove-and-the-trailing-null.md`

| Column | Contents |
|---|---|
| Teaches | The reader can walk `add(E)`, `add(int, E)`, `remove(int)` and `remove(Object)` statement by statement and say what each costs and why. |
| Frame rows | 6, 7 |
| Questions | Q-19, Q-20 |
| Primary concepts | `add(E)` and the `MaxInlineSize` helper split; `add(int, E)` as one `System.arraycopy`; `fastRemove` and the explicit trailing null; `remove(Object)` and its labelled-break scan |
| Sources | `ArrayList.java` lines 426–600 (`get`, `set`, both `add`, `remove(int)`, `removeFirst`, `removeLast`) and 695–740 (`remove(Object)`, `fastRemove`, `clear`), JDK 21.0.7; the `MaxInlineSize = 35` flag reading; the two distinct out-of-bounds message shapes, measured |
| Diagrams | D-07 — One `arraycopy` moves the whole tail. Inserting at 0 moves everything; inserting at `size` moves nothing. · D-08 — The shift closes the gap; the explicit null is what lets the removed `LedgerEntry` be collected. Capacity is unchanged. |
| Examples | Inserting a correcting `LedgerEntry` at index 0 of a `Movement`'s entries versus appending it — and why the ledger's append-only invariant (§11.7) makes the append the only correct one anyway. Removing a lifted `Restriction` by value from a client's restriction list. |
| Assumes | `Assumes: the field set, the sentinels, and how grow computes capacity (file 05).` |
| Sets up | `Next: what happens when you remove many elements at once, and the bitset the JDK reaches for.` |
| Previous | `05-internals-fields-sentinels-and-growth.md` |
| Next | `07-internals-bulk-removal-and-exception-safety.md` |
| Est. lines | 410 |
| Status | written |
| Lines | 430 |

### `07-internals-bulk-removal-and-exception-safety.md`

| Column | Contents |
|---|---|
| Teaches | The reader can explain why `removeIf` needs two passes and a `long[]`, and what `batchRemove`'s `catch` block repairs. |
| Frame rows | 6, 7, 10 |
| Questions | Q-21 |
| Primary concepts | `removeIf`'s `deathRow` bitset and its two passes; `batchRemove` as the shared engine for `removeAll`/`retainAll`; the exception-safety repair in `catch` and `finally`; the `removeAll(List)` quadratic trap |
| Sources | `ArrayList.java` lines 728–760 (`nBits`/`setBit`/`isClear`, `removeIf`), 817–835 (`removeRange`, `shiftTailOverGap`), 872–935 (`removeAll`, `retainAll`, `batchRemove`), JDK 21.0.7 |
| Examples | Lifting expired restrictions from a client's `List<Restriction>` with `removeIf(r -> r.expiresAt().isBefore(now))` at 38 000 applied-and-lifted per day (Appendix A.5). `retainAll` against a `Set` of reversible restriction keys, and the same call against a `List` turning O(n) into O(n·m). |
| Diagrams | D-09 — Two passes, not one: mark in a `long[]` bitset, then compact. The `modCount` check sits between them. |
| Assumes | `Assumes: the arraycopy shift and the trailing null (file 06).` |
| Sets up | `Next: how iteration sees all of this, why it throws, and what a subList view really holds.` |
| Previous | `06-internals-add-remove-and-the-trailing-null.md` |
| Next | `08-iteration-fail-fast-and-views.md` |
| Est. lines | 370 |
| Status | written |
| Lines | 345 |

### `08-iteration-fail-fast-and-views.md`

| Column | Contents |
|---|---|
| Teaches | The reader can predict whether a given mutation-during-iteration throws, and can say exactly what a `subList` or `reversed()` view holds and when it becomes undefined. |
| Frame rows | 5, 6 |
| Questions | Q-14, Q-16, Q-22, Q-24 |
| Primary concepts | `Itr`'s three ints and `checkForComodification`; the `ListIterator` state rules; `SubList`'s `root`/`parent`/`offset`; `reversed()` as a write-through view |
| Sources | `ArrayList.java` lines 1004–1190 (`listIterator`, `Itr`, `ListItr`), 1189–1230 and 1481–1507 (`subList`, `SubList` fields, `checkForComodification`, `updateSizeAndModCount`), JDK 21.0.7; `AbstractList.java` `subListRangeCheck`; the measured second-to-last-element escape; the measured `ReverseOrderListView$Rand` class and its write-through behaviour |
| Diagrams | D-10 — Three ints and one comparison. The escape hatch at the bottom is why fail-fast is documented as best-effort. · D-11 — A view holds four ints and two references. It never copies an element, and the root can invalidate it. |
| Examples | The `AA-700` review queue (40 operators, 22 cases/hour, Appendix A.1): iterating `List<ReviewCase>` and removing the assigned ones, and the CME that follows. `subList` for the "show me all my withdrawals" pagination problem (§7.3), and why the view must not outlive the request. |
| Assumes | `Assumes: single- and bulk-mutation mechanics, including modCount increments (files 06, 07).` |
| Sets up | `Next: the other two traversal mechanisms — splitting for parallel streams, and the wire format.` |
| Previous | `07-internals-bulk-removal-and-exception-safety.md` |
| Next | `09-internals-spliterator-and-serialization.md` |
| Est. lines | 450 |
| Status | written |
| Lines | 460 |

### `09-internals-spliterator-and-serialization.md`

| Column | Contents |
|---|---|
| Teaches | The reader can explain why `ArrayList` parallelises cheaply and can describe its wire format from the `writeObject` source. |
| Frame rows | 6 |
| Questions | Q-23, Q-25 |
| Primary concepts | `ArrayListSpliterator`'s lazy fence and `trySplit`; the `ORDERED \| SIZED \| SUBSIZED` characteristics and what each buys; `writeObject`/`readObject` given a `transient` backing array |
| Sources | `ArrayList.java` lines 1590–1725 (`forEach`, `spliterator`, `ArrayListSpliterator` including its 30-line design comment) and 937–1000 (`writeObject`, `readObject`), JDK 21.0.7; the measured characteristics value `16464` and the measured `trySplit` size halving |
| Diagrams | D-12 — Splitting moves two ints. The array is never copied, which is why `ArrayList` parallelises well and `LinkedList` does not. |
| Examples | The 3 400/sec settlement burst (Appendix A.2) split across a fork-join pool as a `List<LedgerEntry>` parallel stream, and why `SIZED` is what lets the splitter pre-size its work units. Serializing a closed `PaymentRun`'s `itemIds` and the capacity-versus-size question the format answers. |
| Assumes | `Assumes: Itr's cursor/modCount protocol and the view structure (file 08).` |
| Sets up | `Next: what all of this costs — in nanoseconds, in bytes, and in the latency one unlucky request pays.` |
| Previous | `08-iteration-fail-fast-and-views.md` |
| Next | `10-cost-and-memory.md` |
| Est. lines | 350 |
| Status | written |
| Lines | 407 |

### `10-cost-and-memory.md`

| Column | Contents |
|---|---|
| Teaches | The reader can state the cost of every operation with its named cause, compute an `ArrayList`'s footprint in bytes, and say precisely what the amortised bound does not promise. |
| Frame rows | 5 (observation), 7 |
| Questions | Q-15, Q-26, Q-27, Q-28, Q-29 |
| Primary concepts | The complete cost table with constant factors; the byte-level memory layout; amortised O(1) and what it refuses to promise; observing capacity and footprint from outside |
| Sources | All measured figures in `## Verified figures used across the set`; `-XX:+PrintFlagsFinal` readings for `UseCompressedOops`, `UseCompressedClassPointers`, `ObjectAlignmentInBytes`; the reflection-on-`elementData` technique; JOL and `jcmd GC.class_histogram` as the external tools |
| Diagrams | D-06 (reused) — Spikes get taller and rarer. The area under them is what "amortised O(1)" measures. · D-13 — 80 bytes to hold one reference, under compressed oops. The measured figure matched the arithmetic to 0.2 bytes. · D-14 — The flat line is the amortised bound. The tall bar is what one unlucky request pays. |
| Examples | The 90-day hot window over 19.8M ledger entries/day at ~180 bytes a row (Appendix A.3): what an in-memory `ArrayList<LedgerEntry>` index would actually cost, and why the answer rules the design out. The 1 200/sec stake-reservation path as the place a resize spike lands on a p99.9. |
| Assumes | `Assumes: growth arithmetic (file 05), the arraycopy shift (file 06), and the spliterator's SIZED guarantee (file 09).` |
| Sets up | `Next: given those costs, when ArrayList is the right answer and which named type wins when it is not.` |
| Previous | `09-internals-spliterator-and-serialization.md` |
| Next | `11-choosing-array-list-and-its-alternatives.md` |
| Est. lines | 440 |
| Status | written |
| Lines | 471 |

### `11-choosing-array-list-and-its-alternatives.md`

| Column | Contents |
|---|---|
| Teaches | The reader can defend a list choice with a measured reason, and can say why `LinkedList` loses even the cases big-O gives it. |
| Frame rows | 7 (locality), 9 |
| Questions | Q-30, Q-33 |
| Primary concepts | The decision tree and its selecting conditions; why locality beats pointer-chasing at equal big-O; `ArrayDeque` as the real answer to head insertion; the concurrent and immutable alternatives |
| Sources | Measured `for-each` 103 µs versus 329 µs; measured `LinkedList.get(i)` 352 ms over 20 000; the 24-byte-versus-40-byte-per-element arithmetic; `ArrayDeque` and `CopyOnWriteArrayList` class Javadoc, JDK 21.0.7 |
| Diagrams | D-15 — Six leaves. `LinkedList` is reachable, but the condition that selects it is narrower than most people assume. |
| Examples | Three QuizStakes fields, three answers: `Movement.entries` (2–4, immutable after posting) → `List.of`; the bank-deposit ingestion queue (§15.1 producer–consumer, 500 000-record month-end file) → `ArrayDeque`; the agreement cache read on every screen → not a list at all. `PaymentRun.itemIds` → pre-sized `ArrayList`. |
| Assumes | `Assumes: the cost table, the footprint arithmetic, and the measured traversal figures (file 10).` |
| Sets up | `Next: the ways a correct-looking ArrayList usage still takes production down.` |
| Previous | `10-cost-and-memory.md` |
| Next | `12-failure-modes-in-production.md` |
| Est. lines | 340 |
| Status | written |
| Lines | 424 |

### `12-failure-modes-in-production.md`

| Column | Contents |
|---|---|
| Teaches | The reader can name the `ArrayList` misuses that pass code review and tests, describe the production symptom each produces, and give the fix. |
| Frame rows | 10 |
| Questions | Q-34, Q-35 |
| Primary concepts | Unbounded growth as an OOM source; the retained-capacity leak; what concurrent mutation actually produces (lost writes, nulls, `ArrayIndexOutOfBoundsException`, a corrupted `size`); the view that outlives its root |
| Sources | The `grow`/`size` non-atomicity in the JDK 21.0.7 source as the mechanism for every concurrency symptom; `clear()` not shrinking `elementData`; `SubList`'s undefined-behaviour clause; `Collections.synchronizedList` iterator caveat |
| Diagrams | none — every failure here is a code-and-symptom pair, and D-10 and D-13 already carry the two pictures this file leans on |
| Examples | §15.1 race condition: two threads appending `LedgerEntry` to one shared `ArrayList` during the 3 400/sec settlement burst — the interleaving that loses an entry and the one that writes a null, breaking the sum-to-zero invariant (§14.2). §15.5 partial failure: accumulating all 500 000 month-end bank records in one `ArrayList` before processing. The retained-capacity leak on a long-lived `PaymentRun` list after `clear()`. |
| Assumes | `Assumes: the add/grow mechanism (files 05, 06), the fail-fast protocol (file 08), and the footprint arithmetic (file 10).` |
| Sets up | `Next: which of the things you now know were different in earlier JDKs, and which stale claims interviewers still ask for.` |
| Previous | `11-choosing-array-list-and-its-alternatives.md` |
| Next | `13-version-history-and-stale-claims.md` |
| Est. lines | 380 |
| Status | written |
| Lines |      447 |

### `13-version-history-and-stale-claims.md`

| Column | Contents |
|---|---|
| Teaches | The reader can date any `ArrayList` behaviour to a JDK release and can answer a stale-premise interview question without either agreeing to the error or dodging it. |
| Frame rows | 8 |
| Questions | Q-31, Q-32 |
| Primary concepts | The seven-release delta table; the four stale claims and what is true today; how to answer a question whose premise is a pre-Java-9 `ArrayList` |
| Sources | JDK 7u, 8, 9, 10+46, 11+28, 12+33, 13+33, 14+36, 17+35 and 21.0.7 `ArrayList.java`, all read in this run — the `newLength` adoption narrowed to JDK 13 by bisecting those tags; the measured JDK 8 versus 11/17/21 `toArray` runtime-type delta; JEP 269 (Java 9), `Stream.toList` (Java 16), JEP 431 (Java 21) |
| Diagrams | D-16 — Growth policy has been 1.5× in every released JDK. What moved is where the arithmetic lives. |
| Examples | `Movement.entries` declared immutable in Appendix C.6: the pre-9 `Collections.unmodifiableList(new ArrayList<>(…))` form, the Java 9 `List.of` form, and the Java 16 `stream().toList()` form, side by side. `entries.getFirst()` as a Java 21 replacement for `entries.get(0)`. |
| Assumes | `Assumes: the current mechanism in full (files 05 through 09) — you cannot see what changed without knowing what it changed to.` |
| Sets up | `Next: the ordering backbone that list.sort depends on, and how a List decides it equals another List.` |
| Previous | `12-failure-modes-in-production.md` |
| Next | `14-backbone-ordering-equality-and-comparators.md` |
| Est. lines | 350 |
| Status | written |
| Lines | 430 |

### `14-backbone-ordering-equality-and-comparators.md`

| Column | Contents |
|---|---|
| Teaches | The reader can write a correct `Comparable` and a composed `Comparator`, explain what `list.sort` runs, and recite the specified `List.equals`/`hashCode` algorithms. |
| Frame rows | 11 |
| Questions | Q-36, Q-37, Q-38 |
| Primary concepts | The `Comparable.compareTo` contract and consistency with `equals`; `Comparator` composition and the never-subtract rule; what `list.sort(c)` runs and how the `modCount` check brackets it; the specified `List.equals`/`hashCode` and `ArrayList`'s faster private paths |
| Sources | `ArrayList.java` lines 598–690 (`equals`, `equalsRange`, `equalsArrayList`, `hashCode`, `hashCodeRange`) and 1802–1809 (`sort`), JDK 21.0.7; `List.java` `equals`/`hashCode` specified algorithms; `AbstractList.java` reference implementations; `Comparable`/`Comparator` Javadoc; TimSort's `IllegalArgumentException` message |
| Diagrams | D-18 — `sort` hands the backing array straight to TimSort. A broken comparator is detected by the sort, not by the list. |
| Examples | Sorting a `List<LedgerEntry>` by `postedAt` then `id` for the reconciliation report (§14.3). `Money.compareTo` across two currencies as the consistent-with-equals trap (Appendix C.1: value equality includes currency, so a comparator on `amount` alone is inconsistent with it). Ordering `WithdrawalTransaction` for the payout file (§13). |
| Assumes | `Assumes: the member surface, including where sort, equals and hashCode are declared (file 03), and the modCount protocol (file 08).` |
| Sets up | `Next: how ArrayList composes with the rest of the platform — streams, arrays, generics, and the wire.` |
| Previous | `13-version-history-and-stale-claims.md` |
| Next | `15-interoperation-streams-arrays-and-generics.md` |
| Est. lines | 420 |
| Status | written |
| Lines | 469 |

### `15-interoperation-streams-arrays-and-generics.md`

| Column | Contents |
|---|---|
| Teaches | The reader can predict the runtime type and mutability of any list-or-array conversion, and can name the erasure and covariance traps that only fail at runtime. |
| Frame rows | 12 |
| Questions | Q-39, Q-40, Q-41, Q-42, Q-43 |
| Primary concepts | Stream interop and the three `toList` forms; the `toArray` covariance trap and its Java 9 change; erasure inside `ArrayList` — the unchecked casts, `toArray(T[])`, heap pollution; serialization hazards and the views that are not serializable; `Arrays.asList` and `List.of` semantics |
| Sources | Measured runtime classes for `stream().toList()`, `Collectors.toList()`, `List.of`, `List.copyOf`, `Arrays.asList`, `subList`, `unmodifiableList`; the measured JDK 8 versus 9+ `toArray` delta including the `ArrayStoreException`; `ArrayList.java` lines 368–415 (`toArray`, `toArray(T[])`, `elementData`, `elementAt`) and 180–188 (`Arrays.copyOf(a, size, Object[].class)`); `Collection.toArray(IntFunction)` since 11 |
| Diagrams | D-17 — The same source line, two runtime types, one JDK apart. JDK-6260652 is why. |
| Examples | Collecting a stake-settlement stream into `List<LedgerEntry>` three ways and what each returns. `entries.toArray(new LedgerEntry[0])` for the payout-file writer, and why the zero-length form is the right one. A `List<Money>` and the erasure that lets a raw-typed adapter put a `String` in it, surfacing as a `ClassCastException` in the ledger rather than at the adapter. Serializing a `subList` of `PaymentRun.itemIds` and the `NotSerializableException` that follows. |
| Assumes | `Assumes: the spliterator characteristics and the wire format (file 09), the view structure (file 08), and the toArray members' lineage (file 03).` |
| Sets up | `Next: build one from scratch and measure it, which is the only way to know you have understood the preceding fourteen files.` |
| Previous | `14-backbone-ordering-equality-and-comparators.md` |
| Next | `16-prove-it-build-and-measure.md` |
| Est. lines | 460 |
| Status | written |
| Lines | 490 |

### `16-prove-it-build-and-measure.md`

| Column | Contents |
|---|---|
| Teaches | The reader can implement an array-backed list with growth, fail-fast iteration and a view, and can reproduce every measurement in this set. |
| Frame rows | 13 |
| Questions | Q-44, Q-45 |
| Primary concepts | The from-scratch build — representation, growth, structural mutation, fail-fast iterator, a `subList` view; the measurement harness; the diff against the JDK |
| Sources | The full JDK 21.0.7 source as the reference to diff against; the four probe programs run in this set (growth trace, footprint measurement, timing benchmark, grow-count computation) with their real output |
| Diagrams | none — this file's artefact is runnable code and its real output, and every picture it would want is already in D-05 through D-14 |
| Examples | `LedgerEntryList` — an array-backed list of `LedgerEntry` with the ledger's append-only bias, built from scratch. Measured against a real `ArrayList` at the 1 800-item payout-file size and the 500 000-record month-end size (Appendix A.5). |
| Assumes | `Assumes: everything from files 01 through 15 — this file assembles them rather than introducing anything.` |
| Sets up | `Next: the interview surface — how this is actually asked, and the answers said out loud.` |
| Previous | `15-interoperation-streams-arrays-and-generics.md` |
| Next | `17-interview-a-questions.md` |
| Est. lines | 480 |
| Status | written |
| Lines | 583 |

### `17-interview-a-questions.md`

| Column | Contents |
|---|---|
| Teaches | The reader can answer the first nineteen `ArrayList` interview questions out loud, in the order a loop asks them. |
| Frame rows | 14 |
| Questions | Q-46 (first half) |
| Primary concepts | The summary table for the whole set; Q&As 1–19 covering contract, hierarchy, surface, construction, growth, mutation, bulk removal — each with the question as phrased in a real loop, the answer said out loud, and the follow-up |
| Sources | Files 01 through 07 of this set, plus every measured figure |
| Diagrams | none — an interview file is a recall surface, and every diagram it would reference is one click away in the file that owns it |
| Examples | Answers grounded on `Movement.entries`, `PaymentRun.itemIds` and the `List<Restriction>` lifting path, so the reader has one worked domain to reach for under pressure. |
| Assumes | `Assumes: files 01 through 16 in full — this file only recalls.` |
| Sets up | `Next: the remaining nineteen questions — cost, choice, failure, versions, ordering, interop.` |
| Previous | `16-prove-it-build-and-measure.md` |
| Next | `18-interview-b-questions.md` |
| Est. lines | 450 |
| Status | written |
| Lines | 538 |

### `18-interview-b-questions.md`

| Column | Contents |
|---|---|
| Teaches | The reader can answer the remaining nineteen questions, including the ones whose premise is wrong. |
| Frame rows | 14 |
| Questions | Q-46 (second half) |
| Primary concepts | Q&As 20–38 covering iteration and views, spliterator and serialization, cost and memory, choosing, failure modes, version history, ordering, interoperation; and the technique for answering a question built on a stale premise |
| Sources | Files 08 through 16 of this set, plus every measured figure |
| Diagrams | none — same reason as `17-` |
| Examples | Same three domain slices as `17-`, continued, so the two files read as one interview. |
| Assumes | `Assumes: files 01 through 16 in full, and questions 1 to 19 (file 17).` |
| Sets up | `Next: eight predict-the-output puzzles and the atomic concept checklist.` |
| Previous | `17-interview-a-questions.md` |
| Next | `19-interview-c-puzzles-and-checklist.md` |
| Est. lines | 450 |
| Status | written |
| Lines | 468 |

### `19-interview-c-puzzles-and-checklist.md`

| Column | Contents |
|---|---|
| Teaches | The reader can predict the output of eight adversarial snippets and can audit their own recall against a flat checklist. |
| Frame rows | 14 |
| Questions | Q-47, Q-48 |
| Primary concepts | Eight predict-the-output puzzles with the real output and the mechanism that produces it; the atomic concept checklist |
| Sources | Every measured behaviour in this run — the second-to-last-element CME escape, the two out-of-bounds message shapes, `ensureCapacity` no-op, `reversed().add`, `Arrays.asList.set` writing through to the array, `List.of(null)`, `Collectors.toList()` mutability, the JDK 8 `ArrayStoreException` |
| Diagrams | none — a puzzle whose picture is drawn for you is not a puzzle |
| Examples | Puzzles posed on `List<LedgerEntry>`, `List<Restriction>` and the `AA-700` review queue. |
| Assumes | `Assumes: files 01 through 18 in full.` |
| Sets up | `Next: nothing — this is the last file. Re-read path is in the map.` |
| Previous | `18-interview-b-questions.md` |
| Next | — |
| Est. lines | 400 |
| Status | written |
| Lines | 514 |

**Seal check.** Every one of Q-01…Q-48 appears in exactly one row (Q-46 is
deliberately split across `17-` and `18-` as first and second half, and is counted
once). Every manifest id D-01…D-18 appears in at least one row; D-06 appears in two
(`05-` and `10-`) and is authored once. Every row names two to six primary concepts.
No concept straddles two rows. No `Assumes` line references a later file. The
`Previous`/`Next` chain runs unbroken from `01-` to `19-`.

---

## Reading order

### Front to back

`01` → `02` → `03` → `04` → `05` → `06` → `07` → `08` → `09` → `10` → `11` → `12`
→ `13` → `14` → `15` → `16` → `17` → `18` → `19`.

Three natural stopping points. After `04` you can use `ArrayList` correctly. After
`10` you can defend it in a design review. After `16` you have built one.

### The night before

1. `19-interview-c-puzzles-and-checklist.md` — the whole atomic concept checklist. Anything you cannot answer, follow its cross-reference.
2. `05-` § the 1.5× sequence, and its cheat sheet. The growth numbers are the single most-asked thing here.
3. `10-` cheat sheet — the cost table and the byte arithmetic.
4. `13-` § the four stale claims. This is where an interviewer's wrong premise is answered without a fight.
5. `08-` § the second-to-last-element escape. The most common puzzle in the set.
6. `03-` cheat sheet only — the declaring-type lineage, skimmed. Do not re-read the table.
7. `17-` and `18-`, questions only, answers folded. Say them out loud.

---

## Open questions

- **`13-version-history-and-stale-claims.md`** — the claim that no released Java 22–25 collections-API change touches `ArrayList` rests on the absence of a release note or JEP naming `ArrayList` in that window, not on a line-by-line source diff. It is marked `**Unverified:**` inline. **What would settle it:** diff `java/util/ArrayList.java` between openjdk tags `jdk-21+35` and the `jdk-25` GA tag.
- **`15-interoperation-streams-arrays-and-generics.md`** — the runtime class of `Collectors.toUnmodifiableList()` was originally unverifiable. **Settled during this run:** measured on JDK 21.0.7 as `java.util.ImmutableCollections$List12` at one or two elements and `$ListN` beyond — the same family as `List.of` and the same class `stream().toList()` returns, yet it rejects nulls where `stream().toList()` accepts them. No open question remains.
- **`12-failure-modes-in-production.md`** — the concurrency demonstration's numbers were originally unverifiable. **Settled during this run:** the reproduction was executed on JDK 21.0.7 (four threads, 25 000 appends each, `CountDownLatch` release) and five consecutive real runs replaced the placeholder figures. Roughly 70 % of appends were lost every run, nulls appeared inside `[0, size)` every run (298 to 2 934), and `ArrayIndexOutOfBoundsException` surfaced in two runs of five. No open question remains.
