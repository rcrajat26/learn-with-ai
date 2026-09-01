# 03 — Concurrency & JVM

**What this decides:** how much concurrency runway the plan needs (it currently
assumes refresher-level), and whether JVM debugging/profiling needs a dedicated
track. At L4/L5 loops, concurrency questions are common for Java candidates.

---

## Part A — Concurrency ladder

### Q1 [L1] explain-back — Process vs thread
**Strong answer:** process = isolated memory space; threads share the
process's heap but have own stacks; thread creation/context-switch cheaper;
shared memory is why synchronization exists.

### Q2 [L1] explain-back — What is a race condition?
Give a concrete example with two threads and `counter++`.
**Strong answer:** `counter++` is read-modify-write (3 steps); interleaving
loses updates. Must decompose the increment; "two threads access the same
variable" alone is 0.5.

### Q3 [L2] explain-back — `synchronized` vs `volatile`
What does each guarantee? When is `volatile` alone enough?
**Strong answer:** `synchronized` = mutual exclusion + visibility (happens-
before on monitor exit/enter); `volatile` = visibility + ordering only, NO
atomicity — enough for a status flag written by one thread, not for
`counter++`. Bonus: mentions happens-before by name.

### Q4 [L2] explain-back — Thread lifecycle + pools
Why thread pools instead of `new Thread()` per task? What are the key
`ThreadPoolExecutor` parameters and what happens when the queue fills?
**Strong answer:** creation cost + unbounded thread risk; core/max pool size,
queue, rejection policy; the trap: with an unbounded queue, maxPoolSize never
kicks in. Sizing intuition: CPU-bound ≈ cores; I/O-bound ≈ cores × (1 + wait/compute).

### Q5 [L3] spot-the-bug — Check-then-act
```java
private final Map<String, User> cache = new ConcurrentHashMap<>();
User get(String id) {
    if (!cache.containsKey(id)) {
        cache.put(id, loadUser(id));   // expensive
    }
    return cache.get(id);
}
```
**Strong answer:** ConcurrentHashMap makes individual ops atomic, but
check-then-act is a compound action — two threads can both miss and both
load. Fix: `computeIfAbsent(id, this::loadUser)`. Bonus: knows
`computeIfAbsent` blocks other writers to that bin — long `loadUser` inside
it has its own cost. The "concurrent collection ≠ compound-action safety"
insight is the whole point.

### Q6 [L3] spot-the-bug — Deadlock
```java
void transfer(Account from, Account to, long amt) {
    synchronized (from) { synchronized (to) {
        from.debit(amt); to.credit(amt);
    }}
}
```
**Strong answer:** transfer(A,B) and transfer(B,A) concurrently → lock-order
deadlock. Fixes: global lock ordering (e.g., by account id), `tryLock` with
timeout, or a single lock per pair. Must name lock *ordering* as the fix.

### Q7 [L3] predict-output — CompletableFuture
```java
CompletableFuture<String> f = CompletableFuture
    .supplyAsync(() -> { throw new RuntimeException("boom"); })
    .thenApply(s -> s + "!");
f.thenAccept(System.out::println);
Thread.sleep(100);
```
What prints? How would you handle the error?
**Strong answer:** nothing prints — the exception flows past `thenApply`/
`thenAccept` (they're skipped on exceptional completion) and is swallowed
because nobody calls `join`/`get`/`exceptionally`. Handle with
`exceptionally`, `handle`, or `whenComplete`. Swallowed-exception awareness
is the discriminator.

### Q8 [L4] scenario — Design a bounded work queue
"Producer threads submit jobs; consumers process them; producers must slow
down when consumers can't keep up. What do you reach for and what are the
knobs?" **Strong answer:** `BlockingQueue` (`ArrayBlockingQueue`) — `put`
blocks when full = backpressure; or executor with bounded queue +
`CallerRunsPolicy`. Knobs: queue size, what "full" behavior should be (block
vs reject vs shed). Bonus: contrasts with unbounded queue → OOM under burst.

### Q9 [L4] discriminator — Atomics and beyond
"When `AtomicLong` vs `synchronized` vs `LongAdder`? What's CAS and when
does it perform badly?"
**Strong answer:** CAS = compare-and-swap, lock-free retry loop; AtomicLong
fine at low contention; under high contention CAS retry-storms → LongAdder
(striped cells) for counters where reads are rare; `synchronized` for
compound invariants that CAS can't express. Naming contention as the axis = L4.

---

## Part B — JVM ladder

### Q10 [L1] explain-back — JVM memory areas
Heap vs stack vs metaspace — what lives where? What error does each overflow
produce? **Strong answer:** objects → heap (shared); frames/locals →
per-thread stacks (`StackOverflowError`); class metadata → metaspace. Heap
exhaustion → `OutOfMemoryError: Java heap space`. Bonus: thread-count OOM.

### Q11 [L2] explain-back — GC basics
Why generational GC? What's a stop-the-world pause? What GC does your service
run right now (do you know)?
**Strong answer:** generational hypothesis (most objects die young) → cheap
young collections; STW = all app threads paused; G1 default since Java 9.
Honest "I don't know what we run in prod" is fine — record it; it feeds the
observability gap.

### Q12 [L3] scenario — Memory leak
"Heap usage climbs over days, full GCs get longer, eventually OOM. What are
your concrete steps and tools?"
**Strong answer:** confirm with GC logs / heap metrics; take a heap dump
(`jcmd GC.heap_dump` / `-XX:+HeapDumpOnOutOfMemoryError`); analyze with
MAT/VisualVM — dominator tree, biggest retained sets; usual suspects: static
collections/caches without eviction, listener registration, ThreadLocals in
pools. Score by tool-concreteness: "look at the code for leaks" = 0.
**This question most directly tests the JVM-debugging gap.**

### Q13 [L4] scenario — 100% CPU in prod
"A JVM service is pinned at 100% CPU. First 10 minutes — exact commands/steps."
**Strong answer:** `top -H -p <pid>` to find hot thread(s) → convert TID to
hex → `jstack <pid>` / `jcmd Thread.print` → match nid → read what that
thread is doing; repeat dumps to see if it moves. Distinguish: busy app code
vs GC threads (→ memory problem wearing a CPU costume) vs spin loops. Bonus:
async-profiler flame graph. Score 1 only with the thread-dump correlation
workflow; "check monitoring" alone = 0.5.

### Q14 [L4] discriminator — Virtual threads (Java 21 awareness probe)
"What problem do virtual threads solve, and where do they NOT help?"
**Strong answer:** cheap threads for I/O-bound blocking code (thread-per-
request without pool exhaustion); don't help CPU-bound work; pinning issue
with `synchronized` around blocking calls (improved in 24+, but knowing the
concept counts). L0–L1 here is expected and fine — it calibrates Week 15,
Day 71 pacing.

---

## Breadth checklist (rate 0–3)

- [CORE] `ExecutorService` — submit vs execute, shutdown vs shutdownNow, Future.get
- [CORE] `ConcurrentHashMap` vs `Collections.synchronizedMap` vs `HashMap` — real differences
- [CORE] Immutability as a concurrency strategy (can you articulate it?)
- [CORE] Reading a stack trace fluently (caused-by chains, suppressed)
- wait/notify (legacy but asked); why loops around wait
- `ReentrantLock` vs synchronized — tryLock, fairness, condition variables
- `ThreadLocal` — uses and the thread-pool leak trap
- `CountDownLatch` / `Semaphore` / `CyclicBarrier` — recognize each's shape
- Happens-before — could you define it?
- Daemon vs user threads; what keeps a JVM alive
- JIT compilation — heard of C1/C2/tiered? (0–1 fine)
- GC tuning flags — ever touched -Xmx/-Xms? Know what they set?
- jcmd / jstack / jmap / jstat — which have you ever run?
- Flame graphs / async-profiler — heard of? used?
- False sharing / CPU caches (L4 bonus territory — 0 is fine)
