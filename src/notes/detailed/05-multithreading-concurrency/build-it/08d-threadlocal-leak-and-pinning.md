# 05 Multithreading and Concurrency — The ThreadLocal leak and pinning harnesses — BUILD IT (§4.8, leaves 4.8.7–4.8.8)

**Target version: Java 21 LTS.** | **Part 4 of 5** | [Index](../00-index.md)
Previous: [The false-sharing and starvation harnesses](08c-false-sharing-and-starvation.md) · Next: [The jcstress publication and DCL harnesses](08e-jcstress-publication-and-dcl.md)

---

## 4.8.7 — The `ThreadLocal` leak harness

### Mental model

A `ThreadLocal<T>` is not a map you own. It is an entry inside a private `ThreadLocalMap` that
lives *on the thread object itself*, keyed by the `ThreadLocal` instance with a **weak reference**
to that key. In a fixed pool the thread never dies between requests, so nothing ever forces the
map to be swept. If a request populates the slot and does not call `remove()`, the value — however
large — is pinned alive for the thread's entire lifetime, and a fixed pool's threads live forever.

### The setup

`gateway-http-1` through `gateway-http-8` handle onboarding calls for `ApplicationGateway`. Each
request stashes a per-request security context — the caller's `ClientId`, scopes, and a decoded
JWT claims blob — in a `ThreadLocal` so downstream code (`ScreeningService`, `AssessmentService`)
can read "who is calling" without threading a parameter through every method. Nobody calls
`remove()` because nobody thought a thread-pool thread would outlive the request.

```java
package quizstakes.gateway;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/** Per-request security context: identity, scopes, and the raw claims payload. */
final class SecurityContext {
    final String clientId;
    final List<String> scopes;
    final byte[] claimsPayload; // decoded JWT body — deliberately sized to be visible in a heap dump

    SecurityContext(String clientId, List<String> scopes, byte[] claimsPayload) {
        this.clientId = clientId;
        this.scopes = scopes;
        this.claimsPayload = claimsPayload;
    }
}

/** BROKEN: never calls remove(), so the pool leaks one payload per thread, forever. */
final class LeakyRequestContext {
    private static final ThreadLocal<SecurityContext> CURRENT = new ThreadLocal<>();

    static void bind(SecurityContext ctx) {
        CURRENT.set(ctx);
    }

    static SecurityContext current() {
        return CURRENT.get();
    }
    // no remove() anywhere in this class
}

public final class ThreadLocalLeakHarness {
    public static void main(String[] args) throws InterruptedException {
        ExecutorService gatewayPool = Executors.newFixedThreadPool(8, r -> {
            Thread t = new Thread(r);
            t.setName("gateway-http-" + t.threadId());
            return t;
        });

        // Simulate 200,000 onboarding requests for client 2401993 across 8 pinned threads.
        byte[] claimsTemplate = new byte[64 * 1024]; // 64 KiB claims blob per request
        for (int i = 0; i < 200_000; i++) {
            gatewayPool.submit(() -> {
                SecurityContext ctx = new SecurityContext(
                        "2401993",
                        List.of("STAKE_PLACE", "WITHDRAW_REQUEST"),
                        claimsTemplate.clone());
                LeakyRequestContext.bind(ctx);
                // ... request handling reads LeakyRequestContext.current() here ...
                // request completes; thread returns to the pool WITHOUT clearing the ThreadLocal
            });
        }
        gatewayPool.shutdown();
        gatewayPool.awaitTermination(5, TimeUnit.MINUTES);
    }
}
```

### What you observe

Only 8 pool threads ever exist, but each request allocates a fresh 64 KiB `claimsPayload` and
overwrites the previous `SecurityContext` in that thread's slot — so at first glance this looks
harmless: the map has exactly one entry per thread at all times, and the old `SecurityContext`
should become garbage the moment `bind()` replaces it. The actual leak in this exact shape is
milder than the classic "unbounded map growth" story: 8 threads × 1 slot × 64 KiB ≈ 512 KiB of
permanently-referenced live data at any instant, which alone is not an OOM.

The real leak in this pattern is the version where the payload **grows per request** — for
example when a downstream call appends audit metadata onto the same context object before the
next `bind()` runs, or when `bind()` is called conditionally so a stale value from an earlier,
larger request survives untouched for many subsequent requests that never call it at all. Order of
magnitude: a pool of 8 threads that each accumulate one stale multi-hundred-KB context that is
never cleared, held for the process lifetime, shows up as a low-tens-of-MB permanent floor in
`jcmd <pid> GC.heap_info` that never returns to baseline after a full GC — small in absolute bytes,
but the shape (a floor that never drops) is the tell, not the size.

**Pitfall:** "It's a `ThreadLocal`, it goes away when the request ends." A `ThreadLocal` value's
lifetime is tied to the **thread**, not the request. A fixed pool's threads are alive for the
process lifetime, so anything bound and not removed is effectively a `static` field scoped per
thread — the opposite of what the name suggests.

### The heap-dump evidence

Trigger a heap dump (`jcmd <pid> GC.heap_dump /tmp/gateway.hprof`) and open it in Eclipse MAT or
`jhat`. What you look for, specifically:

```
Class Name                                          | Shallow Heap | Retained Heap
-----------------------------------------------------|--------------|---------------
java.lang.ThreadLocal$ThreadLocalMap$Entry            |           32 |         65,568
  -> key = null                                       |              |
  -> value = quizstakes.gateway.SecurityContext        |           32 |         65,536
       -> claimsPayload = byte[65536]                  |       65,552 |         65,552
```

The signature is `Entry` with `key == null` but `value != null`. The `Entry` extends
`WeakReference<ThreadLocal<?>>`, so once nothing else holds a strong reference to the
`LeakyRequestContext.CURRENT` field's `ThreadLocal` instance itself the *key* can be collected —
but the map slot (the `Entry` object) and its `value` are **not** weakly referenced, and nothing
sweeps stale entries except a call to `get()`, `set()`, or `remove()` on that same
`ThreadLocalMap` from that thread. A null-key, live-value `Entry` in a dominator tree rooted at a
long-lived `Thread` object is the canonical MAT query for this leak — "Show retained set" on the
`Thread` will surface the `ThreadLocalMap` and every stale `Entry` beneath it.

**Insight:** the weak key is not a safety net for the value. It exists so the `ThreadLocalMap`
*itself* doesn't pin `ThreadLocal` instances that have gone out of scope (e.g. a `ThreadLocal`
created inside a method and never stored anywhere else). It does nothing to reclaim the `value` —
that requires an explicit `remove()`, or the map's internal `expungeStaleEntries` sweep, which only
runs opportunistically during `get`/`set`/`remove` on that *same* thread, and only sweeps entries
whose *key* has already gone null.

### The fix

```java
final class ScopedRequestContext {
    private static final ThreadLocal<SecurityContext> CURRENT = new ThreadLocal<>();

    static void bind(SecurityContext ctx) {
        CURRENT.set(ctx);
    }

    static SecurityContext current() {
        return CURRENT.get();
    }

    /** Callers MUST run request handling inside this, never call bind() bare. */
    static void runScoped(SecurityContext ctx, Runnable requestHandling) {
        CURRENT.set(ctx);
        try {
            requestHandling.run();
        } finally {
            CURRENT.remove(); // guaranteed even if requestHandling throws
        }
    }
}
```

`try/finally` around `remove()` is not optional decoration — without it, a request that throws
mid-handling leaves the stale context bound for whatever the *next* request on that thread does,
which is a correctness bug (client 2401993's context leaking into the next caller's request) on
top of the memory leak. Java 21's built-in fix for the *scoping* half of this problem —
`ScopedValue`, preview in 21, final as JEP 506 in Java 25 — binds a value for the dynamic extent of
a call and unbinds it automatically on return, making a missing `remove()` structurally
impossible. It is out of scope for this file; see the ScopedValue basics file for the mechanism.

**Interview:** "Why does a `ThreadLocal` leak in a thread pool but not in a per-request thread
model?" Because the leak is a property of the *thread's* lifetime, and pool threads are reused
indefinitely; a fresh `Thread` per request dies (and its `ThreadLocalMap` with it) whether or not
`remove()` was called.

> **Definition:** a `ThreadLocal` leak is stale data surviving in a live thread's private map past
> the point its owning logical scope ended, because nothing on that thread called `remove()`,
> `set()` with a fresh value, or `get()` after the key became unreachable.

---

## 4.8.8 — The virtual-thread pinning harness (Java 21) `[VERSION-TRAP]`

### Mental model

A virtual thread is a lightweight task multiplexed onto a small pool of **carrier** platform
threads (the `ForkJoinPool` behind `Executors.newVirtualThreadPerTaskExecutor()`). It normally
*unmounts* from its carrier whenever it blocks — the carrier is freed to run another virtual
thread, and the parked one is remounted later, possibly on a different carrier. On Java 21, two
things prevent that unmount: holding a `synchronized` monitor, and running native/JNI code. When a
virtual thread is pinned, its carrier is stuck doing nothing until the blocking call returns —
which, with only as many carriers as there are CPU cores (or fewer, if forced), can stall the
entire scheduler.

### The setup

`withdrawal-intake-1` handles card withdrawal authorisation for `PaymentService`, calling the card
PSP's `authorise` endpoint at **240 ms p50**. The code wraps the call in a `synchronized` block
because it also needs to touch a shared in-memory rate-limit counter guarded by the same monitor —
a common and reasonable-looking pattern that becomes a scheduler stall once the call runs on a
virtual thread.

```java
package quizstakes.payments;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;

/** Stand-in for the card PSP authorise call — 240ms p50 in production. */
final class CardPsp {
    static void authorise(String withdrawalId) {
        try {
            Thread.sleep(Duration.ofMillis(240));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

/** BROKEN on Java 21: synchronized around a blocking call pins the carrier. */
final class PinningWithdrawalAuthoriser {
    private final Object rateLimitLock = new Object();

    void authorise(String withdrawalId) {
        synchronized (rateLimitLock) {
            CardPsp.authorise(withdrawalId); // blocks WHILE holding the monitor
        }
    }
}

public final class PinningHarness {
    public static void main(String[] args) throws InterruptedException {
        // Force a single-carrier scheduler to make the stall visible and reproducible.
        System.setProperty("jdk.virtualThreadScheduler.parallelism", "1");

        PinningWithdrawalAuthoriser authoriser = new PinningWithdrawalAuthoriser();
        int concurrentWithdrawals = 50;
        CountDownLatch done = new CountDownLatch(concurrentWithdrawals);

        long start = System.nanoTime();
        try (ExecutorService withdrawalExecutor = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < concurrentWithdrawals; i++) {
                String withdrawalId = "wd-" + i;
                withdrawalExecutor.submit(() -> {
                    authoriser.authorise(withdrawalId);
                    done.countDown();
                });
            }
            done.await();
        }
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;
        System.out.println("50 withdrawals, 1 carrier, pinned: elapsed ~" + elapsedMs + " ms");
    }
}
```

### What you observe

With `parallelism=1` there is exactly one carrier. Each virtual thread that enters
`synchronized (rateLimitLock)` and then calls `Thread.sleep` (via `CardPsp.authorise`) cannot
unmount — the carrier is pinned for the full 240 ms, serving nothing else. Fifty withdrawals that
should, if unmounting worked, overlap almost entirely on one carrier instead run essentially back
to back. Order of magnitude: **~50 × 240 ms ≈ the low tens of seconds**, versus the low hundreds of
milliseconds you would see if the sleep were outside the `synchronized` block (where unmounting is
free to happen and the single carrier just round-robins the parking/unparking cost, which is
itself order-of-magnitude microseconds, not milliseconds).

Run with the tracing flag to see the JDK name the exact cause:

```
$ java -Djdk.tracePinnedThreads=full PinningHarness
```

```
Thread[#31,ForkJoinPool-1-worker-1,5,CarrierThreads]
    java.base/java.lang.VirtualThread$VThreadContinuation.onPinned(VirtualThread.java:183)
    java.base/java.lang.VirtualThread.parkOnCarrierThread(VirtualThread.java:1013)
    java.base/java.lang.VirtualThread.park(VirtualThread.java:614)
    java.base/java.lang.System$2.parkVirtualThread(System.java:2643)
    java.base/jdk.internal.misc.VirtualThreads.park(VirtualThreads.java:58)
    java.base/java.lang.VirtualThread.sleepNanos(VirtualThread.java:829)
    java.base/java.lang.Thread.sleep(Thread.java:507)
    quizstakes.payments.CardPsp.authorise(CardPsp.java:12)
    quizstakes.payments.PinningWithdrawalAuthoriser.authorise(PinningWithdrawalAuthoriser.java:22)
    <== monitors:1
```

The `<== monitors:1` line is the tell — the runtime is reporting the virtual thread is pinned
because it holds one monitor while parking. This output is reproduced in the documented format,
not captured from a live run in this environment; the frame names and the `monitors:1` marker
match the JDK 21 `VirtualThread` pinning-trace implementation.

**Pitfall:** "Virtual threads make blocking code free everywhere." Only true when the blocking
call unmounts. `synchronized`, native/JNI frames, and (on 21) certain FFM calls all pin. A codebase
full of legacy `synchronized` blocks wrapping I/O gets *worse*, not better, when naively moved onto
virtual threads with a small carrier count — it trades OS-thread exhaustion for carrier starvation.

### The fix (Java 21): replace `synchronized` with `ReentrantLock`

```java
import java.util.concurrent.locks.ReentrantLock;

final class NonPinningWithdrawalAuthoriser {
    private final ReentrantLock rateLimitLock = new ReentrantLock();

    void authorise(String withdrawalId) {
        rateLimitLock.lock();
        try {
            CardPsp.authorise(withdrawalId); // blocks while holding a LOCK, not a MONITOR
        } finally {
            rateLimitLock.unlock();
        }
    }
}
```

`ReentrantLock` is a `java.util.concurrent` lock built on AQS, not a JVM monitor — parking while
holding it does not invoke the monitor-pinning path at all, so the carrier is freed exactly as it
would be for any other blocking call. Rerunning the harness with `NonPinningWithdrawalAuthoriser`
against the same single-carrier scheduler drops elapsed time back to order-of-magnitude the PSP's
own 240 ms p50 plus scheduling noise — the fifty calls overlap because the carrier is no longer
stuck.

### `[VERSION-TRAP]` — stated plainly

This entire harness is a **Java 21** demonstration and will not reproduce as written on Java 24+:

- **JEP 491, "Synchronize Virtual Threads without Pinning," is final in JDK 24.** From 24 onward,
  `synchronized` no longer pins a virtual thread's carrier for ordinary Java monitor acquisition —
  the `PinningWithdrawalAuthoriser` version above runs at the same speed as the `ReentrantLock`
  version on 24+.
- **`-Djdk.tracePinnedThreads` was removed together with JEP 491.** On JDK 24+ that flag simply
  does not exist; there is nothing left for it to trace for the `synchronized` cause, and the JDK
  does not keep it around as a no-op.
- **What still pins on 24+:** native frames, JNI calls, and Foreign Function & Memory (FFM) calls
  that block inside native code still prevent unmounting, because JEP 491 addresses the *monitor*
  cause specifically, not the native-frame cause. A virtual thread blocked inside a JNI call or an
  FFM downcall on Java 24 or 25 is still pinned, and no `synchronized`-focused fix like
  `ReentrantLock` helps it — the fix there is architectural (move the blocking native call off the
  virtual-thread path entirely, e.g. onto a dedicated platform-thread pool).

**Interview:** "Is `synchronized` still a problem for virtual threads?" Version-scoped answer:
yes on 21 (use `ReentrantLock` or restructure to avoid holding a monitor across a blocking call),
no on 24+ for the monitor case specifically (JEP 491), but native/JNI/FFM pinning is untouched by
that JEP and remains a real constraint on every version.

> **Definition:** carrier pinning is a virtual thread parking while its continuation cannot be
> unmounted from its carrier, because it holds a JVM monitor (Java 21 and earlier) or is executing
> native code (all versions) — the carrier is unavailable to any other virtual thread for the
> duration.

---

## Pitfalls

### Assuming a `ThreadLocal` clears itself when the request object goes out of scope

**Wrong**
```java
void handle(Request req) {
    LeakyRequestContext.bind(new SecurityContext(req.clientId(), req.scopes(), req.claims()));
    process(req);
    // req goes out of scope here; developer assumes SecurityContext does too
}
```
The `SecurityContext` is reachable from the thread's `ThreadLocalMap`, not from `req` — it survives
`handle()` returning and is only replaced (not freed early) by the next request on the same thread.

**Right**
```java
void handle(Request req) {
    ScopedRequestContext.runScoped(
        new SecurityContext(req.clientId(), req.scopes(), req.claims()),
        () -> process(req));
}
```
`runScoped`'s `finally` block calls `remove()` unconditionally, so the map slot is cleared the
moment the logical scope ends, regardless of what else references `req`.

**Why people believe it:** in a per-request-thread model (classic thread-per-connection servers
with short-lived threads) this belief happens to hold, because the *thread* dies with the request.
It stops holding the instant the thread is pooled — the JDK's own `HttpServer`, Tomcat's worker
pool, and any `ExecutorService`-backed service all pool threads by default.

### Believing `-Djdk.tracePinnedThreads` works on any current JDK

**Wrong:** running `java -Djdk.tracePinnedThreads=full` on a JDK 24 or 25 installation expecting a
pinning report for a `synchronized` block, and concluding "must not be pinning" when nothing
prints.

**Right:** check the JDK version first. On 24+, the absence of output from that flag proves
nothing — the flag itself no longer exists as a monitor-pinning tracer because JEP 491 removed the
cause it traced. Use JFR's `jdk.VirtualThreadPinned` event (still relevant for native/JNI/FFM
pinning) instead.

**Why people believe it:** the flag's name and behaviour were stable and widely blogged about for
the entire virtual-threads-preview era (19–20) and the 21 LTS window, so it reads as a permanent
API rather than a Java-21-scoped diagnostic tied to a specific, since-fixed cause.

---

## Cheat sheet

| Failure | Cause | Detection | Fix |
|---|---|---|---|
| `ThreadLocal` leak | pooled thread never calls `remove()` | heap dump: `Entry` with `key=null`, live `value`, retained by long-lived `Thread` | `try/finally` with `remove()`, or `ScopedValue` (final JDK 25) |
| Weak key ≠ freed value | `Entry.value` is a strong reference | same as above | never rely on the weak key alone |
| Pinning (Java 21) | `synchronized` held across a blocking call on a virtual thread | `-Djdk.tracePinnedThreads=full` → `<== monitors:1` | swap to `ReentrantLock` |
| Pinning (JDK 24+) | monitor case is gone (JEP 491); native/JNI/FFM still pins | JFR `jdk.VirtualThreadPinned` (native cause only) | move blocking native call off virtual-thread path |
| Trace flag removed | `-Djdk.tracePinnedThreads` deleted alongside JEP 491 | flag absent/no-op on 24+ | do not rely on it past 23 |

## Self-test

**Q1.** Why does replacing `claimsTemplate.clone()` with a smaller object not fix the
`ThreadLocalLeakHarness` if `remove()` is still never called?

<details><summary>Answer</summary>

It reduces the *size* of the leak but not its existence — the stale `SecurityContext` (whatever
size) still survives in the thread's map for the pool's lifetime because nothing calls `remove()`
or overwrites the slot faster than the underlying problem (a growing or conditionally-bound
payload) accumulates it. The fix is structural (`try/finally` with `remove()`), not a size
reduction.

</details>

**Q2.** What exactly does the weak reference in `ThreadLocalMap.Entry` protect against, and what
does it not protect against?

<details><summary>Answer</summary>

It protects against the `ThreadLocalMap` itself pinning `ThreadLocal` instances whose only other
references have gone away — once nothing else holds the `ThreadLocal` key strongly, the key can be
collected and the map's own sweep (`expungeStaleEntries`, run opportunistically during `get`/`set`/
`remove`) can reclaim the entry. It does not protect the `value` from being retained, and it does
not sweep proactively — no background thread walks live threads' maps clearing stale entries.

</details>

**Q3.** On Java 21, why does wrapping only the *rate-limit-counter update* in `synchronized`, and
moving the PSP call outside the block, fix the pinning harness without introducing a
`ReentrantLock`?

<details><summary>Answer</summary>

Pinning only occurs while a virtual thread is both holding a monitor *and* blocking (parking).
If the monitor is released before the blocking call happens, there is nothing pinned during the
240 ms wait — the carrier unmounts normally. The fix works by narrowing the critical section, not
by changing lock type; it is a valid alternative to `ReentrantLock` whenever the monitor's
protected state doesn't need to span the blocking call.

</details>

**Q4.** Why is `<== monitors:1` in the trace output the specific evidence of pinning, rather than
just evidence that a monitor was held?

<details><summary>Answer</summary>

Holding a monitor by itself is not reported — only holding one *while parking* triggers
`onPinned` and the trace line, because that is precisely the combination that prevents the
continuation from unmounting. The count (`monitors:1`) tells you how many nested monitor
acquisitions are active at the parking point, which is useful for diagnosing nested
`synchronized` blocks.

</details>

**Q5.** A team runs `-Djdk.tracePinnedThreads=full` on JDK 25, sees no output under load, and
concludes their virtual-thread code has no pinning. Is that conclusion sound?

<details><summary>Answer</summary>

No. The flag was removed alongside JEP 491 in JDK 24, so on 25 it is either ignored or an
unrecognized option — its absence of output proves nothing about pinning, and in particular says
nothing about native/JNI/FFM pinning, which JEP 491 did not address and which still occurs on 25.
The correct tool there is JFR's `jdk.VirtualThreadPinned` event.

</details>

**Q6.** Why does forcing `jdk.virtualThreadScheduler.parallelism=1` make the pinning harness's
effect visible, when in production with 8 carriers the same buggy code might look "fine"?

<details><summary>Answer</summary>

With 8 carriers, up to 8 pinned virtual threads can run concurrently before contention becomes
visible as added latency — the bug is still present, but its cost is hidden until concurrent
pinned calls exceed the carrier count. Forcing parallelism to 1 makes every pinned call fully
serialize, turning a latent scaling cliff into an immediately observable stall — this is a
deliberate harness technique, not a claim that production runs with one carrier.

</details>

**Q7.** Why can't a `ThreadLocal` leak be fixed by simply calling `System.gc()` periodically?

<details><summary>Answer</summary>

The `Entry`'s `value` is a normal strong reference, not eligible for collection while the `Entry`
itself is reachable from a live thread's `ThreadLocalMap` — a GC cycle (forced or not) will not
collect reachable objects. The leak is a reachability problem, not a "GC hasn't run yet" problem;
only removing the strong reference (via `remove()`, `set()` to a new value, or the thread dying)
makes the value collectible.

</details>

## Deferred

None — both leaves (4.8.7, 4.8.8) are fully covered above.

---

**Leaves covered:** 4.8.7–4.8.8 (2 leaves)
**Leaves deferred:** none
**Diagrams included:** none
**Target version:** Java 21 LTS
**Lines:** 521
