# 05 Multithreading and Concurrency — Interview questions: collections and executors — INTERVIEW (§5.1, questions 5.1.61–5.1.76)

**Target version: Java 21 LTS.** | **Part 5 of 5** | [Index](00-index.md)
Previous: [Interview questions: locks and atomics II](94b2-interview-questions-locks-and-atomics-ii.md) · Next: [Interview questions: collections and executors II](94c2-interview-questions-collections-and-executors-ii.md)

---

### 5.1.61 How does `ConcurrentHashMap` achieve concurrency in Java 8+, and what changed from Java 7?

Java 7's `ConcurrentHashMap` was sharded into a fixed array of `Segment`s, each its own `ReentrantLock`-guarded hash table — you picked concurrency level up front (default 16 segments) and paid a full segment lock for any write inside it, plus the segment count could never shrink or grow once the map was constructed.
Java 8 threw that design away entirely.
It's now a single flat `Node<K,V>[] table`, and the lock granularity dropped from "a sixteenth of the map" to **per-bin**: a write takes a `synchronized` block on the first node of the specific bin it's writing into (a bin lock, not a table lock), so two writes to different bins never contend at all, no matter how many bins the map has.
Reads take no lock whatsoever — `table`, `Node.val` and `Node.next` are all declared `volatile`, so a reader always observes a fully-published node or `null`, never a half-constructed one, because a `Node`'s fields are all set before the volatile publish that makes it reachable.
Structural moves — specifically, creating the very first node in a bin that was previously empty — go through a CAS on the array slot instead of taking any lock at all, so the common case of `putIfAbsent` racing into an empty bin never synchronizes on anything.
Concretely: for `ConcurrentHashMap<ClientId, ClientRestrictions>` sized for 2.4M clients, two threads updating restrictions for two different clients whose ids hash into different bins run fully in parallel — no shared lock exists between them, and the only serialization point in the whole system is the rare case of two writers landing in the very same bin at the same instant.

In JDK source terms the write path calls `tabAt(tab, i)` to read a bin head via `Unsafe`/`VarHandle` volatile get, and `casTabAt(tab, i, null, newNode)` to install the first node of an empty bin without ever entering a `synchronized` block at all.
Only once `tabAt` returns a non-null head does the code fall into `synchronized(f) { ... }` to walk or extend the existing chain.
This two-tier read-cheap, lock-only-when-populated design is why the per-bin story is stronger than "one lock per bin" — an untouched bin costs nothing until the moment it first receives a write.

**Follow-up:**

"So what's actually synchronized on?" — the first `Node` object in the target bin (`synchronized(f) { … }` where `f` is the bin's head), which is why an empty bin never needs a lock at all — the CAS on the array slot handles bin creation, and the `synchronized` block only exists once there's an actual node object to lock on.

**Insight:**

The concurrency isn't a knob you set anymore — Java 7's `concurrencyLevel` constructor argument is still accepted for source compatibility but is no longer treated as a lock-stripe count; on Java 8+ it only hints the initial table capacity, so passing `concurrencyLevel = 64` today changes nothing about how many locks exist.

**Interview:**

This is the single most commonly asked `ConcurrentHashMap` question, and interviewers are specifically listening for "per-bin lock, not table lock" and "reads are lock-free via volatile fields" — an answer that only says "it's thread-safe" without naming the locking granularity reads as memorized rather than understood.

### 5.1.62 Why does `ConcurrentHashMap` forbid null keys and values?

Because in a concurrent map, `get(k) == null` is genuinely ambiguous between "no mapping exists for `k`" and "the mapping exists and its value happens to be null" — and the standard way to disambiguate on a single-threaded `HashMap` is `containsKey(k)` followed by `get(k)`, which is itself a check-then-act race the instant another thread is allowed to mutate the map between your two calls.
Doug Lea's own rationale, carried into the javadoc, is that permitting null in a concurrent map would let that ambiguity look completely correct under single-threaded testing and then fail intermittently in production the moment concurrent writers show up — exactly the class of bug that survives code review and only surfaces as a flaky production incident.
`HashMap` accepts one null key and any number of null values precisely because single-threaded code *can* safely serialize `containsKey` and `get` without a race; `ConcurrentHashMap` can never make that safety promise to a caller, so it refuses the ambiguity outright at the API boundary instead of letting it become a runtime race — `map.put(clientId, null)` throws `NullPointerException` immediately, at the call site, not three call sites downstream.

The same restriction surfaces indirectly through `Collectors.toConcurrentMap`, which is documented to reject a `null` result from either the key or value mapper for exactly this reason — it is building a `ConcurrentHashMap` under the hood, and inherits its null intolerance automatically rather than adding a separate check.

**Follow-up:**

"What do you do instead of a null value?" — model absence explicitly: use `Optional<ClientRestrictions>` as the value type, use a sentinel constant like `ClientRestrictions.NONE`, or simply omit the key entirely and treat `containsKey` returning `false` (or `get` returning `null`, now unambiguous) as "no restriction record."

**Pitfall:**

Porting a `HashMap`-based cache to `ConcurrentHashMap` for thread safety and hitting an unexpected `NullPointerException` on a legitimate null placeholder value that used to work fine — the fix is never "wrap it in some null-tolerant map variant," it's redesigning the value type so null was never meaningful application data in the first place; treating the `NPE` as a signal to fix the modeling, not to route around the map.

**Interview:**

Interviewers use this to check whether a candidate actually internalizes the check-then-act race class, not just the surface fact "nulls throw NPE" — be ready to explain *why* in terms of the containsKey/get race, not just recite the behavior.

**Insight:**

The same design choice shows up in `ConcurrentSkipListMap` and every other `java.util.concurrent` map implementation — null-hostility is a topic-wide convention, not a `ConcurrentHashMap`-specific quirk, precisely because the check-then-act ambiguity applies identically to any concurrent map.

### 5.1.63 Is `size()` on a `ConcurrentHashMap` accurate?

No, and by design it isn't meant to be.
`size()` returns an `int` computed by summing a striped array of `CounterCell` objects plus a `baseCount` field, and it does this without ever pausing other threads' concurrent inserts and removals — by the time the summation finishes and the method returns a value to the caller, the map has very likely already changed again on some other thread.
On a map backing 2.8M-per-day stake reservations under genuinely concurrent writers, `size()` gives you a snapshot of a number that is already stale the instant it's returned — perfectly fine for "roughly how big is this map right now" (a metrics dashboard, a log line), never sound as the basis for a correctness decision like "we're at capacity, deny the next insert," because two threads could both read the same stale count and both decide there's room.
For the 64-bit-safe equivalent with the identical best-effort-estimate semantics (not exactness — just no silent `int` overflow on a genuinely enormous map), call `mappingCount()`, added specifically because `size()` predates `long`-scale counting and can't change its declared return type without breaking every existing caller's contract with the `Map` interface.

Contrast this with plain `HashMap.size()`, which is exact precisely because a single-threaded caller is the only writer and reader in play — there is no concurrent mutation to race against, so summing a maintained field or counting entries directly gives a correct answer with no estimation involved.

**Follow-up:**

"So how do you get an exact size?" — you fundamentally don't, not without external synchronization that locks out every writer for the duration of the count (which defeats the entire point of using a lock-striped concurrent map), or by maintaining your own dedicated atomic counter incremented and decremented alongside every put/remove path in application code.

**Pitfall:**

Using `map.size() == 0` as a "safe to shut down now" gate for a background sweep or drain loop — under concurrent writers this boolean can flip true and false several times within a single millisecond, so a check-then-shutdown built on it races; use an explicit quiescence signal instead, such as a `Phaser`, a shutdown flag checked and honored *before* every insert, or draining a bounded queue to empty with no producers left registered.

**Interview:**

This question is a favorite because the intuitive answer ("yes, `size()` gives you the count") is wrong for any concurrent map, and interviewers use the follow-up about `mappingCount()` to separate candidates who've actually read the javadoc from those who've only used the class casually.

### 5.1.64 Why is `containsKey`-then-`put` still a race on a concurrent map?

Because `ConcurrentHashMap` guarantees that each *individual* operation is atomic and internally consistent, but it makes zero guarantee about anything spanning two separate method calls — nothing in the map's contract stops another thread from inserting a key between your `containsKey` call returning `false` and your subsequent `put` call actually executing.
Two threads can both observe "absent" for the same `ClientId`, both decide independently to insert a fresh `ClientRestrictions` record, and the second `put` silently overwrites the first thread's write with no error, no warning, and no way for either thread to know it happened.
The map being "thread-safe" only ever meant *no internal corruption* — no lost bins, no torn `Node` objects, no infinite loop during resize — it says absolutely nothing about compound application logic assembled out of two calls glued together in your own code, because the map has no way to know those two calls are logically related.
The fix is to never compose two calls where an atomic single-call equivalent already exists: `putIfAbsent(clientId, restrictions)` performs the check-and-insert as one operation under the bin lock, so the losing caller in a race simply gets back the winner's already-installed value instead of overwriting it.

The same shape recurs with `remove`-then-`put` and with `get`-then-conditional-`put` — any two-call sequence that reads state and then acts on that reading is a race on a concurrent structure unless the map itself offers a single atomic method that fuses the read and the write, such as `replace(key, expectedOldValue, newValue)` for the remove-then-replace case.

**Follow-up:**

"What if the value to insert is expensive to compute and should only be built on the actual losing-or-first path?" — use `computeIfAbsent(clientId, id -> buildDefaultRestrictions(id))`, which only ever invokes the supplied lambda if the key is genuinely still absent at the moment the bin lock is acquired, guaranteeing the expensive construction happens at most once per key even under a race.

**Insight:**

This is exactly the same shape of bug as an `AtomicLong` needing `compareAndSet` instead of "read the value, check it, write a new value" — atomicity is a property that belongs to one call, never a property you can retroactively bolt onto two calls just because you happened to write them next to each other.

**Interview:**

Expect this asked as a direct follow-up to "is `ConcurrentHashMap` thread-safe" — the trap is that thread-safety of the map does not imply thread-safety of arbitrary code built on top of it, and the interviewer is checking whether that distinction is automatic or has to be prompted.

### 5.1.65 What runs under the bin lock in `computeIfAbsent`, and what must it not do?

The bin lock is held for the *entire duration* of the remapping function you pass in — `computeIfAbsent`, `compute`, `merge`, and the internal lambda path `putIfAbsent` shares with them, all synchronize on the bin's first node and do not release that lock until your supplied function returns.
That means whatever code sits inside `computeIfAbsent(clientId, id -> ...)` is executing with a real lock held on that bin, so if that lambda attempts to touch the *same* `ConcurrentHashMap` again — either by calling another mapping method for a *different* key that happens to hash into the same already-locked bin, or worse, by recursively calling the identical key — the outcome is either a reentrancy failure (recent JDKs detect the same-key recursive case and throw `IllegalStateException` rather than silently deadlocking) or, for a cross-key collision into the same bin, an actual thread that blocks forever waiting on a lock it itself is holding indirectly through the call stack.
The javadoc states the rule explicitly and without qualification: the mapping function must be short, must not block, and must not attempt to update any other mapping of the same map while it's running.

The actual guard in the JDK source is a boolean `binCount` check combined with a `synchronized (f)` block wrapping the entire call to the user-supplied `Function`/`BiFunction`; nothing in that code path calls back into `tabAt`/`casTabAt` for a *different* bin while the lock is held, which is exactly why touching another bin from inside the lambda is unsupported territory rather than a documented, tested path.

**Follow-up:**

"What if the computation genuinely needs an I/O call, like fetching a `ClientRestrictions` snapshot from an external service over the network?" — never do that inside the lambda; fetch the value outside the map entirely first, then call `putIfAbsent` with the already-computed result, accepting that under a race two threads might both perform the fetch and only one of them actually wins the insert — that's a cheap, safe tradeoff compared to holding a bin lock across a network call.

**Pitfall:**

Writing `map.computeIfAbsent(k, x -> map.get(otherKey))` on the same map and assuming it's harmless because it's "only a read" — if `otherKey` happens to hash into the very bin currently locked by this call on this thread, the call deadlocks or throws instead of silently succeeding, and the bug is invisible in testing until the two keys happen to collide in production.

**Interview:**

This one separates candidates who've only read the method signature from those who've hit the reentrancy trap in practice — a strong answer volunteers the deadlock/`IllegalStateException` risk before being asked, rather than only after a direct prompt.

### 5.1.66 Fail-fast versus weakly consistent versus snapshot iterators

Three genuinely different promises for "what do you see when you iterate a collection while another thread is mutating it concurrently," and confusing them is one of the most common ways this topic gets tested.

| Style | Behavior under concurrent mutation | Example |
|---|---|---|
| **Fail-fast** | Detects structural modification via a `modCount` check and throws `ConcurrentModificationException` on the next `next()` call | `ArrayList`, `HashMap` iterators |
| **Weakly consistent** | Never throws; reflects the collection's state at some unspecified point during the iteration, may or may not see later inserts/removals, but is guaranteed never to see the same element twice and never to throw | `ConcurrentHashMap`, `ConcurrentLinkedQueue` iterators |
| **Snapshot** | Iterates over an immutable copy captured at `iterator()` call time; concurrent mutations after that point are completely invisible for the whole iteration, however long the iteration runs | `CopyOnWriteArrayList` iterator |

A `ConcurrentHashMap<ClientId, ClientRestrictions>` iterator started just before a resize can, in principle, see some entries already in their post-resize bin and other entries still in their pre-resize bin, but it will never throw and never hand back a torn or partially-constructed `Node`.
`CopyOnWriteArrayList`'s iterator, by contrast, is handed a reference to the backing array object at the exact moment `iterator()` is called and never re-reads the list's array field again for the rest of that iteration — even if the underlying list is completely replaced with a brand-new array under it mid-iteration, the iterator keeps walking the old array all the way to its end, oblivious to every subsequent write.

Bulk methods built on the same iteration machinery — `forEach`, `search`, `reduce` on `ConcurrentHashMap` — inherit the identical weakly-consistent guarantee, which is why they are safe to run concurrently with ongoing writes without any of them ever throwing `ConcurrentModificationException`.

**Follow-up:**

"Which category is `Vector`'s iterator?" — fail-fast, same family as `ArrayList`; `Vector` synchronizes each individual method call, but its iterator still checks `modCount` on every `next()` and throws `ConcurrentModificationException` exactly like an unsynchronized `ArrayList` would.

**Interview:**

The one-line summary interviewers are listening for is "weakly consistent means it never throws and may miss very recent writes; snapshot means iterating a frozen copy taken up front; fail-fast means it detects the race and deliberately blows up rather than risk handing back a corrupted read."

### 5.1.67 When is `CopyOnWriteArrayList` the right choice, and when is it a disaster?

It's the right choice specifically when reads vastly outnumber writes and the list itself stays small — the canonical case is a listener registry: `NotificationService` holding a handful of subscriber callback objects that get iterated on every single event fired but are registered or unregistered only rarely, at startup or on configuration change.
Every mutating call (`add`, `remove`, `set`) copies the *entire* backing array, mutates the fresh copy, then volatile-writes the copy back as the list's new array reference — so reads never need to acquire any lock at all (they just read the current array reference once and index into it directly) and iteration never throws `ConcurrentModificationException`, because the iterator snapshotted the array reference before your mutation even started its copy.
It becomes an outright disaster the moment writes become frequent relative to the list's size, because every single write is an **O(n) full array copy**: appending to a `CopyOnWriteArrayList` used to hold stake-reservation records for a workload doing 2.8M appends a day means 2.8M separate full-array copies, and the *n*-th append copies an array that has already grown to hold the previous *n-1* elements — so the whole run is effectively **O(total-elements²)** in copying work alone, on top of the garbage-collection churn from discarding an ever-larger throwaway array on literally every write.

For comparison, a plain `ArrayList` under a single external lock would give O(1) amortized appends but zero-cost-free reads are impossible without that same lock, whereas `CopyOnWriteArrayList` inverts the tradeoff entirely — reads pay nothing, writes pay everything — which is precisely why the choice is a function of the read/write ratio, never a default.

**Follow-up:**

"What's the fix if you need both frequent writes and thread safety?" — a `ConcurrentLinkedQueue` or `ConcurrentLinkedDeque` if indexed access isn't required, a `Collections.synchronizedList` wrapping a plain `ArrayList` combined with explicit external locking for any compound operation, or a structural change so the 2.8M writes route through a `ConcurrentHashMap` keyed by identity rather than a positional list at all.

**Pitfall:**

Reaching for `CopyOnWriteArrayList` as a generic "thread-safe `ArrayList`" purely because the class name sounds like a drop-in replacement for `ArrayList` under concurrency — it is a narrow, special-purpose structure engineered for one specific read-heavy/write-rare access pattern, never a safe general-purpose default for concurrent list usage.

**Interview:**

This question tests judgment, not recall — the strongest answers state the read/write ratio threshold explicitly (small, read-heavy, write-rare) rather than giving a vague "it depends," and back it with the O(n) copy cost as the concrete reason.

**Insight:**

The name itself is the mnemonic worth keeping: "copy on write" literally describes the O(n) cost paid on every mutation, so any time write frequency is unknown or growing, the name alone is a signal to measure before committing to the structure.

### 5.1.68 Why is there no `ConcurrentArrayList`?

Because an array-backed list's core operations — indexed insertion or removal in the middle of the structure, and growing capacity when the backing array is exhausted — inherently require shifting or copying a large contiguous run of elements, and there is no known technique to make either operation "lock-free" or even "lock briefly per element" the way a hash bin or an individually-linked node can be updated in isolation from its neighbors.
Any hypothetical concurrent array-list would need either a single coarse-grained lock guarding the whole structure for any structural change at all — which is just `Collections.synchronizedList` re-branded with a new name — or a fundamentally different, non-contiguous internal memory layout, at which point it stops actually being an array-backed `ArrayList` in any meaningful sense.
The two structures the JDK actually ships instead each solve the problem by explicitly changing what "concurrent" is allowed to mean for a list-like structure: `CopyOnWriteArrayList` accepts O(n) writes in exchange for genuinely lock-free reads, and `ConcurrentLinkedDeque` gives up indexed random access entirely in exchange for lock-free node-level appends and removals at either end of the deque.
There is no way to simultaneously keep O(1) indexed access, in-place structural mutation, and fine-grained per-element concurrency — you get to pick at most two of the three.

Historically, `Vector` looks like it might be the answer — every method is `synchronized` and it is array-backed — but that only gives whole-object mutual exclusion, identical to `Collections.synchronizedList`, not fine-grained concurrency; it was never a solution to this problem, just an early, coarse one.

**Follow-up:**

"What about `CopyOnWriteArraySet`?" — it uses the identical underlying copy-on-write array strategy as the list, layered with deduplication on insert, and it inherits precisely the same disaster-under-frequent-writes profile that makes `CopyOnWriteArrayList` dangerous for high-churn workloads.

**Interview:**

A confident, fast "there is no `ConcurrentArrayList`" followed immediately by the structural reason (contiguous-array operations can't be made fine-grained) is a strong signal; hesitating and guessing at a class name that doesn't exist is a common tell.

**Pitfall:**

Reaching for `Vector` when the actual need is fine-grained concurrent mutation — `Vector` gives whole-object mutual exclusion identical to `Collections.synchronizedList`, not the bin-level or node-level granularity `ConcurrentHashMap` or `ConcurrentLinkedDeque` provide, so swapping `ArrayList` for `Vector` under load fixes nothing about the actual contention.

### 5.1.69 `Hashtable` versus `Collections.synchronizedMap` versus `ConcurrentHashMap`

| | `Hashtable` | `Collections.synchronizedMap(new HashMap<>())` | `ConcurrentHashMap` |
|---|---|---|---|
| Lock granularity | Whole map, every method `synchronized` | Whole map, via one wrapper lock (or a caller-supplied lock object) | Per-bin |
| Null keys/values | Neither allowed | Both allowed (inherited from `HashMap`) | Neither allowed |
| Iteration | Fail-fast (plus the legacy `Enumeration` API) | Fail-fast — caller must manually wrap the entire iteration in `synchronized(map)` | Weakly consistent, never throws |
| Read concurrency | None — every read blocks behind every write | None — every read blocks behind every write | Full — reads take no lock at all |
| Compound atomics | None built in | None built in | `putIfAbsent`, `computeIfAbsent`, `merge`, `compute`, and friends |
| Era | Java 1.0 legacy collection | Java 1.2 Collections Framework utility wrapper | Java 5, entirely rewritten for Java 8 |

`Hashtable` and `synchronizedMap` are functionally near-identical in practice — both serialize every single access behind exactly one lock — the only real difference is that `Hashtable` predates the Collections Framework entirely and disallows nulls for the same check-then-act reason `ConcurrentHashMap` does, while `synchronizedMap` simply inherits whatever null policy its wrapped map already has.
Neither of the two older options gives you actual concurrency; they give you *safety* (no internal corruption) purely at the cost of serializing every single thread through one shared lock, which is exactly the throughput bottleneck `ConcurrentHashMap`'s per-bin locking design exists to remove.
For a `ClientRestrictions` lookup performed on every single stake attempt at 1,200/sec peak, `Hashtable` or `synchronizedMap` would serialize every one of those reads behind one lock even though the reads touch entirely unrelated clients and share nothing — `ConcurrentHashMap` lets all of them proceed genuinely in parallel.

For sorted concurrent iteration specifically, none of these three is the right tool at all — `ConcurrentSkipListMap` is, since it is the concurrent analogue of `TreeMap` and preserves ordered traversal under concurrent writers where a hash-based map fundamentally cannot.

**Follow-up:**

"When would you still deliberately reach for `synchronizedMap` today?" — specifically when you need an atomic *multi-step* compound operation spanning arbitrary keys — "iterate the whole map and remove every entry matching a predicate, then insert one summary key," all as a single atomic unit — `synchronized(map) { ... }` wrapped around that whole block gives you that guarantee directly; `ConcurrentHashMap` deliberately does not offer any whole-map atomic block, because whole-map locking is precisely the bottleneck it exists to avoid.

**Interview:**

This comparison question rewards a table-shaped answer even when spoken aloud — walking granularity, then nulls, then iteration style, in that order, reads as more organized than a single blended paragraph covering all three at once.

**Insight:**

The progression across all three also tracks JDK history in order — `Hashtable` from Java 1.0, `synchronizedMap` from the Java 1.2 Collections Framework as a general-purpose wrapper for any map implementation, and `ConcurrentHashMap` from Java 5, rewritten again for Java 8 — which is itself a useful way to remember why the newest of the three is also the most sophisticated.

### 5.1.70 How does `ConcurrentHashMap` resize while readers are reading it?

Resize is **cooperative and incremental**, never a single stop-the-world copy of the whole table.
When the map determines it needs to grow, it allocates the new, double-sized table up front and then transfers bins from the old table into the new one in small chunks — the named constant `MIN_TRANSFER_STRIDE = 16` sets the minimum number of bins any single participating thread claims per transfer step, so multiple threads (any thread that happens to call `put` and notices a resize already underway) can each grab a stride of bins and help move them in parallel rather than one lone thread being forced to migrate the entire table alone.
A bin that has already finished being transferred is marked with a special forwarding node whose hash field carries the sentinel value `MOVED = -1`; any reader or writer that subsequently lands on a forwarding node knows immediately to redirect its lookup into the new table instead of the old one.
Readers never block on any part of this process: the `table` field itself is `volatile`, so a reader either sees the old table reference (and finds its target bin in a state that is still internally consistent, because the old bin's contents are never mutated in place until the transfer for that specific bin is fully complete) or sees the new table reference after the atomic swap — there is no window in which a reader can observe a torn or half-migrated table.
Two related sentinel hash values live in the same forwarding-node mechanism family: `TREEBIN = -2` marks a bin that has been converted into a red-black tree root wrapper node, and `RESERVED = -3` marks a bin transiently reserved during `computeIfAbsent`'s bin-creation race so a second thread trying to create the same bin backs off instead of colliding.

The `sizeCtl` field is the coordination point for all of this: a negative value encodes "a resize is in progress" (with the low bits identifying how many threads are actively helping), and any thread that calls `put` and observes that negative value joins the transfer instead of proceeding with its own write, which is the mechanism that turns "one thread resizing" into "many threads cooperatively resizing."

**Follow-up:**

"What triggers treeify, and can a bin un-treeify afterward?" — a bin converts from a linked list to a tree once it accumulates `TREEIFY_THRESHOLD = 8` nodes **and** the table itself has already reached at least `MIN_TREEIFY_CAPACITY = 64` (below that table capacity, the map resizes the entire table instead of treeifying just one hot bin, on the theory that a small table with one overloaded bin is more likely a bad initial sizing than a genuine hash-collision attack); a treeified bin converts back into a plain linked list once removals bring its population down to `UNTREEIFY_THRESHOLD = 6` nodes.

**Insight:**

The resize trigger math shares the same shape as plain `HashMap` — `DEFAULT_CAPACITY = 16` initial buckets combined with a hard-coded load factor of **0.75** (unlike `HashMap`, `ConcurrentHashMap`'s constructor argument for "load factor" only influences the *initial* table sizing calculation, not a persistent configurable field the map checks on every put) — but the *execution* of the resize itself is what genuinely differs: incremental, helped by multiple concurrent threads, and completely non-blocking for readers throughout, versus `HashMap`'s single-threaded, all-at-once full rehash.

**Interview:**

This is one of the harder internals questions in the set, and interviewers use it to gauge whether a candidate can reason about a data structure mutating underneath a lock-free reader without hand-waving "it's just thread-safe, trust me."

### 5.1.71 State the `ThreadPoolExecutor` submission algorithm in order

Four steps, checked strictly in this exact order for every single `execute(task)` call, and this is the most-asked single question in this entire range — walk it slowly and completely:

1. **If the current worker count is below `corePoolSize`, start a brand-new core worker to run this task directly** — even if some existing core workers happen to be idle right now. This is the detail almost everyone gets wrong under pressure: the check is purely against the *worker count*, never against "is anyone currently free." A pool with `core=8` and 3 idle workers sitting completely free will still start a 4th, 5th, up to an 8th core worker for new submissions until it actually has 8 workers total, before it ever considers routing work to an idle one via the queue.
2. **Otherwise (core count already satisfied), try to enqueue the task on the work queue.** If the enqueue succeeds, the executor performs a **double-check**: it re-verifies the pool is still in the running state (if the pool was shut down in the narrow window between step 1 failing and the enqueue succeeding, the just-enqueued task is removed again and handed to rejection instead), and it re-checks that at least one live worker still exists to eventually pick the task up (if the pool somehow had zero workers at that instant — every worker having died or the pool having `core=0` — a brand-new worker is started specifically to guarantee the just-enqueued task isn't stranded forever with nobody to run it).
3. **If the queue rejects the offer** — meaning it's a bounded queue and it's currently full — the executor tries to start a new worker, this time allowed to grow past `corePoolSize` all the way up to `maximumPoolSize`.
4. **If that attempt also fails** — the pool is already at `maximumPoolSize` and every worker is busy — the task is finally handed to the configured `RejectedExecutionHandler`, which is the only point at which the four rejection policies (5.1.74) ever come into play.

For a stake-settlement pool sized `core=8, max=16` and backed by a bounded `LinkedBlockingQueue` of capacity 500, absorbing the 3,400/sec settlement burst plays out exactly this way in practice: the first 8 concurrent settlement tasks each spin up a dedicated core worker directly (step 1); the next wave of tasks — while all 8 core workers stay continuously busy — fills the 500-slot queue (step 2); only once that queue is also completely full does the pool begin growing past 8 workers toward its ceiling of 16 (step 3); only once all 16 workers are busy and the queue is still full does the `RejectedExecutionHandler` ever actually fire (step 4).

A related detail worth stating: `getTask()` inside the worker loop is what actually blocks on `queue.take()` (or `poll(keepAliveTime, unit)` once `allowCoreThreadTimeOut` is enabled or the worker count exceeds `corePoolSize`), and a `getTask()` that returns `null` is what causes a worker thread to exit and decrement the live worker count, which is the mechanism idle-timeout eventually acts through.

**Follow-up:**

"Why doesn't step 1 check whether any core worker is currently idle before starting a new one?" — because checking "is anyone idle" would require synchronizing on live per-worker state on every single submission, reintroducing exactly the kind of pool-wide lock contention the whole queue-plus-worker-count design exists to avoid; the queue itself is the mechanism that routes work to an idle worker, not the core-worker-count check in step 1.

**Pitfall:**

Assuming a pool with `core=8, max=16` and one visibly idle worker will route the very next submitted task to that idle worker instead of growing the pool further — no: until the core count is fully satisfied and the queue is genuinely full, growth toward `max` can occur even while a worker looks idle, purely because of timing between steps; in steady state this rarely matters because an idle core worker pulls from the queue almost instantly, but it explains real, observable transient over-provisioning under bursty submission patterns.

**Interview:**

This is the highest-value question in the whole file to over-prepare — many interviewers will not move past it until every one of the four steps and the double-check are stated correctly and in the right order, so rehearsing it out loud, not just reading it, pays off disproportionately.

### 5.1.72 Why is `newFixedThreadPool` dangerous in production?

`Executors.newFixedThreadPool(n)` sets `core == max == n` and, critically, backs the pool with an **unbounded** `LinkedBlockingQueue` (its no-argument constructor, whose effective capacity is `Integer.MAX_VALUE`).
Trace that configuration through the submission algorithm above: steps 3 and 4 are structurally unreachable, because the queue never rejects an `offer` call — it has no real capacity limit to hit — so the pool can never grow past its fixed `n` workers and the rejection handler can never fire, no matter how catastrophically far behind the workers fall.
If `PaymentService` submits `WithdrawalTransaction` processing tasks faster than the fixed `n` workers can drain them — say a `PaymentRun` burst lands right as downstream banking-partner calls happen to be running at their documented p99 of 45 seconds instead of the usual p50 of 2 seconds — the queue simply grows without any bound, silently holding an ever-larger backlog of pending transaction objects in heap memory with zero backpressure signal anywhere in the entire system.
The resulting failure mode is not "some submissions get cleanly rejected and the caller finds out immediately" — it's "the process slowly exhausts available heap under sustained load and eventually dies," which surfaces to whoever's on call as an `OutOfMemoryError` thrown from some completely unrelated allocation site, far downstream of the actual root cause that triggered it hours earlier.

Running the concrete arithmetic: a `PaymentRun` burst holding even 50,000 pending `WithdrawalTransaction` objects at a modest few hundred bytes each is only tens of megabytes, survivable on its own — the real danger is many independent unbounded-queue pools across a large service compounding under the same burst, each individually looking harmless in isolation.

**Follow-up:**

"So what should be built instead of reaching for the `Executors` factory methods?" — construct `ThreadPoolExecutor` directly via its full constructor, with an explicitly bounded queue capacity and a rejection policy chosen deliberately per 5.1.74/5.1.75, rather than reaching for any of the `Executors` convenience factories at all — this is precisely why most modern style guides and static-analysis rulesets now flag or outright ban `Executors.newFixedThreadPool`/`newCachedThreadPool` in production code paths.

**Pitfall:**

Believing the word "fixed" in the factory method name implies the whole pool configuration is bounded — the name describes only the worker count, never the queue; the queue defaults to unbounded, and that unbounded queue is the actual, concrete production danger, not the fixed worker count.

**Interview:**

The strongest answers connect this directly back to the submission algorithm from 5.1.71 rather than treating it as a separate fact — naming *which* step becomes unreachable is what distinguishes understanding from memorized warning.

**Insight:**

The two dangerous factory methods share a root cause worth stating explicitly: both leave one axis of the pool's configuration — queue capacity for `newFixedThreadPool`, worker count for `newCachedThreadPool` — at its absolute extreme instead of a deliberately chosen bound, which is precisely the property the four-argument `ThreadPoolExecutor` constructor forces a caller to confront directly.

### 5.1.73 Why is `newCachedThreadPool` dangerous in production?

`Executors.newCachedThreadPool()` sets `core=0, max=Integer.MAX_VALUE`, backed by a `SynchronousQueue` — a queue with literally zero storage capacity, where every `offer` must be matched by a waiting `take` on another thread at that exact instant or the offer fails immediately.
Walk that configuration through the submission algorithm: step 1 never applies at all, since `core=0` means the worker-count-below-core check is trivially already satisfied; step 2's enqueue attempt onto a zero-capacity `SynchronousQueue` fails essentially instantly unless a worker happens to already be idle and blocked in `take()` waiting for exactly this task; so step 3 fires on almost every submission that doesn't find a worker already parked and waiting — and because `max` is `Integer.MAX_VALUE`, step 3 always succeeds, unconditionally, with no ceiling whatsoever.
The net effect is a pool that spins up a brand-new OS thread for essentially every burst of concurrent submissions that doesn't find an idle worker sitting ready.
Point the kind of load implied by 55k concurrent sessions' worth of bursty short-lived tasks at a cached pool during a spike and, in the worst realistic case, tens of thousands of native OS threads can be created within a short window — each one carrying its own reserved stack (roughly 1 MB of address space on typical JVM defaults) — which is exactly how a cached pool converts a routine request spike into `OutOfMemoryError: unable to create new native thread`, and it happens well before heap pressure would ever have become the actual bottleneck.

The `SynchronousQueue`-backed design is also why `newCachedThreadPool` reuses idle threads so eagerly under steady, non-bursty load — a worker that just finished a task immediately parks in `take()` waiting up to 60 seconds for the next handoff, so a sustained low-concurrency workload actually converges to a small, stable thread count despite the pool's theoretically unbounded ceiling.

**Follow-up:**

"Doesn't the 60-second idle-thread keep-alive timeout protect against exactly this?" — no: that timeout only reclaims threads *after* they've already sat idle for 60 uninterrupted seconds; it does absolutely nothing to cap how many threads get created *during* the initial spike itself, because thread creation happens well before any of those newly-created threads has had a chance to go idle in the first place.

**Insight:**

`newFixedThreadPool` fails by leaving the *queue* unbounded; `newCachedThreadPool` fails by leaving the *worker count* unbounded — they are the two mirror-image ends of the exact same structural mistake, an unbounded resource sitting somewhere in the submission algorithm.

**Interview:**

As with `newFixedThreadPool`, tying the danger back to a specific step of the submission algorithm (here, step 3 always succeeding because `max` is unbounded) is what separates a memorized warning from a derived one.

### 5.1.74 Name the four rejection policies and say which one gives backpressure

| Policy | Behavior | Backpressure? |
|---|---|---|
| `AbortPolicy` (default) | Throws `RejectedExecutionException` synchronously on the submitting thread | Yes — the caller is forced to notice and react, but nothing automatically slows it down |
| `CallerRunsPolicy` | Runs the rejected task synchronously on the very thread that called `submit`/`execute` | Yes, and the strongest form of the four — it directly throttles the producer thread itself |
| `DiscardPolicy` | Silently drops the task on the floor, no exception thrown, no execution at all | No — and it is the one to be genuinely wary of, because failures become completely invisible |
| `DiscardOldestPolicy` | Removes the oldest task currently sitting in the queue, then retries offering the new task | Partial — it sheds load under pressure, but it destroys FIFO ordering guarantees and silently discards old, possibly already-committed-to work |

`CallerRunsPolicy` delivers the strongest genuine backpressure because it doesn't just *notify* the caller that the system is overloaded — it makes the caller *pay the exact cost directly and immediately*: the thread trying to submit the next `WithdrawalTransaction` for processing is forced to execute that task itself, synchronously, which means it structurally cannot submit anything further until that one task finishes running, which in turn naturally throttles the entire upstream producer down to match whatever throughput the downstream pool can actually sustain.
`AbortPolicy` provides backpressure only in the weaker sense that the caller is forced to notice and make an explicit decision (retry with backoff, shed the request, escalate an alert) — but nothing about it automatically slows the producer down; a poorly-written caller could simply catch the exception and immediately hammer the pool again at the same rate.
`DiscardPolicy` is the one that deserves the most scrutiny in any code review: work silently vanishes with zero trace, and unless something else entirely is independently monitoring queue-full counters or rejection rates, nobody discovers a given `WithdrawalTransaction` was never actually processed until a client files a complaint days later.

A custom `RejectedExecutionHandler` is also legal and common in production: implementing `rejectedExecution(Runnable r, ThreadPoolExecutor executor)` to route rejected `WithdrawalTransaction` tasks to a dead-letter queue for later reprocessing is a fifth option outside the four built-in policies, and it is frequently the actual right answer when neither dropping nor blocking the caller is acceptable.

**Follow-up:**

"Which would you actually pick for the stake-settlement pool specifically?" — `CallerRunsPolicy`, because settlement work carries a client-visible correctness and timing expectation, and both silently dropping it and letting it queue unboundedly are strictly worse outcomes than briefly, measurably slowing down the caller that's producing more work than the pool can currently absorb.

**Pitfall:**

Picking `DiscardOldestPolicy` on the assumption that it's "smarter" than plain `DiscardPolicy` because it at least keeps the newest work around — for FIFO-sensitive processing such as ordered settlements, discarding an *older* already-queued task out of turn can silently violate correctness or ordering invariants the calling code assumed the queue was preserving, which is often a worse failure than dropping the newest arrival instead.

**Insight:**

All four policies only ever fire from step 4 of the submission algorithm in 5.1.71 — the pool is already at `maximumPoolSize` with every worker busy and the queue already full — so choosing among them is really a decision about what should happen at the single, well-defined moment the pool has genuinely run out of every other option.

**Interview:**

Interviewers sometimes ask this as "you have five seconds to add backpressure to an overloaded pool, what do you do" — the expected instinct is `CallerRunsPolicy` named immediately, with the other three policies distinguished only if asked.

### 5.1.75 How do you size a thread pool for CPU-bound and for I/O-bound work — derive it

**CPU-bound work:** the natural ceiling is the number of available cores, because scheduling more genuinely runnable threads than there are cores just means the OS time-slices between them with no throughput gain whatsoever — only added context-switch overhead and cache-line eviction between switches.
The standard rule of thumb is `Nthreads = Ncpu + 1`, where the `+1` exists to cover a thread occasionally page-faulting or blocking very briefly on something incidental, so that a core doesn't sit fully idle during that narrow gap while every other thread is legitimately busy computing.

**I/O-bound work:** the general derivation, from *Java Concurrency in Practice*, is:

```
Nthreads = Ncpu × Utarget × (1 + W/C)
```

where `Ncpu` is the number of available cores, `Utarget` is the target CPU utilization expressed from 0 to 1, `W` is the average time a task spends waiting per unit of work, and `C` is the average time a task spends actually computing.
Plugging in this domain's own concrete numbers — 8 cores, a target utilization of 90%, a downstream wait of 100 ms and only 2 ms of actual local compute per task — gives `W/C = 100 / 2 = 50`, so:

```
Nthreads = 8 × 0.9 × (1 + 50) = 8 × 0.9 × 51 = 367.2 ≈ 367
```

That 367 is the pool size required to keep those 8 cores 90%-busy specifically when each task spends 50 times longer blocked waiting on a downstream call (say a card-PSP authorize call, whose documented p50 sits at 240 ms) than it spends doing local computation.
**[PROVE]** the intuition behind the multiplier directly: if a single task is 98% waiting and only 2% actually computing, then keeping one core continuously fed with that 2%-share of real work requires roughly 50 such tasks interleaved concurrently, because any one thread running that pattern is only using its assigned core for 2% of its own lifetime — so it takes on the order of 1/0.02 = 50 threads' worth of that exact interleaving pattern to add up to one core kept continuously, 90%-utilized busy, and multiplying that per-core requirement by 8 cores and the 0.9 target gives the 367 figure above.

Both formulas assume the workload is homogeneous — every task roughly the same shape — which rarely holds exactly in a real service; the practical response is to size per distinct workload class (a small CPU-bound pool for hashing/validation, a large I/O-bound pool for PSP calls) rather than a single shared pool sized by an averaged, blended `W/C` ratio across unrelated task types.

**Follow-up:**

"What breaks this formula when applied naively in practice?" — it silently assumes every task is fully independent and that the downstream system can genuinely absorb 367 simultaneous in-flight calls; if the PSP itself enforces a lower internal concurrency cap than that, the formula's output just relocates the queueing pressure from your process into theirs, or trips their own overload protection instead of yours.

**Insight:**

This is the identical Little's-Law-flavored reasoning used elsewhere in this topic for concurrency sizing — `W/C` is really answering "how many overlapping task-lifetimes of concurrency does it take to deliver one continuous unit of actual compute work."

**Interview:**

Be ready to actually work the arithmetic on a whiteboard, not just recite the formula — interviewers commonly change the numbers (a different wait/compute ratio, a different core count) specifically to check the formula is understood rather than memorized for one specific input.

### 5.1.76 `shutdown()` versus `shutdownNow()`, and the correct two-phase shutdown

`shutdown()` is the graceful path: the pool immediately stops accepting brand-new tasks (any further call to `submit`/`execute` throws `RejectedExecutionException` right away), but every task that's already queued or already actively running is allowed to run through to completion normally — it never interrupts any currently-executing worker thread.
`shutdownNow()` is the forceful path: it also stops accepting new tasks, but additionally **interrupts** every actively-running worker thread immediately, and it returns the `List<Runnable>` of whatever tasks were still sitting in the queue and had never even started, so the caller has the option of deciding what to do with that abandoned work.
Neither call blocks the caller — both return essentially instantly, with the pool continuing to shut down asynchronously in the background well after either method call has already returned.

The correct production pattern almost never calls just one of these in isolation — it's the two-phase shutdown documented directly in the JDK's own `ExecutorService` javadoc example:

```java
void shutdownPaymentPool(ExecutorService pool) {
    pool.shutdown();
    try {
        if (!pool.awaitTermination(30, TimeUnit.SECONDS)) {
            pool.shutdownNow();
            if (!pool.awaitTermination(10, TimeUnit.SECONDS)) {
                System.err.println("Payment pool did not terminate");
            }
        }
    } catch (InterruptedException e) {
        pool.shutdownNow();
        Thread.currentThread().interrupt();
    }
}
```

Call `shutdown()` first, to let genuinely in-flight `WithdrawalTransaction` processing finish cleanly and consistently; wait a firmly bounded amount of time via `awaitTermination`; and only escalate to `shutdownNow()`'s interrupt-everything behavior if that grace period actually expires without the pool draining — going straight to `shutdownNow()` on day one risks interrupting a worker thread mid-write to the ledger, and calling only `shutdown()` with no escalation at all risks the caller waiting forever if even one task is genuinely stuck.

It's also worth naming the pattern's usual home: this two-phase shutdown sequence typically lives inside a JVM shutdown hook registered via `Runtime.getRuntime().addShutdownHook(new Thread(() -> shutdownPaymentPool(pool)))`, so that a `SIGTERM` from an orchestrator triggers the same graceful drain rather than an abrupt process kill mid-settlement.

**Follow-up:**

"What happens to a task that's currently blocked inside `Object.wait()` or `Thread.sleep()` at the moment `shutdownNow()` interrupts it?" — it wakes immediately with `InterruptedException` thrown from that blocking call, provided the task's own code correctly propagates or acts on that exception rather than swallowing it; a task written to catch `InterruptedException` and simply continue looping defeats `shutdownNow()`'s interrupt entirely, and no amount of calling `shutdownNow()` again will fix badly-written task code.

**Pitfall:**

Calling `shutdownNow()` and treating its returned list as "the complete accounting of all work that didn't happen" — it only ever contains tasks that never *started* executing in the first place; tasks that were already mid-execution when the interrupt landed may have partially run, mutated some state, and then aborted, and none of that partial-completion state shows up anywhere in that returned list, so `shutdownNow()` alone never gives a clean, complete accounting of exactly what needs to be retried afterward.

**Interview:**

The two-phase code sample is worth having memorized nearly verbatim, since it's lifted almost directly from the JDK's own `ExecutorService` javadoc and is one of the more commonly requested "write it on the whiteboard" snippets in this entire topic.

---

**Leaves covered:** 5.1.61–5.1.76 (16 questions)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 423

