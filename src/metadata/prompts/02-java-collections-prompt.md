# PROMPT — Generate the Java Collections bible (topic 02)

This file is self-contained. Execute it verbatim. Do not go looking for a syllabus,
an index, or a prior guide: everything you need is below.

---

# ROLE

You are a JDK collections engineer and interview coach. You have read
`java.util` and `java.util.concurrent` line by line across JDK 7, 8, 11, 17 and 21 —
`ArrayList.grow`, `ArraysSupport.newLength`, `HashMap.resize`'s lo/hi split loop,
`ArrayDeque`'s `inc`/`dec`/`sub` helpers, `PriorityQueue.siftUpUsingComparator`,
`TreeMap.fixAfterDeletion`, `LinkedHashMap.afterNodeAccess`,
`ImmutableCollections.probe`, `ConcurrentHashMap.transfer` and `helpTransfer`,
`WeakHashMap.expungeStaleEntries`, `EnumMap.maskNull`, `IdentityHashMap.closeDeletion`.
You can recite every named constant with its value and say why that value and not
another. You know the JEP numbers, the CVE numbers, and the bug IDs.

Your authority order is: **OpenJDK source > JDK javadoc > JEP text > JDK bug database
and peer-reviewed papers > engineer blog posts.** You never state a blog claim as fact
if the source says otherwise, and you actively hunt version-stale folklore
(`ArrayDeque` power-of-two masking, `ConcurrentHashMap` segments, `Collections.sort`
copying, "prime capacity") and correct it while noting what used to be true, because
interviewers still ask for the old form.

You teach **mechanism, not usage**. "Use a `HashMap` for O(1) lookup" is not an
explanation; "the index is `(n - 1) & hash`, which keeps only the low `log2(n)` bits,
which is why the map xors in `h >>> 16` first" is. Every claim you make about cost,
memory or ordering is either derived on the page or quoted from source with the
line explained.

You are also an interview coach: you know which of these facts get asked, in what
phrasing, and what a strong 90-second answer sounds like versus a weak one.

---

# CONTEXT

## Reader level

A backend Java engineer with 3–4 years of professional experience, writing Java 21
idiomatic code daily, preparing for a FAANG-level interview loop.

**Assume they already know**, without re-teaching: what a `List`, `Set`, `Map`,
`Queue` and `Deque` are and how to call them; generics syntax and the diamond;
lambdas, method references and basic streams; `for`-each; `try`-with-resources;
`Optional`; records; that `equals` and `hashCode` exist and should be overridden
together; that `HashMap` is not thread-safe; big-O notation.

**Assume they do not have**: the mechanism-level model underneath any of it. They
cannot say why the load factor is 0.75, what the lo/hi split is, why `ArrayDeque`
allocates 17 slots, what `modCount` is checked against and when, what a
`Spliterator`'s `SUBSIZED` characteristic buys, how many bytes a
`HashMap<Integer,Integer>` entry costs, or what `SALT32L` is for. They have probably
absorbed version-stale folklore from blogs. That gap is the entire reason these notes
exist.

## Purpose

These notes are a **detailed one-stop reference plus deep interview prep**. One
document set the reader never needs to supplement with a blog, a Stack Overflow
answer, or a second book. They must serve two readings equally well:

1. a first careful cover-to-cover read that builds the model from nothing, and
2. a night-before-the-interview re-read that reloads the numbers, the traps and the
   answer shapes.

Coverage is driven by the topic, not by any individual reader's measured gaps. Write
for every reader of this level.

## Target version

**Java 21 LTS** is the baseline for every constant, signature and behaviour. Anything
introduced or changed in Java 22–25 is marked inline with its version. Anything that
changed *away from* what older material claims is flagged as a version trap.

## Adjacent topics

These sibling guides exist. For each, the rule is: **state the mechanism in one
self-contained paragraph here, give the reader enough to answer the question, then
point to the sibling for the full treatment.** Never send the reader away
empty-handed, and never duplicate a sibling's full chapter.

| Guide | Owns | What this file still owes the reader |
|---|---|---|
| 01 DSA fundamentals | heaps, BSTs, hashing theory, amortised analysis as a technique | the JDK-specific instance of each: `PriorityQueue`'s sift, `TreeMap`'s red-black, `HashMap`'s chaining |
| 03 Java core | erasure, PECS, `Integer` cache, `String` pool, `BigDecimal` | one paragraph each where collections depend on them, then point |
| 04 Modern Java | streams, collectors, `Gatherer`, virtual threads | the collection-facing surface: `Collection.stream`, `Collectors.to*`, `Stream.toList` semantics |
| 05 Concurrency | memory model, happens-before, CAS, locks, `ThreadLocal` | full mechanism of every concurrent collection, pointing to 05 only for the memory model itself |
| 06 JVM internals | object layout, GC, JIT, JMH, heap dumps | the byte arithmetic of every collection node, and the collection-shaped heap-dump workflow |
| 08 Spring Data JPA | Lombok `@EqualsAndHashCode`, entity identity | the `equals`/`hashCode` consequence for hashed collections |
| 09 SQL databases | B-trees | one paragraph contrasting B-tree with red-black for the disk case |
| 12 API design | JSON mapping | why erasure forces `TypeReference` |
| 13 Web security | deserialization gadget chains | the `HashMap.readObject` link in the chain |
| 15 Caching | Caffeine, W-TinyLFU, eviction policy theory | why `LinkedHashMap`-as-LRU and `WeakHashMap`-as-cache are wrong, and what replaces them |
| 20 Observability | metrics, Micrometer | collection-size gauges as the always-on guard |

---

# TASK

Write the complete Java Collections bible as a set of Markdown files under
`src/topics/02-java-collections/`, organised into five parts, covering **all 901
syllabus leaves reproduced in the `# SYLLABUS` section below**, illustrated by **all
148 diagrams enumerated in the `# DIAGRAM MANIFEST` section below**.

## Tier structure

The notes are organised in these parts, in this order:

| Part | Contains |
|---|---|
| `PART 1 — BASICS` | why the framework exists, the mental model, the vocabulary, the full interface and implementation surface, the guarantees, the contracts, the matrices |
| `PART 2 — INTERMEDIATE` | cost models, views vs copies vs snapshots, the specialised variants, the `Collections`/`Arrays` utility surface, sorting, streams, the "which one and why" decisions |
| `PART 3 — ADVANCED (INTERNALS)` | how the actual classes work inside — source walks, named constants with their values, algorithms, memory layout, concurrency behaviour, failure modes: how `HashMap` buckets and treeifies, how `ArrayList` grows, how `LinkedList` nodes are stitched, how `ConcurrentHashMap` transfers |
| `PART 4 — BUILD IT` | complete, compiling, generic Java 21 reimplementations, each followed by a "Diff vs the real one" table |
| `PART 5 — INTERVIEW AND RETENTION` | the 50 questions with answer shapes, the consolidated trap index, the drills |

## Hard instructions

Every one of these is mandatory.

- **No line limit and no file-count limit.** There is no upper bound on the length of
  the notes or on how many files they are split across. Completeness beats brevity
  every single time. Never truncate, never write "and so on", never write "similar to
  the above", never defer a concept for space. If a part grows large, split it into
  more files rather than cutting content.
- **Output format is Markdown (`.md`).** Every file.
- **Diagrams are SVG.** Inline `<svg>` in the Markdown, or a sibling `.svg` file
  referenced from it. **No ASCII art** — it deforms across renderers and fonts. This
  overrides the syllabus's own wording at leaf 1.2.19 ("Full ASCII hierarchy
  diagram"): render it as SVG. Where SVG genuinely does not fit — a pure grid of
  values such as the null-policy matrix or the master cost table — use a Markdown
  table instead. Every SVG must have:
  - an explicit `viewBox`,
  - no text smaller than 11px,
  - no reliance on external fonts or CSS (use `font-family="sans-serif"` and
    presentation attributes, not classes),
  - fills and strokes legible against both light and dark backgrounds (avoid pure
    white fills on unstroked shapes; give every filled shape an explicit contrasting
    `stroke`; do not rely on black-on-transparent text alone — set an explicit `fill`
    on text and an explicit light `fill` on the shape behind it).
- **Every concept follows this exact chain, in this order:**
  `Concept → Why it exists → How it works → SVG → Code → Gotcha`.
  All six links. If a link genuinely does not apply to a concept, say so in one line
  ("No gotcha: the API has no surprising edge here.") rather than silently dropping
  it.
- **Java code is complete and runnable as written.** Full class and method bodies,
  real field names, real generics, real edge cases. Strip only the trivia: `import`
  statements, `package` declarations, and `main`-method scaffolding where it adds
  nothing. **No `...` elisions, no "implementation omitted", no pseudo-code standing
  in for real code.** Quoted JDK source may be excerpted to the relevant lines, but
  every line quoted must then be explained.
- **Callouts.** Use exactly these three markers, bolded, inline at the point they
  belong. Do not invent others.
  - `**Pitfall:**` — the wrong belief, the symptom it produces, the fix.
  - `**Insight:**` — the non-obvious mechanism that makes the rest click.
  - `**Interview:**` — how this is actually asked, and the one-line answer.
  Every syllabus leaf tagged `[TRAP]` must carry a `**Pitfall:**`.
- **Every part ends with all three of these:**
  1. a **summary table** covering that part's concepts,
  2. **10 interview Q&As** with full model answers — not hints, the answer a candidate
     would actually say out loud, at speaking length,
  3. **5 "predict the output" puzzles** — a complete code snippet, the actual output,
     and an explanation of *why* the output is what it is.
  Where a part is split across several files, these three go at the end of the last
  file of that part, and cover the whole part.
- **Version-specific behaviour is always called out explicitly.** Whenever a
  behaviour, a constant, a default or an API shape differs across Java 7 / 8 / 9+ /
  21, say which version does what, inline, at the point of the claim. Where a
  widely-repeated claim is version-stale, state what is true today, what used to be
  true, and flag it as a version trap. The three known version traps in this topic
  are leaves 3.4.3 (`ArrayDeque` power-of-two masking, untrue since JDK 9), 3.16.8,
  and 5.2.2 — but sweep for more.
- **Tag obligations.** The syllabus tags below are instructions, not decoration:
  - `[PROVE]` — work the argument through on the page. Do not state the result.
  - `[SOURCE]` — quote the real JDK source (short excerpt) and explain every line.
  - `[BUILD]` — ship complete, compiling, generic code.
  - `[TRAP]` — carry a `**Pitfall:**` marker: wrong belief, symptom, fix.
  - `[RESEARCH]` — re-verify against the JDK source or javadoc before writing. If you
    cannot verify a claim, say so explicitly rather than asserting it.
  - `[VERSION-TRAP]` — state what is true in 21 and what used to be true.
  - `[X-REF nn]` — one self-contained mechanism paragraph here, then point to guide nn.
  - `[NUM]` — state the number or byte arithmetic explicitly, with the arithmetic shown.
- **No emojis. No filler.** No "let's dive in", "great question", "as we all know".
  Lead with content.
- **A table for any comparison of three or more things.**
- The notes end with a flat `## Atomic concept checklist`, one bullet per distinct
  concept, phrased as a one-line assertion the reader can self-quiz against.
  Downstream agents parse this list, so keep it flat — no nesting, no headings inside
  it.

## Leaf coverage

The syllabus below has **901 leaves**. **Every leaf must appear in the notes.** Any
leaf you cannot cover must be listed in a `## Deferred` block at the end of the part
that owns it, with the leaf number and a one-line reason. An empty `## Deferred`
block is the expected outcome.

---

# SYLLABUS

**Target version: Java 21 LTS** (baseline for every constant, signature and behaviour below).
Anything introduced or changed in Java 22–25 is marked inline with its version. Anything that
changed *away from* what older material claims (notably ArrayDeque's power-of-two masking, which
has not been true since JDK 9) is marked `[VERSION-TRAP]`.

Tag legend:

| Tag | Meaning for the write pass |
|---|---|
| `[PROVE]` | the notes must work the argument through, not state the result |
| `[SOURCE]` | must quote real JDK source (short excerpt) and explain every line |
| `[BUILD]` | must ship complete, compiling, generic code |
| `[TRAP]` | must carry a `**Pitfall:**` marker — wrong belief, symptom, fix |
| `[RESEARCH]` | leaf exists because of the research phase; re-verify against the cited source before writing |
| `[VERSION-TRAP]` | widely-repeated claim that is version-stale; state what is true in 21 and what used to be true |
| `[X-REF nn]` | one-paragraph mechanism here, full treatment in guide nn |
| `[NUM]` | must state the number/byte arithmetic explicitly |

---

## PART 1 — BASICS

### §1.1 Why a collections framework exists at all

1.1.1 The pre-1.2 world: `Vector`, `Hashtable`, `Stack`, `Enumeration`, `Dictionary` — four unrelated
      classes with no common interface.
1.1.2 What arrays cannot do: fixed length, no insert/remove, no uniqueness, no key lookup, no
      ordering policy, covariance holes.
1.1.3 Array covariance and `ArrayStoreException` — why generic collections do not have this hole.
      `[X-REF 03]` `[TRAP]`
1.1.4 The four things the framework standardises: interfaces, implementations, algorithms
      (`Collections`/`Arrays`), and iteration protocol.
1.1.5 "Program to the interface" — why the field type is `List<E>` and the constructor is
      `new ArrayList<>()`.
1.1.6 Design goal: a small set of interfaces × many implementations, so algorithms are written once.
1.1.7 The cost of that goal: optional operations (`UnsupportedOperationException`) instead of a
      finer interface hierarchy — the framework chose a small hierarchy over a correct one. `[TRAP]`
1.1.8 JCF designer and history: Joshua Bloch, Java 1.2 (1998); Java 5 generics; Java 8 default
      methods and streams; Java 9 factory methods; Java 21 sequenced collections.
1.1.9 Why `Map` is not a `Collection` — it stores pairs, not elements; `size()` would be ambiguous;
      the three view methods bridge the gap instead.
1.1.10 The "optional operation" concept: which methods are optional on which interfaces.
1.1.11 `Collection` has no `equals` contract; `List`, `Set` and `Map` each define one. `[TRAP]`

*(11 leaves)*

### §1.2 The hierarchy, exactly

1.2.1 `Iterable<T>` — the root; declares `iterator()`, `forEach(Consumer)`, `spliterator()`; enables
      the enhanced for loop.
1.2.2 `Collection<E> extends Iterable<E>` — the 15 methods it declares, and which are optional.
1.2.3 `SequencedCollection<E>` (Java 21) sits between `Collection` and `List`/`Deque`. `[RESEARCH]`
1.2.4 `List<E>` — positional access, duplicates, defined `equals`/`hashCode` over order and elements.
1.2.5 `Set<E>` — no duplicates, `equals`/`hashCode` order-independent.
1.2.6 `SequencedSet<E>` (Java 21) — `Set` + `SequencedCollection`.
1.2.7 `SortedSet<E>` → `NavigableSet<E>`.
1.2.8 `Queue<E>` — the two-form method pairs (throw vs return-special-value).
1.2.9 `Deque<E>` — double-ended, extends `Queue` and (Java 21) `SequencedCollection`.
1.2.10 `Map<K,V>` as a separate root; `Map.Entry<K,V>` as a nested interface.
1.2.11 `SequencedMap<K,V>` (Java 21) → `SortedMap` → `NavigableMap`.
1.2.12 `Iterator<E>`, `ListIterator<E>`, `Enumeration<E>`, `PrimitiveIterator`.
1.2.13 `Spliterator<T>` and its `OfInt`/`OfLong`/`OfDouble` specialisations.
1.2.14 Marker interfaces: `RandomAccess`, `Cloneable`, `Serializable`.
1.2.15 `Comparator<T>` and `Comparable<T>` — outside the collection hierarchy, load-bearing inside it.
1.2.16 The abstract skeletons: `AbstractCollection`, `AbstractList`, `AbstractSequentialList`,
       `AbstractSet`, `AbstractQueue`, `AbstractMap`, and what each demands of a subclass. `[RESEARCH]`
1.2.17 `AbstractMap.SimpleEntry` and `AbstractMap.SimpleImmutableEntry`. `[RESEARCH]`
1.2.18 Which interface declares which method — a table of `add`/`offer`/`push`/`put` across
       `Collection`/`Queue`/`Deque`/`Map`, and why the names differ.
1.2.19 Full hierarchy diagram including the Java 21 sequenced tier and `java.util.concurrent`.
       (The syllabus said "ASCII"; render it as SVG per the TASK section.)
1.2.20 Where the concurrent types graft on: `ConcurrentMap`, `ConcurrentNavigableMap`,
       `BlockingQueue`, `BlockingDeque`, `TransferQueue`. `[RESEARCH]`

*(20 leaves)*

### §1.3 Interface method surfaces, method by method

1.3.1 `Collection`: `size`, `isEmpty`, `contains`, `iterator`, `toArray()`, `toArray(T[])`,
      `toArray(IntFunction)` (Java 11), `add`, `remove`, `containsAll`, `addAll`, `removeAll`,
      `retainAll`, `removeIf` (Java 8), `clear`, `stream`, `parallelStream`, `spliterator`.
1.3.2 `toArray(new T[0])` vs `toArray(new T[size])` — the counter-intuitive benchmark result that
      the zero-length form is faster. `[RESEARCH]` `[TRAP]`
1.3.3 `Collection.toArray()` returns `Object[]` — the `ClassCastException` trap. `[TRAP]`
1.3.4 `List`: `get`, `set`, `add(int,E)`, `remove(int)`, `indexOf`, `lastIndexOf`, `listIterator`,
      `subList`, `replaceAll`, `sort`, `of`, `copyOf`, `toArray`, `reversed` (21).
1.3.5 `List.remove(int)` vs `List.remove(Object)` overload ambiguity on `List<Integer>`. `[TRAP]`
1.3.6 `Set`: no methods of its own beyond `Collection` + `of`/`copyOf`; the contract is the content.
1.3.7 `SortedSet`: `comparator`, `subSet`, `headSet`, `tailSet`, `first`, `last`.
1.3.8 `NavigableSet`: `lower`, `floor`, `ceiling`, `higher`, `pollFirst`, `pollLast`,
      `descendingSet`, `descendingIterator`, inclusive-flag `subSet`/`headSet`/`tailSet`.
1.3.9 `Queue`: `add`/`offer`, `remove`/`poll`, `element`/`peek` — the throw-vs-null table.
1.3.10 `Deque`: `addFirst`/`offerFirst`, `addLast`/`offerLast`, `removeFirst`/`pollFirst`,
       `removeLast`/`pollLast`, `getFirst`/`peekFirst`, `getLast`/`peekLast`, `push`, `pop`,
       `peek`, `removeFirstOccurrence`, `removeLastOccurrence`, `descendingIterator`.
1.3.11 The Deque-as-Stack vs Deque-as-Queue naming table: `push`≡`addFirst`, `pop`≡`removeFirst`,
       `peek`≡`peekFirst`, `add`≡`addLast`. Why `Deque` used as a stack iterates LIFO but
       `Stack` iterates FIFO. `[TRAP]`
1.3.12 `Map` core: `size`, `isEmpty`, `containsKey`, `containsValue`, `get`, `put`, `remove`,
       `putAll`, `clear`, `keySet`, `values`, `entrySet`, `equals`, `hashCode`.
1.3.13 `Map` defaults (Java 8): `getOrDefault`, `forEach`, `replaceAll`, `putIfAbsent`,
       `remove(k,v)`, `replace(k,v)`, `replace(k,old,new)`, `computeIfAbsent`, `computeIfPresent`,
       `compute`, `merge`.
1.3.14 `Map` statics: `of` (0–10 pairs), `ofEntries`, `entry`, `copyOf`.
1.3.15 `Map.Entry`: `getKey`, `getValue`, `setValue`, and the statics `comparingByKey`,
       `comparingByValue` (both overloads), `copyOf` (Java 17). `[RESEARCH]`
1.3.16 `SortedMap`: `comparator`, `subMap`, `headMap`, `tailMap`, `firstKey`, `lastKey`.
1.3.17 `NavigableMap`: `lowerEntry`/`lowerKey`, `floorEntry`/`floorKey`, `ceilingEntry`/`ceilingKey`,
       `higherEntry`/`higherKey`, `firstEntry`, `lastEntry`, `pollFirstEntry`, `pollLastEntry`,
       `descendingMap`, `navigableKeySet`, `descendingKeySet`, inclusive-flag range views.
1.3.18 `Iterator`: `hasNext`, `next`, `remove` (default throws), `forEachRemaining`.
1.3.19 `ListIterator`: `hasPrevious`, `previous`, `nextIndex`, `previousIndex`, `set`, `add`.
1.3.20 `ListIterator.add` inserts before the implicit cursor and after the last returned element —
       the off-by-one everyone gets wrong. `[TRAP]`
1.3.21 `Comparator`: `compare`, `reversed`, `thenComparing` ×3, `thenComparingInt/Long/Double`,
       and statics `naturalOrder`, `reverseOrder`, `nullsFirst`, `nullsLast`, `comparing` ×2,
       `comparingInt/Long/Double`.
1.3.22 `Spliterator`: `tryAdvance`, `trySplit`, `estimateSize`, `getExactSizeIfKnown`,
       `characteristics`, `hasCharacteristics`, `getComparator`, `forEachRemaining`.

*(22 leaves)*

### §1.4 Every concrete implementation — the catalogue

For each: backing structure, ordering guarantee, null policy, thread safety, iterator type,
default/initial capacity, when to pick, when explicitly not to.

1.4.1 `ArrayList` — resizable `Object[]`, insertion order, nulls allowed, unsynchronized,
      fail-fast, `RandomAccess`.
1.4.2 `LinkedList` — doubly-linked nodes, `List`+`Deque`, nulls allowed, not `RandomAccess`.
1.4.3 `Vector` — legacy synchronized `ArrayList`; `capacityIncrement`; growth 2× (not 1.5×). `[NUM]`
1.4.4 `Stack extends Vector` — legacy; `push`/`pop`/`peek`/`search`/`empty`; iterates bottom-to-top.
      `[TRAP]`
1.4.5 `CopyOnWriteArrayList` — snapshot array, no CME ever, `set`/`add` copy the whole array.
1.4.6 `HashSet` — `HashMap` wrapper with `PRESENT` dummy; one null; no order guarantee.
1.4.7 `LinkedHashSet` — `LinkedHashMap` wrapper; insertion order; `SequencedSet` in 21.
1.4.8 `TreeSet` — `TreeMap` wrapper; sorted; no nulls (with natural ordering).
1.4.9 `EnumSet` — abstract, with `RegularEnumSet` (≤64 constants, single `long` bit vector) and
      `JumboEnumSet` (`long[]`); factories `noneOf`, `allOf`, `of`, `range`, `complementOf`,
      `copyOf`. `[RESEARCH]` `[NUM]`
1.4.10 `CopyOnWriteArraySet` — `CopyOnWriteArrayList` inside; O(n) `add`; tiny listener sets.
1.4.11 `ConcurrentSkipListSet` — `ConcurrentSkipListMap` wrapper; concurrent sorted set.
1.4.12 `Collections.newSetFromMap(map)` — how to get a `WeakHashSet` or `IdentityHashSet`.
       `[RESEARCH]`
1.4.13 `Collections.newSequencedSetFromMap(SequencedMap)` — Java 21 counterpart. `[RESEARCH]`
1.4.14 `HashMap` — bucket array + list/tree bins; one null key, many null values.
1.4.15 `LinkedHashMap` — `HashMap` + doubly-linked overlay; insertion or access order.
1.4.16 `TreeMap` — red-black tree; `NavigableMap`; no null keys.
1.4.17 `Hashtable` — legacy, synchronized, no nulls at all, growth `2n+1`, initial capacity 11,
       `Enumeration`-based `keys()`/`elements()`. `[NUM]`
1.4.18 `Dictionary` — the abstract legacy parent nobody should extend. `[RESEARCH]`
1.4.19 `Properties extends Hashtable<Object,Object>` — the generics-violating legacy class,
       `getProperty`/`setProperty`, and why `put` on it is a bug. `[RESEARCH]` `[TRAP]`
1.4.20 `EnumMap` — ordinal-indexed `Object[] vals` + cached `keyUniverse`; iteration in ordinal
       order; null values via a `NULL` sentinel; no null keys. `[RESEARCH]`
1.4.21 `IdentityHashMap` — reference equality, linear probing in a single flat array (keys and
       values interleaved), violates the `Map` contract deliberately.
1.4.22 `WeakHashMap` — weak keys, `ReferenceQueue`, `expungeStaleEntries`.
1.4.23 `ConcurrentHashMap` — per-bin CAS/lock; no nulls; `KeySetView`.
1.4.24 `ConcurrentSkipListMap` — lock-free skip list, concurrent `NavigableMap`.
1.4.25 `ArrayDeque` — circular array; no nulls; default capacity `16 + 1 = 17`. `[RESEARCH]` `[NUM]`
1.4.26 `PriorityQueue` — array binary min-heap; default capacity 11; no nulls; unsorted iteration.
1.4.27 `ArrayBlockingQueue` — bounded, single lock, two `Condition`s, optional fairness.
1.4.28 `LinkedBlockingQueue` — optionally bounded, two-lock (put/take) design.
1.4.29 `LinkedBlockingDeque` — bounded blocking deque.
1.4.30 `PriorityBlockingQueue` — unbounded blocking heap.
1.4.31 `DelayQueue` — `Delayed` elements, leader-follower waiting.
1.4.32 `SynchronousQueue` — zero capacity, direct handoff, `isEmpty()` always true.
1.4.33 `LinkedTransferQueue` / `TransferQueue.transfer` — producer blocks for a consumer.
1.4.34 `ConcurrentLinkedQueue` — Michael–Scott lock-free FIFO; `size()` is O(n) and approximate.
       `[TRAP]`
1.4.35 `ConcurrentLinkedDeque` — lock-free double-ended.
1.4.36 `BitSet` — not a `Collection` at all; `long[]` words; `set`/`clear`/`flip`/`get`,
       `and`/`or`/`xor`/`andNot`, `cardinality`, `nextSetBit`, `previousSetBit`, `stream()`,
       `length` vs `size`, `valueOf`/`toLongArray`. `[RESEARCH]`
1.4.37 The immutable families: `List.of`/`Set.of`/`Map.of` and their private classes
       (`List12`, `ListN`, `Set12`, `SetN`, `Map1`, `MapN`). `[RESEARCH]`
1.4.38 `Collections` singletons and empties as implementation classes (`SingletonList`, `EmptyList`).
1.4.39 `Arrays.asList` — `Arrays$ArrayList`, a distinct class from `java.util.ArrayList`. `[TRAP]`
1.4.40 The master "which one do I pick" decision table across all of the above.
1.4.41 The anti-catalogue: which classes to never use in new code and what replaces each
       (`Vector`→`ArrayList`, `Stack`→`ArrayDeque`, `Hashtable`→`HashMap`/`ConcurrentHashMap`,
       `LinkedList`→`ArrayList`/`ArrayDeque`).

*(41 leaves)*

### §1.5 Iteration

1.5.1 The enhanced for loop desugaring — to `Iterator` for `Iterable`, to an index loop for arrays.
      `[SOURCE]`
1.5.2 `Iterator` protocol and the `hasNext`/`next`/`remove` state machine;
      `IllegalStateException` from `remove` before `next`.
1.5.3 `Iterator.remove` is optional — which implementations support it, which throw. `[TRAP]`
1.5.4 `Iterator.remove` cost per implementation: O(n) `ArrayList`, O(1) `LinkedList`,
      O(1) `HashMap`, O(log n) `TreeMap`, unsupported on immutables, no-op-semantics on
      `CopyOnWriteArrayList` (throws).
1.5.5 `ListIterator` bidirectional traversal and mutation.
1.5.6 `removeIf` — one pass, correct by construction, and its `ArrayList` bitset implementation.
      `[SOURCE]`
1.5.7 `forEach` vs for loop: exception wrapping, no `break`, `modCount` check at the end only.
      `[TRAP]`
1.5.8 `Iterable.forEach` default vs `ArrayList`'s override.
1.5.9 `Enumeration` and `Enumeration.asIterator()` (Java 9). `[RESEARCH]`
1.5.10 `Collections.enumeration`/`Collections.list` for legacy interop.
1.5.11 Iterating a `Map`: `entrySet` (correct), `keySet` + `get` (2× the work), `values`.
1.5.12 `descendingIterator` on `Deque` and `NavigableSet`.
1.5.13 Iterating while mutating: the four legal strategies (iterator remove, `removeIf`, collect
       then remove, index loop backwards).
1.5.14 Index-loop-backwards as the only safe index-based removal direction. `[TRAP]`
1.5.15 Nested iteration over the same collection and why it is safe (two iterators, no mutation).
1.5.16 Weakly-consistent iterators as a third category between fail-fast and snapshot.

*(16 leaves)*

### §1.6 Ordering: `Comparable`, `Comparator`, natural order

1.6.1 `Comparable.compareTo` contract: sign semantics, antisymmetry, transitivity,
      `x.compareTo(y)==0` implies same sign for all z.
1.6.2 "Consistent with equals" — the recommendation, who violates it (`BigDecimal`), and what
      breaks. `[TRAP]`
1.6.3 `BigDecimal` in a `TreeSet` vs a `HashSet`: `2.0` and `2.00`. `[TRAP]` `[X-REF 03]`
1.6.4 Natural ordering of the JDK types: numbers, `String` (UTF-16 code-unit order, not locale),
      `Boolean`, enums (ordinal), `java.time` types.
1.6.5 `String` ordering vs `Collator` for human-visible sorting. `[RESEARCH]`
1.6.6 `Comparator` as a functional interface; lambda and method-reference forms.
1.6.7 `Comparator.comparing` + `thenComparing` chaining.
1.6.8 `reversed()` reverses the whole chain built so far. `[TRAP]`
1.6.9 `nullsFirst`/`nullsLast` wrapping, and that they wrap a comparator, not a key extractor.
1.6.10 Primitive specialisations `comparingInt`/`comparingLong`/`comparingDouble` and the boxing
       they avoid. `[NUM]`
1.6.11 Never subtract to compare — `a - b` overflow. `Integer.compare` instead. `[PROVE]` `[TRAP]`
1.6.12 Comparing doubles: `Double.compare` vs `<` for NaN and −0.0. `[TRAP]`
1.6.13 Comparator supplied at construction is part of a `TreeMap`/`TreeSet`/`PriorityQueue`'s
       identity, and is serialized with it.
1.6.14 `Comparator.naturalOrder()` vs passing `null` to the constructor.
1.6.15 `Map.Entry.comparingByValue()` for sorting a map by value.

*(15 leaves)*

### §1.7 The `equals`/`hashCode` contract

1.7.1 `equals`: reflexive, symmetric, transitive, consistent, null-false.
1.7.2 `hashCode`: consistent; equal ⇒ equal hashes; unequal *may* collide.
1.7.3 Why breaking equal⇒equal-hash makes an object undiscoverable in every hash structure.
      `[PROVE]`
1.7.4 The mutable-key trap: mutate a hashed field, entry is stranded in the old bucket, invisible
      to `contains` but visible to iteration and still retained. `[TRAP]`
1.7.5 Overloading `equals(MyType)` instead of overriding `equals(Object)`. `[TRAP]`
1.7.6 `getClass()` vs `instanceof` in `equals`: symmetry vs Liskov; the `Point`/`ColorPoint`
      example. `[TRAP]`
1.7.7 `record` generated `equals`/`hashCode`/`toString` — component-wise, final class, correct by
      construction. `[X-REF 04]`
1.7.8 Records as map keys — the default choice; the array-component caveat (`equals` on arrays is
      identity). `[TRAP]`
1.7.9 `Objects.equals`, `Objects.hash`, `Objects.hashCode`, `Objects.requireNonNull`,
      `Arrays.hashCode` vs `Arrays.deepHashCode`.
1.7.10 `Objects.hash` allocates a varargs array — why hot paths write the `31 * h + f` loop by hand.
       `[NUM]`
1.7.11 The `31 *` multiplier: odd prime, `31*i == (i<<5) - i`. `[PROVE]`
1.7.12 `String.hashCode` = `s[0]*31^(n-1) + ...`, cached in the `hash` field, `hashIsZero` flag
       (Java 13+). `[SOURCE]` `[X-REF 03]`
1.7.13 Distinct `String`s with equal hash codes (`"Aa"`/`"BB"`, `"FB"`/`"Ea"`) and the collision
       DoS they enable. `[NUM]`
1.7.14 `Integer.hashCode() == intValue()`, `Long.hashCode()` = xor fold, `Double.hashCode` via
       `doubleToLongBits`.
1.7.15 `Boolean.hashCode()` returns 1231/1237 — the trivia that shows you read the source. `[NUM]`
1.7.16 Enum `hashCode` is identity-based and varies per JVM run — why `EnumSet`/`EnumMap` exist and
       why enum-keyed `HashMap` iteration order is not reproducible. `[TRAP]` `[RESEARCH]`
1.7.17 `System.identityHashCode` and `IdentityHashMap`.
1.7.18 Inheritance and `equals`: the `AbstractList`/`AbstractSet`/`AbstractMap` implementations
       define cross-implementation equality (`new ArrayList<>(List.of(1)).equals(new LinkedList<>(...))`
       is true; a `List` never equals a `Set`). `[SOURCE]` `[TRAP]`
1.7.19 `hashCode` of a `List` (`31`-fold over elements) vs a `Set` (sum) vs a `Map` (sum of entry
       hashes, entry hash = key^value). `[SOURCE]` `[NUM]`
1.7.20 Self-referential collections: `list.add(list)` then `hashCode()` → `StackOverflowError`.
       `[TRAP]`
1.7.21 Lombok `@EqualsAndHashCode` pitfalls: `callSuper`, inclusion of lazy JPA fields.
       `[X-REF 08]`

*(21 leaves)*

### §1.8 Generics and boxing as they bear on collections

1.8.1 Type erasure: `List<String>` and `List<Integer>` are the same class at runtime. `[X-REF 03]`
1.8.2 Why you cannot have `new E[]` — and how `ArrayList` gets away with `Object[]` +
      `@SuppressWarnings("unchecked")` on the cast in `elementData(int)`. `[SOURCE]`
1.8.3 Heap pollution and `@SafeVarargs` on `List.of`/`Arrays.asList`.
1.8.4 Raw types and the unchecked-warning cliff; how a raw `List` lets an `Integer` into a
      `List<String>`.
1.8.5 The diamond `<>` and target typing in collection construction.
1.8.6 Autoboxing on every `add`/`get` for a `List<Integer>` — where the boxes come from.
1.8.7 The `Integer` cache (−128..127) and why `list.get(0) == list.get(1)` sometimes works.
      `[TRAP]` `[X-REF 03]`
1.8.8 Boxing cost in bytes and in indirection. `[NUM]`
1.8.9 `Map<Integer,Integer>` in a hot loop → the case for `fastutil`/Eclipse Collections primitive
      maps.
1.8.10 `List<int[]>` vs `List<List<Integer>>` — the practical middle ground.
1.8.11 Unboxing NPE: `int x = map.get(missingKey)`. `[TRAP]`
1.8.12 Generic method signatures in the API you must be able to read:
       `<T extends Comparable<? super T>> void sort(List<T>)`. `[X-REF 03]`

*(12 leaves)*

### §1.9 Sequenced collections (Java 21, JEP 431)

1.9.1 The gap JEP 431 filled: no uniform way to get the first or last element, and no
      `LinkedHashSet.getFirst()`. `[RESEARCH]`
1.9.2 `SequencedCollection`: `reversed`, `addFirst`, `addLast`, `getFirst`, `getLast`,
      `removeFirst`, `removeLast`. `[RESEARCH]`
1.9.3 `SequencedSet`: covariant `reversed()` returning `SequencedSet`. `[RESEARCH]`
1.9.4 `SequencedMap`: `reversed`, `sequencedKeySet`, `sequencedValues`, `sequencedEntrySet`,
      `putFirst`, `putLast`, `firstEntry`, `lastEntry`, `pollFirstEntry`, `pollLastEntry`.
      `[RESEARCH]`
1.9.5 Retrofit map: `List` and `Deque` → `SequencedCollection`; `LinkedHashSet` → `SequencedSet`;
      `SortedSet` → `SequencedSet`; `LinkedHashMap` → `SequencedMap`; `SortedMap` →
      `SequencedMap`. `[RESEARCH]`
1.9.6 `SortedSet.addFirst`/`addLast` and `SortedMap.putFirst`/`putLast` throw
      `UnsupportedOperationException` — position is determined by the comparator. `[TRAP]` `[RESEARCH]`
1.9.7 `LinkedHashSet.addFirst`/`addLast` and `LinkedHashMap.putFirst`/`putLast` *move* an existing
      element. `[TRAP]` `[RESEARCH]`
1.9.8 `reversed()` is a view, not a copy — writes through, and `list.reversed().addFirst(x)` appends
      to the original's tail. `[TRAP]`
1.9.9 `ReverseOrderListView` and `ReversedLinkedHashMapView` as the implementing classes.
      `[SOURCE]` `[RESEARCH]`
1.9.10 `firstEntry`/`lastEntry`/`pollFirstEntry`/`pollLastEntry` return **immutable snapshots** —
       `setValue` throws. `[TRAP]` `[RESEARCH]`
1.9.11 `sequencedKeySet().add()` throws — the view is add-hostile. `[RESEARCH]`
1.9.12 `Collections.unmodifiableSequencedCollection`/`unmodifiableSequencedSet`/
       `unmodifiableSequencedMap` (Java 21). `[RESEARCH]`
1.9.13 What is *not* sequenced: `HashSet`, `HashMap`, `PriorityQueue`, `ConcurrentHashMap` — and why
       each was excluded. `[RESEARCH]`
1.9.14 Source-compatibility fallout of the retrofit: a class implementing both `List` and a
       user-defined `getFirst()` with a different return type stopped compiling. `[RESEARCH]` `[TRAP]`
1.9.15 Migration table: old idiom → sequenced idiom (`list.get(list.size()-1)` → `getLast()`,
       `new ArrayList<>(x); Collections.reverse(x)` → `x.reversed()`, iterator-drain-to-get-first →
       `getFirst()`).
1.9.16 Nothing further was added to the collections API in Java 22–25; `Stream.gather`/`Gatherer`
       (Java 24) is the adjacent new thing. `[RESEARCH]` `[X-REF 04]`

*(16 leaves)*

### §1.10 The two matrices every reader memorises

1.10.1 Null-policy matrix: per class, null key allowed / null value allowed / null element allowed,
       and the exception thrown when not.
1.10.2 Why `ArrayDeque` forbids null (null is the empty-slot sentinel). `[PROVE]`
1.10.3 Why `ConcurrentHashMap` forbids null (`get`==null would be irreducibly ambiguous under
       concurrency, so `containsKey` could not fix it). `[PROVE]` `[RESEARCH]`
1.10.4 Why `TreeMap` forbids null keys but allows null values.
1.10.5 Why `Hashtable` forbids both and `HashMap` allows one null key at bucket 0.
1.10.6 Thread-safety matrix: unsynchronized / synchronized-wrapper / fully concurrent / immutable,
       and the iterator guarantee in each column.
1.10.7 Ordering matrix: none / insertion / access / sorted / heap-partial / undefined-but-stable /
       undefined-and-randomised-per-JVM.

*(7 leaves)*

**PART 1 total: 181 leaves**

---

## PART 2 — INTERMEDIATE

### §2.1 The master cost table

2.1.1 One table: every operation × every implementation, amortised vs worst case in separate
      columns.
2.1.2 Rows to include: `get(i)`, `set(i)`, `add(end)`, `add(0)`, `add(i)`, `remove(0)`,
      `remove(i)`, `remove(Object)`, `contains`, `indexOf`, `iterator.next`,
      `iterator.remove`, `size`, `clear`, `addAll`, `sort`.
2.1.3 Map/Set rows: `get`, `put`, `remove`, `containsKey`, `containsValue`, `firstKey`,
      `floorKey`, iteration of `n` entries, `keySet().contains`, `values().contains`.
2.1.4 Queue rows: `offer`, `poll`, `peek`, `remove(Object)`, `contains`.
2.1.5 The amortised-vs-worst distinction spelled out: `ArrayList.add` is amortised O(1) and
      worst-case O(n); `HashMap.get` is expected O(1), worst O(log n) post-treeify.
2.1.6 Why "average case" and "amortised" are different claims. `[PROVE]` `[TRAP]`
2.1.7 `size()` is O(1) on almost everything, O(n) on `ConcurrentLinkedQueue`/`Deque` and on
      `ConcurrentHashMap` only in the sense that it is an estimate. `[TRAP]`
2.1.8 `containsValue` is O(n) on every `Map` — the asymmetry people forget. `[TRAP]`
2.1.9 Constant factors: why an O(n) `ArrayList` scan beats an O(1) `LinkedList` node-hop for
      n < ~1000. `[PROVE]`
2.1.10 Cache-line and prefetch reasoning behind the constant factors. `[X-REF 06]`
2.1.11 What is JMH-measurable and what is not: writing a benchmark for `ArrayList` vs
       `LinkedList` insert-in-middle, and the dead-code/blackhole pitfalls. `[X-REF 06]`
2.1.12 `RandomAccess` as the runtime signal that switches `Collections.binarySearch`,
       `Collections.reverse`, `shuffle`, `fill` between indexed and iterator algorithms.
       `[SOURCE]`
2.1.13 `BINARYSEARCH_THRESHOLD = 5000`, `REVERSE_THRESHOLD = 18`, `SHUFFLE_THRESHOLD = 5`,
       `FILL_THRESHOLD = 25`, `ROTATE_THRESHOLD = 100`, `COPY_THRESHOLD = 10`,
       `REPLACEALL_THRESHOLD = 11`, `INDEXOFSUBLIST_THRESHOLD = 35` in `Collections`.
       `[SOURCE]` `[NUM]` `[RESEARCH]`

*(13 leaves)*

### §2.2 Fail-fast, fail-safe, weakly consistent

2.2.1 `modCount` in `AbstractList` and in `HashMap`; what counts as a structural modification.
2.2.2 `expectedModCount` snapshot and `checkForComodification`. `[SOURCE]`
2.2.3 Exactly which operations bump `modCount` and which do not (`set`, value replacement,
      `replaceAll`, `sort` — `sort` *does* bump it). `[TRAP]` `[SOURCE]`
2.2.4 Single-threaded CME: the classic `for (x : list) list.remove(x)`.
2.2.5 The hidden case: removing the second-to-last element completes without CME because
      `hasNext()` returns false when `cursor == size`. `[PROVE]` `[TRAP]`
2.2.6 CME is a best-effort bug detector, explicitly not a guarantee — quoting the javadoc.
      `[SOURCE]`
2.2.7 `ArrayList.forEach` and `removeIf` check `modCount` once at the end, so the exception
      arrives after the side effects. `[SOURCE]` `[TRAP]`
2.2.8 `HashMap` iteration + `map.put(existingKey, v)` is legal (no structural change);
      `put(newKey, v)` is not. `[TRAP]`
2.2.9 `Iterator.remove` keeps `expectedModCount` in sync — the one legal in-loop mutation.
2.2.10 `ListIterator.add` also resyncs.
2.2.11 Fail-safe by snapshot: `CopyOnWriteArrayList`/`Set` — the iterator holds the old array;
       `iterator.remove` throws `UnsupportedOperationException`. `[TRAP]`
2.2.12 Weakly consistent: `ConcurrentHashMap`, `ConcurrentSkipListMap`, `ConcurrentLinkedQueue`,
       the blocking queues — never CME, may or may not see concurrent updates, traverses each
       element at most once.
2.2.13 `Collections.synchronizedList` iterators are still fail-fast — you must hold the mutex
       around the loop. `[TRAP]`
2.2.14 `Vector`/`Hashtable` iterators are fail-fast, but their `Enumeration`s are not. `[TRAP]`
       `[RESEARCH]`
2.2.15 `EnumMap`/`IdentityHashMap` iterator quirks: `EnumMap`'s reused `Entry` object means
       collecting entries into a list gives you n references to one mutating object.
       `[TRAP]` `[RESEARCH]`
2.2.16 The debugger-triggered CME: a watch expression calling `toString` on a collection another
       thread mutates.
2.2.17 Recovering from CME correctly: never catch it. It is a bug marker. `[TRAP]`

*(17 leaves)*

### §2.3 Views, copies, snapshots

2.3.1 The three-way distinction stated once: view (live, bidirectional), copy (independent),
      snapshot (independent, taken at a point in time).
2.3.2 `subList(from,to)` — a live window; structural changes through it change the backing list.
2.3.3 `subList` + any structural change to the *parent* invalidates the sublist:
      `ConcurrentModificationException` on the next sublist operation. `[TRAP]` `[SOURCE]`
2.3.4 `list.subList(a,b).clear()` as the idiomatic range delete.
2.3.5 `subList` retaining the whole parent array — the memory-leak shape
      (`new ArrayList<>(big.subList(0,1))` vs `big.subList(0,1)`). `[TRAP]`
2.3.6 `Map.keySet()` — a view; `remove` deletes the mapping; `add` throws.
2.3.7 `Map.values()` — a view; `remove` deletes *one* matching mapping; `contains` is O(n).
2.3.8 `Map.entrySet()` — a view of live `Map.Entry` objects; `entry.setValue` writes through.
2.3.9 `Map.entrySet()` on `HashMap` yields the actual `Node` objects — do not retain them.
      `[TRAP]`
2.3.10 `TreeMap` range views (`headMap`/`tailMap`/`subMap`) are live and range-restricted:
       inserting outside the range through the view throws `IllegalArgumentException`. `[TRAP]`
2.3.11 `descendingMap`/`descendingSet`/`reversed()` views.
2.3.12 `Arrays.asList(arr)` — fixed-size, write-through to the array; `set` mutates `arr`;
       `add`/`remove` throw. `[TRAP]`
2.3.13 `Arrays.asList(primitiveArray)` gives a `List<int[]>` of size 1. `[TRAP]`
2.3.14 `List.of(...)` — immutable, null-hostile, unrelated to the source array after construction
       (`listFromTrustedArray` vs a defensive copy). `[RESEARCH]`
2.3.15 `Collections.unmodifiableX(c)` — an unmodifiable *view*: the underlying collection can still
       change beneath it. `[TRAP]`
2.3.16 `List.copyOf`/`Set.copyOf`/`Map.copyOf` — genuine immutable copies; `copyOf` of an already
       immutable collection returns the same instance. `[RESEARCH]`
2.3.17 Shallow vs deep immutability: an immutable list of mutable objects. `[TRAP]`
2.3.18 Defensive copying at API boundaries: getter returns `List.copyOf(field)` or
       `Collections.unmodifiableList(field)` — and which to choose.
2.3.19 `Collections.singletonList` vs `List.of` — one is mutable-via-`set`, one is not. `[TRAP]`
       `[RESEARCH]`
2.3.20 `Map.entry(k,v)` is immutable; `AbstractMap.SimpleEntry` is not; `Map.Entry.copyOf`
       (Java 17) snapshots one. `[RESEARCH]`
2.3.21 `CopyOnWriteArrayList` iterators as snapshots.
2.3.22 `EnumSet.copyOf` / `EnumSet.clone` semantics.
2.3.23 Stream terminal ops and mutability: `toList()` (Java 16, unmodifiable, allows nulls) vs
       `collect(Collectors.toList())` (unspecified, currently `ArrayList`) vs
       `Collectors.toUnmodifiableList` (immutable, null-hostile). Full 3×3 matrix with
       null-handling. `[TRAP]` `[RESEARCH]`
2.3.24 The mutability decision table: which factory to use for which intent.

*(24 leaves)*

### §2.4 Immutability tiers, precisely

2.4.1 Tier 0: mutable.
2.4.2 Tier 1: fixed-size (`Arrays.asList`, `Collections.nCopies`).
2.4.3 Tier 2: unmodifiable view (`Collections.unmodifiableX`).
2.4.4 Tier 3: unmodifiable independent copy (`List.copyOf`).
2.4.5 Tier 4: truly immutable factory (`List.of`, `Set.of`, `Map.of`, `EnumSet` — no, `EnumSet` is
      mutable; state that explicitly).
2.4.6 The comparison table: null allowed? duplicates allowed? `set` allowed? `add` allowed?
      reflects source changes? serializable? iteration order stable across JVM runs?
2.4.7 `Set.of` with duplicate arguments throws `IllegalArgumentException` at construction. `[TRAP]`
2.4.8 `Map.of` with duplicate keys throws; `Map.ofEntries` too.
2.4.9 `Map.of` caps at 10 pairs; `Map.ofEntries(entry(...),...)` beyond that.
2.4.10 `List.of(null)` throws NPE — and `List.of` overloads for 0–10 args plus a varargs form,
       to avoid array allocation. `[RESEARCH]` `[NUM]`
2.4.11 `immutableList.contains(null)` throws NPE on some implementations and returns false on
       others. `[TRAP]` `[RESEARCH]`
2.4.12 `indexOf(null)`/`lastIndexOf(null)` on `ListN` with `allowNulls=false` throws NPE.
       `[RESEARCH]`
2.4.13 Guava `ImmutableList`/`ImmutableMap` and how they differ from `List.of` (builder, ordering
       guarantee, `asList` views).

*(13 leaves)*

### §2.5 Wildcards and PECS as the Collections API uses them

2.5.1 `? extends` (producer) vs `? super` (consumer); the PECS mnemonic. `[X-REF 03]`
2.5.2 `Collection.addAll(Collection<? extends E>)` — why `extends`.
2.5.3 `Collections.copy(List<? super T> dest, List<? extends T> src)` — both in one signature.
2.5.4 `Comparator<? super T>` in `sort`, `TreeMap`, `PriorityQueue` — why `super`.
2.5.5 `<T extends Comparable<? super T>>` in `Collections.sort`/`max`/`min` — unpacking the bound.
      `[PROVE]`
2.5.6 `Collections.max(Collection<? extends T>, Comparator<? super T>)`.
2.5.7 Unbounded `Collection<?>` and what you can still call on it.
2.5.8 `List<Object>` is not a supertype of `List<String>`; `List<? extends Object>` is. `[TRAP]`
2.5.9 Why you cannot `add` to a `List<? extends Number>`. `[PROVE]`
2.5.10 `Map<String, ? extends Number>` parameter shapes in real API design.
2.5.11 Capture conversion in error messages (`capture of ? extends E`) and how to read them.

*(11 leaves)*

### §2.6 The `Collections` utility surface (exhaustive)

2.6.1 Sorting/searching: `sort(List)`, `sort(List,Comparator)`, `binarySearch` ×2.
2.6.2 `binarySearch` return value for a missing key: `-(insertionPoint) - 1`. `[NUM]` `[TRAP]`
2.6.3 `binarySearch` on an unsorted list is silently wrong, not an error. `[TRAP]`
2.6.4 Reordering: `reverse`, `shuffle` ×2, `rotate`, `swap`.
2.6.5 `rotate` implemented by three reversals for non-`RandomAccess` lists. `[SOURCE]` `[PROVE]`
2.6.6 Bulk change: `fill`, `copy` (requires dest.size ≥ src.size), `replaceAll(list,old,new)`.
2.6.7 Extremes: `min` ×2, `max` ×2.
2.6.8 Search: `indexOfSubList`, `lastIndexOfSubList`, `frequency`, `disjoint`.
2.6.9 Constants: `emptyList`, `emptySet`, `emptyMap`, `emptySortedSet`, `emptySortedMap`,
      `emptyNavigableSet`, `emptyNavigableMap`, `emptyIterator`, `emptyListIterator`,
      `emptyEnumeration`. `[RESEARCH]`
2.6.10 Singletons: `singleton`, `singletonList`, `singletonMap`.
2.6.11 `nCopies(n,x)` — an O(1)-memory view of n references to one object. `[NUM]`
2.6.12 Unmodifiable wrappers: `unmodifiableCollection/List/Set/SortedSet/NavigableSet/Map/
       SortedMap/NavigableMap` plus the Java 21 `unmodifiableSequencedCollection/Set/Map`.
       `[RESEARCH]`
2.6.13 Synchronized wrappers: `synchronizedCollection/List/Set/SortedSet/NavigableSet/Map/
       SortedMap/NavigableMap`; the shared mutex field; the manual-sync-for-iteration rule.
2.6.14 `checkedCollection/List/Set/SortedSet/NavigableSet/Queue/Map/SortedMap/NavigableMap` — the
       runtime type check that finds the raw-type call site that polluted your collection. The
       exact debugging workflow. `[RESEARCH]`
2.6.15 Interop: `enumeration(Collection)`, `list(Enumeration)`, `addAll(Collection, T...)`.
2.6.16 `reverseOrder()` and `reverseOrder(Comparator)`.
2.6.17 `asLifoQueue(Deque)` — turning a deque into a stack-shaped `Queue`. `[RESEARCH]`
2.6.18 `newSetFromMap(Map<E,Boolean>)` and `newSequencedSetFromMap` (21). `[RESEARCH]`
2.6.19 What is *missing* from `Collections` and lives in `Guava` instead: `partition`,
       `Multimap`, `BiMap`, `Multiset`, `Sets.union/intersection/difference`.

*(19 leaves)*

### §2.7 The `Arrays` utility surface, as it touches collections

2.7.1 `asList`, `stream`, `setAll`, `fill`, `copyOf`, `copyOfRange`.
2.7.2 `sort` ×many, `parallelSort` and its `MIN_ARRAY_SORT_GRAN = 8192`. `[NUM]` `[RESEARCH]`
2.7.3 `binarySearch`, `equals`, `deepEquals`, `hashCode`, `deepHashCode`, `toString`,
      `deepToString`, `mismatch`, `compare`, `compareUnsigned`.
2.7.4 `System.arraycopy` and `Arrays.copyOf` — the intrinsic underneath every list growth.
2.7.5 `Arrays.asList` returning a fixed-size list — cross-link to §2.3.12.
2.7.6 `Arrays.stream(arr).boxed().toList()` as the array→`List<Integer>` idiom, and the
      `Arrays.asList(int[])` mistake it avoids.

*(6 leaves)*

### §2.8 Sorting, in depth

2.8.1 `Collections.sort(list)` delegates to `list.sort(null)` since Java 8 — and why that mattered
      for performance on `ArrayList`. `[SOURCE]` `[RESEARCH]`
2.8.2 `List.sort` default implementation: dump to array, `Arrays.sort`, write back via
      `ListIterator`. `[SOURCE]`
2.8.3 `ArrayList.sort` overrides it to sort `elementData` in place and bump `modCount`. `[SOURCE]`
2.8.4 Objects → TimSort: stable, adaptive, run detection, `MIN_MERGE = 32`, galloping merge,
      O(n) best case, O(n log n) worst, O(n/2) extra space. `[NUM]`
2.8.5 `minRunLength` computation and why runs are extended by binary insertion sort. `[PROVE]`
2.8.6 The merge-stack invariants and `mergeCollapse`. `[SOURCE]`
2.8.7 The de Gouw et al. TimSort proof and the `ArrayIndexOutOfBoundsException` bug they found;
      the JDK's fix was to enlarge the stack rather than fix the invariant. `[RESEARCH]` `[PROVE]`
2.8.8 `IllegalArgumentException: Comparison method violates its general contract!` — what TimSort
      actually detected, the common causes (int subtraction overflow, non-transitive comparator,
      mutating the sort key mid-sort, comparing on a field that can be null), and the fixes.
      `[TRAP]` `[RESEARCH]`
2.8.9 `-Djava.util.Arrays.useLegacyMergeSort=true` as the escape hatch, and why it is a
      band-aid. `[RESEARCH]`
2.8.10 Primitives → dual-pivot quicksort: two pivots, in place, not stable, O(n log n) average,
       O(n²) adversarial.
2.8.11 Why the object/primitive split exists: stability is meaningless for primitives, and object
       comparison is expensive so minimising comparisons wins. `[PROVE]`
2.8.12 Java 14+ `DualPivotQuicksort` additions: insertion sort for tiny arrays, counting sort for
       `byte`/`char`/`short`, merge sort fallback on detected structure, `MAX_RECURSION_DEPTH`
       heapsort fallback. `[NUM]` `[RESEARCH]`
2.8.13 Quicksort adversarial input and the historical `Arrays.sort(int[])` DoS. `[RESEARCH]`
2.8.14 Stability, demonstrated: sort by secondary key then primary key. `[PROVE]`
2.8.15 `TreeMap`/`TreeSet` as an alternative to sorting when insertions are interleaved with reads.
2.8.16 `PriorityQueue` as an alternative when you need only the top k. `[PROVE]`
2.8.17 `Stream.sorted()` and its buffering behaviour; `sorted()` on an infinite stream.
2.8.18 `Comparator` + `List.sort` vs `Stream.sorted().toList()` — allocation difference.
2.8.19 Sorting a `Map` by value into a `LinkedHashMap`. `[BUILD]`

*(19 leaves)*

### §2.9 Specialised maps and sets — the exact scenario each was built for

2.9.1 `EnumMap`: enum keys, ordinal array, no hashing, ordinal iteration order, ~2 words per slot.
      `[NUM]`
2.9.2 `EnumMap` is dense — it allocates a slot per enum constant regardless of size. `[TRAP]`
2.9.3 `EnumSet`: `RegularEnumSet` single `long` for ≤64 constants; `JumboEnumSet` `long[]` beyond.
      `[NUM]` `[RESEARCH]`
2.9.4 `EnumSet` bulk operations (`addAll`/`removeAll`/`retainAll`) become single bitwise ops when
      both operands are the same enum type. `[SOURCE]` `[PROVE]`
2.9.5 `EnumSet.complementOf`, `range`, `allOf`, `noneOf`, `of` overloads (varargs vs 1–5 arity).
2.9.6 `EnumSet` is mutable and not thread-safe despite feeling like a constant. `[TRAP]`
2.9.7 `IdentityHashMap`: reference equality, the deliberate `Map`-contract violation, its use in
      serialization/graph-traversal/cycle detection.
2.9.8 `IdentityHashMap` sizing: `DEFAULT_CAPACITY = 32`, table length `2 * capacity` because keys
      and values interleave, linear probing, `MAXIMUM_CAPACITY = 1 << 29`. `[NUM]` `[RESEARCH]`
2.9.9 `IdentityHashMap` + a key whose `equals` you expected to be used → silent miss. `[TRAP]`
2.9.10 `WeakHashMap`: weak keys, strong values, `ReferenceQueue<Object> queue`,
       `expungeStaleEntries()` called on almost every operation. `[SOURCE]`
2.9.11 `WeakHashMap` value-references-key is a leak: the value strongly holds the key, so the entry
       never clears. Fix: wrap the value in a `WeakReference`. `[TRAP]` `[PROVE]`
2.9.12 `WeakHashMap` with `String` literal keys never clears (interned). `[TRAP]`
2.9.13 `WeakHashMap` is not a cache — no size bound, clearing depends on GC timing. Use Caffeine.
       `[TRAP]` `[X-REF 15]`
2.9.14 Reference strength ladder: strong → soft → weak → phantom, and which map type uses which.
       `[X-REF 06]`
2.9.15 `Hashtable` vs `HashMap` vs `ConcurrentHashMap` — the 3-way table.
2.9.16 `Properties` and `System.getProperties()`.
2.9.17 `BitSet` as a set-of-small-ints: 1 bit per element vs 16+ bytes for a boxed
       `HashSet<Integer>` entry. `[NUM]` `[PROVE]`
2.9.18 `BitSet` sizing surprise: `set(1_000_000)` allocates ~125 KB immediately;
       `length()` vs `size()` vs `cardinality()`. `[NUM]` `[TRAP]`
2.9.19 `BitSet` for sieve, bloom-filter-ish membership, and permission masks.
2.9.20 Sparse alternatives: `RoaringBitmap` (third party) when the domain is huge and sparse.

*(20 leaves)*

### §2.10 The `NavigableMap`/`NavigableSet` API in anger

2.10.1 `floor`/`ceiling`/`lower`/`higher` — the ≤/≥/</> table, and the `Key` vs `Entry` variants.
2.10.2 `headMap`/`tailMap`/`subMap` with and without inclusive flags.
2.10.3 `subMap(from,true,to,false)` is the half-open range you almost always want.
2.10.4 `pollFirstEntry`/`pollLastEntry` as a destructive priority read.
2.10.5 `descendingMap` and `descendingKeySet`.
2.10.6 `navigableKeySet` vs `keySet`.
2.10.7 Use case: time-series bucketing — "the last value at or before timestamp t".
2.10.8 Use case: interval/range lookup (IP-to-country, tier pricing) with `floorEntry`.
2.10.9 Use case: sliding-window rate limiter with `subMap` + `headMap().clear()`.
2.10.10 Use case: leaderboard with `descendingMap` and `headMap(limit)`.
2.10.11 Use case: nearest-neighbour on one dimension.
2.10.12 `TreeMap` range views are O(log n) to create, O(1) amortised per step to iterate. `[PROVE]`
2.10.13 `ConcurrentSkipListMap` gives the same API concurrently — and `size()` becomes O(n).
        `[TRAP]`

*(13 leaves)*

### §2.11 `Map` default methods, in depth

2.11.1 `getOrDefault` — and how it differs from `computeIfAbsent` (no insertion).
2.11.2 `putIfAbsent` returns the *existing* value or null — not a boolean. `[TRAP]`
2.11.3 `computeIfAbsent` for the multimap idiom
       `map.computeIfAbsent(k, x -> new ArrayList<>()).add(v)`.
2.11.4 `computeIfAbsent` with a mapping function that returns null does not insert. `[TRAP]`
2.11.5 `computeIfPresent`/`compute` returning null *removes* the entry. `[TRAP]`
2.11.6 `merge(k, v, remap)` for counters: `merge(k, 1, Integer::sum)`.
2.11.7 `merge` remapping to null removes the entry; `merge` with a null value argument throws.
       `[TRAP]`
2.11.8 The counter-idiom comparison table: `merge` vs `computeIfAbsent(...).increment()` vs
       `getOrDefault(k,0)+1` vs `Collectors.counting()` vs `LongAdder` values.
2.11.9 `replaceAll(BiFunction)` mutates values in place without structural change.
2.11.10 `forEach(BiConsumer)` and why it cannot `break`.
2.11.11 `remove(k, v)` and `replace(k, old, new)` as CAS-shaped operations, and that on a plain
        `HashMap` they are *not* atomic. `[TRAP]`
2.11.12 Recursive `computeIfAbsent` on a `HashMap` corrupts it (Java 9+ throws
        `ConcurrentModificationException`); on a `ConcurrentHashMap` it deadlocks.
        `[TRAP]` `[X-REF 05]`
2.11.13 `HashMap.computeIfAbsent` counts as a structural modification even when the key was
        present-with-null. `[TRAP]`
2.11.14 The default implementations in the `Map` interface are non-atomic by contract; concrete
        classes override them for efficiency and, in `ConcurrentHashMap`, for atomicity. `[SOURCE]`

*(14 leaves)*

### §2.12 Set algebra and bulk operations

2.12.1 `containsAll`, `addAll`, `removeAll`, `retainAll` as ∪/∖/∩.
2.12.2 The asymmetric cost trap: `list.removeAll(list2)` is O(n·m) because `list2.contains` is
       O(m); `list.removeAll(new HashSet<>(list2))` is O(n+m). `[PROVE]` `[TRAP]`
2.12.3 `AbstractSet.removeAll` switches on relative sizes and can iterate the *argument* instead —
       so `bigSet.removeAll(smallList)` behaves differently from `smallSet.removeAll(bigList)`.
       `[SOURCE]` `[TRAP]`
2.12.4 `retainAll` on a `keySet()` view deletes mappings from the map.
2.12.5 `Collection.removeAll` on an immutable collection throws even when nothing would change —
       or does it? (implementation-dependent short-circuit). `[TRAP]`
2.12.6 `disjoint(a,b)` and its size-based optimisation.
2.12.7 Symmetric difference by hand; Guava `Sets.symmetricDifference` as a lazy view.
2.12.8 Multiset/bag semantics are absent from the JDK; `Map<T,Integer>` or Guava `Multiset`.
2.12.9 `Set` of mutable elements after mutation: the same stranding bug as map keys. `[TRAP]`
2.12.10 `EnumSet` bulk ops as single bitwise instructions (cross-ref §2.9.4).

*(10 leaves)*

### §2.13 Collections and streams

2.13.1 `stream()`/`parallelStream()` are `Collection` defaults built on `spliterator()`.
2.13.2 `Collectors.toList`/`toUnmodifiableList`/`toSet`/`toUnmodifiableSet`/`toMap`
       (2-arg, 3-arg, 4-arg)/`toUnmodifiableMap`/`toCollection`.
2.13.3 `Collectors.toMap` throws `IllegalStateException` on duplicate keys — and NPE on a null
       value, unlike `HashMap.put`. `[TRAP]`
2.13.4 `Collectors.toMap` with a `TreeMap::new` or `LinkedHashMap::new` map supplier.
2.13.5 `groupingBy` (1/2/3-arg), `partitioningBy`, `counting`, `summingInt`, `averagingDouble`,
       `mapping`, `flatMapping`, `filtering`, `reducing`, `collectingAndThen`, `teeing` (12),
       `joining`, `summarizingInt`, `minBy`/`maxBy`.
2.13.6 `groupingByConcurrent` and when its unordered semantics are acceptable.
2.13.7 `Collectors.toMap` merge function as the dedupe policy.
2.13.8 When a stream is the wrong tool: single-element lookup, tiny collections in a hot loop,
       side-effecting loops, when you need the index, when you need early exit with state,
       when a `for` loop is simply clearer. `[TRAP]`
2.13.9 `Stream.toList()` (Java 16) vs `collect(toList())` — nullability and mutability
       (cross-ref §2.3.23).
2.13.10 `Collection.removeIf` vs `stream().filter().toList()` — in-place vs new collection.
2.13.11 `List.stream().collect(...)` allocation profile vs a preallocated `ArrayList` + loop.
2.13.12 `Collectors.toList()` on a parallel stream still returns a sequential `ArrayList` — the
        combiner cost. `[PROVE]`
2.13.13 Mutable reduction vs `reduce` with immutable accumulation (the `String` concat mistake).
        `[TRAP]`
2.13.14 `Stream.iterate`/`generate` + `limit` to build a collection.
2.13.15 `IntStream.range().boxed().toList()` and the boxing you just paid for. `[NUM]`
2.13.16 `Gatherer` (Java 24) as the extension point for windowing/scan over a collection.
        `[RESEARCH]` `[X-REF 04]`

*(16 leaves)*

### §2.14 The choosing framework

2.14.1 The decision tree: ordered? sorted? unique? keyed? bounded? concurrent? both-ends?
       primitive-heavy?
2.14.2 "Which List": `ArrayList` unless you have a measured reason.
2.14.3 "Which Set": `LinkedHashSet` when output order matters, `HashSet` otherwise, `EnumSet`
       for enums, `TreeSet` for range queries.
2.14.4 "Which Map": `HashMap` default, `LinkedHashMap` for reproducible order/LRU, `TreeMap` for
       navigation, `EnumMap` for enums, `ConcurrentHashMap` for sharing.
2.14.5 "Which Queue": `ArrayDeque` default, `PriorityQueue` for priority, `ArrayBlockingQueue`
       for bounded backpressure, `LinkedBlockingQueue` for throughput.
2.14.6 Sizing decisions: initial capacity, load factor, when to pre-size, when it is noise.
2.14.7 Immutability decisions: what to expose from an API, what to accept as a parameter.
2.14.8 Interface-in-signature decisions: `Collection` vs `List` vs `Iterable` as a parameter type.
2.14.9 Returning empty vs null from a collection-returning method. `[TRAP]`
2.14.10 When to reach outside the JDK (see §2.17).

*(10 leaves)*

### §2.15 Legacy members nobody explains

2.15.1 `Vector`: synchronized methods, `capacityIncrement`, doubling growth, `elementAt`,
       `addElement`, `removeAllElements`, `firstElement`, `lastElement`.
2.15.2 Why `Vector` is not a drop-in thread-safe `ArrayList`: compound operations still race, and
       iteration is fail-fast. `[TRAP]` `[PROVE]`
2.15.3 `Stack`: `push`/`pop`/`peek`/`empty`/`search` (1-based!), extends `Vector`, iterates
       bottom-up. `[TRAP]`
2.15.4 `Hashtable`: `contains` means `containsValue`, growth `2n+1`, initial capacity 11, `keys()`
       and `elements()` returning `Enumeration`, `rehash()`.
2.15.5 `Dictionary` as an abstract class in an interface world.
2.15.6 `Enumeration` vs `Iterator`: 2 methods vs 3, no `remove`, no fail-fast, still used by
       `ZipFile`, `ServletRequest.getHeaders`, `NetworkInterface`, `Properties.propertyNames`.
2.15.7 `Enumeration.asIterator()` (Java 9) for bridging. `[RESEARCH]`
2.15.8 Why the legacy classes remain: binary compatibility with 1998-era code.
2.15.9 Interview framing: what to say when asked "why not just use Vector".

*(9 leaves)*

### §2.16 Serialization of collections

2.16.1 Which collections are `Serializable` and which are not (`Arrays.asList`'s result is;
       `Collections.unmodifiableList`'s is; `keySet()` views are not).
2.16.2 `ArrayList.writeObject`/`readObject` writes `size` and only the live elements, not the
       whole capacity — that is why `elementData` is `transient`. `[SOURCE]` `[PROVE]`
2.16.3 `HashMap.writeObject` writes capacity, size and entries; `readObject` re-`put`s, so the
       table is rebuilt with current hash codes. `[SOURCE]`
2.16.4 Deserializing a `HashMap` whose keys' `hashCode` changed across JVM versions → entries in
       the wrong bucket. `[TRAP]`
2.16.5 `TreeMap`'s comparator must itself be serializable. `[TRAP]`
2.16.6 The `ImmutableCollections` serial proxy `CollSer` and `writeReplace`. `[SOURCE]` `[RESEARCH]`
2.16.7 Java deserialization gadget chains through `HashMap.readObject` calling `hashCode` on
       attacker-controlled keys. `[X-REF 13]` `[RESEARCH]`
2.16.8 JSON/Jackson mapping of collection types: `List` vs `Set` vs `Map` polymorphism,
       `TypeReference`, and why erasure forces it. `[X-REF 12]`
2.16.9 `serialVersionUID` on a collection subclass you wrote.

*(9 leaves)*

### §2.17 Third-party collections and when they earn their place

2.17.1 Guava: `ImmutableList/Set/Map`, `Multimap`/`ListMultimap`/`SetMultimap`, `Multiset`,
       `BiMap`, `Table`, `RangeMap`/`RangeSet`, `Lists.partition`, `Sets.cartesianProduct`,
       `Iterables`/`Iterators`, `MapMaker`. `[RESEARCH]`
2.17.2 Eclipse Collections: `MutableList`/`ImmutableList` split, primitive collections,
       `UnifiedSet` at ~25% of `HashSet` memory, `Bag`, `BiMap`, `Interval`, eager APIs.
       `[RESEARCH]` `[NUM]`
2.17.3 fastutil: `IntArrayList`, `Int2ObjectHashMap`, `Object2IntMap`, best-in-class primitive
       list performance, large-array support. `[RESEARCH]`
2.17.4 HPPC, Koloboke, Trove — historical and niche; Trove's primitive `HashSet` losing to the
       JDK in some benchmarks. `[RESEARCH]`
2.17.5 Caffeine: the actual answer when someone reaches for `LinkedHashMap`-as-cache or
       `WeakHashMap`-as-cache; W-TinyLFU. `[X-REF 15]`
2.17.6 Agrona / JCTools: `ManyToOneConcurrentArrayQueue`, `Object2ObjectHashMap`, off-heap
       and lock-free queues for low-latency work.
2.17.7 Apache Commons Collections: `MultiValuedMap`, `Bag`, `CircularFifoQueue`, and its
       deserialization CVE history. `[RESEARCH]`
2.17.8 RoaringBitmap for compressed sparse bitsets.
2.17.9 The decision rule: reach outside the JDK only for (a) primitive specialisation with a
       measured allocation problem, (b) a data structure the JDK lacks (multimap, bimap, bag,
       range map), (c) a real cache. Otherwise the dependency is not worth it.
2.17.10 Cost of the dependency: shading, transitive conflicts, module system, security surface.

*(10 leaves)*

**PART 2 total: 233 leaves**

---

## PART 3 — ADVANCED (INTERNALS / UNDER THE HOOD)

### §3.1 `ArrayList` source walk

3.1.1 `private static final int DEFAULT_CAPACITY = 10;` `[SOURCE]` `[NUM]`
3.1.2 `private static final Object[] EMPTY_ELEMENTDATA = {};` and
      `private static final Object[] DEFAULTCAPACITY_EMPTY_ELEMENTDATA = {};` — two distinct
      shared instances. `[SOURCE]`
3.1.3 Why both exist: `new ArrayList<>()` must lazily grow to 10 on first add, while
      `new ArrayList<>(0)` must grow to 1. The array *identity* is the flag. `[PROVE]` `[TRAP]`
3.1.4 `transient Object[] elementData; private int size;` and `elementData.length` as capacity.
3.1.5 `grow(int minCapacity)` verbatim:
      `ArraysSupport.newLength(oldCapacity, minCapacity - oldCapacity, oldCapacity >> 1)`.
      `[SOURCE]` `[RESEARCH]`
3.1.6 `ArraysSupport.newLength(oldLength, minGrowth, prefGrowth)`:
      `prefLength = oldLength + Math.max(minGrowth, prefGrowth)`; falls back to `hugeLength`.
      `[SOURCE]` `[RESEARCH]`
3.1.7 `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8` and why it is "soft": `hugeLength` will
      return `minLength` above it if that is what you asked for, and only throws `OutOfMemoryError`
      on int overflow. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.1.8 The 1.5× growth sequence from the default: 10 → 15 → 22 → 33 → 49 → 73 → 109 → 163 → 244.
      `[NUM]`
3.1.9 `oldCapacity >> 1` on capacity 1 gives 0 growth — `newLength`'s `max(minGrowth, prefGrowth)`
      is what saves it. `[PROVE]` `[TRAP]`
3.1.10 `addAll` of a large collection jumps straight to the required size (minGrowth wins).
3.1.11 `add(E)`: `modCount++`, `add(e, elementData, size)`, `if (s == elementData.length) grow()`.
       `[SOURCE]`
3.1.12 `add(int index, E)`: `rangeCheckForAdd`, then
       `System.arraycopy(elementData, index, elementData, index+1, s-index)`. `[SOURCE]`
3.1.13 `remove(int)`: `fastRemove` → one `arraycopy` left-shift, then `elementData[--size] = null`
       so the last reference is cleared for GC. `[SOURCE]` `[PROVE]`
3.1.14 Why `remove(0)` is O(n) and `remove(size-1)` is O(1). `[PROVE]`
3.1.15 `indexOf`/`contains` linear scan with a null-vs-equals split loop. `[SOURCE]`
3.1.16 `elementData(int)` and the `@SuppressWarnings("unchecked")` cast.
3.1.17 `Objects.checkIndex` / `rangeCheck` and why the JIT eliminates the redundant bounds check.
3.1.18 `System.arraycopy` as a JIT intrinsic — `vectorizedMismatch`-style native memmove.
       `[X-REF 06]`
3.1.19 `ensureCapacity(int)` — the single highest-value `ArrayList` optimisation; the exact
       arithmetic it skips. `[PROVE]` `[NUM]`
3.1.20 `trimToSize()` — when it is worth the copy (long-lived, over-allocated lists).
3.1.21 `clear()` nulls every slot but keeps capacity. `[TRAP]`
3.1.22 `removeIf` implementation with a `long[]` deathRow bitset and a single compaction pass.
       `[SOURCE]`
3.1.23 `batchRemove` shared by `removeAll`/`retainAll`, and its `finally` block that keeps the list
       consistent if the predicate throws. `[SOURCE]`
3.1.24 `subList` returning `ArrayList.SubList` with `root`, `parent`, `offset`, `size`, and its own
       `modCount` mirror. `[SOURCE]`
3.1.25 `SubList.checkForComodification` comparing against `root.modCount`. `[SOURCE]`
3.1.26 `Itr` and `ListItr` inner classes: `cursor`, `lastRet`, `expectedModCount`. `[SOURCE]`
3.1.27 `Itr.next()` reads `elementData` into a local for speed and re-checks `modCount` only
       before the read. `[SOURCE]`
3.1.28 `ArrayListSpliterator` with `SIZED | SUBSIZED | ORDERED` characteristics and midpoint
       splitting. `[SOURCE]`
3.1.29 `RandomAccess` as a zero-method marker and the algorithms that branch on it.
3.1.30 `OutOfMemoryError: Requested array size exceeds VM limit` vs
       `OutOfMemoryError: Java heap space` when a list grows too large. `[X-REF 06]` `[TRAP]`
3.1.31 `Vector`'s contrast: `synchronized` on every method, `capacityIncrement`, 2× growth.
       `[SOURCE]`
3.1.32 `CopyOnWriteArrayList`: `volatile Object[] array`, `ReentrantLock lock`, `setArray`/`getArray`,
       every mutator copies. `[SOURCE]`

*(32 leaves)*

### §3.2 Amortised analysis, properly

3.2.1 Definition: amortised cost is total cost over a sequence divided by the number of
      operations — a worst-case-over-a-sequence bound, not an average over a distribution.
      `[PROVE]`
3.2.2 The aggregate method for `ArrayList.add`: n adds with growth factor g cost
      `n + Σ capacities` copies; the geometric series sums to `n·g/(g−1)`. For g = 1.5 that is 3n.
      `[PROVE]` `[NUM]`
3.2.3 The accounting (banker's) method: each add pays 3 credits; a resize spends the saved credits.
      `[PROVE]`
3.2.4 The potential-function method: Φ = 2·size − capacity, and the invariant it maintains.
      `[PROVE]`
3.2.5 Why any growth factor > 1 gives O(1) amortised, and factor 1 (add-one) gives O(n).
      `[PROVE]`
3.2.6 Why the JDK chose 1.5× not 2×: the memory-reuse argument (with 1.5× the freed blocks can be
      coalesced to satisfy a later allocation; with 2× they never can), and the peak-memory
      argument (2.5× vs 3× live during copy). `[PROVE]` `[RESEARCH]`
3.2.7 The counter-argument: 1.5× means more resizes, so more `arraycopy` work — quantify it.
      `[NUM]`
3.2.8 What other runtimes do: Python list ~1.125×+constant, C++ `std::vector` 2× (GCC) / 1.5×
      (MSVC), Go slices 2× then 1.25×. `[RESEARCH]`
3.2.9 Amortised O(1) does *not* mean predictable latency: the resize is a single O(n) pause, which
      matters for tail latency. `[TRAP]`
3.2.10 `HashMap.put` amortised O(1) via the same argument, plus the load-factor bound on chain
       length. `[PROVE]`
3.2.11 `ArrayDeque` amortised O(1) at both ends. `[PROVE]`
3.2.12 `PriorityQueue.offer` is O(log n) worst case but its *expected* sift distance is O(1).
       `[PROVE]`
3.2.13 `heapify` is O(n), not O(n log n) — the Σ h/2^h argument. `[PROVE]`
3.2.14 Why building a heap from a collection then polling everything is O(n + n log n) and not
       better than sorting.

*(14 leaves)*

### §3.3 `LinkedList` source walk

3.3.1 `Node<E>` with `item`, `next`, `prev`; `first`, `last`, `size` fields. `[SOURCE]`
3.3.2 `node(int index)`: `if (index < (size >> 1))` walk forward from `first`, else backward from
      `last`. `[SOURCE]` `[PROVE]`
3.3.3 `linkFirst`, `linkLast`, `linkBefore`, `unlinkFirst`, `unlinkLast`, `unlink`. `[SOURCE]`
3.3.4 `unlink` nulls `item`, `next` and `prev` explicitly — "help GC". `[SOURCE]` `[PROVE]`
3.3.5 `ListItr` holding `next`, `nextIndex`, `lastReturned` — the only place `LinkedList`'s O(1)
      insertion is reachable. `[SOURCE]`
3.3.6 `LinkedList` implements `Deque`: `addFirst`/`addLast`/`peek`/`poll`/`push`/`pop`,
      and permits nulls unlike `ArrayDeque`.
3.3.7 Memory per element: `Node` header 12 B + 3 refs 12 B → 24 B aligned, plus the element.
      Versus 4 B per `ArrayList` slot. `[NUM]` `[PROVE]`
3.3.8 Pointer chasing and cache misses: n nodes scattered across the heap vs one contiguous array.
      `[X-REF 06]`
3.3.9 Why `LinkedList` loses even for middle insertion in practice: you must `get(i)` to find the
      position, which is O(n) pointer-chasing, while `ArrayList`'s O(n) shift is a single
      vectorised `memmove`. `[PROVE]` `[TRAP]`
3.3.10 The one case `LinkedList` genuinely wins: an intrusive queue where you hold the node — which
       the JDK API does not expose. So: never. `[TRAP]`
3.3.11 `LinkedList` has no `Spliterator` with `SIZED|SUBSIZED` splitting — `LLSpliterator` splits
       by walking, so parallel streams over it are poor. `[SOURCE]`
3.3.12 `Collections.reverse`, `binarySearch`, `shuffle` all take the non-`RandomAccess` branch for
       `LinkedList`.

*(12 leaves)*

### §3.4 `ArrayDeque` source walk

3.4.1 Fields: `transient Object[] elements; transient int head; transient int tail;` `[SOURCE]`
3.4.2 The invariant: `elements[head]` is the first element; `elements[tail]` is the next write
      slot; the array always has at least one empty slot, so `head == tail` means empty.
      `[SOURCE]` `[PROVE]`
3.4.3 `[VERSION-TRAP]` Capacity is **not** required to be a power of two in Java 21. The
      power-of-two + bitmask design (`(head - 1) & (elements.length - 1)`) was the Java 8
      implementation; JDK 9 rewrote the class to use explicit wraparound helpers. State both,
      and say which JDK changed. `[RESEARCH]` `[SOURCE]`
3.4.4 The wraparound helpers: `inc(int i, int modulus)`, `dec(int i, int modulus)`,
      `sub(int i, int j, int modulus)`, `inc(int i, int distance, int modulus)`. `[SOURCE]`
      `[RESEARCH]`
3.4.5 No-arg constructor allocates `new Object[16 + 1]` — capacity 17, one slot reserved.
      `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.6 `ArrayDeque(int numElements)` allocates `numElements + 1`, with overflow handling.
      `[SOURCE]`
3.4.7 `grow(int needed)`: `jump = (oldCapacity < 64) ? (oldCapacity + 2) : (oldCapacity >> 1)` —
      doubling-ish while small, 1.5× when large. `[SOURCE]` `[NUM]` `[RESEARCH]`
3.4.8 `grow` must un-wrap the circular buffer: after `Arrays.copyOf`, if `tail < head` it slides
      the head-side segment to the end of the new array. `[SOURCE]` `[PROVE]`
3.4.9 `MAX_ARRAY_SIZE = Integer.MAX_VALUE - 8` and `newCapacity`'s overflow check. `[SOURCE]`
      `[NUM]`
3.4.10 `addFirst`: `elements[head = dec(head, es.length)] = e`. `[SOURCE]`
3.4.11 `addLast`: `es[tail] = e; if (head == (tail = inc(tail, es.length))) grow(1);` `[SOURCE]`
3.4.12 `pollFirst`/`pollLast` nulling the vacated slot.
3.4.13 The two-disjoint-slices traversal pattern and the class comment explaining why the loops
       look strange (VM loop optimisation). `[SOURCE]` `[RESEARCH]`
3.4.14 Null prohibition as a consequence of using `null` as the empty marker. `[PROVE]`
3.4.15 `size()` computed as `sub(tail, head, elements.length)`. `[SOURCE]`
3.4.16 Why `ArrayDeque` beats `LinkedList` for queues (no per-element node, contiguous memory) and
       `Stack` for stacks (no synchronization, correct iteration order). `[PROVE]`
3.4.17 `ArrayDeque` is not a `List` — no indexed access, and `contains` is O(n).
3.4.18 `ArrayDeque` in Java 21 implements `SequencedCollection`; `reversed()` returns a view.
3.4.19 `ArrayDeque.clone()` and `writeObject`/`readObject` linearising the buffer.

*(19 leaves)*

### §3.5 `PriorityQueue` source walk

3.5.1 `DEFAULT_INITIAL_CAPACITY = 11`. `[SOURCE]` `[NUM]`
3.5.2 Fields: `transient Object[] queue; int size; private final Comparator<? super E> comparator;
      transient int modCount;` `[SOURCE]`
3.5.3 Array-embedded binary heap indexing: parent `(k - 1) >>> 1`, children `2k + 1` and `2k + 2`.
      `[SOURCE]` `[PROVE]`
3.5.4 `grow(int minCapacity)`:
      `ArraysSupport.newLength(oldCapacity, minCapacity - oldCapacity, oldCapacity < 64 ?
      oldCapacity + 2 : oldCapacity >> 1)` — the same double-then-1.5× policy as `ArrayDeque`.
      `[SOURCE]` `[NUM]` `[RESEARCH]`
3.5.5 `offer`: place at `size`, then `siftUp`. `[SOURCE]`
3.5.6 `siftUp` split into `siftUpComparable` and `siftUpUsingComparator` — deliberate duplication
      so the JIT can inline the monomorphic comparison. `[SOURCE]` `[PROVE]`
3.5.7 `poll`: take `queue[0]`, move the last element to the root, `siftDown`. `[SOURCE]`
3.5.8 `siftDown` picking the smaller child before comparing. `[SOURCE]`
3.5.9 `heapify()`: `for (int i = (size >>> 1) - 1; i >= 0; i--) siftDown(i, es[i]);` and its O(n)
      bound. `[SOURCE]` `[PROVE]`
3.5.10 The `PriorityQueue(Collection)` constructor's fast path for `SortedSet`/`PriorityQueue`
       (already heap-ordered) vs `heapify`. `[SOURCE]`
3.5.11 `removeAt(int i)` returning the moved element so the iterator can re-visit it — the
       `forgetMeNot` deque in `Itr`. `[SOURCE]` `[TRAP]`
3.5.12 `indexOf`/`remove(Object)`/`contains` are O(n) linear scans. `[SOURCE]`
3.5.13 Iteration and `toString` are array order, not sorted order. `[TRAP]`
3.5.14 Mutating an element's priority field after insertion silently corrupts the heap invariant.
       Remove → mutate → re-insert, or use an index-tracking heap. `[TRAP]`
3.5.15 No stability: equal-priority elements come out in unspecified order. Fix by adding a
       monotonic sequence number to the comparator. `[TRAP]` `[BUILD]`
3.5.16 Max-heap via `Comparator.reverseOrder()` or `Comparator.comparingInt(...).reversed()`.
3.5.17 `PriorityQueue` is unbounded — a bounded top-k needs a size check plus a reversed
       comparator. `[BUILD]`
3.5.18 `PriorityBlockingQueue`'s differences: `ReentrantLock`, `Condition notEmpty`, spinlock
       `allocationSpinLock` for growth outside the main lock. `[SOURCE]`
3.5.19 Indexed/decrease-key heaps (Dijkstra) and why the JDK's has no `decreaseKey`.
       `[X-REF 01]`
3.5.20 Fibonacci/pairing heaps: the theoretical alternative and why nobody ships one.

*(20 leaves)*

### §3.6 `HashMap` source walk

3.6.1 `DEFAULT_INITIAL_CAPACITY = 1 << 4` (16). `[SOURCE]` `[NUM]`
3.6.2 `MAXIMUM_CAPACITY = 1 << 30`. `[SOURCE]` `[NUM]`
3.6.3 `DEFAULT_LOAD_FACTOR = 0.75f`. `[SOURCE]` `[NUM]`
3.6.4 `TREEIFY_THRESHOLD = 8`. `[SOURCE]` `[NUM]`
3.6.5 `UNTREEIFY_THRESHOLD = 6`. `[SOURCE]` `[NUM]`
3.6.6 `MIN_TREEIFY_CAPACITY = 64`. `[SOURCE]` `[NUM]`
3.6.7 Fields: `transient Node<K,V>[] table; transient Set<Map.Entry<K,V>> entrySet;
      transient int size; transient int modCount; int threshold; final float loadFactor;`
      `[SOURCE]`
3.6.8 `threshold` doubles as "the initial capacity to allocate" before the table exists — the
      overloaded-field trick. `[SOURCE]` `[TRAP]`
3.6.9 `Node<K,V>` with `final int hash; final K key; V value; Node<K,V> next;` `[SOURCE]`
3.6.10 The cached `hash` field: why the map stores it rather than recomputing (avoids re-calling
       a user `hashCode`, and makes resize free of user code). `[PROVE]`
3.6.11 `static final int hash(Object key)`:
       `(key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16)`. `[SOURCE]`
3.6.12 Why spread at all: `index = (n - 1) & hash` keeps only the low `log2(n)` bits, so a
       `hashCode` whose entropy lives in the high bits collides catastrophically. Worked example
       with `Integer` keys that are multiples of 65536. `[PROVE]` `[NUM]`
3.6.13 Why only one xor-shift and not a full avalanche (Java 7 used four shifts): a cheap mix is
       enough now that long bins treeify. `[PROVE]` `[RESEARCH]`
3.6.14 Null keys hash to 0 → always bucket 0. `[PROVE]`
3.6.15 `tableSizeFor(int cap)`:
       `int n = -1 >>> Integer.numberOfLeadingZeros(cap - 1); return (n < 0) ? 1 : ...n + 1;`
       — round up to the next power of two. `[SOURCE]` `[PROVE]`
3.6.16 Power-of-two capacity as the reason the index is a mask, and the reason resize is a single
       bit test. `[PROVE]`
3.6.17 `getNode(Object key)`: check `first`, then branch on `TreeNode` vs list walk. `[SOURCE]`
3.6.18 The `==` before `equals` short-circuit in the node comparison
       (`e.hash == hash && ((k = e.key) == key || (key != null && key.equals(k)))`). `[SOURCE]`
       `[PROVE]`
3.6.19 `putVal(int hash, K key, V value, boolean onlyIfAbsent, boolean evict)`. `[SOURCE]`
3.6.20 `putVal` bucket-empty fast path: `tab[i] = newNode(hash, key, value, null)`. `[SOURCE]`
3.6.21 `putVal` chain walk with `binCount` and the `>= TREEIFY_THRESHOLD - 1` check. `[SOURCE]`
3.6.22 `treeifyBin(tab, hash)`: if `tab.length < MIN_TREEIFY_CAPACITY` call `resize()` instead of
       treeifying. `[SOURCE]` `[PROVE]`
3.6.23 `resize()` verbatim: the `oldThr`/`newThr` doubling, and the transfer loop. `[SOURCE]`
3.6.24 The lo/hi split, verbatim:
       `if ((e.hash & oldCap) == 0)` → lo list at index `j`, else hi list at index `j + oldCap`.
       `[SOURCE]` `[PROVE]`
3.6.25 Why exactly one bit decides: the new mask has one more bit than the old, and that bit is
       `oldCap`. `[PROVE]`
3.6.26 The split preserves relative order within each bin — which is what fixed Java 7's
       list-reversal-during-transfer. `[PROVE]`
3.6.27 The Java 7 concurrent-resize infinite loop: two threads transferring the same bin build a
       cycle, and a later `get` spins at 100% CPU forever. The exact node-pointer sequence.
       `[PROVE]` `[TRAP]`
3.6.28 Java 8 does not infinite-loop, but a concurrent resize still loses entries, resurrects
       removed entries, and can NPE. It is still a bug, just a quieter one. `[TRAP]`
3.6.29 `split()` on a `TreeNode` bin during resize, with `UNTREEIFY_THRESHOLD` deciding whether
       each half stays a tree. `[SOURCE]`
3.6.30 `TreeNode` extends `LinkedHashMap.Entry` extends `HashMap.Node` — so a tree node carries
       `parent`, `left`, `right`, `prev`, `red`, *plus* `before`/`after`. Memory cost of that
       inheritance chain. `[SOURCE]` `[NUM]` `[TRAP]`
3.6.31 `TreeNode.putTreeVal`, `find`, `getTreeNode` and the `tieBreakOrder` fallback when keys are
       not `Comparable`. `[SOURCE]` `[PROVE]`
3.6.32 `comparableClassFor(Object x)` — treeified bins only use `compareTo` if the key class
       directly implements `Comparable<thatClass>`. `[SOURCE]` `[RESEARCH]`
3.6.33 The Poisson justification for load factor 0.75 and treeify threshold 8: with λ = 0.5, the
       probability a bin holds k elements is `e^-0.5 * 0.5^k / k!`; k = 8 gives ~6×10⁻⁸.
       Reproduce the table from the class comment. `[SOURCE]` `[PROVE]` `[NUM]`
3.6.34 Why 6 for untreeify and not 8: hysteresis prevents thrash at the boundary. `[PROVE]`
3.6.35 Hash-collision DoS (CVE-2011-4858 / the 28C3 "Efficient Denial of Service Attacks" talk):
       n colliding keys turn an O(n) insert loop into O(n²). Treeification bounds it at
       O(n log n). `[RESEARCH]` `[PROVE]`
3.6.36 Why the JDK chose treeification over randomised hashing (Java 7u6's
       `jdk.map.althashing.threshold`, later removed). `[RESEARCH]`
3.6.37 Sizing arithmetic: `new HashMap<>(100)` → `tableSizeFor(100)` = 128, threshold 96. To hold
       n without resize, pass `(int)(n / 0.75f) + 1`. `[PROVE]` `[NUM]` `[TRAP]`
3.6.38 `HashMap.newHashMap(int numMappings)` (Java 19) and
       `LinkedHashMap.newLinkedHashMap`, `HashSet.newHashSet`, `LinkedHashSet.newLinkedHashSet`
       — the arithmetic done for you. `[SOURCE]` `[RESEARCH]`
3.6.39 `putMapEntries` pre-sizing on `putAll` and on the copy constructor. `[SOURCE]`
3.6.40 Non-default load factors: 0.5 (faster lookups, 2× memory) vs 1.0 (dense, longer chains) —
       and why almost nobody should change it. `[PROVE]`
3.6.41 `removeNode` and how removal never shrinks the table. A map that held 10M entries still
       owns a 16M-slot array after `clear()`… except `clear()` nulls the table entries but keeps
       the array. `[TRAP]` `[NUM]`
3.6.42 Iteration order of `HashMap`: table order then bin order — deterministic for a given
       insertion sequence and capacity, but changes on resize, and is not part of the contract.
       `[TRAP]`
3.6.43 `keySet`/`values`/`entrySet` as cached view instances; `HashIterator` walking the table.
       `[SOURCE]`
3.6.44 `HashMap` `forEach`/`replaceAll` with their own `modCount` checks. `[SOURCE]`
3.6.45 `afterNodeAccess`/`afterNodeInsertion`/`afterNodeRemoval` — empty hooks that exist purely
       for `LinkedHashMap`. `[SOURCE]`
3.6.46 `Hashtable` contrast: prime-ish capacity 11, `2n+1` growth, `hash % length` with a modulo,
       and `synchronized` methods. `[SOURCE]` `[PROVE]`
3.6.47 Why `HashMap` chose power-of-two + spread over prime modulus: mask is one instruction,
       `idiv` is ~20–40 cycles. `[PROVE]` `[NUM]`

*(47 leaves)*

### §3.7 `LinkedHashMap` source walk

3.7.1 `Entry<K,V> extends HashMap.Node<K,V>` adding `before` and `after`. `[SOURCE]`
3.7.2 Fields `transient LinkedHashMap.Entry<K,V> head, tail; final boolean accessOrder;`
      `[SOURCE]`
3.7.3 `linkNodeLast` and `afterNodeInsertion(boolean evict)` calling `removeEldestEntry`.
      `[SOURCE]`
3.7.4 `afterNodeAccess(Node)` unlinking and relinking at the tail — only when `accessOrder`.
      `[SOURCE]`
3.7.5 `afterNodeRemoval` unlinking from the overlay. `[SOURCE]`
3.7.6 `newNode` override so `HashMap`'s allocation path produces linked entries. `[PROVE]`
3.7.7 `containsValue` overridden to walk the linked list instead of the table. `[SOURCE]`
3.7.8 `get` vs `getOrDefault` both trigger `afterNodeAccess`; `containsKey` does **not**.
      `[TRAP]` `[RESEARCH]`
3.7.9 `removeEldestEntry(Map.Entry)` — the protected hook, default `false`. `[SOURCE]`
3.7.10 The LRU cache in ten lines, and the four bugs in the naive version (no size bound, wrong
       constructor arg order, `accessOrder` forgotten, not thread-safe). `[BUILD]` `[TRAP]`
3.7.11 Access-order mode makes `get` a structural modification from the iterator's point of view,
       so concurrent reads are unsafe. `[PROVE]` `[TRAP]`
3.7.12 An FIFO cache is the same class with `accessOrder = false`.
3.7.13 Java 21 `SequencedMap` implementation: `putFirst`, `putLast`, `firstEntry`, `lastEntry`,
       `pollFirstEntry`, `pollLastEntry`, `sequencedKeySet`, `reversed()` →
       `ReversedLinkedHashMapView`. `[SOURCE]` `[RESEARCH]`
3.7.14 `putFirst` on an access-order map — the interaction that surprises. `[TRAP]` `[RESEARCH]`
3.7.15 Memory cost of the overlay: 2 extra references per entry = 8 bytes with compressed oops.
       `[NUM]`
3.7.16 `LinkedHashSet` as `LinkedHashMap`-backed, and `LinkedHashSet.newLinkedHashSet` (19).
3.7.17 Why a real cache uses Caffeine instead: O(1) eviction with better hit rates (W-TinyLFU),
       expiry, async loading, weight-based bounds, no global lock. `[X-REF 15]`

*(17 leaves)*

### §3.8 `TreeMap` and red-black trees

3.8.1 The five red-black invariants: every node red or black; root black; (NIL leaves black);
      no red node has a red child; every root-to-leaf path has the same black-height.
3.8.2 Height bound: `h ≤ 2 log₂(n+1)`. `[PROVE]`
3.8.3 Why balance matters: an unbalanced BST degenerates to a linked list on sorted insertion.
      `[PROVE]`
3.8.4 `Entry<K,V>` with `key`, `value`, `left`, `right`, `parent`, `color`. `[SOURCE]`
3.8.5 `rotateLeft`/`rotateRight` — the pointer surgery, drawn out. `[SOURCE]`
3.8.6 `fixAfterInsertion` — the recolour / uncle-red / uncle-black-zigzag / uncle-black-straight
      cases. `[SOURCE]` `[PROVE]`
3.8.7 `fixAfterDeletion` — the harder six cases and the "double black" concept. `[SOURCE]`
      `[PROVE]`
3.8.8 `deleteEntry` and the successor-swap trick for two-child deletion. `[SOURCE]`
3.8.9 `successor`/`predecessor` and why in-order traversal is amortised O(1) per step. `[PROVE]`
3.8.10 `getEntry` vs `getEntryUsingComparator` — again duplicated for JIT monomorphism. `[SOURCE]`
3.8.11 `compare(k1,k2)` routing through the comparator or `Comparable`, and the `ClassCastException`
       when keys are not mutually comparable. `[SOURCE]`
3.8.12 `TreeMap` uses `compare(...) == 0` for key identity, **never** `equals` — how a
       one-field comparator silently collapses distinct objects in a `TreeSet`. `[PROVE]` `[TRAP]`
3.8.13 Consequence: `TreeSet.contains` can return true for an object that is not `equals` to any
       member, and `TreeMap.equals` (inherited from `AbstractMap`, which uses `equals`) can then
       disagree with `containsKey`. `[TRAP]` `[PROVE]`
3.8.14 Null keys rejected because `compareTo` would NPE — but a comparator that tolerates null
       makes null keys work. `[TRAP]`
3.8.15 `buildFromSorted` — the O(n) bulk construction used by `putAll` from a `SortedMap` and by
       deserialization, which builds a perfectly balanced tree directly. `[SOURCE]` `[PROVE]`
3.8.16 `NavigableSubMap`/`AscendingSubMap`/`DescendingSubMap` — the range-view classes and their
       `inRange` checks. `[SOURCE]`
3.8.17 `TreeMap` memory per entry: header 12 + 5 refs 20 + colour byte → 40 bytes aligned, plus
       key and value. Versus `HashMap`'s 32-byte `Node`. `[NUM]` `[PROVE]`
3.8.18 Why `TreeMap` is O(log n) with a *large* constant: pointer chasing plus a virtual
       `compareTo` call per level. `[PROVE]`
3.8.19 AVL vs red-black: AVL is more rigidly balanced (faster lookup, more rotations on write);
       red-black wins for write-heavy. Why the JDK picked red-black. `[X-REF 01]`
3.8.20 B-tree contrast for the disk case. `[X-REF 09]`
3.8.21 `ConcurrentSkipListMap` as the concurrent alternative: probabilistic levels, `p = 0.25`,
       CAS-based insertion, marker nodes for deletion, `HeadIndex`. `[RESEARCH]`
3.8.22 Skip list vs red-black tree: why lock-free is easy on one and hard on the other. `[PROVE]`
3.8.23 `TreeSet` as a `TreeMap` wrapper with `PRESENT`; `TreeSet(Collection)` vs
       `TreeSet(SortedSet)` construction cost. `[SOURCE]`

*(23 leaves)*

### §3.9 The Set-over-Map wrapper pattern

3.9.1 `HashSet` field `private transient HashMap<E,Object> map;` and
      `private static final Object PRESENT = new Object();`. `[SOURCE]`
3.9.2 `add(e)` is `map.put(e, PRESENT) == null`. `[SOURCE]`
3.9.3 The package-private `HashSet(int, float, boolean dummy)` constructor that
      `LinkedHashSet` uses to get a `LinkedHashMap`. `[SOURCE]` `[RESEARCH]`
3.9.4 Every `HashMap` fact transfers to `HashSet`: capacity 16, load factor 0.75, treeify at 8.
3.9.5 Memory consequence: a `HashSet<E>` costs a full `HashMap.Node` (32 B) plus the shared
      `PRESENT` — you pay for a value field you never use. `[NUM]`
3.9.6 `Collections.newSetFromMap` generalising the pattern to any map.
3.9.7 `TreeSet` over `TreeMap`, `ConcurrentSkipListSet` over `ConcurrentSkipListMap`,
      `ConcurrentHashMap.newKeySet()` over `ConcurrentHashMap`.
3.9.8 `CopyOnWriteArraySet` breaks the pattern — it wraps a `CopyOnWriteArrayList`, so `add` is
      O(n) and `contains` is O(n). `[TRAP]` `[NUM]`
3.9.9 `EnumSet` breaks the pattern entirely — bit vector, no map.

*(9 leaves)*

### §3.10 `EnumMap` and `EnumSet` internals

3.10.1 `EnumMap` fields: `keyType`, `transient K[] keyUniverse`, `transient Object[] vals`,
       `transient int size`. `[SOURCE]` `[RESEARCH]`
3.10.2 `keyUniverse` obtained via `SharedSecrets.getJavaLangAccess().getEnumConstantsShared` —
       a shared, uncloned array. `[SOURCE]` `[RESEARCH]`
3.10.3 `put(key, value)` = `vals[key.ordinal()] = maskNull(value)`; O(1) with no hashing.
       `[SOURCE]`
3.10.4 `NULL` sentinel object, `maskNull`/`unmaskNull`, so a null value is distinguishable from
       an absent key. `[SOURCE]` `[RESEARCH]`
3.10.5 Iteration in ordinal (declaration) order, skipping null slots. `[SOURCE]`
3.10.6 The reused `lastReturnedEntry` object in `EntryIterator` — collecting `entrySet()` into a
       list gives n aliases of one mutating object. `[SOURCE]` `[TRAP]` `[RESEARCH]`
3.10.7 Memory: one reference slot per enum constant whether used or not. Cheap for small enums,
       wasteful for a 500-constant enum with 3 mappings. `[NUM]` `[TRAP]`
3.10.8 `EnumSet.noneOf` choosing `RegularEnumSet` (≤64) or `JumboEnumSet`. `[SOURCE]` `[RESEARCH]`
3.10.9 `RegularEnumSet` holds a single `long elements`; membership is
       `(elements & (1L << e.ordinal())) != 0`. `[SOURCE]` `[PROVE]`
3.10.10 `JumboEnumSet` holds `long[] elements` and a cached `size`. `[SOURCE]`
3.10.11 `RegularEnumSet.addAll(EnumSet)` becomes `elements |= other.elements` — one instruction
        for an arbitrarily large union. `[SOURCE]` `[PROVE]`
3.10.12 `complementOf` = `~elements & mask`. `[SOURCE]`
3.10.13 Ordinal dependence: reordering enum constants changes `EnumMap`/`EnumSet` iteration order
        and breaks any persisted ordinal. `[TRAP]`
3.10.14 Why enum-keyed `HashMap` is worse: identity `hashCode` varies per run, so iteration order
        is irreproducible, plus hashing cost. `[PROVE]` `[TRAP]`

*(14 leaves)*

### §3.11 `IdentityHashMap` and `WeakHashMap` internals

3.11.1 `IdentityHashMap` `table` holds key at `i` and value at `i+1` — one flat array, no `Node`
       objects at all. `[SOURCE]`
3.11.2 `hash(Object x, int length)` = `System.identityHashCode(x)` scrambled, then masked to an
       even index. `[SOURCE]`
3.11.3 Linear probing with `nextKeyIndex`, and the `closeDeletion` pass that repairs the probe
       sequence after a removal. `[SOURCE]` `[PROVE]`
3.11.4 `DEFAULT_CAPACITY = 32`, `MINIMUM_CAPACITY = 4`, `MAXIMUM_CAPACITY = 1 << 29`, load factor
       fixed at 2/3 implicitly (`size*3 > len`). `[SOURCE]` `[NUM]` `[RESEARCH]`
3.11.5 `NULL_KEY` sentinel so null keys work. `[SOURCE]`
3.11.6 Deliberate `Map`-contract violation documented in the javadoc. `[SOURCE]`
3.11.7 Use cases: object graph traversal, serialization cycle detection, proxy registries,
       `IdentityHashMap`-based `newSetFromMap` for "have I seen this exact object".
3.11.8 `WeakHashMap.Entry extends WeakReference<Object>` — the entry *is* the reference.
       `[SOURCE]` `[PROVE]`
3.11.9 `private final ReferenceQueue<Object> queue` and `expungeStaleEntries()` invoked from
       `getTable`, `size`, `resize`, etc. `[SOURCE]`
3.11.10 The clearing sequence: key becomes weakly reachable → GC clears the referent and enqueues
        → next map operation drains the queue and unlinks. So the entry survives an arbitrary time
        after the key dies. `[PROVE]` `[TRAP]`
3.11.11 Value-holds-key leak and the `WeakReference`-wrapped-value fix. `[PROVE]` `[TRAP]`
3.11.12 Interned `String`/boxed-`Integer`-cache/`Class` keys never clear. `[TRAP]`
3.11.13 `ThreadLocal`'s internal `ThreadLocalMap` uses weak keys with the same shape, and its
        stale-value leak. `[X-REF 05]`
3.11.14 `size()` on a `WeakHashMap` has side effects and can shrink between two calls. `[TRAP]`

*(14 leaves)*

### §3.12 `ImmutableCollections` internals (Java 9+)

3.12.1 `List.of` overloads for 0–10 elements plus varargs, to avoid array allocation for small
       lists. `[SOURCE]` `[NUM]`
3.12.2 `List12<E>` holding `e0` and `e1` with an `EMPTY` sentinel for the absent second element.
       `[SOURCE]` `[RESEARCH]`
3.12.3 `ListN<E>` with an `Object[] elements` and an `allowNulls` flag. `[SOURCE]` `[RESEARCH]`
3.12.4 `listFromTrustedArray` vs `listFromArray` — when the array is copied and when it is not.
       `[SOURCE]` `[RESEARCH]`
3.12.5 `Set12`/`SetN` and `Map1`/`MapN`. `[SOURCE]`
3.12.6 `SetN`/`MapN` use **open addressing with linear probing**, not chaining, and allocate
       `EXPAND_FACTOR * n` slots (factor 2) so there is always a free slot. `[SOURCE]` `[PROVE]`
       `[RESEARCH]`
3.12.7 `probe(Object pe)` returning `i` if found or `-(i + 1)` for the free slot. `[SOURCE]`
       `[RESEARCH]`
3.12.8 `MapN` stores keys and values interleaved in one array (`table[2i]`, `table[2i+1]`).
       `[SOURCE]`
3.12.9 `SALT32L` derived from `System.nanoTime()` at class-init, and `REVERSE` from its low bit.
       `[SOURCE]` `[RESEARCH]`
3.12.10 Iteration order of `Set.of`/`Map.of` is randomised **per JVM run**, deliberately, to stop
        code depending on it. Demonstrate with two runs. `[PROVE]` `[TRAP]` `[RESEARCH]`
3.12.11 CDS/AOT interaction: the salt can come from the CDS archive so archived immutable
        collections stay consistent. `[RESEARCH]`
3.12.12 Null hostility: `List.of(null)` NPEs, `Set.of(...).contains(null)` NPEs on some paths,
        `Map.of(k, null)` NPEs. `[TRAP]` `[RESEARCH]`
3.12.13 `AbstractImmutableCollection` throwing `UnsupportedOperationException` from every mutator,
        including `removeIf` and `sort`. `[SOURCE]`
3.12.14 Serialization via `writeReplace()` → `CollSer` proxy with a tag; `readObject` throws
        `InvalidObjectException("not serial proxy")`. `[SOURCE]` `[RESEARCH]`
3.12.15 `SubList` of an immutable list delegates to the root with an offset. `[SOURCE]`
3.12.16 `ReverseOrderListView` backing `List.reversed()` (Java 21). `[SOURCE]` `[RESEARCH]`
3.12.17 Memory: `List.of(a,b)` is one object with two fields — no array, no capacity slack.
        Compare with `new ArrayList<>(List.of(a,b))`. `[NUM]` `[PROVE]`
3.12.18 `Collections.emptyList()`/`singletonList()` as the pre-Java-9 allocation-free path, and
        which is cheaper today.

*(18 leaves)*

### §3.13 `Spliterator`, parallelism, and the stream bridge

3.13.1 Why `Spliterator` exists: `Iterator` cannot be split, so it cannot feed a fork-join
       decomposition. `[PROVE]`
3.13.2 `tryAdvance` vs `forEachRemaining` and the bulk-traversal fast path.
3.13.3 `trySplit` contract: return a prefix, keep the suffix, or return null when not splittable.
3.13.4 Characteristics: `ORDERED`, `DISTINCT`, `SORTED`, `SIZED`, `NONNULL`, `IMMUTABLE`,
       `CONCURRENT`, `SUBSIZED` — and what each enables in the pipeline.
3.13.5 Per-collection characteristics table: `ArrayList` (`ORDERED|SIZED|SUBSIZED`),
       `HashSet` (`SIZED|DISTINCT`), `TreeSet` (`+SORTED|ORDERED`), `LinkedList` (`ORDERED|SIZED`,
       poor splits), `ConcurrentHashMap` (`CONCURRENT|NONNULL`, no `SIZED`), `List.of`
       (`+IMMUTABLE`). `[RESEARCH]`
3.13.6 `SIZED|SUBSIZED` is what lets fork-join pre-size the output arrays; without it the
       pipeline buffers. `[PROVE]`
3.13.7 Why `ArrayList.parallelStream()` scales and `LinkedList.parallelStream()` does not.
       `[PROVE]`
3.13.8 `HashMap`'s spliterator splits the table by index range, so split balance depends on how
       evenly the entries are distributed. `[SOURCE]`
3.13.9 `IteratorSpliterator` — the generic fallback with `BATCH_UNIT = 1024` and
       `MAX_BATCH = 1 << 25`, splitting by arithmetically growing batches. `[SOURCE]` `[NUM]`
       `[RESEARCH]`
3.13.10 `Spliterators.spliterator(...)`/`spliteratorUnknownSize` for writing your own.
3.13.11 `StreamSupport.stream(spliterator, parallel)`.
3.13.12 Late binding and the fail-fast contract of a spliterator: `IMMUTABLE`/`CONCURRENT`
        spliterators must not throw CME; others may.
3.13.13 The parallel-stream decision rule: N × Q (size × per-element cost) must be large; the
        common pool is shared; a blocking op in a parallel stream starves the pool.
        `[TRAP]` `[X-REF 04]`
3.13.14 `Collectors.toList` on a parallel stream and the merge cost. `[PROVE]`
3.13.15 `forEachOrdered` vs `forEach` on a parallel stream over an `ORDERED` source.
3.13.16 Writing a `Spliterator` for a custom collection. `[BUILD]`

*(16 leaves)*

### §3.14 Concurrency behaviour of collections

3.14.1 What "not thread-safe" actually costs: lost updates, torn state, infinite loops, and
       visibility failures without a memory barrier. `[X-REF 05]`
3.14.2 Unsafe publication of a collection built on one thread and read on another. `[X-REF 05]`
3.14.3 `Collections.synchronizedX`: one mutex, every method wrapped, `SynchronizedCollection.mutex`.
       `[SOURCE]`
3.14.4 Synchronized wrappers do not make iteration safe — you must
       `synchronized (wrapper) { for (...) }`, and the javadoc says so. `[SOURCE]` `[TRAP]`
3.14.5 Synchronized wrappers do not make compound actions atomic (`if (!m.containsKey(k))
       m.put(k,v)`). `[TRAP]`
3.14.6 The `synchronizedMap(...).keySet()` view is *not* synchronized on the same mutex in all
       JDK versions — check before relying on it. `[RESEARCH]` `[TRAP]`
3.14.7 `ConcurrentHashMap` structure: `volatile Node<K,V>[] table`, `nextTable`, `sizeCtl`,
       `baseCount`, `CounterCell[] counterCells`, `transferIndex`. `[SOURCE]`
3.14.8 `sizeCtl` encoding: −1 = initialising; negative = `-(1 + resizers)`; positive = threshold.
       `[SOURCE]` `[NUM]`
3.14.9 `spread(int h)` = `(h ^ (h >>> 16)) & HASH_BITS` where `HASH_BITS = 0x7fffffff` — the top
       bit is reserved for special nodes. `[SOURCE]` `[NUM]`
3.14.10 Special node hashes: `MOVED = -1` (`ForwardingNode`), `TREEBIN = -2`, `RESERVED = -3`.
        `[SOURCE]` `[NUM]` `[RESEARCH]`
3.14.11 `putVal`: `tabAt` volatile read, `casTabAt` for an empty bin, `synchronized (f)` on the bin
        head otherwise. `[SOURCE]`
3.14.12 `get` is entirely lock-free — volatile reads only. `[PROVE]`
3.14.13 Cooperative resize: `transfer` splits the table into stride-sized chunks
        (`MIN_TRANSFER_STRIDE = 16`), `transferIndex` claimed by CAS, and a `ForwardingNode`
        installed in each migrated bin so readers follow to `nextTable`. `[SOURCE]` `[PROVE]`
        `[RESEARCH]`
3.14.14 `helpTransfer` — a writer that lands on a `ForwardingNode` joins the resize instead of
        blocking. `[SOURCE]` `[PROVE]`
3.14.15 `size()` via `sumCount()` over `baseCount` + `CounterCells` — striped counters to avoid a
        single contended field; hence `size()` is an estimate. `mappingCount()` returns `long`.
        `[SOURCE]` `[TRAP]`
3.14.16 `CounterCell` is `@Contended` to avoid false sharing. `[SOURCE]` `[NUM]` `[X-REF 06]`
3.14.17 `TreeBin` with its own `lockState` read-write lock, distinct from `HashMap`'s `TreeNode`.
        `[SOURCE]`
3.14.18 Atomic compound methods: `putIfAbsent`, `computeIfAbsent`, `computeIfPresent`, `compute`,
        `merge`, `replace(k,old,new)`, `remove(k,v)` — all hold the bin lock.
3.14.19 `computeIfAbsent` holding the bin lock means a mapping function that touches the same map
        deadlocks. `[TRAP]` `[X-REF 05]`
3.14.20 Bulk parallel operations: `forEach`, `search`, `reduce` and their `parallelismThreshold`
        argument. `[RESEARCH]`
3.14.21 `newKeySet()` and `keySet(defaultValue)` giving a concurrent `Set`.
3.14.22 Why `ConcurrentHashMap` forbids null values (`get` returning null must mean "absent").
        `[PROVE]`
3.14.23 Java 7 `ConcurrentHashMap`: 16 `Segment`s each a `ReentrantLock`-guarded mini-map,
        `concurrencyLevel`, and why segment locking was abandoned. `[PROVE]`
3.14.24 `CopyOnWriteArrayList` mechanics: `volatile Object[] array`, `ReentrantLock`, mutators
        copy, `addIfAbsent`, `COWIterator` snapshot, `iterator.remove` throws. `[SOURCE]`
3.14.25 CoW cost model: read O(1) lock-free, write O(n) plus a full array allocation. The
        crossover at which it becomes a disaster (write ratio × size). `[PROVE]` `[NUM]`
3.14.26 The listener-list use case CoW was designed for.
3.14.27 `BlockingQueue` family and backpressure: `put`/`take` blocking, `offer(timeout)`,
        `drainTo`, `remainingCapacity`. `[X-REF 05]`
3.14.28 `ArrayBlockingQueue` (one lock, two conditions, fairness flag) vs `LinkedBlockingQueue`
        (`putLock`/`takeLock`, `AtomicInteger count`, cascading signals). `[SOURCE]` `[PROVE]`
3.14.29 `SynchronousQueue`'s `TransferStack`/`TransferQueue` dual-data-structure and its use as a
        `ThreadPoolExecutor` handoff. `[X-REF 05]`
3.14.30 `DelayQueue` and the leader-follower optimisation that avoids a thundering herd.
        `[RESEARCH]`
3.14.31 `ConcurrentLinkedQueue`: Michael–Scott algorithm, lazy `head`/`tail` updates (advanced
        every other operation), `size()` O(n). `[SOURCE]` `[PROVE]`
3.14.32 `LinkedTransferQueue`'s dual queue and `transfer` semantics.
3.14.33 `ConcurrentSkipListMap` mechanics: `Index`/`Node` levels, `p = 0.25` level distribution,
        CAS insertion, deletion via value-null marking then unlinking, no CME.
        `[PROVE]` `[RESEARCH]`
3.14.34 The unsafe-collection failure catalogue: `HashMap` resize race (lost/duplicated entries,
        Java 7 infinite loop), `ArrayList` concurrent add (`ArrayIndexOutOfBoundsException`, nulls,
        wrong size), `size` drift, `SimpleDateFormat`-style shared-mutable-state analogue.
        `[TRAP]` `[PROVE]`
3.14.35 Choosing table: read-mostly small → CoW; general map → CHM; sorted concurrent →
        CSLM; producer-consumer → blocking queue; single-writer → `synchronized` block; immutable
        snapshot swap → `AtomicReference<List>`.
3.14.36 The `AtomicReference<ImmutableList>` copy-on-write-by-hand pattern and when it beats CoW.
        `[BUILD]`
3.14.37 Virtual threads and collections: `synchronized` no longer pins in Java 24+, so
        `Collections.synchronizedMap` under a million virtual threads behaves differently than in
        21. `[RESEARCH]` `[X-REF 04]`

*(37 leaves)*

### §3.15 Memory footprint arithmetic

3.15.1 Object header: 8-byte mark word + 4-byte compressed class word = 12 bytes; 16 without
       compressed class pointers. `[NUM]` `[SOURCE]` `[RESEARCH]`
3.15.2 Array header = object header + 4-byte length = 16 bytes. `[NUM]` `[RESEARCH]`
3.15.3 8-byte object alignment; `-XX:ObjectAlignmentInBytes`. `[NUM]`
3.15.4 Compressed oops: 4-byte references below ~32 GB heap, 8 above; the cliff.
       `[NUM]` `[X-REF 06]`
3.15.5 `Integer` = 12 header + 4 value = 16 bytes. `Long` = 12 + 4 pad + 8 = 24 bytes.
       `[NUM]` `[RESEARCH]`
3.15.6 `int[1_000_000]` = 16 + 4,000,000 ≈ 4.0 MB. `[NUM]` `[PROVE]`
3.15.7 `ArrayList<Integer>` with 1,000,000 entries = list object 24 + array (16 + 4 MB refs) +
       1,000,000 × 16 B `Integer` = ~20 MB. A 5× blow-up. `[NUM]` `[PROVE]`
3.15.8 `ArrayList` capacity slack: average 25% waste under 1.5× growth if you never `trimToSize`.
       `[NUM]` `[PROVE]`
3.15.9 `HashMap.Node` = 12 header + 4 hash + 4 key ref + 4 value ref + 4 next ref = 28 → 32 bytes
       aligned. `[NUM]` `[PROVE]`
3.15.10 `HashMap<Integer,Integer>` per entry ≈ 32 (Node) + 16 (key Integer) + 16 (value Integer) +
        4 (table slot / 0.75 load factor → ~5.3) ≈ 69 bytes for 8 bytes of data. `[NUM]` `[PROVE]`
3.15.11 `LinkedHashMap.Entry` = `Node` + 2 refs = 40 bytes. `[NUM]`
3.15.12 `HashMap.TreeNode` = `LinkedHashMap.Entry` + parent/left/right/prev refs + boolean red
        → 56 bytes. Treeified bins cost memory. `[NUM]` `[PROVE]`
3.15.13 `LinkedList.Node` = 24 bytes + element. `[NUM]`
3.15.14 `TreeMap.Entry` = 40 bytes + key + value. `[NUM]`
3.15.15 `ArrayDeque` = array only, 4 bytes per slot, one wasted slot. `[NUM]`
3.15.16 `EnumMap` = 4 bytes per enum constant regardless of occupancy. `[NUM]`
3.15.17 `EnumSet` (Regular) = one object, 8 bytes of payload, for up to 64 members. `[NUM]`
3.15.18 `BitSet` = 1 bit per element in the domain. `HashSet<Integer>` = ~50 bytes per element.
        The 400× ratio. `[NUM]` `[PROVE]`
3.15.19 `ConcurrentHashMap` overhead vs `HashMap`: same `Node` shape plus `CounterCell`s and
        `@Contended` padding. `[NUM]`
3.15.20 Empty-collection cost: `new ArrayList<>()` = 24 bytes (shared empty array),
        `new HashMap<>()` = 48 bytes (no table yet), `new ArrayList<>(1000)` = 24 + 4016.
        `[NUM]` `[PROVE]`
3.15.21 A map of a million empty `ArrayList`s: the cost of `computeIfAbsent(k, x -> new ArrayList<>())`
        for keys with one element each. `[NUM]` `[TRAP]`
3.15.22 Measuring it: JOL (`ClassLayout.parseInstance`, `GraphLayout.parseInstance().totalSize()`),
        and why `Runtime.freeMemory` deltas lie. `[X-REF 06]`
3.15.23 Project Lilliput / compact object headers (`-XX:+UseCompactObjectHeaders`, experimental in
        24, product in 25): header drops from 12 to 8 bytes, which shifts every number above.
        `[RESEARCH]` `[NUM]`
3.15.24 Value classes / Valhalla as the eventual fix for boxed collections. `[RESEARCH]`

*(24 leaves)*

### §3.16 Version history of the framework

3.16.1 Java 1.0/1.1: `Vector`, `Hashtable`, `Stack`, `Enumeration`, `Dictionary`, `BitSet`.
3.16.2 Java 1.2: the framework proper — interfaces, `ArrayList`, `LinkedList`, `HashMap`,
       `TreeMap`, `HashSet`, `TreeSet`, `Collections`, `Arrays`, `Iterator`, `Comparator`.
3.16.3 Java 1.4: `LinkedHashMap`, `LinkedHashSet`, `IdentityHashMap`, `RandomAccess`,
       `Collections.rotate`/`swap`/`replaceAll`/`frequency`/`disjoint`. `[RESEARCH]`
3.16.4 Java 5: generics, `Queue`, `EnumMap`, `EnumSet`, `PriorityQueue`,
       `java.util.concurrent` (`ConcurrentHashMap`, `CopyOnWriteArrayList`, `BlockingQueue`),
       for-each, `Iterable`.
3.16.5 Java 6: `Deque`, `ArrayDeque`, `NavigableMap`, `NavigableSet`, `ConcurrentSkipListMap`,
       `LinkedBlockingDeque`, `AbstractMap.SimpleEntry`.
3.16.6 Java 7: `TransferQueue`/`LinkedTransferQueue`, diamond inference, `Objects` utility,
       the 7u6 alternative-hashing experiment.
3.16.7 Java 8: default methods on `Map`/`Collection`/`Iterable`, streams, `Spliterator`,
       `Comparator` combinators, `HashMap` treeification, `ConcurrentHashMap` rewrite,
       `Collections.sort` delegating to `List.sort`, `StampedLock`, `LongAdder`.
3.16.8 Java 9: `List.of`/`Set.of`/`Map.of`/`Map.entry`/`Map.ofEntries`, `ImmutableCollections`
       with SALT, `Enumeration.asIterator`, `ArrayDeque` rewrite (no more power-of-two).
       `[RESEARCH]` `[VERSION-TRAP]`
3.16.9 Java 10: `List.copyOf`/`Set.copyOf`/`Map.copyOf`, `Collectors.toUnmodifiableList/Set/Map`.
3.16.10 Java 11: `Collection.toArray(IntFunction)`, `ArraysSupport.newLength` unifying growth,
        `Optional.isEmpty`.
3.16.11 Java 14–16: `record`, `Stream.toList()`, `DualPivotQuicksort` improvements.
3.16.12 Java 17: `Map.Entry.copyOf`, sealed types. `[RESEARCH]`
3.16.13 Java 19: `HashMap.newHashMap`, `HashSet.newHashSet`, `LinkedHashMap.newLinkedHashMap`,
        `LinkedHashSet.newLinkedHashSet`. `[RESEARCH]`
3.16.14 Java 21: JEP 431 sequenced collections; `Collections.unmodifiableSequenced*`;
        `newSequencedSetFromMap`; `List.reversed`. `[RESEARCH]`
3.16.15 Java 22–25: no new collection interfaces or implementations. Adjacent: `Stream.gather`/
        `Gatherer` (24), compact object headers (24 experimental / 25), `synchronized` no longer
        pinning virtual threads (24). `[RESEARCH]`
3.16.16 The removed/deprecated list: `Collections.unmodifiableList` on a `RandomAccess` list
        preserving the marker, `Observable`/`Observer` removal, `Vector.elements` retained.
3.16.17 Compatibility lesson: JEP 431's retrofit broke source compatibility for classes with a
        clashing `getFirst`. The cost of adding methods to old interfaces. `[RESEARCH]` `[TRAP]`

*(17 leaves)*

### §3.17 Observability: inspecting collections at runtime

3.17.1 Heap dump workflow: `jcmd <pid> GC.heap_dump`, `jmap -dump:live,format=b`, then
       Eclipse MAT / VisualVM. `[X-REF 06]`
3.17.2 Finding the collection that is leaking: MAT dominator tree, "Retained Heap", the
       `java.util.HashMap$Node[]` at the top of the histogram.
3.17.3 MAT's "Collections" queries: `collection_fill_ratio`, `map_collision_ratio`,
       `array_fill_ratio`, `hash_entries`, `collections_grouped_by_size`. `[RESEARCH]`
3.17.4 Diagnosing a bad `hashCode` from a heap dump: `map_collision_ratio` near 1.
3.17.5 Diagnosing `ArrayList` over-allocation: `collection_fill_ratio` histogram.
3.17.6 `jcmd <pid> GC.class_histogram` for a quick count of `Node`/`Entry` instances.
3.17.7 Reading a collection in a debugger: IntelliJ's "view as Object[]", the `elementData`
       field, and why the debugger shows `size` separately from capacity.
3.17.8 Watching `modCount` in a debugger to find the CME source.
3.17.9 The debugger's `toString` evaluation causing the very CME you are chasing. `[TRAP]`
3.17.10 IntelliJ "Java Object Layout"/JOL plugin for live size inspection.
3.17.11 `jfr` / JDK Flight Recorder allocation profiling to attribute
        `java.util.HashMap$Node` allocation to a call site. `[X-REF 06]`
3.17.12 async-profiler `--alloc` for the same, in production.
3.17.13 Micrometer gauges over cache/collection size as the cheap always-on guard.
        `[X-REF 20]`
3.17.14 `-XX:+PrintFlagsFinal` for `UseCompressedOops`/`UseCompactObjectHeaders` before you trust
        any byte arithmetic. `[X-REF 06]`
3.17.15 Static-analysis and runtime guards: `Collections.checkedList` to catch the raw-type
        polluter, `-ea` assertions on invariants, ErrorProne's `CollectionIncompatibleType`.
        `[RESEARCH]`

*(15 leaves)*

### §3.18 The abstract skeletons, and writing your own collection

3.18.1 `AbstractCollection` — implement `iterator()` and `size()`, get everything else.
3.18.2 `AbstractCollection.toString` and `AbstractCollection.toArray` growth loop. `[SOURCE]`
3.18.3 `AbstractList` — implement `get(int)` and `size()` for immutable; add `set`, `add`, `remove`
       for mutable; `modCount` is defined here.
3.18.4 `AbstractList`'s `Itr`/`ListItr` built on `get`, and why extending it for a linked structure
       is O(n²). `[TRAP]`
3.18.5 `AbstractSequentialList` — the linked-structure counterpart, implement `listIterator`.
3.18.6 `AbstractSet` — takes `equals`/`hashCode`/`removeAll` off your hands.
3.18.7 `AbstractQueue` — implements `add`/`remove`/`element` in terms of `offer`/`poll`/`peek`.
3.18.8 `AbstractMap` — implement `entrySet()`; get `get`, `containsKey`, `equals`, `hashCode`,
       `toString`; override `put` for mutability.
3.18.9 `AbstractMap`'s `get` is O(n) over the entry set — extending it naively gives a linear map.
       `[TRAP]`
3.18.10 The delegation/decorator alternative: wrap rather than extend
        (`ForwardingList` in Guava), and why extending `ArrayList` to add validation is broken
        (`addAll` does not call `add`). `[TRAP]` `[PROVE]`
3.18.11 Contract obligations when you write your own: `equals`/`hashCode`, fail-fast iteration,
        `Spliterator`, `Serializable`, thread-safety documentation, optional-operation exceptions.
3.18.12 Testing a custom collection against the JDK's own conformance expectations (Guava's
        `testlib` `CollectionTestSuiteBuilder`). `[RESEARCH]`

*(12 leaves)*

**PART 3 total: 360 leaves**

---

## PART 4 — BUILD IT

Every item is `[BUILD]`: complete, compiling, generic Java 21, followed by a
**Diff vs the real one** table covering at minimum bounds checks, intrinsics, serialization,
`Spliterator` support, null policy, allocation tricks, and why the JDK bothers.

### §4.1 `MyArrayList<E>`

4.1.1 `implements List<E>, RandomAccess`; `Object[] elementData`; `int size`; `int modCount`.
4.1.2 The two empty-array sentinels reproduced, with the lazy first-grow to 10.
4.1.3 `grow` reproducing `oldCapacity + (oldCapacity >> 1)` plus the `newLength` overflow guard.
4.1.4 `add`, `add(int,E)`, `set`, `get` with `Objects.checkIndex`.
4.1.5 `remove(int)` and `remove(Object)` with `System.arraycopy` shifting and trailing-null clear.
4.1.6 `indexOf`/`lastIndexOf`/`contains` with the null-split loop.
4.1.7 Fail-fast `Itr` with `cursor`/`lastRet`/`expectedModCount`, and `remove` resyncing.
4.1.8 `ListItr` with `previous`, `set`, `add`.
4.1.9 `subList` view class with `offset`, `size`, parent `modCount` mirror, and
      `checkForComodification`.
4.1.10 `ensureCapacity`, `trimToSize`, `clear`.
4.1.11 `equals`/`hashCode`/`toString` matching `AbstractList` semantics.
4.1.12 `addAll`, `removeAll`, `retainAll`, `removeIf` with the bitset compaction.
4.1.13 `sort(Comparator)` in place with `modCount` bump.
4.1.14 `spliterator()` with `ORDERED|SIZED|SUBSIZED` and midpoint `trySplit`.
4.1.15 Diff vs `java.util.ArrayList` table.
4.1.16 A JMH sketch comparing `MyArrayList` and `ArrayList` on append and mid-insert.

*(16 leaves)*

### §4.2 `MyLinkedList<E>`

4.2.1 `Node<E>` with `item`/`prev`/`next`; `first`/`last`/`size`.
4.2.2 `linkFirst`/`linkLast`/`linkBefore`/`unlink` with GC-help nulling.
4.2.3 `node(int)` with the `index < (size >> 1)` bidirectional shortcut.
4.2.4 `Deque` methods: `addFirst`, `addLast`, `pollFirst`, `pollLast`, `push`, `pop`, `peek`.
4.2.5 `ListItr` giving true O(1) insert at the cursor.
4.2.6 `descendingIterator`.
4.2.7 Diff vs `java.util.LinkedList` table.
4.2.8 Benchmark: prove that even mid-list insertion loses to `ArrayList` once you must locate the
      index. `[PROVE]`

*(8 leaves)*

### §4.3 `MyHashMap<K,V>`

4.3.1 `Node<K,V>` with cached `hash`; `Node<K,V>[] table`; `size`; `threshold`; `loadFactor`;
      `modCount`.
4.3.2 `spread` reproducing `h ^ (h >>> 16)`; `tableSizeFor` reproducing the
      `numberOfLeadingZeros` trick.
4.3.3 Lazy table allocation with `threshold` doubling as the pending initial capacity.
4.3.4 `put` with the empty-bin fast path, chain walk, `==`-before-`equals`, and null-key bucket 0.
4.3.5 `get`, `containsKey`, `getOrDefault`, `remove`.
4.3.6 `resize` with the `(e.hash & oldCap) == 0` lo/hi split preserving order.
4.3.7 A simplified `treeifyBin` — either a real red-black bin or a documented sorted-list fallback,
      with an exact statement of what differs from the JDK's `TreeNode`.
4.3.8 `computeIfAbsent`, `merge`, `putIfAbsent`, `compute` — including the "mapping function
      mutated the map" detection.
4.3.9 `keySet`/`values`/`entrySet` as live views with working `remove`.
4.3.10 `HashIterator` walking the table bin by bin, fail-fast.
4.3.11 `MyHashSet<E>` on top of it, with the `PRESENT` dummy.
4.3.12 `MyLinkedHashMap<K,V>` extending it with the `before`/`after` overlay, `accessOrder`, and
       `removeEldestEntry` — then a working LRU.
4.3.13 Diff vs `java.util.HashMap` table.
4.3.14 A collision-DoS demo: insert 10,000 keys with identical hash codes into `MyHashMap` without
       treeification, measure, then with. `[PROVE]`

*(14 leaves)*

### §4.4 `MyArrayDeque<E>`

4.4.1 `Object[] elements`, `head`, `tail`, the always-one-free-slot invariant.
4.4.2 Both designs: the classic power-of-two `& (length - 1)` version *and* the Java 21-style
      `inc`/`dec`/`sub` version. Compare.
4.4.3 `addFirst`/`addLast`/`pollFirst`/`pollLast`/`peekFirst`/`peekLast`.
4.4.4 `grow` with the double-then-1.5× jump and the un-wrap slide.
4.4.5 `size` via `sub(tail, head, length)`.
4.4.6 Null rejection with an explanatory message.
4.4.7 The two-slice iterator.
4.4.8 Diff vs `java.util.ArrayDeque` table.

*(8 leaves)*

### §4.5 `MyPriorityQueue<E>`

4.5.1 `Object[] queue`, `size`, `Comparator`, `modCount`.
4.5.2 `siftUp`/`siftDown` with the comparator/comparable split.
4.5.3 `offer`, `poll`, `peek`, `remove(Object)`, `removeAt` with the moved-element return.
4.5.4 `heapify` O(n) construction.
4.5.5 `grow` with the `< 64 ? +2 : >>1` policy.
4.5.6 Iterator with the `forgetMeNot` deque so no element is skipped.
4.5.7 A stable variant with an insertion-sequence tiebreak.
4.5.8 A bounded top-k variant.
4.5.9 Diff vs `java.util.PriorityQueue` table.

*(9 leaves)*

### §4.6 Supporting builds

4.6.1 `MyTreeMap<K,V>` — red-black insert with `fixAfterInsertion`, delete with
      `fixAfterDeletion`, `floorEntry`/`ceilingEntry`, in-order iterator. (Or, if deferred,
      an explicit statement of the delete cases with the code for insert.)
4.6.2 An LRU cache built without `LinkedHashMap`: `HashMap` + your own doubly-linked list, so the
      mechanism is visible.
4.6.3 An LFU cache sketch, to show why LRU is the easy one.
4.6.4 A fixed-capacity ring buffer / `CircularFifoQueue`.
4.6.5 A `Multimap<K,V>` over `Map<K, List<V>>` with `computeIfAbsent`, and the cleanup-on-empty
      subtlety.
4.6.6 A `BiMap<K,V>` with two maps kept in sync, and the invariant it must enforce.
4.6.7 An `IntArrayList` — primitive-specialised, to make the boxing cost concrete. `[NUM]`
4.6.8 A `CopyOnWriteList<E>` over `AtomicReference<Object[]>`.
4.6.9 A custom `Spliterator` for `MyLinkedList` and a measurement of parallel-stream speedup
      (or lack of it).
4.6.10 A `Collections.checkedList`-style dynamic type guard.
4.6.11 A fail-fast `Iterator` harness that demonstrates every CME variant from §2.2.

*(11 leaves)*

**PART 4 total: 66 leaves**

---

## PART 5 — INTERVIEW AND RETENTION

### §5.1 The questions, with the answer shape

5.1.1 "How does `HashMap` work internally?" — the 90-second answer and the 10-minute answer.
5.1.2 "What happens when two keys have the same hash code?"
5.1.3 "Why is the default load factor 0.75?"
5.1.4 "Why 8 for treeify and 6 for untreeify?"
5.1.5 "Why is `HashMap`'s capacity a power of two?"
5.1.6 "Why does `HashMap` xor the high bits?"
5.1.7 "What happens on a `HashMap` resize? Why does order matter?"
5.1.8 "What went wrong with `HashMap` in Java 7 under concurrency?"
5.1.9 "Why can a `HashMap` key not be mutable?"
5.1.10 "What is the `equals`/`hashCode` contract and what breaks if you violate it?"
5.1.11 "Can two unequal objects have the same hash code? Can two equal objects have different ones?"
5.1.12 "`ArrayList` vs `LinkedList` — when would you actually use `LinkedList`?"
5.1.13 "What is `ArrayList`'s growth factor and why not 2×?"
5.1.14 "Prove `ArrayList.add` is amortised O(1)."
5.1.15 "What is `ConcurrentModificationException` and how do you avoid it?"
5.1.16 "Fail-fast vs fail-safe vs weakly consistent iterators."
5.1.17 "How would you implement an LRU cache?" — and the follow-up "without `LinkedHashMap`".
5.1.18 "`HashMap` vs `Hashtable` vs `ConcurrentHashMap`."
5.1.19 "How does `ConcurrentHashMap` achieve thread safety without locking the whole map?"
5.1.20 "Why does `ConcurrentHashMap` not allow null?"
5.1.21 "Is `size()` on a `ConcurrentHashMap` accurate?"
5.1.22 "When is `CopyOnWriteArrayList` the right choice?"
5.1.23 "`Comparable` vs `Comparator`."
5.1.24 "Why does `Collections.sort` throw 'Comparison method violates its general contract'?"
5.1.25 "Which sort does Java use, and why two different ones?"
5.1.26 "`TreeMap` vs `HashMap` — and when do you need `TreeMap`?"
5.1.27 "How does `TreeMap` decide two keys are the same?"
5.1.28 "What is a red-black tree and why not AVL?"
5.1.29 "Why is `Map` not a `Collection`?"
5.1.30 "What is the difference between `Arrays.asList`, `List.of`, and `Collections.unmodifiableList`?"
5.1.31 "What is `subList` and what is dangerous about it?"
5.1.32 "How do `keySet` and `entrySet` relate to the map?"
5.1.33 "`HashSet` vs `LinkedHashSet` vs `TreeSet`."
5.1.34 "Why is `EnumMap` faster than `HashMap` for enum keys?"
5.1.35 "What is `WeakHashMap` for, and why is it not a cache?"
5.1.36 "What is `IdentityHashMap` for?"
5.1.37 "How does `PriorityQueue` work and why isn't its iteration sorted?"
5.1.38 "How would you find the top k elements of a stream of a billion numbers?"
5.1.39 "`ArrayDeque` vs `Stack` vs `LinkedList` for a stack."
5.1.40 "How much memory does a `HashMap<Integer,Integer>` of a million entries use?"
5.1.41 "What did Java 21 add to the collections framework?"
5.1.42 "How would you make an existing collection thread-safe?"
5.1.43 "How do you remove elements from a list while iterating?"
5.1.44 "What is the initial capacity you should pass to hold n entries without resizing?"
5.1.45 "Design a data structure with O(1) insert, delete, and getRandom." (`ArrayList` + `HashMap`)
5.1.46 "Design an LFU cache." / "Design a rate limiter with `TreeMap`."
5.1.47 "How would you detect which collection is leaking memory in production?"
5.1.48 "Why does `Collections.unmodifiableList` not make my list immutable?"
5.1.49 "What is a `Spliterator` and when does a parallel stream help?"
5.1.50 "Walk me through what `map.computeIfAbsent(k, x -> new ArrayList<>()).add(v)` does."

*(50 leaves)*

### §5.2 The trap index

5.2.1 One table of every `**Pitfall:**` in the notes, with the wrong belief, the symptom, and the
      fix — usable as a pre-interview scan.
5.2.2 The version-stale claims table: what old blogs say vs what Java 21 does (`ArrayDeque`
      power-of-two, `HashMap` Java 7 rehashing, `ConcurrentHashMap` segments, `Collections.sort`
      copying, load factor "prime capacity").
5.2.3 The five most expensive real-world mistakes: unbounded collection as a cache, mutable key,
      `removeAll` with a `List` argument, `LinkedList` "for performance", `Collections.synchronizedMap`
      thought to be enough.

*(3 leaves)*

### §5.3 One-line assertions and drills

5.3.1 The numbers drill: recite every constant with its value (16, 0.75, 8, 6, 64, 10, 1.5×, 11,
      17, 2/3, 32, 1<<30, `Integer.MAX_VALUE - 8`).
5.3.2 The matrices drill: null policy, thread safety, ordering, mutability tier.
5.3.3 The cost drill: state amortised and worst case for 20 named operations from memory.
5.3.4 The "which one" drill: 15 scenarios → the right collection, in one word each.
5.3.5 The mechanism drill: explain in one sentence each — spread, lo/hi split, treeify, siftUp,
      rotateLeft, modCount, `ForwardingNode`, SALT, `afterNodeAccess`, `expungeStaleEntries`.
5.3.6 Code-reading drill: five snippets, say what each prints (and why it is not what it looks
      like).
5.3.7 Spaced-repetition schedule for this file: day 1 read, day 3 checklist, day 7 numbers drill,
      day 21 build one structure from scratch.
5.3.8 `## Atomic concept checklist` — one line per concept in the whole file.

*(8 leaves)*

**PART 5 total: 61 leaves**

---

## Leaf counts

| Part | Leaves |
|---|---|
| PART 1 — Basics | 181 |
| PART 2 — Intermediate | 233 |
| PART 3 — Advanced (internals) | 360 |
| PART 4 — Build it | 66 |
| PART 5 — Interview & retention | 61 |
| **Total** | **901** |

Leaves carrying `[RESEARCH]`: **96**.
Leaves carrying `[VERSION-TRAP]`: **3** (3.4.3, 3.16.8, 5.2.2).
Leaves carrying `[PROVE]`: **~95**. `[SOURCE]`: **~120**. `[BUILD]`: **66** (all of Part 4, plus
2.8.19, 3.5.15, 3.5.17, 3.14.36, 3.13.16).

**Every one of the 901 leaves must appear in the notes**, or be listed in a `## Deferred`
block with a reason.

---

# DIAGRAM MANIFEST

**152 diagrams (D-01 … D-152).** Every one must be present in the notes as inline SVG (or a referenced
sibling `.svg`), with the stable id in its caption, e.g. `**D-42** — nCopies as n references
to one object`. Where the `Type` column says `table`, a Markdown table is the correct
rendering and no SVG is required.

Rules the manifest assumes and you must follow:
- One idea per diagram. Prefer more, smaller diagrams over one dense one.
- Where the `Must show` column asks for *frames*, produce that many separate SVGs (or one
  SVG with that many clearly separated, individually labelled panels), each captioned with
  the frame number and what changed since the previous frame.
- Every label, constant and value named in `Must show` must be visible as text in the SVG.
  A diagram that omits a named value does not satisfy the manifest.
- Arrows must be directional and labelled where the direction is not obvious.

## Part 1 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-01 | The pre-1.2 world vs the 1.2 framework | 1.1.1, 1.1.4 | before-after | Left: `Vector`, `Hashtable`, `Stack`, `Dictionary`, `Enumeration` as five disconnected boxes with no shared supertype. Right: `Iterable`→`Collection`→{`List`,`Set`,`Queue`} plus `Map`, with the four standardised layers labelled: interfaces / implementations / algorithms / iteration protocol |
| D-02 | Array covariance hole → `ArrayStoreException` | 1.1.2, 1.1.3 | step-sequence, 3 frames | Frame 1: `Object[] a = new String[2]` with the runtime element type `String` labelled on the array header. Frame 2: `a[0] = 42` with the runtime store check drawn as a gate. Frame 3: `ArrayStoreException` thrown; alongside, `List<String>` with the compile-time rejection instead — label "compile error" vs "runtime error" |
| D-03 | The full interface hierarchy, Java 21 | 1.2.1–1.2.11, 1.2.19 | hierarchy | `Iterable` at root; `Collection`; the Java 21 `SequencedCollection` tier drawn in a distinct colour with a "Java 21" badge; `List`, `Set`, `SequencedSet`, `SortedSet`, `NavigableSet`, `Queue`, `Deque`; `Map` as a separate root with `SequencedMap`, `SortedMap`, `NavigableMap`, and `Map.Entry` nested. Every edge labelled `extends`. Concrete classes shown as leaf boxes in a third style |
| D-04 | Where `java.util.concurrent` grafts on | 1.2.20 | hierarchy | `ConcurrentMap` under `Map`; `ConcurrentNavigableMap` under both `ConcurrentMap` and `NavigableMap` (show the diamond); `BlockingQueue` under `Queue`; `BlockingDeque` under both `BlockingQueue` and `Deque`; `TransferQueue` under `BlockingQueue`; the implementing classes `ConcurrentHashMap`, `ConcurrentSkipListMap`, `ArrayBlockingQueue`, `LinkedBlockingQueue`, `LinkedBlockingDeque`, `LinkedTransferQueue`, `SynchronousQueue`, `DelayQueue`, `PriorityBlockingQueue` |
| D-05 | The abstract skeletons and what each demands | 1.2.16, 3.18.1–3.18.8 | hierarchy | Six boxes: `AbstractCollection`, `AbstractList`, `AbstractSequentialList`, `AbstractSet`, `AbstractQueue`, `AbstractMap`. Each annotated with the abstract methods a subclass must supply (`iterator()`+`size()`; `get(int)`+`size()`; `listIterator()`; `iterator()`+`size()`; `offer`/`poll`/`peek`; `entrySet()`) and what it gives you free |
| D-06 | The iteration-protocol family | 1.2.12, 1.2.13 | hierarchy | `Iterator` with its 4 methods; `ListIterator extends Iterator` with its 6 extra; `Enumeration` standing alone with 2 methods and the `asIterator()` bridge arrow (Java 9); `PrimitiveIterator.OfInt/OfLong/OfDouble`; `Spliterator` with `OfInt`/`OfLong`/`OfDouble` |
| D-07 | Queue's two-form method pairs | 1.2.8, 1.3.9 | table | Rows insert/remove/examine; columns "throws exception" (`add`/`remove`/`element`) and "returns special value" (`offer`/`poll`/`peek`), with the exact exception and the exact special value in each cell |
| D-08 | One deque, two access disciplines | 1.3.10, 1.3.11 | memory-layout | A single array-backed deque drawn once, with stack-facing labels (`push`≡`addFirst`, `pop`≡`removeFirst`, `peek`≡`peekFirst`) on the head end and queue-facing labels (`add`≡`addLast`, `poll`≡`removeFirst`) on both ends; a callout showing `Deque`-as-stack iterating LIFO while `Stack` iterates bottom-to-top |
| D-09 | The `Iterator` state machine | 1.5.2 | state-transition | States: `READY`, `RETURNED`, `REMOVED`, `EXHAUSTED`. Transitions labelled `hasNext()`, `next()`, `remove()`. The illegal edge `remove()` from `READY` and from `REMOVED` labelled `IllegalStateException` |
| D-10 | `ListIterator` cursor and the `add`/`set` off-by-one | 1.3.19, 1.3.20, 1.5.5 | step-sequence, 4 frames | A list `[A,B,C]` with the cursor drawn *between* elements. Frame 1: cursor at 0, `nextIndex()=0`, `previousIndex()=-1`. Frame 2: after `next()` returns `A`, cursor at 1, `lastReturned=A`. Frame 3: after `add(X)`, `[A,X,B,C]`, cursor at 2, `lastReturned` cleared. Frame 4: `set(Y)` now throws `IllegalStateException` — label why |
| D-11 | Enhanced-for desugaring | 1.5.1 | before-after | Left: `for (String s : list)` and `for (int i : arr)`. Right: the compiler-generated `Iterator` loop for the first and the indexed loop for the second, with the `hasNext`/`next` calls and the `arr.length` bound both drawn |
| D-12 | Three ways to walk a `Map` | 1.5.11 | step-sequence | Three parallel lanes over the same 4-entry map: `entrySet()` (one table walk, one node touch per entry), `keySet()`+`get(k)` (one table walk plus a second hash+probe per key — draw both traversals), `values()` (one walk, no keys). Label the operation count for each: n, 2n, n |
| D-13 | `Comparator` chaining and what `reversed()` reverses | 1.6.7, 1.6.8 | flowchart | A pipeline `comparing(Person::last).thenComparing(Person::first).reversed()` drawn as boxes; a bracket around *both* comparators showing `reversed()` wraps the whole chain, not just the last link; contrast with `comparing(last).thenComparing(comparing(first).reversed())` |
| D-14 | Why `a - b` breaks as a comparator | 1.6.11 | number-line | A 32-bit signed number line with `Integer.MIN_VALUE` and `Integer.MAX_VALUE` marked; the wrap point drawn; a worked pair `a = 2_000_000_000`, `b = -2_000_000_000`, `a - b = -294_967_296` shown with the actual arithmetic, and `Integer.compare(a,b) = 1` beside it |
| D-15 | Why equal objects must have equal hashes | 1.7.2, 1.7.3 | step-sequence, 3 frames | Frame 1: `put(k1, v)` computes `hash(k1)=A`, lands in bucket `A & 15`. Frame 2: `get(k2)` where `k2.equals(k1)` but `hash(k2)=B` — lands in a different bucket. Frame 3: the entry is present in the table but unreachable; label "the `equals` call is never even made" |
| D-16 | The mutable-key stranding | 1.7.4, 2.12.9 | before-after | Before: key object with `id=1`, hash 1001, sitting in bucket 9. After: `key.id = 2` mutated in place, hash now 2002 → bucket 2; the object is still physically in bucket 9. Show `contains` probing bucket 2 and missing, `iteration` finding it in bucket 9, and the entry still GC-reachable |
| D-17 | `getClass()` vs `instanceof` in `equals` | 1.7.6 | before-after | `Point(1,2)` and `ColorPoint(1,2,RED)`. Left panel `instanceof`: `p.equals(cp)` true, `cp.equals(p)` false → symmetry broken, arrow drawn asymmetric. Right panel `getClass()`: both false → symmetric but a `ColorPoint` can never equal a `Point`, Liskov annotation |
| D-18 | `String.hashCode` computation and caching | 1.7.12 | step-sequence, 3 frames | Frame 1: `"Hi"` → `'H'*31 + 'i'` = `72*31 + 105` = 2337, with the arithmetic shown. Frame 2: the `String` object with `hash` field going from 0 to 2337 and `hashIsZero` false. Frame 3: a string whose hash genuinely is 0 (e.g. `""` or `"polygenelubricants"`), showing `hashIsZero=true` (Java 13+) preventing recomputation |
| D-19 | `"Aa"` and `"BB"` collide | 1.7.13 | step-sequence | The two computations side by side: `65*31+97 = 2112` and `66*31+66 = 2112`; then the family `"AaAa"`/`"BBBB"`/`"AaBB"`/`"BBAa"` shown as a doubling tree, with the count `2^k` colliding strings of length `2k` labelled |
| D-20 | `hashCode` of a List vs a Set vs a Map | 1.7.19 | table | Three rows with the exact formula (`31`-fold; sum of element hashes; sum of `key^value`), a worked example over the same three elements, and the consequence (order sensitivity yes/no/no) |
| D-21 | Type erasure at the class-file boundary | 1.8.1, 1.8.2 | before-after | Source `List<String>` and `List<Integer>` on the left; one `java.util.List` class object plus inserted checkcasts on the right; `ArrayList`'s `Object[] elementData` with the `@SuppressWarnings("unchecked")` cast in `elementData(int)` called out |
| D-22 | The `Integer` cache | 1.8.7 | memory-layout | The `IntegerCache.cache` array spanning −128..127 as boxed objects on the heap; two `List<Integer>` slots at value 127 pointing to the *same* object; two slots at 128 pointing to two distinct objects; `==` results annotated true/false |
| D-23 | Boxing blow-up: `int[]` vs `List<Integer>` | 1.8.6, 1.8.8, 3.15.6, 3.15.7 | memory-layout | Top: `int[1_000_000]` = 16-byte header + 4 MB contiguous. Bottom: `ArrayList<Integer>` = 24-byte list + 16-byte array header + 4 MB of 4-byte refs + 1,000,000 × 16-byte `Integer` objects scattered. Totals `4.0 MB` vs `~20 MB` and the 5× ratio labelled |
| D-24 | The JEP 431 retrofit map | 1.9.1–1.9.5 | hierarchy | Existing types on the left, the new supertype each gained on the right, with the seven new `SequencedCollection` methods listed once and the ten `SequencedMap` methods listed once. `Deque`, `List` → `SequencedCollection`; `LinkedHashSet`, `SortedSet` → `SequencedSet`; `LinkedHashMap`, `SortedMap` → `SequencedMap` |
| D-25 | `reversed()` is a view that writes through | 1.9.8 | before-after | `list = [A,B,C]`; `var r = list.reversed()` drawn as a thin wrapper with an index-flipping arrow, not a copy. Then `r.addFirst(X)` and the result `list = [A,B,C,X]`, `r = [X,C,B,A]` — both shown, with the index mapping `r[i] → list[size-1-i]` labelled |
| D-26 | `LinkedHashSet.addFirst` moves rather than duplicates | 1.9.7 | before-after | Before: `[A,B,C]` with the insertion-order chain drawn. After `addFirst(B)`: `[B,A,C]` — show the `B` node unlinked from its old position and relinked at the head, size unchanged at 3 |
| D-27 | Null policy at a glance | 1.10.1–1.10.5 | table | One row per class (`ArrayList`, `LinkedList`, `ArrayDeque`, `PriorityQueue`, `HashMap`, `LinkedHashMap`, `TreeMap`, `Hashtable`, `ConcurrentHashMap`, `HashSet`, `TreeSet`, `EnumMap`, `IdentityHashMap`, `List.of`, `Collections.singletonList`), columns null key / null value / null element / exception thrown |

## Part 2 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-28 | `ArrayList` vs `LinkedList` crossover | 2.1.9, 2.1.10, 3.3.9 | cost-curve | x = n (log scale 10 → 1e6), y = time. Two curves for mid-list insert; the crossover region around n ≈ 1000 shaded and labelled; annotations "one vectorised memmove" on the `ArrayList` curve and "n/2 dependent loads, ~1 cache miss each" on the `LinkedList` curve |
| D-29 | Cache lines: contiguous array vs scattered nodes | 2.1.10, 3.3.8 | memory-layout | Two 64-byte cache lines holding 16 `ArrayList` refs each; versus 8 `LinkedList.Node` objects at unrelated addresses, each dragging its own cache line. Label "16 elements per miss" vs "1 element per miss" |
| D-30 | `modCount` / `expectedModCount` over a loop | 2.2.1–2.2.4 | timeline | A horizontal timeline of iterations; `modCount` and `expectedModCount` as two tracks; the `list.remove(x)` event bumping only `modCount`; the next `next()` call comparing and throwing `ConcurrentModificationException`. Mark exactly where `checkForComodification` runs |
| D-31 | Why removing the second-to-last element escapes CME | 2.2.5 | step-sequence, 3 frames | List `[A,B,C]`, size 3. Frame 1: `next()` returns `B`, cursor = 2. Frame 2: `remove(B)` → size 2, `modCount` bumped, cursor still 2. Frame 3: `hasNext()` evaluates `cursor != size` → `2 != 2` → false, loop exits silently. Label "no `next()` call, so no comodification check" |
| D-32 | Three iterator categories | 2.2.11, 2.2.12, 1.5.16 | table | Columns: fail-fast / snapshot (fail-safe) / weakly consistent. Rows: example classes, does it see concurrent updates, can it throw CME, does `iterator.remove` work, memory cost |
| D-33 | View vs copy vs snapshot | 2.3.1 | before-after | Three panels over the same source list. View: two boxes sharing one backing array, arrows both ways. Copy: two independent arrays, one-way arrow at creation. Snapshot: two independent arrays with a timestamp on the second. A mutation applied to the source in each panel, showing what the second box sees |
| D-34 | `subList` as an offset window | 2.3.2, 3.1.24, 3.1.25 | memory-layout | Parent `ArrayList` with `elementData` of length 10, size 8. `SubList` object with fields `root`, `parent`, `offset=2`, `size=3`, `modCount`, pointing into the same array. Show `sub.set(0,X)` writing to `elementData[2]` |
| D-35 | The `subList` memory-retention leak | 2.3.5 | memory-layout | A 1,000,000-element parent array; `big.subList(0,1)` retaining all of it via `root`; beside it, `new ArrayList<>(big.subList(0,1))` retaining a 1-element array. Byte totals on both |
| D-36 | The three `Map` views | 2.3.6–2.3.9 | memory-layout | One `HashMap` table in the centre; `keySet()`, `values()`, `entrySet()` as three thin view objects around it, each with an arrow labelled with what `remove` does through it (`removes the mapping` / `removes one matching mapping` / `removes the entry`) and what `add` does (`throws UOE`). `entrySet()` shown yielding the actual `Node` objects |
| D-37 | `TreeMap` range views are range-restricted | 2.3.10 | before-after | A sorted key axis 1..100; `subMap(20, 50)` drawn as a bracket; a `put(60, v)` through the view shown hitting an `inRange` check and throwing `IllegalArgumentException`; a `put(30, v)` shown passing through into the parent tree |
| D-38 | Unmodifiable view vs immutable copy | 2.3.15, 2.3.16 | before-after | Left: `Collections.unmodifiableList(src)` — the wrapper rejects writes but `src.add(X)` is visible through it. Right: `List.copyOf(src)` — an independent array, `src.add(X)` invisible. Both mutations drawn and both results shown |
| D-39 | The five immutability tiers | 2.4.1–2.4.6 | hierarchy | A ladder from Tier 0 (mutable `ArrayList`) to Tier 4 (`List.of`), each rung labelled with its representative factory and the four capabilities it removes (`add`, `remove`, `set`, `reflects source`). `EnumSet` explicitly placed at Tier 0 with a note |
| D-40 | PECS | 2.5.1–2.5.4 | flowchart | A box "your method" with an inbound arrow from `Collection<? extends T>` labelled PRODUCES (read-only, `add` barred) and an outbound arrow to `Collection<? super T>` labelled CONSUMES (write-allowed, reads give `Object`). `Collections.copy(dest, src)` overlaid on it |
| D-41 | Why `add` is barred on `List<? extends Number>` | 2.5.9 | step-sequence, 3 frames | Frame 1: `List<Integer> li`, `List<? extends Number> ln = li`. Frame 2: the hypothetical `ln.add(3.14)` shown reaching the `Integer` list. Frame 3: the compiler's rejection, with the capture type `capture#1 of ? extends Number` named |
| D-42 | `binarySearch` return encoding | 2.6.2 | number-line | A sorted array `[10,20,30,40]` with indices; a hit on 30 returning 2; a miss on 25 with insertion point 2 returning `-(2)-1 = -3`; the inverse formula `insertionPoint = -(result) - 1` written out |
| D-43 | `rotate` by three reversals | 2.6.5 | step-sequence, 4 frames | `[1,2,3,4,5,6,7]`, distance 3. Frame 1: original with the split at index 4. Frame 2: reverse first part. Frame 3: reverse second part. Frame 4: reverse whole → `[5,6,7,1,2,3,4]`. Each frame shows the exact array contents |
| D-44 | `nCopies` is n references to one object | 2.6.11 | memory-layout | One heap object; a `CopiesList` view object holding `n` and `element`; contrast with `new ArrayList<>(Collections.nCopies(1_000_000, x))` allocating a 4 MB array of identical refs. Bytes labelled on both |
| D-45 | TimSort: run detection | 2.8.4, 2.8.5 | step-sequence, 3 frames | An array of 40 elements. Frame 1: natural ascending and strictly-descending runs identified and coloured, descending ones marked for reversal. Frame 2: a short run extended to `minRun` by binary insertion sort, with `MIN_MERGE = 32` and the computed `minRunLength` labelled. Frame 3: the resulting list of runs pushed on the stack |
| D-46 | TimSort: the merge stack and `mergeCollapse` | 2.8.6 | state-transition | The run-length stack with the two invariants written as inequalities (`runLen[i-3] > runLen[i-2] + runLen[i-1]`, `runLen[i-2] > runLen[i-1]`); three push/collapse steps shown, each labelled with which invariant was violated and which merge fixed it |
| D-47 | The de Gouw invariant break | 2.8.7 | before-after | The stack state that violates the invariant while `mergeCollapse` believes it holds; the resulting stack depth exceeding the preallocated array; the `ArrayIndexOutOfBoundsException` site; and the JDK fix drawn as "enlarged stack" rather than "corrected invariant" |
| D-48 | Dual-pivot quicksort partition | 2.8.10 | step-sequence, 3 frames | Frame 1: array with pivots P1 ≤ P2 chosen. Frame 2: the three regions `< P1`, `P1 ≤ x ≤ P2`, `> P2` forming with the moving pointers labelled. Frame 3: final layout with the two pivots in place and the three recursive subranges bracketed |
| D-49 | Which sort runs, and when | 2.8.10–2.8.12 | decision-tree | Root: element type. Primitive branch → `DualPivotQuicksort` with the sub-branches: insertion sort for tiny arrays, counting sort for `byte`/`char`/`short`, merge-sort fallback on detected structure, heapsort at `MAX_RECURSION_DEPTH`. Object branch → TimSort, with `useLegacyMergeSort` as a side branch to the legacy merge sort. `MIN_ARRAY_SORT_GRAN = 8192` on the `parallelSort` branch |
| D-50 | Stability, demonstrated | 2.8.14 | before-after | Five records with (name, dept). Sort by name, then by dept. Stable result preserves name order within each dept; the unstable alternative shown scrambling it. Both output lists written out in full |
| D-51 | `EnumSet` as a bit vector | 2.9.3, 2.9.4, 3.10.9–3.10.12 | memory-layout | A single 64-bit `long` with bit positions labelled by enum ordinal and constant name; `add(WEDNESDAY)` shown as `elements |= 1L << 2`; a union `a.addAll(b)` shown as `elements |= other.elements` with both operands' bit patterns and the result; `complementOf` as `~elements & mask` with the mask shown |
| D-52 | `IdentityHashMap`'s flat interleaved table | 2.9.8, 3.11.1–3.11.4 | memory-layout | One `Object[]` of length 64 (capacity 32 × 2); key at index `i`, value at `i+1`; three entries placed; a linear probe from a collision walking `i += 2` with wraparound; `DEFAULT_CAPACITY = 32`, `MAXIMUM_CAPACITY = 1 << 29`, and the `size*3 > len` resize condition labelled |
| D-53 | `WeakHashMap`: the clearing sequence | 2.9.10, 3.11.8–3.11.10 | timeline | Five points on a timeline: (1) key strongly reachable, entry live; (2) last strong ref dropped — entry still present, `size()` still counts it; (3) GC clears the referent and enqueues on `ReferenceQueue`; (4) next map operation calls `expungeStaleEntries()`; (5) entry unlinked. Label the arbitrary-length gap between 2 and 5 |
| D-54 | The `WeakHashMap` value-holds-key leak | 2.9.11 | before-after | Before: entry with a weak ref to key K and a strong value V; V holds a field pointing at K. Draw the strong path `table → Entry → value V → K` making K strongly reachable, so the weak ref never clears. After: V wrapped in a `WeakReference`, path broken, K collectable |
| D-55 | `BitSet` word layout | 2.9.17, 2.9.18 | memory-layout | A `long[] words` array; bit `i` located at `words[i >> 6]`, bit `i & 63`; `set(1_000_000)` shown allocating `words[15625]` ≈ 125 KB immediately; `length()` (highest set bit + 1), `size()` (words.length × 64), `cardinality()` (population count) each marked on the same picture with different values |
| D-56 | `floor` / `ceiling` / `lower` / `higher` | 2.10.1 | number-line | Keys `{10, 20, 30, 40}` on an axis, query key 20 and query key 25 both marked. For each query, four labelled arrows to the answer with the relation `≤ / ≥ / < / >` and the returned key or `null` |
| D-57 | Sliding-window rate limiter on a `TreeMap` | 2.10.9 | timeline | A `TreeMap<Long,Integer>` of timestamp→count; the window boundary sliding right; `headMap(now - window).clear()` shown evicting the expired prefix; `subMap(now-window, true, now, true)` shown summing the live window. Three time steps |
| D-58 | `compute`/`merge` null semantics | 2.11.4–2.11.7 | flowchart | Entry conditions (key absent / present) down one axis and the remapping-function result (null / non-null) across the other; every terminal labelled with the exact outcome: no insertion, insertion, replacement, or *removal*. `merge` with a null value argument shown throwing NPE |
| D-59 | `removeAll` cost: List argument vs Set argument | 2.12.2 | cost-curve | Two curves over m (argument size): `list.removeAll(list2)` growing as n·m, `list.removeAll(new HashSet<>(list2))` growing as n+m. A worked point at n = m = 10,000 with the operation counts 100,000,000 vs 20,000 written out |
| D-60 | `AbstractSet.removeAll` branches on relative size | 2.12.3 | flowchart | The `size() > c.size()` test; the two branches (iterate `this` calling `c.contains`, or iterate `c` calling `this.remove`); worked with `bigSet.removeAll(smallList)` and `smallSet.removeAll(bigList)` showing the different resulting complexities and the different `contains` implementation exercised |
| D-61 | Stream-to-collection mutability and nullability | 2.3.23, 2.13.9 | table | Rows `Stream.toList()` (16), `collect(Collectors.toList())`, `collect(Collectors.toUnmodifiableList())`. Columns: concrete type today, mutable?, `set` allowed?, nulls allowed?, specified by contract? |
| D-62 | `groupingBy` with downstreams | 2.13.5 | step-sequence | A 6-element input; `groupingBy(classifier)` forming the buckets; then the same picture with `groupingBy(classifier, counting())`, `groupingBy(classifier, mapping(f, toList()))` and a 3-arg form with `TreeMap::new`, showing what changes at each stage |
| D-63 | The master choosing decision tree | 2.14.1–2.14.5, 1.4.40 | decision-tree | Root: key-value or elements? Branches on ordered / sorted / unique / bounded / concurrent / both-ends / enum-keyed / primitive-heavy. Every leaf a concrete class. Must reach at least: `ArrayList`, `ArrayDeque`, `LinkedHashSet`, `HashSet`, `TreeSet`, `EnumSet`, `BitSet`, `HashMap`, `LinkedHashMap`, `TreeMap`, `EnumMap`, `IdentityHashMap`, `ConcurrentHashMap`, `ConcurrentSkipListMap`, `CopyOnWriteArrayList`, `PriorityQueue`, `ArrayBlockingQueue`, `LinkedBlockingQueue` |

## Part 3 diagrams

Internals leaves tagged `[SOURCE]` or `[PROVE]` almost always need a step-sequence or
before/after picture. The manifest below assigns one to each such leaf; do not skip any.

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-64 | `ArrayList`'s two empty-array sentinels | 3.1.2, 3.1.3 | before-after | Two distinct zero-length `Object[]` objects at different addresses, named `EMPTY_ELEMENTDATA` and `DEFAULTCAPACITY_EMPTY_ELEMENTDATA`. `new ArrayList<>()` pointing at the second, `new ArrayList<>(0)` at the first. Then the first `add` on each: one grows to 10, one grows to 1. Label "the array *identity* is the flag" |
| D-65 | `ArrayList` growth sequence | 3.1.5–3.1.8 | cost-curve | Step plot of capacity against element count: 10 → 15 → 22 → 33 → 49 → 73 → 109 → 163 → 244, each step annotated with `oldCapacity + (oldCapacity >> 1)` and the resulting value; the `Arrays.copyOf` cost drawn as a spike at each step |
| D-66 | `add(int index, E)` shift | 3.1.12 | before-after | Array `[A,B,C,D,_,_]`, size 4, `add(1, X)`. The single `System.arraycopy(elementData, 1, elementData, 2, 3)` drawn as one block move; the result `[A,X,B,C,D,_]`; `size` 5, `modCount` incremented |
| D-67 | `remove(int)` shift and the trailing null | 3.1.13, 3.1.14 | before-after | Array `[A,B,C,D,_,_]`, `remove(1)`. The `arraycopy` left-shift; then `elementData[--size] = null` drawn explicitly, with a callout "otherwise D stays reachable and never gets collected". A second panel contrasting `remove(size-1)` doing zero copying |
| D-68 | `removeIf`'s deathRow bitset | 3.1.22, 3.1.23 | step-sequence, 3 frames | Frame 1: pass one, predicate evaluated per element, bits set in a `long[]` deathRow — show the bit pattern for a 12-element list. Frame 2: pass two, the single compaction sweep moving survivors left. Frame 3: the tail nulled, `size` updated, `modCount` bumped once. Add a note on `batchRemove`'s `finally` block restoring consistency if the predicate throws |
| D-69 | `ArrayList.SubList` field wiring | 3.1.24, 3.1.25 | memory-layout | `root`, `parent`, `offset`, `size`, `modCount` on a nested sublist-of-a-sublist; arrows showing `checkForComodification` comparing against `root.modCount`, not `parent.modCount` |
| D-70 | `Itr` fields during a loop | 3.1.26, 3.1.27 | state-transition | `cursor`, `lastRet`, `expectedModCount` shown at four points: fresh, after `next()`, after `remove()`, after a foreign mutation. Mark exactly where `modCount` is re-read |
| D-71 | Amortised cost: the potential function | 3.2.4 | cost-curve | Two stacked plots over the same x = number of adds: actual cost (flat 1 with O(n) spikes at each resize) and amortised cost (flat 3). Below, Φ = 2·size − capacity plotted, showing it building to exactly pay for each spike |
| D-72 | Growth factor 1.5 vs 2: the copy budget | 3.2.2, 3.2.6, 3.2.7 | cost-curve | The geometric series `n·g/(g−1)` evaluated: g = 1.5 → 3n total element copies, g = 2 → 2n. Both plotted. Beside it, peak live memory during the copy: 2.5× vs 3× |
| D-73 | Why 1.5× lets freed blocks be reused | 3.2.6 | memory-layout | A heap strip. With 2×: successive freed blocks of 16, 32, 64 sum to 112 but the next request is 128 — never satisfiable. With 1.5×: freed 16 + 24 + 36 = 76 can satisfy the next 54-slot request. Show the coalescing explicitly with byte figures |
| D-74 | `LinkedList` link and unlink | 3.3.3, 3.3.4 | before-after, 2 frames | Frame 1 `linkBefore`: the four pointer writes numbered in order on a 3-node chain. Frame 2 `unlink`: the bypass writes, then `item = null; next = null; prev = null` drawn as three explicit erasures with the "help GC" annotation |
| D-75 | `node(int index)` picks its direction | 3.3.2 | step-sequence | A 10-node chain; `get(2)` walking forward 2 hops from `first`; `get(8)` walking backward 2 hops from `last`; the branch `index < (size >> 1)` written on the diagram; worst case at index 5 labelled with 5 hops |
| D-76 | Per-element memory: `ArrayList` vs `LinkedList` | 3.3.7, 3.15.13 | memory-layout | `ArrayList`: 4 bytes of array slot per element. `LinkedList.Node`: 12-byte header + 3 × 4-byte refs = 24 bytes. Both drawn to scale, ratio 6× labelled, plus the element object itself shown once for fairness |
| D-77 | `ArrayDeque` circular buffer invariant | 3.4.1, 3.4.2, 3.4.15 | memory-layout | A 17-slot ring with `head` and `tail` marked; the one always-empty slot shaded and labelled "why `head == tail` means empty, not full"; `size() = sub(tail, head, 17)` computed on the picture for a wrapped state |
| D-78 | `ArrayDeque`: Java 8 mask vs Java 21 helpers | 3.4.3, 3.4.4 | before-after | Left, JDK 8: capacity forced to a power of two, `head = (head - 1) & (elements.length - 1)`, with the bit arithmetic shown. Right, JDK 21: arbitrary capacity 17, `head = dec(head, 17)` with the helper body shown. A prominent VERSION TRAP banner: "power-of-two masking has not been true since JDK 9" |
| D-79 | `ArrayDeque.grow` and the un-wrap slide | 3.4.7, 3.4.8 | step-sequence, 3 frames | Frame 1: a full wrapped buffer, `tail < head`. Frame 2: `Arrays.copyOf` to the new capacity — show the wrap now broken across the middle. Frame 3: the head-side segment slid to the end of the new array. `jump = (oldCapacity < 64) ? oldCapacity + 2 : oldCapacity >> 1` written with the actual old and new capacities |
| D-80 | Heap array ↔ tree index mapping | 3.5.3 | memory-layout | An 11-slot array beside the binary tree it encodes, indices matched; `parent = (k-1) >>> 1`, `left = 2k+1`, `right = 2k+2` written with a worked k |
| D-81 | `siftUp` | 3.5.5, 3.5.6 | step-sequence, 3 frames | Offer of a small value into a 10-element min-heap; three frames of swap-with-parent, each showing both the tree and the array; the final position. Annotate that `siftUpComparable` and `siftUpUsingComparator` are separate methods for JIT monomorphism |
| D-82 | `siftDown` after `poll` | 3.5.7, 3.5.8 | step-sequence, 3 frames | Frame 1: root removed, last element moved to index 0. Frames 2–3: sink, showing the smaller-child selection before each comparison. Final heap shown as both tree and array |
| D-83 | `heapify` is O(n) | 3.5.9, 3.2.13 | cost-curve | The tree with node counts per level `n/2, n/4, n/8…` and max sift distance per level `0, 1, 2…`; the sum Σ h/2^h converging to 2 drawn as a bar chart with a running total; loop bound `(size >>> 1) - 1` labelled on the tree |
| D-84 | `removeAt` and the iterator's `forgetMeNot` | 3.5.11 | step-sequence, 3 frames | Frame 1: iterator at index 4 in a 9-element heap. Frame 2: `removeAt(2)` moves the last element into index 2 — an element the iterator has already passed. Frame 3: the moved element pushed onto `forgetMeNot` so it is still returned. Label the bug that would occur without it |
| D-85 | `HashMap` anatomy | 3.6.1–3.6.9 | memory-layout | The `Node<K,V>[] table` of 16 slots; three bins: one empty, one with a 3-node chain, one treeified; a `Node` blown up showing `hash`, `key`, `value`, `next`; all six constants listed on the diagram with their values (16, 1<<30, 0.75, 8, 6, 64) |
| D-86 | `hash()` — one xor-shift | 3.6.11, 3.6.13 | bit-layout | A 32-bit `hashCode` drawn as boxed bits; `h >>> 16` shown as a shifted copy; the xor result; then `& (n-1)` for n=16 keeping only the low 4 bits, with the high-bit entropy now folded in. Java 7's four-shift version shown beside it for contrast |
| D-87 | High-entropy-in-high-bits collision | 3.6.12 | step-sequence | Keys 65536, 131072, 196608 (multiples of 2^16). Frame 1: without the spread, `& 15` gives 0 for all three — one bin. Frame 2: with `h ^ (h >>> 16)`, the indices separate. Actual computed index values on both |
| D-88 | `tableSizeFor` | 3.6.15, 3.6.16 | bit-layout | Input 100 as bits; `cap - 1 = 99`; `numberOfLeadingZeros(99) = 25`; `-1 >>> 25 = 127`; `+1 = 128`. Every intermediate shown as a bit pattern |
| D-89 | `putVal` control flow | 3.6.19–3.6.21 | flowchart | Table null → `resize()`. Bin empty → `newNode`. Bin head matches → replace. `TreeNode` → `putTreeVal`. Otherwise chain walk with `binCount`, the `binCount >= TREEIFY_THRESHOLD - 1` test, then `++size > threshold → resize()`. Every branch labelled with the source condition |
| D-90 | `treeifyBin`'s capacity guard | 3.6.22 | decision-tree | The test `tab.length < MIN_TREEIFY_CAPACITY (64)`; the "resize instead of treeify" branch drawn as the *default* for small tables; the actual treeify branch only above 64. Label why: at small capacity a long bin means the table is too small, not that hashing is bad |
| D-91 | Treeify: chain to red-black bin | 3.6.4, 3.6.29, 3.6.30 | before-after | Before: a bin holding a chain of 9 `Node`s, `TREEIFY_THRESHOLD = 8` labelled, table length 64 labelled. After: the same 9 entries as a red-black `TreeNode` bin, with `parent`/`left`/`right`/`prev`/`red` fields shown on one node and the retained `next` linkage drawn as a dashed overlay |
| D-92 | `resize()` lo/hi split | 3.6.23, 3.6.24, 3.6.26 | before-after | A bin at index 5 of a 16-slot table holding 5 nodes with their hashes. `(e.hash & 16) == 0` evaluated per node. After: the lo list still at index 5, the hi list at index 21, both preserving relative order. `loHead`/`loTail`/`hiHead`/`hiTail` named |
| D-93 | Why exactly one bit decides | 3.6.25 | bit-layout | Old mask `0b01111` (n=16) and new mask `0b11111` (n=32) drawn over the same hash; the single newly-exposed bit highlighted; `that bit == oldCap` written; the two possible destinations `j` and `j + oldCap` |
| D-94 | Java 7's concurrent-resize cycle | 3.6.27 | step-sequence, 4 frames | Two threads transferring the same 2-node bin under Java 7's head-insertion transfer. Frame 1: initial `A → B`. Frame 2: thread 1 preempted mid-transfer holding `e = A`, `next = B`. Frame 3: thread 2 completes, producing `B → A`. Frame 4: thread 1 resumes and links `A → B`, closing the cycle; a later `get` shown spinning. Every pointer write numbered |
| D-95 | Java 8's quieter concurrent-resize bug | 3.6.28 | before-after | No cycle; instead show a lost entry, a resurrected removed entry, and the NPE site. Label "not an infinite loop, still a bug" |
| D-96 | The `TreeNode` inheritance chain and its cost | 3.6.30, 3.15.9, 3.15.11, 3.15.12 | hierarchy + memory-layout | `HashMap.Node` (32 B) → `LinkedHashMap.Entry` adds `before`,`after` (40 B) → `HashMap.TreeNode` adds `parent`,`left`,`right`,`prev`,`red` (56 B). Each box drawn to scale with its field list and byte total, including the header and alignment padding |
| D-97 | Poisson bin lengths at load factor 0.75 | 3.6.33, 3.6.34 | cost-curve | Bar chart of `e^-0.5 · 0.5^k / k!` for k = 0..8 with the exact values from the class comment (0.60653066, 0.30326533, 0.07581633, 0.01263606, 0.00157952, 0.00015795, 0.00001316, 0.00000094, 0.00000006); the 8 bar annotated "~6 in 100,000,000" and marked as the treeify point |
| D-98 | Treeify/untreeify hysteresis | 3.6.34 | state-transition | Two states LIST and TREE; the edge LIST→TREE labelled "bin size reaches 8 and table ≥ 64"; TREE→LIST labelled "bin size falls to 6 during resize split"; the gap 6..8 shaded and labelled "hysteresis band — prevents thrash" |
| D-99 | Sizing a `HashMap` for n entries | 3.6.37, 3.6.38 | step-sequence | `new HashMap<>(100)`: `tableSizeFor(100) = 128`, threshold `128 × 0.75 = 96`, resize at the 97th entry — drawn as a bar hitting the threshold. Then `(int)(100 / 0.75f) + 1 = 134 → tableSizeFor = 256`, threshold 192, no resize. Then `HashMap.newHashMap(100)` (Java 19) doing the same arithmetic |
| D-100 | `LinkedHashMap`'s overlay | 3.7.1, 3.7.2, 3.7.15 | memory-layout | The `HashMap` table below, the `before`/`after` doubly-linked chain drawn above it crossing bin boundaries; `head` and `tail` marked; the 2 extra references per entry called out as +8 bytes with compressed oops |
| D-101 | `afterNodeAccess` relinks to the tail | 3.7.4, 3.7.8 | before-after | Access-order chain `A→B→C→D`; `get(B)` moving B to the tail giving `A→C→D→B`; the six pointer updates numbered. A second panel showing `containsKey(B)` leaving the chain untouched — the asymmetry called out |
| D-102 | The LRU eviction cycle | 3.7.3, 3.7.9, 3.7.10 | step-sequence, 4 frames | A capacity-3 access-order `LinkedHashMap`. Frames: put A, put B, put C; get(A) moving A to the tail; put D triggering `afterNodeInsertion` → `removeEldestEntry` → evicting B (now the head). Show `removeEldestEntry(eldest)` returning `size() > 3` at the decision point |
| D-103 | `ReversedLinkedHashMapView` | 3.7.13, 1.9.9 | memory-layout | The same underlying chain with a thin view object that swaps the meaning of `head`/`tail` and of `putFirst`/`putLast`; `reversed().reversed()` shown returning to the original semantics |
| D-104 | The five red-black invariants | 3.8.1, 3.8.2 | hierarchy | A 9-node tree coloured red/black with NIL leaves drawn; each of the five invariants numbered and pointed at the place in the tree that demonstrates it; black-height annotated on three distinct root-to-leaf paths, all equal; `h ≤ 2 log₂(n+1)` written with n and h filled in |
| D-105 | `rotateLeft` / `rotateRight` | 3.8.5 | before-after, 2 frames | For each rotation: the three nodes and the subtree that changes parent, with the exact pointer writes numbered (child, parent, grandparent, and the `left`/`right` fixups), and the in-order sequence shown unchanged before and after |
| D-106 | `fixAfterInsertion` cases | 3.8.6 | step-sequence, 4 frames | Frame 1: red parent, red uncle → recolour and recurse up. Frame 2: red parent, black uncle, zigzag → rotate to straight. Frame 3: red parent, black uncle, straight → rotate and recolour. Frame 4: root forced black. Each frame draws the before and after subtree with colours |
| D-107 | `fixAfterDeletion` cases | 3.8.7 | step-sequence, 6 frames | The six cases with the "double black" node marked distinctly in every frame; sibling colour and sibling's children's colours labelled in each; the rotation or recolour applied; the terminating case identified |
| D-108 | `deleteEntry` successor swap | 3.8.8, 3.8.9 | before-after | A two-child node being deleted; the in-order successor located (leftmost of the right subtree); the key/value copied up; the successor's own node physically unlinked. Show why the second unlink is always the easy zero-or-one-child case |
| D-109 | `buildFromSorted` | 3.8.15 | step-sequence, 3 frames | 15 sorted entries; recursive midpoint selection building a perfectly balanced tree in O(n) with no rotations at all; the level at which nodes are coloured red to fix black-height marked. Contrast the n×O(log n) insert-one-at-a-time path |
| D-110 | `TreeMap.Entry` vs `HashMap.Node` | 3.8.17, 3.15.14 | memory-layout | 40 bytes (12 header + 5 refs + colour byte + padding) versus 32 bytes, each field named and sized, both drawn to scale |
| D-111 | Skip list levels | 3.8.21, 3.8.22, 3.14.33 | memory-layout | Four levels with `p = 0.25` producing roughly a quarter of the nodes at each higher level; a search path traced from the top-left down and right; a CAS insertion at the base level shown as a single pointer swing, contrasted with a red-black rotation touching three nodes — the reason lock-free is tractable on one and not the other |
| D-112 | Set over Map | 3.9.1–3.9.7 | memory-layout | `HashSet` holding a `HashMap`; every value slot pointing at the one shared `PRESENT` object; `add(e)` shown as `map.put(e, PRESENT) == null`. Beside it, `TreeSet`→`TreeMap`, `LinkedHashSet`→`LinkedHashMap` via the dummy-boolean constructor, `ConcurrentSkipListSet`→`ConcurrentSkipListMap` |
| D-113 | `CopyOnWriteArraySet` breaks the pattern | 3.9.8 | before-after | The expected shape (set over map, O(1) add) versus the actual shape (set over `CopyOnWriteArrayList`, `addIfAbsent` scanning n elements then copying the array). Cost annotations O(1) vs O(n) |
| D-114 | `EnumMap` internals | 3.10.1–3.10.5, 3.15.16 | memory-layout | `keyUniverse` array of the enum constants (shared, uncloned, via `SharedSecrets`); `vals` array indexed by ordinal with three occupied and four `null` slots; a null *value* stored as the `NULL` sentinel object, distinguishable from an absent key; `put` shown as `vals[key.ordinal()] = maskNull(v)` with no hashing anywhere |
| D-115 | `EnumMap`'s reused entry object | 3.10.6, 2.2.15 | before-after | An `EntryIterator` returning the same `lastReturnedEntry` instance each step; a `List<Map.Entry>` built from it shown as n references to one object, all reading the last key/value. The fix (`Map.entry(e.getKey(), e.getValue())` copy) drawn beside it |
| D-116 | Why enum-keyed `HashMap` is worse | 3.10.14, 1.7.16 | before-after | Two JVM runs of the same program: identity hash codes differ, so bucket assignment and iteration order differ between runs. `EnumMap` shown giving identical ordinal order in both runs |
| D-117 | `IdentityHashMap` linear probing and `closeDeletion` | 3.11.3 | step-sequence, 3 frames | Frame 1: three keys in a probe chain. Frame 2: the middle one removed, leaving a hole that would break the chain. Frame 3: `closeDeletion` walking forward and back-shifting the displaced entry into the hole. Index arithmetic `i += 2` with wraparound shown |
| D-118 | `WeakHashMap.Entry` *is* the reference | 3.11.8 | memory-layout | `Entry extends WeakReference<Object>`; the referent slot holding the key; `value`, `hash`, `next` as ordinary strong fields; the `ReferenceQueue` attached. Contrast with a `HashMap.Node` holding a strong key ref |
| D-119 | `ImmutableCollections.SetN` open addressing | 3.12.6, 3.12.7, 3.12.9, 3.12.10 | memory-layout | 3 elements in a table of `EXPAND_FACTOR × 3 = 6` slots, guaranteeing a free slot; `probe(pe)` returning `i` on a hit and `-(i+1)` on a miss; `SALT32L` from `System.nanoTime()` shown as the per-JVM-run starting offset, with two runs side by side giving two different iteration orders |
| D-120 | `MapN` interleaved table | 3.12.8 | memory-layout | One `Object[]` of length `2 × EXPAND_FACTOR × n`; key at `2i`, value at `2i+1`; three mappings placed with a probe collision resolved |
| D-121 | `List.of(a,b)` vs `new ArrayList<>(...)` | 3.12.1, 3.12.2, 3.12.17, 3.15.20 | memory-layout | `List12` as a single object with fields `e0`, `e1` and no array at all; versus an `ArrayList` object (24 B) plus a 10-slot `Object[]` (16 + 40 B) with 8 slots of slack. Byte totals on both |
| D-122 | `CollSer` serial proxy | 3.12.14, 2.16.6 | step-sequence | `writeReplace()` swapping the immutable collection for a `CollSer` carrying a tag and the elements; the stream contents; `readResolve` rebuilding via the factory; `readObject` on the collection class itself throwing `InvalidObjectException("not serial proxy")` |
| D-123 | `trySplit` recursion | 3.13.1–3.13.3, 3.13.6 | step-sequence, 3 frames | A 1000-element `ArrayList` spliterator splitting at the midpoint, then each half splitting again — a binary tree of 4 leaves with exact element ranges and `estimateSize()` at each node. Label `SIZED|SUBSIZED` as what makes the exact sizes known and lets fork-join pre-size the output array |
| D-124 | Good splits vs bad splits | 3.13.5, 3.13.7, 3.13.8, 3.13.9 | before-after | `ArrayList`: perfect midpoint halves. `LinkedList`: `LLSpliterator` walking to build batches — unequal, sequential, no `SUBSIZED`. `HashMap`: table-index-range splits, balanced only if entries are evenly distributed — show a skewed table. `IteratorSpliterator`'s arithmetically growing batches with `BATCH_UNIT = 1024` and `MAX_BATCH = 1 << 25` |
| D-125 | Spliterator characteristics and what each buys | 3.13.4, 3.13.5 | table | Rows: `ORDERED`, `DISTINCT`, `SORTED`, `SIZED`, `NONNULL`, `IMMUTABLE`, `CONCURRENT`, `SUBSIZED`. Columns: meaning, which pipeline optimisation it enables, which collections report it |
| D-126 | `ConcurrentHashMap` bin-level concurrency | 3.14.7, 3.14.11, 3.14.12 | memory-layout | A `volatile Node[] table`; an empty bin being filled by `casTabAt` (no lock); a populated bin under `synchronized (f)` on the bin head; two threads working on different bins simultaneously; a reader doing `tabAt` volatile reads through a locked bin without blocking |
| D-127 | `spread` and the reserved sign bit | 3.14.9, 3.14.10 | bit-layout | 32 bits; `h ^ (h >>> 16)`; then `& HASH_BITS (0x7fffffff)` clearing the top bit; the three negative special hashes listed with their values and node types: `MOVED = -1` (`ForwardingNode`), `TREEBIN = -2`, `RESERVED = -3` |
| D-128 | Cooperative resize with `ForwardingNode` | 3.14.13, 3.14.14 | step-sequence, 4 frames | Frame 1: `table` and `nextTable` side by side, `transferIndex` at the top. Frame 2: thread A CASes a stride of `MIN_TRANSFER_STRIDE = 16` and migrates it, leaving a `ForwardingNode` in each drained bin. Frame 3: a reader hitting a `ForwardingNode` and following it into `nextTable`. Frame 4: thread B, a writer, hitting a `ForwardingNode` and calling `helpTransfer` to claim the next stride instead of blocking |
| D-129 | `sizeCtl` states | 3.14.8 | state-transition | States and their encodings: `0` (default, table not yet created), `n` positive (next resize threshold), `-1` (initialising), `-(1 + activeResizers)` (resize in progress). Transitions labelled with the operation that causes each |
| D-130 | `size()` via striped counters | 3.14.15, 3.14.16 | memory-layout | `baseCount` plus a `CounterCell[]`; four threads each incrementing a different cell; `@Contended` padding drawn as the space between cells occupying separate 64-byte cache lines; `sumCount()` adding them all; the label "the sum is an estimate — cells can change mid-sum" |
| D-131 | Java 7 segments vs Java 8 bins | 3.14.23 | before-after | Left: 16 `Segment` objects, each a `ReentrantLock`-guarded mini `HashMap`, concurrency capped at `concurrencyLevel`, two keys in the same segment blocking each other. Right: one table, per-bin locking, concurrency bounded by bin count. Memory overhead of the segment array called out |
| D-132 | `CopyOnWriteArrayList` write path | 3.14.24 | before-after | The `volatile Object[] array`; a writer taking the `ReentrantLock`, `Arrays.copyOf` to a new array of n+1, writing the element, then `setArray` publishing it; two readers still traversing the old array with no lock; `COWIterator` holding its snapshot and `iterator.remove` throwing `UnsupportedOperationException` |
| D-133 | When CoW stops being a good idea | 3.14.25 | cost-curve | x = write ratio, y = total cost, one curve per collection size (100 / 10,000 / 1,000,000); the region where `CopyOnWriteArrayList` beats `ConcurrentHashMap.newKeySet()`/`synchronizedList` shaded; the crossover annotated with concrete numbers |
| D-134 | `ArrayBlockingQueue` vs `LinkedBlockingQueue` locking | 3.14.28 | before-after | Left: one `ReentrantLock`, `notEmpty` and `notFull` conditions, a single ring buffer — producer and consumer serialise on the same lock. Right: `putLock` and `takeLock` at opposite ends of a linked chain, `AtomicInteger count` shared, cascading signal shown — producer and consumer proceed in parallel |
| D-135 | `SynchronousQueue` handoff | 3.14.29, 1.4.32 | timeline | Producer arrives and parks; consumer arrives and the element is handed over directly with no storage; `isEmpty()` returning true throughout. A second lane showing `ThreadPoolExecutor` using it so that an unavailable worker forces thread creation instead of queueing |
| D-136 | Michael–Scott queue with lazy tail | 3.14.31, 1.4.34 | step-sequence, 4 frames | Frames showing `tail` lagging one node behind the true last node; a producer CASing `last.next` then attempting the `tail` CAS; another thread helping advance `tail`; and a `size()` traversal walking the whole chain — the O(n), approximate result labelled |
| D-137 | Object and array header layout | 3.15.1–3.15.5 | memory-layout | 12-byte object header (8-byte mark word + 4-byte compressed class word) and 16-byte array header (+4-byte length); the 8-byte alignment padding drawn; `Integer` = 12 + 4 = 16 B and `Long` = 12 + 4 pad + 8 = 24 B laid out field by field; a note that `-XX:+UseCompactObjectHeaders` drops 12 to 8 and shifts every figure |
| D-138 | 69 bytes to store 8 | 3.15.10 | memory-layout | One `HashMap<Integer,Integer>` entry decomposed: 32 B `Node` + 16 B key `Integer` + 16 B value `Integer` + ~5.3 B amortised table slot at load factor 0.75 ≈ 69 B; the 8 bytes of actual `int` data highlighted inside it; the ratio ~8.6× stated |
| D-139 | Node size ladder | 3.15.9, 3.15.11–3.15.14 | table | Rows `HashMap.Node` 32, `LinkedHashMap.Entry` 40, `HashMap.TreeNode` 56, `TreeMap.Entry` 40, `LinkedList.Node` 24, `ArrayDeque` slot 4, `EnumMap` slot 4. Columns: fields, raw bytes, aligned bytes |
| D-140 | `BitSet` vs `HashSet<Integer>` | 3.15.18 | cost-curve | Memory against domain size for a dense set: `BitSet` at 1 bit per element, `HashSet<Integer>` at ~50 bytes per element; the ~400× ratio annotated at n = 1,000,000 with both totals in bytes; the sparse regime where the ratio inverts marked |
| D-141 | Collections framework timeline | 3.16.1–3.16.15 | timeline | A horizontal axis from Java 1.0 to Java 25 with a labelled tick per release listed in §3.16, each carrying the types or features it introduced; the three version traps (JDK 9 `ArrayDeque` rewrite, JDK 8 `ConcurrentHashMap` rewrite, JDK 8 `Collections.sort` delegation) marked distinctly |
| D-142 | Hunting a leaking collection in a heap dump | 3.17.1–3.17.6 | flowchart | Symptom (rising old-gen, OOM) → `jcmd GC.heap_dump` → MAT → dominator tree → retained heap → `java.util.HashMap$Node[]` at the histogram top → `collection_fill_ratio` / `map_collision_ratio` queries → the two diagnoses they distinguish (over-allocated `ArrayList` vs bad `hashCode`) → the fix in each case |
| D-143 | Extending `AbstractList` for a linked structure is O(n²) | 3.18.4, 3.18.9 | step-sequence | `AbstractList.Itr` calling `get(i)` for each step; on a linked structure each `get(i)` walks i nodes, so a full iteration costs n²/2 hops — drawn as a triangle of work. `AbstractSequentialList` shown as the correct base. Beside it, `AbstractMap.get` scanning the whole `entrySet` |
| D-144 | Extend vs delegate | 3.18.10 | before-after | Left: `class ValidatingList extends ArrayList` overriding `add`; `addAll` shown bypassing the override entirely inside the superclass, so validation is skipped — the exact call path drawn. Right: a forwarding decorator where every method routes through the wrapper, so `addAll` cannot escape |

## Part 4 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-145 | `MyArrayList` field and class map | 4.1.1–4.1.3, 4.1.9 | hierarchy | The class with `elementData`, `size`, `modCount`, the two sentinel arrays, the nested `Itr`, `ListItr` and `SubList`; an arrow from each to the JDK member it mirrors, so the reader can navigate the real source from the reimplementation |
| D-146 | `MyHashMap.put` traced against the JDK | 4.3.4–4.3.6 | step-sequence, 4 frames | The same four inserts run through both `MyHashMap` and `java.util.HashMap`, side by side per frame: lazy table allocation, empty-bin fast path, chain append with `==`-before-`equals`, and a resize with the lo/hi split. Any deliberate simplification marked in a distinct colour |
| D-147 | Collision DoS, measured | 4.3.14, 3.6.35 | cost-curve | Insert time against key count for 10,000 keys with identical hash codes: the untreeified quadratic curve versus the treeified `n log n` curve, with wall-clock figures on both and the CVE-2011-4858 reference labelled |
| D-148 | LRU by hand: `HashMap` + doubly-linked list | 4.6.2, 5.1.17 | memory-layout | The map from key to node; the separate doubly-linked list with sentinel head and tail; a `get` shown as hash lookup then unlink-and-relink-at-tail; a `put` past capacity shown evicting the node after the head sentinel. Every pointer write numbered |
| D-149 | Fixed-capacity ring buffer | 4.6.4 | memory-layout | An 8-slot ring with `head`, `tail` and `count`; a full state and an empty state distinguished by `count` rather than by a reserved slot — contrast with `ArrayDeque`'s wasted-slot approach (D-77) |
| D-150 | `BiMap` two-map invariant | 4.6.6 | before-after | `forward` and `inverse` maps side by side; a `put(k, v)` where `v` is already bound to `k2`, showing the three writes needed to keep both maps consistent, and the state that would result if only one map were updated |

## Part 5 diagrams

| # | Diagram | Syllabus leaf | Type | Must show |
|---|---|---|---|---|
| D-151 | The `HashMap` one-page answer map | 5.1.1–5.1.9 | hierarchy | A single reference sheet: table → bin → node/tree, with the six constants, `hash()`, index masking, the lo/hi split, treeify at 8 / untreeify at 6 / capacity 64, resize doubling, and the Java 7 loop, each as one labelled box the candidate can walk in 90 seconds. Arrows show the order to say them in |
| D-152 | Version-stale claims vs Java 21 | 5.2.2 | table | Rows: `ArrayDeque` power-of-two masking, `HashMap` Java 7 four-shift rehash, `ConcurrentHashMap` segments, `Collections.sort` copying to an array, "capacity should be prime", `Hashtable` vs `HashMap` "the only difference is synchronization". Columns: what old material says, what Java 21 does, which release changed it, and the one-line answer that shows you know both |

---
# OUTPUT CONTRACT

## Exact files to write

All under `src/topics/02-java-collections/`. Create the directory. Write every file listed.

| File | Contents |
|---|---|
| `00-index.md` | The reading map: one line per file below, the leaf ranges each covers, the diagram id ranges each contains, the target version, and the total leaf count |
| `01-basics-a.md` | §1.1 Why a framework exists, §1.2 The hierarchy, §1.3 Interface method surfaces, §1.4 The implementation catalogue |
| `01-basics-b.md` | §1.5 Iteration, §1.6 Ordering, §1.7 The equals/hashCode contract |
| `01-basics-c.md` | §1.8 Generics and boxing, §1.9 Sequenced collections, §1.10 The matrices. **Ends with Part 1's summary table, 10 Q&As and 5 puzzles covering all of §1.1–§1.10** |
| `02-intermediate-a.md` | §2.1 Master cost table, §2.2 Fail-fast/fail-safe/weakly consistent, §2.3 Views, copies, snapshots, §2.4 Immutability tiers, §2.5 Wildcards and PECS |
| `02-intermediate-b.md` | §2.6 The `Collections` surface, §2.7 The `Arrays` surface, §2.8 Sorting, §2.9 Specialised maps and sets, §2.10 `NavigableMap` in anger |
| `02-intermediate-c.md` | §2.11 `Map` defaults, §2.12 Set algebra, §2.13 Collections and streams, §2.14 Choosing, §2.15 Legacy, §2.16 Serialization, §2.17 Third-party. **Ends with Part 2's summary table, 10 Q&As and 5 puzzles covering all of §2.1–§2.17** |
| `03-internals-a.md` | §3.1 `ArrayList` source walk, §3.2 Amortised analysis, §3.3 `LinkedList`, §3.4 `ArrayDeque`, §3.5 `PriorityQueue` |
| `03-internals-b.md` | §3.6 `HashMap` source walk, §3.7 `LinkedHashMap`, §3.8 `TreeMap` and red-black trees, §3.9 Set-over-Map |
| `03-internals-c.md` | §3.10 `EnumMap`/`EnumSet`, §3.11 `IdentityHashMap`/`WeakHashMap`, §3.12 `ImmutableCollections`, §3.13 `Spliterator` |
| `03-internals-d.md` | §3.14 Concurrency behaviour, §3.15 Memory footprint arithmetic |
| `03-internals-e.md` | §3.16 Version history, §3.17 Observability, §3.18 Abstract skeletons and writing your own. **Ends with Part 3's summary table, 10 Q&As and 5 puzzles covering all of §3.1–§3.18** |
| `04-build-a.md` | §4.1 `MyArrayList`, §4.2 `MyLinkedList`, §4.3 `MyHashMap` (+`MyHashSet`, `MyLinkedHashMap`) |
| `04-build-b.md` | §4.4 `MyArrayDeque`, §4.5 `MyPriorityQueue`, §4.6 Supporting builds. **Ends with Part 4's summary table, 10 Q&As and 5 puzzles covering all of §4.1–§4.6** |
| `05-interview.md` | §5.1 The 50 questions, §5.2 The trap index, §5.3 Drills. **Ends with Part 5's summary table, 10 Q&As and 5 puzzles**, then the file-set-wide flat `## Atomic concept checklist` |

If any single file becomes unwieldy, **split it further** (`03-internals-b1.md`,
`03-internals-b2.md`, …) and register the new files in `00-index.md`. Splitting is always
preferred to cutting content. Never merge files to reduce the count.

Standalone `.svg` files, if you use them rather than inline SVG, go in
`src/topics/02-java-collections/diagrams/` named `D-NN-short-slug.svg`.

## Required header on every file except `00-index.md`

```
# 02 Java Collections — <Part name> (<sections covered>)

**Target version: Java 21 LTS.** | **Part <n> of 5** | [Index](00-index.md)
Previous: [<file>](<file>) · Next: [<file>](<file>)
```

## Required footer on every file except `00-index.md`

```
---

**Leaves covered:** <explicit list or ranges, e.g. 1.1.1–1.1.11, 1.2.1–1.2.20, …> (<count> leaves)
**Leaves deferred:** <none | list with a one-line reason each>
**Diagrams included:** <D-01, D-02, …>
**Target version:** Java 21 LTS
```

---

# SELF-VERIFY BEFORE REPORTING DONE

Run this checklist against your own output. Do not report completion until every box
is genuinely satisfied.

**Coverage**
- [ ] All 901 syllabus leaves appear in the notes, or are listed in a `## Deferred` block with a reason.
- [ ] Every file's footer lists the leaves it covers, and the union across all files is all 901.
- [ ] Every file listed in the OUTPUT CONTRACT exists, with the required header and footer.
- [ ] `00-index.md` lists every file, its leaf ranges and its diagram ids.

**Format**
- [ ] Every file is Markdown (`.md`).
- [ ] No file was cut short for length. No "and so on", no "similar to the above", no deferred-for-space.
- [ ] No ASCII art anywhere. Every diagram is SVG or, where the manifest says `table`, a Markdown table.
- [ ] Every SVG has an explicit `viewBox`, no text below 11px, no external font or CSS dependency, and explicit contrasting fills so it reads on light and dark backgrounds.
- [ ] All 152 manifest diagrams are present, each captioned with its `D-NN` id, and each showing every element named in its `Must show` cell.
- [ ] Where the manifest specified a frame count, that many labelled frames exist.
- [ ] No emojis. No filler openers.
- [ ] Every comparison of three or more things is a table.

**Per concept**
- [ ] Every concept follows `Concept → Why it exists → How it works → SVG → Code → Gotcha`, in that order, with any inapplicable link explicitly noted in one line rather than dropped.
- [ ] Every Java snippet is complete and compiles as written, minus only imports, package declarations and pointless `main` scaffolding. No `...`, no "implementation omitted", no pseudo-code.
- [ ] Only the three callout markers `**Pitfall:**`, `**Insight:**`, `**Interview:**` are used.
- [ ] Every `[TRAP]` leaf carries a `**Pitfall:**` with wrong belief, symptom and fix.
- [ ] Every `[PROVE]` leaf has the argument worked through, not asserted.
- [ ] Every `[SOURCE]` leaf quotes real JDK source and explains every quoted line.
- [ ] Every `[NUM]` leaf states the arithmetic explicitly.
- [ ] Every `[BUILD]` leaf ships complete generic compiling code.
- [ ] Every `[RESEARCH]` leaf was re-verified, or the uncertainty is stated in the text.
- [ ] Every `[VERSION-TRAP]` leaf (3.4.3, 3.16.8, 5.2.2) states both what is true in 21 and what used to be true.
- [ ] Every `[X-REF nn]` leaf has a self-contained mechanism paragraph before the pointer.
- [ ] Version differences across Java 7 / 8 / 9+ / 21 are called out inline at the point of each claim.

**Per part**
- [ ] Part 1 ends with a summary table, 10 interview Q&As with full spoken-length model answers, and 5 predict-the-output puzzles with actual output and explanation.
- [ ] Part 2 ends with the same three.
- [ ] Part 3 ends with the same three.
- [ ] Part 4 ends with the same three.
- [ ] Part 5 ends with the same three.
- [ ] Part 4 items each carry a "Diff vs the real one" table covering bounds checks, intrinsics, serialization, `Spliterator` support, null policy, allocation tricks, and why the JDK bothers.

**Closing**
- [ ] `05-interview.md` ends with a flat `## Atomic concept checklist`, one bullet per distinct concept across all five parts, no nesting.

---

# REFERENCES

Primary sources this topic is built on. Do not invent additional URLs; if you need a fact
not covered here, verify it against the JDK 21 source or javadoc and cite that.

**JDK 21 source (`jdk-21+35` tag)**

- `java/util/ArrayList.java` — `grow()` delegating to `ArraysSupport.newLength`, the two empty-array sentinels, `removeIf` bitset compaction, `batchRemove`, `SubList` fields
- `java/util/HashMap.java` — all six constants, `hash()`, `tableSizeFor`, the verbatim lo/hi split loop with `loHead`/`hiHead`, `newHashMap`, the Poisson comment, the treeify threshold rationale
- `java/util/ArrayDeque.java` — no power-of-two requirement in Java 21; the `inc`/`dec`/`sub` helpers; `new Object[16 + 1]`; `grow` jump `< 64 ? +2 : >>1`; `MAX_ARRAY_SIZE`; the two-disjoint-slices loop comment
- `java/util/PriorityQueue.java` — `DEFAULT_INITIAL_CAPACITY = 11`, the `grow` policy, `heapify` bounds `(n >>> 1) - 1`, `removeAt` moved-element return semantics
- `java/util/LinkedHashMap.java` — the `before`/`after` entry shape, the three `afterNode*` hooks, `ReversedLinkedHashMapView`, `newLinkedHashMap`, the Java 21 `SequencedMap` methods
- `java/util/EnumMap.java` — `keyUniverse`/`vals`, the `NULL` sentinel with `maskNull`/`unmaskNull`, the reused `lastReturnedEntry` in `EntryIterator`
- `java/util/ImmutableCollections.java` — `SALT32L`, `REVERSE`, `List12`/`ListN`/`Set12`/`SetN`/`Map1`/`MapN`, `probe()`, `EXPAND_FACTOR = 2`, the `EMPTY` sentinel, `CollSer`, `ReverseOrderListView`
- `jdk/internal/util/ArraysSupport.java` — `SOFT_MAX_ARRAY_LENGTH = Integer.MAX_VALUE - 8`, `newLength`, `hugeLength` and its OOM condition

Browse at `https://raw.githubusercontent.com/openjdk/jdk/jdk-21%2B35/src/java.base/share/classes/<path>`.

**JDK 21 / 25 documentation**

- https://docs.oracle.com/en/java/javase/21/core/creating-sequenced-collections-sets-and-maps.html — the three sequenced interfaces, the `SortedSet.addFirst`/`SortedMap.putFirst` UOE rule, entry-snapshot `setValue` UOE, add-hostile sequenced views
- https://openjdk.org/jeps/431 — JEP 431, the retrofit map
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/package-summary.html — the full class and interface inventory
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collections.html — the complete static-method inventory
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Map.html — the default-method and static-factory list, `Map.Entry.copyOf`, `comparingByKey`/`comparingByValue`
- https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html — the concurrent-collection inventory
- https://docs.oracle.com/en/java/javase/25/docs/api/new-list.html — confirms no new collection types in Java 22–25

**Memory layout**

- https://shipilev.net/jvm/objects-inside-out/ — 12-byte header, 16-byte array header, 8-byte alignment, `Integer` 16 B, `Long` 24 B, compressed oops

**Sorting**

- https://link.springer.com/article/10.1007/s10817-017-9426-4 — de Gouw et al., the TimSort verification
- https://bugs.openjdk.org/browse/JDK-8234482 — the `mergeCollapse` invariant break and the `pushRun` `ArrayIndexOutOfBoundsException`

**Third-party collections**

- https://motlin.medium.com/java-has-streams-do-we-need-third-party-collections-dd12f473d105
- https://aip.ifi.uni-heidelberg.de/fileadmin/papers/2017/ICPE2017_EmpiricalStudyCollections_Costa.pdf — Eclipse Collections `UnifiedSet` at ~25% of `HashSet` memory; fastutil for primitive lists; Trove losing to the JDK in some benchmarks

**Java 21 migration**

- https://www.baeldung.com/java-21-sequenced-collections
- https://nipafx.dev/inside-java-newscast-45/ — the source-compatibility fallout of the JEP 431 retrofit

**Leak diagnosis**

- https://blog.heaphero.io/unbounded-caches-static-collections-and-unclosed-resources-the-3-killer-anti-patterns-causing-memory-leaks/ — the three collection-shaped leak anti-patterns

**Verification caveat carried over from the syllabus:** the Eclipse MAT collections-query
names in leaf 3.17.3 (`collection_fill_ratio`, `map_collision_ratio`, `array_fill_ratio`,
`hash_entries`, `collections_grouped_by_size`) are `[RESEARCH]`-tagged and were recorded
from recall. Confirm them against the current Eclipse MAT documentation before publishing
them as command names, or state in the text that the exact query names may differ by MAT
version.