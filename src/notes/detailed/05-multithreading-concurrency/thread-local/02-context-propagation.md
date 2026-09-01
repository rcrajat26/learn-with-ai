# 05 Multithreading and Concurrency — ThreadLocal and context propagation — INTERMEDIATE (§2.11)

**Target version: Java 21 LTS.** | **Part 2 of 5** | [Index](../00-index.md)
Previous: [Thread-safe class design](../thread-safety/03-class-design.md) · Next: [Testing and verifying concurrent code](../observability/01-testing-and-verifying.md)

## The problem stated generally

`ApplicationGateway` receives a request, attaches a trace id to the calling thread (SLF4J MDC,
or a similar mechanism), and calls into `AssessmentService` to run the wealth-scoring pipeline.
`AssessmentService` submits three independent lookups — declared income, employment check,
existing exposure — to an `ExecutorService` so they run concurrently instead of one after
another. Each task, on its own pool thread, logs. None of those log lines carry the trace id.

The pool thread did not inherit anything from the submitting thread. A `ThreadLocal` — and MDC's
context map is exactly a `ThreadLocal<Map<String, String>>` — lives on the thread object it was
set on. The gateway's thread and the pool thread are two different `Thread` instances; nothing in
the JDK copies one thread's `ThreadLocal` state into another's. Submitting a `Runnable` to an
`Executor` crosses a thread boundary, and *no JDK mechanism does that copy for you*. This is not a
bug to fix once — it is a structural gap every pool-based system has, and the five mechanisms
below are the five ways people close it.

### 2.11.1 Why pools make this worse than it looks

A single-threaded request handler never notices the gap: the same thread that received the
request logs its own trace id all the way through, because it never leaves that thread. The
moment work is handed to a pool — `Executors.newFixedThreadPool`, an `@Async` method, a
`CompletableFuture.supplyAsync`, a virtual-thread-per-task executor — the context has to be
carried across explicitly, and it has to be carried across *every* boundary, not just the first
one: a task that itself submits a sub-task needs the same copy repeated.

## The five mechanisms — the map before the streets

D-137 lays out the five ways to solve this, side by side, before the notes to a table walk through
each in turn.

**D-137** — The five context-propagation mechanisms.

| Mechanism | Works across a pool | Works across a structured scope | Cleanup required | What it cannot do | Spring / OpenTelemetry equivalent |
|---|---|---|---|---|---|
| Manual copy | Yes, if every call site remembers | N/A — no scope construct | Manual `finally` at every call site | Scale: one missed call site silently drops context | None — this is what the others replace |
| Decorating `Runnable`/`Callable` | Yes, per submitted task | N/A | `finally` inside the wrapper, once | Only covers tasks submitted through it; a raw `new Thread(...).start()` bypasses it | Spring's `TaskDecorator` |
| Decorating `Executor` | Yes, for every task the pool ever runs | N/A | Same `finally`, centralised in one place | Does not help a task that spawns work on another executor it wasn't given | `spring.mvc.async` config decorating the async task executor |
| Micrometer `ContextSnapshot` | Yes, generically across many context types at once | Yes — designed to also cross Reactor's non-thread-bound scopes | `Scope` from `setThreadLocalsFrom` must be closed | Needs every context type registered with a `ContextAccessor`; will not find one it doesn't know about | `ContextSnapshotFactory` / OpenTelemetry `Context` bridging |
| `ScopedValue` + structured concurrency | Yes — inherited automatically by threads a `StructuredTaskScope` forks | Yes — this is its native habitat | None — the binding unwinds automatically when the scope exits | Cannot be set by a callee for its caller; cannot outlive the scope; cannot cross a non-structured, unrelated pool | OpenTelemetry's `Context.makeCurrent()` `try`-with-resources shape, conceptually |

**Insight:** the first three rows are all the same idea at different scopes — copy the value,
install it on the new thread, remove it when done — and the last two exist because that manual
discipline does not scale: `ContextSnapshot` generalizes it across context *types*, and
`ScopedValue` removes the need for the discipline entirely by making propagation structural.

### 2.11.2 Manual copy, and the decorating `Runnable`

The narrowest fix: read the trace id off the calling thread, close over it, and set it again
inside the task.

```java
String traceId = MDC.get("traceId");
executor.submit(() -> {
    MDC.put("traceId", traceId);
    try {
        assessmentService.scoreIncome(applicationId);
    } finally {
        MDC.remove("traceId");
    }
});
```

This works, and it is exactly what the next mechanism automates. Its failure mode is scale: every
call site that submits to an executor has to remember to do this, by hand, forever. Miss one and
that task's logs are silently unattributed — no exception, no test failure, just a gap in the
trace the next incident review notices at 2 a.m.

A decorating `Callable`/`Runnable` centralizes the copy at construction time instead of at every
submit site:

```java
static Runnable withTraceId(Runnable task) {
    String traceId = MDC.get("traceId");
    return () -> {
        Map<String, String> previous = MDC.getCopyOfContextMap();
        if (traceId != null) {
            MDC.put("traceId", traceId);
        }
        try {
            task.run();
        } finally {
            if (previous != null) {
                MDC.setContextMap(previous);
            } else {
                MDC.clear();
            }
        }
    };
}
```

This is better than the inline version because the capture-install-restore triplet lives in one
place, but every caller still has to remember to wrap. It is still one boundary at a time.

### 2.11.3 The decorating `Executor`

Wrapping the executor itself, rather than each task, removes the last thing a caller has to
remember: `executorService.submit(task)` looks identical to submitting to any other executor, and
every task that goes through it is automatically wrapped. Spring's `TaskDecorator` interface
(applied to a `ThreadPoolTaskExecutor` via `setTaskDecorator`) is exactly this shape, and it is
what `spring.mvc.async` uses to keep `SecurityContext` and MDC state attached to `@Async` methods
and Spring MVC async request handling — see the deeper walk of Spring's async execution model in
guide 07. Here is the same idea with no framework, decorating a plain `ExecutorService` so every
task submitted through it inherits the submitting thread's trace id:

```java
final class TracePropagatingExecutor implements Executor {

    private final Executor delegate;

    TracePropagatingExecutor(Executor delegate) {
        this.delegate = delegate;
    }

    @Override
    public void execute(Runnable task) {
        String traceId = MDC.get("traceId");
        delegate.execute(() -> {
            Map<String, String> previousContext = MDC.getCopyOfContextMap();
            if (traceId != null) {
                MDC.put("traceId", traceId);
            } else {
                MDC.clear();
            }
            try {
                task.run();
            } finally {
                if (previousContext != null) {
                    MDC.setContextMap(previousContext);
                } else {
                    MDC.clear();
                }
            }
        });
    }
}
```

Used at the `AssessmentService` boundary:

```java
Executor scoringExecutor = new TracePropagatingExecutor(
        Executors.newFixedThreadPool(3));

CompletableFuture<WealthVerdict> incomeCheck =
        CompletableFuture.supplyAsync(
                () -> assessmentService.scoreIncome(applicationId),
                scoringExecutor);
```

**Why the restore, not just a `clear()`, matters:** pool threads are reused. If task A sets
`traceId=abc` and only `clear()`s at the end, and task B on the same pool thread never sets a
trace id at all (a background sweep, say), B's log lines are silent — arguably correct. But if the
pool thread was *already* carrying context from an outer scope before this executor's task ran
(nested executors, or a thread pool used for more than one purpose), a bare `clear()` erases that
outer context instead of restoring it. Capturing `previousContext` and restoring it, rather than
unconditionally clearing, is what makes the decorator safe to nest.

### 2.11.4 SLF4J MDC — the mandatory `finally`

Confirmed against the SLF4J javadoc: `MDC` is a static utility over a per-thread context map, with
`put(String, String)`, `get(String)`, `remove(String)`, `clear()`, `getCopyOfContextMap()`
(returns a copy of the current thread's map, or `null` if empty), and `setContextMap(Map)`
(replaces the thread's entire map). `putCloseable` also exists, returning a `Closeable` so the
remove can be expressed as `try`-with-resources instead of a manual `finally`.

**Pitfall:** treating `MDC.remove` as optional because "the log line already printed, so what does
it matter." On a pool thread, it matters enormously: the thread is returned to the pool and reused
for the next unrelated task. If task A sets `traceId=abc-123` and never removes it, task B — which
never touches MDC at all — inherits `abc-123` in every log line it emits, silently attributing
B's work to A's trace. The fix is unconditional: every path that sets an MDC value must clear or
restore it in a `finally`, including the exception path, because an uncaught exception is exactly
when the trace id is most needed downstream and exactly when a naive `try { … } catch` without a
`finally` skips the cleanup.

> **Definition.** MDC (Mapped Diagnostic Context) is a `ThreadLocal`-backed key-value map that
> logging frameworks interpolate into log output; on a thread pool its lifetime must be scoped
> with `try`/`finally` to the task, never left to expire with the thread.

### 2.11.5 OpenTelemetry `Context` and `Scope`

**[RESEARCH]** OpenTelemetry's propagation story is structurally the same pattern as MDC, wearing
different names: `Context` is the immutable, request-scoped value (trace id, span id, baggage);
`Context.makeCurrent()` installs it on the current thread and returns a `Scope`; the `Scope` is
`AutoCloseable`, so the idiomatic shape is `try (Scope scope = context.makeCurrent()) { … }`,
where the `try`-with-resources block *is* the `finally` — the compiler generates the close call
rather than a human writing one by hand.

```java
Context assessmentContext = Context.current().with(ASSESSMENT_SPAN, span);
executor.execute(() -> {
    try (Scope scope = assessmentContext.makeCurrent()) {
        assessmentService.scoreIncome(applicationId);
    }
});
```

**Unverified:** the exact class and method names above (`io.opentelemetry.context.Context`,
`.makeCurrent()`, `Scope`) reflect the well-known OpenTelemetry Java API shape, but this session's
web research could not load the OpenTelemetry javadoc to confirm current signatures against the
live source; see `## Open questions`.

## The `ThreadLocal` audit

### 2.11.6 Finding leaks in a running system

A `ThreadLocalMap$Entry` leak has a specific, recognizable signature in a heap dump, because
`ThreadLocalMap`'s entries are weakly referenced *on the key* (the `ThreadLocal` object) but
strongly referenced *on the value*. When the `ThreadLocal` itself becomes unreachable — commonly
because it was a `static final` field in a class loaded by a web-app classloader that has since
been undeployed — the weak key is cleared, but the strong value reference keeps the entry, and
everything it points to, alive as long as the owning `Thread` lives. On a pooled thread that never
terminates, that is forever.

**The audit checklist:**

1. Take a heap dump of the running JVM (`jcmd <pid> GC.heap_dump <path>`, or on OOM automatically
   via `-XX:+HeapDumpOnOutOfMemoryError`).
2. In the analyzer, query for instances of `java.lang.ThreadLocal$ThreadLocalMap$Entry`.
3. For each retained entry, inspect the `value` field's class and its classloader. A value whose
   class was loaded by a classloader that is itself unreachable from any live root except this
   entry — the "value class loaded by a dead classloader" signature — is a confirmed leak: the
   classloader, and every class and static field it defined, is being kept alive purely by one
   forgotten `ThreadLocal` entry.
4. Cross-reference the entry's owning `Thread` against the thread pool it belongs to. If the pool
   is long-lived (which almost all application server and executor pools are), every entry that
   was ever set and never removed accumulates for the life of the process.
5. In the source, grep for every `ThreadLocal.set(...)` and confirm each has a matching `remove()`
   reachable from every exit path of the method that set it, including exceptions.
6. Repeat the heap dump after a load test that exercises the suspect code path repeatedly; a real
   leak shows entry count growing linearly with request count instead of staying flat.

### 2.11.7 Why a leak persists indefinitely

`ThreadLocalMap` does not proactively scan for and remove stale entries (ones whose key has been
garbage-collected) on any timer or background thread. Expunging happens only *opportunistically*,
as a side effect of `get`, `set`, or `remove` calls that happen to probe a bucket containing a
stale entry during their own linear-probe traversal. If nothing ever calls `get`/`set`/`remove`
again for that `ThreadLocal` on that thread, the stale entry sits in the map, holding its
value, for as long as the thread lives — which on a pool thread can be the lifetime of the
process. This is precisely why "just let the GC handle it" is wrong: the *key* is weak and does
get collected, but the *entry slot and its value* are not, and nothing walks the table to reclaim
them without a triggering access.

## `ThreadLocal` as context, never cache

### 2.11.8 The virtual-thread rule

`ThreadLocal` is fully supported on virtual threads and behaves identically in every observable
way — it is still per-thread state. What changes is the cost model of misusing it. A pooled
platform thread is a scarce, long-lived resource shared across many requests; a `ThreadLocal`
used to *cache* an expensive-to-construct object per thread (a `SimpleDateFormat`, a
`DocumentBuilder`, a per-thread scratch buffer) amortizes that construction cost across the many
requests that thread will serve over its lifetime. A virtual thread is created fresh per task and
discarded after — there is no "next request" on the same virtual thread to amortize against.
Using `ThreadLocal` as a cache on virtual threads means paying the full construction cost on
*every single task*, an initialization storm multiplied by however many virtual threads the
application spins up, which on a system built for `55k` peak concurrent sessions each on its own
virtual thread is not a rounding error.

**Pitfall:** carrying forward the pooled-thread habit of "cache the expensive object in a
`ThreadLocal` so we only pay for it once" onto virtual threads. The symptom is a system that gets
*slower* under the virtual-thread migration a team expected to speed things up, because every task
now re-runs the expensive initializer that used to be amortized. The fix is to separate the two
uses `ThreadLocal` had been quietly serving: as **context** (small, request-scoped, always
removed in a `finally` — trace ids, the current `Reservation`'s tenant, the authenticated
principal for the duration of one call) it is still correct and cheap on virtual threads, because
its lifetime already matches the task's lifetime. As a **cache** (large or expensive,
thread-scoped, meant to outlive any one task) it is a memory leak on a bounded pool and an
initialization storm on virtual threads — the fix there is a real cache keyed by something other
than the thread (a `ConcurrentHashMap`, an object pool, or simply constructing the object once at
class-init time if it is thread-safe to share).

> **Definition.** `ThreadLocal` is context, never cache: it should hold small, request-scoped
> values whose lifetime is bounded and removed in a `finally`, never a thread-scoped cache of an
> expensive object, because that distinction is exactly what breaks under virtual threads.

### 2.11.9 `ScopedValue` as the migration target

`ScopedValue` (final in JDK 25 per JEP 506; still preview in Java 21, requiring
`--enable-preview`) replaces the context use of `ThreadLocal` with a value that is bound for the
dynamic extent of one call — `ScopedValue.where(TRACE_ID, id).run(() -> ...)` — and is immutable
and automatically unbound when that call returns, including via exception. That constraint (no
`set`, no `remove`, cannot outlive the binding block) is exactly what makes it safe by
construction where `ThreadLocal` is safe only by discipline: there is no `finally` to forget,
because there is nothing to clean up — the binding is popped by the JVM when the `run` block
exits.

| | `ThreadLocal` | `ScopedValue` |
|---|---|---|
| Mutability | Mutable (`set` any time) | Immutable for the life of the binding |
| Lifetime | Until explicit `remove()`, or the thread dies | Exactly the dynamic extent of one `run`/`call` |
| Cleanup | Manual, in a `finally` | Automatic, structural |
| Inherited by child threads | No (needs `InheritableThreadLocal`, and even that doesn't cross pools) | Yes, automatically, by threads a `StructuredTaskScope` forks from within the binding |
| Typical failure mode | Leak from a forgotten `remove()` | Cannot be used for the leftover use cases below |

### 2.11.10 What still needs `ThreadLocal` after `ScopedValue`

`ScopedValue` does not replace every use of `ThreadLocal`, because its two constraints are also
its two hard limits. First, anything that must be **set by a callee for its caller to read
later** — a validation method that accumulates warnings into a per-thread list its caller inspects
afterward, or a JDBC-style pattern where a lower layer stashes a generated id for an upper layer
to retrieve after the call returns — cannot be expressed as a `ScopedValue`, because a
`ScopedValue` binding is read-only once installed by whoever called `where(...).run(...)`; the
callee cannot rebind it for the caller. Second, anything crossing a **non-structured boundary** —
handing work to an unrelated thread pool that was not forked from within the current binding via
`StructuredTaskScope`, a message picked up later by a consumer thread, a value that needs to
outlive the call that produced it — has no scope for `ScopedValue` to be bound to, since its whole
safety model depends on there being a lexical block whose exit unbinds it. `ApplicationGateway`'s
trace id, if forwarded onto a Kafka message header for `AssessmentService` to pick up on a
consumer thread minutes later, is exactly this second case: there is no shared call stack for a
`ScopedValue` to span, so the receiving side reads the header and sets a fresh `ThreadLocal` (or
MDC entry) of its own.

**Pitfall:** assuming `ScopedValue` is a drop-in replacement everywhere `ThreadLocal` appears
today. It replaces the common case — read-only, call-scoped context passed down and across
structured concurrency — but the caller-mutates-for-caller and cross-non-structured-boundary cases
are not migratable, and forcing them onto `ScopedValue` either does not compile (no `set`) or
requires restructuring the call shape to fit a scope that does not naturally exist.

## Pitfalls

### Assuming `ThreadLocal.remove()` in a `finally` is optional if the task "always succeeds"

**Wrong**

```java
executor.submit(() -> {
    MDC.put("traceId", traceId);
    assessmentService.scoreIncome(applicationId); // throws on a bad applicationId
    MDC.remove("traceId"); // never reached
});
```

An exception thrown by `scoreIncome` skips the `remove()` entirely. The pool thread returns to the
pool still carrying `traceId`, and the very next unrelated task run on that thread inherits it —
its logs now falsely claim the previous request's trace id.

**Right**

```java
executor.submit(() -> {
    MDC.put("traceId", traceId);
    try {
        assessmentService.scoreIncome(applicationId);
    } finally {
        MDC.remove("traceId");
    }
});
```

The `finally` runs on every exit path, exception or not, which is the only way to guarantee the
pool thread is clean before it is reused.

**Why people believe it:** in a single-shot, one-thread-per-request model (a `Thread` created and
discarded per request, or the pre-pool servlet-container era) the thread dies after the request
regardless of what is left in its `ThreadLocal` map, so skipping cleanup was genuinely harmless.
The habit outlives the model once the same code moves onto a pooled executor.

### Using `ThreadLocal` to cache an expensive object and expecting the same win on virtual threads

**Wrong**

```java
private static final ThreadLocal<ExpensiveScoringModel> MODEL =
        ThreadLocal.withInitial(ExpensiveScoringModel::new); // constructs a fresh model per task
```

On a fixed pool of, say, 20 platform threads serving thousands of requests, the model is built 20
times total. On a virtual-thread-per-task executor handling `55k` peak concurrent sessions, each
virtual thread is new, so `withInitial` runs on effectively every task — tens of thousands of
constructions instead of 20.

**Right**

```java
private static final ExpensiveScoringModel MODEL = new ExpensiveScoringModel(); // built once,
                                                                                  // shared, if
                                                                                  // thread-safe
```

or, if the model genuinely needs per-caller isolation, a bounded object pool keyed by checkout,
not by thread identity.

**Why people believe it:** the `ThreadLocal`-as-cache idiom was correct and idiomatic advice for
years under the platform-thread-pool model that dominated Java service code before virtual
threads existed; the advice did not change with the runtime, but the cost model it depended on
did.

## Cheat sheet

| Question | Answer |
|---|---|
| Does an `Executor` copy `ThreadLocal` state automatically? | No — never, for any `Executor` |
| Cheapest fix for one call site | Manual copy: read, set, `finally` remove |
| Fix that scales across a whole pool | Decorate the `Executor`, not each `Runnable` |
| Fix that generalizes across many context types at once | Micrometer `ContextSnapshot` |
| Fix with no cleanup step needed | `ScopedValue` + structured concurrency (binding auto-unwinds) |
| MDC's non-negotiable rule on a pool | `MDC.remove()` / `MDC.clear()` in a `finally`, every exit path |
| Heap-dump signature of a `ThreadLocal` leak | `ThreadLocalMap$Entry` value class loaded by a dead classloader |
| Why a stale entry doesn't just disappear | Expunging is opportunistic, triggered only by `get`/`set`/`remove` on that map |
| `ThreadLocal` as context vs. cache | Context: fine, still fine on virtual threads. Cache: leak on pools, init storm on virtual threads |
| What `ScopedValue` cannot do | Be set by a callee for its caller; cross a non-structured boundary; outlive its `run` block |

## Self-test

**Q1.** Why does submitting a `Runnable` to an `ExecutorService` not automatically carry the
submitting thread's MDC trace id into the task?

<details><summary>Answer</summary>

MDC's context map is a `ThreadLocal`, which is state attached to one specific `Thread` object.
The pool thread that eventually runs the task is a different `Thread` instance from the one that
called `submit`, and the JDK does not copy any `ThreadLocal` state across that boundary — it has
to be copied explicitly, by one of the five mechanisms in D-137.

</details>

**Q2.** What is the practical difference between decorating each submitted `Runnable` and
decorating the `Executor` itself?

<details><summary>Answer</summary>

Decorating each `Runnable` requires every call site that submits work to remember to wrap it —
one missed call site silently loses context. Decorating the `Executor` centralizes the wrap so
every task that passes through it is covered automatically, with no per-call-site discipline
required.

</details>

**Q3.** Why must `MDC.remove()` (or an equivalent restore) run in a `finally`, not just at the end
of the happy path?

<details><summary>Answer</summary>

Pool threads are reused across many unrelated tasks. If a task throws and the cleanup line after
it is never reached, the thread returns to the pool still carrying that task's trace id, and the
next task run on that same thread inherits it, misattributing its own log lines.

</details>

**Q4.** Why does a `ThreadLocal` leak persist even though the `ThreadLocal` object itself is only
weakly referenced from the map entry?

<details><summary>Answer</summary>

The weak reference is only on the entry's *key* (the `ThreadLocal` instance); the *value* is
strongly referenced. When the key is collected, the entry becomes stale but is not automatically
removed — removal (expunging) only happens opportunistically as a side effect of a later
`get`/`set`/`remove` call on that same map. If nothing touches the map again, the stale entry and
its value stay alive for the life of the thread.

</details>

**Q5.** Why is caching an expensive object in a `ThreadLocal` a much worse idea on virtual threads
than on a platform-thread pool?

<details><summary>Answer</summary>

On a bounded platform-thread pool, the cache is built once per pool thread and amortized across
every request that thread ever serves. A virtual thread is created fresh per task and never
reused, so the same caching pattern rebuilds the expensive object on effectively every task — an
initialization storm proportional to task count rather than pool size.

</details>

**Q6.** Name one legitimate use of `ThreadLocal` that `ScopedValue` cannot replace, and explain
why.

<details><summary>Answer</summary>

A value that must be set by a callee for its caller to read after the call returns — `ScopedValue`
bindings are read-only for the duration set by whoever called `where(...).run(...)`; a callee
cannot rebind the value for its caller. Also, anything crossing a non-structured boundary (an
unrelated thread pool, a message consumed later) has no lexical scope for a `ScopedValue` binding
to be attached to.

</details>

**Q7.** In the decorating-`Executor` example, why does the wrapper capture and restore
`previousContext` instead of just calling `MDC.clear()` at the end?

<details><summary>Answer</summary>

If the pool thread was already carrying context from an outer scope before this task ran (nested
decorators, or a pool used for more than one purpose), an unconditional `clear()` would erase that
outer context instead of restoring it. Capturing the previous map and restoring it makes the
decorator safe to nest.

</details>

**Q8.** What heap-dump evidence distinguishes a genuine `ThreadLocal` leak from a `ThreadLocal`
that is simply still legitimately in use?

<details><summary>Answer</summary>

A genuine leak shows a `ThreadLocalMap$Entry` whose value's class was loaded by a classloader that
is otherwise unreachable — the "dead classloader" signature — meaning the only thing keeping that
classloader (and everything it defined) alive is the forgotten entry. A legitimately in-use entry
points to a class loaded by a live, reachable classloader.

</details>

## Open questions

- **Unverified:** the exact OpenTelemetry Java API class and method names quoted in §2.11.5
  (`io.opentelemetry.context.Context`, `.current()`, `.with(...)`, `.makeCurrent()`, `Scope`) —
  this session could not load OpenTelemetry's own javadoc to confirm current signatures; the shape
  quoted matches the well-known public API but was not re-verified against a live primary source
  this run.
- **Unverified:** Micrometer `ContextSnapshot`'s exact method names (`captureAll`, `wrap`,
  `setThreadLocalsFrom` and similar) — this session's WebFetch reached only the context-propagation
  landing page and a javadoc index page, neither of which rendered the interface's method list;
  the row in D-137 describes the library's documented purpose (propagating `ThreadLocal`, Reactor
  `Context`, and other context types) rather than asserting specific signatures.

---

**Leaves covered:** 2.11.1–2.11.10 (10 leaves)
**Leaves deferred:** none
**Diagrams included:** D-137
**Target version:** Java 21 LTS
**Lines:** 528
