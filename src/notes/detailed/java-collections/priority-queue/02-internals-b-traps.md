# 02 Java Collections — `PriorityQueue` — INTERNALS (§3.5.14–3.5.20 mutation, stability, bounds, `PriorityBlockingQueue` and `decreaseKey`)

**Target version: Java 21 LTS.** | [Index](../00-index.md)
Previous: [priority-queue/01b-internals-removeat-and-iteration.md](01b-internals-removeat-and-iteration.md) · Next: [priority-queue/03-build-my-priority-queue.md](03-build-my-priority-queue.md)

[01](01-internals-a-heap.md) and [01b](01b-internals-removeat-and-iteration.md) walked the source. This file is about the ways a correct `PriorityQueue` still gives you the wrong answer — and each of them traces back to the same fact, which is that a heap does not store an ordering, it stores a *snapshot of comparison results made at insertion time*. Change the inputs to those comparisons afterwards and the structure is silently wrong; ask for a guarantee the comparisons never made and you get nothing.

Four traps, one API gap, and one class that solves a different problem.

---

### Mutating a priority after insertion

**Mental model.** `siftUp` compares the incoming element against its parents *once*, at insertion, and writes the result into the array as a position. The comparison is not stored, not repeated, and not revalidated. So the array is a fossil record of comparisons that were true at the moment they were made. Mutate the field the comparator reads and the fossil does not update — the element sits exactly where it was, now in the wrong place, and nothing in the JDK notices.

**Why it bites.** Because the natural design for a scheduler or a Dijkstra frontier is a mutable object with a `priority` field, and "just update the priority" is the obvious operation. Every other Java collection tolerates mutating a field that nothing indexes on. A heap indexes on it.

**When to reach for what.** Never mutate in place. Either remove, mutate, re-insert; or make the element immutable and insert a new one, tombstoning the old; or maintain a side index and re-sift explicitly. The third is the only one that is O(log n), and the JDK gives you no hook for it (see `decreaseKey` below).

**How it fails.** Measured, on JDK 21.0.7:

```java
PriorityQueue<int[]> pq = new PriorityQueue<>(Comparator.comparingInt(x -> x[0]));
int[] lo = {1, 100}, mid = {5, 200}, hi = {9, 300};
pq.offer(lo); pq.offer(mid); pq.offer(hi);
System.out.println("head priority " + pq.peek()[0]);
lo[0] = 99;                                  // mutate in place
System.out.println("head priority " + pq.peek()[0]);
StringBuilder order = new StringBuilder();
while (!pq.isEmpty()) order.append(pq.poll()[0]).append(' ');
System.out.println("poll order " + order.toString().trim());
```

```
before mutation    = head priority 1
after lo[0] = 99   = head priority 99 (still the mutated one)
poll order now     = 99 5 9  (not ascending)
```

`99` came out first. It is at `queue[0]` because it *was* `1` when it was placed there, and `peek()` is a bare array read of index 0 — no comparison, nothing to detect the lie. The drained sequence `99 5 9` is not ascending and not descending; it is arbitrary, which is the worst kind of wrong because no assertion pattern catches it reliably.

**Pitfall:** the wrong belief is "the queue will re-order when I change the priority, or at worst on the next `poll`". The symptom is a scheduler that runs tasks out of order, or a Dijkstra implementation that returns paths that are not shortest — both intermittent, both dependent on where in the array the mutated element happened to sit, and neither throwing anything. The fix, in order of preference:

```java
// 1. remove, mutate, re-insert — O(n) for the remove, correct
pq.remove(lo);          // O(n): indexOf then removeAt
lo[0] = 99;
pq.offer(lo);           // O(log n)

// 2. immutable elements plus a tombstone — O(log n), the usual production answer
record Entry(int prio, long seq, Task task) {}
pq.offer(new Entry(99, seq++, task));       // stale Entry stays, skipped on poll

// 3. an indexed heap that exposes re-sift — O(log n), but you must write it
//    yourself: a Map<E,Integer> of positions, maintained by every array write
//    inside siftUp and siftDown. Sketched under "No decreaseKey" below.
//    Not built in this set; §4.5 builds the plain heap, a stable variant and
//    a bounded top-k, all in 03/04/05.
```

**Interview:** "What happens if you change an element's priority while it is in a `PriorityQueue`?" — Nothing, which is the problem. The element's position was decided by comparisons made at insertion; it does not move, `peek()` may return a non-minimum, and the drain order becomes arbitrary. Remove-mutate-reinsert, or use immutable entries with tombstones.

> A heap position records the result of comparisons made at insertion time; mutating the field a comparator reads invalidates that record silently, and no JDK code path revalidates it.

---

### No stability, and the sequence-number fix

**Mental model.** Stability means equal elements come out in insertion order. A heap cannot give it, and the reason is visible in two characters of the source: `siftUp` breaks on `compareTo(parent) >= 0` and `siftDown` breaks on `compareTo(child) <= 0`. Equal stops the movement — so an element equal to its parent stays *below* it, and an element equal to a child stays *above* it. Which one is above which is therefore decided by whichever happened to arrive when, and by the shape the array had at the time. That is not insertion order; it is an artefact of the sift paths.

**Why it exists.** Nothing in the `Queue` or `Comparator` contract asks for stability, and providing it would cost a tiebreak comparison on every single comparison — or a hidden sequence field on every element, which the JDK cannot add because it does not own the element type.

**How it fails.** Measured: seven tasks, all priority 1, inserted `a b c d e f g`:

```
equal priorities    = agfedcb (insertion order was abcdefg)
```

Not insertion order, not reverse insertion order. `a` first because it went to the root and never moved; the rest in an order that is a direct fingerprint of the sift paths. Change the count from seven to eight and the sequence changes again.

**The fix** is to make the tie impossible by adding a monotonic sequence number to the *comparator*, not to the elements:

```java
record Seq<T>(T value, long seq) {}

static <T> PriorityQueue<Seq<T>> stable(Comparator<? super T> byPriority) {
    return new PriorityQueue<>(
        Comparator.<Seq<T>, T>comparing(Seq::value, byPriority)
                  .thenComparingLong(Seq::seq));
}

// usage
AtomicLong seq = new AtomicLong();
var q = stable(Comparator.comparingInt(Task::prio));
q.offer(new Seq<>(task, seq.getAndIncrement()));
```

Now no two elements compare equal, so `>= 0` and `<= 0` never fire on a tie, and the drain order is total: by priority, then by insertion. The same seven equal-priority tasks, measured:

```
stable drain        = abcdefg
```

The cost is 8 bytes per element for the `long` plus the wrapper object — 16 bytes of header and two fields, so around 32 bytes per element on top of what you were already paying — and one extra comparison only on the ties that used to be ambiguous.

`thenComparingLong` rather than `thenComparing` matters: the boxing variant would allocate a `Long` per comparison, which on a `poll`-heavy workload is 2·log₂(n) allocations per operation.

**Pitfall:** the wrong belief is that `PriorityQueue` is FIFO within equal priorities, because that is what a "priority queue" means in most textbook descriptions and in most other languages' libraries. The symptom is a work queue whose tasks at the same priority run in an order that looks random and changes between runs — often surfacing as a flaky integration test rather than as a bug report. The fix is the sequence-number tiebreak; there is no flag or constructor argument for it.

**Interview:** "Is `PriorityQueue` stable?" — No. `siftUp` breaks on `>= 0` and `siftDown` on `<= 0`, so equal elements stop moving and their relative order is an artefact of the sift paths. Seven equal-priority items inserted `a`..`g` drain as `agfedcb`. Add a monotonic sequence number as a `thenComparingLong` tiebreak if you need FIFO within a priority.

> A heap is not stable, because both sift loops halt on equality; the only fix is to eliminate equality, with a monotonic sequence number as a secondary comparison key.

---

## Supporting facts

**Max-heap (leaf 3.5.16).** `PriorityQueue` is a min-heap and there is no flag to change it. Reverse the comparator:

```java
// natural ordering, reversed
new PriorityQueue<Integer>(Comparator.reverseOrder());

// key extractor, reversed — note where the reversed() goes
new PriorityQueue<Task>(Comparator.comparingInt(Task::prio).reversed());

// equivalently, and one fewer wrapper
new PriorityQueue<Task>((a, b) -> Integer.compare(b.prio(), a.prio()));
```

`Comparator.reverseOrder()` and `Collections.reverseOrder()` are the same object — `Collections.reverseOrder()` returns the singleton `ReverseComparator.REVERSE_ORDER`. Watch where `.reversed()` sits in a chain: it wraps *everything* to its left, so `comparing(A).thenComparing(B).reversed()` reverses both keys, which is almost never what someone typing it wanted. See [contracts/01](../contracts/01-ordering.md) and [D-13](../diagrams/D-13-comparator-chaining-reversed.svg).

**Bounded top-k (leaf 3.5.17).** `PriorityQueue` is unbounded — no capacity constraint exists, `offer` always returns `true`, and there is nothing to reject an insertion. A bounded top-k needs both a size check and an *inverted* comparator, and the inversion is the part people get wrong:

```java
/** Keeps the k largest elements seen. Uses a MIN-heap, deliberately. */
static <T extends Comparable<? super T>> PriorityQueue<T> topK(int k, Iterable<T> src) {
    PriorityQueue<T> heap = new PriorityQueue<>(k);      // min-heap
    for (T t : src) {
        if (heap.size() < k) {
            heap.offer(t);
        } else if (t.compareTo(heap.peek()) > 0) {
            heap.poll();                                 // evict the smallest kept
            heap.offer(t);
        }
    }
    return heap;                                         // k largest, unordered
}
```

**Insight:** to keep the k *largest* you need a *min*-heap, because the element you must be able to find and evict in O(1)/O(log n) is the smallest of the ones you are keeping — the one a new arrival has to beat. A max-heap would put the largest at the root, which is exactly the element you never want to touch. The cost is `O(n log k)` and `O(k)` memory, versus `O(n log n)` and `O(n)` for sorting everything, which is the whole point when `n` is a stream and `k` is 10.

The `else if (t.compareTo(heap.peek()) > 0)` guard is what keeps it `O(n log k)` rather than `O(n log k)` with a constant factor of two: without it, every element does a `poll` plus an `offer` even when it loses.

**No `decreaseKey` (leaf 3.5.19).** Dijkstra's algorithm, as written in every textbook, calls `decreaseKey(vertex, newDistance)` — lower a vertex's tentative distance and sift it up. That is O(log n) *if* you know where the vertex is. The JDK has no such method, and cannot usefully add one, because finding the element is `indexOf`, which is O(n): the API would advertise O(log n) and deliver O(n).

What an indexed heap adds is a `Map<E, Integer>` from element to array position, maintained by every `siftUp` and `siftDown` write. Then `decreaseKey` is a hash lookup plus a sift. The costs are a hash entry per element — around 69 bytes for a boxed-`Integer` value, per [D-138](../diagrams/D-138-69-bytes-to-store-8.svg) — a map write on every array write inside the sift loops, and a hard requirement that the elements have stable `hashCode`/`equals` (which, given the mutation trap above, is a real constraint: you must not hash on the mutating priority).

The standard workaround, and what most production Dijkstra code in Java actually does, is the **lazy-deletion** form: never decrease, just insert the improved entry again and skip stale pops.

```java
record Step(int node, long dist) {}
var pq = new PriorityQueue<Step>(Comparator.comparingLong(Step::dist));
long[] best = new long[n];
Arrays.fill(best, Long.MAX_VALUE);
best[source] = 0;
pq.offer(new Step(source, 0));
while (!pq.isEmpty()) {
    Step s = pq.poll();
    if (s.dist() > best[s.node()]) continue;      // stale entry, skip
    for (Edge e : adj[s.node()]) {
        long nd = s.dist() + e.weight();
        if (nd < best[e.to()]) {
            best[e.to()] = nd;
            pq.offer(new Step(e.to(), nd));       // no decreaseKey needed
        }
    }
}
```

The heap can hold up to `E` entries instead of `V`, so the bound is `O(E log E)` rather than `O(E log V)` — asymptotically the same for any graph, since `E ≤ V²` makes `log E ≤ 2 log V`. In exchange you need no index, no map, and no mutable elements. The full treatment of graph algorithms is in guide 01; this is the one paragraph of mechanism that belongs here.

**Fibonacci and pairing heaps (leaf 3.5.20).** A Fibonacci heap gives `decreaseKey` in O(1) amortised and `deleteMin` in O(log n) amortised, which improves Dijkstra's theoretical bound from `O(E log V)` to `O(E + V log V)`. Nobody ships one, and the reasons are entirely practical:

| | Binary heap (array) | Fibonacci heap | Pairing heap |
|---|---|---|---|
| `insert` | O(log n) worst | O(1) amortised | O(1) worst |
| `deleteMin` | O(log n) worst | O(log n) amortised | O(log n) amortised |
| `decreaseKey` | O(log n) *given the index* | O(1) amortised | O(log n) amortised, O(1) conjectured |
| Memory per element | 4 bytes (one array slot) | ~40 bytes: 4 pointers + degree + mark flag | ~20 bytes: 3 pointers |
| Locality | contiguous, cache-friendly | pointer-chasing, one miss per hop | pointer-chasing |
| Constant factor | small | large — lazy consolidation, cascading cuts |  moderate |
| Implementation | ~100 lines | ~400 lines, easy to get subtly wrong | ~150 lines |

The array heap's constant factor and cache behaviour beat the Fibonacci heap's asymptotics at every graph size anyone actually runs. Measured comparisons in the literature consistently put the array binary heap ahead for Dijkstra on real road networks and social graphs; the pairing heap is the one that occasionally wins, and only for `decreaseKey`-heavy workloads. **Unverified:** no specific published benchmark is cited here — the qualitative result (array heap wins in practice) is the settled consensus in the algorithms-engineering literature, but I have not re-confirmed a particular paper's numbers against its source for this note. *Would settle it:* a DIMACS shortest-path challenge report, or the Larkin–Sen–Tarjan 2014 experimental study of priority queues.

---

### `PriorityBlockingQueue`, and the spinlock that grows outside the lock

**Mental model.** `PriorityBlockingQueue` is `PriorityQueue`'s algorithm — the same array heap, the same `siftUp`/`siftDown`, the same duplication for monomorphism — wrapped in a single `ReentrantLock` with a `notEmpty` condition, plus one unusual trick: **growing the array happens outside the main lock**, guarded by its own spinlock, so that a resize does not block every reader and writer for the duration of an `Arrays.copyOf`.

**Why it exists.** A `BlockingQueue` implementation that held the main lock across a copy of a million-element array would stall every producer and consumer for the length of that copy. Growth is rare; the lock is hot. So the class trades some complexity for the ability to allocate concurrently.

**How it works.**

```java
    private final ReentrantLock lock = new ReentrantLock();
    private final Condition notEmpty = lock.newCondition();
    private transient volatile int allocationSpinLock;
```
— `java.base/java/util/concurrent/PriorityBlockingQueue.java`, JDK 21, lines 164, 170, 175.

```java
    private void tryGrow(Object[] array, int oldCap) {
        lock.unlock(); // must release and then re-acquire main lock
        Object[] newArray = null;
        if (allocationSpinLock == 0 &&
            ALLOCATIONSPINLOCK.compareAndSet(this, 0, 1)) {
            try {
                int growth = (oldCap < 64)
                    ? (oldCap + 2) // grow faster if small
                    : (oldCap >> 1);
                int newCap = ArraysSupport.newLength(oldCap, 1, growth);
                if (queue == array)
                    newArray = new Object[newCap];
            } finally {
                allocationSpinLock = 0;
            }
        }
        if (newArray == null) // back off if another thread is allocating
            Thread.yield();
        lock.lock();
        if (newArray != null && queue == array) {
            queue = newArray;
            System.arraycopy(array, 0, newArray, 0, oldCap);
        }
    }
```
— lines 287–310. (leaf 3.5.18)

Read it in order. `lock.unlock()` on the *first* line — the method is called while holding the main lock, and its first act is to give it up. That is why it is `tryGrow` and not `grow`: releasing the lock means the queue can change underneath, so everything after is conditional.

`allocationSpinLock` is a `volatile int` CASed from 0 to 1 through a `VarHandle` named `ALLOCATIONSPINLOCK`. It is a spinlock rather than a second `ReentrantLock` because the critical section is one allocation with no blocking inside it, so there is nothing to park for and a monitor's bookkeeping would cost more than the section. The plain `allocationSpinLock == 0` read before the CAS is the standard test-then-test-and-set: a volatile read is far cheaper than a failed CAS on a contended line.

`if (queue == array)` appears twice — once inside the spinlock, once after re-acquiring the main lock — and both are necessary. Another thread may have grown the array while this one had the lock released, in which case this allocation is wasted and must not be published. The second check is what prevents a stale, smaller array from clobbering a larger one.

`Thread.yield()` when `newArray == null`: another thread holds the allocation spinlock, so this thread backs off rather than spinning, then re-takes the main lock and lets the caller retry. Note that a yield here is not a correctness mechanism — the caller's loop is.

The `arraycopy` happens **after** re-acquiring the main lock, not inside the spinlock. So the expensive-but-parallelisable part (allocation, which the GC can do concurrently and which touches only thread-local space until published) is outside the lock, and the part that must see a consistent heap (the copy) is inside it. That division is the whole design.

Growth policy is identical to `PriorityQueue`'s: `oldCap < 64 ? oldCap + 2 : oldCap >> 1`, through the same `ArraysSupport.newLength`.

| | `PriorityQueue` | `PriorityBlockingQueue` |
|---|---|---|
| Thread safety | none | one `ReentrantLock` for all operations |
| Blocking | none | `take()` waits on `notEmpty`; `put` never blocks (unbounded) |
| Growth | `grow` under no lock at all | `tryGrow`: allocate outside the main lock under `allocationSpinLock`, copy inside |
| Iterator | fail-fast via `modCount`, with `forgetMeNot` | **snapshot** — `toArray()` under the lock, so no CME and no `forgetMeNot` |
| `size()` | a field read | a field read under the lock |
| Nulls | rejected | rejected |
| Bounded | no | no — `put` never blocks, so the "blocking" is only on `take` |
| Sorted iteration | no | no, and the snapshot is heap order too |

**Insight:** `PriorityBlockingQueue` is an unbounded `BlockingQueue`, which means it gives you no backpressure — `put` never blocks and never rejects. A producer faster than its consumer will exhaust the heap rather than being slowed down. If you reached for it in a `ThreadPoolExecutor` expecting the queue to throttle submission, it will not; see [concurrent-collections/05](../concurrent-collections/05-blocking-and-lock-free-queues.md).

**Interview:** "How does `PriorityBlockingQueue` differ from `PriorityQueue`?" — Same array heap and same sift code, wrapped in one `ReentrantLock` with a `notEmpty` condition, plus a separate `allocationSpinLock` so array growth allocates outside the main lock. Its iterator is a snapshot rather than fail-fast. And it is unbounded, so it provides no backpressure.

> `PriorityBlockingQueue` reuses `PriorityQueue`'s algorithm under a single `ReentrantLock`, and releases that lock during growth so the allocation happens under a cheap spinlock instead — re-checking `queue == array` on both sides, because the queue can change while the main lock is down.

---

## Pitfalls

### Mutating an element's priority in place

**Wrong**

```java
PriorityQueue<int[]> pq = new PriorityQueue<>(Comparator.comparingInt(x -> x[0]));
int[] lo = {1, 100};
pq.offer(lo);
pq.offer(new int[]{5, 200});
pq.offer(new int[]{9, 300});
lo[0] = 99;                              // "raise the priority"
while (!pq.isEmpty()) System.out.print(pq.poll()[0] + " ");
```

Output: `99 5 9` — measured. Not ascending. `99` is still at index 0 because it was `1` when `siftUp` put it there, and `peek()`/`poll()` read index 0 without comparing anything.

**Right**

```java
pq.remove(lo);          // O(n): indexOf, then removeAt repairs the heap
lo[0] = 99;
pq.offer(lo);           // O(log n)
```

or, better, make entries immutable and tombstone the stale ones, so nothing in the heap ever changes:

```java
record Step(int node, long dist) {}
// insert an improved entry; skip on poll if dist > best[node]
```

**Why people believe it:** every other collection in `java.util` tolerates mutating a field it does not index on, and a `List` or an `ArrayDeque` genuinely does not care. A heap's element *positions* are the index, and they were computed once.

### Expecting FIFO within equal priorities

**Wrong**

```java
var q = new PriorityQueue<Task>(Comparator.comparingInt(Task::prio));
for (String n : List.of("a","b","c","d","e","f","g")) q.offer(new Task(n, 1));
while (!q.isEmpty()) System.out.print(q.poll().name());
```

Output: `agfedcb` — measured. Insertion order was `abcdefg`. Both sift loops halt on equality (`>= 0` climbing, `<= 0` sinking), so equal elements never move past each other and their relative order is a fingerprint of the sift paths, not of arrival time.

**Right**

```java
record Seq<T>(T value, long seq) {}
AtomicLong counter = new AtomicLong();
var q = new PriorityQueue<Seq<Task>>(
    Comparator.<Seq<Task>, Integer>comparing(s -> s.value().prio())
              .thenComparingLong(Seq::seq));
q.offer(new Seq<>(task, counter.getAndIncrement()));
```

`thenComparingLong`, not `thenComparing` — the boxing form allocates a `Long` per comparison, and `poll` does about `2 log₂ n` of them.

**Why people believe it:** most textbook descriptions and most other standard libraries describe a priority queue as FIFO within a priority class, and the javadoc's phrasing ("ties are broken arbitrarily") is easy to skim past.

### Using a max-heap for top-k

**Wrong**

```java
// keep the 10 largest
var heap = new PriorityQueue<Integer>(Comparator.reverseOrder());   // max-heap
for (int v : stream) {
    heap.offer(v);
    if (heap.size() > 10) heap.poll();     // evicts the LARGEST
}
```

Output, measured over a shuffled `1..100`:

```
topK(10) min-heap   = [91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
topK(10) max-heap   = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

The max-heap version kept the ten *smallest*. The root of a max-heap is the biggest thing you have, so `poll` throws away exactly what you were trying to keep.

**Right**

```java
// keep the 10 largest: use a MIN-heap, evict its root
var heap = new PriorityQueue<Integer>(10);                          // min-heap
for (int v : stream) {
    if (heap.size() < 10) heap.offer(v);
    else if (v > heap.peek()) { heap.poll(); heap.offer(v); }
}
```

**Why people believe it:** "I want the largest, so I want a max-heap" is a natural inference and it is backwards. The element you need cheap access to is the *weakest of the ones you are keeping* — the threshold a new arrival must beat — which is the minimum. The inversion catches almost everyone once.

### Reaching for `PriorityBlockingQueue` for backpressure

**Wrong**

```java
var executor = new ThreadPoolExecutor(4, 4, 0L, TimeUnit.MILLISECONDS,
        new PriorityBlockingQueue<>());
// belief: submission will block when the queue is full
```

It never blocks and never rejects, because `PriorityBlockingQueue` is unbounded — there is no capacity, `put` cannot wait, and `offer` always returns `true`. A producer faster than four consumers grows the heap until the heap exhausts the JVM. The "blocking" in the name refers only to `take()` waiting for an element.

**Right**

```java
// bounded, so submission blocks or the RejectedExecutionHandler fires —
// but ArrayBlockingQueue is FIFO, so you lose the priority ordering
var executor = new ThreadPoolExecutor(4, 4, 0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(1000));

// to keep both, bound it yourself with a semaphore at the submission point
private final Semaphore permits = new Semaphore(1000);
void submit(Runnable task) throws InterruptedException {
    permits.acquire();
    executor.execute(() -> { try { task.run(); } finally { permits.release(); } });
}
```

**Why people believe it:** every other `BlockingQueue` in `java.util.concurrent` that people meet first — `ArrayBlockingQueue`, `LinkedBlockingQueue` with a capacity — is bounded, and the interface name promises blocking. `PriorityBlockingQueue`, `LinkedBlockingQueue` with no capacity argument, and `LinkedTransferQueue` are the unbounded ones.

---

## Cheat sheet

| Fact | Value |
|---|---|
| Mutating a priority in place | position never updates; `peek()` can return a non-minimum; drain order arbitrary |
| Measured proof | `{1,5,9}` with the 1 mutated to 99 drains as `99 5 9` |
| The three fixes | remove-mutate-reinsert (O(n)); immutable entries + tombstones (O(log n)); indexed heap (O(log n), DIY) |
| Stability | **none.** `siftUp` breaks on `>= 0`, `siftDown` on `<= 0` — equal stops moving |
| Measured proof | seven equal-priority items `a`..`g` drain as `agfedcb` |
| Stability fix | `thenComparingLong(Seq::seq)` with a monotonic counter; never `thenComparing` (boxes) |
| Max-heap | `Comparator.reverseOrder()`, or `comparingInt(f).reversed()`; `.reversed()` wraps the whole chain |
| Bounded? | **no.** Unbounded, `offer` always returns `true` |
| Top-k largest | keep a **min**-heap of size k; evict its root; `O(n log k)`, `O(k)` memory |
| Why min-heap for top-k | the root must be the weakest element you are keeping — the one a new arrival must beat |
| `decreaseKey` | absent, and cannot be O(log n) without an index, since `indexOf` is O(n) |
| Dijkstra in practice | lazy deletion: re-insert improved entries, skip stale pops; `O(E log E)` |
| Fibonacci heap | O(1) amortised `decreaseKey`, but ~40 bytes/element and pointer-chasing; loses in practice |
| `PriorityBlockingQueue` lock | one `ReentrantLock` + `Condition notEmpty` (lines 164, 170) |
| `allocationSpinLock` | `transient volatile int` (line 175), CASed via a `VarHandle`, guards growth outside the main lock |
| `tryGrow` | unlocks first, allocates under the spinlock, `Thread.yield()`s on contention, copies after re-locking |
| `queue == array` checked twice | inside the spinlock and after re-locking — the queue can change while the lock is down |
| PBQ iterator | snapshot over `toArray()` under the lock — no CME, no `forgetMeNot` |
| PBQ growth policy | identical: `oldCap < 64 ? oldCap + 2 : oldCap >> 1` |

---

## Self-test

**Q1.** Exactly why does mutating an element's priority not re-order the queue?

<details><summary>Answer</summary>

Because the position was determined by comparisons made once, at insertion, inside `siftUp`, and nothing stores or repeats them. The array holds elements at indices; the indices encode "this element compared `<=` its parent at the time it was placed". `peek()` is `queue[0]`, a bare array read with no comparison. `poll()` reads index 0, then sinks the last element — it never revalidates the elements it does not touch. So a mutated element stays exactly where it was, and the invariant is now false in a way that nothing in the class detects. Measured: `{1, 5, 9}` with the 1 mutated to 99 drains as `99 5 9`.

</details>

**Q2.** Point at the source that proves `PriorityQueue` is not stable.

<details><summary>Answer</summary>

`siftUpComparable`: `if (key.compareTo((T) e) >= 0) break;` — line 648. `siftDownComparable`: `if (key.compareTo((T) c) <= 0) break;` — line 695. Both halt on equality, so an element equal to its parent stops below it and an element equal to a child stops above it. Neither loop consults arrival time, and there is nowhere to store it: the JDK does not own the element type and there is no hidden sequence field. The consequence is measurable — seven items all of priority 1, inserted `abcdefg`, drain as `agfedcb`.

</details>

**Q3.** To keep the k largest elements of a stream, which heap and why?

<details><summary>Answer</summary>

A **min**-heap of size k. The operation you need to be cheap is "find and evict the weakest element I am currently keeping", because that is the threshold a new arrival has to beat — and the weakest of the kept elements is the smallest. A min-heap puts it at the root, so `peek()` is the comparison and `poll()` is the eviction, both O(1)/O(log k). A max-heap puts the *largest* at the root, so `poll()` discards the element you most want to keep. Total cost `O(n log k)` with `O(k)` memory, versus `O(n log n)` and `O(n)` for sorting everything — which is the entire reason to do it this way when n is a stream.

</details>

**Q4.** Why can the JDK not simply add a `decreaseKey(E element, int newPriority)` method?

<details><summary>Answer</summary>

Because it would have to find the element first, and `indexOf` is an O(n) linear scan — there is nothing in the heap invariant to prune on. So the method would advertise the O(log n) that `decreaseKey` means and deliver O(n), which is worse than useless: callers would build Dijkstra on it and get quadratic behaviour. Making it genuinely O(log n) requires a `Map<E, Integer>` from element to array position, maintained on every array write inside both sift loops — which costs a hash entry per element (~69 bytes for a boxed `Integer` value), slows every `offer` and `poll`, and requires elements with stable `hashCode`/`equals` that specifically do *not* hash on the mutating priority. That is a different data structure, so the JDK leaves it to the caller.

</details>

**Q5.** In `tryGrow`, why is `if (queue == array)` checked twice?

<details><summary>Answer</summary>

Because `tryGrow` releases the main lock on its first line, so the queue can be grown by another thread while this one is allocating. The first check, inside the allocation spinlock, avoids allocating at all if the array has already been replaced. The second, after re-acquiring the main lock, is the one that matters for correctness: without it a thread that allocated a 150-slot array could publish it over a 300-slot array another thread had already installed, silently discarding elements. The pattern is compare-and-publish with a stale-detection guard, and the guard is the array *identity*.

</details>

**Q6.** Why is `allocationSpinLock` a spinlock rather than a second `ReentrantLock`?

<details><summary>Answer</summary>

Because its critical section is one `new Object[newCap]` and nothing else — no blocking, no waiting, no condition to await. A `ReentrantLock` buys queueing, fairness options, reentrancy and interruptible acquisition, all of which cost bookkeeping that would exceed the section it is protecting. Contention is expected to be rare (growth is rare), and when it happens the loser calls `Thread.yield()` and lets the caller retry rather than parking. Note the `allocationSpinLock == 0` volatile read before the CAS — the standard test-then-test-and-set, because a plain volatile read is much cheaper than a failed CAS on a contended cache line.

</details>

**Q7.** You put a `PriorityBlockingQueue` in a `ThreadPoolExecutor` to get prioritised tasks with backpressure. What do you actually get?

<details><summary>Answer</summary>

Prioritised tasks and no backpressure. `PriorityBlockingQueue` is unbounded: there is no capacity argument, `offer` always returns `true`, and `put` never waits — the "blocking" is only `take()` waiting for an element to arrive. A producer faster than the pool grows the heap until the JVM runs out of memory, and `RejectedExecutionHandler` never fires because nothing is ever rejected. Also worth knowing: `ThreadPoolExecutor` only creates threads beyond the core size when the queue *refuses* an offer, so an unbounded queue means the pool never grows past `corePoolSize` either. To get both properties you bound submission yourself — a `Semaphore` acquired before `execute` and released in a `finally` — or accept FIFO with an `ArrayBlockingQueue`.

</details>

**Q8.** Fibonacci heaps beat binary heaps asymptotically for Dijkstra. Why does nobody ship one?

<details><summary>Answer</summary>

Constant factors and memory locality. A Fibonacci heap node carries four pointers plus a degree and a mark flag — roughly 40 bytes against an array heap's 4-byte slot — and every operation is pointer-chasing, so each hop is a potential cache miss where the array heap's parent and children are often in the same cache line. Its O(1) `decreaseKey` is *amortised* and depends on lazy consolidation and cascading cuts, both of which are intricate to implement and easy to get subtly wrong. The asymptotic win, `O(E + V log V)` versus `O(E log V)`, is swamped by those factors at every input size anyone runs. The pairing heap is the structure that sometimes wins, and only on `decreaseKey`-heavy workloads. **Unverified:** I have not re-confirmed a specific published benchmark for this note; the Larkin–Sen–Tarjan experimental study of priority queues, or a DIMACS shortest-path challenge report, would settle it with numbers.

</details>

---

## Open questions

1. **Fibonacci and pairing heap performance (leaf 3.5.20).** The claim that array binary heaps beat Fibonacci heaps in practice for Dijkstra is stated as the settled consensus of the algorithms-engineering literature, and the *reasons* given (node size, pointer-chasing, amortised-versus-worst-case, implementation intricacy) are structural and verifiable from the algorithms themselves. But no specific benchmark's numbers are reproduced here, because none was re-confirmed against its source. *Would settle it:* the Larkin, Sen and Tarjan experimental study of priority queues, or a DIMACS Implementation Challenge shortest-path report with per-structure timings on named graphs.

---

**Leaves covered:** 3.5.14–3.5.20 (7 leaves)
**Leaves deferred:** none
**Diagrams included:** none new — `removeAt`/`forgetMeNot` and D-84 are covered in [01b-internals-removeat-and-iteration.md](01b-internals-removeat-and-iteration.md)
**Target version:** Java 21 LTS
**Lines:** 506
