# Concurrency Primer — targeted at the E1/E2 misses

Scope: exactly what papers E1 Q5–Q6 and E2 Q5–Q6 tested and what E3–E5 will
retest. ~2–3 hours. Read actively: after each block, close the file and
explain it aloud. The papers verify; this teaches.

## 1. Process vs thread (E1 Q5 — answered backwards)

A **process** is a running instance of a program with its own isolated
virtual memory space (its heap, its file handles, its address space). The
OS guarantees process A cannot read process B's memory.

A **thread** is an execution unit *inside* a process — a call stack plus a
program counter that the OS scheduler runs on a core.

**What threads of one process share vs own:**

| Shared (one per process) | Private (one per thread) |
|---|---|
| Heap — ALL objects, `static` fields | Stack — local variables, call frames |
| Loaded classes, method area | Program counter |
| Open files, sockets | Thread-local storage |

Memorize the asymmetry: **share the heap, own your stack.** Every
concurrency bug lives in the shared part; locals are automatically safe.
That's also why a `Runnable`'s local variables need no synchronization but
a field it touches does.

## 2. Why race conditions happen (E1 Q6 — mechanism missing)

`counter++` is three operations, not one:

```
1. read  counter        (load from heap into register)
2. add   1
3. write counter        (store back to heap)
```

Two threads both at step 1 read `5`; both write `6`; one increment is lost
forever. Any **read–modify–write** or **check-then-act** compound is a race
window. The one-liner to keep: *"individual steps can be atomic; the
COMPOUND isn't, and the scheduler can interleave between any two steps."*

## 3. `synchronized` — both guarantees (E2 Q6 — you had one of two)

`synchronized` on a method/block acquires the monitor lock of an object:

1. **Mutual exclusion** — at most one thread inside any block synchronized
   on the SAME object (note: it's per-object monitor, not per-method).
2. **Visibility** — everything a thread wrote before RELEASING the monitor
   is guaranteed visible to the next thread that ACQUIRES it
   (a *happens-before* edge).

Guarantee 2 is the one everyone forgets. Without synchronization there is
no promise a write on thread A is EVER seen by thread B — caches and
compiler reordering are allowed to hide it.

**`volatile`** (E5 will test this): gives you guarantee 2 only —
visibility, no mutual exclusion. Right for a `volatile boolean running`
stop-flag; wrong for `counter++` (still a compound). For a lone counter,
`AtomicInteger.incrementAndGet()` does the read-modify-write atomically
via CAS.

## 4. Thread pools / ExecutorService (E2 Q5 — "not aware")

Creating a `new Thread()` per task is bad for two reasons:

1. **Cost** — thread creation/destruction is expensive (OS call, ~1MB
   stack allocation). A pool creates threads once and reuses them across
   thousands of tasks.
2. **No bound** — traffic spike → 50,000 threads → memory exhaustion and
   scheduler collapse. A pool caps concurrency at a number you chose.

```java
ExecutorService pool = Executors.newFixedThreadPool(8);
pool.submit(() -> handle(job));        // queues if all 8 busy
pool.shutdown();                        // finish queued work, then stop
```

Mental model: a pool = **N worker threads + a task queue**. Tasks beyond N
wait in the queue instead of becoming new threads. Sizing intuition:
CPU-bound work → ≈ number of cores; I/O-bound → more (threads mostly wait).

`Future<T> f = pool.submit(callable)` — `f.get()` blocks until the result
is ready. That's the whole submit/collect loop.

## 5. Thread lifecycle (E5 retests this)

NEW → RUNNABLE → (BLOCKED | WAITING | TIMED_WAITING) → TERMINATED

- **BLOCKED**: wants a monitor another thread holds (stuck at
  `synchronized`).
- **WAITING**: parked itself on purpose — `wait()`, `join()`,
  `LockSupport.park()` — until another thread signals.
- Calling `start()` runs `run()` on a NEW thread; calling `run()` directly
  is just a normal method call on the CURRENT thread (E4 retests this).

## 6. Deadlock (E3 retests this)

Two threads, two locks, opposite order:

```
T1: lock A ─── waits for B
T2: lock B ─── waits for A        → both wait forever
```

Four conditions must ALL hold (mutual exclusion, hold-and-wait, no
preemption, circular wait). The standard fix kills circular wait: **always
acquire locks in one global order** (e.g., lower account-id first). The
transfer(A,B)/transfer(B,A) example is the canonical interview question.

## 7. Heap/stack errors (E3 retests this)

- Runaway recursion → each call adds a stack frame → **StackOverflowError**
  (per-thread stack).
- Objects that can't be reclaimed keep accumulating → heap fills →
  **OutOfMemoryError: Java heap space**.
- GC frees objects **unreachable from any live reference chain**;
  `System.gc()` is a hint, never a guarantee.

## Self-check (do this before opening E3)

Answer aloud, no notes: (1) What do two threads share, what do they own?
(2) Why is `counter++` broken and what are TWO fixes? (3) Both guarantees
of `synchronized`? (4) Two reasons for a thread pool over raw threads?
(5) Sketch the two-lock deadlock and the fix. If any answer stalls, reread
that block only — then take E3.