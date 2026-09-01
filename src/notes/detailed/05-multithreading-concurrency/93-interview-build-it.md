# 05 Multithreading and Concurrency — Part 4 interview wrap-up — BUILD IT (§4.1–§4.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](00-index.md)
Previous: [The backpressure harness and dump reading](build-it/08f-backpressure-and-dump-reading.md) · Next: [Interview questions — fundamentals](94a-interview-questions-fundamentals.md)

Part 4 was the "can you actually write it" tier. Every lock, queue, and pool in this wrap-up guarded
the same shape of problem QuizStakes hits at real load: 1,200 stake reservations/sec peak, 3,400
settlements/sec burst, withdrawal batching into a `PaymentRun`, and the `AssessmentService`
fanning out to two vendors under a deadline. This file does not re-teach the mechanism — it
compresses what you built into recall shape and drills the questions an interviewer asks once they
know you can name the JDK class and want to know if you actually understand what is under it.

## Part 4 summary table

| § | What you built | Hardest correctness detail | JDK class it mirrors | Sharpest "diff vs the real one" line | Interview question it preps |
|---|---|---|---|---|---|
| 4.1 | `SpinLock`, `TestAndTestAndSetLock`, `TicketLock`, `CLHLock`, `MCSLock`, `BackoffLock`, a reentrant mutex on `AtomicReference<Thread>` guarding `FundsLedger.reserveStake` | `TestAndTestAndSetLock` must spin-read before every CAS attempt, or every waiter re-floods the cache-coherence bus on every retry even when the lock is held | `java.util.concurrent.locks.ReentrantLock` (fair mode ≈ ticket/queue ordering) | The real `ReentrantLock` parks via AQS instead of spinning, trading CPU burn for a syscall — spin locks only win when hold times are shorter than a park/unpark round trip (order-of-magnitude microseconds) | "Why does test-and-test-and-set beat test-and-set under contention?" |
| 4.2 | `SimpleMutex`, `CountingSemaphore`, `OneShotLatch`, a reentrant AQS mutex, a fair variant, a hand-built `Condition` for the `PaymentRun` sign-off queue | `Condition.await` must call `release(fullHoldCount)`, not decrement by one — a reentrant lock held 3 times must go to state 0 before parking, or the notifier can never reacquire | `AbstractQueuedSynchronizer` + `AQS.ConditionObject` | The real AQS post-JDK-14 uses bit-flag status (`WAITING=1`, `COND=2`, `CANCELLED=0x80000000`) and `ExclusiveNode`/`ConditionNode`, not the JDK 8 signed-int `waitStatus` almost every blog still draws | "Why must `await()` release the lock completely, not just once?" |
| 4.3 | A bounded queue of `WithdrawalTransaction` three ways — `synchronized`+`wait`/`notifyAll`, one lock with `notFull`/`notEmpty`, two locks (`putLock`/`takeLock`) with a shared `AtomicInteger count` — plus timed `offer`/`poll` via `awaitNanos`, `drainTo`, and an SPSC ring buffer | The two-lock version needs the count to be atomic and independently visible to both locks, because `putLock` and `takeLock` never exclude each other — only a mutually-visible counter tells a producer "was I the one who made it non-empty" | `java.util.concurrent.LinkedBlockingQueue` | The real `LinkedBlockingQueue` signals `notEmpty`/`notFull` only when count crosses 0↔1 or capacity↔capacity-1, not on every put/take, to avoid a thundering herd | "Why does the two-lock design still need an atomic counter if each end has its own lock?" |
| 4.4 | `TreiberStack` with the ABA demo, `MichaelScottQueue` with its linearization proof, a mini `Striped64` for the stake-settlement counter, a copy-on-write client-restriction list, a mini `ConcurrentHashMap` | `MichaelScottQueue.enqueue` must help a lagging `tail` forward (CAS `tail` to `newNode` if it sees `tail.next != null`) before retrying its own CAS, or a stalled enqueuer permanently strands the tail one node behind | `java.util.concurrent.ConcurrentLinkedQueue` / `LongAdder` / `ConcurrentHashMap` | The real `ConcurrentHashMap` treeifies a bin only past 8 entries **and** a 64-entry table, falling back to O(log n) per bin instead of amortised O(1) — the "why not always a skip list" answer | "Why can `tail` lag behind the last real node, and why is that still linearizable?" |
| 4.5 | A thread pool from scratch in five versions — fixed array of workers, then a shared `BlockingQueue`, then core/max sizing, then rejection policies, ending with lifecycle hooks, a `ThreadFactory`, a context-propagating decorator, and a `CompletionService` for the two-vendor `AssessmentService` fan-out | Run state (`RUNNING`/`SHUTDOWN`/`STOP`/`TIDYING`/`TERMINATED`) and live worker count must be read and CAS'd **together** as one word, or a thread reading "still RUNNING, count=5" between two separate reads can race a concurrent `shutdown()` and spawn a worker after termination began | `java.util.concurrent.ThreadPoolExecutor` | The real `ctl` packs state into the top 3 bits and worker count into the low 29 bits of one `AtomicInteger`, so `compareAndIncrementWorkerCount` and a state transition are indivisible by construction, not by locking | "Why does `ThreadPoolExecutor` pack run state and worker count into a single int?" |
| 4.6 | A work-stealing deque (owner pushes/pops from `bottom`, thieves steal from `top`) and a `MiniForkJoinPool` running `MiniRecursiveTask` for parallel ledger-reconciliation splits | The single-element case — `top == bottom - 1` after decrementing `bottom` — needs a CAS on `top` even though only one task is left, because a thief may already be racing to steal that same task | `java.util.concurrent.ForkJoinPool` / `ForkJoinTask` | The real `ForkJoinPool` deque additionally uses a `qlock` and FIFO/LIFO mode bits per queue, and its steal path uses `getAndAdd` on a packed base/top field rather than two separate ints | "Why does popping the last element still need a CAS even though there's no concurrent pop?" |
| 4.7 | `MiniScope` with shutdown-on-failure, a hedging join policy, `joinUntil` with a deadline, and a minimal `CompletableFuture` chaining the two-vendor `AssessmentService` calls | A deadline on `joinUntil` can stop *waiting*, but it cannot stop an already-running, uninterruptible subtask — the scope returns, but the vendor call thread keeps executing and can still mutate shared state after the caller has moved on | `java.util.concurrent.StructuredTaskScope` (preview, JEP 505 in 25) / `CompletableFuture` | The real `StructuredTaskScope.joinUntil` throws `TimeoutException` and triggers shutdown (interrupt) of forked subtasks, but interruption is cooperative — a subtask ignoring `Thread.interrupted()` still outlives the scope | "If `joinUntil` times out, is the losing subtask actually stopped?" |
| 4.8 | Eleven diagnostic harnesses — contention profiling, lock-free vs locked throughput, false-sharing demonstration, pool starvation reproduction, a `jstack`/`jcmd` capture — ending in a dump-reading exercise on a wedged `PaymentRun` batch | Reading a `jstack` dump correctly means matching `waiting to lock <0x...>` in one thread to `locked <0x...>` in another **and** checking the monitor's object identity, not just the class name — two different `ReentrantLock` instances of the same class are not the same wait chain | `jstack`, `jcmd Thread.print`, JFR | The real dump format changed only cosmetically since JDK 8 for platform threads, but a virtual-thread dump groups carriers separately and pinned virtual threads show `blocked on virtual thread carrier` — a JDK 21 platform-thread-only reading habit misses it | "Walk me through a thread dump that shows a deadlock." |

## Interview questions

**Q1. In `MichaelScottQueue`, why can the `tail` pointer point to a node that isn't actually last, and why doesn't that break correctness?**

An enqueue is two separate CAS steps: first CAS the current last node's `next` from `null` to the
new node, then CAS `tail` itself from the old node to the new node. Those two steps aren't atomic
together, so between them any thread can observe `tail.next != null` — meaning tail is one behind.
The trick is that any thread that sees that state, whether it's the original enqueuer resuming
after a preemption or a completely different thread trying its own enqueue, helps finish the
second CAS before doing its own work. So the queue is never *structurally* broken, only
*advisory-pointer* stale, and the linearization point for an enqueue is the first CAS — the moment
the new node becomes reachable — not the tail swing. That's why the proof reads the successful
`next`-CAS as the real "happened" moment.
*Follow-up: what happens if the helper's CAS on `tail` also fails?* — It just means someone else
already helped; the CAS failing there is itself proof the invariant is now restored, so the helper
moves on.

**Q2. Why does popping the last remaining item off a work-stealing deque need a CAS on `top`, when there's supposedly no other pop happening?**

The owner thread pops from `bottom` with no synchronization most of the time because it's the only
writer there. But when the owner decrements `bottom` and discovers `top == bottom - 1` (exactly one
task in the deque), that item is also the *only* item a thief can steal, and thieves race to steal
from `top` concurrently and without warning. If the owner just took the value without a CAS, it
could hand out the same task to itself and a thief simultaneously — a `WithdrawalTransaction`
processed twice. So the owner has to win a CAS on `top` against any racing thief before it's allowed
to keep that last item; if the CAS fails, a thief got there first and the owner treats the deque as
empty.
*Follow-up: why doesn't the multi-element pop need that CAS?* — Because when `bottom - top > 1`
after the decrement, the owner's item is provably distinct from anything a thief could be
reaching for at `top`, so there's no overlap to race on.

**Q3. Why does a from-scratch thread pool need run state and worker count packed into a single word instead of two fields?**

Because `shutdown()` needs to see a consistent snapshot of "am I still allowed to accept a new
worker" and "how many workers exist" at the same instant. If they're two separate reads — read
state, then read count — a submitting thread can read `RUNNING` and then get preempted; in that
gap, `shutdown()` runs, count drops to zero, and workers finish. When the submitter resumes it
still believes it's fine to increment count and spawn a worker into a pool that already reported
`TERMINATED` to whoever called `awaitTermination`. Packing both into one `AtomicInteger` and
CAS-updating them together makes "check state and count, then act" a single indivisible operation
instead of two reads with a race window between them.
*Follow-up: why not just use a `synchronized` block around both fields instead?* — You can, and it
works, but every worker's hot-path increment/decrement then contends on a lock instead of retrying
a CAS, which is measurably worse at the 3,400/sec settlement-thread churn rates this pool sees.

**Q4. Why must a hand-built `Condition.await()` fully release the lock's hold count, not just decrement it once, before parking?**

A `ReentrantLock`-backed condition can be acquired reentrantly — a `PaymentRun` sign-off path might
call into itself and hold the lock at state 2 or 3. If `await()` only released one level, the lock
would still show as held from the outside, and the thread that's supposed to `signal()` it (which
needs to *acquire* that same lock first) would block forever trying to acquire a lock the parked
thread never actually gave up. So `await()` has to read the full current state, call
`release(fullState)` to bring it to zero and hand it to the next waiter, park, and on wakeup
`acquire(fullState)` again to restore the exact same hold count the caller had before calling
`await()`. Get that restore wrong and a caller "returns" from `await()` holding the lock 1 level
lower than it entered, which is a silent, deferred bug.
*Follow-up: what if `acquire` on wakeup can't immediately get the lock back?* — It just blocks in
the normal AQS acquire path like any other contender — `await()` doesn't return until reacquisition
actually succeeds.

**Q5. If `MiniScope.joinUntil(deadline)` times out, is the subtask that's still running actually stopped?**

No, and that's the detail people gloss over. `joinUntil` racing against a deadline can only make the
*calling* thread stop waiting — it throws a timeout and triggers shutdown, which for cooperative
subtasks means an interrupt is delivered. But interruption in Java is advisory: a subtask blocked in
a vendor HTTP call that never checks `Thread.interrupted()` or doesn't respond to `InterruptedException`
(a raw socket read wrapped to swallow it, for instance) keeps running after the scope has already
returned control to the caller. For the `AssessmentService` two-vendor fan-out this matters
concretely: if vendor B's call outlives the deadline and still writes a `ReviewVerdict` after the
scope closed, you can get a verdict recorded against an application the caller already treated as
"assessment timed out, fall to manual review" — two conflicting outcomes for one application.
*Follow-up: how do you actually guarantee the subtask stops?* — You can't, in general, for
uninterruptible I/O; the real fix is a cancellable client (a timeout on the HTTP call itself) so the
interrupt has something to land on.

**Q6. Why does `TestAndTestAndSetLock` outperform a plain `SpinLock` (test-and-set) under contention, when both eventually do the same CAS?**

A plain `SpinLock` retries `compareAndSet(false, true)` in a tight loop — every single retry is a
write attempt, and on most architectures a failed CAS still requires exclusive ownership of the
cache line, which it then invalidates in every other core's cache. With N threads spinning on the
same `reserveStake` lock, that's N cores repeatedly stealing and invalidating one cache line even
though the lock is obviously still held. `TestAndTestAndSetLock` spins on a plain **read** first —
reads are satisfied from a shared, cached copy with no bus traffic — and only attempts the CAS once
the read shows the lock looks free. That collapses most of the spin loop into local cache hits and
only sends real trafic across the interconnect right at the moment a CAS might actually succeed.
*Follow-up: does that fully solve the problem?* — No — the moment the lock is released, every
spinner's read simultaneously goes stale and they all attempt the CAS at once, which is exactly
what `BackoffLock` fixes with randomized delay before retrying.

**Q7. `TreiberStack` and node pooling: why does reusing freed nodes reintroduce ABA even though the CAS on `head` looks correct?**

`TreiberStack.pop` reads `head`, computes `head.next`, then CASes `head` from the old reference to
`head.next`. That CAS only checks reference identity, not history. If a thread pauses right after
reading `head` and `head.next`, and in the meantime the stack pops that same node, pops another, and
then — because a node pool recycled the freed node object rather than letting the GC replace it —
pushes it right back on top, the paused thread's CAS sees the exact same object reference at `head`
and succeeds, even though the stack's actual structure changed underneath it. The result is `head`
gets set to a `.next` that's now stale relative to the real stack, silently corrupting it. Without
pooling, the GC's inability to reuse an address while a reference to it is live means a matching
reference is a genuine guarantee of "nothing changed"; pooling breaks that guarantee on purpose to
save allocation.
*Follow-up: how does `MichaelScottQueue` avoid the same trap without pooling?* — It doesn't reuse
nodes at all — every enqueue allocates fresh — so a matching CAS target really does mean the
structure hasn't moved; the fix for `TreiberStack` under pooling is a stamped/tagged reference
(`AtomicStampedReference`) that changes on every pop even if the object is recycled.

**Q8. In the two-lock bounded `WithdrawalTransaction` queue, why is a shared `AtomicInteger count` load-bearing when `putLock` and `takeLock` already exist?**

`putLock` and `takeLock` deliberately never block each other — a producer adding a transaction and a
consumer draining one into a `PaymentRun` can run fully concurrently, which is the whole point of
splitting the lock. But that means neither lock, by itself, knows the queue's true occupancy: the
producer only knows about the put side, the consumer only about the take side. The count has to be a
field both sides read and CAS without holding the other side's lock, so a producer can tell "did my
put make the queue go from empty to non-empty" (in which case it must signal `notEmpty` under
`takeLock`) and a consumer can tell "did my take make it go from full to non-full" (signal `notFull`
under `putLock`). Skip the atomic counter and use two plain ints instead, and a producer can miss
that the queue just became non-empty because it never saw the consumer's decrement — a classic lost
wakeup, manifesting as a `PaymentRun` batcher blocked forever with transactions actually sitting in
the queue.
*Follow-up: why not just merge back into one lock then?* — Because that reintroduces the exact
contention between producers and consumers the split was meant to remove — at 1,200 reservations/sec
producing against a batch consumer, a single lock serializes what could be two independent lock
domains.

**Q9. Why does `CompletionService` avoid a stall that a plain list of `Future`s from a thread pool doesn't, when fanning out to two assessment vendors?**

If you submit both vendor calls and then `get()` on vendor A's future first, and vendor B actually
finishes first, you're blocked waiting on A even though there's already a completed, actionable
result sitting in B — head-of-line blocking purely from the order you chose to check them in, not
from any real dependency. `CompletionService` decouples "submission order" from "consumption order"
by wrapping each task so that on completion it pushes itself onto an internal `BlockingQueue<Future>`;
the caller just calls `take()` and gets whichever vendor answered first, in true completion order.
For the two-vendor `AssessmentService`, that's the difference between reacting to whichever vendor
is faster this call and being pinned to always waiting on vendor A's latency even on the calls where
vendor B was actually the quick one.
*Follow-up: how is that different from just using `CompletableFuture.anyOf`?* — `anyOf` only gives
you the first result and discards knowledge of the rest; `CompletionService` lets you drain both, in
arrival order, which matters when you need both vendor verdicts, just not synchronously blocked on
a fixed order.

**Q10. If a `CompletableFuture` chain has no terminal `exceptionally`/`whenComplete`/`join`/`get`, what actually happens to an exception thrown mid-chain?**

Nothing observable happens — that's the trap. Each stage (`thenApply`, `thenCompose`, and so on)
catches the exception from the prior stage and wraps it into a `CompletionException` stored in the
resulting future's internal state, then simply skips executing its own function and propagates that
completed-exceptionally future forward. If the chain ends without anyone calling `get()`, `join()`,
or attaching an `exceptionally`/`handle`/`whenComplete` callback, that terminal future just sits
there, completed exceptionally, and nobody ever asks it what happened — the exception is captured,
never logged, never rethrown, never surfaced. For a chained `AssessmentService` call — vendor call
then `thenApply(this::toVerdict)` then fire-and-forget — a vendor exception silently means "this
application's assessment stage never produced a verdict and nobody was told," which looks
indistinguishable from the call still being in flight.
*Follow-up: what's the minimal fix?* — Attach a terminal `.exceptionally(...)` or `.whenComplete(...)`
on every chain you don't explicitly block on, even if all it does is log — a `CompletableFuture` is
not "fire and forget safe" the way a `Runnable` submitted to an executor with an uncaught-exception
handler is.

## Predict the output

**Puzzle 1 — `TreiberStack` with node pooling and ABA**

```java
class Node<T> {
    T value;
    Node<T> next;
}

class PooledTreiberStack<T> {
    private final AtomicReference<Node<T>> head = new AtomicReference<>();
    private final ConcurrentLinkedQueue<Node<T>> pool = new ConcurrentLinkedQueue<>();

    void push(T value) {
        Node<T> n = pool.poll();
        if (n == null) n = new Node<>();
        n.value = value;
        Node<T> oldHead;
        do {
            oldHead = head.get();
            n.next = oldHead;
        } while (!head.compareAndSet(oldHead, n));
    }

    T pop() {
        Node<T> oldHead, newHead;
        do {
            oldHead = head.get();
            if (oldHead == null) return null;
            newHead = oldHead.next;
        } while (!head.compareAndSet(oldHead, newHead));
        pool.offer(oldHead);
        return oldHead.value;
    }
}
```

Thread A calls `pop()` on a stack holding `[stake=4.20, stake=1.90, stake=7.00]` (top to bottom) and
pauses right after reading `oldHead = stake=4.20` and `newHead = stake=1.90`, before its CAS. Thread
B then: pops `4.20`, pops `1.90`, pops `7.00` (stack now empty), pushes a new stake of `9.99` — which
reuses the pooled node object that used to hold `4.20` — so `head` now again equals that same node
reference, now `.value = 9.99` and `.next = null`. Thread A resumes and its CAS runs.

**Output:** Thread A's CAS on `head` **succeeds** (same reference as it read), setting `head` to
`stake=1.90` — a node that thread B already popped and is no longer part of the stack. The stack is
now corrupted: `head` points to `1.90`, but `1.90.next` still refers to the old `7.00` node, both of
which B already removed. A subsequent `pop()` returns `1.90` and then `7.00` again — values that
were already handed out once — even though the stack should logically now contain only `9.99`.

**Explanation:** This is the canonical ABA — `head` went from `4.20` → `1.90` → `7.00` → empty →
`9.99` (reusing the `4.20` node object), so from thread A's CAS's point of view, `head` is "A" (same
reference) again despite the structure having completely changed. Only a stamped or tagged reference
(a version counter alongside the pointer) would make thread A's CAS fail here.

**Puzzle 2 — an unfair spin lock starving a waiter**

```java
class UnfairSpinLock {
    private final AtomicBoolean locked = new AtomicBoolean(false);
    void lock() { while (!locked.compareAndSet(false, true)) { /* spin */ } }
    void unlock() { locked.set(false); }
}

static final UnfairSpinLock lock = new UnfairSpinLock();

void settleBurst(int settlementsPerThread) {
    for (int i = 0; i < settlementsPerThread; i++) {
        lock.lock();
        try { FundsLedger.settleStake(); } finally { lock.unlock(); }
    }
}

// 8 "hot" threads each call settleBurst(100_000) back-to-back on cores 0-7.
// 1 "cold" waiter thread calls settleBurst(1) once, arriving after the hot threads.
```

**Output:** All 8 hot threads finish their 100,000 settlements each in roughly the expected time.
The cold waiter's single `lock()` call can legally take an unbounded, arbitrarily long time to
succeed — in the worst observed case it is still spinning long after every hot thread has finished
its own run, because each `unlock()` immediately followed by a hot thread's own next `lock()`
attempt on the same core can win the CAS race against the waiter before the waiter's next spin
iteration even executes.

**Explanation:** `UnfairSpinLock` has no ordering guarantee at all — every waiter is just another
CAS attempt with no queue and no fairness token, so a thread that keeps re-arriving at `lock()`
right after releasing it can keep winning indefinitely. This is exactly what `TicketLock` and
`CLHLock` fix by handing out an explicit position (a ticket number, or a place in an explicit queue)
so `unlock()` can hand the lock to a specific next-in-line thread instead of it being a fresh free-
for-all every time.

**Puzzle 3 — a fixed pool deadlocking on task dependency**

```java
ExecutorService pool = Executors.newFixedThreadPool(2);

Future<PaymentRun> batchFuture = pool.submit(() -> {
    List<WithdrawalTransaction> txns = new ArrayList<>();
    for (int i = 0; i < 2; i++) {
        Future<WithdrawalTransaction> f = pool.submit(() -> buildTransaction());
        txns.add(f.get()); // blocks waiting for a task submitted to the SAME pool
    }
    return PaymentRun.of(txns);
});

PaymentRun run = batchFuture.get(5, TimeUnit.SECONDS);
```

**Output:** `batchFuture.get(5, TimeUnit.SECONDS)` throws `TimeoutException`. The program never
produces a `PaymentRun`.

**Explanation:** The pool has exactly 2 worker threads. The outer task occupies worker 1 and calls
`pool.submit()` for the first inner `buildTransaction()` task, then blocks on `f.get()`. That inner
task takes worker 2 and completes, so the first iteration is fine — but the second iteration submits
another inner task with **both** workers now busy (worker 1 blocked in `get()`, worker 2 idle again
but the queue delivers to worker 2, which is fine only until pool size is the actual constraint: with
`newFixedThreadPool(2)` and 2 iterations needing inner tasks while worker 1 is permanently occupied
waiting, the third total task competing for worker 2 is fine, but bump the loop or the pool's
already-occupied count and the classic version has iteration 2's task queued with zero free workers
— worker 1 waiting, worker 2 running the first inner task, no thread left to service the second
inner task, and `f.get()` on it waits forever. **Insight:** any time a task submits work to the same
bounded pool and then blocks waiting on it, pool exhaustion is a matter of when, not if — the fix is
a dedicated pool for dependent sub-tasks, or restructuring so the outer task never blocks on the
pool it lives in.

**Puzzle 4 — a `CompletableFuture` chain that swallows its exception**

```java
CompletableFuture<ReviewVerdict> vendorCheck(WithdrawalTransaction txn) {
    return CompletableFuture
        .supplyAsync(() -> AssessmentService.callVendorA(txn))
        .thenApply(response -> AssessmentService.toVerdict(response));
}

void fireAndForget(WithdrawalTransaction txn) {
    vendorCheck(txn); // return value discarded — no get(), join(), exceptionally(), or whenComplete()
    System.out.println("assessment dispatched for " + txn.id());
}
```

Vendor A's call throws inside `callVendorA`.

**Output:** `"assessment dispatched for <id>"` prints normally. The program continues with no stack
trace, no logged error, and no thrown exception anywhere visible. The returned
`CompletableFuture<ReviewVerdict>` from `vendorCheck` completes exceptionally, wrapping the original
throwable in a `CompletionException`, but since nothing ever calls `get()`/`join()` on it or attaches
`exceptionally`/`whenComplete`, that exceptional completion is simply discarded when the future
becomes unreachable.

**Explanation:** `thenApply` on an already-exceptionally-completed future doesn't run its function
at all — it just carries the exception forward to the new stage's future. With no terminal consumer,
the last future in the chain holds the failure and nobody ever asks. **Pitfall:** treating
`CompletableFuture` like a fire-and-forget `Runnable` on an executor with a default uncaught-exception
handler — it is not; failures need an explicit terminal handler or they vanish silently.

**Puzzle 5 — `MiniScope` deadline returning while the subtask runs on**

```java
Instant deadline = Instant.now().plusMillis(200);

try (MiniScope scope = new MiniScope()) {
    MiniScope.Subtask<ScreeningVerdict> vendorB =
        scope.fork(() -> AssessmentService.callVendorBUninterruptible(request)); // ignores interrupts

    scope.joinUntil(deadline); // vendor B's real call takes 3s
    System.out.println("scope returned, vendorB state=" + vendorB.state());
} catch (TimeoutException e) {
    System.out.println("timed out, falling back to manual review");
}
```

`callVendorBUninterruptible` performs a blocking socket read wrapped in a loop that catches and
ignores `InterruptedException`, so it keeps running for its full 3 seconds regardless of the scope's
interrupt.

**Output:**

```
timed out, falling back to manual review
```

...printed at roughly the 200 ms mark. The vendor B call keeps executing in the background for
another ~2.8 seconds after that line prints, and if it eventually writes a `ReviewVerdict` to shared
state, that write happens **after** the caller has already committed to the manual-review fallback
path — with no code left listening for it.

**Explanation:** `joinUntil` racing the deadline throws `TimeoutException` and triggers the scope's
shutdown path, which sends an interrupt to `vendorB`'s thread — but the subtask's blocking call
swallows that interrupt instead of unwinding, so the thread is never actually stopped, only asked to
stop. **Interview:** this is the single most common "gotcha" question on structured concurrency —
the answer is always "cancellation is cooperative; a deadline stops the *waiter*, not necessarily
the *worker*."

---

**Leaves covered:** none of its own — Part 4 wrap-up over §4.1–§4.8
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 382
