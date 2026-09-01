# 02 Java Collections — Utility surfaces — INTERMEDIATE (§2.17)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [utilities/06-serialization.md](06-serialization.md) · Next: [build-it/01-supporting-builds.md](../build-it/01-supporting-builds.md)

## 1. Why this section exists

The JDK collections framework covers lists, sets, maps, queues, and deques —
but it does not cover multimaps, bimaps, bags, range maps, primitive
collections without boxing, or a real cache eviction policy. Every team
eventually hits one of these gaps and reaches for a library. This section
surveys the libraries that fill those gaps, what each one actually buys you
over hand-rolling the structure yourself, and — the concept that matters more
than any individual library name — the decision rule for when a third-party
dependency earns its place versus when it is dead weight.

## 2. Guava — the structures the JDK lacks [BOTH] (§2.17.1)

**Maven coordinate (verified):** `com.google.guava:guava:33.7.1-jre` (Maven
Central, checked 2026).

Guava is Google's general-purpose collections and utilities library. Its
value is almost entirely in structures the JDK never shipped:

- **`ImmutableList` / `ImmutableSet` / `ImmutableMap`** — truly immutable
  (not just unmodifiable views over a mutable backing collection), built via
  fluent builders, null-hostile by design (fails fast instead of silently
  admitting a `null` that surfaces as an NPE three calls later).
- **`Multimap` / `ListMultimap` / `SetMultimap`** — a key mapping to *multiple*
  values, backed by `Map<K, Collection<V>>` semantics without the boilerplate
  of `computeIfAbsent(key, k -> new ArrayList<>()).add(value)` scattered
  through the codebase.
- **`Multiset`** — a collection that tracks per-element counts (a "bag").
  Replaces the common `Map<T, Integer>` counting idiom.
- **`BiMap`** — a bidirectional map guaranteeing both keys and values are
  unique, with `inverse()` giving you the reverse mapping without maintaining
  two synchronized maps by hand.
- **`Table`** — a map keyed by *two* dimensions (row, column) to a value.
  Replaces `Map<R, Map<C, V>>` nesting.
- **`RangeMap` / `RangeSet`** — associate values with, or represent, a set of
  disjoint ranges (e.g., tax brackets, IP address blocks).
- **`Lists.partition`** — chunk a list into fixed-size sublists.
- **`Sets.cartesianProduct`** — the cartesian product of a list of sets.
- **`Iterables` / `Iterators`** — `Iterable`-level equivalents of `Stream`
  operations that predate `java.util.stream` and still cover corners streams
  don't (e.g., cycling, partitioning an `Iterable` lazily).
- **`MapMaker`** — Guava's original cache/map builder; largely superseded by
  Guava's own `CacheBuilder` and, better still, by Caffeine (§5 below) for
  new code.

**Insight:** the pattern across this list is "the JDK has the primitive
building block but not the composite shape." A `Multimap` is not a new
algorithm — it is `Map<K, List<V>>` with the null-checks, resizing, and
mutation-safety already handled. That is exactly the kind of gap a dependency
is justified in filling: a shape the JDK omits, not a marginally faster
version of a shape it already has.

```java
import com.google.common.collect.ArrayListMultimap;
import com.google.common.collect.Multimap;

Multimap<String, String> teamToMembers = ArrayListMultimap.create();
teamToMembers.put("platform", "amara");
teamToMembers.put("platform", "koji");
teamToMembers.put("payments", "lena");

teamToMembers.get("platform"); // ["amara", "koji"] — never null, empty if absent
```

### Which Guava type replaces which hand-rolled pattern

| Hand-rolled pattern | Guava replacement | What you stop writing |
|---|---|---|
| `Map<K, List<V>>` with manual `computeIfAbsent` | `ListMultimap` | Null-checks, list creation on first insert |
| `Map<K, Set<V>>` with manual `computeIfAbsent` | `SetMultimap` | Same, deduplicated |
| `Map<T, Integer>` counters, manual increment/decrement/remove-at-zero | `Multiset` | Boxing, zero-removal bookkeeping |
| Two maps kept in sync for forward/reverse lookup | `BiMap` | Manual dual-write, drift risk |
| `Map<R, Map<C, V>>` nested maps | `Table` | Null outer-map checks, `row()`/`column()` views |
| `if (x >= lo && x < hi) return bracket;` chains | `RangeMap` | Linear bracket search, boundary bugs |
| Defensive-copy wrapper classes for "never mutate this" | `ImmutableList/Set/Map` | Hand-written unmodifiable wrappers, null-guard code |

## 3. The decision rule — when a dependency earns its place [STAFF] (§2.17.9, §2.17.10)

This is the concept every reader of this section should walk away with,
because the section as a whole is answering one question: *should I add
this dependency?*

**Reach outside the JDK only for one of three reasons:**

1. **Primitive specialisation with a measured allocation problem.** You have
   profiled — not guessed — that boxing `Integer`/`Long` in a hot `HashMap`
   or `ArrayList` is producing GC pressure or cache-miss cost that matters at
   your throughput. "It feels slow" is not a measurement; a heap histogram or
   an allocation-rate flame graph is.
2. **A data structure the JDK genuinely lacks.** Multimap, bimap, bag, range
   map, off-heap ring buffer, compressed bitset — the JDK has no equivalent
   at all, so you are not choosing between "JDK version" and "library
   version," you are choosing between "write it yourself" and "use a
   library that has already had the edge cases found."
3. **A real cache.** `LinkedHashMap` in access-order mode with
   `removeEldestEntry` overridden, or `WeakHashMap` used for its GC-tied
   eviction, are both structurally incapable of being a correct cache (see
   §4 below). If you need eviction under memory or size pressure with a
   sane hit rate, that is a real requirement a real cache library answers.

**Otherwise the dependency is not worth it.** "This third-party `HashMap`
benchmarks 8% faster on a microbenchmark" is not a reason — production
workloads rarely look like microbenchmarks, and the 8% is dwarfed by the
cost below.

**Cost of the dependency, every time, regardless of which of the three
reasons applies:**

- **Shading.** If your library depends on Guava (a near-certainty in the
  Java ecosystem) and the third-party collections library also depends on a
  *different* Guava version, you now own a version-conflict problem that
  either you resolve with shading/relocation or your build tool resolves for
  you — badly, via "nearest wins," which silently picks a version nobody
  tested against.
- **Transitive conflicts.** Every dependency you add is also every
  dependency *it* depends on. A "just add fastutil" decision can pull in
  version skew across a dozen transitive jars you never intended to touch.
- **Module system friction.** Java's module system (JPMS) requires
  well-formed module descriptors to participate cleanly in a modular build;
  older or slower-moving third-party libraries lag on `module-info.java`
  support, forcing you onto the classpath (unnamed module) or automatic
  modules with weaker encapsulation guarantees.
- **Security surface.** Every dependency is code you did not write, did not
  review, and now ship in production. §7 below is the canonical cautionary
  tale for this exact cost.

**Interview:** if asked "would you add library X to replace `HashMap`?", the
strong answer is not "yes, it's faster" or "no, never" — it is naming which
of the three reasons applies (or doesn't) and pricing the dependency cost
against the measured problem it solves.

## 4. Primitive-collection libraries [SENIOR IC] (§2.17.2, §2.17.3, §2.17.4)

Every JDK collection over a primitive type — `List<Integer>`, `Map<Long,
String>` — boxes. Each element becomes a separate heap object with its own
header, and iteration chases pointers instead of walking a contiguous array.
For numeric-heavy workloads (graph algorithms, columnar data, ID-keyed
lookups at scale) this is the single most common measured reason to reach
outside the JDK.

**Eclipse Collections** (`org.eclipse.collections:eclipse-collections:13.0.0`,
Maven Central, checked 2026) — a collections framework built around three
ideas: a strict `MutableList`/`ImmutableList` type split (so the type system,
not a runtime exception, tells you a list can't be mutated), dedicated
primitive collections (`IntList`, `LongSet`, etc.) alongside object
collections, and eager (not lazily-streamed) functional methods. It also
ships `UnifiedSet`/`UnifiedMap` as drop-in `HashSet`/`HashMap` replacements,
a `Bag` (multiset) type, a `BiMap`, and `Interval` for lazy numeric ranges.
Eclipse Collections' own published benchmarks and engineering blog report
`UnifiedSet` using roughly 25% of the memory of `java.util.HashSet` for
equivalent contents — verified via the Eclipse Collections engineering blog
("UnifiedSet — The Memory Saver") and cross-referenced against the project's
own benchmark suite.

**fastutil** (`it.unimi.dsi:fastutil:8.5.18`, Maven Central, checked 2026) —
type-specialized collections for every primitive combination:
`IntArrayList`, `Int2ObjectHashMap`(-shaped types, named `Int2ObjectOpenHashMap`
in fastutil's actual API), `Object2IntMap`, and so on, generated for all
eight primitive types crossed with object types. It is widely regarded as
best-in-class for raw primitive list/map throughput and is one of the few
libraries in this space with genuine large-array support (arrays addressed
by `long` index, past the `int`-indexed `2^31` JDK array limit).

```java
import it.unimi.dsi.fastutil.ints.IntArrayList;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;

IntArrayList ids = new IntArrayList();
ids.add(101);
ids.add(102); // no boxing — backed by a raw int[]

Int2ObjectOpenHashMap<String> idToName = new Int2ObjectOpenHashMap<>();
idToName.put(101, "amara");
```

**HPPC, Koloboke, Trove — historical and niche.** HPPC (High Performance
Primitive Collections) and Koloboke occupied the same niche as fastutil and
Eclipse Collections' primitive types but saw far less ongoing maintenance;
most new work in this space converges on fastutil or Eclipse Collections.
Trove was for years the default answer to "primitive `HashMap` in Java," but
JDK `HashMap`/`HashSet` implementation improvements over subsequent releases
closed enough of the gap that Trove's primitive `HashSet` loses to the JDK's
own in some published benchmarks — a concrete illustration of §3's decision
rule: a library justified by a performance delta stops being justified once
the delta disappears.

### Primitive-collection libraries compared

| Library | Type-safety model | Primitive support | Standout feature | Maintenance status (2026) |
|---|---|---|---|---|
| JDK `HashMap`/`ArrayList` (boxed) | Generic, boxes primitives | None natively | Zero dependency, universally understood | Actively maintained (JDK core) |
| fastutil | Generated per-type classes | All 8 primitives × object | Best-in-class raw primitive throughput; `long`-indexed large arrays | Actively maintained |
| Eclipse Collections | `Mutable`/`Immutable` interface split | `IntList`, `LongSet`, etc. | `UnifiedSet` ~25% memory of `HashSet`; eager functional API | Actively maintained (Eclipse Foundation) |
| HPPC | Generated per-type classes | Most primitives | Simpler API surface than fastutil | Low/inactive |
| Koloboke | Generated per-type classes | Most primitives | Open-addressing focus | Low/inactive |
| Trove | Generated per-type classes | Most primitives | Historical default; superseded | Effectively unmaintained; JDK now competitive or better for primitive `HashSet` |

**Pitfall:** picking fastutil (or any primitive library) because "primitives
are faster" without a heap profile confirming boxing is actually the
bottleneck. If your hot path is I/O-bound or the collection in question holds
a few hundred elements, the boxing overhead is noise, and you have paid the
full dependency cost of §3 for a change nothing will measure.

## 5. Caffeine — the actual cache answer [BOTH] `[X-REF 15]` (§2.17.5)

The single most common third-party-collection question in interviews and in
real codebases is "we need a cache, can we just use a `LinkedHashMap`?" The
honest answer is no, for two structural reasons, not stylistic ones:

`LinkedHashMap` in access-order mode with `removeEldestEntry` overridden
gives you LRU-by-insertion/access-order and nothing else — no policy that
distinguishes a frequently-reused entry from a one-off scan, no admission
policy to decide whether a *new* entry is worth admitting over an existing
one, and no automatic size-bound enforcement beyond what you wire up
yourself in `removeEldestEntry`. `WeakHashMap` is worse for this purpose:
its eviction is tied to GC reachability of the *key*, which means eviction
timing is nondeterministic and driven by garbage-collector behavior you do
not control, not by any notion of "this entry is cold." Neither structure
was designed as a cache; both happen to have a method that superficially
resembles one.

**Caffeine** (`com.github.ben-manes.caffeine:caffeine:3.2.4`, Maven Central,
checked 2026, requires Java 11+; use the 2.x line only on Java 8) is a
purpose-built cache backed by **W-TinyLFU** (Window TinyLFU), an admission +
eviction policy that tracks approximate access frequency (via a compact
counting sketch, not a full LRU chain) and uses it to decide both what to
evict and what to admit in the first place. Caffeine's own published
benchmarks show a measured hit-rate improvement over plain LRU on real-world
trace workloads at comparable or lower memory cost — the two axes
`LinkedHashMap`-as-LRU cannot even express, since it has no frequency signal
and no admission decision at all.

Full treatment of W-TinyLFU's internals, the counting sketch, and Caffeine's
API surface (`Caffeine.newBuilder()`, refresh-ahead, async loading caches) is
owned by the caching guide — see guide 15 for the complete deep dive. This
section's job is only to establish *why* `LinkedHashMap`/`WeakHashMap` fail
structurally and point you at guide 15.

## 6. Low-latency and specialized libraries — supporting facts (§2.17.6, §2.17.7, §2.17.8)

These three do not carry the same central tradeoff as Guava's structural
gap-filling or the primitive-vs-boxed decision — each is "this library exists
and solves this specific niche problem" — so they are covered as supporting
facts and folded into the survey table in §7.

**Agrona / JCTools** (`org.agrona:agrona:2.5.0` and
`org.jctools:jctools-core:4.0.6`, both Maven Central, checked 2026) are the
low-latency trading-system-grade end of this space. Agrona provides
off-heap and direct-buffer-backed structures (`Object2ObjectHashMap` as a
GC-friendlier map, ring buffers, off-heap atomic structures) built for
predictable latency under load. JCTools provides lock-free and
wait-free concurrent queues beyond what `java.util.concurrent` ships —
notably `MpscArrayQueue` and the general family including
`ManyToOneConcurrentArrayQueue`-shaped many-producer/single-consumer queues,
purpose-built for the specific producer/consumer cardinality of a workload
rather than the general-purpose `ConcurrentLinkedQueue`.

**Apache Commons Collections** (`org.apache.commons:commons-collections4`,
current `4.6.0`, Maven Central, checked 2026 — note the legacy
`commons-collections:commons-collections` 3.x artifact is the vulnerable one,
see §7) adds `MultiValuedMap` (Commons' own multimap), `Bag`, and
`CircularFifoQueue` (a fixed-capacity queue that silently overwrites the
oldest element once full — useful for "keep the last N events" patterns).

**RoaringBitmap** (`org.roaringbitmap:RoaringBitmap:1.6.14`, Maven Central,
checked 2026) is a compressed bitset structure used for sparse or
semi-sparse sets of integers — set membership, boolean masks, and set
operations (union, intersection) at scale, used in production by systems
like Apache Spark, Apache Pinot, and Netflix's Atlas for exactly this
compressed-bitset role.

## 7. Library survey table

| Library | Maven coordinate (verified 2026) | What it adds/replaces | Reach for it when |
|---|---|---|---|
| Guava | `com.google.guava:guava:33.7.1-jre` | Multimap, BiMap, Multiset, Table, RangeMap/RangeSet, immutable collections | You need a shape the JDK lacks entirely |
| Eclipse Collections | `org.eclipse.collections:eclipse-collections:13.0.0` | Mutable/Immutable type split, primitive collections, `UnifiedSet`/`UnifiedMap` (~25% memory of JDK `HashSet`) | Measured memory pressure from boxed collections, or want eager functional API with type-enforced immutability |
| fastutil | `it.unimi.dsi:fastutil:8.5.18` | Per-primitive-type collections, `long`-indexed large arrays | Measured allocation/boxing bottleneck in numeric-heavy code |
| HPPC / Koloboke / Trove | (historical; no current recommended coordinate) | Primitive collections (older generation) | Legacy code only — new code should use fastutil or Eclipse Collections instead |
| Caffeine | `com.github.ben-manes.caffeine:caffeine:3.2.4` | Real cache: W-TinyLFU admission + eviction, size/time-bound, async loading | Any time you need bounded eviction with a real hit-rate policy — never `LinkedHashMap`/`WeakHashMap` as a cache |
| Agrona | `org.agrona:agrona:2.5.0` | Off-heap/direct-buffer structures, GC-friendlier maps, ring buffers | Low-latency systems needing predictable, allocation-free hot paths |
| JCTools | `org.jctools:jctools-core:4.0.6` | Lock-free/wait-free concurrent queues tuned to producer/consumer cardinality | High-throughput concurrent queueing where `java.util.concurrent`'s general-purpose queues aren't tight enough |
| Apache Commons Collections | `org.apache.commons:commons-collections4:4.6.0` | `MultiValuedMap`, `Bag`, `CircularFifoQueue` | Small utility gaps — but audit the version and never use the legacy 3.x `commons-collections` artifact |
| RoaringBitmap | `org.roaringbitmap:RoaringBitmap:1.6.14` | Compressed sparse/semi-sparse bitsets with fast set operations | Large integer-keyed membership/boolean-mask sets at scale |

## Pitfalls

**Pitfall:** reaching for a third-party collection library before measuring
whether the problem it solves actually exists in your workload. "fastutil is
faster" or "Eclipse Collections uses less memory" are true statements about
the library in isolation, but irrelevant if your `HashMap<Integer, String>`
holds two hundred entries and is touched once per request — the fix here is
§3's rule: profile first (heap histogram, allocation flame graph, or GC log),
then reach outside the JDK only once the profile shows the JDK structure is
actually the bottleneck.

**Pitfall:** treating "add a dependency" as free because the library is
popular or well-known. Apache Commons Collections is the canonical
counter-example: versions of `commons-collections` prior to 3.2.2 (and
`commons-collections4` prior to 4.1) shipped `InvokerTransformer`, a class
whose `transform()` method could be chained via Java's own deserialization
mechanism into arbitrary code execution (CVE-2015-6420). This was not a
theoretical bug — it was the basis of the "ysoserial" gadget chain used
against real production deployments of IBM WebSphere, Oracle WebLogic, and
others once any of those systems deserialized untrusted data with a
vulnerable Commons Collections version on the classpath. Every dependency
you add, including a "just a utility library" one, is code shipping in your
process with its own CVE surface and its own patch cadence you now own.

## Cheat sheet

See the library survey table in §7 above — it doubles as the cheat sheet:
one row per library, what it adds, and the concrete trigger condition for
reaching for it.

**Decision rule, restated as a checklist:**

- [ ] Have I profiled (not guessed) that boxing/allocation is the bottleneck? → primitive library (fastutil / Eclipse Collections)
- [ ] Does the JDK have no equivalent shape at all (multimap/bimap/bag/range map/bitset)? → Guava / Commons Collections / RoaringBitmap
- [ ] Do I need eviction with a real hit-rate policy, not just insertion order? → Caffeine, never `LinkedHashMap`/`WeakHashMap`
- [ ] Am I in a genuinely low-latency, allocation-sensitive hot path with measured GC/queue contention? → Agrona / JCTools
- [ ] Have I priced shading, transitive conflicts, module-system friction, and CVE surface against the measured problem? → if no, stop and measure first

## Self-test

<details>
<summary>1. Why is `Multimap` in Guava considered filling a gap the JDK lacks, rather than a faster version of something the JDK has?</summary>

Because the JDK has no `Map<K, List<V>>`-shaped type at all — you would
otherwise hand-roll it with `computeIfAbsent`. Guava is not competing on
speed here; it is providing a composite shape the standard library never
shipped.
</details>

<details>
<summary>2. Under the decision rule in §3, which of the three justified reasons applies to reaching for RoaringBitmap over a `BitSet` or `HashSet<Integer>`?</summary>

Reason (b): the JDK has no compressed sparse-bitset structure with fast
set-algebra operations at scale. It is not a primitive-boxing fix (reason a)
or a cache (reason c) — it is a data structure the JDK genuinely lacks for
that access pattern.
</details>

<details>
<summary>3. What two structural properties does `LinkedHashMap`-as-LRU lack that a real cache library provides?</summary>

An eviction policy driven by more than insertion/access order (i.e., no
frequency signal distinguishing hot from cold entries), and an admission
policy — a decision about whether a new entry is even worth admitting over
an existing one. `LinkedHashMap` has neither; it only orders and lets you
manually enforce a size bound in `removeEldestEntry`.
</details>

<details>
<summary>4. Why is `WeakHashMap` specifically worse than `LinkedHashMap` as a cache mechanism?</summary>

Its eviction is tied to garbage-collector reachability of the key, which
means eviction timing is nondeterministic and controlled by GC behavior, not
by any notion of which entries are cold. `LinkedHashMap` at least gives you
deterministic, policy-driven (if primitive) ordering.
</details>

<details>
<summary>5. What does W-TinyLFU add over plain LRU that Caffeine's benchmarks are measuring?</summary>

A frequency-aware admission and eviction policy backed by a compact counting
sketch — it tracks approximate access frequency, not just recency, and uses
that to decide both what to evict and whether a new entry deserves admission
at all. The measured result is a higher hit rate than plain LRU at
comparable memory cost.
</details>

<details>
<summary>6. Concretely, what made CVE-2015-6420 in Apache Commons Collections dangerous, and which artifact/versions were affected?</summary>

`InvokerTransformer.transform()` could be chained through Java's native
object deserialization into arbitrary method invocation, enabling remote
code execution against any application that deserialized untrusted data
with a vulnerable version on the classpath. Affected: `commons-collections`
prior to 3.2.2, and `commons-collections4` prior to 4.1. It became the basis
of real-world exploit chains against WebSphere, WebLogic, and other
production systems.
</details>

<details>
<summary>7. Eclipse Collections' `UnifiedSet` claims roughly what memory footprint relative to `java.util.HashSet`, and does that come at zero cost elsewhere?</summary>

Roughly 25% of `HashSet`'s memory footprint per the project's own published
benchmarks. It is not free in every dimension — the project's own benchmark
data shows JDK `HashSet` performing slightly better than `UnifiedSet` on raw
`add()` throughput, though `forEach()` iteration favors `UnifiedSet`. Memory
savings and add-throughput are a real tradeoff, not a strict win.
</details>

<details>
<summary>8. Why does Trove's primitive `HashSet` losing to the JDK's own `HashSet` in some benchmarks matter beyond "Trove is old"?</summary>

It is a concrete illustration of §3's decision rule: a dependency justified
purely by a performance delta stops being justified once the JDK closes that
delta. The lesson generalizes past Trove — any library adopted for "it's
faster" needs periodic re-measurement, not a one-time decision baked in
forever.
</details>

<details>
<summary>9. Name the four costs listed under "cost of the dependency" in §3, beyond the library's runtime behavior.</summary>

Shading (resolving conflicting transitive versions of the same library),
transitive conflicts (version skew pulled in by the new dependency's own
dependencies), module system friction (JPMS descriptor support, automatic
modules, weaker encapsulation on the classpath), and security surface
(code you didn't write or review, now shipping in production with its own
CVE exposure).
</details>

<details>
<summary>10. A colleague wants to add JCTools purely because "lock-free queues sound faster than `ConcurrentLinkedQueue`." How should you evaluate that request under this section's decision rule?</summary>

Ask what producer/consumer cardinality the workload actually has and whether
there is a measured latency or throughput problem with the current queue.
JCTools' value is a queue implementation tuned to a specific cardinality
(e.g., many-producer/single-consumer); if there's no measured bottleneck and
no cardinality mismatch, this is the §3 anti-pattern — paying dependency
cost (transitive conflicts, module friction, security surface) for an
unmeasured, possibly nonexistent problem.
</details>

## Open questions

- None. All numeric and version claims in this file were verified via web
  search against Maven Central / project sources at time of writing
  (2026-08); none required an `**Unverified:**` marker.

---

**Leaves covered:** 2.17.1-2.17.10 (10 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 445
