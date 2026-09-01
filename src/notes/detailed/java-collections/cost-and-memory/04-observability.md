# 02 Java Collections — Cost and memory — INTERNALS (§3.17 Observability: inspecting collections at runtime)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [cost-and-memory/03-internals-memory-collections.md](03-internals-memory-collections.md) · Next: [array-list/01-internals-a-growth.md](../array-list/01-internals-a-growth.md)

Everything before this file was arithmetic you can do with a spec in hand; this file is what you reach for when the arithmetic says a collection should be small and production says otherwise. The tools here range from a full-stop-the-world heap dump you take once during an incident to an always-on Micrometer gauge that costs nothing and catches the problem before the incident starts — the discipline running through the whole file is knowing which end of that spectrum a given symptom calls for, and never reaching for the expensive tool when the cheap one would have shown you the same thing sooner.

## Hierarchy before details

| Tool | Question it answers | Production-safe? | Cost while running | What it cannot tell you |
|---|---|---|---|---|
| `jcmd GC.heap_dump` / `jmap -dump:live` | What is retaining memory right now, in full object-graph detail | No — stop-the-world pause, multi-GB file | Seconds to tens of seconds STW; disk I/O for a file often larger than live heap | Anything about the past — one frozen snapshot, no history |
| Eclipse MAT (offline, on the dump) | Which collection dominates retained heap; is it collisions or over-allocation | Yes — runs on a laptop against the file, not the live process | Analysis-time only: minutes of MAT's own heap and CPU | Allocation call sites — MAT sees the graph, not who built it |
| `jcmd GC.class_histogram` | Rough live counts of `Node`/`Entry`/array instances, no dump needed | Mostly yes — still triggers a young-ish pause, far cheaper than a full dump | A single, short STW pause (no file write) | Retained-heap relationships — a count, not a graph |
| Debugger (breakpoint + watch) | What is in this collection, right now, at this line | Only in dev/staging — pausing a live thread in prod is rarely acceptable | Pauses the one thread (or the JVM, depending on breakpoint type) indefinitely | Anything before the breakpoint fired or on threads you aren't watching |
| JFR allocation profiling (`ObjectAllocationSample`) | Which call site is allocating the `HashMap$Node`/`Object[]` instances | Yes — designed for production, sub-1% overhead | Continuous low overhead; recording file grows with duration | Exact byte-for-byte size — it samples, it does not dump |
| async-profiler `-e alloc` | Same question, out-of-process, no JFR wiring needed | Yes — attaches via `-p <pid>`, low overhead | Similar to JFR; slightly higher fidelity at slightly higher cost | Retained-heap graph — allocation only, not lifetime |
| Micrometer gauge on collection size | Is this cache/collection growing unbounded, continuously | Yes — this is the always-on guard | Effectively free — one `size()` call per scrape | Root cause — a gauge tells you *that*, never *why* |

**Insight:** read the table top to bottom as escalation, not as a menu — a Micrometer gauge trend is what should page you, JFR/async-profiler is what tells you where the growth is coming from, and a heap dump plus MAT is the last resort you reach for only once the first two have narrowed the search, because it is the only row that stops the world.

## 3.17.1–3.17.6 The heap-dump-to-MAT leak-hunting workflow `[X-REF 06]`

**Mental model.** A leaking `HashMap` does not announce itself; it shows up as a slowly rising old-gen sawtooth that stops falling back to baseline, then an `OutOfMemoryError: Java heap space`. The workflow that gets you from that symptom to a root cause is always the same five steps: freeze the heap, load it into a tool that understands object graphs, find the biggest retainer, ask whether it is collisions or over-allocation, fix that specific thing.

**Why it exists.** A running JVM's heap is a live, constantly mutating graph across potentially millions of objects — no amount of staring at `jconsole`'s memory graph tells you *which* `HashMap` field on *which* instance is holding the objects that should have been garbage. You need a frozen, navigable snapshot, and a tool built to compute retained-size and dominator relationships over it; that is a heap dump plus Eclipse MAT (or VisualVM's OQL/heap-walker views, which cover a subset of the same ground).

**When to reach for it, and when not.** Reach for it once a Micrometer trend or a `GC.class_histogram` count has already told you *something* is growing — a full heap dump is expensive enough (seconds of STW, a file frequently larger than the live heap set because it also captures dead-but-not-yet-collected objects) that pulling one speculatively, on a healthy service, is itself an incident. Do not reach for it to answer "is my cache too big" — a Micrometer gauge answers that for free (§3.17.13).

**How it works.** Take the dump with one of two equivalent commands:

```bash
# Preferred: attaches via the Attach API, works against any HotSpot JVM you can jcmd
jcmd 12345 GC.heap_dump /tmp/heap.hprof

# Older / scriptable equivalent, same file format
jmap -dump:live,format=b,file=/tmp/heap.hprof 12345
```

`jmap -dump:live` (the `live` qualifier) forces a full GC before dumping so only reachable objects are captured — this makes the dump smaller and the leak candidate stand out, but it is also the reason the pause is longer than a bare `jcmd GC.heap_dump`, which does not force a collection first. On a multi-gigabyte heap, budget the STW pause in the seconds-to-tens-of-seconds range and the file size as comparable to live-set size; do this against a drained/cordoned instance in a fleet, never against the one instance serving 100% of production traffic if you have a choice.

Open the file in Eclipse MAT. Run the **Leak Suspects Report** first — it is automated and frequently names the culprit outright — then drill into the **Dominator Tree**, sorted by **Retained Heap** descending. The dominator tree answers "if I deleted this one object, what else would become garbage with it" — that is exactly the question a leak hunt needs, because a leaking `HashMap` field dominates every `Node` and every key/value it holds, and MAT's retained-size column will show that whole subtree as one number against the map instance. When `java.util.HashMap$Node[]` (the bucket table, not any individual `Node`) sits at the top of the class histogram by retained size, you have found the collection; the next question is *why* it grew, which leaves 3.17.3–3.17.5 answer.

![Heap-dump leak-hunt workflow: symptom (rising old-gen, OOM) through jcmd GC.heap_dump, MAT's dominator tree, the HashMap$Node[] at the top of the histogram, the collection_fill_ratio / map_collision_ratio queries that split into over-allocated ArrayList versus bad hashCode, and the fix for each](../diagrams/D-142-heap-dump-leak-hunt.svg)

**Example.** MAT also exposes an OQL (Object Query Language) console for ad hoc graph queries once you have a suspect class:

```
SELECT * FROM java.util.HashMap$Node WHERE this.@retainedHeapSize > 1000000
```

**Gotcha:** the dominator tree is computed over the *dump*, which is a snapshot of one instant — a map that grows and shrinks cyclically (e.g. a per-request cache cleared at request end) can look identical in a dump taken mid-cycle to one that never shrinks; take two dumps minutes apart and diff the retained sizes (MAT's **Compare Basket**) before concluding you have a leak rather than a healthy peak.

> The heap-dump-to-MAT workflow turns "something is using too much memory" into "this field on this instance, retaining this many bytes" by freezing the heap and computing dominator relationships over the frozen graph.

## 3.17.3 MAT's Collections queries: fill ratio, collision ratio, and friends `[RESEARCH]`

**Mental model.** Once MAT has told you *which* collection dominates the heap, its **Collections** query category (right-click a class or set of instances → `Java Collections`) answers the follow-up question — is this collection sized about right for what it holds, or is something structurally wrong with it.

**Why it exists.** A raw retained-size number does not distinguish "this map correctly holds ten million entries because the business really has ten million users" from "this map holds ten thousand entries in a table sized for ten million" or "this map holds ten thousand entries whose hash codes collided into one bucket." Those are three different bugs (or non-bugs) with the same symptom, and MAT's collections queries are purpose-built to tell them apart.

**When to reach for it, and when not.** Reach for it immediately after the dominator tree names a collection class as the top retainer — it is the next click, not a separate investigation. Skip it when the dominator tree already shows a plainly correct cause (e.g. ten million distinct business keys you can independently verify against a row count).

**How it works.** The relevant built-in queries, run from MAT's `Java Collections` category (exact menu names as of MAT 1.14):

| Query | What it measures | Reads as a problem when |
|---|---|---|
| `Collection Fill Ratio` (`collection_fill_ratio`) | Ratio of used slots to allocated capacity, per instance, for `ArrayList`/array-backed collections | Consistently well under 1.0 across many instances → systematic over-allocation |
| `Map Collision Ratio` (`map_collision_ratio`) | Ratio of entries sharing a bucket to total entries, for `HashMap`/`Hashtable`-family maps | Near 1.0 → almost every entry is chained off a collision, not spread across buckets |
| `Array Fill Ratio` (`array_fill_ratio`) | Same idea as collection fill ratio, applied to raw arrays rather than collection wrappers | Low ratio on a large array → oversized backing array not yet (or never) filled |
| `Hash Entries` (`hash_entries`) | Enumerates the live key/value pairs of a chosen map/set instance | Used to eyeball actual key distribution, not a ratio |
| `Collections grouped by size` (`collections_grouped_by_size`) | Buckets all instances of a collection class by element count | A long tail of many small, mostly-empty instances → a per-object collection field that should have been lazily allocated |

**Example.** Run from the OQL console equivalent, listing every `ArrayList` under a fill-ratio threshold:

```
SELECT AS RETAINED SET l FROM java.util.ArrayList l WHERE (l.size / l.@elementData.@length) < 0.25
```

**Gotcha:** `map_collision_ratio` and `collection_fill_ratio` are per-instance statistics — a single healthy map with correct distribution sitting next to a thousand tiny pathological ones will not move the aggregate you glance at first; always sort by instance, not by an averaged summary.

**Unverified:** exact MAT UI query labels have shifted cosmetically across MAT releases (1.12 vs 1.14); the underlying OQL identifiers (`collection_fill_ratio`, `map_collision_ratio`, `array_fill_ratio`, `hash_entries`, `collections_grouped_by_size`) are the stable, version-independent names — confirm against your installed MAT's query browser if a menu label looks different.

> MAT's Collections queries turn a suspect collection class into a specific diagnosis — fill ratio for over-allocation, collision ratio for hashing pathology — instead of leaving you to eyeball the object graph by hand.

## 3.17.4 Diagnosing a bad `hashCode` from a heap dump `[X-REF: contracts/02]`

**Mental model.** Picture a `HashMap<Key, V>` with ten thousand entries that should be spread across an eight-thousand-slot table, but every `Key` returns the same `hashCode()` — MAT's dominator tree shows one giant `Node` chain hanging off a single bucket, ninety-nine buckets sitting empty, and every `get`/`put` degrading toward the O(n) worst case documented for the `hashCode`/`equals` contract in `../contracts/02-equals-hashcode-contract.md`.

**Why it exists.** This diagnosis exists because the fix and the fix for 3.17.5 look identical from the outside (a map "using too much memory" or "running too slowly") but require opposite remedies — resizing the table does nothing for a collision pathology, because every extra bucket the resize creates is still empty; the entries are all colliding into the same one regardless of table size.

**When to reach for it, and when not.** Reach for it once `map_collision_ratio` on the suspect map is near 1.0. Do not reach for it on a `LinkedHashMap`/`TreeMap` symptom — collision ratio is meaningless for a tree-backed map (`TreeMap`) and only marginally relevant for `LinkedHashMap`'s access-order bookkeeping, which is a separate cost axis from hashing.

**How it works.** A `map_collision_ratio` near 1 means almost every `Node` shares its bucket with at least one other `Node`, which happens when (a) the `hashCode()` implementation returns a constant or a value with poor bit distribution (e.g. hashing only a mutable prefix field that is the same across most instances), or (b) a correct hash is being truncated by a bad custom `hash()` override that discards entropy before the table's `(n - 1) & hash` masking step. Confirm by running MAT's `Hash Entries` query on the suspect map and eyeballing whether the printed `hashCode()` values (not just object identities) repeat.

**Example.** The fix is almost always in the `hashCode()` implementation, not the map:

```java
// Before: every Order with the same customerId hashes identically,
// regardless of orderId — a customer with many orders collapses into one bucket.
public final class Order {
    private final String customerId;
    private final String orderId;

    @Override
    public int hashCode() {
        return customerId.hashCode();
    }
}

// After: combine both identity-bearing fields so distinct orders spread across buckets.
public final class Order {
    private final String customerId;
    private final String orderId;

    @Override
    public int hashCode() {
        return java.util.Objects.hash(customerId, orderId);
    }
}
```

**Gotcha:** a mutable field used in `hashCode()` is a second, worse bug hiding behind the first — even after the collision is fixed, mutating that field after insertion moves the entry's ideal bucket without moving the `Node` itself, silently breaking future lookups. `../contracts/02-equals-hashcode-contract.md` covers this immutability requirement in full; this file only diagnoses the collision symptom.

> A `map_collision_ratio` near 1 diagnoses a `hashCode()` that fails to spread keys across buckets, and the fix lives in the key type's `hashCode()`, never in the map's capacity.

## 3.17.5 Diagnosing `ArrayList` over-allocation `[X-REF: array-list/01]`

**Mental model.** Picture the opposite shape: a service builds a `new ArrayList<>(10_000)` per request "to be safe," fills it with a typical 20 elements, and never trims it — `collection_fill_ratio` on that class sits around 0.002, and MAT's histogram shows thousands of `Object[]` instances each carrying 9,980 empty slots that will never be filled, each slot a live 4- or 8-byte reference cell.

**Why it exists.** This is the mirror image of 3.17.4: the map-collision symptom is entries piled into too few buckets; the list-over-allocation symptom is capacity spread across too many unused slots. Growth-factor arithmetic in `../array-list/01-internals-a-growth.md` explains the amortized-growth reasoning that makes a *reasonable* initial capacity guess a legitimate optimization — this leaf is about catching the case where that guess was wrong by two or three orders of magnitude.

**When to reach for it, and when not.** Reach for it once `collection_fill_ratio` is persistently low across many instances of the same call site — a single low-fill instance mid-fill (captured while a loop is still appending) is normal and not a bug; the pathology is a low ratio that holds true across the class's entire population in the dump.

**How it works.** Cross-reference the dump against the call site: MAT's **Path to GC Roots** on a sample low-fill instance leads back through field references to the constructing method, or a JFR/async-profiler allocation trace (3.17.11–3.17.12) names the call site directly without needing a dump at all. Once the call site is known, the fix is to size the initial capacity to the true expected count, or drop the explicit capacity argument entirely and let the default growth sequence documented in `../array-list/01-internals-a-growth.md` handle it — default growth's amortized-doubling cost is almost always cheaper than a habitually oversized guess multiplied across every request.

**Example.**

```java
// Before: "just in case" capacity, paid on every request regardless of actual size.
List<OrderLine> lines = new ArrayList<>(10_000);

// After: size to the real expectation (here, a bounded page size), or omit entirely.
List<OrderLine> lines = new ArrayList<>(expectedLineCount);
```

**Gotcha:** `ArrayList.trimToSize()` exists to reclaim this after the fact, but calling it on a list that will grow again immediately just re-triggers a full backing-array copy on the next `add` — it is a one-shot cleanup for lists that are done growing (e.g. before caching a built list long-term), not a habit to sprinkle after every fill loop.

> `collection_fill_ratio` persistently near zero across many instances of the same class diagnoses over-allocated capacity, and the fix is at the call site that chose the capacity, not in the collection implementation.

## 3.17.2 / 3.17.6 Finding the culprit without opening MAT first

**Mechanism.** Before committing to a full heap dump, `jcmd <pid> GC.class_histogram` gives a live, in-process count of instances per class, sorted by total size, with no file written and a far shorter pause than a full dump:

```bash
jcmd 12345 GC.class_histogram | head -20
```

The output's `instances` and `bytes` columns for `java.util.HashMap$Node` or `[Ljava.util.HashMap$Node;` (the bucket array) tell you whether a map-shaped problem is worth a full dump at all — a modest count rules it out cheaply; a count in the millions justifies paying for the dump and MAT session in 3.17.1.

**Gotcha:** `GC.class_histogram` counts instances reachable *right now*, including garbage not yet collected on a young generation that hasn't run — a spike immediately after a burst of short-lived allocation can look like a leak for a few seconds until the next minor GC clears it; run it twice a GC cycle apart before trusting the number.

> `jcmd GC.class_histogram` is the cheap, dump-free first check that tells you whether a full heap dump is warranted before you pay its stop-the-world cost.

## 3.17.7 Reading a collection in a debugger

**Mechanism.** IntelliJ's debugger renders an `ArrayList` breakpoint variable with a "View as: Object[]" toggle that exposes the raw `elementData` backing array, including the trailing `null` slots beyond `size` — this is the one place you can visually confirm capacity versus size without any tooling beyond the IDE, because the debugger shows `size` (the field) and the array's own `.length` (the capacity) as two separate values in the same watch pane.

**Gotcha:** the default "collection view" (showing only the logical elements 0..size-1) hides exactly the over-allocation symptom from 3.17.5 — you have to explicitly switch to the raw array view to see the unused tail; the friendly default view is the wrong view for a capacity investigation.

> A debugger's raw-array view of a list's backing store separates capacity from size in a way the default collection-friendly view intentionally hides.

## 3.17.8 Watching `modCount` in a debugger to find a CME source

**Mechanism.** Set a watch on the private `modCount` field (inherited from `AbstractList`/`AbstractMap`) and step through the suspect code; every structural mutation — `add`, `remove`, `clear`, but not `set` — increments it, and the field's value at the moment an iterator's `checkForComodification()` throws tells you it no longer matches the `expectedModCount` the iterator captured at construction, which is the fail-fast mechanism itself, not a separate bug.

**Gotcha:** `modCount` is `protected`/package-private and unnamed in the public API, so IDE auto-complete on a watch expression will not surface it by name unless you type it directly — `((java.util.ArrayList<?>) list).modCount` via a cast expression in the watch pane, since it is not accessible through the interface type.

> Watching `modCount` directly turns "why did this throw `ConcurrentModificationException`" into "here is the exact line that mutated the collection out from under the iterator."

## 3.17.9 The debugger's own `toString` evaluation causing the CME `[TRAP]` `[X-REF: iteration/02]`

**Mental model.** You set a breakpoint inside a loop that's mutating a shared `List`, hit it, and the instant the debugger's variables pane renders the list's value — which means calling `toString()`, which internally iterates — a second thread concurrently mutates the same list, and the debugger's own background `toString()` evaluation throws `ConcurrentModificationException` right there in the watch pane, even though your own code hasn't reached the line that would have thrown it.

**Why it exists.** IntelliJ (and most JVM debuggers) auto-evaluate `toString()` on every object shown in the Variables/Watches pane so you see `[a, b, c]` instead of a bare object reference — this is a convenience feature, and it runs on a background thread the moment the breakpoint suspends, which means it iterates the collection exactly like any other reader would, with exactly the same fail-fast exposure documented for concurrent structural modification in `../iteration/02-fail-fast-fail-safe.md` (leaf 2.2.16 covers the underlying `modCount` mechanics from the iteration side; this leaf is the debugger-specific manifestation of that same trap).

**When to reach for it, and when not.** Recognize this the moment a CME's stack trace bottoms out inside a debugger-internal rendering call (a `com.intellij.debugger` internal frame, or your IDE's equivalent) rather than inside your own code — that is the signature that the debugger caused the exception you were trying to observe, not your code.

**How it works.** Disable automatic `toString` invocation: in IntelliJ, **Settings → Build, Execution, Deployment → Debugger → Data Views**, uncheck **"Enable 'toString()' object view"** (or scope it per-type via **"toString()" object renderers**), which stops the background evaluation from touching the collection at all while it is suspended; you can still manually invoke `toString()` on demand once you know it is safe.

**Example.** The failure looks like this in the debugger's own evaluation log, not your application log:

```
Method threw 'java.util.ConcurrentModificationException' exception.
    at java.base/java.util.ArrayList$Itr.checkForComodification(ArrayList.java:1013)
    at java.base/java.util.ArrayList$Itr.next(ArrayList.java:967)
    at java.base/java.util.AbstractCollection.toString(AbstractCollection.java:465)
    // the frame above is the debugger's rendering call, not application code
```

**Gotcha:** turning the renderer off blinds you to every other object's friendly display too, not just the mutating collection's — the targeted fix is a per-type renderer exclusion for the specific mutable-shared-state class, not a blanket global toggle, if the IDE version's settings expose that granularity.

> The debugger's convenience `toString()` rendering is itself a concurrent reader of the collection it is displaying, and disabling automatic `toString()` evaluation is the fix, not a workaround for a bug in your code.

## 3.17.10 JOL for live object-size inspection `[X-REF: cost-and-memory/03]`

**Mechanism.** `org.openjdk.jol:jol-core`'s `ClassLayout.parseInstance(obj).toPrintable()` prints the actual field offsets, padding, and total shallow size of a live object, which is the empirical check against the byte arithmetic worked out from header/reference-width tables in `../cost-and-memory/02-internals-memory-headers.md` and applied to whole collections in `03-internals-memory-collections.md`.

**Gotcha:** JOL reports *shallow* size by default (`ClassLayout`, one object) — for a collection's true footprint you need `GraphLayout.parseInstance(obj).totalSize()`, which walks the referenced graph (backing array, `Node`s, boxed values); using the shallow variant on a `HashMap` reports only the map object's own few fields, not the multi-kilobyte structure it points to, and looks deceptively small.

> JOL turns the header-and-alignment arithmetic from earlier files into a live, verifiable number pulled straight from the running JVM instead of a hand-computed estimate.

## 3.17.11 JFR allocation profiling with `ObjectAllocationSample` `[X-REF 06]`

**Mental model.** A JFR recording running continuously in production, sampling allocations rather than dumping the heap, can answer "which call site is allocating all these `HashMap$Node` instances" without ever pausing the world for more than the sub-millisecond cost of a sample.

**Why it exists.** A heap dump tells you what is alive right now and who retains it; it does not tell you *who allocated it* — for a leak whose cause is a hot allocation site rather than a retention bug (e.g. correctly-short-lived objects being allocated at an unsustainable rate, churning the young generation), allocation profiling is the right tool and a heap dump is the wrong one.

**When to reach for it, and when not.** Reach for it as the low-overhead, always-safe-to-run-in-production first step whenever a Micrometer gauge (3.17.13) shows unexplained growth — it is cheap enough to leave attached to a live service for minutes without operational risk, unlike a heap dump. Skip it if you already know the retaining field from a prior dump and only need the collision/fill-ratio diagnosis, which is MAT's job, not JFR's.

**How it works.** JDK 16+ (and backported to 11u) ships `jdk.ObjectAllocationSample`, a low-overhead sampling event that supersedes the older `jdk.ObjectAllocationInTLAB`/`jdk.ObjectAllocationOutsideTLAB` pair used on JDK 8–15 — check which event names your JDK emits before writing a query, since the event name is the version-sensitive detail here. Start, run, and dump a recording targeting only allocation profiling:

```bash
# Start a time-bounded recording focused on allocation profiling
jcmd 12345 JFR.start name=allocdump settings=profile duration=120s filename=/tmp/alloc.jfr

# let it run for the configured duration, then confirm/stop if it hasn't auto-stopped
jcmd 12345 JFR.dump name=allocdump filename=/tmp/alloc.jfr

# Print just the allocation-sample events with their stack traces
jfr print --events jdk.ObjectAllocationSample /tmp/alloc.jfr
```

The printed events include the allocated class (`java.util.HashMap$Node` or `[Ljava.util.HashMap$Node;`) and a full stack trace at the sampled allocation, which is the call site 3.17.5's over-allocation diagnosis needs when a heap dump alone only shows the *result*, not the *cause*.

**Gotcha:** `settings=profile` samples more aggressively (and costs more) than `settings=default`; `default` targets roughly 1% overhead and is safe to leave on indefinitely in production, while `profile` is meant for a bounded, deliberate diagnostic window like the 120-second recording above, not a permanent attachment.

> `jdk.ObjectAllocationSample` (JDK 16+) attributes hot allocation of a specific collection-internal class to an exact call site and stack trace, at a cost low enough to run continuously in production.

## 3.17.12 async-profiler `-e alloc` for the same job, out-of-process `[X-REF 06]`

**Mental model.** Where JFR requires the target JVM to have flight recording enabled and a `.jfr` file pipeline, async-profiler attaches to a running process by PID from the outside and produces the same allocation-attribution answer, which matters when you don't control the JVM's startup flags or want a portable diagnostic tool independent of JFR's configuration.

**Why it exists.** async-profiler predates JFR's allocation-sampling maturity and remains popular because it produces flame graphs directly and can attach without any special startup configuration on the target — it is a common choice in environments where JFR is locked down or the team's tooling is already built around async-profiler's output format.

**When to reach for it, and when not.** Reach for it when you need to attach to a process you didn't start with JFR-friendly flags, or want a flame graph rather than a raw event stream. Prefer JFR when the target already runs with continuous recording enabled, since starting a second profiler doubles the sampling overhead for no extra information.

**How it works.** async-profiler's allocation-profiling event flag is `-e alloc` in current releases (2.9+); older releases (pre-2.0) used the now-removed `--alloc` long-flag form — confirm your installed version's flag with `asprof list` if the command below errors, since this is exactly the kind of detail that silently breaks across a version bump.

```bash
# Attach to pid 12345, profile allocations for 60 seconds, write a collapsed flame graph
./profiler.sh -e alloc -d 60 -f /tmp/alloc-flamegraph.html 12345
```

**Gotcha:** async-profiler's allocation event samples by allocated *bytes*, not by allocation *count*, above a per-thread sampling interval (`-i`) — a call site that allocates many small, cheap objects can under-report relative to one allocating fewer, larger objects, which matters when hunting a `HashMap$Node`-sized leak rather than a large-array one; adjust `-i` down if small-object allocation is the suspect.

> async-profiler `-e alloc` (current versions; `--alloc` on releases before 2.0) attributes allocation to call sites from outside the target process, without requiring the target to have been started with JFR enabled.

## 3.17.13 Micrometer gauges as the always-on guard `[X-REF 20]`

**Mental model.** Every tool above this line is something you run *after* you already suspect a problem; a Micrometer gauge on a cache's or collection's size is the one thing running *before* you suspect anything, turning "the service OOM'd" into "the dashboard showed this cache climbing linearly for six hours before anyone looked."

**Why it exists.** Heap dumps, JFR sessions, and debugger breakpoints are all reactive — they require a human to decide something is wrong first. A gauge scraped on a normal metrics interval (typically 10–60s) costs one `size()` call per scrape, which is O(1) for `ArrayList`/`HashMap`/`ConcurrentHashMap` and therefore free at any reasonable scrape cadence, and it converts an invisible slow leak into a visible, alertable trend line.

**When to reach for it, and when not.** Put one on every long-lived cache, queue, or map with unbounded lifetime by default, as a matter of course — this is not an optional diagnostic step, it is the baseline hygiene that makes the reactive tools unnecessary in the common case. Skip it only for genuinely request-scoped collections that cannot outlive a single request/response cycle, where "growth" has no meaning.

**How it works.** `Gauge.builder` registers a weak reference to the target object plus a size-extracting function, so the gauge does not itself keep the collection alive past its natural lifetime:

```java
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public final class SessionCache {
    private final Map<String, Object> sessions = new ConcurrentHashMap<>();

    public SessionCache(MeterRegistry registry) {
        Gauge.builder("cache.sessions.size", sessions, Map::size)
                .description("Live entry count in the in-memory session cache")
                .tag("cache", "sessions")
                .register(registry);
    }
}
```

**Gotcha:** `Gauge.builder(name, stateObject, valueFunction)` holds only a weak reference to `stateObject` by design — if nothing else in the application holds a strong reference to `sessions` (unlikely for a field like this one, but easy to get wrong for a locally-scoped object passed only to the gauge), the gauge silently stops reporting once the object is collected, with no error raised.

> A Micrometer gauge over a collection's `size()` is the free, always-on tripwire that should turn an unbounded-growth bug into a dashboard trend line long before it becomes a heap dump.

## 3.17.14 `-XX:+PrintFlagsFinal` before trusting any byte arithmetic `[X-REF 06]`

**Mechanism.** Every byte-count claim in `../cost-and-memory/02-internals-memory-headers.md` (header size, reference width, alignment quantum) is conditional on specific JVM flag values, and the only reliable way to know what those flags actually resolve to on a given deployment — as opposed to what the defaults are documented to be — is to ask the running JVM directly:

```bash
java -XX:+PrintFlagsFinal -version | grep -E "UseCompressedOops|UseCompressedClassPointers|ObjectAlignmentInBytes|UseCompactObjectHeaders"
```

**Gotcha:** `UseCompressedOops` auto-disables once the max heap crosses roughly the 32 GB boundary (the exact cliff depends on alignment settings, per `../cost-and-memory/02-internals-memory-headers.md`), silently doubling every reference-holding field's cost — a team that hand-computed byte arithmetic assuming compressed oops, then later raised `-Xmx` past the cliff without re-checking flags, will see every downstream number quietly stop matching reality.

> `-XX:+PrintFlagsFinal` is the single command that turns "the defaults should be X" into "this specific JVM instance is actually running with Y," and every byte-arithmetic claim in this note set depends on checking it rather than assuming it.

## 3.17.15 Static-analysis and runtime guards `[RESEARCH]` `[X-REF: utilities/01]`

**Mechanism.** Three complementary, cheap guards catch collection misuse before it reaches production: `Collections.checkedList` (and its `checkedMap`/`checkedSet`/`checkedCollection` siblings) wraps a collection with a runtime type check on every insertion, converting a raw-type pollution bug into an immediate `ClassCastException` at the point of insertion rather than a confusing one at the point of a later, unrelated read; `-ea` (enable assertions) turns `assert` statements checking collection invariants (non-null elements, expected size bounds) from silently-skipped no-ops into active runtime checks in test/staging environments; and Error Prone's `CollectionIncompatibleType` check flags calls like `list.contains(wrongTypeArg)` or `map.get(wrongTypeKey)` at compile time, since those calls compile and silently return `false`/`null` rather than failing, precisely the raw-type-adjacent trap `checkedList` catches at runtime instead.

```java
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@SuppressWarnings("rawtypes")
List raw = new ArrayList();
List<String> guarded = Collections.checkedList(new ArrayList<>(), String.class);
raw.add(42);            // compiles silently on the raw list, corrupts it for later readers
guarded.add("ok");       // fine
// guarded.addAll(raw); // throws ClassCastException immediately, naming the offending element
```

**Gotcha:** `Collections.checkedList` only guards insertions made *through the wrapper reference* — if the same backing `ArrayList` is also reachable and mutated through an unwrapped raw-typed reference (as `raw` inserted into `guarded.addAll(raw)` demonstrates only at the `addAll` boundary, not for direct mutation of a separately-held raw reference to the same list), the check never fires for that other path; it is a boundary guard, not a runtime type parameter on the object itself.

**Unverified:** Error Prone's exact bug-pattern identifier is `CollectionIncompatibleType` in current releases (confirmed present in Error Prone's bug-pattern catalog); if your team's Error Prone version predates it or has it disabled by default in a custom `-Xep` configuration, verify with `-XepAllErrorsAsWarnings` or the project's Error Prone config before relying on it as a safety net.

> `Collections.checkedList`, `-ea` assertions, and Error Prone's `CollectionIncompatibleType` are three independent, cheap layers that catch raw-type and type-incompatible collection misuse at the earliest point each is capable of catching it — insertion, runtime invariant, and compile time respectively.

## Pitfalls

### "A heap dump is basically free, just take one to check"

**Wrong**

```bash
# Taken speculatively on a fully loaded production instance, "just to see"
jmap -dump:live,format=b,file=/tmp/heap.hprof 12345
# Result: multi-second STW pause on the one instance serving live traffic,
# a 6 GB file, and a spike in p99 latency that pages someone else
```

**Right**

```bash
# Check first, cheaply, with no pause-worthy cost
jcmd 12345 GC.class_histogram | head -20
# Only escalate to a full dump against a cordoned/drained instance
# once the histogram or a Micrometer trend justifies it
```

**Why people believe it:** `jcmd`/`jmap` are single, quick-to-type commands with no obvious warning in their help text about pause duration, so they look as cheap as any other one-line diagnostic command.

### "The collision-ratio and fill-ratio bugs have the same fix — just resize the map"

**Wrong**

```java
// Map has map_collision_ratio near 1.0 (bad hashCode), "fixed" by growing the table
Map<Order, Status> orders = new HashMap<>(1 << 20);
// Result: table is bigger, but every Order still collides into the same bucket —
// lookup is still effectively O(n)
```

**Right**

```java
// Fix the hashCode() itself, as in 3.17.4 — the table size was never the problem
@Override
public int hashCode() {
    return java.util.Objects.hash(customerId, orderId);
}
```

**Why people believe it:** both symptoms present identically from the outside as "this map is slow/big," and resizing is the first lever most engineers reach for on any map-shaped performance problem.

### "IntelliJ threw a ConcurrentModificationException, so my code has a bug"

**Wrong**

```
// Stack trace bottoms out in AbstractCollection.toString, not your code —
// treating this as an application bug and adding synchronization in the wrong place
```

**Right**

```
Settings → Build, Execution, Deployment → Debugger → Data Views
→ uncheck "Enable 'toString()' object view"
// Re-run; if the CME disappears, it was the debugger's own rendering, not your code
```

**Why people believe it:** the exception type, message, and general shape are identical to a real application-level CME, and the debugger frame at the bottom of the trace is easy to skim past.

## Cheat sheet

| Task | Command |
|---|---|
| Heap dump (attach API) | `jcmd <pid> GC.heap_dump /tmp/heap.hprof` |
| Heap dump (force full GC first) | `jmap -dump:live,format=b,file=/tmp/heap.hprof <pid>` |
| Quick live class counts | `jcmd <pid> GC.class_histogram` |
| MAT: retention view | Dominator Tree, sort by Retained Heap |
| MAT: over-allocation | `collection_fill_ratio`, `array_fill_ratio` |
| MAT: bad hashCode | `map_collision_ratio` near 1.0 |
| MAT: enumerate entries | `hash_entries` |
| MAT: group by size | `collections_grouped_by_size` |
| MAT: ad hoc query | OQL console, e.g. `SELECT * FROM java.util.HashMap$Node WHERE this.@retainedHeapSize > 1000000` |
| JOL: shallow size | `ClassLayout.parseInstance(obj).toPrintable()` |
| JOL: deep/graph size | `GraphLayout.parseInstance(obj).totalSize()` |
| JFR: start allocation recording | `jcmd <pid> JFR.start name=allocdump settings=profile duration=120s filename=/tmp/alloc.jfr` |
| JFR: print allocation events | `jfr print --events jdk.ObjectAllocationSample /tmp/alloc.jfr` |
| async-profiler: allocation flame graph | `./profiler.sh -e alloc -d 60 -f /tmp/alloc-flamegraph.html <pid>` |
| Verify JVM memory flags | `java -XX:+PrintFlagsFinal -version \| grep -E "UseCompressedOops\|ObjectAlignmentInBytes"` |
| Type-safety guard | `Collections.checkedList(new ArrayList<>(), String.class)` |
| Metrics guard | `Gauge.builder("cache.size", map, Map::size).register(registry)` |

## Self-test

**Q1.** Why does `jcmd <pid> GC.class_histogram` come before `jcmd <pid> GC.heap_dump` in a leak-hunting sequence?

<details><summary>Answer</summary>

`GC.class_histogram` gives a live instance/byte count with a much shorter pause and no file written, letting you confirm a collection-shaped problem is real before paying the cost of a full heap dump (seconds of STW, a file often larger than the live heap set). It is the cheap gate in front of the expensive tool.

</details>

**Q2.** A `HashMap` shows `map_collision_ratio` near 1.0 in MAT. What is the fix, and why doesn't resizing the map's initial capacity help?

<details><summary>Answer</summary>

Fix the key type's `hashCode()` implementation so it spreads keys across buckets (e.g. combine all identity-bearing fields with `Objects.hash(Object[])`). Resizing does not help because the entries are all colliding into the same bucket(s) regardless of table size — a bigger table just creates more empty buckets alongside the same one overloaded bucket; it does not change which bucket any given key maps to relative to the others.

</details>

**Q3.** What does `collection_fill_ratio` near 0 across many `ArrayList` instances of the same class indicate, and where do you look to fix it?

<details><summary>Answer</summary>

It indicates systematic over-allocation — the lists' backing arrays are sized far larger than the elements actually stored. Fix it at the call site that chose the initial capacity (via `Path to GC Roots` in MAT, or an allocation-profiling trace from JFR/async-profiler), sizing it to the real expected element count or omitting the explicit capacity and relying on default growth.

</details>

**Q4.** You set a breakpoint inside code mutating a shared `ArrayList` from another thread, and the debugger throws a `ConcurrentModificationException` before your breakpoint's own line executes. What is happening, and what is the fix?

<details><summary>Answer</summary>

The debugger's variables/watches pane is auto-evaluating `toString()` on the list to display its value, and that `toString()` call iterates the list — triggering the same fail-fast `modCount` check a real reader would, against a list another thread is concurrently mutating. Fix it by disabling automatic `toString()` evaluation (IntelliJ: Settings → Build, Execution, Deployment → Debugger → Data Views → uncheck "Enable 'toString()' object view").

</details>

**Q5.** Why is JOL's `ClassLayout.parseInstance` insufficient for measuring a `HashMap`'s true memory footprint, and what should you use instead?

<details><summary>Answer</summary>

`ClassLayout.parseInstance` reports only the shallow size of the map object itself — its own few fields — not the backing bucket array, `Node` instances, or boxed keys/values it references. Use `GraphLayout.parseInstance(obj).totalSize()` instead, which walks the full referenced object graph.

</details>

**Q6.** Name the JFR event used for allocation profiling on JDK 21, and the two older event names it replaced.

<details><summary>Answer</summary>

`jdk.ObjectAllocationSample` (available JDK 16+, low-overhead sampling). It replaced the older `jdk.ObjectAllocationInTLAB` and `jdk.ObjectAllocationOutsideTLAB` events used on JDK 8–15.

</details>

**Q7.** What is async-profiler's current flag for allocation profiling, and what changed from older versions?

<details><summary>Answer</summary>

`-e alloc` in current (2.9+) releases. Releases before 2.0 used a `--alloc` long-flag form that has since been removed; check `asprof list` against your installed version before relying on either form.

</details>

**Q8.** Why should a Micrometer gauge on a cache's size use `Gauge.builder(name, stateObject, valueFunction)` rather than computing and pushing the value directly, and what is the corresponding gotcha?

<details><summary>Answer</summary>

`Gauge.builder` holds only a weak reference to `stateObject`, so registering the gauge does not itself keep the collection alive past its natural lifetime — the gauge observes, it does not pin memory. The gotcha is the flip side: if nothing else holds a strong reference to the collection, it can be collected and the gauge will silently stop reporting with no error.

</details>

**Q9.** What is the difference in what `Collections.checkedList` catches versus what Error Prone's `CollectionIncompatibleType` catches, and when does each one fire?

<details><summary>Answer</summary>

`Collections.checkedList` is a runtime guard — it throws `ClassCastException` immediately when an incompatible element is inserted through the wrapper reference, catching raw-type pollution at insertion time in a running program. `CollectionIncompatibleType` is a compile-time static-analysis check that flags calls like `list.contains(wrongType)` or `map.get(wrongTypeKey)` that would otherwise compile silently and just return `false`/`null`. One fires at build time, the other at insertion time; using both covers a mistake either misses alone.

</details>

**Q10.** Before trusting a byte-arithmetic estimate for object header size on a specific production JVM, what command should you run, and what is the one flag most likely to invalidate the estimate silently?

<details><summary>Answer</summary>

Run `java -XX:+PrintFlagsFinal -version` and check the actual resolved values, especially `UseCompressedOops`. It auto-disables once the max heap crosses roughly the 32 GB boundary (exact cliff depends on alignment), silently doubling every reference-holding field's cost relative to an estimate that assumed compressed oops were active.

</details>

---

**Leaves covered:** 3.17.1–3.17.15 (15 leaves)
**Leaves deferred:** none
**Diagrams included:** D-142
**Target version:** Java 21 LTS
**Lines:** 502
