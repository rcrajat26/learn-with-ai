# 05 Multithreading and Concurrency — Why plain Java is usually ABA-safe — BUILD IT (§4.4, leaves 4.4.3–4.4.4)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [Treiber stack and ABA](04-treiber-stack-and-aba.md) · Next: [The Michael–Scott queue](04c-michael-scott-queue.md)

## 4.4.3 Why the plain `TreiberStack<E>` is usually ABA-safe

### The claim, stated precisely

The `TreiberStack<E>` from [04-treiber-stack-and-aba.md](04-treiber-stack-and-aba.md) §4.4.1 — no
pool, no recycling, every popped node simply falling out of scope — is **usually** immune to ABA in
ordinary Java, not because CAS behaves any differently, but because of one fact about garbage
collection that has nothing to do with concurrency control: **a garbage collector will not reclaim
an object's memory while any thread still holds a live reference to it.**

### [PROVE] Working the argument through

Take the exact interleaving from 04's walkthrough, but strip out the pool and replay it against the
plain stack. Stack before the race, top to bottom: **X** (`WD-501`) → **Y** (`WD-502`) → **Z**
(`WD-503`), shared by `settlement-ingest-4` (the stalled reader) and `payment-run-worker-1` (the
thread doing legitimate work).

1. `settlement-ingest-4` calls `pop()`. It executes `currentTop = top.get()`, reading node **X**,
   then `next = currentTop.next`, reading **Y** — and is descheduled immediately before its
   `compareAndSet(X, Y)` executes. Critically: **`settlement-ingest-4`'s stack frame now holds a
   live local variable `currentTop` pointing at the `Node` object X.** That is a GC root. As long as
   this thread is suspended mid-method with that local live, object X is *reachable* from a GC root
   and cannot be collected, no matter how long the thread stays parked.
2. `payment-run-worker-1` calls `pop()` and CASes `top` from **X** to **Y**. Node **X** falls off the
   stack's own bookkeeping — `top` no longer points at it — but `settlement-ingest-4`'s local
   variable still does. From the collector's point of view, X has two referrers going into this
   step and one referrer (the stalled thread) coming out of it. It is unreachable *from the data
   structure* but still reachable *from a live thread stack*, and reachability from any GC root is
   the only thing a tracing collector checks.
3. `payment-run-worker-1` continues doing real work: it hands `WD-501`'s logical withdrawal off to
   whatever consumes it, pops **Y** for `WD-502`, and eventually needs a **new** `Node` for the next
   withdrawal it pushes, `WD-777`. It calls `new Node<>(item)` — an ordinary allocation. **This is
   the crux.** In the pooling version, "get a node" meant "ask the pool, which may hand back X." In
   the plain version, "get a node" means "ask the allocator," and the allocator has no channel back
   to objects that a live reference still pins in reachable memory. G1 (the Java 21 default
   collector) will happily allocate a fresh object in a fresh region; it has no reason and no
   mechanism to notice that some *other*, still-reachable object happens to be logically similar.
4. `settlement-ingest-4` resumes and executes `top.compareAndSet(X, Y)`. `top`'s current value is
   whatever node `payment-run-worker-1` last pushed — a distinct new object, not X, because nothing
   handed X's identity back into circulation. The CAS **fails honestly**: `top` does not hold the
   value `settlement-ingest-4` expected, so it re-reads `top` and retries from current state. No
   corruption occurs — not because the algorithm defends against ABA, but because ABA's precondition
   (the value at the memory location cycling back to something reference-equal to what the stalled
   thread remembered) never arose.

The property this leans on is not "Java prevents stale references" in some magical sense — it is
the ordinary, unglamorous guarantee every tracing GC gives every Java program: **reachable objects
are never reclaimed, and reclaimed objects never come back with new identity while something still
points at the old one.** ABA needs a *third* event — recycling — to close the loop between "value
moved away" and "value came back." A GC that will not reuse live memory removes exactly that third
event.

**Insight:** this is the same mechanism, seen from the opposite side, that makes the pooling
demonstration in 04.4.2 need to *deliberately* introduce a pool. A pool is a program-level promise
to hand identical object identity back out on request — which is precisely the promise a GC refuses
to make on its own. ABA in Java is not a JVM defect; it is what happens when application code
re-implements object reuse (pooling, freelists, off-heap slabs) and thereby reintroduces the
recycling event the collector was quietly preventing.

### Why "usually," not "always"

Three carve-outs, each a case where something *other* than the collector reintroduces recycling:

| Carve-out | Why it reintroduces ABA | Where it shows up |
|---|---|---|
| Explicit object pooling / free lists | The whole point of a pool is to hand the same object identity back out — exactly the 04.4.2 demonstration | Connection pools, buffer pools, custom allocators built for GC-pressure reduction |
| Off-heap / manual memory (`Unsafe`, `MemorySegment`, JNI-owned buffers) | No GC governs that memory at all; a freed-and-reallocated native address can legitimately repeat | Direct `ByteBuffer` arenas, the Foreign Function & Memory API, native interop |
| Index/slot recycling instead of object recycling | The "value" being CASed is a small integer slot number into an array, and slot numbers are bounded and *must* repeat — the object behind the slot is irrelevant, the ABA hazard moves to "does slot 3 still mean what I think it means" | Lock-free ring buffers, array-backed queues that CAS an index rather than a reference |

**Pitfall:** treating this leaf as "ABA cannot happen in Java" and then adding a node pool to a
lock-free structure "to cut allocation" without re-adding a stamp. The pool is not a performance
detail orthogonal to correctness — it is the one change that puts ABA back on the table. Any code
review of a lock-free structure should treat "does anything recycle the nodes/objects this CAS
target points at?" as the single load-bearing question, not "is this Java."

**Interview:** "Is the JVM's Treiber stack immune to ABA?" — the honest answer is: the plain,
non-pooling version is immune in practice because the GC will not let a live reference's target be
reused for something else, but the moment you pool nodes for allocation efficiency you reintroduce
the exact bug, which is why production lock-free code either avoids pooling or uses a stamped
reference regardless.

> Plain Java's `TreiberStack<E>` is *usually* ABA-safe not by algorithmic design but because a
> tracing garbage collector will not reclaim and reissue the identity of an object while any thread
> still holds a live reference to it — a guarantee that explicit node pooling, off-heap memory, and
> recycled array slots each independently defeat.

## 4.4.4 Hazard pointers and epoch-based reclamation — the C++ answer

### The problem restated for a language with no GC

A C++ lock-free stack has the identical CAS retry-loop shape as `TreiberStack<E>`, but `delete`-ing
a popped node the moment it is unlinked is exactly the recycling event that section 4.4.3 argued
Java's collector avoids for you. If thread A is stalled holding a raw pointer to a node that thread
B has already popped and `delete`d, A's next dereference of that pointer is **use-after-free** —
worse than logical ABA, it is undefined behavior — and if the freed memory has already been handed
back out by the allocator for an unrelated allocation of the same size, A's subsequent CAS can
succeed against genuinely different content living at the same address, the classic C++ ABA. There
is no collector standing between "unlink from the stack" and "the memory is available again." The
language gives you manual `delete`; safe reclamation has to be built by hand, and two techniques
dominate production non-GC lock-free code: hazard pointers and epoch-based reclamation.

### Hazard pointers

**Mechanism.** Each thread that intends to dereference a shared pointer first *publishes its intent*
by writing that pointer's value into one of its own thread-local "hazard pointer" slots — a small,
globally visible array, one or a few slots per thread — using a `store`-then-`fence` (or a
sequentially consistent store) so every other thread's next read sees the publication before the
dereference happens. Concretely, for a Treiber-style pop: a thread reads `top` into a local, writes
that same value into its hazard slot, then **re-reads `top`** to confirm nothing changed between the
first read and the publish (if it did, retry the whole sequence) — only then is it safe to
dereference. Before any thread reclaims (frees) a node it has unlinked, it must first scan **every
other thread's** hazard-pointer slots; if the node's address appears in any slot, that thread defers
reclamation — typically by pushing the node onto a small per-thread "retired list" — and retries the
scan later, only actually calling `delete` once no hazard slot anywhere names that address.

**Cost.** A full scan of all threads' hazard slots on every reclamation attempt is O(number of
threads) work per retirement, and the retired-list bookkeeping adds a second data structure
alongside the lock-free one it protects. The payoff is a hard bound: retired memory is reclaimed
promptly (as soon as no hazard slot names it), which keeps peak unreclaimed memory small and
predictable — the technique used inside Meta's Folly library and Microsoft's `concurrency::` runtime
for exactly this reason.

### Epoch-based reclamation (EBR)

**Mechanism.** A single global epoch counter advances periodically (often on a timer or after N
operations). Each thread, before touching any shared lock-free structure, announces "I am active in
epoch E" by reading the global counter into a thread-local slot; when it finishes its operation it
marks itself inactive (or simply re-announces on its next operation). A thread that unlinks a node
does not free it immediately — it tags the node with the epoch it was retired in and defers it to a
per-epoch retirement list. Reclamation of an epoch's retirement list is only safe once **every**
thread has been observed to have passed through — i.e., every thread's last-announced epoch is at
least as recent — meaning no thread could still be mid-traversal holding a pointer read during that
older epoch. That "everyone has passed a grace point" condition is structurally the same idea as an
RCU (read-copy-update) grace period in the Linux kernel, and EBR is often described as userspace RCU.

**Cost.** Bookkeeping per operation is cheaper than hazard pointers' full scan — announcing an epoch
is one write, not an O(threads) scan — but reclamation is *batched and delayed*: a node retired in
epoch 5 cannot be freed until every thread has moved past epoch 5, which can be arbitrarily long if
even one thread stalls (blocked on I/O, descheduled, or simply slow), so peak memory held by
unreclaimed nodes is unbounded in the pathological case, unlike hazard pointers' bounded-by-thread-
count-and-slots-per-thread guarantee. This is the classic hazard-pointers-vs-EBR trade-off: bounded
memory and per-op scan cost, versus cheaper per-op cost and unbounded worst-case memory.

| Dimension | Hazard pointers | Epoch-based reclamation |
|---|---|---|
| Per-operation cost | publish + re-verify + O(threads) scan on reclaim | one epoch announcement (cheap write) |
| Reclamation latency | prompt — as soon as no slot names the node | delayed — until every thread crosses a grace point |
| Worst-case unreclaimed memory | bounded (threads × slots) | unbounded if a thread stalls indefinitely |
| Conceptual relative | per-object reference counting, checked cooperatively | RCU grace periods (Linux kernel heritage) |
| Java's equivalent problem | solved for free by the tracing GC (§4.4.3) — no hand-rolled scheme needed for on-heap objects | same |

### Would you still need this in Java?

Yes — precisely in the carve-outs §4.4.3 listed. If a Java program pools `Node` objects to cut
allocation churn, it has voluntarily stepped outside the GC's guarantee and re-created the exact
problem C++ has natively: an object identity can be handed back out while a stalled thread still
references its old logical content. `AtomicStampedReference` (04-treiber-stack-and-aba.md) is Java's
usual answer because it is simpler to bolt onto an existing CAS loop, but hazard pointers or
epoch-based schemes are the more general fix and are what a Java program manipulating **off-heap**
memory (`java.lang.foreign.MemorySegment`, direct buffers) must build by hand, because the GC's
reachability guarantee stops at the boundary of the Java heap — it says nothing about a native
memory segment's lifecycle.

**Pitfall:** assuming "Java has a GC so I never need hazard pointers or epochs." True for on-heap
object graphs under ordinary allocation. False the moment a lock-free structure pools its own nodes,
or touches memory the GC does not manage — the technique gap does not close, only the *default*
need for it does.

**Interview:** "How would you implement a lock-free stack in C++ without ABA?" — pair the CAS
loop with either hazard pointers (publish-before-dereference, scan-before-free, bounded memory,
O(threads) per reclaim) or epoch-based reclamation (cheap per-op announcement, batched reclaim after
a grace period, unbounded worst-case memory if a thread stalls) — Java sidesteps both by default
because its GC already refuses to recycle a reachable object's identity.

> Hazard pointers make a thread's about-to-be-dereferenced pointer globally visible so a reclaimer
> can defer freeing it; epoch-based reclamation instead waits for every thread to cross a global
> grace point before freeing anything retired before that point — both are hand-built substitutes
> for the reachability guarantee Java's garbage collector gives on-heap objects for free.

## Pitfalls

### Believing plain Java's Treiber stack is ABA-safe "because Java"

**Wrong**
```java
// "This can't have ABA, Java has a garbage collector."
private final AtomicReference<Node<E>> top = new AtomicReference<>();
// ...later, "optimizing":
private final Pool<Node<E>> nodePool = new Pool<>(); // reuse nodes to cut allocation
```
Adding the pool reintroduces the exact recycling event the GC was preventing — see the full
demonstration in `04-treiber-stack-and-aba.md` §4.4.2.

**Right**
```java
private final AtomicReference<Node<E>> top = new AtomicReference<>();
// nodes are never pooled; a popped Node becomes ordinary garbage
```
or, if pooling is genuinely required for allocation pressure, pair it with
`AtomicStampedReference<Node<E>>` so a stale CAS fails instead of succeeding against recycled
identity.

**Why people believe it:** "Java has a GC" is true and does causally prevent the *default* case of
ABA, so it is easy to over-generalize from "the common case is safe" to "the mechanism itself is
safe," without noticing that the safety was contingent on never reintroducing recycling.

### Assuming hazard pointers or EBR are needed in ordinary Java code

**Wrong** — hand-rolling a hazard-pointer scheme around a plain, non-pooling `AtomicReference<Node<E>>`
stack because "that's how real lock-free structures work."

**Right** — recognize that hazard pointers and EBR solve a problem (manual reclamation racing a
stalled reader) that a tracing GC has already solved for on-heap objects; reach for them in Java only
when working with pooled nodes at extreme allocation-sensitivity, or off-heap memory the GC does not
manage.

**Why people believe it:** most lock-free literature and interview material is written from a C++
perspective, where reclamation is always manual, so the pattern gets copied into Java contexts
without re-checking whether the underlying problem (manual `delete`) even exists there.

## Cheat sheet

| Concept | One-line fact |
|---|---|
| Why plain `TreiberStack<E>` is usually ABA-safe | GC will not reclaim/reissue a reachable object's identity while any thread holds a live reference |
| What breaks the guarantee | node pooling, off-heap memory, recycled array slot indices |
| Hazard pointers | publish pointer before dereference, scan all threads' slots before reclaiming, bounded memory, O(threads) per reclaim |
| Epoch-based reclamation | cheap per-op epoch announcement, defer reclaim until every thread crosses a grace point, unbounded worst-case memory |
| EBR's conceptual relative | userspace RCU (Linux kernel) |
| Java's own fix for pooled nodes | `AtomicStampedReference<V>` (simpler to bolt onto an existing CAS loop than hazard pointers/EBR) |
| When Java still needs hazard pointers/EBR | off-heap memory (`MemorySegment`, direct buffers) the GC does not govern |

## Self-test

**Q1.** Why does a stalled thread's local variable matter to whether ABA can occur in plain Java?

<details><summary>Answer</summary>

A local variable holding a reference to an object is a GC root. As long as the thread that declared
it is suspended with that variable live on its stack, the object it points to is reachable and
cannot be reclaimed by the collector — which means the collector cannot hand that object's identity
back out for a different logical purpose. That is the entire mechanism behind "plain Java is usually
ABA-safe": the stalled thread's own reference is what keeps the object from being recycled.

</details>

**Q2.** What single change turns a GC-safe Treiber stack into an ABA-exposed one, and why?

<details><summary>Answer</summary>

Introducing an object pool (or free list) that hands popped `Node` objects back out for reuse. The
pool is a program-level mechanism that voluntarily does what the GC refuses to do on its own —
reissue an object's identity while some other thread might still hold a stale reference to it —
which is precisely the third event ABA needs beyond "value moved away."

</details>

**Q3.** In C++, why is a use-after-free bug worse than a Java-style ABA bug?

<details><summary>Answer</summary>

Java's ABA at worst causes a CAS to succeed against a value that logically changed underneath a
thread — corrupted bookkeeping, but the memory itself is always a valid, live object. In C++,
`delete`-ing a node while another thread still holds a raw pointer to it means that thread's next
dereference reads freed memory, which is undefined behavior — it may crash, read garbage, or (if the
allocator has already reissued that memory for something else) silently succeed against unrelated
content, which is the C++ analogue of ABA layered on top of memory-safety violation.

</details>

**Q4.** Describe the two-step publish sequence a hazard-pointer scheme uses before a thread
dereferences a shared pointer, and why the second step is necessary.

<details><summary>Answer</summary>

The thread first reads the shared pointer into a local, then writes that same value into its own
globally visible hazard slot. It then re-reads the shared pointer to confirm the value has not
changed since the first read. The second read is necessary because between the first read and the
publish, another thread could have already unlinked and started reclaiming that exact node — without
re-verifying, the publishing thread could "protect" a pointer value that a reclaimer has already
decided is safe to free, because the reclaimer's scan happened in the gap between the first read and
the publish.

</details>

**Q5.** Why can epoch-based reclamation have unbounded worst-case memory, while hazard pointers
cannot?

<details><summary>Answer</summary>

EBR only reclaims a retired node once every thread has been observed to have advanced past the
epoch the node was retired in. If even one thread stalls indefinitely (blocked, descheduled, or
simply slow) without advancing its announced epoch, every node retired since that stall accumulates
on retirement lists with no bound. Hazard pointers instead bound the number of "protected" pointers
by the number of threads times the number of hazard slots per thread — a stalled thread can hold at
most a fixed number of nodes hostage, not an unbounded backlog.

</details>

**Q6.** Why doesn't Java need hazard pointers or epoch-based reclamation for an ordinary, non-pooling
lock-free stack of heap objects?

<details><summary>Answer</summary>

Both techniques exist to answer one question safely without a garbage collector: "is it safe to free
this memory yet, given some thread might still hold a pointer to it?" A tracing garbage collector
already answers exactly that question for every heap object, continuously, as part of normal
collection — an object is only ever reclaimed once no GC root (including a stalled thread's local
variable) reaches it. Hazard pointers and EBR are hand-built substitutes for a guarantee the JVM
already provides for on-heap objects.

</details>

**Q7.** Give one concrete situation in modern Java where hazard-pointer- or EBR-style thinking is
still relevant, and explain why the GC does not cover it.

<details><summary>Answer</summary>

Manipulating off-heap memory through the Foreign Function & Memory API's `MemorySegment`, or a
direct `ByteBuffer`, in a lock-free structure. The GC manages the Java heap; it has no visibility
into, and gives no reachability guarantee over, memory obtained from `malloc`-equivalent native
allocation. A lock-free structure built over such memory needs its own reclamation discipline —
hazard pointers, epochs, or an explicit reference-counting scheme — exactly as C++ does, because the
JVM's safety net stops at the heap boundary.

</details>

---

**Leaves covered:** 4.4.3–4.4.4 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 339
